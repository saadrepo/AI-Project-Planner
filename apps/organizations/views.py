import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.core.utils import emails_match

from .forms import InvitationCreateForm, OrganizationCreateForm, OrganizationMemberAssignForm, OrganizationMemberRoleForm, OrganizationSwitchForm, OrganizationUpdateForm
from .models import Organization, OrganizationInvitation, OrganizationMember, OrganizationMemberRole
from .services import (
    can_change_member_role,
    can_create_organization,
    can_edit_organization,
    can_manage_invitations,
    can_manage_members,
    can_remove_member,
    can_view_organization,
    create_organization,
    get_active_organization,
    get_membership,
    get_organization_for_user,
    get_pending_invitations,
    get_user_organizations,
    is_organization_member,
    log_activity,
    send_organization_invitation_email,
    set_active_organization,
)


@login_required
def organization_list_view(request):
    organizations = get_user_organizations(request.user)
    active_organization = get_active_organization(request)
    active_organization_membership = get_membership(request.user, active_organization) if active_organization else None
    return render(request, "organizations/list.html", {
        "organizations": organizations,
        "active_organization": active_organization,
        "can_create_organization": can_create_organization(request.user),
        "active_organization_membership": active_organization_membership,
    })


@login_required
def organization_create_view(request):
    if not can_create_organization(request.user):
        return HttpResponseForbidden("Only an existing organization owner can create an organization.")
    form = OrganizationCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            organization = create_organization(request.user, form.cleaned_data["name"], form.cleaned_data.get("description", ""))
        except (PermissionDenied, ValueError) as exc:
            form.add_error(None, str(exc))
        else:
            set_active_organization(request, organization)
            messages.success(request, f"Organization '{organization.name}' created successfully.")
            return redirect("organization_detail", slug=organization.slug)
    return render(request, "organizations/create.html", {"form": form})


@login_required
def organization_detail_view(request, slug):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to this organization.")
    if not can_view_organization(request.user, organization):
        return HttpResponseForbidden("You do not have access to this organization.")
    set_active_organization(request, organization)
    member_count = organization.members.filter(is_active=True).count()
    membership = get_membership(request.user, organization)
    pending_invitation_count = get_pending_invitations(organization).count()
    return render(request, "organizations/detail.html", {"organization": organization, "membership": membership, "member_count": member_count, "pending_invitation_count": pending_invitation_count})


@login_required
@require_POST
def organization_switch_view(request):
    form = OrganizationSwitchForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Select a valid organization.")
        return redirect("organization_list")
    try:
        organization = get_organization_for_user(request.user, organization_id=form.cleaned_data["organization_id"])
    except Organization.DoesNotExist:
        messages.error(request, "You do not belong to that organization.")
        return redirect("organization_list")
    if not is_organization_member(request.user, organization):
        messages.error(request, "You do not belong to that organization.")
        return redirect("organization_list")
    set_active_organization(request, organization)
    messages.success(request, f"Switched to {organization.name}.")
    return redirect("organization_detail", slug=organization.slug)


@login_required
def organization_members_view(request, slug):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to this organization.")
    if not can_view_organization(request.user, organization):
        return HttpResponseForbidden("You do not have access to this organization.")
    members = organization.members.filter(is_active=True).select_related("user").order_by("role", "user__email")
    membership = get_membership(request.user, organization)
    return render(request, "organizations/members.html", {"organization": organization, "members": members, "membership": membership})


@login_required
def organization_member_assign_view(request, slug):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to this organization.")
    membership = get_membership(request.user, organization)
    if membership is None or membership.role != OrganizationMemberRole.OWNER:
        return HttpResponseForbidden("Only the organization owner can assign registered users.")

    form = OrganizationMemberAssignForm(request.POST or None)
    users = User.objects.filter(is_active=True).order_by("email")
    existing_memberships = {
        member.user_id: member
        for member in organization.members.filter(is_active=True).select_related("user")
    }
    for user in users:
        user.organization_membership = existing_memberships.get(user.pk)
    if request.method == "POST" and form.is_valid():
        user = User.objects.filter(pk=form.cleaned_data["user_id"], is_active=True).first()
        if user is None:
            form.add_error("user_id", "Select a valid registered user.")
        elif user.pk == request.user.pk:
            form.add_error("user_id", "The owner is already a member of this organization.")
        else:
            assigned_membership = organization.members.filter(user=user).first()
            if assigned_membership is None:
                assigned_membership = OrganizationMember.objects.create(
                    organization=organization,
                    user=user,
                    role=form.cleaned_data["role"],
                    is_active=True,
                )
                action = "member_assigned"
            else:
                assigned_membership.role = form.cleaned_data["role"]
                assigned_membership.is_active = True
                assigned_membership.save(update_fields=["role", "is_active", "updated_at"])
                action = "member_assigned"
            log_activity(organization, request.user, action, "organization_member", str(assigned_membership.pk), description=f"Assigned {user.email} to the organization")
            messages.success(request, f"{user.email} was assigned to {organization.name}.")
            return redirect("organization_member_assign", slug=organization.slug)
    return render(request, "organizations/assign_member.html", {"organization": organization, "membership": membership, "users": users, "form": form})


@login_required
@require_POST
def member_role_view(request, slug, member_id):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to this organization.")
    membership = organization.members.filter(pk=member_id, is_active=True).select_related("user").first()
    if membership is None:
        return HttpResponseForbidden("Membership not found.")
    if not can_change_member_role(request.user, organization, membership):
        return HttpResponseForbidden("You are not allowed to change this member role.")
    form = OrganizationMemberRoleForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a valid role.")
        return redirect("organization_members", slug=organization.slug)
    requested_role = form.cleaned_data["role"]
    if requested_role == OrganizationMemberRole.OWNER:
        messages.error(request, "Ownership cannot be assigned or transferred.")
        return redirect("organization_members", slug=organization.slug)
    previous_role = membership.role
    membership.role = requested_role
    membership.save(update_fields=["role", "updated_at"])
    log_activity(organization, request.user, "member_role_changed", "organization_member", str(membership.pk), description=f"Changed member role from {previous_role} to {requested_role}")
    messages.success(request, f"Updated {membership.user.email} to {requested_role}.")
    return redirect("organization_members", slug=organization.slug)


@login_required
@require_POST
def member_remove_view(request, slug, member_id):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to this organization.")
    membership = organization.members.filter(pk=member_id, is_active=True).select_related("user").first()
    if membership is None:
        return HttpResponseForbidden("Membership not found.")
    if not can_remove_member(request.user, organization, membership):
        return HttpResponseForbidden("You are not allowed to remove this member.")
    if membership.user_id == request.user.pk and organization.members.filter(role=OrganizationMemberRole.OWNER, is_active=True).count() <= 1:
        messages.error(request, "You cannot remove the only owner.")
        return redirect("organization_members", slug=organization.slug)
    log_activity(organization, request.user, "member_removed", "organization_member", str(membership.pk), description=f"Removed member {membership.user.email}")
    membership.delete()
    messages.success(request, f"Removed {membership.user.email} from {organization.name}.")
    return redirect("organization_members", slug=organization.slug)


@login_required
def organization_invitations_view(request, slug):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to this organization.")
    if not can_manage_invitations(request.user, organization):
        return HttpResponseForbidden("You are not allowed to manage invitations.")
    form = InvitationCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        role = form.cleaned_data["role"]
        if organization.members.filter(user__email__iexact=email, is_active=True).exists():
            form.add_error("email", "This user is already a member of this organization.")
        elif OrganizationInvitation.objects.filter(organization=organization, email__iexact=email, status=OrganizationInvitation.Status.PENDING, expires_at__gt=timezone.now()).exists():
            invitation = OrganizationInvitation.objects.filter(
                organization=organization,
                email__iexact=email,
                status=OrganizationInvitation.Status.PENDING,
                expires_at__gt=timezone.now(),
            ).order_by("-created_at").first()
            invitation.token = secrets.token_urlsafe(32)
            invitation.expires_at = timezone.now() + timedelta(days=7)
            invitation.role = role
            invitation.invited_by = request.user
            invitation.save(update_fields=["token", "expires_at", "role", "invited_by", "updated_at"])
            email_sent = send_organization_invitation_email(invitation)
            log_activity(organization, request.user, "invitation_resent", "organization_invitation", str(invitation.pk), description=f"Resent invitation for {email}")
            if email_sent:
                messages.success(request, f"Invitation resent to {email}.")
            else:
                messages.warning(request, "Invitation exists, but email delivery failed. Check your SMTP server and try again.")
            return redirect("organization_invitations", slug=organization.slug)
        else:
            token = secrets.token_urlsafe(32)
            invitation = OrganizationInvitation.objects.create(
                organization=organization,
                email=email,
                role=role,
                invited_by=request.user,
                token=token,
                expires_at=timezone.now() + timedelta(days=7),
            )
            email_sent = send_organization_invitation_email(invitation)
            log_activity(organization, request.user, "invitation_created", "organization_invitation", str(invitation.pk), description=f"Invited {email} as {role}")
            if email_sent:
                messages.success(request, f"Invitation sent to {email}.")
            else:
                messages.warning(request, "Invitation created, but email delivery failed. Check your SMTP settings or resend the invitation later.")
            return redirect("organization_invitations", slug=organization.slug)
    invitations = get_pending_invitations(organization)
    return render(request, "organizations/invitations.html", {"organization": organization, "invitations": invitations, "form": form})


@login_required
@require_POST
def create_invitation_view(request, slug):
    return organization_invitations_view(request, slug)


@login_required
@require_POST
def resend_invitation_view(request, slug, invitation_id):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to this organization.")
    if not can_manage_invitations(request.user, organization):
        return HttpResponseForbidden("You are not allowed to manage invitations.")
    invitation = organization.invitations.filter(pk=invitation_id).first()
    if invitation is None:
        return HttpResponseForbidden("Invitation not found.")
    invitation.token = secrets.token_urlsafe(32)
    invitation.expires_at = timezone.now() + timedelta(days=7)
    invitation.status = OrganizationInvitation.Status.PENDING
    invitation.revoked_at = None
    invitation.accepted_at = None
    invitation.save(update_fields=["token", "expires_at", "status", "revoked_at", "accepted_at", "updated_at"])
    email_sent = send_organization_invitation_email(invitation)
    log_activity(organization, request.user, "invitation_resent", "organization_invitation", str(invitation.pk), description=f"Resent invitation for {invitation.email}")
    if email_sent:
        messages.success(request, "Invitation resent.")
    else:
        messages.warning(request, "Invitation was resent, but email delivery failed. Check SMTP settings or try again later.")
    return redirect("organization_invitations", slug=organization.slug)


@login_required
@require_POST
def revoke_invitation_view(request, slug, invitation_id):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to this organization.")
    if not can_manage_invitations(request.user, organization):
        return HttpResponseForbidden("You are not allowed to manage invitations.")
    invitation = organization.invitations.filter(pk=invitation_id).first()
    if invitation is None:
        return HttpResponseForbidden("Invitation not found.")
    invitation.status = OrganizationInvitation.Status.REVOKED
    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=["status", "revoked_at", "updated_at"])
    log_activity(organization, request.user, "invitation_revoked", "organization_invitation", str(invitation.pk), description=f"Revoked invitation for {invitation.email}")
    messages.success(request, "Invitation revoked.")
    return redirect("organization_invitations", slug=organization.slug)


def accept_invitation_view(request, token):
    invitation = OrganizationInvitation.objects.filter(token=token).select_related("organization").first()
    if invitation is None:
        return render(request, "organizations/invitation_accept.html", {"valid": False, "error": "This invitation is invalid or no longer available."})
    if invitation.status == OrganizationInvitation.Status.ACCEPTED:
        return render(request, "organizations/invitation_accept.html", {"valid": False, "invitation": invitation, "error": "This invitation has already been accepted. Open Organizations to access the team."})
    if invitation.status == OrganizationInvitation.Status.REVOKED or invitation.status == OrganizationInvitation.Status.EXPIRED or invitation.expires_at <= timezone.now():
        return render(request, "organizations/invitation_accept.html", {"valid": False, "invitation": invitation, "error": "This invitation is no longer valid."})
    if not request.user.is_authenticated:
        return redirect(f"/login/?next=/invitations/{token}/")
    if not emails_match(request.user.email, invitation.email):
        return render(request, "organizations/invitation_accept.html", {"valid": False, "invitation": invitation, "error": "This invitation is for a different email address."})
    organization = invitation.organization
    if request.method != "POST":
        return render(request, "organizations/invitation_accept.html", {"valid": True, "invitation": invitation})
    if organization.members.filter(user=request.user, is_active=True).exists():
        invitation.accepted_at = timezone.now()
        invitation.status = OrganizationInvitation.Status.ACCEPTED
        invitation.save(update_fields=["accepted_at", "status", "updated_at"])
        messages.info(request, "You are already a member of this organization.")
        return redirect("organization_detail", slug=organization.slug)
    with transaction.atomic():
        OrganizationMember.objects.create(organization=organization, user=request.user, role=invitation.role, is_active=True)
        invitation.accepted_at = timezone.now()
        invitation.status = OrganizationInvitation.Status.ACCEPTED
        invitation.save(update_fields=["accepted_at", "status", "updated_at"])
        set_active_organization(request, organization)
    messages.success(request, f"Welcome to {organization.name}.")
    log_activity(organization, request.user, "invitation_accepted", "organization_invitation", str(invitation.pk), description=f"Accepted invitation to {organization.name}")
    return redirect("organization_detail", slug=organization.slug)


@login_required
def organization_settings_view(request, slug):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to this organization.")
    if not can_edit_organization(request.user, organization):
        return HttpResponseForbidden("You are not allowed to edit this organization.")

    if request.method == "POST":
        data = request.POST.copy()
        if not data.get("slug"):
            data["slug"] = organization.slug
        form = OrganizationUpdateForm(data, instance=organization)
        if form.is_valid():
            form.save()
            messages.success(request, "Organization settings updated.")
            log_activity(organization, request.user, "organization_updated", "organization", str(organization.pk), description="Updated organization details")
            return redirect("organization_detail", slug=organization.slug)
    else:
        form = OrganizationUpdateForm(instance=organization)

    return render(request, "organizations/settings.html", {"form": form, "organization": organization})

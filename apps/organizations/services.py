from __future__ import annotations

import logging
from smtplib import SMTPAuthenticationError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db.models import QuerySet
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)

from apps.core.models import ActivityLog
from apps.core.utils import emails_match

from .models import Organization, OrganizationInvitation, OrganizationMember, OrganizationMemberRole

User = get_user_model()


def get_user_organizations(user):
    return Organization.objects.filter(members__user=user, members__is_active=True).distinct().order_by("name")


def can_create_organization(user):
    return bool(
        user
        and user.is_authenticated
        and OrganizationMember.objects.filter(
            user=user,
            role=OrganizationMemberRole.OWNER,
            is_active=True,
        ).exists()
    )


def create_organization(user, name, description=""):
    if not can_create_organization(user):
        raise PermissionDenied("Only an existing organization owner can create an organization.")
    name = (name or "").strip()
    slug = slugify(name)
    if not name or not slug:
        raise ValueError("Organization name is required.")
    with transaction.atomic():
        organization = Organization.objects.create(
            name=name,
            description=description or "",
            slug=slug,
            owner=user,
        )
        OrganizationMember.objects.create(
            organization=organization,
            user=user,
            role=OrganizationMemberRole.OWNER,
            is_active=True,
        )
        log_activity(organization, user, "organization_created", "organization", str(organization.pk), description="Created organization")
    return organization


def is_organization_member(user, organization):
    if not user or not user.is_authenticated:
        return False
    return OrganizationMember.objects.filter(user=user, organization=organization, is_active=True).exists()


def get_membership(user, organization):
    if not user or not user.is_authenticated:
        return None
    return OrganizationMember.objects.filter(user=user, organization=organization, is_active=True).select_related("organization", "user").first()


def get_active_organization(request):
    if not request.user.is_authenticated:
        return None
    active_id = request.session.get("active_organization_id")
    if not active_id:
        org = get_user_organizations(request.user).first()
        if org:
            request.session["active_organization_id"] = str(org.pk)
        return org
    try:
        organization = get_user_organizations(request.user).get(pk=active_id)
    except (Organization.DoesNotExist, ValueError):
        request.session.pop("active_organization_id", None)
        fallback = get_user_organizations(request.user).first()
        if fallback:
            request.session["active_organization_id"] = str(fallback.pk)
        return fallback
    return organization


def set_active_organization(request, organization):
    if organization is None:
        request.session.pop("active_organization_id", None)
        return
    if not is_organization_member(request.user, organization):
        raise PermissionDenied("You do not belong to this organization.")
    request.session["active_organization_id"] = str(organization.pk)


def can_view_organization(user, organization):
    return is_organization_member(user, organization)


def can_manage_organization(user, organization):
    membership = get_membership(user, organization)
    return bool(membership and membership.role in {OrganizationMemberRole.OWNER, OrganizationMemberRole.ADMIN})


def can_manage_members(user, organization):
    membership = get_membership(user, organization)
    return bool(membership and membership.role in {OrganizationMemberRole.OWNER, OrganizationMemberRole.ADMIN})


def can_manage_invitations(user, organization):
    membership = get_membership(user, organization)
    return bool(membership and membership.role in {OrganizationMemberRole.OWNER, OrganizationMemberRole.ADMIN})


def can_edit_organization(user, organization):
    membership = get_membership(user, organization)
    return bool(membership and membership.role == OrganizationMemberRole.OWNER)


def can_change_member_role(user, organization, target_membership):
    if not user or not user.is_authenticated:
        return False
    if target_membership is None or target_membership.organization_id != organization.pk:
        return False
    membership = get_membership(user, organization)
    if membership is None:
        return False
    if membership.role not in {OrganizationMemberRole.OWNER, OrganizationMemberRole.ADMIN}:
        return False
    if target_membership.role == OrganizationMemberRole.OWNER:
        return False
    return True


def can_remove_member(user, organization, target_membership):
    if not user or not user.is_authenticated:
        return False
    if target_membership is None or target_membership.organization_id != organization.pk:
        return False
    membership = get_membership(user, organization)
    if membership is None:
        return False
    if membership.role not in {OrganizationMemberRole.OWNER, OrganizationMemberRole.ADMIN}:
        return False
    if target_membership.role == OrganizationMemberRole.OWNER:
        return False
    return True


def get_organization_for_user(user, slug=None, organization_id=None):
    qs = get_user_organizations(user)
    if slug is not None:
        return qs.get(slug=slug)
    if organization_id is not None:
        return qs.get(pk=organization_id)
    raise ValueError("An organization lookup key is required.")


def log_activity(organization, user, action, entity_type, entity_id=None, description="", metadata=None):
    if organization is None:
        return None
    return ActivityLog.objects.create(
        organization=organization,
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        metadata=metadata or {},
    )


def get_pending_invitations(organization):
    return OrganizationInvitation.objects.filter(
        organization=organization,
        status=OrganizationInvitation.Status.PENDING,
        expires_at__gt=timezone.now(),
    ).order_by("-created_at")


def send_organization_invitation_email(invitation):
    if invitation is None:
        return None

    accept_url = f"{settings.BASE_URL}/invitations/{invitation.token}/" if getattr(settings, "BASE_URL", None) else None
    context = {
        "organization": invitation.organization,
        "invited_by": invitation.invited_by,
        "invitation": invitation,
        "accept_url": accept_url,
    }
    subject = f"You’re invited to join {invitation.organization.name} on ProjectPilot AI"
    message = render_to_string("organizations/invitation_email.txt", context)

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [invitation.email], fail_silently=False)
    except SMTPAuthenticationError:
        logger.exception("SMTP authentication failed while sending invitation email to %s", invitation.email)
        return False
    except Exception:
        logger.exception("Failed to send invitation email to %s", invitation.email)
        return False

    return True

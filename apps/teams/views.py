from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from apps.organizations.models import Organization
from apps.organizations.services import can_manage_members, get_membership, get_organization_for_user, log_activity

from .forms import TeamCreateForm


@login_required
def team_list_view(request, slug):
    try:
        organization = get_organization_for_user(request.user, slug=slug)
    except Organization.DoesNotExist:
        return HttpResponseForbidden("You do not have access to that organization.")
    membership = get_membership(request.user, organization)
    form = TeamCreateForm(request.POST or None)
    if request.method == "POST":
        if not can_manage_members(request.user, organization):
            return HttpResponseForbidden("You are not allowed to manage teams.")
        if form.is_valid():
            try:
                team = form.save(commit=False)
                team.organization = organization
                team.save()
            except IntegrityError:
                form.add_error("name", "A team with this name already exists.")
            else:
                log_activity(organization, request.user, "team_created", "team", str(team.pk), description=f"Created team {team.name}")
                messages.success(request, f"Team '{team.name}' created.")
                return redirect("organization_teams", slug=organization.slug)
    teams = organization.teams.prefetch_related("members__user").all()
    return render(request, "teams/list.html", {"organization": organization, "membership": membership, "teams": teams, "form": form})

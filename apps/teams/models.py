from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.organizations.models import Organization


class Team(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    lead = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="led_teams")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_team_name_per_organization"),
        ]
        indexes = [
            models.Index(fields=["organization", "name"]),
            models.Index(fields=["lead", "organization"]),
        ]
        ordering = ["organization__name", "name"]

    def __str__(self):
        return self.name


class TeamMember(BaseModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_memberships")
    role = models.CharField(max_length=50, default="MEMBER")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="unique_team_member"),
        ]
        indexes = [models.Index(fields=["team", "user"]), models.Index(fields=["user", "role"])]
        ordering = ["team__name", "user__email"]

    def __str__(self):
        return f"{self.user.email} in {self.team.name}"

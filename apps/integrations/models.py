from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.organizations.models import Organization


class IntegrationProvider(models.TextChoices):
    SLACK = "SLACK", "Slack"
    MICROSOFT_TEAMS = "MICROSOFT_TEAMS", "Microsoft Teams"
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR", "Google Calendar"
    GOOGLE_DRIVE = "GOOGLE_DRIVE", "Google Drive"
    GITHUB = "GITHUB", "GitHub"
    JIRA = "JIRA", "Jira"
    NOTION = "NOTION", "Notion"
    TRELLO = "TRELLO", "Trello"
    LINEAR = "LINEAR", "Linear"


class IntegrationStatus(models.TextChoices):
    CONNECTED = "CONNECTED", "Connected"
    DISCONNECTED = "DISCONNECTED", "Disconnected"
    ERROR = "ERROR", "Error"


class Integration(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="integrations")
    provider = models.CharField(max_length=30, choices=IntegrationProvider.choices, default=IntegrationProvider.SLACK)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=IntegrationStatus.choices, default=IntegrationStatus.DISCONNECTED)
    credentials = models.JSONField(default=dict, blank=True)
    integration_settings = models.JSONField(default=dict, blank=True)
    connected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="connected_integrations")
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["connected_by", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.provider})"

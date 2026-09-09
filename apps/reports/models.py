import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.organizations.models import Organization
from apps.projects.models import Project


class ReportType(models.TextChoices):
    DAILY = "DAILY", "Daily"
    WEEKLY = "WEEKLY", "Weekly"
    MONTHLY = "MONTHLY", "Monthly"
    EXECUTIVE = "EXECUTIVE", "Executive"
    PROJECT = "PROJECT", "Project"
    TEAM = "TEAM", "Team"


class ReportStatus(models.TextChoices):
    GENERATING = "GENERATING", "Generating"
    READY = "READY", "Ready"
    FAILED = "FAILED", "Failed"


class Report(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="reports")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="reports", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_reports")
    report_type = models.CharField(max_length=20, choices=ReportType.choices, default=ReportType.DAILY)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.GENERATING)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    content = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    file = models.FileField(upload_to="reports/%Y/%m/%d/", blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["project", "report_type"]),
            models.Index(fields=["created_by", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

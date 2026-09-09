from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.organizations.models import Organization


class NotificationType(models.TextChoices):
    TASK_ASSIGNED = "TASK_ASSIGNED", "Task Assigned"
    TASK_DUE = "TASK_DUE", "Task Due"
    TASK_OVERDUE = "TASK_OVERDUE", "Task Overdue"
    TASK_COMPLETED = "TASK_COMPLETED", "Task Completed"
    MENTION = "MENTION", "Mention"
    PROJECT_UPDATE = "PROJECT_UPDATE", "Project Update"
    RISK_ALERT = "RISK_ALERT", "Risk Alert"
    AI_RECOMMENDATION = "AI_RECOMMENDATION", "AI Recommendation"
    REPORT_READY = "REPORT_READY", "Report Ready"
    INVITATION = "INVITATION", "Invitation"
    SYSTEM = "SYSTEM", "System"


class Notification(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["organization", "is_read"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

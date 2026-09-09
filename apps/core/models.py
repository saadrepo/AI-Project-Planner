import uuid

from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActivityLog(BaseModel):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="activity_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.UUIDField(db_index=True, null=True, blank=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on {self.entity_type}"

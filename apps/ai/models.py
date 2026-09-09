from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.organizations.models import Organization
from apps.projects.models import Project


class ConversationContextType(models.TextChoices):
    PROJECT = "PROJECT", "Project"
    TASK = "TASK", "Task"
    ORGANIZATION = "ORGANIZATION", "Organization"
    GENERAL = "GENERAL", "General"


class AIConversation(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="ai_conversations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversations")
    title = models.CharField(max_length=255, blank=True)
    context_type = models.CharField(max_length=30, choices=ConversationContextType.choices, default=ConversationContextType.GENERAL)
    context_id = models.UUIDField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "user"]),
            models.Index(fields=["context_type", "context_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Conversation {self.id}"


class AIMessageRole(models.TextChoices):
    SYSTEM = "SYSTEM", "System"
    USER = "USER", "User"
    ASSISTANT = "ASSISTANT", "Assistant"
    TOOL = "TOOL", "Tool"


class AIMessage(BaseModel):
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=AIMessageRole.choices, default=AIMessageRole.USER)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["conversation", "created_at"])]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} message"


class AIRecommendationType(models.TextChoices):
    TASK_PRIORITY = "TASK_PRIORITY", "Task Priority"
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT", "Task Assignment"
    DEADLINE = "DEADLINE", "Deadline"
    RISK = "RISK", "Risk"
    WORKLOAD = "WORKLOAD", "Workload"
    PROJECT_PLAN = "PROJECT_PLAN", "Project Plan"
    PROJECT_HEALTH = "PROJECT_HEALTH", "Project Health"
    GENERAL = "GENERAL", "General"


class AIRecommendationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    EXECUTED = "EXECUTED", "Executed"
    EXPIRED = "EXPIRED", "Expired"


class AIRecommendation(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="ai_recommendations")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="ai_recommendations", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_ai_recommendations")
    recommendation_type = models.CharField(max_length=30, choices=AIRecommendationType.choices, default=AIRecommendationType.GENERAL)
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20, default="MEDIUM")
    status = models.CharField(max_length=20, choices=AIRecommendationStatus.choices, default=AIRecommendationStatus.PENDING)
    payload = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["created_by", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

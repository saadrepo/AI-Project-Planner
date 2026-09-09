import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.organizations.models import Organization


class ProjectStatus(models.TextChoices):
    PLANNING = "PLANNING", "Planning"
    ACTIVE = "ACTIVE", "Active"
    ON_HOLD = "ON_HOLD", "On Hold"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class ProjectPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class Project(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=ProjectStatus.choices, default=ProjectStatus.PLANNING)
    priority = models.CharField(max_length=20, choices=ProjectPriority.choices, default=ProjectPriority.MEDIUM)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_projects")
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    progress = models.IntegerField(default=0)
    health_score = models.IntegerField(default=0)
    is_archived = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "slug"], name="unique_project_slug_per_organization"),
            models.CheckConstraint(check=models.Q(progress__gte=0, progress__lte=100), name="project_progress_range"),
            models.CheckConstraint(check=models.Q(health_score__gte=0, health_score__lte=100), name="project_health_score_range"),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "due_date"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["status", "priority"]),
        ]
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValidationError({"start_date": "Start date cannot be after due date."})
        if not 0 <= self.progress <= 100:
            raise ValidationError({"progress": "Progress must be between 0 and 100."})
        if not 0 <= self.health_score <= 100:
            raise ValidationError({"health_score": "Health score must be between 0 and 100."})

    def __str__(self):
        return self.name


class ProjectMemberRole(models.TextChoices):
    MANAGER = "MANAGER", "Manager"
    MEMBER = "MEMBER", "Member"
    VIEWER = "VIEWER", "Viewer"


class ProjectMember(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=ProjectMemberRole.choices, default=ProjectMemberRole.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_project_member"),
        ]
        indexes = [
            models.Index(fields=["project", "user"]),
            models.Index(fields=["user", "role"]),
        ]
        ordering = ["project__name", "user__email"]

    def __str__(self):
        return f"{self.user.email} on {self.project.name}"


class MilestoneStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planned"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class Milestone(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=MilestoneStatus.choices, default=MilestoneStatus.PLANNED)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress = models.IntegerField(default=0)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_milestones")

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(progress__gte=0, progress__lte=100), name="milestone_progress_range"),
        ]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "due_date"]),
            models.Index(fields=["owner", "status"]),
        ]
        ordering = ["due_date", "-created_at"]

    def clean(self):
        super().clean()
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValidationError({"start_date": "Start date cannot be after due date."})
        if not 0 <= self.progress <= 100:
            raise ValidationError({"progress": "Progress must be between 0 and 100."})

    def __str__(self):
        return self.name


class ProjectUpdateStatus(models.TextChoices):
    INFO = "INFO", "Info"
    PROGRESS = "PROGRESS", "Progress"
    BLOCKER = "BLOCKER", "Blocker"
    MILESTONE = "MILESTONE", "Milestone"


class ProjectUpdate(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="updates")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_updates")
    title = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=ProjectUpdateStatus.choices, default=ProjectUpdateStatus.INFO)

    class Meta:
        indexes = [models.Index(fields=["project", "created_at"]), models.Index(fields=["author", "created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class RiskSeverity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class RiskProbability(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class RiskStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    MONITORING = "MONITORING", "Monitoring"
    MITIGATED = "MITIGATED", "Mitigated"
    RESOLVED = "RESOLVED", "Resolved"
    ACCEPTED = "ACCEPTED", "Accepted"


class Risk(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="risks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=RiskSeverity.choices, default=RiskSeverity.MEDIUM)
    probability = models.CharField(max_length=20, choices=RiskProbability.choices, default=RiskProbability.MEDIUM)
    status = models.CharField(max_length=20, choices=RiskStatus.choices, default=RiskStatus.OPEN)
    impact = models.TextField(blank=True)
    mitigation = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_risks")
    detected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="detected_risks")
    due_date = models.DateField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "severity"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["due_date", "status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

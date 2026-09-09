import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.projects.models import Project, Milestone


class TaskStatus(models.TextChoices):
    BACKLOG = "BACKLOG", "Backlog"
    TODO = "TODO", "To Do"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    IN_REVIEW = "IN_REVIEW", "In Review"
    BLOCKED = "BLOCKED", "Blocked"
    DONE = "DONE", "Done"
    CANCELLED = "CANCELLED", "Cancelled"


class TaskPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class TaskType(models.TextChoices):
    TASK = "TASK", "Task"
    BUG = "BUG", "Bug"
    FEATURE = "FEATURE", "Feature"
    IMPROVEMENT = "IMPROVEMENT", "Improvement"
    RESEARCH = "RESEARCH", "Research"
    MEETING = "MEETING", "Meeting"


class Task(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    milestone = models.ForeignKey(Milestone, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.TODO)
    priority = models.CharField(max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    task_type = models.CharField(max_length=30, choices=TaskType.choices, default=TaskType.TASK)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_tasks")
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, null=True, blank=True)
    progress = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "due_date"]),
            models.Index(fields=["assignee", "status"]),
            models.Index(fields=["created_by", "created_at"]),
            models.Index(fields=["milestone", "status"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(progress__gte=0, progress__lte=100), name="task_progress_range"),
            models.CheckConstraint(check=models.Q(estimated_hours__gte=0) | models.Q(estimated_hours__isnull=True), name="task_estimated_hours_non_negative"),
            models.CheckConstraint(check=models.Q(actual_hours__gte=0) | models.Q(actual_hours__isnull=True), name="task_actual_hours_non_negative"),
        ]
        ordering = ["-due_date", "-created_at"]

    def clean(self):
        super().clean()
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValidationError({"start_date": "Start date cannot be after due date."})
        if self.estimated_hours is not None and self.estimated_hours < 0:
            raise ValidationError({"estimated_hours": "Estimated hours cannot be negative."})
        if self.actual_hours is not None and self.actual_hours < 0:
            raise ValidationError({"actual_hours": "Actual hours cannot be negative."})
        if not 0 <= self.progress <= 100:
            raise ValidationError({"progress": "Progress must be between 0 and 100."})
        if self.parent and self.parent == self:
            raise ValidationError({"parent": "Task cannot be its own parent."})
        if self.milestone and self.milestone.project_id != self.project_id:
            raise ValidationError({"milestone": "Milestone must belong to the same project as the task."})
        if self.parent and self.parent.project_id != self.project_id:
            raise ValidationError({"parent": "Parent task must belong to the same project."})

    def __str__(self):
        return self.title


class TaskDependencyType(models.TextChoices):
    BLOCKS = "BLOCKS", "Blocks"
    BLOCKED_BY = "BLOCKED_BY", "Blocked By"


class TaskDependency(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="dependencies")
    depends_on = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="dependents")
    dependency_type = models.CharField(max_length=20, choices=TaskDependencyType.choices, default=TaskDependencyType.BLOCKS)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "depends_on"], name="unique_task_dependency"),
            models.CheckConstraint(check=~models.Q(task=models.F("depends_on")), name="task_dependency_not_self"),
        ]
        indexes = [
            models.Index(fields=["task", "depends_on"]),
            models.Index(fields=["depends_on", "dependency_type"]),
        ]
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.task_id == self.depends_on_id:
            raise ValidationError({"depends_on": "A task cannot depend on itself."})
        if self.task.project_id != self.depends_on.project_id:
            raise ValidationError({"depends_on": "Tasks in a dependency must belong to the same project."})

    def __str__(self):
        return f"{self.task.title} -> {self.depends_on.title}"


class TaskComment(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_comments")
    content = models.TextField()

    class Meta:
        indexes = [models.Index(fields=["task", "created_at"]), models.Index(fields=["author", "created_at"])]
        ordering = ["created_at"]

    def clean(self):
        super().clean()
        if not self.content or not self.content.strip():
            raise ValidationError({"content": "Comment content cannot be empty."})

    def __str__(self):
        return f"Comment by {self.author.email} on {self.task.title}"


class TaskAttachment(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_task_attachments")
    file = models.FileField(upload_to="task_attachments/%Y/%m/%d/")
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=200, blank=True)

    class Meta:
        indexes = [models.Index(fields=["task", "created_at"]), models.Index(fields=["uploaded_by", "created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return self.file_name


class Tag(BaseModel):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=80)
    color = models.CharField(max_length=20, default="#6B7280")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_organization_tag_name"),
        ]
        indexes = [models.Index(fields=["organization", "name"])]
        ordering = ["organization__name", "name"]

    def __str__(self):
        return self.name


class TaskTag(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="task_tags")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="task_assignments")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "tag"], name="unique_task_tag"),
        ]
        indexes = [models.Index(fields=["task", "tag"])]
        ordering = ["task__title", "tag__name"]

    def __str__(self):
        return f"{self.task.title} – {self.tag.name}"


class TimeEntry(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="time_entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="time_entries")
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True, default=None)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["task", "user"]),
            models.Index(fields=["user", "started_at"]),
        ]
        ordering = ["-started_at"]

    def clean(self):
        super().clean()
        if self.duration_minutes is not None and self.duration_minutes < 0:
            raise ValidationError({"duration_minutes": "Duration cannot be negative."})
        if self.ended_at and self.started_at and self.ended_at < self.started_at:
            raise ValidationError({"ended_at": "End time cannot be before start time."})

    def __str__(self):
        return f"{self.user.email} on {self.task.title}"

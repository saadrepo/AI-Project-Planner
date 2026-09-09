from django.contrib import admin

from .models import Task, TaskAttachment, TaskComment, TaskDependency, Tag, TaskTag, TimeEntry


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "priority", "task_type", "assignee", "due_date", "progress")
    list_filter = ("project", "status", "priority", "task_type", "assignee")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = ("task", "depends_on", "dependency_type")
    list_filter = ("dependency_type",)


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "created_at")
    search_fields = ("content", "author__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ("task", "file_name", "uploaded_by", "created_at")
    search_fields = ("file_name", "task__title")
    readonly_fields = ("created_at",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("organization", "name", "color")
    list_filter = ("organization",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(TaskTag)
class TaskTagAdmin(admin.ModelAdmin):
    list_display = ("task", "tag")
    list_filter = ("tag",)


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "started_at", "ended_at", "duration_minutes")
    list_filter = ("user", "task")
    search_fields = ("description", "task__title")
    readonly_fields = ("created_at", "updated_at")

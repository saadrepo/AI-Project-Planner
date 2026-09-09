from django.contrib import admin

from .models import Milestone, Project, ProjectMember


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "status", "priority", "owner", "due_date", "progress", "health_score")
    list_filter = ("organization", "status", "priority", "is_archived")
    search_fields = ("name", "slug", "owner__email")
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "joined_at")
    list_filter = ("role", "project")
    search_fields = ("project__name", "user__email")
    readonly_fields = ("joined_at", "created_at", "updated_at")


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "status", "due_date", "progress", "owner")
    list_filter = ("status", "project")
    search_fields = ("name", "project__name")
    readonly_fields = ("created_at", "updated_at")

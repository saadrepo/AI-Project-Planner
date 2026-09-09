from django.contrib import admin

from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("organization", "action", "entity_type", "user", "created_at")
    list_filter = ("action", "entity_type", "organization")
    search_fields = ("organization__name", "user__email", "description")
    readonly_fields = ("organization", "user", "action", "entity_type", "entity_id", "description", "metadata", "created_at", "updated_at")

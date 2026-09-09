from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "organization")
    search_fields = ("title", "message", "user__email")
    readonly_fields = ("created_at", "updated_at")

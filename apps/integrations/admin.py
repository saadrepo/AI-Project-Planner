from django.contrib import admin

from .models import Integration


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "provider", "status", "connected_by", "last_synced_at")
    list_filter = ("organization", "provider", "status")
    search_fields = ("name", "provider")
    readonly_fields = ("created_at", "updated_at")

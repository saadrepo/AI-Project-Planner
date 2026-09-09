from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "project", "report_type", "status", "created_by", "created_at")
    list_filter = ("organization", "project", "report_type", "status")
    search_fields = ("title", "organization__name")
    readonly_fields = ("created_at", "updated_at")

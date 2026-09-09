from django.contrib import admin

from .models import Team, TeamMember


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "lead", "created_at")
    list_filter = ("organization",)
    search_fields = ("name", "description", "lead__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "role")
    list_filter = ("team", "role")
    search_fields = ("user__email", "team__name")
    readonly_fields = ("created_at", "updated_at")

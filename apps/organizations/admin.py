from django.contrib import admin

from .models import Organization, OrganizationInvitation, OrganizationMember


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "is_active", "created_at")
    list_filter = ("is_active", "owner")
    search_fields = ("name", "slug", "owner__email")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "is_active", "joined_at")
    list_filter = ("role", "is_active", "organization")
    search_fields = ("organization__name", "user__email")
    readonly_fields = ("joined_at", "created_at", "updated_at")


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = ("organization", "email", "role", "status", "expires_at", "accepted_at", "revoked_at")
    list_filter = ("role", "status", "organization")
    search_fields = ("email", "organization__name")
    readonly_fields = ("token", "created_at", "updated_at")

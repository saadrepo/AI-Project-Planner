from django.contrib import admin

from .models import AIConversation, AIMessage, AIRecommendation


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "user", "context_type", "created_at")
    list_filter = ("organization", "context_type")
    search_fields = ("title", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "created_at")
    list_filter = ("role",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "project", "recommendation_type", "status", "priority", "created_at")
    list_filter = ("organization", "status", "recommendation_type")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")

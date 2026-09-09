from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "plan", "status", "provider", "current_period_end")
    list_filter = ("plan", "status", "provider")
    search_fields = ("organization__name", "external_customer_id", "external_subscription_id")
    readonly_fields = ("created_at", "updated_at")

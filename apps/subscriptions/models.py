from django.db import models

from apps.core.models import BaseModel
from apps.organizations.models import Organization


class SubscriptionPlan(models.TextChoices):
    FREE = "FREE", "Free"
    PRO = "PRO", "Pro"
    BUSINESS = "BUSINESS", "Business"


class SubscriptionStatus(models.TextChoices):
    TRIALING = "TRIALING", "Trialing"
    ACTIVE = "ACTIVE", "Active"
    PAST_DUE = "PAST_DUE", "Past Due"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class Subscription(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.CharField(max_length=20, choices=SubscriptionPlan.choices, default=SubscriptionPlan.FREE)
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE)
    provider = models.CharField(max_length=100, blank=True)
    external_customer_id = models.CharField(max_length=255, blank=True)
    external_subscription_id = models.CharField(max_length=255, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["organization", "status"]), models.Index(fields=["provider", "status"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization.name} - {self.plan}"

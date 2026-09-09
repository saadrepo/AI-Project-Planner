from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.subscriptions.models import Subscription, SubscriptionPlan, SubscriptionStatus


class SubscriptionModelTests(TestCase):
    def test_subscription_creation(self):
        user = User.objects.create_user(email="subowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Sub Org", slug="sub-org", owner=user)
        subscription = Subscription.objects.create(
            organization=org,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
            provider="stripe",
        )
        self.assertEqual(subscription.organization, org)
        self.assertEqual(subscription.plan, SubscriptionPlan.PRO)

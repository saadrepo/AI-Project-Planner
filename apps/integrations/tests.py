from django.test import TestCase

from apps.accounts.models import User
from apps.integrations.models import Integration, IntegrationProvider, IntegrationStatus
from apps.organizations.models import Organization


class IntegrationModelTests(TestCase):
    def test_integration_creation(self):
        user = User.objects.create_user(email="integrateuser@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Integration Org", slug="integration-org", owner=user)
        integration = Integration.objects.create(
            organization=org,
            provider=IntegrationProvider.SLACK,
            name="Ops Slack",
            status=IntegrationStatus.CONNECTED,
            connected_by=user,
        )
        self.assertEqual(integration.organization, org)
        self.assertEqual(integration.provider, IntegrationProvider.SLACK)

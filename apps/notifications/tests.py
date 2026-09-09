from django.test import TestCase

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationType
from apps.organizations.models import Organization


class NotificationModelTests(TestCase):
    def test_notification_read_state(self):
        user = User.objects.create_user(email="noteuser@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Notify Org", slug="notify-org", owner=user)
        notification = Notification.objects.create(
            user=user,
            organization=org,
            notification_type=NotificationType.TASK_ASSIGNED,
            title="Assigned task",
            message="You have a new task.",
        )
        self.assertFalse(notification.is_read)
        notification.is_read = True
        notification.save()
        self.assertTrue(notification.is_read)

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.ai.models import AIRecommendation, AIRecommendationStatus
from apps.notifications.models import Notification, NotificationType
from apps.organizations.models import Organization, OrganizationMember, OrganizationMemberRole
from apps.projects.models import Project, ProjectPriority, ProjectStatus
from apps.tasks.models import Task, TaskDependency, TaskPriority, TaskStatus, TaskType, TimeEntry


class CoreTests(TestCase):
    def test_health_endpoint(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_database_connection(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.assertEqual(cursor.fetchone(), (1,))

    def test_organization_project_relationships(self):
        org_a = Organization.objects.create(name="Org A", slug="org-a", owner=self._create_user("owner-a@example.com"))
        org_b = Organization.objects.create(name="Org B", slug="org-b", owner=self._create_user("owner-b@example.com"))
        project_a = Project.objects.create(
            organization=org_a,
            name="Project A",
            slug="project-a",
            owner=org_a.owner,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.HIGH,
        )
        project_b = Project.objects.create(
            organization=org_b,
            name="Project B",
            slug="project-b",
            owner=org_b.owner,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.HIGH,
        )

        self.assertEqual(project_a.organization, org_a)
        self.assertEqual(project_b.organization, org_b)
        self.assertNotEqual(project_a.organization_id, project_b.organization_id)

    def test_project_progress_constraint(self):
        org = Organization.objects.create(name="Org", slug="org", owner=self._create_user("owner@example.com"))
        project = Project(
            organization=org,
            name="Valid",
            slug="valid",
            owner=org.owner,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
            progress=101,
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            project.full_clean()

    def test_task_negative_hours_rejected(self):
        org = Organization.objects.create(name="Org", slug="org-task", owner=self._create_user("owner-task@example.com"))
        project = Project.objects.create(
            organization=org,
            name="Task Project",
            slug="task-project",
            owner=org.owner,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        task = Task(
            project=project,
            title="Bad hours",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            task_type=TaskType.TASK,
            created_by=org.owner,
            estimated_hours=-1,
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            task.full_clean()

    def test_task_self_dependency_rejected(self):
        org = Organization.objects.create(name="Org", slug="org-dep", owner=self._create_user("owner-dep@example.com"))
        project = Project.objects.create(
            organization=org,
            name="Dependency Project",
            slug="dependency-project",
            owner=org.owner,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        task = Task.objects.create(
            project=project,
            title="Parent task",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.TASK,
            created_by=org.owner,
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            TaskDependency.objects.create(task=task, depends_on=task, dependency_type="BLOCKS")

    def test_notification_read_state(self):
        user = self._create_user("notify@example.com")
        notification = Notification.objects.create(
            user=user,
            organization=Organization.objects.create(name="Notify Org", slug="notify-org", owner=user),
            notification_type=NotificationType.TASK_ASSIGNED,
            title="Assigned",
            message="You were assigned a task.",
        )
        self.assertFalse(notification.is_read)
        notification.is_read = True
        notification.save()
        self.assertTrue(notification.is_read)

    def test_ai_recommendation_status(self):
        user = self._create_user("ai@example.com")
        org = Organization.objects.create(name="AI Org", slug="ai-org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="AI Project",
            slug="ai-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        rec = AIRecommendation.objects.create(
            organization=org,
            project=project,
            created_by=user,
            recommendation_type="TASK_PRIORITY",
            title="Reprioritize",
            description="Rebalance tasks",
            priority="HIGH",
            status=AIRecommendationStatus.PENDING,
        )
        self.assertEqual(rec.status, AIRecommendationStatus.PENDING)

    @staticmethod
    def _create_user(email):
        return User.objects.create_user(email=email, password="StrongPass123!")

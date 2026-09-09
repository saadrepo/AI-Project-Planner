from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.projects.models import Milestone, Project, ProjectPriority, ProjectStatus
from apps.tasks.models import Task, TaskDependency, TaskPriority as TaskPriorityEnum, TaskStatus, TaskType


class ProjectModelTests(TestCase):
    def test_project_creation(self):
        user = User.objects.create_user(email="projectowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Org", slug="org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="Sample Project",
            slug="sample-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.HIGH,
        )
        self.assertEqual(project.organization, org)
        self.assertEqual(project.owner, user)

    def test_project_date_validation(self):
        user = User.objects.create_user(email="dateowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Date Org", slug="date-org", owner=user)
        project = Project(
            organization=org,
            name="Bad Dates",
            slug="bad-dates",
            owner=user,
            status=ProjectStatus.PLANNING,
            priority=ProjectPriority.MEDIUM,
            start_date="2026-05-10",
            due_date="2026-05-01",
        )
        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_milestone_creation_and_validation(self):
        user = User.objects.create_user(email="mileowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Milestone Org", slug="milestone-org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="Milestone Project",
            slug="milestone-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        milestone = Milestone(
            project=project,
            name="Alpha",
            start_date="2026-05-01",
            due_date="2026-04-30",
            progress=10,
            owner=user,
        )
        with self.assertRaises(ValidationError):
            milestone.full_clean()

    def test_task_self_dependency_rejected(self):
        user = User.objects.create_user(email="depowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Dep Org", slug="dep-org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="Dep Project",
            slug="dep-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        task = Task.objects.create(
            project=project,
            title="Task",
            status=TaskStatus.TODO,
            priority=TaskPriorityEnum.MEDIUM,
            task_type=TaskType.TASK,
            created_by=user,
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            TaskDependency.objects.create(task=task, depends_on=task, dependency_type="BLOCKS")

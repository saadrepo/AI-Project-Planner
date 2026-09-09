from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.projects.models import Project, ProjectPriority, ProjectStatus
from apps.tasks.models import Tag, Task, TaskDependency, TaskPriority, TaskStatus, TaskTag, TaskType, TimeEntry


class TaskModelTests(TestCase):
    def test_task_creation(self):
        user = User.objects.create_user(email="taskowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Task Org", slug="task-org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="Task Project",
            slug="task-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        task = Task.objects.create(
            project=project,
            title="Build form",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            task_type=TaskType.TASK,
            created_by=user,
        )
        self.assertEqual(task.project, project)
        self.assertEqual(task.created_by, user)

    def test_negative_hours_rejected(self):
        user = User.objects.create_user(email="negowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Neg Org", slug="neg-org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="Neg Project",
            slug="neg-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        task = Task(
            project=project,
            title="Invalid hours",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.TASK,
            created_by=user,
            estimated_hours=-1,
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_tag_uniqueness(self):
        user = User.objects.create_user(email="tagowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Tag Org", slug="tag-org", owner=user)
        tag = Tag.objects.create(organization=org, name="urgent", color="#FF0000")
        self.assertEqual(tag.name, "urgent")
        with self.assertRaises((IntegrityError, ValidationError)):
            Tag.objects.create(organization=org, name="urgent", color="#00FF00")

    def test_time_entry_validation(self):
        user = User.objects.create_user(email="timeowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Time Org", slug="time-org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="Time Project",
            slug="time-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        task = Task.objects.create(
            project=project,
            title="Track time",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.TASK,
            created_by=user,
        )
        entry = TimeEntry(
            task=task,
            user=user,
            started_at="2026-06-01T09:00:00Z",
            ended_at="2026-06-01T08:00:00Z",
            duration_minutes=30,
        )
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_task_dependency_rejected(self):
        user = User.objects.create_user(email="taskdepowner@example.com", password="StrongPass123!")
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
            title="A",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            task_type=TaskType.TASK,
            created_by=user,
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            TaskDependency.objects.create(task=task, depends_on=task, dependency_type="BLOCKS")

    def test_task_tag_uniqueness(self):
        user = User.objects.create_user(email="ttagowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Task Tag Org", slug="task-tag-org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="Task Tag Project",
            slug="task-tag-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        task = Task.objects.create(
            project=project,
            title="B",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.TASK,
            created_by=user,
        )
        tag = Tag.objects.create(organization=org, name="release", color="#00FF00")
        TaskTag.objects.create(task=task, tag=tag)
        with self.assertRaises((IntegrityError, ValidationError)):
            TaskTag.objects.create(task=task, tag=tag)

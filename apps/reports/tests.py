from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.projects.models import Project, ProjectPriority, ProjectStatus
from apps.reports.models import Report, ReportStatus, ReportType


class ReportModelTests(TestCase):
    def test_report_creation(self):
        user = User.objects.create_user(email="reportowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Report Org", slug="report-org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="Report Project",
            slug="report-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.MEDIUM,
        )
        report = Report.objects.create(
            organization=org,
            project=project,
            created_by=user,
            report_type=ReportType.WEEKLY,
            title="Weekly Summary",
            status=ReportStatus.READY,
        )
        self.assertEqual(report.organization, org)
        self.assertEqual(report.project, project)

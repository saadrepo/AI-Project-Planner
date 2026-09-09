from django.test import TestCase

from apps.accounts.models import User
from apps.ai.models import AIConversation, AIMessage, AIMessageRole, AIRecommendation, AIRecommendationStatus, AIRecommendationType, ConversationContextType
from apps.organizations.models import Organization
from apps.projects.models import Project, ProjectPriority, ProjectStatus


class AIModelTests(TestCase):
    def test_ai_conversation_and_message(self):
        user = User.objects.create_user(email="aiuser@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="AI Org", slug="ai-org", owner=user)
        conversation = AIConversation.objects.create(
            organization=org,
            user=user,
            title="Project planning",
            context_type=ConversationContextType.PROJECT,
            context_id="123e4567-e89b-12d3-a456-426614174000",
        )
        AIMessage.objects.create(conversation=conversation, role=AIMessageRole.USER, content="Can we plan this project?")
        self.assertEqual(conversation.messages.count(), 1)

    def test_ai_recommendation_creation(self):
        user = User.objects.create_user(email="airec@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="AI Rec Org", slug="ai-rec-org", owner=user)
        project = Project.objects.create(
            organization=org,
            name="AI Rec Project",
            slug="ai-rec-project",
            owner=user,
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.HIGH,
        )
        rec = AIRecommendation.objects.create(
            organization=org,
            project=project,
            created_by=user,
            recommendation_type=AIRecommendationType.TASK_PRIORITY,
            title="Prioritize tasks",
            description="Do this first",
            priority="HIGH",
            status=AIRecommendationStatus.PENDING,
        )
        self.assertEqual(rec.project, project)
        self.assertEqual(rec.status, AIRecommendationStatus.PENDING)

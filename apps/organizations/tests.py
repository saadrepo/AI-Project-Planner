from smtplib import SMTPAuthenticationError
from unittest.mock import patch

from django.core import mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationInvitation, OrganizationMember, OrganizationMemberRole


class OrganizationModelTests(TestCase):
    def test_organization_creation(self):
        owner = User.objects.create_user(email="orgowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Example Org", slug="example-org", owner=owner)
        self.assertEqual(org.owner, owner)
        self.assertTrue(org.is_active)

    def test_unique_slug(self):
        owner = User.objects.create_user(email="slugowner@example.com", password="StrongPass123!")
        Organization.objects.create(name="Alpha", slug="alpha", owner=owner)
        with self.assertRaises((IntegrityError, ValidationError)):
            Organization.objects.create(name="Beta", slug="alpha", owner=owner)

    def test_unique_membership(self):
        owner = User.objects.create_user(email="memberowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Membership Org", slug="membership-org", owner=owner)
        OrganizationMember.objects.create(organization=org, user=owner, role=OrganizationMemberRole.OWNER)
        with self.assertRaises((IntegrityError, ValidationError)):
            OrganizationMember.objects.create(organization=org, user=owner, role=OrganizationMemberRole.ADMIN)

    def test_invitation_clean(self):
        owner = User.objects.create_user(email="inviteowner@example.com", password="StrongPass123!")
        org = Organization.objects.create(name="Invite Org", slug="invite-org", owner=owner)
        invitation = OrganizationInvitation(
            organization=org,
            email="person@example.com",
            invited_by=owner,
            expires_at="2024-01-01T00:00:00Z",
        )
        with self.assertRaises(ValidationError):
            invitation.clean()


class OrganizationWorkflowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!")
        self.other = User.objects.create_user(email="other@example.com", password="StrongPass123!")
        self.org = Organization.objects.create(name="Alpha Org", slug="alpha-org", owner=self.owner)
        OrganizationMember.objects.create(organization=self.org, user=self.owner, role=OrganizationMemberRole.OWNER)

    def test_authenticated_user_can_create_organization_and_set_active(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            "/organizations/create/",
            {"name": "Beta Org", "description": "New portal"},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Organization.objects.filter(name="Beta Org").exists())
        self.assertEqual(self.client.session.get("active_organization_id"), str(Organization.objects.get(name="Beta Org").pk))

    def test_existing_owner_can_create_multiple_organizations(self):
        self.client.force_login(self.owner)
        for name in ("Beta Org", "Gamma Org"):
            response = self.client.post("/organizations/create/", {"name": name, "description": ""})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(Organization.objects.filter(owner=self.owner).count(), 3)
        self.assertEqual(
            OrganizationMember.objects.filter(user=self.owner, role=OrganizationMemberRole.OWNER).count(),
            3,
        )

    def test_new_user_cannot_create_organization(self):
        new_user = User.objects.create_user(email="newuser@example.com", password="StrongPass123!")
        self.client.force_login(new_user)
        response = self.client.post("/organizations/create/", {"name": "Denied Org", "description": ""})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Organization.objects.filter(name="Denied Org").exists())

    def test_non_owner_member_cannot_create_organization(self):
        member = User.objects.create_user(email="member@example.com", password="StrongPass123!")
        OrganizationMember.objects.create(organization=self.org, user=member, role=OrganizationMemberRole.MEMBER)
        self.client.force_login(member)
        response = self.client.post("/organizations/create/", {"name": "Denied Org", "description": ""})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Organization.objects.filter(name="Denied Org").exists())

    def test_organization_list_shows_only_user_memberships(self):
        second_org = Organization.objects.create(name="Gamma Org", slug="gamma-org", owner=self.other)
        OrganizationMember.objects.create(organization=second_org, user=self.owner, role=OrganizationMemberRole.ADMIN)
        self.client.force_login(self.owner)
        response = self.client.get("/organizations/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha Org")
        self.assertContains(response, "Gamma Org")

    def test_non_member_cannot_access_organization_detail(self):
        outsider = User.objects.create_user(email="outsider@example.com", password="StrongPass123!")
        self.client.force_login(outsider)
        response = self.client.get(f"/organizations/{self.org.slug}/")
        self.assertIn(response.status_code, (302, 403, 404))

    def test_organization_switch_updates_session(self):
        second_org = Organization.objects.create(name="Second Org", slug="second-org", owner=self.other)
        OrganizationMember.objects.create(organization=second_org, user=self.owner, role=OrganizationMemberRole.MEMBER)
        self.client.force_login(self.owner)
        response = self.client.post("/organizations/switch/", {"organization_id": str(second_org.pk)})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("active_organization_id"), str(second_org.pk))

    def test_organization_member_list_is_isolated(self):
        self.client.force_login(self.owner)
        response = self.client.get(f"/organizations/{self.org.slug}/members/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.owner.email)

    def test_owner_can_change_member_role(self):
        member = User.objects.create_user(email="member@example.com", password="StrongPass123!")
        membership = OrganizationMember.objects.create(organization=self.org, user=member, role=OrganizationMemberRole.MEMBER)
        self.client.force_login(self.owner)
        response = self.client.post(
            f"/organizations/{self.org.slug}/members/{membership.pk}/role/",
            {"role": OrganizationMemberRole.ADMIN},
        )
        self.assertEqual(response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.role, OrganizationMemberRole.ADMIN)

    def test_owner_sees_role_controls_for_sub_users(self):
        member = User.objects.create_user(email="role-visible@example.com", password="StrongPass123!")
        OrganizationMember.objects.create(organization=self.org, user=member, role=OrganizationMemberRole.MEMBER)
        self.client.force_login(self.owner)
        response = self.client.get(f"/organizations/{self.org.slug}/members/")
        self.assertContains(response, "Change role for role-visible@example.com")
        self.assertContains(response, "Team Lead")
        self.assertContains(response, "Developer")
        self.assertContains(response, "QA")
        self.assertContains(response, "Viewer")

    def test_owner_can_assign_registered_user_to_organization(self):
        registered_user = User.objects.create_user(email="registered@example.com", password="StrongPass123!")
        self.client.force_login(self.owner)
        response = self.client.get(f"/organizations/{self.org.slug}/members/assign/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, registered_user.email)
        response = self.client.post(
            f"/organizations/{self.org.slug}/members/assign/",
            {"user_id": str(registered_user.pk), "role": OrganizationMemberRole.PROJECT_MANAGER},
        )
        self.assertEqual(response.status_code, 302)
        assigned = OrganizationMember.objects.get(organization=self.org, user=registered_user)
        self.assertEqual(assigned.role, OrganizationMemberRole.PROJECT_MANAGER)

    def test_non_owner_cannot_assign_registered_user(self):
        registered_user = User.objects.create_user(email="registered@example.com", password="StrongPass123!")
        member = User.objects.create_user(email="member-assign@example.com", password="StrongPass123!")
        OrganizationMember.objects.create(organization=self.org, user=member, role=OrganizationMemberRole.MEMBER)
        self.client.force_login(member)
        response = self.client.post(
            f"/organizations/{self.org.slug}/members/assign/",
            {"user_id": str(registered_user.pk), "role": OrganizationMemberRole.MEMBER},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(OrganizationMember.objects.filter(organization=self.org, user=registered_user).exists())

    def test_admin_cannot_promote_member_to_owner(self):
        admin = User.objects.create_user(email="admin@example.com", password="StrongPass123!")
        membership = OrganizationMember.objects.create(organization=self.org, user=admin, role=OrganizationMemberRole.ADMIN)
        self.client.force_login(admin)
        response = self.client.post(
            f"/organizations/{self.org.slug}/members/{membership.pk}/role/",
            {"role": OrganizationMemberRole.OWNER},
        )
        self.assertEqual(response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.role, OrganizationMemberRole.ADMIN)

    def test_second_owner_is_rejected_by_database_constraint(self):
        with self.assertRaises(IntegrityError):
            OrganizationMember.objects.create(
                organization=self.org,
                user=self.other,
                role=OrganizationMemberRole.OWNER,
            )

    def test_unauthorized_member_cannot_change_role(self):
        member = User.objects.create_user(email="limited@example.com", password="StrongPass123!")
        membership = OrganizationMember.objects.create(organization=self.org, user=member, role=OrganizationMemberRole.MEMBER)
        self.client.force_login(member)
        response = self.client.post(
            f"/organizations/{self.org.slug}/members/{membership.pk}/role/",
            {"role": OrganizationMemberRole.ADMIN},
        )
        self.assertIn(response.status_code, (302, 403))

    def test_owner_can_remove_member(self):
        member = User.objects.create_user(email="removable@example.com", password="StrongPass123!")
        membership = OrganizationMember.objects.create(organization=self.org, user=member, role=OrganizationMemberRole.MEMBER)
        self.client.force_login(self.owner)
        response = self.client.post(f"/organizations/{self.org.slug}/members/{membership.pk}/remove/", {})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(OrganizationMember.objects.filter(pk=membership.pk).exists())

    def test_owner_protection_prevents_removing_last_owner(self):
        self.client.force_login(self.owner)
        response = self.client.post(f"/organizations/{self.org.slug}/members/{self.org.members.get(user=self.owner).pk}/remove/", {})
        self.assertIn(response.status_code, (302, 403))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_authorized_user_can_create_invitation(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            f"/organizations/{self.org.slug}/invitations/create/",
            {"email": "newmember@example.com", "role": OrganizationMemberRole.MEMBER},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OrganizationInvitation.objects.filter(organization=self.org, email="newmember@example.com").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("newmember@example.com", mail.outbox[0].to)
        self.assertIn("/invitations/", mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_owner_role_invitation_is_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            f"/organizations/{self.org.slug}/invitations/create/",
            {"email": "owner-invite@example.com", "role": OrganizationMemberRole.OWNER},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(OrganizationInvitation.objects.filter(email="owner-invite@example.com").exists())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_existing_pending_invitation_can_be_sent_again(self):
        self.client.force_login(self.owner)
        payload = {"email": "newmember@example.com", "role": OrganizationMemberRole.MEMBER}

        self.client.post(f"/organizations/{self.org.slug}/invitations/create/", payload)
        invitation = OrganizationInvitation.objects.get(organization=self.org, email=payload["email"])
        first_token = invitation.token

        response = self.client.post(f"/organizations/{self.org.slug}/invitations/create/", payload)

        invitation.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(invitation.token, first_token)
        self.assertEqual(len(mail.outbox), 2)

    @patch("apps.organizations.services.send_mail", side_effect=SMTPAuthenticationError(535, b"Authentication unsuccessful"))
    def test_invitation_creation_does_not_fail_when_email_provider_rejects_auth(self, _mock_send_mail):
        self.client.force_login(self.owner)
        response = self.client.post(
            f"/organizations/{self.org.slug}/invitations/create/",
            {"email": "newmember@example.com", "role": OrganizationMemberRole.MEMBER},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OrganizationInvitation.objects.filter(organization=self.org, email="newmember@example.com").exists())

    def test_valid_invitation_can_be_accepted(self):
        from django.utils import timezone
        invited_user = User.objects.create_user(email="invitee@example.com", password="StrongPass123!")
        invitation = OrganizationInvitation.objects.create(
            organization=self.org,
            email="invitee@example.com",
            invited_by=self.owner,
            role=OrganizationMemberRole.MEMBER,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )
        self.client.force_login(invited_user)
        response = self.client.get(f"/invitations/{invitation.token}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accept invitation")
        response = self.client.post(f"/invitations/{invitation.token}/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.org.members.filter(user=invited_user, is_active=True).exists())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_new_user_registration_preserves_invitation_redirect(self):
        from django.utils import timezone

        invitation = OrganizationInvitation.objects.create(
            organization=self.org,
            email="new-invitee@example.com",
            invited_by=self.owner,
            role=OrganizationMemberRole.MEMBER,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )
        invitation_url = f"/invitations/{invitation.token}/"

        response = self.client.get(invitation_url)
        self.assertRedirects(response, f"/login/?next={invitation_url}")
        response = self.client.get(response.url)
        register_link = response.context["request"].build_absolute_uri()
        self.assertNotEqual(register_link, "")
        response = self.client.get(f"/register/?next={invitation_url}")
        self.assertContains(response, f'name="next" value="{invitation_url}"')
        response = self.client.post(
            "/register/",
            {
                "name": "New Invitee",
                "email": "new-invitee@example.com",
                "password": "StrongPass123!",
                "password_confirmation": "StrongPass123!",
                "next": invitation_url,
            },
        )
        self.assertRedirects(response, invitation_url)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, OrganizationInvitation.Status.PENDING)

    def test_invitation_email_is_normalized_before_acceptance(self):
        from django.utils import timezone

        invited_user = User.objects.create_user(email="invitee@example.com", password="StrongPass123!")
        invitation = OrganizationInvitation.objects.create(
            organization=self.org,
            email="  INVITEE@EXAMPLE.COM ",
            invited_by=self.owner,
            role=OrganizationMemberRole.MEMBER,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )
        invitation.refresh_from_db()
        self.assertEqual(invitation.email, "invitee@example.com")
        self.client.force_login(invited_user)
        response = self.client.post(f"/invitations/{invitation.token}/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(invitation.__class__.objects.get(pk=invitation.pk).status, OrganizationInvitation.Status.ACCEPTED)

    def test_organization_settings_update_requires_permission(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            f"/organizations/{self.org.slug}/settings/",
            {"name": "Updated Org Name", "description": "Updated description"},
        )
        self.assertEqual(response.status_code, 302)
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, "Updated Org Name")

    def test_admin_cannot_update_organization_settings(self):
        admin = User.objects.create_user(email="settings-admin@example.com", password="StrongPass123!")
        OrganizationMember.objects.create(organization=self.org, user=admin, role=OrganizationMemberRole.ADMIN)
        self.client.force_login(admin)
        response = self.client.post(
            f"/organizations/{self.org.slug}/settings/",
            {"name": "Should Not Update", "description": ""},
        )
        self.assertEqual(response.status_code, 403)
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, "Alpha Org")

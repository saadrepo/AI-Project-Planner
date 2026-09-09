from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin import UserAdmin
from .models import User

UserModel = get_user_model()


class UserTests(TestCase):
    def test_user_can_be_created_with_email(self):
        user = User.objects.create_user("Test@Example.com", "strong-password")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("strong-password"))
        self.assertTrue(user.is_active)

    def test_admin_configuration(self):
        user_admin = UserAdmin(User, AdminSite())
        self.assertIn("email", user_admin.search_fields)
        self.assertIn("is_staff", user_admin.list_filter)
        self.assertIn("email", user_admin.list_display)

    def test_registration_creates_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "password": "StrongPass123!",
                "password_confirmation": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserModel.objects.filter(email="jane@example.com").exists())

    def test_duplicate_email_is_rejected(self):
        UserModel.objects.create_user(email="dup@example.com", password="StrongPass123!")
        response = self.client.post(
            reverse("register"),
            {
                "name": "Test User",
                "email": "Dup@Example.com",
                "password": "StrongPass123!",
                "password_confirmation": "StrongPass123!",
            },
        )
        self.assertContains(response, "already exists")

    def test_login_success(self):
        user = UserModel.objects.create_user(email="login@example.com", password="StrongPass123!")
        response = self.client.post(
            reverse("login"),
            {"email": "login@example.com", "password": "StrongPass123!", "remember_me": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))
        self.assertTrue(response.url.endswith("/organizations/"))

    def test_login_inactive_user_is_rejected(self):
        UserModel.objects.create_user(email="inactive@example.com", password="StrongPass123!", is_active=False)
        response = self.client.post(
            reverse("login"),
            {"email": "inactive@example.com", "password": "StrongPass123!"},
        )
        self.assertContains(response, "inactive")

    def test_logout_requires_post(self):
        user = UserModel.objects.create_user(email="logout@example.com", password="StrongPass123!")
        self.client.force_login(user)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)

    def test_password_change_success(self):
        user = UserModel.objects.create_user(email="change@example.com", password="StrongPass123!")
        self.client.force_login(user)
        response = self.client.post(
            reverse("change_password"),
            {
                "current_password": "StrongPass123!",
                "new_password": "NewPass456!",
                "new_password_confirmation": "NewPass456!",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass456!"))

    def test_password_change_bad_current_password(self):
        user = UserModel.objects.create_user(email="wrong@example.com", password="StrongPass123!")
        self.client.force_login(user)
        response = self.client.post(
            reverse("change_password"),
            {
                "current_password": "WRONGPASSWORD",
                "new_password": "NewPass456!",
                "new_password_confirmation": "NewPass456!",
            },
        )
        self.assertContains(response, "Current password is incorrect.")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_sends_email_and_allows_valid_reset(self):
        user = UserModel.objects.create_user(email="reset@example.com", password="StrongPass123!")
        response = self.client.post(reverse("password_reset"), {"email": "reset@example.com"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(len(mail.outbox) > 0)

        token = default_token_generator.make_token(user)
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_response = self.client.post(
            reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token}),
            {"new_password1": "ResetPass789!", "new_password2": "ResetPass789!"},
        )
        self.assertIn(reset_response.status_code, (200, 302))
        user.refresh_from_db()
        self.assertTrue(user.check_password("ResetPass789!"))

    def test_email_verification_token_sets_verified_status(self):
        user = UserModel.objects.create_user(email="verify@example.com", password="StrongPass123!")
        token = default_token_generator.make_token(user)
        uid = user.pk
        response = self.client.get(reverse("verify_email", kwargs={"uidb64": str(uid), "token": token}))
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertIsNotNone(user.email_verified_at)

    def test_account_page_requires_login(self):
        response = self.client.get(reverse("account"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/login/?next=/account/"))

    def test_profile_update_requires_authentication(self):
        response = self.client.post(
            reverse("settings"),
            {"name": "New Name", "email": "new@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_user_manager_requires_email(self):
        with self.assertRaises(ValueError):
            UserModel.objects.create_user(email="", password="StrongPass123!")

    def test_email_is_normalized(self):
        user = UserModel.objects.create_user(email="UPPER@EXAMPLE.COM", password="StrongPass123!")
        self.assertEqual(user.email, "upper@example.com")

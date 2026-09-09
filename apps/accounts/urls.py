from django.urls import path

from .views import (
    CustomPasswordResetCompleteView,
    CustomPasswordResetDoneView,
    account_view,
    change_password_view,
    home_view,
    login_view,
    logout_view,
    password_reset_confirm_view,
    password_reset_request_view,
    register_view,
    resend_verification_view,
    settings_view,
    verify_email_view,
)

urlpatterns = [
    path("", home_view, name="home"),
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("account/", account_view, name="account"),
    path("settings/", settings_view, name="settings"),
    path("settings/password/", change_password_view, name="change_password"),
    path("password-reset/", password_reset_request_view, name="password_reset"),
    path("password-reset/done/", CustomPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", password_reset_confirm_view, name="password_reset_confirm"),
    path("reset/done/", CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("verify-email/<uidb64>/<token>/", verify_email_view, name="verify_email"),
    path("verify-email/resend/", resend_verification_view, name="resend_verification"),
]

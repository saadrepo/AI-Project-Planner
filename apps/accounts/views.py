from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetCompleteView, PasswordResetDoneView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    CustomPasswordChangeForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    LoginForm,
    RegisterForm,
    UserSettingsForm,
)
from .models import User
from .services import (
    authenticate_user,
    change_password,
    is_rate_limited,
    login_user,
    logout_user,
    register_user,
    request_password_reset,
    resend_verification_email,
    reset_password,
    update_profile,
    verify_email,
)


@login_required
@user_passes_test(lambda user: user.is_active)
def account_view(request):
    return render(request, "accounts/account.html", {"user": request.user})


def register_view(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = None
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = register_user(
                        name=form.cleaned_data["name"],
                        email=form.cleaned_data["email"],
                        password=form.cleaned_data["password"],
                    )
                if user is not None:
                    login_user(request, user)
                messages.success(request, "Registration successful.")
                if next_url:
                    return redirect(next_url)
                return redirect("organization_list")
            except ValueError as exc:
                form.add_error(None, str(exc))
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form, "next_url": next_url})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate_user(email, password)
            if user is None:
                form.add_error(None, "Invalid email or password.")
            else:
                if not user.is_active:
                    form.add_error(None, "This account is inactive.")
                else:
                    login_user(request, user, remember_me=form.cleaned_data.get("remember_me", False))
                    next_url = request.POST.get("next") or request.GET.get("next")
                    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                        return redirect(next_url)
                    return redirect("organization_list")
    else:
        form = LoginForm()
        form.fields["email"].widget.attrs["autofocus"] = "autofocus"
    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout_user(request)
    return redirect("login")


@login_required
@user_passes_test(lambda user: user.is_active)
def settings_view(request):
    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            try:
                updated_user = update_profile(
                    user=request.user,
                    name=form.cleaned_data.get("name"),
                    email=form.cleaned_data.get("email"),
                    job_title=form.cleaned_data.get("job_title"),
                )
                if updated_user.email != request.user.email:
                    messages.success(request, "Profile updated. Please verify your new email address.")
                    return redirect("settings")
                messages.success(request, "Profile updated.")
                return redirect("settings")
            except ValueError as exc:
                form.add_error(None, str(exc))
    else:
        form = UserSettingsForm(instance=request.user)
    return render(request, "accounts/settings.html", {"form": form})


@login_required
@user_passes_test(lambda user: user.is_active)
def change_password_view(request):
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            try:
                change_password(
                    request.user,
                    form.cleaned_data["current_password"],
                    form.cleaned_data["new_password"],
                )
                messages.success(request, "Your password was updated successfully.")
                return redirect("account")
            except ValueError as exc:
                form.add_error("current_password", str(exc))
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, "accounts/change_password.html", {"form": form})


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


def password_reset_request_view(request):
    if request.method == "POST":
        client_ip = request.META.get("REMOTE_ADDR", "unknown")
        if is_rate_limited(f"password-reset:{client_ip}", limit=5, window_seconds=900):
            return redirect("password_reset_done")
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            request_password_reset(form.cleaned_data["email"])
            return redirect("password_reset_done")
    else:
        form = CustomPasswordResetForm()
    return render(request, "accounts/password_reset_form.html", {"form": form})


def password_reset_confirm_view(request, uidb64, token):
    try:
        user = User.objects.get(pk=uidb64)
    except (User.DoesNotExist, ValidationError):
        try:
            from django.utils.encoding import force_str
            from django.utils.http import urlsafe_base64_decode
            decoded = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=decoded)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
            return render(request, "accounts/password_reset_confirm.html", {"validlink": False, "form": CustomSetPasswordForm(None)})

    if not default_token_generator.check_token(user, token):
        return render(request, "accounts/password_reset_confirm.html", {"validlink": False, "form": CustomSetPasswordForm(None)})

    if request.method == "POST":
        form = CustomSetPasswordForm(user, request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data["new_password1"])
            user.save(update_fields=["password", "updated_at"])
            return redirect("password_reset_complete")
    else:
        form = CustomSetPasswordForm(user)

    return render(request, "accounts/password_reset_confirm.html", {"validlink": True, "form": form})


def verify_email_view(request, uidb64, token):
    try:
        verify_email(uidb64, token)
    except ValueError:
        return render(request, "accounts/verify_email.html", {"valid": False})
    messages.success(request, "Your email has been verified successfully.")
    if request.user.is_authenticated:
        return redirect("account")
    return redirect("login")


@login_required
@user_passes_test(lambda user: user.is_active)
def resend_verification_view(request):
    if request.method == "POST":
        resend_verification_email(request.user)
        messages.success(request, "A verification email has been sent to your inbox.")
        return redirect("account")
    return render(request, "accounts/resend_verification.html")


def home_view(request):
    if request.user.is_authenticated:
        return redirect("organization_list")
    return redirect("login")

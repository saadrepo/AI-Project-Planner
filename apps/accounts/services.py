from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

User = get_user_model()


def normalize_email(email):
    return (email or "").strip().lower()


def is_rate_limited(identifier, limit=5, window_seconds=900):
    key = f"auth-rate-limit:{identifier}"
    attempts = cache.get(key, 0)
    if attempts >= limit:
        return True
    cache.set(key, attempts + 1, window_seconds)
    return False


def clear_rate_limit(identifier):
    cache.delete(f"auth-rate-limit:{identifier}")


def register_user(name, email, password):
    normalized_email = normalize_email(email)
    if not normalized_email:
        raise ValueError("Email is required.")
    if User.objects.filter(email__iexact=normalized_email).exists():
        raise ValueError("A user with that email already exists.")
    user = User.objects.create_user(email=normalized_email, password=password, name=name)
    return user


def authenticate_user(email, password):
    normalized_email = normalize_email(email)
    if not normalized_email or not password:
        return None
    user = User.objects.filter(email__iexact=normalized_email).first()
    if user is None:
        return None
    if not user.check_password(password):
        return None
    if not user.is_active:
        return None
    return user


def login_user(request, user, remember_me=False):
    login(request, user)
    if remember_me:
        request.session.set_expiry(60 * 60 * 24 * 30)
    else:
        request.session.set_expiry(0)
    return user


def logout_user(request):
    logout(request)


def get_current_user(request):
    if getattr(request, "user", None) and request.user.is_authenticated:
        return request.user
    return None


def change_password(user, current_password, new_password):
    if not user.check_password(current_password):
        raise ValueError("Current password is incorrect.")
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    return user


def request_password_reset(email):
    normalized_email = normalize_email(email)
    user = User.objects.filter(email__iexact=normalized_email, is_active=True).first()
    if user is None:
        return None

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.BASE_URL}/reset/{uid}/{token}/" if getattr(settings, "BASE_URL", None) else None
    context = {"user": user, "uid": uid, "token": token, "reset_url": reset_url}
    subject = "Password reset for ProjectPilot AI"
    message = render_to_string("accounts/password_reset_email.txt", context)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    return user


def resolve_user_from_uid(uidb64):
    try:
        decoded = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=decoded)
    except (TypeError, ValueError, OverflowError):
        try:
            return User.objects.get(pk=uidb64)
        except User.DoesNotExist:
            raise ValueError("Invalid user link.")


def reset_password(uidb64, token, new_password):
    try:
        user = resolve_user_from_uid(uidb64)
    except ValueError as exc:
        raise ValueError("Invalid reset link.") from exc

    if not default_token_generator.check_token(user, token):
        raise ValueError("This reset link is invalid or has expired.")

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    return user


def verify_email(uidb64, token):
    try:
        user = resolve_user_from_uid(uidb64)
    except ValueError as exc:
        raise ValueError("Invalid verification link.") from exc

    if not default_token_generator.check_token(user, token):
        raise ValueError("This verification link is invalid or has expired.")

    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at", "updated_at"])
    return user


def resend_verification_email(user):
    if user is None:
        return None
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verification_url = f"{settings.BASE_URL}/verify-email/{uid}/{token}/" if getattr(settings, "BASE_URL", None) else None
    context = {"user": user, "uid": uid, "token": token, "verification_url": verification_url}
    subject = "Verify your ProjectPilot AI email"
    message = render_to_string("accounts/verification_email.txt", context)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    return user


def update_profile(user, name=None, email=None, job_title=None):
    if name is not None:
        user.name = name.strip()
    if email is not None:
        normalized_email = normalize_email(email)
        if User.objects.filter(email__iexact=normalized_email).exclude(pk=user.pk).exists():
            raise ValueError("A user with that email already exists.")
        if user.email.lower() != normalized_email:
            user.email_verified_at = None
        user.email = normalized_email
    if job_title is not None:
        user.job_title = job_title.strip()
    user.save(update_fields=["name", "email", "email_verified_at", "job_title", "updated_at"])
    return user

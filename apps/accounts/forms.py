from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm

from .models import User


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), strip=False)
    password_confirmation = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), strip=False)

    class Meta:
        model = User
        fields = ["name", "email", "password"]

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirmation = cleaned_data.get("password_confirmation")
        email = cleaned_data.get("email")

        if password and password_confirmation and password != password_confirmation:
            self.add_error("password_confirmation", "Passwords do not match.")

        if email and User.objects.filter(email__iexact=email).exists():
            self.add_error("email", "A user with that email already exists.")

        if password:
            password_validation.validate_password(password)

        return cleaned_data

    def save(self, commit=True):
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            name=self.cleaned_data["name"],
        )
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autocomplete": "username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}), strip=False)
    remember_me = forms.BooleanField(required=False)

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "email", "job_title"]

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        return email

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            self.add_error("email", "A user with that email already exists.")
        return cleaned_data


class CustomPasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}), strip=False)
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), strip=False)
    new_password_confirmation = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), strip=False)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data.get("current_password")
        if not self.user.check_password(password):
            raise forms.ValidationError("Current password is incorrect.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        new_password_confirmation = cleaned_data.get("new_password_confirmation")
        if new_password and new_password_confirmation and new_password != new_password_confirmation:
            self.add_error("new_password_confirmation", "Passwords do not match.")
        if new_password:
            password_validation.validate_password(new_password, self.user)
        return cleaned_data


class CustomPasswordResetForm(DjangoPasswordResetForm):
    def get_users(self, email):
        return User.objects.filter(email__iexact=email, is_active=True)


class CustomSetPasswordForm(DjangoSetPasswordForm):
    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        if password:
            password_validation.validate_password(password, self.user)
        return password

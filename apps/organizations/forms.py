from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify

from .models import Organization, OrganizationInvitation, OrganizationMember, OrganizationMemberRole

ALLOWED_MEMBER_ROLES = tuple(
    (role.value, role.label)
    for role in (
        OrganizationMemberRole.ADMIN,
        OrganizationMemberRole.PROJECT_MANAGER,
        OrganizationMemberRole.MEMBER,
        OrganizationMemberRole.QA,
        OrganizationMemberRole.VIEWER,
    )
    if role != OrganizationMemberRole.OWNER
)


class OrganizationCreateForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"}),
            "description": forms.Textarea(attrs={"class": "mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200", "rows": 4}),
        }

    def clean_name(self):
        value = (self.cleaned_data.get("name") or "").strip()
        if not value:
            raise forms.ValidationError("Organization name is required.")
        return value


class OrganizationUpdateForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "description", "slug"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"}),
            "description": forms.Textarea(attrs={"class": "mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200", "rows": 4}),
            "slug": forms.TextInput(attrs={"class": "mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        if not slug:
            slug = self.instance.slug or ""
        slug = slugify(slug) if slug else slugify(self.cleaned_data.get("name") or self.instance.name)
        if not slug:
            raise forms.ValidationError("Slug is required.")
        if Organization.objects.filter(slug__iexact=slug).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This slug is already in use.")
        return slug

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("slug"):
            cleaned_data["slug"] = self.instance.slug or slugify(cleaned_data.get("name") or self.instance.name)
        return cleaned_data

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Organization name is required.")
        return name


class OrganizationMemberRoleForm(forms.Form):
    role = forms.ChoiceField(choices=ALLOWED_MEMBER_ROLES)


class OrganizationMemberAssignForm(forms.Form):
    user_id = forms.UUIDField()
    role = forms.ChoiceField(choices=ALLOWED_MEMBER_ROLES)


class InvitationCreateForm(forms.Form):
    email = forms.EmailField()
    role = forms.ChoiceField(choices=ALLOWED_MEMBER_ROLES)

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()


class OrganizationSwitchForm(forms.Form):
    organization_id = forms.UUIDField()


class OrganizationInviteResendForm(forms.Form):
    pass


class OrganizationInvitationRevokeForm(forms.Form):
    pass

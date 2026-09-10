import uuid
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import BaseModel


def generate_invitation_token():
    return uuid.uuid4().hex


class Organization(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="organizations/logos/", blank=True, null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_organizations")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["owner"]) ]

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "Organization name is required."})
        slug_value = (self.slug or "").strip() or slugify(self.name)
        slug_value = slugify(slug_value)
        if not slug_value:
            raise ValidationError({"name": "Organization name must generate a valid slug."})
        self.slug = slug_value
        if Organization.objects.filter(slug__iexact=slug_value).exclude(pk=self.pk).exists():
            raise ValidationError({"slug": "An organization with this slug already exists."})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class OrganizationMemberRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    PROJECT_MANAGER = "PROJECT_MANAGER", "Team Lead"
    MEMBER = "MEMBER", "Developer"
    QA = "QA", "QA"
    VIEWER = "VIEWER", "Viewer"


class OrganizationMember(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_memberships")
    role = models.CharField(max_length=30, choices=OrganizationMemberRole.choices, default=OrganizationMemberRole.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="unique_organization_member"),
            models.UniqueConstraint(
                fields=["organization"],
                condition=models.Q(role=OrganizationMemberRole.OWNER),
                name="unique_owner_per_organization",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "user"]),
            models.Index(fields=["organization", "role"]),
            models.Index(fields=["user", "is_active"]),
        ]
        ordering = ["organization__name", "user__email"]

    def __str__(self):
        return f"{self.user.email} @ {self.organization.name}"


class OrganizationInvitation(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REVOKED = "REVOKED", "Revoked"
        EXPIRED = "EXPIRED", "Expired"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=30, choices=OrganizationMemberRole.choices, default=OrganizationMemberRole.MEMBER)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_organization_invitations")
    token = models.CharField(max_length=64, unique=True, db_index=True, default=generate_invitation_token)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "email"]),
            models.Index(fields=["organization", "accepted_at"]),
            models.Index(fields=["email", "expires_at"]),
        ]
        ordering = ["-created_at"]

    @property
    def is_valid(self):
        return self.status == self.Status.PENDING and self.expires_at and self.expires_at > timezone.now() and not self.accepted_at and not self.revoked_at

    def clean(self):
        super().clean()
        self.email = self.email.strip().lower() if self.email else self.email
        expires_at = self.expires_at
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at.tzinfo is None:
                expires_at = timezone.make_aware(expires_at, timezone.utc)
        if expires_at and self.created_at and expires_at < self.created_at:
            raise ValidationError({"expires_at": "Expiration date must be after creation date."})
        if expires_at and expires_at <= timezone.now():
            raise ValidationError({"expires_at": "Expiration date must be in the future."})
        if self.accepted_at and self.status == self.Status.PENDING:
            self.status = self.Status.ACCEPTED
        if self.revoked_at and self.status == self.Status.PENDING:
            self.status = self.Status.REVOKED

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Invitation for {self.email} to {self.organization.name}"

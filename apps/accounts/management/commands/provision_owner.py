from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import User
from apps.core.models import ActivityLog
from apps.organizations.models import Organization, OrganizationMember, OrganizationMemberRole


class Command(BaseCommand):
    help = "Provision an existing user as the owner of a development organization."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("name")
        parser.add_argument("--description", default="")

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email=options["email"].strip().lower())
        except User.DoesNotExist as exc:
            raise CommandError("The user must already exist before provisioning an owner.") from exc
        name = options["name"].strip()
        slug = slugify(name)
        if not slug:
            raise CommandError("Organization name must contain letters or numbers.")
        with transaction.atomic():
            organization = Organization.objects.create(
                name=name,
                slug=slug,
                description=options["description"],
                owner=user,
            )
            OrganizationMember.objects.create(
                organization=organization,
                user=user,
                role=OrganizationMemberRole.OWNER,
            )
            ActivityLog.objects.create(
                organization=organization,
                user=user,
                action="organization_created",
                entity_type="organization",
                entity_id=organization.pk,
                description="Provisioned development owner organization",
            )
        self.stdout.write(self.style.SUCCESS(f"Provisioned {user.email} as OWNER of {organization.name}."))

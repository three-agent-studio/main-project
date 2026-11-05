"""Provision a synthetic student without committing a password or granting staff rights."""
import getpass
import sys

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Faculty, StudentProfile, StudyGroup, User


class Command(BaseCommand):
    help = "Create a synthetic student; password is read privately from the terminal or stdin."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--password-stdin", action="store_true")

    def handle(self, *args, **options):
        username = options["username"]
        user = User(username=username)
        try:
            user.full_clean(exclude=["password"])
        except ValidationError as exc:
            raise CommandError("Username is invalid or already exists.") from exc
        if options["password_stdin"]:
            password = sys.stdin.readline().rstrip("\r\n")
        else:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Repeat password: "):
                raise CommandError("Passwords do not match.")
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("Password does not meet the configured requirements.") from exc
        with transaction.atomic():
            faculty, _ = Faculty.objects.get_or_create(name="Демонстрационный факультет")
            group, _ = StudyGroup.objects.get_or_create(
                name="ДЕМО-1", defaults={"faculty": faculty, "programme": "ИТ", "course": 1}
            )
            user.set_password(password)
            user.save()
            StudentProfile.objects.create(
                user=user, full_name="Демонстрационный студент", group=group
            )
        self.stdout.write(self.style.SUCCESS(
            "Student created with a profile and no staff privileges."
        ))

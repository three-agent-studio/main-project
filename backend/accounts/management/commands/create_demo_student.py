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
        parser.add_argument("--full-name", default="Демонстрационный студент")
        parser.add_argument("--group", default="ДЕМО-1")

    def handle(self, *args, **options):
        username = options["username"]
        full_name = options["full_name"].strip()
        group_name = options["group"].strip()
        if not full_name or len(full_name) > 250 or not group_name or len(group_name) > 50:
            raise CommandError(
                "Provide a full name (1–250 characters) and group (1–50 characters)."
            )
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
                name=group_name, defaults={"faculty": faculty, "programme": "ИТ", "course": 1}
            )
            if group.faculty_id != faculty.pk:
                raise CommandError("This group belongs to another faculty; choose a demo group.")
            user.set_password(password)
            user.save()
            StudentProfile.objects.create(user=user, full_name=full_name, group=group)
        self.stdout.write(
            self.style.SUCCESS("Student created with a profile and no staff privileges.")
        )

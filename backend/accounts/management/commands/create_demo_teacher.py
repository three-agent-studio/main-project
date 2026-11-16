"""Explicit demo account provisioning; never reset an existing user's password or grants."""

import getpass
import json
import secrets

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import StudyGroup
from accounts.provisioning import create_teacher_account


class Command(BaseCommand):
    help = "Создать вымышленного преподавателя без прав Admin для одной группы/дисциплины."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--group", required=True)
        parser.add_argument("--subject", default="Демо: базы данных")
        parser.add_argument("--full-name", default="Демонстрационный преподаватель")
        parser.add_argument("--generate-password", action="store_true")

    def handle(self, *args, **options):
        try:
            group = StudyGroup.objects.get(name=options["group"])
        except StudyGroup.DoesNotExist:
            raise CommandError("Укажите существующую демонстрационную группу.") from None
        password = (
            secrets.token_urlsafe(18)
            if options["generate_password"]
            else getpass.getpass("Пароль преподавателя: ")
        )
        if not options["generate_password"] and getpass.getpass("Повторите пароль: ") != password:
            raise CommandError("Пароли не совпали.")
        try:
            user = create_teacher_account(
                username=options["username"],
                password=password,
                group=group,
                full_name=options["full_name"],
                subject=options["subject"],
            )
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from None
        # Credentials go only to the invoking administrator, after the transaction commits.
        self.stdout.write(json.dumps({"username": user.username, "password": password}))

"""Explicit, repeatable synthetic schedule; never provisions accounts or resets data."""

from datetime import date, datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academics.models import Lesson
from academics.services import change_lesson
from accounts.models import StudyGroup


class Command(BaseCommand):
    help = "Добавить вымышленное расписание существующей демонстрационной группе."

    def add_arguments(self, parser):
        parser.add_argument("--group", required=True, help="Имя существующей группы")
        parser.add_argument(
            "--week-start",
            type=date.fromisoformat,
            help="Понедельник YYYY-MM-DD; по умолчанию текущая неделя",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            group = StudyGroup.objects.get(name=options["group"])
        except StudyGroup.DoesNotExist:
            raise CommandError("Сначала создайте демонстрационную группу.") from None
        today = timezone.localdate(timezone=timezone.get_default_timezone())
        monday = options["week_start"] or today - timedelta(days=today.weekday())
        if monday.weekday() != 0 or monday.year >= 9999:
            raise CommandError("Укажите понедельник в допустимом диапазоне дат.")
        created_count = 0
        for offset, subject in enumerate(
            [
                "Демо: проектирование интерфейсов",
                "Демо: базы данных",
                "Демо: алгоритмы",
                "Демо: командный проект",
            ]
        ):
            starts = datetime.combine(
                monday + timedelta(days=offset), time(9), tzinfo=timezone.get_default_timezone()
            )
            lesson, created = Lesson.objects.get_or_create(
                pk=uuid5(NAMESPACE_URL, f"deanery:demo:{group.pk}:{monday}:{offset}"),
                defaults={
                    "group": group,
                    "subject": subject,
                    "teacher": "Вымышленный преподаватель",
                    "room": "ДЕМО-101",
                    "kind": Lesson.Kind.PRACTICE,
                    "starts_at": starts,
                    "ends_at": starts + timedelta(minutes=90),
                },
            )
            if not created:
                continue  # Never undo a person's subsequent edits on repeated seed.
            created_count += 1
            if offset == 1:
                change_lesson(
                    lesson.pk,
                    changes={
                        "starts_at": starts + timedelta(hours=2),
                        "ends_at": starts + timedelta(hours=3, minutes=30),
                        "room": "ДЕМО-202",
                    },
                    reason="Демонстрационный перенос занятия",
                )
            if offset == 2:
                change_lesson(
                    lesson.pk,
                    changes={"status": Lesson.Status.CANCELLED},
                    reason="Демонстрационная отмена занятия",
                )
        self.stdout.write(self.style.SUCCESS(f"Создано демонстрационных занятий: {created_count}"))

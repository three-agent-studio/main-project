"""Provision four isolated demo accounts and synthetic jury data."""

import json
import os
import secrets
from datetime import timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academics.models import AcademicActivity, Assessment, TeachingAssignment
from accounts.models import Faculty, StaffProfile, StudentProfile, StudyGroup, TeacherProfile, User
from notifications.models import Announcement
from service_requests.models import RequestEvent, ServiceRequest

IDENTITIES = ("jury_student_a", "jury_student_b", "jury_deanery", "jury_teacher")
GROUPS = (
    ("ДЕМО-ЖЮРИ-А", "ДЕМО: инженерный факультет", "Инженерные системы", 2, "Макетов Лев Ильич"),
    ("ДЕМО-ЖЮРИ-Б", "ДЕМО: факультет дизайна", "Прикладной дизайн", 1, "Эскизова Мира Денисовна"),
)


def demo_id(label):
    return uuid5(NAMESPACE_URL, f"digital-deanery:contest:{label}")


def credentials(path):
    # Create a private file before any DB changes. A retry reuses recoverable credentials.
    if path.exists():
        if path.is_symlink() or (os.name != "nt" and path.stat().st_mode & 0o077):
            raise CommandError("Файл доступа должен быть обычным файлом с правами 600.")
        data = json.loads(path.read_text())
        if (
            not isinstance(data, dict)
            or set(data) != set(IDENTITIES)
            or not all(
                isinstance(password, str) and len(password) >= 18 for password in data.values()
            )
        ):
            raise CommandError("Файл доступа не соответствует ожидаемым демо-аккаунтам.")
        return data
    if User.objects.filter(username__in=IDENTITIES).exists():
        raise CommandError("Демо-логин уже занят. Нужен файл доступа от первоначальной настройки.")
    data = {username: secrets.token_urlsafe(20) for username in IDENTITIES}
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        json.dump(data, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    return data


class Command(BaseCommand):
    help = "Подготовить два вымышленных кабинета студента, сотрудника и преподавателя для жюри."

    def add_arguments(self, parser):
        parser.add_argument("--credentials", type=Path, required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        path = options["credentials"]
        passwords = credentials(path)
        users = {}
        for username, password in passwords.items():
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User.objects.create_user(username=username, password=password)
            elif (
                not user.check_password(password)
                or not user.is_active
                or user.is_staff
                or user.is_superuser
                or user.groups.exists()
                or user.user_permissions.exists()
            ):
                raise CommandError(f"Аккаунт {username} уже существует с другими настройками.")
            users[username] = user

        groups = []
        for username, (name, faculty_name, programme, course, person) in zip(IDENTITIES, GROUPS):
            faculty, _ = Faculty.objects.get_or_create(name=faculty_name)
            group, _ = StudyGroup.objects.get_or_create(
                name=name,
                defaults={"faculty": faculty, "programme": programme, "course": course},
            )
            if group.faculty_id != faculty.pk:
                raise CommandError(f"Группа {name} относится к другому факультету.")
            student, _ = StudentProfile.objects.get_or_create(
                user=users[username],
                defaults={"full_name": person, "group": group},
            )
            if student.group_id != group.pk:
                raise CommandError(f"Аккаунт {username} относится к другой группе.")
            groups.append((group, student))

        (first, first_student), (second, second_student) = groups
        staff, _ = StaffProfile.objects.get_or_create(
            user=users["jury_deanery"],
            defaults={"full_name": "Справкина Нина Олеговна", "faculty": first.faculty},
        )
        teacher, _ = TeacherProfile.objects.get_or_create(
            user=users["jury_teacher"],
            defaults={"full_name": "Проектов Павел Игоревич", "faculty": first.faculty},
        )
        if staff.faculty_id != first.faculty_id or teacher.faculty_id != first.faculty_id:
            raise CommandError("У сотрудника или преподавателя другой факультет.")
        for username, user in users.items():
            expected = {
                "jury_student_a": (True, False, False),
                "jury_student_b": (True, False, False),
                "jury_deanery": (False, True, False),
                "jury_teacher": (False, False, True),
            }[username]
            actual = tuple(
                hasattr(user, name)
                for name in ("student_profile", "staff_profile", "teacher_profile")
            )
            if actual != expected or (username == "jury_teacher" and not teacher.is_active):
                raise CommandError(f"У {username} обнаружены другие роли или назначение отключено.")

        call_command("seed_demo_schedule", group=first.name, profile="engineering", weeks=3)
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        for week in range(3):
            call_command(
                "seed_demo_schedule", group=second.name, week_start=monday + timedelta(weeks=week)
            )

        assignment, _ = TeachingAssignment.objects.get_or_create(
            teacher=teacher,
            group=first,
            subject="ДЕМО: проектирование",
            term="Демонстрационный семестр",
        )
        now = timezone.now()
        work, _ = AcademicActivity.objects.get_or_create(
            pk=demo_id("activity"),
            defaults={
                "assignment": assignment,
                "kind": AcademicActivity.Kind.HOMEWORK,
                "title": "Спроектировать учебный сервис",
                "due_at": now + timedelta(hours=36),
                "description": (
                    "Опишите один сценарий вымышленного студента и нарисуйте схему экранов."
                ),
            },
        )
        Assessment.objects.get_or_create(
            activity=work,
            student=first_student,
            defaults={"status": Assessment.Status.GRADED, "score": 5, "comment": "Учебная оценка."},
        )
        request, created = ServiceRequest.objects.get_or_create(
            student=second_student,
            request_key=demo_id("request-B"),
            defaults={
                "kind": ServiceRequest.Kind.APPLICATION,
                "text": "Демо: вопрос о графике консультаций.",
            },
        )
        if created:
            RequestEvent.objects.create(
                ticket=request,
                status=request.status,
                revision=request.revision,
                actor=second_student.user,
            )
        for group, title, body in (
            (
                first,
                "Неделя инженерных проектов",
                "Проверьте ближайшие занятия и сроки по проектной работе.",
            ),
            (
                second,
                "Консультация по эскизам",
                "Проверьте расписание своей группы перед консультацией.",
            ),
        ):
            Announcement.objects.get_or_create(
                pk=demo_id(group.name),
                defaults={"faculty": group.faculty, "title": title, "message": body},
            )
        self.stdout.write(
            self.style.SUCCESS(f"Демо-аккаунты готовы. Закрытый файл доступа: {path}")
        )

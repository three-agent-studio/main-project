"""Curated synthetic engineering timetable, not an import of a university group.

Only subject families and the rhythm of 100-minute classes are inspired by public
SPbPU materials. Teachers, rooms, dates and combinations below are invented.
Keep stable slot keys: repeat runs must preserve a person's later edits.
"""

from datetime import datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5

from django.db import transaction
from django.utils import timezone

from accounts.models import StudyGroup

from .models import Lesson
from .services import change_lesson

# Subject, synthetic teacher label, synthetic room. No real personal data.
COURSES = {
    "math": ("Высшая математика", "Математика", "А · 201"),
    "graphics": ("Инженерная графика", "Графика", "А · 310"),
    "physics": ("Физика", "Физика", "Б · 102"),
    "mechanics": ("Теоретическая механика", "Механика", "А · 204"),
    "materials": ("Материаловедение", "Материалы", "Б · лаборатория 105"),
    "language": ("Иностранный язык", "Иностранный язык", "А · 215"),
    "cad": ("Компьютерное проектирование (CAD)", "CAD", "В · компьютерный класс 302"),
    "sport": ("Физическая культура", "Физическая культура", "Спортзал"),
    "strength": ("Сопротивление материалов", "Прочность", "А · 208"),
    "metrology": ("Метрология и технические измерения", "Измерения", "Б · лаборатория 107"),
    "project": ("Проектная работа", "Проектный практикум", "В · проектная мастерская"),
    "manufacturing": ("Технология машиностроения", "Технологии", "Б · 206"),
}

# Day offset, start hour, subject key, kind in synthetic week A / B.
# Three or four pairs on weekdays, two on Saturday, Sunday free; no hidden
# dependency on the group's real programme/year or SPbPU's actual week parity.
SLOTS = (
    (0, 8, "math", "lecture", "practice"),
    (0, 10, "graphics", "practice", "lecture"),
    (0, 12, "physics", "lecture", "lecture"),
    (1, 10, "mechanics", "lecture", "seminar"),
    (1, 12, "materials", "lecture", "lecture"),
    (1, 14, "language", "practice", "practice"),
    (2, 8, "math", "practice", "lecture"),
    (2, 10, "physics", "lab", "seminar"),
    (2, 12, "cad", "lab", "lab"),
    (2, 14, "sport", "practice", "practice"),
    (3, 10, "strength", "lecture", "practice"),
    (3, 12, "metrology", "practice", "lab"),
    (3, 14, "graphics", "lab", "practice"),
    (4, 8, "mechanics", "practice", "lecture"),
    (4, 10, "materials", "lab", "practice"),
    (4, 12, "project", "practice", "practice"),
    (5, 10, "manufacturing", "lecture", "practice"),
    (5, 12, "sport", "practice", "practice"),
)


def occurrences(group, monday, weeks):
    zone = timezone.get_default_timezone()
    for week in range(weeks):
        start = monday + timedelta(weeks=week)
        # Anchor parity to a fixed Monday, not the requested batch's first week.
        # Otherwise re-running an overlapping date range changes its template.
        phase = (start.toordinal() // 7) % 2
        for day, hour, key, kind_a, kind_b in SLOTS:
            subject, teacher, room = COURSES[key]
            begins = datetime.combine(start + timedelta(days=day), time(hour), tzinfo=zone)
            identifier = uuid5(
                NAMESPACE_URL, f"deanery:engineering:v1:{group.pk}:{begins.date()}:{hour}"
            )
            changes = None
            reason = ""
            if key == "metrology" and phase == 0:
                changes = {"room": "ДЕМО-Б · лаборатория 109"}
                reason = "Учебный пример: занятие перенесено в соседнюю лабораторию."
            if day == 5 and key == "sport" and phase == 1:
                changes = {"status": Lesson.Status.CANCELLED}
                reason = "Учебный пример: занятие отменено, самостоятельная подготовка."
            yield (
                identifier,
                {
                    "group": group,
                    "subject": subject,
                    "teacher": f"Демо-преподаватель: {teacher}",
                    "room": f"ДЕМО-{room}",
                    "kind": kind_a if phase == 0 else kind_b,
                    "starts_at": begins,
                    "ends_at": begins + timedelta(minutes=100),
                },
                changes,
                reason,
            )


@transaction.atomic
def seed_engineering_schedule(group, monday, weeks, *, dry_run=False):
    # Serialize repeat seed jobs for this group; other groups remain independent.
    StudyGroup.objects.select_for_update().get(pk=group.pk)
    report = {
        "profile": "engineering",
        "group": group.name,
        "from": monday.isoformat(),
        "to": (monday + timedelta(weeks=weeks, days=-1)).isoformat(),
        "weeks": weeks,
        "subjects": [course[0] for course in COURSES.values()],
        "dry_run": dry_run,
        "created": 0,
        "existing": 0,
        "conflicts": 0,
        "planned": 0,
        "created_ids": [],
    }
    for identifier, defaults, changes, reason in occurrences(group, monday, weeks):
        if Lesson.objects.filter(pk=identifier).exists():
            report["existing"] += 1
            continue  # Preserve edits, cancellation and history on every repeat.
        overlaps = Lesson.objects.filter(
            group=group, starts_at__lt=defaults["ends_at"], ends_at__gt=defaults["starts_at"]
        ).exclude(status=Lesson.Status.CANCELLED)
        if overlaps.exists():
            report["conflicts"] += 1
            continue  # Never remove or move existing lessons to fit demo data.
        report["planned"] += 1
        if dry_run:
            continue
        lesson = Lesson(pk=identifier, **defaults)
        lesson.full_clean()
        lesson.save(force_insert=True)
        if changes:
            change_lesson(lesson.pk, changes=changes, reason=reason)
        report["created"] += 1
        report["created_ids"].append(str(identifier))
    return report

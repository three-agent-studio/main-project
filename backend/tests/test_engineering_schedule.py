"""Synthetic data is repeatable, realistic and preserves the operator's work."""

import json
from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from django.utils import timezone

from academics.engineering_schedule import COURSES
from academics.models import Lesson, LessonChange
from academics.services import change_lesson
from accounts.models import Faculty, StudentProfile, StudyGroup, User

pytestmark = pytest.mark.django_db
MONDAY = date(2026, 11, 16)


@pytest.fixture
def group():
    faculty = Faculty.objects.create(name="Вымышленный инженерный факультет")
    return StudyGroup.objects.create(
        name="ДЕМО-ИНЖ", faculty=faculty, programme="Учебный инженерный профиль", course=2
    )


def seed(group, **kwargs):
    output = StringIO()
    call_command(
        "seed_demo_schedule",
        group=group.name,
        profile="engineering",
        json_output=True,
        stdout=output,
        **({"weeks": 4, "week_start": MONDAY} | kwargs),
    )
    return json.loads(output.getvalue())


def test_four_weeks_have_varied_non_overlapping_synthetic_classes(group):
    report = seed(group)
    assert report["created"] == 72 and report["conflicts"] == 0
    assert len(report["subjects"]) == 12
    assert set(Lesson.objects.values_list("kind", flat=True)) == set(Lesson.Kind.values)
    assert LessonChange.objects.count() == 4
    assert set(Lesson.objects.values_list("status", flat=True)) == set(Lesson.Status.values)
    last_by_day = {}
    count_by_day = {}
    for lesson in Lesson.objects.order_by("starts_at"):
        start, end = timezone.localtime(lesson.starts_at), timezone.localtime(lesson.ends_at)
        day = start.date()
        assert day.weekday() < 6
        assert end - start == timedelta(minutes=100)
        assert 8 <= start.hour < end.hour <= 16
        if day in last_by_day:
            assert start - last_by_day[day] >= timedelta(minutes=20)
        last_by_day[day] = end
        count_by_day[day] = count_by_day.get(day, 0) + 1
        assert lesson.room.startswith("ДЕМО-")
        assert lesson.teacher in {course[1] for course in COURSES.values()}
    assert set(count_by_day.values()) == {2, 3, 4}


def test_repeat_and_overlapping_batches_preserve_manual_edits_and_history(group):
    seed(group, weeks=2)
    lesson = Lesson.objects.order_by("starts_at").first()
    change_lesson(lesson.pk, changes={"room": "ДЕМО-РУЧНАЯ"}, reason="Ручная правка")
    history = LessonChange.objects.count()
    report = seed(group, weeks=2)
    assert report["created"] == 0 and report["existing"] == 36
    lesson.refresh_from_db()
    assert lesson.room == "ДЕМО-РУЧНАЯ" and LessonChange.objects.count() == history
    next_report = seed(group, weeks=2, week_start=MONDAY + timedelta(weeks=1))
    assert next_report["created"] == 18 and next_report["existing"] == 18
    assert Lesson.objects.count() == 54


@pytest.mark.parametrize("cancelled", [False, True])
def test_existing_active_lessons_win_over_seed_slots(group, cancelled):
    from academics.engineering_schedule import occurrences

    _, defaults, _, _ = next(occurrences(group, MONDAY, 1))
    manual = Lesson.objects.create(
        **(
            defaults
            | {"subject": "Ручное занятие", "status": "cancelled" if cancelled else "scheduled"}
        )
    )
    report = seed(group, weeks=1)
    assert report["created"] == (18 if cancelled else 17)
    assert report["conflicts"] == (0 if cancelled else 1)
    manual.refresh_from_db()
    assert manual.subject == "Ручное занятие"


def test_dry_run_does_not_write_lessons_or_history(group):
    report = seed(group, dry_run=True)
    assert report["planned"] == 72 and report["created"] == 0
    assert not Lesson.objects.exists() and not LessonChange.objects.exists()


@pytest.mark.parametrize(
    "params",
    [
        {"weeks": 0},
        {"weeks": 9},
        {"week_start": date(2026, 11, 17)},
        {"week_start": date(9999, 12, 27)},
    ],
)
def test_invalid_period_never_partially_fills_the_database(group, params):
    with pytest.raises(CommandError):
        seed(group, **params)
    assert not Lesson.objects.exists()


def test_history_failure_rolls_back_the_entire_seed(group, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic history failure")

    monkeypatch.setattr("academics.engineering_schedule.change_lesson", fail)
    with pytest.raises(RuntimeError, match="history failure"):
        seed(group)
    assert not Lesson.objects.exists()


def test_filled_schedule_is_visible_only_to_its_current_group(group, monkeypatch):
    seed(group)
    other = StudyGroup.objects.create(
        name="ДЕМО-ДРУГАЯ", faculty=group.faculty, programme="Другое направление", course=1
    )
    seed(other, weeks=1)
    user = User.objects.create_user(username="synthetic_timetable_student")
    StudentProfile.objects.create(user=user, full_name="Учебный студент", group=group)
    client = Client()
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    monkeypatch.setattr("academics.views.timezone.localdate", lambda **kwargs: MONDAY)
    response = client.get("/api/v1/lessons/", {"group_id": other.pk})
    assert response.status_code == 200
    page = response.json()
    assert page["count"] == 18
    assert {item["group"] for item in page["results"]} == {group.name}


def restore_old_placeholders():
    from academics.engineering_schedule import LEGACY_TEACHERS

    for old, full in LEGACY_TEACHERS.items():
        Lesson.objects.filter(teacher=full).update(teacher=old)


def test_explicit_name_upgrade_is_audited_and_keeps_manual_changes(group):
    seed(group, weeks=2)
    restore_old_placeholders()
    first, second = list(Lesson.objects.order_by("starts_at")[:2])
    change_lesson(
        first.pk, changes={"teacher": "Вымышленный Ручной Преподаватель"}, reason="Ручное ФИО"
    )
    change_lesson(second.pk, changes={"subject": "Ручной предмет"}, reason="Ручной предмет")
    fields = ["id", "group_id", "subject", "room", "starts_at", "ends_at", "status"]
    before = list(Lesson.objects.order_by("id").values_list(*fields))
    assert seed(group, weeks=2)["teachers_updated"] == 0
    old_history = LessonChange.objects.count()
    report = seed(group, weeks=2, refresh_demo_teachers=True)
    assert report["teachers_updated"] == 34 and report["created"] == 0
    assert LessonChange.objects.count() == old_history + 34
    assert list(Lesson.objects.order_by("id").values_list(*fields)) == before
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.teacher == "Вымышленный Ручной Преподаватель"
    assert second.teacher.startswith("Демо-преподаватель:")
    assert seed(group, weeks=2, refresh_demo_teachers=True)["teachers_updated"] == 0
    assert LessonChange.objects.count() == old_history + 34


def test_name_upgrade_dry_run_keeps_the_database_unchanged(group):
    seed(group, weeks=1)
    restore_old_placeholders()
    before = list(Lesson.objects.order_by("id").values_list("teacher", "revision"))
    history = LessonChange.objects.count()
    report = seed(group, weeks=1, refresh_demo_teachers=True, dry_run=True)
    assert report["teachers_planned"] == 18 and report["teachers_updated"] == 0
    assert list(Lesson.objects.order_by("id").values_list("teacher", "revision")) == before
    assert LessonChange.objects.count() == history


def test_failed_name_upgrade_rolls_back_earlier_updates(group, monkeypatch):
    seed(group, weeks=1)
    restore_old_placeholders()
    before = list(Lesson.objects.order_by("id").values_list("teacher", "revision"))
    history = LessonChange.objects.count()
    calls = 0

    def fail_after_one(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Synthetic update failure")
        return change_lesson(*args, **kwargs)

    monkeypatch.setattr("academics.engineering_schedule.change_lesson", fail_after_one)
    with pytest.raises(RuntimeError, match="update failure"):
        seed(group, weeks=1, refresh_demo_teachers=True)
    assert list(Lesson.objects.order_by("id").values_list("teacher", "revision")) == before
    assert LessonChange.objects.count() == history

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client

from academics.models import Lesson, LessonChange
from academics.services import change_lesson
from accounts.models import Faculty, StaffProfile, StudentProfile, StudyGroup, User

pytestmark = pytest.mark.django_db
ZONE = ZoneInfo("Europe/Moscow")
START = datetime(2026, 11, 16, 9, tzinfo=ZONE)
PERIOD = {"from": "2026-11-16", "to": "2026-11-22"}
BACKEND = "django.contrib.auth.backends.ModelBackend"


@pytest.fixture
def schedule():
    faculty = Faculty.objects.create(name="Демо-факультет")
    groups = [
        StudyGroup.objects.create(name=name, faculty=faculty, programme="ИТ", course=1)
        for name in ("ДЕМО-А", "ДЕМО-Б")
    ]
    users, lessons = [], []
    for i, group in enumerate(groups):
        user = User.objects.create_user(username=f"schedule_{i}")
        StudentProfile.objects.create(user=user, full_name=f"Демо {i}", group=group)
        users.append(user)
        lessons.append(
            Lesson.objects.create(
                group=group,
                subject=f"Демо-дисциплина {i}",
                teacher="Вымышленный преподаватель",
                room="ДЕМО-101",
                starts_at=START,
                ends_at=START + timedelta(minutes=90),
            )
        )
    employee = User.objects.create_user(username="schedule_staff", is_staff=True, is_superuser=True)
    StaffProfile.objects.create(user=employee, full_name="Демо-сотрудник", faculty=faculty)
    client = Client()
    client.force_login(users[0], backend=BACKEND)
    return SimpleNamespace(
        groups=groups, users=users, lessons=lessons, employee=employee, client=client
    )


def test_schedule_is_group_scoped_even_with_forged_parameters(schedule):
    response = schedule.client.get(
        "/api/v1/lessons/",
        {
            **PERIOD,
            "group_id": schedule.groups[1].pk,
            "user_id": schedule.users[1].pk,
        },
    )
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    data = response.json()
    assert data["count"] == 1
    lesson = data["results"][0]
    assert lesson["id"] == str(schedule.lessons[0].pk)
    assert lesson["group"] == "ДЕМО-А"
    assert lesson["last_change"] is None
    assert schedule.client.get(f"/api/v1/lessons/{schedule.lessons[1].pk}/").status_code == 404
    assert schedule.client.get(f"/api/v1/lessons/{schedule.lessons[0].pk}/").status_code == 200


def test_other_student_in_same_group_can_read_shared_lessons(schedule):
    user = User.objects.create_user(username="same_group_student")
    StudentProfile.objects.create(user=user, full_name="Демо", group=schedule.groups[0])
    schedule.client.force_login(user, backend=BACKEND)
    assert schedule.client.get("/api/v1/lessons/", PERIOD).json()["count"] == 1


def test_group_reassignment_is_effective_on_next_request(schedule):
    StudentProfile.objects.filter(user=schedule.users[0]).update(group=schedule.groups[1])
    results = schedule.client.get("/api/v1/lessons/", PERIOD).json()["results"]
    assert [row["id"] for row in results] == [str(schedule.lessons[1].pk)]
    assert schedule.client.get(f"/api/v1/lessons/{schedule.lessons[0].pk}/").status_code == 404


def test_login_and_student_role_are_required(schedule):
    assert Client().get("/api/v1/lessons/").status_code == 403
    schedule.client.force_login(schedule.employee, backend=BACKEND)
    assert schedule.client.get("/api/v1/lessons/", PERIOD).status_code == 403
    assert schedule.client.get(f"/api/v1/lessons/{schedule.lessons[0].pk}/").status_code == 403


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_student_cannot_mutate_schedule(schedule, method):
    for url in ("/api/v1/lessons/", f"/api/v1/lessons/{schedule.lessons[0].pk}/"):
        response = getattr(schedule.client, method)(
            url, {"room": "forged"}, content_type="application/json"
        )
        assert response.status_code == 405
    schedule.lessons[0].refresh_from_db()
    assert schedule.lessons[0].room == "ДЕМО-101"


@pytest.mark.parametrize(
    "params",
    [
        {"from": "bad"},
        {"to": "2026-02-30"},
        {"from": ""},
        {"from": "2026-11-20", "to": "2026-11-19"},
        {"from": "2026-11-01", "to": "2026-12-02"},
        {"from": "9999-12-31"},
        {"from": "9999-12-31", "to": "9999-12-31"},
    ],
)
def test_invalid_period_returns_structured_400(schedule, params):
    response = schedule.client.get("/api/v1/lessons/", params)
    assert response.status_code == 400
    assert response.json()["error"]["status"] == 400


def test_today_includes_cross_midnight_and_excludes_exact_end_boundary(schedule):
    lesson = schedule.lessons[0]
    lesson.starts_at = datetime(2026, 11, 15, 23, 30, tzinfo=ZONE)
    lesson.ends_at = datetime(2026, 11, 16, 0, 30, tzinfo=ZONE)
    lesson.save()
    response = schedule.client.get("/api/v1/lessons/", {"from": "2026-11-16", "to": "2026-11-16"})
    assert response.json()["count"] == 1
    lesson.ends_at = datetime(2026, 11, 16, 0, 0, tzinfo=ZONE)
    lesson.save()
    assert schedule.client.get("/api/v1/lessons/", PERIOD).json()["count"] == 0


def test_default_period_is_monday_to_sunday(schedule, monkeypatch):
    monkeypatch.setattr("academics.views.timezone.localdate", lambda **kwargs: date(2026, 11, 18))
    assert schedule.client.get("/api/v1/lessons/").json()["count"] == 1
    assert schedule.client.get("/api/v1/lessons/", {"from": "2026-11-23"}).json()["count"] == 0


def test_changes_are_atomic_versioned_and_visible_in_api(schedule):
    lesson = schedule.lessons[0]
    changed = change_lesson(
        lesson.pk,
        changes={"room": "ДЕМО-202"},
        reason="Перенос аудитории",
        actor=schedule.employee,
        expected_revision=1,
    )
    assert changed.status == Lesson.Status.MOVED
    assert changed.revision == 2
    event = LessonChange.objects.get(lesson=lesson)
    assert event.before["room"] == "ДЕМО-101"
    assert event.after["room"] == "ДЕМО-202"
    assert event.changed_by_id == schedule.employee.pk
    change_lesson(lesson.pk, changes={"status": "cancelled"}, reason="Демо-отмена")
    detail = schedule.client.get(f"/api/v1/lessons/{lesson.pk}/").json()
    assert detail["status"] == "cancelled"
    assert detail["last_change"]["revision"] == 3
    assert detail["last_change"]["reason"] == "Демо-отмена"
    assert "changed_by" not in detail["last_change"]
    assert schedule.client.get("/api/v1/lessons/", PERIOD).json()["count"] == 1
    assert LessonChange.objects.filter(lesson=lesson).count() == 2


def test_same_save_is_not_another_event_even_with_another_timezone(schedule):
    lesson = schedule.lessons[0]
    change_lesson(lesson.pk, changes={"starts_at": START.astimezone(ZoneInfo("UTC"))}, reason="")
    assert not LessonChange.objects.exists()
    lesson.refresh_from_db()
    assert lesson.revision == 1


def test_invalid_or_stale_change_does_not_modify_lesson(schedule):
    lesson = schedule.lessons[0]
    for changes, reason in [
        ({"room": "ДЕМО-202"}, ""),
        ({"group_id": 123}, "test"),
        ({"ends_at": START}, "Неверное время"),
    ]:
        with pytest.raises(ValidationError):
            change_lesson(lesson.pk, changes=changes, reason=reason)
    with pytest.raises(ValidationError):
        change_lesson(lesson.pk, changes={"room": "ДЕМО-202"}, reason="test", expected_revision=99)
    lesson.refresh_from_db()
    assert lesson.room == "ДЕМО-101" and lesson.revision == 1
    assert not LessonChange.objects.exists()


def test_history_failure_rolls_back_the_lesson_update(schedule, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("synthetic event storage failure")

    monkeypatch.setattr(LessonChange.objects, "create", fail)
    with pytest.raises(RuntimeError):
        change_lesson(schedule.lessons[0].pk, changes={"room": "ДЕМО-202"}, reason="Test")
    schedule.lessons[0].refresh_from_db()
    assert schedule.lessons[0].room == "ДЕМО-101"
    assert not LessonChange.objects.exists()


def test_database_rejects_non_positive_duration(schedule):
    with pytest.raises(IntegrityError), transaction.atomic():
        Lesson.objects.filter(pk=schedule.lessons[0].pk).update(ends_at=START)


def test_demo_seed_is_idempotent_and_keeps_later_edits(schedule):
    args = {"group": "ДЕМО-А", "week_start": date(2026, 11, 16)}
    call_command("seed_demo_schedule", **args)
    count, changes = Lesson.objects.count(), LessonChange.objects.count()
    demo = Lesson.objects.get(subject="Демо: проектирование интерфейсов")
    change_lesson(demo.pk, changes={"room": "ДЕМО-999"}, reason="Сохранить ручное изменение")
    call_command("seed_demo_schedule", **args)
    assert Lesson.objects.count() == count
    assert LessonChange.objects.count() == changes + 1
    demo.refresh_from_db()
    assert demo.room == "ДЕМО-999"
    with pytest.raises(CommandError):
        call_command("seed_demo_schedule", group="unknown", week_start=date(2026, 11, 16))


def test_schedule_pagination_is_stable(schedule):
    original = schedule.lessons[0]
    for _ in range(25):
        Lesson.objects.create(
            group=original.group,
            subject="Демо",
            teacher="Демо",
            room="Демо",
            starts_at=START,
            ends_at=START + timedelta(hours=1),
        )
    first = schedule.client.get("/api/v1/lessons/", PERIOD).json()
    second = schedule.client.get(first["next"]).json()
    assert first["count"] == 26 and len(first["results"]) == 25
    assert len(second["results"]) == 1
    assert {row["id"] for row in first["results"]}.isdisjoint(
        row["id"] for row in second["results"]
    )


def test_time_transfer_uses_current_period_and_preserves_previous_time(schedule):
    lesson = schedule.lessons[0]
    later = START + timedelta(days=7)
    change_lesson(
        lesson.pk,
        changes={"starts_at": later, "ends_at": later + timedelta(hours=1)},
        reason="Демо-перенос на следующую неделю",
    )
    assert schedule.client.get("/api/v1/lessons/", PERIOD).json()["count"] == 0
    results = schedule.client.get("/api/v1/lessons/", {"from": "2026-11-23"}).json()["results"]
    assert results[0]["status"] == "moved"
    previous = datetime.fromisoformat(results[0]["last_change"]["before"]["starts_at"])
    assert previous == START


def test_admin_edits_use_history_and_reject_stale_forms(schedule):
    client = Client()
    client.force_login(schedule.employee, backend=BACKEND)
    url = f"/admin/academics/lesson/{schedule.lessons[0].pk}/change/"
    response = client.get(url)
    assert response.status_code == 200
    data = {
        "subject": "Демо-дисциплина 0",
        "teacher": "Вымышленный преподаватель",
        "room": "ДЕМО-303",
        "kind": "practice",
        "status": "scheduled",
        "starts_at_0": "2026-11-16",
        "starts_at_1": "09:00:00",
        "ends_at_0": "2026-11-16",
        "ends_at_1": "10:30:00",
        "expected_revision": "1",
        "change_reason": "Демо-перенос из Admin",
        "_save": "1",
    }
    assert client.post(url, data).status_code == 302
    lesson = Lesson.objects.get(pk=schedule.lessons[0].pk)
    assert lesson.room == "ДЕМО-303" and lesson.status == "moved"
    assert lesson.revision == 2
    assert LessonChange.objects.get(lesson=lesson).changed_by_id == schedule.employee.pk
    response = client.post(url, {**data, "room": "ДЕМО-404"})
    assert response.status_code == 200
    assert "Занятие уже изменилось" in response.content.decode()
    lesson.refresh_from_db()
    assert lesson.room == "ДЕМО-303"
    assert LessonChange.objects.filter(lesson=lesson).count() == 1

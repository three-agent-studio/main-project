import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from academics.models import AcademicActivity, Lesson, LessonChange, TeachingAssignment
from accounts.models import Faculty, StaffProfile, StudentProfile, StudyGroup, TeacherProfile
from notifications.models import Announcement, NoticeRead
from service_requests.models import ServiceRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def people():
    users = get_user_model().objects
    faculty = Faculty.objects.create(name="ДЕМО А")
    other_faculty = Faculty.objects.create(name="ДЕМО Б")
    students = []
    for index, current_faculty in enumerate((faculty, faculty, other_faculty)):
        user = users.create_user(username=f"student-{index}")
        group, _ = StudyGroup.objects.get_or_create(
            name=f"Группа {current_faculty.pk}",
            defaults={"faculty": current_faculty, "course": 1, "programme": "ИТ"},
        )
        students.append(StudentProfile.objects.create(user=user, group=group, full_name="Демо"))
    staff = users.create_user(username="employee")
    StaffProfile.objects.create(user=staff, faculty=faculty, full_name="Демо сотрудник")
    return students, staff


def signed_in(user):
    client = APIClient()
    client.force_login(user)
    return client


def submit(student, **extra):
    client = signed_in(student.user)
    return client.post(
        "/api/v1/requests/",
        {
            "kind": "certificate",
            "request_key": str(uuid.uuid4()),
            **extra,
        },
        format="json",
    )


def transition(client, ticket_id, status, revision=1, comment=""):
    return client.post(
        f"/api/v1/staff/requests/{ticket_id}/status/",
        {
            "status": status,
            "expected_revision": revision,
            "comment": comment,
        },
        format="json",
    )


def test_scopes_and_transactional_history(people):
    (owner, peer, outsider), staff = people
    submitted = submit(owner, student_id=peer.pk, status="ready")
    assert submitted.status_code == 201
    ticket = submitted.json()
    assert ticket["status"] == "submitted"
    assert ServiceRequest.objects.get(pk=ticket["id"]).student == owner
    foreign = submit(outsider).json()
    mine = signed_in(owner.user)
    peer_client = signed_in(peer.user)
    queue = signed_in(staff)
    path = f"/api/v1/requests/{ticket['id']}/"
    assert peer_client.get(path).status_code == 404
    assert peer_client.get("/api/v1/requests/").json()["count"] == 0
    assert mine.patch(path, {"status": "ready"}).status_code == 405
    assert transition(mine, ticket["id"], "in_progress").status_code == 403
    assert queue.get("/api/v1/staff/requests/").json()["count"] == 1
    assert queue.get(f"/api/v1/staff/requests/{foreign['id']}/").status_code == 404
    assert transition(queue, foreign["id"], "in_progress").status_code == 404
    assert transition(queue, ticket["id"], "ready").status_code == 400
    assert transition(queue, ticket["id"], "in_progress").status_code == 200
    assert transition(queue, ticket["id"], "ready").status_code == 409
    assert transition(queue, ticket["id"], "rejected", revision=2).status_code == 400
    assert transition(queue, ticket["id"], "ready", revision=2, comment="Готово").status_code == 200
    history = mine.get(path).json()["history"]
    assert [entry["status"] for entry in history] == ["submitted", "in_progress", "ready"]
    assert history[-1]["comment"] == "Готово"
    assert "actor" not in history[-1]
    assert transition(queue, ticket["id"], "rejected", 3, "Поздно").status_code == 400
    StaffProfile.objects.filter(user=staff).delete()
    assert queue.get("/api/v1/staff/requests/").status_code == 403


def test_creation_retry_and_csrf(people):
    (owner, peer, _), _staff = people
    key = str(uuid.uuid4())
    first = submit(owner, request_key=key).json()
    duplicate = submit(owner, request_key=key)
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == first["id"]
    assert len(duplicate.json()["history"]) == 1
    assert submit(owner, request_key=key, text="Другой текст").status_code == 409
    assert submit(peer, request_key=key).status_code == 201
    assert submit(owner, kind="application", text=" ").status_code == 400
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(owner.user)
    assert client.post("/api/v1/requests/", {}, format="json").status_code == 403


def test_notice_audiences_due_time_and_private_read_receipts(people):
    (owner, peer, outsider), staff = people
    now = timezone.now()
    faculty = owner.group.faculty
    Announcement.objects.create(title="Общее", message="Для всех")
    Announcement.objects.create(title="Новости А", message="Для А", faculty=faculty)
    Announcement.objects.create(title="Новости Б", message="Для Б", faculty=outsider.group.faculty)
    Announcement.objects.create(
        title="Будущее", message="Позже", published_at=now + timedelta(days=1)
    )
    ticket = submit(owner).json()
    assert (
        transition(signed_in(staff), ticket["id"], "in_progress", comment="Ответ").status_code
        == 200
    )
    lesson = Lesson.objects.create(
        group=owner.group,
        subject="Перенос пары",
        teacher="Демо",
        room="1",
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
    )
    LessonChange.objects.create(
        lesson=lesson, revision=2, reason="Новая аудитория", before={}, after={}
    )
    teacher = TeacherProfile.objects.create(user=staff, faculty=faculty, full_name="Демо")
    assignment = TeachingAssignment.objects.create(
        group=owner.group,
        teacher=teacher,
        subject="Демо",
        term="1",
    )
    work = AcademicActivity.objects.create(
        assignment=assignment,
        kind="homework",
        title="Дедлайн А",
        due_at=now + timedelta(hours=3),
    )
    owner_client = signed_in(owner.user)
    peer_client = signed_in(peer.user)
    other_client = signed_in(outsider.user)

    def notices(client):
        response = client.get("/api/v1/notifications/")
        assert response.status_code == 200
        return response.json()["results"]

    data = notices(owner_client)
    assert {row["category"] for row in data} == {"news", "schedule", "request", "deadline"}
    assert len({row["key"] for row in data}) == len(data) == 5
    assert len(notices(peer_client)) == 4
    assert {row["headline"] for row in notices(other_client)} == {"Общее", "Новости Б"}
    private = next(row for row in data if row["category"] == "request")
    secret_path = f"/api/v1/notifications/{private['key']}/read/"
    assert peer_client.post(secret_path).status_code == 404
    assert other_client.post(secret_path).status_code == 404
    assert owner_client.post(secret_path).status_code == 204
    assert owner_client.post(secret_path).status_code == 204
    assert NoticeRead.objects.count() == 1
    assert next(row for row in notices(owner_client) if row["key"] == private["key"])["read"]
    old = next(row["key"] for row in data if row["category"] == "deadline")
    work.due_at += timedelta(hours=1)
    work.save(update_fields=["due_at"])
    assert next(row["key"] for row in notices(owner_client) if row["category"] == "deadline") != old
    assert owner_client.post(f"/api/v1/notifications/{old}/read/").status_code == 404
    owner.group = outsider.group
    owner.save(update_fields=["group"])
    assert {row["headline"] for row in notices(owner_client)} == {
        "Общее",
        "Новости Б",
        "Справка об обучении · В работе",
    }


def test_notification_list_is_paginated(people):
    (owner, _, _), _staff = people
    Announcement.objects.bulk_create(
        [Announcement(title=f"Новость {index}", message="Текст") for index in range(30)]
    )
    client = signed_in(owner.user)
    first = client.get("/api/v1/notifications/").json()
    second = client.get("/api/v1/notifications/?page=2").json()
    assert len(first["results"]) == 25 and len(second["results"]) == 5
    assert not {row["key"] for row in first["results"]} & {row["key"] for row in second["results"]}


def test_announcement_publish_uses_staff_faculty(people):
    (owner, _, outsider), staff = people
    payload = {"title": "Новый график", "message": "Демо", "faculty": outsider.group.faculty_id}
    endpoint = "/api/v1/staff/announcements/"
    assert signed_in(owner.user).post(endpoint, payload, format="json").status_code == 403
    response = signed_in(staff).post(endpoint, payload, format="json")
    assert response.status_code == 201
    assert Announcement.objects.get(pk=response.json()["id"]).faculty_id == owner.group.faculty_id
    assert signed_in(owner.user).get("/api/v1/notifications/").json()["count"] == 1
    assert signed_in(outsider.user).get("/api/v1/notifications/").json()["count"] == 0


def test_contest_seed_is_private_repeatable_and_scope_checked(tmp_path):
    from django.core.management import call_command

    path = tmp_path / "jury-access.json"
    call_command("setup_contest_demo", credentials=path)
    original = path.read_bytes()
    call_command("setup_contest_demo", credentials=path)
    assert path.read_bytes() == original
    users = get_user_model().objects
    a = users.get(username="jury_student_a")
    b = users.get(username="jury_student_b")
    office = users.get(username="jury_deanery")
    assert not office.is_staff and not office.is_superuser
    assert a.student_profile.group_id != b.student_profile.group_id
    assert signed_in(a).get("/api/v1/assessments/").json()["count"] == 1
    assert signed_in(b).get("/api/v1/assessments/").json()["count"] == 0
    assert signed_in(b).get("/api/v1/requests/").json()["count"] == 1
    assert signed_in(office).get("/api/v1/staff/requests/").json()["count"] == 0

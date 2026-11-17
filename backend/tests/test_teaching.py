import io
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone

from academics.models import AcademicActivity, Assessment, AssessmentChange, TeachingAssignment
from academics.teaching_services import set_result
from accounts.models import Faculty, StudentProfile, StudyGroup, TeacherProfile, User

pytestmark = pytest.mark.django_db
AUTH = "django.contrib.auth.backends.ModelBackend"


def signed(user, csrf=False):
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user, backend=AUTH)
    return client


@pytest.fixture
def school():
    faculties = [Faculty.objects.create(name=f"Демо-факультет {i}") for i in range(2)]
    groups = [
        StudyGroup.objects.create(
            name=f"ДЕМО-{i}", faculty=faculties[i // 2], programme="ИТ", course=1
        )
        for i in range(3)
    ]
    students = []
    for i, group in enumerate([groups[0], groups[0], groups[1], groups[2]]):
        user = User.objects.create_user(username=f"learner_{i}", password="synthetic-test-only")
        students.append(
            StudentProfile.objects.create(user=user, group=group, full_name=f"Демо {i}")
        )
    teachers, assignments = [], []
    for i, group in enumerate([groups[0], groups[0], groups[2]]):
        user = User.objects.create_user(username=f"teacher_{i}", password="synthetic-test-only")
        profile = TeacherProfile.objects.create(
            user=user, faculty=group.faculty, full_name=f"Демо-преподаватель {i}"
        )
        teachers.append(user)
        assignments.append(
            TeachingAssignment.objects.create(
                teacher=profile,
                group=group,
                subject=f"Демо-предмет {i}",
                term="2026/27 — 1 семестр",
            )
        )
    activity = AcademicActivity.objects.create(
        assignment=assignments[0],
        kind="credit",
        title="Демо-зачёт",
        scheduled_at=timezone.now() + timedelta(days=7),
    )
    client = signed(teachers[0])
    return SimpleNamespace(
        groups=groups,
        students=students,
        teachers=teachers,
        assignments=assignments,
        activity=activity,
        client=client,
    )


def result_url(activity):
    return f"/api/v1/teaching/activities/{activity.pk}/results/"


def payload(student, **kwargs):
    return {
        "student": student.pk,
        "expected_revision": 0,
        "status": "graded",
        "score": 5,
        "comment": "Демо-результат",
        **kwargs,
    }


def test_teacher_role_is_explicit_and_login_targets_cabinet(school):
    me = school.client.get("/api/v1/me/").json()
    assert me["roles"] == ["teacher"]
    assert me["teacher_profile"]["full_name"] == "Демо-преподаватель 0"
    assert school.client.get("/admin/").status_code == 302
    assert (
        school.client.patch(
            "/api/v1/me/", {"roles": ["deanery_staff"]}, content_type="application/json"
        ).status_code
        == 405
    )
    client = Client()
    assert (
        client.post("/auth/login/", {"username": "teacher_0", "password": "synthetic-test-only"})[
            "Location"
        ]
        == "/teaching"
    )
    assert (
        Client().post(
            "/auth/login/",
            {"username": "teacher_0", "password": "synthetic-test-only", "next": "/profile"},
        )["Location"]
        == "/profile"
    )
    assert (
        Client().post(
            "/auth/login/",
            {
                "username": "teacher_0",
                "password": "synthetic-test-only",
                "next": "https://example.invalid",
            },
        )["Location"]
        == "/teaching"
    )


def test_teacher_and_student_have_separate_scopes(school):
    assert signed(school.students[0].user).get("/api/v1/teaching/assignments/").status_code == 403
    assert school.client.get("/api/v1/assessments/").status_code == 403
    assert Client().get("/api/v1/teaching/assignments/").status_code == 403
    technical = User.objects.create_user(username="technical", is_staff=True, is_superuser=True)
    assert signed(technical).get("/api/v1/teaching/assignments/").status_code == 403
    StudentProfile.objects.create(user=school.teachers[0], group=school.groups[2], full_name="Демо")
    assert school.client.get("/api/v1/me/").json()["roles"] == ["student", "teacher"]
    assert school.client.get("/api/v1/activities/").json()["count"] == 0
    assert school.client.get("/api/v1/teaching/activities/").json()["count"] == 1


def test_teacher_assignment_roster_and_activity_scope(school):
    own = school.client.get("/api/v1/teaching/assignments/").json()["results"]
    assert [x["id"] for x in own] == [school.assignments[0].pk]
    roster = school.client.get(f"/api/v1/teaching/activities/{school.activity.pk}/students/").json()
    assert {x["id"] for x in roster["results"]} == {s.pk for s in school.students[:2]}
    other = signed(school.teachers[1])  # same faculty and group still does not grant this subject.
    assert other.get(f"/api/v1/teaching/activities/{school.activity.pk}/").status_code == 404
    assert other.get(result_url(school.activity)).status_code == 404
    assert (
        other.get(f"/api/v1/teaching/activities/{school.activity.pk}/students/").status_code == 404
    )
    assert (
        other.post(
            result_url(school.activity),
            payload(school.students[0]),
            content_type="application/json",
        ).status_code
        == 404
    )


@pytest.mark.parametrize("kind", ["homework", "test", "credit", "exam"])
def test_create_and_reschedule_activity(school, kind):
    when = timezone.now() + timedelta(days=5)
    data = {
        "assignment": school.assignments[0].pk,
        "kind": kind,
        "title": "Демо-работа",
        "description": "Только вымышленные данные",
        "scheduled_at": when.isoformat(),
        "due_at": (when + timedelta(days=1)).isoformat(),
        "room": "ДЕМО-10",
    }
    response = school.client.post(
        "/api/v1/teaching/activities/", data, content_type="application/json"
    )
    assert response.status_code == 201, response.content
    obj = response.json()
    url = f"/api/v1/teaching/activities/{obj['id']}/"
    response = school.client.patch(
        url,
        {"expected_revision": 1, "scheduled_at": (when + timedelta(hours=2)).isoformat()},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["revision"] == 2
    assert (
        school.client.patch(
            url, {"expected_revision": 1, "title": "stale"}, content_type="application/json"
        ).status_code
        == 400
    )
    student = signed(school.students[0].user)
    assert obj["id"] in [x["id"] for x in student.get("/api/v1/activities/").json()["results"]]
    assert signed(school.students[2].user).get("/api/v1/activities/").json()["count"] == 0


@pytest.mark.parametrize(
    "extra",
    [
        {"assignment": "foreign"},
        {"kind": "homework", "due_at": None},
        {"kind": "credit", "scheduled_at": None},
        {"title": ""},
    ],
)
def test_invalid_activity_is_rejected(school, extra):
    data = {
        "assignment": school.assignments[0].pk,
        "kind": "credit",
        "title": "Демо",
        "scheduled_at": (timezone.now() + timedelta(days=1)).isoformat(),
    }
    if extra.get("assignment") == "foreign":
        extra = {"assignment": school.assignments[1].pk}
    assert (
        school.client.post(
            "/api/v1/teaching/activities/", {**data, **extra}, content_type="application/json"
        ).status_code
        == 400
    )


def test_activity_grant_and_kind_cannot_be_reassigned(school):
    url = f"/api/v1/teaching/activities/{school.activity.pk}/"
    for data in [{"assignment": school.assignments[1].pk}, {"kind": "exam"}]:
        assert (
            school.client.patch(
                url, {"expected_revision": 1, **data}, content_type="application/json"
            ).status_code
            == 400
        )
    assert school.client.delete(url).status_code == 405


def test_grading_debt_and_retake_are_audited_and_personal(school):
    url = result_url(school.activity)
    response = school.client.post(
        url, payload(school.students[0], status="debt", score=None), content_type="application/json"
    )
    assert response.status_code == 201, response.content
    assert response.json()["is_debt"]
    learner = signed(school.students[0].user)
    assert learner.get("/api/v1/assessments/?debt=true").json()["count"] == 1
    assert signed(school.students[1].user).get("/api/v1/assessments/").json()["count"] == 0
    response = school.client.post(
        url,
        payload(school.students[0], expected_revision=1, status="passed", score=None),
        content_type="application/json",
    )
    assert response.status_code == 200 and not response.json()["is_debt"]
    assert learner.get("/api/v1/assessments/?debt=true").json()["count"] == 0
    assert learner.get("/api/v1/assessments/?debt=false").json()["count"] == 1
    assert learner.get("/api/v1/assessments/?debt=bad").status_code == 400
    assert AssessmentChange.objects.count() == 2
    assert (
        school.client.post(
            url, payload(school.students[0], expected_revision=1), content_type="application/json"
        ).status_code
        == 400
    )
    assert (
        school.client.post(
            url,
            payload(school.students[0], expected_revision=2, status="passed", score=None),
            content_type="application/json",
        ).status_code
        == 200
    )
    assert AssessmentChange.objects.count() == 2  # repeated identical decisions are idempotent.


@pytest.mark.parametrize("status,score", [("graded", 2), ("failed", None), ("debt", None)])
def test_unsatisfactory_results_count_as_debts(school, status, score):
    r = school.client.post(
        result_url(school.activity),
        payload(school.students[0], status=status, score=score),
        content_type="application/json",
    )
    assert r.status_code == 201 and r.json()["is_debt"]


@pytest.mark.parametrize(
    "extra",
    [
        {"score": 6},
        {"score": 1},
        {"score": None},
        {"status": "passed", "score": 4},
        {"status": "unknown"},
    ],
)
def test_invalid_scores_are_rejected(school, extra):
    assert (
        school.client.post(
            result_url(school.activity),
            payload(school.students[0], **extra),
            content_type="application/json",
        ).status_code
        == 400
    )
    assert not Assessment.objects.exists()


def test_cannot_grade_foreign_student_or_cancelled_activity(school):
    assert (
        school.client.post(
            result_url(school.activity),
            payload(school.students[2]),
            content_type="application/json",
        ).status_code
        == 404
    )
    AcademicActivity.objects.filter(pk=school.activity.pk).update(is_cancelled=True)
    assert (
        school.client.post(
            result_url(school.activity),
            payload(school.students[0]),
            content_type="application/json",
        ).status_code
        == 400
    )


def test_real_csrf_is_required_for_teacher_writes(school):
    client = signed(school.teachers[0], csrf=True)
    assert (
        client.post(
            result_url(school.activity),
            payload(school.students[0]),
            content_type="application/json",
        ).status_code
        == 403
    )
    token = client.get("/api/v1/csrf/").json()["csrfToken"]
    r = client.post(
        result_url(school.activity),
        payload(school.students[0]),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert r.status_code == 201
    assert (
        client.post(
            result_url(school.activity),
            payload(school.students[1]),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="https://example.invalid",
        ).status_code
        == 403
    )


def test_grants_are_revoked_on_next_request(school):
    school.assignments[0].is_active = False
    school.assignments[0].save(update_fields=["is_active"])
    assert school.client.get("/api/v1/teaching/activities/").json()["count"] == 0
    assert (
        school.client.post(
            result_url(school.activity),
            payload(school.students[0]),
            content_type="application/json",
        ).status_code
        == 404
    )
    TeacherProfile.objects.filter(user=school.teachers[0]).update(is_active=False)
    assert school.client.get("/api/v1/me/").json()["roles"] == []
    assert school.client.get("/api/v1/teaching/assignments/").status_code == 403


def test_group_transfer_keeps_personal_history_but_removes_teacher_access(school):
    school.client.post(
        result_url(school.activity), payload(school.students[0]), content_type="application/json"
    )
    StudentProfile.objects.filter(pk=school.students[0].pk).update(group=school.groups[1])
    assert school.client.get(result_url(school.activity)).json()["count"] == 0
    assert signed(school.students[0].user).get("/api/v1/assessments/").json()["count"] == 1
    assert (
        school.client.post(
            result_url(school.activity),
            payload(school.students[0], expected_revision=1),
            content_type="application/json",
        ).status_code
        == 404
    )


def test_result_audit_failure_rolls_back_grade(school, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(AssessmentChange.objects, "create", fail)
    data = payload(school.students[0])
    with pytest.raises(RuntimeError):
        set_result(school.teachers[0], school.activity.pk, **data)
    assert not Assessment.objects.exists()


def test_database_rejects_score_for_non_graded_result(school):
    school.client.post(
        result_url(school.activity), payload(school.students[0]), content_type="application/json"
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Assessment.objects.update(status="passed", score=5)


def test_demo_teacher_has_no_admin_rights_and_existing_users_are_not_changed(school):
    output = io.StringIO()
    call_command(
        "create_demo_teacher",
        "demo_teaching_test",
        group=school.groups[0].name,
        generate_password=True,
        stdout=output,
    )
    credentials = json.loads(output.getvalue())
    user = User.objects.get(username=credentials["username"])
    assert user.check_password(credentials["password"])
    assert not user.is_staff and not user.is_superuser
    assert user.teacher_profile.faculty_id == school.groups[0].faculty_id
    assert TeachingAssignment.objects.filter(teacher=user.teacher_profile).count() == 1
    with pytest.raises(CommandError):
        call_command(
            "create_demo_teacher",
            "demo_teaching_test",
            group=school.groups[1].name,
            generate_password=True,
            stdout=io.StringIO(),
        )
    user.refresh_from_db()
    assert user.check_password(credentials["password"])

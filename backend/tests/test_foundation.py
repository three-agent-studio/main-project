import pytest
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import Client
from django.urls import reverse

from accounts.models import Faculty, StudentProfile, StudyGroup


@pytest.fixture
def students(db):
    faculty = Faculty.objects.create(name="Демонстрационный факультет")
    group = StudyGroup.objects.create(name="ДЕМО-1", faculty=faculty, programme="ИТ", course=1)
    result = []
    for name in ("student_a", "student_b"):
        user = get_user_model().objects.create_user(username=name, password="test-password-only")
        StudentProfile.objects.create(user=user, full_name=name, group=group)
        result.append(user)
    return result


def test_health_and_db_failure(client, monkeypatch):
    assert client.get("/health/live/").json() == {"status": "ok"}
    def broken_cursor(*args, **kwargs):
        raise DatabaseError("private database details")
    monkeypatch.setattr("core.views.connection.cursor", broken_cursor)
    response = client.get("/health/ready/")
    assert response.status_code == 503
    assert "private database" not in response.content.decode()


@pytest.mark.django_db
def test_readiness(client):
    assert client.get("/health/ready/").status_code == 200


def test_me_requires_authentication(client):
    response = client.get(reverse("me"))
    assert response.status_code == 403
    assert response.json()["error"]["status"] == 403
    assert "no-store" in response["Cache-Control"]


def test_students_only_get_their_profile(client, students):
    for user in students:
        client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
        response = client.get(reverse("me"), {"user_id": students[1].pk})
        assert response.json()["id"] == user.pk
        assert response.json()["student_profile"]["full_name"] == user.username
        assert client.get(f"/api/v1/users/{students[1].pk}/").status_code == 404
        assert client.patch(reverse("me"), {"is_staff": True}).status_code == 405
        client.logout()


def test_login_logout_csrf_and_password_hashing(students):
    client = Client(enforce_csrf_checks=True)
    user = students[0]
    assert user.password != "test-password-only"
    assert client.post("/auth/login/", {"username": user.username}).status_code == 403
    client.get("/auth/login/")
    response = client.post("/auth/login/", {
        "username": user.username, "password": "test-password-only",
        "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
    })
    assert response.status_code == 302
    assert client.get(reverse("me")).status_code == 200
    assert client.get("/auth/logout/").status_code == 405
    assert client.post("/auth/logout/").status_code == 403
    response = client.post("/auth/logout/", {
        "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
    })
    assert response.status_code == 302
    assert client.get(reverse("me")).status_code == 403


def test_demo_student_command_creates_hashed_password_and_profile(db):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    # Synthetic test-only input. Real provisioning passwords never belong in test fixtures.
    password = "Synthetic-Student-Only-47!"
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("accounts.management.commands.create_demo_student.getpass.getpass",
                      lambda prompt: password)
        call_command("create_demo_student", "demo_local")
        user = get_user_model().objects.get(username="demo_local")
        assert user.check_password(password)
        assert not user.is_staff and not user.is_superuser
        assert user.student_profile.group.name == "ДЕМО-1"
        with pytest.raises(CommandError):
            call_command("create_demo_student", "demo_local")


def test_demo_student_command_rejects_weak_password_without_creating_user(db):
    from django.core.management import call_command
    from django.core.management.base import CommandError
    from django.test import override_settings

    with pytest.MonkeyPatch.context() as patch, override_settings(
        AUTH_PASSWORD_VALIDATORS=[{
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        }]
    ):
        patch.setattr("accounts.management.commands.create_demo_student.getpass.getpass",
                      lambda prompt: "short")
        with pytest.raises(CommandError):
            call_command("create_demo_student", "invalid_demo")
    assert not get_user_model().objects.filter(username="invalid_demo").exists()

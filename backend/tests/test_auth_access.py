"""Authorization regressions exercise real profiles and DB-backed authentication."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from axes.models import AccessAttempt
from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.test import Client, override_settings
from django.utils import timezone

from accounts.access import (
    IsDeaneryStaff,
    require_student,
    scope_faculty_records,
    scope_student_records,
    staff_faculty_id,
)
from accounts.models import Faculty, StaffProfile, StudentProfile, StudyGroup, User

PASSWORD = "Synthetic-Only-Password-47!"
MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"
pytestmark = pytest.mark.django_db


@pytest.fixture
def identities():
    faculty_a = Faculty.objects.create(name="Демонстрационный факультет А")
    faculty_b = Faculty.objects.create(name="Демонстрационный факультет Б")
    group_a = StudyGroup.objects.create(name="ДЕМО-А", faculty=faculty_a, programme="ИТ", course=1)
    group_b = StudyGroup.objects.create(
        name="ДЕМО-Б", faculty=faculty_b, programme="Физика", course=2
    )
    students = []
    for username, group in (("student_a", group_a), ("student_b", group_a), ("student_c", group_b)):
        user = User.objects.create_user(username=username, password=PASSWORD)
        StudentProfile.objects.create(user=user, full_name=f"Вымышленный {username}", group=group)
        students.append(user)
    employee = User.objects.create_user(username="employee", password=PASSWORD)
    StaffProfile.objects.create(user=employee, full_name="Вымышленный сотрудник", faculty=faculty_a)
    return SimpleNamespace(
        a=students[0],
        b=students[1],
        c=students[2],
        employee=employee,
        faculty_a=faculty_a,
        faculty_b=faculty_b,
    )


def login(client, username, password=PASSWORD, **headers):
    client.get("/auth/login/")
    return client.post(
        "/auth/login/",
        {
            "username": username,
            "password": password,
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        },
        **headers,
    )


def test_failed_login_locks_account_across_clients_and_spoofed_headers(identities):
    for number in range(5):
        client = Client(enforce_csrf_checks=True)
        response = login(
            client,
            "student_a",
            "wrong-password",
            REMOTE_ADDR=f"192.0.2.{number + 1}",
            HTTP_X_FORWARDED_FOR=f"198.51.100.{number + 1}",
            HTTP_USER_AGENT=f"agent-{number}",
        )
        assert response.status_code == (429 if number == 4 else 200)
        assert "wrong-password" not in response.content.decode()
    assert response["Retry-After"] == "900"
    assert "no-store" in response["Cache-Control"]
    assert AccessAttempt.objects.filter(username="student_a").exists()
    # A new client simulates a new worker/request; the DB counter must still apply.
    blocked = Client(enforce_csrf_checks=True)
    assert login(blocked, "student_a").status_code == 429
    assert blocked.get("/api/v1/me/").status_code == 403
    assert blocked.get("/auth/login/").status_code == 200
    # Another student behind the same campus connection must still be able to sign in.
    assert login(Client(enforce_csrf_checks=True), "student_b").status_code == 302


def test_whitespace_does_not_bypass_username_lockout(identities):
    for _ in range(5):
        response = login(Client(), "student_a", "wrong-password")
    assert response.status_code == 429
    assert login(Client(), "  student_a  ").status_code == 429


@pytest.mark.parametrize("username", ["student_a", "unknown_student"])
def test_lockout_response_does_not_disclose_account_existence(identities, username):
    client = Client()
    for _ in range(5):
        response = login(client, username, "wrong-password")
    assert response.status_code == 429
    assert "Вход временно ограничен" in response.content.decode()
    assert username not in response.content.decode()


def test_lockout_expires_without_restarting_server(identities):
    client = Client()
    for _ in range(5):
        login(client, "student_a", "wrong-password")
    AccessAttempt.objects.filter(username="student_a").update(
        attempt_time=timezone.now() - timedelta(minutes=16)
    )
    assert login(Client(), "student_a").status_code == 302


def test_success_clears_previous_failures_and_admin_login_is_also_protected(identities):
    client = Client()
    for _ in range(2):
        login(client, "student_a", "wrong-password")
    assert login(client, "student_a").status_code == 302
    assert not AccessAttempt.objects.filter(username="student_a").exists()
    User.objects.create_user(username="technical", password=PASSWORD, is_staff=True)
    for _ in range(5):
        response = Client().post(
            "/admin/login/",
            {
                "username": "technical",
                "password": "wrong-password",
                "next": "/admin/",
            },
        )
    assert response.status_code == 429
    assert login(Client(), "technical").status_code == 429


def test_session_key_rotates_and_logout_cookie_cannot_be_replayed(identities):
    client = Client(enforce_csrf_checks=True)
    session = client.session
    session["pre_login"] = "synthetic-marker"
    session.save()
    anonymous_key = session.session_key
    client.cookies["sessionid"] = anonymous_key
    assert login(client, "student_a").status_code == 302
    authenticated_key = client.cookies["sessionid"].value
    assert authenticated_key != anonymous_key
    assert not Session.objects.filter(session_key=anonymous_key).exists()
    assert (
        client.post(
            "/auth/logout/",
            {
                "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            },
        ).status_code
        == 302
    )
    replay = Client()
    replay.cookies["sessionid"] = authenticated_key
    assert replay.get("/api/v1/me/").status_code == 403
    assert not Session.objects.filter(session_key=authenticated_key).exists()


def test_csrf_is_checked_before_counting_login_failures(identities):
    client = Client(enforce_csrf_checks=True)
    assert (
        client.post(
            "/auth/login/",
            {
                "username": "student_a",
                "password": "wrong-password",
            },
        ).status_code
        == 403
    )
    assert not AccessAttempt.objects.exists()


def test_password_change_and_deactivation_revoke_existing_sessions(identities):
    first, second = Client(), Client()
    first.force_login(identities.a, backend=MODEL_BACKEND)
    second.force_login(identities.a, backend=MODEL_BACKEND)
    identities.a.set_password("Another-Synthetic-Password-82!")
    identities.a.save(update_fields=["password"])
    assert first.get("/api/v1/me/").status_code == 403
    assert second.get("/api/v1/me/").status_code == 403
    first.force_login(identities.a, backend=MODEL_BACKEND)
    identities.a.is_active = False
    identities.a.save(update_fields=["is_active"])
    assert first.get("/api/v1/me/").status_code == 403
    assert login(Client(), "student_a", "Another-Synthetic-Password-82!").status_code == 200


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"])
def test_real_password_hasher_is_used_without_plaintext_storage():
    user = User.objects.create_user(username="hash_example", password=PASSWORD)
    assert user.password.startswith("pbkdf2_sha256$")
    assert user.check_password(PASSWORD)
    assert PASSWORD not in user.password


@pytest.mark.parametrize("next_url", ["https://example.invalid/steal", "//example.invalid/"])
def test_login_does_not_redirect_credentials_to_an_external_site(identities, next_url):
    response = Client().post(
        "/auth/login/",
        {
            "username": "student_a",
            "password": PASSWORD,
            "next": next_url,
        },
    )
    assert response.status_code == 302
    assert response["Location"] == "/profile"


def test_me_is_personal_and_privileges_cannot_be_self_assigned(identities):
    client = Client()
    for user in (identities.a, identities.c):
        client.force_login(user, backend=MODEL_BACKEND)
        data = client.get("/api/v1/me/", {"user_id": identities.employee.pk}).json()
        assert data["username"] == user.username
        assert data["roles"] == ["student"]
        assert data["staff_profile"] is None
        assert data["student_profile"]["faculty"] == user.student_profile.group.faculty.name
        for method in (client.post, client.put, client.patch, client.delete):
            response = method(
                "/api/v1/me/",
                data={
                    "is_staff": True,
                    "is_superuser": True,
                    "roles": ["deanery_staff"],
                    "staff_profile": {"faculty_id": identities.faculty_b.pk},
                },
                content_type="application/json",
            )
            assert response.status_code == 405
        user.refresh_from_db()
        assert not user.is_staff and not user.is_superuser
        assert not StaffProfile.objects.filter(user=user).exists()
        assert client.get(f"/api/v1/users/{identities.employee.pk}/").status_code == 404


def test_employee_me_exposes_only_the_assigned_faculty_and_no_admin_access(identities):
    client = Client()
    assert login(client, "employee").status_code == 302
    data = client.get("/api/v1/me/").json()
    assert data["roles"] == ["deanery_staff"]
    assert data["student_profile"] is None
    assert data["staff_profile"]["faculty_id"] == identities.faculty_a.pk
    assert not identities.employee.is_staff
    assert client.get("/admin/").status_code == 302


def test_personal_querysets_scope_reads_and_writes_and_deny_foreign_ids(identities):
    records = StudentProfile.objects.select_related("group__faculty")
    for user in (identities.a, identities.b, identities.c):
        scoped = scope_student_records(records, user, student_path="")
        assert list(scoped.values_list("user_id", flat=True)) == [user.pk]
        other = identities.c if user.pk != identities.c.pk else identities.a
        with pytest.raises(StudentProfile.DoesNotExist):
            scoped.get(pk=other.student_profile.pk)
        assert scoped.filter(pk=other.student_profile.pk).update(full_name="tampered") == 0
        assert scoped.filter(pk=other.student_profile.pk).delete()[0] == 0
    assert records.count() == 3
    assert not scope_student_records(records, AnonymousUser(), student_path="").exists()
    assert require_student(identities.a).user_id == identities.a.pk
    with pytest.raises(PermissionDenied):
        require_student(identities.employee)


def test_employee_scope_is_explicit_and_does_not_widen_personal_endpoints(identities):
    records = StudentProfile.objects.all()
    assert not scope_student_records(records, identities.employee, student_path="").exists()
    scoped = scope_faculty_records(records, identities.employee, student_path="")
    assert set(scoped.values_list("user_id", flat=True)) == {identities.a.pk, identities.b.pk}
    assert scoped.filter(pk=identities.c.student_profile.pk).update(full_name="tampered") == 0
    with pytest.raises(StudentProfile.DoesNotExist):
        scoped.get(pk=identities.c.student_profile.pk)
    assert IsDeaneryStaff().has_permission(SimpleNamespace(user=identities.employee), None)
    assert not IsDeaneryStaff().has_permission(SimpleNamespace(user=identities.a), None)
    assert not scope_faculty_records(records, identities.a, student_path="").exists()
    assert not scope_faculty_records(records, AnonymousUser(), student_path="").exists()


def test_staff_scope_never_includes_own_student_record_from_another_faculty(identities):
    StudentProfile.objects.create(
        user=identities.employee,
        full_name="Вымышленный учащийся сотрудник",
        group=identities.c.student_profile.group,
    )
    personal = scope_student_records(
        StudentProfile.objects.all(), identities.employee, student_path=""
    )
    faculty = scope_faculty_records(
        StudentProfile.objects.all(), identities.employee, student_path=""
    )
    assert list(personal.values_list("user_id", flat=True)) == [identities.employee.pk]
    assert identities.employee.pk not in faculty.values_list("user_id", flat=True)


def test_admin_flags_do_not_implicitly_grant_business_access_or_role_assignment(identities):
    technical = User.objects.create_user(username="technical", is_staff=True, is_superuser=True)
    assert staff_faculty_id(technical) is None
    assert not IsDeaneryStaff().has_permission(SimpleNamespace(user=technical), None)
    assert not scope_faculty_records(
        StudentProfile.objects.all(), technical, student_path=""
    ).exists()
    staff_admin = admin.site._registry[StaffProfile]
    employee = identities.employee
    employee.is_staff = True
    employee.save(update_fields=["is_staff"])
    request = SimpleNamespace(user=employee)
    assert not staff_admin.has_view_permission(request)
    assert not staff_admin.has_add_permission(request)
    assert not staff_admin.has_change_permission(request)
    assert not staff_admin.has_delete_permission(request)
    assert staff_admin.has_add_permission(SimpleNamespace(user=technical))


def test_role_revocation_and_inactive_users_immediately_lose_scope(identities):
    employee = identities.employee
    _ = employee.staff_profile  # Deliberately prime Django's related-object cache.
    StaffProfile.objects.filter(user=employee).delete()
    assert staff_faculty_id(employee) is None
    assert not IsDeaneryStaff().has_permission(SimpleNamespace(user=employee), None)
    identities.a.is_active = False
    assert not scope_student_records(
        StudentProfile.objects.all(), identities.a, student_path=""
    ).exists()


def test_locked_requests_do_not_extend_cooloff_or_store_passwords(identities):
    client = Client()
    for _ in range(5):
        login(client, "student_a", "wrong-password")
    before = list(AccessAttempt.objects.values_list("pk", "attempt_time", "failures_since_start"))
    assert login(Client(), "student_a").status_code == 429
    after = list(AccessAttempt.objects.values_list("pk", "attempt_time", "failures_since_start"))
    assert before == after
    for attempt in AccessAttempt.objects.all():
        assert "wrong-password" not in attempt.post_data
        assert PASSWORD not in attempt.post_data


def test_unicode_equivalent_username_cannot_bypass_lockout(identities):
    for _ in range(5):
        login(Client(), "student_a", "wrong-password")
    assert login(Client(), "ｓｔｕｄｅｎｔ＿ａ").status_code == 429


def test_valid_csrf_token_from_a_foreign_origin_is_rejected(identities):
    client = Client(enforce_csrf_checks=True)
    assert login(client, "student_a", HTTP_ORIGIN="https://example.invalid").status_code == 403
    assert client.get("/api/v1/me/").status_code == 403
    assert not AccessAttempt.objects.exists()


def test_demo_command_can_provision_two_distinct_profiles(monkeypatch):
    from django.core.management import call_command

    monkeypatch.setattr(
        "accounts.management.commands.create_demo_student.getpass.getpass", lambda prompt: PASSWORD
    )
    call_command("create_demo_student", "local_a", full_name="Вымышленный А", group="ЛОК-А")
    call_command("create_demo_student", "local_b", full_name="Вымышленный Б", group="ЛОК-Б")
    first = User.objects.get(username="local_a")
    second = User.objects.get(username="local_b")
    assert first.student_profile.full_name != second.student_profile.full_name
    assert first.student_profile.group_id != second.student_profile.group_id
    assert first.check_password(PASSWORD) and second.check_password(PASSWORD)
    assert not first.is_staff and not second.is_staff

"""Apply additive migrations with a verified local DB backup and provision a demo teacher.

Run explicitly in the Mac's Terminal. Passwords are generated locally and written
only to ignored mode-600 state; never pass them as command-line arguments.
"""

import argparse
import json
import os
import re
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path

from local_preview_state import atomic_private_json, backup_database
from team_preview import database_environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-env", required=True, type=Path)
    parser.add_argument("--username", default="demo_teacher")
    parser.add_argument(
        "--student",
        default="six_seven",
        help="Existing synthetic student in target group",
    )
    parser.add_argument("--database-container", default="main-project-db-1")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,39}", args.username):
        parser.error("Use an ASCII demo username, 3–40 characters.")
    state = ROOT / ".team-preview"
    state.mkdir(mode=0o700, exist_ok=True)
    state.chmod(0o700)
    credentials_file = state / "teacher-credentials.json"
    if credentials_file.is_symlink():
        raise RuntimeError("Credentials file must not be a symlink.")
    environment = database_environment(args.database_env)
    os.environ.update(environment)
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.development"
    sys.path.insert(0, str(ROOT / "backend"))
    import django

    django.setup()
    from django.core.management import call_command
    from django.test import Client

    from academics.models import TeachingAssignment
    from accounts.models import StudentProfile, TeacherProfile, User
    from accounts.provisioning import create_teacher_account

    student = StudentProfile.objects.select_related("group__faculty").get(
        user__username=args.student
    )
    credentials = json.loads(credentials_file.read_text()) if credentials_file.exists() else None
    user = User.objects.filter(username=args.username).first()
    if credentials and credentials.get("username") != args.username:
        raise RuntimeError("Existing credentials belong to another demo username; not overwriting.")
    if user and (not credentials or not user.check_password(credentials["password"])):
        raise RuntimeError("Username is already in use; existing account was not modified.")
    backup = backup_database(environment, state, args.database_container)
    print(f"Database backup: {backup}")
    if credentials is not None:
        credentials["verified"] = False
        atomic_private_json(credentials_file, credentials)
    call_command("migrate", interactive=False)
    if credentials is None:
        credentials = {
            "username": args.username,
            "password": secrets.token_urlsafe(18),
            "verified": False,
        }
        atomic_private_json(credentials_file, credentials)
    if user is None:
        user = create_teacher_account(
            username=args.username,
            password=credentials["password"],
            group=student.group,
            full_name="Демонстрационный преподаватель",
            subject="Демо: базы данных",
        )
    if user.is_staff or user.is_superuser or not user.is_active:
        raise RuntimeError("Unexpected account permissions or inactive account; not changing them.")
    teacher = TeacherProfile.objects.get(user=user, is_active=True, faculty=student.group.faculty)
    if not TeachingAssignment.objects.filter(
        teacher=teacher,
        group=student.group,
        is_active=True,
        subject="Демо: базы данных",
    ).exists():
        raise RuntimeError("Expected demo teaching assignment is absent; not broadening access.")
    # Verify the actual database through the real authentication and API views.
    # This is an isolated temporary session; logout below does not affect other users.
    client = Client(enforce_csrf_checks=True)
    client.get("/auth/login/")
    from django.conf import settings

    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    response = client.post(
        "/auth/login/",
        {
            "username": args.username,
            "password": credentials["password"],
            "csrfmiddlewaretoken": token,
        },
    )
    if response.status_code != 302 or response["Location"] != "/teaching":
        raise RuntimeError("Teacher login verification failed.")
    me = client.get("/api/v1/me/").json()
    if me.get("roles") != ["teacher"]:
        raise RuntimeError("Teacher role verification failed.")
    client.post(
        "/auth/logout/",
        {"csrfmiddlewaretoken": client.cookies[settings.CSRF_COOKIE_NAME].value},
    )
    credentials["verified"] = True
    credentials["verified_at"] = datetime.now(UTC).isoformat()
    credentials["group"] = student.group.name
    atomic_private_json(credentials_file, credentials)
    print(f"Teacher verified: {args.username}; credentials saved privately in {credentials_file}")


if __name__ == "__main__":
    main()

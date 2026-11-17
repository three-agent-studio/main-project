"""Back up and fill the existing synthetic student's group with engineering lessons.

No accounts, roles, grades or migrations are changed. Run explicitly in the Mac's
Terminal, using the same database .env as the running preview.
"""

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from pathlib import Path

from local_preview_state import atomic_private_json, backup_database
from team_preview import database_environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-env", required=True, type=Path)
    parser.add_argument("--student", default="six_seven")
    parser.add_argument("--weeks", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--week-start", type=date.fromisoformat)
    parser.add_argument("--database-container", default="main-project-db-1")
    parser.add_argument("--refresh-demo-teachers", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    environment = database_environment(args.database_env)
    os.environ.update(environment)
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.development"
    sys.path.insert(0, str(ROOT / "backend"))
    import django

    django.setup()
    from django.core.management import call_command
    from django.test import Client
    from django.utils import timezone

    from accounts.models import StudentProfile

    learner = StudentProfile.objects.select_related("user", "group").get(
        user__username=args.student
    )
    if not learner.group.name.startswith("ДЕМО-"):
        raise RuntimeError("This runner only fills an explicitly synthetic ДЕМО- group.")
    today = timezone.localdate(timezone=timezone.get_default_timezone())
    monday = args.week_start or today - timedelta(days=today.weekday())
    if monday.weekday() != 0 or monday.year >= 9999:
        parser.error("--week-start must be a Monday in the supported date range.")
    try:
        end = monday + timedelta(weeks=args.weeks, days=-1)
    except OverflowError:
        parser.error("The selected date range is too large.")
    state = ROOT / ".team-preview"
    state.mkdir(mode=0o700, exist_ok=True)
    state.chmod(0o700)
    if not args.dry_run:
        atomic_private_json(
            state / "engineering-schedule.json",
            {
                "verified": False,
                "started_at": datetime.now(UTC).isoformat(),
                "group": learner.group.name,
                "from": monday.isoformat(),
                "to": end.isoformat(),
            },
        )
        backup = backup_database(environment, state, args.database_container, label="schedule")
        print(f"Database backup: {backup}")
    output = StringIO()
    call_command(
        "seed_demo_schedule",
        group=learner.group.name,
        profile="engineering",
        weeks=args.weeks,
        week_start=monday,
        dry_run=args.dry_run,
        refresh_demo_teachers=args.refresh_demo_teachers,
        json_output=True,
        stdout=output,
    )
    report = json.loads(output.getvalue())
    if not args.dry_run:
        # Verify the same scoped API used by the browser, including every page.
        # This temporary session neither signs out other users nor resets a password.
        client = Client()
        client.force_login(learner.user, backend="django.contrib.auth.backends.ModelBackend")
        visible = set()
        try:
            for week in range(args.weeks):
                start = monday + timedelta(weeks=week)
                url = f"/api/v1/lessons/?from={start}&to={start + timedelta(days=6)}"
                while url:
                    response = client.get(url)
                    if response.status_code != 200:
                        raise RuntimeError("Schedule API verification failed.")
                    page = response.json()
                    if any(item["group"] != learner.group.name for item in page["results"]):
                        raise RuntimeError("API returned a different group's lessons.")
                    visible.update(item["id"] for item in page["results"])
                    url = page["next"]
        finally:
            client.logout()
        if not set(report["created_ids"] + report["updated_ids"]).issubset(visible):
            raise RuntimeError("New lessons are absent from the student's schedule API.")
        report["verified"] = True
        report["visible_count"] = len(visible)
        report["verified_at"] = datetime.now(UTC).isoformat()
        atomic_private_json(state / "engineering-schedule.json", report)
    print(
        f"Engineering schedule {monday} — {end}: created={report['created']}, "
        f"existing={report['existing']}, conflicts={report['conflicts']}, "
        f"planned={report['planned']}, subjects={len(report['subjects'])}, "
        f"teachers_updated={report['teachers_updated']}, "
        f"verified={report.get('verified', False)}"
    )


if __name__ == "__main__":
    main()

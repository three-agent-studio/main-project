"""Back up the local Mac preview database, apply migrations and provision jury access."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from local_preview_state import backup_database
from team_preview import database_environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-env", required=True, type=Path)
    parser.add_argument("--database-container", default="main-project-db-1")
    args = parser.parse_args()
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        parser.error("Build frontend first: npm ci && npm run build inside frontend")
    state = ROOT / ".team-preview"
    state.mkdir(mode=0o700, exist_ok=True)
    state.chmod(0o700)
    database = database_environment(args.database_env)
    backup = backup_database(database, state, args.database_container, label="release")
    print(f"Database backup: {backup}", flush=True)
    env = os.environ | database | {"DJANGO_SETTINGS_MODULE": "config.settings.development"}
    manage = [sys.executable, str(ROOT / "backend" / "manage.py")]
    subprocess.run([*manage, "migrate", "--noinput"], env=env, check=True)
    subprocess.run(
        [
            *manage,
            "setup_contest_demo",
            "--credentials",
            str(state / "jury-access.json"),
        ],
        env=env,
        check=True,
    )
    print("Ready to restart the preview.", flush=True)


if __name__ == "__main__":
    main()

"""Run a compiled review site behind a trusted HTTPS tunnel bound to loopback only."""

import argparse
import os
import secrets
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DB_KEYS = {
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
}


def database_environment(path):
    # Parse values, not shell code. Never echo .env contents or include passwords in argv.
    values = {}
    for line in path.read_text().splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key.strip() in DB_KEYS:
            tokens = shlex.split(value, comments=True)
            values[key.strip()] = tokens[0] if tokens else ""
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--origin", required=True, help="Public HTTPS URL printed by the tunnel"
    )
    parser.add_argument("--database-env", type=Path, default=ROOT / ".env")
    parser.add_argument("--port", type=int, default=19090)
    parser.add_argument(
        "--migrate", action="store_true", help="Apply additive DB migrations first"
    )
    args = parser.parse_args()
    origin = urlsplit(args.origin)
    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.path not in ("", "/")
        or origin.username
        or origin.password
        or origin.port
        or origin.query
        or origin.fragment
    ):
        parser.error(
            "Use a plain public HTTPS origin, without credentials or a URL path"
        )
    state = ROOT / ".team-preview"
    state.mkdir(mode=0o700, exist_ok=True)
    key_file = state / "secret.key"
    if not key_file.exists():
        fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(secrets.token_urlsafe(64))
    env = (
        os.environ
        | database_environment(args.database_env)
        | {
            "DJANGO_SETTINGS_MODULE": "config.settings.team_preview",
            "DJANGO_SECRET_KEY": key_file.read_text().strip(),
            "DJANGO_ALLOWED_HOSTS": f"{origin.hostname},127.0.0.1,localhost",
            "CSRF_TRUSTED_ORIGINS": f"https://{origin.hostname}",
        }
    )
    manage = [sys.executable, str(ROOT / "backend" / "manage.py")]
    if args.migrate:
        subprocess.run([*manage, "migrate", "--noinput"], env=env, check=True)
    subprocess.run([*manage, "migrate", "--check"], env=env, check=True)
    subprocess.run([*manage, "collectstatic", "--noinput"], env=env, check=True)
    subprocess.run([*manage, "check"], env=env, check=True)
    os.chdir(ROOT / "backend")
    os.environ.update(env)
    # Do not bind to 0.0.0.0: forwarded headers are trusted only on this local tunnel endpoint.
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "gunicorn",
            "config.wsgi:application",
            "--bind",
            f"127.0.0.1:{args.port}",
            "--workers",
            "2",
            "--error-logfile",
            "-",
        ],
    )


if __name__ == "__main__":
    main()

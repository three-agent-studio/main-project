"""Private local state and checked backups shared by explicit preview commands."""

import json
import os
import secrets
import shutil
import subprocess
from datetime import UTC, datetime


def atomic_private_json(path, data):
    temporary = path.with_name(path.name + "." + secrets.token_hex(6) + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def backup_database(environment, state, container, *, label="teaching"):
    if label not in {"teaching", "schedule", "release"}:
        raise ValueError("Unsupported backup label.")
    host = environment.get("POSTGRES_HOST", "127.0.0.1")
    port = environment.get("POSTGRES_PORT", "5432")
    db = environment.get("POSTGRES_DB", "deanery")
    user = environment.get("POSTGRES_USER", "deanery")
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("This runner only supports the explicitly configured local database.")
    pg_dump = shutil.which("pg_dump")
    if pg_dump:
        command = [
            pg_dump,
            "--host",
            host,
            "--port",
            port,
            "--username",
            user,
            "--dbname",
            db,
            "--format=custom",
            "--no-owner",
            "--no-acl",
        ]
        env = os.environ | {"PGPASSWORD": environment.get("POSTGRES_PASSWORD", "")}
    else:
        # Check the published port before choosing the container, so the backup
        # cannot silently refer to a different PostgreSQL instance.
        published = subprocess.check_output(["docker", "port", container, "5432/tcp"], text=True)
        expected = {
            f"127.0.0.1:{port}",
            f"0.0.0.0:{port}",
            f"[::1]:{port}",
            f"[::]:{port}",
        }
        if not expected.intersection(published.splitlines()):
            raise RuntimeError("Docker PostgreSQL port does not match the configured database.")
        command = [
            "docker",
            "exec",
            container,
            "pg_dump",
            "--username",
            user,
            "--dbname",
            db,
            "--format=custom",
            "--no-owner",
            "--no-acl",
        ]
        env = os.environ.copy()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = state / f"before-{label}-{stamp}-{secrets.token_hex(3)}.dump"
    descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        subprocess.run(command, env=env, stdout=stream, check=True)
    with backup.open("rb") as stream:
        if stream.read(5) != b"PGDMP":
            raise RuntimeError("Backup archive header is invalid; migrations were not applied.")
    return backup

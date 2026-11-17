"""Backup safety checks use disposable archives, never the developer's database."""

import importlib.util
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "local_preview_state", ROOT / "scripts/local_preview_state.py"
)
provision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provision)


def test_private_credentials_are_atomic_and_not_world_readable(tmp_path):
    target = tmp_path / "credentials.json"
    provision.atomic_private_json(target, {"username": "synthetic", "password": "test-only"})
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    provision.atomic_private_json(target, {"username": "synthetic", "verified": True})
    assert "password" not in target.read_text()
    assert list(tmp_path.iterdir()) == [target]


def test_wrong_database_target_stops_before_dump(monkeypatch, tmp_path):
    monkeypatch.setattr(provision.shutil, "which", lambda _: None)
    monkeypatch.setattr(provision.subprocess, "check_output", lambda *a, **k: "127.0.0.1:5433\n")
    with pytest.raises(RuntimeError, match="port does not match"):
        provision.backup_database({}, tmp_path, "synthetic-container")
    assert not list(tmp_path.iterdir())
    with pytest.raises(RuntimeError, match="local database"):
        provision.backup_database(
            {"POSTGRES_HOST": "remote.example"}, tmp_path, "synthetic-container"
        )


def test_backup_header_and_permissions_are_verified(monkeypatch, tmp_path):
    monkeypatch.setattr(provision.shutil, "which", lambda _: None)
    monkeypatch.setattr(provision.subprocess, "check_output", lambda *a, **k: "127.0.0.1:5432\n")

    def dump(command, *, env, stdout, check):
        assert "pg_dump" in command and check
        stdout.write(b"PGDMPsynthetic-test-only")

    monkeypatch.setattr(provision.subprocess, "run", dump)
    archive = provision.backup_database({}, tmp_path, "synthetic-container")
    assert stat.S_IMODE(archive.stat().st_mode) == 0o600
    schedule_archive = provision.backup_database(
        {}, tmp_path, "synthetic-container", label="schedule"
    )
    assert schedule_archive.name.startswith("before-schedule-")
    with pytest.raises(ValueError, match="Unsupported backup label"):
        provision.backup_database({}, tmp_path, "synthetic-container", label="../invalid")
    monkeypatch.setattr(provision.subprocess, "run", lambda *a, **k: None)
    with pytest.raises(RuntimeError, match="header is invalid"):
        provision.backup_database({}, tmp_path, "synthetic-container")

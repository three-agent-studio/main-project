"""Exercise tunnel output handling without opening a network connection."""

import importlib.util
import os
from pathlib import Path

import pytest


def load_launcher():
    path = Path(__file__).resolve().parents[2] / "scripts/share_preview.py"
    spec = importlib.util.spec_from_file_location("share_preview", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rotation_in_buffered_output_updates_origin_and_cleans_up(monkeypatch, tmp_path):
    launcher = load_launcher()
    (tmp_path / "frontend/dist").mkdir(parents=True)
    (tmp_path / "frontend/dist/index.html").write_text("compiled")
    (tmp_path / ".env").touch()
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher.sys, "argv", ["share_preview"])
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    monkeypatch.setattr(launcher.signal, "signal", lambda *args: None)
    servers = []
    calls = []

    class Server:
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            self.returncode = 0

        def wait(self, **kwargs):
            return self.returncode

    read_fd, write_fd = os.pipe()
    # All lines arrive in a single chunk, as happens with buffered SSH banners.
    os.write(
        write_fd,
        b"banner\nhttps://first.lhr.life\nhttps://first.lhr.life\nhttps://second.lhr.life\n",
    )
    os.close(write_fd)

    class Tunnel(Server):
        stdout = os.fdopen(read_fd, "rb", buffering=0)

        def poll(self):
            return 0 if len(servers) == 2 else None

        def wait(self, **kwargs):
            return 0

    tunnel = Tunnel()

    def spawn(argv, **kwargs):
        if argv[0] == "ssh":
            return tunnel
        calls.append(argv)
        process = Server()
        servers.append(process)
        return process

    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    try:
        with pytest.raises(SystemExit) as result:
            launcher.main()
        assert result.value.code == 1
        assert [call[call.index("--origin") + 1] for call in calls] == [
            "https://first.lhr.life",
            "https://second.lhr.life",
        ]
        assert all(server.returncode == 0 for server in servers)
    finally:
        tunnel.stdout.close()

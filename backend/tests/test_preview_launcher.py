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


@pytest.mark.parametrize(
    "provider,domain", [("localhost-run", "lhr.life"), ("serveo", "serveo.net")]
)
def test_rotation_in_buffered_output_updates_origin_and_cleans_up(
    monkeypatch, tmp_path, provider, domain
):
    launcher = load_launcher()
    (tmp_path / "frontend/dist").mkdir(parents=True)
    (tmp_path / "frontend/dist/index.html").write_text("compiled")
    (tmp_path / ".env").touch()
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher.sys, "argv", ["share_preview", "--provider", provider])
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
        (
            "banner\n"
            + "".join(
                f"Forwarding HTTP traffic from https://{name}.{domain}\n"
                for name in ["first", "first", "second"]
            )
        ).encode(),
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
            # Require the proxy contract explicitly; TLS terminates at the tunnel service.
            if provider == "localhost-run":
                assert argv[-2:] == ["--", "--inject-http-proxy-headers"]
            else:
                assert argv[-5:] == ["-p", "22", "--", "serveo.net", "--https-only"]
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
            f"https://first.{domain}",
            f"https://second.{domain}",
        ]
        assert all(server.returncode == 0 for server in servers)
    finally:
        tunnel.stdout.close()


@pytest.mark.parametrize("provider", ["localhost-run", "serveo"])
def test_openssh_parses_actual_command_without_connecting(tmp_path, provider):
    import shutil
    import subprocess

    if shutil.which("ssh") is None:
        pytest.skip("OpenSSH is not installed")
    command = load_launcher().tunnel_command(provider, tmp_path, 19090)
    # -G prints configuration without a connection; -F disables user config/Match exec.
    result = subprocess.run(
        [command[0], "-G", "-F", os.devnull, *command[1:]],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    if provider == "serveo":
        assert "batchmode no" in result.stdout
        assert "preferredauthentications keyboard-interactive" in result.stdout

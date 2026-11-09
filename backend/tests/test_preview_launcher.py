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
def test_buffered_ssh_output_is_drained_even_after_process_exit(provider, domain):
    from collections import deque
    from io import StringIO
    from types import SimpleNamespace

    launcher = load_launcher()
    read_fd, write_fd = os.pipe()
    data = (
        "banner\n"
        + "".join(
            f"Forwarding HTTP traffic from https://{name}.{domain}\n"
            for name in ["first", "first", "second"]
        )
        + "Port forwarding expired\n"
    )
    os.write(write_fd, data.encode())
    os.close(write_fd)
    output = deque(maxlen=12)
    with os.fdopen(read_fd, "rb", buffering=0) as stream:
        tunnel = SimpleNamespace(stdout=stream, poll=lambda: 0)
        urls = list(launcher.connection_urls(tunnel, provider, lambda: True, StringIO(), output))
    assert urls == [f"https://{name}.{domain}" for name in ["first", "first", "second"]]
    assert "expired" in output[-1]


@pytest.fixture
def supervisor(monkeypatch, tmp_path):
    import io
    from types import SimpleNamespace

    launcher = load_launcher()
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    clock = SimpleNamespace(now=0)
    delays = []
    monkeypatch.setattr(
        launcher,
        "time",
        SimpleNamespace(
            monotonic=lambda: clock.now,
            sleep=delays.append,
        ),
    )
    servers, tunnels = [], []

    class Process:
        returncode = None

        def __init__(self):
            self.stdout = io.BytesIO()

        def poll(self):
            return self.returncode

        def terminate(self):
            self.returncode = 0

        def wait(self, **kwargs):
            return self.returncode

    def spawn(argv, **kwargs):
        process = Process()
        (tunnels if argv[0] == "ssh" else servers).append((argv, process))
        return process

    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    args = SimpleNamespace(
        identity_file=None,
        hostname=None,
        ssh_verbose=False,
        provider="serveo",
        database_env=tmp_path / ".env",
        port=19090,
    )
    return SimpleNamespace(
        module=launcher,
        state=tmp_path,
        args=args,
        log=io.StringIO(),
        clock=clock,
        delays=delays,
        servers=servers,
        tunnels=tunnels,
    )


def test_expired_tunnel_reconnects_without_restarting_same_origin_server(supervisor, monkeypatch):
    import json

    fixture = supervisor
    sessions = []
    origins = ["https://same.serveo.net", "https://same.serveo.net", "https://changed.serveo.net"]

    def urls(tunnel, provider, healthy, log, output):
        assert healthy()
        index = len(sessions)
        sessions.append(tunnel)
        yield origins[index]
        fixture.clock.now += 61
        if len(sessions) == len(origins):
            raise KeyboardInterrupt
        output.append("Port forwarding expired")

    monkeypatch.setattr(fixture.module, "connection_urls", urls)
    fixture.module.supervise(fixture.args, fixture.state, fixture.log)
    assert len(fixture.tunnels) == 3
    assert len(fixture.servers) == 2
    assert fixture.delays == [3, 3]
    assert all(process.returncode == 0 for _, process in fixture.servers + fixture.tunnels)
    status = json.loads((fixture.state / "status.json").read_text())
    assert status["phase"] == "stopped"
    assert status["url"] == origins[-1]


def test_repeated_failures_back_off_and_stop(supervisor, monkeypatch):
    import json

    fixture = supervisor
    monkeypatch.setattr(fixture.module, "connection_urls", lambda *args: iter(()))
    with pytest.raises(SystemExit) as result:
        fixture.module.supervise(fixture.args, fixture.state, fixture.log)
    assert result.value.code == 1
    assert len(fixture.tunnels) == 5
    assert not fixture.servers
    assert fixture.delays == [6, 12, 24, 30]
    assert json.loads((fixture.state / "status.json").read_text())["phase"] == "failed"


def test_authentication_failure_is_not_retried(supervisor, monkeypatch):
    fixture = supervisor

    def denied(tunnel, provider, healthy, log, output):
        output.append("Permission denied (publickey)")
        return iter(())

    monkeypatch.setattr(fixture.module, "connection_urls", denied)
    with pytest.raises(SystemExit):
        fixture.module.supervise(fixture.args, fixture.state, fixture.log)
    assert len(fixture.tunnels) == 1
    assert not fixture.delays


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


def test_reserved_hostname_uses_only_dedicated_public_key(tmp_path):
    import shutil
    import subprocess

    if shutil.which("ssh") is None:
        pytest.skip("OpenSSH is not installed")
    identity = tmp_path / "dedicated_key"
    identity.touch(mode=0o600)
    command = load_launcher().tunnel_command(
        "serveo",
        tmp_path,
        19090,
        identity,
        "deanery.serveousercontent.com",
    )
    assert command[command.index("-R") + 1] == "deanery.serveousercontent.com:80:127.0.0.1:19090"
    result = subprocess.run(
        [command[0], "-G", "-F", os.devnull, *command[1:]],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert "batchmode no" in result.stdout
    assert "preferredauthentications publickey,keyboard-interactive" in result.stdout
    assert f"identityfile {identity}" in result.stdout


def test_reserved_hostname_never_silently_switches_to_another_domain(supervisor, monkeypatch):
    fixture = supervisor
    fixture.args.hostname = "reserved.serveousercontent.com"
    fixture.args.identity_file = fixture.state / "dedicated_key"
    monkeypatch.setattr(
        fixture.module,
        "connection_urls",
        lambda *args: iter(
            [
                "https://unexpected.serveousercontent.com",
            ]
        ),
    )
    with pytest.raises(SystemExit):
        fixture.module.supervise(fixture.args, fixture.state, fixture.log)
    assert not fixture.servers
    assert not fixture.delays


@pytest.mark.parametrize(
    "hostname",
    [
        "https://deanery.serveousercontent.com",
        "deanery.example.org",
        "deanery.serveousercontent.com/path",
        "-oProxyCommand=invalid",
    ],
)
def test_reserved_hostname_validation_precedes_network_or_server_start(
    tmp_path, monkeypatch, hostname
):
    launcher = load_launcher()
    key = tmp_path / "dedicated_key"
    key.touch(mode=0o600)
    monkeypatch.setattr(
        launcher.sys,
        "argv",
        [
            "share_preview",
            "--provider",
            "serveo",
            "--identity-file",
            str(key),
            "--hostname",
            hostname,
        ],
    )
    with pytest.raises(SystemExit) as result:
        launcher.main()
    assert result.value.code == 2


def test_expiry_message_reconnects_even_when_ssh_stays_alive(monkeypatch):
    from collections import deque
    from io import StringIO
    from types import SimpleNamespace

    launcher = load_launcher()
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"Port forwarding for preview.serveousercontent.com expired\n")

    class Selector:
        calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def register(self, *args):
            pass

        def select(self, **kwargs):
            self.calls += 1
            assert self.calls == 1, "An expired forward must not wait for SSH to exit"
            return [(SimpleNamespace(fileobj=stream), 1)]

    monkeypatch.setattr(launcher.selectors, "DefaultSelector", Selector)
    try:
        with os.fdopen(read_fd, "rb", buffering=0) as stream:
            tunnel = SimpleNamespace(stdout=stream, poll=lambda: None)
            assert (
                list(
                    launcher.connection_urls(
                        tunnel,
                        "serveo",
                        lambda: True,
                        StringIO(),
                        deque(maxlen=12),
                    )
                )
                == []
            )
    finally:
        os.close(write_fd)


def test_verbose_diagnostics_reach_the_ssh_process(supervisor, monkeypatch):
    fixture = supervisor
    fixture.args.ssh_verbose = True
    monkeypatch.setattr(fixture.module, "connection_urls", lambda *args: iter(()))
    with pytest.raises(SystemExit):
        fixture.module.supervise(fixture.args, fixture.state, fixture.log)
    assert fixture.tunnels
    assert all("-v" in command for command, _ in fixture.tunnels)

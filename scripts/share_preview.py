"""Share this checkout over HTTPS; keep this process running while the team reviews it."""

import argparse
import os
import re
import selectors
import signal
import subprocess
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Only accept provider-owned hostnames from SSH output, never arbitrary shell commands.
PUBLIC_URLS = {
    "localhost-run": re.compile(
        r"https://[a-z0-9-]+\.(?:lhr\.life|localhost\.run)(?=\s|$)"
    ),
    "serveo": re.compile(
        r"https://[a-z0-9-]+\.(?:serveo\.net|serveousercontent\.com)(?=\s|$|\x1b)"
    ),
}


def tunnel_command(provider, state, port):
    remote = (
        ["nokey@localhost.run", "--", "--inject-http-proxy-headers"]
        if provider == "localhost-run"
        # OpenSSH parses options after the host too unless '--' precedes it.
        else [
            "-o",
            "PreferredAuthentications=keyboard-interactive",
            "-p",
            "22",
            "--",
            "serveo.net",
            "--https-only",
        ]
    )
    return [
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes" if provider == "localhost-run" else "BatchMode=no",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"UserKnownHostsFile={state / 'known_hosts'}",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "IdentityAgent=none",
        "-o",
        "IdentitiesOnly=yes",
        "-R",
        f"80:127.0.0.1:{port}",
        *remote,
    ]


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-env", type=Path, default=ROOT / ".env")
    parser.add_argument("--port", type=int, default=19090)
    parser.add_argument("--provider", choices=PUBLIC_URLS, default="localhost-run")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use an unprivileged port between 1024 and 65535")
    if not args.database_env.is_file():
        parser.error("Database .env file not found; pass --database-env PATH")
    if not (ROOT / "frontend/dist/index.html").is_file():
        parser.error("Build frontend first: cd frontend && npm ci && npm run build")
    state = ROOT / ".team-preview"
    state.mkdir(mode=0o700, exist_ok=True)
    server = tunnel = awake = None
    origin = None
    recent_output = deque(maxlen=12)
    log_file = os.fdopen(
        os.open(state / "tunnel.log", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w"
    )

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        # A dedicated known_hosts file preserves SSH host verification between launches.
        # nokey needs no service account; its public URL can rotate after a few hours.
        tunnel = subprocess.Popen(
            tunnel_command(args.provider, state, args.port),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if sys.platform == "darwin":
            awake = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        pending = ""
        with selectors.DefaultSelector() as events:
            events.register(tunnel.stdout, selectors.EVENT_READ)
            while tunnel.poll() is None:
                if server is not None and server.poll() is not None:
                    raise RuntimeError(
                        f"Preview server stopped (exit {server.returncode})."
                    )
                for event, _ in events.select(timeout=1):
                    chunk = os.read(event.fileobj.fileno(), 65536)
                    if not chunk:
                        continue
                    pending += chunk.decode(errors="replace")
                    log_file.write(chunk.decode(errors="replace"))
                    log_file.flush()
                    lines = pending.split("\n")
                    pending = lines.pop()
                    for line in lines:
                        recent_output.append(line.strip())
                        if line.startswith("ssh:") or "Permission denied" in line:
                            print(line.strip(), file=sys.stderr, flush=True)
                        if (
                            args.provider == "serveo"
                            and "Forwarding HTTP traffic" not in line
                        ):
                            continue
                        match = PUBLIC_URLS[args.provider].search(line)
                        if not match or match.group() == origin:
                            continue
                        origin = match.group()
                        stop(server)
                        # Restart only our own server when the free URL rotates. Update both
                        # host validation and CSRF origin together, without wildcard hosts.
                        server = subprocess.Popen(
                            [
                                sys.executable,
                                str(ROOT / "scripts/team_preview.py"),
                                "--origin",
                                origin,
                                "--database-env",
                                str(args.database_env.resolve()),
                                "--port",
                                str(args.port),
                            ],
                        )
                        print(
                            f"Team preview: {origin} (server starting; wait for Gunicorn workers)",
                            flush=True,
                        )
        raise RuntimeError(
            f"HTTPS tunnel ended (exit {tunnel.wait()}); restart this command."
        )
    except RuntimeError as error:
        print(str(error), file=sys.stderr, flush=True)
        # Do not hide the actual SSH failure behind an unhelpful exit code 255.
        print("\n".join(recent_output), file=sys.stderr, flush=True)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        print("Stopping team preview.", flush=True)
    finally:
        stop(server)
        stop(tunnel)
        stop(awake)
        log_file.close()


if __name__ == "__main__":
    main()

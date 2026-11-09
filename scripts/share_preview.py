"""Share this checkout over HTTPS; keep this process running while the team reviews it."""

import argparse
import json
import os
import re
import selectors
import signal
import subprocess
import sys
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

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


def tunnel_command(
    provider, state, port, identity_file=None, hostname=None, verbose=False
):
    # Hosted Serveo can finish login via keyboard-interactive after the key offer.
    # Keep normal method negotiation; do not force publickey-only/BatchMode here.
    remote = (
        ["nokey@localhost.run", "--", "--inject-http-proxy-headers"]
        if provider == "localhost-run"
        # OpenSSH parses options after the host too unless '--' precedes it.
        else [
            "-o",
            "PreferredAuthentications=publickey,keyboard-interactive"
            if identity_file
            else "PreferredAuthentications=keyboard-interactive",
            "-p",
            "22",
            "--",
            "serveo.net",
            "--https-only",
        ]
    )
    forward = f"{hostname}:80:127.0.0.1:{port}" if hostname else f"80:127.0.0.1:{port}"
    return [
        "ssh",
        *(["-v"] if verbose else []),
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
        *(["-i", str(identity_file.resolve())] if identity_file else []),
        "-R",
        forward,
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


def write_status(state, phase, origin):
    # Local operational state only; neither credentials nor database data belong here.
    target = state / "status.json"
    temporary = state / "status.tmp"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(
            {
                "phase": phase,
                "url": origin,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            stream,
        )
    os.replace(temporary, target)


def connection_urls(tunnel, provider, server_is_running, log_file, recent_output):
    """Drain every buffered SSH line, including its final expiry message before exit."""
    pending = ""
    with selectors.DefaultSelector() as events:
        events.register(tunnel.stdout, selectors.EVENT_READ)
        while True:
            if not server_is_running():
                raise RuntimeError(
                    "Preview server stopped; fix the server error before reconnecting."
                )
            ready = events.select(timeout=1)
            if not ready and tunnel.poll() is not None:
                break
            for event, _ in ready:
                chunk = os.read(event.fileobj.fileno(), 65536)
                if not chunk:
                    # The caller reaps its own SSH child even if poll() lags EOF.
                    return
                decoded = chunk.decode(errors="replace")
                log_file.write(decoded)
                log_file.flush()
                pending += decoded
                lines = pending.split("\n")
                pending = lines.pop()
                for line in lines:
                    recent_output.append(line.strip())
                    # Some providers expire the forward before closing SSH itself.
                    # A live SSH process is then no evidence of a working public site.
                    if re.search(r"Port forwarding for [a-zA-Z0-9.-]+ expired", line):
                        return
                    if line.startswith("ssh:") or "Permission denied" in line:
                        print(line.strip(), file=sys.stderr, flush=True)
                    if provider == "serveo" and "Forwarding HTTP traffic" not in line:
                        continue
                    if match := PUBLIC_URLS[provider].search(line):
                        yield match.group()


def supervise(args, state, log_file):
    server = tunnel = awake = None
    origin = None
    failures = 0
    recent_output = deque(maxlen=12)
    fatal_errors = (
        "REMOTE HOST IDENTIFICATION HAS CHANGED",
        "Host key verification failed",
        "Permission denied",
        "illegal option",
        "Bad configuration option",
    )

    def server_is_running():
        return server is None or server.poll() is None

    try:
        if sys.platform == "darwin":
            awake = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        while True:
            write_status(state, "connecting", origin)
            recent_output.clear()
            started = time.monotonic()
            log_file.write(
                f"\n[{datetime.now(UTC).isoformat()}] Connecting {args.provider}\n"
            )
            log_file.flush()
            assigned = False
            tunnel = subprocess.Popen(
                tunnel_command(
                    args.provider,
                    state,
                    args.port,
                    args.identity_file,
                    args.hostname,
                    args.ssh_verbose,
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            try:
                for public_url in connection_urls(
                    tunnel,
                    args.provider,
                    server_is_running,
                    log_file,
                    recent_output,
                ):
                    if args.hostname and urlsplit(public_url).hostname != args.hostname:
                        raise RuntimeError(
                            "Provider returned a different hostname than the reserved one."
                        )
                    assigned = True
                    # Preserve the process and its sessions on same-domain reconnects.
                    # A changed host must update both host validation and CSRF together.
                    if public_url != origin:
                        if origin is not None:
                            print(
                                f"Public address changed: {origin} -> {public_url}",
                                flush=True,
                            )
                        stop(server)
                        origin = public_url
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
                            ]
                        )
                    write_status(state, "tunnel_connected", origin)
                    print(
                        f"Team preview: {origin} (wait for Gunicorn workers on first start)",
                        flush=True,
                    )
            finally:
                stop(tunnel)
                tunnel.stdout.close()
            details = "\n".join(recent_output)
            if any(message in details for message in fatal_errors):
                raise RuntimeError(
                    f"SSH configuration/authentication error:\n{details}"
                )
            # A normal long-lived session expiring is recoverable. Repeated rapid
            # failures have bounded exponential backoff; never spin on a broken setup.
            failures = (
                0 if assigned and time.monotonic() - started >= 60 else failures + 1
            )
            if failures >= 5:
                raise RuntimeError(f"SSH failed 5 consecutive times:\n{details}")
            delay = min(3 * 2**failures, 30)
            write_status(state, "reconnecting", origin)
            log_file.write(
                f"\n[{datetime.now(UTC).isoformat()}] Reconnecting in {delay}s\n"
            )
            log_file.flush()
            print(
                f"HTTPS tunnel ended; reconnecting in {delay}s. Last address: {origin}",
                flush=True,
            )
            time.sleep(delay)
    except KeyboardInterrupt:
        print("Stopping team preview.", flush=True)
        write_status(state, "stopped", origin)
    except (RuntimeError, OSError) as error:
        write_status(state, "failed", origin)
        print(str(error), file=sys.stderr, flush=True)
        raise SystemExit(1) from None
    finally:
        stop(server)
        stop(tunnel)
        stop(awake)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-env", type=Path, default=ROOT / ".env")
    parser.add_argument("--port", type=int, default=19090)
    parser.add_argument("--provider", choices=PUBLIC_URLS, default="localhost-run")
    parser.add_argument(
        "--identity-file",
        type=Path,
        help="Dedicated SSH private key registered with Serveo",
    )
    parser.add_argument(
        "--hostname", help="Reserved Serveo hostname from your own console"
    )
    parser.add_argument(
        "--ssh-verbose",
        action="store_true",
        help="Save detailed SSH diagnostics in the local tunnel log",
    )
    args = parser.parse_args()
    if args.identity_file and not args.identity_file.is_file():
        parser.error("SSH identity file does not exist")
    if args.hostname:
        args.hostname = args.hostname.lower()
        if args.provider != "serveo" or not args.identity_file:
            parser.error(
                "A reserved hostname requires --provider serveo and --identity-file"
            )
        if not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.(?:serveo\.net|serveousercontent\.com)",
            args.hostname,
        ):
            parser.error("Use the reserved Serveo hostname without a scheme or path")
    if not 1024 <= args.port <= 65535:
        parser.error("Use an unprivileged port between 1024 and 65535")
    if not args.database_env.is_file():
        parser.error("Database .env file not found; pass --database-env PATH")
    if not (ROOT / "frontend/dist/index.html").is_file():
        parser.error("Build frontend first: cd frontend && npm ci && npm run build")
    state = ROOT / ".team-preview"
    state.mkdir(mode=0o700, exist_ok=True)

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    fd = os.open(state / "tunnel.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as log_file:
        supervise(args, state, log_file)


if __name__ == "__main__":
    main()

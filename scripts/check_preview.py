"""Compare public preview assets with this build, without cookies or account data."""

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin", help="Current HTTPS link printed by share_preview.py")
    args = parser.parse_args()
    origin = urlsplit(args.origin)
    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.username
        or origin.password
        or origin.path not in ("", "/")
        or origin.query
        or origin.fragment
    ):
        parser.error("Pass a plain public HTTPS origin")
    base = args.origin.rstrip("/")
    dist = ROOT / "frontend/dist"
    index = (dist / "index.html").read_text()
    paths = ["/", *re.findall(r'(?:src|href)="(/assets/[^\"]+)"', index)]
    results = []
    state = ROOT / ".team-preview"
    state.mkdir(mode=0o700, exist_ok=True)
    report = state / "asset-check.json"
    with tempfile.TemporaryDirectory(dir=state) as temporary:
        body_path = Path(temporary) / "body"
        for path in paths:
            expected = dist / ("index.html" if path == "/" else path.lstrip("/"))
            item = {"path": path, "expected_bytes": expected.stat().st_size}
            # macOS system curl uses its configured trust store. Never pass -k or
            # disable certificate verification to work around a Python CA setup issue.
            result = subprocess.run(
                [
                    "/usr/bin/curl",
                    "--silent",
                    "--show-error",
                    "--location",
                    "--max-redirs",
                    "5",
                    "--max-time",
                    "30",
                    "--header",
                    "Accept-Encoding: identity",
                    "--output",
                    str(body_path),
                    "--write-out",
                    "%{http_code}\\n%{content_type}\\n%{url_effective}\\n",
                    base + path,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                item["error"] = result.stderr.strip()
            else:
                status, content_type, final_url = result.stdout.splitlines()
                content = body_path.read_bytes()
                item.update(
                    status=int(status),
                    final_url=final_url,
                    content_type=content_type,
                    received_bytes=len(content),
                    matches_build=hashlib.sha256(content).digest()
                    == hashlib.sha256(expected.read_bytes()).digest(),
                )
            results.append(item)
            print(json.dumps(item, ensure_ascii=False), flush=True)
            report.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Saved: {report}")


if __name__ == "__main__":
    main()

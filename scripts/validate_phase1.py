#!/usr/bin/env python3
"""Phase 1 foundation validation suite (Milestone 1.11).

Targets a running Compose stack (default localhost). Exit 0 only if all
critical checks pass.

Usage (repo root, stack up):
  python scripts/validate_phase1.py
  python scripts/validate_phase1.py --api http://localhost:8000 --web http://localhost:3000
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
import urllib.error
import urllib.request
from typing import Any


def _request(
    method: str,
    url: str,
    *,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    raw: bytes | None = None,
    content_type: str | None = None,
    timeout: float = 60.0,
) -> tuple[int, Any]:
    hdrs = dict(headers or {})
    body = raw
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    if content_type:
        hdrs["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(payload)
            except json.JSONDecodeError:
                return resp.status, payload
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--web", default="http://localhost:3000")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="ChangeMeAdmin!")
    args = parser.parse_args()

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))

    api = args.api.rstrip("/")
    web = args.web.rstrip("/")

    for path in ("/health", "/ready", "/openapi.json", "/docs", "/api/v1/ping"):
        status, _ = _request("GET", f"{api}{path}")
        check(path, status == 200, f"status={status}")

    status, _ = _request("GET", f"{api}/api/v1/auth/me")
    check("auth denies anonymous /me", status in (401, 403), f"status={status}")

    status, login = _request(
        "POST",
        f"{api}/api/v1/auth/login",
        data={"email": args.email, "password": args.password},
    )
    token = (login.get("data") or {}).get("access_token") if isinstance(login, dict) else None
    check("login", status == 200 and bool(token), f"status={status}")
    if not token:
        _summarize(checks)
        return 1
    auth = {"Authorization": f"Bearer {token}"}

    status, me = _request("GET", f"{api}/api/v1/auth/me", headers=auth)
    email = (me.get("data") or {}).get("email") if isinstance(me, dict) else None
    check("authenticated /me", status == 200 and email == args.email, f"email={email}")

    status, _ = _request("GET", f"{api}/api/v1/documents/catalog?limit=5", headers=auth)
    check("documents catalog", status == 200, f"status={status}")

    status, _ = _request("GET", f"{api}/api/v1/documents/catalog/stats", headers=auth)
    check("catalog stats", status == 200, f"status={status}")

    status, _ = _request("GET", f"{api}/api/v1/sync/status", headers=auth)
    check("sync status", status == 200, f"status={status}")

    status, sync_auth = _request("GET", f"{api}/api/v1/sync/auth/check", headers=auth)
    check("sync auth/check", status == 200, f"data={sync_auth.get('data') if isinstance(sync_auth, dict) else sync_auth}")

    status, discover = _request(
        "POST",
        f"{api}/api/v1/sync/start",
        data={"mode": "discover"},
        headers=auth,
    )
    check(
        "discovery completes without hang",
        status == 200,
        f"status={status} data={discover.get('data') if isinstance(discover, dict) else discover}",
    )

    boundary = f"----Bound{uuid.uuid4().hex}"
    file_body = b"%PDF-1.4 phase1-gate"
    parts = [
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="folder_path"\r\n\r\n'
            f"Motors/Tests\r\n"
        ).encode(),
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; '
            f'filename="phase1-gate.pdf"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode()
        + file_body
        + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    status, upload = _request(
        "POST",
        f"{api}/api/v1/documents/upload",
        headers=auth,
        raw=b"".join(parts),
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    check("document upload to storage+DB", status in (200, 201), f"status={status}")

    status, stats = _request(
        "GET", f"{api}/api/v1/documents/catalog/stats", headers=auth
    )
    total = ((stats.get("data") or {}).get("total") if isinstance(stats, dict) else 0) or 0
    check("catalog non-zero after upload", status == 200 and total >= 1, f"total={total}")

    routes = [
        "/login",
        "/dashboard",
        "/motors",
        "/documents",
        "/graph",
        "/drawings",
        "/maintenance",
        "/compliance",
        "/search",
        "/analytics",
        "/admin",
        "/sync",
        "/copilot",
    ]
    for path in routes:
        status, _ = _request("GET", f"{web}{path}")
        check(f"web {path}", status == 200, f"status={status}")

    return _summarize(checks)


def _summarize(checks: list[tuple[str, bool, str]]) -> int:
    failed = [c for c in checks if not c[1]]
    print("---")
    print(f"TOTAL {len(checks)}  PASS {len(checks) - len(failed)}  FAIL {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

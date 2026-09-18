#!/usr/bin/env python3
"""
r509_preserve_forensics_tail.py — Act 1 of the CEO-ordered act sequence:
PRESERVE the ephemeral worker-forensics ledger tail BEFORE any Space restart.

Background (R508): all six R506 battery runs were LOST to silent worker
failure (6x INCOMPLETE_INFRASTRUCTURE_FAILURE, Art. LXI). The death evidence
(the ledger tail after the 00:09:15Z durable snapshot) exists ONLY in the
Space's ephemeral local ledger and dies with any restart/rebuild. The owner
act ordered: "capture the tail or trigger a durable snapshot" BEFORE any
restart.

THE CAPABILITY DISCOVERY (measured this round, R509): the engine's own
durable snapshot system (toscanini/durable.py::_collect_payload) pushes
sessions.json WHOLESALE to the durable branch runtime-state-hf — and
sessions.json stores each session's opaque owner_key (toscanini/sessions.py).
The six battery sessions' owner capabilities are therefore already durable
bytes at commit 691d8d3d. The owner-scoped per-session diagnostics route
(GET /api/run/{sid}/worker-diagnostics, R463 — no operator key exists) serves
exactly the death evidence: worker log tail + spawn forensics events from the
LIVE ledger + artifact job lines. The R506-part7 conclusion "the live-API
poll leg is permanently closed" was true of the driver's local capability
file, but false of the engine's own durable bytes.

DISCIPLINE:
  - READ-ONLY against the Space: GET routes only. No restart, no rebuild,
    no redeploy, no resubmission, no battery mutation (the forbidden-until-
    1+2 list is respected by construction).
  - ZERO-KEY: owner keys are loaded in-memory from the durable worktree
    bytes and used ONLY as request headers. They are never written to any
    output file, never logged, never pushed anywhere (BS-021). Every
    captured payload is scanned defensively for the key strings before it
    is written; a hit fails the run closed.
  - FAIL-CLOSED same-boot assertion: /api/health must report the same boot
    (boot-1789685856, epoch-exact 2026-09-17T22:57:36Z) before AND after
    the capture. A different boot means the tail is already gone — the
    capture proceeds (to document the post-restore state) but is TYPED
    POST_RESTART (evidence class changed, disclosed).
  - Provenance: every response's raw bytes are sha256-recorded; method,
    endpoints, timestamps, and the durable ref are recorded in a MANIFEST.

Python 3.12, stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SPACE_BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
EXPECTED_BOOT_ID = "boot-1789685856"  # epoch 2026-09-17T22:57:36Z — the battery-loss boot
BATTERY_MANIFEST_SHA = "e9c72c58193f781a6940191427f1726589fb10f8c68787eeaf6fd8bcaf777fe4"
DURABLE_CUSTODY_REF = "691d8d3de95d2e3bf6d20c3702c4f82677c8d63f"

REQUEST_TIMEOUT_S = 25
PAUSE_BETWEEN_REQUESTS_S = 1.0


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def http_get(url: str, owner_key: str | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    if owner_key:
        req.add_header("X-Tosca-Owner", owner_key)
    req.add_header("User-Agent", "r509-preservation-capture/1.0 (read-only)")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except Exception as exc:  # noqa: BLE001 — typed below, never raised past capture
        return 0, json.dumps({"error_type": type(exc).__name__,
                              "error": str(exc)}).encode()


def load_battery_sessions(durable_worktree: Path) -> list[dict]:
    """Load the six battery sessions (id + owner capability) from the
    ENGINE's own durable sessions.json bytes — in-memory only (BS-021:
    nothing here is ever written out)."""
    mirror = json.loads(
        (Path(__file__).resolve().parent.parent / "R506"
         / "BATTERY_SESSIONS_REDACTED.json").read_text(encoding="utf-8"))
    wanted = {s["session_id"]: s for s in mirror["submissions"]}
    data = json.loads((durable_worktree / "sessions.json").read_text(
        encoding="utf-8"))
    sessions = data.get("sessions", [])
    if isinstance(sessions, dict):
        sessions = list(sessions.values())
    out = []
    for s in sessions:
        sid = s.get("session_id")
        if sid in wanted:
            key = s.get("owner_key") or ""
            out.append({
                "session_id": sid,
                "owner_key": key,
                "problem_index": wanted[sid]["problem_index"],
                "declared_family": wanted[sid]["declared_family"],
                "durable_status_at_custody": s.get("status"),
            })
    out.sort(key=lambda r: r["problem_index"])
    if len(out) != 6:
        raise SystemExit(
            f"FAIL-CLOSED: expected 6 battery sessions in durable bytes, "
            f"found {len(out)}")
    missing_keys = [r["session_id"] for r in out if not r["owner_key"]]
    if missing_keys:
        raise SystemExit(
            f"FAIL-CLOSED: owner capability absent on durable bytes for "
            f"{missing_keys} — the capture cannot proceed owner-scoped")
    return out


def assert_zero_keys(payload_bytes: bytes, keys: list[str], where: str) -> None:
    """BS-021 defensive scan: no owner capability string may appear in any
    byte this script writes."""
    for k in keys:
        if k and k.encode() in payload_bytes:
            raise SystemExit(
                f"FAIL-CLOSED (BS-021): owner-key bytes detected in {where} "
                f"— nothing written, run aborted")


def main() -> int:
    durable_worktree = Path(sys.argv[1] if len(sys.argv) > 1
                            else "/home/z/my-project/r506_durable")
    out_dir = (Path(__file__).resolve().parent.parent / "R509"
               / ("PRESERVATION_" + utcnow().replace(":", "").replace(
                   ".", "")[:-4]))
    out_dir.mkdir(parents=True, exist_ok=True)

    sessions = load_battery_sessions(durable_worktree)
    keys = [r["owner_key"] for r in sessions]
    print(f"[{utcnow()}] loaded {len(sessions)} battery sessions from durable "
          f"bytes (in-memory only); output {out_dir}")

    manifest: dict = {
        "artifact_type": "FORENSICS_TAIL_PRESERVATION",
        "round": "R509",
        "purpose": ("CEO-ordered act 1 (PRESERVE): capture the ephemeral "
                    "worker-forensics ledger tail before any restart"),
        "method": ("read-only GET through the owner-scoped per-session "
                   "diagnostics route (R463) + the live session view, "
                   "capabilities taken from the engine's own durable "
                   "sessions.json bytes (measured discovery, disclosed); "
                   "in-memory only, zero keys written (BS-021)"),
        "space_base": SPACE_BASE,
        "expected_boot_id": EXPECTED_BOOT_ID,
        "durable_custody_ref": DURABLE_CUSTODY_REF,
        "battery_manifest_sha256": BATTERY_MANIFEST_SHA,
        "captured_at_utc": utcnow(),
        "requests": [],
        "same_boot_verified": None,
        "typing": "MEASURED_LIVE",
    }

    # --- pre-probe: /api/version + /api/health (no owner scope needed) ----
    for name, path in (("version_pre", "/api/version"),
                       ("health_pre", "/api/health")):
        code, body = http_get(SPACE_BASE + path)
        assert_zero_keys(body, keys, f"{name}")
        (out_dir / f"{name}.json").write_bytes(body)
        manifest["requests"].append({
            "name": name, "path": path, "status": code,
            "sha256": sha256_bytes(body), "at_utc": utcnow()})
        print(f"[{utcnow()}] {name}: HTTP {code} ({len(body)} bytes)")
        time.sleep(PAUSE_BETWEEN_REQUESTS_S)

    try:
        health_pre = json.loads((out_dir / "health_pre.json").read_text())
        boot_now = (health_pre.get("worker_forensics", {}).get("boot_id")
                    or health_pre.get("boot_id"))
        if boot_now and boot_now != EXPECTED_BOOT_ID:
            manifest["typing"] = "POST_RESTART"
            manifest["same_boot_verified"] = False
            print(f"[{utcnow()}] WARNING: boot changed "
                  f"({boot_now} != {EXPECTED_BOOT_ID}) — typing POST_RESTART")
        else:
            manifest["same_boot_verified"] = True
            print(f"[{utcnow()}] same-boot verified: {boot_now}")
    except Exception as exc:  # noqa: BLE001
        manifest["same_boot_verified"] = "UNVERIFIABLE"
        print(f"[{utcnow()}] boot verification unreadable: {exc}")

    # --- per-session capture (read-only, owner-scoped) --------------------
    for s in sessions:
        sid = s["session_id"]
        sess_result: dict = {
            "session_id": sid,
            "problem_index": s["problem_index"],
            "declared_family": s["declared_family"],
            "durable_status_at_custody": s["durable_status_at_custody"],
            "captures": [],
        }
        for name, url in (
            ("session_view", f"{SPACE_BASE}/api/sessions/{sid}"),
            ("worker_diagnostics",
             f"{SPACE_BASE}/api/run/{sid}/worker-diagnostics"),
        ):
            code, body = http_get(url, owner_key=s["owner_key"])
            assert_zero_keys(body, keys, f"{sid}/{name}")
            fname = f"ts_{s['problem_index']}_{sid}_{name}.json"
            (out_dir / fname).write_bytes(body)
            sess_result["captures"].append({
                "name": name, "url_path": url.replace(SPACE_BASE, ""),
                "http_status": code, "byte_len": len(body),
                "sha256": sha256_bytes(body), "at_utc": utcnow(),
                "file": fname})
            print(f"[{utcnow()}] {sid} {name}: HTTP {code} ({len(body)} bytes)")
            time.sleep(PAUSE_BETWEEN_REQUESTS_S)
        manifest["requests"].append(sess_result)

    # --- post-probe: same-boot assertion AFTER the capture ----------------
    code, body = http_get(SPACE_BASE + "/api/health")
    assert_zero_keys(body, keys, "health_post")
    (out_dir / "health_post.json").write_bytes(body)
    manifest["requests"].append({
        "name": "health_post", "path": "/api/health", "status": code,
        "sha256": sha256_bytes(body), "at_utc": utcnow()})
    try:
        health_post = json.loads(body)
        boot_post = (health_post.get("worker_forensics", {}).get("boot_id")
                     or health_post.get("boot_id"))
        manifest["same_boot_verified"] = (manifest["same_boot_verified"]
                                          and boot_post == EXPECTED_BOOT_ID)
        print(f"[{utcnow()}] post-capture boot: {boot_post}")
    except Exception:  # noqa: BLE001
        pass

    # --- MANIFEST (zero-key by construction, re-scanned defensively) ------
    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False)
    assert_zero_keys(manifest_text.encode(), keys, "MANIFEST")
    (out_dir / "MANIFEST.json").write_text(manifest_text, encoding="utf-8")
    print(f"[{utcnow()}] MANIFEST written; capture COMPLETE "
          f"({len(list(out_dir.iterdir()))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

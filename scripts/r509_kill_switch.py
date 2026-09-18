#!/usr/bin/env python3
"""scripts/r509_kill_switch.py — R509 Phase 3 armament (coder directive):
the per-session kill-switch, armed at submit for battery execution #2.

DESIGN (the directive, verbatim discipline): "if any session passes 2x p90
without durable progression, declare per-session STALLED early, preserve,
and root-cause from fresh evidence — no second 7-hour silent loss. The
kill-switch observes and types; it does not touch workers."

WHAT IT DOES on a per-session STALL declaration (> 82 min without durable
progression while the session is non-terminal-durable; 2x p90=41, the
n=98 measured distribution — Art. XXVII, no invented thresholds):
  1. TYPES the session STALLED_PER_SESSION (an observation, never a
     verdict about the run — Art. LXXIV/XXV).
  2. PRESERVES fresh evidence immediately via the measured-open read-only
     path (R509 act-1 precedent): GET /api/sessions/{sid} and
     GET /api/run/{sid}/worker-diagnostics with the session's own opaque
     owner_key loaded IN-MEMORY from the engine's durable sessions.json
     bytes — never written anywhere (BS-021; every payload is scanned
     against every owner_key string before write; a hit aborts).
  3. RECORDS the typed alert + the preserved evidence path.

WHAT IT NEVER DOES: restart, resubmit, mutate sessions, answer
clarifications, touch workers, deploy, or hold execution state as
authority. The durable branch remains the terminal authority.

Usage:
  --once              single evaluation pass (cron-friendly)
  --loop CADENCE_MIN  continuous watch
  --sessions SID ...  tracked sessions (default: the six R506 battery sids;
                      execution #2 sids are passed at arm time)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE_BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
STALLED_MIN = 82          # 2 x p90(41) — the directive's bound, n=98 measured
TERMINAL_STATUSES = {"COMPLETE", "ERROR_RUN", "ERROR_STUCK", "INTERRUPTED"}
R506_SIDS = [
    "ts_dbdf24c91535", "ts_ca977637f50b", "ts_66e23c67b511",
    "ts_84a8807b12dc", "ts_6da1b9339ce5", "ts_d9b7d3463583",
]


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def S(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {args[:2]}: {r.stderr[:200]}")
    return r.stdout


def durable_snapshot() -> tuple[str | None, dict[str, str | None],
                                list[str], dt.datetime | None]:
    """Fetch the durable branch; return (tip, per-tracked-status,
    owner_keys_in_memory_only, last_event_time)."""
    git("fetch", "origin", "runtime-state-hf")
    tip = git("rev-parse", "origin/runtime-state-hf").strip()
    raw = subprocess.run(["git", "-C", str(REPO), "show",
                          f"{tip}:sessions.json"], capture_output=True)
    data = json.loads(raw.stdout)
    sessions = data.get("sessions", [])
    idx = {e.get("session_id"): e for e in sessions}
    log = git("log", "--format=%ci|-|%s", "-30", "origin/runtime-state-hf")
    last_ev = None
    for line in log.splitlines():
        if "|-|" in line:
            ci, subj = line.split("|-|", 1)
            try:
                last_ev = dt.datetime.fromisoformat(ci.strip().replace("Z", "+00:00").split(".")[0] + "+00:00")
            except ValueError:
                continue
            break
    return tip, idx, sessions, last_ev


def http_get(url: str, owner_key: str | None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    if owner_key:
        req.add_header("X-Tosca-Owner", owner_key)
    req.add_header("User-Agent", "toscanini-killswitch/R509 (read-only)")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return 0, json.dumps({"error_type": type(e).__name__,
                              "error": str(e)}).encode()


def preserve_evidence(sid: str, owner_key: str | None,
                      all_keys: list[str], out_dir: Path) -> dict:
    """The R509 act-1 read-only capture path, per stalled session."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rec: dict = {"session_id": sid, "captures": []}
    for name, url in [
        ("session_view", f"{SPACE_BASE}/api/sessions/{sid}"),
        ("worker_diagnostics", f"{SPACE_BASE}/api/run/{sid}/worker-diagnostics"),
    ]:
        status, body = http_get(url, owner_key)
        entry = {"endpoint": name, "http_status": status,
                 "bytes": len(body),
                 "sha256": hashlib.sha256(body).hexdigest(),
                 "at_utc": S(utcnow())}
        if status == 200:
            text = body.decode("utf-8", "replace")
            for key in all_keys:  # BS-021 fail-closed scan
                if key and len(key) >= 16 and key in text:
                    print(f"KILL-SWITCH BS-021 ABORT: key material in {name} "
                          f"payload for {sid}", file=sys.stderr)
                    sys.exit(2)
            (out_dir / f"{sid}_{name}.json").write_text(text, encoding="utf-8")
            entry["written"] = str(out_dir / f"{sid}_{name}.json")
        else:
            entry["written"] = None
            entry["typed"] = "CAPTURE_UNAVAILABLE" + (
                "_OWNERSHIP_MASK" if status in (403, 404) else "")
        rec["captures"].append(entry)
        time.sleep(1.0)
    return rec


def evaluate(tracked: list[str], alert_log: Path, preserve_dir: Path,
             declared: set[str]) -> list[dict]:
    now = utcnow()
    try:
        tip, idx, sessions, last_ev = durable_snapshot()
    except Exception as e:  # noqa: BLE001
        print(f"[{S(now)}] OBSERVATION_GAP durable: {e}", file=sys.stderr)
        return []
    if last_ev is None:
        return []
    silent_min = (now - last_ev).total_seconds() / 60.0
    all_keys = [e.get("owner_key") for e in sessions
                if isinstance(e.get("owner_key"), str)
                and len(e.get("owner_key", "")) >= 16]
    fired: list[dict] = []
    for sid in tracked:
        if sid in declared:
            continue
        e = idx.get(sid)
        status = e.get("status") if e else None
        if status is None or status in TERMINAL_STATUSES:
            continue  # absent (pre-creation) or terminal-durable: protected
        if silent_min > STALLED_MIN:
            a = {"alert": "STALLED_PER_SESSION", "at": S(now), "session_id": sid,
                 "durable_silent_for_min": round(silent_min, 1),
                 "durable_status": status,
                 "tip": tip[:16],
                 "basis": f"no durable progression > {STALLED_MIN} min "
                          "(2x p90=41, n=98 measured) while non-terminal-durable",
                 "action": "PRESERVE_NOW (read-only); no worker touched"}
            # immediate preservation — the R509 act-1 path, fresh evidence
            try:
                a["preservation"] = preserve_evidence(
                    sid, e.get("owner_key"), all_keys,
                    preserve_dir / S(now).replace(":", "").replace("-", ""))
            except SystemExit:
                raise
            except Exception as ex:  # noqa: BLE001
                a["preservation"] = {"error": f"{type(ex).__name__}: {ex}"[:200]}
            declared.add(sid)
            fired.append(a)
            print(json.dumps(a))
            with alert_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(a) + "\n")
    return fired


def self_test() -> int:
    """Logic-only self-test (no Space, no durable fetch): monkeypatched
    durable_snapshot + http_get. Verifies: per-session STALLED declared
    exactly once; terminal sessions never declared; BS-021 aborts on key
    material in a payload."""
    import tempfile
    import r509_kill_switch as ks  # self-import for monkeypatching module state

    tmp = Path(tempfile.mkdtemp(prefix="ks_selftest_"))
    log = tmp / "alerts.jsonl"
    pdir = tmp / "preservations"

    now = utcnow()
    stalled_ev = now - dt.timedelta(minutes=100)  # > 82 min silent
    sessions = [
        {"session_id": "s_stalled", "status": "RUNNING", "owner_key": "k" * 32},
        {"session_id": "s_terminal", "status": "COMPLETE", "owner_key": "k" * 32},
    ]
    orig_ds, orig_pe = ks.durable_snapshot, ks.preserve_evidence
    ks.durable_snapshot = lambda: ("tip" * 20, {e["session_id"]: e for e in sessions}, sessions, stalled_ev)
    ks.preserve_evidence = lambda sid, key, keys, out: {"session_id": sid, "captures": [{"endpoint": "mock"}]}
    try:
        declared: set[str] = set()
        fired = ks.evaluate(["s_stalled", "s_terminal"], log, pdir, declared)
        assert len(fired) == 1 and fired[0]["session_id"] == "s_stalled", fired
        assert log.read_text().count("STALLED_PER_SESSION") == 1
        # second pass: no re-declaration (declared set)
        fired2 = ks.evaluate(["s_stalled", "s_terminal"], log, pdir, declared)
        assert not fired2, fired2
        # BS-021: key material in a payload aborts
        ks.preserve_evidence = orig_pe
        import types
        ks.http_get = lambda url, key: (200, ('{"owner_key":"' + 'k' * 32 + '"}').encode())
        try:
            ks.preserve_evidence("s_stalled", None, ['k' * 32], pdir / "x")
            raise AssertionError("BS-021 scan did not abort")
        except SystemExit:
            pass  # expected abort
    finally:
        ks.durable_snapshot, ks.preserve_evidence = orig_ds, orig_pe
    print("kill-switch self-test: 3/3 OK (declare-once, terminal-never, BS-021 abort)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--loop", type=int, default=None, metavar="CADENCE_MIN")
    ap.add_argument("--sessions", nargs="*", default=None)
    ap.add_argument("--alert-log",
                    default=str(REPO / "R509" / "kill_switch_alerts.jsonl"))
    ap.add_argument("--preserve-dir",
                    default=str(REPO / "R509" / "kill_switch_preservations"))
    args = ap.parse_args()
    tracked = args.sessions if args.sessions else R506_SIDS
    alert_log = Path(args.alert_log)
    preserve_dir = Path(args.preserve_dir)
    declared: set[str] = set()

    if args.self_test:
        return self_test()
    if args.once:
        evaluate(tracked, alert_log, preserve_dir, declared)
        return 0
    if args.loop:
        while True:
            evaluate(tracked, alert_log, preserve_dir, declared)
            time.sleep(args.loop * 60)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

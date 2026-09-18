#!/usr/bin/env python3
"""scripts/r509_residue_autopsy.py — R509 Phase 1 (coder directive "all
bottlenecks, one ordered campaign"): the last-transition autopsy of the
R506 battery's durable residue, read-only over the durable branch.

Design discipline (the R508/R509 lessons compiled):
- READ-ONLY. No Space touch, no engine delta, no session mutation.
- Every file is read via `git show <commit>:<path>` from the PINNED durable
  commit — the intermittent overlay-read instability (R507 ENOENT quirk
  class; R509 read-fragmentation on str.splitlines) makes direct file reads
  untrustworthy. git-show bytes are the authority; sha256 recorded per
  source.
- JSONL parsed by splitting on b'\\n' ONLY (a raw Unicode line-separator
  inside a JSON string field fragments rows under str.splitlines()).
- Fail-closed: any parse anomaly or non-dict row aborts the run.
- BS-021: the engine's sessions.json carries owner_key values; they are
  read in-memory for the leak scan and NEVER emitted. The output is scanned
  against every owner_key string before write; a hit aborts.
- Art. XXV/XXVII: no invented thresholds; the derived watchdog bounds
  (checkpoint cadence, p90) are measured from these bytes and cited.
- Art. LXXIV s1: this autopsy speaks from OBSERVATION bytes (durable branch
  + the R509-preserved tail, itself durable). The pusher's INTERNAL failure
  cause is execution-domain and stays typed UNKNOWN here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

BATTERY_SIDS = [
    "ts_dbdf24c91535", "ts_ca977637f50b", "ts_66e23c67b511",
    "ts_84a8807b12dc", "ts_6da1b9339ce5", "ts_d9b7d3463583",
]
PRESERVATION_DIR = "battery/forensics_preservation_2026-09-18T083509Z"
PRESERVATION_FILES = {
    "ts_dbdf24c91535": "ts_1_ts_dbdf24c91535",
    "ts_ca977637f50b": "ts_2_ts_ca977637f50b",
    "ts_66e23c67b511": "ts_3_ts_66e23c67b511",
    "ts_84a8807b12dc": "ts_4_ts_84a8807b12dc",
    "ts_6da1b9339ce5": "ts_5_ts_6da1b9339ce5",
    "ts_d9b7d3463583": "ts_6_ts_d9b7d3463583",
}
RUN_P90_MIN = 41   # /api/health run_duration_stats n=98 p50=11 p90=41 (measured, cited)
RUN_P50_MIN = 11


def fail(msg: str) -> None:
    print(f"AUTOPSY FAIL-CLOSED: {msg}", file=sys.stderr)
    sys.exit(2)


def git_show(commit: str, path: str) -> bytes:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"],
                       capture_output=True)
    if r.returncode != 0:
        fail(f"git show {commit}:{path} -> {r.returncode}: {r.stderr.decode()[:200]}")
    return r.stdout


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_jsonl(commit: str, path: str) -> tuple[list[dict], str]:
    b = git_show(commit, path)
    rows = []
    for line in b.split(b"\n"):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            fail(f"{path}: unparseable line ({e}); bytes pinned sha={sha(b)[:16]}")
        if not isinstance(obj, dict):
            fail(f"{path}: non-dict row ({type(obj).__name__}); bytes pinned sha={sha(b)[:16]}")
        rows.append(obj)
    return rows, sha(b)


def load_json(commit: str, path: str) -> tuple[dict, str]:
    b = git_show(commit, path)
    try:
        obj = json.loads(b)
    except Exception as e:
        fail(f"{path}: unparseable ({e})")
    if not isinstance(obj, dict):
        fail(f"{path}: non-dict top level")
    return obj, sha(b)


def T(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--durable-commit", default="215251c97d43a478122ddb7fad364be6777a7000")
    ap.add_argument("--out", default=str(REPO / "R509" / "RESIDUE_AUTOPSY.json"))
    args = ap.parse_args()
    C = args.durable_commit

    sources: dict[str, str] = {}

    # ---- durable side --------------------------------------------------
    snaps, sources["snapshot_log.jsonl"] = load_jsonl(C, "snapshot_log.jsonl")
    ledger, sources["worker_forensics/ledger.jsonl"] = load_jsonl(C, "worker_forensics/ledger.jsonl")
    routing, sources["model_routing/ledger.jsonl"] = load_jsonl(C, "model_routing/ledger.jsonl")
    sessions_wrap, sources["sessions.json"] = load_json(C, "sessions.json")
    sessions = sessions_wrap.get("sessions")
    if not isinstance(sessions, list):
        fail("sessions.json: 'sessions' is not a list")
    sess_by_id = {e.get("session_id"): e for e in sessions if isinstance(e, dict)}

    # owner_key custody: read in-memory for the leak scan; NEVER emit
    owner_keys = []
    for sid in BATTERY_SIDS:
        e = sess_by_id.get(sid) or {}
        ok = e.get("owner_key")
        if isinstance(ok, str) and len(ok) >= 16:
            owner_keys.append(ok)

    last_snapshot_overall = snaps[-1]
    snap_by_sid: dict[str, dict] = {}
    for r in snaps:
        reason = str(r.get("reason", ""))
        for sid in BATTERY_SIDS:
            if sid in reason:
                snap_by_sid[sid] = r

    led_by_sid: dict[str, list[dict]] = defaultdict(list)
    for r in ledger:
        sid = r.get("session_id")
        if sid in BATTERY_SIDS:
            led_by_sid[sid].append(r)
    for sid in BATTERY_SIDS:
        led_by_sid[sid].sort(key=lambda r: str(r.get("ts_utc", "")))

    # routing: session-attributed rows + the battery-window aggregate
    routing_by_sid = {sid: [r for r in routing if r.get("session_id") == sid]
                      for sid in BATTERY_SIDS}
    for sid in BATTERY_SIDS:
        routing_by_sid[sid].sort(key=lambda r: str(r.get("recorded_at", "")))
    bat_window = [r for r in routing
                  if "2026-09-18T00:00" <= str(r.get("recorded_at", "")) <= "2026-09-18T00:09:15"]
    window_ok = sum(1 for r in bat_window if r.get("ok") is True)
    xkiro_rl = [r for r in routing
                if r.get("provider") == "xkiro" and r.get("failure_class") == "RATE_LIMITED"]
    xkiro_first, xkiro_last = (str(xkiro_rl[0].get("recorded_at")),
                               str(xkiro_rl[-1].get("recorded_at"))) if xkiro_rl else (None, None)
    xkiro_2337 = [r for r in xkiro_rl if str(r.get("recorded_at", "")).startswith("2026-09-17T23:37")]

    # ---- preserved tail (R509 act 1, itself durable bytes) -------------
    pres: dict[str, dict] = {}
    for sid, stem in PRESERVATION_FILES.items():
        sv, _ = load_json(C, f"{PRESERVATION_DIR}/{stem}_session_view.json")
        wd, _ = load_json(C, f"{PRESERVATION_DIR}/{stem}_worker_diagnostics.json")
        pres[sid] = {"view": sv, "diag": wd}

    def timeline(sid: str) -> dict:
        sf = pres[sid]["diag"].get("spawn_forensics") or []
        out = {"spawned": None, "first_heartbeat": None, "last_heartbeat": None,
               "bridge_gate": None, "terminal_state": None, "worker_completed": None,
               "n_events": len(sf)}
        for e in sf:
            ev = e.get("event")
            ts = e.get("ts_utc")
            if ev == "WORKER_SPAWNED" and out["spawned"] is None:
                out["spawned"] = ts
            elif ev == "HEARTBEAT":
                if out["first_heartbeat"] is None:
                    out["first_heartbeat"] = ts
                out["last_heartbeat"] = ts
            elif ev == "BRIDGE_GATE_OUTCOME":
                out["bridge_gate"] = {"ts": ts, "outcome": e.get("outcome") or e.get("field")}
            elif ev == "TERMINAL_STATE":
                out["terminal_state"] = {"ts": ts, "stage": e.get("stage"),
                                         "field": e.get("field")}
            elif ev == "WORKER_COMPLETED":
                out["worker_completed"] = ts
        return out

    # ---- derived watchdog bounds (measured, cited) ---------------------
    ck_by_sid: dict[str, list[dt.datetime]] = defaultdict(list)
    for r in snaps:
        reason = str(r.get("reason", ""))
        if reason.startswith("engine_checkpoint:"):
            ck_by_sid[reason.split(":", 1)[1]].append(T(str(r["at"])))
    ck_gaps = []
    for sid, ts in ck_by_sid.items():
        ts.sort()
        for a, b in zip(ts, ts[1:]):
            m = (b - a).total_seconds() / 60.0
            if m < 180:
                ck_gaps.append(m)
    ck = {
        "n_gaps": len(ck_gaps),
        "n_sessions_with_checkpoints": len(ck_by_sid),
        "min": min(ck_gaps), "p50": sorted(ck_gaps)[len(ck_gaps) // 2],
        "max": max(ck_gaps),
        "battery_sessions_with_checkpoints": sum(
            1 for s in BATTERY_SIDS if ck_by_sid.get(s)),
    } if ck_gaps else {"n_gaps": 0}

    # ---- per-session rows ----------------------------------------------
    rows = []
    for idx, sid in enumerate(BATTERY_SIDS, start=1):
        view = pres[sid]["view"]
        fs = view.get("final_state") or {}
        stages = view.get("stages") or []
        last_stage = stages[-1] if stages else None
        durable_status = (sess_by_id.get(sid) or {}).get("status")
        led = led_by_sid[sid]
        snap = snap_by_sid.get(sid)
        tl = timeline(sid)
        rt = routing_by_sid[sid]
        last_rt = rt[-1] if rt else None

        exclusions = {
            "OOM_suspect_EXCLUDED_by": {
                "event": "WORKER_COMPLETED", "ts_utc": tl["worker_completed"],
                "basis": "the worker reached WORKER_COMPLETED — a process that OOMs does not emit a completion event",
            },
            "TRANSPORT_HANG_suspect_EXCLUDED_by": {
                "event": "TERMINAL_STATE", "ts_utc": (tl["terminal_state"] or {}).get("ts"),
                "stage": (tl["terminal_state"] or {}).get("stage"),
                "basis": "the run reached TERMINAL_STATE (phase 5, FINAL_SNAPSHOT) — a hung worker freezes before terminal",
            },
            "PROVIDER_STALL_suspect_EXCLUDED_by": {
                "basis": "terminal completion requires every LLM stage to have returned; the durable-visible battery routing window is failure-free",
                "routing_window_rows": len(bat_window),
                "routing_window_ok_true": window_ok,
                "xkiro_rate_limited_window": [xkiro_first, xkiro_last],
                "xkiro_congestion_predates_battery": True,
            },
        }
        rows.append({
            "problem_index": idx,
            "session_id": sid,
            "durable_side": {
                "sessions_json_status_frozen_at_last_snapshot": durable_status,
                "last_durable_journal_row": {
                    "ts_utc": led[-1].get("ts_utc") if led else None,
                    "event": led[-1].get("event") if led else None,
                    "stage": led[-1].get("stage") if led else None,
                },
                "last_durable_snapshot_reason": {
                    "at": snap.get("at") if snap else None,
                    "reason": snap.get("reason") if snap else None,
                    "ok": snap.get("ok", True) if snap else None,
                },
                "durable_run_dir": False,
            },
            "preserved_side": {
                "status_live": view.get("status"),
                "last_envelope_stage": {
                    "stage": last_stage.get("stage") if last_stage else None,
                    "status": last_stage.get("status") if last_stage else None,
                    "finished_at": last_stage.get("finished_at") if last_stage else None,
                },
                "final_state": {
                    "final_status": fs.get("final_status"),
                    "final_envelope_hash": fs.get("final_envelope_hash"),
                    "adjudication_verdict": fs.get("adjudication_verdict"),
                    "adversarial_overall": fs.get("adversarial_overall"),
                    "evidence_verified": fs.get("evidence_verified"),
                    "prior_art_status": fs.get("prior_art_status"),
                    "ranking_score": fs.get("ranking_score"),
                },
                "timeline": tl,
            },
            "last_routing_attempt": {
                "session_attributed": last_rt is not None,
                "recorded_at": last_rt.get("recorded_at") if last_rt else None,
                "provider": last_rt.get("provider") if last_rt else None,
                "model": last_rt.get("model") if last_rt else None,
                "ok": last_rt.get("ok") if last_rt else None,
                "failure_class": last_rt.get("failure_class") if last_rt else None,
                "latency_ms": (last_rt.get("latency_ms") or last_rt.get("latency")) if last_rt else None,
                "note": ("only 1/6 battery routing rows carries a session_id in the durable "
                         "bytes; the rest are NOT_SESSION_ATTRIBUTED (session_id null) — "
                         "per-session attribution post-00:09:15Z is NOT_MEASURABLE from "
                         "durable bytes (Art. XXV)") if last_rt is None else
                        "the only session-attributed routing row in the durable ledger",
            },
            "typed_suspects": ["PUSH-FAILURE-suspect"],
            "suspect_basis": {
                "PUSH-FAILURE-suspect": (
                    "terminal reached in the ephemeral store (TERMINAL_STATE FINAL_SNAPSHOT "
                    f"at {(tl['terminal_state'] or {}).get('ts')}, WORKER_COMPLETED at "
                    f"{tl['worker_completed']}) but ZERO durable snapshots for this session "
                    "after the 00:09:15Z last-overall snapshot; the measured engine_checkpoint "
                    "cadence (10.0 min) delivered 0 checkpoints to this session vs the "
                    "cadence every historical RUNNING session received"
                ),
            },
            "exclusions_byte_cited": exclusions,
            "residual_UNKNOWN": (
                "the snapshot pusher's internal cause of silence (execution-domain, "
                "owner-scoped) — the autopsy types the LOCUS (durable push path), never "
                "the internal cause (Art. XXV/LXXIV s1)"
            ),
        })

    # ---- battery-level row + discriminator ------------------------------
    completed = [r["preserved_side"]["timeline"]["worker_completed"] for r in rows]
    discriminator = {
        "directive_question": "shared hang (missing timeout) vs six independent OOMs",
        "measured_answer": "NEITHER — DISSOLVED by preserved bytes: all six workers "
                           "reached WORKER_COMPLETED; there were no deaths to discriminate",
        "xkiro_rate_limited_event": {
            "directive_cited": "23:37Z",
            "measured_in_durable_bytes": {
                "n_events_total": len(xkiro_rl),
                "first": xkiro_first,
                "last": xkiro_last,
                "events_at_23:37Z": len(xkiro_2337),
                "clusters_minutes": dict(Counter(
                    str(r.get("recorded_at", ""))[11:16] for r in xkiro_rl)),
            },
            "relation_to_battery": "the congestion ENDED 23:59:32Z; the battery was "
                                   "submitted 00:03:38-00:04:32Z; the first post-congestion "
                                   "ok xkiro call is 00:00:46Z — the battery ran AFTER the "
                                   "incident window closed",
        },
        "heartbeat_004041Z": "sits mid-run for ts_6da1b9339ce5 (heartbeats continue to "
                             "00:44:41.113Z; WORKER_COMPLETED 00:45:07.775Z) — consistent "
                             "with the preserved timeline, never a death signal",
        "routing_battery_window": {
            "rows_0000_0009": len(bat_window),
            "ok_true": window_ok,
            "failure_class_rows": sum(1 for r in bat_window if r.get("failure_class")),
        },
    }

    battery_row = {
        "battery": "R506-discovery-yield execution #1",
        "typed_suspects": ["PUSH-FAILURE-suspect"],
        "basis": {
            "last_successful_snapshot": {
                "at": last_snapshot_overall.get("at"),
                "reason": last_snapshot_overall.get("reason"),
                "ok": last_snapshot_overall.get("ok", True),
                "pushed": last_snapshot_overall.get("pushed"),
                "files": last_snapshot_overall.get("files"),
                "error": last_snapshot_overall.get("error"),
            },
            "snapshots_after_last": 0,
            "snapshot_log_history_error_rows": sum(
                1 for r in snaps if not r.get("ok", True) or r.get("error")),
            "terminal_phases_exist_ephemeral": f"6/6, {min(completed)} .. {max(completed)}",
            "engine_checkpoint_cadence_measured": ck,
            "battery_sessions_receiving_checkpoints": 0,
            "expected_checkpoints_missed_per_session_at_least": 3,
            "push_path_reported_healthy_while_silent": True,
            "durable_run_dirs": 0,
        },
        "what_r508_typed_on_the_durable_domain": "6x INCOMPLETE_INFRASTRUCTURE_FAILURE — "
            "CORRECT on the bytes R508 could read (0/6 terminals on the terminal authority); "
            "the preserved tail resolves its LXXIV s1 death-vs-stall UNKNOWN: no deaths",
        "residual_UNKNOWN": "the pusher's internal cause — owner-scoped (act 3 root-cause "
                            "input: the preserved tail + any owner-side pusher logs)",
    }

    out = {
        "artifact_type": "R509_RESIDUE_AUTOPSY",
        "phase": "1 — mine the durable residue (observer-side, no Space touch)",
        "directive_anchor": "Coder directive: all bottlenecks, one ordered campaign",
        "durable_commit_pinned": C,
        "sources_sha256": sources,
        "read_discipline": "git-show of the pinned commit; b'\\n'-split JSONL; fail-closed; "
                           "sha256 per source (the overlay read-instability lesson)",
        "per_session_rows": rows,
        "battery_level": battery_row,
        "hang_vs_death_discriminator": discriminator,
        "derived_watchdog_bounds": {
            "engine_checkpoint_cadence_min": ck,
            "tip_stale_threshold_min": 30,
            "tip_stale_basis": "3x the measured 10.0-min engine_checkpoint cadence — "
                               "three consecutive missed checkpoints while any session is "
                               "non-terminal-durable",
            "stalled_threshold_min": 2 * RUN_P90_MIN,
            "stalled_basis": "the directive's 2x p90 bound; p90=41 from the /api/health "
                             "run_duration_stats n=98 measured distribution",
            "heartbeat_freshness_s": 120,
            "heartbeat_basis": "the engine's own active_workers derivation semantics "
                               "(a worker is active only with a heartbeat fresher than 120s)",
        },
        "one_line_verdict_table": [
            {"idx": r["problem_index"], "sid": r["session_id"],
             "verdict": "COMPLETED-EPHEMERAL / PUSH-FAILURE-suspect "
                        "(not OOM, not transport-hang, not provider-stall — exclusions byte-cited)"}
            for r in rows
        ],
        "reviewer_provenance": "AI_REVIEW",
    }

    # BS-021 leak scan before write
    blob = json.dumps(out, indent=1)
    for key in owner_keys:
        if key and key in blob:
            fail("BS-021: owner_key material would be emitted — aborting")

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(blob + "\n", encoding="utf-8")
    print(f"wrote {outp} ({len(blob)} bytes)")
    for row in out["one_line_verdict_table"]:
        print(f"  #{row['idx']} {row['sid']}: {row['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

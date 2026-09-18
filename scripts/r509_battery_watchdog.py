#!/usr/bin/env python3
"""scripts/r509_battery_watchdog.py — R509 Phase 2 (coder directive):
observer-side watchdog for battery executions. NO engine delta; the
battery stays valid (it changes nothing the engine can observe).

LXXIV discipline: this watchdog OBSERVES and TYPES. It never restarts,
never resubmits, never touches workers, never holds execution state as
authority — the durable branch is the terminal authority. Observation
gaps are typed OBSERVATION_GAP and are never an alert basis (Art. XXV).

Three typed alerts (bounds measured, never invented — Art. XXVII):
  STALLED_OVER_2X_P90    a tracked session, non-terminal-durable, with no
                         durable progression for > 2 x p90 = 82 min
                         (p90=41 min from /api/health run_duration_stats
                         n=98, the deployment's own measured distribution)
  HEARTLESS_WORKERS      active_workers == [] while >=1 tracked session is
                         non-terminal-durable (the engine's own semantics:
                         a worker is active only with a heartbeat fresher
                         than 120 s)
  DURABLE_TIP_STALE      durable tip unchanged > 30 min while >=1 tracked
                         session is non-terminal-durable AND the push path
                         reports healthy — 30 min = 3x the measured
                         engine_checkpoint cadence of 10.0 min (R509
                         autopsy: n=17 gaps, all 10.0-10.1 min, 6 sessions;
                         the R506 battery received ZERO checkpoints after
                         00:09:15Z while its workers ran 35 more minutes)

Hysteresis: every alert requires its condition on 2 consecutive polls
(default cadence 5 min) — provider jitter cannot flap it.

Modes:
  --live          poll the public endpoints + durable branch (observer)
  --replay START END [ --track SID ... ]
                  reconstruct the observation timeline from durable git
                  history + preserved bytes and replay the watchdog logic
                  (the dry-run acceptance path; no network)
  --self-test     synthetic timeline checks of the alert logic
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE_BASE = "https://prateekm1-toscanini-prod-validation.hf.space"

P90_MIN = 41
STALLED_MIN = 2 * P90_MIN            # 82
TIP_STALE_MIN = 30                   # 3 x 10.0-min measured checkpoint cadence
HEARTBEAT_FRESH_S = 120              # the engine's own active_workers semantics
TERMINAL_STATUSES = {"COMPLETE", "ERROR_RUN", "ERROR_STUCK", "INTERRUPTED"}
R506_SIDS = [
    "ts_dbdf24c91535", "ts_ca977637f50b", "ts_66e23c67b511",
    "ts_84a8807b12dc", "ts_6da1b9339ce5", "ts_d9b7d3463583",
]


def T(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def S(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# alert engine (pure logic; shared by live and replay)
# --------------------------------------------------------------------------

class AlertEngine:
    def __init__(self, tracked: list[str]):
        self.tracked = tracked
        self.state: dict[str, dict] = {}
        self.alerts: list[dict] = []
        # hysteresis counters: condition-true streak per alert
        self._streak = defaultdict(int)

    def observe(self, t: dt.datetime, *, tip: str | None,
                tip_last_change: dt.datetime | None,
                sessions_status: dict[str, str | None],
                active_workers: list[str] | set[str] | None,
                push_path_healthy: bool | None) -> list[dict]:
        """One poll. Returns alerts fired at this poll (also appended to
        self.alerts). Any None input = OBSERVATION_GAP for that channel —
        it resets hysteresis and never fires anything (Art. XXV)."""
        fired: list[dict] = []
        # non-terminal-durable = EXISTS in sessions.json and not terminal.
        # A session absent from the observed sessions.json is either
        # not-yet-created or observation-lagged: it NEVER alerts (a
        # pre-creation window must not false-fire; Art. XXV).
        nonterminal = [s for s in self.tracked
                       if s in sessions_status
                       and sessions_status[s] is not None
                       and sessions_status[s] not in TERMINAL_STATUSES]

        # -- STALLED_OVER_2X_P90 ------------------------------------------
        if tip_last_change is None:
            self._streak["stalled"] = 0
        else:
            stalled_sessions = [
                s for s in nonterminal
                if (t - tip_last_change).total_seconds() / 60 > STALLED_MIN
            ]
            if stalled_sessions:
                self._streak["stalled"] += 1
                if self._streak["stalled"] == 2:
                    a = {"alert": "STALLED_OVER_2X_P90", "at": S(t),
                         "sessions": stalled_sessions,
                         "durable_silent_for_min": round(
                             (t - tip_last_change).total_seconds() / 60, 1),
                         "basis": f"no durable progression > {STALLED_MIN} min "
                                  f"(2 x p90={P90_MIN} min, n=98 measured)"}
                    self.alerts.append(a); fired.append(a)
            else:
                self._streak["stalled"] = 0

        # -- HEARTLESS_WORKERS --------------------------------------------
        if active_workers is None:
            self._streak["heartless"] = 0
        else:
            empty = len(list(active_workers)) == 0
            if empty and nonterminal:
                self._streak["heartless"] += 1
                if self._streak["heartless"] == 2:
                    a = {"alert": "HEARTLESS_WORKERS", "at": S(t),
                         "sessions": nonterminal,
                         "basis": "active_workers empty (no heartbeat fresher "
                                  f"than {HEARTBEAT_FRESH_S}s) while "
                                  f"{len(nonterminal)} tracked session(s) "
                                  "non-terminal-durable"}
                    self.alerts.append(a); fired.append(a)
            else:
                self._streak["heartless"] = 0

        # -- DURABLE_TIP_STALE --------------------------------------------
        if tip is None or tip_last_change is None or push_path_healthy is None:
            self._streak["tipstale"] = 0
        else:
            stale_min = (t - tip_last_change).total_seconds() / 60
            if stale_min > TIP_STALE_MIN and nonterminal and push_path_healthy:
                self._streak["tipstale"] += 1
                if self._streak["tipstale"] == 2:
                    a = {"alert": "DURABLE_TIP_STALE", "at": S(t),
                         "tip": tip, "stale_min": round(stale_min, 1),
                         "sessions": nonterminal,
                         "basis": f"durable tip unchanged > {TIP_STALE_MIN} min "
                                  "(3x the measured 10.0-min engine_checkpoint "
                                  "cadence) with non-terminal-durable sessions "
                                  "and a push path reporting healthy"}
                    self.alerts.append(a); fired.append(a)
            else:
                self._streak["tipstale"] = 0

        return fired


# --------------------------------------------------------------------------
# replay (dry-run) machinery
# --------------------------------------------------------------------------

def git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {args[:2]}: {r.stderr[:200]}")
    return r.stdout


def load_durable_json(commit: str, path: str):
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git show {path}: {r.stderr[:200]}")
    return json.loads(r.stdout)


def build_replay(start: dt.datetime, end: dt.datetime, tracked: list[str]):
    """Reconstruct the observation timeline from durable bytes only."""
    branch = "origin/runtime-state-hf"
    # durable events: every commit on the branch in [start, end]
    log = git("log", "--format=%H|%ci|%s", "--since",
              S(start), "--until", S(end), branch)
    events = []  # (t, commit_sha, subject)
    for line in log.splitlines():
        if "|" not in line:
            continue
        sha, ci, subj = line.split("|", 2)
        events.append((T(ci.strip()), sha, subj.strip()))
    events.sort()
    if not events:
        raise RuntimeError("no durable commits in the replay window")

    # heartbeats: durable ledger + preserved battery tail
    heartbeats: dict[str, list[dt.datetime]] = defaultdict(list)
    tip_c = git("rev-parse", branch).strip()
    led = load_durable_json(tip_c, "worker_forensics/ledger.jsonl") \
        if False else None
    r = subprocess.run(["git", "-C", str(REPO), "show",
                        f"{tip_c}:worker_forensics/ledger.jsonl"],
                       capture_output=True)
    for line in r.stdout.split(b"\n"):
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("event") == "HEARTBEAT" and e.get("session_id") in tracked:
            heartbeats[e["session_id"]].append(T(e["ts_utc"]))
    # preserved tail heartbeats for the battery six
    pdir = "battery/forensics_preservation_2026-09-18T083509Z"
    pmap = {"ts_dbdf24c91535": "ts_1_ts_dbdf24c91535",
            "ts_ca977637f50b": "ts_2_ts_ca977637f50b",
            "ts_66e23c67b511": "ts_3_ts_66e23c67b511",
            "ts_84a8807b12dc": "ts_4_ts_84a8807b12dc",
            "ts_6da1b9339ce5": "ts_5_ts_6da1b9339ce5",
            "ts_d9b7d3463583": "ts_6_ts_d9b7d3463583"}
    for sid, stem in pmap.items():
        if sid not in tracked:
            continue
        wd = load_durable_json(tip_c, f"{pdir}/{stem}_worker_diagnostics.json")
        for e in (wd.get("spawn_forensics") or []):
            if e.get("event") == "HEARTBEAT":
                heartbeats[sid].append(T(e["ts_utc"]))
    for sid in heartbeats:
        heartbeats[sid].sort()

    def active_at(t: dt.datetime) -> list[str]:
        out = []
        for sid, ts in heartbeats.items():
            if any(0 <= (t - h).total_seconds() <= HEARTBEAT_FRESH_S
                   for h in ts):
                out.append(sid)
        return sorted(out)

    # sessions.json versions: statuses of tracked sids at each event commit
    sess_commits = git("log", "--format=%H|%ci", "--since", S(start),
                       "--until", S(end), branch, "--", "sessions.json")
    versions = []  # (t, {sid: status})
    for line in sess_commits.splitlines():
        if "|" not in line:
            continue
        sha, ci = line.split("|", 1)
        versions.append((T(ci.strip()), sha))
    versions.sort()

    def statuses_at(t: dt.datetime) -> dict[str, str | None]:
        # newest sessions.json commit at or before t
        pick = None
        for vt, vsha in versions:
            if vt <= t:
                pick = vsha
            else:
                break
        if pick is None:
            return {s: None for s in tracked}
        try:
            data = load_durable_json(pick, "sessions.json")
        except Exception:
            return {s: None for s in tracked}
        idx = {e.get("session_id"): e.get("status")
               for e in data.get("sessions", [])}
        return {s: idx.get(s) for s in tracked}

    # push path health in replay: measured healthy across all durable bytes
    # (snapshot_log: 760/760 ok, zero error rows; preserved health pre/post:
    #  last_write_error=null) — typed as a measured replay assumption
    def push_healthy(_t: dt.datetime) -> bool:
        return True

    return events, active_at, statuses_at, push_healthy


def run_replay(start: dt.datetime, end: dt.datetime, tracked: list[str],
               cadence_min: int = 5) -> dict:
    events, active_at, statuses_at, push_healthy = build_replay(start, end, tracked)
    eng = AlertEngine(tracked)
    polls = []
    t = start
    ev_i = 0
    while t <= end:
        while ev_i < len(events) and events[ev_i][0] <= t:
            ev_i += 1
        tip = events[ev_i - 1][1] if ev_i > 0 else None
        # last tip change time at or before t
        tip_last = events[ev_i - 1][0] if ev_i > 0 else None
        # tip_last_change must reflect the LAST CHANGE, not the last event:
        # replay uses event boundaries; between events the tip is unchanged.
        fired = eng.observe(
            t, tip=tip, tip_last_change=tip_last,
            sessions_status=statuses_at(t),
            active_workers=active_at(t),
            push_path_healthy=push_healthy(t))
        polls.append({"at": S(t), "tip": (tip or "")[:12],
                      "fired": [a["alert"] for a in fired]})
        t += dt.timedelta(minutes=cadence_min)
    return {"start": S(start), "end": S(end), "tracked": tracked,
            "cadence_min": cadence_min, "polls": len(polls),
            "alerts": eng.alerts, "poll_log": polls}


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def self_test() -> int:
    t0 = dt.datetime(2026, 9, 18, 0, 0, tzinfo=dt.timezone.utc)
    eng = AlertEngine(["s1"])
    st = {"s1": "RUNNING"}
    # 1) no alerts while tip advances and heartbeats present
    t = t0
    for i in range(6):
        eng.observe(t, tip=f"c{i}", tip_last_change=t,
                    sessions_status=st, active_workers=["s1"],
                    push_path_healthy=True)
        t += dt.timedelta(minutes=5)
    assert not eng.alerts, f"false alerts on healthy timeline: {eng.alerts}"

    # 2) TIP_STALE fires at 2 consecutive polls past 30 min, STALLED past 82
    eng2 = AlertEngine(["s1"])
    last_change = t0
    t = t0
    fired_at = {}
    for i in range(30):
        f = eng2.observe(t, tip="c0", tip_last_change=last_change,
                         sessions_status=st, active_workers=["s1"],
                         push_path_healthy=True)
        for a in f:
            fired_at.setdefault(a["alert"], a["at"])
        t += dt.timedelta(minutes=5)
    assert "DURABLE_TIP_STALE" in fired_at, "TIP_STALE never fired"
    assert fired_at["DURABLE_TIP_STALE"] == "2026-09-18T00:40:00Z", fired_at
    assert "STALLED_OVER_2X_P90" in fired_at, "STALLED never fired"
    assert fired_at["STALLED_OVER_2X_P90"] == "2026-09-18T01:30:00Z", fired_at

    # 3) HEARTLESS only with non-terminal sessions; terminal session -> no fire
    eng3 = AlertEngine(["s1"])
    for i in range(4):
        eng3.observe(t0 + dt.timedelta(minutes=5 * i), tip="c", 
                     tip_last_change=t0,
                     sessions_status={"s1": "COMPLETE"},
                     active_workers=[], push_path_healthy=True)
    assert not eng3.alerts, "false HEARTLESS on terminal-durable session"

    # 4) observation gap resets hysteresis (never fires on missing data)
    eng4 = AlertEngine(["s1"])
    eng4.observe(t0, tip="c", tip_last_change=t0, sessions_status=st,
                 active_workers=None, push_path_healthy=True)
    eng4.observe(t0 + dt.timedelta(minutes=5), tip="c",
                 tip_last_change=t0, sessions_status=st,
                 active_workers=None, push_path_healthy=True)
    assert not eng4.alerts, "fired on observation gap"

    # 5) terminal-durable session stops all alerts even if tip frozen
    eng5 = AlertEngine(["s1"])
    for i in range(20):
        eng5.observe(t0 + dt.timedelta(minutes=10 * i), tip="c",
                     tip_last_change=t0,
                     sessions_status={"s1": "COMPLETE"},
                     active_workers=[], push_path_healthy=True)
    assert not eng5.alerts, "fired with all sessions terminal-durable"
    print("self-test: 5/5 OK")
    return 0


# --------------------------------------------------------------------------
# live mode
# --------------------------------------------------------------------------

def live(track: list[str], cadence_min: int, alert_log: Path,
         once: bool = False) -> int:
    eng = AlertEngine(track)
    prev_tip = None
    tip_since = None
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        tip = None
        try:
            git("fetch", "origin", "runtime-state-hf")
            tip = git("rev-parse", "origin/runtime-state-hf").strip()
        except Exception as e:
            print(f"[{S(now)}] OBSERVATION_GAP durable: {e}", file=sys.stderr)
        if tip is not None:
            if tip != prev_tip:
                tip_since = now
                prev_tip = tip
        health = None
        try:
            req = urllib.request.Request(
                SPACE_BASE + "/api/health",
                headers={"User-Agent": "toscanini-watchdog/R509"})
            with urllib.request.urlopen(req, timeout=45) as r:
                health = json.loads(r.read().decode())
        except Exception as e:
            print(f"[{S(now)}] OBSERVATION_GAP health: {e}", file=sys.stderr)
        statuses: dict[str, str | None] = {s: None for s in track}
        push_healthy = None
        active = None
        if health is not None:
            wf = health.get("worker_forensics") or {}
            active = wf.get("active_workers")
            ls = (health.get("durable") or {}).get("last_snapshot") or {}
            push_healthy = (ls.get("error") is None
                            and wf.get("forensics_degraded") is False)
        if tip is not None:
            try:
                data = load_durable_json(tip, "sessions.json")
                idx = {e.get("session_id"): e.get("status")
                       for e in data.get("sessions", [])}
                statuses = {s: idx.get(s) for s in track}
            except Exception:
                pass  # stays OBSERVATION_GAP-shaped (None)
        fired = eng.observe(now, tip=tip, tip_last_change=tip_since,
                            sessions_status=statuses,
                            active_workers=active,
                            push_path_healthy=push_healthy)
        for a in fired:
            print(f"[{a['at']}] ALERT {a['alert']}: {a['basis']}")
            with alert_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(a) + "\n")
        if once:
            return 0
        time.sleep(cadence_min * 60)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--once", action="store_true",
                    help="live mode: single poll (for cron-driven runs)")
    ap.add_argument("--replay", nargs=2, metavar=("START", "END"),
                    help="ISO timestamps, e.g. 2026-09-18T00:00Z 2026-09-18T02:00Z")
    ap.add_argument("--track", nargs="*", default=None,
                    help="session ids to track (default: the six R506 battery sids)")
    ap.add_argument("--cadence-min", type=int, default=5)
    ap.add_argument("--alert-log", default=str(REPO / "R509" / "watchdog_alerts.jsonl"))
    ap.add_argument("--out", default=None, help="replay: write the run record here")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    track = args.track if args.track else R506_SIDS

    if args.self_test:
        return self_test()
    if args.replay:
        start, end = T(args.replay[0]), T(args.replay[1])
        rec = run_replay(start, end, track, args.cadence_min)
        blob = json.dumps(rec, indent=1)
        if args.out:
            Path(args.out).write_text(blob + "\n", encoding="utf-8")
            print(f"wrote {args.out}")
        print(f"replay {rec['start']} -> {rec['end']}: polls={rec['polls']} "
              f"alerts={len(rec['alerts'])}")
        for a in rec["alerts"]:
            print(f"  {a['at']}  {a['alert']}  sessions={a.get('sessions')}")
        return 0
    if args.live:
        return live(track, args.cadence_min, Path(args.alert_log), once=args.once)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

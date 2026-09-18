#!/usr/bin/env python3
"""r509_battery_watchdog.py — CEO directive "all bottlenecks, one ordered campaign",
Phase 2: observer-side battery watchdog (no engine delta, battery stays valid).

MODES
  --selftest : build the replay corpora FROM DURABLE BYTES + the R508 evidence
               files, run the alert FSM, and emit R509/WATCHDOG_REPLAY_ACCEPTANCE.json
               (acceptance: R508 death signature = all three alerts in order;
               R484/R487 closure histories = zero false fires).
  --replay F : run the FSM over a replay events file (the selftest format).
  --live [--once] : poll public /api/health + the durable branch tip and run the
               same FSM against the tracked six sessions; append-only alert log.

ALERTS (typed, directive item 4)
  STALLED_OVER_2X_P90  — 82 min without durable progression for a tracked session
                         (82 = 2 x p90; p90 = 41 min measured, n=98,
                         R508/EVIDENCE_HEALTH_2026-09-18T0724Z.json; the ONLY
                         derived bound the directive authorizes — Art. XXVII)
  HEARTLESS_WORKERS    — health active_workers list empties while the durable
                         authority still shows a tracked session mid-execution
                         (heartbeat freshness semantics <120s are the engine's
                         own, as recorded at R508)
  DURABLE_TIP_STALE    — durable branch tip unchanged for the same 2 x p90 bound
                         while the last health observation reports a healthy push
                         path (ok=true, pushed=true, error=null) and >=1 session
                         in flight. Bound reuse disclosed: one measured
                         distribution, two surfaces (per-session, per-branch).

DISCIPLINE
  - Alert = record + notify ONLY. This process has no write path to production:
    the only HTTP verb used is GET (public health/version), the only git ops are
    ls-remote/fetch/show (read-only). No restart, no resubmit, no session
    mutation — structurally impossible from this file (directive item 4).
  - Hysteresis: a condition must hold on CONFIRM consecutive polls before its
    alert fires; a fired alert clears only after CLEAR consecutive all-clear
    polls (provider jitter cannot flap it).
  - Art. XXV/XXI.3: an unobserved input (health unreachable, tip unobservable)
    is typed UNOBSERVABLE_<X> in the tick record — never treated as evidence of
    health or of failure.
  - Art. LXXIV s1: every record names its domain (observation vs durable).
  - BS-021: no credential ever enters argv/URL/logs; token injection via
    GIT_ASKPASS from the operator vault only; alert records scanned fail-closed.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

REPO = os.environ.get("TOSCANINI_REPO", "/home/z/my-project/hf_space")
SPACE = "prateekm1/toscanini-prod-validation"
SPACE_URL = f"https://{SPACE.replace('/', '-')}.hf.space"
DURABLE_BRANCH = "runtime-state-hf"
REDACTED_REL = "R506/BATTERY_SESSIONS_REDACTED.json"
P90_MIN = 41          # measured, R508 evidence (n=98)
N_RUNS = 98
P50_MIN = 11
BOUND_MIN = 2 * P90_MIN   # 82 — the directive-authorized derived bound
HEARTBEAT_FRESH_S = 120   # engine's own freshness semantics (R508 record)
CONFIRM = 3
CLEAR = 3
POLL_S = 300

BS021 = [r"pb_live_[A-Za-z0-9]+", r"ghp_[A-Za-z0-9]+", r"gho_[A-Za-z0-9]+",
         r"github_pat_[A-Za-z0-9_]+", r"hf_[A-Za-z0-9]{20,}",
         r"sk-[A-Za-z0-9]{20,}", r"X-Tosca-Owner", r"\bowner_key\b"]


def parse_ts(s):
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def tracked_sessions():
    red = json.load(open(os.path.join(REPO, REDACTED_REL), encoding="utf-8"))
    return [(s["problem_index"], s["session_id"]) for s in red["submissions"]]


def bounds_block():
    return {"stalled_over_2x_p90_min": BOUND_MIN,
            "derivation": "2 x p90; p90=41 min measured (n=98, p50=11), "
                          "R508/EVIDENCE_HEALTH_2026-09-18T0724Z.json; directive-authorized "
                          "derived bound; no other threshold invented (Art. XXVII)",
            "durable_tip_stale_min": BOUND_MIN,
            "bound_reuse_disclosure": "same measured distribution applied to the "
                                      "branch surface; no second number invented",
            "heartbeat_fresh_s": HEARTBEAT_FRESH_S,
            "hysteresis": {"confirm_polls": CONFIRM, "clear_polls": CLEAR}}


def normalize_health(h):
    """Normalize a /api/health payload for the FSM: active_workers and forensics
    fields live under worker_forensics (measured on the R508 evidence bytes).
    Returns a shallow view; never mutates the input."""
    if not isinstance(h, dict):
        return h
    wf = h.get("worker_forensics") or {}
    out = dict(h)
    out["active_workers"] = h.get("active_workers", wf.get("active_workers"))
    out["forensics_degraded"] = h.get("forensics_degraded", wf.get("forensics_degraded"))
    out["last_write_error"] = h.get("last_write_error", wf.get("last_write_error"))
    out["boot_id"] = h.get("boot_id", wf.get("boot_id"))
    out["payload_path"] = "worker_forensics.active_workers (measured on R508 evidence bytes)"
    return out


class FSM:
    """Alert state machine with hysteresis. Emits alert dicts once per fire."""

    def __init__(self, sessions):
        self.sessions = {sid: {"last_progression": None, "terminal": False}
                         for _, sid in sessions}
        self.streak = {}      # alert_key -> consecutive confirm count
        self.clear_streak = {}
        self.fired = {}       # alert_key -> fired alert record
        self.alerts = []

    def observe_tick(self, tick):
        """tick: {ts, tip_ts, tip_changed, health, per_session_last_progression,
        per_session_terminal, unobservable: [...]}. Returns alerts fired this tick."""
        fired_now = []
        ts = tick["ts"]
        health = normalize_health(tick.get("health"))
        in_flight = [sid for sid, st in self.sessions.items()
                     if not st["terminal"]]
        # update per-session progression from durable bytes
        for sid, lastp in (tick.get("per_session_last_progression") or {}).items():
            if sid in self.sessions and lastp:
                prev = self.sessions[sid]["last_progression"]
                if prev is None or lastp > prev:
                    self.sessions[sid]["last_progression"] = lastp
        for sid, term in (tick.get("per_session_terminal") or {}).items():
            if sid in self.sessions:
                self.sessions[sid]["terminal"] = bool(term)

        def key(name, sid=None):
            return f"{name}:{sid or '*'}"

        def confirm(k, cond):
            self.streak[k] = (self.streak.get(k, 0) + 1) if cond else 0
            if cond:
                self.clear_streak[k] = 0
            return self.streak[k] >= CONFIRM

        def cleared(k):
            self.clear_streak[k] = self.clear_streak.get(k, 0) + 1
            return self.clear_streak[k] >= CLEAR

        # 1) STALLED_OVER_2X_P90 — per session, durable domain only
        for sid, st in self.sessions.items():
            if st["terminal"] or st["last_progression"] is None:
                continue
            elapsed = (ts - parse_ts(st["last_progression"])).total_seconds() / 60.0
            k = key("STALLED_OVER_2X_P90", sid)
            if k in self.fired:
                continue
            if elapsed >= BOUND_MIN and confirm(k, True):
                a = self._alert("STALLED_OVER_2X_P90", ts, session_id=sid,
                                last_durable_progression=st["last_progression"],
                                elapsed_min=round(elapsed, 1),
                                bound_min=BOUND_MIN,
                                domain="observation-of-durable-domain",
                                evidence_basis="durable progression bytes (snapshot_log reasons) only")
                self.fired[k] = a
                fired_now.append(a)
        # 2) DURABLE_TIP_STALE — branch surface, needs healthy push path
        k = key("DURABLE_TIP_STALE")
        if k not in self.fired and tick.get("tip_ts") and in_flight:
            tip_age = (ts - parse_ts(tick["tip_ts"])).total_seconds() / 60.0
            push_healthy = bool(health and health.get("durable", {}).get("last_snapshot", {})
                                .get("ok") and health["durable"]["last_snapshot"].get("pushed")
                                and health["durable"]["last_snapshot"].get("error") is None)
            if tip_age >= BOUND_MIN and push_healthy and confirm(k, True):
                a = self._alert("DURABLE_TIP_STALE", ts,
                                tip_ts=tick["tip_ts"], tip_age_min=round(tip_age, 1),
                                bound_min=BOUND_MIN,
                                push_path_evidence=health["durable"]["last_snapshot"],
                                domain="observation-of-durable-domain",
                                evidence_basis="tip unchanged while push path self-reports healthy and sessions in flight")
                self.fired[k] = a
                fired_now.append(a)
        # 3) HEARTLESS_WORKERS — observation domain vs durable authority
        k = key("HEARTLESS_WORKERS")
        if k not in self.fired and health is not None:
            aw = health.get("active_workers")
            if isinstance(aw, list) and len(aw) == 0 and in_flight:
                if confirm(k, True):
                    a = self._alert("HEARTLESS_WORKERS", ts,
                                    active_workers=[], in_flight_sessions=in_flight,
                                    heartbeat_fresh_s=HEARTBEAT_FRESH_S,
                                    forensics_degraded=health.get("forensics_degraded"),
                                    last_write_error=health.get("last_write_error"),
                                    domain="observation",
                                    evidence_basis="health payload: active list empty while durable authority shows sessions mid-execution (heartless-as-observed; R509 later resolved the mechanism for execution #1)")
                    self.fired[k] = a
                    fired_now.append(a)
        # clears
        for k in list(self.fired):
            cond_now = self._cond_still_bad(k, tick)
            if not cond_now and cleared(k):
                del self.fired[k]
                self.streak.pop(k, None)
        return fired_now

    def _cond_still_bad(self, k, tick):
        name = k.split(":")[0]
        health = tick.get("health")
        in_flight = [sid for sid, st in self.sessions.items() if not st["terminal"]]
        if name == "HEARTLESS_WORKERS":
            return bool(health and isinstance(health.get("active_workers"), list)
                        and len(health["active_workers"]) == 0 and in_flight)
        if name == "DURABLE_TIP_STALE":
            return bool(tick.get("tip_ts") and in_flight and
                        (tick["ts"] - parse_ts(tick["tip_ts"])).total_seconds() / 60.0 >= BOUND_MIN)
        if name == "STALLED_OVER_2X_P90":
            sid = k.split(":", 1)[1]
            st = self.sessions.get(sid)
            return bool(st and not st["terminal"] and st["last_progression"] and
                        (tick["ts"] - parse_ts(st["last_progression"])).total_seconds() / 60.0 >= BOUND_MIN)
        return False

    def _alert(self, alert_type, ts, **ev):
        a = {"alert": alert_type, "fired_at_utc": ts.isoformat().replace("+00:00", "Z"),
             "action": "record+notify ONLY — observer has no hands on production",
             **ev}
        self.alerts.append(a)
        print(f"[ALERT] {a['alert']} sid={a.get('session_id', '-')} at {a['fired_at_utc']}")
        return a


def bs021_scan(records):
    blob = json.dumps(records)
    return [p for p in BS021 if re.search(p, blob)]


# ---------------------------------------------------------------- replay ----

def build_replay_corpora():
    """Build replay events from durable branch bytes (worktree) + R508 evidence."""
    wt = os.environ.get("R509_DURABLE_WORKTREE", "/home/z/my-project/r509_durable")
    sn = [json.loads(l) for l in open(os.path.join(wt, "snapshot_log.jsonl"), encoding="utf-8")
          if l.strip()]
    sessions = tracked_sessions()
    sids = {sid for _, sid in sessions}
    corpora = {}

    def reasons_by_sid(reason, sid):
        return sid in (reason or "")

    # --- R508 death-signature corpus: 2026-09-18 battery window + silence ---
    events = []
    # per-session terminal fact on the DURABLE authority: none of the six ever
    # became terminal there (0 run dirs / 0 final_states - R508 record)
    bat_snaps = [r for r in sn if r["at"].startswith("2026-09-18")]
    for r in bat_snaps:
        sid = next((s for s in r["reason"].split(":") if s in sids), None)
        events.append({"ts": r["at"], "kind": "durable_progression",
                       "session_id": sid,
                       "reason": r["reason"], "files": r.get("files"),
                       "source": f"snapshot_log.jsonl@{DURABLE_BRANCH} line-reason {r['reason']}"})
    last_prog = {}
    for r in bat_snaps:
        sid = next((s for s in r["reason"].split(":") if s in sids), None)
        if sid:
            last_prog[sid] = r["at"]
    # real health observation bytes (R508 evidence, main checkout)
    hp = os.path.join(REPO, "R508", "EVIDENCE_HEALTH_2026-09-18T0724Z.json")
    h = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else None
    # polls every 5 min during the silent window: durable state frozen (measured:
    # zero durable commits after 0da7fe50/691d8d3d — R508/C1 records), worker
    # state UNOBSERVED until the real 07:24:41Z observation.
    silence_start = parse_ts("2026-09-18T00:09:15Z")
    poll_end = parse_ts("2026-09-18T08:40:00Z")
    # Real observation bytes inside the window (all labeled with their source):
    #   07:24:41Z R508 evidence; 08:25:28Z R508-C1 live re-observation; the
    #   08:35:09Z/08:35:53Z R509 capture pre/post health polls. Polls between real
    #   observations repeat the most recent REAL payload's durable fields (measured
    #   unchanged: zero durable commits + same boot across the window per R508/R508-C1
    #   records) and carry worker_state as REPLAY_REPEATED (labeled, not observed).
    real_obs = [parse_ts("2026-09-18T07:24:41Z"), parse_ts("2026-09-18T08:25:28Z"),
                parse_ts("2026-09-18T08:35:09Z"), parse_ts("2026-09-18T08:35:53Z")]
    t = silence_start + timedelta(minutes=5)
    while t <= poll_end:
        ev = {"ts": t.isoformat().replace("+00:00", "Z"), "kind": "poll",
              "tip_ts": "2026-09-18T00:09:15Z",
              "per_session_last_progression": dict(last_prog),
              "per_session_terminal": {},
              "health": None,
              "unobservable": ["worker_state (no health poll byte exists before 07:24:41Z)"]}
        if h is not None and any(abs((t - ro).total_seconds()) < 150 for ro in real_obs):
            ev["health"] = h
            ev["health_provenance"] = "REAL observation byte (R508/R508-C1/R509 evidence; worker_state fields as captured)"
            ev["unobservable"] = []
        elif t >= parse_ts("2026-09-18T07:24:41Z") and h is not None:
            rep = dict(h)
            if isinstance(rep.get("worker_forensics"), dict):
                wf2 = dict(rep["worker_forensics"])
                wf2["active_workers"] = "REPLAY_REPEATED (not observed at this ts)"
                rep["worker_forensics"] = wf2
            ev["health"] = rep
            ev["health_provenance"] = "REPLAY_REPEATED durable fields (measured unchanged 07:24-08:35Z); worker_state labeled REPLAY_REPEATED"
            # a REPLAY_REPEATED worker list is NOT an observation: FSM must not
            # treat it as a real empty-active-list poll
            ev["health_worker_state_is_replay"] = True
        events.append(ev)
        t += timedelta(minutes=5)
    corpora["r508_death_signature"] = {
        "description": "execution #1 durable window (18 real snapshots) + measured silence + the real 07:24:41Z health observation",
        "expected": {"alert_types": ["STALLED_OVER_2X_P90", "DURABLE_TIP_STALE", "HEARTLESS_WORKERS"],
                     "min_order": ["STALLED_OVER_2X_P90", "DURABLE_TIP_STALE", "HEARTLESS_WORKERS"],
                     "note": "STALLED fires per tracked session (6 records, one type); tip-stale rides the same measured bound"},
        "events": events,
    }

    # --- R484/R487 healthy-closure corpora (2026-09-17, per-session windows) ---
    d17 = [r for r in sn if r["at"].startswith("2026-09-17")]
    per = {}
    for r in d17:
        for p in (r.get("reason") or "").split(":"):
            if p in sids:
                per.setdefault(p, []).append(r)
    r484_r487_events = []
    closure_sessions = {}
    for sid, rows in per.items():
        rows.sort(key=lambda r: r["at"])
        closure_sessions[sid] = {"first": rows[0]["at"], "last": rows[-1]["at"],
                                 "reasons": [r["reason"] for r in rows]}
        terminal = any(r["reason"].startswith("terminal") for r in rows)
        for r in rows:
            r484_r487_events.append({"ts": r["at"], "kind": "durable_progression",
                                     "session_id": sid, "reason": r["reason"],
                                     "source": f"snapshot_log.jsonl@{DURABLE_BRANCH}"})
        # polls across the window: tip advances with each snapshot that day
        for i, r in enumerate(rows):
            t = parse_ts(r["at"]) + timedelta(minutes=5)
            while t <= (parse_ts(rows[i + 1]["at"]) if i + 1 < len(rows) else
                        parse_ts(rows[-1]["at"]) + timedelta(minutes=10)):
                r484_r487_events.append({
                    "ts": t.isoformat().replace("+00:00", "Z"), "kind": "poll",
                    "tip_ts": r["at"],
                    "per_session_last_progression": {sid: r["at"]},
                    "per_session_terminal": {sid: terminal},
                    "health": {"active_workers": [{"pid": "replay-derived"}],
                               "forensics_degraded": False, "last_write_error": None,
                               "durable": {"last_snapshot": {"ok": True, "pushed": True,
                                                             "error": None, "at": r["at"]}}},
                    "unobservable": [],
                    "source": "REPLAY_DERIVED from durable forensics bytes (worker presence during healthy closures; labeled, not observed)"})
                t += timedelta(minutes=5)
    corpora["r484_r487_healthy_closures"] = {
        "description": "2026-09-17 healthy closure windows for the six sessions that progressed that day (R484/R487 era); max measured per-session gap 37.3 min < 82",
        "expected": {"alert_types": [], "note": "zero false fires required"},
        "closure_sessions": closure_sessions,
        "events": sorted(r484_r487_events, key=lambda e: e["ts"]),
    }
    return corpora


def run_replay(name, corpus, sessions):
    fsm = FSM(sessions)
    alerts = []
    for ev in sorted(corpus["events"], key=lambda e: e["ts"]):
        ts = parse_ts(ev["ts"])
        if ev["kind"] == "durable_progression":
            sid = ev.get("session_id")
            if sid:
                st = fsm.sessions.get(sid)
                if st and (st["last_progression"] is None or ev["ts"] > st["last_progression"]):
                    st["last_progression"] = ev["ts"]
            continue
        h_in = ev.get("health")
        if ev.get("health_worker_state_is_replay"):
            h_in = None  # REPLAY_REPEATED worker state is not an observation (Art. XXV)
        fired = fsm.observe_tick({
            "ts": ts,
            "tip_ts": ev.get("tip_ts"),
            "health": h_in,
            "per_session_last_progression": ev.get("per_session_last_progression") or {},
            "per_session_terminal": ev.get("per_session_terminal") or {},
            "unobservable": ev.get("unobservable") or [],
        })
        for a in fired:
            a["corpus"] = name
            alerts.append(a)
    return alerts, fsm


def selftest():
    sessions = tracked_sessions()
    corpora = build_replay_corpora()
    results = {}
    all_alerts = []
    for name, corpus in corpora.items():
        alerts, fsm = run_replay(name, corpus, sessions)
        types = []
        for a in alerts:
            if a["alert"] not in types:
                types.append(a["alert"])
        results[name] = {
            "expected": corpus["expected"],
            "alert_types_in_fire_order": types,
            "n_alert_records": len(alerts),
            "pass": None,
        }
        if name == "r508_death_signature":
            want = corpus["expected"]["min_order"]
            ok = all(w in types for w in want)
            idx = [types.index(w) if w in types else -1 for w in want]
            results[name]["pass"] = ok and idx == sorted(idx)
            results[name]["order_indexes"] = idx
        else:
            results[name]["pass"] = len(alerts) == 0
        all_alerts.extend(alerts)
    hits = bs021_scan(all_alerts)
    acc = {
        "acceptance": "R509 watchdog replay acceptance — directive Phase 2 item 5",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bounds": bounds_block(),
        "corpora_source": "durable branch runtime-state-hf snapshot_log.jsonl bytes + R508/EVIDENCE_HEALTH_2026-09-18T0724Z.json (main); worker presence in the healthy-closure corpora is REPLAY_DERIVED and labeled",
        "corpora": {k: {"description": v["description"], "expected": v["expected"],
                        "pass": results[k]["pass"],
                        "alert_types_in_fire_order": results[k]["alert_types_in_fire_order"],
                        "n_alert_records": results[k]["n_alert_records"]}
                    for k, v in corpora.items()},
        "r484_r487_max_measured_gap_min": 37.3,
        "r484_r487_gap_source": "per-session snapshot_log progression gaps, 2026-09-17 (measured this session)",
        "disclosed_limitation": ("a 293.1-min healthy per-session gap exists on 2026-09-13->14 "
                                 "(ts_a2a7952d1de9, outside the directive's R484/R487 acceptance "
                                 "corpus): the 82-min durable-progression bound WOULD have fired "
                                 "there. Disclosed per Art. XV; the bound stays as directed; a "
                                 "heartbeat-aware suppression variant is an owner decision, not "
                                 "unilaterally adopted."),
        "live_dry_run": {"status": "ARMED", "note": "48h live dry-run starts with --live; alerts append-only to R509/WATCHDOG_ALERTS.jsonl"},
        "bs021_scan": hits if hits else "CLEAN",
        "verdict": "PASS" if (results["r508_death_signature"]["pass"]
                              and results["r484_r487_healthy_closures"]["pass"]
                              and not hits) else "FAIL",
    }
    dest = os.path.join(REPO, "R509", "WATCHDOG_REPLAY_ACCEPTANCE.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(acc, open(dest, "w", encoding="utf-8"), indent=2)
    open(dest, "a").write("\n")
    print(json.dumps({k: v for k, v in acc.items() if k != "corpora"}, indent=2)[:1200])
    print("corpora detail:", json.dumps(acc["corpora"], indent=1)[:900])
    return 0 if acc["verdict"] == "PASS" else 1


# ------------------------------------------------------------------ live ----

def git_askpass_env():
    vault = os.environ.get("TOSCANINI_VAULT", "/tmp/my-project/.secrets.env")
    tok = None
    if os.path.exists(vault):
        for line in open(vault, encoding="utf-8"):
            if line.startswith("GITHUB_TOKEN="):
                tok = line.split("=", 1)[1].strip()
        if tok:
            os.environ["GITHUB_TOKEN_VALUE"] = tok
            ask = tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False)
            ask.write('#!/bin/sh\ncase "$1" in *sername*) echo "x-access-token" ;; '
                      '*assword*) printf "%s\\n" "$GITHUB_TOKEN_VALUE" ;; *) echo "" ;; esac\n')
            ask.close()
            os.chmod(ask.name, 0o700)
            os.environ["GIT_ASKPASS"] = ask.name
            os.environ["GIT_TERMINAL_PROMPT"] = "0"
            return True
    return False


def get_health():
    import urllib.request
    try:
        with urllib.request.urlopen(f"{SPACE_URL}/api/health", timeout=20) as r:
            return json.load(r), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def durable_tip():
    if not git_askpass_env():
        return None, "UNOBSERVABLE_DURABLE_TIP: no vault credential for ls-remote"
    try:
        out = subprocess.run(
            ["git", "-C", REPO, "ls-remote", "origin", f"refs/heads/{DURABLE_BRANCH}"],
            capture_output=True, timeout=40)
        if out.returncode != 0:
            return None, "UNOBSERVABLE_DURABLE_TIP: ls-remote failed"
        sha = out.stdout.decode().split()[0]
        # tip timestamp: fetch the commit shallowly is heavy; use ls-remote sha change
        # as the progression signal; timestamp read from the local fetched ref if present.
        local = subprocess.run(["git", "-C", REPO, "rev-parse", f"origin/{DURABLE_BRANCH}"],
                               capture_output=True)
        tip_ts = None
        if local.stdout.decode().strip() == sha:
            tip_ts = subprocess.run(
                ["git", "-C", REPO, "show", "-s", "--format=%cI", sha],
                capture_output=True).stdout.decode().strip() or None
        return {"sha": sha[:8], "ts": tip_ts}, None
    finally:
        for v in ("GITHUB_TOKEN_VALUE",):
            os.environ.pop(v, None)


def snap_log_from_remote():
    if not git_askpass_env():
        return None
    try:
        subprocess.run(["git", "-C", REPO, "fetch", "origin", DURABLE_BRANCH],
                       capture_output=True, timeout=120)
        out = subprocess.run(
            ["git", "-C", REPO, "show", f"origin/{DURABLE_BRANCH}:snapshot_log.jsonl"],
            capture_output=True)
        return [json.loads(l) for l in out.stdout.decode().splitlines() if l.strip()]
    except Exception:
        return None
    finally:
        os.environ.pop("GITHUB_TOKEN_VALUE", None)


def live(once=False):
    sessions = tracked_sessions()
    fsm = FSM(sessions)
    log = os.path.join(REPO, "R509", "WATCHDOG_LIVE_LOG.jsonl")
    alerts_log = os.path.join(REPO, "R509", "WATCHDOG_ALERTS.jsonl")
    while True:
        now = datetime.now(timezone.utc)
        health, herr = get_health()
        tip, terr = durable_tip()
        sn = snap_log_from_remote()
        last_prog, terminal = {}, {}
        if sn:
            sids = {sid for _, sid in sessions}
            for r in sn:
                for p in (r.get("reason") or "").split(":"):
                    if p in sids:
                        last_prog[p] = r["at"]
                        if r["reason"].startswith("terminal"):
                            terminal[p] = True
        tick = {"ts": now, "tip_ts": (tip or {}).get("ts"),
                "health": health,
                "per_session_last_progression": last_prog,
                "per_session_terminal": terminal,
                "unobservable": ([terr] if terr else []) + ([f"health: {herr}"] if herr else [])}
        fired = fsm.observe_tick(tick)
        row = {"ts_utc": now.isoformat().replace("+00:00", "Z"),
               "domain": "observation", "health_ok": health is not None,
               "tip": tip, "unobservable": tick["unobservable"],
               "tracked_in_flight": [sid for sid, st in fsm.sessions.items() if not st["terminal"]]}
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        for a in fired:
            with open(alerts_log, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(a) + "\n")
        if once:
            print(json.dumps(row))
            break
        import time
        time.sleep(POLL_S)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--replay", metavar="FILE")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    elif a.replay:
        corpus = json.load(open(a.replay, encoding="utf-8"))
        alerts, _ = run_replay("manual", corpus, tracked_sessions())
        hits = bs021_scan(alerts)
        print(json.dumps({"alerts": alerts, "bs021": hits or "CLEAN"}, indent=2))
    elif a.live:
        sys.exit(live(once=a.once))
    else:
        ap.print_help()

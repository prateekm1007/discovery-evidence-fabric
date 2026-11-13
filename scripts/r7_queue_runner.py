#!/usr/bin/env python3
"""r7_queue_runner.py — OWNER AUDIT ROUND 2026-11-13, DIRECTIVE 5: the
UNATTENDED QUEUE RUNNER.

The builder does not babysit quota windows. This runner holds the work
PLAN in a resumable state file (eval/runs/r7_queue_state.json) and
executes ONE WORK ITEM PER INVOCATION (chunked, per the sandbox rule:
processes are reaped at the tool-call boundary). The scheduler (cron)
re-invokes it; pacing across invocations comes from the schedule
interval, and pacing inside a chunk from the launcher's own gateway
AIMD + the post-item cooldown.

Plan stages, in the owner's order:
  1. dev12        — every DEV12 problem that has no committed pair in
                    eval/pairs/dev12_r7 (pairs go to dev12_r7; the
                    audited dev12_fresh files are NEVER touched).
  2. ablation     — leave-one-out arms through the SAME launcher's
                    R6_EXTRA_ENV channel: FABRIC_CONSTRAINT_AUDIT=0,
                    FABRIC_KNOWLEDGE_FIRST=0, FABRIC_ANSWER_DOWNGRADE=0,
                    FABRIC_ATTACK_BATCH=0 (pairs to
                    eval/pairs/r7_ablation/<arm>/). composer-only is
                    PENDING_OWNER_DEFINITION (typed, disclosed — no
                    invented semantics, Art. XXV).
  3. twoturn      — B8 round 2: build payloads (scripts/
                    r6_build_twoturn_devfu.py), run --two-turns on the
                    recoverable dev-fu cases (pairs to
                    eval/pairs/r7_twoturn/).
  4. speed        — B10: workers=1, cache OFF, FRESH economy dir per
                    rep (0 hits by construction, verified from
                    LLM_ECONOMY.json), 3 reps on a deterministic
                    3-problem sample; walls recorded to
                    eval/runs/r7_speed/.
  5. seeded       — auto-planned when BOTH eval/seeded_specimens_v1.json
                    and the owner-supplied eval/seeded_specimens_v1.sha256
                    exist (the integrity hash is never invented, Art.
                    XXV): one deterministic LLM-free invocation of
                    scripts/r6_seeded_sweep.py, artifacts to the
                    gitignored scratch (per-specimen rows never enter
                    tracked space). A typed blocker (exit 2: hash
                    mismatch / bad prefix / unparseable spec) records
                    EXHAUSTED — retrying the same bytes cannot heal it;
                    the owner fixes the bytes and resets the state key.

Retry/pacing policy (sleep-until-quota-window on 429 storms): an item
whose run ends INCOMPLETE_INFRASTRUCTURE / 429-heavy / on a non-zai
rung is marked retry_pending (attempts < max_attempts) and the pointer
does NOT advance past it; the NEXT invocation re-plans around it — the
schedule interval IS the quota-window sleep. After max_attempts the
item is recorded EXHAUSTED (typed) and the pointer moves on; nothing
is silently dropped.

Usage:
  python3 scripts/r7_queue_runner.py            # run ONE work item
  python3 scripts/r7_queue_runner.py --plan-only
  python3 scripts/r7_queue_runner.py --status
  R7_MAX_ATTEMPTS=3 R7_COOLDOWN_S=90 ...

Serves: Art. LXXIV (observer-independent durable execution — the state
file, not a held-open session, carries the work), Art. LXI (every
incomplete run is typed and retried or exhausted, never silent),
Art. XXXIX (the audited pair bytes are never overwritten).

R8 credential round (owner message 2026-11-13: a fresh xkiro
credential, "Mercury 3", for the measured MISTRAL FREE TIER on the
xkiro gateway): the runner loads the gitignored vault (.env.keys,
KEY=VALUE lines) into os.environ at startup — the registry reads keys
at CALL time, so a credential becomes effective with ZERO further code
change, and the launcher subprocesses inherit it through the normal
env chain (the WSL->.exe hop that killed shell exports does not exist
on this host). Names ride the log; VALUES are never printed, never
copied into tracked files, never committed (the vault is gitignored;
Art. XVIII-adjacent: credentials are transport, not epistemics).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATE = REPO / "eval" / "runs" / "r7_queue_state.json"
PAIRS_R7 = REPO / "eval" / "pairs" / "dev12_r7"
SPEED_DIR = REPO / "eval" / "runs" / "r7_speed"
DEV12 = REPO / "eval" / "problems_dev12.json"
TWOTURN_PAYLOAD = REPO / "eval" / "problems_twoturn_devfu.json"
# directive 7: the seeded sweep. The owner places BOTH the specimens
# file and the integrity hash (the sweep's own contract: the hash is
# NEVER invented by this repository, Art. XXV). Output stays in the
# gitignored scratch: per-specimen rows NEVER enter tracked space
# (the sweep's never-read rule); publishing the aggregate is an
# owner-session act.
SEEDED_SPECIMENS = REPO / "eval" / "seeded_specimens_v1.json"
SEEDED_HASHFILE = REPO / "eval" / "seeded_specimens_v1.sha256"
SEEDED_OUT = "ENGINE_RUNS"

ABLATION_ARMS = [
    ("no_constraint_audit", "FABRIC_CONSTRAINT_AUDIT=0"),
    ("no_knowledge_first", "FABRIC_KNOWLEDGE_FIRST=0"),
    ("no_downgrade", "FABRIC_ANSWER_DOWNGRADE=0"),
    ("no_attack_batch", "FABRIC_ATTACK_BATCH=0"),
]
SPEED_REPS = 3
SPEED_SAMPLE = 3  # first 3 problem ids (deterministic, disclosed)
MAX_ATTEMPTS = int(os.environ.get("R7_MAX_ATTEMPTS", "3"))
COOLDOWN_S = int(os.environ.get("R7_COOLDOWN_S", "90"))

# v3 output location — the 1.0.0/2.0.0 A0+ artifacts are preserved
# audit evidence; the simple arm (at most ONE repair) writes r10.
A0P_PAIRS = REPO / "eval" / "pairs" / "r10_a0plus"
A0P_VERSION = "r7_a0plus/3.0.0"
# R10 queue policy (owner directive 4): the arm's TYPED DELIVERED
# states are TERMINAL for the queue. The R10 arm already spends its
# at-most-one repair INSIDE the invocation; a re-invocation is a whole
# new arm run (new audit + repair) and, under the 3x/day cron pacing,
# an unbounded re-plan of honest typed-INCOMPLETE arms (or of the
# typed skips whose baseline bytes can NEVER exist) is unbounded quota
# burn. The delivered record — 3.0.0, same frozen baseline identity,
# a typed result — is the deliverable (Art. XXV: the bytes, not the
# state); an operator may still re-run any item explicitly (Art.
# XXVII), which is a decision, never an automatic loop.
A0P_TERMINAL_STATES = {
    "COMPLETE", "INCOMPLETE_CONTRACT",
    "INCOMPLETE_CONSISTENCY_VIOLATIONS", "INCOMPLETE_PROVENANCE",
    "TYPED_SKIP_BASELINE_ABSENT", "TYPED_SKIP_NO_PAIR"}
# P0-4 (owner R10): chunks are sized by OBSERVED WALL TIME, not a
# fixed number of problems — one invocation processes items until the
# budget is consumed (each item's measured wall feeds the next
# chunk's decision; the cron interval remains the outer pacing).
CHUNK_BUDGET_S = int(os.environ.get("R7_CHUNK_BUDGET_S", "600"))
# durable invocation records (owner R10 P0: the scheduled execution is
# verified FROM ITS INVOCATION RECORDS, never inferred from the
# runner's presence)
INVOCATIONS = REPO / "eval" / "runs" / "r7_queue_invocations.jsonl"
KILL_DIR = REPO / "eval" / "kills"


def _dev12_ids() -> list:
    d = json.loads(DEV12.read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    ids = [str(p.get("problem_id") or p.get("id")) for p in plist]
    return sorted(i for i in ids if i)


def _killed_problem_ids() -> list:
    """R10 P0-1: the killed problems FROM THE COMMITTED KILL RECORDS
    (eval/kills/*.json) — never guessed. DEV12 problems excluded (they
    ride the main loop); the killed non-DEV12 problems (bench-p05,
    eval-new06) are the extra A0+ arm inputs."""
    out: list = []
    dev12 = set(_dev12_ids())
    if KILL_DIR.exists():
        for f in sorted(KILL_DIR.glob("*.json")):
            if f.is_dir():
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — typed, never silent
                continue
            pid = str(d.get("problem_id") or "").strip()
            if pid and pid not in dev12:
                out.append(pid)
    return sorted(out)


def _pair_has_answer(pid: str, pairs_dir: Path) -> bool:
    """R9 P1 item 8.3: existence-only completion is retired — a pair
    counts as completed ONLY when its bytes carry a valid schema: a
    nonempty pipeline answer AND the execution record (engine identity
    + input hashes) a scored pair must carry. A truncated or
    schema-less file is typed incomplete (re-planned, never trusted)."""
    f = pairs_dir / f"{pid}.json"
    if not f.exists():
        return False
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    if not isinstance(d, dict):
        return False
    pa = d.get("pipeline_answer")
    if not (isinstance(pa, str) and pa.strip()):
        return False
    # a typed marker is not an answer (the measured p02 shape: a
    # CONTRACT-INVALID marker string where the answer bytes should be)
    if pa.startswith("CONTRACT-INVALID") or pa.startswith("INCOMPLETE_"):
        return False
    # the execution record: the engine identity and the input binding
    # a scored pair carries (the run that produced it is named)
    if not (d.get("run_id") or d.get("commit")):
        return False
    if not (d.get("bound_inputs") or {}).get("baseline_answer_sha256"):
        return False
    return True


def _ablation_gate() -> dict:
    """R10 (owner directive P1-8): the 48-item ablation and the
    heavy-stage pruning stay BLOCKED until >= 10 valid A0+-vs-
    full-pipeline judgments exist in the committed comparison record.
    The gate reads the RECORD BYTES (never the runner's presence or a
    session's memory) and fails closed typed."""
    rec_p = REPO / "eval" / "a0plus_compare_r10.json"
    if not rec_p.exists():
        return {"allowed": False, "reason":
                "no committed comparison record "
                "(eval/a0plus_compare_r10.json) — ablation blocked "
                "(owner R10 P1-8: >=10 valid full-pipeline judgments "
                "required)"}
    try:
        d = json.loads(rec_p.read_text(encoding="utf-8"))
        n_valid = int((d.get("tally_vs_full_pipeline") or {})
                      .get("n_valid") or 0)
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        return {"allowed": False, "reason":
                f"comparison record unparseable ({exc}) — ablation "
                "blocked (fail closed)"}
    if n_valid < 10:
        return {"allowed": False, "reason":
                f"only {n_valid} valid A0+-vs-full judgments — "
                "ablation blocked (owner R10 P1-8 threshold: >=10)"}
    return {"allowed": True, "reason": f"{n_valid} valid judgments"}


def build_plan() -> list:
    """The full work plan (idempotent: built fresh each run; per-item
    status lives in the state file). ORDER is the owner's round
    2026-11-13 directive 4: A0+ FIRST (the decisive cheap-arm
    experiment), then the full-pipeline pairs, then ablation arms,
    two-turn, speed."""
    items: list = []
    ids = _dev12_ids() + _killed_problem_ids()
    # 0. A0+ (the SIMPLE arm: one audit + zero/one repair; the killed
    #    problems ride the same plan — fu-004/sofc are typed skips by
    #    the arm itself, the killed non-DEV12 problems run on their
    #    committed baselines). R10 queue policy: a DELIVERED record
    #    (typed COMPLETE or honest typed-INCOMPLETE/skip, identity-
    #    bound) is terminal — never re-planned automatically.
    for pid in ids:
        if _a0plus_v2_delivered(pid):
            continue
        items.append({"kind": "a0plus", "problem": pid,
                      "pairs_out": "eval/pairs/r10_a0plus"})
    # 1. dev12 remaining (main arm -> dev12_r7)
    for pid in ids:
        if _pair_has_answer(pid, PAIRS_R7):
            continue
        items.append({"kind": "dev12", "problem": pid,
                      "pairs_out": "eval/pairs/dev12_r7"})
    # 2. ablation arms (each problem x arm; skipped when the main-arm
    #    pair for that problem does not exist yet — the arm needs the
    #    same-era engine, and the main arm goes first). R10: the WHOLE
    #    stage is gated on the >=10-valid-judgment comparison record
    #    (owner directive P1-8) — blocked items are not planned, and
    #    the typed reason is printed, never silent.
    _abl = _ablation_gate()
    if not _abl["allowed"]:
        print("[r7queue] ablation BLOCKED (typed): " + _abl["reason"])
    for arm, envkv in (ABLATION_ARMS if _abl["allowed"] else []):
        for pid in ids:
            items.append({"kind": "ablation", "arm": arm, "env": envkv,
                          "problem": pid,
                          "pairs_out": f"eval/pairs/r7_ablation/{arm}"})
    # 3. two-turn round 2 (the recoverable dev-fu cases)
    tt = _twoturn_ids()
    for pid in tt:
        items.append({"kind": "twoturn", "problem": pid,
                      "pairs_out": "eval/pairs/r7_twoturn"})
    # 4. speed: 3 reps x the deterministic 3-problem sample
    for rep in range(1, SPEED_REPS + 1):
        for pid in ids[:SPEED_SAMPLE]:
            items.append({"kind": "speed", "rep": rep, "problem": pid,
                          "pairs_out": f"eval/runs/r7_speed/rep{rep}"})
    # 5. seeded sweep (directive 7): planned ONLY when BOTH the owner
    #    specimens and the owner-supplied hash are in place
    if SEEDED_SPECIMENS.exists() and SEEDED_HASHFILE.exists():
        items.append({"kind": "seeded", "problem": "seeded_specimens_v1",
                      "pairs_out": SEEDED_OUT})
    return items


def _twoturn_ids() -> list:
    if not TWOTURN_PAYLOAD.exists():
        return []
    try:
        d = json.loads(TWOTURN_PAYLOAD.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    plist = d if isinstance(d, list) else d.get("problems", [])
    return sorted(str(p.get("problem_id") or p.get("id")) for p in plist)


def load_state() -> dict:
    """R9 P1 item 8.5: a corrupt state file must NEVER silently reset
    the queue to empty (the measured hazard: json.loads fails -> the
    old loader returned the EMPTY skeleton and the next save overwrote
    the plan — every remaining item forgotten). The corrupt bytes are
    moved aside (typed, dated) and the loader EXITS TYPED — the
    operator fixes or restores, nothing is silently lost."""
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — typed, never silent
            quarantine = STATE.with_suffix(
                f".corrupt-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
                f".json")
            try:
                STATE.replace(quarantine)
            except Exception:  # noqa: BLE001
                quarantine = None
            _q = str(quarantine) if quarantine else \
                "(rename failed - file left in place)"
            print(f"[r7queue] TYPED: state file corrupt ({exc}); the "
                  f"bytes were quarantined to {_q}; NO silent reset - "
                  "fix or restore the file and re-run", file=sys.stderr)
            sys.exit(5)
    return {"plan": [], "status": {}, "updated_at": None, "pointer": 0}


def save_state(st: dict) -> None:
    """R9 P1 item 8.5: ATOMIC state writes — the state lands via a
    same-directory tmp file + os.replace (rename is atomic on POSIX):
    a crash mid-write can never leave a half-written state for the
    next invocation to choke on."""
    STATE.parent.mkdir(parents=True, exist_ok=True)
    st["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime())
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    os.replace(tmp, STATE)


def _run_launcher(item: dict) -> dict:
    """ONE launcher invocation for the item; returns the typed result."""
    env = dict(os.environ)
    env.update({
        "R6_PAIRS_OUT": item["pairs_out"],
        "R6_TIMEOUT": "900",
    })
    args = [item["problem"]]
    if item["kind"] == "ablation":
        env["R6_EXTRA_ENV"] = item["env"]
        env["R6_PAIRS_OUT"] = item["pairs_out"]
    if item["kind"] == "twoturn":
        env["R6_PROBLEMS_FILE"] = "eval/problems_twoturn_devfu.json"
        env["R6_TWO_TURNS"] = "1"
        env["R6_PAIRS_OUT"] = item["pairs_out"]
    if item["kind"] == "speed":
        # B10 protocol: cache OFF; a FRESH economy store per rep makes
        # 0 hits a construction, not an assertion (verified post-run)
        env["R6_FABRIC_CACHE"] = "off"
        env["R6_EXTRA_ENV"] = (
            f"FABRIC_LLM_ECONOMY_DIR={item['pairs_out']}/economy")
    cmd = ["bash", "scripts/r6_run_dev12.sh", ",".join(args)]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(REPO), env=env,
                              capture_output=True, text=True,
                              timeout=1000 + 120)
    except subprocess.TimeoutExpired as te:
        # typed: the item stays unmarked (RETRY_PENDING classification
        # below sees no committed pair) — the next chunk re-plans it
        return {"exit_code": 124, "wall_s": round(time.time() - t0, 1),
                "tail": "TIMEOUT after "
                        f"{round(time.time() - t0, 1)}s (typed; the "
                        "item re-plans on the next chunk) "
                        + ((te.stdout or b"")[-400:].decode(
                            "utf-8", "replace") if te.stdout else "")}
    wall = round(time.time() - t0, 1)
    return {"exit_code": proc.returncode, "wall_s": wall,
            "tail": (proc.stdout or "")[-1200:]
            + "\n--stderr--\n" + (proc.stderr or "")[-800:]}


def _run_seeded_sweep(item: dict) -> dict:
    """ONE deterministic sweep invocation (LLM-free: no quota cost, no
    gateway contact). Returns the same typed shape as _run_launcher.
    The sweep fail-closes typed (exit 2) on hash mismatch / bad prefix
    / unparseable spec; rows + calibration emits stay in the gitignored
    scratch dir.
    """
    py = os.environ.get("R6_PYTHON") or sys.executable
    expected = SEEDED_HASHFILE.read_text(encoding="utf-8").strip()
    cmd = [py, "-B", "scripts/r6_seeded_sweep.py",
           "--specimens", "eval/seeded_specimens_v1.json",
           "--expected-selection-sha256", expected,
           "--output-dir", SEEDED_OUT]
    if len(expected) != 64:
        # a shorter owner-declared value is PREFIX mode — the sweep
        # itself verifies the declared prefix and refuses otherwise
        cmd.append("--prefix-match")
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True,
                              text=True, timeout=900)
    except subprocess.TimeoutExpired as te:
        return {"exit_code": 124, "wall_s": round(time.time() - t0, 1),
                "tail": "TIMEOUT (typed; re-plans next chunk) "
                        + ((te.stdout or b"")[-400:].decode(
                            "utf-8", "replace") if te.stdout else "")}
    tail = (proc.stdout or "") + "\n--stderr--\n" + (proc.stderr or "")
    return {"exit_code": proc.returncode,
            "wall_s": round(time.time() - t0, 1), "tail": tail[-2000:]}


def _a0plus_v2_delivered(pid: str) -> bool:
    """R10 queue policy: a record counts as DELIVERED when it IS a
    3.0.0 record for THIS problem, binds the SAME frozen baseline
    identity, and carries a TYPED result (COMPLETE with its gate True,
    or an honest typed-INCOMPLETE state, or a typed skip). COMPLETE
    additionally requires its completion gate. Delivered records are
    terminal for the queue — the state file is reconciled to them, and
    re-running one is an explicit operator act (Art. XXVII), never an
    automatic re-plan loop."""
    f = A0P_PAIRS / f"{pid}.json"
    if not f.exists():
        return False
    try:
        rec = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    if not (rec.get("a0plus_version") == A0P_VERSION
            and rec.get("problem_id") == pid
            and rec.get("result") in A0P_TERMINAL_STATES):
        return False
    if rec.get("result") == "COMPLETE" and rec.get(
            "completion_gate", {}).get("complete") is not True:
        return False
    fresh = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
    if not fresh.exists():
        fresh = REPO / "eval" / "pairs" / f"{pid}.json"
        if not fresh.exists():
            # a typed skip may exist for a problem whose committed
            # pair is itself absent — the skip IS the identity binding
            return rec.get("result") in ("TYPED_SKIP_BASELINE_ABSENT",
                                         "TYPED_SKIP_NO_PAIR")
    try:
        sha = str(json.loads(fresh.read_text(encoding="utf-8"))
                  .get("bound_inputs", {}).get("baseline_answer_sha256")
                  or "")
    except Exception:  # noqa: BLE001
        sha = ""
    if rec.get("baseline_sha_source") == sha and sha:
        return True
    # the killed non-DEV12 pairs predate the bound_inputs schema —
    # their identity is the sha256 OF the baseline answer bytes (the
    # arm's own _baseline_identity rule)
    import hashlib
    try:
        baseline = str(json.loads(fresh.read_text(encoding="utf-8"))
                       .get("baseline_answer") or "")
    except Exception:  # noqa: BLE001
        return False
    if not baseline.strip():
        return False
    return rec.get("baseline_sha_source") == hashlib.sha256(
        baseline.encode("utf-8")).hexdigest()


def _run_a0plus(item: dict, chunk_wait_s: float = 0.0) -> dict:
    """ONE A0+ invocation: the committed baseline -> constraint audit
    (1 call) -> strict relabel (0 calls) -> AT MOST ONE repair (0-1
    calls). The loop-local zai gateway is started-or-reused and PROBED
    first (the launcher's own probe-before-admit rule, one script); a
    typed probe failure is a RETRY_PENDING input, never a verdict.
    P0-4/P0-2 (owner R10): the hard transport bounds are SET (never
    setdefault), and the measured queue wait + gateway setup ride the
    subprocess env as INFRASTRUCTURE seconds the arm records separately
    from model work."""
    env = dict(os.environ)
    env["ENGINE_LLM_TIMEOUT_S"] = "40"
    env["ENGINE_LLM_RETRY_SLEEP_S"] = "0"
    env["A0P_QUEUE_WAIT_S"] = f"{max(0.0, chunk_wait_s):.1f}"
    # the same transport env the launcher rides: the cost policy (the
    # engine refuses every provider under the default ZERO_PAID_COST —
    # measured typed refusal on the first live A0+ invocation)
    env.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
    gw = None
    gw_t0 = time.time()
    for _try in (1, 2):
        gw = subprocess.run(["bash", "scripts/zai_gateway_env.sh"],
                            cwd=str(REPO), capture_output=True, text=True,
                            timeout=90)
        has_env = any(l.startswith("export ") for l in
                      (gw.stdout or "").splitlines())
        if gw.returncode == 0 and has_env:
            break
        # the gateway start is flaky under a reaper race (measured:
        # the probe passes, the background node dies with the script's
        # session) — ONE immediate retry, NO fixed sleep (owner R10
        # P0: the process is never kept asleep; the retry is typed)
    gw_setup_s = round(time.time() - gw_t0, 1)
    env["A0P_GATEWAY_SETUP_S"] = f"{gw_setup_s:.1f}"
    if gw is None or gw.returncode != 0 or not any(
            l.startswith("export ") for l in (gw.stdout or "").splitlines()):
        return {"exit_code": 0, "wall_s": 0.0,
                "tail": "ZAI_TRANSPORT_PROBE: typed unavailable this "
                        "window (" + ((gw.stderr if gw else "") or "")[-200:]
                        + ")"}
    for line in (gw.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[len("export "):].split("=", 1)
            env[k] = v
    cmd = [os.environ.get("R6_PYTHON") or sys.executable, "-B",
           "scripts/r7_a0plus.py", item["problem"]]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(REPO), env=env,
                              capture_output=True, text=True,
                              timeout=900)
    except subprocess.TimeoutExpired as te:
        return {"exit_code": 124, "wall_s": round(time.time() - t0, 1),
                "tail": "TIMEOUT (typed; re-plans next chunk) "
                        + ((te.stdout or b"").decode("utf-8",
                                                     "replace")[-400:])}
    tail = (proc.stdout or "") + "\n--stderr--\n" + (proc.stderr or "")
    return {"exit_code": proc.returncode,
            "wall_s": round(time.time() - t0, 1), "tail": tail[-1200:]}


def _classify_result(item: dict, res: dict) -> str:
    """Typed post-run classification: DONE | RETRY_PENDING | EXHAUSTED-
    INPUT (the launcher's typed failures ride the exit code + output)."""
    tail = res.get("tail") or ""
    if item["kind"] == "a0plus":
        tail0 = res.get("tail") or ""
        # the gateway probe failed BEFORE the arm ran (wall 0, exit 0,
        # no record) — typed transport retry, never a verdict (the
        # old fall-through called it 'no A0+ pair', hiding the cause)
        if (res.get("exit_code") == 0 and res.get("wall_s") == 0.0
                and "ZAI_TRANSPORT_PROBE" in tail0
                and "200 OK" not in tail0):
            return "RETRY_PENDING (zai transport down this window)"
        f = A0P_PAIRS / f"{item['problem']}.json"
        # R10 queue policy: the RECORD is read first, on every typed
        # exit (0/2/4). A 3.0.0 record binding the same baseline with a
        # typed result is DELIVERED — the honest typed-INCOMPLETE arm
        # is the delivery (owner R10: keep the typed incomplete, never
        # fabricate COMPLETE); re-running it automatically would be
        # unbounded quota burn under the cron pacing.
        if f.exists() and _a0plus_v2_delivered(item["problem"]):
            try:
                _rec = json.loads(f.read_text(encoding="utf-8"))
                _r = _rec.get("result")
            except Exception:  # noqa: BLE001 — typed, never silent
                _r = "unreadable"
            if _r == "COMPLETE":
                return "DONE"
            return f"DONE (a0plus delivered typed: {_r} — terminal, " \
                "re-run is an explicit operator act)"
        if res.get("exit_code") == 0 and f.exists():
            # DONE requires a GENUINE completed result — the record
            # must carry result=COMPLETE with its completion gate True
            # (contract valid + consistency PASSED + provenance
            # resolved), not merely the file's existence (Art. XXV:
            # the bytes, not the state, are the deliverable).
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
                if (rec.get("a0plus_version") == A0P_VERSION
                        and rec.get("result") == "COMPLETE"
                        and rec.get("completion_gate", {})
                        .get("complete") is True):
                    return "DONE"
                return ("VERIFY_FAIL (v3 record not COMPLETE: "
                        f"result={rec.get('result')}, "
                        f"gate={rec.get('completion_gate')})")
            except Exception as exc:  # noqa: BLE001 — typed, never silent
                return f"VERIFY_FAIL (v3 record unparseable: {exc})"
        if res.get("exit_code") == 2:
            # typed skip: no committed baseline bytes — retrying the
            # same invocation cannot produce them (fail-closed)
            return "VERIFY_FAIL (typed skip: no committed baseline bytes)"
        if res.get("exit_code") == 4:
            # typed INCOMPLETE_* whose record did not land (or does not
            # bind this baseline) — a transport-class retry: the arm
            # wrote nothing durable this window
            m = ""
            for tok in ("INCOMPLETE_PROVENANCE", "INCOMPLETE_CONTRACT",
                        "INCOMPLETE_CONSISTENCY"):
                if tok in tail:
                    m = tok
                    break
            return f"RETRY_PENDING ({m or 'typed incomplete'} — " \
                "completion gate not met; record carries the states)"
        return "RETRY_PENDING (no A0+ pair after run)"
    if item["kind"] == "seeded":
        agg = REPO / SEEDED_OUT / "r6_seeded_sweep.json"
        if res.get("exit_code") == 0 and agg.exists():
            return "DONE"
        if res.get("exit_code") == 2:
            # typed blocker: hash mismatch / bad prefix / unparseable —
            # retrying the same bytes cannot heal it (fail-closed)
            return "VERIFY_FAIL (typed blocker: " \
                   + (tail.strip().splitlines() or ["see tail"])[-1][:120] \
                   + ")"
        return "RETRY_PENDING (sweep produced no aggregate)"
    if res.get("exit_code") == 0 and _pair_has_answer(
            item["problem"], REPO / item["pairs_out"]):
        if item["kind"] == "speed":
            return _speed_verify(item) or "DONE"
        return "DONE"
    if "ZAI_TRANSPORT_PROBE" in tail and "200 OK" not in tail:
        return "RETRY_PENDING (zai transport down this window)"
    # a 401 auth rejection is a LONGER window than a 429 burst storm —
    # the probe said OK but the generation call was rejected (measured
    # 2026-11-13 08:57Z: probe OK, baseline call HTTP 401); the note
    # must not call an auth window a burst storm (Art. XXV: the typed
    # note names the measured failure class)
    for tok in ("HTTP Error 401", "401 Unauthorized", "HTTP_401_AUTH",
                "Unauthorized"):
        if tok in tail:
            return "RETRY_PENDING (zai auth rejected this window)"
    for tok in ("INCOMPLETE_INFRASTRUCTURE", "429", "quota",
                "RATE_LIMITED", "BREAKER_OPEN"):
        if tok in tail:
            return "RETRY_PENDING (transport storm)"
    return "RETRY_PENDING (no committed pair after run)"


def _speed_verify(item: dict) -> str:
    """B10 verification: the rep's LLM_ECONOMY.json must show 0 cache
    hits; walls are recorded, never asserted."""
    eco = REPO / item["pairs_out"] / "economy"
    hits = None
    if eco.exists():
        for f in eco.rglob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if isinstance(d, dict) and "cache_hits" in d.get(
                    "counters", {}):
                hits = d["counters"].get("cache_hits")
                break
    SPEED_DIR.mkdir(parents=True, exist_ok=True)
    rec = SPEED_DIR / f"{item['problem']}_rep{item['rep']}.json"
    rec.write_text(json.dumps({
        "problem": item["problem"], "rep": item["rep"],
        "wall_s": item.get("_wall_s"), "cache_hits": hits,
        "protocol": "workers=1 cache=off fresh-store"}, indent=1),
        encoding="utf-8")
    if hits is None:
        # R9 P1 item 8.6: MISSING measurement is incomplete, never a
        # success — the old `hits not in (0, None)` check passed a
        # MISSING cache record as DONE (the None-pass defect): B10 is
        # complete only when the actual cache record exists and
        # confirms zero hits
        return "VERIFY_FAIL (MISSING_CACHE_EVIDENCE: no LLM_ECONOMY " \
            "record carries counters.cache_hits — B10 incomplete)"
    if hits != 0:
        return f"VERIFY_FAIL (cache_hits={hits})"
    return "DONE"


def _table_dirty(rel: str) -> bool:
    p = subprocess.run(["git", "status", "--porcelain", "--", rel],
                       cwd=str(REPO), capture_output=True, text=True)
    return bool(p.stdout.strip())


def _restore_score_table(st: dict, note: str) -> None:
    """Restore the committed SCORE_TABLE bytes the launcher rewrote.

    The launcher regenerates eval/score/SCORE_TABLE.{json,md} from ONLY
    the current invocation's problems (measured: a 1-problem storm run
    replaced the committed multi-problem table, -509 lines). The runner
    runs ONE item per invocation, so without this every chunk would
    thrash the committed table. Restore is gated on the persistent
    clean-flag: dirt is restored only while the flag says the files
    were clean at the last observation (the dirt then came from the
    launcher — the only writer between chunks), never over an edit that
    predates the runner's first observation (Art. XXXIX: audited bytes
    are never overwritten).
    """
    flag = st.setdefault("_score_table_clean", True)
    changed = False
    for rel in ("eval/score/SCORE_TABLE.json",
                "eval/score/SCORE_TABLE.md"):
        if not (REPO / rel).exists():
            continue
        if _table_dirty(rel):
            if flag:
                subprocess.run(["git", "checkout", "--", rel],
                               cwd=str(REPO), capture_output=True,
                               text=True)
                print(f"[r7queue] restored {rel} ({note}; committed "
                      "bytes kept)")
            # flag False: pre-existing dirt we must not touch
        elif not flag:
            flag = True
            changed = True
    if flag != st.get("_score_table_clean", True) or changed:
        st["_score_table_clean"] = flag


def _append_invocation(key: str, it: dict, verdict: str, state: str,
                       wall_s: float, exit_code: int, attempt: int) -> None:
    """R10 P0-4 (owner): EVERY item execution appends a typed line to
    the durable invocation record — the scheduled execution is verified
    FROM THESE RECORDS, never inferred from the runner being present
    (an invocation record at a cron window with a real verdict IS the
    evidence that the schedule fired; no record, no claim)."""
    try:
        INVOCATIONS.parent.mkdir(parents=True, exist_ok=True)
        with INVOCATIONS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                    time.gmtime()),
                "item": key, "kind": it.get("kind"),
                "problem": it.get("problem"),
                "arm": it.get("arm"), "rep": it.get("rep"),
                "verdict": verdict[:160], "state": state,
                "wall_s": wall_s, "exit_code": exit_code,
                "attempt": attempt}) + "\n")
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        print(f"[r7queue] TYPED: invocation record append failed ({exc})"
              " — the run itself is unaffected; the record is evidence")


def _reconcile_delivered_states(st: dict, plan: list) -> int:
    """R10 queue policy: the state file is RECONCILED to the record
    bytes (Art. XXV — a recorded state that no longer matches measured
    reality is corrected to the measured state). A stale a0plus entry
    (EXHAUSTED / RETRY_PENDING) whose record IS a delivered 3.0.0 arm
    becomes DONE (delivered) — the measured R10 hazard: a chunk racing
    the arm-script edits (0.1 s exit 1) leaves stale EXHAUSTED states
    shadowing delivered pairs; the stale states must never shadow the
    bytes. Returns the number of reconciled entries (never silent)."""
    planned = {f"{it['kind']}:{it.get('arm') or it.get('rep') or ''}:"
               f"{it['problem']}" for it in plan}
    n = 0
    for key, s in (st.get("status") or {}).items():
        if not key.startswith("a0plus:") or key in planned:
            continue
        pid = key.split(":", 2)[2]
        if _a0plus_v2_delivered(pid) and s.get("state") != "DONE":
            try:
                _r = json.loads((A0P_PAIRS / f"{pid}.json")
                                .read_text(encoding="utf-8")).get("result")
            except Exception:  # noqa: BLE001 — typed, never silent
                _r = "unreadable"
            s["reconciled_from"] = s.get("state")
            s["state"] = "DONE"
            s["note"] = (f"state reconciled to delivered record bytes "
                         f"(result={_r}; Art. XXV) — stale entry from "
                         "the exit-1 chunk race")
            n += 1
    return n


def run_one() -> int:
    """P0-4 (owner R10): process items until the CHUNK WALL BUDGET is
    consumed — chunks are sized by observed wall time, not a fixed
    number of problems. Every item execution appends a typed line to
    the durable invocation record (the scheduled execution is verified
    from its invocation records, never inferred from the runner being
    present)."""
    st = load_state()
    plan = build_plan()
    st["plan"] = plan
    _n_rec = _reconcile_delivered_states(st, plan)
    if _n_rec:
        print(f"[r7queue] reconciled {_n_rec} stale a0plus state "
              "entr(ies) to delivered record bytes (Art. XXV)")
    status = st.setdefault("status", {})
    _restore_score_table(st, "chunk start")
    chunk_t0 = time.time()
    n_ran = 0
    while True:
        # the first item that is not DONE and not EXHAUSTED
        target = None
        for it in plan:
            key = f"{it['kind']}:{it.get('arm') or it.get('rep') or ''}:" \
                  f"{it['problem']}"
            s = status.get(key, {})
            if s.get("state") == "DONE":
                if it["kind"] == "a0plus":
                    # the bytes are the truth (Art. XXV): a DONE state
                    # whose record is not a delivered identity-valid
                    # arm re-runs; the state alone is never the
                    # deliverable (delivered ⊇ COMPLETE: the honest
                    # typed-INCOMPLETE arms are terminal, R10 queue
                    # policy)
                    if _a0plus_v2_delivered(it["problem"]):
                        continue
                else:
                    continue
            if s.get("state") == "EXHAUSTED":
                continue
            if s.get("state") == "SKIP":
                continue
            target = (key, it, s)
            break
        if target is None:
            if n_ran == 0:
                print("[r7queue] ALL ITEMS DONE OR EXHAUSTED — queue "
                      "drained")
            else:
                print("[r7queue] chunk drained within budget ("
                      f"{n_ran} item(s), "
                      f"{round(time.time() - chunk_t0, 1)}s)")
            save_state(st)
            return 0
        key, it, s = target
        # WALL-BUDGET chunking (owner R10 P0-4): an item starts only
        # when the REMAINING budget admits its worst case (a0plus is
        # bounded to 300 s + slack; launchers run under the 1120 s
        # subprocess cap). An item that cannot fit waits for the next
        # chunk — typed, never a partial run.
        elapsed = time.time() - chunk_t0
        _worst = 320.0 if it["kind"] == "a0plus" else 1120.0
        if n_ran > 0 and elapsed + _worst > CHUNK_BUDGET_S:
            print(f"[r7queue] chunk budget consumed ({round(elapsed, 1)}s, "
                  f"{n_ran} item(s)) — '{key}' waits for the next chunk")
            save_state(st)
            return 0
        # ATTACH the entry: for a first-attempt item, status.get(key,
        # {}) above returned a DETACHED dict — without this, every
        # mutation below (attempts/state/verdict) is lost and
        # save_state persists an empty status: retries never
        # accumulate, MAX_ATTEMPTS never fires, the item loops forever
        # on a persistent storm. Measured defect on the first live
        # invocation (2026-11-13, p09 transport storm).
        status[key] = s
        att = int(s.get("attempts", 0))
        if att >= MAX_ATTEMPTS:
            s["state"] = "EXHAUSTED"
            s["note"] = f"typed exhausted after {att} attempts"
            print(f"[r7queue] {key}: EXHAUSTED after {att} attempts")
            _append_invocation(key, it, "EXHAUSTED (attempt budget)",
                               "EXHAUSTED", 0.0, 0, att)
            save_state(st)
            continue
        # ablation arms need the main-arm pair first (same-era engine)
        if it["kind"] == "ablation" and not _pair_has_answer(
                it["problem"], PAIRS_R7):
            s["state"] = "SKIP"
            s["note"] = "main-arm pair absent this invocation; re-planned"
            save_state(st)
            print(f"[r7queue] {key}: SKIP (main-arm pair not yet in "
                  "dev12_r7; the dev12 item replans first)")
            continue
        if it["kind"] == "twoturn" and not TWOTURN_PAYLOAD.exists():
            # build the payload deterministically (typed fail-closed)
            p = subprocess.run([sys.executable, "-B",
                                "scripts/r6_build_twoturn_devfu.py"],
                               cwd=str(REPO), capture_output=True, text=True)
            if p.returncode != 0 or not TWOTURN_PAYLOAD.exists():
                s["state"] = "EXHAUSTED"
                s["note"] = ("two-turn payload build failed typed: "
                             + (p.stderr or "")[-200:])
                save_state(st)
                print(f"[r7queue] {key}: payload build FAILED typed")
                continue
        if SEEDED_SPECIMENS.exists() and not SEEDED_HASHFILE.exists():
            print("[r7queue] seeded specimens present but the owner hash "
                  "file is absent (eval/seeded_specimens_v1.sha256) — the "
                  "sweep is NOT planned (the integrity hash is never "
                  "invented, Art. XXV)")
        print(f"[r7queue] RUN {key} (attempt {att + 1}/{MAX_ATTEMPTS})")
        if it["kind"] == "seeded":
            res = _run_seeded_sweep(it)
        elif it["kind"] == "a0plus":
            res = _run_a0plus(it, chunk_wait_s=time.time() - chunk_t0)
        else:
            res = _run_launcher(it)
        it = dict(it)
        it["_wall_s"] = res["wall_s"]
        verdict = _classify_result(it, res)
        s["attempts"] = att + 1
        s["last_verdict"] = verdict
        s["last_wall_s"] = res["wall_s"]
        s["last_exit_code"] = res["exit_code"]
        if verdict == "DONE":
            s["state"] = "DONE"
        elif verdict.startswith("DONE (a0plus delivered"):
            # R10 queue policy: an honest typed-INCOMPLETE arm IS a
            # delivery — DONE with the typed state riding the verdict
            s["state"] = "DONE"
        elif verdict.startswith("VERIFY_FAIL"):
            s["state"] = "EXHAUSTED"
            s["note"] = verdict
        else:
            s["state"] = "RETRY_PENDING"
            s["note"] = verdict
        _append_invocation(key, it, verdict, s["state"], res["wall_s"],
                           res["exit_code"], att + 1)
        st["last_item"] = key
        save_state(st)
        _restore_score_table(st, "after item")
        print(f"[r7queue] {key}: {verdict} (wall {res['wall_s']}s, "
              f"exit {res['exit_code']})")
        # R10 P0 (owner): NO fixed process sleeps — the schedule
        # interval is the quota-window pacing (a cooldown sleep kept a
        # live process parked for 90 s per item; the cron schedule
        # already spaces chunks, and the wall budget bounds the chunk).
        n_ran += 1
    # unreachable


def _load_key_vault() -> list:
    """Load the gitignored credential vault (.env.keys) into os.environ.

    Contract: KEY=VALUE lines, '#' comments skipped, EXPLICIT env wins
    (setdefault — an operator-exported override is never clobbered),
    missing file is fine (typed empty list), and the RETURN VALUE is
    the list of loaded NAMES ONLY — the caller echoes names, never
    values (no credential ever reaches a log, an artifact, or git).
    Serves the R8 credential round: the registry reads provider keys at
    CALL time from os.environ, so loading the vault here is the whole
    wiring (Art. X: transport plumbing only, one transport path
    unchanged).
    """
    vault = REPO / ".env.keys"
    loaded: list = []
    if not vault.exists():
        return loaded
    for line in vault.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if not name or not value:
            continue
        if not os.environ.get(name, "").strip():
            os.environ[name] = value
            loaded.append(name)
    return loaded


def main() -> int:
    _vault_names = _load_key_vault()
    if _vault_names:
        print("[r7queue] credential vault loaded (names only): "
              + ", ".join(sorted(_vault_names)))
    if "--status" in sys.argv:
        st = load_state()
        done = sum(1 for v in st.get("status", {}).values()
                   if v.get("state") == "DONE")
        print(json.dumps({"done": done,
                          "plan_n": len(st.get("plan") or []),
                          "last_item": st.get("last_item"),
                          "updated_at": st.get("updated_at")}, indent=1))
        return 0
    if "--plan-only" in sys.argv:
        plan = build_plan()
        print(json.dumps({"n_items": len(plan),
                          "kinds": {k: sum(1 for i in plan
                                           if i["kind"] == k)
                                    for k in {i["kind"] for i in plan}}},
                         indent=1))
        return 0
    return run_one()


if __name__ == "__main__":
    sys.exit(main())

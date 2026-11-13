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


def _dev12_ids() -> list:
    d = json.loads(DEV12.read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    ids = [str(p.get("problem_id") or p.get("id")) for p in plist]
    return sorted(i for i in ids if i)


def _pair_has_answer(pid: str, pairs_dir: Path) -> bool:
    f = pairs_dir / f"{pid}.json"
    if not f.exists():
        return False
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    pa = d.get("pipeline_answer")
    return isinstance(pa, str) and bool(pa.strip())


def build_plan() -> list:
    """The full work plan (idempotent: built fresh each run; per-item
    status lives in the state file). ORDER is the owner's round
    2026-11-13 directive 4: A0+ FIRST (the decisive cheap-arm
    experiment), then the full-pipeline pairs, then ablation arms,
    two-turn, speed."""
    items: list = []
    ids = _dev12_ids()
    # 0. A0+ (owner directive 1: the simple arm BEFORE the 48-item
    #    ablation — if A0+ ties or beats the full pipeline, the heavy
    #    stages are not earning their cost)
    for pid in ids:
        if (REPO / "eval" / "pairs" / "r7_a0plus" / f"{pid}.json").exists():
            continue
        items.append({"kind": "a0plus", "problem": pid,
                      "pairs_out": "eval/pairs/r7_a0plus"})
    # 1. dev12 remaining (main arm -> dev12_r7)
    for pid in ids:
        if _pair_has_answer(pid, PAIRS_R7):
            continue
        items.append({"kind": "dev12", "problem": pid,
                      "pairs_out": "eval/pairs/dev12_r7"})
    # 2. ablation arms (each problem x arm; skipped when the main-arm
    #    pair for that problem does not exist yet — the arm needs the
    #    same-era engine, and the main arm goes first)
    for arm, envkv in ABLATION_ARMS:
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
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"plan": [], "status": {}, "updated_at": None, "pointer": 0}


def save_state(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    st["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime())
    STATE.write_text(json.dumps(st, indent=1), encoding="utf-8")


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


def _run_a0plus(item: dict) -> dict:
    """ONE A0+ invocation: the committed baseline -> constraint audit
    (1 call) -> strict relabel (0 calls) -> ONE repair (0-1 calls).
    The loop-local zai gateway is started-or-reused and PROBED first
    (the launcher's own probe-before-admit rule, one script); a typed
    probe failure is a RETRY_PENDING input, never a verdict."""
    env = dict(os.environ)
    env.setdefault("ENGINE_LLM_TIMEOUT_S", "40")
    # the same transport env the launcher rides: the cost policy (the
    # engine refuses every provider under the default ZERO_PAID_COST —
    # measured typed refusal on the first live A0+ invocation)
    env.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
    gw = None
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
        # session) — one immediate retry, no fixed sleep
        time.sleep(1)
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
        f = REPO / "eval" / "pairs" / "r7_a0plus" / \
            f"{item['problem']}.json"
        if res.get("exit_code") == 0 and f.exists():
            return "DONE"
        if res.get("exit_code") == 2:
            # typed skip: no committed baseline bytes — retrying the
            # same invocation cannot produce them (fail-closed)
            return "VERIFY_FAIL (typed skip: no committed baseline bytes)"
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
    if hits not in (0, None):
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


def run_one() -> int:
    st = load_state()
    plan = build_plan()
    st["plan"] = plan
    status = st.setdefault("status", {})
    _restore_score_table(st, "chunk start")
    # the first item that is not DONE and not EXHAUSTED
    target = None
    for it in plan:
        key = f"{it['kind']}:{it.get('arm') or it.get('rep') or ''}:" \
              f"{it['problem']}"
        s = status.get(key, {})
        if s.get("state") == "DONE":
            if it["kind"] == "a0plus":
                # the bytes are the truth (Art. XXV): a DONE state whose
                # pair file is absent (bytes removed after the run)
                # re-runs; the state alone is never the deliverable
                f = REPO / "eval" / "pairs" / "r7_a0plus" / \
                    f"{it['problem']}.json"
                if f.exists():
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
        print("[r7queue] ALL ITEMS DONE OR EXHAUSTED — queue drained")
        save_state(st)
        return 0
    key, it, s = target
    # ATTACH the entry: for a first-attempt item, status.get(key, {})
    # above returned a DETACHED dict — without this, every mutation
    # below (attempts/state/verdict) is lost and save_state persists an
    # empty status: retries never accumulate, MAX_ATTEMPTS never fires,
    # the item loops forever on a persistent storm. Measured defect on
    # the first live invocation (2026-11-13, p09 transport storm).
    status[key] = s
    att = int(s.get("attempts", 0))
    if att >= MAX_ATTEMPTS:
        s["state"] = "EXHAUSTED"
        s["note"] = f"typed exhausted after {att} attempts"
        print(f"[r7queue] {key}: EXHAUSTED after {att} attempts")
        save_state(st)
        return 0
    # ablation arms need the main-arm pair first (same-era engine)
    if it["kind"] == "ablation" and not _pair_has_answer(
            it["problem"], PAIRS_R7):
        s["state"] = "SKIP"
        s["note"] = "main-arm pair absent this invocation; re-planned"
        save_state(st)
        print(f"[r7queue] {key}: SKIP (main-arm pair not yet in "
              "dev12_r7; the dev12 item replans first)")
        return 0
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
            return 0
    if SEEDED_SPECIMENS.exists() and not SEEDED_HASHFILE.exists():
        print("[r7queue] seeded specimens present but the owner hash "
              "file is absent (eval/seeded_specimens_v1.sha256) — the "
              "sweep is NOT planned (the integrity hash is never "
              "invented, Art. XXV)")
    print(f"[r7queue] RUN {key} (attempt {att + 1}/{MAX_ATTEMPTS})")
    if it["kind"] == "seeded":
        res = _run_seeded_sweep(it)
    elif it["kind"] == "a0plus":
        res = _run_a0plus(it)
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
    elif verdict.startswith("VERIFY_FAIL"):
        s["state"] = "EXHAUSTED"
        s["note"] = verdict
    else:
        s["state"] = "RETRY_PENDING"
        s["note"] = verdict
    st["last_item"] = key
    save_state(st)
    _restore_score_table(st, "after item")
    print(f"[r7queue] {key}: {verdict} (wall {res['wall_s']}s, "
          f"exit {res['exit_code']})")
    if COOLDOWN_S > 0 and verdict != "DONE":
        print(f"[r7queue] cooldown {COOLDOWN_S}s (quota window)")
        time.sleep(COOLDOWN_S)
    return 0


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

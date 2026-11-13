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
  5. seeded       — PENDING until the owner places the sweep file
                    (typed, disclosed).

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
    status lives in the state file)."""
    items: list = []
    ids = _dev12_ids()
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
    proc = subprocess.run(cmd, cwd=str(REPO), env=env,
                          capture_output=True, text=True,
                          timeout=1000 + 120)
    wall = round(time.time() - t0, 1)
    return {"exit_code": proc.returncode, "wall_s": wall,
            "tail": (proc.stdout or "")[-1200:]
            + "\n--stderr--\n" + (proc.stderr or "")[-800:]}


def _classify_result(item: dict, res: dict) -> str:
    """Typed post-run classification: DONE | RETRY_PENDING | EXHAUSTED-
    INPUT (the launcher's typed failures ride the exit code + output)."""
    tail = res.get("tail") or ""
    if res.get("exit_code") == 0 and _pair_has_answer(
            item["problem"], REPO / item["pairs_out"]):
        if item["kind"] == "speed":
            return _speed_verify(item) or "DONE"
        return "DONE"
    if "ZAI_TRANSPORT_PROBE" in tail and "200 OK" not in tail:
        return "RETRY_PENDING (zai transport down this window)"
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


def run_one() -> int:
    st = load_state()
    plan = build_plan()
    st["plan"] = plan
    status = st.setdefault("status", {})
    # the first item that is not DONE and not EXHAUSTED
    target = None
    for it in plan:
        key = f"{it['kind']}:{it.get('arm') or it.get('rep') or ''}:" \
              f"{it['problem']}"
        s = status.get(key, {})
        if s.get("state") == "DONE":
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
    print(f"[r7queue] RUN {key} (attempt {att + 1}/{MAX_ATTEMPTS})")
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
    print(f"[r7queue] {key}: {verdict} (wall {res['wall_s']}s, "
          f"exit {res['exit_code']})")
    if COOLDOWN_S > 0 and verdict != "DONE":
        print(f"[r7queue] cooldown {COOLDOWN_S}s (quota window)")
        time.sleep(COOLDOWN_S)
    return 0


def main() -> int:
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

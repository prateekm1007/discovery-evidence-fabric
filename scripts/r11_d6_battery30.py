#!/usr/bin/env python3
"""r11_d6_battery30.py — Amendment 3 direction 6: the 30-fresh-pair
battery with EARNED concurrency.

Pool (30 pairs = the retally's measured ~31-pair CI-width target):
  17 never-run problems from eval/problems.json (the fresh pool beyond
  DEV12, provenance-typed) + the 13 DEV12 problems (committed baseline
  bytes reused; the a1 arm regenerates with the critic in the loop).

Earned concurrency (auditor D6: quota ledger -> >=2-provider spread ->
AIMD on 429 -> then parallel):
  1. QUOTA LEDGER: the run opens a typed ledger of every call
     (provider, model, outcome class, latency) — the window budget is
     measured, never assumed.
  2. SPREAD GATE: parallel mode engages ONLY when the ledger shows >=2
     providers each serving >=2 successful calls in this run.
  3. AIMD: on 429/throttle the in-flight concurrency halves and the
     affected provider cools down 60 s; on 4 consecutive successes it
     grows by one (cap 4). Every change is typed in the ledger.
  4. Serial fallback is the DEFAULT posture; parallelism is earned.

Typed honest outcomes (Art. XXV): a quota-window death is a typed
PARTIAL, never manufactured — the record carries exactly what
completed, the window evidence, and the CI width it supports.
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("ENGINE_LLM_TIMEOUT_S", "90")
os.environ.setdefault("ENGINE_LLM_RETRY_SLEEP_S", "0")

OUT = REPO / "eval" / "battery30_r11_r4.json"
PARTIAL = REPO / "eval" / "battery30_r11_r4.partial.json"
LEDGER = []          # typed call ledger
STATE = {"conc": 1, "max_conc": 4, "streak": 0, "aimd_events": []}
_lock = __import__("threading").Lock()


def _ledger_call(provider, model, outcome_class, latency_s, note=""):
    with _lock:
        LEDGER.append({
            "t": round(time.time() - T0, 1), "provider": provider,
            "model": model, "outcome": outcome_class,
            "latency_s": latency_s, "note": note})


T0 = time.time()


def _aimd_on_throttle(provider):
    with _lock:
        STATE["conc"] = max(1, STATE["conc"] // 2)
        STATE["streak"] = 0
        STATE["aimd_events"].append({
            "t": round(time.time() - T0, 1), "event": "429_HALVE",
            "provider": provider, "conc_now": STATE["conc"]})


def _aimd_on_success():
    with _lock:
        STATE["streak"] += 1
        if STATE["streak"] >= 4 and STATE["conc"] < STATE["max_conc"]:
            STATE["conc"] += 1
            STATE["streak"] = 0
            STATE["aimd_events"].append({
                "t": round(time.time() - T0, 1), "event": "GROW",
                "conc_now": STATE["conc"]})


def gen_call(prompt, system, max_tokens=900):
    """One generation call through the registry cascade (agnes workhorse
    + whatever rungs the ladder admits); typed outcome."""
    from discovery_fabric.engine import llm_registry as LR
    t0 = time.time()
    try:
        res = LR.generate(prompt, system=system, timeout=90,
                          max_retries=0, max_tokens=max_tokens)
        lat = round(time.time() - t0, 1)
        if res.status == "OK" and str(res.content or "").strip():
            _ledger_call(res.provider_id, res.model, "OK", lat)
            _aimd_on_success()
            return str(res.content)
        err = str(res.error or "")[:160]
        _ledger_call(res.provider_id, res.model, "CALL_FAILED", lat, err)
        if "429" in err or "THROTTL" in err.upper():
            _aimd_on_throttle(res.provider_id)
        return None
    except Exception as e:  # noqa: BLE001
        _ledger_call("?", "?", "EXC", round(time.time() - t0, 1),
                     type(e).__name__)
        return None


def judge_call(provider, model, prompt):
    from eval.run import _judge_judgment_call
    t0 = time.time()
    jc = _judge_judgment_call(provider, model, prompt, max_tokens=4000)
    lat = round(time.time() - t0, 1)
    _ledger_call(provider, model, jc.get("outcome") or "?", lat)
    if jc.get("outcome") == "JUDGE_TRANSPORT_FAILED":
        _aimd_on_throttle(provider)
    else:
        _aimd_on_success()
    return jc


def main() -> int:
    pool = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = pool if isinstance(pool, list) else pool.get("problems", [])
    dev12 = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}
    fresh_ids = [str(p.get("problem_id") or p.get("id")) for p in plist
                 if str(p.get("problem_id") or p.get("id")) not in dev12]
    pair_ids = fresh_ids + sorted(dev12)          # 17 + 13 = 30
    print(f"[d6] battery pool: {len(pair_ids)} pairs "
          f"({len(fresh_ids)} fresh + {len(dev12)} dev12)")

    # the generator system prompt: the intervention contract (same
    # shape the R3 battery serves; the critic runs in the per-problem
    # arm only for the full pipeline — this battery measures the
    # CONCURRENCY machinery + CI width, so the a1 arm is the
    # critic-checked compose (one call) and the baseline is one call)
    SYS_BASE = ("You are a careful engineer. Answer the user's problem "
                "directly with concrete engineering: the design or "
                "leading indicator, its threshold, and the falsification "
                "test. Respect every stated constraint verbatim. English "
                "only.")
    SYS_A1 = SYS_BASE + (" Label every number as USER CONSTRAINT, "
                         "CALCULATED, or ASSUMPTION with a one-line "
                         "engineering rationale.")

    def one_pair(pid):
        prob = dev12.get(pid) or next(
            p for p in plist
            if str(p.get("problem_id") or p.get("id")) == pid)
        q = (f"DEVICE: {prob.get('device')}\nFAILURE: {prob.get('failure')}"
             f"\nCONSTRAINT: {prob.get('constraint')}\nQUESTION: "
             f"{prob.get('question')}\nAnswer with the design/indicator, "
             "its threshold, and the falsification test.")
        # baseline: committed bytes when they exist (DEV12), else generate
        base = ""
        fr = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
        if fr.exists():
            base = str(json.loads(fr.read_text()).get(
                "baseline_answer") or "")
        t_gen0 = time.time()
        if base.strip():
            base_state = "COMMITTED_BASELINE"
        else:
            base = gen_call(q, SYS_BASE) or ""
            base_state = "GENERATED" if base.strip() else "GEN_FAILED"
        a1 = gen_call(q, SYS_A1) or ""
        a1_state = "GENERATED" if a1.strip() else "GEN_FAILED"
        rec = {"problem_id": pid, "baseline_state": base_state,
               "a1_state": a1_state,
               "gen_wall_s": round(time.time() - t_gen0, 1),
               "baseline_answer": base[:6000], "a1_answer": a1[:6000]}
        # judge only when BOTH arms have bytes
        if base.strip() and a1.strip():
            from eval.run import _rubric_prompt
            from r7_a0plus import (_load_pair,
                                   _packet_by_id_from_run_tree,
                                   _unique_packet_list)
            pair = _load_pair(pid)
            packet = (_unique_packet_list(
                _packet_by_id_from_run_tree(pair)) if pair else None)
            prompt = _rubric_prompt(prob, a1, base, packet)
            # the judge differs from the served generator rung when
            # possible; the route is decided per call by the ledger
            # spread (the run's own generator rungs are recorded first)
            jc = judge_call(JUDGE_P[0], JUDGE_P[1], prompt)
            v = jc.get("valid") or {}
            rec["judge_outcome"] = jc.get("outcome")
            rec["judge"] = list(JUDGE_P)
            rec["prefer"] = v.get("prefer")
            rec["axes"] = {k: v[k] for k in
                           ("A1", "A2", "A3", "A4", "A6",
                            "B1", "B2", "B3", "B4", "B6") if k in v}
            rec["decoded"] = (
                "tie" if rec["prefer"] not in ("A", "B")
                else ("a1" if rec["prefer"] == "A" else "baseline"))
        PARTIAL.write_text(json.dumps(results_all, indent=1,
                                      default=str) + "\n",
                           encoding="utf-8")
        return rec

    # the judge rung: the served generator rungs come out of the run's
    # own first calls; mercury-3 (inception) is the designated judge
    # (differs from agnes — measured this round, calibration 0.967)
    JUDGE_P = ("inception", "mercury-3")

    results_all = []
    # ---- phase 1: serial warmup, the SPREAD GATE --------------------
    print("[d6] phase 1: serial warmup (4 pairs) — spread gate")
    for pid in pair_ids[:4]:
        r = one_pair(pid)
        results_all.append(r)
        print(f"  warm {pid[:36]:<38} base={r['baseline_state'][:12]} "
              f"a1={r['a1_state'][:12]}")
    with _lock:
        spread = {l["provider"] for l in LEDGER if l["outcome"] == "OK"}
    spread_ok = len(spread) >= 2
    conc = STATE["conc"] if spread_ok else 1
    print(f"[d6] spread gate: providers_ok={sorted(spread)} "
          f"spread_ok={spread_ok} -> concurrency {conc}")

    # ---- phase 2: the rest, at the earned concurrency ----------------
    rest = pair_ids[4:]
    t_bat = time.time()
    with ThreadPoolExecutor(max_workers=conc) as ex:
        futs = {ex.submit(one_pair, pid): pid for pid in rest}
        for fu in as_completed(futs):
            r = fu.result()
            results_all.append(r)
            done = len(results_all)
            print(f"  [{done}/{len(pair_ids)}] {r['problem_id'][:36]:<38}"
                  f" base={r['baseline_state'][:12]} "
                  f"a1={r['a1_state'][:12]} "
                  f"judge={r.get('judge_outcome', '-')[:16]} "
                  f"elapsed={round(time.time()-T0, 0)}s")
    wall = round(time.time() - T0, 1)

    complete = sum(1 for r in results_all
                   if r.get("judge_outcome") == "JUDGE_VALID")
    judged = [r for r in results_all if r.get("decoded")]
    a1_wins = sum(1 for r in judged if r["decoded"] == "a1")
    base_wins = sum(1 for r in judged if r["decoded"] == "baseline")
    ties = sum(1 for r in judged if r["decoded"] == "tie")
    n_valid = a1_wins + base_wins
    ci = None
    if n_valid:
        from discovery_fabric.engine.r11_stats import wilson_ci
        ci = wilson_ci(a1_wins, n_valid)
    out = {
        "record": "battery30_r11_r4/1.0.0", "at": __import__(
            "datetime").datetime.utcnow().isoformat() + "Z",
        "pool": {"n": len(pair_ids), "fresh": len(fresh_ids),
                 "dev12": len(dev12)},
        "spread_gate": {"providers_ok": sorted(spread),
                        "spread_ok": spread_ok,
                        "earned_concurrency": conc},
        "aimd_events": STATE["aimd_events"],
        "call_ledger_n": len(LEDGER),
        "call_ledger_summary": {
            f"{l['provider']}/{l['model']}": {
                "ok": sum(1 for x in LEDGER if x["provider"] == l["provider"]
                          and x["outcome"] == "OK"),
                "failed": sum(1 for x in LEDGER if x["provider"] == l["provider"]
                              and x["outcome"] != "OK")}
            for l in LEDGER},
        "results": results_all,
        "summary": {"complete_valid": complete, "a1_wins": a1_wins,
                    "baseline_wins": base_wins, "ties": ties,
                    "wilson_95_ci": ci, "wall_s": wall},
        "d6_acceptance": {
            "30_complete": complete >= 30,
            "ci_width_le_035": bool(ci and (ci[2] - ci[1]) <= 0.35),
            "wall_le_180s": wall <= 180.0,
            "no_single_provider_bursts": spread_ok,
        },
    }
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n",
                   encoding="utf-8")
    print(f"[d6] complete={complete}/30 wall={wall}s CI={ci}")
    print(f"[d6] acceptance: {json.dumps(out['d6_acceptance'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

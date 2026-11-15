#!/usr/bin/env python3
"""r26_battery_v7.py — AM25 D1: the V7 CATALOG-COMPOSITION arm, measured
under Art. 29 claim-before-work (claim c-0020, EXECUTOR builder-r26s1).

WORK ITEM: the NEW feasibility lever (AM25 direction 1, verbatim):
"Produce novel COMBINATIONS of procurable catalog components (novel
arrangement, no new development, and no audit apparatus that itself
reads as burden), so implementation burden is provably <= standard
practice." Lever kind = NOVELTY-RELOCATION (distinct from the three
RETIRED generation-side levers: BOK selection r21, V5 repair r22,
V6/V6.1 contract-bind r23/r24 — those bound the SAME novelty target
harder; V7 relocates the novelty target into the ARRANGEMENT of
generic-class procurable components, so the fictional-catalog failure
mode measured at bench-p05/p10 (fgap 4) is excluded BY CONSTRUCTION).

BYTE MAP (pre-declared, ALL-FRESH — the r23/r24 rides floor
14/30 ~= 0.467 made the <=0.25 gate clause structurally unreachable;
the auditor typed "the clause needs an all-fresh battery once a bound
generator proves out"):
  FRESH_V7_INT (18): every intervention problem, one draft under
    SYS_A1_INT_V7 (V4 + V6 bind + constraint awareness + the V7
    catalog-composition bind), typed machine repairs (budget 2), NO
    selection (K_GEN=1).
  FRESH_V5_PRED (12): every predictor problem, one draft under
    SYS_A1F_V5 (the current machine predictor contract, r24,
    holdout-v3-proven at 3.0/4) — its first battery measurement; the
    predictor incumbent reference is the r11 judged rides rows
    (fgap sum 14).
  PILOT_8 (pre-declared subset of FRESH_V7_INT): the r24 intervention
    rows with fgap >= 2 AND novelty delta >= 2 — bench-p03, bench-p04,
    bench-p05, bench-p06, bench-p08, bench-p09, bench-p10, bench-p12
    (V6.1 pilot-8 fgap mean 3.0; incumbent r20 pilot-8 fgap 2.25,
    nd 3.25). The pilot is a typed DIRECTION PROBE (MECHANICS_PILOT,
    the r19 precedent — NOT an Art. 20 round): pre-registered gate —
    proceed to the full battery if V7 pilot-8 fgap <= 2.5
    (improvement >= 0.5 vs V6.1); typed WEAK-proceed if 2.5 < fgap <
    3.0; NO_DIRECTION-stop if fgap >= 3.0 (the lever is typed at the
    pilot, the full battery is NOT run, the auditor re-decides — no
    self-certified retirement). Pilot rows ride their judged rows
    byte-identical into the full battery (AM19 sec.2 determinism,
    disclosed).

ACCEPTANCE (AM25 D1 verbatim): feasibility |gap| <= 0.25 AND novelty
delta >= 0.5 on >= 30 pairs, and the ablation beats the incumbent (CI
excludes it) — incumbent = SYS_A1_INT_V4 single-draw (the r20 bytes),
intervention fgap 1.5, nd 2.333. Art. 20: round 1 of 2 for this lever
kind. Judge crowllm/qwen-3.8-max:free K=3 (canonical, unchanged);
metric core eval/battery_metrics.py unchanged (Art. 16/19).
VERIFIER INVITED (Art. 13, zero-LLM recompute from committed bytes).
"""
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
import os  # noqa: E402
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")
os.environ.setdefault(
    "ZAI_GATEWAY_LOG",
    str(REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"))

from r26_a1w_v7_contract import (  # noqa: E402
    contract_for_v7, MACHINE_REPAIR_DIRECTIVE)
from r26_catalog_scan import scan_catalog  # noqa: E402
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r19_a1w_v4_contract import predictor_violations  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r26_v7_catalog"
R11 = REPO / "eval" / "battery_a1w_r11.json"
R20_REC = REPO / "eval" / "battery_a1w2_full_r20.json"
R24_REC = REPO / "eval" / "battery_feas_bind_v61_r24.json"
PILOT_OUT = REPO / "eval" / "battery_v7_catalog_r26_pilot.json"
FULL_OUT = REPO / "eval" / "battery_v7_catalog_r26.json"
FULL_PARTIAL = REPO / "eval" / "battery_v7_catalog_r26.partial.json"
JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
K = 3
REPAIR_BUDGET = 2
LADDER_BACKOFF_S = (20.0, 60.0)
SWEEP_PASSES = 2
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

R20ROWS = {r["problem_id"]: r for r in
           json.loads(R20_REC.read_text(encoding="utf-8"))["results"]}
R24ROWS = {r["problem_id"]: r for r in
           json.loads(R24_REC.read_text(encoding="utf-8"))["results"]}

FRESH_V7_INT = sorted(p for p, r in R20ROWS.items()
                      if str(r.get("question_type", "")).startswith(
                          "intervention"))
FRESH_V5_PRED = sorted(p for p, r in R20ROWS.items()
                       if str(r.get("question_type", "")).startswith(
                           "predictor"))
ALL = FRESH_V7_INT + FRESH_V5_PRED
assert len(ALL) == 30 and len(set(ALL)) == 30, "r26 byte map malformed"
assert len(FRESH_V7_INT) == 18 and len(FRESH_V5_PRED) == 12

# pre-declared pilot: r24 intervention rows fgap>=2 AND nd>=2
PILOT_8 = sorted(p for p in FRESH_V7_INT
                 if (R24ROWS[p].get("feasibility_abs_gap") or 0) >= 2
                 and (R24ROWS[p].get("novelty_delta") or 0) >= 2)
V61_PILOT8_FGAP = round(sum(R24ROWS[p]["feasibility_abs_gap"]
                            for p in PILOT_8) / len(PILOT_8), 3)
R20_PILOT8_FGAP = round(sum(R20ROWS[p]["feasibility_abs_gap"]
                            for p in PILOT_8) / len(PILOT_8), 3)
R20_PILOT8_ND = round(sum(R20ROWS[p]["novelty_delta"]
                          for p in PILOT_8) / len(PILOT_8), 3)
GATE_PROCEED_BELOW = round(V61_PILOT8_FGAP - 0.5, 3)   # 2.5
assert len(PILOT_8) == 8, f"pilot subset drifted: {PILOT_8}"

R11ROWS = {r["problem_id"]: r for r in
           json.loads(R11.read_text(encoding="utf-8"))["results"]}
R11_PRED_FGAP_SUM = sum(R11ROWS[p].get("feasibility_abs_gap") or 0
                        for p in FRESH_V5_PRED)
R20_IV_FGAP = round(sum(r["feasibility_abs_gap"] for r in R20ROWS.values()
                        if str(r.get("question_type", "")).startswith(
                            "intervention")) / 18, 3)
R20_IV_ND = round(sum(r["novelty_delta"] for r in R20ROWS.values()
                      if str(r.get("question_type", "")).startswith(
                          "intervention")) / 18, 3)


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _now():
    return datetime.datetime.now(datetime.UTC).isoformat().replace(
        "+00:00", "Z")


def baseline_for(pid):
    d12 = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
    if d12.exists():
        base = str(json.loads(d12.read_text()).get("baseline_answer") or "")
        if base.strip():
            return base, "CURATED_COMMITTED_dev12"
    cur = REPO / "eval" / "baselines_curated" / f"{pid}.json"
    if cur.exists():
        base = str(json.loads(cur.read_text()).get("baseline_answer") or "")
        if base.strip():
            return base, "CURATED_STANDARD_REFERENCE_builder"
    return "", ""


def _retry_call(f, *args, tries=5, backoff=(10.0, 30.0, 60.0, 120.0)):
    last = None
    for t in range(tries):
        try:
            return f(*args)
        except Exception as e:  # noqa: BLE001 — typed infra retry (Art. 15)
            last = e
            if t < tries - 1:
                time.sleep(backoff[min(t, len(backoff) - 1)])
                print(f"    [retry {t+1}] {type(e).__name__}: "
                      f"{str(e)[:90]}", flush=True)
    raise last


def machine_generate(prob, gw_key):
    """The R26 type-aware machine: one generation pass under
    contract_for_v7(qt) + critic + question-type gate + typed scans
    (base + constraint-fit + CATALOG v2 on interventions + predictor
    violations on the predictor side) + the machine's own NEUTRAL
    repair directives (REPAIR_BUDGET=2). NO outcome-based feedback, NO
    selection. The catalog scan is the V7/D2 lever's deterministic leg
    (disclosed as part of the machine under test)."""
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    contract = contract_for_v7(qt)
    attempts = []
    final, lat = _retry_call(_gen, q, contract, gw_key)
    tries = 1
    final_meta = {}
    rep = 0
    while True:
        cr = _retry_call(critic, final, prob)
        tg = gate_question_type(final, prob)
        vio = {}
        vio.update(base_scan(final))
        vio.update(scan_constraint_fit(prob, final))
        if not qt.startswith("predictor"):
            vio.update(scan_catalog(prob, final))
        else:
            pv = predictor_violations(final)
            if pv:
                vio.update({"PREDICTOR_VIOLATION": list(pv)})
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        problems = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        problems += findings
        att = {"stage": ("draft" if rep == 0 else f"repair_{rep}"),
               "chars": len(final), "latency_s": round(lat, 1),
               "transport_tries": tries,
               "critic_verdict": cr["verdict"], "type_gate": tg,
               "scan": {k: list(v) for k, v in vio.items()},
               "sha256_16": _sha(final)}
        if rep:
            att["findings_disclosed"] = [p for p in problems if p]
        attempts.append(att)
        if not [p for p in problems if p]:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "residual_findings": {}}
            return final, attempts, final_meta
        if rep == REPAIR_BUDGET:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()}}
            return final, attempts, final_meta
        directive = MACHINE_REPAIR_DIRECTIVE.format(
            findings="; ".join(p for p in problems if p))
        final, lat = _retry_call(
            _gen, q + "\n\n" + directive, contract, gw_key)
        tries += 1
        rep += 1


def judge_slot(pid, k, prompt):
    attempts = []
    outcome = None
    jc = None
    for try_n in range(1 + len(LADDER_BACKOFF_S)):
        if try_n:
            time.sleep(LADDER_BACKOFF_S[try_n - 1])
        econ.reset_governor(f"r26v7:{pid}:{k}"
                            + (f":retry{try_n}" if try_n else ""))
        jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                  max_tokens=4000)
        outcome = jc.get("outcome")
        attempts.append({"n": try_n + 1, "outcome": outcome,
                         "latency_s": (jc.get("latencies") or [None])[-1]})
        if outcome == "JUDGE_VALID":
            break
    return jc, outcome, attempts


def valid_draws(row):
    return sum(1 for d in row["draws"] if d["outcome"] == "JUDGE_VALID")


def _row_from_record(pid, rec, prob):
    """Judge one pair (K draws) and build the battery row."""
    a1 = str(rec["a1_answer"])
    base, b_src = baseline_for(pid)
    assert base.strip(), f"no baseline for {pid}"
    prompt = _rubric_prompt(prob, a1[:7000], base[:7000], None) + AXIS_SUFFIX
    draws = []
    for k in range(K):
        jc, outcome, atts = judge_slot(pid, k, prompt)
        draws.append({"k": k, "outcome": outcome,
                      "axes": parse_axes(jc),
                      "prefer": (jc.get("valid") or {}).get("prefer"),
                      "transport_attempts": atts})
        time.sleep(PACE_S)
    dec = row_metrics(draws)
    med = dec["median_axes"]
    arm = ("SYS_A1_INT_V7_CATALOG_COMPOSITION"
           if str(prob.get("question_type", "")).startswith("intervention")
           else "SYS_A1F_V5_PRIMARY_INDICATOR")
    row = {"problem_id": pid, "a1_arm": arm,
           "question_type": prob.get("question_type"),
           "question_type_gate": rec["meta"]["attempts"][0]["type_gate"],
           "baseline_source": b_src,
           "byte_provenance": {
               "byte_source": f"eval/pairs/r26_v7_catalog/{pid}.json",
               "a1_answer_sha256_16": _sha(a1),
               "generation": "single draft under contract_for_v7 "
                             "(V7 catalog-composition bind on "
                             "interventions / SYS_A1F_V5 on predictors) "
                             "+ neutral typed repairs; no selection"},
           "judge": list(JUDGE), "draws": draws,
           "majority_prefer": dec["majority_prefer"],
           "median_axes": med}
    if med:
        row["novelty_delta"] = med["N_A"] - med["N_B"]
        row["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
        row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
        row["testability_delta"] = med["T_A"] - med["T_B"]
        row["constraint_delta"] = med["C_A"] - med["C_B"]
    return row


def _generate_one(pid, prob, gw_key):
    dst = OUT_DIR / f"{pid}.json"
    if dst.exists():
        print(f"  [gen] {pid[:36]:<38} exists", flush=True)
        return
    t0 = time.time()
    ans, meta = machine_generate(prob, gw_key)
    dst.write_text(
        json.dumps({"problem_id": pid,
                    "a1_source": ("SYS_A1_INT_V7/r26_a1w_v7_contract"
                                  if str(prob.get("question_type", ""))
                                  .startswith("intervention")
                                  else "SYS_A1F_V5/r24_a1w_v61_contract"),
                    "question_type": prob.get("question_type"),
                    "a1_answer": ans, "meta": meta,
                    "generated_at": _now()},
                   indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"  [gen] {pid[:36]:<38} repairs={meta['repairs']} "
          f"residual={list(meta['residual_findings']) or 'CLEAN'} "
          f"({time.time()-t0:.0f}s)", flush=True)


def _prob_map():
    probs = {}
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = (plist if isinstance(plist, list) else plist.get("problems", []))
    for p in plist:
        probs[str(p.get("problem_id") or p.get("id"))] = p
    for p in json.loads((REPO / "eval" / "problems_dev12.json")
                        .read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)
    return probs


def _judge_set(probs, pids, results, prior):
    """Generate (resumable) + judge (resumable) the given pair set."""
    for pid in pids:
        if pid in prior:
            results.append(prior[pid])
            print(f"  [{pid[:32]:<34}] resumed", flush=True)
            continue
        prob = probs[pid]
        _generate_one(pid, prob, gw_key)
        rec = json.loads((OUT_DIR / f"{pid}.json").read_text(
            encoding="utf-8"))
        row = _row_from_record(pid, rec, prob)
        results.append(row)
        FULL_PARTIAL.write_text(
            json.dumps(results, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"  [{pid[:32]:<34}] judged nd="
              f"{row.get('novelty_delta')} fgap="
              f"{row.get('feasibility_abs_gap')} "
              f"prefer={row.get('majority_prefer')}", flush=True)


def main() -> int:
    global gw_key
    probs = _prob_map()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gw, gw_key = start_gateway()
    print(f"[gateway] up (pid {gw.pid}) | judge {JUDGE[0]}/{JUDGE[1]} "
          f"K={K} pace {PACE_S}s", flush=True)
    try:
        # ---------------- phase 0: the PILOT (direction probe) ----------
        pilot_done = PILOT_OUT.exists()
        if not pilot_done:
            pilot_rows = []
            for pid in PILOT_8:
                prob = probs[pid]
                _generate_one(pid, prob, gw_key)
                rec = json.loads((OUT_DIR / f"{pid}.json").read_text(
                    encoding="utf-8"))
                row = _row_from_record(pid, rec, prob)
                pilot_rows.append(row)
                time.sleep(PACE_S)
                print(f"  [pilot {pid[:30]:<32}] nd="
                      f"{row.get('novelty_delta')} fgap="
                      f"{row.get('feasibility_abs_gap')}", flush=True)
            valid = [r for r in pilot_rows if r.get("median_axes")]
            if len(valid) < 6:
                PILOT_OUT.write_text(json.dumps({
                    "record": "BATTERY_V7_CATALOG_PILOT_R26/1.0.0",
                    "at": _now(),
                    "status": "TRANSPORT_SHORTFALL",
                    "n_valid": len(valid), "rows": pilot_rows,
                }, indent=1, default=str) + "\n", encoding="utf-8")
                print("[pilot] TRANSPORT_SHORTFALL — fail closed, "
                      "rerun to resume", flush=True)
                return 2
            pg = round(sum(r["feasibility_abs_gap"] for r in valid)
                       / len(valid), 3)
            pnd = round(sum(r["novelty_delta"] for r in valid)
                        / len(valid), 3)
            if pg >= V61_PILOT8_FGAP:
                gate = "NO_DIRECTION_STOP"
            elif pg <= GATE_PROCEED_BELOW:
                gate = "PROCEED"
            else:
                gate = "WEAK_PROCEED"
            PILOT_OUT.write_text(json.dumps({
                "record": "BATTERY_V7_CATALOG_PILOT_R26/1.0.0",
                "at": _now(), "status": "SCORED", "gate": gate,
                "pre_registered": {
                    "subset_criterion": "r24 intervention rows fgap>=2 "
                                        "AND nd>=2",
                    "subset": PILOT_8,
                    "v61_pilot8_fgap_mean": V61_PILOT8_FGAP,
                    "incumbent_r20_pilot8_fgap": R20_PILOT8_FGAP,
                    "incumbent_r20_pilot8_nd": R20_PILOT8_ND,
                    "gate": "proceed if V7 pilot-8 fgap <= 2.5 "
                            "(improvement >= 0.5 vs V6.1 3.0); "
                            "WEAK-proceed if 2.5 < fgap < 3.0; "
                            "NO_DIRECTION-stop if fgap >= 3.0"},
                "v7_pilot8_fgap_mean": pg, "v7_pilot8_nd_mean": pnd,
                "rows": pilot_rows,
            }, indent=1, default=str) + "\n", encoding="utf-8")
            print(f"[pilot] V7 pilot-8 fgap {pg} nd {pnd} | "
                  f"V6.1 {V61_PILOT8_FGAP} | incumbent r20 "
                  f"{R20_PILOT8_FGAP} | GATE: {gate}", flush=True)
            if gate == "NO_DIRECTION_STOP":
                print("[pilot] NO_DIRECTION_STOP — the full battery is "
                      "NOT run (pre-registered); the lever is typed at "
                      "the pilot for the auditor's re-decision",
                      flush=True)
                return 3
        else:
            pr = json.loads(PILOT_OUT.read_text(encoding="utf-8"))
            print(f"[pilot] exists: gate={pr.get('gate')} "
                  f"fgap={pr.get('v7_pilot8_fgap_mean')}", flush=True)
            if pr.get("gate") == "NO_DIRECTION_STOP":
                print("[pilot] gate NO_DIRECTION_STOP stands — fail "
                      "closed", flush=True)
                return 3

        # ---------------- phase 1: the FULL 30-pair battery -------------
        prior = {}
        if FULL_PARTIAL.exists():
            for r in json.loads(FULL_PARTIAL.read_text(encoding="utf-8")):
                prior[r["problem_id"]] = r
        results = []
        done = {r["problem_id"] for r in prior.values()}
        # pilot rows ride their judged rows byte-identical (AM19 sec.2)
        pilot_rows = {r["problem_id"]: r for r in
                      json.loads(PILOT_OUT.read_text(
                          encoding="utf-8"))["rows"]}
        for pid in ALL:
            if pid in done:
                results.append(prior[pid])
                print(f"  [{pid[:32]:<34}] resumed", flush=True)
            elif pid in PILOT_8 and pid in pilot_rows \
                    and pilot_rows[pid].get("median_axes"):
                row = dict(pilot_rows[pid])
                row["ride"] = {
                    "row_source": "battery_v7_catalog_r26_pilot.json",
                    "byte_source": f"eval/pairs/r26_v7_catalog/{pid}.json",
                    "a1_answer_sha256_16": _sha(str(json.loads(
                        (OUT_DIR / f"{pid}.json").read_text(
                            encoding="utf-8"))["a1_answer"])),
                    "rule": "byte-identical pair rides its committed "
                            "judged pilot row (AM19 sec.2 determinism; "
                            "the pilot is the pre-declared subset)"}
                results.append(row)
                FULL_PARTIAL.write_text(
                    json.dumps(results, indent=1, ensure_ascii=False)
                    + "\n", encoding="utf-8")
                print(f"  [{pid[:32]:<34}] pilot ride", flush=True)
            else:
                _judge_set(probs, [pid], results, {})
        assert len(results) == 30, f"pool incomplete: {len(results)}"

        # ---------------- phase 2: transport sweep -----------------------
        for sweep in range(SWEEP_PASSES):
            dead = [r for r in results
                    if r.get("draws") and valid_draws(r) < 2]
            if not dead:
                break
            print(f"  [sweep {sweep+1}] re-drawing {len(dead)} dead rows",
                  flush=True)
            for row in dead:
                pid = row["problem_id"]
                prob = probs[pid]
                rec = json.loads((OUT_DIR / f"{pid}.json").read_text(
                    encoding="utf-8"))
                base, _ = baseline_for(pid)
                prompt = _rubric_prompt(prob,
                                        str(rec["a1_answer"])[:7000],
                                        base[:7000], None) + AXIS_SUFFIX
                for k in range(K):
                    if any(d["outcome"] == "JUDGE_VALID"
                           for d in row["draws"] if d["k"] == k):
                        continue
                    jc, outcome, atts = judge_slot(pid, k, prompt)
                    row["draws"].append({"k": f"sw{sweep+1}-{k}",
                                         "outcome": outcome,
                                         "axes": parse_axes(jc),
                                         "prefer": (jc.get("valid") or {})
                                         .get("prefer"),
                                         "transport_attempts": atts})
                    time.sleep(PACE_S)
                dec = row_metrics(row["draws"])
                med = dec["median_axes"]
                if med:
                    row["majority_prefer"] = dec["majority_prefer"]
                    row["median_axes"] = med
                    row["novelty_delta"] = med["N_A"] - med["N_B"]
                    row["feasibility_abs_gap"] = abs(
                        med["F_A"] - med["F_B"])
                    row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
                    row["testability_delta"] = med["T_A"] - med["T_B"]
                    row["constraint_delta"] = med["C_A"] - med["C_B"]
                FULL_PARTIAL.write_text(
                    json.dumps(results, indent=1, ensure_ascii=False)
                    + "\n", encoding="utf-8")

        # ---------------- phase 3: summaries + ablation ------------------
        iv = [r for r in results
              if str(r.get("question_type", "")).startswith("intervention")]
        pred = [r for r in results
                if str(r.get("question_type", "")).startswith("predictor")]
        tc = [r for r in results
              if (r.get("question_type_gate") or {}).get("verdict")
              == "MATCH"]
        s_all = summarize(results, "ALL 30 pairs (ALL-FRESH, no rides "
                                  "floor)")
        s_tc = summarize(tc, "type-MATCH pairs only (primary form)")
        s_iv = summarize(iv, "INTERVENTION rows (the changed arm)")
        s_pred = summarize(pred, "PREDICTOR rows (SYS_A1F_V5 first "
                                 "battery measurement)")
        iv_r20 = summarize(
            [r for r in R20ROWS.values()
             if str(r.get("question_type", "")).startswith("intervention")],
            "r20 incumbent single-draw intervention rows")
        ladder_stats = {"first_try_valid": 0, "recovered": 0,
                        "still_dead": 0, "total_attempts": 0}
        for r in results:
            for d in r.get("draws") or []:
                atts = d.get("transport_attempts") or []
                ladder_stats["total_attempts"] += len(atts)
                if d.get("outcome") == "JUDGE_VALID":
                    ladder_stats["first_try_valid"] += len(atts) == 1
                    ladder_stats["recovered"] += len(atts) > 1
                else:
                    ladder_stats["still_dead"] += 1
        gen_meta = {p: json.loads((OUT_DIR / f"{p}.json").read_text(
            encoding="utf-8"))["meta"] for p in ALL}
        repairs_total = sum(m["repairs"] for m in gen_meta.values())
        residual_pairs = sum(1 for m in gen_meta.values()
                             if m["residual_findings"])
        catalog_residual = sum(
            1 for p, m in gen_meta.items()
            if any(k.startswith(("ALLOWED", "APPARATUS", "NAMED"))
                   for k in m["residual_findings"]))
        # Art. 20 ablation (the changed arm = intervention rows)
        iv_fg = [r["feasibility_abs_gap"] for r in iv
                 if r.get("median_axes")]
        iv_lo, iv_hi = _ci(iv_fg)
        beats = iv_hi < R20_IV_FGAP
        pilot = json.loads(PILOT_OUT.read_text(encoding="utf-8"))
        record = {
            "record": "BATTERY_INT_V7_CATALOG_COMPOSITION_R26/1.0.0 — "
                      "the AM25 D1 novelty-relocation lever "
                      "(catalog-composition), round 1/2",
            "at": _now(),
            "claim": {"work_id": "r26-v7-catalog-battery",
                      "claim_id": "c-0020",
                      "executor": "builder-r26s1",
                      "scan_claim": "c-0019 (r26-constraint-scan-v2)",
                      "verifier": "INVITED — recomputes from committed "
                                  "bytes (Art. 13), never re-runs"},
            "pre_registration": {
                "byte_map": {"fresh_v7_intervention": FRESH_V7_INT,
                             "fresh_v5_predictor": FRESH_V5_PRED,
                             "pilot_8_riding_full": PILOT_8},
                "lever": "NOVELTY-RELOCATION (catalog-composition) — "
                         "distinct kind from the retired "
                         "contract-bind levers; the V7 bind relocates "
                         "novelty into the arrangement of generic-class "
                         "procurable components (fictional-catalog "
                         "failure excluded by construction)",
                "all_fresh_disclosure": "the rides floor 14/30 ~= 0.467 "
                                        "made the <=0.25 clause "
                                        "structurally unreachable on "
                                        "the r23/r24 map; this battery "
                                        "is ALL-FRESH (the auditor's "
                                        "typed condition 'once a bound "
                                        "generator proves out')",
                "pilot_gate": {"status": pilot.get("gate"),
                               "v7_pilot8_fgap":
                                   pilot.get("v7_pilot8_fgap_mean"),
                               "v61_reference": V61_PILOT8_FGAP},
                "acceptance_verbatim": "feasibility |gap| <= 0.25 AND "
                                       "novelty delta >= 0.5 on >= 30 "
                                       "pairs, and the ablation beats "
                                       "the incumbent (CI excludes it)",
            },
            "judge": {"route": list(JUDGE), "k": K, "pace_s": PACE_S,
                      "transport_ladder": True},
            "generation_record": [
                {"problem_id": p, "repairs": gen_meta[p]["repairs"],
                 "residual_findings":
                     gen_meta[p]["residual_findings"] or "CLEAN"}
                for p in ALL],
            "machine_summary": {
                "repairs_total": repairs_total,
                "pairs_with_residual_findings": residual_pairs,
                "pairs_with_catalog_residual": catalog_residual,
                "disclosure": "the catalog scan (r26) is the V7/D2 "
                              "lever's deterministic leg — findings "
                              "feed the NEUTRAL repair directive"},
            "ladder_stats": ladder_stats,
            "results": results,
            "summary_all_fresh": s_all,
            "summary_type_credited": s_tc,
            "summary_intervention_rows": s_iv,
            "summary_predictor_rows": s_pred,
            "art20_ablation": {
                "arm_under_test": "SYS_A1_INT_V7 (catalog-composition "
                                  "bind) — lever kind "
                                  "novelty-relocation, round 1/2",
                "incumbent": "SYS_A1_INT_V4 single-draw (the r20 bytes)",
                "metric": "intervention-subset feasibility |gap|",
                "incumbent_intervention_fgap_r20": R20_IV_FGAP,
                "incumbent_intervention_nd_r20": R20_IV_ND,
                "v7_intervention_fgap_this":
                    s_iv.get("feasibility_abs_gap_mean"),
                "v7_intervention_fgap_ci": [iv_lo, iv_hi],
                "v7_ndelta_this": s_iv.get("novelty_delta_mean"),
                "beats_incumbent": beats,
                "round_rule": "if not beating the incumbent on the "
                              "primary metric, ONE more round is "
                              "allowed (Art. 20) — the lever retires "
                              "at 2 if round 2 also fails",
                "predictor_reference": {
                    "r11_rides_fgap_sum": R11_PRED_FGAP_SUM,
                    "v5_fresh_fgap_mean":
                        s_pred.get("feasibility_abs_gap_mean"),
                    "note": "the predictor side's first battery "
                            "measurement under SYS_A1F_V5 (r24, "
                            "holdout-v3-proven); rides floor no longer "
                            "applies"},
            },
        }
        FULL_OUT.write_text(json.dumps(record, indent=1, default=str)
                            + "\n", encoding="utf-8")
        for lbl, s in (("ALL-FRESH (GATE)", s_all),
                       ("INTERVENTION (ABLATION)", s_iv),
                       ("PREDICTOR", s_pred)):
            print(f"[r26v7] {lbl}: n={s.get('n_valid')} | nov Δ "
                  f"{s.get('novelty_delta_mean')} CI "
                  f"{s.get('novelty_ci95')} | feas |gap| "
                  f"{s.get('feasibility_abs_gap_mean')} CI "
                  f"{s.get('feasibility_ci95')} | prefer "
                  f"{s.get('prefer_tally')}", flush=True)
        ab = record["art20_ablation"]
        print(f"[r26v7] ablation: incumbent {ab['incumbent_intervention_fgap_r20']}"
              f" | V7 {ab['v7_intervention_fgap_this']} CI "
              f"{ab['v7_intervention_fgap_ci']} | beats_incumbent="
              f"{ab['beats_incumbent']} | nd {ab['v7_ndelta_this']} vs "
              f"{ab['incumbent_intervention_nd_r20']}", flush=True)
        print(f"[r26v7] catalog-fit: {catalog_residual}/30 pairs with "
              f"catalog residuals | repairs={repairs_total}", flush=True)
        print(f"-> {FULL_OUT}", flush=True)
        return 0
    finally:
        gw.terminate()


def _ci(vals):
    """Normal-approx 95% CI (the metric core's form) for the ablation
    read."""
    import math
    if not vals:
        return None, None
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1)) \
        if len(vals) > 1 else 0.0
    se = sd / math.sqrt(len(vals))
    return round(m - 1.96 * se, 3), round(m + 1.96 * se, 3)


if __name__ == "__main__":
    raise SystemExit(main() or 0)

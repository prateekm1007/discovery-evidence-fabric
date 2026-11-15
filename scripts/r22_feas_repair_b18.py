#!/usr/bin/env python3
"""r22_feas_repair_b18.py — AM22 D1: the DIRECT feasibility lever
(feasibility-repair leg, V5) under Art. 29 claim-before-work.

PRE-REGISTERED BEFORE ANY MEASUREMENT (this file + the claim c-0006 ride
the same push, before any judge call exists).

WORK ITEM (Art. 29): claim c-0006 in eval/work_claims.json — work_id
"r22-feas-repair-b18", EXECUTOR builder-r20s1, kind "measurement".
VERIFIER: the peer session, INVITED — it recomputes from these committed
bytes (Art. 13) and NEVER re-runs. The c-0004 verifier invitation also
stands (F35 recompute instrument lands this round as executor-side
diligence; the Art. 29c verifier record remains the peer's to file).

DESIGN CHOICE (typed, AM22 D1 offered two options): the REPAIR LEG, not
feasibility-first selection. Basis: the BOK arm measured NEGATIVE with a
judge-blind selector (no feasibility signal; bill-heavy preference read
as burden; 2 novelty-negative selections) — selection is measured dead;
the residual is BILL-LEVEL (development-program leakage + burden), which
a typed repair pass acts on directly. Feasibility-first selection by the
canonical judge would break judge!=generator independence (Art. 10/26);
selection by a second model is a NEW arm without measured basis. The
repair leg is judge-blind end-to-end.

BYTE MAP (pre-declared, from committed bytes):
  RIDE_R11_PRED (12): ALL 12 predictor pairs ride their r11 committed
    judged rows byte-identical (row source eval/battery_a1w_r11.json;
    byte source eval/pairs/r11_a1w_r1/; sha-verified at run time).
    TYPED BASIS: unchanged from r21 — the V4-predictor retarget is
    RETIRED per Art. 20 (two non-winning rounds); rides keep the
    judge-stability control and recover eval-new10 (n=30).
  FRESH_V5_REPAIR (18): ALL 18 intervention pairs — single draft under
    SYS_A1_INT_V4 (contract byte-unchanged), typed feasibility scan,
    then the V5 REPAIR LEG (budget 2, machine-enforced scan + typed
    rework directive; residuals disclosed). NO selection (K_GEN=1): the
    lever is the repair leg, isolated from the dead selection lever.
    NO outcome-based exclusions; all candidate/repair bytes recorded.

JUDGING: the CANONICAL battery metric, unchanged (Art. 16/19):
  eval/run._rubric_prompt + scripts/_f28_axis_suffix_v2.txt +
  crowllm/qwen-3.8-max:free t=0, K=3, eval/battery_metrics strict
  plurality. Judge != generator (crowllm/Qwen vs zai/GLM). Transport
  ladder identical to the c-0002/c-0004 pre-registrations (3 attempts,
  20s/60s backoff on non-JUDGE_VALID, attempts recorded) + final sweep
  for rows with <2 valid draws. Judge phases staggered against any
  concurrent peer judging (generation runs first here).

FAIL-CLOSED ARITHMETIC DISCLOSURE (pre-registered): the 12 predictor
rides carry r11 feasibility |gap| summing to 14 over 30 rows, so the
overall <=0.25 acceptance floor is 14/30 ~= 0.467 EVEN IF every fresh
row judged at gap 0. This battery DECIDES THE REPAIR LEVER (Art. 20
ablation vs the single-draw incumbent on the changed arm); the clause
needs an all-fresh battery once a lever proves out — pre-registered
contingency, unchanged since r21.

ACCEPTANCE (AM22 D1, verbatim): feasibility |gap| <= 0.25 AND novelty
  delta >= 0.5 on >= 30 pairs, pre-registered, type-credited,
  judge != generator, queue CI green. One EXECUTOR (this claim) + one
  VERIFIER record (the peer's, on committed bytes). Gate re-decision is
  the auditor's; this record measures.

TYPED EXPECTATION (disclosed, not invented): the repair leg targets the
residual where the V4 pilot proved the contract binds (bill level). If
it works, the changed-arm feasibility |gap| drops below the incumbent's
1.5 with novelty held >= +0.5; if the audit block reads as burden, the
arm loses and is retired at round 1 (honest either way; Art. 20 clock).
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

from r19_a1w_v4_contract import SYS_A1_INT_V4  # noqa: E402
from r22_a1w_v5_repair import scan, repair_directive, AUDIT_HEADER  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r22_feas_repair_v5"
R11 = REPO / "eval" / "battery_a1w_r11.json"
R11_DIR = REPO / "eval" / "pairs" / "r11_a1w_r1"
R20_REC = REPO / "eval" / "battery_a1w2_full_r20.json"
FULL_OUT = REPO / "eval" / "battery_feas_repair_r22.json"
FULL_PARTIAL = REPO / "eval" / "battery_feas_repair_r22.partial.json"
JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
K = 3
REPAIR_BUDGET = 2
LADDER_BACKOFF_S = (20.0, 60.0)
SWEEP_PASSES = 2
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

R11ROWS = {r["problem_id"]: r for r in
           json.loads(R11.read_text(encoding="utf-8"))["results"]}
R20ROWS = {r["problem_id"]: r for r in
           json.loads(R20_REC.read_text(encoding="utf-8"))["results"]}
RIDE_R11_PRED = sorted(p for p, r in R11ROWS.items()
                       if str(r.get("question_type", "")).startswith(
                           "predictor"))
FRESH_V5 = sorted(p for p in R11ROWS if p not in RIDE_R11_PRED)
ALL = RIDE_R11_PRED + FRESH_V5
RETIRED_V4_PRED = {"eval-new06-bearing-vibration-predictor",
                   "eval-new07-transformer-dga-predictor",
                   "eval-new10-solar-inverter-predictor",
                   "eval-new12-axle-bearing-predictor"}

assert len(ALL) == 30 and len(set(ALL)) == 30, "r22 byte map malformed"
assert set(ALL) == set(R11ROWS), "r22 byte map != r11 pool"
assert len(RIDE_R11_PRED) == 12 and len(FRESH_V5) == 18, "r22 split drifted"
assert not RETIRED_V4_PRED - set(RIDE_R11_PRED), "retired pairs off ride set"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _backfill_tc(row):
    med = row.get("median_axes")
    if med and "testability_delta" not in row:
        if "T_A" in med and "T_B" in med:
            row["testability_delta"] = med["T_A"] - med["T_B"]
        if "C_A" in med and "C_B" in med:
            row["constraint_delta"] = med["C_A"] - med["C_B"]
        row["tc_backfilled_from"] = "median_axes (committed bytes)"
    return row


def _prob_q(prob):
    return json.dumps(prob, ensure_ascii=False)


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


def _retry_call(f, *args, tries=3, backoff=(10.0, 30.0)):
    """Transient-failure retry (typed, Art. 15: infra failure is never
    scientific rejection): generation/critic calls get 3 attempts with
    backoff on any transport exception; the r21 run lost a whole driver
    pass to a single HTTP 500 — never again."""
    last = None
    for t in range(tries):
        try:
            return f(*args)
        except Exception as e:  # noqa: BLE001 — typed infra retry
            last = e
            if t < tries - 1:
                time.sleep(backoff[min(t, len(backoff) - 1)])
                print(f"    [retry {t+1}] {type(e).__name__}: {str(e)[:90]}",
                      flush=True)
    raise last


def draft_and_repair(pid, prob, gw_key):
    """V5 leg: one draft under the UNCHANGED V4 contract, typed scan,
    repair pass (budget 2) with the typed rework directive, re-scan.
    All drafts/repairs + scans recorded for verifier recomputation.
    Generation/critic calls are transient-retry hardened (Art. 15)."""
    qt = (prob.get("question_type") or "").lower()
    q = _prob_q(prob)
    attempts = []
    draft, lat = _retry_call(_gen, q, SYS_A1_INT_V4, gw_key)
    cr = _retry_call(critic, draft, prob)
    tg = gate_question_type(draft, prob)
    vio0 = scan(draft)
    attempts.append({"stage": "draft", "chars": len(draft),
                     "latency_s": round(lat, 1),
                     "critic_verdict": cr["verdict"], "type_gate": tg,
                     "scan": vio0, "sha256_16": _sha(draft)})
    print(f"    [draft] CLEAN={cr['verdict']} gate={tg['verdict']} "
          f"scan={list(vio0) or 'CLEAN'}", flush=True)
    final, meta = draft, {"repairs": 0, "residual_findings": [],
                          "audit_block": False}
    vio = vio0
    for rep in range(1, REPAIR_BUDGET + 1):
        if not vio:
            break
        directive = repair_directive(vio)
        final, rlat = _retry_call(_gen, q + "\n\n" + directive,
                                  SYS_A1_INT_V4, gw_key)
        cr_r = _retry_call(critic, final, prob)
        vio = scan(final, repaired=True)
        attempts.append({"stage": f"repair_{rep}", "chars": len(final),
                         "latency_s": round(rlat, 1),
                         "critic_verdict": cr_r["verdict"],
                         "scan": vio, "sha256_16": _sha(final)})
        meta["repairs"] = rep
        print(f"    [repair {rep}] scan={list(vio) or 'CLEAN'} "
              f"({rlat:.0f}s)", flush=True)
    meta["residual_findings"] = vio
    meta["audit_block"] = AUDIT_HEADER in final
    meta["final_sha256_16"] = _sha(final)
    meta["attempts"] = attempts
    return final, meta


def judge_slot(pid, k, prompt):
    attempts = []
    outcome = None
    jc = None
    for try_n in range(1 + len(LADDER_BACKOFF_S)):
        if try_n:
            time.sleep(LADDER_BACKOFF_S[try_n - 1])
        econ.reset_governor(f"r22frepa:{pid}:{k}"
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


def main() -> int:
    r11_pred_bytes = {p: json.loads((R11_DIR / f"{p}.json").read_text(
        encoding="utf-8"))["a1_answer"] for p in RIDE_R11_PRED}
    gw, gw_key = start_gateway()
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        # ---------- phase 1: draft + repair (resume-safe) ---------------
        for pid in FRESH_V5:
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [gen] {pid[:36]:<38} exists (rides)", flush=True)
                continue
            prob = _prob(pid)
            t0 = time.time()
            ans, meta = draft_and_repair(pid, prob, gw_key)
            dst.write_text(
                json.dumps({"problem_id": pid,
                            "a1_source":
                                "SYS_A1_INT_V4+V5-repair-leg/r22_feas_repair_b18",
                            "question_type": prob.get("question_type"),
                            "a1_answer": ans, "meta": meta,
                            "generated_at": now},
                           indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [gen] {pid[:36]:<38} repairs={meta['repairs']} "
                  f"residual={list(meta['residual_findings']) or 'CLEAN'} "
                  f"audit={meta['audit_block']} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        # ---------- phase 2: assemble + judge (canonical) ----------------
        prior = {}
        if FULL_PARTIAL.exists():
            for r in json.loads(FULL_PARTIAL.read_text(encoding="utf-8")):
                prior[r["problem_id"]] = r
        results, ride_manifest = [], []
        for pid in ALL:
            if pid in prior:
                results.append(prior[pid])
                print(f"  [{pid[:32]:<34}] resumed", flush=True)
                continue
            if pid in RIDE_R11_PRED:
                row = _backfill_tc(dict(R11ROWS[pid]))
                row["ride"] = {
                    "row_source": "battery_a1w_r11.json",
                    "byte_source": f"eval/pairs/r11_a1w_r1/{pid}.json",
                    "a1_answer_sha256_16": _sha(r11_pred_bytes[pid]),
                    "rule": "byte-identical pair rides its committed "
                            "judged row (AM19 sec.2 determinism finding)"
                            + ("; V4-PRED RETARGET RETIRED per Art. 20 "
                               "(typed r21) — incumbent bytes ride"
                               if pid in RETIRED_V4_PRED else "")}
                ride_manifest.append({"problem_id": pid, "row_source": "r11",
                                      "retired_v4_pred":
                                          pid in RETIRED_V4_PRED})
                results.append(row)
                print(f"  [{pid[:32]:<34}] ride r11 row", flush=True)
                continue
            prob = _prob(pid)
            rec = json.loads((OUT_DIR / f"{pid}.json").read_text(
                encoding="utf-8"))
            a1 = str(rec["a1_answer"])
            base, b_src = baseline_for(pid)
            assert base.strip(), f"no baseline for {pid}"
            prompt = _rubric_prompt(prob, a1[:7000], base[:7000],
                                    None) + AXIS_SUFFIX
            draws = []
            for k in range(K):
                jc, outcome, atts = judge_slot(pid, k, prompt)
                draws.append({"k": k, "outcome": outcome,
                              "axes": parse_axes(jc),
                              "prefer": (jc.get("valid") or {}).get(
                                  "prefer"),
                              "transport_attempts": atts})
                time.sleep(PACE_S)
            dec = row_metrics(draws)
            med = dec["median_axes"]
            r20row = R20ROWS[pid]
            row = {"problem_id": pid,
                   "a1_arm": "SYS_A1_INT_V4+V5_REPAIR_LEG",
                   "question_type": prob.get("question_type"),
                   "question_type_gate":
                       rec["meta"]["attempts"][0]["type_gate"],
                   "baseline_source": b_src,
                   "byte_provenance": {
                       "byte_source":
                           f"eval/pairs/r22_feas_repair_v5/{pid}.json",
                       "a1_answer_sha256_16": _sha(a1),
                       "generation": "single draft (V4 contract, "
                                     "byte-unchanged) + V5 feasibility-"
                                     "repair leg (typed scan, budget 2, "
                                     "no selection)"},
                   "judge": list(JUDGE), "draws": draws,
                   "majority_prefer": dec["majority_prefer"],
                   "median_axes": med,
                   "r20_reference": {
                       "record": "eval/battery_a1w2_full_r20.json",
                       "r20_fgap": r20row.get("feasibility_abs_gap"),
                       "r20_ndelta": r20row.get("novelty_delta")}}
            if med:
                row["novelty_delta"] = med["N_A"] - med["N_B"]
                row["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
                row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
                row["testability_delta"] = med["T_A"] - med["T_B"]
                row["constraint_delta"] = med["C_A"] - med["C_B"]
            results.append(row)
            FULL_PARTIAL.write_text(
                json.dumps(results, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [{pid[:32]:<34}] judged nd="
                  f"{row.get('novelty_delta')} fgap="
                  f"{row.get('feasibility_abs_gap')} "
                  f"prefer={row.get('majority_prefer')}", flush=True)
        # ---------- phase 3: transport sweep ------------------------------
        for sweep in range(SWEEP_PASSES):
            dead = [r for r in results
                    if r.get("draws") and valid_draws(r) < 2
                    and str(r.get("a1_arm") or "").startswith("SYS_A1_INT_V4+V5")]
            if not dead:
                break
            print(f"  [sweep {sweep+1}] re-drawing {len(dead)} dead rows",
                  flush=True)
            for row in dead:
                pid = row["problem_id"]
                prob = _prob(pid)
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
                    row["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
                    row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
                    row["testability_delta"] = med["T_A"] - med["T_B"]
                    row["constraint_delta"] = med["C_A"] - med["C_B"]
                FULL_PARTIAL.write_text(
                    json.dumps(results, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
        assert len(results) == 30, f"pool incomplete: {len(results)}"
        # ---------- phase 4: summaries + ablation -------------------------
        iv = [r for r in results
              if str(r.get("question_type", "")).startswith("intervention")]
        pd_ = [r for r in results
               if str(r.get("question_type", "")).startswith("predictor")]
        tc = [r for r in results
              if (r.get("question_type_gate") or {}).get("verdict")
              == "MATCH"]
        s_tc = summarize(tc, "type-MATCH pairs only — the AM22 D1 "
                             "acceptance form (rides carry r11 gate "
                             "MATCH; fresh rows carry their draft's "
                             "typed gate verdict)")
        s_iv = summarize(iv, "INTERVENTION rows only (the changed arm — "
                             "the Art. 20 ablation read)")
        iv_r20 = summarize(
            [r for r in R20ROWS.values()
             if str(r.get("question_type", "")).startswith("intervention")],
            "r20 intervention rows (incumbent single-draw bytes)")
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
        repairs_total = sum(
            json.loads((OUT_DIR / f"{p}.json").read_text(
                encoding="utf-8"))["meta"]["repairs"] for p in FRESH_V5)
        residual = sum(
            1 for p in FRESH_V5
            if json.loads((OUT_DIR / f"{p}.json").read_text(
                encoding="utf-8"))["meta"]["residual_findings"])
        record = {
            "record": "BATTERY_INT_FREPAIR_R22/1.0.0 — the AM22 D1 "
                      "direct-feasibility measurement (V5 repair leg vs "
                      "the single-draw incumbent)",
            "at": now,
            "claim": {"work_id": "r22-feas-repair-b18", "claim_id": "c-0006",
                      "executor": "builder-r20s1",
                      "registry": "eval/work_claims.json",
                      "verifier": "peer session INVITED — recomputes "
                                  "from committed bytes (Art. 13), "
                                  "never re-runs; drafts, repair "
                                  "attempts and scans are all recorded "
                                  "per pair"},
            "pre_registration": {
                "commit": "this driver + registry claim c-0006 pushed "
                          "BEFORE any LLM call (git history order)",
                "byte_map": {"ride_r11_predictor": RIDE_R11_PRED,
                             "fresh_v5_repair": FRESH_V5},
                "design_choice": "repair leg (option b), NOT "
                                 "feasibility-first selection — typed "
                                 "basis: BOK selection measured NEGATIVE "
                                 "(c-0004); judge-scored selection would "
                                 "break judge!=generator (Art. 10/26)",
                "repair_leg": "scan (DEV_NEED / BILL_UNTAGGED / "
                              "AUDIT_MISSING) + typed rework directive "
                              "(procurable classes, MINIMAL bill, "
                              "mechanism preserved, FEASIBILITY AUDIT "
                              "(V5) block); budget 2; residuals "
                              "disclosed",
                "acceptance_verbatim": "feasibility |gap| <= 0.25 AND "
                                       "novelty delta >= 0.5 on >= 30 "
                                       "pairs, pre-registered, "
                                       "type-credited, judge != "
                                       "generator, queue CI green",
                "arithmetic_disclosure": "the 12 predictor rides carry "
                                         "r11 fgap summing to 14 -> "
                                         "overall floor 14/30 ~= 0.467 "
                                         "even at fresh=0; this battery "
                                         "decides the REPAIR LEVER"},
            "arms": {
                "A": "18 fresh intervention pairs: single V4 draft + V5 "
                     "feasibility-repair leg (K_GEN=1, no selection) + "
                     "12 predictor pairs riding r11 incumbent bytes "
                     "byte-identical (V4-pred retarget retired per "
                     "Art. 20, typed r21)",
                "B": "CURATED baselines — assembly identical to "
                     "batteries r7-r22"},
            "judge": {"route": list(JUDGE), "k": K, "pace_s": PACE_S,
                      "transport_ladder": True,
                      "independence": "crowllm/Qwen vs zai/GLM "
                                      "generator — provider AND family "
                                      "independent"},
            "ride_manifest": ride_manifest,
            "generation_record": [
                {"problem_id": p,
                 "repairs": json.loads((OUT_DIR / f"{p}.json").read_text(
                     encoding="utf-8"))["meta"]["repairs"],
                 "residual_findings":
                     json.loads((OUT_DIR / f"{p}.json").read_text(
                         encoding="utf-8"))["meta"]["residual_findings"]
                     or "CLEAN",
                 "audit_block":
                     json.loads((OUT_DIR / f"{p}.json").read_text(
                         encoding="utf-8"))["meta"]["audit_block"]}
                for p in FRESH_V5],
            "repair_leg_summary": {"repairs_total": repairs_total,
                                   "pairs_with_residual_findings": residual,
                                   "pairs_with_audit_block": sum(
                                       1 for g in record.get(
                                           "generation_record", [])
                                       if g.get("audit_block"))},
            "ladder_stats": ladder_stats,
            "results": results,
            "summary_type_credited": s_tc,
            "summary_intervention_rows": s_iv,
            "summary_predictor_rows": summarize(
                pd_, "PREDICTOR rows only (12 byte-identical r11 rides)"),
            "summary_all_valid": summarize(
                results, "all valid pairs (unfiltered sensitivity)"),
            "art20_ablation": {
                "arm_under_test": "SYS_A1_INT_V4 + V5 feasibility-repair "
                                  "leg (direct feasibility lever)",
                "incumbent": "SYS_A1_INT_V4 single-draw (the r20 bytes)",
                "metric": "intervention-subset type-credited feasibility "
                          "|gap| (the arm that changed); overall "
                          "type-credited read for continuity",
                "incumbent_intervention_fgap_r20":
                    iv_r20.get("feasibility_abs_gap_mean"),
                "v5_intervention_fgap_this":
                    s_iv.get("feasibility_abs_gap_mean"),
                "incumbent_ndelta_r20": iv_r20.get("novelty_delta_mean"),
                "v5_ndelta_this": s_iv.get("novelty_delta_mean"),
                "beats_incumbent": (
                    (s_iv.get("feasibility_abs_gap_mean") or 9)
                    < (iv_r20.get("feasibility_abs_gap_mean") or 0)
                    and (s_iv.get("novelty_delta_mean") or 0) >= 0.5),
                "rule": "auto-retire if not beating the incumbent on the "
                        "primary metric within 2 rounds (Art. 20); "
                        "round 1/2 measured here; the BOK arm is "
                        "RETIRED in the same change that ships this "
                        "replacement (Art. 16 accounting in "
                        "ABLATION_REGISTRY.json)"},
            "gate_note": ("MEASUREMENT for the auditor (AM22 D1 lane): "
                          "read on summary_type_credited (primary); the "
                          "<=0.25 clause is arithmetically capped by the "
                          "pre-registered rides at ~0.467 (disclosed "
                          "pre-registration); the REPAIR-LEVER decision "
                          "reads on art20_ablation; the authoritative "
                          "gate re-decision is the auditor's"),
        }
        FULL_OUT.write_text(
            json.dumps(record, indent=1, default=str) + "\n",
            encoding="utf-8")
        for lbl, s in (("TYPE-CREDITED (PRIMARY)", s_tc),
                       ("INTERVENTION (ABLATION)", s_iv),
                       ("ALL-VALID", record["summary_all_valid"])):
            print(f"[r22frepa] {lbl}: n={s.get('n_valid')} | nov Δ "
                  f"{s.get('novelty_delta_mean')} CI "
                  f"{s.get('novelty_ci95')} | feas |gap| "
                  f"{s.get('feasibility_abs_gap_mean')} CI "
                  f"{s.get('feasibility_ci95')} | prefer "
                  f"{s.get('prefer_tally')}", flush=True)
        print(f"[r22frepa] art20 beats_incumbent="
              f"{record['art20_ablation']['beats_incumbent']} | repairs="
              f"{repairs_total} residual={residual}", flush=True)
        print(f"-> {FULL_OUT}", flush=True)
        return 0
    finally:
        gw.terminate()


_PROBS = None


def _prob(pid):
    global _PROBS
    if _PROBS is None:
        _PROBS = {}
        plist = json.loads((REPO / "eval" / "problems.json").read_text())
        plist = (plist if isinstance(plist, list)
                 else plist.get("problems", []))
        for p in plist:
            _PROBS[str(p.get("problem_id") or p.get("id"))] = p
        for p in json.loads((REPO / "eval" / "problems_dev12.json")
                            .read_text())["problems"]:
            _PROBS.setdefault(p["problem_id"], p)
    return _PROBS[pid]


if __name__ == "__main__":
    raise SystemExit(main() or 0)

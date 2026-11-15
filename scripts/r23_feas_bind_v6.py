#!/usr/bin/env python3
"""r23_feas_bind_v6.py — AM23 D2 round-2: the feasibility lever moves
INTO the draft contract (SYS_A1_INT_V6 = V4 + FEASIBILITY BIND at
mechanism choice) under Art. 29 claim-before-work.

WORK ITEM (Art. 29): claim c-0012 in eval/work_claims.json — work_id
"r23-feas-bind-v6", EXECUTOR builder-r20s1, kind "measurement".
VERIFIER: the peer session, INVITED — recomputes from committed bytes
(Art. 13), never re-runs.

EVOLUTION, TYPED (Art. VI/20): the V5 post-generation repair leg
measured NEGATIVE (r22: changed-arm 2.222 vs incumbent 1.5; 11/18
residuals — the directive neither binds the bill format nor reroutes
the mechanism). V5 is RETIRED at round 1 in the same change that ships
its successor (Art. 16 accounting): V6 binds at MECHANISM CHOICE — the
level the V4 pilot proved responsive (hard-7 fgap 3.0 -> 1.857). The
machine path is byte-unchanged (critic + gate + typed machine repair
directives, budget 2 — the r20/r21/holdout code path, disclosed); the
repair pass is NEUTRAL (resolve typed findings only) so the arm under
test is the CONTRACT BIND, isolated from the retired repair lever.

BYTE MAP (pre-declared, unchanged from r21/r22):
  RIDE_R11_PRED (12): ALL 12 predictor pairs ride their r11 committed
    judged rows byte-identical (recovers eval-new10; n=30).
  FRESH_V6 (18): ALL 18 intervention pairs — single draft under
    SYS_A1_INT_V6, machine-internal typed repairs (budget 2,
    findings disclosed), NO selection (K_GEN=1), NO outcome-based
    exclusions.

FAIL-CLOSED ARITHMETIC DISCLOSURE (pre-registered): the 12 predictor
rides carry r11 feasibility |gap| summing to 14 over 30 rows, so the
overall <=0.25 acceptance floor is 14/30 ~= 0.467 EVEN IF every fresh
row judged at gap 0. This battery DECIDES THE LEVER (Art. 20 ablation
vs the single-draw incumbent on the changed arm); the clause needs an
all-fresh battery once a feasibility-bound generator proves out.

ACCEPTANCE (AM22/AM23 D2, verbatim): feasibility |gap| <= 0.25 AND
  novelty delta >= 0.5 on >= 30 pairs, pre-registered, type-credited,
  judge != generator, queue CI green. One EXECUTOR (this claim) + one
  VERIFIER record (the peer's, on committed bytes).
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

from r23_a1w_v6_contract import (  # noqa: E402
    SYS_A1_INT_V6, MACHINE_REPAIR_DIRECTIVE)
from r22_a1w_v5_repair import scan  # noqa: E402  (the typed scanner)
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r23_feas_bind_v6"
R11 = REPO / "eval" / "battery_a1w_r11.json"
R11_DIR = REPO / "eval" / "pairs" / "r11_a1w_r1"
R20_REC = REPO / "eval" / "battery_a1w2_full_r20.json"
FULL_OUT = REPO / "eval" / "battery_feas_bind_v6_r23.json"
FULL_PARTIAL = REPO / "eval" / "battery_feas_bind_v6_r23.partial.json"
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
FRESH_V6 = sorted(p for p in R11ROWS if p not in RIDE_R11_PRED)
ALL = RIDE_R11_PRED + FRESH_V6
RETIRED_V4_PRED = {"eval-new06-bearing-vibration-predictor",
                   "eval-new07-transformer-dga-predictor",
                   "eval-new10-solar-inverter-predictor",
                   "eval-new12-axle-bearing-predictor"}

assert len(ALL) == 30 and len(set(ALL)) == 30, "r23 byte map malformed"
assert set(ALL) == set(R11ROWS), "r23 byte map != r11 pool"
assert len(RIDE_R11_PRED) == 12 and len(FRESH_V6) == 18, "r23 split drifted"
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
    last = None
    for t in range(tries):
        try:
            return f(*args)
        except Exception as e:  # noqa: BLE001 — typed infra retry (Art. 15)
            last = e
            if t < tries - 1:
                time.sleep(backoff[min(t, len(backoff) - 1)])
                print(f"    [retry {t+1}] {type(e).__name__}: {str(e)[:90]}",
                      flush=True)
    raise last


def draft_with_machine_repairs(pid, prob, gw_key):
    """V6: ONE draft under the bind contract; machine-internal typed
    repairs (neutral directive, budget 2) if the typed scan fires;
    residuals disclosed. NO feasibility-rework text, NO selection."""
    q = _prob_q(prob)
    attempts = []
    draft, lat = _retry_call(_gen, q, SYS_A1_INT_V6, gw_key)
    cr = _retry_call(critic, draft, prob)
    tg = gate_question_type(draft, prob)
    vio0 = scan(draft)
    attempts.append({"stage": "draft", "chars": len(draft),
                     "latency_s": round(lat, 1),
                     "critic_verdict": cr["verdict"], "type_gate": tg,
                     "scan": vio0, "sha256_16": _sha(draft)})
    print(f"    [draft] CLEAN={cr['verdict']} gate={tg['verdict']} "
          f"scan={list(vio0) or 'CLEAN'}", flush=True)
    final, meta = draft, {"repairs": 0, "residual_findings": []}
    vio = vio0
    for rep in range(1, REPAIR_BUDGET + 1):
        if not vio:
            break
        findings = "; ".join(f"{k}: {'; '.join(v)[:120]}"
                             for k, v in vio.items()) or "none"
        final, rlat = _retry_call(
            _gen, q + "\n\n" + MACHINE_REPAIR_DIRECTIVE.format(
                findings=findings), SYS_A1_INT_V6, gw_key)
        cr_r = _retry_call(critic, final, prob)
        vio = scan(final)
        attempts.append({"stage": f"repair_{rep}", "chars": len(final),
                         "latency_s": round(rlat, 1),
                         "critic_verdict": cr_r["verdict"],
                         "findings_disclosed": list(vio),
                         "sha256_16": _sha(final)})
        meta["repairs"] = rep
        print(f"    [repair {rep}] scan={list(vio) or 'CLEAN'} "
              f"({rlat:.0f}s)", flush=True)
    meta["residual_findings"] = vio
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
        econ.reset_governor(f"r23v6bind:{pid}:{k}"
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
        # ---------- phase 1: draft + machine repairs --------------------
        for pid in FRESH_V6:
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [gen] {pid[:36]:<38} exists (rides)", flush=True)
                continue
            prob = _prob(pid)
            t0 = time.time()
            ans, meta = draft_with_machine_repairs(pid, prob, gw_key)
            dst.write_text(
                json.dumps({"problem_id": pid,
                            "a1_source": "SYS_A1_INT_V6/r23_feas_bind_v6",
                            "question_type": prob.get("question_type"),
                            "a1_answer": ans, "meta": meta,
                            "generated_at": now},
                           indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [gen] {pid[:36]:<38} repairs={meta['repairs']} "
                  f"residual={list(meta['residual_findings']) or 'CLEAN'} "
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
                   "a1_arm": "SYS_A1_INT_V6_BIND",
                   "question_type": prob.get("question_type"),
                   "question_type_gate":
                       rec["meta"]["attempts"][0]["type_gate"],
                   "baseline_source": b_src,
                   "byte_provenance": {
                       "byte_source":
                           f"eval/pairs/r23_feas_bind_v6/{pid}.json",
                       "a1_answer_sha256_16": _sha(a1),
                       "generation": "single draft under SYS_A1_INT_V6 "
                                     "(V4 + feasibility bind at "
                                     "mechanism choice) + neutral "
                                     "machine-internal repairs "
                                     "(budget 2); no selection"},
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
                    and str(r.get("a1_arm") or "").startswith(
                        "SYS_A1_INT_V6")]
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
                    json.dumps(results, indent=1, ensure_ascii=False)
                    + "\n", encoding="utf-8")
        assert len(results) == 30, f"pool incomplete: {len(results)}"
        # ---------- phase 4: summaries + ablation -------------------------
        iv = [r for r in results
              if str(r.get("question_type", "")).startswith("intervention")]
        pd_ = [r for r in results
               if str(r.get("question_type", "")).startswith("predictor")]
        tc = [r for r in results
              if (r.get("question_type_gate") or {}).get("verdict")
              == "MATCH"]
        s_tc = summarize(tc, "type-MATCH pairs only — the AM22/AM23 D2 "
                             "acceptance form (rides carry r11 gate "
                             "MATCH; fresh rows carry their draft's "
                             "typed gate verdict)")
        s_iv = summarize(iv, "INTERVENTION rows only (the changed arm — "
                             "the Art. 20 ablation read)")
        iv_r20 = summarize(
            [r for r in R20ROWS.values()
             if str(r.get("question_type", "")).startswith("intervention")],
            "r20 intervention rows (incumbent single-draw bytes)")
        iv_r22 = summarize(
            [r for r in json.loads((REPO / "eval"
                                    / "battery_feas_repair_r22.json")
                                   .read_text(encoding="utf-8"))["results"]
             if str(r.get("question_type", "")).startswith("intervention")],
            "r22 V5-repair-leg intervention rows (retired arm, context)")
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
                encoding="utf-8"))["meta"]["repairs"] for p in FRESH_V6)
        residual = sum(
            1 for p in FRESH_V6
            if json.loads((OUT_DIR / f"{p}.json").read_text(
                encoding="utf-8"))["meta"]["residual_findings"])
        record = {
            "record": "BATTERY_INT_V6BIND_R23/1.0.0 — the AM23 D2 "
                      "round-2 feasibility measurement (contract-level "
                      "bind vs the single-draw incumbent)",
            "at": now,
            "claim": {"work_id": "r23-feas-bind-v6", "claim_id": "c-0012",
                      "executor": "builder-r20s1",
                      "registry": "eval/work_claims.json",
                      "verifier": "peer session INVITED — recomputes "
                                  "from committed bytes (Art. 13), "
                                  "never re-runs"},
            "pre_registration": {
                "commit": "this driver + registry claim c-0012 pushed "
                          "BEFORE any LLM call (git history order)",
                "byte_map": {"ride_r11_predictor": RIDE_R11_PRED,
                             "fresh_v6_bind": FRESH_V6},
                "evolution": "V5 (post-generation repair) RETIRED at "
                             "round 1 in the same change that ships V6 "
                             "(Art. 16); V6 = V4 contract + feasibility "
                             "bind AT MECHANISM CHOICE — the level the "
                             "V4 pilot proved responsive",
                "machine_path": "byte-unchanged r20/r21/holdout code "
                                "path (critic + gate + neutral typed "
                                "machine repairs, budget 2, findings "
                                "disclosed); the repair pass is "
                                "NEUTRAL so the arm under test is the "
                                "contract bind",
                "acceptance_verbatim": "feasibility |gap| <= 0.25 AND "
                                       "novelty delta >= 0.5 on >= 30 "
                                       "pairs, pre-registered, "
                                       "type-credited, judge != "
                                       "generator, queue CI green",
                "arithmetic_disclosure": "the 12 predictor rides carry "
                                         "r11 fgap summing to 14 -> "
                                         "overall floor 14/30 ~= 0.467 "
                                         "even at fresh=0; this battery "
                                         "decides the LEVER"},
            "arms": {
                "A": "18 fresh intervention pairs: single draft under "
                     "SYS_A1_INT_V6 (feasibility bind at mechanism "
                     "choice) + neutral machine repairs (K_GEN=1) + "
                     "12 predictor pairs riding r11 incumbent bytes "
                     "byte-identical",
                "B": "CURATED baselines — assembly identical to "
                     "batteries r7-r23"},
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
                     or "CLEAN"} for p in FRESH_V6],
            "bind_summary": {"repairs_total": repairs_total,
                             "pairs_with_residual_findings": residual},
            "ladder_stats": ladder_stats,
            "results": results,
            "summary_type_credited": s_tc,
            "summary_intervention_rows": s_iv,
            "summary_predictor_rows": summarize(
                pd_, "PREDICTOR rows only (12 byte-identical r11 rides)"),
            "summary_all_valid": summarize(
                results, "all valid pairs (unfiltered sensitivity)"),
            "art20_ablation": {
                "arm_under_test": "SYS_A1_INT_V6 (feasibility bind at "
                                  "mechanism choice)",
                "incumbent": "SYS_A1_INT_V4 single-draw (the r20 bytes)",
                "metric": "intervention-subset type-credited feasibility "
                          "|gap| (the arm that changed)",
                "incumbent_intervention_fgap_r20":
                    iv_r20.get("feasibility_abs_gap_mean"),
                "v5_repair_leg_intervention_fgap_r22":
                    iv_r22.get("feasibility_abs_gap_mean"),
                "v6_bind_intervention_fgap_this":
                    s_iv.get("feasibility_abs_gap_mean"),
                "incumbent_ndelta_r20": iv_r20.get("novelty_delta_mean"),
                "v6_ndelta_this": s_iv.get("novelty_delta_mean"),
                "beats_incumbent": (
                    (s_iv.get("feasibility_abs_gap_mean") or 9)
                    < (iv_r20.get("feasibility_abs_gap_mean") or 0)
                    and (s_iv.get("novelty_delta_mean") or 0) >= 0.5),
                "rule": "auto-retire if not beating the incumbent on the "
                        "primary metric within 2 rounds (Art. 20); "
                        "round 1/2 measured here; V5 retired at 1 with "
                        "this successor shipping in the same change"},
            "gate_note": ("MEASUREMENT for the auditor (AM23 D2 lane): "
                          "read on summary_type_credited (primary); the "
                          "<=0.25 clause is arithmetically capped by the "
                          "pre-registered rides at ~0.467 (disclosed "
                          "pre-registration); the LEVER decision reads "
                          "on art20_ablation; the authoritative gate "
                          "re-decision is the auditor's"),
        }
        FULL_OUT.write_text(
            json.dumps(record, indent=1, default=str) + "\n",
            encoding="utf-8")
        for lbl, s in (("TYPE-CREDITED (PRIMARY)", s_tc),
                       ("INTERVENTION (ABLATION)", s_iv),
                       ("ALL-VALID", record["summary_all_valid"])):
            print(f"[r23v6] {lbl}: n={s.get('n_valid')} | nov Δ "
                  f"{s.get('novelty_delta_mean')} CI "
                  f"{s.get('novelty_ci95')} | feas |gap| "
                  f"{s.get('feasibility_abs_gap_mean')} CI "
                  f"{s.get('feasibility_ci95')} | prefer "
                  f"{s.get('prefer_tally')}", flush=True)
        print(f"[r23v6] art20 beats_incumbent="
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

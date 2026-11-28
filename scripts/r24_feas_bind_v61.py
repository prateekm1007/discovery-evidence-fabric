#!/usr/bin/env python3
"""r24_feas_bind_v61.py — AM24 D1: V6 ROUND 2 (Art. 20 clock 2/2) —
the feasibility bind + the F36 constraint-awareness fix, measured
under Art. 29 claim-before-work.

WORK ITEM: claim c-0014 in eval/work_claims.json — work_id
"r24-v61-constraint-bind", EXECUTOR builder-r20s1, kind "measurement".
VERIFIER: the peer session INVITED (Art. 13, from committed bytes).

The lever is UNCHANGED in kind (contract-level bind at mechanism
choice); round 2 strengthens it with the constraint-awareness the
auditor's F36 finding demands (allowed-measures enumerations + hard
exclusions read from the problem's own constraint text). Typed as
round 2 of the SAME arm — no clock reset (Art. 20 anti-zombie): if
this round does not beat the incumbent on the changed arm, the
contract-bind lever RETIRES at 2 with full accounting.

BYTE MAP (pre-declared, identical to r23 — controlled comparison):
  RIDE_R11_PRED (12): the 12 predictor pairs ride r11 committed judged
    rows byte-identical (n=30).
  FRESH_V61 (18): the 18 intervention pairs — single draft under
    SYS_A1_INT_V61, typed machine repairs (budget 2: critic/scan +
    constraint-fit findings), NO selection (K_GEN=1).

FAIL-CLOSED ARITHMETIC DISCLOSURE (unchanged, pre-registered): the 12
predictor rides carry r11 fgap summing to 14 -> the overall <=0.25
floor is 14/30 ~= 0.467 even at fresh=0. The Art. 20 decision reads on
the changed arm; the clause needs an all-fresh battery once a bound
generator proves out.

ACCEPTANCE (AM24 D1): feasibility |gap| <= 0.25 AND novelty delta >=
0.5 on >= 30 pairs, and the ablation beats the incumbent (CI excludes
it). Constraint-fit (AM24 D2) is measured here as a typed proxy:
zero-violation rate under the deterministic scan (the authoritative
read stays the auditor's, on holdout v3).
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

from r24_a1w_v61_contract import (  # noqa: E402
    SYS_A1_INT_V61, MACHINE_REPAIR_DIRECTIVE)
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r24_feas_bind_v61"
R11 = REPO / "eval" / "battery_a1w_r11.json"
R11_DIR = REPO / "eval" / "pairs" / "r11_a1w_r1"
R20_REC = REPO / "eval" / "battery_a1w2_full_r20.json"
R23_REC = REPO / "eval" / "battery_feas_bind_v6_r23.json"
FULL_OUT = REPO / "eval" / "battery_feas_bind_v61_r24.json"
FULL_PARTIAL = REPO / "eval" / "battery_feas_bind_v61_r24.partial.json"
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
FRESH_V61 = sorted(p for p in R11ROWS if p not in RIDE_R11_PRED)
ALL = RIDE_R11_PRED + FRESH_V61
assert len(ALL) == 30 and len(set(ALL)) == 30, "r24 byte map malformed"
assert len(RIDE_R11_PRED) == 12 and len(FRESH_V61) == 18


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


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


def draft_with_machine_repairs(pid, prob, gw_key):
    """V6.1: ONE draft under the constraint+bind contract; the
    machine-internal typed repair loop (budget 2) resolves critic
    findings, base-scan findings AND constraint-fit findings; residual
    findings disclosed. NO outcome-based feedback, NO selection."""
    q = _prob_q(prob)
    attempts = []
    draft, lat = _retry_call(_gen, q, SYS_A1_INT_V61, gw_key)
    cr = _retry_call(critic, draft, prob)
    tg = gate_question_type(draft, prob)
    vio = {}
    vio.update(base_scan(draft))
    vio.update(scan_constraint_fit(prob, draft))
    attempts.append({"stage": "draft", "chars": len(draft),
                     "latency_s": round(lat, 1),
                     "critic_verdict": cr["verdict"], "type_gate": tg,
                     "scan": {k: list(v) for k, v in vio.items()},
                     "sha256_16": _sha(draft)})
    print(f"    [draft] CLEAN={cr['verdict']} gate={tg['verdict']} "
          f"scan={list(vio) or 'CLEAN'}", flush=True)
    final, meta = draft, {"repairs": 0, "residual_findings": {}}
    for rep in range(1, REPAIR_BUDGET + 1):
        if not vio:
            break
        findings = "; ".join(f"{k}: {'; '.join(map(str, v))[:110]}"
                             for k, v in vio.items()) or "none"
        final, rlat = _retry_call(
            _gen, q + "\n\n" + MACHINE_REPAIR_DIRECTIVE.format(
                findings=findings), SYS_A1_INT_V61, gw_key)
        cr_r = _retry_call(critic, final, prob)
        vio = {}
        vio.update(base_scan(final))
        vio.update(scan_constraint_fit(prob, final))
        attempts.append({"stage": f"repair_{rep}", "chars": len(final),
                         "latency_s": round(rlat, 1),
                         "critic_verdict": cr_r["verdict"],
                         "findings_disclosed":
                             {k: list(v) for k, v in vio.items()},
                         "sha256_16": _sha(final)})
        meta["repairs"] = rep
        print(f"    [repair {rep}] scan={list(vio) or 'CLEAN'} "
              f"({rlat:.0f}s)", flush=True)
    meta["residual_findings"] = {k: list(v) for k, v in vio.items()}
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
        econ.reset_governor(f"r24v61bind:{pid}:{k}"
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
    gw, gw_key = start_gateway()
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        # ---------- phase 1: drafts + typed machine repairs -------------
        for pid in FRESH_V61:
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [gen] {pid[:36]:<38} exists", flush=True)
                continue
            prob = _prob(pid)
            t0 = time.time()
            ans, meta = draft_with_machine_repairs(pid, prob, gw_key)
            dst.write_text(
                json.dumps({"problem_id": pid,
                            "a1_source": "SYS_A1_INT_V61/r24_feas_bind_v61",
                            "question_type": prob.get("question_type"),
                            "a1_answer": ans, "meta": meta,
                            "generated_at": now},
                           indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [gen] {pid[:36]:<38} repairs={meta['repairs']} "
                  f"residual={list(meta['residual_findings']) or 'CLEAN'} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        # ---------- phase 2: judge (canonical) ---------------------------
        prior = {}
        if FULL_PARTIAL.exists():
            for r in json.loads(FULL_PARTIAL.read_text(encoding="utf-8")):
                prior[r["problem_id"]] = r
        results = []
        for pid in ALL:
            if pid in prior:
                results.append(prior[pid])
                print(f"  [{pid[:32]:<34}] resumed", flush=True)
                continue
            if pid in RIDE_R11_PRED:
                row = dict(R11ROWS[pid])
                row["ride"] = {
                    "row_source": "battery_a1w_r11.json",
                    "byte_source": f"eval/pairs/r11_a1w_r1/{pid}.json",
                    "a1_answer_sha256_16": _sha(
                        json.loads((R11_DIR / f"{pid}.json").read_text(
                            encoding="utf-8"))["a1_answer"]),
                    "rule": "byte-identical pair rides its committed "
                            "judged row (AM19 sec.2 determinism)"}
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
            row = {"problem_id": pid,
                   "a1_arm": "SYS_A1_INT_V61_CONSTRAINT_BIND",
                   "question_type": prob.get("question_type"),
                   "question_type_gate":
                       rec["meta"]["attempts"][0]["type_gate"],
                   "baseline_source": b_src,
                   "byte_provenance": {
                       "byte_source":
                           f"eval/pairs/r24_feas_bind_v61/{pid}.json",
                       "a1_answer_sha256_16": _sha(a1),
                       "generation": "single draft under SYS_A1_INT_V61 "
                                     "(V6 bind + constraint awareness, "
                                     "F36) + neutral typed repairs; no "
                                     "selection"},
                   "judge": list(JUDGE), "draws": draws,
                   "majority_prefer": dec["majority_prefer"],
                   "median_axes": med}
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
                        "SYS_A1_INT_V61")]
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
        # ---------- phase 4: summaries + ablation + constraint fit --------
        iv = [r for r in results
              if str(r.get("question_type", "")).startswith("intervention")]
        tc = [r for r in results
              if (r.get("question_type_gate") or {}).get("verdict")
              == "MATCH"]
        s_tc = summarize(tc, "type-MATCH pairs only (primary form)")
        s_iv = summarize(iv, "INTERVENTION rows (the changed arm)")
        iv_r20 = summarize(
            [r for r in R20ROWS.values()
             if str(r.get("question_type", "")).startswith("intervention")],
            "r20 incumbent single-draw intervention rows")
        r23 = json.loads(R23_REC.read_text(encoding="utf-8"))
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
            encoding="utf-8"))["meta"] for p in FRESH_V61}
        repairs_total = sum(m["repairs"] for m in gen_meta.values())
        residual_pairs = sum(1 for m in gen_meta.values()
                             if m["residual_findings"])
        constraint_residual = sum(
            1 for m in gen_meta.values()
            if any(k.startswith("CONSTRAINT") or
                   k.startswith("ALLOWED") for k in m["residual_findings"]))
        record = {
            "record": "BATTERY_INT_V61_CONSTRAINT_BIND_R24/1.0.0 — V6 "
                      "ROUND 2 (Art. 20 clock 2/2) + the F36 "
                      "constraint-fit fix",
            "at": now,
            "claim": {"work_id": "r24-v61-constraint-bind",
                      "claim_id": "c-0014", "executor": "builder-r20s1",
                      "verifier": "peer session INVITED — recomputes "
                                  "from committed bytes (Art. 13), "
                                  "never re-runs"},
            "pre_registration": {
                "commit": "driver + contract + claim pushed BEFORE any "
                          "LLM call (git history order)",
                "byte_map": {"ride_r11_predictor": RIDE_R11_PRED,
                             "fresh_v61": FRESH_V61},
                "lever": "UNCHANGED in kind (contract-level bind at "
                         "mechanism choice — the V6 arm, round 2/2); "
                         "strengthened with constraint-awareness: "
                         "allowed-measures enumerations + hard "
                         "exclusions read from the problem's own "
                         "constraint text (the F36 fix, AM24 D2)",
                "acceptance_verbatim": "feasibility |gap| <= 0.25 AND "
                                       "novelty delta >= 0.5 on >= 30 "
                                       "pairs, and the ablation beats "
                                       "the incumbent (CI excludes it)",
                "arithmetic_disclosure": "rides floor 14/30 ~= 0.467 "
                                         "(pre-registered, unchanged)"},
            "judge": {"route": list(JUDGE), "k": K, "pace_s": PACE_S,
                      "transport_ladder": True},
            "generation_record": [
                {"problem_id": p, "repairs": gen_meta[p]["repairs"],
                 "residual_findings":
                     gen_meta[p]["residual_findings"] or "CLEAN"}
                for p in FRESH_V61],
            "bind_summary": {"repairs_total": repairs_total,
                             "pairs_with_residual_findings":
                                 residual_pairs,
                             "pairs_with_constraint_residual":
                                 constraint_residual},
            "ladder_stats": ladder_stats,
            "results": results,
            "summary_type_credited": s_tc,
            "summary_intervention_rows": s_iv,
            "art20_ablation": {
                "arm_under_test": "SYS_A1_INT_V61 (V6 bind + constraint "
                                  "awareness) — V6 arm ROUND 2/2",
                "incumbent": "SYS_A1_INT_V4 single-draw (the r20 bytes)",
                "metric": "intervention-subset type-credited feasibility "
                          "|gap|",
                "incumbent_intervention_fgap_r20":
                    iv_r20.get("feasibility_abs_gap_mean"),
                "v6_round1_intervention_fgap_r23":
                    r23["art20_ablation"][
                        "v6_bind_intervention_fgap_this"],
                "v61_round2_intervention_fgap_this":
                    s_iv.get("feasibility_abs_gap_mean"),
                "incumbent_ndelta_r20": iv_r20.get("novelty_delta_mean"),
                "v61_ndelta_this": s_iv.get("novelty_delta_mean"),
                "round_2_rule": "if not beating the incumbent on the "
                                "primary metric, the contract-bind "
                                "lever RETIRES at 2 (Art. 20) — no "
                                "round 3 under this lever kind",
                "typed_note": "constraint-fit (F36) is measured as a "
                              "typed deterministic proxy here "
                              "(zero-violation rate); the AUTHORITATIVE "
                              "read is the auditor's, on holdout v3"},
        }
        FULL_OUT.write_text(json.dumps(record, indent=1, default=str)
                            + "\n", encoding="utf-8")
        for lbl, s in (("TYPE-CREDITED", s_tc),
                       ("INTERVENTION (ABLATION)", s_iv)):
            print(f"[r24v61] {lbl}: n={s.get('n_valid')} | nov Δ "
                  f"{s.get('novelty_delta_mean')} CI "
                  f"{s.get('novelty_ci95')} | feas |gap| "
                  f"{s.get('feasibility_abs_gap_mean')} CI "
                  f"{s.get('feasibility_ci95')} | prefer "
                  f"{s.get('prefer_tally')}", flush=True)
        ab = record["art20_ablation"]
        print(f"[r24v61] ablation: incumbent {ab['incumbent_intervention_fgap_r20']}"
              f" | V6r1 {ab['v6_round1_intervention_fgap_r23']} | V6.1r2 "
              f"{ab['v61_round2_intervention_fgap_this']} | nd "
              f"{ab['v61_ndelta_this']} vs {ab['incumbent_ndelta_r20']}",
              flush=True)
        print(f"[r24v61] constraint-fit proxy: {constraint_residual}/18 "
              f"pairs with constraint residuals | repairs={repairs_total}",
              flush=True)
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

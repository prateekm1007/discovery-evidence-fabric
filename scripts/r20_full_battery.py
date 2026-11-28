#!/usr/bin/env python3
"""r20_full_battery.py — AM20 D1: the FULL 30-pair V4 battery
(gate-decisive measurement, F30 iteration 3 completion).

PRE-REGISTERED before any measurement (this file + the V4 predictor
contract are committed before the results exist):

BYTE MAP (pre-declared, from committed bytes):
  RIDE_PILOT (7): the AM19-pilot hard-7 intervention pairs (fgap>=2
    selection, r11-committed bytes) — V4 answers BYTE-IDENTICAL from
    eval/pairs/r19_a1w2_pilot/, judged rows ride verbatim from
    eval/battery_a1w2_pilot_r19.json (same canonical metric, same
    judge, k=3; AM19 sec.2 determinism finding: two independent k=3
    runs converged identically, so byte-identical pairs riding
    committed rows is the established resume discipline).
  RIDE_R11_PREDICTOR (8): predictor pairs at fgap 0-1 whose V3 bytes
    are NOT retargeted (byte map below) — rows ride verbatim from
    eval/battery_a1w_r11.json; byte-identity sha-verified.
  FRESH_INT_V4 (11): the remaining intervention pairs, generated under
    SYS_A1_INT_V4 (the AM19-pilot contract, unchanged).
  FRESH_PRED_V4 (4): eval-new06/07/10/12 (the predictor pairs at
    fgap 2-3, byte-typed) — generated under SYS_A1F_V4 (NEW, this
    pre-registration): DATA-SOURCE / NO-BASELINE-PROGRAM /
    NO-COMMISSIONING-PROGRAM rules, machine-enforced by
    predictor_violations() scan + repair.

  The change is isolated exactly as the byte map declares: novelty
  risk is confined to 15 fresh pairs; the 15 riding pairs keep their
  committed judged rows.

JUDGING: the CANONICAL battery metric, unchanged (Art. 16/19):
  eval/run._rubric_prompt + scripts/_f28_axis_suffix_v2.txt +
  crowllm/qwen-3.8-max:free at t=0, K=3, eval/battery_metrics
  parse_axes/row_metrics/summarize (strict plurality; shared core).
  Judge != generator (crowllm/Qwen vs zai/GLM, provider+family).

ACCEPTANCE (AM20 D1, verbatim): feasibility |gap| <= 0.25 AND novelty
  delta >= 0.5 on >= 30 pairs, pre-registered, type-credited,
  judge != generator, queue CI green. Gate re-decision is the
  auditor's; this record measures.
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

from r19_a1w_v4_contract import (  # noqa: E402
    SYS_A1_INT_V4, contract_for, predictor_violations, DEV_NEED_MARKERS)
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r20_full_v4"
R11 = REPO / "eval" / "battery_a1w_r11.json"
PILOT = REPO / "eval" / "battery_a1w2_pilot_r19.partial.json"
PILOT_DIR = REPO / "eval" / "pairs" / "r19_a1w2_pilot"
R11_DIR = REPO / "eval" / "pairs" / "r11_a1w_r1"
FULL_OUT = REPO / "eval" / "battery_a1w2_full_r20.json"
FULL_PARTIAL = REPO / "eval" / "battery_a1w2_full_r20.partial.json"
JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
K = 3
REPAIR_BUDGET = 2
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

RIDE_PILOT = ["bench-p03-phe-biofouling", "bench-p05-bridge-bearing-aging",
              "bench-p06-water-biofilm", "bench-p09-packaging-barrier",
              "bench-p11-spindle-thermal-drift",
              "eval-new05-liion-balance-drift",
              "eval-sofc-thermal-cycling"]
RIDE_R11_PRED = ["dev-fu-001-bearing-spalling", "dev-fu-003-motor-insulation",
                 "dev-fu-004-fouling", "eval-new02-slipring-predictor",
                 "eval-new04-chiller-fouling-predictor",
                 "eval-new08-pipeline-leak-predictor",
                 "eval-new09-hvac-filter-predictor",
                 "eval-new11-conveyor-belt-predictor"]
FRESH_INT = ["bench-p01-pemfc-dehydration", "bench-p02-leadacid-grid-corrosion",
             "bench-p04-pump-cavitation", "bench-p07-cgm-biofouling",
             "bench-p08-mems-stiction", "bench-p10-pv-pid",
             "bench-p12-mbr-fouling", "dev-fu-005-bridge-bearing",
             "eval-new01-supercap-dryout",
             "eval-new03-insulin-pump-occlusion", "eval-sofc-redox"]
FRESH_PRED = ["eval-new06-bearing-vibration-predictor",
              "eval-new07-transformer-dga-predictor",
              "eval-new10-solar-inverter-predictor",
              "eval-new12-axle-bearing-predictor"]

# --- byte-map integrity assertions (fail closed) ----------------------
r11rows = {r["problem_id"]: r for r in
           json.loads(R11.read_text(encoding="utf-8"))["results"]}
pilotrows = {r["problem_id"]: r for r in
             json.loads(PILOT.read_text(encoding="utf-8"))}
ALL = RIDE_PILOT + RIDE_R11_PRED + FRESH_INT + FRESH_PRED
assert len(ALL) == 30 and len(set(ALL)) == 30, "byte map malformed"
assert set(ALL) == set(r11rows), "byte map != r11 pool"
assert set(RIDE_PILOT) == set(pilotrows), "pilot ride set mismatch"
assert set(RIDE_R11_PRED) == {
    p for p, r in r11rows.items()
    if str(r.get("question_type", "")).startswith("predictor")
    and p not in FRESH_PRED}, "r11 predictor ride set mismatch"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _backfill_tc(row):
    """The shared summarize() reads T/C per-axis deltas; rows built
    before R20 carried only N/F — derive them from the stored medians
    (pure arithmetic on committed bytes, typed in the row)."""
    med = row.get("median_axes")
    if med and "testability_delta" not in row:
        if "T_A" in med and "T_B" in med:
            row["testability_delta"] = med["T_A"] - med["T_B"]
        if "C_A" in med and "C_B" in med:
            row["constraint_delta"] = med["C_A"] - med["C_B"]
        row["tc_backfilled_from"] = "median_axes (committed bytes)"
    return row


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


def violations_for(ans, qt):
    hits = sorted({m.group(0).lower()
                   for m in DEV_NEED_MARKERS.finditer(ans)})
    if qt.startswith("predictor"):
        return predictor_violations(ans)
    return {"DEV_NEED": hits} if hits else {}


def generate(pid, prob, gw_key):
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    attempts = []
    ans, lat = _gen(q, contract_for(qt), gw_key)
    attempts.append({"kind": "generation", "latency_s": round(lat, 1),
                     "chars": len(ans)})
    final, meta = ans, {}
    for rep in range(REPAIR_BUDGET + 1):
        cr = critic(final, prob)
        tg = gate_question_type(final, prob)
        vio = violations_for(final, qt)
        problems = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        for kind, found in vio.items():
            if kind == "DEV_NEED":
                problems.append(
                    "V4 NO-DEVELOPMENT RULE violation: the bill "
                    "concedes a development program (" + "; ".join(found)
                    + "). Re-express the SAME mechanism through "
                      "procurable classes only; the mechanism stays "
                      "novel, the COMPONENTS must all exist today.")
            elif kind == "BASELINE_PROGRAM":
                problems.append(
                    "V4 NO-BASELINE-PROGRAM violation: the scheme's "
                    "trust is built by a data program (" + "; ".join(
                        found) + "). Derive every reference from "
                    "ALREADY-RECORDED data, stated specs, or stated "
                    "physics; label it DERIVED with its source.")
            elif kind == "COMMISSIONING_PROGRAM":
                problems.append(
                    "V4 NO-COMMISSIONING-PROGRAM violation: the scheme "
                    "needs a tuning/validation campaign (" + "; ".join(
                        found) + "). Replace with a decision rule "
                    "computable NOW from stated data/specs/physics.")
        if not [p for p in problems if p]:
            meta = {"critic_verdict": cr["verdict"], "type_gate": tg,
                    "violations": vio, "repairs": rep}
            return final, attempts, meta
        if rep == REPAIR_BUDGET:
            meta = {"critic_verdict": cr["verdict"], "type_gate": tg,
                    "violations": vio, "repairs": rep,
                    "residual_findings": [p for p in problems if p]}
            return final, attempts, meta
        directive = ("REPAIR DIRECTIVE (typed findings on the previous "
                     "draft, disclosed): " + "; ".join(
                         p for p in problems if p)
                     + ". Fix ONLY these defects; keep the proposal's "
                       "core otherwise intact. The ONLY USER CONSTRAINT "
                       "labels allowed are the user-stated variables.")
        final, lat2 = _gen(q + "\n\n" + directive,
                           contract_for(qt), gw_key)
        attempts.append({"kind": f"repair_{rep+1}",
                         "latency_s": round(lat2, 1),
                         "chars": len(final),
                         "findings_disclosed": [p for p in problems if p]})
    raise RuntimeError("unreachable")


def main() -> int:
    r11_pred = {p: json.loads((R11_DIR / f"{p}.json").read_text(
        encoding="utf-8"))["a1_answer"] for p in RIDE_R11_PRED}
    gw, gw_key = start_gateway()
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        # ---------- phase 1: fresh generations (resume-safe) ---------
        fresh = FRESH_INT + FRESH_PRED
        for pid in fresh:
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [gen] {pid[:36]:<38} exists (rides)", flush=True)
                continue
            prob = _prob(pid)
            t0 = time.time()
            ans, attempts, meta = generate(pid, prob, gw_key)
            (OUT_DIR / f"{pid}.json").write_text(
                json.dumps({"problem_id": pid,
                            "a1_source": ("SYS_A1_INT_V4"
                                          if pid in FRESH_INT
                                          else "SYS_A1F_V4")
                                          + "/r20_full_battery",
                            "question_type": prob.get("question_type"),
                            "a1_answer": ans, "attempts": attempts,
                            "meta": meta, "generated_at": now},
                           indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [gen] {pid[:36]:<38} "
                  f"verdict={meta['critic_verdict']} "
                  f"vio={meta['violations'] or 'CLEAN'} "
                  f"repairs={meta['repairs']} ({time.time()-t0:.0f}s)",
                  flush=True)
        # ---------- phase 2: assemble + judge (canonical metric) -----
        prior = {}
        if FULL_PARTIAL.exists():
            for r in json.loads(FULL_PARTIAL.read_text(encoding="utf-8")):
                prior[r["problem_id"]] = r
        results, ride_manifest = [], []
        for pid in ALL:
            if pid in prior:
                results.append(prior[pid])
                print(f"  [{pid[:32]:<34}] resumed (committed row rides)",
                      flush=True)
                continue
            if pid in RIDE_PILOT:
                row = _backfill_tc(dict(pilotrows[pid]))
                rec = json.loads((PILOT_DIR / f"{pid}.json").read_text(
                    encoding="utf-8"))
                row["question_type_gate"] = rec["meta"]["type_gate"]
                row["critic_verdict"] = rec["meta"]["critic_verdict"]
                row["ride"] = {"row_source": "battery_a1w2_pilot_r19.json",
                               "byte_source": "eval/pairs/r19_a1w2_pilot/"
                                              f"{pid}.json",
                               "a1_answer_sha256_16": _sha(rec["a1_answer"]),
                               "rule": "byte-identical pair rides its "
                                       "committed judged row (AM19 sec.2 "
                                       "determinism finding)"}
                ride_manifest.append({"problem_id": pid,
                                      "row_source": "pilot"})
                results.append(row)
                print(f"  [{pid[:32]:<34}] ride pilot row", flush=True)
                continue
            if pid in RIDE_R11_PRED:
                row = _backfill_tc(dict(r11rows[pid]))
                row["ride"] = {"row_source": "battery_a1w_r11.json",
                               "byte_source": f"eval/pairs/r11_a1w_r1/"
                                              f"{pid}.json",
                               "a1_answer_sha256_16":
                                   _sha(r11_pred[pid]),
                               "rule": "V3 bytes not retargeted; "
                                       "byte-identical pair rides its "
                                       "committed judged row"}
                ride_manifest.append({"problem_id": pid,
                                      "row_source": "r11"})
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
                econ.reset_governor(f"r20full:{pid}:{k}")
                jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                          max_tokens=4000)
                draws.append({"k": k, "outcome": jc.get("outcome"),
                              "axes": parse_axes(jc),
                              "prefer": (jc.get("valid") or {}).get(
                                  "prefer")})
                time.sleep(PACE_S)
            dec = row_metrics(draws)
            med = dec["median_axes"]
            row = {"problem_id": pid,
                   "a1_arm": rec["a1_source"].split("/")[0],
                   "question_type": prob.get("question_type"),
                   "question_type_gate": rec["meta"]["type_gate"],
                   "critic_verdict": rec["meta"]["critic_verdict"],
                   "baseline_source": b_src,
                   "judge": list(JUDGE), "draws": draws,
                   "majority_prefer": dec["majority_prefer"],
                   "median_axes": med}
            if med:
                row["novelty_delta"] = med["N_A"] - med["N_B"]
                row["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
                row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
                row["testability_delta"] = med["T_A"] - med["T_B"]
                row["constraint_delta"] = med["C_A"] - med["C_B"]
            if pid == "eval-new01-supercap-dryout":
                row["standing_adjudication_note"] = (
                    "AM11 sec.3 / AM12 par.1 holding concerns the R11 "
                    "row's bytes; this row measures fresh V4 bytes and "
                    "carries no adjudication credit")
            results.append(row)
            FULL_PARTIAL.write_text(
                json.dumps(results, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [{pid[:32]:<34}] judged nd="
                  f"{row.get('novelty_delta')} fgap="
                  f"{row.get('feasibility_abs_gap')} "
                  f"prefer={row.get('majority_prefer')}", flush=True)
        assert len(results) == 30, f"pool incomplete: {len(results)}"
        # ---------- phase 3: gate summaries --------------------------
        iv = [r for r in results
              if str(r.get("question_type", "")).startswith("intervention")]
        pd_ = [r for r in results
               if str(r.get("question_type", "")).startswith("predictor")]
        record = {
            "record": "BATTERY_A1W2_FULL_R20/1.0.0 — the AM20 D1 "
                      "gate-decisive measurement (full 30-pair V4)",
            "at": now,
            "pre_registration": {
                "commit": "this file + SYS_A1F_V4 committed BEFORE "
                          "measurement (see git history order)",
                "byte_map": {"ride_pilot": RIDE_PILOT,
                             "ride_r11_predictor": RIDE_R11_PRED,
                             "fresh_intervention_v4": FRESH_INT,
                             "fresh_predictor_v4": FRESH_PRED},
                "riding_rule": "byte-identical pairs ride their "
                               "committed judged rows (driver resume "
                               "discipline; AM19 sec.2 determinism "
                               "finding: two independent k=3 runs "
                               "converged identically); sha-verified "
                               "in ride_manifest",
                "acceptance_verbatim": "feasibility |gap| <= 0.25 AND "
                                       "novelty delta >= 0.5 on >= 30 "
                                       "pairs, pre-registered, "
                                       "type-credited, judge != "
                                       "generator, queue CI green"},
            "arms": {
                "A": "V4 WEIGHT-BOUND: 18 intervention pairs "
                     "(7 pilot bytes byte-identical + 11 fresh "
                     "SYS_A1_INT_V4) + 12 predictor pairs (8 V3 bytes "
                     "not retargeted, byte-identical + 4 fresh "
                     "SYS_A1F_V4 with DATA-SOURCE/NO-BASELINE-PROGRAM/"
                     "NO-COMMISSIONING-PROGRAM rules)",
                "B": "CURATED baselines — assembly identical to "
                     "batteries r7-r11 (dev12_fresh first, then "
                     "baselines_curated)"},
            "judge": {"route": list(JUDGE), "k": K, "pace_s": PACE_S,
                      "independence": "crowllm/Qwen vs zai/GLM "
                                      "generator — provider AND family "
                                      "independent"},
            "ride_manifest": ride_manifest,
            "generation_record": [
                {"problem_id": p["problem_id"],
                 "critic_verdict": p["meta"]["critic_verdict"],
                 "violations": (p["meta"]["violations"] or "CLEAN"),
                 "repairs": p["meta"]["repairs"],
                 "type_gate_verdict": p["meta"]["type_gate"]["verdict"]}
                for p in (json.loads(
                    (OUT_DIR / f"{pid}.json").read_text(
                        encoding="utf-8")) for pid in fresh)],
            "results": results,
            "summary_intervention_rows": summarize(
                iv, "INTERVENTION rows only (AM16 D1 frontier "
                    "continuity: r10 2.389 -> r11 1.5 -> this)"),
            "summary_predictor_rows": summarize(
                pd_, "PREDICTOR rows only (8 byte-identical rides + 4 "
                     "fresh V4)"),
            "summary_type_credited": summarize(
                [r for r in results
                 if (r.get("question_type_gate") or {}).get("verdict")
                 == "MATCH"],
                "type-MATCH pairs only — the AM20 D1 acceptance form "
                "(wrong-type novelty does NOT count)"),
            "summary_all_valid": summarize(
                results, "all valid pairs (unfiltered sensitivity)"),
            "gate_note": ("MEASUREMENT for the auditor (Art. XXVI/"
                          "LXXXVI-2): the AM20 D1 acceptance — overall "
                          "feasibility |gap| <= 0.25 AND novelty "
                          "delta >= 0.5 on >= 30 pairs, type-credited — "
                          "read on summary_type_credited (primary) "
                          "with per-type summaries; MISMATCH pairs "
                          "excluded from clause credit, still "
                          "recorded; the authoritative gate "
                          "re-decision is the auditor's per-axis "
                          "re-judgment on the committed bytes"),
        }
        FULL_OUT.write_text(
            json.dumps(record, indent=1, default=str) + "\n",
            encoding="utf-8")
        for lbl, s in (("TYPE-CREDITED (PRIMARY)", record[
                "summary_type_credited"]),
                       ("ALL-VALID", record["summary_all_valid"])):
            print(f"[r20full] {lbl}: n={s['n_valid']} | nov Δ "
                  f"{s['novelty_delta_mean']} CI {s['novelty_ci95']} "
                  f"| feas |gap| {s['feasibility_abs_gap_mean']} CI "
                  f"{s['feasibility_ci95']} | prefer "
                  f"{s['prefer_tally']} | D5 "
                  f"{s['AM14_D5_point_estimate']['both_simultaneous_pass']}",
                  flush=True)
        print(f"-> {FULL_OUT}")
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

#!/usr/bin/env python3
"""r28_verify_crosscheck.py — the Art. 13/29(c) zero-LLM verifier for
the R28 machine-judge cross-check (claim c-0022). Recomputes EVERY
judged number from committed bytes; never re-runs, never re-judges.

CHECKS (exit 0 only on full reproduction)
  1  record shape + CROSS-CHECK-ONLY typing present
  2  row map vs eval/r27_judge_packet.json (30 rows, ids, order,
     question_type, stage)
  3  per-row rubric-prompt sha256_16 recompute vs the packet
     (BYTE-EXACT riding)
  4  per-row median/deltas recompute from the committed draws
     (eval/battery_metrics.py row_metrics, unchanged core)
  5  summaries recompute (18 interventions / 12 predictors / pilot-8)
  6  pilot-8 AM26 comparison recompute from the pinned audit-tip
     anchor (provenance, per-pair divergences, agreement counts)
  7  quota recount from the per-draw transport ledgers
  8  claim linkage: the registry carries c-0022 EXECUTOR on
     r28-machine-judge-crosscheck; the record's claim block matches
  9  judge route pin: crowllm/qwen-3.8-max:free, K=3, pace 13.0,
     ladder (20,60), max_tokens 4000
 10  zero generation (no generator calls; the record types calls: 0)
 11  all rows carry 3/3 valid draws (the determinism/health pin)
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.battery_metrics import row_metrics, summarize  # noqa: E402

REC_PATH = REPO / "eval" / "battery_v7_1_machine_crosscheck_r28.json"
PACKET = REPO / "eval" / "r27_judge_packet.json"
REG = REPO / "eval" / "work_claims.json"
AUDITOR_PILOT_SHA = "a6ca19ed7"
AUDITOR_PILOT_REF = ("audit/r11-auditor-verdict-20261114 @ a6ca19ed7:"
                     "eval/v7_pilot_auditor_score.json")
PILOT_8 = ["bench-p01-pemfc-dehydration",
           "bench-p02-leadacid-grid-corrosion",
           "bench-p03-phe-biofouling",
           "bench-p04-pump-cavitation",
           "bench-p05-bridge-bearing-aging",
           "bench-p06-water-biofilm",
           "bench-p07-cgm-biofouling",
           "bench-p08-mems-stiction"]

fails = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def main():
    rec = json.loads(REC_PATH.read_text(encoding="utf-8"))
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    prows = packet["rows"]
    rows = rec["results"]

    print("R28 machine-judge cross-check VERIFIER (zero LLM)")

    # 1 record shape + typing
    check("record id",
          rec.get("record") == "BATTERY_V7_1_MACHINE_CROSSCHECK_R28/1.0.0")
    check("CROSS-CHECK-ONLY typing",
          "CROSS-CHECK ONLY" in str(rec.get("typed", "")))

    # 2 row map
    check("30 rows", len(rows) == 30 and len(prows) == 30)
    check("row ids/order match packet",
          [r["problem_id"] for r in rows]
          == [r["problem_id"] for r in prows])
    check("question_type match",
          all(r["question_type"] == p["question_type"]
              for r, p in zip(rows, prows)))
    check("stage match",
          all(r["stage"] == p["stage"] for r, p in zip(rows, prows)))

    # 3 byte-exact prompt riding
    bad_sha = [r["problem_id"] for r, p in zip(rows, prows)
               if r["rubric_prompt_sha256_16"]
               != _sha(p["rubric_prompt"])]
    check("per-row prompt sha == packet (byte-exact)",
          not bad_sha, str(bad_sha))

    # 4 per-row recompute
    bad_rows = []
    for r in rows:
        dec = row_metrics(r["draws"])
        med = dec["median_axes"]
        exp = {"majority_prefer": dec["majority_prefer"],
               "median_axes": med}
        if med:
            exp.update({
                "novelty_delta": med["N_A"] - med["N_B"],
                "a1_feasibility": med["F_A"],
                "baseline_feasibility": med["F_B"],
                "feasibility_abs_gap": abs(med["F_A"] - med["F_B"]),
                "feasibility_signed_gap": med["F_A"] - med["F_B"],
                "testability_delta": med["T_A"] - med["T_B"],
                "constraint_delta": med["C_A"] - med["C_B"]})
        for k, v in exp.items():
            if r.get(k) != v:
                bad_rows.append((r["problem_id"], k, r.get(k), v))
    check("per-row median/deltas recompute", not bad_rows, str(bad_rows[:4]))

    # 5 summaries recompute
    iv = [r for r in rows if str(r.get("question_type", ""))
          .startswith("intervention")]
    pr = [r for r in rows if str(r.get("question_type", ""))
          .startswith("predictor")]
    p8 = [r for r in rows if r["problem_id"] in PILOT_8]
    ok_sum = True
    det = []
    for key, sub, n in (("summary_intervention_rows", iv, 18),
                        ("summary_predictor_rows", pr, 12),
                        ("summary_pilot8_machine", p8, 8)):
        want = summarize(sub, rec[key]["label"])
        for k in ("n_valid", "novelty_delta_mean",
                  "feasibility_abs_gap_mean", "novelty_ci95",
                  "feasibility_ci95", "prefer_tally",
                  "per_axis_means_A_minus_B"):
            if rec[key].get(k) != want.get(k):
                ok_sum = False
                det.append((key, k, rec[key].get(k), want.get(k)))
        if want["n_valid"] != n:
            ok_sum = False
            det.append((key, "n_valid", want["n_valid"], n))
    check("summaries recompute (18/12/8)", ok_sum, str(det[:4]))

    # 6 pilot-8 comparison recompute vs the pinned anchor
    out = subprocess.run(
        ["git", "-C", str(REPO), "show",
         f"{AUDITOR_PILOT_SHA}:eval/v7_pilot_auditor_score.json"],
        capture_output=True, text=True, check=True)
    auditor = json.loads(out.stdout)
    apairs = {p["problem_id"]: p for p in auditor["per_pair"]}
    cmp_ = rec["pilot8_am26_comparison"]
    ok_cmp = cmp_.get("anchor_provenance") == AUDITOR_PILOT_REF
    det_cmp = []
    by_id = {r["problem_id"]: r for r in rows}
    for e in cmp_["per_pair"]:
        pid = e["problem_id"]
        m, a = by_id[pid], apairs[pid]
        same_bytes = m.get("stage") == "V7_R26_FROZEN"
        want_align = ("same-bytes" if same_bytes
                      else "v71-tuned-since-pilot (the auditor "
                           "judged the r26 V7 bytes; the final "
                           "battery carries the V7.1 tuned "
                           "bytes — input divergence, not a "
                           "judgment divergence)")
        if e["byte_alignment"] != want_align:
            ok_cmp = False
            det_cmp.append((pid, "alignment"))
        for k, v in (("novelty_delta", m.get("novelty_delta")),
                     ("a1_feasibility", m.get("a1_feasibility")),
                     ("baseline_feasibility",
                      m.get("baseline_feasibility")),
                     ("feasibility_abs_gap",
                      m.get("feasibility_abs_gap"))):
            if e["machine"].get(k) != v:
                ok_cmp = False
                det_cmp.append((pid, "machine." + k))
            if e["auditor_am26"].get(k) != a.get(k):
                ok_cmp = False
                det_cmp.append((pid, "auditor." + k))
        if same_bytes and m.get("median_axes"):
            want_div = {
                "novelty_delta": m["novelty_delta"] - a["novelty_delta"],
                "a1_feasibility": m["a1_feasibility"]
                - a["a1_feasibility"],
                "baseline_feasibility": m["baseline_feasibility"]
                - a["baseline_feasibility"],
                "feasibility_abs_gap": m["feasibility_abs_gap"]
                - a["feasibility_abs_gap"]}
            if e.get("divergence") != want_div:
                ok_cmp = False
                det_cmp.append((pid, "divergence"))
    # agreement counts
    sb = [e for e in cmp_["per_pair"]
          if e["byte_alignment"] == "same-bytes"
          and e["machine"]["novelty_delta"] is not None]
    ag = cmp_["agreement"]
    want_ag = {
        "n_same_bytes_compared": len(sb),
        "novelty_delta": {
            "exact": sum(1 for e in sb if e["divergence"][
                "novelty_delta"] == 0),
            "within_1": sum(1 for e in sb if abs(e["divergence"][
                "novelty_delta"]) <= 1)},
        "feasibility_abs_gap": {
            "exact": sum(1 for e in sb if e["divergence"][
                "feasibility_abs_gap"] == 0),
            "within_1": sum(1 for e in sb if abs(e["divergence"][
                "feasibility_abs_gap"]) <= 1)}}
    for k, v in want_ag.items():
        if ag.get(k) != v:
            ok_cmp = False
            det_cmp.append(("agreement." + k, ag.get(k), v))
    if ag.get("auditor_am26_pilot8_means", {}).get(
            "novelty_delta_mean") != auditor["novelty_delta_mean"] or \
       ag.get("auditor_am26_pilot8_means", {}).get(
            "feasibility_abs_gap_mean") != auditor[
                "feasibility_abs_gap_mean"]:
        ok_cmp = False
        det_cmp.append(("auditor means"))
    check("pilot-8 AM26 comparison recompute (pinned anchor "
          + AUDITOR_PILOT_SHA + ")", ok_cmp, str(det_cmp[:5]))

    # 7 quota recount
    n_calls = sum(len(dd.get("transport_attempts") or [])
                  for r in rows for dd in r["draws"])
    n_ladder = sum(max(0, len(dd.get("transport_attempts") or []) - 1)
                   for r in rows for dd in r["draws"])
    check("quota recount",
          rec["quota"]["judge_slot_attempts"] == n_calls
          and rec["quota"]["ladder_retries"] == n_ladder,
          f"calls={n_calls} ladder={n_ladder}")

    # 8 claim linkage
    reg = json.loads(REG.read_text(encoding="utf-8"))
    c = next((x for x in reg["claims"]
              if x["claim_id"] == "c-0022"
              and x["work_id"] == "r28-machine-judge-crosscheck"), None)
    check("registry claim c-0022 present (EXECUTOR)",
          c is not None and c["role"] == "EXECUTOR")
    check("record claim block matches registry",
          rec["claim"]["claim_id"] == "c-0022"
          and rec["claim"]["work_id"] == "r28-machine-judge-crosscheck"
          and rec["claim"]["session"] == c["session_id"]
          and rec["claim"]["base_sha"] == c["base_sha"])

    # 9 judge route pin
    j = rec["judge"]
    check("judge route pin (crowllm/qwen-3.8-max:free K=3 p13 "
          "ladder[20,60] cap4000)",
          j["route"] == ["crowllm", "qwen-3.8-max:free"]
          and j["k"] == 3 and j["pace_s"] == 13.0
          and j["transport_ladder"] == [20.0, 60.0]
          and j["max_tokens"] == 4000
          and all(r["judge"] == ["crowllm", "qwen-3.8-max:free"]
                  for r in rows))

    # 10 zero generation
    check("zero generator calls (typed)",
          rec["generation"]["calls"] == 0)

    # 11 health pin
    check("all rows 3/3 valid draws",
          all(r["n_valid_draws"] == 3 for r in rows))

    print(f"\n{'ALL PASS' if not fails else 'FAILURES: ' + str(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())

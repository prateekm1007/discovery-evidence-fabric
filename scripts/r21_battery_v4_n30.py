#!/usr/bin/env python3
"""r21_battery_v4_n30.py — AM21 D2: the gate-decisive 30-pair V4 battery
run under claim-before-work (Art. 29).

PRE-REGISTERED BEFORE ANY MEASUREMENT (this file + the Art. 29 registry
claims ride the same commit, pushed before any judge call exists):

WORK ITEM (Art. 29): claim c-0002 in eval/work_claims.json — work_id
"r21-v4-battery-n30", EXECUTOR builder-r20s2, kind "measurement",
filed BEFORE this run per Art. 29(b). VERIFIER: the peer session,
INVITED — it recomputes from these committed bytes (Art. 13) and NEVER
re-runs; it files a typed VERIFIER claim in eval/work_claims.json.

BYTE MAP (pre-declared; ZERO generation this round — every A-side
answer byte is already committed):
  PILOT_BYTES (7):  eval/pairs/r19_a1w2_pilot/<pid>.json — V4
    intervention bytes (judged rows exist in battery_a1w2_pilot_r19).
  R11_PRED_BYTES (8): eval/pairs/r11_a1w_r1/<pid>.json — V3 predictor
    bytes, not retargeted (judged rows in battery_a1w_r11).
  FRESH_V4_BYTES (15): eval/pairs/r20_full_v4/<pid>.json — 11
    SYS_A1_INT_V4 + 4 SYS_A1F_V4 (judged in battery_a1w2_full_r20).
  The 30 A-side bytes are IDENTICAL to the AM20 D1 battery's bytes;
  each is sha256-verified at run time against the ride shas the r20
  record committed (fail-closed on any mismatch). Generator draw
  variance is therefore held CONSTANT and the only lever under test is
  judge transport robustness — the typed next lever from BOTH R20
  sessions' converged finding.

WHAT IS NEW (typed; measurement infrastructure only — the CANONICAL
metric core is UNCHANGED, Art. 16/19):
  TRANSPORT LADDER: each draw slot (k=0,1,2) gets up to 3 attempts on
  any non-JUDGE_VALID outcome, with typed backoff (20s, 60s) between
  attempts; per-draw attempt counts are recorded. R20 measured 27/90
  transport failures (eval-new10 lost ALL draws -> n=29); the ladder's
  purpose is to recover those draws and satisfy the acceptance's
  ">= 30 pairs" clause. No change to rubric, suffix, judge identity,
  temperature, K, aggregation, or thresholds.

JUDGING (canonical, unchanged): eval/run._rubric_prompt +
scripts/_f28_axis_suffix_v2.txt + crowllm/qwen-3.8-max:free at t=0,
K=3, eval/battery_metrics parse_axes/row_metrics/summarize (strict
plurality; shared core). Judge != generator (crowllm/Qwen vs zai/GLM,
provider AND family).

ACCEPTANCE (AM21 D2, verbatim): feasibility |gap| <= 0.25 AND novelty
delta >= 0.5 on >= 30 pairs, pre-registered, type-credited, judge !=
generator, queue CI green; one EXECUTOR + one VERIFIER record. The
gate re-decision is the auditor's; this record measures.

TYPED EXPECTATION (disclosed, not invented): on draws that transport,
the judge is deterministic at t=0 (R17 sec.2 / R19 sec.2 findings), so
rows should reproduce their r20 medians unless a recovered draw
displaces a k=3 median. Transport recovery alone is NOT expected to
move feasibility to <= 0.25 (1.379 at n=29 in r20); this record
measures honestly whatever it measures.
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

from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402

R20_REC = REPO / "eval" / "battery_a1w2_full_r20.json"
PILOT_DIR = REPO / "eval" / "pairs" / "r19_a1w2_pilot"
R11_DIR = REPO / "eval" / "pairs" / "r11_a1w_r1"
V4_DIR = REPO / "eval" / "pairs" / "r20_full_v4"
OUT = REPO / "eval" / "battery_v4_n30_r21.json"
PARTIAL = REPO / "eval" / "battery_v4_n30_r21.partial.json"
JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
K = 3
LADDER_BACKOFF_S = (20.0, 60.0)
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

PILOT_BYTES = ["bench-p03-phe-biofouling", "bench-p05-bridge-bearing-aging",
               "bench-p06-water-biofilm", "bench-p09-packaging-barrier",
               "bench-p11-spindle-thermal-drift",
               "eval-new05-liion-balance-drift",
               "eval-sofc-thermal-cycling"]
R11_PRED_BYTES = ["dev-fu-001-bearing-spalling", "dev-fu-003-motor-insulation",
                  "dev-fu-004-fouling", "eval-new02-slipring-predictor",
                  "eval-new04-chiller-fouling-predictor",
                  "eval-new08-pipeline-leak-predictor",
                  "eval-new09-hvac-filter-predictor",
                  "eval-new11-conveyor-belt-predictor"]
FRESH_V4_BYTES = ["bench-p01-pemfc-dehydration",
                  "bench-p02-leadacid-grid-corrosion",
                  "bench-p04-pump-cavitation", "bench-p07-cgm-biofouling",
                  "bench-p08-mems-stiction", "bench-p10-pv-pid",
                  "bench-p12-mbr-fouling", "dev-fu-005-bridge-bearing",
                  "eval-new01-supercap-dryout",
                  "eval-new03-insulin-pump-occlusion", "eval-sofc-redox",
                  "eval-new06-bearing-vibration-predictor",
                  "eval-new07-transformer-dga-predictor",
                  "eval-new10-solar-inverter-predictor",
                  "eval-new12-axle-bearing-predictor"]
ALL = PILOT_BYTES + R11_PRED_BYTES + FRESH_V4_BYTES

# --- pre-registered byte-map assertions (fail closed, Art. 3) ---------
_r20 = json.loads(R20_REC.read_text(encoding="utf-8"))
_r20rows = {r["problem_id"]: r for r in _r20["results"]}
_bm = _r20["pre_registration"]["byte_map"]
assert len(ALL) == 30 and len(set(ALL)) == 30, "r21 byte map malformed"
assert set(ALL) == set(_r20rows), "r21 byte map != r20 pool"
assert set(PILOT_BYTES) == set(_bm["ride_pilot"]), "pilot byte set drifted"
assert set(R11_PRED_BYTES) == set(_bm["ride_r11_predictor"]), \
    "r11 predictor byte set drifted"
assert set(FRESH_V4_BYTES) == (set(_bm["fresh_intervention_v4"])
                               | set(_bm["fresh_predictor_v4"])), \
    "fresh V4 byte set drifted"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _atomic_write(path, text):
    """Chunked-execution discipline (Art. 18/29(d)): the run is resumed
    across foreground chunks, so the partial record is written
    atomically — a kill mid-write can never corrupt resume state."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def a_bytes_for(pid):
    """The committed A-side answer bytes, resolved by byte map, sha'd,
    and cross-checked against the ride sha the r20 record committed."""
    if pid in PILOT_BYTES:
        src, path = "PILOT_BYTES", PILOT_DIR / f"{pid}.json"
    elif pid in R11_PRED_BYTES:
        src, path = "R11_PRED_BYTES", R11_DIR / f"{pid}.json"
    else:
        src, path = "FRESH_V4_BYTES", V4_DIR / f"{pid}.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    ans = str(rec["a1_answer"])
    sha = _sha(ans)
    r20ride = (_r20rows[pid].get("ride") or {}).get("a1_answer_sha256_16")
    assert (not r20ride) or (r20ride == sha), \
        f"{pid}: byte drift vs r20 committed ride sha ({sha} != {r20ride})"
    return ans, str(rec.get("a1_source") or ""), src, path, sha


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


def judge_slot(pid, k, prompt):
    """One draw slot under the pre-registered transport ladder."""
    attempts = []
    outcome = None
    jc = None
    for try_n in range(1 + len(LADDER_BACKOFF_S)):
        if try_n:
            time.sleep(LADDER_BACKOFF_S[try_n - 1])
        econ.reset_governor(f"r21n30:{pid}:{k}"
                            + (f":retry{try_n}" if try_n else ""))
        jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                  max_tokens=4000)
        outcome = jc.get("outcome")
        attempts.append({"n": try_n + 1, "outcome": outcome,
                         "latency_s": (jc.get("latencies") or [None])[-1]})
        if outcome == "JUDGE_VALID":
            break
    return jc, outcome, attempts


def main() -> int:
    prior = {}
    if PARTIAL.exists():
        for r in json.loads(PARTIAL.read_text(encoding="utf-8")):
            prior[r["problem_id"]] = r
    results = []
    ladder_stats = {"slots": 0, "first_try_valid": 0, "recovered": 0,
                    "still_dead": 0, "total_attempts": 0}
    for pid in ALL:
        if pid in prior:
            results.append(prior[pid])
            print(f"  [{pid[:32]:<34}] resumed (partial)", flush=True)
            continue
        prob = _prob(pid)
        a1, a1_src, byte_src, byte_path, a1_sha = a_bytes_for(pid)
        base, b_src = baseline_for(pid)
        assert base.strip(), f"no baseline for {pid}"
        prompt = _rubric_prompt(prob, a1[:7000], base[:7000],
                                None) + AXIS_SUFFIX
        draws = []
        for k in range(K):
            jc, outcome, atts = judge_slot(pid, k, prompt)
            ladder_stats["slots"] += 1
            ladder_stats["total_attempts"] += len(atts)
            if outcome == "JUDGE_VALID":
                if len(atts) == 1:
                    ladder_stats["first_try_valid"] += 1
                else:
                    ladder_stats["recovered"] += 1
            else:
                ladder_stats["still_dead"] += 1
            draws.append({"k": k, "outcome": outcome,
                          "axes": parse_axes(jc),
                          "prefer": (jc.get("valid") or {}).get("prefer"),
                          "transport_attempts": atts})
            time.sleep(PACE_S)
        dec = row_metrics(draws)
        med = dec["median_axes"]
        r20row = _r20rows[pid]
        row = {"problem_id": pid,
               "a1_arm": r20row.get("a1_arm")
                         or str(a1_src).split("/")[0],
               "question_type": r20row.get("question_type")
                                or prob.get("question_type"),
               "question_type_gate": r20row.get("question_type_gate"),
               "critic_verdict": r20row.get("critic_verdict"),
               "baseline_source": b_src,
               "byte_provenance": {"byte_source": str(
                                       byte_path.relative_to(REPO)),
                                   "byte_class": byte_src,
                                   "a1_answer_sha256_16": a1_sha,
                                   "generation": "NONE this round — "
                                       "committed AM20 D1 bytes "
                                       "re-judged (draw variance held "
                                       "constant)"},
               "judge": list(JUDGE),
               "draws": draws,
               "majority_prefer": dec["majority_prefer"],
               "median_axes": med,
               "r20_reference": {
                   "record": "eval/battery_a1w2_full_r20.json",
                   "r20_medians": r20row.get("median_axes") or {},
                   "r20_fgap": r20row.get("feasibility_abs_gap"),
                   "r20_ndelta": r20row.get("novelty_delta")}}
        if med:
            row["novelty_delta"] = med["N_A"] - med["N_B"]
            row["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
            row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
            row["testability_delta"] = med["T_A"] - med["T_B"]
            row["constraint_delta"] = med["C_A"] - med["C_B"]
            r20med = r20row.get("median_axes") or {}
            row["r20_reference"]["medians_reproduced"] = (
                bool(r20med) and r20med == med)
        if pid == "eval-new01-supercap-dryout":
            row["standing_adjudication_note"] = r20row.get(
                "standing_adjudication_note")
        results.append(row)
        _atomic_write(PARTIAL,
                      json.dumps(results, indent=1, ensure_ascii=False)
                      + "\n")
        print(f"  [{pid[:32]:<34}] judged nd="
              f"{row.get('novelty_delta')} fgap="
              f"{row.get('feasibility_abs_gap')} "
              f"prefer={row.get('majority_prefer')} "
              f"r20med_match={row['r20_reference'].get('medians_reproduced')}",
              flush=True)
    assert len(results) == 30, f"pool incomplete: {len(results)}"
    # ---------- gate summaries (canonical core, unchanged) -------------
    iv = [r for r in results
          if str(r.get("question_type", "")).startswith("intervention")]
    pd_ = [r for r in results
           if str(r.get("question_type", "")).startswith("predictor")]
    tc = [r for r in results
          if (r.get("question_type_gate") or {}).get("verdict") == "MATCH"]
    repro = [r["r20_reference"]["medians_reproduced"] for r in results
             if r.get("median_axes")
             and "medians_reproduced" in r.get("r20_reference", {})]
    record = {
        "record": "BATTERY_A1W2_FULL_R21/1.0.0 — the AM21 D2 "
                  "gate-decisive measurement: 30-pair V4 re-judgment "
                  "under Art. 29 claim-before-work",
        "at": now,
        "claim": {"work_id": "r21-v4-battery-n30", "claim_id": "c-0002",
                  "executor": "builder-r20s2",
                  "registry": "eval/work_claims.json",
                  "verifier": "peer session INVITED — recomputes from "
                              "these committed bytes (Art. 13), never "
                              "re-runs; files a typed VERIFIER claim"},
        "pre_registration": {
            "commit": "this driver + the registry claims committed and "
                      "pushed BEFORE any judge call (git history order)",
            "byte_map": {"pilot_bytes": PILOT_BYTES,
                         "r11_pred_bytes": R11_PRED_BYTES,
                         "fresh_v4_bytes": FRESH_V4_BYTES},
            "generation": "ZERO — all 30 A-side answer bytes are the "
                          "committed AM20 D1 bytes, sha-verified "
                          "fail-closed at run time",
            "transport_ladder": {"attempts_per_slot": 1 + len(
                                     LADDER_BACKOFF_S),
                                 "backoff_s": list(LADDER_BACKOFF_S),
                                 "typed_purpose": "recover r20's 27/90 "
                                     "transport failures; reach the "
                                     ">= 30-pair clause; metric core "
                                     "unchanged"},
            "acceptance_verbatim": "feasibility |gap| <= 0.25 AND "
                                   "novelty delta >= 0.5 on >= 30 "
                                   "pairs, pre-registered, "
                                   "type-credited, judge != generator, "
                                   "queue CI green"},
        "arms": {
            "A": "V4 bytes byte-identical to the AM20 D1 battery "
                 "(7 pilot + 8 r11-predictor + 15 fresh V4, all "
                 "committed; sha-verified)",
            "B": "CURATED baselines — assembly identical to batteries "
                 "r7-r21 (dev12_fresh first, then baselines_curated)"},
        "judge": {"route": list(JUDGE), "k": K, "pace_s": PACE_S,
                  "transport_ladder": True,
                  "independence": "crowllm/Qwen vs zai/GLM generator — "
                                  "provider AND family independent"},
        "ladder_stats": ladder_stats,
        "results": results,
        "reproducibility_vs_r20": {
            "typed_finding": "judge determinism at t=0 predicts "
                             "median reproduction on rows whose r20 "
                             "medians came from >= 1 valid draw",
            "rows_with_medians": len(repro),
            "medians_reproduced": sum(1 for x in repro if x),
            "medians_moved": sum(1 for x in repro if not x)},
        "summary_intervention_rows": summarize(
            iv, "INTERVENTION rows only (AM16 D1 frontier continuity: "
                "r10 2.389 -> r11 1.5 -> r20 1.5 -> this)"),
        "summary_predictor_rows": summarize(
            pd_, "PREDICTOR rows only (r20 bytes re-judged)"),
        "summary_type_credited": summarize(
            tc, "type-MATCH pairs only — the AM21 D2 acceptance form "
                "(wrong-type novelty does NOT count)"),
        "summary_all_valid": summarize(
            results, "all valid pairs (unfiltered sensitivity)"),
        "gate_note": ("MEASUREMENT for the auditor (AM21 D2): the "
                      "acceptance — overall feasibility |gap| <= 0.25 "
                      "AND novelty delta >= 0.5 on >= 30 pairs, "
                      "type-credited — read on summary_type_credited "
                      "(primary); the >= 30-pair clause reads n_valid "
                      "there; the gate re-decision is the auditor's"),
    }
    _atomic_write(OUT, json.dumps(record, indent=1, default=str) + "\n")
    for lbl, s in (("TYPE-CREDITED (PRIMARY)", record[
            "summary_type_credited"]),
                   ("ALL-VALID", record["summary_all_valid"])):
        print(f"[r21n30] {lbl}: n={s.get('n_valid')} | nov Δ "
              f"{s.get('novelty_delta_mean')} CI {s.get('novelty_ci95')} "
              f"| feas |gap| {s.get('feasibility_abs_gap_mean')} CI "
              f"{s.get('feasibility_ci95')} | prefer "
              f"{s.get('prefer_tally')}", flush=True)
    print(f"[r21n30] ladder: {ladder_stats}", flush=True)
    print(f"[r21n30] repro vs r20: {record['reproducibility_vs_r20']}",
          flush=True)
    print(f"-> {OUT}", flush=True)
    return 0


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

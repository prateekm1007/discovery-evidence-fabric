#!/usr/bin/env python3
"""scripts/r53_p2_ablation_criteria.py — the zero-LLM adoption-criteria
evaluator for the P2 matched-budget DEV ablation (roadmap P2; claim
c-0071).

WHAT THIS IS: the deterministic evaluator of the three pre-registered
adoption criteria — schedule-share <= 17%, ALLOWED_ROW_OUTSIDE = 0,
mean score no drop vs the V7.7 baseline — over two run-row files. It
computes the typed verdict inputs and NOTHING else.

WHAT THIS IS NOT (typed): it is NOT the ablation itself. The ablation's
expansion leg is the machine's LLM job; this sandbox's LLM credential
state is degraded (the typed mid-R52 NVIDIA key absence carries over),
and the "mean no drop" leg must be scored under a valid metric
instrument — the public v8 rubric is burned evidence (F60) and may not
score anything. The ablation RUN therefore defers to the round where
the machine leg runs under a confidential instrument (v9 post-P0
custody). Committing the evaluator now keeps the adoption bar
pre-registered and CI-testable BEFORE any run (the AM44 protocol:
criteria before data).

AMENDMENT — R58 (2026-11-17, claim c-0079, dated BEFORE any scored
evaluation and BEFORE this round's criteria legs ran): the verdict
order is corrected for the UNMEASURABLE criterion-3 case. The v1.0.0
verdict ladder typed DELETE whenever criteria 1+2 were met but
criterion 3 was UNMEASURABLE — a deletion decided on NO measurement,
the symmetric violation of "never pass a gate on a point estimate"
(auditor constitution Art. 14: an under-powered or unmeasured clause
is UNRESOLVED, never passed and never failed). The amendment:
criterion 3 UNMEASURABLE with criteria 1+2 met now types
ADOPTION_DEFERRED_CRITERION_3_UNMEASURABLE (the adoption decision
waits for the confidential instrument; the numeric bars 1+2 still
bind and can still kill the addition). The MEASURED paths are
UNCHANGED: all-measured-and-met -> ADOPT; measured-and-unmet ->
DELETE; criteria 1/2 unmet -> the pre-registered bar says the
addition does not survive. No numeric bar (SCHEDULE_BAR, the 0/0
legs, the mean comparison) is touched by this amendment.

AMENDMENT — R60 (2026-11-18, session builder-r60s1, dated BEFORE the
arms-complete criteria evaluation runs): the row SHAPE is now checked
and refused TYPED (Art. 3 — fail closed, refusals typed never silent).
Empirical basis: the R59 verifier record's non-blocking Art. 3
observation (590fac029), reproduced live from committed bytes this
round — feeding RAW run-records (the per-row files under
rows_<arm>/) crashed v1.1.0 with an untyped AttributeError ('str'
object has no attribute 'get'), and a partial dict silently defaulted
allowed_row_outside to 0 (a silent pass path). v1.2.0 validates the
normalizer's shape BEFORE any computation: top level a non-empty JSON
object keyed by problem_id; every value an object; the required
fields present with legal types (mean_score number-or-None,
measure_classes list[str], allowed_row_outside int, bools refused —
never a silent .get default). A violation returns verdict
EVALUATION_REFUSED with a typed row_shape reason naming the offending
key and the fix (run the driver's --normalize step). The MEASURED
paths on well-shaped inputs are byte-equivalent to v1.1.0: no numeric
bar, no verdict-ladder rung, no aggregation changed.

Zero LLM, zero network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# v3.2.0 Art. 22 measured-path declaration (c-0079, F61 class): when the
# v9 machine leg runs, its measurement goes through the ENGINE route
# (discovery_fabric.engine.engine_route -> mechanism_space, the typed-
# operator engine), never a wrapper. See eval/measured_path_decision_r47
# .json (the committed routing decision) and
# tests/test_article22_measured_path.py (the CI that enforces this).
MEASURED_PATH = "discovery_fabric.engine.engine_route -> mechanism_space"

SCHEDULE_BAR = 0.17

# The normalizer's row shape, typed (v1.2.0): the ONLY legal input to
# evaluate() is the driver's --normalize output. Raw run-records (the
# per-row files under rows_<arm>/) carry these field-name keys at the
# TOP level; a normalized dict never does (its keys are problem ids).
RAW_RUN_RECORD_MARKERS = ("a1_answer", "final_meta", "arm_design",
                          "declared_template_prose", "sha256_16")
_ROW_FIELDS = {"mean_score": "number-or-None",
               "measure_classes": "list[str]",
               "allowed_row_outside": "int"}


def _is_number(v) -> bool:
    # bool is an int subclass in Python — a boolean is NOT a legal
    # score/outside count (typed shape, never a silent 0/1 pass)
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _shape_violation(rows, which: str):
    """Typed shape check (Art. 3, v1.2.0). Returns None when the rows
    match the normalizer shape; else a one-line typed reason. Never
    raises on bad shape — an untyped crash was the observed v1.1.0
    defect (AttributeError on raw run-records) and a silent .get
    default was the other (allowed_row_outside -> 0)."""
    if not isinstance(rows, dict):
        return (f"{which}: top level is {type(rows).__name__}, "
                "expected a JSON object keyed by problem_id (the "
                "driver's --normalize output)")
    if not rows:
        return f"{which}: empty rows object — nothing to evaluate"
    for pid, row in rows.items():
        if not isinstance(row, dict):
            return (f"{which}: row '{pid}' is {type(row).__name__}, "
                    "expected an object — RAW RUN-RECORD shape (the "
                    "per-row files under rows_<arm>/ are NOT the "
                    "evaluator input; run the driver's --normalize "
                    "step first)")
        raw_hits = [k for k in RAW_RUN_RECORD_MARKERS if k in row]
        if raw_hits:
            return (f"{which}: row '{pid}' carries raw run-record "
                    f"fields {raw_hits} — normalize first (the "
                    "evaluator input is the --normalize output shape)")
        for f, want in _ROW_FIELDS.items():
            if f not in row:
                return (f"{which}: row '{pid}' is missing required "
                        f"field '{f}' — a partial dict is refused, "
                        "never silently defaulted (v1.1.0 defaulted "
                        "allowed_row_outside to 0)")
        if not (_is_number(row["mean_score"]) or
                row["mean_score"] is None):
            return (f"{which}: row '{pid}' mean_score is "
                    f"{type(row['mean_score']).__name__}, expected "
                    "number or null")
        if not (isinstance(row["measure_classes"], list) and all(
                isinstance(c, str) for c in row["measure_classes"])):
            return (f"{which}: row '{pid}' measure_classes is not a "
                    "list of strings")
        if not (isinstance(row["allowed_row_outside"], int) and
                not isinstance(row["allowed_row_outside"], bool)):
            return (f"{which}: row '{pid}' allowed_row_outside is "
                    f"{type(row['allowed_row_outside']).__name__} "
                    f"({row['allowed_row_outside']!r}), expected int")
    return None


def evaluate(rows_path: Path, baseline_path: Path) -> dict:
    """Evaluate the three criteria. Row files are dicts keyed by
    problem_id -> {"mean_score": float|None, "measure_classes":
    [..], "allowed_row_outside": int} — the machine run's normalizer
    emits this shape; the evaluator refuses to guess (v1.2.0: the
    refusal is now TYPED and comes BEFORE any computation — a raw
    run-record or partial dict is EVALUATION_REFUSED, never an
    untyped crash and never a silent default)."""
    rows = json.loads(rows_path.read_text())
    base = json.loads(baseline_path.read_text())
    # Art. 3 (v1.2.0): typed shape refusal before computation
    bad = _shape_violation(rows, "candidate rows") \
        or _shape_violation(base, "baseline rows")
    if bad:
        return {"record": "R53_P2_ABLATION_CRITERIA/1.2.0",
                "verdict": "EVALUATION_REFUSED",
                "refusal": "row_shape",
                "reason": bad,
                "expected_shape": {"<problem_id>": {
                    "mean_score": "number|null",
                    "measure_classes": "[str, ..]",
                    "allowed_row_outside": "int"},
                    "producer": "scripts/r58_p2_ablation_driver.py "
                                "--normalize (the evaluator never "
                                "guesses a missing field)"}}
    common = sorted(set(rows) & set(base))
    if not common:
        return {"verdict": "EVALUATION_REFUSED",
                "reason": "no overlapping problem ids between the "
                          "candidate rows and the baseline rows — "
                          "nothing is invented"}
    # criterion 1: schedule-share over the candidate rows' measure
    # classes (duty_cycle = the monoculture family, F54)
    cls = [c for pid in common
           for c in rows[pid].get("measure_classes", [])]
    share = (cls.count("duty_cycle") / len(cls)) if cls else None
    crit1 = {"criterion": "schedule_share<=0.17",
             "value": share, "met": share is not None and
             share <= SCHEDULE_BAR}
    # criterion 2: ALLOWED_ROW_OUTSIDE must be 0
    outside = sum(rows[pid].get("allowed_row_outside", 0)
                  for pid in common)
    crit2 = {"criterion": "ALLOWED_ROW_OUTSIDE==0", "value": outside,
             "met": outside == 0}
    # criterion 3: mean no drop (scored under a valid instrument only;
    # absent scores -> UNMEASURABLE, never fabricated)
    if all(rows[pid].get("mean_score") is not None for pid in common) \
            and all(base[pid].get("mean_score") is not None
                    for pid in common):
        cand_m = sum(rows[pid]["mean_score"] for pid in common) / len(common)
        base_m = sum(base[pid]["mean_score"] for pid in common) / len(common)
        crit3 = {"criterion": "mean_no_drop", "candidate": round(cand_m, 4),
                 "baseline": round(base_m, 4), "met": cand_m >= base_m}
    else:
        crit3 = {"criterion": "mean_no_drop", "value": "UNMEASURABLE",
                 "reason": "scores absent — the instrument must be a "
                           "confidential valid one (v9 post-P0 custody)",
                 "met": False}
    all_met = crit1["met"] and crit2["met"] and crit3["met"]
    crit3_unmeasurable = crit3.get("value") == "UNMEASURABLE"
    # R58 amendment (dated above): an UNMEASURABLE criterion-3 with
    # criteria 1+2 met DEFERS the adoption decision — never a DELETE
    # on no measurement (auditor Art. 14: unmeasured = UNRESOLVED).
    # The measured paths are byte-equivalent to v1.0.0.
    verdict = ("ADOPT" if all_met else
               "ADOPTION_DEFERRED_CRITERION_3_UNMEASURABLE"
               if crit1["met"] and crit2["met"] and crit3_unmeasurable
               else "DELETE" if crit1["met"] and crit2["met"] else
               "INCOMPLETE — criteria unmet; the pre-registered "
               "bar says the addition does not survive")
    return {"record": "R53_P2_ABLATION_CRITERIA/1.2.0",
            "schedule_bar": SCHEDULE_BAR,
            "overlapping_rows": len(common),
            "criteria": [crit1, crit2, crit3],
            "verdict": verdict,
            "note": "evaluator only; the RUN defers (see module "
                     "docstring); v1.1.0 = the R58 UNMEASURABLE-"
                     "verdict amendment; v1.2.0 = the R60 typed "
                     "row-shape refusal (Art. 3; amendments dated in "
                     "the docstring)"}


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: r53_p2_ablation_criteria.py <candidate_rows.json> "
              "<baseline_rows.json>")
        sys.exit(2)
    out = evaluate(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

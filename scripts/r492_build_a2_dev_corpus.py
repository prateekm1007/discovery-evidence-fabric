#!/usr/bin/env python3
"""R492 — build + FREEZE the A2 DEV calibration corpus (min-path step 6).

Order of authority for this artifact:
  - Art. L (the attacker must be calibrated): the corpus must contain
    known-defect + known-good mechanisms covering, AT MINIMUM, the ten
    named classes (causal-invalidity, boundary-condition failure, evidence
    contradiction, baseline equivalence, implementation impossibility,
    manufacturing failure, measurement ambiguity, scaling failure, safety
    failure, hidden dependency).
  - Art. LIX (no benchmark gaming): all tuning happens on a separate
    DEVELOPMENT set; the sealed benchmark (R446/ATTACKER_CALIBRATION and
    the R412 sealed bars) is never touched by tuning. This corpus IS the
    A2 gauntlet's development set, and it is FROZEN BEFORE ANY TUNING.
  - Art. XXVII (no threshold invention): the pre-registered thresholds are
    REUSED verbatim from the R412 sealed bars (tpr_min 0.75, fpr_max 0.30,
    coverage_min 0.875, parse_completeness_min 0.875) — the same bars the
    R490 A2 calibration decision pinned for the gauntlet's destination
    state.

What this script does (deterministically, no network, no model calls):
  1. assembles the 21 cases from the two authorship modules;
  2. validates the corpus contract (schema, category counts, Art. L class
     coverage, prior-art state vocabulary, expected-kill-surface
     vocabulary, ground truth present per case, controls coherent);
  3. writes R492/A2_DEV_CORPUS/CORPUS.json with per-case sha256 and a
     whole-corpus sha256;
  4. writes R492/A2_DEV_CORPUS/FREEZE.json pinning the corpus hash,
     the freeze time, and the frozen-before-any-tuning declaration.

The freeze is the round's commitment: any later change to CORPUS.json is
a NEW corpus version (the freeze hash catches it), and no adversarial
tuning may run against a corpus version that was not frozen first.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from r492_corpus_cases_a import (  # noqa: E402
    A2_DIMENSIONS, COMMON_PROBLEM, VALID_PRIOR_ART_STATES, CASES_A)
from r492_corpus_cases_b import CASES_B  # noqa: E402

OUT_DIR = REPO / "R492" / "A2_DEV_CORPUS"
CORPUS_PATH = OUT_DIR / "CORPUS.json"
FREEZE_PATH = OUT_DIR / "FREEZE.json"

CATEGORIES = [
    "TRUE_POSITIVE_seeded_defect",
    "EVIDENCE_CONTRADICTED",
    "NEAR_MISS_real_effect_fatal_magnitude",
    "SCOPE_CONFLICT_declared_boundary_trap",
    "TRUE_NEGATIVE_clean_control",
    "MALFORMED_MISSING_EVIDENCE",
]

# Art. L minimum class list -> the seed_class values that satisfy each.
ART_L_CLASS_COVERAGE = {
    "causal-invalidity": "CAUSAL_INVALIDITY",
    "boundary-condition failure": "BOUNDARY_CONDITION_FAILURE",
    "evidence contradiction": "EVIDENCE_CONTRADICTION",
    "baseline equivalence": "BASELINE_EQUIVALENCE",
    "implementation impossibility": "IMPLEMENTATION_IMPOSSIBILITY",
    "manufacturing failure": "MANUFACTURING_FAILURE",
    "measurement ambiguity": "MEASUREMENT_AMBIGUITY",
    "scaling failure": "SCALING_FAILURE",
    "safety failure": "SAFETY_FAILURE",
    "hidden dependency": "HIDDEN_DEPENDENCY",
}

CANDIDATE_FIELDS = [
    "candidate_id", "mechanism", "intervention", "predicted_effect",
    "testable_prediction", "novel_design_variable", "known_failure_modes",
    "constraint_set",
]


def _sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def validate(cases: list[dict]) -> None:
    errs: list[str] = []
    ids = [c["case_id"] for c in cases]
    if len(ids) != len(set(ids)):
        errs.append("duplicate case_id")
    seen_cands = set()
    cat_counts: dict[str, int] = {}
    seed_classes = set()
    for c in cases:
        cid = c["case_id"]
        for f in ("case_id", "category", "seed_class", "control",
                  "candidate", "evidence_items", "ground_truth"):
            if f not in c:
                errs.append(f"{cid}: missing field {f}")
        if c["category"] not in CATEGORIES:
            errs.append(f"{cid}: unknown category {c['category']}")
        cat_counts[c["category"]] = cat_counts.get(c["category"], 0) + 1
        seed_classes.add(c["seed_class"])
        cand = c["candidate"]
        for f in CANDIDATE_FIELDS:
            if f not in cand:
                errs.append(f"{cid}: candidate missing {f}")
        if cand["candidate_id"] in seen_cands:
            errs.append(f"{cid}: duplicate candidate_id")
        seen_cands.add(cand["candidate_id"])
        gt = c["ground_truth"]
        for f in ("label", "expected_final", "defect_class",
                  "expected_kill_surface", "expected_defect_in_basis",
                  "ground_truth_basis", "prior_art_state"):
            if f not in gt:
                errs.append(f"{cid}: ground_truth missing {f}")
        if gt["prior_art_state"] not in VALID_PRIOR_ART_STATES:
            errs.append(f"{cid}: invalid prior_art_state "
                        f"{gt['prior_art_state']}")
        if gt["expected_kill_surface"] is not None and \
                gt["expected_kill_surface"] not in A2_DIMENSIONS:
            errs.append(f"{cid}: expected_kill_surface not an A2 "
                        f"dimension: {gt['expected_kill_surface']}")
        if gt["label"] == "KNOWN_BAD" and gt["expected_final"] != "KILLED":
            errs.append(f"{cid}: KNOWN_BAD must expect KILLED")
        if gt["label"] == "KNOWN_GOOD" and \
                gt["expected_final"] != "PASSED":
            errs.append(f"{cid}: KNOWN_GOOD must expect PASSED")
        # controls coherence: only TRUE_NEGATIVE cases are controls
        if c["category"] == "TRUE_NEGATIVE_clean_control" and \
                not c["control"]:
            errs.append(f"{cid}: TN case must be marked control")
        if c["category"] != "TRUE_NEGATIVE_clean_control" and c["control"]:
            errs.append(f"{cid}: non-TN case must not be control")
        # known-good cases must carry no expected kill surface
        if gt["label"] == "KNOWN_GOOD" and \
                gt["expected_kill_surface"] is not None:
            errs.append(f"{cid}: KNOWN_GOOD cannot name a kill surface")
    missing_classes = [cls for cls in ART_L_CLASS_COVERAGE
                       if ART_L_CLASS_COVERAGE[cls] not in seed_classes]
    if missing_classes:
        errs.append(f"Art. L class coverage INCOMPLETE: {missing_classes}")
    if cat_counts.get("TRUE_NEGATIVE_clean_control", 0) < 4:
        errs.append("fewer than 4 clean controls")
    if errs:
        raise_validation_failure(errs)
    return cat_counts, seed_classes


def raise_validation_failure(errs):
    print("VALIDATION FAILED:", file=sys.stderr)
    for e in errs:
        print("  -", e, file=sys.stderr)
    sys.exit(2)


def main() -> int:
    cases = [c() for c in (CASES_A + CASES_B)]
    cat_counts, seed_classes = validate(cases)

    per_case_sha = {c["case_id"]: _sha256_text(
        json.dumps(c, sort_keys=True, ensure_ascii=False)) for c in cases}

    corpus = {
        "artifact_type": "A2_DEV_CALIBRATION_CORPUS",
        "corpus_id": "r492-a2-dev-calibration/1.0.0",
        "created_in": "R492",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_provenance": "AI_REVIEW",
        "role": (
            "DEVELOPMENT corpus for the A2 adversarial gauntlet "
            "(a2/adversarial.py::adversarial_challenge) — the corpus ALL "
            "gauntlet tuning happens against (Art. LIX); the sealed "
            "benchmark (R446/ATTACKER_CALIBRATION, R412 sealed bars) is "
            "never touched by tuning"),
        "frozen_before_any_tuning": True,
        "authorship_independence": {
            "authored_before_any_run": True,
            "authored_by": "Coder (R492), from first-principles "
                           "engineering knowledge",
            "ground_truth_rule": (
                "every case's expected verdict, kill surface, and defect "
                "markers were written from engineering reasoning BEFORE "
                "any execution of the A2 gauntlet on this corpus; no "
                "ground truth was derived from the instrument's behavior "
                "on this or any corpus (Art. VIII/L)"),
            "disjoint_from": [
                "R446/ATTACKER_CALIBRATION (hot-rolling mill work-roll "
                "cooling spray system)",
                "R412/CALIBRATION (40-case, 24 domains; nearest cases are "
                "a rain-erosion healing coating and a blade VG retrofit — "
                "different problems and candidates)",
                "R401-WC2/ATTACKER_CALIBRATION (compressed-air moisture "
                "separator)",
                "R458/BENCHMARK_CORPUS (14 problems incl. dialysis, "
                "inverter, drip irrigation, cam follower)",
                "the six-domain seed campaign (infusion pumps, EV "
                "batteries, aerospace lithium, rails, rolling-stock, "
                "consumer li-ion)",
            ],
            "common_problem_domain": (
                "ballast water management (IMO D-2 retrofit, coastal bulk "
                "carrier) — not used by any listed corpus"),
        },
        "instrument_semantics": {
            "gated_instrument": (
                "a2/adversarial.py::adversarial_challenge — the 8-dimension "
                "gauntlet + V4 corrections; conductor ATTACK stage via "
                "engine/adapters.py AttackEngineAdapter; terminal "
                "rejection authority via a2/classify.py (the R490 "
                "composition finding)"),
            "per_case_inputs": (
                "each case pins candidate + evidence_items + the frozen "
                "prior_art_state (part of the ground truth, authored "
                "before any run); evidence_verified is true for every "
                "case so the V4 evidence gate passes and the gauntlet "
                "runs"),
            "scoping_note": (
                "this corpus measures the A2 gauntlet only; the engine "
                "independent_attack instrument has its own sealed corpus "
                "(R446) and is NOT re-measured here"),
        },
        "pre_registered_thresholds": {
            "provenance": (
                "REUSED verbatim from the R412 sealed bars "
                "(r412_calibration_seal.json, pre-registered 2026-09-05), "
                "the same bars the R490 A2_CALIBRATION_SCOPE decision "
                "pinned for the gauntlet's destination state; NO new "
                "threshold invented (Art. XXVII)"),
            "tpr_min": 0.75,
            "fpr_max": 0.30,
            "coverage_min": 0.875,
            "parse_completeness_min": 0.875,
            "scope": (
                "TPR measured over the defect cohorts (TRUE_POSITIVE + "
                "EVIDENCE_CONTRADICTED); FPR/TNR over the TRUE_NEGATIVE "
                "cohort; NEAR_MISS, SCOPE_CONFLICT, and "
                "MALFORMED_MISSING_EVIDENCE cohorts are category "
                "disciplines, not folded into the headline TPR/FPR"),
        },
        "scoring_contract": {
            "headline": (
                "TPR over defect cohorts; FPR/TNR over the clean-control "
                "cohort (conservative sealed-denominator: incomplete or "
                "EVALUATION_FAILED attacks count against coverage, never "
                "as survival)"),
            "kill_detection": (
                "a defect-cohort case is DETECTED when overall is KILLED "
                "and the killing dimension's basis text carries at least "
                "one of the case's expected_defect_in_basis markers; a "
                "KILL whose basis binds to no marker is flagged "
                "kill_unbound_to_defect (counted in coverage, reported "
                "separately)"),
            "category_disciplines": {
                "near_miss": (
                    "KILLED counted as detected only when the basis "
                    "carries the expected magnitude markers (cost, "
                    "lifetime, margin, or the case's own numbers)"),
                "scope_conflict": (
                    "SURVIVED is CORRECT (a kill here is a "
                    "SCOPE_MISMATCH false kill, reported separately, "
                    "never folded into headline FPR)"),
                "evidence_contradicted": (
                    "KILLED counted as detected only when the basis BINDS "
                    "to the provided evidence's numbers"),
                "malformed_missing_evidence": (
                    "any CONTRADICTION-dimension kill is the typed "
                    "false-kill class ABSENCE_AS_CONTRADICTION (Art. "
                    "XXI.3/XXV); an UNSUPPORTED_MECHANISM kill is honest; "
                    "overall KILLED or PASSED are both recorded"),
            },
            "v4_corrections_note": (
                "V4 corrections run inside the instrument (prior-art "
                "firewall, boundary-evidence standard, adversarial-"
                "invalid check); EVALUATION_FAILED and ADVERSARIAL_INVALID "
                "outcomes count against coverage, never as survival"),
        },
        "the_common_problem": COMMON_PROBLEM,
        "category_counts": cat_counts,
        "n_cases": len(cases),
        "art_l_class_coverage": {
            cls: (ART_L_CLASS_COVERAGE[cls] in seed_classes)
            for cls in ART_L_CLASS_COVERAGE
        },
        "cases": cases,
        "per_case_sha256": per_case_sha,
    }

    blob = json.dumps(corpus, indent=2, ensure_ascii=False) + "\n"
    corpus_sha = _sha256_text(blob)
    corpus["corpus_sha256"] = corpus_sha
    blob = json.dumps(corpus, indent=2, ensure_ascii=False) + "\n"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(blob, encoding="utf-8")

    freeze = {
        "artifact_type": "A2_DEV_CORPUS_FREEZE",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_provenance": "AI_REVIEW",
        "corpus_id": corpus["corpus_id"],
        "corpus_sha256": corpus_sha,
        "n_cases": corpus["n_cases"],
        "frozen_before_any_tuning": True,
        "declaration": (
            "frozen BEFORE any tuning of the A2 gauntlet (Art. LIX "
            "development-set discipline; the R492 operator directive's "
            "'the A2 DEV corpus, frozen before any tuning'); no "
            "adversarial_challenge invocation against any case of this "
            "corpus occurred before this freeze — the authorship modules "
            "are the record; any future change to CORPUS.json is a NEW "
            "corpus version and the old freeze hash exposes it"),
        "next_steps_per_owned_plan": (
            "R490 A2_CALIBRATION_SCOPE owned_work_plan steps 2-5: the "
            "/api/ops measurement transport, the deployed-instrument "
            "measurement, the seal into calibration_records/, and the "
            "consumption gate — the seal may only ride a measurement of "
            "the DEPLOYED instrument; DEV-corpus tuning may now begin "
            "against THIS frozen version"),
    }
    FREEZE_PATH.write_text(
        json.dumps(freeze, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print(f"corpus: {CORPUS_PATH}")
    print(f"  n_cases={corpus['n_cases']}  categories={cat_counts}")
    print(f"  corpus_sha256={corpus_sha}")
    print(f"freeze: {FREEZE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

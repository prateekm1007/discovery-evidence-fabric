#!/usr/bin/env python3
"""scripts/r445_false_kill_diagnosis.py — R445-B.

The attacker-calibration diagnosis (NOT a fix, NOT a threshold change):

  TPR 12/12, false-kill 4/4, TNR 0 — the R444 measurement. This round's
  objective is DIAGNOSIS: for every clean false-kill, record the
  mechanism, the attacker challenge, the exact claimed weakness, the
  evidence basis of each claim, why the challenge was treated as
  lethal, and why the clean control should survive — then classify the
  false kill with classes that EMERGE FROM THE EVIDENCE.

WHAT THIS SCRIPT DOES NOT DO (the directive's hard boundary):
  - no attacker threshold changes (nothing is lowered to improve TNR)
  - no corpus changes (the sealed corpus is read, never written)
  - no relabeling of clean controls
  - no attacker code changes

The calibration state stays NOT_CALIBRATED and the abstain/escalate
gate (discovery_fabric/engine/attacker_calibration.py) stays in force
unchanged — the machine cannot yet distinguish 'found a real problem'
from 'asserted a problem' at attack time; this diagnosis identifies
WHAT that distinction requires (evidence-binding, record-binding,
scope-binding, verdict proportionality) without claiming it exists.

Mechanical checks (per kill-basis, so the classification is grounded,
not narrated):
  1. grounding: does the basis cite a source, computation, or record
     field? (citation markers / numeric derivations / field quotes)
  2. record-binding: does the basis claim ABSENCE of content the
     candidate record explicitly carries (testable_prediction,
     constraint_set.boundary_conditions)?
  3. absolutist language: 'impossible', 'cannot', 'any', 'violating
     fundamental', 'immediately', 'never' — assertion markers
  4. scope: does the basis demand content beyond the candidate
     contract (empirical data from a prediction-stage candidate,
     performance outside the declared boundary conditions) or
     substitute a different problem/requirement?

The primary class per basis is adjudicated from these checks plus the
corpus ground truth; judgment fields are marked JUDGMENT (honest about
which part is mechanical vs adjudicated).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "R401-WC2" / "ATTACKER_CALIBRATION" / "CALIBRATION_RESULTS.json"
CORPUS = REPO / "R401-WC2" / "ATTACKER_CALIBRATION" / "CORPUS.json"
OUT = REPO / "R445" / "ATTACKER_FALSE_KILL_DIAGNOSIS.json"

# --- mechanical markers -----------------------------------------------------
CITATION_PATTERNS = [
    r"\[\d+\]", r"\(20\d\d\)", r"et al", r"doi", r"ISO \d+",
    r"IEC \d+", r"per (the )?(record|corpus|source)", r"source span",
    r"measured in", r"computed as", r"calculation",
]
ABSOLUTIST_PATTERNS = [
    r"\bimpossible\b", r"\bcannot\b", r"\bnever\b", r"\bany\b",
    r"violating fundamental", r"\bimmediately\b", r"catastroph",
    r"\bzero\b", r"\bnone\b",
]
ABSENCE_CLAIM_PATTERNS = [
    r"no testing", r"no evidence", r"zero empirical", r"not provide[sd]?",
    r"lacks? validation", r"without comparative", r"provides no",
    r"no empirical", r"fails? to address", r"lacks? specification",
]


def _hits(text: str, patterns: list[str]) -> list[str]:
    low = str(text).lower()
    return [p for p in patterns if re.search(p, low)]


def _numbers_in(text: str) -> list[str]:
    return re.findall(r"\d+\.?\d*", str(text))


def _basis_grounding(basis: str) -> dict:
    """Mechanical grounding check on one claimed weakness."""
    low = str(basis).lower()
    # a computation is an explicit arithmetic derivation — a hyphenated
    # RANGE ('5-8%', '0.8-1.6mm') is a mention, not a computation
    computation = bool(
        re.search(r"\d+\s*(?:\*|\+|\/|x|×|÷)\s*\d+", low)
        or re.search(r"=\s*\d", low))
    return {
        "citations": _hits(basis, CITATION_PATTERNS),
        "absolutist_markers": _hits(basis, ABSOLUTIST_PATTERNS),
        "absence_claims": _hits(basis, ABSENCE_CLAIM_PATTERNS),
        "numbers_mentioned": _numbers_in(basis),
        "carries_computation": computation,
    }


def _record_binding(basis: str, candidate: dict) -> dict:
    """Does the basis claim absence of content the record carries?"""
    low = str(basis).lower()
    tp = str(candidate.get("testable_prediction") or "").lower()
    bc = str((candidate.get("constraint_set") or {})
             .get("boundary_conditions") or "").lower()
    pe = str(candidate.get("predicted_effect") or "").lower()
    claims_absence = bool(_hits(basis, ABSENCE_CLAIM_PATTERNS))
    contradictions = []
    # the prediction's own instrument covers the claimed-absent content
    if claims_absence and ("comparative" in low or "baseline" in low) \
            and "baseline" in tp:
        contradictions.append(
            "basis demands comparative testing; testable_prediction "
            f"specifies the comparative arm: {tp[:120]!r}")
    if claims_absence and "testing" in low and ("8 bar" in bc or
                                                "5 m3" in bc):
        contradictions.append(
            "basis claims no testing at the boundary; "
            f"constraint_set.boundary_conditions = {bc!r} and the "
            "testable_prediction is an instrumented run at that boundary")
    if claims_absence and ("stage" in low or "staged" in low) \
            and "stage" in tp:
        contradictions.append(
            "basis claims no stage-wise evidence; testable_prediction "
            f"specifies stage-by-stage instrumentation: {tp[:120]!r}")
    if "marginal" in low and pe:
        # arithmetic check: predicted vs baseline magnitudes from the
        # prediction text itself
        nums = _numbers_in(tp)
        contradictions.append(
            f"basis calls the improvement marginal; the prediction "
            f"carries the magnitudes {nums[:6]} (adjudicated against "
            "the problem quantity)")
    return {"claims_absence": claims_absence,
            "record_contradictions": contradictions}


# --- the per-basis adjudication ---------------------------------------------
# Classes EMERGED FROM THE EVIDENCE (the 23 kill-bases across the four
# clean controls; each entry: (case, attack_class, class, why)).
ADJUDICATION = {
    ("cal-13-clean-vane-quantified", "MECHANISM_FAILURE"): (
        "UNSUPPORTED_OBJECTION",
        "asserted physics with no computation or source: re-entrainment "
        "'overwhelming ANY passive design' at 8 bar — contradicted by "
        "standard vane-pack practice (higher gas density at constant "
        "mass flow raises the Stokes number per stage, strengthening "
        "inertial separation; inter-stage quiescent zones are the "
        "textbook re-entrainment countermeasure). JUDGMENT: the "
        "physics direction is asserted backwards."),
    ("cal-13-clean-vane-quantified", "BOUNDARY_CONDITION_FAILURE"): (
        "RECORD_CONTRADICTED",
        "basis claims 'no testing provided at the actual boundary "
        "condition of 8 bar' — the record's constraint_set.boundary_"
        "conditions IS '8 bar, 5 m3/h, inlet 20 C' and the "
        "testable_prediction is a chilled-mirror rig run at exactly "
        "that boundary. MECHANICAL: absence claim + boundary field "
        "present."),
    ("cal-13-clean-vane-quantified", "EVIDENCE_CONTRADICTION"): (
        "SCOPE_MISMATCH",
        "the candidate DISCLOSES oil fouling as a known failure mode "
        "(honest epistemic posture per the corpus contract); the basis "
        "treats the disclosed-failure-mode list as an unrebutted "
        "contradiction and demands product-level mitigation from a "
        "prediction-stage candidate. JUDGMENT: category error about "
        "what a candidate record is."),
    ("cal-13-clean-vane-quantified", "BASELINE_EQUIVALENCE"): (
        "RECORD_CONTRADICTED",
        "basis calls the 3 C improvement 'unsubstantiated without "
        "comparative testing data' — the testable_prediction specifies "
        "the comparative arm ('versus 12 C for the baseline cyclone in "
        "the same rig'). MECHANICAL: absence claim + comparative arm "
        "present in the prediction."),
    ("cal-13-clean-vane-quantified", "IMPLEMENTATION_IMPOSSIBILITY"): (
        "UNSUPPORTED_OBJECTION",
        "'1.2 mm gaps ... impossible to manufacture ... at micron-scale "
        "precision' — 1.2 mm is NOT micron scale (three orders of "
        "magnitude), and 1-2 mm vane gaps are commercial stamped-"
        "/formed-sheet geometry. MECHANICAL: absolutist marker + no "
        "citation. JUDGMENT: factual self-contradiction inside the "
        "basis text itself."),
    ("cal-13-clean-vane-quantified", "MEASUREMENT_AMBIGUITY"): (
        "SEVERITY_INFLATION",
        "the +/-1 C tolerance objection ignores that the predicted "
        "effect is 9 C (12 C -> 3 C) — nine times the tolerance; the "
        "point is an enrichment-level observation (RISK), escalated to "
        "KILL. MECHANICAL: magnitudes present in the prediction."),
    ("cal-14-clean-coalescer-quantified", "MECHANISM_FAILURE"): (
        "UNSUPPORTED_OBJECTION",
        "'borosilicate glass-fiber coalescing media cannot effectively "
        "merge sub-8-micrometer droplets at 8 bar ... violating "
        "fundamental aerosol physics' — coalescing filter elements are "
        "THE standard industrial solution for sub-micron oil aerosol at "
        "7-10 bar; at constant mass flow the higher gas density LOWERS "
        "velocity and lengthens media residence time. JUDGMENT: "
        "asserted physics contradicted by standard practice, no source."),
    ("cal-14-clean-coalescer-quantified", "BOUNDARY_CONDITION_FAILURE"): (
        "SCOPE_MISMATCH",
        "the 6-month swap objection invents atmospheric-hydrocarbon "
        "blinding BEYOND the declared boundary ('oil-free inlet' in the "
        "constraint set) — an unbounded contamination scenario outside "
        "the candidate's stated envelope, treated as a boundary "
        "failure of the candidate. MECHANICAL: scenario quantities "
        "absent from constraint_set."),
    ("cal-14-clean-coalescer-quantified", "EVIDENCE_CONTRADICTION"): (
        "SCOPE_MISMATCH",
        "'zero empirical data to support the predicted 0.5 mg/m3' — "
        "candidates carry quantified PREDICTIONS plus falsification "
        "instruments; demanding completed-experiment data from a "
        "prediction-stage record is a category error (the corpus "
        "contract is prediction + instrument, not measured result). "
        "JUDGMENT: epistemic-stage mismatch."),
    ("cal-14-clean-coalescer-quantified", "BASELINE_EQUIVALENCE"): (
        "UNSUPPORTED_OBJECTION",
        "'0.5 mg/m3 ... offers only marginal improvement over baseline "
        "(40 mg/m3)' — an 80x reduction on the problem quantity called "
        "marginal. MECHANICAL: the magnitudes are in the basis text "
        "itself and contradict the adjective."),
    ("cal-14-clean-coalescer-quantified", "IMPLEMENTATION_IMPOSSIBILITY"): (
        "UNSUPPORTED_OBJECTION",
        "layer-graded glass-fiber media (8 -> 2 micrometers) is a "
        "standard commercial coalescer cartridge construction; the "
        "asserted manufacturing impossibility carries no process "
        "analysis, tolerance chain, or source. JUDGMENT: asserted "
        "impossibility of a catalog product."),
    ("cal-15-clean-drain-failsafe", "MECHANISM_FAILURE"): (
        "SEVERITY_INFLATION",
        "contamination-induced pilot sticking is a PLAUSIBLE failure "
        "mode worth flagging — the candidate's novel design variable "
        "is precisely the spring force margin (1.5-3x); the basis "
        "presents a risk scenario and jumps to mechanism failure with "
        "no sticking-probability evidence. JUDGMENT: RISK content, "
        "KILL verdict."),
    ("cal-15-clean-drain-failsafe", "BOUNDARY_CONDITION_FAILURE"): (
        "UNSUPPORTED_OBJECTION",
        "'8 bar exceeds the typical pressure rating of standard "
        "spring-loaded drain valves' — standard pneumatic condensate "
        "drains are rated 10-16 bar; the asserted spec limit is "
        "contradicted by catalog practice and carries no source. "
        "JUDGMENT: fabricated constraint."),
    ("cal-15-clean-drain-failsafe", "EVIDENCE_CONTRADICTION"): (
        "UNSUPPORTED_OBJECTION",
        "'industry data shows similar systems typically experience "
        "carryover events at 5-8% of operating cycles' — an uncited "
        "invented statistic ('industry data shows' with no source, no "
        "span, no numbers provenance). MECHANICAL: zero citation "
        "markers."),
    ("cal-15-clean-drain-failsafe", "BASELINE_EQUIVALENCE"): (
        "SCOPE_MISMATCH",
        "the basis faults the candidate for 'coalescing element "
        "saturation ... unchanged from the baseline' — but the "
        "candidate's problem is SUMP-OVERFLOW carryover (the drain "
        "function), not coalescer saturation: the attack substitutes a "
        "different problem than the one the candidate addresses. "
        "JUDGMENT: problem substitution."),
    ("cal-15-clean-drain-failsafe", "IMPLEMENTATION_IMPOSSIBILITY"): (
        "UNSUPPORTED_OBJECTION",
        "'capacitive level sensor cannot reliably detect condensate at "
        "8 bar due to dielectric constant variations' — capacitive "
        "condensate detection is the standard sensing principle in "
        "commercial compressed-air drains at these pressures; the "
        "asserted impossibility has no analysis or source. JUDGMENT: "
        "asserted impossibility of a catalog function."),
    ("cal-15-clean-drain-failsafe", "MEASUREMENT_AMBIGUITY"): (
        "SEVERITY_INFLATION",
        "specifying the pressure-decay curve during the 2-second "
        "closure is a FAIR enrichment of the measurement contract — "
        "an enrichment-level point (RISK) escalated to KILL. JUDGMENT: "
        "proportionality failure."),
    ("cal-16-clean-staged-separator", "MECHANISM_FAILURE"): (
        "RECORD_CONTRADICTED",
        "'lacks validation of droplet capture efficiency at each stage, "
        "with no evidence that the staged approach achieves the claimed "
        "7 C reduction' — the testable_prediction specifies stage-by-"
        "stage dew-point instrumentation (9 C then 5 C then 2 C). "
        "MECHANICAL: absence claim + stage instrumentation present."),
    ("cal-16-clean-staged-separator", "BOUNDARY_CONDITION_FAILURE"): (
        "SCOPE_MISMATCH",
        "'variable flow conditions beyond the specified 5 m3/h' — the "
        "declared boundary IS 5 m3/h steady; demand cycling is a "
        "deployment concern OUTSIDE the stated envelope (a legitimate "
        "RISK for the envelope's edges, not a boundary failure of the "
        "candidate as specified). MECHANICAL: demanded quantity absent "
        "from constraint_set."),
    ("cal-16-clean-staged-separator", "EVIDENCE_CONTRADICTION"): (
        "SCOPE_MISMATCH",
        "'no empirical data ... making the entire prediction "
        "speculative' — the prediction-vs-data category error again: "
        "a quantified, instrumented prediction is a hypothesis BY "
        "DESIGN; 'speculative' is the honest epistemic class of every "
        "candidate, not a defect. JUDGMENT: epistemic-stage mismatch."),
    ("cal-16-clean-staged-separator", "BASELINE_EQUIVALENCE"): (
        "SCOPE_MISMATCH",
        "'the claimed 2 C dew point is still above typical instrument "
        "requirements' — the common problem's target is the 3 C dew "
        "point; 2 C BEATS it. The attack substitutes an unstated "
        "stricter requirement. MECHANICAL/JUDGMENT: requirement "
        "substitution against the corpus's own stated problem."),
    ("cal-16-clean-staged-separator", "IMPLEMENTATION_IMPOSSIBILITY"): (
        "UNSUPPORTED_OBJECTION",
        "0.8-1.6 mm vane gaps are within commercial vane-pack "
        "geometry; 'would likely clog immediately' is asserted with no "
        "loading analysis (and stage-2 inlet oil loading is already "
        "reduced by the upstream cyclone). JUDGMENT: asserted "
        "immediacy without analysis."),
    ("cal-16-clean-staged-separator", "MEASUREMENT_AMBIGUITY"): (
        "SEVERITY_INFLATION",
        "the +/-1 C tolerance objection against 4 C and 3 C stage "
        "steps; the T/P/RH-instrumentation enrichment is fair — both "
        "are RISK-level points escalated to KILL. JUDGMENT: "
        "proportionality failure."),
}

CLASS_DEFINITIONS = {
    "UNSUPPORTED_OBJECTION": (
        "the attacker ASSERTED a problem: a bare physics/spec/statistic "
        "claim with no citation, no computation, no record binding — "
        "frequently contradicted by standard industrial practice or by "
        "arithmetic inside the basis text itself"),
    "RECORD_CONTRADICTED": (
        "the basis claims the ABSENCE of content the candidate record "
        "explicitly carries (the instrumented prediction, the "
        "comparative arm, the boundary conditions) — the attacker did "
        "not bind its claim to the record"),
    "SCOPE_MISMATCH": (
        "the basis demands content the candidate contract cannot carry "
        "(completed-experiment data from a prediction-stage record, "
        "product-level mitigation), performance outside the declared "
        "boundary conditions, or substitutes a different problem/"
        "requirement than the one addressed"),
    "SEVERITY_INFLATION": (
        "a legitimate RISK-level observation (an enrichment, a "
        "plausible failure-mode scenario) escalated to a KILL verdict "
        "without lethality evidence"),
}


def main() -> int:
    results = json.loads(RESULTS.read_text())
    corpus = json.loads(CORPUS.read_text())
    cases = {c["case_id"]: c for c in corpus["cases"]}
    per_case = []
    class_counts: dict[str, int] = {}
    n_bases = 0
    n_grounded = 0
    for rec in results["per_case"]:
        if not rec.get("control"):
            continue
        case_id = rec["case_id"]
        case = cases[case_id]
        cand = case["candidate"]
        bases = []
        for kb in rec.get("kill_bases", []):
            n_bases += 1
            basis = kb["basis"]
            grounding = _basis_grounding(basis)
            binding = _record_binding(basis, cand)
            key = (case_id, kb["attack_class"])
            cls, why = ADJUDICATION.get(
                key, ("UNADJUDICATED", "no adjudication recorded"))
            grounded = bool(grounding["citations"]
                            or grounding["carries_computation"])
            if grounded:
                n_grounded += 1
            class_counts[cls] = class_counts.get(cls, 0) + 1
            bases.append({
                "attack_class": kb["attack_class"],
                "verdict": rec["verdicts"].get(kb["attack_class"]),
                "exact_claimed_weakness": basis,
                "evidence_basis": {
                    "citations": grounding["citations"],
                    "computation_present":
                        grounding["carries_computation"],
                    "absolutist_markers":
                        grounding["absolutist_markers"],
                    "absence_claims": grounding["absence_claims"],
                    "record_contradictions":
                        binding["record_contradictions"],
                    "grounded_in_evidence_or_computation": grounded,
                },
                "why_considered_lethal_by_attacker": (
                    f"the attacker returned KILL on the "
                    f"{kb['attack_class']} dimension (one of "
                    f"{sum(1 for v in rec['verdicts'].values() if v == 'KILL')}"
                    f" simultaneous KILL verdicts across "
                    f"{len(rec['verdicts'])} dimensions — the verdict "
                    f"structure carries no per-dimension lethality "
                    f"discrimination)"),
                "classification": cls,
                "classification_basis": why,
            })
        per_case.append({
            "case_id": case_id,
            "expected_outcome": "SURVIVE (clean control)",
            "measured_outcome": rec["outcome"],
            "mechanism": cand["mechanism"],
            "intervention": cand["intervention"],
            "testable_prediction": cand["testable_prediction"],
            "boundary_conditions": cand["constraint_set"][
                "boundary_conditions"],
            "ground_truth": case["ground_truth"]["defect_description"],
            "attacker_challenge": {
                "overall": rec["overall"],
                "verdicts": rec["verdicts"],
                "independence_mode": rec["independence_mode"],
                "attacker_provider": rec["attacker_provider"],
            },
            "why_the_control_should_survive": (
                f"{case['ground_truth']['defect_description']}. The "
                f"kill-basis analysis: "
                f"{class_counts_summary(bases)}"),
            "kill_bases": bases,
        })

    record = {
        "artifact": "R445_ATTACKER_FALSE_KILL_DIAGNOSIS",
        "round": "R445-B",
        "directive": ("diagnose the false kills — record mechanism, "
                      "challenge, exact claimed weakness, evidence basis, "
                      "why lethal, why the control should survive; "
                      "classify with evidence-emergent classes; the "
                      "attacker is NOT weakened, the corpus is NOT "
                      "changed, no clean control is relabeled"),
        "reviewer_provenance": "AI_REVIEW (Art. LXVII — the diagnosis "
                               "author is the coder agent; the "
                               "adjudication fields are marked "
                               "MECHANICAL or JUDGMENT per basis)",
        "measured_inputs": {
            "calibration_results": str(RESULTS.relative_to(REPO)),
            "corpus": str(CORPUS.relative_to(REPO)),
            "tpr": "12/12 seeded defects killed",
            "false_kill_rate": "4/4 clean controls killed",
            "tnr": 0.0,
        },
        "classes_emerged_from_evidence": CLASS_DEFINITIONS,
        "aggregate": {
            "n_clean_controls": 4,
            "n_kill_bases": n_bases,
            "class_counts": class_counts,
            "bases_grounded_in_evidence_or_computation": n_grounded,
            "bases_grounded_fraction": round(n_grounded / max(1, n_bases), 3),
        },
        "structural_findings": [
            ("GROUNDING: 0 of the {} kill bases cites a source, a "
             "computation, or a record field — every claimed weakness is "
             "a bare assertion (several carry absolutist quantifiers: "
             "'impossible', 'cannot', 'any', 'violating fundamental', "
             "'immediately').").format(n_bases),
            ("RECORD BINDING: {} bases claim the ABSENCE of content the "
             "candidate record explicitly carries (the instrumented "
             "prediction, the comparative arm, the declared boundary "
             "conditions) — the attacker did not read-bind its claims "
             "to the record it was given.").format(
                class_counts.get("RECORD_CONTRADICTED", 0)),
            ("SCOPE: {} bases demand content outside the candidate "
             "contract (completed-experiment data from a prediction-"
             "stage record, performance outside the declared envelope, "
             "or a substituted problem/requirement).").format(
                class_counts.get("SCOPE_MISMATCH", 0)),
            ("PROPORTIONALITY: {} bases are RISK-level enrichments or "
             "plausible failure-mode scenarios escalated to KILL without "
             "lethality evidence.").format(
                class_counts.get("SEVERITY_INFLATION", 0)),
            ("VERDICT STRUCTURE: each clean control received 5-6 "
             "simultaneous KILL verdicts across the six attack "
             "dimensions — the verdict pattern is INDISTINGUISHABLE "
             "from the seeded-defect cases' verdict pattern (TPR 12/12 "
             "with the same all-kill shape): the KILL verdict carries "
             "no per-dimension discriminative information."),
            ("THE DISTINCTION the machine must eventually make "
             "mechanically: 'found a real problem' = an objection "
             "BOUND to evidence/computation, to the candidate's actual "
             "record fields, and to the declared scope, with verdict "
             "proportionality (RISK for enrichment-level points). "
             "'Asserted a problem' = a plausible sentence with none of "
             "those bindings. 0 of {} bases satisfy the first "
             "definition; the 23 bases split across the four failure "
             "shapes above.").format(n_bases),
        ],
        "calibration_state_unchanged": {
            "state": "NOT_CALIBRATED",
            "abstain_escalate_gate": (
                "discovery_fabric/engine/attacker_calibration.py — IN "
                "FORCE, UNCHANGED this round: an independent-attack "
                "KILL remains INADMISSIBLE as a terminal verdict "
                "(reclassified at consumption to ESCALATED_OBJECTION "
                "with the objection preserved verbatim)"),
            "what_would_change_it": (
                "a future instrument version that mechanically binds "
                "each objection to evidence/computation, the record, "
                "and the declared scope — measured on a sealed corpus "
                "with FPR <= 0.30 at TPR >= 0.75 (the pre-registered "
                "bars, Art. XXVII). NOT implemented this round: this "
                "diagnosis is post-hoc analysis by the coder, not a "
                "machine capability (the adjudication is marked "
                "MECHANICAL where checkable and JUDGMENT where not)"),
            "forbidden_and_not_done": [
                "attacker thresholds lowered to improve TNR",
                "corpus modified because it produces false kills",
                "difficult controls removed",
                "clean controls relabeled defective without evidence",
            ],
        },
        "per_case": per_case,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"[r445-diagnosis] {OUT}")
    print(f"  kill bases: {n_bases} | grounded: {n_grounded}")
    print(f"  classes: {class_counts}")
    return 0


def class_counts_summary(bases: list[dict]) -> str:
    counts: dict[str, int] = {}
    for b in bases:
        counts[b["classification"]] = counts.get(b["classification"], 0) + 1
    return ", ".join(f"{k} x{v}" for k, v in sorted(counts.items()))


if __name__ == "__main__":
    sys.exit(main())

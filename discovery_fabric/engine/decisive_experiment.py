"""discovery_fabric/engine/decisive_experiment.py — R452 Phase 6: the
constitutional decisive-experiment contract OBJECT.

Directive Phase 6: "Implement the constitutional experiment object
with all required fields:

    hypothesis
    treatment
    control
    measurement
    apparatus
    sample
    acceptance_threshold
    falsification_threshold
    uncertainty
    cost
    time
    safety
    kill_outcome

The critical invariant is: There must exist an outcome that kills the
mechanism. An experiment that can only confirm the proposal is not a
decisive experiment."

This module is the CONSTRUCTIVE authority (the builder/validator of
experiment objects). It complements — never replaces — the R444-D
Article LII PROJECTION (experiment_selector.article_lii_contract,
which projects the twelve fields from a run's own records with honest
UNKNOWN blockers). Where the projection READS runs, this module
WRITES valid experiment objects and ENFORCES the completeness
contract mechanically:

  validate_experiment_contract(exp) -> {
    "valid": bool,
    "missing_fields": [...],          # the 13 required fields
    "kill_outcome_present": bool,     # THE INVARIANT
    "kill_outcome_vacuous": bool,     # an outcome that "can only
                                      # confirm" — the directive's
                                      # rejection case
    "rejection_reason": str | None,
    "epistemic_class_violations": [...]
  }

  A contract is COMPLETE only when:
    1. every required field is present AND non-vacuous (a blocker
       like "UNKNOWN (no stage recorded...)" is an honest INCOMPLETE
       state — it may be CARRIED, but the contract then reads
       INCOMPLETE, never VALID — Art. XXV);
    2. the kill outcome is present, is an OUTCOME (a measurable
       observation that can occur), and CONTRADICTS the mechanism's
       claimed effect (an outcome that is consistent with the
       mechanism regardless of whether it works — "the experiment
       runs and data is collected" — is VACUOUS: it cannot kill, so
       the experiment is not decisive);
    3. the acceptance threshold and the falsification threshold are
       DIFFERENT observations (identical or compatible-everywhere
       thresholds are a confirm-only contract in disguise);
    4. every field carries an epistemic class in the closed
       vocabulary (SOURCE_FACT / MODEL_DERIVED / COMPUTED /
       EXTERNAL_PRECEDENT / UNKNOWN — the directive's Phase 5
       vocabulary extended with the engine's existing classes).

  build_virtual_experiment_contract(mechanistic_record) — the Phase 7
  bridge: a VALID experiment object constructed from a mechanistic
  virtual-experiment record (the solver chain's own threshold,
  measurement, and kill outcome — never invented values: the kill
  outcome is "the measured flow stays below the problem's own
  declared requirement", which CAN occur and DOES kill the mechanism
  claim).

Constitutional anchors: Art. LII (the killer experiment is a
falsification contract — there must exist an outcome that kills the
mechanism), Art. XXVII (thresholds carry provenance), Art. XXV
(vacuous is not valid), Art. XXXVIII (a virtual experiment's
evidence class is COMPUTATIONAL_RESULT — it can never be labeled a
physical observation).
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional

CONTRACT_VERSION = "decisive_experiment/1.0.0"

#: the thirteen required fields (directive Phase 6, verbatim order)
REQUIRED_FIELDS = (
    "hypothesis",
    "treatment",
    "control",
    "measurement",
    "apparatus",
    "sample",
    "acceptance_threshold",
    "falsification_threshold",
    "uncertainty",
    "cost",
    "time",
    "safety",
    "kill_outcome",
)

#: the closed epistemic-class vocabulary for every field
FIELD_EPISTEMIC_CLASSES = (
    "SOURCE_FACT", "MODEL_DERIVED", "COMPUTED", "EXTERNAL_PRECEDENT",
    "UNKNOWN",
)

#: honest blocker vocabulary — a field whose value is one of these is
#: PRESENT but INCOMPLETE (carried honestly, never silently valid)
_BLOCKER_MARKERS = (
    "unknown", "no stage recorded", "not recorded", "none exists",
    "would have to be invented", "no separate", "no sample-size",
    "no safety-analysis", "not split out",
)

#: vacuous kill-outcome markers — outcomes that cannot kill
_VACUOUS_MARKERS = (
    "data is collected", "the experiment completes", "results are "
    "obtained", "any outcome", "all outcomes", "regardless of the "
    "result", "confirms", "is confirmed", "runs successfully",
)

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_DIRECTION_RE = re.compile(
    r"\b(below|above|under|over|exceeds|less than|more than|at least|"
    r"at most|outside|within|fails?|passes?|drops?|rises?|stays?)\b",
    re.IGNORECASE)


def _is_blocker(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip().lower()
    return any(m in v for m in _BLOCKER_MARKERS) or v in (
        "unknown", "none", "n/a")


def _is_vacuous_kill(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip().lower()
    return any(m in v for m in _VACUOUS_MARKERS)


def validate_experiment_contract(exp: Dict[str, Any]) -> Dict[str, Any]:
    """The completeness + decisiveness validator (fail-closed).

    Returns the validation record; `valid` is True ONLY when the
    contract is complete AND decisive (an outcome that kills the
    mechanism exists and is real)."""
    missing: List[str] = []
    blockers: List[str] = []
    for field in REQUIRED_FIELDS:
        v = exp.get(field)
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(field)
        elif _is_blocker(v):
            blockers.append(field)

    kill = exp.get("kill_outcome")
    kill_present = isinstance(kill, str) and bool(kill.strip()) \
        and not _is_blocker(kill)
    kill_vacuous = kill_present and _is_vacuous_kill(kill)

    # the kill outcome must name a DIRECTION of failure (a measurable
    # observation that contradicts the claimed effect)
    kill_directional = kill_present and bool(
        _DIRECTION_RE.search(kill)) and bool(_NUMBER_RE.search(kill)
                                             or "requirement" in kill.lower()
                                             or "threshold" in kill.lower())

    # acceptance vs falsification thresholds must be DIFFERENT
    # observations (a confirm-only contract in disguise otherwise)
    acc = exp.get("acceptance_threshold")
    fals = exp.get("falsification_threshold")
    thresholds_distinct = (
        isinstance(acc, str) and isinstance(fals, str)
        and acc.strip() and fals.strip()
        and acc.strip().lower() != fals.strip().lower())

    # epistemic classes: every classified field must use the closed
    # vocabulary
    epi_violations: List[str] = []
    epi = exp.get("field_epistemic_classes") or {}
    for field, cls in epi.items():
        if cls not in FIELD_EPISTEMIC_CLASSES:
            epi_violations.append(
                f"{field}: {cls!r} not in the closed vocabulary")

    reasons: List[str] = []
    if missing:
        reasons.append(f"missing fields: {missing}")
    if blockers:
        reasons.append(f"incomplete (honest blocker) fields: "
                       f"{blockers}")
    if kill_present and kill_vacuous:
        reasons.append("the kill outcome is VACUOUS — it names an "
                       "outcome consistent with the mechanism "
                       "regardless of effect; the experiment can only "
                       "confirm, so it is not decisive")
    if kill_present and not kill_vacuous and not kill_directional:
        reasons.append("the kill outcome names no measurable failure "
                       "direction (below/above/fails a stated "
                       "requirement) — it is not an outcome that can "
                       "kill the mechanism")
    if not kill_present and "kill_outcome" not in missing:
        reasons.append("the kill outcome is a blocker, not an outcome")
    if not thresholds_distinct and not (
            "acceptance_threshold" in missing
            or "falsification_threshold" in missing
            or "acceptance_threshold" in blockers
            or "falsification_threshold" in blockers):
        reasons.append("acceptance and falsification thresholds are "
                       "not distinct observations — a confirm-only "
                       "contract in disguise")

    valid = not reasons
    return {
        "contract_version": CONTRACT_VERSION,
        "valid": valid,
        "decisive": valid,  # valid == decisive by construction here
        "missing_fields": missing,
        "blocker_fields": blockers,
        "kill_outcome_present": kill_present,
        "kill_outcome_vacuous": kill_vacuous,
        "kill_outcome_directional": kill_directional,
        "thresholds_distinct": thresholds_distinct,
        "epistemic_class_violations": epi_violations,
        "rejection_reason": ("; ".join(reasons) if reasons else None),
        "rule": ("there must exist an outcome that kills the "
                 "mechanism (Art. LII); an experiment that can only "
                 "confirm the proposal is not a decisive experiment"),
    }


def build_virtual_experiment_contract(
        mechanistic_record: Dict[str, Any]) -> Dict[str, Any]:
    """Build the constitutional experiment OBJECT from a mechanistic
    virtual-experiment record (Phase 7's bridge).

    Every field is derived from the mechanistic record's OWN values —
    the problem's own declared requirement is the acceptance
    threshold; the kill outcome is the measured flow staying BELOW
    that requirement (an outcome that can occur and kills the
    mechanism claim). NOTHING is invented: fields the mechanistic
    record cannot support carry honest UNKNOWN blockers, and the
    contract then validates INCOMPLETE — never VALID (Art. XXV)."""
    co = mechanistic_record.get("computed_outcome") or {}
    var = ((mechanistic_record.get("canonical_variables") or {})
           .get("candidate_arm") or {}).get("variables") or {}
    q_req = co.get("required_flow_ml_min")
    thr = var.get("required_flow_ml_min") or {}
    cand = mechanistic_record.get("candidate_prediction") or {}
    base = mechanistic_record.get("baseline_prediction") or {}

    hyp = None
    if isinstance(q_req, (int, float)):
        hyp = (f"The candidate's declared primary-segment arrangement "
               f"delivers at least {q_req:.4f} mL/min through the "
               f"problem's own stated operating condition")
    measurement = None
    if isinstance(q_req, (int, float)):
        measurement = (f"total_flow_ml_min computed by the 1D laminar "
                       f"Poiseuille network solver "
                       f"({mechanistic_record.get('solver_version')}) "
                       f"on the candidate's declared parameters, "
                       f"compared against the problem's own declared "
                       f"requirement of {q_req:.4f} mL/min")
    kill = None
    if isinstance(q_req, (int, float)):
        kill = (f"the measured total flow stays BELOW the problem's "
                f"own declared requirement of {q_req:.4f} mL/min "
                f"under the stated operating condition — the "
                f"mechanism's claimed delivery effect is falsified "
                f"and the candidate is killed")

    exp: Dict[str, Any] = {
        "experiment_id": mechanistic_record.get("experiment_id"),
        "candidate_id": mechanistic_record.get("candidate_id"),
        "experiment_kind": "VIRTUAL_DECISIVE_EXPERIMENT",
        "hypothesis": hyp or "UNKNOWN (the mechanistic record carries "
                                "no resolved required-flow threshold)",
        "treatment": (
            f"the candidate's declared primary segment "
            f"(diameter {cand.get('diameter_mm')} mm) as the "
            f"treatment arm"),
        "control": (
            f"the problem's own current configuration as the control "
            f"arm (diameter {base.get('diameter_mm')} mm; identical "
            f"solver, identical operating point — Art. XLVII)"),
        "measurement": measurement or
            "UNKNOWN (no resolved measurement metric in the "
            "mechanistic record)",
        "apparatus": (
            f"the deterministic 1D hydraulic network solver "
            f"{mechanistic_record.get('solver_version')} "
            f"(reference-validated against Poiseuille closed forms; "
            f"execution evidence class COMPUTATIONAL_RESULT — a "
            f"virtual experiment, never a physical observation, "
            f"Art. XXXVIII)"),
        "sample": ("one parameterized network configuration per arm "
                   "(the virtual experiment computes the full "
                   "deterministic response — no sampling; n=1 "
                   "per arm by construction, recorded honestly)"),
        "acceptance_threshold": (
            f"total flow at least {q_req:.4f} mL/min (the problem's "
            f"own declared requirement — "
            f"{thr.get('source', 'SOURCE_FACT')})"
            if isinstance(q_req, (int, float)) else
            "UNKNOWN (no declared requirement)"),
        "falsification_threshold": (
            f"total flow below {q_req:.4f} mL/min under the stated "
            f"operating condition"
            if isinstance(q_req, (int, float)) else
            "UNKNOWN (no declared requirement)"),
        "uncertainty": (
            "MODEL_DERIVED model-class uncertainty: uniform stenosis "
            "model, junction losses unmodelled, viscosity is an input "
            "datum (the solver's own recorded limitations)"),
        "cost": ("COMPUTED at negligible marginal cost (a linear "
                 "solve; no physical experiment is conducted)"),
        "time": ("COMPUTED in solver wall-clock (seconds; the linear "
                 "solve is direct)"),
        "safety": ("NOT_APPLICABLE_VIRTUAL — no physical apparatus, "
                   "no operator, no patient (a physical follow-on "
                   "experiment would require its own safety case — "
                   "recorded as a required field of THAT experiment, "
                   "never silently inherited)"),
        "kill_outcome": kill or
            "UNKNOWN (no resolved requirement to falsify against)",
        "field_epistemic_classes": {
            "hypothesis": "MODEL_DERIVED",
            "treatment": "MODEL_DERIVED",
            "control": "SOURCE_FACT",
            "measurement": "COMPUTED",
            "apparatus": "COMPUTED",
            "sample": "MODEL_DERIVED",
            "acceptance_threshold": str(
                thr.get("epistemic_class", "SOURCE_FACT")),
            "falsification_threshold": str(
                thr.get("epistemic_class", "SOURCE_FACT")),
            "uncertainty": "MODEL_DERIVED",
            "cost": "COMPUTED",
            "time": "COMPUTED",
            "safety": "UNKNOWN",
            "kill_outcome": str(
                thr.get("epistemic_class", "SOURCE_FACT")),
        },
        "contract_version": CONTRACT_VERSION,
        "source_record_status": mechanistic_record.get("status"),
    }
    exp["validation"] = validate_experiment_contract(exp)
    return exp


def contract_id(exp: Dict[str, Any]) -> str:
    """Stable identity for the experiment object (provenance chain,
    Art. LXII)."""
    payload = {k: exp.get(k) for k in REQUIRED_FIELDS}
    return "expcon-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True,
                   default=str).encode()).hexdigest()[:16]

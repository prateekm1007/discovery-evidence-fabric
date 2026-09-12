"""Toscanini Visual Feedback Layer — canonical trajectory projection (R450-C2).

Coder 2 boundary (operator directive R450-C2): the visual layer PRESENTS and
INTERROGATES the engineering truth Coder 1 establishes. It never owns it.

    visual presentation is not engineering validation.

The projection consumes ONLY canonical state (the engine's
INVENTION_LINEAGE.json evolution records — Coder 1's improvement loop) and
produces a deterministic presentation record for the trajectory viewer:

    V1 -> FAILURE -> CAUSE -> DIRECTION -> MUTATION -> V2 -> MEASURED CHANGE

Every element carries an epistemic badge derived fail-closed from the
element's OWN provenance fields (Art. III — the verifier never trusts the
claimant); unknown stays unknown (Art. XXV); no physics is interpreted
here (Art. XXVIII — no silent semantic promotion); the lineage's own
INVENTION_* status vocabulary is carried VERBATIM and never re-labeled
(Art. X; the R433 projection discipline).

Determinism contract: the same canonical lineage bytes project to the
byte-identical trajectory record (no timestamps, no generated ids, sorted
keys) — the visual regression battery holds this mechanically.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# The five-class epistemic badge vocabulary (operator directive R450-C2 §8).
#
# Constitutional mapping (EPISTEMIC_CONSTITUTION.md v2.4.0):
#   MEASURED    = PHYSICAL_OBSERVATION (Art. XXXVIII layer 5) — requires an
#                 R370G-shaped REALITY_EVENT (event_id + raw_data_sha256 +
#                 attestation + custody). Nothing else is ever MEASURED.
#   SIMULATED   = COMPUTATIONAL_RESULT (Art. XXXVIII layer 4) — requires a
#                 computation record (named instrument + deterministic basis
#                 and/or input/output hashes).
#   INFERRED    = AI_INFERENCE / engine determination (layer 3) — a recorded
#                 determination with an explicit basis and method identity.
#   PROPOSED    = model-proposed CONTENT (Art. XVIII) — never evidence.
#   UNVERIFIED  = unknown / unproven (Art. XXV) — the fail-closed floor.
# ---------------------------------------------------------------------------

TRAJECTORY_SCHEMA_ID = "TOSCANINI_TRAJECTORY"
TRAJECTORY_SCHEMA_VERSION = "1.0.0"

BADGE_MEASURED = "MEASURED"
BADGE_SIMULATED = "SIMULATED"
BADGE_INFERRED = "INFERRED"
BADGE_PROPOSED = "PROPOSED"
BADGE_UNVERIFIED = "UNVERIFIED"

EPISTEMIC_BADGES = (
    BADGE_MEASURED,
    BADGE_SIMULATED,
    BADGE_INFERRED,
    BADGE_PROPOSED,
    BADGE_UNVERIFIED,
)

# The closed set of prediction-outcome values. Absent evaluation is
# NOT_EVALUATED — never "held" (Art. XXV: unknown must remain unknown).
PREDICTION_HELD = "HELD"
PREDICTION_REFUTED = "REFUTED"
PREDICTION_INDETERMINATE = "INDETERMINATE"
PREDICTION_NOT_EVALUATED = "NOT_EVALUATED"
PREDICTION_OUTCOMES = (
    PREDICTION_HELD,
    PREDICTION_REFUTED,
    PREDICTION_INDETERMINATE,
    PREDICTION_NOT_EVALUATED,
)

# R370G REALITY_EVENT fields required before ANY element may badge MEASURED.
_MEASURED_REQUIRED_FIELDS = (
    "event_id",
    "raw_data_sha256",
    "attestation",
)


class TrajectoryProjectionError(Exception):
    """Raised when a canonical record cannot be projected honestly."""


# ---------------------------------------------------------------------------
# Deterministic serialization
# ---------------------------------------------------------------------------

def canonical_json(record: Any) -> str:
    """Byte-stable JSON for hashing and byte-equality regression checks."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def record_sha256(record: Any) -> str:
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Badge derivation — Art. III: the verifier never trusts the claimant.
# The badge is derived from the element's OWN provenance FIELDS, never from
# a claimed label. Claimed-but-unproven degrades to UNVERIFIED, never up.
# ---------------------------------------------------------------------------

def _attestation_ok(attestation: Any) -> bool:
    if isinstance(attestation, dict):
        return bool(attestation.get("attestation_hash")
                    or attestation.get("attestation_text"))
    return isinstance(attestation, str) and bool(attestation.strip())


def derive_badge(provenance: Optional[Dict[str, Any]]) -> str:
    """Derive the epistemic badge from provenance fields. Fail closed.

    Order: MEASURED proof -> SIMULATED proof -> INFERRED proof ->
    PROPOSED proof -> UNVERIFIED. A record that claims a higher class
    without its required fields falls through to the lower class it CAN
    prove, floor UNVERIFIED.
    """
    p = provenance or {}
    if not isinstance(p, dict):
        return BADGE_UNVERIFIED

    # 1. MEASURED — R370G-shaped event only (Art. XXXVIII).
    ev = p.get("event")
    if isinstance(ev, dict):
        if all(ev.get(f) for f in _MEASURED_REQUIRED_FIELDS) \
                and _attestation_ok(ev.get("attestation")):
            return BADGE_MEASURED

    # 2. SIMULATED — named computation instrument with a deterministic
    #    basis and/or recorded input/output hashes.
    comp = p.get("computation")
    if isinstance(comp, dict):
        has_instrument = bool(comp.get("instrument") or comp.get("evaluator")
                              or comp.get("solver"))
        has_basis = bool(comp.get("basis") or comp.get("inputs_sha256")
                         or comp.get("output_sha256")
                         or comp.get("instrument_version"))
        if has_instrument and has_basis:
            return BADGE_SIMULATED

    # 3. INFERRED — a recorded determination with an explicit basis and
    #    method identity (e.g. evolution.diagnose_from_generation/1.0.0).
    inf = p.get("inference")
    if isinstance(inf, dict):
        if (inf.get("basis") or inf.get("bases")) and \
                (inf.get("method") or inf.get("diagnosed_by")
                 or inf.get("adjudicator")):
            return BADGE_INFERRED

    # 4. PROPOSED — model-proposed content with proposal provenance
    #    (Art. XVIII: content, never evidence).
    prop = p.get("proposal")
    if isinstance(prop, dict):
        if prop.get("provider") or prop.get("model") or prop.get("output_hash"):
            return BADGE_PROPOSED

    return BADGE_UNVERIFIED


# ---------------------------------------------------------------------------
# Lineage projection
# ---------------------------------------------------------------------------

def _truncate(value: Any, limit: int = 400) -> str:
    return "" if value is None else str(value)[:limit]


def _uncertainty_text(ch: Dict[str, Any]) -> Optional[str]:
    """The uncertainty label: the recorded text verbatim; when the lineage
    records SURVIVED_WITH_UNCERTAINTIES without itemizing them, the honest
    absence is RENDERED (an explicit not-itemized label) rather than left
    for the user to infer from prose (Art. XXV: unknown stays unknown, but
    visibly so)."""
    text = _truncate(ch.get("uncertainties"), 300)
    if text:
        return text
    if ch.get("attack_overall") == "SURVIVED_WITH_UNCERTAINTIES":
        return ("uncertainties recorded as present but not itemized in "
                "the lineage record")
    return None


def _failure_element(gen: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The FAILURE element: the generation's recorded challenge verdict,
    verbatim from the lineage (the projection never invents a verdict)."""
    ch = gen.get("challenge") or {}
    if not isinstance(ch, dict) or not ch:
        return None
    killed = ch.get("killed")
    if killed is None and not ch.get("kill_reason") \
            and not ch.get("attack_overall"):
        return None
    return {
        "kind": "FAILURE",
        "killed": bool(killed),
        "kill_reason": _truncate(ch.get("kill_reason"), 300) or None,
        "attack_overall": ch.get("attack_overall"),
        "final_status": ch.get("final_status"),
        "evidence_verified": ch.get("evidence_verified"),
        "uncertainties": _uncertainty_text(ch),
        "survived_with_uncertainties": (
            ch.get("attack_overall") == "SURVIVED_WITH_UNCERTAINTIES"),
        # a challenge verdict is the system's own verification
        # determination: badge derived from its recorded basis fields
        "epistemic_badge": derive_badge({"inference": {
            "basis": (ch.get("kill_reason") or ch.get("attack_overall")),
            "method": "engine challenge record (lineage verdict)",
        }}) if ch.get("kill_reason") or ch.get("attack_overall")
            else BADGE_UNVERIFIED,
    }


def _cause_element(gen: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The CAUSE element: the recorded diagnosis, verbatim."""
    diag = gen.get("diagnosis") or {}
    if not isinstance(diag, dict) or not diag:
        return None
    cause = diag.get("cause")
    basis = diag.get("basis")
    if cause is None and not basis:
        return None
    return {
        "kind": "CAUSE",
        "cause": _truncate(cause, 200) or None,
        "basis": [_truncate(b, 300) for b in basis] if isinstance(basis, list)
                 else (_truncate(basis, 300) or None),
        "infrastructure_class": bool(diag.get("infrastructure_class")),
        "diagnosed_by": diag.get("diagnosed_by"),
        "epistemic_badge": derive_badge({"inference": {
            "basis": basis or cause,
            "method": diag.get("diagnosed_by"),
        }}),
    }


def _direction_element(gen: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The DIRECTION element: the recorded causal change the mutation
    intends (the engine's stated direction — content, never evidence)."""
    cd = gen.get("causal_delta")
    if not isinstance(cd, dict):
        return None
    causal_change = cd.get("causal_change") or gen.get("change_delta")
    if not causal_change:
        return None
    return {
        "kind": "DIRECTION",
        "failure_or_challenge": _truncate(cd.get("failure_or_challenge"),
                                          300) or None,
        "diagnosed_cause": _truncate(cd.get("diagnosed_cause"), 200) or None,
        "causal_change": _truncate(causal_change),
        "transferred_capability": _truncate(
            gen.get("reason_for_change"), 400) or None,
        # the stated direction is the engine's PROPOSAL for what the
        # mutation should cause — never itself a measurement
        "epistemic_badge": BADGE_PROPOSED,
    }


def _mutation_element(gen: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The MUTATION element. Two canonical shapes exist:

    1. R378 improvement-engine `mutation.changed` — a structured
       {field: {before, after}} map -> the BEFORE/AFTER/DELTA table.
    2. The evolution lineage's change_delta narrative -> rendered
       verbatim, labeled narrative (never presented as a structured
       engineering delta).
    """
    mut = gen.get("mutation")
    if isinstance(mut, dict):
        changed = mut.get("changed")
        if isinstance(changed, dict) and changed:
            fields = []
            for name in sorted(changed):
                ch = changed[name] or {}
                fields.append({
                    "field": name,
                    "before": _truncate(ch.get("before")),
                    "after": _truncate(ch.get("after")),
                    "changed": _truncate(ch.get("before")) !=
                               _truncate(ch.get("after")),
                })
            return {
                "kind": "MUTATION",
                "shape": "STRUCTURED",
                "mutation_type": mut.get("mutation_type"),
                "mutation_id": mut.get("mutation_id"),
                "fields": fields,
                "diagnostic_trigger": mut.get("diagnostic_trigger") or None,
                "epistemic_badge": BADGE_PROPOSED,
            }
    delta = gen.get("change_delta")
    if delta:
        return {
            "kind": "MUTATION",
            "shape": "NARRATIVE",
            "change_delta": _truncate(delta),
            "epistemic_badge": BADGE_PROPOSED,
        }
    return None


def _prediction_element(gen: Dict[str, Any],
                        child: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The PREDICTION element: what the mutation predicted (expected
    effect / falsification test, when the lineage records them) and
    whether the outcome was evaluated. Fail closed: absent evaluation is
    NOT_EVALUATED — never 'held' (Art. XXV)."""
    mech = (gen.get("invention_spec") or {}) if \
        isinstance(gen.get("invention_spec"), dict) else {}
    expected = (mech.get("expected_effect")
                or gen.get("expected_effect"))
    falsifies = (mech.get("falsification_test")
                 or gen.get("falsification_test"))
    evaluation = gen.get("evaluation") or gen.get("re_evaluation") \
        or gen.get("keep_or_kill")
    outcome = PREDICTION_NOT_EVALUATED
    if isinstance(evaluation, dict):
        verdict = evaluation.get("verdict") or evaluation.get("outcome") \
            or evaluation.get("kept")
        if verdict in ("HELD", "REFUTED", "INDETERMINATE"):
            outcome = verdict
        elif verdict is True:
            outcome = PREDICTION_HELD
        elif verdict is False:
            outcome = PREDICTION_REFUTED
    if expected is None and falsifies is None \
            and outcome == PREDICTION_NOT_EVALUATED:
        return None
    return {
        "kind": "PREDICTION",
        "expected_effect": _truncate(expected, 400) or None,
        "falsification_test": _truncate(falsifies, 400) or None,
        "prediction_outcome": outcome,
        # the prediction is MODELLED content; its outcome, when recorded,
        # is the engine's determination (badge below)
        "epistemic_badge": BADGE_PROPOSED if outcome == PREDICTION_NOT_EVALUATED
        else derive_badge({"inference": {
            "basis": f"recorded evaluation verdict {outcome}",
            "method": "lineage evaluation record",
        }}),
    }


def _state_element(gen: Dict[str, Any], current: bool) -> Dict[str, Any]:
    """One V-state: the generation's OWN status vocabulary verbatim
    (INVENTION_*, maturity) plus the fail-closed epistemic badge. The
    state's own challenge context (killed / survived-with-uncertainties)
    rides on the state too: the CURRENT state has no following transition,
    and its uncertainty must still be visible (Art. XXV)."""
    state = gen.get("state")
    if not state:
        raise TrajectoryProjectionError(
            f"generation {gen.get('gen')} carries no state — the lineage's "
            "own vocabulary is the only admissible status source")
    return {
        "kind": "STATE",
        "gen": gen.get("gen"),
        "invention_id": gen.get("invention_id"),
        "status": state,               # verbatim INVENTION_* vocabulary
        "maturity": gen.get("maturity"),  # verbatim maturity ladder
        "origin": gen.get("origin"),
        "current": bool(current),
        # the state's own recorded challenge context (None -> honest absence)
        "challenge": _failure_element(gen),
        # the state verdict is the engine's determination from its
        # recorded challenge/adjudication chain
        "epistemic_badge": derive_badge({"inference": {
            "basis": f"lineage state {state} with recorded challenge chain",
            "method": "engine evolution lineage (Coder 1 canonical)",
        }}),
    }


def project_trajectory(lineage: Dict[str, Any]) -> Dict[str, Any]:
    """Project a canonical INVENTION_LINEAGE record into the deterministic
    presentation trajectory. Pure function; adds NO timestamps, ids, or
    narrative absent from the lineage; re-labels nothing."""
    if not isinstance(lineage, dict):
        raise TrajectoryProjectionError("lineage must be a dict")
    schema = lineage.get("schema")
    if not (isinstance(schema, str) and schema.startswith("INVENTION_LINEAGE")):
        raise TrajectoryProjectionError(
            f"not an INVENTION_LINEAGE record (schema={schema!r})")
    generations = lineage.get("generations")
    if not isinstance(generations, list) or not generations:
        raise TrajectoryProjectionError(
            "lineage carries no generations — an empty trajectory is not "
            "projected (honest absence is the caller's to render)")

    n = len(generations)
    states: List[Dict[str, Any]] = []
    transitions: List[Dict[str, Any]] = []
    for i, gen in enumerate(generations):
        if not isinstance(gen, dict):
            raise TrajectoryProjectionError(
                f"generation index {i} is not a dict")
        current = (i == n - 1)
        states.append(_state_element(gen, current))
        if i == 0:
            continue
        parent = generations[i - 1]
        transitions.append({
            "kind": "TRANSITION",
            "from_gen": parent.get("gen"),
            "to_gen": gen.get("gen"),
            "failure": _failure_element(parent),
            "cause": _cause_element(parent),
            "direction": _direction_element(gen),
            "mutation": _mutation_element(gen),
            "prediction": _prediction_element(gen, gen),
            "result": {
                "gen": gen.get("gen"),
                "status": gen.get("state"),
                "maturity": gen.get("maturity"),
                "epistemic_badge": derive_badge({"inference": {
                    "basis": f"lineage state {gen.get('state')}",
                    "method": "engine evolution lineage (Coder 1 canonical)",
                }}),
            },
            # the UPDATE: what the loop learned, verbatim from the lineage
            "update": {
                "stop_reason_impact": None,  # filled below from the summary
                "superseded": True,
            },
        })

    stop_reason = lineage.get("stop_reason")
    if transitions and stop_reason:
        transitions[-1]["update"] = {
            "stop_reason": stop_reason,
            "survivor_reached": bool(lineage.get("survivor_reached")),
            "superseded": False,
        }

    current_invention = lineage.get("current_invention") or {}
    record: Dict[str, Any] = {
        "schema": f"{TRAJECTORY_SCHEMA_ID}/{TRAJECTORY_SCHEMA_VERSION}",
        "trajectory_id": f"trajectory:{record_sha256(lineage)[:16]}",
        "source": {
            "kind": "INVENTION_LINEAGE",
            "lineage_schema": schema,
            "lineage_sha256": record_sha256(lineage),
            "run_id": lineage.get("run_id"),
            "authority": "coder1:engineering (Art. X — one canonical state)",
        },
        "epistemic_boundary": (
            "visual presentation is not engineering validation; every "
            "physical claim originates from the engineering/evaluation "
            "state (R450-C2; Arts. XXVIII/LXXII)"),
        "badge_vocabulary": list(EPISTEMIC_BADGES),
        "stop_reason": stop_reason,
        "n_generations": n,
        "current_invention": {
            "gen": current_invention.get("gen"),
            "invention_id": current_invention.get("invention_id"),
            "status": current_invention.get("status"),
            "maturity": current_invention.get("maturity"),
        },
        "states": states,
        "transitions": transitions,
    }
    return record


# ---------------------------------------------------------------------------
# Sensitivity projection — rendered ONLY when Coder 1 supplies a legitimate
# sensitivity result. The visual layer calculates nothing and interprets
# nothing: values pass through verbatim; the declared basis is rendered
# with its badge; a record without a declared basis is REFUSED (fail
# closed) rather than silently presented (Art. XXVII — no threshold
# invention; the viewer must never manufacture scientific interpretation).
# ---------------------------------------------------------------------------

_SENSITIVITY_BASES = ("MEASURED", "SIMULATED", "MODELLED")


def project_sensitivity(record: Dict[str, Any]) -> Dict[str, Any]:
    """Project a Coder-1-supplied parameter-sensitivity result.

    Required shape:
        {
          "parameter": <name>,
          "basis": "MEASURED" | "SIMULATED" | "MODELLED",
          "provenance": {...badge-derivable fields...},
          "objective": <objective name>,
          "points": [{"value": ..., "objective": ...}, ...]
        }
    """
    if not isinstance(record, dict):
        raise TrajectoryProjectionError("sensitivity record must be a dict")
    parameter = record.get("parameter")
    basis = record.get("basis")
    points = record.get("points")
    if not parameter:
        raise TrajectoryProjectionError(
            "sensitivity record without a parameter name is refused "
            "(fail closed)")
    if basis not in _SENSITIVITY_BASES:
        raise TrajectoryProjectionError(
            f"sensitivity record without a declared basis "
            f"({_SENSITIVITY_BASES}) is refused (fail closed — the viewer "
            "never invents scientific provenance)")
    if not isinstance(points, list) or len(points) < 2:
        raise TrajectoryProjectionError(
            "sensitivity record needs >= 2 (value, objective) points")
    clean_points = []
    for pt in points:
        if not isinstance(pt, dict) or "value" not in pt \
                or "objective" not in pt:
            raise TrajectoryProjectionError(
                "sensitivity point missing 'value'/'objective' is refused")
        clean_points.append({"value": pt["value"],
                             "objective": pt["objective"]})

    badge = derive_badge(record.get("provenance"))
    if badge == BADGE_MEASURED and basis != "MEASURED":
        raise TrajectoryProjectionError(
            "MEASURED badge requires a MEASURED-declared basis")
    if basis == "MEASURED" and badge != BADGE_MEASURED:
        # claimed-measured without an R370G event: degrade, never spoof
        badge = BADGE_UNVERIFIED
    if basis == "SIMULATED" and badge == BADGE_MEASURED:
        badge = BADGE_SIMULATED
    if basis == "MODELLED" and badge in (BADGE_MEASURED, BADGE_SIMULATED):
        badge = BADGE_PROPOSED

    return {
        "schema": "TOSCANINI_SENSITIVITY/1.0.0",
        "parameter": parameter,
        "objective": _truncate(record.get("objective"), 200) or None,
        "basis": basis,
        "epistemic_badge": badge,
        "points": clean_points,
        "note": ("values rendered verbatim from the supplied record; the "
                 "visual layer calculates and interprets nothing"),
    }

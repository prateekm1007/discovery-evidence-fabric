"""Toscanini Visual Feedback Layer — trajectory guard (R450-C2).

Machine enforcement of the operator's absolute boundary for the trajectory
viewer, extending the R448 epistemic guard to the trajectory surface:

  1. visual presentation is not engineering validation.
  2. An AI-generated mesh is NEVER engineering truth (Art. LXXII —
     CadQuery/OCCT stays the geometry authority).
  3. No element may claim MEASURED without an R370G-shaped event
     (Art. XXXVIII — AI may not claim that reality happened).
  4. Uncertain state must carry its uncertainty label visibly (Art. XXV —
     unknown stays unknown); a beautiful render marked validated is the
     exact failure this guard exists to prevent.
  5. The lineage's own INVENTION_* vocabulary is carried verbatim — the
     projection never re-labels or invents a verdict (Art. X).

Every check fails closed: ambiguity, missing provenance, or an unknown
value is a violation, never a warning (Art. IV/V).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Path-robust import of the projection schema (the guard and the schema
# live in sibling packages; the batteries run both flat and packaged).
_LAB_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_LAB_ROOT / "trajectory"), str(_LAB_ROOT / "guard")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:  # packaged import
    from ..trajectory.schema import (  # type: ignore
        BADGE_INFERRED,
        BADGE_MEASURED,
        BADGE_PROPOSED,
        BADGE_SIMULATED,
        BADGE_UNVERIFIED,
        EPISTEMIC_BADGES,
        PREDICTION_NOT_EVALUATED,
        PREDICTION_OUTCOMES,
        TRAJECTORY_SCHEMA_ID,
    )
except ImportError:  # flat battery import (house direct-run style)
    from schema import (  # type: ignore
        BADGE_INFERRED,
        BADGE_MEASURED,
        BADGE_PROPOSED,
        BADGE_SIMULATED,
        BADGE_UNVERIFIED,
        EPISTEMIC_BADGES,
        PREDICTION_NOT_EVALUATED,
        PREDICTION_OUTCOMES,
        TRAJECTORY_SCHEMA_ID,
    )

# The ONLY generator identity permitted to emit engineering geometry
# (shared with the R448 guard — one authority, one vocabulary).
ENGINEERING_AUTHORITY_GENERATOR = "coder1:cad"

_MEASURED_REQUIRED_FIELDS = ("event_id", "raw_data_sha256", "attestation")

# Element kinds every transition must be able to name (a present-but-empty
# element is rendered as an honest absence — never fabricated).
TRANSITION_KINDS = ("FAILURE", "CAUSE", "DIRECTION", "MUTATION", "RESULT",
                    "UPDATE")


class TrajectoryViolation(Exception):
    """Raised whenever a trajectory record violates the epistemic boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TrajectoryViolation(message)


def _attestation_ok(attestation: Any) -> bool:
    if isinstance(attestation, dict):
        return bool(attestation.get("attestation_hash")
                    or attestation.get("attestation_text"))
    return isinstance(attestation, str) and bool(attestation.strip())


def validate_trajectory_projection(traj: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a projected trajectory record. Returns a summary dict on
    success; raises TrajectoryViolation on the first violated boundary.

    This is the engineering-vs-presentation guard for the trajectory
    surface: the viewer may render whatever passes here, and nothing
    that fails here may render as an engineering truth.
    """
    _require(isinstance(traj, dict), "trajectory record must be a dict")
    schema = traj.get("schema")
    _require(isinstance(schema, str)
             and schema.startswith(f"{TRAJECTORY_SCHEMA_ID}/"),
             f"unknown trajectory schema {schema!r} (fail closed)")
    _require(traj.get("epistemic_boundary") is not None,
             "trajectory record without the epistemic boundary statement is "
             "refused — the presentation/validation distinction must be "
             "carried on the record itself")

    badges = traj.get("badge_vocabulary")
    _require(isinstance(badges, list) and set(badges) == set(EPISTEMIC_BADGES),
             "badge vocabulary must be the fixed five-class set")

    states = traj.get("states")
    _require(isinstance(states, list) and bool(states),
             "trajectory without states is refused (honest absence is "
             "rendered by NOT emitting the panel, not by an empty shell)")

    seen_gens = []
    current_count = 0
    for st in states:
        _require(isinstance(st, dict), "state element must be a dict")
        gen = st.get("gen")
        _require(gen is not None, "state element without a generation index")
        seen_gens.append(gen)
        # the status vocabulary must be the lineage's own — verbatim
        status = st.get("status")
        _require(isinstance(status, str) and status.startswith("INVENTION_"),
                 f"state {gen}: status {status!r} is not the lineage's "
                 "INVENTION_* vocabulary — re-labeling the canonical state "
                 "vocabulary is a silent semantic promotion (Art. XXVIII)")
        _badge_ok(st, f"state {gen}")
        if isinstance(st.get("challenge"), dict):
            _badge_ok(st["challenge"], f"state {gen} challenge")
        if st.get("current"):
            current_count += 1
    _require(current_count == 1,
             f"exactly one CURRENT state required, found {current_count}")
    _require(seen_gens == sorted(seen_gens),
             "trajectory state ordering must preserve the lineage's "
             "generation order (same trajectory -> same state ordering)")

    transitions = traj.get("transitions") or []
    _require(len(transitions) == max(0, len(states) - 1),
             "one transition per adjacent state pair required")
    for tr in transitions:
        _require(isinstance(tr, dict), "transition must be a dict")
        label = f"transition {tr.get('from_gen')}->{tr.get('to_gen')}"
        for kind in ("failure", "cause", "direction", "mutation", "prediction"):
            el = tr.get(kind)
            if el is None:
                continue  # honest absence
            _require(isinstance(el, dict), f"{label}: {kind} must be a dict")
            if el is not None and el.get("kind"):
                _require(el["kind"] == kind.upper(),
                         f"{label}: {kind} element mislabeled "
                         f"{el['kind']!r}")
            _badge_ok(el, f"{label} {kind}")
        result = tr.get("result")
        _require(isinstance(result, dict) and result.get("status"),
                 f"{label}: result must carry the child's verbatim status")
        _badge_ok(result, f"{label} result")
        pred = tr.get("prediction")
        if isinstance(pred, dict):
            outcome = pred.get("prediction_outcome")
            _require(outcome in PREDICTION_OUTCOMES,
                     f"{label}: prediction_outcome {outcome!r} outside the "
                     "closed set — absent evaluation is NOT_EVALUATED, "
                     "never 'held' (Art. XXV)")
            if outcome != PREDICTION_NOT_EVALUATED:
                _require(pred.get("epistemic_badge") in
                         (BADGE_INFERRED, BADGE_MEASURED),
                         f"{label}: a recorded prediction outcome must be "
                         "badge INFERRED (or MEASURED with an event), never "
                         "PROPOSED — a proposed outcome is unevaluated")

    _require(isinstance(traj.get("source"), dict)
             and traj["source"].get("lineage_sha256"),
             "trajectory must cite its canonical source lineage hash "
             "(provenance custody, Art. XII)")

    return {
        "trajectory_id": traj.get("trajectory_id"),
        "n_states": len(states),
        "n_transitions": len(transitions),
        "violations": 0,
        "verdict": "PASS",
    }


def _badge_ok(element: Dict[str, Any], where: str) -> None:
    badge = element.get("epistemic_badge")
    _require(badge in EPISTEMIC_BADGES,
             f"{where}: epistemic badge {badge!r} outside the five-class "
             "vocabulary (fail closed)")
    if badge == BADGE_MEASURED:
        event = (element.get("provenance") or {}).get("event") \
            if isinstance(element.get("provenance"), dict) else None
        _require(isinstance(event, dict)
                 and all(event.get(f) for f in _MEASURED_REQUIRED_FIELDS)
                 and _attestation_ok(event.get("attestation")),
                 f"{where}: MEASURED badge without an R370G-shaped event "
                 "(event_id + raw_data_sha256 + attestation) — AI may not "
                 "claim reality happened (Art. XXXVIII)")
    if element.get("survived_with_uncertainties"):
        _require(bool(element.get("uncertainties")),
                 f"{where}: SURVIVED_WITH_UNCERTAINTIES without the "
                 "uncertainties carried verbatim — the uncertainty label "
                 "must be visible (Art. XXV)")


def check_generation_geometry_authority(gen_artifacts: Dict[str, Any],
                                        lineage_root_sha256: Optional[str]
                                        ) -> None:
    """A generation's geometry artifact may only be presented as
    ENGINEERING_GEOMETRY when its lineage root is the canonical geometry
    authority (Coder 1). An AI-generated / lab mesh can ride the
    trajectory ONLY as a presentation candidate — never as engineering
    truth (operator directive R450-C2 §2; Art. LXXII)."""
    _require(isinstance(gen_artifacts, dict),
             "generation artifacts must be a dict")
    for name, artifact in gen_artifacts.items():
        if not isinstance(artifact, dict):
            continue
        cls = artifact.get("epistemic_class")
        if cls is None:
            continue
        if cls == "ENGINEERING_GEOMETRY":
            _require(
                artifact.get("generator") == ENGINEERING_AUTHORITY_GENERATOR,
                f"artifact {name}: ENGINEERING_GEOMETRY from generator "
                f"{artifact.get('generator')!r} — only {ENGINEERING_AUTHORITY_GENERATOR!r} "
                "may emit engineering geometry (Art. LXXII)")
            _require(
                artifact.get("lineage_root_sha256") == lineage_root_sha256
                and lineage_root_sha256 is not None,
                f"artifact {name}: ENGINEERING_GEOMETRY without a verified "
                "canonical lineage root — unvalidated AI geometry can never "
                "appear as engineering-certified geometry")


def check_no_production_promotion(traj: Dict[str, Any]) -> None:
    """The trajectory surface carries NO promotion claim: a trajectory
    record must not contain production/integration/grandfathering
    vocabulary that would present a lab capability as production truth
    (operator directive R450-C2: no production model integration without
    evidence; the R448 lab stays laboratory/provisional)."""
    def _scan(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                _scan(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                _scan(v, f"{path}[{i}]")
        elif isinstance(node, str):
            lowered = node.lower()
            for banned in ("production-ready", "production ready",
                           "engineering-certified", "engineering certified",
                           "physically validated", "physics validated"):
                _require(banned not in lowered,
                         f"{path}: presentation surface carries the banned "
                         f"claim {banned!r} — visual presentation is not "
                         "engineering validation")

    _scan(traj, "trajectory")

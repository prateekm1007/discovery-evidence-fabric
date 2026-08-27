"""discovery_fabric/engine/learning_loop.py — E13 external learning loop.

Closes the actual AI learning loop (CEO E13):

    BUYER_FEEDBACK / ENGINEER_REVIEW / PHYSICAL_OBSERVATION
        -> REALITY_EVENT validation (reuses the frozen R370G schema gate)
        -> belief update on the candidate hypothesis (deterministic Bayes)
        -> append-only candidate mutation (Art. XXXVIII: no silent mutation)
        -> dossier V2 regeneration via package_factory (same builder chain)
        -> discovery constraint emission for future problem formation

Reality Boundary enforcement (Constitution Art. XXXVIII):
  - Every event is validated by premium_package_factory/gates/
    r370g_reality_event_schema.validate_reality_event BEFORE use. Invalid
    provenance = rejected event, no belief change, explicit record.
  - source_type="AI" is forbidden upstream; a CONTROLLED_REHEARSAL event may
    exercise the machinery but NEVER moves loop_verification_state and its
    dossier output is flagged SYNTHETIC_REHEARSAL=TRUE.
  - REAL_LOOP_VERIFIED stays a DERIVED state; this module never assigns it.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .candidate import sha256_obj, utc_now

REPO_ROOT = Path(__file__).resolve().parents[2]
R370G = REPO_ROOT / "premium_package_factory" / "gates" / \
    "r370g_reality_event_schema.py"


def _load_r370g():
    spec = importlib.util.spec_from_file_location("engine_r370g_schema", R370G)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["engine_r370g_schema"] = mod
    spec.loader.exec_module(mod)
    return mod


# Outcome vocabulary a supported event may carry in `outcome.observation`
SUPPORTS = "SUPPORTS_EXPECTED_EFFECT"
REFUTES = "REFUTES_EXPECTED_EFFECT"
NEUTRAL = "UNINFORMATIVE"

OUTCOMES = (SUPPORTS, REFUTES, NEUTRAL)


def _belief_update(prior: float, outcome: str, strength: float = 1.0
                   ) -> Dict[str, Any]:
    """Deterministic Beta-style posterior update on P(expected effect holds).
    `strength` is the pseudo-count weight of the observation. The PRIOR is
    the loop's MODEL_DERIVED prior; the UPDATE comes only from a validated
    external event (its epistemic class becomes EXPERIMENTALLY_ESTIMATED for
    the observation content — the one thing reality is allowed to do)."""
    if outcome == SUPPORTS:
        alpha_inc, beta_inc = strength, 0.0
    elif outcome == REFUTES:
        alpha_inc, beta_inc = 0.0, strength
    else:
        alpha_inc, beta_inc = 0.0, 0.0
    posterior = (prior + alpha_inc) / (1.0 + alpha_inc + beta_inc)
    return {
        "prior": round(prior, 6),
        "posterior": round(posterior, 6),
        "update": {"alpha_inc": alpha_inc, "beta_inc": beta_inc},
        "prior_epistemic_class": "MODEL_DERIVED",
        "observation_epistemic_class": "EXPERIMENTALLY_ESTIMATED",
        "method": "Beta(1,1)-neutral pseudo-count update; deterministic",
    }


def ingest_external_event(
        event: Dict[str, Any], package_context: Dict[str, Any],
        out_dir: str,
        ledger_path: Optional[str] = None) -> Dict[str, Any]:
    """Process one external event against a package's candidate context.

    package_context: {
        "package_id", "invention_spec": spec dict, "engineering_spec": dict,
        "prior_belief": float, "candidate_envelope_hash": str
    }
    ledger_path: redirect target for the frozen R370G ledger. Production
        code MUST leave this None (events append to the canonical
        REALITY_EVENT_LEDGER.jsonl). Only tests/control-rehearsals redirect,
        so synthetic events can never contaminate the real ledger (Art. VI:
        never manufacture provenance; Art. XXXI lesson codified).
    Returns a full processing record (event validation result, belief update,
    mutation entry, V2 package report or skip reason, constraint emitted).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {
        "processing_id": f"learn:{sha256_obj(event)[:10]}",
        "received_at": utc_now(),
        "package_id": package_context.get("package_id"),
    }

    # 1. Validate through the FROZEN R370G gate (reuse, no re-implementation)
    r370g = _load_r370g()
    valid, errors = r370g.validate_reality_event(dict(event))
    record["event_validation"] = {
        "valid": bool(valid),
        "errors": [str(e) for e in (errors or [])],
        "event_type": event.get("event_type"),
        "source_type": event.get("source_type"),
        "event_id": event.get("event_id")}
    if not valid:
        record["action"] = "REJECTED_INVALID_EVENT"
        record["belief_changed"] = False
        (out / f"{record['processing_id']}_REJECTED.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False))
        return record

    # 2. Record the event in the frozen ledger (append-only, same code path
    #    as the portfolio's reality loop). ledger_path redirect is for
    #    tests/rehearsals ONLY (default None = canonical ledger).
    try:
        if ledger_path:
            original = r370g.REALITY_EVENT_LEDGER_PATH
            r370g.REALITY_EVENT_LEDGER_PATH = ledger_path
        try:
            r370g.record_reality_event(dict(event))
            record["ledger_appended"] = True
            record["ledger_path_used"] = (ledger_path or
                                          "CANONICAL_REALITY_EVENT_LEDGER")
        finally:
            if ledger_path:
                r370g.REALITY_EVENT_LEDGER_PATH = original
    except Exception as exc:  # noqa: BLE001 — recorded, never fatal
        record["ledger_appended"] = False
        record["ledger_error"] = f"{type(exc).__name__}: {exc}"

    rehearsal = event.get("source_type") == "CONTROLLED_REHEARSAL"

    # 3. Belief update — only informative, human/instrument/system events
    outcome = (event.get("outcome") or {}).get("observation", NEUTRAL)
    if outcome not in OUTCOMES:
        outcome = NEUTRAL
    prior = float(package_context.get("prior_belief", 0.6))
    update = _belief_update(prior, outcome)
    record["belief_update"] = update
    record["belief_changed"] = (abs(update["posterior"] - prior) > 1e-12)

    # 4. Append-only mutation entry (Art. XXXVIII causal mutation fields)
    mutation = {
        "mutation_id": f"mut:{record['processing_id']}",
        "before_hash": sha256_obj({"belief": prior,
                                   "envelope": package_context.get(
                                       "candidate_envelope_hash")}),
        "after_hash": sha256_obj({"belief": update["posterior"],
                                  "envelope": package_context.get(
                                      "candidate_envelope_hash")}),
        "trigger_event_id": event.get("event_id"),
        "reason": f"external {event.get('event_type')} outcome={outcome}",
        "timestamp": utc_now(),
    }
    record["candidate_mutation"] = mutation
    _append_jsonl(out / "CANDIDATE_MUTATION_LEDGER.jsonl", mutation)

    # 5. Discovery constraint emission for the search engine
    constraint = {
        "constraint_id": f"cons:{record['processing_id']}",
        "derived_from_event": event.get("event_id"),
        "package_id": package_context.get("package_id"),
        "constraint": (
            f"downstream searches must treat '{(event.get('outcome') or {}).get('parameter', 'the expected effect')}' "
            f"as {'SUPPORTED' if outcome == SUPPORTS else 'REFUTED' if outcome == REFUTES else 'UNCHANGED'} "
            "by external evidence; future candidates in this territory must "
            "cite or update this constraint"),
        "epistemic_class": "EXPERIMENTALLY_ESTIMATED" if not rehearsal
                           else "CONTROLLED_REHEARSAL",
        "timestamp": utc_now()}
    record["discovery_constraint"] = constraint
    _append_jsonl(out / "LEARNING_CONSTRAINTS.jsonl", constraint)

    # 6. Dossier V2 — regenerate through the same package factory
    spec = package_context.get("invention_spec")
    eng = package_context.get("engineering_spec")
    if spec and eng:
        from .package_factory import generate_buyer_package
        # mutate the spec's provenance with the new posterior (V2 basis)
        spec = json.loads(json.dumps(spec))  # deep copy; never mutate input
        spec.setdefault("provenance", {})["value"]["learning"] = {
            "events_ingested": [event.get("event_id")],
            "posterior_belief": update["posterior"],
            "mutation_id": mutation["mutation_id"]}
        spec["_spec_hash"] = sha256_obj(
            {k: v for k, v in spec.items() if not k.startswith("_")})
        report = generate_buyer_package(
            str(out / "V2_PACKAGE"), spec, eng,
            env=None, run_ctx={
                "run_id": package_context.get("run_id",
                                              record["processing_id"]),
                "package_number": package_context.get("package_number",
                                                      "91")},
            rehearsal=rehearsal)
        # V2 mutation addendum, mirroring the frozen portfolio's V2 shape
        addendum = {
            "addendum_type": "V2_MUTATION_ADDENDUM",
            "trigger_event_id": event.get("event_id"),
            "mutation_id": mutation["mutation_id"],
            "before_belief": update["prior"],
            "after_belief": update["posterior"],
            "outcome": outcome,
            "loop_verification_state": "NONE",
            "real_loop_verified": False,
            "synthetic_rehearsal": rehearsal,
            "note": ("REAL_LOOP_VERIFIED remains FALSE: it is a DERIVED "
                     "state requiring the full R370G causal chain validated "
                     "at portfolio level; this addendum never assigns it"),
            "timestamp": utc_now()}
        v2_dir = Path(report["folder"])
        if v2_dir.exists():
            (v2_dir / "V2_MUTATION_ADDENDUM.json").write_text(
                json.dumps(addendum, indent=2, ensure_ascii=False))
        record["dossier_v2"] = {
            "folder": report.get("folder"),
            "complete": report.get("complete"),
            "zip": report.get("zip"),
            "addendum": addendum}
    else:
        record["dossier_v2"] = {
            "skipped": True,
            "reason": "no invention/engineering spec in context; belief and "
                      "constraint recorded without package regeneration"}

    record["final_action"] = "PROCESSED"
    (out / f"{record['processing_id']}_RECORD.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False))
    return record


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")

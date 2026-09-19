"""discovery_fabric/engine/transition_trace.py — observation-only
candidate transition ledger for the mechanism-space path.

R510 next-cliff instrumentation: every generated candidate is followed
through the transitions the pipeline ACTUALLY implements (no new
semantics, no threshold/prompt/matcher changes — this module only
READS states the instruments already produced):

  OPERATOR_GENERATED
  -> STRUCTURALLY_ADMISSIBLE (candidate_state == CANDIDATE at assembly;
     the testable-prediction gate; the operator_semantic_check booleans
     ride as observed fields — they do not gate today)
  -> CEMETERY_CONSULTED -> CEMETERY_BLOCKED / CEMETERY_CLEAR
     (NOT_CONSULTED when the candidate never reached consultation;
     CONSULTATION_UNAVAILABLE on infrastructure failure — Art. XXV)
  -> DISTINCT / EQUIVALENT / INDETERMINATE (the real adjudicator's
     verdict; NOT_ADJUDICATED when dropped earlier)
  -> SUPPORT_VERIFIED (SUPPORTED / PARTIALLY_SUPPORTED /
     NOT_ENOUGH_EVIDENCE / CONTESTED; NOT_VERIFIED when dropped
     earlier — support verification LABELS, it does not filter)
  -> RETAINED / DROPPED (pipeline membership in space candidates)

Two tracks are recorded separately and honestly:
  pipeline_retained — the candidate continues downstream (pool,
     attack, ranking). A retained candidate is NOT a survivor.
  drop_transition — where the candidate ceased to be
     survivor-eligible (null when still eligible): NOT_GENERATED /
     STRUCTURALLY_INADMISSIBLE / CEMETERY_BLOCK / DISTINCTNESS_DROP /
     DISTINCTNESS_INDETERMINATE / SUPPORT_VERIFICATION.
     A SUPPORT_VERIFICATION drop with pipeline_retained=True is the
     measured shape "retained but unaffirmed" (e.g. the P1 MS
     candidate: ranked + pool-attacked, never survivor-eligible).

Pure functions (no I/O, no LLM, no timestamps). The adapter supplies
the instruments' real outputs; control tests supply real-instrument
outputs on crafted inputs through the same builder.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

TRACE_VERSION = "candidate_transition/1.0.0"

SUPPORT_AFFIRMED = ("SUPPORTED", "PARTIALLY_SUPPORTED")


def empty_operator_counts() -> Dict[str, int]:
    return {
        "generated": 0,
        "structurally_admissible": 0,
        "cemetery_consulted": 0,
        "cemetery_blocked": 0,
        "cemetery_clear": 0,
        "distinct": 0,
        "equivalent": 0,
        "indeterminate": 0,
        "support_supported": 0,
        "support_partial": 0,
        "support_not_enough_evidence": 0,
        "support_contested": 0,
        "retained": 0,
        "dropped": 0,
    }


def _drop_for(trace: Dict[str, Any]) -> Optional[str]:
    """Survivor-eligibility loss, from measured states only. Every
    branch is a pipeline fact; infrastructure failure yields the
    honest CEMETERY_UNKNOWN (Art. XXV — never a scientific drop,
    never silent eligibility)."""
    if trace.get("generation_status") in (
            "NO_APPLICABLE_EVIDENCE", "NO_EVIDENCE",
            "OPERATOR_INSTANTIATION_FAILED", "NOT_ATTEMPTED"):
        return "NOT_GENERATED"
    if not trace.get("structurally_admissible"):
        return "STRUCTURALLY_INADMISSIBLE"
    if trace.get("cemetery_state") == "BLOCKED":
        return "CEMETERY_BLOCK"
    if trace.get("cemetery_state") == "CONSULTATION_UNAVAILABLE":
        return "CEMETERY_UNKNOWN"
    if trace.get("cemetery_state") != "CLEAR":
        return "CEMETERY_UNREACHED"
    if trace.get("distinctness_verdict") == "EQUIVALENT":
        return "DISTINCTNESS_DROP"
    if trace.get("distinctness_verdict") == "INDETERMINATE":
        return "DISTINCTNESS_INDETERMINATE"
    if trace.get("distinctness_verdict") != "DISTINCT":
        return "DISTINCTNESS_UNADJUDICATED"
    if trace.get("support_state") not in SUPPORT_AFFIRMED:
        return "SUPPORT_VERIFICATION"
    return None


def build_transition_ledger(
        assembled: List[Dict[str, Any]],
        operator_id: str,
        generation_status: str,
        states_before_cemetery: Dict[str, str],
        consult_record: Dict[str, Any],
        distinctness_by_id: Dict[str, Dict[str, Any]],
        retained_ids: List[str],
        support_by_id: Dict[str, Dict[str, Any]],
        semantic_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build the per-candidate transition ledger + per-operator
    aggregates from the instruments' already-produced outputs.

    assembled: candidate dicts as assembled (with candidate_id,
      candidate_state, testable_prediction_check).
    states_before_cemetery: candidate_id -> candidate_state snapshot
      taken after assembly, before consultation.
    consult_record: the _consult_cemetery record (blocked entries with
      candidate_id + entry ids + reasons).
    distinctness_by_id: candidate_id -> {verdict, basis} from dedup.
    retained_ids: kept_ids from the retention step.
    support_by_id: candidate_id -> mechanism_support record.
    semantic_by_id: candidate_id -> operator_semantic_check record.
    """
    semantic_by_id = semantic_by_id or {}
    blocked_by_id: Dict[str, Dict[str, Any]] = {}
    for b in (consult_record or {}).get("blocked", []):
        if isinstance(b, dict) and b.get("candidate_id"):
            blocked_by_id[str(b["candidate_id"])] = b
    consult_state = str((consult_record or {}).get("state") or "")
    consulted = consult_state not in (
        "", "CEMETERY_CONSULTATION_UNAVAILABLE")
    traces: List[Dict[str, Any]] = []
    counts = empty_operator_counts()
    for c in assembled:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("candidate_id") or "")
        state_now = str(c.get("candidate_state") or "")
        state_before = str(states_before_cemetery.get(cid, ""))
        admissible = state_before == "CANDIDATE"
        testable = ((c.get("testable_prediction_check") or {})
                    .get("testable"))
        sem = semantic_by_id.get(cid, {})
        if cid in blocked_by_id:
            cem_state = "BLOCKED"
        elif not admissible:
            cem_state = "NOT_CONSULTED"
        elif not consulted:
            cem_state = "CONSULTATION_UNAVAILABLE"
        else:
            cem_state = "CLEAR"
        block = blocked_by_id.get(cid, {})
        dd = distinctness_by_id.get(cid, {})
        # The adjudicator stamps verdicts only on consulted
        # survivors; anything earlier is NOT_ADJUDICATED (never
        # inferred — Art. XXV).
        verdict = str(dd.get("verdict") or "NOT_ADJUDICATED")
        sup = support_by_id.get(cid, {})
        support_state = str(sup.get("mechanism_support_state") or
                            "NOT_VERIFIED")
        retained = cid in retained_ids
        trace = {
            "candidate_id": c.get("candidate_id"),
            "operator_id": operator_id,
            "generation_status": generation_status,
            "candidate_state_before_cemetery": state_before or None,
            "structurally_admissible": admissible,
            "testable_at_assembly": testable,
            "semantic_invariant_held": sem.get("invariant_held"),
            "semantic_required_change": sem.get(
                "required_change_present"),
            "cemetery_consulted": cem_state in ("CLEAR", "BLOCKED"),
            "cemetery_state": cem_state,
            "cemetery_entry_ids": [e for e in (
                block.get("entries") or [])],
            "cemetery_block_reason": (
                block.get("physical_constraint")
                or block.get("lesson") or block.get("reason")
                or None),
            "distinctness_verdict": verdict,
            "distinctness_basis": dd.get("basis"),
            "support_state": support_state,
            "support_counts": sup.get("counts"),
            "pipeline_retained": retained,
            "final_retained_state": state_now if retained else None,
        }
        trace["drop_transition"] = _drop_for(trace)
        trace["survivor_eligible"] = trace["drop_transition"] is None
        traces.append(trace)
        counts["generated"] += 1
        if admissible:
            counts["structurally_admissible"] += 1
        if trace["cemetery_consulted"]:
            counts["cemetery_consulted"] += 1
        if cem_state == "BLOCKED":
            counts["cemetery_blocked"] += 1
        elif cem_state == "CLEAR":
            counts["cemetery_clear"] += 1
        if verdict == "DISTINCT":
            counts["distinct"] += 1
        elif verdict == "EQUIVALENT":
            counts["equivalent"] += 1
        elif verdict == "INDETERMINATE":
            counts["indeterminate"] += 1
        if support_state == "SUPPORTED":
            counts["support_supported"] += 1
        elif support_state == "PARTIALLY_SUPPORTED":
            counts["support_partial"] += 1
        elif support_state == "NOT_ENOUGH_EVIDENCE":
            counts["support_not_enough_evidence"] += 1
        elif support_state == "CONTESTED":
            counts["support_contested"] += 1
        if retained:
            counts["retained"] += 1
        else:
            counts["dropped"] += 1
    return {"trace_version": TRACE_VERSION,
            "operator_id": operator_id,
            "generation_status": generation_status,
            "candidate_traces": traces,
            "operator_counts": counts}

"""The directional improvement loop's state transitions (R450 §3;
R451 §§3-5).

    EVIDENCE -> MECHANISM -> CANDIDATE -> ATTACK -> FAILURE
    -> CAUSAL DIAGNOSIS -> DIRECTIONAL HYPOTHESIS (ground-gated)
    -> [GAP RETRIEVAL -> RE-PROPOSAL -> VERIFIED DIRECTION_DELTA]
    -> CONTROLLED MUTATION -> EVALUATION -> OBSERVATION
    -> CAUSAL UPDATE -> NEXT DIRECTION

Implemented as ONE step function the engine's evolution pipeline calls
between the diagnosis and the generation. Every transition retains
provenance; there is no hidden parallel state and no second invention
graph — the step REFERENCES the canonical generation records and
persists its own typed records in the run directory:

    DIRECTIONAL_HYPOTHESES.json     (all hypotheses + gate records)
    IMPROVEMENT_TRAJECTORY.json     (the append-only trajectory)

THE UNGUIDED CONTROL (the benchmark's Arm B): when
ENGINE_EVOLUTION_MODE=UNGUIDED the generation prompt deliberately
carries NEITHER the diagnosis NOR a directional hypothesis — a generic
"improve this candidate" mutation. This isolates the value of causal
directional feedback (same gauntlet, same transport, same engine).

The evidence-driven direction reversal (§5's reverse path, R451 §3):
when a gated hypothesis declares evidence_gaps, the gap queries are
derived (from the target variable + the diagnosed mechanism) and
served through the R449 evidence fabric; the hypothesis is then
RE-PROPOSED against the new evidence and the DIRECTION_DELTA is
COMPUTED AND VERIFIED mechanically (before + new evidence + after,
per-field attribution to exact evidence ids whose spans verify
verbatim). evidence_changed_direction is True ONLY when a CLOSED
causal field changed WITH a verified attribution — the R450 shortcut
(retrieval returned items -> True) is REPLACED (fail-closed, no
exceptions).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.directional.hypothesis import (
    apply_gate, ground_gate, make_hypothesis_id, propose_directional_hypothesis,
    repropose_with_evidence, utc_now,
)
from discovery_fabric.directional.delta import (
    CAUSAL_FIELDS, direction_delta,
)
from discovery_fabric.directional.observation import (
    apply_causal_update, causal_update, extract_observation,
)
from discovery_fabric.directional.trajectory import (
    append_step, load_trajectory,
)

HYPOTHESES_FILENAME = "DIRECTIONAL_HYPOTHESES.json"


def directional_enabled() -> bool:
    """The directional layer is ON by default (the directive: 'The
    current loop must become [the directional loop]')."""
    return (os.environ.get("ENGINE_DIRECTIONAL", "1").strip() or "1") \
        != "0"


def evolution_mode() -> str:
    """DIRECTIONAL (default) | LEGACY (diagnosis prompt, no gate) |
    UNGUIDED (generic prompt — the benchmark's Arm B)."""
    m = (os.environ.get("ENGINE_EVOLUTION_MODE", "DIRECTIONAL").strip()
         or "DIRECTIONAL").upper()
    return m if m in ("DIRECTIONAL", "LEGACY", "UNGUIDED") else \
        "DIRECTIONAL"


# ---------------------------------------------------------------------------
# the record stores (append-only, in the run directory)
# ---------------------------------------------------------------------------

def _load_hypotheses(run_dir: Path) -> Dict[str, Any]:
    p = Path(run_dir) / HYPOTHESES_FILENAME
    if p.exists():
        try:
            d = json.loads(p.read_text())
            if isinstance(d, dict):
                return d
        except Exception:  # noqa: BLE001
            pass
    return {"artifact_type": "DIRECTIONAL_HYPOTHESES",
            "schema_version": "hypotheses/1.0",
            "created_at": utc_now(),
            "hypotheses": []}


def _persist_hypotheses(run_dir: Path, store: Dict[str, Any]) -> None:
    p = Path(run_dir) / HYPOTHESES_FILENAME
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, indent=1, ensure_ascii=False,
                            default=str))


# ---------------------------------------------------------------------------
# the reverse path: evidence gaps -> retrieval (§5)
# ---------------------------------------------------------------------------

_GAP_QUERY_TEMPLATES = [
    "{target} {mech_terms}",
    "{target} failure mechanism",
    "{mech_terms} alternative",
]


def evidence_gap_queries(hypothesis: Dict[str, Any]) -> List[str]:
    """Deterministic gap queries from the hypothesis's OWN declared
    gaps (the reverse path: DIRECTION -> WHAT EVIDENCE IS REQUIRED ->
    RETRIEVAL). Fixed templates, recorded derivation."""
    target = str(hypothesis.get("target_variable") or "")
    mech = str(hypothesis.get("mechanism_affected") or "")
    mech_terms = " ".join(
        w for w in re.findall(r"[a-z0-9]{4,}", mech.lower())[:3])
    out: List[str] = []
    seen = set()
    for tmpl in _GAP_QUERY_TEMPLATES:
        q = re.sub(r"\s+", " ",
                   tmpl.format(target=target, mech_terms=mech_terms)
                   ).strip()
        if len(q.split()) >= 2 and q not in seen:
            seen.add(q)
            out.append(q)
    return out[:3]


def serve_evidence_gaps(problem: Dict[str, Any],
                        hypothesis: Dict[str, Any]
                        ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Retrieve evidence for the declared gaps through the R449
    evidence fabric (federated; the same canonical EvidenceRecord
    normalization). Failures are recorded as UNKNOWN-class channel
    states — never absence (Art. XXI.3)."""
    queries = evidence_gap_queries(hypothesis)
    record: Dict[str, Any] = {
        "loop_step": "EVIDENCE_GAP_RETRIEVAL",
        "derived_queries": queries,
        "derivation": ("deterministic templates over the hypothesis's "
                       "target_variable + mechanism_affected (the "
                       "reverse path: direction -> required evidence "
                       "-> retrieval)"),
        "retrieved_at": utc_now(),
        "n_items": 0,
        "evidence_ids": [],
        "channel_states": [],
    }
    if not queries:
        record["state"] = "NO_GAP_QUERY_DERIVABLE"
        return [], record
    try:
        from discovery_fabric import evidence_fabric as ef
        items, report = ef.retrieve_evidence(problem,
                                              extra_queries=queries[:2])
        record["n_items"] = len(items)
        record["evidence_ids"] = [i.get("id") for i in items]
        record["channel_states"] = [
            {"source_id": c.get("source_id"), "query": c.get("query"),
             "state": c.get("state")}
            for c in report.get("channels", [])]
        record["state"] = "OK" if items else "NO_RESULTS"
    except Exception as exc:  # noqa: BLE001 — infra, never a verdict
        record["state"] = f"CHANNEL_ERROR: {type(exc).__name__}"[:200]
    return items, record


# ---------------------------------------------------------------------------
# THE STEP (called by the engine's evolution pipeline)
# ---------------------------------------------------------------------------

def _design_state(problem: Dict[str, Any],
                  parent: Dict[str, Any]) -> Dict[str, Any]:
    """R451 §5 G6: the design's OWN declared state — the failed
    candidate's mechanism/intervention plus the problem's declared
    quantities (a direction about a variable outside this state moves
    a variable the machine does not control)."""
    arch = parent.get("architecture") or {}
    prob_text = " ".join(
        str(problem.get(k) or "") for k in
        ("device", "failure", "constraint", "text", "problem_text"))
    return {
        "mechanism": arch.get("mechanism") or parent.get("mechanism"),
        "intervention": arch.get("intervention") or
        parent.get("intervention"),
        "expected_effect": arch.get("expected_effect") or
        parent.get("expected_effect"),
        "problem_text": prob_text,
        "targets": [problem.get("device"), problem.get("constraint")],
    }


def _falsified_priors(store: Dict[str, Any]) -> List[Dict[str, Any]]:
    """R451 §5 G9: the run's own FALSIFIED hypotheses — negative
    knowledge (Art. LI): a falsified (target_variable, direction)
    pair may not be re-proposed."""
    return [h for h in (store.get("hypotheses") or [])
            if h.get("status") == "FALSIFIED"]


def directional_step(
        *,
        run_dir: Path,
        problem: Dict[str, Any],
        parent: Dict[str, Any],
        diagnosis: Dict[str, Any],
        failure_summary: str,
        evidence_items: List[Dict[str, Any]],
        gen_n: int,
        attempt: int = 1) -> Optional[Dict[str, Any]]:
    """DIAGNOSIS -> DIRECTIONAL HYPOTHESIS -> (ground gate) ->
    [gap retrieval -> RE-PROPOSAL -> DIRECTION_DELTA] -> returns the
    GROUNDED hypothesis (or None with the rejection recorded — the
    mutation never executes).

    The caller (engine) derives the controlled mutation FROM the
    returned hypothesis; the observation/causal-update legs run after
    the gauntlet (record_directional_outcome).

    R451 §3: evidence_changed_direction is set ONLY by the verified
    DIRECTION_DELTA (before + new evidence + after, with per-field
    attribution to exact evidence whose span verifies verbatim) —
    the R450 shortcut (gap retrieval returned items -> True) is
    REPLACED. R451 §4: an EXPLORATORY hypothesis (structure sound,
    support PARTIAL/MISSING) returns with NO mutation — the next
    action is retrieval or a decisive-experiment specification.
    """
    store = _load_hypotheses(run_dir)
    known_ids = {str(i.get("id") or "") for i in evidence_items or []}

    # ---- stamp the diagnosis with its deterministic id ----------------
    # the engine's diagnosis records (evolution._cause) carry cause +
    # basis but no id; the directional layer derives ONE deterministic
    # id from (parent, cause) — the same (parent, cause) is the same
    # diagnosis event; a different cause is a different event (Art. VI)
    import hashlib as _hl
    if not diagnosis.get("diagnosis_id"):
        basis_key = "; ".join(str(b) for b in
                              (diagnosis.get("basis") or [])[:2])[:200]
        diagnosis["diagnosis_id"] = "diag:" + _hl.sha256(
            f"{parent.get('invention_id')}|{diagnosis.get('cause')}|"
            f"{basis_key}".encode("utf-8")).hexdigest()[:16]

    # ---- PROPOSE (LLM, stamped AI_PROPOSED) ---------------------------
    hyp = propose_directional_hypothesis(
        parent, failure_summary, diagnosis, evidence_items,
        attempt=attempt)
    if hyp is None:
        # transport-class: the direction layer failed to produce a
        # proposal — an infrastructure state, never a scientific one
        store["hypotheses"].append({
            "hypothesis_id": make_hypothesis_id(
                str(parent.get("invention_id") or "cand"),
                str(diagnosis.get("diagnosis_id") or "failure"),
                "", attempt),
            "status": "ABSENT_PROPOSAL_TRANSPORT",
            "recorded_at": utc_now(),
            "note": ("the LLM proposal failed (transport class) — no "
                     "mutation executes; the legacy evolution path is "
                     "NOT silently substituted (Art. IV)"),
        })
        _persist_hypotheses(run_dir, store)
        append_step(run_dir, {
            "gen": gen_n,
            "candidate_id": parent.get("invention_id"),
            "failure_id": diagnosis.get("diagnosis_id"),
            "diagnosis": {"diagnosis_id": diagnosis.get("diagnosis_id"),
                          "cause": diagnosis.get("cause")},
            "hypothesis": {"status": "ABSENT_PROPOSAL_TRANSPORT"},
            "mutation": None,
            "observation": None,
            "causal_update": None,
            "mode": evolution_mode(),
        })
        return None

    # ---- GROUND GATE (mechanical) --------------------------------------
    parent_mechanism = str((parent.get("architecture") or {}).get(
        "mechanism") or parent.get("mechanism") or "")
    evidence_texts = {str(i.get("id") or ""): i
                      for i in (evidence_items or [])}
    gate = ground_gate(
        hyp, diagnosis, parent_mechanism,
        known_evidence_ids=known_ids,
        design_state=_design_state(problem, parent),
        evidence_texts=evidence_texts,
        falsified_priors=_falsified_priors(store))
    hyp = apply_gate(hyp, gate)

    # ---- REVERSE PATH (R451 §3): gaps -> retrieval -> RE-PROPOSAL ->
    # the VERIFIED DIRECTION_DELTA. The R450 shortcut (gap items
    # returned -> evidence_changed_direction = True) is REPLACED: only
    # a verified causal-field change attributed to exact new evidence
    # (span verified verbatim) ever sets the flag. -----------------------
    if hyp["status"] in ("GROUNDED", "EXPLORATORY") \
            and hyp.get("evidence_gaps"):
        gap_items, gap_record = serve_evidence_gaps(problem, hyp)
        hyp["gap_retrieval"] = gap_record
        if gap_items:
            hyp_before = {k: hyp.get(k) for k in CAUSAL_FIELDS}
            after = repropose_with_evidence(
                hyp, gap_items, attempt=attempt)
            if after is None:
                # transport-class: the re-proposal failed — the BEFORE
                # hypothesis stands, the evidence did NOT change the
                # direction (an infrastructure state, never a verdict)
                hyp["evidence_changed_direction"] = False
                hyp["reproposal_transport_failed"] = True
            else:
                claims = after.pop("_attribution_claims", []) or []
                delta = direction_delta(hyp_before, gap_items, after,
                                       claims)
                hyp["direction_delta"] = delta
                hyp["evidence_changed_direction"] = bool(
                    delta["evidence_changed_direction"])
                if delta["evidence_changed_direction"]:
                    # the AFTER direction replaces the BEFORE — the
                    # changed causal fields are adopted (each carries
                    # its verified or unverified attribution in the
                    # delta record) and the merged hypothesis is
                    # RE-GATED with the new evidence in custody
                    for f in CAUSAL_FIELDS:
                        if after.get(f):
                            hyp[f] = after[f]
                    hyp["evidence_support"] = after.get(
                        "evidence_support") or hyp.get(
                        "evidence_support")
                    hyp["evidence_gaps"] = after.get("evidence_gaps") \
                        or []
                    for it in gap_items[:4]:
                        eid = str(it.get("id") or "")
                        if eid and eid not in {
                                e.get("evidence_id")
                                for e in hyp.get("evidence_support") or []}:
                            # the span is the item's OWN retrieved text
                            # (verbatim from custody — G5 verifies the
                            # binding; Art. II/XII)
                            hyp["evidence_support"].append({
                                "evidence_id": eid,
                                "span": str(it.get("abstract") or
                                            "")[:200],
                                "acquired_through":
                                    "EVIDENCE_GAP_RETRIEVAL",
                                "source": (it.get("provenance") or {}).get(
                                    "provider"),
                            })
                    merged_texts = dict(evidence_texts)
                    for it in gap_items:
                        merged_texts[str(it.get("id") or "")] = it
                    gate2 = ground_gate(
                        hyp, diagnosis, parent_mechanism,
                        known_evidence_ids=(known_ids | {
                            str(i.get("id") or "") for i in gap_items}),
                        design_state=_design_state(problem, parent),
                        evidence_texts=merged_texts,
                        falsified_priors=_falsified_priors(store))
                    hyp = apply_gate(hyp, gate2)
                else:
                    # honest states (R451 §3): evidence arrived and
                    # changed NOTHING (or the changes did not verify) —
                    # recorded, never silently credited
                    hyp.setdefault("evidence_arrived_with_no_direction_change",
                                   True)
                    hyp["evidence_gaps"] = after.get("evidence_gaps") \
                        or []
                    for it in gap_items[:4]:
                        eid = str(it.get("id") or "")
                        if eid and eid not in {
                                e.get("evidence_id")
                                for e in hyp.get("evidence_support") or []}:
                            hyp["evidence_support"].append({
                                "evidence_id": eid,
                                "span": str(it.get("abstract") or
                                            "")[:200],
                                "acquired_through":
                                    "EVIDENCE_GAP_RETRIEVAL",
                                "source": (it.get("provenance") or {}).get(
                                    "provider"),
                            })
                    # support may have arrived WITHOUT a direction
                    # change — re-gate so the evidence class reflects
                    # the served evidence (GROUNDED/EXPLORATORY)
                    merged_texts = dict(evidence_texts)
                    for it in gap_items:
                        merged_texts[str(it.get("id") or "")] = it
                    gate2 = ground_gate(
                        hyp, diagnosis, parent_mechanism,
                        known_evidence_ids=(known_ids | {
                            str(i.get("id") or "") for i in gap_items}),
                        design_state=_design_state(problem, parent),
                        evidence_texts=merged_texts,
                        falsified_priors=_falsified_priors(store))
                    hyp = apply_gate(hyp, gate2)
        else:
            hyp["evidence_changed_direction"] = False

    store["hypotheses"].append(hyp)
    _persist_hypotheses(run_dir, store)

    if hyp["status"] == "REJECTED":
        # THE DIRECTIVE'S RULE: ungrounded mutation -> REJECT; the
        # mutation NEVER executes; the rejection is recorded (negative
        # knowledge — brute-force mutation is not mistaken for
        # intelligence)
        append_step(run_dir, {
            "gen": gen_n,
            "candidate_id": parent.get("invention_id"),
            "failure_id": diagnosis.get("diagnosis_id"),
            "diagnosis": {"diagnosis_id": diagnosis.get("diagnosis_id"),
                          "cause": diagnosis.get("cause")},
            "hypothesis": {"hypothesis_id": hyp["hypothesis_id"],
                           "status": "REJECTED",
                           "target_variable": hyp["target_variable"],
                           "gate": hyp.get("gate")},
            "mutation": None,
            "observation": None,
            "causal_update": None,
            "rejection_note": ("the ground gate rejected the direction; "
                               "no mutation executed (R450 §4)"),
            "mode": evolution_mode(),
        })
        return None
    if hyp["status"] == "EXPLORATORY":
        # R451 §4: structure passed but the evidence class is
        # PARTIAL/MISSING — the direction is at most an EXPLORATORY
        # hypothesis: NO mutation executes; the next action is further
        # retrieval or a decisive-experiment specification (never
        # pretend-grounded -> mutate)
        append_step(run_dir, {
            "gen": gen_n,
            "candidate_id": parent.get("invention_id"),
            "failure_id": diagnosis.get("diagnosis_id"),
            "diagnosis": {"diagnosis_id": diagnosis.get("diagnosis_id"),
                          "cause": diagnosis.get("cause")},
            "hypothesis": {
                "hypothesis_id": hyp["hypothesis_id"],
                "status": "EXPLORATORY",
                "target_variable": hyp["target_variable"],
                "evidence_class": (hyp.get("gate") or {}).get(
                    "evidence_class"),
                "evidence_changed_direction": bool(
                    hyp.get("evidence_changed_direction")),
                "gate": hyp.get("gate"),
            },
            "mutation": None,
            "observation": None,
            "causal_update": None,
            "exploratory_note": (
                "structure sound, evidence class "
                f"{(hyp.get('gate') or {}).get('evidence_class')} — "
                "no mutation; next action: retrieve the missing "
                "evidence or specify the decisive experiment "
                "(R451 §4)"),
            "mode": evolution_mode(),
        })
        return None
    return hyp


def _upsert_hypothesis(store: Dict[str, Any],
                       hypothesis: Dict[str, Any]) -> None:
    """Upsert ONE hypothesis into the store by id (append when absent,
    update the status when present — the record is never duplicated)."""
    hid = hypothesis.get("hypothesis_id")
    for h in store["hypotheses"]:
        if h.get("hypothesis_id") == hid:
            h["status"] = hypothesis.get("status")
            if hypothesis.get("mutation_id"):
                h["mutation_id"] = hypothesis["mutation_id"]
            for k in ("causal_updates", "gap_retrieval",
                      "evidence_changed_direction", "direction_delta",
                      "evidence_arrived_with_no_direction_change",
                      "reproposal_transport_failed"):
                if hypothesis.get(k):
                    h[k] = hypothesis[k]
            return
    store["hypotheses"].append(hypothesis)


def record_directional_outcome(
        *,
        run_dir: Path,
        hypothesis: Dict[str, Any],
        mutation_id: str,
        gauntlet_result: Dict[str, Any],
        gen_n: int,
        candidate_id: str) -> Dict[str, Any]:
    """EVALUATION -> OBSERVATION -> CAUSAL UPDATE -> NEXT DIRECTION's
    persisted record. Called by the engine after the gauntlet."""
    # mark executed
    store = _load_hypotheses(run_dir)
    hypothesis = dict(hypothesis, status="EXECUTED",
                      mutation_id=mutation_id)
    _upsert_hypothesis(store, hypothesis)
    _persist_hypotheses(run_dir, store)

    observation = extract_observation(candidate_id, mutation_id,
                                      hypothesis, gauntlet_result)
    update = causal_update(hypothesis, observation)
    hypothesis = apply_causal_update(hypothesis, update)
    # persist the final statuses
    store = _load_hypotheses(run_dir)
    _upsert_hypothesis(store, hypothesis)
    if not hypothesis.get("causal_updates"):
        hypothesis.setdefault("causal_updates", []).append(update)
        _upsert_hypothesis(store, hypothesis)
    _persist_hypotheses(run_dir, store)

    append_step(run_dir, {
        "gen": gen_n,
        "candidate_id": candidate_id,
        "failure_id": hypothesis.get("failure_id"),
        "diagnosis": {"diagnosis_id":
                      hypothesis.get("causal_diagnosis_id")},
        "hypothesis": {
            "hypothesis_id": hypothesis.get("hypothesis_id"),
            "status": hypothesis.get("status"),
            "target_variable": hypothesis.get("target_variable"),
            "direction": hypothesis.get("direction"),
            "intervention_type": hypothesis.get("intervention_type"),
            "predicted_effect": hypothesis.get("predicted_effect"),
            "falsifier": hypothesis.get("falsifier"),
            "evidence_changed_direction": bool(
                hypothesis.get("evidence_changed_direction")),
            "direction_delta_verdict": (
                (hypothesis.get("direction_delta") or {}).get("verdict")),
        },
        "mutation": {"mutation_id": mutation_id,
                     "intervention_type":
                         hypothesis.get("intervention_type")},
        "observation": observation,
        "causal_update": update,
        "mode": evolution_mode(),
    })
    return {"observation": observation, "causal_update": update,
            "hypothesis": hypothesis}


def record_unguided_outcome(
        *,
        run_dir: Path,
        mutation_id: str,
        gauntlet_result: Dict[str, Any],
        gen_n: int,
        candidate_id: str) -> Dict[str, Any]:
    """The UNGUIDED arm's outcome record (same observation extraction,
    no hypothesis, no causal update — the control arm's honest shape)."""
    observation = extract_observation(candidate_id, mutation_id, None,
                                      gauntlet_result)
    append_step(run_dir, {
        "gen": gen_n,
        "candidate_id": candidate_id,
        "hypothesis": None,
        "mutation": {"mutation_id": mutation_id, "mode": "UNGUIDED"},
        "observation": observation,
        "causal_update": None,
        "mode": "UNGUIDED",
        "note": ("unguided control: mutation without a directional "
                 "hypothesis (no ground gate, no causal update)"),
    })
    return {"observation": observation}

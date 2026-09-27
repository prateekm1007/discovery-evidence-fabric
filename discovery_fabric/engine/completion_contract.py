"""discovery_fabric/engine/completion_contract.py — R542 the authoritative
finished-discovery completion verifier.

PRODUCT INVARIANT (the operator contract):

    VALID_QUERY
  + EVIDENCE_BOUND
  + AT_LEAST_ONE_ADMISSIBLE_SURVIVOR
  + COMPLETE_DISCOVERY_RECORD          (6-part conversation shape)
  + COMPLETE_CANDIDATE_BOUND_TECHNOLOGY_PACKAGE
  = FINISHED_DISCOVERY

where the complete discovery record exposes, for EVERY displayed
admissible survivor:

    1. evidence found + source provenance (id, source, span, custody)
    2. competing mechanisms + falsification / kill condition
    3. adversarial challenge + disposition (why survived / killed)
    4. engineering definition + geometry / explicit model class
    5. decisive experiment + decision rule (the stated kill outcome)
    6. downloadable candidate-bound technology package

This module is the FINAL PRODUCT-STATE AUTHORITY. It inspects the
run's durable record and answers mechanically:

    Is this a finished discovery?
    If not, exactly which contract component is missing?
    Is the missing component recoverable by an existing engine path?
    If recoverable, did the engine attempt that recovery?
    If exhausted, what typed terminal state remains?

Design rules (Constitution Art. III/X/XXV/XXVIII/LXXVII):

  * The verifier never trusts the claimant — package hashes are
    re-measured from the on-disk ZIP by ranked_result_set; component
    presence is read from the run's own persisted artifacts.
  * It is NOT a UI calculation. The engine writes COMPLETION_CONTRACT_
    JSON at the run tail; the session/UI surface READS it.
  * A typed constitutional blocker (premise malformed, problem
    existence unestablished, policy stop) is never converted into a
    fake discovery; the typed terminal state is preserved verbatim.
  * An ordinary valid query with a genuine missing component reports
    the missing component + the EXISTING engine path that recovers it
    (the recovery graph below — no new epistemology; recovery always
    returns through the same evidence and admission gates).
  * "Two survivors" is NOT a product requirement. One survivor after
    multiple competing candidates were investigated (some killed) is
    a finished discovery; the two-survivor shape is a ranking test.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import ranked_result_set as _rrs

COMPLETION_CONTRACT_SCHEMA = "COMPLETION_CONTRACT/1.0.0"
CONTRACT_FILE = "COMPLETION_CONTRACT.json"

# ---------------------------------------------------------------------------
# the six contract components
# ---------------------------------------------------------------------------
COMP_EVIDENCE = "evidence"
COMP_MECHANISMS = "mechanisms"
COMP_ADVERSARIAL = "adversarial"
COMP_ENGINEERING = "engineering_model"
COMP_EXPERIMENT = "decisive_experiment"
COMP_PACKAGE = "technology_package"
COMPONENTS = (COMP_EVIDENCE, COMP_MECHANISMS, COMP_ADVERSARIAL,
              COMP_ENGINEERING, COMP_EXPERIMENT, COMP_PACKAGE)

# the five preconditions of the product invariant
PRE_VALID_QUERY = "VALID_QUERY"
PRE_EVIDENCE_BOUND = "EVIDENCE_BOUND"
PRE_SURVIVOR = "AT_LEAST_ONE_ADMISSIBLE_SURVIVOR"
PRE_RECORD = "COMPLETE_DISCOVERY_RECORD"
PRE_PACKAGE = "COMPLETE_CANDIDATE_BOUND_TECHNOLOGY_PACKAGE"
PRECONDITIONS = (PRE_VALID_QUERY, PRE_EVIDENCE_BOUND, PRE_SURVIVOR,
                 PRE_RECORD, PRE_PACKAGE)

# ---------------------------------------------------------------------------
# typed query classes — a typed blocker is NEVER re-labeled as success
# ---------------------------------------------------------------------------
#: the query itself was never valid (constitutional terminal states).
INVALID_QUERY_STATES = frozenset({
    "MALFORMED_OR_FALSE_PREMISE",
    "PROBLEM_EXISTENCE_UNESTABLISHED",
})
#: infrastructure-class blocks (resumable / recoverable — Art. LXI).
INFRASTRUCTURE_STATES = frozenset({
    "CAPABILITY_BLOCKED",
    "CAPABILITY_INSUFFICIENT",
    "TRANSPORT_BLOCKED",
    "TRANSPORT_FAILURE",
    "ADJUDICATION_BLOCKED",
    "INFRASTRUCTURE_FAILURE",
})
#: a coherent query that simply produced no admissible survivor —
#: a valid query whose survivor precondition failed (the recovery
#: path is the mechanism-generation / evolution graph, never a fake
#: candidate).
NO_SURVIVOR_STATES = frozenset({
    "REJECTED",
    "MECHANISM_STARVED",
    "MECHANISM_GENERATION_FAILED",
})

# disposition vocabulary that can NEVER be surfaced as SURVIVED
UNRESOLVED_ATTACK_STATES = frozenset({
    "UNRESOLVED", "UNCALIBRATED", "TRANSPORT_FAILURE", "NOT_RUN",
    "", None,
})

# ---------------------------------------------------------------------------
# THE RECOVERY GRAPH — existing engine paths, never a new epistemology.
# Recovery may change the engineering path, provider, candidate, or
# iteration, but it always returns through the same evidence and
# admission gates.
# ---------------------------------------------------------------------------
RECOVERY_GRAPH: Dict[str, Dict[str, Any]] = {
    COMP_EVIDENCE: {
        "failure": "NO / INSUFFICIENT EVIDENCE",
        "path": ("evidence retrieval + custody freeze (RETRIEVE stage, "
                 "the evidence fabric's own repair/retry path)"),
        "attempt_artifacts": ("stage_RETRIEVE.json",
                              "stage_RETRIEVE_FAILURE.json",
                              "EVIDENCE_FREEZE.json"),
        "class": "EVIDENCE",
    },
    COMP_MECHANISMS: {
        "failure": "NO / INSUFFICIENT MECHANISMS",
        "path": ("mechanism-generation / evolution / retry path "
                 "(INVENTION_LINEAGE.json + the IMPROVE kill-point "
                 "children path)"),
        "attempt_artifacts": ("INVENTION_LINEAGE.json",
                              "stage_IMPROVE.json",
                              "IMPROVEMENT_LEDGER.json"),
        "class": "MECHANISM",
    },
    COMP_ADVERSARIAL: {
        "failure": "ADVERSARIAL KILL / UNRESOLVED CHALLENGE",
        "path": ("IMPROVE kill-point -> fresh candidate -> re-run gates "
                 "(engineering_attack + independent attack)"),
        "attempt_artifacts": ("stage_IMPROVE.json",
                              "POST_RANK_ATTRIBUTION.json",
                              "SURVIVOR_SELECTION.json"),
        "class": "ADVERSARIAL",
    },
    COMP_ENGINEERING: {
        "failure": "3D BUILD FAILURE / MODEL CLASS NOT ESTABLISHED",
        "path": ("domain-aware conceptual/model fallback "
                 "(_candidate_geometry -> explicit model class)"),
        "attempt_artifacts": ("GEOMETRY_OUT.json",
                              "CAD_PIPELINE_LEDGER.json",
                              "RANKED_PACKAGE_RECORDS.json"),
        "class": "MODEL",
    },
    COMP_EXPERIMENT: {
        "failure": "DECISIVE EXPERIMENT NOT ESTABLISHED",
        "path": ("experiment selector + falsification-contract "
                 "projection (DECISIVE_EXPERIMENT.json); a kill outcome "
                 "stated from the run's own records or the honest "
                 "INVENTION_REQUIRES_EXPERIMENT terminal"),
        "attempt_artifacts": ("DECISIVE_EXPERIMENT.json",
                              "stage_KILLER_EXPERIMENT.json",
                              "stage_IMPROVE.json"),
        "class": "EXPERIMENT",
    },
    COMP_PACKAGE: {
        "failure": "PACKAGE FAILURE",
        "path": ("package compiler retry / repair "
                 "(EngineRun._compile_ranked_packages -> the canonical "
                 "package_compiler with the candidate's own inputs)"),
        "attempt_artifacts": ("RANKED_PACKAGE_RECORDS.json",
                              "RANKED_PACKAGE_FAILED.json"),
        "class": "PACKAGE",
    },
    "transport": {
        "failure": "TRANSPORT FAILURE",
        "path": ("existing provider ladder / retry "
                 "(model_routing's recorded fallback chain)"),
        "attempt_artifacts": ("ROUTING_LEDGER_RUN.json",
                              "CAPABILITY_GATE.json"),
        "class": "TRANSPORT",
    },
}


def _read(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a missing/corrupt record is an
        return None      # honest absence (Art. XXV), never an exception
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _model_class(run_dir: Path, key: str, eng: Dict[str, Any],
                 pkg_rec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The explicit model class for one candidate — DELEGATED to the
    ranked projection's ONE resolution chain (Art. XXVIII: earned
    engineering geometry where warranted, an explicit conceptual/system
    classification otherwise, never a vague 'see package' placeholder;
    Art. X: one authority, so the contract and the projection cannot
    disagree)."""
    return _rrs.resolve_model_class(run_dir, key, eng, pkg_rec)


def _candidate_artifact(run_dir: Path, kind: str,
                        key: str) -> Dict[str, Any]:
    """R543-3: one candidate's OWN suffixed artifact — no primary
    fallback. A non-primary candidate (key != primary) reads ONLY
    <KIND>_<key>.json; an absent file is an honest empty record and
    the missing artifact name is returned so the component can name
    it in the missing-components report. The primary candidate's
    canonical un-suffixed file is its own record by construction."""
    fname = f"{kind}.json" if key in (None, "primary") \
        else f"{kind}_{key}.json"
    rec = _read(run_dir / fname)
    missing = None if rec is not None else fname
    return (rec or {}), missing


def _evidence_component(run_dir: Path,
                       survivors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Component 1 — evidence found + source provenance.

    Every displayed survivor's own invention specification must carry
    custodied evidence records (id + source identity + content hash)
    AND the mechanism's supporting span (the exact recorded span the
    mechanism was derived from). Missing pieces are typed, never
    papered over (Art. XXV). R543-3: a non-primary survivor's own
    suffixed specification is the ONLY source — a missing file is a
    typed component gap, never the primary's content."""
    per: List[Dict[str, Any]] = []
    complete = bool(survivors)
    missing_artifact_names: List[str] = []
    for r in survivors:
        key = r.get("key") or "primary"
        spec, _missing = _candidate_artifact(run_dir,
                                             "INVENTION_SPECIFICATION", key)
        if _missing:
            missing_artifact_names.append(_missing)
        ev_field = spec.get("evidence") or {}
        records = ev_field.get("value") if isinstance(ev_field, dict) \
            and "value" in ev_field else ev_field
        if not isinstance(records, list):
            records = []
        recs = [x for x in records if isinstance(x, dict)]
        mm = spec.get("mechanism") or {}
        if isinstance(mm, dict) and "value" in mm:
            mm = mm.get("value") or {}
        span = (mm.get("mechanism_source_span") or "").strip() \
            if isinstance(mm, dict) else ""
        no_source = [x.get("id") for x in recs
                     if not (x.get("source") or x.get("source_id")
                             or x.get("source_uri"))]
        no_custody = [x.get("id") for x in recs
                      if not (x.get("content_hash") or x.get("frozen")
                              or x.get("custody"))]
        ok = bool(recs) and not no_source and not no_custody \
            and bool(span)
        per.append({
            "candidate_id": r.get("candidate_id"),
            "n_records": len(recs),
            "sources": sorted({str(x.get("source") or x.get("source_id")
                                   or x.get("source_uri") or "")
                               for x in recs}),
            "records_missing_source_identity": no_source,
            "records_missing_custody": no_custody,
            "mechanism_source_span_chars": len(span),
            "evidence_bound": ok,
        })
        complete = complete and ok
    return {
        "component": COMP_EVIDENCE,
        "complete": bool(complete) and not missing_artifact_names,
        "source_files": ["INVENTION_SPECIFICATION[_<key>].json"],
        "missing_candidate_artifacts": missing_artifact_names,
        "per_survivor": per,
        "requirement": ("custodied evidence records (source identity + "
                        "content hash) + the mechanism's supporting "
                        "span, for every displayed survivor"),
    }


def _mechanisms_component(selection: Dict[str, Any],
                          survivors: List[Dict[str, Any]]
                          ) -> Dict[str, Any]:
    """Component 2 — competing mechanisms + falsification / kill
    condition. The COMPETING set (everything investigated, including
    kills) is kept distinct from the SURVIVING set."""
    rows = [r for r in (selection.get("ranked") or [])
            if isinstance(r, dict)]
    per: List[Dict[str, Any]] = []
    complete = bool(survivors) and bool(rows)
    for r in survivors:
        key = r.get("key") or "primary"
        c = (r.get("components") or {}).get("mechanism") or {}
        mech = str(c.get("mechanism") or "").strip()
        kill = str(c.get("falsification_test") or "").strip()
        ok = bool(mech) and bool(kill)
        per.append({
            "candidate_id": r.get("candidate_id"),
            "mechanism_recorded": bool(mech),
            "kill_condition_recorded": bool(kill),
            "mechanism": mech[:240],
            "what_would_kill_it": kill[:240],
        })
        complete = complete and ok
    killed = [x for x in rows if x.get("killed")]
    excluded = [x for x in rows
                if (x.get("disposition") or "") == "EXCLUDED"]
    return {
        "component": COMP_MECHANISMS,
        "complete": bool(complete),
        "source_files": ["SURVIVOR_SELECTION.json",
                         "INVENTION_SPECIFICATION[_<key>].json"],
        "n_competing_investigated": len(rows),
        "n_killed": len(killed),
        "n_excluded_by_gates": len(excluded),
        "n_surviving": len(survivors),
        "competing_vs_surviving": {
            "competing_candidates_investigated": [
                x.get("candidate_id") for x in rows],
            "killed_by_challenge": [x.get("candidate_id") for x in killed],
            "excluded_by_gates": [x.get("candidate_id") for x in excluded],
            "surviving_candidates": [x.get("candidate_id")
                                     for x in survivors],
            "note": ("competing != surviving; a single survivor after "
                     "multiple competing candidates were investigated "
                     "is a genuine competing-mechanism investigation "
                     "(kills and recorded gate exclusions are distinct "
                     "outcomes, both exposed)"),
        },
        "per_survivor": per,
        "requirement": (">=1 mechanism with a stated falsification / "
                        "kill condition per displayed survivor; the "
                        "competing set is recorded, kills included"),
    }


def _adversarial_component(selection: Dict[str, Any],
                           survivors: List[Dict[str, Any]]
                           ) -> Dict[str, Any]:
    """Component 3 — adversarial challenge + disposition.

    'ATTACK ran' is not enough: every displayed row must carry a
    RESOLVED disposition with its basis; a transport failure,
    uncalibrated attack, or unresolved attack is NEVER surfaced as
    SURVIVED (Art. XXV/XXIX)."""
    rows = [r for r in (selection.get("ranked") or [])
            if isinstance(r, dict)]
    by_cid = {r.get("candidate_id"): r for r in rows}
    per: List[Dict[str, Any]] = []
    complete = bool(survivors)
    unresolved: List[Any] = []
    excluded: List[Any] = []
    for r in rows:
        disp = r.get("disposition") or "UNRESOLVED"
        # R542: three RESOLVED outcomes — SURVIVED (the challenge ran
        # and it survived), KILLED (the challenge killed it), EXCLUDED
        # (a deterministic gate resolved against it: quality FAIL, span
        # underived, or physics-ineligible — a recorded exclusion with
        # its reason on the row, never an unresolved attack). Only a
        # MISSING / UNRESOLVED disposition blocks: the challenge never
        # produced a verdict, so the discovery record is incomplete.
        if disp == "EXCLUDED":
            excluded.append(r.get("candidate_id"))
        elif disp not in ("SURVIVED", "KILLED"):
            unresolved.append(r.get("candidate_id"))
    for r in survivors:
        # the selection row is the single authority for the recorded
        # disposition/verdict (Art. X) — the derived ranked result only
        # projects it
        src = by_cid.get(r.get("candidate_id")) or {}
        disp = src.get("disposition") or "UNRESOLVED"
        overall = src.get("attack_overall")
        quality = src.get("quality_verdict")
        ok = (disp == "SURVIVED"
              and overall not in UNRESOLVED_ATTACK_STATES
              and quality not in (None, ""))
        per.append({
            "candidate_id": r.get("candidate_id"),
            "disposition": disp,
            "attack_overall": overall,
            "quality_verdict": quality,
            "why": ("survived the engineering attack gauntlet with a "
                    "recorded overall verdict and quality verdict"
                    if ok else
                    "disposition/verdict not resolved from records "
                    "(transport failure, uncalibrated attack, or "
                    "unresolved challenge is never SURVIVED)"),
            "resolved": ok,
        })
        complete = complete and ok
    return {
        "component": COMP_ADVERSARIAL,
        "complete": bool(complete) and not unresolved,
        "source_files": ["SURVIVOR_SELECTION.json"],
        "unresolved_rows": unresolved,
        "excluded_rows": excluded,
        "per_survivor": per,
        "requirement": ("every displayed survivor: recorded SURVIVED "
                        "disposition + attack overall + quality verdict; "
                        "every investigated candidate: a RESOLVED "
                        "disposition — SURVIVED, KILLED (the challenge "
                        "killed it), or EXCLUDED (a recorded gate "
                        "exclusion: quality/span/physics). Only a "
                        "MISSING/UNRESOLVED disposition blocks a "
                        "finished discovery — an unresolved challenge "
                        "is never papered over (Art. XXV/XXIX)"),
    }


def _engineering_component(run_dir: Path,
                           survivors: List[Dict[str, Any]],
                           pkg_records: Dict[str, Any]
                           ) -> Dict[str, Any]:
    """Component 4 — engineering definition + applicable 3D model.

    Physical/geometric invention -> earned engineering geometry + 3D
    model. Non-geometric invention -> an EXPLICIT conceptual/system 3D
    model class, labeled as such. What is prohibited is silently
    presenting a conceptual object as earned engineering CAD — and a
    vague 'see package' placeholder is not a model artifact. R543-3:
    a non-primary survivor's own suffixed ENGINEERING_SPECIFICATION is
    the ONLY source — a missing file is a typed component gap, never
    the primary candidate's engineering record."""
    pkgs = (pkg_records.get("packages") or {})
    per: List[Dict[str, Any]] = []
    complete = bool(survivors)
    missing_artifact_names: List[str] = []
    for r in survivors:
        key = r.get("key") or "primary"
        eng, _missing = _candidate_artifact(
            run_dir, "ENGINEERING_SPECIFICATION", key)
        if _missing:
            missing_artifact_names.append(_missing)
        core = eng.get("engineering_core") or {}
        arch = eng.get("system_architecture") or {}
        geo = eng.get("geometry") or {}
        definition = bool(core) or bool(geo) or bool(arch)
        pkg_rec = pkgs.get(str(r.get("candidate_id"))) \
            or pkgs.get(str(key)) or {}
        m = _model_class(run_dir, key, eng, pkg_rec)
        ok = definition and bool(m.get("model_class"))
        per.append({
            "candidate_id": r.get("candidate_id"),
            "engineering_definition_present": definition,
            "model_class": m.get("model_class"),
            "model_class_source": m.get("source"),
            "earned_engineering_geometry": bool(
                m.get("earned_geometry")),
            "labeling": ("earned engineering geometry + 3D model"
                         if m.get("earned_geometry") else
                         "explicit conceptual/system 3D model class "
                         "(never presented as earned CAD)"),
        })
        complete = complete and ok
    return {
        "component": COMP_ENGINEERING,
        "complete": bool(complete) and not missing_artifact_names,
        "missing_candidate_artifacts": missing_artifact_names,
        "source_files": ["ENGINEERING_SPECIFICATION[_<key>].json",
                         "GEOMETRY_OUT.json",
                         "RANKED_PACKAGE_RECORDS.json"],
        "per_survivor": per,
        "requirement": ("engineering definition present + an explicit "
                         "model class (earned geometry or labeled "
                         "conceptual/system model) for every displayed "
                         "survivor — never a 'see package' placeholder"),
    }


def _experiment_component(run_dir: Path,
                          survivors: List[Dict[str, Any]]
                          ) -> Dict[str, Any]:
    """Component 5 — decisive experiment + decision rule.

    Not a title: the record must carry the experiment, the discriminating
    outcomes (prediction), and a STATED falsification condition — the
    engine's own authority is state_integrity.falsification_contract_
    status (Art. LII: the contract is complete only when an outcome that
    kills the mechanism is stated; UNKNOWN fields limit maturity, never
    completeness)."""
    from . import state_integrity as _si
    per: List[Dict[str, Any]] = []
    complete = bool(survivors)
    missing_artifact_names: List[str] = []
    for r in survivors:
        key = r.get("key") or "primary"
        dec, _missing = _candidate_artifact(run_dir,
                                            "DECISIVE_EXPERIMENT", key)
        if _missing:
            missing_artifact_names.append(_missing)
        sel = dec.get("selected") or {}
        name = str(sel.get("experiment") or sel.get("name") or "").strip()
        hyps = sel.get("hypotheses") or []
        prediction = bool(hyps) and any(
            str(h.get("description") or "").strip() for h in hyps
            if isinstance(h, dict))
        discriminator = len([h for h in hyps if isinstance(h, dict)]) >= 2
        contract = dec.get("falsification_contract") or {}
        status = _si.falsification_contract_status(contract) \
            if contract else {"contract_complete": False,
                              "answered_fields": [],
                              "unknown_fields": {}}
        execution = dec.get("execution_status") or "SPECIFIED"
        ok = bool(name) and prediction and bool(
            status.get("contract_complete"))
        per.append({
            "candidate_id": r.get("candidate_id"),
            "experiment": name[:240],
            "predicted_discriminator_recorded": discriminator,
            "prediction_recorded": prediction,
            "decision_rule_state": (
                "STATED_KILL_OUTCOME" if status.get(
                    "contract_complete")
                else "FALSIFICATION_THRESHOLD_BLOCKER"),
            "answered_fields": status.get("answered_fields") or [],
            "unknown_fields": sorted(
                (status.get("unknown_fields") or {}).keys()),
            "execution_status": execution,
            "decisive": ok,
        })
        complete = complete and ok
    return {
        "component": COMP_EXPERIMENT,
        "complete": bool(complete) and not missing_artifact_names,
        "missing_candidate_artifacts": missing_artifact_names,
        "source_files": ["DECISIVE_EXPERIMENT[_<key>].json"],
        "authority": ("state_integrity.falsification_contract_status "
                      "(Art. LII): complete only when an experimental "
                      "outcome that kills the mechanism is stated"),
        "per_survivor": per,
        "requirement": ("experiment + discriminator + prediction + "
                        "decision rule / falsification condition + "
                        "execution status, for every displayed survivor"),
    }


def _package_component(run_dir: Path,
                       ranked_record: Dict[str, Any]) -> Dict[str, Any]:
    """Component 6 — the downloadable candidate-bound technology
    package (hash re-measured from disk by ranked_result_set)."""
    # R399 W2.1: a scientifically rejected run NEVER has a package —
    # the packaging refusal is a recorded constitutional state
    # (PACKAGE_SKIPPED_SCIENTIFICALLY_REJECTED.json), not a compile
    # failure to be "recovered" (a scientific verdict is terminal).
    rejected = bool(
        (run_dir / "PACKAGE_SKIPPED_SCIENTIFICALLY_REJECTED.json")
        .exists())
    verify = _rrs.verify_ranked_result_set(ranked_record, run_dir)
    n_adm = ranked_record.get("n_admissible") or 0
    n_pk = ranked_record.get("n_complete_packages") or 0
    complete = bool(n_adm) and n_pk == n_adm and verify["verified"] \
        and not rejected
    out = {
        "component": COMP_PACKAGE,
        "complete": bool(complete),
        "source_files": ["RANKED_PACKAGE_RECORDS.json",
                         "DOWNLOAD/<candidate-bound zip>",
                         "RANKED_DISCOVERY_RESULTS.json"],
        "n_admissible_survivors": n_adm,
        "n_complete_candidate_bound_packages": n_pk,
        "hash_verification": verify.get("per_candidate") or [],
        "violations": verify.get("violations") or [],
        "requirement": ("every displayed admissible survivor has its "
                        "OWN complete candidate-bound package whose "
                        "recorded SHA-256 equals the on-disk bytes"),
    }
    if rejected:
        out["scientifically_rejected"] = True
        out["skip_record"] = (
            "PACKAGE_SKIPPED_SCIENTIFICALLY_REJECTED.json")
        out["note"] = (
            "R399 W2.1: the run's candidate was scientifically "
            "REJECTED — packaging was refused by constitutional rule "
            "and the refusal is recorded; the package is not a "
            "missing component awaiting recovery")
    return out


def _valid_query(run_dir: Path, final_status: Optional[str],
                 manifest: Dict[str, Any]) -> Dict[str, Any]:
    """VALID_QUERY — the problem is coherent/established AND the
    required infrastructure/evidence path is available. Constitutional
    blockers stay typed failures (never converted into discoveries)."""
    failed = manifest.get("failed_stages") or {}
    policy_stop = any(str(v).startswith("POLICY_STOP:")
                      for v in failed.values())
    gate = _read(run_dir / "CAPABILITY_GATE.json") or {}
    capability_blocked = gate.get("status") == "BLOCKED"
    if policy_stop:
        return {"valid": False, "class": "POLICY_STOP",
                "typed_blocker": "POLICY_STOP",
                "reason": ("the stage policy stopped the run before "
                           "candidate generation (problem existence "
                           "unestablished) — no discovery is owed for "
                           "an unverified problem (Art. XX)")}
    if final_status in INVALID_QUERY_STATES:
        return {"valid": False, "class": "INVALID_QUERY",
                "typed_blocker": final_status,
                "reason": ("constitutional terminal — the premise was "
                           "malformed or problem existence could not be "
                           "established; never converted into a fake "
                           "discovery")}
    if final_status is None:
        return {"valid": False, "class": "PIPELINE_INCOMPLETE",
                "typed_blocker": "PIPELINE_INCOMPLETE",
                "reason": ("no final state was recorded — the run did "
                           "not reach a terminal state")}
    if capability_blocked or final_status in INFRASTRUCTURE_STATES:
        return {"valid": False, "class": "INFRASTRUCTURE_BLOCKED",
                "typed_blocker": final_status or "CAPABILITY_BLOCKED",
                "reason": ("infrastructure class (Art. LXI): "
                           "resumable/recoverable, never a scientific "
                           "rejection")}
    return {"valid": True, "class": "VALID_QUERY", "typed_blocker": None,
            "reason": ("coherent problem + available evidence/"
                       "infrastructure path")}


def _recovery_entry(component: str, complete: bool,
                    run_dir: Path, attempted_extra: bool = False
                    ) -> Optional[Dict[str, Any]]:
    """The typed recovery entry for one missing component: is it
    recoverable by an EXISTING engine path, did the engine attempt it,
    is the attempt exhausted?"""
    if complete:
        return None
    g = RECOVERY_GRAPH.get(component) or {}
    artifacts = []
    for name in (g.get("attempt_artifacts") or ()):
        p = run_dir / name
        if p.exists():
            artifacts.append(name)
    attempted = bool(artifacts) or attempted_extra
    return {
        "component": component,
        "missing_because": g.get("failure"),
        "recoverable": True,
        "recovery_path": g.get("path"),
        "recovery_class": g.get("class"),
        "attempted": bool(attempted),
        "attempt_evidence": artifacts,
        "exhausted": bool(attempted),
        "note": ("recovery (when attempted) always returns through the "
                 "same evidence and admission gates — the path may "
                 "change the engineering route, provider, candidate, or "
                 "iteration, never the epistemology"),
    }


def verify_completion_contract(
        run_dir: Path,
        run_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Mechanically answer: is this a finished discovery? If not,
    exactly which contract component is missing?

    Pure read-only verification over the run's durable record. The
    persist-side entry point (persist_completion_contract) adds the
    bounded automatic-recovery attempt."""
    run_dir = Path(run_dir)
    final = _read(run_dir / "final_state.json") or {}
    manifest = _read(run_dir / "run_manifest.json") or {}
    selection = _read(run_dir / "SURVIVOR_SELECTION.json") or {}
    pkg_records = _read(run_dir / "RANKED_PACKAGE_RECORDS.json") or {}

    # the ranked projection (SURVIVOR_SELECTION + the candidate-bound
    # package artifacts on disk — the R541 authority, never re-derived
    # admission; Art. X: one authority)
    ranked = _rrs.derive_ranked_result_set(run_dir, run_result)
    survivors = [r for r in (ranked.get("ranked_results") or [])
                 if r.get("admissible")]

    final_status = final.get("final_status") \
        or (run_result or {}).get("final_status")
    valid = _valid_query(run_dir, final_status, manifest)

    comps = {
        COMP_EVIDENCE: _evidence_component(run_dir, survivors),
        COMP_MECHANISMS: _mechanisms_component(selection, survivors),
        COMP_ADVERSARIAL: _adversarial_component(selection, survivors),
        COMP_ENGINEERING: _engineering_component(run_dir, survivors,
                                                 pkg_records),
        COMP_EXPERIMENT: _experiment_component(run_dir, survivors),
        COMP_PACKAGE: _package_component(run_dir, ranked),
    }

    preconditions = {
        PRE_VALID_QUERY: bool(valid.get("valid")),
        PRE_EVIDENCE_BOUND: bool(comps[COMP_EVIDENCE]["complete"]),
        PRE_SURVIVOR: len(survivors) >= 1,
        PRE_RECORD: all(bool(comps[c]["complete"]) for c in (
            COMP_MECHANISMS, COMP_ADVERSARIAL, COMP_ENGINEERING,
            COMP_EXPERIMENT)),
        PRE_PACKAGE: bool(comps[COMP_PACKAGE]["complete"]),
    }
    # COMPLETE_DISCOVERY_RECORD implies the evidence bound as well
    preconditions[PRE_RECORD] = preconditions[PRE_RECORD] and \
        preconditions[PRE_EVIDENCE_BOUND]

    finished = all(preconditions.values())
    missing = [c for c in COMPONENTS if not comps[c]["complete"]]

    # R399 W2.1: the scientific rejection is a TYPED terminal state —
    # the run's own verdict, never an "incomplete discovery" that
    # invites packaging recovery attempts.
    rejected = final_status == "REJECTED" or bool(
        (run_dir / "PACKAGE_SKIPPED_SCIENTIFICALLY_REJECTED.json")
        .exists())

    # ---- typed terminal state (honest, never re-labeled) --------------
    if finished:
        terminal = "FINISHED_DISCOVERY"
    elif not valid.get("valid"):
        terminal = valid.get("typed_blocker") or "INVALID_QUERY"
    elif rejected:
        terminal = final_status or "REJECTED"
    elif not survivors:
        terminal = final_status or "NO_ADMISSIBLE_SURVIVOR"
    else:
        terminal = "INCOMPLETE_DISCOVERY"

    if rejected:
        # a scientific verdict is terminal: there is no engine path
        # that "recovers" a rejected candidate into a discovery
        recovery: List[Dict[str, Any]] = []
    else:
        recovery = [e for e in (
            _recovery_entry(c, comps[c]["complete"], run_dir)
            for c in COMPONENTS) if e]

    out = {
        "schema": COMPLETION_CONTRACT_SCHEMA,
        "run_id": final.get("run_id") or (run_result or {}).get("run_id")
                  or "",
        "final_status": final_status,
        "verified_at": _utc_now(),
        "authority": (
            "this record is the final product-state authority for the "
            "run (backend, machine-checkable); the session/UI surface "
            "READS it and never re-derives FINISHED_DISCOVERY"),
        "valid_query": valid,
        "preconditions": preconditions,
        "components": comps,
        "missing_components": missing,
        "recovery": recovery,
        "competing_vs_surviving": comps[COMP_MECHANISMS][
            "competing_vs_surviving"],
        "finished_discovery": bool(finished),
        "typed_terminal_state": terminal,
        "diagnostic_only": bool(
            not survivors
            and ((ranked.get("completion") or {}).get("PIPELINE_COMPLETED")
                 or (ranked.get("completion") or {}).get(
                     "pipeline_completed"))),
        "invariant": (
            "FINISHED_DISCOVERY = VALID_QUERY + EVIDENCE_BOUND + "
            "AT_LEAST_ONE_ADMISSIBLE_SURVIVOR + COMPLETE_DISCOVERY_"
            "RECORD (6-part shape) + COMPLETE_CANDIDATE_BOUND_TECHNOLOGY"
            "_PACKAGE; typed constitutional blockers are never converted "
            "into discoveries; one survivor after competing candidates "
            "were investigated IS a finished discovery"),
    }
    if rejected:
        out["recovery_note"] = (
            "the run's terminal state is the scientific verdict "
            "REJECTED (R399 W2.1) — a typed terminal, never an "
            "incomplete discovery with a packaging recovery path")
    return out


def completion_states(contract: Optional[Dict[str, Any]]
                      ) -> Dict[str, Any]:
    """The product completion states as served to the session/UI
    surface — computed ONLY from the durable contract (the authority)."""
    if not isinstance(contract, dict):
        return {}
    comps = contract.get("components") or {}
    pre = contract.get("preconditions") or {}
    return {
        "PIPELINE_COMPLETED": bool(
            contract.get("final_status") is not None),
        "DISCOVERY_COMPLETED": bool(pre.get(PRE_SURVIVOR)),
        "TECHNOLOGY_PACKAGE_COMPLETED": bool(
            (comps.get(COMP_PACKAGE) or {}).get("complete")),
        "FINISHED_DISCOVERY": bool(contract.get("finished_discovery")),
        "typed_terminal_state": contract.get("typed_terminal_state"),
        "missing_components": list(contract.get("missing_components")
                                   or []),
    }


def persist_completion_contract(
        run_dir: Path,
        run_result: Optional[Dict[str, Any]] = None,
        package_retry: Optional[Any] = None,
) -> Dict[str, Any]:
    """Verify, run the BOUNDED automatic recovery for a recoverable
    missing package (the engine's existing compile path), re-verify,
    and persist COMPLETION_CONTRACT.json into the run dir.

    `package_retry` is the engine's own re-compile callback (run.py's
    _compile_ranked_packages + ranked result re-persist). It is invoked
    AT MOST ONCE, only when a survivor exists and the technology-package
    component is the missing piece. No other component is recovered
    here: mechanism/adversarial/experiment recovery happens inside the
    run (evolution / IMPROVE / experiment selector), and its attempt
    evidence is read from the artifacts the run already wrote."""
    run_dir = Path(run_dir)
    attempts: List[Dict[str, Any]] = []
    record = verify_completion_contract(run_dir, run_result)
    # R399 W2.1: a scientifically rejected run never triggers the
    # packaging recovery — the refusal is the product state.
    rejected = record.get("final_status") == "REJECTED" or bool(
        (run_dir / "PACKAGE_SKIPPED_SCIENTIFICALLY_REJECTED.json")
        .exists())

    try:
        pkg_ok = (record.get("components") or {}).get(
            COMP_PACKAGE, {}).get("complete")
        has_survivor = bool((record.get("preconditions") or {}).get(
            PRE_SURVIVOR))
        if not pkg_ok and has_survivor and not rejected \
                and callable(package_retry):
            attempts.append({
                "component": COMP_PACKAGE,
                "action": "PACKAGE_COMPILER_RETRY",
                "attempted_at": _utc_now(),
                "path": RECOVERY_GRAPH[COMP_PACKAGE]["path"],
            })
            try:
                package_retry()
            except Exception as exc:  # noqa: BLE001 — disclosed, the
                # verification below stays honest
                attempts[-1]["error"] = f"{type(exc).__name__}: {exc}"
            record = verify_completion_contract(run_dir, run_result)
    finally:
        record["recovery_attempts"] = attempts
        if rejected:
            # the scientific verdict is terminal — never rebuilt into a
            # recovery-shaped list (Art. XXV/W2.1)
            record["recovery"] = []
            record.setdefault(
                "recovery_note",
                "the run's terminal state is the scientific verdict "
                "REJECTED (R399 W2.1) — not a recoverable missing "
                "component")
        else:
            # refresh recovery entries with the post-attempt truth
            record["recovery"] = [
                e for e in (
                    _recovery_entry(c, (record.get("components") or {})
                                    .get(c, {}).get("complete"), run_dir,
                                    attempted_extra=bool(attempts))
                    for c in COMPONENTS) if e]
            for e in record.get("recovery") or []:
                for a in attempts:
                    if a.get("component") == e.get("component"):
                        e["attempted"] = True
                        e["exhausted"] = not (record.get("components")
                                              or {}).get(
                            e["component"], {}).get("complete")
                        e.setdefault("attempt_evidence", []).append(
                            "COMPLETION_CONTRACT.recovery_attempts")
        try:
            out = run_dir / CONTRACT_FILE
            out.write_text(json.dumps(record, indent=2,
                                      ensure_ascii=False,
                                      default=str),
                           encoding="utf-8")
        except Exception:  # noqa: BLE001 — the return value stands
            pass
    return record


def load(run_dir: Path) -> Optional[Dict[str, Any]]:
    """The durable contract record for a run (the session/UI read
    path). None when the run never reached the verifier — absence is
    honest, never a manufactured finished state."""
    return _read(Path(run_dir) / CONTRACT_FILE)

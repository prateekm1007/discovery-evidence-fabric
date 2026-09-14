"""discovery_fabric/engine/release_gate.py — CEO E16-H: the holdout
release gate.

A generated dossier can AUTOMATICALLY RELEASE only when ALL SIX gates
evaluate PASS:

    SUBSTANTIVE_DEPTH     E16-C content evaluation against the
                          TRAINING_REFERENCE distribution (content
                          evidence, not counts)
    CAUSAL_CORRECTNESS    E16-D semantic validation of every critical
                          causal chain (one INCORRECT chain blocks)
    TRACEABILITY          structural traceability passed, zero
                          untraceable critical fields, zero orphan
                          PRIMARY design inputs
    PROVENANCE            number provenance clean (no unsupported
                          numbers), display-value integrity all
                          verifiable, reasoning-chain enforcement at
                          full coverage
    DOMAIN_REASONING      why_this_domain present with equation
                          applicability verdicts AND the
                          mechanism-sensitivity answer ("what would
                          change if the mechanism changed")
    HOLDOUT_TEST          the generated package's content vector meets
                          the SEALED BLIND_HOLDOUT distribution (opened
                          only now, at evaluation time — E16-A/E16-B)

Release policy (CEO E16-H, verbatim semantics):

    RELEASED                 all six gates PASS — automatic release.
    HELD_FOR_HUMAN_REVIEW    any gate CONDITIONAL — CONDITIONAL means
                             "requires human engineering review before
                             release" and is NEVER counted as an
                             automatic PASS.
    BLOCKED                  any gate FAIL — the dossier does not leave
                             the engine.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from archive.r455_retired.discovery_fabric.engine.benchmark_split import open_sealed_blind_vectors
from .substance_metrics import (CONTENT_DIMENSIONS, content_vector,
                                evaluate_substance, reference_distribution)
from archive.r455_retired.discovery_fabric.engine.benchmark_split import list_frozen_packages, load_split

GATES = ("SUBSTANTIVE_DEPTH", "CAUSAL_CORRECTNESS", "TRACEABILITY",
         "PROVENANCE", "DOMAIN_REASONING", "HOLDOUT_TEST")

RELEASED = "RELEASED"
HELD_FOR_HUMAN_REVIEW = "HELD_FOR_HUMAN_REVIEW"
BLOCKED = "BLOCKED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _worst(verdicts: Dict[str, str]) -> str:
    if any(v == "FAIL" for v in verdicts.values()):
        return "FAIL"
    if any(v == "CONDITIONAL" for v in verdicts.values()):
        return "CONDITIONAL"
    if any(v not in ("PASS", "CONDITIONAL", "FAIL")
           for v in verdicts.values()):
        return "FAIL"
    return "PASS"


def _apply_candidate_honesty_caps(overall: str,
                                  verdicts: Dict[str, str],
                                  gates: Dict[str, Dict[str, Any]],
                                  spec: Dict[str, Any]):
    """Candidate-origin honesty caps (pure; independently tested).

    E16-F cap: an exploration-grid candidate (discovery-level
    verification NOT performed for it) can be HELD at best.

    R401 Phase 4 cap: a mechanism-space candidate whose mechanism-level
    evidence support is not affirmatively SUPPORTED can be HELD at best
    — PARTIALLY_SUPPORTED / CONTESTED / NOT_ENOUGH_EVIDENCE are honest
    non-affirmative states, never converted into automatic release. A
    SUPPORTED candidate records the affirmative MECHANISM_SUPPORT gate.
    """
    exploration = spec.get("_exploration_candidate")
    if exploration and overall == "RELEASED":
        overall = HELD_FOR_HUMAN_REVIEW
        verdicts["DISCOVERY_VERIFICATION"] = "CONDITIONAL"
        gates["DISCOVERY_VERIFICATION"] = {
            "verdict": "CONDITIONAL",
            "note": exploration.get("consequence")}
    ms_marker = spec.get("_mechanism_space_candidate")
    if ms_marker and overall == "RELEASED":
        support_state = ms_marker.get("mechanism_support_state")
        if support_state != "SUPPORTED":
            overall = HELD_FOR_HUMAN_REVIEW
            verdicts["DISCOVERY_VERIFICATION"] = "CONDITIONAL"
            gates["DISCOVERY_VERIFICATION"] = {
                "verdict": "CONDITIONAL",
                "note": (
                    f"mechanism-level evidence support state is "
                    f"{support_state} (R401 Phase 4) — "
                    + str(ms_marker.get("consequence") or ""))}
        else:
            verdicts["MECHANISM_SUPPORT"] = "PASS"
            gates["MECHANISM_SUPPORT"] = {
                "verdict": "PASS",
                "note": ("mechanism-level evidence verification found "
                         "affirmative SUPPORTS with no contradictions "
                         "(R401 Phase 4)")}
    return overall, verdicts, gates


def evaluate_release_gate(spec: Dict[str, Any], eng: Dict[str, Any],
                          package_report: Dict[str, Any],
                          causal_result: Optional[Dict[str, Any]] = None,
                          corpus_root: Optional[Path] = None,
                          ) -> Dict[str, Any]:
    """Compute the six E16-H gates for ONE generated package."""
    folder = Path(package_report.get("folder") or ".")
    gates: Dict[str, Dict[str, Any]] = {}

    reference_dirs = None
    try:
        strata = load_split()["strata"]
        reference_dirs = [d for d in list_frozen_packages(corpus_root)
                          if d.name in strata["TRAINING_REFERENCE"]]
    except Exception:  # noqa: BLE001 — recorded honestly below
        reference_dirs = None

    # 1. SUBSTANTIVE_DEPTH (E16-C)
    if reference_dirs:
        dist = reference_distribution(reference_dirs)
        cv = content_vector(folder)
        sub = evaluate_substance(cv, dist)
        gates["SUBSTANTIVE_DEPTH"] = {
            "verdict": sub["verdict"],
            "dims_at_or_above_p25": sub["dims_at_or_above_p25"],
            "deficient_areas": sub["deficient_areas"],
            "content_vector": {k: cv[k] for k in CONTENT_DIMENSIONS}}
    else:
        gates["SUBSTANTIVE_DEPTH"] = {
            "verdict": "CONDITIONAL",
            "note": "TRAINING_REFERENCE corpus not reachable from this "
                    "environment — substance could not be measured "
                    "(honest unknown, Art. XXV)"}

    # 2. CAUSAL_CORRECTNESS (E16-D)
    from .causal_correctness import evaluate_causal_correctness
    causal = causal_result or evaluate_causal_correctness(eng)
    gates["CAUSAL_CORRECTNESS"] = {
        "verdict": causal["verdict"], "counts": causal["counts"],
        "rule": causal["verdict_rule"]}
    gates["CAUSAL_CORRECTNESS"]["verdict"] = (
        "FAIL" if causal["verdict"] == "FAIL" else
        "CONDITIONAL" if causal["verdict"] == "CONDITIONAL" else "PASS")

    # 3. TRACEABILITY
    trace_path = folder / "ENGINEERING_TRACEABILITY.json"
    import json
    trace = json.loads(trace_path.read_text()) if trace_path.exists() else {}
    referenced = {pid for d in eng.get("design_outputs", [])
                  for pid in (d.get("parent_ids") or [])}
    orphans = [d["id"] for d in eng.get("design_inputs", [])
               if d.get("design_role", "PRIMARY") == "PRIMARY"
               and d["id"] not in referenced]
    trace_ok = bool(trace.get("passed")) and \
        not trace.get("untraceable_engineering_fields") and not orphans
    gates["TRACEABILITY"] = {
        "verdict": "PASS" if trace_ok else "FAIL",
        "trace_passed": bool(trace.get("passed")),
        "untraceable_fields": trace.get(
            "untraceable_engineering_fields", []),
        "orphan_primary_design_inputs": orphans}

    # 4. PROVENANCE
    np_clean = not (trace.get("number_provenance") or {}).get(
        "violations")
    manifest_path = folder / "PACKAGE_MANIFEST.json"
    display_ok = True
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        dvi = manifest.get("display_value_integrity") or {}
        display_ok = bool(dvi.get("all_mappings_verifiable"))
    ce = eng.get("chain_enforcement") or {}
    chains_full = (ce.get("coverage") == 1.0 and ce.get("enforced"))
    prov_ok = np_clean and display_ok and chains_full
    gates["PROVENANCE"] = {
        "verdict": "PASS" if prov_ok else "CONDITIONAL",
        "number_provenance_violations":
            (trace.get("number_provenance") or {}).get("violations"),
        "display_value_integrity_all_verifiable": display_ok,
        "chain_enforcement_coverage": ce.get("coverage")}

    # 5. DOMAIN_REASONING
    why = eng.get("why_this_domain") or {}
    equations = ((eng.get("engineering_core") or {})
                 .get("governing_model", {}).get("equations", []) or [])
    has_verdicts = all(
        str((e.get("selection_rationale") or {}).get("verdict") or "")
        for e in equations) if equations else False
    sens = ((why.get("mechanism_sensitivity") or {}).get("answer") or {})
    dr_ok = (bool(why.get("basis")) and bool(why.get("matched_signals"))
             and has_verdicts and bool(sens)
             and bool(sens.get("governing_models_at_risk") is not None))
    gates["DOMAIN_REASONING"] = {
        "verdict": "PASS" if dr_ok else "CONDITIONAL",
        "why_this_domain_present": bool(why.get("basis")),
        "matched_signals": why.get("matched_signals"),
        "all_equations_judged": has_verdicts,
        "mechanism_sensitivity_present": bool(sens),
        "mechanism_sensitivity_models_at_risk": len(
            sens.get("governing_models_at_risk") or [])}

    # 6. HOLDOUT_TEST — the seal is opened HERE, at evaluation time
    try:
        sealed = open_sealed_blind_vectors()
        blind_content = [v["content"] for v in
                         sealed["vectors"].values()]
        cv = gates["SUBSTANTIVE_DEPTH"].get("content_vector") or \
            content_vector(folder)
        dims_ok = 0
        dim_results = {}
        guard_violations = []
        for dim in CONTENT_DIMENSIONS:
            got = cv.get(dim)
            ref_min = min(b.get(dim, 0) for b in blind_content)
            ok = isinstance(got, (int, float)) and got >= ref_min
            dim_results[dim] = {"value": got, "blind_min": ref_min,
                                "at_or_above_blind_min": ok}
            if ok:
                dims_ok += 1
            elif not (isinstance(got, (int, float))
                      and got >= 0.5 * ref_min):
                guard_violations.append(dim)
        holdout_pass = dims_ok >= 7 and not guard_violations
        gates["HOLDOUT_TEST"] = {
            "verdict": "PASS" if holdout_pass else
            ("CONDITIONAL" if dims_ok >= 5 and not guard_violations
             else "FAIL"),
            "seal_verified": True,
            "blind_packages": sorted(sealed["vectors"].keys()),
            "dims_at_or_above_blind_min": dims_ok,
            "dimensions": dim_results,
            "policy": (">= 7/10 content dimensions at or above the blind "
                       "holdout minimum and no dimension below 0.5x that "
                       "minimum")}
    except RuntimeError as exc:
        gates["HOLDOUT_TEST"] = {
            "verdict": "CONDITIONAL",
            "note": f"sealed holdout could not be opened: {exc}"}

    verdicts = {g: gates[g]["verdict"] for g in GATES}
    overall = _worst(verdicts)
    overall, verdicts, gates = _apply_candidate_honesty_caps(
        overall, verdicts, gates, spec)
    policy = {
        RELEASED: "all six gates PASS",
        HELD_FOR_HUMAN_REVIEW: ("any gate CONDITIONAL — requires human "
                                "engineering review before release; "
                                "NEVER counted as an automatic PASS "
                                "(CEO E16-H)"),
        BLOCKED: "any gate FAIL — the dossier does not leave the engine",
    }
    return {
        "gate": "E16_HOLDOUT_RELEASE_GATE",
        "version": "1.0.0",
        "gates": gates,
        "verdicts": verdicts,
        "decision": overall,
        "decision_rule": (f"{RELEASED} = all six PASS; "
                          f"{HELD_FOR_HUMAN_REVIEW} = any CONDITIONAL; "
                          f"{BLOCKED} = any FAIL"),
        "policy_detail": policy,
        "evaluated_at": utc_now(),
    }

"""Phase 3 — substantive dossier quality evaluator (Coder 2).

Evaluates a generated dossier on 13 dimensions with PASS / CONDITIONAL /
FAIL verdicts and machine-readable reasons. NO vanity scores (no "94/100").

Phase 7 is built in: every dimension reports SECTION_PRESENT separately
from ENGINEERING_DEPTH — a section can exist and still be too shallow.

Dimensions:
    MECHANISM_DEPTH, ENGINEERING_REASONING_DEPTH, DESIGN_TRACEABILITY,
    EQUATION_APPLICABILITY, PARAMETER_PROVENANCE, FAILURE_ANALYSIS_DEPTH,
    VERIFICATION_SPECIFICITY, VALIDATION_SPECIFICITY,
    MANUFACTURING_REASONING, TRANSFER_SPECIFICITY, BUYER_ACTIONABILITY,
    EVIDENCE_DENSITY, UNKNOWN_DISCLOSURE
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import equation_integrity as eq_mod
from . import reasoning_audit as ra_mod
from . import vv_separation as vv_mod
from . import transfer_audit as tf_mod


def _reason(code: str, detail: str, **kw) -> Dict[str, Any]:
    r = {"code": code, "detail": detail}
    r.update(kw)
    return r


def _verdict_from(reasons: List[Dict[str, Any]]) -> str:
    if any(r.get("severity") == "FAIL" for r in reasons):
        return "FAIL"
    if any(r.get("severity") == "CONDITIONAL" for r in reasons):
        return "CONDITIONAL"
    return "PASS"


def _floor(contract: Dict[str, Any], section: str, key: str) -> Optional[Any]:
    for s in contract.get("sections", []):
        if s.get("section") == section:
            return (s.get("minimum_depth") or {}).get(key)
    return None


def evaluate_dossier(metrics: Dict[str, Any],
                     contract: Optional[Dict[str, Any]] = None,
                     profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Evaluate one package's dossier quality against the depth contract."""
    contract = contract or {}
    eng = metrics.get("eng_spec")
    inv = metrics.get("inv_spec")
    objs = metrics.get("objects") or {}
    td = metrics.get("traceability_density") or {}
    dims: Dict[str, Dict[str, Any]] = {}

    def floor(section: str, key: str, default=None):
        v = _floor(contract, section, key)
        return default if v is None else v

    # ---------------------------------------------------------------- 1
    dims["MECHANISM_DEPTH"] = _mechanism_depth(metrics, profile)
    # ---------------------------------------------------------------- 2
    reasoning = ra_mod.audit_reasoning(eng, inv)
    dims["ENGINEERING_REASONING_DEPTH"] = {
        "section_present": reasoning.get("available", False),
        "chain_completeness_rate": reasoning.get("completeness_rate"),
        "chains_total": reasoning.get("chains_total"),
        "chains_complete": reasoning.get("chains_complete"),
        "verdict": reasoning.get("verdict") if reasoning.get("available")
        else "NOT_MEASURABLE",
        "reasons": [] if not reasoning.get("available") else [
            _reason("REASONING_CHAINS", f"{reasoning.get('chains_complete')}"
                    f"/{reasoning.get('chains_total')} design-output chains "
                    f"complete",
                    severity=("PASS" if reasoning.get("completeness_rate", 0)
                              >= 0.5 else
                              "CONDITIONAL" if reasoning.get(
                                  "chains_complete", 0) > 0 else "FAIL"))],
    }
    # ---------------------------------------------------------------- 3
    dims["DESIGN_TRACEABILITY"] = _traceability(metrics, td, objs, floor)
    # ---------------------------------------------------------------- 4
    eq_floor = floor("ENGINEERING_CORE", "equations")
    eq_audit = eq_mod.audit_equations(eng, floor_equations=eq_floor)
    eq_issues = [f"{e['equation_id']}: {i}" for e in
                 eq_audit.get("equations", []) for i in e["issues"]]
    if eq_audit.get("count_floor_issue"):
        eq_issues.append(eq_audit["count_floor_issue"])
    dims["EQUATION_APPLICABILITY"] = {
        "section_present": eq_audit.get("available", False),
        "equations_total": eq_audit.get("equations_total"),
        "equations_with_issues": eq_audit.get("equations_with_issues"),
        "issues": eq_issues,
        "verdict": eq_audit.get("verdict"),
        "reasons": ([_reason("EQUATION_ISSUES", i, severity="FAIL")
                     for i in eq_issues]
                    if eq_audit.get("available") else
                    [_reason("NOT_MEASURABLE", "no engineering spec",
                             severity="CONDITIONAL")]),
    }
    # ---------------------------------------------------------------- 5
    # numerical provenance is audited by the runner (needs run_dir for
    # source corpus); the dimension consumes its result when provided
    dims["PARAMETER_PROVENANCE"] = metrics.get("_param_provenance_dim") or {
        "section_present": eng is not None,
        "verdict": "NOT_MEASURABLE",
        "reasons": [_reason("DEFERRED", "numerical provenance audit runs "
                            "with run-dir sources", severity="CONDITIONAL")],
    }
    # ---------------------------------------------------------------- 6
    dims["FAILURE_ANALYSIS_DEPTH"] = _failure_analysis(metrics, floor)
    # ---------------------------------------------------------------- 7
    dims["VERIFICATION_SPECIFICITY"] = _verification(metrics, floor)
    # ---------------------------------------------------------------- 8
    vv_audit = vv_mod.audit_vv_separation(
        eng, None)
    val_total = (metrics.get("vv_probe") or {}).get("validations_total")
    if val_total is None:
        val_total = objs.get("validations")
    dims["VALIDATION_SPECIFICITY"] = {
        "section_present": bool(val_total),
        "validations_total": val_total,
        "validation_honesty_basis": (metrics.get("vv_probe") or {}).get("validation_honesty_basis"),
        "vv_violations": vv_audit.get("violations"),
        "verdict": ("FAIL" if vv_audit.get("violation_count") else
                    "PASS" if val_total else
                    "CONDITIONAL"),
        "reasons": ([_reason("VV_VIOLATION", v["violation"] + ": " +
                             v["detail"], severity="FAIL")
                     for v in vv_audit.get("violations", [])] or
                    ([_reason("VALIDATIONS_AT_FLOOR",
                              f"{val_total} "
                              f"validation item(s), honestly NOT_PERFORMED",
                              severity="PASS")])),
    }
    # ---------------------------------------------------------------- 9
    dims["MANUFACTURING_REASONING"] = _manufacturing(metrics, floor)
    # ---------------------------------------------------------------- 10
    dims["TRANSFER_SPECIFICITY"] = _transfer(metrics)
    # ---------------------------------------------------------------- 11
    dims["BUYER_ACTIONABILITY"] = _buyer_actionability(metrics, floor)
    # ---------------------------------------------------------------- 12
    dims["EVIDENCE_DENSITY"] = _evidence_density(metrics, td, objs, floor)
    # ---------------------------------------------------------------- 13
    dims["UNKNOWN_DISCLOSURE"] = _unknown_disclosure(metrics, floor)

    overall = "PASS"
    if any(d["verdict"] == "FAIL" for d in dims.values()):
        overall = "FAIL"
    elif any(d["verdict"] in ("CONDITIONAL", "NOT_MEASURABLE")
             for d in dims.values()):
        overall = "CONDITIONAL"

    return {
        "artifact": "DOSSIER_QUALITY_EVALUATION",
        "owner": "CODER2",
        "package_id": metrics.get("package_id"),
        "dimensions": dims,
        "dimension_verdicts": {k: d["verdict"] for k, d in dims.items()},
        "overall_verdict": overall,
        "verdict_vocabulary": ["PASS", "CONDITIONAL", "FAIL",
                               "NOT_MEASURABLE"],
        "no_vanity_scores": "no numeric quality score is emitted by design",
    }


# ---------------------------------------------------------------------------
def _mechanism_depth(m, profile) -> Dict[str, Any]:
    eng = m.get("eng_spec")
    inv = m.get("inv_spec") or {}
    reasons = []
    present = False
    if eng:
        ma = eng.get("mechanism_architecture") or {}
        present = bool(ma.get("physical_changes"))
        if not present:
            reasons.append(_reason("MECHANISM_ABSENT",
                                   "mechanism architecture has no physical "
                                   "change statement", severity="FAIL"))
        else:
            reasons.append(_reason("MECHANISM_PRESENT",
                                   "physical change statement present",
                                   severity="PASS"))
        if not ma.get("key_physics"):
            reasons.append(_reason("PHYSICS_ABSENT", "no key physics "
                                   "recorded", severity="CONDITIONAL"))
    cc = (inv.get("causal_chain") or {}).get("value") \
        if isinstance(inv.get("causal_chain"), dict) else None
    if cc:
        reasons.append(_reason("CAUSAL_CHAIN_PRESENT",
                               "invention specification carries a causal "
                               "chain", severity="PASS"))
    elif eng:
        reasons.append(_reason("CAUSAL_CHAIN_ABSENT",
                               "no causal chain in invention specification",
                               severity="CONDITIONAL"))
    # depth signal: mechanism text length in dossier sections 1-2
    sc = (m.get("section_coverage") or {}).get("section_chars") or {}
    mech_chars = int(sc.get("1", 0)) + int(sc.get("2", 0))
    corpus_floor = _section_chars_floor(profile, (1, 2))
    if corpus_floor and mech_chars:
        reasons.append(_reason(
            "MECHANISM_SECTION_DEPTH",
            f"sections 1+2 render {mech_chars} chars vs corpus floor "
            f"{corpus_floor}",
            severity="PASS" if mech_chars >= corpus_floor * 0.5 else
            "CONDITIONAL"))
    return {"section_present": present or bool(sc),
            "mechanism_section_chars": mech_chars,
            "corpus_floor_mechanism_chars": corpus_floor,
            "verdict": _verdict_from(reasons),
            "reasons": reasons}


def _section_chars_floor(profile, nums) -> Optional[int]:
    if not profile:
        return None
    totals = []
    for p in profile.get("packages", []):
        sc = (p.get("section_coverage") or {}).get("section_chars") or {}
        t = sum(int(sc.get(str(n), 0)) for n in nums)
        totals.append(t)
    return min(totals) if totals else None


def _traceability(m, td, objs, floor) -> Dict[str, Any]:
    reasons = []
    chains = td.get("chains_total")
    rate = td.get("chain_linkage_rate")
    ev_per_obj = td.get("evidence_ids_per_object")
    f_chains = floor("DESIGN_CHAIN", "traceability_chains")
    f_rate = floor("DESIGN_CHAIN", "chain_linkage_rate")
    f_evpo = floor("DESIGN_CHAIN", "evidence_ids_per_object")
    f_orphan_do = floor("DESIGN_CHAIN", "orphan_design_outputs_max")
    f_di = floor("DESIGN_CHAIN", "design_inputs")
    f_do = floor("DESIGN_CHAIN", "design_outputs")
    if f_di is not None and objs.get("design_inputs") is not None:
        reasons.append(_reason(
            "DI_COUNT", f"{objs['design_inputs']} design inputs vs corpus "
            f"floor {f_di}",
            severity="PASS" if objs["design_inputs"] >= f_di else "FAIL",
            count=objs["design_inputs"], floor=f_di))
    if f_do is not None and objs.get("design_outputs") is not None:
        reasons.append(_reason(
            "DO_COUNT", f"{objs['design_outputs']} design outputs vs corpus "
            f"floor {f_do}",
            severity="PASS" if objs["design_outputs"] >= f_do else "FAIL",
            count=objs["design_outputs"], floor=f_do))
    if chains is not None and f_chains is not None:
        reasons.append(_reason(
            "CHAIN_COUNT", f"{chains} chains vs corpus floor {f_chains}",
            severity="PASS" if chains >= f_chains else "FAIL",
            count=chains, floor=f_chains))
    if rate is not None and f_rate is not None:
        reasons.append(_reason(
            "LINKAGE_RATE", f"chain linkage rate {rate:.3f} vs corpus "
            f"floor {f_rate:.3f}",
            severity="PASS" if rate >= f_rate else "FAIL", rate=rate))
    if ev_per_obj is not None and f_evpo is not None:
        reasons.append(_reason(
            "EVIDENCE_BINDING", f"{ev_per_obj:.3f} evidence ids per object "
            f"vs corpus floor {f_evpo:.3f}",
            severity="PASS" if ev_per_obj >= f_evpo else "FAIL",
            rate=ev_per_obj))
    orphan_do = td.get("orphan_design_outputs")
    if orphan_do is not None and f_orphan_do is not None:
        reasons.append(_reason(
            "ORPHAN_DESIGN_OUTPUTS",
            f"{orphan_do} orphan design outputs vs corpus ceiling "
            f"{f_orphan_do}",
            severity="FAIL" if orphan_do > f_orphan_do else
            ("CONDITIONAL" if orphan_do > 1 else "PASS"),
            count=orphan_do, ceiling=f_orphan_do))
    return {"section_present": bool(chains),
            "chains_total": chains, "chains_linked": td.get("chains_linked"),
            "chain_linkage_rate": rate,
            "evidence_ids_per_object": ev_per_obj,
            "orphan_design_outputs": orphan_do,
            "orphan_failure_modes": td.get("orphan_failure_modes"),
            "verdict": _verdict_from(reasons), "reasons": reasons}


def _failure_analysis(m, floor) -> Dict[str, Any]:
    objs = m.get("objects") or {}
    eng = m.get("eng_spec")
    reasons = []
    n = objs.get("failure_modes")
    f = floor("FAILURE_ANALYSIS", "failure_modes")
    if n is not None and f is not None:
        reasons.append(_reason(
            "FM_COUNT", f"{n} failure modes vs corpus floor {f}",
            severity="PASS" if n >= f else "FAIL", count=n, floor=f))
    # Phase 7 depth: mechanism specificity / design controls / verification
    # links per failure mode
    specificity = None
    if eng:
        fms = [x for x in (eng.get("failure_analysis", []) or [])
               if isinstance(x, dict)]
        with_mechanism = sum(1 for x in fms if x.get("mechanism") and
                             "NOT ESTABLISHED" not in
                             str(x.get("mechanism")).upper())
        with_mitigation = sum(1 for x in fms if x.get("mitigation") and
                              "NOT ESTABLISHED" not in
                              str(x.get("mitigation")).upper())
        with_verification = sum(1 for x in fms if x.get("verification") and
                                "NOT ESTABLISHED" not in
                                str(x.get("verification")).upper())
        with_uncertainty = sum(1 for x in fms if x.get("residual_uncertainty"))
        specificity = {
            "failure_modes_total": len(fms),
            "with_mechanism": with_mechanism,
            "with_design_control_mitigation": with_mitigation,
            "with_verification_link": with_verification,
            "with_residual_uncertainty": with_uncertainty,
        }
        if fms:
            if with_mitigation == 0:
                reasons.append(_reason(
                    "NO_DESIGN_CONTROLS", "zero failure modes carry a "
                    "design-control mitigation", severity="FAIL"))
            elif with_mitigation < len(fms) / 2:
                reasons.append(_reason(
                    "WEAK_DESIGN_CONTROLS",
                    f"{with_mitigation}/{len(fms)} failure modes carry "
                    f"design-control mitigations", severity="CONDITIONAL"))
            else:
                reasons.append(_reason(
                    "DESIGN_CONTROLS",
                    f"{with_mitigation}/{len(fms)} failure modes carry "
                    f"design-control mitigations", severity="PASS"))
            if with_verification == 0:
                reasons.append(_reason(
                    "NO_VERIFICATION_LINKS", "zero failure modes link a "
                    "verification", severity="CONDITIONAL"))
    return {"section_present": n is not None and n > 0,
            "failure_modes": n, "mechanism_specificity": specificity,
            "verdict": _verdict_from(reasons), "reasons": reasons}


def _verification(m, floor) -> Dict[str, Any]:
    objs = m.get("objects") or {}
    eng = m.get("eng_spec")
    reasons = []
    n = objs.get("verifications")
    f = floor("VERIFICATION_VALIDATION", "verifications")
    if n is not None and f is not None:
        reasons.append(_reason(
            "VF_COUNT", f"{n} verification items vs corpus floor {f}",
            severity="PASS" if n >= f else "FAIL", count=n, floor=f))
    specificity = None
    if eng:
        vfs = [v for v in (eng.get("verification_matrix", []) or [])
               if isinstance(v, dict)]
        with_method = sum(1 for v in vfs if v.get("method") and
                          "NOT ESTABLISHED" not in str(v.get("method")).upper())
        with_acceptance = sum(1 for v in vfs if v.get("acceptance") and
                              "NOT ESTABLISHED" not in
                              str(v.get("acceptance")).upper())
        specificity = {"verifications_total": len(vfs),
                       "with_method": with_method,
                       "with_acceptance_criterion": with_acceptance}
        if vfs:
            if with_acceptance == 0:
                reasons.append(_reason(
                    "NO_ACCEPTANCE_CRITERIA", "zero verification rows carry "
                    "an acceptance criterion (all NOT ESTABLISHED)",
                    severity="FAIL"))
            elif with_acceptance < len(vfs) / 2:
                reasons.append(_reason(
                    "WEAK_ACCEPTANCE_CRITERIA",
                    f"{with_acceptance}/{len(vfs)} rows carry acceptance "
                    f"criteria", severity="CONDITIONAL"))
    return {"section_present": n is not None and n > 0,
            "verifications": n, "specificity": specificity,
            "verdict": _verdict_from(reasons), "reasons": reasons}


def _manufacturing(m, floor) -> Dict[str, Any]:
    mfg = m.get("manufacturing") or {}
    reg = m.get("regulatory") or {}
    reasons = []
    if mfg.get("has_processes") or mfg.get("candidate_processes"):
        reasons.append(_reason("MFG_PROCESSES", "candidate manufacturing "
                               "processes present", severity="PASS"))
    else:
        reasons.append(_reason("MFG_ABSENT", "no manufacturing processes "
                               "recorded", severity="CONDITIONAL"))
    if reg.get("has_regulatory_di") or (reg.get("regulatory_di_count") or 0) > 0:
        reasons.append(_reason("REG_DI", "regulatory design input present",
                               severity="PASS"))
    else:
        reasons.append(_reason("REG_DI_ABSENT", "regulatory design input "
                               "absent", severity="FAIL"))
    return {"section_present": True,
            "manufacturing": mfg, "regulatory": reg,
            "verdict": _verdict_from(reasons), "reasons": reasons}


def _transfer(m) -> Dict[str, Any]:
    audit = tf_mod.audit_transfer(m)
    return {"section_present": bool(audit.get("buyer_must_verify_present")),
            "audit": audit,
            "verdict": audit["verdict"],
            "reasons": ([_reason(v["violation"], v["detail"],
                                 severity="FAIL")
                         for v in audit["violations"]] or
                        [_reason("TRANSFER_BOUNDARY_INTACT",
                                 "receive/develop/verify boundary intact; "
                                 "transfer_ready honestly "
                                 f"{audit.get('transfer_ready_reported')}",
                                 severity="PASS")])}


def _buyer_actionability(m, floor) -> Dict[str, Any]:
    bd = m.get("buyer_decision") or {}
    ke = m.get("killer_experiment") or {}
    objs = m.get("objects") or {}
    reasons = []
    present = len(bd.get("elements_present") or [])
    if present < 9:
        reasons.append(_reason("BUYER_ELEMENTS", f"{present}/9 buyer "
                               "decision elements present",
                               severity="FAIL" if present < 7 else
                               "CONDITIONAL"))
    else:
        reasons.append(_reason("BUYER_ELEMENTS", "all 9 buyer decision "
                               "elements present", severity="PASS"))
    if not ke.get("block_present"):
        reasons.append(_reason("DECISIVE_EXPERIMENT_ABSENT", "no decisive "
                               "experiment block", severity="FAIL"))
    else:
        if ke.get("has_measurable_criterion"):
            reasons.append(_reason("DECISIVE_EXPERIMENT_MEASURABLE",
                                   "decisive experiment carries a "
                                   "measurable criterion", severity="PASS"))
        else:
            reasons.append(_reason("DECISIVE_EXPERIMENT_VAGUE",
                                   "decisive experiment lacks measurable "
                                   "criterion", severity="CONDITIONAL"))
    bp = objs.get("build_plan_steps")
    f_bp = floor("DOSSIER_COMPLETENESS", "build_plan_steps")
    if bp is not None and f_bp is not None and f_bp != "CORPUS_FLOOR":
        reasons.append(_reason("BUILD_PLAN", f"{bp} build-plan steps",
                               severity="PASS" if bp >= 5 else "CONDITIONAL"))
    return {"section_present": present > 0,
            "buyer_decision_elements": present,
            "killer_experiment": ke,
            "build_plan_steps": bp,
            "verdict": _verdict_from(reasons), "reasons": reasons}


def _evidence_density(m, td, objs, floor) -> Dict[str, Any]:
    reasons = []
    ext = objs.get("external_evidence")
    f_ext = floor("EVIDENCE_PROVENANCE", "external_evidence")
    f_evpo = floor("EVIDENCE_PROVENANCE", "evidence_ids_per_object")
    if ext is not None and f_ext is not None:
        reasons.append(_reason(
            "EXTERNAL_EVIDENCE", f"{ext} external evidence items vs corpus "
            f"floor {f_ext}",
            severity="PASS" if ext >= f_ext else "FAIL",
            count=ext, floor=f_ext))
    evpo = td.get("evidence_ids_per_object")
    if evpo is not None and f_evpo is not None:
        reasons.append(_reason(
            "EVIDENCE_PER_OBJECT", f"{evpo:.3f} evidence ids per object vs "
            f"corpus floor {f_evpo:.3f}",
            severity="PASS" if evpo >= f_evpo else "FAIL"))
    unsup = td.get("unsupported_numbers")
    if unsup is not None:
        reasons.append(_reason(
            "UNSUPPORTED_NUMBERS", f"{unsup} unsupported numbers",
            severity="FAIL" if unsup else "PASS"))
    return {"section_present": ext is not None and ext > 0,
            "external_evidence": ext,
            "evidence_ids_per_object": evpo,
            "verdict": _verdict_from(reasons), "reasons": reasons}


def _unknown_disclosure(m, floor) -> Dict[str, Any]:
    ud = m.get("unknown_disclosure") or {}
    objs = m.get("objects") or {}
    reasons = []
    markers = ud.get("markers_total")
    f_markers = floor("ENGINEERING_CORE", "unknown_markers")
    if markers is not None and f_markers is not None:
        reasons.append(_reason(
            "UNKNOWN_MARKERS", f"{markers} unknown markers vs corpus floor "
            f"{f_markers}",
            severity="PASS" if markers >= f_markers else "CONDITIONAL",
            count=markers, floor=f_markers))
    ru = objs.get("remaining_unknowns")
    f_ru = floor("ENGINEERING_CORE", "remaining_unknowns")
    if ru is not None and f_ru is not None:
        reasons.append(_reason(
            "REMAINING_UNKNOWNS", f"{ru} remaining unknowns vs corpus floor "
            f"{f_ru}",
            severity="PASS" if ru >= f_ru else "FAIL"))
    return {"section_present": markers is not None,
            "unknown_markers": markers,
            "by_marker": ud.get("by_marker"),
            "remaining_unknowns": ru,
            "verdict": _verdict_from(reasons), "reasons": reasons}

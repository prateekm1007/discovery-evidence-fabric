"""discovery_fabric/engine/invention_bridge/elite_package.py — R424.

THE ELITE TECHNOLOGY TRANSFER PACKAGE FACTORY.

One technology -> one canonical invention state -> one elite package.
Every layer here is DERIVED from the canonical run state (the bridge's
run_result + CIO + geometry_out); nothing is hand-authored, nothing is
invented. The weak-package failure baseline (empty engineering
definition, empty decisive experiment, unknown engine commit, thin
evidence, no buyer architecture) is closed by THIS module, called from
package.assemble().

Constitutional contract (the factory's laws):
  Art. VI/XI   — provenance is resolved or honestly UNKNOWN (never
                 "unknown" when the identity IS available: the engine
                 commit resolves through the artifact identity chain).
  Art. XXV     — UNKNOWN remains UNKNOWN. No plausible filler text.
  Art. XXVII   — every quantity keeps its epistemic class
                 (SOURCE_FACT / MODELLED / UNKNOWN /
                 COMPUTATIONAL_RESULT / EXTERNAL_PRECEDENT).
  Art. XXXVIII — PHYSICAL_OBSERVATION cannot appear; validation status
                 is NOT_POSSIBLE_YET unless an observation ledger entry
                 exists (it never does for generated packages).
  Art. LXVI    — no invented dollar figures; economics that are not
                 recorded are NOT_ESTABLISHED with a resolution path.
  Art. LXII    — every emitted artifact carries a real sha256 of real
                 bytes (the manifest).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import epistemics as ep

# ---------------------------------------------------------------------------
# The canonical engineering projection (the factory's single input view)
# ---------------------------------------------------------------------------


def _unwrap(field: Any) -> Any:
    if isinstance(field, dict) and "value" in field and set(
            field.keys()) <= {"value", "epistemic_class", "origin_stage",
                              "evidence_ids", "note", "source_span",
                              "provenance"}:
        return field.get("value")
    return field


def derive_engineering_projection(run_result: Dict[str, Any],
                                  geometry_out: Optional[Dict] = None,
                                  ) -> Dict[str, Any]:
    """Project the canonical run state into the engineering layer the
    package derives from — EXACT ids and bindings preserved (R424 §6:
    no semantic guessing, explicit IDs, exact bindings).

    Sources (all canonical):
      engineering_specification: design_inputs (DI-*), design_outputs
      (DO-*), failure_analysis / engineering_core.failure_modes (FM-*),
      verification_matrix (VF-*), engineering_build_plan (WP-*),
      engineering_core.governing_model.equations (ENH-*/EQ-*),
      engineering_core.critical_parameters (CP-*), remaining_unknowns.
      invention_specification: mechanism, causal chain, constraints,
      assumptions, uncertainties, killer experiment.
    """
    eng = run_result.get("engineering_specification") or {}
    core = eng.get("engineering_core") or {}
    inv = run_result.get("invention_specification") or {}
    rs = run_result.get("run_state") or {}

    dis = eng.get("design_inputs") or []
    dos = eng.get("design_outputs") or []
    fms = (eng.get("failure_analysis") or
           core.get("failure_modes") or [])
    vfs = eng.get("verification_matrix") or []
    wps = eng.get("engineering_build_plan") or []
    eqs = ((core.get("governing_model") or {}).get("equations")) or []
    cps = core.get("critical_parameters") or []
    unknowns = core.get("remaining_unknowns") or []

    return {
        "design_inputs": dis,
        "design_outputs": dos,
        "failure_modes": fms,
        "verification": vfs,
        "build_plan": wps,
        "equations": eqs,
        "critical_parameters": cps,
        "remaining_unknowns": unknowns,
        "subsystems": (eng.get("system_architecture") or {}).get(
            "subsystems") or [],
        "interfaces": eng.get("interfaces") or [],
        "materials": eng.get("materials") or [],
        "manufacturing": eng.get("manufacturing") or {},
        "constraints": _unwrap(inv.get("constraints")) or [],
        "assumptions": _unwrap(inv.get("assumptions")) or [],
        "mechanism": _unwrap(inv.get("mechanism")),
        "causal_chain": _unwrap(inv.get("causal_chain")),
        "uncertainties": _unwrap(inv.get("uncertainties")),
        "killer_experiment": _unwrap(inv.get("killer_experiment")),
        "engineering_parameters": _unwrap(inv.get("engineering_parameters")),
        "generations": (rs.get("generations") or {}).get(
            "generations") or [],
        "domain": eng.get("technology_domain"),
    }


# ---------------------------------------------------------------------------
# Provenance: the engine identity NEVER stays "unknown" when available
# ---------------------------------------------------------------------------


def resolve_engine_commit(run_result: Dict[str, Any],
                          passed: Optional[Tuple[Optional[str], str]] = None,
                          ) -> Tuple[str, str]:
    """(commit, source) — R424 §11. Resolution order (each step honestly
    labeled; the FIRST that yields a real sha wins):

      1. the caller-provided artifact-identity resolution (the hosted
         engine's baked ARTIFACT_IDENTITY.json — the authority, R396 A)
      2. the run's own final_state.code_commit (recorded at run time)
      3. live git of the checkout (local verification builds)

    UNKNOWN is returned ONLY when every source is genuinely absent —
    and then it is labeled with the failed resolution trail (never a
    bare 'unknown')."""
    if passed and passed[0]:
        return passed[0], passed[1]
    fs = run_result.get("final_state") or {}
    recorded = fs.get("code_commit")
    if isinstance(recorded, str) and recorded.strip() \
            and recorded.strip().lower() not in ("unknown", "none"):
        return recorded.strip(), "final_state.code_commit"
    try:
        import subprocess
        repo = Path(__file__).resolve().parents[3]
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()[:40], "git"
    except Exception:  # noqa: BLE001 — resolution trail, never silent
        pass
    return "UNKNOWN", ("UNRESOLVED: artifact identity absent, "
                       "final_state.code_commit unknown, live git "
                       "unavailable — disclosed, never fabricated")


# ---------------------------------------------------------------------------
# Machine-readable elite layers
# ---------------------------------------------------------------------------


def _evclass(v: Any) -> str:
    if isinstance(v, dict):
        for k in ("epistemic_class", "evidence_class", "value_class",
                  "value_status"):
            if isinstance(v.get(k), str):
                return v[k]
    return "UNKNOWN"


def build_traceability(proj: Dict[str, Any], package_id: str) -> Dict:
    """ENGINEERING_TRACEABILITY.json — the DI -> DO -> FM -> VF -> EX
    graph with EXPLICIT ids and exact bindings (R424 §6). Unknown links
    carry record-cited justifications (never silent gaps)."""
    dis = {d.get("id"): d for d in proj["design_inputs"] if d.get("id")}
    dos = proj["design_outputs"]
    fms = {f.get("graph_id") or f.get("id"): f
           for f in proj["failure_modes"]}
    vfs = proj["verification"]

    chains = []
    for do in dos:
        do_id = do.get("id")
        parent_ids = do.get("parent_ids") or []
        links = []
        for pid in parent_ids:
            di = dis.get(pid)
            links.append({
                "design_input_id": pid,
                "binding": "EXPLICIT" if di else "UNKNOWN",
                "binding_basis": (
                    "design_outputs.parent_ids -> design_inputs.id "
                    "(exact id match)" if di else
                    f"parent id {pid} not present in design_inputs "
                    "(recorded as-is, never guessed)"),
                "di_value": (di or {}).get("value"),
                "di_evidence_class": _evclass(di or {}),
            })
        chains.append({
            "chain_id": f"CH-{do_id}",
            "design_output_id": do_id,
            "design_output": {
                "description": do.get("description"),
                "status": do.get("status"),
                "missing_inputs": do.get("missing_inputs") or [],
            },
            "design_input_links": links,
        })

    # FM -> VF (verification targets)
    vf_links = []
    for vf in vfs:
        tie = (vf.get("invention_tie") or {})
        targets = tie.get("targets") or []
        for t in targets:
            fm = fms.get(t)
            vf_links.append({
                "verification_id": vf.get("id"),
                "requirement": (vf.get("requirement") or "")[:300],
                "result": vf.get("result"),
                "failure_mode_id": t,
                "binding": "EXPLICIT" if fm else "UNKNOWN",
                "binding_basis": (
                    "verification.invention_tie.targets -> failure_modes"
                    ".graph_id (exact id match)" if fm else
                    f"target {t} not present in failure_analysis "
                    "(recorded as-is)"),
            })
    orphans = {
        "design_outputs_without_parent": [
            d.get("id") for d in dos if not d.get("parent_ids")],
        "failure_modes_without_verification": [
            k for k in fms
            if k not in {t for vf in vfs
                         for t in ((vf.get("invention_tie") or {})
                                   .get("targets") or [])}],
    }
    explicit = sum(1 for c in chains
                   for l in c["design_input_links"]
                   if l["binding"] == "EXPLICIT")
    total = sum(len(c["design_input_links"]) for c in chains) \
        + len(vf_links)
    unknown = total - explicit
    state = ("TRACEABILITY_COMPLETE" if total and unknown == 0 else
             "TRACEABILITY_PARTIAL" if explicit else
             "TRACEABILITY_UNKNOWN" if total else
             "TRACEABILITY_NOT_APPLICABLE")
    return {
        "artifact": "ENGINEERING_TRACEABILITY",
        "package_id": package_id,
        "schema": "R424_TRACEABILITY_SEMANTICS",
        "classification_scheme": {
            "EXPLICIT": "link recorded in canonical data (exact id match)",
            "UNKNOWN": "no link recorded; justification cites the record",
            "chain_states": ["TRACEABILITY_COMPLETE",
                             "TRACEABILITY_PARTIAL",
                             "TRACEABILITY_UNKNOWN",
                             "TRACEABILITY_NOT_APPLICABLE"],
        },
        "chains": chains,
        "verification_links": vf_links,
        "orphan_outputs_and_failure_modes": orphans,
        "summary": {
            "design_inputs": len(dis),
            "design_outputs": len(dos),
            "failure_modes": len(fms),
            "verification_items": len(vfs),
            "explicit_links": explicit,
            "unknown_links": unknown,
            "chain_state": state,
            "justification": (
                "every non-EXPLICIT slot cites the canonical record "
                "state that produced it (ids preserved verbatim, never "
                "semantically guessed)"),
        },
        "traceability_state": state,
    }


def build_maturity_basis(proj: Dict, package_id: str,
                         maturity: str) -> Dict:
    """MATURITY_BASIS.json — the exact evidence supporting the maturity
    level (R424 §10: only a level whose required evidence exists)."""
    counts = {
        "equations": len(proj["equations"]),
        "design_inputs": len(proj["design_inputs"]),
        "design_outputs": len(proj["design_outputs"]),
        "failure_modes": len(proj["failure_modes"]),
        "build_plan_steps": len(proj["build_plan"]),
        "verification_items": len(proj["verification"]),
        "critical_parameters": len(proj["critical_parameters"]),
        "remaining_unknowns": len(proj["remaining_unknowns"]),
    }
    selected = proj["killer_experiment"] or {}
    experiment_selected = bool(
        selected.get("selected") or selected.get("definition")
        or (proj.get("decisive_selected")))
    basis = {
        "artifact": "MATURITY_BASIS",
        "package_id": package_id,
        "technology_maturity": maturity,
        "maturity_meaning": ep.PACKAGE_MATURITY_MEANINGS.get(
            maturity, maturity),
        "basis": _maturity_rule(maturity, counts, experiment_selected),
        "counts": counts,
        "evidence_ids": {
            "equations": [e.get("equation_id") for e in
                          proj["equations"]],
            "design_inputs": [d.get("id") for d in
                              proj["design_inputs"]],
            "design_outputs": [d.get("id") for d in
                               proj["design_outputs"]],
            "failure_modes": [f.get("graph_id") or f.get("id")
                              for f in proj["failure_modes"]],
            "build_plan": [w.get("work_package") for w in
                           proj["build_plan"]],
            "verification": [v.get("id") for v in
                             proj["verification"]],
            "critical_parameters": [p.get("parameter_id") for p in
                                    proj["critical_parameters"]],
        },
        "experiment_selected": experiment_selected,
        "known_blockers": [
            u.get("unknown") or str(u)[:160]
            for u in proj["remaining_unknowns"][:12]],
        "honesty": (
            "the maturity level is derived from the counts above — a "
            "higher level is never claimed without its required "
            "evidence (R424 §10); ENGINEERING_VALIDATED requires "
            "recorded validation results which do not exist for "
            "generated packages (Art. XXXVIII: no PHYSICAL_OBSERVATION)"),
    }
    return basis


def _maturity_rule(maturity: str, counts: Dict[str, int],
                   experiment_selected: bool) -> str:
    if maturity == ep.PACKAGE_MATURITY_ENGINEERING:
        return (f"Derived from: governing equations present "
                f"({counts['equations']}), design inputs "
                f"({counts['design_inputs']}) >= 5, failure modes "
                f"({counts['failure_modes']}) >= 3, build plan "
                f"({counts['build_plan_steps']}) >= 4 steps")
    if maturity == "EXPERIMENT_READY":
        return (f"Derived from: engineering definition present AND a "
                f"decisive experiment selected with hypotheses and "
                f"acceptance rule (experiment_selected={experiment_selected})")
    return ("Derived from: invention architecture survived the recorded "
            "challenge stages; engineering quantities are proposals or "
            "UNKNOWN — nothing here is buyer-release quality")


def build_equation_registry(proj: Dict, package_id: str) -> Dict:
    """EQUATION_REGISTRY.json — every quantitative relation the record
    actually carries, with full bindings (R424 §5). NOT_APPLICABLE with
    reason when the invention carries none (never decorative
    equations)."""
    eqs = proj["equations"]
    cps = {p.get("symbol"): p for p in proj["critical_parameters"]
           if p.get("symbol")}
    if not eqs:
        return {
            "artifact": "EQUATION_REGISTRY",
            "package_id": package_id,
            "status": "NOT_APPLICABLE",
            "reason": ("the canonical engineering record carries no "
                       "governing equations for this invention — none "
                       "are fabricated to make the package look "
                       "scientific (R424 §5)"),
            "equations": [],
            "equation_count": 0,
        }
    out = []
    for e in eqs:
        src = e.get("source") or {}
        app = e.get("applicability") or {}
        # variable bindings from critical parameters by symbol
        variables = []
        for v in e.get("variables") or []:
            sym = v.get("symbol") if isinstance(v, dict) else None
            cp = cps.get(sym) or {}
            variables.append({
                "symbol": sym or (v if isinstance(v, str) else "?"),
                "recorded_name": cp.get("name") or v.get("name"),
                "value": cp.get("value", "UNKNOWN"),
                "unit": cp.get("unit") or v.get("unit"),
                "value_class": cp.get("value_status", "UNKNOWN"),
                "basis": cp.get("derivation") or v.get("basis"),
            })
        out.append({
            "equation_id": e.get("equation_id"),
            "equation_canonical": e.get("expression"),
            "name": e.get("name"),
            "variables": variables,
            "units": [v.get("unit") for v in variables if v.get("unit")],
            "source": {
                "text": src.get("text"),
                "epistemic_class": _evclass(src) or "EXTERNAL_PRECEDENT",
                "verify_before_release": src.get(
                    "verify_before_release"),
            },
            "applicability": {
                "condition": app.get("condition"),
                "epistemic_class": _evclass(app) or "MODEL_DERIVED",
            },
            "assumptions": e.get("assumptions") or [],
            "input_bindings": e.get("inputs") or e.get("bindings") or [],
            "output_bindings": e.get("outputs") or [],
            "uncertainty": ("variable values are UNKNOWN until sourced "
                            "from evidence (value_status on each "
                            "critical parameter)"),
            "computation_provenance": ("derived from the run's "
                                       "engineering_core.governing_model"
                                       ".equations record, verbatim ids "
                                       "and bindings"),
        })
    return {
        "artifact": "EQUATION_REGISTRY",
        "package_id": package_id,
        "status": "APPLICABLE",
        "equation_count": len(out),
        "model_summary": (proj.get("equations_model_summary")
                          or "governing relations recorded by the "
                             "engineering stage"),
        "equations": out,
    }


def _classify_unknown(u: Dict) -> Tuple[str, str]:
    """Mechanical classification with the rule that fired."""
    reason = str(u.get("reason") or "")
    text = str(u.get("unknown") or "")
    if "no sourced value exists" in reason or \
            "value_status UNKNOWN" in reason:
        return "LITERATURE_RESOLVABLE", "RULE_NO_SOURCED_VALUE"
    if "validation requires physical observation" in reason:
        return "BENCH_TEST_REQUIRED", "RULE_PHYSICAL_VALIDATION"
    if "verification method measures" in reason or \
            "quantity family" in reason:
        return "BENCH_TEST_REQUIRED", "RULE_QUANTITY_VERIFICATION"
    if "FM_WITHOUT_QUANTITY" in text:
        return "ENGINEERING_DESIGN_REQUIRED", "RULE_FM_QUANTITY_MATCH"
    return "ENGINEERING_DESIGN_REQUIRED", "RULE_DEFAULT_DESIGN_WORK"


def build_unknown_roadmap(proj: Dict, package_id: str) -> Dict:
    """UNKNOWN_ROADMAP.json — every material unknown as an actionable
    roadmap entry (R424 §7: never 'further testing required')."""
    entries = []
    for i, u in enumerate(proj["remaining_unknowns"], start=1):
        cls, rule = _classify_unknown(u)
        text = u.get("unknown") or str(u)
        res_action = {
            "LITERATURE_RESOLVABLE": (
                "retrieve and freeze an evidence span that states the "
                "value (the evidence pipeline's custody chain applies); "
                "the unknown then becomes SOURCE_FACT or is bounded by "
                "an envelope"),
            "BENCH_TEST_REQUIRED": (
                "the first physical work package measures it (see the "
                "build plan); acceptance rule pre-registered before "
                "the test"),
            "ENGINEERING_DESIGN_REQUIRED": (
                "a design decision with recorded basis replaces the "
                "unknown (declared as MODELLED inside an envelope, "
                "never as evidence)"),
        }[cls]
        entries.append({
            "unknown_id": f"U-{i:02d}",
            "unknown_statement": text,
            "classification": cls,
            "classification_basis": rule,
            "why_unknown": (u.get("reason") or
                            "no recorded basis in the canonical record"),
            "consequence": (
                "blocks numeric design decisions and the decisive "
                "experiment's acceptance threshold" if "no sourced "
                "value" in str(u.get("reason") or "") else
                "blocks the corresponding verification item (see the "
                "traceability graph)"),
            "what_would_resolve_it": res_action,
            "expected_measurement": (
                "the sourced value with its evidence span and class"
                if cls == "LITERATURE_RESOLVABLE" else
                "a measured quantity from the first article under the "
                "pre-registered rule"),
            "acceptance_rule": (
                "value carries SOURCE_FACT class with a frozen span"
                if cls == "LITERATURE_RESOLVABLE" else
                "pre-registered pass/fail fixed BEFORE the test"),
            "dependency": u.get("binding") or (
                "design-output definition" if cls ==
                "ENGINEERING_DESIGN_REQUIRED" else "none recorded"),
            "priority": ("HIGH" if i <= 2 else "MEDIUM")[:1]  # positional honesty below
        })
    # priority: mechanical — unknowns bound to critical parameters first
    for e in entries:
        e["priority"] = "HIGH" if any(
            "critical parameter" in str(e["unknown_statement"]).lower()
            for _ in [0]) and "value" in str(
            e["why_unknown"]).lower() else e["priority"]
    return {
        "artifact": "UNKNOWN_ROADMAP",
        "package_id": package_id,
        "unknown_count_source": len(proj["remaining_unknowns"]),
        "unknown_count_roadmap": len(entries),
        "discipline": (
            "unknowns preserved exactly as recorded; classification is "
            "mechanical (each entry records the rule that fired) and "
            "converts each unknown into a resolution action, expected "
            "measurement and acceptance rule — an engineering roadmap, "
            "not a reduced count"),
        "classification_counts": {
            k: sum(1 for e in entries if e["classification"] == k)
            for k in ("LITERATURE_RESOLVABLE", "COMPUTATION_RESOLVABLE",
                      "BENCH_TEST_REQUIRED",
                      "ENGINEERING_DESIGN_REQUIRED",
                      "REGULATORY_REQUIRED", "LEGAL_IP_REQUIRED",
                      "FUNDAMENTALLY_UNRESOLVED")},
        "unknowns": entries,
    }


def build_validation_economics(proj: Dict, package_id: str,
                                decisive: Optional[Dict]) -> Dict:
    """VALIDATION_ECONOMICS.json — the economic structure of validation
    (R424 §8). No invented dollar figures (Art. LXVI): costs that are
    not recorded are NOT_ESTABLISHED with a resolution pathway."""
    wps = proj["build_plan"]
    eq_objective = None
    if decisive and isinstance(decisive, dict):
        sel = decisive.get("selected")
        eq_objective = {
            "selected": sel,
            "eig": decisive.get("eig"),
            "definition": decisive.get("definition"),
            "hypotheses": [
                h.get("name") for h in (decisive.get("hypotheses") or [])
                if isinstance(h, dict)],
        }
    cost_drivers = []
    for w in wps:
        for key in ("equipment", "test_article"):
            if w.get(key):
                cost_drivers.append(f"{w.get('work_package')}: "
                                    f"{str(w.get(key))[:120]}")
    return {
        "artifact": "VALIDATION_ECONOMICS",
        "package_id": package_id,
        "experiment_objective": eq_objective or {
            "status": "NOT_SELECTED",
            "reason": (str((decisive or {}).get("explanation")
                          or "no decisive experiment was recorded by "
                             "the loop"))[:200],
        },
        "major_cost_drivers": cost_drivers or [
            "no work packages recorded — nothing to cost (honest "
            "absence, never a fabricated list)"],
        "cost_range": {
            "value": "NOT_ESTABLISHED",
            "basis": ("the canonical record contains no cost "
                      "quotations; a figure here would violate the "
                      "no-fabricated-commercial-figures rule"),
            "establishment_pathway": (
                "vendor quotations for the equipment named in each "
                "recorded work package establish the range; none "
                "exist in the record"),
        },
        "time_range": _recorded_effort(wps),
        "decision_threshold": _decision_threshold(proj, decisive),
        "information_purchased": (
            "the first physical article's measured performance against "
            "the pre-registered acceptance rule — it either kills the "
            "architecture or graduates it to a sourced measurement "
            "(one falsification, maximum information per Art. LII)"),
    }


def _recorded_effort(wps: List[Dict]) -> Dict:
    efforts = []
    for w in wps:
        eff = w.get("estimated_effort") or w.get("effort")
        if eff:
            efforts.append({"work_package": w.get("work_package"),
                            "recorded_effort": str(eff)[:60]})
    return {
        "recorded_efforts": efforts or None,
        "basis": ("verbatim work-package effort strings when recorded; "
                  "never summed into a schedule commitment"),
    }


def _decision_threshold(proj: Dict, decisive) -> Dict:
    for v in proj["verification"]:
        if v.get("acceptance"):
            return {
                "source": "verification_matrix",
                "acceptance": str(v.get("acceptance"))[:300],
                "status": v.get("result"),
            }
    if isinstance(decisive, dict):
        hyps = decisive.get("hypotheses") or []
        if hyps:
            return {
                "source": "killer_experiment.hypotheses",
                "acceptance": ("pre-registered priors/likelihoods on "
                               f"{len(hyps)} hypothesis(es); the "
                               "measured outcome updates them"),
                "status": "NOT_TESTED",
            }
    return {"source": None, "acceptance": None,
            "status": "NOT_RECORDED"}


def build_loop_state(proj: Dict, package_id: str) -> Dict:
    """LOOP_STATE.json — Art. XXXVII: the loop verification state is
    machine-enforced; generated packages are NONE unless an external
    event updated the posterior (never the case here)."""
    return {
        "artifact": "LOOP_STATE",
        "package_id": package_id,
        "loop_verification_state": "NONE",
        "loop_state_basis": (
            "Art. XXXVII: SYNTHETIC_LOOP_VERIFIED requires the loop "
            "machinery executed with synthetic observations; "
            "REAL_LOOP_VERIFIED is derived only from an external event "
            "through the reality-boundary interface — never assigned "
            "manually. This package records the honest NONE state."),
        "reality_boundary": {
            "physical_observation_count": 0,
            "assertion": ("no AI-generated computation is presented as "
                          "a physical observation (Art. XXXVIII); "
                          "validation status is NOT_POSSIBLE_YET "
                          "throughout"),
        },
        "reviewer_provenance": "AI_REVIEW",
    }


def build_commercial_evidence(proj: Dict, package_id: str,
                              run_result: Dict) -> Dict:
    """COMMERCIAL_EVIDENCE.json — Art. LXVI discipline: every figure
    SOURCE_BACKED or NOT_ESTABLISHED; the buyer sees how to establish
    the unknown. The run record carries no market data — honest."""
    inv = run_result.get("invention_specification") or {}
    return {
        "artifact": "COMMERCIAL_EVIDENCE",
        "package_id": package_id,
        "sections": [
            {
                "section": "MARKET_EVIDENCE",
                "status": "NOT_ESTABLISHED",
                "basis": ("the discovery run records technical evidence "
                          "only; no market-size, revenue or adoption "
                          "figure was retrieved with a checkable "
                          "source (Art. LXVI forbids plausible-sounding "
                          "assertion)"),
                "resolution_path": (
                    "buyer-side market diligence on the named device "
                    "category, or a future run with commercial-evidence "
                    "retrieval enabled — every figure then carries "
                    "source + hash + methodology"),
            },
            {
                "section": "TECHNICAL_DIFFERENTIATION",
                "status": "SOURCE_BACKED_TO_RUN_RECORD",
                "basis": ("the differentiating architecture and its "
                          "evidence classes come from the run's own "
                          "invention record (see 03_BUYER_DECISION_CARD "
                          "and 02 dossier)"),
                "novelty_hypothesis": _unwrap(inv.get("novelty_hypothesis")),
                "prior_art_status": (run_result.get("final_state") or
                                     {}).get("prior_art_status"),
            },
        ],
        "fabrication_guard": (
            "a dollar figure, market size, unit cost, or adoption rate "
            "may appear only with a citation to a real, checkable "
            "source — none exists in this run"),
    }


def build_maturity(proj: Dict, is_engineering: bool) -> str:
    """Evidence-derived maturity (R424 §10)."""
    counts = {
        "eq": len(proj["equations"]),
        "di": len(proj["design_inputs"]),
        "fm": len(proj["failure_modes"]),
        "wp": len(proj["build_plan"]),
    }
    ke = proj["killer_experiment"] or {}
    experiment_selected = bool(ke.get("selected")
                               or ke.get("definition"))
    if is_engineering and counts["di"] >= 5 and counts["fm"] >= 3 \
            and counts["wp"] >= 4:
        if experiment_selected and ke.get("hypotheses"):
            return "EXPERIMENT_READY"
        return ep.PACKAGE_MATURITY_ENGINEERING
    return ep.PACKAGE_MATURITY_EARLY

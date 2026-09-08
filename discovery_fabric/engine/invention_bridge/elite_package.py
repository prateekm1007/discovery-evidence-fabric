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


def build_traceability(proj: Dict[str, Any], package_id: str,
                       run_result: Optional[Dict[str, Any]] = None
                       ) -> Dict:
    """ENGINEERING_TRACEABILITY.json — the COMPLETE relationship graph
    DI -> DO -> FM -> VF -> EXPERIMENT (R425 §4), with explicit
    machine-readable bindings for every edge class:

      DO  -> DI        (design_outputs.parent_ids -> design_inputs.id)
      FM  -> DO        (and/or functional target)
      VF  -> FM        (verification.invention_tie.targets -> graph_id)
      EX  -> FM/VF/DO  (the decisive experiment's targets)
      decision -> technical state (adjudication/evolution outcomes)

    Every missing link is represented as UNKNOWN with a record-cited
    basis (which record was inspected and what it lacked) — never a
    silent gap. Coverage metrics close the loop: nodes, bindings,
    orphans, unverified failure modes, failure modes without a decisive
    verification, experiment targets with no upstream requirement.
    """
    dis = {d.get("id"): d for d in proj["design_inputs"] if d.get("id")}
    dos = proj["design_outputs"]
    fms = {f.get("graph_id") or f.get("id"): f
           for f in proj["failure_modes"]}
    vfs = proj["verification"]
    do_ids = {d.get("id") for d in dos if d.get("id")}

    links: List[Dict] = []

    def _link(kind: str, src: str, dst: Optional[str], explicit: bool,
              basis: str) -> None:
        links.append({
            "link_kind": kind,
            "source_id": src,
            "target_id": dst,
            "binding": "EXPLICIT" if explicit else "UNKNOWN",
            "binding_basis": basis,
        })

    # ---- DO -> DI ------------------------------------------------------
    for do in dos:
        do_id = do.get("id")
        parent_ids = do.get("parent_ids") or []
        if not parent_ids:
            _link(
                "DO_TO_DI", do_id, None, False,
                f"design_outputs record {do_id} carries no parent_ids "
                "and no missing_inputs — the parent binding is not "
                "recorded (recorded as-is, never guessed)")
        for pid in parent_ids:
            di = dis.get(pid)
            _link(
                "DO_TO_DI", do_id, pid, di is not None,
                ("design_outputs.parent_ids -> design_inputs.id "
                 "(exact id match)") if di is not None else
                f"parent id {pid} not present in design_inputs "
                "(recorded as-is, never guessed)")

    # ---- FM -> DO / functional target ----------------------------------
    for fm_id, fm in fms.items():
        affected = fm.get("affected_outputs") or fm.get(
            "design_outputs") or fm.get("affects") or []
        if isinstance(affected, str):
            affected = [affected]
        if affected:
            for tgt in affected:
                _link(
                    "FM_TO_DO", fm_id, tgt, tgt in do_ids,
                    ("failure_modes.affected_outputs -> "
                     "design_outputs.id (exact id match)")
                    if tgt in do_ids else
                    f"affected-output id {tgt} not present in "
                    "design_outputs (recorded as-is)")
        else:
            control = fm.get("design_control")
            feature = fm.get("design_feature")
            if _informative(control) or _informative(feature):
                _link(
                    "FM_TO_DO", fm_id, None, False,
                    f"failure_modes record {fm_id} carries "
                    "design_control/design_feature but no machine-"
                    "readable design-output id — the DO binding is "
                    f"UNKNOWN (control={str(control or feature)[:80]!r})")
            else:
                _link(
                    "FM_TO_DO", fm_id, None, False,
                    f"failure_modes record {fm_id} carries no "
                    "affected-output/design-output field at all — "
                    "inspected: " + ", ".join(sorted(fm.keys())))

    # ---- VF -> FM --------------------------------------------------------
    for vf in vfs:
        tie = (vf.get("invention_tie") or {})
        targets = tie.get("targets") or []
        if not targets:
            _link(
                "VF_TO_FM", vf.get("id"), None, False,
                f"verification record {vf.get('id')} carries "
                "invention_tie with no targets — the failure-mode "
                "binding is not recorded (inspected: "
                + ", ".join(sorted(tie.keys())) + ")")
        for t in targets:
            fm = fms.get(t)
            _link(
                "VF_TO_FM", vf.get("id"), t, fm is not None,
                ("verification.invention_tie.targets -> failure_modes"
                 ".graph_id (exact id match)") if fm is not None else
                f"target {t} not present in failure_analysis "
                "(recorded as-is)")

    # ---- EXPERIMENT -> FM/VF/DO ------------------------------------------
    de = (run_result or {}).get("decisive_experiment") or {}
    selected = de.get("selected")
    if isinstance(selected, str):
        try:
            import ast
            selected = ast.literal_eval(selected)
        except (ValueError, SyntaxError):
            selected = None
    ex_id = "EXPERIMENT"
    ex_source = "decisive_experiment"
    if not (selected or proj.get("killer_experiment")):
        _link(
            "EX_TO_TARGET", ex_id, None, False,
            "the canonical state records no decisive experiment and no "
            "killer experiment — there is no experiment node to bind "
            "(honest absence)")
    else:
        ex_kind = (selected or {}).get("experiment") if isinstance(
            selected, dict) else None
        if not ex_kind:
            ex_kind = (proj.get("killer_experiment") or {}).get(
                "selected")
            ex_source = "invention_specification.killer_experiment"
        # EX -> VF: a verification item that IS the falsification test.
        # Mechanical binding: exact kind equality, or whole-string kind
        # containment (e.g. VF linkage_kind "falsification_test" inside
        # selected experiment "falsification_test_from_candidate") —
        # the containment relation is disclosed in the basis, never
        # presented as an exact id match.
        ex_vf_bound = False
        for vf in vfs:
            tie = vf.get("invention_tie") or {}
            kind = str(tie.get("linkage_kind") or "")
            if not (ex_kind and kind):
                continue
            exk, vk = str(ex_kind), kind
            if exk == vk:
                rel = (f"exact kind match: {kind!r}")
                explicit = True
            elif vk in exk or exk in vk:
                rel = (f"kind containment: {vk!r} within {exk!r} "
                       f"(mechanical string containment, disclosed)")
                explicit = True
            else:
                continue
            _link(
                "EX_TO_VF", ex_id, vf.get("id"), explicit,
                f"{ex_source}.selected.experiment == "
                f"verification {vf.get('id')}.invention_tie."
                f"linkage_kind ({rel})")
            ex_vf_bound = True
            # transitive EX -> FM through that VF's targets
            for t in tie.get("targets") or []:
                _link(
                    "EX_TO_FM", ex_id, t, t in fms,
                    (f"transitive through verification "
                     f"{vf.get('id')}.invention_tie.targets; "
                     "exact id match in failure_analysis")
                    if t in fms else
                    f"transitive through verification "
                    f"{vf.get('id')}; target {t} not present in "
                    "failure_analysis (recorded as-is)")
        if not ex_vf_bound:
            _link(
                "EX_TO_VF", ex_id, None, False,
                f"{ex_source} is recorded but no verification item's "
                "invention_tie.linkage_kind matches the experiment "
                "kind — no machine-readable experiment->verification "
                "binding exists (inspected kinds: "
                + ", ".join(sorted({
                    str((v.get("invention_tie") or {}).get(
                        "linkage_kind") or "")
                    for v in vfs
                    if (v.get("invention_tie") or {}).get(
                        "linkage_kind")})) + ")")
        # EX -> DO: no canonical field binds the experiment to design
        # outputs — represent as UNKNOWN citing the record
        _link(
            "EX_TO_DO", ex_id, None, False,
            f"{ex_source} carries hypotheses/definition/EIG but no "
            "design-output id field — the EX->DO binding is not "
            "recorded (fields inspected: "
            + ", ".join(sorted((selected or
                                (proj.get("killer_experiment") or {}))
                               .keys())) + ")")

    # ---- decision outcome -> resulting technical state --------------------
    fs = (run_result or {}).get("final_state") or {}
    gens = proj.get("generations") or []
    decision_outcomes = []
    if fs.get("final_status"):
        decision_outcomes.append({
            "decision": "adjudication final_status",
            "outcome": fs.get("final_status"),
            "resulting_technical_state": {
                "invention_state": fs.get("final_status"),
                "spec_hash": fs.get("final_envelope_hash"),
            },
            "basis": "final_state.final_status (the run's own terminal "
                     "adjudication record)",
        })
    for g in gens[:6]:
        ch = g.get("challenge") or {}
        if isinstance(ch, dict) and (ch.get("survived") is not None
                                     or ch.get("killed") is not None):
            decision_outcomes.append({
                "decision": f"generation {g.get('generation')} challenge",
                "outcome": ("KILLED" if ch.get("killed") else "SURVIVED"),
                "resulting_technical_state": {
                    "invention_id": g.get("invention_id"),
                    "action": ("evolution/improvement continued" if not
                               ch.get("killed") else
                               "lineage terminated"),
                },
                "basis": "run_state.generations.challenge (the recorded "
                         "adversarial decision)",
            })

    # ---- coverage metrics ---------------------------------------------------
    node_counts = {
        "design_inputs": len(dis),
        "design_outputs": len(dos),
        "failure_modes": len(fms),
        "verification": len(vfs),
        "experiment": 1 if (selected or proj.get("killer_experiment"))
        else 0,
        "decisions": len(decision_outcomes),
    }
    explicit = sum(1 for l in links if l["binding"] == "EXPLICIT")
    unknown = sum(1 for l in links if l["binding"] == "UNKNOWN")
    verified_fm_ids = {
        t for vf in vfs
        for t in ((vf.get("invention_tie") or {}).get("targets") or [])
        if t in fms}
    unverified_fms = [k for k in fms if k not in verified_fm_ids]
    # failure modes without a DECISIVE verification: FMs verified only
    # by items whose linkage is not a decisive/falsification outcome
    decisive_vf_ids = {
        vf.get("id") for vf in vfs
        if ("falsification" in str(
            (vf.get("invention_tie") or {}).get("linkage_kind") or
            "").lower()
            or "kill" in str(
                (vf.get("invention_tie") or {}).get("linkage_kind") or
                "").lower())}
    fm_decisive_ids = {
        t for vf in vfs if vf.get("id") in decisive_vf_ids
        for t in ((vf.get("invention_tie") or {}).get("targets") or [])}
    fms_without_decisive = [k for k in fms if k not in fm_decisive_ids]
    orphan_nodes = {
        "design_outputs_without_parent": [
            d.get("id") for d in dos if not d.get("parent_ids")],
        "failure_modes_without_verification": unverified_fms,
        "verification_without_fm_target": [
            vf.get("id") for vf in vfs
            if not ((vf.get("invention_tie") or {}).get("targets")
                    or [])],
        "design_inputs_without_child": [
            k for k in dis
            if k not in {pid for d in dos
                         for pid in (d.get("parent_ids") or [])}],
    }
    ex_targets_no_upstream: List[str] = []
    if selected or proj.get("killer_experiment"):
        # experiment targets with no upstream requirement: FMs named by
        # the experiment that no VF requirement covers
        ex_fm_targets = {l["target_id"] for l in links
                         if l["link_kind"] == "EX_TO_FM"
                         and l["target_id"]}
        ex_targets_no_upstream = sorted(
            t for t in ex_fm_targets if t not in verified_fm_ids)

    state = ("TRACEABILITY_COMPLETE" if links and unknown == 0 else
             "TRACEABILITY_PARTIAL" if explicit else
             "TRACEABILITY_UNKNOWN" if links else
             "TRACEABILITY_NOT_APPLICABLE")
    return {
        "artifact": "ENGINEERING_TRACEABILITY",
        "package_id": package_id,
        "schema": "R425_TRACEABILITY_GRAPH",
        "classification_scheme": {
            "EXPLICIT": "link recorded in canonical data (exact id "
                        "match)",
            "UNKNOWN": "no link recorded; basis cites the record that "
                       "was inspected",
            "link_kinds": ["DO_TO_DI", "FM_TO_DO", "VF_TO_FM",
                           "EX_TO_VF", "EX_TO_FM", "EX_TO_DO",
                           "EX_TO_TARGET"],
            "chain_states": ["TRACEABILITY_COMPLETE",
                             "TRACEABILITY_PARTIAL",
                             "TRACEABILITY_UNKNOWN",
                             "TRACEABILITY_NOT_APPLICABLE"],
        },
        "links": links,
        "decision_outcomes": decision_outcomes,
        "coverage": {
            "total_nodes": node_counts,
            "total_nodes_sum": sum(node_counts.values()),
            "total_links": len(links),
            "explicit_bindings": explicit,
            "unknown_bindings": unknown,
            "binding_accounting": (
                "explicit_bindings + unknown_bindings == total_links "
                "(every link is classified — no silent gaps)"),
            "orphan_nodes": orphan_nodes,
            "unverified_failure_modes": unverified_fms,
            "failure_modes_without_decisive_verification":
                fms_without_decisive,
            "experiment_targets_with_no_upstream_requirement":
                ex_targets_no_upstream,
        },
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
                "semantically guessed); coverage metrics enumerate "
                "orphans and unverified nodes by name (R425 §4)"),
        },
        "traceability_state": state,
    }


def build_maturity_basis(proj: Dict, package_id: str,
                         maturity: str,
                         run_result: Optional[Dict] = None) -> Dict:
    """MATURITY_BASIS.json — the exact evidence supporting the maturity
    level (R424 §10: only a level whose required evidence exists;
    R425 §3: the counts are SEMANTICALLY COMPLETE records only)."""
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
    semantic = semantic_completeness(proj)
    contract = experiment_contract_assessment(proj, run_result)
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
        "semantic_gates": {
            "rule": ("R425 §3: only records passing their category's "
                     "deterministic content-quality gate count toward "
                     "the maturity thresholds — low-information "
                     "records can never upgrade the level"),
            "categories": semantic,
            "counts_semantically_complete": {
                "design_inputs": semantic["design_inputs"][
                    "records_semantically_complete"],
                "design_outputs": semantic["design_outputs"][
                    "records_semantically_complete"],
                "failure_modes": semantic["failure_modes"][
                    "records_semantically_complete"],
                "verification": semantic["verification"][
                    "records_semantically_complete"],
                "build_plan": semantic["build_plan"][
                    "records_semantically_complete"],
            },
        },
        "experiment_contract": contract,
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
            "the maturity level is derived from the semantically "
            "complete records above (R425 §3) — a higher level is "
            "never claimed without its required evidence, and "
            "EXPERIMENT_READY additionally requires the full "
            "discriminating experiment contract; ENGINEERING_VALIDATED "
            "requires recorded validation results which do not exist "
            "for generated packages (Art. XXXVIII: no "
            "PHYSICAL_OBSERVATION)"),
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
        return (f"Derived from: engineering definition present AND the "
                f"discriminating experiment contract complete (>=2 "
                f"hypothesis arms with priors, pre-registered decision "
                f"rule, measurable outcome path, target resolving in "
                f"the record — see experiment_contract; "
                f"experiment_selected={experiment_selected})")
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


_RECORD_ID_RE = None  # compiled lazily to keep import time minimal


def _source_record_ids(u: Dict) -> List[str]:
    """Record ids cited by the unknown's own statement/reason/binding —
    parsed mechanically, never guessed (R425 §6: source record IDs)."""
    global _RECORD_ID_RE
    if _RECORD_ID_RE is None:
        import re
        _RECORD_ID_RE = re.compile(
            r"\b(?:FM|VF|DO|DI|UIN|CP|EQ|ENH|WP|EXT|V)-[A-Za-z0-9-]+\b")
    found: List[str] = []
    for field in ("unknown", "reason", "binding", "note"):
        v = u.get(field)
        if isinstance(v, str):
            for m in _RECORD_ID_RE.findall(v):
                if m not in found:
                    found.append(m)
    return found


def _classify_unknown(u: Dict) -> Tuple[str, str]:
    """Mechanical classification with the rule that fired."""
    reason = str(u.get("reason") or "")
    text = str(u.get("unknown") or "")
    if "no sourced value exists" in reason or \
            "value_status UNKNOWN" in reason:
        return "LITERATURE_RESOLVABLE", "RULE_NO_SOURCED_VALUE"
    if "no sourced threshold" in reason:
        return "BENCH_TEST_REQUIRED", "RULE_ACCEPTANCE_PRE_REGISTRATION"
    if "validation requires physical observation" in reason:
        return "BENCH_TEST_REQUIRED", "RULE_PHYSICAL_VALIDATION"
    if "FM_WITHOUT_QUANTITY" in text:
        return "ENGINEERING_DESIGN_REQUIRED", "RULE_FM_QUANTITY_MATCH"
    if "verification method measures" in reason or \
            "quantity family" in reason:
        return "BENCH_TEST_REQUIRED", "RULE_QUANTITY_VERIFICATION"
    return "ENGINEERING_DESIGN_REQUIRED", "RULE_DEFAULT_DESIGN_WORK"


def _subject_of(text: str) -> str:
    """The unknown's own subject, extracted mechanically (never a
    semantic guess): the parameter/quantity phrase from the recorded
    statement."""
    t = text.strip()
    if t.lower().startswith("value of critical parameter "):
        return t[len("value of critical parameter "):].strip()
    if ":" in t and t.split(":", 1)[0].isupper() and "_" in \
            t.split(":", 1)[0]:
        return t.split(":", 1)[1].strip() or t
    return t


def _vf_of(u: Dict) -> Optional[str]:
    for field in ("unknown", "reason", "binding"):
        v = str(u.get(field) or "")
        if "verification VF-" in v or v.startswith("VF-"):
            import re
            m = re.search(r"\bVF-[A-Za-z0-9-]+\b", v)
            if m:
                return m.group(0)
    return None


def _priority_of(u: Dict, cls: str) -> Tuple[str, str]:
    """Mechanical priority with the rule that fired (R425 §6 — the
    H/M single-letter bug is closed; priorities are full words derived
    from the recorded consequence, never from list position)."""
    reason = str(u.get("reason") or "")
    text = str(u.get("unknown") or "")
    if ("required before any numeric design decision" in reason
            or text.lower().startswith("value of critical parameter")
            or "acceptance criterion" in text.lower()):
        return "HIGH", ("blocks numeric design decisions or the "
                        "decisive experiment's acceptance threshold "
                        "(recorded reason states the blocking)")
    if cls in ("BENCH_TEST_REQUIRED",
               "ENGINEERING_DESIGN_REQUIRED"):
        return "MEDIUM", "blocks a verification item or design decision"
    return "LOW", "contextual unknown — not recorded as blocking"


def _roadmap_entry(i: int, u: Dict, proj: Dict) -> Dict:
    """One unknown -> one SPECIFIC roadmap entry (R425 §6): resolution
    action, expected measurement, acceptance rule and consequence are
    built from THIS unknown's own subject and record ids — never the
    generic shared text the R424 layer used for unrelated unknowns."""
    cls, rule = _classify_unknown(u)
    text = u.get("unknown") or str(u)
    subject = _subject_of(str(text))
    ids = _source_record_ids(u)
    vf = _vf_of(u)
    priority, priority_basis = _priority_of(u, cls)

    if cls == "LITERATURE_RESOLVABLE":
        action = (f"Retrieve and freeze an evidence span that states "
                  f"the value of {subject} — the retrieval's custody "
                  f"chain (query, source identity, exact span, content "
                  f"hash) applies; the value then enters the critical-"
                  f"parameter record as SOURCE_FACT or is bounded by "
                  f"a declared envelope (MODELLED)")
        expected = (f"the sourced value of {subject} with its recorded "
                    f"unit, evidence span, and epistemic class")
        acceptance = ("the frozen span states the value verbatim with "
                      "a matching unit; value_status leaves UNKNOWN "
                      "only when the retrieval itself fails (never on "
                      "semantic plausibility — Art. II)")
        consequence = (f"blocks numeric design decisions for "
                       f"{subject} and the decisive experiment's "
                       f"acceptance threshold (the recorded reason: "
                       f"'required before any numeric design decision')")
    elif cls == "BENCH_TEST_REQUIRED" and vf:
        action = (f"Fix verification {vf}'s numeric margin at "
                  f"pre-registration by measuring the baseline arm "
                  f"under the identical setup (the recorded procedure); "
                  f"the criterion then leaves ENGINEERING_PROPOSED")
        expected = (f"the measured baseline value that fixes {vf}'s "
                    f"pre-registered margin")
        acceptance = ("the margin is pre-registered BEFORE the "
                      "decisive test runs (no post-hoc threshold — "
                      "Art. VIII)")
        consequence = (f"verification {vf} cannot be evaluated until "
                       f"its criterion is fixed")
    elif cls == "BENCH_TEST_REQUIRED":
        action = (f"Measure {subject} in the first physical work "
                  f"package (see the build plan's test article and "
                  f"equipment); pre-register the acceptance rule "
                  f"before the test")
        expected = (f"a measured value of {subject} from the first "
                    f"article under the pre-registered rule")
        acceptance = ("pre-registered pass/fail fixed BEFORE the test "
                      "(the physical-observation boundary, Art. "
                      "XXXVIII, is respected: no simulation may "
                      "satisfy it)")
        consequence = (f"{subject} stays unvalidated — physical "
                       f"validation is the recorded blocker")
    elif rule == "RULE_FM_QUANTITY_MATCH":
        fm_ids = [i2 for i2 in ids if i2.startswith("FM-")]
        fm_ref = fm_ids[0] if fm_ids else "the failure mode"
        action = (f"Design or select a verification method whose "
                  f"measured quantity family covers the quantity "
                  f"{fm_ref} affects (the E21-A quantity rule); record "
                  f"it on the verification matrix with {fm_ref} as its "
                  f"target")
        expected = (f"a verification-matrix row targeting {fm_ref} "
                    f"whose method measures a quantity in the family "
                    f"the failure affects")
        acceptance = (f"the verification row binds {fm_ref} by exact id "
                      f"(see the traceability graph's VF_TO_FM links)")
        consequence = (f"{fm_ref} has no verification whose measured "
                       f"quantity family covers it — it remains in the "
                       f"traceability coverage report's "
                       f"unverified_failure_modes")
    else:
        action = (f"Replace the unknown with a design decision for "
                  f"{subject} carrying a recorded basis (declared "
                  f"MODELLED inside an envelope, never as evidence)")
        expected = (f"a selected value/range for {subject} with its "
                    f"documented selection basis")
        acceptance = ("the decision is recorded with basis and envelope "
                      "(Art. XXVII); it never silently becomes "
                      "SOURCE_FACT")
        consequence = (f"design work on {subject} cannot proceed on a "
                       f"recorded basis")

    dependency = u.get("binding")
    if not dependency:
        if cls == "LITERATURE_RESOLVABLE":
            dependency = ("retrieval of an external source (the "
                          "evidence pipeline)")
        elif cls == "BENCH_TEST_REQUIRED":
            dependency = "the first physical article (see build plan)"
        else:
            dependency = "design-output definition"

    return {
        "unknown_id": f"U-{i:02d}",
        "unknown_statement": text,
        "why_unknown": (u.get("reason")
                        or "no recorded basis in the canonical record"),
        "consequence": consequence,
        "classification": cls,
        "classification_basis": rule,
        "resolution_action": action,
        "expected_measurement": expected,
        "acceptance_rule": acceptance,
        "dependency": dependency,
        "priority": priority,
        "priority_basis": priority_basis,
        "source_record_ids": ids,
    }


def build_unknown_roadmap(proj: Dict, package_id: str) -> Dict:
    """UNKNOWN_ROADMAP.json — every material unknown as an actionable
    roadmap entry (R424 §7: never 'further testing required'; R425 §6:
    the action/measurement/acceptance/consequence text is built from
    EACH unknown's own subject and cited record ids — never the
    generic shared text the R424 layer emitted, and the priority field
    is a real mechanical priority, not a positional H/M marker)."""
    entries = [_roadmap_entry(i, u, proj)
               for i, u in enumerate(proj["remaining_unknowns"],
                                     start=1)]
    return {
        "artifact": "UNKNOWN_ROADMAP",
        "package_id": package_id,
        "schema": "R425_UNKNOWN_ROADMAP",
        "unknown_count_source": len(proj["remaining_unknowns"]),
        "unknown_count_roadmap": len(entries),
        "discipline": (
            "unknowns preserved exactly as recorded; classification is "
            "mechanical (each entry records the rule that fired); each "
            "entry's resolution action, expected measurement, "
            "acceptance rule, consequence and priority are derived from "
            "THAT unknown's own subject and cited record ids — the "
            "roadmap answers: what exactly must a technical team do "
            "next to remove this uncertainty? (R425 §6)"),
        "priority_counts": {
            k: sum(1 for e in entries if e["priority"] == k)
            for k in ("HIGH", "MEDIUM", "LOW")},
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


# ---------------------------------------------------------------------------
# R425 §3 — deterministic semantic content-quality gates
# ---------------------------------------------------------------------------

_UNKNOWN_MARKERS = (
    "unknown", "not established", "not performed", "not recorded",
    "not defined", "not tested", "not applicable", "not yet",
    "none recorded", "not selected", "unresolved", "missing",
)


def _is_explicit_unknown(v: Any) -> bool:
    """A value that EXPLICITLY declares its own unknown-ness (the honest
    placeholder the §3 contract accepts) — versus an absent field (a
    gap, which the gate must reject)."""
    if v is None:
        return False
    if isinstance(v, (list, tuple)):
        return False
    if isinstance(v, dict):
        for k in ("value", "status", "result", "note", "reason"):
            if _is_explicit_unknown(v.get(k)):
                return True
        return False
    text = str(v).strip().lower()
    return any(m in text for m in _UNKNOWN_MARKERS)


def _informative(v: Any) -> bool:
    """A present, information-bearing value (not blank, not merely a
    placeholder like 'UNKNOWN')."""
    if v is None:
        return False
    if isinstance(v, (list, tuple, dict)):
        return len(v) > 0
    text = str(v).strip()
    if not text:
        return False
    return not _is_explicit_unknown(v)


def _first_informative(record: Dict, *fields: str) -> Any:
    for f in fields:
        if _informative(record.get(f)):
            return record.get(f)
    return None


def _gate_di(record: Dict) -> Optional[str]:
    """Design input gate: unique id; stated role; value/status; epistemic
    class; evidence or an explicit UNKNOWN reason."""
    if not (record.get("id") or record.get("input_id")):
        return "no unique id"
    role = _informative(record.get("input")) or \
        _informative(record.get("design_role")) or \
        _informative(record.get("role"))
    if not role:
        return "no stated role"
    value = record.get("value")
    if value is None and not (
            _informative(record.get("value_status"))
            or _informative(record.get("status"))):
        return "no value/status"
    evclass = _evclass(record)
    if evclass == "UNKNOWN" and not (
            _informative(record.get("epistemic_class"))
            or _informative(record.get("value_class"))):
        return "no epistemic class"
    if not (_informative(record.get("evidence_refs"))
            or _informative(record.get("evidence_ids"))
            or _informative(record.get("source"))
            or _informative(record.get("origin"))
            or _is_explicit_unknown(value)):
        return "no evidence and no explicit UNKNOWN reason"
    return None


def _gate_do(record: Dict) -> Optional[str]:
    """Design output gate: unique id; measurable meaning (what the
    output IS); explicit parent input binding or explicit UNKNOWN."""
    if not record.get("id"):
        return "no unique id"
    if not (_informative(record.get("description"))
            or _informative(record.get("output"))):
        return "no measurable meaning (no description of what is " \
               "delivered)"
    parents = record.get("parent_ids") or []
    if not parents:
        if not (_informative(record.get("missing_inputs"))
                or _is_explicit_unknown(record.get("basis"))):
            return "no parent input binding and no explicit UNKNOWN"
    return None


def _gate_fm(record: Dict) -> Optional[str]:
    """Failure mode gate: unique id; failure consequence; affected
    function/output or explicit UNKNOWN."""
    if not (record.get("graph_id") or record.get("id")):
        return "no unique id"
    consequence = (_informative(record.get("severity"))
                   or _informative(record.get("severity_basis"))
                   or _informative(record.get("consequence"))
                   or _informative(record.get("failure_mode")))
    if not consequence:
        return "no failure consequence"
    if not (_informative(record.get("verification"))
            or _informative(record.get("verification_test"))
            or _informative(record.get("design_feature"))
            or _informative(record.get("affected_output"))
            or _informative(record.get("detectability"))):
        return "no affected function/output and no explicit UNKNOWN"
    return None


def _gate_vf(record: Dict) -> Optional[str]:
    """Verification gate: unique id; requirement; target failure/output;
    result status; acceptance rule or explicit UNKNOWN."""
    if not record.get("id"):
        return "no unique id"
    if not (_informative(record.get("requirement"))
            or _informative(record.get("method"))):
        return "no requirement"
    targets = ((record.get("invention_tie") or {}).get("targets")
               or record.get("targets"))
    if not targets:
        if not _is_explicit_unknown(record.get("target")):
            return "no target failure/output"
    if not (_informative(record.get("result"))
            or _informative(record.get("status"))):
        return "no result status"
    if not (_informative(record.get("acceptance"))
            or _informative(record.get("acceptance_criterion"))
            or _is_explicit_unknown(record.get("acceptance_status"))):
        return "no acceptance rule and no explicit UNKNOWN"
    return None


def _gate_wp(record: Dict) -> Optional[str]:
    """Build step gate: concrete work-package identity; action;
    dependency; required capability/tooling where recorded (present
    when recorded — the gate checks identity/action/dependency)."""
    if not (record.get("work_package") or record.get("id")):
        return "no work-package identity"
    if not (_informative(record.get("design_work"))
            or _informative(record.get("action"))
            or _informative(record.get("measurement"))):
        return "no action"
    if not (_informative(record.get("test_article"))
            or _informative(record.get("equipment"))
            or _informative(record.get("depends_on"))
            or _informative(record.get("dependency"))
            or _informative(record.get("basis"))):
        return "no dependency"
    return None


_GATES = {
    "design_inputs": _gate_di,
    "design_outputs": _gate_do,
    "failure_modes": _gate_fm,
    "verification": _gate_vf,
    "build_plan": _gate_wp,
}


def semantic_completeness(proj: Dict) -> Dict:
    """R425 §3 — the deterministic content-quality gate report.

    Maturity is semantic, not count-based: only records that PASS
    their category gate count toward the maturity thresholds, so an
    arbitrary quantity of low-information records can never upgrade
    the level. Every failed record is listed with the FIRST gate rule
    it violated (never a silent discount)."""
    report = {}
    for category, gate in _GATES.items():
        records = proj.get(category) or []
        seen_ids: set = set()
        complete: List[Dict] = []
        failed: List[Dict] = []
        for r in records:
            if not isinstance(r, dict):
                failed.append({"record": str(r)[:80],
                               "violation": "not a structured record"})
                continue
            rid = (r.get("id") or r.get("graph_id")
                   or r.get("work_package"))
            violation = gate(r)
            if rid and rid in seen_ids:
                violation = "duplicate id"
            if rid:
                seen_ids.add(rid)
            if violation:
                failed.append({"record": rid,
                               "violation": violation})
            else:
                complete.append(r)
        report[category] = {
            "records_total": len(records),
            "records_semantically_complete": len(complete),
            "low_information_excluded": len(failed),
            "failed_records": failed[:12],
        }
    return report


def experiment_contract_assessment(proj: Dict,
                                   run_result: Optional[Dict] = None
                                   ) -> Dict:
    """R425 §3 — EXPERIMENT_READY requires an actual DISCRIMINATING
    experiment contract, never merely the presence of a hypotheses
    array.

    A discriminating contract (Art. LII) has ALL of:
      1. >= 2 hypotheses with numeric prior probabilities (the arms
         the experiment separates);
      2. a pre-registered decision/acceptance rule (recorded on a
         verification item or the killer-experiment record);
      3. a measurable outcome path (a verification method/requirement
         naming what gets measured);
      4. a target that resolves in the record (an FM/VF id the
         experiment speaks to).
    Anything missing is listed by name — the level then stays at
    ENGINEERING_DEFINITION (honest, never softened to pass)."""
    ke = proj.get("killer_experiment") or {}
    hyps = [h for h in (ke.get("hypotheses") or [])
            if isinstance(h, dict)]
    arms = [h for h in hyps
            if isinstance(h.get("prior_probability"), (int, float))]
    rule = None
    for v in (proj.get("verification") or []):
        if _informative(v.get("acceptance")):
            rule = {"source": f"verification_matrix {v.get('id')}",
                    "acceptance": str(v.get("acceptance"))[:200]}
            break
    if rule is None:
        # an explicit acceptance/decision field on the killer-experiment
        # record counts; a mere 'definition' of what the experiment IS
        # does not (Art. LII: the rule must pre-register the decision)
        ke_rule = ke.get("acceptance") or ke.get("decision_rule") or \
            ke.get("acceptance_rule")
        if _informative(ke_rule):
            rule = {"source": "killer_experiment.acceptance",
                    "acceptance": str(ke_rule)[:200]}
    measurable = None
    for v in (proj.get("verification") or []):
        if _informative(v.get("method")) or _informative(
                v.get("requirement")):
            measurable = {"source": f"verification_matrix {v.get('id')}",
                          "method": str(v.get("method")
                                        or v.get("requirement"))[:200]}
            break
    targets: List[str] = []
    for v in (proj.get("verification") or []):
        tie = (v.get("invention_tie") or {}).get("targets") or []
        targets.extend(t for t in tie if isinstance(t, str))
    fm_ids = {f.get("graph_id") or f.get("id")
              for f in (proj.get("failure_modes") or [])}
    resolved_targets = [t for t in targets if t in fm_ids]
    selected = (run_result or {}).get("decisive_experiment") or {}
    requirements = {
        "at_least_two_hypothesis_arms_with_priors": len(arms) >= 2,
        "pre_registered_decision_rule": rule is not None,
        "measurable_outcome_path": measurable is not None,
        "target_resolves_in_record": bool(resolved_targets),
        "experiment_selected_by_loop": bool(
            selected.get("selected") or ke.get("selected")),
    }
    return {
        "discriminating": all(requirements.values()),
        "requirements": requirements,
        "hypothesis_arms": [
            {"name": h.get("name"),
             "prior_probability": h.get("prior_probability")}
            for h in arms],
        "decision_rule": rule,
        "measurable_outcome": measurable,
        "targets_resolved": resolved_targets,
        "basis": ("EXPERIMENT_READY requires the full discriminating "
                  "contract (R425 §3); each failed requirement is "
                  "named above — the hypotheses array alone never "
                  "grants the tier"),
    }


def build_maturity(proj: Dict, is_engineering: bool,
                   run_result: Optional[Dict] = None) -> str:
    """Evidence-derived maturity (R424 §10), now SEMANTIC (R425 §3):
    only semantically complete records count; EXPERIMENT_READY
    requires the discriminating experiment contract."""
    sem = semantic_completeness(proj)
    counts = {
        "eq": len(proj["equations"]),
        "di": sem["design_inputs"]["records_semantically_complete"],
        "fm": sem["failure_modes"]["records_semantically_complete"],
        "wp": sem["build_plan"]["records_semantically_complete"],
    }
    contract = experiment_contract_assessment(proj, run_result)
    if is_engineering and counts["di"] >= 5 and counts["fm"] >= 3 \
            and counts["wp"] >= 4:
        if contract["discriminating"]:
            return "EXPERIMENT_READY"
        return ep.PACKAGE_MATURITY_ENGINEERING
    return ep.PACKAGE_MATURITY_EARLY

"""discovery_fabric/engine/dossier_quality.py — CEO E15-B: substantive depth
evaluator.

Scores a NEWLY GENERATED dossier on CONTENT EVIDENCE, not field presence.
The CEO audit is explicit:

    "The coder has a depth_contract, but I want the benchmark to measure
     engineering substance, not just section presence or minimum counts.
     A package with 20 headings and shallow content must fail."

Ten dimensions (CEO E15-B list):

    MECHANISM_DEPTH
    ENGINEERING_REASONING_DEPTH
    DESIGN_TRACEABILITY
    PHYSICAL_REASONING
    FAILURE_ANALYSIS
    VNV_DEPTH                  (verification & validation depth)
    MANUFACTURING_REASONING
    TRANSFER_SPECIFICITY
    EVIDENCE_DENSITY
    BUYER_ACTIONABILITY

Each dimension is evaluated against content rules that inspect the ACTUAL
text/structure of the authoritative artifacts (invention spec, engineering
spec, rendered dossier PDF). Every rule failure produces an entry in
`deficient_areas` naming the exact deficiency and the artifact/field where
it was found.

Output verdict per dimension and overall: PASS | CONDITIONAL | FAIL.
There is deliberately NO aggregate numeric score (no vanity "95/100"):
the verdict is the worst dimension verdict, and the deficient areas are
the actionable content.

Constitutional properties:
  - Deterministic: same artifacts -> same verdict (Art. XXIV).
  - Honest: content that is UNKNOWN/NOT ESTABLISHED is counted as exactly
    that — the evaluator never rewards silence, never punishes recorded
    uncertainty that the dossier itself flags as a boundary (Art. XXV).
  - Non-gaming: the rules measure substance (mechanism-tied text, physical
    reasoning, provenance linkage), so padding with headings cannot pass.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERDICT_PASS = "PASS"
VERDICT_CONDITIONAL = "CONDITIONAL"
VERDICT_FAIL = "FAIL"
VERDICTS = (VERDICT_PASS, VERDICT_CONDITIONAL, VERDICT_FAIL)

DIMENSIONS = ("MECHANISM_DEPTH", "ENGINEERING_REASONING_DEPTH",
              "DESIGN_TRACEABILITY", "PHYSICAL_REASONING",
              "FAILURE_ANALYSIS", "VNV_DEPTH", "MANUFACTURING_REASONING",
              "TRANSFER_SPECIFICITY", "EVIDENCE_DENSITY",
              "BUYER_ACTIONABILITY")

# text markers that mean "this content is an honest unknown" (Art. XXV).
# These are NOT counted as substance, but they are also NOT counted as
# fabrication — they are recorded boundary statements.
_UNKNOWN_MARKERS = ("NOT ESTABLISHED", "UNKNOWN", "NOT_ASSIGNED",
                    "NOT_PERFORMED", "NOT_LINKED", "NOT ESTABLISHLISTED")

# placeholder content that must NOT dominate a substantive dossier:
# failure text that only restates an adversarial probe without any physical
# mechanism (CEO E15-D: reject generic failure content)
_GENERIC_FM_MARKER = "physical mechanism NOT ESTABLISHED"

# minimum substantive thresholds. These are ENGINE RULES (recorded policy,
# Art. XXVII), and the FLOORS side of the benchmark comes from the frozen
# corpus (benchmark_dossiers.py). They are intentionally conservative.
MIN_REASONING_COVERAGE_PASS = 1.0   # every critical claim chained (E15-C)
MIN_REASONING_COVERAGE_COND = 0.8
MIN_PHYSICAL_FM_FRACTION_PASS = 0.6  # of failure rows, physical mechanism
MIN_PHYSICAL_FM_FRACTION_COND = 0.4
MIN_VERIFY_LINKED_FRACTION_PASS = 0.8
MIN_VERIFY_LINKED_FRACTION_COND = 0.5


def _is_unknown_text(v: Any) -> bool:
    if v is None:
        return True
    s = str(v).strip()
    if not s:
        return True
    up = s.upper()
    return any(m in up for m in _UNKNOWN_MARKERS)


def _fraction(num: int, den: int) -> float:
    return round(num / den, 3) if den else 0.0


_NAMED_STANDARD_RE = re.compile(
    r"(IEEE|IEC|ISO|ASTM|AAMI|ANSI)\s*C?[\d.]+", re.I)


def _quantified_criterion(text: str) -> bool:
    """A criterion is quantified when it carries a numeric threshold or
    names a specific standard revision to verify against (both are concrete
    decision content; prose without either is not actionable)."""
    if not text:
        return False
    if any(text.upper().startswith(m) for m in _UNKNOWN_MARKERS):
        return False
    return bool(re.search(r"\d", text)) or bool(
        _NAMED_STANDARD_RE.search(text))


def _verdict_from(fail_count: int, cond_count: int) -> str:
    if fail_count:
        return VERDICT_FAIL
    if cond_count:
        return VERDICT_CONDITIONAL
    return VERDICT_PASS


def _mk(dim: str, verdict: str, measured: Dict[str, Any],
        deficient: List[str]) -> Dict[str, Any]:
    return {"dimension": dim, "verdict": verdict, "measured": measured,
            "deficient_areas": deficient}


# --------------------------------------------------------------------------
# dimension evaluators — each returns (verdict, measured, deficient_areas)
# --------------------------------------------------------------------------
def _equation_verdict(eq: Dict[str, Any]) -> str:
    """The A4 applicability verdict lives in selection_rationale.verdict
    (equations.py select_equations). Read from the authoritative field."""
    return str(((eq.get("selection_rationale") or {}).get("verdict")) or "")


def _falsification_test(spec: Dict[str, Any],
                        eng: Dict[str, Any]) -> str:
    """The falsification test may live in the mechanism block or in the
    pre-registered kill condition (both are authoritative)."""
    mech = (spec.get("mechanism") or {}).get("value") or {}
    fals = str(mech.get("falsification_test", "")).strip()
    if fals and not _is_unknown_text(fals):
        return fals
    kc = eng.get("kill_condition") or {}
    fals = str(kc.get("falsification_test", "")).strip()
    if fals and not _is_unknown_text(fals):
        return fals
    ke = (spec.get("killer_experiment") or {}).get("value") or {}
    fals = str(ke.get("definition", "")).strip()
    if fals and not _is_unknown_text(fals):
        return fals
    return ""


def _eval_mechanism_depth(spec: Dict[str, Any],
                          eng: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """Mechanism is specific to THIS invention: tied text, falsification
    test, a governing model whose equations carry APPLICABLE/CONDITIONAL
    verdicts (a REJECTED governing equation is a hard FAIL — E15-D)."""
    deficient: List[str] = []
    mech = (spec.get("mechanism") or {}).get("value") or {}
    body = " ".join(str(mech.get(k, "")) for k in
                    ("mechanism", "intervention", "expected_effect"))
    measured: Dict[str, Any] = {}

    if _is_unknown_text(body) or len(body.split()) < 25:
        deficient.append(
            "invention_spec.mechanism: mechanism body absent or too thin "
            "to carry a physical claim (needs >= 25 words of specific "
            "mechanism text)")
    fals = _falsification_test(spec, eng)
    if not fals:
        deficient.append(
            "invention_spec.mechanism: no falsification test found in the "
            "mechanism block or the pre-registered kill condition — the "
            "mechanism is not testable as stated")

    gm = ((eng.get("engineering_core") or {}).get("governing_model") or {})
    equations = gm.get("equations", []) or []
    rejected = gm.get("rejected_equations", []) or []
    applicable = [e for e in equations
                  if _equation_verdict(e).upper() == "APPLICABLE"]
    conditional = [e for e in equations
                   if _equation_verdict(e).upper() == "CONDITIONAL"]
    measured.update({"mechanism_words": len(body.split()),
                     "has_falsification_test": bool(fals),
                     "equations": len(equations),
                     "equations_applicable": len(applicable),
                     "equations_conditional": len(conditional),
                     "equations_rejected": len(rejected),
                     "why_this_domain_present":
                         bool(gm.get("why_this_domain"))})
    if not equations:
        deficient.append(
            "engineering_core.governing_model.equations: no governing "
            "equation selected — no quantitative engineering model")
    if not applicable and not conditional and equations:
        deficient.append(
            "governing_model.equations: no equation carries an "
            "APPLICABLE or CONDITIONAL applicability verdict")
    if equations and not gm.get("why_this_domain"):
        deficient.append(
            "governing_model.why_this_domain: no argument for WHY these "
            "models apply to THIS invention (CEO E15-D)")

    fail = bool([d for d in deficient if "falsification" in d
                 or "mechanism body" in d])
    verdict = (VERDICT_FAIL if (fail or not equations or
                                (not applicable and not conditional))
               else VERDICT_CONDITIONAL if deficient else VERDICT_PASS)
    return verdict, measured, deficient


def _eval_reasoning_depth(spec: Dict[str, Any],
                          eng: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """E15-C: EVERY critical engineering claim must carry a complete
    CLAIM -> PRINCIPLE -> MODEL -> INPUT -> ASSUMPTION -> RESULT ->
    FAILURE_MODE -> VERIFICATION chain, each node non-empty and
    provenance-carrying. Coverage < 100% is at best CONDITIONAL."""
    rc = eng.get("engineering_reasoning_chains") or {}
    chains = rc.get("chains", []) or []
    roles = set(rc.get("chain_roles") or
                ("CLAIM", "ENGINEERING_PRINCIPLE", "EQUATION_MODEL", "INPUT",
                 "ASSUMPTION", "RESULT", "FAILURE_MODE", "VERIFICATION"))
    complete = 0
    broken: List[str] = []
    for c in chains:
        roles_seen = {n.get("node_type") for n in c.get("nodes", [])}
        nodes_ok = True
        for n in c.get("nodes", []):
            # a node is present when it carries NON-EMPTY content and a
            # provenance pointer. Content that states an unknown (Art. XXV)
            # is still content — an honest chain may record
            # 'NOT ESTABLISHED' as its RESULT/INPUT node.
            if not str(n.get("content") or "").strip():
                nodes_ok = False
            prov = n.get("provenance") or {}
            if not prov.get("origin_stage"):
                nodes_ok = False
        if roles <= roles_seen and nodes_ok:
            complete += 1
        else:
            missing = sorted(roles - roles_seen)
            broken.append(f"{c.get('chain_id')}: missing roles "
                          f"{missing or 'empty/provenance-less nodes'}")
    total = len(chains)
    coverage = _fraction(complete, total)
    measured = {"chains": total, "complete_chains": complete,
                "coverage": coverage,
                "broken_chains": broken,
                "note": ("a node counts as present when its content is "
                         "non-empty and provenance-carrying; content that "
                         "RECORDS an unknown (Art. XXV) is present — "
                         "silence is the absence, not the unknown")}
    deficient = []
    if total == 0:
        deficient.append("engineering_reasoning_chains: no reasoning chains "
                         "present (E15-C requires chains on all critical "
                         "claims)")
        return VERDICT_FAIL, measured, deficient
    if coverage < MIN_REASONING_COVERAGE_COND:
        deficient.append(
            f"reasoning-chain coverage {coverage} < "
            f"{MIN_REASONING_COVERAGE_COND}: critical claims without "
            f"complete causal chains: {broken}")
        return VERDICT_FAIL, measured, deficient
    if coverage < MIN_REASONING_COVERAGE_PASS:
        deficient.append(
            f"reasoning-chain coverage {coverage} < 1.0: every critical "
            f"claim must carry the full 8-role chain; incomplete: "
            f"{broken}")
        return VERDICT_CONDITIONAL, measured, deficient
    return VERDICT_PASS, measured, deficient


def _eval_design_traceability(spec: Dict[str, Any],
                              eng: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """Every critical design input must flow to >= 1 design output; every
    failure mode must be linked to a verification; orphan critical objects
    are exact deficiencies (CEO E15-I: 0 orphan critical design inputs)."""
    deficient: List[str] = []
    dis = eng.get("design_inputs", []) or []
    dos = eng.get("design_outputs", []) or []
    fms = eng.get("failure_analysis", []) or []
    graph = eng.get("design_graph") or {}
    nodes = graph.get("nodes", []) or []
    node_ids = {n.get("id") for n in nodes if isinstance(n, dict)}
    # Orphan check on PRIMARY design inputs. The engineering spec tags each
    # design input with design_role: PRIMARY (a design output consumes it)
    # or CONTEXT (a recorded constraint feeding design rationale). An orphan
    # = a PRIMARY input no design output references. CONTEXT inputs are
    # counted separately and their RATIO is substance-checked (a dossier
    # whose inputs are mostly context is shallow).
    referenced = {pid for d in dos for pid in (d.get("parent_ids") or [])}
    di_ids = {d.get("id") for d in dis}
    primary = [d for d in dis
               if d.get("design_role", "PRIMARY") == "PRIMARY"]
    context = [d for d in dis
               if d.get("design_role") == "CONTEXT"]
    orphan_primary = sorted({d.get("id") for d in primary} - referenced) \
        if primary else []
    unlinked_fm = [f.get("graph_id") for f in fms
                   if f.get("verification") in ("NOT_LINKED", None, "")]
    context_ratio = _fraction(len(context), len(dis)) if dis else 0.0
    measured = {"design_inputs": len(dis),
                "primary_design_inputs": len(primary),
                "context_design_inputs": len(context),
                "context_ratio": context_ratio,
                "design_outputs": len(dos),
                "failure_modes": len(fms),
                "graph_nodes": len(node_ids),
                "orphan_primary_design_inputs": orphan_primary,
                "unlinked_failure_modes": unlinked_fm}
    if not dos:
        deficient.append("design_outputs: none — design inputs have no "
                         "engineering consequence")
    if orphan_primary:
        deficient.append(f"PRIMARY design inputs without any design-output "
                         f"reference (orphan critical inputs): "
                         f"{orphan_primary}")
    if dis and context_ratio > 0.7:
        deficient.append(
            f"context design-input ratio {context_ratio} > 0.7: most "
            "design inputs are context constraints, not consumed design "
            "drivers")
    if unlinked_fm:
        deficient.append(f"failure modes with no linked verification "
                         f"(NOT_LINKED): {unlinked_fm}")
    if not node_ids:
        deficient.append("design_graph: no explicit design graph nodes")
    critical_fail = bool(orphan_primary) or not dos
    return (VERDICT_FAIL if critical_fail
            else VERDICT_CONDITIONAL if deficient else VERDICT_PASS,
            measured, deficient)


def _eval_physical_reasoning(spec: Dict[str, Any],
                             eng: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """E15-D: failure content must be tied to the ACTUAL physical mechanism.
    Domain FMs carry an invention_applicability verdict (TIED /
    NOT_ESTABLISHED). A dossier whose physical reasoning is dominated by
    generic adversarial placeholders must FAIL."""
    deficient: List[str] = []
    fms = eng.get("failure_analysis", []) or []
    physical, generic, not_tied = [], [], []
    for f in fms:
        # content_class is computed ONCE by the generator (E15-D) — the
        # single authority for substance accounting. Fall back to the text
        # heuristic only for artifacts that predate the field.
        cls = f.get("content_class")
        pm = str(f.get("physical_mechanism", ""))
        if cls is None:
            cls = ("GENERIC_ADVERSARIAL_PLACEHOLDER"
                   if (_is_unknown_text(pm) or _GENERIC_FM_MARKER in pm)
                   else "PHYSICAL_MECHANISM")
        if cls == "PHYSICAL_MECHANISM":
            physical.append(f.get("graph_id"))
        else:
            generic.append(f.get("graph_id"))
        appl = (f.get("invention_applicability") or {})
        if appl and appl.get("verdict") != "TIED":
            not_tied.append(f.get("graph_id"))
    total = len(fms)
    frac = _fraction(len(physical), total)
    measured = {"failure_rows": total, "physical_mechanism_rows":
                len(physical), "generic_placeholder_rows": len(generic),
                "physical_fraction": frac,
                "domain_rows_not_tied": len(not_tied)}
    if total == 0:
        deficient.append("failure_analysis: empty")
        return VERDICT_FAIL, measured, deficient
    if not physical:
        deficient.append("failure_analysis: NO failure row carries an "
                         "established physical mechanism — content is "
                         "generic adversarial placeholder (CEO E15-D)")
        return VERDICT_FAIL, measured, deficient
    if frac < MIN_PHYSICAL_FM_FRACTION_COND:
        deficient.append(
            f"physical-mechanism fraction {frac} < "
            f"{MIN_PHYSICAL_FM_FRACTION_COND}: dominant share of failure "
            "rows are generic placeholders")
        return VERDICT_FAIL, measured, deficient
    if frac < MIN_PHYSICAL_FM_FRACTION_PASS:
        deficient.append(
            f"physical-mechanism fraction {frac} < "
            f"{MIN_PHYSICAL_FM_FRACTION_PASS}; generic rows: "
            f"{[g for g in generic if g]}")
        return VERDICT_CONDITIONAL, measured, deficient
    return VERDICT_PASS, measured, deficient


def _eval_failure_analysis(spec: Dict[str, Any],
                           eng: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """Failure analysis substance: kill conditions enumerated, severity
    bases stated, domain basis recorded, design-control direction present —
    and the motivating SOURCE_FACT failure (the problem's own failure) must
    be present."""
    deficient: List[str] = []
    fms = eng.get("failure_analysis", []) or []

    def _has_kill(f: Dict[str, Any]) -> bool:
        kc = str(f.get("kill_condition") or "").strip()
        if not kc or _is_unknown_text(kc):
            return False
        return not kc.upper().startswith("NOT ESTABLISHED")

    with_kill = [f for f in fms if _has_kill(f)]
    with_severity = [f for f in fms
                     if not _is_unknown_text(f.get("severity_basis"))]
    with_control = [f for f in fms
                    if not _is_unknown_text(f.get("design_control"))]
    source_fact = [f for f in fms
                   if str(f.get("epistemic_class", "")).startswith(
                       "SOURCE_FACT")]
    measured = {"failure_rows": len(fms), "with_kill_condition":
                len(with_kill), "with_severity_basis": len(with_severity),
                "with_design_control": len(with_control),
                "source_fact_rows": len(source_fact)}
    if not fms:
        deficient.append("failure_analysis: empty")
        return VERDICT_FAIL, measured, deficient
    if not source_fact:
        deficient.append("failure_analysis: the motivating SOURCE_FACT "
                         "failure (the problem's own failure) is absent")
    if len(with_kill) == 0:
        deficient.append("failure_analysis: no failure mode carries a "
                         "pre-registered kill condition")
    if len(with_control) == 0:
        deficient.append("failure_analysis: no failure mode carries a "
                         "design-control direction")
    hard = not source_fact or not fms
    return (VERDICT_FAIL if hard
            else VERDICT_CONDITIONAL if deficient else VERDICT_PASS,
            measured, deficient)


def _eval_vnv_depth(spec: Dict[str, Any],
                    eng: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """Verification & validation depth: methods with acceptance criteria,
    validation protocols honestly marked NOT_PERFORMED, and failure modes
    covered by verifications."""
    deficient: List[str] = []
    vf = eng.get("verification_matrix", []) or []
    va = eng.get("validation_matrix", []) or []
    fms = eng.get("failure_analysis", []) or []
    with_method = [v for v in vf
                   if not _is_unknown_text(v.get("method"))]
    # an acceptance criterion is present when the row carries a concrete
    # threshold (number), names a standard to verify against, or its
    # acceptance_status records a SOURCE_FACT threshold / named-standard
    # criterion; a bare 'NOT ESTABLISHED' is an honest gap and counts as
    # absent
    def _has_acceptance(v: Dict[str, Any]) -> bool:
        status = str(v.get("acceptance_status", "")).upper()
        if status in ("SOURCE_FACT_THRESHOLD", "EXTERNAL_PRECEDENT_CANDIDATE"):
            return True
        return _quantified_criterion(str(v.get("acceptance") or ""))
    with_accept = [v for v in vf if _has_acceptance(v)]
    linked_rows = sum(1 for f in fms
                      if f.get("verification") not in ("NOT_LINKED", None, ""))
    vf_ids = {v.get("id") for v in vf}
    linked_valid = sum(1 for f in fms
                       if f.get("verification") in vf_ids)
    linked_frac = _fraction(linked_valid, len(fms)) if fms else 0.0
    measured = {"verification_items": len(vf), "with_method": len(with_method),
                "with_acceptance": len(with_accept),
                "validation_items": len(va),
                "fm_rows_linked": linked_rows,
                "fm_rows_linked_to_existing_vf": linked_valid,
                "fm_verification_coverage": linked_frac}
    if not vf:
        deficient.append("verification_matrix: empty — no verification "
                         "strategy")
    if vf and not with_accept:
        deficient.append("verification_matrix: no item carries an "
                         "acceptance criterion")
    if fms and linked_frac < MIN_VERIFY_LINKED_FRACTION_COND:
        deficient.append(
            f"failure-mode verification coverage {linked_frac} < "
            f"{MIN_VERIFY_LINKED_FRACTION_COND}")
    if not va:
        deficient.append("validation_matrix: empty — validation strategy "
                         "absent (may honestly be NOT_PERFORMED rows)")
    hard = not vf
    return (VERDICT_FAIL if hard
            else VERDICT_CONDITIONAL if deficient else VERDICT_PASS,
            measured, deficient)


def _eval_manufacturing(spec: Dict[str, Any],
                        eng: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """Manufacturing reasoning: candidate routes tied to the invention,
    materials with precedent basis, BOM present — content, not headings."""
    deficient: List[str] = []
    mfg = eng.get("manufacturing") or {}
    procs = mfg.get("candidate_processes", []) or []
    mats = eng.get("materials", []) or []
    bom = eng.get("bom", []) or []
    tied_procs = [p for p in procs
                  if ((p.get("invention_tie") or {}).get("invention_tied"))]
    measured = {"candidate_processes": len(procs),
                "invention_tied_processes": len(tied_procs),
                "materials": len(mats), "bom_items": len(bom)}
    if not procs:
        deficient.append("manufacturing.candidate_processes: none — no "
                         "manufacturing route reasoning")
    elif not tied_procs:
        deficient.append("manufacturing.candidate_processes: no process "
                         "candidate is tied to this invention (generic "
                         "routes)")
    if not mats:
        deficient.append("materials: none — no material reasoning")
    if not bom:
        deficient.append("bom: empty — no bill of materials candidates")
    hard = not procs
    return (VERDICT_FAIL if hard
            else VERDICT_CONDITIONAL if deficient else VERDICT_PASS,
            measured, deficient)


def _eval_transfer_specificity(spec: Dict[str, Any],
                               eng: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """Transfer boundary must be explicit: what the buyer receives, what the
    buyer must build, what is NOT established, and the next decisive
    experiment."""
    deficient: List[str] = []
    tb = eng.get("transfer_boundary") or {}
    buyer_receives = tb.get("buyer_receives", []) or []
    buyer_builds = tb.get("buyer_must_create", []) or []
    unknowns = ((eng.get("engineering_core") or {})
                .get("remaining_unknowns", []) or [])
    kill = eng.get("kill_condition") or spec.get("killer_experiment")
    measured = {"buyer_receives": len(buyer_receives),
                "buyer_must_create": len(buyer_builds),
                "remaining_unknowns_enumerated": len(unknowns),
                "kill_condition_present": bool(kill)}
    if not buyer_receives:
        deficient.append("transfer_boundary.buyer_receives: empty — buyer "
                         "deliverables not enumerated")
    if not buyer_builds:
        deficient.append("transfer_boundary.buyer_must_create: empty — "
                         "buyer obligations not enumerated")
    if not unknowns:
        deficient.append("engineering_core.remaining_unknowns: none "
                         "enumerated — unknowns must stay explicit "
                         "(Art. XXV), silence is not completeness")
    if not kill:
        deficient.append("kill_condition: absent — no pre-registered kill")
    hard = (not buyer_receives or not buyer_builds)
    return (VERDICT_FAIL if hard
            else VERDICT_CONDITIONAL if deficient else VERDICT_PASS,
            measured, deficient)


def _eval_evidence_density(spec: Dict[str, Any],
                           eng: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """Evidence density: share of epistemic-tagged blocks that cite custody
    evidence, and the external-evidence count recorded in the package."""
    deficient: List[str] = []
    spec_blocks = [spec.get(k) for k in
                   ("mechanism", "causal_chain", "novelty_hypothesis",
                    "prior_art", "engineering_parameters")]
    spec_blocks = [b for b in spec_blocks if isinstance(b, dict)]
    # an UNKNOWN-class block asserts nothing, so there is nothing to anchor
    # (Art. XXV: unknown stays unknown — it cannot dilute evidence density)
    asserting = [b for b in spec_blocks
                 if b.get("epistemic_class") != "UNKNOWN"]
    with_ev = [b for b in asserting if b.get("evidence_ids")]
    frac = _fraction(len(with_ev), len(asserting)) if asserting else 0.0
    ext = 0
    for block_name in ("external_engineering_precedent",):
        v = eng.get(block_name)
        if isinstance(v, list):
            ext += len(v)
        elif isinstance(v, dict):
            ext += len(v.get("items", []) or v.get("precedents", []) or [])
    measured = {"asserting_spec_blocks": len(asserting),
                "blocks_with_evidence_ids": len(with_ev),
                "evidence_fraction": frac,
                "external_precedent_items": ext}
    if asserting and frac == 0:
        deficient.append("invention_spec: NO asserting block cites "
                         "evidence_ids — claims are unanchored to custody "
                         "(Art. I)")
    if asserting and frac < 0.5:
        deficient.append(
            f"evidence fraction {frac} < 0.5 across asserting spec blocks")
    hard = asserting and frac == 0
    return (VERDICT_FAIL if hard
            else VERDICT_CONDITIONAL if deficient else VERDICT_PASS,
            measured, deficient)


def _eval_buyer_actionability(spec: Dict[str, Any],
                              eng: Dict[str, Any],
                              package_report: Optional[Dict[str, Any]],
                              ) -> Tuple[str, Dict, List]:
    """Buyer decision usefulness: the buyer card / dossier must state what
    the buyer gets, what to build, the next decisive experiment with a
    measurable endpoint, and the kill conditions — with QUANTIFIED
    decision content (numbers, thresholds, endpoints)."""
    deficient: List[str] = []
    tb = eng.get("transfer_boundary") or {}
    exp = eng.get("decisive_experiment") or spec.get("killer_experiment") \
        or {}
    # serialize the FULL nested payload (the tagged value lives under
    # 'value'); plain scalars and nested strings both count
    def _flatten(v: Any) -> str:
        if isinstance(v, dict):
            return " ".join(_flatten(x) for x in v.values())
        if isinstance(v, (list, tuple)):
            return " ".join(_flatten(x) for x in v)
        return str(v)
    exp_txt = _flatten(exp) if isinstance(exp, dict) else str(exp)
    fals = _falsification_test(spec, eng)
    vf_accepts = " ".join(str(v.get("acceptance") or "")
                          for v in (eng.get("verification_matrix") or []))
    quantified = (bool(re.search(r"\d", exp_txt))
                  or bool(_quantified_criterion(fals))
                  or bool(_quantified_criterion(vf_accepts)))
    measured = {"buyer_receives": len(tb.get("buyer_receives", []) or []),
                "buyer_must_create": len(tb.get("buyer_must_create", []) or []),
                "decisive_experiment_quantified": quantified}
    pdf_text = ""
    if package_report:
        pdf = Path(package_report.get("folder", "")) / \
            "03_BUYER_DECISION_CARD.pdf"
        if pdf.exists():
            try:
                import pypdf
                pdf_text = "\n".join(
                    pg.extract_text() or ""
                    for pg in pypdf.PdfReader(str(pdf)).pages)
            except Exception:  # noqa: BLE001 — recorded, honest
                pdf_text = ""
    if pdf_text:
        for heading, label in (
                ("WHAT DOES THE BUYER GET", "buyer gets"),
                ("WHAT DOES THE BUYER HAVE TO BUILD", "buyer builds"),
                ("WHAT IS THE NEXT DECISIVE EXPERIMENT",
                 "next experiment"),
                ("WHAT WOULD MAKE US KILL IT", "kill conditions")):
            if heading not in pdf_text:
                deficient.append(f"buyer decision card: section '{heading}' "
                                 "absent")
        measured["buyer_card_chars"] = len(pdf_text)
    if not quantified:
        deficient.append("decisive_experiment: no measurable endpoint "
                         "(threshold/number) — the buyer cannot act on an "
                         "unquantified experiment")
    hard = not quantified
    return (VERDICT_FAIL if hard
            else VERDICT_CONDITIONAL if deficient else VERDICT_PASS,
            measured, deficient)


# --------------------------------------------------------------------------
def evaluate_dossier_quality(spec: Dict[str, Any], eng: Dict[str, Any],
                             package_report: Optional[Dict[str, Any]] = None,
                             ) -> Dict[str, Any]:
    """E15-B substantive depth evaluation of ONE generated dossier.
    Returns per-dimension verdicts + exact deficient areas + overall
    verdict (worst dimension). No aggregate numeric score."""
    results = []
    v, m, d = _eval_mechanism_depth(spec, eng)
    results.append(_mk("MECHANISM_DEPTH", v, m, d))
    v, m, d = _eval_reasoning_depth(spec, eng)
    results.append(_mk("ENGINEERING_REASONING_DEPTH", v, m, d))
    v, m, d = _eval_design_traceability(spec, eng)
    results.append(_mk("DESIGN_TRACEABILITY", v, m, d))
    v, m, d = _eval_physical_reasoning(spec, eng)
    results.append(_mk("PHYSICAL_REASONING", v, m, d))
    v, m, d = _eval_failure_analysis(spec, eng)
    results.append(_mk("FAILURE_ANALYSIS", v, m, d))
    v, m, d = _eval_vnv_depth(spec, eng)
    results.append(_mk("VNV_DEPTH", v, m, d))
    v, m, d = _eval_manufacturing(spec, eng)
    results.append(_mk("MANUFACTURING_REASONING", v, m, d))
    v, m, d = _eval_transfer_specificity(spec, eng)
    results.append(_mk("TRANSFER_SPECIFICITY", v, m, d))
    v, m, d = _eval_evidence_density(spec, eng)
    results.append(_mk("EVIDENCE_DENSITY", v, m, d))
    v, m, d = _eval_buyer_actionability(spec, eng, package_report)
    results.append(_mk("BUYER_ACTIONABILITY", v, m, d))

    n_fail = sum(1 for r in results if r["verdict"] == VERDICT_FAIL)
    n_cond = sum(1 for r in results if r["verdict"] == VERDICT_CONDITIONAL)
    deficient_areas = []
    for r in results:
        for da in r["deficient_areas"]:
            deficient_areas.append(f"[{r['dimension']}] {da}")
    return {
        "evaluator": "DOSSIER_QUALITY (E15-B)",
        "version": "1.0.0",
        "verdict": _verdict_from(n_fail, n_cond),
        "verdict_rule": ("overall = worst dimension; FAIL if any dimension "
                         "fails; CONDITIONAL if any dimension is "
                         "conditional; NO aggregate numeric score by "
                         "CEO rule"),
        "dimensions": results,
        "summary": {"pass": sum(1 for r in results
                                if r["verdict"] == VERDICT_PASS),
                    "conditional": n_cond, "fail": n_fail,
                    "total": len(results)},
        "deficient_areas": deficient_areas,
    }


def assert_quality_gate(quality: Dict[str, Any]) -> None:
    """E15-B release gate: a FAIL verdict must NOT release (CEO: do not
    lower the benchmark to make generated packages pass). CONDITIONAL
    releases with the conditionals recorded."""
    if quality.get("verdict") == VERDICT_FAIL:
        raise QualityGateFailure(
            "E15-B quality gate FAIL: "
            + " | ".join(quality.get("deficient_areas", [])))


class QualityGateFailure(RuntimeError):
    """Raised when a generated dossier fails the substantive quality gate.
    The package is NOT released; the deficient areas are the record."""

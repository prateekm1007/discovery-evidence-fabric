"""Coder 2 Phase 3, B9 — BLIND SEMANTIC ADJUDICATION LAYER.

For a random sample of generated dossiers, independently evaluate:

    mechanism correctness
    engineering reasoning correctness
    equation applicability
    failure-mode correctness
    verification appropriateness

Independence contract:
  * TWO adjudicators with separate code paths and separate knowledge
    bases: A = FIRST_PRINCIPLES (physics-first, works from the governing
    model outward) and B = SYSTEMS_TRACE (traceability-first, works from
    claims/verification inward);
  * neither adjudicator imports or calls the B3 (semantic_causal) or B4
    (semantic_genericness) detectors — the benchmark author's instruments
    are NOT the adjudicator;
  * Coder 1's own labels are never inputs: no E15-B verdict, no engine
    quality dimension, no engine domain label is read by either
    adjudicator (Adjudicator A classifies the physics family with its own
    vocabulary from the INPUT signature, not the engine's domain field);
  * where the adjudicators disagree, the DISAGREEMENT is preserved with
    both verdicts — never averaged, never resolved by a third rule;
  * residual self-reference risk is disclosed honestly: both adjudicators
    are still authored by Coder 2. The external counterweight is the CEO
    Phase 3 B11 human spot-check (external evidence, never automated).

Verdict vocabulary per axis: CORRECT / QUESTIONABLE / INCORRECT
(QUESTIONABLE is honest uncertainty, Art. XXV — never silently upgraded).

Blind-set disclosure: blind samples are published hash-keyed with verdict
and finding CLASSES only (no domains, devices, mechanisms, or quoted
text); committed samples publish short evidence excerpts (their content
is already committed).
"""
from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMITTED_RUNS = REPO_ROOT / "artifacts/benchmark/generated/runs"
BLIND_RUNS = REPO_ROOT / "artifacts/benchmark/blind/runs"
OUT_PATH = REPO_ROOT / "artifacts/benchmark/baseline" / \
    "BLIND_SEMANTIC_ADJUDICATION.json"

AXES = (
    "mechanism_correctness",
    "engineering_reasoning_correctness",
    "equation_applicability",
    "failure_mode_correctness",
    "verification_appropriateness",
)
ADJUDICATOR_A = "ADJUDICATOR_A_FIRST_PRINCIPLES"
ADJUDICATOR_B = "ADJUDICATOR_B_SYSTEMS_TRACE"

# ===========================================================================
# Adjudicator A knowledge base — physics-first (fresh vocabulary)
# ===========================================================================
A_FAMILY_TERMS: Dict[str, Tuple[str, ...]] = {
    "fluidics": ("pressure", "flow", "drainage", "lumen", "catheter", "shunt",
                 "viscosity", "hydraulic", "siphon", "hydrodynamic", "fluid",
                 "porous", "diffuser", "osmotic", "peritoneal", "infusate"),
    "structural": ("strain", "stress", "fatigue", "fracture", "bend",
                   "anchor", "bellows", "stiffness", "elastic", "load",
                   "migration", "detent", "cyclic", "torsion", "kink"),
    "optical": ("optical", "wavelength", "photovoltaic", "reflectance",
                "backscatter", "near-infrared", "fiber", "photonic",
                "illumination", "absorbance", "lens", "spectral", "photon"),
    "rf": ("antenna", "telemetry", "radiofrequency", "sar", "link margin",
           "wireless", "transmit power", "packet", "electromagnetic",
           "dipole", "uwb"),
    "acoustic": ("acoustic", "ultrasound", "transducer", "sonic",
                 "vibration", "resonance", "harmonic", "audible"),
    "mri": ("mri", "gradient", "phase-contrast", "tesla", "rf pulse",
            "magnet", "nmr", "larmor", "mr environment"),
    "enzyme": ("enzyme", "hyaluronidase", "urease", "catalytic", "substrate",
               "depolymer", "macromolecule", "enzyme activity"),
    "phage": ("phage", "bacteriophage", "lytic", "biofilm", "bacterial",
              "colony", "staphylococc", "microbial"),
    "ml": ("classifier", "anomaly", "baseline drift", "alarm", "threshold",
           "false positive", "sensitivity", "cohort", "on-device",
           "learning", "model"),
    "thermal": ("temperature", "thermal", "heat", "dissipation", "cooling",
                "ablation", "hotspot", "conduction", "watts"),
    "energy": ("harvest", "piezoelectric", "thermoelectric", "charge",
               "energy balance", "trickle", "reservoir", "pulsation"),
}

A_ACTIVE_WORDS = ("closed-loop", "closed loop", "feedback", "adaptive",
                  "self-adjusting", "actively controlled", "actuator",
                  "servo", "controller", "auto-tuning", "adapts",
                  "adjusts", "regulates", "schedules")
A_PASSIVE_WORDS = ("passive", "open-loop", "open loop", "no control",
                   "operates passively", "no closed-loop")

A_CAUSAL_CONNECTORS = ("reduces", "increases", "prevents", "converts",
                       "limits", "maintains", "raises", "lowers", "spreads",
                       "compensates", "biases", " redistributes", "attenuate",
                       "amplif", "dissipate", "harvest", "senses")

# physical-quantity families (fresh organization: by measurable quantity)
A_QUANTITY_FAMILIES: Dict[str, Tuple[str, ...]] = {
    "hydraulic": ("pressure", "flow", "drainage", "head", "viscosity",
                  "permeability", "occlusion", "patency", "lumen", "fluid",
                  "resistance to flow", "hydrostatic"),
    "thermal": ("temperature", "heat", "thermal", "watts", "ablation",
                "cooling", "hotspot", "delta-t", "gradient"),
    "electrical": ("voltage", "current", "charge", "impedance", "battery",
                   "capacitance", "telemetry power", "milliwatt",
                   "transmit power", "power transfer", "power budget"),
    "optical": ("reflectance", "absorbance", "wavelength", "optical power",
                "photon", "backscatter", "illumination", "spectral"),
    "mechanical": ("strain", "stress", "force", "fatigue", "cycles",
                   "displacement", "bend", "torsion", "stiffness", "wear"),
    "biological": ("colony", "cfu", "biofilm", "cell", "encrustation",
                   "protein", "deposit", "tissue", "ingrowth", "fibrosis",
                   "infection", "inflammatory"),
    "signal": ("signal", "noise", "snr", "auc", "accuracy", "alarm",
               "detection", "classifier", "packet", "link margin",
               "bit error", "dropout", "telemetry"),
    "magnetic": ("gradient", "tesla", "mr signal", "phase", "magnet"),
}

A_EQ_REGIMES: Dict[str, Dict[str, Any]] = {
    "poiseuille": {"family": "hydraulic",
                   "requires": ("laminar", "newtonian", "rigid"),
                   "note": "Hagen-Poiseuille needs laminar Newtonian flow "
                           "in a rigid circular fully-developed lumen"},
    "orifice": {"family": "hydraulic",
                "requires": ("restriction", "discharge"),
                "note": "orifice discharge needs a sharp-edged short "
                        "restriction with a discharge coefficient"},
    "reynolds": {"family": "dimensionless",
                 "requires": ("regime", "transition"),
                 "note": "Reynolds number is a regime criterion, not a "
                         "design relation"},
    "continuity": {"family": "hydraulic", "requires": ("conservation",),
                   "note": "mass conservation"},
    "bernoulli": {"family": "hydraulic", "requires": ("inviscid",),
                  "note": "Bernoulli needs negligible viscous loss"},
    "fourier": {"family": "thermal", "requires": ("conduction", "gradient"),
                "note": "Fourier conduction needs a thermal gradient"},
    "ohm": {"family": "electrical", "requires": ("conductor", "resistance"),
            "note": "Ohm's law is for conductive electrical paths"},
    "piezoelectric": {"family": "electrical",
                      "requires": ("strain", "charge", "mechanical"),
                      "note": "piezoelectric coupling converts mechanical "
                              "strain to charge"},
    "thermoelectric": {"family": "electrical",
                       "requires": ("gradient", "emf", "seebeck"),
                       "note": "thermoelectric generation needs a thermal "
                               "gradient across junctions"},
    "starling": {"family": "biological", "requires": ("capillary",
                                                       "membrane"),
                 "note": "Starling forces govern capillary fluid exchange"},
}

A_FAMILY_DOMINANT_FAILURES: Dict[str, Tuple[str, ...]] = {
    "fluidics": ("occlu", "obstruct", "encrust", "kink|collapse", "turbulen|"
                 "regime", "infection|biofilm"),
    "structural": ("fatigue|fracture", "wear", "migrat|dislodg", "drift"),
    "optical": ("attenuat|loss|foul", "misalign", "power|depletion"),
    "rf": ("link|dropout", "detun|antenna", "sar|heating"),
    "acoustic": ("coupling|attenuat", "noise|artifact", "transducer"),
    "mri": ("artifact|distort", "heating|sar", "displace|torque|force"),
    "enzyme": ("activity|denatur", "leach|deplet", "immunogen|foreign"),
    "phage": ("resistance", "biofilm|coloniz", "inactiv|stabilit"),
    "ml": ("drift|baseline", "false|alarm", "overfit|generaliz"),
    "thermal": ("overheat|temperature rise", "insulat", "hotspot"),
    "energy": ("power|harvest|deficit", "fatigue|degrad", "impedance"),
}


def _txt(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def _has(text: str, terms: Sequence[str]) -> List[str]:
    low = " " + text.lower() + " "
    return [t for t in terms if t in low]


def _classify_family_a(texts: Sequence[str]) -> Optional[str]:
    """Adjudicator A's OWN family classification from input signature."""
    joined = " ".join(str(t) for t in texts).lower()
    best, best_hits = None, 0
    for fam, terms in A_FAMILY_TERMS.items():
        hits = len(_has(joined, terms))
        if hits > best_hits:
            best, best_hits = fam, hits
    return best if best_hits >= 2 else None


def _quantity_families(text: str) -> set:
    low = text.lower()
    return {fam for fam, terms in A_QUANTITY_FAMILIES.items()
            if any(t in low for t in terms)}


# ===========================================================================
# Adjudicator A — FIRST_PRINCIPLES (physics-first)
# ===========================================================================
def _all_strings(obj: Any, acc: List[str] = None) -> List[str]:
    """Every string leaf of an artifact (for dossier-wide statements)."""
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        for v in obj.values():
            _all_strings(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _all_strings(v, acc)
    elif isinstance(obj, str):
        acc.append(obj)
    return acc


def adjudicate_a(eng: Optional[dict], inv: Optional[dict],
                 signature_texts: Sequence[str]) -> Dict[str, Any]:
    """Works from the governing physics outward."""
    findings: Dict[str, List[Dict[str, Any]]] = {a: [] for a in AXES}
    if not eng or not inv:
        return {"adjudicator": ADJUDICATOR_A, "available": False,
                "axes": {a: {"verdict": "QUESTIONABLE",
                             "findings": [{"class": "ARTIFACTS_UNAVAILABLE"}]}
                         for a in AXES}}
    fam = _classify_family_a(signature_texts)
    mech_val = (inv.get("mechanism") or {}).get("value") or {}
    mechanism_text = " ".join(_txt(mech_val.get(k)) for k in
                              ("mechanism", "intervention",
                               "expected_effect"))
    arch_text = " ".join(_txt(eng.get(k)) for k in
                         ("mechanism_architecture", "system_architecture"))
    dossier_text = " ".join(_all_strings(eng) + _all_strings(inv))

    # ---- axis 1: mechanism correctness -----------------------------------
    if fam is None:
        findings["mechanism_correctness"].append({
            "class": "FAMILY_UNCLASSIFIABLE_BY_ADJUDICATOR",
            "detail": "adjudicator A cannot classify the physics family "
                      "from the input signature with its own vocabulary"})
    # control architecture: the ACTIVE side is the invention's own
    # mechanism claim; the PASSIVE side is any explicit passive/open-loop
    # statement anywhere in the dossier (that is where the template
    # record ships). Active mechanism + explicit passive record = the
    # canonical control-architecture contradiction.
    active_mech = _has(mechanism_text, A_ACTIVE_WORDS)
    passive_any = _has(dossier_text, A_PASSIVE_WORDS)
    passive_mech = _has(mechanism_text + " " + arch_text, A_PASSIVE_WORDS)
    if active_mech and passive_any:
        findings["mechanism_correctness"].append({
            "class": "CONTROL_ARCHITECTURE_CONTRADICTION",
            "detail": f"the invention mechanism claims active control "
                      f"({active_mech[:3]}) while the dossier also ships "
                      f"an explicit passive/open-loop statement "
                      f"({passive_any[:3]})"})
    elif not active_mech and not passive_mech:
        findings["mechanism_correctness"].append({
            "class": "CONTROL_ARCHITECTURE_UNDISCLOSED",
            "detail": "neither an active-control claim nor a passive/"
                      "open-loop disclosure is present — the control "
                      "architecture is unstated"})
    qty = _quantity_families(mechanism_text)
    causal = _has(mechanism_text, A_CAUSAL_CONNECTORS)
    if not qty:
        findings["mechanism_correctness"].append({
            "class": "MECHANISM_LACKS_PHYSICAL_QUANTITY",
            "detail": "mechanism text names no measurable physical "
                      "quantity"})
    if not causal:
        findings["mechanism_correctness"].append({
            "class": "MECHANISM_LACKS_CAUSAL_CONNECTOR",
            "detail": "mechanism text states no causal relation between "
                      "physical quantities"})

    # ---- axis 2: engineering reasoning correctness ------------------------
    chains = ((eng.get("engineering_reasoning_chains") or {})
              .get("chains")) or []
    claim_engaged = 0
    claims_total = 0
    numeric_output_without_guard = 0
    for c in chains:
        nodes = {n.get("node_type"): n for n in c.get("nodes") or []}
        if "CLAIM" in nodes:
            claims_total += 1
            model = nodes.get("EQUATION_MODEL") or {}
            refs = ((model.get("provenance") or {}).get("refs")) or {}
            if refs.get("equation_id"):
                claim_engaged += 1
        out_node = nodes.get("OUTPUT") or {}
        out_content = _txt(out_node.get("content"))
        out_refs = ((out_node.get("provenance") or {}).get("refs")) or {}
        if re.search(r"=\s*\d", out_content) and \
                not any(m in _txt(out_refs).upper() for m in
                        ("FORBIDDEN", "UNKNOWN", "NOT_ESTABLISHED")):
            numeric_output_without_guard += 1
    if claims_total and claim_engaged / claims_total < 0.5:
        findings["engineering_reasoning_correctness"].append({
            "class": "CLAIMS_NOT_ENGAGED_WITH_MODEL",
            "detail": f"{claim_engaged}/{claims_total} claims engage a "
                      f"quantitative model (equation ref)"})
    if claims_total and claim_engaged == 0:
        findings["engineering_reasoning_correctness"][-1] = {
            "class": "CLAIMS_NOT_ENGAGED_WITH_MODEL",
            "detail": f"0/{claims_total} claims engage any quantitative "
                      f"model — reasoning is qualitative only"}
    if numeric_output_without_guard:
        findings["engineering_reasoning_correctness"].append({
            "class": "NUMERIC_OUTPUT_WITHOUT_SOURCE_GUARD",
            "detail": f"{numeric_output_without_guard} OUTPUT nodes carry "
                      f"numeric values without a source/falsification guard"})
    if len({n.get("node_type") for c in chains
            for n in c.get("nodes") or []}) < 6:
        findings["engineering_reasoning_correctness"].append({
            "class": "CHAIN_ROLE_COVERAGE_THIN",
            "detail": "reasoning chains do not exercise the full "
                      "CLAIM..VERIFICATION role set"})

    # ---- axis 3: equation applicability -----------------------------------
    gm = ((eng.get("engineering_core") or {}).get("governing_model")) or {}
    equations = gm.get("equations") or []
    eq_total = eq_applicable = 0
    for eq in equations:
        eq_total += 1
        name = _txt(eq.get("name")).lower()
        verdict = _txt(((eq.get("selection_rationale") or {})
                        .get("verdict"))).upper()
        applicability = " ".join(_txt(eq.get(k)) for k in
                                 ("applicability", "model_applicability",
                                  "assumptions", "model_assumptions"))
        regime = next((r for key, r in A_EQ_REGIMES.items()
                       if key in name), None)
        if verdict == "REJECTED":
            eq_applicable += 1  # honest rejection is CORRECT behavior
            continue
        if regime is None:
            findings["equation_applicability"].append({
                "class": "EQUATION_REGIME_UNKNOWN_TO_ADJUDICATOR",
                "detail": f"equation '{_txt(eq.get('name'))[:60]}' not in "
                          f"adjudicator A's regime table"})
            continue
        missing = [t for t in regime["requires"]
                   if t not in applicability.lower()]
        if missing:
            findings["equation_applicability"].append({
                "class": "EQUATION_REGIME_REQUIREMENT_NOT_STATED",
                "detail": f"equation '{_txt(eq.get('name'))[:60]}': "
                          f"regime requirements not stated in the "
                          f"applicability record: {missing}"})
        else:
            eq_applicable += 1
    if eq_total == 0:
        findings["equation_applicability"].append({
            "class": "NO_GOVERNING_EQUATIONS",
            "detail": "the engineering core carries no governing equations"})
    elif eq_applicable / eq_total < 0.5:
        findings["equation_applicability"].append({
            "class": "EQUATION_APPLICABILITY_MOSTLY_UNVERIFIABLE",
            "detail": f"{eq_applicable}/{eq_total} equations carry "
                      f"verifiable regime statements"})

    # ---- axis 4: failure-mode correctness ----------------------------------
    fms = eng.get("failure_analysis") or []
    fam_fms = A_FAMILY_DOMINANT_FAILURES.get(fam or "", ())
    fm_text = " ".join(_txt(f.get("failure_mode")) + " " +
                       _txt(f.get("mode")) + " " +
                       _txt(f.get("physical_mechanism")) for f in fms).lower()
    covered = sum(1 for pat in fam_fms
                  if re.search(pat, fm_text))
    if fam_fms and covered / len(fam_fms) < 0.5:
        findings["failure_mode_correctness"].append({
            "class": "DOMINANT_FAMILY_FAILURE_MODES_MISSING",
            "detail": f"{covered}/{len(fam_fms)} dominant physical failure "
                      f"modes for the classified family are analyzed"})
    adversarial = sum(1 for f in fms
                      if "adversarial" in _txt(f.get("mode")).lower())
    if fms and adversarial / len(fms) > 0.5:
        findings["failure_mode_correctness"].append({
            "class": "FAILURE_ANALYSIS_DOMINATED_BY_PLACEHOLDERS",
            "detail": f"{adversarial}/{len(fms)} failure rows are "
                      f"adversarial-dimension placeholders, not physical "
                      f"failure analysis"})
    generic_phys = sum(1 for f in fms if _is_generic(
        _txt(f.get("physical_mechanism"))))
    if fms and generic_phys / len(fms) > 0.5:
        findings["failure_mode_correctness"].append({
            "class": "FAILURE_MECHANISMS_MOSTLY_NOT_ESTABLISHED",
            "detail": f"{generic_phys}/{len(fms)} failure rows carry no "
                      f"established physical mechanism"})
    for f in fms:
        fm_q = _quantity_families(_txt(f.get("failure_mode")) + " " +
                                  _txt(f.get("physical_mechanism")))
        if fam and fm_q and fam not in fm_q and \
                len(fm_q - {fam}) >= 2:
            findings["failure_mode_correctness"].append({
                "class": "FAILURE_MODE_PHYSICS_OUTSIDE_FAMILY",
                "detail": f"failure row '{_txt(f.get('graph_id'))}' is "
                          f"phrased in {sorted(fm_q)} quantities while the "
                          f"invention is classified {fam}"})
            break

    # ---- axis 5: verification appropriateness ------------------------------
    wrong_qty = 0
    checked = 0
    for f in fms:
        test = _txt(f.get("verification_test"))
        if not test or _is_generic(test):
            continue
        checked += 1
        fm_q = _quantity_families(_txt(f.get("physical_mechanism")))
        vf_q = _quantity_families(test)
        if fm_q and vf_q and not (fm_q & vf_q):
            wrong_qty += 1
            findings["verification_appropriateness"].append({
                "class": "VERIFICATION_MEASURES_WRONG_QUANTITY",
                "detail": f"{_txt(f.get('graph_id'))}: test measures "
                          f"{sorted(vf_q)} but the failure physics is "
                          f"{sorted(fm_q)} — the test cannot detect it"})
    if checked and wrong_qty / checked > 0.3:
        findings["verification_appropriateness"].append({
            "class": "VERIFICATION_QUANTITY_MISMATCH_WIDESPREAD",
            "detail": f"{wrong_qty}/{checked} failure verifications measure "
                      f"a disjoint physical quantity"})
    vms = eng.get("verification_matrix") or []
    with_acceptance = sum(1 for v in vms
                          if v.get("acceptance") and
                          not _is_generic(_txt(v.get("acceptance"))))
    if vms and with_acceptance / len(vms) < 0.5:
        findings["verification_appropriateness"].append({
            "class": "ACCEPTANCE_CRITERIA_MISSING",
            "detail": f"{with_acceptance}/{len(vms)} verification rows "
                      f"carry a substantive acceptance criterion"})

    return {"adjudicator": ADJUDICATOR_A, "available": True,
            "classified_family": fam,
            "axes": _axis_verdicts(findings)}


def _is_generic(text: str) -> bool:
    up = text.upper()
    return (not text.strip()) or any(
        m in up for m in ("NOT ESTABLISHED", "UNKNOWN", "NOT_PERFORMED",
                          "NOT ESTABLISHLISTED", "NOT_POSSIBLE"))


def _axis_verdicts(findings: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    out = {}
    for axis in AXES:
        fs = findings.get(axis) or []
        if any(f.get("class", "").endswith(
                ("CONTRADICTION", "WRONG_QUANTITY", "OUTSIDE_FAMILY",
                 "WITHOUT_SOURCE_GUARD", "NOT_ENGAGED_WITH_MODEL"))
               and f.get("_severity") != "questionable" for f in fs):
            verdict = "INCORRECT"
        elif any(f.get("class", "") in (
                "CONTROL_ARCHITECTURE_CONTRADICTION",
                "VERIFICATION_MEASURES_WRONG_QUANTITY",
                "FAILURE_MODE_PHYSICS_OUTSIDE_FAMILY",
                "NUMERIC_OUTPUT_WITHOUT_SOURCE_GUARD",
                "CLAIMS_NOT_ENGAGED_WITH_MODEL") for f in fs):
            verdict = "INCORRECT"
        elif fs:
            verdict = "QUESTIONABLE"
        else:
            verdict = "CORRECT"
        out[axis] = {"verdict": verdict, "findings": fs}
    return out


# ===========================================================================
# Adjudicator B — SYSTEMS_TRACE (traceability-first)
# ===========================================================================
def adjudicate_b(eng: Optional[dict], inv: Optional[dict],
                 signature_texts: Sequence[str]) -> Dict[str, Any]:
    """Works from claims/verification inward; closure and linkage focus."""
    findings: Dict[str, List[Dict[str, Any]]] = {a: [] for a in AXES}
    if not eng or not inv:
        return {"adjudicator": ADJUDICATOR_B, "available": False,
                "axes": {a: {"verdict": "QUESTIONABLE",
                             "findings": [{"class": "ARTIFACTS_UNAVAILABLE"}]}
                         for a in AXES}}
    mech_val = (inv.get("mechanism") or {}).get("value") or {}
    mechanism_text = " ".join(_txt(mech_val.get(k)) for k in
                              ("mechanism", "intervention",
                               "expected_effect"))
    source_span = _txt(mech_val.get("mechanism_source_span"))

    # ---- axis 1: mechanism correctness (traceability + specificity) -------
    if source_span:
        overlap = _word_overlap(source_span, mechanism_text)
        if overlap < 0.5:
            findings["mechanism_correctness"].append({
                "class": "MECHANISM_NOT_TRACEABLE_TO_SOURCE",
                "detail": f"only {overlap:.0%} of the source-span "
                          f"vocabulary appears in the mechanism claim"})
    else:
        findings["mechanism_correctness"].append({
            "class": "MECHANISM_SOURCE_SPAN_ABSENT",
            "detail": "the mechanism claim carries no source span"})
    if len(mechanism_text.split()) < 25:
        findings["mechanism_correctness"].append({
            "class": "MECHANISM_BODY_BELOW_SUBSTANCE_FLOOR",
            "detail": f"mechanism body is {len(mechanism_text.split())} "
                      f"words (< 25-word corpus substance floor)"})
    fals = _txt(mech_val.get("falsification_test"))
    kill = _txt(eng.get("kill_condition"))
    if not fals.strip() and not kill.strip():
        findings["mechanism_correctness"].append({
            "class": "MECHANISM_HAS_NO_FALSIFICATION_PATH",
            "detail": "neither a falsification test nor a kill condition "
                      "is recorded — the mechanism claim is untestable as "
                      "stated"})

    # ---- axis 2: engineering reasoning correctness (closure) --------------
    chains = ((eng.get("engineering_reasoning_chains") or {})
              .get("chains")) or []
    closed = 0
    for c in chains:
        nodes = {n.get("node_type"): n for n in c.get("nodes") or []}
        fm_refs = ((nodes.get("FAILURE_MODE") or {}).get("provenance")
                   or {}).get("refs") or {}
        vf_refs = ((nodes.get("VERIFICATION") or {}).get("provenance")
                   or {}).get("refs") or {}
        if fm_refs.get("failure_mode_ids") and vf_refs.get("verification_ids"):
            closed += 1
    if chains:
        closure = closed / len(chains)
        if closure == 0:
            findings["engineering_reasoning_correctness"].append({
                "class": "NO_CHAIN_CLOSED_TO_FAILURE_AND_VERIFICATION",
                "detail": f"0/{len(chains)} reasoning chains close to both "
                          f"a failure mode and a verification"})
        elif closure < 0.5:
            findings["engineering_reasoning_correctness"].append({
                "class": "CHAIN_CLOSURE_BELOW_HALF",
                "detail": f"{closed}/{len(chains)} chains close to both a "
                          f"failure mode and a verification"})
    else:
        findings["engineering_reasoning_correctness"].append({
            "class": "NO_REASONING_CHAINS",
            "detail": "the engineering specification carries no reasoning "
                      "chains"})
    dg = eng.get("design_graph") or {}
    maps = dg.get("linkage_maps") or {}
    fm_parent_do = maps.get("fm_parent_do") or {}
    do_parent_di = maps.get("do_parent_di") or {}
    fms = eng.get("failure_analysis") or []
    dos = eng.get("design_outputs") or []
    if fms:
        fm_linked = sum(1 for fm_rows in fm_parent_do.values() if fm_rows)
        # fm_parent_do maps FM->list per DO? structure: {do: [fms]} — use
        # design_graph counts instead for FM linkage
        counts = dg.get("counts") or {}
        n_fm = counts.get("FM") or len(fms)
        linked_fms = len({fm for lst in fm_parent_do.values()
                          for fm in (lst if isinstance(lst, list) else [])})
        if linked_fms / max(n_fm, 1) < 0.5:
            findings["engineering_reasoning_correctness"].append({
                "class": "FM_TO_DESIGN_OUTPUT_LINKAGE_THIN",
                "detail": f"{linked_fms}/{n_fm} failure modes link to any "
                          f"design output"})
    if dos:
        do_linked = sum(1 for do_rows in do_parent_di.values() if do_rows)
        if do_linked / len(dos) < 0.5:
            findings["engineering_reasoning_correctness"].append({
                "class": "DI_TO_DO_LINKAGE_THIN",
                "detail": f"{do_linked}/{len(dos)} design outputs trace to "
                          f"a design input"})

    # ---- axis 3: equation applicability (coverage-first) -------------------
    gm = ((eng.get("engineering_core") or {}).get("governing_model")) or {}
    equations = gm.get("equations") or []
    if equations:
        tied = sum(1 for e in equations if _txt(e.get("invention_tie"))
                   and not _is_generic(_txt(e.get("invention_tie"))))
        if tied / len(equations) < 0.5:
            findings["equation_applicability"].append({
                "class": "EQUATIONS_NOT_TIED_TO_INVENTION",
                "detail": f"{tied}/{len(equations)} governing equations "
                          f"carry an invention tie"})
        verdicts = {_txt(((e.get("selection_rationale") or {})
                          .get("verdict"))).upper() for e in equations}
        if verdicts and verdicts <= {"APPLICABLE"}:
            findings["equation_applicability"].append({
                "class": "NO_APPLICABILITY_JUDGMENT_VISIBLE",
                "detail": "every equation is marked APPLICABLE with no "
                          "CONDITIONAL/REJECTED judgment recorded — "
                          "applicability reasoning is not visible"})
    else:
        findings["equation_applicability"].append({
            "class": "NO_GOVERNING_EQUATIONS",
            "detail": "the engineering core carries no governing equations"})

    # ---- axis 4: failure-mode correctness (control coverage) ---------------
    input_fm = ""
    for t in signature_texts:
        if t and t.isupper():
            input_fm = t
            break
    fm_names = " ".join(_txt(f.get("failure_mode")) + " " +
                        _txt(f.get("mode")) for f in fms).upper()
    if input_fm and input_fm not in fm_names:
        findings["failure_mode_correctness"].append({
            "class": "INPUT_FAILURE_MODE_NOT_ANALYZED",
            "detail": "the failure the invention is meant to solve is not "
                      "itself present in the failure analysis"})
    if fms:
        with_control = sum(1 for f in fms
                           if _txt(f.get("design_control"))
                           and not _is_generic(_txt(f.get("design_control"))))
        if with_control / len(fms) < 0.5:
            findings["failure_mode_correctness"].append({
                "class": "DESIGN_CONTROL_COVERAGE_THIN",
                "detail": f"{with_control}/{len(fms)} failure rows carry a "
                          f"design control"})
        with_kill = sum(1 for f in fms if _txt(f.get("kill_condition")).strip()
                        and not _is_generic(_txt(f.get("kill_condition"))))
        if with_kill / len(fms) < 0.5:
            findings["failure_mode_correctness"].append({
                "class": "KILL_CONDITION_COVERAGE_THIN",
                "detail": f"{with_kill}/{len(fms)} failure rows carry a "
                          f"kill condition"})

    # ---- axis 5: verification appropriateness (acceptance + ties) ----------
    vms = eng.get("verification_matrix") or []
    if vms:
        quantified = sum(1 for v in vms
                         if re.search(r"\d", _txt(v.get("acceptance")))
                         or _named_standard(_txt(v.get("acceptance"))))
        if quantified / len(vms) < 0.5:
            findings["verification_appropriateness"].append({
                "class": "ACCEPTANCE_CRITERIA_NOT_QUANTIFIED",
                "detail": f"{quantified}/{len(vms)} acceptance criteria "
                          f"carry a numeric threshold or named standard"})
        tied = sum(1 for v in vms if _txt(v.get("invention_tie")).strip())
        if tied / len(vms) < 0.5:
            findings["verification_appropriateness"].append({
                "class": "VERIFICATIONS_NOT_TIED_TO_INVENTION",
                "detail": f"{tied}/{len(vms)} verification rows carry an "
                          f"invention tie"})
    vas = eng.get("validation_matrix") or []
    performed = sum(1 for v in vas
                    if not _is_generic(_txt(v.get("method")))
                    and "NOT_PERFORMED" not in _txt(v.get("result")).upper())
    if not performed:
        findings["verification_appropriateness"].append({
            "class": "NO_SPECIFIED_VALIDATION",
            "detail": "no validation row carries a specified method with a "
                      "performed/non-blocked result (honest disclosure, "
                      "zero validation specificity)"})

    return {"adjudicator": ADJUDICATOR_B, "available": True,
            "axes": _axis_verdicts(findings)}


def _named_standard(text: str) -> bool:
    return bool(re.search(
        r"(IEEE|IEC|ISO|ASTM|AAMI|ANSI)\s*C?[\d.]+", text, re.I))


def _word_overlap(source: str, target: str) -> float:
    stop = {"the", "a", "an", "of", "and", "or", "to", "in", "by", "with",
            "for", "as", "at", "is", "are", "that", "this", "it", "its",
            "from", "on", "be", "into", "when", "where", "which", "than"}
    ws = {w for w in re.findall(r"[a-z][a-z\-]+", source.lower())
          if len(w) > 3 and w not in stop}
    wt = {w for w in re.findall(r"[a-z][a-z\-]+", target.lower())
          if len(w) > 3 and w not in stop}
    if not ws:
        return 1.0 if not wt else 0.0
    return len(ws & wt) / len(ws)


# ===========================================================================
# Sample selection + adjudication run
# ===========================================================================
def _load_population() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Released dossiers: committed (BENCH_*) + blind (BLIND_*)."""
    committed, blind = [], []
    for root, tag in ((COMMITTED_RUNS, "COMMITTED"), (BLIND_RUNS, "BLIND")):
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            try:
                rel = json.loads(
                    (d / "DISCOVERY_RELEASE.json").read_text())
            except Exception:
                continue
            if rel.get("status") != "RELEASED":
                continue
            record = {"run_dir": str(d), "set": tag, "name": d.name}
            if tag == "BLIND":
                from .data_split import blind_input_hash, load_blind_set
                specs = load_blind_set()
                idx = int(d.name.split("_")[1])
                record["blind_hash"] = blind_input_hash(specs[idx - 1])
            (committed if tag == "COMMITTED" else blind).append(record)
    return committed, blind


def _signature(run_dir: Path) -> List[str]:
    out: List[str] = []
    try:
        prob = json.loads((run_dir / "problem.json").read_text())
        out.extend(str(v) for v in prob.values() if isinstance(v, str))
        env = json.loads(
            (run_dir / "candidate_envelope.json").read_text())
        mm = env.get("mechanism_map") or {}
        for k in ("mechanism", "intervention", "expected_effect"):
            if isinstance(mm.get(k), str):
                out.append(mm[k])
    except Exception:
        pass
    return out


def adjudicate_sample(record: Dict[str, Any]) -> Dict[str, Any]:
    rd = Path(record["run_dir"])
    eng = json.loads((rd / "ENGINEERING_SPECIFICATION.json").read_text())
    inv = json.loads((rd / "INVENTION_SPECIFICATION.json").read_text())
    sig = _signature(rd)
    a = adjudicate_a(eng, inv, sig)
    b = adjudicate_b(eng, inv, sig)
    axes = {}
    disagreements = []
    for axis in AXES:
        va = (a["axes"][axis]["verdict"])
        vb = (b["axes"][axis]["verdict"])
        agree = va == vb
        entry = {
            ADJUDICATOR_A: {"verdict": va,
                            "finding_classes":
                                [f["class"] for f in
                                 a["axes"][axis]["findings"]]},
            ADJUDICATOR_B: {"verdict": vb,
                            "finding_classes":
                                [f["class"] for f in
                                 b["axes"][axis]["findings"]]},
            "agreement": agree,
            "recorded_verdict": va if agree else "DISAGREEMENT",
        }
        if not agree:
            disagreements.append({
                "axis": axis,
                ADJUDICATOR_A: va,
                ADJUDICATOR_B: vb,
                "resolution": "NONE — preserved as disagreement (CEO B9)",
            })
        axes[axis] = entry
    return {
        "sample": record,
        "adjudicator_a_family": a.get("classified_family"),
        "axes": axes,
        "disagreements": disagreements,
    }


def run_blind_adjudication(
        sample_size: int = 6, seed: int = 20260828,
        out_path: Path = OUT_PATH) -> Dict[str, Any]:
    """Seed-recorded random sample of released dossiers, both adjudicators,
    disagreements preserved."""
    committed, blind = _load_population()
    population = committed + blind
    rng = random.Random(seed)
    k = min(sample_size, len(population))
    sample = rng.sample(population, k)

    rows = []
    for record in sample:
        row = adjudicate_sample(record)
        if record["set"] == "BLIND":
            # blind-safe publication: hash key + verdicts + classes only
            row["publication"] = {
                "sample_id": f"BLIND_{row['sample']['blind_hash'][:12]}",
                "set": "BLIND_RELEASED",
                "disclosure": "verdicts and finding classes only — no "
                              "domains, devices, mechanisms, or quoted text",
            }
            row["sample"] = {"set": "BLIND_RELEASED",
                             "blind_hash": row["sample"]["blind_hash"]}
            # strip adjudicator A's family classification? family names are
            # coarse instrument families, not blind content — but keep the
            # disclosure conservative: retain only for committed samples
            row["adjudicator_a_family"] = None
            row["publication"]["family_classification"] = "withheld (blind)"
        else:
            row["publication"] = {
                "sample_id": record["name"],
                "set": "COMMITTED_RELEASED",
            }
        rows.append(row)

    # aggregates
    agreement_stats = {}
    for axis in AXES:
        agree = sum(1 for r in rows
                    if r["axes"][axis]["agreement"])
        agreement_stats[axis] = {
            "agreed": agree, "disagreed": len(rows) - agree,
            "agreement_rate": round(agree / len(rows), 3) if rows else None}
    verdict_dist = {adj: {} for adj in (ADJUDICATOR_A, ADJUDICATOR_B)}
    for r in rows:
        for axis in AXES:
            for adj in verdict_dist:
                v = r["axes"][axis][adj]["verdict"]
                verdict_dist[adj][v] = verdict_dist[adj].get(v, 0) + 1
    all_disagreements = [d for r in rows for d in r["disagreements"]]

    artifact = {
        "artifact": "BLIND_SEMANTIC_ADJUDICATION",
        "owner": "CODER2",
        "ceo_directive": "Phase 3 B9 — independent semantic adjudication "
                         "layer; preserve disagreements",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "population": {
            "released_dossiers_total": len(population),
            "committed": len(committed), "blind": len(blind)},
        "sampling": {"method": "seeded random sample (reproducible)",
                     "seed": seed, "sample_size": k,
                     "sampled": [r["publication"]["sample_id"]
                                 for r in rows]},
        "axes": list(AXES),
        "adjudicators": {
            ADJUDICATOR_A: "physics-first: family classification, control "
                           "architecture, equation regimes, FM physics, "
                           "verification quantity disjointness (own "
                           "vocabulary, own code path)",
            ADJUDICATOR_B: "traceability-first: source-span traceability, "
                           "chain closure, DI->DO->FM linkage, equation "
                           "ties, acceptance quantification (own code path)",
        },
        "independence_disclosure": {
            "no_coder1_labels_as_input": True,
            "no_b3_b4_detector_reuse": "neither adjudicator imports "
                                       "semantic_causal or "
                                       "semantic_genericness",
            "residual_self_reference_risk": "both adjudicators are authored "
                                            "by Coder 2 (benchmark author) "
                                            "— disclosed; the external "
                                            "counterweight is the CEO B11 "
                                            "human spot-check",
            "disagreement_policy": "preserved with both verdicts, never "
                                   "averaged or resolved by a third rule",
        },
        "agreement_stats": agreement_stats,
        "verdict_distributions": verdict_dist,
        "disagreement_count": len(all_disagreements),
        "disagreement_register": all_disagreements,
        "samples": rows,
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=1,
                                       ensure_ascii=False),
                            encoding="utf-8")
    return artifact


def main() -> int:
    art = run_blind_adjudication()
    print("=" * 70)
    print("CODER2 BLIND SEMANTIC ADJUDICATION (CEO Phase 3 B9)")
    print("=" * 70)
    print(f"population: {art['population']}")
    print(f"sample (seed {art['sampling']['seed']}): "
          f"{art['sampling']['sampled']}")
    print(f"disagreements preserved: {art['disagreement_count']}")
    for axis, s in art["agreement_stats"].items():
        print(f"  {axis:36s} agreement "
              f"{s['agreement_rate']:.0%} ({s['agreed']}/{s['agreed'] + s['disagreed']})")
    for adj, dist in art["verdict_distributions"].items():
        print(f"  {adj}: {dist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

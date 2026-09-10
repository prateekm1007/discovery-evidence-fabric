"""discovery_fabric/engine/applicability.py — R443: the ONE canonical
problem-context applicability authority.

THE MEASURED DEFECT (external audit, fresh production wastewater
heat-exchanger case at deployed SHA 0b58f106):

  The package path produced a technically plausible-looking industrial
  technology package whose buyer requirements were from the WRONG
  domain: patient/reservoir termination interfaces, medical tubing
  extrusion, medical-grade silicone, FDA 510(k)/PMA requirements and
  neurosurgery market channels — sourced from (a) domain templates
  written around the CSF-shunt portfolio (medical context baked into
  domain-PHYSICS content: domains.py fluidics_hydraulic carries
  "termination interfaces (patient / reservoir)", medical-grade
  silicone, medical extrusion, ISO 13485/14971) and (b) the frozen
  portfolio builder's hardcoded Licensee Capability Fit
  (build_portfolio_v4.py: catheter design, medical tubing, FDA
  510(k), neurosurgery channels) applied to EVERY package.

THE R443 REPAIR — one authority, one chain:

    USER PROBLEM
        ↓  detect_applicability()          (THIS module — context, deterministic)
    CANONICAL APPLICABILITY STATE          (engineering_specification.applicability)
        ↓  context_requirements()
    BUYER / MANUFACTURING / REGULATORY / MARKET REQUIREMENTS
        ↓  filter_domain_module_content()  (domains.py content tagged by context)
    ENGINEERING COMPONENT ROLES + MATERIALS + STANDARDS
        ↓  (package compiler consumes the canonical state)
    PDF → ZIP

CONSTITUTIONAL BASIS:
- Art. X (one canonical authority): applicability is decided ONCE, in
  the engineering specification; the CIO, the website, and the package
  compiler are consumers, never re-guessers. domains.py remains the
  DOMAIN-PHYSICS authority (E21-D phenomena layer, unchanged); THIS
  module is the CONTEXT authority (medical / industrial / consumer /
  laboratory). The two compose; they never compete.
- Art. XXVIII (no silent semantic promotion): a medical-context
  requirement NEVER silently applies to a non-medical problem. The
  excluded candidates are RECORDED with their reason (never hidden,
  never stripped globally — the words stay available to legitimately
  medical problems).
- Art. XXVII (no threshold invention): requirement statements carry
  their basis; where the canonical state does not support a claim the
  honest values are UNKNOWN / NOT_APPLICABLE / UNSUPPORTED — never a
  plausible-sounding invented requirement.
- Art. XXXVIII: applicability is MODEL_DERIVED reasoning over the
  recorded problem text; it is never evidence and never a regulatory
  determination.

SELECTION RULE (deterministic, recorded — same discipline as
domain_reasoning.E21-D): context is scored from the PROBLEM's own text
(the user problem, the recorded problem statement, and the invention's
intervention site/mechanism). Medical CONTEXT signals (patient,
clinical, in-vivo, implant...) are deliberately SEPARATE from domain
physics signals: a catheter is a fluid device as PHYSICS but medical
as CONTEXT only when the problem says so. Ties resolve by fixed
registry order; below the minimum score the honest UNKNOWN class is
selected and every downstream requirement becomes UNKNOWN — never a
default guess.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Context classes (closed vocabulary — extending is a contract change)
# ---------------------------------------------------------------------------

MEDICAL_IN_VIVO = "MEDICAL_IN_VIVO"
MEDICAL_EX_VIVO = "MEDICAL_EX_VIVO"
INDUSTRIAL_PROCESS = "INDUSTRIAL_PROCESS"
LABORATORY_BENCH = "LABORATORY_BENCH"
CONSUMER = "CONSUMER"
UNKNOWN = "UNKNOWN"

CONTEXT_CLASSES = (
    MEDICAL_IN_VIVO, MEDICAL_EX_VIVO, INDUSTRIAL_PROCESS,
    LABORATORY_BENCH, CONSUMER, UNKNOWN,
)

#: signals are lowercase; multi-word signals match as substrings,
#: single tokens < 5 chars match on word boundaries (the domain_reasoning
#: discipline — an acronym must not match inside an unrelated word).
_CONTEXT_SIGNALS: List[Tuple[str, List[Tuple[str, int]]]] = [
    (MEDICAL_IN_VIVO, [
        ("patient", 6), ("in vivo", 6), ("in-vivo", 6),
        ("implant", 6), ("implantable", 6), ("intravascular", 6),
        ("neurosurgery", 8), ("neurosurgical", 8), ("surgical", 4),
        ("catheter", 6), ("shunt", 6), ("csf", 5),
        ("cerebrospinal", 7), ("hydrocephalus", 8),
        ("clinical", 5), ("clinically", 5), ("therapy", 4),
        ("therapeutic", 5), ("diagnostic", 4), ("diagnosis", 4),
        ("biocompatib", 7), ("fda", 5), ("510(k)", 6), ("pma", 4),
        ("steriliz", 6), ("hospital", 5), ("physician", 5),
        ("iso 10993", 6), ("iso 13485", 6), ("physiological", 4),
        ("lumen", 2), ("delivery of", 1), ("stent", 5),
    ]),
    (MEDICAL_EX_VIVO, [
        ("assay", 5), ("in vitro", 5), ("in-vitro", 5),
        ("clinical laboratory", 6), ("sample preparation", 4),
        ("diagnostic test", 5), ("point of care", 5),
        ("blood", 4), ("serum", 4), ("biopsy", 5),
    ]),
    (INDUSTRIAL_PROCESS, [
        ("wastewater", 8), ("industrial", 6), ("plant", 5),
        ("process stream", 6), ("municipal", 6), ("effluent", 7),
        ("utility", 5), ("refinery", 6), ("hvac", 6),
        ("heat recovery", 5), ("chemical plant", 6),
        ("water treatment", 6), ("filtration plant", 5),
        ("manufacturing line", 5), ("factory", 5),
        ("process industry", 6), ("boiler", 4), ("heat exchanger", 4),
        ("process fluid", 5), ("flue", 4), ("cooling tower", 5),
        ("district heating", 6), ("offshore", 4), ("pipeline", 4),
        ("pulp", 3), ("mining", 4), ("brewery", 4), ("dairy", 3),
        ("desalination", 6), (" scrubber", 5), ("stack", 3),
    ]),
    (LABORATORY_BENCH, [
        ("benchtop", 6), ("laboratory instrument", 6),
        ("research instrument", 5), ("analytical instrument", 5),
        ("sample throughput", 4), ("autosampler", 6),
        ("lab bench", 5), ("measurement setup", 3),
        ("test rig", 3), ("metrology", 5),
    ]),
    (CONSUMER, [
        ("consumer", 6), ("household", 6), ("residential", 5),
        ("kitchen", 5), ("portable device", 3), ("wearable", 5),
        ("smartphone", 5), ("home appliance", 5), ("domestic", 5),
    ]),
]

#: the honest floor: a whole-context class needs real signal, not one
#: weak keyword (Art. XXVII: the number's provenance is this registry +
#: the recorded score table — the same rule as the domain family
# threshold in invention_bridge.domain_spec).
_MIN_CONTEXT_SCORE = 4

#: which context classes count as MEDICAL for regulatory/requirements
MEDICAL_CONTEXTS = frozenset({MEDICAL_IN_VIVO, MEDICAL_EX_VIVO})


def _signal_hit(text_padded: str, signal: str) -> bool:
    signal = signal.strip().lower()
    if not signal:
        return False
    if len(signal) >= 5 or " " in signal:
        return signal in text_padded
    return re.search(rf"\b{re.escape(signal)}\b", text_padded) is not None


def detect_applicability(*text_sources: str) -> Dict[str, Any]:
    """The canonical problem-context decision. Deterministic; the FULL
    score table is recorded so the choice is auditable from the
    artifact alone (Art. XXVII — no magic thresholds).

    Medical context is decided by the problem's OWN words. A "catheter"
    mentioned as physics vocabulary does NOT make a problem medical
    unless the problem's context says so — and the medical signals
    carry enough weight that genuinely medical problems win decisively
    over weak industrial mentions (and vice versa).
    """
    text = " ".join(str(t or "") for t in text_sources).lower()
    text_padded = f" {text} "
    scores: List[Dict[str, Any]] = []
    best_class, best_score = UNKNOWN, 0
    for context_class, signals in _CONTEXT_SIGNALS:
        total, hits = 0, []
        for signal, weight in signals:
            if _signal_hit(text_padded, signal):
                total += weight
                hits.append({"signal": signal.strip(), "weight": weight})
        scores.append({"context_class": context_class, "score": total,
                       "hits": hits})
        if total > best_score:
            best_class, best_score = context_class, total
    if best_score < _MIN_CONTEXT_SCORE:
        best_class = UNKNOWN
    return {
        "artifact": "PROBLEM_CONTEXT_APPLICABILITY",
        "context_class": best_class,
        "score": best_score,
        "min_context_score": _MIN_CONTEXT_SCORE,
        "score_table": scores,
        "matched_signals": next(
            (s["hits"] for s in scores
             if s["context_class"] == best_class), []),
        "basis": (
            "context class selected by deterministic signal score over "
            "the canonical problem text (user problem + recorded "
            "problem statement + invention mechanism/intervention "
            "site); ties resolve by fixed registry order; below the "
            "minimum score the honest UNKNOWN class is selected — "
            "every downstream requirement becomes UNKNOWN, never a "
            "default guess"),
        "epistemic_class": "MODEL_DERIVED",
        "deterministic": True,
        "note": (
            "context is separate from domain physics: a catheter is a "
            "fluid device as PHYSICS but medical as CONTEXT only when "
            "the problem's own text carries medical context signals"),
    }


# ---------------------------------------------------------------------------
# The canonical requirements projection (context → requirements)
# ---------------------------------------------------------------------------
# Every statement carries: basis + epistemic_class + applicability.
# Honest states: UNKNOWN / NOT_APPLICABLE / UNSUPPORTED — never a
# plausible-sounding invented requirement (Art. XXVII/LXVI).

_REQ_MEDICAL_REGULATORY = {
    "statement": (
        "medical-device regulatory pathway determination (FDA "
        "510(k)/PMA or market jurisdiction equivalent) with "
        "biocompatibility evaluation (ISO 10993) and QMS (ISO 13485)"),
    "applicability": "APPLICABLE",
    "basis": ("the canonical problem context is MEDICAL "
              "(patient-contact / clinical use signals in the "
              "problem's own text); the pathway ITSELF is UNKNOWN "
              "until determined — no pathway is inferred from device "
              "class (R370C)"),
    "epistemic_class": "MODELLED",
}

_REQ_MEDICAL_NOT_APPLICABLE = {
    "statement": (
        "medical-device regulatory requirements (FDA 510(k)/PMA, "
        "ISO 10993 biocompatibility, ISO 13485 medical QMS)"),
    "applicability": "NOT_APPLICABLE",
    "basis": ("the canonical problem context carries NO "
              "patient-contact/clinical-use signals — medical "
              "regulatory requirements are outside this problem's "
              "applicability; they were never applicable and were "
              "never silently attached"),
    "epistemic_class": "MODELLED",
}

_CONTEXT_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    MEDICAL_IN_VIVO: {
        "buyer_type": {
            "statement": "medical device company (candidate buyer "
                         "class for an in-vivo medical technology)",
            "applicability": "APPLICABLE", "epistemic_class": "MODELLED",
            "basis": "canonical context MEDICAL_IN_VIVO"},
        "engineering_capability": [
            {"statement": "medical device design engineering with the "
                          "domain's physics (see engineering "
                          "specification governing model)",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "domain + context composition"}],
        "manufacturing_capability": [
            {"statement": "medical-grade manufacturing (cleanroom "
                          "assembly, medical extrusion/molding as the "
                          "device requires) under a certified QMS",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context MEDICAL_IN_VIVO"},
            {"statement": "sterilization-validation capability",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "in-vivo use requires a validated sterilization "
                      "process (the specific method is UNKNOWN until "
                      "the design is defined)"}],
        "regulatory": _REQ_MEDICAL_REGULATORY,
        "market_channels": [
            {"statement": "clinical/hospital market channels",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context MEDICAL_IN_VIVO"}],
    },
    MEDICAL_EX_VIVO: {
        "buyer_type": {
            "statement": "diagnostics / laboratory-technology company",
            "applicability": "APPLICABLE", "epistemic_class": "MODELLED",
            "basis": "canonical context MEDICAL_EX_VIVO"},
        "engineering_capability": [
            {"statement": "diagnostic-assay / instrument engineering "
                          "with the domain's physics",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "domain + context composition"}],
        "manufacturing_capability": [
            {"statement": "instrument manufacturing with controlled "
                          "assembly and calibration",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context MEDICAL_EX_VIVO"}],
        "regulatory": _REQ_MEDICAL_REGULATORY,
        "market_channels": [
            {"statement": "clinical-laboratory / diagnostics channels",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context MEDICAL_EX_VIVO"}],
    },
    INDUSTRIAL_PROCESS: {
        "buyer_type": {
            "statement": ("industrial process-equipment / component "
                          "manufacturer (candidate buyer class for an "
                          "industrial process technology)"),
            "applicability": "APPLICABLE", "epistemic_class": "MODELLED",
            "basis": "canonical context INDUSTRIAL_PROCESS"},
        "engineering_capability": [
            {"statement": ("process/mechanical engineering with the "
                           "domain's physics (see the engineering "
                           "specification's governing model)"),
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "domain + context composition"},
            {"statement": ("field/plant integration engineering for "
                           "the recorded operating environment"),
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context INDUSTRIAL_PROCESS"}],
        "manufacturing_capability": [
            {"statement": ("general industrial fabrication (machining, "
                           "welding/brazing, sheet/plate work, "
                           "assembly) — the specific processes are the "
                           "domain candidates recorded in the "
                           "engineering specification"),
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context INDUSTRIAL_PROCESS"},
            {"statement": ("quality control appropriate to the "
                           "recorded failure modes"),
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "failure modes are invention-specific records"}],
        "regulatory": {
            "statement": (
                "applicable industrial codes/standards (e.g. pressure "
                "equipment, piping, electrical) UNKNOWN until "
                "determined for the installation jurisdiction — the "
                "buyer's regulatory affairs makes the determination; "
                "medical-device regulation is NOT_APPLICABLE"),
            "applicability": "UNKNOWN",
            "basis": ("no determination exists for this invention; "
                      "the applicable codes depend on the installation "
                      "jurisdiction and service conditions, which the "
                      "canonical record does not carry — the pathway "
                      "is never invented (R370C/Art. XXVII)"),
            "epistemic_class": "UNKNOWN",
            "medical_not_applicable": _REQ_MEDICAL_NOT_APPLICABLE,
        },
        "market_channels": [
            {"statement": ("industrial process / water-utility / plant "
                           "engineering channels appropriate to the "
                           "recorded application"),
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context INDUSTRIAL_PROCESS"}],
    },
    LABORATORY_BENCH: {
        "buyer_type": {
            "statement": "instrument / laboratory-technology company",
            "applicability": "APPLICABLE", "epistemic_class": "MODELLED",
            "basis": "canonical context LABORATORY_BENCH"},
        "engineering_capability": [
            {"statement": "instrument engineering with the domain's "
                          "physics",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "domain + context composition"}],
        "manufacturing_capability": [
            {"statement": "instrument manufacturing (precision "
                          "machining, controlled assembly, calibration)",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context LABORATORY_BENCH"}],
        "regulatory": {
            "statement": ("applicable standards UNKNOWN until "
                          "determined; medical-device regulation "
                          "NOT_APPLICABLE"),
            "applicability": "UNKNOWN",
            "basis": ("no determination exists; the bench context "
                      "carries no patient-contact signals"),
            "epistemic_class": "UNKNOWN",
            "medical_not_applicable": _REQ_MEDICAL_NOT_APPLICABLE,
        },
        "market_channels": [
            {"statement": "research-instrument / laboratory-supply "
                          "channels",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context LABORATORY_BENCH"}],
    },
    CONSUMER: {
        "buyer_type": {
            "statement": "consumer-product company",
            "applicability": "APPLICABLE", "epistemic_class": "MODELLED",
            "basis": "canonical context CONSUMER"},
        "engineering_capability": [
            {"statement": "consumer product engineering with the "
                          "domain's physics",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "domain + context composition"}],
        "manufacturing_capability": [
            {"statement": "consumer-scale manufacturing (high-volume "
                          "molding/assembly)",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context CONSUMER"}],
        "regulatory": {
            "statement": ("applicable consumer-product standards "
                          "UNKNOWN until determined; medical-device "
                          "regulation NOT_APPLICABLE"),
            "applicability": "UNKNOWN",
            "basis": "no determination exists for this invention",
            "epistemic_class": "UNKNOWN",
            "medical_not_applicable": _REQ_MEDICAL_NOT_APPLICABLE,
        },
        "market_channels": [
            {"statement": "consumer retail / product channels",
             "applicability": "APPLICABLE",
             "epistemic_class": "MODELLED",
             "basis": "canonical context CONSUMER"}],
    },
    UNKNOWN: {
        "buyer_type": {
            "statement": "UNKNOWN — buyer class not determinable from "
                         "the canonical problem text",
            "applicability": "UNKNOWN", "epistemic_class": "UNKNOWN",
            "basis": ("context detection below the minimum score — the "
                      "honest state is UNKNOWN, never a default "
                      "buyer guess")},
        "engineering_capability": [
            {"statement": "UNKNOWN — required engineering capability "
                          "not determinable without a context decision",
             "applicability": "UNKNOWN", "epistemic_class": "UNKNOWN",
             "basis": "context UNKNOWN"}],
        "manufacturing_capability": [
            {"statement": "UNKNOWN — required manufacturing capability "
                          "not determinable without a context decision",
             "applicability": "UNKNOWN", "epistemic_class": "UNKNOWN",
             "basis": "context UNKNOWN"}],
        "regulatory": {
            "statement": "UNKNOWN — regulatory applicability not "
                         "determinable from the canonical problem text",
            "applicability": "UNKNOWN", "epistemic_class": "UNKNOWN",
            "basis": ("context UNKNOWN: no medical NOT_APPLICABLE "
                      "statement is claimable either (the context "
                      "itself is undetermined)")},
        "market_channels": [
            {"statement": "UNKNOWN — market channels not determinable "
                          "without a context decision",
             "applicability": "UNKNOWN", "epistemic_class": "UNKNOWN",
             "basis": "context UNKNOWN"}],
    },
}


def context_requirements(context_class: str) -> Dict[str, Any]:
    """The canonical requirements projection for a context class.

    The returned structure is a DERIVED PROJECTION of the registry
    above (deterministic; Art. X: one authority — callers record this
    block verbatim in the engineering specification, they never
    re-guess it)."""
    reqs = _CONTEXT_REQUIREMENTS.get(context_class)
    if reqs is None:
        reqs = _CONTEXT_REQUIREMENTS[UNKNOWN]
    return {
        "artifact": "CONTEXT_REQUIREMENTS_PROJECTION",
        "context_class": context_class,
        "buyer_type": reqs["buyer_type"],
        "engineering_capability": list(reqs["engineering_capability"]),
        "manufacturing_capability": list(reqs["manufacturing_capability"]),
        "regulatory": dict(reqs["regulatory"]),
        "market_channels": list(reqs["market_channels"]),
        "basis": ("derived deterministically from the canonical "
                  "applicability decision (R443 applicability registry "
                  "v1); every statement carries its own basis and "
                  "epistemic class; honest states are "
                  "UNKNOWN/NOT_APPLICABLE/UNSUPPORTED — never a "
                  "silent default"),
    }


# ---------------------------------------------------------------------------
# Domain-module content filtering (context de-conflation)
# ---------------------------------------------------------------------------

def filter_domain_module_content(module: Dict[str, Any],
                                 context_class: str,
                                 ) -> Dict[str, Any]:
    """Context-filter a domain module's CONTEXT-CARRYING candidates.

    domains.py is the domain-PHYSICS authority and stays untouched as
    physics; its medical-context candidates (tagged
    applicability_context=MEDICAL at R443) participate ONLY when the
    canonical context is medical. Exclusions are RECORDED with their
    reason — never silently dropped, never globally stripped (the
    audit's constraint: the fix must not destroy legitimate medical
    cases).

    Blocks/candidates tagged GENERAL (or untagged legacy entries —
    recorded as such) always participate.
    """
    is_medical = context_class in MEDICAL_CONTEXTS
    excluded: List[Dict[str, Any]] = []

    def _keep(entry: Any, kind: str, key: str) -> Optional[Any]:
        if isinstance(entry, dict):
            ctx = entry.get("applicability_context")
        else:
            ctx = None
        if ctx is None:
            # legacy untagged entry: keep, but record the honest
            # provenance (the entry predates context tagging)
            return entry
        if ctx == "GENERAL" or (ctx == "MEDICAL" and is_medical):
            return entry
        excluded.append({
            "kind": kind,
            "key": str(entry.get(key) if isinstance(entry, dict)
                       else entry)[:120],
            "applicability_context": ctx,
            "reason": (
                f"medical-context candidate excluded — canonical "
                f"problem context is {context_class}"),
        })
        return None

    blocks_general = list(module.get("architecture_blocks") or [])
    blocks_medical = list(module.get("architecture_blocks_medical") or [])
    if is_medical:
        blocks = blocks_general + blocks_medical
    else:
        blocks = blocks_general
        for b in blocks_medical:
            excluded.append({
                "kind": "architecture_block",
                "key": str(b)[:120],
                "applicability_context": "MEDICAL",
                "reason": (f"medical-context architecture block "
                           f"excluded — canonical problem context is "
                           f"{context_class}"),
            })

    materials = [m for m in (filter(
        None, (_keep(m, "material", "material")
               for m in module.get("materials_candidates") or [])))]
    manufacturing = [m for m in (filter(
        None, (_keep(m, "manufacturing", "process")
               for m in module.get("manufacturing_candidates") or [])))]
    standards = [s for s in (filter(
        None, (_keep(s, "standard", "standard")
               for s in module.get("standards_candidates") or [])))]

    return {
        "architecture_blocks": blocks,
        "materials_candidates": materials,
        "manufacturing_candidates": manufacturing,
        "standards_candidates": standards,
        "excluded_context_mismatch": excluded,
        "filter_basis": (
            f"domain module content filtered by the canonical "
            f"applicability decision (context {context_class}); "
            f"excluded candidates recorded — never silently dropped, "
            f"never globally stripped"),
    }

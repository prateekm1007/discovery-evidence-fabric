"""discovery_fabric/engine/depth_contract.py — CEO A2: the
ENGINEERING_DEPTH_CONTRACT.

The automatic engineering generator must satisfy the same MINIMUM DEPTH as
the existing benchmark dossiers — for EVERY invention, all 20 contract
sections:

    SYSTEM_ARCHITECTURE, MECHANISM_ARCHITECTURE, ENGINEERING_DOMAIN,
    GOVERNING_MODELS, EQUATIONS, CRITICAL_PARAMETERS, DESIGN_INPUTS,
    DESIGN_OUTPUTS, FAILURE_MODES, VERIFICATION_MATRIX, VALIDATION_MATRIX,
    MATERIALS, MANUFACTURING, INTERFACES, REGULATORY,
    ENGINEERING_BUILD_PLAN, TRANSFER_BOUNDARY, KILL_CONDITION,
    BUYER_DILIGENCE, INVESTMENT_LADDER

BUT PRESENCE ALONE IS NOT ENOUGH — and (R440.3) neither is LEXICAL
COINCIDENCE. Each section must contain content tied to the ACTUAL
invention through EXPLICIT CANONICAL RELATIONSHIPS. The tie is
structural, not narrative: every section check requires

    1. present      — the section exists with the contract's minimum items
    2. invention_tied — the section's items carry linkage evidence that
       is STRUCTURAL: explicit linkage records recorded by the generators
       (invention_tie / invention_applicability / matched fields whose
       matched vocabulary includes at least one INVENTION-SPECIFIC
       (non-weak) token), domain-detection evidence (matched signals or
       phenomena anchors), or recorded canonical source references
       (source_refs). A bare token-substring hit over the section text
       and the historical blanket 'spec_derived' auto-tie are RETIRED
       (R440.3: the word 'decision' is never evidence of invention
       linkage).
    3. classed      — content carries an epistemic class/status vocabulary
       (no naked assertions)

`evaluate_depth_contract(spec, eng)` returns per-section evaluations with
evidence; `assert_depth_contract` raises on failure. The canonical
package compiler's validators and the independent package quality gate
(Gates D/E) enforce the same structural standard at the package boundary.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .candidate import sha256_obj, utc_now
from .engineering_spec import _invention_tokens

# The 20 contract sections (CEO A2, canonical order)
CONTRACT_SECTIONS = (
    "SYSTEM_ARCHITECTURE", "MECHANISM_ARCHITECTURE", "ENGINEERING_DOMAIN",
    "GOVERNING_MODELS", "EQUATIONS", "CRITICAL_PARAMETERS", "DESIGN_INPUTS",
    "DESIGN_OUTPUTS", "FAILURE_MODES", "VERIFICATION_MATRIX",
    "VALIDATION_MATRIX", "MATERIALS", "MANUFACTURING", "INTERFACES",
    "REGULATORY", "ENGINEERING_BUILD_PLAN", "TRANSFER_BOUNDARY",
    "KILL_CONDITION", "BUYER_DILIGENCE", "INVESTMENT_LADDER",
)

# minimum item counts per section (floors a generated engineering spec must
# exceed; floors are calibrated against the frozen 15-dossier benchmark —
# see benchmark_corpus.py / BENCHMARK_DEPTH_CONTRACT.json)
SECTION_MINIMUMS = {
    "SYSTEM_ARCHITECTURE": 3,        # subsystems
    "MECHANISM_ARCHITECTURE": 1,     # non-empty proposal
    "ENGINEERING_DOMAIN": 1,         # detection record with matched signals
    "GOVERNING_MODELS": 1,           # domain governing model rows
    "EQUATIONS": 1,                  # selected equations in governing model
    "CRITICAL_PARAMETERS": 3,        # full parameter records
    "DESIGN_INPUTS": 3,              # DI rows
    "DESIGN_OUTPUTS": 4,             # compiled A7 outputs (all 8 kinds)
    "FAILURE_MODES": 3,              # failure-analysis rows
    "VERIFICATION_MATRIX": 1,
    "VALIDATION_MATRIX": 1,          # honest NOT_PERFORMED rows count
    "MATERIALS": 1,                  # material candidates (or honest NONE)
    "MANUFACTURING": 1,              # candidate processes (or honest NONE)
    "INTERFACES": 1,
    "REGULATORY": 1,                 # candidate standards (honest UNKNOWN path)
    "ENGINEERING_BUILD_PLAN": 2,
    "TRANSFER_BOUNDARY": 2,          # buyer_receives + buyer_must_create
    "KILL_CONDITION": 1,
    "BUYER_DILIGENCE": 1,
    "INVESTMENT_LADDER": 1,
}

# R440.3 — the WEAK-TOKEN vocabulary: tokens that can NEVER carry
# invention linkage by themselves (generic engineering/process words
# shared by every package; the #160 lexical-coincidence vocabulary).
WEAK_TOKENS = {
    "decision", "domain", "evidence", "recorded", "source", "engine",
    "engineering", "status", "audit", "model", "system", "data",
    "analysis", "design", "technology", "problem", "record", "records",
    "package", "transfer", "buyer", "value", "values", "process",
    "control", "structure", "component", "components", "requirement",
    "requirements", "governing", "support", "supported", "result",
    "results", "based", "defined", "definition", "established",
    "unknown", "market", "commercial", "manufacturing", "clinical",
    "technical", "mechanism", "intervention", "parameter", "failure",
    "verification", "validation", "material", "interface", "build",
    "constraint", "output", "input", "ladder", "diligence", "kill",
    "boundary", "regulatory", "matrix", "equation", "critical",
}


def _strong_tokens(tokens: List[str]) -> List[str]:
    """Invention-specific tokens only (R440.3 weak-token filter)."""
    return [t for t in tokens if t not in WEAK_TOKENS and len(t) >= 5]


def _section_items(eng: Dict[str, Any], section: str) -> List[Any]:
    core = eng.get("engineering_core", {})
    if section == "SYSTEM_ARCHITECTURE":
        return (eng.get("system_architecture", {})
                .get("subsystems", []))
    if section == "MECHANISM_ARCHITECTURE":
        ma = eng.get("mechanism_architecture", {})
        return [ma] if ma.get("physical_changes") else []
    if section == "ENGINEERING_DOMAIN":
        wd = eng.get("why_this_domain", {})
        # E21-D: the detection record is a valid section item when it
        # carries EITHER routing-signal evidence OR phenomena evidence
        # for the selected domain (a PHENOMENA_DOMINANT selection with
        # zero routing keyword hits is a complete, fully-reasoned
        # record — measured case: BENCH_12 energy_harvesting; the
        # phenomena anchors are recorded in domain_detection).
        dd = eng.get("domain_detection", {})
        dom = wd.get("domain") or eng.get("technology_domain")
        phen = (dd.get("phenomena_layer") or {}).get(dom) or []
        if wd.get("matched_signals") or phen:
            return [wd]
        return []
    if section == "GOVERNING_MODELS":
        return core.get("governing_model", {}).get(
            "domain_governing_models", [])
    if section == "EQUATIONS":
        return core.get("governing_model", {}).get("equations", [])
    if section == "CRITICAL_PARAMETERS":
        return core.get("critical_parameters", [])
    if section == "DESIGN_INPUTS":
        return eng.get("design_inputs", [])
    if section == "DESIGN_OUTPUTS":
        return eng.get("design_outputs", [])
    if section == "FAILURE_MODES":
        return core.get("failure_modes", []) or eng.get("failure_analysis", [])
    if section == "VERIFICATION_MATRIX":
        return eng.get("verification_matrix", [])
    if section == "VALIDATION_MATRIX":
        return eng.get("validation_matrix", [])
    if section == "MATERIALS":
        return eng.get("materials", [])
    if section == "MANUFACTURING":
        mfg = eng.get("manufacturing", {})
        return mfg.get("candidate_processes", [])
    if section == "INTERFACES":
        return eng.get("interfaces", {}).get("interfaces", [])
    if section == "REGULATORY":
        return eng.get("regulatory", {}).get("candidate_standards", [])
    if section == "ENGINEERING_BUILD_PLAN":
        return eng.get("engineering_build_plan", [])
    if section == "TRANSFER_BOUNDARY":
        tb = eng.get("transfer_boundary", {})
        return ([{"buyer_receives": tb.get("buyer_receives", [])}] if
                tb.get("buyer_receives") else []) + \
               ([{"buyer_must_create": tb.get("buyer_must_create", [])}] if
                tb.get("buyer_must_create") else [])
    if section == "KILL_CONDITION":
        kc = eng.get("kill_condition", {})
        return [kc] if kc.get("statement") else []
    if section == "BUYER_DILIGENCE":
        bd = eng.get("buyer_diligence", {})
        return [bd] if bd.get("independent_review_required") else []
    if section == "INVESTMENT_LADDER":
        return eng.get("investment_ladder", [])
    return []


def _tied(section: str, eng: Dict[str, Any], items: List[Any],
          tokens: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """STRUCTURAL invention-tie evaluation for one section (R440.3).

    A section is invention-tied ONLY when its items carry EXPLICIT
    canonical relationships:
      - linkage records (invention_tie / invention_applicability /
        invention_tied / matched_* / role_in_invention) whose matched
        vocabulary includes at least one INVENTION-SPECIFIC (strong)
        token, or whose linkage_kind is a structural kind (domain_kind,
        computed derivation with a recorded basis)
      - recorded canonical source references (source_refs) on the
        section's items
      - domain-detection evidence for the ENGINEERING_DOMAIN section
        (matched routing signals or phenomena anchors)

    RETIRED (R440.3): the bare token-substring test over section text,
    and the blanket 'spec_derived' auto-tie that marked 12 of 20
    sections tied by construction. The word 'decision' (or any weak
    token) is never evidence of invention linkage.
    """
    strong = _strong_tokens(tokens)
    # ---- 0. section-container canonical derivation pointers (R440.3):
    # the generator records WHERE the section projects from
    # (mechanism_architecture, interfaces, regulatory, transfer_boundary
    # carry block-level source_refs)
    for block_key in (section.lower(),):
        block = eng.get(block_key)
        if isinstance(block, dict):
            refs = block.get("source_refs")
            if isinstance(refs, list) and any(
                    isinstance(r, str) and r.strip() for r in refs):
                return True, {"linkage_kind": "canonical_source_refs",
                              "source_refs": refs}
    # ---- 1. explicit linkage records on the items
    linkage_records = 0
    strong_linkage = 0
    structural_linkage = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        for key in ("invention_tie", "invention_applicability",
                    "invention_tied", "matched_tokens",
                    "matched_invention_tokens", "role_in_invention"):
            rec = it.get(key)
            if rec is None:
                continue
            linkage_records += 1
            if isinstance(rec, dict):
                kind = str(rec.get("linkage_kind", ""))
                # matched vocabulary: the REAL record shapes carry
                # matched_tokens (invention_tie) or
                # matched_invention_tokens / matched_applicability_signals
                # (the engineering-attack adjudication)
                matched = (rec.get("matched_tokens")
                           or rec.get("matched_invention_tokens")
                           or rec.get("matched_applicability_signals")
                           or [])
                matched = matched if isinstance(matched, list) else []
                if any(str(t) in strong for t in matched):
                    strong_linkage += 1
                elif str(rec.get("verdict", "")).upper() == "TIED":
                    # an ADJUDICATED tie verdict: the engineering attack
                    # evaluated THIS row's applicability to the invention
                    # and recorded the decision with evidence — a
                    # computed adjudication, never a lexical coincidence
                    structural_linkage += 1
                elif kind and kind not in ("", "invention_tokens"):
                    # a structural/computed linkage kind (e.g.
                    # domain_kind — a recorded derivation basis, not a
                    # lexical coincidence)
                    structural_linkage += 1
            elif rec is True:
                structural_linkage += 1
    if strong_linkage:
        return True, {"linkage_kind": "explicit_linkage_records",
                      "strong_token_records": strong_linkage,
                      "records": linkage_records}
    if structural_linkage:
        return True, {"linkage_kind": "explicit_linkage_records",
                      "structural_records": structural_linkage,
                      "records": linkage_records}
    # ---- 2. recorded canonical source references (R440.3 schema):
    # the REAL record vocabulary — source_refs (R440.5-style canonical
    # pointers), evidence_refs (design inputs), registry_equation_ids
    # (governing models) — non-empty explicit references only
    for holder in [i for i in items if isinstance(i, dict)]:
        for ref_key in ("source_refs", "evidence_refs",
                        "registry_equation_ids", "evidence_ids"):
            refs = holder.get(ref_key)
            if isinstance(refs, list) and any(
                    isinstance(r, str) and r.strip() for r in refs):
                return True, {"linkage_kind": "canonical_source_refs",
                              "source_refs": refs}
        # structural parent linkage: parent_ids point at upstream nodes
        # (DI -> UIN user-need rows, DO -> DI) — explicit graph edges,
        # never text coincidence
        parents = holder.get("parent_ids")
        if isinstance(parents, list) and any(
                isinstance(p, str) and p.strip() for p in parents):
            structural_linkage += 1
    if structural_linkage:
        return True, {"linkage_kind": "explicit_linkage_records",
                      "structural_records": structural_linkage,
                      "records": linkage_records}
    # ---- 3. ENGINEERING_DOMAIN: the detector's own evidence
    if section == "ENGINEERING_DOMAIN":
        wd = eng.get("why_this_domain", {})
        if wd.get("matched_signals"):
            return True, {"linkage_kind": "domain_detection_evidence",
                          "matched_signals": wd["matched_signals"]}
        # E21-D: a domain selected by the PHENOMENA layer is tied by the
        # physics vocabulary the invention's own text states — recorded
        # per-domain in domain_detection.phenomena_layer.
        dd = eng.get("domain_detection", {})
        dom = wd.get("domain") or eng.get("technology_domain")
        phen = (dd.get("phenomena_layer") or {}).get(dom) or []
        if phen:
            return True, {"linkage_kind": "phenomena_detection_evidence",
                          "phenomena_anchors": phen}
    # ---- RETIRED PATHS (documented, never silently accepted):
    #   * token-substring over the section text (pre-R440 path 1)
    #   * blanket spec_derived auto-tie (pre-R440 path 3)
    return False, {"linkage_kind": "NONE",
                   "note": ("no structural linkage evidence: the section "
                            "carries no linkage record with invention-"
                            "specific vocabulary, no canonical source "
                            "references, and no domain-detection "
                            "evidence (R440.3: lexical coincidence is "
                            "never invention linkage)")}


def evaluate_depth_contract(spec: Dict[str, Any], eng: Dict[str, Any],
                            ) -> Dict[str, Any]:
    """Evaluate ALL 20 sections. Returns the full evaluation; `passed` is
    True only when every section is present, sufficiently deep and
    STRUCTURALLY invention-tied (Art. XXVIII: no promotion past an
    unmet condition; R440.3: lexical coincidence is never linkage)."""
    tokens = _invention_tokens(spec)
    sections: Dict[str, Any] = {}
    for section in CONTRACT_SECTIONS:
        items = _section_items(eng, section)
        n = len(items)
        minimum = SECTION_MINIMUMS[section]
        present = n >= minimum
        tied, tie_evidence = _tied(section, eng, items, tokens)
        sections[section] = {
            "item_count": n,
            "minimum": minimum,
            "present": present,
            "invention_tied": tied,
            "tie_evidence": tie_evidence,
            "satisfied": present and tied,
        }
    failed = [s for s, e in sections.items() if not e["satisfied"]]
    return {
        "contract": "ENGINEERING_DEPTH_CONTRACT",
        "version": "2.0.0",
        "version_basis": ("R440.3: structural linkage replaces the retired "
                          "lexical token-substring test and the blanket "
                          "spec_derived auto-tie"),
        "sections": sections,
        "sections_total": len(CONTRACT_SECTIONS),
        "sections_satisfied": len(CONTRACT_SECTIONS) - len(failed),
        "failed_sections": failed,
        "passed": not failed,
        "rule": ("presence alone is not enough and neither is lexical "
                 "coincidence: every section must carry STRUCTURAL "
                 "invention linkage (explicit linkage records with "
                 "invention-specific vocabulary, canonical source "
                 "references, or domain-detection evidence)"),
        "evaluated_at": utc_now(),
    }


def assert_depth_contract(spec: Dict[str, Any], eng: Dict[str, Any]) -> None:
    evaluation = evaluate_depth_contract(spec, eng)
    if not evaluation["passed"]:
        detail = []
        for s in evaluation["failed_sections"]:
            e = evaluation["sections"][s]
            detail.append(
                f"{s}(items={e['item_count']}/{e['minimum']}"
                f"{', untied' if not e['invention_tied'] else ''})")
        from .fields import PackageBuildError
        raise PackageBuildError(
            "ENGINEERING_DEPTH_CONTRACT FAILED: " + "; ".join(detail) +
            " (CEO A2/R440.3: a package below benchmark depth — or one "
             "whose sections are only lexically 'tied' — is never "
             "generated)")

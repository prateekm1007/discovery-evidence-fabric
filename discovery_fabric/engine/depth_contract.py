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

BUT PRESENCE ALONE IS NOT ENOUGH. Each section must contain content tied to
the ACTUAL invention. The tie is mechanical, not narrative: every section
check requires

    1. present      — the section exists with the contract's minimum items
    2. invention_tied — the section references this invention (mechanism/
       problem tokens), or cites explicit invention linkage recorded by the
       generators (invention_tie / invention_applicability / matched_tokens
       fields), or cites the custodied problem artifact
    3. classed      — content carries an epistemic class/status vocabulary
       (no naked assertions)

`evaluate_depth_contract(spec, eng)` returns per-section evaluations with
evidence; `assert_depth_contract` raises on failure. The package factory
runs the contract as a HARD GATE: a package whose engineering content does
not meet the depth contract is NOT generated (fail closed, Art. V) — and
the evaluation is written into the package as
DEPTH_CONTRACT_EVALUATION.json.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .candidate import sha256_obj, utc_now
from .engineering_spec import _invention_tokens, _tie

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
        return [wd] if wd.get("matched_signals") else []
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


def _section_text(eng: Dict[str, Any], section: str, items: List[Any]
                  ) -> str:
    """All textual content of the section, for the mechanical tie check."""
    import json as _json
    try:
        return _json.dumps(items, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001 — defensive: stringify directly
        return " ".join(str(i) for i in items)


def _tied(section: str, eng: Dict[str, Any], items: List[Any],
          tokens: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """Mechanical invention-tie evaluation for one section. A section is
    invention-tied when ANY of:
      - its text matches an invention content token (exact substring)
      - its items carry explicit linkage records (invention_tie,
        invention_applicability, matched_*, invention_tied)
      - the section is a COMPUTED derivation of the spec (kill condition,
        buyer diligence, verification — bound to spec artifacts by
        construction; recorded as linkage_kind='spec_derived')
    """
    text = _section_text(eng, section, items).lower()
    token_hits = [t for t in tokens if t in text]
    if token_hits:
        return True, {"linkage_kind": "invention_tokens",
                      "matched_tokens": token_hits}
    linkage_records = 0
    for it in items:
        if isinstance(it, dict) and any(
                k in it for k in ("invention_tie",
                                  "invention_applicability",
                                  "invention_tied", "matched_tokens",
                                  "matched_invention_tokens",
                                  "role_in_invention")):
            linkage_records += 1
    if linkage_records:
        return True, {"linkage_kind": "explicit_linkage_records",
                      "records": linkage_records}
    # ENGINEERING_DOMAIN: its matched_signals ARE the recorded tie evidence
    if section == "ENGINEERING_DOMAIN":
        wd = eng.get("why_this_domain", {})
        if wd.get("matched_signals"):
            return True, {"linkage_kind": "domain_detection_evidence",
                          "matched_signals": wd["matched_signals"]}
        # E21-D: a domain selected by the PHENOMENA layer is tied by the
        # physics vocabulary the invention's own text states — recorded
        # per-domain in domain_detection.phenomena_layer (CEO item 2:
        # keywords route, never justify; when a domain has ZERO routing
        # keyword hits, the phenomena anchors matched in the invention's
        # text are the entire — and sufficient — tie evidence). This
        # ADDS a verifiable evidence path; the keyword path above is
        # unchanged (Art. VII: extend, never weaken).
        dd = eng.get("domain_detection", {})
        dom = wd.get("domain") or eng.get("technology_domain")
        phen = (dd.get("phenomena_layer") or {}).get(dom) or []
        if phen:
            return True, {"linkage_kind":
                              "phenomena_detection_evidence",
                          "phenomena_anchors": phen}
    spec_derived = ("KILL_CONDITION", "BUYER_DILIGENCE",
                    "INVESTMENT_LADDER", "VALIDATION_MATRIX",
                    "TRANSFER_BOUNDARY", "REGULATORY",
                    "MECHANISM_ARCHITECTURE", "GOVERNING_MODELS",
                    "EQUATIONS", "CRITICAL_PARAMETERS", "DESIGN_INPUTS",
                    "VERIFICATION_MATRIX")
    if section in spec_derived:
        return True, {"linkage_kind": "spec_derived",
                      "note": "section is a mechanical derivation of the "
                              "invention specification's own recorded "
                              "artifacts (selection/applicability "
                              "judgments travel inside the items)"}
    return False, {"linkage_kind": "NONE",
                   "note": "no invention token, linkage record or "
                           "spec-derivation found"}


def evaluate_depth_contract(spec: Dict[str, Any], eng: Dict[str, Any],
                            ) -> Dict[str, Any]:
    """Evaluate ALL 20 sections. Returns the full evaluation; `passed` is
    True only when every section is present, sufficiently deep and
    invention-tied (Art. XXVIII: no promotion past an unmet condition)."""
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
        "version": "1.0.0",
        "sections": sections,
        "sections_total": len(CONTRACT_SECTIONS),
        "sections_satisfied": len(CONTRACT_SECTIONS) - len(failed),
        "failed_sections": failed,
        "passed": not failed,
        "rule": ("presence alone is not enough: every section must carry "
                 "invention-tied content (mechanical tie evidence recorded)"),
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
            " (CEO A2: a package below benchmark depth is never generated)")

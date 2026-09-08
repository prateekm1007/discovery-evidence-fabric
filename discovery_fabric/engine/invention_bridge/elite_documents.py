"""discovery_fabric/engine/invention_bridge/elite_documents.py — R424.

The six elite buyer documents (00-05), rendered as deterministic PDFs
from the SAME canonical projection as the machine-readable layers.
Content discipline: every section is derived from the run record;
UNKNOWN stays UNKNOWN; no patent language; no invented numbers.

  00_PACKAGE_README               plain-language orientation
  01_EXECUTIVE_TECHNOLOGY_BRIEF   one-page executive summary
  02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER   the technical core
  03_BUYER_DECISION_CARD          the nine-question decision architecture
  04_EVIDENCE_SUMMARY             evidence structured by role
  05_TRANSFER_MANIFEST            what transfers and what it takes
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from . import epistemics as ep


def _txt(v: Any, limit: int = 900) -> str:
    """Deterministic plain text from any canonical field."""
    if v is None:
        return "UNKNOWN (not recorded)"
    if isinstance(v, str):
        return v if len(v) <= limit else v[:limit] + "…"
    try:
        s = json.dumps(v, indent=1, default=str, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        s = str(v)
    return s if len(s) <= limit else s[:limit] + "…"


def _sec(title: str, body: str) -> Dict:
    return {"title": title, "body": body}


def build_readme(proj: Dict, run_result: Dict, package_id: str,
                 maturity: str, is_engineering: bool,
                 geometry_class: str) -> Dict:
    """00 — plain language: what this is, what it is not, what a buyer
    receives, the decisive next action (R424 §3). NO patent claims."""
    inv = run_result.get("invention_specification") or {}
    fs = run_result.get("final_state") or {}
    mechanism = _txt(proj.get("mechanism"), 400)
    sections = [
        _sec("What this technology is",
             f"A recorded invention candidate for the problem: "
             f"“{_txt(run_result.get('user_text') or run_result.get('title'), 300)}”. "
             f"The proposed causal mechanism: {mechanism}"),
        _sec("The problem addressed",
             f"{_txt(_u(inv.get('problem')), 500)}"),
        _sec("Why the problem matters",
             f"{_txt(_u(inv.get('user_need')), 400)}"),
        _sec("Invention summary",
             f"Intervention: {_txt(_u(inv.get('mechanism')), 300)} "
             f"applied at the recorded intervention site. "
             f"Status: {_txt(fs.get('final_status'))}."),
        _sec("Current maturity",
             f"{maturity} — {ep.PACKAGE_MATURITY_MEANINGS.get(maturity, '')}"),
        _sec("What is actually demonstrated",
             "The architecture survived the recorded adversarial "
             "challenge, adjudication, and evolution stages; the "
             "evidence roles are itemized in 04. "
             + ("The parametric engineering model exists with "
                "measured geometry and validation gates "
                "(ENGINEERING_3D)." if is_engineering else
                "The 3D representation is a conceptual architecture "
                f"({geometry_class}) — engineering CAD is unearned.")),
        _sec("What is NOT demonstrated",
             "Nothing in this package was measured in reality; no "
             "physical experiment has been run (validation status "
             "NOT_POSSIBLE_YET throughout, Art. XXXVIII). "
             "EXPERIMENTALLY VERIFIED is not claimed anywhere."),
        _sec("What a buyer receives",
             "This package: the technical essay and engineering "
             "dossier, the buyer decision card, the evidence summary "
             "with roles, the transfer manifest, the machine-readable "
             "engineering layers (traceability, equations, unknown "
             "roadmap, validation economics), and the 3D artifacts "
             "this invention earned."),
        _sec("Decisive next action",
             _decisive_action(proj)),
    ]
    return {
        "section_order": [s["title"] for s in sections],
        "titles": {s["title"]: s["title"] for s in sections},
        "sections": {s["title"]: s["body"] for s in sections},
    }


def _u(field: Any) -> Any:
    if isinstance(field, dict) and "value" in field and set(
            field.keys()) <= {"value", "epistemic_class", "origin_stage",
                              "evidence_ids", "note", "source_span",
                              "provenance"}:
        return field.get("value")
    return field


def _decisive_action(proj: Dict) -> str:
    ke = proj.get("killer_experiment") or {}
    if ke.get("selected") or ke.get("definition"):
        return (f"Fund and run the recorded decisive experiment "
                f"({_txt(ke.get('definition'), 200)}) — the "
                f"pre-registered rule either kills the architecture or "
                f"graduates it to a sourced measurement.")
    return ("Commission the engineering design work in the unknown "
            "roadmap (05 layers) — the recorded blockers say exactly "
            "which values must be sourced before any numeric design "
            "decision or decisive experiment is possible.")


def build_executive_brief(proj: Dict, run_result: Dict,
                          maturity: str) -> Dict:
    """01 — the one-page executive summary (10 items, R424 §3)."""
    inv = run_result.get("invention_specification") or {}
    fs = run_result.get("final_state") or {}
    counts = fs.get("evidence_classification_counts") or {}
    sections = [
        _sec("Technology",
             _txt(run_result.get("title") or
                  _u(inv.get("invention_id")), 200)),
        _sec("Bottleneck",
             _txt(_u(inv.get("problem")), 300)),
        _sec("Causal mechanism",
             _txt(_u(inv.get("mechanism")), 300)),
        _sec("Differentiating architecture",
             _txt(_u(inv.get("novelty_hypothesis"))
                  or _u(inv.get("distinguishing_features")), 300)),
        _sec("Expected technical advantage",
             _txt(_u(inv.get("mechanism")) and
                  _txt(_u((inv.get("causal_chain") or {}).get(
                      "expected_effect")) if isinstance(
                      inv.get("causal_chain"), dict) else None, 300)
                  or "expected effect as recorded in the invention "
                     "specification", 300)),
        _sec("Strongest supporting evidence",
             f"Evidence classification counts from the run's own "
             f"verification: {json.dumps(counts)}; direct-support "
             f"spans are itemized in 04_EVIDENCE_SUMMARY."),
        _sec("Biggest uncertainty",
             _txt((proj.get("remaining_unknowns") or [{}])[0].get(
                 "unknown") if proj.get("remaining_unknowns") else None,
                 300) or "recorded in the unknown roadmap"),
        _sec("Engineering status",
             f"{maturity}; "
             f"{len(proj.get('design_inputs') or [])} design inputs, "
             f"{len(proj.get('failure_modes') or [])} failure modes, "
             f"{len(proj.get('equations') or [])} governing equations "
             f"recorded"),
        _sec("Decisive experiment",
             _txt((proj.get("killer_experiment") or {}).get("definition")
                  or "not selected — see the unknown roadmap", 200)),
        _sec("Buyer decision",
             "evaluate this package against the nine questions in "
             "03_BUYER_DECISION_CARD; the cheapest falsification is "
             "named there with its acceptance rule"),
    ]
    return _essayish(sections)


def _essayish(sections: List[Dict]) -> Dict:
    return {
        "section_order": [s["title"] for s in sections],
        "titles": {s["title"]: s["title"] for s in sections},
        "sections": {s["title"]: s["body"] for s in sections},
    }


def build_dossier(proj: Dict, run_result: Dict, essay: Dict,
                  maturity: str, geometry_out: Optional[Dict],
                  is_engineering: bool) -> Dict:
    """02 — the technical core (R424 §3: 18 items, generated from
    canonical run state; no invented values). The recorded essay's
    sections (why it could work / what is different / evidence /
    unknowns / kill conditions) are woven in verbatim — one canonical
    source."""
    inv = run_result.get("invention_specification") or {}
    essay_secs = essay.get("sections") or {}

    def es(name: str) -> str:
        return _txt(essay_secs.get(name), 700)

    sections = [
        _sec("Problem definition",
             _txt(_u(inv.get("problem")), 500)),
        _sec("Failure mode being addressed",
             _failure_summary(proj)),
        _sec("Mechanism", es("what_toscanini_invented")),
        _sec("Causal delta", es("what_is_genuinely_different")),
        _sec("Architecture",
             _subsystem_table(proj)),
        _sec("Subsystem breakdown", _subsystem_table(proj, full=True)),
        _sec("Governing equations", _equation_summary(proj)),
        _sec("Parameter definitions", _parameter_summary(proj)),
        _sec("Constraints", _constraints_summary(proj)),
        _sec("Engineering assumptions", _assumptions_summary(proj)),
        _sec("Failure modes", _failure_modes_table(proj)),
        _sec("Verification plan", _verification_table(proj)),
        _sec("Build / manufacturing pathway", _build_plan_table(proj)),
        _sec("Decisive experiment",
             _txt(_u(inv.get("killer_experiment"))
                  or proj.get("killer_experiment"), 500)),
        _sec("Expected measurements",
             _expected_measurements(proj)),
        _sec("Acceptance criteria", _acceptance_summary(proj)),
        _sec("Unresolved technical risks", es("what_remains_unknown")),
        _sec("3D explanation", _3d_explanation(
            geometry_out, is_engineering)),
        _sec("Artifact references",
             "every layer of this package is named in "
             "PACKAGE_MANIFEST.json with per-file sha256; the "
             "machine-readable layers are ENGINEERING_TRACEABILITY, "
             "EQUATION_REGISTRY, UNKNOWN_ROADMAP, "
             "VALIDATION_ECONOMICS, MATURITY_BASIS, LOOP_STATE, "
             "PROVENANCE (top level) and the MODEL/ tree"),
    ]
    return _essayish(sections)


def _failure_summary(proj: Dict) -> str:
    fms = proj.get("failure_modes") or []
    if not fms:
        return "UNKNOWN (no failure analysis recorded)"
    first = fms[0]
    return (f"{len(fms)} failure modes recorded. Primary: "
            f"{_txt(first.get('failure_mode') or first.get('mode'), 200)} "
            f"— trigger: {_txt(first.get('trigger'), 250)}")


def _subsystem_table(proj: Dict, full: bool = False) -> str:
    subs = proj.get("subsystems") or []
    if not subs:
        return "UNKNOWN (no subsystem architecture recorded)"
    lines = []
    for s in subs[:10 if full else 6]:
        if isinstance(s, dict):
            lines.append(f"• {s.get('name')} — status "
                         f"{s.get('status', 'UNKNOWN')}"
                         + (f": {_txt(s.get('detail'), 160)}" if full
                            else ""))
    return "\n".join(lines)


def _equation_summary(proj: Dict) -> str:
    eqs = proj.get("equations") or []
    if not eqs:
        return ("NOT_APPLICABLE — the record carries no governing "
                "equations; none are fabricated (see "
                "EQUATION_REGISTRY.json)")
    lines = []
    for e in eqs[:8]:
        lines.append(f"• {e.get('equation_id')}: "
                     f"{_txt(e.get('expression'), 160)} — "
                     f"{_txt(e.get('name'), 120)}")
    return "\n".join(lines) + (
        f"\n({len(eqs)} total; full bindings in EQUATION_REGISTRY.json)")


def _parameter_summary(proj: Dict) -> str:
    cps = proj.get("critical_parameters") or []
    if not cps:
        return ("UNKNOWN — no engineering parameters are recorded; "
                "physical geometry/materials/setpoints are "
                "ENGINEERING_PROPOSED at best and are never invented")
    lines = []
    for p in cps[:10]:
        lines.append(
            f"• {p.get('parameter_id')} {p.get('name')} "
            f"[{p.get('symbol')} {p.get('unit') or ''}] = "
            f"{_txt(p.get('value'), 80)} ({p.get('value_status')})")
    return "\n".join(lines)


def _constraints_summary(proj: Dict) -> str:
    c = proj.get("constraints")
    if not c:
        return ("UNKNOWN (no constraints recorded beyond the problem "
                "statement)")
    if isinstance(c, list):
        return "\n".join(f"• {_txt(x, 200)}" for x in c[:8])
    return _txt(c, 500)


def _assumptions_summary(proj: Dict) -> str:
    a = proj.get("assumptions")
    if not a:
        return "none recorded"
    if isinstance(a, list):
        return "\n".join(f"• {_txt(x, 200)}" for x in a[:8])
    return _txt(a, 400)


def _failure_modes_table(proj: Dict) -> str:
    fms = proj.get("failure_modes") or []
    lines = []
    for f in fms[:10]:
        if isinstance(f, dict):
            lines.append(
                f"• {f.get('graph_id') or f.get('id')}: "
                f"{_txt(f.get('failure_mode') or f.get('mode'), 120)} "
                f"— severity {_txt(f.get('severity'), 80)}")
    return "\n".join(lines) or "UNKNOWN (none recorded)"


def _verification_table(proj: Dict) -> str:
    vfs = proj.get("verification") or []
    lines = []
    for v in vfs[:10]:
        if isinstance(v, dict):
            lines.append(f"• {v.get('id')}: result "
                         f"{v.get('result', 'UNKNOWN')} — "
                         f"{_txt(v.get('requirement'), 200)}")
    return "\n".join(lines) or "UNKNOWN (no verification items recorded)"


def _build_plan_table(proj: Dict) -> str:
    wps = proj.get("build_plan") or []
    lines = []
    for w in wps[:10]:
        if isinstance(w, dict):
            lines.append(f"• {w.get('work_package')}: test article "
                         f"{_txt(w.get('test_article'), 120)}; "
                         f"measurement {_txt(w.get('measurement'), 120)}")
    return "\n".join(lines) or "UNKNOWN (no build plan recorded)"


def _expected_measurements(proj: Dict) -> str:
    vfs = proj.get("verification") or []
    meas = [v.get("method") for v in vfs if v.get("method")]
    if meas:
        return ("\n".join(f"• {_txt(m, 160)}" for m in meas[:6])
                + "\n(all NOT_TESTED — expected values are UNKNOWN "
                  "until the experiment runs)")
    return ("UNKNOWN — expected measurements exist only after the "
            "decisive experiment runs; no values are invented here")


def _acceptance_summary(proj: Dict) -> str:
    for v in proj.get("verification") or []:
        if v.get("acceptance"):
            return (f"Pre-registered rule (from {v.get('id')}): "
                    f"{_txt(v.get('acceptance'), 300)}")
    return ("UNKNOWN — no sourced threshold exists yet; the "
            "acceptance rule must be fixed BEFORE the decisive "
            "experiment runs (pre-registration discipline)")


def _3d_explanation(geometry_out: Optional[Dict],
                    is_engineering: bool) -> str:
    if not geometry_out:
        return ("3D_NOT_APPLICABLE — the classifier recorded no honest "
                "visual representation (see 3D_DESIGN_STATUS)")
    if is_engineering:
        return ("The parametric engineering model (CadQuery/OCCT "
                "authority) with STEP/STL exports, measured key "
                "dimensions and validation gates; the derivation chain "
                "is in MODEL/ENGINEERING_PROVENANCE.json and the "
                "independent checks in MODEL/3D_EVIDENCE/. Renders are "
                "presentation artifacts — never physical truth.")
    return ("A conceptual architecture visualization "
            f"({geometry_out.get('visualizability_class')}) — topology "
            "and named components only, NO engineering dimensions; "
            "engineering CAD is earned only when parameters are "
            "sourced (labeled in 3D_DESIGN_STATUS.json)")


def build_decision_card(proj: Dict, run_result: Dict,
                        maturity: str) -> Dict:
    """03 — the elite nine-question decision architecture (R424 §3)."""
    inv = run_result.get("invention_specification") or {}
    fs = run_result.get("final_state") or {}
    ke = proj.get("killer_experiment") or {}
    q = [
        ("What problem?", _txt(_u(inv.get("problem")), 300)),
        ("Why does it matter?", _txt(_u(inv.get("user_need")), 300)),
        ("What is different?",
         _txt(_u(inv.get("novelty_hypothesis"))
              or _u(inv.get("distinguishing_features")), 300)),
        ("How does it work?", _txt(_u(inv.get("mechanism")), 300)),
        ("What evidence exists?",
         f"classification counts {json.dumps(fs.get('evidence_classification_counts') or {})}; "
         f"prior-art status {fs.get('prior_art_status')}; roles "
         "itemized in 04"),
        ("What remains unknown?",
         f"{len(proj.get('remaining_unknowns') or [])} recorded "
         f"unknowns — each with a resolution action in "
         f"UNKNOWN_ROADMAP.json"),
        ("What would we build?",
         _build_plan_table(proj)),
        ("What experiment would decide?",
         _txt(ke.get("definition") or "not selected — see the unknown "
              "roadmap for the blockers", 300)),
        ("What should we do next?", _decisive_action(proj)),
    ]
    sections = [_sec(t, b) for t, b in q]
    return _essayish(sections)


def build_evidence_summary(proj: Dict, run_result: Dict) -> Dict:
    """04 — evidence structured by role with exact provenance
    (R424 §3: direct support, partial support, background, analogy,
    contradiction, unavailable sources, coverage limitations)."""
    fs = run_result.get("final_state") or {}
    counts = fs.get("evidence_classification_counts") or {}
    ep_ = run_result.get("evidence_pack") or {}
    retrieval = ep_.get("retrieval") or []
    roles = [
        ("Direct support", counts.get("DIRECT_SUPPORT", 0),
         "spans that state the claimed proposition"),
        ("Partial support", counts.get("PARTIAL_SUPPORT", 0),
         "spans that support part of the claim"),
        ("Background", counts.get("BACKGROUND", 0),
         "contextual, not claim-bearing"),
        ("Analogy", counts.get("ANALOGY", 0),
         "adjacent-domain transfer, weaker class"),
        ("Contradiction", counts.get("CONTRADICTORY", 0),
         "spans that contradict the claim"),
        ("Unavailable sources",
         sum(1 for r in retrieval
             if isinstance(r, dict) and r.get("error")),
         "retrieval failures — absence is never evidence (Art. XXI.3)"),
    ]
    lines = [f"• {name}: {count} — {desc}" for name, count, desc in
             roles]
    unresolved = [r for r in retrieval
                  if isinstance(r, dict) and r.get("error")]
    for r in unresolved[:5]:
        lines.append(f"  – unresolved source: {_txt(r.get('source') or r.get('query'), 80)} "
                     f"({_txt(r.get('error'), 80)})")
    cov = (f"coverage limitations: {len(unresolved)} retrieval "
           f"failure(s) recorded; unknown records stay UNKNOWN "
           f"(Art. XXV)")
    sections = [
        _sec("Evidence by role", "\n".join(lines)),
        _sec("Provenance", "every classified span carries its evidence "
             "id and custody chain in the run record; the invention "
             "specification's _evidence_index maps claims to spans"),
        _sec("Coverage limitations", cov),
    ]
    return _essayish(sections)


def build_transfer_manifest(proj: Dict, run_result: Dict,
                            package_id: str, maturity: str,
                            is_engineering: bool,
                            geometry_class: str) -> Dict:
    """05 — what transfers, what it takes (R424 §3)."""
    sections = [
        _sec("What is transferable",
             "the recorded invention architecture with its evidence "
             "roles, the engineering projection (design inputs, "
             "failure modes, verification items, build plan, "
             "equations), the unknown roadmap, and the 3D artifacts "
             f"this class earned ({geometry_class})"),
        _sec("Artifact inventory",
             "every file with sha256 in PACKAGE_MANIFEST.json; the "
             "machine-readable layers listed in 00; MODEL/ carries the "
             "parametric source and derived CAD when "
             "ENGINEERING_3D is earned"),
        _sec("Engineering maturity",
             f"{maturity} — basis and counts in MATURITY_BASIS.json"),
        _sec("Buyer capability needed",
             "an engineering team able to take ENGINEERING_PROPOSED "
             "state to manufacturable definition (the design work "
             "named in the unknown roadmap) and to run the "
             "pre-registered decisive experiment"),
        _sec("Required tooling",
             "CAD (STEP readers; CadQuery/OCCT for parametric "
             "rebuilds — see MODEL/PARAMETRIC_MODEL_SOURCE.py), "
             "mesh inspection (any STL viewer; trimesh used for the "
             "independent watertight check), and the bench equipment "
             "named in the build plan"),
        _sec("Dependencies",
             "no external services; the package is self-contained "
             "with real hashes (verify after transfer against "
             "PACKAGE_MANIFEST.json)"),
        _sec("Confidentiality classification",
             "CONFIDENTIAL — technical evaluation draft for the "
             "recipient's engineering diligence only; not a release "
             "document, not legal advice"),
        _sec("Reproduction instructions",
             "rebuild the geometry from MODEL/PARAMETRIC_MODEL_SOURCE."
             "py + MODEL/PARAMETERS.json (the regeneration check "
             "records the expected measurements); verify every file "
             "against the manifest hashes"),
        _sec("Open technical work",
             f"{len(proj.get('remaining_unknowns') or [])} unknowns "
             "with resolution actions in UNKNOWN_ROADMAP.json — "
             "this is the recipient's first work queue"),
    ]
    return _essayish(sections)

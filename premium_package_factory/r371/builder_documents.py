"""
builder_documents.py — R371 V5 document renderers.

Each renderer takes the canonical package view + derived artifacts and
produces one buyer-facing PDF. All content derives from canonical data;
nothing is hand-authored.
"""

import os

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer

from .builder import (
    _doc, _esc, _footer_canvas, _img, _mut, _tbl, CONFIDENTIALITY,
    NOT_ESTABLISHED,
)
from .equations import render_equation_png

S = None  # styles, injected via init_styles


def init_styles(styles):
    global S
    S = styles


# ---------------------------------------------------------------------------
# 01 EXECUTIVE TECHNOLOGY BRIEF — one page, CEO hierarchy (Phase 4)
# ---------------------------------------------------------------------------
def render_exec_brief(pkg, hl, comm, eco, loopstate, out_path):
    ident = pkg.identity_line
    doc = _doc(out_path, ident, f"Executive Technology Brief — {pkg.pkg_id}")
    st = []
    st.append(Paragraph(_esc(f"{hl['technology_name']}"), S["CT"]))
    st.append(Paragraph(_esc(
        f"Package {pkg.pkg_id} · Portfolio {pkg.num} of 15 · Version {pkg.version} · "
        f"Maturity: ENGINEERING_DEFINITION · Posture: SPONSORED_VALIDATION · "
        f"Loop state: {pkg.loop_state}"), S["CS"]))
    st.append(Paragraph(_esc(pkg.domain), S["SM"]))
    st.append(Spacer(1, 6))

    st.append(Paragraph("WHAT IS IT?", S["QH"]))
    st.append(Paragraph(_esc(_mut(pkg, hl["mechanism"])), S["BT"]))

    st.append(Paragraph("WHY DOES IT MATTER?", S["QH"]))
    st.append(Paragraph(_esc(_mut(pkg, hl["problem"])), S["BT"]))

    st.append(Paragraph("WHAT IS ESTABLISHED?", S["QH"]))
    ec = loopstate["evidence_class_counts"]
    established_text = (
        f"Engineering definition exists: {len(pkg.equations)} governing equations, "
        f"{len(pkg.design_inputs)} design inputs, {len(pkg.design_outputs)} design outputs, "
        f"{len(pkg.failure_analysis)} analyzed failure modes, {len(pkg.build_plan)}-step build plan. "
        f"Evidence classes across {sum(ec.values())} traced claims: "
        f"{ec.get('SOURCE_FACT',0)} source-fact, {ec.get('EXTERNAL_PRECEDENT',0)} external-precedent, "
        f"{ec.get('COMPUTATIONAL_RESULT',0)} computational, {ec.get('UNKNOWN',0)} recorded-UNKNOWN. "
        f"Physical observations: {ec.get('PHYSICAL_OBSERVATION',0)}. No prototype exists.")
    st.append(Paragraph(_esc(established_text), S["BT"]))

    st.append(Paragraph("WHAT IS NOT ESTABLISHED?", S["QH"]))
    n_unk = len(pkg.unknowns)
    crit = [u for u in pkg.unknowns if "critical" in u.lower()][:2]
    comp_verdict = (comm["commercial_evidence"][1]["verdict"].lower()
                    if len(comm["commercial_evidence"]) > 1 else NOT_ESTABLISHED.lower())
    not_est_text = (
        f"{n_unk} recorded UNKNOWNs (none suppressed). "
        + ("Most critical: " + "; ".join(crit) + ". " if crit else "")
        + "Market size: NOT_ESTABLISHED. Competitive landscape: "
        + comp_verdict
        + ". Full resolution roadmap in the engineering dossier.")
    st.append(Paragraph(_esc(not_est_text), S["BT"]))

    st.append(Paragraph("WHAT DOES THE BUYER DO NEXT?", S["QH"]))
    wp1 = pkg.build_plan[0] if pkg.build_plan else {}
    t_first = eco["time_range"]["first_decisive_work_package"]
    st.append(Paragraph(_esc(
        f"Decisive experiment: {wp1.get('work_package','WP-01')} — "
        f"{wp1.get('test_article','')} ({wp1.get('measurement','')}). "
        f"Recorded effort: {wp1.get('estimated_effort','NOT_RECORDED')}. "
        f"Validation cost: NOT_ESTABLISHED (no quotation basis exists in the "
        f"engineering record — vendor quotations required). "
        f"Kill condition: {hl['kill_if']}"), S["BT"]))

    st.append(Paragraph(_esc(
        "This is an engineering-definition technology-transfer dossier. It is "
        "not a representation that the technology is physically validated, "
        "manufacturing-qualified, clinically validated, or regulatory-cleared. "
        "Full engineering detail: 02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf."),
        S["DIS"]))
    doc.build(st, onFirstPage=_footer_canvas(ident), onLaterPages=_footer_canvas(ident))
    return out_path


# ---------------------------------------------------------------------------
# 03 BUYER DECISION CARD — CEO's exact 9-question order (Phase 4)
# ---------------------------------------------------------------------------
def render_buyer_card(pkg, hl, comm, eco, loopstate, out_path):
    ident = pkg.identity_line
    doc = _doc(out_path, ident, f"Buyer Decision Card — {pkg.pkg_id}")
    st = [Paragraph("BUYER DECISION CARD", S["CT"]),
          Paragraph(_esc(f"{hl['technology_name']} — Package {pkg.pkg_id} "
                         f"(Portfolio {pkg.num} of 15, Version {pkg.version})"), S["CS"]),
          Spacer(1, 4)]

    rows = []
    wp1 = pkg.build_plan[0] if pkg.build_plan else {}
    tb = pkg.transfer_boundary or {}
    buyer_receives = "; ".join(tb.get("buyer_receives", [])[:5]) or "See transfer manifest"
    buyer_must = "; ".join(
        (tb.get("buyer_must_develop", []) or [])[:5]) or "See transfer manifest"
    profile = next((s for s in comm["commercial_evidence"]
                    if s["section"] == "BUYER_PROFILE"), {})
    caps = "; ".join(profile.get("required_capabilities", []))
    ec = loopstate["evidence_class_counts"]

    # ---- FIVE DECISION CRITICALS (CEO R372-5) --------------------------
    # The five things a buyer must see immediately. The nine-question
    # architecture below remains the full decision structure.
    crit_rows = [
        ["1. WHAT IS THE INVENTION?", _mut(pkg, hl["mechanism"])],
        ["2. WHAT IS ACTUALLY ESTABLISHED?",
         f"Engineering definition: {len(pkg.equations)} governing equations, "
         f"{len(pkg.design_inputs)} design inputs, {len(pkg.design_outputs)} "
         f"design outputs, {len(pkg.failure_analysis)} failure modes analyzed, "
         f"{len(pkg.build_plan)}-step build plan. "
         f"{ec.get('SOURCE_FACT',0)+ec.get('EXTERNAL_PRECEDENT',0)} "
         f"source-backed claims; {ec.get('PHYSICAL_OBSERVATION',0)} physical "
         f"observations (none — no prototype exists; all verification "
         f"NOT_TESTED)."],
        ["3. WHAT REMAINS UNCERTAIN?",
         f"{len(pkg.unknowns)} recorded UNKNOWNs with resolution roadmap "
         f"(resolution classes in the engineering dossier); market size, "
         f"competitive landscape, FTO and novelty NOT_ESTABLISHED."],
        ["4. CHEAPEST DECISIVE NEXT EXPERIMENT?",
         f"{wp1.get('work_package','WP-01')}: {wp1.get('test_article','')} — "
         f"{wp1.get('measurement','')}. Recorded effort: "
         f"{wp1.get('estimated_effort','NOT_RECORDED')}. Cost NOT_ESTABLISHED "
         f"(no quotation basis — vendor quotations required); this is the "
         f"first, lowest-cost-known step of the recorded build plan."],
        ["5. WHAT EVIDENCE WOULD CAUSE THE BUYER TO STOP?", hl["kill_if"]],
    ]
    st.append(Paragraph("THE FIVE DECISION CRITICALS", S["SH"]))
    st.append(_tbl([["Critical", "Answer"]] + crit_rows,
                   [1.6 * 72, 5.0 * 72], fontsize=7.4))
    st.append(Spacer(1, 6))

    qa = [
        ("1. WHAT IS IT?", _mut(pkg, hl["mechanism"])),
        ("2. WHY DOES IT MATTER?", _mut(pkg, hl["problem"])),
        ("3. WHAT IS ESTABLISHED?",
         f"Engineering definition with {len(pkg.equations)} governing equations, "
         f"{len(pkg.design_inputs)} design inputs, {len(pkg.failure_analysis)} failure "
         f"modes analyzed, {len(pkg.build_plan)}-step build plan; "
         f"{ec.get('SOURCE_FACT',0)+ec.get('EXTERNAL_PRECEDENT',0)} source-backed claims; "
         f"{ec.get('PHYSICAL_OBSERVATION',0)} physical observations (none — no prototype)."),
        ("4. WHAT IS NOT ESTABLISHED?",
         f"{len(pkg.unknowns)} recorded UNKNOWNs with resolution roadmap; "
         f"market size NOT_ESTABLISHED; physical validation not performed; "
         f"novelty determination and FTO NOT_ESTABLISHED."),
        ("5. WHY MIGHT A BUYER CARE?",
         f"Addresses a documented failure mode with a defined mechanism at "
         f"engineering-definition maturity; the decisive falsification "
         f"experiment is specified and costed as NOT_ESTABLISHED pending "
         f"vendor quotation — no invented precision."),
        ("6. WHAT IS THE DECISIVE EXPERIMENT?",
         f"{wp1.get('work_package','WP-01')}: {wp1.get('test_article','')} — "
         f"{wp1.get('measurement','')}. Acceptance: "
         f"{(pkg.verification[0].get('acceptance','') if pkg.verification else wp1.get('acceptance_criterion',''))} "
         f"Recorded effort: {wp1.get('estimated_effort','NOT_RECORDED')}."),
        ("7. WHAT DOES THE BUYER RECEIVE?", buyer_receives),
        ("8. WHAT MUST THE BUYER DEVELOP?", buyer_must),
        ("9. WHAT WOULD KILL THE PROJECT?", hl["kill_if"]),
    ]
    for q, a in qa:
        st.append(Paragraph(_esc(q), S["QH"]))
        st.append(Paragraph(_esc(a), S["BC"]))

    if caps:
        st.append(Paragraph("BUYER CAPABILITY REQUIRED", S["QH"]))
        st.append(Paragraph(_esc(caps), S["BC"]))

    st.append(Paragraph(_esc(
        "Evidence discipline: every claim is traceable to the engineering record; "
        "unknowns are preserved, not suppressed; no AI-generated result is "
        "presented as a physical observation (Constitution Art. XXXVIII)."),
        S["DIS"]))
    doc.build(st, onFirstPage=_footer_canvas(ident), onLaterPages=_footer_canvas(ident))
    return out_path


# ---------------------------------------------------------------------------
# 00 PACKAGE README
# ---------------------------------------------------------------------------
def render_package_readme(pkg, hl, files_manifest, out_path):
    ident = pkg.identity_line
    doc = _doc(out_path, ident, f"Package README — {pkg.pkg_id}")
    st = [Paragraph(_esc(hl["technology_name"]), S["CT"]),
          Paragraph(_esc(f"Package {pkg.pkg_id} · Portfolio {pkg.num} of 15 · "
                         f"Version {pkg.version}"), S["CS"]), Spacer(1, 6)]
    st.append(Paragraph("READING ORDER", S["SH"]))
    st.append(Paragraph(
        "1. 03_BUYER_DECISION_CARD.pdf — the nine decision questions<br/>"
        "2. 01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf — one-page executive summary<br/>"
        "3. 02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf — full engineering "
        "definition with mechanism diagram, experiment setup diagram and "
        "typeset governing equations<br/>"
        "4. 04_EVIDENCE_SUMMARY.pdf — external precedent with source hashes<br/>"
        "5. 05_TRANSFER_MANIFEST.pdf — transfer boundary and buyer capability<br/>"
        "Machine-readable layer: the JSON files listed below.", S["BT"]))
    st.append(Paragraph("PACKAGE CONTENTS (from the release manifest)", S["SH"]))
    rows = [["File", "Role", "SHA-256 (first 16)"]]
    for f in files_manifest:
        rows.append([f["file"], f.get("role", ""), f["sha256"][:16]])
    st.append(_tbl(rows, [2.6 * 72, 1.7 * 72, 1.6 * 72]))
    st.append(Paragraph(_esc(
        "Identity: this package's portfolio number, historical package ID, "
        "folder name and content hashes are bound in "
        "PORTFOLIO_IDENTITY_REGISTRY.json at the release root and are "
        "machine-enforced. Historical package IDs are immutable and are "
        "never renumbered."), S["DIS"]))
    doc.build(st, onFirstPage=_footer_canvas(ident), onLaterPages=_footer_canvas(ident))
    return out_path


# ---------------------------------------------------------------------------
# 04 EVIDENCE SUMMARY
# ---------------------------------------------------------------------------
def render_evidence_summary(pkg, hl, loopstate, out_path):
    ident = pkg.identity_line
    doc = _doc(out_path, ident, f"Evidence Summary — {pkg.pkg_id}")
    st = [Paragraph("EVIDENCE SUMMARY", S["CT"]),
          Paragraph(_esc(f"{hl['technology_name']} — Package {pkg.pkg_id}"), S["CS"]),
          Spacer(1, 4)]
    ec = loopstate["evidence_class_counts"]
    st.append(Paragraph("EVIDENCE CLASS DISCIPLINE (Constitution Art. XXXVIII)", S["SH"]))
    rows = [["Class", "Count", "Meaning"]]
    meanings = {
        "SOURCE_FACT": "Fact stated by a captured source",
        "EXTERNAL_PRECEDENT": "Precedent established in captured external sources",
        "AI_INFERENCE": "Inference authored by the engine (untrusted component)",
        "COMPUTATIONAL_RESULT": "Result of a recorded computation",
        "PHYSICAL_OBSERVATION": "Attested measurement of physical reality",
        "UNKNOWN": "Recorded unresolved item (preserved, never converted)",
        "UNCLASSIFIED": "Claim whose recorded origin did not map to a class",
    }
    for cls, cnt in ec.items():
        if cnt:
            rows.append([cls, str(cnt), meanings.get(cls, "")])
    st.append(_tbl(rows, [1.9 * 72, 0.6 * 72, 4.0 * 72]))
    st.append(Paragraph(_esc(
        f"PHYSICAL_OBSERVATION = {ec.get('PHYSICAL_OBSERVATION',0)}. No "
        f"AI-generated computation is presented as a physical observation. "
        f"Loop verification state: {pkg.loop_state}."), S["OK"]))

    st.append(Paragraph("EXTERNAL ENGINEERING PRECEDENT (hashed sources)", S["SH"]))
    for i, ext in enumerate(pkg.external_precedent, start=1):
        st.append(Paragraph(_esc(
            f"Source {i}: {ext.get('source_title', ext.get('source',''))}"), S["QH"]))
        st.append(Paragraph(_esc(f"URL: {ext.get('source','')}"), S["MT"]))
        st.append(Paragraph(_esc(f"Source hash: {ext.get('source_hash','')}"), S["MT"]))
        snippet = _mut(pkg, ext.get("source_snippet", ""))
        st.append(Paragraph(_esc(f"Excerpt: {snippet[:600]}"), S["SM"]))

    if pkg.addendum:
        st.append(Paragraph("V2 MUTATION TRAIL (external evidence that changed this dossier)", S["SH"]))
        for m in pkg.addendum.get("mutations", []):
            st.append(Paragraph(_esc(
                f"{m.get('mutation_id')}: {m.get('field_affected')} — "
                f"reason: {str(m.get('reason',''))[:300]}"), S["SM"]))
            # R372-6: the V2 text itself is rendered in the buyer document
            # (a trail that only names the mutation without showing the
            # correction leaves the buyer with V1 content)
            v2_text = str(m.get("v2_text", ""))
            if v2_text:
                st.append(Paragraph(_esc(
                    f"V2 text now in effect: {v2_text[:700]}"), S["SM"]))
        st.append(Paragraph(
            "Full V1->V2 text trail ships as V2_MUTATION_ADDENDUM.json in this package.",
            S["DIS"]))

    st.append(Paragraph(_esc(
        "Evidence classification: this package contains source-native "
        "information, derived engineering analysis, engineering proposals and "
        "unresolved questions. No evidence has been physically validated."),
        S["DIS"]))
    doc.build(st, onFirstPage=_footer_canvas(ident), onLaterPages=_footer_canvas(ident))
    return out_path


# ---------------------------------------------------------------------------
# 05 TRANSFER MANIFEST — with buyer capability + confidentiality (Phase A5)
# ---------------------------------------------------------------------------
def render_transfer_manifest(pkg, hl, comm, out_path):
    ident = pkg.identity_line
    doc = _doc(out_path, ident, f"Transfer Manifest — {pkg.pkg_id}")
    st = [Paragraph("TRANSFER MANIFEST", S["CT"]),
          Paragraph(_esc(f"{hl['technology_name']} — Package {pkg.pkg_id} "
                         f"(Portfolio {pkg.num} of 15, Version {pkg.version})"), S["CS"]),
          Paragraph(_esc(CONFIDENTIALITY), ParagraphStyle2()), Spacer(1, 4)]
    tb = pkg.transfer_boundary or {}

    st.append(Paragraph("CONFIDENTIALITY CLASSIFICATION", S["SH"]))
    st.append(Paragraph(_esc(
        "CONFIDENTIAL — TECHNOLOGY TRANSFER EVALUATION. This document is "
        "provided for evaluation under non-disclosure. It contains "
        "unpublished engineering definitions and trade secrets."), S["BT"]))

    st.append(Paragraph("WHAT TRANSFERS", S["SH"]))
    for item in tb.get("buyer_receives", []):
        st.append(Paragraph("• " + _esc(_mut(pkg, item)), S["BC"]))

    st.append(Paragraph("WHAT DOES NOT TRANSFER (BUYER MUST DEVELOP)", S["SH"]))
    for item in (tb.get("buyer_must_develop", []) or []):
        st.append(Paragraph("• " + _esc(_mut(pkg, item)), S["BC"]))
    if not (tb.get("buyer_must_develop")):
        st.append(Paragraph("• See engineering dossier build plan — the "
                            "buyer executes the validation work packages.", S["BC"]))

    st.append(Paragraph("BUYER CAPABILITY REQUIRED", S["SH"]))
    profile = next((s for s in comm["commercial_evidence"]
                    if s["section"] == "BUYER_PROFILE"), {})
    for cap in profile.get("required_capabilities", []):
        st.append(Paragraph("• " + _esc(cap), S["BC"]))

    st.append(Paragraph("IP STATUS", S["SH"]))
    ip = next((s for s in comm["commercial_evidence"]
               if s["section"] == "IP_STATUS"), {})
    st.append(Paragraph(_esc(
        f"Patent applications filed by transferor: {ip.get('patent_applications_filed_by_transferor')}. "
        f"Freedom to operate: {ip.get('freedom_to_operate')}. "
        f"Novelty determination: {ip.get('novelty_determination')}. "
        f"{ip.get('novelty_basis','')}"), S["BT"]))

    st.append(Paragraph("TRANSFER CONDITIONS", S["SH"]))
    st.append(Paragraph(_esc(
        "Transfer of this package does not include regulatory clearance, "
        "clinical validation, manufacturing qualification, or any "
        "representation of physical performance. Items marked NOT_ESTABLISHED "
        "or UNKNOWN do not exist as established facts. This manifest is "
        "honest: unavailable items are named as unavailable."), S["BT"]))
    doc.build(st, onFirstPage=_footer_canvas(ident), onLaterPages=_footer_canvas(ident))
    return out_path


def ParagraphStyle2():
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors as _c
    return ParagraphStyle("conf", fontName="Helvetica-Bold", fontSize=8,
                          textColor=_c.HexColor("#b91c1c"), spaceAfter=6)

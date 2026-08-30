"""
builder_dossier.py — R371 V5 full engineering dossier renderer (Phase 4/5/6/7/8/9).

Structure (buyer-facing, engineering-depth):
  1. Cover / identity
  2. System architecture + MECHANISM DIAGRAM (Visual 1)
  3. Governing model — TYPESET EQUATIONS with variables/units/applicability/
     assumptions (Phase 6)
  4. Critical parameters (UNKNOWN values preserved)
  5. Design inputs / design outputs
  6. Failure analysis
  7. Verification & validation + DECISIVE EXPERIMENT DIAGRAM (Visual 2)
  8. Engineering build plan (recorded effort; NO invented cost ladder)
  9. UNKNOWN ROADMAP (Phase 7)
  10. Commercial evidence summary (Phase 3/8 discipline)
  11. Validation economics (Phase 9)
  12. Transfer boundary and kill condition
  13. Loop state (Phase 11)
  14. Abbreviations (generated glossary)
  15. Disclosure
"""

import os

from reportlab.platypus import Image, PageBreak, Paragraph, Spacer, Table, TableStyle

from .builder import (
    _doc, _esc, _footer_canvas, _img, _mut, _tbl, NOT_ESTABLISHED, cell_full,
)
from .equations import measured_equation_image, render_equation_png


def render_engineering_dossier(pkg, hl, eq_registry, roadmap, comm, eco,
                               loopstate, mech_png, exp_pngs, out_path):
    ident = pkg.identity_line
    doc = _doc(out_path, ident,
               f"Engineering Technology-Transfer Dossier — {pkg.pkg_id}")
    st = []

    # -- cover --------------------------------------------------------------
    st.append(Paragraph("ENGINEERING TECHNOLOGY-TRANSFER DOSSIER", S["CT"]))
    st.append(Paragraph(_esc(hl["technology_name"]), ParagraphStyleTitle()))
    st.append(Paragraph(_esc(
        f"Package {pkg.pkg_id} · Portfolio {pkg.num} of 15 · Version {pkg.version} · "
        f"Domain: {pkg.domain}"), S["CS"]))
    st.append(Paragraph(_esc(
        f"Technology maturity: ENGINEERING_DEFINITION · Transfer posture: "
        f"SPONSORED_VALIDATION · Loop verification state: {pkg.loop_state} · "
        f"Physical observations: 0 (no prototype exists)"), S["CS"]))
    st.append(Spacer(1, 8))

    # -- 1. what it is / problem -------------------------------------------
    st.append(Paragraph("1. TECHNOLOGY AND PROBLEM", S["SH"]))
    st.append(Paragraph("WHAT IS IT?", S["QH"]))
    st.append(Paragraph(_esc(_mut(pkg, hl["mechanism"])), S["BT"]))
    st.append(Paragraph("WHY DOES IT MATTER? (problem statement, V2-corrected where recorded)", S["QH"]))
    st.append(Paragraph(_esc(_mut(pkg, hl["problem"])), S["BT"]))

    # -- 2. system architecture + mechanism diagram -------------------------
    st.append(Paragraph("2. SYSTEM ARCHITECTURE", S["SH"]))
    sa = pkg.eng.get("system_architecture", {})
    if isinstance(sa, dict):
        st.append(Paragraph(_esc(_mut(pkg, sa.get("description", ""))), S["BT"]))
        rows = [["ID", "Subsystem", "Function", "Status", "Evidence source"]]
        for sub in sa.get("subsystems", []):
            rows.append([sub.get("id", ""), _mut(pkg, sub.get("name", "")),
                         _mut(pkg, sub.get("function", "")),
                         sub.get("status", ""),
                         _mut(pkg, str(sub.get("evidence_source", "")))])
        if len(rows) > 1:
            st.append(_tbl(rows, [0.5 * 72, 1.35 * 72, 1.9 * 72, 0.75 * 72, 1.9 * 72]))
    st.append(Spacer(1, 6))
    st.append(Paragraph("MECHANISM / SYSTEM ARCHITECTURE (schematic, "
                        "auto-derived from the canonical mechanism record)", S["QH"]))
    if mech_png and os.path.exists(mech_png):
        st.append(_img(mech_png, 6.6 * 72))
    st.append(Paragraph("Schematic representation of the mechanism. No "
                        "prototype exists; this is an engineering-definition "
                        "diagram, not a product rendering.", S["DIS"]))

    # -- 3. governing model: typeset equations ------------------------------
    st.append(Paragraph("3. GOVERNING MODEL — TYPESET EQUATIONS", S["SH"]))
    st.append(Paragraph(_esc(_mut(pkg, eq_registry.get("model_summary", ""))), S["BT"]))
    for e in eq_registry["equations"]:
        st.append(Spacer(1, 4))
        st.append(Paragraph(_esc(
            f"{e['equation_id']} — canonical form (machine-readable, "
            f"verbatim): {e['equation_canonical']}"), S["MT"]))
        if e["typeset"]:
            png = os.path.join(_TMP_DIR, f"{pkg.pkg_id}_{e['equation_id']}.png")
            render_equation_png(e["typeset"], png)
            # R375-3/7: measured equation embed — the typeset PNG is placed
            # at its natural size (up to the 504pt frame) and NEVER below
            # an 8pt effective glyph size; an equation too wide for a
            # readable one-line embed falls back to the verbatim record
            # (rendered as wrapping monospace text) instead of shipping an
            # unreadably shrunken image.
            eq_img, note = measured_equation_image(png, frame_pt=504.0,
                                                   floor_pt=8.0)
            if eq_img is not None:
                st.append(eq_img)
            else:
                st.append(Paragraph(_esc(
                    f"Typeset form omitted for readability — the equation "
                    f"exceeds one readable line at page width ({note}). "
                    f"Verbatim canonical form below."), S["SM"]))
                st.append(Paragraph(_esc(
                    f"{e['equation_canonical']}"), S["MT"]))
        else:
            st.append(Paragraph(_esc(
                f"Relation (rendered verbatim from the record — "
                f"{e['rendering_note']}): {e['math_expression']}"), S["MT"]))
        if e.get("caption"):
            st.append(Paragraph(_esc(f"Caption: {e['caption']}"), S["SM"]))
        if e["variables"]:
            st.append(Paragraph("Variables (recorded critical parameters):", S["SM"]))
            for v in e["variables"]:
                st.append(Paragraph(_esc(
                    f"  {v['symbol']} — {v['recorded_name']} = {v['value']} "
                    f"[{v['unit']}] (basis: {v['basis']})"), S["SM"]))
    st.append(Spacer(1, 4))
    if eq_registry["equations"]:
        e0 = eq_registry["equations"][0]
        if e0.get("applicability"):
            st.append(Paragraph("Applicability / boundary conditions:", S["SM"]))
            for b in e0["applicability"]:
                st.append(Paragraph("  • " + _esc(b), S["SM"]))
        if e0.get("assumptions"):
            st.append(Paragraph("Model assumptions (as recorded):", S["SM"]))
            for a in e0["assumptions"]:
                st.append(Paragraph("  • " + _esc(a), S["SM"]))
    st.append(Spacer(1, 4))
    if eq_registry.get("r374_validation_status"):
        rv = eq_registry["r374_validation_status"]
        t = rv["totals"]
        st.append(Paragraph(_esc(
            f"Validation status (three levels, CEO R374-2 — 'validated' "
            f"never implies an unproven level): STRUCTURAL proven for "
            f"{t['structural_validated']} of {t['equations']} equations; "
            f"APPLICABILITY proven for {t['applicability_validated']} of "
            f"{t['equations']}; DIMENSIONAL proven for "
            f"{t['dimensionally_validated']} of {t['equations']} "
            f"({t['dimensional_not_evaluable']} not evaluable — units "
            f"unrecorded in the canonical record; "
            f"{t['dimensionally_inconsistent']} inconsistent). Per-symbol "
            f"unit status (SOURCE_BACKED / UNKNOWN with resolution "
            f"paths) is carried in EQUATION_REGISTRY.json."), S["DIS"]))
    st.append(Paragraph(
        "The canonical equation strings are retained verbatim in "
        "EQUATION_REGISTRY.json; the typeset form above is a deterministic "
        "rendering of them. Where a canonical string is corrupted, the "
        "corruption is preserved and flagged, never repaired.", S["DIS"]))

    # -- 4. critical parameters ----------------------------------------------
    st.append(Paragraph("4. CRITICAL PARAMETERS (UNKNOWN preserved)", S["SH"]))
    rows = [["Parameter", "Recorded value", "Unit", "Basis", "Verification required"]]
    for cp in pkg.critical_parameters:
        rows.append([_mut(pkg, cp.get("name", "")),
                     _mut(pkg, str(cp.get("value", ""))),
                     cp.get("unit", ""), _mut(pkg, cp.get("basis", "")),
                     _mut(pkg, cp.get("verification_requirement", ""))])
    if len(rows) > 1:
        st.append(_tbl(rows, [1.5 * 72, 1.9 * 72, 0.7 * 72, 0.9 * 72, 1.4 * 72]))

    # -- 5. design inputs / outputs ------------------------------------------
    # R375-1: design inputs are AUTHORITATIVE engineering content — the
    # full value renders (Paragraph wraps, row grows, table splits); no
    # summarization, no truncation.
    st.append(Paragraph("5. DESIGN INPUTS / DESIGN OUTPUTS", S["SH"]))
    rows = [["ID", "Design input", "Value / source"]]
    for di in pkg.design_inputs:
        rows.append([di.get("id", ""), _mut(pkg, di.get("input", "")),
                     cell_full(_mut(pkg, di.get("value", "")))])
    st.append(_tbl(rows, [0.55 * 72, 1.7 * 72, 4.4 * 72]))
    st.append(Spacer(1, 5))
    rows = [["ID", "Design output", "Status", "Missing inputs"]]
    for do in pkg.design_outputs:
        rows.append([do.get("id", ""), _mut(pkg, do.get("description", "")),
                     do.get("status", ""),
                     cell_full(_mut(pkg, "; ".join(
                         do.get("missing_inputs", []) or [])))])
    st.append(_tbl(rows, [0.55 * 72, 2.3 * 72, 0.8 * 72, 3.0 * 72]))

    # -- 6. failure analysis --------------------------------------------------
    st.append(Paragraph("6. FAILURE ANALYSIS", S["SH"]))
    rows = [["Failure mode", "Mechanism", "Design feature affected", "Evidence"]]
    for fm in pkg.failure_analysis:
        rows.append([_mut(pkg, fm.get("failure_mode", "")),
                     _mut(pkg, fm.get("mechanism", "")),
                     _mut(pkg, fm.get("design_feature_affected", "")),
                     cell_full(_mut(pkg, fm.get("evidence", "")))])
    st.append(_tbl(rows, [1.3 * 72, 1.7 * 72, 1.4 * 72, 2.25 * 72]))

    # -- 7. verification + experiment diagram ---------------------------------
    st.append(Paragraph("7. VERIFICATION AND VALIDATION", S["SH"]))
    rows = [["ID", "Requirement", "Method", "Acceptance", "Result"]]
    for v in pkg.verification:
        rows.append([v.get("id", ""), _mut(pkg, v.get("requirement", "")),
                     cell_full(_mut(pkg, v.get("method", ""))),
                     cell_full(_mut(pkg, v.get("acceptance", ""))),
                     v.get("result", "NOT_TESTED")])
    st.append(_tbl(rows, [0.5 * 72, 1.7 * 72, 1.8 * 72, 1.7 * 72, 0.8 * 72]))
    for v in pkg.validation:
        if isinstance(v, dict):
            st.append(Paragraph(_esc(
                f"Validation: {v.get('requirement','')} — {v.get('method','')} "
                f"(status: {v.get('status','NOT_PERFORMED')})"), S["SM"]))
    st.append(Spacer(1, 6))
    st.append(Paragraph("DECISIVE EXPERIMENT / VERIFICATION SETUP "
                        "(schematic, auto-derived from the canonical build plan)", S["QH"]))
    # R375-3: the diagram may reflow into MULTIPLE parts (each page-fitting,
    # auto-sized); embed every part, each on its own page if needed.
    if exp_pngs:
        pngs = [exp_pngs] if isinstance(exp_pngs, str) else list(exp_pngs)
        for k, png in enumerate(pngs):
            if os.path.exists(png):
                if k > 0:
                    st.append(PageBreak())
                st.append(_img(png, 6.9 * 72))

    # -- 8. build plan ----------------------------------------------------------
    st.append(Paragraph("8. ENGINEERING BUILD PLAN (recorded effort; cost NOT_ESTABLISHED)", S["SH"]))
    rows = [["WP", "Test article", "Measurement", "Acceptance criterion", "Recorded effort"]]
    for step in pkg.build_plan:
        rows.append([step.get("work_package", ""),
                     cell_full(_mut(pkg, step.get("test_article", ""))),
                     cell_full(_mut(pkg, step.get("measurement", ""))),
                     cell_full(_mut(pkg, step.get("acceptance_criterion", ""))),
                     step.get("estimated_effort", "")])
    st.append(_tbl(rows, [0.45 * 72, 1.65 * 72, 1.65 * 72, 1.65 * 72, 0.9 * 72]))
    st.append(Paragraph(_esc(
        "The prior '$5K / $25K / $100K' investment ladder was a template "
        "artifact with no basis in the engineering record and has been "
        "retired. See VALIDATION_ECONOMICS.json: cost is NOT_ESTABLISHED; "
        "time ranges derive mechanically from the recorded per-work-package "
        "efforts above."), S["DIS"]))

    # -- 9. unknown roadmap ------------------------------------------------------
    st.append(Paragraph("9. UNKNOWN ROADMAP (every recorded UNKNOWN, classified)", S["SH"]))
    st.append(Paragraph(_esc(
        f"{roadmap['unknown_count_roadmap']} unknowns preserved exactly as "
        f"recorded. Classification counts: "
        + ", ".join(f"{k}={v}" for k, v in roadmap["classification_counts"].items() if v)
        + ". Each unknown carries a resolution action, expected output and "
        "decision impact — uncertainty as an engineering roadmap, not a "
        "reduced count."), S["BT"]))
    rows = [["ID", "Unknown (verbatim)", "Class", "Resolution action", "Decision impact"]]
    for u in roadmap["unknowns"]:
        rows.append([u["unknown_id"],
                     cell_full(u["unknown_statement"], fontsize=6.7),
                     u["classification"],
                     cell_full(u["resolution_action"], fontsize=6.7),
                     "CRITICAL gate" if u["is_critical"] else "design gate"])
    st.append(_tbl(rows, [0.42 * 72, 2.0 * 72, 1.05 * 72, 2.3 * 72, 0.7 * 72], fontsize=6.7))

    # -- 10. commercial evidence summary -----------------------------------------
    st.append(Paragraph("10. COMMERCIAL EVIDENCE (provenance discipline)", S["SH"]))
    market = next((s for s in comm["commercial_evidence"] if s["section"] == "MARKET_EVIDENCE"), {})
    comp = next((s for s in comm["commercial_evidence"] if s["section"] == "COMPETITOR_EVIDENCE"), {})
    prec = next((s for s in comm["commercial_evidence"] if s["section"] == "COMMERCIAL_PRECEDENT"), {})
    ip = next((s for s in comm["commercial_evidence"] if s["section"] == "IP_STATUS"), {})
    st.append(Paragraph(_esc(f"MARKET: {market.get('verdict','')} — no "
                             "market-research source is integrated; no figures "
                             "are invented (see COMMERCIAL_EVIDENCE.json for "
                             "the full metric schema and establishment pathway)."), S["BT"]))
    st.append(Paragraph(_esc(f"COMPETITIVE CONTEXT: {comp.get('verdict','')}"), S["BT"]))
    if comp.get("entries"):
        for entry in comp["entries"]:
            st.append(Paragraph(_esc(
                f"  {entry['entry_id']}: {', '.join(entry['companies_named_in_source'])} "
                f"— cited within hashed source '{entry['source_title']}'"), S["SM"]))
    st.append(Paragraph(_esc(f"COMMERCIAL PRECEDENT: {prec.get('verdict','')}"), S["BT"]))
    st.append(Paragraph(_esc(
        f"IP STATUS: patents filed: {ip.get('patent_applications_filed_by_transferor','')}; "
        f"FTO: {ip.get('freedom_to_operate','')}; novelty: {ip.get('novelty_determination','')}."), S["BT"]))

    # -- 11. validation economics --------------------------------------------------
    st.append(Paragraph("11. VALIDATION ECONOMICS", S["SH"]))
    tr = eco["time_range"]
    st.append(Paragraph(_esc(
        f"Cost range: {eco['cost_range']['value']} — {eco['cost_range']['basis']}"), S["BT"]))
    st.append(Paragraph(_esc(
        f"Time to decisive experiment (WP-01): {tr['first_decisive_work_package'].get('recorded_effort')}. "
        f"Full build plan (sequential sum of recorded efforts): "
        f"{tr['full_build_plan']['low_weeks']}–{tr['full_build_plan']['high_weeks']} weeks. "
        f"Basis: {tr['basis']}"), S["BT"]))
    st.append(Paragraph(_esc(
        f"Expected decision: {eco['expected_decision']['decision']} — "
        f"acceptance: {eco['expected_decision']['acceptance_criterion']}"), S["BT"]))

    # -- 12. transfer boundary + kill ------------------------------------------------
    st.append(Paragraph("12. TRANSFER BOUNDARY AND KILL CONDITION", S["SH"]))
    tb = pkg.transfer_boundary or {}
    st.append(Paragraph("BUYER RECEIVES:", S["QH"]))
    for item in tb.get("buyer_receives", []):
        st.append(Paragraph("• " + _esc(_mut(pkg, item)), S["BC"]))
    st.append(Paragraph("BUYER MUST DEVELOP:", S["QH"]))
    for item in (tb.get("buyer_must_develop", []) or []):
        st.append(Paragraph("• " + _esc(_mut(pkg, item)), S["BC"]))
    st.append(Paragraph("KILL CONDITION (falsification criterion):", S["QH"]))
    st.append(Paragraph(_esc(hl["kill_if"]), ParagraphStyleKill()))

    # -- 13. loop state ----------------------------------------------------------------
    st.append(Paragraph("13. AI LOOP STATE (SYNTHETIC / MODELLED / PROPOSED / REAL separation)", S["SH"]))
    ec = loopstate["evidence_class_counts"]
    st.append(Paragraph(_esc(
        f"Loop verification state: {pkg.loop_state}. Evidence classes: "
        f"SOURCE_FACT={ec.get('SOURCE_FACT',0)}, EXTERNAL_PRECEDENT={ec.get('EXTERNAL_PRECEDENT',0)}, "
        f"AI_INFERENCE={ec.get('AI_INFERENCE',0)}, COMPUTATIONAL_RESULT={ec.get('COMPUTATIONAL_RESULT',0)}, "
        f"PHYSICAL_OBSERVATION={ec.get('PHYSICAL_OBSERVATION',0)}, UNKNOWN={ec.get('UNKNOWN',0)}. "
        "No AI-generated event is presented as REAL. External-loop event queues "
        "(buyer feedback, engineer review, experiment results, observations, "
        "belief updates, package revisions) are defined in LOOP_STATE.json and "
        "are empty — no external contact has occurred."), S["BT"]))

    # -- 14. abbreviations ----------------------------------------------------------------
    st.append(Paragraph("14. ABBREVIATIONS", S["SH"]))
    st.append(_abbrev_table(pkg, hl))

    # -- 15. V2 corrections in effect (R373-5: the dossier PDF is a chain
    # stage — every recorded mutation, INCLUDING additive disclosures that
    # replace no V1 string, must be carried by this document) -------------
    if pkg.addendum:
        st.append(Paragraph(
            "15. V2 CORRECTIONS IN EFFECT (external evidence that changed "
            "this dossier)", S["SH"]))
        for m in pkg.addendum.get("mutations", []):
            basis = "; ".join(m.get("evidence_basis", [])) or \
                "evidence basis recorded in the addendum"
            st.append(Paragraph(_esc(
                f"{m.get('mutation_id')} — {m.get('field_affected')}: "
                f"{str(m.get('v2_text', ''))} "
                f"[Evidence basis: {basis}]"), S["BT"]))
        st.append(Paragraph(_esc(
            "Full V1->V2 text trail with evidence basis ships as "
            "V2_MUTATION_ADDENDUM.json in this package."), S["DIS"]))

    st.append(Paragraph(_esc(
        "Disclosure: this dossier is an engineering-definition technology-"
        "transfer document. It contains source-native information, derived "
        "engineering analysis, engineering proposals and unresolved "
        "questions. No physical validation has been performed. Nothing in "
        "this document is a representation of regulatory clearance, clinical "
        "performance, or manufacturing readiness."), S["DIS"]))

    doc.build(st, onFirstPage=_footer_canvas(ident), onLaterPages=_footer_canvas(ident))
    return out_path


# ---------------------------------------------------------------------------
_TMP_DIR = "/tmp/r371_eq_render"
import os as _os
_os.makedirs(_TMP_DIR, exist_ok=True)

_ABBREVIATIONS = {
    "MEMS": "Micro-Electro-Mechanical System",
    "PZT": "Lead Zirconate Titanate (piezoelectric ceramic)",
    "UWB": "Ultra-Wideband",
    "SAR": "Specific Absorption Rate",
    "SNR": "Signal-to-Noise Ratio",
    "TOA": "Time of Arrival",
    "ICP": "Intracranial Pressure",
    "CSF": "Cerebrospinal Fluid",
    "NIR": "Near-Infrared",
    "PV": "Photovoltaic",
    "ML": "Machine Learning",
    "AUC": "Area Under the (ROC) Curve",
    "NMR": "Nuclear Magnetic Resonance",
    "MRI": "Magnetic Resonance Imaging",
    "RF": "Radio Frequency",
    "ASD": "Adjustable Siphon / Anti-Siphon Device (context: shunt valve)",
    "NPH": "Normal Pressure Hydrocephalus",
    "NEP": "Neprilysin",
    "FTO": "Freedom to Operate",
    "Cpk": "Process Capability Index",
    "EI": "Flexural Stiffness (E × I)",
    "VENC": "Velocity Encoding (MR flow imaging)",
    "GUDID": "Global Unique Device Identification Database",
    "EMA": "European Medicines Agency",
    "ASTM": "ASTM International (standards body)",
    "ISO": "International Organization for Standardization",
}


def _abbrev_table(pkg, hl):
    import re
    text = " ".join([
        hl.get("mechanism", ""), hl.get("problem", ""), hl.get("kill_if", ""),
        pkg.gm.get("summary", ""),
        " ".join(str(e) for e in pkg.equations),
        " ".join(str(u) for u in pkg.unknowns),
        " ".join(str(cp.get("name", "")) + " " + str(cp.get("value", "")) + " " + str(cp.get("verification_requirement", "")) for cp in pkg.critical_parameters),
        " ".join(str(s.get("test_article", "")) + " " + str(s.get("equipment", "")) + " " + str(s.get("measurement", "")) for s in pkg.build_plan),
    ])
    found = []
    for abbr, full in _ABBREVIATIONS.items():
        if re.search(rf"\b{abbr}\b", text):
            found.append([abbr, full])
    if not found:
        found = [["(none)", "No abbreviated terms used in this dossier"]]
    return _tbl(found, [1.0 * 72, 5.7 * 72], header=False, fontsize=7.4)


def ParagraphStyleTitle():
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors as _c
    return ParagraphStyle("title2", fontName="Helvetica-Bold", fontSize=13.5,
                          leading=17, textColor=_c.HexColor("#0c1e38"),
                          spaceAfter=6)


def ParagraphStyleKill():
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors as _c
    return ParagraphStyle("kill", fontName="Helvetica-Bold", fontSize=9.6,
                          leading=13, textColor=_c.HexColor("#b91c1c"),
                          spaceAfter=6, borderPadding=4)


# styles injected
S = None


def init_styles(styles):
    global S
    S = styles

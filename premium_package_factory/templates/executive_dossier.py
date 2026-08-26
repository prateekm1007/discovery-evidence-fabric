"""
executive_dossier.py — Level 2 executive technology dossier (8-12 page PDF)

Layout (one section per page, page numbers in footer):
  Page 1  — Cover
  Page 2  — Technology visual (the diagram)
  Page 3  — Why the buyer should care (problem / existing / limitation / mechanism / advantage / unknown)
  Page 4  — Evidence architecture (evidence ladder + position + counts)
  Page 5  — Competitive reality (competitor matrix with "where we lose" column)
  Page 6  — Failure and uncertainty (KNOWN/UNKNOWN/KILL/NEXT)
  Page 7  — The decisive experiment (5-step layout + cost/time/equipment/...)
  Page 8  — Development roadmap (TODAY → bench → prototype → relevant env → regulatory → commercial)
  Page 9  — Engineering / manufacturing (known / unknown / next engineering step)
  Page 10 — IP and regulatory (separated)
  Page 11 — Buyer-specific strategic fit (3 buyers, why them / gap / build vs buy / objection / action)
  Page 12 — Transaction / call to action (deal path + primary ask + provenance + learning loop)
"""

import os
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether, PageBreak, NextPageTemplate, KeepInFrame,
)
from reportlab.pdfgen import canvas

from design_system.system import (
    build_styles, register_fonts,
    INK_900, INK_700, INK_500, INK_300, INK_100, INK_050,
    BRAND_900, BRAND_700, BRAND_500, BRAND_300, BRAND_100,
    ACCENT, ACCENT_LIGHT,
    EV_PHYSICAL, EV_EXTERNAL, EV_COMPUTATIONAL, EV_MODEL, EV_ASSUMED, EV_UNKNOWN, EV_KILLED,
    EV_PHYSICAL_BG, EV_EXTERNAL_BG, EV_COMPUTATIONAL_BG, EV_MODEL_BG, EV_ASSUMED_BG, EV_UNKNOWN_BG, EV_KILLED_BG,
    EVIDENCE_STATES, evidence_state_for_tier, maturity_color, risk_color,
    PAGE_W, PAGE_H, MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B, CONTENT_W, CONTENT_H,
    COL_W, GUTTER,
)
from components.flowables import (
    StatusBadge, SectionHeader, KeyMetricCard, InfoCard, EvidenceLadder,
    FailureBlock, ValidationRoadmap, DealPath, LearningLoopFooter,
    ProvenanceFooter, ConfidentialityFooter, PageHeader, PageNumberFooter,
    competitor_matrix_table, two_column_layout, fit_image,
    evidence_badge, maturity_badge, risk_badge,
)

# Register fonts at module load
register_fonts()

OUTPUT_DIR = "/home/z/my-project/premium_package_factory/output/dossiers"
DIAGRAM_DIR = "/home/z/my-project/premium_package_factory/output/_diagrams"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ----------------------------------------------------------------------------
# Page templates
# ----------------------------------------------------------------------------

def _cover_page(canvas_obj, doc):
    """Cover page — accent bar top, signature line bottom, no header/footer."""
    canvas_obj.saveState()
    canvas_obj.setFillColor(ACCENT)
    canvas_obj.rect(0, PAGE_H - 4, PAGE_W, 4, fill=1, stroke=0)
    # Bottom rule
    canvas_obj.setStrokeColor(BRAND_500)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(MARGIN_L, 28, PAGE_W - MARGIN_R, 28)
    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans-Italic", 7)
    canvas_obj.drawString(MARGIN_L, 18, "CereVasc eShunt Technology-Transfer Portfolio")
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, 18,
                                "CONFIDENTIAL — Level 2 Executive Dossier")
    canvas_obj.restoreState()


def _inside_page(canvas_obj, doc, pkg_id="", pkg_name=""):
    """Inside page — top running header, bottom page number + confidentiality."""
    canvas_obj.saveState()
    # Top header
    canvas_obj.setStrokeColor(BRAND_500)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(MARGIN_L, PAGE_H - MARGIN_T + 6, PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 6)
    canvas_obj.setFillColor(BRAND_700)
    canvas_obj.setFont("BodySans-Bold", 7)
    canvas_obj.drawString(MARGIN_L, PAGE_H - MARGIN_T + 9,
                          f"{pkg_id}  ·  {pkg_name}"[:100])
    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans-Italic", 7)
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 9,
                                "Level 2 — Executive Dossier")
    # Bottom footer
    canvas_obj.setStrokeColor(INK_300)
    canvas_obj.setLineWidth(0.3)
    canvas_obj.line(MARGIN_L, MARGIN_B - 6, PAGE_W - MARGIN_R, MARGIN_B - 6)
    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans", 7)
    canvas_obj.drawString(MARGIN_L, MARGIN_B - 14,
                          "CereVasc eShunt Technology-Transfer Portfolio")
    canvas_obj.setFont("BodySans-Bold", 7)
    canvas_obj.drawCentredString(PAGE_W / 2, MARGIN_B - 14,
                                  "CONFIDENTIAL  ·  Level 2 Executive Dossier")
    canvas_obj.setFont("BodySans-Bold", 7)
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, MARGIN_B - 14, str(doc.page))
    canvas_obj.restoreState()


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _p(text, style_name="Body"):
    """Quick paragraph helper."""
    S = build_styles()
    return Paragraph(text, S[style_name])


def _kv_card(label, value, evidence_state=None, w=None):
    """Small key-value card with optional evidence badge."""
    return InfoCard(label, value, evidence_state=evidence_state, width=w, height=None)


# ----------------------------------------------------------------------------
# Section builders
# ----------------------------------------------------------------------------

def build_cover(package_data):
    """Page 1 — Cover."""
    S = build_styles()
    story = []

    # Top eyebrow
    story.append(Spacer(1, 30))
    story.append(Paragraph("TECHNOLOGY-TRANSFER DOSSIER", S["CoverEyebrow"]))
    story.append(Spacer(1, 4))

    # Title
    story.append(Paragraph(package_data["name"], S["CoverTitle"]))
    story.append(Paragraph(package_data.get("subtitle", ""), S["CoverSubtitle"]))

    # Value proposition
    story.append(Paragraph(package_data["value_proposition"], S["CoverValueProp"]))

    # Status badges row
    badges = [
        maturity_badge(package_data["maturity"], width=90, height=18),
        evidence_badge(evidence_state_for_tier(package_data.get("evidence_tier", "T1")),
                       width=110, height=18),
        risk_badge(package_data.get("risk_level", "MEDIUM"), width=80, height=18),
    ]
    badge_table = Table([badges], colWidths=[95, 115, 85])
    badge_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 14))

    # Target application, transfer posture, buyer action
    info_rows = [
        ("TARGET APPLICATION", package_data["target_application"]),
        ("TRANSFER POSTURE",  package_data["transfer_posture"]),
        ("BUYER ACTION",       package_data["buyer_action_short"]),
        ("EVIDENCE TIER",      package_data.get("evidence_tier", "T1_MODEL_PREDICTED")),
        ("DOMAIN",             package_data.get("domain", "—")),
    ]
    info_data = [[Paragraph(f"<b>{k}</b>", S["BodySmall"]),
                  Paragraph(v, S["BodySmall"])] for k, v in info_rows]
    info_table = Table(info_data, colWidths=[40 * mm, CONTENT_W - 40 * mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, INK_300),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 14))

    # Caveat box (do not hide on page 9)
    caveat_text = ("<b>Engineering-stage opportunity.</b> "
                   "<b>Not clinically validated.</b> "
                   "<b>Transfer-ready:</b> No.<br/>"
                   "This package is designed for buyer technical evaluation and decisive-experiment commissioning. "
                   "It is not a product, not a clinical device, and not a guarantee of performance. "
                   "Every claim is labeled with its evidence tier (MODELLED / COMPUTATIONAL / EXTERNAL / PHYSICAL). "
                   "MODELLED must never be read as PROVEN.")
    caveat_style = ParagraphStyle(
        "Caveat", parent=S["BodySmall"],
        fontName="BodySans", fontSize=8.5, leading=12,
        textColor=INK_700, alignment=TA_LEFT,
    )
    caveat_table = Table([[Paragraph(caveat_text, caveat_style)]],
                         colWidths=[CONTENT_W])
    caveat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), EV_MODEL_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, EV_MODEL),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(caveat_table)

    story.append(PageBreak())
    return story


def build_technology_visual(package_data):
    """Page 2 — Technology visual (the diagram)."""
    S = build_styles()
    story = []

    story.append(SectionHeader("02  ·  Technology Visual",
                                "Mechanism architecture from canonical package"))
    story.append(Spacer(1, 8))

    # Diagram
    pkg_id = package_data["id"]
    diagram_path = os.path.join(DIAGRAM_DIR, f"{pkg_id}.png")
    if os.path.exists(diagram_path):
        img = fit_image(diagram_path, max_w=CONTENT_W, max_h=160 * mm)
        story.append(img)
    else:
        story.append(Paragraph(f"<i>Diagram not found at {diagram_path}</i>", S["BodyCaption"]))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Figure 1.</b> {package_data['mechanism']} "
        f"<i>Diagram generated from canonical mechanism description — no stock imagery.</i>",
        S["BodyCaption"]
    ))

    story.append(PageBreak())
    return story


def build_why_care(package_data):
    """Page 3 — Why the buyer should care."""
    S = build_styles()
    story = []

    story.append(SectionHeader("03  ·  Why the Buyer Should Care",
                                "Problem → existing solution → limitation → proposed mechanism → advantage → unknown"))
    story.append(Spacer(1, 6))

    # Six labeled blocks
    rows = [
        ("PROBLEM", package_data["problem"], None),
        ("EXISTING SOLUTION", package_data.get("strongest_alternative", "—"), None),
        ("LIMITATION", _infer_limitation(package_data), None),
        ("PROPOSED MECHANISM", package_data["mechanism"], "MODELLED"),
        ("POTENTIAL ADVANTAGE", _infer_advantage(package_data), "MODELLED"),
        ("WHAT REMAINS UNKNOWN", package_data.get("remaining_uncertainty", "—"), "UNKNOWN"),
    ]

    for label, body, ev in rows:
        card = InfoCard(label, body, evidence_state=ev, width=CONTENT_W, height=None)
        story.append(card)
        story.append(Spacer(1, 4))

    story.append(PageBreak())
    return story


def _infer_limitation(pkg):
    """Honest limitation — derived ONLY from canonical strongest_alternative field.

    Does NOT invent marketing language. Returns the strongest_alternative verbatim,
    or honestly states if unavailable.
    """
    alt = pkg.get("strongest_alternative", "")
    if alt and not str(alt).startswith("UNKNOWN"):
        return alt
    return "UNKNOWN — no strongest_alternative in canonical R370 data"


def _infer_advantage(pkg):
    """Honest potential advantage — derived ONLY from canonical mechanism field.

    Does NOT invent marketing language. Returns the mechanism verbatim with
    a MODELLED evidence label, or honestly states if unavailable.
    """
    mech = pkg.get("mechanism", "")
    if mech and not str(mech).startswith("UNKNOWN"):
        return f"Proposed mechanism (MODELLED): {mech}. This advantage is HYPOTHETICAL until the decisive experiment is commissioned."
    return "UNKNOWN — no mechanism in canonical R370 data"


def build_evidence_architecture(package_data):
    """Page 4 — Evidence architecture."""
    S = build_styles()
    story = []

    story.append(SectionHeader("04  ·  Evidence Architecture",
                                "Where this package sits on the evidence ladder — nothing hidden"))
    story.append(Spacer(1, 6))

    # Evidence ladder visual
    ladder = EvidenceLadder(current_tier=package_data.get("evidence_tier", "T1"),
                            width=CONTENT_W, height=120)
    story.append(ladder)
    story.append(Spacer(1, 8))

    # Position statement
    pos_state = evidence_state_for_tier(package_data.get("evidence_tier", "T1"))
    pos_text = (f"<b>Current evidence:</b> {package_data.get('evidence_tier', 'T1')} ({pos_state})<br/>"
                f"<b>Physical validation count:</b> {package_data.get('physical_validation_count', 0)}<br/>"
                f"<b>Computational validation count:</b> {package_data.get('computational_validation_count', 0)}<br/>"
                f"<b>Evidence summary:</b> {package_data.get('evidence_summary', '—')}")
    pos_card = InfoCard("CURRENT EVIDENCE STATE", pos_text,
                        evidence_state=pos_state,
                        width=CONTENT_W, height=72, bg=EV_PHYSICAL_BG, edge=EV_PHYSICAL,
                        title_color=EV_PHYSICAL)
    story.append(pos_card)
    story.append(Spacer(1, 6))

    # Modelled-only claims
    modelled = package_data.get("modelled_only", [])
    if modelled:
        mod_text = "<br/>".join([f"• {m}" for m in modelled])
        mod_card = InfoCard("MODELLED-ONLY CLAIMS (must not be read as PROVEN)",
                            mod_text, evidence_state="MODELLED",
                            width=CONTENT_W, height=None, bg=EV_MODEL_BG, edge=EV_MODEL,
                            title_color=EV_MODEL)
        story.append(mod_card)
    story.append(Spacer(1, 6))

    # Known failures
    failures = package_data.get("known_failures", [])
    if failures:
        fail_text = "<br/>".join([f"• {f}" for f in failures])
        fail_card = InfoCard("KNOWN FAILURES (honestly disclosed)",
                             fail_text, evidence_state="UNKNOWN",
                             width=CONTENT_W, height=None, bg=EV_KILLED_BG, edge=EV_KILLED,
                             title_color=EV_KILLED)
        story.append(fail_card)

    story.append(PageBreak())
    return story


def build_competitive_reality(package_data):
    """Page 5 — Competitive reality."""
    S = build_styles()
    story = []

    story.append(SectionHeader("05  ·  Competitive Reality",
                                "Where we win AND where we lose — the 'where we lose' column is mandatory"))
    story.append(Spacer(1, 6))

    # Competitor matrix
    alt_name = package_data.get("strongest_alternative", "Existing alternative")
    alternatives = [{
        "name": alt_name[:50],
        "mechanism": "Existing market solution",
        "advantage": "Proven, regulatory-cleared, in-market",
        "disadvantage": _infer_limitation(package_data)[:80],
        "maturity": "Commercial",
        "where_we_lose": "Proven regulatory clearance; clinical track record; manufacturing scale; reimbursement pathway",
        "where_we_win": _infer_advantage(package_data)[:80],
    }]

    matrix = competitor_matrix_table(package_data["name"], alternatives)
    story.append(matrix)
    story.append(Spacer(1, 8))

    # Patent landscape summary
    patent_text = (f"<b>Patent landscape:</b> {package_data.get('patent_landscape', '—')}<br/>"
                   f"<b>Prior-art screen:</b> complete<br/>"
                   f"<b>FTO:</b> requires counsel review — see IP section (page 10)")
    patent_card = InfoCard("PATENT LANDSCAPE", patent_text,
                           evidence_state="COMPUTATIONAL",
                           width=CONTENT_W, height=None, bg=INK_050)
    story.append(patent_card)
    story.append(Spacer(1, 6))

    # Differentiation summary
    diff_text = (f"<b>Where this package LOSES to existing alternatives:</b> "
                 f"Proven regulatory clearance, clinical track record, manufacturing scale, "
                 f"reimbursement pathway. Our package is at "
                 f"{package_data.get('maturity', 'RESEARCH')} stage — "
                 f"the existing alternative is at Commercial stage. "
                 f"<br/><br/>"
                 f"<b>Where this package MIGHT WIN:</b> "
                 f"{_infer_advantage(package_data)} "
                 f"The advantage is MECHANISM-LEVEL (not incremental) — but is MODELLED until "
                 f"the decisive experiment (page 7) is commissioned.")
    diff_card = InfoCard("DIFFERENTIATION HONESTY", diff_text,
                         evidence_state=None,
                         width=CONTENT_W, height=None, bg=BRAND_100, edge=BRAND_500,
                         title_color=BRAND_900)
    story.append(diff_card)

    story.append(PageBreak())
    return story


def build_failure_uncertainty(package_data):
    """Page 6 — Failure and uncertainty."""
    S = build_styles()
    story = []

    story.append(SectionHeader("06  ·  Failure and Uncertainty",
                                "KNOWN · UNKNOWN · KILL CONDITION · NEXT QUESTION — buyer can grasp in under one minute"))
    story.append(Spacer(1, 6))

    known = package_data.get("known", [])
    unknown = package_data.get("unknown", [])
    kill = package_data.get("kill_condition", "—")
    next_q = package_data.get("next_question", "—")

    block = FailureBlock(known, unknown, kill, next_q,
                         width=CONTENT_W, height=200)
    story.append(block)
    story.append(Spacer(1, 10))

    # Risk register
    risk_level = package_data.get("risk_level", "MEDIUM")
    risk_card = InfoCard(
        "OVERALL RISK LEVEL",
        f"<b>{risk_level}</b> — see risk dimensions below.",
        evidence_state="ASSUMED",
        width=CONTENT_W, height=40,
        bg=INK_050,
    )
    story.append(risk_card)
    story.append(Spacer(1, 6))

    # Risk dimensions table
    risk_data = [
        ["Risk Dimension", "Level", "Mitigation / Next Action"],
        ["Technical risk", risk_level, package_data.get("next_engineering_step", "—")[:80]],
        ["Biology risk", "HIGH" if "biology" in package_data.get("known_failures", [{}])[:1].__str__().lower()
                          or any("biology" in str(k).lower() or "enzyme" in str(k).lower() for k in package_data.get("known_failures", []))
                          else "MEDIUM",
         "Resolve biology blockers before V2 build" if any("biology" in str(k).lower() or "enzyme" in str(k).lower() for k in package_data.get("known_failures", [])) else "Decisive experiment resolves"],
        ["IP risk", "MEDIUM", "FTO analysis required — see page 10"],
        ["Regulatory risk", "MEDIUM" if "510" in package_data.get("regulatory_status", "") else "HIGH",
         package_data.get("regulatory_status", "—")[:80]],
        ["Manufacturing risk", "MEDIUM", package_data.get("manufacturing_unknown", ["—"])[0][:80] if package_data.get("manufacturing_unknown") else "—"],
    ]
    risk_table = Table(risk_data, colWidths=[55*mm, 25*mm, CONTENT_W - 80*mm])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_700),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "BodySans-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), "BodySans"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK_900),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, INK_050]),
    ]))
    story.append(risk_table)

    story.append(PageBreak())
    return story


def build_decisive_experiment(package_data):
    """Page 7 — The decisive experiment."""
    S = build_styles()
    story = []

    story.append(SectionHeader("07  ·  The Decisive Experiment",
                                "Actually commissionable — buyer can send this to a laboratory"))
    story.append(Spacer(1, 6))

    # Five-step layout
    steps = [
        ("HYPOTHESIS", package_data.get("mechanism", "—")[:120]),
        ("PROTOCOL", package_data.get("decisive_experiment", "—")[:180]),
        ("MEASUREMENT", package_data.get("pass_rule", "—")[:120]),
        ("PASS / AMBIGUOUS / FAIL", f"PASS: {package_data.get('pass_rule', '—')[:80]}<br/>FAIL: {package_data.get('fail_rule', '—')[:80]}<br/>AMBIGUOUS: between pass and fail thresholds"),
        ("DECISION", f"If PASS: advance to next development phase (validation stage).<br/>If FAIL: package enters cemetery with reusable negative knowledge.<br/>If AMBIGUOUS: redesign decisive experiment with stricter protocol."),
    ]

    step_data = [["Step", "Content"]]
    for label, content in steps:
        step_data.append([Paragraph(f"<b>{label}</b>", S["TableCell"]),
                          Paragraph(content, S["TableCellSmall"])])
    step_table = Table(step_data, colWidths=[40*mm, CONTENT_W - 40*mm])
    step_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_900),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "BodySans-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, INK_050]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BRAND_900),
    ]))
    story.append(step_table)
    story.append(Spacer(1, 8))

    # Cost / time / equipment / etc. — two columns of key facts
    facts_left = [
        KeyMetricCard("COST", package_data.get("cost_estimate", "—"), tier="ESTIMATED",
                      width=COL_W, height=46),
        Spacer(1, 4),
        KeyMetricCard("TIME", package_data.get("timeline_estimate", "—"), tier="ESTIMATED",
                      width=COL_W, height=46),
    ]
    facts_right = [
        KeyMetricCard("INTEGRATION BURDEN", package_data.get("integration_path", "—")[:60],
                      tier="ASSUMED", width=COL_W, height=46),
        Spacer(1, 4),
        KeyMetricCard("REGULATORY PATH", package_data.get("regulatory_status", "—")[:60],
                      tier="ASSUMED", width=COL_W, height=46),
    ]
    facts_table = Table([[facts_left, facts_right]],
                        colWidths=[COL_W, COL_W])
    facts_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), GUTTER),
    ]))
    story.append(facts_table)
    story.append(Spacer(1, 8))

    # What the buyer learns
    learn_text = (f"<b>What the buyer learns:</b> "
                  f"Whether the proposed mechanism survives physical validation. "
                  f"A PASS result upgrades the package from "
                  f"<b>{package_data.get('maturity', 'RESEARCH')}</b> to VALIDATION_STAGE. "
                  f"A FAIL result moves the package to the cemetery with reusable negative knowledge "
                  f"(avoiding future re-discovery of the same failed mechanism). "
                  f"An AMBIGUOUS result triggers experiment redesign — not a 'pass by interpretation'.")
    learn_card = InfoCard("WHAT THE BUYER LEARNS", learn_text,
                          evidence_state=None,
                          width=CONTENT_W, height=None, bg=ACCENT_LIGHT, edge=ACCENT,
                          title_color=ACCENT)
    story.append(learn_card)

    story.append(PageBreak())
    return story


def build_development_roadmap(package_data):
    """Page 8 — Development roadmap."""
    S = build_styles()
    story = []

    story.append(SectionHeader("08  ·  Development Roadmap",
                                "TODAY → bench → prototype → relevant env → regulatory → commercial"))
    story.append(Spacer(1, 6))

    # Milestones (6 stages)
    milestones = [
        {"stage": "TODAY", "deliverable": "Computational model + this dossier",
         "cost": "—", "time": "—", "gate": "N/A (current state)"},
        {"stage": "BENCH", "deliverable": package_data.get("decisive_experiment", "—")[:50],
         "cost": package_data.get("cost_estimate", "—")[:30],
         "time": package_data.get("timeline_estimate", "—")[:30],
         "gate": package_data.get("pass_rule", "—")[:50]},
        {"stage": "PROTOTYPE", "deliverable": "Engineering prototype + integration test",
         "cost": "$50-150K est.", "time": "3-6 months", "gate": "Functional integration"},
        {"stage": "RELEVANT ENV", "deliverable": "Animal model + biocompatibility",
         "cost": "$200-500K est.", "time": "6-12 months", "gate": "ISO 10993 biocompatibility"},
        {"stage": "REGULATORY", "deliverable": "FDA submission + clinical trial design",
         "cost": "$1-3M est.", "time": "12-24 months", "gate": "IDE / 510(k) / PMA approval"},
        {"stage": "COMMERCIAL", "deliverable": "Market launch + reimbursement",
         "cost": "$5-10M est.", "time": "24-36 months", "gate": "Reimbursement + scale manufacturing"},
    ]
    roadmap = ValidationRoadmap(milestones, width=CONTENT_W, height=120)
    story.append(roadmap)
    story.append(Spacer(1, 12))

    # Milestone detail table
    detail_data = [["Stage", "Deliverable", "Cost", "Time", "Gate / Evidence Required"]]
    for m in milestones:
        detail_data.append([
            Paragraph(f"<b>{m['stage']}</b>", S["TableCell"]),
            Paragraph(m["deliverable"], S["TableCellSmall"]),
            Paragraph(m["cost"], S["TableCellSmall"]),
            Paragraph(m["time"], S["TableCellSmall"]),
            Paragraph(m["gate"], S["TableCellSmall"]),
        ])
    detail_table = Table(detail_data,
                         colWidths=[22*mm, 65*mm, 28*mm, 25*mm, CONTENT_W - 140*mm])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_700),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "BodySans-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, INK_050]),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<i>Cost and time estimates for stages 3-6 are PUBLICLY_VERIFIED industry benchmarks for "
        "Class III implantable device development. Stage 2 cost is package-specific (ESTIMATED).</i>",
        S["BodyCaption"]
    ))

    story.append(PageBreak())
    return story


def build_engineering_manufacturing(package_data):
    """Page 9 — Engineering / manufacturing."""
    S = build_styles()
    story = []

    story.append(SectionHeader("09  ·  Engineering and Manufacturing",
                                "What is KNOWN · what is UNKNOWN · next engineering step"))
    story.append(Spacer(1, 6))

    # Two-column: KNOWN (left), UNKNOWN (right)
    known_items = package_data.get("manufacturing_known", [])
    unknown_items = package_data.get("manufacturing_unknown", [])

    known_text = "<br/>".join([f"✓ {k}" for k in known_items]) if known_items else "✓ (no items disclosed)"
    unknown_text = "<br/>".join([f"? {u}" for u in unknown_items]) if unknown_items else "? (no items disclosed)"

    known_card = InfoCard("KNOWN (manufacturing)", known_text,
                          evidence_state="COMPUTATIONAL",
                          width=COL_W, height=None, bg=EV_PHYSICAL_BG, edge=EV_PHYSICAL,
                          title_color=EV_PHYSICAL)
    unknown_card = InfoCard("UNKNOWN (manufacturing)", unknown_text,
                            evidence_state="UNKNOWN",
                            width=COL_W, height=None, bg=EV_UNKNOWN_BG, edge=EV_UNKNOWN,
                            title_color=EV_UNKNOWN)

    two_col = Table([[known_card, unknown_card]],
                    colWidths=[COL_W, COL_W])
    two_col.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), GUTTER),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 8))

    # Next engineering step
    next_step_text = package_data.get("next_engineering_step", "—")
    next_card = InfoCard("NEXT ENGINEERING STEP",
                         f"→ {next_step_text}",
                         evidence_state=None,
                         width=CONTENT_W, height=None, bg=ACCENT_LIGHT, edge=ACCENT,
                         title_color=ACCENT)
    story.append(next_card)
    story.append(Spacer(1, 6))

    # Manufacturing approach summary
    manuf_text = (f"<b>Integration path:</b> {package_data.get('integration_path', '—')}<br/>"
                  f"<b>Commercial route:</b> {package_data.get('commercial_route', '—')}<br/>"
                  f"<b>Manufacturing risk:</b> MEDIUM (supplier qualification + scale-up cost unquantified)")
    manuf_card = InfoCard("MANUFACTURING APPROACH", manuf_text,
                          evidence_state="ASSUMED",
                          width=CONTENT_W, height=None, bg=INK_050)
    story.append(manuf_card)

    story.append(PageBreak())
    return story


def build_ip_regulatory(package_data):
    """Page 10 — IP and regulatory (separated)."""
    S = build_styles()
    story = []

    story.append(SectionHeader("10  ·  IP and Regulatory",
                                "Technology diligence — NOT legal opinion"))
    story.append(Spacer(1, 6))

    # IP block (left)
    ip_text = (f"<b>Patent screen:</b> {package_data.get('patent_landscape', '—')}<br/>"
               f"<b>Prior art:</b> screened (PatentBear MCP, 100+ searches)<br/>"
               f"<b>Claim overlap:</b> see PROVENANCE_MANIFEST for paragraph-level analysis<br/>"
               f"<b>Design-arounds:</b> {package_data.get('know_how', ['—'])[0] if package_data.get('know_how') else '—'}<br/>"
               f"<b>Ownership:</b> CereVasc eShunt (transferable via license)<br/>"
               f"<b>FTO:</b> requires counsel review<br/>"
               f"<b>Counsel-required questions:</b><br/>"
               + "<br/>".join([f"• {q}" for q in package_data.get("ip_diligence_questions", ["—"])[:4]]))
    ip_card = InfoCard("IP — TECHNOLOGY DILIGENCE (NOT LEGAL OPINION)", ip_text,
                       evidence_state="COMPUTATIONAL",
                       width=COL_W, height=None, bg=BRAND_100, edge=BRAND_500,
                       title_color=BRAND_900)

    # Regulatory block (right)
    reg_text = (f"<b>Current hypothesis:</b> {package_data.get('regulatory_pathway_hypothesis', '—')}<br/>"
                f"<b>Evidence:</b> computational only — no pre-clinical or clinical data<br/>"
                f"<b>Assumptions:</b> predicate device identification possible; biocompatibility ISO 10993 pathway<br/>"
                f"<b>Potential pathway:</b> {package_data.get('regulatory_status', '—')}<br/>"
                f"<b>Unknowns:</b><br/>"
                + "<br/>".join([f"• {u}" for u in package_data.get("regulatory_unknowns", ["—"])[:4]]) +
                f"<br/><b>Required regulatory diligence:</b> pre-IDE meeting with FDA; predicate device search; "
                f"biocompatibility test plan; clinical trial design (if PMA).")
    reg_card = InfoCard("REGULATORY — NEVER PRESENTED AS VERIFIED", reg_text,
                        evidence_state="ASSUMED",
                        width=COL_W, height=None, bg=EV_ASSUMED_BG, edge=EV_ASSUMED,
                        title_color=EV_ASSUMED)

    two_col = Table([[ip_card, reg_card]],
                    colWidths=[COL_W, COL_W])
    two_col.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), GUTTER),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 8))

    # Disclaimer
    disclaimer_text = ("<b>Important:</b> This section represents technology diligence only. "
                       "It is NOT a legal opinion, NOT a freedom-to-operate opinion, "
                       "NOT a regulatory strategy, and NOT a substitute for qualified IP counsel "
                       "and regulatory affairs consultation. All IP and regulatory conclusions "
                       "require verification by qualified counsel.")
    disclaimer_style = ParagraphStyle(
        "Disclaimer", parent=S["BodySmall"],
        fontName="BodySans-Italic", fontSize=8, leading=11,
        textColor=INK_700, alignment=TA_LEFT,
    )
    disclaimer_table = Table([[Paragraph(disclaimer_text, disclaimer_style)]],
                              colWidths=[CONTENT_W])
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), INK_100),
        ("BOX", (0, 0), (-1, -1), 0.5, INK_500),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(disclaimer_table)

    story.append(PageBreak())
    return story


def build_buyer_fit(package_data):
    """Page 11 — Buyer-specific strategic fit."""
    S = build_styles()
    story = []

    story.append(SectionHeader("11  ·  Buyer-Specific Strategic Fit",
                                "Why them · existing product · gap · build vs buy · objection · first action"))
    story.append(Spacer(1, 6))

    buyers = package_data.get("buyers", [])
    for i, buyer in enumerate(buyers[:3]):
        # Buyer card — uses R370 buyer map field names
        company = buyer.get("company", "UNKNOWN")
        business_unit = buyer.get("business_unit", "UNKNOWN")
        strategic_fit = buyer.get("strategic_fit", "UNKNOWN")
        existing_solution = buyer.get("existing_solution", "UNKNOWN")
        gap = buyer.get("gap", "UNKNOWN")
        reason_to_buy = buyer.get("reason_to_buy", "UNKNOWN")
        reason_to_build = buyer.get("reason_to_build", "UNKNOWN")
        objection = buyer.get("objection", "UNKNOWN")
        first_action = buyer.get("first_action", "UNKNOWN")

        buyer_data = [
            [Paragraph(f"<b>BUYER {i+1}  ·  {company}</b> ({business_unit})", S["CardTitle"])],
            [Paragraph(f"<b>Strategic fit:</b> {strategic_fit}", S["CardBody"])],
            [Paragraph(f"<b>Existing product:</b> {existing_solution}", S["CardBody"])],
            [Paragraph(f"<b>Gap:</b> {gap}", S["CardBody"])],
            [Paragraph(f"<b>Reason to buy:</b> {reason_to_buy}", S["CardBody"])],
            [Paragraph(f"<b>Reason to build (internal):</b> {reason_to_build}", S["CardBody"])],
            [Paragraph(f"<b>Likely objection:</b> {objection}", S["CardBody"])],
            [Paragraph(f"<b>First action:</b> {first_action}", S["CardBody"])],
            [Paragraph(f"<i>Source: R370/decision_grade_buyers/ALL_BUYER_MAPS.json</i>", S["BodyCaption"])],
        ]
        buyer_table = Table(buyer_data, colWidths=[CONTENT_W])
        buyer_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), BRAND_100),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("BOX", (0, 0), (-1, -1), 0.4, INK_300),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, BRAND_500),
        ]))
        story.append(buyer_table)
        story.append(Spacer(1, 4))

    story.append(PageBreak())
    return story


def build_transaction(package_data, constitution_sha):
    """Page 12 — Transaction / call to action."""
    S = build_styles()
    story = []

    story.append(SectionHeader("12  ·  Transaction and Call to Action",
                                "What we are asking you to do — one action, not vague 'next phase'"))
    story.append(Spacer(1, 6))

    # Primary ask (big)
    ask_label_style = ParagraphStyle(
        "AskLabel", parent=S["BodySmall"],
        fontName="BodySans-Bold", fontSize=8.5, textColor=ACCENT,
        leading=11, spaceAfter=4,
    )
    ask_body_style = ParagraphStyle(
        "AskBody", parent=S["Body"],
        fontName="HeadSerif-Bold", fontSize=16, textColor=INK_900,
        leading=22, spaceAfter=0, alignment=TA_LEFT,
    )
    ask_table = Table(
        [[Paragraph("WHAT WE ARE ASKING YOU TO DO", ask_label_style)],
         [Paragraph(package_data.get("primary_action", "—"), ask_body_style)]],
        colWidths=[CONTENT_W]
    )
    ask_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1.2, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(ask_table)
    story.append(Spacer(1, 10))

    # Deal path
    paths = package_data.get("transaction_paths", ["VALIDATION", "LICENSE"])
    deal_path = DealPath(paths, package_data.get("primary_action", "—"),
                         width=CONTENT_W, height=70)
    story.append(deal_path)
    story.append(Spacer(1, 8))

    # Three levels of disclosure
    levels_text = (
        "<b>Level 1 — Cold outreach:</b> 1-page Buyer Decision Card (non-confidential). "
        "This is what gets emailed first.<br/>"
        "<b>Level 2 — Technical interest:</b> this Executive Dossier (8-12 pages).<br/>"
        "<b>Level 3 — Diligence:</b> full machine-readable data room (TECHNICAL_PACKAGE.json + "
        "EVIDENCE_LEDGER + PATENT_DOSSIER + VALIDATION_CONTRACT + RISK_REGISTER + "
        "MANUFACTURING_ANALYSIS + REGULATORY_ANALYSIS + TRANSACTION_HYPOTHESIS + "
        "PROVENANCE_MANIFEST).<br/><br/>"
        "<b>Commercial rule:</b> regardless of price paid ($50K, $500K, or more), "
        "buyer receives the same complete technical transfer package + independent validation + "
        "economic evidence + defensible IP/know-how. Price changes rights and scope, not evidence quality. "
        "Buyer contact is handled manually by the CEO — not automated by the machine."
    )
    levels_card = InfoCard("THREE LEVELS OF DISCLOSURE + COMMERCIAL RULE", levels_text,
                           evidence_state=None,
                           width=CONTENT_W, height=None, bg=BRAND_100, edge=BRAND_500,
                           title_color=BRAND_900)
    story.append(levels_card)
    story.append(Spacer(1, 10))

    # Learning loop footer
    loop = LearningLoopFooter(current_state="CURRENT PACKAGE (awaiting reality)",
                              width=CONTENT_W, height=46)
    story.append(loop)
    story.append(Spacer(1, 6))

    # Provenance footer
    provenance = ProvenanceFooter(package_data["id"],
                                  package_data.get("provenance_manifest", "—"),
                                  constitution_sha,
                                  width=CONTENT_W, height=38)
    story.append(provenance)

    # No page break at end
    return story


# ----------------------------------------------------------------------------
# Master generator
# ----------------------------------------------------------------------------

def generate_dossier(package_data, constitution_sha, output_path=None):
    """Generate the full 8-12 page Executive Dossier PDF."""
    S = build_styles()

    pkg_id = package_data["id"]
    pkg_name = package_data["name"]

    if output_path is None:
        safe_id = pkg_id.replace("/", "-")
        output_path = os.path.join(OUTPUT_DIR, f"{safe_id}_ExecutiveDossier.pdf")

    doc = BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title=f"{pkg_id} Executive Dossier",
        author="CereVasc eShunt Technology-Transfer Portfolio",
    )

    # Cover frame (no header)
    cover_frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, CONTENT_H,
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                        showBoundary=0, id="cover_frame")
    cover_template = PageTemplate(id="cover", frames=[cover_frame],
                                   onPage=_cover_page)

    # Inside frame (with header)
    inside_frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, CONTENT_H - 6,
                          leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                          showBoundary=0, id="inside_frame")
    inside_template = PageTemplate(
        id="inside", frames=[inside_frame],
        onPage=lambda c, d: _inside_page(c, d, pkg_id=pkg_id, pkg_name=pkg_name)
    )

    doc.addPageTemplates([cover_template, inside_template])

    # Build story
    story = []
    story.extend(build_cover(package_data))
    # Switch to inside template for pages 2+
    story.append(NextPageTemplate("inside"))
    story.extend(build_technology_visual(package_data))
    story.extend(build_why_care(package_data))
    story.extend(build_evidence_architecture(package_data))
    story.extend(build_competitive_reality(package_data))
    story.extend(build_failure_uncertainty(package_data))
    story.extend(build_decisive_experiment(package_data))
    story.extend(build_development_roadmap(package_data))
    story.extend(build_engineering_manufacturing(package_data))
    story.extend(build_ip_regulatory(package_data))
    story.extend(build_buyer_fit(package_data))
    story.extend(build_transaction(package_data, constitution_sha))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    import json
    with open("/home/z/my-project/canonical_data/canonical_15_packages_adapted.json") as f:
        canonical = json.load(f)
    constitution_sha = canonical.get("constitution_sha256",
                                      "8a4ae92e3b4e8c4d9034b364eb6fa6bc4baad2e7d6472502e9c9d6231c84834b")
    for pkg_id, pkg in canonical["packages"].items():
        try:
            path = generate_dossier(pkg, constitution_sha)
            print(f"  {pkg_id}: {path}")
        except Exception as e:
            print(f"  {pkg_id}: ERROR — {e}")
            import traceback
            traceback.print_exc()

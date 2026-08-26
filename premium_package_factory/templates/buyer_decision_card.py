"""
buyer_decision_card.py — Level 1 cold-outreach one-page PDF generator.

Every package gets ONE page. No confidential information.

Layout (top to bottom):
  - Header: PKG ID + name + maturity badge + evidence badge
  - WHAT (one-sentence value proposition)
  - WHY IT MATTERS (problem + buyer)
  - WHAT IS PROVEN (evidence summary + tier)
  - WHAT IS NOT PROVEN (modelled-only + known failures)
  - WHY YOU (top buyer + why)
  - DECISIVE EXPERIMENT (one-line + pass rule)
  - COST / TIME (badge)
  - WHAT WE WANT (primary action)
"""

import os
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether
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
)
from components.flowables import (
    StatusBadge, evidence_badge, maturity_badge, risk_badge, fit_image,
)

# Register fonts at module load (page callbacks may fire before generate_* runs)
register_fonts()

OUTPUT_DIR = "/home/z/my-project/premium_package_factory/output/buyer_cards"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _on_page(canvas_obj, doc, package_id=None, package_name=None):
    """Page callback: minimal header, footer with confidentiality."""
    canvas_obj.saveState()

    # Top accent bar
    canvas_obj.setFillColor(ACCENT)
    canvas_obj.rect(0, PAGE_H - 4, PAGE_W, 4, fill=1, stroke=0)

    # Top thin rule
    canvas_obj.setStrokeColor(BRAND_500)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(MARGIN_L, PAGE_H - MARGIN_T + 4, PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 4)

    canvas_obj.setFillColor(BRAND_700)
    canvas_obj.setFont("BodySans-Bold", 7)
    canvas_obj.drawString(MARGIN_L, PAGE_H - MARGIN_T + 8,
                          f"{package_id}  ·  BUYER DECISION CARD" if package_id else "BUYER DECISION CARD")
    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans-Italic", 7)
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 8,
                               "Level 1 — Cold Outreach (Non-Confidential)")

    # Bottom: confidentiality + portfolio signature
    canvas_obj.setStrokeColor(INK_300)
    canvas_obj.setLineWidth(0.3)
    canvas_obj.line(MARGIN_L, MARGIN_B - 6, PAGE_W - MARGIN_R, MARGIN_B - 6)

    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans", 7)
    canvas_obj.drawString(MARGIN_L, MARGIN_B - 14, "CereVasc eShunt Technology-Transfer Portfolio")

    canvas_obj.setFont("BodySans-Bold", 7)
    canvas_obj.drawCentredString(PAGE_W / 2, MARGIN_B - 14, "CONFIDENTIAL  ·  Level 1 Cold-Outreach Card")

    canvas_obj.setFont("BodySans-Bold", 7)
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, MARGIN_B - 14, package_id or "")

    canvas_obj.restoreState()


def _make_field_box(label, body_text, evidence_state=None, w=None, h=None,
                    label_color=BRAND_700, body_color=INK_900, bg=INK_050):
    """Build a labeled info box as a Table (so it wraps text properly)."""
    S = build_styles()
    label_style = ParagraphStyle(
        "FieldLabel", parent=S["BodySmall"],
        fontName="BodySans-Bold", fontSize=7, textColor=label_color,
        leading=9, spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "FieldBody", parent=S["BodySmall"],
        fontName="BodySans", fontSize=8.5, textColor=body_color,
        leading=11, spaceAfter=0,
    )

    label_p = Paragraph(label.upper(), label_style)
    body_p = Paragraph(body_text, body_style)

    rows = [[label_p], [body_p]]
    t = Table(rows, colWidths=[w or CONTENT_W], rowHeights=[10, h or 22])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.4, INK_300),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def generate_buyer_card(package_data, output_path=None):
    """Generate a one-page Buyer Decision Card PDF for a single package."""
    register_fonts()
    S = build_styles()

    pkg_id = package_data["id"]
    pkg_name = package_data["name"]
    pkg_subtitle = package_data.get("subtitle", "")
    value_prop = package_data["value_proposition"]
    problem = package_data["problem"]
    buyer = package_data["buyer"]
    evidence_now = package_data["evidence_now"]
    evidence_tier = package_data.get("evidence_tier", "T1_MODEL_PREDICTED")
    modelled_only = package_data.get("modelled_only", [])
    known_failures = package_data.get("known_failures", [])
    decisive_exp = package_data["decisive_experiment"]
    pass_rule = package_data["pass_rule"]
    cost = package_data["cost_estimate"]
    timeline = package_data["timeline_estimate"]
    primary_action = package_data["primary_action"]
    maturity = package_data["maturity"]
    buyers = package_data.get("buyers", [])
    top_buyer = buyers[0] if buyers else None

    # Output path
    if output_path is None:
        safe_id = pkg_id.replace("/", "-")
        output_path = os.path.join(OUTPUT_DIR, f"{safe_id}_BuyerDecisionCard.pdf")

    # Setup doc
    doc = BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title=f"{pkg_id} Buyer Decision Card",
        author="CereVasc eShunt Technology-Transfer Portfolio",
    )

    def page_callback(canvas_obj, doc):
        _on_page(canvas_obj, doc, package_id=pkg_id, package_name=pkg_name)

    frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, CONTENT_H,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                  showBoundary=0)
    template = PageTemplate(id="card", frames=[frame], onPage=page_callback)
    doc.addPageTemplates([template])

    story = []

    # ----- Header row: PKG ID + name + maturity badge -----
    title_style = ParagraphStyle(
        "CardTitle", parent=S["CoverTitle"],
        fontName="HeadSerif-Bold", fontSize=20, leading=22,
        textColor=INK_900, spaceAfter=2, alignment=TA_LEFT,
    )
    subtitle_style = ParagraphStyle(
        "CardSubtitle", parent=S["CoverSubtitle"],
        fontName="HeadSerif-Italic", fontSize=10.5, leading=13,
        textColor=INK_700, spaceAfter=8, alignment=TA_LEFT,
    )

    # Badges row
    badges = [
        maturity_badge(maturity, width=80, height=15),
        evidence_badge(evidence_state_for_tier(evidence_tier), width=90, height=15),
    ]
    badge_table = Table([badges], colWidths=[85, 95])
    badge_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 6))

    # Title + subtitle
    story.append(Paragraph(pkg_name, title_style))
    story.append(Paragraph(pkg_subtitle, subtitle_style))

    # ----- WHAT (value proposition) -----
    story.append(_make_field_box(
        "WHAT — Value Proposition", value_prop,
        w=CONTENT_W, h=None,
        bg=BRAND_100, label_color=BRAND_900,
    ))
    story.append(Spacer(1, 4))

    # ----- WHY IT MATTERS (problem + buyer) -----
    why_text = f"<b>Problem:</b> {problem}<br/><b>Buyer:</b> {buyer}"
    story.append(_make_field_box(
        "WHY IT MATTERS", why_text,
        w=CONTENT_W, h=None, bg=INK_050,
    ))
    story.append(Spacer(1, 4))

    # ----- WHAT IS PROVEN (evidence summary) -----
    proven_text = f"{evidence_now}<br/><b>Tier:</b> {evidence_tier}"
    story.append(_make_field_box(
        "WHAT IS PROVEN", proven_text,
        w=CONTENT_W, h=None, bg=EV_PHYSICAL_BG, label_color=EV_PHYSICAL,
    ))
    story.append(Spacer(1, 4))

    # ----- WHAT IS NOT PROVEN (modelled + known failures) -----
    modelled_str = "; ".join(modelled_only[:3]) if modelled_only else "None"
    failures_str = "; ".join(known_failures[:2]) if known_failures else "None"
    not_proven_text = f"<b>Modelled only:</b> {modelled_str}<br/><b>Known failures:</b> {failures_str}"
    story.append(_make_field_box(
        "WHAT IS NOT PROVEN", not_proven_text,
        w=CONTENT_W, h=None, bg=EV_MODEL_BG, label_color=EV_MODEL,
    ))
    story.append(Spacer(1, 4))

    # ----- WHY YOU (top buyer) -----
    if top_buyer:
        why_you = (f"<b>{top_buyer['name']}</b> — {top_buyer['why']} "
                   f"<i>Gap:</i> {top_buyer['gap']} "
                   f"<i>First action:</i> {top_buyer['first_technical_action']}")
    else:
        why_you = buyer
    story.append(_make_field_box(
        "WHY YOU", why_you,
        w=CONTENT_W, h=None, bg=BRAND_100, label_color=BRAND_900,
    ))
    story.append(Spacer(1, 4))

    # ----- DECISIVE EXPERIMENT -----
    exp_text = f"{decisive_exp}<br/><b>Pass:</b> {pass_rule}"
    story.append(_make_field_box(
        "DECISIVE EXPERIMENT", exp_text,
        w=CONTENT_W * 0.62, h=None, bg=ACCENT_LIGHT, label_color=ACCENT,
    ))

    # Cost / time on the right
    cost_text = f"<b>Cost:</b> {cost}<br/><b>Time:</b> {timeline}"
    cost_box = _make_field_box(
        "COST / TIME", cost_text,
        w=CONTENT_W * 0.35, h=None, bg=INK_050, label_color=INK_700,
    )
    # Two-column layout for experiment + cost
    exp_row = Table(
        [[story.pop(), cost_box]],
        colWidths=[CONTENT_W * 0.63, CONTENT_W * 0.35]
    )
    exp_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 6),
    ]))
    story.append(exp_row)
    story.append(Spacer(1, 6))

    # ----- WHAT WE WANT (primary action — large) -----
    ask_style_label = ParagraphStyle(
        "AskLabel", parent=S["BodySmall"],
        fontName="BodySans-Bold", fontSize=8.5, textColor=ACCENT,
        leading=11, spaceAfter=4,
    )
    ask_style_body = ParagraphStyle(
        "AskBody", parent=S["Body"],
        fontName="HeadSerif-Bold", fontSize=14, textColor=INK_900,
        leading=18, spaceAfter=0, alignment=TA_LEFT,
    )
    ask_table = Table(
        [[Paragraph("WHAT WE ARE ASKING YOU TO DO", ask_style_label)],
         [Paragraph(primary_action, ask_style_body)]],
        colWidths=[CONTENT_W]
    )
    ask_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1.0, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(ask_table)

    # Build the PDF
    doc.build(story)
    return output_path


if __name__ == "__main__":
    import json
    with open("/home/z/my-project/canonical_data/canonical_15_packages_adapted.json") as f:
        canonical = json.load(f)
    for pkg_id, pkg in canonical["packages"].items():
        try:
            path = generate_buyer_card(pkg)
            print(f"  {pkg_id}: {path}")
        except Exception as e:
            print(f"  {pkg_id}: ERROR — {e}")
            import traceback
            traceback.print_exc()

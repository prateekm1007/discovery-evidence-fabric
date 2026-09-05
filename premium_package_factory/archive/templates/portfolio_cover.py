"""
portfolio_cover.py — Portfolio-level PDF for the 15-technology portfolio.

Pages:
  Page 1  — Cover (THE 15-TECHNOLOGY PORTFOLIO)
  Page 2  — Portfolio thesis
  Page 3  — 15-package map (table)
  Page 4  — Maturity map (visual)
  Page 5  — Technology domains
  Page 6  — Buyer sectors
  Page 7  — Validation capital required
  Page 8  — Top five opportunities
  Page 9  — Portfolio risk map
  Page 10 — How the AI learning loop works
  Page 11 — Individual package cards (mini)
"""

import os
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, NextPageTemplate,
)

from design_system.system import (
    build_styles, register_fonts,
    INK_900, INK_700, INK_500, INK_300, INK_100, INK_050,
    BRAND_900, BRAND_700, BRAND_500, BRAND_300, BRAND_100,
    ACCENT, ACCENT_LIGHT,
    EV_PHYSICAL, EV_EXTERNAL, EV_COMPUTATIONAL, EV_MODEL, EV_ASSUMED, EV_UNKNOWN, EV_KILLED,
    EV_PHYSICAL_BG, EV_EXTERNAL_BG, EV_COMPUTATIONAL_BG, EV_MODEL_BG, EV_ASSUMED_BG, EV_UNKNOWN_BG, EV_KILLED_BG,
    MAT_TRANSFER_READY, MAT_VALIDATION_STAGE, MAT_ENGINEERING, MAT_RESEARCH,
    MAT_TRANSFER_READY_BG, MAT_VALIDATION_STAGE_BG, MAT_ENGINEERING_BG, MAT_RESEARCH_BG,
    EVIDENCE_STATES, evidence_state_for_tier, maturity_color, risk_color,
    PAGE_W, PAGE_H, MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B, CONTENT_W, CONTENT_H,
    COL_W, GUTTER,
)
from components.flowables import (
    StatusBadge, SectionHeader, KeyMetricCard, InfoCard, EvidenceLadder,
    FailureBlock, ValidationRoadmap, DealPath, LearningLoopFooter,
    ProvenanceFooter, ConfidentialityFooter,
    evidence_badge, maturity_badge, risk_badge,
)

register_fonts()

OUTPUT_DIR = "/home/z/my-project/premium_package_factory/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _cover_page(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFillColor(ACCENT)
    canvas_obj.rect(0, PAGE_H - 4, PAGE_W, 4, fill=1, stroke=0)
    canvas_obj.setStrokeColor(BRAND_500)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(MARGIN_L, 28, PAGE_W - MARGIN_R, 28)
    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans-Italic", 7)
    canvas_obj.drawString(MARGIN_L, 18, "CereVasc eShunt Technology-Transfer Portfolio")
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, 18,
                                "CONFIDENTIAL — Portfolio Overview")
    canvas_obj.restoreState()


def _inside_page(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(BRAND_500)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(MARGIN_L, PAGE_H - MARGIN_T + 6, PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 6)
    canvas_obj.setFillColor(BRAND_700)
    canvas_obj.setFont("BodySans-Bold", 7)
    canvas_obj.drawString(MARGIN_L, PAGE_H - MARGIN_T + 9,
                          "CereVasc eShunt  ·  15-Technology Portfolio")
    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans-Italic", 7)
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 9,
                                "Portfolio Overview")
    canvas_obj.setStrokeColor(INK_300)
    canvas_obj.setLineWidth(0.3)
    canvas_obj.line(MARGIN_L, MARGIN_B - 6, PAGE_W - MARGIN_R, MARGIN_B - 6)
    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans", 7)
    canvas_obj.drawString(MARGIN_L, MARGIN_B - 14,
                          "CereVasc eShunt Technology-Transfer Portfolio")
    canvas_obj.setFont("BodySans-Bold", 7)
    canvas_obj.drawCentredString(PAGE_W / 2, MARGIN_B - 14,
                                  "CONFIDENTIAL  ·  Portfolio Overview")
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, MARGIN_B - 14, str(doc.page))
    canvas_obj.restoreState()


def _p(text, style_name="Body"):
    S = build_styles()
    return Paragraph(text, S[style_name])


# ----------------------------------------------------------------------------
# Section builders
# ----------------------------------------------------------------------------

def build_portfolio_cover():
    """Page 1 — Portfolio cover."""
    S = build_styles()
    story = []

    story.append(Spacer(1, 30))
    story.append(Paragraph("TECHNOLOGY-TRANSFER PORTFOLIO", S["CoverEyebrow"]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("THE 15-TECHNOLOGY PORTFOLIO", S["PortfolioTitle"]))
    story.append(Paragraph(
        "An honest, evidence-classified portfolio of fifteen technology-transfer "
        "opportunities in CSF shunt systems — each with buyer-actionable decisive experiments.",
        S["PortfolioSubtitle"]
    ))

    # Summary stats
    story.append(Spacer(1, 14))
    stats_data = [
        [KeyMetricCard("ACTIVE PACKAGES", "15", tier="MODELLED",
                       width=COL_W, height=46, note="13 RESEARCH + 2 ENGINEERING"),
         KeyMetricCard("TRANSFER-READY", "0", tier="UNKNOWN",
                       width=COL_W, height=46, note="honest disclosure")]
    ]
    stats1 = Table(stats_data, colWidths=[COL_W, COL_W])
    stats1.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), GUTTER),
    ]))
    story.append(stats1)
    story.append(Spacer(1, 6))

    stats2_data = [
        [KeyMetricCard("REAL BUYER", "0", tier="UNKNOWN",
                       width=COL_W, height=46, note="CEO-owned, not automated"),
         KeyMetricCard("REAL EXPERIMENT", "0", tier="UNKNOWN",
                       width=COL_W, height=46, note="reality = bottleneck")]
    ]
    stats2 = Table(stats2_data, colWidths=[COL_W, COL_W])
    stats2.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), GUTTER),
    ]))
    story.append(stats2)
    story.append(Spacer(1, 6))

    stats3_data = [
        [KeyMetricCard("SYNTHETIC LOOP", "3", tier="COMPUTATIONAL",
                       width=COL_W, height=46, note="synthetically verified"),
         KeyMetricCard("REAL LOOP", "0", tier="UNKNOWN",
                       width=COL_W, height=46, note="awaiting real buyer")]
    ]
    stats3 = Table(stats3_data, colWidths=[COL_W, COL_W])
    stats3.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), GUTTER),
    ]))
    story.append(stats3)
    story.append(Spacer(1, 14))

    # Constitution / provenance
    constitution_text = (
        "<b>Constitution v1.7.0</b> (37 articles including Article XXXVII SYNTHETIC_VS_REAL_LOOP)<br/>"
        "<b>SHA-256:</b> 8a4ae92e3b4e8c4d9034b364eb6fa6bc4baad2e7d6472502e9c9d6231c84834b<br/>"
        "<b>Cemetery:</b> 8 packages with reusable negative knowledge (P-03, P-05, P-10, P-12, P-19, P-20, P-23, P-25)"
    )
    con_card = InfoCard("PORTFOLIO PROVENANCE", constitution_text,
                        evidence_state="COMPUTATIONAL",
                        width=CONTENT_W, height=70, bg=INK_050)
    story.append(con_card)

    story.append(PageBreak())
    return story


def build_thesis():
    """Page 2 — Portfolio thesis."""
    S = build_styles()
    story = []

    story.append(SectionHeader("02  ·  Portfolio Thesis",
                                "Why this portfolio exists and what it does NOT claim"))
    story.append(Spacer(1, 8))

    thesis_text = (
        "<b>The portfolio mission:</b> identify, classify, and make buyer-evaluable "
        "fifteen distinct technology opportunities for improving CSF shunt outcomes — "
        "each with a decisive, commissionable validation experiment.<br/><br/>"

        "<b>What this portfolio IS:</b><br/>"
        "• An honest, evidence-classified set of 15 technology-transfer packages<br/>"
        "• A system where every claim carries an evidence tier (MODELLED / COMPUTATIONAL / EXTERNAL / PHYSICAL)<br/>"
        "• A portfolio where failed candidates produce reusable negative knowledge<br/>"
        "• A portfolio where each package can be commissioned for decisive validation by a buyer<br/><br/>"

        "<b>What this portfolio is NOT:</b><br/>"
        "• A set of clinically validated technologies (none have physical validation)<br/>"
        "• A set of transfer-ready products (TRANSFER_READY = 0/15)<br/>"
        "• A guarantee of regulatory clearance (regulatory pathways are HYPOTHESES)<br/>"
        "• A substitute for IP counsel, regulatory affairs, or clinical validation<br/>"
        "• A static invention report (the portfolio is designed to evolve with real data)<br/><br/>"

        "<b>The honest state:</b> 0/15 transfer-ready, 0/15 physically validated, "
        "0 real buyers, 0 real experiments, 0 real loops. The portfolio is at the "
        "<b>evidence-quality-and-presentation layer</b>, not the validation layer. "
        "The next milestone is NOT more code — it is the first real buyer → real feedback → "
        "real experiment → real data cycle."
    )
    thesis_card = InfoCard("PORTFOLIO THESIS", thesis_text,
                           evidence_state=None,
                           width=CONTENT_W, height=None, bg=BRAND_100, edge=BRAND_500,
                           title_color=BRAND_900)
    story.append(thesis_card)
    story.append(Spacer(1, 8))

    # AI loop footer
    loop = LearningLoopFooter(current_state="PORTFOLIO (awaiting reality)",
                              width=CONTENT_W, height=46)
    story.append(loop)

    story.append(PageBreak())
    return story


def build_package_map(canonical):
    """Page 3 — 15-package map."""
    S = build_styles()
    story = []

    story.append(SectionHeader("03  ·  15-Package Map",
                                "All active packages with maturity + evidence tier + decisive experiment"))
    story.append(Spacer(1, 6))

    # Build table
    data = [["ID", "Name", "Domain", "Maturity", "Tier", "Decisive Experiment (short)"]]
    for pkg_id, pkg in canonical["packages"].items():
        dec_exp = pkg.get("decisive_experiment", "—")
        # Shorten
        dec_short = dec_exp[:60] + ("…" if len(dec_exp) > 60 else "")
        data.append([
            Paragraph(f"<b>{pkg_id}</b>", S["TableCellSmall"]),
            Paragraph(pkg["name"][:35], S["TableCellSmall"]),
            Paragraph(pkg.get("domain", "—")[:20], S["TableCellSmall"]),
            Paragraph(pkg.get("maturity", "—"), S["TableCellSmall"]),
            Paragraph(pkg.get("evidence_tier", "—")[:20], S["TableCellSmall"]),
            Paragraph(dec_short, S["TableCellSmall"]),
        ])

    col_widths = [16*mm, 36*mm, 24*mm, 22*mm, 24*mm, CONTENT_W - 122*mm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_900),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "BodySans-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, INK_050]),
    ]))
    story.append(t)

    story.append(PageBreak())
    return story


def build_maturity_map(canonical):
    """Page 4 — Maturity map."""
    S = build_styles()
    story = []

    story.append(SectionHeader("04  ·  Maturity Map",
                                "0 TRANSFER_READY · 0 VALIDATION_STAGE · 2 ENGINEERING · 13 RESEARCH"))
    story.append(Spacer(1, 8))

    # Count by maturity
    maturities = {}
    for pkg in canonical["packages"].values():
        m = pkg.get("maturity", "RESEARCH")
        maturities[m] = maturities.get(m, 0) + 1

    # Build a 4-tier visual
    tiers = [
        ("TRANSFER_READY", maturities.get("TRANSFER_READY", 0),
         MAT_TRANSFER_READY, MAT_TRANSFER_READY_BG,
         "Physical validation passed. Engineering, IP, regulatory, manufacturing, economics all closed."),
        ("VALIDATION_STAGE", maturities.get("VALIDATION_STAGE", 0),
         MAT_VALIDATION_STAGE, MAT_VALIDATION_STAGE_BG,
         "Decisive experiment physically executed by independent lab. Pass/Fail/Partial outcome known."),
        ("ENGINEERING", maturities.get("ENGINEERING", 0),
         MAT_ENGINEERING, MAT_ENGINEERING_BG,
         "Mechanism computationally demonstrated AND externally verified (T2). Physical validation outstanding."),
        ("RESEARCH", maturities.get("RESEARCH", 0),
         MAT_RESEARCH, MAT_RESEARCH_BG,
         "Mechanism specified, computational model exists. Buyer can commission the decisive experiment."),
    ]

    for label, count, fg, bg, desc in tiers:
        # Big count + label
        count_data = [
            [Paragraph(f"<font size='22'><b>{count}</b></font>", S["Body"]),
             Paragraph(f"<b>{label.replace('_', ' ')}</b><br/><font size='7' color='#64748B'>{desc}</font>",
                       S["BodySmall"])]
        ]
        count_table = Table(count_data, colWidths=[30*mm, CONTENT_W - 30*mm])
        count_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0.8, fg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(count_table)
        story.append(Spacer(1, 6))

    # List which packages are in each tier
    story.append(Spacer(1, 8))
    list_text_parts = []
    for label, count, fg, bg, desc in tiers:
        pkgs = [pid for pid, p in canonical["packages"].items()
                if p.get("maturity") == label]
        if pkgs:
            list_text_parts.append(f"<b>{label.replace('_', ' ')} ({count}):</b> {', '.join(pkgs)}")
    list_card = InfoCard("PACKAGES BY MATURITY",
                         "<br/>".join(list_text_parts),
                         evidence_state=None,
                         width=CONTENT_W, height=None, bg=INK_050)
    story.append(list_card)

    story.append(PageBreak())
    return story


def build_domains(canonical):
    """Page 5 — Technology domains."""
    S = build_styles()
    story = []

    story.append(SectionHeader("05  ·  Technology Domains",
                                "15 packages span 9 technical domains"))
    story.append(Spacer(1, 8))

    # Count by domain
    domains = {}
    for pkg_id, pkg in canonical["packages"].items():
        d = pkg.get("domain", "Other")
        if d not in domains:
            domains[d] = []
        domains[d].append(pkg_id)

    # Build domain cards in a 2-column layout
    domain_cards = []
    for domain, pkgs in domains.items():
        card = InfoCard(domain,
                        f"<b>{len(pkgs)} package(s):</b> {', '.join(pkgs)}",
                        evidence_state="COMPUTATIONAL",
                        width=COL_W, height=None, bg=BRAND_100, edge=BRAND_500,
                        title_color=BRAND_900)
        domain_cards.append(card)

    # Arrange in 2 columns
    rows = []
    for i in range(0, len(domain_cards), 2):
        left = domain_cards[i]
        right = domain_cards[i+1] if i+1 < len(domain_cards) else Paragraph("", S["Body"])
        rows.append([left, right])

    domain_table = Table(rows, colWidths=[COL_W, COL_W])
    domain_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), GUTTER),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(domain_table)

    story.append(PageBreak())
    return story


def build_buyer_sectors(canonical):
    """Page 6 — Buyer sectors."""
    S = build_styles()
    story = []

    story.append(SectionHeader("06  ·  Buyer Sectors",
                                "15 packages target 6 distinct buyer sectors"))
    story.append(Spacer(1, 8))

    # Count by buyer sector (extract from buyer field)
    sectors = {}
    for pkg_id, pkg in canonical["packages"].items():
        buyer = pkg.get("buyer", "Other")
        # Normalize sector
        if "OEM" in buyer or "shunt" in buyer.lower():
            sector = "Shunt OEMs"
        elif "biotech" in buyer.lower() or "CNS" in buyer:
            sector = "CNS Biotech"
        elif "implantable" in buyer.lower() or "sensor" in buyer.lower():
            sector = "Implantable Sensor Companies"
        elif "imaging" in buyer.lower():
            sector = "Medical Imaging Companies"
        elif "hospital" in buyer.lower():
            sector = "Hospital Systems"
        elif "catheter" in buyer.lower() or "interventional" in buyer.lower():
            sector = "Catheter / Interventional"
        else:
            sector = "Other"

        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(pkg_id)

    # Build sector cards
    sector_cards = []
    for sector, pkgs in sectors.items():
        card = InfoCard(sector,
                        f"<b>{len(pkgs)} package(s):</b> {', '.join(pkgs)}",
                        evidence_state="COMPUTATIONAL",
                        width=COL_W, height=None, bg=ACCENT_LIGHT, edge=ACCENT,
                        title_color=ACCENT)
        sector_cards.append(card)

    rows = []
    for i in range(0, len(sector_cards), 2):
        left = sector_cards[i]
        right = sector_cards[i+1] if i+1 < len(sector_cards) else Paragraph("", S["Body"])
        rows.append([left, right])

    sector_table = Table(rows, colWidths=[COL_W, COL_W])
    sector_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), GUTTER),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sector_table)

    story.append(PageBreak())
    return story


def build_validation_capital(canonical):
    """Page 7 — Validation capital required."""
    S = build_styles()
    story = []

    story.append(SectionHeader("07  ·  Validation Capital Required",
                                "Total capital to commission decisive experiments for all 15 packages"))
    story.append(Spacer(1, 8))

    # Sum cost estimates (parse ranges)
    total_low = 0
    total_high = 0
    pkg_costs = []
    for pkg_id, pkg in canonical["packages"].items():
        cost_str = pkg.get("cost_estimate", "$0")
        # Parse "$X-YK" or "$X-YK"
        import re
        match = re.search(r'\$(\d+)-(\d+)K', cost_str)
        if match:
            low = int(match.group(1))
            high = int(match.group(2))
            total_low += low
            total_high += high
            pkg_costs.append((pkg_id, low, high))
        else:
            pkg_costs.append((pkg_id, 0, 0))

    # Big total
    total_card = InfoCard(
        "TOTAL DECISIVE-EXPERIMENT CAPITAL (15 packages)",
        f"<b>${total_low}K - ${total_high}K</b> (estimated, ESTIMATED tier)<br/>"
        f"<b>Average per package:</b> ${total_low//15}K - ${total_high//15}K<br/>"
        f"<b>Range per package:</b> $2K (lowest, P-16) to $60K (highest, P-29)<br/>"
        f"<b>Time horizon:</b> 1-12 weeks per package (ESTIMATED)",
        evidence_state="MODELLED",
        width=CONTENT_W, height=80, bg=ACCENT_LIGHT, edge=ACCENT,
        title_color=ACCENT
    )
    story.append(total_card)
    story.append(Spacer(1, 8))

    # Per-package cost table
    cost_data = [["Package", "Low ($K)", "High ($K)", "Time"]]
    for pkg_id, pkg in canonical["packages"].items():
        cost_str = pkg.get("cost_estimate", "$0")
        import re
        match = re.search(r'\$(\d+)-(\d+)K', cost_str)
        low = match.group(1) if match else "?"
        high = match.group(2) if match else "?"
        time_str = pkg.get("timeline_estimate", "—")[:30]
        cost_data.append([
            Paragraph(f"<b>{pkg_id}</b>", S["TableCellSmall"]),
            Paragraph(low, S["TableCellSmall"]),
            Paragraph(high, S["TableCellSmall"]),
            Paragraph(time_str, S["TableCellSmall"]),
        ])
    cost_table = Table(cost_data, colWidths=[20*mm, 25*mm, 25*mm, CONTENT_W - 70*mm])
    cost_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_700),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "BodySans-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, INK_050]),
    ]))
    story.append(cost_table)

    story.append(PageBreak())
    return story


def build_top_opportunities(canonical):
    """Page 8 — Top five opportunities."""
    S = build_styles()
    story = []

    story.append(SectionHeader("08  ·  Top Five Opportunities",
                                "Ranked by combined evidence strength + buyer demand signal"))
    story.append(Spacer(1, 8))

    # Rank by evidence tier + maturity
    tier_scores = {"T2-CONFIRMED": 4, "T2-CONDITIONAL": 3, "T1_MODEL_PREDICTED": 2, "T1": 1}
    mat_scores = {"TRANSFER_READY": 4, "VALIDATION_STAGE": 3, "ENGINEERING": 2, "RESEARCH": 1}

    scored = []
    for pkg_id, pkg in canonical["packages"].items():
        tier = pkg.get("evidence_tier", "T1")
        mat = pkg.get("maturity", "RESEARCH")
        score = tier_scores.get(tier, 1) + mat_scores.get(mat, 1)
        # Bonus for 0 prior-art hits (completely novel)
        if "0 specific" in pkg.get("patent_landscape", "") or "0 patent" in pkg.get("patent_landscape", ""):
            score += 1
        scored.append((score, pkg_id, pkg))
    scored.sort(reverse=True)

    # Top 5
    for rank, (score, pkg_id, pkg) in enumerate(scored[:5], 1):
        # Card with rank
        body = (f"<b>Rank {rank}  ·  Score: {score}/8</b><br/>"
                f"<b>Evidence tier:</b> {pkg.get('evidence_tier', '—')}<br/>"
                f"<b>Maturity:</b> {pkg.get('maturity', '—')}<br/>"
                f"<b>Patent landscape:</b> {pkg.get('patent_landscape', '—')}<br/>"
                f"<b>Decisive experiment:</b> {pkg.get('decisive_experiment', '—')}<br/>"  # R370U-U6: no truncation
                f"<b>Cost:</b> {pkg.get('cost_estimate', '—')}  ·  <b>Time:</b> {pkg.get('timeline_estimate', '—')}<br/>"
                f"<b>Primary action:</b> {pkg.get('primary_action', '—')}")
        card = InfoCard(f"{pkg_id}  ·  {pkg['name']}", body,
                        evidence_state=evidence_state_for_tier(pkg.get("evidence_tier", "T1")),
                        width=CONTENT_W, height=None,
                        bg=ACCENT_LIGHT if rank == 1 else INK_050,
                        edge=ACCENT if rank == 1 else INK_300,
                        title_color=ACCENT if rank == 1 else BRAND_700)
        story.append(card)
        story.append(Spacer(1, 4))

    story.append(PageBreak())
    return story


def build_risk_map(canonical):
    """Page 9 — Portfolio risk map."""
    S = build_styles()
    story = []

    story.append(SectionHeader("09  ·  Portfolio Risk Map",
                                "Risk levels across 15 packages"))
    story.append(Spacer(1, 8))

    # Count by risk
    risk_levels = {}
    for pkg_id, pkg in canonical["packages"].items():
        r = pkg.get("risk_level", "MEDIUM")
        # Normalize
        if "VERY" in r.upper():
            r_norm = "VERY HIGH"
        elif "HIGH" in r.upper():
            r_norm = "HIGH"
        elif "MEDIUM" in r.upper():
            r_norm = "MEDIUM"
        else:
            r_norm = "LOW"
        if r_norm not in risk_levels:
            risk_levels[r_norm] = []
        risk_levels[r_norm].append(pkg_id)

    # Build risk tiers
    risk_tiers = [
        ("VERY HIGH", risk_levels.get("VERY HIGH", []),
         colors.HexColor("#B71C1C"), colors.HexColor("#FFEBEE")),
        ("HIGH", risk_levels.get("HIGH", []),
         colors.HexColor("#C62828"), colors.HexColor("#FFEBEE")),
        ("MEDIUM", risk_levels.get("MEDIUM", []),
         colors.HexColor("#F57F17"), colors.HexColor("#FFF8E1")),
        ("LOW", risk_levels.get("LOW", []),
         colors.HexColor("#1B5E20"), colors.HexColor("#E8F5E9")),
    ]

    for label, pkgs, fg, bg in risk_tiers:
        if not pkgs:
            continue
        body = f"<b>{len(pkgs)} package(s):</b> {', '.join(pkgs)}"
        card = InfoCard(f"RISK: {label}", body,
                        evidence_state="ASSUMED",
                        width=CONTENT_W, height=None, bg=bg, edge=fg,
                        title_color=fg)
        story.append(card)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 6))

    # Risk concentration callout
    risk_conc_text = (
        "<b>Risk concentration:</b> P-29 (MR Flow Quantification Sensor) carries VERY HIGH risk "
        "due to unverified miniaturization feasibility + patent landscape unknown. "
        "P-15-R1, P-21-R1, P-22-R1, P-27-R1 carry HIGH risk as R1 repair candidates "
        "whose original architectures were FALSIFIED — the R1 mechanism is MODELLED, not verified. "
        "P-04 carries HIGH risk due to biology blockers (4/8 parameters unresolved). "
        "The remaining packages carry MEDIUM risk — typical for research-stage technologies."
    )
    risk_conc_card = InfoCard("RISK CONCENTRATION", risk_conc_text,
                              evidence_state=None,
                              width=CONTENT_W, height=None, bg=INK_050)
    story.append(risk_conc_card)

    story.append(PageBreak())
    return story


def build_learning_loop_explainer():
    """Page 10 — How the AI learning loop works."""
    S = build_styles()
    story = []

    story.append(SectionHeader("10  ·  How the AI Learning Loop Works",
                                "Designed to evolve — not a static invention report"))
    story.append(Spacer(1, 8))

    # Big learning loop visual
    loop = LearningLoopFooter(current_state="PORTFOLIO (awaiting reality)",
                              width=CONTENT_W, height=80)
    story.append(loop)
    story.append(Spacer(1, 10))

    # 8-stage explanation
    stages_text = (
        "<b>1. CURRENT PACKAGE</b> — this dossier (computational model + IP + commercial logic). "
        "Reality has not been observed.<br/><br/>"
        "<b>2. BUYER EVALUATION</b> — buyer's R&D team reviews the dossier. "
        "Real buyer feedback is captured (not machine-generated).<br/><br/>"
        "<b>3. EXPERIMENT</b> — buyer commissions the decisive experiment defined on page 7. "
        "Protocol is pre-registered; thresholds are frozen BEFORE execution.<br/><br/>"
        "<b>4. REAL DATA</b> — physical measurements from the experiment. "
        "This is the first reality input into the loop.<br/><br/>"
        "<b>5. BELIEF UPDATE</b> — AI updates posterior belief in the mechanism. "
        "PASS upgrades maturity (RESEARCH → VALIDATION_STAGE). "
        "FAIL moves package to cemetery with reusable negative knowledge.<br/><br/>"
        "<b>6. KNOWLEDGE</b> — new knowledge atom (KA) is created. "
        "Example: P-25 cemetery entry produced KA-014 (biofouling-limited sensor constraint).<br/><br/>"
        "<b>7. NEXT EXPERIMENT</b> — AI prioritizes the next experiment using Expected Information Gain (EIG). "
        "The next experiment is chosen to maximally resolve remaining uncertainty.<br/><br/>"
        "<b>8. PACKAGE V2</b> — dossier is regenerated with updated evidence state. "
        "Buyer receives the new dossier with explicit diff from V1."
    )
    stages_card = InfoCard("THE 8-STAGE LEARNING LOOP", stages_text,
                           evidence_state=None,
                           width=CONTENT_W, height=None, bg=BRAND_100, edge=BRAND_500,
                           title_color=BRAND_900)
    story.append(stages_card)
    story.append(Spacer(1, 8))

    # Current state
    current_text = (
        "<b>Current state:</b> Stage 1 (CURRENT PACKAGE) for all 15 packages. "
        "Stages 2-8 require a real buyer. "
        "<b>REALITY NOT YET OBSERVED</b> is marked on every package. "
        "Synthetic loop has been verified 3 times (Article XXXVII); "
        "real loop = 0 (WAITING_FOR_REALITY)."
    )
    current_card = InfoCard("CURRENT LOOP STATE", current_text,
                            evidence_state="UNKNOWN",
                            width=CONTENT_W, height=None, bg=EV_UNKNOWN_BG, edge=EV_UNKNOWN,
                            title_color=EV_UNKNOWN)
    story.append(current_card)

    story.append(PageBreak())
    return story


def build_package_cards(canonical):
    """Page 11 — Individual package mini-cards."""
    S = build_styles()
    story = []

    story.append(SectionHeader("11  ·  Individual Package Cards",
                                "15 mini-cards — each links to a full Executive Dossier"))
    story.append(Spacer(1, 6))

    # Build 3-column grid of mini cards
    mini_cards = []
    for pkg_id, pkg in canonical["packages"].items():
        # Mini card: ID + name + maturity + tier + 1-line value prop
        mini_body = (
            f"<b>{pkg['name']}</b><br/>"
            f"<font size='6' color='#64748B'>{pkg.get('subtitle', '')[:80]}</font><br/>"
            f"<b>Maturity:</b> {pkg.get('maturity', '—')}  ·  "
            f"<b>Tier:</b> {pkg.get('evidence_tier', '—')[:15]}<br/>"
            f"<b>Cost:</b> {pkg.get('cost_estimate', '—')[:25]}"
        )
        card = InfoCard(pkg_id, mini_body,
                        evidence_state=evidence_state_for_tier(pkg.get("evidence_tier", "T1")),
                        width=(CONTENT_W - 2 * 4) / 3, height=None,
                        bg=INK_050)
        mini_cards.append(card)

    # Arrange in 3 columns
    rows = []
    for i in range(0, len(mini_cards), 3):
        row = mini_cards[i:i+3]
        while len(row) < 3:
            row.append(Paragraph("", S["Body"]))
        rows.append(row)

    grid = Table(rows, colWidths=[(CONTENT_W - 2 * 4) / 3] * 3)
    grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(grid)

    # Footer
    story.append(Spacer(1, 8))
    footer_text = (
        "<b>Each package has three disclosure levels:</b><br/>"
        "Level 1 — 1-page Buyer Decision Card (non-confidential, cold outreach)<br/>"
        "Level 2 — 8-12 page Executive Dossier (this portfolio's per-package deliverable)<br/>"
        "Level 3 — Full machine-readable data room (TECHNICAL_PACKAGE.json + 8 supporting files)"
    )
    footer_card = InfoCard("DISCLOSURE LEVELS", footer_text,
                           evidence_state=None,
                           width=CONTENT_W, height=None, bg=BRAND_100, edge=BRAND_500,
                           title_color=BRAND_900)
    story.append(footer_card)

    return story


# ----------------------------------------------------------------------------
# Master generator
# ----------------------------------------------------------------------------

def generate_portfolio_cover(canonical, constitution_sha, output_path=None):
    """Generate the portfolio cover PDF."""
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "Portfolio_15_Technologies.pdf")

    doc = BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title="CereVasc eShunt 15-Technology Portfolio",
        author="CereVasc eShunt Technology-Transfer Portfolio",
    )

    cover_frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, CONTENT_H,
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                        showBoundary=0, id="cover_frame")
    cover_template = PageTemplate(id="cover", frames=[cover_frame],
                                   onPage=_cover_page)

    inside_frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, CONTENT_H - 6,
                          leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                          showBoundary=0, id="inside_frame")
    inside_template = PageTemplate(id="inside", frames=[inside_frame],
                                    onPage=_inside_page)

    doc.addPageTemplates([cover_template, inside_template])

    story = []
    story.extend(build_portfolio_cover())
    story.append(NextPageTemplate("inside"))
    story.extend(build_thesis())
    story.extend(build_package_map(canonical))
    story.extend(build_maturity_map(canonical))
    story.extend(build_domains(canonical))
    story.extend(build_buyer_sectors(canonical))
    story.extend(build_validation_capital(canonical))
    story.extend(build_top_opportunities(canonical))
    story.extend(build_risk_map(canonical))
    story.extend(build_learning_loop_explainer())
    story.extend(build_package_cards(canonical))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    import json
    with open("/home/z/my-project/canonical_data/canonical_15_packages_adapted.json") as f:
        canonical = json.load(f)
    constitution_sha = canonical.get("constitution_sha256", "")
    path = generate_portfolio_cover(canonical, constitution_sha)
    print(f"Portfolio: {path}")

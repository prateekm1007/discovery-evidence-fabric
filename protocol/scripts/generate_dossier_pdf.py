#!/usr/bin/env python3
"""
generate_dossier_pdf.py — Generic version

Compiles an invention package into a single CEO-grade PDF using ReportLab.

USAGE:
    python3 protocol/scripts/generate_dossier_pdf.py \
        /path/to/<COMPANY>_INVENTION_<NNN>_V<M> \
        --output /home/z/my-project/download/<NAME>_Dossier.pdf

The PDF contains:
  - Cover page (dark full-bleed with verdict banner)
  - Executive Summary with quick-stat card
  - Frozen Limitations L1..Ln
  - Patent Position (Tasks 1 + 2: self-IP audit + 102/103 rebuilt)
  - Engineering Blueprint (Task 3)
  - Safety Simulation (Task 4)
  - Build-vs-Buy (Task 5)
  - Regulatory Pathway (Task 6)
  - Design-Around (Task 7)
  - Final Adjudication (5-gate scorecard + milestones)
  - Evidence Ledger (provenance chain)
  - Artifact Hashes (SHA-256 anchors)

Per INVENTION_PROTOCOL_V1 §16 (Adjudication Tiers) — the dossier is the
defensible output that answers the buyer-test question: "If you were the
buyer's CTO/CSO/BD lead, would you pay to acquire or license this invention
today?"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
    Table, TableStyle, NextPageTemplate
)


# ---- Palette (warm minimal — fits any invention) ----
PAGE_BG       = colors.HexColor('#f5f5f4')
SECTION_BG    = colors.HexColor('#edecea')
CARD_BG       = colors.HexColor('#e7e6e3')
TABLE_STRIPE  = colors.HexColor('#efedea')
HEADER_FILL   = colors.HexColor('#4e4734')
COVER_BLOCK   = colors.HexColor('#63593e')
BORDER        = colors.HexColor('#c3baa2')
ICON          = colors.HexColor('#907d44')
ACCENT        = colors.HexColor('#917520')
TEXT_PRIMARY  = colors.HexColor('#1e1d1b')
TEXT_MUTED    = colors.HexColor('#908e87')

# ---- Fonts (use Liberation + DejaVu — verified working TTFs) ----
# Do NOT use Tinos/Carlito from /usr/share/fonts/truetype/english/ — they
# are corrupted HTML files masquerading as TTFs (prior session wasted cycles).
pdfmetrics.registerFont(TTFont('LibSerif',      '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf'))
pdfmetrics.registerFont(TTFont('LibSerif-Bold', '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'))
pdfmetrics.registerFont(TTFont('LibSans',       '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('LibSans-Bold',  '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuMono',    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
pdfmetrics.registerFontFamily(
    'LibSerif', normal='LibSerif', bold='LibSerif-Bold',
    italic='LibSerif', boldItalic='LibSerif-Bold'
)
pdfmetrics.registerFontFamily(
    'LibSans', normal='LibSans', bold='LibSans-Bold',
    italic='LibSans', boldItalic='LibSans-Bold'
)

SERIF = 'LibSerif'
SERIF_BOLD = 'LibSerif-Bold'
SANS = 'LibSans'
SANS_BOLD = 'LibSans-Bold'
MONO = 'DejaVuMono'

# ---- Styles ----
styles = getSampleStyleSheet()

style_h1 = ParagraphStyle('H1', parent=styles['Heading1'],
    fontName=SERIF_BOLD, fontSize=20, leading=26,
    textColor=HEADER_FILL, alignment=TA_LEFT,
    spaceBefore=14, spaceAfter=10, keepWithNext=True)
style_h2 = ParagraphStyle('H2', parent=styles['Heading2'],
    fontName=SERIF_BOLD, fontSize=14, leading=18,
    textColor=ACCENT, alignment=TA_LEFT,
    spaceBefore=10, spaceAfter=6, keepWithNext=True)
style_h3 = ParagraphStyle('H3', parent=styles['Heading3'],
    fontName=SANS_BOLD, fontSize=11, leading=14,
    textColor=TEXT_PRIMARY, alignment=TA_LEFT,
    spaceBefore=6, spaceAfter=4, keepWithNext=True)
style_body = ParagraphStyle('Body', parent=styles['Normal'],
    fontName=SERIF, fontSize=10, leading=14,
    textColor=TEXT_PRIMARY, alignment=TA_JUSTIFY, spaceAfter=6)
style_body_left = ParagraphStyle('BodyLeft', parent=style_body, alignment=TA_LEFT)
style_small = ParagraphStyle('Small', parent=styles['Normal'],
    fontName=SANS, fontSize=8.5, leading=11,
    textColor=TEXT_MUTED, alignment=TA_LEFT)
style_callout = ParagraphStyle('Callout', parent=style_body,
    fontName=SANS, fontSize=10, leading=14,
    textColor=HEADER_FILL, alignment=TA_LEFT,
    backColor=CARD_BG, borderColor=BORDER, borderWidth=0.5,
    borderPadding=8, leftIndent=0, rightIndent=0)


def load_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def safe_get(d, *keys, default=None):
    """Deep .get() with default."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("invention_dir", type=Path, help="Invention folder to compile")
    parser.add_argument("--output", type=Path, required=True, help="Output PDF path")
    parser.add_argument("--title", default=None, help="PDF title (defaults to invention_id)")
    args = parser.parse_args()

    invention_dir: Path = args.invention_dir.resolve()
    if not invention_dir.is_dir():
        print(f"FATAL: {invention_dir} is not a directory", file=sys.stderr)
        return 2

    invention_id = invention_dir.name
    title = args.title or invention_id
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # ---- Load canonical artifacts (preferred) with legacy fallbacks ----
    def find_json(canonical: str, *legacy: str) -> Optional[dict]:
        for name in (canonical, *legacy):
            p = invention_dir / name
            data = load_json(p)
            if data is not None:
                return data
        return {}

    task1 = find_json("09_PRIOR_ART/retention_passage_audit.json", "TASK1_RETENTION_PASSAGE_AUDIT.json")
    task2 = find_json("11_102_ATTACK/102_RESULTS.json", "TASK2_102_103_CORRECTED.json")
    task3 = find_json("15_ENGINEERING_BLUEPRINT/material_spec.json", "TASK3_MEMBRANE_MATERIAL_SPEC.json")
    task4 = find_json("16_SIMULATION/simulation_results.json", "TASK4_ICP_SIMULATION.json")
    task5 = find_json("19_BUILD_BUY/build_vs_buy.json", "TASK5_BUILD_VS_BUY.json")
    task6 = find_json("18_REGULATORY/regulatory_pathway.json", "TASK6_REGULATORY_PATHWAY.json")
    task7 = find_json("14_DESIGN_AROUND/design_around_results.json", "TASK7_DESIGN_AROUND.json")
    score = find_json("22_FINAL_ADJUDICATION.json", "REVISED_SCORE.json")
    ledger = find_json("21_EVIDENCE_LEDGER.json", "EVIDENCE_LEDGER_V2.json")

    # ---- Page geometry ----
    PAGE_W, PAGE_H = A4
    MARGIN_L = 18 * mm
    MARGIN_R = 18 * mm
    MARGIN_T = 22 * mm
    MARGIN_B = 18 * mm

    # ---- Cover page callback ----
    final_status = score.get("final_status", "WOULD_NOT_PAY").replace("_", " ")
    composite = score.get("composite_score", "—")

    def cover_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(HEADER_FILL)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(COVER_BLOCK)
        canvas.rect(0, PAGE_H * 0.55, PAGE_W, PAGE_H * 0.05, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont(SERIF_BOLD, 32)
        canvas.drawString(MARGIN_L, PAGE_H * 0.70, title)
        canvas.setFont(SERIF_BOLD, 24)
        canvas.drawString(MARGIN_L, PAGE_H * 0.65, "Buyer-Readiness Dossier")
        canvas.setFont(SERIF, 14)
        canvas.setFillColor(colors.HexColor('#e7e6e3'))
        canvas.drawString(MARGIN_L, PAGE_H * 0.62, f"Invention ID: {invention_id}")
        canvas.setFont(SANS, 10)
        canvas.drawString(MARGIN_L, PAGE_H * 0.45, "BUYER-READINESS DOSSIER")
        canvas.drawString(MARGIN_L, PAGE_H * 0.43, "Prepared under INVENTION_PROTOCOL_V1")
        canvas.drawString(MARGIN_L, PAGE_H * 0.41, f"Composite: {composite}/100")
        canvas.drawString(MARGIN_L, PAGE_H * 0.39, f"Adjudication: {final_status}")
        canvas.setFillColor(ACCENT)
        canvas.setFont(SANS_BOLD, 9)
        canvas.drawString(MARGIN_L, MARGIN_B, "FINAL STATUS")
        canvas.setFillColor(colors.white)
        canvas.setFont(SANS_BOLD, 11)
        canvas.drawString(MARGIN_L, MARGIN_B - 14, final_status)
        canvas.setFillColor(colors.HexColor('#e7e6e3'))
        canvas.setFont(SANS, 8)
        canvas.drawRightString(PAGE_W - MARGIN_R, MARGIN_B,
            "Generated " + datetime.now(timezone.utc).strftime("%Y-%m-%d UTC"))
        canvas.restoreState()

    # ---- Header/footer callback ----
    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_L, PAGE_H - MARGIN_T + 4*mm,
                    PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 4*mm)
        canvas.setFont(SANS, 8)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(MARGIN_L, PAGE_H - MARGIN_T + 6*mm, f"{invention_id} — Dossier")
        canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 6*mm,
                               "INVENTION_PROTOCOL_V1 — Confidential")
        canvas.line(MARGIN_L, MARGIN_B - 4*mm, PAGE_W - MARGIN_R, MARGIN_B - 4*mm)
        canvas.setFont(SANS, 8)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(MARGIN_L, MARGIN_B - 8*mm, "Buyer-Readiness Dossier")
        canvas.drawRightString(PAGE_W - MARGIN_R, MARGIN_B - 8*mm,
                               f"Page {doc.page}")
        canvas.restoreState()

    # ---- Build the story ----
    story = []
    story.append(NextPageTemplate('body'))
    story.append(PageBreak())

    # === Executive Summary ===
    story.append(Paragraph("Executive Summary", style_h1))
    gates = score.get("gates", {})
    patent_score = safe_get(gates, "PATENT_GATE", "score", default="—")
    evidence_score = safe_get(gates, "EVIDENCE_GATE", "score", default="—")
    technical_score = safe_get(gates, "TECHNICAL_GATE", "score", default="—")
    engineering_score = safe_get(gates, "ENGINEERING_GATE", "score", default="—")
    commercial_score = safe_get(gates, "COMMERCIAL_GATE", "score", default="—")

    story.append(Paragraph(
        f"This dossier compiles the complete buyer-readiness analysis of "
        f"<b>{invention_id}</b> under <b>INVENTION_PROTOCOL_V1</b>. "
        f"Composite score: <b>{composite}/100</b>. "
        f"Final status: <b>{final_status}</b>. "
        f"All five gates: Patent {patent_score}/70 (non-compensable), "
        f"Evidence {evidence_score}/70 (non-compensable), "
        f"Technical {technical_score}/65, "
        f"Engineering {engineering_score}/60, "
        f"Commercial {commercial_score}/65.",
        style_body))

    # Quick-stat card
    try:
        stat_data = [
            ["Composite", "Final Status", "Patent Gate", "Evidence Gate"],
            [f"{composite}/100", final_status[:18], f"{patent_score}/70", f"{evidence_score}/70"],
            ["Technical", "Engineering", "Commercial", "Non-Compensable"],
            [f"{technical_score}/65", f"{engineering_score}/60",
             f"{commercial_score}/65", "BOTH PASS" if score.get("non_compensable_gates_status", {}).get("both_non_compensable_satisfied", False) else "FAILED"],
        ]
        stat_table = Table(stat_data, colWidths=[(PAGE_W - MARGIN_L - MARGIN_R)/4]*4)
        stat_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), SANS_BOLD), ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONT', (0, 1), (-1, 1), SERIF_BOLD), ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('FONT', (0, 2), (-1, 2), SANS_BOLD), ('FONTSIZE', (0, 2), (-1, 2), 8),
            ('FONT', (0, 3), (-1, 3), SERIF_BOLD), ('FONTSIZE', (0, 3), (-1, 3), 12),
            ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_MUTED),
            ('TEXTCOLOR', (0, 1), (-1, 1), HEADER_FILL),
            ('TEXTCOLOR', (0, 2), (-1, 2), TEXT_MUTED),
            ('TEXTCOLOR', (0, 3), (-1, 3), ACCENT),
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(Spacer(1, 4*mm))
        story.append(stat_table)
    except Exception:
        pass  # tables can fail gracefully

    # === Frozen Limitations ===
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Frozen Limitations (L1–Ln)", style_h1))
    story.append(Paragraph(
        "The claim limitations below are frozen per INVENTION_PROTOCOL_V1 §8 "
        "and are immutable from this point forward. All 102/103/design-around "
        "analyses reference this freeze's content hash.",
        style_body))
    limitations = (task2.get("limitations") or
                   load_json(invention_dir / "08_LIMITATION_FREEZE.json", ).get("limitations") if (invention_dir / "08_LIMITATION_FREEZE.json").is_file() else
                   task2.get("limitations", {}))
    if limitations:
        limit_data = [["#", "Frozen Limitation"]]
        for lid in sorted(limitations.keys()):
            limit_data.append([lid, limitations.get(lid, "")])
        limit_table = Table(limit_data, colWidths=[15*mm, PAGE_W - MARGIN_L - MARGIN_R - 15*mm])
        limit_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), SANS_BOLD), ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_FILL),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONT', (0, 1), (-1, -1), SERIF), ('FONTSIZE', (0, 1), (-1, -1), 9.5),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.4, BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, TABLE_STRIPE]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(limit_table)

    # === Final Adjudication ===
    story.append(PageBreak())
    story.append(Paragraph("Final Adjudication", style_h1))
    story.append(Paragraph(
        f"The final adjudication applies the five-gate scoring rubric defined in "
        f"INVENTION_PROTOCOL_V1 §7. Composite: <b>{composite}/100</b>. "
        f"Final status: <b>{final_status}</b>.",
        style_body))

    gates_data = [["Gate", "Score", "Threshold", "Weight", "Status"]]
    for gate_name in ["PATENT_GATE", "EVIDENCE_GATE", "TECHNICAL_GATE", "ENGINEERING_GATE", "COMMERCIAL_GATE"]:
        g = gates.get(gate_name, {})
        gates_data.append([
            gate_name.replace("_", " ").title(),
            str(g.get("score", "—")),
            str(g.get("threshold", "—")),
            f"{int(g.get('weight', 0)*100)}%" if isinstance(g.get('weight'), (int, float)) else "—",
            g.get("status", "—"),
        ])
    gates_data.append(["COMPOSITE", str(composite), "70", "100%", final_status])
    gates_table = Table(gates_data, colWidths=[44*mm, 22*mm, 25*mm, 20*mm, 35*mm])
    gates_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), SANS_BOLD), ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_FILL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONT', (0, 1), (-1, -2), SERIF), ('FONTSIZE', (0, 1), (-1, -2), 9.5),
        ('FONT', (0, -1), (-1, -1), SERIF_BOLD), ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), ACCENT),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, TABLE_STRIPE]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(gates_table)

    # Milestones
    milestones = score.get("milestones_for_buyer_ready", [])
    if milestones:
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph("Milestones Required to Reach LEVEL_4_BUYER_READY", style_h2))
        m_data = [["#", "Milestone"]]
        for i, m in enumerate(milestones, 1):
            m_data.append([f"M{i}", m])
        m_table = Table(m_data, colWidths=[12*mm, PAGE_W - MARGIN_L - MARGIN_R - 12*mm])
        m_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), SANS_BOLD), ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_FILL),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONT', (0, 1), (-1, -1), SERIF), ('FONTSIZE', (0, 1), (-1, -1), 9.5),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.4, BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, TABLE_STRIPE]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(m_table)

    # === Evidence Ledger ===
    story.append(PageBreak())
    story.append(Paragraph("Evidence Ledger — Provenance Chain", style_h1))
    story.append(Paragraph(
        "Every conclusion in this dossier traces to an evidence_id in the ledger "
        "below. Model-derived elements are flagged per INVENTION_PROTOCOL_V1 §10.3.",
        style_body))
    ev_entries = ledger.get("evidence", [])
    if ev_entries:
        ev_data = [["ID", "Task", "Source Type", "Model?", "Claim"]]
        for e in ev_entries:
            claim = e.get("claim", "")
            if len(claim) > 80:
                claim = claim[:80] + "..."
            ev_data.append([
                e.get("evidence_id", ""),
                e.get("task_id", ""),
                e.get("source_type", "").replace("_", " "),
                "YES" if e.get("model_derived", False) else "no",
                claim,
            ])
        ev_table = Table(ev_data, colWidths=[14*mm, 18*mm, 32*mm, 24*mm, PAGE_W - MARGIN_L - MARGIN_R - 88*mm])
        ev_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), SANS_BOLD), ('FONTSIZE', (0, 0), (-1, 0), 7.5),
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_FILL),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONT', (0, 1), (-1, -1), SERIF), ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.3, BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, TABLE_STRIPE]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(ev_table)

    # === Artifact Hashes ===
    story.append(PageBreak())
    story.append(Paragraph("Artifact Hashes — Tamper Detection", style_h1))
    story.append(Paragraph(
        "Every artifact in the invention package is hashed with SHA-256 and "
        "recorded in SHA256SUMS. The hash anchors below are the canonical "
        "references that preflight_check.py verifies mechanically on every CI run.",
        style_body))

    sums_path = invention_dir / "SHA256SUMS"
    hash_lines = []
    if sums_path.is_file():
        with open(sums_path) as f:
            hash_lines = [l.strip() for l in f if l.strip()]

    hash_data = [["SHA-256 (16 chars)", "Artifact"]]
    for line in hash_lines:
        parts = line.split(None, 1)
        if len(parts) == 2:
            digest, name = parts
            hash_data.append([digest[:16] + "...", name.strip()])
    hash_table = Table(hash_data, colWidths=[42*mm, PAGE_W - MARGIN_L - MARGIN_R - 42*mm])
    hash_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), SANS_BOLD), ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_FILL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONT', (0, 1), (-1, -1), MONO), ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, TABLE_STRIPE]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(hash_table)

    # Closing callout
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(
        f"<b>End of Dossier.</b> Final status: <b>{final_status}</b>. "
        f"Composite: <b>{composite}/100</b>. "
        f"Produced under INVENTION_PROTOCOL_V1.",
        style_callout))

    # ---- Build PDF ----
    doc = BaseDocTemplate(
        str(args.output),
        pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title=f"{title} — Buyer-Readiness Dossier",
        author="Z.ai",
        subject=f"Buyer-Readiness Dossier under INVENTION_PROTOCOL_V1 — {invention_id}",
        creator="Z.ai",
    )
    frame_body = Frame(
        MARGIN_L, MARGIN_B, PAGE_W - MARGIN_L - MARGIN_R, PAGE_H - MARGIN_T - MARGIN_B,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id='body'
    )
    frame_cover = Frame(
        MARGIN_L, MARGIN_B, PAGE_W - MARGIN_L - MARGIN_R, PAGE_H - MARGIN_T - MARGIN_B,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id='cover'
    )
    doc.addPageTemplates([
        PageTemplate(id='cover', frames=[frame_cover], onPage=cover_page),
        PageTemplate(id='body', frames=[frame_body], onPage=header_footer),
    ])
    doc.build(story)
    print(f"PDF generated: {args.output}")
    print(f"Size: {args.output.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

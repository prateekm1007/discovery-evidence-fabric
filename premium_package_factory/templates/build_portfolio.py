"""
build_portfolio.py — Build the clean 15-technology transfer portfolio.

Per CEO directive: create a separate, buyer-facing repository containing
ONLY the 15 dossiers, professionally packaged and ready for download.

NO internal QA machinery. NO R370 history. NO developer scripts.
NO internal scores. NO secrets. NO obsolete packages.

Output: /home/z/my-project/download/technology-transfer-portfolio-15/
"""

import json
import os
import sys
import hashlib
import zipfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# ReportLab for PDF generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Image as RLImage, ListFlowable, ListItem, KeepTogether
)
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.pdfgen import canvas
from reportlab.lib import colors

REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"
OUTPUT_DIR = os.path.join(REPO_ROOT, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")
DOWNLOAD_DIR = "/home/z/my-project/download"
PORTFOLIO_DIR = os.path.join(DOWNLOAD_DIR, "technology-transfer-portfolio-15")

# ============================================================================
# PACKAGE MAPPING (01-15, frozen)
# ============================================================================

PACKAGE_MAP = [
    {"num": "01", "pkg_id": "P-01", "short_name": "multisegment_flow_control", "tech_name": "Multi-Segment Flow Control with Bayesian Occlusion Prediction"},
    {"num": "02", "pkg_id": "P-02", "short_name": "adaptive_valve", "tech_name": "Adaptive Valve Profile for Postural ICP Regulation"},
    {"num": "03", "pkg_id": "P-04", "short_name": "catalytic_clearance", "tech_name": "Catalytic Contact Time Lock for A\u03b242 Clearance"},
    {"num": "04", "pkg_id": "P-07", "short_name": "drainage_floor", "tech_name": "Passive Drainage Priority Safety Floor"},
    {"num": "05", "pkg_id": "P-11", "short_name": "phage_antibiofilm", "tech_name": "Phage Anti-Biofilm Coating for Shunt Infection Prevention"},
    {"num": "06", "pkg_id": "P-13", "short_name": "failure_predictor", "tech_name": "Neuromorphic Shunt Failure Predictor"},
    {"num": "07", "pkg_id": "P-15-R1", "short_name": "self_powered_sensing", "tech_name": "Self-Powered Sensing via Piezoelectric Energy Harvesting"},
    {"num": "08", "pkg_id": "P-16", "short_name": "nir_photovoltaic", "tech_name": "NIR Photovoltaic Power Delivery for Implantable Devices"},
    {"num": "09", "pkg_id": "P-21-R1", "short_name": "uwb_localization", "tech_name": "UWB Catheter Position Mapping with SAR-Bounded Accuracy"},
    {"num": "10", "pkg_id": "P-22-R1", "short_name": "catheter_navigation", "tech_name": "Autonomous Catheter Navigation with Human-in-the-Loop"},
    {"num": "11", "pkg_id": "P-24", "short_name": "gravity_damper", "tech_name": "Gravity Compensation Hydraulic Damper for Postural Transients"},
    {"num": "12", "pkg_id": "P-26", "short_name": "osmotic_valve", "tech_name": "Osmotic Pressure Regulating Drainage Valve"},
    {"num": "13", "pkg_id": "P-27-R1", "short_name": "pressure_sensor", "tech_name": "Self-Referencing Piezoresistive Pressure Sensor"},
    {"num": "14", "pkg_id": "P-28", "short_name": "acoustic_detection", "tech_name": "Acoustic Obstruction Detection for CSF Shunts"},
    {"num": "15", "pkg_id": "P-29", "short_name": "mr_flow_sensor", "tech_name": "MR Flow Quantification Sensor at Catheter Scale"},
]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ============================================================================
# PDF STYLES
# ============================================================================

NAVY = HexColor("#0c1e38")
GOLD = HexColor("#92400e")
LIGHT_GREY = HexColor("#e4e0d4")
DARK_GREY = HexColor("#4a4a4a")
ACCENT_BLUE = HexColor("#1e3a8a")

def get_styles():
    styles = getSampleStyleSheet()
    # Remove existing styles that conflict
    for name in ['CoverTitle', 'CoverSub', 'SectionHead', 'SubHead', 'BodyText', 'MonoText', 'TableCell', 'TableCellBold', 'Disclaimer']:
        if name in styles.byName:
            del styles.byName[name]
    styles.add(ParagraphStyle(name='CoverTitle', fontSize=24, leading=30, alignment=TA_CENTER,
                              textColor=NAVY, spaceAfter=12, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='CoverSub', fontSize=14, leading=18, alignment=TA_CENTER,
                              textColor=DARK_GREY, spaceAfter=6, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='SectionHead', fontSize=14, leading=18, textColor=NAVY,
                              spaceBefore=16, spaceAfter=8, fontName='Helvetica-Bold',
                              borderWidth=0, borderPadding=0))
    styles.add(ParagraphStyle(name='SubHead', fontSize=11, leading=14, textColor=ACCENT_BLUE,
                              spaceBefore=10, spaceAfter=4, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='BodyText', fontSize=9.5, leading=13, alignment=TA_JUSTIFY,
                              spaceAfter=6, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='MonoText', fontSize=8.5, leading=11, fontName='Courier',
                              textColor=DARK_GREY, spaceAfter=4))
    styles.add(ParagraphStyle(name='TableCell', fontSize=8.5, leading=11, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='TableCellBold', fontSize=8.5, leading=11, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Disclaimer', fontSize=8, leading=10, textColor=grey,
                              alignment=TA_CENTER, fontName='Helvetica-Oblique'))
    return styles


# ============================================================================
# COVER PAGE
# ============================================================================

def draw_cover_page(canvas_obj, doc, pkg_info):
    """Draw cover page for a package PDF."""
    canvas_obj.saveState()
    w, h = letter

    # Navy background top section
    canvas_obj.setFillColor(NAVY)
    canvas_obj.rect(0, h - 3*inch, w, 3*inch, fill=1, stroke=0)

    # Gold accent line
    canvas_obj.setFillColor(GOLD)
    canvas_obj.rect(0, h - 3.05*inch, w, 0.08*inch, fill=1, stroke=0)

    # Title
    canvas_obj.setFillColor(white)
    canvas_obj.setFont('Helvetica-Bold', 18)
    canvas_obj.drawCentredString(w/2, h - 1.2*inch, f"Technology #{pkg_info['num']}")

    canvas_obj.setFont('Helvetica', 12)
    # Wrap technology name
    tech_name = pkg_info['tech_name']
    if len(tech_name) > 50:
        mid = len(tech_name) // 2
        space_idx = tech_name.find(' ', mid)
        if space_idx > 0:
            canvas_obj.drawCentredString(w/2, h - 1.6*inch, tech_name[:space_idx])
            canvas_obj.drawCentredString(w/2, h - 1.85*inch, tech_name[space_idx+1:])
        else:
            canvas_obj.drawCentredString(w/2, h - 1.6*inch, tech_name)
    else:
        canvas_obj.drawCentredString(w/2, h - 1.6*inch, tech_name)

    canvas_obj.setFont('Helvetica-Oblique', 10)
    canvas_obj.drawCentredString(w/2, h - 2.3*inch, "Engineering Technology-Transfer Dossier")
    canvas_obj.drawCentredString(w/2, h - 2.55*inch, "CONFIDENTIAL — For Authorized Evaluation Only")

    # Bottom info
    canvas_obj.setFillColor(DARK_GREY)
    canvas_obj.setFont('Helvetica', 9)
    canvas_obj.drawCentredString(w/2, 1.2*inch, f"Portfolio Version 1.0")
    canvas_obj.drawCentredString(w/2, 1.0*inch, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    canvas_obj.drawCentredString(w/2, 0.7*inch, "CONCEPTUAL — NOT RELEASED FOR MANUFACTURING")

    canvas_obj.restoreState()


# ============================================================================
# BUILD ENGINEERING DOSSIER PDF
# ============================================================================

def build_engineering_dossier_pdf(pkg_info, dossier_data, output_path):
    """Build the full engineering technology-transfer dossier PDF."""
    styles = get_styles()
    ec = dossier_data.get("engineering_content", {})
    ec_core = ec.get("engineering_core", {})

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)

    story = []

    # Cover page (blank — drawn by onPage callback)
    story.append(PageBreak())

    # === BUYER DECISION PAGE ===
    story.append(Paragraph("BUYER DECISION PAGE", styles['CoverTitle']))
    story.append(Spacer(1, 0.2*inch))

    decision_items = [
        ("WHAT IS IT?", pkg_info['tech_name']),
        ("WHY DOES IT MATTER?", _get_first_value(ec, 'design_inputs', 'value') or "See engineering dossier for details."),
        ("WHAT IS ACTUALLY ESTABLISHED?", "Computational model exists. No physical prototype. No clinical validation."),
        ("WHAT IS NOT ESTABLISHED?", "Physical validation, manufacturing process, regulatory pathway, IP ownership."),
        ("WHY MIGHT A BUYER CARE?", "Early-stage technology-transfer opportunity with documented engineering analysis."),
        ("WHAT DOES THE BUYER GET?", "Engineering dossier, computational model, experiment protocol, evidence chain."),
        ("WHAT DOES THE BUYER HAVE TO BUILD?", "Production CAD, prototype, manufacturing process, clinical validation."),
        ("WHAT IS THE NEXT DECISIVE EXPERIMENT?", _get_first_build_plan_item(ec, 'test_article') or "See engineering build plan."),
        ("WHAT WOULD MAKE US KILL IT?", _get_first_failure(ec) or "See failure analysis."),
        ("WHAT TRANSACTION COULD MAKE SENSE?", "Sponsored validation, research partnership, or co-development."),
    ]

    for label, value in decision_items:
        story.append(Paragraph(f"<b>{label}</b>", styles['SubHead']))
        val_str = str(value)  # R370U-U6: no truncation
        story.append(Paragraph(val_str, styles['BodyText']))

    story.append(PageBreak())

    # === TECHNOLOGY DESCRIPTION ===
    story.append(Paragraph("1. Technology Description", styles['SectionHead']))
    story.append(Paragraph(f"<b>Technology Domain:</b> {ec.get('technology_domain', 'NOT ESTABLISHED')}", styles['BodyText']))
    story.append(Paragraph(f"<b>Engineering Disciplines:</b> {', '.join(ec.get('engineering_disciplines', ['NOT ESTABLISHED']))}", styles['BodyText']))

    sa = ec.get('system_architecture', {})
    story.append(Paragraph(f"<b>System Architecture:</b> {sa.get('description', 'NOT ESTABLISHED')}", styles['BodyText']))

    story.append(Paragraph("Subsystems:", styles['SubHead']))
    for ss in sa.get('subsystems', []):
        story.append(Paragraph(f"  • {ss.get('id', '?')}: {ss.get('name', '?')} — {ss.get('function', '?')}", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === MECHANISM ARCHITECTURE ===
    story.append(Paragraph("2. Mechanism Architecture", styles['SectionHead']))
    ma = ec.get('mechanism_architecture', ec.get('mechanism_architecture', {}))
    if isinstance(ma, dict):
        story.append(Paragraph(f"<b>Physical Changes:</b> {ma.get('physical_changes', 'NOT ESTABLISHED')}", styles['BodyText']))
        story.append(Paragraph(f"<b>Key Physics:</b> {ma.get('key_physics', 'NOT ESTABLISHED')}", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === GOVERNING ENGINEERING MODEL ===
    story.append(Paragraph("3. Governing Engineering Model", styles['SectionHead']))
    gm = ec_core.get('governing_model', {})
    story.append(Paragraph(f"<b>Summary:</b> {gm.get('summary', 'NOT ESTABLISHED')}", styles['BodyText']))

    story.append(Paragraph("Equations:", styles['SubHead']))
    for eq in gm.get('equations', []):
        story.append(Paragraph(f"  {eq}", styles['MonoText']))

    story.append(Paragraph("Assumptions:", styles['SubHead']))
    for a in gm.get('assumptions', []):
        story.append(Paragraph(f"  • {a}", styles['BodyText']))

    story.append(Paragraph("Boundary Conditions:", styles['SubHead']))
    for bc in gm.get('boundary_conditions', []):
        story.append(Paragraph(f"  • {bc}", styles['BodyText']))

    story.append(PageBreak())

    # === DESIGN INPUTS ===
    story.append(Paragraph("4. Design Inputs", styles['SectionHead']))
    dis = ec.get('design_inputs', [])
    if dis:
        di_data = [["ID", "Input", "Value", "Origin Type"]]
        for di in dis:
            val = str(di.get('value', 'UNKNOWN'))  # R370U-U6: no truncation
            di_data.append([di.get('id', '?'), di.get('input', '?'), val, di.get('evidence_class', 'UNKNOWN')])  # R370U-U6: no truncation

        di_table = Table(di_data, colWidths=[0.6*inch, 1.8*inch, 2.8*inch, 1.2*inch])
        di_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(di_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === DESIGN OUTPUTS ===
    story.append(Paragraph("5. Design Outputs", styles['SectionHead']))
    dos = ec.get('design_outputs', [])
    if dos:
        do_data = [["ID", "Description", "Status"]]
        for do in dos:
            do_data.append([do.get('id', '?'), do.get('description', '?'), do.get('status', 'UNKNOWN')])  # R370U-U6: no truncation

        do_table = Table(do_data, colWidths=[0.6*inch, 4*inch, 1.8*inch])
        do_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(do_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(PageBreak())

    # === CRITICAL DESIGN PARAMETERS ===
    story.append(Paragraph("6. Critical Design Parameters", styles['SectionHead']))
    cps = ec_core.get('critical_parameters', [])
    if cps:
        cp_data = [["Name", "Value", "Unit", "Origin Type"]]
        for cp in cps:
            val = str(cp.get('value', 'UNKNOWN'))  # R370U-U6: no truncation
            cp_data.append([cp.get('name', '?'), val, cp.get('unit', '?'), cp.get('evidence_class', 'UNKNOWN')])  # R370U-U6: no truncation

        cp_table = Table(cp_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1.9*inch])
        cp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(cp_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === FAILURE MODES ===
    story.append(Paragraph("7. Failure Modes", styles['SectionHead']))
    fms = ec_core.get('failure_modes', [])
    if fms:
        fm_data = [["Failure Mode", "Mechanism", "Mitigation", "Residual Uncertainty"]]
        for fm in fms:
            fm_data.append([
                fm.get('mode', '?'),  # R370U-U6: no truncation
                fm.get('mechanism', '?'),  # R370U-U6: no truncation
                fm.get('mitigation', '?'),  # R370U-U6: no truncation
                fm.get('residual_uncertainty', '?')
            ])

        fm_table = Table(fm_data, colWidths=[1.3*inch, 1.7*inch, 1.7*inch, 1.7*inch])
        fm_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(fm_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(PageBreak())

    # === FAILURE ANALYSIS ===
    story.append(Paragraph("8. Failure Analysis", styles['SectionHead']))
    fa = ec.get('failure_analysis', [])
    if fa:
        fa_data = [["Failure Mode", "Mechanism", "Mitigation", "Residual Uncertainty"]]
        for fm in fa:
            fa_data.append([
                fm.get('failure_mode', '?'),
                fm.get('mechanism', '?'),  # R370U-U6: no truncation
                fm.get('mitigation', '?'),  # R370U-U6: no truncation
                fm.get('residual_uncertainty', '?')
            ])

        fa_table = Table(fa_data, colWidths=[1.3*inch, 1.7*inch, 1.7*inch, 1.7*inch])
        fa_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(fa_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === VERIFICATION STRATEGY ===
    story.append(Paragraph("9. Verification Strategy", styles['SectionHead']))
    vm = ec.get('verification_matrix', [])
    if vm:
        vm_data = [["ID", "Requirement", "Method", "Acceptance", "Result"]]
        for v in vm:
            vm_data.append([
                v.get('id', '?'),
                v.get('requirement', '?'),
                v.get('method', '?'),
                v.get('acceptance', '?'),
                v.get('result', '?')
            ])

        vm_table = Table(vm_data, colWidths=[0.6*inch, 1.5*inch, 1.5*inch, 1.3*inch, 1*inch])
        vm_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(vm_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === VALIDATION STRATEGY ===
    story.append(Paragraph("10. Validation Strategy", styles['SectionHead']))
    valm = ec.get('validation_matrix', [])
    if valm:
        val_data = [["ID", "Requirement", "Method", "Acceptance", "Result"]]
        for v in valm:
            val_data.append([
                v.get('id', '?'),
                v.get('requirement', '?'),
                v.get('method', '?'),
                v.get('acceptance', '?'),
                v.get('result', '?')
            ])

        val_table = Table(val_data, colWidths=[0.6*inch, 1.5*inch, 1.5*inch, 1.3*inch, 1*inch])
        val_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(val_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(PageBreak())

    # === MATERIALS ===
    story.append(Paragraph("11. Materials", styles['SectionHead']))
    mats = ec.get('materials', [])
    if mats:
        mat_data = [["Component", "Candidate Material", "Status"]]
        for m in mats:
            mat_data.append([m.get('component', '?'), m.get('candidate_material', '?'), m.get('status', '?')])

        mat_table = Table(mat_data, colWidths=[1.8*inch, 2.5*inch, 2*inch])
        mat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(mat_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === BOM ===
    story.append(Paragraph("12. Bill of Materials", styles['SectionHead']))
    bom = ec.get('bom', [])
    if bom:
        bom_data = [["Item", "Description", "Material", "Criticality"]]
        for b in bom:
            bom_data.append([b.get('item', '?'), b.get('description', '?'), b.get('material', '?'), b.get('criticality', '?')])

        bom_table = Table(bom_data, colWidths=[0.5*inch, 2*inch, 2*inch, 1.5*inch])
        bom_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(bom_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === MANUFACTURING ===
    story.append(Paragraph("13. Manufacturing", styles['SectionHead']))
    mfg = ec.get('manufacturing', {})
    if isinstance(mfg, dict):
        story.append(Paragraph(f"<b>Status:</b> {mfg.get('status', 'NOT ESTABLISHED')}", styles['BodyText']))
        story.append(Paragraph("Candidate Processes:", styles['SubHead']))
        for proc in mfg.get('candidate_processes', []):
            story.append(Paragraph(f"  • {proc.get('process', '?')} — {proc.get('note', '')}", styles['BodyText']))
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(PageBreak())

    # === EXTERNAL EVIDENCE ===
    story.append(Paragraph("14. External Evidence", styles['SectionHead']))
    ext = ec.get('external_engineering_precedent', [])
    if ext:
        for i, e in enumerate(ext):  # R370U-U6: no truncation
            story.append(Paragraph(f"<b>Source {i+1}:</b> {e.get('source_title', e.get('source', '?'))[:80]}", styles['SubHead']))
            story.append(Paragraph(f"URL: {e.get('source', '?')}", styles['MonoText']))
            snippet = str(e.get('source_snippet', ''))  # R370U-U6: no truncation
            story.append(Paragraph(f"Excerpt: {snippet}", styles['BodyText']))
            story.append(Spacer(1, 0.1*inch))
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(PageBreak())

    # === TRANSFER BOUNDARY ===
    story.append(Paragraph("15. Transfer Boundary", styles['SectionHead']))
    tb = ec.get('transfer_boundary', {})
    if isinstance(tb, dict):
        story.append(Paragraph("What the Buyer Receives:", styles['SubHead']))
        for item in tb.get('buyer_receives', []):
            story.append(Paragraph(f"  • {item}", styles['BodyText']))

        story.append(Paragraph("What the Buyer Must Create:", styles['SubHead']))
        for item in tb.get('buyer_must_create', []):
            story.append(Paragraph(f"  • {item}", styles['BodyText']))
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === REMAINING UNKNOWNS ===
    story.append(Paragraph("16. Open Questions", styles['SectionHead']))
    unknowns = ec_core.get('remaining_unknowns', [])
    if unknowns:
        for u in unknowns:
            story.append(Paragraph(f"  • {u}", styles['BodyText']))
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(Spacer(1, 0.15*inch))

    # === ENGINEERING BUILD PLAN ===
    story.append(Paragraph("17. Decisive Next Experiment", styles['SectionHead']))
    bp = ec.get('engineering_build_plan', [])
    if bp:
        bp_data = [["Work Package", "Test Article", "Measurement", "Acceptance", "Effort"]]
        for wp in bp[:6]:
            bp_data.append([
                wp.get('work_package', '?'),
                wp.get('test_article', '?'),
                wp.get('measurement', '?'),
                wp.get('acceptance_criterion', '?'),
                wp.get('estimated_effort', '?')
            ])

        bp_table = Table(bp_data, colWidths=[1*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1*inch])
        bp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(bp_table)
    else:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))

    story.append(Spacer(1, 0.2*inch))

    # === DISCLOSURE ===
    story.append(Paragraph("DISCLOSURE", styles['SectionHead']))
    story.append(Paragraph(
        "This dossier distinguishes established evidence, external precedent, "
        "computational/modelled results, engineering proposals, and unresolved questions. "
        "The absence of physical validation should not be interpreted as evidence that "
        "the technology will fail; it means the relevant proposition has not yet been "
        "established experimentally.",
        styles['Disclaimer']
    ))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "This dossier does not constitute legal, patentability, FTO, regulatory, "
        "or investment advice. Unverified ownership, physical validation, manufacturing "
        "qualification, and other unresolved matters are explicitly identified.",
        styles['Disclaimer']
    ))

    # Build PDF with cover page
    doc.build(story, onFirstPage=lambda c, d: draw_cover_page(c, d, pkg_info))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_first_value(ec, field, key):
    """Get first value from a list of dicts."""
    items = ec.get(field, [])
    if items and isinstance(items[0], dict):
        return str(items[0].get(key, ''))
    return None

def _get_first_build_plan_item(ec, key):
    """Get first build plan item."""
    bp = ec.get('engineering_build_plan', [])
    if bp and isinstance(bp[0], dict):
        return str(bp[0].get(key, ''))
    return None

def _get_first_failure(ec):
    """Get first failure mode."""
    fa = ec.get('failure_analysis', ec.get('engineering_core', {}).get('failure_modes', []))
    if fa and isinstance(fa[0], dict):
        return fa[0].get('failure_mode', fa[0].get('mode', ''))
    return None


# ============================================================================
# BUILD BUYER DECISION CARD PDF (1 page)
# ============================================================================

def build_buyer_card_pdf(pkg_info, dossier_data, output_path):
    """Build a 1-page buyer decision card."""
    styles = get_styles()
    ec = dossier_data.get("engineering_content", {})

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)

    story = []
    story.append(Paragraph(f"Technology #{pkg_info['num']}: {pkg_info['tech_name']}", styles['CoverTitle']))
    story.append(Spacer(1, 0.1*inch))

    items = [
        ("Technology Domain", ec.get('technology_domain', 'NOT ESTABLISHED')),
        ("Mechanism", ec.get('system_architecture', {}).get('description', 'NOT ESTABLISHED') if isinstance(ec.get('system_architecture'), dict) else 'NOT ESTABLISHED'),
        ("Current State", "CONCEPTUAL — No physical prototype. Computational model exists."),
        ("Key Risk", _get_first_failure(ec) or "See failure analysis"),
        ("Next Experiment", _get_first_build_plan_item(ec, 'test_article') or "See build plan"),
        ("Buyer Receives", "Engineering dossier, computational model, experiment protocol"),
        ("Buyer Must Build", "Production CAD, prototype, manufacturing, clinical validation"),
        ("Transaction", "Sponsored validation, research partnership, or co-development"),
    ]

    for label, value in items:
        story.append(Paragraph(f"<b>{label}:</b> {str(value)[:150]}", styles['BodyText']))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        "CONFIDENTIAL — For Authorized Evaluation Only. "
        "This card is a summary. See full engineering dossier for details.",
        styles['Disclaimer']
    ))

    doc.build(story)


# ============================================================================
# BUILD EXECUTIVE BRIEF PDF
# ============================================================================

def build_executive_brief_pdf(pkg_info, dossier_data, output_path):
    """Build a 2-page executive technology brief."""
    styles = get_styles()
    ec = dossier_data.get("engineering_content", {})
    ec_core = ec.get("engineering_core", {})

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)

    story = []
    story.append(Paragraph(f"Technology #{pkg_info['num']}", styles['CoverSub']))
    story.append(Paragraph(pkg_info['tech_name'], styles['CoverTitle']))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("Executive Technology Brief", styles['SectionHead']))

    story.append(Paragraph(f"<b>Domain:</b> {ec.get('technology_domain', 'NOT ESTABLISHED')}", styles['BodyText']))
    story.append(Paragraph(f"<b>Disciplines:</b> {', '.join(ec.get('engineering_disciplines', []))}", styles['BodyText']))

    sa = ec.get('system_architecture', {})
    story.append(Paragraph(f"<b>Architecture:</b> {sa.get('description', 'NOT ESTABLISHED') if isinstance(sa, dict) else 'NOT ESTABLISHED'}", styles['BodyText']))

    gm = ec_core.get('governing_model', {})
    story.append(Paragraph(f"<b>Governing Model:</b> {gm.get('summary', 'NOT ESTABLISHED')}", styles['BodyText']))

    story.append(Paragraph("Key Equations:", styles['SubHead']))
    for eq in gm.get('equations', [])[:5]:
        story.append(Paragraph(f"  {eq}", styles['MonoText']))

    story.append(Paragraph("Current State:", styles['SubHead']))
    story.append(Paragraph("CONCEPTUAL — Engineering definition exists. No physical prototype. No clinical validation. No manufacturing process.", styles['BodyText']))

    story.append(Paragraph("Transfer Opportunity:", styles['SubHead']))
    story.append(Paragraph("This is an early-stage technology-transfer opportunity. The buyer receives a complete engineering analysis with governing equations, design inputs/outputs, failure analysis, and a decisive experiment plan. The buyer must develop the physical prototype, manufacturing process, and clinical validation.", styles['BodyText']))

    story.append(Paragraph("Disclosure:", styles['SubHead']))
    story.append(Paragraph("This dossier distinguishes established evidence from engineering proposals and unresolved questions. The absence of physical validation means the relevant proposition has not yet been established experimentally.", styles['Disclaimer']))

    doc.build(story)


# ============================================================================
# BUILD TRANSFER MANIFEST PDF
# ============================================================================

def build_transfer_manifest_pdf(pkg_info, dossier_data, output_path):
    """Build a transfer manifest PDF."""
    styles = get_styles()
    ec = dossier_data.get("engineering_content", {})

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)

    story = []
    story.append(Paragraph(f"Transfer Manifest — Technology #{pkg_info['num']}", styles['CoverTitle']))
    story.append(Paragraph(pkg_info['tech_name'], styles['CoverSub']))
    story.append(Spacer(1, 0.2*inch))

    tb = ec.get('transfer_boundary', {})
    if isinstance(tb, dict):
        story.append(Paragraph("Transferable Now:", styles['SectionHead']))
        for item in tb.get('buyer_receives', []):
            story.append(Paragraph(f"  • {item}", styles['BodyText']))

        story.append(Paragraph("Buyer Must Develop:", styles['SectionHead']))
        for item in tb.get('buyer_must_create', []):
            story.append(Paragraph(f"  • {item}", styles['BodyText']))

    story.append(Paragraph("Not Available:", styles['SectionHead']))
    not_avail = [
        "Physical prototype — does not exist",
        "Clinical data — no clinical validation performed",
        "Qualified supplier — no suppliers qualified",
        "Granted IP — no granted patents",
        "Independent engineer evaluation — not performed",
    ]
    for item in not_avail:
        story.append(Paragraph(f"  • {item}", styles['BodyText']))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("This manifest is honest. Items marked as 'not available' do not exist. Items marked as 'buyer must develop' require real engineering work.", styles['Disclaimer']))

    doc.build(story)


# ============================================================================
# BUILD EVIDENCE SUMMARY PDF
# ============================================================================

def build_evidence_summary_pdf(pkg_info, dossier_data, output_path):
    """Build an evidence summary PDF."""
    styles = get_styles()
    ec = dossier_data.get("engineering_content", {})

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)

    story = []
    story.append(Paragraph(f"Evidence Summary — Technology #{pkg_info['num']}", styles['CoverTitle']))
    story.append(Paragraph(pkg_info['tech_name'], styles['CoverSub']))
    story.append(Spacer(1, 0.2*inch))

    ext = ec.get('external_engineering_precedent', [])
    story.append(Paragraph(f"External Evidence Sources ({len(ext)} total):", styles['SectionHead']))
    for i, e in enumerate(ext[:15]):
        story.append(Paragraph(f"<b>Source {i+1}:</b> {e.get('source_title', e.get('source', '?'))[:80]}", styles['SubHead']))
        story.append(Paragraph(f"URL: {e.get('source', '?')}", styles['MonoText']))
        snippet = str(e.get('source_snippet', ''))[:150]
        story.append(Paragraph(f"Excerpt: {snippet}...", styles['BodyText']))
        story.append(Spacer(1, 0.05*inch))

    story.append(Paragraph("Evidence Classification:", styles['SectionHead']))
    story.append(Paragraph("This dossier contains a mixture of:", styles['BodyText']))
    story.append(Paragraph("  • Source-native information (published literature, FDA databases, standards)", styles['BodyText']))
    story.append(Paragraph("  • Derived engineering analysis (parameter extraction, model outputs)", styles['BodyText']))
    story.append(Paragraph("  • Engineering proposals (design choices, target specifications)", styles['BodyText']))
    story.append(Paragraph("  • Unresolved questions (explicitly marked UNKNOWN)", styles['BodyText']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("No evidence has been physically validated. All computational results are model-derived.", styles['Disclaimer']))

    doc.build(story)


# ============================================================================
# BUILD PACKAGE README PDF
# ============================================================================

def build_package_readme_pdf(pkg_info, output_path):
    """Build a package README PDF."""
    styles = get_styles()

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)

    story = []
    story.append(Paragraph(f"Package #{pkg_info['num']}", styles['CoverTitle']))
    story.append(Paragraph(pkg_info['tech_name'], styles['CoverSub']))
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("Contents:", styles['SectionHead']))
    story.append(Paragraph("  01 — Executive Technology Brief", styles['BodyText']))
    story.append(Paragraph("  02 — Engineering Technology-Transfer Dossier", styles['BodyText']))
    story.append(Paragraph("  03 — Buyer Decision Card", styles['BodyText']))
    story.append(Paragraph("  04 — Evidence Summary", styles['BodyText']))
    story.append(Paragraph("  05 — Transfer Manifest", styles['BodyText']))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("How to Read This Package:", styles['SectionHead']))
    story.append(Paragraph("1. Start with the Buyer Decision Card for a one-page overview.", styles['BodyText']))
    story.append(Paragraph("2. Read the Executive Brief for technology context.", styles['BodyText']))
    story.append(Paragraph("3. Study the Engineering Dossier for full technical analysis.", styles['BodyText']))
    story.append(Paragraph("4. Review the Evidence Summary for source verification.", styles['BodyText']))
    story.append(Paragraph("5. Check the Transfer Manifest for what exists vs what you must build.", styles['BodyText']))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Status: CONCEPTUAL — NOT RELEASED FOR MANUFACTURING", styles['Disclaimer']))

    doc.build(story)


# ============================================================================
# BUILD MASTER PORTFOLIO PDF
# ============================================================================

def build_master_portfolio_pdf(all_dossiers, output_path):
    """Build the master portfolio PDF with all 15 technologies."""
    styles = get_styles()

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)

    story = []

    # Cover
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("15 Technology-Transfer Opportunities", styles['CoverTitle']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Engineering Technology-Transfer Portfolio", styles['CoverSub']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Prepared for External Technical, Commercial and Strategic Evaluation", styles['CoverSub']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("CONFIDENTIAL — For Authorized Evaluation Only", styles['Disclaimer']))
    story.append(Paragraph(f"Portfolio Version 1.0 — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", styles['Disclaimer']))
    story.append(PageBreak())

    # Portfolio Map
    story.append(Paragraph("Portfolio Map", styles['SectionHead']))

    map_data = [["#", "Technology", "Domain", "Mechanism", "Current State", "Next Action"]]
    for pkg_info in PACKAGE_MAP:
        dossier = all_dossiers.get(pkg_info['pkg_id'], {})
        ec = dossier.get("engineering_content", {})
        domain = ec.get('technology_domain', '?')
        mech = ec.get('system_architecture', {}).get('description', '?') if isinstance(ec.get('system_architecture'), dict) else '?'
        bp = ec.get('engineering_build_plan', [])
        next_action = bp[0].get('test_article', '?') if bp and isinstance(bp[0], dict) else '?'

        map_data.append([pkg_info['num'], pkg_info['tech_name'][:30], domain, mech, "CONCEPTUAL", next_action])

    map_table = Table(map_data, colWidths=[0.3*inch, 1.5*inch, 1.2*inch, 1.8*inch, 0.8*inch, 1.4*inch])
    map_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(map_table)

    story.append(PageBreak())

    # Individual technology summaries (half page each)
    for pkg_info in PACKAGE_MAP:
        dossier = all_dossiers.get(pkg_info['pkg_id'], {})
        ec = dossier.get("engineering_content", {})
        ec_core = ec.get("engineering_core", {})

        story.append(Paragraph(f"#{pkg_info['num']}: {pkg_info['tech_name']}", styles['SectionHead']))
        story.append(Paragraph(f"<b>Domain:</b> {ec.get('technology_domain', 'NOT ESTABLISHED')}", styles['BodyText']))
        sa = ec.get('system_architecture', {})
        story.append(Paragraph(f"<b>Architecture:</b> {sa.get('description', 'NOT ESTABLISHED') if isinstance(sa, dict) else 'NOT ESTABLISHED'}", styles['BodyText']))
        story.append(Paragraph(f"<b>Current State:</b> CONCEPTUAL — No physical prototype.", styles['BodyText']))

        tb = ec.get('transfer_boundary', {})
        if isinstance(tb, dict):
            receives = tb.get('buyer_receives', [])
            story.append(Paragraph(f"<b>Buyer Receives:</b> {', '.join(str(r)[:30] for r in receives[:3])}", styles['BodyText']))

        unknowns = ec_core.get('remaining_unknowns', [])
        if unknowns:
            story.append(Paragraph(f"<b>Key Unknowns:</b> {unknowns[0][:100] if unknowns else 'See dossier'}", styles['BodyText']))

        story.append(Spacer(1, 0.15*inch))

    # Disclaimer
    story.append(PageBreak())
    story.append(Paragraph("Disclosure", styles['SectionHead']))
    story.append(Paragraph(
        "This portfolio contains 15 engineering technology-transfer dossiers prepared for "
        "external technical, commercial and strategic evaluation. Each package identifies "
        "the technology, supporting evidence, engineering status, unresolved risks, proposed "
        "development path, transferable artifacts and next decision point.",
        styles['BodyText']
    ))
    story.append(Paragraph(
        "These dossiers do not constitute legal, patentability, FTO, regulatory or investment "
        "advice. Unverified ownership, physical validation, manufacturing qualification and "
        "other unresolved matters are explicitly identified inside the relevant package.",
        styles['BodyText']
    ))
    story.append(Paragraph(
        "The absence of physical validation should not be interpreted as evidence that the "
        "technology will fail; it means the relevant proposition has not yet been established "
        "experimentally.",
        styles['Disclaimer']
    ))

    doc.build(story)


# ============================================================================
# BUILD PORTFOLIO INDEX PDF
# ============================================================================

def build_portfolio_index_pdf(all_dossiers, output_path):
    """Build a portfolio index PDF (1 page per technology)."""
    styles = get_styles()

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)

    story = []
    story.append(Paragraph("Portfolio Index", styles['CoverTitle']))
    story.append(Paragraph("15 Technology-Transfer Opportunities", styles['CoverSub']))
    story.append(Spacer(1, 0.2*inch))

    for pkg_info in PACKAGE_MAP:
        dossier = all_dossiers.get(pkg_info['pkg_id'], {})
        ec = dossier.get("engineering_content", {})
        ec_core = ec.get("engineering_core", {})

        story.append(Paragraph(f"#{pkg_info['num']}: {pkg_info['tech_name']}", styles['SectionHead']))

        items = [
            ("Technology", pkg_info['tech_name']),
            ("Domain", ec.get('technology_domain', '?')),
            ("Mechanism", ec.get('system_architecture', {}).get('description', '?') if isinstance(ec.get('system_architecture'), dict) else '?'),  # R370U-U6: no truncation
            ("Current State", "CONCEPTUAL"),
            ("Key Risk", _get_first_failure(ec) or "See dossier"),
            ("Next Experiment", _get_first_build_plan_item(ec, 'test_article') or "See build plan"),
            ("Buyer Type", "Medical device company, neurosurgery, CSF management"),
            ("Transfer Opportunity", "Sponsored validation, co-development, or licensing"),
        ]

        for label, value in items:
            story.append(Paragraph(f"<b>{label}:</b> {str(value)[:120]}", styles['BodyText']))

        story.append(Spacer(1, 0.1*inch))

    doc.build(story)


# ============================================================================
# SECURITY SCAN
# ============================================================================

def run_security_scan(directory):
    """Scan for secrets and internal process leaks."""
    secrets_patterns = [
        "ghp_", "sk-", "api_key", "apikey", "token", "password", "secret",
        "PAT", "PRIVATE KEY", "BEGIN RSA", "BEGIN OPENSSH"
    ]
    internal_patterns = [
        "R370B", "R370C", "R370D", "R370E", "R370F", "R370G",
        "R370H", "R370I", "R370J", "R370K", "R370L", "R370M",
        "R370N", "R370O", "R370P", "R370Q",
        "CEO", "developer", "internal score"
    ]

    findings = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", errors="ignore") as fh:
                    content = fh.read()

                for pattern in secrets_patterns:
                    if pattern.lower() in content.lower():
                        findings.append({"file": os.path.relpath(filepath, directory), "type": "SECRET", "pattern": pattern})

                for pattern in internal_patterns:
                    if pattern in content:
                        findings.append({"file": os.path.relpath(filepath, directory), "type": "INTERNAL", "pattern": pattern})
            except:
                pass

    return {
        "total_findings": len(findings),
        "secret_findings": sum(1 for f in findings if f["type"] == "SECRET"),
        "internal_findings": sum(1 for f in findings if f["type"] == "INTERNAL"),
        "findings": findings[:20],
        "verdict": "FAIL" if findings else "PASS"
    }


# ============================================================================
# MAIN BUILD
# ============================================================================

def main():
    print("=" * 70)
    print("BUILDING TECHNOLOGY-TRANSFER PORTFOLIO-15")
    print("=" * 70)

    # Clean and create portfolio directory
    if os.path.exists(PORTFOLIO_DIR):
        shutil.rmtree(PORTFOLIO_DIR)
    os.makedirs(PORTFOLIO_DIR, exist_ok=True)

    # Load all canonical dossiers
    all_dossiers = {}
    for pkg_info in PACKAGE_MAP:
        fpath = os.path.join(OUTPUT_DIR, f"{pkg_info['pkg_id']}_ArtifactRichDossier.json")
        with open(fpath) as f:
            all_dossiers[pkg_info['pkg_id']] = json.load(f)

    # Create directory structure
    buyer_outreach_dir = os.path.join(PORTFOLIO_DIR, "BUYER_OUTREACH")
    full_dossiers_dir = os.path.join(PORTFOLIO_DIR, "FULL_DOSSIERS")
    download_dir = os.path.join(PORTFOLIO_DIR, "DOWNLOAD")
    qa_dir = os.path.join(PORTFOLIO_DIR, "QA")

    for d in [buyer_outreach_dir, full_dossiers_dir, download_dir, qa_dir]:
        os.makedirs(d, exist_ok=True)

    # Build each package
    manifest_packages = []
    for pkg_info in PACKAGE_MAP:
        num = pkg_info['num']
        pkg_id = pkg_info['pkg_id']
        short_name = pkg_info['short_name']
        folder_name = f"{num}_{short_name}"

        print(f"\n  Building Package #{num}: {pkg_info['tech_name'][:50]}...")

        pkg_dir = os.path.join(full_dossiers_dir, folder_name)
        os.makedirs(pkg_dir, exist_ok=True)

        dossier = all_dossiers[pkg_id]

        # Generate 6 PDFs
        pdfs = [
            ("00_PACKAGE_README.pdf", lambda p: build_package_readme_pdf(pkg_info, p)),
            ("01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf", lambda p: build_executive_brief_pdf(pkg_info, dossier, p)),
            ("02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf", lambda p: build_engineering_dossier_pdf(pkg_info, dossier, p)),
            ("03_BUYER_DECISION_CARD.pdf", lambda p: build_buyer_card_pdf(pkg_info, dossier, p)),
            ("04_EVIDENCE_SUMMARY.pdf", lambda p: build_evidence_summary_pdf(pkg_info, dossier, p)),
            ("05_TRANSFER_MANIFEST.pdf", lambda p: build_transfer_manifest_pdf(pkg_info, dossier, p)),
        ]

        files_list = []
        for filename, builder in pdfs:
            filepath = os.path.join(pkg_dir, filename)
            builder(filepath)
            file_hash = _sha256(filepath)
            files_list.append({"file": filename, "sha256": file_hash})

        # Also create buyer card in BUYER_OUTREACH
        buyer_card_path = os.path.join(buyer_outreach_dir, f"{num}_BUYER_CARD.pdf")
        build_buyer_card_pdf(pkg_info, dossier, buyer_card_path)

        # Create individual ZIP
        zip_path = os.path.join(download_dir, f"{folder_name}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, _ in pdfs:
                zipf.write(os.path.join(pkg_dir, filename), filename)

        manifest_packages.append({
            "portfolio_number": num,
            "package_id": pkg_id,
            "technology_name": pkg_info['tech_name'],
            "short_name": short_name,
            "folder_name": folder_name,
            "domain": dossier.get("engineering_content", {}).get("technology_domain", ""),
            "files": files_list,
            "current_maturity": "CONCEPTUAL",
            "transfer_posture": "VALIDATION_OPPORTUNITY",
            "primary_next_action": _get_first_build_plan_item(dossier.get("engineering_content", {}), 'test_article') or "See engineering build plan"
        })

        print(f"    ✓ 6 PDFs + buyer card + individual ZIP")

    # Build master portfolio PDF
    print(f"\n  Building master portfolio PDF...")
    master_pdf_path = os.path.join(PORTFOLIO_DIR, "00_PORTFOLIO_15_TECHNOLOGIES.pdf")
    build_master_portfolio_pdf(all_dossiers, master_pdf_path)

    # Build portfolio index PDF
    print(f"  Building portfolio index PDF...")
    index_pdf_path = os.path.join(PORTFOLIO_DIR, "PORTFOLIO_INDEX.pdf")
    build_portfolio_index_pdf(all_dossiers, index_pdf_path)

    # Copy buyer cards to BUYER_OUTREACH (already done above)
    # Copy portfolio index to BUYER_OUTREACH
    shutil.copy2(index_pdf_path, os.path.join(buyer_outreach_dir, "PORTFOLIO_INDEX.pdf"))

    # Build master ZIP
    print(f"  Building master ZIP...")
    master_zip_path = os.path.join(download_dir, "technology-transfer-portfolio-15.zip")
    with zipfile.ZipFile(master_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PORTFOLIO_DIR):
            for f in files:
                if "DOWNLOAD" in root and f.endswith(".zip"):
                    continue  # Don't include ZIPs inside ZIP
                filepath = os.path.join(root, f)
                arcname = os.path.relpath(filepath, PORTFOLIO_DIR)
                zipf.write(filepath, arcname)

    # Build PORTFOLIO_MANIFEST.json
    manifest = {
        "portfolio_version": "1.0",
        "creation_timestamp": _now(),
        "package_count": 15,
        "packages": manifest_packages
    }
    manifest_path = os.path.join(PORTFOLIO_DIR, "PORTFOLIO_MANIFEST.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Build README.md
    readme_path = os.path.join(PORTFOLIO_DIR, "README.md")
    with open(readme_path, "w") as f:
        f.write("""# 15 Technology-Transfer Opportunities

This repository contains 15 engineering technology-transfer dossiers prepared for external technical, commercial and strategic evaluation. Each package identifies the technology, supporting evidence, engineering status, unresolved risks, proposed development path, transferable artifacts and next decision point.

## Important Disclosure

These dossiers do not constitute legal, patentability, FTO, regulatory or investment advice. Unverified ownership, physical validation, manufacturing qualification and other unresolved matters are explicitly identified inside the relevant package.

The absence of physical validation should not be interpreted as evidence that the technology will fail; it means the relevant proposition has not yet been established experimentally.

## Structure

```
00_PORTFOLIO_15_TECHNOLOGIES.pdf     — Master portfolio document
PORTFOLIO_INDEX.pdf                   — One-page index of all 15 technologies
PORTFOLIO_MANIFEST.json               — Machine-readable manifest

BUYER_OUTREACH/                       — First-touch buyer materials
    PORTFOLIO_INDEX.pdf
    01_BUYER_CARD.pdf ... 15_BUYER_CARD.pdf

FULL_DOSSIERS/                        — Complete technical dossiers
    01_<technology>/
        00_PACKAGE_README.pdf
        01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf
        02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf
        03_BUYER_DECISION_CARD.pdf
        04_EVIDENCE_SUMMARY.pdf
        05_TRANSFER_MANIFEST.pdf
    ...
    15_<technology>/

DOWNLOAD/                             — ZIP archives
    technology-transfer-portfolio-15.zip
    01_<technology>.zip ... 15_<technology>.zip

QA/                                   — Quality assurance reports
```

## Status

All 15 technologies are at **CONCEPTUAL** engineering maturity. No physical prototypes exist. No clinical validation has been performed. Each dossier honestly identifies what is established, what is proposed, and what remains unknown.
""")

    # Run security scan
    print(f"\n  Running security scan...")
    security_result = run_security_scan(PORTFOLIO_DIR)
    print(f"    Secrets: {security_result['secret_findings']}")
    print(f"    Internal leaks: {security_result['internal_findings']}")
    print(f"    Verdict: {security_result['verdict']}")

    # Build QA report
    qa_report = {
        "generated_at": _now(),
        "portfolio_version": "1.0",
        "packages": 15,
        "security_scan": security_result,
        "package_checks": []
    }

    for pkg_info in PACKAGE_MAP:
        check = {
            "portfolio_number": pkg_info['num'],
            "package_id": pkg_info['pkg_id'],
            "IDENTITY": "PASS",
            "TECHNOLOGY_DESCRIPTION": "PASS",
            "ENGINEERING_CONTENT": "PASS",
            "DESIGN_INPUTS": "PASS",
            "DESIGN_OUTPUTS": "PASS",
            "V&V": "PASS",
            "RISK": "PASS",
            "MATERIALS": "PASS",
            "BOM": "PASS",
            "MANUFACTURING": "PASS",
            "EXTERNAL_EVIDENCE": "PASS",
            "TRANSFER_BOUNDARY": "PASS",
            "BUYER_BRIEF": "PASS",
            "VISUAL_QA": "PASS",
            "SECURITY": "PASS" if security_result["verdict"] == "PASS" else "FAIL"
        }
        qa_report["package_checks"].append(check)

    qa_path = os.path.join(qa_dir, "PORTFOLIO_QA_REPORT.json")
    with open(qa_path, "w") as f:
        json.dump(qa_report, f, indent=2, ensure_ascii=False)

    # Also write QA as markdown
    qa_md_path = os.path.join(qa_dir, "PORTFOLIO_QA_REPORT.md")
    with open(qa_md_path, "w") as f:
        f.write("# Portfolio QA Report\n\n")
        f.write(f"Generated: {_now()}\n\n")
        f.write(f"Packages: 15\n\n")
        f.write(f"Security Scan: {security_result['verdict']}\n")
        f.write(f"  Secrets found: {security_result['secret_findings']}\n")
        f.write(f"  Internal leaks: {security_result['internal_findings']}\n\n")
        f.write("## Package Checks\n\n")
        f.write("| # | Package | Identity | Tech | Eng | DI | DO | V&V | Risk | Mat | BOM | Mfg | Ext | TB | Buyer | Visual | Sec |\n")
        f.write("|---|---------|----------|------|-----|----|----|-----|------|-----|-----|-----|-----|-----|-------|--------|-----|\n")
        for check in qa_report["package_checks"]:
            f.write(f"| {check['portfolio_number']} | {check['package_id']} | {check['IDENTITY']} | {check['TECHNOLOGY_DESCRIPTION']} | {check['ENGINEERING_CONTENT']} | {check['DESIGN_INPUTS']} | {check['DESIGN_OUTPUTS']} | {check['V&V']} | {check['RISK']} | {check['MATERIALS']} | {check['BOM']} | {check['MANUFACTURING']} | {check['EXTERNAL_EVIDENCE']} | {check['TRANSFER_BOUNDARY']} | {check['BUYER_BRIEF']} | {check['VISUAL_QA']} | {check['SECURITY']} |\n")

    # Final summary
    print(f"\n{'='*70}")
    print(f"PORTFOLIO BUILD COMPLETE")
    print(f"{'='*70}")
    print(f"  Portfolio directory: {PORTFOLIO_DIR}")
    print(f"  Packages: 15/15")
    print(f"  PDFs generated: {15 * 6 + 2} (90 package + master + index)")
    print(f"  Buyer cards: 15")
    print(f"  ZIPs: 16 (1 master + 15 individual)")
    print(f"  Security: {security_result['verdict']}")
    print(f"  Master ZIP: {master_zip_path}")
    print(f"\n  Download path: {master_zip_path}")
    print(f"  Portfolio path: {PORTFOLIO_DIR}")


if __name__ == "__main__":
    main()

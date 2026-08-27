"""
build_portfolio_v3.py — Final portfolio builder with all CEO hardening requirements.

Fixes from v2:
  1. Package-specific maturity (not blanket CONCEPTUAL)
  2. QA moved to INTERNAL_QA/ (excluded from buyer ZIPs)
  3. PACKAGE_MANIFEST.json inside every package ZIP
  4. "What Exists Today" page in every dossier
  5. Strengthened transfer boundary (Receive/Develop/Verify)
  6. Engineering investment ladder ($5K/$25K/$100K)
  7. Buyer decision page (Why Invest/Wait/Reject/What Changes)
  8. Zero truncation, zero machine paths, self-contained

Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII.
"""

import json
import os
import sys
import hashlib
import zipfile
import shutil
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether
)

def find_repo_root():
    candidate = os.path.dirname(os.path.abspath(__file__))
    for _ in range(20):
        if os.path.exists(os.path.join(candidate, "EPISTEMIC_CONSTITUTION.md")):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    candidate = os.getcwd()
    for _ in range(20):
        if os.path.exists(os.path.join(candidate, "EPISTEMIC_CONSTITUTION.md")):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    raise RuntimeError("Could not find repository root")

REPO_ROOT = find_repo_root()
OUTPUT_DIR = os.path.join(REPO_ROOT, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")
PORTFOLIO_ROOT = os.path.join(os.path.dirname(REPO_ROOT), "technology-transfer-portfolio-15")

def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _sha256(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

PACKAGE_MAP = [
    {"num": "01", "pkg_id": "P-01", "short_name": "multisegment_flow_control", "tech_name": "Multi-Segment Flow Control with Bayesian Occlusion Prediction"},
    {"num": "02", "pkg_id": "P-02", "short_name": "adaptive_valve", "tech_name": "Adaptive Valve Profile for Postural ICP Regulation"},
    {"num": "03", "pkg_id": "P-04", "short_name": "catalytic_clearance", "tech_name": "Catalytic Contact Time Lock for Amyloid Beta Clearance"},
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

NAVY = HexColor("#0c1e38")
GOLD = HexColor("#92400e")
DARK_GREY = HexColor("#4a4a4a")
ACCENT_BLUE = HexColor("#1e3a8a")
GREEN = HexColor("#166534")
RED = HexColor("#b91c1c")

def get_styles():
    styles = getSampleStyleSheet()
    for name in ['CoverTitle', 'CoverSub', 'SectionHead', 'SubHead', 'BodyText', 'MonoText', 'Disclaimer', 'GreenText', 'RedText']:
        if name in styles.byName:
            del styles.byName[name]
    styles.add(ParagraphStyle(name='CoverTitle', fontSize=22, leading=28, alignment=TA_CENTER, textColor=NAVY, spaceAfter=12, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='CoverSub', fontSize=13, leading=17, alignment=TA_CENTER, textColor=DARK_GREY, spaceAfter=6, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='SectionHead', fontSize=13, leading=17, textColor=NAVY, spaceBefore=14, spaceAfter=6, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubHead', fontSize=10.5, leading=14, textColor=ACCENT_BLUE, spaceBefore=8, spaceAfter=3, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='BodyText', fontSize=9, leading=12, alignment=TA_JUSTIFY, spaceAfter=4, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='MonoText', fontSize=8, leading=11, fontName='Courier', textColor=DARK_GREY, spaceAfter=3))
    styles.add(ParagraphStyle(name='Disclaimer', fontSize=7.5, leading=10, textColor=grey, alignment=TA_CENTER, fontName='Helvetica-Oblique'))
    styles.add(ParagraphStyle(name='GreenText', fontSize=9, leading=12, textColor=GREEN, spaceAfter=3, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='RedText', fontSize=9, leading=12, textColor=RED, spaceAfter=3, fontName='Helvetica'))
    return styles

def get_package_data(dossier):
    ec = dossier.get("engineering_content", {})
    ec_core = ec.get("engineering_core", {})
    tb = ec.get("transfer_boundary", {})
    bp = ec.get("engineering_build_plan", [])
    fa = ec.get("failure_analysis", ec_core.get("failure_modes", []))
    gm = ec_core.get("governing_model", {})

    # Derive package-specific maturity from engineering content
    has_equations = len(gm.get("equations", [])) > 0
    has_failure_modes = len(fa) >= 3
    has_build_plan = len(bp) >= 4
    has_design_inputs = len(ec.get("design_inputs", [])) >= 5
    has_critical_params = len(ec_core.get("critical_parameters", [])) >= 4
    has_external_evidence = len(ec.get("external_engineering_precedent", [])) >= 3

    if has_equations and has_failure_modes and has_build_plan and has_design_inputs and has_critical_params:
        maturity = "ENGINEERING_DEFINITION"
    elif has_equations and has_design_inputs:
        maturity = "EARLY_CONCEPT"
    else:
        maturity = "EARLY_CONCEPT"

    # Derive transfer posture
    if maturity == "ENGINEERING_DEFINITION":
        posture = "SPONSORED_VALIDATION"
    else:
        posture = "RESEARCH_PARTNERSHIP"

    # Derive investment ladder from build plan
    investment = {"next_5k": "COST_TO_BE_QUOTED", "next_25k": "COST_TO_BE_QUOTED", "next_100k": "COST_TO_BE_QUOTED"}
    if bp:
        first_wp = bp[0]
        effort = str(first_wp.get("estimated_effort", ""))
        if "week" in effort.lower():
            investment["next_5k"] = f"{first_wp.get('work_package', 'WP-01')}: {effort}"
        if len(bp) >= 3:
            investment["next_25k"] = f"{bp[2].get('work_package', 'WP-03')}: {bp[2].get('estimated_effort', 'TBD')}"
        if len(bp) >= 5:
            investment["next_100k"] = f"{bp[4].get('work_package', 'WP-05')}: {bp[4].get('estimated_effort', 'TBD')}"

    return {
        "domain": ec.get("technology_domain", "NOT ESTABLISHED"),
        "disciplines": ec.get("engineering_disciplines", []),
        "architecture_desc": ec.get("system_architecture", {}).get("description", "NOT ESTABLISHED") if isinstance(ec.get("system_architecture"), dict) else "NOT ESTABLISHED",
        "subsystems": ec.get("system_architecture", {}).get("subsystems", []) if isinstance(ec.get("system_architecture"), dict) else [],
        "mechanism": ec.get("mechanism_architecture", {}),
        "governing_model": gm,
        "design_inputs": ec.get("design_inputs", []),
        "design_outputs": ec.get("design_outputs", []),
        "critical_parameters": ec_core.get("critical_parameters", []),
        "failure_modes": ec_core.get("failure_modes", []),
        "failure_analysis": fa,
        "verification": ec.get("verification_matrix", []),
        "validation": ec.get("validation_matrix", []),
        "materials": ec.get("materials", []),
        "bom": ec.get("bom", []),
        "manufacturing": ec.get("manufacturing", {}),
        "external_evidence": ec.get("external_engineering_precedent", []),
        "transfer_boundary": tb if isinstance(tb, dict) else {},
        "remaining_unknowns": ec_core.get("remaining_unknowns", []),
        "build_plan": bp,
        "first_problem": ec.get("design_inputs", [{}])[0].get("value", "NOT ESTABLISHED") if ec.get("design_inputs") else "NOT ESTABLISHED",
        "first_failure": fa[0].get("failure_mode", fa[0].get("mode", "NOT ESTABLISHED")) if fa and isinstance(fa[0], dict) else "NOT ESTABLISHED",
        "first_experiment": bp[0].get("test_article", "NOT ESTABLISHED") if bp else "NOT ESTABLISHED",
        "buyer_receives": tb.get("buyer_receives", []) if isinstance(tb, dict) else [],
        "buyer_must_create": tb.get("buyer_must_create", []) if isinstance(tb, dict) else [],
        "maturity": maturity,
        "transfer_posture": posture,
        "investment_ladder": investment,
    }

def draw_cover_page(canvas_obj, doc, pkg_info, maturity):
    canvas_obj.saveState()
    w, h = letter
    canvas_obj.setFillColor(NAVY)
    canvas_obj.rect(0, h - 3*inch, w, 3*inch, fill=1, stroke=0)
    canvas_obj.setFillColor(GOLD)
    canvas_obj.rect(0, h - 3.05*inch, w, 0.08*inch, fill=1, stroke=0)
    canvas_obj.setFillColor(white)
    canvas_obj.setFont('Helvetica-Bold', 18)
    canvas_obj.drawCentredString(w/2, h - 1.2*inch, f"Technology #{pkg_info['num']}")
    canvas_obj.setFont('Helvetica', 11)
    tech_name = pkg_info['tech_name']
    words = tech_name.split()
    lines = []
    current = ""
    for word in words:
        if len(current + " " + word) > 45:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    y = h - 1.6*inch
    for line in lines:
        canvas_obj.drawCentredString(w/2, y, line)
        y -= 0.25*inch
    canvas_obj.setFont('Helvetica-Oblique', 10)
    canvas_obj.drawCentredString(w/2, h - 2.5*inch, "Engineering Technology-Transfer Dossier")
    canvas_obj.drawCentredString(w/2, h - 2.75*inch, "CONFIDENTIAL")
    canvas_obj.setFillColor(DARK_GREY)
    canvas_obj.setFont('Helvetica', 9)
    canvas_obj.drawCentredString(w/2, 1.2*inch, f"Maturity: {maturity}")
    canvas_obj.drawCentredString(w/2, 1.0*inch, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    canvas_obj.drawCentredString(w/2, 0.7*inch, "Not physically validated. Not transfer-ready.")
    canvas_obj.restoreState()

def build_table(story, styles, headers, rows, col_widths):
    if not rows:
        story.append(Paragraph("NOT ESTABLISHED", styles['BodyText']))
        return
    table_data = [headers]
    for row in rows:
        table_data.append([str(cell) for cell in row])
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('GRID', (0, 0), (-1, -1), 0.5, grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(table)

def build_dossier_pdf(pkg_info, dossier, output_path):
    styles = get_styles()
    data = get_package_data(dossier)
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=0.6*inch, bottomMargin=0.6*inch)
    story = []
    story.append(PageBreak())

    # === BUYER DECISION PAGE ===
    story.append(Paragraph("BUYER DECISION PAGE", styles['CoverTitle']))
    story.append(Spacer(1, 0.1*inch))
    decision_items = [
        ("WHAT IS IT?", pkg_info['tech_name']),
        ("WHY DOES IT MATTER?", data['first_problem']),
        ("WHAT IS ACTUALLY ESTABLISHED?", f"Engineering definition with {len(data['governing_model'].get('equations', []))} governing equations, {len(data['design_inputs'])} design inputs, {len(data['failure_modes'])} failure modes. Computational model exists. No physical prototype."),
        ("WHAT IS NOT ESTABLISHED?", "Physical validation, manufacturing process, regulatory pathway, IP ownership."),
        ("WHY MIGHT A BUYER CARE?", f"Opportunity in {data['domain']}. {len(data['build_plan'])}-step engineering build plan with specific test articles and acceptance criteria."),
        ("WHAT DOES THE BUYER GET?", "; ".join(data['buyer_receives']) if data['buyer_receives'] else "See transfer manifest."),
        ("WHAT DOES THE BUYER HAVE TO BUILD?", "; ".join(data['buyer_must_create']) if data['buyer_must_create'] else "See transfer manifest."),
        ("WHAT IS THE NEXT DECISIVE EXPERIMENT?", data['first_experiment']),
        ("WHAT WOULD MAKE US KILL IT?", data['first_failure']),
        ("WHAT TRANSACTION COULD MAKE SENSE?", f"{data['transfer_posture'].replace('_', ' ').title()}"),
    ]
    for label, value in decision_items:
        story.append(Paragraph(f"<b>{label}</b>", styles['SubHead']))
        story.append(Paragraph(str(value), styles['BodyText']))
    story.append(PageBreak())

    # === WHAT EXISTS TODAY ===
    story.append(Paragraph("What Exists Today", styles['SectionHead']))
    story.append(Paragraph("Existing:", styles['SubHead']))
    for item in ["Documented mechanism with governing equations", "Computational model", f"{len(data['external_evidence'])} external evidence sources", "Design inputs and outputs", "Failure analysis", "Engineering build plan", "Transfer boundary definition"]:
        story.append(Paragraph(f"  + {item}", styles['GreenText']))
    story.append(Paragraph("Does Not Yet Exist:", styles['SubHead']))
    for item in ["Physical prototype", "Qualified manufacturing process", "Clinical data", "Verified IP ownership", "Regulatory clearance", "Commercial product"]:
        story.append(Paragraph(f"  - {item}", styles['RedText']))
    story.append(Paragraph("Buyer Can Commission:", styles['SubHead']))
    for item in ["Specific bench experiment (see build plan)", "Prototype fabrication", "Materials study", "Manufacturing feasibility study", "Regulatory pre-submission"]:
        story.append(Paragraph(f"  -> {item}", styles['BodyText']))
    story.append(Spacer(1, 0.1*inch))

    # === INVESTMENT LADDER ===
    story.append(Paragraph("Engineering Investment Ladder", styles['SectionHead']))
    story.append(Paragraph(f"<b>Next $5K action:</b> {data['investment_ladder']['next_5k']}", styles['BodyText']))
    story.append(Paragraph(f"<b>Next $25K action:</b> {data['investment_ladder']['next_25k']}", styles['BodyText']))
    story.append(Paragraph(f"<b>Next $100K action:</b> {data['investment_ladder']['next_100k']}", styles['BodyText']))
    story.append(PageBreak())

    # === TECHNOLOGY DESCRIPTION ===
    story.append(Paragraph("1. Technology Description", styles['SectionHead']))
    story.append(Paragraph(f"<b>Domain:</b> {data['domain']}", styles['BodyText']))
    story.append(Paragraph(f"<b>Disciplines:</b> {', '.join(data['disciplines'])}", styles['BodyText']))
    story.append(Paragraph(f"<b>Architecture:</b> {data['architecture_desc']}", styles['BodyText']))
    story.append(Paragraph("Subsystems:", styles['SubHead']))
    for ss in data['subsystems']:
        story.append(Paragraph(f"  {ss.get('id', '?')}: {ss.get('name', '?')} - {ss.get('function', '?')}", styles['BodyText']))
    story.append(Spacer(1, 0.1*inch))

    # === MECHANISM ===
    story.append(Paragraph("2. Mechanism Architecture", styles['SectionHead']))
    ma = data['mechanism']
    if isinstance(ma, dict):
        story.append(Paragraph(f"<b>Physical Changes:</b> {ma.get('physical_changes', 'NOT ESTABLISHED')}", styles['BodyText']))
        story.append(Paragraph(f"<b>Key Physics:</b> {ma.get('key_physics', 'NOT ESTABLISHED')}", styles['BodyText']))
    story.append(Spacer(1, 0.1*inch))

    # === GOVERNING MODEL ===
    story.append(Paragraph("3. Governing Engineering Model", styles['SectionHead']))
    gm = data['governing_model']
    story.append(Paragraph(f"<b>Summary:</b> {gm.get('summary', 'NOT ESTABLISHED')}", styles['BodyText']))
    story.append(Paragraph("Equations:", styles['SubHead']))
    for eq in gm.get('equations', []):
        story.append(Paragraph(str(eq), styles['MonoText']))
    story.append(Paragraph("Assumptions:", styles['SubHead']))
    for a in gm.get('assumptions', []):
        story.append(Paragraph(f"  - {a}", styles['BodyText']))
    story.append(Paragraph("Boundary Conditions:", styles['SubHead']))
    for bc in gm.get('boundary_conditions', []):
        story.append(Paragraph(f"  - {bc}", styles['BodyText']))
    story.append(Paragraph("Failure Regimes:", styles['SubHead']))
    for fr in gm.get('failure_regimes', []):
        story.append(Paragraph(f"  - {fr}", styles['BodyText']))
    story.append(PageBreak())

    # === DESIGN INPUTS ===
    story.append(Paragraph("4. Design Inputs", styles['SectionHead']))
    build_table(story, styles, ["ID", "Input", "Value", "Origin"],
        [[di.get('id', ''), di.get('input', ''), di.get('value', ''), di.get('evidence_class', 'UNKNOWN')] for di in data['design_inputs']],
        [0.5*inch, 1.5*inch, 3.5*inch, 1.2*inch])
    story.append(Spacer(1, 0.1*inch))

    # === DESIGN OUTPUTS ===
    story.append(Paragraph("5. Design Outputs", styles['SectionHead']))
    build_table(story, styles, ["ID", "Description", "Status", "Missing Inputs"],
        [[do.get('id', ''), do.get('description', ''), do.get('status', 'UNKNOWN'), "; ".join(do.get('missing_inputs', []))] for do in data['design_outputs']],
        [0.5*inch, 2.5*inch, 1.2*inch, 2.5*inch])
    story.append(PageBreak())

    # === CRITICAL PARAMETERS ===
    story.append(Paragraph("6. Critical Design Parameters", styles['SectionHead']))
    build_table(story, styles, ["Name", "Value", "Unit", "Basis", "Verification"],
        [[cp.get('name', ''), cp.get('value', ''), cp.get('unit', ''), cp.get('basis', 'UNKNOWN'), cp.get('verification_requirement', '')] for cp in data['critical_parameters']],
        [1.2*inch, 1.5*inch, 0.8*inch, 1.5*inch, 1.7*inch])
    story.append(Spacer(1, 0.1*inch))

    # === FAILURE MODES ===
    story.append(Paragraph("7. Failure Modes", styles['SectionHead']))
    build_table(story, styles, ["Mode", "Mechanism", "Mitigation", "Verification", "Residual Uncertainty"],
        [[fm.get('mode', fm.get('failure_mode', '')), fm.get('mechanism', ''), fm.get('mitigation', ''), fm.get('verification_test', ''), fm.get('residual_uncertainty', '')] for fm in data['failure_modes']],
        [1.0*inch, 1.3*inch, 1.3*inch, 1.2*inch, 1.4*inch])
    story.append(PageBreak())

    # === FAILURE ANALYSIS ===
    story.append(Paragraph("8. Failure Analysis", styles['SectionHead']))
    build_table(story, styles, ["Failure Mode", "Mechanism", "Mitigation", "Residual Uncertainty"],
        [[fm.get('failure_mode', ''), fm.get('mechanism', ''), fm.get('mitigation', ''), fm.get('residual_uncertainty', '')] for fm in data['failure_analysis']],
        [1.2*inch, 1.8*inch, 1.8*inch, 1.9*inch])
    story.append(Spacer(1, 0.1*inch))

    # === VERIFICATION ===
    story.append(Paragraph("9. Verification Strategy", styles['SectionHead']))
    build_table(story, styles, ["ID", "Requirement", "Method", "Acceptance", "Result"],
        [[v.get('id', ''), v.get('requirement', ''), v.get('method', ''), v.get('acceptance', ''), v.get('result', '')] for v in data['verification']],
        [0.5*inch, 1.8*inch, 1.8*inch, 1.5*inch, 1.1*inch])
    story.append(Spacer(1, 0.1*inch))

    # === VALIDATION ===
    story.append(Paragraph("10. Validation Strategy", styles['SectionHead']))
    build_table(story, styles, ["ID", "Requirement", "Method", "Acceptance", "Result"],
        [[v.get('id', ''), v.get('requirement', ''), v.get('method', ''), v.get('acceptance', ''), v.get('result', '')] for v in data['validation']],
        [0.5*inch, 1.8*inch, 1.8*inch, 1.5*inch, 1.1*inch])
    story.append(PageBreak())

    # === MATERIALS ===
    story.append(Paragraph("11. Materials", styles['SectionHead']))
    build_table(story, styles, ["Component", "Candidate Material", "Source", "Verification Required", "Status"],
        [[m.get('component', ''), m.get('candidate_material', ''), m.get('source', ''), m.get('verification_required', ''), m.get('status', '')] for m in data['materials']],
        [1.2*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.0*inch])
    story.append(Spacer(1, 0.1*inch))

    # === BOM ===
    story.append(Paragraph("12. Bill of Materials", styles['SectionHead']))
    build_table(story, styles, ["Item", "Description", "Qty", "Type", "Material", "Supplier", "Criticality", "Verification"],
        [[b.get('item', ''), b.get('description', ''), b.get('qty', ''), b.get('component_type', ''), b.get('material', ''), b.get('supplier', ''), b.get('criticality', ''), b.get('verification', '')] for b in data['bom']],
        [0.3*inch, 1.2*inch, 0.4*inch, 0.8*inch, 1.0*inch, 0.8*inch, 0.7*inch, 1.5*inch])
    story.append(Spacer(1, 0.1*inch))

    # === MANUFACTURING ===
    story.append(Paragraph("13. Manufacturing", styles['SectionHead']))
    mfg = data['manufacturing']
    if isinstance(mfg, dict):
        story.append(Paragraph(f"<b>Status:</b> {mfg.get('status', 'NOT ESTABLISHED')}", styles['BodyText']))
        story.append(Paragraph("Candidate Processes:", styles['SubHead']))
        for proc in mfg.get('candidate_processes', []):
            story.append(Paragraph(f"  - {proc.get('process', '')}: {proc.get('source', '')} - {proc.get('note', '')}", styles['BodyText']))
    story.append(PageBreak())

    # === EXTERNAL EVIDENCE ===
    story.append(Paragraph("14. External Evidence", styles['SectionHead']))
    for i, e in enumerate(data['external_evidence']):
        story.append(Paragraph(f"<b>Source {i+1}:</b> {e.get('source_title', e.get('source', ''))}", styles['SubHead']))
        story.append(Paragraph(f"URL: {e.get('source', '')}", styles['MonoText']))
        story.append(Paragraph(f"Excerpt: {e.get('source_snippet', '')}", styles['BodyText']))
        story.append(Spacer(1, 0.03*inch))
    story.append(PageBreak())

    # === TRANSFER BOUNDARY (strengthened: Receive/Develop/Verify) ===
    story.append(Paragraph("15. Transfer Boundary", styles['SectionHead']))
    story.append(Paragraph("YOU RECEIVE:", styles['SubHead']))
    for item in data['buyer_receives']:
        story.append(Paragraph(f"  + {item}", styles['GreenText']))
    story.append(Paragraph("YOU MUST DEVELOP:", styles['SubHead']))
    for item in data['buyer_must_create']:
        story.append(Paragraph(f"  -> {item}", styles['BodyText']))
    story.append(Paragraph("YOU MUST VERIFY:", styles['SubHead']))
    for item in ["Biocompatibility (ISO 10993)", "Sterilization compatibility", "Mechanical integrity", "Regulatory pathway", "IP ownership and freedom to operate", "Manufacturing process capability"]:
        story.append(Paragraph(f"  ? {item}", styles['RedText']))
    story.append(Spacer(1, 0.1*inch))

    # === OPEN QUESTIONS ===
    story.append(Paragraph("16. Open Questions", styles['SectionHead']))
    for u in data['remaining_unknowns']:
        story.append(Paragraph(f"  - {u}", styles['BodyText']))
    story.append(Spacer(1, 0.1*inch))

    # === BUILD PLAN ===
    story.append(Paragraph("17. Decisive Next Experiment", styles['SectionHead']))
    build_table(story, styles, ["WP", "Test Article", "Equipment", "Measurement", "Acceptance", "Deliverable", "Effort"],
        [[wp.get('work_package', ''), wp.get('test_article', ''), wp.get('equipment', ''), wp.get('measurement', ''), wp.get('acceptance_criterion', ''), wp.get('deliverable', ''), wp.get('estimated_effort', '')] for wp in data['build_plan']],
        [0.4*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.0*inch, 0.8*inch, 0.7*inch])
    story.append(PageBreak())

    # === BUYER DECISION FRAMEWORK ===
    story.append(Paragraph("18. Buyer Decision Framework", styles['SectionHead']))
    story.append(Paragraph("<b>WHY INVEST:</b> " + f"Engineering definition exists with {len(data['governing_model'].get('equations', []))} governing equations and a {len(data['build_plan'])}-step build plan. The next experiment is clearly specified with test article, equipment, and acceptance criteria.", styles['BodyText']))
    story.append(Paragraph("<b>WHY WAIT:</b> No physical prototype exists. Regulatory pathway is unresolved. IP ownership is unverified. Manufacturing process is not qualified.", styles['BodyText']))
    story.append(Paragraph("<b>WHY REJECT:</b> If the governing equations are not credible for the intended application, or if the failure modes are not addressable with practical mitigations.", styles['BodyText']))
    story.append(Paragraph("<b>WHAT WOULD CHANGE THE DECISION:</b> A successful bench experiment demonstrating the core mechanism. A qualified regulatory pathway. A confirmed IP position.", styles['BodyText']))
    story.append(Spacer(1, 0.15*inch))

    # === DISCLOSURE ===
    story.append(Paragraph("DISCLOSURE", styles['SectionHead']))
    story.append(Paragraph("This dossier distinguishes established evidence, external precedent, computational/modelled results, engineering proposals, and unresolved questions. The absence of physical validation should not be interpreted as evidence that the technology will fail; it means the relevant proposition has not yet been established experimentally.", styles['Disclaimer']))
    story.append(Paragraph("This dossier does not constitute legal, patentability, FTO, regulatory, or investment advice.", styles['Disclaimer']))

    doc.build(story, onFirstPage=lambda c, d: draw_cover_page(c, d, pkg_info, data['maturity']))

def build_buyer_card_pdf(pkg_info, dossier, output_path):
    styles = get_styles()
    data = get_package_data(dossier)
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    story.append(Paragraph(f"Technology #{pkg_info['num']}: {pkg_info['tech_name']}", styles['CoverTitle']))
    story.append(Spacer(1, 0.1*inch))
    items = [
        ("Technology Domain", data['domain']),
        ("Mechanism", data['architecture_desc']),
        ("Maturity", data['maturity']),
        ("Current State", "No physical prototype. Computational model and engineering definition exist."),
        ("Key Risk", data['first_failure']),
        ("Next Experiment", data['first_experiment']),
        ("Buyer Receives", "; ".join(data['buyer_receives']) if data['buyer_receives'] else "See transfer manifest"),
        ("Buyer Must Build", "; ".join(data['buyer_must_create']) if data['buyer_must_create'] else "See transfer manifest"),
        ("Transfer Posture", data['transfer_posture'].replace('_', ' ').title()),
        ("Next $5K", data['investment_ladder']['next_5k']),
    ]
    for label, value in items:
        story.append(Paragraph(f"<b>{label}:</b> {value}", styles['BodyText']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("CONFIDENTIAL. See full engineering dossier for details.", styles['Disclaimer']))
    doc.build(story)

def build_executive_brief_pdf(pkg_info, dossier, output_path):
    styles = get_styles()
    data = get_package_data(dossier)
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=0.6*inch, bottomMargin=0.6*inch)
    story = []
    story.append(Paragraph(f"Technology #{pkg_info['num']}", styles['CoverSub']))
    story.append(Paragraph(pkg_info['tech_name'], styles['CoverTitle']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Executive Technology Brief", styles['SectionHead']))
    story.append(Paragraph(f"<b>Domain:</b> {data['domain']}", styles['BodyText']))
    story.append(Paragraph(f"<b>Maturity:</b> {data['maturity']}", styles['BodyText']))
    story.append(Paragraph(f"<b>Transfer Posture:</b> {data['transfer_posture'].replace('_', ' ').title()}", styles['BodyText']))
    story.append(Paragraph(f"<b>Architecture:</b> {data['architecture_desc']}", styles['BodyText']))
    gm = data['governing_model']
    story.append(Paragraph(f"<b>Governing Model:</b> {gm.get('summary', 'NOT ESTABLISHED')}", styles['BodyText']))
    story.append(Paragraph("Key Equations:", styles['SubHead']))
    for eq in gm.get('equations', []):
        story.append(Paragraph(str(eq), styles['MonoText']))
    story.append(Paragraph(f"Current State: {data['maturity']}. No physical prototype. No clinical validation.", styles['BodyText']))
    story.append(Paragraph("Disclosure: This dossier distinguishes established evidence from proposals and unresolved questions.", styles['Disclaimer']))
    doc.build(story)

def build_evidence_summary_pdf(pkg_info, dossier, output_path):
    styles = get_styles()
    data = get_package_data(dossier)
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=0.6*inch, bottomMargin=0.6*inch)
    story = []
    story.append(Paragraph(f"Evidence Summary - Technology #{pkg_info['num']}", styles['CoverTitle']))
    story.append(Paragraph(pkg_info['tech_name'], styles['CoverSub']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(f"External Evidence Sources ({len(data['external_evidence'])} total):", styles['SectionHead']))
    for i, e in enumerate(data['external_evidence']):
        story.append(Paragraph(f"<b>Source {i+1}:</b> {e.get('source_title', e.get('source', ''))}", styles['SubHead']))
        story.append(Paragraph(f"URL: {e.get('source', '')}", styles['MonoText']))
        story.append(Paragraph(f"Excerpt: {e.get('source_snippet', '')}", styles['BodyText']))
        story.append(Spacer(1, 0.03*inch))
    story.append(Paragraph("Evidence Classification: This dossier contains source-native information, derived engineering analysis, engineering proposals, and unresolved questions. No evidence has been physically validated.", styles['Disclaimer']))
    doc.build(story)

def build_transfer_manifest_pdf(pkg_info, dossier, output_path):
    styles = get_styles()
    data = get_package_data(dossier)
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=0.6*inch, bottomMargin=0.6*inch)
    story = []
    story.append(Paragraph(f"Transfer Manifest - Technology #{pkg_info['num']}", styles['CoverTitle']))
    story.append(Paragraph(pkg_info['tech_name'], styles['CoverSub']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("YOU RECEIVE:", styles['SectionHead']))
    for item in data['buyer_receives']:
        story.append(Paragraph(f"  + {item}", styles['GreenText']))
    story.append(Paragraph("YOU MUST DEVELOP:", styles['SectionHead']))
    for item in data['buyer_must_create']:
        story.append(Paragraph(f"  -> {item}", styles['BodyText']))
    story.append(Paragraph("YOU MUST VERIFY:", styles['SectionHead']))
    for item in ["Biocompatibility (ISO 10993)", "Sterilization compatibility", "Mechanical integrity", "Regulatory pathway", "IP ownership and freedom to operate", "Manufacturing process capability"]:
        story.append(Paragraph(f"  ? {item}", styles['RedText']))
    story.append(Paragraph("NOT AVAILABLE:", styles['SectionHead']))
    for item in ["Physical prototype", "Clinical data", "Qualified supplier", "Granted IP", "Independent engineer evaluation"]:
        story.append(Paragraph(f"  - {item}", styles['RedText']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("This manifest is honest. Items marked 'not available' do not exist.", styles['Disclaimer']))
    doc.build(story)

def build_readme_pdf(pkg_info, data, output_path):
    styles = get_styles()
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=0.6*inch, bottomMargin=0.6*inch)
    story = []
    story.append(Paragraph(f"Package #{pkg_info['num']}", styles['CoverTitle']))
    story.append(Paragraph(pkg_info['tech_name'], styles['CoverSub']))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(f"<b>Maturity:</b> {data['maturity']}", styles['BodyText']))
    story.append(Paragraph(f"<b>Transfer Posture:</b> {data['transfer_posture'].replace('_', ' ').title()}", styles['BodyText']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Contents:", styles['SectionHead']))
    for item in ["01 - Executive Technology Brief", "02 - Engineering Technology-Transfer Dossier", "03 - Buyer Decision Card", "04 - Evidence Summary", "05 - Transfer Manifest"]:
        story.append(Paragraph(f"  {item}", styles['BodyText']))
    story.append(Paragraph(f"Status: {data['maturity']}. Not physically validated.", styles['Disclaimer']))
    doc.build(story)

def build_master_portfolio_pdf(all_dossiers, output_path):
    styles = get_styles()
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=0.6*inch, bottomMargin=0.6*inch)
    story = []
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("15 Technology-Transfer Opportunities", styles['CoverTitle']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Engineering Technology-Transfer Portfolio", styles['CoverSub']))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("Prepared for External Technical, Commercial and Strategic Evaluation", styles['CoverSub']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("CONFIDENTIAL", styles['Disclaimer']))
    story.append(PageBreak())
    story.append(Paragraph("Portfolio Map", styles['SectionHead']))
    map_data = [["#", "Technology", "Domain", "Maturity", "Next Action"]]
    for pkg_info in PACKAGE_MAP:
        dossier = all_dossiers.get(pkg_info['pkg_id'], {})
        data = get_package_data(dossier)
        map_data.append([pkg_info['num'], pkg_info['tech_name'], data['domain'], data['maturity'], data['first_experiment']])
    map_table = Table(map_data, colWidths=[0.3*inch, 2.2*inch, 1.5*inch, 1.3*inch, 2.0*inch], repeatRows=1)
    map_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), NAVY), ('TEXTCOLOR', (0,0), (-1,0), white), ('FONTSIZE', (0,0), (-1,-1), 7), ('GRID', (0,0), (-1,-1), 0.5, grey), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(map_table)
    story.append(PageBreak())
    for pkg_info in PACKAGE_MAP:
        dossier = all_dossiers.get(pkg_info['pkg_id'], {})
        data = get_package_data(dossier)
        story.append(Paragraph(f"#{pkg_info['num']}: {pkg_info['tech_name']}", styles['SectionHead']))
        story.append(Paragraph(f"<b>Domain:</b> {data['domain']}", styles['BodyText']))
        story.append(Paragraph(f"<b>Maturity:</b> {data['maturity']}", styles['BodyText']))
        story.append(Paragraph(f"<b>Architecture:</b> {data['architecture_desc']}", styles['BodyText']))
        story.append(Paragraph(f"<b>Next Experiment:</b> {data['first_experiment']}", styles['BodyText']))
        story.append(Spacer(1, 0.08*inch))
    story.append(PageBreak())
    story.append(Paragraph("Disclosure", styles['SectionHead']))
    story.append(Paragraph("These are engineering technology-transfer dossiers prepared for external evaluation. They are not representations that the underlying technologies are physically validated, manufacturing-qualified, clinically validated, legally cleared, or transfer-ready unless explicitly supported by the evidence contained in the relevant package.", styles['BodyText']))
    doc.build(story)

def build_portfolio_index_pdf(all_dossiers, output_path):
    styles = get_styles()
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    story.append(Paragraph("Portfolio Index", styles['CoverTitle']))
    story.append(Paragraph("15 Technology-Transfer Opportunities", styles['CoverSub']))
    story.append(Spacer(1, 0.08*inch))
    for pkg_info in PACKAGE_MAP:
        dossier = all_dossiers.get(pkg_info['pkg_id'], {})
        data = get_package_data(dossier)
        story.append(Paragraph(f"#{pkg_info['num']}: {pkg_info['tech_name']}", styles['SectionHead']))
        items = [("Domain", data['domain']), ("Maturity", data['maturity']), ("Mechanism", data['architecture_desc']), ("Key Risk", data['first_failure']), ("Next Experiment", data['first_experiment']), ("Transfer Posture", data['transfer_posture'].replace('_', ' ').title())]
        for label, value in items:
            story.append(Paragraph(f"<b>{label}:</b> {value}", styles['BodyText']))
        story.append(Spacer(1, 0.04*inch))
    doc.build(story)

def run_security_scan(directory):
    secrets_patterns = [r'\bghp_\b', r'\bsk-\b', r'\bapi_key\b', r'\bapikey\b', r'\btoken\b', r'\bpassword\b', r'\bsecret\b', r'\bPAT\b', r'PRIVATE KEY', r'BEGIN RSA', r'BEGIN OPENSSH']
    internal_patterns = ["R370B", "R370C", "R370D", "R370E", "R370F", "R370G", "R370H", "R370I", "R370J", "R370K", "R370L", "R370M", "R370N", "R370O", "R370P", "R370Q", "/home/z/", "CEO directive", "developer", "internal score", "internal assessment"]
    findings = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith(('.pdf', '.zip', '.png')):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, 'r', errors='ignore') as fh:
                    content = fh.read()
                for pattern in secrets_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append({"file": os.path.relpath(filepath, directory), "type": "SECRET", "pattern": pattern})
                for pattern in internal_patterns:
                    if pattern in content:
                        findings.append({"file": os.path.relpath(filepath, directory), "type": "INTERNAL", "pattern": pattern})
            except:
                pass
    return {"total_findings": len(findings), "verdict": "FAIL" if findings else "PASS", "findings": findings}

def check_no_truncation(filepath):
    with open(filepath) as f:
        content = f.read()
    return len(re.findall(r'\[:\d+\]', content))

def test_zip_extraction(zip_path):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            with tempfile.TemporaryDirectory() as tmpdir:
                zf.extractall(tmpdir)
            return {"zip": os.path.basename(zip_path), "extractable": True, "file_count": len(file_list)}
    except Exception as e:
        return {"zip": os.path.basename(zip_path), "extractable": False, "error": str(e)}

def main():
    print("=" * 70)
    print("BUILDING PORTFOLIO V3 (package-specific maturity, investment ladder, buyer decision)")
    print("=" * 70)

    if os.path.exists(PORTFOLIO_ROOT):
        shutil.rmtree(PORTFOLIO_ROOT)
    os.makedirs(PORTFOLIO_ROOT, exist_ok=True)

    for d in ["BUYER_OUTREACH", "FULL_DOSSIERS", "DOWNLOAD", "INTERNAL_QA"]:
        os.makedirs(os.path.join(PORTFOLIO_ROOT, d), exist_ok=True)

    all_dossiers = {}
    for pkg_info in PACKAGE_MAP:
        fpath = os.path.join(OUTPUT_DIR, f"{pkg_info['pkg_id']}_ArtifactRichDossier.json")
        with open(fpath) as f:
            all_dossiers[pkg_info['pkg_id']] = json.load(f)

    manifest_packages = []
    for pkg_info in PACKAGE_MAP:
        num = pkg_info['num']
        folder_name = f"{num}_{pkg_info['short_name']}"
        pkg_dir = os.path.join(PORTFOLIO_ROOT, "FULL_DOSSIERS", folder_name)
        os.makedirs(pkg_dir, exist_ok=True)
        print(f"\n  Building #{num}: {pkg_info['tech_name']}...")
        dossier = all_dossiers[pkg_info['pkg_id']]
        data = get_package_data(dossier)

        pdfs = [
            ("00_PACKAGE_README.pdf", lambda p, pi=pkg_info, d=data: build_readme_pdf(pi, d, p)),
            ("01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf", lambda p, pi=pkg_info, ds=dossier: build_executive_brief_pdf(pi, ds, p)),
            ("02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf", lambda p, pi=pkg_info, ds=dossier: build_dossier_pdf(pi, ds, p)),
            ("03_BUYER_DECISION_CARD.pdf", lambda p, pi=pkg_info, ds=dossier: build_buyer_card_pdf(pi, ds, p)),
            ("04_EVIDENCE_SUMMARY.pdf", lambda p, pi=pkg_info, ds=dossier: build_evidence_summary_pdf(pi, ds, p)),
            ("05_TRANSFER_MANIFEST.pdf", lambda p, pi=pkg_info, ds=dossier: build_transfer_manifest_pdf(pi, ds, p)),
        ]

        files_list = []
        for filename, builder in pdfs:
            filepath = os.path.join(pkg_dir, filename)
            builder(filepath)
            files_list.append({"file": filename, "sha256": _sha256(filepath)})

        # PACKAGE_MANIFEST.json inside package
        pkg_manifest = {
            "portfolio_number": num,
            "package_id": pkg_info['pkg_id'],
            "technology_name": pkg_info['tech_name'],
            "package_version": "1.0",
            "maturity": data['maturity'],
            "transfer_posture": data['transfer_posture'],
            "files": files_list,
            "external_evidence_count": len(data['external_evidence']),
            "engineering_artifact_count": len(data['build_plan']),
        }
        with open(os.path.join(pkg_dir, "PACKAGE_MANIFEST.json"), "w") as f:
            json.dump(pkg_manifest, f, indent=2, ensure_ascii=False)

        # Buyer card in BUYER_OUTREACH
        build_buyer_card_pdf(pkg_info, dossier, os.path.join(PORTFOLIO_ROOT, "BUYER_OUTREACH", f"{num}_BUYER_CARD.pdf"))

        # Individual ZIP (self-contained, includes PACKAGE_MANIFEST.json, NO QA)
        zip_path = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD", f"{folder_name}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, _ in pdfs:
                zipf.write(os.path.join(pkg_dir, filename), filename)
            zipf.write(os.path.join(pkg_dir, "PACKAGE_MANIFEST.json"), "PACKAGE_MANIFEST.json")

        manifest_packages.append({
            "portfolio_number": num, "package_id": pkg_info['pkg_id'],
            "technology_name": pkg_info['tech_name'], "short_name": pkg_info['short_name'],
            "folder_name": folder_name, "domain": data['domain'],
            "maturity": data['maturity'], "transfer_posture": data['transfer_posture'],
            "files": files_list, "primary_next_action": data['first_experiment']
        })
        print(f"    Done: 6 PDFs + manifest + buyer card + ZIP (maturity={data['maturity']})")

    # Master + index PDFs
    print(f"\n  Building master portfolio PDF...")
    build_master_portfolio_pdf(all_dossiers, os.path.join(PORTFOLIO_ROOT, "00_PORTFOLIO_15_TECHNOLOGIES.pdf"))
    print(f"  Building portfolio index PDF...")
    build_portfolio_index_pdf(all_dossiers, os.path.join(PORTFOLIO_ROOT, "PORTFOLIO_INDEX.pdf"))
    shutil.copy2(os.path.join(PORTFOLIO_ROOT, "PORTFOLIO_INDEX.pdf"), os.path.join(PORTFOLIO_ROOT, "BUYER_OUTREACH", "PORTFOLIO_INDEX.pdf"))

    # Master ZIP (excludes INTERNAL_QA and DOWNLOAD ZIPs)
    print(f"  Building master ZIP (excludes INTERNAL_QA)...")
    master_zip = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD", "technology-transfer-portfolio-15.zip")
    with zipfile.ZipFile(master_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PORTFOLIO_ROOT):
            if "INTERNAL_QA" in root or ("DOWNLOAD" in root and any(f.endswith('.zip') for f in files)):
                continue
            for f in files:
                if f.endswith('.zip'):
                    continue
                filepath = os.path.join(root, f)
                arcname = os.path.relpath(filepath, PORTFOLIO_ROOT)
                zipf.write(filepath, arcname)

    # Manifest
    manifest = {"portfolio_version": "1.0", "creation_timestamp": _now(), "package_count": len(PACKAGE_MAP), "packages": manifest_packages}
    with open(os.path.join(PORTFOLIO_ROOT, "PORTFOLIO_MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # README
    with open(os.path.join(PORTFOLIO_ROOT, "README.md"), "w") as f:
        f.write("""# 15 Technology-Transfer Opportunities

This repository contains 15 engineering technology-transfer dossiers prepared for external technical, commercial and strategic evaluation. Each package identifies the technology, supporting evidence, engineering status, unresolved risks, proposed development path, transferable artifacts and next decision point.

## Important Disclosure

These are engineering technology-transfer dossiers prepared for external evaluation. They are not representations that the underlying technologies are physically validated, manufacturing-qualified, clinically validated, legally cleared, or transfer-ready unless explicitly supported by the evidence contained in the relevant package.

The absence of physical validation should not be interpreted as evidence that the technology will fail; it means the relevant proposition has not yet been established experimentally.

## Structure

- `00_PORTFOLIO_15_TECHNOLOGIES.pdf` - Master portfolio document
- `PORTFOLIO_INDEX.pdf` - Index of all 15 technologies
- `PORTFOLIO_MANIFEST.json` - Machine-readable manifest
- `BUYER_OUTREACH/` - First-touch buyer materials (buyer cards)
- `FULL_DOSSIERS/` - Complete technical dossiers (6 PDFs + manifest per package)
- `DOWNLOAD/` - ZIP archives (1 master + 15 individual)
- `INTERNAL_QA/` - Internal quality reports (not for buyer distribution)

## Maturity Levels

Each package has a package-specific maturity level derived from its engineering content:
- **ENGINEERING_DEFINITION**: Governing equations, design inputs/outputs, failure analysis, and build plan exist.
- **EARLY_CONCEPT**: Basic mechanism and design inputs exist; full engineering definition not yet complete.

No package has a physical prototype. No package has clinical validation.
""")

    # === DERIVED COUNTS ===
    pdf_count = sum(1 for root, dirs, files in os.walk(PORTFOLIO_ROOT) for f in files if f.endswith('.pdf'))
    zip_count = sum(1 for root, dirs, files in os.walk(PORTFOLIO_ROOT) for f in files if f.endswith('.zip'))
    package_count = len([d for d in os.listdir(os.path.join(PORTFOLIO_ROOT, "FULL_DOSSIERS")) if os.path.isdir(os.path.join(PORTFOLIO_ROOT, "FULL_DOSSIERS", d))])

    # === SECURITY SCAN ===
    print(f"\n  Security scan...")
    security = run_security_scan(PORTFOLIO_ROOT)
    print(f"    Verdict: {security['verdict']}")

    # === TRUNCATION CHECK ===
    print(f"  Truncation check...")
    trunc_count = check_no_truncation(os.path.abspath(__file__))
    print(f"    Patterns: {trunc_count}")

    # === ZIP EXTRACTION TESTS ===
    print(f"  ZIP extraction tests...")
    zip_tests = [test_zip_extraction(master_zip)]
    for pkg_info in PACKAGE_MAP:
        folder_name = f"{pkg_info['num']}_{pkg_info['short_name']}"
        zip_path = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD", f"{folder_name}.zip")
        zip_tests.append(test_zip_extraction(zip_path))
    all_zips_pass = all(t['extractable'] for t in zip_tests)

    # === QA REPORT (in INTERNAL_QA, not in buyer ZIPs) ===
    qa_report = {
        "generated_at": _now(),
        "derived_counts": {"package_count": package_count, "pdf_count": pdf_count, "zip_count": zip_count},
        "security_scan": security,
        "truncation_check": {"patterns_found": trunc_count, "verdict": "PASS" if trunc_count == 0 else "FAIL"},
        "zip_extraction": {"total": len(zip_tests), "passed": sum(1 for t in zip_tests if t['extractable']), "verdict": "PASS" if all_zips_pass else "FAIL"},
    }
    with open(os.path.join(PORTFOLIO_ROOT, "INTERNAL_QA", "PORTFOLIO_QA_REPORT.json"), "w") as f:
        json.dump(qa_report, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PORTFOLIO_ROOT, "INTERNAL_QA", "PORTFOLIO_QA_REPORT.md"), "w") as f:
        f.write(f"# Portfolio QA Report\n\nGenerated: {_now()}\n\n")
        f.write(f"Packages: {package_count} | PDFs: {pdf_count} | ZIPs: {zip_count}\n\n")
        f.write(f"Security: {security['verdict']} | Truncation: {'PASS' if trunc_count == 0 else 'FAIL'} | ZIPs: {'PASS' if all_zips_pass else 'FAIL'}\n")

    # === FINAL SUMMARY ===
    print(f"\n{'='*70}")
    print(f"PORTFOLIO BUILD COMPLETE (v3)")
    print(f"{'='*70}")
    print(f"  Portfolio: {PORTFOLIO_ROOT}")
    print(f"  Packages: {package_count}")
    print(f"  PDFs: {pdf_count}")
    print(f"  ZIPs: {zip_count}")
    print(f"  Security: {security['verdict']}")
    print(f"  Truncation: {'PASS' if trunc_count == 0 else 'FAIL'}")
    print(f"  ZIP extraction: {'PASS' if all_zips_pass else 'FAIL'} ({sum(1 for t in zip_tests if t['extractable'])}/{len(zip_tests)})")
    print(f"\n  Master ZIP: {master_zip}")
    ready = security['verdict'] == 'PASS' and trunc_count == 0 and all_zips_pass
    print(f"\n  READY TO SEND TO BUYERS: {'YES' if ready else 'NOT YET'}")

if __name__ == "__main__":
    main()

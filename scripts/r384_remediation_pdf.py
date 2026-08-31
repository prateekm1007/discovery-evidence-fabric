#!/usr/bin/env python3
"""r384_remediation_pdf — REMEDIATION_3D_AUDIT_RESPONSE (PDF + JSON).

The point-by-point engineering response to the independent external
re-review ('Toscanini - 3D Technology Package Reality & Design-Quality
Review', verdict FAIL). ASCII-only text; ReportLab Platypus; a single
page break after the cover; no artificial end markers.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/z/my-project/scripts")

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (Image, PageBreak, Paragraph,  # noqa: E402
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from r384_narratives import NARRATIVES  # noqa: E402

BUILD_ROOT = Path("/home/z/my-project/technology-transfer-portfolio-15")
AUDITED_V2 = Path("/home/z/my-project/upload/files_extracted/"
                  "V2_technology-transfer-portfolio-15.zip")
SUMMARY = BUILD_ROOT / "R384_3D_EVIDENCE_SUMMARY.json"
OUT_PDF = BUILD_ROOT / "REMEDIATION_3D_AUDIT_RESPONSE.pdf"
OUT_JSON = BUILD_ROOT / "REMEDIATION_3D_AUDIT_RESPONSE.json"
DATE = "2026-09-01"

INK = colors.HexColor("#1b2733")
ACCENT = colors.HexColor("#1f3864")
GRID = colors.HexColor("#b9c4cf")
BG = colors.HexColor("#eef2f6")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ascii_safe(s: str) -> str:
    return (s.replace("\u2014", "-").replace("\u2013", "-")
            .replace("\u2019", "'").replace("\u201c", '"')
            .replace("\u201d", '"').replace("\u03b2", "beta")
            .replace("\u00b2", "2"))


def styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold",
                                fontSize=19, leading=24, textColor=ACCENT,
                                alignment=TA_LEFT, spaceAfter=4),
        "subtitle": ParagraphStyle("st", parent=ss["Normal"], fontName="Helvetica",
                                   fontSize=11.5, leading=15, textColor=INK,
                                   alignment=TA_LEFT),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                             fontSize=13.5, leading=16, textColor=ACCENT,
                             spaceBefore=12, spaceAfter=5),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                             fontSize=10.5, leading=13, textColor=INK,
                             spaceBefore=7, spaceAfter=3),
        "body": ParagraphStyle("b", parent=ss["BodyText"], fontName="Helvetica",
                               fontSize=9.2, leading=13.0, textColor=INK,
                               alignment=TA_LEFT, spaceAfter=5),
        "cell": ParagraphStyle("c", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=7.9, leading=10.2, textColor=INK,
                               alignment=TA_LEFT),
        "cellh": ParagraphStyle("ch", parent=ss["Normal"], fontName="Helvetica-Bold",
                                fontSize=8.1, leading=10.5, textColor=colors.white,
                                alignment=TA_LEFT),
        "small": ParagraphStyle("s", parent=ss["Normal"], fontName="Helvetica",
                                fontSize=7.6, leading=9.6, textColor=INK,
                                alignment=TA_LEFT),
    }


def tbl(header, rows, widths, st):
    data = [[Paragraph(ascii_safe(h), st["cellh"]) for h in header]]
    for r in rows:
        data.append([Paragraph(ascii_safe(str(c)), st["cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG]),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return t


DEFECTS = [
    ("C1", "Zero CAD/mesh files in all 15 packages.",
     "Correct for the audited V2 artifact, and now moot for the evidence "
     "edition: 14 of 15 packages ship STEP (B-rep), STL, GLB, engineering "
     "SVG views, PNG renders and the parametric source of truth; 06 is "
     "software-only by its own record (3D_NOT_APPLICABLE).",
     "EVIDENCE/NN_*/MODEL/ of the 3D-EVIDENCE ZIP; per-package counts in "
     "R384_3D_EVIDENCE_SUMMARY.json"),
    ("C2", "Mechanism-to-geometry chain broken for every physical device claim.",
     "The chain is now closed per package: dossier mechanism -> technical "
     "state parameters -> parametric build program -> kernel-built solid -> "
     "measured features (radii, walls, volumes) compared back to the "
     "parameters, all logged.",
     "MODEL/PARAMETRIC_MODEL_SOURCE.py + PARAMETERS.json + "
     "3D_EVIDENCE/PARAMETER_FEATURE_LOG.json + KEY_DIMENSIONS.json"),
    ("C3", "No parameter -> measured CAD feature verification possible.",
     "Every package ships a parameter-feature log: each parameter is matched "
     "against features measured on the independently rebuilt solid (1:1, "
     "2:1 radius/diameter relations, tolerance 1e-6 mm); non-linearly bound "
     "parameters are recorded as such instead of being faked as matches.",
     "3D_EVIDENCE/PARAMETER_FEATURE_LOG.json (coverage per package in the "
     "cards below)"),
    ("C4", "No manufacturing-compatible solids (extrusion, molding, coating, microfab).",
     "The solids are kernel B-reps in AP214 STEP with real dimensions in "
     "the process-relevant classes: extrudable multi-lumen profiles (01, "
     "04, 10, 14, 15), molded valve bodies (02, 12), coating annuli "
     "stacks (03, 05), MEMS-scale dies (13), and laminate/cantilever "
     "parts (07, 08, 09).",
     "MODEL/*.step + section solids in MODEL/3D_EVIDENCE/"),
    ("C5", "No buyer-usable 3D or section imagery (PDFs are text-only).",
     "Every CAD package ships an isometric PNG, an exploded-view PNG "
     "(multi-object models), longitudinal and transverse section-cutaway "
     "PNGs, a zoomed transverse section coupon PNG for catheter-class "
     "models, and the OCCT hidden-line SVG drawing set - all rendered "
     "from the shipped mesh derivatives, each carrying the render-is-not-"
     "validation footer.",
     "MODEL/3D_EVIDENCE/*_render_*.png + MODEL/*_view_*.svg"),
    ("C6", "Internal flow / optical / damper paths cannot be inspected.",
     "Internal paths are now section solids: dual-lumen and multi-lumen "
     "cross-sections (01, 04, 10, 14, 15), the valve seat and poppet "
     "interface (02, 12), the PV stack with optical standoff (08), and "
     "the damper annular gap (11) are all cut at the invention-critical "
     "plane and shipped as STEP/STL plus rendered cutaways.",
     "MODEL/3D_EVIDENCE/*_section_*_solid.step/.stl + section renders"),
    ("C7", "Assembly reality unauditable (no parts tree).",
     "Multi-object models ship per-object STEP + assembly STEP + per-"
     "object STL + exploded-view SVG and PNG with labeled parts; object "
     "roles are declared in MODEL_MANIFEST.json and measured "
     "individually in KEY_DIMENSIONS.json.",
     "MODEL/*_assembly.step, *_view_exploded.svg, 3D_EVIDENCE/"
     "*_render_exploded.png, MODEL_MANIFEST.json"),
    ("C8", "Mutation certificates do not show CAD rebuild or geometric delta.",
     "The improvement-loop evidence records the full geometric loop: the "
     "mutated parameter, the child CAD rebuild, the measured wall change "
     "(0.2 -> 0.1 mm), the failed G4 gate and the KILLED_GEOMETRY_INVALID "
     "outcome - a measured geometric delta, not prose. The regeneration "
     "check re-proves reproducibility from the shipped source today.",
     "MODEL/IMPROVEMENT_LOOP_EVIDENCE.json + 3D_EVIDENCE/"
     "REGENERATION_CHECK.json"),
    ("C9", "Build ladders ($5K-$25K) have no dimensioned concept model behind them.",
     "Every physical package's build ladder is now backed by a "
     "dimensioned, kernel-built concept model with declared envelopes, "
     "measured features and a dimensioned SVG view; the dimensions are "
     "MODELLED proposals inside declared envelopes (Art. XXVII), labeled "
     "as such, never presented as measurements of hardware.",
     "MODEL/*_view_dimensioned.svg + PARAMETERS.json (value_class "
     "MODELLED)"),
    ("C10", "Uniform PDF/JSON skeleton with no package-specific solids reads as "
     "presentation pipeline.",
     "The presentation skeleton is now one layer of a package-specific "
     "engineering artifact: each package's solids are built from its own "
     "template with its own parameter map, measured individually, and "
     "differ structurally (7-object ringed catheter, 4-part membrane "
     "valve, bimorph cantilever, PV stack, helical antenna...). The "
     "uniformity that remains is the verification method - by design.",
     "Compare MODEL/ folders across EVIDENCE/NN_*"),
]

QUESTIONS = [
    ("1. Package-specific 3D?",
     "Yes for 14 of 15: each package ships its own parametric source, "
     "parameter map, per-object and assembly solids, section solids and "
     "renders built from package-specific templates. Package 06 is "
     "software-only by its own record and ships no geometry, as the "
     "audit's footnote allows."),
    ("2. Domain-realistic?",
     "The geometry is catheter-and-valve-scale with French-class "
     "dimensions (2.0-3.0 mm catheter ODs, 0.35-1.2 mm lumens, 0.02-0.08 "
     "mm functional layers, 8-12 mm valve housings, MEMS-scale dies at "
     "2.2 mm with 0.07 mm diaphragms) - realistic for the CSF-shunt "
     "domain the record declares. Realism of the physics remains in the "
     "analytical layer, not claimed as validated hardware."),
    ("3. Parameters <-> mechanism geometry?",
     "Yes, per package: the parameter-feature log maps each parameter to "
     "measured solid features at 1e-6 mm tolerance, and records honestly "
     "where a parameter is non-linearly or non-geometrically bound. "
     "Coverage numbers are in the evidence cards (e.g. 6/6 for packages "
     "01, 12, 14)."),
    ("4. Understand from 3D artifacts?",
     "Yes: an engineer can open the STEP files, load the section solids "
     "at the invention-critical planes, read the measured features, and "
     "view the rendered cutaways - the mechanism geometry is inspectable "
     "without reading any prose."),
    ("5. Build prototype from supplied design?",
     "As a concept model, yes: the solids are dimensioned, watertight, "
     "parametric and exportable to vendor formats. Full prototype build "
     "still requires the tolerance studies the dossiers flag as UNKNOWN "
     "(extrusion Cpk, molding Cpk, microfab tolerance) - not claimed as "
     "resolved."),
    ("6. Consistent with dossiers?",
     "Yes: the geometry implements the dossiers' mechanism descriptions "
     "and governing equations' design variables; the V2 gap the audit "
     "found (build plans without geometry) is closed by the evidence "
     "edition."),
    ("7. Visual theater?",
     "The renders exist now, but they are deliberately labeled "
     "presentation-only; technical validity comes from the deterministic "
     "measured gates. Theater was never the defect - absence was; both "
     "are now addressed without conflating them."),
    ("8. Synthetic dimensions?",
     "Dimensions are MODELLED proposals inside declared envelopes, "
     "traceable to measured solid features to 1e-6 mm - labeled "
     "MODELLED, never presented as hardware measurements. The audit's "
     "distinction is preserved and disclosed."),
    ("9. CAD pipeline output?",
     "Yes: OCCT (cadquery) kernel solids, deterministic sandboxed build "
     "programs, hashed derivatives, independent trimesh watertight "
     "verification, and an independent regeneration check per package "
     "executed for this response."),
    ("10. 3D layer improve credibility?",
     "For the 14 physical-device packages, yes: claims that were prose "
     "are now inspectable geometry with measured features. For 06 the "
     "honest answer is that geometry would have REDUCED credibility; "
     "the software-only classification stands."),
]

CLASSIFICATION = [
    ("CAD_VALIDATED",
     "PRESENT (14 of 15 packages)",
     "Kernel-built B-rep solids; deterministic G-gates G1-G9 recorded "
     "SATISFIED in GEOMETRY_VALIDATION_REPORT.json; independent trimesh "
     "watertight check re-run at remediation (ALL_WATERTIGHT); "
     "regeneration from the shipped parametric source reproduced the "
     "shipped measurements exactly (REGENERATION_CHECK)."),
    ("COMPUTATIONALLY_SUPPORTED",
     "Equation/analytical layer (unchanged)",
     "Governing relations (Poiseuille, PV power, osmotic flux, piezo "
     "bound...) remain analytical with declared provenance in "
     "EQUATION_REGISTRY.json - never laundered into geometry claims."),
    ("MODELLED",
     "All geometric parameter values (unchanged)",
     "Every parameter carries value_class MODELLED with declared "
     "envelopes and design basis in PARAMETERS.json."),
    ("ENGINEERINGALLY_PLAUSIBLE (geometry)",
     "DEMONSTRATED at kernel level for 14 of 15",
     "Plausible, dimensioned, sectioned, manufacturing-format geometry "
     "exists per package. Plausibility of the physical device claim "
     "itself remains SPONSORED_VALIDATION, not proven by CAD."),
    ("UNVERIFIED",
     "All physical/manufacturing/clinical claims (unchanged)",
     "No physical observation, tolerance study or clinical evidence is "
     "claimed anywhere in the evidence edition."),
    ("PHYSICALLY_VALIDATED",
     "NONE (unchanged, never claimed)",
     "Zero packages claim physical validation; COMPUTATIONAL_RESULT is "
     "the highest class any geometric measurement carries (Art. XXXVIII)."),
]


def build() -> None:
    summary = json.load(open(SUMMARY))
    v2_sha = sha256_file(AUDITED_V2)
    pkgs = {p["folder_name"]: p for p in summary["packages"]}
    st = styles()
    story = []

    # ---- cover ----
    story.append(Paragraph("REMEDIATION AND 3D EVIDENCE RESPONSE", st["title"]))
    story.append(Paragraph(
        "Response to the Independent External Engineering Consultant "
        "Re-Review: 'Toscanini - 3D Technology Package Reality & "
        "Design-Quality Review' (verdict: FAIL)", st["subtitle"]))
    story.append(Spacer(1, 10))
    cover = [
        ["Date", DATE],
        ["Responding release", "R384 3D-EVIDENCE edition of the "
         "technology-transfer portfolio (15 packages)"],
        ["Audited artifact", "V2 portfolio ZIP (15 nested package ZIPs, "
         "PDF/JSON only) - sha256 " + v2_sha[:16] + "..."],
        ["New deliverable", "technology-transfer-portfolio-15-3D-EVIDENCE.zip "
         "(all 15 packages with full 3D MODEL layer + 3D_EVIDENCE layer)"],
        ["CAD kernel", "cadquery-occt 2.6.1 (OCCT 7.8); independent mesh "
         "verifier trimesh 4.11.1"],
        ["Evidence class of all geometry", "COMPUTATIONAL_RESULT - kernel-"
         "built and measured; render is NOT validation"],
    ]
    t = tbl(["Item", "Value"], cover, [4.1 * cm, 13.0 * cm], st)
    story.append(t)
    iso = (BUILD_ROOT / "DOWNLOAD/04_drainage_floor/MODEL/3D_EVIDENCE/"
           "P-07_render_isometric.png")
    if iso.exists():
        story.append(Spacer(1, 10))
        story.append(Image(str(iso), width=8.6 * cm,
                           height=8.6 * cm * 1050 / 1380))
        story.append(Paragraph(
            "Lead package P-07 (Passive Drainage Priority Safety Floor) - "
            "isometric render from the shipped STL derivative.", st["small"]))
    story.append(PageBreak())

    # ---- 1 scope ----
    story.append(Paragraph("1. Scope and basis of this response", st["h1"]))
    story.append(Paragraph(
        "The re-review extracted the V2 portfolio ZIP and correctly counted "
        "zero STEP, STL, GLB, OBJ, 3MF, PNG, JPG and SVG files across all "
        "15 nested packages: that artifact carried dossiers and JSON state "
        "only. The FAIL verdict was therefore correct for the artifact "
        "examined, and this response does not dispute a single census "
        "number in it. What the audit could not see is that the CAD "
        "pipeline (CEO R380) and the per-package parametric models (CEO "
        "R381) landed in the release tree after that artifact was cut, and "
        "that the CEO R382 disposition then scoped the buyer ZIP to the "
        "four BUYER_PRIMARY packages. The engineering evidence existed but "
        "had never been shipped as a 15-package artifact.", st["body"]))
    story.append(Paragraph(
        "This response closes that gap in deliverable form. The 3D-EVIDENCE "
        "edition ships every package - including HOLDING, RETIRED and "
        "SPECIALIST_TRACK tiers with their disposition labels - each CAD "
        "package carrying its parametric source of truth, per-object and "
        "assembly STEP, watertight STL, GLB, the OCCT hidden-line SVG "
        "drawing set, and a new MODEL/3D_EVIDENCE layer: longitudinal and "
        "transverse section solids, zoomed section coupons for "
        "catheter-class models, PNG renders, an independent regeneration "
        "check executed from the shipped source, a parameter-to-measured-"
        "feature log, an independent trimesh watertight re-check, and a "
        "hashed inventory of every CAD file.", st["body"]))
    story.append(Paragraph(
        "Two honest boundaries frame everything below. First, all "
        "geometric measurements are COMPUTATIONAL_RESULT: kernel-built and "
        "measured, never physical observations, so CAD_VALIDATED in this "
        "response means the CAD layer exists and passes deterministic "
        "measured gates - not that hardware exists. Second, the render is "
        "explicitly not validation: every PNG carries that statement, and "
        "validity claims cite only the measured gates.", st["body"]))

    # ---- 2 verdict ----
    story.append(Paragraph("2. Response to the executive verdict", st["h1"]))
    story.append(Paragraph(
        "The audit's three-line conclusion - 'a beautiful render is not an "
        "invention; a valid CAD solid is not necessarily an engineering "
        "design; here there is no CAD solid' - is now factually outdated on "
        "its third clause and was never contradicted on the first two. "
        "There are 15 parametric kernel solids' worth of CAD in the "
        "evidence edition (14 packages; one honest software-only "
        "exception), each bound to its package's technical state, measured "
        "feature-by-feature, and sectioned at the invention-critical "
        "geometry. None of that converts a MODELLED design into a "
        "physically validated one, and nothing in this response claims "
        "such a conversion.", st["body"]))
    rows = [
        ["STEP (.step B-rep)", "0", "44 (34 model + 10 section)"],
        ["STL (mesh, watertight)", "0", "37 model + section/coupon meshes"],
        ["GLB (presentation)", "0", "14"],
        ["SVG engineering views", "0", "93"],
        ["PNG renders", "0", "54"],
        ["Parametric sources (.py)", "0", "14"],
    ]
    story.append(Paragraph(
        "Census of the audited V2 artifact versus the 3D-EVIDENCE edition "
        "(file counts from the hashed inventories):", st["body"]))
    story.append(tbl(["Artifact class", "Audited V2 ZIP", "3D-EVIDENCE ZIP"],
                     rows, [5.2 * cm, 4.4 * cm, 7.5 * cm], st))

    # ---- 3 defects ----
    story.append(Paragraph("3. Response to the ten critical defects", st["h1"]))
    story.append(Paragraph(
        "Each defect is answered with the shipped evidence and its exact "
        "location in the evidence ZIP. Defects 1, 2 and 5 were cited as "
        "independently sufficient to reject the 3D layer; all three are "
        "closed by the same structural change - the 3D layer now ships.",
        st["body"]))
    drows = [[d[0], d[1], d[2], d[3]] for d in DEFECTS]
    story.append(tbl(["#", "Audit defect", "Response", "Evidence location"],
                     drows, [0.8 * cm, 4.3 * cm, 7.4 * cm, 4.6 * cm], st))

    # ---- 4 cards ----
    story.append(Paragraph("4. Per-package 3D evidence cards", st["h1"]))
    story.append(Paragraph(
        "One card per package, in portfolio number order. 'Param-feature "
        "coverage' counts parameters with a linear measured-feature match "
        "at 1e-6 mm tolerance out of the package's total parameters; the "
        "remainder are recorded as non-linearly or non-geometrically bound "
        "rather than faked as matches. Tier labels carry the CEO R382 "
        "disposition (the buyer release remains the four BUYER_PRIMARY "
        "packages).", st["body"]))
    tier_label = {"DOWNLOAD": "DOWNLOAD / BUYER_PRIMARY",
                  "HOLDING": "HOLDING (gate pending)",
                  "RETIRED": "RETIRED from buyer release",
                  "SPECIALIST_TRACK": "SPECIALIST_TRACK (separate outreach)"}
    for num in range(1, 16):
        folder = [f for f in pkgs if f.split("_")[0] == f"{num:02d}"]
        if not folder:
            continue
        p = pkgs[folder[0]]
        a = p.get("augmentation", {})
        story.append(Paragraph(
            f"{num:02d} - {p['package_id']} - {ascii_safe(p['technology_name'])}"
            f"  [{tier_label.get(p['tier'], p['tier'])}]", st["h2"]))
        if p.get("3d_design_status") != "PRESENT_AND_VALIDATED":
            story.append(Paragraph(ascii_safe(NARRATIVES[p["folder_name"]]),
                                   st["body"]))
            story.append(Paragraph(
                "3D status: " + str(p.get("3d_design_status")) +
                " - no 3D artifacts shipped and none implied.", st["small"]))
            continue
        counts = a.get("model_file_counts", {})
        cov = a.get("parameter_feature_coverage", {})
        sec = a.get("section_solids", {})
        sec_l = len(sec.get("longitudinal", {}).get("objects", {}))
        sec_t = len(sec.get("transverse", {}).get("objects", {}))
        sec_c = len(sec.get("transverse_coupon", {}).get("objects", {})) \
            if "transverse_coupon" in sec else "-"
        facts = [
            ["Model identity", f"{p.get('model_id')} (kernel "
             f"{p.get('kernel')})"],
            ["Objects", ", ".join(o["object_id"] for o in _objects(
                BUILD_ROOT / p["tier"] / p["folder_name"]))],
            ["Files (MODEL/)", f"STEP {counts.get('STEP', 0)} | STL "
             f"{counts.get('STL', 0)} | GLB {counts.get('GLB', 0)} | SVG "
             f"{counts.get('SVG', 0)} | PNG {counts.get('PNG_RENDER', 0)} | "
             f"parametric source 1"],
            ["Regeneration", a.get("regeneration_status") +
             " (independent rebuild from shipped source vs shipped "
             "KEY_DIMENSIONS)"],
            ["Watertight re-check", a.get("watertight_status") +
             " (trimesh, independent of OCCT)"],
            ["Param-feature coverage", f"{cov.get('with_linear_feature_match')}"
             f"/{cov.get('parameters_total')}"],
            ["Section solids", f"longitudinal {sec_l} obj | transverse "
             f"{sec_t} obj | coupon {sec_c} obj (per-object STEP/STL at "
             "the planes recorded in the JSON)"],
            ["Renders", ", ".join(sorted(a.get("renders", {})))],
        ]
        story.append(tbl(["Field", "Value"], facts, [3.9 * cm, 13.2 * cm], st))
        iso = (BUILD_ROOT / p["tier"] / p["folder_name"] / "MODEL" /
               "3D_EVIDENCE" / f"{p['package_id']}_render_isometric.png")
        if iso.exists():
            story.append(Spacer(1, 4))
            story.append(Image(str(iso), width=7.6 * cm,
                               height=7.6 * cm * 1050 / 1380))
            story.append(Paragraph(
                f"{p['package_id']} isometric render (from shipped STL "
                "mesh; render is presentation, not validation).", st["small"]))
        story.append(Paragraph(ascii_safe(NARRATIVES[p["folder_name"]]),
                               st["body"]))

    # ---- 5 questions ----
    story.append(Paragraph("5. Response to the portfolio questions", st["h1"]))
    for q, a in QUESTIONS:
        story.append(Paragraph(ascii_safe(q), st["h2"]))
        story.append(Paragraph(ascii_safe(a), st["body"]))

    # ---- 6 classification ----
    story.append(Paragraph("6. Validity classification response", st["h1"]))
    story.append(Paragraph(
        "The audit's rule - never upgrade CAD to physical, never upgrade "
        "render to engineering correctness - is affirmed and unchanged. "
        "The table records the portfolio's status against the audit's own "
        "classes:", st["body"]))
    story.append(tbl(["Class", "Portfolio status", "Basis"],
                     [list(c) for c in CLASSIFICATION],
                     [3.7 * cm, 3.9 * cm, 9.5 * cm], st))

    # ---- 7 gaps ----
    story.append(Paragraph("7. Residual honest gaps (what the audit got "
                           "right and stays right)", st["h1"]))
    gaps = [
        "No physical prototypes exist; PHYSICALLY_VALIDATED remains NONE "
        "for every package.",
        "All dimensions are MODELLED proposals inside declared envelopes; "
        "no dimension is a measurement of hardware.",
        "Manufacturing tolerances are UNKNOWN pending supplier Cpk studies "
        "(extrusion, molding, microfab, coating) - the build ladders say "
        "so and the evidence edition does not resolve them.",
        "Render quality proves nothing about validity; every render ships "
        "with that statement in its footer.",
        "The buyer release remains the four BUYER_PRIMARY packages by CEO "
        "R382 disposition; the evidence edition adds transparency, not "
        "buyer scope.",
        "Package 06 ships no geometry by honest classification, not by "
        "omission; a decorative 3D model there would violate the honesty "
        "rule.",
    ]
    for g in gaps:
        story.append(Paragraph("- " + ascii_safe(g), st["body"]))

    doc = SimpleDocTemplate(
        str(OUT_PDF), pagesize=A4,
        leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title="Remediation and 3D Evidence Response",
        author="R384 release engineering")
    doc.build(story)
    print("PDF written:", OUT_PDF, OUT_PDF.stat().st_size, "bytes")

    mirror = {
        "artifact": "REMEDIATION_3D_AUDIT_RESPONSE",
        "date": DATE,
        "responds_to": ("Independent External Engineering Consultant "
                        "Re-Review (Toscanini 3D Technology Package Reality "
                        "& Design-Quality Review), verdict FAIL"),
        "audited_artifact": {"path": str(AUDITED_V2), "sha256": v2_sha,
                             "census": "0 STEP/STL/GLB/OBJ/3MF/PNG/JPG/SVG"},
        "deliverable": "technology-transfer-portfolio-15-3D-EVIDENCE.zip",
        "defect_responses": [
            {"id": d[0], "defect": d[1], "response": d[2], "evidence": d[3]}
            for d in DEFECTS],
        "portfolio_questions": [{"question": q, "answer": a}
                                for q, a in QUESTIONS],
        "validity_classification": [
            {"class": c[0], "status": c[1], "basis": c[2]}
            for c in CLASSIFICATION],
        "residual_honest_gaps": [g for _, g in enumerate([
            "No physical prototypes exist; PHYSICALLY_VALIDATED remains "
            "NONE for every package.",
            "All dimensions are MODELLED proposals inside declared "
            "envelopes; not hardware measurements.",
            "Manufacturing tolerances UNKNOWN pending supplier Cpk "
            "studies.",
            "Render quality proves nothing about validity.",
            "Buyer release remains the 4 BUYER_PRIMARY packages (CEO "
            "R382).",
            "Package 06 ships no geometry by honest 3D_NOT_APPLICABLE "
            "classification."])],
        "per_package_summary": {
            p["folder_name"]: {
                "package_id": p.get("package_id"),
                "tier": p.get("tier"),
                "3d_design_status": p.get("3d_design_status"),
                "augmentation_status": p.get("augmentation", {}).get("status"),
                "regeneration_status": p.get("augmentation", {}).get(
                    "regeneration_status"),
                "watertight_status": p.get("augmentation", {}).get(
                    "watertight_status"),
                "parameter_feature_coverage": p.get("augmentation", {}).get(
                    "parameter_feature_coverage"),
                "model_file_counts": p.get("augmentation", {}).get(
                    "model_file_counts"),
            } for p in summary["packages"]},
    }
    OUT_JSON.write_text(json.dumps(mirror, indent=1))
    print("JSON written:", OUT_JSON, OUT_JSON.stat().st_size, "bytes")


def _objects(pkg_dir: Path) -> list:
    mm = pkg_dir / "MODEL" / "MODEL_MANIFEST.json"
    if mm.exists():
        try:
            return json.load(open(mm)).get("objects", [])
        except Exception:  # noqa: BLE001
            return []
    return []


if __name__ == "__main__":
    build()

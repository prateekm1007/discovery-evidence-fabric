"""
builder.py — R371 portfolio V5 builder.

Implements CEO Phases 2, 4, 5, 6 (rendering):
  - Buyer-facing architecture in the CEO's exact 9-question order (Phase 4)
  - Two technical visuals per package embedded in the PDFs: mechanism/system
    architecture + decisive experiment setup (Phase 5)
  - Typeset governing equations rendered from the canonical equation strings
    (Phase 6)
  - Identity line on every page of every document, derived from the same
    mapping that becomes PORTFOLIO_IDENTITY_REGISTRY.json (Phase 1)
  - README.md GENERATED from RELEASE_CONTENT_MANIFEST.json which is built
    from the actual release filesystem — never hand-authored (Phase 2)
  - uW -> µW notation normalization (typography; documented, not a fact change)

All engineering content comes from canonical_source (R370Q export + V2
mutations). Nothing is hand-authored; no engineering fact is altered.
"""

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .canonical_source import (
    CanonicalPackage, apply_mutations, load_all_packages, normalize_units,
    PACKAGE_MAP,
)
from .commercial import build_commercial_evidence
from .economics import build_validation_economics
from .equations import build_equation_registry, render_equation_png
from .experiment_diagram import build_experiment_diagram
from .identity import build_registry, verify_registry, write_registry
from .loopstate import build_loop_state, portfolio_loop_summary
from .mechanism_diagram import build_all_mechanism_diagrams
from .ranking import build_ranking
from .unknowns import build_unknown_roadmap

NOT_ESTABLISHED = "NOT_ESTABLISHED"
CONFIDENTIALITY = "CONFIDENTIAL — TECHNOLOGY TRANSFER EVALUATION"

NAVY = colors.HexColor("#0c1e38")
ACCENT = colors.HexColor("#1e3a8a")
GOLD = colors.HexColor("#92400e")
DGREY = colors.HexColor("#4a4a4a")
LGREY = colors.HexColor("#e5e7eb")
GREEN = colors.HexColor("#166534")
RED = colors.HexColor("#b91c1c")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(fp):
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
def get_styles():
    return {
        "CT": ParagraphStyle("CT", fontName="Helvetica-Bold", fontSize=19,
                             leading=24, textColor=NAVY, spaceAfter=8),
        "CS": ParagraphStyle("CS", fontName="Helvetica", fontSize=10.5,
                             leading=14, textColor=DGREY, spaceAfter=4),
        "SH": ParagraphStyle("SH", fontName="Helvetica-Bold", fontSize=12.5,
                             leading=16, textColor=NAVY, spaceBefore=12,
                             spaceAfter=5),
        "QH": ParagraphStyle("QH", fontName="Helvetica-Bold", fontSize=9.6,
                             leading=13, textColor=ACCENT, spaceBefore=7,
                             spaceAfter=2),
        "BT": ParagraphStyle("BT", fontName="Helvetica", fontSize=8.6,
                             leading=11.6, alignment=TA_JUSTIFY, spaceAfter=4,
                             textColor=colors.HexColor("#1f2937")),
        "BC": ParagraphStyle("BC", fontName="Helvetica", fontSize=8.6,
                             leading=11.6, alignment=TA_LEFT, spaceAfter=3,
                             textColor=colors.HexColor("#1f2937")),
        "SM": ParagraphStyle("SM", fontName="Helvetica", fontSize=7.6,
                             leading=10, textColor=DGREY, spaceAfter=2),
        "MT": ParagraphStyle("MT", fontName="Courier", fontSize=7.8,
                             leading=10.4, textColor=DGREY, spaceAfter=3),
        "DIS": ParagraphStyle("DIS", fontName="Helvetica-Oblique", fontSize=7.2,
                              leading=9.6, textColor=DGREY, alignment=TA_CENTER,
                              spaceBefore=6),
        "WARN": ParagraphStyle("WARN", fontName="Helvetica-Bold", fontSize=8.4,
                               leading=11, textColor=RED, spaceAfter=3),
        "OK": ParagraphStyle("OK", fontName="Helvetica", fontSize=8.4,
                             leading=11, textColor=GREEN, spaceAfter=3),
    }


def _footer_canvas(identity_line, confidentiality=CONFIDENTIALITY):
    """Page decorator: identity line + confidentiality + page number."""
    def _draw(canvas, doc):
        canvas.saveState()
        w, _ = letter
        canvas.setFont("Helvetica", 6.8)
        canvas.setFillColor(DGREY)
        canvas.drawString(0.7 * inch, 0.42 * inch, identity_line)
        canvas.drawCentredString(w / 2, 0.42 * inch, confidentiality)
        canvas.drawRightString(w - 0.7 * inch, 0.42 * inch,
                               f"Page {doc.page}")
        canvas.setStrokeColor(LGREY)
        canvas.setLineWidth(0.5)
        canvas.line(0.7 * inch, 0.55 * inch, w - 0.7 * inch, 0.55 * inch)
        canvas.restoreState()
    return _draw


def _doc(path, identity_line, title, author="Discovery Engine (R372 V6)"):
    # R372 reproducibility: invariant=1 removes the embedded creation
    # timestamp so PDF bytes are deterministic across builds (fresh-clone
    # reproduction compares byte hashes; a timestamped PDF can never
    # reproduce byte-identically).
    from reportlab import rl_config
    rl_config.invariant = 1
    return SimpleDocTemplate(
        path, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.75 * inch,
        title=title, author=author,
        subject=identity_line,
    )


def _tbl(rows, widths, header=True, fontsize=7.6):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, LGREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), fontsize),
        ("LEADING", (0, 0), (-1, -1), fontsize + 2.6),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1f2937")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f6f8fb")]),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def _img(path, width):
    from reportlab.lib.utils import ImageReader
    ir = ImageReader(path)
    iw, ih = ir.getSize()
    return Image(path, width=width, height=width * ih / iw)


def _esc(t):
    return (str(t) if t is not None else "").replace("&", "&amp;").replace(
        "<", "&lt;").replace(">", "&gt;")


def _mut(pkg, text):
    """Normalize notation + apply V2 mutations for buyer rendering."""
    return normalize_units(apply_mutations(str(text), pkg.addendum))

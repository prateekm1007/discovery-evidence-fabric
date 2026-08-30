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
        # R375: wordWrap='LTR' — canonical equation strings, source URLs and
        # hashes are long UNBROKEN tokens; without long-word breaking a
        # single 200-char token overflows the frame horizontally (the exact
        # V2 defect class). The worst-case-equation fixture pins this.
        "MT": ParagraphStyle("MT", fontName="Courier", fontSize=7.8,
                             leading=10.4, textColor=DGREY, spaceAfter=3,
                             wordWrap="LTR"),
        "DIS": ParagraphStyle("DIS", fontName="Helvetica-Oblique", fontSize=7.2,
                              leading=9.6, textColor=DGREY, alignment=TA_CENTER,
                              spaceBefore=6),
        "WARN": ParagraphStyle("WARN", fontName="Helvetica-Bold", fontSize=8.4,
                               leading=11, textColor=RED, spaceAfter=3),
        "OK": ParagraphStyle("OK", fontName="Helvetica", fontSize=8.4,
                             leading=11, textColor=GREEN, spaceAfter=3),
    }


def _footer_canvas(identity_line, confidentiality=CONFIDENTIALITY):
    """Page decorator: identity line + confidentiality + page number.

    V3 render fix (2026-08-30): the identity line is now MEASURED against
    the centered confidentiality text and truncated with an ellipsis if
    the two would collide — the portfolio-level documents carry identity
    strings long enough to overprint the centered footer (the V3 render
    gate caught exactly 8 overlapping pairs per page from this)."""
    def _draw(canvas, doc):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        canvas.saveState()
        w, _ = letter
        canvas.setFont("Helvetica", 6.8)
        canvas.setFillColor(DGREY)
        left_x = 0.7 * inch
        right_x = w - 0.7 * inch
        conf_w = stringWidth(confidentiality, "Helvetica", 6.8)
        conf_left = w / 2 - conf_w / 2
        # the identity line must end before the centered text minus a gap
        max_ident_w = (conf_left - 8.0) - left_x
        ident = identity_line
        if stringWidth(ident, "Helvetica", 6.8) > max_ident_w:
            while ident and stringWidth(ident + "…", "Helvetica", 6.8) > \
                    max_ident_w:
                ident = ident[:-1]
            ident += "…"
        canvas.drawString(left_x, 0.42 * inch, ident)
        canvas.drawCentredString(w / 2, 0.42 * inch, confidentiality)
        canvas.drawRightString(right_x, 0.42 * inch,
                               f"Page {doc.page}")
        canvas.setStrokeColor(LGREY)
        canvas.setLineWidth(0.5)
        canvas.line(0.7 * inch, 0.55 * inch, right_x, 0.55 * inch)
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
    """Unified table factory (CEO V3 render directive 2026-08-30, Directives
    1a/1b/4 — forensic fix for the V2 overprinting defect).

    ROOT CAUSE this repairs: V2 passed RAW STRINGS to Table, which
    ReportLab draws as a single unwrapped line at natural width — a
    150-char cell drew to x=2,797pt on a 612pt page, overprinting every
    neighbouring column (598-1,029 overlapping char pairs per package).

    THE FIX: every cell becomes a Paragraph with wordWrap='LTR' so text
    wraps inside its column and the ROW grows vertically instead. Column
    widths are asserted against the REAL frame width (letter page, 54pt
    margins -> 504pt usable; the directive's 492pt assumed 60pt margins)
    so a mis-sized table can never silently ship.

    Cell values may be raw strings (escaped here) or pre-built Paragraphs
    (e.g. cell_safe() output — Directive 4 summarization for long-form
    narrative fields). TableStyle FONT* settings do not affect Paragraph
    cells, so type styling lives in the paragraph styles below.
    """
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle

    PAGE_W = 612.0
    MARGINS = 2 * 54.0                     # 0.75in each side (see _doc)
    USABLE = PAGE_W - MARGINS              # 504pt — NEVER EXCEED
    total = sum(widths)
    assert total <= USABLE + 0.5, (
        f"table col widths sum {total:.1f}pt exceeds the {USABLE:.0f}pt "
        f"frame — V3 render contract (Directive 1b)")

    cell_style = ParagraphStyle(
        "Cell", fontName="Helvetica", fontSize=fontsize,
        leading=fontsize + 2.6, wordWrap="LTR",
        textColor=colors.HexColor("#1f2937"), allowWidows=0, allowOrphans=0)
    head_style = ParagraphStyle(
        "CellHead", fontName="Helvetica-Bold", fontSize=fontsize,
        leading=fontsize + 2.6, wordWrap="LTR",
        textColor=colors.white, allowWidows=0, allowOrphans=0)

    def _cell(v, style):
        if isinstance(v, Paragraph):
            return v
        safe = _winansi_safe(v).replace(
            "&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(safe, style)

    data = []
    for i, row in enumerate(rows):
        style = head_style if (header and i == 0) else cell_style
        data.append([_cell(v, style) for v in row])

    t = Table(data, colWidths=widths,
              repeatRows=1 if header else 0,
              hAlign="LEFT", splitByRow=True)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, LGREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),   # prevents row bleed
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f6f8fb")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8,
             colors.HexColor("#2d4a7a")),
        ]
    t.setStyle(TableStyle(style))
    return t


#: R375-1 — AUTHORITATIVE vs SUMMARY-ONLY tables.
#:
#: The V3 fix summarized long narrative fields everywhere. CEO R375-1
#: (2026-08-30) removes authoritative truncation ENTIRELY: a table that
#: carries engineering record content must render the FULL value
#: (cell_full); ONLY tables that are explicitly summary views may shorten,
#: and then ONLY with an explicit pointer to where the full authoritative
#: record lives inside the same package.
#:
#: Summary-only tables (the COMPLETE list — enforced by
#: tests/test_r375_render_hardening.py::test_cell_safe_only_in_summary_tables):
#:   - builder_portfolio.py portfolio INDEX comparison table (per-package
#:     cells point at DOWNLOAD/<folder>/02_..._DOSSIER.pdf)
SUMMARY_TABLE_WHITELIST = {
    "premium_package_factory/r371/builder_portfolio.py",
}


def cell_full(text, fontsize=7.6, bold=False):
    """R375-1 FULL_VALUE cell preparation.

    Returns a Paragraph containing the COMPLETE text — never truncated,
    never summarized, never elided. Long content wraps inside the column
    (wordWrap='LTR' breaks unbroken tokens too); the row grows to the
    measured paragraph height and the table splits across pages
    (repeatRows=1 repeats the header). This is the ONLY legal cell
    preparation for authoritative engineering content.
    """
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle

    raw = _winansi_safe(text)
    style = ParagraphStyle(
        "CellFull", fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=fontsize, leading=fontsize + 2.6, wordWrap="LTR",
        allowWidows=0, allowOrphans=0)
    safe = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe or "—", style)


def cell_safe(field_name, text, max_chars=180, register=None, fontsize=7.6):
    """R375-1 SUMMARY cell preparation — LEGAL ONLY IN SUMMARY-ONLY TABLES.

    A summary table shows a short digest + an EXPLICIT pointer to the full
    authoritative record inside the same package. It may NEVER be used for
    authoritative engineering content (design inputs, failure evidence,
    V&V methods/acceptance, build plan, unknown statements, mutations).

    Call sites are mechanically restricted to SUMMARY_TABLE_WHITELIST.
    Returns a Paragraph for _tbl() (never a raw string).
    """
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle

    raw = _winansi_safe(text)
    if not register:
        raise ValueError(
            "cell_safe() R375-1 contract: summary cells MUST carry an "
            "explicit pointer (register=...) to the full authoritative "
            "record inside the package")
    style = ParagraphStyle(
        "CellSafe", fontName="Helvetica", fontSize=fontsize,
        leading=fontsize + 2.6, wordWrap="LTR",
        allowWidows=0, allowOrphans=0)

    if len(raw) > max_chars:
        sentences = raw.replace("\n", " ").split(". ")
        summary = sentences[0]
        if len(summary) > max_chars:
            summary = summary[:max_chars].rstrip() + "…"
        elif len(sentences) > 1:
            summary += "."
        text = f"{summary} [SUMMARY — full text: {register}]"
    else:
        text = raw if raw else "—"

    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe, style)


def _img(path, width):
    """Embed an image at `width` pt, DEFENSIVELY contained to one page.

    R375-3/4: containment is defensive only — the diagram/equation layers
    upstream must already produce page-fitting aspect ratios (they now
    reflow and split); this clamp guarantees an oversized PNG can never
    push a flowable past the frame (ReportLab would raise LayoutError,
    which IS the correct hard failure — the clamp simply keeps the
    geometry honest while it does).
    """
    from reportlab.lib.utils import ImageReader
    ir = ImageReader(path)
    iw, ih = ir.getSize()
    PAGE_H = 792.0
    TOP, BOTTOM = 0.7 * 72, 0.75 * 72
    usable_h = PAGE_H - TOP - BOTTOM
    h = width * ih / iw
    if h > usable_h:
        width = width * usable_h / h
    return Image(path, width=width, height=width * ih / iw)


#: R375-1/10 glyph-truth map: characters in the canonical record that
#: Helvetica (cp1252) cannot encode. RenderLab would silently draw a
#: placeholder box for these (found live by the content-completeness
#: gate on P-01: '→', '・'). Substitutions are meaning-preserving and
#: applied IDENTICALLY at render and in the completeness expectations,
#: so containment stays byte-exact.
_GLYPH_MAP = {
    "\u03b2": "beta",      # β
    "\u03bc": "\u00b5",   # μ -> micro sign µ (cp1252 0xB5, same look)
    "\u30fb": "\u00b7",   # ・ -> middle dot ·
    "\u2192": "->",        # →
    "\u2190": "<-",        # ←
    "\u21d2": "=>",        # ⇒
    "\u2264": "<=",        # ≤
    "\u2265": ">=",        # ≥
    "\u2248": "~",         # ≈
    "\u2260": "!=",        # ≠
    "\u2010": "-",         # ‐ hyphen
    "\u03c0": "pi",        # π
    "\u0394": "Delta",     # Δ
    "\u03a9": "ohm",       # Ω
    "\u00b2": "\u00b2", "\u00b3": "\u00b3",
}


def _winansi_safe(t):
    """Replace non-cp1252 glyphs with meaning-preserving equivalents so
    the buyer never sees a placeholder box; unknown exotics fall back to
    cp1252 'replace' encoding (and are disclosed by the build gate
    because completeness applies the SAME transform)."""
    s = str(t if t is not None else "")
    for k, v in _GLYPH_MAP.items():
        s = s.replace(k, v)
    try:
        s.encode("cp1252")
        return s
    except UnicodeEncodeError:
        return s.encode("cp1252", errors="replace").decode("cp1252")


def _esc(t):
    return _winansi_safe(t).replace("&", "&amp;").replace(
        "<", "&lt;").replace(">", "&gt;")


def _mut(pkg, text):
    """Normalize notation + apply V2 mutations for buyer rendering."""
    return normalize_units(apply_mutations(str(text), pkg.addendum))

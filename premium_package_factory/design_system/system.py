"""
design_system.py — Premium Package Factory visual system

Defines the palette, typography, spacing, and reusable ReportLab styles
used across all 15 packages. The system is intentionally restrained:
corporate-technology-diligence + premium-engineering-dossier.

Design principles:
- Restraint over decoration
- Diagram-first communication
- Evidence-status badges are FIRST-CLASS visual elements
- Generous whitespace
- Strong grid
- No clipart, no stock photos, no giant paragraphs
- MODELLED must never visually look like PROVEN
"""

from reportlab.lib import colors
from reportlab.lib.units import mm, inch
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os


# ----------------------------------------------------------------------------
# Page geometry
# ----------------------------------------------------------------------------

PAGE_SIZE = A4              # 210 x 297 mm
PAGE_W, PAGE_H = PAGE_SIZE

MARGIN_L = 18 * mm
MARGIN_R = 18 * mm
MARGIN_T = 20 * mm
MARGIN_B = 22 * mm          # extra bottom for page-number + confidentiality footer

CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R    # ~174 mm
CONTENT_H = PAGE_H - MARGIN_T - MARGIN_B    # ~255 mm

# Column gutter for two-column layouts
GUTTER = 6 * mm
COL_W = (CONTENT_W - GUTTER) / 2


# ----------------------------------------------------------------------------
# Font registration
# We use Noto Serif SC + Noto Sans SC (already installed) so that the
# package can render CJK fallback cleanly even though primary copy is English.
# Primary Latin sans = Inter-like via DejaVu Sans (always available).
# Primary Latin serif = Tinos (Times-style, always available).
# ----------------------------------------------------------------------------

FONT_DIRS = [
    "/usr/share/fonts/truetype/english/",
    "/usr/share/fonts/truetype/dejavu/",
    "/usr/share/fonts/truetype/liberation/",
    "/usr/share/fonts/truetype/freefont/",
    "/usr/share/fonts/truetype/noto-serif-sc/",
    "/usr/share/fonts/truetype/chinese/",
]

def _try_register(name, path):
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            return True
        except Exception:
            return False
    return False


def register_fonts():
    """Register all fonts used by the design system. Idempotent."""

    # Latin sans family (body / UI / badges) — use Liberation Sans (has italic)
    sans_reg = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    sans_bd  = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    sans_it  = "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"
    sans_bdit = "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf"

    # Latin serif family (covers + headings for editorial feel) — Liberation Serif
    # (Tinos files in /usr/share/fonts are HTML placeholders, not real TTFs)
    serif_reg = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
    serif_bd  = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
    serif_it  = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
    serif_bdit = "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"

    _try_register("BodySans",       sans_reg)
    _try_register("BodySans-Bold",  sans_bd)
    _try_register("BodySans-Italic", sans_it)
    _try_register("BodySans-BoldItalic", sans_bdit)

    _try_register("HeadSerif",          serif_reg)
    _try_register("HeadSerif-Bold",     serif_bd)
    _try_register("HeadSerif-Italic",   serif_it)
    _try_register("HeadSerif-BoldItalic", serif_bdit)

    # Mono for provenance hashes / IDs — Liberation Mono has italic
    mono_reg = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"
    mono_bd  = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"
    _try_register("Mono",       mono_reg)
    _try_register("Mono-Bold",  mono_bd)

    # Register font family mappings so <b> and <i> work in Paragraph
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily(
        "BodySans",
        normal="BodySans", bold="BodySans-Bold",
        italic="BodySans-Italic", boldItalic="BodySans-BoldItalic"
    )
    registerFontFamily(
        "HeadSerif",
        normal="HeadSerif", bold="HeadSerif-Bold",
        italic="HeadSerif-Italic", boldItalic="HeadSerif-BoldItalic"
    )
    registerFontFamily(
        "Mono",
        normal="Mono", bold="Mono-Bold",
        italic="Mono", boldItalic="Mono-Bold"
    )


# ----------------------------------------------------------------------------
# Color palette — restrained, premium technology-transfer
# ----------------------------------------------------------------------------

# Ink (primary text)
INK_900 = colors.HexColor("#0F172A")    # near-black, primary text
INK_700 = colors.HexColor("#334155")    # secondary text
INK_500 = colors.HexColor("#64748B")    # tertiary / captions
INK_300 = colors.HexColor("#CBD5E1")    # hairline borders
INK_100 = colors.HexColor("#F1F5F9")    # surface tint
INK_050 = colors.HexColor("#F8FAFC")    # page background (unused; we keep white)

# Brand — slate blue, restrained
BRAND_900 = colors.HexColor("#0F2A4D")
BRAND_700 = colors.HexColor("#1E3A5F")
BRAND_500 = colors.HexColor("#2E5C8A")
BRAND_300 = colors.HexColor("#7BA7CC")
BRAND_100 = colors.HexColor("#E3EDF5")

# Accent — single accent for highlights (used sparingly)
ACCENT = colors.HexColor("#B8860B")    # dark goldenrod, premium feel
ACCENT_LIGHT = colors.HexColor("#F4E4BC")

# Evidence taxonomy — semantically meaningful, never decorative
EV_PHYSICAL        = colors.HexColor("#1B5E20")   # deep green
EV_EXTERNAL        = colors.HexColor("#2E7D32")   # green
EV_COMPUTATIONAL   = colors.HexColor("#1565C0")   # blue
EV_MODEL           = colors.HexColor("#F57F17")   # amber
EV_ASSUMED         = colors.HexColor("#6A1B9A")   # purple
EV_UNKNOWN         = colors.HexColor("#424242")   # gray
EV_KILLED          = colors.HexColor("#B71C1C")   # red

EV_PHYSICAL_BG        = colors.HexColor("#E8F5E9")
EV_EXTERNAL_BG        = colors.HexColor("#E8F5E9")
EV_COMPUTATIONAL_BG   = colors.HexColor("#E3F2FD")
EV_MODEL_BG           = colors.HexColor("#FFF8E1")
EV_ASSUMED_BG         = colors.HexColor("#F3E5F5")
EV_UNKNOWN_BG         = colors.HexColor("#ECEFF1")
EV_KILLED_BG          = colors.HexColor("#FFEBEE")

# Risk colors
RISK_LOW    = colors.HexColor("#1B5E20")
RISK_MEDIUM = colors.HexColor("#F57F17")
RISK_HIGH   = colors.HexColor("#C62828")
RISK_VERY_HIGH = colors.HexColor("#B71C1C")

RISK_LOW_BG    = colors.HexColor("#E8F5E9")
RISK_MEDIUM_BG = colors.HexColor("#FFF8E1")
RISK_HIGH_BG   = colors.HexColor("#FFEBEE")
RISK_VERY_HIGH_BG = colors.HexColor("#FFEBEE")

# Maturity colors
MAT_TRANSFER_READY    = colors.HexColor("#1B5E20")
MAT_VALIDATION_STAGE  = colors.HexColor("#2E7D32")
MAT_ENGINEERING       = colors.HexColor("#1565C0")
MAT_RESEARCH          = colors.HexColor("#F57F17")

MAT_TRANSFER_READY_BG    = colors.HexColor("#E8F5E9")
MAT_VALIDATION_STAGE_BG  = colors.HexColor("#E8F5E9")
MAT_ENGINEERING_BG       = colors.HexColor("#E3F2FD")
MAT_RESEARCH_BG          = colors.HexColor("#FFF8E1")


# ----------------------------------------------------------------------------
# Evidence-state helpers — used everywhere, must be visually distinct
# ----------------------------------------------------------------------------

EVIDENCE_STATES = {
    # Tier label              fg color            bg color            short
    "OBSERVED":              (EV_PHYSICAL,       EV_PHYSICAL_BG,     "OBS"),
    "EXTERNALLY_VERIFIED":   (EV_EXTERNAL,       EV_EXTERNAL_BG,     "EXT"),
    "COMPUTATIONAL":         (EV_COMPUTATIONAL,  EV_COMPUTATIONAL_BG,"COMP"),
    "MODELLED":              (EV_MODEL,          EV_MODEL_BG,        "MOD"),
    "ASSUMED":               (EV_ASSUMED,        EV_ASSUMED_BG,      "ASM"),
    "UNKNOWN":               (EV_UNKNOWN,        EV_UNKNOWN_BG,      "UNK"),
}


def evidence_state_for_tier(tier_label):
    """Map a T0/T1/T2/T3 evidence tier to a visual evidence state."""

    if not tier_label:
        return "UNKNOWN"
    t = tier_label.upper()
    if t.startswith("T3") or "PHYSICAL" in t:
        return "OBSERVED"
    if t.startswith("T2") or "INDEPENDENT" in t or "EXTERNAL" in t:
        return "EXTERNALLY_VERIFIED"
    if t.startswith("T1") or "MODEL" in t:
        return "MODELLED"
    if t.startswith("T0"):
        return "OBSERVED"
    return "UNKNOWN"


# ----------------------------------------------------------------------------
# Paragraph styles
# ----------------------------------------------------------------------------

def build_styles():
    """Build the full paragraph style sheet. Idempotent."""

    register_fonts()
    sample = getSampleStyleSheet()

    S = {}

    # Cover
    S["CoverEyebrow"] = ParagraphStyle(
        "CoverEyebrow", parent=sample["Normal"],
        fontName="BodySans-Bold", fontSize=8.5, leading=11,
        textColor=BRAND_500, spaceAfter=6, alignment=TA_LEFT,
    )
    S["CoverTitle"] = ParagraphStyle(
        "CoverTitle", parent=sample["Normal"],
        fontName="HeadSerif-Bold", fontSize=30, leading=34,
        textColor=INK_900, spaceAfter=8, alignment=TA_LEFT,
    )
    S["CoverSubtitle"] = ParagraphStyle(
        "CoverSubtitle", parent=sample["Normal"],
        fontName="HeadSerif-Italic", fontSize=14, leading=18,
        textColor=INK_700, spaceAfter=18, alignment=TA_LEFT,
    )
    S["CoverValueProp"] = ParagraphStyle(
        "CoverValueProp", parent=sample["Normal"],
        fontName="BodySans", fontSize=10.5, leading=15,
        textColor=INK_700, spaceAfter=14, alignment=TA_LEFT,
    )

    # Section header
    S["SectionHeader"] = ParagraphStyle(
        "SectionHeader", parent=sample["Normal"],
        fontName="HeadSerif-Bold", fontSize=14, leading=18,
        textColor=INK_900, spaceBefore=4, spaceAfter=6, alignment=TA_LEFT,
    )
    S["SectionHeaderEyebrow"] = ParagraphStyle(
        "SectionHeaderEyebrow", parent=sample["Normal"],
        fontName="BodySans-Bold", fontSize=7.5, leading=10,
        textColor=BRAND_500, spaceAfter=2, alignment=TA_LEFT,
    )
    S["SubsectionHeader"] = ParagraphStyle(
        "SubsectionHeader", parent=sample["Normal"],
        fontName="BodySans-Bold", fontSize=10, leading=13,
        textColor=INK_900, spaceBefore=6, spaceAfter=3, alignment=TA_LEFT,
    )

    # Body
    S["Body"] = ParagraphStyle(
        "Body", parent=sample["Normal"],
        fontName="BodySans", fontSize=9.5, leading=13.5,
        textColor=INK_900, spaceAfter=6, alignment=TA_LEFT,
    )
    S["BodySmall"] = ParagraphStyle(
        "BodySmall", parent=sample["Normal"],
        fontName="BodySans", fontSize=8.5, leading=12,
        textColor=INK_700, spaceAfter=4, alignment=TA_LEFT,
    )
    S["BodyCaption"] = ParagraphStyle(
        "BodyCaption", parent=sample["Normal"],
        fontName="BodySans-Italic", fontSize=8, leading=11,
        textColor=INK_500, spaceAfter=4, alignment=TA_LEFT,
    )
    S["Mono"] = ParagraphStyle(
        "Mono", parent=sample["Normal"],
        fontName="Mono", fontSize=8, leading=11,
        textColor=INK_700, spaceAfter=4, alignment=TA_LEFT,
    )

    # Card body
    S["CardTitle"] = ParagraphStyle(
        "CardTitle", parent=sample["Normal"],
        fontName="BodySans-Bold", fontSize=8.5, leading=11,
        textColor=BRAND_700, spaceAfter=3, alignment=TA_LEFT,
    )
    S["CardBody"] = ParagraphStyle(
        "CardBody", parent=sample["Normal"],
        fontName="BodySans", fontSize=8.5, leading=12,
        textColor=INK_900, spaceAfter=3, alignment=TA_LEFT,
    )
    S["CardLabel"] = ParagraphStyle(
        "CardLabel", parent=sample["Normal"],
        fontName="BodySans-Bold", fontSize=7.5, leading=10,
        textColor=INK_500, spaceAfter=2, alignment=TA_LEFT,
    )
    S["CardValue"] = ParagraphStyle(
        "CardValue", parent=sample["Normal"],
        fontName="BodySans-Bold", fontSize=10, leading=13,
        textColor=INK_900, spaceAfter=2, alignment=TA_LEFT,
    )
    S["CardValueLarge"] = ParagraphStyle(
        "CardValueLarge", parent=sample["Normal"],
        fontName="HeadSerif-Bold", fontSize=18, leading=22,
        textColor=INK_900, spaceAfter=2, alignment=TA_LEFT,
    )

    # Table cell
    S["TableCell"] = ParagraphStyle(
        "TableCell", parent=sample["Normal"],
        fontName="BodySans", fontSize=8.5, leading=11.5,
        textColor=INK_900, alignment=TA_LEFT,
    )
    S["TableCellSmall"] = ParagraphStyle(
        "TableCellSmall", parent=sample["Normal"],
        fontName="BodySans", fontSize=7.5, leading=10.5,
        textColor=INK_900, alignment=TA_LEFT,
    )
    S["TableHeader"] = ParagraphStyle(
        "TableHeader", parent=sample["Normal"],
        fontName="BodySans-Bold", fontSize=8.5, leading=11.5,
        textColor=colors.white, alignment=TA_LEFT,
    )

    # Footer
    S["PageNumber"] = ParagraphStyle(
        "PageNumber", parent=sample["Normal"],
        fontName="BodySans", fontSize=7.5, leading=10,
        textColor=INK_500, alignment=TA_RIGHT,
    )
    S["FooterLeft"] = ParagraphStyle(
        "FooterLeft", parent=sample["Normal"],
        fontName="BodySans", fontSize=7.5, leading=10,
        textColor=INK_500, alignment=TA_LEFT,
    )
    S["Confidentiality"] = ParagraphStyle(
        "Confidentiality", parent=sample["Normal"],
        fontName="BodySans-Bold", fontSize=7, leading=9,
        textColor=INK_500, alignment=TA_CENTER,
    )

    # Status badge
    S["Badge"] = ParagraphStyle(
        "Badge", parent=sample["Normal"],
        fontName="BodySans-Bold", fontSize=7.5, leading=10,
        textColor=colors.white, alignment=TA_CENTER,
    )

    # Big callout
    S["CalloutBig"] = ParagraphStyle(
        "CalloutBig", parent=sample["Normal"],
        fontName="HeadSerif-Bold", fontSize=22, leading=26,
        textColor=INK_900, alignment=TA_LEFT, spaceAfter=4,
    )
    S["CalloutBody"] = ParagraphStyle(
        "CalloutBody", parent=sample["Normal"],
        fontName="BodySans", fontSize=10, leading=14,
        textColor=INK_700, alignment=TA_LEFT, spaceAfter=2,
    )

    # Portfolio
    S["PortfolioTitle"] = ParagraphStyle(
        "PortfolioTitle", parent=sample["Normal"],
        fontName="HeadSerif-Bold", fontSize=42, leading=48,
        textColor=INK_900, spaceAfter=10, alignment=TA_LEFT,
    )
    S["PortfolioSubtitle"] = ParagraphStyle(
        "PortfolioSubtitle", parent=sample["Normal"],
        fontName="HeadSerif-Italic", fontSize=18, leading=22,
        textColor=INK_700, spaceAfter=24, alignment=TA_LEFT,
    )

    return S


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def mm_to_pt(x):
    """Convert millimeters to points."""
    return x * mm


def evidence_badge_color(state):
    """Return (fg, bg) for an evidence state label."""
    return EVIDENCE_STATES.get(state, EVIDENCE_STATES["UNKNOWN"])[:2]


def maturity_color(maturity):
    """Map a maturity string to (fg, bg)."""
    m = maturity.upper()
    if "TRANSFER" in m:
        return (MAT_TRANSFER_READY, MAT_TRANSFER_READY_BG)
    if "VALIDATION" in m:
        return (MAT_VALIDATION_STAGE, MAT_VALIDATION_STAGE_BG)
    if "ENGINEERING" in m:
        return (MAT_ENGINEERING, MAT_ENGINEERING_BG)
    return (MAT_RESEARCH, MAT_RESEARCH_BG)


def risk_color(risk):
    """Map a risk level string to (fg, bg)."""
    r = risk.upper()
    if "VERY" in r or "EXTREME" in r:
        return (RISK_VERY_HIGH, RISK_VERY_HIGH_BG)
    if "HIGH" in r:
        return (RISK_HIGH, RISK_HIGH_BG)
    if "MEDIUM" in r:
        return (RISK_MEDIUM, RISK_MEDIUM_BG)
    return (RISK_LOW, RISK_LOW_BG)


def tier_color(tier_label):
    """Map an evidence tier (T0/T1/T2/T3) to a color."""
    state = evidence_state_for_tier(tier_label)
    return EVIDENCE_STATES[state][:2]

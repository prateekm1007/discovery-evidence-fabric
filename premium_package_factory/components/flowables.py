"""
components.py — Reusable ReportLab flowables for the Premium Package Factory.

Every flowable is designed to be VISUALLY CONSISTENT across all 15 packages.
The design system is restrained; evidence-status badges are first-class.
"""

from reportlab.lib import colors
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    Flowable, Paragraph, Spacer, Table, TableStyle, Image,
    KeepTogether, KeepInFrame, PageBreak, NextPageTemplate, FrameBreak,
    BaseDocTemplate, PageTemplate, Frame, ActionFlowable
)
from reportlab.platypus.flowables import HRFlowable, ListFlowable, ListItem
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from design_system.system import (
    build_styles, register_fonts,
    INK_900, INK_700, INK_500, INK_300, INK_100, INK_050,
    BRAND_900, BRAND_700, BRAND_500, BRAND_300, BRAND_100,
    ACCENT, ACCENT_LIGHT,
    EV_PHYSICAL, EV_EXTERNAL, EV_COMPUTATIONAL, EV_MODEL, EV_ASSUMED, EV_UNKNOWN, EV_KILLED,
    EV_PHYSICAL_BG, EV_EXTERNAL_BG, EV_COMPUTATIONAL_BG, EV_MODEL_BG, EV_ASSUMED_BG, EV_UNKNOWN_BG, EV_KILLED_BG,
    RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_VERY_HIGH,
    RISK_LOW_BG, RISK_MEDIUM_BG, RISK_HIGH_BG, RISK_VERY_HIGH_BG,
    MAT_TRANSFER_READY, MAT_VALIDATION_STAGE, MAT_ENGINEERING, MAT_RESEARCH,
    MAT_TRANSFER_READY_BG, MAT_VALIDATION_STAGE_BG, MAT_ENGINEERING_BG, MAT_RESEARCH_BG,
    EVIDENCE_STATES, evidence_state_for_tier, maturity_color, risk_color, tier_color,
    PAGE_W, PAGE_H, MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B, CONTENT_W, CONTENT_H,
    COL_W, GUTTER,
)


# ----------------------------------------------------------------------------
# Status badge
# ----------------------------------------------------------------------------

class StatusBadge(Flowable):
    """A pill-shaped badge with semantic color."""

    def __init__(self, label, fg=colors.white, bg=BRAND_500, width=None, height=14, fontsize=7.5):
        Flowable.__init__(self)
        self.label = label
        self.fg = fg
        self.bg = bg
        self.width = width
        self.height = height
        self.fontsize = fontsize
        if width is None:
            # auto-size based on label length
            from reportlab.pdfbase.pdfmetrics import stringWidth
            self.width = stringWidth(label, "BodySans-Bold", fontsize) + 12

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.setStrokeColor(self.bg)
        c.roundRect(0, 0, self.width, self.height, self.height / 2, fill=1, stroke=0)
        c.setFillColor(self.fg)
        c.setFont("BodySans-Bold", self.fontsize)
        c.drawCentredString(self.width / 2, (self.height - self.fontsize) / 2 + 1, self.label)


def evidence_badge(state_label, width=None, height=13):
    """Build a StatusBadge for an evidence state label."""
    if state_label not in EVIDENCE_STATES:
        state_label = "UNKNOWN"
    fg, bg, short = EVIDENCE_STATES[state_label]
    return StatusBadge(state_label.replace("_", " "), fg=colors.white, bg=fg,
                       width=width, height=height, fontsize=7)


def maturity_badge(maturity, width=None, height=14):
    """Build a StatusBadge for a maturity level."""
    fg, bg = maturity_color(maturity)
    return StatusBadge(maturity, fg=colors.white, bg=fg, width=width, height=height, fontsize=7.5)


def risk_badge(risk_level, width=None, height=14):
    """Build a StatusBadge for a risk level."""
    fg, bg = risk_color(risk_level)
    return StatusBadge(risk_level, fg=colors.white, bg=fg, width=width, height=height, fontsize=7.5)


# ----------------------------------------------------------------------------
# Section header
# ----------------------------------------------------------------------------

class SectionHeader(Flowable):
    """A page-section header with eyebrow + title + accent rule."""

    def __init__(self, eyebrow, title, width=None):
        Flowable.__init__(self)
        self.eyebrow = eyebrow
        self.title = title
        self.width = width or CONTENT_W
        self.height = 28

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        # Eyebrow
        c.setFillColor(BRAND_500)
        c.setFont("BodySans-Bold", 7.5)
        c.drawString(0, self.height - 10, self.eyebrow.upper())
        # Title
        c.setFillColor(INK_900)
        c.setFont("HeadSerif-Bold", 14)
        c.drawString(0, self.height - 24, self.title)
        # Accent rule
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1.5)
        c.line(0, 0, 40, 0)


# ----------------------------------------------------------------------------
# Key metric card
# ----------------------------------------------------------------------------

class KeyMetricCard(Flowable):
    """A small card showing a single key metric with its evidence tier."""

    def __init__(self, label, value, tier="MODELLED", note=None, width=None, height=46):
        Flowable.__init__(self)
        self.label = label
        self.value = value
        self.tier = tier
        self.note = note
        self.width = width or 80 * mm
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        # Background card
        c.setFillColor(INK_050)
        c.setStrokeColor(INK_300)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, self.width, self.height, 2, fill=1, stroke=1)
        # Label
        c.setFillColor(INK_500)
        c.setFont("BodySans-Bold", 7)
        c.drawString(6, self.height - 12, self.label.upper())
        # Value
        c.setFillColor(INK_900)
        c.setFont("HeadSerif-Bold", 14)
        c.drawString(6, self.height - 28, str(self.value)[:32])
        # Tier badge (right side)
        state = evidence_state_for_tier(self.tier)
        fg, bg, short = EVIDENCE_STATES[state]
        badge_w = 50
        c.setFillColor(bg)
        c.roundRect(self.width - badge_w - 4, 4, badge_w, 11, 5.5, fill=1, stroke=0)
        c.setFillColor(fg)
        c.setFont("BodySans-Bold", 6.5)
        c.drawCentredString(self.width - badge_w / 2 - 4, 7, state)
        # Note (if any)
        if self.note:
            c.setFillColor(INK_500)
            c.setFont("BodySans-Italic", 6.5)
            c.drawString(6, 6, self.note[:60])


# ----------------------------------------------------------------------------
# Generic info card (label + body, optional evidence badge)
# ----------------------------------------------------------------------------

class InfoCard(Flowable):
    """A card with title, body text, and optional evidence badge."""

    def __init__(self, title, body, evidence_state=None, width=None, height=None,
                 bg=INK_050, edge=INK_300, title_color=BRAND_700):
        Flowable.__init__(self)
        self.title = title
        self.body = body
        self.evidence_state = evidence_state
        self.width = width or 80 * mm
        # Estimate height from body length
        if height is None:
            lines = max(2, len(body) // 60 + 1)
            height = 18 + lines * 11 + 8
            if evidence_state:
                height = max(height, 38)
        self.height = height
        self.bg = bg
        self.edge = edge
        self.title_color = title_color

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        # Background
        c.setFillColor(self.bg)
        c.setStrokeColor(self.edge)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, self.width, self.height, 2, fill=1, stroke=1)
        # Title
        c.setFillColor(self.title_color)
        c.setFont("BodySans-Bold", 8)
        c.drawString(6, self.height - 14, self.title.upper())
        # Body — wrap manually
        c.setFillColor(INK_900)
        c.setFont("BodySans", 8.5)
        words = self.body.split()
        line = ""
        y = self.height - 28
        max_w = self.width - 12
        if self.evidence_state:
            max_w = self.width - 60
        for w in words:
            test = (line + " " + w).strip()
            from reportlab.pdfbase.pdfmetrics import stringWidth
            if stringWidth(test, "BodySans", 8.5) > max_w:
                c.drawString(6, y, line)
                line = w
                y -= 11
                if y < 8:
                    break
            else:
                line = test
        if line and y >= 8:
            c.drawString(6, y, line)
        # Evidence badge
        if self.evidence_state:
            state = self.evidence_state
            if state not in EVIDENCE_STATES:
                state = "UNKNOWN"
            fg, bg, short = EVIDENCE_STATES[state]
            badge_w = 48
            c.setFillColor(bg)
            c.roundRect(self.width - badge_w - 6, self.height - 22, badge_w, 12, 6, fill=1, stroke=0)
            c.setFillColor(fg)
            c.setFont("BodySans-Bold", 6.5)
            c.drawCentredString(self.width - badge_w / 2 - 6, self.height - 20, state)


# ----------------------------------------------------------------------------
# Evidence ladder (visual)
# ----------------------------------------------------------------------------

class EvidenceLadder(Flowable):
    """A visual evidence ladder showing 4 tiers with current position highlighted."""

    def __init__(self, current_tier=None, width=None, height=120):
        Flowable.__init__(self)
        self.current_tier = current_tier or "MODEL_PREDICTION"
        self.width = width or CONTENT_W
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        # 4 tiers, top to bottom: PHYSICAL > EXTERNAL > COMPUTATIONAL > MODEL
        tiers = [
            ("PHYSICAL VALIDATION", "T3 — Real hardware, independent lab", EV_PHYSICAL, EV_PHYSICAL_BG),
            ("EXTERNAL VALIDATION", "T2 — Independent code base reproduces", EV_EXTERNAL, EV_EXTERNAL_BG),
            ("COMPUTATIONAL VALIDATION", "T2 — Internal computational model", EV_COMPUTATIONAL, EV_COMPUTATIONAL_BG),
            ("MODEL PREDICTION", "T1 — Model-only, no verification", EV_MODEL, EV_MODEL_BG),
        ]
        tier_keys = ["OBSERVED", "EXTERNALLY_VERIFIED", "COMPUTATIONAL", "MODELLED"]
        current_state = evidence_state_for_tier(self.current_tier)

        bar_h = (self.height - 10) / 4
        x_center = self.width / 2
        bar_w = 240

        for i, (label, sub, fg, bg) in enumerate(tiers):
            y = self.height - 10 - (i + 1) * bar_h
            is_current = (current_state == tier_keys[i])
            # Bar
            if is_current:
                c.setFillColor(fg)
                c.setStrokeColor(fg)
                c.setLineWidth(1.5)
            else:
                c.setFillColor(bg)
                c.setStrokeColor(fg)
                c.setLineWidth(0.5)
                c.setFillColor(bg)
            c.roundRect(x_center - bar_w / 2, y + 4, bar_w, bar_h - 8, 4, fill=1, stroke=1)
            # Label
            if is_current:
                c.setFillColor(colors.white)
                c.setFont("BodySans-Bold", 9)
                c.drawCentredString(x_center, y + bar_h / 2 + 2, label + "  ← CURRENT")
                c.setFont("BodySans-Italic", 7)
                c.drawCentredString(x_center, y + bar_h / 2 - 9, sub)
            else:
                c.setFillColor(fg)
                c.setFont("BodySans-Bold", 8.5)
                c.drawCentredString(x_center, y + bar_h / 2 + 2, label)
                c.setFillColor(INK_500)
                c.setFont("BodySans-Italic", 7)
                c.drawCentredString(x_center, y + bar_h / 2 - 9, sub)
            # Connector arrow downward
            if i < 3:
                c.setStrokeColor(INK_300)
                c.setLineWidth(0.5)
                c.line(x_center, y + 2, x_center, y - 4)
                # small arrowhead
                c.setFillColor(INK_300)
                p = c.beginPath()
                p.moveTo(x_center - 2, y - 2)
                p.lineTo(x_center + 2, y - 2)
                p.lineTo(x_center, y - 5)
                p.close()
                c.drawPath(p, fill=1, stroke=0)


# ----------------------------------------------------------------------------
# Competitor matrix
# ----------------------------------------------------------------------------

def competitor_matrix_table(our_tech_name, alternatives):
    """
    Build a competitor matrix table.
    alternatives: list of dicts with keys:
      name, mechanism, advantage, disadvantage, maturity, where_we_lose, where_we_win
    """
    S = build_styles()
    header = ["Dimension", "Our Technology"] + [a["name"] for a in alternatives]
    data = [header]

    rows = [
        ("Mechanism", "mechanism"),
        ("Advantage", "advantage"),
        ("Disadvantage", "disadvantage"),
        ("Maturity", "maturity"),
        ("Where we LOSE", "where_we_lose"),
        ("Where we might WIN", "where_we_win"),
    ]

    # Our tech column for each row
    for label, key in rows:
        our_val = ""
        if key == "mechanism":
            our_val = our_tech_name
        elif key == "advantage":
            our_val = "(see dossier)"
        elif key == "disadvantage":
            our_val = "(see dossier)"
        elif key == "maturity":
            our_val = "RESEARCH"
        elif key == "where_we_lose":
            our_val = "(see dossier)"
        elif key == "where_we_win":
            our_val = "(see dossier)"
        row = [label, Paragraph(our_val, S["TableCellSmall"])]
        for a in alternatives:
            v = a.get(key, "—")
            row.append(Paragraph(str(v), S["TableCellSmall"]))
        data.append(row)

    col_widths = [22 * mm, 38 * mm] + [(CONTENT_W - 60 * mm) / max(1, len(alternatives))] * len(alternatives)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_700),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "BodySans-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, INK_050]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BRAND_900),
        ("LINEABOVE", (0, 5), (-1, 5), 0.3, INK_300),  # rule before "where we lose"
        ("TEXTCOLOR", (0, 5), (0, 5), RISK_HIGH),
        ("FONTNAME", (0, 5), (0, 5), "BodySans-Bold"),
    ]))
    return t


# ----------------------------------------------------------------------------
# Failure / uncertainty block
# ----------------------------------------------------------------------------

class FailureBlock(Flowable):
    """KNOWN / UNKNOWN / KILL CONDITION / NEXT QUESTION block."""

    def __init__(self, known_list, unknown_list, kill_condition, next_question,
                 width=None, height=None):
        Flowable.__init__(self)
        self.known = known_list
        self.unknown = unknown_list
        self.kill = kill_condition
        self.next_q = next_question
        self.width = width or CONTENT_W
        # Estimate height
        max_items = max(len(known_list), len(unknown_list), 1)
        self.height = height or (40 + max_items * 11 + 60)

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        # Two columns: KNOWN (left), UNKNOWN (right)
        col_w = (self.width - 6) / 2
        col_h = self.height - 60

        # KNOWN column
        c.setFillColor(EV_PHYSICAL_BG)
        c.setStrokeColor(EV_PHYSICAL)
        c.setLineWidth(0.5)
        c.roundRect(0, self.height - col_h - 12, col_w, col_h, 3, fill=1, stroke=1)
        c.setFillColor(EV_PHYSICAL)
        c.setFont("BodySans-Bold", 8.5)
        c.drawString(6, self.height - 24, "KNOWN")
        c.setFillColor(INK_900)
        c.setFont("BodySans", 8)
        y = self.height - 38
        for item in self.known[:6]:
            # Checkmark
            c.setFillColor(EV_PHYSICAL)
            c.drawString(6, y, "✓")
            c.setFillColor(INK_900)
            # Item text (truncate if long)
            text = item[:65] + ("…" if len(item) > 65 else "")
            c.drawString(14, y, text)
            y -= 11

        # UNKNOWN column
        c.setFillColor(EV_UNKNOWN_BG)
        c.setStrokeColor(EV_UNKNOWN)
        c.setLineWidth(0.5)
        c.roundRect(col_w + 6, self.height - col_h - 12, col_w, col_h, 3, fill=1, stroke=1)
        c.setFillColor(EV_UNKNOWN)
        c.setFont("BodySans-Bold", 8.5)
        c.drawString(col_w + 12, self.height - 24, "UNKNOWN")
        c.setFillColor(INK_900)
        c.setFont("BodySans", 8)
        y = self.height - 38
        for item in self.unknown[:6]:
            # Question mark
            c.setFillColor(EV_UNKNOWN)
            c.drawString(col_w + 12, y, "?")
            c.setFillColor(INK_900)
            text = item[:65] + ("…" if len(item) > 65 else "")
            c.drawString(col_w + 20, y, text)
            y -= 11

        # KILL CONDITION (red bar)
        kill_y = 28
        c.setFillColor(EV_KILLED_BG)
        c.setStrokeColor(EV_KILLED)
        c.setLineWidth(0.5)
        c.roundRect(0, kill_y, self.width, 22, 3, fill=1, stroke=1)
        c.setFillColor(EV_KILLED)
        c.setFont("BodySans-Bold", 7.5)
        c.drawString(6, kill_y + 14, "KILL CONDITION")
        c.setFillColor(INK_900)
        c.setFont("BodySans", 8)
        c.drawString(6, kill_y + 4, self.kill[:110] + ("…" if len(self.kill) > 110 else ""))

        # NEXT QUESTION (accent bar)
        nq_y = 2
        c.setFillColor(ACCENT_LIGHT)
        c.setStrokeColor(ACCENT)
        c.setLineWidth(0.5)
        c.roundRect(0, nq_y, self.width, 22, 3, fill=1, stroke=1)
        c.setFillColor(ACCENT)
        c.setFont("BodySans-Bold", 7.5)
        c.drawString(6, nq_y + 14, "NEXT QUESTION")
        c.setFillColor(INK_900)
        c.setFont("BodySans", 8)
        c.drawString(6, nq_y + 4, self.next_q[:110] + ("…" if len(self.next_q) > 110 else ""))


# ----------------------------------------------------------------------------
# Validation roadmap (TODAY → bench → prototype → relevant env → regulatory → commercial)
# ----------------------------------------------------------------------------

class ValidationRoadmap(Flowable):
    """Horizontal milestone roadmap."""

    def __init__(self, milestones, width=None, height=110):
        Flowable.__init__(self)
        self.milestones = milestones  # list of dicts: stage, deliverable, cost, time, gate
        self.width = width or CONTENT_W
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        if not self.milestones:
            return
        n = len(self.milestones)
        spacing = self.width / n
        y_center = self.height / 2 + 8

        # Horizontal line
        c.setStrokeColor(INK_300)
        c.setLineWidth(2)
        c.line(spacing / 2, y_center, self.width - spacing / 2, y_center)

        for i, m in enumerate(self.milestones):
            cx = spacing * (i + 0.5)
            # Circle node
            is_today = (i == 0)
            if is_today:
                c.setFillColor(ACCENT)
                c.setStrokeColor(ACCENT)
            else:
                c.setFillColor(colors.white)
                c.setStrokeColor(BRAND_500)
            c.setLineWidth(1.5)
            c.circle(cx, y_center, 5, fill=1, stroke=1)
            if is_today:
                c.setFillColor(ACCENT)
                c.circle(cx, y_center, 2.5, fill=1, stroke=0)

            # Stage label (above)
            c.setFillColor(INK_900 if is_today else INK_700)
            c.setFont("BodySans-Bold", 8)
            c.drawCentredString(cx, y_center + 12, m.get("stage", f"M{i}"))

            # Detail (below)
            c.setFillColor(INK_500)
            c.setFont("BodySans-Italic", 6.5)
            detail_parts = []
            if m.get("cost"):
                detail_parts.append(m["cost"])
            if m.get("time"):
                detail_parts.append(m["time"])
            detail = " · ".join(detail_parts)
            c.drawCentredString(cx, y_center - 10, detail[:30])

            if m.get("deliverable"):
                # Wrap deliverable
                words = m["deliverable"].split()
                line = ""
                y = y_center - 22
                for w in words:
                    test = (line + " " + w).strip()
                    from reportlab.pdfbase.pdfmetrics import stringWidth
                    if stringWidth(test, "BodySans", 7) > spacing - 4:
                        c.setFillColor(INK_700)
                        c.setFont("BodySans", 7)
                        c.drawCentredString(cx, y, line)
                        line = w
                        y -= 8
                        if y < 4:
                            break
                    else:
                        line = test
                if line and y >= 4:
                    c.setFillColor(INK_700)
                    c.setFont("BodySans", 7)
                    c.drawCentredString(cx, y, line)

        # TODAY label on left
        c.setFillColor(ACCENT)
        c.setFont("BodySans-Bold", 7)
        c.drawString(0, self.height - 6, "TODAY")


# ----------------------------------------------------------------------------
# Deal path (VALIDATION → CO-DEVELOPMENT → LICENSE → ACQUISITION)
# ----------------------------------------------------------------------------

class DealPath(Flowable):
    """Horizontal deal path with arrows."""

    def __init__(self, paths, primary_action, width=None, height=70):
        Flowable.__init__(self)
        self.paths = paths
        self.primary = primary_action
        self.width = width or CONTENT_W
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        if not self.paths:
            return

        # Primary action at top
        c.setFillColor(ACCENT_LIGHT)
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1)
        c.roundRect(0, self.height - 24, self.width, 18, 3, fill=1, stroke=1)
        c.setFillColor(ACCENT)
        c.setFont("BodySans-Bold", 7)
        c.drawString(8, self.height - 14, "PRIMARY ASK")
        c.setFillColor(INK_900)
        c.setFont("BodySans-Bold", 9)
        c.drawString(80, self.height - 14, self.primary[:90])

        # Pathway
        n = len(self.paths)
        spacing = self.width / n
        y = 18
        for i, p in enumerate(self.paths):
            cx = spacing * (i + 0.5)
            # Box
            c.setFillColor(BRAND_100)
            c.setStrokeColor(BRAND_500)
            c.setLineWidth(0.8)
            box_w = min(spacing - 8, 90)
            c.roundRect(cx - box_w / 2, y - 4, box_w, 16, 3, fill=1, stroke=1)
            c.setFillColor(BRAND_900)
            c.setFont("BodySans-Bold", 7.5)
            c.drawCentredString(cx, y + 2, p)
            # Arrow to next
            if i < n - 1:
                c.setStrokeColor(INK_500)
                c.setLineWidth(0.8)
                c.line(cx + box_w / 2 + 2, y + 4, cx + spacing - box_w / 2 - 2, y + 4)
                # Arrowhead
                c.setFillColor(INK_500)
                p_obj = c.beginPath()
                p_obj.moveTo(cx + spacing - box_w / 2 - 5, y + 6)
                p_obj.lineTo(cx + spacing - box_w / 2 - 2, y + 4)
                p_obj.lineTo(cx + spacing - box_w / 2 - 5, y + 2)
                p_obj.close()
                c.drawPath(p_obj, fill=1, stroke=0)


# ----------------------------------------------------------------------------
# AI learning loop footer
# ----------------------------------------------------------------------------

class LearningLoopFooter(Flowable):
    """The small footer showing the AI learning loop."""

    def __init__(self, current_state="CURRENT STATE", width=None, height=46):
        Flowable.__init__(self)
        self.current_state = current_state
        self.width = width or CONTENT_W
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        stages = ["CURRENT PACKAGE", "BUYER EVAL", "EXPERIMENT", "REAL DATA",
                  "BELIEF UPDATE", "KNOWLEDGE", "NEXT EXPERIMENT", "PACKAGE V2"]
        n = len(stages)
        spacing = self.width / n

        # Box + label
        c.setFillColor(INK_050)
        c.setStrokeColor(INK_300)
        c.setLineWidth(0.4)
        c.roundRect(0, 0, self.width, self.height, 2, fill=1, stroke=1)

        # Title
        c.setFillColor(INK_500)
        c.setFont("BodySans-Bold", 6.5)
        c.drawString(4, self.height - 8, "AI LEARNING LOOP")

        # Reality marker
        c.setFillColor(EV_KILLED)
        c.setFont("BodySans-BoldItalic", 6)
        c.drawString(self.width - 100, self.height - 8, "REALITY NOT YET OBSERVED")

        # Stages
        y = 8
        for i, s in enumerate(stages):
            cx = spacing * (i + 0.5)
            is_current = (i == 0)
            if is_current:
                c.setFillColor(ACCENT)
            else:
                c.setFillColor(BRAND_300)
            c.circle(cx, y + 6, 2.5, fill=1, stroke=0)
            c.setFillColor(INK_700 if not is_current else ACCENT)
            c.setFont("BodySans-Bold" if is_current else "BodySans", 5.5)
            c.drawCentredString(cx, y - 1, s)
            if i < n - 1:
                c.setStrokeColor(INK_300)
                c.setLineWidth(0.4)
                c.line(cx + 2.5, y + 6, cx + spacing - 2.5, y + 6)


# ----------------------------------------------------------------------------
# Provenance footer
# ----------------------------------------------------------------------------

class ProvenanceFooter(Flowable):
    """Provenance footer with hash + sources."""

    def __init__(self, package_id, manifest, constitution_sha, width=None, height=38):
        Flowable.__init__(self)
        self.package_id = package_id
        self.manifest = manifest
        self.constitution_sha = constitution_sha
        self.width = width or CONTENT_W
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(INK_050)
        c.setStrokeColor(INK_300)
        c.setLineWidth(0.4)
        c.roundRect(0, 0, self.width, self.height, 2, fill=1, stroke=1)
        # Eyebrow
        c.setFillColor(INK_500)
        c.setFont("BodySans-Bold", 6.5)
        c.drawString(6, self.height - 9, "PROVENANCE")
        # Manifest
        c.setFillColor(INK_700)
        c.setFont("Mono", 6.5)
        manifest_text = self.manifest[:110] + ("…" if len(self.manifest) > 110 else "")
        c.drawString(6, self.height - 18, manifest_text)
        # Constitution hash
        c.setFillColor(INK_500)
        c.setFont("BodySans-Italic", 6)
        c.drawString(6, 4, f"Constitution v1.7.0 SHA-256: {self.constitution_sha[:24]}…")
        # Package ID (right)
        c.setFillColor(BRAND_700)
        c.setFont("BodySans-Bold", 7)
        c.drawRightString(self.width - 6, self.height - 9, f"PACKAGE {self.package_id}")


# ----------------------------------------------------------------------------
# Confidentiality footer
# ----------------------------------------------------------------------------

class ConfidentialityFooter(Flowable):
    """Confidentiality banner for the bottom of every page."""

    def __init__(self, package_id=None, level="Level 2 — Executive Dossier", width=None, height=14):
        Flowable.__init__(self)
        self.package_id = package_id
        self.level = level
        self.width = width or CONTENT_W
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(INK_100)
        c.setStrokeColor(INK_300)
        c.setLineWidth(0.3)
        c.roundRect(0, 0, self.width, self.height, 1.5, fill=1, stroke=1)
        c.setFillColor(INK_500)
        c.setFont("BodySans-Bold", 6.5)
        left_text = "CONFIDENTIAL — Technology Transfer Package — Do Not Distribute"
        c.drawString(4, 4, left_text)
        c.setFont("BodySans", 6.5)
        c.drawCentredString(self.width / 2, 4, self.level)
        c.setFont("BodySans-Bold", 6.5)
        right_text = f"PKG {self.package_id}" if self.package_id else ""
        c.drawRightString(self.width - 4, 4, right_text)


# ----------------------------------------------------------------------------
# Page header (running header for inside pages)
# ----------------------------------------------------------------------------

class PageHeader(Flowable):
    """Small running header at top of inside pages."""

    def __init__(self, package_id, package_name, section_name=None, width=None, height=18):
        Flowable.__init__(self)
        self.package_id = package_id
        self.package_name = package_name
        self.section_name = section_name
        self.width = width or CONTENT_W
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        # Top rule
        c.setStrokeColor(BRAND_500)
        c.setLineWidth(0.5)
        c.line(0, self.height - 2, self.width, self.height - 2)
        # Left: package ID + name
        c.setFillColor(BRAND_700)
        c.setFont("BodySans-Bold", 7)
        c.drawString(0, self.height - 11, f"{self.package_id}  ·  {self.package_name}"[:90])
        # Right: section name
        if self.section_name:
            c.setFillColor(INK_500)
            c.setFont("BodySans-Italic", 7)
            c.drawRightString(self.width, self.height - 11, self.section_name)


# ----------------------------------------------------------------------------
# Page footer (page number)
# ----------------------------------------------------------------------------

class PageNumberFooter(Flowable):
    """Page number footer."""

    def __init__(self, page_num, total_pages=None, width=None, height=10):
        Flowable.__init__(self)
        self.page_num = page_num
        self.total_pages = total_pages
        self.width = width or CONTENT_W
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(INK_500)
        c.setFont("BodySans", 7)
        if self.total_pages:
            text = f"{self.page_num} / {self.total_pages}"
        else:
            text = f"{self.page_num}"
        c.drawRightString(self.width, 0, text)
        c.setFont("BodySans-Italic", 7)
        c.drawString(0, 0, "CereVasc eShunt Technology-Transfer Portfolio")


# ----------------------------------------------------------------------------
# Helper: build two-column layout
# ----------------------------------------------------------------------------

def two_column_layout(left_flowables, right_flowables, col_w=None, gutter=GUTTER):
    """Build a two-column table layout."""
    if col_w is None:
        col_w = (CONTENT_W - gutter) / 2
    t = Table([[left_flowables, right_flowables]],
              colWidths=[col_w, col_w])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), gutter),
    ]))
    return t


# ----------------------------------------------------------------------------
# Page templates (Frame + onPage callback)
# ----------------------------------------------------------------------------

def make_page_template(canvas_obj, doc, package_id=None, package_name=None, level="Executive Dossier"):
    """Standard onPage callback: draw header, footer, page number, confidentiality."""
    canvas_obj.saveState()

    # Page background (subtle)
    # (kept white for restraint)

    # Top running header
    if package_id:
        canvas_obj.setStrokeColor(BRAND_500)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(MARGIN_L, PAGE_H - MARGIN_T + 6,
                        PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 6)
        canvas_obj.setFillColor(BRAND_700)
        canvas_obj.setFont("BodySans-Bold", 7)
        canvas_obj.drawString(MARGIN_L, PAGE_H - MARGIN_T + 9,
                              f"{package_id}  ·  {package_name}"[:100] if package_name else package_id)
        canvas_obj.setFillColor(INK_500)
        canvas_obj.setFont("BodySans-Italic", 7)
        canvas_obj.drawRightString(PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 9, level)

    # Bottom: page number + confidentiality
    canvas_obj.setStrokeColor(INK_300)
    canvas_obj.setLineWidth(0.3)
    canvas_obj.line(MARGIN_L, MARGIN_B - 6, PAGE_W - MARGIN_R, MARGIN_B - 6)

    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans", 7)
    canvas_obj.drawString(MARGIN_L, MARGIN_B - 14,
                          "CereVasc eShunt Technology-Transfer Portfolio")

    canvas_obj.setFont("BodySans-Bold", 7)
    canvas_obj.drawCentredString(PAGE_W / 2, MARGIN_B - 14,
                                 f"CONFIDENTIAL  ·  {level}")

    canvas_obj.setFont("BodySans", 7)
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, MARGIN_B - 14,
                               f"{doc.page}")

    canvas_obj.restoreState()


def make_cover_page_template(canvas_obj, doc):
    """Cover page template — minimal, no header/footer."""
    canvas_obj.saveState()
    # Subtle accent bar at the very top
    canvas_obj.setFillColor(ACCENT)
    canvas_obj.rect(0, PAGE_H - 4, PAGE_W, 4, fill=1, stroke=0)
    # Bottom signature line
    canvas_obj.setStrokeColor(BRAND_500)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(MARGIN_L, 28, PAGE_W - MARGIN_R, 28)
    canvas_obj.setFillColor(INK_500)
    canvas_obj.setFont("BodySans-Italic", 7)
    canvas_obj.drawString(MARGIN_L, 18, "CereVasc eShunt Technology-Transfer Portfolio")
    canvas_obj.drawRightString(PAGE_W - MARGIN_R, 18, "CONFIDENTIAL — Level 2 Executive Dossier")
    canvas_obj.restoreState()


# ----------------------------------------------------------------------------
# Image flowable with fit-to-width
# ----------------------------------------------------------------------------

def fit_image(path, max_w=None, max_h=None):
    """Load an image and scale to fit max_w/max_h while preserving aspect ratio."""
    if max_w is None:
        max_w = CONTENT_W
    if max_h is None:
        max_h = 110 * mm

    img = Image(path)
    iw, ih = img.imageWidth, img.imageHeight
    aspect = iw / ih
    target_w = max_w
    target_h = target_w / aspect
    if target_h > max_h:
        target_h = max_h
        target_w = target_h * aspect
    img.drawWidth = target_w
    img.drawHeight = target_h
    return img

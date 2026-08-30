"""
experiment_diagram.py — R371 Phase 5 / R372-2 upgrade: decisive-experiment
/ verification-setup diagram, rendered FROM a structured, machine-checkable
spec (r372.diagram_adequacy.experiment_diagram_spec).

Every box corresponds to a required experiment role (CEO R372-2):
  test article / stimulus / instrumentation / measured outputs /
  control variables / decision criterion / kill condition

Every label comes from the canonical engineering record:
  test article   <- build plan WP-01 .test_article
  stimulus       <- verification V-001 .method (the applied test protocol)
  apparatus      <- build plan WP-01 .equipment
  measurement    <- build plan WP-01 .measurement
  acceptance     <- verification V-001 .acceptance (or WP acceptance_criterion)
  control vars   <- critical parameters (recorded values) with the explicit
                    NOT_SEPARATELY_RECORDED marker — the canonical record has
                    no separate control-variable field and that fact is
                    stated, never papered over (Constitution Art. XXV)
  fail branch    <- package kill condition (headlines registry)
  duration       <- build plan WP-01 .estimated_effort

No decorative medical imagery. No fake CAD. No depiction of a prototype.
The diagram explicitly states that no experiment has been run
(verification results are NOT_TESTED in the canonical record).

R375-3 (CEO final PDF rendering hardening, 2026-08-30):
  * The figure GROWS with measured content (same text size, taller
    canvas) instead of ever shrinking fonts.
  * If the one-page aspect budget would be exceeded, the diagram
    SPLITS into two stacked figures (rows reflowed), each embedded on
    its own page — content is never clipped and never shrunk to
    unreadability.
  * After layout, the engine SELF-VERIFIES: every box inside the axes
    bounds, zero box-box overlap, measured text fits its box. Any
    violation raises (hard build failure, Art. XIV).
"""

import os
import re
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

try:
    fm.fontManager.addfont('/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf')
except Exception:
    pass
try:
    fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
except Exception:
    pass
plt.rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

INK = "#0c1e38"
BRAND = "#1e3a8a"
BRAND_LIGHT = "#e8eef9"
GREEN = "#166534"
GREEN_LIGHT = "#e7f3ea"
RED = "#b91c1c"
RED_LIGHT = "#fbeaea"
GREY = "#4a4a4a"


def _wrap(text: str, width: int = 30) -> str:
    return "\n".join(textwrap.wrap(text, width=width)) if text else ""


def _clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


# --- V3 render fix (CEO Directive 2, 2026-08-30) ---------------------------
# The V2 diagram drew every box at a FIXED height (1.75 data units). When a
# MODELLED/UNKNOWN parameter list was long, the text spilled below the box
# boundary and overwrote the PASS/FAIL boxes — 265-493 overlapping pairs on
# the build-plan page across the 15 packages. The helpers below MEASURE the
# content BEFORE drawing: the box height derives from the wrapped line
# count, and each row's layout y advances by the measured max height.

FIG_W_IN = 12.5                                # figure width (inches)
XU = 13.0                                      # axes data width (data units)

# R375-3 one-page aspect budget: the dossier embeds the diagram at
# 6.9*72 = 496.8pt width; the usable page height is 792 - 50.4 - 54 =
# 687.6pt. Max aspect = 687.6 / 496.8 = 1.384 -> YU_max = XU * 1.384.
# The figure GROWS with content (fig_h = yu * 7.6/8.6), so the vertical
# data-unit scale (du per inch) is CONSTANT — box offsets measured in
# data units keep their physical size on every canvas size. Text never
# shrinks; the canvas gets taller.
MAX_ASPECT = 1.38
YU_MAX = XU * MAX_ASPECT
DU_PER_IN_Y = 8.6 / 7.6                       # constant vertical scale


def _du_per_in_x() -> float:
    return XU / FIG_W_IN


def _du_per_in_y() -> float:
    return DU_PER_IN_Y


def _measure_height(body: str, w_du: float, body_size: float) -> float:
    """Height (data units) the wrapped body needs inside a box of width
    w_du: wrap to a character budget derived from the physical column
    width, then convert line count * leading to data units."""
    inner_in = max(0.2, (w_du * _du_per_in_x()) - 0.12)   # minus padding
    # R375-4: measured DejaVu/Noto average 0.00784 in/char/pt; 0.0082
    # with margin (V3 used 0.0075 -> rendered lines exceeded columns)
    char_w_in = body_size * 0.0082
    chars_per_line = max(8, int(inner_in / char_w_in))
    lines = textwrap.wrap(str(body), width=chars_per_line) or [""]
    line_h_in = (body_size * 1.30) / 72.0
    # R375-4 LIVE DEFECT FIX (found by the FX4 fixture self-check, latent
    # since V3): data units per VERTICAL inch is > 1 (8.6du over 7.6in),
    # so line height in du must MULTIPLY by it. V3 divided, making every
    # wrapped box ~12% shorter than its text (invisible to the PDF-layer
    # gate; mechanically caught by the new in-PNG text-geometry check).
    return len(lines) * line_h_in * _du_per_in_y()


def _box_height(header: str, body: str, w_du: float, body_size: float,
                min_h: float = 1.05) -> float:
    """Total box height = header band + measured content + padding, never
    below min_h (a short box still looks like a box). Heights are measured
    in the BASE geometry (7.6in figure) so layout is font-size-exact.
    R375-4: 0.12du extra headroom below the header — glyph ascent/descent
    exceed the nominal line box at high line counts (caught live by the
    FX4 fixture self-check at 45 wrapped lines)."""
    content_h = _measure_height(body, w_du, body_size)
    header_h = 0.54
    return max(min_h, header_h + content_h + 0.22)


def _self_verify(boxes, yu, label):
    """R375-3/4: mechanical layout verification. boxes = list of
    (x, y_bottom, w, h, name) in data units. Raises on any violation."""
    errors = []
    for (x, y, w, h, name) in boxes:
        if x < -1e-6 or y < -1e-6 or x + w > XU + 1e-6 or y + h > yu + 1e-6:
            errors.append(
                f"box '{name}' outside axes bounds: "
                f"x[{x:.2f},{x + w:.2f}] y[{y:.2f},{y + h:.2f}] "
                f"within [0,{XU:.1f}]x[0,{yu:.1f}]")
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            ax_, ay, aw, ah, an = boxes[i]
            bx, by, bw, bh, bn = boxes[j]
            # pad=0.06 in boxstyle inflates drawn boxes slightly
            ix = min(ax_ + aw, bx + bw) - max(ax_, bx)
            iy = min(ay + ah, by + bh) - max(ay, by)
            if ix > 0.12 and iy > 0.12:   # > padding tolerance
                errors.append(
                    f"box overlap: '{an}' intersects '{bn}' by "
                    f"{ix:.2f}x{iy:.2f} data units")
    if errors:
        raise RuntimeError(
            f"experiment diagram layout invalid ({label}): "
            + "; ".join(errors))


def build_experiment_diagrams(pkg, headlines: dict, out_path: str,
                              spec: dict = None) -> list:
    """Render the decisive-experiment setup diagram(s) for one package.

    R375-3: returns a LIST of PNG paths (one element normally; two when
    the content reflows past the one-page aspect budget and the layout
    splits into 'setup' + 'decision' figures). Every box is auto-sized
    from measured content; fonts never shrink; layout self-verifies.
    """
    from premium_package_factory.diagrams.factory import (
        verify_text_geometry)
    if spec is None:
        from premium_package_factory.r372.diagram_adequacy import (
            experiment_diagram_spec)
        spec = experiment_diagram_spec(pkg, headlines)

    roles = spec["roles"]
    wp_id = spec.get("work_package", "WP-01")

    consequence = roles.get("decision_consequence", {}).get("content", "")
    pass_branch = consequence.split(". IF KILL")[0] if consequence else \
        "Proceed per canonical build plan"
    fail_branch = consequence.split("IF KILL CONDITION MET -> stop; "
                                    "do not build: ")[-1] if "IF KILL" in \
        consequence else roles["kill_condition"]["content"]

    # ---- measure all rows (base geometry, data units) --------------------
    r1_w1, r1_w2, r1_w3 = 3.6, 3.5, 4.1
    r2_w1, r2_w2, r2_w3 = 3.6, 3.6, 4.2
    r3_w1, r3_w2 = 3.6, 4.2

    # R375-3 COLUMNAR REFLOW for pathological control lists: a single
    # 3.6du-wide control box whose measured height exceeds CTRL_SINGLE_MAX
    # reflows into a FULL-WIDTH multi-column band (up to 3 columns) so a
    # large variable record still fits one page. Fonts never shrink.
    CTRL_SINGLE_MAX = 11.0
    ctrl_content = roles["control_variables"]["content"]

    def _ctrl_chunks(k):
        col_w = (12.4 - 0.3 * (k - 1)) / k
        items = ctrl_content.split("; ")
        per = -(-len(items) // k)
        return col_w, ["; ".join(items[ci * per:(ci + 1) * per]).strip(" ;")
                      or "—" for ci in range(k)]

    def _ctrl_band_height(k):
        """Measured from the ACTUAL chunks — a /k division would
        undercount (headers and padding do not divide)."""
        col_w, chunks = _ctrl_chunks(k)
        return max(_box_height("CONTROL VARIABLES", c, col_w, 6.4)
                   for c in chunks)

    ctrl_columns = 1
    h_ctrl_single = _box_height("CONTROL VARIABLES", ctrl_content, r2_w1,
                                6.4)
    if h_ctrl_single > CTRL_SINGLE_MAX:
        for k in (2, 3):
            if _ctrl_band_height(k) <= CTRL_SINGLE_MAX:
                ctrl_columns = k
                break
        if ctrl_columns == 1:
            # even 3 columns cannot contain it -> hard fail (Art. XIV)
            raise RuntimeError(
                f"experiment diagram: control-variable record for "
                f"{pkg.pkg_id} exceeds diagram capacity even in a "
                f"3-column reflow (single-column height "
                f"{h_ctrl_single:.1f} du vs {CTRL_SINGLE_MAX} budget) — "
                f"split the canonical record or extend the layout "
                f"engine; no text shrinking")

    h1 = max(_box_height("TEST ARTICLE", roles["test_article"]["content"],
                         r1_w1, 7.0),
             _box_height("STIMULUS", roles["stimulus"]["content"], r1_w2, 7.0),
             _box_height("INSTRUMENTATION",
                         roles["instrumentation"]["content"], r1_w3, 7.0),
             1.45)
    h_meas = _box_height("MEASURED OUTPUTS",
                         roles["measured_outputs"]["content"], r2_w2, 7.0)
    h_crit = _box_height("DECISION CRITERION",
                         roles["decision_criterion"]["content"], r2_w3, 7.0)
    if ctrl_columns == 1:
        h_ctrl_band = 0.0                       # inline in row 2
        h_row2 = max(h_ctrl_single, h_meas, h_crit, 1.45)
    else:
        h_ctrl_band = _ctrl_band_height(ctrl_columns)  # dedicated band
        h_row2 = max(h_meas, h_crit, 1.45)
    h3 = max(_box_height("PASS → CONSEQUENCE", pass_branch, r3_w2, 6.3),
             _box_height("FAIL → KILL CONDITION",
                         f"Stop; do not build: {fail_branch}", r3_w1, 6.3),
             1.35)

    title_zone = 1.55      # title + subtitle + gap
    gap = 0.55
    footer_zone = 0.85
    base_bottom = 0.52

    def _stack(h3_arg):
        """Total canvas height for the given decision-row height."""
        h = title_zone + h1 + gap
        if h_ctrl_band:
            h += h_ctrl_band + gap
        h += h_row2 + gap
        if h3_arg:
            h += h3_arg + base_bottom
        else:
            h += base_bottom
        return h + footer_zone

    needed_one = _stack(h3)
    if needed_one <= YU_MAX:
        plans = [("full", h3)]
    else:
        # R375-3 reflow -> split: part A = setup rows, part B = decision
        part_a = _stack(None)
        part_b = title_zone + h3 + base_bottom + footer_zone
        if part_a > YU_MAX or part_b > YU_MAX:
            raise RuntimeError(
                f"experiment diagram cannot fit one page even after "
                f"split (part A {part_a:.1f}, part B {part_b:.1f}, "
                f"budget {YU_MAX:.1f} data units) — the canonical "
                f"content for {pkg.pkg_id} exceeds the diagram "
                f"capacity; split the record or extend the layout "
                f"engine (no text shrinking, Art. XIV fail-closed)")
        plans = [("setup", None), ("decision", h3)]

    paths = []
    stem, ext = os.path.splitext(out_path)
    for part_idx, plan in enumerate(plans):
        mode, ph3 = plan
        if mode == "full":
            yu = max(8.6, needed_one)
        elif mode == "setup":
            yu = max(8.6, _stack(None))
        else:
            yu = max(8.6, title_zone + ph3 + base_bottom + footer_zone)
        # R375-3: the figure GROWS — data-unit height grows with it, so
        # the drawn text size in INCHES (what the buyer sees) is constant.
        fig_h_in = yu * (7.6 / 8.6)

        part_path = (out_path if len(plans) == 1
                     else f"{stem}_part{part_idx + 1}{ext}")
        # R375-4 robustness: constrained_layout COLLAPSES on tall canvases
        # (caught live by the FX4 fixture: 'axes sizes collapsed to zero'
        # -> texts landed outside the shrunken axes). A full-bleed
        # schematic needs NO layout engine: the axes fills the figure
        # exactly and all geometry is controlled in data units, verified
        # mechanically after draw.
        fig = plt.figure(figsize=(FIG_W_IN, fig_h_in))
        ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.set_xlim(0, XU)
        ax.set_ylim(0, yu)
        ax.axis("off")

        ax.text(XU / 2, yu - 0.30, f"Decisive Experiment Setup — {wp_id}"
                + ("" if mode == "full" else
                   f" ({'setup' if mode == 'setup' else 'decision'}, "
                   f"part {part_idx + 1} of {len(plans)})"),
                ha="center", va="center", fontsize=13.5, fontweight="bold",
                color=INK)
        ax.text(XU / 2, yu - 0.65,
                f"{pkg.pkg_id} · {_clean(headlines.get('technology_name',''))}",
                ha="center", va="center", fontsize=8.5, color=GREY)

        def line_h_du(body_size):
            return (body_size * 1.30 / 72.0) * _du_per_in_y()

        def box(x, y_bottom, w, header, body, edge, face, body_size=7.0,
                h=None, name=""):
            """Auto-sized box anchored at its BOTTOM edge (measured)."""
            total_h = h if h is not None else _box_height(
                header, body, w, body_size)
            ax.add_patch(FancyBboxPatch((x, y_bottom), w, total_h,
                         boxstyle="round,pad=0.06,rounding_size=0.12",
                         linewidth=1.3, edgecolor=edge, facecolor=face))
            ax.text(x + w / 2, y_bottom + total_h - 0.20, header,
                    ha="center", va="center", fontsize=8.2,
                    fontweight="bold", color=edge)
            inner_in = max(0.2, (w * _du_per_in_x()) - 0.12)
            char_w_in = body_size * 0.0082
            chars_per_line = max(8, int(inner_in / char_w_in))
            lines = textwrap.wrap(str(body), width=chars_per_line) or [""]
            lh = line_h_du(body_size)
            text_y = y_bottom + total_h - 0.58 - (len(lines) - 1) * lh / 2
            ax.text(x + w / 2, text_y, "\n".join(lines), ha="center",
                    va="center", fontsize=body_size, color=INK,
                    linespacing=1.30)
            layout_boxes.append((x, y_bottom, w, total_h, name or header))

        def arrow(x1, y1, x2, y2, label="", color=INK, rad=0.0):
            ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                         arrowstyle="-|>", mutation_scale=13, linewidth=1.2,
                         color=color,
                         connectionstyle=f"arc3,rad={rad}"))
            if label:
                ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.16, label,
                        ha="center", va="center", fontsize=7.4, color=color,
                        fontweight="bold")

        layout_boxes = []

        if mode in ("full", "setup"):
            y1 = yu - title_zone - h1
            box(0.3, y1, r1_w1, "TEST ARTICLE",
                roles["test_article"]["content"], BRAND, BRAND_LIGHT,
                body_size=7.0, h=h1, name="test_article")
            box(4.3, y1, r1_w2, "STIMULUS", roles["stimulus"]["content"],
                BRAND, BRAND_LIGHT, body_size=7.0, h=h1, name="stimulus")
            box(8.6, y1, r1_w3, "INSTRUMENTATION",
                roles["instrumentation"]["content"], BRAND, BRAND_LIGHT,
                body_size=7.0, h=h1, name="instrumentation")
            arrow(3.9, y1 + h1 / 2, 4.3, y1 + h1 / 2)
            arrow(7.8, y1 + h1 / 2, 8.6, y1 + h1 / 2)
            ax.text(2.1, y1 - 0.30,
                    f"Planned effort: "
                    f"{spec.get('planned_effort', 'NOT_RECORDED')}",
                    ha="center", va="center", fontsize=7.0, color=GREY,
                    style="italic")

            y2 = y1 - gap - (h_ctrl_band + gap if h_ctrl_band else 0) \
                - h_row2
            if ctrl_columns == 1:
                box(0.3, y2, r2_w1, "CONTROL VARIABLES",
                    roles["control_variables"]["content"], GREY, "#f4f4f4",
                    body_size=6.4, h=h_row2, name="control_variables")
            else:
                # dedicated full-width multi-column control band
                ycb = y2 + h_row2 + gap
                col_w, chunks = _ctrl_chunks(ctrl_columns)
                for ci, chunk in enumerate(chunks):
                    cx = 0.3 + ci * (col_w + 0.3)
                    box(cx, ycb, col_w,
                        f"CONTROL VARIABLES ({ci + 1}/{ctrl_columns})",
                        chunk, GREY, "#f4f4f4",
                        body_size=6.4, h=h_ctrl_band,
                        name=f"control_variables_col{ci + 1}")
            box(4.4, y2, r2_w2, "MEASURED OUTPUTS",
                roles["measured_outputs"]["content"], BRAND, BRAND_LIGHT,
                body_size=7.0, h=h_row2, name="measured_outputs")
            box(8.5, y2, r2_w3, "DECISION CRITERION",
                roles["decision_criterion"]["content"], GREEN, GREEN_LIGHT,
                body_size=7.0, h=h_row2, name="decision_criterion")
            arrow(3.9, y1, 3.9, y2 + h_row2, rad=0.0)
            arrow(3.9, y2 + h_row2 / 2, 4.4, y2 + h_row2 / 2)
            arrow(8.0, y2 + h_row2 / 2, 8.5, y2 + h_row2 / 2)
            arrow(10.6, y1, 10.6, y2 + h_row2)

        if mode in ("full", "decision"):
            if mode == "full":
                y3 = base_bottom
                h_pass = _box_height("PASS → CONSEQUENCE", pass_branch,
                                     r3_w2, 6.3)
                box(8.5, y3, r3_w2, "PASS → CONSEQUENCE", pass_branch,
                    GREEN, GREEN_LIGHT, body_size=6.3, h=h3,
                    name="pass")
                box(4.4, y3, r3_w1, "FAIL → KILL CONDITION",
                    f"Stop; do not build: {fail_branch}", RED, RED_LIGHT,
                    body_size=6.3, h=h3, name="fail")
                arrow(10.2, y2, 10.6, y3 + h3 + 0.18, "PASS", GREEN)
                arrow(8.5, y2 + 0.35, 8.0, y3 + h3 + 0.18, "FAIL", RED,
                      rad=0.18)
            else:
                y3 = base_bottom
                box(8.5, y3, r3_w2, "PASS → CONSEQUENCE", pass_branch,
                    GREEN, GREEN_LIGHT, body_size=6.3, h=ph3, name="pass")
                box(4.4, y3, r3_w1, "FAIL → KILL CONDITION",
                    f"Stop; do not build: {fail_branch}", RED, RED_LIGHT,
                    body_size=6.3, h=ph3, name="fail")
                arrow(10.2, yu - title_zone, 10.6, y3 + ph3 + 0.18,
                      "from setup", GREEN)

        # R375-4: the provenance footer is WRAPPED to the canvas width —
        # the V2/V3 single-line footer was wider than the canvas and only
        # survived via bbox_inches='tight' cropping (aspect drift).
        footer_text = (
            "Schematic auto-derived from the canonical engineering build "
            "plan and verification record. No prototype exists and no "
            "experiment has been run (all verification results "
            "NOT_TESTED). Control variables: the canonical record does "
            "not enumerate held-constant variables separately — recorded "
            "critical parameters are shown verbatim.")
        footer_chars = max(20, int((FIG_W_IN - 0.4) / (6.3 * 0.0075)))
        footer_wrapped = "\n".join(
            textwrap.wrap(footer_text, width=footer_chars))
        ax.text(0.3, 0.24, footer_wrapped,
                ha="left", va="center", fontsize=6.3, color=GREY,
                style="italic")

        verify_text_geometry(
            fig, f"{pkg.pkg_id} experiment part {part_idx + 1}")
        _self_verify(layout_boxes, yu, f"{pkg.pkg_id} part {part_idx + 1}")
        fig.savefig(part_path, dpi=220, facecolor="white")
        plt.close(fig)
        paths.append(part_path)
    return paths


def build_experiment_diagram(pkg, headlines: dict, out_path: str,
                             spec: dict = None) -> list:
    """Backward-compatible name — R375-3 returns the LIST of part paths."""
    return build_experiment_diagrams(pkg, headlines, out_path, spec=spec)


def build_all(packages, headlines_by_pkg: dict, out_dir: str) -> dict:
    """Render experiment diagrams for all packages. Returns {pkg_id: [paths]}."""
    from premium_package_factory.r372.diagram_adequacy import (
        experiment_diagram_spec)
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for pkg in packages:
        h = headlines_by_pkg.get(pkg.pkg_id, {})
        spec = experiment_diagram_spec(pkg, h)
        fp = os.path.join(out_dir, f"{pkg.num}_experiment_setup.png")
        paths[pkg.pkg_id] = build_experiment_diagrams(pkg, h, fp, spec=spec)
    return paths

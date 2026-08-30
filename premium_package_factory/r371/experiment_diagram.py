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

FIG_W_IN, FIG_H_IN = 12.5, 7.6          # figsize (inches)
XU, YU = 13.0, 8.6                      # axes data extents

def _du_per_in_x() -> float:
    return XU / FIG_W_IN

def _du_per_in_y() -> float:
    return YU / FIG_H_IN

def _measure_height(body: str, w_du: float, body_size: float) -> float:
    """Height (data units) the wrapped body needs inside a box of width
    w_du: wrap to a character budget derived from the physical column
    width, then convert line count * leading to data units."""
    inner_in = max(0.2, (w_du * _du_per_in_x()) - 0.12)   # minus padding
    char_w_in = body_size * 0.0075                          # ~Helvetica avg
    chars_per_line = max(8, int(inner_in / char_w_in))
    lines = textwrap.wrap(str(body), width=chars_per_line) or [""]
    line_h_in = (body_size * 1.30) / 72.0
    return len(lines) * line_h_in * (1.0 / _du_per_in_y())

def _box_height(header: str, body: str, w_du: float, body_size: float,
                min_h: float = 1.05) -> float:
    """Total box height = header band + measured content + padding, never
    below min_h (a short box still looks like a box)."""
    content_h = _measure_height(body, w_du, body_size)
    header_h = 0.42
    return max(min_h, header_h + content_h + 0.22)


def build_experiment_diagram(pkg, headlines: dict, out_path: str,
                             spec: dict = None) -> str:
    """Render the decisive-experiment setup diagram for one package FROM
    the structured spec (built on demand if not supplied).

    V3: every box auto-sizes to its content (Directive 2). Row y-positions
    are computed from MEASURED heights, never hardcoded, so long
    MODELLED/UNKNOWN control-variable lists grow their box instead of
    spilling over neighbours."""
    if spec is None:
        from premium_package_factory.r372.diagram_adequacy import (
            experiment_diagram_spec)
        spec = experiment_diagram_spec(pkg, headlines)

    roles = spec["roles"]
    wp_id = spec.get("work_package", "WP-01")

    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN),
                           constrained_layout=True)
    ax.set_xlim(0, XU)
    ax.set_ylim(0, YU)
    ax.axis("off")

    ax.text(6.5, 8.3, f"Decisive Experiment Setup — {wp_id}",
            ha="center", va="center", fontsize=13.5, fontweight="bold", color=INK)
    ax.text(6.5, 7.95,
            f"{pkg.pkg_id} · {_clean(headlines.get('technology_name',''))[:80]}",
            ha="center", va="center", fontsize=8.5, color=GREY)

    def box(x, y_bottom, w, header, body, edge, face, body_size=7.0,
            h=None):
        """Auto-sized box anchored at its BOTTOM edge. Height is measured
        from content unless explicitly given (callers pass measured row
        heights so boxes in one row share the max)."""
        total_h = h if h is not None else _box_height(header, body, w,
                                                      body_size)
        ax.add_patch(FancyBboxPatch((x, y_bottom), w, total_h,
                     boxstyle="round,pad=0.06,rounding_size=0.12",
                     linewidth=1.3, edgecolor=edge, facecolor=face))
        ax.text(x + w / 2, y_bottom + total_h - 0.20, header,
                ha="center", va="center", fontsize=8.2,
                fontweight="bold", color=edge)
        inner_in = max(0.2, (w * _du_per_in_x()) - 0.12)
        char_w_in = body_size * 0.0075
        chars_per_line = max(8, int(inner_in / char_w_in))
        lines = textwrap.wrap(str(body), width=chars_per_line) or [""]
        line_h_du = (body_size * 1.30 / 72.0) * (1.0 / _du_per_in_y())
        text_y = y_bottom + total_h - 0.44 - (len(lines) - 1) * line_h_du / 2
        ax.text(x + w / 2, text_y, "\n".join(lines), ha="center",
                va="center", fontsize=body_size, color=INK,
                linespacing=1.30)
        return total_h

    def arrow(x1, y1, x2, y2, label="", color=INK, rad=0.0):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                     arrowstyle="-|>", mutation_scale=13, linewidth=1.2,
                     color=color,
                     connectionstyle=f"arc3,rad={rad}"))
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.16, label, ha="center",
                    va="center", fontsize=7.4, color=color, fontweight="bold")

    # ---- Row 3 (bottom-up layout: measure first, place later) -----------
    consequence = roles.get("decision_consequence", {}).get("content", "")
    pass_branch = consequence.split(". IF KILL")[0] if consequence else \
        "Proceed per canonical build plan"
    fail_branch = consequence.split("IF KILL CONDITION MET -> stop; "
                                    "do not build: ")[-1] if "IF KILL" in \
        consequence else roles["kill_condition"]["content"]
    r3_w1, r3_w2 = 3.6, 4.2
    h_pass = _box_height("PASS → CONSEQUENCE", pass_branch, r3_w2, 6.3)
    h_fail = _box_height("FAIL → KILL CONDITION",
                         f"Stop; do not build: {fail_branch}", r3_w1, 6.3)
    h3 = max(h_pass, h_fail, 1.35)
    y3 = 0.52

    # ---- Row 2: control variables -> measured outputs -> criterion ------
    r2_w1, r2_w2, r2_w3 = 3.6, 3.6, 4.2
    h_ctrl = _box_height("CONTROL VARIABLES",
                         roles["control_variables"]["content"], r2_w1, 6.4)
    h_meas = _box_height("MEASURED OUTPUTS",
                         roles["measured_outputs"]["content"], r2_w2, 7.0)
    h_crit = _box_height("DECISION CRITERION",
                         roles["decision_criterion"]["content"], r2_w3, 7.0)
    h2 = max(h_ctrl, h_meas, h_crit, 1.45)
    y2 = y3 + h3 + 0.55

    # ---- Row 1: test article -> stimulus -> instrumentation -------------
    r1_w1, r1_w2, r1_w3 = 3.6, 3.5, 4.1
    h_ta = _box_height("TEST ARTICLE", roles["test_article"]["content"],
                       r1_w1, 7.0)
    h_st = _box_height("STIMULUS", roles["stimulus"]["content"], r1_w2, 7.0)
    h_in = _box_height("INSTRUMENTATION",
                       roles["instrumentation"]["content"], r1_w3, 7.0)
    h1 = max(h_ta, h_st, h_in, 1.45)
    y1 = y2 + h2 + 0.55

    # ---- draw all boxes with the measured shared row heights ------------
    box(0.3, y1, r1_w1, "TEST ARTICLE", roles["test_article"]["content"],
        BRAND, BRAND_LIGHT, body_size=7.0, h=h1)
    box(4.3, y1, r1_w2, "STIMULUS", roles["stimulus"]["content"],
        BRAND, BRAND_LIGHT, body_size=7.0, h=h1)
    box(8.6, y1, r1_w3, "INSTRUMENTATION",
        roles["instrumentation"]["content"], BRAND, BRAND_LIGHT,
        body_size=7.0, h=h1)
    arrow(3.9, y1 + h1 / 2, 4.3, y1 + h1 / 2)
    arrow(7.8, y1 + h1 / 2, 8.6, y1 + h1 / 2)

    box(0.3, y2, r2_w1, "CONTROL VARIABLES",
        roles["control_variables"]["content"], GREY, "#f4f4f4",
        body_size=6.4, h=h2)
    box(4.4, y2, r2_w2, "MEASURED OUTPUTS",
        roles["measured_outputs"]["content"], BRAND, BRAND_LIGHT,
        body_size=7.0, h=h2)
    box(8.5, y2, r2_w3, "DECISION CRITERION",
        roles["decision_criterion"]["content"], GREEN, GREEN_LIGHT,
        body_size=7.0, h=h2)
    arrow(3.9, y1, 3.9, y2 + h2, rad=0.0)             # article under test
    arrow(3.9, y2 + h2 / 2, 4.4, y2 + h2 / 2)         # controls -> setup
    arrow(8.0, y2 + h2 / 2, 8.5, y2 + h2 / 2)         # measurement -> crit
    arrow(10.6, y1, 10.6, y2 + h2)                    # apparatus -> meas

    ax.text(2.1, y1 - 0.30,
            f"Planned effort: {spec.get('planned_effort', 'NOT_RECORDED')}",
            ha="center", va="center", fontsize=7.0, color=GREY,
            style="italic")

    box(8.5, y3, r3_w2, "PASS → CONSEQUENCE", pass_branch, GREEN,
        GREEN_LIGHT, body_size=6.3, h=h3)
    box(4.4, y3, r3_w1, "FAIL → KILL CONDITION",
        f"Stop; do not build: {fail_branch}", RED, RED_LIGHT,
        body_size=6.3, h=h3)
    arrow(10.2, y2, 10.6, y3 + h3 + 0.18, "PASS", GREEN)
    arrow(8.5, y2 + 0.35, 8.0, y3 + h3 + 0.18, "FAIL", RED, rad=0.18)

    # provenance footer
    ax.text(0.3, 0.24,
            "Schematic auto-derived from the canonical engineering build plan and "
            "verification record. No prototype exists and no experiment has been run "
            "(all verification results NOT_TESTED). Control variables: the canonical "
            "record does not enumerate held-constant variables separately — recorded "
            "critical parameters are shown verbatim.",
            ha="left", va="center", fontsize=6.3, color=GREY, style="italic")

    fig.savefig(out_path, dpi=220, facecolor="white")
    plt.close(fig)
    return out_path


def build_all(packages, headlines_by_pkg: dict, out_dir: str) -> dict:
    """Render experiment diagrams for all packages. Returns {pkg_id: path}."""
    from premium_package_factory.r372.diagram_adequacy import (
        experiment_diagram_spec)
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for pkg in packages:
        h = headlines_by_pkg.get(pkg.pkg_id, {})
        spec = experiment_diagram_spec(pkg, h)
        fp = os.path.join(out_dir, f"{pkg.num}_experiment_setup.png")
        build_experiment_diagram(pkg, h, fp, spec=spec)
        paths[pkg.pkg_id] = fp
    return paths

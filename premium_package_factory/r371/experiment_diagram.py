"""
experiment_diagram.py — R371 Phase 5, Visual 2: decisive-experiment /
verification-setup diagram, auto-derived from canonical engineering data.

Every label comes from the canonical engineering record:
  test article   <- build plan WP-01 .test_article
  apparatus      <- build plan WP-01 .equipment
  measurement    <- build plan WP-01 .measurement
  acceptance     <- verification V-001 .acceptance (or WP acceptance_criterion)
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


def build_experiment_diagram(pkg, headlines: dict, out_path: str) -> str:
    """Render the decisive-experiment setup diagram for one package."""
    bp = pkg.build_plan
    wp1 = bp[0] if bp else {}
    ver = pkg.verification[0] if pkg.verification else {}
    kill_if = _clean(headlines.get("kill_if", ""))

    test_article = _clean(wp1.get("test_article", "NOT_RECORDED"))
    equipment = _clean(wp1.get("equipment", "NOT_RECORDED"))
    measurement = _clean(wp1.get("measurement", "NOT_RECORDED"))
    acceptance = _clean(
        ver.get("acceptance") or wp1.get("acceptance_criterion") or "NOT_RECORDED"
    )
    duration = _clean(wp1.get("estimated_effort", "NOT_RECORDED"))
    wp_id = _clean(wp1.get("work_package", "WP-01"))

    fig, ax = plt.subplots(figsize=(11.5, 5.4), constrained_layout=True)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    # title
    ax.text(6, 5.72, f"Decisive Experiment Setup — {wp_id}",
            ha="center", va="center", fontsize=13.5, fontweight="bold", color=INK)
    ax.text(6, 5.38,
            f"{pkg.pkg_id} · {_clean(headlines.get('technology_name',''))[:70]}",
            ha="center", va="center", fontsize=8.5, color=GREY)

    def box(x, y, w, h, header, body, edge, face):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0.06,rounding_size=0.12",
                     linewidth=1.3, edgecolor=edge, facecolor=face))
        ax.text(x + w / 2, y + h - 0.26, header, ha="center", va="center",
                fontsize=8.6, fontweight="bold", color=edge)
        ax.text(x + w / 2, y + (h - 0.5) / 2, _wrap(body, 26), ha="center",
                va="center", fontsize=7.2, color=INK)

    def arrow(x1, y1, x2, y2, label="", color=INK, style="-|>", rad=0.0):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                     arrowstyle=style, mutation_scale=13, linewidth=1.2,
                     color=color,
                     connectionstyle=f"arc3,rad={rad}"))
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.16, label, ha="center",
                    va="center", fontsize=7.4, color=color, fontweight="bold")

    # main chain: test article -> apparatus -> measurement -> acceptance
    bw, bh = 2.55, 1.9
    y0 = 3.0
    box(0.35, y0, bw, bh, "TEST ARTICLE", test_article, BRAND, BRAND_LIGHT)
    box(3.35, y0, bw, bh, "APPARATUS", equipment, BRAND, BRAND_LIGHT)
    box(6.35, y0, bw, bh, "MEASURED QUANTITY", measurement, BRAND, BRAND_LIGHT)
    box(9.35, y0, 2.35, bh, "ACCEPTANCE GATE", acceptance, GREEN, GREEN_LIGHT)

    arrow(2.9, y0 + bh / 2, 3.35, y0 + bh / 2)
    arrow(5.9, y0 + bh / 2, 6.35, y0 + bh / 2)
    arrow(8.9, y0 + bh / 2, 9.35, y0 + bh / 2)

    # duration band under main chain
    ax.text(1.62, y0 - 0.34, f"Planned effort: {duration}", ha="center",
            va="center", fontsize=7.0, color=GREY, style="italic")

    # outcome branches from acceptance gate
    box(9.35, 0.55, 2.35, 1.35, "PASS → ADVANCE",
        "Proceed to next work package in the canonical build plan",
        GREEN, GREEN_LIGHT)
    box(5.6, 0.55, 3.2, 1.35, "FAIL → KILL CONDITION",
        kill_if, RED, RED_LIGHT)
    arrow(10.5, y0, 10.5, 1.9, "PASS", GREEN)
    arrow(9.35, y0 + 0.35, 8.8, 1.9, "FAIL", RED, rad=0.18)

    # provenance footer
    ax.text(0.35, 0.18,
            "Schematic auto-derived from the canonical engineering build plan and "
            "verification record. No prototype exists and no experiment has been run "
            "(all verification results NOT_TESTED).",
            ha="left", va="center", fontsize=6.6, color=GREY, style="italic")

    fig.savefig(out_path, dpi=220, facecolor="white")
    plt.close(fig)
    return out_path


def build_all(packages, headlines_by_pkg: dict, out_dir: str) -> dict:
    """Render experiment diagrams for all packages. Returns {pkg_id: path}."""
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for pkg in packages:
        h = headlines_by_pkg.get(pkg.pkg_id, {})
        fp = os.path.join(out_dir, f"{pkg.num}_experiment_setup.png")
        build_experiment_diagram(pkg, h, fp)
        paths[pkg.pkg_id] = fp
    return paths

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


def build_experiment_diagram(pkg, headlines: dict, out_path: str,
                             spec: dict = None) -> str:
    """Render the decisive-experiment setup diagram for one package FROM
    the structured spec (built on demand if not supplied)."""
    if spec is None:
        from premium_package_factory.r372.diagram_adequacy import (
            experiment_diagram_spec)
        spec = experiment_diagram_spec(pkg, headlines)

    roles = spec["roles"]
    wp_id = spec.get("work_package", "WP-01")

    fig, ax = plt.subplots(figsize=(12.5, 7.6), constrained_layout=True)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8.6)
    ax.axis("off")

    # title
    ax.text(6.5, 8.3, f"Decisive Experiment Setup — {wp_id}",
            ha="center", va="center", fontsize=13.5, fontweight="bold", color=INK)
    ax.text(6.5, 7.95,
            f"{pkg.pkg_id} · {_clean(headlines.get('technology_name',''))[:80]}",
            ha="center", va="center", fontsize=8.5, color=GREY)

    def box(x, y, w, h, header, body, edge, face, body_size=7.0):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0.06,rounding_size=0.12",
                     linewidth=1.3, edgecolor=edge, facecolor=face))
        ax.text(x + w / 2, y + h - 0.26, header, ha="center", va="center",
                fontsize=8.4, fontweight="bold", color=edge)
        ax.text(x + w / 2, y + (h - 0.5) / 2, _wrap(body, 30), ha="center",
                va="center", fontsize=body_size, color=INK)

    def arrow(x1, y1, x2, y2, label="", color=INK, rad=0.0):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                     arrowstyle="-|>", mutation_scale=13, linewidth=1.2,
                     color=color,
                     connectionstyle=f"arc3,rad={rad}"))
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.16, label, ha="center",
                    va="center", fontsize=7.4, color=color, fontweight="bold")

    # Row 1: test article -> stimulus -> instrumentation
    bw, bh = 3.6, 1.75
    y1 = 5.6
    box(0.3, y1, bw, bh, "TEST ARTICLE", roles["test_article"]["content"],
        BRAND, BRAND_LIGHT)
    box(4.3, y1, 3.5, bh, "STIMULUS", roles["stimulus"]["content"],
        BRAND, BRAND_LIGHT)
    box(8.6, y1, 4.1, bh, "INSTRUMENTATION",
        roles["instrumentation"]["content"], BRAND, BRAND_LIGHT)
    arrow(3.9, y1 + bh / 2, 4.3, y1 + bh / 2)
    arrow(7.8, y1 + bh / 2, 8.6, y1 + bh / 2)

    # Row 2: control variables -> measured outputs -> decision criterion
    bw2, bh2 = 3.6, 1.75
    y2 = 3.3
    box(0.3, y2, bw2, bh2, "CONTROL VARIABLES",
        roles["control_variables"]["content"], GREY, "#f4f4f4", body_size=6.4)
    box(4.4, y2, bw2, bh2, "MEASURED OUTPUTS",
        roles["measured_outputs"]["content"], BRAND, BRAND_LIGHT)
    box(8.5, y2, 4.2, bh2, "DECISION CRITERION",
        roles["decision_criterion"]["content"], GREEN, GREEN_LIGHT)
    arrow(3.9, y1, 3.9, y2 + bh2, rad=0.0)          # article under test
    arrow(3.9, y2 + bh2 / 2, 4.4, y2 + bh2 / 2)      # controls -> setup
    arrow(8.0, y2 + bh2 / 2, 8.5, y2 + bh2 / 2)      # measurement -> criterion
    arrow(10.6, y1, 10.6, y2 + bh2)                   # apparatus -> measurement

    # duration band
    ax.text(2.1, y1 - 0.32,
            f"Planned effort: {spec.get('planned_effort', 'NOT_RECORDED')}",
            ha="center", va="center", fontsize=7.0, color=GREY, style="italic")

    # outcome branches from decision criterion — R373-2: the consequence is
    # the canonical decision_consequence role (pass branch from the build
    # plan deliverable/sequence; fail branch = kill condition).
    consequence = roles.get("decision_consequence", {}).get("content", "")
    pass_branch = consequence.split(". IF KILL")[0] if consequence else \
        "Proceed per canonical build plan"
    fail_branch = consequence.split("IF KILL CONDITION MET -> stop; "
                                    "do not build: ")[-1] if "IF KILL" in \
        consequence else roles["kill_condition"]["content"]
    box(8.5, 0.55, 4.2, 1.7, "PASS → CONSEQUENCE",
        pass_branch, GREEN, GREEN_LIGHT, body_size=6.3)
    box(4.4, 0.55, 3.6, 1.7, "FAIL → KILL CONDITION",
        f"Stop; do not build: {fail_branch}", RED, RED_LIGHT, body_size=6.3)
    arrow(10.2, y2, 10.6, 2.3, "PASS", GREEN)
    arrow(8.5, y2 + 0.35, 8.0, 2.3, "FAIL", RED, rad=0.18)

    # provenance footer
    ax.text(0.3, 0.28,
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

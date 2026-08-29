"""
diagram_factory.py — Generate 15 unique technical diagrams

Each diagram is generated from the canonical mechanism description.
No decorative stock imagery. Diagram-first communication.

Diagram kinds (one per package, chosen from mechanism type):
  system_architecture  — block diagram of system components
  mechanism_diagram    — physical/chemical mechanism flow
  flow_diagram         — process or data flow
  device_cross_section — physical device geometry
  control_loop         — feedback control architecture
  energy_flow          — energy harvest → conditioning → load
  sensor_architecture  — sensor + signal processing chain
  data_pipeline        — ML/data pipeline
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle, Ellipse, Polygon, ConnectionPatch
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import numpy as np

# Register fonts for matplotlib
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

# ----------------------------------------------------------------------------
# Palette (mirror design_system.py)
# ----------------------------------------------------------------------------

INK_900 = "#0F172A"
INK_700 = "#334155"
INK_500 = "#64748B"
INK_300 = "#CBD5E1"
INK_100 = "#F1F5F9"

BRAND_900 = "#0F2A4D"
BRAND_700 = "#1E3A5F"
BRAND_500 = "#2E5C8A"
BRAND_300 = "#7BA7CC"
BRAND_100 = "#E3EDF5"

ACCENT = "#B8860B"
ACCENT_LIGHT = "#F4E4BC"

# Evidence colors
EV_PHYSICAL = "#1B5E20"
EV_EXTERNAL = "#2E7D32"
EV_COMPUTATIONAL = "#1565C0"
EV_MODEL = "#F57F17"
EV_ASSUMED = "#6A1B9A"
EV_UNKNOWN = "#424242"
EV_KILLED = "#B71C1C"
EV_KILLED_BG = "#FFEBEE"
EV_PHYSICAL_BG = "#E8F5E9"
EV_EXTERNAL_BG = "#E8F5E9"
EV_COMPUTATIONAL_BG = "#E3F2FD"
EV_MODEL_BG = "#FFF8E1"
EV_ASSUMED_BG = "#F3E5F5"
EV_UNKNOWN_BG = "#ECEFF1"

OUTPUT_DIR = "/home/z/my-project/premium_package_factory/output/_diagrams"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ----------------------------------------------------------------------------
# Drawing primitives
# ----------------------------------------------------------------------------

def _setup_axes(figsize=(9, 6), xlim=(0, 10), ylim=(0, 6)):
    """Create a clean axes with no spines/ticks for diagram drawing."""
    fig, ax = plt.subplots(figsize=figsize, dpi=180)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor('white')
    return fig, ax


def _block(ax, x, y, w, h, label, sublabel=None, color=BRAND_500, bg=BRAND_100,
           label_color="white", sublabel_color=INK_700, fontsize=9, sublabel_size=7.5,
           radius=0.08, lw=0.8):
    """Draw a labeled rounded rectangle block."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        facecolor=color, edgecolor=color, linewidth=lw, alpha=0.95
    )
    ax.add_patch(box)
    # Inner background for label area
    if bg != color:
        inner = FancyBboxPatch(
            (x + 0.04, y + 0.04), w - 0.08, h - 0.08,
            boxstyle=f"round,pad=0.01,rounding_size={max(0.04, radius - 0.02)}",
            facecolor=bg, edgecolor='none', alpha=0.95
        )
        ax.add_patch(inner)

    txt_color = label_color if color != bg else INK_900
    if sublabel:
        ax.text(x + w / 2, y + h * 0.62, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color=txt_color)
        ax.text(x + w / 2, y + h * 0.28, sublabel, ha='center', va='center',
                fontsize=sublabel_size, color=sublabel_color, style='italic')
    else:
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color=txt_color)


def _arrow(ax, x1, y1, x2, y2, label=None, color=INK_700, lw=1.2,
           label_offset=(0, 0.18), label_color=INK_700, label_size=7.5,
           arrowstyle="->", curve=0.0):
    """Draw an arrow between two points with optional label."""
    if curve:
        connectionstyle = f"arc3,rad={curve}"
    else:
        connectionstyle = "arc3,rad=0"
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=arrowstyle, mutation_scale=12,
        color=color, linewidth=lw, connectionstyle=connectionstyle
    )
    ax.add_patch(arrow)
    if label:
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=label_size, color=label_color, style='italic',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white',
                          edgecolor='none', alpha=0.92))


def _title(ax, text, subtitle=None, y=5.7):
    """Add a diagram title."""
    ax.text(5, y, text, ha='center', va='center',
            fontsize=11, fontweight='bold', color=INK_900)
    if subtitle:
        ax.text(5, y - 0.35, subtitle, ha='center', va='center',
                fontsize=8.5, color=INK_500, style='italic')


def _save(fig, name):
    """Save figure to output dir and return path."""
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    fig.savefig(path, dpi=180, bbox_inches='tight', facecolor='white',
                pad_inches=0.15)
    plt.close(fig)
    return path


# ----------------------------------------------------------------------------
# Per-package diagram generators
# ----------------------------------------------------------------------------

def diagram_P01(name="P-01"):
    """P-01 Rate-Limited Conductance Control — system architecture.
    Multi-segment catheter with Bayesian predictor + controller.
    """
    fig, ax = _setup_axes(figsize=(9, 6.2), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-01 Multi-Segment CSF Shunt",
           "Multi-segment catheter + Bayesian occlusion predictor + alpha controller",
           y=6.7)

    # CSF source
    _block(ax, 0.4, 4.5, 1.6, 1.0, "CSF Production", sublabel="Q_prod",
           color=BRAND_700, bg=BRAND_100, label_color="white")

    # Ventricles
    _block(ax, 2.6, 4.5, 1.4, 1.0, "Ventricles", sublabel="P_ICP",
           color=BRAND_500, bg=BRAND_100, label_color="white")

    # 4 segments
    seg_y = [3.0, 2.0, 1.0, 0.0]
    seg_labels = ["Segment 1", "Segment 2", "Segment 3", "Segment 4"]
    for i, (y, lab) in enumerate(zip(seg_y, seg_labels)):
        _block(ax, 4.6, y, 1.6, 0.8, lab, sublabel=f"alpha_{i+1}",
               color=BRAND_500, bg="white", label_color=BRAND_700,
               sublabel_color=INK_500, fontsize=8.5)
        _arrow(ax, 4.0, 5.0, 4.6, y + 0.4, color=INK_700, lw=1.0,
               label=f"alpha_{i+1}", label_size=6.5, label_offset=(-0.3, 0))
        # Flow sensor
        _block(ax, 6.6, y, 1.4, 0.8, f"Flow Sensor {i+1}", sublabel=f"F_{i+1}",
               color=INK_500, bg=INK_100, label_color="white",
               sublabel_color=INK_700, fontsize=8)
        _arrow(ax, 6.2, y + 0.4, 6.6, y + 0.4, color=INK_700, lw=1.0)
        # Drainage
        _arrow(ax, 8.0, y + 0.4, 9.4, y + 0.4, color=INK_700, lw=1.0,
               label="drainage", label_size=6.5, label_offset=(0, 0.18))

    # Drainage outlet label
    ax.text(9.7, 1.8, "Distal\nDrainage", ha='left', va='center',
            fontsize=8, color=INK_500, style='italic')

    # Bayesian predictor block (above the segments)
    _block(ax, 6.6, 5.6, 2.4, 1.0, "Bayesian Predictor",
           sublabel="P(occlude_i | F_obs)",
           color=BRAND_900, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9)
    # Arrows from flow sensors to predictor
    for y in seg_y:
        _arrow(ax, 7.3, y + 0.8, 7.3, 5.6, color=EV_COMPUTATIONAL, lw=0.8,
               arrowstyle="-", label_offset=(0.5, 0))

    # Controller
    _block(ax, 4.4, 5.6, 1.8, 1.0, "Alpha Controller",
           sublabel="INV-1: P_ICP<=20\nINV-2: F_i<=F_MAX",
           color=BRAND_900, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=6.5)
    _arrow(ax, 6.6, 6.1, 6.4, 6.1, color=INK_700, lw=1.0, label="P(occlude)",
           label_size=7, label_offset=(0, 0.2))
    # Controller back to ventricles (alpha update)
    _arrow(ax, 5.3, 5.6, 3.3, 5.5, color=ACCENT, lw=1.4,
           label="alpha update", label_size=7, label_offset=(0, 0.25),
           curve=-0.15)

    # Honest state callout
    ax.text(0.4, 0.2,
            "Honest state: T2-CONDITIONAL (svMultiPhysics verified 1D model within 16%). Strict dual-invariant FALSIFIED → graceful degradation.",
            fontsize=7, color=INK_500, style='italic')

    return _save(fig, name)


def diagram_P02(name="P-02"):
    """P-02 Adaptive Valve Profile — control loop."""
    fig, ax = _setup_axes(figsize=(9, 5.5), xlim=(0, 11), ylim=(0, 6.5))

    _title(ax, "P-02 Adaptive Valve Profile",
           "Feedback loop: ICP sensor → trend extractor → adaptive profile → valve",
           y=6.0)

    # ICP sensor
    _block(ax, 0.4, 3.5, 1.8, 1.0, "ICP Sensor", sublabel="(existing, implanted)",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)

    # Trend extractor
    _block(ax, 3.0, 3.5, 1.8, 1.0, "Trend Extractor", sublabel="dP/dt + postural",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 2.2, 4.0, 3.0, 4.0, color=INK_700, lw=1.2, label="P_ICP(t)",
           label_size=7.5, label_offset=(0, 0.2))

    # Adaptive profile generator
    _block(ax, 5.6, 3.5, 2.0, 1.0, "Adaptive Profile", sublabel="opening profile\n(k_p, k_d)",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 4.8, 4.0, 5.6, 4.0, color=INK_700, lw=1.2, label="trends",
           label_size=7.5, label_offset=(0, 0.2))

    # Valve actuator
    _block(ax, 8.4, 3.5, 1.8, 1.0, "Valve Actuator", sublabel="(programmable valve)",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 7.6, 4.0, 8.4, 4.0, color=INK_700, lw=1.2, label="opening profile",
           label_size=7.5, label_offset=(0, 0.2))

    # Patient postural state (input)
    _block(ax, 3.0, 1.0, 1.8, 0.9, "Postural State", sublabel="(accelerometer)",
           color=INK_500, bg=INK_100, label_color="white",
           sublabel_color=INK_700, fontsize=8.5, sublabel_size=7)
    _arrow(ax, 3.9, 1.9, 3.9, 3.5, color=INK_700, lw=1.0, label="context",
           label_size=7, label_offset=(0.3, 0))

    # Feedback loop (valve actuator back to ICP sensor via drainage modulates P_ICP)
    _arrow(ax, 9.3, 3.5, 9.3, 1.5, color=ACCENT, lw=1.4)
    _arrow(ax, 9.3, 1.5, 1.3, 1.5, color=ACCENT, lw=1.4)
    _arrow(ax, 1.3, 1.5, 1.3, 3.5, color=ACCENT, lw=1.4,
           label="drainage modulates P_ICP", label_size=7.5,
           label_offset=(0, -0.2))

    ax.text(0.4, 0.4,
            "Honest state: T1 MODEL_PREDICTED (47.3% ICP excursion reduction, not physically measured).\n"
            "Critical parameters (recorded, UNKNOWN): P_crack · A_max · tau_valve",
            fontsize=7, color=INK_500, style='italic')

    return _save(fig, name)


def diagram_P04(name="P-04"):
    """P-04 Catalytic Contact-Time Lock — mechanism diagram."""
    fig, ax = _setup_axes(figsize=(9, 5.8), xlim=(0, 11), ylim=(0, 6.5))

    _title(ax, "P-04 Catalytic Contact-Time Lock",
           "NEP enzyme on catheter wall clears Aβ42 via mass-transport-limited contact",
           y=6.0)

    # CSF inflow
    _block(ax, 0.3, 3.5, 1.6, 1.0, "CSF Inflow", sublabel="Aβ42 substrate",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)

    # Catheter (long horizontal block with wall)
    cath = FancyBboxPatch((2.4, 3.2), 6.5, 1.6,
                           boxstyle="round,pad=0.02,rounding_size=0.05",
                           facecolor='white', edgecolor=BRAND_700, linewidth=1.5)
    ax.add_patch(cath)
    ax.text(5.65, 4.95, "Catheter body (substrate) + NEP-immobilized coating",
            ha='center', va='center',
            fontsize=7, color=BRAND_700, fontweight='bold')
    ax.text(5.65, 3.0, "inner lumen (Contact-time control geometry)", ha='center', va='center',
            fontsize=7.5, color=INK_500, style='italic')

    # NEP enzymes on wall (small circles)
    for i, x in enumerate(np.linspace(2.8, 8.5, 6)):
        circ = Circle((x, 4.7), 0.18, facecolor=EV_PHYSICAL,
                      edgecolor=INK_900, linewidth=0.5, zorder=5)
        ax.add_patch(circ)
        ax.text(x, 4.7, "NEP", ha='center', va='center',
                fontsize=5.5, color='white', fontweight='bold', zorder=6)

    # Aβ42 molecules flowing through lumen (small diamonds)
    for i, (x, y) in enumerate([(3.2, 3.9), (4.0, 3.7), (4.8, 4.0), (5.6, 3.7),
                                 (6.4, 4.0), (7.2, 3.7), (8.0, 3.9)]):
        diag = Polygon([(x, y+0.12), (x+0.12, y), (x, y-0.12), (x-0.12, y)],
                       facecolor=EV_MODEL, edgecolor=INK_900, linewidth=0.4, zorder=4)
        ax.add_patch(diag)
    ax.text(5.65, 3.3, "Aβ42 substrate", ha='center', va='center',
            fontsize=7, color=EV_MODEL, style='italic')

    # Arrows showing flow + cleavage
    _arrow(ax, 1.9, 4.0, 2.4, 4.0, color=INK_700, lw=1.2)
    _arrow(ax, 8.9, 4.0, 9.6, 4.0, color=INK_700, lw=1.2,
           label="cleared peptides", label_size=7, label_offset=(0, 0.25))

    # Cleavage arrows (enzyme to substrate)
    for x in [3.5, 5.0, 6.5, 8.0]:
        _arrow(ax, x, 4.55, x, 4.15, color=EV_PHYSICAL, lw=0.6,
               arrowstyle="->", label_offset=(0, 0))

    # Outflow
    _block(ax, 9.6, 3.5, 1.2, 1.0, "Outflow", sublabel="cleared peptides",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=8.5, sublabel_size=7)

    # Bottom annotations (recorded unknowns — R370Q export)
    ax.text(0.3, 1.8, "UNKNOWN (critical parameters):", fontsize=8.5,
            color=BRAND_700, fontweight='bold')
    ax.text(0.3, 1.4, "• Enzyme surface density Gamma • Catheter length L\n• Lumen diameter d • Contact time tau",
            fontsize=7.5, color=INK_700)

    ax.text(5.7, 1.8, "UNKNOWN (enzyme):", fontsize=8.5,
            color=ACCENT, fontweight='bold')
    ax.text(5.7, 1.4, "• Enzyme half-life in CSF environment • Immunogenicity of immobilized NEP\n• Substrate competition magnitude • In vivo clearance per pass",
            fontsize=7.5, color=INK_700)

    ax.text(0.3, 0.4,
            "Honest state: T1 MODEL_PREDICTED (100% clearance model). Biology blocked — decisive experiment can resolve enzyme stability question.",
            fontsize=7, color=INK_500, style='italic')

    return _save(fig, name)


def diagram_P07(name="P-07"):
    """P-07 Drainage Priority Clearance — device cross-section."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-07 Passive Drainage Priority Safety Floor",
           "Passive mechanical bypass maintains drainage when primary path obstructs",
           y=6.5)

    # Catheter main lumen (large horizontal rounded rectangle)
    main_lumen = FancyBboxPatch((1.0, 3.5), 8.5, 1.5,
                                 boxstyle="round,pad=0.02,rounding_size=0.1",
                                 facecolor=BRAND_100, edgecolor=BRAND_700, linewidth=1.5)
    ax.add_patch(main_lumen)
    ax.text(5.25, 5.2, "Catheter Main Lumen", ha='center', va='center',
            fontsize=9, color=BRAND_700, fontweight='bold')

    # CSF inflow arrow
    _arrow(ax, 0.2, 4.25, 1.0, 4.25, color=INK_700, lw=1.4,
           label="CSF", label_size=8, label_offset=(0, 0.25))

    # Primary drainage path (top, normal flow)
    _arrow(ax, 9.5, 4.6, 10.5, 4.6, color=BRAND_500, lw=1.4,
           label="primary", label_size=7.5, label_offset=(0, 0.25))

    # Obstruction site (red blob on primary path)
    obstruct = Ellipse((8.7, 4.6), 0.6, 0.4, facecolor=EV_KILLED,
                       edgecolor=INK_900, linewidth=0.8, alpha=0.85, zorder=5)
    ax.add_patch(obstruct)
    ax.text(8.7, 4.6, "70%\nobstr", ha='center', va='center',
            fontsize=6, color='white', fontweight='bold', zorder=6)
    ax.text(8.7, 5.2, "Obstruction", ha='center', va='center',
            fontsize=7, color=EV_KILLED, fontweight='bold')

    # Passive floor bypass (bottom)
    bypass = FancyBboxPatch((3.0, 1.8), 5.5, 0.7,
                             boxstyle="round,pad=0.02,rounding_size=0.05",
                             facecolor=EV_PHYSICAL_BG, edgecolor=EV_PHYSICAL, linewidth=1.5)
    ax.add_patch(bypass)
    ax.text(5.75, 2.15, "Passive Floor Bypass Channel", ha='center', va='center',
            fontsize=8, color=EV_PHYSICAL, fontweight='bold')

    # Pressure-triggered arrow from lumen to bypass
    _arrow(ax, 5.75, 3.5, 5.75, 2.5, color=EV_PHYSICAL, lw=1.4,
           label="pressure-activated", label_size=7, label_offset=(1.0, 0))

    # Bypass to drainage outlet
    _arrow(ax, 8.5, 2.15, 10.5, 2.15, color=EV_PHYSICAL, lw=1.4,
           label="fail-safe Q_min ~0.05 mL/min", label_size=7, label_offset=(0, 0.25))

    # Drainage outlet
    _block(ax, 10.5, 3.7, 0.5, 1.8, "Outlet", color=INK_500, bg=INK_100,
           label_color="white", fontsize=8)

    # Annotation: P-03 failure mode
    ax.text(0.4, 1.2,
            "P-03 (related) FALSIFIED: floor 0.001 mL/min/mmHg.\n"
            "P-07 redesign: pressure-threshold-activated floor (semi-active), larger bypass channel.",
            fontsize=7.5, color=INK_700, style='italic',
            bbox=dict(boxstyle="round,pad=0.3", facecolor=INK_100,
                      edgecolor=INK_300, linewidth=0.5))

    return _save(fig, name)


def diagram_P11(name="P-11"):
    """P-11 Phage Anti-Biofilm — mechanism diagram."""
    fig, ax = _setup_axes(figsize=(9, 5.8), xlim=(0, 11), ylim=(0, 6.5))

    _title(ax, "P-11 Phage Anti-Biofilm",
           "S. aureus phage K immobilized on electrospun Ti-coated catheter surface",
           y=6.0)

    # Ti-coated catheter surface (bottom horizontal block)
    ti = FancyBboxPatch((0.5, 1.5), 9.5, 0.5,
                         boxstyle="round,pad=0.02,rounding_size=0.05",
                         facecolor=INK_500, edgecolor=INK_900, linewidth=1.0)
    ax.add_patch(ti)
    ax.text(5.25, 1.75, "Electrospun titanium coating (Catheter body substrate)", ha='center', va='center',
            fontsize=7.5, color='white', fontweight='bold')

    # Electrospun nanofiber matrix (above Ti)
    nanofiber = FancyBboxPatch((0.5, 2.2), 9.5, 0.4,
                                boxstyle="round,pad=0.02,rounding_size=0.05",
                                facecolor=BRAND_300, edgecolor=BRAND_700, linewidth=1.0,
                                alpha=0.7)
    ax.add_patch(nanofiber)
    ax.text(5.25, 2.4, "Electrospun Nanofiber Matrix", ha='center', va='center',
            fontsize=7.5, color=BRAND_900, fontweight='bold')

    # Phage K particles (multiple, on nanofiber)
    for i, x in enumerate(np.linspace(1.2, 9.8, 8)):
        # Phage = head (circle) + tail (line)
        head = Circle((x, 3.2), 0.18, facecolor=EV_PHYSICAL,
                      edgecolor=INK_900, linewidth=0.5, zorder=5)
        ax.add_patch(head)
        ax.plot([x, x], [3.05, 2.65], color=INK_900, linewidth=1.0, zorder=5)
    ax.text(0.4, 3.2, "Phage K", ha='right', va='center',
            fontsize=8, color=EV_PHYSICAL, fontweight='bold')

    # S. aureus bacteria (ovals, attacking from above)
    for i, (x, y) in enumerate([(2.0, 5.0), (3.5, 5.3), (5.0, 5.0), (6.5, 5.3),
                                 (8.0, 5.0), (9.5, 5.3)]):
        bact = Ellipse((x, y), 0.45, 0.30, facecolor=EV_KILLED,
                       edgecolor=INK_900, linewidth=0.5, alpha=0.9, zorder=4)
        ax.add_patch(bact)
    ax.text(5.25, 5.7, "Bacterial challenge load (S. aureus, CFU/mL)", ha='center',
            va='center', fontsize=8, color=EV_KILLED, fontweight='bold')

    # Lysis arrows (bacteria → phage)
    for x in [2.0, 3.5, 5.0, 6.5, 8.0, 9.5]:
        _arrow(ax, x, 4.85, x, 3.45, color=EV_PHYSICAL, lw=0.8,
               arrowstyle="->", label_offset=(0, 0))

    # Biofilm matrix (inhibited — grayed out)
    biofilm = FancyBboxPatch((0.5, 3.7), 9.5, 0.3,
                              boxstyle="round,pad=0.02,rounding_size=0.05",
                              facecolor='none', edgecolor=INK_300,
                              linewidth=1.0, linestyle='--', alpha=0.5)
    ax.add_patch(biofilm)
    ax.text(5.25, 3.85, "Biofilm Matrix (INHIBITED — log reduction >= 3 / 99.9% at 24h)",
            ha='center', va='center', fontsize=7, color=INK_500, style='italic')

    ax.text(0.4, 0.4,
            "Honest state: T1 MODEL_PREDICTED. Decisive experiment: 7-day S. aureus biofilm assay with phage-coated vs uncoated Ti.\n"
            "Kinetic parameters (recorded): k_ads (phage-bacteria adsorption rate) · k_decay (phage decay rate)",
            fontsize=7, color=INK_500, style='italic')

    return _save(fig, name)


def diagram_P13(name="P-13"):
    """P-13 Neuromorphic Predictor — data pipeline."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-13 Neuromorphic Predictor",
           "ML pipeline: ICP+flow sensor streams → features → predictor → clinical alert",
           y=6.5)

    # Two sensor streams
    _block(ax, 0.3, 4.5, 1.6, 1.0, "ICP Sensor", sublabel="P_ICP(t)",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _block(ax, 0.3, 2.5, 1.6, 1.0, "Flow Sensor", sublabel="F(t)",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)

    # Feature extractor
    _block(ax, 2.6, 3.5, 1.8, 1.6, "Feature Extractor",
           sublabel="Rolling window\n24h features",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 1.9, 5.0, 2.6, 4.5, color=INK_700, lw=1.0)
    _arrow(ax, 1.9, 3.0, 2.6, 3.5, color=INK_700, lw=1.0)

    # ML predictor
    _block(ax, 5.0, 3.5, 2.0, 1.6, "ML Predictor",
           sublabel="Gradient boosting\n(0 prior-art hits)",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 4.4, 4.3, 5.0, 4.3, color=INK_700, lw=1.2, label="features",
           label_size=7.5, label_offset=(0, 0.2))

    # Threshold classifier
    _block(ax, 7.6, 3.5, 1.6, 1.6, "Classifier", sublabel="P > 0.7\n→ alert",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 7.0, 4.3, 7.6, 4.3, color=INK_700, lw=1.2, label="P(fail)",
           label_size=7.5, label_offset=(0, 0.2))

    # Clinical alert
    _block(ax, 9.6, 3.5, 1.2, 1.6, "Clinical Alert",
           sublabel="24h lead",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7)
    _arrow(ax, 9.2, 4.3, 9.6, 4.3, color=ACCENT, lw=1.4)

    # Power dependency note
    _block(ax, 0.3, 0.5, 4.5, 1.4, "POWER DEPENDENCY",
           sublabel="P-13 conditional on P-15-R1 / P-16 energy source.\n"
                    "If both fail, P-13 has no power source.",
           color=EV_KILLED, bg=EV_KILLED_BG, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7.5)

    # Data dependency note
    _block(ax, 5.5, 0.5, 5.3, 1.4, "DATA DEPENDENCY",
           sublabel="AUC + lead time MODELLED, not measured.\n"
                    "Decisive experiment: 100+ patient-years retrospective.",
           color=EV_MODEL, bg=EV_MODEL_BG, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7.5)

    # Recorded parameters
    ax.text(0.3, 1.4, "Recorded parameters: Sensor sampling rate ~1-10 Hz (MODELLED) · Prediction horizon target (hours to days)",
            fontsize=7, color=INK_500, style='italic')

    return _save(fig, name)


def diagram_P15R1(name="P-15-R1"):
    """P-15-R1 Self-Powered Sensing — energy flow (R1 repair)."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-15-R1 Self-Powered Sensing (R1 Repair)",
           "Extracardiac harvesting: CSF pulsation + neck motion → piezo → cap → duty-cycled sensor",
           y=6.5)

    # Two energy sources
    _block(ax, 0.3, 4.5, 1.8, 1.0, "CSF Pulsation", sublabel="mechanical",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)
    _block(ax, 0.3, 2.5, 1.8, 1.0, "Neck Motion", sublabel="mechanical",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)

    # Piezoelectric harvester
    _block(ax, 2.7, 3.5, 1.8, 1.6, "Piezo Harvester",
           sublabel="target >=5 μW\n(R1 repair)",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 2.1, 5.0, 2.7, 4.5, color=INK_700, lw=1.0, label="coupling",
           label_size=7, label_offset=(-0.3, 0.1))
    _arrow(ax, 2.1, 3.0, 2.7, 3.5, color=INK_700, lw=1.0)

    # Power conditioning
    _block(ax, 5.0, 3.5, 1.6, 1.6, "Power Cond.", sublabel="regulator",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 4.5, 4.3, 5.0, 4.3, color=INK_700, lw=1.2, label="electrical",
           label_size=7, label_offset=(0, 0.2))

    # Capacitor
    _block(ax, 7.0, 3.5, 1.4, 1.6, "100μF Cap", sublabel="storage",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 6.6, 4.3, 7.0, 4.3, color=INK_700, lw=1.2)

    # Duty-cycled sensor
    _block(ax, 8.7, 4.5, 1.4, 1.0, "Sensor", sublabel="1% duty",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 8.4, 4.8, 8.7, 4.8, color=INK_700, lw=1.0)

    # Wireless transmitter
    _block(ax, 8.7, 2.5, 1.4, 1.0, "TX", sublabel="every 100s",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 9.4, 4.5, 9.4, 3.5, color=ACCENT, lw=1.2, label="sample",
           label_size=7, label_offset=(0.4, 0))

    # P-15 original failure callout (red boundary)
    fail = FancyBboxPatch((0.3, 0.4), 10.4, 1.3,
                          boxstyle="round,pad=0.02,rounding_size=0.05",
                          facecolor=EV_KILLED_BG, edgecolor=EV_KILLED,
                          linewidth=1.0)
    ax.add_patch(fail)
    ax.text(0.5, 1.4, "P-15 ORIGINAL FAILURE:", fontsize=8, color=EV_KILLED,
            fontweight='bold')
    ax.text(0.5, 0.9,
            "Cardiac motion harvesting failed in shunt geometry (10 μW P50 not achievable).\n"
            "R1 REPAIR: extracardiac harvesting (CSF pulsation + neck motion) — modelled, NOT yet measured.",
            fontsize=7.5, color=INK_700)

    return _save(fig, name)


def diagram_P16(name="P-16"):
    """P-16 940nm Optical Power Delivery — system architecture."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-16 940nm Optical Power Delivery",
           "External 940nm LED → scalp/skull tissue → implanted GaAs PV → power conditioning → load",
           y=6.5)

    # External LED
    _block(ax, 0.3, 3.5, 1.6, 1.4, "940nm LED", sublabel="external\nwearable",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7.5)

    # Scalp/skull tissue (vertical block)
    tissue = FancyBboxPatch((2.4, 2.5), 3.0, 3.4,
                             boxstyle="round,pad=0.02,rounding_size=0.05",
                             facecolor='#F5DEB3', edgecolor=INK_700, linewidth=1.0,
                             alpha=0.5)
    ax.add_patch(tissue)
    ax.text(3.9, 5.5, "Scalp + Skull", ha='center', va='center',
            fontsize=9, color=INK_700, fontweight='bold')
    ax.text(3.9, 4.2, "5mm tissue path", ha='center', va='center',
            fontsize=7.5, color=INK_500, style='italic')
    ax.text(3.9, 3.5, "Jacques 2013 + PyTissueOptics v2.0.1 (DCC-Lab, independent):\nμ_a=0.05/cm, μ_s=8.0/cm",
            ha='center', va='center', fontsize=7, color=INK_500)

    # GaAs PV cell
    _block(ax, 5.9, 3.5, 1.6, 1.4, "GaAs PV", sublabel="implanted",
           color=BRAND_900, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)

    # Power conditioning
    _block(ax, 7.9, 3.5, 1.4, 1.4, "Power Cond.", sublabel="regulator",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7.5)

    # Load (sensor)
    _block(ax, 9.5, 3.5, 1.2, 1.4, "Sensor /", sublabel="Load",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=8.5, sublabel_size=7.5)

    # Arrows
    _arrow(ax, 1.9, 4.2, 2.4, 4.2, color=INK_700, lw=1.2,
           label="940nm collimated", label_size=7, label_offset=(0, 0.25))
    _arrow(ax, 5.4, 4.2, 5.9, 4.2, color=ACCENT, lw=1.4,
           label="fluence 1.05 mW/cm²\n(T2-CONFIRMED)", label_size=7,
           label_offset=(0, 0.4))
    _arrow(ax, 7.5, 4.2, 7.9, 4.2, color=INK_700, lw=1.2,
           label="~1050 μW", label_size=7, label_offset=(0, 0.25))
    _arrow(ax, 9.3, 4.2, 9.5, 4.2, color=INK_700, lw=1.2)

    # Evidence ladder (T2 verified callout)
    ev_box = FancyBboxPatch((0.3, 0.4), 10.4, 1.4,
                             boxstyle="round,pad=0.02,rounding_size=0.05",
                             facecolor=EV_COMPUTATIONAL_BG, edgecolor=EV_COMPUTATIONAL,
                             linewidth=1.0)
    ax.add_patch(ev_box)
    ax.text(0.5, 1.4, "EVIDENCE: COMPUTATIONALLY_SUPPORTED (T2-CONFIRMED)",
            fontsize=8.5, color=EV_COMPUTATIONAL, fontweight='bold')
    ax.text(0.5, 0.85,
            "PyTissueOptics v2.0.1 (DCC-Lab, independent) + Jacques 2013 (evidence source).\n"
            "MC convergence documented (CIs overlap). Published Jacques 2013 range confirmed.\n"
            "Reproducible: pip install pytissueoptics. PHYSICAL VALIDATION OUTSTANDING (LED + phantom + PV bench).",
            fontsize=7.5, color=INK_700)

    return _save(fig, name)


def diagram_P21R1(name="P-21-R1"):
    """P-21-R1 UWB Catheter Position Mapping R1 Repair — sensor architecture."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-21-R1 UWB Catheter Position Mapping (R1 Repair)",
           "Implantable UWB transmitter → external receiver array → TOA localization (SAR-bounded)",
           y=6.5)

    # Patient skull (semi-circle representation)
    theta = np.linspace(0, np.pi, 50)
    x_skull = 5.5 + 3.5 * np.cos(theta)
    y_skull = 2.5 + 2.5 * np.sin(theta)
    ax.fill_between(x_skull, y_skull, 0.5, color='#F5DEB3', alpha=0.4,
                    edgecolor=INK_700, linewidth=1.0)
    ax.text(5.5, 4.5, "Patient Skull/Scalp", ha='center', va='center',
            fontsize=8.5, color=INK_700, fontweight='bold', style='italic')

    # Implantable UWB transmitter at catheter tip
    tag = Circle((5.5, 2.0), 0.35, facecolor=EV_PHYSICAL,
                 edgecolor=INK_900, linewidth=1.0, zorder=5)
    ax.add_patch(tag)
    ax.text(5.5, 2.0, "UWB\nTX", ha='center', va='center',
            fontsize=7, color='white', fontweight='bold', zorder=6)
    ax.text(5.5, 1.4, "Catheter Tip (UWB transmitter)",
            ha='center', va='center', fontsize=7, color=INK_500, style='italic')

    # External receiver array (above skull)
    _block(ax, 4.0, 5.3, 3.0, 0.8, "External Receiver Array", sublabel="4+ antennas",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=8, sublabel_size=7)

    # RF link (bidirectional arrow)
    _arrow(ax, 5.5, 5.3, 5.5, 2.35, color=BRAND_500, lw=1.4,
           label="UWB pulse train\nthrough skull tissue",
           label_size=7, label_offset=(1.6, 0.3))

    # Localization algorithm
    _block(ax, 7.8, 4.3, 2.4, 1.6, "Localization Algorithm",
           sublabel="TOA + TDOA\n3D position",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=8, sublabel_size=7.5)
    _arrow(ax, 7.0, 5.55, 7.8, 5.1, color=INK_700, lw=1.2,
           label="signal", label_size=7, label_offset=(0.1, 0.25))

    # Clinical display
    _block(ax, 10.35, 4.3, 0.65, 1.6, "Display", sublabel="(x,y,z)",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=7, sublabel_size=6.5)
    _arrow(ax, 10.2, 5.1, 10.35, 5.1, color=ACCENT, lw=1.4)

    # R1 repair note (red boundary)
    fail_box = FancyBboxPatch((0.3, 0.4), 10.4, 1.3,
                              boxstyle="round,pad=0.02,rounding_size=0.05",
                              facecolor=EV_KILLED_BG, edgecolor=EV_KILLED,
                              linewidth=1.0)
    ax.add_patch(fail_box)
    ax.text(0.5, 1.4, "P-21 ORIGINAL FAILURE:", fontsize=8, color=EV_KILLED,
            fontweight='bold')
    ax.text(0.5, 0.85,
            "P-21 original: assumed sub-mm accuracy without SAR analysis.\n"
            "R1 REPAIR: bounds accuracy by SAR limit (1.6 W/kg averaged over 1g tissue) and tissue propagation physics.\n"
            "UWB requires Bandwidth B >= 500 MHz (EXTERNAL_PRECEDENT).",
            fontsize=7.5, color=INK_700)

    return _save(fig, name)


def diagram_P22R1(name="P-22-R1"):
    """P-22-R1 Autonomous Catheter Navigation R1 Repair — control loop (hydraulic)."""
    fig, ax = _setup_axes(figsize=(9, 6.2), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-22-R1 Autonomous Catheter Navigation (R1 Repair)",
           "Hydraulic pressure-driven multi-segment catheter navigation [R1 REPAIR from SMP]",
           y=6.5)

    # Hydraulic pressure source
    _block(ax, 0.3, 4.5, 1.8, 1.0, "Hydraulic Source", sublabel="P_hyd per segment",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)

    # Multi-segment catheter
    _block(ax, 2.6, 4.0, 2.4, 1.6, "Multi-segment\nCatheter",
           sublabel="hydraulic chambers\n(no buckling failure mode)",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 2.1, 5.0, 2.6, 4.8, color=INK_700, lw=1.2)

    # Position sensor
    _block(ax, 5.6, 4.5, 1.4, 1.0, "Position Sensor", sublabel="(x,y,z) tip",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 5.0, 5.0, 5.6, 5.0, color=INK_700, lw=1.0)

    # PID controller
    _block(ax, 7.5, 4.5, 1.8, 1.0, "PID Controller", sublabel="delay compensated",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 7.0, 5.0, 7.5, 5.0, color=INK_700, lw=1.2, label="error",
           label_size=7, label_offset=(0, 0.2))

    # Feedback to hydraulic source
    _arrow(ax, 8.4, 5.5, 8.4, 6.3, color=ACCENT, lw=1.4)
    _arrow(ax, 8.4, 6.3, 1.2, 6.3, color=ACCENT, lw=1.4)
    _arrow(ax, 1.2, 6.3, 1.2, 5.5, color=ACCENT, lw=1.4,
           label="P_hyd update (closed loop)", label_size=7,
           label_offset=(0, 0.25))

    # Tissue phantom
    _block(ax, 2.6, 1.5, 4.0, 1.5, "Tissue Phantom",
           sublabel="contact force target < 0.01 N\n(P-22 original: effective force 0.039 N exceeds damage threshold 0.01 N by 4x)",
           color=INK_500, bg=INK_100, label_color="white",
           sublabel_color=INK_700, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 3.8, 4.0, 3.8, 3.0, color=INK_700, lw=1.2,
           label="contact", label_size=7, label_offset=(0.5, 0))

    # Target
    _block(ax, 7.5, 1.5, 2.5, 1.5, "Target Position",
           sublabel="5mm accuracy\nsafe navigation",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7.5)
    _arrow(ax, 6.6, 2.25, 7.5, 2.25, color=ACCENT, lw=1.4,
           label="reach", label_size=7, label_offset=(0, 0.25))

    # R1 repair note
    fail_box = FancyBboxPatch((0.3, 0.0), 10.4, 1.0,
                              boxstyle="round,pad=0.02,rounding_size=0.05",
                              facecolor=EV_KILLED_BG, edgecolor=EV_KILLED,
                              linewidth=1.0)
    ax.add_patch(fail_box)
    ax.text(0.5, 0.7, "P-22 ORIGINAL FAILURE (4 UNRESOLVED):", fontsize=8,
            color=EV_KILLED, fontweight='bold')
    ax.text(0.5, 0.2,
            "SMP buckling (82x exceedance) • Tissue safety (0.039 N > 0.01 N by 4x) • Control stability (30s delay) • No failure recovery.\n"
            "R1 REPAIR: hydraulic pressure-driven navigation + delay-compensated PID + tissue safety.",
            fontsize=7, color=INK_700)

    return _save(fig, name)


def diagram_P24(name="P-24"):
    """P-24 Gravity-Compensated Hydraulic Damper — device cross-section."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-24 Gravity Compensation Hydraulic Damper for Postural Transients",
           "Passive gravity-head damper for postural ICP compensation",
           y=6.5)

    # CSF inflow
    _block(ax, 0.3, 3.5, 1.4, 1.4, "CSF Inflow", sublabel="postural pressure transients",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 1.7, 4.2, 2.4, 4.2, color=INK_700, lw=1.2)

    # Damper chamber (large rounded rect, gravity head visualized)
    chamber = FancyBboxPatch((2.4, 2.5), 3.0, 3.0,
                             boxstyle="round,pad=0.02,rounding_size=0.1",
                             facecolor=BRAND_100, edgecolor=BRAND_700, linewidth=1.5)
    ax.add_patch(chamber)
    ax.text(3.9, 5.2, "Damper Chamber", ha='center', va='center',
            fontsize=9, color=BRAND_700, fontweight='bold')

    # Gravity head (liquid level visualization)
    liquid = Polygon([(2.6, 2.7), (5.2, 2.7), (5.2, 4.5), (2.6, 4.5)],
                      facecolor=BRAND_300, edgecolor=BRAND_500, linewidth=0.8, alpha=0.6)
    ax.add_patch(liquid)
    ax.text(3.9, 3.6, "gravity head h", ha='center', va='center',
            fontsize=8, color=BRAND_900, style='italic', fontweight='bold')

    # Adjustable orifice
    _block(ax, 5.8, 3.7, 1.4, 1.0, "Adjustable Orifice", sublabel="hydraulic resistance",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=8.5, sublabel_size=7)
    _arrow(ax, 5.4, 4.2, 5.8, 4.2, color=INK_700, lw=1.2)

    # Gravity reference chamber (pressure equalization)
    _block(ax, 7.6, 3.7, 1.6, 1.0, "Gravity Reference Chamber", sublabel="dP_gravity = rho * g * dh",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=8, sublabel_size=6.5)
    _arrow(ax, 7.2, 4.2, 7.6, 4.2, color=INK_700, lw=1.2)

    # Drainage outlet
    _block(ax, 9.6, 3.7, 1.2, 1.0, "Outlet", sublabel="Settling time: tau",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 9.2, 4.2, 9.6, 4.2, color=INK_700, lw=1.2)

    # Postural scenarios (bottom)
    ax.text(0.3, 1.7, "Postural ICP compensation:", fontsize=8.5,
            color=BRAND_700, fontweight='bold')
    scenarios = ["Upright", "Supine", "Postural change"]
    for i, s in enumerate(scenarios):
        x = 1.5 + i * 1.8
        sc = FancyBboxPatch((x, 1.1), 1.5, 0.4,
                             boxstyle="round,pad=0.02,rounding_size=0.05",
                             facecolor=BRAND_100, edgecolor=BRAND_300, linewidth=0.5)
        ax.add_patch(sc)
        ax.text(x + 0.75, 1.3, s, ha='center', va='center',
                fontsize=7, color=BRAND_700)

    # Honest state
    ax.text(0.3, 0.4,
            "Honest state: T1 MODEL_PREDICTED (60% postural ICP excursion reduction). Passive — no electronics, no actuation.",
            fontsize=7, color=INK_500, style='italic')

    return _save(fig, name)


def diagram_P26(name="P-26"):
    """P-26 Osmotic-Regulated Drainage Valve — mechanism diagram."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-26 Osmotic-Regulated Drainage Valve",
           "Passive osmotic membrane responds to CSF osmolarity changes",
           y=6.5)

    # CSF inflow (variable osmolarity)
    _block(ax, 0.3, 4.0, 1.6, 1.4, "CSF Inflow", sublabel="osmolarity Δ\n(~290 mOsm/kg, EXTERNAL_PRECEDENT)",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 1.9, 4.7, 2.4, 4.7, color=INK_700, lw=1.2)

    # Osmotic membrane (vertical, semi-permeable)
    membrane = Rectangle((2.4, 2.5), 0.3, 3.5,
                         facecolor=BRAND_300, edgecolor=BRAND_700, linewidth=1.0,
                         alpha=0.7)
    ax.add_patch(membrane)
    ax.text(2.55, 6.2, "Semi-permeable\nMembrane", ha='center', va='center',
            fontsize=7.5, color=BRAND_700, fontweight='bold')

    # Water flux arrows (CSF → osmotic chamber)
    for y in [3.5, 4.5, 5.5]:
        _arrow(ax, 2.0, y, 2.4, y, color=BRAND_500, lw=0.8,
               arrowstyle="->", label_offset=(0, 0))

    # Osmotic chamber (reference solution)
    chamber = FancyBboxPatch((3.0, 2.5), 2.5, 3.5,
                             boxstyle="round,pad=0.02,rounding_size=0.05",
                             facecolor=ACCENT_LIGHT, edgecolor=ACCENT, linewidth=1.0)
    ax.add_patch(chamber)
    ax.text(4.25, 5.7, "Osmotic Chamber", ha='center', va='center',
            fontsize=8.5, color=INK_900, fontweight='bold')
    ax.text(4.25, 4.2, "Reference\nSolution\n(fixed osmolarity)", ha='center',
            va='center', fontsize=7.5, color=INK_700, style='italic')

    # Mechanical linkage
    _block(ax, 6.0, 4.0, 1.6, 1.4, "Mechanical Linkage", sublabel="pressure Δ\nJv = Lp * (dP - sigma * dPi)",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=6.5)
    _arrow(ax, 5.5, 4.7, 6.0, 4.7, color=INK_700, lw=1.2)

    # Drainage orifice (variable)
    _block(ax, 8.1, 4.0, 1.4, 1.4, "Variable Orifice", sublabel="area adjusts",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 7.6, 4.7, 8.1, 4.7, color=INK_700, lw=1.2)

    # Drainage outlet
    _block(ax, 9.8, 4.0, 1.0, 1.4, "Outlet", sublabel="self-regulating",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 9.5, 4.7, 9.8, 4.7, color=INK_700, lw=1.2)

    # Bottom annotation
    ax.text(0.3, 1.7, "Target response:", fontsize=8.5, color=BRAND_700,
            fontweight='bold')
    ax.text(0.3, 1.3, "• Drainage adjusts proportionally (self-regulation)\n"
                       "• Passive self-regulating CSF drainage\n"
                       "• Osmolarity reference ~290 mOsm/kg (EXTERNAL_PRECEDENT)",
            fontsize=7.5, color=INK_700)

    ax.text(0.3, 0.3,
            "Honest state: T1 MODEL_PREDICTED (35% drainage regulation improvement). Prior-art: 11 hits — FTO analysis required.",
            fontsize=7, color=INK_500, style='italic')

    return _save(fig, name)


def diagram_P27R1(name="P-27-R1"):
    """P-27-R1 Self-Referenced Piezoresistive Sensor R1 Repair — sensor architecture (metal tube)."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-27-R1 Self-Referenced Piezoresistive Sensor (R1 Repair)",
           "Metal tube substrate + vacuum reference chamber for drift compensation",
           y=6.5)

    # Pressure-sensitive diaphragm (left)
    diaphragm = FancyBboxPatch((0.5, 2.8), 0.3, 2.5,
                                boxstyle="round,pad=0.01,rounding_size=0.02",
                                facecolor=BRAND_300, edgecolor=BRAND_700, linewidth=1.0)
    ax.add_patch(diaphragm)
    ax.text(0.65, 5.5, "Diaphragm", ha='center', va='center',
            fontsize=8, color=BRAND_700, fontweight='bold')
    ax.text(0.1, 4.0, "CSF pressure", ha='center', va='center', fontsize=9,
            color=INK_700, fontweight='bold')
    _arrow(ax, 0.0, 4.0, 0.5, 4.0, color=INK_700, lw=1.4,
           label="CSF pressure", label_size=7, label_offset=(-0.3, 0.5))

    # Metal tube substrate (horizontal)
    tube = FancyBboxPatch((0.8, 3.5), 5.0, 1.0,
                           boxstyle="round,pad=0.02,rounding_size=0.05",
                           facecolor=INK_500, edgecolor=INK_900, linewidth=1.0)
    ax.add_patch(tube)
    ax.text(3.3, 4.0, "Metal Tube Substrate (316L SS)",
            ha='center', va='center', fontsize=8.5, color='white', fontweight='bold')
    _arrow(ax, 0.8, 4.0, 0.8, 3.5, color=INK_500, lw=0.6,
           arrowstyle="-", label_offset=(0, 0))

    # Piezoresistive element (on top of tube)
    pe_block = Rectangle((2.5, 4.5), 1.5, 0.4,
                         facecolor=EV_PHYSICAL, edgecolor=INK_900, linewidth=0.8)
    ax.add_patch(pe_block)
    ax.text(3.25, 4.7, "Piezoresistive (strain gauge)", ha='center', va='center',
            fontsize=7, color='white', fontweight='bold')

    # Reference chamber (vacuum, below tube)
    ref_chamber = FancyBboxPatch((4.5, 2.5), 1.5, 0.9,
                                  boxstyle="round,pad=0.02,rounding_size=0.05",
                                  facecolor='white', edgecolor=BRAND_700,
                                  linewidth=1.0, linestyle='--')
    ax.add_patch(ref_chamber)
    ax.text(5.25, 2.95, "Vacuum Reference", ha='center', va='center',
            fontsize=7.5, color=BRAND_700, fontweight='bold')
    _arrow(ax, 5.25, 3.5, 5.25, 3.4, color=BRAND_500, lw=1.0,
           label="self-reference", label_size=7, label_offset=(1.0, 0))

    # Signal conditioning
    _block(ax, 6.5, 3.5, 1.8, 1.0, "Signal Cond.", sublabel="resistance change → V",
           color=BRAND_500, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 6.0, 4.0, 6.5, 4.0, color=INK_700, lw=1.2, label="resistance change",
           label_size=7, label_offset=(0, 0.2))

    # Output
    _block(ax, 8.7, 3.5, 1.5, 1.0, "Output", sublabel="P (drift compensation)",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7)
    _arrow(ax, 8.3, 4.0, 8.7, 4.0, color=ACCENT, lw=1.4)

    # R1 repair callout
    fail_box = FancyBboxPatch((0.3, 0.4), 10.4, 1.5,
                              boxstyle="round,pad=0.02,rounding_size=0.05",
                              facecolor=EV_KILLED_BG, edgecolor=EV_KILLED,
                              linewidth=1.0)
    ax.add_patch(fail_box)
    ax.text(0.5, 1.6, "P-27 ORIGINAL FAILURE:", fontsize=8, color=EV_KILLED,
            fontweight='bold')
    ax.text(0.5, 0.9,
            "Polymer substrate: hysteresis 8% (target <1%), drift 2%/day (target <0.5%/day).\n"
            "R1 REPAIR: metal tube (316L SS) for low hysteresis + vacuum reference for drift compensation.\n"
            "Drift target <0.5%/day — modelled, NOT yet measured.",
            fontsize=7.5, color=INK_700)

    return _save(fig, name)


def diagram_P28(name="P-28"):
    """P-28 Acoustic Obstruction Detection — mechanism diagram."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-28 Acoustic Obstruction Detection",
           "External acoustic transducer → skull → CSF column → obstruction detection",
           y=6.5)

    # External acoustic transducer
    _block(ax, 0.3, 4.5, 1.6, 1.0, "Acoustic TX", sublabel="1-10 kHz",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7)

    # Patient scalp/skull (curved)
    theta = np.linspace(0, np.pi, 50)
    x_skull = 4.5 + 3.5 * np.cos(theta)
    y_skull = 1.5 + 3.0 * np.sin(theta)
    ax.fill_between(x_skull, y_skull, 0.5, color='#F5DEB3', alpha=0.4,
                    edgecolor=INK_700, linewidth=1.0)
    ax.text(4.5, 4.0, "Patient Skull", ha='center', va='center',
            fontsize=8.5, color=INK_700, fontweight='bold', style='italic')

    # CSF column (vertical, inside skull)
    csf = Rectangle((4.3, 1.5), 0.4, 2.5,
                    facecolor=BRAND_100, edgecolor=BRAND_500, linewidth=1.0)
    ax.add_patch(csf)
    ax.text(4.5, 1.2, "CSF column\n(catheter)", ha='center', va='center',
            fontsize=7, color=BRAND_700, fontweight='bold')

    # Obstruction site (red blob on CSF column)
    obstruct = Circle((4.5, 2.5), 0.18, facecolor=EV_KILLED,
                      edgecolor=INK_900, linewidth=0.6, zorder=5)
    ax.add_patch(obstruct)
    ax.text(5.0, 2.5, "obstruction", ha='left', va='center',
            fontsize=7, color=EV_KILLED, fontweight='bold')

    # Acoustic path (transmit through skull to CSF)
    _arrow(ax, 1.9, 5.0, 3.0, 4.3, color=ACCENT, lw=1.2,
           label="acoustic pulse", label_size=7, label_offset=(0, 0.3))
    _arrow(ax, 3.5, 4.0, 4.3, 3.8, color=ACCENT, lw=1.0)

    # External acoustic receiver
    _block(ax, 7.5, 4.5, 1.6, 1.0, "Acoustic RX", sublabel="received echo",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7)
    _arrow(ax, 5.5, 4.0, 7.5, 4.8, color=ACCENT, lw=1.0,
           label="modified resonance", label_size=7, label_offset=(0, 0.3))

    # Signal processor
    _block(ax, 9.5, 4.5, 1.2, 1.0, "Signal Proc.", sublabel="echo classification",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=8, sublabel_size=6.5)
    _arrow(ax, 9.1, 5.0, 9.5, 5.0, color=INK_700, lw=1.2)

    # Detection states (bottom) — recorded obstruction types (V-001)
    states = [("normal", BRAND_700), ("debris", ACCENT),
              ("tissue proxy", EV_MODEL), ("air bubble", EV_KILLED)]
    for i, (state, color) in enumerate(states):
        x = 1.0 + i * 2.3
        sc = FancyBboxPatch((x, 1.0), 1.8, 0.5,
                             boxstyle="round,pad=0.02,rounding_size=0.05",
                             facecolor=color, edgecolor=color, linewidth=0.5,
                             alpha=0.85)
        ax.add_patch(sc)
        ax.text(x + 0.9, 1.25, f"{state}", ha='center', va='center',
                fontsize=7, color='white', fontweight='bold')

    # Honest state
    ax.text(0.3, 0.3,
            "Honest state: T1 MODEL_PREDICTED (>=90% detection accuracy). PATENT SEARCH PENDING — high priority for buyer diligence.",
            fontsize=7, color=INK_500, style='italic')

    return _save(fig, name)


def diagram_P29(name="P-29"):
    """P-29 MR Flow Quantification Sensor — sensor architecture (miniaturized NMR)."""
    fig, ax = _setup_axes(figsize=(9, 6), xlim=(0, 11), ylim=(0, 7))

    _title(ax, "P-29 MR Flow Quantification Sensor",
           "Miniaturized NMR: B0 field + RF coil → proton spin phase shift → flow rate",
           y=6.5)

    # Permanent magnet array (top + bottom)
    mag_top = Rectangle((2.5, 5.0), 5.0, 0.5,
                        facecolor=INK_500, edgecolor=INK_900, linewidth=1.0)
    mag_bot = Rectangle((2.5, 1.5), 5.0, 0.5,
                        facecolor=INK_500, edgecolor=INK_900, linewidth=1.0)
    ax.add_patch(mag_top)
    ax.add_patch(mag_bot)
    ax.text(5.0, 5.25, "Miniaturized Permanent Magnet (B0 source)", ha='center', va='center',
            fontsize=7.5, color='white', fontweight='bold')
    ax.text(5.0, 1.75, "Miniaturized Permanent Magnet (B0 source)", ha='center', va='center',
            fontsize=7.5, color='white', fontweight='bold')

    # B0 field arrows (downward)
    for x in [3.0, 4.0, 5.0, 6.0, 7.0]:
        _arrow(ax, x, 5.0, x, 2.0, color=INK_500, lw=0.5,
               arrowstyle="->", label_offset=(0, 0))

    # CSF flow channel (horizontal between magnets)
    csf = FancyBboxPatch((2.5, 2.5), 5.0, 2.0,
                          boxstyle="round,pad=0.02,rounding_size=0.05",
                          facecolor=BRAND_100, edgecolor=BRAND_700, linewidth=1.0)
    ax.add_patch(csf)
    ax.text(5.0, 4.2, "CSF Flow Channel", ha='center', va='center',
            fontsize=8, color=BRAND_700, fontweight='bold')
    ax.text(5.0, 3.5, "(B0 0.1-1 T — design choice, UNKNOWN)", ha='center', va='center',
            fontsize=7, color=INK_500, style='italic')

    # Miniaturized RF coil (around CSF channel)
    for x in [3.5, 4.5, 5.5, 6.5]:
        coil = Circle((x, 3.5), 0.15, facecolor='none',
                      edgecolor=ACCENT, linewidth=1.5)
        ax.add_patch(coil)
    ax.text(8.0, 3.5, "RF Coil", ha='left', va='center',
            fontsize=8, color=ACCENT, fontweight='bold')
    ax.text(5.0, 2.2, "Gradient Coil (bipolar)", ha='center', va='center',
            fontsize=7.5, color=BRAND_700, fontweight='bold', style='italic')

    # Spin excitation circuit (left)
    _block(ax, 0.3, 4.0, 1.6, 1.0, "Spin Excite", sublabel="90° RF pulse",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7)
    _arrow(ax, 1.9, 4.5, 2.5, 4.0, color=ACCENT, lw=1.2)

    # Spin detection circuit (right)
    _block(ax, 8.7, 4.0, 1.6, 1.0, "Spin Detect", sublabel="echo signal",
           color=ACCENT, bg=ACCENT_LIGHT, label_color="white",
           sublabel_color=INK_900, fontsize=9, sublabel_size=7)
    _arrow(ax, 7.5, 4.0, 8.7, 4.5, color=ACCENT, lw=1.2)

    # Signal processor
    _block(ax, 8.7, 2.0, 1.6, 1.0, "Signal Proc.", sublabel="phase → flow",
           color=BRAND_700, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 9.5, 4.0, 9.5, 3.0, color=INK_700, lw=1.0)

    # Output
    _block(ax, 8.7, 0.5, 1.6, 1.0, "Output", sublabel="flow rate ±5%",
           color=BRAND_900, bg=BRAND_100, label_color="white",
           sublabel_color=BRAND_700, fontsize=9, sublabel_size=7)
    _arrow(ax, 9.5, 2.0, 9.5, 1.5, color=INK_700, lw=1.0)

    # HIGH RISK callout
    risk_box = FancyBboxPatch((0.3, 0.2), 7.5, 1.5,
                              boxstyle="round,pad=0.02,rounding_size=0.05",
                              facecolor=EV_KILLED_BG, edgecolor=EV_KILLED,
                              linewidth=1.0)
    ax.add_patch(risk_box)
    ax.text(0.5, 1.4, "HIGH RISK ALTERNATIVE CANDIDATE", fontsize=8,
            color=EV_KILLED, fontweight='bold')
    ax.text(0.5, 0.7,
            "Miniaturization feasibility UNVERIFIED (target <5mm diameter).\n"
            "Miniaturization feasibility is a critical UNKNOWN.\n"
            "PATENT SEARCH PENDING. Power consumption + magnetic safety unknown.",
            fontsize=7.5, color=INK_700)

    return _save(fig, name)


# ----------------------------------------------------------------------------
# Master generator
# ----------------------------------------------------------------------------

DIAGRAM_GENERATORS = {
    "P-01": diagram_P01,
    "P-02": diagram_P02,
    "P-04": diagram_P04,
    "P-07": diagram_P07,
    "P-11": diagram_P11,
    "P-13": diagram_P13,
    "P-15-R1": diagram_P15R1,
    "P-16": diagram_P16,
    "P-21-R1": diagram_P21R1,
    "P-22-R1": diagram_P22R1,
    "P-24": diagram_P24,
    "P-26": diagram_P26,
    "P-27-R1": diagram_P27R1,
    "P-28": diagram_P28,
    "P-29": diagram_P29,
}


def generate_all_diagrams():
    """Generate all 15 diagrams and return {pkg_id: path}."""
    results = {}
    for pkg_id, gen in DIAGRAM_GENERATORS.items():
        try:
            path = gen()
            results[pkg_id] = path
        except Exception as e:
            print(f"ERROR generating {pkg_id}: {e}")
            import traceback
            traceback.print_exc()
            results[pkg_id] = None
    return results


if __name__ == "__main__":
    results = generate_all_diagrams()
    print(f"\nGenerated {sum(1 for v in results.values() if v)} / 15 diagrams")
    for k, v in results.items():
        print(f"  {k}: {v}")

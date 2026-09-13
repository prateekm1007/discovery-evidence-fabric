"""Deterministic domain geometry builders (R432 sections 3, 9, 10).

Consumes the canonical geometry spec (domain_spec.py) and builds the
technology model with CadQuery/OCCT — the geometry authority:

    canonical geometry spec  ->  deterministic builders  ->  GLB
                                       (this module)

Contract:
  * Node names ARE the canonical component IDs (R432 section 9 —
    battery_pack, solar_roof, traction_motor…; never Cube.001).
  * Deterministic: identical spec -> identical geometry -> identical
    GLB sha256 (the hash identity the artifact chain carries).
  * Abstract presentation units only — never mm, never engineering
    dimensions (measurement_basis=TOPOLOGY_ONLY; epistemics guards
    apply unchanged).
  * Material classes ride the spec (domain_spec assigns them); the
    vertex-color palette here and the Blender PBR presets in
    blender_render.py both key off THE SAME spec — one source of
    material truth (the R425 one-CAD-source discipline extended to
    materials).
  * Presentation form components are geometric only: the builders
    never fabricate engineering relationships that the recorded state
    does not carry; interfaces drawn are exactly the spec interfaces.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import trimesh

from .coloring import apply_gltf_yup, set_uniform_color
from ..domains import canonical_family_of_bridge_archetype


class _CadQueryLazy:
    """R452 C2 (external audit): LAZY CadQuery/OCP loader — the ~500 MB
    RSS import is paid ONLY when a geometry build actually executes,
    never by the bridge import itself (a conceptual-class run never
    crosses it). First access rebinds this global to the real module."""

    def __getattr__(self, name: str):
        import cadquery as cq
        globals()["cq"] = cq
        return getattr(cq, name)


cq = _CadQueryLazy()

# Vertex-color palette per material class (abstract presentation colors;
# the Blender stage replaces these with PBR material presets).
MATERIAL_COLORS: Dict[str, Tuple[int, int, int, int]] = {
    "body_metal": (172, 176, 184, 255),
    "glass": (104, 138, 172, 255),
    "silicon": (10, 18, 56, 255),
    "battery": (38, 40, 44, 255),
    "rubber": (24, 24, 26, 255),
    "polymer": (210, 206, 196, 255),
    "machined_metal": (136, 140, 146, 255),
    "circuit": (46, 80, 60, 255),
    "ceramic": (222, 220, 214, 255),
    "composite": (96, 114, 132, 255),
    "conduit_power": (188, 116, 64, 255),
    "conduit_data": (86, 132, 182, 255),
    "default": (160, 110, 78, 255),
}

# Material classes Blender maps to PBR presets (section 10).
MATERIAL_CLASSES = tuple(MATERIAL_COLORS)


# ---------------------------------------------------------------------------
# Mesh helpers (multi-body components concatenate tessellations — one node
# may legitimately be a multi-shell solid: e.g. a fin stack, a tube loop)
# ---------------------------------------------------------------------------

def _mesh_from_shapes(shapes: Sequence[Any],
                      tolerance: float = 0.08) -> trimesh.Trimesh:
    """Concatenate cq shapes AND/OR ready trimesh meshes into one mesh
    (one node may legitimately be a multi-shell solid: fin stacks, tube
    loops)."""
    verts: List[Tuple[float, float, float]] = []
    faces: List[List[int]] = []
    for shape in shapes:
        if isinstance(shape, trimesh.Trimesh):
            v = shape.vertices
            t = shape.faces
            off = len(verts)
            verts.extend((float(p[0]), float(p[1]), float(p[2])) for p in v)
            faces.extend([[int(a) + off, int(b) + off, int(c) + off]
                          for (a, b, c) in t])
            continue
        v, t = (shape.val() if hasattr(shape, "val") else shape).tessellate(
            tolerance)
        off = len(verts)
        verts.extend((p.x, p.y, p.z) for p in v)
        faces.extend([[a + off, b + off, c + off] for (a, b, c) in t])
    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)


def _box(l: float, w: float, h: float, cx: float = 0.0, cy: float = 0.0,
         cz: float = 0.0) -> cq.Workplane:
    return (cq.Workplane("XY")
            .box(l, w, h, centered=(False, False, False))
            .translate((cx - l / 2, cy - w / 2, cz)))


def _cyl_x(radius: float, length: float, cx: float = 0.0, cy: float = 0.0,
           cz: float = 0.0) -> cq.Workplane:
    """Cylinder along +X (axis through cx,cy,cz)."""
    return (cq.Workplane("YZ")
            .circle(radius).extrude(length)
            .translate((cx - length / 2, cy, cz)))


def _cyl_y(radius: float, length: float, cx: float = 0.0, cy: float = 0.0,
           cz: float = 0.0) -> cq.Workplane:
    """Cylinder along Y (axis through cx,cy,cz)."""
    return (cq.Workplane("XZ")
            .circle(radius).extrude(length, both=True)
            .translate((cx, cy, cz)))


def _cyl_z(radius: float, length: float, cx: float = 0.0, cy: float = 0.0,
           cz: float = 0.0) -> cq.Workplane:
    """Cylinder along +Z (base at cz)."""
    return (cq.Workplane("XY")
            .circle(radius).extrude(length)
            .translate((cx, cy, cz)))


def _tube(p1: Tuple[float, float, float], p2: Tuple[float, float, float],
          radius: float) -> trimesh.Trimesh:
    """A capped cylinder tube connecting two points — ANY direction.

    R432 iteration fix: the rotate-based orientation silently failed
    for pure-Y/pure-Z directions (horiz=0 skips the second rotation —
    a cross tube ended up sticking 0.65 units out of the vehicle
    nose, flagged by the visual audit). trimesh segment cylinders are
    direction-exact by construction."""
    return trimesh.creation.cylinder(
        radius=radius, sections=24,
        segment=[list(p1), list(p2)])


def _cone_z(r1: float, r2: float, h: float, cx: float = 0.0,
            cy: float = 0.0, cz: float = 0.0) -> cq.Workplane:
    """Tapered solid along +Z (base radius r1 at cz, top r2)."""
    return (cq.Workplane("XY")
            .circle(r1).workplane(offset=h).circle(r2)
            .loft().translate((cx, cy, cz)))


def _ring_x(radius_outer: float, radius_inner: float, length: float,
            cx: float = 0.0, cy: float = 0.0, cz: float = 0.0) -> cq.Workplane:
    body = _cyl_x(radius_outer, length, cx, cy, cz)
    hole = _cyl_x(radius_inner, length + 2.0, cx, cy, cz)
    return body.cut(hole)


# ---------------------------------------------------------------------------
# Build plan: each family builder returns
#   components: [(component_id, [shapes], material_class)]
#   anchors:    {component_id: (x, y, z)}   (conduit attachment points)
# ---------------------------------------------------------------------------

def _build_vehicle(spec: Dict[str, Any]) -> Dict[str, Any]:
    """A vehicle-form architecture: hull + tapered cabin + 4 wheels with
    wheel wells, battery pack in the floor, solar surfaces, drivetrain,
    power electronics, thermal loop, charging interface.

    Abstract units: length 9.4 (X), width 4.2 (Y), ground z=0.
    """
    L, W = 9.4, 4.2
    # realistic proportions: fender line flush with wheel tops, wheels
    # flush with the body sides, arches cut as true fender arches
    wheel_r, tread = 0.78, 0.60
    ax_f, ax_r = 2.9, -2.9
    hull_h, hull_z = 1.15, 0.42          # hull spans z 0.42..1.57
    wheel_y = 1.55                        # outer face ~flush with hull side
    arch_r, arch_z = 0.82, 0.74           # arch top 1.56 ~ fender line
    hull_top = hull_z + hull_h

    comps: List[Tuple[str, List[Any], str]] = []
    anchors: Dict[str, Tuple[float, float, float]] = {}

    # --- hull with wheel wells (true fender arches) ------------------------
    hull = _box(L, W - 0.55, hull_h, 0, 0, hull_z)
    hull = hull.edges("|Z").chamfer(0.45)
    for ax in (ax_f, ax_r):
        well = _cyl_y(arch_r, W, ax, 0, arch_z)
        hull = hull.cut(well)
    comps.append(("chassis", [hull], "body_metal"))
    anchors["chassis"] = (0.0, 0.0, hull_top)

    # --- tapered cabin (greenhouse) ---------------------------------------
    cab_l, cab_w = 4.1, W - 1.15
    top_l, top_w = 2.9, W - 1.55
    cabin = (cq.Workplane("XY")
             .rect(cab_l, cab_w)
             .workplane(offset=0.92)
             .rect(top_l, top_w)
             .loft())
    cabin = cabin.translate((-0.55, 0, hull_top - 0.02))
    comps.append(("cabin", [cabin], "glass"))
    anchors["cabin"] = (-0.55, 0, hull_top + 0.92)

    # the spec's own component set drives every conditional slot below
    # (the builder draws exactly what the spec carries — parity is
    # gate-checked; an unmapped node or a missing node are both defects)
    ids = {c["component_id"] for c in spec["components"]}

    # --- wheels --------------------------------------------------------------
    for cid, (ax, sy) in {
        "wheel_fl": (ax_f, 1), "wheel_fr": (ax_f, -1),
        "wheel_rl": (ax_r, 1), "wheel_rr": (ax_r, -1),
    }.items():
        tire = _cyl_y(wheel_r, tread, ax, sy * wheel_y, wheel_r)
        hub = _cyl_y(wheel_r * 0.55, tread + 0.10, ax, sy * wheel_y,
                     wheel_r)
        comps.append((cid, [tire, hub], "rubber"))
    anchors["wheel_fl"] = (ax_f, wheel_y, wheel_r)
    anchors["wheel_fr"] = (ax_f, -wheel_y, wheel_r)
    anchors["wheel_rl"] = (ax_r, wheel_y, wheel_r)
    anchors["wheel_rr"] = (ax_r, -wheel_y, wheel_r)

    # --- solar surfaces ------------------------------------------------------
    # hood/deck are STRUCTURAL (always in the spec); the roof panel is a
    # MAPPED slot (present only when a recorded subsystem maps to it) —
    # the builder draws exactly what the spec carries (spec<->scene
    # parity is gate-checked; drawing an unmapped node is a defect)
    hood = _box(0.80, W - 1.30, 0.10, 4.18, 0, hull_top + 0.01)
    deck = _box(0.80, W - 1.45, 0.10, -4.18, 0, hull_top + 0.01)
    comps.append(("solar_hood", [hood], "silicon"))
    comps.append(("solar_deck", [deck], "silicon"))
    if "solar_roof" in ids:
        roof = _box(top_l - 0.12, top_w - 0.12, 0.10, -0.55, 0,
                    hull_top + 0.90)
        comps.append(("solar_roof", [roof], "silicon"))
        anchors["solar_roof"] = (-0.55, 0.0, hull_top + 0.95)

    # --- optional slots (only when the spec carries them) --------------------

    if "battery_pack" in ids:
        pack = _box(3.7, W - 1.35, 0.52, 0, 0, 0.08)
        comps.append(("battery_pack", [pack], "battery"))
        anchors["battery_pack"] = (0.0, W / 2 - 0.85, 0.34)

    if "traction_motor" in ids:
        motor = _cyl_y(0.50, 1.55, ax_r + 0.15, 0, 0.95)
        gearbox = _box(1.05, 1.0, 0.62, ax_r + 0.15, 0, 0.62)
        comps.append(("traction_motor", [motor, gearbox], "machined_metal"))
        anchors["traction_motor"] = (ax_r + 0.15, 0.75, 0.95)

    if "power_electronics" in ids:
        bay = _box(1.5, 1.7, 0.55, 3.55, 0, hull_top - 0.57)
        comps.append(("power_electronics", [bay], "machined_metal"))
        anchors["power_electronics"] = (3.55, 0.0, hull_top - 0.30)

    if "thermal_loop" in ids:
        radiator = _box(0.30, 1.9, 1.15, L / 2 - 0.35, 0, hull_z)
        rail_y = 1.15  # inside the wheel envelope — never crosses a wheel
        z_t = hull_z + 0.18
        rails = [
            _tube((-3.4, rail_y, z_t), (L / 2 - 0.5, rail_y, z_t), 0.09),
            _tube((-3.4, -rail_y, z_t), (L / 2 - 0.5, -rail_y, z_t), 0.09),
            _tube((-3.4, -rail_y, z_t), (-3.4, rail_y, z_t), 0.09),
            _tube((L / 2 - 0.5, -rail_y, z_t), (L / 2 - 0.5, rail_y, z_t),
                  0.09),
        ]
        comps.append(("thermal_loop", [radiator] + rails, "conduit_power"))
        anchors["thermal_loop"] = (L / 2 - 0.35, 0.9, hull_z + 0.6)

    if "charging_port" in ids:
        port = _cyl_y(0.22, 0.50, 0.7, W / 2 - 0.55, 1.00)
        comps.append(("charging_port", [port], "polymer"))
        anchors["charging_port"] = (0.7, W / 2 - 0.45, 1.00)

    # mounted modules (unmapped subsystems) on the rear deck — resting
    # on the hull top behind the cabin, clear of the solar deck
    mods = [c for c in spec["components"] if c["form"] == "module"]
    for i, m in enumerate(mods):
        mx = -3.05 - 0.65 * (i // 2)
        my = 0.80 * (1 if i % 2 == 0 else -1)
        mz = hull_top
        box = _box(1.00, 0.85, 0.55, mx, my, mz)
        comps.append((m["component_id"], [box], "polymer"))
        anchors[m["component_id"]] = (mx, my, mz + 0.55)

    # mapped control/sensing slots live INSIDE the front bay (internal
    # electronics — real placement; visible in the section view, listed
    # in the component panel; never an unexplained box on the exterior)
    placed = {cid for cid, _, _ in comps}
    for cid, (mx, my, mz), mat in _VEHICLE_SLOT_SITES:
        if cid in ids and cid not in placed:
            comps.append((cid, [_box(1.15, 0.95, 0.62, mx, my, mz)], mat))
            anchors[cid] = (mx, my, mz)

    # interfaces are carried in the spec; conduit link nodes are
    # OPTIONAL in the scene (VEHICLE draws none — the harness runs
    # inside the body). The parity check stays strong: every spec
    # component MUST exist as a node, and every node must be either a
    # spec component or a spec interface link.
    anchors = anchors

    return {"components": comps, "anchors": anchors,
            "interfaces": spec.get("interfaces") or [],
            "draws_conduits": False}


_VEHICLE_SLOT_SITES = [
    # internal bay positions ahead of the front arch (occluded by the
    # opaque body; revealed by the section view; listed in the panel)
    ("control_module", (3.95, 1.45, 0.78), "circuit"),
    ("sensor_module", (3.95, -1.45, 0.78), "circuit"),
]


def _build_medical_device(spec: Dict[str, Any]) -> Dict[str, Any]:
    """A catheter-form architecture along X (distal tip at +X)."""
    comps: List[Tuple[str, List[Any], str]] = []
    anchors: Dict[str, Tuple[float, float, float]] = {}
    ids = {c["component_id"] for c in spec["components"]}

    shaft = _cyl_x(0.50, 8.0, -0.5, 0, 0.5)
    comps.append(("device_shaft", [shaft], "polymer"))
    anchors["device_shaft"] = (0.0, 0.0, 0.5)

    tip = (cq.Workplane("YZ").workplane(offset=7.5)
           .circle(0.50).workplane(offset=1.3).circle(0.14).loft())
    comps.append(("distal_tip", [tip], "polymer"))
    anchors["distal_tip"] = (7.6, 0.0, 0.5)

    hub_body = _box(1.05, 1.5, 1.5, -2.55, 0, -0.25)
    port = _cyl_y(0.22, 0.75, -2.55, 0.9, 0.35)
    comps.append(("hub", [hub_body, port], "polymer"))
    anchors["hub"] = (-2.55, 0.0, 0.5)

    if "flow_lumen" in ids:
        lumen = _cyl_x(0.13, 7.6, 0.2, 0.30, 0.62)
        comps.append(("flow_lumen", [lumen], "conduit_power"))
        anchors["flow_lumen"] = (0.2, 0.30, 0.62)
    if "therapy_lumen" in ids:
        tl = _cyl_x(0.11, 7.4, 0.1, -0.30, 0.44)
        comps.append(("therapy_lumen", [tl], "conduit_data"))
        anchors["therapy_lumen"] = (0.1, -0.30, 0.44)
    if "valve_membrane" in ids:
        vbox = _box(0.75, 0.85, 0.55, 5.2, 0, 0.24)
        comps.append(("valve_membrane", [vbox], "composite"))
        anchors["valve_membrane"] = (5.2, 0.0, 0.5)
    if "sensor_band" in ids:
        band = _ring_x(0.62, 0.46, 0.4, 6.4, 0, 0.5)
        comps.append(("sensor_band", [band], "machined_metal"))
        anchors["sensor_band"] = (6.4, 0.0, 0.5)
    if "surface_coating" in ids:
        sleeve = _cyl_x(0.54, 2.6, 5.0, 0, 0.5)
        comps.append(("surface_coating", [sleeve], "composite"))
        anchors["surface_coating"] = (5.0, 0.0, 0.5)
    if "control_module" in ids:
        ctl = _box(0.95, 0.85, 0.75, -1.6, 0.95, 0.62)
        comps.append(("control_module", [ctl], "circuit"))
        anchors["control_module"] = (-1.6, 0.95, 0.9)
    mods = [c for c in spec["components"] if c["form"] == "module"]
    for i, m in enumerate(mods):
        mx = -1.0 - 1.15 * i
        box = _box(0.9, 0.8, 0.7, mx, -1.0, 0.55)
        comps.append((m["component_id"], [box], "polymer"))
        anchors[m["component_id"]] = (mx, -1.0, 0.85)

    return {"components": comps, "anchors": anchors,
            "interfaces": spec.get("interfaces") or []}


def _build_fluid_device(spec: Dict[str, Any]) -> Dict[str, Any]:
    """A fluid device: body + chamber + through channel + ports + stages."""
    comps: List[Tuple[str, List[Any], str]] = []
    anchors: Dict[str, Tuple[float, float, float]] = {}
    ids = {c["component_id"] for c in spec["components"]}

    body = _box(6.2, 4.0, 2.4, 0, 0, 0.0)
    body = body.edges("|Z").chamfer(0.45)
    comps.append(("device_body", [body], "polymer"))
    anchors["device_body"] = (0.0, 0.0, 2.4)

    channel = _cyl_x(0.32, 8.4, 0, 0, 1.15)
    comps.append(("flow_channel", [channel], "conduit_power"))
    anchors["flow_channel"] = (0.0, 0.0, 1.15)

    if "chamber" in ids:
        dome = _cyl_z(1.35, 1.9, 0, 0, 2.4)
        comps.append(("chamber", [dome], "polymer"))
        anchors["chamber"] = (0.0, 0.0, 3.6)
    if "inlet_port" in ids:
        port = _cyl_x(0.34, 1.6, -3.9, 0, 1.15)
        flange = _cyl_x(0.5, 0.25, -3.25, 0, 1.15)
        comps.append(("inlet_port", [port, flange], "polymer"))
        anchors["inlet_port"] = (-3.9, 0.0, 1.15)
    if "outlet_port" in ids:
        port = _cyl_x(0.34, 1.6, 3.9, 0, 1.15)
        flange = _cyl_x(0.5, 0.25, 3.25, 0, 1.15)
        comps.append(("outlet_port", [port, flange], "polymer"))
        anchors["outlet_port"] = (3.9, 0.0, 1.15)
    if "valve_stage" in ids:
        vbox = _box(1.3, 1.5, 1.0, -1.4, 0, 2.4)
        stem = _cyl_z(0.22, 1.1, -1.4, 0, 3.4)
        comps.append(("valve_stage", [vbox, stem], "machined_metal"))
        anchors["valve_stage"] = (-1.4, 0.0, 3.3)
    if "flow_sensor" in ids:
        ring = _ring_x(0.52, 0.36, 0.5, 1.6, 0, 1.15)
        comps.append(("flow_sensor", [ring], "machined_metal"))
        anchors["flow_sensor"] = (1.6, 0.0, 1.15)
    if "actuator_stage" in ids:
        abox = _box(1.4, 1.2, 0.9, 0.8, 1.35, 2.4)
        comps.append(("actuator_stage", [abox], "circuit"))
        anchors["actuator_stage"] = (0.8, 1.35, 2.9)
    mods = [c for c in spec["components"] if c["form"] == "module"]
    # R443: distinct placement per module (the audit defect: every
    # module at one position -> duplicate geometry + invisible stack).
    # Grid on the rear deck, column stride 1.3 (> box width 1.1) with
    # row wrap every 3 columns — every module gets its own cell.
    for i, m in enumerate(mods):
        col, row = i % 3, i // 3
        mx = 2.2 - 1.35 * col
        my = -1.35 - 1.05 * row
        box = _box(1.1, 0.9, 0.8, mx, my, 2.4)
        comps.append((m["component_id"], [box], "polymer"))
        anchors[m["component_id"]] = (mx, my, 2.9)

    return {"components": comps, "anchors": anchors,
            "interfaces": spec.get("interfaces") or []}


def _build_thermal_system(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Thermal system: base + heat source + cold plate + fin stack + loop."""
    comps: List[Tuple[str, List[Any], str]] = []
    anchors: Dict[str, Tuple[float, float, float]] = {}
    ids = {c["component_id"] for c in spec["components"]}

    base = _box(7.4, 5.0, 0.45, 0, 0, 0.0)
    comps.append(("assembly_base", [base], "body_metal"))
    anchors["assembly_base"] = (0.0, 0.0, 0.45)

    if "heat_source" in ids:
        src = _box(2.6, 3.0, 1.15, -2.1, 0, 0.45)
        comps.append(("heat_source", [src], "battery"))
        anchors["heat_source"] = (-2.1, 0.0, 1.6)
    if "cold_plate" in ids:
        plate = _box(0.85, 3.4, 0.4, 0.2, 0, 0.45)
        comps.append(("cold_plate", [plate], "machined_metal"))
        anchors["cold_plate"] = (0.2, 0.0, 0.85)
    if "heat_sink" in ids:
        sink_base = _box(2.8, 3.4, 0.35, 2.4, 0, 0.45)
        fins = [_box(0.16, 3.0, 1.5, 2.4 - 1.1 + 0.28 * k, 0, 0.8)
                for k in range(8)]
        comps.append(("heat_sink", [sink_base] + fins, "machined_metal"))
        anchors["heat_sink"] = (2.4, 0.0, 2.3)
    if "coolant_loop" in ids:
        y_o = 2.05
        z_t = 0.62
        loop = [
            _tube((-2.1, y_o, z_t), (2.4, y_o, z_t), 0.10),
            _tube((-2.1, -y_o, z_t), (2.4, -y_o, z_t), 0.10),
            _tube((-2.1, -y_o, z_t), (-2.1, y_o, z_t), 0.10),
            _tube((2.4, -y_o, z_t), (2.4, y_o, z_t), 0.10),
        ]
        comps.append(("coolant_loop", loop, "conduit_power"))
        anchors["coolant_loop"] = (0.0, y_o, z_t)
    if "control_module" in ids:
        ctl = _box(1.3, 1.1, 0.9, 0.2, -1.95, 0.45)
        comps.append(("control_module", [ctl], "circuit"))
        anchors["control_module"] = (0.2, -1.95, 1.35)
    mods = [c for c in spec["components"] if c["form"] == "module"]
    # R443: distinct placement per module (the audit defect: all modules
    # at one position -> no_duplicate_model FAIL "module_01==module_02").
    # Grid along the rear-left deck margin: column stride 1.3 (> box
    # width 1.1), row stride 1.05 (> box depth 0.9) — non-overlapping.
    for i, m in enumerate(mods):
        col, row = i % 3, i // 3
        mx = -3.1 + 1.3 * col
        my = 1.85 - 1.05 * row
        box = _box(1.1, 0.9, 0.8, mx, my, 0.45)
        comps.append((m["component_id"], [box], "polymer"))
        anchors[m["component_id"]] = (mx, my, 1.25)

    return {"components": comps, "anchors": anchors,
            "interfaces": spec.get("interfaces") or []}


def _build_mechanical_component(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Mechanical component: housing + shaft + bearings + spring + load path."""
    comps: List[Tuple[str, List[Any], str]] = []
    anchors: Dict[str, Tuple[float, float, float]] = {}
    ids = {c["component_id"] for c in spec["components"]}

    shell = _cyl_z(1.55, 2.6, 0, 0, 0.5)
    cavity = _cyl_z(1.28, 2.0, 0, 0, 0.8)
    housing = shell.cut(cavity)
    comps.append(("housing", [housing], "body_metal"))
    anchors["housing"] = (0.0, 0.0, 3.1)

    plate = _box(4.6, 3.4, 0.45, 0, 0, 0.0)
    pillars = [_box(0.55, 0.55, 3.1, -1.9, 1.25, 0.0),
               _box(0.55, 0.55, 3.1, 1.9, -1.25, 0.0)]
    top = _box(4.6, 3.4, 0.4, 0, 0, 3.35)
    comps.append(("load_path", [plate] + pillars + [top], "body_metal"))
    anchors["load_path"] = (1.9, 1.25, 3.35)

    if "shaft" in ids:
        shaft = _cyl_z(0.34, 4.4, 0, 0, -0.2)
        comps.append(("shaft", [shaft], "machined_metal"))
        anchors["shaft"] = (0.0, 0.0, 4.2)
    if "bearing" in ids:
        b1 = _ring_z(0.62, 0.36, 0.34, 0, 0, 1.18)
        b2 = _ring_z(0.62, 0.36, 0.34, 0, 0, 2.12)
        comps.append(("bearing", [b1, b2], "machined_metal"))
        anchors["bearing"] = (0.0, 0.0, 1.35)
    if "spring" in ids:
        coils = []
        for k in range(9):
            cz = 1.55 + 0.17 * k
            coils.append(_ring_z(0.52, 0.40, 0.10, 0, 0, cz))
        comps.append(("spring", coils, "machined_metal"))
        anchors["spring"] = (0.0, 0.52, 2.1)
    if "sensor_module" in ids:
        smod = _box(1.0, 0.85, 0.7, 2.05, 1.15, 3.75)
        comps.append(("sensor_module", [smod], "circuit"))
        anchors["sensor_module"] = (2.05, 1.15, 4.1)
    mods = [c for c in spec["components"] if c["form"] == "module"]
    # R443: distinct placement per module (grid, column stride 1.1 >
    # box width 0.95, row wrap every 3) — no stacked duplicates.
    for i, m in enumerate(mods):
        col, row = i % 3, i // 3
        mx = -2.35 + 1.1 * col
        my = -1.15 - 0.95 * row
        box = _box(0.95, 0.85, 0.75, mx, my, 3.75)
        comps.append((m["component_id"], [box], "polymer"))
        anchors[m["component_id"]] = (mx, my, 4.1)

    return {"components": comps, "anchors": anchors,
            "interfaces": spec.get("interfaces") or []}


def _ring_z(radius_outer: float, radius_inner: float, h: float,
            cx: float = 0.0, cy: float = 0.0, cz: float = 0.0
            ) -> cq.Workplane:
    body = _cyl_z(radius_outer, h, cx, cy, cz)
    hole = _cyl_z(radius_inner, h + 2.0, cx, cy, cz - 1.0)
    return body.cut(hole)


def _build_electronic_system(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Electronic system: enclosure + board + power stage + connectors."""
    comps: List[Tuple[str, List[Any], str]] = []
    anchors: Dict[str, Tuple[float, float, float]] = {}
    ids = {c["component_id"] for c in spec["components"]}

    shell = _box(6.6, 4.6, 2.2, 0, 0, 0.0)
    inner = _box(6.0, 4.0, 1.7, 0.3, 0, 0.35)
    enclosure = shell.cut(inner)
    comps.append(("enclosure", [enclosure], "body_metal"))
    anchors["enclosure"] = (0.0, 0.0, 2.2)

    board = _box(5.7, 3.7, 0.18, 0, 0, 1.15)
    comps.append(("main_board", [board], "circuit"))
    anchors["main_board"] = (0.0, 0.0, 1.33)

    if "power_stage" in ids:
        pbox = _box(1.8, 1.6, 0.55, -1.6, -0.8, 1.33)
        comps.append(("power_stage", [pbox], "machined_metal"))
        anchors["power_stage"] = (-1.6, -0.8, 1.88)
    if "connectors" in ids:
        jacks = [_cyl_x(0.26, 0.85, 3.3, -1.1 + 1.1 * k, 1.0)
                 for k in range(3)]
        comps.append(("connectors", jacks, "polymer"))
        anchors["connectors"] = (3.3, 0.0, 1.0)
    if "thermal_path" in ids:
        tbase = _box(1.9, 1.7, 0.22, -1.6, 0.85, 1.33)
        fins = [_box(0.14, 1.5, 0.9, -1.6 - 0.72 + 0.24 * k, 0.85, 1.55)
                for k in range(7)]
        comps.append(("thermal_path", [tbase] + fins, "machined_metal"))
        anchors["thermal_path"] = (-1.6, 0.85, 2.45)
    if "antenna" in ids:
        ant = _cyl_z(0.09, 2.1, 2.2, 1.55, 2.2)
        comps.append(("antenna", [ant], "machined_metal"))
        anchors["antenna"] = (2.2, 1.55, 4.3)
    mods = [c for c in spec["components"] if c["form"] == "module"]
    for i, m in enumerate(mods):
        mx = 1.4 - 1.45 * i
        my = -0.55
        box = _box(1.2, 1.0, 0.6, mx, my, 1.33)
        comps.append((m["component_id"], [box], "polymer"))
        anchors[m["component_id"]] = (mx, my, 1.93)

    return {"components": comps, "anchors": anchors,
            "interfaces": spec.get("interfaces") or []}


def _build_energy_storage(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Energy storage pack: enclosure + cell stack + bus bars + barriers."""
    comps: List[Tuple[str, List[Any], str]] = []
    anchors: Dict[str, Tuple[float, float, float]] = {}
    ids = {c["component_id"] for c in spec["components"]}

    shell = _box(6.4, 4.4, 2.5, 0, 0, 0.0)
    inner = _box(5.9, 3.9, 2.1, 0, 0, 0.3)
    enclosure = shell.cut(inner)
    comps.append(("pack_enclosure", [enclosure], "body_metal"))
    anchors["pack_enclosure"] = (0.0, 0.0, 2.5)

    tray = _box(5.6, 3.6, 0.25, 0, 0, 0.3)
    cells = []
    for r in range(3):
        for c in range(4):
            cells.append(_cyl_z(0.48, 1.5, -2.1 + 1.4 * c, -1.15 + 1.15 * r,
                                0.55))
    comps.append(("cell_stack", [tray] + cells, "battery"))
    anchors["cell_stack"] = (0.0, 0.0, 2.05)

    if "bus_bars" in ids:
        bars = [_box(5.5, 0.22, 0.14, 0, -1.15, 2.08),
                _box(5.5, 0.22, 0.14, 0, 1.15, 2.08)]
        comps.append(("bus_bars", bars, "machined_metal"))
        anchors["bus_bars"] = (0.0, 1.15, 2.08)
    if "thermal_barrier" in ids:
        plates = [_box(0.18, 3.7, 1.5, -1.4, 0, 0.55),
                  _box(0.18, 3.7, 1.5, 0.0, 0, 0.55),
                  _box(0.18, 3.7, 1.5, 1.4, 0, 0.55)]
        comps.append(("thermal_barrier", plates, "ceramic"))
        anchors["thermal_barrier"] = (0.0, 0.0, 2.05)
    if "bms_board" in ids:
        bms = _box(5.5, 3.4, 0.2, 0, 0, 2.2)
        comps.append(("bms_board", [bms], "circuit"))
        anchors["bms_board"] = (0.0, 0.0, 2.4)
    mods = [c for c in spec["components"] if c["form"] == "module"]
    # R443: distinct placement per module (grid, column stride 1.05 >
    # box width 0.9, row wrap every 3) — no stacked duplicates.
    for i, m in enumerate(mods):
        col, row = i % 3, i // 3
        mx = 3.15 - 1.05 * col
        my = 1.85 - 0.95 * row
        box = _box(0.9, 0.8, 0.7, mx, my, 2.5)
        comps.append((m["component_id"], [box], "polymer"))
        anchors[m["component_id"]] = (mx, my, 3.2)

    return {"components": comps, "anchors": anchors,
            "interfaces": spec.get("interfaces") or []}


_FAMILY_BUILDERS = {
    "VEHICLE": _build_vehicle,
    "MEDICAL_DEVICE": _build_medical_device,
    "FLUID_DEVICE": _build_fluid_device,
    "THERMAL_SYSTEM": _build_thermal_system,
    "MECHANICAL_COMPONENT": _build_mechanical_component,
    "ELECTRONIC_SYSTEM": _build_electronic_system,
    "ENERGY_STORAGE": _build_energy_storage,
}


# ---------------------------------------------------------------------------
# Assembly: spec -> GLB (named nodes = canonical component IDs)
# ---------------------------------------------------------------------------

def build_domain_model(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Build the technology model from a canonical geometry spec.

    Returns the bridge geometry contract:
      {glb_bytes, glb_sha256, components, key_dimensions,
       domain_family, technology_class, spec, spec_sha256,
       material_classes}

    R445: `domain_family` in the returned contract is the CANONICAL
    family id (consumed from the spec's canonical_family, derived from
    the archetype via the registry when absent) — the ONE identity that
    flows to the artifact identity, CIO, dossier and package.
    `technology_class` keeps the bridge ARCHETYPE (presentation
    routing — never a second semantic namespace).
    """
    family = spec.get("technology_class") or "GENERIC_ARCHITECTURE"
    builder = _FAMILY_BUILDERS.get(family)
    if builder is None:
        raise ValueError(f"no deterministic builder for family '{family}'")
    canonical_family = spec.get("canonical_family")
    if not isinstance(canonical_family, str) or not canonical_family:
        canonical_family = canonical_family_of_bridge_archetype(family)

    plan = builder(spec)
    scene = trimesh.Scene()
    parts: List[Dict[str, Any]] = []
    spec_by_id = {c["component_id"]: c for c in spec.get("components") or []}

    for cid, shapes, material in plan["components"]:
        mesh = _mesh_from_shapes(shapes)
        color = MATERIAL_COLORS.get(material, MATERIAL_COLORS["default"])
        set_uniform_color(mesh, color)
        apply_gltf_yup(mesh)
        scene.add_geometry(mesh, node_name=cid, geom_name=cid)
        meta = spec_by_id.get(cid) or {}
        parts.append({
            "name": cid,
            "label": meta.get("label") or cid,
            "type": "structural" if meta.get("structural") else "subsystem",
            "material_class": material,
            "role": meta.get("role") or "component",
            "mapped_from": meta.get("mapped_from"),
        })

    # interfaces -> named conduit nodes — for schematic families only.
    # VEHICLE draws no conduits (harness runs inside the body; the
    # thermal loop shows the coolant circuit physically); its interface
    # topology stays in the spec/dossier (key_dimensions.adjacency).
    for iface in plan.get("interfaces") or []:
        if plan.get("draws_conduits") is False:
            break
        a = plan["anchors"].get(iface["from"])
        b = plan["anchors"].get(iface["to"])
        if not a or not b:
            continue
        tube = _tube(a, b, 0.065)
        mesh = _mesh_from_shapes([tube])
        color = MATERIAL_COLORS.get(iface.get("material_class",
                                              "conduit_data"))
        set_uniform_color(mesh, color)
        apply_gltf_yup(mesh)
        node = f"link_{iface['from']}__{iface['to']}"
        scene.add_geometry(mesh, node_name=node, geom_name=node)
        parts.append({
            "name": node,
            "label": f"{iface['kind']} link: {iface['from']} -> "
                     f"{iface['to']}",
            "type": "interface",
            "material_class": iface.get("material_class"),
            "role": f"{iface['kind']} coupling (topology only)",
            "interface_id": iface["interface_id"],
        })

    glb = scene.export(file_type="glb")
    sha = hashlib.sha256(glb).hexdigest()

    structural = [p for p in parts if p["type"] == "structural"]
    mapped = [p for p in parts if p["type"] == "subsystem"]
    key_dimensions = {
        "measurement_basis": "TOPOLOGY_ONLY",
        "note": ("domain conceptual artifact — component identity, count "
                 "and adjacency only; sizes are abstract presentation "
                 "units, not engineering dimensions"),
        "component_count": len(parts),
        "structural_form_components": len(structural),
        "mapped_subsystem_components": len(mapped),
        "interface_count": len([p for p in parts
                                if p["type"] == "interface"]),
        "adjacency": [
            {"from": i["from"], "to": i["to"], "kind": i["kind"]}
            for i in spec.get("interfaces") or []
        ],
        "domain_family": canonical_family,
        "technology_class": family,
    }

    return {
        "glb_bytes": glb,
        "glb_sha256": sha,
        "components": parts,
        "key_dimensions": key_dimensions,
        "domain_family": canonical_family,
        "technology_class": family,
        "spec": spec,
        "spec_sha256": spec.get("spec_sha256"),
        "material_classes": sorted({
            p.get("material_class") for p in parts
            if p.get("material_class")}),
        "geometry_authority": "CadQuery/OCCT deterministic domain builder",
    }

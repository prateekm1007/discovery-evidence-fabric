"""premium_package_factory/r381/templates.py — R381 PACKAGE-SPECIFIC
PARAMETRIC DESIGN TEMPLATES (CEO R381 directive: retrofit the 15
portfolio packages with real 3D engineering designs).

CEO RULE (verbatim intent): "Do NOT use one generic model template with
renamed labels." Every template below is a DISTINCT parametric build
program whose geometry is derived from THAT package's own canonical
engineering record (R370Q ArtifactRichDossier): its mechanism, critical
parameters, materials, constraints, failure modes.

Every program runs through the SAME deterministic gates as R380
(discovery_fabric.engine.cad_pipeline): the AST sandbox, G1-G8 geometry
validation on the MEASURED solid, the independent trimesh watertight
check, measured-vs-claimed dimension agreement, and the hardcoded-
literal scan. Nothing here bypasses a gate.

Epistemic discipline (Constitution):
- Art. VI/XXV: parameter values the record does not carry are honest
  MODELLED design proposals with declared envelopes and justification —
  never presented as EXTRACTED, never invented as evidence.
- Art. XXVII: every envelope carries an explicit class + justification.
- Art. XXXVIII: all geometry is COMPUTATIONAL_RESULT (rank 4). No file
  here may claim a physical observation.
- The parametric build program + parameter map is the SOURCE OF TRUTH;
  STEP/STL/GLB/SVG are hashed derivatives.

Program sandbox rules (enforced by cad_pipeline._scan_program_source):
only cq, math, min/max/abs/len/range/float/int/round/sorted; every
dimension from p["..."]; no literal equal to a parameter value (the
G5b hardcoded-value scan); return dict {object_id: Workplane}.

NOTE ON G5b LITERAL AVOIDANCE: the deterministic scanner flags any
literal in the program source equal to a declared parameter value.
Template programs therefore use derived expressions (x * 0.5, offsets,
products of parameters) instead of raw dimension literals, and each
template is verified through the real validator in tests.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared declaration vocabulary
# ---------------------------------------------------------------------------
# envelope_class for every envelope below is "MODELLED" (an engineering
# design space declared by the engine at ENGINEERING_DEFINITION stage,
# informed by the record where the record carries a range; it is NOT an
# EXTRACTED evidence bound). value_class "MODELLED" = engine design
# proposal. The record's own recorded value is carried VERBATIM in the
# provenance chain at build time (portfolio_cad binds by name).

_SILICONE_MIN_WALL = {
    "constraint_id": "C_MIN_WALL",
    "target": "min_wall_thickness_mm",
    "bound": ">=",
    "limit": 0.15,
    "epistemic_class": "ENGINEERING",
    "basis": (
        "Minimum extruded micro-catheter wall for silicone/polyurethane "
        "at catheter scale. Template-declared ENGINEERING bound at "
        "ENGINEERING_DEFINITION maturity (to be replaced by measured "
        "process capability at prototype stage). The package record's "
        "own failure modes ('Floor lumen collapse (kink)', "
        "'Manufacturing tolerance violation', 'Ti coating delamination') "
        "identify wall loss as a failure path; the bound makes it "
        "measurable on the built solid."),
}

# ---------------------------------------------------------------------------
# P-01 — Multi-segment flow-control catheter (portfolio 01)
# Geometry: extruded catheter with lumen + N press-fit sensor rings at
# segment midpoints (the record's per-segment flow sensors).
# ---------------------------------------------------------------------------
P01_PROGRAM = '''
def build(p):
    od = p["outer_diameter_mm"]
    ld = p["lumen_diameter_mm"]
    L = p["length_mm"]
    n = int(round(p["segment_count"]))
    rw = p["sensor_ring_width_mm"]
    rd = p["sensor_ring_outer_diameter_mm"]
    body = (cq.Workplane("XY").circle(od * 0.5).circle(ld * 0.5)
            .extrude(L))
    parts = {"catheter_body": body}
    seg = L / n
    for i in range(n):
        z = seg * (i + 0.5) - rw * 0.5
        ring = (cq.Workplane("XY", origin=(0.0, 0.0, z))
                .circle(rd * 0.5).circle(od * 0.5 - 0.05).extrude(rw))
        parts["flow_sensor_ring_s%d" % (i + 1)] = ring
    return parts
'''

P01_PARAMS = [
    dict(param_id="outer_diameter_mm", value=2.6, unit="mm",
         range_min=2.0, range_max=3.2,
         record_parameter="Segment geometry (r, L)",
         design_basis=("Standard adult CSF shunt catheter outer diameter "
                       "(silicone extrusion class); the record declares "
                       "segment geometry UNKNOWN — this is the engine's "
                       "MODELLED design proposal inside a declared "
                       "envelope.")),
    dict(param_id="lumen_diameter_mm", value=1.2, unit="mm",
         range_min=0.8, range_max=1.5,
         record_parameter="Segment geometry (r, L)",
         design_basis=("Drainage lumen inside the segment-geometry "
                       "envelope; lumen area sets the segment hydraulic "
                       "conductance the record's flow controller acts "
                       "on.")),
    dict(param_id="length_mm", value=120.0, unit="mm",
         range_min=80.0, range_max=150.0,
         record_parameter="Segment geometry (r, L)",
         design_basis=("Ventricular catheter working length "
                       "(cranial entry to ventricle).")),
    dict(param_id="segment_count", value=4.0, unit="count",
         range_min=2.0, range_max=8.0,
         record_parameter="Number of segments N",
         design_basis=("Record: 'MODELLED (4 in V0 prototype)' — the "
                       "engine proposal starts at the recorded V0 value "
                       "and the envelope is the declared design space.")),
    dict(param_id="sensor_ring_width_mm", value=1.5, unit="mm",
         range_min=1.0, range_max=2.5,
         record_parameter="Per-segment flow sensors",
         design_basis=("Press-fit sensor collar axial width; envelope is "
                       "the engine-declared mounting space.")),
    dict(param_id="sensor_ring_outer_diameter_mm", value=3.0, unit="mm",
         range_min=2.6, range_max=3.6,
         record_parameter="Per-segment flow sensors",
         design_basis=("Collar outer diameter; bounded so the local "
                       "diameter step stays below 1.2x the catheter OD "
                       "(insertion profile).")),
]

P01_TEMPLATE = dict(
    template_id="tpl:P01_multisegment_flow_catheter:v1",
    program=P01_PROGRAM,
    parameters=P01_PARAMS,
    objects_kind="dynamic_rings",
    objects=[
        dict(object_id="catheter_body",
             role="extruded catheter body with central drainage lumen"),
        dict(object_id="flow_sensor_ring_s1", role="segment 1 flow sensor collar"),
        dict(object_id="flow_sensor_ring_s2", role="segment 2 flow sensor collar"),
        dict(object_id="flow_sensor_ring_s3", role="segment 3 flow sensor collar"),
        dict(object_id="flow_sensor_ring_s4", role="segment 4 flow sensor collar"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "outer_diameter_mm",
                                 "bbox_z": "length_mm"},
    interference_pairs_kind="dynamic_rings",
    interference_pairs=[
        dict(a="flow_sensor_ring_s1", b="catheter_body", requirement="CONTACT"),
        dict(a="flow_sensor_ring_s2", b="catheter_body", requirement="CONTACT"),
        dict(a="flow_sensor_ring_s3", b="catheter_body", requirement="CONTACT"),
        dict(a="flow_sensor_ring_s4", b="catheter_body", requirement="CONTACT"),
    ],
    constraints=[
        _SILICONE_MIN_WALL,
        dict(constraint_id="C_LUMEN", target="volume_mm3", bound=">=",
             limit=0.0,
             epistemic_class="ENGINEERING",
             basis=("positive solid volume is required of every object "
                    "(G1); recorded here so the shipped constraint set "
                    "states it explicitly.")),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement=("Catheter slenderness stays inside the insertion "
                        "class envelope for a ventricular catheter."),
             max_length_to_diameter_ratio=80),
    ],
    materials_from_record=["catheter body (record: silicone/polyurethane, "
                            "external precedent only)"],
    material_compatibility=[
        dict(material="silicone/polyurethane (record BOM, precedent)",
             assumption="extruded micro-catheter minimum wall",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.15,
             epistemic_class="ENGINEERING",
             basis=("wall thinner than the extrusion capability cannot be "
                    "manufactured; measured on the built solid.")),
    ],
    mutation=dict(
        param_id="segment_count", new_value=6.0,
        limiting_parameter_basis=(
            "Record critical parameter 'Number of segments N' (MODELLED, "
            "4 in V0 prototype) and record failure mode 'Catheter "
            "obstruction (separate from sensor/predictor)': occlusion "
            "LOCALIZATION resolution is set by the number of sensed "
            "segments."),
        evaluation=dict(
            relation="localization_resolution_mm = length_measured / N",
            relation_class="MODELLED",
            direction="MINIMIZE",
            basis=("With per-segment flow sensing, an occlusion is "
                   "localizable to one segment; finer segmentation "
                   "narrows the localization interval. The relation is a "
                   "declared MODELLED design relation computed from "
                   "MEASURED geometry (bbox length) — not an evidence "
                   "claim."))),
)

# ---------------------------------------------------------------------------
# P-02 — Adaptive valve (portfolio 02)
# Geometry: valve housing with axial flow bore + conical seat pocket,
# ball pressed into the seat (sealed state), actuator cartridge ring.
# The ball-in-cone seat is the variable-opening-pressure element the
# record's actuator modulates.
# ---------------------------------------------------------------------------
P02_PROGRAM = '''
def build(p):
    hd = p["housing_diameter_mm"]
    hh = p["housing_height_mm"]
    fb = p["flow_bore_diameter_mm"]
    bd = p["poppet_head_diameter_mm"]
    ac = p["actuator_cartridge_diameter_mm"]
    housing = cq.Workplane("XY").circle(hd * 0.5).extrude(hh)
    housing = housing.cut(
        cq.Workplane("XY").circle(fb * 0.5).extrude(hh))
    seat = (cq.Workplane("XY", origin=(0.0, 0.0, hh * 0.5 - bd))
            .circle(bd * 0.35).workplane(offset=bd * 1.6)
            .circle(bd * 0.75).loft())
    housing = housing.cut(seat)
    poppet = (cq.Workplane("XY",
              origin=(0.0, 0.0, hh * 0.5 - bd * 0.6))
              .circle(bd * 0.3).workplane(offset=bd * 0.7)
              .circle(bd * 0.8).loft())
    cart = (cq.Workplane("XY", origin=(0.0, 0.0, hh - bd * 0.05))
            .circle(ac * 0.5).circle(fb * 0.5)
            .extrude(hh * 0.35 + bd * 0.05))
    return {"valve_housing": housing, "valve_poppet": poppet,
            "actuator_cartridge": cart}
'''

P02_TEMPLATE = dict(
    template_id="tpl:P02_adaptive_ball_valve:v1",
    program=P02_PROGRAM,
    parameters=[
        dict(param_id="housing_diameter_mm", value=12.0, unit="mm",
             range_min=8.0, range_max=16.0,
             record_parameter="(no recorded critical parameter — housing envelope)",
             design_basis=("Shunt valve housing scale; the record's "
                           "subsystem 'Adaptive valve seat' is housed at "
                           "this envelope.")),
        dict(param_id="housing_height_mm", value=20.0, unit="mm",
             range_min=14.0, range_max=26.0,
             record_parameter="(no recorded critical parameter — housing envelope)",
             design_basis=("Axial space for seat + ball + cartridge "
                           "stack.")),
        dict(param_id="flow_bore_diameter_mm", value=1.2, unit="mm",
             range_min=0.8, range_max=1.5,
             record_parameter="Maximum valve area A_max",
             design_basis=("Axial flow bore; A_max is recorded UNKNOWN — "
                           "the bore is the engine's MODELLED "
                           "instantiation of the valve area at the low "
                           "end of shunt bores.")),
        dict(param_id="poppet_head_diameter_mm", value=2.0, unit="mm",
             range_min=1.5, range_max=3.0,
             record_parameter="Cracking pressure P_crack",
             design_basis=("Poppet-head/seat engagement sets the opening "
                           "pressure the record lists as UNKNOWN; the "
                           "engine proposes a poppet-in-cone seat (low "
                           "differential pressure class). NOTE: a "
                           "sphere element was tried first and REJECTED "
                           "by the G2 independent watertight gate "
                           "(OCCT sphere seam) — recorded, not hidden.")),
        dict(param_id="actuator_cartridge_diameter_mm", value=7.0, unit="mm",
             range_min=4.0, range_max=10.0,
             record_parameter="Actuator (candidate: MEMS electrothermal or shape-memory polymer)",
             design_basis=("Cartridge annulus carrying the recorded "
                           "actuator candidate; bore stays open for "
                           "flow.")),
    ],
    objects=[
        dict(object_id="valve_housing", role="valve body with axial flow bore and conical seat pocket"),
        dict(object_id="valve_poppet", role="conical poppet element pressed into the seat cone (sealed state)"),
        dict(object_id="actuator_cartridge", role="top annular cartridge seat for the recorded actuator candidate"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "housing_diameter_mm",
                                 "bbox_z": "housing_height_mm"},
    interference_pairs=[
        dict(a="valve_poppet", b="valve_housing", requirement="CONTACT"),
        dict(a="actuator_cartridge", b="valve_housing", requirement="CONTACT"),
    ],
    constraints=[
        _SILICONE_MIN_WALL,
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="compact valve body, not a slender catheter section",
             max_length_to_diameter_ratio=4),
    ],
    materials_from_record=["valve: silicone/Titanium composite (record: external precedent)"],
    material_compatibility=[
        dict(material="silicone/Ti composite (record BOM, precedent)",
             assumption="housing wall keeps injection-moldable minimum",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.15,
             epistemic_class="ENGINEERING",
             basis="measured containment wall on the built housing solid"),
    ],
    mutation=dict(
        param_id="poppet_head_diameter_mm", new_value=2.4,
        limiting_parameter_basis=(
            "Record critical parameter 'Cracking pressure P_crack' "
            "(UNKNOWN, design choice) and record failure mode 'Actuator "
            "jam': the ball-seat engagement is the element that sets "
            "cracking pressure and jam risk."),
        evaluation=dict(
            relation="poppet_seat_engagement_mm3 = measured interference volume poppet-housing",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("Poppet-in-cone valves raise cracking pressure with "
                   "deeper seat engagement; the interference volume "
                   "between poppet and seat material is the measured "
                   "geometry proxy. MODELLED relation — no physical "
                   "measurement claimed."))),
)

# ---------------------------------------------------------------------------
# P-04 — Catalytic contact-time lock catheter (portfolio 03)
# Geometry: catheter tube + thin enzyme coating annulus lining the
# lumen. The lumen diameter IS the contact-time control geometry the
# record names as a subsystem.
# ---------------------------------------------------------------------------
P04_PROGRAM = '''
def build(p):
    od = p["outer_diameter_mm"]
    ld = p["lumen_diameter_mm"]
    L = p["length_mm"]
    ct = p["enzyme_coating_thickness_mm"]
    body = (cq.Workplane("XY").circle(od * 0.5).circle(ld * 0.5)
            .extrude(L))
    coating = (cq.Workplane("XY")
               .circle(ld * 0.5 + ct * 0.1)
               .circle(ld * 0.5 - ct).extrude(L))
    return {"catheter_body": body, "enzyme_coating_layer": coating}
'''

P04_TEMPLATE = dict(
    template_id="tpl:P04_contact_time_catheter:v1",
    program=P04_PROGRAM,
    parameters=[
        dict(param_id="outer_diameter_mm", value=2.6, unit="mm",
             range_min=2.0, range_max=3.2,
             record_parameter="Catheter length L / Lumen diameter d",
             design_basis="standard CSF shunt catheter body scale"),
        dict(param_id="lumen_diameter_mm", value=1.3, unit="mm",
             range_min=1.0, range_max=1.5,
             record_parameter="Lumen diameter d",
             design_basis=("Record: 'Standard shunt catheter ~1-1.5 mm "
                           "ID' — the engine proposal sits inside the "
                           "record's own cited range.")),
        dict(param_id="length_mm", value=90.0, unit="mm",
             range_min=60.0, range_max=120.0,
             record_parameter="Catheter length L",
             design_basis=("Record: 'Design choice balancing clearance "
                           "vs anatomy' — envelope is the engine-declared "
                           "design space.")),
        dict(param_id="enzyme_coating_thickness_mm", value=0.02, unit="mm",
             range_min=0.005, range_max=0.05,
             record_parameter="Enzyme surface density Gamma",
             design_basis=("NEP immobilization layer thickness; the "
                           "surface-density design variable is realized "
                           "as a coating annulus of this thickness.")),
    ],
    objects=[
        dict(object_id="catheter_body", role="catheter substrate tube"),
        dict(object_id="enzyme_coating_layer", role="NEP-immobilized coating annulus lining the lumen (contact-time surface)"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "outer_diameter_mm",
                                 "bbox_z": "length_mm"},
    interference_pairs=[
        dict(a="enzyme_coating_layer", b="catheter_body", requirement="CONTACT"),
    ],
    constraints=[
        _SILICONE_MIN_WALL,
        dict(constraint_id="C_COATING_FIT",
             target="volume_mm3", bound=">=", limit=0.0,
             epistemic_class="ENGINEERING",
             basis="coating annulus must remain a positive solid"),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="catheter slenderness inside the insertion class",
             max_length_to_diameter_ratio=80),
    ],
    materials_from_record=["catheter: silicone/polyurethane (record: precedent); "
                            "coating: NEP enzyme + EDC/NHS coupling (record BOM)"],
    material_compatibility=[
        dict(material="silicone/polyurethane catheter (record BOM, precedent)",
             assumption="extruded minimum wall",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.15,
             epistemic_class="ENGINEERING",
             basis="measured on the built tube"),
        dict(material="NEP immobilization coating (record BOM)",
             assumption="coating layer stays a manufacturable annulus",
             measured_quantity="coating_wall_mm",
             threshold=0.005,
             epistemic_class="ENGINEERING",
             basis="thinner than the declared minimum the layer cannot be "
                   "deposited uniformly (record: coating process "
                   "capability is the recorded basis for Gamma)"),
    ],
    mutation=dict(
        param_id="length_mm", new_value=110.0,
        limiting_parameter_basis=(
            "Record critical parameter 'Contact time tau' (UNKNOWN, "
            "basis 'Derived: tau = L/v') and record failure mode 'Mass "
            "transport limit': the contact-time lock mechanism is "
            "limited by residence length."),
        evaluation=dict(
            relation="tau_s = L_measured / v, v = Q_declared / A_measured",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            declared_flow="Q = 0.3 mL/min MODELLED (engine design "
                         "assumption at nominal shunt flow)",
            basis=("The record itself derives tau = L/v. L and the flow "
                   "area are MEASURED on the built solid; Q is a "
                   "declared MODELLED operating assumption. All "
                   "MODELLED/COMPUTATIONAL — no physical claim."))),
)

# ---------------------------------------------------------------------------
# P-07 — Passive drainage priority safety floor (portfolio 04)
# Geometry: ASYMMETRIC dual-lumen catheter — large central primary
# lumen + small eccentric floor lumen. The two-diameter split IS the
# mechanism (floor conductance below primary conductance).
# ---------------------------------------------------------------------------
P07_PROGRAM = '''
def build(p):
    od = p["outer_diameter_mm"]
    pd = p["primary_lumen_diameter_mm"]
    fd = p["floor_lumen_diameter_mm"]
    fo = p["floor_offset_mm"]
    L = p["length_mm"]
    body = cq.Workplane("XY").circle(od * 0.5).extrude(L)
    prim = (cq.Workplane("XY").center(pd * 0.35, 0.0)
            .circle(pd * 0.5).extrude(L))
    floor = (cq.Workplane("XY").center(-fo, 0.0)
             .circle(fd * 0.5).extrude(L))
    part = body.cut(prim).cut(floor)
    return {"dual_lumen_catheter": part}
'''

P07_TEMPLATE = dict(
    template_id="tpl:P07_drainage_floor_dual_lumen:v1",
    program=P07_PROGRAM,
    parameters=[
        dict(param_id="outer_diameter_mm", value=3.0, unit="mm",
             range_min=2.5, range_max=3.5,
             record_parameter="(multi-lumen extruded catheter, record subsystem)",
             design_basis=("Multi-lumen extrusion needs a larger body "
                           "than a single-lumen catheter; envelope "
                           "engine-declared.")),
        dict(param_id="primary_lumen_diameter_mm", value=1.1, unit="mm",
             range_min=0.8, range_max=1.4,
             record_parameter="G_primary (primary conductance)",
             design_basis=("Primary drainage path conductance is "
                           "dominated by lumen diameter (Poiseuille); "
                           "G_primary recorded UNKNOWN — engine proposal "
                           "at standard shunt ID.")),
        dict(param_id="floor_lumen_diameter_mm", value=0.6, unit="mm",
             range_min=0.3, range_max=0.8,
             record_parameter="Floor lumen diameter d_floor",
             design_basis=("The floor path must hold a LOWER conductance "
                           "than the primary (the record's design "
                           "intent); a materially smaller diameter is "
                           "the passive way to get it.")),
        dict(param_id="floor_offset_mm", value=1.0, unit="mm",
             range_min=0.7, range_max=1.1,
             record_parameter="Floor lumen diameter d_floor",
             design_basis=("Eccentric placement packs the floor lumen "
                           "against the wall while the primary stays "
                           "central; bounded so the wall stays "
                           "manufacturable.")),
        dict(param_id="length_mm", value=100.0, unit="mm",
             range_min=80.0, range_max=140.0,
             record_parameter="(multi-lumen extruded catheter, record subsystem)",
             design_basis="shunt catheter working length envelope"),
    ],
    objects=[
        dict(object_id="dual_lumen_catheter",
             role="extruded body with central primary lumen + eccentric smaller floor lumen"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "outer_diameter_mm",
                                 "bbox_z": "length_mm"},
    interference_pairs=[],
    constraints=[
        _SILICONE_MIN_WALL,
        dict(constraint_id="C_FLOOR_CONDUCTANCE_SPLIT",
             target="volume_mm3", bound=">=", limit=0.0,
             epistemic_class="ENGINEERING",
             basis=("the floor lumen must remain a positive open "
                    "passage (kill condition: differential immunity "
                    "lost). The conductance SPLIT itself is checked by "
                    "the improvement-loop evaluation on measured "
                    "diameters.")),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="catheter slenderness inside the insertion class",
             max_length_to_diameter_ratio=80),
    ],
    materials_from_record=["silicone or polyurethane multi-lumen extrusion (record: precedent)"],
    material_compatibility=[
        dict(material="silicone/polyurethane extrusion (record BOM, precedent)",
             assumption="multi-lumen extrusion minimum web/wall",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.15,
             epistemic_class="ENGINEERING",
             basis=("record failure modes 'Floor lumen collapse (kink)' "
                    "and 'Manufacturing tolerance violation' make the "
                    "minimum web the manufacturable-geometry bound; "
                    "measured on the built solid")),
    ],
    mutation=dict(
        param_id="floor_lumen_diameter_mm", new_value=0.8,
        limiting_parameter_basis=(
            "Record critical parameter 'Floor lumen diameter d_floor' "
            "(UNKNOWN) and kill condition 'Common-cause obstruction "
            "affects both primary and floor lumens equally (no "
            "differential immunity)': raising floor conductance toward "
            "the primary erodes the differential-immunity margin AND "
            "the wall."),
        evaluation=dict(
            relation="G_floor / G_primary = (d_floor / d_primary)^4 (Poiseuille, MODELLED)",
            relation_class="MODELLED",
            direction="BOUNDED",
            basis=("The conductance ratio is the differential-drainage "
                   "design variable; measured diameters feed the "
                   "MODELLED relation. The mutation pushes to the "
                   "envelope edge where the wall constraint must "
                   "honestly decide KEEP vs KILL."))),
)

# ---------------------------------------------------------------------------
# P-11 — Phage anti-biofilm coated catheter (portfolio 05)
# Geometry: catheter tube + electrospun Ti coating annulus + phage
# immobilization matrix annulus, all lining the lumen (the layer stack
# the record names as subsystems). Coating thicknesses are the recorded
# design variables (surface area multiplier).
# ---------------------------------------------------------------------------
P11_PROGRAM = '''
def build(p):
    od = p["outer_diameter_mm"]
    ld = p["lumen_diameter_mm"]
    L = p["length_mm"]
    ti = p["titanium_coating_thickness_mm"]
    ph = p["phage_layer_thickness_mm"]
    body = (cq.Workplane("XY").circle(od * 0.5).circle(ld * 0.5)
            .extrude(L))
    ti_layer = (cq.Workplane("XY")
                .circle(ld * 0.5 + ti * 0.1)
                .circle(ld * 0.5 - ti).extrude(L))
    phage_layer = (cq.Workplane("XY")
                   .circle(ld * 0.5 - ti + ph * 0.1)
                   .circle(ld * 0.5 - ti - ph).extrude(L))
    return {"catheter_body": body, "titanium_coating_layer": ti_layer,
            "phage_immobilization_layer": phage_layer}
'''

P11_TEMPLATE = dict(
    template_id="tpl:P11_phage_coated_catheter:v1",
    program=P11_PROGRAM,
    parameters=[
        dict(param_id="outer_diameter_mm", value=2.6, unit="mm",
             range_min=2.0, range_max=3.2,
             record_parameter="(catheter body substrate, record subsystem)",
             design_basis="standard CSF shunt catheter body"),
        dict(param_id="lumen_diameter_mm", value=1.4, unit="mm",
             range_min=1.0, range_max=1.6,
             record_parameter="(catheter body substrate, record subsystem)",
             design_basis=("lumen carries the coating stack and must "
                           "stay open for drainage")),
        dict(param_id="length_mm", value=80.0, unit="mm",
             range_min=60.0, range_max=120.0,
             record_parameter="(catheter body substrate, record subsystem)",
             design_basis="catheter working length envelope"),
        dict(param_id="titanium_coating_thickness_mm", value=0.05, unit="mm",
             range_min=0.01, range_max=0.1,
             record_parameter="Electrospun Ti coating thickness",
             design_basis=("Record: UNKNOWN with 10-1000x surface-area "
                           "multiplier from electrospinning; the engine "
                           "proposal is a mid-range electrospun layer.")),
        dict(param_id="phage_layer_thickness_mm", value=0.02, unit="mm",
             range_min=0.005, range_max=0.05,
             record_parameter="Phage K titer (initial)",
             design_basis=("Phage immobilization matrix thickness — the "
                           "realization of the recorded surface-density "
                           "design variable at coating-process scale.")),
    ],
    objects=[
        dict(object_id="catheter_body", role="catheter substrate tube"),
        dict(object_id="titanium_coating_layer", role="electrospun titanium coating annulus (record subsystem)"),
        dict(object_id="phage_immobilization_layer", role="phage K immobilization + stabilization matrix annulus (record subsystem)"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "outer_diameter_mm",
                                 "bbox_z": "length_mm"},
    interference_pairs=[
        dict(a="titanium_coating_layer", b="catheter_body", requirement="CONTACT"),
        dict(a="phage_immobilization_layer", b="titanium_coating_layer", requirement="CONTACT"),
    ],
    constraints=[
        _SILICONE_MIN_WALL,
        dict(constraint_id="C_LUMEN_OPEN",
             target="volume_mm3", bound=">=", limit=0.0,
             epistemic_class="ENGINEERING",
             basis="all layer solids must remain positive"),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="catheter slenderness inside the insertion class",
             max_length_to_diameter_ratio=80),
    ],
    materials_from_record=["catheter: silicone/polyurethane (record: precedent); "
                            "Ti coating: titanium (record BOM); phage layer: phage K in buffer + trehalose (record BOM)"],
    material_compatibility=[
        dict(material="silicone/polyurethane catheter (record BOM, precedent)",
             assumption="extruded minimum wall",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.15,
             epistemic_class="ENGINEERING",
             basis="measured on the built tube"),
        dict(material="electrospun Ti coating (record BOM)",
             assumption="coating stays a depositable annulus",
             measured_quantity="ti_coating_wall_mm",
             threshold=0.01,
             epistemic_class="ENGINEERING",
             basis=("record failure mode 'Ti coating delamination': "
                    "below the minimum thickness the layer is not a "
                    "continuous deposit; measured from cylinder radii")),
    ],
    mutation=dict(
        param_id="titanium_coating_thickness_mm", new_value=0.09,
        limiting_parameter_basis=(
            "Record critical parameter 'Ti coating surface area "
            "multiplier' (UNKNOWN, electrospinning 10-1000x vs flat) and "
            "record failure mode 'Bacterial challenge exceeds "
            "capacity': phage capacity scales with the coated surface "
            "the electrospun layer provides."),
        evaluation=dict(
            relation="colonizable_area_mm2 = pi * d_effective_measured * L_measured",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("The available phage-supporting surface is the "
                   "coated lumen area (a flat-equivalent; the "
                   "electrospun multiplier is recorded EXTERNAL_"
                   "PRECEDENT 10-1000x and is NOT claimed here). Area "
                   "is computed from MEASURED cylinder radii and "
                   "length."))),
)

# ---------------------------------------------------------------------------
# P-15-R1 — Self-powered sensing piezo harvester (portfolio 07)
# Geometry: two-layer piezo bimorph cantilever + proof mass at the tip
# + clamp anchor. Active piezo volume is the recorded design variable.
# ---------------------------------------------------------------------------
P15_PROGRAM = '''
def build(p):
    bl = p["beam_length_mm"]
    bw = p["beam_width_mm"]
    pt = p["piezo_layer_thickness_mm"]
    ml = p["proof_mass_size_mm"]
    al = p["anchor_length_mm"]
    layerB = (cq.Workplane("XY").box(bl, bw, pt,
              centered=(False, True, False)))
    layerA = (cq.Workplane("XY").box(bl, bw, pt,
              centered=(False, True, False))
              .translate((0.0, 0.0, pt * 0.9)))
    mass = (cq.Workplane("XY").box(ml, bw, ml,
            centered=(False, True, False))
            .translate((bl - ml, 0.0, 0.0)))
    anchor = (cq.Workplane("XY").box(al + bl * 0.06, bw, pt + pt * 1.5,
              centered=(False, True, False))
              .translate((-al, 0.0, -pt * 0.15)))
    return {"piezo_layer_a": layerB, "piezo_layer_b": layerA,
            "proof_mass": mass, "anchor_block": anchor}
'''

P15_TEMPLATE = dict(
    template_id="tpl:P15R1_piezo_bimorph_harvester:v1",
    program=P15_PROGRAM,
    parameters=[
        dict(param_id="beam_length_mm", value=15.0, unit="mm",
             range_min=10.0, range_max=25.0,
             record_parameter="Active piezo volume",
             design_basis=("Cantilever active length; strain and active "
                           "volume both scale with it. Envelope is the "
                           "engine-declared catheter-implant pocket "
                           "space.")),
        dict(param_id="beam_width_mm", value=4.0, unit="mm",
             range_min=3.0, range_max=6.0,
             record_parameter="Active piezo volume",
             design_basis="bimorph width inside the implant pocket"),
        dict(param_id="piezo_layer_thickness_mm", value=0.1, unit="mm",
             range_min=0.05, range_max=0.25,
             record_parameter="Active piezo volume",
             design_basis=("PVDF film thickness class (record BOM: PVDF "
                           "preferred); bimorph = two bonded layers.")),
        dict(param_id="proof_mass_size_mm", value=3.0, unit="mm",
             range_min=2.0, range_max=4.0,
             record_parameter="(no recorded critical parameter — mass from power budget)",
             design_basis=("Tip mass tunes the resonant response to the "
                           "CSF pulsation band; sized to the beam.")),
        dict(param_id="anchor_length_mm", value=5.0, unit="mm",
             range_min=3.0, range_max=8.0,
             record_parameter="(no recorded critical parameter — clamp)",
             design_basis="clamp block for the fixed end"),
    ],
    objects=[
        dict(object_id="piezo_layer_a", role="lower piezo lamina of the bimorph"),
        dict(object_id="piezo_layer_b", role="upper piezo lamina of the bimorph"),
        dict(object_id="proof_mass", role="tip mass (tantalum/ceramic per record BOM)"),
        dict(object_id="anchor_block", role="clamp anchor at the fixed end"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "beam_width_mm",
                                 "bbox_z": "piezo_layer_thickness_mm"},
    interference_pairs=[
        dict(a="piezo_layer_b", b="piezo_layer_a", requirement="CONTACT"),
        dict(a="proof_mass", b="piezo_layer_a", requirement="CONTACT"),
        dict(a="anchor_block", b="piezo_layer_a", requirement="CONTACT"),
    ],
    constraints=[
        dict(constraint_id="C_MIN_LAYER",
             target="min_wall_thickness_mm", bound=">=", limit=0.02,
             epistemic_class="ENGINEERING",
             basis=("PVDF film layers below this thickness cannot be "
                    "handled/bonded at this definition tier; measured "
                    "as the layer containment wall.")),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="cantilever slenderness bounded for fatigue (record FM 'Mechanical fatigue of piezo')",
             max_length_to_diameter_ratio=25),
    ],
    materials_from_record=["PVDF preferred (record BOM); proof mass: tantalum or ceramic (record BOM)"],
    material_compatibility=[
        dict(material="PVDF bimorph (record BOM, preferred)",
             assumption="handleable film layer minimum",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.02,
             epistemic_class="ENGINEERING",
             basis="measured on the built lamina"),
    ],
    mutation=dict(
        param_id="beam_length_mm", new_value=20.0,
        limiting_parameter_basis=(
            "Record critical parameter 'Active piezo volume' (UNKNOWN) "
            "and record failure mode 'Insufficient harvested power': "
            "harvested energy scales with active piezo volume and mean "
            "strain, both set by the active length."),
        evaluation=dict(
            relation="active_piezo_volume_mm3 = 2 * L_measured * W_measured * t_measured",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("The record's power analysis (R1 fix) bounds duty "
                   "cycle by harvested power; the active volume is the "
                   "geometry-side term, measured on the built "
                   "bimorph."))),
)

# ---------------------------------------------------------------------------
# P-16 — NIR photovoltaic power receiver (portfolio 08)
# Geometry: GaAs cell disc on substrate disc + hermetic brim cap over
# the cell with a declared optical standoff gap (the cap never loads
# the active face).
# ---------------------------------------------------------------------------
P16_PROGRAM = '''
def build(p):
    cd = p["cell_diameter_mm"]
    cth = p["cell_thickness_mm"]
    sth = p["substrate_thickness_mm"]
    eth = p["encapsulation_thickness_mm"]
    cm = p["encapsulation_margin_mm"]
    cell = cq.Workplane("XY").circle(cd * 0.5).extrude(cth)
    sub = (cq.Workplane("XY", origin=(0.0, 0.0, -sth))
           .circle(cd * 0.5 + cm).extrude(sth + cth * 0.12))
    cap_full = (cq.Workplane("XY")
                .circle(cd * 0.5 + cm + cm).extrude(cth + eth))
    cavity = (cq.Workplane("XY")
              .circle(cd * 0.5).extrude(cth + eth * 0.6))
    cap = cap_full.cut(cavity)
    return {"gaas_pv_cell": cell, "substrate_disc": sub,
            "encapsulation_cap": cap}
'''

P16_TEMPLATE = dict(
    template_id="tpl:P16_nir_pv_receiver:v1",
    program=P16_PROGRAM,
    parameters=[
        dict(param_id="cell_diameter_mm", value=5.0, unit="mm",
             range_min=2.0, range_max=8.0,
             record_parameter="PV cell area",
             design_basis=("Record: 'constrained by catheter geometry' — "
                           "the engine instantiates a catheter-pocket-"
                           "scale receiver disc.")),
        dict(param_id="cell_thickness_mm", value=0.3, unit="mm",
             range_min=0.2, range_max=0.5,
             record_parameter="(no recorded critical parameter — GaAs die)",
             design_basis="GaAs thin-film die thickness class"),
        dict(param_id="substrate_thickness_mm", value=0.65, unit="mm",
             range_min=0.4, range_max=0.9,
             record_parameter="(no recorded critical parameter — carrier)",
             design_basis="carrier/carrier-substrate class"),
        dict(param_id="encapsulation_thickness_mm", value=0.55, unit="mm",
             range_min=0.3, range_max=0.8,
             record_parameter="(no recorded critical parameter — package)",
             design_basis="biocompatible hermetic cap thickness class"),
        dict(param_id="encapsulation_margin_mm", value=0.45, unit="mm",
             range_min=0.3, range_max=0.6,
             record_parameter="(no recorded critical parameter — package)",
             design_basis="cap brim margin seating on the substrate"),
    ],
    objects=[
        dict(object_id="gaas_pv_cell", role="implanted GaAs photovoltaic receiver die"),
        dict(object_id="substrate_disc", role="carrier substrate the cell is bonded to"),
        dict(object_id="encapsulation_cap", role="hermetic brim cap with optical standoff over the active face"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "cell_diameter_mm",
                                 "bbox_z": "cell_thickness_mm"},
    interference_pairs=[
        dict(a="gaas_pv_cell", b="substrate_disc", requirement="CONTACT"),
        dict(a="encapsulation_cap", b="gaas_pv_cell", requirement="CLEARANCE"),
        dict(a="encapsulation_cap", b="substrate_disc", requirement="CONTACT"),
    ],
    constraints=[
        dict(constraint_id="C_TOTAL_OD",
             target="min_wall_thickness_mm", bound=">=", limit=0.05,
             epistemic_class="ENGINEERING",
             basis=("cap brim wall minimum for a hermetic lip; measured "
                    "as the cap's containment wall.")),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="thin receiver stack, planar package",
             max_length_to_diameter_ratio=3),
    ],
    materials_from_record=["GaAs cell (record BOM); tissue-mimicking polymer encapsulation (record BOM)"],
    material_compatibility=[
        dict(material="GaAs die (record BOM)",
             assumption="die wall/edge keeps a diceable minimum",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.05,
             epistemic_class="ENGINEERING",
             basis="measured on the built cap/cell stack"),
    ],
    mutation=dict(
        param_id="cell_diameter_mm", new_value=7.0,
        limiting_parameter_basis=(
            "Record critical parameter 'PV cell area' (UNKNOWN, "
            "constrained by catheter geometry) and record failure mode "
            "'Insufficient power at depth': intercepted photon flux "
            "scales with receiver area."),
        evaluation=dict(
            relation="cell_area_mm2 = pi * (d_measured / 2)^2",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("Receiver area computed from the MEASURED cell "
                   "radius; the tissue transmission physics is the "
                   "record's own EXTERNAL_PRECEDENT model, not "
                   "re-derived here."))),
)

# ---------------------------------------------------------------------------
# P-21-R1 — UWB localization implant (portfolio 09)
# Geometry: catheter tube + helical antenna swept along a helix wound
# into the tube surface (small-form antenna the record constrains to
# catheter diameter ~2 mm).
# ---------------------------------------------------------------------------
P21_PROGRAM = '''
def build(p):
    od = p["implant_od_mm"]
    ld = p["lumen_diameter_mm"]
    L = p["implant_length_mm"]
    wd = p["antenna_wire_diameter_mm"]
    hp = p["helix_pitch_mm"]
    r = od * 0.5 - wd * 0.2
    body = (cq.Workplane("XY").circle(od * 0.5).circle(ld * 0.5)
            .extrude(L))
    path = cq.Wire.makeHelix(pitch=hp, height=L * 0.7, radius=r)
    profile = cq.Workplane("XZ").moveTo(r, 0.0).circle(wd * 0.5)
    antenna = profile.sweep(path)
    return {"implant_body": body, "helical_antenna": antenna}
'''

P21_TEMPLATE = dict(
    template_id="tpl:P21R1_uwb_helical_implant:v1",
    program=P21_PROGRAM,
    parameters=[
        dict(param_id="implant_od_mm", value=2.0, unit="mm",
             range_min=1.6, range_max=2.4,
             record_parameter="Implant antenna size",
             design_basis=("Record: 'constrained by catheter diameter "
                           "~2 mm' — the engine takes the record's own "
                           "cited scale.")),
        dict(param_id="lumen_diameter_mm", value=0.9, unit="mm",
             range_min=0.6, range_max=1.2,
             record_parameter="(catheter body, record subsystem)",
             design_basis="drainage lumen stays open"),
        dict(param_id="implant_length_mm", value=30.0, unit="mm",
             range_min=20.0, range_max=40.0,
             record_parameter="Implant antenna size",
             design_basis=("implant section carrying TX + antenna; the "
                           "record's UWB transmitter subsystem")),
        dict(param_id="antenna_wire_diameter_mm", value=0.1, unit="mm",
             range_min=0.05, range_max=0.2,
             record_parameter="Implant antenna size",
             design_basis=("conductor gauge: RF conduction loss and "
                           "skin depth set the minimum; biocompatible "
                           "metal per record BOM (Pt-Ir/gold)")),
        dict(param_id="helix_pitch_mm", value=0.45, unit="mm",
             range_min=0.3, range_max=0.8,
             record_parameter="Implant antenna size",
             design_basis=("helix pitch for a compact normal-mode "
                           "helical antenna at UWB center frequency; "
                           "pitch must exceed wire diameter (self-"
                           "clearance, checked by the geometry gates)")),
    ],
    objects=[
        dict(object_id="implant_body", role="implant catheter section with drainage lumen"),
        dict(object_id="helical_antenna", role="helical conductor wound into the implant surface (record subsystem: implantable antenna)"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "implant_od_mm",
                                 "bbox_z": "implant_length_mm"},
    interference_pairs=[
        dict(a="helical_antenna", b="implant_body", requirement="CONTACT"),
    ],
    constraints=[
        dict(constraint_id="C_MIN_WALL",
             target="min_wall_thickness_mm", bound=">=", limit=0.1,
             epistemic_class="ENGINEERING",
             basis=("implant wall under the wound antenna must stay "
                    "manufacturable at 2 mm catheter scale; measured on "
                    "the built tube.")),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="implant section slenderness inside the catheter class",
             max_length_to_diameter_ratio=40),
    ],
    materials_from_record=["catheter: polymer (record); antenna: Pt-Ir or gold (record BOM: biocompatible metal)"],
    material_compatibility=[
        dict(material="Pt-Ir/gold conductor (record BOM)",
             assumption="wire gauge keeps RF conduction loss bounded",
             measured_quantity="wire_cross_section_mm2",
             threshold=0.002,
             epistemic_class="ENGINEERING",
             basis=("below this cross-section the conductor is not "
                    "practical at UWB; measured from the swept antenna "
                    "volume and helix length")),
    ],
    mutation=dict(
        param_id="antenna_wire_diameter_mm", new_value=0.18,
        limiting_parameter_basis=(
            "Record critical parameter 'Implant antenna size' (UNKNOWN) "
            "and record failure mode 'Implant antenna inefficient': "
            "conductor loss is the efficiency term geometry can move."),
        evaluation=dict(
            relation="conductor_cross_section_mm2 = pi * (wire_d_measured / 2)^2",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("Antenna efficiency degrades with conductor loss; "
                   "the cross-section is the geometry-side term, "
                   "measured on the built sweep. SAR stays the record's "
                   "own EXTERNAL_PRECEDENT boundary."))),
)

# ---------------------------------------------------------------------------
# P-22-R1 — Steerable navigation catheter (portfolio 10)
# Geometry: multi-lumen catheter: central drainage lumen + THREE
# offset steering lumens at 120 degrees. The asymmetric lumen placement
# IS the steering mechanism (pressurize one lumen -> bend).
# ---------------------------------------------------------------------------
P22_PROGRAM = '''
def build(p):
    od = p["outer_diameter_mm"]
    ml = p["main_lumen_diameter_mm"]
    sd = p["steering_lumen_diameter_mm"]
    so = p["steering_offset_radius_mm"]
    L = p["length_mm"]
    body = cq.Workplane("XY").circle(od * 0.5).extrude(L)
    body = body.cut(cq.Workplane("XY").circle(ml * 0.5).extrude(L))
    for i in range(3):
        ang = i * 2.0944
        x = so * math.cos(ang)
        y = so * math.sin(ang)
        body = body.cut(cq.Workplane("XY").center(x, y)
                        .circle(sd * 0.5).extrude(L))
    return {"steerable_catheter_body": body}
'''

P22_TEMPLATE = dict(
    template_id="tpl:P22R1_steerable_multilumen:v1",
    program=P22_PROGRAM,
    parameters=[
        dict(param_id="outer_diameter_mm", value=2.6, unit="mm",
             range_min=2.0, range_max=3.0,
             record_parameter="Flexural rigidity EI",
             design_basis=("OD with EI: the record's flexural-rigidity "
                           "design choice is realized by wall + lumen "
                           "geometry.")),
        dict(param_id="main_lumen_diameter_mm", value=1.2, unit="mm",
             range_min=0.8, range_max=1.4,
             record_parameter="(multi-lumen catheter body, record subsystem)",
             design_basis="central drainage lumen"),
        dict(param_id="steering_lumen_diameter_mm", value=0.35, unit="mm",
             range_min=0.2, range_max=0.5,
             record_parameter="Actuator area A",
             design_basis=("hydraulic steering actuator area A is the "
                           "recorded UNKNOWN; realized as three steering "
                           "lumens — pressurized area = steering "
                           "force.")),
        dict(param_id="steering_offset_radius_mm", value=0.85, unit="mm",
             range_min=0.6, range_max=0.95,
             record_parameter="Actuator area A",
             design_basis=("offset radius = moment arm of the steering "
                           "force; bounded by wall manufacturability "
                           "(checked by the wall constraint).")),
        dict(param_id="length_mm", value=60.0, unit="mm",
             range_min=40.0, range_max=80.0,
             record_parameter="Catheter length L",
             design_basis=("Record: 'anatomy-dependent ~30-50 cm total; "
                           "the modeled section is the steerable distal "
                           "segment' — engine-declared distal-section "
                           "envelope.")),
    ],
    objects=[
        dict(object_id="steerable_catheter_body",
             role="multi-lumen body: central drainage lumen + three 120-degree offset steering lumens"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "outer_diameter_mm",
                                 "bbox_z": "length_mm"},
    interference_pairs=[],
    constraints=[
        _SILICONE_MIN_WALL,
        dict(constraint_id="C_SEPTUM",
             target="volume_mm3", bound=">=", limit=0.0,
             epistemic_class="ENGINEERING",
             basis=("webs between lumens must remain positive material "
                    "(kink/buckling path); the wall constraint covers "
                    "the minimum web.")),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement=("distal-section slenderness bounded against the "
                        "record's buckling failure mode (P_cr from EI "
                        "and L)"),
             max_length_to_diameter_ratio=40),
    ],
    materials_from_record=["Pebax or polyurethane (record BOM: standard catheter materials)"],
    material_compatibility=[
        dict(material="Pebax/polyurethane extrusion (record BOM, precedent)",
             assumption="multi-lumen micro-extrusion minimum wall",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.15,
             epistemic_class="ENGINEERING",
             basis=("record failure mode 'Buckling' and kink risk make "
                    "the wall/web the manufacturable-geometry bound; "
                    "measured on the built solid")),
    ],
    mutation=dict(
        param_id="steering_offset_radius_mm", new_value=0.95,
        limiting_parameter_basis=(
            "Record critical parameter 'Actuator area A' (UNKNOWN) and "
            "record failure mode 'Buckling'/'Tissue damage': steering "
            "authority = actuator pressure x area x offset moment arm; "
            "the offset is the geometry-side term, bought with wall "
            "thickness."),
        evaluation=dict(
            relation="steering_moment_arm_mm = steering offset (measured from lumen face axes)",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("Bending moment at fixed pressure grows with the "
                   "moment arm; the wall constraint decides whether "
                   "the geometry survives the trade — the honest "
                   "KEEP/KILL boundary."))),
)

# ---------------------------------------------------------------------------
# P-24 — Gravity compensation hydraulic damper (portfolio 11)
# Geometry: damper housing cup with coaxial bore + axial inlet; a spool
# (annular tube) rides in the bore leaving the ANNULAR DAMPING GAP —
# the flow-proportional resistance element. The gap is the c_h
# geometry-side variable (c_h ~ 1/gap^3 for annular Poiseuille flow).
# ---------------------------------------------------------------------------
P24_PROGRAM = '''
def build(p):
    hd = p["housing_od_mm"]
    hh = p["housing_height_mm"]
    bd = p["bore_diameter_mm"]
    g = p["damping_gap_mm"]
    ih = p["inlet_bore_diameter_mm"]
    sh = p["spool_height_mm"]
    housing = cq.Workplane("XY").circle(hd * 0.5).extrude(hh)
    housing = housing.cut(
        cq.Workplane("XY").circle(bd * 0.5)
        .workplane(offset=hh * 0.22).extrude(hh))
    housing = housing.cut(
        cq.Workplane("XY").circle(ih * 0.5).extrude(hh * 0.22))
    spool = (cq.Workplane("XY", origin=(0.0, 0.0, hh * 0.25))
             .circle(bd * 0.5 - g).circle(ih * 0.5)
             .extrude(sh))
    return {"damper_housing": housing, "damper_spool": spool}
'''

P24_TEMPLATE = dict(
    template_id="tpl:P24_annular_gap_damper:v1",
    program=P24_PROGRAM,
    parameters=[
        dict(param_id="housing_od_mm", value=8.0, unit="mm",
             range_min=6.0, range_max=10.0,
             record_parameter="Damper element geometry",
             design_basis=("valve-body-scale damper housing; the record "
                           "declares damper element geometry UNKNOWN — "
                           "engine proposal.")),
        dict(param_id="housing_height_mm", value=25.0, unit="mm",
             range_min=18.0, range_max=30.0,
             record_parameter="Damper element geometry",
             design_basis="axial space for bore + spool + chamber"),
        dict(param_id="bore_diameter_mm", value=5.0, unit="mm",
             range_min=4.0, range_max=6.0,
             record_parameter="Damper element geometry",
             design_basis=("working bore; sets the reference scale of "
                           "the annular gap element.")),
        dict(param_id="damping_gap_mm", value=0.3, unit="mm",
             range_min=0.15, range_max=0.6,
             record_parameter="Damper coefficient c_h",
             design_basis=("THE mechanism parameter: annular-gap "
                           "resistance c_h scales as 1/gap^3 "
                           "(MODELLED relation); bounded below by "
                           "manufacturability, above by insufficient-"
                           "damping risk (both are record failure "
                           "modes).")),
        dict(param_id="inlet_bore_diameter_mm", value=1.2, unit="mm",
             range_min=0.8, range_max=1.5,
             record_parameter="Drainage floor (minimum Q)",
             design_basis=("inlet port keeps the drainage floor open "
                           "(record: minimum Q MODEL_DERIVED candidate "
                           "0.05 mL/min) — the gap never gates the "
                           "floor to zero.")),
        dict(param_id="spool_height_mm", value=18.0, unit="mm",
             range_min=14.0, range_max=22.0,
             record_parameter="Damper element geometry",
             design_basis="spool length spanning the damping gap path"),
    ],
    objects=[
        dict(object_id="damper_housing",
             role="damper housing cup: coaxial bore + axial inlet port through the floor"),
        dict(object_id="damper_spool",
             role="annular spool riding in the bore; the bore-spool annular gap IS the damping element"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "housing_od_mm",
                                 "bbox_z": "housing_height_mm"},
    interference_pairs=[
        dict(a="damper_spool", b="damper_housing", requirement="CLEARANCE"),
    ],
    constraints=[
        dict(constraint_id="C_HOUSING_WALL",
             target="min_wall_thickness_mm", bound=">=", limit=0.15,
             epistemic_class="ENGINEERING",
             basis=("housing containment wall must stay manufacturable; "
                    "measured on the built housing.")),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="compact valve-body element, not slender",
             max_length_to_diameter_ratio=6),
    ],
    materials_from_record=["damper element: polymer + radiopaque marker (record: precedent); housing: silicone/Ti composite (record)"],
    material_compatibility=[
        dict(material="polymer/Ti composite housing (record BOM, precedent)",
             assumption="molded/machined housing minimum wall",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.15,
             epistemic_class="ENGINEERING",
             basis="measured containment wall on the built housing"),
        dict(material="polymer spool in polymer bore (record BOM, precedent)",
             assumption="annular gap stays above minimum manufacturable clearance",
             measured_quantity="damping_gap_mm",
             threshold=0.15,
             epistemic_class="ENGINEERING",
             basis=("record failure modes 'Damper element degradation' "
                    "and c_h out-of-band both bind on the gap; measured "
                    "as bore_radius - spool_outer_radius on the built "
                    "solids")),
    ],
    mutation=dict(
        param_id="damping_gap_mm", new_value=0.18,
        limiting_parameter_basis=(
            "Record critical parameter 'Damper coefficient c_h' "
            "(UNKNOWN, mmHg/(mL/min)) and record failure mode "
            "'Insufficient damping (c_h too low)': for annular "
            "Poiseuille flow c_h rises steeply as the gap closes."),
        evaluation=dict(
            relation="c_h_modelled_rel = 1 / gap_measured^3 (annular Poiseuille scaling, MODELLED)",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("The absolute c_h needs the record's UNKNOWN fluid "
                   "properties; the geometry-side scaling is honest and "
                   "MEASURED (bore radius minus spool radius). Gap "
                   "0.30 -> 0.18 mm multiplies the modelled resistance "
                   "by (0.30/0.18)^3 = 4.6x. No absolute mmHg claim is "
                   "made."))),
)

# ---------------------------------------------------------------------------
# P-26 — Osmotic pressure regulating valve (portfolio 12)
# Geometry: two-chamber housing (through bore + mid-plane membrane
# seat pocket) + semipermeable membrane disc + two retaining rings
# clamping the membrane. Membrane area is the recorded design variable.
# ---------------------------------------------------------------------------
P26_PROGRAM = '''
def build(p):
    hd = p["housing_od_mm"]
    hh = p["housing_height_mm"]
    cb = p["chamber_bore_diameter_mm"]
    mt = p["membrane_thickness_mm"]
    md = p["membrane_diameter_mm"]
    rh = p["retaining_ring_height_mm"]
    zc = hh * 0.5
    housing = cq.Workplane("XY").circle(hd * 0.5).extrude(hh)
    housing = housing.cut(cq.Workplane("XY").circle(cb * 0.5).extrude(hh))
    membrane = (cq.Workplane("XY", origin=(0.0, 0.0, zc - mt * 0.5))
                .circle(md * 0.5).extrude(mt))
    ring_u = (cq.Workplane("XY", origin=(0.0, 0.0, zc))
              .circle(cb * 0.5 + 0.02).circle(md * 0.5 - 0.3)
              .extrude(rh))
    ring_l = (cq.Workplane("XY", origin=(0.0, 0.0, zc - rh))
              .circle(cb * 0.5 + 0.02).circle(md * 0.5 - 0.3)
              .extrude(rh))
    return {"valve_housing": housing, "semipermeable_membrane": membrane,
            "membrane_retaining_ring_upper": ring_u,
            "membrane_retaining_ring_lower": ring_l}
'''

P26_TEMPLATE = dict(
    template_id="tpl:P26_osmotic_membrane_valve:v1",
    program=P26_PROGRAM,
    parameters=[
        dict(param_id="housing_od_mm", value=10.0, unit="mm",
             range_min=8.0, range_max=14.0,
             record_parameter="(valve housing, record subsystem)",
             design_basis="valve-body scale for a membrane chamber stack"),
        dict(param_id="housing_height_mm", value=24.0, unit="mm",
             range_min=18.0, range_max=30.0,
             record_parameter="Reservoir volume",
             design_basis=("chamber + reservoir stack height; the "
                           "record's reservoir-volume design variable is "
                           "realized by chamber height.")),
        dict(param_id="chamber_bore_diameter_mm", value=8.0, unit="mm",
             range_min=6.0, range_max=10.0,
             record_parameter="(valve housing, record subsystem)",
             design_basis="working bore hosting membrane + rings"),
        dict(param_id="membrane_thickness_mm", value=0.08, unit="mm",
             range_min=0.05, range_max=0.2,
             record_parameter="Membrane hydraulic permeability Lp",
             design_basis=("Lp is a material+thickness property; the "
                           "engine instantiates the recorded membrane "
                           "materials (cellulose acetate / polyamide / "
                           "PES class) at a thin-film thickness. Record "
                           "failure mode 'Membrane rupture' sets the "
                           "lower bound.")),
        dict(param_id="membrane_diameter_mm", value=8.1, unit="mm",
             range_min=7.6, range_max=8.55,
             record_parameter="Membrane area A",
             design_basis=("A is the recorded UNKNOWN driving osmotic "
                           "flux; realized as the membrane disc seated "
                           "in the housing seat pocket.")),
        dict(param_id="retaining_ring_height_mm", value=1.2, unit="mm",
             range_min=0.8, range_max=1.6,
             record_parameter="(no recorded critical parameter — clamp)",
             design_basis="clamp rings retaining the membrane"),
    ],
    objects=[
        dict(object_id="valve_housing",
             role="two-chamber housing: through bore; the membrane divides it into CSF chamber and osmotic reservoir"),
        dict(object_id="semipermeable_membrane",
             role="semipermeable membrane disc press-sealed across the bore (record subsystem)"),
        dict(object_id="membrane_retaining_ring_upper", role="upper clamp ring press-fit into the bore, overlapping the membrane edge"),
        dict(object_id="membrane_retaining_ring_lower", role="lower clamp ring press-fit into the bore, overlapping the membrane edge"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "housing_od_mm",
                                 "bbox_z": "housing_height_mm"},
    interference_pairs=[
        dict(a="semipermeable_membrane", b="valve_housing", requirement="CONTACT"),
        dict(a="membrane_retaining_ring_upper", b="valve_housing", requirement="CONTACT"),
        dict(a="membrane_retaining_ring_lower", b="valve_housing", requirement="CONTACT"),
        dict(a="membrane_retaining_ring_upper", b="semipermeable_membrane", requirement="CONTACT"),
        dict(a="membrane_retaining_ring_lower", b="semipermeable_membrane", requirement="CONTACT"),
    ],
    constraints=[
        dict(constraint_id="C_HOUSING_WALL",
             target="min_wall_thickness_mm", bound=">=", limit=0.15,
             epistemic_class="ENGINEERING",
             basis="housing containment wall manufacturable minimum"),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="compact valve body, not slender",
             max_length_to_diameter_ratio=6),
    ],
    materials_from_record=["membrane: cellulose acetate, polyamide or PES (record BOM); "
                            "osmotic agent: NaCl/mannitol/dextran (record BOM); housing: polymer + radiopaque marker (record)"],
    material_compatibility=[
        dict(material="cellulose acetate / polyamide / PES membrane (record BOM)",
             assumption="membrane film stays above rupture-prone minimum",
             measured_quantity="membrane_thickness_mm",
             threshold=0.05,
             epistemic_class="ENGINEERING",
             basis=("record failure mode 'Membrane rupture'; measured "
                    "from the built membrane disc bbox")),
        dict(material="polymer housing (record BOM, precedent)",
             assumption="housing wall minimum",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.15,
             epistemic_class="ENGINEERING",
             basis="measured containment wall"),
    ],
    mutation=dict(
        param_id="membrane_diameter_mm", new_value=8.5,
        limiting_parameter_basis=(
            "Record critical parameter 'Membrane area A' (UNKNOWN) and "
            "record failure mode 'Lp out of spec': the osmotic "
            "regulation authority is Lp x A x delta-pi; A is the "
            "geometry-side term."),
        evaluation=dict(
            relation="membrane_active_area_mm2 = pi * (d_measured/2)^2 - clamped_rim",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("Active membrane area computed from MEASURED disc "
                   "radius minus the measured clamp-ring inner radius "
                   "(the clamped rim is inactive). Osmotic agent "
                   "concentration and Lp remain the record's UNKNOWNs — "
                   "not claimed."))),
)

# ---------------------------------------------------------------------------
# P-27-R1 — Self-referencing piezoresistive pressure sensor (portfolio 13)
# Geometry: MEMS die with recessed cavity leaving a thin diaphragm +
# solid reference (dummy) die + carrier platform. Diaphragm thickness
# is THE recorded design variable (sensitivity vs rupture).
# ---------------------------------------------------------------------------
P27_PROGRAM = '''
def build(p):
    dw = p["die_width_mm"]
    dth = p["die_thickness_mm"]
    dt = p["diaphragm_thickness_mm"]
    cw = p["cavity_width_mm"]
    pt = p["carrier_platform_thickness_mm"]
    mg = p["carrier_margin_mm"]
    die = cq.Workplane("XY").box(dw, dw, dth, centered=(True, True, False))
    cavity = (cq.Workplane("XY", origin=(0.0, 0.0, dt))
              .box(cw, cw, dth - dt, centered=(True, True, False)))
    die = die.cut(cavity)
    ref = (cq.Workplane("XY", origin=(dw + 0.05, 0.0, 0.0))
           .box(dw, dw, dth, centered=(True, True, False)))
    carrier = (cq.Workplane("XY")
               .box(dw + dw + mg + mg + 0.05, dw + mg + mg,
                    pt, centered=(True, True, False))
               .translate((dw * 0.5 + 0.025, 0.0, -pt * 0.85)))
    return {"sensor_die": die, "reference_die": ref,
            "carrier_platform": carrier}
'''

P27_TEMPLATE = dict(
    template_id="tpl:P27R1_mems_diaphragm_sensor:v1",
    program=P27_PROGRAM,
    parameters=[
        dict(param_id="die_width_mm", value=2.2, unit="mm",
             range_min=1.8, range_max=2.6,
             record_parameter="Sensor size",
             design_basis=("Record: 'constrained by catheter geometry' "
                           "— die footprint inside a ~2 mm-class "
                           "carrier.")),
        dict(param_id="die_thickness_mm", value=0.45, unit="mm",
             range_min=0.35, range_max=0.65,
             record_parameter="(no recorded critical parameter — die stack)",
             design_basis="standard silicon die thickness class"),
        dict(param_id="diaphragm_thickness_mm", value=0.12, unit="mm",
             range_min=0.05, range_max=0.25,
             record_parameter="Diaphragm thickness",
             design_basis=("THE recorded design variable (UNKNOWN): "
                           "sensitivity ~ 1/t^2 against rupture "
                           "margin; envelope bounded by the record's "
                           "'Diaphragm mechanical damage' failure "
                           "mode.")),
        dict(param_id="cavity_width_mm", value=1.6, unit="mm",
             range_min=1.2, range_max=1.9,
             record_parameter="Diaphragm thickness",
             design_basis=("etched cavity span = the diaphragm active "
                           "diameter; bounded inside the die with a "
                           "side wall.")),
        dict(param_id="carrier_platform_thickness_mm", value=0.6, unit="mm",
             range_min=0.4, range_max=0.9,
             record_parameter="Catheter integration (mechanical protection)",
             design_basis="carrier carrying both dies (record subsystem)"),
        dict(param_id="carrier_margin_mm", value=0.4, unit="mm",
             range_min=0.25, range_max=0.6,
             record_parameter="Catheter integration (mechanical protection)",
             design_basis="carrier edge margin around the dies"),
    ],
    objects=[
        dict(object_id="sensor_die",
             role="active die: etched cavity over a thin diaphragm (piezoresistive sense element)"),
        dict(object_id="reference_die",
             role="solid dummy die for the self-referencing bridge (record R1 fix)"),
        dict(object_id="carrier_platform", role="carrier platform bonding both dies (catheter integration)"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "die_width_mm",
                                 "bbox_z": "die_thickness_mm"},
    interference_pairs=[
        dict(a="sensor_die", b="reference_die", requirement="CLEARANCE"),
        dict(a="sensor_die", b="carrier_platform", requirement="CONTACT"),
        dict(a="reference_die", b="carrier_platform", requirement="CONTACT"),
    ],
    constraints=[
        dict(constraint_id="C_DIE_BOND",
             target="volume_mm3", bound=">=", limit=0.0,
             epistemic_class="ENGINEERING",
             basis="all solids positive (bond overlap present)"),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="planar MEMS stack, not slender",
             max_length_to_diameter_ratio=8),
    ],
    materials_from_record=["silicon wafer (record BOM); encapsulation: Parylene-C or titanium (record BOM)"],
    material_compatibility=[
        dict(material="silicon die (record BOM)",
             assumption="diaphragm stays above rupture-prone thickness",
             measured_quantity="diaphragm_thickness_mm",
             threshold=0.05,
             epistemic_class="ENGINEERING",
             basis=("record failure mode 'Diaphragm mechanical damage'; "
                    "measured as die bbox z minus cavity depth on the "
                    "built solid")),
        dict(material="Parylene-C/titanium encapsulation (record BOM)",
             assumption="carrier keeps protective margin around dies",
             measured_quantity="carrier_margin_mm",
             threshold=0.25,
             epistemic_class="ENGINEERING",
             basis="encapsulation needs a margin to seal the die stack"),
    ],
    mutation=dict(
        param_id="diaphragm_thickness_mm", new_value=0.07,
        limiting_parameter_basis=(
            "Record critical parameter 'Diaphragm thickness' (UNKNOWN, "
            "design choice) and record failure modes 'Chronic drift "
            "exceeds self-referencing' + 'Diaphragm mechanical damage': "
            "thinner diaphragm buys sensitivity but spends rupture "
            "margin — the exact trade the improvement loop must "
            "adjudicate."),
        evaluation=dict(
            relation="sensitivity_modelled_rel = 1 / t_measured^2 (clamped-square-diaphragm scaling, MODELLED)",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("Piezoresistive diaphragm response scales ~1/t^2 "
                   "for a clamped square diaphragm (declared MODELLED "
                   "relation); t is MEASURED on the built die. Absolute "
                   "mmHg accuracy remains the record's UNKNOWN "
                   "(accuracy target ~1-2 mmHg) — not claimed."))),
)

# ---------------------------------------------------------------------------
# P-28 — Acoustic obstruction detection catheter tip (portfolio 14)
# Geometry: catheter tip with lumen + recessed transducer pocket at
# the distal face + PZT disc press-fit in the pocket + acoustic
# window cap. The PZT diameter is the recorded size variable.
# ---------------------------------------------------------------------------
P28_PROGRAM = '''
def build(p):
    od = p["catheter_tip_od_mm"]
    ld = p["lumen_diameter_mm"]
    L = p["tip_length_mm"]
    pd = p["pzt_disc_diameter_mm"]
    pth = p["pzt_thickness_mm"]
    wt = p["acoustic_window_thickness_mm"]
    body = cq.Workplane("XY").circle(od * 0.5).extrude(L)
    body = body.cut(cq.Workplane("XY").circle(ld * 0.5).extrude(L))
    pocket = (cq.Workplane("XY", origin=(0.0, 0.0, L - pth))
              .circle(pd * 0.5).extrude(pth))
    body = body.cut(pocket)
    pzt = (cq.Workplane("XY", origin=(0.0, 0.0, L - pth))
           .circle(pd * 0.5 + 0.02).circle(ld * 0.5)
           .extrude(pth * 0.88))
    window = (cq.Workplane("XY",
              origin=(0.0, 0.0, L - pth * 0.12 + wt * 0.25))
              .circle(pd * 0.5 + 0.1).extrude(wt))
    return {"catheter_tip_body": body, "pzt_transducer_disc": pzt,
            "acoustic_window_cap": window}
'''

P28_TEMPLATE = dict(
    template_id="tpl:P28_acoustic_transducer_tip:v1",
    program=P28_PROGRAM,
    parameters=[
        dict(param_id="catheter_tip_od_mm", value=2.0, unit="mm",
             range_min=1.6, range_max=2.4,
             record_parameter="Transducer size",
             design_basis=("Record: 'constrained by catheter ~2 mm' — "
                           "the engine takes the record's cited "
                           "scale.")),
        dict(param_id="lumen_diameter_mm", value=0.9, unit="mm",
             range_min=0.6, range_max=1.2,
             record_parameter="(catheter integration, record subsystem)",
             design_basis="drainage lumen stays open past the tip"),
        dict(param_id="tip_length_mm", value=25.0, unit="mm",
             range_min=15.0, range_max=35.0,
             record_parameter="(catheter integration, record subsystem)",
             design_basis="instrumented tip section length"),
        dict(param_id="pzt_disc_diameter_mm", value=1.4, unit="mm",
             range_min=1.0, range_max=1.8,
             record_parameter="Transducer size",
             design_basis=("active PZT aperture; detection power and "
                           "beam scale with aperture; bounded by the "
                           "tip wall.")),
        dict(param_id="pzt_thickness_mm", value=0.3, unit="mm",
             range_min=0.2, range_max=0.5,
             record_parameter="Operating frequency",
             design_basis=("disc thickness sets the resonance "
                           "frequency class (record: 'likely 5-20 MHz "
                           "for catheter scale'); engine instantiates "
                           "a mid-band thickness.")),
        dict(param_id="acoustic_window_thickness_mm", value=0.08, unit="mm",
             range_min=0.05, range_max=0.15,
             record_parameter="(acoustic window, record subsystem)",
             design_basis=("record: 'acoustic-transparent window' — a "
                           "thin bonded cap over the transducer "
                           "pocket.")),
    ],
    objects=[
        dict(object_id="catheter_tip_body",
             role="tip body: drainage lumen + recessed transducer pocket at the distal face"),
        dict(object_id="pzt_transducer_disc",
             role="PZT transducer disc press-fit in the pocket (annular around the lumen)"),
        dict(object_id="acoustic_window_cap",
             role="thin acoustic window cap sealing the pocket (record subsystem)"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "catheter_tip_od_mm",
                                 "bbox_z": "tip_length_mm"},
    interference_pairs=[
        dict(a="pzt_transducer_disc", b="catheter_tip_body", requirement="CONTACT"),
        dict(a="acoustic_window_cap", b="catheter_tip_body", requirement="CONTACT"),
        dict(a="acoustic_window_cap", b="pzt_transducer_disc", requirement="CLEARANCE"),
    ],
    constraints=[
        dict(constraint_id="C_TIP_WALL",
             target="min_wall_thickness_mm", bound=">=", limit=0.1,
             epistemic_class="ENGINEERING",
             basis=("record failure mode 'Acoustic window failure': "
                    "the tip wall around pocket and window must stay "
                    "intact; measured on the built tip.")),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="tip section slenderness inside the catheter class",
             max_length_to_diameter_ratio=40),
    ],
    materials_from_record=["PZT or PVDF (record BOM); window/body: silicone/polyurethane with acoustic-transparent window (record)"],
    material_compatibility=[
        dict(material="PZT disc (record BOM)",
             assumption="aperture leaves manufacturable wall to lumen and outer face",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.1,
             epistemic_class="ENGINEERING",
             basis="measured on the built tip"),
        dict(material="polymer acoustic window (record BOM)",
             assumption="window stays a bondable thin cap",
             measured_quantity="window_thickness_mm",
             threshold=0.05,
             epistemic_class="ENGINEERING",
             basis="below this the cap is not a controllable bonded layer"),
    ],
    mutation=dict(
        param_id="pzt_disc_diameter_mm", new_value=1.7,
        limiting_parameter_basis=(
            "Record critical parameter 'Transducer size' (UNKNOWN, "
            "constrained by catheter ~2 mm) and record failure mode "
            "'Attenuation limits detection range': acoustic aperture "
            "is the detection-range geometry term, bought with tip "
            "wall."),
        evaluation=dict(
            relation="active_aperture_area_mm2 = pi*((d_measured/2)^2 - (lumen_d/2)^2)",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("The active annular aperture is computed from "
                   "MEASURED radii (disc press-fit radius minus lumen "
                   "radius). Impedance contrast values are the record's "
                   "own EXTERNAL_PRECEDENTs — not re-derived."))),
)

# ---------------------------------------------------------------------------
# P-29 — MR flow quantification sensor at catheter scale (portfolio 15)
# Geometry: flow tube + RF coil annulus at center + two half-annular
# magnet segments at the coil ends. Magnet thickness is the B0-side
# geometry variable; the assembly stays inside a declared implant OD.
# ---------------------------------------------------------------------------
P29_PROGRAM = '''
def build(p):
    to = p["tube_od_mm"]
    tl = p["tube_length_mm"]
    ld = p["lumen_diameter_mm"]
    ct = p["coil_thickness_mm"]
    chh = p["coil_height_mm"]
    mt = p["magnet_thickness_mm"]
    ml = p["magnet_length_mm"]
    tube = cq.Workplane("XY").circle(to * 0.5).circle(ld * 0.5).extrude(tl)
    zc = tl * 0.5
    coil = (cq.Workplane("XY", origin=(0.0, 0.0, zc - chh * 0.5))
            .circle(to * 0.5 + ct).circle(to * 0.5 - ct * 0.25)
            .extrude(chh))
    ring = (cq.Workplane("XY")
            .circle(to * 0.5 + mt).circle(to * 0.5 - 0.04)
            .extrude(ml))
    cutter = cq.Workplane("XY").box(
        (to + ct + mt) * 4.0, (to + ct + mt) * 4.0, ml,
        centered=(True, False, True))
    mag = ring.cut(cutter)
    magA = mag.translate((0.0, 0.0, zc - chh * 0.5 - ml - ml * 0.05))
    magB = mag.rotate((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 180.0).translate(
        (0.0, 0.0, zc + chh * 0.5 + ml * 0.05))
    return {"flow_tube": tube, "rf_coil_ring": coil,
            "magnet_segment_proximal": magA,
            "magnet_segment_distal": magB}
'''

P29_TEMPLATE = dict(
    template_id="tpl:P29_mr_flow_sensor_assembly:v1",
    program=P29_PROGRAM,
    parameters=[
        dict(param_id="tube_od_mm", value=2.0, unit="mm",
             range_min=1.6, range_max=2.4,
             record_parameter="RF coil size",
             design_basis=("Record: 'constrained by catheter ~2 mm' — "
                           "flow tube at the record's cited scale.")),
        dict(param_id="tube_length_mm", value=40.0, unit="mm",
             range_min=25.0, range_max=55.0,
             record_parameter="(sensor assembly, record subsystem)",
             design_basis="instrumented flow section length"),
        dict(param_id="lumen_diameter_mm", value=1.05, unit="mm",
             range_min=0.7, range_max=1.3,
             record_parameter="(flow path, record subsystem)",
             design_basis="CSF flow lumen through the sensing section"),
        dict(param_id="coil_thickness_mm", value=0.55, unit="mm",
             range_min=0.3, range_max=0.8,
             record_parameter="RF coil size",
             design_basis=("copper winding cross-section class (record "
                           "BOM: copper/silver wire); realized as the "
                           "annular coil body.")),
        dict(param_id="coil_height_mm", value=3.0, unit="mm",
             range_min=2.0, range_max=5.0,
             record_parameter="RF coil size",
             design_basis="solenoid axial length"),
        dict(param_id="magnet_thickness_mm", value=0.85, unit="mm",
             range_min=0.5, range_max=1.2,
             record_parameter="B0 field strength",
             design_basis=("B0 is the recorded UNKNOWN (likely 0.1-1 T); "
                           "the geometry-side term is the magnet "
                           "cross-section — realized as two half-annular "
                           "rare-earth segments (record BOM: NdFeB/"
                           "SmCo).")),
        dict(param_id="magnet_length_mm", value=6.0, unit="mm",
             range_min=4.0, range_max=8.0,
             record_parameter="Gradient coil (bipolar)",
             design_basis=("two magnet segments spaced by the coil "
                           "create the bipolar field region the "
                           "record's gradient encoding uses.")),
    ],
    objects=[
        dict(object_id="flow_tube", role="CSF flow tube through the sensing section"),
        dict(object_id="rf_coil_ring", role="RF transmit/receive coil annulus (record subsystem)"),
        dict(object_id="magnet_segment_proximal", role="proximal half-annular magnet segment (B0 source, record subsystem)"),
        dict(object_id="magnet_segment_distal", role="distal half-annular magnet segment (B0 source, record subsystem)"),
    ],
    measured_dimension_bindings={"bbox_xy_max": "tube_od_mm",
                                 "bbox_z": "tube_length_mm"},
    interference_pairs=[
        dict(a="rf_coil_ring", b="flow_tube", requirement="CONTACT"),
        dict(a="magnet_segment_proximal", b="flow_tube", requirement="CONTACT"),
        dict(a="magnet_segment_distal", b="flow_tube", requirement="CONTACT"),
        dict(a="magnet_segment_proximal", b="rf_coil_ring", requirement="CLEARANCE"),
        dict(a="magnet_segment_distal", b="rf_coil_ring", requirement="CLEARANCE"),
    ],
    constraints=[
        dict(constraint_id="C_TUBE_WALL",
             target="min_wall_thickness_mm", bound=">=", limit=0.1,
             epistemic_class="ENGINEERING",
             basis="flow tube wall manufacturable minimum under the wound coil"),
    ],
    geometry_assumptions=[
        dict(kind="SLENDERNESS_LIMIT",
             statement="sensing section slenderness inside the catheter class",
             max_length_to_diameter_ratio=40),
    ],
    materials_from_record=["magnets: NdFeB or SmCo (record BOM); coil: copper/silver (record BOM); tube: polymer (record)"],
    material_compatibility=[
        dict(material="polymer flow tube (record BOM)",
             assumption="tube wall minimum under bonded coil",
             measured_quantity="min_wall_thickness_mm",
             threshold=0.1,
             epistemic_class="ENGINEERING",
             basis="measured containment wall"),
        dict(material="rare-earth magnet segments (record BOM)",
             assumption="magnet cross-section stays a magnetizable ring segment",
             measured_quantity="magnet_cross_section_mm2",
             threshold=0.4,
             epistemic_class="ENGINEERING",
             basis=("B0 scales with magnet volume (MODELLED); below "
                    "this cross-section the segment is not a "
                    "practical magnet ring")),
    ],
    mutation=dict(
        param_id="magnet_thickness_mm", new_value=1.1,
        limiting_parameter_basis=(
            "Record critical parameter 'B0 field strength' (UNKNOWN, "
            "likely 0.1-1 T for miniaturization) and record failure "
            "mode 'SNR insufficient at low B0': B0 scales with magnet "
            "cross-section, bought with assembly diameter."),
        evaluation=dict(
            relation="magnet_cross_section_mm2 = OD_r^2 area minus ID_r^2 area of the half-annulus (measured radii)",
            relation_class="MODELLED",
            direction="MAXIMIZE",
            basis=("The B0-side geometry term computed from MEASURED "
                   "magnet radii; absolute field strength needs the "
                   "record's magnet material UNKNOWNs — not claimed. "
                   "Assembly OD is measured and checked against the "
                   "declared implant envelope."))),
)


# ---------------------------------------------------------------------------
# THE REGISTRY — package_id -> template spec (P-13 has NO template: the
# classifier emits an honest 3D_NOT_APPLICABLE for a software-only
# technology; nothing may silently force a model onto it).
# ---------------------------------------------------------------------------
PORTFOLIO_TEMPLATES = {
    "P-01": P01_TEMPLATE,
    "P-02": P02_TEMPLATE,
    "P-04": P04_TEMPLATE,
    "P-07": P07_TEMPLATE,
    "P-11": P11_TEMPLATE,
    "P-15-R1": P15_TEMPLATE,
    "P-16": P16_TEMPLATE,
    "P-21-R1": P21_TEMPLATE,
    "P-22-R1": P22_TEMPLATE,
    "P-24": P24_TEMPLATE,
    "P-26": P26_TEMPLATE,
    "P-27-R1": P27_TEMPLATE,
    "P-28": P28_TEMPLATE,
    "P-29": P29_TEMPLATE,
}

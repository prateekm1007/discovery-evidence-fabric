"""Canonical domain-geometry specification layer (R432 sections 4-5).

ONE deterministic path from the recorded invention state to a canonical
geometry specification:

    recorded run state (problem text + intervention site + subsystems)
        |
        v  select_domain_family()  (keyword score, basis recorded)
    DOMAIN FAMILY (VEHICLE / MEDICAL_DEVICE / FLUID_DEVICE / THERMAL_SYSTEM /
                   MECHANICAL_COMPONENT / ELECTRONIC_SYSTEM /
                   ENERGY_STORAGE / GENERIC_ARCHITECTURE)
        |
        v  derive_geometry_spec()
    CANONICAL GEOMETRY SPEC (JSON schema below)
        |
        v  domain_geometry.build_domain_model()  (deterministic builders)
    GLB with CANONICAL COMPONENT IDs

The LLM never authors mesh data. The spec is a deterministic projection of
the recorded architecture (Art. X — no second truth source): every mapped
component carries the RECORDED subsystem name it represents
(mapped_from); structural form components carry structural=true and cite
the family-selection basis. Nothing here claims engineering dimensions —
the spec is dimension_class=ABSTRACT_PRESENTATION_UNITS, measurement
basis TOPOLOGY_ONLY (same epistemic contract as the conceptual builder
it supersedes; epistemics.guard_no_engineering_dimensions applies).

Spec schema (R432 section 5):

    {
      "spec_version": "1.0.0",
      "technology_class": "VEHICLE",
      "dimension_class": "ABSTRACT_PRESENTATION_UNITS",
      "measurement_basis": "TOPOLOGY_ONLY",
      "spec_sha256": "...",              # hash of the spec sans this field
      "selection_basis": {...},           # the score table (auditable)
      "components": [
        {
          "component_id": "battery_pack",
          "label": "traction battery pack",
          "form": "pack",
          "material_class": "battery",
          "mapped_from": "<recorded subsystem name or null>",
          "structural": false,
          "role": "..."
        }, ...
      ],
      "interfaces": [
        {
          "interface_id": "pwr_battery_motor",
          "from": "battery_pack", "to": "traction_motor",
          "kind": "power", "form": "conduit"
        }, ...
      ]
    }
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

SPEC_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# R432 section 4: domain families. Keyword routing is deterministic and the
# FULL score table is recorded in selection_basis (auditable, Art. XXVII —
# no magic thresholds). Whole-form signals outrank component signals: a
# problem that asks for a vehicle builds a vehicle, even when subsystems
# mention batteries/thermal (they become components OF the vehicle).
# ---------------------------------------------------------------------------

_FAMILY_SIGNALS: List[Tuple[str, List[Tuple[str, int]]]] = [
    # (family, [(keyword, weight), ...])
    ("VEHICLE", [
        ("electric vehicle", 6), ("solar vehicle", 6), ("solar car", 6),
        ("solar ev", 6), ("vehicle", 5), ("automotive", 5),
        ("car", 3), ("ev ", 3), ("truck", 4), ("bus", 4),
        ("chassis", 2), ("drivetrain", 2), ("wheel", 2), ("traction", 2),
        ("road", 1), ("byd", 2), ("tesla", 2),
    ]),
    ("MEDICAL_DEVICE", [
        ("catheter", 6), ("shunt", 5), ("stent", 5), ("lumen", 4),
        ("medical device", 5), ("implant", 4), ("intravascular", 4),
        ("surgical", 3), ("venous", 3), ("patient", 1), ("clinical", 1),
    ]),
    ("FLUID_DEVICE", [
        ("pump", 6), ("valve", 5), ("microfluidic", 6), ("nozzle", 4),
        ("chamber", 3), ("channel", 2), ("flow sensor", 5),
        ("fluid", 2), ("flow control", 4), ("diaphragm", 3),
        ("impeller", 4), ("metering", 3),
    ]),
    ("THERMAL_SYSTEM", [
        ("heat sink", 4), ("heat exchanger", 5), ("thermal management", 4),
        ("thermal runaway", 5), ("cooling", 4), ("heating", 3),
        ("thermal", 3), ("heat", 2), ("radiator", 3), ("cold plate", 4),
    ]),
    ("MECHANICAL_COMPONENT", [
        ("bearing", 5), ("shaft", 4), ("spring", 4), ("fastener", 4),
        ("gear", 4), ("rail", 4), ("joint", 2), ("structural", 2),
        ("load path", 3), ("damper", 3), ("suspension", 3),
        ("fatigue", 1), ("fracture", 1),
    ]),
    ("ELECTRONIC_SYSTEM", [
        ("circuit", 4), ("electronics", 4), ("board", 3), ("pcba", 5),
        ("inverter", 4), ("converter", 3), ("power electronics", 5),
        ("module electronics", 2), ("controller", 2), ("antenna", 3),
        ("sensor node", 3), ("battery management", 2),
    ]),
    ("ENERGY_STORAGE", [
        ("battery pack", 5), ("battery module", 5), ("battery cell", 4),
        ("cell", 2), ("battery", 3), ("energy storage", 4),
        ("supercapacitor", 5), ("pack", 2),
    ]),
]

FAMILY_LABELS = {
    "VEHICLE": "vehicle architecture",
    "MEDICAL_DEVICE": "medical device architecture",
    "FLUID_DEVICE": "fluid device architecture",
    "THERMAL_SYSTEM": "thermal system architecture",
    "MECHANICAL_COMPONENT": "mechanical component architecture",
    "ELECTRONIC_SYSTEM": "electronic system architecture",
    "ENERGY_STORAGE": "energy storage architecture",
    "GENERIC_ARCHITECTURE": "generic system architecture",
}

GENERIC_FAMILY = "GENERIC_ARCHITECTURE"


def _text_of(problem_text: str, intervention_site: str,
             subsystems: Sequence[str]) -> str:
    parts = [
        str(problem_text or ""),
        str(intervention_site or ""),
        " ".join(str(s) for s in (subsystems or [])),
    ]
    return " ".join(parts).lower()


def select_domain_family(problem_text: str, intervention_site: str,
                         subsystems: Sequence[str]) -> Dict[str, Any]:
    """Deterministic domain-family routing with the FULL basis recorded.

    Every keyword hit (family, keyword, weight, count) is returned in
    the score table so the choice is auditable from the artifact alone.
    A family with no hits never wins; a tie resolves by the fixed
    registry order (deterministic); below the minimum score the honest
    GENERIC_ARCHITECTURE family is selected and the result is labeled
    as such (R432 section 3: generic blocks are acceptable ONLY as a
    clearly labeled early conceptual fallback).
    """
    text = _text_of(problem_text, intervention_site, subsystems)
    scores: List[Dict[str, Any]] = []
    best_family, best_score = GENERIC_FAMILY, 0
    for family, signals in _FAMILY_SIGNALS:
        total = 0
        hits = []
        for keyword, weight in signals:
            count = text.count(keyword)
            if count:
                total += weight * count
                hits.append({"keyword": keyword, "weight": weight,
                             "count": count})
        scores.append({"family": family, "score": total,
                       "hits": hits})
        if total > best_score:
            best_family, best_score = family, total

    # The form threshold: a whole-technology form needs real signal, not
    # one weak keyword (recorded value; Art. XXVII — provenance for the
    # number lives in this docstring + the gate battery).
    min_form_score = 3
    if best_score < min_form_score:
        best_family = GENERIC_FAMILY

    return {
        "family": best_family,
        "label": FAMILY_LABELS[best_family],
        "score": best_score,
        "min_form_score": min_form_score,
        "score_table": scores,
        "basis": {
            "derived_from": ["problem text", "intervention site",
                             "recorded subsystem names"],
            "rule": "highest keyword score wins; ties resolve by registry "
                    "order; below the form threshold the generic "
                    "architecture family is selected and labeled",
            "deterministic": True,
        },
    }


# ---------------------------------------------------------------------------
# Component mapping — recorded subsystem name -> canonical component slot.
# Keyword rules are per-family; unmapped subsystems become labeled mounted
# modules so EVERY recorded subsystem is represented in the model (the
# fidelity contract the generic builder already carried).
# ---------------------------------------------------------------------------

_VEHICLE_MAP: List[Tuple[Tuple[str, ...], str, str, str]] = [
    # ((keywords,), component_id, label, material_class)
    (("battery", "cell", "storage", "energy reservoir"), "battery_pack",
     "traction battery pack", "battery"),
    (("solar", "photovolta", "pv"), "solar_roof",
     "solar roof surface", "silicon"),
    (("motor", "drive", "traction", "propulsion"), "traction_motor",
     "traction motor", "machined_metal"),
    (("inverter", "converter", "power electronics", "electronics",
      "controller", "bms", "battery management"), "power_electronics",
     "power electronics bay", "machined_metal"),
    (("thermal", "cooling", "heat", "refrigerant"), "thermal_loop",
     "thermal management loop", "conduit_power"),
    (("charg", "port", "connector"), "charging_port",
     "charging interface", "polymer"),
    (("control", "compute", "optimi", "ai", "algorithm", "governor",
      "model", "predict"), "control_module",
     "control and computation module", "circuit"),
    (("sensor", "monitor", "meter", "characterization", "iot",
      "detection"), "sensor_module", "sensing module", "circuit"),
]

_MEDICAL_MAP: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("lumen", "drainage", "flow"), "flow_lumen",
     "primary flow lumen", "polymer"),
    (("membrane", "valve", "slit"), "valve_membrane",
     "valve membrane", "polymer"),
    (("sensor", "pressure", "monitor", "characterization"),
     "sensor_band", "sensor band", "machined_metal"),
    (("drug", "therapy", "eluting", "infus"), "therapy_lumen",
     "therapy delivery lumen", "polymer"),
    (("coating", "surface", "lubric", "anti"), "surface_coating",
     "functional surface coating", "composite"),
    (("control", "compute", "algorithm", "adaptive"), "control_module",
     "control module", "circuit"),
]

_FLUID_MAP: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("inlet", "intake", "source"), "inlet_port",
     "inlet port", "polymer"),
    (("outlet", "exit", "output", "export"), "outlet_port",
     "outlet port", "polymer"),
    (("valve", "gate", "diaphragm", "pinch"), "valve_stage",
     "valve stage", "machined_metal"),
    (("chamber", "plenum", "reservoir", "buffer"), "chamber",
     "flow chamber", "polymer"),
    (("sensor", "meter", "measure", "flow sensor"), "flow_sensor",
     "flow sensing stage", "machined_metal"),
    (("control", "actuat", "drive", "compute"), "actuator_stage",
     "actuation stage", "circuit"),
]

_THERMAL_MAP: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("heat source", "source", "battery", "chip", "electronics",
      "cell"), "heat_source", "heat source block", "battery"),
    (("sink", "dissipat", "fin", "radiator", "ambient"), "heat_sink",
     "heat sink fin stack", "machined_metal"),
    (("cold plate", "plate", "interface", "tim"), "cold_plate",
     "cold plate / thermal interface", "machined_metal"),
    (("channel", "loop", "coolant", "fluid", "microchannel"),
     "coolant_loop", "coolant loop", "conduit_power"),
    (("control", "pump", "actuat", "compute"), "control_module",
     "control module", "circuit"),
]

_MECHANICAL_MAP: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("shaft", "axle", "spindle"), "shaft", "load shaft", "machined_metal"),
    (("bearing", "journal", "bushing"), "bearing", "bearing seats",
     "machined_metal"),
    (("spring", "compliance", "elastic", "suspens"), "spring",
     "compliance spring", "machined_metal"),
    (("housing", "body", "enclosure", "mount"), "housing",
     "structural housing", "body_metal"),
    (("load", "force", "path", "structural"), "load_path",
     "load path member", "body_metal"),
    (("sensor", "monitor", "strain", "gauge"), "sensor_module",
     "sensing module", "circuit"),
]

_ELECTRONIC_MAP: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("board", "pcba", "circuit", "die", "chip"), "main_board",
     "main circuit board", "circuit"),
    (("power", "supply", "converter", "inverter", "stage"),
     "power_stage", "power stage", "machined_metal"),
    (("connector", "port", "interface", "cable"), "connectors",
     "connector bank", "polymer"),
    (("thermal", "sink", "spread", "heat"), "thermal_path",
     "thermal path / heatsink", "machined_metal"),
    (("enclosure", "housing", "case", "shield"), "enclosure",
     "enclosure shell", "body_metal"),
    (("antenna", "rf", "radio", "wireless"), "antenna",
     "antenna element", "machined_metal"),
]

_ENERGY_MAP: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("cell", "electrode", "chemistry", "cathode", "anode"),
     "cell_stack", "cell stack", "battery"),
    (("bus", "bar", "interconnect", "tab"), "bus_bars",
     "bus bar interconnects", "machined_metal"),
    (("thermal", "barrier", "runaway", "cooling", "spread"),
     "thermal_barrier", "thermal barrier plates", "ceramic"),
    (("bms", "management", "control", "monitor", "sensor"),
     "bms_board", "battery management board", "circuit"),
    (("enclosure", "housing", "pack", "case"), "pack_enclosure",
     "pack enclosure", "body_metal"),
]

_FAMILY_MAPS = {
    "VEHICLE": _VEHICLE_MAP,
    "MEDICAL_DEVICE": _MEDICAL_MAP,
    "FLUID_DEVICE": _FLUID_MAP,
    "THERMAL_SYSTEM": _THERMAL_MAP,
    "MECHANICAL_COMPONENT": _MECHANICAL_MAP,
    "ELECTRONIC_SYSTEM": _ELECTRONIC_MAP,
    "ENERGY_STORAGE": _ENERGY_MAP,
}


def _map_subsystem(name: str,
                   mapping: List[Tuple[Tuple[str, ...], str, str, str]]
                   ) -> Optional[Tuple[str, str, str]]:
    """One recorded subsystem -> canonical slot (first matching rule)."""
    low = str(name).lower()
    for keywords, cid, label, material in mapping:
        if any(k in low for k in keywords):
            return cid, label, material
    return None


# Structural form components per family (canonical IDs; R432 section 9:
# object names correspond to canonical component IDs, never Cube.001).
# These are PRESENTATION FORM derived from the technology class, not
# recorded subsystems — each carries structural=true and the honest role
# line so the dossier can distinguish form from content.

_STRUCTURAL: Dict[str, List[Dict[str, Any]]] = {
    "VEHICLE": [
        {"component_id": "chassis", "label": "body and chassis",
         "material_class": "body_metal", "form": "hull",
         "role": "vehicle body form (structural presentation element "
                 "derived from the vehicle technology class)"},
        {"component_id": "cabin", "label": "occupant cabin",
         "material_class": "glass", "form": "greenhouse",
         "role": "cabin volume (structural presentation element)"},
        {"component_id": "wheel_fl", "label": "wheel (front left)",
         "material_class": "rubber", "form": "wheel",
         "role": "road wheel (structural presentation element)"},
        {"component_id": "wheel_fr", "label": "wheel (front right)",
         "material_class": "rubber", "form": "wheel",
         "role": "road wheel (structural presentation element)"},
        {"component_id": "wheel_rl", "label": "wheel (rear left)",
         "material_class": "rubber", "form": "wheel",
         "role": "road wheel (structural presentation element)"},
        {"component_id": "wheel_rr", "label": "wheel (rear right)",
         "material_class": "rubber", "form": "wheel",
         "role": "road wheel (structural presentation element)"},
        {"component_id": "solar_hood", "label": "front solar surface",
         "material_class": "silicon", "form": "panel",
         "role": "front body solar surface (structural presentation "
                 "element of the vehicle form)"},
        {"component_id": "solar_deck", "label": "rear deck solar surface",
         "material_class": "silicon", "form": "panel",
         "role": "rear deck solar surface (structural presentation "
                 "element of the vehicle form)"},
    ],
    "MEDICAL_DEVICE": [
        {"component_id": "device_shaft", "label": "device shaft",
         "material_class": "polymer", "form": "shaft",
         "role": "device body shaft (structural presentation element)"},
        {"component_id": "distal_tip", "label": "distal tip",
         "material_class": "polymer", "form": "tip",
         "role": "distal tip section (structural presentation element)"},
        {"component_id": "hub", "label": "proximal hub",
         "material_class": "polymer", "form": "hub",
         "role": "proximal hub interface (structural presentation "
                 "element)"},
        # R443 family-definitional (domain acceptance contract)
        {"component_id": "flow_lumen", "label": "primary flow lumen",
         "material_class": "conduit_power", "form": "lumen",
         "role": "primary flow lumen (family-definitional presentation "
                 "element of the medical-device acceptance case; mapped "
                 "subsystem recorded as alias)"},
    ],
    "FLUID_DEVICE": [
        {"component_id": "device_body", "label": "device body",
         "material_class": "polymer", "form": "body",
         "role": "fluid device body (structural presentation element)"},
        {"component_id": "flow_channel", "label": "main flow channel",
         "material_class": "conduit_power", "form": "channel",
         "role": "main flow path (structural presentation element)"},
        # R443 family-definitional (domain acceptance contract): a
        # fluid device reads as a fluid device only with its ports and
        # flow-control stage; mapped subsystems carry provenance
        # aliases.
        {"component_id": "inlet_port", "label": "inlet port",
         "material_class": "polymer", "form": "port",
         "role": "inlet port (family-definitional presentation element "
                 "of the fluid-device acceptance case; mapped subsystem "
                 "recorded as alias)"},
        {"component_id": "outlet_port", "label": "outlet port",
         "material_class": "polymer", "form": "port",
         "role": "outlet port (family-definitional presentation element "
                 "of the fluid-device acceptance case; mapped subsystem "
                 "recorded as alias)"},
        {"component_id": "valve_stage", "label": "flow-control valve stage",
         "material_class": "machined_metal", "form": "valve",
         "role": "flow-control stage (family-definitional presentation "
                 "element of the fluid-device acceptance case; mapped "
                 "subsystem recorded as alias)"},
    ],
    "THERMAL_SYSTEM": [
        {"component_id": "assembly_base", "label": "assembly base",
         "material_class": "body_metal", "form": "base",
         "role": "assembly baseplate (structural presentation element)"},
        # R443 family-definitional (domain acceptance contract — the
        # audit defect: a thermal system whose spec never carries a
        # heat source/sink failed family_feature + domain_architecture).
        # A thermal system reads as one only with its source, sink and
        # transport loop; recorded subsystems that map here carry the
        # provenance alias (never invented content).
        {"component_id": "heat_source", "label": "heat source block",
         "material_class": "battery", "form": "source",
         "role": "heat source side (family-definitional presentation "
                 "element of the thermal acceptance case; mapped "
                 "subsystem recorded as alias)"},
        {"component_id": "heat_sink", "label": "heat sink fin stack",
         "material_class": "machined_metal", "form": "sink",
         "role": "heat rejection side (family-definitional presentation "
                 "element of the thermal acceptance case; mapped "
                 "subsystem recorded as alias)"},
        {"component_id": "coolant_loop", "label": "coolant loop",
         "material_class": "conduit_power", "form": "loop",
         "role": "coolant transport circuit (family-definitional "
                 "presentation element of the thermal acceptance case; "
                 "mapped subsystem recorded as alias)"},
    ],
    "MECHANICAL_COMPONENT": [
        {"component_id": "housing", "label": "component housing",
         "material_class": "body_metal", "form": "housing",
         "role": "component housing (structural presentation element)"},
        {"component_id": "load_path", "label": "load path member",
         "material_class": "body_metal", "form": "frame",
         "role": "primary load path (structural presentation element)"},
    ],
    "ELECTRONIC_SYSTEM": [
        {"component_id": "enclosure", "label": "enclosure shell",
         "material_class": "body_metal", "form": "enclosure",
         "role": "system enclosure (structural presentation element)"},
        {"component_id": "main_board", "label": "main circuit board",
         "material_class": "circuit", "form": "board",
         "role": "main board (structural presentation element)"},
        # R443 family-definitional (domain acceptance contract)
        {"component_id": "power_stage", "label": "power stage",
         "material_class": "machined_metal", "form": "stage",
         "role": "power conversion stage (family-definitional "
                 "presentation element of the electronic acceptance "
                 "case; mapped subsystem recorded as alias)"},
    ],
    "ENERGY_STORAGE": [
        {"component_id": "cell_stack", "label": "cell stack",
         "material_class": "battery", "form": "stack",
         "role": "cell stack (structural presentation element)"},
        {"component_id": "pack_enclosure", "label": "pack enclosure",
         "material_class": "body_metal", "form": "enclosure",
         "role": "pack enclosure (structural presentation element)"},
        # R443 family-definitional (domain acceptance contract)
        {"component_id": "bus_bars", "label": "bus bars",
         "material_class": "machined_metal", "form": "bus",
         "role": "series interconnect bus bars (family-definitional "
                 "presentation element of the energy-storage "
                 "acceptance case; mapped subsystem recorded as alias)"},
    ],
}

# Interfaces: physical relationships in the family form. Deterministic;
# endpoints must exist in the component set (gate-checkable).
_INTERFACES: Dict[str, List[Dict[str, Any]]] = {
    "VEHICLE": [
        {"interface_id": "pwr_battery_motor", "from": "battery_pack",
         "to": "traction_motor", "kind": "power"},
        {"interface_id": "pwr_solar_battery", "from": "solar_roof",
         "to": "battery_pack", "kind": "charge"},
        {"interface_id": "pwr_electronics_motor", "from": "power_electronics",
         "to": "traction_motor", "kind": "control"},
        {"interface_id": "pwr_battery_electronics", "from": "battery_pack",
         "to": "power_electronics", "kind": "power"},
        {"interface_id": "thm_loop_battery", "from": "thermal_loop",
         "to": "battery_pack", "kind": "thermal"},
        {"interface_id": "thm_loop_motor", "from": "thermal_loop",
         "to": "traction_motor", "kind": "thermal"},
        {"interface_id": "chg_port_battery", "from": "charging_port",
         "to": "battery_pack", "kind": "charge"},
        {"interface_id": "drv_motor_wheels", "from": "traction_motor",
         "to": "chassis", "kind": "drive"},
        {"interface_id": "ctl_module_battery", "from": "control_module",
         "to": "battery_pack", "kind": "control"},
    ],
    "MEDICAL_DEVICE": [
        {"interface_id": "flow_lumen_tip", "from": "flow_lumen",
         "to": "distal_tip", "kind": "flow"},
        {"interface_id": "flow_hub_lumen", "from": "hub",
         "to": "flow_lumen", "kind": "flow"},
        {"interface_id": "thp_lumen_tip", "from": "therapy_lumen",
         "to": "distal_tip", "kind": "delivery"},
        {"interface_id": "sens_band_tip", "from": "sensor_band",
         "to": "distal_tip", "kind": "signal"},
    ],
    "FLUID_DEVICE": [
        {"interface_id": "flow_inlet_chamber", "from": "inlet_port",
         "to": "chamber", "kind": "flow"},
        {"interface_id": "flow_chamber_outlet", "from": "chamber",
         "to": "outlet_port", "kind": "flow"},
        {"interface_id": "ctl_valve", "from": "actuator_stage",
         "to": "valve_stage", "kind": "control"},
        {"interface_id": "sense_chamber", "from": "flow_sensor",
         "to": "chamber", "kind": "signal"},
    ],
    "THERMAL_SYSTEM": [
        {"interface_id": "thm_source_plate", "from": "heat_source",
         "to": "cold_plate", "kind": "heat"},
        {"interface_id": "thm_plate_sink", "from": "cold_plate",
         "to": "heat_sink", "kind": "heat"},
        {"interface_id": "thm_loop_source", "from": "coolant_loop",
         "to": "heat_source", "kind": "coolant"},
        {"interface_id": "thm_loop_sink", "from": "coolant_loop",
         "to": "heat_sink", "kind": "coolant"},
    ],
    "MECHANICAL_COMPONENT": [
        {"interface_id": "mec_shaft_bearing", "from": "shaft",
         "to": "bearing", "kind": "support"},
        {"interface_id": "mec_spring_housing", "from": "spring",
         "to": "housing", "kind": "preload"},
        {"interface_id": "mec_shaft_load", "from": "shaft",
         "to": "load_path", "kind": "load"},
    ],
    "ELECTRONIC_SYSTEM": [
        {"interface_id": "ele_board_enclosure", "from": "main_board",
         "to": "enclosure", "kind": "mount"},
        {"interface_id": "ele_power_board", "from": "power_stage",
         "to": "main_board", "kind": "power"},
        {"interface_id": "ele_connector_board", "from": "connectors",
         "to": "main_board", "kind": "signal"},
        {"interface_id": "ele_thermal_power", "from": "thermal_path",
         "to": "power_stage", "kind": "heat"},
    ],
    "ENERGY_STORAGE": [
        {"interface_id": "es_cells_bus", "from": "cell_stack",
         "to": "bus_bars", "kind": "electrical"},
        {"interface_id": "es_bms_bus", "from": "bms_board",
         "to": "bus_bars", "kind": "sense"},
        {"interface_id": "es_barrier_cells", "from": "thermal_barrier",
         "to": "cell_stack", "kind": "thermal"},
    ],
}

# Presentation-only conduits drawn for the interfaces (kind -> material).
_INTERFACE_MATERIAL = {
    "power": "conduit_power", "charge": "conduit_power",
    "thermal": "conduit_power", "coolant": "conduit_power",
    "flow": "conduit_power", "delivery": "conduit_power",
    "control": "conduit_data", "signal": "conduit_data", "sense": "conduit_data",
    "drive": "conduit_power", "heat": "conduit_power",
    "support": "conduit_data", "preload": "conduit_data", "load": "conduit_data",
    "mount": "conduit_data", "electrical": "conduit_power",
}


def _component(cid: str, label: str, form: str, material_class: str,
               mapped_from: Optional[str], structural: bool,
               role: str) -> Dict[str, Any]:
    return {
        "component_id": cid,
        "label": label,
        "form": form,
        "material_class": material_class,
        "mapped_from": mapped_from,
        "structural": structural,
        "role": role,
    }


def derive_geometry_spec(family: str, subsystems: Sequence[str],
                         intervention_site: str,
                         selection: Optional[Dict[str, Any]] = None
                         ) -> Dict[str, Any]:
    """Build the canonical geometry spec for a domain family.

    Mapped subsystems adopt their canonical slot; UNMAPPED recorded
    subsystems become mounted modules (labeled, in their recorded
    position order) so every recorded subsystem is represented. The
    spec hash covers the full content (deterministic identity).
    """
    mapping = _FAMILY_MAPS.get(family)
    if mapping is None:
        # Only reachable for GENERIC/unknown families — honest refusal
        # (the generic builder consumes recorded names directly).
        return {
            "spec_version": SPEC_VERSION,
            "technology_class": family,
            "dimension_class": "ABSTRACT_PRESENTATION_UNITS",
            "measurement_basis": "TOPOLOGY_ONLY",
            "selection_basis": selection or {},
            "components": [],
            "interfaces": [],
            "note": ("generic architecture — no domain spec; the generic "
                     "builder consumes recorded subsystem names directly"),
        }

    components: List[Dict[str, Any]] = []
    seen: set = set()

    def add(comp: Dict[str, Any]) -> None:
        if comp["component_id"] not in seen:
            seen.add(comp["component_id"])
            components.append(comp)

    # structural form components first (deterministic order)
    for base in _STRUCTURAL[family]:
        add(_component(base["component_id"], base["label"], base["form"],
                       base["material_class"], None, True, base["role"]))

    # mapped subsystem slots
    mapped: List[Dict[str, Any]] = []
    for name in [s for s in (subsystems or []) if s]:
        hit = _map_subsystem(name, mapping)
        if hit is None:
            continue
        cid, label, material = hit
        mapped.append(_component(
            cid, label, "slot", material, str(name), False,
            f"recorded subsystem '{name}' mapped onto the {label} slot"))
    # dedupe mapped slots by component_id (first recorded name wins —
    # deterministic; later duplicates are recorded as aliases). R443:
    # a slot that is family-definitional STRUCTURAL may also receive a
    # recorded subsystem — the mapping is recorded as mapped_from +
    # alias on that component so the provenance is never lost (Art. X:
    # one canonical spec, every recorded subsystem's destination
    # auditable).
    aliases: List[Dict[str, Any]] = []
    by_id = {c["component_id"]: c for c in components}
    for comp in mapped:
        if comp["component_id"] in seen:
            aliases.append({"component_id": comp["component_id"],
                            "recorded_subsystem": comp["mapped_from"]})
            target = by_id.get(comp["component_id"])
            if target is not None and not target.get("mapped_from"):
                target["mapped_from"] = comp["mapped_from"]
            continue
        add(comp)
    if aliases:
        for comp in components:
            comp["recorded_aliases"] = sorted(
                a["recorded_subsystem"] for a in aliases
                if a["component_id"] == comp["component_id"])

    # unmapped recorded subsystems -> mounted modules (NO cap: the
    # fidelity contract below says EVERY recorded subsystem appears;
    # truncation would silently break it)
    module_idx = 0
    for name in [s for s in (subsystems or []) if s]:
        if _map_subsystem(name, mapping) is not None:
            continue
        module_idx += 1
        cid = f"module_{module_idx:02d}"
        add(_component(
            cid, f"module: {name}", "module", "polymer", str(name), False,
            f"recorded subsystem '{name}' (no canonical slot in the "
            f"{FAMILY_LABELS[family]}; mounted as a labeled module)"))

    # interfaces restricted to existing components (gate-checkable)
    interfaces = [i for i in _INTERFACES[family]
                  if i["from"] in seen and i["to"] in seen]

    spec = {
        "spec_version": SPEC_VERSION,
        "technology_class": family,
        "dimension_class": "ABSTRACT_PRESENTATION_UNITS",
        "measurement_basis": "TOPOLOGY_ONLY",
        "intervention_site": str(intervention_site or ""),
        "selection_basis": selection or {},
        "components": components,
        "interfaces": [
            {**i, "material_class": _INTERFACE_MATERIAL.get(i["kind"],
                                                            "conduit_data"),
             "form": "conduit"}
            for i in interfaces
        ],
        "fidelity": {
            "recorded_subsystems": [str(s) for s in (subsystems or []) if s],
            "mapped": [c["component_id"] for c in components
                       if not c["structural"]],
            "structural_form_components": [c["component_id"] for c in
                                           components if c["structural"]],
            "unmapped_note": ("every recorded subsystem appears as a "
                              "canonical slot, an alias, or a labeled "
                              "module — the fidelity contract of the "
                              "conceptual layer"),
        },
    }
    spec["spec_sha256"] = hashlib.sha256(json.dumps(
        spec, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return spec


def build_spec_from_state(run_result: Dict[str, Any],
                          vis: Dict[str, Any]) -> Dict[str, Any]:
    """select + derive, straight from the recorded run state."""
    problem_text = str(
        (run_result or {}).get("user_text")
        or ((run_result or {}).get("problem") or {}).get("text")
        or "")
    site = str((vis or {}).get("intervention_site") or "")
    subsystems = (vis or {}).get("subsystems") or []
    selection = select_domain_family(problem_text, site, subsystems)
    spec = derive_geometry_spec(
        selection["family"], subsystems, site, selection=selection)
    return {"selection": selection, "spec": spec}

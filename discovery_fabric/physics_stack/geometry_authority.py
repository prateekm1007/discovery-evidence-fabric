"""geometry_authority.py — the geometry authority boundary (R413,
operator directive V2 Phase 4).

THE OPERATOR'S BOUNDARY, VERBATIM:
    "CadQuery is the engineering geometry authority; Blender is a
     downstream visualization/rendering system and cannot originate or
     independently validate engineering geometry."

This module makes the boundary MACHINE-ENFORCED, not aspirational:

1. The set of engineering-geometry authorities is CLOSED and measured:
   {cadquery} — availability carries a probe (this environment:
   OPERATIONAL, cadquery 2.6.1, live parametric build verified against
   closed-form volume; Art. VI: measured, never assumed).
2. A GEOMETRY_SPEC may only carry geometry_authority='cadquery'.
   Blender (or any renderer) as the ORIGIN of engineering geometry is
   REJECTED_GEOMETRY_AUTHORITY — the two-sources-of-geometric-truth
   failure mode the operator and the external auditor both flagged is
   structurally impossible.
3. A geometry VALIDATION record may never cite blender as validator
   (a render cannot validate engineering geometry).
4. Blender's only admissible role is DOWNSTREAM: RENDERING-stage
   records that CONSUME a geometry_hash + simulation_output_hash
   (validated in pipeline.py) and reference the simulation artifact
   ID (operator Phase 7: "the render should reference the simulation
   artifact ID").

The CI note (honest): the external auditor reported cadquery as
persistently failing in the CI/audit environment. THIS session's
workspace measures OPERATIONAL. Both facts are recorded — the probe
artifact is environment-scoped, and the CI discrepancy remains an
open infrastructure item for the operator (Art. XV disclosure).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
PROBES_PATH = (REPO / "R413" / "PHYSICS_STACK_V1"
               / "GEOMETRY_AUTHORITY_PROBES.json")

#: THE CLOSED SET — the only authorities that may originate
#: engineering geometry. (Directive V2; adding an authority is a
#: contract change requiring a new registry version, never a silent
#: append.)
ENGINEERING_GEOMETRY_AUTHORITIES = frozenset({"cadquery"})

#: the visualization layer's admissible role (downstream only)
VISUALIZATION_ROLE = ("DOWNSTREAM_RENDERING: consumes a geometry_hash "
                      "and a simulation_output_hash; cannot originate "
                      "or independently validate engineering geometry")

#: renderer ids (kept in sync with coverage.VISUALIZATION_SOURCE_IDS)
RENDERER_IDS = frozenset({
    "blender", "blender_rigidbody", "sofa_blender_bridge",
})

VERDICT_BOUNDARY_OK = "BOUNDARY_OK"
VERDICT_REJECTED_AUTHORITY = "REJECTED_GEOMETRY_AUTHORITY"
VERDICT_REJECTED_VALIDATOR = "REJECTED_GEOMETRY_VALIDATOR"
VERDICT_REJECTED_UNPROBED = "REJECTED_AUTHORITY_NOT_MEASURED"


def _load_probe() -> Dict[str, Any]:
    if not PROBES_PATH.exists():
        raise FileNotFoundError(
            f"geometry authority probe artifact missing: {PROBES_PATH} "
            "— authority may never be assumed without measurement "
            "(Art. VI)")
    return json.loads(PROBES_PATH.read_text())


def cadquery_measured_state() -> Dict[str, Any]:
    """The MEASURED state of the engineering geometry authority in
    THIS environment (Art. VI)."""
    probe = _load_probe()["probes"]["cadquery"]
    return {
        "state": probe["result"],
        "cadquery_version": probe.get("cadquery_version"),
        "probe": probe["probe"],
        "parametric_build_verification": probe.get(
            "parametric_build_verification"),
    }


def validate_geometry_spec(doc: Dict[str, Any]) -> List[str]:
    """GEOMETRY_SPEC boundary validation. EMPTY = valid.

    Enforces: authority is CadQuery (the closed authority set); the
    authority is MEASURED operational in this environment; the spec
    carries a geometry hash and parameters (geometry is DATA, not
    pictures — the V0 discipline); no renderer-originated geometry."""
    v: List[str] = []
    authority = doc.get("geometry_authority")
    if authority is None:
        v.append("geometry_authority is REQUIRED — engineering "
                 "geometry without a declared authority has no "
                 "single source of truth (operator Phase 4)")
    elif authority not in ENGINEERING_GEOMETRY_AUTHORITIES:
        if authority in RENDERER_IDS or authority == "blender":
            v.append(
                f"REJECTED_GEOMETRY_AUTHORITY: {authority!r} cannot "
                "originate engineering geometry — CadQuery is the "
                "engineering geometry authority; Blender is a "
                "downstream visualization/rendering system (operator "
                "directive V2 Phase 4; two competing sources of "
                "geometric truth are structurally forbidden)")
        else:
            v.append(
                f"REJECTED_GEOMETRY_AUTHORITY: {authority!r} is not "
                "in the closed authority set "
                f"{sorted(ENGINEERING_GEOMETRY_AUTHORITIES)} — adding "
                "an authority is a contract change (new registry "
                "version), never a silent append")
    if not doc.get("geometry_hash"):
        v.append("geometry_hash required — geometry is data with a "
                 "canonical pin, not a picture")
    if not doc.get("parameters"):
        v.append("parameters required — parametric geometry "
                 "specification (the CadQuery authority is "
                 "PARAMETRIC engineering geometry)")
    if doc.get("origin") in RENDERER_IDS:
        v.append(
            f"REJECTED_GEOMETRY_AUTHORITY: origin {doc['origin']!r} "
            "is a renderer — renderer-originated geometry may never "
            "enter engineering validation")
    # measured availability (Art. VI) — only when the authority itself
    # is the expected one
    if authority in ENGINEERING_GEOMETRY_AUTHORITIES:
        state = cadquery_measured_state()
        if state["state"] != "OPERATIONAL":
            v.append(
                f"authority {authority!r} measures "
                f"{state['state']!r} in this environment — the "
                "honest failure state is "
                "INCOMPLETE_GEOMETRY_AUTHORITY_UNAVAILABLE (Art. LXI), "
                "never a fabricated geometry run")
    return v


def validate_geometry_validation_record(doc: Dict[str, Any]
                                        ) -> List[str]:
    """Geometry VALIDATION records may cite only the authority or
    derived deterministic checks — never a renderer."""
    v: List[str] = []
    validator = doc.get("validated_by") or doc.get("validator")
    if validator in RENDERER_IDS:
        v.append(
            f"REJECTED_GEOMETRY_VALIDATOR: {validator!r} — a render "
            "cannot independently validate engineering geometry "
            "(operator Phase 4; the boundary is visual, never "
            "evidential)")
    if not doc.get("geometry_hash"):
        v.append("geometry validation must pin the geometry_hash it "
                 "validates")
    return v


def validate_render_record(doc: Dict[str, Any]) -> List[str]:
    """RENDERING boundary validation (operator Phase 7 contract,
    encoded now):

    - the render must reference the simulation artifact (output hash
      AND artifact id) — so no PDF/website can ever imply that
      Blender established the physical result;
    - the render must consume an EXISTING geometry_hash (downstream
      of CadQuery), never originate one;
    - the renderer must be a visualization-layer id.
    """
    v: List[str] = []
    if not doc.get("simulation_output_hash"):
        v.append("a render without a simulation_output_hash is "
                 "VISUALIZATION_WITHOUT_COMPUTATION — the forbidden "
                 "'AI -> Blender picture -> looks physically "
                 "plausible' path (operator anti-pattern)")
    if not doc.get("simulation_artifact_id"):
        v.append("the render must reference the simulation ARTIFACT "
                 "ID (operator Phase 7) — the PDF/website must never "
                 "imply Blender established the physical result")
    if not doc.get("geometry_hash"):
        v.append("the render must consume the CadQuery geometry_hash "
                 "(downstream of the authority) — a render never "
                 "originates engineering geometry")
    if doc.get("renderer") not in RENDERER_IDS:
        v.append("renderer must be a visualization-layer id "
                 f"({sorted(RENDERER_IDS)})")
    if doc.get("originates_geometry"):
        v.append("REJECTED_GEOMETRY_AUTHORITY: a render record may "
                 "never declare itself the origin of engineering "
                 "geometry")
    return v

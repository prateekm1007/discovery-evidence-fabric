"""physics_core.py — R394 section 7-11: the ONE deterministic physics
solver (V0).

SELECTION JUSTIFICATION (directive section 7: "Choose the first solver
based on: existing portfolio fit, deterministic reproducibility,
analytical reference case, CAD binding, failure-mode coverage, speed" —
the consultant's 1D hydraulic network recommendation is ACCEPTED and
independently justified):

  1. PORTFOLIO FIT      the program's flagship reality-loop artifact
                        (P-07 drainage floor) is a hydraulic drainage
                        device; the R390 REAL closure (floor lumen
                        diameter 0.6 -> 0.5471 mm, EQ-1 conductance
                        compensation) is exactly a 1D hydraulic
                        conductance question. The strongest existing
                        evidence chain is hydraulic.
  2. DETERMINISM        1D laminar incompressible network flow reduces
                        to a LINEAR system (Poiseuille conductances +
                        mass conservation). No stochastic terms, no
                        mesh, no solver seed. Identical inputs ->
                        bit-identical outputs (numpy linalg on the same
                        matrix; the residual is recorded).
  3. ANALYTICAL REFERENCE closed forms exist for every topology the V0
                        supports: single tube (Q = dP*pi*d^4/(128*mu*L)),
                        series (resistances add), parallel (conductances
                        add). validate_against_reference() proves the
                        solver matches closed form to < 1e-12 relative.
  4. CAD BINDING        the R381 parametric templates expose the exact
                        segment parameters the solver consumes
                        (primary_lumen_diameter_mm,
                        floor_lumen_diameter_mm, length_mm) — geometry
                        identity + hash flow straight from the CAD
                        rebuild envelope.
  5. FAILURE-MODE COVERAGE the failure mode the P-07 invention EXISTS
                        for (primary lumen obstruction) is natively a
                        network-flow question: obstruction = segment
                        conductance reduction; alternative path =
                        parallel branch. NORMAL / PARTIAL / SEVERE /
                        ALTERNATIVE PATH are network scenarios.
  6. SPEED              one linear solve — microseconds. The loop in
                        section 12 can afford thousands of evaluations.

SCOPE DISCIPLINE (directive section 7: "Do not build a solver suite"):
  this module implements exactly ONE physical model. Thermal,
  structural, EM, and multi-physics solvers are OUT OF SCOPE for V0;
  a mechanism whose failure mode is not hydraulic receives
  MECHANISM_NOT_SIMULATABLE — never a forced analogy (section 9).

CONTRACT (directive section 8) — input:
    geometry identity + geometry hash + material/fluid properties +
    boundary conditions + operating conditions + model version
  output:
    predicted quantities (with units) + convergence/error + assumptions
    + limitations + solver version + input hash + output hash
  emission:
    COMPUTATIONAL_RESULT through the EXISTING evidence architecture
    (Art. XXXVIII layer 4: requires a computation log — the input/output
    hashes, solver version, residual, and scenario record ARE the log;
    no parallel truth ledger is created).
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

SOLVER_VERSION = "hydraulic_network_1d/1.0.0"
MODEL_VERSION = "1d-laminar-incompressible-network/1.0.0"

# ---------------------------------------------------------------------------
# Declared thresholds (Art. XXVII — provenance, class, uncertainty)
# ---------------------------------------------------------------------------
THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "LAMINAR_RE_LIMIT": {
        "value": 2300,
        "epistemic_class": "ENGINEERING",
        "justification": ("the standard laminar-turbulent transition "
                          "Reynolds number for internal pipe flow; above "
                          "it the Poiseuille conductance model is "
                          "physically invalid (the result is flagged "
                          "MODEL_INVALIDITY, never silently returned)"),
        "uncertainty": "transition is gradual in reality; 2300 is the "
                       "conventional onset",
    },
    "REFERENCE_REL_TOL": {
        "value": 1e-12,
        "epistemic_class": "ENGINEERING",
        "justification": ("a linear solve of a closed-form problem must "
                          "match to machine precision; anything looser "
                          "hides a formulation bug"),
        "uncertainty": "none",
    },
    "SEVERE_OBSTRUCTION_PCT": {
        "value": 90,
        "epistemic_class": "ENGINEERING",
        "justification": ("the P-07 package's own obstruction envelope "
                          "(the failure-mode scenarios the invention "
                          "exists for); representative severe case"),
        "uncertainty": "obstruction severity is continuous; 90% is the "
                       "declared severe scenario",
    },
    "PARTIAL_OBSTRUCTION_PCT": {
        "value": 50,
        "epistemic_class": "ENGINEERING",
        "justification": "declared representative partial scenario",
        "uncertainty": "as above",
    },
}

ASSUMPTIONS = (
    "laminar fully-developed Poiseuille flow in every segment",
    "incompressible Newtonian fluid with constant viscosity at the "
    "stated operating temperature",
    "rigid walls (no collapsible lumen mechanics)",
    "no gravity head (horizontal network; declare elevation explicitly "
    "if it matters — V0 does not model it)",
    "steady state (no transient pressure waves)",
)
LIMITATIONS = (
    "invalid above the laminar Reynolds limit (flagged per segment, "
    "never silently returned)",
    "no wall compliance, no non-Newtonian rheology, no slip",
    "junction losses are not modelled (V0 counts only developed-flow "
    "resistance); short segments overestimate conductance",
    "obstruction is modeled as a uniform diameter reduction of the "
    "segment, not as a discrete stenosis geometry",
)

_UNIT_MM_HG_TO_PA = 133.322


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# The network model
# ---------------------------------------------------------------------------

def poiseuille_conductance(diameter_mm: float, length_mm: float,
                           viscosity_mPa_s: float) -> float:
    """Hydraulic conductance of a circular segment, in (mL/s)/mmHg.

    G = pi*d^4 / (128*mu*L) with d in m, L in m, mu in Pa.s, G in
    m^3/(s.Pa); converted to (mL/s)/mmHg for physiological units.

    R405 CORRECTION (unit-conversion defect, disclosed at
    R405/UNIT_CONVERSION_DEFECT_DISCLOSURE.json): converting a
    conductance FROM per-Pa TO per-mmHg MULTIPLIES by 133.322 (each
    mmHg = 133.322 Pa drives 133.322x the per-Pa flow). The pre-R405
    code divided, making every absolute conductance and therefore
    every absolute flow emitted by solve_network 133.322^2 = 17,774.7x
    too small (node pressures are fixed in mmHg, so Q = G * dP_mmHg
    inherited the same factor). All recorded RATIO-based verdicts
    (BEATS_BASELINE margins, G_floor/G_primary, conductance
    restoration ratios, KEEP/KILL gate decisions) are unaffected —
    the constant factor cancels. Physical magnitude sanity: a 1.0 mm
    ID x 90 mm water segment at 8 mmHg passes ~17 mL/min, not
    ~9.8e-6 mL/min.
    """
    if diameter_mm < 0 or length_mm <= 0 or viscosity_mPa_s <= 0:
        raise ValueError(
            f"non-physical segment: d={diameter_mm} mm, L={length_mm} mm, "
            f"mu={viscosity_mPa_s} mPa.s (plausibility bound violated "
            "before solve — R394 s11)")
    if diameter_mm == 0:
        return 0.0  # fully obstructed segment (ALTERNATIVE_PATH scenario
        # at 100%): conductance zero is the physical statement, not an
        # error — flow through the blocked path must vanish, not crash
    d_m = diameter_mm * 1e-3
    L_m = length_mm * 1e-3
    mu_pa_s = viscosity_mPa_s * 1e-3
    g_si = math.pi * d_m ** 4 / (128.0 * mu_pa_s * L_m)   # m3/(s.Pa)
    # per-mmHg conductance = per-Pa conductance x 133.322 (R405:
    # MULTIPLY — the pre-R405 divide was the defect); m3 -> mL is 1e6
    return g_si * 1e6 * _UNIT_MM_HG_TO_PA                 # (mL/s)/mmHg


def effective_diameter(diameter_mm: float, obstruction_pct: float) -> float:
    """Obstruction modeled as uniform diameter reduction: d_eff scales
    with the OPEN area fraction sqrt (d ~ sqrt of area) — a 50%
    obstruction (half the area closed) reduces diameter by sqrt(0.5)
    and conductance by 0.5^2 (Poiseuille d^4). Disclosed model choice
    (uniform stenosis, not discrete)."""
    pct = max(0.0, min(100.0, obstruction_pct))
    open_fraction = 1.0 - pct / 100.0
    return diameter_mm * math.sqrt(open_fraction)


# ---------------------------------------------------------------------------
# The solver (section 8 contract)
# ---------------------------------------------------------------------------

def solve_network(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Solve one 1D hydraulic network.

    spec (the FULL section-8 INPUT):
      geometry_identity   str       e.g. CAD model_id / parametric id
      geometry_hash       str       sha256 of the canonical geometry
      fluid               dict      viscosity_mPa_s, density_kg_m3,
                                    temperature_K (+ source class per
                                    field, Art. XXVII)
      boundary            dict      inlet_mmHg, outlet_mmHg (fixed
                                    pressure nodes)
      segments            list      {segment_id, node_a, node_b,
                                    diameter_mm, length_mm,
                                    obstruction_pct}
      operating_conditions dict     optional notes (e.g. temperature
                                    basis) — carried to the record

    Returns the section-8 OUTPUT record (see module docstring) with
    input_hash + output_hash; never mutates the spec.
    """
    required = ("geometry_identity", "geometry_hash", "fluid",
                "boundary", "segments")
    for k in required:
        if k not in spec:
            raise ValueError(f"solver input missing required key {k!r}")

    fluid = spec["fluid"]
    boundary = spec["boundary"]
    segments = list(spec["segments"])

    viscosity = float(fluid["viscosity_mPa_s"])
    density = float(fluid.get("density_kg_m3") or 993.0)

    inlet_p = float(boundary["inlet_mmHg"])
    outlet_p = float(boundary["outlet_mmHg"])

    # ---- plausibility bounds (section 11 — BEFORE the solve) --------
    violations = _plausibility_violations(spec)
    if violations:
        return {
            "solver_version": SOLVER_VERSION,
            "model_version": MODEL_VERSION,
            "status": "PLAUSIBILITY_BOUND_VIOLATED",
            "violations": violations,
            "input_hash": _sha(_canonical(spec)),
            "note": ("deterministic physical bound failed BEFORE "
                     "simulation; no computational result is emitted "
                     "and the candidate must not be advertised as "
                     "solver-validated (R394 s11)"),
        }

    # ---- assemble the linear system ----------------------------------
    node_ids = sorted({s["node_a"] for s in segments} |
                      {s["node_b"] for s in segments})
    idx = {n: i for i, n in enumerate(node_ids)}
    n = len(node_ids)
    G = np.zeros((n, n))
    b = np.zeros(n)
    seg_meta: List[Dict[str, Any]] = []
    for s in segments:
        d_eff = effective_diameter(float(s["diameter_mm"]),
                                   float(s.get("obstruction_pct") or 0.0))
        g = poiseuille_conductance(d_eff, float(s["length_mm"]), viscosity)
        i, j = idx[s["node_a"]], idx[s["node_b"]]
        G[i, i] += g
        G[j, j] += g
        G[i, j] -= g
        G[j, i] -= g
        seg_meta.append({"segment_id": s["segment_id"],
                         "node_a": s["node_a"], "node_b": s["node_b"],
                         "diameter_mm": float(s["diameter_mm"]),
                         "effective_diameter_mm": round(d_eff, 6),
                         "length_mm": float(s["length_mm"]),
                         "obstruction_pct": float(
                             s.get("obstruction_pct") or 0.0),
                         "conductance_ml_s_mmhg": float(g)})  # full precision (no
        # decimal rounding — see flows note)

    # boundary conditions: fixed pressures. Defaults are TOPOLOGICAL
    # (first segment's node_a = inlet, last segment's node_b = outlet)
    # — never alphabetical guessing (measured defect: the series
    # reference case silently fixed the MIDDLE node as outlet).
    inlet_node = boundary.get("inlet_node") or (
        segments[0]["node_a"] if segments else None)
    outlet_node = boundary.get("outlet_node") or (
        segments[-1]["node_b"] if segments else None)
    fixed = {idx[inlet_node]: inlet_p, idx[outlet_node]: outlet_p}
    free = [i for i in range(n) if i not in fixed]
    for i, p in fixed.items():
        G[i, :] = 0.0
        G[i, i] = 1.0
        b[i] = p

    pressures = np.zeros(n)
    if free:
        Gff = G[np.ix_(free, free)]
        rhs = b[free].copy()
        fixed_cols = list(fixed.keys())
        fixed_vals = np.array([fixed[i] for i in fixed_cols])
        rhs = rhs - G[np.ix_(free, fixed_cols)] @ fixed_vals
        p_free = np.linalg.solve(Gff, rhs)
        pressures[free] = p_free
    for i, p in fixed.items():
        pressures[i] = p

    # residual: mass-conservation error at free nodes (the solver's own
    # error report — section 8 'convergence/error')
    residual = 0.0
    for i in free:
        net = float(G[i, :] @ pressures - b[i])
        residual = max(residual, abs(net))
    total_residual = residual

    # per-segment flows (positive: node_a -> node_b). Values are NOT
    # decimal-rounded — physiological flows are ~1e-6 mL/s and decimal
    # rounding destroys precision (measured: rel error 3e-7 on the
    # closed-form reference from round(...,9) alone). Full float
    # precision; JSON serializes deterministically.
    flows = []
    for s, m in zip(segments, seg_meta):
        i, j = idx[s["node_a"]], idx[s["node_b"]]
        q = m["conductance_ml_s_mmhg"] * (pressures[i] - pressures[j])
        flows.append({**m, "flow_ml_s": float(q),
                      "flow_ml_min": float(q) * 60.0})

    total_inlet_flow = sum(
        f["flow_ml_s"] for f, s in zip(flows, segments)
        if s["node_a"] == inlet_node)
    total_outlet_flow = sum(
        f["flow_ml_s"] for f, s in zip(flows, segments)
        if s["node_b"] == outlet_node)

    # Reynolds validity per segment (laminar assumption check)
    re_flags = []
    for f in flows:
        d_m = f["effective_diameter_mm"] * 1e-3
        q_m3_s = f["flow_ml_s"] * 1e-6
        area = math.pi * (d_m / 2.0) ** 2
        v = (q_m3_s / area) if area > 0 else 0.0
        re = (density * v * d_m) / (viscosity * 1e-3) if d_m > 0 else 0.0
        f["velocity_m_s"] = v
        f["reynolds"] = re
        if re > THRESHOLDS["LAMINAR_RE_LIMIT"]["value"]:
            re_flags.append({"segment_id": f["segment_id"],
                             "reynolds": re})

    node_pressures = {node_ids[i]: float(pressures[i]) for i in range(n)}
    output_core = {
        "predicted_quantities": {
            "total_flow_ml_min": float(total_inlet_flow * 60.0),
            "total_flow_ml_s": float(total_inlet_flow),
            "inlet_node_pressure_mmHg": inlet_p,
            "outlet_node_pressure_mmHg": outlet_p,
            "node_pressures_mmHg": node_pressures,
            "segment_flows": list(flows),
        },
        "units": {"flow": "mL/min (mL/s where stated)",
                  "pressure": "mmHg", "conductance": "(mL/s)/mmHg",
                  "velocity": "m/s", "reynolds": "dimensionless"},
        "convergence": {
            "mass_conservation_residual_ml_s": total_residual,
            "linear_solve": "numpy.linalg.solve (direct LU)",
            "reference_tolerance":
                THRESHOLDS["REFERENCE_REL_TOL"]["value"],
        },
        "model_validity": {
            "laminar_valid": not re_flags,
            "reynolds_flags": re_flags,
            "note": ("" if not re_flags else
                     "MODEL_INVALIDITY: laminar assumption exceeded on "
                     "flagged segments — the Poiseuille conductances are "
                     "not valid there; the result is DISCLOSED as "
                     "invalid for those segments, never silently used"),
        },
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
    status = "COMPUTATIONAL_RESULT"
    if re_flags:
        status = "COMPUTATIONAL_RESULT_MODEL_INVALIDITY"

    record = {
        "solver_version": SOLVER_VERSION,
        "model_version": MODEL_VERSION,
        "status": status,
        "evidence_class": "COMPUTATIONAL_RESULT",
        "input_hash": _sha(_canonical(spec)),
        "geometry_identity": spec.get("geometry_identity"),
        "geometry_hash": spec.get("geometry_hash"),
        **output_core,
    }

    # R396 D.2 — post-solve physical caps (flow/energy/mass/
    # attenuation families), still BEFORE any expensive downstream
    # compute. A violated cap demotes the record: NO computational
    # evidence is emitted for an unphysical result (the raw numbers
    # stay in the record for audit — never hidden, never cited).
    cap_violations = _physical_cap_violations(record, spec)
    if cap_violations:
        record["status"] = "PLAUSIBILITY_BOUND_VIOLATED"
        record["violations"] = cap_violations
        record["cap_check_note"] = (
            "post-solve physical cap failed (R396 D.2: flow/energy/"
            "mass/attenuation families); predicted quantities are "
            "retained for audit but this is NOT computational "
            "evidence — the input envelope is unphysical or outside "
            "the declared domain")

    record["output_hash"] = _sha(_canonical(
        {k: v for k, v in record.items() if k != "output_hash"}))
    return record


# ---------------------------------------------------------------------------
# Section 11 — cheap physical plausibility bounds BEFORE the solve
# ---------------------------------------------------------------------------

def _plausibility_violations(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic, cheap bounds. Each violation states the bound, the
    measured value, and the class. Geometry-scale + flow-scale + power
    bounds; anything failing means the hypothesis is physically
    impossible or outside the model's domain — kill EARLY, before
    burning solve/loop compute (directive s11).

    R396 Phase D.2 completes the directive's six bound families
    (mass / energy / flow / thermal / attenuation / scale):
      thermal     liquid-water-class temperature range (the declared
                  V0 fluid class — NIST SRD 69 liquid range, class
                  ENGINEERING)
      flow/energy/mass  the inviscid Bernoulli cap (checked on the
                  solved output in _physical_cap_violations — a REAL
                  physical bound, not an invented envelope: no passive
                  network can deliver more flow than sqrt(2*dP/rho)
                  through the total area)
      attenuation  passive-network pressure monotonicity (checked on
                  solved node pressures — pressure cannot amplify
                  without a pump)
    """
    v: List[Dict[str, Any]] = []
    fluid = spec["fluid"]
    boundary = spec["boundary"]
    if float(fluid["viscosity_mPa_s"]) <= 0:
        v.append({"bound": "fluid.viscosity > 0",
                  "measured": fluid["viscosity_mPa_s"],
                  "class": "PHYSICAL"})
    # R396 D.2 — thermal bound (declared V0 fluid class)
    t_k = fluid.get("temperature_K")
    if t_k is not None:
        t_k = float(t_k)
        if not (273.15 <= t_k <= 373.15):
            v.append({
                "bound": "273.15 K <= fluid.temperature_K <= 373.15 K "
                         "(liquid-water-class fluid; the declared V0 "
                         "fluid class)",
                "measured": t_k,
                "class": "THERMAL",
                "basis": "NIST SRD 69 liquid-water range at 1 atm, "
                         "applied to the declared V0 fluid class "
                         "(water-like Newtonian liquid)",
                "threshold_class": "ENGINEERING"})
    if float(boundary["inlet_mmHg"]) <= float(boundary["outlet_mmHg"]):
        v.append({"bound": "inlet pressure > outlet pressure (forward "
                           "flow requested)",
                  "measured": {"inlet": boundary["inlet_mmHg"],
                               "outlet": boundary["outlet_mmHg"]},
                  "class": "PHYSICAL"})
    for s in spec["segments"]:
        sid = s.get("segment_id")
        if float(s["diameter_mm"]) <= 0:
            v.append({"bound": "segment diameter > 0",
                      "measured": s["diameter_mm"], "segment": sid,
                      "class": "PHYSICAL"})
        if float(s["diameter_mm"]) > 50.0:
            v.append({"bound": "segment diameter <= 50 mm (declared "
                               "V0 geometric scale — micro/medical "
                               "hydraulics domain)",
                      "measured": s["diameter_mm"], "segment": sid,
                      "class": "GEOMETRIC_SCALE"})
        if float(s["length_mm"]) <= 0:
            v.append({"bound": "segment length > 0",
                      "measured": s["length_mm"], "segment": sid,
                      "class": "PHYSICAL"})
        if float(s.get("obstruction_pct") or 0.0) > 100.0:
            v.append({"bound": "obstruction <= 100%",
                      "measured": s.get("obstruction_pct"),
                      "segment": sid, "class": "PHYSICAL"})
    return v


def _physical_cap_violations(record: Dict[str, Any],
                             spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """R396 D.2 — post-solve physical caps (flow / energy / mass /
    attenuation), derived from REAL physics, never invented envelopes:

      flow    the inviscid Bernoulli cap: no passive network can
              exceed v_max = sqrt(2 * dP / rho); per-segment velocity
              AND total flow are checked against their caps.
      energy  hydraulic dissipated power P = dP * Q_total <= dP * Q_cap
              (follows from the flow cap — reported separately because
              the directive names the family).
      mass    mass flow = rho * Q_total <= rho * Q_cap (likewise).
      attenuation  every solved node pressure lies within
              [outlet_p, inlet_p] — a passive hydraulic network cannot
              amplify pressure (no pump in the model).

    Checked immediately after the (cheap, deterministic) V0 solve —
    still BEFORE any expensive downstream CAD/simulation compute. A
    violation means the input envelope is unphysical or the network is
    outside the declared domain; the record is marked and NO
    computational evidence is emitted."""
    v: List[Dict[str, Any]] = []
    fluid = spec["fluid"]
    boundary = spec["boundary"]
    rho = float(fluid.get("density_kg_m3") or 993.0)
    dp_pa = (float(boundary["inlet_mmHg"])
             - float(boundary["outlet_mmHg"])) * _UNIT_MM_HG_TO_PA
    pq = record.get("predicted_quantities") or {}
    if dp_pa <= 0:
        return v  # degenerate pressure handled by the pre-solve bound
    v_max = (2.0 * dp_pa / rho) ** 0.5
    # per-segment velocity cap (flow family)
    for f in (pq.get("segment_flows") or []):
        vel = float(f.get("velocity_m_s") or 0.0)
        if vel > v_max * (1.0 + 1e-9):
            v.append({
                "bound": f"segment velocity <= inviscid cap "
                         f"sqrt(2*dP/rho) = {v_max:.4f} m/s",
                "measured": {"segment": f.get("segment_id"),
                             "velocity_m_s": vel},
                "class": "FLOW_CAP",
                "basis": "Bernoulli inviscid limit — no passive flow can "
                         "exceed it for the applied pressure gradient "
                         "(physical bound, not a declared envelope)"})
    # total flow / energy / mass caps
    q_total_ml_s = float(pq.get("total_flow_ml_s") or 0.0)
    area_total_m2 = 0.0
    for s in spec["segments"]:
        d_eff = effective_diameter(float(s["diameter_mm"]),
                                   float(s.get("obstruction_pct") or 0.0))
        area_total_m2 += math.pi * (d_eff * 1e-3 / 2.0) ** 2
    q_cap_m3_s = area_total_m2 * v_max
    q_cap_ml_s = q_cap_m3_s * 1e6
    if q_total_ml_s > q_cap_ml_s * (1.0 + 1e-9):
        v.append({
            "bound": "total flow <= inviscid cap A_total * "
                     f"sqrt(2*dP/rho) = {q_cap_ml_s:.6f} mL/s",
            "measured": q_total_ml_s,
            "class": "FLOW_CAP",
            "basis": "Bernoulli inviscid limit over the total effective "
                     "area (physical bound)"})
        power_w = dp_pa * q_total_ml_s * 1e-9
        power_cap_w = dp_pa * q_cap_m3_s
        v.append({
            "bound": "hydraulic dissipated power dP*Q <= dP*Q_cap = "
                     f"{power_cap_w:.6f} W",
            "measured": round(power_w, 9),
            "class": "ENERGY_CAP",
            "basis": "follows from the inviscid flow cap (physical "
                     "bound; the power family the directive names)"})
        v.append({
            "bound": f"mass flow rho*Q <= rho*Q_cap = "
                     f"{rho * q_cap_m3_s * 1000.0:.6f} g/s",
            "measured": round(rho * q_total_ml_s * 1e-6 * 1000.0, 9),
            "class": "MASS_CAP",
            "basis": "mass conservation at the inviscid flow cap "
                     "(physical bound)"})
    # attenuation: passive-network pressure monotonicity
    lo = float(boundary["outlet_mmHg"])
    hi = float(boundary["inlet_mmHg"])
    for node, p in (pq.get("node_pressures_mmHg") or {}).items():
        p = float(p)
        if p < lo - 1e-9 or p > hi + 1e-9:
            v.append({
                "bound": "passive node pressure within [outlet, inlet] "
                         "(pressure cannot amplify without a pump)",
                "measured": {"node": node, "pressure_mmHg": p},
                "class": "ATTENUATION",
                "basis": "passive hydraulic network physics (the solver "
                         "models no pump)"})
            break
    return v


# ---------------------------------------------------------------------------
# Section 9 — simulate the ACTUAL failure mode (vs BASELINE)
# ---------------------------------------------------------------------------

FAILURE_MODE_SCENARIOS = ("NORMAL", "PARTIAL_OBSTRUCTION",
                          "SEVERE_OBSTRUCTION", "ALTERNATIVE_PATH")


def simulate_failure_modes(spec: Dict[str, Any],
                           primary_segment_id: str,
                           target_metric: str = "total_flow_ml_min",
                           ) -> Dict[str, Any]:
    """Run the four declared failure-mode scenarios on ONE network.

    The invention's reason-to-exist must be REPRESENTED: obstruction of
    the primary path at declared severities, and the alternative-path
    case (primary fully blocked). If the spec has no such segment, the
    honest state is MECHANISM_NOT_SIMULATABLE — the candidate is NOT
    solver-validated (directive s9).
    """
    segment_ids = {s["segment_id"] for s in spec["segments"]}
    if primary_segment_id not in segment_ids:
        return {
            "status": "MECHANISM_NOT_SIMULATABLE",
            "solver_version": SOLVER_VERSION,
            "reason": (f"primary segment {primary_segment_id!r} not in "
                       "geometry — the failure mode the mechanism "
                       "exists for cannot be represented by this "
                       "solver; NO solver-validated claim is permitted "
                       "(R394 s9)"),
        }

    partial = THRESHOLDS["PARTIAL_OBSTRUCTION_PCT"]["value"]
    severe = THRESHOLDS["SEVERE_OBSTRUCTION_PCT"]["value"]

    def _scenario(name: str, obstruction_pct: float) -> Dict[str, Any]:
        segs = []
        for s in spec["segments"]:
            s2 = dict(s)
            if s["segment_id"] == primary_segment_id:
                s2["obstruction_pct"] = obstruction_pct
            segs.append(s2)
        spec2 = {**spec, "segments": segs}
        spec2["geometry_hash"] = _sha(_canonical(
            {"base": spec.get("geometry_hash"),
             "scenario": name, "obstruction_pct": obstruction_pct}))
        spec2["geometry_identity"] = (
            f"{spec.get('geometry_identity')}@{name}")
        r = solve_network(spec2)
        return {"scenario": name,
                "target_metric": target_metric,
                "value": (r.get("predicted_quantities", {})
                          .get(target_metric)),
                "result": r}

    scenarios = [
        _scenario("NORMAL", 0.0),
        _scenario("PARTIAL_OBSTRUCTION", partial),
        _scenario("SEVERE_OBSTRUCTION", severe),
        _scenario("ALTERNATIVE_PATH", 100.0),
    ]
    return {
        "status": "SIMULATED",
        "solver_version": SOLVER_VERSION,
        "failure_mode_scenarios": FAILURE_MODE_SCENARIOS,
        "scenarios": scenarios,
        "note": ("ALTERNATIVE_PATH = primary fully obstructed; the "
                 "candidate's reason-to-exist is the flow that remains "
                 "through the alternative branch"),
    }


# ---------------------------------------------------------------------------
# Section 10 — the baseline-beating invention rule
# ---------------------------------------------------------------------------

def compare_to_baseline(candidate_spec: Dict[str, Any],
                        baseline_spec: Dict[str, Any],
                        primary_segment_id: str,
                        scenario: str = "SEVERE_OBSTRUCTION",
                        target_metric: str = "total_flow_ml_min",
                        required_min: Optional[float] = None,
                        ) -> Dict[str, Any]:
    """Candidate vs BASELINE under the failure scenario. NEVER converts
    'simulation ran' into 'invention succeeded'.

    Allowed outcomes (directive s10): BEATS_BASELINE /
    DOES_NOT_BEAT_BASELINE / INCONCLUSIVE. Records baseline, candidate,
    target metric, operating condition, constraints, uncertainty,
    improvement.
    """
    cand = simulate_failure_modes(candidate_spec, primary_segment_id,
                                  target_metric)
    base = simulate_failure_modes(baseline_spec, primary_segment_id,
                                  target_metric)
    if cand.get("status") != "SIMULATED" or base.get("status") != "SIMULATED":
        return {
            "outcome": "INCONCLUSIVE",
            "reason": ("one or both networks are not simulatable "
                       f"(candidate={cand.get('status')}, "
                       f"baseline={base.get('status')}) — no comparison "
                       "claim is permitted (R394 s10)"),
            "candidate": cand, "baseline": base,
        }
    cand_val = _scenario_value(cand, scenario, target_metric)
    base_val = _scenario_value(base, scenario, target_metric)
    if cand_val is None or base_val is None:
        return {"outcome": "INCONCLUSIVE",
                "reason": "scenario result missing target metric",
                "candidate": cand, "baseline": base}

    improvement = (cand_val - base_val)
    rel = (improvement / base_val) if base_val not in (0.0, None) else None
    beats = cand_val > base_val
    uncertainty = {
        "model_class": "MODEL_DERIVED",
        "sources": [
            "uniform-obstruction stenosis model (not discrete geometry)",
            "junction losses unmodelled (V0)",
            "fluid viscosity is an input datum, not a measured "
            "operating condition",
        ],
    }
    verdict = "BEATS_BASELINE" if beats else "DOES_NOT_BEAT_BASELINE"
    record = {
        "outcome": verdict,
        # R396 D.1: the directive's exact vocabulary, surfaced verbatim
        # (CANDIDATE_DOES_NOT_BEAT_BASELINE must be a PRODUCIBLE state
        # of the machine, not only an internal comparison verdict)
        "candidate_outcome": (
            "CANDIDATE_BEATS_BASELINE" if verdict == "BEATS_BASELINE"
            else "CANDIDATE_DOES_NOT_BEAT_BASELINE"),
        "baseline": {"spec_summary": _spec_summary(baseline_spec),
                     "value": base_val},
        "candidate": {"spec_summary": _spec_summary(candidate_spec),
                      "value": cand_val},
        # R397 Phase 2: the directive's five required fields surfaced
        # TOP-LEVEL (BASELINE, CANDIDATE, TARGET METRIC, CONSTRAINTS,
        # RELATIVE IMPROVEMENT) — the nested comparison block keeps the
        # full detail; the top-level keys are the contract downstream
        # stages and the lifecycle mapping read
        "target_metric": target_metric,
        "relative_improvement": (round(rel, 6) if rel is not None
                                 else None),
        "comparison": {
            "scenario": scenario,
            "target_metric": target_metric,
            "operating_condition": {
                "inlet_mmHg": candidate_spec["boundary"]["inlet_mmHg"],
                "outlet_mmHg": candidate_spec["boundary"]["outlet_mmHg"],
                "fluid": candidate_spec["fluid"],
            },
            "improvement_absolute": round(improvement, 9),
            "improvement_relative": (round(rel, 6)
                                     if rel is not None else None),
        },
        "constraints": {
            "required_min": required_min,
            "meets_required_min": (cand_val >= required_min
                                   if required_min is not None else None),
        },
        "uncertainty": uncertainty,
        "solver_version": SOLVER_VERSION,
        "rule": ("'simulation ran' is NEVER 'invention succeeded'; the "
                 "outcome is comparative against the declared baseline "
                 "under the declared failure scenario (R394 s10)"),
    }
    return record


def _scenario_value(sim: Dict[str, Any], scenario: str,
                    metric: str) -> Optional[float]:
    for s in sim.get("scenarios", []):
        if s.get("scenario") == scenario:
            return s.get("value")
    return None


def _spec_summary(spec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "geometry_identity": spec.get("geometry_identity"),
        "geometry_hash": spec.get("geometry_hash"),
        "n_segments": len(spec.get("segments") or []),
        "segments": [
            {"segment_id": s["segment_id"],
             "diameter_mm": s["diameter_mm"],
             "length_mm": s["length_mm"]}
            for s in (spec.get("segments") or [])[:8]],
    }


# ---------------------------------------------------------------------------
# Section 7 — analytical reference validation (the solver attacks itself)
# ---------------------------------------------------------------------------

def validate_against_reference() -> Dict[str, Any]:
    """Closed-form checks. A solver that cannot reproduce Poiseuille on
    the trivial topologies is broken — this is run by tests AND by any
    consumer that wants to verify the instrument before trusting it
    (Art. III: the verifier never trusts the claimant)."""
    tol = THRESHOLDS["REFERENCE_REL_TOL"]["value"]
    fluid = {"viscosity_mPa_s": 1.0, "density_kg_m3": 998.0,
             "temperature_K": 310.15}
    results = []

    # single tube
    d, L = 0.6, 120.0
    dP = 8.0
    g = poiseuille_conductance(d, L, 1.0)
    q_closed = g * dP  # mL/s
    spec = {
        "geometry_identity": "reference:single-tube",
        "geometry_hash": _sha("reference:single-tube"),
        "fluid": fluid, "boundary": {"inlet_mmHg": 10.0,
                                     "outlet_mmHg": 10.0 - dP},
        "segments": [{"segment_id": "seg", "node_a": "A", "node_b": "B",
                      "diameter_mm": d, "length_mm": L}],
    }
    r = solve_network(spec)
    q_solver = r["predicted_quantities"]["total_flow_ml_s"]
    rel = abs(q_solver - q_closed) / max(abs(q_closed), 1e-30)
    results.append({"case": "single-tube-poiseuille",
                    "closed_form_ml_s": q_closed,
                    "solver_ml_s": q_solver,
                    "rel_error": rel, "pass": rel < tol})
    assert r["convergence"]["mass_conservation_residual_ml_s"] < 1e-9

    # series: two tubes — resistances add
    spec_series = {
        "geometry_identity": "reference:series",
        "geometry_hash": _sha("reference:series"),
        "fluid": fluid, "boundary": {"inlet_mmHg": 10.0, "outlet_mmHg": 2.0},
        "segments": [
            {"segment_id": "s1", "node_a": "A", "node_b": "M",
             "diameter_mm": d, "length_mm": L},
            {"segment_id": "s2", "node_a": "M", "node_b": "B",
             "diameter_mm": d, "length_mm": L},
        ],
    }
    r2 = solve_network(spec_series)
    q_series_closed = poiseuille_conductance(d, 2 * L, 1.0) * 8.0
    rel2 = abs(r2["predicted_quantities"]["total_flow_ml_s"]
               - q_series_closed) / q_series_closed
    results.append({"case": "series-resistances-add",
                    "closed_form_ml_s": q_series_closed,
                    "solver_ml_s": r2["predicted_quantities"]["total_flow_ml_s"],
                    "rel_error": rel2, "pass": rel2 < tol})

    # parallel: conductances add
    spec_parallel = {
        "geometry_identity": "reference:parallel",
        "geometry_hash": _sha("reference:parallel"),
        "fluid": fluid, "boundary": {"inlet_mmHg": 10.0, "outlet_mmHg": 2.0},
        "segments": [
            {"segment_id": "p1", "node_a": "A", "node_b": "B",
             "diameter_mm": d, "length_mm": L},
            {"segment_id": "p2", "node_a": "A", "node_b": "B",
             "diameter_mm": d, "length_mm": L},
        ],
    }
    r3 = solve_network(spec_parallel)
    q_parallel_closed = 2 * poiseuille_conductance(d, L, 1.0) * 8.0
    rel3 = abs(r3["predicted_quantities"]["total_flow_ml_s"]
               - q_parallel_closed) / q_parallel_closed
    results.append({"case": "parallel-conductances-add",
                    "closed_form_ml_s": q_parallel_closed,
                    "solver_ml_s": r3["predicted_quantities"]["total_flow_ml_s"],
                    "rel_error": rel3, "pass": rel3 < tol})

    all_pass = all(x["pass"] for x in results)
    return {"status": "REFERENCE_VALIDATED" if all_pass
            else "REFERENCE_FAILED",
            "tolerance": tol, "cases": results,
            "solver_version": SOLVER_VERSION}


# ---------------------------------------------------------------------------
# Section 8 — emit through the EXISTING evidence architecture
# ---------------------------------------------------------------------------

def to_computational_result(record: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap a solver output record as an Art. XXXVIII layer-4
    COMPUTATIONAL_RESULT evidence item — the computation log IS the
    input/output hash + solver version + residual + scenario identity.
    No parallel truth ledger: the record carries the same evidence
    class vocabulary the rest of the engine uses."""
    if record.get("status") not in ("COMPUTATIONAL_RESULT",
                                    "COMPUTATIONAL_RESULT_MODEL_INVALIDITY"):
        return {"evidence_class": "NOT_EMITTED",
                "reason": (f"solver status {record.get('status')!r} is not "
                           "a computational result — a plausibility "
                           "violation or non-simulatable mechanism emits "
                           "NO computational evidence (R394 s8/s9/s11)"),
                "solver_version": record.get("solver_version",
                                             SOLVER_VERSION)}
    return {
        "evidence_class": "COMPUTATIONAL_RESULT",
        "art_xxxviii_rank": 4,
        "solver_version": record["solver_version"],
        "model_version": record["model_version"],
        "input_hash": record["input_hash"],
        "output_hash": record["output_hash"],
        "geometry_identity": record.get("geometry_identity"),
        "geometry_hash": record.get("geometry_hash"),
        "computation_log": {
            "method": "linear solve of Poiseuille network (numpy.linalg)",
            "residual_ml_s":
                (record.get("convergence", {})
                 .get("mass_conservation_residual_ml_s")),
            "scenarios": [s.get("scenario") for s in
                          record.get("scenarios", [])] or None,
            "assumptions": record.get("assumptions"),
            "limitations": record.get("limitations"),
        },
        "model_validity": record.get("model_validity"),
        "epistemic_note": ("computation, not measurement — Art. XXXVIII "
                           "layer 4; may never be cited as physical "
                           "observation"),
    }


def conductance_ml_per_min_mmhg(d_mm: float, eta_mPa_s: float,
                                L_mm: float) -> float:
    """G = pi*d^4 / (128*eta*L), converted to mL/(min*mmHg).

    R410 RELOCATION NOTE: this function is the VERBATIM body of the
    legacy discovery_fabric/engine/reality_loop.py::
    _conductance_ml_per_min_mmhg (Gen-1 reality-loop code, deleted this
    round as superseded). The function itself is pure deterministic
    physics arithmetic (COMPUTATIONAL_RESULT class) — it lived in the
    wrong module. Relocated byte-equivalent so the R405/R406 test pins
    (tests/test_r405_external_audit_response.py,
    tests/test_r406_real_loop.py — the 17,774.7x unit-conversion-defect
    pins) keep testing the IDENTICAL arithmetic with the IDENTICAL
    values (Art. VII: relocation, never semantic change).

    Pure deterministic arithmetic from the package's EQ-1 (unit
    conversions: 1 mm = 1e-3 m; 1 mPa*s = 1e-3 Pa*s; 1 mmHg = 133.322 Pa;
    1 mL = 1e-6 m^3; 1 min = 60 s). COMPUTATIONAL_RESULT, computation-
    logged by the closure records (this function's inputs and output are
    recorded verbatim in those records).

    R405 CORRECTION (unit-conversion defect, disclosed at
    R405/UNIT_CONVERSION_DEFECT_DISCLOSURE.json): converting a
    conductance FROM per-Pa TO per-mmHg MULTIPLIES by 133.322 (a mmHg
    is 133.322 Pa, so each mmHg drives 133.322x the flow of each Pa).
    The pre-R405 code divided, making every absolute conductance
    133.322^2 = 17,774.7x too small. Ratio-based results (the NIST
    diameter compensation, conductance_restored_ratio) were unaffected
    because the constant error cancels in ratios. Physical magnitude
    sanity: a 0.6 mm ID x 100 mm water column at 1 mmHg passes
    ~0.25 mL/min, not ~1.4e-5 mL/min.
    """
    d_m = d_mm * 1e-3
    eta_pa_s = eta_mPa_s * 1e-3
    L_m = L_mm * 1e-3
    g_m3_per_s_pa = math.pi * d_m ** 4 / (128.0 * eta_pa_s * L_m)
    # m^3 -> mL is 1e6 (1 mL = 1e-6 m^3); min = 60 s; per-mmHg is
    # 133.322x per-Pa (R405: MULTIPLY, the pre-R405 divide was the
    # defect)
    return g_m3_per_s_pa * 1e6 * 60.0 * 133.322

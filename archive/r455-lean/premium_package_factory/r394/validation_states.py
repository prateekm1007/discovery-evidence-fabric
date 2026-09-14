"""validation_states.py — R394: split CAD validation from engineering
validation. PRESENT_AND_VALIDATED (one blob) is retired.

The CEO directive (13 / Priority 8): never collapse these states —
  CAD_PRESENT                model artifacts exist on disk
  CAD_VALIDATED              the deterministic geometry gates passed on
                             the built solid (G1-G8) AND the regeneration
                             check reproduced the geometry
  MECHANISM_GEOMETRY_PRESENT every invention-critical mechanism feature
                             maps to a named model feature/parameter
  ENGINEERING_MODEL_VALIDATED every governing equation proven
                             DIMENSIONALLY_CONSISTENT under recorded
                             units
  BENCH_TESTED               bench observations recorded in the evidence
                             ledger (physical layer)
  PHYSICALLY_VALIDATED       physical observation ledger entries exist
                             (Art. XXXVIII PHYSICAL_OBSERVATION)
  CLINICALLY_VALIDATED       clinical validation records exist
  REGULATORY_STATUS          NOT_ESTABLISHED unless recorded otherwise

Every state is DERIVED from artifacts (never hand-set; Art. VI), and the
derivation basis is recorded per state.
"""

from __future__ import annotations

import os
import re

_MECH_VERBS = re.compile(
    r"\b(activat|switch|open|close|respond|regulat|maintain|prevent|"
    r"valve|trigger|actuat|threshold)\w*", re.I)

# Actuation vocabulary: words that claim a MECHANICAL ACTUATING element
# (a switch, valve, trigger, threshold-activated mechanism). A subsystem
# whose text carries these words is only MAPPED when a model feature
# carries the same vocabulary — otherwise the actuation claim has no
# geometric implementation (the P-07 SS-03 defect class). Electronic
# behavior words (regulate/respond) are deliberately NOT actuation —
# power-conditioning electronics is not a mechanical switch claim.
_ACTUATION_RE = re.compile(
    r"\b(switch\w*|valve\w*|activat\w*|actuat\w*|trigger\w*|"
    r"threshold\w*)", re.I)


def _actuation_words(text: str) -> list:
    return sorted(set(m.group(0).lower() for m in
                      _ACTUATION_RE.finditer(text or "")))


def _has_glbs(model_dir: str) -> bool:
    return any(f.endswith(".glb")
               for f in os.listdir(model_dir)) if os.path.isdir(model_dir) \
        else False


def _cad_validated(model_dir: str, status: dict) -> bool:
    gv_path = os.path.join(model_dir, "GEOMETRY_VALIDATION_REPORT.json")
    if not os.path.isfile(gv_path):
        return False
    try:
        import json
        gv = json.load(open(gv_path, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    regen_ok = (status.get("regeneration_check") or {}).get("status") \
        == "REPRODUCIBLE"
    return bool(gv.get("valid")) and regen_ok


def mechanism_feature_mapping(pkg, model_dir: str) -> dict:
    """Map each subsystem to model parameters/features.

    TWO-TIER rule (deterministic, recorded — CEO hard gate):
      1. ACTUATION tier: if the subsystem's text carries actuation
         vocabulary (switch/valve/activate/trigger/threshold/...), the
         mapping requires a model parameter carrying the SAME
         vocabulary; otherwise the subsystem is UNMAPPED — an actuation
         claim without geometric implementation (the P-07 SS-03
         pressure-activated-switch defect).
      2. PASSIVE tier: mechanisms without actuation vocabulary map by
         shared canonical identifiers / exact parameter-name tokens
         (lumen, diameter, ...).

    A subsystem with mechanism-action language that maps to NO model
    feature in its tier is UNMAPPED — that is the
    MECHANISM_CLAIM_WITHOUT_GEOMETRIC_IMPLEMENTATION signal.
    """
    import json
    params_path = os.path.join(model_dir, "PARAMETERS.json")
    plist = []
    if os.path.isfile(params_path):
        try:
            plist = (json.load(open(params_path, encoding="utf-8"))
                     .get("parameters") or [])
        except Exception:  # noqa: BLE001
            plist = []
    param_ids = [str(p.get("param_id") or "") for p in plist]
    subs = ((pkg.eng.get("system_architecture") or {})
            .get("subsystems") or [])
    mapping = []
    for ss in subs:
        text = " ".join(str(ss.get(k, "")) for k in ("name", "function"))
        idents = set(re.findall(r"\b[A-Za-z]+(?:_[A-Za-z0-9]+)+\b", text))
        words = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", text)}
        matched = sorted(
            pid for pid in param_ids
            if any(i.lower() in pid.lower() for i in idents)
            or any(w in pid.lower() for w in words if len(w) >= 5))
        mechanism_bearing = bool(_MECH_VERBS.search(
            str(ss.get("function") or "")))
        actuation = _actuation_words(text)
        if actuation:
            # actuation tier: the actuation itself must have geometry
            act_matched = sorted(
                pid for pid in param_ids
                if any(a[:6] in pid.lower() for a in actuation))
            if act_matched:
                state, mapped = "MAPPED", act_matched
                tier = ("ACTUATION_MAPPED — model features carry the "
                        "actuation vocabulary")
            else:
                state, mapped = "UNMAPPED", []
                tier = ("ACTUATION_WITHOUT_GEOMETRY — the subsystem "
                        "claims an actuating element "
                        f"({', '.join(actuation)}) but no model feature "
                        "implements it")
        else:
            state, mapped = ("MAPPED" if matched else "UNMAPPED"), matched
            tier = ("PASSIVE — maps by shared identifiers/name tokens"
                    if matched else
                    "PASSIVE — no model feature shares the vocabulary")
        mapping.append({
            "subsystem_id": ss.get("id"),
            "subsystem_name": ss.get("name"),
            "mechanism_bearing": mechanism_bearing,
            "mapping_tier": tier,
            "actuation_vocabulary": actuation,
            "mapped_model_parameters": mapped,
            "state": state,
        })
    return {
        "subsystems": mapping,
        "all_mechanism_bearing_mapped": all(
            m["state"] == "MAPPED" for m in mapping
            if m["mechanism_bearing"]),
    }


def engineering_model_validated(equation_registry: dict) -> dict:
    """Every governing equation must be proven DIMENSIONALLY_CONSISTENT
    under recorded units for this state to be TRUE."""
    r374 = (equation_registry or {}).get("r374_validation_status") or {}
    totals = r374.get("totals") or {}
    n = totals.get("equations") or 0
    dim_ok = totals.get("dimensionally_validated") or 0
    return {
        "state": n > 0 and dim_ok == n,
        "equations": n,
        "dimensionally_validated": dim_ok,
        "basis": ("TRUE only when every governing equation is proven "
                  "DIMENSIONALLY_CONSISTENT under RECORDED units "
                  "(r374_validation_status); a single unproven equation "
                  "keeps the state FALSE (Art. XXVIII — never promoted)."),
    }


def derive_validation_states(pkg, model_dir: str,
                             equation_registry: dict,
                             loop_state: dict) -> dict:
    """The split state record for one package (shipped as
    MODEL/VALIDATION_STATES.json + surfaced in PACKAGE_MANIFEST)."""
    import json
    status = {}
    sp = os.path.join(model_dir, "3D_DESIGN_STATUS.json")
    if os.path.isfile(sp):
        try:
            status = json.load(open(sp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            status = {}

    mech = mechanism_feature_mapping(pkg, model_dir)
    eng = engineering_model_validated(equation_registry)

    # physical layer — Art. XXXVIII: only the observation ledger can
    # produce PHYSICAL_OBSERVATION; nothing here can fabricate it.
    phys_obs = ((loop_state or {}).get("evidence_class_counts") or {}) \
        .get("PHYSICAL_OBSERVATION", 0)
    bench = ((loop_state or {}).get("evidence_class_counts") or {}) \
        .get("BENCH_OBSERVATION", 0)

    cad_present = _has_glbs(model_dir)
    cad_validated = _cad_validated(model_dir, status)

    states = {
        "schema": "R394_VALIDATION_STATES",
        "package_id": pkg.pkg_id,
        "cad_present": {
            "state": cad_present,
            "basis": "GLB/STEP/STL model artifacts exist in MODEL/.",
        },
        "cad_validated": {
            "state": cad_validated,
            "basis": "GEOMETRY_VALIDATION_REPORT valid AND regeneration "
                     "check REPRODUCIBLE — deterministic geometry gates "
                     "on the built solid (CAD validation, never physical "
                     "validation).",
        },
        "mechanism_geometry_present": {
            "state": mech["all_mechanism_bearing_mapped"],
            "mapping": mech,
            "basis": "Every subsystem whose function carries "
                     "mechanism-action language maps to named model "
                     "parameters (shared canonical identifiers / exact "
                     "name tokens). UNMAPPED mechanism-bearing "
                     "subsystems fail the state (CEO hard gate).",
        },
        "engineering_model_validated": eng,
        "bench_tested": {
            "state": bench > 0,
            "basis": "BENCH_OBSERVATION evidence-class count in "
                     "LOOP_STATE.json.",
        },
        "physically_validated": {
            "state": phys_obs > 0,
            "basis": "PHYSICAL_OBSERVATION entries in the evidence "
                     "ledger (Art. XXXVIII — AI may not create these).",
        },
        "clinically_validated": {
            "state": False,
            "basis": "No clinical validation record exists for this "
                     "package (validation_matrix all NOT_PERFORMED).",
        },
        "regulatory_status": {
            "state": "NOT_ESTABLISHED",
            "basis": "No regulatory submission or clearance recorded "
                     "(remaining_unknowns lists the pathway as UNKNOWN).",
        },
        "language_rule": (
            "CAD_VALIDATED never implies physical, bench, clinical, or "
            "regulatory validation; each state is derived separately "
            "from its own artifact basis (CEO R392/R393 directive 13; "
            "Constitution Art. XXVIII)."),
    }
    return states


def compact_epistemic_line(states: dict) -> list:
    """The one-line buyer maturity view (CEO directive 15): restrained,
    derived, never hand-written."""
    if not states.get("cad_present", {}).get("state"):
        return ["COMPUTATIONALLY PROPOSED"]
    line = ["COMPUTATIONALLY PROPOSED"]
    if states.get("cad_validated", {}).get("state"):
        line.append("CAD VALIDATED")
    if not states.get("physically_validated", {}).get("state") \
            and not states.get("bench_tested", {}).get("state"):
        line.append("PHYSICAL VALIDATION PENDING")
    if states.get("engineering_model_validated", {}).get("state"):
        line.append("ENGINEERING MODEL VALIDATED")
    return line

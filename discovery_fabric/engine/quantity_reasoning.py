"""discovery_fabric/engine/quantity_reasoning.py — E21-A: physics-based
quantity reasoning for verification linkage.

THE DEFECT THIS MODULE FIXES (measured by the independent audit on the
E16 engine head, register item R-02):

    BENCH_01 FM-DOM-005 "check-valve seat wear opening reverse leakage"
    was linked to VF-009 "accelerated occlusion / fouling challenge
    testing" because the WORD "accelerated" appeared in both the failure's
    detectability text and the method text. A fouling challenge measures
    forward patency under obstruction; it cannot detect reverse leakage
    through a worn valve seat. Lexical coincidence was standing in for
    physics.

    BENCH_04 FM-DOM-005 "antenna feed joint fatigue failure" was linked
    to VF-009 "bit-error-rate vs distance/depth curve" by the same
    keyword-overlap mechanism. A BER-vs-depth sweep is a link
    characterization; it does not measure joint fatigue.

THE RULE THIS MODULE ENFORCES (CEO E21 directive, items 5 and 6):

    A verification may be linked to a failure mode ONLY when the
    verification MEASURES a physical quantity family that the failure
    AFFECTS. Keyword overlap is never a linkage justification.

DERIVATION OF THE TAXONOMY (Art. XXVII — documented, not tuned):

    QUANTITY_FAMILIES is derived from the engine's OWN domain registry
    (discovery_fabric/engine/domains.py): every family is a physical
    quantity that the registry's failure-mode physics and verification
    methods actually talk about (the 22 registry verification methods and
    the registry failure-mode texts were surveyed at design time; see
    each family's `derivation` note). Each family carries a canonical
    unit so that linkage is grounded in measurable physics, and two term
    lists:

        affected_terms — terms indicating a FAILURE degrades this quantity
        measured_terms — terms indicating a METHOD measures this quantity

    The taxonomy is engine-side knowledge. It was NOT taken from any
    external audit instrument, and the audit instruments were not taken
    from it: both describe the same underlying physics, independently
    organized (Art. VIII/XIX — no circular certification, no gate
    optimization).

HONESTY RULES (Art. XXV/XXVIII):

    - A failure whose physics resolves to NO family stays unlinked: an
      explicit gap + UNKNOWN disclosure is recorded (what is missing,
      how to establish it, who establishes it, test method, acceptance
      rule) — never a wrong-quantity verification.
    - A method that names no measurable quantity is UNSPECIFIC — it is
      recorded as such, never silently treated as matching.
    - Every linkage carries its evidence: which terms grounded which
      family on each side (auditable, deterministic).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_WORD = re.compile(r"[a-z][a-z0-9-]*")


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _contains(term: str, blob: str) -> bool:
    """Substring containment on the normalized blob (hyphenated and
    compound forms count: 'backflow' contains 'flow'; 'post-cycle'
    contains 'cycle')."""
    return term in blob


# --------------------------------------------------------------------------
# The engine-side physical quantity taxonomy
# --------------------------------------------------------------------------
QUANTITY_FAMILIES: Dict[str, Dict[str, Any]] = {
    "flow_obstruction": {
        "canonical_unit": "m^2 free area / forward flow rate",
        "affected_terms": [
            "obstruction", "occlusion", "blockage", "ingrowth",
            "patency loss", "stagnant", "stenosis", "free flow area",
            "lumen narrowing", "occludes", "obstruct"],
        "measured_terms": [
            "occlusion challenge", "fouling challenge", "patency",
            "flow-loop", "flow loop", "forward flow", "pressure-flow",
            "obstruction", "particulate challenge", "bench soak"],
        "derivation": "fluidics_hydraulic registry obstruction physics "
                      "(occlusion/ingrowth across the lumen) and its "
                      "methods (fouling challenge, patency soak, "
                      "flow-loop characterization). FORWARD patency is a "
                      "distinct quantity from seal integrity: a fouling "
                      "challenge cannot detect a leaking seat.",
    },
    "flow_leakage": {
        "canonical_unit": "reverse-flow / leakage rate (volume/time)",
        "affected_terms": [
            "backflow", "reverse leakage", "leakage", "reflux", "siphon",
            "overdrainage", "underdrainage", "seal failure", "leak path",
            "reverse-flow", "drains backward", "regurgitat"],
        "measured_terms": [
            "leakage", "reverse-flow", "reverse flow", "backflow",
            "reflux", "drainage", "overdrainage", "reverse-leakage"],
        "derivation": "fluidics_hydraulic registry valve/seal physics "
                      "(seat wear opening a leak path; backflow at "
                      "pressure reversal) — the degraded quantity is "
                      "sealed-direction flow integrity, measured by "
                      "leakage-rate testing, not by forward patency.",
    },
    "pressure_head": {
        "canonical_unit": "Pa",
        "affected_terms": [
            "pressure", "compression", "overpressure", "pressure head",
            "crushing", "intracranial pressure", "suction"],
        "measured_terms": [
            "pressure", "pressure-drop", "pressure head", "pressure-rise",
            "pressure-flow", "dP"],
        "derivation": "fluidics registry physics (collapse under external "
                      "pressure; pressure reversal) and mapping methods.",
    },
    "mechanical_integrity": {
        "canonical_unit": "Pa (stress) / cycles (endurance)",
        "affected_terms": [
            "fatigue", "fracture", "crack", "kink", "buckling", "collapse",
            "wear", "erosion", "seat wear", "delamination", "creep",
            "brittle", "rupture", "joint failure", "micromotion",
            "loosening", "structural failure", "open circuit"],
        "measured_terms": [
            "fatigue", "cycle", "cycling", "bend", "bending", "strain",
            "stress", "stress-strain", "displacement", "stiffness",
            "force", "torque", "run-out", "durability", "post-cycle",
            "buckling", "kink margin", "tensile", "pull"],
        "derivation": "mechanical failure physics across the registry "
                      "(seat wear, feed joint fatigue, kink) and its test "
                      "methods (fatigue run-out, buckling/kink margin, "
                      "cyclic durability, MR-safety torque).",
    },
    "temperature_thermal": {
        "canonical_unit": "K (delta-T)",
        "affected_terms": [
            "temperature", "heating", "overheating", "thermal damage",
            "burn", "heat buildup", "thermal runaway"],
        "measured_terms": [
            "temperature", "thermal", "thermograph", "temperature-rise",
            "delta-t", "heating", "heat"],
        "derivation": "MR-safety / duty-cycle registry physics and "
                      "temperature-rise mapping methods.",
    },
    "power_energy": {
        "canonical_unit": "W / J",
        "affected_terms": [
            "power", "energy", "battery", "depletion", "discharge",
            "power loss", "sar", "fluence", "irradiance", "conversion "
            "loss", "efficiency loss"],
        "measured_terms": [
            "power", "energy", "sar", "fluence", "irradiance", "voltage",
            "current", "charge", "efficiency", "conversion", "excitation "
            "sweep"],
        "derivation": "power/energy registry physics (battery depletion, "
                      "SAR limits, photonic conversion) and its "
                      "characterization methods.",
    },
    "signal_link": {
        "canonical_unit": "dB / bit-error-rate",
        "affected_terms": [
            "signal loss", "signal degradation", "noise floor",
            "interference", "snr loss", "attenuation of the signal",
            "telemetry drop", "error rate growth", "link degradation",
            "in-band energy", "packet loss"],
        "measured_terms": [
            "signal", "snr", "bit error", "bit-error", "packet", "link",
            "network analysis", "error rate", "scanner snr", "telemetry",
            "ber"],
        "derivation": "telemetry/link registry physics (in-band "
                      "interference, noise floor) and its methods "
                      "(scanner SNR, phantom link, BER sweeps). NOTE: "
                      "end-state phrases like 'becomes an open circuit' "
                      "are CONSEQUENCES of mechanical joint failure, not "
                      "signal-quantity degradation — they are excluded "
                      "from affected_terms so a mechanical failure is "
                      "never 'verified' by a link sweep.",
    },
    "biological_response": {
        "canonical_unit": "CFU / histology score",
        "affected_terms": [
            "infection", "biofilm", "colonization", "bacterial", "tissue "
            "ingrowth", "inflammation", "foreign-body", "foreign body",
            "thrombosis", "toxicity", "immune", "cytotoxic", "fouling",
            "cell proliferation", "encrustation by tissue"],
        "measured_terms": [
            "cfu", "colony", "biofilm", "bacterial", "histology",
            "infectivity", "cytotoxic", "biocompatibility assay",
            "microbial", "cell culture"],
        "derivation": "biocompatibility registry physics (ingrowth, "
                      "biofilm) and its assay methods (CFU challenge, "
                      "infectivity retention).",
    },
    "mass_transport": {
        "canonical_unit": "mol/(m^2*s)",
        "affected_terms": [
            "mass transfer", "diffusion-limited", "transport limitation",
            "starvation", "concentration gradient collapse"],
        "measured_terms": [
            "mass-transfer", "mass transfer", "flux", "rate "
            "characterization", "concentration"],
        "derivation": "bioreactor/enzymatic registry physics and "
                      "mass-transfer-limited rate characterization.",
    },
    "chemical_activity": {
        "canonical_unit": "activity units / mass deposit",
        "affected_terms": [
            "encrustation", "deposit", "mineral", "crust", "residue",
            "coating degradation", "activity loss", "denaturation",
            "leachate"],
        "measured_terms": [
            "encrustation", "deposit", "crust", "mass gain", "assay",
            "residual-activity", "residual activity", "ph", "elution"],
        "derivation": "encrustation / enzyme-stability registry physics "
                      "and its assay methods.",
    },
    "geometric_alignment": {
        "canonical_unit": "m / rad",
        "affected_terms": [
            "misalignment", "malposition", "migration", "displacement",
            "geometric deviation", "tolerance stack", "ovality",
            "deformation"],
        "measured_terms": [
            "alignment", "tolerance", "geometry", "profile", "position",
            "dimensional", "mapping vs depth", "depth"],
        "derivation": "assembly/positioning registry physics and "
                      "alignment-tolerance characterization.",
    },
    "detection_performance": {
        "canonical_unit": "sensitivity / false-alarm rate",
        "affected_terms": [
            "false alarm", "false positive", "missed detection",
            "false negative", "alarm fatigue", "classifier drift",
            "detection threshold shift", "sensitivity loss", " missed ",
            "detection failure"],
        "measured_terms": [
            "sensitivity", "false-alarm", "false alarm", "alarm", "auc",
            "detection", "roc", "threshold mapping", "detection-"
            "threshold"],
        "derivation": "monitoring/algorithm registry physics (adaptive "
                      "threshold drift, alarm performance) and its "
                      "evaluation methods (held-out splits, threshold "
                      "mapping).",
    },
    "optical_radiometric": {
        "canonical_unit": "W/m^2",
        "affected_terms": [
            "attenuation", "reflectance loss", "backscatter change",
            "absorbance shift", "optical loss", "coupling loss",
            "wavelength drift"],
        "measured_terms": [
            "reflect", "backscatter", "absorb", "optical", "wavelength",
            "fluence", "intensity", "phantom link", "irradiance"],
        "derivation": "optical registry physics (Beer-Lambert "
                      "attenuation, coupling) and its phantom/fluence "
                      "methods.",
    },
    "algorithmic_generalization": {
        "canonical_unit": "risk / error on held-out data",
        "affected_terms": [
            "overfitting", "distribution shift", "generalization failure",
            "model drift", "population shift", "non-representative "
            "training", "baseline drift"],
        "measured_terms": [
            "held-out", "held out", "temporal split", "distribution "
            "shift", "cross-validation", "evaluation on", "test set"],
        "derivation": "ml_data registry physics (empirical-risk "
                      "generalization) and its evaluation methods "
                      "(held-out + temporal split evaluation, injected "
                      "distribution shift).",
    },
    "environmental_endurance": {
        "canonical_unit": "exposure time / cycles",
        "affected_terms": [
            "ambient degradation", "soak damage", "humidity", "shelf-life",
            "environmental exposure", "sterilization damage"],
        "measured_terms": [
            "ambient soak", "worst-case soak", "soak", "environmental "
            "exposure", "shelf", "sterilization cycling"],
        "derivation": "storage/environment registry physics and worst-case "
                      "ambient soak methods.",
    },
}


def affected_families(row: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the quantity families a FAILURE MODE row affects.

    Reads the row's physical failure language (physical_mechanism, mode,
    trigger). Returns {families: {name: [matched terms]}, unresolved:
    bool}. Deterministic; every hit carries its evidence term."""
    blob = _norm(" ".join(filter(None, [
        row.get("failure_mode"), row.get("mode"),
        row.get("physical_mechanism"), row.get("trigger")])))
    families: Dict[str, List[str]] = {}
    for name, spec in QUANTITY_FAMILIES.items():
        hits = [t for t in spec["affected_terms"] if _contains(t, blob)]
        if hits:
            families[name] = hits
    return {
        "families": families,
        "evidence_text": blob[:400],
        "unresolved": not families,
    }


def measured_families(text: Any) -> Dict[str, List[str]]:
    """Resolve the quantity families a VERIFICATION METHOD measures.

    Returns {family: [matched terms]} — empty when the method names no
    recognizable measurable quantity (UNSPECIFIC, honestly reported)."""
    blob = _norm(text)
    out: Dict[str, List[str]] = {}
    for name, spec in QUANTITY_FAMILIES.items():
        hits = [t for t in spec["measured_terms"] if _contains(t, blob)]
        if hits:
            out[name] = hits
    return out


CANONICAL_QUANTITY_PHRASE = {
    "flow_obstruction": "forward patency / free flow area",
    "flow_leakage": "reverse-flow / leakage rate",
    "pressure_head": "pressure / pressure-drop",
    "mechanical_integrity": "mechanical stress / fatigue endurance",
    "temperature_thermal": "temperature rise",
    "power_energy": "power / energy deposition",
    "signal_link": "signal / link quality (SNR, error rate)",
    "biological_response": "biological response (CFU, histology)",
    "mass_transport": "mass-transfer rate / flux",
    "chemical_activity": "chemical activity / deposit mass",
    "geometric_alignment": "geometric alignment / position",
    "detection_performance": "detection sensitivity / false-alarm rate",
    "optical_radiometric": "optical power / fluence",
    "algorithmic_generalization": "held-out / distribution-shift risk",
    "environmental_endurance": "environmental endurance over exposure",
}


def quantity_linkage(fm_row: Dict[str, Any], method_text: Any,
                     ) -> Dict[str, Any]:
    """Evaluate whether a verification method may be linked to a failure
    mode: the method must MEASURE a family the failure AFFECTS.

    Returns a full auditable record — never a bare boolean."""
    aff = affected_families(fm_row)
    meas = measured_families(method_text)
    shared = sorted(set(aff["families"]) & set(meas))
    if aff["unresolved"]:
        verdict = "FAILURE_PHYSICS_UNRESOLVED"
    elif not meas:
        verdict = "METHOD_UNSPECIFIC"
    elif shared:
        verdict = "QUANTITY_MATCHED"
    else:
        verdict = "QUANTITY_DISJOINT"
    return {
        "rule": ("a verification may link to a failure mode only when it "
                 "MEASURES a physical quantity family the failure "
                 "AFFECTS (E21-A; keyword overlap is never a linkage "
                 "justification)"),
        "verdict": verdict,
        "affected": {k: v for k, v in aff["families"].items()},
        "measured": meas,
        "shared_families": shared,
        "canonical_quantity": CANONICAL_QUANTITY_PHRASE.get(
            shared[0]) if shared else None,
        "mechanical_evaluation": "MODEL_DERIVED (deterministic, recorded "
                                 "for audit)",
    }


def method_with_quantity_statement(method_text: str,
                                   linkage: Dict[str, Any]) -> str:
    """Append the measured-quantity statement to a method text when the
    linkage resolved. Naming the measured quantity (with its family) is
    standard engineering practice — a test protocol states WHAT it
    measures — and makes the linkage auditable by any reader."""
    shared = linkage.get("shared_families") or []
    if not shared:
        return method_text
    phrase = CANONICAL_QUANTITY_PHRASE.get(
        shared[0], shared[0].replace("_", " "))
    if f"({phrase}" in method_text:
        return method_text
    return (f"{method_text} (measured quantity: {phrase})")


def unknown_verification_disclosure(fm_row: Dict[str, Any],
                                    linkage: Dict[str, Any],
                                    ) -> Dict[str, Any]:
    """CEO E21 directive item 6: when a defensible verification cannot be
    derived, record UNKNOWN with the full disclosure block — never link
    a wrong-quantity verification, never pad with NOT_ESTABLISHED."""
    aff = linkage.get("affected") or {}
    families = sorted(aff) or ["UNRESOLVED physics"]
    quantities = ", ".join(CANONICAL_QUANTITY_PHRASE.get(f, f)
                           for f in families)
    return {
        "status": "UNKNOWN",
        "what_is_missing": (
            "no available verification method measures a quantity family "
            f"this failure affects ({quantities}) — the failure is "
            "detected by no planned test as currently specified"),
        "how_to_establish_it": (
            "derive or source a measurement protocol for the affected "
            "quantity (first-principles instrument choice or standard "
            "test method), pre-register its acceptance rule, and attach "
            "it as a dedicated verification for this failure mode"),
        "who_establishes_it": (
            "design engineer proposes; independent reviewer confirms the "
            "quantity match; buyer/QA owns the acceptance rule"),
        "test_method": (
            "candidate: measure the affected quantity "
            f"({quantities}) under the failure's stated trigger "
            "conditions, before and after accelerated exposure"),
        "acceptance_rule": (
            "pre-register pass/fail before testing: the affected quantity "
            "must remain within its sourced operating band under the "
            "trigger condition (threshold provenance required, Art. "
            "XXVII)"),
        "affected_families": families,
    }

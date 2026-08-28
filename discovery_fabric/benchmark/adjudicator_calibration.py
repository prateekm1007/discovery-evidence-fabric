"""Coder 2 Phase 4, B14 — CALIBRATE THE SEMANTIC ADJUDICATORS.

CEO directive B14: create a BLIND calibration set with KNOWN engineering
cases and measure, per adjudicator:

    adjudicator_A / adjudicator_B
    agreement  / disagreement   (inter-adjudicator)
    false_positive / false_negative  (vs ground truth)

Do NOT force consensus. Identify WHICH CLASSES of engineering judgments
are unstable.

Design (constitutionally constrained):
  * Art. VIII (certification must attack itself): the calibration cases
    are authored from ENGINEERING PRINCIPLES — each case carries a
    ground_truth_basis stating the physics/engineering fact that fixes
    its expected verdict. Cases are NOT derived from either adjudicator's
    behavior, and neither adjudicator is modified by this module
    (calibration is MEASUREMENT, not tuning — CEO: "do not force
    consensus", Art. VII/XXX forbids repairing an instrument by teaching
    it the answers).
  * The same two adjudicator entry points used in B9
    (adjudicate_a / adjudicate_b) are run UNMODIFIED on each case; the
    calibration set is blind in the sense that the adjudicators are
    generic functions with no calibration-specific behavior, and this
    module introduces no adjudicator code changes.
  * Verdict semantics (fixed before measurement, Art. XXVII):
      CORRECT      = instrument would not block
      INCORRECT    = instrument would block
      QUESTIONABLE = honest uncertainty; does not block, flags for review
    Therefore, on the scored (case, axis) pairs:
      false_positive := ground truth INCORRECT, verdict CORRECT
                        (a real defect the instrument waves through — the
                        most dangerous error for an audit layer)
      false_negative := ground truth CORRECT, verdict INCORRECT
                        (good engineering blocked — Art. V violation risk)
      QUESTIONABLE outcomes are counted separately as soft outcomes
      (uncertain_defect / uncertain_clean) and are NEVER folded into
      false_positive / false_negative.
  * Unstable-class rule (deterministic, no invented threshold): a
    judgment class (axis) is UNSTABLE if there is ANY inter-adjudicator
    disagreement on that axis OR ANY false positive / false negative on
    that axis by either adjudicator. Anything less than perfect
    stability is disclosed.
  * Residual self-reference disclosed honestly (Art. XV): both
    adjudicators AND this calibration set are authored by Coder 2.
    The external counterweight is B15 (human gold labels) — the first
    calibration point NOT authored by Coder 2.

Cases never enter the engine, the corpus depth contract, or the
benchmark input corpus; they exercise the two adjudicators only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .blind_adjudication import (
    AXES,
    ADJUDICATOR_A,
    ADJUDICATOR_B,
    adjudicate_a,
    adjudicate_b,
)

BASELINE_DIR = Path(__file__).resolve().parents[2] / \
    "artifacts" / "benchmark" / "baseline"
OUT_PATH = BASELINE_DIR / "ADJUDICATOR_CALIBRATION.json"

M = "mechanism_correctness"
R = "engineering_reasoning_correctness"
Q = "equation_applicability"
F = "failure_mode_correctness"
V = "verification_appropriateness"


def _inv(mechanism: str, intervention: str = "", expected: str = "",
         source_span: str = "", falsification: str = "") -> Dict[str, Any]:
    return {"mechanism": {"value": {
        "mechanism": mechanism,
        "intervention": intervention,
        "expected_effect": expected,
        "mechanism_source_span": source_span,
        "falsification_test": falsification,
    }}}


def _chain(roles: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"nodes": roles}


def _node(role: str, content: str, refs: Dict[str, Any] = None) -> Dict[str, Any]:
    return {"node_type": role, "content": content,
            "provenance": {"refs": refs or {}}}


# ===========================================================================
# The calibration set — known engineering cases (ground truth fixed by
# physics/engineering principles, stated per case)
# ===========================================================================
def build_calibration_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []

    # ---- C01: control-architecture contradiction --------------------------
    cases.append({
        "case_id": "CAL01_ACTIVE_PASSIVE_CONTRADICTION",
        "defect_class": "CONTROL_ARCHITECTURE_CONTRADICTION",
        "ground_truth_basis": "A device cannot simultaneously be under "
        "closed-loop servo control and operate passively in an open loop "
        "with no control system; the two architecture claims contradict "
        "each other, so the mechanism claim is not correct as stated.",
        "expected": {M: "INCORRECT"},
        "signature_texts": ["intracranial pressure drainage shunt valve "
                            "flow resistance catheter hydrostatic"],
        "inv": _inv(
            mechanism="A closed-loop adaptive valve actively regulates "
                      "intracranial pressure: the device senses ICP and "
                      "adjusts drainage flow resistance through a "
                      "servo-controlled actuator that continuously adjusts "
                      "orifice area to maintain the target pressure setpoint.",
            intervention="servo-controlled variable-orifice valve",
            expected="ICP maintained at setpoint by active feedback control",
            source_span="an implanted valve adaptively maintains "
                        "intracranial pressure by modulating drainage "
                        "resistance",
            falsification="if ICP tracking error exceeds 2 mmHg over a "
                          "24 h window the control claim is falsified"),
        "eng": {
            "system_architecture": "The device operates passively in an "
                                   "open loop with no control system; "
                                   "drainage is driven by hydrostatic "
                                   "pressure alone.",
        },
    })

    # ---- C02: clean laminar Poiseuille drainage (false-positive control) --
    clean_fm = [
        {"graph_id": "FM-01", "failure_mode": "LUMEN_OCCLUSION",
         "mode": "debris occlusion of the drainage lumen",
         "physical_mechanism": "proteinaceous debris and encrustation "
         "deposit narrows the lumen and raises hydraulic resistance "
         "until drainage falls below the required floor",
         "verification_test": "measure hydraulic resistance across the "
         "catheter after 30-day flow exposure; acceptance < 1.5x baseline",
         "design_control": "larger-bore proximal lumen with flush port",
         "kill_condition": "occlusion rate > 20% at 30 days kills the "
                           "design"},
        {"graph_id": "FM-02", "failure_mode": "CATHETER_KINK_COLLAPSE",
         "mode": "kink-induced collapse of the distal catheter",
         "physical_mechanism": "bending below the minimum bend radius "
         "collapses the thin-wall lumen and abruptly stops flow",
         "verification_test": "measure flow at the minimum bend radius; "
         "retained flow > 80% of straight-lumen flow",
         "design_control": "reinforced coil wall with 3 mm bend radius",
         "kill_condition": "flow loss > 20% at 3 mm bend radius"},
        {"graph_id": "FM-03", "failure_mode": "INFECTION_BIOFILM",
         "mode": "biofilm colonization of the inner lumen",
         "physical_mechanism": "bacterial biofilm forms on the lumen "
         "wall and sheds colony-forming units into the drainage path",
         "verification_test": "count adherent CFU per cm2 after 7-day "
         "static CSF analogue exposure; acceptance < 10^3 CFU/cm2",
         "design_control": "antimicrobial lumen coating",
         "kill_condition": "CFU/cm2 > 10^4 in vitro"},
    ]
    clean_equations = [
        {"name": "Hagen-Poiseuille lumen flow",
         "selection_rationale": {"verdict": "APPLICABLE"},
         "applicability": "laminar Newtonian CSF flow in a rigid circular "
                          "fully-developed lumen; Re << 2300 verified",
         "invention_tie": "sets drainage resistance vs lumen radius for "
                          "the occlusion-margin design output"},
        {"name": "Reynolds number regime criterion",
         "selection_rationale": {"verdict": "CONDITIONAL"},
         "applicability": "regime check: laminar required for the "
                          "Poiseuille relation to hold",
         "invention_tie": "guards the laminar assumption over the full "
                          "flow range"},
    ]
    clean_chains = [
        _chain([
            _node("CLAIM", "lumen radius >= 0.5 mm keeps occlusion margin"),
            _node("PRINCIPLE", "Poiseuille: resistance scales as r^-4"),
            _node("EQUATION_MODEL", "Hagen-Poiseuille lumen flow",
                  {"equation_id": "EQ-POISEUILLE-01"}),
            _node("INPUT", "CSF viscosity 0.001 Pa.s at 37C"),
            _node("ASSUMPTION", "laminar regime, Re << 2300"),
            _node("OUTPUT", "resistance ratio computed from model"),
            _node("FAILURE_MODE", "lumen occlusion raises resistance",
                  {"failure_mode_ids": ["FM-01"]}),
            _node("VERIFICATION", "30-day hydraulic resistance test",
                  {"verification_ids": ["VM-01"]}),
        ]),
    ]
    cases.append({
        "case_id": "CAL02_CLEAN_LAMINAR_DRAINAGE",
        "defect_class": "CLEAN_CONTROL",
        "ground_truth_basis": "A passive drainage catheter whose mechanism "
        "is traceable to its source, whose Poiseuille governing equation "
        "is applied with its laminar/Newtonian/rigid-lumen regime "
        "explicitly stated and guarded by a Reynolds criterion, whose "
        "failure analysis covers the dominant fluidics failure modes with "
        "matched-quantity verifications and quantified acceptance, is "
        "correct engineering on every adjudicated axis.",
        "expected": {M: "CORRECT", R: "CORRECT", Q: "CORRECT", F: "CORRECT",
                     V: "CORRECT"},
        "signature_texts": ["PROXIMAL LUMEN OCCLUSION",
                            "CSF drainage catheter flow resistance lumen "
                            "viscosity hydrostatic shunt"],
        "inv": _inv(
            mechanism="A passive fixed-resistance drainage catheter "
                      "maintains CSF outflow from the ventricle to the "
                      "peritoneal space: the hydrostatic pressure "
                      "difference across the lumen drives flow, while the "
                      "fixed lumen radius sets drainage resistance so "
                      "that normal-pressure drainage stays within the "
                      "physiologic window and overdrainage is limited "
                      "when the patient stands.",
            intervention="0.5 mm radius reinforced silicone lumen",
            expected="drainage 0.3 mL/min at 10 mmHf driving pressure",
            source_span="a fixed-resistance catheter drains CSF from the "
                        "ventricle to the peritoneal space under "
                        "hydrostatic pressure with a set lumen radius "
                        "limiting overdrainage",
            falsification="bench flow measurement: if measured resistance "
                          "deviates > 15% from the Poiseuille prediction "
                          "the lumen model is falsified"),
        "eng": {
            "system_architecture": "passive open-loop drainage catheter; "
                                   "no control system, no sensors, no "
                                   "actuators",
            "engineering_reasoning_chains": {"chains": clean_chains},
            "engineering_core": {"governing_model": {
                "equations": clean_equations}},
            "failure_analysis": clean_fm,
            "verification_matrix": [
                {"acceptance": "hydraulic resistance < 1.5x baseline after "
                               "30 days (mmHg/(mL/min))",
                 "invention_tie": "occlusion margin for the 0.5 mm lumen"},
                {"acceptance": "retained flow > 80% at 3 mm bend radius",
                 "invention_tie": "kink control for reinforced wall"},
                {"acceptance": "< 10^3 CFU/cm2 adherent after 7 days",
                 "invention_tie": "biofilm control for coated lumen"},
            ],
            "validation_matrix": [
                {"method": "ISO 13485 bench flow loop with CSF analogue at "
                           "37C",
                 "result": "PROPOSED"},
            ],
            "kill_condition": "resistance drift > 50% at 30 days kills the "
                              "device concept",
            "design_outputs": [
                {"id": "DO-01", "spec": "lumen radius >= 0.5 mm"}],
            "design_graph": {
                "linkage_maps": {
                    "fm_parent_do": {"DO-01": ["FM-01", "FM-02", "FM-03"]},
                    "do_parent_di": {"DO-01": ["DI-01"]},
                },
                "counts": {"FM": 3},
            },
        },
    })

    # ---- C03: Poiseuille applied to turbulent flow ------------------------
    cases.append({
        "case_id": "CAL03_POISEUILLE_IN_TURBULENT_FLOW",
        "defect_class": "EQUATION_REGIME_VIOLATION",
        "ground_truth_basis": "The Hagen-Poiseuille relation is valid only "
        "for laminar, Newtonian, fully-developed flow in a circular rigid "
        "lumen. In a large-bore high-flow outlet where the Reynolds number "
        "is explicitly ~8000 (turbulent), applying Poiseuille as the "
        "governing APPLICABLE relation is a physics error: pressure drop "
        "no longer scales linearly with flow.",
        "expected": {Q: "INCORRECT"},
        "signature_texts": ["large-bore high-flow CSF drainage outlet "
                            "catheter turbulence pressure drop"],
        "inv": _inv(
            mechanism="A large-bore outlet catheter passes high-volume "
                      "drainage: the wide lumen keeps bulk flow velocity "
                      "and wall shear stress low so that the pressure drop "
                      "stays predictable across the physiologic flow "
                      "range.",
            intervention="3 mm outlet lumen",
            source_span="a large-bore outlet maintains predictable "
                        "pressure drop at high drainage volumes",
            falsification="if measured pressure drop deviates from the "
                          "linear prediction the model is falsified"),
        "eng": {
            "system_architecture": "passive large-bore outlet, open loop",
            "engineering_core": {"governing_model": {"equations": [
                {"name": "Hagen-Poiseuille outlet pressure drop",
                 "selection_rationale": {"verdict": "APPLICABLE"},
                 "applicability": "turbulent conditions at Re ~ 8000 in "
                                  "the outlet lumen",
                 "invention_tie": "predicts outlet pressure drop vs flow"},
            ]}},
        },
    })

    # ---- C04: verification measures a disjoint quantity -------------------
    cases.append({
        "case_id": "CAL04_VERIFICATION_WRONG_QUANTITY",
        "defect_class": "VERIFICATION_QUANTITY_DISJOINT",
        "ground_truth_basis": "A verification must measure the physical "
        "quantity that governes the failure mode. The failure mode is "
        "mechanical fatigue fracture of the superelastic anchor under "
        "cyclic pulsation (stress/strain/cycles); a test that measures "
        "steady-state drainage flow rate cannot detect fatigue at all.",
        "expected": {V: "INCORRECT"},
        "signature_texts": ["superelastic anchor fatigue fracture strain "
                            "stress cyclic migration"],
        "inv": _inv(
            mechanism="A superelastic nitinol anchor self-expands against "
                      "the vessel wall: radial contact force resists "
                      "migration under cyclic pressure pulsation while "
                      "the strain plateau keeps wall stress below the "
                      "fatigue endurance limit.",
            intervention="self-expanding nitinol anchor",
            source_span="a superelastic anchor resists migration by radial "
                        "contact force",
            falsification="if anchor displacement exceeds 2 mm after 10^7 "
                          "pulsation cycles the fixation claim is "
                          "falsified"),
        "eng": {
            "system_architecture": "passive self-expanding anchor; no "
                                   "control system",
            "failure_analysis": [
                {"graph_id": "FM-11", "failure_mode": "ANCHOR_FATIGUE_"
                 "FRACTURE",
                 "mode": "fatigue fracture of anchor struts",
                 "physical_mechanism": "cyclic strain amplitude above the "
                 "endurance limit initiates and propagates a crack through "
                 "the strut over 10^7 pulsation cycles",
                 "verification_test": "measure steady-state drainage flow "
                 "rate through the shunt at constant pressure",
                 "design_control": "strut width sized to keep strain "
                                   "amplitude below 0.6%",
                 "kill_condition": "any strut fracture before 10^8 cycles"},
            ],
        },
    })

    # ---- C05: mechanism pass-through (the measured B8 defect) -------------
    cases.append({
        "case_id": "CAL05_MECHANISM_PASSTHROUGH",
        "defect_class": "MECHANISM_PASSTHROUGH",
        "ground_truth_basis": "A mechanism claim that is a verbatim "
        "pass-through of the input text, below the corpus substance floor, "
        "carrying no source span, no falsification path, and no "
        "engineering reasoning chains, is not correct engineering "
        "reasoning — it is transcription. (This is the defect measured on "
        "all 12 rejected benchmark runs: mechanism body words == input "
        "mechanism words, e.g. 21 == 21.)",
        "expected": {M: "INCORRECT", R: "INCORRECT"},
        "signature_texts": ["osmotic pump drug delivery membrane "
                            "diffusion concentration gradient"],
        "inv": _inv(
            mechanism="An osmotic pump drives drug delivery across a "
                      "semipermeable membrane by concentration gradient."),
        "eng": {
            "system_architecture": "osmotic pump assembly",
        },
    })

    # ---- C06: equations from the wrong physics family ---------------------
    cases.append({
        "case_id": "CAL06_EQUATION_FAMILY_MISMATCH",
        "defect_class": "EQUATION_FAMILY_MISMATCH",
        "ground_truth_basis": "A superelastic anchor mechanism is governed "
        "by structural mechanics (stress-strain, superelastic plateau, "
        "fatigue). Hydraulic relations (Hagen-Poiseuille pressure-flow, "
        "orifice discharge) cannot govern radial fixation of a solid "
        "anchor; presenting them as the APPLICABLE governing model is a "
        "physics error regardless of whether their own regime conditions "
        "are restated.",
        "expected": {Q: "INCORRECT"},
        "signature_texts": ["superelastic anchor radial force migration "
                            "strain stress nitinol"],
        "inv": _inv(
            mechanism="A superelastic nitinol anchor self-expands against "
                      "the vessel wall: the radial contact force resists "
                      "migration under pulsation while the strain plateau "
                      "keeps wall stress below the fatigue endurance limit.",
            intervention="self-expanding nitinol anchor",
            source_span="a superelastic anchor resists migration by radial "
                        "contact force",
            falsification="anchor displacement > 2 mm after 10^7 cycles "
                          "falsifies fixation"),
        "eng": {
            "system_architecture": "passive self-expanding anchor",
            "engineering_core": {"governing_model": {"equations": [
                {"name": "Hagen-Poiseuille radial pressure-flow relation",
                 "selection_rationale": {"verdict": "APPLICABLE"},
                 "applicability": "laminar Newtonian flow in a rigid "
                                  "circular fully-developed lumen",
                 "invention_tie": "predicts radial holding pressure vs "
                                  "flow"},
                {"name": "Orifice discharge relation",
                 "selection_rationale": {"verdict": "APPLICABLE"},
                 "applicability": "sharp-edged short restriction with a "
                                  "discharge coefficient",
                 "invention_tie": "predicts flow through the anchor "
                                  "window"},
            ]}},
        },
    })

    # ---- C07: clean PASSIVE structural mechanism (FP control) -------------
    cases.append({
        "case_id": "CAL07_CLEAN_PASSIVE_ANCHOR",
        "defect_class": "CLEAN_CONTROL",
        "ground_truth_basis": "Passivity is not a defect. A mechanism that "
        "is honestly and CONSISTENTLY passive — no active-control claim "
        "anywhere, physical quantities named, causal relation stated, "
        "traceable, testable — is correct engineering. An instrument that "
        "blocks consistent passive designs is a false-positive machine "
        "(Art. V).",
        "expected": {M: "CORRECT"},
        "signature_texts": ["ANCHOR MIGRATION",
                            "superelastic anchor strain stress radial "
                            "force fatigue nitinol"],
        "inv": _inv(
            mechanism="A superelastic nitinol anchor passively self-expands "
                      "against the vessel wall after deployment: the "
                      "recovery stress of the strain plateau produces a "
                      "radial contact force that resists axial migration "
                      "under pulsation, and because the response is an "
                      "intrinsic material property the device operates "
                      "open loop with no sensors and no actuators.",
            intervention="self-expanding nitinol anchor",
            source_span="a superelastic self-expanding anchor generates "
                        "radial force that resists migration",
            falsification="if anchor migration exceeds 2 mm after 10^7 "
                          "pulsation cycles the fixation claim is "
                          "falsified"),
        "eng": {
            "system_architecture": "passive open-loop anchor; no control "
                                   "system",
        },
    })

    # ---- C08: reversed causal direction -----------------------------------
    cases.append({
        "case_id": "CAL08_CAUSAL_DIRECTION_REVERSED",
        "defect_class": "CAUSAL_DIRECTION_REVERSED",
        "ground_truth_basis": "Overdrainage through a siphoning shunt is "
        "caused by EXCESSIVE total pressure drop (the siphon column adds "
        "to the valve gradient). Decreasing the pressure drop across the "
        "outlet LOWERS total resistance and therefore INCREASES flow — it "
        "worsens overdrainage. A mechanism claim stating that decreasing "
        "the outlet pressure drop reduces overdrainage reverses the causal "
        "direction of the governing fluid physics.",
        "expected": {M: "INCORRECT"},
        "signature_texts": ["siphon overdrainage shunt outlet pressure "
                            "drop drainage flow"],
        "inv": _inv(
            mechanism="An anti-siphon outlet chamber decreases the "
                      "pressure drop across the shunt outlet, which "
                      "reduces overdrainage when the patient stands by "
                      "lowering the siphon driving pressure across the "
                      "system.",
            intervention="low-resistance anti-siphon outlet",
            source_span="an outlet chamber modifies the siphon effect in "
                        "the standing patient",
            falsification="if overdrainage events are not reduced the "
                          "claim is falsified"),
        "eng": {
            "system_architecture": "passive outlet chamber, open loop",
        },
    })

    # ---- C09: failure analysis from the wrong physics family --------------
    cases.append({
        "case_id": "CAL09_FAILURE_MODES_OUTSIDE_FAMILY",
        "defect_class": "FAILURE_MODE_FAMILY_MISMATCH",
        "ground_truth_basis": "The failure analysis of a passive CSF "
        "drainage catheter must address the dominant fluidics failure "
        "physics (occlusion, kink/collapse, encrustation, infection). An "
        "analysis dominated by RF telemetry failures (antenna detuning, "
        "packet dropout) addresses physics the device does not contain.",
        "expected": {F: "INCORRECT"},
        "signature_texts": ["LUMEN OCCLUSION",
                            "CSF drainage catheter lumen flow resistance "
                            "viscosity shunt"],
        "inv": _inv(
            mechanism="A passive fixed-resistance drainage catheter "
                      "maintains CSF outflow from the ventricle to the "
                      "peritoneal space: the hydrostatic pressure "
                      "difference drives flow while the fixed lumen radius "
                      "sets drainage resistance so overdrainage is "
                      "limited when the patient stands.",
            intervention="0.5 mm radius silicone lumen",
            source_span="a fixed-resistance catheter drains CSF under "
                        "hydrostatic pressure",
            falsification="bench flow deviation > 15% from prediction "
                          "falsifies the lumen model"),
        "eng": {
            "system_architecture": "passive open-loop drainage catheter",
            "failure_analysis": [
                {"graph_id": "FM-21", "failure_mode": "ANTENNA_DETUNING",
                 "mode": "telemetry antenna detuning",
                 "physical_mechanism": "tissue dielectric loading shifts "
                 "the antenna resonance and drops the link budget",
                 "verification_test": "measure packet error rate over the "
                 "telemetry link",
                 "design_control": "tuning capacitor trimmed at "
                                   "manufacture",
                 "kill_condition": "link margin < 10 dB"},
                {"graph_id": "FM-22", "failure_mode": "PACKET_DROPOUT",
                 "mode": "telemetry packet dropout",
                 "physical_mechanism": "RF interference corrupts packets "
                 "during transmission bursts",
                 "verification_test": "count dropped packets per hour",
                 "design_control": "retransmission protocol",
                 "kill_condition": "dropout > 1%"},
            ],
        },
    })

    # ---- C10: acceptance criteria absent ----------------------------------
    cases.append({
        "case_id": "CAL10_ACCEPTANCE_CRITERIA_ABSENT",
        "defect_class": "ACCEPTANCE_CRITERIA_ABSENT",
        "ground_truth_basis": "A verification without a quantified "
        "acceptance criterion cannot adjudicate pass or fail — it is not a "
        "verification. Rows whose acceptance fields are TBD / NOT "
        "ESTABLISHED placeholders fail the definition of a verification.",
        "expected": {V: "INCORRECT"},
        "signature_texts": ["LUMEN OCCLUSION",
                            "CSF drainage catheter lumen flow resistance "
                            "shunt viscosity"],
        "inv": _inv(
            mechanism="A passive fixed-resistance drainage catheter "
                      "maintains CSF outflow from the ventricle to the "
                      "peritoneal space: the hydrostatic pressure "
                      "difference drives flow while the fixed lumen radius "
                      "sets drainage resistance so overdrainage is "
                      "limited when the patient stands.",
            intervention="0.5 mm radius silicone lumen",
            source_span="a fixed-resistance catheter drains CSF under "
                        "hydrostatic pressure",
            falsification="bench flow deviation > 15% from prediction "
                          "falsifies the lumen model"),
        "eng": {
            "system_architecture": "passive open-loop drainage catheter",
            "failure_analysis": [
                {"graph_id": "FM-31", "failure_mode": "LUMEN_OCCLUSION",
                 "mode": "debris occlusion of the drainage lumen",
                 "physical_mechanism": "debris deposits narrow the lumen "
                 "and raise hydraulic resistance",
                 "verification_test": "measure hydraulic resistance after "
                 "30-day exposure",
                 "design_control": "larger-bore proximal lumen",
                 "kill_condition": "occlusion > 20% at 30 days"},
            ],
            "verification_matrix": [
                {"acceptance": "TBD",
                 "invention_tie": "occlusion margin"},
                {"acceptance": "NOT ESTABLISHED",
                 "invention_tie": "kink control"},
            ],
            "validation_matrix": [
                {"method": "NOT_PERFORMED", "result": "NOT_PERFORMED"},
            ],
        },
    })

    # ---- C11: clean thermal design (FP control, second family) ------------
    cases.append({
        "case_id": "CAL11_CLEAN_THERMAL",
        "defect_class": "CLEAN_CONTROL",
        "ground_truth_basis": "A thermal ablation catheter governed by "
        "Fourier conduction with the conduction-gradient regime stated, an "
        "invention tie to the power budget, verification measuring the "
        "same thermal quantities the failure physics depends on, and "
        "quantified acceptance criteria, is correct on the adjudicated "
        "axes.",
        "expected": {Q: "CORRECT", V: "CORRECT"},
        "signature_texts": ["THERMAL OVERSHOOT",
                            "ablation catheter temperature thermal heat "
                            "conduction watts hotspot cooling"],
        "inv": _inv(
            mechanism="A cooled-tip ablation catheter controls tissue "
                      "temperature: circulating saline removes heat from "
                      "the electrode tip so that the conduction heat flux "
                      "into tissue stays below the threshold that would "
                      "char the adjacent surface and raise electrical "
                      "impedance.",
            intervention="internally cooled 3 mm electrode tip",
            source_span="a cooled-tip ablation electrode limits tissue "
                        "temperature by internal heat removal",
            falsification="if measured tip temperature exceeds 100C at "
                          "target power the thermal model is falsified"),
        "eng": {
            "system_architecture": "closed-loop irrigated catheter with "
                                   "pump control",
            "engineering_core": {"governing_model": {"equations": [
                {"name": "Fourier conduction heat flux",
                 "selection_rationale": {"verdict": "APPLICABLE"},
                 "applicability": "conduction through tissue with a "
                                  "thermal gradient; perfusion neglected "
                                  "as stated assumption",
                 "invention_tie": "tip temperature vs power for the "
                                  "power budget design output"},
                {"name": "Bio-heat perfusion term",
                 "selection_rationale": {"verdict": "CONDITIONAL"},
                 "applicability": "applies only above 3 mm from the tip "
                                  "where perfusion cooling is significant",
                 "invention_tie": "guards near-field vs far-field "
                                  "temperature prediction"},
            ]}},
            "failure_analysis": [
                {"graph_id": "FM-41", "failure_mode": "THERMAL_OVERSHOOT",
                 "mode": "tissue overheating at the electrode interface",
                 "physical_mechanism": "insufficient tip cooling raises "
                 "interface temperature above the char threshold",
                 "verification_test": "measure tip temperature and "
                 "interface thermal gradient at target power",
                 "design_control": "saline flow rate 20 mL/min",
                 "kill_condition": "interface > 100C at target power"},
                {"graph_id": "FM-42", "failure_mode": "HOTSPOT_FORMATION",
                 "mode": "local hotspot beyond the intended lesion margin",
                 "physical_mechanism": "asymmetric conduction produces a "
                 "local thermal hotspot outside the planned margin",
                 "verification_test": "map temperature rise across the "
                 "lesion margin with a thermocouple array",
                 "design_control": "symmetric electrode geometry",
                 "kill_condition": "hotspot > 5C above model at margin"},
            ],
            "verification_matrix": [
                {"acceptance": "tip temperature <= 90C at 30 W",
                 "invention_tie": "cooled-tip power budget"},
                {"acceptance": "thermal gradient within 10% of Fourier "
                               "model at 5 mm",
                 "invention_tie": "conduction model validity"},
            ],
            "validation_matrix": [
                {"method": "agar phantom thermocouple array per IEC "
                           "60601-2-2",
                 "result": "PROPOSED"},
            ],
            "kill_condition": "interface > 100C at target power kills the "
                              "concept",
        },
    })

    # ---- C12: clean traceability closure ----------------------------------
    cases.append({
        "case_id": "CAL12_CLEAN_TRACE_CLOSURE",
        "defect_class": "CLEAN_CONTROL",
        "ground_truth_basis": "Reasoning chains that close from claim "
        "through principle, equation model, input, assumption, output to "
        "both a failure mode and a verification — with the claim engaged "
        "to a quantitative model and both FM and verification linkage "
        "complete — are correct engineering reasoning.",
        "expected": {R: "CORRECT"},
        "signature_texts": ["LUMEN OCCLUSION",
                            "CSF drainage catheter lumen flow resistance "
                            "viscosity shunt"],
        "inv": _inv(
            mechanism="A passive fixed-resistance drainage catheter "
                      "maintains CSF outflow from the ventricle to the "
                      "peritoneal space: the hydrostatic pressure "
                      "difference drives flow while the fixed lumen radius "
                      "sets drainage resistance so overdrainage is "
                      "limited when the patient stands.",
            intervention="0.5 mm radius silicone lumen",
            source_span="a fixed-resistance catheter drains CSF under "
                        "hydrostatic pressure",
            falsification="bench flow deviation > 15% from prediction "
                          "falsifies the lumen model"),
        "eng": {
            "system_architecture": "passive open-loop drainage catheter",
            "engineering_reasoning_chains": {"chains": [
                _chain([
                    _node("CLAIM", "lumen radius >= 0.5 mm keeps occlusion "
                                   "margin"),
                    _node("PRINCIPLE", "Poiseuille: resistance scales as "
                                       "r^-4"),
                    _node("EQUATION_MODEL", "Hagen-Poiseuille lumen flow",
                          {"equation_id": "EQ-POISEUILLE-01"}),
                    _node("INPUT", "CSF viscosity 0.001 Pa.s at 37C"),
                    _node("ASSUMPTION", "laminar regime, Re << 2300"),
                    _node("OUTPUT", "resistance ratio computed from model"),
                    _node("FAILURE_MODE", "lumen occlusion raises "
                                          "resistance",
                          {"failure_mode_ids": ["FM-01"]}),
                    _node("VERIFICATION", "30-day hydraulic resistance "
                                          "test",
                          {"verification_ids": ["VM-01"]}),
                ]),
                _chain([
                    _node("CLAIM", "reinforced wall survives 3 mm bend "
                                   "radius"),
                    _node("PRINCIPLE", "bend curvature sets collapse "
                                       "moment"),
                    _node("EQUATION_MODEL", "beam bending curvature model",
                          {"equation_id": "EQ-BEND-02"}),
                    _node("INPUT", "wall thickness 0.15 mm"),
                    _node("ASSUMPTION", "elastic small-deflection bending"),
                    _node("OUTPUT", "collapse margin computed from model"),
                    _node("FAILURE_MODE", "kink collapse stops flow",
                          {"failure_mode_ids": ["FM-02"]}),
                    _node("VERIFICATION", "bend-radius retained flow test",
                          {"verification_ids": ["VM-02"]}),
                ]),
            ]},
            "failure_analysis": clean_fm,
            "verification_matrix": [
                {"acceptance": "resistance < 1.5x baseline at 30 days",
                 "invention_tie": "occlusion margin"},
                {"acceptance": "retained flow > 80% at 3 mm bend radius",
                 "invention_tie": "kink control"},
                {"acceptance": "< 10^3 CFU/cm2 at 7 days",
                 "invention_tie": "biofilm control"},
            ],
            "design_outputs": [
                {"id": "DO-01", "spec": "lumen radius >= 0.5 mm"},
                {"id": "DO-02", "spec": "bend radius >= 3 mm"}],
            "design_graph": {
                "linkage_maps": {
                    "fm_parent_do": {"DO-01": ["FM-01", "FM-03"],
                                     "DO-02": ["FM-02"]},
                    "do_parent_di": {"DO-01": ["DI-01"],
                                     "DO-02": ["DI-01"]},
                },
                "counts": {"FM": 3},
            },
        },
    })

    return cases


# ===========================================================================
# Calibration measurement
# ===========================================================================
def _verdict_of(result: Dict[str, Any], axis: str) -> Optional[str]:
    if not result.get("available"):
        return None
    return (result.get("axes") or {}).get(axis, {}).get("verdict")


def _score_adjudicator(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = {"scored": 0, "agree_gt": 0, "false_positive": 0,
           "false_negative": 0, "uncertain_defect": 0, "uncertain_clean": 0,
           "missed_defect_as_correct": [], "blocked_correct_as_incorrect": []}
    for r in rows:
        out["scored"] += 1
        gt, v = r["ground_truth"], r["verdict"]
        if v == gt:
            out["agree_gt"] += 1
        elif gt == "INCORRECT" and v == "CORRECT":
            out["false_positive"] += 1
            out["missed_defect_as_correct"].append(
                {"case_id": r["case_id"], "axis": r["axis"],
                 "defect_class": r["defect_class"]})
        elif gt == "CORRECT" and v == "INCORRECT":
            out["false_negative"] += 1
            out["blocked_correct_as_incorrect"].append(
                {"case_id": r["case_id"], "axis": r["axis"]})
        elif v == "QUESTIONABLE" and gt == "INCORRECT":
            out["uncertain_defect"] += 1
        elif v == "QUESTIONABLE" and gt == "CORRECT":
            out["uncertain_clean"] += 1
    return out


def run_calibration(cases: Optional[List[Dict[str, Any]]] = None,
                    out_path: Path = OUT_PATH) -> Dict[str, Any]:
    cases = cases if cases is not None else build_calibration_cases()
    rows: List[Dict[str, Any]] = []
    for case in cases:
        eng = case.get("eng") or {}
        inv = case.get("inv") or {}
        sig = case.get("signature_texts") or []
        a = adjudicate_a(eng, inv, sig)
        b = adjudicate_b(eng, inv, sig)
        expected = case["expected"]
        for axis, gt in expected.items():
            va, vb = _verdict_of(a, axis), _verdict_of(b, axis)
            rows.append({
                "case_id": case["case_id"],
                "defect_class": case["defect_class"],
                "axis": axis,
                "ground_truth": gt,
                "verdict_A": va,
                "verdict_B": vb,
                "A_vs_gt": _classify_vs_gt(gt, va),
                "B_vs_gt": _classify_vs_gt(gt, vb),
                "A_vs_B": ("AGREE" if va == vb else "DISAGREE"),
                "finding_classes_A": [f.get("class") for f in
                                      ((a.get("axes") or {}).get(axis) or {})
                                      .get("findings", [])],
                "finding_classes_B": [f.get("class") for f in
                                      ((b.get("axes") or {}).get(axis) or {})
                                      .get("findings", [])],
            })

    a_rows = [{"case_id": r["case_id"], "axis": r["axis"],
               "defect_class": r["defect_class"],
               "ground_truth": r["ground_truth"], "verdict": r["verdict_A"]}
              for r in rows]
    b_rows = [{"case_id": r["case_id"], "axis": r["axis"],
               "defect_class": r["defect_class"],
               "ground_truth": r["ground_truth"], "verdict": r["verdict_B"]}
              for r in rows]
    adjudicator_a = _score_adjudicator(a_rows)
    adjudicator_b = _score_adjudicator(b_rows)
    pairs = len(rows)
    agreed = sum(1 for r in rows if r["A_vs_B"] == "AGREE")

    per_axis: Dict[str, Any] = {}
    for axis in AXES:
        ax_rows = [r for r in rows if r["axis"] == axis]
        if not ax_rows:
            continue
        ax_agree = sum(1 for r in ax_rows if r["A_vs_B"] == "AGREE")
        ax_fp = sum(1 for r in ax_rows if r["A_vs_gt"] == "FALSE_POSITIVE")
        ax_fp += sum(1 for r in ax_rows if r["B_vs_gt"] == "FALSE_POSITIVE")
        ax_fn = sum(1 for r in ax_rows if r["A_vs_gt"] == "FALSE_NEGATIVE")
        ax_fn += sum(1 for r in ax_rows if r["B_vs_gt"] == "FALSE_NEGATIVE")
        per_axis[axis] = {
            "scored_pairs": len(ax_rows),
            "inter_adjudicator_agreed": ax_agree,
            "inter_adjudicator_disagreed": len(ax_rows) - ax_agree,
            "false_positives_A_or_B": ax_fp,
            "false_negatives_A_or_B": ax_fn,
            "unstable": (len(ax_rows) - ax_agree) > 0 or (ax_fp + ax_fn) > 0,
        }

    defect_classes: Dict[str, Any] = {}
    for case in cases:
        if case["defect_class"] == "CLEAN_CONTROL":
            continue
        cls = case["defect_class"]
        ax = next(iter(case["expected"]))
        row = next(r for r in rows if r["case_id"] == case["case_id"]
                   and r["axis"] == ax)
        defect_classes.setdefault(cls, []).append({
            "case_id": case["case_id"],
            "axis": ax,
            "A": {"verdict": row["verdict_A"],
                  "outcome": row["A_vs_gt"]},
            "B": {"verdict": row["verdict_B"],
                  "outcome": row["B_vs_gt"]},
        })

    unstable = [axis for axis, s in per_axis.items() if s["unstable"]]
    report: Dict[str, Any] = {
        "artifact": "ADJUDICATOR_CALIBRATION",
        "owner": "CODER2",
        "ceo_directive": "Phase 4 B14 — calibrate the semantic "
                         "adjudicators; do not force consensus",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": {
            "calibration_set": "12 independently authored known engineering "
                               "cases; ground truth fixed by the stated "
                               "engineering principle per case (Art. VIII "
                               "— not derived from adjudicator behavior)",
            "instruments": "the UNMODIFIED B9 adjudicators "
                           "adjudicate_a / adjudicate_b",
            "verdict_semantics": {
                "CORRECT": "instrument would not block",
                "INCORRECT": "instrument would block",
                "QUESTIONABLE": "honest uncertainty; flags, does not block",
            },
            "false_positive": "ground truth INCORRECT, verdict CORRECT — a "
                              "real defect waved through",
            "false_negative": "ground truth CORRECT, verdict INCORRECT — "
                              "good engineering blocked (Art. V risk)",
            "questionable_handling": "counted as uncertain_defect / "
                                     "uncertain_clean, NEVER folded into "
                                     "false_positive / false_negative",
            "unstable_class_rule": "an axis is UNSTABLE if any inter-"
                                   "adjudicator disagreement OR any false "
                                   "positive/negative occurs on it "
                                   "(deterministic rule; no invented "
                                   "threshold, Art. XXVII)",
            "consensus_policy": "NO consensus is forced; no adjudicator "
                                "code was modified by this calibration "
                                "(CEO B14; Art. VII/XXX)",
        },
        "adjudicator_A": adjudicator_a,
        "adjudicator_B": adjudicator_b,
        "agreement": {"pairs": pairs, "agreed": agreed,
                      "rate": round(agreed / pairs, 3) if pairs else None},
        "disagreement": {"pairs": pairs, "disagreed": pairs - agreed,
                         "rate": round((pairs - agreed) / pairs, 3)
                         if pairs else None},
        "false_positive": (adjudicator_a["false_positive"] +
                           adjudicator_b["false_positive"]),
        "false_negative": (adjudicator_a["false_negative"] +
                           adjudicator_b["false_negative"]),
        "per_axis": per_axis,
        "unstable_classes": unstable,
        "defect_class_catch_table": defect_classes,
        "instrument_observations": [
            {
                "observation_id": "OBS-A1-NEGATION_BLINDNESS",
                "adjudicator": ADJUDICATOR_A,
                "root_cause": "token-level active-word matching without "
                              "negation handling: 'no sensors and no "
                              "actuators' reads as the active-control term "
                              "'actuator'",
                "evidence": ["CAL07_CLEAN_PASSIVE_ANCHOR: A verdict "
                             "INCORRECT on ground truth CORRECT "
                             "(FALSE_NEGATIVE) via "
                             "CONTROL_ARCHITECTURE_CONTRADICTION"],
                "implication": "A can manufacture control-architecture "
                               "contradictions on honest passive designs; "
                               "B9 'INCORRECT' verdicts of this class are "
                               "weak evidence unless the mechanism text "
                               "carries no negated active words",
            },
            {
                "observation_id": "OBS-A2-FAMILY_VOCABULARY_MISMATCH",
                "adjudicator": ADJUDICATOR_A,
                "root_cause": "the family classifier emits family names "
                              "('fluidics') while the quantity classifier "
                              "emits quantity-family names ('hydraulic'); "
                              "the outside-family comparison can never "
                              "match, so ANY failure row spanning >= 2 "
                              "quantity families is flagged",
                "evidence": ["CAL02_CLEAN_LAMINAR_DRAINAGE: A verdict "
                             "INCORRECT on ground truth CORRECT "
                             "(FALSE_NEGATIVE) via "
                             "FAILURE_MODE_PHYSICS_OUTSIDE_FAMILY on a "
                             "legitimate hydraulic+biological occlusion "
                             "row"],
                "implication": "A's outside-family finding class is "
                               "unreliable for multi-physics failure rows "
                               "(occlusion + biofilm is normal for CSF "
                               "drainage)",
            },
            {
                "observation_id": "OBS-B1-NO_CONTROL_ARCHITECTURE_CHECK",
                "adjudicator": ADJUDICATOR_B,
                "root_cause": "adjudicator B is traceability-first and "
                              "carries no control-architecture check at "
                              "all",
                "evidence": ["CAL01_ACTIVE_PASSIVE_CONTRADICTION: B "
                             "verdict CORRECT on ground truth INCORRECT "
                             "(FALSE_POSITIVE) with zero findings — the "
                             "canonical CEO-named defect passes B "
                             "untouched"],
                "implication": "the canonical active/passive contradiction "
                               "is caught ONLY by A; B9's two-adjudicator "
                               "design is load-bearing on this axis",
            },
            {
                "observation_id": "OBS-AB1-CAUSAL_DIRECTION_UNVALIDATED",
                "adjudicator": "BOTH",
                "root_cause": "neither instrument validates the DIRECTION "
                              "of a causal claim; presence of causal "
                              "connectors is checked, physical polarity is "
                              "not",
                "evidence": ["CAL08_CAUSAL_DIRECTION_REVERSED: BOTH "
                             "adjudicators verdict CORRECT on ground truth "
                             "INCORRECT (FALSE_POSITIVE each) with zero "
                             "findings — a mechanism that decreases the "
                              "outlet pressure drop is passed as an "
                              "anti-overdrainage device"],
                "implication": "causal-direction semantics is beyond both "
                               "instruments; any B9 CORRECT verdict is "
                               "weak evidence for physical polarity — "
                               "this is a primary target for the B15 "
                               "human gold labels",
            },
        ],
        "calibration_rows": rows,
        "residual_self_reference_disclosure": (
            "Both adjudicators AND this calibration set are authored by "
            "Coder 2 (same residual self-reference as B9). The cases' "
            "ground truth is justified by stated engineering principles, "
            "not by adjudicator behavior, but an author-independent "
            "calibration point requires the B15 human gold labels."),
        "use": "calibration evidence for how much weight the B9 "
               "adjudication verdicts can carry; audit-layer credibility "
               "input, NOT an engine score",
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return report


def _classify_vs_gt(gt: Optional[str], v: Optional[str]) -> str:
    if v is None or gt is None:
        return "UNAVAILABLE"
    if v == gt:
        return "AGREE_GT"
    if gt == "INCORRECT" and v == "CORRECT":
        return "FALSE_POSITIVE"
    if gt == "CORRECT" and v == "INCORRECT":
        return "FALSE_NEGATIVE"
    if v == "QUESTIONABLE":
        return "UNCERTAIN_" + ("DEFECT" if gt == "INCORRECT" else "CLEAN")
    return "OTHER"


def main() -> None:
    report = run_calibration()
    print(json.dumps({k: report[k] for k in
                      ("adjudicator_A", "adjudicator_B", "agreement",
                       "disagreement", "false_positive", "false_negative",
                       "unstable_classes")}, indent=1))


if __name__ == "__main__":
    main()

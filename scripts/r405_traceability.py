#!/usr/bin/env python3
"""R405 — engine-side ENGINEERING_TRACEABILITY records: link the three
critical DI->DO->V chains per lead package using R394-identifier binding
(shared canonical identifiers present in both artifacts' recorded text) —
NEVER semantic association (Art. II / r394 binding rules).

The BUYER-side traceability files are frozen (owner release-chain, Art.
XXXIX); these engine-side records are the canonical links the next buyer
release will carry. Chains the evidence does not support stay UNKNOWN
(verbatim from the buyer-side truth model: EXPLICIT 0 / PARTIAL 0 /
UNKNOWN 9-11 per package) — this round links exactly three per package and
says so.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LP4 = REPO / "LEAD_PORTFOLIO_4"


def write(pkg, hid, tech, chains, summary_note):
    rec = {
        "artifact_type": "ENGINEERING_TRACEABILITY",
        "company_designation": pkg,
        "historical_package_id": hid,
        "technology_name": tech,
        "constitutional_basis": "R394 identifier-binding rules (IDENTIFIER "
                                "or exact PHRASE >= 12 chars shared between "
                                "artifacts; NEVER semantic association); "
                                "Art. II; the external audit's finding that "
                                "the buyer-side truth model records "
                                "EXPLICIT 0 / PARTIAL 0 / UNKNOWN 9-11 "
                                "chains per package",
        "binding_rules_verbatim": {
            "IDENTIFIER": "shared canonical engineering identifier "
                          "(underscore symbol or standard number) present "
                          "in both artifacts' recorded text",
            "PHRASE": "exact normalized phrase (>= 12 chars) shared",
            "NEVER": "semantic association, fuzzy match, or invented "
                     "binding (Art. II)",
        },
        "purpose": "the audit's $0 item 'Link 3 critical DI chains': link "
                   "the clinical-need -> primary-function -> primary-"
                   "verification chain per package ENGINE-SIDE so the next "
                   "buyer release carries an honest partial graph instead "
                   "of an all-UNKNOWN one",
        "chains": chains,
        "package_state_after_r405": {
            "chains_linked_this_round": 3,
            "chains_remaining_unknown": summary_note,
            "state": "TRACEABILITY_PARTIAL (engine-side canonical; the "
                     "buyer-side frozen files remain all-UNKNOWN until "
                     "the owner release-chain operation)",
        },
        "honest_limits": [
            "the V items are NOT_TESTED — linking a chain documents the "
            "graph, it does not execute the verification (Art. XXVIII: "
            "no promotion without new evidence)",
            "these are ENGINE-side records; the buyer surface is frozen "
            "(Art. XXXIX) and changes only through the release chain",
            "chains not listed here remain TRACEABILITY_UNKNOWN in the "
            "buyer-side truth model — they are not silently linked by "
            "this record",
        ],
    }
    (LP4 / pkg / "ENGINEERING_TRACEABILITY.json").write_text(
        json.dumps(rec, sort_keys=True, ensure_ascii=False, indent=1)
        + "\n")


def chain(di, param, feature, geometry, do, do_param, v, v_param,
          experiment, expected, decision, evidence_classes):
    return {
        "design_input_id": di,
        "design_input_parameter": param,
        "mechanism_feature": {
            "state": "EXPLICIT",
            "binding": "IDENTIFIER",
            "evidence": f"shared identifier {do} + exact phrase "
                        f"'{feature}' in the frozen corpus "
                        "MATURITY_BASIS design_output_evidence_ids and the "
                        "R403 canonical records",
        },
        "geometry_parameter": geometry,
        "design_output_id": do,
        "design_output_parameter": do_param,
        "verification_id": v,
        "verification_parameter": v_param,
        "experiment": {
            "state": "EXPLICIT",
            "binding": "IDENTIFIER",
            "linked_id": experiment,
            "evidence": "the R403 DECISIVE_EXPERIMENT contract carries the "
                        "same primary endpoint identifiers and the same "
                        "parameter names",
        },
        "expected_observation": expected,
        "decision": decision,
        "evidence_classes": evidence_classes,
    }


# --- P04 -----------------------------------------------------------------
write(
    "P04", "P-07", "Passive Drainage Priority Safety Floor",
    [
        chain("DI-001", "Clinical need", "dual-lumen drainage",
              "floor_lumen_diameter_mm (canonical 0.6 / NIST 0.5471)",
              "DO-001", "Dual-lumen catheter geometry", "V-001",
              "Bench obstruction challenge vs single-lumen control",
              "LEAD_PORTFOLIO_4/P04/DECISIVE_EXPERIMENT.json",
              "residual floor flow >= Q_min (0.2-0.4 mL/min declared "
              "range) under full primary obstruction at >= 2 of the "
              "physiological pressure heads",
              "ACCEPT -> sponsored bench validation; common-cause "
              "occlusion >= 90% of cases -> KILL (r405 quantified arm)",
              {"di": "SOURCE_FACT (frozen corpus dossier)",
               "do": "COMPUTATIONAL_RESULT (validated CAD)",
               "v": "NOT_TESTED (bench experiment unexecuted)",
               "q_min": "EXTERNAL_PRECEDENT (web-verified citations)"}),
        chain("DI-005", "Q_min target (minimum drainage)", "floor lumen "
              "conductance", "floor_lumen_diameter_mm x length_mm = 100",
              "DO-001", "Dual-lumen catheter geometry", "V-001",
              "Bench flow measurement",
              "LEAD_PORTFOLIO_4/P04/QMIN_FLOOR_FLOW_CALCULATION.json",
              "corrected Poiseuille floor conductance 0.254 mL/(min*mmHg) "
              "-> 152.7 mL/hr at 10 mmHg (NIST-corrected geometry) vs Q_min "
              "12-24 mL/hr: conductance margin 6-12x; the discriminating "
              "boundary is ~47% effective-diameter reduction (common-cause "
              "tolerance)",
              "the Q_min pass rule is quantified and testable; "
              "below-Q_min residual flow at all heads -> KILL",
              {"di": "RECORDED (dossier design input)",
               "calculation": "COMPUTATIONAL_RESULT (R405 script log)",
               "v": "NOT_TESTED"}),
        chain("DI-003", "Flow regime", "Poiseuille laminar network model",
              "primary_lumen_diameter_mm 1.1 / floor 0.5471",
              "DO-001", "Dual-lumen catheter geometry", "V-002",
              "Flow/pressure measurement across the postural matrix",
              "LEAD_PORTFOLIO_4/P04/DECISIVE_EXPERIMENT.json",
              "laminar regime holds across 10-40 mmHg (Reynolds far below "
              "the laminar limit at corrected magnitudes — R405 unit "
              "correction)",
              "regime violation -> model invalidity declared, experiment "
              "re-specified (honest failure, not a silent retry)",
              {"di": "RECORDED (dossier design input)",
               "model": "MODELLED (Poiseuille, deterministic)",
               "v": "NOT_TESTED"}),
    ],
    "7 of 10 (frozen-corpus chain count) — including DI-007 "
    "biocompatibility, DI-008 sterilization, DI-010 material, which are "
    "ISO/standard-verifiable but carry no experiment binding in the "
    "current records")

# --- P08 -----------------------------------------------------------------
write(
    "P08", "P-16", "NIR Photovoltaic Power Delivery for Implantable "
                   "Devices",
    [
        chain("DI-001", "Clinical need", "battery-elimination for shunt "
              "electronics", "PV receiver area 0.3848 cm2 (38.4845 mm2)",
              "DO-001", "940 nm PV receiver", "V-001",
              "Phantom optical bench test (three-instrument triangle)",
              "LEAD_PORTFOLIO_4/P08/DECISIVE_EXPERIMENT.json",
              "measured electrical power inside the pre-registered band; "
              "phantom fluence consistent with the asserted range "
              "(RECOVERED_EXECUTION_ARTIFACT chain: R310/R311/R312 "
              "restored with custody)",
              "inside band -> chain confirmed + D2 relocation decision; "
              "fluence materially below range at permissible power -> "
              "KILL (physics)",
              {"di": "SOURCE_FACT (dossier)",
               "do": "COMPUTATIONAL_RESULT (validated CAD)",
               "fluence": "RECOVERED_EXECUTION_ARTIFACT (restored "
                          "simulations, hash-pinned)",
               "v": "NOT_TESTED"}),
        chain("DI-004", "Wavelength", "940 nm tissue window",
              "receiver + source spectral class",
              "DO-001", "940 nm PV receiver", "V-002",
              "Fluence measurement at the receiver plane",
              "LEAD_PORTFOLIO_4/P08/VERIFICATION_EVIDENCE/ (R310/R311/"
              "R312 restored artifacts)",
              "fluence 1.049-1.416 mW/cm2 at the receiver (restored "
              "simulation chain, converged, CI-overlap verdict)",
              "chain-confirmation vs kill is decided by the phantom "
              "experiment, not by the restored chain alone (Art. XXVIII)",
              {"di": "RECORDED (dossier design input)",
               "simulation": "COMPUTATIONAL_RESULT (recovered artifacts)",
               "v": "NOT_TESTED"}),
        chain("DI-008", "Thermal safety", "skin/thermal exposure boundary",
              "source power class (owner action: real source spec)",
              "DO-003", "Thermal envelope / source operating point",
              "V-001", "Phantom optical bench test (thermal probes)",
              "LEAD_PORTFOLIO_4/P08/DECISIVE_EXPERIMENT.json + ENERGY_"
              "BUDGET.r405_extensions.thermal_kill_boundary",
              "surface irradiance within the pre-registered ANSI/"
              "IEC-class skin limit for the declared exposure duration",
              "exceeds the pre-registered limit at useful power -> KILL "
              "(thermally infeasible)",
              {"di": "RECORDED (dossier design input)",
               "threshold": "OWNER-GATED (paywalled standards; numbers "
                            "reported-not-verified by the audit)",
               "v": "NOT_TESTED"}),
    ],
    "6 of 9 — the biocompatibility/sterilization/interface chains carry "
    "no experiment binding in the current records")

# --- P11 -----------------------------------------------------------------
write(
    "P11", "P-24", "Gravity Compensation Hydraulic Damper for Postural "
                   "Transients",
    [
        chain("DI-001", "Clinical need", "postural over-drainage "
              "attenuation", "annular gap 0.18 mm x 5.0 mm OD element",
              "DO-001", "Annular damping element", "V-001",
              "Bench flow response test (mock CSF loop, blinded)",
              "LEAD_PORTFOLIO_4/P11/DECISIVE_EXPERIMENT.json",
              "settling-time and target-flow-accuracy endpoints vs the "
              "REAL ASD arm across 10/20/30/40 mmHg; MDD 0.0253 s vs the "
              "claimed 0.1 s difference (INSTRUMENT_MDD_CALCULATION.json)",
              "the r405 quantified conditions A/B decide KILL vs "
              "proceeding; both differentiators UNESTABLISHED until then",
              {"di": "SOURCE_FACT (dossier)",
               "do": "COMPUTATIONAL_RESULT (validated CAD, KEEP child)",
               "c_h": "MODELLED (back-calculated, unvalidated)",
               "v": "NOT_TESTED"}),
        chain("DI-003", "Postural head range", "10-40 mmHg pressure "
              "matrix", "postural-step actuator class",
              "DO-001", "Annular damping element", "V-001",
              "Bench flow response test (4 pressures x 10 runs)",
              "LEAD_PORTFOLIO_4/P11/DECISIVE_EXPERIMENT.json (R339 "
              "protocol lift)",
              "flow transient attenuation across the postural matrix at "
              "physiological 1-3 s transition rates",
              "no material advantage at any pressure -> KILL path per the "
              "recorded falsifier",
              {"di": "RECORDED (dossier design input)",
               "protocol": "RECORDED (R339)",
               "v": "NOT_TESTED"}),
        chain("DI-009", "Comparative clinical endpoint vs ASD",
              "proportional vs binary control",
              "damper element vs ASD membrane architecture",
              "DO-004", "Comparative performance specification", "V-001",
              "ASD comparison arm (real Codman-class ASD, identical "
              "instrument)",
              "LEAD_PORTFOLIO_4/P11/DIFFERENTIATION_AND_CAUSAL_CHAIN.json",
              "the honest finding is recorded: ASD beats P-24 at "
              "target-flow matching in 3/4 postures (MODELLED); the "
              "experiment tests whether either differentiator is real",
              "ASD superiority confirmed at the bench -> the package has "
              "no case (KILL path); differentiator decisively positive -> "
              "proceed",
              {"di": "RECORDED (dossier design input)",
               "comparison": "MODELLED (0 of 2 differentiators "
                             "established)",
               "v": "NOT_TESTED"}),
    ],
    "6 of 9 — biocompatibility/sterilization chains carry no experiment "
    "binding in the current records")

# --- P13 -----------------------------------------------------------------
write(
    "P13", "P-27-R1", "Self-Referencing Piezoresistive Pressure Sensor",
    [
        chain("DI-001", "Clinical need", "ICP drift reduction",
              "diaphragm 0.07 mm (improvement-loop KEEP child)",
              "DO-001", "Self-referencing bridge geometry", "V-001",
              "Bench drift measurement (paired-die, blinded)",
              "LEAD_PORTFOLIO_4/P13/DECISIVE_EXPERIMENT.json",
              "drift improvement ratio over the single-ended baseline "
              "exceeds the pre-registered material margin; target class "
              "< 0.5 mmHg/month (MODEL_DERIVED)",
              "immaterial improvement -> KILL (the bridge buys nothing)",
              {"di": "SOURCE_FACT (dossier)",
               "do": "COMPUTATIONAL_RESULT (validated CAD)",
               "drift_target": "MODEL_DERIVED (no hardware basis — "
                               "sourcing is an open owner action)",
               "v": "NOT_TESTED"}),
        chain("DI-005", "Drift target", "common-mode cancellation model",
              "active + dummy bridge elements",
              "DO-001", "Self-referencing bridge geometry", "V-003",
              "Thermal sweep test (baseline vs self-referencing)",
              "LEAD_PORTFOLIO_4/P13/BENCHMARK_SPECIFICATION.json",
              "thermal drift cancellation ratio consistent with the "
              "modelled bridge estimate",
              "cancellation fails to reach the registered margin -> the "
              "central proposition dies",
              {"di": "RECORDED (dossier design input)",
               "model": "MODELLED (bridge cancellation estimate)",
               "v": "NOT_TESTED"}),
        chain("DI-004", "Piezoresistive coefficient", "sensing element "
              "physics", "diaphragm geometry + piezoresistive elements",
              "DO-001", "Self-referencing bridge geometry", "V-005",
              "Accelerated fouling arm (BSA protocol, r405)",
              "LEAD_PORTFOLIO_4/P13/DECISIVE_EXPERIMENT.json + "
              "LINEAGE_AUDIT.json",
              "KA-014 channel: differential bridge drift after 4-week "
              "fouling exposure stays inside the pre-registered band — "
              "this is the exact test the predecessor P-25 failed "
              "(3.45 mmHg > 2.0 threshold)",
              "differential drift > 1 mmHg after fouling -> KA-014 "
              "recurs -> repair with a non-common-mode mechanism or "
              "cemetery",
              {"di": "RECORDED (dossier design input)",
               "predecessor": "RECORDED PRECEDENT (P-25 failure, R337/"
                              "R347)",
               "v": "NOT_TESTED"}),
    ],
    "8 of 11 — the EMC/hermeticity/battery chains carry no experiment "
    "binding in the current records")

print("engine-side ENGINEERING_TRACEABILITY records written: "
      "P04, P08, P11, P13 (3 chains each, R394 identifier bindings)")

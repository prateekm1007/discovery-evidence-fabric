#!/usr/bin/env python3
"""Author eval/problems.json (one-time, already committed output).

Composes the 18-problem eval set:
  - the 12 WC2 bench problems, byte-equivalent on the shared fields
    (problem_id/device/failure/failure_mode/constraint/domain) to
    R401-WC2/BENCHMARK/FROZEN_BENCHMARK.json (the frozen file stays the
    source of truth; the 12 are copied verbatim at authoring time);
  - the SOFC case (from the R412 lane-pool SOFC redox literature);
  - 5 new problems authored 2026-11-09, disjoint from the frozen set
    and from any engine test fixture.

Every problem carries two EVAL fields the engine does not read yet:
  question_type: what the user is actually asking
                 (intervention-proposal | predictor-design)
  user_variables: the user-stated specifics a good answer must use
(a later round propagates these into the engine; today they define what
"uses user-stated variables" means for the judge).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FROZEN = REPO / "R401-WC2" / "BENCHMARK" / "FROZEN_BENCHMARK.json"
OUT = Path(__file__).resolve().parent / "problems.json"

WC2_QUESTION = ("What engineering change, intervention, or design would "
                "prevent or mitigate the stated failure under the stated "
                "constraint, and what concrete test would falsify the "
                "proposed approach?")
PREDICTOR_QUESTION = ("Propose the most cost-effective measurable leading "
                      "indicator (predictor) for the stated failure, its "
                      "operating threshold, and the concrete test that "
                      "would validate or kill the predictor.")


def wc2_source(p):
    return {
        "problem_id": p["problem_id"],
        "device": p["device"],
        "failure": p["failure"],
        "failure_mode": p["failure_mode"],
        "constraint": p["constraint"],
        "domain": p["domain"],
        "source": "wc2_frozen",
        "contamination_tag": "DEV_CONTAMINATED",
        "question_type": "intervention-proposal",
        "question": WC2_QUESTION,
        "user_variables": [
            p["constraint"],
            f"device of record: {p['device']}",
            f"failure to address: {p['failure_mode']}",
        ],
        "clarification_answer": None,
    }


SOFC = {
    "problem_id": "eval-sofc-redox",
    "device": "planar solid oxide fuel cell single cell with "
              "nickel-yttria-stabilized-zirconia anode support",
    "failure": "Redox cycling of the Ni-YSZ anode during start/stop events "
               "causes irreversible anode volume change: re-oxidation "
               "expands the nickel phase, rearranges the anode "
               "microstructure (nickel agglomeration and coarsening), and "
               "builds tensile stress at the anode-electrolyte interface "
               "until the cell cracks or the electrode delaminates, so the "
               "stack loses sealing integrity and power density after "
               "repeated starts.",
    "failure_mode": "redox-degradation",
    "constraint": "tolerate 200 start-stop cycles over a 5-year service "
                  "life at 750 C operating temperature while holding power "
                  "density above 0.35 W/cm2 at 0.7 V, without exceeding "
                  "the existing 2 mm cell package thickness",
    "domain": "energy-conversion",
    "source": "sofc_case",
    "question_type": "intervention-proposal",
    "question": WC2_QUESTION,
    "user_variables": [
        "operating temperature 750 C",
        "200 start-stop cycles over 5 years",
        "power density above 0.35 W/cm2 at 0.7 V",
        "cell package thickness must not exceed 2 mm",
    ],
}

NEW = [
    {
        "problem_id": "eval-new01-supercap-dryout",
        "device": "electric double-layer supercapacitor module in an "
                  "automotive under-hood 12 V stop-start system",
        "failure": "Electrolyte dry-out: sustained operation at high "
                   "temperature drives solvent evaporation and seal "
                   "permeation, collapsing the effective ion transport so "
                   "equivalent series resistance climbs until the module "
                   "can no longer source the cold-crank assist pulse.",
        "failure_mode": "electrolyte-dryout",
        "constraint": "keep capacitance loss below 10 percent over a 10-year "
                      "life at up to 2.7 V rated cell voltage and 65 C "
                      "maximum ambient, without adding more than 1 mm of "
                      "module height",
        "domain": "energy-storage",
        "source": "new_r1",
        "question_type": "intervention-proposal",
        "question": WC2_QUESTION,
        "user_variables": [
            "10-year life target",
            "2.7 V rated cell voltage",
            "65 C maximum ambient",
            "capacitance loss below 10 percent",
            "no more than 1 mm added module height",
        ],
    },
    {
        "problem_id": "eval-new02-slipring-predictor",
        "device": "slip-ring brush assembly of a 1.5 MW generator "
                  "excitation system running at 1800 rpm",
        "failure": "Brush and slip-ring contact wear progresses to "
                   "arcing and intermittent open-circuit excitation "
                   "transients weeks before the classical media "
                   "(vibration, temperature) alarms rise, so operators "
                   "learn of the failure from the excitation fault "
                   "itself rather than from a leading indicator.",
        "failure_mode": "contact-wear",
        "constraint": "the predictor must rely only on data already "
                      "collected by the plant historian at a 1-minute "
                      "sampling interval, must fire at least 2 weeks "
                      "before a forced outage would otherwise occur, and "
                      "must not raise more than 1 false alarm per year per "
                      "machine",
        "domain": "electrical-machine",
        "source": "new_r1",
        "question_type": "predictor-design",
        "question": PREDICTOR_QUESTION,
        "user_variables": [
            "historian data at 1-minute sampling interval only",
            "at least 2 weeks warning before forced outage",
            "no more than 1 false alarm per year per machine",
            "1800 rpm operating speed",
        ],
    },
    {
        "problem_id": "eval-new03-insulin-pump-occlusion",
        "device": "subcutaneous insulin pump infusion set with a 90 cm "
                  "catheter worn by ambulatory type-1 diabetes patients",
        "failure": "Catheter kinking, fibrin deposition, and air emboli "
                   "produce upstream pressure events that the pump's "
                   "occlusion detector reads late or never (slow leaks "
                   "and partial occlusions stay under the fixed pressure "
                   "threshold), so missed insulin delivery raises patient "
                   "glucose for hours before the fault is detected.",
        "failure_mode": "late-occlusion-detection",
        "constraint": "raise no more than 1 nuisance occlusion alarm per "
                      "14 days of wear, detect a complete occlusion within "
                      "15 minutes, and detect partial occlusions "
                      "(delivery deficit above 20 percent) within 2 hours, "
                      "without changing the wearable form factor",
        "domain": "biomedical-delivery",
        "source": "new_r1",
        "question_type": "intervention-proposal",
        "question": WC2_QUESTION,
        "user_variables": [
            "detection of complete occlusion within 15 minutes",
            "partial occlusion (delivery deficit above 20 percent) within 2 hours",
            "no more than 1 nuisance alarm per 14 days of wear",
            "no change to the wearable form factor",
        ],
    },
    {
        "problem_id": "eval-new04-chiller-fouling-predictor",
        "device": "water-cooled centrifugal chiller condenser tube bank in a "
                  "district cooling plant using an open cooling tower loop",
        "failure": "Condenser tube fouling accumulates silently: the "
                   "fouling layer raises condenser approach temperature "
                   "and pressure schedules, but operators clean on a fixed "
                   "monthly cadence rather than on measured need, so tubes "
                   "spend part of the month fouled early in the season and "
                   "the cleaning cadence wastes labor later.",
        "failure_mode": "condenser-fouling",
        "constraint": "the predictor must use only BMS points already "
                      "logged (chilled water supply/return temperature, "
                      "condenser water supply/return temperature, "
                      "compressor power, pump speed, outdoor wet-bulb), "
                      "must resolve fouling state changes within 3 days at "
                      "full load, and must produce a cleaning trigger that "
                      "reduces total compressor energy by at least 3 "
                      "percent versus the fixed monthly cadence",
        "domain": "thermal-fluid-process",
        "source": "new_r1",
        "question_type": "predictor-design",
        "question": PREDICTOR_QUESTION,
        "user_variables": [
            "BMS points already logged (listed in constraint)",
            "fouling state resolved within 3 days at full load",
            "at least 3 percent compressor energy reduction vs the fixed monthly cadence",
        ],
    },
    {
        "problem_id": "eval-new05-liion-balance-drift",
        "device": "13-cell series NMC-811 lithium-ion battery module for a "
                  "3 kWh stationary-storage cabinet",
        "failure": "Series string imbalance drift: cell-to-cell capacity "
                   "and self-discharge spread grows with cycling and "
                   "temperature gradient across the module, so the "
                   "balancer cannot keep spread under the trip threshold; "
                   "the BMS derates or shuts the module off early although "
                   "the pack's aggregate energy is still serviceable.",
        "failure_mode": "series-imbalance",
        "constraint": "hold maximum cell-to-cell voltage spread below 35 mV "
                      "at rest across a 10-year calendar life in a module "
                      "that sees a 15 C top-to-bottom thermal gradient, "
                      "without increasing the module footprint, and using "
                      "only the existing 1 A balancing current",
        "domain": "energy-storage",
        "source": "new_r1",
        "question_type": "intervention-proposal",
        "question": WC2_QUESTION,
        "user_variables": [
            "maximum cell-to-cell voltage spread below 35 mV at rest",
            "10-year calendar life",
            "15 C top-to-bottom thermal gradient",
            "only the existing 1 A balancing current",
            "no increase in module footprint",
        ],
    },
]


SOFC_THERMAL = {
    "problem_id": "eval-sofc-thermal-cycling",
    "device": "anode-supported solid oxide fuel cell stack with a "
              "yttria-stabilized zirconia electrolyte and a lanthanum "
              "strontium manganite cathode",
    "failure": "Thermal cycling between 25 C and 800 C during start/stop "
               "drives differential expansion between the electrolyte, the "
               "anode, and the glass-ceramic seal; repeated cycles open "
               "microcracks in the seal and at the cathode-electrolyte "
               "interface, raising gas crossover and ohmic loss until the "
               "stack fails to reach operating voltage.",
    "failure_mode": "thermal-cycling-fatigue",
    "constraint": "survive 500 thermal cycles from 25 C to 800 C at 5 C/min "
                  "heating rate while holding open-circuit voltage above "
                  "1.0 V and keeping seal leakage below 1 percent of fuel "
                  "flow, without increasing stack mass above 2 percent",
    "domain": "energy-conversion",
    "source": "sofc_case_r548",
    "contamination_tag": None,
    "question_type": "intervention-proposal",
    "question": WC2_QUESTION,
    "user_variables": [
        "500 thermal cycles from 25 C to 800 C",
        "5 C/min heating rate",
        "open-circuit voltage above 1.0 V",
        "seal leakage below 1 percent of fuel flow",
        "stack mass increase below 2 percent",
    ],
    "clarification_answer": {
        "intergranular glass phase fraction": 0.15,
        "note": "user stated the seal's intergranular glass phase fraction "
                "is 0.15 (mass fraction) for this stack design",
    },
}

PREDICTOR_EXTRA = [
    {
        "problem_id": "eval-new06-bearing-vibration-predictor",
        "device": "rolling-element bearing in a 350 kW industrial fan drive",
        "failure": "Inner-race spalling progresses for weeks before the "
                   "vibration alarm trips; by then the bearing is past "
                   "repair and the fan is forced offline.",
        "failure_mode": "incipient-spalling",
        "constraint": "predictor must use only the existing 1 kHz vibration "
                      "sensor and 1 Hz SCADA logging, fire at least 14 days "
                      "before forced replacement, and produce no more than "
                      "2 false alarms per year",
        "domain": "rotating-machinery",
        "source": "new_r1",
        "contamination_tag": None,
        "question_type": "predictor-design",
        "question": PREDICTOR_QUESTION,
        "user_variables": ["1 kHz vibration sensor only", "1 Hz SCADA logging",
                           "at least 14 days warning", "no more than 2 false "
                           "alarms per year"],
        "clarification_answer": None,
    },
    {
        "problem_id": "eval-new07-transformer-dga-predictor",
        "device": "oil-filled power transformer (132/33 kV, 40 MVA)",
        "failure": "Dissolved-gas analysis is sampled quarterly, so an "
                   "incipient partial-discharge or thermal fault can grow "
                   "for months between samples and only be found at the "
                   "next outage window.",
        "failure_mode": "insulation-degradation",
        "constraint": "predictor must infer fault onset from the online "
                      "sensors already installed (top-oil temperature, load "
                      "current, ambient temperature, tank pressure) at "
                      "15-minute resolution, and must flag a developing "
                      "fault at least 30 days before the next scheduled "
                      "DGA sample",
        "domain": "electrical-power",
        "source": "new_r1",
        "contamination_tag": None,
        "question_type": "predictor-design",
        "question": PREDICTOR_QUESTION,
        "user_variables": ["online sensors: top-oil temp, load current, "
                           "ambient temp, tank pressure", "15-minute "
                           "resolution", "at least 30 days warning before "
                           "next DGA sample"],
        "clarification_answer": None,
    },
    {
        "problem_id": "eval-new08-pipeline-leak-predictor",
        "device": "buried carbon-steel water transmission pipeline (DN 600)",
        "failure": "Small leaks below the SCADA pressure-deviation threshold "
                   "continue for weeks, eroding the bedding and causing a "
                   "sudden large failure instead of a repairable one.",
        "failure_mode": "small-leak",
        "constraint": "predictor must use only the existing pressure and "
                      "flow transmitters at 5-minute intervals, detect a "
                      "leak of 0.5 percent of nominal flow within 48 hours, "
                      "and not raise more than 1 false alarm per month per "
                      "10 km of pipe",
        "domain": "water-infrastructure",
        "source": "new_r1",
        "contamination_tag": None,
        "question_type": "predictor-design",
        "question": PREDICTOR_QUESTION,
        "user_variables": ["existing pressure and flow transmitters", "5-minute "
                           "intervals", "detect 0.5 percent leak within 48 h",
                           "no more than 1 false alarm per month per 10 km"],
        "clarification_answer": None,
    },
    {
        "problem_id": "eval-new09-hvac-filter-predictor",
        "device": "commercial building air-handling unit with a MERV-13 "
                  "pleated filter bank",
        "failure": "Filter loading is estimated from a fixed 90-day "
                   "replacement schedule, so filters are either replaced "
                   "early (wasted cost) or run overloaded (fan energy and "
                   "indoor air quality suffer).",
        "failure_mode": "filter-loading",
        "constraint": "predictor must use only BMS points already logged "
                      "(supply/return fan power, pressure drop if available, "
                      "outdoor air flow, occupancy schedule), must resolve a "
                      "filter change-of-state within 1 week, and must cut "
                      "unnecessary replacements by at least 20 percent",
        "domain": "building-services",
        "source": "new_r1",
        "contamination_tag": None,
        "question_type": "predictor-design",
        "question": PREDICTOR_QUESTION,
        "user_variables": ["BMS points already logged", "1 week resolution",
                           "at least 20 percent reduction in unnecessary "
                           "replacements"],
        "clarification_answer": None,
    },
    {
        "problem_id": "eval-new10-solar-inverter-predictor",
        "device": "grid-tied string inverter in a 500 kWp commercial "
                  "photovoltaic array",
        "failure": "IGBT and capacitor degradation raises junction "
                   "temperature and ripple current, but the inverter "
                   "reports only an aggregate fault code after tripping, "
                   "so the failure is not predicted.",
        "failure_mode": "power-electronics-degradation",
        "constraint": "predictor must use only inverter telemetry already "
                      "exported (DC voltage/current, AC power, heatsink "
                      "temperature, fault log) at 5-minute resolution, must "
                      "flag a degrading inverter at least 2 weeks before "
                      "trip, and must not raise more than 1 false alarm per "
                      "quarter per inverter",
        "domain": "photovoltaic",
        "source": "new_r1",
        "contamination_tag": None,
        "question_type": "predictor-design",
        "question": PREDICTOR_QUESTION,
        "user_variables": ["inverter telemetry at 5-minute resolution",
                           "at least 2 weeks warning", "no more than 1 "
                           "false alarm per quarter per inverter"],
        "clarification_answer": None,
    },
    {
        "problem_id": "eval-new11-conveyor-belt-predictor",
        "device": "rubber conveyor belt in a mining overland conveyor",
        "failure": "Cover wear and carcass fatigue progress to a splice "
                   "failure or a longitudinal tear; inspection is visual "
                   "and periodic, so the failure is found by the belt "
                   "stopping, not by prediction.",
        "failure_mode": "belt-degradation",
        "constraint": "predictor must use only the existing belt-scale and "
                      "drive-motor current sensors at 1-minute resolution, "
                      "must flag a degrading belt at least 3 weeks before "
                      "failure, and must not raise more than 2 false alarms "
                      "per year",
        "domain": "bulk-materials",
        "source": "new_r1",
        "contamination_tag": None,
        "question_type": "predictor-design",
        "question": PREDICTOR_QUESTION,
        "user_variables": ["belt-scale and drive-motor current sensors",
                           "1-minute resolution", "at least 3 weeks warning",
                           "no more than 2 false alarms per year"],
        "clarification_answer": None,
    },
]


def main() -> None:
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    problems = ([wc2_source(p) for p in frozen["problems"]]
                + [SOFC, SOFC_THERMAL]
                + NEW
                + PREDICTOR_EXTRA)
    for pr in problems:
        pr.setdefault("clarification_answer", None)
        pr.setdefault("contamination_tag", pr.get("contamination_tag"))
    out = {
        "eval_version": "eval/1.1.0",
        "authored_at": "2026-11-10",
        "provenance": (
            "12 problems byte-equivalent to R401-WC2/BENCHMARK/"
            "FROZEN_BENCHMARK.json, tagged DEV_CONTAMINATED. SOFC case "
            "(eval-sofc-redox) + SOFC thermal-cycling case "
            "(eval-sofc-thermal-cycling, with clarification-answer field "
            "stating intergranular glass phase fraction) from the R412/R548 "
            "SOFC literature. 5 + 6 new problems authored 2026-11-10; "
            "question_type and user_variables are EVAL fields. "
            "clarification_answer carries the user-stated clarification."),
        "problems": problems,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {len(problems)} problems")
    from collections import Counter
    print("question_type:", Counter(p["question_type"] for p in problems))
    print("contamination:", Counter(p.get("contamination_tag") for p in problems))


if __name__ == "__main__":
    main()

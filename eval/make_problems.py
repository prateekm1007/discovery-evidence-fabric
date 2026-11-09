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
        "question_type": "intervention-proposal",
        "question": WC2_QUESTION,
        "user_variables": [
            p["constraint"],
            f"device of record: {p['device']}",
            f"failure to address: {p['failure_mode']}",
        ],
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


def main() -> None:
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    problems = [wc2_source(p) for p in frozen["problems"]] + [SOFC] + NEW
    out = {
        "eval_version": "eval/1.0.0",
        "authored_at": "2026-11-09",
        "provenance": (
            "12 problems byte-equivalent to R401-WC2/BENCHMARK/"
            "FROZEN_BENCHMARK.json (source of truth; the frozen file's "
            "freeze semantics carry over); the SOFC case follows the R412 "
            "lane-pool SOFC redox literature; 5 new problems authored "
            "2026-11-09, disjoint from the frozen set and from engine test "
            "fixtures. question_type and user_variables are EVAL fields "
            "the engine reads only when a later round adds the wiring."),
        "problems": problems,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {len(problems)} problems")
    for p in problems:
        print(" -", p["problem_id"], p["question_type"])


if __name__ == "__main__":
    main()

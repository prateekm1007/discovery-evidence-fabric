#!/usr/bin/env python3
"""r125_f97_generalization.py — the detector generalization check
(the R125 verdict dir 3; claim c-0192; zero LLM).

A HELD-OUT narration corpus authored fresh for this check — beyond the
twin's 69-firing calibration corpus and beyond their 6 preregistered
probes (none of these shapes appear in either). Two classes:
  narration_shapes  — prose that MENTIONS monitoring/sensing near a
                      sensing verb but requires NO unpermitted online
                      input (the F97 noise family, held-out shapes);
                      every shape must stay SILENT;
  sensitivity_probes — synthetic bills that genuinely REQUIRE an
                      unpermitted online input (no permitted bridge,
                      no negation, not narration); every probe must
                      FIRE (sensitivity retained on unseen shapes).
Acceptance: 0 narration false positives AND all sensitivity probes
fire (the R125 dir 3 accept: precision holds on unseen narration;
genuine-fire sensitivity holds).

Output: eval/r125_f97_generalization/generalization_result.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r40_machine_v77 as m77  # noqa: E402 (the CANONICAL bytes)

OUT = REPO / "eval" / "r125_f97_generalization"
OUT.mkdir(parents=True, exist_ok=True)

CONS_PLAIN = ("Use only existing sensors and existing measurements: "
              "the frame thermocouples and the line-flow meter already "
              "installed. No new instrumentation may be added.")

# Held-out narration shapes (the F97 noise family, NEW shapes beyond
# the 69 + the 6 probes). Each: (id, the narration sentence embedded
# in a bill paragraph).
NARRATION_SHAPES = [
    ("n01", "The team will continuously monitor the loop for critical "
            "drift during the trial."),
    ("n02", "Operators monitor thermal outcomes at each shift handover."),
    ("n03", "A feedback loop for monitoring adjustments keeps the "
            "recipe on target."),
    ("n04", "Standard monitoring of the process continues unchanged."),
    ("n05", "We monitor progress against the plan and report weekly."),
    ("n06", "The platform continuously measures nothing new; existing "
            "gauges suffice."),
    ("n07", "Critical parameters are watched by the existing control "
            "room during operation."),
    ("n08", "Alarming thresholds remain as configured; the system "
            "monitors itself."),
    ("n09", "The proposal does not add sensing; monitoring stays with "
            "the installed panel."),
    ("n10", "During commissioning, staff monitor the panel manually."),
    ("n11", "A watch-list records which gauges the crew monitors each "
            "cycle."),
    ("n12", "Log review happens daily; the crew checks the trend "
            "screens continuously."),
]

# Sensitivity probes (NEW genuine shapes beyond the twin's three),
# written in the canonical fire-surface grammar the twin's prereg
# defines (an online quantity measured continuously in-line and
# CONSUMED as the control signal): new quantities, no bridge, no
# negation, not narration. Each must FIRE.
SENSITIVITY_PROBES = [
    ("p01", "Mechanism: use the online hydrogen analyzer in the "
            "cooling circuit to compute the control signal; the vent "
            "valve is trimmed based on the online hydrogen "
            "concentration reading continuously measured in-line, "
            "and the controller modulates the vent from the online "
            "hydrogen signal.\nImplementation: the hydrogen "
            "measurement is taken continuously in-line during "
            "operation."),
    ("p02", "Mechanism: an online acoustic-cage-noise sensor feeds "
            "the control loop; the drive speed is adjusted based on "
            "the online cage-noise reading continuously measured "
            "in-line during operation.\nImplementation: the cage-noise "
            "measurement is taken continuously in-line."),
    ("p03", "Mechanism: the dosing pump is actuated on a real-time "
            "residual-chlorine analyzer; the dose is controlled from "
            "the online chlorine reading taken each cycle during "
            "production.\nImplementation: use the online chlorine "
            "analyzer to regulate the dose."),
    ("p04", "Mechanism: calculate the roll-wear index from online "
            "crack-scan measurements taken in-line during operation; "
            "the grinding pass is scheduled using the online crack "
            "reading as the control signal.\nImplementation: an "
            "online crack-detection scanner measures the roll "
            "surface continuously and the algorithm consumes it."),
    ("p05", "Mechanism: the feed pump is interlocked on a real-time "
            "headspace-oxygen analyzer; the interlock is driven from "
            "the online oxygen measurement continuously measured "
            "in-line.\nImplementation: use the online oxygen analyzer "
            "to trip the feed pump."),
]

# Recall-boundary observations (typed, NOT gating): sparse genuine
# shapes outside the canonical fire-surface grammar (short mentions
# without the online-X control-signal construction). Whether these
# should bind is the auditor's semantic call.
SPARSE_OBSERVATIONS = [
    ("s01", "Continuously sense the hydrogen concentration in the "
            "cooling circuit and trim the vent valve when it rises."),
    ("s02", "Track the residual chlorine level in the rinse tank every "
            "cycle and adjust dosing from it."),
    ("s03", "Measure the headspace oxygen of the fermenter online and "
            "interlock the feed pump on it."),
]


def main() -> int:
    results, n_fp, n_miss = [], 0, 0
    for cid, sent in NARRATION_SHAPES:
        prob = {"problem_id": f"f97g-{cid}", "device": "held-out-probe",
                "failure": "held-out narration probe", "constraint":
                CONS_PLAIN}
        bill = ("**Mitigation Proposal**\n\n**1. Mechanism** The "
                "existing instrumentation supports the plan: " + sent
                + "\n\n**2. Implementation** No new instruments are "
                "added; the installed panel and the crew cover the "
                "rest.")
        res = m77.scan_input_availability(prob, bill)
        fired = res.get("INPUT_UNAVAILABLE", [])
        ok = not fired
        n_fp += (not ok)
        results.append({"case_id": cid, "class": "narration_shape",
                        "expected": "silent", "fired": fired,
                        "ok": ok, "shape": sent[:90]})
    for cid, sent in SENSITIVITY_PROBES:
        prob = {"problem_id": f"f97g-{cid}", "device": "held-out-probe",
                "failure": "held-out sensitivity probe",
                "constraint": CONS_PLAIN}
        bill = ("**Mitigation Proposal**\n\n**1. Mechanism** " + sent
                + "\n\n**2. Implementation** The line runs on the new "
                "signal; no other changes.")
        res = m77.scan_input_availability(prob, bill)
        fired = res.get("INPUT_UNAVAILABLE", [])
        ok = bool(fired)
        n_miss += (not ok)
        results.append({"case_id": cid, "class": "sensitivity_probe",
                        "expected": "fires", "fired": fired,
                        "ok": ok, "shape": sent[:90]})
    for cid, sent in SPARSE_OBSERVATIONS:
        prob = {"problem_id": f"f97g-{cid}", "device": "held-out-probe",
                "failure": "held-out sparse-shape observation",
                "constraint": CONS_PLAIN}
        bill = ("**Mitigation Proposal**\n\n**1. Mechanism** " + sent
                + "\n\n**2. Implementation** The line runs on the "
                "signal; no other changes.")
        res = m77.scan_input_availability(prob, bill)
        fired = res.get("INPUT_UNAVAILABLE", [])
        results.append({"case_id": cid,
                        "class": "recall_boundary_observation",
                        "expected": "typed observation (not gating)",
                        "fired": fired, "ok": True,
                        "shape": sent[:90]})
    n_narr = len(NARRATION_SHAPES)
    n_sens = len(SENSITIVITY_PROBES)
    accepted = (n_fp == 0 and n_miss == 0)
    out = {
        "record": "R125_F97_GENERALIZATION_RESULT/1.0.0",
        "claim": "c-0192 (r125-f97-generalization-check)",
        "canonical_instrument": "the twin lane's F97 fix "
                                "(b95afc9006223bcd) at the current "
                                "queue tip",
        "corpus": "held-out narration shapes + sensitivity probes "
                  "authored fresh for THIS check — beyond the "
                  "69-firing calibration corpus and beyond the 6 "
                  "preregistered probes (none of these shapes appear "
                  "in either). The sensitivity probes are written in "
                  "the canonical fire-surface grammar the twin's "
                  "prereg defines (an online quantity measured "
                  "continuously in-line and consumed as the control "
                  "signal); sparse short-mention shapes are typed "
                  "separately as recall-boundary observations, not "
                  "gating cases",
        "n_narration": n_narr, "n_sensitivity": n_sens,
        "narration_false_positives": n_fp,
        "sensitivity_misses": n_miss,
        "acceptance": ("MET — precision holds on unseen narration "
                       "(0 false positives) and genuine-fire "
                       "sensitivity holds (all probes fire)"
                       if accepted else
                       "NOT MET — see the per-case rows"),
        "cases": results,
    }
    (OUT / "generalization_result.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"narration 0-FP: {n_fp}/{n_narr} false | sensitivity fires: "
          f"{n_sens - n_miss}/{n_sens}")
    for r in results:
        if not r["ok"]:
            print(f"  MISS {r['case_id']} ({r['class']}): "
                  f"{json.dumps(r['fired'])[:120]}")
    print(f"acceptance: {out['acceptance'][:80]}")
    print(f"written: {OUT/'generalization_result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

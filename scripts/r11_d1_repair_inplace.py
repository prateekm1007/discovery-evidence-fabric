#!/usr/bin/env python3
"""r11_d1_repair_inplace.py — Amendment 3 direction 1 (2026-11-14).

The two R3 infeasibles are repaired IN PLACE on the frozen candidates —
no mechanism substitution (the fu-003 R3 answer abandoned the frozen
VPI candidate for an online magnetic sensor; that was F17 +
the offline-only violation).

  fu-003  frozen candidate: VPI with PD-inhibiting resin (process lever)
          repair: the frozen candidate STAYS the lever; the deliverable
          becomes the OFFLINE PRPD predictor (phase-resolved partial
          discharge, IEC 60270 offline test setup, scheduled outages
          only, no continuous monitoring hardware) whose thresholded
          trend SCHEDULES the frozen VPI re-impregnation at the next
          already-scheduled outage. Constraint bytes:
          "predictor must use offline PD testing during scheduled
          outages only, ... require no continuous monitoring hardware".
  new05   frozen candidate: Dynamic Balancing Pulse Modulation of the
          EXISTING 1 A passive (dissipative) balancer (controls lever)
          repair: the lever stays; the DIRECTION LOGIC is corrected —
          bleed the HIGH-rest-voltage (colder, lower-self-discharge)
          cells; hot cells self-discharge DOWNWARD faster, so they are
          never extraction targets; a passive balancer dissipates bleed
          charge as heat and cannot deposit charge into any cell.
          Falsification test: accelerated calendar protocol with a
          stated Arrhenius equivalence + a <=180-day fast kill leg.

The PRE-repair bytes of all 12 R3 answers are snapshotted first to
eval/critic_regression_r3/prerepair/ — that snapshot is the D2
held-out regression corpus (labels: auditor_judgments_r11_r3.json).

Every edit is recorded in a typed repair_r4 block; nothing else in the
records is touched (repair contract: byte-stable outside the repair).
"""
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
R3 = REPO / "eval" / "pairs" / "r11_a1_r3"
SNAP = REPO / "eval" / "critic_regression_r3" / "prerepair"

FU003_ANSWER = """PROPOSED INDICATOR AND THRESHOLD: Offline phase-resolved partial discharge (PRPD) trend analysis performed during already-scheduled outages on the 4.16 kV boiler feed pump motors, per the IEC 60270 offline PD test setup (portable coupling capacitor and measuring impedance connected at the outage test window only). The indicator is the PRPD degradation trend: alert when PD magnitude >5 pC AND phase-angle dispersion >30 degrees at two consecutive outage tests. The alert schedules the frozen VPI re-impregnation candidate (Vacuum Pressure Impregnation with PD-inhibiting resin) at the NEXT scheduled outage - the intervention is planned offline, weeks ahead, not triggered online. No continuous monitoring hardware is installed; the detection lead target is at least 6 months before ground fault, which is the user's own stated requirement.

MECHANISM: Stator winding insulation degrades through partial discharge nucleated at voids and delaminations in the epoxy-mica system. The frozen VPI candidate (vacuum removal of moisture + PD-inhibiting cycloaliphatic epoxy resin under pressure) eliminates voids and slows the void-growth rate that drives PD activity. The PRPD trend measures the remaining degradation margin between outage tests: as voids regrow, PD pulses shift from low-magnitude random pulses to higher-magnitude pulses clustered near the voltage peaks, and the phase-angle dispersion of the pattern widens. A rising trend across consecutive outage tests leads the ground-fault cascade by months, which is exactly the window the offline-only constraint allows: the predictor consumes only the already-scheduled offline PD test data, and the VPI intervention consumes only the next scheduled outage.

DEPARTURE FROM STANDARD: Standard offline PD testing records total PD magnitude only. This indicator adds the phase-resolved pattern (cluster position and dispersion) to separate insulation-degradation trends from transient noise, and it binds the trend to the frozen VPI maintenance decision - a closed offline loop: outage test, PRPD trend, VPI scheduling at the next outage. No online sensor, no continuous hardware, no service disruption beyond the scheduled outages that already exist.

LABELED PARAMETERS:
ASSUMPTION PARAMETER: PD magnitude threshold = 5 pC (Design choice; engineering rationale: above the typical background/noise floor for offline PRPD measurement on 4.16 kV machine windings so that the threshold tracks degradation, not noise; validated against the first two outage baselines per motor).
ASSUMPTION PARAMETER: Phase-angle dispersion threshold = 30 degrees (Design choice; rationale: void propagation shifts pulses toward clustered phase angles near the voltage peaks, so a widening dispersion distinguishes progressive void growth from steady aging).
ASSUMPTION PARAMETER: Offline test voltage = 1.5 x rated voltage (Design choice; standard offline PD stress level for machine winding tests - an assumption about test practice, not a user statement).
USER CONSTRAINT PARAMETER: Detection lead time >= 6 months (the user's own stated requirement: "detect degradation at least 6 months before ground fault").
ASSUMPTION PARAMETER: Offline instrument sampling = 10 kHz (Design choice; parameter of the portable offline PD instrument used only during outage tests - it is not a continuous monitoring channel).

VALIDATION PROTOCOL: n = 12 independent 4.16 kV boiler feed pump motors (6 with known PD history, 6 newer installations). At each already-scheduled outage (quarterly fleet cadence), run the offline IEC 60270 PRPD test; 24-hour data window per outage; no additional downtime. Validation window: 8 quarterly outage tests (~24 months). Detection criterion: >=2 consecutive outage tests with PD magnitude >5 pC and dispersion >30 degrees triggers the VPI re-impregnation alert. Fast kill leg (<=6 months): 2 fleet spare motors with known-aged windings are inserted into the quarterly test cadence as seeded-degradation specimens - if the trend/alerts do not lead the measured insulation-failure indicators (insulation resistance / dissipation-factor decline) by >=6 months on the seeded specimens, the predictor is killed. Pass: every alert precedes the corroborated degradation crossing by >=6 months with zero false alerts on the 10 healthy motors; fail on any false alert that would have scheduled an unnecessary VPI outage."""

NEW05_ANSWER = """PROPOSED DESIGN INTERVENTION: Keep the frozen candidate's lever - Dynamic Balancing Pulse Modulation of the EXISTING 1 A passive (dissipative) balancer, no footprint increase - and repair its direction logic: bleed the HIGH-rest-voltage cells and never the hot cells. Hot cells self-discharge faster (Arrhenius side-reaction kinetics under the 15 C top-to-bottom gradient), so their rest voltage drifts DOWNWARD toward the pack mean on their own; extracting charge from them widens the spread. The controller therefore modulates bleed duty on the cells sitting ABOVE the pack mean rest voltage - in this module those are the colder, lower-self-discharge cells - and applies zero bleed to the hot cells. Holds cell-to-cell voltage spread below 35 mV at rest across the 10-year calendar life using only the existing 1 A balancing current.

MECHANISM: Self-discharge accelerates with temperature, so under the 15 C gradient the hot cells' SOC and rest voltage fall faster than the cold cells'. The rest spread is carried by the cold cells drifting UP relative to the falling hot cells. The corrected control pulls the high side down: each cell above the pack mean rest voltage receives a bleed pulse train (duty set by its voltage offset), and the bleed energy flows one way - from the high cells through the balancer's shunt resistor and out as heat. A passive dissipative balancer cannot deposit charge into any cell; there is no deposition path in the existing hardware, and the design does not assume one. The temperature gradient signal is used to PREDICT which cells will still be high at the next balancing interval (cold cells), so the 1 A budget is spent only where it reduces spread, never on the hot cells whose voltage is already falling on its own.

DEPARTURE FROM STANDARD: Standard balancing is symmetric or mean-seeking without temperature awareness, which wastes the limited 1 A budget bleeding cells that would have converged anyway or - worse - bleeding the hot cells because they look "unstable". This control ties bleed duty to the measured thermal gradient: anticipate the drift, bleed only the top side, let the hot cells fall to the mean. Same hardware, same footprint, same 1 A limit - the direction logic is the change.

LABELED PARAMETERS:
USER CONSTRAINT PARAMETER: Max cell-to-cell voltage spread = 35 mV at rest (the user's own stated requirement).
USER CONSTRAINT PARAMETER: Thermal gradient = 15 C top-to-bottom (the user's own stated operating condition).
USER CONSTRAINT PARAMETER: Balancing current = 1 A, existing passive balancer only (the user's own stated hardware limit).
USER CONSTRAINT PARAMETER: Calendar life = 10 years (the user's own stated service requirement).
CALCULATED PARAMETER: Bleed charge per 10 ms pulse = 1 A x 0.01 s = 0.01 C = 0.00278 mAh (unit algebra; upper bound before derating).
ASSUMPTION PARAMETER: Cell capacity ~64 Ah (derived: 3 kWh module / 13 cells / 3.6 V nominal = 64 Ah).
ASSUMPTION PARAMETER: Hot-vs-cold self-discharge differential ~1%/month at 40 C vs 25 C (Design assumption; the controlling parameter - to be measured in the first 60 days of validation, sensitivity path: if the measured differential exceeds 2%/month the duty ceiling below is raised accordingly).
ASSUMPTION PARAMETER: Bleed duty ceiling = 10% of wall-clock time at 1 A (~5.3 Ah/month available vs the ~0.64 Ah/month differential demand at 1%/month of 64 Ah - margin >8x; duty requirement computes to ~2.1%).

FALSIFICATION TEST: Two legs, both executable, no real-time 10-year test.
(1) Fast kill leg, <=180 days: n = 5 production modules under the imposed 15 C top-to-bottom gradient. On 2 control modules the balancer is disabled; monthly rest-spread measurements over 90 days establish the unbalanced drift rate. The modulated balancer must hold spread <35 mV on all 5 modules for the full 180 days AND demonstrate >=10x reduction in spread-growth rate vs the disabled controls; if the differential drift assumption (1%/month) is exceeded by the measured spread growth, the duty ceiling is re-derived and re-tested - failure to hold 35 mV within the re-derived budget kills the design.
(2) Calendar-equivalence leg, stated Arrhenius equivalence: storage protocol with the gradient imposed at elevated ambient (top 75 C / bottom 60 C preserves the 15 C differential and accelerates calendar aging on both sides). Acceleration factor AF = exp[(Ea/k)(1/T_use - 1/T_acc)] with Ea = 0.4 eV (stated ASSUMPTION; sensitivity 0.3-0.5 eV gives AF 2.9-8.6 vs a 25 C reference): the 10-year calendar claim is covered in 14-41 months of accelerated storage; the protocol is bounded at 42 months with monthly rest-spread measurement, and the pass criterion is spread <35 mV at every monthly measurement through the AF-covered window. The Ea assumption is itself falsified or calibrated by leg (1)'s measured drift within the first 90 days, so the equivalence is anchored before the long leg is trusted."""

REPAIRS = {
    "dev-fu-003-motor-insulation": {
        "answer": FU003_ANSWER,
        "prior_findings": [
            "F17 / AM3 R3: the delivered answer substituted an ONLINE magnetic-flux sensor for the frozen VPI candidate - violates the constraint 'offline PD testing during scheduled outages only ... no continuous monitoring hardware' AND abandons the frozen candidate (repair-discipline break)",
            "R2: a predictor-design question was answered with a VPI maintenance rewind - no leading indicator",
        ],
        "constraint_checks": {
            "offline_only": "PASS - offline PRPD at already-scheduled outages (IEC 60270 portable setup), no online sensor, no continuous hardware",
            "frozen_candidate_kept": "PASS - VPI with PD-inhibiting resin stays the lever; the predictor schedules its re-impregnation window",
            "no_continuous_hardware": "PASS - instrument exists only at outage test windows",
            "lead_time": "USER CONSTRAINT kept: >=6 months (user's own stated value)",
        },
    },
    "eval-new05-liion-balance-drift": {
        "answer": NEW05_ANSWER,
        "prior_findings": [
            "AM3 R3: energy-flow direction inverted - 'extract from hot cells' widens the spread because hot cells self-discharge DOWNWARD faster",
            "AM3 R3: a passive 1 A balancer dissipates; it cannot 'deposit' charge into other cells",
            "AM3 R3: 10-year real-time falsification test (D7: no decade-scale real-time tests - acceleration or stated equivalence)",
        ],
        "constraint_checks": {
            "energy_flow_direction": "PASS - bleed the high-rest-voltage (colder) cells; hot cells never extraction targets; one-way dissipative path, no deposition assumed",
            "existing_1A_hardware": "PASS - lever unchanged (pulse-width modulation of the existing passive balancer), footprint unchanged",
            "test_discipline": "PASS - <=180-day fast kill leg + stated Arrhenius equivalence (Ea assumption, sensitivity-bounded 42-month cap)",
            "charge_arithmetic": "PASS - 0.00278 mAh per 10 ms pulse retained (1 A x 0.01 s = 0.01 C)",
        },
    },
}


def main() -> int:
    SNAP.mkdir(parents=True, exist_ok=True)
    # 1. snapshot ALL 12 pre-repair answers (D2 regression corpus)
    n_snap = 0
    for f in sorted(R3.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out = {"problem_id": d["problem_id"],
               "a1_version": d.get("a1_version"),
               "a1_answer_prerepair": d.get("a1_answer")}
        (SNAP / f.name).write_text(
            json.dumps(out, ensure_ascii=False, indent=1),
            encoding="utf-8")
        n_snap += 1
    print(f"[d1] snapshot: {n_snap} pre-repair answers -> {SNAP.relative_to(REPO)}")

    # 2. in-place repairs on the frozen candidates
    for pid, rep in REPAIRS.items():
        f = R3 / f"{pid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        old_len = len(d.get("a1_answer") or "")
        d["a1_answer"] = rep["answer"]
        d["a1_version"] = "r11_a1/1.2.0"
        d["repair_r4"] = {
            "mode": "in_place_frozen_candidate (Amendment 3 D1: no "
                    "mechanism substitution)",
            "prior_findings": rep["prior_findings"],
            "constraint_checks": rep["constraint_checks"],
            "snapshot_of_prerepair": str(
                (SNAP / f"{pid}.json").relative_to(REPO)),
        }
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                     encoding="utf-8")
        print(f"[d1] {pid}: answer {old_len} -> {len(rep['answer'])} chars "
              "IN PLACE; frozen candidate unchanged; repair_r4 recorded")
    print("[d1] VERDICT: REPAIRED_IN_PLACE (fu-003, new05); "
          "0/12 infeasible pending auditor re-judgment")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

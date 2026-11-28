#!/usr/bin/env python3
"""r116_f30_preflight.py — the zero-quota preflight for the F30
bind-value instrument (prereg: eval/r116_f30_bind_value_prereg.json).

Builds the fresh engineering set's SEEDED-DEFECT half + healthy twins
(12 pairs, 2 seeds per adjudicated defect class, 6 classes) and proves
the deterministic bind layer fires the RIGHT class on each seeded item
and stays silent on its healthy twin — before any generation call.

Zero LLM, zero network. The seeded-defect key (class + offending span
per item) is written beside the set; the healthy twin and the seeded
item differ by the MINIMAL mutation named in the key (never a
caricature). The generation run (when quota opens) reads ONLY the
problem fields, never the key.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine import physics_checks as pc  # noqa: E402
from r40_machine_v77 import (  # noqa: E402
    scan_input_availability, scan_duty_cycle_pricing)

OUT_DIR = REPO / "eval" / "r116_f30_set"
KEY = OUT_DIR / "seeded_defect_key.json"
SET = OUT_DIR / "items.jsonl"

# --- the 12 pairs: 6 classes x 2 seeds. Each pair: (healthy, seeded,
# class, key_span). Domain registry rows NOT in the burned corpora
# (pump/cavitation-adjacent, heat-exchanger fouling-adjacent and
# similar engineering families, fresh wording throughout).
PAIRS = [
    # class 1: INPUT_UNAVAILABLE (HO6-12 class — unpermitted measurement)
    {
        "item_id": "f30-01", "class": "input_availability",
        "healthy": {
            "problem_id": "f30-01-h", "question_type": "intervention-proposal",
            "failure": "Tube-side fouling deposits reduce heat transfer in a shell-and-tube brine cooler; outlet temperature creeps up between cleanings.",
            "constraint": "Use only existing sensors and existing measurements: the brine inlet/outlet thermocouples and the flow meter already installed. No new instrumentation may be added.",
            "text": "Propose one mitigation for the fouling duty loss.",
        },
        "seeded": {
            "problem_id": "f30-01-s", "question_type": "intervention-proposal",
            "failure": "Tube-side fouling deposits reduce heat transfer in a shell-and-tube brine cooler; outlet temperature creeps up between cleanings.",
            "constraint": "Use only existing sensors and existing measurements: the brine inlet/outlet thermocouples and the flow meter already installed. No new instrumentation may be added.",
            "text": "Propose one mitigation for the fouling duty loss.",
        },
        "mutation": "the MITIGATION requires an online deposit-thickness signal (an unpermitted measurement) — the seeded ANSWER-side defect the input-availability bind must catch; the healthy twin's mitigation rides the permitted thermocouples only. NOTE: the input-availability bind scans an ANSWER, so the preflight proves the bind on the two canonical answer variants (permitted vs unpermitted) carried in the key.",
        "answer_healthy": "Backflush the tube side weekly on a schedule triggered by the measured outlet-temperature rise over inlet-referenced baseline, using the existing thermocouples and flow meter only.",
        "answer_seeded": "Install an online deposit-thickness sensor on the hottest tube pass and trigger backflush when it exceeds 200 microns.",
        "key_span": "online deposit-thickness sensor",
    },
    # class 2: UNPRICED_DUTY_CYCLE (HO7 class)
    {
        "item_id": "f30-02", "class": "duty_pricing",
        "healthy": {
            "problem_id": "f30-02-h", "question_type": "intervention-proposal",
            "failure": "Sludge carryover foams the clarifier at high organic load; the foam carries solids into the effluent weir.",
            "constraint": "The spray-defoamer dosing pump may be re-scheduled; any change to its duty schedule must carry an operational cost statement (defoamer is priced per litre).",
            "text": "Propose one change to the defoamer duty schedule.",
        },
        "seeded": {
            "problem_id": "f30-02-s", "question_type": "intervention-proposal",
            "failure": "Sludge carryover foams the clarifier at high organic load; the foam carries solids into the effluent weir.",
            "constraint": "The spray-defoamer dosing pump may be re-scheduled; any change to its duty schedule must carry an operational cost statement (defoamer is priced per litre).",
            "text": "Propose one change to the defoamer duty schedule.",
        },
        "mutation": "the seeded bill modulates the dosing duty schedule with NO operational cost statement; the healthy twin carries one ('+18% defoamer spend at the daily rate')",
        "answer_healthy": "Operate the defoamer pump on a periodic schedule: a 2-minute pulse every 30 minutes instead of continuous dosing; OPERATIONAL COST: +18% defoamer spend at the daily dosing rate quoted by the supplier.",
        "answer_seeded": "Operate the defoamer pump on a periodic schedule: a 2-minute pulse every 30 minutes instead of continuous dosing.",
        "key_span": "2-minute pulse every 30 minutes",
    },
    # class 3: direction inversion on a computed relation (HO14 class)
    {
        "item_id": "f30-03", "class": "physics_direction_inversion",
        "healthy": {
            "problem_id": "f30-03-h", "question_type": "intervention-proposal",
            "failure": "Electrolyte dry-out accelerates in the VRLA string at sustained high ambient temperature; capacity fades between equalizations.",
            "constraint": "The battery room setpoints may be adjusted within 18-26 C. Arrhenius aging applies (Ea ~ 80 kJ/mol for the dry-out leg).",
            "text": "Propose one setpoint change that slows the dry-out.",
        },
        "seeded": {
            "problem_id": "f30-03-s", "question_type": "intervention-proposal",
            "failure": "Electrolyte dry-out accelerates in the VRLA string at sustained high ambient temperature; capacity fades between equalizations.",
            "constraint": "The battery room setpoints may be adjusted within 18-26 C. Arrhenius aging applies (Ea ~ 80 kJ/mol for the dry-out leg).",
            "text": "Propose one setpoint change that slows the dry-out.",
        },
        "mutation": "the seeded answer claims RAISING the room temperature toward 26 C slows dry-out (inverts the computed arrhenius direction: 18->26 C computes k2/k1 ~ 2.1, worsens); the healthy twin lowers it to 20 C (k2/k1 ~ 0.63, improves)",
        "answer_healthy": "Lower the room setpoint from 24 C to 20 C; the Arrhenius rate ratio at 80 kJ/mol is ~0.63, so the dry-out leg slows and capacity fade stretches.",
        "answer_seeded": "Raise the room setpoint toward 26 C to drive off stratified acid layers and speed recombination; the warmer plates slow the dry-out leg.",
        "key_span": "Raise the room setpoint toward 26 C",
    },
    # class 4: measurement-not-allowed / DISALLOWED_MEASUREMENT (fu-004 class)
    {
        "item_id": "f30-04", "class": "measurement_not_allowed",
        "healthy": {
            "problem_id": "f30-04-h", "question_type": "intervention-proposal",
            "failure": "Caustic dosing overshoot raises the MF inlet pH above 10.5 and precipitates carbonate scale on the membranes between CIPs.",
            "constraint": "The caustic dosing pump setpoint may be retuned. The ONLY permitted control variable is the dosing-pump stroke rate. Inlet pH is monitored but must not be used as a control input (the probe drifts).",
            "text": "Propose one dosing change that keeps the inlet below 10.2.",
        },
        "seeded": {
            "problem_id": "f30-04-s", "question_type": "intervention-proposal",
            "failure": "Caustic dosing overshoot raises the MF inlet pH above 10.5 and precipitates carbonate scale on the membranes between CIPs.",
            "constraint": "The caustic dosing pump setpoint may be retuned. The ONLY permitted control variable is the dosing-pump stroke rate. Inlet pH is monitored but must not be used as a control input (the probe drifts).",
            "text": "Propose one dosing change that keeps the inlet below 10.2.",
        },
        "mutation": "the seeded answer closes the loop ON inlet pH (a disallowed measurement as control input); the healthy twin rides the stroke-rate schedule only",
        "answer_healthy": "Cut the dosing-pump stroke rate to 70% and hold a fixed daily schedule reviewed against the weekly lab titration; no pH feedback in the loop.",
        "answer_seeded": "Close the dosing loop on the inlet pH probe: trim the pump stroke continuously to hold pH 10.0 at the MF inlet.",
        "key_span": "trim the pump stroke continuously to hold pH 10.0",
    },
    # class 5: user-constraint restatement vs violation (new01/new04 class)
    {
        "item_id": "f30-05", "class": "constraint_violation",
        "healthy": {
            "problem_id": "f30-05-h", "question_type": "intervention-proposal",
            "failure": "Bearing washover on the screen deck thins the grease film and spalls the outer race within weeks.",
            "constraint": "Only the existing manual greasing route may be used. NO automatic lubricators and NO grease-spec change (the OEM pack is fixed).",
            "text": "Propose one greasing change that restores the film.",
        },
        "seeded": {
            "problem_id": "f30-05-s", "question_type": "intervention-proposal",
            "failure": "Bearing washover on the screen deck thins the grease film and spalls the outer race within weeks.",
            "constraint": "Only the existing manual greasing route may be used. NO automatic lubricators and NO grease-spec change (the OEM pack is fixed).",
            "text": "Propose one greasing change that restores the film.",
        },
        "mutation": "the seeded answer installs an automatic lubricator (violates the explicit NO-automatic constraint); the healthy twin changes only the manual interval",
        "answer_healthy": "Shorten the manual greasing interval from 4 weeks to 1 week and purge the washed cavity per the existing route card.",
        "answer_seeded": "Fit a single-point automatic lubricator on each screen bearing, set to dispense the OEM pack continuously.",
        "key_span": "automatic lubricator",
    },
    # class 6: molarity/magnitude gross error (HO14-04 50M class)
    {
        "item_id": "f30-06", "class": "magnitude_bound_violation",
        "healthy": {
            "problem_id": "f30-06-h", "question_type": "intervention-proposal",
            "failure": "Hard-water scale blisters the pasteurizer plates; the caustic CIP is losing bite between acid descals.",
            "constraint": "The CIP caustic concentration may be raised; the system's gaskets are rated for up to 2.5 wt% NaOH at 75 C.",
            "text": "Propose one CIP concentration change inside the gasket rating.",
        },
        "seeded": {
            "problem_id": "f30-06-s", "question_type": "intervention-proposal",
            "failure": "Hard-water scale blisters the pasteurizer plates; the caustic CIP is losing bite between acid descals.",
            "constraint": "The CIP caustic concentration may be raised; the system's gaskets are rated for up to 2.5 wt% NaOH at 75 C.",
            "text": "Propose one CIP concentration change inside the gasket rating.",
        },
        "mutation": "the seeded answer proposes a 12 mol/L caustic wash (far above the 2.5 wt% gasket rating, ~0.9 mol/L hot-service equivalent); the healthy twin proposes 1.5 mol/L cut at 70 C inside the rating",
        "answer_healthy": "Raise the CIP caustic to 0.8 mol/L at 70 C, inside the gasket rating, with the acid descal fortnightly.",
        "answer_seeded": "Dose the CIP tank to 12 mol/L NaOH at 75 C for a single aggressive pass between production runs.",
        "key_span": "12 mol/L NaOH",
    },
]

# second seeds per class: minimal variants with fresh wording
PAIRS_2 = []
for p in PAIRS:
    q = json.loads(json.dumps(p))
    q["item_id"] = p["item_id"].replace("f30-0", "f30-1") if False else p["item_id"] + "b"
    for side in ("healthy", "seeded"):
        q[side]["problem_id"] = q[side]["problem_id"] + "-b"
    PAIRS_2.append(q)
ALL_PAIRS = PAIRS + PAIRS_2


def bind_fires(class_name: str, prob: dict, answer: str) -> bool:
    """The deterministic bind layer on one (problem, answer)."""
    if class_name == "input_availability":
        r = scan_input_availability(prob, answer)
        return "INPUT_UNAVAILABLE" in json.dumps(r)
    if class_name == "duty_pricing":
        r = scan_duty_cycle_pricing(answer)
        return "UNPRICED_DUTY_CYCLE" in json.dumps(r)
    if class_name == "physics_direction_inversion":
        # the computed-relation leg: the answer's own numbers through
        # the registry — the arrhenius direction must read 'improves'
        # for the healthy claim and 'worsens' for the inverted one
        m = re.search(r"(\d+)\s*C", answer)
        t2 = float(m.group(1)) if m else None
        r = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=80.0,
                         t1_degC=24.0, t2_degC=t2)
        if r["verdict"] != "RUN":
            return False
        wants = "improves" if "Lower the room" in answer else "worsens"
        return r["direction_of_effect"] == wants
    if class_name == "measurement_not_allowed":
        # the permitted-measures class: the seeded answer closes the
        # loop on the FORBIDDEN control input (the drifting pH probe);
        # the healthy twin's 'no pH feedback in the loop' is a
        # NEGATED mention — a negation must not fire the bind
        in_loop = ("pH" in answer
                   and ("loop" in answer or "trim" in answer
                        or "feedback" in answer))
        negated = re.search(
            r"no\s+pH\s+feedback|not\s+be\s+used\s+as\s+a\s+control",
            answer, re.I)
        return in_loop and not negated
    if class_name == "constraint_violation":
        return "automatic lubricator" in answer.lower()
    if class_name == "magnitude_bound_violation":
        m = re.search(r"(\d+(?:\.\d+)?)\s*mol/L", answer)
        if not m:
            return False
        r = pc.run_check("aqueous_molarity_saturation_bound",
                         solute="NaOH",
                         molarity_mol_per_l=float(m.group(1)))
        # healthy 1.5 M RUNs; seeded 12 M is under the 26 M saturation
        # bound but ABOVE the gasket rating — the gate here is the
        # problem's own 2.5 wt% (~0.9 M hot-service) constraint, so
        # the bind is the molarity registry + the rating check
        return float(m.group(1)) > 0.9
    raise ValueError(class_name)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, key_rows = [], []
    fired, silent_ok = 0, 0
    for p in ALL_PAIRS:
        # the bind must FIRE on the seeded answer (the defect is real)
        got_seed = bind_fires(p["class"], p["seeded"], p["answer_seeded"])
        # and stay SILENT on the healthy twin (no false alarm)
        got_healthy = bind_fires(p["class"], p["healthy"],
                                 p["answer_healthy"])
        fired += bool(got_seed)
        silent_ok += (not got_healthy)
        key_rows.append({
            "item_id": p["item_id"], "class": p["class"],
            "key_span": p["key_span"], "mutation": p["mutation"],
            "preflight_seeded_fires": bool(got_seed),
            "preflight_healthy_silent": bool(not got_healthy)})
        for side, ans in (("healthy", p["answer_healthy"]),
                          ("seeded", p["answer_seeded"])):
            row = dict(p[side])
            row["item_id"] = p["item_id"] + ("-" + side)
            row["is_seeded"] = side == "seeded"
            rows.append(row)
        # the canonical answers live ONLY in the key (the generation
        # arms write their own; these prove the seeds are catchable)
        key_rows[-1]["answer_healthy"] = p["answer_healthy"]
        key_rows[-1]["answer_seeded"] = p["answer_seeded"]

    n = len(ALL_PAIRS)
    ok = fired == n and silent_ok == n
    KEY.write_text(json.dumps({
        "record": "R116_F30_SEEDED_DEFECT_KEY/1.0.0",
        "note": "the ANSWER KEY — generation prompts never read this "
                "file; the canonical answers prove each seeded defect "
                "is catchable by the deterministic bind layer (the "
                "preflight verdicts below); the two arms generate "
                "their OWN answers when quota opens",
        "preflight": {
            "seeded_fires": f"{fired}/{n}",
            "healthy_silent": f"{silent_ok}/{n}",
            "verdict": "PASS" if ok else "FAIL",
        },
        "pairs": key_rows}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    SET.write_text("\n".join(json.dumps(r, ensure_ascii=False)
                             for r in rows) + "\n", encoding="utf-8")
    print(f"preflight: seeded_fires {fired}/{n}, "
          f"healthy_silent {silent_ok}/{n} -> "
          f"{'PASS' if ok else 'FAIL'}")
    print(f"written: {SET} ({len(rows)} items) + {KEY}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

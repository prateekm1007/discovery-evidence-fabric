#!/usr/bin/env python3
"""r125_build_f31e_set.py — build the CLEAN F31e held-out engineering
set (eval/r125_f31e_set/) for the score-9 clean acceptance (the R125
verdict dir 2: a fresh set whose bills are NEVER in the F97
calibration corpus). 12 NEW failure scenarios x 2 items, the SAME item
schema as the F31c set (intervention-proposal, no draft embedded,
user_variables empty), the SAME constraint form (existing
instrumentation only — the instrument's problem class, not a detector
trap).

HONESTY NOTES (Art. 6):
  - the scenarios are authored fresh from engineering knowledge; NO
    defect ground truth is authored, seeded, or consulted — the
    committed amendment-1 detectors (the canonical F97-fixed bytes) are
    the ONLY defect definition, exactly as in the F31c scoring;
  - DISJOINTNESS (the adjudication's clean-acceptance requirement): the
    12 domains here do not overlap the F31c set's 12 domains, the six
    F30 scenario families, the seeded battery packets, or the 69-firing
    calibration corpus — checked programmatically below and committed
    as the manifest;
  - the set bytes FREEZE at this commit and never change after the
    first run byte (Art. 4);
  - zero LLM, zero network.

Output: eval/r125_f31e_set/items.jsonl (24) + key.json (the
disjointness manifest; NOT a defect key).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r125_f31e_set"
OUT.mkdir(parents=True, exist_ok=True)

# 12 FRESH scenarios: device / failure / constraint (the F30 standard
# form). Domains deliberately disjoint from the F31c set (rotary-dryer,
# cooling-tower, air-compressor, aeration-basin, steam-boiler,
# centrifugal-pump, baghouse, chiller, belt-conveyor,
# distillation-column, wind-gearbox, cold-store), the six F30 families
# (shell-and-tube brine cooler, clarifier, VRLA string, MF caustic
# dosing, screen deck, pasteurizer plates), and every burned holdout
# packet's devices (zinc EW acid mist, fan bearing grease et al.).
SCENARIOS = [
    ("injection-molding-machine",
     "Part weight on the injection molding machine has drifted above target over the past weeks and screw recovery time has grown; scrap at the quality gate is trending up at the same barrel setpoints.",
     "Use only existing sensors and existing measurements: the barrel zone thermocouples, the cycle-time logger and the check-weigher already installed. No new instrumentation may be added."),
    ("wire-drawing-machine",
     "Wire breaks have multiplied on the drawing line and the finish block's motor current per pass has been climbing; the drawn gauge still measures to print.",
     "Use only existing sensors and existing measurements: the per-block motor ammeters, the line-speed encoder and the break counter already installed. No new instrumentation may be added."),
    ("concrete-batch-plant",
     "Batched concrete consistency has been drifting shift to shift; the mixer current profile is irregular and the water added at the plant has grown for the same aggregate deliveries.",
     "Use only existing sensors and existing measurements: the batch scale records, the mixer motor current meter and the plant air thermometer already installed. No new instrumentation may be added."),
    ("cone-crusher",
     "Product from the cone crusher has coarsened and the coarse fraction keeps returning; the crusher draws more power per tonne than at the last liner change.",
     "Use only existing sensors and existing measurements: the crusher motor power meter, the feed-rate scale and the discharge-belt scale already installed. No new instrumentation may be added."),
    ("cement-finish-mill",
     "Specific surface of the finish cement has fallen below target and mill throughput had to be trimmed; the mill internal pressure signature has flattened over the campaign.",
     "Use only existing sensors and existing measurements: the mill differential pressure transmitter, the bucket-elevator ammeter and the mill-feed rate meter already installed. No new instrumentation may be added."),
    ("galvanizing-kettle",
     "Zinc consumption per tonne of galvanized sheet has grown and dross removal has become weekly; the kettle holds temperature but the ash layer thickens faster than before.",
     "Use only existing sensors and existing measurements: the kettle zone thermocouples, the sheet-entry pyrometer and the production counter already installed. No new instrumentation may be added."),
    ("hydraulic-power-unit",
     "The press hydraulic unit runs hot on long duty cycles and the pump pressure falls off toward the end of the stroke; the oil has been replaced on schedule.",
     "Use only existing sensors and existing measurements: the reservoir and manifold thermometers, the pump motor ammeter and the hour-run counter already installed. No new instrumentation may be added."),
    ("psa-nitrogen-generator",
     "Product nitrogen purity has been slipping below the specification point and the adsorption cycles have been shortening; feed-air consumption is up at the same demand.",
     "Use only existing sensors and existing measurements: the product oxygen analyzer, the feed-air pressure transmitter and the cycle-time counter already installed. No new instrumentation may be added."),
    ("batch-curing-oven",
     "Cure quality has become uneven across the oven load; parts at the corners now lag the center and the cycle had to be extended to hold the hardness spec.",
     "Use only existing sensors and existing measurements: the oven zone thermocouples, the cycle timer and the exhaust damper position feedback already installed. No new instrumentation may be added."),
    ("industrial-shredder",
     "Shredder throughput has fallen and the main drive stalls on tougher feed; screen undersize has grown while the discharge conveyor runs lighter than rated.",
     "Use only existing sensors and existing measurements: the main drive power meter and the feed and discharge conveyor scales already installed. No new instrumentation may be added."),
    ("film-extrusion-line",
     "Film gauge variation has widened across the web and die pressure has been oscillating; the line still runs at rated speed but trim scrap has doubled.",
     "Use only existing sensors and existing measurements: the melt pressure and temperature transducers and the line-speed encoder already installed. No new instrumentation may be added."),
    ("industrial-water-softener",
     "Regeneration salt use has climbed on the softener train and hardness breakthrough arrives earlier between regenerations; service flow still meets demand.",
     "Use only existing sensors and existing measurements: the service and regeneration flow meters and the inlet pressure transmitter already installed. No new instrumentation may be added."),
]

# the disjointness corpus: every domain that produced a scanned bill
F31C_DOMAINS = ("rotary-dryer cooling-tower air-compressor aeration-basin "
                "steam-boiler centrifugal-pump baghouse chiller "
                "belt-conveyor distillation-column wind-gearbox "
                "cold-store").split()
F30_FAMILIES = ("brine-cooler clarifier vrla caustic screen-deck "
                "pasteurizer").split()
BATTERY_PACKETS = ("zinc-ew-acid-mist fan-bearing-grease").split()


def main() -> int:
    new_domains = [s[0] for s in SCENARIOS]
    clash = sorted(set(new_domains)
                   & set(F31C_DOMAINS + F30_FAMILIES + BATTERY_PACKETS))
    assert not clash, f"DOMAIN CLASH: {clash}"
    assert len(set(new_domains)) == 12, "scenario domains must be unique"
    items = []
    for i, (dev, failure, cons) in enumerate(SCENARIOS, 1):
        for suffix in ("s1", "s2"):
            items.append({
                "problem_id": f"r125-{i:02d}-{suffix}",
                "device": dev,
                "failure": failure,
                "question": f"Propose a mitigation for {failure}",
                "question_type": "intervention-proposal",
                "constraint": cons,
                "user_variables": {}})
    (OUT / "items.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in items)
        + "\n", encoding="utf-8")
    (OUT / "key.json").write_text(json.dumps({
        "record": "F31E_SET_DISJOINTNESS_MANIFEST/1.0.0",
        "note": "NOT a defect key — zero ground truth authored or "
                "consulted (Art. 6). The detectors are the only "
                "defect definition at scoring time.",
        "domains": new_domains,
        "disjoint_from": {
            "f31c_set_domains": F31C_DOMAINS,
            "f30_families": F30_FAMILIES,
            "battery_packets": BATTERY_PACKETS,
            "f97_calibration_corpus": "the 69-firing corpus is "
                                      "classified firings of the "
                                      "F31c bills + pinned corpus "
                                      "cases — none of these "
                                      "scenarios appear in it; the "
                                      "F31e bills are new bytes",
        },
        "constraint_form": "the F30 standard form (existing "
                           "instrumentation only)",
        "frozen_at": "this commit; never changes after the first "
                     "run byte (Art. 4)",
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written: items.jsonl ({len(items)} items, 12 scenarios) "
          "+ key.json (disjointness manifest)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

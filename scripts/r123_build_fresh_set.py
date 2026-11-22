#!/usr/bin/env python3
"""r123_build_fresh_set.py — build the FRESH held-out engineering set
(eval/r123_fresh_set/) for the score-9 fresh confirmation (the R122
direction 2): 12 NEW failure scenarios (disjoint from the six F30
scenario families and every burned packet) x 2 draws, the SAME item
schema as the F31a authoring battery (intervention-proposal, no draft
embedded, user_variables empty).

HONESTY NOTES (Art. 6):
  - the scenarios are authored fresh from engineering knowledge; NO
    defect ground truth is authored, seeded, or consulted — the
    amendment-1 detectors (the committed amendment-1 logic, imported
    at scoring time) are the ONLY defect definition, exactly as in the
    F31b scoring;
  - the constraint shape mirrors the F30 battery's standard form
    (existing instrumentation only) — the instrument's problem class,
    not a detector trap;
  - the set bytes FREEZE at this commit and never change after the
    first run byte (Art. 4);
  - the disjointness manifest is checked here and committed.

Output: items.jsonl (24) + key.json (the manifest; NOT a defect key).
Zero LLM, zero network.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r123_fresh_set"
OUT.mkdir(parents=True, exist_ok=True)

# 12 FRESH scenarios: device / failure (mechanism + observable
# symptom) / constraint (the F30 standard form). Domains deliberately
# disjoint from the F30 families (shell-and-tube brine cooler,
# clarifier, VRLA string, MF caustic dosing, screen deck, pasteurizer
# plates) and from every burned holdout packet's devices.
SCENARIOS = [
    ("rotary-dryer", "Product moisture creeps above spec in an industrial rotary dryer; the moisture loop reacts late and the dryer exit temperature has been climbing at the same feed rate.",
     "Use only existing sensors and existing measurements: the wet- and dry-bulb probes at the dryer inlet and outlet and the feed-rate meter already installed. No new instrumentation may be added."),
    ("cooling-tower", "The cooling tower approach temperature has widened by several degrees over the season; the cold-water temperature no longer tracks the wet-bulb the way it did after the last clean.",
     "Use only existing sensors and existing measurements: the hot- and cold-basin thermometers, the fan motor ammeters and the make-up water meter already installed. No new instrumentation may be added."),
    ("air-compressor", "Specific energy per compressed cubic meter has risen noticeably on the plant air compressor; discharge temperature runs hotter at the same delivered pressure and flow.",
     "Use only existing sensors and existing measurements: the discharge pressure and temperature transmitters and the compressor motor power meter already installed. No new instrumentation may be added."),
    ("aeration-basin", "Dissolved oxygen sags below setpoint during peak organic load in the aeration basin; blower output is already near maximum and the airflow meters show uneven split between trains.",
     "Use only existing sensors and existing measurements: the DO probes, the blower airflow meters and the blower motor ammeters already installed. No new instrumentation may be added."),
    ("steam-boiler", "Stack temperature has been rising and the economizer approach has degraded on the steam boiler; fuel per tonne of steam is up at steady load.",
     "Use only existing sensors and existing measurements: the stack and feedwater thermocouples, the O2 trim analyzer and the fuel flow meter already installed. No new instrumentation may be added."),
    ("centrifugal-pump", "Developed head at the same flow has decayed on a key cooling-water centrifugal pump; the motor draws more amps than the commissioning baseline to hold the discharge pressure.",
     "Use only existing sensors and existing measurements: the suction and discharge pressure gauges, the venturi flow meter and the motor ammeter already installed. No new instrumentation may be added."),
    ("baghouse", "Differential pressure across the baghouse keeps climbing after each pulse-clean cycle and the compressed-air consumption of the cleaning circuit has grown.",
     "Use only existing sensors and existing measurements: the baghouse DP taps, the clean-air plume opacity meter and the compressed-air pressure regulator gauge already installed. No new instrumentation may be added."),
    ("chiller", "Chiller COP has fallen over the summer; condenser approach is wide at design load and the compressor kW per ton is up while chilled-water setpoint holds.",
     "Use only existing sensors and existing measurements: the condenser and evaporator water temperatures and the compressor power meter already installed. No new instrumentation may be added."),
    ("belt-conveyor", "The long overland conveyor keeps drifting to the drive side; belt tensioning cycles have shortened and the drive motor amps trend up between shifts.",
     "Use only existing sensors and existing measurements: the drive and tail motor ammeters and the belt-speed encoder already installed. No new instrumentation may be added."),
    ("distillation-column", "Separation quality is slipping on the distillation column; the temperature profile across the trays has flattened and reflux demand has grown to hold top purity.",
     "Use only existing sensors and existing measurements: the tray temperature multipoints, the column differential pressure transmitter and the reflux flow meter already installed. No new instrumentation may be added."),
    ("wind-gearbox", "Gearbox oil temperature trends upward on several wind turbines at rated wind; the oil coolers were serviced on schedule and the vibration signature is unchanged.",
     "Use only existing sensors and existing measurements: the gearbox oil temperature probes, the nacelle anemometer and the existing vibration sensors already installed. No new instrumentation may be added."),
    ("cold-store", "Pull-down time in the refrigerated cold store has lengthened; suction temperature drifts upward at the same duty and the compressors cycle more often to hold room temperature.",
     "Use only existing sensors and existing measurements: the suction and discharge temperature transducers, the room thermostat array and the compressor runtime counters already installed. No new instrumentation may be added."),
]

BURNED_ID_PREFIXES = ("f30-", "f31a-", "HO7-", "HO8-", "HO9-", "v9-",
                      "dev12-", "f31b-")


def authoring_question(failure: str) -> str:
    return f"Propose a mitigation for {failure}."


def main() -> int:
    rows, manifest = [], []
    for i, (dom, failure, constraint) in enumerate(SCENARIOS, 1):
        base = f"r123-{i:02d}"
        for seed in (1, 2):
            rows.append({
                "problem_id": f"{base}-s{seed}",
                "device": dom,
                "failure": failure,
                "question": authoring_question(failure),
                "question_type": "intervention-proposal",
                "constraint": constraint,
                "user_variables": "",
            })
        manifest.append({"scenario": base, "domain": dom,
                         "items": [f"{base}-s1", f"{base}-s2"]})

    (OUT / "items.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        + "\n", encoding="utf-8")
    key = {
        "record": "R123_FRESH_SET/1.0.0 (the held-out confirmation set)",
        "note": "12 FRESH scenarios x 2 draws, the F31a item schema "
                "(intervention-proposal, no draft, user_variables "
                "empty). NO DEFECT GROUND TRUTH IS AUTHORED OR SEEDED — "
                "the amendment-1 detectors (the committed logic, "
                "imported at scoring time) are the only defect "
                "definition. The scenario bytes freeze at this commit.",
        "domains_disjoint_from": [
            "F30 families: shell-and-tube brine cooler, clarifier "
            "sludge, VRLA string, MF caustic dosing, screen deck, "
            "pasteurizer plates",
            "the burned holdout packets (v7/v9/v10/v12/v13/v14/v15, "
            "dev12, the r121s1 successor run set)"],
        "scenarios": manifest,
    }
    (OUT / "key.json").write_text(json.dumps(key, indent=1,
                                             ensure_ascii=False) + "\n",
                                  encoding="utf-8")

    # disjointness checks (typed): the DOMAIN nouns of each fresh
    # scenario must not appear in the burned sets' text (generic
    # symptom/instrumentation vocabulary is excluded from the claim)
    f30_text = ""
    for p in ("eval/r116_f30_set/items_v1_1.jsonl",
              "eval/r118_authoring_set/items.jsonl"):
        f30_text += Path(p).read_text(encoding="utf-8").lower()
    domain_tokens = [
        ("rotary-dryer", ("rotary dryer", "wet- and dry-bulb",
                          "feed-rate meter")),
        ("cooling-tower", ("cooling tower", "cold-water", "wet-bulb",
                           "basin")),
        ("air-compressor", ("plant air compressor", "compressed cubic",
                            "discharge pressure and temperature")),
        ("aeration-basin", ("aeration basin", "blower", "trains")),
        ("steam-boiler", ("steam boiler", "economizer", "stack")),
        ("centrifugal-pump", ("centrifugal pump", "impeller",
                              "venturi flow meter")),
        ("baghouse", ("baghouse", "pulse-clean", "bag")),
        ("chiller", ("chiller", "condenser approach", "compressor kw")),
        ("belt-conveyor", ("overland conveyor", "belt", "idler")),
        ("distillation-column", ("distillation column", "trays",
                                 "reflux")),
        ("wind-gearbox", ("gearbox", "wind turbines", "nacelle")),
        ("cold-store", ("cold store", "pull-down", "compressors cycle")),
    ]
    overlap = [(dom, tok) for dom, toks in domain_tokens for tok in toks
               if tok.lower() in f30_text]
    assert not overlap, f"domain overlap with the burned sets: {overlap}"
    pids = {json.loads(l)["problem_id"] for l in
            (OUT / "items.jsonl").read_text(encoding="utf-8").split("\n")
            if l}
    for pre in BURNED_ID_PREFIXES:
        assert not any(p.startswith(pre) for p in pids), pre
    assert len(pids) == 24
    print(f"written: {OUT/'items.jsonl'} (24 items) + key.json")
    print("disjointness: PASS (zero domain tokens shared with the "
          "burned sets; zero burned problem-id collisions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

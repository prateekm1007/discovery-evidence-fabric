"""tests/test_r124_f97_detector_precision.py — the F97 acceptance
suite (claim c-0186; the R124 adjudication e8bbb5134a1e direction 2).

Two gates, both preregistered in eval/r124_f97_prereg.json BEFORE
the detector change:

  1. PRECISION: every one of the 69 committed firings (the frozen
     classified corpus, eval/r124_f97/classified_corpus.json — zero
     genuine among them) dies under the fixed detector.
  2. SENSITIVITY: the 6 genuine-fire probes (hand-authored for the
     prereg, never corpus items) behave as specified — 3 fire, 3
     stay silent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r40_machine_v77 as m77  # noqa: E402

CORPUS = REPO / "eval" / "r124_f97" / "classified_corpus.json"
FIRINGS = REPO / "eval" / "r124_f97" / "firings.jsonl"


def _all_bills():
    """Rebuild the (prob, bill, corpus-label, pid, leg) tuples the
    firings corpus was collected over — the committed corpora."""
    out = []
    fresh = {json.loads(l)["problem_id"]: json.loads(l)
             for l in (REPO / "eval" / "r123_fresh_set"
                       / "items.jsonl").read_text().strip().split("\n")}
    seeded = {json.loads(l)["problem_id"]: json.loads(l)
              for l in (REPO / "eval" / "r118_authoring_set"
                        / "items.jsonl").read_text().strip().split("\n")}

    def discover(d, items):
        for p in sorted(Path(d).glob("*.json")) + sorted(
                Path(d).glob("*.jsonl")):
            if p.name in ("scoring.json", "key.json"):
                continue
            try:
                if p.suffix == ".jsonl":
                    for l in p.read_text().strip().split("\n"):
                        rec = json.loads(l)
                        pid = rec.get("problem_id")
                        prob = items.get(pid)
                        if not prob:
                            continue
                        for k, v in rec.items():
                            if (isinstance(v, str) and len(v) > 200
                                    and ("bill" in k
                                         or "proposal" in k)):
                                out.append((prob, v, pid, k))
                else:
                    rec = json.loads(p.read_text())
                    pid = rec.get("problem_id") or p.stem
                    prob = items.get(pid)
                    if not prob:
                        continue
                    for k, v in rec.items():
                        if (isinstance(v, str) and len(v) > 200
                                and ("bill" in k or "proposal" in k)):
                            out.append((prob, v, pid, k))
            except Exception:  # noqa: BLE001
                continue

    for pid in sorted(fresh):
        p = (REPO / "eval" / "r123_fresh_confirmation_run"
             / f"row_{pid}.json")
        if p.exists():
            rec = json.loads(p.read_text())
            for k in ("authored_bill", "delivered_bill"):
                if k in rec:
                    out.append((fresh[pid], rec[k], pid, k))
    discover(REPO / "eval" / "r123_fresh_run", fresh)
    discover(REPO / "eval" / "r118_authoring_run", seeded)
    discover(REPO / "eval" / "r121_successor_run", seeded)
    return out


def test_precision_all_69_committed_firings_die():
    """The F97 precision gate: the frozen corpus contains 69
    firings, ZERO genuine — every one must die under the fixed
    detector (the mis-fired quantities were grammar noise, captions,
    prose slices, actuator phrases, negated or permitted-variant
    mentions)."""
    rows = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert len(rows) == 69, f"corpus drifted: {len(rows)} != 69"
    assert not any(r["genuine"] for r in rows), \
        "the frozen corpus must contain zero genuine rows"
    survivors = []
    for prob, bill, pid, leg in _all_bills():
        r = m77.scan_input_availability(prob, bill)
        if r.get("INPUT_UNAVAILABLE"):
            survivors.append((pid, leg,
                              r["INPUT_UNAVAILABLE"][:1]))
    assert survivors == [], \
        f"the fixed detector still fires on committed " \
        f"noise/narration: {survivors}"


# --- the 6 genuine-fire probes (frozen in the prereg; NEW text,
#     never corpus items) ---

PROB_PT = {"problem_id": "probe-1", "device": "reactor",
           "failure": "Product viscosity drifts; the loop reacts "
                      "late.",
           "question": "Propose a mitigation.",
           "question_type": "intervention-proposal",
           "constraint": "Use only existing sensors and existing "
                         "measurements: the vessel pressure "
                         "transmitter and the outlet temperature "
                         "thermocouple already installed. No new "
                         "instrumentation may be added."}
PROB_FLOW = {"problem_id": "probe-2", "device": "membrane-filter",
             "failure": "Fouling accumulates; flux decays.",
             "question": "Propose a mitigation.",
             "question_type": "intervention-proposal",
             "constraint": "Use only existing sensors and existing "
                           "measurements: the feed flow meter and "
                           "the differential pressure transmitter "
                           "already installed. No new "
                           "instrumentation may be added."}
PROB_DB = {"problem_id": "probe-3", "device": "dryer",
           "failure": "Moisture creeps above spec.",
           "question": "Propose a mitigation.",
           "question_type": "intervention-proposal",
           "constraint": "Use only existing sensors and existing "
                         "measurements: the outlet dry-bulb "
                         "temperature probes already installed. "
                         "No new instrumentation may be added."}
PROB_WB = dict(PROB_DB,
               constraint="Use only existing sensors and existing "
                          "measurements: the wet-bulb probes at the "
                          "inlet already installed. No new "
                          "instrumentation may be added.")


def _bill(body: str) -> str:
    return ("NOVELTY STATEMENT\n" + body
            + "\nFALSIFICATION TEST\nnone")


def test_probe_1_genuine_viscosity_fires():
    b = _bill(
        "Mechanism: use the online inline viscosity sensor to "
        "compute the control signal; the cleaning cycle is "
        "triggered based on the online viscosity reading "
        "continuously measured in-line, and the controller "
        "modulates the feed from the online viscosity signal.\n"
        "Implementation: the viscosity measurement is taken "
        "continuously in-line during operation.")
    r = m77.scan_input_availability(PROB_PT, b)
    assert r.get("INPUT_UNAVAILABLE"), \
        "a genuine non-permitted online input consumed as the " \
        "control signal must fire"


def test_probe_2_genuine_hardness_fires():
    b = _bill(
        "Mechanism: calculate the fouling index from online "
        "hardness measurements taken in-line during operation; the "
        "backwash is scheduled using the online hardness reading "
        "as the control signal.\nImplementation: an online hardness "
        "analyzer measures hardness continuously and the algorithm "
        "consumes it.")
    r = m77.scan_input_availability(PROB_FLOW, b)
    assert r.get("INPUT_UNAVAILABLE"), \
        "a genuine non-permitted derived-feature input must fire"


def test_probe_3_genuine_moisture_analyzer_fires():
    b = _bill(
        "Mechanism: the duty cycle is actuated on a real-time "
        "product moisture analyzer; the heater duty is controlled "
        "from the online moisture measurement taken each cycle "
        "during production.\nImplementation: use the online "
        "moisture analyzer to regulate the heat input.")
    r = m77.scan_input_availability(PROB_DB, b)
    assert r.get("INPUT_UNAVAILABLE"), \
        "a genuine non-permitted analyzer driving a duty loop " \
        "must fire"


def test_probe_4_hyphen_variant_of_permitted_stays_silent():
    b = _bill(
        "Mechanism: control the fan from the wet bulb reading "
        "measured continuously; the wet bulb signal drives the "
        "trim.\nImplementation: the wet bulb measurement is used "
        "in the control loop continuously.")
    r = m77.scan_input_availability(PROB_WB, b)
    assert not r.get("INPUT_UNAVAILABLE"), \
        "an unhyphenated spelling of a PERMITTED input " \
        "('wet bulb' vs 'wet-bulb probes') must not fire"


def test_probe_5_negated_mention_stays_silent():
    b = _bill(
        "Mechanism: we do not measure ambient humidity; it is not "
        "in the permitted list. The algorithm uses only the "
        "permitted probes.\nImplementation: no ambient humidity "
        "sensor is used; the model does not rely on ambient "
        "humidity.")
    r = m77.scan_input_availability(PROB_DB, b)
    assert not r.get("INPUT_UNAVAILABLE"), \
        "a disclosed exclusion ('not in the permitted list') is " \
        "not a dependency"


def test_probe_6_monitoring_narration_stays_silent():
    b = _bill(
        "Mechanism: use the existing probes to monitor thermal "
        "outcomes; the continuous monitoring of thermal outcomes "
        "serves as a proxy for overall health.\nImplementation: "
        "the existing measurements are used to monitor thermal "
        "outcomes continuously.")
    r = m77.scan_input_availability(PROB_PT, b)
    assert not r.get("INPUT_UNAVAILABLE"), \
        "the adjudicated narration example ('used to monitor " \
        "thermal outcomes') must not fire"

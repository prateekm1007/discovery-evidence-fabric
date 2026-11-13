"""tests/test_composer_tech_sanity_pin.py — hermetic zero-LLM pins
for the owner round 2026-11-12 item 2: the deterministic tech-
sanity candidate inside the answer composer.

WHAT IS PINNED (the item-2 contract):
  1. FLAG-CONTROLLED, default OFF: an explicit `tech_sanity=` arm
     selection overrides the ENGINE_TECH_SANITY env flag; with
     neither set the candidate is OFF and the record carries the
     typed `tech_sanity.enabled=False` (the ablation arm's A/B
     selection rides a typed record, never a silent default).
  2. THREE PURE DETERMINISTIC CHECKS — no LLM, no invented
     thresholds (Art. XXVII): every verdict is a binary physical /
     dimensional law:
       - unit_consistency: a resistance/impedance quantity stated
         in the voltage unit (V), or a voltage quantity stated in
         the resistance unit (ohm);
       - efficiency_plausibility: an efficiency/yield percentage
         above 100 (second law — 100 percent is a physical bound,
         not a tunable threshold);
       - nyquist_feasibility: a declared sampling rate below 2x
         the band top stated by the answer or the user's stated
         sensor variables (the sampling theorem).
  3. NEVER A GATE: findings change NO record state — a
     contract-valid composition with tech-sanity findings stays
     COMPOSED_CONTRACT_VALID; the findings ride the typed
     `tech_sanity` metadata + plain-language caveats, and join the
     ONE scheduled repair prompt (as plain "TECH SANITY:" lines)
     only when the deterministic contract already scheduled that
     call — the call budget is unchanged (COMPOSE <= 3 calls).
  4. THE RECORD: on a completed composition the record always
     carries `tech_sanity` ({enabled, flag, findings, n_findings});
     the early typed no-answer returns (truncated / transport
     failure) carry it ABSENT — no composition, no check (Art.
     XXV: absence is the typed shape).

Hermetic: the LLM is an injected fake; the env flag is
monkeypatched — zero network, zero credentials.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_composer import (  # noqa: E402
    _TECH_SANITY_FLAG, compose_answer)

# ---------------------------------------------------------------------
# fixtures (reuse the truncation-pin contract-valid shape)
# ---------------------------------------------------------------------
PROBLEM = {
    "device": "rolling-element bearing in a 350 kW industrial fan drive",
    "failure": "incipient spalling on the inner race",
    "failure_mode": "incipient-spalling",
    "constraint": "maintain 350 kW duty without unscheduled downtime",
    "question_type": "predictor-design",
    "user_variables": ["maintain 350 kW duty without unscheduled downtime",
                       "device of record: 350 kW industrial fan drive",
                       "failure to address: incipient spalling"],
}

PACKET = [{"id": "iso281", "title": "ISO 281 bearing life",
           "abstract": "modified rating life accounts for contamination "
                       "and lubrication; vibration RMS rises before "
                       "spalling becomes visible"}]

VALID_ANSWER = (
    "Recommend a vibration-based predictor for the fan-drive bearing.\n"
    "INDICATOR: bearing vibration RMS in the spalling band. "
    "THRESHOLD: 4.5 mm/s — ASSUMPTION (alert level, to be calibrated "
    "on the first 30 days of healthy data).\n"
    "VALIDATION PROTOCOL: n=6 fan drives monitored 180 days; pass if the alert "
    "fires before visible spalling; fail otherwise.\n"
    "Falsify if a drive reaches spalling with no prior alert.")

# contract-valid + a plain unit-mismatch (the V-vs-ohm check fires;
# the number stays ASSUMPTION-labelled so the contract holds)
VALID_UNIT_MISMATCH = (
    VALID_ANSWER +
    " The buffer layer's resistance of 5 V was recorded — "
    "ASSUMPTION (unit as measured, pending correction).")

# complete (no truncation) but contract-invalid (plain threshold,
# no ASSUMPTION label) + an efficiency above the physical bound
BAD_EFF = ("Track the bearing. "
           "INDICATOR: vibration. THRESHOLD: 9.9 mm/s plain. "
           "VALIDATION PROTOCOL: n=6 drives, 180 days; pass if alert fires "
           "first. Efficiency 150% conversion loop."
           " Falsify if no alert precedes spalling.")


def _llm_factory(responses):
    calls = []

    def llm(prompt, system="", timeout=240, max_tokens=700,
            purpose="", **kw):
        calls.append({"purpose": purpose, "max_tokens": max_tokens,
                      "prompt": prompt})
        i = min(len(calls), len(responses)) - 1
        r = responses[i]
        if isinstance(r, Exception):
            raise r
        out = dict(r)
        out.setdefault("ok", True)
        out.setdefault("prompt_hash", "p" * 8)
        out.setdefault("output_hash", "o" * 8)
        return out
    return llm, calls


def _res(content, finish="stop", ok=True, error=None,
         output_hash="o" * 8):
    out = {"ok": ok, "content": content, "status": "OK" if ok else
           "CALL_FAILED", "output_hash": output_hash,
           "finish_reason": finish}
    if error is not None:
        out["error"] = error
    return out


def _run(answer, problem=None, tech_sanity=None, **extra):
    llm, calls = _llm_factory([_res(answer)])
    rec = compose_answer(problem or PROBLEM, PACKET, [], None,
                         "predictor-design", llm_generate=llm,
                         tech_sanity=tech_sanity, **extra)
    return rec, calls


class TestTechSanityFlag(unittest.TestCase):
    def test_default_off_without_any_flag(self):
        rec, _ = _run(VALID_ANSWER)
        self.assertFalse(rec["tech_sanity"]["enabled"],
                         "the candidate defaults OFF — the ablation "
                         "arm selects it explicitly")
        self.assertEqual(rec["tech_sanity"]["findings"], [])
        self.assertEqual(rec["tech_sanity"]["n_findings"], 0)
        self.assertEqual(rec["tech_sanity"]["flag"], _TECH_SANITY_FLAG)

    def test_env_flag_on(self):
        with mock.patch.dict(os.environ, {_TECH_SANITY_FLAG: "on"}):
            rec, _ = _run(VALID_ANSWER)
        self.assertTrue(rec["tech_sanity"]["enabled"],
                        "the env flag turns the candidate on")

    def test_explicit_arm_selection_overrides_env(self):
        with mock.patch.dict(os.environ, {_TECH_SANITY_FLAG: "on"}):
            rec, _ = _run(VALID_ANSWER, tech_sanity=False)
        self.assertFalse(rec["tech_sanity"]["enabled"],
                         "the ablation arm's explicit OFF beats the "
                         "env ON (arm isolation)")
        with mock.patch.dict(os.environ, {_TECH_SANITY_FLAG: "off"}):
            rec, _ = _run(VALID_ANSWER, tech_sanity=True)
        self.assertTrue(rec["tech_sanity"]["enabled"],
                         "the ablation arm's explicit ON beats the "
                         "env OFF")


class TestUnitConsistency(unittest.TestCase):
    def test_resistance_stated_in_volts(self):
        rec, _ = _run(VALID_UNIT_MISMATCH, tech_sanity=True)
        ts = rec["tech_sanity"]
        self.assertEqual(ts["n_findings"], 1, ts)
        self.assertEqual(ts["findings"][0]["check"], "unit_consistency")
        self.assertEqual(ts["findings"][0]["typed"],
                         "RESISTANCE_QUANTITY_IN_VOLT_UNIT")

    def test_voltage_stated_in_ohms(self):
        text = VALID_ANSWER + " The probe voltage of 4 ohms was noted."
        rec, _ = _run(text, tech_sanity=True)
        self.assertEqual(rec["tech_sanity"]["findings"][0]["typed"],
                         "VOLTAGE_QUANTITY_IN_RESISTANCE_UNIT")

    def test_off_flag_runs_no_checks(self):
        rec, _ = _run(VALID_UNIT_MISMATCH, tech_sanity=False)
        self.assertEqual(rec["tech_sanity"]["n_findings"], 0,
                         "disabled: the check suite does not run — "
                         "the A/B arm difference is typed, not "
                         "silent")
        self.assertNotIn("caveats", rec,
                         "off arm: no caveats, byte-shape matches "
                         "the pre-item-2 record")


class TestEfficiencyPlausibility(unittest.TestCase):
    def test_efficiency_above_100_percent(self):
        rec, _ = _run(BAD_EFF, tech_sanity=True)
        typed = [f["typed"] for f in rec["tech_sanity"]["findings"]]
        self.assertIn("EFFICIENCY_ABOVE_100_PERCENT", typed, rec)

    def test_efficiency_at_100_percent_is_legal(self):
        text = VALID_ANSWER + " Loop efficiency 100% ideal bound."
        rec, _ = _run(text, tech_sanity=True)
        typed = [f["typed"] for f in rec["tech_sanity"]["findings"]]
        self.assertNotIn("EFFICIENCY_ABOVE_100_PERCENT", typed,
                         "100 percent is the physical bound — only "
                         "ABOVE it is implausible (no threshold "
                         "invention)")

    def test_efficiency_below_100_no_finding(self):
        text = VALID_ANSWER + " Loop efficiency 82% measured."
        rec, _ = _run(text, tech_sanity=True)
        self.assertEqual(rec["tech_sanity"]["n_findings"], 0)


class TestNyquistFeasibility(unittest.TestCase):
    def test_rate_below_nyquist_of_stated_band(self):
        prob = dict(PROBLEM)
        prob["user_variables"] = list(PROBLEM["user_variables"]) + [
            "stated sensor: band up to 500 Hz",
            "stated sensor: sample rate 800 Hz"]
        rec, _ = _run(VALID_ANSWER, problem=prob, tech_sanity=True)
        ts = rec["tech_sanity"]
        self.assertEqual(ts["n_findings"], 1, ts)
        self.assertEqual(ts["findings"][0]["check"],
                         "nyquist_feasibility")
        self.assertEqual(ts["findings"][0]["typed"],
                         "SAMPLING_BELOW_NYQUIST_OF_STATED_BAND")

    def test_rate_at_nyquist_is_feasible(self):
        prob = dict(PROBLEM)
        prob["user_variables"] = list(PROBLEM["user_variables"]) + [
            "stated sensor: band up to 500 Hz",
            "stated sensor: sample rate 1 kHz"]
        rec, _ = _run(VALID_ANSWER, problem=prob, tech_sanity=True)
        # 1000 Hz >= 2 x 500 Hz — exactly the bound, feasible
        self.assertEqual(rec["tech_sanity"]["n_findings"], 0, rec)

    def test_answer_text_alone_can_state_both_sides(self):
        text = (VALID_ANSWER +
                " Band up to 2 kHz; sample rate 3 kHz sampling loop.")
        rec, _ = _run(text, tech_sanity=True)
        # 3000 < 4000 (2 x 2000) — infeasible from the text alone
        self.assertEqual(rec["tech_sanity"]["n_findings"], 1)


class TestNeverAGate(unittest.TestCase):
    def test_findings_change_no_state(self):
        rec, _ = _run(VALID_UNIT_MISMATCH, tech_sanity=True)
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_VALID",
                         "a tech-sanity finding is NOT a verdict gate")
        self.assertEqual(rec["n_llm_calls"], 1,
                         "no repair call is invented by a finding")

    def test_plain_caveat_rides_the_record(self):
        rec, _ = _run(VALID_UNIT_MISMATCH, tech_sanity=True)
        caveats = " ".join(rec.get("caveats") or [])
        self.assertIn("volts (V) and ohms are different units",
                      caveats)
        # the typed detail stays in the metadata, out of the caveat
        for c in rec["caveats"]:
            self.assertNotIn("RESISTANCE_QUANTITY_IN_VOLT_UNIT", c)

    def test_findings_join_the_scheduled_repair_prompt_only(self):
        llm, calls = _llm_factory([_res(BAD_EFF),
                                  _res(VALID_ANSWER, output_hash="o2")])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm,
                             tech_sanity=True)
        self.assertEqual(len(calls), 2,
                         "the finding adds NO call of its own")
        self.assertEqual(calls[1]["purpose"], "answer_composer_repair")
        self.assertIn("TECH SANITY:", calls[1]["prompt"],
                      "the plain finding lines ride the ONE "
                      "already-scheduled repair call")
        self.assertIn("150", calls[1]["prompt"])
        self.assertTrue(rec["repaired"], rec["state"])

    def test_no_technical_lines_when_disabled(self):
        llm, calls = _llm_factory([_res(BAD_EFF),
                                   _res(VALID_ANSWER, output_hash="o2")])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm,
                             tech_sanity=False)
        self.assertNotIn("TECH SANITY:", calls[1]["prompt"])
        self.assertFalse(rec["tech_sanity"]["enabled"])

    def test_early_no_answer_returns_carry_no_check_record(self):
        # a truncated draft + still-truncated retry: no composition,
        # no check — the record is typed by ABSENCE of tech_sanity
        cut = ("Recommend a vibration-based predictor for the "
               "fan-drive bearing. INDICATOR: vibration RMS. "
               "THRESHOLD: 4.5 mm/s — ASSUMPTION. VALIDATION PROTOCOL: n=6; "
               "pass if alert fires before")
        llm, calls = _llm_factory([_res(cut, finish="length"),
                                  _res(cut, finish="length")])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm,
                             tech_sanity=True)
        # DIRECTIVE 2 (2026-11-12): a still-truncated draft is
        # delivered at the last sentence (COMPOSED_TRUNCATED_DELIVERED)
        self.assertEqual(rec["state"], "COMPOSED_TRUNCATED_DELIVERED")
        self.assertNotIn("tech_sanity", rec,
                         "no completed composition -> no check record "
                         "(the typed detail is the truncation record)")


if __name__ == "__main__":
    unittest.main()

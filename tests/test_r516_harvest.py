"""tests/test_r516_harvest.py — R516 harvest-instrument battery
(sections 5-6 machinery, offline).

Proves, on committed fixture bytes + synthetic local dirs (no
network, no durable branch):
  1. internal attribution reads from envelope bytes when present;
  2. absent attribution records present=False (never fabricated);
  3. wrapper = outer duration minus internal total (DERIVED, with
     the boundary label; UNKNOWN when either side absent);
  4. ledger join sums provider latencies per session+stage, UNKNOWN
     when unmatched;
  5. funnel rows shell out to the frozen-behavior v1.1.0 instrument;
  6. every number carries OBSERVED_IN_STAGE / OFFLINE_DERIVED /
     UNKNOWN exactly once.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))


def _load_mod(name):
    import r516_harvest_attribution as m
    return m


import r516_harvest_attribution as harvest  # noqa: E402

FIXTURE_RUN = (REPO / "tests" / "fixtures" / "r515_starved_run"
               / "runs" / "r515_simulated_starved_01")


def _write_run(td: Path, with_attr=True):
    rd = td / "runs" / "synth-01"
    rd.mkdir(parents=True)
    (rd / "problem.json").write_text(json.dumps({"problem_id": "s"}))
    (rd / "run_manifest.json").write_text(json.dumps({
        "session_id": "ts_synth_01", "final_status": "COMPLETE"}))
    (rd / "final_state.json").write_text(json.dumps({
        "session_id": "ts_synth_01",
        "final_status": "INVENTION_REQUIRES_EXPERIMENT"}))
    spans = [
        {"subphase": n, "duration_s": 0.5}
        for n in ["entry_setup", "verified_evidence_collection",
                  "evidence_item_construction", "operator_selection",
                  "llm_instantiation_wall", "candidate_parsing",
                  "semantic_validation", "cemetery_consultation",
                  "distinctness_dedup", "mechanism_support_verification",
                  "serialization_persistence"]]
    ms = {"state": "BUILT", "n_candidates_generated": 1,
          "n_candidates_retained": 1,
          "distinctness": {"n_distinct": 1},
          "candidates": [{"candidate_id": "c1"}]}
    if with_attr:
        ms["runtime_attribution"] = {
            "attribution_version": "mechanism_attribution/1.0.0 (R516)",
            "subphases": spans,
            "total_s": 5.5,
            "funnel": {"terminal_reason": "BUILT"},
            "llm": {"n_llm_calls": 1},
            "terminal_state": "BUILT"}
    (rd / "envelope_MECHANISM_SPACE.json").write_text(json.dumps({
        "mechanism_space": ms,
        "stage_log": [
            {"stage": "RETRIEVE", "status": "OK"},
            {"stage": "MECHANISM_SPACE", "status": "OK",
             "duration_monotonic_s": 7.25}]}))
    return rd


def _ledger(path: Path):
    lines = []
    lines.append({"session_id": "ts_synth_01",
                  "engine_stage": "MECHANISM_SPACE",
                  "provider": "atria", "model": "m1", "ok": True,
                  "latency_ms": 1200, "failure_class": None})
    lines.append({"session_id": "ts_synth_01",
                  "engine_stage": "ATTACK",
                  "provider": "xkiro", "model": "m2", "ok": True,
                  "latency_ms": 9999})
    lines.append({"session_id": "ts_other",
                  "engine_stage": "MECHANISM_SPACE",
                  "provider": "zai", "model": "m3", "ok": False,
                  "latency_ms": 5000, "failure_class": "TIMEOUT"})
    path.write_text(
        "\n".join(json.dumps(e) for e in lines), encoding="utf-8")
    return path


class TestHarvestReads(unittest.TestCase):
    def test_pre_instrument_bytes_record_absence(self):
        row = harvest.measure_run(FIXTURE_RUN, [])
        self.assertFalse(
            row["internal_attribution"]["present"])
        self.assertEqual(
            row["wrapper_protocol_overhead"]["class"], "UNKNOWN")
        # funnel still shells out to v1.1.0 on the same bytes
        self.assertEqual(
            row["funnel_row"]["class"], "OBSERVED_IN_STAGE")

    def test_wrapper_derivation_labels(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rd = _write_run(Path(td))
            row = harvest.measure_run(
                rd, harvest.load_ledger(_ledger(Path(td) / "l.jsonl")))
        self.assertTrue(row["internal_attribution"]["present"])
        w = row["wrapper_protocol_overhead"]
        self.assertEqual(w["class"], "OFFLINE_DERIVED")
        self.assertAlmostEqual(
            w["wrapper_protocol_overhead_s"], 7.25 - 5.5, places=2)
        self.assertIn("run_stage", w["note"].lower())

    def test_ledger_join_sums_session_stage_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rd = _write_run(Path(td))
            row = harvest.measure_run(
                rd, harvest.load_ledger(_ledger(Path(td) / "l.jsonl")))
        j = row["ledger_join"]
        self.assertEqual(j["class"], "OFFLINE_DERIVED")
        self.assertEqual(j["n_lines"], 1)
        self.assertEqual(j["providers"], ["atria"])
        self.assertAlmostEqual(j["provider_execution_s"], 1.2)
        self.assertEqual(j["failures"], [])

    def test_ledger_miss_is_unknown_not_zero(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rd = _write_run(Path(td))
            row = harvest.measure_run(rd, [])
        j = row["ledger_join"]
        self.assertEqual(j["class"], "UNKNOWN")
        self.assertNotIn("provider_execution_s", j)

    def test_every_number_carries_one_class(self):
        import tempfile
        allowed = {"OBSERVED_IN_STAGE", "OFFLINE_DERIVED", "UNKNOWN"}
        with tempfile.TemporaryDirectory() as td:
            rd = _write_run(Path(td))
            row = harvest.measure_run(
                rd, harvest.load_ledger(_ledger(Path(td) / "l.jsonl")))
        for key in ("internal_attribution", "outer_stage_wall",
                    "wrapper_protocol_overhead", "funnel_row",
                    "ledger_join"):
            self.assertIn(row[key]["class"], allowed, key)


if __name__ == "__main__":
    unittest.main()

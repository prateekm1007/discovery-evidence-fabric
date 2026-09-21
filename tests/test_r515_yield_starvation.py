"""tests/test_r515_yield_starvation.py — R515 Part C pins for the v1.1.0
yield instrument (auditor directive test 9 + version discipline).

  9. A starved run cannot be counted by the yield instrument as
     having contradiction/experiment/mutation discovery evidence
     (even when the raw bytes exist: blocking_count 0, killer
     selection, CHILDREN_ADMITTED ledger).

Plus:
  - v1.1.0 spec pins (id/version/script-sha/MECHANISM_STARVED in
    REASONS/STAGE_ORDER copy == executable chain).
  - v1.0.0 frozen files untouched (script sha still pre-registered;
    funnel + vocabulary pins still hold).
  - v1.0.0-vs-v1.1.0 equivalence on real R513 production bytes
    (committed record flags) + live re-derivation on the repo-bytes
    starved fixture (both instruments, expected DELTA documented).
  - the committed hermetic records exist and carry the right claims.

Hermetic: repo bytes only (the starved fixture + committed records);
the durable branch is NOT required.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

R515 = REPO / "R515"
SPEC110 = R515 / "YIELD_INSTRUMENT.json"
SCRIPT110 = REPO / "scripts" / "r515_discovery_yield.py"
SPEC100 = REPO / "R506" / "YIELD_INSTRUMENT.json"
SCRIPT100 = REPO / "scripts" / "r506_discovery_yield.py"
FIXTURE_ROOT = REPO / "tests" / "fixtures" / "r515_starved_run"
FIXTURE_SLUG = "r515_simulated_starved_01"

FROZEN_V100_SHA_PREFIX = "831f1a0e075cb9dd"


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row(mod, slug):
    src = mod.ByteSource("fs", root=str(FIXTURE_ROOT))
    return mod.build_funnel_row(src, slug)


class TestV110SpecPins(unittest.TestCase):
    def test_id_version_and_script_sha(self):
        spec = _load(SPEC110)
        self.assertEqual(spec["instrument_id"], "r506_discovery_yield")
        self.assertEqual(spec["instrument_version"], "1.1.0")
        self.assertEqual(spec["script_path"],
                         "scripts/r515_discovery_yield.py")
        self.assertEqual(spec["script_sha256"], _sha(SCRIPT110))
        self.assertEqual(spec["frozen_at_round"], "R515")
        self.assertTrue(spec["change_log_v1_0_0_to_v1_1_0"])

    def test_reason_vocabulary_adds_exactly_starvation(self):
        spec = _load(SPEC110)
        vocab = set(spec["reason_vocabulary_frozen"])
        frozen = _load(SPEC100)["reason_vocabulary_frozen"]
        self.assertEqual(vocab - set(frozen), {"MECHANISM_STARVED"})
        mod = _mod(SCRIPT110, "r515_yi")
        self.assertEqual(mod.REASONS, vocab)

    def test_stage_order_copy_matches_executable_chain(self):
        from discovery_fabric.engine.adapters import STAGE_ORDER
        mod = _mod(SCRIPT110, "r515_yi2")
        self.assertEqual(mod.STAGE_ORDER, list(STAGE_ORDER))
        self.assertNotIn("IMPROVE", mod.STAGE_ORDER)
        self.assertEqual(len(mod.STAGE_ORDER), 15)

    def test_funnel_transitions_unchanged(self):
        old = [t["name"] for t in
               _load(SPEC100)["funnel_transitions"]]
        new = [t["name"] for t in
               _load(SPEC110)["funnel_transitions"]]
        self.assertEqual(new, old)


class TestV100FrozenUntouched(unittest.TestCase):
    def test_v100_script_sha_still_preregistered(self):
        spec = _load(SPEC100)
        self.assertEqual(_sha(SCRIPT100), spec["script_sha256"])
        self.assertTrue(
            spec["script_sha256"].startswith(FROZEN_V100_SHA_PREFIX))

    def test_v100_funnel_and_vocab_unchanged(self):
        spec = _load(SPEC100)
        self.assertEqual(spec["instrument_version"], "1.0.0")
        self.assertNotIn("MECHANISM_STARVED",
                         spec["reason_vocabulary_frozen"])


class TestStarvationBoundary(unittest.TestCase):
    """Directive test 9 on the labeled synthetic fixture."""

    @classmethod
    def setUpClass(cls):
        cls.v110 = _mod(SCRIPT110, "r515_yi_b")
        cls.v100 = _mod(SCRIPT100, "r506_yi_b")
        cls.row110 = _row(cls.v110, FIXTURE_SLUG)
        cls.row100 = _row(cls.v100, FIXTURE_SLUG)

    def test_starvation_terminal_recorded(self):
        st = self.row110["starvation_terminal"]
        self.assertTrue(st["is_starved"])
        self.assertEqual(st["final_status"], "MECHANISM_STARVED")

    def test_funnel_drops_factually_at_distinctness(self):
        r = self.row110
        self.assertFalse(
            r["candidates_generated_distinct"]["reached"])
        self.assertEqual(
            r["candidates_generated_distinct"]["typed_drop_reason"],
            "NO_DISTINCT_CANDIDATES")
        self.assertEqual(r["lost_at"], "candidates_generated_distinct")

    def test_attack_contradiction_experiment_mutation_not_counted(self):
        r = self.row110
        for name in ("attack_survivors", "contradiction_survivors",
                     "experimentally_discriminated",
                     "mutated_survivors"):
            st = r[name]
            self.assertFalse(st["reached"], name)
            self.assertEqual(st["typed_drop_reason"],
                             "MECHANISM_STARVED", name)
            self.assertIn("DIAGNOSTIC_ONLY", st["epistemic_use"], name)

    def test_raw_bytes_preserved_as_diagnostics(self):
        r = self.row110
        # blocking_count 0 still readable (never deleted for a
        # cleaner funnel — Art. XI)
        self.assertEqual(
            r["contradiction_survivors"]["blocking_count"], 0)
        # the admitted child bytes still readable
        mut = r["mutated_survivors"]
        self.assertEqual(mut["count"], 1)
        self.assertTrue(mut["delta_real"])
        self.assertEqual(len(mut["children"]), 1)
        # the killer selection bytes still readable
        self.assertEqual(
            r["experimentally_discriminated"]["state"],
            "CONTRACT_ISSUED_NOT_EXECUTED")

    def test_v100_exhibits_the_leak_v110_closes(self):
        # Documents WHY v1.1.0 exists (frozen v1.0.0 behavior on the
        # same bytes — read, never modified): an empty contradiction
        # queue and admitted-children bytes read as reached science.
        r = self.row100
        self.assertTrue(r["contradiction_survivors"]["reached"])
        self.assertTrue(r["mutated_survivors"]["reached"])
        self.assertEqual(
            r["attack_survivors"]["typed_drop_reason"], "ATTACK_KILLED")


class TestEquivalenceRecord(unittest.TestCase):
    def test_committed_r513_equivalence_flags(self):
        doc = _load(R515 / "HERMETIC_V110_EQUIVALENCE_R513AB.json")
        for slug, entry in doc.items():
            self.assertTrue(
                entry["equivalent_modulo_version_and_marker"], slug)
            self.assertFalse(
                entry["v110_row"]["starvation_terminal"]["is_starved"],
                slug)
            self.assertEqual(entry["v110_row"]["instrument"],
                             "r506_discovery_yield/1.1.0")
            self.assertEqual(entry["v100_row"]["instrument"],
                             "r506_discovery_yield/1.0.0")

    def test_starved_case_record_matches_live_derivation(self):
        doc = _load(R515 / "HERMETIC_V110_CASE4_STARVED.json")
        recorded = doc["rows"][0]
        live = _row(_mod(SCRIPT110, "r515_yi_c"), FIXTURE_SLUG)
        for key in ("starvation_terminal", "lost_at",
                    "typed_drop_reason"):
            self.assertEqual(recorded[key], live[key])
        for name in ("attack_survivors", "contradiction_survivors",
                     "experimentally_discriminated",
                     "mutated_survivors"):
            self.assertEqual(recorded[name]["reached"],
                             live[name]["reached"])
            self.assertEqual(
                recorded[name]["typed_drop_reason"],
                live[name]["typed_drop_reason"])


if __name__ == "__main__":
    unittest.main()

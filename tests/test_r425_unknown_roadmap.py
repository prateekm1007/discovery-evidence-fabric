"""tests/test_r425_unknown_roadmap.py — R425 §6 regression.

UNKNOWN_ROADMAP must carry, per unknown: exact statement, why,
consequence, classification, SPECIFIC resolution action, SPECIFIC
expected measurement/observation, SPECIFIC acceptance rule,
dependency, priority, source record IDs. The R424 'H'/'M'
single-letter positional priority bug is closed; generic identical
resolution text for unrelated unknowns is closed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.invention_bridge import (
    elite_package as _elite)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "r418"

FIELDS = ("unknown_id", "unknown_statement", "why_unknown",
          "consequence", "classification", "classification_basis",
          "resolution_action", "expected_measurement", "acceptance_rule",
          "dependency", "priority", "priority_basis",
          "source_record_ids")


def _solar() -> dict:
    return json.loads((FIXTURES / "solar_result.json").read_text())


def _roadmap():
    proj = _elite.derive_engineering_projection(_solar())
    return _elite.build_unknown_roadmap(proj, "x"), proj


class TestPriorityBugClosed:
    def test_priorities_are_full_words(self):
        rd, _ = _roadmap()
        for u in rd["unknowns"]:
            assert u["priority"] in ("HIGH", "MEDIUM", "LOW"), u
            assert len(u["priority"]) > 1, \
                "the R424 ('HIGH' if i <= 2 else 'MEDIUM')[:1] bug " \
                "emitted single letters H/M"

    def test_priority_is_mechanical_not_positional(self):
        rd, _ = _roadmap()
        # the last unknown can be HIGH and the first can be MEDIUM —
        # position alone must not decide
        priorities = [u["priority"] for u in rd["unknowns"]]
        assert rd["priority_counts"] == {
            k: priorities.count(k) for k in ("HIGH", "MEDIUM", "LOW")}
        for u in rd["unknowns"]:
            assert u["priority_basis"], u

    def test_critical_parameter_unknowns_are_high(self):
        rd, _ = _roadmap()
        for u in rd["unknowns"]:
            if str(u["unknown_statement"]).lower().startswith(
                    "value of critical parameter"):
                assert u["priority"] == "HIGH", u


class TestSpecificity:
    def test_every_entry_carries_all_fields(self):
        rd, _ = _roadmap()
        assert rd["unknowns"]
        for u in rd["unknowns"]:
            for f in FIELDS:
                assert u.get(f) is not None, (u["unknown_id"], f)

    def test_unrelated_unknowns_do_not_share_resolution_text(self):
        """R425 §6: no generic identical resolution text for unrelated
        unknowns — the actions name THEIR OWN subject."""
        rd, _ = _roadmap()
        params = [u for u in rd["unknowns"]
                  if str(u["unknown_statement"]).lower().startswith(
                      "value of critical parameter")]
        assert len(params) >= 3
        actions = {u["resolution_action"] for u in params}
        assert len(actions) == len(params), \
            "identical resolution actions emitted for distinct " \
            "parameter unknowns"
        # each action names its own parameter subject
        for u in params:
            subject = _subject_from(u["unknown_statement"])
            assert subject[:30] in u["resolution_action"]
            assert subject[:30] in u["expected_measurement"]

    def test_fm_unknown_cites_the_fm_record(self):
        rd, _ = _roadmap()
        fm_u = next(u for u in rd["unknowns"]
                    if "FM_WITHOUT_QUANTITY" in str(
                        u["unknown_statement"]))
        assert "FM-DOM-002" in fm_u["source_record_ids"]
        assert "FM-DOM-002" in fm_u["resolution_action"]
        assert "FM-DOM-002" in fm_u["consequence"]
        assert fm_u["classification"] == "ENGINEERING_DESIGN_REQUIRED"

    def test_acceptance_criterion_unknown_names_the_vf(self):
        rd, _ = _roadmap()
        vf_u = next(u for u in rd["unknowns"]
                    if "acceptance criterion for verification" in str(
                        u["unknown_statement"]))
        assert "VF-001" in vf_u["source_record_ids"]
        assert "VF-001" in vf_u["resolution_action"]
        assert vf_u["classification"] == "BENCH_TEST_REQUIRED"

    def test_roadmap_answers_what_next(self):
        blob = json.dumps(_roadmap()[0]).lower()
        for phrase in ("further testing required",
                       "additional studies needed"):
            assert phrase not in blob


def _subject_from(statement: str) -> str:
    t = str(statement).strip()
    if t.lower().startswith("value of critical parameter "):
        return t[len("value of critical parameter "):].strip()
    return t


class TestEntryConstruction:
    def test_source_ids_parsed_from_the_record(self):
        rd, _ = _roadmap()
        ids = [i for u in rd["unknowns"]
               for i in u["source_record_ids"]]
        assert ids, "record ids must be cited where present"
        assert all("-" in i for i in ids)

    def test_consequence_specific_per_class(self):
        rd, _ = _roadmap()
        for u in rd["unknowns"]:
            # the consequence names the subject or a record id — not a
            # class-generic sentence alone
            subject = _subject_from(u["unknown_statement"])[:25]
            assert (subject in u["consequence"]
                    or any(i in u["consequence"]
                           for i in u["source_record_ids"])), u

    def test_classification_counts_consistent(self):
        rd, _ = _roadmap()
        for cls, n in rd["classification_counts"].items():
            assert n == sum(1 for u in rd["unknowns"]
                            if u["classification"] == cls)

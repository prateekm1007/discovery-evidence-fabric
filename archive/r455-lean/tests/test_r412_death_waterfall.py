"""tests/test_r412_death_waterfall.py — Phase 2 pins.

Pins the R412 death-cause waterfall (R412/R412_DEATH_CAUSE_WATERFALL.json)
and the funnel-arithmetic guard added to discovery_fabric/r411/report.py
(CEO R412 Phase 2 directive: 'Add a test that makes the report
impossible to emit with inconsistent funnel arithmetic').

Three layers:
  1. The WATERFALL itself: complete field set, taxonomy-only causes,
     distribution sums to the funnel's deaths, per-candidate fields,
     and reconciliation with the FROZEN R411 artifacts.
  2. The EMISSION GUARD: build_run_record refuses to emit when the
     funnel arithmetic is inconsistent (adversarial mutations must
     raise, not produce records).
  3. The ENGINEERING-GATED denominator: the report builder counts
     unique ids, and the waterfall explains the frozen R411 '28'.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from discovery_fabric.r411.report import (
    _assert_funnel_arithmetic, build_run_record,
)

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "R411" / "DISCOVERY_RUN"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"
FROZEN_RUN = REPO / "R411" / "R411_DISCOVERY_RUN.json"

TAXONOMY = ["problem_premise", "evidence", "mechanism", "prior_art",
            "physics", "baseline", "engineering", "attack", "other"]

REQUIRED_DEATH_FIELDS = (
    "candidate_id", "operator", "domain", "death_stage", "death_reason",
    "evidence_ids", "attacker_basis",
)


def _waterfall():
    return json.loads(WATERFALL.read_text())


def _frozen_state():
    return json.loads((RUN / "STATE.json").read_text())


# ---------------------------------------------------------------------------
# 1. The waterfall itself
# ---------------------------------------------------------------------------

class TestWaterfallCompleteness:
    def test_file_exists_and_declares_itself(self):
        w = _waterfall()
        assert w["artifact_type"] == "R412_DEATH_CAUSE_WATERFALL"
        assert w["subject_run"] == "r411:1788584836"
        assert w["reviewer_provenance"] == "AI_REVIEW"  # Art. LXVII

    def test_all_14_deaths_with_required_fields(self):
        w = _waterfall()
        deaths = w["deaths"]
        assert len(deaths) == 14
        for d in deaths:
            for f in REQUIRED_DEATH_FIELDS:
                assert d.get(f) is not None, (
                    f"{d.get('candidate_id')} missing {f}")
            assert d["death_cause"] in TAXONOMY
            assert d["operator"] in ("DIRECT_TRANSFER",
                                     "CROSS_DOMAIN_ANALOGY")
            assert d["death_reason"], "death_reason must be substantive"
            assert d["attacker_basis"], "attacker_basis must be verbatim"
            assert d["classification_source"], (
                "every classification carries its source")

    def test_death_ids_match_the_frozen_attacked_set(self):
        w = _waterfall()
        state = _frozen_state()
        assert sorted(d["candidate_id"] for d in w["deaths"]) == \
            sorted(set(state["attack_done"]))

    def test_distribution_sums_to_deaths(self):
        w = _waterfall()
        dist = w["death_cause_distribution"]
        assert set(dist) == set(TAXONOMY)
        assert sum(dist.values()) == w["n_deaths"] == 14
        assert w["distribution_sums_to_deaths"] is True

    def test_every_cause_class_used_or_zeroed(self):
        """Distribution keys are exactly the taxonomy — no invented
        classes, no dropped classes (the zero-count causes are
        explicitly enumerated and noted)."""
        w = _waterfall()
        zero = {k for k, v in w["death_cause_distribution"].items()
                if v == 0}
        assert zero == set(w["zero_count_causes"])

    def test_operators_recorded_not_retrofitted(self):
        """The operator field maps the FROZEN extraction record's own
        fields (pain_class + cross_domain_transition) onto the
        five-operator taxonomy — the mapping rule is disclosed per
        entry, never silently invented."""
        w = _waterfall()
        shortlist = {c["candidate_id"]: c for c in json.loads(
            (RUN / "shortlist.json").read_text())}
        for d in w["deaths"]:
            c = shortlist[d["candidate_id"]]
            xdom = (c.get("cross_domain_transition") or "NONE")
            expected = ("CROSS_DOMAIN_ANALOGY"
                        if xdom.strip().upper() != "NONE"
                        else "DIRECT_TRANSFER")
            assert d["operator"] == expected
            assert d["operator_basis"]["r411_generation_call"] == \
                c.get("pain_class")


class TestWaterfallFunnelReconciliation:
    def test_identity_reconciles_with_frozen_artifacts(self):
        """raw - medical - collision - dedup_merged == survivors, from
        the FROZEN funnel_collision.json (not from the waterfall's own
        restatement)."""
        w = _waterfall()
        funnel = json.loads((RUN / "funnel_collision.json").read_text())
        raw = funnel["raw_accepted_from_extraction"]
        med = funnel["medical_excluded_count"]
        col = funnel["collision_rejected_count"]
        merged = len(funnel["dedup"].get("merge_events") or [])
        assert raw - med - col - merged == funnel["survivor_count"]
        rec = w["funnel_reconciliation"]
        assert rec["raw_accepted_from_extraction"] == raw
        assert rec["candidate_survivors"] == funnel["survivor_count"]

    def test_deaths_equal_frozen_killed_verdicts(self):
        w = _waterfall()
        run = json.loads(FROZEN_RUN.read_text())
        killed = [cid for cid, v in
                  run["attacker_results"]["verdicts"].items()
                  if v == "KILLED"]
        assert len(w["deaths"]) == len(killed) == 14

    def test_selected_is_zero(self):
        w = _waterfall()
        assert w["funnel_reconciliation"]["selected"] == 0
        assert w["funnel_arithmetic_verified"]["selected_eq_zero"]

    def test_all_arithmetic_booleans_true(self):
        w = _waterfall()
        assert all(w["funnel_arithmetic_verified"].values())

    def test_engineering_28_explained_with_measurement(self):
        """The unexplained 'engineering-gated = 28' is closed: the
        waterfall records the measured structure (28 list entries, 14
        unique ids, 2 append sites) and the frozen R411 state is the
        evidence."""
        w = _waterfall()
        state = _frozen_state()
        eng = state["engineering_done"]
        rec = w["funnel_reconciliation"]
        assert rec["engineering_gated_as_recorded"] == len(eng) == 28
        assert rec["engineering_gated_unique"] == len(set(eng)) == 14
        assert rec["engineering_gated_28_explanation"]
        assert w["funnel_arithmetic_verified"][
            "engineering_unique_eq_shortlist"]


# ---------------------------------------------------------------------------
# 2. The emission guard — inconsistent arithmetic cannot be emitted
# ---------------------------------------------------------------------------

class TestFunnelArithmeticGuard:
    def _collision(self, **over):
        base = {
            "raw_accepted_from_extraction": 550,
            "medical_excluded_count": 8,
            "collision_rejected_count": 142,
            "survivor_count": 400,
            "dedup": {"merge_events": [], "indeterminate_pairs": []},
        }
        base.update(over)
        return base

    def test_valid_funnel_passes(self):
        _assert_funnel_arithmetic(self._collision(), 267,
                                  ["a", "b", "a", "b"])

    def test_broken_survivors_raise(self):
        with pytest.raises(ValueError, match="does not reconcile"):
            _assert_funnel_arithmetic(
                self._collision(survivor_count=399), 267, [])

    def test_broken_rejections_raise(self):
        # 550 - 8 - 143 - 0 != 400
        with pytest.raises(ValueError, match="does not reconcile"):
            _assert_funnel_arithmetic(
                self._collision(collision_rejected_count=143), 267, [])

    def test_non_integer_funnel_raises(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            _assert_funnel_arithmetic(
                self._collision(raw_accepted_from_extraction="550"), 0, [])

    def test_missing_funnel_raises(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            _assert_funnel_arithmetic({}, 0, [])

    def test_dedup_merged_is_a_subtraction_term(self):
        # 550 - 8 - 142 - 1 != 400 — merged candidates MUST be removed
        with pytest.raises(ValueError, match="does not reconcile"):
            _assert_funnel_arithmetic(
                self._collision(
                    dedup={"merge_events": [{"x": 1}],
                           "indeterminate_pairs": []}), 267, [])

    def test_engineering_appends_beyond_two_sites_raise(self):
        # 3x appends would mean an unknown third append site — refuse
        with pytest.raises(ValueError, match="more than 2x"):
            _assert_funnel_arithmetic(
                self._collision(), 0, ["a", "a", "a", "b", "b", "b"])

    def _record_ctx(self, run_dir):
        return SimpleNamespace(run_dir=str(run_dir), state={})

    def test_build_run_record_raises_on_inconsistent_state(self, tmp_path):
        """The emission-side guard: a run directory whose funnel does
        not reconcile produces a RAISED ValueError, never a JSON record
        with inconsistent arithmetic."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "funnel_collision.json").write_text(json.dumps({
            "raw_accepted_from_extraction": 100,
            "medical_excluded_count": 5,
            "collision_rejected_count": 10,
            "survivor_count": 85,  # 100-5-10 = 85 == OK... break it:
            "dedup": {"merge_events": [{"m": 1}],
                      "indeterminate_pairs": []},
        }))  # 100-5-10-1 = 84 != 85 -> guard must fire
        with pytest.raises(ValueError, match="does not reconcile"):
            build_run_record(self._record_ctx(run_dir))

    def test_build_run_record_raises_on_double_count_beyond_two_sites(
            self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "funnel_collision.json").write_text(json.dumps({
            "raw_accepted_from_extraction": 100,
            "medical_excluded_count": 5,
            "collision_rejected_count": 10,
            "survivor_count": 85,
            "dedup": {"merge_events": [], "indeterminate_pairs": []},
        }))
        ctx = SimpleNamespace(
            run_dir=str(run_dir),
            state={"engineering_done": ["x", "x", "x"]},
        )
        with pytest.raises(ValueError, match="more than 2x"):
            build_run_record(ctx)

    def test_build_run_record_emits_unique_engineering_count(
            self, tmp_path):
        """The R411 double-count class can never recur: with the
        state's two append sites populated, the emitted record reports
        the UNIQUE id count and discloses the append sites."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "funnel_collision.json").write_text(json.dumps({
            "raw_accepted_from_extraction": 100,
            "medical_excluded_count": 5,
            "collision_rejected_count": 10,
            "survivor_count": 85,
            "dedup": {"merge_events": [], "indeterminate_pairs": []},
        }))
        (run_dir / "domain_matrix.json").write_text(json.dumps(
            {"n_domains": 0, "entries": []}))
        (run_dir / "shortlist.json").write_text("[]")
        (run_dir / "selection.json").write_text(json.dumps(
            {"selected": [], "rejected": []}))
        (run_dir / "attack_calibration.json").write_text(json.dumps(
            {"n_defects": 0, "n_killed_as_expected": 0}))
        cids = ["c1", "c2"]
        ctx = SimpleNamespace(
            run_dir=str(run_dir),
            state={"engineering_done": cids + cids,
                   "attack_done": [], "prior_art_done": [],
                   "extraction_done": [], "retrieval_done": [],
                   "shortlist_ids": [], "selected_ids": [],
                   "evidence_subset_ids": [], "buyer_manifest": []},
        )
        record = build_run_record(ctx)
        eng = record["engineering_results"]
        assert eng["n_gated"] == 2  # unique ids, NOT 4 appends
        assert eng["n_gated_append_sites"] == 2
        assert record["candidate_rejections"]["funnel_reconciliation"] == \
            "survivors = raw(100) - medical_excluded(5) - " \
            "collision_rejected(10) - dedup_merged(0) = 85"

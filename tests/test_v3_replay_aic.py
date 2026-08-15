#!/usr/bin/env python3
"""
Machine tests for V3 Replay AIC Candidate extraction.

Tests:
  - per-arm count reconciliation (M0=60, M1=67, M2=57, M3=54, M4=64, M4B=58, M4C=56)
  - 100 candidates per arm (AIC + NON_AIC = 100)
  - no duplicate problem_id within arm
  - every replay candidate has proposed_modification
  - every replay candidate has evidence
  - every replay candidate has provenance
  - original V3 artifacts unchanged (root hash preserved)
"""
import json, os, sys, hashlib, pytest
from pathlib import Path
from collections import Counter

REPO = Path(__file__).parent.parent
EDIR = REPO / "experiments"
REPLAY_CANDIDATES_DIR = EDIR / "replay_candidates"
TDIR = REPO / "tournament_v3"

ARMS = ["M0", "M1", "M2", "M3", "M4", "M4B", "M4C"]
EXPECTED_COUNTS = {"M0": 60, "M1": 67, "M2": 57, "M3": 54, "M4": 64, "M4B": 58, "M4C": 56}

# V3 historical root hash (must not change)
V3_HISTORICAL_ROOT_HASH = "4d10e01c5c246133"


def load_main_manifest():
    with open(EDIR / "V3_REPLAY_AIC_CANDIDATES.json") as f:
        return json.load(f)

def load_arm_split(arm, aic_or_non):
    path = REPLAY_CANDIDATES_DIR / f"{arm}_REPLAY_{aic_or_non}.json"
    with open(path) as f:
        return json.load(f)


class TestCountReconciliation:
    """Per-arm count reconciliation against expected values."""

    def test_all_counts_match(self):
        manifest = load_main_manifest()
        assert manifest["all_counts_match"] is True

    def test_per_arm_counts(self):
        manifest = load_main_manifest()
        for arm in ARMS:
            c = manifest["counts_by_arm"][arm]
            assert c["replay_aic"] == EXPECTED_COUNTS[arm], \
                f"{arm}: got {c['replay_aic']}, expected {EXPECTED_COUNTS[arm]}"
            assert c["count_matches"] is True

    def test_total_count(self):
        manifest = load_main_manifest()
        assert manifest["total_replay_aic"] == sum(EXPECTED_COUNTS.values())
        assert manifest["total_replay_aic"] == 416  # 60+67+57+54+64+58+56


class TestCandidateDenominator:
    """100 candidates per arm (AIC + NON_AIC = 100)."""

    def test_100_per_arm(self):
        for arm in ARMS:
            aic = load_arm_split(arm, "AIC")
            non_aic = load_arm_split(arm, "NON_AIC")
            total = aic["count"] + non_aic["count"]
            assert total == 100, f"{arm}: AIC={aic['count']} + NON_AIC={non_aic['count']} = {total}, expected 100"


class TestNoDuplicates:
    """No duplicate problem_id within arm."""

    def test_no_duplicate_pids(self):
        for arm in ARMS:
            aic = load_arm_split(arm, "AIC")
            non_aic = load_arm_split(arm, "NON_AIC")
            all_pids = [c["problem_id"] for c in aic["candidates"]] + \
                       [c["problem_id"] for c in non_aic["candidates"]]
            assert len(all_pids) == len(set(all_pids)), \
                f"{arm}: duplicate problem_ids found"


class TestCandidateCompleteness:
    """Every replay candidate has required fields."""

    REQUIRED_FIELDS = [
        "architecture_origin", "arm", "problem_id", "problem_hash",
        "device_class", "failure_mode", "documented_failure",
        "proposed_modification", "mechanistic_reasoning", "expected_effect",
        "why_different_from_baseline", "falsification_test",
        "source_ids", "source_hashes", "source_spans", "packet_hash",
        "transfer_level", "problem_evidence", "mechanism_evidence", "transfer_evidence",
        "original_prior_art_state", "corrected_prior_art_state",
        "original_adversarial_state", "corrected_adversarial_state",
        "original_adversarial_dimensions", "corrected_adversarial_dimensions",
        "original_aic_state", "replay_aic_state",
        "replay_corrections_applied",
        "provider", "model", "prompt_hash",
        "invention_type", "qualitative_analysis_facts",
        "disclaimer",
    ]

    def test_all_fields_present(self):
        manifest = load_main_manifest()
        for m in manifest["candidates"]:
            for field in self.REQUIRED_FIELDS:
                assert field in m, f"{m['problem_id']} ({m['arm']}): missing field '{field}'"

    def test_every_candidate_has_proposed_modification(self):
        manifest = load_main_manifest()
        for m in manifest["candidates"]:
            assert m["proposed_modification"], f"{m['problem_id']} ({m['arm']}): empty proposed_modification"

    def test_every_candidate_has_evidence(self):
        """Every candidate must have source_ids (evidence)."""
        manifest = load_main_manifest()
        for m in manifest["candidates"]:
            assert len(m["source_ids"]) > 0, f"{m['problem_id']} ({m['arm']}): no source_ids"

    def test_every_candidate_has_provenance(self):
        """Every candidate must have prompt_hash + response_hash + provider + model."""
        manifest = load_main_manifest()
        for m in manifest["candidates"]:
            assert m["prompt_hash"], f"{m['problem_id']} ({m['arm']}): missing prompt_hash"
            assert m["response_hash"], f"{m['problem_id']} ({m['arm']}): missing response_hash"
            assert m["provider"], f"{m['problem_id']} ({m['arm']}): missing provider"
            assert m["model"], f"{m['problem_id']} ({m['arm']}): missing model"


class TestReplayAICLabeling:
    """Replay AIC candidates must be labeled REPLAY_AIC_CANDIDATE, not AUTOMATED_INVENTION_CANDIDATE."""

    def test_no_automated_invention_candidate_label(self):
        manifest = load_main_manifest()
        for m in manifest["candidates"]:
            assert m["replay_aic_state"] != "AUTOMATED_INVENTION_CANDIDATE", \
                f"{m['problem_id']} ({m['arm']}): must not be labeled AUTOMATED_INVENTION_CANDIDATE"
            assert m["replay_aic_state"] in ("REPLAY_AIC_CANDIDATE", "NOT_REPLAY_AIC")

    def test_disclaimer_present(self):
        manifest = load_main_manifest()
        for m in manifest["candidates"]:
            assert "REPLAY_AIC_CANDIDATE" in m["disclaimer"]
            assert "not been independently re-evaluated" in m["disclaimer"]


class TestV3ArtifactsUnchanged:
    """Original V3 artifacts must be unchanged (root hash preserved)."""

    def test_v3_root_hash_preserved(self):
        """Recompute V3 root hash from tournament_v3/ and verify it matches historical."""
        all_hashes = []
        for arm in ARMS:
            path = TDIR / f"{arm}_progress.json"
            if not path.exists():
                continue
            with open(path) as f:
                results = json.load(f).get("results", [])
            for r in results:
                all_hashes.append(r.get("response_hash", r.get("status", "")))
        recomputed = hashlib.sha256(json.dumps(all_hashes).encode()).hexdigest()[:16]
        assert recomputed == V3_HISTORICAL_ROOT_HASH, \
            f"V3 root hash changed: {recomputed} != {V3_HISTORICAL_ROOT_HASH}"


class TestInventionType:
    """Every candidate has an invention type from the descriptive taxonomy."""

    VALID_TYPES = {
        "INCREMENTAL", "MODULAR_REDESIGN", "MATERIAL_SUBSTITUTION", "MECHANISM_TRANSFER",
        "ARCHITECTURAL_CHANGE", "CONTROL_STRATEGY", "ENERGY_ARCHITECTURE",
        "SENSING_ARCHITECTURE", "BIOLOGICAL_INTERFACE", "COATING", "OTHER",
    }

    def test_all_have_valid_type(self):
        manifest = load_main_manifest()
        for m in manifest["candidates"]:
            assert m["invention_type"] in self.VALID_TYPES, \
                f"{m['problem_id']} ({m['arm']}): invalid invention_type '{m['invention_type']}'"


class TestQualitativeFacts:
    """Every candidate has qualitative analysis facts (not numerical scores)."""

    REQUIRED_FACT_CATEGORIES = [
        "problem_severity", "mechanism_depth", "novelty_distance",
        "technical_leverage", "specificity", "validation_tractability", "regulatory_relevance",
    ]

    def test_all_fact_categories_present(self):
        manifest = load_main_manifest()
        for m in manifest["candidates"]:
            facts = m["qualitative_analysis_facts"]
            for cat in self.REQUIRED_FACT_CATEGORIES:
                assert cat in facts, f"{m['problem_id']} ({m['arm']}): missing fact category '{cat}'"

    def test_facts_are_descriptive_not_numerical(self):
        """Facts should be descriptive (strings, lists, booleans), not numerical scores."""
        manifest = load_main_manifest()
        for m in manifest["candidates"][:5]:  # sample first 5
            facts = m["qualitative_analysis_facts"]
            # Check that no fact category has a "score" field
            for cat, cat_facts in facts.items():
                assert "score" not in cat_facts, \
                    f"{m['problem_id']} ({m['arm']}): {cat} has numerical 'score' — should be descriptive facts only"


class TestSourceHashReconstruction:
    """Source hash reconstruction method must be recorded."""

    def test_method_recorded(self):
        manifest = load_main_manifest()
        assert manifest["source_hash_reconstruction_method"] == "PHASE_D_PACKET_JOIN"

    def test_per_candidate_reconstruction(self):
        manifest = load_main_manifest()
        for m in manifest["candidates"]:
            assert "source_hash_reconstruction" in m
            assert m["source_hash_reconstruction"]["source_hash_reconstruction_method"] == "PHASE_D_PACKET_JOIN"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

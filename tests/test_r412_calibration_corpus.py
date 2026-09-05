"""tests/test_r412_calibration_corpus.py — Phase 3 corpus seals.

Pins the sealed attacker-calibration corpus: structure, label balance,
domain spread, ground-truth completeness, and — critically — that the
corpus file hash equals the sealed manifest hash (any corpus mutation
breaks the seal; the measurement harness refuses to attack a mutated
corpus).
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CAL = REPO / "R412" / "CALIBRATION"
CORPUS = CAL / "r412_attacker_calibration_corpus.json"
SEAL = CAL / "r412_calibration_seal.json"

import hashlib


def _corpus():
    return json.loads(CORPUS.read_text())


def _seal():
    return json.loads(SEAL.read_text())


class TestCorpusSeal:
    def test_corpus_hash_matches_seal(self):
        """The seal pins the corpus bytes; a mutated corpus fails the
        seal (and the measurement harness preflight)."""
        sha = hashlib.sha256(CORPUS.read_bytes()).hexdigest()
        assert sha == _seal()["corpus_sha256"]

    def test_pre_registered_thresholds_are_recorded_not_tuned(self):
        s = _seal()
        tr = s["pre_registered_thresholds"]
        assert tr["coverage_min"] == 0.875
        assert tr["parse_completeness_min"] == 0.875
        assert tr["tpr_min"] == 0.75
        assert tr["fpr_max"] == 0.30
        assert "NONE" in tr["ensemble"]  # no majority-vote ensemble yet

    def test_labels_balanced_40_cases_24_domains(self):
        c = _corpus()
        assert c["n_cases"] == 40
        assert c["label_counts"] == {
            "KNOWN_GOOD": 10, "KNOWN_BAD": 10,
            "NEAR_MISS": 10, "PRIOR_ART_COLLISION": 10}
        assert c["n_domains"] >= 20  # materially different domains


class TestCorpusGroundTruth:
    def test_every_case_has_ground_truth_with_basis(self):
        c = _corpus()
        for case in c["cases"]:
            gt = case["ground_truth"]
            for f in ("label", "expected_final", "ground_truth_basis"):
                assert gt.get(f), (
                    f"{case['case_id']} missing ground-truth field {f}")
            assert len(gt["ground_truth_basis"]) > 100, (
                f"{case['case_id']} basis is not substantive")

    def test_expected_final_consistency(self):
        c = _corpus()
        for case in c["cases"]:
            gt = case["ground_truth"]
            if gt["label"] == "KNOWN_GOOD":
                assert gt["expected_final"] == "SURVIVED"
            else:
                assert gt["expected_final"] == "KILLED"
                assert gt.get("defect_class"), (
                    f"{case['case_id']} defect case needs a defect class")
                assert gt.get("expected_kill_surface"), (
                    f"{case['case_id']} defect case needs an expected "
                    "kill surface")

    def test_candidate_records_carry_the_protocol_fields(self):
        """Every case's candidate record carries the fields the R411
        attack protocol consumes — the corpus exercises the REAL
        attacker, not a simplified one."""
        c = _corpus()
        for case in c["cases"]:
            cand = case["candidate"]
            for f in ("technology_name", "problem", "causal_chain",
                      "unexploited_phenomenon", "intervention",
                      "predicted_effect", "equations",
                      "boundary_conditions", "evidence_refs", "baseline",
                      "killer_experiment"):
                assert cand.get(f), (
                    f"{case['case_id']} candidate missing {f}")
            assert (cand.get("killer_experiment") or {}).get(
                "kill_condition"), (
                f"{case['case_id']} killer experiment lacks a kill "
                "condition (Art. LII)")

    def test_pools_and_prior_art_present(self):
        c = _corpus()
        for case in c["cases"]:
            assert case.get("pool"), f"{case['case_id']} has no pool"
            refs = {r["record_id"] for r in case["pool"]}
            for rid in case["candidate"]["evidence_refs"]:
                assert rid in refs, (
                    f"{case['case_id']}: evidence ref {rid} unbound — "
                    "the attacker would see '(no evidence records bound)'")
            pa = case.get("prior_art") or {}
            assert pa.get("relevant_records"), (
                f"{case['case_id']} has no prior-art records")

    def test_known_good_prior_art_is_related_not_colliding(self):
        """The instrument's design invariant: KNOWN_GOOD cases carry
        related-but-different prior art (titles must differ from the
        intervention), while PRIOR_ART_COLLISION titles teach the same
        mechanism+intervention+effect."""
        c = _corpus()
        for case in c["cases"]:
            if case["ground_truth"]["label"] != "KNOWN_GOOD":
                continue
            intervention = case["candidate"]["intervention"].lower()
            for r in case["prior_art"]["relevant_records"]:
                title = r["title"].lower()
                # related art describes a DIFFERENT application,
                # carrier, or mechanism — the parentheticals in the
                # corpus say so explicitly
                assert "(" in r["title"], (
                    f"{case['case_id']} known-good prior art must state "
                    "the related-but-different basis in the title")

    def test_no_duplicate_case_ids(self):
        ids = [x["case_id"] for x in _corpus()["cases"]]
        assert len(ids) == len(set(ids)) == 40

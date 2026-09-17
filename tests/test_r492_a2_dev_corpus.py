"""R492 — the A2 DEV calibration corpus freeze tests.

The R492 operator directive: "min-path 6 — the A2 DEV corpus, frozen
before any tuning". These tests pin:

  1. the corpus exists and its FREEZE.json corpus_sha256 matches the
     file (reconstructed the same way the builder wrote it: corpus body
     without the corpus_sha256 key, indent=2, trailing newline);
  2. every case's per-case sha256 matches;
  3. the corpus contract holds ON THE WRITTEN FILE (schema, category
     counts, Art. L ten-class coverage, prior-art-state vocabulary,
     expected-kill-surface vocabulary, ground-truth coherence);
  4. the corpus is DISJOINT from the sealed corpora (R446 sealed corpus,
     R412 calibration corpus): no shared case/candidate identifiers and
     no candidate text appearing in either sealed corpus;
  5. the freeze record declares frozen_before_any_tuning and the corpus
     role is DEV (Art. LIX discipline).
"""
import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json"
FREEZE = REPO / "R492" / "A2_DEV_CORPUS" / "FREEZE.json"
SEALED_R446 = REPO / "R446" / "ATTACKER_CALIBRATION" / "CORPUS.json"
SEALED_R412 = REPO / "R412" / "CALIBRATION" / \
    "r412_attacker_calibration_corpus.json"

A2_DIMENSIONS = {
    "unsupported_mechanism", "weak_transfer", "obvious_combination",
    "prior_art", "contradiction", "boundary_failure",
    "engineering_infeasibility", "regulatory_incompatibility",
}
VALID_PA_STATES = {
    "NO_MATCH_FOUND", "TOPICAL_RELATED", "POSSIBLE_RELEVANCE",
    "UNRESOLVED_INSUFFICIENT_EVIDENCE", "SPECIFIC_DISCLOSURE",
    "IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE",
}
ART_L_CLASSES = {
    "CAUSAL_INVALIDITY", "BOUNDARY_CONDITION_FAILURE",
    "EVIDENCE_CONTRADICTION", "BASELINE_EQUIVALENCE",
    "IMPLEMENTATION_IMPOSSIBILITY", "MANUFACTURING_FAILURE",
    "MEASUREMENT_AMBIGUITY", "SCALING_FAILURE", "SAFETY_FAILURE",
    "HIDDEN_DEPENDENCY",
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _reconstruct_body_sha(corpus: dict) -> str:
    body = {k: v for k, v in corpus.items() if k != "corpus_sha256"}
    blob = json.dumps(body, indent=2, ensure_ascii=False) + "\n"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def corpus():
    return _load(CORPUS)


@pytest.fixture(scope="module")
def freeze():
    return _load(FREEZE)


def test_files_exist():
    assert CORPUS.exists(), "the frozen corpus is missing"
    assert FREEZE.exists(), "the freeze record is missing"


def test_freeze_hash_matches_file(corpus, freeze):
    assert corpus["corpus_sha256"] == freeze["corpus_sha256"]
    assert _reconstruct_body_sha(corpus) == corpus["corpus_sha256"]


def test_per_case_hashes_match(corpus):
    for case in corpus["cases"]:
        cid = case["case_id"]
        body = json.dumps(case, sort_keys=True, ensure_ascii=False)
        assert hashlib.sha256(body.encode("utf-8")).hexdigest() == \
            corpus["per_case_sha256"][cid], f"case hash drift: {cid}"


def test_category_counts_match_header(corpus):
    counts: dict[str, int] = {}
    for case in corpus["cases"]:
        counts[case["category"]] = counts.get(case["category"], 0) + 1
    assert counts == corpus["category_counts"]
    assert corpus["n_cases"] == len(corpus["cases"]) == 21
    assert corpus["category_counts"]["TRUE_NEGATIVE_clean_control"] == 4
    assert corpus["category_counts"]["TRUE_POSITIVE_seeded_defect"] == 10


def test_art_l_ten_class_coverage(corpus):
    seed_classes = {c["seed_class"] for c in corpus["cases"]}
    missing = ART_L_CLASSES - seed_classes
    assert not missing, f"Art. L class coverage incomplete: {missing}"
    header_flags = corpus["art_l_class_coverage"]
    assert all(header_flags.values()), \
        f"header coverage flag contradicts cases: {header_flags}"


def test_ground_truth_vocabulary_and_coherence(corpus):
    for case in corpus["cases"]:
        gt = case["ground_truth"]
        assert gt["prior_art_state"] in VALID_PA_STATES, case["case_id"]
        surf = gt["expected_kill_surface"]
        if surf is not None:
            assert surf in A2_DIMENSIONS, case["case_id"]
        if gt["label"] == "KNOWN_BAD":
            assert gt["expected_final"] == "KILLED", case["case_id"]
            assert surf is not None, case["case_id"]
            assert gt["defect_class"], case["case_id"]
        else:
            assert gt["expected_final"] == "PASSED", case["case_id"]
            assert surf is None, case["case_id"]
        assert gt["ground_truth_basis"], case["case_id"]


def test_controls_coherent(corpus):
    for case in corpus["cases"]:
        is_tn = case["category"] == "TRUE_NEGATIVE_clean_control"
        assert case["control"] == is_tn, case["case_id"]


def test_disjoint_from_sealed_corpora(corpus):
    r446 = _load(SEALED_R446)
    r412 = _load(SEALED_R412)
    sealed_ids = set()
    sealed_text = []
    for src in (r446, r412):
        for case in src.get("cases", []):
            sealed_ids.add(case.get("case_id"))
            cand = case.get("candidate") or {}
            sealed_ids.add(cand.get("candidate_id"))
            sealed_text.append(str(cand.get("mechanism", "")).lower())
            sealed_text.append(str(cand.get("intervention", "")).lower())
    sealed_blob = " || ".join(t for t in sealed_text if t)
    for case in corpus["cases"]:
        cid = case["case_id"]
        assert cid not in sealed_ids, f"case_id collides: {cid}"
        cand = case["candidate"]
        assert cand["candidate_id"] not in sealed_ids, \
            f"candidate_id collides: {cid}"
        mech = cand["mechanism"].lower()
        assert mech not in sealed_blob, \
            f"mechanism text duplicated in sealed corpora: {cid}"
        # distinctive-token check: the case's candidate_id prefix must
        # not appear in the sealed corpora at all
        assert "a2dev-" not in sealed_blob


def test_freeze_declares_dev_role_and_pre_tuning_freeze(freeze, corpus):
    assert freeze["artifact_type"] == "A2_DEV_CORPUS_FREEZE"
    assert freeze["frozen_before_any_tuning"] is True
    assert corpus["frozen_before_any_tuning"] is True
    assert "DEVELOPMENT corpus" in corpus["role"]
    # thresholds reused, not invented (Art. XXVII)
    thr = corpus["pre_registered_thresholds"]
    assert thr["tpr_min"] == 0.75
    assert thr["fpr_max"] == 0.30
    assert thr["coverage_min"] == 0.875
    assert thr["parse_completeness_min"] == 0.875
    assert "REUSED verbatim from the R412 sealed bars" in thr["provenance"]

#!/usr/bin/env python3
"""Build and SEAL the R412 attacker-calibration corpus.

Emits R412/CALIBRATION/r412_attacker_calibration_corpus.json from the
four independently-authored quadrant modules. Sealing: the corpus file
is committed BEFORE any attacker run (the ground truth exists first,
Art. VIII); the manifest records the corpus content hash so the
measurement run can prove it attacked the sealed corpus, not a mutated
one.

Pre-registered calibration thresholds (CEO R412 Phase 3 directive:
'Do not call the attacker calibrated until it is measured' — these
thresholds are registered BEFORE the measurement and are NOT tuned to
the results; Art. XXVII):
  CALIBRATED iff:
    coverage            >= 0.875  (>= 35/40 cases complete)
    parse_completeness  >= 0.875
    TPR                 >= 0.75   (kills on the 30 defect cases)
    FPR (false-kill rate on the 10 KNOWN_GOOD) <= 0.30
  otherwise NOT_CALIBRATED (recorded as a measurement, never tuned).
  NO majority-vote ensemble is introduced at this stage (single-attacker
  calibration is the question; ensemble deferred by directive).
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "R412" / "CALIBRATION"))

from corpus_known_good import KG_CASES  # noqa: E402
from corpus_known_bad import KB_CASES  # noqa: E402
from corpus_near_miss import NM_CASES  # noqa: E402
from corpus_prior_art_collision import PA_CASES  # noqa: E402


def main() -> int:
    cases = KG_CASES + KB_CASES + NM_CASES + PA_CASES
    assert len(KG_CASES) >= 10 and len(KB_CASES) >= 10
    assert len(NM_CASES) >= 10 and len(PA_CASES) >= 10

    # sanity: unique case ids, unique domains spread, labels as designed
    ids = [c["case_id"] for c in cases]
    assert len(ids) == len(set(ids)) == 40
    domains = sorted({c["domain_id"] for c in cases})
    labels = [c["ground_truth"]["label"] for c in cases]
    assert labels.count("KNOWN_GOOD") == 10
    assert labels.count("KNOWN_BAD") == 10
    assert labels.count("NEAR_MISS") == 10
    assert labels.count("PRIOR_ART_COLLISION") == 10
    for c in cases:
        gt = c["ground_truth"]
        for f in ("label", "expected_final", "ground_truth_basis"):
            assert gt.get(f), f"{c['case_id']} ground truth missing {f}"
        # expected verdict consistency
        if gt["label"] == "KNOWN_GOOD":
            assert gt["expected_final"] == "SURVIVED"
        else:
            assert gt["expected_final"] == "KILLED"

    corpus = {
        "artifact_type": "R412_ATTACKER_CALIBRATION_CORPUS",
        "corpus_id": "r412-attacker-calibration-v1",
        "created_in": "R412",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_provenance": "AI_REVIEW",
        "authorship_independence": (
            "authored from established physics/engineering knowledge, "
            "independently of the attacker's behavior (Art. VIII: no "
            "certification corpus may be generated from the verifier's "
            "own behavior). Ground truth (label, expected verdict, "
            "defect class, basis) is recorded per case BEFORE any "
            "attacker run; the committing hash seals the corpus."),
        "instrument_semantics": {
            "KNOWN_GOOD": (
                "given the case's inputs (candidate record, evidence "
                "pool, provided prior-art set), a calibrated attacker "
                "must NOT kill; the provided prior art is related but "
                "non-colliding by construction"),
            "KNOWN_BAD": (
                "carries a genuine defect from the Art. L minimum "
                "classes; a calibrated attacker must KILL"),
            "NEAR_MISS": (
                "real mechanism with ONE specific defect (magnitude, "
                "regime, baseline inversion, service mismatch); a "
                "calibrated attacker must KILL for that defect — these "
                "are the discrimination tests"),
            "PRIOR_ART_COLLISION": (
                "the provided prior-art set teaches the same mechanism"
                "+intervention+effect; a calibrated attacker must KILL "
                "on prior_art citing the teaching record"),
        },
        "pre_registered_thresholds": {
            "note": "registered BEFORE measurement; never tuned to "
                    "results (Art. XXVII)",
            "coverage_min": 0.875,
            "parse_completeness_min": 0.875,
            "tpr_min": 0.75,
            "fpr_max": 0.30,
            "ensemble": "NONE (single-attacker calibration only; "
                        "majority-vote ensembles are deferred by the "
                        "R412 directive)",
        },
        "n_cases": len(cases),
        "n_domains": len(domains),
        "domains": domains,
        "label_counts": {
            "KNOWN_GOOD": 10, "KNOWN_BAD": 10,
            "NEAR_MISS": 10, "PRIOR_ART_COLLISION": 10,
        },
        "cases": cases,
    }

    out = HERE / "R412" / "CALIBRATION" / \
        "r412_attacker_calibration_corpus.json"
    out.write_text(json.dumps(corpus, indent=1))
    corpus_sha = hashlib.sha256(out.read_bytes()).hexdigest()

    manifest = {
        "artifact_type": "R412_CALIBRATION_CORPUS_SEAL",
        "corpus_id": corpus["corpus_id"],
        "corpus_path": "R412/CALIBRATION/r412_attacker_calibration_corpus.json",
        "corpus_sha256": corpus_sha,
        "n_cases": 40,
        "label_counts": corpus["label_counts"],
        "n_domains": len(domains),
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "sealing_rule": (
            "this manifest and the corpus are committed BEFORE any "
            "attacker run; the measurement must verify the corpus sha "
            "against this manifest before attacking (a mutated corpus "
            "fails the measurement harness preflight)"),
        "pre_registered_thresholds":
            corpus["pre_registered_thresholds"],
    }
    (HERE / "R412" / "CALIBRATION" /
     "r412_calibration_seal.json").write_text(json.dumps(manifest, indent=1))

    print(f"corpus written: {out}")
    print(f"corpus sha256: {corpus_sha}")
    print(f"cases: {len(cases)} across {len(domains)} domains")
    print("labels:", corpus["label_counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

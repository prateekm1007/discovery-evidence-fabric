#!/usr/bin/env python3
"""scripts/r494_ship_records.py — R494: ship the union 2.0.0's
measured-NOT_CALIBRATED records into the calibration registry's
pinned shipment (the R486/R487 discipline: a failing measurement
SHIPS — the state derives from real numbers, never from absence).

The operative record: the union's XKIRO measurement (the deployed
transport's ring — the production-representative path; R493/
A2_V4_UNION_XKIRO). The zai-gateway replication (R494/
A2_V4_CALIBRATION) rides the same commit as the cross-ring
disclosure. Both fail tpr_min; the registry entry derives
NOT_CALIBRATED, fail-closed — the consumption gate keeps escalating
(the ring-bound terminal authority stays off).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

XKIRO_RESULTS = REPO / "R493" / "A2_V4_UNION_XKIRO" / \
    "MEASUREMENT_RESULTS.json"
ZAI_RESULTS = REPO / "R494" / "A2_V4_CALIBRATION" / \
    "MEASUREMENT_RESULTS.json"
CORPUS_PATH = REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json"
SHIPPED = REPO / "discovery_fabric" / "engine" / "calibration_records"
MEAS_OUT = SHIPPED / "a2_gauntlet_v4_measurement.json"
SEAL_OUT = SHIPPED / "a2_gauntlet_v4_seal.json"
DIGESTS = SHIPPED / "DIGESTS.json"


def main() -> int:
    xkiro = json.loads(XKIRO_RESULTS.read_text())
    zai = json.loads(ZAI_RESULTS.read_text())
    corpus = json.loads(CORPUS_PATH.read_text())
    h_x, h_z = xkiro["headline"], zai["headline"]

    measurement = {
        "artifact_type": "A2_GAUNTLET_V4_MEASUREMENT",
        "instrument": "a2_adversarial_gauntlet/2.0.0",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_provenance": "AI_REVIEW",
        "operative_ring": "xkiro (the deployed transport's ring)",
        "corpus": {
            "path": "R492/A2_DEV_CORPUS/CORPUS.json",
            "corpus_id": corpus.get("corpus_id"),
            "sha256": corpus.get("corpus_sha256"),
            "frozen_unchanged": True,
            "n_cases": xkiro.get("n_cases"),
        },
        "attacker_ring": {
            "provider": "xkiro",
            "model": "qwen3.8-max (the served model id recorded on "
                     "every RAW record)",
            "ring_pin": "xkiro",
            "serving": "21 cases via POST /api/ops/a2-attack "
                       "(require_provider=xkiro), zero deviations",
            "pin_violations": [],
            "note": "the calibration is (rules x ring) — the gate "
                    "binds terminal kill authority to THIS ring at "
                    "consumption (R488/R491)",
        },
        "metrics": {
            "false_kill_rate_on_known_good": h_x["fpr_known_good"],
            "coverage": h_x["coverage_all_9_fields"],
            "parse_completeness": h_x["parse_completeness"],
            "tnr": h_x["tnr"],
        },
        "scoped_tpr_diagnostic": {
            "tpr": h_x["tpr_defect_cohorts"],
            "cohort": "defect cohorts (TRUE_POSITIVE_seeded_defect + "
                      "EVIDENCE_CONTRADICTED), marker-bound kills per "
                      "the corpus's scoring contract",
        },
        "n_cases_attacked": xkiro.get("n_measured"),
        "threshold_verdict": xkiro["threshold_verdict"],
        "measured_verdict_note": (
            "the union 2.0.0 (the three-verdict burden-of-proof rules) "
            "on the frozen R492 DEV corpus: the false-kill class is "
            "ELIMINATED (FPR 0.0 — was 1.0 on the untuned baseline, "
            "both rings) but detection collapsed (TPR 0.2727 xkiro / "
            "0.3636 zai vs the 0.75 bar): the LLM hedges derivable-"
            "but-uncomputed defects into RISK (the typed failure: the "
            "objections are correct and well-formed — the attacker-"
            "computes kill standard is the named v4.2 lever). The "
            "seal is REFUSED; the state derives NOT_CALIBRATED, "
            "fail-closed"),
        "cross_ring_replication": {
            "zai_gateway": {
                "tpr": h_z["tpr_defect_cohorts"],
                "fpr": h_z["fpr_known_good"],
                "coverage": h_z["coverage_all_9_fields"],
                "parse": h_z["parse_completeness"],
                "record": "R494/A2_V4_CALIBRATION/MEASUREMENT_RESULTS.json",
            },
            "note": ("the same instrument measured on both rings: "
                     "FPR 0.0 ring-independent; TPR ring-dependent "
                     "(0.27 xkiro / 0.36 zai — both far below the "
                     "bar); the (rules x ring) lesson extends to the "
                     "vocabulary temperament"),
        },
        "measurement_history": {
            "untuned_1_0_0": {
                "tpr": 0.0909, "fpr": 1.0,
                "rings": "xkiro (R493/A2_BASELINE) + zai (R493/"
                         "A2_BASELINE_ZAI_GATEWAY) — the before-number "
                         "is RING-INDEPENDENT",
            },
            "sibling_v4_1_1_0_line": {
                "tpr": 0.6364, "fpr": 0.0,
                "record": "R493/A2_V4_MEASUREMENT (their binary-"
                          "vocabulary line; SEAL REFUSED by their "
                          "round record)",
            },
            "union_2_0_0": "this record",
        },
        "per_case": xkiro.get("per_case"),
    }
    MEAS_OUT.write_text(json.dumps(measurement, indent=1, default=str))

    seal = {
        "artifact_type": "A2_GAUNTLET_V4_SEAL",
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "instrument": "a2_adversarial_gauntlet/2.0.0",
        "corpus_id": corpus.get("corpus_id"),
        "corpus_sha256": corpus.get("corpus_sha256"),
        "pre_registered_thresholds": corpus["pre_registered_thresholds"],
        "threshold_provenance": (
            "copied VERBATIM from the frozen corpus's own "
            "pre_registered_thresholds (R492/A2_DEV_CORPUS/"
            "CORPUS.json — the R412 sealed bars REUSED per Art. "
            "XXVII); the thresholds predate every tuning iteration "
            "(frozen 2026-09-17 before any A2 measurement ran)"),
        "sealing_discipline": (
            "Art. LIX: the DEV corpus is the tuning surface (the "
            "sealed corpora were never touched); the seal is REFUSED "
            "— the operative measurement fails tpr_min (0.2727 < "
            "0.75); the registry entry derives NOT_CALIBRATED and "
            "the consumption gate keeps escalating; the shipped "
            "record makes the state MEASURED-honest (the R487 "
            "precedent: a failing measurement ships; the state "
            "derives from real numbers, never from absence)"),
        "reviewer_provenance": "AI_REVIEW",
    }
    SEAL_OUT.write_text(json.dumps(seal, indent=1))

    digests = json.loads(DIGESTS.read_text())
    digests.setdefault("sha256", {})[MEAS_OUT.name] = \
        hashlib.sha256(MEAS_OUT.read_bytes()).hexdigest()
    digests["sha256"][SEAL_OUT.name] = \
        hashlib.sha256(SEAL_OUT.read_bytes()).hexdigest()
    digests["r494_extension"] = {
        "purpose": ("the union 2.0.0's measured-NOT_CALIBRATED records "
                    "(the seal refused; the state derived from real "
                    "numbers — the R487 failing-measurement precedent)"),
        "operative_ring": "xkiro",
        "cross_ring": "zai (R494/A2_V4_CALIBRATION)",
    }
    DIGESTS.write_text(json.dumps(digests, indent=1))
    print(f"shipped: {MEAS_OUT.name} + {SEAL_OUT.name} (digests pinned)")

    # verify the derived state
    from discovery_fabric.engine import attacker_calibration as gate
    st = gate.resolve_state(instrument_version="a2_adversarial_gauntlet/2.0.0")
    print("derived state:", st["state"],
          "| terminal_kill_admissible:", st["terminal_kill_admissible"])
    print("measured:", json.dumps(st.get("measured", {}), indent=1)[:300])
    assert st["state"] == "NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False
    print("FAIL-CLOSED VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

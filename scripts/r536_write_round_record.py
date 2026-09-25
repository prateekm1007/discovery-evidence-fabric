#!/usr/bin/env python3
"""R536 round record generator (the sealed round artifact).

R536 is the audit-directed cliff round: the auditor found a defect
in R532's own instrument that changes R535's conclusion.  Two
sequential one-cliff fixes:

  Cliff 1 — the R532 typed-outcome classifier's priority-order bug
  (cemetery_blocked read AFTER candidate_state, so every cemetery
  hard-block — which overwrites candidate_state to
  NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT — was mislabeled
  ASSEMBLY_INVALID).  Fixed observability-only in
  adapters._ms_attempt_outcome; the corrected R535 typed dropout
  table is reclassified from the durable bytes (no new live calls):
  4/5 NO_CANDIDATES rows are CEMETERY_BLOCK, 1 (problem 3) is a
  genuine still-unexplained assembly loss.

  Cliff 2 — the mechanism cemetery's PROVEN_INVARIANT hard-block
  fired on cross-domain generic physics vocabulary (CE-001's
  cardiovascular "state/measurement/condition" terms matching a
  hemodialysis catheter candidate — the audit's 80% quantification
  of R535's admission loss).  The domain-identity prerequisite now
  gates the hard-block on the entry's TERRITORY-SPECIFIC terms
  (never on generic process language), with recorded provenance
  (which signal fired, which specific terms matched).  Shipped in
  the same commit: the ensemble.py span_instruction KeyError crash
  repair (a latent crash on the path the cemetery fix makes
  reachable).

  Also delivered: R536 §3 dependency-contract proof (the 4-case x
  consumer matrix driven on the real conductor, 0 violations, the
  two-authority divergences documented not refactored) + R535 §12
  vehicle-count correction + §13 artifact-structure rule + §5 FREEZE
  observational instrumentation (admission semantics unchanged) +
  §4 corrected causal decomposition.

Classification: R536 closed the audit's two cliffs (measurement
repairs on the discovery instrument + one cliff fix), no new live
battery, no deployment this round — the corrected instrument is the
deliverable; the next round runs the blind battery on the fixed
engine to confirm the 4/8 cemetery false-positives no longer block
cross-domain candidates.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R536" / "R536_ROUND_RECORD.json"


def main() -> int:
    rec = {
        "artifact": "R536_ROUND_RECORD/1.0",
        "round": "R536",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "classification":
            "CLIFFS_CLOSED__CLASSIFIER_AND_CEMETERY_REPAIRED",
        "audit_driven": True,
        "audit_finding": (
            "the R532 typed-outcome instrument mislabeled every "
            "cemetery hard-block as ASSEMBLY_INVALID (the classifier "
            "read candidate_state before cemetery_blocked); "
            "reclassifying R535's own durable bytes, 4 of 5 "
            "NO_CANDIDATES rows are CEMETERY_BLOCK — the R535 "
            "'upstream causality not yet established' conclusion was "
            "built on a broken instrument"),
        "cliffs": [
            {
                "cliff": 1,
                "name": "R532 typed-outcome classifier priority bug",
                "fix": ("adapters._ms_attempt_outcome: the "
                        "cemetery_blocked check now precedes the "
                        "candidate_state check, independent of it "
                        "(observability-only: the engine's behavior "
                        "is unchanged, only the label is right)"),
                "regression": "tests/test_r536_classifier_priority.py",
                "corrected_evidence": (
                    "R536/R536_CORRECTED_TYPED_DROPOUT_TABLE.json "
                    "(read-only reclassification of the R535 "
                    "harvest; 4 CEMETERY_BLOCK / 1 ASSEMBLY_INVALID "
                    "/ 2 ACCEPTED / 1 SEMANTIC_REJECT)"),
            },
            {
                "cliff": 2,
                "name": "cemetery cross-domain false-positive hard-"
                        "block",
                "fix": ("orchestrator/mechanism_cemetery.py: the "
                        "PROVEN_INVARIANT hard-block now requires a "
                        "domain-identity prerequisite on the entry's "
                        "TERRITORY-SPECIFIC terms (the generic cross-"
                        "domain physics vocabulary never establishes "
                        "territory); two signals (structural same-"
                        "department graph overlap, lexical territory-"
                        "specific text match) each recorded on the "
                        "block; an entry with no territory-specific "
                        "vocabulary downgrades to a recorded WARNING "
                        "instead of a cross-domain kill"),
                "shipped_with": ("ensemble.py span_instruction "
                                 "KeyError crash repair (the latent "
                                 "crash on the path the cemetery fix "
                                 "makes reachable)"),
                "regression":
                    "tests/test_r536_cemetery_domain_identity.py",
            },
        ],
        "measurement_deliverables": [
            "R536/R536_DEPENDENCY_CONTRACT_PROOF.json (the §3 4-case "
            "x consumer matrix, 0 contract violations, the two-"
            "authority divergences documented)",
            "R536/R536_MECHANISM_SPACE_CAUSAL_DECOMPOSITION.json "
            "(the corrected §4 join: 4 CEMETERY_BLOCK / 1 "
            "ASSEMBLY_INVALID / 1 SEMANTIC_REJECT losses, all post-"
            "provider deterministic, 0 upstream)",
            "R536/R536_CORRECTED_TYPED_DROPOUT_TABLE.json "
            "(Cliff 1 reclassification of the R535 durable bytes)",
            "R535/R535_VEHICLE_COUNT_CORRECTION.json (§12 "
            "append-only: 6 reported / 5 actual scored, Nissan "
            "Altima raw-fetch-only)",
            "R536/R536_ARTIFACT_STRUCTURE_RULE.json (§13 "
            "historical/current namespace rule, machine-generated, "
            "no rewrite of the R526 harvest)",
        ],
        "instrumentation_deliverables": [
            "adapters.py EvidenceFreezeAdapter §5 observational "
            "custody fields (input/promoted/failed/hash-pass/hash-"
            "fail/final count/lineage; admission semantics "
            "unchanged)",
            "adapters.py A2RetrievalAdapter §7 retrieval_subphases "
            "observational span (fabric vs post-fabric-local; "
            "retrieved_count semantics unchanged)",
        ],
        "tests": "28 new + amended (test_r536_classifier_priority, "
                  "test_r536_cemetery_domain_identity) + the "
                  "R532/R535/R402 suites re-run green; the 5 "
                  "pre-existing R422/R453/R418 failures are "
                  "byte-identical to the R535 baseline (no new "
                  "failures introduced)",
        "next_authorized": (
            "a fresh blind battery on the fixed engine confirming "
            "the 4/8 cemetery false-positives no longer block cross-"
            "domain candidates (the §16 counterfactual), THEN the "
            "1/8 genuine assembly loss (problem 3) gets its own "
            "upstream RETRIEVE/FREEZE/VERIFY instrumentation "
            "round — the original R536 §4-§7 scope, deferred per "
            "the audit's one-cliff-at-a-time rule"),
        "optimization_authorized": False,
        "constitution_ref": ("Art. XXV (UNKNOWN first-class, never "
                             "a fabricated cause), Art. XXVII "
                             "(every blocking decision carries its "
                             "provenance), Art. XI (corrections "
                             "append-only, sealed records never "
                             "rewritten), Art. XVII/XVIII (the "
                             "attack that found the bug is the test "
                             "that holds the fix), Art. LXXXIII "
                             "(one cliff at a time)"),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

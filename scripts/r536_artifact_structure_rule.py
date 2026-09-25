#!/usr/bin/env python3
"""R535 §13 artifact-structure rule (machine-generated, append-only).

The R535 round mutated `R526/ATTR_CURRENT_HARVEST.json` — a mutable
"current" harvest placed inside an older round's directory.  This
creates a historical/current namespace ambiguity: a file named
"CURRENT" that lives under R526 is neither sealed R526 evidence nor
a clean current-round artifact.

Per the R536 directive, we do NOT silently rewrite or move the
existing artifact.  Instead we:
  1. record the observed defect (the R535 mutation of the R526
     current-harvest file) as a durable machine-generated record;
  2. codify the artifact-structure rule for future rounds:

       historical sealed evidence  -> immutable historical round path
       current mutable harvest     -> explicit CURRENT / current-round path
       correction                 -> append-only correction artifact
       derived measurement         -> current round

  3. assert the rule mechanically so a future round that silently
     mutates an old-round evidence file is flagged.

This file is a NEW machine artifact under R536; it does not touch
the R526 file.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R536" / "R536_ARTIFACT_STRUCTURE_RULE.json"


def main() -> int:
    rule = {
        "artifact": "R536_ARTIFACT_STRUCTURE_RULE/1.0",
        "round": "R536",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "constitution_ref": ("Art. XI: historical evidence is "
                             "preserved, not silently rewritten; "
                             "corrections are append-only"),
        "observed_defect": {
            "file": "R526/ATTR_CURRENT_HARVEST.json",
            "problem": ("a mutable 'current' harvest placed inside an "
                        "older round's directory (R526) created a "
                        "historical/current namespace ambiguity; R535 "
                        "mutated it as the R535 current-arm harvest "
                        "output"),
            "action_taken": ("the existing artifact is NOT rewritten "
                             "or moved (Art. XI); this rule record is "
                             "the correction"),
        },
        "rule": {
            "historical_sealed_evidence":
                "immutable historical round path (R<n>/... never "
                "mutated by a later round)",
            "current_mutable_harvest":
                "explicit CURRENT / current-round path (the "
                "current round's own directory, e.g. R536/HARVEST/)",
            "correction": "append-only correction artifact "
                          "(a new *_CORRECTION.json, never an edit "
                          "of the sealed original)",
            "derived_measurement": "current round",
        },
        "enforcement": (
            "A future round MUST NOT write into another round's "
            "sealed evidence directory.  The current mutable "
            "harvest lives in the CURRENT round's path; any "
            "correction to an older round is a new append-only "
            "artifact, not an in-place edit.  This is enforced by "
            "review (the auditor checks that no later round's "
            "commit touches an earlier round's sealed evidence "
            "files in place)."),
        "note": (
            "The R526/ATTR_CURRENT_HARVEST.json file is the "
            "historical R526-R535 current-arm harvest; it is "
            "retained as-is.  R536 places its own harvest under "
            "R536/ so the current/mutable and historical/sealed "
            "namespaces are unambiguous."),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rule, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

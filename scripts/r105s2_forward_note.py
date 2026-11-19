#!/usr/bin/env python3
"""Append the r105s2 forward note to eval/r105s1_status.json — the
auditor R105 verdict D6 item: quote the final-tip 747e2fa1 CI (the
API-quoted check-run) in the r105 status forward note.

Art. 4 typed in-place correction (the dacffd034 verifier-remediates
precedent): the r105s1 status is the EXECUTOR's record; the forward
note is appended as a NEW key (nothing existing is rewritten), with
the correction disclosed here and in the round record.
"""
import json
import sys
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
PATH = REPO / "eval" / "r105s1_status.json"


def main(ci_747: dict, ci_tip: dict):
    d = json.loads(PATH.read_text())
    assert "forward_note_r105s2" not in d, \
        "the forward note already exists (never rewrite twice)"
    d["forward_note_r105s2"] = {
        "appended_by": "builder-r105s2 (the c-0123 precision lane; "
                       "the auditor R105 verdict D6 item: 'quote "
                       "final-tip 747e2fa1 CI in r105 status forward "
                       "note')",
        "typed_as": "Art. 4 in-place append (no existing field "
                    "rewritten; the dacffd034 precedent)",
        "final_tip_747e2fa1_ci": ci_747,
        "lane_tip_ci": ci_tip,
        "lane_state": ("the c-0123 precision lane closed: the pairwise "
                       "disjointness JSON records committed (42 pairs "
                       "clean, 3 chain gates PASS), the guard "
                       "self-comparison refusal typed + proven, the "
                       "stale F81 note deleted on the audit branch "
                       "(89d1f9ae8, verdict-directed), the pyribs "
                       "NOT-ADOPTED row kept, no new guard/claim "
                       "kinds; round record "
                       "eval/r105s2_precision_round_record.json"),
    }
    PATH.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    print("forward note appended")


if __name__ == "__main__":
    main(json.loads(sys.argv[1]), json.loads(sys.argv[2]))

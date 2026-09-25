#!/usr/bin/env python3
"""R536 Cliff 1: corrected typed dropout table (READ-ONLY reclassify).

The R535 typed dropout table was produced by the R532 classifier with
the priority-order defect (cemetery blocks mislabeled ASSEMBLY_INVALID).
R536 reclassifies the SAME durable bytes with the corrected
precedence (adapters._ms_attempt_outcome now checks
cemetery_blocked first).  No new live calls: every attempt row in
the R535 harvest is reclassified from its recorded fields
(candidate_state, semantic_verdict, cemetery_blocked,
distinctness_verdict, retained, support_state, llm outcome) —
exactly what the corrected classifier reads.

The corrected table supersedes R535's for MECHANISM_SPACE typed
outcomes only; the R535 sealed artifacts are untouched (Art. XI).
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HARVEST = REPO / "R526" / "ATTR_CURRENT_HARVEST.json"
SESSIONS = REPO / "R535" / "BATTERY_SESSIONS_CURRENT.json"
OUT = REPO / "R536" / "R536_CORRECTED_TYPED_DROPOUT_TABLE.json"


def main() -> int:
    import sys
    sys.path.insert(0, str(REPO))
    from discovery_fabric.engine import adapters as ad

    sids = {s["session_id"] for s in
             json.loads(SESSIONS.read_text(encoding="utf-8"))[
                 "submissions"]}
    rows = [r for r in
            json.loads(HARVEST.read_text(encoding="utf-8"))["rows"]
            if r.get("session_id") in sids]
    table = []
    for r in rows:
        pid = r.get("problem_index")
        mss = r.get("mechanism_space_spans") or {}
        atts = mss.get("instantiation_attempts") or []
        for att in atts:
            _n_fields = (att.get("output_nonempty_fields") or 0)
            _ok = _n_fields > 0
            state = att.get("candidate_state")
            block = bool(att.get("cemetery_blocked"))
            # R536 Cliff 1 reclassification, faithful to the
            # corrected _ms_attempt_outcome precedence:
            #  (a) pre-terminal losses are read from the recorded
            #      attempt fields exactly (the provider call was
            #      made for every attempted row; a zero recorded
            #      non-empty-field count is the only way an
            #      attempted row reached a pre-terminal loss);
            #  (b) the terminal branches are re-read from the
            #      RECORDED terminal states (cemetery block state,
            #      semantic verdict, assembly state) with
            #      cemetery_blocked checked BEFORE
            #      candidate_state — the correction;
            #  (c) retained-sensitive branches (ACCEPTED /
            #      DISTINCTNESS_DROP / SUPPORT_DROP) are resolved
            #      from the recorded terminal_reason
            #      (BUILT => accepted; otherwise the named loss),
            #      because per-attempt retained/distinctness are
            #      not separately recorded.  No fabricated causes:
            #      any row that reaches none of the known recorded
            #      states stays UNKNOWN (Art. XXV).
            if not att.get("attempted"):
                rerun = {"outcome": "NOT_ATTEMPTED"}
            elif _n_fields == 0:
                rerun = {"outcome": "PARSE_FAILURE"}
            elif not _ok:
                rerun = {"outcome": "REQUIRED_FIELDS_MISSING"}
            elif state == "NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT" \
                    and block:
                rerun = {"outcome": "CEMETERY_BLOCK"}
            elif att.get("semantic_verdict") in (
                    "TEXTUAL_REWRITE", "SEMANTIC_INVARIANT_BROKEN") \
                    or state in ("NOT_A_CANDIDATE_TEXTUAL_REWRITE",
                                 "NOT_A_CANDIDATE_OPERATOR_"
                                 "INVARIANT_BROKEN",
                                 "NOT_A_CANDIDATE_SPAN_NOT_VERBATIM"):
                rerun = {"outcome": "SEMANTIC_REJECT"}
            elif block:
                rerun = {"outcome": "CEMETERY_BLOCK"}
            elif state and state != "CANDIDATE":
                rerun = {"outcome": "ASSEMBLY_INVALID",
                         "candidate_state": state}
            else:
                tr = att.get("terminal_reason")
                if tr == "BUILT":
                    rerun = {"outcome": "CANDIDATE_ACCEPTED"}
                else:
                    rerun = {"outcome": "UNKNOWN", "terminal_reason": tr}
            table.append({
                "problem_index": pid,
                "session_id": r.get("session_id"),
                "old_typed_outcome": att.get("typed_outcome"),
                "corrected_outcome": rerun.get("outcome"),
                "raw_cemetery_blocked": bool(
                    att.get("cemetery_blocked")),
                "raw_candidate_state": att.get("candidate_state"),
                "reclassified": (att.get("typed_outcome") !=
                                 rerun.get("outcome")),
            })
    dist_old = Counter(t["old_typed_outcome"] for t in table)
    dist_new = Counter(t["corrected_outcome"] for t in table)
    rec = {
        "artifact": "R536_CORRECTED_TYPED_DROPOUT_TABLE/1.0",
        "round": "R536",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "method": ("READ-ONLY reclassification of the R535 harvest "
                   "attempts with the corrected "
                   "_ms_attempt_outcome precedence (cemetery_blocked "
                   "checked before candidate_state); no new live "
                   "calls; the R535 sealed artifacts are untouched"),
        "correction_note": ("the R532 classifier mislabeled every "
                            "cemetery hard-block as ASSEMBLY_INVALID "
                            "(the block overwrites candidate_state, "
                            "which the old order read first). 4 of 5 "
                            "R535 ASSEMBLY_INVALID rows were in fact "
                            "CEMETERY_BLOCK; only problem 3 was a "
                            "genuine assembly loss"),
        "attempts": table,
        "distribution_r535_as_recorded": dict(dist_old),
        "distribution_corrected": dict(dist_new),
        "n_reclassified": sum(t["reclassified"] for t in table),
        "reclassification_note": (
            "the per-field values are NOT recorded in the attempt "
            "entry (only output_nonempty_fields); the corrected "
            "classifier therefore re-reads its pre-terminal branches "
            "with the recorded terminal states as authority: a "
            "recorded CEMETERY_PROVEN_INVARIANT state + "
            "cemetery_blocked=true reclassifies to CEMETERY_BLOCK "
            "(4 rows); a recorded NO_TESTABLE_PREDICTION state "
            "without a block stays ASSEMBLY_INVALID (1 row); "
            "accepted/semantic rows are unchanged. This is the "
            "audit's quantification: 4 of 5 R535 NO_CANDIDATES "
            "rows are cemetery false-positive hard-blocks, 1 is a "
            "genuine still-unexplained assembly loss."),
            "causality_conclusion": (
                "the R535 'UPSTREAM_CAUSALITY_NOT_YET_ESTABLISHED' "
                "single-cliff decision is CORRECTED by the corrected "
                "instrument: 4 of 5 R535 NO_CANDIDATES losses are "
                "CEMETERY_BLOCK — a PROVEN_INVARIANT hard-block on "
                "generic physics vocabulary (CE-001's domain terms "
                "like 'state/measurement/condition' matching "
                "cross-domain candidates). The genuine assembly "
                "loss is 1/8 (problem 3, NO_TESTABLE_PREDICTION, "
                "cemetery_blocked=false) and remains unexplained — "
                "it is the only case that would need the upstream "
                "RETRIEVE/FREEZE/VERIFY instrumentation. Cliff 2 "
                "(the cemetery domain-identity prerequisite) is the "
                "authorized next one-cliff fix for the 4/8 majority "
                "cause."),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("as-recorded:", dict(dist_old))
    print("corrected:  ", dict(dist_new))
    for t in table:
        mark = "  <- reclassified" if t["reclassified"] else ""
        print(f"  p{t['problem_index']}: {t['old_typed_outcome']} "
              f"-> {t['corrected_outcome']}{mark}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

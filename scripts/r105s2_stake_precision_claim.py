#!/usr/bin/env python3
"""Stake c-0123 — the r105s2 precision lane (auditor R105 verdict, score 7).

Art. 29(b): staked BEFORE any work byte of the lane. Zero sealed-problem
bytes read this session (the v15 one-shot is COMPLETE and BURNED — the
set's instrument maps were already committed by the r105s1 executor;
this lane touches NO problem bytes at all).

Lane contents (auditor VERDICT R105 directions 6-7, the precision
fixes; DISJOINT from the score-8 lane which stakes separately):
(1) commit the r99 pairwise-disjointness JSON records — the pairwise
    chain (v13-vs-v1-12, v14-vs-v1-13, v15-vs-v1-14) as committed JSON
    artifacts, not prose-only status lines (the auditor's "(F82)" item);
(2) typed refusal on self-comparison: r99_disjointness_guard refuses
    (exit 2, SELF_COMPARISON_REFUSED) when the target set's own version
    is inside the prior-corpus range — the auditor DELETED the
    "non-vacuity self-clash proof" usage (the meaningless 54-clash run
    in the r103 verifier record; verdict D7: "the --versions=1-14
    self-comparison usage");
(3) the stale F81 note deletion in audit/ROADMAP_4_TO_9_DETAILED.md
    "COPYABLE TECHNIQUES — UPDATE 2" (line 84: "NOTE F81: ... MISSING
    from NOTICE.md") — NOTICE.md carries the Reflexion (MIT) /
    Self-Refine (Apache-2.0) attributions since the R94 verification;
    the auditor verdict rules the note stale. ONE surgical sentence
    deletion on the audit branch, explicitly directed by the verdict
    D7 — the crossing is disclosed in the round record;
(4) the final-tip CI read: the R11 Queue Surface Check at 747e2fa1
    quoted (API-quoted check-run) into the r105s1 status forward note
    (typed Art. 4 in-place correction, the dacffd034 precedent);
(5) pyribs NOT-ADOPTED row KEPT (verdict D7); no new guard/claim kinds;
    Art. 16 accounting for the deleted usage typed in the round record.

Art. 27 typing: precision/custody lane — ZERO discovery_fabric/engine
lines changed by design (the guard lives in scripts/; the lane is a
typed precision disclosure, not a capability round).
"""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
PATH = REPO + "/eval/work_claims.json"

now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, cwd=REPO).stdout.strip()[:9]

session_note = (
    "R105 session-2: continuation of the r105s1/r103s1 builder lineage "
    "(same lane family, fresh sandbox context after the recycle; queue "
    "re-synced bfaab8511 -> 747e2fa1f ff-only, the stale R64s4-era "
    "untracked eval/holdout_v9_generation/ backed OUT of tree to "
    "/home/z/my-project/r64s4_untracked_backup/ before the ff). "
    "Vault restored via r77_vault_restore.py (6 keys, digests "
    "COMMITTED_RECORD_MATCH — the 2-key rotation digests "
    "d0c666a3842f + 5c4dffd28fe4 match the auditor attestation). "
    "FULL EPISTEMIC_CONSTITUTION.md v3.3.0 read @ 747e2fa1 (29 "
    "articles + 4 amendment records + the Art. 28 addendum). "
    "Executor of the R105-verdict precision lane.")

claim = {
    "claim_id": "c-0123",
    "claimed_at": f"{now} (sandbox clock, TRUE UTC)",
    "registered_at": f"{now} (sandbox clock, TRUE UTC)",
    "work_id": "r105s2-precision-lane",
    "title": (
        "THE PRECISION LANE (builder-r105s2, auditor R105 verdict "
        "score-7 directions 6-7): (1) r99 pairwise-disjointness JSON "
        "records committed — the pairwise chain v13-vs-v1-12 / "
        "v14-vs-v1-13 / v15-vs-v1-14 (+dev12) as JSON artifacts from "
        "the committed guard bytes; (2) typed self-comparison refusal "
        "in r99_disjointness_guard (exit 2 SELF_COMPARISON_REFUSED "
        "when the target version is inside the prior-corpus range — "
        "the verdict D7 deletion of the meaningless 54/55-clash "
        "self-clash-proof usage), with the Art. 16 accounting note; "
        "(3) the stale F81 note deleted from audit/"
        "ROADMAP_4_TO_9_DETAILED.md Update 2 (ONE sentence, verdict-"
        "directed; the crossing disclosed); (4) the final-tip CI read "
        "at 747e2fa1 quoted API-side into the r105s1 status forward "
        "note (typed Art. 4 correction); (5) pyribs NOT-ADOPTED row "
        "kept; NO new guard/claim kinds; the score-8 lane stakes "
        "SEPARATELY (disjoint work_id). Zero problem bytes; zero LLM "
        "generation; zero acceptance/score claims."),
    "status": "OPEN",
    "session_id": "builder-r105s2",
    "role": "EXECUTOR",
    "kind": "precision_fixes",
    "base_sha": base,
    "lease_expiry": "2026-11-22T23:59:00Z",
    "artifact_paths": [
        "scripts/r99_disjointness_guard.py",
        "scripts/r105s2_pairwise_records.py",
        "eval/r99_disjointness_pairwise_records.json",
        "eval/r105s2_precision_round_record.json",
        "eval/r105s1_status.json",
        "audit/ROADMAP_4_TO_9_DETAILED.md",
    ],
    "notes": (
        "Art. 29(b): claimed before any lane work byte. No problem "
        "bytes in this lane (the sealed sets are BURNED and this lane "
        "touches none). The --versions flag itself is KEPT (the v15 "
        "corpus extension 1-14 is the legitimate form); only the "
        "SELF-COMPARISON configuration (target version inside the "
        "corpus range) becomes a typed refusal, replacing the "
        "one-off self-clash-proof technique the auditor deleted "
        "(its bytes stay in the r103 verifier record — history is "
        "evidence, Art. 4). F81 disposition: NOTICE.md verified to "
        "carry noahshinn/reflexion (MIT) + madaan/self-refine "
        "(Apache-2.0) rows; the stale 'MISSING from NOTICE.md' note "
        "is deleted per the verdict's own resolution statement."),
    "no_problem_read_before_claim": "True",
}


def main():
    with open(PATH) as f:
        d = json.load(f)
    claims = d["claims"]
    assert all(c["claim_id"] != "c-0123" for c in claims), \
        "c-0123 already exists"
    assert not any(c.get("work_id") == "r105s2-precision-lane"
                   for c in claims), \
        "work_id r105s2-precision-lane already claimed (no dual stake)"
    d["sessions"]["builder-r105s2"] = {
        "registered_at": f"{now} (sandbox clock, TRUE UTC)",
        "role": "builder",
        "note": session_note,
    }
    claims.append(claim)
    with open(PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("c-0123 staked (r105s2-precision-lane, precision_fixes) | "
          "claims:", len(claims), "| base:", base, "| session "
          "builder-r105s2 registered")


if __name__ == "__main__":
    main()

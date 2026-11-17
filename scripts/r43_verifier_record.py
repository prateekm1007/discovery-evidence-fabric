#!/usr/bin/env python3
"""r43_verifier_record.py — the Art. 29(c) VERIFIER record for c-0060
(session builder-r43s2; the c-0057/c-0059 precedent). Zero-LLM
recompute from committed bytes only: the peer/auditor verifier recompute
that the a792a6a97 closeout's EXECUTION-COMPLETE-PENDING-VERIFIER-
RECOMPUTE status awaits. This record NEVER re-runs generation; every
leg recomputes or re-executes deterministic surfaces from the committed
bytes, and the remote conclusions come from the check-run API (the D2
rule).

THE RACE IS DISCLOSED IN THIS RECORD: this sandbox session began
building the same D1/D2/D5 lane WITHOUT having pushed a claim first
(the claim script existed but was not committed/pushed — a process
miss by this session, Art. 29(b)); the peer session (builder-r43s1)
pushed claim c-0060 at b1632cd2c 2026-11-17T01:33:10Z, BEFORE this
session's first implementation write (~01:58Z local). Pusher-wins per
Art. 29(b)/(e): the duplicate executor lane was STOOD DOWN before any
push (the duplicate scratch was never committed to the queue branch;
it is archived OUTSIDE the repo at r43_duplicate_lane_scratch/ and is
not evidence), and this session became the VERIFIER for c-0060. The
coordination design caught the duplicate exactly as designed: two
c-0060 claims never reached the registry."""
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _now() -> str:
    import datetime
    return datetime.datetime.now(datetime.UTC).isoformat().replace(
        "+00:00", "Z")


def main():
    record = {
        "record": "R43_VERIFIER_c0060/1.0.0",
        "session": "builder-r43s2",
        "role": "VERIFIER for c-0060 (work v8-generation-binds, "
                "EXECUTOR builder-r43s1)",
        "verified_tip": "a792a6a97 (origin/queue/dev12_r7)",
        "at": _now(),
        "method": "zero-LLM recompute from committed bytes only "
                  "(Art. 13 / Art. 29(c)): the executor's 23-test "
                  "bind suite re-executed at the verified tip; the "
                  "full rendered queue-CI pytest surface extracted "
                  "from the committed workflow YAML and executed "
                  "locally as bash (the F56 procedure: bash -n clean "
                  "before execution); the pushed CI read from the "
                  "check-run API at THREE SHAs; the diff secret-"
                  "grepped; trailers, registry, Art. 27 ledger keys "
                  "and the Art. 16 retirement ledger checked; the "
                  "F45-class security finding verified typed (counts "
                  "only — values never printed)",
        "race_disclosure": {
            "what": "this session (builder-r43s2) independently built "
                    "the same D1/D2/D5 lane from the same "
                    "90ad970d7 basis while the peer's claim was "
                    "already pushed",
            "why": "Art. 29(b) process miss by THIS session: the "
                   "claim was written but never committed/pushed "
                   "before implementation started; the peer's pushed "
                   "claim (b1632cd2c, 01:33:10Z) predates this "
                   "session's first implementation write (~01:58Z)",
            "resolution": "pusher-wins (Art. 29(b)/(e)): stand down "
                          "to VERIFIER, never rebase a duplicate — "
                          "the duplicate scratch was never pushed, "
                          "is archived outside the repo, and no "
                          "second c-0060 claim exists in the "
                          "registry (the push-as-mutex held)",
            "registry_effect": "builder-r43s2 registered as a new "
                               "session; claim c-0061 filed (VERIFIER "
                               "for c-0060); c-0060 flips "
                               "DONE-with-verifier on this record's "
                               "push (the c-0056/c-0058 and c-0057/"
                               "c-0059 precedents)"},
        "legs": {},
    }

    # the per-leg evidence is assembled by the recompute script
    record["legs"] = json.loads(
        (REPO / "eval" / "r43_verifier_c0060_legs.json").read_text(
            encoding="utf-8"))
    out = REPO / "eval" / "r43_verifier_c0060.json"
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print("wrote", out)
    print("verdict:", record["legs"].get("VERDICT"))


if __name__ == "__main__":
    main()

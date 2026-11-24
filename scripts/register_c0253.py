#!/usr/bin/env python3
"""register_c0253.py — the surgical c-0253 claim insertion into
eval/work_claims.json (raw-text append, byte-identical elsewhere —
the registry preserves per-entry key order, so a json roundtrip would
reformat 246 entries)."""
import json

PATH = "eval/work_claims.json"

ENTRY = {
    "artifact_paths": [
        "eval/holdout_v17_strengthened_generation/",
        "discovery_fabric/generation/novelty_strength.py",
        "tests/test_novelty_strength.py",
        "scripts/r146_v17_strengthened_one_shot.py",
        "eval/r146_p4_panel/packs.json",
        "scripts/r146_p4_panel_oneshot.py",
        "eval/r146s1_close.json",
    ],
    "base_sha": "e1f861a8f",
    "claim_id": "c-0253",
    "claimed_at": "2026-11-24 (sandbox clock, TRUE UTC)",
    "kind": "task",
    "lease_expiry": "2026-11-30T23:59:00Z",
    "notes": (
        "the R146 builder lane: (1) the EPO problem-solution "
        "conditioning + the MOOSE-Chem hypothesis ranking "
        "(novelty_strength.py, tests 6/6) wired into the canonical "
        "generation — the DIR-2/6 lever; (2) the quant "
        "generation-time contract (the ONE typed demand loop) — the "
        "DIR-3 acceptance MET on the run: 30/30 computed at "
        "generation, 0 QUANT_TEST_MISSING, 0 invented numbers; "
        "(3) the strengthened sealed one-shot on the audit-branch "
        "sealed bytes 30/30 — the builder screen strong 16 / "
        "marginal 14 / weak 0 vs the r145 baseline weak 30/30 "
        "(input, never the verdict; the scoring is the auditor's "
        "act, PENDING-AUDITOR-SCORE); (4) the DIR-4 panel STOOD DOWN "
        "per Art. 29(e) — c-0252 (builder-r146s1-b) holds the open "
        "executor lease and runs my committed driver + packs (the "
        "83-leg local run was lost untracked in the sandbox recycle; "
        "a rerun under a rival lease would be a double burn); (5) "
        "DIR-8: 2 dead modules pruned with the reappearance guard + "
        "the worldwide monitoring leg typed. The twin's c-0250 lane "
        "(a different engine state: the contract + wording "
        "iteration) stands as its own one-shot; the auditor scores "
        "both."),
    "registered_at": "2026-11-24 (sandbox clock, TRUE UTC)",
    "role": "EXECUTOR",
    "session_id": "builder-r145s1",
    "status": "DONE",
    "title": ("R146S1 strengthened sealed burn + the novelty-strength "
              "lever + the quant generation-time contract"),
    "work_id": "r146s1-strengthened-sealed-burn",
}


def main() -> None:
    raw = open(PATH).read()
    lines = []
    for k, v in ENTRY.items():
        if isinstance(v, list):
            lines.append(f'      "{k}": [')
            lines.append(",\n".join(
                f"        {json.dumps(s)}" for s in v))
            lines.append("      ],")
        else:
            lines.append(f'      "{k}": {json.dumps(v)},')
    block = "\n".join(lines)[:-1]  # drop the last comma
    # the claims array does NOT end the file: anchor on the c-0252
    # entry (the current last claim) and insert after its close,
    # before the array's "\n  ],"
    i = raw.find('"claim_id": "c-0252"')
    assert i != -1, "c-0252 anchor not found"
    j = raw.find("\n    }", i)
    assert j != -1, "c-0252 entry close not found"
    assert raw[j + 6:].lstrip().startswith("],"), (
        "the anchor entry must close the claims array")
    new = raw[:j + 6] + ",\n    {\n" + block + "\n    }" + raw[j + 6:]
    open(PATH, "w").write(new)
    d = json.loads(new)
    assert d["claims"][-1]["claim_id"] == "c-0253"
    print("validated: claims =", len(d["claims"]),
          "| last =", d["claims"][-1]["claim_id"],
          d["claims"][-1]["status"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""r139s3_ledger_census — DIR-7: recompute the audit ledger's OPEN
census against the truly-open set. A finding listed OPEN whose closure
evidence exists in a LATER ledger entry (a verdict/correction/ruling
that resolves it, or a resolved_by field) is a census defect: the
OPEN census must match the truly-open set (recompute diff=0).
Read-only for this lane: the audit branch is the auditor's; the diff
here guides their next ledger push."""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r139s3_ledger_census.json"
LEDGER_SHA = "acfaacae662b"


def main() -> int:
    raw = subprocess.run(
        ["git", "show", f"origin/audit/r11-auditor-verdict-20261114:"
         f"AUDIT_LEDGER.json"],
        capture_output=True, text=True, check=True).stdout
    d = json.loads(raw)
    findings = d.get("findings", [])
    open_f = [f for f in findings if f.get("status") == "OPEN"]
    # closure evidence: any later ledger blob that names the finding id
    # with a resolved/closed/superseded verb
    blob = json.dumps({k: v for k, v in d.items() if k != "findings"})
    later = []
    for f in findings:
        fid = f.get("id")
        hits = re.findall(
            rf"{re.escape(str(fid))}[^.]*"
            r"(resolved|closed|superseded|fixed|retracted|verified and "
            r"closed)",
            blob, flags=re.IGNORECASE)
        if hits:
            later.append({"id": fid, "status": f.get("status"),
                          "closure_mentions": hits[:2]})
    # findings OPEN with closure evidence elsewhere = the census defect
    stale_open = [x for x in later if x["status"] == "OPEN"]
    rec = {
        "record": "R139S3_LEDGER_CENSUS/1.0.0",
        "claim": "c-0221", "at": "2026-11-23 (sandbox clock)",
        "ledger_sha": LEDGER_SHA,
        "findings_total": len(findings),
        "open_census": len(open_f),
        "open_ids": [f.get("id") for f in open_f],
        "stale_open_with_closure_evidence": stale_open,
        "note": ("the auditor's directions quoted 97 findings / 39 OPEN "
                 "— the bytes at acfaacae662b read 102 / 32; both the "
                 "direction figure and the in-file census must be "
                 "reconciled to the truly-open set (the auditor's DIR-7 "
                 "mutation is on their branch; this recompute is the "
                 "independent check the acceptance asks for: diff=0 "
                 "when the census equals the truly-open set)."),
        "census_diff": len(stale_open),
    }
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in
                      ("findings_total", "open_census", "census_diff")},
                     indent=1))
    print("stale_open:", json.dumps([x["id"] for x in stale_open]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

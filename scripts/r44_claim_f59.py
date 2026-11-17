#!/usr/bin/env python3
"""r44_claim_f59.py — file claim c-0063 (work_id f59-exposure-scan,
kind task) and append the honest process note: the scan EXECUTED at
~03:26Z before this claim was filed (an Art. 29(b) process miss by
this session, disclosed; read-only scan + a record commit, no machine
or quota touched, and the coordinator's directions ordered the scan
explicitly). The scan record rides this claim."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOW = "2026-11-17T03:30:00Z (sandbox clock)"

p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
claims = d.setdefault("claims", [])
assert not any(c.get("claim_id") == "c-0063" for c in claims)
claims.append({
    "claim_id": "c-0063",
    "work_id": "f59-exposure-scan",
    "title": "the F59 precision fix: per-branch exact live-token "
             "byte-grep (23 remote branch tips) + a pickaxe sweep over "
             "all reachable history; the reported exposure set must "
             "EQUAL the auditor's byte-verified set (r448/visual-lab "
             "x 2 files); values never printed or written",
    "status": "DONE",
    "registered_at": NOW,
    "session_id": "builder-r44s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": "04ef10ab6",
    "claimed_at": NOW,
    "lease_expiry": "2026-11-17T15:30:00Z",
    "takes_over": None,
    "artifact_paths": ["eval/r44_f59_scan.json",
                       "scripts/r44_f59_scan.py"],
    "notes": "PROCESS MISS DISCLOSED (Art. 29(b)): the scan executed "
             "~03:26Z before this claim was filed — the coordinator's "
             "direction ordered the scan and this session filed the "
             "claim late; typed here, never silent. Zero LLM calls; "
             "read-only; the token was read at runtime from the "
             "gitignored vault and never printed, written, or "
             "committed. RESULT: exposure_set_equals_auditor=true — "
             "exactly {r448/visual-lab: [scripts/r447_canonical_space_"
             "record.py, scripts/r447_hf_deploy.py]}; the R43 verifier "
             "record's shape-match reachability claim (R451 scan "
             "records) is superseded as an over-claim (F59)."})
d["at"] = NOW
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("claim c-0063 filed (f59-exposure-scan, DONE, miss disclosed)")

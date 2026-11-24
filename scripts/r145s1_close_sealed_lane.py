#!/usr/bin/env python3
"""r145s1 v17-sealed-lane close: claim c-0247 -> DONE with the typed
verdict; the deterministic verifier recompute registered as the next
free verifier lane (Art. 29(c): never re-runs, recomputes from the
committed bytes)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REG = REPO / "eval" / "work_claims.json"
CNT = REPO / "eval" / "claim_next_id.txt"

d = json.loads(REG.read_text())
claims = d["claims"]
c247 = [c for c in claims if c.get("claim_id") == "c-0247"][0]
assert c247["work_id"] == "r145-v17-sealed-one-shot"
if c247["status"] == "OPEN":
    c247["status"] = "DONE"
    c247["closed_at"] = "2026-11-24 (sandbox clock)"
    c247["completed_by"] = "builder-r145s1 (the registered executor)"
    c247["completion_commit"] = "de5cdbc0f"
    c247["verdict"] = {
        "acceptance": (
            "LANE MET with the auditor gate typed PENDING: (1) the v17 "
            "SEALED one-shot COMPLETE — 30/30 generated, 0 resumed, "
            "637.6s wall, problem-only, agnes-3.0-flash pinned, on the "
            "OWNER's sealed audit-branch bytes (the digest typed per "
            "row); the raw rows + events ledger committed with the "
            "run; (2) the class routing 30/30 EXACTLY the owner's "
            "10-class grouping (3 per class); (3) OFF-TARGET MECHANISM "
            "FIRES 0/30 (the machine scan); (4) the DIR-3 surface: "
            "worked calculation 30/30, numeric-with-unit 29/30, "
            "kill-condition/falsification-test 28/30, the generic-"
            "quant pint layer COMPUTED 29/30 (1 typed "
            "insufficient_parameters with the plan); QUANT_TEST_"
            "MISSING typed on 4 rows (surfaced, never hidden); (5) "
            "the mean>=3.3 / CI lower>3.0 / >=30% strong / 0 "
            "off-target / 0-0-0 gate is PENDING-AUDITOR-SCORE (the "
            "builder never scores itself, Art. 10/14)"),
        "method": ("the sealed instrument executed end-to-end; the "
                   "screen computed from the committed bytes only"),
    }
    c247["verifier_note"] = (
        "the deterministic verifier recompute: (a) 30/30 row presence "
        "+ per-row engine_trace.strength_kit + final_meta read; (b) "
        "the screen numbers recomputed (routing, 0-off-target scan, "
        "the quant surfaces, the novelty-gate recompute) vs "
        "eval/holdout_v17_sealed_screen.json — diff>0 is a finding; "
        "(c) the generic-quant computed records re-checked per row")
else:
    print("c-0247 already closed (idempotent)")

ids = [c.get("claim_id") for c in claims]
counter_val = CNT.read_text().strip()
if counter_val in ids:
    # the counter was advanced by a concurrent registration; find the
    # next genuinely-free id AFTER the counter
    n = int(counter_val[2:])
    while f"c-{n:04d}" in ids:
        n += 1
    counter_val = f"c-{n:04d}"
verifier = {
    "work_id": "r145-v17-sealed-one-shot",
    "claim_id": counter_val,
    "role": "VERIFIER",
    "session_id": "builder-r145s1",
    "kind": "task",
    "status": "OPEN",
    "base_sha": "de5cdbc0f",
    "lease_expiry": "2026-12-01T23:59:00Z",
    "claimed_at": "2026-11-24 (sandbox clock)",
    "registered_at": "2026-11-24 (sandbox clock)",
    "artifact_paths": [
        "eval/holdout_v17_sealed_generation/",
        "eval/holdout_v17_sealed_screen.json",
        "scripts/r145_sealed_screen.py",
    ],
    "title": (
        "R145S1 VERIFIER (claim " + counter_val + ", base de5cdbc0f): "
        "the c-0247 sealed-one-shot lane — the deterministic recompute "
        "from the committed bytes (Art. 13/29(c): never re-run): the "
        "screen's numbers recomputed over the 30 row records (the "
        "class routing vs the owner's grouping, the 0-off-target "
        "scan, the quant surfaces, the novelty-gate recompute) — "
        "diff>0 is a finding"),
}
claims.append(verifier)
d["claims"] = claims
CNT.write_text(f"c-{int(counter_val[2:]) + 1:04d}\n")
REG.write_text(json.dumps(d, indent=2, ensure_ascii=True) + "\n")
print(f"c-0247 -> DONE; verifier lane {counter_val} registered OPEN; "
      f"counter -> c-{int(counter_val[2:]) + 1:04d}")

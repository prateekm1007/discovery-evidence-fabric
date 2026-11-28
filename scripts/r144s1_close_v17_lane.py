#!/usr/bin/env python3
"""r144s1 v17-lane close: claim c-0245 -> DONE with the typed verdict;
the deterministic verifier recompute registered as OPEN verifier lane
c-0246 for the next window (Art. 29(c): VERIFIER never re-runs — it
recomputes from the committed bytes; the bf9151e7e precedent)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REG = REPO / "eval" / "work_claims.json"
CNT = REPO / "eval" / "claim_next_id.txt"

d = json.loads(REG.read_text())
claims = d["claims"]

c245 = [c for c in claims if c.get("claim_id") == "c-0245"][0]
assert c245["work_id"] == "r144-v17-one-shot" and c245["status"] == "OPEN"
c245["status"] = "DONE"
c245["closed_at"] = "2026-11-24 (sandbox clock)"
c245["completed_by"] = "builder-r144s1 (the registered executor)"
c245["completion_commit"] = "0ce9c00b6"
c245["verdict"] = {
    "acceptance": (
        "LANE MET with the auditor gate typed PENDING: (1) the v17 "
        "ONE-SHOT COMPLETE — 30/30 generated, 0 resumed, 355.7s wall, "
        "problem-only, agnes-3.0-flash pinned, the raw rows + events "
        "ledger committed with the run (Art. 18/22); (2) the builder "
        "screen (eval/holdout_v17_builder_screen.json) typed as "
        "INPUTS — family routing 29/30 under the extended lexicon, "
        "winner classes configuration 18 / geometry 5 / chemistry 5 / "
        "boundary 2, the chemical-CP-for-abrasion class GONE, the "
        "worked-calculation surface 28/30, the kill-condition surface "
        "2/30 (the measured gap: the bind rides the SEALED instrument "
        "— wired in this lane, this run's bytes unchanged, no "
        "re-roll), OFF_TARGET_MECHANISM 1/30 fired by the landed "
        "scan; (3) the additive lexicon extension measured-necessary "
        "(9/30 -> 29/30 fresh routing; the 9 v16 re-routes typed; "
        "the r52 F77 refresh verdict UNCHANGED PASS 0/0/0; the "
        "off-target scan re-validated 2/2 precision, 0 false fires); "
        "(4) the mean>=3.3/CI>3.0/>=30%-strong gate is the AUDITOR's "
        "sealed scoring (PENDING-AUDITOR-SCORE — the builder never "
        "scores itself, Art. 10/14; the v17 set is the builder-"
        "authored CANDIDATE set, the seal + rubrics stay the "
        "auditor's act)"),
    "method": "the one-shot instrument executed end-to-end; the screen computed from the committed bytes only",
}
c245["verifier_note"] = (
    "the verifier recompute lane registered as c-0246 (OPEN, next "
    "window): recompute the screen numbers from the committed row "
    "bytes (the family/winner/read of each row's engine_trace + "
    "final_meta; the screen's regexes re-run over the 30 a1_answer "
    "texts), diff vs eval/holdout_v17_builder_screen.json — "
    "deterministic, zero generation, reads only committed bytes")

ids = [c.get("claim_id") for c in claims]
assert "c-0246" not in ids, "c-0246 collision"
counter_val = CNT.read_text().strip()
verifier = {
    "work_id": "r144-v17-one-shot",
    "claim_id": counter_val,
    "role": "VERIFIER",
    "session_id": "builder-r144s1",
    "kind": "task",
    "status": "OPEN",
    "base_sha": "0ce9c00b6",
    "lease_expiry": "2026-12-01T23:59:00Z",
    "claimed_at": "2026-11-24 (sandbox clock)",
    "registered_at": "2026-11-24 (sandbox clock)",
    "artifact_paths": [
        "eval/holdout_v17_generation/",
        "eval/holdout_v17_builder_screen.json",
        "scripts/r144_v17_builder_screen.py",
    ],
    "title": (
        "R144S1 VERIFIER (claim " + counter_val + ", base 0ce9c00b6): "
        "the c-0245 v17 one-shot lane — the deterministic recompute "
        "from the committed bytes (Art. 13/29(c): never re-run): "
        "(a) 30/30 row presence + per-row engine_trace.failure_physics "
        "and final_meta read; (b) the screen's numbers recomputed "
        "(family routing, winner classes, the quant/kill-condition "
        "regex surface, the finding keys) vs "
        "eval/holdout_v17_builder_screen.json — diff>0 is a finding; "
        "(c) the OFF_TARGET_MECHANISM fire re-checked on v17-15"),
}
claims.append(verifier)
d["claims"] = claims
CNT.write_text(f"c-{int(counter_val[2:]) + 1:04d}\n")
REG.write_text(json.dumps(d, indent=2, ensure_ascii=True) + "\n")
print(f"c-0245 -> DONE; verifier lane {counter_val} registered OPEN; "
      f"counter -> c-{int(counter_val[2:]) + 1:04d}")

#!/usr/bin/env python3
"""r109s2_close_claim.py — the c-0138 close (status DONE + the record
reference) + the VF-1/VF-2/VF-3 typed correction appends on c-0130's
notes (forward-only: the historical text preserved verbatim, Art. 4;
the c-0131 precedent of verifier-registered forward-only disclosures).
Registry formatting preserved. Fail-closed idempotence guards.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

REG = Path(__file__).resolve().parents[1] / "eval" / "work_claims.json"
NOW = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")

d = json.loads(REG.read_text(encoding="utf-8"))
assert d["schema"] == "work-claims/v1"
by_id = {c.get("claim_id"): c for c in d["claims"]}

c138 = by_id.get("c-0138")
assert c138 and c138["session_id"] == "builder-r109s2", "c-0138 missing"
assert c138["status"] == "OPEN", f"c-0138 already {c138['status']}"
c138["status"] = "DONE"
c138["done_at"] = NOW
c138["notes"] = ("VERIFIER COMPLETE (Art. 29(c), the recompute — never a "
                 "re-run; zero quota/LLM/sealed bytes): 17 checks = 11 "
                 "PASS / 0 FAIL / 6 TYPED. D8: the cross-record Bolt "
                 "numbers byte-match stage-3; all 8 CWRU legs recompute "
                 "as exact fractions; the winner/tie rules apply as "
                 "typed. D7: the archive lives (2538/2496), the "
                 "attribution structure (zero per-minute time collisions "
                 "between the bearings) AND integrity (173/173 into the "
                 "committed listing), the cadence, the coverage fractions "
                 "(30/37, 33/50, 28/50), the CTX adaptation math (26/40), "
                 "and the RMS ratios (6.5473/2.0115) recompute EXACTLY "
                 "from committed bytes. Six findings filed (VF-1..VF-6: "
                 "one P2 — the wall-clock definition mismatch behind the "
                 "'2.5x faster' claim — + five P3 disclosure/precision "
                 "findings; none invalidates a committed measurement). "
                 "Record: eval/r109s2_c0130_verifier_record.json; the "
                 "independent recompute log: eval/"
                 "r109s2_c0130_recompute_log.json (scripts/"
                 "r109s2_c0130_verify.py, zero executor-driver imports). "
                 "The raw channels/RMS series/sample mtimes are "
                 "sandbox-local: typed UNVERIFIED-FROM-COMMIT where so.")

c130 = by_id.get("c-0130")
assert c130 and c130["session_id"] == "builder-r105s2", "c-0130 missing"
CORR = (" VERIFIER CORRECTIONS (builder-r109s2 c-0138 @ " + NOW
        + ", forward-only — the historical text above preserved, Art. 4; "
        "full findings in eval/r109s2_c0130_verifier_record.json): "
        "VF-1 the census figures '62/100, 152/260 eligible' are the "
        "n>=192 counts under the mislabeled "
        "'n_eligible_ge_2ctx_plus20' key — the ACTUAL unit filter in "
        "both stages is n>=212 (37 FD001 / 92 FD002); the measured legs "
        "are identical across arms (code-verified), no measurement "
        "affected. VF-2 the 'Sundial 2.5x faster wall-clock' claim "
        "compares per-call (2022.9, arm.last_ms) vs per-walk (4996.2, "
        "the full sliding_walk timing mislabeled per-call in stage-3) — "
        "the honest same-definition ratio is NOT derivable from "
        "committed bytes; the direction (Sundial faster) stands, the "
        "2.5x magnitude is withdrawn. VF-3 the CWRU comparison above "
        "reads 'Sundial 8/9/7 fault alarms vs Bolt 0/0/0/1' — the "
        "committed Sundial quadruple is 1/8/9/7, and '0/0/0/1' is the "
        "stage-3b DUAL arm's fault detection, not the stage-3 SLIDING "
        "Bolt (0/2/2/4) that 'Bolt's sliding absorbed them' references; "
        "the qualitative claim holds against both arms, the quadruples "
        "as written cite no single committed pair.")
if "VERIFIER CORRECTIONS" not in c130.get("notes", ""):
    c130["notes"] = c130.get("notes", "") + CORR

REG.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("c-0138 -> DONE; c-0130 corrections appended "
      f"({len(d['claims'])} claims)")

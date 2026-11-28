#!/usr/bin/env python3
"""r30_claim_v75.py — file claim c-0030 (AM28 D2 conversion batch)
BEFORE any LLM call (Art. 29(b)). Idempotent."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
if "c-0030" in {c["claim_id"] for c in d["claims"]}:
    print("c-0030 already filed")
    raise SystemExit(0)
d["claims"].append({
    "claim_id": "c-0030", "work_id": "r30-v75-conversion",
    "session_id": "builder-r20s1", "role": "EXECUTOR",
    "kind": "conversion-generation", "base_sha": "397f26921",
    "claimed_at": "2026-11-16T12:40:00Z",
    "lease_expiry": "2026-11-16T17:00:00Z", "status": "OPEN",
    "takes_over": None,
    "artifact_paths": ["eval/pairs/r30_v75_converted/",
                       "eval/r30_v75_tuning_generation.json"],
    "notes": "AM28 D2 (the 3 residual gap-1 rows) + the F40 content "
             "correction, in ONE machine run. Re-draw set (4 rows, "
             "the auditor's AM28 residuals verbatim): bench-p09 "
             "(silica-nanoparticle sheet catalog reality unproven), "
             "bench-p11 ('existing hydraulic ports' premise "
             "assumption), eval-new03 (0.1 mm bypass-lumen catheter "
             "= new infusion-set design + regulatory path), "
             "bench-p10 (F40: SentryGlas ionoplast misattributed as "
             "a sodium-barrier film — recompose on a REAL "
             "ion-barrier exemplar class, SiOx-coated PET, with a "
             "supplier-datasheet basis). Machine: the V7.4 path "
             "BYTE-UNCHANGED in logic (one generation pass under "
             "contract_for_v72 + critic + type gate + typed scans "
             "[base + constraint-fit + catalog-v2 + standard-bill + "
             "operational-loss + conversion] + NEUTRAL repair "
             "directive, budget 3, K_GEN=1, judge-blind) with ONE "
             "pre-registered change: the repair directive gains the "
             "three V75 clauses (EXEMPLAR-REALITY / PREMISE-VALIDITY "
             "/ CERTIFIED-SYSTEM-AS-SOLD) on top of the V7.4 "
             "DEPLOYED-PART clause — directive module "
             "scripts/r30_v75_directive.py committed in the same "
             "push. All other rows stay BYTE-FROZEN at their "
             "committed battery bytes. Rows land PENDING-AUDITOR "
             "(Art. 10); the acceptance is the auditor's re-read "
             "(feasibility |gap| <=0.25 held on the full 30 with all "
             "rows gap 0-1 and no premise assumptions). Post-batch "
             "F40 pin: the corrected bench-p10 bill names no "
             "ionoplast interlayer as an ion barrier and names the "
             "exemplar class with a datasheet basis. VERIFIER: peer "
             "session invited — recompute from committed bytes "
             "(Art. 13)."})
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("claim c-0030 filed (r30-v75-conversion)")

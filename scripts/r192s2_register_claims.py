#!/usr/bin/env python3
"""R192S2: register session builder-r192s2 + claims c-0304/05/06
(claim-before-work, Art. 29(b)) — the push is the lock.
c-0306 references the dead leases (c-0299 builder-r159s2, c-0302
builder-r190s1) per the Art. 29(d) takeover rule and resumes from the
committed PARTIAL ablation rows (21/24)."""
import datetime, json, subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
PATH = REPO + "/eval/work_claims.json"
now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, cwd=REPO).stdout.strip()[:9]

doc = json.load(open(PATH))
doc.setdefault("sessions", {})
doc["sessions"]["builder-r192s2"] = {
    "registered_at": now, "role": "BUILDER",
    "note": "successor session to builder-r159s2 (sandbox recycled)"}

claims = [
    {
        "claim_id": "c-0304",
        "work_id": "r192s2-dir3-critic-calibration",
        "role": "EXECUTOR",
        "kind": "measurement",
        "status": "OPEN",
        "session_id": "builder-r192s2",
        "claimed_at": now,
        "lease_expiry": "2026-11-29T23:00:00Z",
        "base_sha": base,
        "artifact_paths": [
            "scripts/r190s1_critic_calibrate.py",
            "eval/r190s1_critic_calibration/",
            "eval/r192s2_dir3_accept.json",
        ],
        "note": ("DIR 3: the calibration RUN on the owner-delivered 48 "
                 "labels (7da44fae5; DIR-1 hash verify 48/48 this "
                 "session, scripts/r192s2_dir1_hash_verify.py). The bar "
                 "is pre-registered (eval/r190s1_critic_prereg.json, the "
                 "typed amendment; recall>=0.60 serious / FP<=0.25 clean "
                 "/ keep best F1). One calibration run per label-set "
                 "version; byte-resume per (variant,row)."),
    },
    {
        "claim_id": "c-0305",
        "work_id": "r192s2-dir2-selector-remeasure",
        "role": "EXECUTOR",
        "kind": "measurement",
        "status": "OPEN",
        "session_id": "builder-r192s2",
        "claimed_at": now,
        "lease_expiry": "2026-11-29T23:00:00Z",
        "base_sha": base,
        "artifact_paths": [
            "scripts/r190s1_threearm_run.py",
            "eval/r192s2_dir2_remeasure/",
        ],
        "note": ("DIR 2: re-measure the 8 labeled items with the locked "
                 "selector (departure -> relaxation -> contradiction, "
                 "plain deleted, first-clean selection, no tournament "
                 "gate). Accept: 8/8 judged, clean-pick and novel-pick "
                 "counts from bytes, >=7/8 both. Gated on the c-0304 "
                 "calibrated critic."),
    },
    {
        "claim_id": "c-0306",
        "work_id": "r192s2-dir4-ablation-resume-22-24",
        "role": "EXECUTOR",
        "kind": "measurement",
        "status": "OPEN",
        "session_id": "builder-r192s2",
        "claimed_at": now,
        "lease_expiry": "2026-11-29T23:00:00Z",
        "base_sha": base,
        "artifact_paths": [
            "scripts/r186s1_ablation_repair.py",
            "eval/r186s1_ablation/",
        ],
        "note": ("DIR 4: Art. 29(d) TAKEOVER of the ablation completion "
                 "lane — references the dead leases c-0299 "
                 "(builder-r159s2, sandbox recycled) and c-0302 "
                 "(builder-r190s1, sandbox recycled); resumes from the "
                 "committed PARTIAL rows (21/24, 2W/17T/2L, delta "
                 "+0.000 at 49a9789dc). Byte-resume items 22-24 from "
                 "zero legs; no re-run of measured bytes; then the "
                 "formal PRUNE verdict + router 6->4."),
    },
]
for c in claims:
    doc["claims"].append(c)

with open(PATH, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
with open(REPO + "/eval/claim_next_id.txt", "w") as fh:
    fh.write("c-0307\n")
print("registered session builder-r192s2 + claims c-0304/c-0305/c-0306, next c-0307, base", base)

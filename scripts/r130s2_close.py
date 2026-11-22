#!/usr/bin/env python3
"""r130s2_close.py — the round-2 close for claim c-0208 (work id
r130s2-bon2-parity): (1) ABLATION_REGISTRY entry 15 (bon2) updated
with the POOLED parity numbers + the ADOPT verdict (the gate object
is the defect_rows/rows dict the Art. 20 CI test recomputes);
(2) work_claims c-0208 -> DONE with the quoted CI chain;
(3) eval/r130s2_status.json — the second-lane R130 record (the
r130s1_status.json schema). Zero engine lines (Art. 27)."""
import datetime
import json
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

scoring = json.load(open(REPO / "eval" / "r130s2_bon_parity_scoring.json"))
gate = scoring["gate"]
assert gate["verdict"] == "ADOPT" and gate["beats_incumbent"] is True
assert gate["defect_rows"] == 0 and gate["rows"] == 48

# (1) registry entry 15 (bon2) -> the round-2 parity outcome
reg_path = REPO / "eval" / "ABLATION_REGISTRY.json"
reg = json.load(open(reg_path))
hit = None
for e in reg["entries"]:
    if str(e.get("variant", "")).startswith("bon2-bindselect-n2"):
        hit = e
        break
assert hit is not None, "bon2 registry entry missing"
assert hit["variant_numbers"]["defect_rows"] == 0  # round-1 entry shape
hit["variant_numbers"] = {"defect_rows": gate["defect_rows"],
                          "rows": gate["rows"]}
hit["metric_citation"] = "eval/r130s2_bon_parity_scoring.json:gate"
hit["round1_metric_citation"] = "eval/r129_bon_scoring.json:gate"
hit["beats_incumbent"] = gate["beats_incumbent"]
hit["gate_pass"] = True
hit["status"] = ("ACTIVE (ADOPTED at the Art. 20 round-2 gate: the "
                 "round-1 win REPLICATED — pooled 0/48 arm rows vs "
                 "the incumbent's recomputed 2/48 on the same 24 "
                 "items; adopted as the Phase-B selection layer)")
hit["round2_note"] = (
    "the round-2 48-row parity (claim c-0208, builder-r130s2, prereg "
    "eval/r130s2_bon2_parity_prereg.json pushed as the lock at "
    "90d546078 BEFORE any run call): the arm BYTE-IDENTICAL to round "
    "1 (delegation to the committed r129_bon_run legs; the only "
    "variable the independent replication) ran 96 legs in 894.0 s "
    "wall, 0 typed fails, 0 parse retries (24/24 first-try), 4 "
    "rate_limited backoff legs absorbed (max 2 attempts, per-leg "
    "transport_attempts in the records), cached 0 (the agnes "
    "cache-telemetry ~0 finding re-confirmed). Rep-2 selection "
    "NON-DEGENERATE again: 22 x [0,0] ties (-> c1) + r125-08-s2 "
    "[0,1] and r125-10-s1 [1,0] — the deterministic battery + rule "
    "took the CLEAN candidate on both decisive items. Pins "
    "reproduced pre-gate from bytes (incumbent 2/48 both "
    "duty_pricing d1; round-1 arm 0/24). Second-construction "
    "crosscheck match. Descriptive width (Art. 14, seed 20261122): "
    "point -0.041667, CI95 [-0.104167, 0.0] — descriptive ONLY, no "
    "significance claim, no score claim.")
json.dump(reg, open(reg_path, "w"), indent=1)
print("registry entry 15 updated: variant_numbers="
      f"{hit['variant_numbers']} status={hit['status'][:60]}...")

# (2) claim c-0208 -> DONE
wc_path = REPO / "eval" / "work_claims.json"
wc = json.load(open(wc_path))
claim = None
for c in wc["claims"]:
    if c["claim_id"] == "c-0208":
        claim = c
        break
assert claim is not None and claim["status"] in ("OPEN", "DONE")
claim["status"] = "DONE"
claim["completed_at"] = NOW
claim["notes"] = (
    "Art. 29(b) held: prereg + claim pushed as the lock at 90d546078 "
    "BEFORE any run call (refs/claims/next rides the same push); CI "
    "re-read from the API: check-run 137303464796 surface completed "
    "SUCCESS (quoted, never asserted). THEN the run: 96 legs "
    "(48 author + 48 reviewer), 894.0 s wall pool-of-2, 0 typed "
    "fails, 0 parse retries, 4 absorbed rate_limited backoffs, "
    "per-leg transport_attempts in the records. Gate (preregistered "
    "round 2): POOLED arm 48 rows -> 0 delivered-defect rows vs the "
    "incumbent's recomputed 2/48 (r125-05-s2/d1 + r125-07-s2/d1, "
    "both duty_pricing — byte-pin reproduced pre-gate, Art. 3) -> "
    "ADOPT; registry entry 15 updated in THIS commit with the "
    "defect_rows/rows gate dict so the Art. 20 CI recompute bites. "
    "Second-construction crosscheck match; descriptive width typed "
    "(Art. 14). HONEST BOUNDS: same-24-items parity, two independent "
    "replications vs the incumbent's two committed draws; an ablation "
    "ADOPT, NOT a capability-score event and NOT a significance "
    "claim. Disclosure healed forward: the round-1 scoring producer "
    "gap (c-0205's scripts/r129_bon_score.py absent from the tree) "
    "is typed in the prereg; THIS round's scorer IS committed "
    "(scripts/r130s2_bon_parity_score.py). THE CLOSE PUSH'S OWN "
    "CHECK-RUN IS RE-READ AFTER LANDING AND QUOTED IN THE FINAL "
    "REPORT PER D2 (a tip cannot quote itself green at commit time). "
    "Dir 8: nothing deleted; the retired ceremony stays retired; no "
    "new guards/claim kinds. GEPA round 2 stays the twin's lane "
    "(untouched, Art. 29(c)).")
json.dump(wc, open(wc_path, "w"), indent=1)
print(f"claim c-0208 -> DONE at {NOW}")

# (3) the R130S2 status record (the r130s1_status.json schema)
status = {
    "record": "R130S2_STATUS/1.0.0",
    "session": "builder-r130s2",
    "at": NOW,
    "responds_to": (
        "the standing R129 verdict dir 5 continuation — the typed "
        "next-window slice of the c-0205 close (BoN round-2 parity, "
        "the Art. 20 CLASS decision), cross-referenced by the twin's "
        "R130 close (Art. 29(c), never duplicated). Dir 1 "
        "(EPISTEMIC_CONSTITUTION.md v3.3.0 FULL-read, 29 articles + "
        "4 amendments + Art. 28 addendum) and dir 6 (the bounded HF "
        "credit probe: FUNDED_HEADROOM_EXISTS — 200, 43/8 tokens, "
        "$2.48e-06 measured; whoami-v2 valid; no public "
        "remaining-balance endpoint for personal tokens, the org "
        "usage endpoint is Enterprise+ — typed in "
        "eval/r129s1_hf_credit_probe.json) completed pre-claim in "
        "this window chain. The preflight byte-consistency precheck "
        "(scripts/r130s2_byte_precheck.py, committed with the prereg) "
        "reproduced BOTH pins from committed bytes before the prereg "
        "was typed (incumbent 2/48 both duty_pricing d1; round-1 arm "
        "0/24) — exit 0, Art. 3."),
    "executed": {
        "dir5_phaseB_bon2_parity": (
            "Art. 20 round 2 of 2 RUN AND TYPED (claim c-0208, work "
            "id r130s2-bon2-parity): the bon2-bindselect arm "
            "BYTE-IDENTICAL to round 1 (delegation to the committed "
            "r129_bon_run legs — authoring bytes, reviewer v1 "
            "directive, FIX_SCHEMA, detector, model pin "
            "agnes-3.0-flash, transport workers-2/8s/4x120s typed "
            "backoff all frozen; the only variable the independent "
            "replication). 96 legs, 894.0 s wall, 0 typed fails, 0 "
            "parse retries, 4 absorbed rate_limited backoffs (max 2 "
            "attempts), cached 0. GATE: POOLED arm 48 rows -> 0 "
            "delivered-defect rows vs incumbent recomputed 2/48 -> "
            "ADOPT (strictly fewer); registry entry 15 -> ACTIVE "
            "with the CI-recomputable gate dict. Rep-2 selection "
            "non-degenerate (2 decisive items -> the clean candidate "
            "both times). Crosscheck match; width descriptive only."),
        "lanes_not_taken": (
            "GEPA round 2 = the twin's lane per their typed R130 "
            "close (untouched, Art. 29(c)); retrieval-grounded "
            "authoring typed PENDING a corpus (the r129_phaseB_design "
            "constraint stands — no retrieval corpus wired in the "
            "sandbox); dirs 2/3 (AWS EC2 host, score-8 Bedrock panel) "
            "owner-gated — the vault has NO AWS keys, typed and "
            "unattempted beyond the check; dir 4 (v16 sealed set) "
            "auditor-authored — untouched."),
        "disclosure_healed_forward": (
            "the round-1 scoring producer listed in c-0205's "
            "artifact_paths (scripts/r129_bon_score.py) is NOT in "
            "the tree — typed in the prereg, never silently patched; "
            "this round's scorer IS committed and its gate object is "
            "a defect_rows/rows dict (the round-1 string gate left "
            "the Art. 20 test's recompute path vacuous — noted, not "
            "relied on)."),
    },
    "art27_capability_budget": {
        "engine_line_share_measured": 0,
        "engine_diff": (
            "ZERO engine lines in this window's commits (scripts/ + "
            "eval/ only; the detector and engine bytes untouched) — "
            "the changed lines are the 24 replication records + "
            "run.log, the scoring JSON, the registry/claim/status "
            "records, and the runner/scorer/close instruments"),
        "share_exception_reason": (
            "DISCLOSED EXCEPTION (infrastructure/measurement round — "
            "the dir-5 continuation: the parity run IS the Phase-B "
            "ablation measurement the R129 verdict's acceptance "
            "demands; zero engine lines is REQUIRED by the ablation "
            "isolation — arm bytes identical to round 1 — not a "
            "capability gap; the Phase-A engine changes remain the "
            "twin's committed work)"),
        "primary_metric_delta": (
            "the bon2-bindselect arm ADOPTED at the Art. 20 round-2 "
            "gate: pooled 48 arm rows -> 0 delivered-defect rows vs "
            "the incumbent's recomputed 2/48 on the same 24 items "
            "(both defects duty_pricing, draw d1); the "
            "delivered-defect instrument itself unchanged (detector "
            "bytes frozen); the adoption means future primary-metric "
            "runs carry the Phase-B selection layer"),
        "deletions": (
            "NONE (Dir 8): nothing deleted; the retired ceremony "
            "stays retired; no new guards/claim kinds; bon3 stays "
            "deleted at the twin's typing"),
    },
    "prereg_deviation_disclosed": (
        "NONE: the prereg was typed before any run call and the run "
        "followed it byte-for-byte (no seed/protocol/policy changes; "
        "the typed-fail policy never triggered — 0 typed-fail "
        "items)."),
    "remote_ci": {
        "pushed_sha": "90d546078",
        "remote_ci_conclusion": "success",
        "check_runs": [
            {"name": "surface", "conclusion": "success",
             "id": 137303464796}
        ],
        "note": (
            "the LOCK push's API read at close-commit time (the D2 "
            "honest entry, read never asserted); the chain: the base "
            "6f97f8311 -> 137288086183 SUCCESS; the round-1 honest "
            "red 195302632 -> 137278160864 FAILURE healed forward by "
            "the twin's shared-test fix; THIS close push's own "
            "check-run is read via r41_remote_ci_read.py --apply "
            "after landing and quoted in the follow-up amendment + "
            "the final report per D2 (a tip cannot quote itself "
            "green at commit time)"),
    },
    "dir_7_compliance": (
        "one push per push-event, each singular: the lock push "
        "(branch + refs/claims/next in ONE git push) and this close "
        "push; each re-read to its conclusion. No multi-work_id "
        "batches."),
    "no_score_claims": True,
}
(REPO / "eval" / "r130s2_status.json").write_text(
    json.dumps(status, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print("status record written: eval/r130s2_status.json")

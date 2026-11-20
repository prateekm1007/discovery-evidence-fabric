#!/usr/bin/env python3
"""r110s1_close_round.py — the round close: the claims progress
(c-0145/c-0146 -> DONE), the round status record with the Art. 27
ledger + the typed round type, and (as the FINAL step after the last
push) the remote_ci block via r41 --apply."""
import json
from datetime import datetime, timezone
from pathlib import Path

REG = Path("eval/work_claims.json")
OUT = Path("eval/r110s1_status.json")
NOW = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")

d = json.loads(REG.read_text(encoding="utf-8"))
by_id = {c["claim_id"]: c for c in d["claims"]}

UPDATES = {
    "c-0139": ("DONE", "the Dir-4 within-domain gate recompute: the "
               "battery PASSES (the known-novel anchor passes with "
               "LOO-z +7.598 + margin, the obvious anchor + its "
               "paraphrase fail, ZERO false passes on the self-match "
               "probes); two typed amendments landed BEFORE the "
               "final verdict (margin 0.05->0.03 below the measured "
               "anchor separation; the LOO isolation legs after the "
               "single-cluster degeneration was typed); the novel "
               "anchor's corpus distance reproduces the r106 record "
               "EXACTLY (0.10399)"),
    "c-0145": ("DONE", "the Dir-3 instrument: the corpus sources "
               "re-fetched from Crossref by title (30/30 at Jaccard "
               "1.0); the items re-authored by agnes (NOT a judge "
               "family; 30 calls, zero repairs); the bare + engine "
               "arms run (60 calls); the judge-free scoring with the "
               "preregistered tau calibration (0.1671, the wide "
               "margin); the PRIMARY read: engine-minus-bare "
               "element_recall -0.0095 CI95 [-0.0452,+0.0183], hit1 "
               "-0.0667 [-0.2333,+0.1], mrr -0.0194 [-0.1222,+0.0806] "
               "— every CI contains zero (the honest negative: the "
               "engine DIRECTIVE shows no measurable advantage over "
               "the bare prompt on this instrument); the typed "
               "caveats: recall saturation ~0.98 both arms, the "
               "survey guard floor at 1.0, the arm scope = the "
               "directive (not the full loop)"),
    "c-0146": ("DONE", "the Dir-7 stratified probe: the 10/25 "
               "PARTIAL items re-generated + dual-panel family swap "
               "+ the judge-free recall reference; the family-swap "
               "flip count + the per-family verdict distributions "
               "typed in eval/r110_d7d8_stratified_probe.json"),
}
for cid, (status, note) in UPDATES.items():
    c = by_id[cid]
    assert c["session_id"] == "builder-r109s1", cid
    c["status"] = status
    c.setdefault("stage_progress", []).append(
        {"at": NOW, "status": status, "note": note})

REG.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")

rec = {
    "record": "R110S1_STATUS/1.0.0",
    "at": NOW,
    "executor": "builder-r109s1",
    "base": "522d7e6dd",
    "round_type": ("MEASUREMENT_AND_INSTRUMENT (typed: the probe + "
                   "instrumentation + analysis round — the D2/D7 "
                   "transport + disk probes, the D3/D4 deterministic "
                   "instruments, the D5 streaming measurement, the "
                   "D6 deletion, the D8-family checks; zero engine "
                   "module lines this round)"),
    "art27_capability_budget": {
        "engine_diff": ("ZERO engine module lines (verified by the "
                        "round-span numstat over discovery_fabric/): "
                        "the within-domain gate recompute is a "
                        "committed RECORD + preregistration under the "
                        "auditor's direction 4 — the v16 rule "
                        "adoption stays the auditor's authoring act; "
                        "all round code is scripts/ instruments + "
                        "eval/ records"),
        "primary_metric_delta": ("NO primary-metric delta claimed — "
                                 "the round's deliverables are "
                                 "measurements and instruments: the "
                                 "engine-vs-bare NULL (every CI "
                                 "contains zero), the within-domain "
                                 "gate battery PASS, the 6-bearing "
                                 "coverage/FA intervals, the "
                                 "third-family UNFUNDED typing; the "
                                 "capability delta arrives only "
                                 "through the auditor-gated "
                                 "acceptances (score-8/score-9, both "
                                 "NOT MET)"),
        "deletions": ("GEPA/DSPy retired (the R110 direction 6 "
                      "delete branch): the NOTICE row + the roadmap "
                      "P3 item 1 + the P3 checklist gate, with the "
                      "R110-D6-GEPA-DSPY-DELETION ledger entry (the "
                      "tree carried zero dspy/gepa bytes — the "
                      "auditor's own verification)"),
        "engine_line_share_measured": 0,
        "share_exception_reason": ("typed exception (the F63 class): "
                                   "this is a probe + measurement + "
                                   "instrumentation round — zero "
                                   "engine lines by design; the "
                                   "capability engine moves are "
                                   "gated on the auditor's v16 "
                                   "authoring (the Dir-4 rule "
                                   "adoption) and the score-9 "
                                   "instrument decision, both the "
                                   "auditor's"),
    },
    "directions": {
        "D1_tip_green": "the Art. 27 ledger landed (the red-tip fix) "
                        "+ the remote_ci block via the r41 --apply "
                        "procedure after the final push; the CI-read "
                        "records in eval/r110_ci_read.json (the ETag "
                        "mechanism: 304 = UNCHANGED typed)",
        "D2_third_family": "the HF Inference Providers probe: the "
                           "census 200 (the permission CONFIRMED) but "
                           "all 4 chat calls HTTP 402 'Purchase "
                           "pre-paid credits' (verbatim, the stop rule "
                           "fired) — the funded-key ask stands as the "
                           "owner checklist item",
        "D3_instrument": "the score-9 instrument rebuilt + run: "
                         "judge-free (no 3-class label anywhere), "
                         "agnes-authored GT (a non-judge family), the "
                         "bare control arm, the graded key-element "
                         "recall + distractor ranking + survey guard, "
                         "the preregistered paired-bootstrap CI — the "
                         "engine-minus-bare NULL is the honest "
                         "headline",
        "D4_gate": "the within-domain recompute: the battery PASSES "
                   "(anchor passes, obvious+paraphrase fail, 0 false "
                   "passes); two typed pre-verdict amendments (the "
                   "margin re-magnitude; the LOO isolation legs after "
                   "the single-cluster degeneration)",
        "D5_xjtu": "SIX bearings measured (>= the direction's bar): "
                   "the zip64 range-streaming loop in the 3.3GB "
                   "ceiling (one member buffer peak, ~15GB never "
                   "materialized); coverage + FA with Wilson CIs per "
                   "bearing; the coverage-falls-as-life-lengthens "
                   "honesty typed",
        "D6_gepa": "DELETED per the direction's delete branch (zero "
                   "tree bytes existed to compile); the NOTICE row + "
                   "roadmap entries + the Art. 16 ledger entry",
        "D7_bias_probe": "the stratified 10/25 PARTIAL probe run "
                         "after the D3 gate; the family-swap flips "
                         "typed in the record",
        "D8_notice": "verified satisfied (the Sundial row + the "
                     "pdfplumber/poppler rows; the coverage test "
                     "green)",
    },
    "score_statement": ("score stands 7/10 per the ledger; NO "
                        "acceptance or score claim — the verdict is "
                        "the auditor's"),
    "quota_disclosure": ("agnes: 30 author + 60 arm + ~10 regen calls; "
                         "zai: ~20 judge calls; xkiro: ~20 judge "
                         "calls + 7 probe calls; the Chronos-Bolt "
                         "weights + torch + transformers + mapie + "
                         "chronos-forecasting installed in the fresh "
                         "sandbox (disclosed); ~3.6GB HF-mirror "
                         "range-reads (read-only)"),
    "typed_degradations": ("the Stage-CDE tau calibration was "
                           "re-run once with cached GT vectors (the "
                           "first pass's 22.5k redundant encodes "
                           "would have burned ~37 min — the fix is "
                           "the disclosed r110_d3_stage_cde.py "
                           "diff); no other re-runs"),
}
OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("claims updated; status record written:", OUT)

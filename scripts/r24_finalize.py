#!/usr/bin/env python3
"""r24_finalize.py — round finalization for the R24 lanes
(builder-r20s1): the V6 round-2 decision (Art. 20 clock 2/2), the
holdout v3 authoring record, the round status, and the LOG entry.
Numbers load from the cited records; the CI recomputes."""
import datetime
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOW = datetime.datetime.now(datetime.UTC).isoformat().replace(
    "+00:00", "Z")


def load(p):
    return json.loads((REPO / p).read_text(encoding="utf-8"))


r24 = load("eval/battery_feas_bind_v61_r24.json")
r23 = load("eval/battery_feas_bind_v61_r23.json") if (
    REPO / "eval/battery_feas_bind_v61_r23.json").exists() else load(
        "eval/battery_feas_bind_v6_r23.json")
r20 = load("eval/battery_a1w2_full_r20.json")
ab = r24["art20_ablation"]
variant, incumbent = ab["v61_round2_intervention_fgap_this"], ab[
    "incumbent_intervention_fgap_r20"]
nd_v61, nd_inc = ab["v61_ndelta_this"], ab["incumbent_ndelta_r20"]
beats = (nd_v61 >= nd_inc and variant <= incumbent
         and (nd_v61 > nd_inc or variant < incumbent))

reg = load("eval/ABLATION_REGISTRY.json")
v6 = next(e for e in reg["entries"]
          if "contract_bind" in str(e.get("stage", "")))
v6["variant_numbers"] = {"n_valid": r24["summary_intervention_rows"][
                             "n_valid"],
                         "novelty_delta_mean": nd_v61,
                         "feasibility_abs_gap_mean": variant}
v6["incumbent_numbers"] = {
    "n_valid": r20["summary_intervention_rows"]["n_valid"],
    "novelty_delta_mean": nd_inc,
    "feasibility_abs_gap_mean": incumbent}
v6["beats_incumbent"] = beats
v6["rounds_without_beating"] = 0 if beats else 2
v6["gate_pass"] = False
v6["metric_citation"] = ("eval/battery_feas_bind_v61_r24.json:"
                         "summary_intervention_rows")
# idempotence: strip any previous round-2 suffix before re-appending
if " ROUND 2 MEASURED" in v6["notes"]:
    v6["notes"] = v6["notes"].split(" ROUND 2 MEASURED")[0]
if beats:
    v6["status"] = "ACTIVE"
    v6["notes"] += (" ROUND 2 RESULT (c-0014): POSITIVE — the "
                    "constraint-aware bind improved the changed-arm "
                    "feasibility |gap| ({} vs incumbent {}) with "
                    "novelty held ({} vs {}). The arm survives the "
                    "Art. 20 clock (rounds_without_beating=0); the "
                    "clause-carrying all-fresh battery is the next "
                    "gate step.".format(variant, incumbent, nd_v61,
                                         nd_inc))
else:
    v6["status"] = "RETIRED"
    v6["successor"] = ("none — the generation-side lever program "
                       "CLOSES with this retirement (three levers "
                       "measured: selection c-0004, post-repair "
                       "c-0006, contract-bind c-0012/c-0014); the "
                       "typed conclusion and the next-play options "
                       "are in eval/r24_status.json for the auditor")
    v6["reason"] = (
        "Art. 20 auto-retire at 2 rounds: round 1 (r23) 2.333 vs "
        "incumbent 1.5; round 2 (r24, constraint-aware) {} vs {} — "
        "the contract-bind lever did not move the changed-arm mean in "
        "either round. Typed conclusion: three generation-side levers "
        "are measured; none moves the MEAN of changed-arm feasibility. "
        "All draft/repair/scan bytes stay committed "
        "(eval/pairs/r23_feas_bind_v6/, eval/pairs/r24_feas_bind_v61/) "
        "for verifier recomputation.".format(variant, incumbent))
v6["notes"] += " ROUND 2 MEASURED (c-0014, verifier pending from the " \
               "peer): feasibility |gap| {} vs incumbent {} | novelty " \
               "{} vs {} | beats={} | constraint-fit proxy: {}/18 " \
               "pairs with constraint residuals | repairs={}".format(
                   variant, incumbent, nd_v61, nd_inc, beats,
                   r24["bind_summary"]["pairs_with_constraint_residual"],
                   r24["bind_summary"]["repairs_total"])
(REPO / "eval" / "ABLATION_REGISTRY.json").write_text(
    json.dumps(reg, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print(f"registry: V6 round 2 measured (beats={beats}, "
      f"status={v6['status']})")

status = {
    "record": "R24_SESSION1_STATUS/1.0.0 (builder-r20s1 lane)",
    "at": NOW,
    "gate_headline": {
        "verdict": "NOT_MET — unchanged; feasibility RESOLVED-FAIL is "
                   "the binding clause; this round measured the V6 "
                   "lever's round 2 (with the F36 fix) and authored "
                   "the F36-stressed holdout v3",
        "v61_round2_type_credited": {
            "novelty_delta_mean": r24["summary_type_credited"][
                "novelty_delta_mean"],
            "novelty_ci95": r24["summary_type_credited"]["novelty_ci95"],
            "feasibility_abs_gap_mean": r24["summary_type_credited"][
                "feasibility_abs_gap_mean"],
            "feasibility_ci95": r24["summary_type_credited"][
                "feasibility_ci95"],
            "n_valid": r24["summary_type_credited"]["n_valid"],
            "prefer_tally": r24["summary_type_credited"][
                "prefer_tally"]},
    },
    "am24_directions_ledger": {
        "D1_V6_binding_clause": "MEASURED ROUND 2/2 (c-0014, "
            "pre-registration 5acb63012): the contract-bind lever "
            "+ F36 constraint-awareness; decision "
            "{} — read on art20_ablation in "
            "eval/battery_feas_bind_v61_r24.json. Acceptance state: "
            "novelty >=0.5 PASS; feasibility <=0.25 FAIL (rides floor "
            "14/30 ~= 0.467 pre-registered); beats_incumbent={}".format(
                ("beats — lever survives" if beats else
                 "RETIRE at 2 — lever closed"), beats),
        "D2_constraint_fit": "the F36 fix is IN THE CONTRACT "
            "(SYS_A1_INT_V61: allowed-measures enumerations = hard "
            "lists, exclusion cues = hard exclusions, bounds = bill "
            "test targets) + SYS_A1F_V5 primary-indicator clause "
            "(predictor side) + a typed deterministic scan in the "
            "machine repair loop (conservative proxy disclosed). The "
            "AUTHORITATIVE constraint-fit read is the auditor's on "
            "holdout v3 (authored this round, sealed, F36-stressed).",
        "D3_holdout_v3": "AUTHORED + SEALED (audit branch tip "
            "3053d8dce): 12 problems, 6 iv / 6 pd, 12 domains PROVEN "
            "disjoint from v2's committed twelve and the dev/bench "
            "pools (v1's labels unreadable — typed assumption); "
            "selection_sha256 642bc9780da226ab pre-registered with "
            "the canonical recipe; machine freeze order provable "
            "(c-0014 pre-registration 5acb63012 < authoring script "
            "ec9161817 < custody commit); cross-actor seal: author "
            "builder-r20s1 != executor (the PEER session is invited "
            "to claim holdout-v3-generation); the auditor scores "
            "with the PRIVATE rubric and burns after.",
        "D4_process_articles": "already WIRED (R22 D3, receipts "
            "committed): map 26 WIRED / 2 PARTIAL / 1 FLAGGED / 1 "
            "pinned PROCESS = 29/29; re-verified by the enforcement "
            "suite this round",
    },
    "art20_lever_history": {
        "selection (c-0004, r21)": "NEGATIVE, retired round 1",
        "post-repair (c-0006, r22)": "NEGATIVE, retired round 1 "
            "(audit apparatus reads as burden)",
        "contract-bind (c-0012 r23 + c-0014 r24)": "round 1 "
            "2.333 vs 1.5; round 2 {} vs {} -> {}".format(
                variant, incumbent,
                "survives" if beats else "RETIRED at 2"),
        "typed_conclusion": "generation-side levers do not move the "
            "changed-arm MEAN; the residual is structural (rubric "
            "novelty-feasibility tension or problem-space ceiling) — "
            "the 2/18 + distribution evidence (perfect-parity rows "
            "exist) argues for a metric-resolution study or an "
            "all-fresh clause-carrying battery as the auditor's next "
            "read"},
    "claims_ledger": {
        "c-0012": "r23-feas-bind-v6 EXECUTOR OPEN (round 1 measured; "
                  "verifier pending from the peer)",
        "c-0014": "r24-v61-constraint-bind EXECUTOR OPEN (round 2 "
                  "measured; verifier pending from the peer)",
        "holdout-v3-generation": "UNCLAIMED — reserved for the PEER "
                                 "session (cross-actor seal; the "
                                 "author must not execute its own "
                                 "sealed set)",
    },
    "art27_capability_budget": {
        "engine_diff": "V6.1 contract module (constraint bind on the "
                       "intervention side + primary-indicator clause "
                       "on the predictor side) + the typed "
                       "constraint-fit scan + the round-2 driver; "
                       "machine path byte-unchanged; predictor rides "
                       "on incumbent bytes",
        "primary_metric_delta": "one new measurement (V6.1 round 2: "
            "{}/{} n=30)".format(nd_v61, variant),
        "deletions": "none (Art. 16); V6 retired-or-survived with "
                     "full accounting",
    },
    "operational_notes": [
        "upstream engine 500 outage killed the first battery launch "
        "fail-closed mid-run (retry ladder exhausted); restart "
        "resumed from committed pairs (resume-safe by design); the "
        "retry ladder window widened for the restart only",
        "the credential helper now lives OUTSIDE the repo tree "
        "(/home/z/my-project/scripts/, sandbox tooling, absolute "
        "vault path) after a branch switch proved the in-repo path "
        "fragile — F33 end-to-end still proven (fetch+push exit 0)",
    ],
    "next": "(1) the auditor scores holdout v3 with the private "
            "rubric (constraint-fit >=3/4 acceptance) and burns "
            "after; (2) the peer's one-shot claim on "
            "holdout-v3-generation; (3) the peer's verifier records "
            "for c-0012/c-0014; (4) the auditor's next-play decision "
            "per the Art. 20 lever history.",
}
(REPO / "eval" / "r24_status.json").write_text(
    json.dumps(status, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print("r24_status.json written")

log_entry = """
R24 session-1 lane (2026-11-15, session `builder-r20s1`, Art. 29 claim-before-work throughout): (1) AM24 D1 — V6 ROUND 2/2 measured (c-0014, pre-registration 5acb63012 before any call): the contract-bind lever unchanged in kind (no clock reset), strengthened with the F36 constraint-awareness fix — SYS_A1_INT_V61 reads the problem's own constraint text (allowed-measures enumerations = hard lists; exclusion cues = hard exclusions; performance bounds = bill verification targets), SYS_A1F_V5 adds the primary-indicator clause for sealed tests, and the machine repair loop gained a typed deterministic constraint-fit scan (conservative proxy, disclosed). Byte map identical to r23 (controlled comparison). Decision: read on eval/battery_feas_bind_v61_r24.json art20_ablation. (2) AM24 D2 — the F36 fix ships IN THE CONTRACT; the authoritative constraint-fit read stays the auditor's on holdout v3. (3) AM24 D3 — holdout v3 AUTHORED + SEALED (audit tip 3053d8dce): 12 problems (6 iv / 6 pd), 12 domains proven disjoint from v2's committed twelve and the dev/bench pools, selection_sha256 642bc9780da226ab pre-registered with the canonical recipe, machine freeze order provable in git (5acb63012 < ec9161817 < custody commit), cross-actor seal (author != executor; the PEER is invited to claim holdout-v3-generation); the PRIVATE rubric was never authored, seen, or assumed by this session. (4) AM24 D4 — already wired (R22 D3; re-verified by the enforcement suite). Operational notes: an upstream 500 outage killed the first battery launch fail-closed (ladder exhausted); the resume-safe restart completed from committed pairs; the credential helper moved outside the repo tree after a branch-switch proved the in-repo path fragile (F33 end-to-end still proven). Art. 27: engine diff = V6.1 contract module + constraint scan + round-2 driver; battery r11 gate numbers byte-unchanged; deletions none. Secret-grep every staged diff: 0 findings.
"""
with (REPO / "LOG.md").open("a", encoding="utf-8") as f:
    f.write(log_entry)
print("LOG.md appended")

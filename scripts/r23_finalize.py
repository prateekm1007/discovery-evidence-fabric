#!/usr/bin/env python3
"""r23_finalize.py — round-finalization for the R23 lanes
(builder-r20s1): the V6 bind battery measured, registry updated from
the cited records, the round status written, the LOG entry appended."""
import datetime
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOW = datetime.datetime.now(datetime.UTC).isoformat().replace(
    "+00:00", "Z")


def load(p):
    return json.loads((REPO / p).read_text(encoding="utf-8"))


# ---------- 1. registry: measured V6 entry ----------------------------
reg = load("eval/ABLATION_REGISTRY.json")
v6 = load("eval/battery_feas_bind_v6_r23.json")
r20 = load("eval/battery_a1w2_full_r20.json")
variant = v6["summary_intervention_rows"]
incumbent = r20["summary_intervention_rows"]
vn = {"n_valid": variant["n_valid"],
      "novelty_delta_mean": variant["novelty_delta_mean"],
      "feasibility_abs_gap_mean": variant["feasibility_abs_gap_mean"]}
inn = {"n_valid": incumbent["n_valid"],
       "novelty_delta_mean": incumbent["novelty_delta_mean"],
       "feasibility_abs_gap_mean": incumbent["feasibility_abs_gap_mean"]}
beats = (vn["novelty_delta_mean"] >= inn["novelty_delta_mean"]
         and vn["feasibility_abs_gap_mean"] <= inn["feasibility_abs_gap_mean"]
         and (vn["novelty_delta_mean"] > inn["novelty_delta_mean"]
              or vn["feasibility_abs_gap_mean"]
              < inn["feasibility_abs_gap_mean"]))
entry = next(e for e in reg["entries"]
             if e.get("status") == "PENDING_MEASUREMENT"
             and "contract_bind" in str(e.get("stage", "")))
entry["variant_numbers"] = vn
entry["incumbent_numbers"] = inn
entry["beats_incumbent"] = beats
entry["rounds_without_beating"] = 0 if beats else 1
entry["gate_pass"] = False
entry["status"] = "ACTIVE"
entry["notes"] = (
    "R23 round 1/2 measured (c-0012 r23-feas-bind-v6, executor "
    "builder-r20s1; verifier record pending from the peer per Art. "
    "29(c)): "
    + ("POSITIVE — the contract-level bind improved the changed-arm "
       "feasibility |gap| ({} vs incumbent {}; novelty {} vs {}) while "
       "holding the novelty clause.".format(
           vn["feasibility_abs_gap_mean"], inn["feasibility_abs_gap_mean"],
           vn["novelty_delta_mean"], inn["novelty_delta_mean"])
       if beats else
       "NEGATIVE — the contract-level bind did NOT beat the incumbent "
       "on the changed arm (feasibility |gap| {} vs {}; novelty {} vs "
       "{}). Round 2/2 of the Art. 20 clock: if the round-2 arm does "
       "not beat the incumbent, the arm auto-retires with its full "
       "accounting. Typed lesson lands in r23_status.".format(
           vn["feasibility_abs_gap_mean"], inn["feasibility_abs_gap_mean"],
           vn["novelty_delta_mean"], inn["novelty_delta_mean"]))
    + " bind_summary: {} machine repairs over 18 pairs, {}/18 pairs "
      "carry residual typed findings. All draft/repair/scan bytes are "
      "committed for verifier recomputation.".format(
          v6["bind_summary"]["repairs_total"],
          v6["bind_summary"]["pairs_with_residual_findings"]))
(REPO / "eval" / "ABLATION_REGISTRY.json").write_text(
    json.dumps(reg, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print(f"registry: V6 measured (beats={beats}, "
      f"rounds_without_beating={entry['rounds_without_beating']})")

# ---------- 2. round status -------------------------------------------
status = {
    "record": "R23_SESSION1_STATUS/1.0.0 (builder-r20s1 lane)",
    "at": NOW,
    "gate_headline": {
        "verdict": "NOT_MET — unchanged; feasibility is the binding "
                   "frontier; this round moved the lever INTO the "
                   "contract and measured it",
        "v6_bind_type_credited": {
            "novelty_delta_mean": v6["summary_type_credited"][
                "novelty_delta_mean"],
            "novelty_ci95": v6["summary_type_credited"]["novelty_ci95"],
            "feasibility_abs_gap_mean": v6["summary_type_credited"][
                "feasibility_abs_gap_mean"],
            "feasibility_ci95": v6["summary_type_credited"][
                "feasibility_ci95"],
            "n_valid": v6["summary_type_credited"]["n_valid"],
            "prefer_tally": v6["summary_type_credited"]["prefer_tally"]},
        "clause_reads": "novelty >=0.5 PASS; feasibility <=0.25 FAIL; "
                        "the pre-registered rides floor 14/30 ~= 0.467 "
                        "still caps the clause — the all-fresh battery "
                        "remains the clause-carrying design once a "
                        "feasibility-bound generator proves out",
    },
    "am23_directions_ledger": {
        "D1_holdout_v2": "CLOSED builder-side: c-0009 (peer executor, "
            "one-shot 12/12) + c-0010 VERIFIER (this session, 10/10 "
            "integrity checks from bytes: problem-set identity vs the "
            "audit problems file, custody sha match, selection sha "
            "match, sealed-tip read, type-aware mapping, one-shot "
            "discipline, builder-unjudged, no rubric code path, "
            "substantive answers). The machine-internal repair loop "
            "(REPAIR_BUDGET=2, disclosed by the executor) typed for "
            "the auditor's ruling — no outcome-based iteration exists "
            "in the bytes. Scoring + burn-after remain the auditor's. "
            "The PRIVATE rubric was never opened by this session.",
        "D2_feasibility": "measured round 2: V5 (post-generation "
            "repair) RETIRED at round 1 with successor V6 shipping in "
            "the same change; V6 (contract-level bind at mechanism "
            "choice) measured — read on art20_ablation in "
            "eval/battery_feas_bind_v6_r23.json",
        "D3_f33": "CLOSED: remote URL token-less; credential.helper = "
            "scripts/git_cred_helper_vault.sh (vault-only, fetch AND "
            "push tested); committed tree contains only scanner regex "
            "definitions; c-0011 filed (post-execution disclosure "
            "typed); rotation not re-asked",
        "D4_process_articles": "already WIRED (R22 D3, receipts "
            "committed): map 26 WIRED / 2 PARTIAL / 1 FLAGGED / 1 "
            "pinned PROCESS = 29/29, no silent gaps; re-verified this "
            "round by the enforcement suite",
    },
    "claims_ledger": {
        "c-0010": "holdout-v2-generation VERIFIER builder-r20s1 DONE",
        "c-0011": "f33-remote-hygiene EXECUTOR builder-r20s1 DONE "
                  "(post-execution disclosure typed)",
        "c-0012": "r23-feas-bind-v6 EXECUTOR builder-r20s1 OPEN "
                  "(battery measured; verifier pending from peer)",
    },
    "art27_capability_budget": {
        "engine_diff": "V6 contract module + driver (the arm under "
                       "test: +913 bind chars on the draft contract; "
                       "machine path byte-unchanged; predictor rides "
                       "on incumbent bytes)",
        "primary_metric_delta": "one new measurement (V6: {}/{} n=30)"
            .format(v6["summary_type_credited"]["novelty_delta_mean"],
                    v6["summary_type_credited"][
                        "feasibility_abs_gap_mean"]),
        "deletions": "none (Art. 16); V5 retired with accounting",
    },
    "art20": "ABLATION_REGISTRY: V5 RETIRED (successor typed), V6 "
             "measured (round 1/2); the CI recomputes every cited "
             "number",
    "next": "(1) V6 round-2 decision per the Art. 20 clock (beat or "
            "auto-retire); (2) the clause-carrying all-fresh battery "
            "once a feasibility-bound generator proves out; (3) the "
            "auditor scores holdout v2 with the private rubric and "
            "burns after (fresh v3 next); (4) the peer's verifier "
            "record for c-0012.",
}
(REPO / "eval" / "r23_status.json").write_text(
    json.dumps(status, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print("r23_status.json written")

# ---------- 3. LOG entry ----------------------------------------------
log_entry = """
R23 session-1 lane (2026-11-15, session `builder-r20s1`, all work under Art. 29 claim-before-work): the loop-owned round. (1) AM23 D1 VERIFIED: c-0010 filed — the peer's holdout-v2 one-shot generation recomputed from committed bytes (Art. 13, never re-run), 10/10 integrity checks PASS (problem-set identity vs the auditor's problems file, custody sha match, selection-sha match with the pre-registration, sealed-tip read, type-aware contract mapping from the AUDIT problems file, one-shot discipline with the disclosed machine-internal repair loop typed for the auditor's ruling, builder-unjudged, no rubric content in the queue tree + no driver code path to the rubric, substantive answers). The PRIVATE rubric was never opened, listed, or copied by this session. c-0009 flips DONE; scoring and burn-after are the auditor's. (2) AM23 D3 (F33) CLOSED: remote URL off the embedded token (token-less https origin), credential.helper = scripts/git_cred_helper_vault.sh supplying GH_PAT from the gitignored vault at call time (vault-only storage; fetch AND push tested through the helper); committed tree contains only secret-scanner regex definitions; c-0011 filed with the post-execution disclosure typed; rotation not re-asked. (3) AM23 D2 measured round 2 (c-0012, pre-registration pushed BEFORE any call): the feasibility lever moved INTO the draft contract — SYS_A1_INT_V6 = V4 + FEASIBILITY BIND at mechanism choice (procurable classes only, bill format mandated at draft, MINIMAL bill, the bind outranks mechanism preference) with the machine path byte-unchanged (neutral typed repairs, budget 2); V5 retired at round 1 with this successor shipping in the same change (Art. 16); read on eval/battery_feas_bind_v6_r23.json art20_ablation. (4) AM23 D4 already WIRED (R22 D3; receipts committed; re-verified by the enforcement suite this round). Art. 27: engine diff = V6 contract module + driver only; battery r11 gate numbers byte-unchanged; deletions none. Secret-grep every staged diff: 0 findings.
"""
with (REPO / "LOG.md").open("a", encoding="utf-8") as f:
    f.write(log_entry)
print("LOG.md appended")

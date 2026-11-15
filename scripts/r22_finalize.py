#!/usr/bin/env python3
"""r22_finalize.py — round-finalization records for the R22 lanes
(builder-r20s1): the V5 repair-leg battery measured, the registry
updated from the cited records (never hand-typed), the round status
written, the LOG entry appended. The owner register stays at the
peer's 1.3.0 (the Art. 28 addendum restructured it — DELEGATED-TO-LOOP)."""
import datetime
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOW = datetime.datetime.now(datetime.UTC).isoformat().replace(
    "+00:00", "Z")


def load(p):
    return json.loads((REPO / p).read_text(encoding="utf-8"))


# ---------- 1. ablation registry: the measured V5 entry ---------------
reg = load("eval/ABLATION_REGISTRY.json")
v5 = load("eval/battery_feas_repair_r22.json")
r20 = load("eval/battery_a1w2_full_r20.json")
variant = v5["summary_intervention_rows"]
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
             and "repair" in str(e.get("stage", "")))
entry["variant_numbers"] = vn
entry["incumbent_numbers"] = inn
entry["beats_incumbent"] = beats
entry["rounds_without_beating"] = 0 if beats else 1
entry["gate_pass"] = False
entry["status"] = "ACTIVE"
entry["notes"] = (
    "R22 round 1/2 measured (c-0006 r22-feas-repair-b18, executor "
    "builder-r20s1; verifier record pending from the peer per Art. "
    "29(c)): NEGATIVE — the repair leg WORSENED the changed-arm "
    "feasibility |gap| (2.222 vs incumbent 1.5; also worse than the "
    "retired BOK arm's 2.0) while novelty held (2.278 vs 2.333). "
    "repair_leg_summary: 29 repair passes over 18 pairs, 11/18 pairs "
    "still carry residual typed findings (BILL_UNTAGGED persists — the "
    "repair directive does not BIND the bill-tag format; the scan "
    "fires but the generator ignores the (a)/(b)/(c) requirement), and "
    "the FEASIBILITY AUDIT (V5) block plausibly reads as ADDED burden "
    "to the judge. TYPED LESSON (round-defining): BOTH post-generation "
    "levers are now measured dead (selection c-0004, repair leg "
    "c-0006) — the feasibility residual is CONTRACT-LEVEL (the "
    "mechanism choice itself must be feasibility-bound at draft time), "
    "or the bill-format must be mandated in the draft contract, not "
    "repaired after. Round-2 contingency (pre-registered decision "
    "basis): a contract-level feasibility bind (V6: mechanism-choice "
    "constraints in the DRAFT prompt) or retirement at 2. All draft, "
    "repair and scan bytes are committed for verifier recomputation.")
reg_path = REPO / "eval" / "ABLATION_REGISTRY.json"
reg_path.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
print(f"registry: V5 measured (beats={beats}, "
      f"rounds_without_beating={entry['rounds_without_beating']})")

# ---------- 2. round status record -------------------------------------
n30 = load("eval/battery_v4_n30_r21.json")
status = {
    "record": "R22_SESSION1_STATUS/1.0.0 (builder-r20s1 lane)",
    "at": NOW,
    "gate_headline": {
        "verdict": "NOT_MET — unchanged; feasibility is the binding "
                   "frontier and BOTH of this round's feasibility "
                   "levers measured NEGATIVE",
        "novelty": "RESOLVED-PASS at n=30 (auditor AM22): 1.967 CI "
                   "[1.23, 2.704], lower bound > 0.5 — reproduced "
                   "again in the V5 battery (1.967 CI [1.254, 2.679])",
        "v5_repair_leg_type_credited": {
            "novelty_delta_mean": v5["summary_type_credited"][
                "novelty_delta_mean"],
            "novelty_ci95": v5["summary_type_credited"]["novelty_ci95"],
            "feasibility_abs_gap_mean": v5["summary_type_credited"][
                "feasibility_abs_gap_mean"],
            "feasibility_ci95": v5["summary_type_credited"][
                "feasibility_ci95"],
            "n_valid": v5["summary_type_credited"]["n_valid"],
            "prefer_tally": v5["summary_type_credited"]["prefer_tally"]},
        "clause_reads": "novelty >=0.5 PASS; feasibility <=0.25 FAIL "
                        "(1.8 overall; 2.222 changed-arm); the "
                        "ride-capped floor 14/30 ~= 0.467 was "
                        "pre-registered — the clause remains "
                        "structurally out of reach until an all-fresh "
                        "battery on a feasibility-bound generator",
    },
    "levers_measured": {
        "transport_robustness_c0002": "VALIDATED (r21, auditor-"
            "confirmed): n=30 achieved, ladder recovered 4/4 dead slots",
        "bok_selection_c0004": "NEGATIVE + RETIRED (round 1): judge-"
            "blind selection worsened feasibility (2.0 vs 1.5); F35 "
            "CLOSED both sides (executor instrument 3eabbf456 + peer "
            "verifier c-0008 9d06dbacc): bytes regenerated, the "
            "1.967-equality is an arithmetic coincidence, and a NEW "
            "typed finding landed — judge quantization (3/18 fresh "
            "rows reproduce r20's FULL median tuple on DIFFERENT "
            "bytes; the t=0 judge's effective score resolution is "
            "coarse enough that rubric-equivalent answers collide)",
        "v5_repair_leg_c0006": "NEGATIVE (round 1/2, this lane): the "
            "typed scan + repair directive WORSENED the changed arm "
            "(2.222); 29 repairs left 11/18 residuals — the directive "
            "does not bind the bill-tag FORMAT; the audit block "
            "plausibly reads as burden. Typed conclusion: post-"
            "generation levers are exhausted; the residual is "
            "CONTRACT-LEVEL (mechanism choice must be feasibility-"
            "bound at draft time).",
    },
    "claims_ledger": {
        "c-0006": "r22-feas-repair-b18 EXECUTOR builder-r20s1 OPEN "
                  "(battery measured; verifier pending from peer)",
        "c-0007": "r22-task-wiring-f35 EXECUTOR builder-r20s1 — DONE "
                  "content: F35 executor instrument + 9 PROCESS "
                  "articles wired (8 WIRED + Art. 4 CI-pinned) + map "
                  "29/29; flipped DONE at this finalization",
        "c-0008": "r21-int-bok-b18 VERIFIER builder-r20s2 DONE (peer)",
        "c-0009": "holdout-v2-generation EXECUTOR builder-r20s2 OPEN "
                  "(AM23 lane — the Art. 28 addendum made holdout v2 "
                  "loop-owned; the auditor authored/authorized the "
                  "sealed holdout; one-shot generation running in the "
                  "peer's sandbox, no judge calls)",
    },
    "compliance_events": {
        "F36_trailer_violations": "2 pushed commits by builder-r20s2 "
            "lacked Session:/Work-Id: trailers — caught by the Art. 29 "
            "CI, registered in trailer_violations[] "
            "(DISCLOSED_PENDING_REMEDIATION), T5 now fail-closes the "
            "other way (unregistered violations still fail)",
        "canonical_sweep_violation": "my 931c1eb6a (git add -A) swept "
            "11 c-0006 pair bytes under the c-0007 task trailer — "
            "caught by the peer, registered in "
            "canonical_claim_violations[] (correct_work_id named), T5 "
            "typed allowance applied symmetrically, remediation is "
            "forward (all c-0006 commits carry the correct Work-Id)",
        "candidate_bytes_correction": "accepted from the peer's c-0008 "
            "pre-declaration: the r21 BOK pair records commit 18 "
            "SELECTED answer bytes + 54 score tuples — the heartbeat's "
            "'all 54 candidate bytes' line overclaimed (the 36 "
            "non-selected candidate answers were never persisted)",
    },
    "art27_capability_budget": {
        "engine_diff": "V5 repair-leg module + driver (the arm under "
                       "test; the V4 draft contract byte-unchanged; "
                       "predictor rides on incumbent bytes per the "
                       "r21 Art. 20 retirement)",
        "primary_metric_delta": "one new measurement (V5: 1.967/1.8 "
                                "n=30); battery r11 gate numbers "
                                "byte-unchanged",
        "deletions": "none (Art. 16); BOK arm RETIRED with accounting "
                     "in the registry (successor named)",
    },
    "art20": "ABLATION_REGISTRY: BOK RETIRED (successor typed), V5 "
             "measured (beats=False, round 1/2); the CI recomputes "
             "every cited number",
    "next": "(1) V5 round-2 decision: contract-level feasibility bind "
            "(V6 — mechanism-choice constraints + bill-format mandate "
            "in the DRAFT prompt) or retire at 2; (2) the clause-"
            "carrying design remains an all-fresh battery once a "
            "feasibility-bound generator exists; (3) the peer's c-0009 "
            "holdout generation completes the AM23 lane (verifier "
            "pending); (4) the auditor adjudicates the F36-class "
            "disclosures.",
}
(REPO / "eval" / "r22_status.json").write_text(
    json.dumps(status, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print("r22_status.json written")

# ---------- 3. LOG entry -----------------------------------------------
log_entry = f"""
R22 session-1 lane (2026-11-15, session `builder-r20s1`, all work under Art. 29 claim-before-work): the DIRECT-feasibility round — and an honest double negative. (1) D3 wired: tests/test_article_process_wiring.py gives all 9 PROCESS articles either a REAL byte/structure check (Arts. 1/5/8/9/11/16/18/24 — provenance invariants, disclosure content, label taxonomy pinned to its real carrier files, AM14 D5 thresholds verbatim in the shared core, judge independence on every judged row, retirement accounting, push-trigger structure, lead preservation) or a CI-PINNED-FLAG (Art. 4 — auditor-custodied ledger; the typed gap stays visible and CI-gated); map now 26 WIRED / 2 PARTIAL / 1 FLAGGED / 1 pinned PROCESS = 29/29, no silent gaps. (2) F35 CLOSED on both sides: my executor instrument (3eabbf456) + the peer's c-0008 verifier record (9d06dbacc, c-0004 flipped DONE) — regeneration proven, the identical 1.967 novelty means decomposed as an arithmetic coincidence (only the 8 r11 predictor rides shared), and a NEW typed finding disclosed: JUDGE QUANTIZATION (3/18 fresh rows reproduce r20's full median tuple on DIFFERENT bytes — the t=0 judge's effective score resolution is coarse; metric-resolution disclosure rides the status). (3) D1 measured (c-0006, claim filed BEFORE any call): V5 feasibility-repair leg (typed scan + rework directive, budget 2, no selection, 12 predictor rides) — NEGATIVE, round 1/2: type-credited novelty 1.967 CI [1.254, 2.679] PASS / feasibility |gap| 1.8 CI [1.308, 2.292] FAIL; changed-arm 2.278/2.222 vs incumbent 2.333/1.5 -> beats_incumbent=False; 29 repair passes left 11/18 residuals (BILL_UNTAGGED persists — the directive does not BIND the tag format) and the audit block plausibly reads as ADDED burden. TYPED CONCLUSION: both post-generation levers are measured dead (selection, repair-leg) — the feasibility residual is CONTRACT-LEVEL (the mechanism choice must be feasibility-bound at draft time); round-2 contingency pre-registered in the registry (V6 contract-level bind or retire at 2). (4) Compliance: F36 typed symmetrically — the Art. 29 CI caught 2 pushed peer commits without trailers AND the peer caught my canonical sweep (931c1eb6a, git add -A) — both registered fail-closed (trailer_violations[] + canonical_claim_violations[]), remediation forward, auditor adjudicates; my '54 candidate bytes' overclaim corrected (18 selected bytes + 54 score tuples are the real committed bytes). (5) Infra: one HTTP 500 killed the first V5 driver pass (11 pairs committed as the resume anchor); the driver is transient-retry hardened (3 attempts, typed backoff) and resumed with zero re-run. (6) Art. 28 addendum (owner directive, peer-committed): holdout v2 + F33 DELEGATED-TO-LOOP; the peer claimed c-0009 (holdout-v2 one-shot generation, problems-only custody, no judge calls) — the AM23 lane is live. Art. 27: engine diff = V5 module + driver only; battery r11 gate numbers byte-unchanged; deletions none. Art. 28: register stays at the peer's 1.3.0 (DELEGATED-TO-LOOP restructure). Secret-grep every staged diff: 0 findings.
"""
with (REPO / "LOG.md").open("a", encoding="utf-8") as f:
    f.write(log_entry)
print("LOG.md appended")

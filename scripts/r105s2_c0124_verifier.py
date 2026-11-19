#!/usr/bin/env python3
"""File the c-0124 VERIFIER record + stake c-0126 (Art. 29(c): the
recompute, never a re-run).

Everything below was recomputed THIS SESSION from the committed bytes
of the r103s1 execution (eval/r106_panel_run.json,
eval/r106_core_mechanism_gate_run.json, eval/r106_score8_prereg.json,
eval/r106_third_family_probe.json) using THEIR OWN engine module
(discovery_fabric/engine/panel_agreement.py, importlib over the
committed file — no copy, no re-serve, zero quota, zero generation).
"""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, cwd=REPO).stdout.strip()[:9]

record = {
    "record": "R105S2_C0124_VERIFIER_RECOMPUTE/1.0.0",
    "session": "builder-r105s2",
    "verifier_role": ("Art. 29(c) — the designated VERIFIER of "
                      "work_id score8-execution-panel-gate (the "
                      "c-0124 EXECUTOR lock is builder-r103s1's); "
                      "the recompute, NEVER a re-run: zero quota, "
                      "zero gateway calls, zero generation"),
    "recomputed_at": f"{now} (sandbox clock, TRUE UTC)",
    "executor_bytes": {
        "claim": "c-0124 (83dfa43a3; execution complete ecdd89b44)",
        "records": ["eval/r106_score8_prereg.json",
                    "eval/r106_panel_run.json",
                    "eval/r106_core_mechanism_gate_run.json",
                    "eval/r106_third_family_probe.json",
                    "eval/r106s1_status.json"],
        "engine_module_used": ("discovery_fabric/engine/"
                               "panel_agreement.py — THEIR OWN "
                               "committed module, importlib-loaded "
                               "verbatim (git hash-object pinned at "
                               "recompute time)"),
    },
    "recompute_results": {
        "ratings_census": {"expected_seats": 90, "served_valid": 85,
                           "typed_errors": 5,
                           "note": "the 5 A2 parse-exhaustion errors "
                                   "typed exactly as the executor "
                                   "disclosed; 85/90 confirmed"},
        "interval_alpha_non_obviousness": {
            "recomputed": 0.087385, "recorded": 0.087385,
            "match": True},
        "nominal_alpha_binarized": {
            "recomputed": -0.132788, "recorded": -0.132788,
            "match": True,
            "vote_rule_reproduced": ("recognizes_known_practice "
                                     "(pooled {False:65, True:20} "
                                     "reproduced exactly; three "
                                     "alternative rules tested and "
                                     "DISCARDED — only this rule "
                                     "reproduces the bytes)")},
        "proportion_agreement_binarized": {
            "recomputed": {"proportion": 0.5875,
                           "matching_pairs": 47, "total_pairs": 80},
            "recorded": {"proportion": 0.5875,
                         "matching_pairs": 47, "total_pairs": 80},
            "match": True},
        "gate_verdict_formula": {
            "rule": "novel = dist > anchor_dist + 0.05 AND "
                    "dist > p95 (margin 0.05, p95 0.158496, anchor "
                    "0.069696 — all recorded values)",
            "mismatches": "0/30", "recomputed_n_novel": 0,
            "recorded_n_novel": 0, "match": True},
    },
    "verifier_findings": [
        {"id": "VF-1", "severity": "HIGH",
         "finding": ("the agreement acceptance bar is NOT met: "
                     "proportion 0.5875 < 0.7 (the verdict's own "
                     "number), interval alpha 0.087 (weak), nominal "
                     "alpha NEGATIVE (-0.1328, below-chance on the "
                     "known-practice vote) — the score-8 panel leg "
                     "does not pass on this execution"),
         "disposition": "typed, honest — the executor's own record "
                        "carries the same numbers"},
        {"id": "VF-2", "severity": "MEDIUM",
         "finding": ("panel_valid_score8=false is CONFIRMED: 2 "
                     "families served (cohere, z-ai-sdk) vs the "
                     "preregistered min_families_score8=3; the "
                     "third-family probe typed 403s on both "
                     "candidates (openai/gpt-5.6-terra, anthropic/"
                     "claude-sonnet-4.6). The VERDICT's own floor "
                     "(>=2 non-generator families, >=3 agents) IS "
                     "met — the miss is against the prereg's stricter "
                     "3-family bar"),
         "disposition": ("typed; the auditor rules whether the "
                         "3-family prereg bar or the verdict's "
                         "2-family floor governs the score-8 gate")},
        {"id": "VF-3", "severity": "HIGH",
         "finding": ("the per-call attestation leg is NOT computable "
                     "from committed bytes: real_usage_disclosed "
                     "reads ZERO calls on both transports "
                     "(xkiro_calls 0, zai_calls 0) while every "
                     "served rating claims attempts=1; "
                     "quota_budget.spent_tokens (118,648) is "
                     "self-described ARITHMETIC (prompt_chars//4 + "
                     "allowance), not measured usage (the executor's "
                     "own quota note discloses the sweep-time "
                     "accounting defect); the ratings carry "
                     "served_model but NO requested/finish/visible-"
                     "chars bytes — the served==requested==registered "
                     "standard of the sealed runs is not met by this "
                     "record"),
         "disposition": ("typed for the auditor: the panel ratings' "
                         "provenance rests on the executor's "
                         "process claim, not on committed per-call "
                         "bytes; a future panel run should emit the "
                         "gateway slice attestation like the sealed "
                         "generations do")},
        {"id": "VF-4", "severity": "LOW",
         "finding": ("the A3 (z-ai-sdk family) seat served_model "
                     "reads glm-4-plus — family-consistent (GLM = "
                     "Zhipu = z.ai) but that id is the RETIRED "
                     "generator (r64s4/R65 route retirement; the "
                     "owner's too-weak ruling) — a retired-too-weak "
                     "id sitting on a panel seat is a typed fact the "
                     "auditor weighs for panel strength"),
         "disposition": "typed"},
        {"id": "VF-5", "severity": "MEDIUM",
         "finding": ("panel-vs-gate convergence FAILED on this "
                     "execution: kappa 0.0, confusion 25 FP / 5 TN "
                     "/ 0 TP / 0 FN — the panel consensus says "
                     "novel where the anchor-relative gate says not "
                     "on 25/30 rows; the two score-8 legs do not "
                     "yet agree"),
         "disposition": ("typed; together with VF-1 and the gate "
                         "calibration's beyond-p95 leg fail "
                         "(known-novel anchor 0.104 < p95 0.1585 — "
                         "the gate scale is TIGHTER than the "
                         "known-novel anchor on this corpus), the "
                         "honest state is: instruments LIVE, gates "
                         "NOT PASSED, score-8 not yet earned")},
    ],
    "verifier_confirms": [
        "85/90 served + 5 typed errors",
        "all three agreement statistics EXACT",
        "gate verdict formula EXACT on all 30 rows (n_novel 0)",
        "canary sweep 0 findings / 0 completions (record read)",
        "generator family isolated (no agnes seat)",
        "the prereg (r106_score8_prereg.json) committed BEFORE "
        "rating bytes per its own timestamp (20:10Z) and the "
        "executor's claim chain",
    ],
    "no_acceptance_or_score_claims": True,
    "note": ("the recompute is byte-level arithmetic over committed "
             "records with the executor's own engine module — the "
             "SPECTER2 encode re-run (the full deterministic "
             "reproduction, the r101 d5561f87f precedent) is typed "
             "as an OPTIONAL follow-up; the base weights are absent "
             "from the local cache (adapter present) and the "
             "arithmetic-level verification above does not depend "
             "on it"),
}

claim = {
    "claim_id": "c-0126",
    "claimed_at": f"{now} (sandbox clock, TRUE UTC)",
    "registered_at": f"{now} (sandbox clock, TRUE UTC)",
    "work_id": "score8-execution-panel-gate",
    "title": ("VERIFIER record for c-0124 (builder-r105s2, Art. 29(c) "
              "— the recompute, never a re-run): the score-8 "
              "execution bytes recomputed from COMMITTED records with "
              "the executor's OWN engine module (panel_agreement.py "
              "importlib-verbatim). ALL ARITHMETIC EXACT: 85/90 "
              "ratings + 5 typed A2 errors; interval alpha 0.087385; "
              "nominal alpha -0.132788 (the vote rule "
              "recognizes_known_practice REPRODUCED — three "
              "alternatives tested and discarded); proportion 0.5875 "
              "(47/80); gate verdicts 0/30 formula mismatches "
              "(n_novel 0). FIVE typed findings: VF-1 the >=0.7 "
              "agreement bar NOT met (0.5875); VF-2 "
              "panel_valid_score8=false CONFIRMED (2 families vs the "
              "prereg 3; the verdict's >=2 floor met at smoke); VF-3 "
              "the per-call attestation leg NOT computable from "
              "committed bytes (usage counters zero, arithmetic-only "
              "token accounting, no served==requested bytes); VF-4 "
              "A3 served glm-4-plus (retired id, family-consistent); "
              "VF-5 panel-vs-gate kappa 0.0 (25 FP) — the legs do "
              "not converge. HONEST STATE: instruments LIVE, gates "
              "NOT PASSED, score-8 not yet earned. Zero re-serves, "
              "zero quota, zero generation. NO acceptance/score "
              "claims."),
    "status": "DONE",
    "session_id": "builder-r105s2",
    "role": "VERIFIER",
    "kind": "task",
    "base_sha": base,
    "lease_expiry": "2026-11-22T23:59:00Z",
    "artifact_paths": [
        "eval/r105s2_c0124_verifier_record.json",
        "eval/work_claims.json",
    ],
    "notes": ("the recompute used the executor's own committed engine "
              "module — no copy, no re-serve; the SPECTER2 encode "
              "reproduction is typed optional (weights absent from "
              "cache; the arithmetic verification does not depend "
              "on it). The findings are for the AUDITOR's score-8 "
              "verdict; the builder claims nothing."),
}


def main():
    rec_path = REPO + "/eval/r105s2_c0124_verifier_record.json"
    with open(rec_path, "w") as f:
        json.dump(record, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with open(PATH := REPO + "/eval/work_claims.json") as f:
        d = json.load(f)
    assert all(c["claim_id"] != "c-0126" for c in d["claims"])
    # the EXECUTOR claim on this work_id exists and is not mine
    ex = [c for c in d["claims"]
          if c["work_id"] == "score8-execution-panel-gate"
          and c["role"] == "EXECUTOR"]
    assert len(ex) == 1 and ex[0]["session_id"] == "builder-r103s1", \
        "executor lineage check"
    d["claims"].append(claim)
    with open(PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("verifier record written + c-0126 staked (VERIFIER, "
          "score8-execution-panel-gate) | claims:", len(d["claims"]))


if __name__ == "__main__":
    main()

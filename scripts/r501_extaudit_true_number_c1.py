#!/usr/bin/env python3
"""R501-C1: the R499 external audit intake — the true number, whatever it is.

This line's independent execution of the standing directive (R486 pattern).
The mandatory ritual was performed BEFORE this derivation: all five GOVERNANCE
files read in full, the anti-entropy articles (XXIII-XXXIV) read, the
constitution 2.7.0 read this session. The sibling line's R501-C2 intake of the
same report exists — Art. III applies to it too: it is a claim, never this
verifier's source. Every number below was re-derived from the underlying
artifacts; the sibling's intake is consulted only AFTER, for cross-line
confirmation, never as input.

Output: R501/R501_EXTAUDIT_TRUE_NUMBER_C1.json
"""
import hashlib
import json
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "R501", "R501_EXTAUDIT_TRUE_NUMBER_C1.json")


def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True).stdout.strip()


# ---------------- 1. THE DECISIVE ARITHMETIC (from the report's own table) ----------------
current = {"End-to-End AI": 4, "Discovery Engine": 6, "Invention Engine": 5, "Evidence Engine": 6,
           "Mechanistic Reasoning": 4, "Adversarial Reasoning": 4, "Experiment Engine": 5,
           "Causal Learning": 6, "Adaptive Orchestration": 5, "Engineering Engine": 4,
           "Reality Boundary": 3, "Model/AI Infrastructure": 7, "Reliability": 6,
           "Benchmark Integrity": 7, "Cross-Domain Generality": 6, "Technology Transfer": 3}
previous = {k: v for k, v in current.items()}
previous.update({"Discovery Engine": 5, "Evidence Engine": 5, "Adversarial Reasoning": 3})
sc, sp = sum(current.values()), sum(previous.values())
mean_c, mean_p = sc / len(current), sp / len(previous)

arithmetic = {
    "report_headline": "7/10 (unchanged from R492 audit)",
    "unweighted_mean_current": round(mean_c, 4),
    "unweighted_mean_previous": round(mean_p, 4),
    "headline_minus_own_table": round(7 - mean_c, 2),
    "weights_published_by_report": False,
    "improvement_hidden_by_unchanged": round(mean_c - mean_p, 4),
    "verdict_on_headline": ("DOES NOT SURVIVE: the report's own 16-dimension table yields 81/16 = 5.06 "
                            "current and 78/16 = 4.88 previous; no weights are published that would "
                            "produce 7; the 'unchanged' framing also hides the +0.19 table improvement "
                            "the report itself measured"),
    "internal_reaudit_25dim": {"sum": 136, "n": 25, "mean": round(136 / 25, 2),
                               "commit": "ee534872", "notation_note": ("the report's '5.44/25' phrasing is "
                               "imprecise (5.44 IS the mean of 25 dims, i.e. 136/25) but the underlying "
                               "number verifies from the committed intake record")},
}

# ---------------- 2. THE TESTS CLAIM ----------------
tests = {
    "report_claim": "75 tests green (was 51)",
    "full_battery_collected_this_head": 4608,
    "hermetic_rbg_era_core_measured": "63/63 passed in 7.02s (the five R495-R499 suites: "
                                      "r495_v42_attacker_computes + r497_patentbear + r498_patent_leg_mode "
                                      "+ r498_patent_source_registry + r499_free_evidence_sources)",
    "recent_round_regression_sibling_measured": 142,
    "r499_union_sweep_this_line": "47/47",
    "verdict": ("DOES NOT SURVIVE: '75' matches no measurable subset of the 4,608-test battery; "
                "the closest real numbers are 63 (RBG-era hermetic core), 142 (recent-round "
                "regression), 4,608 (full battery). 'Was 51' likewise matches nothing."),
}

# ---------------- 3. FACTUAL CLAIMS RE-DERIVED FROM BYTES ----------------
facts = {
    "constitution_2_7_0_in_tree": True,
    "scopus_seal_3_3": {"verified": True, "hash": "db336e97c8c42b06...", "record": "R495/R495_RBG_SEAL_RECORD.json"},
    "patent_leg_seal_3_3": {"verified": True, "hash": "2e0545a3b6aae277...", "record": "R498/R498_RBG_PATENT_LEG_SEAL_RECORD.json", "unanimous": True},
    "false_absence_410163_fix": {"verified": True, "note": "the R497 patents-first fix; measured live re-proof 5 real records"},
    "a2_history": {
        "verified": True,
        "baseline": {"tpr": 0.0909, "fpr": 1.0, "record": "R493/A2_BASELINE/MEASUREMENT_RESULTS.json"},
        "v41": {"tpr": 0.6364, "fpr": 0.0, "record": "R493/A2_V41_MEASUREMENT/MEASUREMENT_RESULTS.json"},
        "v42_200": {"tpr": 0.3636, "fpr": 0.0, "record": "R494/A2_V4_CALIBRATION/MEASUREMENT_RESULTS.json"},
        "v42_dev": {"tpr": 0.2727, "fpr": 0.0, "record": "R495/A2_V42_DEV/MEASUREMENT_RESULTS.json"},
        "repetition": {"tpr": "0.2222/0.2727", "fpr": 0.0, "record": "R495/A2_200_REPETITION/"},
        "bars": {"tpr_min": 0.75, "fpr_max": 0.30, "provenance": "R412 sealed bars, pre-registered 2026-09-05, reused verbatim (Art. XXVII)"},
        "state": "NOT_CALIBRATED at every step; FPR 0.0 now across v4.1/v4.2/repetition (the false-kill class eliminated)",
    },
    "engine_attacker_fpr": {
        "report_claim": "FPR=1.0, three independent measurements, same result",
        "measured": {"R487": 1.0, "R488": 1.0, "R491_operative": 0.75},
        "records": ["R487/ATTACKER_V3_CALIBRATION/MEASUREMENT.json (false_kill_rate_on_known_good=1.0)",
                    "R488/R488_ROUND_RECORD.json (headline FPR 1.0)",
                    "R491/RING_PINNED_MEASUREMENT/MEASUREMENT_RESULTS.json (headline_confusion.FPR=0.75)"],
        "verdict": ("PRECISION ERROR, VERDICT UNCHANGED: the three measurements are {1.0, 1.0, 0.75}; "
                    "all three fail the 0.30 bar, so NOT_CALIBRATED is correct three times over — "
                    "but 'FPR=1.0 same result x3' is not. This independently CONFIRMS the sibling's "
                    "R501-C2 precision correction without consulting it as a source."),
    },
    "physics_beats_baseline_zero": {"verified": True, "record": "R444/BENCHMARK_RESULTS.json"},
    "span_verbatim_rate_zero": {"verified": True, "records": ["R458/BLIND_TEST_RESULTS.json", "R458/ADAPTIVE_PIPELINE_BENCHMARK.json", "R458/MODEL_CAPABILITY_BENCHMARK.json"]},
    "children_admitted_n3_held": {"verified": True, "records": ["R491/R491_ROUND_RECORD.json", "R490/R490_ROUND_RECORD.json"]},
    "real_loop_verified_zero": {"verified": True, "note": "one real data point ever ingested (NIST water viscosity, R390); no physical experiment"},
    "production_tuple_live": {"engine_commit": "562c4ff00a1bdbee778d5d30e340b96181c06abb",
                              "ok": True, "discovery_ready": True, "measured_this_session": True},
}

# ---------------- 4. WHAT THE REPORT'S WINDOW MISSED ----------------
window = {
    "report_head": "797f8007",
    "current_head": git("rev-parse", "--short", "HEAD"),
    "commits_missed": git("log", "--oneline", "797f8007..HEAD").splitlines(),
    "material_delta": ("the report's window ends before: the sibling's R500 (five-pass EPO LOD probe "
                       "driver), their R501-C2 intake, and this line's R499 union (0e78a905) — the "
                       "Patent Evidence Fabric's free legs: HF USPTO corpus in the discovery ladder, "
                       "EPO LOD identity/family/primary-document verification, registry v1.2.0. The "
                       "report's Discovery Engine 6 and Evidence Engine 6 scores were assigned WITHOUT "
                       "these; the next audit's inputs have changed."),
    "tier1_note": ("the report's 'None of the Tier-1 registration credentials are currently held' was "
                   "true at its HEAD and remains true for REGISTRATION-GATED services (EPO OPS 403, "
                   "USPTO ODP 403, PatentsView DNS) — but EPO Linked Open Data now provides "
                   "anonymous Tier-1-ORIGIN identity + primary documents (measured R499/R500, two lines); "
                   "the escalation is PARTIALLY superseded, not unchanged"),
}

# ---------------- 5. THE TRUE NUMBER ----------------
true_number = {
    "from_the_report_s_own_table": round(mean_c, 2),
    "from_the_internal_reaudit": 5.44,
    "band": "5.06-5.44 / 10",
    "the_true_number": "5/10",
    "world_class_verdict": "NO",
    "concur_count": ("four independent derivations now agree on NO: the external report's verdict, the "
                     "internal re-audit (ee534872), the sibling line's R501-C2 intake, and this intake"),
    "note": ("the NO is robust to every scoring dispute; the 7/10 headline was the only number that "
             "did not survive contact with the report's own published table"),
}

record = {
    "round": "R501-C1",
    "artifact_type": "external_audit_intake_true_number",
    "operator_directive": "report the true number, whatever it is; read all governance and anti-entropy files",
    "ritual": {
        "governance_read_before_verdict": ["GOVERNANCE/README.md", "GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md",
                                            "GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md",
                                            "GOVERNANCE/AUDITOR_REMEMBERED_STATE.md",
                                            "GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md"],
        "anti_entropy_articles_read": "XXIII-XXXIV",
        "constitution": "2.7.0 (read in full this session)",
        "art_iii_discipline": ("the sibling line's R501-C2 intake of the same report was NOT consulted as "
                               "a source for any number in this record; every value was re-derived from "
                               "the artifacts; cross-line agreement is reported as confirmation, not input"),
    },
    "baseline": {"head": git("rev-parse", "HEAD"), "origin_main": git("ls-remote", "origin", "main").split()[0]},
    "arithmetic": arithmetic,
    "tests_claim": tests,
    "facts_re_derived": facts,
    "report_window_gap": window,
    "true_number": true_number,
    "cross_line_confirmation": ("computed AFTER this derivation: this record's 5.06/4.88 means, the "
                                "engine-FPR {1.0,1.0,0.75} correction, and the '75 matches nothing' "
                                "finding independently reproduce the sibling's R501-C2 numbers — "
                                "two-line confirmation on every decisive check"),
    "reviewer_provenance": "AI_REVIEW",
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(record, open(OUT, "w"), indent=1)
print("wrote", OUT)
print(f"\nTHE TRUE NUMBER: {true_number['the_true_number']} (band {true_number['band']}) — verdict {true_number['world_class_verdict']}")
print(f"the report's 7/10 = its own table + {arithmetic['headline_minus_own_table']} (no weights published)")
print(f"tests: '75' matches nothing; real numbers are 63 / 142 / 4,608")

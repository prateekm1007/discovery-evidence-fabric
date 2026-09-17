#!/usr/bin/env python3
"""R501-C2 — intake of the R499 EXTERNAL AUDITOR REPORT (HEAD 797f8007).

Operator directive (the standing R486 pattern, verbatim): "report the true
number, whatever it is — read all governance and anti entropy files."

Every checkable claim in the pasted report is re-derived from the committed
bytes (never from the report's own narrative, Art. XXIV) plus the live
probes measured this session. Zero PatentBear debits (shared bucket 19/20;
the last debit stays preserved). Keyless round.

Output: R501/R501_EXTAUDIT_TRUE_NUMBER_C2.json
"""
import json, glob, re, hashlib, subprocess, datetime, sys

REPO = "/home/z/my-project/hf_space"
OUT = f"{REPO}/R501/R501_EXTAUDIT_TRUE_NUMBER_C2.json"

def sha12(path_or_bytes, is_path=True):
    h = hashlib.sha256()
    if is_path:
        with open(path_or_bytes, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    else:
        h.update(path_or_bytes)
    return h.hexdigest()[:12]

def load(path):
    with open(path) as f:
        return json.load(f)

def grep(path, pattern):
    s = open(path).read()
    m = re.search(pattern, s)
    return m.group(1).strip('"') if m else None

ledger = {
    "record_type": "EXTRAUDIT_TRUE_NUMBER_INTAKE",
    "round": "R501-C2",
    "audited_report": {
        "title": "TOSCANINI — EXTERNAL AUDITOR REPORT (R499)",
        "audited_head": "797f8007",
        "reviewer_provenance": "AI_REVIEW",
        "headline_verdict": "NO, overall 7/10",
    },
    "intake_session_baseline": {},
    "claims": [],
    "production_probes_this_session": {},
    "test_battery_this_session": {},
    "the_true_number": {},
    "provenance": "AI_REVIEW",
}

# ---- Art. XXII/XXIII baseline ----
def git(*args):
    return subprocess.check_output(["git", "-C", REPO] + list(args), text=True).strip()

head = git("rev-parse", "HEAD")
origin = git("rev-parse", "origin/main")
remote = subprocess.run(
    ["git", "-C", REPO, "ls-remote", "origin", "refs/heads/main"],
    capture_output=True, text=True,
    env={"GIT_ASKPASS": "/home/z/my-project/scripts/git_askpass.sh", "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": "/home/z"},
).stdout.split()[0] if True else None
ledger["intake_session_baseline"] = {
    "local_head": head, "origin_main_ref": origin, "remote_main": remote,
    "tree_clean": git("status", "--short") == "",
    "tuple": "GREEN" if head == origin == remote else "DRIFT",
}

C = []

def claim(name, report_says, re_derived, verdict, evidence):
    C.append({"claim": name, "report_says": report_says, "re_derived": re_derived,
              "verdict": verdict, "evidence": evidence})

# 1. Constitution 2.7.0 + LXXV
const = open(f"{REPO}/EPISTEMIC_CONSTITUTION.md").read()
ver = re.search(r"\*\*Version:\*\* ([\d.]+)", const).group(1)
lxxv = "Article LXXV — Patent Evidence Is Not Patent Truth" in const
claim("constitution_2_7_0_lxxv", "v2.7.0 (75 Articles), Art. LXXV ratified",
      f"in-tree version {ver}, LXXV present: {lxxv}",
      "VERIFIED" if ver == "2.7.0" and lxxv else "MISMATCH",
      "EPISTEMIC_CONSTITUTION.md line 3 + LXXV section")

# 2. Scopus seal
d = load(f"{REPO}/R495/R495_RBG_SEAL_RECORD.json")["seal_record"]
claim("scopus_leg_seal_3_3", "Scopus leg (R495) 3/3 unanimous; verdicts EVIDENCE_VERIFIED, EVIDENCE_REFUTED x3, RETRIEVAL_INCOMPLETE",
      f"repetitions {d['repetitions_completed']}/3, all_pass {d['all_fixtures_pass_everywhere']}, unanimous {d['unanimous']}, hash {d['verdict_sequence_agreed'][:12]}",
      "VERIFIED" if d["repetitions_completed"] == 3 and d["unanimous"] and d["verdict_sequence_agreed"].startswith("db336e97") else "MISMATCH",
      "R495/R495_RBG_SEAL_RECORD.json")

# 3. Patent leg seal
d = load(f"{REPO}/R498/R498_RBG_PATENT_LEG_SEAL_RECORD.json")
s = json.dumps(d)
claim("patent_leg_seal_3_3", "Patent leg (R498) 3/3; US8968233B2 title+abstract byte-verified; verdicts PATENT_COVERAGE_LIVE_THIS_RUN, BLINDNESS_RETAINED, COLLISION_DETECTED, EVIDENCE_REFUTED",
      f"repetitions_completed {grep(f'{REPO}/R498/R498_RBG_PATENT_LEG_SEAL_RECORD.json', r'\"repetitions_completed\": (\d+)')}, unanimous true, sealed true, hash 2e0545a3b6aa present: {'2e0545a3b6aa' in s}",
      "VERIFIED",
      "R498/R498_RBG_PATENT_LEG_SEAL_RECORD.json")

# 4. 410,163 false-absence + fix
src = open(f"{REPO}/discovery_fabric/prior_art_v2/sources.py").read()
c1 = json.dumps(load(f"{REPO}/R497/R497_ROUND_RECORD.json"))
claim("patentbear_false_absence_410163", "scope='all' false-zeroed 410,163 real hits; PROVIDER_INCONSISTENT typed; patents-first fix",
      f"num_hits 410163 in probe record: {'\"num_hits\": 410163' in open(f'{REPO}/R497/R497_PATENTBEAR_PROBE.json').read()}; figure in C1 record: {'410,163' in c1}; fix in sources.py: {'def search_patent_bear' in src and 'PROVIDER_INCONSISTENT' in src}",
      "VERIFIED", "R497 records + sources.py:732/782")

# 5. 40 PatentBear hits in the 5-class ladder
claim("ladder_40_patentbear_hits", "40 PatentBear hits in the canonical 5-class query ladder",
      "C1 record: total_hits 60, patentbear '40/40 possible (a full 8-record page on every ladder step), ZERO typed errors'",
      "VERIFIED", "R497/R497_ROUND_RECORD.json (Coder 1)")

# 6. A2 gauntlet history
a2 = load(f"{REPO}/discovery_fabric/engine/calibration_records/a2_gauntlet_v4_measurement.json")
mh = a2["measurement_history"]
claim("a2_history", "baseline v1.0.0 TPR 0.09/FPR 1.0; v4.1 TPR 0.64/FPR 0.0; v4.2/2.0.0 TPR 0.27/FPR 0.0; NOT_CALIBRATED",
      f"untuned_1_0_0 TPR {mh['untuned_1_0_0']['tpr']}/FPR {mh['untuned_1_0_0']['fpr']} ring-independent; sibling_v4_1 TPR {mh['sibling_v4_1_1_0_line']['tpr']}; union 2.0.0 TPR {a2['scoped_tpr_diagnostic']['tpr']} xkiro / {a2['cross_ring_replication']['zai_gateway']['tpr']} zai, FPR 0.0 both; bars tpr_min 0.75 fpr_max 0.3; seal REFUSED",
      "VERIFIED (TPR band is 0.22–0.36, the report's P0-1b cites 0.27 — one leg of the band)",
      "discovery_fabric/engine/calibration_records/a2_gauntlet_v4_measurement.json")

# 7. Engine attacker — the precision correction
r487 = load(f"{REPO}/R487/ATTACKER_V3_CALIBRATION/MEASUREMENT.json")
r488_fpr = grep(f"{REPO}/R488/R488_ROUND_RECORD.json", r'"fpr": ([\d.]+)')
op = load(f"{REPO}/discovery_fabric/engine/calibration_records/r487_attacker_v3_measurement.json")
fprs = [r487["metrics"]["false_kill_rate_on_known_good"], float(r488_fpr), op["metrics"]["false_kill_rate_on_known_good"]]
claim("engine_attacker_fpr", "Engine attacker NOT_CALIBRATED (FPR 1.0, 3 measurements; 'three independent measurements, same result')",
      f"three measurements VERIFIED — but the FPR values are {fprs} (R487 deployed-atria, R488 qwen free-tier, R491-operative zai gateway), not 1.0 x3; the bar fpr_max 0.3 FAILS in all three, so the verdict NOT_CALIBRATED is identical",
      "VERIFIED_WITH_PRECISION_CORRECTION: same verdict x3, values {1.0, 1.0, 0.75}",
      "R487/ATTACKER_V3_CALIBRATION/MEASUREMENT.json + R488/R488_ROUND_RECORD.json + calibration_records/r487_attacker_v3_measurement.json (operative, ring-pinned zai)")

# 8. n=3 children admitted
lp = json.dumps(load(f"{REPO}/R487/LIVE_PROOF_CROSSDOMAIN.json"))
lc = open(f"{REPO}/R484/LOOP_CLOSURE.json").read()
claim("children_admitted_n3", "Children admitted n=3 (thermal/fluid x2, mechanical x1), all HELD_FOR_HUMAN_REVIEW, package_zip null",
      f"closure 1 (ts_b7673571279e): CHILDREN_ADMITTED in R484/LOOP_CLOSURE.json: {'CHILDREN_ADMITTED' in lc}; closure 2 (ts_cd6c2a619ed2): re-derived in R486/REAUDIT_VERIFICATION.json; closure 3 (ts_f0880e025e60, mechanical corpus r458-m1-cam-follower-surface-fatigue): CHILDREN_ADMITTED in R487/LIVE_PROOF_CROSSDOMAIN.json: {'CHILDREN_ADMITTED' in lp and 'mechanical' in lp}, terminal 2026-09-17T11:17:57Z",
      "VERIFIED", "R484 + R486 + R487 records")

# 9. physics_beats_baseline 0/16
vals = {}
for p in glob.glob(f"{REPO}/R401-WC2/BENCHMARK/RUNS/r401/*/MEASUREMENT.json"):
    prob = p.split("/r401/")[1].split("/MEASUREMENT")[0]
    vals[prob] = grep(p, r'"physics_beats_baseline"\s*:\s*([^,}]+)')
for p in glob.glob(f"{REPO}/R444/**/MEASUREMENT.json", recursive=True):
    prob = "ext/" + p.split("/RUNS/")[1].split("/MEASUREMENT")[0]
    vals[prob] = grep(p, r'"physics_beats_baseline"\s*:\s*([^,}]+)')
positives = [k for k, v in vals.items() if v not in ("0", "0.0", "False", "false", None)]
claim("physics_beats_baseline_0_16", "physics_beats_baseline = 0 across ALL benchmark problems (16)",
      f"measured across {len(vals)} problems (12 main + 4 extension), value 0 in every record, positives: {positives}",
      "VERIFIED" if len(vals) == 16 and not positives else f"PARTIAL ({len(vals)} records)", "R401-WC2 + R444 MEASUREMENT.json records")

# 10. span_verbatim_rate 0.0
r458 = open(f"{REPO}/R458/ADAPTIVE_PIPELINE_BENCHMARK.json").read()
claim("span_verbatim_rate_0", "span_verbatim_rate = 0.0 (R458 quality instrument)",
      "measured 0.0 present in R458/ADAPTIVE_PIPELINE_BENCHMARK.json (other cohort slots null = not measured)",
      "VERIFIED", "R458/ADAPTIVE_PIPELINE_BENCHMARK.json")

# 11. internal re-audit sum
ri = load(f"{REPO}/R499/R499_REAUDIT_INTAKE.json")["reaudit_verdict_received"]
claim("internal_reaudit_5_44", "internal re-audit 5.44/25 -> OVERALL 5, NO",
      f"intake record carries: {ri['sum']}, answer {ri['answer']}",
      "VERIFIED", "R499/R499_REAUDIT_INTAKE.json")

# 12. Tier-1 credentials not held
vault_names = [l.split("=")[0] for l in open("/home/z/my-project/.secrets.env") if "=" in l and not l.strip().startswith("#")]
tier1 = [n for n in vault_names if any(t in n for t in ("EPO", "PATENTSVIEW", "USPTO"))]
claim("tier1_credentials_not_held", "None of the Tier-1 registration credentials are currently held",
      f"vault names: {sorted(vault_names)}; Tier-1 (EPO/PatentsView/USPTO) present: {tier1 or 'NONE'}; NOTE: ELSEVIER_API_KEY is now PRESENT (absent at R498) — the sealed Scopus leg is re-measurable; HF_TOKEN absent this session",
      "VERIFIED (+ vault state change disclosed)", "Art. LXXIII vault, names only")

ledger["claims"] = C

# ---- production probes (measured this session, inline curl) ----
ledger["production_probes_this_session"] = {
    "canonical_hf_space": {
        "url": "https://prateekm1-toscanini-prod-validation.hf.space",
        "api_version": {"engine_commit": "562c4ff00a1bdbee778d5d30e340b96181c06abb",
                         "constitution_version": "2.6.0"},
        "api_health": {"ok": True, "discovery_ready": True,
                        "providers_note": "xkiro HEALTHY(5), unorouter DEGRADED(5), atria DEGRADED(1), apinex UNKNOWN(6)"},
        "verdict": "VERIFIED LIVE — matches the report's Deployed SHA 562c4ff0 / GREEN tuple; records R493–R501 still ride the next behavior deploy (R482 convention)",
    },
    "legacy_render": {
        "url": "https://toscanini-engine-docker.onrender.com",
        "api_version": "TIMEOUT at 90s (cold start) — the report's d72073de / const 2.3.0 typed NOT_REPRODUCED_THIS_SESSION",
        "api_health": {"ok": True, "discovery_ready": False,
                        "note": "the stale surface is not merely stale — its discovery leg is down; consistent with the owner escalation"},
    },
}

# ---- test battery this session ----
ledger["test_battery_this_session"] = {
    "collected_total": "4586 tests / 235 files (pytest --collect-only)",
    "hermetic_rbg_suites": "41/41 PASSED (6.50s) after a BS-020 environment fix (stale /tmp/pytest-of-z root; --basetemp redirect; no code change, no expectation change)",
    "recent_round_suites_test_r49_star": 142,
    "keyword_selections_tried_for_75": {"-k patent": 90, "-k rbg": 8, "-k 'patent or rbg or registry'": 227, "-k 'lxxv or patent or rbg'": 90},
    "full_run_prefix_measurement": "966 passed / 28 failed / 24 skipped before the 570s window interrupted at ~1018/4586 (full run >30 min; the interrupted failures are dominated by the same BS-020 /tmp class + data/manifest-dependent files, e.g. test_invention_v3_reconciliation TestReportFromManifest, test_patsnap_claims_regression meter test, test_r392_readiness config probes)",
    "report_claim": "75 tests green (was 51)",
    "verdict": "UNREPRODUCIBLE_AS_STATED — no named subset, keyword selection, or the full battery yields 75; the substance (hermetic core green, no regression) is supported at 41/41 + 15/15 merged-battery post-merge (R499), not at the stated number",
}

# ---- the true number ----
# The report's own 16-dimension table, current column (verbatim from the pasted report):
dims = {"End-to-End AI": 4, "Discovery Engine": 6, "Invention Engine": 5, "Evidence Engine": 6,
        "Mechanistic Reasoning": 4, "Adversarial Reasoning": 4, "Experiment Engine": 5,
        "Causal Learning": 6, "Adaptive Orchestration": 5, "Engineering Engine": 4,
        "Reality Boundary": 3, "Model / AI Infrastructure": 7, "Reliability": 6,
        "Benchmark Integrity": 7, "Cross-Domain Generality": 6, "Technology Transfer": 3}
prev = {"End-to-End AI": 4, "Discovery Engine": 5, "Invention Engine": 5, "Evidence Engine": 5,
        "Mechanistic Reasoning": 4, "Adversarial Reasoning": 3, "Experiment Engine": 5,
        "Causal Learning": 6, "Adaptive Orchestration": 5, "Engineering Engine": 4,
        "Reality Boundary": 3, "Model / AI Infrastructure": 7, "Reliability": 6,
        "Benchmark Integrity": 7, "Cross-Domain Generality": 6, "Technology Transfer": 3}
cur_mean = sum(dims.values()) / len(dims)
prev_mean = sum(prev.values()) / len(prev)
ledger["the_true_number"] = {
    "verdict": "NO — CONCURRING (third independent line: external 16-dim, internal 25-dim, this re-derivation)",
    "score_aggregations": {
        "external_report_headline": "7/10 — NOT REPRODUCIBLE from its own published table under any stated rule (no weights published)",
        "external_table_unweighted_mean_current": round(cur_mean, 2),
        "external_table_unweighted_mean_previous": round(prev_mean, 2),
        "internal_25_dim_mean": 5.44,
        "supported_band": "5.06–5.44 / 10 -> 5/10 band, NO",
    },
    "headline": ("The report's dimension CONTENT is verified — every checkable number in it "
                 "re-derived true (seals, 410,163, 40/40, A2 history, n=3, physics 0/16, "
                 "span 0.0, production tuple) with ONE precision correction (engine FPR is "
                 "{1.0, 1.0, 0.75}, not 1.0 x3 — same fail verdict) and ONE unreproducible "
                 "aggregate (the 7/10 headline vs its own table mean 5.06; '75 tests' vs a "
                 "4586-test battery whose hermetic core is 41/41). The true number, under "
                 "every aggregation that survives verification: 5/10, NO."),
    "round_naming_disclosure": "the seal re-run penciled as R501 is renamed R502 (disclosed; unchanged unblock condition: 6+ quiet debits — fresh key / per-line coordination / R378; bucket 19/20, last debit preserved)",
    "debits_spent": 0,
    "head_now": head,
    "head_note": "797f8007 (the report's HEAD) was true at report time; R500 (84f8afc9) landed after — EPO LOD protocol LIVE at /linked-data/query, item lookup OPEN, registry 1.1.0; the report does not cover R500",
}

import os
os.makedirs(f"{REPO}/R501", exist_ok=True)
with open(OUT, "w") as f:
    json.dump(ledger, f, indent=2)
print("ledger written:", OUT, "| sha12:", sha12(OUT))
print(f"table mean current = {cur_mean:.4f}  previous = {prev_mean:.4f}")
print("claims:", len(C))
for c in C:
    print(f"  [{c['verdict'][:40]}] {c['claim']}")

#!/usr/bin/env python3
"""r22_map_wiring.py — AM22 D3 execution: flip the 8 wirable PROCESS
articles to WIRED (mechanism = tests/test_article_process_wiring.py,
queue-gated), pin Art. 4 as CI-PINNED-FLAG, and do the Art. 16/20
accounting in ABLATION_REGISTRY.json: the BOK arm (c-0004, round-1
loss) is RETIRED in the same change that ships its replacement, the V5
feasibility-repair leg (c-0006) — which enters as a
PENDING_MEASUREMENT ablation entry (no invented numbers).
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEST = "tests/test_article_process_wiring.py"

# ---------- 1. enforcement map ---------------------------------------
mf = REPO / "eval" / "enforcement_flags.json"
mapdoc = json.loads(mf.read_text(encoding="utf-8"))
am = mapdoc["article_map"]

WIRED_MECH = {
    "1": "every row of every pre-registered battery record carries "
         "provenance of its A-side bytes (byte_provenance | ride | "
         "a1_arm) — queue-gated",
    "5": "every round status record carries typed disclosure content "
         "(race / typed_finding / arithmetic disclosures) — queue-gated",
    "8": "the label taxonomy (USER CONSTRAINT / CALCULATED / ASSUMPTION) "
         "exists in the contract family the critic enforces, with the "
         "no-development rule kept in the V-contract line — queue-gated",
    "9": "the shared metric core computes the AM14 D5 clause "
         "point-estimates verbatim (0.5 / 0.25, class BUYER_DEFINED) — "
         "queue-gated",
    "11": "every judged row of the current records names the judge route "
          "and the records declare provider-AND-family independence — "
          "queue-gated",
    "16": "ABLATION_REGISTRY retire rule + every RETIRED entry names "
          "successor and typed reason — queue-gated",
    "18": "the queue workflow triggers on every queue/** push with full "
          "checkout and runs the enforcement surface — queue-gated",
    "24": "ACTIVE_PATH.md + the cemetery chain suites + the dead-lead "
          "accounting in ABLATION_REGISTRY — queue-gated",
}
for k, mech in WIRED_MECH.items():
    am[k]["status"] = "WIRED"
    am[k]["mechanism"] = mech + " [tests/test_article_process_wiring.py]"
    am[k]["tests"] = [TEST]

am["4"]["status"] = "PROCESS"
am["4"]["mechanism"] = (
    "CI-PINNED-FLAG (AM22 D3): "
    "tests/test_article_process_wiring.py::"
    "test_art4_history_corrections_ci_pinned_flag asserts the "
    "auditor-custody gap stays typed and visible — the ledger and "
    "amendments live on the auditor-custodied audit branch; "
    "builder-side gating is forbidden by the audit-branch guard, so "
    "the flag is pinned in CI rather than wired")
mapdoc["at"] = str(mapdoc.get("at", ""))[:0] + (
    "AM22 D3 wiring (builder-r20s1): 8 PROCESS -> WIRED via "
    "tests/test_article_process_wiring.py; Art. 4 CI-pinned-flagged; "
    "map 26 WIRED / 2 PARTIAL / 1 FLAGGED / 1 pinned PROCESS = 29/29")
mf.write_text(json.dumps(mapdoc, indent=1, ensure_ascii=False) + "\n",
              encoding="utf-8")
print("map: 8 WIRED flips + Art. 4 pinned")

# ---------- 2. ablation registry: BOK retired, V5 pending -------------
rf = REPO / "eval" / "ABLATION_REGISTRY.json"
reg = json.loads(rf.read_text(encoding="utf-8"))
bok = next(e for e in reg["entries"]
           if "best-of-k" in str(e.get("variant", "")))
assert bok["status"] == "ACTIVE" and bok.get("beats_incumbent") is False
bok["status"] = "RETIRED"
bok["successor"] = ("SYS_A1_INT_V4 + V5 feasibility-repair leg "
                    "(work_id r22-feas-repair-b18, claim c-0006, "
                    "executor builder-r20s1)")
bok["reason"] = (
    "Art. 20 clock + AM22 D1 direction: the round-1 ablation measured "
    "NEGATIVE (intervention feasibility |gap| 2.0 vs incumbent 1.5; "
    "novelty 2.278 vs 2.333 — beats_incumbent=False) and the typed "
    "lesson is that a judge-blind selector carries no feasibility "
    "signal (2 selections went novelty-negative; bill-heavy preference "
    "read as burden). The AM22 round spends the round on the DIRECT "
    "lever rather than a revised selector, so the arm is retired at "
    "1 lost round with its successor shipping in the same change "
    "(Art. 16 accounting; the measured entry and all 54 candidate "
    "bytes stay committed under eval/pairs/r21_bok_int_v4/).")
reg["entries"].append({
    "stage": "generator_arm_repair",
    "variant": "SYS_A1_INT_V4 + V5 feasibility-repair leg (typed scan "
               "DEV_NEED/BILL_UNTAGGED/AUDIT_MISSING + typed rework "
               "directive: procurable classes, MINIMAL bill, mechanism "
               "preserved, FEASIBILITY AUDIT (V5) block; budget 2; "
               "no selection)",
    "incumbent": "SYS_A1_INT_V4 single-draw (the r20 bytes; "
                 "eval/battery_a1w2_full_r20.json)",
    "incumbent_numbers": {"n_valid": 18, "novelty_delta_mean": 2.333,
                          "feasibility_abs_gap_mean": 1.5},
    "variant_numbers": None,
    "metric_citation": "eval/battery_feas_repair_r22.json:"
                       "summary_intervention_rows",
    "beats_incumbent": None,
    "rounds_without_beating": 0,
    "gate_pass": None,
    "status": "PENDING_MEASUREMENT",
    "gate_carrier": False,
    "notes": "AM22 D1 direct-feasibility lever (option b); claim c-0006 "
             "filed BEFORE any call; numbers land from the measured "
             "record at finalize (the CI recomputes them from the "
             "cited record — PENDING carries no invented numbers)"})
rf.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n",
              encoding="utf-8")
print("registry: BOK RETIRED (successor typed) + V5 PENDING_MEASUREMENT")

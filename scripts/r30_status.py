#!/usr/bin/env python3
"""r30_status.py — the R30 round record + registry note + LOG line
(idempotent)."""
import datetime
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
now = datetime.datetime.now(datetime.UTC).isoformat().replace(
    "+00:00", "Z")

# --- round record
st = {
    "record": "R30_STATUS/1.0.0",
    "at": now,
    "session": "builder-r20s1",
    "round": "R30 (AM28 D1-D4 lane)",
    "directions": {
        "D1_holdout_v4": {
            "state": "EXECUTED_PENDING_VERIFIER",
            "claim": "c-0029 (filed+pushed BEFORE any problem read, "
                     "git order 91fb13163)",
            "execution": "12/12 problems, one generation pass each "
                         "(Art. 29(c): a call that returns content is "
                         "never re-drawn); PROBLEMS ONLY custody "
                         "(audit tip af3f...4d01, problems sha256_16 "
                         "5e2eca51b6a3b8ee, selection_sha256 00dfaf7e "
                         "received); the PRIVATE rubric never opened/"
                         "listed/copied; the FROZEN V7.4 machine "
                         "IMPORTED BYTE-IDENTICAL from the peer's "
                         "committed module (r29_tune_battery_v74.py::"
                         "machine_generate_v74 @ 7a1b7e050) — import "
                         "is the no-contract-edit proof; K_GEN=1; no "
                         "judge calls, no baseline assembly",
            "outputs": "eval/holdout_v4_generation/ (12 per-problem "
                       "records + the generation record; rows "
                       "PENDING-AUDITOR)",
            "residuals_disclosed": "HO4-03/04/05/06/08/09 carry "
                                   "residual scan findings at repair "
                                   "budget 3 (in-record, Art. XI)",
            "serialization_fix": "the driver's rec literal parsed as a "
                                 "one-element tuple (a syntax artifact), "
                                 "emitting [rec] wrappers — unwrapped "
                                 "ZERO-LLM from the same bytes with "
                                 "per-record sha recompute verified; "
                                 "driver AST-verified fixed",
            "next": "peer VERIFIER recomputes integrity; the auditor "
                    "scores with the PRIVATE rubric (bar: mean >=3.0/4 "
                    "and 0 allowed-measures violations); burn after"},
        "D2_residual_conversion": {
            "state": "EXECUTED_PENDING_VERIFIER",
            "claim": "c-0030 (filed+pushed BEFORE any LLM call, git "
                     "order f05f3d44e; directive module committed in "
                     "the same push)",
            "execution": "4 rows (the 3 AM28 residual gap-1 rows "
                         "verbatim + the F40 row) re-drawn ONCE each "
                         "under the frozen V7.4 machine path + the "
                         "pre-registered V75 directive (EXEMPLAR-"
                         "REALITY / PREMISE-VALIDITY / CERTIFIED-"
                         "SYSTEM-AS-SOLD on top of the V7.4 "
                         "DEPLOYED-PART clause); all other rows "
                         "BYTE-FROZEN",
            "outcomes": "bench-p09 CLEAN at draft (nanoclay masterbatch "
                        "on the stated existing die — catalog-real); "
                        "bench-p10 F40 closed on the bytes (no "
                        "SentryGlas/ionoplast; a stocked barrier-film "
                        "class with basis — 2 pins green); bench-p11 "
                        "and eval-new03 carry disclosed residuals at "
                        "budget 3 (bench-p11 row 1 replaces the "
                        "housing — a deployed-part modification the "
                        "scans did not catch, typed for the auditor)",
            "acceptance": "the auditor's re-read per AM28 D2 verbatim"},
        "D3_recalibration": {
            "state": "BLOCKED_INFRA_TYPED",
            "claim": "c-0026 (the peer's pre-registration; probe-gated "
                     "by design)",
            "block": "the judge route (crowllm/qwen-3.8-max:free) is "
                     "not servable: probe tiny call HTTP 503 Service "
                     "Unavailable, twice, ~75 s apart (07:29:29Z and "
                     "07:31Z) — provider-side; the probe gate BLOCKED "
                     "(TINY_CALL_FAILED) and the script stops as "
                     "pre-registered",
            "next": "run probe -> run -> assemble when the route is "
                    "servable; the acceptance stands (within +/-1 of "
                    "the auditor on >=16/18 intervention AND >=10/12 "
                    "predictor rows); until then the judge stays "
                    "NOVELTY-ONLY cross-check (AM28 F39)"},
        "D4_F40_F41": {
            "state": "DONE",
            "F41": "the named-variant net stops flagging engineering-"
                   "class designations (DN/PN/NPT/BSP/ANSI-class + "
                   "NTC/PTC/PT sensor classes stripped before the "
                   "brand net); 4 pins green, 0 false positives on "
                   "conformant bills; brand/model/custom-variant "
                   "still flag",
            "F40": "content closed on the bytes by the c-0030 re-draw "
                   "(no SentryGlas/ionoplast; stocked exemplar with "
                   "basis); 2 pins green; typed limitation stands: no "
                   "lexical scan can verify product-property claims"},
    },
    "claims_touched": ["c-0029", "c-0030"],
    "pushes": ["91fb13163 (c-0029 claim)", "397f26921 (F41)",
               "f05f3d44e (c-0030 claim)", "5aae951e0 (one-shot)",
               "5e6718c84 (c-0030 batch)"],
}
(REPO / "eval" / "r30_status.json").write_text(
    json.dumps(st, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")

# --- registry note (idempotent)
rf = REPO / "eval" / "ABLATION_REGISTRY.json"
reg = json.loads(rf.read_text(encoding="utf-8"))
reg["entries"] = [e for e in reg["entries"]
                  if e.get("stage") != "generator_arm_v75_conversion"]
reg["entries"].append({
    "stage": "generator_arm_v75_conversion",
    "variant": "SYS_A1_INT_V72 + V75 directive (EXEMPLAR-REALITY / "
               "PREMISE-VALIDITY / CERTIFIED-SYSTEM-AS-SOLD)",
    "incumbent": "standard-practice baseline (the committed pairs)",
    "variant_numbers": None,
    "incumbent_numbers": None,
    "beats_incumbent": None,
    "rounds_without_beating": 0,
    "gate_pass": False,
    "gate_carrier": False,
    "status": "PENDING_MEASUREMENT",
    "registered_at": "2026-11-16",
    "lever_kind": "continuation of the V7 line (the AM28 D2 "
                  "conversion round on the auditor's 3 residual rows "
                  "+ the F40 row; the machine path byte-unchanged, "
                  "directive-only delta, pre-registered)",
    "metric_citation": "eval/pairs/r30_v75_converted/",
    "metric_citation_note": "rows PENDING-AUDITOR (Art. 10); the "
                            "auditor's re-read fills "
                            "variant_numbers at decision time",
    "notes": "Claim c-0030 (executor builder-r20s1; pre-registration "
             "pushed BEFORE any LLM call). Disclosed residuals at "
             "repair budget 3 on 3/4 rows (bench-p11 housing "
             "replacement typed for the auditor; eval-new03 "
             "named-variant residual). The F40 row closed on the "
             "bytes (2 pins).",
})
rf.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n",
              encoding="utf-8")

# --- LOG line (idempotent)
log = REPO / "R30_QUEUE_LOG.md"
line = None
if log.exists():
    txt = log.read_text(encoding="utf-8")
else:
    txt = ""
marker = "R30 (builder-r20s1): AM28 D1-D4 lane"
if marker not in txt:
    entry = (
        f"\n## {now} — {marker}\n\n"
        "- **c-0029 (AM28 D1) EXECUTED**: the holdout v4 ONE-SHOT "
        "generation — 12/12 problems, one pass each, PROBLEMS-ONLY "
        "custody (rubric never touched), the frozen V7.4 machine "
        "imported byte-identical from the peer's committed module, "
        "K_GEN=1, rows PENDING-AUDITOR; a driver serialization "
        "artifact ([rec] tuple-wrap) unwrapped zero-LLM with per-record "
        "sha recompute verified; awaiting the peer verifier + the "
        "auditor's private-rubric scoring (acceptance bar mean >=3.0/4 "
        "and 0 allowed-measures violations; burn after).\n"
        "- **c-0030 (AM28 D2 + F40) EXECUTED**: the V7.5 conversion "
        "batch — the 3 residual gap-1 rows + the F40 row re-drawn once "
        "under the frozen machine + the pre-registered V75 directive; "
        "bench-p09 clean at draft, F40 closed on the bytes (pinned), "
        "bench-p11/new03 residuals disclosed for the auditor's read.\n"
        "- **D4 DONE**: F41 — the named-variant net exempts "
        "engineering-class designations (4 pins, 0 false positives); "
        "F40 — 2 content pins green.\n"
        "- **D3 BLOCKED (infra, typed)**: the judge route 503 on the "
        "probe tiny call twice ~75s apart; the probe gate BLOCKED per "
        "the c-0026 pre-registration; the recalibration runs when the "
        "route is servable; the judge stays novelty-only cross-check "
        "until then (F39 open).\n")
    txt = txt + entry if txt else entry
    log.write_text(txt, encoding="utf-8")
print("r30_status.json + registry note + LOG written")

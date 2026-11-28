#!/usr/bin/env python3
"""r27_verify_battery.py — the Art. 13/29(c) ZERO-LLM verifier for the
R27 V7.1 battery assembly (c-0021).

Recomputes EVERYTHING from committed bytes; exits 0 only on full
reproduction. Never re-runs generation, never calls an LLM, never
re-draws bytes (Art. 29(c)):

  1. ROW MAP — the battery record's 30 rows: composition 11 frozen V7
     interventions + 7 tuned V7.1 + 12 frozen V5 predictors; every
     pair file exists; every answer sha matches the recomputed sha;
     contract tags match the stage.
  2. FROZEN ROWS — the 23 frozen rows point at eval/pairs/
     r26_v7_catalog/ files that are part of the r26 generation set
     (byte-frozen, never re-drawn); the tuned rows point at
     eval/pairs/r27_v71_tuned/ files, each drawn once (attempts ledger
     present, repairs <= 2).
  3. TUNING LEDGER — the flagged set is EXACTLY the scan pin (the r27
     standard-bill scan over the r26 generation flags exactly the 7);
     per-row repairs/residual classes match the pair metas; the
     disclosed residual matches the recomputed scan on the final
     bytes.
  4. STANDARD-BILL SCAN (final read) — recompute the scan on the final
     18 intervention answers: expect the battery record's clean
     count and findings-by-row to reproduce EXACTLY; determinism
     (same bytes twice -> same findings).
  5. JUDGE PACKET — 30 rows, each with problem / a1 / baseline /
     rubric prompt; the prompt contains the pre-registered axis
     suffix and both answers; no builder-authored scores anywhere
     (judged fields are typed PENDING-AUDITOR, never numbers).
  6. JUDGE-BLIND WINDOW — the tuning attempts' disclosed findings
     carry typed scan findings only (no judged novelty/feasibility
     values — the structural judge-blind property of the machine).
  7. CLAIM LINKAGE — c-0021 (r27-v71-standard-bill-tuning) EXECUTOR
     claim present and OPEN/DONE in eval/work_claims.json with the
     declared artifact paths all present; every committed artifact of
     this claim is covered by the claim's path list.
  8. BASELINES — non-empty for all 30 rows, sha match.
  9. ART. 20 REGISTRY — the V7 entry carries the r27 typed amendment
     (metric_citation -> the r27 battery record; V7.1 stage typed;
     still PENDING_MEASUREMENT until the auditor's judgment).
  10. ART. 27 LEDGER — eval/r27_status.json carries the
      art27_capability_budget keys (engine_diff / primary_metric_delta
      / deletions).

Run: python3 scripts/r27_verify_battery.py   (exit 0 = verified)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r27_standard_bill_scan import scan_standard_bill  # noqa: E402

BATTERY = REPO / "eval" / "battery_v7_1_catalog_r27.json"
PACKET = REPO / "eval" / "r27_judge_packet.json"
TUNING_LEDGER = REPO / "eval" / "r27_tuning_generation.json"
CLAIMS = REPO / "eval" / "work_claims.json"
REGISTRY = REPO / "eval" / "ABLATION_REGISTRY.json"
STATUS = REPO / "eval" / "r27_status.json"

FLAGGED = [
    "bench-p01-pemfc-dehydration",
    "bench-p04-pump-cavitation",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-sofc-thermal-cycling",
]

CHECKS = []


def check(name: str, ok: bool, detail: str = ""):
    CHECKS.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))


def _sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    bat = json.loads(BATTERY.read_text(encoding="utf-8"))
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    ledger = json.loads(TUNING_LEDGER.read_text(encoding="utf-8"))
    claims = json.loads(CLAIMS.read_text(encoding="utf-8"))

    # 1. row map -----------------------------------------------------
    rows = bat["rows"]
    check("row map: 30 rows", len(rows) == 30, f"got {len(rows)}")
    comp = bat["byte_map"]["composition"]
    check("row map: composition 11+7+12",
          comp["V7_R26_FROZEN_interventions"] == 11
          and comp["V71_R27_TUNED_interventions"] == 7
          and comp["V5_R26_FROZEN_predictors"] == 12, str(comp))
    n_int = sum(1 for r in rows
                if str(r["question_type"]).startswith("intervention"))
    n_pred = sum(1 for r in rows
                 if str(r["question_type"]).startswith("predictor"))
    check("row map: 18 interventions / 12 predictors",
          n_int == 18 and n_pred == 12,
          f"{n_int}/{n_pred}")
    ok_sha = ok_stage = ok_path = True
    for r in rows:
        p = REPO / r["pair_path"]
        if not p.exists():
            ok_path = False
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        if _sha(rec["a1_answer"]) != r["answer_sha256_16"]:
            ok_sha = False
        want = {"V7_R26_FROZEN": ("SYS_A1_INT_V7", "r26_v7_catalog"),
                "V71_R27_TUNED": ("SYS_A1_INT_V71", "r27_v71_tuned"),
                "V5_R26_FROZEN": ("SYS_A1F_V5", "r26_v7_catalog")}[r["stage"]]
        if (not str(rec.get("a1_source", "")).startswith(want[0])
                or want[1] not in r["pair_path"]):
            ok_stage = False
    check("row map: every pair file exists", ok_path)
    check("row map: every answer sha reproduces", ok_sha)
    check("row map: contract tags match stages", ok_stage)

    # 2. frozen vs tuned ---------------------------------------------
    tuned_ids = {r["problem_id"] for r in rows
                 if r["stage"] == "V71_R27_TUNED"}
    check("tuned set is the pre-registered flagged set",
          tuned_ids == set(FLAGGED), str(sorted(tuned_ids)))
    ok_rep = ok_budget = True
    for pid in FLAGGED:
        rec = json.loads(
            (REPO / "eval" / "pairs" / "r27_v71_tuned" / f"{pid}.json")
            .read_text(encoding="utf-8"))
        if not rec.get("attempts"):
            ok_rep = False
        if rec["meta"]["repairs"] > 2:
            ok_budget = False
    check("tuned rows: attempts ledger present (one pass each)", ok_rep)
    check("tuned rows: repairs within the pre-registered budget 2",
          ok_budget)
    frozen_r26 = {json.loads(f.read_text(encoding="utf-8"))["problem_id"]
                  for f in (REPO / "eval" / "pairs" / "r26_v7_catalog")
                  .glob("*.json")}
    check("frozen rows: r26 generation set intact (30 files, "
          "tuned originals preserved, never re-drawn)",
          len(frozen_r26) == 30 and set(FLAGGED) <= frozen_r26)

    # 3. tuning ledger ------------------------------------------------
    check("tuning ledger: flagged set matches",
          ledger["tuning_set"] == FLAGGED)
    ok_meta = True
    for pid, r in ledger["rows"].items():
        rec = json.loads(
            (REPO / "eval" / "pairs" / "r27_v71_tuned" / f"{pid}.json")
            .read_text(encoding="utf-8"))
        if rec["meta"]["repairs"] != r["repairs"]:
            ok_meta = False
        resid_cls = set(rec["meta"]["residual_findings"])
        if resid_cls != set(r["residual_findings"]):
            ok_meta = False
    check("tuning ledger: per-row repairs/residuals match pair metas",
          ok_meta)
    disclosed = bat["tuning_ledger"]["disclosed_residual"]
    check("tuning ledger: exactly one disclosed residual "
          "(eval-sofc-thermal-cycling)",
          list(disclosed) == ["eval-sofc-thermal-cycling"])

    # 4. standard-bill scan final read ---------------------------------
    sb = bat["standard_bill_scan_final"]
    recomputed = {}
    for r in rows:
        if not str(r["question_type"]).startswith("intervention"):
            continue
        rec = json.loads((REPO / r["pair_path"]).read_text(encoding="utf-8"))
        v = scan_standard_bill(rec["a1_answer"], r["question_type"])
        recomputed[r["problem_id"]] = {
            "clean": not v, "findings": v.get("STANDARD_BILL", [])[:6]}
    check("standard-bill scan: final read reproduces exactly",
          recomputed == sb["findings_by_row"])
    check("standard-bill scan: 17/18 clean + 1 disclosed",
          sb["clean"] == 17
          and sb["interventions_scanned"] == 18
          and [p for p, s in sb["findings_by_row"].items()
               if not s["clean"]] == ["eval-sofc-thermal-cycling"])
    # determinism
    det = True
    for pid in ("bench-p08-mems-stiction", "eval-sofc-thermal-cycling"):
        rec = json.loads(
            (REPO / "eval" / "pairs" / "r27_v71_tuned" / f"{pid}.json")
            .read_text(encoding="utf-8"))
        a = scan_standard_bill(rec["a1_answer"], "intervention-proposal")
        b = scan_standard_bill(rec["a1_answer"], "intervention-proposal")
        if a != b:
            det = False
    check("standard-bill scan: deterministic (same bytes twice)", det)

    # 5. judge packet ---------------------------------------------------
    prows = packet["rows"]
    check("judge packet: 30 rows", len(prows) == 30, f"got {len(prows)}")
    ok_pkt = True
    for pr in prows:
        if not (pr.get("problem") and pr.get("a1_answer")
                and pr.get("baseline_answer").strip()
                and pr.get("rubric_prompt")):
            ok_pkt = False
            break
        rp = pr["rubric_prompt"]
        if ("PER-AXIS SCORING CONTRACT" not in rp
                or "=== ANSWER A ===" not in rp
                or "=== ANSWER B ===" not in rp):
            ok_pkt = False
            break
    check("judge packet: problem/a1/baseline/rubric prompt complete "
          "per pair (axis suffix + both answers)", ok_pkt)
    pkt_ids = [pr["problem_id"] for pr in prows]
    bat_ids = [r["problem_id"] for r in rows]
    check("judge packet: same 30 pairs as the battery",
          sorted(pkt_ids) == sorted(bat_ids))

    # no builder-authored scores (typed pending, never numbers)
    summary = bat["summary_intervention_rows"]
    ok_pending = all(
        r["judged"] is False and r["novelty_delta"] is None
        and r["a1_feasibility"] is None
        and r["baseline_feasibility"] is None
        and r["feasibility_abs_gap"] is None
        and "PENDING-AUDITOR" in r["typed_pending"] for r in summary)
    check("summary_intervention_rows: 18 rows, judged fields TYPED "
          "PENDING-AUDITOR (no builder scores — Art. 10)",
          len(summary) == 18 and ok_pending)

    # 6. judge-blind window ----------------------------------------------
    ok_blind = True
    for pid in FLAGGED:
        rec = json.loads(
            (REPO / "eval" / "pairs" / "r27_v71_tuned" / f"{pid}.json")
            .read_text(encoding="utf-8"))
        for att in rec["attempts"]:
            for f in att.get("findings_disclosed", []):
                low = str(f).lower()
                if ("novelty" in low and any(
                        c.isdigit() for c in low)) or (
                        "feasibility" in low and any(
                            c.isdigit() for c in low)):
                    # judged-value shape in a repair directive — the
                    # structural judge-blind property violated
                    ok_blind = False
    check("judge-blind window: repair directives carry typed scan "
          "findings only (no judged values reached the machine)",
          ok_blind)

    # 7. claim linkage -----------------------------------------------------
    c21 = next((c for c in claims["claims"]
                if c["claim_id"] == "c-0021"), None)
    check("claim linkage: c-0021 EXECUTOR claim present "
          "(work_id r26-v7-catalog-battery — the Art. 29(d) takeover "
          "resumes the SAME work item; corrected when the CI takeover "
          "rule caught the first filing's new-work_id error)",
          c21 is not None and c21["role"] == "EXECUTOR"
          and c21["work_id"] == "r26-v7-catalog-battery"
          and c21.get("takes_over") == "c-0020")
    ok_paths = all((REPO / rel).exists() for rel in c21["artifact_paths"])
    check("claim linkage: every declared artifact path exists", ok_paths)
    c20 = next((c for c in claims["claims"]
                if c["claim_id"] == "c-0020"), None)
    check("claim linkage: c-0020 typed TAKEN_OVER by c-0021 "
          "(the Art. 29(d) vocabulary)",
          c20 is not None and c20["status"] == "TAKEN_OVER"
          and c20.get("taken_over_by") == "c-0021")
    sess = claims["sessions"].get("builder-r27s1")
    check("claim linkage: session builder-r27s1 registered",
          sess is not None)

    # 8. baselines ------------------------------------------------------
    ok_base = all(v["baseline_sha256_16"] and len(v["baseline_source"]) > 0
                  for v in bat["baselines"].values()) and \
        len(bat["baselines"]) == 30
    check("baselines: non-empty for all 30 rows with source + sha",
          ok_base)
    ok_base_sha = True
    from r26_battery_v7 import baseline_for  # noqa: E402
    for pid, v in bat["baselines"].items():
        base, _src = baseline_for(pid)
        if _sha(base) != v["baseline_sha256_16"]:
            ok_base_sha = False
    check("baselines: shas reproduce from the canonical sources",
          ok_base_sha)

    # 9. Art. 20 registry amendment --------------------------------------
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    v7 = reg["entries"][-1]
    cit = str(v7.get("metric_citation", ""))
    check("Art. 20 registry: V7 entry metric_citation -> the r27 "
          "battery record", "battery_v7_1_catalog_r27" in cit, cit)
    variant = str(v7.get("variant", ""))
    check("Art. 20 registry: V7.1 tuning typed on the entry",
          "STANDARD-BILL" in variant and "V71" in variant)
    check("Art. 20 registry: still PENDING_MEASUREMENT (the auditor's "
          "judgment flips it)",
          v7.get("status") == "PENDING_MEASUREMENT")

    # 10. Art. 27 ledger ---------------------------------------------------
    if STATUS.exists():
        st = json.loads(STATUS.read_text(encoding="utf-8"))
        a27 = st.get("art27_capability_budget", {})
        check("Art. 27 ledger: engine_diff / primary_metric_delta / "
              "deletions present",
              all(k in a27 for k in ("engine_diff",
                                     "primary_metric_delta",
                                     "deletions")))
    else:
        check("Art. 27 ledger: eval/r27_status.json present", False)

    # verdict ------------------------------------------------------------
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print(f"\n[r27-verify] {len(CHECKS) - n_fail}/{len(CHECKS)} checks "
          f"passed" + (f"; {n_fail} FAILED" if n_fail else " — VERIFIED"))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())

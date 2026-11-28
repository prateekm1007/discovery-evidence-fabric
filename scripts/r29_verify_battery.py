#!/usr/bin/env python3
"""r29_verify_battery.py — the Art. 13/29(c) ZERO-LLM verifier for the
R29 V7.2 battery assembly (c-0025).

Recomputes EVERYTHING from committed bytes; exits 0 only on full
reproduction. Never re-runs generation, never calls an LLM, never
re-draws bytes (Art. 29(c)):

  1. ROW MAP — the battery record's 30 rows: composition 8 frozen V7
     interventions (the adjudicated gap-0 set) + 10 tuned V7.2 + 12
     frozen V5 predictors; every pair file exists; every answer sha
     matches the recomputed sha; contract tags match the stage.
  2. FROZEN ROWS — the 20 frozen rows point at eval/pairs/
     r26_v7_catalog/ files (byte-frozen, never re-drawn); the tuned
     rows point at eval/pairs/r29_v72_tuned/ files, each drawn once
     (attempts ledger present, repairs <= 2); NO r27_v71_tuned byte
     remains in the battery (all 7 r27-tuned rows re-drawn under
     V7.2).
  3. TUNING SET — the flagged set is EXACTLY the pre-registered set
     (the auditor's gap>=1 set + bench-p10) and EXACTLY the
     conversion-scan pin set + the operational-loss pin (bench-p10);
     per-row repairs/residual classes match the pair metas.
  4. FINAL SCAN READS — recompute the standard-bill + operational-
     loss + conversion + named-variant scans on the final 18
     intervention answers: expect the battery record's clean count
     and findings-by-row to reproduce EXACTLY; determinism (same
     bytes twice -> same findings). The AM27 D1 acceptance (0 rows
     with unpriced operational loss) recomputes from the bytes.
  5. JUDGE PACKET — 30 rows, each with problem / a1 / baseline /
     rubric prompt; the prompt is BYTE-IDENTICAL to the r27 packet's
     per-pair prompt for the 20 frozen rows (same problem + same
     bytes + same rubric form) and carries the pre-registered axis
     suffix for all; no builder-authored scores anywhere (judged
     fields typed PENDING-AUDITOR, never numbers).
  6. JUDGE-BLIND WINDOW — the tuning attempts' disclosed findings
     carry typed scan findings only (no judged novelty/feasibility
     values — the structural judge-blind property of the machine).
  7. CLAIM LINKAGE — c-0025 (r29-v72-battery-conversion) EXECUTOR
     claim present and OPEN in eval/work_claims.json with the
     declared artifact paths all present.
  8. BASELINES — non-empty for all 30 rows, sha match.
  9. ART. 20 REGISTRY — the V7 entry carries the r29 typed amendment
     (metric_citation -> the r29 battery record; V7.2 stage typed;
     still PENDING_MEASUREMENT until the auditor's judgment).

Run: python3 scripts/r29_verify_battery.py   (exit 0 = verified)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r29_conversion_scan import scan_conversion  # noqa: E402
from r29_operational_loss_scan import scan_operational_loss  # noqa: E402
from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r26_catalog_scan import scan_catalog  # noqa: E402
from r26_battery_v7 import baseline_for  # noqa: E402

BATTERY = REPO / "eval" / "battery_v7_2_catalog_r29.json"
PACKET = REPO / "eval" / "r29_judge_packet.json"
R27_PACKET = REPO / "eval" / "r27_judge_packet.json"
TUNING_LEDGER = REPO / "eval" / "r29_tuning_generation.json"
CLAIMS = REPO / "eval" / "work_claims.json"
REGISTRY = REPO / "eval" / "ABLATION_REGISTRY.json"

FLAGGED = [
    "bench-p01-pemfc-dehydration",
    "bench-p04-pump-cavitation",
    "bench-p06-water-biofilm",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p10-pv-pid",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-new03-insulin-pump-occlusion",
    "eval-sofc-thermal-cycling",
]
V73_SET = [
    "bench-p04-pump-cavitation",
    "bench-p08-mems-stiction",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-new03-insulin-pump-occlusion",
]
V74_SET = [
    "bench-p04-pump-cavitation",
]
TUNED_DIRS = {
    "V74_R29_TUNED": "eval/pairs/r29_v74_tuned/",
    "V73_R29_TUNED": "eval/pairs/r29_v73_tuned/",
    "V72_R29_TUNED": "eval/pairs/r29_v72_tuned/",
}
# the conversion-scan pin set (tests/test_r29_conversion_scan.py) +
# bench-p10 (the operational-loss pin)
CONVERSION_PIN_SET = [
    "bench-p01-pemfc-dehydration",
    "bench-p04-pump-cavitation",
    "bench-p06-water-biofilm",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-new03-insulin-pump-occlusion",
]
OPERATIONAL_PIN = "bench-p10-pv-pid"
# the sofc row's target defect (the graded composition) is pinned by
# the r27 CUSTOM_MATERIAL class in tests/test_r27_standard_bill_scan.py
# (the disclosed V7.1 residual this conversion round clears)
R27_SB_PIN = "eval-sofc-thermal-cycling"

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
    gen = json.loads(TUNING_LEDGER.read_text(encoding="utf-8"))
    claims = json.loads(CLAIMS.read_text(encoding="utf-8"))

    # ---- 1. row map
    rows = bat["rows"]
    check("row map: 30 rows", len(rows) == 30, str(len(rows)))
    comp = bat["byte_map"]["composition"]
    n_frozen_int = sum(1 for r in rows if r["stage"] == "V7_R26_FROZEN")
    n_tuned = sum(1 for r in rows
                  if r["stage"] in TUNED_DIRS)
    n_pred = sum(1 for r in rows if r["stage"] == "V5_R26_FROZEN")
    check("composition 8+10+12",
          (n_frozen_int, n_tuned, n_pred) == (8, 10, 12),
          f"{(n_frozen_int, n_tuned, n_pred)}")
    n_v72 = sum(1 for r in rows if r["stage"] == "V72_R29_TUNED")
    n_v73 = sum(1 for r in rows if r["stage"] == "V73_R29_TUNED")
    n_v74 = sum(1 for r in rows if r["stage"] == "V74_R29_TUNED")
    check("per-round composition 5+4+1",
          (n_v72, n_v73, n_v74) == (5, 4, 1),
          f"{(n_v72, n_v73, n_v74)}")
    check("byte_map matches rows",
          comp["V7_R26_FROZEN_interventions"] == n_frozen_int
          and comp["V72_R29_TUNED_interventions"] == n_v72
          and comp["V73_R29_TUNED_interventions"] == n_v73
          and comp["V74_R29_TUNED_interventions"] == n_v74
          and comp["V5_R26_FROZEN_predictors"] == n_pred)
    sha_ok = True
    for r in rows:
        rec = json.loads((REPO / r["pair_path"]).read_text(
            encoding="utf-8"))
        if _sha(rec["a1_answer"]) != r["answer_sha256_16"]:
            sha_ok = False
        if r["stage"] in TUNED_DIRS:
            if not r["pair_path"].startswith(TUNED_DIRS[r["stage"]]):
                sha_ok = False
            src = json.loads((REPO / r["pair_path"]).read_text(
                encoding="utf-8"))["a1_source"]
            if "SYS_A1_INT_V72" not in src:
                sha_ok = False
        if r["stage"] not in TUNED_DIRS and \
                not r["pair_path"].startswith("eval/pairs/r26_v7_catalog/"):
            sha_ok = False
    check("per-row sha + contract + per-round path provenance", sha_ok)

    # ---- 2. frozen/tuned discipline
    no_v71 = all("r27_v71_tuned" not in r["pair_path"] for r in rows)
    check("no r27_v71_tuned byte remains in the battery", no_v71)
    tuned_ok = True
    for r in rows:
        if r["stage"] not in TUNED_DIRS:
            continue
        rec = json.loads((REPO / r["pair_path"]).read_text(
            encoding="utf-8"))
        if not rec.get("attempts"):
            tuned_ok = False
        if (rec.get("meta", {}).get("repairs") or 0) > 3:
            tuned_ok = False
    check("tuned rows drawn once (attempts present, repairs <= 3)",
          tuned_ok)
    # the V7.3/V7.4 sets match the pinned round identities
    v73_rows = sorted(r["problem_id"] for r in rows
                      if r["stage"] in ("V73_R29_TUNED", "V74_R29_TUNED"))
    check("V7.3/V7.4 rows == the pinned round sets",
          v73_rows == sorted(set(V73_SET)), str(v73_rows))
    check("V7.4 row == the pinned micro-round set",
          sorted(r["problem_id"] for r in rows
                 if r["stage"] == "V74_R29_TUNED") == sorted(V74_SET))

    # ---- 3. tuning set identity
    check("tuning set == the pre-registered conversion set",
          sorted(gen["tuning_set"]) == sorted(FLAGGED)
          and sorted(bat["tuning_ledger"]["flagged_set"])
          == sorted(FLAGGED))
    check("tuning set == conversion-pin set + the operational pin "
          "+ the r27 standard-bill pin",
          sorted(CONVERSION_PIN_SET + [OPERATIONAL_PIN, R27_SB_PIN])
          == sorted(FLAGGED))
    check("round ledgers present (v72/v73/v74)",
          all((REPO / p).exists() for p in (
              "eval/r29_tuning_generation.json",
              "eval/r29_v73_tuning_generation.json",
              "eval/r29_v74_tuning_generation.json")))
    per_row_match = all(
        json.loads((REPO / next(
            r["pair_path"] for r in rows
            if r["problem_id"] == pid)).read_text(
                encoding="utf-8"))["meta"]["repairs"]
        == (gen["rows"][pid]["repairs"] if pid not in V73_SET + V74_SET
            else json.loads((REPO / (
                "eval/r29_v74_tuning_generation.json"
                if pid in V74_SET
                else "eval/r29_v73_tuning_generation.json"))
                .read_text(encoding="utf-8"))["rows"][pid]["repairs"])
        for pid in FLAGGED)
    check("round ledgers' per-row repairs match the pair metas",
          per_row_match)

    # ---- 4. final scan reads recompute
    probs = {}
    for f in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / f).read_text(encoding="utf-8"))[
                "problems"]:
            probs[p["problem_id"]] = p
    reads = bat["final_scan_reads"]["findings_by_row"]
    recompute_ok = True
    ol_rows = []
    for r in rows:
        if not str(r["question_type"]).startswith("intervention"):
            continue
        rec = json.loads((REPO / r["pair_path"]).read_text(
            encoding="utf-8"))
        pid = r["problem_id"]
        prob = probs[pid]
        sb = scan_standard_bill(rec["a1_answer"], r["question_type"])
        ol = scan_operational_loss(rec["a1_answer"], r["question_type"])
        cv = scan_conversion(rec["a1_answer"], r["question_type"], prob)
        nv = scan_catalog(prob, rec["a1_answer"])
        if ol:
            ol_rows.append(pid)
        got = reads[pid]
        if bool(sb.get("STANDARD_BILL")) != bool(got["standard_bill"]):
            recompute_ok = False
        if bool(ol.get("UNPRICED_OPERATIONAL_LOSS")) \
                != bool(got["operational_loss"]):
            recompute_ok = False
        if bool(cv.get("CONVERSION")) != bool(got["conversion"]):
            recompute_ok = False
        if bool(nv.get("NAMED_VARIANT")) != bool(got["named_variant"]):
            recompute_ok = False
        if (not (sb or ol or cv or nv)) != got["clean"]:
            recompute_ok = False
        # determinism
        if scan_conversion(rec["a1_answer"], r["question_type"],
                           prob) != cv:
            recompute_ok = False
    check("final scan reads recompute exactly (incl. determinism)",
          recompute_ok)
    n_clean = sum(1 for s in reads.values() if s["clean"])
    check("battery clean count matches",
          n_clean == bat["final_scan_reads"]["fully_clean"],
          f"{n_clean}")
    check("AM27 D1 acceptance: 0 rows with unpriced operational loss",
          not ol_rows, str(ol_rows))

    # ---- 5. judge packet
    check("packet 30 rows", len(packet["rows"]) == 30)
    packet_ok = True
    suffix = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
    r27_rows = {r["problem_id"]: r for r in json.loads(
        R27_PACKET.read_text(encoding="utf-8"))["rows"]}
    for pr in packet["rows"]:
        if suffix not in pr["rubric_prompt"]:
            packet_ok = False
        if not pr["a1_answer"].strip() or \
                not pr["baseline_answer"].strip():
            packet_ok = False
        # frozen rows: prompt BYTE-IDENTICAL to the r27 packet's
        # (same problem + same bytes + same rubric form)
        if pr["stage"] in ("V7_R26_FROZEN", "V5_R26_FROZEN"):
            if r27_rows[pr["problem_id"]]["rubric_prompt"] \
                    != pr["rubric_prompt"]:
                packet_ok = False
    check("packet prompts carry the axis suffix; frozen-row prompts "
          "byte-identical to the r27 packet", packet_ok)
    no_scores = all(
        r.get("novelty_delta") is None and r.get("a1_feasibility") is None
        for r in bat["summary_intervention_rows"])
    check("judged fields typed PENDING-AUDITOR (never numbers)",
          no_scores and all(
              not r["judged"] for r in bat["summary_intervention_rows"]))

    # ---- 6. judge-blind window
    blind_ok = True
    for tuned_dir in ("r29_v72_tuned", "r29_v73_tuned",
                      "r29_v74_tuned"):
        d = REPO / "eval" / "pairs" / tuned_dir
        if not d.exists():
            continue
        for pf in sorted(d.glob("*.json")):
            rec = json.loads(pf.read_text(encoding="utf-8"))
            for att in rec.get("attempts", []):
                for f in (att.get("findings_disclosed") or []):
                    low = f.lower()
                    if ("novelty delta" in low or "novelty_delta" in low
                            or "feasibility gap" in low
                            or "feasibility_gap" in low
                            or "judged" in low):
                        blind_ok = False
    check("judge-blind window (no judged numbers in any repair prompt)",
          blind_ok)

    # ---- 7. claim linkage
    c25 = [c for c in claims["claims"] if c["claim_id"] == "c-0025"]
    check("c-0025 EXECUTOR claim present and OPEN",
          len(c25) == 1 and c25[0]["role"] == "EXECUTOR"
          and c25[0]["status"] == "OPEN"
          and c25[0]["work_id"] == "r29-v72-battery-conversion")
    c27 = [c for c in claims["claims"] if c["claim_id"] == "c-0027"]
    c28 = [c for c in claims["claims"] if c["claim_id"] == "c-0028"]
    check("c-0027/c-0028 EXECUTOR claims present",
          len(c27) == 1 and len(c28) == 1
          and c27[0]["work_id"] == "r29-v73-residual-conversion"
          and c28[0]["work_id"]
          == "r29-v74-deployed-part-no-modification")
    paths_ok = all((REPO / p).exists() for p in c25[0]["artifact_paths"]
                   if not p.endswith("/"))
    check("claim artifact paths exist", paths_ok)

    # ---- 8. baselines
    base_ok = True
    for pid, b in bat["baselines"].items():
        base, _ = baseline_for(pid)
        if not base.strip() or _sha(base) != b["baseline_sha256_16"]:
            base_ok = False
    check("baselines non-empty + sha match (30 rows)", base_ok)

    # ---- 9. Art. 20 registry amendment
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    v7 = [e for e in reg["entries"]
          if "novelty_relocation" in str(e.get("stage", ""))
          or "V7" in str(e.get("variant", ""))]
    amend_ok = any("battery_v7_2_catalog_r29.json"
                   in str(e.get("metric_citation", ""))
                   or "V72" in str(e.get("variant", ""))
                   or "V7.2" in str(e.get("variant", ""))
                   for e in v7)
    check("Art. 20 registry carries the V7.2 typed amendment", amend_ok)

    print()
    n_pass = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"[r29-verify] {n_pass}/{len(CHECKS)} checks PASS")
    for name, ok, detail in CHECKS:
        if not ok:
            print(f"  FAIL: {name} — {detail}")
    return 0 if n_pass == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""r29_assemble_battery.py — assemble the FINAL 30-pair V7.2 battery
(eval/battery_v7_2_catalog_r29.json) + the AUDITOR JUDGE PACKET
(eval/r29_judge_packet.json) from committed bytes, zero-LLM.

The AM27 D2 conversion: the gate is AUDITOR-judged (Art. 14/LXXXVI),
so the judged battery is the auditor's read of the committed bytes.
This assembler produces:

  1. the battery record — 30 rows with per-row provenance:
       - 8 frozen V7 intervention rows (the adjudicated gap-0 rows,
         r26 generation, byte-frozen),
       - 10 tuned V7.2 intervention rows (the pre-registered
         conversion set; eval/pairs/r29_v72_tuned/),
       - 12 frozen V5 predictor rows (r26 generation, byte-frozen;
         SYS_A1F_V5, holdout-v3-proven),
     the tuning ledger, the FINAL scan reads (standard-bill +
     operational-loss + conversion + catalog on the final 18
     intervention answers), and summary_intervention_rows with the
     judged fields TYPED PENDING-AUDITOR (the builder never scores —
     Art. 10: no self-certification);
  2. the judge packet — per-pair problem / a1_answer /
     baseline_answer / the pre-registered rubric prompt (the SAME
     _rubric_prompt + AXIS_SUFFIX form the r27 packet rode), so the
     auditor's judgment rides the same pre-registered rubric.

Zero-LLM: pure byte recompute over committed pair files (Art. 22/13
lineage). Deterministic. No re-draw (Art. 29(c): the 20 frozen rows
are never re-drawn; the 10 tuned rows were drawn once each under the
pre-registered c-0025 machine).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r29_conversion_scan import scan_conversion  # noqa: E402
from r29_operational_loss_scan import scan_operational_loss  # noqa: E402
from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r26_battery_v7 import baseline_for, _prob_map  # noqa: E402
from r26_catalog_scan import scan_catalog  # noqa: E402
from eval.run import _rubric_prompt  # noqa: E402

R26_DIR = REPO / "eval" / "pairs" / "r26_v7_catalog"
R29_DIR = REPO / "eval" / "pairs" / "r29_v72_tuned"
TUNING_LEDGER = REPO / "eval" / "r29_tuning_generation.json"
BATTERY_OUT = REPO / "eval" / "battery_v7_2_catalog_r29.json"
PACKET_OUT = REPO / "eval" / "r29_judge_packet.json"
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()

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


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return (datetime.datetime.now(datetime.UTC).isoformat()
            .replace("+00:00", "Z"))


def _pair_row(pid: str, stage: str, pair_path: Path) -> dict:
    rec = json.loads(pair_path.read_text(encoding="utf-8"))
    assert rec["problem_id"] == pid, (pid, pair_path)
    meta = rec.get("meta", {})
    return {
        "problem_id": pid,
        "question_type": rec.get("question_type"),
        "stage": stage,
        "contract": rec.get("a1_source"),
        "pair_path": str(pair_path.relative_to(REPO)),
        "answer_sha256_16": _sha(rec["a1_answer"]),
        "repairs": meta.get("repairs"),
        "residual_findings": {k: len(v) for k, v in
                              meta.get("residual_findings", {}).items()},
        "a1_answer_chars": len(rec["a1_answer"]),
        "generated_at": rec.get("generated_at"),
    }


def main() -> int:
    probs = _prob_map()
    gen_ledger = json.loads(TUNING_LEDGER.read_text(encoding="utf-8"))

    rows = []
    tuned = set(FLAGGED)
    for f in sorted(R26_DIR.glob("*.json")):
        pid = json.loads(f.read_text(encoding="utf-8"))["problem_id"]
        qt = str(probs[pid].get("question_type", ""))
        if pid in tuned:
            continue
        stage = ("V5_R26_FROZEN" if qt.startswith("predictor")
                 else "V7_R26_FROZEN")
        rows.append(_pair_row(pid, stage, f))
    for pid in FLAGGED:
        rows.append(_pair_row(pid, "V72_R29_TUNED",
                              R29_DIR / f"{pid}.json"))
    rows.sort(key=lambda r: ((r["question_type"] or ""),
                             r["problem_id"]))
    assert len(rows) == 30, len(rows)

    # the FINAL scan reads over the 18 intervention answers (the
    # deterministic V7.2 legs re-read on the final bytes)
    sb_status = {}
    for r in rows:
        if not str(r["question_type"]).startswith("intervention"):
            continue
        rec = json.loads((REPO / r["pair_path"]).read_text(encoding="utf-8"))
        pid = r["problem_id"]
        prob = probs[pid]
        sb = scan_standard_bill(rec["a1_answer"], r["question_type"])
        ol = scan_operational_loss(rec["a1_answer"], r["question_type"])
        cv = scan_conversion(rec["a1_answer"], r["question_type"], prob)
        nv = scan_catalog(prob, rec["a1_answer"])
        sb_status[pid] = {
            "standard_bill": (sb.get("STANDARD_BILL") or [])[:6],
            "operational_loss": (ol.get("UNPRICED_OPERATIONAL_LOSS")
                                 or [])[:4],
            "conversion": (cv.get("CONVERSION") or [])[:6],
            "named_variant": (nv.get("NAMED_VARIANT") or [])[:4],
            "clean": not (sb or ol or cv or nv),
        }
    n_clean = sum(1 for s in sb_status.values() if s["clean"])

    # baselines for every row (the judge packet needs them)
    baselines = {}
    for r in rows:
        base, b_src = baseline_for(r["problem_id"])
        assert base.strip(), f"no baseline for {r['problem_id']}"
        baselines[r["problem_id"]] = {"baseline_answer": base,
                                      "baseline_source": b_src}

    # summary_intervention_rows — judged fields TYPED PENDING-AUDITOR
    summary_intervention_rows = []
    for r in rows:
        if not str(r["question_type"]).startswith("intervention"):
            continue
        summary_intervention_rows.append({
            "problem_id": r["problem_id"],
            "stage": r["stage"],
            "novelty_delta": None,
            "a1_feasibility": None,
            "baseline_feasibility": None,
            "feasibility_abs_gap": None,
            "judged": False,
            "judged_by": None,
            "typed_pending": ("PENDING-AUDITOR — the gate is "
                              "auditor-judged (Art. 14/LXXXVI, AM26/"
                              "AM27); the builder never scores its own "
                              "generation (Art. 10: no "
                              "self-certification)"),
        })

    battery = {
        "record": "BATTERY_V7_2_CATALOG_R29/1.0.0",
        "at": _now(),
        "work_id": "r29-v72-battery-conversion",
        "claim": "c-0025 (EXECUTOR builder-r29s1, Art. 29(b) "
                 "claim-before-work, pushed before any LLM call)",
        "amendment_basis": (
            "AM27 D2 verbatim: 'Kill the premise-flawed row and convert "
            "the seven gap-1 rows. bench-p06 needs a topology-valid "
            "mechanism (no reversal without a second path). The seven "
            "gap-1 rows (micro-roughened vane, MEMS dimples, silica "
            "interlayer, Al-on-steel sleeve, silica packet, added sensor "
            "channel, graded co-firing) must become pure catalog-part or "
            "procedure changes. Accept: feasibility |gap| <=0.25 AND "
            "novelty delta >=0.5 on >=30 pairs, auditor-judged.' Plus "
            "AM27 D1 (F38): 'Any duty-cycle/curtailment/derate "
            "intervention must state the energy/output/throughput loss "
            "and count it against parity.'"),
        "byte_map": {
            "n_pairs": 30,
            "n_interventions": 18,
            "n_predictors": 12,
            "composition": {
                "V7_R26_FROZEN_interventions": 8,
                "V72_R29_TUNED_interventions": 10,
                "V5_R26_FROZEN_predictors": 12,
            },
            "map_note": (
                "the pre-registered r26 ALL-FRESH map (18 V7-family "
                "interventions + 12 V5 predictors), unchanged; the 10 "
                "tuned rows are re-draws of the auditor-adjudicated "
                "gap>=1 set + bench-p10 (F38) under SYS_A1_INT_V72 (the "
                "AM27 D2 conversion), each drawn ONCE under the c-0025 "
                "machine; the 20 frozen rows (8 gap-0 interventions + "
                "12 predictors) are never re-drawn (Art. 29(c)); no "
                "r27_v71_tuned byte remains in the battery — all 7 r27-"
                "tuned rows are re-drawn under V7.2"),
        },
        "tuning_ledger": {
            "flagged_set": FLAGGED,
            "flagged_basis": (
                "the auditor's 18-row re-judgment at audit tip "
                "d7540c6fe:eval/auditor_r28_adjudication.json per_row — "
                "the gap>=1 set (8 rows at gap 1 per the per-row record, "
                "incl. bench-p01; bench-p06 at gap 2) PLUS bench-p10 for "
                "the F38 pricing; pins: tests/test_r29_conversion_scan.py "
                "(9 positive pins on the pre-conversion bytes) + tests/"
                "test_r29_operational_loss_scan.py (the bench-p10 pin)"),
            "machine": gen_ledger["machine"],
            "per_row": gen_ledger["rows"],
            "disclosed_residuals": {
                pid: {k: v for k, v in (gen_ledger["rows"].get(pid, {})
                                         .get("residual_findings")
                                         or {}).items()}
                for pid in FLAGGED
                if (gen_ledger["rows"].get(pid, {})
                    .get("residual_findings"))
            },
        },
        "final_scan_reads": {
            "interventions_scanned": 18,
            "fully_clean": n_clean,
            "legs": ["standard-bill r27", "operational-loss r29",
                     "conversion r29", "catalog-v2 named-variant"],
            "findings_by_row": sb_status,
            "note": ("the deterministic legs' final read on the FINAL "
                     "bytes; residuals are disclosed, never hidden — "
                     "the authoritative feasibility read is the "
                     "AUDITOR's (the gate is auditor-judged)"),
        },
        "rows": rows,
        "baselines": {pid: {"baseline_source": b["baseline_source"],
                            "baseline_sha256_16": _sha(
                                b["baseline_answer"])}
                      for pid, b in baselines.items()},
        "summary_intervention_rows": summary_intervention_rows,
        "acceptance_verbatim": (
            "feasibility |gap| <= 0.25 AND novelty delta >= 0.5 on "
            ">= 30 pairs, auditor-judged; the ablation beats the "
            "incumbent (CI excludes it) — incumbent r20 intervention "
            "fgap 1.5, nd 2.333; the AM27 D1 acceptance: 0 rows with "
            "unpriced operational loss (the final operational-loss "
            "scan read is typed above)"),
        "art20": (
            "lever kind novelty-relocation (V7 family), round 1 of 2 — "
            "the V7.2 conversion is a contract TIGHTENING inside the "
            "SAME arm (every V7.2-compliant bill is V7.1-compliant); "
            "the registry entry carries the typed amendment"),
        "judge": {
            "gate_owner": "AUDITOR (Art. 14/LXXXVI, AM26/AM27: the "
                          "machine judge is an input, never the "
                          "verdict)",
            "machine_judge_crosscheck": (
                "the F39 calibration run (c-0026) is a CROSS-CHECK "
                "ONLY — novelty-only until its feasibility axis is "
                "calibrated within +/-1 of the auditor on >=16/18 rows "
                "(AM27 D3); the r28 crosscheck's feasibility read was "
                "REJECTED as uncalibrated"),
            "judge_packet": "eval/r29_judge_packet.json (per-pair "
                            "problem + a1 + baseline + the "
                            "pre-registered rubric prompt)",
        },
        "independence": (
            "auditor independent of builder/pipeline/generator judges "
            "the committed bytes; the builder's generation rode the "
            "zai gateway (generation transport — Art. 10 separates "
            "generation from VERIFICATION; judging on the generator's "
            "own route would be self-certification and is NOT done)"),
    }
    BATTERY_OUT.write_text(json.dumps(battery, indent=1,
                                      ensure_ascii=False) + "\n",
                           encoding="utf-8")

    # the judge packet: per-pair problem/a1/baseline + rubric prompt
    packet_rows = []
    for r in rows:
        prob = probs[r["problem_id"]]
        rec = json.loads((REPO / r["pair_path"]).read_text(encoding="utf-8"))
        a1 = rec["a1_answer"]
        base = baselines[r["problem_id"]]["baseline_answer"]
        prompt = _rubric_prompt(prob, a1[:7000], base[:7000], None) \
            + AXIS_SUFFIX
        packet_rows.append({
            "problem_id": r["problem_id"],
            "question_type": r["question_type"],
            "stage": r["stage"],
            "problem": prob,
            "a1_answer": a1,
            "baseline_answer": base,
            "rubric_prompt": prompt,
        })
    packet = {
        "record": "R29_JUDGE_PACKET/1.0.0",
        "at": _now(),
        "for": ("the AUDITOR's judgment of the final 30-pair V7.2 "
                "battery (AM27 D2: the gate is auditor-judged); the "
                "rubric prompt per pair is the SAME pre-registered "
                "form the r27 packet rode (_rubric_prompt + "
                "AXIS_SUFFIX, unchanged), so the auditor's scores ride "
                "the pre-registered rubric"),
        "battery": "eval/battery_v7_2_catalog_r29.json",
        "scored_fields_expected": {
            "per_pair": ["novelty_delta", "a1_feasibility",
                         "baseline_feasibility", "feasibility_abs_gap"],
            "summary": ["novelty_delta_mean", "feasibility_abs_gap_mean"],
            "format_reference": ("eval/auditor_r28_adjudication.json "
                                 "(the R28 18-row re-judgment format, "
                                 "audit branch)"),
        },
        "rows": packet_rows,
    }
    PACKET_OUT.write_text(json.dumps(packet, indent=1,
                                     ensure_ascii=False) + "\n",
                          encoding="utf-8")

    print(f"[r29-assemble] battery -> {BATTERY_OUT.relative_to(REPO)}")
    print(f"[r29-assemble] judge packet -> {PACKET_OUT.relative_to(REPO)}")
    print(f"[r29-assemble] rows: {len(rows)} "
          f"(interventions {sum(1 for r in rows if str(r['question_type']).startswith('intervention'))}, "
          f"predictors {sum(1 for r in rows if str(r['question_type']).startswith('predictor'))})")
    dirty = [p for p, s in sb_status.items() if not s["clean"]]
    print(f"[r29-assemble] final scan read on 18 interventions: "
          f"{n_clean}/18 fully clean "
          f"(residuals disclosed: {dirty})")
    ol_bad = [p for p, s in sb_status.items()
              if s["operational_loss"]]
    print(f"[r29-assemble] AM27 D1 acceptance (0 rows with unpriced "
          f"operational loss): {'MET' if not ol_bad else 'NOT MET: ' + str(ol_bad)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

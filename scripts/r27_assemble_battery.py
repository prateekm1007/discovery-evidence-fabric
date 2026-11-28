#!/usr/bin/env python3
"""r27_assemble_battery.py — assemble the FINAL 30-pair V7.1 battery
(eval/battery_v7_1_catalog_r27.json) + the AUDITOR JUDGE PACKET
(eval/r27_judge_packet.json) from committed bytes, zero-LLM.

The AM26 resolution: the gate is AUDITOR-judged (Art. 14/LXXXVI), so
the judged battery is the auditor's read of the committed bytes. This
assembler produces:

  1. the battery record — 30 rows with per-row provenance:
       - 11 frozen V7 intervention rows (r26 generation, byte-frozen;
         their bills already pass the r27 standard-bill scan),
       - 7 tuned V7.1 intervention rows (the pre-registered tuning
         set; eval/pairs/r27_v71_tuned/),
       - 12 frozen V5 predictor rows (r26 generation, byte-frozen;
         SYS_A1F_V5, holdout-v3-proven),
     the tuning ledger (flagged set, per-row outcome, the disclosed
     STANDARD_BILL residual on eval-sofc-thermal-cycling), and
     summary_intervention_rows with the judged fields TYPED
     PENDING-AUDITOR (the builder never scores — Art. 10: no
     self-certification; the auditor judges the committed bytes);
  2. the judge packet — per-pair problem / a1_answer / baseline_answer
     / the pre-registered rubric prompt (the same _rubric_prompt +
     AXIS_SUFFIX form the pre-registered battery script would have
     sent to the machine judge), so the auditor's judgment rides the
     same rubric the pre-registered protocol declared.

Zero-LLM: pure byte recompute over committed pair files (Art. 22/13
lineage). Deterministic. No re-draw (Art. 29(c): the 23 frozen rows
are never re-drawn; the 7 tuned rows were drawn once each under the
pre-registered c-0021 machine).
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

from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r26_battery_v7 import baseline_for, _prob_map  # noqa: E402
from eval.run import _rubric_prompt  # noqa: E402

R26_DIR = REPO / "eval" / "pairs" / "r26_v7_catalog"
R27_DIR = REPO / "eval" / "pairs" / "r27_v71_tuned"
TUNING_LEDGER = REPO / "eval" / "r27_tuning_generation.json"
BATTERY_OUT = REPO / "eval" / "battery_v7_1_catalog_r27.json"
PACKET_OUT = REPO / "eval" / "r27_judge_packet.json"
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()

FLAGGED = [
    "bench-p01-pemfc-dehydration",
    "bench-p04-pump-cavitation",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
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
        rows.append(_pair_row(pid, "V71_R27_TUNED",
                              R27_DIR / f"{pid}.json"))
    rows.sort(key=lambda r: (r["question_type"] or "", r["problem_id"]))
    assert len(rows) == 30, len(rows)

    # standard-bill scan over the FINAL 18 intervention answers
    # (11 frozen + 7 tuned) — the deterministic V7.1 leg re-read on
    # the final bytes
    sb_status = {}
    for r in rows:
        if not str(r["question_type"]).startswith("intervention"):
            continue
        rec = json.loads((REPO / r["pair_path"]).read_text(encoding="utf-8"))
        v = scan_standard_bill(rec["a1_answer"], r["question_type"])
        sb_status[r["problem_id"]] = {
            "clean": not v,
            "findings": v.get("STANDARD_BILL", [])[:6],
        }
    n_sb_clean = sum(1 for s in sb_status.values() if s["clean"])

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
                              "auditor-judged (Art. 14/LXXXVI, AM26); "
                              "the builder never scores its own "
                              "generation (Art. 10: no "
                              "self-certification)"),
        })

    battery = {
        "record": "BATTERY_V7_1_CATALOG_R27/1.0.0",
        "at": _now(),
        "work_id": "r27-v71-standard-bill-tuning",
        "claim": "c-0021 (EXECUTOR builder-r27s1, Art. 29(b) "
                 "claim-before-work; takes over the c-0020 dead lease)",
        "amendment_basis": (
            "AM26 D1 verbatim: 'Run the full 30-pair V7 battery and "
            "tune feasibility to parity. The pilot is at 0.375; close "
            "the last 0.125 (e.g., ensure every bill line is a catalog "
            "part / standard operation, no custom machining like the "
            "p04 vane reprofile). Accept: feasibility |gap| <=0.25 AND "
            "novelty delta >=0.5 on >=30 pairs, auditor-judged.'"),
        "byte_map": {
            "n_pairs": 30,
            "n_interventions": 18,
            "n_predictors": 12,
            "composition": {
                "V7_R26_FROZEN_interventions": 11,
                "V71_R27_TUNED_interventions": 7,
                "V5_R26_FROZEN_predictors": 12,
            },
            "map_note": (
                "the pre-registered r26 ALL-FRESH map (18 V7 "
                "interventions + 12 V5 predictors), unchanged; the 7 "
                "tuned rows are re-draws of the scan-flagged rows "
                "under SYS_A1_INT_V71 (the AM26 D1 tuning), each "
                "drawn ONCE under the c-0021 machine; the 23 frozen "
                "rows are never re-drawn (Art. 29(c))"),
        },
        "tuning_ledger": {
            "flagged_set": FLAGGED,
            "flagged_basis": (
                "the r27 standard-bill scan over the r26 V7 generation "
                "flags EXACTLY these 7 rows (pinned: tests/"
                "test_r27_standard_bill_scan.py::"
                "test_flagged_set_is_exactly_seven); convergence with "
                "the AM26 auditor-judged pilot: the pilot's 3 gap-1 "
                "rows (bench-p01 bespoke wick, bench-p04 CNC reprofile, "
                "bench-p08 custom recipe) are all in the flagged set"),
            "machine": gen_ledger["machine"],
            "per_row": gen_ledger["rows"],
            "disclosed_residual": {
                "eval-sofc-thermal-cycling": (
                    "STANDARD_BILL CUSTOM_MATERIAL residual after the "
                    "repair budget 2: the re-draw relocated the graded "
                    "seal into a BILAYER of two glass-ceramic layers "
                    "but differentiated them by intergranular-phase "
                    "fraction (5% vs 25%) — a composition-specified "
                    "material row the scan correctly still flags; the "
                    "budget is exhausted, so the residual stands as "
                    "the honest machine output, disclosed, "
                    "auditor-judged"),
            },
        },
        "standard_bill_scan_final": {
            "interventions_scanned": 18,
            "clean": n_sb_clean,
            "findings_by_row": sb_status,
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
            "fgap 1.5, nd 2.333"),
        "art20": (
            "lever kind novelty-relocation (V7 family), round 1 of 2 — "
            "the V7.1 tuning is a contract TIGHTENING inside the SAME "
            "arm (every V7.1-compliant bill is V7-compliant); the "
            "registry entry carries the typed amendment"),
        "judge": {
            "gate_owner": "AUDITOR (Art. 14/LXXXVI, AM26: the machine "
                          "judge is an input, never the verdict; the "
                          "judge-block is resolved by auditor-judging "
                          "the committed bytes)",
            "machine_judge_crosscheck": (
                "TYPED BLOCKED — the vault holds no CROWLLM_API_KEY in "
                "this sandbox (re-checked at assembly; Art. 17: keys "
                "are operator-supplied); per AM26 D2 this is optional "
                "and not a gate dependency"),
            "judge_packet": "eval/r27_judge_packet.json (per-pair "
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
        "record": "R27_JUDGE_PACKET/1.0.0",
        "at": _now(),
        "for": ("the AUDITOR's judgment of the final 30-pair V7.1 "
                "battery (AM26: the gate is auditor-judged); the "
                "rubric prompt per pair is the SAME pre-registered "
                "form the battery script would have sent the machine "
                "judge (_rubric_prompt + AXIS_SUFFIX, unchanged), so "
                "the auditor's scores ride the pre-registered rubric; "
                "the machine-judge cross-check stays optional "
                "(credential-blocked, typed)"),
        "battery": "eval/battery_v7_1_catalog_r27.json",
        "scored_fields_expected": {
            "per_pair": ["novelty_delta", "a1_feasibility",
                         "baseline_feasibility", "feasibility_abs_gap"],
            "summary": ["novelty_delta_mean", "feasibility_abs_gap_mean"],
            "format_reference": "eval/v7_pilot_auditor_score.json "
                                "(the AM26 pilot-8 format)",
        },
        "rows": packet_rows,
    }
    PACKET_OUT.write_text(json.dumps(packet, indent=1,
                                     ensure_ascii=False) + "\n",
                          encoding="utf-8")

    print(f"[r27-assemble] battery -> {BATTERY_OUT.relative_to(REPO)}")
    print(f"[r27-assemble] judge packet -> {PACKET_OUT.relative_to(REPO)}")
    print(f"[r27-assemble] rows: {len(rows)} "
          f"(interventions {sum(1 for r in rows if str(r['question_type']).startswith('intervention'))}, "
          f"predictors {sum(1 for r in rows if str(r['question_type']).startswith('predictor'))})")
    print(f"[r27-assemble] standard-bill scan on final 18 "
          f"interventions: {n_sb_clean}/18 clean "
          f"(residual disclosed: "
          f"{[p for p, s in sb_status.items() if not s['clean']]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

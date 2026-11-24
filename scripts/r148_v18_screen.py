#!/usr/bin/env python3
"""r148s1 v18 screen — the r146-strengthened screen's rubric adapted
to the v18 rows (claim c-0258). Byte-faithful to the twin's
instrument: the generation-time gate reconstructed with the
ENGINE-PREDICTED mech class + the cross_domain input (the
inspiration analogies' first from_domain, re-derived deterministically
from the failure class), the two off-target invocation shapes with
the negation-artifact filter, and the independent pint quant recompute.
The DIR-2 delta surface: the physics-validation verdicts ride the rows.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys_paths = [str(REPO), str(REPO / "scripts")]
import sys  # noqa: E402
for pth in sys_paths:
    if pth not in sys.path:
        sys.path.insert(0, pth)

import r146_strengthened_screen as scr  # noqa: E402  (the constants)
from discovery_fabric.generation.mechanism_map import (  # noqa: E402
    classify_failure, select_mechanism)
from discovery_fabric.generation import novelty_gate as ng  # noqa: E402
from discovery_fabric.generation import (  # noqa: E402
    inspiration_retrieval as ir)
from discovery_fabric.generation.quant_generic import (  # noqa: E402
    emit_prediction_generic)

OUT = REPO / "eval" / "holdout_v18_generation"
OUT_SCREEN = REPO / "eval" / "holdout_v18_screen.json"


def main() -> int:
    out = subprocess.run(
        ["git", "show",
         "origin/audit/r11-auditor-verdict-20261114:eval/holdout_v17/"
         "problems.json"], capture_output=True, text=True)
    sealed = json.loads(out.stdout)
    probs = sealed.get("problems") if isinstance(sealed, dict) else sealed
    sealed_by_id = {p["problem_id"]: p for p in probs}

    rows = []
    for f in sorted(OUT.glob("v17-*.json")):
        d = json.loads(f.read_text())
        ans = d["a1_answer"]
        pv_ = d.get("physics_validation") or {}
        sp = sealed_by_id.get(d["problem_id"], {})
        problem_text = str(sp.get("problem", "") or
                           d.get("domain", ""))
        sel = classify_failure(problem_text)
        eng_class = (sel.allowed_mech_classes or [""])[0]
        # the cross_domain input: the inspiration analogies' first
        # from_domain (deterministic from the failure class)
        try:
            insp = ir.retrieve_inspiration(sel.failure_class)
            analogies = insp.get("analogies") or []
            rec_xd = str((analogies[0] or {}).get("from_domain") or "") \
                if analogies else ""
        except Exception:  # noqa: BLE001
            rec_xd = ""
        sel_gen = type("S", (), {"selected_mech_class": eng_class,
                                 "cross_domain": rec_xd,
                                 "off_target": False,
                                 "off_target_reason": ""})()
        gate_gen = ng.gate(ans, sel_gen)
        gate = ng.gate(ans, sel_gen)  # the screen gate (same shape)
        sel_problem = select_mechanism(str(sp.get("problem", "")), ans)
        sel_domain = select_mechanism(str(d.get("domain", "")), ans)
        try:
            rq = emit_prediction_generic(sel.failure_class, ans)
        except Exception as e:  # noqa: BLE001
            rq = {"status": "compute_error",
                  "error": f"{type(e).__name__}: {e}"}
        rows.append({
            "problem_id": d["problem_id"],
            "failure_class": sel.failure_class,
            "engine_prediction_mech_class": eng_class,
            "cross_domain_input": rec_xd,
            "recomputed_quant_status": rq.get("status"),
            "recomputed_quant_computed": rq.get("status") == "computed",
            "novelty_gate_generation_time": gate_gen.get("novelty"),
            "novelty_gate_screen": gate.get("novelty"),
            "quant_markers": gate.get("quant_markers"),
            "physics_verdict": pv_.get("verdict"),
            "physics_n_errors": pv_.get("n_errors"),
            "off_target_measured_problem_shape": {
                "flag": bool(sel_problem.off_target),
                "negation_artifact": scr._negated_flag(
                    ans, sel_problem.off_target_reason),
                "reason": (sel_problem.off_target_reason or None),
                "class": sel_problem.failure_class},
            "off_target_measured_domain_shape": {
                "flag": bool(sel_domain.off_target),
                "negation_artifact": scr._negated_flag(
                    ans, sel_domain.off_target_reason),
                "reason": (sel_domain.off_target_reason or None),
                "class": sel_domain.failure_class},
            "has_numeric_unit": bool(scr.NUM_UNIT.search(ans)),
            "has_falsified_wording": bool(scr.FALSIFIED.search(ans)),
            "has_test_vehicle": bool(scr.TEST_VEHICLE.search(ans)),
            "nonobviousness_sections": {
                "NOVELTY_STATEMENT_header": bool(
                    scr.NOVELTY_HDR.search(ans)),
                "non_obvious_arrangement_stated": bool(
                    scr.NONOBV_ARR.search(ans)),
                "obvious_adjustment_rejection": bool(
                    scr.OBVKNOB2.search(ans)),
                "s2_section_vocabulary_present": bool(
                    scr.NONOBV.search(ans)),
            },
            "chars": len(ans),
            "sha256_16": d.get("sha256_16"),
        })

    n = len(rows)
    ot_dom_clean = sum(1 for r in rows
                       if not r["off_target_measured_domain_shape"]["flag"]
                       or r["off_target_measured_domain_shape"]
                       ["negation_artifact"])
    ot_prob_clean = sum(1 for r in rows
                        if not r["off_target_measured_problem_shape"]["flag"]
                        or r["off_target_measured_problem_shape"]
                        ["negation_artifact"])
    strong = sum(1 for r in rows
                 if r["novelty_gate_generation_time"] == "strong")
    phys_err = sum(1 for r in rows if (r["physics_n_errors"] or 0) > 0)
    rec = {
        "record": "V18_BUILDER_SCREEN/1.0.0 — the r146 screen rubric "
                  "adapted to the v18 rows (the physics-gated "
                  "re-generation, claim c-0258)",
        "at": "2026-11-24 (sandbox clock)",
        "executor": "builder-r148s1 (the c-0258 physics lane)",
        "subject": str(OUT) + "/",
        "method": ("every surface number recomputed from the row "
                   "bytes; the generation-time gate reconstructed "
                   "with the engine-predicted mech class + the "
                   "cross_domain input; the off-target measured in "
                   "both invocation shapes with the negation-artifact "
                   "filter; the pint quant layer re-run per row"),
        "n": n,
        "dir2_surface": {
            "novelty_gate_generation_time_reconstructed": dict(
                Counter(r["novelty_gate_generation_time"]
                        for r in rows)),
            "strong_count_generation_time": strong,
            "strong_pct_generation_time": round(100 * strong / n, 1)
            if n else 0,
            "off_target_domain_shape_clean": ot_dom_clean,
            "off_target_problem_shape_clean": ot_prob_clean,
        },
        "physics_surface": {
            "rows_physics_pass": sum(1 for r in rows
                                     if r["physics_verdict"] == "PASS"),
            "rows_genuine_physics_errors": phys_err,
            "note": "the generation-time gate only emits PASS rows",
        },
        "quant_surface": {
            "recomputed_computed": sum(1 for r in rows
                                       if r["recomputed_quant_computed"]),
        },
        "per_row": rows,
    }
    OUT_SCREEN.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"v18 screen: n={n} | strong {strong}/{n} "
          f"({rec['dir2_surface']['strong_pct_generation_time']}%) | "
          f"off-target clean (domain/problem): "
          f"{ot_dom_clean}/{ot_prob_clean} | physics errors: "
          f"{phys_err} | quant computed: "
          f"{rec['quant_surface']['recomputed_computed']}/{n}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

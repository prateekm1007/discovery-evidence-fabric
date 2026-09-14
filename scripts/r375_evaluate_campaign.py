#!/usr/bin/env python
"""R375 evaluation layer — frozen-evaluator comparison of the GENERATED
new-invention packages against the 15 benchmark dossiers.

For every campaign run that produced a package:
  1. E15-B substantive dimension verdicts (already persisted per run by
     the conductor; read back, never recomputed differently).
  2. E16-H holdout release gate verdicts (read back).
  3. E15-A/E15-J frozen-corpus floor comparison: the identical 16
     instruments applied to the generated package, compared against the
     frozen contract floors (min) and targets (median) — floors are
     LOADED, never modified.
  4. Equation status split (STRUCTURAL / APPLICABILITY / DIMENSIONAL)
     from the package's EQUATION_REGISTRY-equivalent fields.
  5. UNKNOWN honesty: count of UNKNOWN-class fields carrying a
     resolution path vs bare unknowns.
  6. Mechanism substantive-parity elements (CEO R375-6): physical
     principle / causal operation / components / interfaces /
     constraints / critical parameters / failure consequences —
     measured from the persisted engineering specification, each element
     present only when non-empty and non-UNKNOWN.

Aggregate: per-dimension PASS/COUNT table + strict/honest acceptance
counts. Art. XXVI: BUILDER-MEASURED, deterministic, offline.

Usage: python scripts/r375_evaluate_campaign.py [--out <path>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# R455-LEAN-1 reconciliation: calibration_v2/v3 were retired to
# archive/r455-lean/ (ONE canonical archive; it carries a hyphen and is
# deliberately not on the import path). The archived bytes are loaded
# verbatim under their canonical module names so this kept surface
# stays importable (Art. LXIV: importable history; the r440_retired
# importlib precedent).
import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

_REPO_ROOT = _Path(__file__).resolve().parents[1]


def _load_archived(rel: str, name: str):
    if name in _sys.modules:
        return _sys.modules[name]
    _spec = _ilu.spec_from_file_location(name, _REPO_ROOT / rel)
    _mod = _ilu.module_from_spec(_spec)
    _sys.modules[name] = _mod
    _spec.loader.exec_module(_mod)
    return _mod


_load_archived("archive/r455-lean/discovery_fabric/engine/benchmark_corpus.py",
    "discovery_fabric.engine.benchmark_corpus")
_load_archived("archive/r455-lean/discovery_fabric/engine/benchmark_dossiers.py",
    "discovery_fabric.engine.benchmark_dossiers")
from discovery_fabric.engine.benchmark_dossiers import (  # noqa: E402
    load_contract, measure_generated_vector, meets_floors)
from discovery_fabric.engine.dossier_quality import DIMENSIONS  # noqa: E402

M1_DIR = REPO / "discovery_campaigns" / "M1_DOSSIER_CAMPAIGN_2026-08-29"

#: CEO R375-6 mechanism substantive-parity elements -> (spec, eng) field
#: paths that evidence each element (schema verified against the
#: generated ENGINEERING_SPECIFICATION.json on 2026-08-30; a missing
#: field => element ABSENT; an UNKNOWN-valued field => element honestly
#: unresolved, never padded).
MECHANISM_ELEMENTS = {
    "physical_principle": ("eng", "mechanism_architecture", "key_physics"),
    "causal_operation": ("eng", "engineering_core", "governing_model",
                         "summary"),
    "components": ("eng", "system_architecture", "subsystems"),
    "interfaces": ("eng", "interfaces"),
    "constraints": ("eng", "engineering_core", "governing_model",
                    "boundary_conditions"),
    "critical_parameters": ("eng", "engineering_core",
                            "critical_parameters"),
    "failure_consequences": ("eng", "engineering_core", "failure_modes"),
}

UNKNOWN_MARKERS = ("NOT ESTABLISHED", "UNKNOWN", "NOT_ASSIGNED",
                   "NOT_PERFORMED", "NOT_LINKED")


def _dig(obj, path):
    for k in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


def _is_unknown(v) -> bool:
    if v is None:
        return True
    s = str(v).strip()
    if not s:
        return True
    return any(m in s.upper() for m in UNKNOWN_MARKERS)


def evaluate_run(run_record: dict) -> dict | None:
    pkg = run_record.get("package") or {}
    if not pkg.get("folder"):
        return None
    run_dir = REPO / run_record["run_dir"]
    out: dict = {
        "problem_id": run_record.get("problem_id"),
        "candidate_id": run_record.get("candidate_id"),
        "territory": run_record.get("territory_id"),
        "device": run_record.get("device"),
        "run_dir": run_record.get("run_dir"),
        "package_folder": pkg.get("folder"),
        "package_zip": pkg.get("zip"),
        "release_class": run_record.get("release_class"),
        "final_status": run_record.get("final_status"),
    }

    # 1. E15-B (persisted authority — read back, never recomputed)
    q = run_dir / "DOSSIER_QUALITY_EVALUATION.json"
    if q.exists():
        quality = json.loads(q.read_text())
        out["e15b_verdict"] = quality.get("verdict")
        out["e15b_dimensions"] = {
            d["dimension"]: {"verdict": d["verdict"],
                             "measured": d.get("measured")}
            for d in quality.get("dimensions", [])}
        out["e15b_deficient_areas"] = quality.get("deficient_areas", [])
    else:
        out["e15b_verdict"] = "NOT_EVALUATED"

    # 2. E16-H (persisted authority)
    g = run_dir / "RELEASE_GATE_EVALUATION.json"
    if g.exists():
        gate = json.loads(g.read_text())
        out["e16h_decision"] = gate.get("decision")
        verdicts = gate.get("verdicts")
        out["e16h_verdicts"] = (verdicts if isinstance(verdicts, dict)
                                else json.loads(verdicts)
                                if isinstance(verdicts, str) else {})
    else:
        out["e16h_decision"] = "NOT_EVALUATED"

    # 3. frozen-corpus floor comparison (identical instruments)
    spec_p = run_dir / "INVENTION_SPECIFICATION.json"
    eng_p = run_dir / "ENGINEERING_SPECIFICATION.json"
    if spec_p.exists() and eng_p.exists():
        spec = json.loads(spec_p.read_text())
        eng = json.loads(eng_p.read_text())
        try:
            vector = measure_generated_vector(spec, eng, {"folder":
                                                          pkg["folder"]})
            out["benchmark_comparison"] = meets_floors(vector)
        except Exception as exc:  # noqa: BLE001 — recorded, never hidden
            out["benchmark_comparison"] = {"error": f"{type(exc).__name__}: {exc}"}

        # 4. equation status split (honest, three-level — R374-2 language;
        #    applicability carries the judged condition per equation)
        eqs = ((eng.get("engineering_core") or {}).get("governing_model")
               or {}).get("equations", []) or []
        statuses = {}
        for e in eqs:
            st = str(e.get("status") or "PRESENT").upper()
            app = e.get("applicability") or {}
            if isinstance(app, dict) and app.get("condition"):
                st = f"{st}/APPLICABILITY_JUDGED"
            statuses[st] = statuses.get(st, 0) + 1
        out["equations"] = {"total": len(eqs), "status_split": statuses}

        # 6. mechanism substantive-parity elements
        elements = {}
        for name, path in MECHANISM_ELEMENTS.items():
            src = spec if path[0] == "spec" else eng
            v = _dig(src, path[1:])
            if v is None or (isinstance(v, (list, dict)) and not v) or \
                    (isinstance(v, str) and not v.strip()):
                elements[name] = "ABSENT"
            elif isinstance(v, (list, dict)):
                # a populated structure is PRESENT even when individual
                # sub-fields honestly record UNKNOWN values (Art. XXV:
                # the unknown is content, not absence)
                elements[name] = "PRESENT"
            elif _is_unknown(v):
                elements[name] = "UNKNOWN_HONEST"
            else:
                elements[name] = "PRESENT"
        out["mechanism_elements"] = elements

    # 5. UNKNOWN honesty (UNKNOWN fields WITH resolution path)
    folder = Path(pkg["folder"])
    unknown_total = 0
    unknown_with_path = 0
    for jf in folder.glob("*.json"):
        try:
            data = json.loads(jf.read_text())
        except Exception:  # noqa: BLE001
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for k, v in node.items():
                    ku = str(k).upper()
                    if ("UNKNOWN" in ku or "NOT_ESTABLISHED" in ku
                            or ku == "STATUS" and _is_unknown(v)):
                        unknown_total += 1
                        resolution = any(
                            key in node for key in
                            ("what_would_resolve_it", "resolution_path",
                             "how_to_establish", "resolution"))
                        if resolution:
                            unknown_with_path += 1
                    stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
    out["unknown_quality"] = {
        "unknown_fields": unknown_total,
        "with_resolution_path": unknown_with_path,
        "coverage": round(unknown_with_path / unknown_total, 3)
        if unknown_total else None,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(
        REPO / "discovery_campaigns" /
        "R375_NEW_INVENTION_CAMPAIGN_2026-08-30"))
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for p in sorted(M1_DIR.glob("RUN_*.json"),
                    key=lambda x: int(x.stem.split("_")[1])):
        r = json.loads(p.read_text())
        ev = evaluate_run(r)
        if ev:
            ev["campaign_index"] = int(p.stem.split("_")[1])
            records.append(ev)

    # aggregate per-dimension table
    dim_table = {}
    for dim in DIMENSIONS:
        verdicts = [r.get("e15b_dimensions", {}).get(dim, {}).get("verdict")
                    for r in records]
        dim_table[dim] = {
            "PASS": verdicts.count("PASS"),
            "CONDITIONAL": verdicts.count("CONDITIONAL"),
            "FAIL": verdicts.count("FAIL"),
            "not_evaluated": sum(1 for v in verdicts
                                 if v not in ("PASS", "CONDITIONAL", "FAIL")),
            "of_packages": len(records),
        }
    floor_passes = sum(
        1 for r in records
        if (r.get("benchmark_comparison") or {}).get("passed") is True)
    strict_quality = sum(1 for r in records if r.get("e15b_verdict") == "PASS")
    honest_quality = sum(1 for r in records if r.get("e15b_verdict") in
                         ("PASS", "CONDITIONAL"))
    released = sum(1 for r in records if r.get("e16h_decision") == "RELEASED")
    held = sum(1 for r in records
               if r.get("e16h_decision") == "HELD_FOR_HUMAN_REVIEW")

    summary = {
        "directive": "CEO R375 (2026-08-30) — prove the engine can "
                     "reproduce the portfolio standard on new inventions",
        "frozen_evaluator": "E15-B dossier_quality + E15-A/E15-J frozen "
                            "corpus floors (LOADED, unmodified) + E16-H "
                            "holdout release gate",
        "floors_lowered": False,
        "packages_evaluated": len(records),
        "e15b_strict_all_pass": strict_quality,
        "e15b_pass_or_conditional": honest_quality,
        "e16h_released": released,
        "e16h_held_for_human_review": held,
        "frozen_floor_all_pass": floor_passes,
        "dimension_table": dim_table,
        "acceptance_note": (
            "CEO R375-8 acceptance = at least 5 genuinely new inventions "
            "reaching AUTOMATIC ENGINEERING SPECIFICATION + AUTOMATIC "
            "COMPLETE DOSSIER + INDEPENDENT QUALITY PASS without "
            "hand-written repair. This report presents the measured "
            "counts under the frozen instruments; it does not adjust any "
            "floor or verdict to reach the target."),
    }
    (out_dir / "R375_EVALUATION.json").write_text(json.dumps(
        {"summary": summary, "packages": records}, indent=1,
        ensure_ascii=False, default=str))
    print(json.dumps(summary, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

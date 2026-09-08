#!/usr/bin/env python3
"""scripts/r425_extract_p07_benchmark.py — R425 §9 benchmark extraction.

Freezes the CONTENT metrics of the released elite portfolio's strongest
engineering package (P-07, prateekm1007/technology-transfer-portfolio-15
DOWNLOAD/07_self_powered_sensing) into
tests/fixtures/r425/p07_benchmark.json — the frozen reference the
independent package-quality auditor compares fresh packages against BY
CONTENT, not by filename.

The frozen benchmark is a METRIC SNAPSHOT with its own provenance
(portfolio commit, extractor sha) — it is not a copy of buyer bytes.
Re-run this script against a clean clone to refresh the benchmark.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_PORTFOLIO = Path(
    "/home/z/my-project/repos/portfolio/DOWNLOAD/07_self_powered_sensing")
OUT = REPO / "tests" / "fixtures" / "r425" / "p07_benchmark.json"


def _load(pkg_dir: Path, name: str):
    p = pkg_dir / name
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except ValueError:
        return None


def _portfolio_commit(portfolio_root: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(portfolio_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:  # noqa: BLE001 — provenance honest, never fatal
        pass
    return "UNKNOWN (portfolio root not a git checkout)"


def extract(pkg_dir: Path, portfolio_root: Path) -> dict:
    eq = _load(pkg_dir, "EQUATION_REGISTRY.json") or {}
    tr = _load(pkg_dir, "ENGINEERING_TRACEABILITY.json") or {}
    ur = _load(pkg_dir, "UNKNOWN_ROADMAP.json") or {}
    mb = _load(pkg_dir, "MATURITY_BASIS.json") or {}
    ve = _load(pkg_dir, "VALIDATION_ECONOMICS.json") or {}
    ce = _load(pkg_dir, "COMMERCIAL_EVIDENCE.json") or {}
    ls = _load(pkg_dir, "LOOP_STATE.json") or {}
    pm = _load(pkg_dir, "PACKAGE_MANIFEST.json") or {}
    equations = eq.get("equations") or []
    unknowns = ur.get("unknowns") or []
    model_dir = pkg_dir / "MODEL"
    ev_dir = model_dir / "3D_EVIDENCE"

    def _step_files(d: Path, suffix: str) -> int:
        return len([p for p in d.iterdir()
                    if p.is_file() and p.suffix == suffix]) \
            if d.is_dir() else 0

    return {
        "benchmark_id": "P07_CONTENT_BENCHMARK",
        "provenance": {
            "portfolio": "prateekm1007/technology-transfer-"
                         "technology-transfer-portfolio-15",
            "package": "DOWNLOAD/07_self_powered_sensing",
            "portfolio_commit": _portfolio_commit(portfolio_root),
            "extractor": "scripts/r425_extract_p07_benchmark.py",
            "note": "content metrics extracted from the released "
                    "package bytes; refresh by re-running against a "
                    "clean clone",
        },
        "equation_depth": {
            "equation_count": eq.get("equation_count",
                                     len(equations)),
            "with_math_expression": sum(
                1 for e in equations if e.get("math_expression")),
            "with_typeset": sum(
                1 for e in equations if e.get("typeset")),
            "with_caption": sum(
                1 for e in equations if e.get("caption")),
            "with_units": sum(
                1 for e in equations if e.get("units")),
            "avg_variables_per_equation": round(sum(
                len(e.get("variables") or []) for e in equations)
                / max(len(equations), 1), 2),
            "avg_assumptions_per_equation": round(sum(
                len(e.get("assumptions") or []) for e in equations)
                / max(len(equations), 1), 2),
            "with_unit_status_resolution_paths": sum(
                1 for e in equations
                if e.get("r374_unit_status")),
        },
        "traceability_depth": {
            "chains": len(tr.get("chains") or []),
            "orphan_design_outputs": len(
                tr.get("orphan_design_outputs") or []),
            "orphan_failure_modes": len(
                tr.get("orphan_failure_modes") or []),
            "has_release_gate": bool(tr.get("release_gate")),
            "has_truth_model": bool(tr.get("truth_model")),
            "has_three_d_design": bool(tr.get("three_d_design")),
            "has_legacy_record": bool(tr.get("legacy_r370_record")),
        },
        "unknown_specificity": {
            "unknown_count": len(unknowns),
            "avg_fields_per_entry": round(sum(
                len(u) for u in unknowns) / max(len(unknowns), 1), 2),
            "with_resolution_action": sum(
                1 for u in unknowns if u.get("resolution_action")),
            "with_expected_output": sum(
                1 for u in unknowns if u.get("expected_output")),
            "with_decision_impact": sum(
                1 for u in unknowns if u.get("decision_impact")),
            "with_linked_build_plan_step": sum(
                1 for u in unknowns
                if u.get("linked_build_plan_step")),
            "distinct_resolution_actions": len({
                json.dumps(u.get("resolution_action"),
                           sort_keys=True) for u in unknowns}),
        },
        "maturity_honesty": {
            "technology_maturity": mb.get("technology_maturity"),
            "evidence_id_families": len([k for k in mb
                                         if k.endswith("_evidence_ids")]),
            "basis_recorded": bool(mb.get("basis")),
        },
        "validation_economics": {
            "has_decision_threshold": bool(
                ve.get("decision_threshold")),
            "sections": len(ve.get("sections") or []),
        },
        "commercial_evidence": {
            "sections": len(ce.get("sections") or []),
        },
        "loop_state": {
            "loop_verification_state": ls.get(
                "loop_verification_state"),
        },
        "model_layer": {
            "step_files": _step_files(model_dir, ".step"),
            "stl_files": _step_files(model_dir, ".stl"),
            "svg_views": _step_files(model_dir, ".svg"),
            "glb_files": _step_files(model_dir, ".glb"),
            "has_parametric_source": (model_dir
                                      / "PARAMETRIC_MODEL_SOURCE.py"
                                      ).is_file(),
            "evidence_files": _step_files(ev_dir, ".json")
            + _step_files(ev_dir, ".step")
            + _step_files(ev_dir, ".stl"),
            "manifest_hashed_files": len(pm.get("files") or []),
        },
        "documents": {
            "pdf_count": len([p for p in pkg_dir.iterdir()
                              if p.suffix == ".pdf"]),
        },
    }


def main() -> int:
    portfolio_root = DEFAULT_PORTFOLIO
    pkg_dir = portfolio_root
    if len(sys.argv) > 1:
        pkg_dir = Path(sys.argv[1])
        portfolio_root = pkg_dir.parents[2]
    if not pkg_dir.is_dir():
        print(f"package dir not found: {pkg_dir}", file=sys.stderr)
        return 2
    data = extract(pkg_dir, portfolio_root)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"wrote {OUT} (sha256 {digest[:16]}…, "
          f"portfolio commit {data['provenance']['portfolio_commit'][:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

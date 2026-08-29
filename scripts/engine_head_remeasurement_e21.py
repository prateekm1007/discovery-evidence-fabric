#!/usr/bin/env python3
"""E21-D: re-measure the 15 independent benchmark inputs at the E21 head.

Same methodology as scripts/engine_head_remeasurement.py (CODER2
P4-INTEGRATION): regenerate all 15 runs through the engine's real
offline pipeline (rehearsal; no live credentials — hermetic), then
audit every produced dossier with the FROZEN instruments (audit_run,
read-only). DISCLOSURE: this is a BUILDER-measured number pending the
CEO's independent audit; the frozen baseline (3/15 at fbd113b) and the
E16-merge re-measurement (HELD=3/FAILED=12 at 1ff2d707) are the
prior reference rows and are NOT modified.
"""
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.benchmark import audit_runner, corpus_runner  # noqa: E402


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def main() -> int:
    engine_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True).stdout.strip()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        info = corpus_runner.run_benchmark(root, limit=15)
        statuses = {}
        produced = []
        for p in info["run_dirs"]:
            rd = Path(p)
            rel = json.loads((rd / "DISCOVERY_RELEASE.json")
                             .read_text(encoding="utf-8"))
            statuses[rd.name] = rel.get("status")
            has_dossier = bool(rel.get("package_folder") and
                               Path(rel["package_folder"]).exists())
            produced.append({
                "run_id": rd.name,
                "status": rel.get("status"),
                "complete_dossier_on_disk": has_dossier,
                "failure_reason": rel.get("failure_reason"),
                "run_dir": str(rd)})

        contract = json.loads(
            (REPO_ROOT / "artifacts/benchmark/"
             "ENGINEERING_DEPTH_CONTRACT.json").read_text(encoding="utf-8"))
        profile = json.loads(
            (REPO_ROOT / "artifacts/benchmark/"
             "BENCHMARK_DOSSIER_PROFILE.json").read_text(encoding="utf-8"))
        audits = {}
        for p in produced:
            if not p["complete_dossier_on_disk"]:
                continue
            try:
                audits[p["run_id"]] = audit_runner.audit_run(
                    Path(p["run_dir"]), contract, profile)
            except Exception as exc:  # honest per-run failure
                audits[p["run_id"]] = {"audit_error": str(exc)}

        rows = []
        for p in produced:
            row = dict(p)
            a = audits.get(p["run_id"])
            if a and "quality_evaluation" in a:
                dims = a["quality_evaluation"].get("dimensions", {})
                failing = [k for k, v in dims.items()
                           if isinstance(v, dict)
                           and v.get("verdict") in ("FAIL",)]
                sem = a.get("semantic_causal") or {}
                incorrect = 0
                for c in sem.get("chains", []) or []:
                    for lv in c.get("link_verdicts", []) or []:
                        if lv.get("verdict") == "INCORRECT":
                            incorrect += 1
                row["failing_depth_dimensions"] = failing
                row["incorrect_critical_chains"] = incorrect
                row["frozen_instrument_verdict"] = \
                    a["quality_evaluation"].get("verdict")
            rows.append(row)

        dist = {}
        for r in rows:
            dist[r["status"]] = dist.get(r["status"], 0) + 1
        out = {
            "artifact": "ENGINE_HEAD_REMEASUREMENT_E21",
            "owner": "CODER (sole builder; former Coder 2)",
            "disclosure": ("BUILDER-MEASURED pending the CEO's independent "
                           "audit (Art. XXVI): generated AND audited in one "
                           "session; frozen instruments used READ-ONLY "
                           "(Art. XXX) and are byte-identical at HEAD"),
            "generated_at": utc(),
            "engine_head": engine_head,
            "change_series": [
                "E21-A quantity-grounded verification linkage (R-02)",
                "E21-B concept-grounded equation engagement + symbolic "
                "purity (R-05)"],
            "prior_reference_rows": {
                "frozen_baseline_fbd113b8": "RELEASED=3 / REJECTED=12",
                "e16_merge_1ff2d707": "HELD=3 / PIPELINE_FAILED=12 / "
                                      "RELEASED=0",
                "e16_failing_dims": "BENCH_01/04 SEMANTIC_CAUSAL (1 "
                                    "incorrect critical chain each); "
                                    "BENCH_09 EQUATION_APPLICABILITY"},
            "status_distribution_at_e21_head": dist,
            "rows": [{k: v for k, v in r.items() if k != "run_dir"}
                     for r in rows],
        }
        out_path = REPO_ROOT / "artifacts/benchmark/generated" / \
            "ENGINE_HEAD_REMEASUREMENT_E21.json"
        out_path.write_text(json.dumps(out, indent=1, default=str),
                            encoding="utf-8")
        print(json.dumps({"status_distribution": dist,
                          "failing_dims": {r["run_id"]: r.get(
                              "failing_depth_dimensions")
                              for r in rows
                              if r.get("complete_dossier_on_disk")},
                          "incorrect_chains": {r["run_id"]: r.get(
                              "incorrect_critical_chains")
                              for r in rows
                              if r.get("complete_dossier_on_disk")}},
                         indent=1))
        print(f"written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

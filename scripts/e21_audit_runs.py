#!/usr/bin/env python3
"""E21-D audit stage: audit the 15 persisted E21-head runs with the
FROZEN instruments (read-only) and write the measurement artifact."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.benchmark import audit_runner  # noqa: E402

RUNS_ROOT = Path("/home/z/my-project/scripts/e21_runs")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def main() -> int:
    engine_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True).stdout.strip()
    contract = json.loads(
        (REPO_ROOT / "artifacts/benchmark/"
         "ENGINEERING_DEPTH_CONTRACT.json").read_text(encoding="utf-8"))
    profile = json.loads(
        (REPO_ROOT / "artifacts/benchmark/"
         "BENCHMARK_DOSSIER_PROFILE.json").read_text(encoding="utf-8"))
    rows = []
    for idx in range(1, 16):
        rd = RUNS_ROOT / f"BENCH_{idx:02d}"
        rel = json.loads((rd / "DISCOVERY_RELEASE.json")
                         .read_text(encoding="utf-8"))
        row = {
            "run_id": rd.name,
            "status": rel.get("status"),
            "complete_dossier_on_disk": bool(
                rel.get("package_folder")
                and Path(rel["package_folder"]).exists()),
            "failure_reason": rel.get("failure_reason")}
        if row["complete_dossier_on_disk"]:
            try:
                a = audit_runner.audit_run(rd, contract, profile)
                dims = a["quality_evaluation"].get("dimensions", {})
                row["failing_depth_dimensions"] = [
                    k for k, v in dims.items()
                    if isinstance(v, dict) and v.get("verdict") == "FAIL"]
                row["conditional_depth_dimensions"] = [
                    k for k, v in dims.items()
                    if isinstance(v, dict)
                    and v.get("verdict") == "CONDITIONAL"]
                sem = a.get("semantic_causal") or {}
                incorrect = 0
                questionable = 0
                for c in sem.get("chains", []) or []:
                    for lv in c.get("link_verdicts", []) or []:
                        if lv.get("verdict") == "INCORRECT":
                            incorrect += 1
                        elif lv.get("verdict") == "QUESTIONABLE":
                            questionable += 1
                row["incorrect_critical_chains"] = incorrect
                row["questionable_links"] = questionable
                # overall verdict lives at the top level of the audit
                # record (BENCHMARK_PASS / BENCHMARK_CONDITIONAL /
                # BENCHMARK_FAIL); quality_evaluation carries
                # overall_verdict + dimension_verdicts
                row["frozen_instrument_verdict"] = a.get("verdict")
                # capture failing-dim detail for the report
                det = {}
                for k in row["failing_depth_dimensions"]:
                    det[k] = dims.get(k, {}).get("issues") or \
                        dims.get(k, {}).get("reasons")
                if det:
                    row["failing_detail"] = det
            except Exception as exc:  # honest per-run failure
                row["audit_error"] = str(exc)
        rows.append(row)

    dist = {}
    for r in rows:
        dist[r["status"]] = dist.get(r["status"], 0) + 1
    failing = {r["run_id"]: r.get("failing_depth_dimensions")
               for r in rows if r.get("complete_dossier_on_disk")}
    incorrect_total = sum(r.get("incorrect_critical_chains", 0)
                          for r in rows)
    out = {
        "artifact": "ENGINE_HEAD_REMEASUREMENT_E21",
        "owner": "CODER (sole builder; former Coder 2)",
        "disclosure": ("BUILDER-MEASURED pending the CEO's independent "
                       "audit (Art. XXVI): generated AND audited in one "
                       "session; frozen instruments used READ-ONLY "
                       "(Art. XXX), byte-identical at HEAD"),
        "generated_at": utc(),
        "engine_head": engine_head,
        "change_series": [
            "E21-A quantity-grounded verification linkage (R-02)",
            "E21-B concept-grounded equation engagement + symbolic "
            "purity (R-05)",
            "E21-C naked-number elimination at generation time "
            "(OPT-004 subtraction form; TH-001 explicit assumptions; "
            "acceptance texts number-free, values live on provenance-"
            "bearing records)"],
        "prior_reference_rows": {
            "frozen_baseline_fbd113b8": "RELEASED=3 / REJECTED=12",
            "e16_merge_1ff2d707": "HELD=3 / PIPELINE_FAILED=12 / "
                                  "RELEASED=0",
            "e16_failing_dims": "BENCH_01/04 SEMANTIC_CAUSAL (1 "
                                "incorrect critical chain each); "
                                "BENCH_09 EQUATION_APPLICABILITY"},
        "status_distribution_at_e21_head": dist,
        "totals": {
            "incorrect_critical_chains_all_runs": incorrect_total,
            "runs_with_complete_dossiers": sum(
                1 for r in rows if r["complete_dossier_on_disk"])},
        "rows": rows,
    }
    out_path = REPO_ROOT / "artifacts/benchmark/generated" / \
        "ENGINE_HEAD_REMEASUREMENT_E21.json"
    out_path.write_text(json.dumps(out, indent=1, default=str),
                        encoding="utf-8")
    print(json.dumps({"status_distribution": dist,
                      "failing_dims": failing,
                      "incorrect_total": incorrect_total}, indent=1))
    print(f"written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

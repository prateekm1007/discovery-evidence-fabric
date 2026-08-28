"""Coder 2 — ENGINE-HEAD RE-MEASUREMENT (post E16 merge).

After integrating Coder 1's E16/register-fixes state (remote commits
be3e3545..38b546d2), the engine no longer auto-RELEASES any independent
benchmark input: previously-released inputs now return
HELD_FOR_HUMAN_REVIEW (complete dossier on disk, gated pending human
review) and the rest still fail the engine's own E15-H gate.

This script MEASURES the new head with the frozen instruments and
writes an AFTER row to a NEW file (B6 discipline: the frozen 3/15
baseline at engine head fbd113b is never overwritten; AFTER rows go to
new files only).

What is measured per input:
  * engine release status at the new head (RELEASED / HELD_FOR_HUMAN_
    REVIEW / PIPELINE_FAILED);
  * whether a complete dossier exists on disk;
  * the FROZEN 13-dimension depth verdicts (corpus depth contract) for
    every produced dossier (held included);
  * the FROZEN B3 semantic causal verdict for every produced dossier.

The verdict that matters: do the HELD dossiers now PASS the frozen
depth floors and semantic gates that the previously-RELEASED dossiers
failed? If yes, Coder 1's fixes improved real content depth and only
human review stands between output and release. If no, the holds are
re-branded rejections of the same shallow output.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.benchmark import corpus_runner, audit_runner  # noqa: E402

OUT_PATH = REPO_ROOT / "artifacts/benchmark/baseline" / \
    "ENGINE_HEAD_REMEASUREMENT_E16MERGE.json"

FROZEN_BASELINE = {
    "engine_head": "fbd113b8258b378ca09f7f9ec89c4aee06f03025",
    "released": 3, "rejected": 12, "total": 15,
    "released_ids": ["BENCH_01", "BENCH_04", "BENCH_09"],
    "released_depth_verdicts": {"BENCHMARK_FAIL": 3},
}


def main() -> None:
    engine_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True).stdout.strip()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        info = corpus_runner.run_benchmark(root, limit=15)
        statuses: Dict[str, str] = {}
        produced: List[Dict[str, Any]] = []
        for p in info["run_dirs"]:
            rd = Path(p)
            rel = json.loads((rd / "DISCOVERY_RELEASE.json")
                             .read_text(encoding="utf-8"))
            name = rd.name
            statuses[name] = rel.get("status")
            has_dossier = bool(rel.get("package_folder") and
                               Path(rel["package_folder"]).exists())
            produced.append({
                "run_id": name,
                "status": rel.get("status"),
                "complete_dossier_on_disk": has_dossier,
                "failure_reason": rel.get("failure_reason"),
                "run_dir": str(rd),
            })

        # audit every produced dossier (held + released) with the FROZEN
        # instruments; engine-rejected runs have no dossier to audit.
        # NOTE: audit_batch() classifies any status not in (None,
        # RELEASED) as engine-rejected — HELD_FOR_HUMAN_REVIEW is a NEW
        # status that postdates that instrument. To measure held
        # dossiers WITHOUT modifying the shared instrument (Art. XXX),
        # audit each produced run directly via audit_run() — the same
        # frozen per-run instruments, applied per run.
        contract = json.loads(
            (REPO_ROOT / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json")
            .read_text(encoding="utf-8"))
        profile = json.loads(
            (REPO_ROOT / "artifacts/benchmark/BENCHMARK_DOSSIER_PROFILE.json")
            .read_text(encoding="utf-8"))
        audits_by_dir: Dict[str, Dict[str, Any]] = {}
        for p in produced:
            if not p["complete_dossier_on_disk"]:
                continue
            try:
                a = audit_runner.audit_run(Path(p["run_dir"]),
                                           contract, profile)
                audits_by_dir[p["run_id"]] = a
            except Exception as exc:  # honest per-run failure, recorded
                audits_by_dir[p["run_id"]] = {
                    "run_dir": p["run_dir"], "audit_error": str(exc)}
        rows = []
        for p in produced:
            a = audits_by_dir.get(p["run_id"])
            row: Dict[str, Any] = dict(p)
            if a:
                row["frozen_instrument_verdict"] = a.get("verdict")
                dims = a.get("dimension_verdicts") or {}
                row["failing_depth_dimensions"] = [
                    d for d, v in dims.items() if v == "FAIL"]
                sem = a.get("semantic_causal_audit") or {}
                row["incorrect_critical_chains"] = len(
                    sem.get("incorrect_critical_chains") or [])
            else:
                row["frozen_instrument_verdict"] = None
                row["failing_depth_dimensions"] = None
                row["incorrect_critical_chains"] = None
            rows.append(row)

    status_counts: Dict[str, int] = {}
    for s in statuses.values():
        status_counts[s] = status_counts.get(s, 0) + 1

    held = [r for r in rows
            if r["status"] == "HELD_FOR_HUMAN_REVIEW"]
    held_pass_depth = [r for r in held
                       if r.get("frozen_instrument_verdict") in
                       ("BENCHMARK_PASS", "BENCHMARK_CONDITIONAL")]
    held_clean_semantics = [r for r in held
                            if r.get("incorrect_critical_chains") == 0]

    report = {
        "artifact": "ENGINE_HEAD_REMEASUREMENT",
        "owner": "CODER2",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "reason": "post-E16-merge re-measurement: Coder 1's register-fix "
                  "engine head changed release behavior on the "
                  "independent benchmark inputs",
        "engine_head": engine_head,
        "frozen_baseline_reference": FROZEN_BASELINE,
        "baseline_discipline": "the frozen 3/15 baseline (B1/B7/B13) is "
                               "anchored at engine head fbd113b and is "
                               "NEVER overwritten; this AFTER row is a "
                               "new measurement at the new head",
        "status_distribution_at_new_head": status_counts,
        "rows": [{k: v for k, v in r.items() if k != "run_dir"}
                 for r in rows],
        "findings": {
            "auto_released_at_new_head":
                status_counts.get("RELEASED", 0),
            "held_for_human_review":
                status_counts.get("HELD_FOR_HUMAN_REVIEW", 0),
            "engine_self_rejected":
                status_counts.get("PIPELINE_FAILED", 0),
            "held_dossiers_passing_frozen_depth":
                len(held_pass_depth),
            "held_dossiers_clean_semantics":
                len(held_clean_semantics),
            "interpretation_rule": "if held dossiers pass the frozen "
                                   "depth floors AND are semantically "
                                   "clean, Coder 1's fixes improved real "
                                   "content and only human review gates "
                                   "release; if not, the holds re-brand "
                                   "the same shallow output",
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    print(json.dumps({
        "engine_head": engine_head[:12],
        "status_distribution": status_counts,
        "held_pass_depth": len(held_pass_depth),
        "held_clean_semantics": len(held_clean_semantics),
        "out": str(OUT_PATH),
    }, indent=1))


if __name__ == "__main__":
    main()

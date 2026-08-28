"""Coder 2 Phase 2, B2 — BLIND SET benchmark runner.

Runs the BLIND input set through Coder 1's REAL automatic pipeline and
publishes an AGGREGATE-ONLY measurement.

Disclosure contract:
  * blind input CONTENT never enters the repository (loaded from outside
    custody; only sha256 hashes are committed in BLIND_SET_MANIFEST.json);
  * blind run DIRS are gitignored (they contain the input content in
    problem.json / candidate_envelope.json);
  * the published aggregate contains NO domains, devices, mechanisms,
    quoted sentences, package folder names, or per-run artifact paths —
    only hash-keyed verdict rows and dimension counts.

Cross-set contamination is also measured: blind packages are checked
against every committed input's signature (does the engine reproduce
committed-input content into blind outputs?) and vice versa.

Usage:
    python3 -m discovery_fabric.benchmark.blind_runner \
        [--out artifacts/benchmark/blind] [--publish] [--cross-set]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine.run import EngineRun  # noqa: E402
from discovery_fabric.engine.release import (  # noqa: E402
    build_discovery_release, write_discovery_release)

from . import audit_runner  # noqa: E402
from . import corpus_runner as cr  # noqa: E402
from . import data_split as ds  # noqa: E402
from . import tri_measurement as tm  # noqa: E402

CTX = {"run_id": "coder2:blind", "problem_id": "blind"}
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmark" / "blind"
PUBLISH_PATH = REPO_ROOT / "artifacts" / "benchmark" / "baseline" / \
    "BLIND_BASELINE_MEASUREMENT.json"


def run_blind(out_root: Path = DEFAULT_OUT) -> Dict[str, Any]:
    """Generate the blind runs through the real pipeline (gitignored)."""
    specs = ds.load_blind_set()
    ver = ds.verify_blind_inputs(specs)
    if ver["verdict"] != "PASS":
        raise RuntimeError(f"blind set verification failed: {ver['problems']}")
    runs_root = out_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    run_dirs: List[Path] = []
    for idx, spec in enumerate(specs, start=1):
        env = cr.build_benchmark_envelope(spec, idx, prefix="coder2-blind")
        run_dir = runs_root / f"BLIND_{idx:02d}"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_id = f"coder2-blind:{idx:02d}"
        run = EngineRun(env.problem, str(run_dir), run_id=run_id,
                        package_number=f"9{idx:02d}")
        run.env = env
        run.rehearsal = True
        run._post_rank_pipeline({"run_id": run_id})
        (run_dir / "problem.json").write_text(
            json.dumps(env.problem, indent=1, ensure_ascii=False),
            encoding="utf-8")
        (run_dir / "candidate_envelope.json").write_text(
            json.dumps(env.to_dict(), indent=1, ensure_ascii=False,
                       default=str), encoding="utf-8")
        release = build_discovery_release(
            run_dir, run_id=run_id, problem_id=env.problem_id, env=env,
            spec=run._spec, eng=run._eng, package_report=run.package_report,
            failure_reason=run.package_failure)
        write_discovery_release(run_dir, release)
        run_dirs.append(run_dir)
        print(f"[blind {idx:02d}/5] release={(release or {}).get('status', '?')}")
    return {"run_dirs": [str(rd) for rd in run_dirs], "specs": specs}


def audit_blind(out_root: Path = DEFAULT_OUT, contract=None,
                profile=None) -> Dict[str, Any]:
    """Audit the blind runs; results stay in the gitignored dir."""
    runs_root = out_root / "runs"
    run_dirs = sorted(p for p in runs_root.iterdir() if p.is_dir())
    return audit_runner.audit_batch(
        run_dirs, contract=contract, profile=profile, expected_count=5,
        out_dir=out_root / "audit")


def cross_set_contamination(blind_run_dirs: List[Path],
                            committed_run_root: Path) -> Dict[str, Any]:
    """Do blind packages carry committed-input content (or vice versa)?"""
    from . import contamination as ct_mod
    packages = []
    for rd in blind_run_dirs:
        packages.append(_package_record(Path(rd), "BLIND"))
    committed_root = Path(committed_run_root)
    if committed_root.is_dir():
        for rd in sorted(committed_root.iterdir()):
            if rd.is_dir():
                packages.append(_package_record(rd, "COMMITTED"))
    report = ct_mod.audit_contamination(packages) if len(packages) > 1 \
        else {"violation_count": 0, "violations": []}
    blind_violations = [v for v in report.get("violations", [])
                        if "BLIND" in str(v.get("detail", ""))]
    return {
        "artifact": "BLIND_CROSS_SET_CONTAMINATION",
        "packages_checked": len(packages),
        "total_violations": report.get("violation_count"),
        "violations_involving_blind": len(blind_violations),
        "detail withheld": "violation details stay in the gitignored blind "
                           "audit; only counts are published",
    }


def _package_record(run_dir: Path, tag: str) -> Dict[str, Any]:
    rel = audit_runner._j(run_dir / "DISCOVERY_RELEASE.json") or {}
    package_dir = None
    if rel.get("package_folder"):
        p = Path(rel["package_folder"])
        if p.exists():
            package_dir = p
    if package_dir is None:
        dl = run_dir / "DOWNLOAD"
        if dl.is_dir():
            subs = [d for d in dl.iterdir() if d.is_dir()]
            package_dir = subs[0] if subs else None
    return {
        "run_dir": str(run_dir),
        "package_dir": str(package_dir) if package_dir else None,
        "package_id": f"{tag}_{run_dir.name}",
        "invention_id": None, "candidate_id": None,
        "evidence_ids": audit_runner._run_evidence_ids(run_dir),
        "input_signature": audit_runner._input_signature(run_dir),
    }


# ---------------------------------------------------------------------------
# Aggregate-only publication (committed; content-free)
# ---------------------------------------------------------------------------
def publish_aggregate(specs: List[Dict[str, Any]], batch: Dict[str, Any],
                      cross_set: Dict[str, Any], contract=None,
                      out_path: Path = PUBLISH_PATH) -> Dict[str, Any]:
    """Build the content-free blind measurement for the committed repo."""
    blind_hashes = [ds.blind_input_hash(s) for s in specs]
    per_run = []
    audits = {Path(a["run_dir"]).name: a for a in batch.get("runs") or []}
    genericness = batch.get("semantic_genericness_audit") or {}
    mismatch_pkgs = {str(m.get("package_id"))
                     for m in genericness.get("semantic_mismatches") or []}
    for i, h in enumerate(blind_hashes, start=1):
        name = f"BLIND_{i:02d}"
        rel = audit_runner._j(
            Path(batch.get("runs_root", ".")) / name / "DISCOVERY_RELEASE.json"
        ) if batch.get("runs_root") else None
        # prefer per-audit data when released
        a = audits.get(name) or {}
        row = {
            "blind_id": f"BLIND_{h[:12]}",
            "input_sha256": h,
        }
        if a:
            sem = a.get("semantic_causal_audit") or {}
            row.update({
                "release_status": "RELEASED",
                "verdict": a.get("verdict"),
                "failing_dimensions": a.get("failing_dimensions"),
                "conditional_dimensions": a.get("conditional_dimensions"),
                "semantic_incorrect_critical_chains":
                    sem.get("incorrect_critical_count"),
                "semantic_genericness_mismatch": (
                    name in mismatch_pkgs or
                    str(a.get("package_id")) in mismatch_pkgs),
            })
        else:
            # engine-rejected: pull status without content
            rd = _find_blind_run_dir(name)
            rj = audit_runner._j(rd / "DISCOVERY_RELEASE.json") if rd else {}
            sel = audit_runner._j(rd / "SURVIVOR_SELECTION.json") if rd else {}
            row.update({
                "release_status": rj.get("status"),
                "verdict": "ENGINE_REJECTED",
                "engine_rejection_stage": (
                    sel.get("killed") and "ATTACK_KILL") or
                    "E15_H_SELECTION",
                "failing_dimensions": None,
                "conditional_dimensions": None,
                "semantic_incorrect_critical_chains": None,
                "semantic_genericness_mismatch": None,
            })
        if rel and not a and rel.get("status") == "RELEASED":
            row["release_status"] = "RELEASED"
        per_run.append(row)

    dim_fails: Dict[str, int] = {}
    for a in batch.get("runs") or []:
        for d in a.get("failing_dimensions") or []:
            dim_fails[d] = dim_fails.get(d, 0) + 1

    aggregate = {
        "artifact": "CODER2_BLIND_BASELINE_MEASUREMENT",
        "owner": "CODER2",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "disclosure": "AGGREGATE-ONLY — no domains, devices, mechanisms, "
                      "quoted text, or per-run artifact paths. Content "
                      "custody stays outside the repository.",
        "blind_input_count": len(specs),
        "blind_input_hashes": blind_hashes,
        "engine_release_yield": {
            "runs_input": len(specs),
            "released": batch.get("runs_released_and_audited"),
            "engine_rejected": batch.get("engine_rejected_count"),
        },
        "verdict_counts": batch.get("verdict_counts"),
        "failing_dimension_counts": dim_fails,
        "semantic_genericness": {
            "semantic_mismatch_count":
                genericness.get("semantic_mismatch_count"),
            "mismatch_class_counts":
                genericness.get("mismatch_class_counts"),
        },
        "cross_set_contamination": {
            "violations_involving_blind":
                cross_set.get("violations_involving_blind"),
            "total_violations": cross_set.get("total_violations"),
        },
        "per_run": per_run,
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(aggregate, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return aggregate


def _find_blind_run_dir(name: str) -> Path:
    p = DEFAULT_OUT / "runs" / name
    return p if p.exists() else Path("artifacts/benchmark/blind/runs") / name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--contract", default="artifacts/benchmark/"
                                         "ENGINEERING_DEPTH_CONTRACT.json")
    ap.add_argument("--profile", default="artifacts/benchmark/"
                                         "BENCHMARK_DOSSIER_PROFILE.json")
    ap.add_argument("--publish", action="store_true",
                    help="write the aggregate-only measurement to the "
                         "committed baseline dir")
    ap.add_argument("--cross-set", action="store_true",
                    help="measure blind-vs-committed contamination")
    args = ap.parse_args()

    out_root = Path(args.out)
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))

    info = run_blind(out_root)
    batch = audit_blind(out_root, contract, profile)
    cross = {"violations_involving_blind": None, "total_violations": None}
    if args.cross_set:
        cross = cross_set_contamination(
            [Path(p) for p in info["run_dirs"]],
            REPO_ROOT / "artifacts/benchmark/generated/runs")

    print()
    print("=" * 70)
    print("CODER2 BLIND SET MEASUREMENT (aggregate only)")
    print("=" * 70)
    print(f"runs input:         {batch['runs_input']}")
    print(f"released+audited:   {batch['runs_released_and_audited']}")
    print(f"engine-rejected:    {batch['engine_rejected_count']}")
    print(f"batch verdict:      {batch['batch_verdict']}")
    if args.cross_set:
        print(f"cross-set contamination violations involving blind: "
              f"{cross.get('violations_involving_blind')}")
    if args.publish:
        agg = publish_aggregate(info["specs"], batch, cross, contract)
        print(f"published (content-free): {PUBLISH_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

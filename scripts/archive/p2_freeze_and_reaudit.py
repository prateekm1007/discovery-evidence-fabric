"""Coder 2 Phase 2 orchestration: freeze baseline (B1) + reaudit (B6).

Runs against the CURRENT engine state. The baseline is written ONCE and
never overwritten. The reaudit produces the BEFORE table (after == before
for the same engine state — validates the tool; the real AFTER run
happens once Coder 1 delivers repairs).

Usage:
    python3 scripts/p2_freeze_and_reaudit.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.benchmark import baseline as bl  # noqa: E402
from discovery_fabric.benchmark import blind_runner as br  # noqa: E402
from discovery_fabric.benchmark import data_split as ds  # noqa: E402
from discovery_fabric.benchmark import reaudit as ra  # noqa: E402
from discovery_fabric.benchmark import tri_measurement as tm  # noqa: E402

BASELINE_DIR = REPO / "artifacts" / "benchmark" / "baseline"
CONTRACT = REPO / "artifacts" / "benchmark" / "ENGINEERING_DEPTH_CONTRACT.json"
PROFILE = REPO / "artifacts" / "benchmark" / "BENCHMARK_DOSSIER_PROFILE.json"
COMMITTED_AUDIT = REPO / "artifacts" / "benchmark" / "generated" / \
    "AUTOMATED_DOSSIER_BENCHMARK.json"
BLIND_AUDIT = REPO / "artifacts" / "benchmark" / "blind" / "audit" / \
    "AUTOMATED_DOSSIER_BENCHMARK.json"


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
        text=True).stdout.strip()


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    batch = json.loads(COMMITTED_AUDIT.read_text(encoding="utf-8"))
    blind_batch = json.loads(BLIND_AUDIT.read_text(encoding="utf-8"))

    # ---- split manifest + blind manifest (hashes only) -------------------
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    split_manifest = ds.build_split_manifest()
    (BASELINE_DIR / "CODER2_BENCHMARK_SPLIT_MANIFEST.json").write_text(
        json.dumps(split_manifest, indent=1, ensure_ascii=False),
        encoding="utf-8")
    blind_specs = ds.load_blind_set()
    blind_manifest = ds.build_blind_manifest(blind_specs)
    (BASELINE_DIR / "BLIND_SET_MANIFEST.json").write_text(
        json.dumps(blind_manifest, indent=1, ensure_ascii=False),
        encoding="utf-8")
    print("split manifest + blind manifest written (hashes only)")

    # ---- tri-measurement over the committed set ---------------------------
    run_dirs = [REPO / f"artifacts/benchmark/generated/runs/BENCH_{i:02d}"
                for i in range(1, 16)]
    tri = tm.measure_yield_depth_correctness(
        run_dirs, contract=contract, profile=profile, batch_audit=batch,
        split_manifest=split_manifest)
    (BASELINE_DIR / "YIELD_DEPTH_CORRECTNESS_SEPARATION.json").write_text(
        json.dumps(tri, indent=1, ensure_ascii=False), encoding="utf-8")
    print("tri-measurement written:")
    print("  yield:", tri["engine_release_yield"]["released"], "/",
          tri["engine_release_yield"]["runs_input"])
    print("  attribution:", tri["engine_release_yield"]["attribution_counts"])
    print("  correctness fails:",
          tri["dossier_correctness"]["correctness_fail_count"], "/",
          tri["dossier_correctness"]["released_packages"])

    # ---- blind aggregate publication (content-free) ------------------------
    cross = br.cross_set_contamination(
        [REPO / f"artifacts/benchmark/blind/runs/BLIND_{i:02d}"
         for i in range(1, 6)],
        REPO / "artifacts/benchmark/generated/runs")
    agg = br.publish_aggregate(blind_specs, blind_batch, cross, contract)
    print("blind aggregate published (content-free):",
          f"released {agg['engine_release_yield']['released']}/"
          f"{agg['engine_release_yield']['runs_input']}")

    # ---- seven-deficiency measurement --------------------------------------
    measurement = ra.build_deficiency_measurement(
        run_dirs, batch, blind_measurement=agg, contract=contract,
        split_manifest=split_manifest, engine_head=git_head())
    measurement["threshold_integrity"] = {
        "depth_contract_sha256": bl.sha256_file(CONTRACT),
        "dossier_profile_sha256": bl.sha256_file(PROFILE),
    }
    measurement["split_manifest_sha256"] = bl.sha256_obj(split_manifest)
    measurement["baseline_summary"] = {
        "CURRENT_BASELINE": "3/15 RELEASED, 12/15 QUALITY_REJECTED "
                            "(committed set, CEO Phase 2 B1)",
        "blind_set": (
            f"{agg['engine_release_yield']['released']}/"
            f"{agg['engine_release_yield']['runs_input']} RELEASED"),
        "released_dossier_verdicts": batch.get("verdict_counts"),
        "engine_head": git_head(),
    }

    # ---- freeze (once) ------------------------------------------------------
    freeze = bl.freeze_baseline(measurement)
    print("baseline freeze:", freeze["action"],
          freeze.get("content_sha256", "")[:12])

    # ---- reaudit (BEFORE table; after == before for same engine) ----------
    integrity = ra.verify_threshold_integrity(
        measurement["threshold_integrity"])
    print("threshold integrity:", integrity["verdict"])
    result = ra.run_reaudit(measurement, out_dir=BASELINE_DIR)
    print("reaudit comparison_allowed:", result["comparison_allowed"])
    print()
    print(result["markdown"])

    # sanity: blind content must not appear in any committed artifact
    _verify_no_blind_leak(blind_specs)
    return 0


def _verify_no_blind_leak(specs) -> None:
    """Guard: no blind mechanism 3-gram may appear in committed artifacts.

    Single words are too weak (common engineering vocabulary like
    'closure' or 'pressure' legitimately appears everywhere); a leak of
    blind CONTENT means distinctive consecutive phrasing.
    """
    committed = []
    for p in (REPO / "artifacts" / "benchmark" / "baseline").rglob("*.json"):
        committed.append(p.read_text(encoding="utf-8", errors="replace"))
    blob = " ".join(committed).lower()
    for s in specs:
        words = [w for w in re.findall(r"[a-z]+", s["mechanism"].lower())
                 if len(w) > 3]
        grams = [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
        leaked = [g for g in grams if g in blob]
        if leaked:
            raise SystemExit(
                f"BLIND CONTENT LEAK into committed artifacts: {leaked[:3]} "
                f"from '{s['mechanism'][:60]}'")
    print("blind-content leak check: CLEAN (no blind mechanism 3-gram in "
          "committed artifacts)")


if __name__ == "__main__":
    raise SystemExit(main())

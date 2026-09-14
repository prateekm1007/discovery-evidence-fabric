"""Coder 2 Phase 3, B10 — THE UNSEEN-PROBLEM TEST.

A genuine unseen-problem challenge for Coder 1's engine:

  * problem set OUTSIDE the existing 15 technologies, outside the
    committed benchmark fixtures (BENCH_01..15), outside the blind set,
    and never used to tune the evaluator;
  * unseen problem CONTENT never enters the repository — custody outside
    git (same discipline as the blind set); the repo carries sha256
    hashes only (UNSEEN_PROBLEM_MANIFEST.json);
  * the evaluator assesses outputs WITHOUT knowing any expected answer —
    the instruments are the same frozen property-based measurements used
    for the committed/blind sets (corpus depth contract + 13-dimension
    evaluator + B3/B4 semantic gates); no unseen-specific thresholds
    exist, so there is nothing to tune against;
  * the four required pipeline stages are exercised and reported:
    live evidence retrieval (REAL mode, EuropePMC), candidate generation,
    engineering generation, dossier generation (REAL mode when
    credentials allow; labeled rehearsal mode otherwise, with the mode
    stamped on every artifact — Art. XXXVII);
  * failure attribution follows the CEO Phase 3 B12 taxonomy: a run
    blocked by missing LLM credentials is EVIDENCE_FAILURE, never a
    GENERATION_FAILURE.

Outputs (gitignored runs; committed manifest is hashes-only):
    artifacts/benchmark/unseen/            runs + audits (NEVER committed)
    artifacts/benchmark/baseline/
        UNSEEN_PROBLEM_MANIFEST.json       committed: hashes + aggregates
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine.run import EngineRun  # noqa: E402
from discovery_fabric.engine.release import (  # noqa: E402
    build_discovery_release, write_discovery_release)

from . import audit_runner  # noqa: E402
from . import corpus_runner as cr  # noqa: E402
from . import data_split as ds  # noqa: E402

UNSEEN_INPUT_COUNT = 4
UNSEEN_SET_PATH = Path("/home/z/my-project/coder2_blind/UNSEEN_PROBLEM_SET.json")
UNSEEN_CUSTODY_PATH = Path(
    "/home/z/my-project/download/coder2_blind/UNSEEN_PROBLEM_SET.json")
UNSEEN_OUT = REPO_ROOT / "artifacts" / "benchmark" / "unseen"
MANIFEST_PATH = REPO_ROOT / "artifacts/benchmark/baseline" / \
    "UNSEEN_PROBLEM_MANIFEST.json"

REQUIRED_STAGES = (
    "LIVE_EVIDENCE_RETRIEVAL",   # RETRIEVE stage, real mode
    "CANDIDATE_GENERATION",      # SYNTHESIZE stage
    "ENGINEERING_GENERATION",    # post-rank pipeline: eng spec
    "DOSSIER_GENERATION",        # buyer package
)


def load_unseen_set(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load unseen problem specs from outside-repo custody."""
    p = Path(path) if path else UNSEEN_SET_PATH
    if not p.exists() and UNSEEN_CUSTODY_PATH.exists():
        p = UNSEEN_CUSTODY_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    specs = data.get("inputs") if isinstance(data, dict) else data
    if not isinstance(specs, list):
        raise ValueError(f"unseen set file {p} has no inputs list")
    return specs


def unseen_input_hash(spec: Dict[str, Any]) -> str:
    return ds.blind_input_hash(spec)


# ---------------------------------------------------------------------------
# Distinctness verification (mechanical, recorded)
# ---------------------------------------------------------------------------
def verify_unseen_inputs(specs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The unseen set must be genuinely unseen:
      * full survivor-input shape, engine-supported families;
      * mechanism NOT near-duplicate of ANY committed benchmark input or
        blind input (significant-word Jaccard < 0.4 against every one);
      * no unseen mechanism 3-gram appears in any git-tracked file
        (content-leak screen, same instrument as the blind set).
    """
    problems: List[str] = []
    if len(specs) != UNSEEN_INPUT_COUNT:
        problems.append(f"expected {UNSEEN_INPUT_COUNT} unseen inputs, "
                        f"found {len(specs)}")
    hashes = []
    for i, s in enumerate(specs):
        missing = [k for k in ds.REQUIRED_SPEC_KEYS
                   if not str(s.get(k, "")).strip()]
        if missing:
            problems.append(f"unseen[{i}] missing keys: {missing}")
            continue
        if s["domain"] not in ds.KNOWN_DOMAINS:
            problems.append(f"unseen[{i}] unsupported domain "
                            f"{s['domain']!r}")
        if len(s["mechanism"].split()) < 8:
            problems.append(f"unseen[{i}] mechanism too thin")
        hashes.append(unseen_input_hash(s))
        for j, c in enumerate(cr.BENCHMARK_INPUTS, start=1):
            jac = ds._jaccard(s["mechanism"], c["mechanism"])
            if jac >= 0.4:
                problems.append(
                    f"unseen[{i}] mechanism too similar to committed "
                    f"BENCH_{j:02d} (Jaccard {jac:.2f})")
        try:
            for j, b in enumerate(ds.load_blind_set(), start=1):
                jac = ds._jaccard(s["mechanism"], b["mechanism"])
                if jac >= 0.4:
                    problems.append(
                        f"unseen[{i}] mechanism too similar to blind "
                        f"input {j} (Jaccard {jac:.2f})")
        except Exception:
            problems.append("blind set unavailable for distinctness check")
    if len(set(hashes)) != len(hashes):
        problems.append("duplicate unseen inputs")
    # 3-gram leak screen vs every tracked file
    tracked = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                             capture_output=True, text=True
                             ).stdout.splitlines()
    blob_parts = []
    for rel in tracked:
        p = REPO_ROOT / rel
        if p.suffix in (".py", ".json", ".md", ".txt", ".yml", ".yaml"):
            try:
                blob_parts.append(p.read_text(encoding="utf-8",
                                              errors="replace").lower())
            except Exception:
                pass
    blob = "\n".join(blob_parts)
    leaked_grams: List[str] = []
    for s in specs:
        words = [w for w in re.findall(r"[a-z]+",
                                       str(s.get("mechanism", "")).lower())
                 if len(w) > 3]
        for i in range(len(words) - 2):
            gram = " ".join(words[i:i + 3])
            if gram in blob:
                leaked_grams.append(gram)
    if leaked_grams:
        problems.append(f"unseen mechanism 3-grams leaked into tracked "
                        f"files: {leaked_grams[:3]}")
    return {
        "check": "UNSEEN_SET_VERIFICATION",
        "owner": "CODER2",
        "count": len(specs),
        "input_hashes": hashes,
        "distinct_from_committed_and_blind": not any(
            "too similar" in p for p in problems),
        "tracked_repo_3gram_leaks": len(leaked_grams),
        "problems": problems,
        "verdict": "PASS" if not problems else "FAIL",
    }


# ---------------------------------------------------------------------------
# REAL mode — live retrieval, honest fail-closed synthesis
# ---------------------------------------------------------------------------
def _stage_log(run_dir: Path) -> List[Dict[str, Any]]:
    try:
        env = json.loads(
            (run_dir / "candidate_envelope.json").read_text())
        return env.get("stage_log") or []
    except Exception:
        return []


def run_real_mode(spec: Dict[str, Any], idx: int,
                  out_root: Path) -> Dict[str, Any]:
    """One REAL-mode engine run: real EuropePMC retrieval, real custody
    freeze, synthesis honestly fail-closed when LLM credentials are
    absent. Stage outcomes are recorded, never faked."""
    run_dir = out_root / "real" / f"UNSEEN_{idx:02d}"
    if run_dir.exists():
        import shutil
        shutil.rmtree(run_dir)
    problem_id = f"coder2-unseen:{idx:02d}:{spec['domain']}"
    problem = {
        "problem_id": problem_id, "device": spec["device"],
        "failure_mode": spec["failure_mode"], "failure": spec["failure"],
        "constraint": spec["constraint"],
    }
    run_id = f"coder2-unseen-real:{idx:02d}"
    run = EngineRun(problem, str(run_dir), run_id=run_id)
    run.run()
    manifest = json.loads((run_dir / "run_manifest.json").read_text())
    rel = json.loads((run_dir / "DISCOVERY_RELEASE.json").read_text())
    stages = {e.get("stage"): e.get("status") for e in
              _stage_log(run_dir)}
    failed = manifest.get("failed_stages") or {}
    evidence_count = None
    try:
        env = json.loads(
            (run_dir / "candidate_envelope.json").read_text())
        evidence_count = len(env.get("evidence") or [])
    except Exception:
        pass

    synth_error = str(failed.get("SYNTHESIZE") or "")
    if "PROVIDER_UNAVAILABLE" in synth_error or "NO_KEY" in synth_error:
        attribution = ("EVIDENCE_FAILURE — live retrieval succeeded but "
                       "synthesis fail-closed on missing LLM credentials "
                       "(Art. IV/XXIX: infrastructure, not generation)")
    elif "zero evidence" in synth_error:
        attribution = ("EVIDENCE_FAILURE — live retrieval returned no "
                       "usable items (network/source unavailable)")
    elif not failed:
        attribution = "REAL_MODE_COMPLETED (credentials were available)"
    else:
        attribution = f"REAL_MODE stage failure: {synth_error[:120]}"

    return {
        "unseen_id": f"UNSEEN_{unseen_input_hash(spec)[:12]}",
        "mode": "REAL",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "stage_outcomes": {
            "LIVE_EVIDENCE_RETRIEVAL": {
                "engine_stage": "RETRIEVE",
                "status": stages.get("RETRIEVE"),
                "evidence_items_retrieved_live": evidence_count,
                "retrieval_is_real": stages.get("RETRIEVE") == "OK"},
            "CANDIDATE_GENERATION": {
                "engine_stage": "SYNTHESIZE",
                "status": stages.get("SYNTHESIZE"),
                "failure": synth_error[:300] or None},
            "ENGINEERING_GENERATION": {
                "engine_stage": "post-rank pipeline",
                "status": "SKIPPED_UPSTREAM_FAILURE"
                if failed else "EXECUTED"},
            "DOSSIER_GENERATION": {
                "engine_stage": "package build",
                "status": "SKIPPED_UPSTREAM_FAILURE"
                if failed else "EXECUTED"},
        },
        "release_status": rel.get("status"),
        "final_status": manifest.get("final_status"),
        "failure_attribution": attribution,
    }


# ---------------------------------------------------------------------------
# REHEARSAL mode — full four-stage pipeline, labeled
# ---------------------------------------------------------------------------
def run_rehearsal_mode(spec: Dict[str, Any], idx: int,
                       out_root: Path) -> Dict[str, Any]:
    """One labeled rehearsal run through the real pipeline code path
    (same driver pattern as the committed benchmark and blind sets)."""
    import shutil
    run_dir = out_root / "rehearsal" / f"UNSEEN_{idx:02d}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    env = cr.build_benchmark_envelope(spec, idx, prefix="coder2-unseen")
    run_id = f"coder2-unseen-rehearsal:{idx:02d}"
    run = EngineRun(env.problem, str(run_dir), run_id=run_id,
                    package_number=f"7{idx:02d}")
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
    return {
        "unseen_id": f"UNSEEN_{unseen_input_hash(spec)[:12]}",
        "mode": "REHEARSAL_LABELED",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "release_status": (release or {}).get("status"),
        "synthetic_rehearsal": True,
    }


# ---------------------------------------------------------------------------
# Full unseen-problem test
# ---------------------------------------------------------------------------
def run_unseen_test(out_root: Path = UNSEEN_OUT,
                    manifest_path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    specs = load_unseen_set()
    verification = verify_unseen_inputs(specs)
    if verification["verdict"] != "PASS":
        raise RuntimeError(f"unseen set verification failed: "
                           f"{verification['problems']}")
    contract = json.loads(
        (REPO_ROOT / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json")
        .read_text(encoding="utf-8"))
    profile = json.loads(
        (REPO_ROOT / "artifacts/benchmark/BENCHMARK_DOSSIER_PROFILE.json")
        .read_text(encoding="utf-8"))

    real_runs = [run_real_mode(s, i, out_root)
                 for i, s in enumerate(specs, start=1)]
    reh_runs = [run_rehearsal_mode(s, i, out_root)
                for i, s in enumerate(specs, start=1)]

    # evaluate rehearsal outputs with the SAME frozen instruments
    reh_dirs = [Path(r["run_dir"]) for r in reh_runs]
    batch = audit_runner.audit_batch(
        reh_dirs, contract=contract, profile=profile,
        expected_count=len(specs),
        out_dir=out_root / "audit")

    # UNSEEN_PROBLEM_RELEASE / DEPTH / CORRECTNESS (hash-keyed)
    audits_by_dir = {Path(a["run_dir"]).name: a
                     for a in batch.get("runs") or []}
    genericness = batch.get("semantic_genericness_audit") or {}
    mismatch_pkgs = {str(m.get("package_id"))
                     for m in genericness.get("semantic_mismatches") or []}
    per_problem = []
    depth_fail_counts: Dict[str, int] = {}
    correctness_fail = 0
    released_n = 0
    for r, s in zip(reh_runs, specs):
        h = unseen_input_hash(s)
        name = Path(r["run_dir"]).name
        a = audits_by_dir.get(name)
        row: Dict[str, Any] = {
            "unseen_id": f"UNSEEN_{h[:12]}",
            "input_sha256": h,
            "rehearsal_release_status": r["release_status"],
        }
        if a:
            released_n += 1
            dims = a.get("dimension_verdicts") or {}
            depth_fail = [d for d, v in dims.items()
                          if v == "FAIL" and d not in
                          ("SEMANTIC_CAUSAL_CORRECTNESS",
                           "SEMANTIC_GENERICNESS")]
            for d in depth_fail:
                depth_fail_counts[d] = depth_fail_counts.get(d, 0) + 1
            sem = a.get("semantic_causal_audit") or {}
            pid = str(a.get("package_id"))
            sem_fail = dims.get("SEMANTIC_CAUSAL_CORRECTNESS") == "FAIL" \
                or pid in mismatch_pkgs or name in mismatch_pkgs
            if sem_fail:
                correctness_fail += 1
            row.update({
                "verdict": a.get("verdict"),
                "unseen_problem_depth": {
                    "failing_depth_dimensions": depth_fail},
                "unseen_problem_correctness": {
                    "semantic": "FAIL" if sem_fail else "PASS",
                    "incorrect_critical_chains":
                        sem.get("incorrect_critical_count")},
            })
        else:
            row["verdict"] = "ENGINE_REJECTED"
        per_problem.append(row)

    real_released = sum(
        1 for r in real_runs if r["release_status"] == "RELEASED")
    evidence_blocked = sum(
        1 for r in real_runs
        if "EVIDENCE_FAILURE" in r["failure_attribution"])

    artifact = {
        "artifact": "UNSEEN_PROBLEM_TEST",
        "owner": "CODER2",
        "ceo_directive": "Phase 3 B10 — genuine unseen-problem validation",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "unseen_input_count": len(specs),
        "unseen_input_hashes": [unseen_input_hash(s) for s in specs],
        "custody": "content lives outside the repository (Coder 2 custody "
                   "+ CEO copy); this manifest carries hashes only",
        "distinctness_verification": {
            k: v for k, v in verification.items()},
        "evaluation_blindness": {
            "expected_answer_key": "NONE — no expected answers exist for "
                                   "unseen problems; assessment is "
                                   "property-based only",
            "instruments": "the same frozen instruments as the committed "
                           "and blind sets (corpus depth contract + "
                           "13-dimension evaluator + B3 semantic causal + "
                           "B4 genericness)",
            "unseen_specific_thresholds": "NONE — using unseen-specific "
                                          "thresholds would be evaluator "
                                          "tuning",
        },
        "required_stages": list(REQUIRED_STAGES),
        "UNSEEN_PROBLEM_RELEASE": {
            "real_mode": {
                "runs": len(real_runs), "released": real_released,
                "evidence_failure_blocked": evidence_blocked,
                "note": "real mode requires live retrieval AND LLM "
                        "credentials; missing credentials block synthesis "
                        "(EVIDENCE_FAILURE, B12 taxonomy — NOT a "
                        "generation failure)"},
            "rehearsal_mode_labeled": {
                "runs": len(reh_runs), "released": released_n,
                "note": "full four-stage pipeline through the real code "
                        "path with fixture evidence; every artifact "
                        "stamped SYNTHETIC_REHEARSAL (Art. XXXVII)"},
        },
        "UNSEEN_PROBLEM_DEPTH": {
            "released_rehearsal_dossiers": released_n,
            "failing_depth_dimension_counts": depth_fail_counts,
        },
        "UNSEEN_PROBLEM_CORRECTNESS": {
            "released_rehearsal_dossiers": released_n,
            "semantic_fail_count": correctness_fail,
        },
        "real_mode_runs": real_runs,
        "per_problem_hashkeyed": per_problem,
        "disclosure": "per-problem rows are hash-keyed; no unseen domains, "
                      "devices, mechanisms, or quoted text appear in this "
                      "manifest",
    }
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(artifact, indent=1,
                                        ensure_ascii=False),
                             encoding="utf-8")
    return artifact


def main() -> int:
    art = run_unseen_test()
    print("=" * 70)
    print("CODER2 UNSEEN-PROBLEM TEST (CEO Phase 3 B10)")
    print("=" * 70)
    print(f"unseen inputs: {art['unseen_input_count']} "
          f"(distinctness: "
          f"{art['distinctness_verification']['verdict']})")
    r = art["UNSEEN_PROBLEM_RELEASE"]["real_mode"]
    print(f"REAL mode:      {r['released']}/{r['runs']} released; "
          f"{r['evidence_failure_blocked']} blocked by EVIDENCE_FAILURE")
    rh = art["UNSEEN_PROBLEM_RELEASE"]["rehearsal_mode_labeled"]
    print(f"REHEARSAL mode: {rh['released']}/{rh['runs']} released")
    print(f"DEPTH failing dims: "
          f"{art['UNSEEN_PROBLEM_DEPTH']['failing_depth_dimension_counts']}")
    print(f"CORRECTNESS semantic fails: "
          f"{art['UNSEEN_PROBLEM_CORRECTNESS']['semantic_fail_count']}/"
          f"{art['UNSEEN_PROBLEM_CORRECTNESS']['released_rehearsal_dossiers']}")
    for row in art["real_mode_runs"]:
        print(f"  real {row['unseen_id']}: retrieval="
              f"{row['stage_outcomes']['LIVE_EVIDENCE_RETRIEVAL']['status']} "
              f"(live items="
              f"{row['stage_outcomes']['LIVE_EVIDENCE_RETRIEVAL']['evidence_items_retrieved_live']}) "
              f"synthesis="
              f"{row['stage_outcomes']['CANDIDATE_GENERATION']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""E21-D chunked benchmark driver: generate the 15 BENCH runs at the
E21 head, resume-safe (skips indices whose DISCOVERY_RELEASE.json
already exists in the persistent runs root). Usage:
    python scripts/e21_chunked_bench.py START END
Runs are persisted to /home/z/my-project/scripts/e21_runs/BENCH_xx.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import os
RUNS_ROOT = Path(os.environ.get("E21_RUNS_ROOT",
    "/home/z/my-project/scripts/e21_runs"))
RUNS_ROOT.mkdir(parents=True, exist_ok=True)

from discovery_fabric.benchmark.corpus_runner import (  # noqa: E402
    BENCHMARK_INPUTS, build_benchmark_envelope)
from discovery_fabric.engine.run import EngineRun  # noqa: E402
from discovery_fabric.engine.release import (  # noqa: E402
    build_discovery_release, write_discovery_release)


def main() -> int:
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    for idx in range(start, end + 1):
        spec = BENCHMARK_INPUTS[idx - 1]
        run_dir = RUNS_ROOT / f"BENCH_{idx:02d}"
        if (run_dir / "DISCOVERY_RELEASE.json").exists():
            rel = json.loads(
                (run_dir / "DISCOVERY_RELEASE.json").read_text())
            print(f"[{idx:02d}/15] SKIP (exists) "
                  f"status={rel.get('status')}")
            continue
        if run_dir.exists():
            import shutil
            shutil.rmtree(run_dir)
        env = build_benchmark_envelope(spec, idx)
        run_id = f"e21-benchmark:{idx:02d}"
        run = EngineRun(env.problem, str(run_dir), run_id=run_id,
                        package_number=f"8{idx:02d}")
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
        print(f"[{idx:02d}/15] {spec['domain']:22s} "
              f"release={release.get('status')} dir={run_dir.name}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

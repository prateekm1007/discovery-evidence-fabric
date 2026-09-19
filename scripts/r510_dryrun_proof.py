"""scripts/r510_dryrun_proof.py — three-problem dry-run proof runner.

Runs ONE controlled dry-run problem through the REAL EngineRun with
the fixture transport (no live credentials, zero live calls) and
writes the run dir + a per-run proof summary.

Usage:
  python scripts/r510_dryrun_proof.py dry-p1 A C:/proof/dryrun
  python scripts/r510_dryrun_proof.py dry-p1 B C:/proof/dryrun
  ...

Round A and round B use the EXACT same deterministic inputs (same
problem, same fixture bundle, same run_id shape); the repeatability
checker (tests/test_r510_dryrun.py + scripts/r510_dryrun_repeat.py)
compares them.

EPISTEMIC STATUS: controlled test material (see
tests/fixtures/dryrun/problems.py). No discovery claim. Every
artifact carries DRY_RUN_FIXTURE provenance, r506_eligible=False.
"""
from __future__ import annotations

import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from discovery_fabric.engine.adapters import STAGE_ORDER  # noqa: E402
from discovery_fabric.engine.dry_run import FixtureTransport  # noqa: E402
from discovery_fabric.engine.run import EngineRun  # noqa: E402
from tests.fixtures.dryrun.problems import BUNDLE_ID, PACKS  # noqa: E402

DISABLED = sorted(s for s in STAGE_ORDER
                  if s in {"RETRIEVE", "MULTI_SOURCE_DISCOVERY",
                           "COLLISION"})

CRED_VARS = ("NVIDIA_API_KEY", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY",
             "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
             "MISTRAL_API_KEY", "QWEN_API_KEY", "ENGINE_API_KEY")


def _cemetery_bytes():
    try:
        from orchestrator import mechanism_cemetery as _mc
        p = _mc.CEMETERY_PATH
        path = str(p)
        if not os.path.exists(path):
            return {"path": path, "sha256": "ABSENT", "bytes": 0}
        import hashlib as _h
        raw = open(path, "rb").read()
        return {"path": path, "sha256": _h.sha256(raw).hexdigest(),
                "bytes": len(raw)}
    except Exception as exc:
        return {"path": "UNKNOWN", "sha256": "UNREADABLE_%s" % type(
            exc).__name__, "bytes": -1}


def main() -> int:
    problem_id, round_tag, out_root = sys.argv[1:4]
    pack = PACKS[problem_id]
    creds_present = [v for v in CRED_VARS if os.environ.get(v)]
    run_id = "engrun_%s_%s" % (problem_id.replace("-", "_"), round_tag)
    out_dir = os.path.join(out_root, "%s_%s" % (problem_id, round_tag),
                           run_id)
    # Fresh-dir discipline (R401 disk-authority): the engine treats
    # records on disk as the authority (per-candidate envelopes are
    # REUSED when present). Re-running into a used dir mixes two runs
    # and breaks repeatability measurement — fail closed instead.
    if os.path.exists(out_dir):
        print("REFUSED: out_dir exists (fresh-dir discipline): %s"
              % out_dir)
        return 2
    os.makedirs(out_dir, exist_ok=True)
    cem_before = _cemetery_bytes()
    fx = FixtureTransport([dict(s) for s in pack["specs"]],
                          bundle_id=BUNDLE_ID)
    t0 = time.monotonic()
    run = EngineRun(
        problem=dict(pack["problem"]), out_dir=out_dir, run_id=run_id,
        disabled_stages=list(DISABLED), dry_run=True,
        fixture_transport=fx,
        fixture_evidence=[dict(e) for e in pack["evidence"]]).run()
    wall_s = time.monotonic() - t0
    cem_after = _cemetery_bytes()
    try:
        from orchestrator import mechanism_cemetery as _mc2
        cem_path_restored = str(_mc2.CEMETERY_PATH) == cem_before["path"]
    except Exception:
        cem_path_restored = False
    tel = fx.telemetry()
    port = json.load(open(os.path.join(out_dir, "CANDIDATE_PORTFOLIO.json"),
                          encoding="utf-8"))
    fun = json.load(open(os.path.join(out_dir, "DRY_RUN_FUNNEL.json"),
                         encoding="utf-8"))
    try:
        from discovery_fabric.engine.dry_run import (
            _engine_commit as _commit_of)
        commit = _commit_of()
    except Exception:
        commit = "UNKNOWN"
    summary = {
        "code_commit": commit,
        "problem_id": problem_id,
        "round": round_tag,
        "run_id": run_id,
        "out_dir": out_dir,
        "wall_s": round(wall_s, 1),
        "final_status": run.get("final_status"),
        "creds_present_in_env": creds_present,
        "live_calls": tel.get("live_calls"),
        "paid_calls": tel.get("paid_calls"),
        "served": tel.get("n_calls_served"),
        "refused_purposes": tel.get("refused_purposes"),
        "retries": tel.get("retries"),
        "generated": port["candidate_count_generated"],
        "distinct": port["candidate_count_distinct"],
        "ranked": port["candidate_count_ranked"],
        "grid_state": port["grid_state"],
        "r506_eligible": port["r506_eligible"],
        "funnel_counts": {k: fun[k] for k in (
            "submitted", "premise", "evidence", "mechanisms",
            "distinct", "ranked")},
        "blocking_stage": fun["blocking_stage"],
        "production_cemetery_before": cem_before,
        "production_cemetery_after": cem_after,
        "production_cemetery_unchanged": (
            cem_before["sha256"] == cem_after["sha256"]),
        "cemetery_path_restored": cem_path_restored,
        "final_status_funnel": fun.get("final_status"),
        "tail_durations_s": fun.get("tail_durations_s"),
        "stage_durations_s": fun.get("stage_durations_s"),
        "deterministic_input_identity":
            port["deterministic_input_identity"],
        "bundle_identity": port["bundle_identity"],
    }
    with open(os.path.join(out_root, "PROOF_%s_%s.json" % (
            problem_id, round_tag)), "w",
               encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

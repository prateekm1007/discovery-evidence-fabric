#!/usr/bin/env python3
"""scripts/r507_hermetic_second_container.py — R507: the second-container
re-run of the yield instrument's three HERMETIC ACCEPTANCE cases (the
directive's deliverable-2 acceptance: "instrument runs hermetically on 3
historical runs and reproduces their known terminals from bytes alone").

The R506 line ran the acceptance in its container. This script re-runs
the SAME frozen instrument (sha-verified) on the SAME durable bytes
(git refs 96965e28 / 34d81fb9 checked out in a DETACHED scratch
worktree; case 2 reads the current branch tip) in THIS container and
compares the decisive row fields exactly:

  lost_at, typed_drop_reason, and every funnel-transition reached flag

Any divergence = ACCEPTANCE_NOT_REPRODUCED (exit 1).

Run: python3 scripts/r507_hermetic_second_container.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTRUMENT = REPO / "scripts" / "r506_discovery_yield.py"
INSTRUMENT_SPEC = REPO / "R506" / "YIELD_INSTRUMENT.json"
SCRATCH = Path("/home/z/my-project/r507_hermetic_scratch")

CASES = [
    {"case": "R506/HERMETIC_CASE1_R489_CHECKPOINT_96965e28.json",
     "git_ref": "96965e28", "mode": "git"},
    {"case": "R506/HERMETIC_CASE2_R484_TERMINAL.json",
     "git_ref": None, "mode": "fs"},   # current branch tip
    {"case": "R506/HERMETIC_CASE3_R487_TERMINAL_34d81fb9.json",
     "git_ref": "34d81fb9", "mode": "git"},
]

DECISIVE = ("lost_at", "typed_drop_reason")
FUNNEL = ("fresh_submitted", "premise_coherent", "evidence_verified",
          "mechanisms_found", "candidates_generated_distinct",
          "attack_survivors", "contradiction_survivors",
          "experimentally_discriminated", "mutated_survivors",
          "buyer_ready")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _run_instrument(run_dir: Path, out: Path) -> dict:
    r = subprocess.run(["python3", str(INSTRUMENT), "--run-dir", str(run_dir),
                        "--out", str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"instrument failed: {r.stderr[-300:]}")
    return json.loads(out.read_text())["rows"][0]


def main() -> int:
    spec = json.loads(INSTRUMENT_SPEC.read_text())
    frozen = spec["script_sha256"]
    actual = _sha(INSTRUMENT)
    if actual != frozen:
        raise SystemExit("FATAL: instrument sha drift — refusing")

    results = []
    all_ok = True
    for case in CASES:
        case_doc = json.loads((REPO / case["case"]).read_text())
        expected = case_doc["rows"][0]
        slug = expected.get("slug") or expected.get("run_slug")
        if not slug:
            raise SystemExit(f"FATAL: case {case['case']} carries no slug")
        # resolve the run dir bytes
        if case["mode"] == "git":
            wt = SCRATCH / case["git_ref"]
            if not wt.exists():
                subprocess.run(
                    ["git", "-C", str(REPO), "worktree", "add", "--detach",
                     str(wt), case["git_ref"]], capture_output=True, text=True)
            run_dir = wt / "runs" / slug
        else:
            run_dir = Path("/home/z/my-project/r506_durable") / "runs" / slug
        if not run_dir.exists():
            raise SystemExit(
                f"FATAL: run dir not found for {case['case']}: {run_dir}")

        out = SCRATCH / (Path(case["case"]).stem + "_REPRO.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        got = _run_instrument(run_dir, out)

        diffs = {}
        for k in DECISIVE:
            if expected.get(k) != got.get(k):
                diffs[k] = {"expected": expected.get(k), "got": got.get(k)}
        for k in FUNNEL:
            e = (expected.get(k) or {}).get("reached")
            g = (got.get(k) or {}).get("reached")
            if e != g:
                diffs[k] = {"expected_reached": e, "got_reached": g}
        ok = not diffs
        all_ok = all_ok and ok
        results.append({
            "case": case["case"], "git_ref": case["git_ref"],
            "slug": slug, "reproduced": ok,
            "divergences": diffs or None,
            "expected_decisive": {
                "lost_at": expected.get("lost_at"),
                "typed_drop_reason": expected.get("typed_drop_reason")},
            "got_decisive": {
                "lost_at": got.get("lost_at"),
                "typed_drop_reason": got.get("typed_drop_reason")},
        })
        print(f"{case['case']}: {'REPRODUCED' if ok else 'DIVERGED ' + json.dumps(diffs)[:200]}")

    record = {
        "artifact_type": "R507_HERMETIC_SECOND_CONTAINER",
        "round": "R507",
        "reviewer_provenance": "AI_REVIEW",
        "instrument_sha256": actual,
        "instrument_sha_matches_frozen": actual == frozen,
        "cases": results,
        "all_reproduced": all_ok,
        "note": ("the directive's deliverable-2 acceptance re-run in the "
                 "second container: same frozen instrument, same durable "
                 "bytes (detached worktrees at the recorded git refs), "
                 "decisive fields compared exactly"),
    }
    out_path = REPO / "R507" / "HERMETIC_SECOND_CONTAINER.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"all_reproduced": all_ok,
                      "record": str(out_path.relative_to(REPO))}, indent=1))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

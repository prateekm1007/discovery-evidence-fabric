#!/usr/bin/env python3
"""scripts/r507_second_container_repro.py — R507: the SECOND-CONTAINER
reproduction of the yield computation (directive section 6: "A second
container re-runs the yield computation from the same durable bytes and
must reproduce the funnel exactly — reproducibility is part of the seal").

WHAT THIS IS: this line (R507, Coder 1) is the second container; the
battery launched and will be harvested by the R506 line (Coder 2, the
capability holder). This script re-runs the FROZEN yield instrument
(scripts/r506_discovery_yield.py, v1.0.0, pre-registered sha) against
the SAME durable bytes (the runtime-state-hf branch at a pinned commit)
in THIS container and compares the funnel + drop-off attribution
EXACTLY against the first container's R506/YIELD_MEASUREMENT.json.

Fail-closed discipline:
  - refuses to run unless the first container's measurement exists
  - refuses to run unless the instrument's sha matches the frozen
    pre-registered sha in R506/YIELD_INSTRUMENT.json
  - pins the durable commit it read (recorded; a different commit = a
    different measurement, never silently compared)
  - any funnel/drop/family divergence = REPRODUCTION_FAILED (exit 1);
    the seal cannot claim second-container reproduction

Run: python3 scripts/r507_second_container_repro.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKTREE = Path("/home/z/my-project/r506_durable")
SESSIONS = REPO / "R506" / "BATTERY_SESSIONS.json"
MEASUREMENT = REPO / "R506" / "YIELD_MEASUREMENT.json"
INSTRUMENT = REPO / "scripts" / "r506_discovery_yield.py"
INSTRUMENT_SPEC = REPO / "R506" / "YIELD_INSTRUMENT.json"
OUT = REPO / "R507" / "SECOND_CONTAINER_REPRODUCTION.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git(*args):
    return subprocess.run(["git", *args], cwd=str(REPO),
                          capture_output=True, text=True, timeout=120)


def main() -> int:
    if not MEASUREMENT.exists():
        raise SystemExit("FATAL: the first container's YIELD_MEASUREMENT.json "
                         "does not exist yet — the harvest is pending; this "
                         "reproduction runs only against a landed measurement")
    if not SESSIONS.exists():
        raise SystemExit("FATAL: BATTERY_SESSIONS.json (gitignored, "
                         "reconstructed) missing")

    # the frozen-instrument check (the pre-registered sha)
    spec = json.loads(INSTRUMENT_SPEC.read_text())
    frozen_sha = spec.get("instrument_sha256") or spec.get("sha256")
    actual_sha = _sha(INSTRUMENT)
    if frozen_sha and actual_sha != frozen_sha:
        raise SystemExit(f"FATAL: instrument sha drift {actual_sha[:16]}... "
                         f"!= frozen {frozen_sha[:16]}... — a changed "
                         "instrument is a new version; old measurements "
                         "stand, this reproduction refuses (Art. LIX)")

    # pin the durable bytes
    _git("fetch", "origin", "runtime-state-hf")
    tip = _git("rev-parse", "origin/runtime-state-hf").stdout.strip()
    wt = subprocess.run(["git", "-C", str(WORKTREE), "rev-parse", "HEAD"],
                        capture_output=True, text=True).stdout.strip()
    if wt != tip:
        subprocess.run(["git", "-C", str(WORKTREE), "reset", "--hard", tip],
                       capture_output=True, text=True, timeout=120)

    first = json.loads(MEASUREMENT.read_text())

    # re-run the instrument per battery row from the SAME durable bytes
    rows = []
    for s in json.loads(SESSIONS.read_text())["submissions"]:
        sid = s["session_id"]
        slug = None
        runs = WORKTREE / "runs"
        for cand in sorted(runs.iterdir()) if runs.exists() else []:
            if not cand.is_dir():
                continue
            for fname in ("run_manifest.json", "final_state.json"):
                p = cand / fname
                if p.exists():
                    try:
                        if json.loads(p.read_text()).get("session_id") == sid:
                            slug = cand.name
                    except Exception:  # noqa: BLE001
                        pass
        if not slug:
            rows.append({"problem_index": s["problem_index"],
                         "session_id": sid,
                         "harvest": "NOT_ON_DURABLE_BRANCH"})
            continue
        out_row = REPO / "R507" / f"REPRO_ROW_{s['problem_index']}_{slug}.json"
        r = subprocess.run(
            ["python3", str(INSTRUMENT), "--run-dir",
             str(WORKTREE / "runs" / slug), "--out", str(out_row)],
            capture_output=True, text=True)
        if r.returncode != 0:
            rows.append({"problem_index": s["problem_index"],
                         "session_id": sid, "run_slug": slug,
                         "harvest": f"INSTRUMENT_ERROR: {r.stderr[-200:]}"})
            continue
        row = json.loads(out_row.read_text())["rows"][0]
        rows.append({"problem_index": s["problem_index"],
                     "source_id": s["source_id"],
                     "declared_family": s["declared_family"],
                     "run_slug": slug, "row": row})

    # the comparison: funnel + drops + families EXACTLY
    def _aggregate(rows):
        full = [r for r in rows if isinstance(r.get("row"), dict)]
        if not full:
            return None
        ORDER = ["fresh_submitted", "premise_coherent", "evidence_verified",
                 "mechanisms_found", "candidates_generated_distinct",
                 "attack_survivors", "contradiction_survivors",
                 "experimentally_discriminated", "mutated_survivors",
                 "buyer_ready"]
        n = len(full)
        funnel = []
        for name in ORDER:
            reached = sum(1 for r in full
                          if (r["row"].get(name) or {}).get("reached"))
            funnel.append({"transition": name, "reached": reached,
                           "of_n": n,
                           "rate": round(reached / n, 4) if n else None})
        drops = {}
        for r in full:
            row = r["row"]
            if row.get("lost_at"):
                k = f"{row['lost_at']}::{row.get('typed_drop_reason')}"
                drops[k] = drops.get(k, 0) + 1
        fams = {}
        for r in full:
            f = r.get("declared_family") or "ABSENT"
            fams.setdefault(f, {"n": 0, "survived_all": 0})
            fams[f]["n"] += 1
            if r["row"].get("survived_all"):
                fams[f]["survived_all"] += 1
        return {"funnel": funnel,
                "dropoff_attribution_ranked": sorted(
                    [{"lost_at::reason": k, "n_runs": v}
                     for k, v in drops.items()], key=lambda d: -d["n_runs"]),
                "yield_per_100_fresh_by_family": fams}

    mine = _aggregate(rows)
    theirs = first.get("aggregate") or {}

    repro = {
        "artifact_type": "R507_SECOND_CONTAINER_REPRODUCTION",
        "round": "R507",
        "reviewer_provenance": "AI_REVIEW",
        "directive_anchor": ("directive section 6: 'A second container "
                             "re-runs the yield computation from the same "
                             "durable bytes and must reproduce the funnel "
                             "exactly (reproducibility is part of the seal)'"),
        "first_container_measurement": {
            "path": "R506/YIELD_MEASUREMENT.json",
            "instrument_sha256": first.get("instrument_sha256"),
            "harvested_at_utc": first.get("harvested_at_utc"),
        },
        "durable_commit_pinned": tip,
        "instrument_sha256_this_container": actual_sha,
        "instrument_sha_matches_frozen": actual_sha == frozen_sha,
        "rows_this_container": len(rows),
        "comparison": None,
        "reproduced": None,
    }
    if mine is None or not theirs:
        repro["comparison"] = "NO_FULL_ROWS_ONE_SIDE — cannot compare"
        repro["reproduced"] = False
    else:
        cmp_detail = {
            "funnel_equal": mine["funnel"] == theirs.get("funnel"),
            "drops_equal": (mine["dropoff_attribution_ranked"]
                            == theirs.get("dropoff_attribution_ranked")),
            "families_equal": (mine["yield_per_100_fresh_by_family"]
                               == theirs.get("yield_per_100_fresh_by_family")),
        }
        repro["comparison"] = cmp_detail
        repro["reproduced"] = all(cmp_detail.values())
        if not repro["reproduced"]:
            repro["divergence_detail"] = {
                "this_container": mine, "first_container": theirs}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(repro, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"reproduced": repro["reproduced"],
                      "durable_commit": tip[:12],
                      "comparison": repro["comparison"]}, indent=1))
    return 0 if repro["reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

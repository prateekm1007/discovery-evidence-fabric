#!/usr/bin/env python3
"""scripts/r412_replay_collision_screen.py — P0-2 validation replay.

Runs the pre-registered early collision screen
(discovery_fabric/r412/collision_screen.py) over the FROZEN R411
shortlist (14 candidates, their evidence pools, and their retrieved
prior-art records) and compares the screen's decisions against the R412
death-cause waterfall ground truth:

  - the 6 prior_art deaths are the collision targets (a screen catch on
    one of these = the expensive downstream stages WOULD have been
    skipped);
  - the 8 non-collision deaths (physics/evidence/baseline/engineering)
    must NOT be screened (a flag there = a false screen: the candidate
    died for a DIFFERENT reason, and screening it early would have
    mislabeled the death).

Two replay modes, both reported:
  MODE A (production position): evidence-pool records the candidate
    itself cites only — what the screen sees at its actual pipeline
    position (BEFORE prior-art retrieval exists).
  MODE B (diagnostic ceiling): cited evidence records + the run's
    RELEVANT prior-art records — the decision rule's sensitivity when
    prior art is already in hand.

This is a DIAGNOSTIC replay on frozen data, not a blind benchmark
(Art. LIX declared); the screen's thresholds were pre-registered in the
module BEFORE this replay ran. The replay MEASURES the rule; it does
not tune it.

Output: R412/COLLISION_SCREEN/r412_screen_replay_r411.json
"""
import json
import sys
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.collision_screen import (  # noqa: E402
    SCREEN_VERSION, candidate_term_sets, coverage,
    screen_candidate)

RUN = REPO / "R411" / "DISCOVERY_RUN"
OUT_DIR = REPO / "R412" / "COLLISION_SCREEN"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"


def _load(path: Path):
    return json.loads(path.read_text())


def _pool_for(candidate: Dict) -> List[Dict]:
    """The candidate's domain evidence pool records."""
    domain = candidate.get("domain_id")
    p = RUN / "evidence" / f"{domain}.json"
    if not p.exists():
        return []
    pool = _load(p).get("pool") or []
    by_id = {str(r.get("record_id")): r for r in pool}
    cited = [str(r) for r in candidate.get("evidence_refs") or []]
    return [by_id[c] for c in cited if c in by_id]


def _prior_art_for(candidate: Dict) -> List[Dict]:
    p = RUN / "prior_art" / f"{candidate.get('candidate_id')}.json"
    if not p.exists():
        return []
    pa = _load(p)
    return [r for r in (pa.get("relevant_records") or [])
            if str(r.get("relevance")).upper() == "RELEVANT"]


def _death_causes() -> Dict:
    w = _load(WATERFALL)
    return {d["candidate_id"]: d for d in w["deaths"]}


def _best_coverage(candidate: Dict, records: List[Dict]):
    """Diagnostic: the best (specific, core) coverage over the given
    records — recorded for MISSES so the report carries WHY the rule
    did not fire (threshold-adjacent vs vocabulary-divergent)."""
    specific, core = candidate_term_sets(candidate)
    best = {"specific_coverage": 0.0, "core_coverage": 0.0,
            "record_id": None}
    for r in records:
        sc, _ = coverage(specific, r)
        cc, _ = coverage(core, r)
        if sc + cc > (best["specific_coverage"]
                      + best["core_coverage"]):
            best = {"specific_coverage": round(sc, 4),
                    "core_coverage": round(cc, 4),
                    "record_id": r.get("record_id") or r.get("id")}
    return best


def main() -> int:
    shortlist = _load(RUN / "shortlist.json")
    causes = _death_causes()

    per_candidate = []
    counts = {"A": {"collision_target_screened": 0,
                    "collision_target_missed": 0,
                    "non_collision_flagged": 0,
                    "non_collision_passed": 0},
              "B": {"collision_target_screened": 0,
                    "collision_target_missed": 0,
                    "non_collision_flagged": 0,
                    "non_collision_passed": 0}}
    for cand in shortlist:
        cid = cand["candidate_id"]
        cause = causes.get(cid) or {}
        primary = cause.get("death_cause") or "unknown"
        is_collision = primary == "prior_art"
        cited = _pool_for(cand)
        pa = _prior_art_for(cand)
        res_a = screen_candidate(cand, cited, [])
        res_b = screen_candidate(cand, cited, pa)
        best_diag = _best_coverage(cand, cited + pa)
        for mode, res in (("A", res_a), ("B", res_b)):
            screened = res["decision"] == "SCREEN_COLLISION"
            if is_collision:
                key = ("collision_target_screened" if screened
                       else "collision_target_missed")
            else:
                key = ("non_collision_flagged" if screened
                       else "non_collision_passed")
            counts[mode][key] += 1
        per_candidate.append({
            "candidate_id": cid,
            "waterfall_primary_cause": primary,
            "collision_death": is_collision,
            "mode_a_evidence_only": {
                "decision": res_a["decision"],
                "n_matched": len(res_a["matched_records"]),
                "matched": [
                    {k: m[k] for k in ("record_id", "source",
                                       "specific_coverage",
                                       "core_coverage")}
                    for m in res_a["matched_records"][:3]],
            },
            "mode_b_with_prior_art": {
                "decision": res_b["decision"],
                "n_matched": len(res_b["matched_records"]),
                "matched": [
                    {k: m[k] for k in ("record_id", "source",
                                       "specific_coverage",
                                       "core_coverage")}
                    for m in res_b["matched_records"][:3]],
            },
            "best_coverage_diagnostic": best_diag,
        })

    report = {
        "artifact_type": "R412_COLLISION_SCREEN_REPLAY",
        "screen_version": SCREEN_VERSION,
        "subject_run": "r411 (frozen DISCOVERY_RUN)",
        "reviewer_provenance": "AI_REVIEW",
        "replay_kind": (
            "diagnostic on frozen data, NOT a blind benchmark (Art. LIX "
            "declared); the screen thresholds were pre-registered in the "
            "module before this replay ran; this replay MEASURES the "
            "rule, it does not tune it"),
        "ground_truth": (
            "the R412 death-cause waterfall: 6 prior_art deaths are the "
            "collision targets; 8 non-collision deaths must not be "
            "screened (they died for other reasons)"),
        "mode_semantics": {
            "A": ("production position — cited evidence records only "
                  "(what the screen sees BEFORE prior-art retrieval)"),
            "B": ("diagnostic ceiling — cited evidence + RELEVANT "
                  "retrieved prior-art records (the decision rule's "
                  "sensitivity when prior art is in hand)"),
        },
        "counts": counts,
        "per_candidate": per_candidate,
        "honest_notes": [
            "a collision-target MISS in mode A is not a screen defect: "
            "the collision record may exist only in the prior-art "
            "retrieval, which has not happened yet at the screen's "
            "pipeline position",
            "a non-collision FLAG is a false screen: the candidate died "
            "for a different reason and the screen would have mislabeled "
            "its death — precision is the screen's design constraint "
            "(conservative contract)",
            "mode B is a ceiling diagnostic: it answers 'would the rule "
            "fire given the collision evidence', not 'what would the "
            "campaign have done'",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "r412_screen_replay_r411.json"
    out.write_text(json.dumps(report, indent=1))
    print(f"replay written: {out}")
    for mode in ("A", "B"):
        c = counts[mode]
        print(f"mode {mode}: targets screened "
              f"{c['collision_target_screened']}/6, non-collision flagged "
              f"{c['non_collision_flagged']}/8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
ranking.py — R371 Phase 10: machine-derived portfolio ranking.

CEO directive:
  "Do not use arbitrary composite scores. Rank by an explicit decision
   policy and disclose that policy."

Policy (lexicographic, evidence-derived, disclosed in the artifact):
  KEY 1  KILL_TESTABILITY — packages whose recorded kill condition and first
          verification acceptance carry a NUMERIC threshold are more
          decidable: a buyer can call PASS/FAIL without judgment.
          Derived mechanically: numeric-threshold detection on
          headlines.kill_if + verification[0].acceptance.
          QUANTITATIVE ranks above QUALITATIVE.
  KEY 2  EVIDENCE_DEPTH — count of distinct hashed external precedent
          sources in the canonical record (more independently hashed
          sources = better-triangulated problem statement).
  KEY 3  ENGINEERING_ARTIFACT_DEPTH — design_inputs + design_outputs +
          failure_modes + verification + build_plan counts (sum).
  KEY 4  TIME_TO_DECISIVE_EXPERIMENT — canonical WP-01 recorded effort
          (lower = the decisive question is answered sooner). NOT_ESTABLISHED
          ranks last.

Every key is computed from the canonical record; nothing is hand-assigned.
The ranking table exposes all CEO-required columns so a buyer can re-sort
by their own policy.
"""

import re

from .economics import _parse_effort

_NUMERIC_RE = re.compile(
    r"(\d+\.?\d*\s*(?:%|mmHg|µW|uW|W/kg|cm|mm|mL/min|N\b|days?|h\b|:1|kcat"
    r"|mmHg/month|cm H2O)"
    r"|[<>]=?\s*\d|\b>=\s*\d|\bdetection\s+threshold\b)",
)


def kill_testability(headlines: dict, pkg) -> str:
    """QUANTITATIVE if the recorded kill condition or the first verification
    acceptance carries a numeric threshold; else QUALITATIVE."""
    hay = " ".join(
        [
            headlines.get("kill_if", "") or "",
            (pkg.verification[0].get("acceptance", "") if pkg.verification else ""),
            (pkg.verification[0].get("requirement", "") if pkg.verification else ""),
        ]
    )
    return "QUANTITATIVE" if _NUMERIC_RE.search(hay) else "QUALITATIVE"


def _evidence_depth(pkg) -> int:
    seen = set()
    for ext in pkg.external_precedent:
        h = ext.get("source_hash") or ext.get("source") or ""
        if h:
            seen.add(h)
    return len(seen)


def _artifact_depth(pkg) -> int:
    return (
        len(pkg.design_inputs)
        + len(pkg.design_outputs)
        + len(pkg.failure_analysis)
        + len(pkg.verification)
        + len(pkg.build_plan)
    )


def _time_to_decisive(pkg):
    if not pkg.build_plan:
        return None
    parsed = _parse_effort(pkg.build_plan[0].get("estimated_effort", ""))
    return parsed[0] if parsed else None


def largest_uncertainty(roadmap: dict) -> dict:
    """Pick the highest-priority critical unknown for the index table.
    Prefers FUNDAMENTALLY_UNRESOLVED critical, then any critical, then
    the first listed. Deterministic."""
    crits = [u for u in roadmap["unknowns"] if u["is_critical"]]
    pool = crits or roadmap["unknowns"]
    for cls in ("FUNDAMENTALLY_UNRESOLVED", "BENCH_TEST_REQUIRED",
                "REGULATORY_REQUIRED"):
        for u in pool:
            if u["classification"] == cls:
                return {
                    "unknown_id": u["unknown_id"],
                    "statement": u["unknown_statement"],
                    "classification": u["classification"],
                }
    if pool:
        return {
            "unknown_id": pool[0]["unknown_id"],
            "statement": pool[0]["unknown_statement"],
            "classification": pool[0]["classification"],
        }
    return {"unknown_id": None, "statement": "NONE RECORDED", "classification": None}


def strongest_evidence(pkg) -> str:
    """Name the strongest evidence line from the canonical record."""
    ext = pkg.external_precedent
    if ext:
        e = ext[0]
        return (e.get("source_title") or e.get("source") or "captured source")[:90]
    return "NO EXTERNAL PRECEDENT RECORDED"


def build_ranking(packages, headlines_by_pkg, roadmaps_by_pkg) -> dict:
    """PORTFOLIO_RANKING.json content — explicit policy + machine-derived
    table."""
    rows = []
    for pkg in packages:
        h = headlines_by_pkg.get(pkg.pkg_id, {})
        rm = roadmaps_by_pkg[pkg.pkg_id]
        ttd = _time_to_decisive(pkg)
        rows.append(
            {
                "portfolio_number": pkg.num,
                "package_id": pkg.pkg_id,
                "technology": h.get("technology_name"),
                "problem": (h.get("problem") or "")[:220],
                "domain": pkg.domain,
                "maturity": "ENGINEERING_DEFINITION",
                "transfer_posture": "SPONSORED_VALIDATION",
                "kill_testability": kill_testability(h, pkg),
                "evidence_depth": _evidence_depth(pkg),
                "engineering_artifact_depth": _artifact_depth(pkg),
                "time_to_decisive_experiment_weeks": ttd,
                "strongest_evidence": strongest_evidence(pkg),
                "largest_uncertainty": largest_uncertainty(rm),
                "decisive_experiment": (
                    pkg.build_plan[0].get("test_article")
                    if pkg.build_plan
                    else "NOT_RECORDED"
                ),
                "cost_range": "NOT_ESTABLISHED (no quotation basis in the engineering record)",
                "timeline_first_decisive_wp": (
                    pkg.build_plan[0].get("estimated_effort")
                    if pkg.build_plan
                    else "NOT_RECORDED"
                ),
                "buyer_type": "See BUYER_PROFILE in COMMERCIAL_EVIDENCE.json (capability-based)",
                "kill_condition": h.get("kill_if"),
                "loop_verification_state": pkg.loop_state,
            }
        )

    def sort_key(row):
        ttd = row["time_to_decisive_experiment_weeks"]
        return (
            0 if row["kill_testability"] == "QUANTITATIVE" else 1,
            -row["evidence_depth"],
            -row["engineering_artifact_depth"],
            ttd if ttd is not None else 10**6,
        )

    ranked = sorted(rows, key=sort_key)
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank

    return {
        "artifact": "PORTFOLIO_RANKING",
        "policy": {
            "name": "R371 lexicographic buyer-decision policy",
            "description": (
                "Ranking is evidence-derived, not marketing preference, and "
                "uses no composite scores. Keys are applied in order; ties "
                "fall through to the next key."
            ),
            "keys": [
                {
                    "key": 1,
                    "name": "KILL_TESTABILITY",
                    "rule": "QUANTITATIVE (recorded numeric threshold in kill "
                            "condition or first verification acceptance) ranks "
                            "above QUALITATIVE",
                    "basis": "A decidable kill condition is the primary "
                             "buyer-facing virtue of an engineering-definition "
                             "package: it defines the experiment that can end "
                             "the project.",
                },
                {
                    "key": 2,
                    "name": "EVIDENCE_DEPTH",
                    "rule": "Higher count of distinct hashed external "
                            "precedent sources ranks above lower",
                    "basis": "Independent hashed sources triangulate the "
                             "problem statement (Constitution Art. XXI.7).",
                },
                {
                    "key": 3,
                    "name": "ENGINEERING_ARTIFACT_DEPTH",
                    "rule": "Higher sum of design inputs + outputs + failure "
                            "modes + verification + build-plan steps ranks "
                            "above lower",
                    "basis": "Artifact depth measures how much engineering "
                             "definition a buyer receives.",
                },
                {
                    "key": 4,
                    "name": "TIME_TO_DECISIVE_EXPERIMENT",
                    "rule": "Lower canonical WP-01 effort ranks above higher; "
                            "unparseable efforts rank last",
                    "basis": "Sooner decisive question = cheaper option on "
                             "the buyer's decision.",
                },
            ],
            "no_composite_scores": True,
        },
        "rows": ranked,
    }

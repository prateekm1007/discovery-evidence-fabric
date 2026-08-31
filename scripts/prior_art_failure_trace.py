"""PRIOR-ART DIFFERENTIATION + RESOLUTION failure trace — CEO directive
2026-08-31 (cycle R376).

> "Take the weakest Q2/Q3 cases from the 53-run survey and trace exactly
>  why prior-art specificity is poor."

For every measured run, this diagnostic extracts the FULL prior-art chain
from the run's own recorded artifacts:

    intervention wording -> patent queries issued -> hits returned ->
    relevance adjudications -> nearest_prior_art -> prior_art_status

and classifies each weak case into the CEO's six separated causes, WITH
EVIDENCE from the recorded artifacts (never inference):

  W  BAD_INVENTION_WORDING      intervention text is generic action
                                prose, few technical content terms
  F  BAD_SEARCH_FORMULATION     the issued query lost the candidate's
                                technical core (terms dropped/garbled)
  B  INSUFFICIENT_SEARCH_BREADTH too few queries/sources issued to
                                cover the mechanism (<=2 queries, 1
                                source, <=10 hits)
  R  POOR_PATENT_RESULT_RELEVANCE returned hits adjudicated IRRELEVANT
                                (off-domain) — search found junk
  E  ENTITY_CLAIM_MISMATCH      nearest prior art shares < 2 content
                                terms with the INTERVENTION (Q2 entry
                                miss) though adjudicated RELEVANT vs
                                the query — entity mismatch survives
  M  NO_FAMILY_RESOLUTION       multiple distinct prior-art families
                                present in hits but no family structure
                                recorded / no resolution state exists

Diagnostic only (Art. XXVI). Failure classes are measured on recorded
artifacts; where a cause cannot be decided from the record it is
reported as UNDECIDABLE rather than guessed (Art. XXV).

Reproduction: PYTHONPATH=. python3 scripts/prior_art_failure_trace.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.benchmark import candidate_quality as cq  # noqa: E402
from discovery_fabric.source_registry.query_relevance import terms  # noqa: E402

FILLER_WORDS = {
    "implement", "implementation", "system", "using", "use", "within",
    "into", "from", "with", "that", "this", "which", "based", "provide",
    "improve", "improved", "new", "novel", "method", "device", "design",
    "develop", "development", "approach", "technique", "process",
}


def _content_terms(text: str) -> set:
    return set(terms(text or ""))


def classify_wording(intervention: str) -> Dict[str, Any]:
    """W: is the intervention text generic action prose?"""
    t = _content_terms(intervention)
    technical = t - FILLER_WORDS
    return {
        "cause": "W_BAD_INVENTION_WORDING",
        "n_content_terms": len(t),
        "n_technical_terms": len(technical),
        "technical_terms": sorted(technical)[:12],
        "verdict": "HIT" if len(technical) < 3 else "miss",
        "evidence": intervention[:160],
    }


def classify_formulation(intervention: str, queries: List[str]) -> Dict[str, Any]:
    """F: did the issued queries carry the intervention's technical core?"""
    iv_tech = _content_terms(intervention) - FILLER_WORDS
    if not queries:
        return {"cause": "F_BAD_SEARCH_FORMULATION", "verdict": "HIT",
                "evidence": "no patent queries recorded"}
    q_terms = set()
    for q in queries:
        q_terms |= _content_terms(q)
    lost = sorted(iv_tech - q_terms)
    kept = sorted(iv_tech & q_terms)
    # formulation is bad if it lost most of the technical core
    verdict = "HIT" if (iv_tech and len(lost) >= max(2, len(iv_tech) * 0.6)) else "miss"
    return {
        "cause": "F_BAD_SEARCH_FORMULATION", "verdict": verdict,
        "queries": queries,
        "technical_terms_kept": kept[:12],
        "technical_terms_lost": lost[:12],
        "evidence": f"{len(kept)} kept / {len(lost)} lost of "
                    f"{len(iv_tech)} technical terms",
    }


def classify_breadth(queries: List[str], hit_count: int,
                     n_sources: int, n_families: int) -> Dict[str, Any]:
    """B: was the search too narrow to cover the mechanism?"""
    verdict = "HIT" if (len(queries) <= 2 and hit_count <= 10
                        and n_sources <= 1) else "miss"
    return {
        "cause": "B_INSUFFICIENT_SEARCH_BREADTH", "verdict": verdict,
        "n_queries": len(queries), "n_hits": hit_count,
        "n_sources": n_sources,
        "evidence": f"{len(queries)} queries / {n_sources} source / "
                    f"{hit_count} hits (directives require mechanism + "
                    f"distinguishing-feature coverage, direct + adjacent)",
    }


def classify_result_relevance(adjudications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """R: did the search return off-domain junk?"""
    if not adjudications:
        return {"cause": "R_POOR_PATENT_RESULT_RELEVANCE",
                "verdict": "UNDECIDABLE",
                "evidence": "no adjudications recorded (older run artifacts)"}
    relevant = [a for a in adjudications if a.get("relevance") == "RELEVANT"]
    n = len(adjudications)
    verdict = "HIT" if n and len(relevant) / n < 0.5 else "miss"
    return {
        "cause": "R_POOR_PATENT_RESULT_RELEVANCE", "verdict": verdict,
        "n_relevant": len(relevant), "n_total": n,
        "evidence": f"{len(relevant)}/{n} returned hits adjudicated RELEVANT",
    }


def classify_entity_claim(intervention: str,
                          nearest: List[Dict[str, Any]]) -> Dict[str, Any]:
    """E: do nearest-prior-art entries share domain with the candidate?"""
    if not nearest:
        return {"cause": "E_ENTITY_CLAIM_MISMATCH", "verdict": "UNDECIDABLE",
                "evidence": "no nearest_prior_art entries recorded"}
    iv_terms = _content_terms(intervention)
    per_entry = []
    misses = 0
    for p in nearest:
        title = str(p.get("title") or "")
        ov = iv_terms & _content_terms(title)
        per_entry.append({"title": title[:80], "overlap": sorted(ov)})
        if len(ov) < 2:
            misses += 1
    verdict = "HIT" if misses else "miss"
    return {
        "cause": "E_ENTITY_CLAIM_MISMATCH", "verdict": verdict,
        "entries_with_lt2_overlap": misses, "n_entries": len(nearest),
        "per_entry": per_entry,
        "evidence": f"{misses}/{len(nearest)} nearest entries share < 2 "
                    f"content terms with the intervention (Q2 miss)",
    }


def classify_family_resolution(patent_block: Dict[str, Any],
                               status: str) -> Dict[str, Any]:
    """M: multiple prior-art families present but unresolved?"""
    hits = patent_block.get("hits") or []
    nearest = patent_block.get("nearest_prior_art") or \
        (patent_block.get("") or {})
    # family evidence: distinct titles with >=2 shared terms between THEM
    titles = [str(h.get("title") or "") for h in hits]
    fam_clusters: List[List[int]] = []
    for i, t1 in enumerate(titles):
        placed = False
        for cl in fam_clusters:
            if len(_content_terms(t1) & _content_terms(titles[cl[0]])) >= 2:
                cl.append(i)
                placed = True
                break
        if not placed:
            fam_clusters.append([i])
    n_families = len([c for c in fam_clusters if len(c) >= 1])
    families_recorded = patent_block.get("families") is not None
    resolved = str(status).startswith("RESOLVED")
    verdict = "HIT" if (n_families >= 2 and not families_recorded) or \
        (not resolved and n_families >= 1) else "miss"
    return {
        "cause": "M_NO_FAMILY_RESOLUTION", "verdict": verdict,
        "n_hit_families": n_families,
        "families_recorded": families_recorded,
        "status_recorded": status,
        "resolution_state_exists": str(status).startswith("RESOLVED"),
        "evidence": f"{n_families} title-clusters among hits; no family "
                    f"structure recorded; status={status!r} carries no "
                    f"RESOLVED state",
    }


def trace_run(run_dir: Path) -> Dict[str, Any]:
    spec = json.loads((run_dir / "INVENTION_SPECIFICATION.json").read_text())
    df = (spec.get("distinguishing_features") or {}).get("value") or {}
    intervention = str(df.get("intervention") or "")
    pa_block = spec.get("prior_art") or {}
    pa_val = pa_block.get("value") or {}
    nh = (spec.get("novelty_hypothesis") or {}).get("value") or {}
    status = nh.get("prior_art_status") or pa_val.get("status")

    # collision envelope carries the full patent record incl. adjudications
    collision = None
    env_path = run_dir / "envelope_COLLISION.json"
    if env_path.exists():
        try:
            env = json.loads(env_path.read_text())
            collision = (env.get("collision_results") or {})
        except Exception:
            collision = None
    if collision is None:
        collision = (spec.get("prior_art") or {}).get("value", {})
        # spec prior_art.value.nearest only — fall back to spec fields
        collision = {"patent": {"queries": pa_val.get("queries", []),
                                "hits": [], "nearest_prior_art":
                                    (pa_val.get("nearest") or [])},
                     "nearest_prior_art": pa_val.get("nearest") or []}

    patent = collision.get("patent") or {}
    queries = patent.get("queries") or []
    hits = patent.get("hits") or []
    adjudications = patent.get("relevance_adjudications") or []
    nearest = collision.get("nearest_prior_art") or \
        (pa_val.get("nearest") or [])
    # source count: google patents is 1 source unless errors say otherwise
    n_sources = 1 if (hits or queries) else 0

    m = cq.measure_run(run_dir)
    q2 = next((d for d in m.get("dimensions", [])
               if d["dimension"] == "Q2_PRIOR_ART_SPECIFICITY"), {})
    q3 = next((d for d in m.get("dimensions", [])
               if d["dimension"] == "Q3_PRIOR_ART_RESOLUTION"), {})

    causes = [
        classify_wording(intervention),
        classify_formulation(intervention, queries),
        classify_breadth(queries, len(hits), n_sources, 0),
        classify_result_relevance(adjudications),
        classify_entity_claim(intervention, nearest),
        classify_family_resolution(patent, str(status or "")),
    ]
    return {
        "run": run_dir.name,
        "q2_score": q2.get("score"),
        "q3_score": q3.get("score"),
        "q3_status": q3.get("recorded_status"),
        "intervention": intervention[:200],
        "patent_queries": queries,
        "n_hits": len(hits),
        "n_relevant_hits": patent.get("relevant_hit_count"),
        "nearest_titles": [str(p.get("title"))[:80] for p in nearest],
        "causes": causes,
    }


def main() -> int:
    runs_root = REPO / "ENGINE_RUNS"
    rows = []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        if not (run_dir / "INVENTION_SPECIFICATION.json").exists():
            continue
        rows.append(trace_run(run_dir))

    # weakest Q2/Q3 first
    def weak_key(r):
        q2 = r["q2_score"] if isinstance(r["q2_score"], (int, float)) else 1.0
        q3 = r["q3_score"] if isinstance(r["q3_score"], (int, float)) else 1.0
        return (q2 + q3, q2)

    rows.sort(key=weak_key)

    # aggregate cause counts over the weakest 20
    agg: Dict[str, Dict[str, int]] = {}
    for r in rows[:20]:
        for c in r["causes"]:
            a = agg.setdefault(c["cause"], {"HIT": 0, "miss": 0,
                                            "UNDECIDABLE": 0})
            a[c["verdict"]] = a.get(c["verdict"], 0) + 1

    out = {
        "artifact": "PRIOR_ART_FAILURE_TRACE",
        "directive": "CEO 2026-08-31 — trace weakest Q2/Q3 cases; separate "
                     "wording / formulation / breadth / relevance / "
                     "entity-claim / family-resolution causes",
        "n_runs_traced": len(rows),
        "cause_aggregate_weakest_20": agg,
        "all_runs_q3_status_vocabulary": sorted({
            str(r["q3_status"]) for r in rows if r["q3_status"]}),
        "per_run": rows,
    }
    dest = REPO / "TOSCANINI" / "PRIOR_ART_FAILURE_TRACE.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"traced {len(rows)} runs -> {dest}")
    print("\n=== CAUSE AGGREGATE (weakest 20 runs) ===")
    for cause, a in sorted(agg.items()):
        print(f"  {cause:38s} HIT={a.get('HIT', 0):3d}  "
              f"miss={a.get('miss', 0):3d}  UNDECIDABLE={a.get('UNDECIDABLE', 0)}")
    print("\n=== Q3 STATUS VOCABULARY (all runs) ===")
    for s in out["all_runs_q3_status_vocabulary"]:
        print(f"  {s}")
    print("\n=== 10 WEAKEST RUNS ===")
    for r in rows[:10]:
        print(f"  {r['run'][:60]:60s} Q2={r['q2_score']} Q3={r['q3_score']}")
        print(f"    intervention: {r['intervention'][:110]}")
        print(f"    queries: {r['patent_queries']}")
        print(f"    hits={r['n_hits']} relevant={r['n_relevant_hits']} "
              f"nearest={r['nearest_titles'][:2]}")
        hits_ = [c["cause"].split('_', 1)[0] for c in r["causes"]
                 if c["verdict"] == "HIT"]
        print(f"    cause HITs: {hits_}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

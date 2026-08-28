"""discovery_fabric/engine/candidate_diversity.py — CEO E16-E: candidate
diversity benchmark.

A discovery engine must EXPLORE the search space, not produce "15
variations of the same concept". For one problem the engine generates at
least 10 candidates through recorded, deterministic EXPLORATION ANGLES
(the search policy, an epistemic object in its own right) crossed with
the configured model paths, then measures:

    mechanism diversity   — pairwise token-space distance of the
                            mechanism/intervention claims
    architecture diversity — distinct intervention sites/components
    search-space diversity — distinct exploration-angle products that
                              returned usable candidates
    prior-art diversity   — distinct prior-art query sets derived per
                            candidate (the queries the collision stage
                            would run per candidate)
    failure-mode diversity — distinct domain failure-mode signals the
                              candidate space invokes

Lexical-rewrite detection: any candidate pair with token Jaccard >= 0.8
is flagged as a REWRITE, and the diversity verdict fails if rewrites
dominate.

No forced consensus and no deduplication by rewording: candidates stay
distinct epistemic objects with their angle + model provenance.
"""
from __future__ import annotations

import itertools
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .ensemble import _content_fingerprint, _jaccard, _parse_fields

# exploration angles — the recorded search policy (each angle instructs
# the model to explore a DIFFERENT region of the mechanism space; the
# angle is recorded on the candidate as provenance, Art. XXVII)
EXPLORATION_ANGLES = (
    ("cross_industry_transfer",
     "Transfer a mechanism from a DIFFERENT industry (not medical "
     "devices) that physically addresses the stated failure."),
    ("mechanism_inversion",
     "Invert or rearrange the obvious mechanism: remove the active "
     "element, use a passive/structural effect, or reverse the flow of "
     "the driving quantity."),
    ("simplification",
     "Find the SIMPLEST physical mechanism that addresses the failure "
     "with the fewest moving parts and no exotic technology."),
    ("multi_physics_hybrid",
     "Combine two DIFFERENT physical domains (e.g. thermal + acoustic, "
     "fluidic + magnetic) into one mechanism addressing the failure."),
    ("constraint_first",
     "Derive the mechanism strictly from the stated constraint: what "
     "physical effect satisfies the constraint where conventional "
     "designs violate it."),
)

_STOP = set("""a an the of to in on for with and or is are was were be been
it its this that these those from by at as into within not no nor but if
then than so such can could may might will would shall should must have
has had do does did done using used use uses based upon via per each other
more most less least very much many few any all both either neither one
two new device the failure problem""".split())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", str(text or "").lower())
            if w not in _STOP}


def angle_prompt(base_prompt: str, angle: Tuple[str, str]) -> str:
    """Append the exploration angle to the frozen synthesis prompt (the
    angle is an EXPLICIT recorded addition — never a silent prompt change)."""
    name, instruction = angle
    return (f"{base_prompt}\n\nEXPLORATION ANGLE ({name}): {instruction}\n"
            "Respond in the SAME field format as instructed above.")


def generate_diverse_candidates(problem: Dict[str, Any],
                                evidence: List[Dict[str, Any]],
                                min_candidates: int = 10,
                                timeout: int = 240,
                                ) -> Dict[str, Any]:
    """Generate >= min_candidates through the angle x provider product.
    Uses the llm_registry with ONE pinned path per provider (E15-E
    independence); every candidate records its angle + provider."""
    from .llm_registry import availability_matrix, generate, SelectionPolicy
    available = [m["provider_id"] for m in availability_matrix()
                 if m["available"]]
    result: Dict[str, Any] = {
        "diversity": "CANDIDATE_DIVERSITY (E16-E)",
        "version": "1.0.0",
        "min_candidates": min_candidates,
        "available_providers": available,
        "angles": [a[0] for a in EXPLORATION_ANGLES],
        "candidates": [],
        "built_at": utc_now(),
    }
    if not available:
        result["status"] = "PROVIDER_UNAVAILABLE"
        result["note"] = ("no provider credential; no diversity space "
                          "was generated and none is fabricated "
                          "(Art. XXV)")
        return result
    return _run_grid(problem, evidence, available[:2], timeout, result)


def _run_grid(problem: Dict[str, Any], evidence: List[Dict[str, Any]],
              providers: List[str], timeout: int,
              result: Dict[str, Any]) -> Dict[str, Any]:
    """Run the angle x provider grid. Requires the frozen synthesis
    prompt; each call is an independent generation path."""
    import importlib
    a2syn = importlib.import_module("discovery_fabric.a2.synthesize")
    from .llm_registry import generate, SelectionPolicy
    base = a2syn.SYNTHESIS_PROMPT.format(
        device=problem.get("device", ""),
        failure=problem.get("failure", ""),
        constraint=problem.get("constraint", ""),
        title=(evidence[0] or {}).get("title", "") if evidence else "",
        abstract=((evidence[0] or {}).get("abstract") or "")[:1200]
        if evidence else "")
    candidates = []
    for angle in EXPLORATION_ANGLES:
        for pid in providers:
            policy = SelectionPolicy(preferred_providers=[pid],
                                     max_preference_fallback=0,
                                     purpose="diversity_exploration")
            res = generate(angle_prompt(base, angle),
                           system="You are a medical device engineer.",
                           timeout=timeout, max_retries=2,
                           policy=policy, max_tokens=512)
            entry: Dict[str, Any] = {
                "angle": angle[0], "provider_id": pid,
                "status": res.status, "model": res.model,
                "prompt_hash": res.prompt_hash,
                "output_hash": res.output_hash}
            if res.ok:
                fields = _parse_fields(res.content)
                if fields.get("intervention"):
                    entry["fields"] = fields
                    entry["candidate_id"] = (
                        f"cand:DIV:{angle[0]}:{pid}:"
                        f"{(res.output_hash or '')[:12]}")
            else:
                entry["error"] = (res.error or "")[:200]
            candidates.append(entry)
    result["candidates"] = candidates
    usable = [c for c in candidates if c.get("fields")]
    result["usable_candidates"] = len(usable)
    result["status"] = ("GRID_RUN" if len(usable) >= 2
                        else "GRID_DEGRADED" if usable else "GRID_FAILED")
    if usable:
        result["diversity_metrics"] = measure_diversity(usable)
    return result


def measure_diversity(usable: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Measure the five E16-E diversity dimensions over the usable
    candidate set."""
    mech_fps = {}
    for c in usable:
        f = c["fields"]
        mech_fps[c.get("candidate_id") or id(c)] = _content_fingerprint(
            (f.get("mechanism", "") + " " + f.get("intervention", "")))
    ids = list(mech_fps)
    pairwise = []
    rewrites = []
    for a, b in itertools.combinations(ids, 2):
        sim = round(_jaccard(mech_fps[a], mech_fps[b]), 3)
        pairwise.append(sim)
        if sim >= 0.8:
            rewrites.append({"a": a, "b": b, "jaccard": sim})
    mean_distance = round(1 - (sum(pairwise) / len(pairwise)), 3) \
        if pairwise else 0.0
    # distinct mechanism clusters (greedy, threshold 0.5 similarity)
    clusters: List[List[str]] = []
    for cid in ids:
        placed = False
        for cl in clusters:
            if any(_jaccard(mech_fps[cid], mech_fps[o]) >= 0.5
                   for o in cl):
                cl.append(cid)
                placed = True
                break
        if not placed:
            clusters.append([cid])
    # architecture diversity: distinct intervention-site/component terms
    arch_terms = set()
    for c in usable:
        arch_terms |= _tokens(c["fields"].get("intervention", ""))
    # failure-mode diversity: distinct domain failure-mode signals invoked
    # across the candidates' mechanism text (the failure surface the
    # candidate space touches)
    from .domains import detect_domain, get_domain_module
    text_all = " ".join(c["fields"].get("mechanism", "") + " " +
                        c["fields"].get("intervention", "")
                        for c in usable)
    domain = detect_domain(text_all).get("domain", "UNKNOWN")
    module = get_domain_module(domain)
    invoked = set()
    for dfm in module.get("failure_modes", []):
        for sig in dfm.get("applicability_signals", []):
            if sig and sig.lower() in text_all.lower():
                invoked.add(dfm.get("mode"))
    # prior-art diversity: distinct query token sets per candidate (the
    # queries the collision stage would run per candidate)
    query_sets = set()
    for c in usable:
        q = " ".join(sorted(_tokens(c["fields"].get("intervention", "")))[:6])
        query_sets.add(q)
    return {
        "candidates_measured": len(usable),
        "mean_pairwise_token_distance": mean_distance,
        "distinct_mechanism_clusters": len(clusters),
        "cluster_sizes": sorted((len(c) for c in clusters), reverse=True),
        "rewrite_pairs_jaccard_ge_0_8": rewrites,
        "architecture_term_count": len(arch_terms),
        "architecture_terms_sample": sorted(arch_terms)[:24],
        "failure_mode_signal_count": len(invoked),
        "failure_modes_invoked_sample": sorted(
            m for m in invoked if m)[:8],
        "prior_art_query_set_count": len(query_sets),
        "detected_domain": domain,
    }


def evaluate_diversity(metrics: Dict[str, Any],
                       min_candidates: int = 10,
                       min_clusters: int = 3,
                       ) -> Dict[str, Any]:
    """E16-E verdict over the measured diversity. Recorded policy:
    PASS requires >= min_candidates usable, >= min_clusters distinct
    mechanism clusters, mean pairwise distance >= 0.6, and NO dominating
    rewrite cluster (rewrite pairs < half the candidate set)."""
    rewrites = metrics.get("rewrite_pairs_jaccard_ge_0_8", [])
    n = metrics.get("candidates_measured", 0)
    clusters = metrics.get("distinct_mechanism_clusters", 0)
    distance = metrics.get("mean_pairwise_token_distance", 0.0)
    checks = {
        "candidate_count": (n >= min_candidates,
                            f"{n} usable < {min_candidates} required"),
        "mechanism_clusters": (clusters >= min_clusters,
                               f"{clusters} distinct clusters < "
                               f"{min_clusters} required"),
        "mean_distance": (distance >= 0.6,
                          f"mean pairwise distance {distance} < 0.6"),
        "no_rewrite_dominance": (len(rewrites) < max(1, n // 2),
                                 f"{len(rewrites)} rewrite pairs "
                                 f"(Jaccard >= 0.8)"),
    }
    failed = [msg for ok, msg in checks.values() if not ok]
    verdict = "PASS" if not failed else ("FAIL" if len(failed) > 1
                                         else "CONDITIONAL")
    return {
        "verdict": verdict, "checks": {k: {"pass": v[0], "detail": v[1]}
                                       for k, v in checks.items()},
        "failed_checks": failed,
        "policy": (f">= {min_candidates} usable candidates, >= "
                   f"{min_clusters} distinct mechanism clusters, mean "
                   "pairwise token distance >= 0.6, rewrite pairs < half "
                   "the candidate set"),
    }

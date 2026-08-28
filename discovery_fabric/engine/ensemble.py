"""discovery_fabric/engine/ensemble.py — CEO E15-E: multi-model invention
disagreement.

A world-class discovery engine must not depend on ONE model behaving well:
"Model-specific blind spots become system-wide blind spots." When multiple
providers are configured, the engine runs INDEPENDENT generation paths:

    MODEL_A → invention candidate
    MODEL_B → invention candidate
          ↓
    INDEPENDENT CANDIDATES
          ↓
    COMMON CLAIMS       (supported by >= 2 independent paths)
    DISAGREEMENTS       (explicit epistemic objects — NEVER forced to
                         consensus; each carries both claims, the similarity
                         measure, an UNRESOLVED status, and the resolution
                         path: the decisive experiment + buyer diligence)
    UNIQUE MECHANISMS   (claims unique to one path — recorded, not discarded)
          ↓
    ADJUDICATOR         (deterministic, recorded selection basis; picks the
                         PRIMARY candidate but preserves the disagreement
                         objects in the artifact chain)

The ensemble result is an ENVELOPE-LEVEL epistemic object (provenance
class MODELLED / COMPUTED as marked) — it never promotes model output to
evidence (Art. XVIII) and it never fabricates disagreement when only one
provider exists: a single-provider environment records
SINGLE_PROVIDER_PATH honestly (Art. XXV — unknown stays unknown).
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .llm_registry import (LLMCallResult, SelectionPolicy,
                           availability_matrix, generate)

FIELDS = ("MECHANISM", "INTERVENTION", "EXPECTED_EFFECT",
          "FALSIFICATION_TEST", "MECHANISM_SOURCE_SPAN")

_STOP = set("""a an the of to in on for with and or is are was were be been
it its this that these those from by at as into within not no nor but if
then than so such can could may might will would shall should must have has
had do does did done using used use uses based upon via per each other more
most less least very much many few any all both either neither one two""".split())

_SIGNIFICANT = re.compile(r"[a-z]{4,}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _content_fingerprint(text: str) -> frozenset:
    """Significant-word set of a claim text (deterministic comparator)."""
    words = _SIGNIFICANT.findall(str(text or "").lower())
    return frozenset(w for w in words if w not in _STOP)


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _parse_fields(content: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    pat = re.compile(
        rf'^({"|".join(FIELDS)})\s*:\s*(.*)$', re.MULTILINE)
    for m in pat.finditer(content or ""):
        parsed[m.group(1).lower()] = m.group(2).strip()
    return parsed


def _call_provider(provider_id: str, prompt: str, system: str,
                   timeout: int) -> LLMCallResult:
    """One INDEPENDENT generation path pinned to one provider (no fallback:
    a path IS its provider — substitution would silently undo the
    independence E15-E exists to create)."""
    policy = SelectionPolicy(preferred_providers=[provider_id],
                             max_preference_fallback=0,
                             purpose="ensemble_invention")
    return generate(prompt, system=system, timeout=timeout,
                    max_retries=2, policy=policy, max_tokens=512)


def ensemble_synthesize(problem: Dict[str, Any],
                        evidence: List[Dict[str, Any]],
                        max_models: int = 2,
                        timeout: int = 240,
                        ) -> Dict[str, Any]:
    """E15-E: independent invention candidates from >= 2 configured
    providers + disagreement objects + recorded adjudication.
    Honest degradation: 1 provider -> SINGLE_PROVIDER_PATH; 0 ->
    PROVIDER_UNAVAILABLE. NEVER fabricated disagreement."""
    matrix = availability_matrix()
    available = [m["provider_id"] for m in matrix if m["available"]]
    # operator override may pin the ensemble to explicit paths
    override = [p.strip() for p in os.environ.get(
        "ENGINE_ENSEMBLE_PROVIDERS", "").split(",") if p.strip()]
    if override:
        available = [p for p in override if p in available] or available

    result: Dict[str, Any] = {
        "ensemble": "MULTI_MODEL_DISAGREEMENT (E15-E)",
        "version": "1.0.0",
        "requested_models": max_models,
        "available_providers": available,
        "members": [],
        "common_claims": [],
        "disagreements": [],
        "unique_mechanisms": [],
        "adjudication": {},
        "built_at": utc_now(),
    }
    if not available:
        result["status"] = "PROVIDER_UNAVAILABLE"
        result["note"] = ("no provider credential in the environment; "
                          "no ensemble ran and NO disagreement was "
                          "fabricated (Art. XXV)")
        return result

    if len(available) < 2:
        result["status"] = "SINGLE_PROVIDER_PATH"
        result["note"] = (
            f"only one provider configured ({available[0]}); an ensemble "
            "needs >= 2 independent paths — model disagreement cannot be "
            "probed and none is claimed (record honestly, Art. XXV)")
        return result

    # ---- independent generation paths -----------------------------------
    paths = available[:max_models]
    result["status"] = "ENSEMBLE_RUN"
    result["paths"] = paths
    return _run_paths(problem, evidence, paths, timeout, result)


def synthesis_prompt(problem: Dict[str, Any],
                     evidence: List[Dict[str, Any]]) -> str:
    """The frozen A2 synthesis prompt (same protocol, one path per model)."""
    import importlib
    a2syn = importlib.import_module("discovery_fabric.a2.synthesize")
    paper = evidence[0] if evidence else {}
    return a2syn.SYNTHESIS_PROMPT.format(
        device=problem.get("device", ""),
        failure=problem.get("failure", ""),
        constraint=problem.get("constraint", ""),
        title=paper.get("title", ""),
        abstract=(paper.get("abstract") or "")[:1200])


def _run_paths(problem: Dict[str, Any], evidence: List[Dict[str, Any]],
               paths: List[str], timeout: int,
               result: Dict[str, Any]) -> Dict[str, Any]:
    prompt = synthesis_prompt(problem, evidence)
    system = "You are a medical device engineer."
    for i, pid in enumerate(paths):
        res = _call_provider(pid, prompt, system, timeout)
        role = f"MODEL_{'ABCD'[i] if i < 4 else i + 1}"
        member: Dict[str, Any] = {
            "role": role, "provider_id": pid,
            "status": res.status,
            "model": res.model,
            "prompt_hash": res.prompt_hash,
            "output_hash": res.output_hash,
            "latency_ms": res.latency_ms,
        }
        if res.ok:
            fields = _parse_fields(res.content)
            member["fields"] = fields
            member["missing_fields"] = [f.lower() for f in FIELDS
                                        if f.lower() not in fields]
            member["candidate"] = {
                "candidate_id": f"cand:ENS:{pid}:"
                                f"{(res.output_hash or '')[:12]}",
                "mechanism": fields.get("mechanism", ""),
                "intervention": fields.get("intervention", ""),
                "expected_effect": fields.get("expected_effect", ""),
                "falsification_test": fields.get("falsification_test", ""),
                "mechanism_source_span": fields.get(
                    "mechanism_source_span", ""),
                "source_evidence": {
                    "source_id": (evidence[0] or {}).get("id", ""),
                    "source_hash": (evidence[0] or {}).get(
                        "content_hash", "")} if evidence else {},
            }
        else:
            member["error"] = (res.error or "")[:300]
        result["members"].append(member)

    ok_members = [m for m in result["members"] if m["status"] == "OK"
                  and m.get("candidate", {}).get("intervention")]
    if len(ok_members) < 2:
        result["status"] = ("ENSEMBLE_DEGRADED" if ok_members
                            else "ENSEMBLE_FAILED")
        result["note"] = (
            f"{len(ok_members)} independent path(s) returned a usable "
            "candidate; disagreement requires >= 2 — nothing fabricated")
        if ok_members:
            result["adjudication"] = _adjudicate(ok_members)
        return result

    # ---- claim-set comparison --------------------------------------------
    dims = ("mechanism", "intervention", "expected_effect",
            "falsification_test")
    fps = {m["role"]: {d: _content_fingerprint(
        m["candidate"].get(d, "")) for d in dims} for m in ok_members}
    roles = list(fps)
    a, b = roles[0], roles[1]

    common, disagreements, unique = [], [], []
    did = 0
    for d in dims:
        fa, fb = fps[a][d], fps[b][d]
        sim = round(_jaccard(fa, fb), 3)
        claim_a = ok_members[0]["candidate"].get(d, "")
        claim_b = ok_members[1]["candidate"].get(d, "")
        if not fa and not fb:
            continue
        if sim >= 0.30:
            common.append({
                "dimension": d, "similarity": sim,
                "supporting_roles": [a, b],
                "claim": claim_a or claim_b,
                "epistemic_class": "COMPUTED",
                "note": "independently produced by >= 2 paths",
            })
        elif sim <= 0.25:
            did += 1
            disagreements.append({
                "disagreement_id": f"DIS-{did:03d}",
                "dimension": d,
                "role_a": a, "claim_a": claim_a,
                "role_b": b, "claim_b": claim_b,
                "similarity": sim,
                "status": "UNRESOLVED (deliberate — no forced consensus)",
                "resolution_path": ("decisive experiment + buyer "
                                    "diligence; the disagreement travels "
                                    "into the dossier's uncertainty "
                                    "register (Art. XXV)"),
                "epistemic_class": "COMPUTED",
                "recorded_at": utc_now(),
            })
        else:
            # the gray band (0.25 < sim < 0.30): neither agreement nor a
            # sharp disagreement — recorded as a unique variant per role
            for role, claim in ((a, claim_a), (b, claim_b)):
                if claim:
                    unique.append({"dimension": d, "role": role,
                                   "claim": claim,
                                   "epistemic_class": "MODELLED"})
    result["common_claims"] = common
    result["disagreements"] = disagreements
    result["unique_mechanisms"] = unique
    result["comparison"] = {
        "method": "significant-word Jaccard over the four invention "
                  "claim dimensions (deterministic comparator)",
        "thresholds": {"agreement": 0.30, "disagreement": 0.25},
        "note": "the gray band between the thresholds is recorded as "
                "unique per-role variants, never forced into either bin",
    }
    result["adjudication"] = _adjudicate(ok_members)
    return result


def _adjudicate(ok_members: List[Dict[str, Any]]) -> Dict[str, Any]:
    """E15-F/E15-H adjudicator: pick the PRIMARY candidate WITHOUT forcing
    consensus. Deterministic, recorded basis: field completeness first,
    then falsifiability, then source-span presence. Disagreement objects
    are NOT resolved by the adjudicator — they stay epistemic objects."""
    def score(m: Dict[str, Any]) -> Tuple[int, int, int]:
        c = m.get("candidate") or {}
        complete = sum(1 for f in FIELDS if c.get(f.lower()))
        falsifiable = 1 if c.get("falsification_test") else 0
        span = 1 if c.get("mechanism_source_span") else 0
        return (complete, falsifiable, span)

    ranked = sorted(ok_members, key=score, reverse=True)
    primary = ranked[0]
    return {
        "adjudicator": "DETERMINISTIC (field completeness -> "
                       "falsifiability -> source span)",
        "primary_role": primary["role"],
        "primary_provider": primary["provider_id"],
        "primary_candidate_id": primary["candidate"]["candidate_id"],
        "ranking": [{"role": m["role"], "provider_id": m["provider_id"],
                     "score": score(m)} for m in ranked],
        "consensus_forced": False,
        "note": ("the primary candidate enters the pipeline; disagreement "
                 "objects remain UNRESOLVED and travel with the artifact "
                 "chain (E15-E: do not force consensus)"),
        "decided_at": utc_now(),
    }

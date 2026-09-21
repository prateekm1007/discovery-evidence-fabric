"""discovery_fabric/engine/mechanism_attribution.py — R516 Part A:
MECHANISM_SPACE runtime attribution for the LIVE lean path.

WHAT: monotonic wall-time spans + candidate-funnel counts + LLM-call
detail for ONE _lean_mechanism_space execution (adapters.py — the
production path; build_mechanism_space() is test-only, verified by
call-site inspection R516: no production callers).

WHAT NOT: not a gate, not a threshold, not a decision. The clock is
observational (Art. IX): it records durations and counts, it never
steers, skips, retries, or relabels anything. Scientific code paths
are untouched — marks sit BETWEEN existing statements.

WHERE THE RECORD LIVES: space["runtime_attribution"] (one additive
key on the mechanism-space envelope; persisted by the normal
envelope path, so production runs emit it with zero extra plumbing).

PROVIDER-vs-OVERHEAD SPLIT (the R511 blind spot): measured in-stage
as ONE llm_instantiation wall span plus the call meta (provider,
model, status, route hops, prompt/output hashes as join keys). The
provider-call vs routing-overhead SPLIT is derived OFFLINE by
joining the routing ledger on those keys (the R511 reconciliation
precedent) — it is NOT fabricated in-stage (Art. XXV: the split
stays labeled OFFLINE_VIA_ROUTING_LEDGER until a harvest computes
it from both byte sources).

VOCABULARY: every funnel count uses existing typed states
(NO_EVIDENCE, NO_APPLICABLE_EVIDENCE, OPERATOR_INSTANTIATION_FAILED,
NOT_A_CANDIDATE_*, distinctness verdicts, support states). The only
new strings are observational transport classes (output_empty,
output_fields_empty_count) labeled as attribution observations,
never epistemic states.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

ATTRIBUTION_VERSION = "mechanism_attribution/1.0.0 (R516)"

#: the 12 directive subphases, in execution order on the lean path.
#: Eleven are measured wall spans; provider_call_split_offline is an
#: explicit unmeasured marker (the split is offline-derived — see
#: module docstring; a None duration is not a zero, Art. XXV).
SUBPHASES = (
    "entry_setup",
    "verified_evidence_collection",
    "evidence_item_construction",
    "operator_selection",
    "llm_instantiation_wall",
    "provider_call_split_offline",
    "candidate_parsing",
    "semantic_validation",
    "cemetery_consultation",
    "distinctness_dedup",
    "mechanism_support_verification",
    # R516B-E (auditor directive section 2): the old name
    # "serialization_persistence" did not measure persistence — it
    # covers post-verification in-function assembly (transition
    # ledger, public candidates, metrics, return). Renamed to the
    # actual work; durations byte-identical, positional mapping
    # pinned by test.
    "post_support_assembly",
)

_OFFLINE_SPLIT_MARKER = {
    "subphase": "provider_call_split_offline",
    "duration_s": None,
    "derivation": ("OFFLINE_VIA_ROUTING_LEDGER — not measurable "
                   "in-stage; join routing-ledger per-hop latencies "
                   "on the llm.join_keys (Art. XXV: unmeasured stays "
                   "unmeasured, never zero)"),
}


class AttributionClock:
    """Monotonic span recorder. Exception-free by construction
    (perf_counter + list appends only) so instrumentation can never
    break the stage it observes (Art. IX/V)."""

    def __init__(self) -> None:
        self._t0 = time.perf_counter()
        self._last = self._t0
        self._spans: List[Dict[str, Any]] = []

    def mark(self, name: str,
             extra: Optional[Dict[str, Any]] = None) -> float:
        """Close the span since the previous mark (or start) and name
        it. Returns the span duration in seconds."""
        now = time.perf_counter()
        dur = now - self._last
        self._last = now
        span: Dict[str, Any] = {"subphase": name,
                                "duration_s": round(dur, 3)}
        if extra:
            span.update(extra)
        self._spans.append(span)
        return dur

    def total_s(self) -> float:
        return round(time.perf_counter() - self._t0, 3)

    def spans(self) -> List[Dict[str, Any]]:
        return [dict(s) for s in self._spans]


def llm_call_detail(n_calls: int,
                    meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The directive's LLM-path detail from the call meta. On the lean
    path n_calls is 0 (no LLM path taken) or 1 (one instantiation
    call, no corrective retry — R453-LEAN). All fields are observed
    from the meta dict; nothing is inferred."""
    detail: Dict[str, Any] = {
        "n_llm_calls": int(n_calls),
        "llm_retries": 0,
        "retry_basis": ("one call is one call on the lean path "
                        "(R453-LEAN; no corrective retry)"),
    }
    if meta is None:
        detail.update({
            "path_taken": False,
            "reason": "no LLM path taken on this execution",
        })
        return detail
    detail["path_taken"] = True
    detail["provider"] = meta.get("provider")
    detail["model"] = meta.get("model")
    detail["transport_status"] = meta.get("status")
    detail["transport_error"] = (meta.get("error") or "")[:200] \
        if meta.get("error") else None
    detail["failure_type"] = meta.get("failure_type")
    detail["routed_hops"] = [
        {"provider": h.get("provider"),
         "failure_type": h.get("failure_type"),
         "fallback_provider": h.get("fallback_provider")}
        for h in (meta.get("provider_route") or [])]
    detail["n_route_hops"] = len(detail["routed_hops"])
    detail["fallback_occurred"] = len(detail["routed_hops"]) > 1
    content = meta.get("content")
    detail["output_empty"] = not bool(content)
    # join keys for the OFFLINE provider-vs-overhead split (R511
    # ledger reconciliation precedent — the instrument records the
    # keys, the harvest joins the bytes).
    detail["join_keys"] = {
        "prompt_hash": meta.get("prompt_hash"),
        "output_hash": meta.get("output_hash"),
        "provider": meta.get("provider"),
        "model": meta.get("model"),
    }
    detail["provider_vs_overhead_split"] = (
        "OFFLINE_VIA_ROUTING_LEDGER (in-stage wall only; join the "
        "routing ledger on prompt_hash/output_hash for per-hop "
        "latencies — Art. XXV)")
    return detail


def build_record(clock: AttributionClock,
                 funnel: Dict[str, Any],
                 llm: Dict[str, Any],
                 state: str) -> Dict[str, Any]:
    """Assemble the space['runtime_attribution'] record. Pure. The
    12th subphase rides as the explicit offline marker (never a
    fabricated zero)."""
    spans = clock.spans()
    if not any(s.get("subphase") == "provider_call_split_offline"
               for s in spans):
        # canonical position: right after the wall span it splits
        # (SUBPHASES order is the contract consumers read); on paths
        # where the LLM call never ran, it trails the executed spans.
        try:
            at = next(i for i, s in enumerate(spans)
                      if s.get("subphase") == "llm_instantiation_wall") \
                + 1
        except StopIteration:
            at = len(spans)
        spans = spans[:at] + [dict(_OFFLINE_SPLIT_MARKER)] + spans[at:]
    return {
        "attribution_version": ATTRIBUTION_VERSION,
        "subphases": spans,
        "total_s": clock.total_s(),
        "funnel": funnel,
        "llm": llm,
        "terminal_state": state,
    }

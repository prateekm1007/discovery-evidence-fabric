"""discovery_fabric/engine/mechanism_space.py — R401: THE STRUCTURED
MECHANISM SPACE.

The R400-C run measured the weak pattern honestly: ONE problem -> ONE
primary mechanism + 5 exploration-grid prompt-variants. R401 replaces
the single-mechanism core with a structured mechanism space:

    MULTI-SOURCE EVIDENCE
      -> STRUCTURED EVIDENCE (11 fields, span-bound, provenance-custodied)
      -> FIVE TRANSFORMATION OPERATORS (deterministic input contracts +
         LLM instantiation, each with its own search constraint)
      -> CANONICAL MECHANISM CANDIDATES (9 required fields, versioned,
         hashed)
      -> MACHINE-CHECKABLE DISTINCTNESS (6 structural dimensions)
      -> MECHANISM-LEVEL EVIDENCE VERIFICATION (SUPPORTS /
         PARTIALLY_SUPPORTS / CONTRADICTS / IRRELEVANT /
         NOT_ENOUGH_EVIDENCE)

Constitutional anchors:
  Art. II   every extracted field binds to the smallest exact span;
            span validation is deterministic.
  Art. IV   no fallback epistemology — an unextracted field is
            UNEXTRACTED, never guessed.
  Art. VI   provenance is inherited from the custodied evidence item
            (source_id + content_hash + retrieval timestamp) — NO new
            truth ledger.
  Art. XVIII the LLM proposes fields; the deterministic validator
            decides admissibility.
  Art. XXV  unknown stays unknown; a candidate without a testable
            prediction is NOT_A_CANDIDATE (never silently kept).

All LLM access goes through llm_generate() in this module (one call
site — tests monkeypatch it; no other transport path exists).
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .candidate import sha256_obj

MECHANISM_SPACE_VERSION = "mechanism_space/1.0.0"

# ---------------------------------------------------------------------------
# 1. The structured evidence contract (R401 Phase 1 — the exact 11 fields)
# ---------------------------------------------------------------------------
STRUCTURED_EVIDENCE_FIELDS = (
    "source", "claim", "observed_effect", "system", "intervention",
    "mechanism", "boundary_conditions", "constraints", "failure_mode",
    "confidence", "provenance",
)
# Fields the LLM extracts from the evidence text (the other four —
# source, provenance, and the two custody composites — come from the
# ALREADY-CUSTODIED evidence item, never from the model).
_LLM_EXTRACTED_FIELDS = (
    "claim", "observed_effect", "system", "intervention", "mechanism",
    "boundary_conditions", "constraints", "failure_mode", "confidence",
)

VALID_CONFIDENCE = ("HIGH", "MEDIUM", "LOW")
UNEXTRACTED = "UNEXTRACTED"

EVIDENCE_EXTRACTION_PROMPT = """You are a structured-evidence extractor for an engineering discovery engine.

Given a problem statement and ONE retrieved scientific record, extract the structured fields.
Every extracted value must come from the record's own text. If the record does not state a field, write UNEXTRACTED — never guess.

PROBLEM:
- Device: {device}
- Failure: {failure}
- Constraint: {constraint}

RECORD:
- Title: {title}
- Abstract: {abstract}

Respond in EXACTLY this format (each field on ONE line):
CLAIM: <the single claim this record supports, in one sentence>
OBSERVED_EFFECT: <the effect that was actually observed/measured>
SYSTEM: <the physical system the observation was made in>
INTERVENTION: <the intervention or condition that was applied, if any>
MECHANISM: <the causal mechanism the record itself states or demonstrates>
BOUNDARY_CONDITIONS: <operating conditions/boundary conditions of the observation>
CONSTRAINTS: <physical or design constraints stated or implied>
FAILURE_MODE: <failure mode addressed or reported, if any>
CONFIDENCE: <HIGH, MEDIUM, or LOW — your confidence that the record supports its own claim>
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


# ---------------------------------------------------------------------------
# 2. The LLM call site (ONE path; tests monkeypatch this function)
# ---------------------------------------------------------------------------
def llm_generate(prompt: str, system: str = "", timeout: int = 240,
                 max_tokens: int = 700, purpose: str = "mechanism_space",
                 exclude_providers: Optional[List[str]] = None,
                 hard_pin_provider: Optional[str] = None
                 ) -> Dict[str, Any]:
    """Generate through the provider registry. exclude_providers removes
    providers from eligibility (used by the independent-attack separation
    and by operator instantiation to avoid the primary synthesis context
    where possible). Returns the LLMCallResult-shaped meta dict.

    R414: the eligibility order is now ROLE-ROUTED (directive §7) —
    evidence-extraction purposes prefer fast/cheap providers, attack
    purposes keep provider separation, synthesis keeps quality-first —
    and the registry cascades across providers on failure with every hop
    typed and recorded (the result meta carries provider_route).

    R491: hard_pin_provider pins the call to ONE provider id with NO
    fallback (SelectionPolicy max_preference_fallback=0 — the same
    operator-override semantics as the A2 gauntlet's ENGINE_ATTACK_
    PROVIDER pin). Purpose: the SEALED-CORPUS CALIBRATION MEASUREMENT
    must measure the instrument on the ring it declares, not on
    wherever the availability cascade lands under load — the R488
    measured lesson ("attacker calibration is (rules x ring), not
    rules alone": the same v3 rules measured FPR 0.25 on the strong
    ring's frozen outputs and FPR 1.0 live when the cascade fell to
    the free-tier ring). Fail-closed: an unavailable or failing pinned
    provider is PROVIDER_UNAVAILABLE / CALL_FAILED — NEVER a silent
    ring change. The pin travels in the returned meta (never silent,
    Art. IV). Production paths do not set it (their cascade keeps the
    never-refuse-to-run discipline, Art. V)."""
    from .llm_registry import (SelectionPolicy, availability_matrix,
                               generate)
    from .provider_health import order_for_role, role_for_purpose
    matrix = availability_matrix()
    available = [m["provider_id"] for m in matrix if m["available"]]
    hard_pin_status = "not_requested"
    if hard_pin_provider:
        # the measurement ring pin: ONE provider, ZERO fallback. A pin
        # that is not a registered provider id, or is credentialed-out,
        # fails closed RIGHT HERE — the LLM is never called on a ring
        # the measurement did not declare (recorded, never silent).
        registered = [m["provider_id"] for m in matrix]
        if hard_pin_provider not in registered:
            return {
                "ok": False, "status": "PROVIDER_UNAVAILABLE",
                "content": None, "provider": None, "model": None,
                "prompt_hash": None, "output_hash": None,
                "error": (f"hard pin '{hard_pin_provider}' names no "
                          f"registered provider id"),
                "hard_pin": {
                    "requested": hard_pin_provider,
                    "status": (f"unknown_provider_id "
                               f"({hard_pin_provider})")},
                "engine_llm_provider_pin": "not_set (hard_pin active)",
                "call_provenance": {}, "task_degradation": {},
                "cost_provenance": {},
                "excluded_providers": list(exclude_providers or []),
                "fallback_to_excluded": False,
            }
        if hard_pin_provider not in available:
            return {
                "ok": False, "status": "PROVIDER_UNAVAILABLE",
                "content": None, "provider": None, "model": None,
                "prompt_hash": None, "output_hash": None,
                "error": (f"hard-pinned provider '{hard_pin_provider}' "
                          f"holds no credential in this deployment"),
                "hard_pin": {
                    "requested": hard_pin_provider,
                    "status": (f"pinned_provider_unavailable "
                               f"({hard_pin_provider})")},
                "engine_llm_provider_pin": "not_set (hard_pin active)",
                "call_provenance": {}, "task_degradation": {},
                "cost_provenance": {},
                "excluded_providers": list(exclude_providers or []),
                "fallback_to_excluded": False,
            }
        hard_pin_status = "HARD_PINNED_NO_FALLBACK"
        policy = SelectionPolicy(
            preferred_providers=[hard_pin_provider],
            max_preference_fallback=0, purpose=purpose)
        res = generate(prompt, system=system, timeout=timeout,
                       max_retries=2, policy=policy, max_tokens=max_tokens,
                       max_provider_fallbacks=0)
        return {
            "ok": res.ok, "status": res.status, "content": res.content,
            "provider": res.provider_id, "model": res.model,
            "prompt_hash": res.prompt_hash, "output_hash": res.output_hash,
            "error": res.error,
            "hard_pin": {"requested": hard_pin_provider,
                         "status": hard_pin_status},
            "engine_llm_provider_pin": "not_set (hard_pin active)",
            "call_provenance": res.call_provenance,
            "task_degradation": res.task_degradation,
            "cost_provenance": res.cost_provenance,
            "excluded_providers": list(exclude_providers or []),
            "fallback_to_excluded": False,
        }
    if exclude_providers:
        remaining = [p for p in available
                     if p not in set(exclude_providers)]
        preferred = remaining or available  # honest fallback, recorded
    else:
        preferred = available
    # R414 role routing: order the eligible providers for the purpose's
    # role (deterministic; cooldown-aware inside order_for_role). The
    # operator pin below can still promote one provider to the head.
    role = role_for_purpose(purpose)
    if preferred:
        preferred = order_for_role(matrix, role,
                                   avoid_provider=(
                                       set(exclude_providers or []).pop()
                                       if exclude_providers else None))
        if exclude_providers:
            # re-apply the exclusion on the role-ordered list (the
            # honest fallback when NOTHING remains is preserved above)
            remaining = [p for p in preferred
                         if p not in set(exclude_providers)]
            preferred = remaining or preferred
        elif available:
            preferred = [p for p in preferred if p in set(available)]
    # ENGINE_LLM_PROVIDER operator pin (R391 operator-override class):
    # the operator may pin one provider at the head of the eligibility
    # order. A pinned provider without a credential is RECORDED and
    # falls through to the normal order honestly — it never blocks a
    # call, and the pin status travels in the call meta (never silent).
    pin = os.environ.get("ENGINE_LLM_PROVIDER", "").strip()
    pin_status = "not_set"
    if pin:
        if pin in preferred:
            preferred = [pin] + [p for p in preferred if p != pin]
            pin_status = "pinned_to_head"
        else:
            pin_status = f"requested_but_unavailable ({pin})"
    policy = SelectionPolicy(
        preferred_providers=preferred or ["atria", "zai", "openrouter",
                                           "nvidia", "anthropic", "openai",
                                           "gemini", "qwen", "deepseek",
                                           "mistral"],
        purpose=purpose)
    res = generate(prompt, system=system, timeout=timeout,
                   max_retries=2, policy=policy, max_tokens=max_tokens,
                   max_provider_fallbacks=2)
    return {
        "ok": res.ok, "status": res.status, "content": res.content,
        "provider": res.provider_id, "model": res.model,
        "prompt_hash": res.prompt_hash, "output_hash": res.output_hash,
        "error": res.error,
        "engine_llm_provider_pin": pin_status,
        # R451-C1.3/C1.4: the run provenance + the task-degradation
        # record travel into the scientific meta — a candidate states
        # WHICH capability class actually produced it (STRONG vs
        # CHEAP_EMERGENCY_FALLBACK), never silently relabeled
        "call_provenance": res.call_provenance,
        "task_degradation": res.task_degradation,
        "cost_provenance": res.cost_provenance,
        "excluded_providers": list(exclude_providers or []),
        "fallback_to_excluded": bool(
            exclude_providers and not remaining) if exclude_providers
        else False,
        "provider_route": [
            {"provider": h.get("provider_attempted"),
             "failure_type": h.get("failure_type"),
             "fallback_provider": h.get("fallback_provider")}
            for h in (res.route or [])],
        "failure_type": res.failure_type,
        "role": role,
    }


# ---------------------------------------------------------------------------
# 3. Deterministic validation (Art. II / III / XVIII)
# ---------------------------------------------------------------------------
_FIELD_LINE_RE = re.compile(
    r"^(CLAIM|OBSERVED_EFFECT|SYSTEM|INTERVENTION|MECHANISM|"
    r"BOUNDARY_CONDITIONS|CONSTRAINTS|FAILURE_MODE|CONFIDENCE)\s*:\s*(.*)$",
    re.MULTILINE)


def _parse_field_lines(text: str) -> Dict[str, str]:
    parsed = {f.lower(): "" for f in _LLM_EXTRACTED_FIELDS}
    for m in _FIELD_LINE_RE.finditer(text or ""):
        parsed[m.group(1).lower()] = m.group(2).strip()
    return parsed


def _terms(text: str) -> set:
    from discovery_fabric.source_registry.query_relevance import terms as _t
    return set(_t(str(text or "")))


def validate_extraction(parsed: Dict[str, str], item_text: str
                        ) -> Dict[str, Any]:
    """Deterministic validation of extracted fields against the record's
    own text. A field whose content terms do not appear in the record is
    UNTRUSTED (the model imported outside knowledge — Art. XVIII) and is
    demoted to UNEXTRACTED with the measurement recorded."""
    record_terms = _terms(item_text)
    field_states: Dict[str, Dict[str, Any]] = {}
    for f in _LLM_EXTRACTED_FIELDS:
        val = str(parsed.get(f) or "").strip()
        if f == "confidence":
            ok = val.upper() in VALID_CONFIDENCE if val else False
            field_states[f] = {
                "value": val.upper() if ok else UNEXTRACTED,
                "state": "VALID" if ok else "INVALID_VALUE",
                "binding": None}
            continue
        if not val or val.upper() == UNEXTRACTED:
            field_states[f] = {"value": UNEXTRACTED, "state": "UNEXTRACTED",
                               "binding": None}
            continue
        fterms = _terms(val)
        overlap = fterms & record_terms
        # binding rule: >= 1 content term of the field must appear in the
        # record text (the smallest exact-span discipline at term grain —
        # a field whose vocabulary is wholly absent was imported, not
        # extracted; threshold 2 for the two long-form causal fields)
        need = 2 if f in ("mechanism", "claim", "observed_effect") else 1
        bound = len(overlap) >= need
        field_states[f] = {
            "value": val if bound else UNEXTRACTED,
            "state": "VALID" if bound else "UNTRUSTED_NOT_IN_RECORD",
            "binding": {"n_shared_terms": len(overlap),
                        "shared_terms": sorted(overlap)[:12],
                        "required": need}}
    return field_states


def extract_structured_evidence_item(item: Dict[str, Any],
                                     problem: Dict[str, Any],
                                     ) -> Dict[str, Any]:
    """Convert ONE custodied evidence item into structured data (the 11
    R401 fields). LLM proposes; the deterministic validator admits.
    Provenance is INHERITED from the custodied item (Art. VI — no new
    ledger, the existing custody chain is the authority)."""
    title = str(item.get("title") or "")
    abstract = str(item.get("abstract") or "")[:1600]
    item_text = f"{title} {abstract}"
    prompt = EVIDENCE_EXTRACTION_PROMPT.format(
        device=problem.get("device", ""),
        failure=problem.get("failure", ""),
        constraint=problem.get("constraint", ""),
        title=title, abstract=abstract)
    meta = llm_generate(prompt, system="You are a precise evidence "
                          "extractor. Never invent content.",
                        purpose="structured_evidence_extraction")
    fields: Dict[str, Dict[str, Any]] = {
        f: {"value": UNEXTRACTED, "state": "LLM_UNAVAILABLE",
            "binding": None} for f in _LLM_EXTRACTED_FIELDS}
    retry_note = None
    if meta.get("ok"):
        parsed = _parse_field_lines(meta["content"] or "")
        fields = validate_extraction(parsed, item_text)
        # R401 RECORDED EXTRACTION RETRY (same provider, one attempt,
        # fully recorded): a record the mechanism-signal ranker
        # selected as CAUSAL+EFFECT dense whose mechanism/observed
        # effect still came back UNEXTRACTED gets ONE corrective
        # attempt — the ranker measured signal the extraction missed.
        # The validator is UNCHANGED; a retry that invents content is
        # still demoted (Art. XVIII decides, not the retry).
        _dense = mechanism_signal_score({"title": title,
                                         "abstract": abstract})
        _mech_missing = (fields.get("mechanism", {}).get("value")
                         == UNEXTRACTED)
        if (_mech_missing
                and _dense.get("classes_present", 0) >= 2
                and "causal" in (_dense.get("class_hits") or {})):
            retry_note = (
                "recorded extraction retry (same provider/model, one "
                "attempt): the record carries causal+effect signal "
                "density (ranker classes: " + ", ".join(sorted(
                    (_dense.get("class_hits") or {}).keys())) +
                ") but MECHANISM/OBSERVED_EFFECT returned UNEXTRACTED")
            meta = llm_generate(
                prompt + "\n\nCORRECT YOUR PREVIOUS ATTEMPT: this "
                "record demonstrably reports demonstrated effects and "
                "causal observations — re-read the text and extract "
                "CLAIM, OBSERVED_EFFECT, SYSTEM and MECHANISM from "
                "what the record ACTUALLY states. Still write "
                "UNEXTRACTED only for fields the text genuinely does "
                "not support.",
                system="You are a precise evidence extractor. Never "
                       "invent content.",
                purpose="structured_evidence_extraction_retry")
            if meta.get("ok"):
                parsed = _parse_field_lines(meta["content"] or "")
                fields = validate_extraction(parsed, item_text)
    # the four custody-composite fields (never model-derived)
    structured: Dict[str, Any] = {
        "structured_evidence_version": MECHANISM_SPACE_VERSION,
        "item_id": item.get("id") or item.get("record_id") or "",
        "fields": {f: fields[f] for f in _LLM_EXTRACTED_FIELDS},
        # source + provenance: the EXISTING custody architecture
        "source": {
            "source_id": item.get("id", ""),
            "source_name": item.get("source", "UNKNOWN"),
            "content_hash": item.get("content_hash", ""),
            "title": title[:300],
            "retrieval_timestamp": item.get("retrieval_timestamp", ""),
            "source_uri": item.get("source_uri", ""),
            "doi": item.get("doi", ""),
        },
        "provenance": {
            "custody": "inherited_from_evidence_item (Art. VI — the "
                       "existing custody chain; no competing ledger)",
            "extraction_provider": meta.get("provider"),
            "extraction_model": meta.get("model"),
            "extraction_status": meta.get("status"),
            "prompt_hash": meta.get("prompt_hash"),
            "output_hash": meta.get("output_hash"),
            "extraction_retry_note": retry_note,
            "extracted_at": utc_now(),
        },
        "extraction_meta": meta,
        "confidence": (fields.get("confidence", {}) or {}).get(
            "value", UNEXTRACTED),
    }
    structured["structured_hash"] = sha256_obj(
        {k: structured[k] for k in
         ("item_id", "fields", "source", "provenance")})
    # R401A A5: the retrieval that fed this item is DISCOVERY_SUPPORT
    # evidence — it is what the five operators consume to CREATE
    # mechanisms (the VERIFICATION_SUPPORT plane is the four-direction
    # search stage around a serious candidate)
    structured["retrieval_role"] = "DISCOVERY_SUPPORT"
    # carry the record's own text so every span validation downstream
    # (operator instantiation, verification) binds against the SAME
    # text the extraction saw — never a re-derived or missing basis
    structured["_record_text"] = item_text
    n_valid = sum(1 for f in fields.values()
                  if f.get("state") == "VALID")
    n_untrusted = sum(1 for f in fields.values()
                      if f.get("state") == "UNTRUSTED_NOT_IN_RECORD")
    structured["extraction_summary"] = {
        "n_fields_valid": n_valid,
        "n_fields_unextracted": sum(
            1 for f in fields.values()
            if f.get("value") == UNEXTRACTED),
        "n_fields_untrusted_demoted": n_untrusted,
        "mechanism_extracted": bool(
            (fields.get("mechanism", {}) or {}).get("state") == "VALID"),
    }
    return structured


# ---------------------------------------------------------------------------
# 4. Mechanism-signal reranking (R401 Phase 5 — retrieval in service of
#    the mechanism space; deterministic, recorded, no semantic fallback)
# ---------------------------------------------------------------------------
# Vocabulary classes a MECHANISM-bearing record signals (each class is a
# recorded policy input — Art. XXVII; density over classes, not counts)
MECHANISM_SIGNAL_VOCAB: Dict[str, Tuple[str, ...]] = {
    "causal": (
        "causes", "caused by", "attributed to", "due to", "results from",
        "results in", "leads to", "we show", "we demonstrate",
        "demonstrated that", "shown to", "driven by", "mediated by",
        "because", "mechanism", "pathway", "underlying",
    ),
    "intervention": (
        "treated with", "coated with", "modified", "introduced",
        "implanted", "applied", "configured", "designed with",
        "incorporating", "fabricated", "deployed",
    ),
    "boundary": (
        "at flow", "under pressure", "at temperature", "in vivo",
        "in vitro", "at ph", "under load", "at Reynolds", "flow rate",
        "pressure gradient", "operating conditions", "shear rate",
        "concentration",
    ),
    "failure": (
        "failure", "failed", "fracture", "occlusion", "thrombosis",
        "restenosis", "fouling", "erosion", "corrosion", "fatigue",
        "delamination", "infection", "migration", "leakage", "wear",
    ),
    "effect": (
        "reduced", "increased", "decreased", "improved", "enhanced",
        "significantly", "fold", "%", "measured", "compared",
        "statistically",
    ),
}


def mechanism_signal_score(record: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic mechanism-signal density of one record. The score
    is the number of DISTINCT signal classes present (0-5) plus the
    term density; the basis is recorded per class. This reranks records
    for structured extraction — retrieval serving the mechanism space,
    never a relevance verdict on its own (Art. XXI: search activity is
    not evidence)."""
    text = " ".join(str(record.get(k) or "") for k in
                    ("title", "abstract", "snippet")).lower()
    hits: Dict[str, List[str]] = {}
    for cls, vocab in MECHANISM_SIGNAL_VOCAB.items():
        found = [v for v in vocab if v in text]
        if found:
            hits[cls] = found[:6]
    classes = len(hits)
    density = sum(len(v) for v in hits.values())
    score = classes + min(density, 10) / 10.0
    return {"classes_present": classes, "class_hits": hits,
            "term_density": density, "score": round(score, 2)}


def mechanism_signal_rerank(records: List[Dict[str, Any]],
                            top_k: int = 6
                            ) -> Dict[str, Any]:
    """Rank records by mechanism-signal density; return the top-k with
    the full recorded basis (every record's score, kept or dropped)."""
    scored = []
    for r in records:
        s = mechanism_signal_score(r)
        s["record_id"] = r.get("id") or r.get("record_id") or ""
        s["title"] = (r.get("title") or "")[:120]
        scored.append(s)
    order = sorted(range(len(records)),
                   key=lambda i: (-scored[i]["score"], scored[i].get(
                       "record_id") or ""))
    top = order[:max(0, top_k)]
    return {
        "reranker_version": "mechanism_signal_rerank/1.0.0",
        "n_input": len(records), "top_k": top_k,
        "selected_indexes": top,
        "selected_ids": [scored[i].get("record_id") for i in top],
        "all_scores": scored,
        "policy": ("deterministic vocabulary-class density; recorded "
                   "basis per record; NOT a relevance verdict (Art. XXI)"),
    }


# ---------------------------------------------------------------------------
# 5. The canonical mechanism candidate (9 R401-required fields)
# ---------------------------------------------------------------------------
CANDIDATE_REQUIRED_FIELDS = (
    "mechanism_graph", "evidence_bundle", "constraint_set",
    "predicted_effect", "known_failure_modes", "novel_design_variable",
    "testable_prediction", "transformation_operator", "derivation_trace",
)

_QUANTITY_RE = re.compile(
    r"\d|increase|decrease|reduce|improve|fold|percent|ratio|rate|"
    r"higher|lower|faster|slower|larger|smaller", re.IGNORECASE)


def build_mechanism_graph(structured_item: Dict[str, Any],
                          candidate_fields: Dict[str, str]
                          ) -> Dict[str, Any]:
    """Deterministic causal graph assembled from the structured fields
    (nodes carry normalized term sets; edges carry types). This is the
    machine-checkable mechanism representation distinctness compares."""
    f = {k: (v or {}).get("value", "") if isinstance(v, dict) else str(v)
         for k, v in (structured_item.get("fields") or {}).items()}
    intervention = candidate_fields.get("intervention", "")
    mechanism = candidate_fields.get("mechanism", "")
    nodes = {
        "intervention_site": {
            "label": "INTERVENTION",
            "terms": sorted(_terms(intervention))[:20]},
        "causal_agent": {
            "label": "MECHANISM",
            "terms": sorted(_terms(mechanism) | _terms(
                f.get("mechanism", "")))[:20]},
        "physical_effect": {
            "label": "PREDICTED_EFFECT",
            "terms": sorted(_terms(
                candidate_fields.get("predicted_effect", "")))[:20]},
        "observed_outcome": {
            "label": "OBSERVED_EFFECT",
            "terms": sorted(_terms(f.get("observed_effect", "")))[:20]},
    }
    edges = [
        {"from": "intervention_site", "to": "causal_agent",
         "relation": "ACTIVATES"},
        {"from": "causal_agent", "to": "physical_effect",
         "relation": "PRODUCES"},
    ]
    if nodes["observed_outcome"]["terms"]:
        edges.append({"from": "physical_effect", "to": "observed_outcome",
                      "relation": "MEASURES_AGAINST"})
    return {"nodes": nodes, "edges": edges,
            "graph_version": "mechanism_graph/1.0.0"}


def _testable_prediction_check(prediction: str) -> Dict[str, Any]:
    """A candidate without a testable prediction is NOT an invention
    candidate (R401 Phase 2 requirement, enforced here — never silently
    kept). A testable prediction must state a measurable quantity and a
    direction or condition."""
    p = str(prediction or "").strip()
    has_quantity = bool(_QUANTITY_RE.search(p))
    long_enough = len(_terms(p)) >= 4
    return {"present": bool(p), "measurable_quantity": has_quantity,
            "sufficiently_specific": long_enough,
            "testable": bool(p and has_quantity and long_enough)}


def assemble_candidate(operator: Dict[str, Any],
                       structured_item: Dict[str, Any],
                       fields: Dict[str, str],
                       problem: Dict[str, Any],
                       llm_meta: Dict[str, Any],
                       ) -> Dict[str, Any]:
    """Assemble the canonical mechanism candidate. Validation failures
    are recorded states (NOT_A_CANDIDATE), never silent drops."""
    testable = _testable_prediction_check(
        fields.get("testable_prediction", ""))
    mechanism_graph = build_mechanism_graph(structured_item, fields)
    derivation_trace = {
        "operator": operator["operator_id"],
        "operator_rule_version": operator["version"],
        "input_contract": operator["input_contract"](
            structured_item, problem),
        "selection_result": structured_item.get("_selection", {}),
        "llm_provider": llm_meta.get("provider"),
        "llm_model": llm_meta.get("model"),
        "prompt_hash": llm_meta.get("prompt_hash"),
        "output_hash": llm_meta.get("output_hash"),
        # R451-C1.3/C1.4: the candidate's derivation trace carries the
        # run provenance and the task-degradation record — the FINAL
        # SCIENTIFIC RECORD states which capability class produced the
        # candidate (a CHEAP_EMERGENCY_FALLBACK candidate is never
        # read as STRONG reasoning; the directive's explicit rule)
        "call_provenance": llm_meta.get("call_provenance"),
        "task_degradation": llm_meta.get("task_degradation"),
        "cost_provenance": llm_meta.get("cost_provenance"),
        "source_item_id": structured_item.get("item_id"),
        "derived_at": utc_now(),
    }
    cand = {
        "candidate_schema": "mechanism_candidate/1.0.0",
        "mechanism_space_version": MECHANISM_SPACE_VERSION,
        "candidate_id": "",
        "transformation_operator": operator["operator_id"],
        "mechanism": fields.get("mechanism", ""),
        "intervention": fields.get("intervention", ""),
        "mechanism_graph": mechanism_graph,
        "evidence_bundle": {
            "primary_item_id": structured_item.get("item_id"),
            "primary_structured_hash":
                structured_item.get("structured_hash"),
            "primary_source": structured_item.get("source", {}),
            "mechanism_source_span": fields.get(
                "mechanism_source_span", ""),
            # Art. XLIV (audit CB-3): every mechanism records the
            # evidence generation it was built from — the plane, the
            # snapshot id + hash, the retrieval role / version /
            # sources / timestamp. A candidate is never ambiguous
            # about which evidence freeze it came from.
            "evidence_plane": structured_item.get("_evidence_plane", ""),
            "evidence_snapshot_id": structured_item.get(
                "_evidence_snapshot_id", ""),
            "evidence_hash": structured_item.get("_evidence_hash", ""),
            "retrieval_role": structured_item.get("_retrieval_role", ""),
            "retrieval_version": (
                "multi_source_expansion/2.0.0"
                if structured_item.get("_evidence_plane") ==
                "DISCOVERY_EXPANSION" else "a2_retrieve/frozen_envelope"),
            "retrieval_sources": structured_item.get(
                "_retrieval_sources", ""),
            "retrieval_timestamp": structured_item.get(
                "_retrieval_timestamp", ""),
        },
        "constraint_set": {
            "problem_constraint": problem.get("constraint", ""),
            "boundary_conditions": fields.get("boundary_conditions", ""),
            "stated_constraints": ((structured_item.get("fields") or {})
                                   .get("constraints", {}) or {})
            .get("value", ""),
        },
        "predicted_effect": fields.get("predicted_effect", ""),
        "known_failure_modes": [fm.strip() for fm in re.split(
            r"[;.]", fields.get("known_failure_modes", "")) if fm.strip()
        ][:6],
        "novel_design_variable": fields.get("novel_design_variable", ""),
        "testable_prediction": fields.get("testable_prediction", ""),
        "testable_prediction_check": testable,
        "derivation_trace": derivation_trace,
        "falsification_test": fields.get("testable_prediction", ""),
        "expected_effect": fields.get("predicted_effect", ""),
        "mechanism_source_span": fields.get("mechanism_source_span", ""),
        "extraction_confidence": structured_item.get("confidence",
                                                     UNEXTRACTED),
        "candidate_state": "CANDIDATE" if testable["testable"] else
        "NOT_A_CANDIDATE_NO_TESTABLE_PREDICTION",
    }
    cand["candidate_id"] = (
        f"cand:MS:{operator['operator_id']}:"
        f"{sha256_obj({k: cand[k] for k in CANDIDATE_REQUIRED_FIELDS})[:12]}"
    ) if cand["candidate_state"] == "CANDIDATE" else (
        f"noncand:MS:{operator['operator_id']}:"
        f"{sha256_obj(cand['derivation_trace'])[:12]}")
    cand["candidate_hash"] = sha256_obj(
        {k: cand[k] for k in CANDIDATE_REQUIRED_FIELDS})
    return cand


# ---------------------------------------------------------------------------
# 6. The five transformation operators (R401 Phase 2)
#
# These are NOT five prompts. Each operator has:
#   - an INPUT CONTRACT: a deterministic predicate over the STRUCTURED
#     evidence (which items this operator may consume, and why — recorded
#     per item in the derivation trace);
#   - a SEARCH CONSTRAINT: the region of the mechanism space the operator
#     explores (structural, not lexical);
#   - a TRANSFORMATION RULE: how the structured fields are transformed;
#   - a DETERMINISTIC OUTPUT SCHEMA with a REQUIRED testable prediction;
#   - a FAILURE STATE: honest refusal when no applicable evidence exists;
#   - PROVENANCE + derivation trace per candidate.
#
# The LLM performs the INSTANTIATION step only (structured input in,
# field-line output out, span-bound); selection and validation are
# deterministic (Art. XVIII).
# ---------------------------------------------------------------------------

def _field_val(item: Dict[str, Any], name: str) -> str:
    v = (item.get("fields") or {}).get(name, {})
    return str((v or {}).get("value") or "")


def _domain_terms(text: str) -> set:
    return _terms(text)


def _contract_direct_transfer(item: Dict[str, Any],
                              problem: Dict[str, Any]) -> Dict[str, Any]:
    """DIRECT_TRANSFER input contract: the evidence's SYSTEM matches the
    problem's device domain (>= 2 shared domain terms) — the mechanism
    was demonstrated IN the target system class."""
    device = str(problem.get("device") or "") + " " + str(
        problem.get("failure") or "")
    system = _field_val(item, "system")
    shared = sorted(_domain_terms(device) & _domain_terms(system))
    return {"operator": "DIRECT_TRANSFER",
            "satisfied": len(shared) >= 2,
            "shared_system_terms": shared,
            "basis": "evidence system-domain overlaps the problem "
                     "device domain (>= 2 terms)"}


def _contract_cross_domain_analogy(item: Dict[str, Any],
                                   problem: Dict[str, Any]) -> Dict[str, Any]:
    """CROSS_DOMAIN_ANALOGY input contract: the evidence's system does
    NOT match the problem domain (zero system overlap) while its
    MECHANISM still speaks to the problem's failure vocabulary — the
    causal structure is transferable, the system is not."""
    device = str(problem.get("device") or "")
    system = _field_val(item, "system")
    mechanism = _field_val(item, "mechanism") + " " + _field_val(
        item, "observed_effect")
    shared_system = sorted(_domain_terms(device) & _domain_terms(system))
    failure_terms = _domain_terms(str(problem.get("failure") or "") + " " +
                                  str(problem.get("failure_mode") or ""))
    mech_overlap = sorted(failure_terms & _domain_terms(mechanism))
    return {"operator": "CROSS_DOMAIN_ANALOGY",
            "satisfied": len(shared_system) == 0 and len(mech_overlap) >= 1,
            "shared_system_terms": shared_system,
            "failure_mechanism_overlap": mech_overlap,
            "basis": "system is foreign to the problem domain while the "
                     "mechanism/failure vocabulary overlaps — analogy "
                     "material, never direct support"}


_GEOMETRY_VOCAB = None


def _geometry_vocab() -> set:
    global _GEOMETRY_VOCAB
    if _GEOMETRY_VOCAB is None:
        _GEOMETRY_VOCAB = {
            "lumen", "lumens", "channel", "channels", "mesh", "porous",
            "porosity", "surface", "coating", "cross", "section",
            "geometry", "diameter", "tube", "tubular", "conduit",
            "groove", "grooves", "spiral", "helical", "bifurcated",
            "tapered", "annular", "wall", "walls", "layer", "layers",
            "grating", "perforated", "slit", "slits", "bore", "mesh",
            "fiber", "fibers", "scaffold", "roughness", "patterned",
        }
    return _GEOMETRY_VOCAB


def _contract_geometric_transformation(item: Dict[str, Any],
                                        problem: Dict[str, Any]
                                        ) -> Dict[str, Any]:
    """GEOMETRIC_TRANSFORMATION input contract: the evidence's
    mechanism/intervention carries geometric embodiment vocabulary — the
    mechanism operates through a physical structure whose geometry can
    be transformed (count, scale, topology, arrangement)."""
    text = " ".join([_field_val(item, "mechanism"),
                     _field_val(item, "intervention"),
                     _field_val(item, "observed_effect")]).lower()
    hits = sorted(_geometry_vocab() & set(re.findall(r"[a-z]+", text)))
    return {"operator": "GEOMETRIC_TRANSFORMATION",
            "satisfied": len(hits) >= 1,
            "geometry_terms": hits,
            "basis": "the mechanism is embodied in a physical structure "
                     "whose geometry is transformable (>= 1 geometry term)"}


_BOUNDARY_VOCAB = None


def _boundary_vocab() -> set:
    global _BOUNDARY_VOCAB
    if _BOUNDARY_VOCAB is None:
        _BOUNDARY_VOCAB = {
            "pressure", "flow", "temperature", "viscosity", "shear",
            "ph", "osmolality", "load", "stress", "strain", "frequency",
            "voltage", "current", "concentration", "velocity", "regime",
            "laminar", "turbulent", "steady", "pulsatile", "cyclic",
            "static", "dynamic", "humidity", "sterile", "corrosive",
            "abrasive", "physiological",
        }
    return _BOUNDARY_VOCAB


def _contract_boundary_condition_change(item: Dict[str, Any],
                                        problem: Dict[str, Any]
                                        ) -> Dict[str, Any]:
    """BOUNDARY_CONDITION_CHANGE input contract: the evidence carries
    explicit boundary/operating conditions under which the mechanism was
    observed — the mechanism can be relocated to a different boundary
    regime (the problem's constraint regime)."""
    bc = _field_val(item, "boundary_conditions").lower()
    hits = sorted(_boundary_vocab() & set(re.findall(r"[a-z]+", bc)))
    return {"operator": "BOUNDARY_CONDITION_CHANGE",
            "satisfied": len(hits) >= 1,
            "boundary_terms": hits,
            "problem_constraint": str(problem.get("constraint") or "")[:200],
            "basis": "the mechanism was observed under explicit boundary "
                     "conditions that can be changed to the problem's "
                     "regime"}


def _contract_failure_path_inversion(item: Dict[str, Any],
                                     problem: Dict[str, Any]
                                     ) -> Dict[str, Any]:
    """FAILURE_PATH_INVERSION input contract: the evidence documents a
    FAILURE MODE (a failure pathway with a cause) — the pathway can be
    inverted: engineer the anti-condition, or use the failure mechanism
    itself as the operating principle."""
    fm = _field_val(item, "failure_mode")
    problem_fm = str(problem.get("failure_mode") or "") + " " + str(
        problem.get("failure") or "")
    fm_terms = _domain_terms(fm)
    problem_fm_terms = _domain_terms(problem_fm)
    shared = sorted(fm_terms & problem_fm_terms)
    return {"operator": "FAILURE_PATH_INVERSION",
            "satisfied": bool(fm.strip()) and len(fm_terms) >= 1,
            "failure_mode_terms": sorted(fm_terms)[:10],
            "shared_with_problem_failure": shared,
            "basis": "the evidence documents a failure pathway that can "
                     "be inverted into an operating mechanism"}


_OPERATOR_INSTANTIATION_PROMPTS: Dict[str, str] = {
    "DIRECT_TRANSFER": """You are a mechanism engineer. Transfer the demonstrated mechanism into the target device DIRECTLY — same mechanism, new instantiation.

STRUCTURED EVIDENCE (from a domain-matched source):
- System: {system}
- Mechanism: {mechanism}
- Observed effect: {observed_effect}
- Intervention: {evidence_intervention}
- Boundary conditions: {boundary_conditions}
- Constraints: {constraints}
- Failure mode addressed: {failure_mode}

TARGET PROBLEM:
- Device: {device}
- Failure: {failure}
- Constraint: {constraint}

RECORD TEXT (the ONLY admissible source for MECHANISM_SOURCE_SPAN — quote your span VERBATIM from here):
{record_text}

Respond in EXACTLY this format (each field on ONE line):
MECHANISM: <the causal mechanism, stated as a physical phenomenon>
INTERVENTION: <the specific design change in the device>
PREDICTED_EFFECT: <the measurable effect on the failure quantity>
NOVEL_DESIGN_VARIABLE: <the ONE new design variable this candidate introduces>
TESTABLE_PREDICTION: <a falsifiable prediction: measurable quantity + direction + conditions>
KNOWN_FAILURE_MODES: <how this design fails, one clause per failure separated by semicolons>
BOUNDARY_CONDITIONS: <operating envelope where the mechanism holds>
MECHANISM_SOURCE_SPAN: <verbatim substring from the source abstract supporting the mechanism>""",
    "CROSS_DOMAIN_ANALOGY": """You are a mechanism engineer. A mechanism demonstrated in a DIFFERENT system must be mapped onto the target device by causal-structure analogy. The analogy must be explicit — the causal chain transfers, the materials/system do not.

SOURCE SYSTEM (foreign domain):
- System: {system}
- Mechanism: {mechanism}
- Observed effect: {observed_effect}
- Intervention: {evidence_intervention}
- Boundary conditions: {boundary_conditions}

TARGET PROBLEM:
- Device: {device}
- Failure: {failure}
- Constraint: {constraint}

RECORD TEXT (the ONLY admissible source for MECHANISM_SOURCE_SPAN — quote your span VERBATIM from here):
{record_text}

Respond in EXACTLY this format (each field on ONE line):
MECHANISM: <the causal mechanism as mapped into the target system>
INTERVENTION: <the specific design change in the device>
PREDICTED_EFFECT: <the measurable effect on the failure quantity>
NOVEL_DESIGN_VARIABLE: <the ONE new design variable this candidate introduces>
TESTABLE_PREDICTION: <a falsifiable prediction: measurable quantity + direction + conditions>
KNOWN_FAILURE_MODES: <how this design fails, one clause per failure separated by semicolons>
BOUNDARY_CONDITIONS: <operating envelope where the mapped mechanism holds>
MECHANISM_SOURCE_SPAN: <verbatim substring from the source abstract supporting the source mechanism>""",
    "GEOMETRIC_TRANSFORMATION": """You are a mechanism engineer. Transform the GEOMETRY through which the mechanism operates — change count, scale, topology, or arrangement of the physical structure — while preserving the causal mechanism.

STRUCTURED EVIDENCE:
- System: {system}
- Mechanism: {mechanism}
- Observed effect: {observed_effect}
- Geometry-bearing intervention: {evidence_intervention}

TARGET PROBLEM:
- Device: {device}
- Failure: {failure}
- Constraint: {constraint}

RECORD TEXT (the ONLY admissible source for MECHANISM_SOURCE_SPAN — quote your span VERBATIM from here):
{record_text}

Respond in EXACTLY this format (each field on ONE line):
MECHANISM: <the causal mechanism (preserved under the geometric change)>
INTERVENTION: <the specific geometric design change in the device>
PREDICTED_EFFECT: <the measurable effect on the failure quantity>
NOVEL_DESIGN_VARIABLE: <the ONE geometric variable this candidate introduces>
TESTABLE_PREDICTION: <a falsifiable prediction: measurable quantity + direction + conditions>
KNOWN_FAILURE_MODES: <how this design fails, one clause per failure separated by semicolons>
BOUNDARY_CONDITIONS: <operating envelope where the mechanism holds>
MECHANISM_SOURCE_SPAN: <verbatim substring from the source abstract supporting the mechanism>""",
    "BOUNDARY_CONDITION_CHANGE": """You are a mechanism engineer. Relocate the mechanism to a DIFFERENT operating regime: the problem's boundary conditions differ from the evidence's — re-derive the intervention so the mechanism operates under the problem's regime.

STRUCTURED EVIDENCE:
- System: {system}
- Mechanism: {mechanism}
- Observed effect (under): {boundary_conditions}
- Failure mode: {failure_mode}

TARGET PROBLEM:
- Device: {device}
- Failure: {failure}
- Constraint (the new regime): {constraint}

RECORD TEXT (the ONLY admissible source for MECHANISM_SOURCE_SPAN — quote your span VERBATIM from here):
{record_text}

Respond in EXACTLY this format (each field on ONE line):
MECHANISM: <the causal mechanism under the NEW boundary regime>
INTERVENTION: <the specific design change that enables operation in the new regime>
PREDICTED_EFFECT: <the measurable effect on the failure quantity>
NOVEL_DESIGN_VARIABLE: <the ONE regime-enabling design variable>
TESTABLE_PREDICTION: <a falsifiable prediction: measurable quantity + direction + conditions>
KNOWN_FAILURE_MODES: <how this design fails, one clause per failure separated by semicolons>
BOUNDARY_CONDITIONS: <the NEW operating envelope>
MECHANISM_SOURCE_SPAN: <verbatim substring from the source abstract supporting the mechanism>""",
    "FAILURE_PATH_INVERSION": """You are a mechanism engineer. INVERT the documented failure pathway into the operating principle: engineer the anti-condition of the failure cause, or use the failure mechanism itself as the design's working mechanism.

DOCUMENTED FAILURE EVIDENCE:
- System: {system}
- Failure mode: {failure_mode}
- Mechanism of failure: {mechanism}
- Observed effect: {observed_effect}

TARGET PROBLEM:
- Device: {device}
- Failure: {failure}
- Constraint: {constraint}

RECORD TEXT (the ONLY admissible source for MECHANISM_SOURCE_SPAN — quote your span VERBATIM from here):
{record_text}

Respond in EXACTLY this format (each field on ONE line):
MECHANISM: <the inverted causal mechanism now used as the operating principle>
INTERVENTION: <the specific design change realizing the inversion>
PREDICTED_EFFECT: <the measurable effect on the failure quantity>
NOVEL_DESIGN_VARIABLE: <the ONE variable that flips the failure pathway>
TESTABLE_PREDICTION: <a falsifiable prediction: measurable quantity + direction + conditions>
KNOWN_FAILURE_MODES: <how this design fails, one clause per failure separated by semicolons>
BOUNDARY_CONDITIONS: <operating envelope where the inversion holds>
MECHANISM_SOURCE_SPAN: <verbatim substring from the source abstract documenting the failure mechanism>""",
}


def _operator(operator_id: str, contract, rule: str,
              constraint: str) -> Dict[str, Any]:
    return {
        "operator_id": operator_id,
        "version": f"{operator_id}/1.0.0",
        "input_contract": contract,
        "transformation_rule": rule,
        "search_constraint": constraint,
        "failure_state": "NO_APPLICABLE_EVIDENCE",
        "output_schema": "mechanism_candidate/1.0.0 (9 required fields "
                         "+ REQUIRED testable_prediction — a candidate "
                         "without one is NOT_A_CANDIDATE)",
        "prompt_template_hash": hashlib.sha256(
            _OPERATOR_INSTANTIATION_PROMPTS[operator_id].encode()
        ).hexdigest()[:16],
    }


TRANSFORMATION_OPERATORS: List[Dict[str, Any]] = [
    _operator(
        "DIRECT_TRANSFER",
        _contract_direct_transfer,
        "instantiate the domain-matched mechanism unchanged; re-derive "
        "only the intervention site and design variable",
        "the region where the evidence system IS the problem system "
        "(same-domain demonstrated mechanisms)"),
    _operator(
        "CROSS_DOMAIN_ANALOGY",
        _contract_cross_domain_analogy,
        "map the foreign system's causal graph onto the target system; "
        "preserve the causal chain, replace the embodiment; the analogy "
        "is DISCLOSED and can never become direct support",
        "the region where the system differs but the causal structure "
        "matches the failure (foreign-domain mechanisms)"),
    _operator(
        "GEOMETRIC_TRANSFORMATION",
        _contract_geometric_transformation,
        "transform the geometry embodying the mechanism (count, scale, "
        "topology, arrangement) while preserving the causal mechanism",
        "the geometric dimension of the mechanism space (structural "
        "embodiments)"),
    _operator(
        "BOUNDARY_CONDITION_CHANGE",
        _contract_boundary_condition_change,
        "relocate the mechanism to the problem's boundary regime; "
        "re-derive the intervention for the new regime",
        "the boundary-condition dimension of the mechanism space "
        "(regime relocation)"),
    _operator(
        "FAILURE_PATH_INVERSION",
        _contract_failure_path_inversion,
        "invert the documented failure pathway into the operating "
        "principle (anti-condition engineering or failure-mechanism "
        "reuse)",
        "the failure-pathway dimension of the mechanism space (negative "
        "knowledge as design material)"),
]
OPERATOR_IDS = tuple(op["operator_id"] for op in TRANSFORMATION_OPERATORS)


def apply_operator(op: Dict[str, Any],
                   structured_evidence: List[Dict[str, Any]],
                   problem: Dict[str, Any],
                   per_operator_item_cap: int = 2,
                   ) -> Dict[str, Any]:
    """Apply ONE operator over the structured evidence.

    Deterministic selection: which items satisfy the input contract is
    decided by the contract predicate alone. LLM instantiation: ONE call
    per (operator, selected item) with the operator's structured prompt.
    Validation: span-bound + testable-prediction checks (deterministic).
    Failure states: NO_APPLICABLE_EVIDENCE (no item satisfied the
    contract), OPERATOR_LLM_UNAVAILABLE, and per-candidate
    NOT_A_CANDIDATE states — all honest, all recorded."""
    selected = []
    for item in structured_evidence:
        contract = op["input_contract"](item, problem)
        if contract["satisfied"]:
            item["_selection"] = {"selected_by": op["operator_id"],
                                  "contract": contract}
            selected.append(item)
        else:
            item.setdefault("_selection_rejections", []).append(
                {"operator": op["operator_id"],
                 "contract": contract})
    result: Dict[str, Any] = {
        "operator": op["operator_id"],
        "operator_version": op["version"],
        "transformation_rule": op["transformation_rule"],
        "search_constraint": op["search_constraint"],
        "n_items_examined": len(structured_evidence),
        "n_items_selected": len(selected),
        "selected_item_ids": [i.get("item_id") for i in selected],
        "candidates": [],
    }
    if not selected:
        result["state"] = op["failure_state"]
        result["note"] = ("no structured evidence item satisfied the "
                          "input contract — honest refusal, nothing "
                          "fabricated (Art. XXV)")
        return result
    used = 0
    for item in selected:
        if used >= per_operator_item_cap:
            break
        used += 1
        prompt = _OPERATOR_INSTANTIATION_PROMPTS[op["operator_id"]].format(
            system=_field_val(item, "system") or "(unextracted)",
            mechanism=_field_val(item, "mechanism") or "(unextracted)",
            observed_effect=_field_val(item, "observed_effect")
            or "(unextracted)",
            evidence_intervention=_field_val(item, "intervention")
            or "(unextracted)",
            boundary_conditions=_field_val(item, "boundary_conditions")
            or "(unextracted)",
            constraints=_field_val(item, "constraints") or "(unextracted)",
            failure_mode=_field_val(item, "failure_mode")
            or "(unextracted)",
            device=problem.get("device", ""),
            failure=problem.get("failure", ""),
            constraint=problem.get("constraint", ""),
            record_text=_item_abstract(item)[:2600] or
            "(record text unavailable)")
        meta = llm_generate(
            prompt, system="You are a rigorous mechanism engineer. "
            "Every claim must derive from the given evidence.",
            purpose=f"operator_{op['operator_id']}")
        if not meta.get("ok"):
            result["candidates"].append({
                "state": "OPERATOR_INSTANTIATION_FAILED",
                "item_id": item.get("item_id"),
                "llm_status": meta.get("status"),
                "llm_error": (meta.get("error") or "")[:200]})
            continue
        # R401 RECORDED CORRECTIVE RETRY (the standing E15 discipline:
        # same provider, defect-specific correction, one retry, fully
        # recorded in the derivation trace — Art. VII fix-the-claim
        # side; the span/semantic gates themselves never move): if the
        # first instantiation fails the SPAN binding or the operator's
        # REQUIRED semantic change, one retry tells the model the exact
        # defect and how to correct it.
        _first_fields = _parse_candidate_fields(meta["content"] or "")
        _first_span = str(_first_fields.get("mechanism_source_span")
                          or "").strip().strip("\"'").strip()
        _first_ok_span = _first_span and (
            _first_span in _item_abstract(item)
            or re.sub(r"\s+", " ", _first_span).lower() in re.sub(
                r"\s+", " ", _item_abstract(item)).lower())
        _pre_cand = assemble_candidate(op, item, _first_fields, problem,
                                       meta)
        _pre_sem = operator_semantic_check(op["operator_id"], item,
                                           _pre_cand, problem)
        retry_note = None
        if not _first_ok_span or _pre_sem["semantic_verdict"] != \
                "SEMANTICALLY_VALID":
            defects = []
            if not _first_ok_span:
                defects.append(
                    "your MECHANISM_SOURCE_SPAN was not a verbatim "
                    "substring of RECORD TEXT — copy it EXACTLY from "
                    "RECORD TEXT")
            if _pre_sem["semantic_verdict"] == "TEXTUAL_REWRITE":
                defects.append(
                    "your output was a textual rewrite of the source: "
                    + _pre_sem["required_change_basis"])
            elif _pre_sem["semantic_verdict"] == \
                    "SEMANTIC_INVARIANT_BROKEN":
                defects.append(
                    "your output lost the source mechanism: "
                    + _pre_sem["invariant_basis"])
            retry_note = (
                "recorded corrective retry (same provider/model, one "
                "attempt): " + "; ".join(defects)[:400])
            meta2 = llm_generate(
                prompt + "\n\nCORRECT YOUR PREVIOUS ATTEMPT — it "
                "failed validation: " + "; ".join(defects)[:400],
                system="You are a rigorous mechanism engineer. Every "
                       "claim must derive from the given evidence. Fix "
                       "the stated defects exactly.",
                purpose=f"operator_{op['operator_id']}_retry")
            if meta2.get("ok"):
                _fields2 = _parse_candidate_fields(
                    meta2["content"] or "")
                _improved = (
                    str(_fields2.get("mechanism_source_span") or "")
                    .strip().strip("\"'").strip())
                _ok2 = _improved and (
                    _improved in _item_abstract(item)
                    or re.sub(r"\s+", " ", _improved).lower() in re.sub(
                        r"\s+", " ", _item_abstract(item)).lower())
                _cand2 = assemble_candidate(op, item, _fields2, problem,
                                            meta2)
                _sem2 = operator_semantic_check(op["operator_id"], item,
                                                _cand2, problem)
                if _ok2 and _sem2["semantic_verdict"] == \
                        "SEMANTICALLY_VALID":
                    meta, cand_fields = meta2, _fields2
                    result.setdefault("_recorded_retries", []).append({
                        "item_id": item.get("item_id"),
                        "operator": op["operator_id"],
                        "defects": defects,
                        "outcome": "RETRY_ADMITTED"})
        cand_fields = _parse_candidate_fields(meta["content"] or "")
        # Art. II span binding — ONE authority, the a2/verify.py
        # contract: verbatim (quote-stripped) in the record text, with
        # case-insensitive/whitespace-normalized fallback (the SAME
        # ladder the discovery loop's span verification uses; not a
        # new weaker rule). A span that fails both modes is rejected —
        # the model reworded or fabricated it.
        span = cand_fields.get("mechanism_source_span", "")
        record_text = _item_abstract(item)
        span_clean = span.strip().strip('"\'').strip()
        _norm = lambda s: re.sub(r"\s+", " ", s).lower().strip()  # noqa: E731
        span_mode = None
        if span_clean and span_clean in record_text:
            span_mode = "VERBATIM"
        elif span_clean and _norm(span_clean) in _norm(record_text):
            span_mode = "CASE_INSENSITIVE_NORMALIZED"
        span_ok = span_mode is not None
        cand = assemble_candidate(op, item, cand_fields, problem, meta)
        # R401B B4: the operator's OWN semantics are enforced on the
        # live path — invariant preserved + required structural change
        # present. A textual rewrite of the source is not a distinct
        # candidate; a broken invariant lost the mechanism entirely.
        semantic = operator_semantic_check(
            op["operator_id"], item, cand, problem)
        cand["operator_semantics"] = semantic
        if semantic["semantic_verdict"] == "TEXTUAL_REWRITE":
            cand["candidate_state"] = "NOT_A_CANDIDATE_TEXTUAL_REWRITE"
        elif semantic["semantic_verdict"] == "SEMANTIC_INVARIANT_BROKEN":
            cand["candidate_state"] = \
                "NOT_A_CANDIDATE_OPERATOR_INVARIANT_BROKEN"
        cand["span_binding"] = {
            "mechanism_source_span": span[:300],
            "verbatim_in_record": span_ok,
            "match_mode": span_mode,
            "contract": ("a2/verify.py ladder: verbatim -> case-"
                         "insensitive normalized; anything else is a "
                         "reworded/fabricated span and is rejected"),
        }
        if not span_ok:
            cand["candidate_state"] = (
                "NOT_A_CANDIDATE_SPAN_NOT_VERBATIM")
        result["candidates"].append(cand)
    n_valid = sum(1 for c in result["candidates"]
                  if c.get("candidate_state") == "CANDIDATE")
    result["state"] = ("OPERATOR_RUN" if n_valid else
                       "OPERATOR_NO_VALID_CANDIDATE")
    result["n_valid_candidates"] = n_valid
    return result


def _item_abstract(item: Dict[str, Any]) -> str:
    # the structured item keeps the record text through its source block
    # (title) + the extraction input; the abstract is recovered from the
    # ORIGINAL evidence item the space was built from — carried in
    # _record_text by build_structured_evidence
    return str(item.get("_record_text") or "")


_CANDIDATE_FIELD_LINE_RE = re.compile(
    r"^(MECHANISM|INTERVENTION|PREDICTED_EFFECT|NOVEL_DESIGN_VARIABLE|"
    r"TESTABLE_PREDICTION|KNOWN_FAILURE_MODES|BOUNDARY_CONDITIONS|"
    r"MECHANISM_SOURCE_SPAN)\s*:\s*(.*)$", re.MULTILINE)


def _parse_candidate_fields(text: str) -> Dict[str, str]:
    parsed = {f.lower(): "" for f in (
        "mechanism", "intervention", "predicted_effect",
        "novel_design_variable", "testable_prediction",
        "known_failure_modes", "boundary_conditions",
        "mechanism_source_span")}
    for m in _CANDIDATE_FIELD_LINE_RE.finditer(text or ""):
        parsed[m.group(1).lower()] = m.group(2).strip()
    return parsed


# ---------------------------------------------------------------------------
# 7. Machine-checkable distinctness (R402 instrument v2 — Art. XLII)
#
# Deterministic comparison over SIX structural dimensions:
#   mechanism_graph, intervention, boundary conditions, failure mode,
#   design variable, predicted effect. Wording is normalized away
#   (term sets, stopwords removed): two candidates differing only in
#   wording must NOT count as distinct.
#
# R402 (audit CB-1, Art. XLII — Mechanism Distinctness Independence):
#   the v1 rule let FREE-TEXT envelope differences (a renamed design
#   knob, a reworded boundary condition) BLOCK the merge of candidates
#   whose causal core was IDENTICAL (graph Jaccard 1.0) — the audit's
#   probes A/B/C measured it: renamed-knob / synonym / added-
#   specificity variants were all kept as GENUINE_MECHANISM_DIFFERENCE.
#   That inverted the Article XLII burden: vocabulary variation in
#   envelope fields was ALLOWED TO CREATE mechanisms.
#
# v2 decision rule (three verdicts, never a forced binary):
#   DISTINCT      causal core materially different (aggregate graph
#                 Jaccard < CAUSAL_CORE_DISTINCT_FLOOR) — different
#                 causal variables / different physics vocabulary.
#   EQUIVALENT    causal core equivalent (>= CAUSAL_CORE_MERGE_JACCARD)
#                 AND at most a design-knob difference: a knob rename /
#                 parameter rename / synonym change CANNOT independently
#                 create a new invention (Art. XLII forbidden list) —
#                 the candidates are the same mechanism family (merged,
#                 the knob delta recorded).
#   INDETERMINATE (a) causal core equivalent but a boundary-regime or
#                 failure-mode delta exists — a boundary-regime change
#                 IS a legitimate distinctness dimension, and a
#                 deterministic term instrument cannot classify regime
#                 change vs rewording; or (b) the causal core sits in
#                 the ambiguous band. INDETERMINATE candidates are kept
#                 in the pipeline (they are hypotheses pending
#                 independent distinctness adjudication) but are NOT
#                 counted by the material-diversity metric (Art. XXV:
#                 the instrument's inability to prove difference is
#                 not proof of difference).
#
#   Threshold provenance (Art. XXVII, MODEL_DERIVED, declared): the
#   bars are calibrated on the repo's own adversarial fixtures —
#   true-duplicate pair (REWORDED_DUPLICATE vs GOOD in
#   tests/test_r401_mechanism_space.py) measures aggregate graph
#   Jaccard 0.8; true-distinct pair (electrostatic vs heparin) measures
#   0.167. CAUSAL_CORE_MERGE_JACCARD = 0.8 (the measured duplicate
#   score, unchanged from v1); CAUSAL_CORE_DISTINCT_FLOOR = 0.45 sits
#   in the wide empty band between 0.167 and 0.8 with margin on both
#   sides. NOT fitted to any output count.
# ---------------------------------------------------------------------------
DISTINCTNESS_INSTRUMENT_VERSION = "mechanism_distinctness/2.0.0"
DISTINCTNESS_VERDICTS = ("DISTINCT", "EQUIVALENT", "INDETERMINATE")
DISTINCTNESS_DIMENSIONS = (
    "mechanism_graph", "intervention", "boundary_conditions",
    "failure_mode", "design_variable", "predicted_effect")
NEAR_DUPLICATE_JACCARD = 0.8            # causal-core merge bar (v1 name kept)
CAUSAL_CORE_MERGE_JACCARD = 0.8         # same value, v2 name (see above)
CAUSAL_CORE_DISTINCT_FLOOR = 0.45       # below = materially different core


def _dimension_terms(candidate: Dict[str, Any], dim: str) -> set:
    if dim == "mechanism_graph":
        g = candidate.get("mechanism_graph") or {}
        node_terms: set = set()
        for n in (g.get("nodes") or {}).values():
            node_terms.update(n.get("terms") or [])
        edge_sig = {f"{e.get('from')}>{e.get('relation')}>"
                    f"{e.get('to')}" for e in g.get("edges") or []}
        return node_terms | edge_sig
    if dim == "intervention":
        return _terms(candidate.get("intervention", ""))
    if dim == "boundary_conditions":
        return _terms(
            (candidate.get("constraint_set") or {}).get(
                "boundary_conditions", ""))
    if dim == "failure_mode":
        return _terms(" ".join(
            candidate.get("known_failure_modes") or []))
    if dim == "design_variable":
        return _terms(candidate.get("novel_design_variable", ""))
    if dim == "predicted_effect":
        return _terms(candidate.get("predicted_effect", ""))
    return set()


def _jaccard(a: set, b: set) -> Optional[float]:
    if not a and not b:
        return None  # both empty — dimension uninformative
    u = a | b
    return round(len(a & b) / len(u), 3) if u else None


def _role_jaccards(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Role-respecting per-node comparison (Art. XLII's representation
    list: causal structure / physical effect / intervention roles are
    compared like-for-like, not as one aggregate bag). Recorded as the
    adjudicator's structural view; the verdict itself uses the
    aggregate core (the calibrated instrument — see thresholds)."""
    out: Dict[str, Any] = {}
    ga = a.get("mechanism_graph") or {}
    gb = b.get("mechanism_graph") or {}
    roles = sorted(set(ga.get("nodes") or {}) | set(gb.get("nodes") or {}))
    for role in roles:
        ta = set((ga.get("nodes") or {}).get(role, {}).get("terms") or [])
        tb = set((gb.get("nodes") or {}).get(role, {}).get("terms") or [])
        j = _jaccard(ta, tb)
        out[role] = {"jaccard": j,
                     "equivalent": True if j is None else
                     j >= CAUSAL_CORE_MERGE_JACCARD}
    edges_a = {f"{e.get('from')}>{e.get('relation')}>{e.get('to')}"
               for e in ga.get("edges") or []}
    edges_b = {f"{e.get('from')}>{e.get('relation')}>{e.get('to')}"
               for e in gb.get("edges") or []}
    out["edge_signatures"] = {
        "a": sorted(edges_a), "b": sorted(edges_b),
        "identical": edges_a == edges_b}
    return out


def compare_candidates(a: Dict[str, Any], b: Dict[str, Any]
                       ) -> Dict[str, Any]:
    """Pairwise structural comparison with the full recorded basis.

    v2 verdict rule (deterministic, recorded): the MECHANISM GRAPH
    aggregate (node term sets + edge signatures) is the machine-
    checkable causal core. Two candidates are EQUIVALENT when the core
    is term-equivalent AND the only residual differences are wording
    class (including design-knob renames — Art. XLII: a knob rename
    cannot independently create an invention). They are DISTINCT when
    the causal core itself is materially different. Everything the
    instrument cannot classify (boundary-regime / failure-mode deltas
    on an identical core; cores in the ambiguous band) is INDETERMINATE
    — kept visible, referred to independent adjudication, never
    counted as distinct."""
    dims = {}
    for d in DISTINCTNESS_DIMENSIONS:
        j = _jaccard(_dimension_terms(a, d), _dimension_terms(b, d))
        if j is None:
            dims[d] = {"jaccard": None, "equivalent": True,
                       "note": "both dimensions empty — uninformative"}
        else:
            dims[d] = {"jaccard": j,
                       "equivalent": j >= CAUSAL_CORE_MERGE_JACCARD}
    core_j = dims["mechanism_graph"]["jaccard"]
    knob = dims["design_variable"]
    regime = dims["boundary_conditions"]
    failure = dims["failure_mode"]

    def _differs(d: Dict[str, Any]) -> bool:
        return d["jaccard"] is not None and not d["equivalent"]

    if core_j is None:
        verdict = "INDETERMINATE"
        basis = ("both causal cores empty — nothing to compare; unknown "
                 "stays unknown (Art. XXV)")
    elif core_j < CAUSAL_CORE_DISTINCT_FLOOR:
        verdict = "DISTINCT"
        basis = (f"causal core materially different (aggregate graph "
                 f"Jaccard {core_j} < {CAUSAL_CORE_DISTINCT_FLOOR}): the "
                 "intervention/mechanism/effect vocabulary itself differs "
                 "— different causal variables, not different wording")
    elif core_j >= CAUSAL_CORE_MERGE_JACCARD:
        # causal core equivalent — envelope fields may NOT create
        # distinctness (Art. XLII). Classify the residual delta.
        if _differs(regime) or _differs(failure):
            verdict = "INDETERMINATE"
            which = [d for d in ("boundary_conditions", "failure_mode")
                     if _differs(dims[d])]
            basis = (f"causal core equivalent (Jaccard {core_j}) but "
                     f"{', '.join(which)} differs materially — a "
                     "boundary-regime / failure-mode change is a "
                     "legitimate distinctness dimension that a "
                     "deterministic term instrument cannot classify "
                     "against rewording; referred to independent "
                     "distinctness adjudication; NOT counted as a "
                     "materially distinct mechanism (Art. XLII/XXV)")
        elif _differs(knob):
            verdict = "EQUIVALENT"
            basis = (f"causal core equivalent (Jaccard {core_j}) and only "
                     "the design variable differs — design-knob renaming "
                     "cannot independently create a new invention "
                     "(Art. XLII forbidden list); same mechanism family, "
                     "knob delta recorded")
        else:
            verdict = "EQUIVALENT"
            basis = (f"causal core equivalent (Jaccard {core_j}) and all "
                     "envelope dimensions equivalent — the candidates "
                     "differ only in wording")
    else:
        verdict = "INDETERMINATE"
        basis = (f"causal core in the ambiguous band "
                 f"({CAUSAL_CORE_DISTINCT_FLOOR} <= Jaccard {core_j} < "
                 f"{CAUSAL_CORE_MERGE_JACCARD}) — the instrument cannot "
                 "classify rewording vs different causal variables; "
                 "referred to independent distinctness adjudication; "
                 "NOT counted as a materially distinct mechanism")

    differing = [d for d in dims
                 if dims[d]["jaccard"] is not None
                 and not dims[d]["equivalent"]]
    return {"verdict": verdict,
            "near_duplicate": verdict == "EQUIVALENT",  # v1 alias
            "mechanism_core_equivalent": bool(
                core_j is not None and
                core_j >= CAUSAL_CORE_MERGE_JACCARD),
            "causal_core_jaccard": core_j,
            "dimensions": dims,
            "role_comparison": _role_jaccards(a, b),
            "differing_dimensions": differing,
            "n_dimensions_equivalent": sum(
                1 for d in dims
                if dims[d]["jaccard"] is not None and dims[d]["equivalent"]),
            "n_dimensions_informative": sum(
                1 for d in dims if dims[d]["jaccard"] is not None),
            "basis": basis,
            "instrument_version": DISTINCTNESS_INSTRUMENT_VERSION,
            "decision_rule": (
                f"v2 three-verdict rule: DISTINCT iff aggregate graph "
                f"Jaccard < {CAUSAL_CORE_DISTINCT_FLOOR}; EQUIVALENT iff "
                f">= {CAUSAL_CORE_MERGE_JACCARD} and at most a "
                "design-knob difference (knob rename cannot create an "
                "invention, Art. XLII); INDETERMINATE for boundary/"
                "failure deltas on an equivalent core or cores in the "
                "ambiguous band — never counted as distinct")}


def deduplicate_candidates(candidates: List[Dict[str, Any]]
                           ) -> Dict[str, Any]:
    """Collapse EQUIVALENT candidates (recording WHY); retain DISTINCT
    and INDETERMINATE candidates (recording the verdict basis); every
    retained candidate carries its distinctness_verdict for downstream
    consumers and the diversity metric counts DISTINCT only (Art.
    XLVIII). Deterministic order: first occurrence (by operator order
    then item order) wins."""
    kept: List[Dict[str, Any]] = []
    dedup_events: List[Dict[str, Any]] = []
    retain_events: List[Dict[str, Any]] = []
    seen_hashes: set = set()
    n_distinct = n_indeterminate = n_equivalent = 0
    for c in candidates:
        if c.get("candidate_state") != "CANDIDATE":
            continue
        h = c.get("candidate_hash")
        if h in seen_hashes:
            dedup_events.append({
                "kept_id": None, "dropped_id": c.get("candidate_id"),
                "reason": "IDENTICAL_HASH (byte-identical candidate)",
                "dimensions": None})
            n_equivalent += 1
            continue
        merged = None
        for k in kept:
            cmp = compare_candidates(k, c)
            if cmp["verdict"] == "EQUIVALENT":
                merged = (k, cmp)
                break
        if merged:
            k, cmp = merged
            n_equivalent += 1
            c["distinctness_verdict"] = "EQUIVALENT"
            c["distinctness_basis"] = cmp["basis"]
            dedup_events.append({
                "kept_id": k.get("candidate_id"),
                "dropped_id": c.get("candidate_id"),
                "verdict": "EQUIVALENT",
                "reason": ("NEAR_DUPLICATE: mechanism core equivalent "
                           f"(graph Jaccard >= {NEAR_DUPLICATE_JACCARD}) "
                           "and the candidates differ only in wording "
                           "(or a design-knob rename, which cannot create "
                           "an invention — Art. XLII)"),
                "comparison": cmp})
        else:
            # no EQUIVALENT twin: retain. Label against the nearest
            # kept candidate — the recorded verdict basis.
            if kept:
                best = max(
                    (compare_candidates(k, c) for k in kept),
                    key=lambda cmp: (
                        cmp["causal_core_jaccard"]
                        if cmp["causal_core_jaccard"] is not None
                        else -1.0))
                verdict = best["verdict"]
                if verdict == "INDETERMINATE":
                    basis = best["basis"]
                else:
                    basis = best["basis"]
                event_basis = {
                    "nearest_kept": None,
                    "verdict": verdict,
                    "differing_dimensions": best["differing_dimensions"],
                    "causal_core_jaccard": best["causal_core_jaccard"],
                    "comparison": best}
            else:
                verdict = "DISTINCT"
                basis = ("first candidate — the first mechanism family "
                         "in this space; no prior family to compare")
                event_basis = {
                    "nearest_kept": None,
                    "verdict": "DISTINCT",
                    "differing_dimensions": None,
                    "causal_core_jaccard": None,
                    "comparison": None,
                    "note": "first family — baseline of the space"}
            c["distinctness_verdict"] = verdict
            c["distinctness_basis"] = basis
            if verdict == "DISTINCT":
                n_distinct += 1
                reason = ("GENUINE_MECHANISM_DIFFERENCE: the causal core "
                          "is materially different (recorded)")
            else:
                n_indeterminate += 1
                reason = ("INDETERMINATE_DISTINCTNESS: retained as a "
                          "hypothesis pending independent distinctness "
                          "adjudication; NOT counted as a materially "
                          "distinct mechanism (Art. XLII/XXV)")
            retain_events.append({
                "retained_id": c.get("candidate_id"),
                "verdict": verdict,
                "reason": reason,
                "difference_basis": event_basis})
            kept.append(c)
            seen_hashes.add(h)
    return {
        "n_input": len(candidates),
        "n_kept": len(kept),
        "kept_ids": [c.get("candidate_id") for c in kept],
        "n_distinct": n_distinct,
        "n_indeterminate": n_indeterminate,
        "n_equivalent_merged": n_equivalent,
        "distinctness_verdicts": {
            "DISTINCT": n_distinct,
            "INDETERMINATE": n_indeterminate,
            "EQUIVALENT": n_equivalent},
        "instrument_version": DISTINCTNESS_INSTRUMENT_VERSION,
        "dedup_events": dedup_events,
        "retain_events": retain_events,
        "distinctness_rule": (
            "v2 three-verdict rule (Art. XLII): the mechanism graph "
            "aggregate (node term sets + edge signatures) is the causal "
            f"core; DISTINCT iff its Jaccard < "
            f"{CAUSAL_CORE_DISTINCT_FLOOR}; EQUIVALENT (merge) iff >= "
            f"{NEAR_DUPLICATE_JACCARD} "
            "with at most a design-knob difference (knob/parameter/"
            "synonym renames cannot independently create an invention); "
            "INDETERMINATE for boundary-regime or failure-mode deltas on "
            "an equivalent core, or cores in the ambiguous band — kept "
            "visible, never counted as distinct; every verdict records "
            "its basis"),
    }


# ---------------------------------------------------------------------------
# 8. Mechanism-level evidence verification (R401 Phase 4)
#
# The question: does the evidence support the MECHANISM this candidate
# asserts? Relations:
#   SUPPORTS             same-system, mechanism-vocabulary overlap >= 2,
#                        the item's OWN extracted mechanism aligns
#   PARTIALLY_SUPPORTS   mechanism overlap >= 2 but cross-system (an
#                        analogy — NEVER direct support), or partial
#                        mechanism overlap with same system
#   CONTRADICTS          negation-proximity co-located with the
#                        candidate's mechanism terms (stays VISIBLE,
#                        never absorbed)
#   NOT_ENOUGH_EVIDENCE  phenomenon/domain overlap WITHOUT mechanism
#                        vocabulary (phenomenon support is NOT mechanism
#                        support — never converted to weak support)
#   IRRELEVANT           no meaningful overlap on any axis
# ---------------------------------------------------------------------------
VERIFY_RELATIONS = ("SUPPORTS", "PARTIALLY_SUPPORTS", "CONTRADICTS",
                    "IRRELEVANT", "NOT_ENOUGH_EVIDENCE")
MIN_MECHANISM_OVERLAP = 2   # the engine's standing bar (one rule family)

_NEGATION_MARKERS = (
    "did not", "does not", "no effect", "not associated", "failed to",
    "without improvement", "no improvement", "no significant",
    "contradicts", "inconsistent with", "refutes", "no difference",
    "not effective", "ineffective", "worsened", "no reduction",
)


def _sentence_split(text: str) -> List[str]:
    return re.split(r"(?<=[.!?])\s+", str(text or ""))


def verify_item_against_candidate(candidate: Dict[str, Any],
                                  item: Dict[str, Any],
                                  problem: Dict[str, Any]
                                  ) -> Dict[str, Any]:
    """Adjudicate ONE structured evidence item against ONE candidate's
    asserted mechanism. Deterministic; every verdict carries its basis."""
    cand_mech_terms = _dimension_terms(candidate, "mechanism_graph")
    cand_mech_terms |= _terms(candidate.get("mechanism", ""))
    f = {k: _field_val(item, k) for k in
         ("system", "mechanism", "observed_effect", "failure_mode")}
    item_mech_terms = _terms(f["mechanism"]) | _terms(f["observed_effect"])
    problem_terms = _terms(
        str(problem.get("device") or "") + " " +
        str(problem.get("failure") or ""))
    item_system_terms = _terms(f["system"])

    mech_overlap = sorted(cand_mech_terms & item_mech_terms)
    system_match = len(problem_terms & item_system_terms) >= 1 and (
        len(_terms(str(problem.get("device") or "")) &
            item_system_terms) >= 1)
    phenomenon_overlap = sorted(
        (_terms(f["observed_effect"]) | _terms(f["failure_mode"]))
        & problem_terms)
    domain_overlap = sorted(problem_terms & (
        item_system_terms | item_mech_terms))

    # CONTRADICTS: negation marker co-located with candidate mechanism
    # terms in the item's record text (the transparent proxy — a
    # disclosed heuristic, not a claim chart)
    record_text = str(item.get("_record_text") or "") + " " + \
        f["mechanism"] + " " + f["observed_effect"]
    contradicts, contradiction_basis = False, ""
    for sent in _sentence_split(record_text):
        low = sent.lower()
        if not any(m in low for m in _NEGATION_MARKERS):
            continue
        near = sorted(_terms(sent) & cand_mech_terms)
        if near:
            contradicts = True
            contradiction_basis = (
                f"negation marker co-located with candidate mechanism "
                f"terms {near} in: '{sent[:160]}'")
            break

    item_own_mechanism_valid = bool(
        ((item.get("fields") or {}).get("mechanism") or {}
         ).get("state") == "VALID")

    if contradicts:
        relation, basis = "CONTRADICTS", contradiction_basis
    elif (len(mech_overlap) >= MIN_MECHANISM_OVERLAP
          and system_match and item_own_mechanism_valid):
        relation = "SUPPORTS"
        basis = (f"same-system (device terms {sorted(
            _terms(str(problem.get('device') or '')) &
            item_system_terms)} present in the item's system field) + "
            f"{len(mech_overlap)} mechanism terms shared and the item's "
            f"own mechanism field is extracted-and-bound")
    elif len(mech_overlap) >= MIN_MECHANISM_OVERLAP:
        relation = "PARTIALLY_SUPPORTS"
        if system_match:
            basis = (f"mechanism overlap {len(mech_overlap)} terms but "
                     "the item's own mechanism field is not bound "
                     "(UNEXTRACTED/UNTRUSTED) — mechanism support is "
                     "inferred from vocabulary only, never direct")
        else:
            basis = (f"mechanism overlap {len(mech_overlap)} terms from "
                     "a DIFFERENT system — ANALOGY: the causal structure "
                     "may transfer, but analogy is never direct support "
                     f"(item system: {f['system'][:120]})")
    elif phenomenon_overlap or domain_overlap:
        relation = "NOT_ENOUGH_EVIDENCE"
        basis = ("phenomenon/domain overlap present "
                 f"({len(phenomenon_overlap or domain_overlap)} terms) "
                 "but the candidate's mechanism vocabulary is absent "
                 f"(overlap {len(mech_overlap)} < "
                 f"{MIN_MECHANISM_OVERLAP}) — phenomenon support is NOT "
                 "mechanism support (R401 Phase 4)")
    else:
        relation = "IRRELEVANT"
        basis = "no system, mechanism, phenomenon or domain overlap"

    return {
        "item_id": item.get("item_id"),
        "relation": relation,
        "basis": basis,
        "overlaps": {
            "mechanism_terms": mech_overlap[:12],
            "system_match": system_match,
            "phenomenon_terms": phenomenon_overlap[:12],
            "domain_terms": domain_overlap[:12],
        },
        "contradiction_basis": contradiction_basis or None,
    }


def verify_mechanism_support(candidate: Dict[str, Any],
                             structured_evidence: List[Dict[str, Any]],
                             problem: Dict[str, Any],
                             ) -> Dict[str, Any]:
    """Verify a candidate's asserted mechanism against the WHOLE
    structured bundle. Contradictions stay visible (CONTESTED state);
    NOT_ENOUGH_EVIDENCE is never converted into support."""
    verdicts = [verify_item_against_candidate(candidate, it, problem)
                for it in structured_evidence]
    counts = {r: 0 for r in VERIFY_RELATIONS}
    for v in verdicts:
        counts[v["relation"]] += 1
    contradictions = [v for v in verdicts
                      if v["relation"] == "CONTRADICTS"]
    supports = [v for v in verdicts if v["relation"] == "SUPPORTS"]
    partials = [v for v in verdicts
                if v["relation"] == "PARTIALLY_SUPPORTS"]
    if contradictions:
        state = "CONTESTED"
    elif supports:
        state = "SUPPORTED"
    elif partials:
        state = "PARTIALLY_SUPPORTED"
    else:
        state = "NOT_ENOUGH_EVIDENCE"
    return {
        "candidate_id": candidate.get("candidate_id"),
        "mechanism_support_state": state,
        "counts": counts,
        "n_items": len(verdicts),
        "verdicts": verdicts,
        "contradictions_visible": [
            {"item_id": c.get("item_id"),
             "basis": c.get("contradiction_basis") or c.get("basis")}
            for c in contradictions],
        "note": ("CONTESTED keeps contradictions VISIBLE alongside any "
                 "support (never absorbed); cross-system items cap at "
                 "PARTIALLY_SUPPORTS (analogy never becomes direct "
                 "support); phenomenon-only overlap is "
                 "NOT_ENOUGH_EVIDENCE (never weak support)"),
    }


# ---------------------------------------------------------------------------
# 9. The orchestrator: build the whole mechanism space for one problem
# ---------------------------------------------------------------------------
# R401 Phase 5 / B1: the mechanism space consumes MULTI-SOURCE evidence
# — the a2 primary plane (EuropePMC) PLUS a bounded expansion through
# the LIVE source-registry connectors (openalex + arxiv + nasa_ntrs:
# free, unmetered, REST). The expansion serves mechanism discovery
# ONLY: every query is recorded in the retrieval log (Art. XXI.9), a
# SEARCH_FAILED source is an honest state (Art. XXI.3 — never
# absence), and the mechanism-signal reranker selects the final set.
MULTI_SOURCE_EXPANSION_SOURCES = ("openalex", "arxiv", "nasa_ntrs")


def _record_to_item(rec: Any) -> Optional[Dict[str, Any]]:
    """A SourceRecord (registry custody) -> the evidence-item shape the
    extraction consumes. Provenance stays the registry's own custody
    chain (retrieval log + record provenance) — nothing re-derived."""
    n = rec.normalized or {}
    abstract = n.get("abstract") or n.get("summary") or ""
    if not abstract or len(str(abstract)) < 200:
        return None  # no usable record text — nothing to extract from
    return {
        "id": rec.record_id,
        "source": rec.source_id,
        "title": rec.title or "",
        "abstract": str(abstract)[:2400],
        "content_hash": rec.raw_payload_sha256 or "",
        "retrieval_timestamp": rec.retrieved_at,
        "source_uri": rec.uri,
        "provenance_record": rec.to_dict() if hasattr(
            rec, "to_dict") else {},
    }


def _evidence_version_record(state: str,
                             records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Art. XLIV — the evidence-version record a NEW retrieval must
    carry: its own snapshot id + hash (over the record content hashes /
    ids, deterministically ordered) and its own freeze event. Post-freeze
    retrieval creates a NEW epistemic version; it never merges silently
    into the frozen plane."""
    basis = sorted(
        str(r.get("content_hash") or r.get("id") or "")
        for r in records)
    snapshot_hash = sha256_obj({"basis": basis})
    snapshot_id = f"evsnap_{snapshot_hash[:16]}"
    return {
        "retrieval_role": "DISCOVERY_EXPANSION",
        "state": state,
        "evidence_snapshot_id": snapshot_id,
        "evidence_hash": snapshot_hash,
        "n_records": len(records),
        "record_ids": [r.get("id") for r in records][:50],
        "retrieved_at": utc_now(),
        "freeze_event": {
            "event": "NEW_FREEZE_PERFORMED",
            "rule": ("Art. XLIV: post-freeze retrieval -> NEW evidence "
                     "snapshot -> NEW freeze -> NEW epistemic version; "
                     "never a silent union with the frozen plane"),
        },
    }


def multi_source_expansion(problem: Dict[str, Any],
                           per_source: int = 3
                           ) -> Dict[str, Any]:
    """Query the expansion sources with problem-derived keyword queries
    (deterministic; two queries: domain terms + failure-mechanism terms).

    R402 v2 (audit CB-2, Art. XLIII — Search-Space Neutrality): the v1
    mechanism query hardcoded an unproven solution class —
    `keyword_form(f"{failure} prevention coating flow")` — injecting
    'coating/flow' into EVERY domain's search space (the audit measured
    it across 8 domains: thermal runaway, DC arc fault, rag clogging,
    aseptic loosening, humidity drift, surface pickup, blade erosion,
    catheter obstruction — all queried for coatings). The v2 mechanism
    query derives from the problem's OWN vocabulary: the failure
    description + the stated constraint (the unmet need the mechanism
    must serve). Every query records its derivation class; no term may
    enter a query unless it came from problem facts, frozen evidence,
    or is an explicitly marked EXPLORATORY_HYPOTHESIS.

    R402 v2 (audit CB-3, Art. XLIV — Evidence Boundary): the expansion
    is POST-FREEZE retrieval and is now versioned as such — it returns
    its own evidence snapshot (id + hash over the retrieved records'
    custody chains) and its own freeze event, so the generation plane
    is never a silent union with the frozen plane (see
    build_structured_evidence)."""
    from discovery_fabric.source_registry.query_relevance import \
        keyword_form
    device = str(problem.get("device") or "")
    failure = str(problem.get("failure_mode") or
                  problem.get("failure") or "")
    constraint = str(problem.get("constraint") or "")
    q_domain = keyword_form(f"{device} {failure}")
    # NOTE: the meta-word "mechanism" is deliberately ABSENT — the
    # measured collision (arxiv "Synthesis of Mechanism ... Differential
    # Evolution" — linkage machinery, not causal mechanism) taught it;
    # failure + intervention vocabulary is the content
    #
    # v2: failure DESCRIPTION + CONSTRAINT vocabulary (problem facts),
    # NOT a hardcoded solution class (Art. XLIII)
    q_mechanism = keyword_form(f"{failure} {constraint}") or q_domain
    out: Dict[str, Any] = {
        "expansion_version": "multi_source_expansion/2.0.0",
        "queries": {
            "domain": {
                "text": q_domain,
                "derivation": "DERIVED_FROM_PROBLEM_FACTS",
                "term_sources": {"device": device,
                                 "failure_mode": failure}},
            "mechanism": {
                "text": q_mechanism,
                "derivation": "DERIVED_FROM_PROBLEM_FACTS",
                "term_sources": {"failure_mode": failure,
                                 "constraint": constraint}}},
        "sources": {}, "records": [],
        "search_space_neutrality": {
            "solution_class_injection": "NONE",
            "rule": ("Art. XLIII: no solution-class term may enter a "
                     "query unless derived from problem facts / frozen "
                     "evidence, or explicitly marked "
                     "EXPLORATORY_HYPOTHESIS — the v1 hardcoded "
                     "'prevention coating flow' class is removed"),
        },
    }
    import importlib
    import os as _os
    if _os.environ.get("R401_NO_EXPANSION"):
        # recorded OFF switch (tests / hermetic runs): the primary a2
        # plane alone; never silent — the state says so
        out["state"] = "DISABLED_BY_ENV (R401_NO_EXPANSION)"
        out["n_records"] = 0
        out["evidence_version"] = _evidence_version_record(
            "DISABLED_BY_ENV", [])
        return out
    _SRC_CLASSES = {
        "openalex": ("discovery_fabric.source_registry.connectors."
                     "scientific", "OpenAlexConnector"),
        "arxiv": ("discovery_fabric.source_registry.connectors."
                  "scientific", "ArxivConnector"),
        "nasa_ntrs": ("discovery_fabric.source_registry.connectors."
                      "govtech_reports", "NasaNtrsConnector"),
    }
    for src in MULTI_SOURCE_EXPANSION_SOURCES:
        spec_ = _SRC_CLASSES.get(src)
        if not spec_:
            out["sources"][src] = {"state": "CONNECTOR_UNKNOWN"}
            continue
        mod = importlib.import_module(spec_[0])
        cls = getattr(mod, spec_[1], None)
        if cls is None:
            out["sources"][src] = {"state": "CONNECTOR_UNKNOWN"}
            continue
        try:
            connector = cls()
            results = []
            for q in (q_domain, q_mechanism):
                r = connector.search(q, timeout=25,
                                     retrieval_role="DISCOVERY")
                entry = {"query": q, "status": r.status,
                         "n_records": len(r.records)}
                if r.error:
                    entry["error"] = str(r.error)[:160]
                results.append((r, entry))
            recs = []
            states = []
            for r, entry in results:
                states.append(entry)
                for rec in r.records:
                    item = _record_to_item(rec)
                    if item:
                        item["source"] = src
                        recs.append(item)
            out["sources"][src] = {
                "state": ("SEARCH_OK" if recs else
                          "NO_USABLE_RECORDS" if any(
                              e["status"] == "OK" for _, e in results)
                          else results[0][1].get("status", "UNKNOWN")),
                "queries": states,
                "n_usable": len(recs)}
            out["records"].extend(recs[:per_source * 2])
        except Exception as exc:  # noqa: BLE001 — honest state, never absence
            out["sources"][src] = {
                "state": "SEARCH_FAILED",
                "error": f"{type(exc).__name__}: {exc}"[:200]}
    out["n_records"] = len(out["records"])
    # Art. XLIV (audit CB-3): post-freeze retrieval carries its own
    # evidence snapshot + freeze event — a NEW epistemic version, never
    # a silent merge into the frozen plane
    out["evidence_version"] = _evidence_version_record(
        out.get("state", "SEARCH_EXECUTED"), out["records"])
    out["note"] = ("expansion evidence rides the registry's own "
                   "retrieval-log custody (Art. XXI.9); SEARCH_FAILED "
                   "and NO_USABLE_RECORDS are recorded states, never "
                   "absence (Art. XXI.3); the expansion is POST-FREEZE "
                   "retrieval and creates its own evidence snapshot + "
                   "freeze + epistemic version (Art. XLIV)")
    return out


def build_structured_evidence(problem: Dict[str, Any],
                              evidence: List[Dict[str, Any]],
                              top_k: int = 6,
                              ) -> Dict[str, Any]:
    """Multi-source custodied evidence -> structured mechanism-space
    data. Rerank (Phase 5) selects the mechanism-signal-dense records;
    each selected record is extracted + validated. Every step recorded.
    No evidence -> honest refusal (Art. XXV).

    R402 v2 (audit CB-3, Art. XLIV — Evidence Boundary): the FROZEN
    plane (the evidence this stage received — already frozen upstream
    by the FREEZE stage) and the EXPANSION plane (post-freeze
    retrieval) are kept as separately-hashed evidence generations.
    The union the reranker consumes is EXPLICIT and recorded: plane
    membership, snapshot ids and hashes travel on every structured
    item and on every candidate's evidence bundle — never a silent
    merge (the v1 `list(evidence) + expansion["records"]` union was
    the audit's B-1/CB-3 finding)."""
    if not evidence:
        return {
            "structured_evidence_version": MECHANISM_SPACE_VERSION,
            "state": "NO_EVIDENCE",
            "n_items": 0, "items": [],
            "note": "no custodied evidence on the envelope — no "
                    "structured mechanism space was built and none was "
                    "fabricated (Art. XXV)"}
    # the frozen plane's own snapshot (hash over the envelope's
    # evidence content hashes — the freeze this stage INHERITED)
    frozen_basis = sorted(
        str(it.get("content_hash") or it.get("id") or "")
        for it in evidence)
    frozen_hash = sha256_obj({"frozen_basis": frozen_basis})
    frozen_snapshot_id = f"evsnap_{frozen_hash[:16]}"
    # the bounded multi-source expansion (R401 Phase 5/B1) — the
    # primary a2 plane stays authoritative; the expansion ADDS
    # cross-domain mechanism material for the operators, and (v2)
    # carries its OWN evidence version + freeze event (Art. XLIV)
    expansion = multi_source_expansion(problem)
    exp_version = expansion.get("evidence_version") or {}
    # EXPLICIT two-plane union (never silent): stamp plane membership
    # on every record before the rerank sees the combined list
    frozen_stamped = []
    for it in evidence:
        it = dict(it)
        it["_evidence_plane"] = "FROZEN_PRIMARY"
        it["_evidence_snapshot_id"] = frozen_snapshot_id
        it["_evidence_hash"] = frozen_hash
        it["_retrieval_role"] = "FROZEN_PRIMARY"
        frozen_stamped.append(it)
    expansion_stamped = []
    for it in expansion["records"]:
        it = dict(it)
        it["_evidence_plane"] = "DISCOVERY_EXPANSION"
        it["_evidence_snapshot_id"] = exp_version.get(
            "evidence_snapshot_id", "")
        it["_evidence_hash"] = exp_version.get("evidence_hash", "")
        it["_retrieval_role"] = "DISCOVERY_EXPANSION"
        expansion_stamped.append(it)
    combined = frozen_stamped + expansion_stamped
    rerank = mechanism_signal_rerank(combined, top_k=top_k)
    selected = [combined[i] for i in rerank["selected_indexes"]]
    items = []
    for rec in selected:
        structured = extract_structured_evidence_item(rec, problem)
        # carry the record text for span validation + verification
        structured["_record_text"] = " ".join(
            str(rec.get(k) or "") for k in ("title", "abstract",
                                            "snippet"))
        # Art. XLIV: the plane / snapshot / role travel on the
        # structured item into every candidate's evidence bundle
        structured["_evidence_plane"] = rec.get("_evidence_plane", "")
        structured["_evidence_snapshot_id"] = rec.get(
            "_evidence_snapshot_id", "")
        structured["_evidence_hash"] = rec.get("_evidence_hash", "")
        structured["_retrieval_role"] = rec.get("_retrieval_role", "")
        structured["_retrieval_sources"] = rec.get("source", "")
        structured["_retrieval_timestamp"] = rec.get(
            "retrieval_timestamp", "")
        items.append(structured)
    n_mech = sum(1 for it in items
                 if it["extraction_summary"]["mechanism_extracted"])
    return {
        "structured_evidence_version": MECHANISM_SPACE_VERSION,
        "state": "BUILT",
        "n_items": len(items),
        "items": items,
        "rerank": rerank,
        "multi_source_expansion": expansion,
        "n_items_with_bound_mechanism": n_mech,
        "evidence_boundary": {
            "rule": ("Art. XLIV: frozen plane and post-freeze "
                     "expansion plane are separately-hashed evidence "
                     "generations; the union is explicit and plane "
                     "membership travels on every item (never a "
                     "silent merge)"),
            "frozen_plane": {
                "retrieval_role": "FROZEN_PRIMARY",
                "evidence_snapshot_id": frozen_snapshot_id,
                "evidence_hash": frozen_hash,
                "n_items": len(evidence)},
            "expansion_plane": exp_version,
            "planes_disjoint": True,
        },
    }


def _consult_cemetery(candidates: List[Dict[str, Any]]
                      ) -> Dict[str, Any]:
    """Art. LI (audit CB-5) — the mechanism space CONSUMES the cemetery.

    For every CANDIDATE-state candidate, consult the negative-knowledge
    library (read-only). A PROVEN_INVARIANT hard-block kills the
    candidate in-place (state -> NOT_A_CANDIDATE_CEMETERY_PROVEN_
    INVARIANT, the block recorded on the candidate with entry ids and
    matched domain terms); STRONG_CONSTRAINT warnings ride the
    candidate downstream (recorded, not blocking — explicit override
    justification territory). The consultation itself is recorded:
    entry count, blocked count, warning count, and the honest
    CEMETERY_CONSULTATION_UNAVAILABLE state if the orchestrator layer
    is not importable in this context (never silent, never a block on
    infrastructure failure — Art. XXV)."""
    record: Dict[str, Any] = {
        "consumption_version": "cemetery_consumption/1.0.0",
        "rule": ("Art. LI: negative knowledge is a state-transition "
                 "mechanism — killed invariants must be capable of "
                 "changing future search; a written-but-never-read "
                 "cemetery is a log, not a memory"),
        "n_candidates_consulted": 0,
        "n_blocked": 0,
        "n_warned": 0,
        "blocked": [],
    }
    try:
        from orchestrator.mechanism_cemetery import \
            check_candidate_against_cemetery
    except Exception as exc:  # noqa: BLE001 — honest state (Art. XXV)
        record["state"] = "CEMETERY_CONSULTATION_UNAVAILABLE"
        record["error"] = f"{type(exc).__name__}: {exc}"[:200]
        record["note"] = ("the cemetery could not be consulted — "
                          "infrastructure state, NOT a scientific "
                          "verdict; no candidate was blocked or "
                          "cleared by this (Art. XXV)")
        return record
    total_lessons: Optional[int] = None
    for c in candidates:
        if c.get("candidate_state") != "CANDIDATE":
            continue
        record["n_candidates_consulted"] += 1
        desc = " ".join(str(c.get(k) or "") for k in (
            "intervention", "mechanism", "predicted_effect",
            "novel_design_variable"))[:2000]
        try:
            res = check_candidate_against_cemetery(desc)
        except Exception as exc:  # noqa: BLE001 — honest state (Art. XXV)
            record["state"] = "CEMETERY_CONSULTATION_UNAVAILABLE"
            record["error"] = f"{type(exc).__name__}: {exc}"[:200]
            return record
        total_lessons = res.get("total_lessons_consulted", 0)
        hard = res.get("hard_blocks") or []
        if hard:
            c["candidate_state"] = \
                "NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT"
            c["cemetery_block"] = hard
            record["n_blocked"] += 1
            record["blocked"].append({
                "candidate_id": c.get("candidate_id"),
                "entries": [b.get("cemetery_entry") for b in hard],
                "domain_match": [b.get("domain_match") for b in hard],
            })
        elif res.get("warnings"):
            c["cemetery_warnings"] = res["warnings"]
            record["n_warned"] += 1
    record["state"] = "CONSULTED"
    record["total_lessons_consulted"] = total_lessons
    return record


def build_mechanism_space(problem: Dict[str, Any],
                          evidence: List[Dict[str, Any]],
                          top_k: int = 6,
                          per_operator_item_cap: int = 0,
                          min_candidates: int = 5,
                          ) -> Dict[str, Any]:
    """The full R401 mechanism-space construction:

        structured evidence -> five operators -> candidates ->
        distinctness -> per-candidate mechanism-level verification ->
        metrics

    Everything is recorded; nothing is converted; the machine is allowed
    to produce zero candidates (that is an honest outcome, stated as
    such)."""
    # OPERATOR OVERRIDE (R401, the standing explicit-logged pattern):
    # R401_OPERATOR_ITEM_CAP raises the per-operator instantiation
    # budget (more LLM instantiation calls = more chances for valid
    # DISTINCT candidates; NEVER a gate change — every candidate still
    # faces the span, semantic, testable-prediction and distinctness
    # gates). Recorded in the space record.
    import os as _os
    if per_operator_item_cap <= 0:
        per_operator_item_cap = int(
            _os.environ.get("R401_OPERATOR_ITEM_CAP", "2"))
    space: Dict[str, Any] = {
        "mechanism_space_version": MECHANISM_SPACE_VERSION,
        "built_at": utc_now(),
        "problem_id": problem.get("problem_id", ""),
        "operator_ids": list(OPERATOR_IDS),
        "per_operator_item_cap": per_operator_item_cap,
        "item_cap_source": ("env R401_OPERATOR_ITEM_CAP"
                            if _os.environ.get("R401_OPERATOR_ITEM_CAP")
                            else "default"),
    }
    se = build_structured_evidence(problem, evidence, top_k=top_k)
    space["structured_evidence"] = {
        "state": se["state"], "n_items": se.get("n_items", 0),
        "n_items_with_bound_mechanism": se.get(
            "n_items_with_bound_mechanism", 0),
        "items": [
            {"item_id": it.get("item_id"),
             "structured_hash": it.get("structured_hash"),
             "extraction_summary": it.get("extraction_summary"),
             "fields": {k: v.get("value") for k, v in
                        (it.get("fields") or {}).items()},
             "source": it.get("source"),
             "provenance": it.get("provenance"),
             "record_text": it.get("_record_text", "")}
            for it in se.get("items", [])],
        "rerank": se.get("rerank"),
        "evidence_boundary": se.get("evidence_boundary"),
        "multi_source_expansion": {
            k: v for k, v in (se.get("multi_source_expansion") or
                              {}).items() if k != "records"} | {
            "n_records": len((se.get("multi_source_expansion") or
                              {}).get("records", []))},
    }
    # keep the full structured items (with validation states) on the
    # record for the verification pass
    structured_items = se.get("items", [])
    if se["state"] != "BUILT":
        space["state"] = "NO_EVIDENCE"
        space["candidates"] = []
        space["metrics"] = _metrics(space, [], [], [], 0)
        return space
    # the five operators
    all_candidates: List[Dict[str, Any]] = []
    operator_results = []
    for op in TRANSFORMATION_OPERATORS:
        res = apply_operator(op, structured_items, problem,
                             per_operator_item_cap=per_operator_item_cap)
        operator_results.append(res)
        for c in res.get("candidates", []):
            if isinstance(c, dict) and c.get("candidate_state") == \
                    "CANDIDATE":
                all_candidates.append(c)
    space["operator_results"] = [
        {k: v for k, v in r.items() if k != "candidates"}
        for r in operator_results]
    space["operator_candidates_full"] = operator_results
    # R402 / Art. LI (audit CB-5): the mechanism space CONSUMES the
    # cemetery — negative knowledge must change future search, not sit
    # in an archive. A candidate whose causal vocabulary hard-blocks on
    # a PROVEN_INVARIANT is killed HERE (recorded, with the entry ids
    # and the matched domain terms); STRONG_CONSTRAINT warnings ride
    # the candidate downstream. The v1 space had ZERO references to
    # the cemetery — failures were archived, never learned.
    cemetery_consumption = _consult_cemetery(all_candidates)
    space["cemetery_consumption"] = cemetery_consumption
    # distinctness
    dedup = deduplicate_candidates(all_candidates)
    kept = dedup["n_kept"]
    retained = _retained_candidates(all_candidates, dedup)
    space["distinctness"] = dedup
    # per-candidate mechanism-level verification (on RETAINED
    # candidates; dropped duplicates inherit their kept twin's verdict)
    verifications = [verify_mechanism_support(c, structured_items,
                                              problem)
                     for c in retained]
    for c, v in zip(retained, verifications):
        c["mechanism_support"] = v
    space["candidates"] = [
        _public_candidate(c) for c in retained]
    space["state"] = ("BUILT" if kept >= min_candidates else
                      "BUILT_BELOW_MIN" if kept else "NO_CANDIDATES")
    space["n_candidates_generated"] = len(all_candidates)
    space["n_candidates_retained"] = len(retained)
    space["min_candidates_required"] = min_candidates
    space["metrics"] = _metrics(space, all_candidates, retained,
                                 verifications, len(structured_items))
    return space


def _retained_candidates(all_candidates: List[Dict[str, Any]],
                         dedup: Dict[str, Any]
                         ) -> List[Dict[str, Any]]:
    by_id = {c.get("candidate_id"): c for c in all_candidates}
    return [by_id[i] for i in dedup.get("kept_ids", []) if i in by_id]


def _public_candidate(c: Dict[str, Any]) -> Dict[str, Any]:
    """The candidate as it travels downstream: the 9 canonical fields +
    the fields the gauntlet consumes (mechanism/intervention/...)."""
    out = {k: c.get(k) for k in (
        "candidate_id", "candidate_hash", "candidate_schema",
        "candidate_state", "transformation_operator",
        "mechanism", "intervention", "mechanism_graph",
        "evidence_bundle", "constraint_set", "predicted_effect",
        "known_failure_modes", "novel_design_variable",
        "testable_prediction", "testable_prediction_check",
        "derivation_trace", "falsification_test", "expected_effect",
        "mechanism_source_span", "span_binding", "extraction_confidence",
        "mechanism_support", "distinctness_verdict",
        "distinctness_basis")}
    return out


# ---------------------------------------------------------------------------
# 10. The R401 metrics (Phase 9 — to expose actual behavior, never to
#     be optimized blindly)
# ---------------------------------------------------------------------------
def _metrics(space: Dict[str, Any],
             generated: List[Dict[str, Any]],
             retained: List[Dict[str, Any]],
             verifications: List[Dict[str, Any]],
             n_structured_items: int) -> Dict[str, Any]:
    n_gen = len(generated)
    n_ret = len(retained)
    # Art. XLVIII (v2): the diversity metric counts DISTINCT verdicts
    # only. INDETERMINATE candidates are retained (hypotheses pending
    # independent adjudication) but never counted; EQUIVALENT merges
    # are reported. The v1 rate (n_ret/n_gen) measured vocabulary
    # entropy of free-text envelope fields — the audit's CB-1 finding.
    verdicts = [c.get("distinctness_verdict") for c in retained]
    n_distinct = sum(1 for v in verdicts if v == "DISTINCT")
    n_indeterminate = sum(1 for v in verdicts
                          if v == "INDETERMINATE")
    n_equivalent = n_gen - n_ret
    operator_counts = {}
    for op_id in OPERATOR_IDS:
        n_op_gen = sum(1 for c in generated
                       if c.get("transformation_operator") == op_id)
        n_op_ret = sum(1 for c in retained
                       if c.get("transformation_operator") == op_id)
        operator_counts[op_id] = {"generated": n_op_gen,
                                  "retained": n_op_ret}
    n_testable = sum(1 for c in generated
                     if (c.get("testable_prediction_check") or {})
                     .get("testable"))
    support_items = contra_items = adjudicated = 0
    for v in verifications:
        for rel, n in (v.get("counts") or {}).items():
            adjudicated += n
            if rel in ("SUPPORTS", "PARTIALLY_SUPPORTS"):
                support_items += n
            elif rel == "CONTRADICTS":
                contra_items += n
    return {
        "mechanism_candidates_generated": n_gen,
        "mechanism_candidates_after_dedup": n_ret,
        "operator_counts": operator_counts,
        "material_distinctness_rate": (
            round(n_distinct / n_gen, 3) if n_gen else None),
        "material_mechanism_diversity": {
            "n_distinct": n_distinct,
            "n_indeterminate": n_indeterminate,
            "n_equivalent_merged": n_equivalent,
            "instrument_version": DISTINCTNESS_INSTRUMENT_VERSION,
            "note": ("MMD per Art. XLVIII: counts DISTINCT verdicts only "
                     "— EQUIVALENT merges and INDETERMINATE referrals "
                     "are reported but never counted as distinct "
                     "mechanisms (Art. XLII/XXV)")},
        "evidence_mechanism_support_rate": (
            round(support_items / adjudicated, 3) if adjudicated
            else None),
        "contradiction_rate": (
            round(contra_items / adjudicated, 3) if adjudicated
            else None),
        "testable_prediction_rate": (
            round(n_testable / n_gen, 3) if n_gen else None),
        "n_structured_evidence_items": n_structured_items,
        "states_vocabulary_note": (
            "rates expose behavior; NOT_ENOUGH_EVIDENCE/CONTESTED are "
            "never affirmative (Art. XXV)"),
    }


# ---------------------------------------------------------------------------
# 6b. Operator SEMANTIC checks (R401B B4 — the hard behavioral gate)
#
# For each operator, given the CONTROLLED SOURCE mechanism M1 (the
# structured evidence item) and the TRANSFORMED candidate M2, the check
# verifies:
#   1. an OPERATOR-SPECIFIC INVARIANT — what must be PRESERVED;
#   2. an OPERATOR-SPECIFIC REQUIRED CHANGE — what must be DIFFERENT;
#   3. an INDEPENDENT STRUCTURAL COMPARISON (term-level, stopword-
#      normalized — not semantic similarity);
#   4. the derivation trace (operator, selection contract, hashes);
#   5. the testable prediction (already enforced by the candidate
#      assembly).
#
# A textual rewrite of M1 that leaves the causal mechanism unchanged
# FAILS every operator's required-change check and is classified
# TEXTUAL_REWRITE (never a distinct candidate).
# ---------------------------------------------------------------------------
_INVARIANT_MIN_SHARED = 2          # shared specific terms (engine bar)
_TARGET_INSTITUTION_MIN = 1        # target-device terms in intervention
_BC_MAX_OVERLAP = 0.5              # boundary regime must differ by half
_INVERSION_MARKERS = (
    "prevent", "inhibits", "inhibit", "avoid", "suppress", "oppose",
    "reverse", "counter", "anti", "block", "neutralize", "opposing",
    "reduce", "eliminate", "mitigate", "counteract", "disrupt",
)
_GEOMETRY_CHANGE_MARKERS = (
    "dual", "multiple", "second", "two", "parallel", "spiral",
    "helical", "tapered", "annular", "concentric", "bifurcated",
    "serpentine", "mesh", "porous", "perforated", "slotted", "grooved",
    "layered", "count", "diameter", "cross-section", "topology",
    "arrangement", "geometry", "lumen", "lumens", "scale",
)


def _problem_device_terms(problem: Dict[str, Any]) -> set:
    return _terms(str(problem.get("device") or "")) - \
        {"device", "system", "the", "and", "for"}


def operator_semantic_check(op_id: str,
                            source_item: Dict[str, Any],
                            candidate: Dict[str, Any],
                            problem: Dict[str, Any]) -> Dict[str, Any]:
    """The B4 behavioral check: invariant + required change, decided by
    independent structural comparison of M1's structured fields vs M2's
    candidate fields (term sets). Pure and deterministic."""
    src = {k: _field_val(source_item, k) for k in
           ("system", "intervention", "mechanism", "observed_effect",
            "boundary_conditions", "failure_mode")}
    m1_mech = _terms(src["mechanism"]) | _terms(src["observed_effect"])
    m1_sys = _terms(src["system"])
    m1_bc = _terms(src["boundary_conditions"])
    m1_int = _terms(src["intervention"])
    m1_fm = _terms(src["failure_mode"])

    m2_mech = _terms(str(candidate.get("mechanism") or ""))
    m2_int = _terms(str(candidate.get("intervention") or ""))
    m2_bc = _terms(str(
        (candidate.get("constraint_set") or {}).get(
            "boundary_conditions") or ""))
    m2_pred = _terms(str(candidate.get("predicted_effect") or "")) | \
        _terms(str(candidate.get("testable_prediction") or ""))
    m2_dv = _terms(str(candidate.get("novel_design_variable") or ""))
    device_terms = _problem_device_terms(problem)

    out: Dict[str, Any] = {"operator": op_id,
                           "source_item_id": source_item.get("item_id"),
                           "checked_fields": {}}

    def _shared(a: set, b: set) -> List[str]:
        return sorted(a & b)

    if op_id == "DIRECT_TRANSFER":
        # INVARIANT: the demonstrated causal mechanism is preserved
        shared_mech = _shared(m1_mech, m2_mech)
        invariant = len(shared_mech) >= _INVARIANT_MIN_SHARED
        # REQUIRED CHANGE: the intervention instantiates the mechanism
        # in the TARGET device (target-device vocabulary present in the
        # intervention, traceable receiving-system change)
        target_hit = _shared(device_terms, m2_int)
        required = len(target_hit) >= _TARGET_INSTITUTION_MIN
        out["checked_fields"] = {
            "mechanism_preserved": {"shared_terms": shared_mech},
            "intervention_in_target_system": {"target_terms": target_hit}}
        out["invariant_held"] = invariant
        out["required_change_present"] = required
        out["invariant_basis"] = ("M2 mechanism shares >= "
                                  f"{_INVARIANT_MIN_SHARED} specific "
                                  "terms with M1's demonstrated "
                                  "mechanism/effect")
        out["required_change_basis"] = (
            "M2 intervention carries target-device vocabulary ("
            + ", ".join(sorted(device_terms)[:4]) + ") — the receiving "
            "system is instantiated, traceably")

    elif op_id == "CROSS_DOMAIN_ANALOGY":
        # INVARIANT: the source-domain mechanism is identified and
        # its causal structure transfers
        shared_mech = _shared(m1_mech, m2_mech)
        invariant = len(shared_mech) >= _INVARIANT_MIN_SHARED
        # REQUIRED CHANGE: the embodiment maps to the TARGET domain —
        # target vocabulary present AND the source system's own
        # distinctive terms do NOT dominate the intervention (the
        # system was replaced, not copied)
        target_hit = _shared(device_terms, m2_int | m2_mech)
        source_leak = [t for t in _shared(m1_sys, m2_int)
                       if t not in device_terms]
        required = len(target_hit) >= _TARGET_INSTITUTION_MIN
        out["checked_fields"] = {
            "source_mechanism_identified": {"shared_terms": shared_mech},
            "target_domain_mapping": {"target_terms": target_hit},
            "source_system_embodiment_not_copied": {
                "source_terms_in_intervention": source_leak}}
        out["invariant_held"] = invariant
        out["required_change_present"] = required
        out["invariant_basis"] = ("M2 mechanism shares the source "
                                  "domain's causal terms — the source "
                                  "mechanism is explicitly identified")
        out["required_change_basis"] = (
            "M2 carries target-domain vocabulary; the source system's "
            "embodiment is mapped away (analogy, never a copy)")

    elif op_id == "GEOMETRIC_TRANSFORMATION":
        # INVARIANT: the causal mechanism is preserved under the
        # geometric change
        shared_mech = _shared(m1_mech, m2_mech)
        invariant = len(shared_mech) >= _INVARIANT_MIN_SHARED
        # REQUIRED CHANGE: geometry-relevant structure CHANGES — new
        # geometry vocabulary appears in M2's intervention/design
        # variable that was absent from M1's intervention (count,
        # scale, topology, arrangement), or a geometric parameter is
        # re-specified
        geo_new = sorted(set(_GEOMETRY_CHANGE_MARKERS)
                         & (m2_int | m2_dv)
                         - (m1_int | set(_GEOMETRY_CHANGE_MARKERS)
                            & m1_int))
        geo_new = [g for g in geo_new
                   if g not in (m1_int | m1_mech)]
        required = len(geo_new) >= 1
        out["checked_fields"] = {
            "mechanism_preserved": {"shared_terms": shared_mech},
            "geometry_structure_changed": {"new_geometry_terms": geo_new}}
        out["invariant_held"] = invariant
        out["required_change_present"] = required
        out["invariant_basis"] = ("the causal mechanism survives the "
                                  "geometric transformation")
        out["required_change_basis"] = (
            "M2 introduces geometry-relevant structure absent from M1 "
            "(count/scale/topology/arrangement vocabulary in the "
            "intervention or design variable) — renaming the device is "
            "not a geometric transformation")

    elif op_id == "BOUNDARY_CONDITION_CHANGE":
        # INVARIANT: the mechanism identity is preserved
        shared_mech = _shared(m1_mech, m2_mech)
        invariant = len(shared_mech) >= _INVARIANT_MIN_SHARED
        # REQUIRED CHANGE: the operating/boundary regime differs —
        # M2's boundary vocabulary diverges from M1's (overlap at or
        # below the declared bar) AND the prediction changes
        # correspondingly (regime-relevant prediction terms)
        bc_shared = _shared(m1_bc, m2_bc)
        bc_overlap = (len(bc_shared) / len(m1_bc | m2_bc)
                      if (m1_bc | m2_bc) else 1.0)
        regime_changed = (bc_overlap <= _BC_MAX_OVERLAP) or (
            m2_bc - m1_bc and not bc_shared)
        pred_differs = bool(m2_pred - m1_mech)
        required = regime_changed and pred_differs
        out["checked_fields"] = {
            "mechanism_preserved": {"shared_terms": shared_mech},
            "boundary_regime_changed": {
                "shared_bc_terms": bc_shared,
                "jaccard": round(bc_overlap, 3)},
            "prediction_changes_with_regime": {
                "new_prediction_terms": sorted(m2_pred - m1_mech)[:10]}}
        out["invariant_held"] = invariant
        out["required_change_present"] = required
        out["invariant_basis"] = ("the mechanism's causal identity is "
                                  "preserved across the regime change")
        out["required_change_basis"] = (
            f"M2's boundary regime diverges from M1's (Jaccard <= "
            f"{_BC_MAX_OVERLAP} or disjoint new terms) and the "
            "prediction changes correspondingly")

    elif op_id == "FAILURE_PATH_INVERSION":
        # INVARIANT: the SAME causal pathway is used — M2's mechanism
        # shares the pathway vocabulary with M1's documented failure
        # mechanism
        pathway = m1_fm | m1_mech
        shared_path = _shared(pathway, m2_mech | m2_int)
        invariant = len(shared_path) >= 1
        # REQUIRED CHANGE: the pathway is INVERTED — the failure cause
        # is countered/prevented/suppressed in M2's intervention/
        # mechanism/prediction (inversion polarity present against the
        # pathway vocabulary), not merely restated
        m2_all = " ".join(str(candidate.get(k) or "") for k in
                          ("mechanism", "intervention",
                           "predicted_effect", "testable_prediction",
                           "novel_design_variable")).lower()
        m2_terms = _terms(m2_all)
        inversion_hits = _shared(set(_INVERSION_MARKERS), m2_terms)
        countered = [t for t in shared_path
                     if any(m in m2_all for m in _INVERSION_MARKERS)]
        required = len(inversion_hits) >= 1 and bool(countered or
                                                     shared_path)
        out["checked_fields"] = {
            "same_causal_pathway": {"shared_pathway_terms": shared_path},
            "pathway_inverted": {"inversion_markers": inversion_hits}}
        out["invariant_held"] = invariant
        out["required_change_present"] = required
        out["invariant_basis"] = ("M2 operates on the same causal "
                                  "pathway M1 documented as failing")
        out["required_change_basis"] = (
            "M2 carries inversion polarity (prevent/inhibit/reverse/"
            "counter...) against the documented failure pathway — "
            "describing the same failure differently is not an "
            "inversion")

    else:
        out["invariant_held"] = False
        out["required_change_present"] = False
        out["invariant_basis"] = "unknown operator"
        out["required_change_basis"] = "unknown operator"

    # THE VERDICT: a textual rewrite fails the required change; a
    # broken invariant means the transformation lost the mechanism
    if not out["invariant_held"]:
        out["semantic_verdict"] = "SEMANTIC_INVARIANT_BROKEN"
    elif not out["required_change_present"]:
        out["semantic_verdict"] = "TEXTUAL_REWRITE"
    else:
        out["semantic_verdict"] = "SEMANTICALLY_VALID"
    return out

"""discovery_fabric/engine/technical_state.py — R379 TECHNICAL
IMPROVEMENT ENGINE V2, layer 1: THE STRUCTURED TECHNICAL STATE.

CEO directive (2026-08-31, TECHNICAL IMPROVEMENT ENGINE V2):

> "1. Define a structured TECHNICAL STATE. A candidate must be able to
>  represent, where applicable: OBJECTS, PARAMETERS, GEOMETRY,
>  MATERIALS, OPERATING CONDITIONS, CONSTRAINTS, OBJECTIVES, FAILURE
>  MODES, DEPENDENCIES, MEASURABLE OUTPUTS. Keep UNKNOWN explicit."

This module is that state as code — plus the untrusted-proposal /
deterministic-validation construction path the constitution requires:

    LLM proposes the state (Art. XVIII — untrusted)
        -> validate_technical_state() (deterministic gates)
        -> invalid pieces DROPPED to UNKNOWN with recorded reasons
           (honest degradation: a failed extraction is a gap, never a
           fabricated value, and never a fatal loop error)

Value-class discipline (Art. XXVII / XXVIII / XXXVIII):
  EXTRACTED  the value is bound to a VERBATIM span of custodied
             evidence and the number/material string appears inside
             that span. SOURCE_FACT-class input.
  MODELLED   a declared design proposal. Never promoted. AI_INFERENCE
             class. Legitimate invention CONTENT when labeled.
  UNKNOWN    no value. A legitimate epistemic state (Art. XXV). Never
             a number, never a zero, never mutated against.

Constitutional anchors:
- Art. II    exact evidence beats semantic plausibility: EXTRACTED
             values are verified character-for-character.
- Art. VI    never manufacture provenance: spans that are not verbatim
             substrings are rejected before any value is admitted.
- Art. XVIII the LLM proposes; only the deterministic validator admits.
- Art. XXV   UNKNOWN stays UNKNOWN; a dropped piece becomes UNKNOWN.
- Art. XXVII every constraint needs a declared class + justification
             before it may gate anything.
- Art. XXVIII no silent promotion: value classes only ever move by
             re-extraction with a verified span.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .candidate import sha256_obj, utc_now

TECHNICAL_STATE_VERSION = "1.0.0"

VALUE_CLASSES = ("EXTRACTED", "MODELLED", "UNKNOWN")

# The ten CEO categories
TECHNICAL_STATE_CATEGORIES = (
    "OBJECTS", "PARAMETERS", "GEOMETRY", "MATERIALS",
    "OPERATING_CONDITIONS", "CONSTRAINTS", "OBJECTIVES",
    "FAILURE_MODES", "DEPENDENCIES", "MEASURABLE_OUTPUTS",
)

# parameter-like categories (a "variable" the mutation engine may move)
PARAM_CATEGORIES = ("PARAMETERS", "GEOMETRY", "MATERIALS",
                    "OPERATING_CONDITIONS")

DIRECTIONS = ("INCREASES", "DECREASES")
OBJECTIVE_DIRECTIONS = ("MINIMIZE", "MAXIMIZE", "MAINTAIN_WITHIN")
BOUNDS = ("<=", ">=")

_NUMBER_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?")


def _number_forms(value: Any) -> List[str]:
    """Every literal form a numeric value can take in text (0.5, .5,
    5e-1 round-trips are NOT searched — only decimal forms)."""
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (int, float)):
        s = str(value)
        forms = {s}
        if isinstance(value, float) and value.is_integer():
            forms.add(str(int(value)))
        if isinstance(value, float):
            forms.add(f"{value:.4f}".rstrip("0").rstrip("."))
        return sorted(forms)
    return [str(value)]


def _numbers_in_text(text: str) -> List[str]:
    return _NUMBER_TOKEN_RE.findall(text or "")


# ---------------------------------------------------------------------------
# The proposal prompt (LLM — untrusted proposer)
# ---------------------------------------------------------------------------
def build_technical_state_prompt(problem: Dict[str, Any],
                                 spec: Dict[str, Any],
                                 evidence_items: List[Dict[str, Any]],
                                 feedback: Optional[List[str]] = None
                                 ) -> str:
    """The extraction prompt. The LLM sees the problem, the candidate's
    mechanism, and the custodied evidence — and may ONLY source values
    from verbatim spans of that evidence. Everything it cannot source
    must be left out (absent = UNKNOWN; inventing a value with a fake
    span fails deterministic validation)."""
    mech = (spec.get("mechanism") or {}).get("value") or {}
    ev_blocks = []
    for e in (evidence_items or [])[:6]:
        ev_blocks.append(
            f"[EVIDENCE {e.get('id','')}] title: {e.get('title','')}\n"
            f"{(e.get('text') or '')[:1600]}")
    evidence_text = "\n\n".join(ev_blocks) if ev_blocks else \
        "(no custodied evidence — propose no values)"

    fb = ""
    if feedback:
        fb = ("\nPREVIOUS EXTRACTION DEFECTS (fix exactly these; do not "
              "repeat them):\n- " + "\n- ".join(feedback[-6:]) + "\n")

    return f"""You are a technical-state engineer. Build the STRUCTURED TECHNICAL
STATE of this invention candidate: the actual objects, design parameters,
geometry, materials, operating conditions, constraints, objectives, failure
modes, causal dependencies, and measurable outputs of the TECHNOLOGY (not
its paperwork).

DEVICE FAILURE (the problem this technology must solve):
- Device: {problem.get('device','')}
- Failure mode: {problem.get('failure_mode') or problem.get('failure','')[:400]}
- Constraint: {str(problem.get('constraint',''))[:400]}

CURRENT CANDIDATE:
- MECHANISM: {str(mech.get('mechanism',''))[:500]}
- INTERVENTION: {str(mech.get('intervention',''))[:500]}
- EXPECTED EFFECT: {str(mech.get('expected_effect',''))[:300]}

CUSTODIED EVIDENCE (the ONLY permissible source for EXTRACTED values —
a value_span must be copied character-for-character from these texts
and must CONTAIN the value you claim):
{evidence_text}
{fb}
Respond with ONE JSON object, no markdown fences, exactly this shape:
{{
 "objects": [{{"object_id": "...", "name": "...", "role": "..."}}],
 "parameters": [{{"param_id": "...", "name": "...", "category": "PARAMETERS|GEOMETRY|MATERIALS|OPERATING_CONDITIONS", "unit": "..." or null,
   "value": <number or material name string> or null, "value_class": "EXTRACTED|MODELLED|UNKNOWN",
   "value_span": "<verbatim substring of an evidence text>" or null, "value_evidence_id": "<evidence id>" or null,
   "range_min": <number> or null, "range_max": <number> or null, "range_span": "<verbatim>" or null, "range_evidence_id": "<id>" or null,
   "role": "what this variable does in the mechanism"}}],
 "constraints": [{{"constraint_id": "...", "target": "<param_id>", "bound": "<=|>=", "limit": <number>, "unit": "...",
   "limit_class": "EXTRACTED|MODELLED", "limit_span": "<verbatim>" or null, "limit_evidence_id": "<id>" or null,
   "justification": "why this limit, and its class (Art. XXVII: no invented thresholds)"}}],
 "objectives": [{{"objective_id": "...", "target": "<param_id>", "direction": "MINIMIZE|MAXIMIZE|MAINTAIN_WITHIN",
   "basis": "tie to the failure mode in one sentence"}}],
 "failure_modes": [{{"mode_id": "...", "name": "...", "problem_link": "tie to the device failure"}}],
 "dependencies": [{{"relation_id": "...", "cause": "<param_id>", "effect": "<param_id>", "direction": "INCREASES|DECREASES",
   "statement": "one sentence of the physical relationship",
   "relation_class": "EXTRACTED|MODELLED", "span": "<verbatim>" or null, "evidence_id": "<id>" or null}}]
}}

RULES (violations are dropped by the deterministic validator):
- EXTRACTED requires value_span AND value_evidence_id; the span must be
  copied character-for-character from that evidence text and MUST
  CONTAIN the value (and both numbers of a range).
- If you do not know a value, set value=null and value_class=UNKNOWN.
  UNKNOWN IS CORRECT AND EXPECTED — a fabricated value with a fake span
  is a provenance forgery and is rejected.
- MODELLED DESIGN ENVELOPE: when the evidence does not state bounds for
  a design variable, you MAY declare range_min/range_max WITHOUT a
  range_span — a declared design proposal for this technology, honestly
  classed MODELLED (never EXTRACTED). It must be physically reasonable
  for the device. Mean plus-minus SD in the evidence is NOT an envelope
  — never convert it into bounds.
- Dependencies describe PHYSICAL causality between the variables you
  declared (cause and effect must be declared param_ids).
- CAUSAL CONNECTIVITY: the objective target must be reachable from at
  least one design variable. For every parameter that carries an
  envelope (range_min/range_max), declare its dependency chain to the
  objective target: the physical variable you can set (cause) must
  connect, directly or through other parameters, to the objective
  (effect), with the direction (INCREASES/DECREASES) the physics
  actually has. If you cannot state the direction honestly, do not
  invent one — leave the dependency out and the variable stays
  unconnected (the mutation engine will honestly report no leverage).
- Only declare variables that exist in THIS technology.
- JSON only. No commentary.
"""


def parse_json_proposal(content: str) -> Optional[Dict[str, Any]]:
    """Extract the outermost JSON object from an LLM response. Failure
    returns None (recorded by the caller as a parse rejection — never
    a fabricated state)."""
    if not content:
        return None
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def propose_technical_state(problem: Dict[str, Any],
                            spec: Dict[str, Any],
                            evidence_items: List[Dict[str, Any]],
                            provider: Optional[str] = None,
                            feedback: Optional[List[str]] = None
                            ) -> Dict[str, Any]:
    """One LLM extraction attempt (with ONE content-retry: a malformed
    or truncated JSON response is re-requested once — a transport-class
    robustness measure, NOT a validation change; every gate below is
    untouched, and both attempts are recorded). The proposal is
    CONTENT, never evidence (Art. XVIII)."""
    from .llm_registry import SelectionPolicy, generate
    prompt = build_technical_state_prompt(problem, spec, evidence_items,
                                          feedback=feedback)
    preferred = [provider] if provider else [
        p for p in ("zai", "gemini", "openrouter", "nvidia", "mistral")]
    record: Dict[str, Any] = {
        "proposal_id": f"tsp:{sha256_obj(prompt)[:12]}",
        "attempts": [],
    }
    parsed: Optional[Dict[str, Any]] = None
    for attempt in range(1, 3):      # max 2 attempts (content retry)
        res = generate(
            prompt,
            system=("You are a technical-state engineer. Respond with "
                    "the JSON object exactly as specified. JSON only, "
                    "no commentary, no trailing text."),
            policy=SelectionPolicy(
                preferred_providers=preferred,
                max_preference_fallback=0,
                purpose="TECHNICAL_STATE_EXTRACTION"),
            max_tokens=3000)
        attempt_rec: Dict[str, Any] = {
            "attempt": attempt,
            "provider": res.provider_id, "model": res.model,
            "status": res.status, "prompt_hash": res.prompt_hash,
            "output_hash": res.output_hash,
            "latency_ms": res.latency_ms, "error": res.error,
        }
        record["attempts"].append(attempt_rec)
        record.update({
            "provider": res.provider_id, "model": res.model,
            "status": res.status, "prompt_hash": res.prompt_hash,
            "output_hash": res.output_hash,
            "latency_ms": res.latency_ms, "error": res.error})
        if not res.ok:
            break
        attempt_rec["raw_content_sha256"] = sha256_obj(res.content or "")
        parsed = parse_json_proposal(res.content)
        if parsed is not None:
            record["proposal"] = parsed
            record["raw_content_sha256"] = attempt_rec[
                "raw_content_sha256"]
            break
        attempt_rec["parse_failed"] = True
        record["parse_failed"] = True
    return record


# ---------------------------------------------------------------------------
# DETERMINISTIC VALIDATION (the trust boundary)
# ---------------------------------------------------------------------------
def _evidence_texts(evidence_items: List[Dict[str, Any]]) -> \
        Dict[str, str]:
    return {str(e.get("id")): f"{e.get('title','')}\n{e.get('text') or ''}"
            for e in (evidence_items or [])}


def _span_ok(span: Optional[str], evidence_id: Optional[str],
             ev_texts: Dict[str, str]) -> Tuple[bool, str]:
    if not span or not evidence_id:
        return False, "span or evidence_id missing"
    text = ev_texts.get(evidence_id)
    if text is None:
        return False, f"evidence {evidence_id!r} not custodied"
    if span not in text:
        return False, "span is NOT a verbatim substring of the evidence"
    return True, ""


def _value_in_span(value: Any, span: str) -> bool:
    """The claimed value must appear inside its own span. Numbers are
    checked by token overlap (a '0.4-0.8 ppm' span proves both 0.4 and
    0.8 and any point value named there); strings by containment."""
    if value is None:
        return False
    span_nums = set(_numbers_in_text(span))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return any(f in span_nums for f in _number_forms(value))
    return str(value).strip() in span


def _clean_param(p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "param_id": str(p.get("param_id") or "").strip(),
        "name": str(p.get("name") or "").strip(),
        "category": str(p.get("category") or "PARAMETERS").strip(),
        "unit": p.get("unit") if p.get("unit") else None,
        "value": p.get("value") if p.get("value") is not None else None,
        "value_class": str(p.get("value_class") or "UNKNOWN").strip(),
        "value_span": p.get("value_span") or None,
        "value_evidence_id": p.get("value_evidence_id") or None,
        "range_min": p.get("range_min") if p.get("range_min") is not None
        else None,
        "range_max": p.get("range_max") if p.get("range_max") is not None
        else None,
        "range_span": p.get("range_span") or None,
        "range_evidence_id": p.get("range_evidence_id") or None,
        "range_class": "UNKNOWN",
        "role": str(p.get("role") or "").strip()[:300],
    }


def validate_technical_state(proposal: Dict[str, Any],
                             evidence_items: List[Dict[str, Any]],
                             problem: Dict[str, Any]
                             ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """The deterministic gates. Admits pieces; drops the rest to
    UNKNOWN with recorded reasons. Returns (technical_state,
    validation_report). The state is NEVER a pass/fail of the whole
    candidate — partial quantification is the expected honest state.

    Gates (each drop is recorded):
      P1 structure/ids; P2 category enum
      P3 EXTRACTED value: span verbatim + value inside span
      P4 MODELLED value: declared (allowed; recorded)
      P5 range: EXTRACTED range must be span-proven + ordered
      P6 value within its own declared range
      C1 constraint: target declared, bound enum, limit numeric,
         class + justification present (Art. XXVII)
      C2 EXTRACTED limit: span-proven + number in span
      O1 objective: target declared, direction enum, basis tied to the
         problem vocabulary (the objective must BE the problem's)
      D1 dependency: cause/effect declared, direction enum
      D2 EXTRACTED relation: span-proven + both endpoint names' terms
         present in the span
    """
    ev_texts = _evidence_texts(evidence_items)
    report: Dict[str, Any] = {
        "validator": "technical_state_v1 (deterministic)",
        "validated_at": utc_now(),
        "gates": [], "dropped": [],
        "admitted_counts": {},
    }

    def _drop(kind: str, ident: str, gate: str, reason: str) -> None:
        report["dropped"].append(
            {"kind": kind, "id": ident, "gate": gate, "reason": reason})

    def _gate(name: str, passed: bool, detail: str = "") -> None:
        report["gates"].append(
            {"gate": name, "passed": passed, "detail": detail[:200]})

    # ---------- P: parameters ----------
    raw_params = [p for p in (proposal.get("parameters") or [])
                  if isinstance(p, dict)]
    params: List[Dict[str, Any]] = []
    seen_ids: set = set()
    for p in raw_params:
        cp = _clean_param(p)
        pid = cp["param_id"]
        if not pid or pid in seen_ids:
            _drop("parameter", pid or "<no-id>", "P1",
                  "missing or duplicate param_id")
            continue
        seen_ids.add(pid)
        if cp["category"] not in PARAM_CATEGORIES:
            _drop("parameter", pid, "P2",
                  f"category {cp['category']!r} not in {PARAM_CATEGORIES}")
            continue
        vc = cp["value_class"]
        if cp["value"] is not None and vc not in ("EXTRACTED", "MODELLED"):
            _drop("parameter", pid, "P3/P4",
                  "value present without EXTRACTED/MODELLED class")
            continue
        if cp["value"] is None:
            cp["value_class"] = "UNKNOWN"
            cp["value_span"] = None
            cp["value_evidence_id"] = None
        elif vc == "EXTRACTED":
            ok, why = _span_ok(cp["value_span"], cp["value_evidence_id"],
                               ev_texts)
            if not ok or not _value_in_span(cp["value"],
                                            cp["value_span"] or ""):
                # DEMOTE, not drop: the value fails its provenance, but
                # the parameter (and any span-proven envelope below)
                # remains a declared variable with an UNKNOWN value —
                # a failed extraction is a gap, not a fabrication
                # (Art. XXV; measured while writing the adversarial
                # tests: dropping the whole param cascaded into
                # dangling dependency/constraint references)
                report["dropped"].append({
                    "kind": "parameter_value", "id": pid, "gate": "P3",
                    "reason": (f"EXTRACTED value not proven by its span "
                               f"({why or 'value not inside span'}) — "
                               f"value demoted to UNKNOWN, parameter kept")})
                cp["value"] = None
                cp["value_class"] = "UNKNOWN"
                cp["value_span"] = None
                cp["value_evidence_id"] = None
        elif vc == "MODELLED":
            _gate("P4_modelled_value_declared", True, pid)
        # range gates (the mutation envelope)
        cp["range_class"] = "UNKNOWN"
        rmin, rmax = cp["range_min"], cp["range_max"]
        if rmin is not None or rmax is not None:
            try:
                rmin = float(rmin) if rmin is not None else None
                rmax = float(rmax) if rmax is not None else None
                cp["range_min"], cp["range_max"] = rmin, rmax
            except (TypeError, ValueError):
                _drop("parameter", pid, "P5", "non-numeric range bounds")
                cp["range_min"] = cp["range_max"] = None
                rmin = rmax = None
            if rmin is not None and rmax is not None and rmin > rmax:
                _drop("parameter", pid, "P5",
                      f"range inverted [{rmin}, {rmax}] — bounds dropped")
                cp["range_min"] = cp["range_max"] = None
            elif (rmin is not None or rmax is not None) and \
                    not cp.get("range_span"):
                # a range without provenance is a MODELLED envelope —
                # declared, never EXTRACTED (Art. XXVII)
                if cp["value_class"] == "EXTRACTED":
                    _gate("P5_range_span_absent", False,
                          f"{pid}: EXTRACTED-value param cannot carry an "
                          f"unproven envelope — bounds dropped")
                    cp["range_min"] = cp["range_max"] = None
                else:
                    cp["range_class"] = "MODELLED"
                    _gate("P5_range_modelled_envelope", True,
                          f"{pid}: declared MODELLED envelope "
                          f"[{rmin}, {rmax}]")
            elif cp.get("range_span"):
                ok, why = _span_ok(cp["range_span"],
                                   cp.get("range_evidence_id"), ev_texts)
                nums_ok = ok and all(
                    _value_in_span(v, cp["range_span"])
                    for v in (cp["range_min"], cp["range_max"])
                    if v is not None)
                if not ok or not nums_ok:
                    _gate("P5_range_unproven", False,
                          f"{pid}: range bounds not span-proven — dropped "
                          f"to UNKNOWN (Art. XXVII)")
                    cp["range_min"] = cp["range_max"] = None
                else:
                    cp["range_class"] = "EXTRACTED"
        # value must sit inside its own proven envelope (P6) — when the
        # value is EXTRACTED it was proven by its own span, but the
        # envelope is the mutation boundary: an out-of-envelope value
        # is demoted, not silently kept
        if cp["value"] is not None and \
                isinstance(cp["value"], (int, float)) and \
                cp["range_min"] is not None and \
                not (cp["range_min"] <= float(cp["value"])):
            report["dropped"].append({
                "kind": "parameter_value", "id": pid, "gate": "P6",
                "reason": (f"value {cp['value']} below its own range_min "
                           f"{cp['range_min']} — demoted to UNKNOWN")})
            cp["value"], cp["value_class"] = None, "UNKNOWN"
            cp["value_span"] = cp["value_evidence_id"] = None
        if cp["value"] is not None and \
                isinstance(cp["value"], (int, float)) and \
                cp["range_max"] is not None and \
                not (float(cp["value"]) <= cp["range_max"]):
            report["dropped"].append({
                "kind": "parameter_value", "id": pid, "gate": "P6",
                "reason": (f"value {cp['value']} above its own range_max "
                           f"{cp['range_max']} — demoted to UNKNOWN")})
            cp["value"], cp["value_class"] = None, "UNKNOWN"
            cp["value_span"] = cp["value_evidence_id"] = None
        params.append(cp)

    param_ids = {p["param_id"] for p in params}

    # ---------- C: constraints ----------
    constraints: List[Dict[str, Any]] = []
    seen_c = set()
    for c in (proposal.get("constraints") or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("constraint_id") or "").strip()
        target = str(c.get("target") or "").strip()
        if not cid or cid in seen_c:
            _drop("constraint", cid or "<no-id>", "C1",
                  "missing or duplicate constraint_id")
            continue
        seen_c.add(cid)
        if target not in param_ids:
            _drop("constraint", cid, "C1",
                  f"target {target!r} is not a declared parameter")
            continue
        bound = str(c.get("bound") or "").strip()
        if bound not in BOUNDS:
            _drop("constraint", cid, "C1",
                  f"bound {bound!r} not in {BOUNDS}")
            continue
        limit = c.get("limit")
        try:
            limit = float(limit)
        except (TypeError, ValueError):
            _drop("constraint", cid, "C1", "limit is not a number")
            continue
        limit_class = str(c.get("limit_class") or "").strip()
        justification = str(c.get("justification") or "").strip()
        if limit_class not in ("EXTRACTED", "MODELLED"):
            _drop("constraint", cid, "C1",
                  "limit_class must be EXTRACTED or MODELLED (Art. XXVII)")
            continue
        if not justification:
            _drop("constraint", cid, "C1",
                  "constraint without justification is an invented "
                  "threshold (Art. XXVII — forbidden)")
            continue
        span = c.get("limit_span") or None
        ev_id = c.get("limit_evidence_id") or None
        if limit_class == "EXTRACTED":
            ok, why = _span_ok(span, ev_id, ev_texts)
            if not ok:
                _drop("constraint", cid, "C2",
                      f"EXTRACTED limit: {why}")
                continue
            if not _value_in_span(limit, span or ""):
                _drop("constraint", cid, "C2",
                      "EXTRACTED limit number not in its span")
                continue
        constraints.append({
            "constraint_id": cid, "target": target, "bound": bound,
            "limit": limit, "unit": c.get("unit") or None,
            "limit_class": limit_class, "limit_span": span,
            "limit_evidence_id": ev_id,
            "justification": justification[:400]})

    # ---------- O: objectives ----------
    objectives: List[Dict[str, Any]] = []
    seen_o = set()
    prob_vocab = " ".join(str(problem.get(k) or "") for k in
                          ("device", "failure_mode", "failure",
                           "constraint")).lower()
    for o in (proposal.get("objectives") or []):
        if not isinstance(o, dict):
            continue
        oid = str(o.get("objective_id") or "").strip()
        target = str(o.get("target") or "").strip()
        if not oid or oid in seen_o:
            _drop("objective", oid or "<no-id>", "O1", "duplicate id")
            continue
        seen_o.add(oid)
        if target not in param_ids:
            _drop("objective", oid, "O1",
                  f"target {target!r} is not a declared parameter")
            continue
        direction = str(o.get("direction") or "").strip()
        if direction not in OBJECTIVE_DIRECTIONS:
            _drop("objective", oid, "O1",
                  f"direction {direction!r} not in {OBJECTIVE_DIRECTIONS}")
            continue
        basis = str(o.get("basis") or "").strip()
        # the objective must BE this problem's objective: at least one
        # non-trivial shared term with the device/failure vocabulary
        basis_terms = {w for w in re.findall(r"[a-z]{4,}", basis.lower())}
        prob_terms = set(re.findall(r"[a-z]{4,}", prob_vocab))
        if not basis or not (basis_terms & prob_terms):
            _drop("objective", oid, "O1",
                  "basis not tied to this problem's device/failure "
                  "vocabulary — an objective the problem does not have")
            continue
        objectives.append({"objective_id": oid, "target": target,
                           "direction": direction, "basis": basis[:400]})

    # ---------- D: dependencies ----------
    dependencies: List[Dict[str, Any]] = []
    seen_d = set()
    for d in (proposal.get("dependencies") or []):
        if not isinstance(d, dict):
            continue
        rid = str(d.get("relation_id") or "").strip()
        cause = str(d.get("cause") or "").strip()
        effect = str(d.get("effect") or "").strip()
        if not rid or rid in seen_d:
            _drop("dependency", rid or "<no-id>", "D1", "duplicate id")
            continue
        seen_d.add(rid)
        if cause not in param_ids or effect not in param_ids:
            _drop("dependency", rid, "D1",
                  f"cause {cause!r} / effect {effect!r} must be declared "
                  f"param_ids")
            continue
        if cause == effect:
            _drop("dependency", rid, "D1", "self-loop")
            continue
        direction = str(d.get("direction") or "").strip()
        if direction not in DIRECTIONS:
            _drop("dependency", rid, "D1",
                  f"direction {direction!r} not in {DIRECTIONS}")
            continue
        rel_class = str(d.get("relation_class") or "").strip()
        if rel_class not in ("EXTRACTED", "MODELLED"):
            _drop("dependency", rid, "D1",
                  "relation_class must be EXTRACTED or MODELLED")
            continue
        span = d.get("span") or None
        ev_id = d.get("evidence_id") or None
        if rel_class == "EXTRACTED":
            ok, why = _span_ok(span, ev_id, ev_texts)
            if not ok:
                _drop("dependency", rid, "D2",
                      f"EXTRACTED relation: {why}")
                continue
            # both endpoints must be named in the span (the span must
            # be ABOUT this relationship)
            span_l = str(span).lower()
            name_a = _param_by_id(params, cause)["name"].lower()
            name_b = _param_by_id(params, effect)["name"].lower()
            ta = {w for w in re.findall(r"[a-z]{4,}", name_a)}
            tb = {w for w in re.findall(r"[a-z]{4,}", name_b)}
            span_terms = set(re.findall(r"[a-z]{4,}", span_l))
            if not (ta & span_terms) or not (tb & span_terms):
                _drop("dependency", rid, "D2",
                      "the span does not name both endpoints — it is "
                      "not evidence for THIS relationship")
                continue
        dependencies.append({
            "relation_id": rid, "cause": cause, "effect": effect,
            "direction": direction,
            "statement": str(d.get("statement") or "")[:400],
            "relation_class": rel_class, "span": span,
            "evidence_id": ev_id})

    # ---------- objects + failure modes (declared, no numbers) ----------
    objects = []
    for o in (proposal.get("objects") or []):
        if isinstance(o, dict) and o.get("object_id") and o.get("name"):
            objects.append({"object_id": str(o["object_id"]),
                            "name": str(o["name"])[:200],
                            "role": str(o.get("role") or "")[:300]})
    failure_modes = []
    for f in (proposal.get("failure_modes") or []):
        if isinstance(f, dict) and f.get("mode_id") and f.get("name"):
            failure_modes.append({
                "mode_id": str(f["mode_id"]),
                "name": str(f["name"])[:200],
                "problem_link": str(f.get("problem_link") or "")[:300]})

    state = {
        "version": TECHNICAL_STATE_VERSION,
        "objects": objects,
        "parameters": params,
        "constraints": constraints,
        "objectives": objectives,
        "failure_modes": failure_modes,
        "dependencies": dependencies,
        "extraction": None,      # filled by the caller (provenance)
    }
    report["admitted_counts"] = {
        "parameters": len(params),
        "parameters_with_value": sum(
            1 for p in params if p["value"] is not None),
        "parameters_extracted": sum(
            1 for p in params if p["value_class"] == "EXTRACTED"),
        "parameters_modelled": sum(
            1 for p in params if p["value_class"] == "MODELLED"),
        "parameters_with_envelope": sum(
            1 for p in params if p["range_min"] is not None
            or p["range_max"] is not None),
        "constraints": len(constraints),
        "objectives": len(objectives),
        "dependencies": len(dependencies),
        "objects": len(objects),
        "failure_modes": len(failure_modes),
    }
    return state, report


def _param_by_id(params: List[Dict[str, Any]], pid: str) -> \
        Dict[str, Any]:
    for p in params:
        if p["param_id"] == pid:
            return p
    return {"param_id": pid, "name": pid, "value": None,
            "value_class": "UNKNOWN", "category": "PARAMETERS",
            "unit": None, "range_min": None, "range_max": None}


def attach_technical_state(spec: Dict[str, Any],
                           state: Dict[str, Any],
                           proposal_record: Dict[str, Any],
                           validation_report: Dict[str, Any]
                           ) -> Dict[str, Any]:
    """Write the validated technical state onto the INVENTION_SPEC as
    a first-class section (CEO item 1). The section carries the
    epistemic class of the state itself (MODELLED — the state is a
    model of the technology, assembled from EXTRACTED pieces) and the
    full extraction provenance."""
    state = dict(state)
    state["extraction"] = {
        "proposal_id": proposal_record.get("proposal_id"),
        "provider": proposal_record.get("provider"),
        "model": proposal_record.get("model"),
        "prompt_hash": proposal_record.get("prompt_hash"),
        "output_hash": proposal_record.get("output_hash"),
        "llm_is_untrusted_proposer": True,
        "validator": validation_report.get("validator"),
        "admitted_counts": validation_report.get("admitted_counts"),
        "dropped_pieces": validation_report.get("dropped"),
        "extracted_at": utc_now(),
    }
    spec = dict(spec)
    spec["technical_state"] = {
        "value": state,
        "epistemic_class": "MODELLED",
        "origin_stage": "TECHNICAL_STATE_EXTRACTION",
        "evidence_ids": sorted({
            p.get("value_evidence_id") for p in state["parameters"]
            if p.get("value_evidence_id")} | {
            c.get("limit_evidence_id") for c in state["constraints"]
            if c.get("limit_evidence_id")} | {
            d.get("evidence_id") for d in state["dependencies"]
            if d.get("evidence_id")}),
        "note": ("structured technical state (R379): values are "
                 "EXTRACTED (span-verified) / MODELLED (declared) / "
                 "UNKNOWN (explicit); the analytical evaluator "
                 "computes predictions from this state — predictions "
                 "are model inferences, never measurements"),
    }
    spec.pop("_spec_hash", None)
    return spec


def get_technical_state(spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ts = spec.get("technical_state")
    if isinstance(ts, dict) and isinstance(ts.get("value"), dict):
        return ts["value"]
    return None


def mutable_parameters(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parameters the mutation engine may move: they have a value (or
    are material strings) AND a declared envelope [range_min,
    range_max] (or for materials: an evidence-proven alternative set —
    V2: materials need a declared range too, expressed as candidate
    string values with spans). An UNBOUNDED parameter is immutable:
    moving it would be unconstrained invention (declared ADR_R379)."""
    out = []
    for p in (state or {}).get("parameters") or []:
        if p.get("range_min") is None and p.get("range_max") is None:
            continue
        out.append(p)
    return out

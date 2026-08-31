"""discovery_fabric/engine/technical_improvement_engine.py — R379
TECHNICAL IMPROVEMENT ENGINE V2: THE TECHNICAL MUTATION LOOP.

CEO directive (2026-08-31, R379) — the loop must become about THE
TECHNOLOGY, not the wording of the technology:

    CANDIDATE A
    -> DIAGNOSE (technical: limiting variable + direction)
    -> TECHNICAL MUTATION (change an ACTUAL design variable)
    -> CANDIDATE B
    -> INDEPENDENT TECHNICAL EVALUATION
    -> EVIDENCE / PRIOR-ART RECHECK
    -> KEEP / KILL
    -> SECOND IMPROVEMENT

and the child must prove it is genuinely BETTER TECHNOLOGY, not merely
a better-scoring description. "Do not accept 'the score increased' as
sufficient evidence of improvement."

Layer map:
  layer 1  technical_state.py       — the structured technical state
  layer 2  technical_evaluator.py   — the evaluator contract + the
                                      analytical evaluator
  layer 3  THIS MODULE — the mutation loop:
             extract_state (LLM proposes, validator admits)
             diagnose      (deterministic: limiting variable)
             propose       (LLM — UNTRUSTED, Art. XVIII)
             validate      (DETERMINISTIC gates; the trust boundary)
             apply         (child technical state + spec-text sync +
                            the Art. XXXVIII causal chain)
             re_evaluate   (fresh technical evaluation + prior-art
                            re-adjudication + BOTH instruments — no
                            inherited scores)
             keep_or_kill  (technical criterion + epistemic invariants)
             loop          (bounded iterations; attribution ledger)

Mutation kinds (CEO item 3):
  PARAMETER_CHANGE           move a numeric design variable
  GEOMETRY_CHANGE            move a GEOMETRY-category variable
  MATERIAL_CHANGE            swap a MATERIAL-category variable
  OPERATING_CONDITION_CHANGE move an OPERATING_CONDITIONS variable
  MECHANISM_CHANGE           add a span-backed causal relation
  ARCHITECTURE_CHANGE        reserved (needs a structural search space)
  CONTROL_POLICY_CHANGE      reserved (needs a control-law class)

Constitutional anchors:
- Art. XX    a candidate already KILLED by the attack is not improved.
- Art. XXV   UNQUANTIFIED is an honest outcome, not a failure; transport
             failure is BLOCKED_TRANSPORT, never a kill.
- Art. XXVII every threshold/convention is declared with class+reason.
- Art. XXVIII value classes never silently promote; MODELLED stays
             MODELLED until re-extracted with a verified span.
- Art. XXX   the KEEP criterion is the technical prediction, never the
             instrument score (the CEO's explicit rule).
- Art. XXXIII a KILL requires the measured ledger.
- Art. XXXVIII every mutation carries the causal chain with hashes.
"""
from __future__ import annotations

import copy
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .candidate import sha256_obj, utc_now
from .evaluator_contract import CandidateContext
from .improvement_engine import (
    collect_negatives, negatives_preserved, re_adjudicate_cached)
from .technical_state import (
    attach_technical_state, get_technical_state,
    propose_technical_state, validate_technical_state)
from .technical_evaluator import evaluate_candidate_technically

TECHNICAL_LEDGER_VERSION = "2.0.0"

# ---------------------------------------------------------------------------
# Declared thresholds (Art. XXVII)
# ---------------------------------------------------------------------------
TECHNICAL_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "MAX_ITERATIONS_DEFAULT": {
        "value": 2,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "the CEO milestone is DIAGNOSE -> TECHNICAL MUTATION -> "
            "RE-EVALUATE -> SECOND IMPROVEMENT; two iterations "
            "demonstrate repeatability at bounded cost")},
    "MAX_PROPOSALS_PER_ITERATION": {
        "value": 3,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "bounded proposal budget, identical to the R378 epistemic "
            "loop: three attempts, then the honest "
            "no-defensible-mutation verdict")},
    "VALUE_CLASS_STRICTNESS": {
        "value": "HARD",
        "epistemic_class": "ENGINEERING",
        "justification": (
            "EXTRACTED claims are span-verified or rejected (Art. II/VI); "
            "MODELLED values are admitted only when declared; an "
            "unbounded parameter is immutable (ADR_R379 anti-gaming)")},
}

TECHNICAL_MUTATION_KINDS = (
    "PARAMETER_CHANGE", "GEOMETRY_CHANGE", "MATERIAL_CHANGE",
    "OPERATING_CONDITION_CHANGE", "MECHANISM_CHANGE",
)
RESERVED_MUTATION_KINDS = (
    "ARCHITECTURE_CHANGE", "CONTROL_POLICY_CHANGE",
)

CATEGORY_TO_KIND = {
    "PARAMETERS": "PARAMETER_CHANGE",
    "GEOMETRY": "GEOMETRY_CHANGE",
    "MATERIALS": "MATERIAL_CHANGE",
    "OPERATING_CONDITIONS": "OPERATING_CONDITION_CHANGE",
}


# ---------------------------------------------------------------------------
# 1. EXTRACT (build the technical state; untrusted proposal, admitted
#    piece-by-piece by the deterministic validator)
# ---------------------------------------------------------------------------
def extract_technical_state(ctx: CandidateContext,
                            provider: Optional[str] = None
                            ) -> Tuple[Optional[CandidateContext],
                                       Dict[str, Any]]:
    """Build/refresh the technical state on the spec. Returns
    (ctx_with_state_or_None, extraction_record). Transport failure
    returns (None, record) — the caller records BLOCKED_TRANSPORT.
    A spec that already carries a state is NOT re-extracted (the
    mutation loop owns state updates from then on)."""
    if get_technical_state(ctx.spec) is not None:
        return ctx, {"status": "ALREADY_PRESENT",
                     "note": ("spec already carries a technical state; "
                              "the mutation loop owns its updates")}
    problem = ctx.problem or (ctx.spec.get("problem") or {}).get(
        "value") or {}
    rec = propose_technical_state(
        problem, ctx.spec, ctx.evidence_items or [], provider=provider)
    if rec.get("status") != "OK" or rec.get("proposal") is None:
        return None, rec
    state, report = validate_technical_state(
        rec["proposal"], ctx.evidence_items or [], problem)
    spec = attach_technical_state(ctx.spec, state, rec, report)
    return CandidateContext(
        spec=spec, decisive=ctx.decisive, problem=ctx.problem,
        evidence_items=ctx.evidence_items, collision=ctx.collision,
        attack=ctx.attack, run_ctx=dict(ctx.run_ctx,
                                        technical_state=True)), rec


# ---------------------------------------------------------------------------
# 2. DIAGNOSE (deterministic — the analytical evaluator)
# ---------------------------------------------------------------------------
def diagnose_technical(spec: Dict[str, Any]) -> Dict[str, Any]:
    return evaluate_candidate_technically(spec)


# ---------------------------------------------------------------------------
# 3. PROPOSE (LLM — untrusted)
# ---------------------------------------------------------------------------
PROPOSAL_FIELDS = (
    "MUTATION_KIND", "TARGET_PARAM", "NEW_VALUE", "DIRECTION",
    "VALUE_CLASS", "VALUE_SPAN", "VALUE_EVIDENCE_ID", "RATIONALE",
    "MECHANISM_DELTA", "INTERVENTION_DELTA",
)

NEW_RELATION_FIELDS = (
    "REL_CAUSE", "REL_EFFECT", "REL_DIRECTION", "REL_STATEMENT",
    "REL_SPAN", "REL_EVIDENCE_ID",
)


def build_mutation_prompt(ctx: CandidateContext,
                          evaluation: Dict[str, Any],
                          feedback: Optional[List[Dict[str, Any]]] = None
                          ) -> str:
    """The controlled technical-mutation prompt. The LLM sees the
    problem, the technical state (with envelopes and classes), the
    evaluator's NAMED limiting variable + improving direction, and the
    previous attempts' deterministic rejection reasons."""
    lv = evaluation.get("limiting_variable") or {}
    state = get_technical_state(ctx.spec) or {}
    params = state.get("parameters") or []
    mech = ((ctx.spec.get("mechanism") or {}).get("value") or {})
    problem = ctx.problem or (ctx.spec.get("problem") or {}).get(
        "value") or {}

    param_lines = []
    for p in params:
        param_lines.append(
            f"- {p.get('param_id')} [{p.get('category')}] "
            f"value={p.get('value')} ({p.get('value_class')}), "
            f"envelope=[{p.get('range_min')}, {p.get('range_max')}] "
            f"({p.get('range_class')}), "
            f"design_variable={p.get('is_design_variable', True)}, "
            f"role: {str(p.get('role'))[:80]}")
    params_text = "\n".join(param_lines) or "(no parameters declared)"

    rel_lines = [
        f"- {d.get('cause')} --{d.get('direction')}--> "
        f"{d.get('effect')} ({d.get('relation_class')})"
        for d in (state.get("dependencies") or [])]
    rels_text = "\n".join(rel_lines) or "(no dependencies declared)"

    con_lines = [
        f"- {c.get('constraint_id')}: {c.get('target')} "
        f"{c.get('bound')} {c.get('limit')} "
        f"({c.get('limit_class')})"
        for c in (state.get("constraints") or [])]
    cons_text = "\n".join(con_lines) or "(no constraints declared)"

    ev_blocks = []
    for e in (ctx.evidence_items or [])[:4]:
        ev_blocks.append(
            f"[EVIDENCE {e.get('id','')}] "
            f"{(e.get('text') or '')[:1400]}")
    evidence_text = "\n\n".join(ev_blocks) if ev_blocks else \
        "(no custodied evidence — no EXTRACTED claims possible)"

    fb = ""
    if feedback:
        lines = []
        for i, f_rec in enumerate(feedback[-2:], 1):
            reasons = "; ".join(f_rec.get("reasons") or [])[:500]
            lines.append(f"ATTEMPT {i} REJECTED: {reasons}")
        fb = ("\nPREVIOUS ATTEMPTS WERE REJECTED by the deterministic "
              "validator — fix EXACTLY these defects:\n"
              + "\n".join(lines) + "\n")

    lv_block = f"""EVALUATOR DIAGNOSIS (the named technical trigger):
- LIMITING VARIABLE: {lv.get('name')} ({lv.get('param_id')})
- IMPROVING DIRECTION: {lv.get('improving_move')}
- OBJECTIVE: {lv.get('objective_target')} ({lv.get('objective_direction')})
- ENVELOPE (the ONLY permissible bounds for the new value): [{lv.get('envelope')[0] if lv.get('envelope') else None}, {lv.get('envelope')[1] if lv.get('envelope') else None}] ({lv.get('envelope_class')})
- EVALUATOR STATEMENT: {lv.get('statement')}"""

    return f"""You are a technical design engineer. One design variable of this
invention has been identified as the LIMITING VARIABLE by a deterministic
technical evaluator. Produce a CONTROLLED TECHNICAL MUTATION: change that
actual design variable in the evaluator's predicted improving direction.

DEVICE FAILURE:
- Device: {problem.get('device','')}
- Failure mode: {problem.get('failure_mode') or str(problem.get('failure',''))[:200]}
- Constraint: {str(problem.get('constraint',''))[:300]}

CURRENT TECHNICAL STATE:
{params_text}
{rels_text}
{cons_text}

CURRENT CANDIDATE:
- MECHANISM: {str(mech.get('mechanism',''))[:400]}
- INTERVENTION: {str(mech.get('intervention',''))[:400]}

{lv_block}
{fb}
CUSTODIED EVIDENCE (only permissible source for EXTRACTED value claims —
a VALUE_SPAN must be copied character-for-character and contain the
value):
{evidence_text}

Rules:
- MUTATION_KIND must match the target's category: PARAMETERS ->
  PARAMETER_CHANGE, GEOMETRY -> GEOMETRY_CHANGE, MATERIALS ->
  MATERIAL_CHANGE, OPERATING_CONDITIONS -> OPERATING_CONDITION_CHANGE.
  (MECHANISM_CHANGE only adds one new causal relation with an EXTRACTED
  span naming both endpoints.)
- TARGET_PARAM must be exactly the limiting variable's param_id.
- DIRECTION must be exactly the evaluator's improving move
  ({lv.get('improving_move')}).
- NEW_VALUE must lie INSIDE the envelope above (endpoints allowed).
- VALUE_CLASS: MODELLED for a proposed design value (the normal case);
  EXTRACTED only if you copy a span that contains the exact value.
- MECHANISM_DELTA / INTERVENTION_DELTA: one sentence each stating the
  technical change (which variable, which new value, why). They are
  appended to the candidate's mechanism/intervention text so the spec
  prose and the technical state stay consistent.

Respond in EXACTLY this format (each field on ONE line):
MUTATION_KIND: <one of the five kinds>
TARGET_PARAM: <param_id>
NEW_VALUE: <number, or material name for MATERIAL_CHANGE>
DIRECTION: <INCREASE or DECREASE>
VALUE_CLASS: <MODELLED or EXTRACTED>
VALUE_SPAN: <verbatim span, or NONE>
VALUE_EVIDENCE_ID: <evidence id, or NONE>
RATIONALE: <one sentence: the predicted physical effect>
MECHANISM_DELTA: <one sentence>
INTERVENTION_DELTA: <one sentence>
"""


def _parse_fields(content: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (content or "").splitlines():
        m = re.match(r"^([A-Z_]+)\s*:\s*(.*)$", line.strip())
        if m and m.group(1) in PROPOSAL_FIELDS + NEW_RELATION_FIELDS:
            out[m.group(1)] = m.group(2).strip()
    return out


def propose_technical_mutation(ctx: CandidateContext,
                               evaluation: Dict[str, Any],
                               provider: Optional[str] = None,
                               feedback: Optional[List[Dict[str, Any]]] = None
                               ) -> Dict[str, Any]:
    """One LLM mutation proposal attempt (untrusted; validated after)."""
    from .llm_registry import SelectionPolicy, generate
    prompt = build_mutation_prompt(ctx, evaluation, feedback=feedback)
    preferred = [provider] if provider else [
        p for p in ("zai", "gemini", "openrouter", "nvidia", "mistral")]
    res = generate(
        prompt,
        system=("You are a technical design engineer. Respond in the "
                "requested format exactly."),
        policy=SelectionPolicy(
            preferred_providers=preferred, max_preference_fallback=0,
            purpose="TECHNICAL_MUTATION_PROPOSAL"),
        max_tokens=700)
    record: Dict[str, Any] = {
        "proposal_id": f"tmp:{sha256_obj(prompt)[:12]}",
        "provider": res.provider_id, "model": res.model,
        "status": res.status, "prompt_hash": res.prompt_hash,
        "output_hash": res.output_hash,
        "latency_ms": res.latency_ms, "error": res.error,
    }
    if res.ok:
        record["fields"] = _parse_fields(res.content)
        record["raw_content_sha256"] = sha256_obj(res.content or "")
    return record


# ---------------------------------------------------------------------------
# 4. VALIDATE (deterministic — the trust boundary)
# ---------------------------------------------------------------------------
def _param(state: Dict[str, Any], pid: str) -> Optional[Dict[str, Any]]:
    for p in state.get("parameters") or []:
        if p.get("param_id") == pid:
            return p
    return None


def validate_technical_mutation(ctx: CandidateContext,
                                proposal: Dict[str, Any],
                                evaluation: Dict[str, Any]
                                ) -> Dict[str, Any]:
    """The deterministic gates. A technical mutation is VALID only if
    it passes EVERY gate. Every verdict is recorded.

    Gates:
      T0 transport + parse
      T1 kind enum + target is the evaluator's named limiting variable
      T2 target is a design variable with a declared envelope
      T3 direction matches the evaluator's predicted improving move
      T4 new value inside the envelope (inclusive)
      T5 no-op rejection
      T6 value class: EXTRACTED -> span verbatim + value inside span;
         MODELLED -> declared (stays MODELLED on the child)
      T7 own-constraint check: the new value must not violate a
         constraint targeting this parameter
      T8 spec-text sync: the deltas name the changed variable
      T9 MECHANISM_CHANGE: span-backed relation, both endpoints named
      T10 CAD geometry gate (R380): when the parent spec carries a
         PARAMETRIC MODEL whose parameter map binds the target
         parameter, the proposed value must REBUILD into valid
         geometry (dry-run, no exports) — a numerically-legal mutation
         that produces an unbuildable design is not defensible
         (CEO R380: CAD generator -> geometry validates -> KEEP/KILL)
    """
    checks: Dict[str, Any] = {}
    reasons: List[str] = []
    f = proposal.get("fields") or {}
    state = get_technical_state(ctx.spec) or {}

    def _fail(check: str, why: str) -> None:
        checks[check] = False
        reasons.append(f"{check}: {why}")

    def _pass(check: str, detail: Any = True) -> None:
        checks[check] = detail

    lv = evaluation.get("limiting_variable") or {}
    if not lv:
        return {"valid": False, "stage": "NO_LIMITING_VARIABLE",
                "checks": {"limiting_variable_present": False},
                "reasons": ["the evaluator named no limiting variable "
                            "(constraint wall or unquantified)"]}

    if proposal.get("status") != "OK" or not f:
        return {"valid": False, "stage": "TRANSPORT_OR_PARSE",
                "checks": {"transport_ok": proposal.get("status") == "OK",
                           "parsed_fields": bool(f)},
                "reasons": [f"transport status {proposal.get('status')}; "
                            f"parsed {len(f)} fields"]}

    kind = f.get("MUTATION_KIND", "")
    target_pid = f.get("TARGET_PARAM", "")
    direction = f.get("DIRECTION", "")
    new_value_raw = f.get("NEW_VALUE", "")

    # T1: kind + target
    if kind not in TECHNICAL_MUTATION_KINDS:
        _fail("mutation_kind_valid",
              f"MUTATION_KIND {kind!r} must be one of "
              f"{TECHNICAL_MUTATION_KINDS}")
    else:
        _pass("mutation_kind_valid", kind)
    if target_pid != lv.get("param_id"):
        _fail("target_is_limiting_variable",
              f"TARGET_PARAM {target_pid!r} != the evaluator's named "
              f"limiting variable {lv.get('param_id')!r} (off-target "
              f"technical mutations are forbidden — the mutation exists "
              f"only with its named trigger)")
    else:
        _pass("target_is_limiting_variable", target_pid)

    p = _param(state, target_pid)
    if p is None:
        _fail("target_exists", f"{target_pid!r} not declared")
    else:
        _pass("target_exists")
        if not p.get("is_design_variable", True):
            _fail("target_is_design_variable",
                  "the target is an OUTCOME (effect of a declared "
                  "relation) — outcomes are moved by their causes, not "
                  "set directly")
        else:
            _pass("target_is_design_variable")
        expected_kind = CATEGORY_TO_KIND.get(str(p.get("category")))
        if kind != expected_kind and kind != "MECHANISM_CHANGE":
            _fail("kind_matches_category",
                  f"category {p.get('category')!r} requires "
                  f"{expected_kind!r}, got {kind!r}")
        else:
            _pass("kind_matches_category")

    # T2: envelope
    if p is not None:
        rmin, rmax = p.get("range_min"), p.get("range_max")
    else:
        rmin = rmax = None
    if p is not None and (rmin is None and rmax is None):
        _fail("envelope_declared",
              "the target has no declared envelope — unbounded "
              "parameters are immutable (ADR_R379: any 'improvement' "
              "on an unbounded variable would be unconstrained "
              "invention)")
    else:
        _pass("envelope_declared", [rmin, rmax])

    # T3: direction
    if direction != lv.get("improving_move"):
        _fail("direction_matches_evaluator",
              f"DIRECTION {direction!r} != the evaluator's predicted "
              f"improving move {lv.get('improving_move')!r}")
    else:
        _pass("direction_matches_evaluator", direction)

    # T4/T5/T6/T7: the value itself (numeric kinds)
    new_value: Any = None
    if kind in ("PARAMETER_CHANGE", "GEOMETRY_CHANGE",
                "OPERATING_CONDITION_CHANGE"):
        try:
            new_value = float(new_value_raw)
        except (TypeError, ValueError):
            _fail("new_value_numeric",
                  f"NEW_VALUE {new_value_raw!r} is not a number")
        else:
            _pass("new_value_numeric", new_value)
            if rmin is not None and new_value < rmin:
                _fail("value_inside_envelope",
                      f"{new_value} < envelope min {rmin}")
            elif rmax is not None and new_value > rmax:
                _fail("value_inside_envelope",
                      f"{new_value} > envelope max {rmax}")
            else:
                _pass("value_inside_envelope",
                      f"[{rmin}, {rmax}]")
            if p is not None and p.get("value") is not None and \
                    isinstance(p.get("value"), (int, float)) and \
                    new_value == float(p["value"]):
                _fail("mutation_changes_value",
                      f"NEW_VALUE {new_value} equals the current value "
                      f"(a no-op is not a mutation)")
            else:
                _pass("mutation_changes_value")
        # T7: own-constraint check
        for c in state.get("constraints") or []:
            if c.get("target") != target_pid:
                continue
            lim = c.get("limit")
            try:
                lim = float(lim)
            except (TypeError, ValueError):
                continue
            ok = (new_value <= lim) if c.get("bound") == "<=" \
                else (new_value >= lim)
            if not ok:
                _fail("own_constraint_satisfied",
                      f"new value {new_value} violates constraint "
                      f"{c.get('constraint_id')} "
                      f"({target_pid} {c.get('bound')} {lim})")
            else:
                _pass("own_constraint_satisfied",
                      c.get("constraint_id"))
    elif kind == "MATERIAL_CHANGE":
        new_value = new_value_raw
        if not new_value:
            _fail("new_value_present", "empty material name")
        else:
            _pass("new_value_present", new_value[:80])
            if p is not None and str(p.get("value")) == str(new_value):
                _fail("mutation_changes_value",
                      "material unchanged (a no-op is not a mutation)")
            else:
                _pass("mutation_changes_value")
    elif kind == "MECHANISM_CHANGE":
        # T9: span-backed new relation
        span = f.get("REL_SPAN", "")
        ev_id = f.get("REL_EVIDENCE_ID", "")
        cause = f.get("REL_CAUSE", "")
        effect = f.get("REL_EFFECT", "")
        rel_dir = f.get("REL_DIRECTION", "")
        if not span or not ev_id:
            _fail("relation_span_present",
                  "MECHANISM_CHANGE requires REL_SPAN + REL_EVIDENCE_ID "
                  "(a new causal relation must be evidence-backed)")
        else:
            ev_texts = {str(e.get("id")):
                        f"{e.get('title','')}\n{e.get('text') or ''}"
                        for e in (ctx.evidence_items or [])}
            text = ev_texts.get(ev_id)
            if text is None or span not in text:
                _fail("relation_span_verbatim",
                      "the span is not a verbatim substring of the "
                      "cited evidence (Art. VI)")
            else:
                _pass("relation_span_verbatim")
        if cause not in {q.get("param_id") for q in
                         (state.get("parameters") or [])} or \
                effect not in {q.get("param_id") for q in
                               (state.get("parameters") or [])}:
            _fail("relation_endpoints_declared",
                  "REL_CAUSE / REL_EFFECT must be declared param_ids")
        else:
            _pass("relation_endpoints_declared", f"{cause}->{effect}")
        if rel_dir not in ("INCREASES", "DECREASES"):
            _fail("relation_direction_valid", rel_dir)
        else:
            _pass("relation_direction_valid", rel_dir)

    # T6: value class discipline
    if kind in ("PARAMETER_CHANGE", "GEOMETRY_CHANGE",
                "OPERATING_CONDITION_CHANGE", "MATERIAL_CHANGE"):
        vclass = f.get("VALUE_CLASS", "")
        span = f.get("VALUE_SPAN", "")
        ev_id = f.get("VALUE_EVIDENCE_ID", "")
        if vclass not in ("MODELLED", "EXTRACTED"):
            _fail("value_class_declared",
                  f"VALUE_CLASS {vclass!r} must be MODELLED or EXTRACTED")
        else:
            _pass("value_class_declared", vclass)
            if vclass == "EXTRACTED":
                ev_texts = {str(e.get("id")):
                            f"{e.get('title','')}\n{e.get('text') or ''}"
                            for e in (ctx.evidence_items or [])}
                text = ev_texts.get(ev_id)
                if text is None or not span or span not in text:
                    _fail("extracted_value_span_verbatim",
                          "EXTRACTED claim without a verbatim span in "
                          "the cited evidence (Art. VI — forgery)")
                elif new_value is not None:
                    from .technical_state import _value_in_span
                    if not _value_in_span(new_value, span):
                        _fail("extracted_value_in_span",
                              "the claimed value does not appear inside "
                              "its own span")
                    else:
                        _pass("extracted_value_in_span")
                else:
                    _pass("extracted_value_span_verbatim")

    # T8: spec-text sync
    md = f.get("MECHANISM_DELTA", "")
    idl = f.get("INTERVENTION_DELTA", "")
    if not md or not idl:
        _fail("spec_text_sync",
              "MECHANISM_DELTA and INTERVENTION_DELTA are required — "
              "the spec prose must carry the technical change (the "
              "state and the text may not diverge)")
    else:
        synced = any(
            tok in (md + " " + idl).lower()
            for tok in re.findall(r"[a-z]{4,}",
                                  str((p or {}).get("name") or
                                      target_pid).lower())) or \
            target_pid.lower() in (md + " " + idl).lower()
        if synced:
            _pass("spec_text_sync", f"{md[:80]} | {idl[:80]}")
        else:
            _fail("spec_text_sync",
                  "the deltas do not name the changed variable — "
                  "prose/state divergence")

    # T10: CAD geometry gate (R380) — the mutation must rebuild into
    # valid geometry when the target parameter drives the parametric
    # model. MEASURED on the dry-run rebuild's built solid; a breach,
    # impossible dimension, or non-manifold result fails here and the
    # proposal is rejected BEFORE any child is constructed.
    if kind in ("PARAMETER_CHANGE", "GEOMETRY_CHANGE") and \
            new_value is not None and target_pid:
        try:
            from .cad_pipeline import (  # noqa: PLC0415
                get_parametric_model, rebuild_with_mutation)
            parent_model = get_parametric_model(ctx.spec)
            if parent_model is not None and target_pid in \
                    (parent_model.get("parameter_map") or {}):
                _child, geo_rec = rebuild_with_mutation(
                    parent_model, target_pid, new_value,
                    mutation_id="dryrun:T10",
                    reason="T10 dry-run geometry validation",
                    out_dir=None)   # no exports at gate time
                gval = ((_child or {}).get("geometry_validation") or {})
                if geo_rec.get("status") == "UNBOUND_PARAMETER":
                    _pass("t10_geometry_gate",
                          "target not bound to the parametric model")
                elif gval.get("valid"):
                    _pass("t10_geometry_gate", {
                        "rebuilt_model_id": _child.get("model_id"),
                        "measured_wall_mm": (
                            (_child.get("measurements") or {})
                            .get("objects", {}).get(
                                next(iter((_child.get("measurements")
                                           or {}).get("objects", {}))),
                                {}).get("min_wall_thickness_mm")),
                        "checks": {g: c.get("status") for g, c in
                                   (gval.get("checks") or {}).items()},
                    })
                else:
                    _fail("t10_geometry_gate",
                          "the mutated value does not rebuild into "
                          "valid geometry: " + "; ".join(
                              str(r)[:200] for r in
                              (gval.get("reasons") or
                               geo_rec.get("build_errors") or
                               ["unknown geometry failure"])))
            else:
                _pass("t10_geometry_gate",
                      "no parametric model bound to this parameter — "
                      "the state-level gates are decisive")
        except ImportError:
            _pass("t10_geometry_gate",
                  "cad_pipeline unavailable (hermetic state-only mode)")

    return {"valid": not reasons, "stage": "VALIDATION",
            "mutation_kind": kind, "target_param": target_pid,
            "checks": checks, "reasons": reasons,
            "validated_at": utc_now()}


# ---------------------------------------------------------------------------
# 5. APPLY (child technical state + spec sync + causal chain)
# ---------------------------------------------------------------------------
def apply_technical_mutation(ctx: CandidateContext,
                             proposal: Dict[str, Any],
                             validation: Dict[str, Any]
                             ) -> CandidateContext:
    """Construct candidate B: the child's technical state carries the
    changed design variable with its (possibly new) value class, the
    spec prose carries the delta sentences, and the mutation record
    holds the full Art. XXXVIII causal chain with hashes."""
    f = proposal.get("fields") or {}
    parent_spec = ctx.spec
    spec = copy.deepcopy(parent_spec)
    kind = validation["mutation_kind"]
    target_pid = validation["target_param"]

    ts = (spec.get("technical_state") or {})
    state = copy.deepcopy(ts.get("value") or {})
    p = _param(state, target_pid)
    old_value = (p or {}).get("value")
    old_class = (p or {}).get("value_class")

    if p is not None and kind != "MECHANISM_CHANGE":
        try:
            new_value: Any = float(f.get("NEW_VALUE", ""))
        except (TypeError, ValueError):
            new_value = f.get("NEW_VALUE", "")
        p["value"] = new_value
        vclass = f.get("VALUE_CLASS", "MODELLED")
        if vclass == "EXTRACTED" and "extracted_value_in_span" in \
                validation.get("checks", {}) and \
                validation["checks"].get("extracted_value_in_span"):
            p["value_class"] = "EXTRACTED"
            p["value_span"] = f.get("VALUE_SPAN")
            p["value_evidence_id"] = f.get("VALUE_EVIDENCE_ID")
        else:
            p["value_class"] = "MODELLED"
            p["value_span"] = None
            p["value_evidence_id"] = None
        # the mutation history on the parameter (append-only)
        p.setdefault("mutation_history", []).append({
            "from": old_value, "to": new_value,
            "from_class": old_class, "to_class": p["value_class"],
            "mutation_id": None,   # filled below
        })

    if kind == "MECHANISM_CHANGE":
        state.setdefault("dependencies", []).append({
            "relation_id": f"rel:{sha256_obj(f)[:10]}",
            "cause": f.get("REL_CAUSE"), "effect": f.get("REL_EFFECT"),
            "direction": f.get("REL_DIRECTION"),
            "statement": f.get("REL_STATEMENT", ""),
            "relation_class": "EXTRACTED",
            "span": f.get("REL_SPAN"),
            "evidence_id": f.get("REL_EVIDENCE_ID")})

    # spec-text sync: append the deltas to mechanism / intervention
    mv = (spec.get("mechanism") or {}).get("value") or {}
    md = f.get("MECHANISM_DELTA", "")
    idl = f.get("INTERVENTION_DELTA", "")
    if kind != "MECHANISM_CHANGE" and md:
        mv["mechanism"] = (str(mv.get("mechanism") or "") +
                           f" [TECHNICAL MUTATION: {md}]")
    if kind != "MECHANISM_CHANGE" and idl:
        mv["intervention"] = (str(mv.get("intervention") or "") +
                              f" [TECHNICAL MUTATION: {idl}]")
    if kind == "MECHANISM_CHANGE" and md:
        mv["mechanism"] = (str(mv.get("mechanism") or "") +
                           f" [TECHNICAL MUTATION (mechanism relation): "
                           f"{md}]")
    spec["mechanism"]["value"] = mv
    df = (spec.get("distinguishing_features") or {}).get("value") or {}
    if kind != "MECHANISM_CHANGE":
        df["intervention"] = mv.get("intervention")
    spec["distinguishing_features"]["value"] = df

    spec["technical_state"] = dict(
        ts, value=state,
        note="structured technical state (R379): mutated design "
             "variables carry their value class; predictions are model "
             "inferences, never measurements")

    # ---- R380 CAD REBUILD: the child's own parametric model ----------
    # When the parent spec carries a parametric model bound to the
    # target parameter, the child's model is REBUILT from the
    # definition with the new value (never inherited derivatives),
    # exported (STEP/STL/GLB/SVG when an output directory is
    # configured), re-validated, and attached to the child spec. A
    # full-validation failure (e.g. non-manifold STL caught only on
    # export) is recorded on the model — the K7 keep gate consumes it.
    cad_rebuild: Optional[Dict[str, Any]] = None
    if kind in ("PARAMETER_CHANGE", "GEOMETRY_CHANGE") and \
            p is not None and isinstance(p.get("value"), (int, float)) \
            and not isinstance(p.get("value"), bool):
        try:
            from .cad_pipeline import (  # noqa: PLC0415
                attach_parametric_model, geometry_warrants_3d,
                get_parametric_model, rebuild_with_mutation)
            parent_model = get_parametric_model(parent_spec)
            if parent_model is not None and target_pid in \
                    (parent_model.get("parameter_map") or {}):
                out_dir = ((ctx.run_ctx or {}).get("cad_out_dir")
                           or None)
                mut_id_ref = f"tmut:{sha256_obj(f)[:12]}"
                rebuilt, geo_rec = rebuild_with_mutation(
                    parent_model, target_pid,
                    float(p["value"]), mutation_id=mut_id_ref,
                    reason=str(f.get("RATIONALE") or "")[:300],
                    out_dir=out_dir)
                if rebuilt is not None:
                    rebuilt["candidate_id"] = \
                        f"{spec.get('candidate_id') or 'candidate'}"
                    spec = attach_parametric_model(
                        spec, rebuilt, geo_rec,
                        geometry_warrants_3d(parent_spec))
                    cad_rebuild = {
                        "before_model_id": parent_model.get("model_id"),
                        "after_model_id": rebuilt.get("model_id"),
                        "param_id": target_pid,
                        "from_value": old_value,
                        "to_value": p["value"],
                        "rebuild_status": geo_rec.get("status"),
                        "geometry_valid": (rebuilt.get(
                            "geometry_validation") or {}).get(
                            "valid"),
                        "geometry_reasons": (rebuilt.get(
                            "geometry_validation") or {}).get(
                            "reasons") or [],
                        "derived_artifacts": sorted(
                            (rebuilt.get("derived_artifacts")
                             or {}).keys()),
                        "evidence_class": "COMPUTATIONAL_RESULT",
                    }
        except ImportError:
            cad_rebuild = {
                "status": "CAD_PIPELINE_UNAVAILABLE",
                "note": "hermetic state-only mode; geometry gates "
                        "skipped (recorded, never silent)",
            }

    parent_hash = (parent_spec.get("_spec_hash") or sha256_obj(
        {k: v for k, v in parent_spec.items()
         if not k.startswith("_")}))

    mutation_block = {
        "chain": ("ORIGINAL CANDIDATE -> TECHNICAL DIAGNOSIS -> "
                  "TECHNICAL MUTATION -> NEW CANDIDATE"),
        "mutation_id": f"tmut:{sha256_obj(f)[:12]}",
        "mutation_kind": kind,
        "layer": "TECHNICAL (R379 V2) — an actual design variable was "
                 "changed, not the wording",
        "diagnostic_trigger": {
            "evaluator": "analytical_monotone_v1 (deterministic)",
            "limiting_variable": target_pid,
            "improving_direction": f.get("DIRECTION"),
            "evaluation_computation_log":
                (diagnose_technical(parent_spec)
                 .get("computation_log")),
        },
        "proposal_provenance": {
            "proposal_id": proposal.get("proposal_id"),
            "provider": proposal.get("provider"),
            "model": proposal.get("model"),
            "prompt_hash": proposal.get("prompt_hash"),
            "output_hash": proposal.get("output_hash"),
            "llm_is_untrusted_proposer": True,
        },
        "validation": validation,
        "changed_variable": {
            "param_id": target_pid,
            "name": (p or {}).get("name"),
            "from_value": old_value, "to_value": p.get("value"),
            "from_class": old_class, "to_class": (p or {}).get(
                "value_class"),
            "envelope": [(p or {}).get("range_min"),
                         (p or {}).get("range_max")],
            "envelope_class": (p or {}).get("range_class"),
        },
        "spec_text_delta": {"mechanism": md, "intervention": idl},
        "cad_rebuild": cad_rebuild,
        "inherited_negatives": collect_negatives(parent_spec,
                                                 ctx.decisive),
        "parent_spec_hash": parent_hash,
        "reason": f.get("RATIONALE", ""),
        "applied_at": utc_now(),
    }
    # close the param mutation_history reference
    if p is not None and p.get("mutation_history"):
        p["mutation_history"][-1]["mutation_id"] = \
            mutation_block["mutation_id"]

    hist = list((parent_spec.get("_technical_improvement") or {})
                .get("history") or []) + [mutation_block]
    spec["_technical_improvement"] = {
        "parent_spec_hash": parent_hash,
        "mutation": mutation_block,
        "history": hist,
    }
    spec.pop("_spec_hash", None)
    return CandidateContext(
        spec=spec, decisive=ctx.decisive, problem=ctx.problem,
        evidence_items=ctx.evidence_items, collision=ctx.collision,
        attack=ctx.attack, run_ctx=dict(ctx.run_ctx,
                                        technically_mutated=True))


# ---------------------------------------------------------------------------
# 6. RE-EVALUATE (independent; nothing inherited)
# ---------------------------------------------------------------------------
def re_evaluate_technical(child_ctx: CandidateContext,
                          parent_ctx: CandidateContext,
                          collision_mode: str = "REPLAY_CACHE",
                          live_sources: Optional[List[str]] = None
                          ) -> Dict[str, Any]:
    """Full independent re-evaluation of candidate B:
      - the analytical technical evaluation re-runs on the CHILD's own
        technical state (fresh evaluator run — no inherited prediction)
      - the prior-art position is re-adjudicated for the mutated
        profile (REPLAY_CACHE mode against the hash-custodied family
        texts, or LIVE)
      - both quality instruments re-run on the child's own artifacts
    Nothing is inherited from the parent's evaluation."""
    from discovery_fabric.benchmark import candidate_quality as cq
    from discovery_fabric.benchmark import invention_quality as iq
    from .improvement_engine import _measure_ctx

    spec = child_ctx.spec
    out: Dict[str, Any] = {"collision_mode": collision_mode,
                           "re_evaluated_at": utc_now()}

    # --- prior-art re-adjudication (the CEO's EVIDENCE/PRIOR-ART RECHECK)
    if collision_mode == "REPLAY_CACHE":
        adj = re_adjudicate_cached(parent_ctx, child_ctx)
        out["re_adjudication"] = adj
        if adj.get("valid"):
            resolution = adj["resolution"]
            pav = (spec.get("prior_art") or {}).get("value") or {}
            pav["differentiation_resolution"] = resolution
            pav["status"] = resolution["state"]
            spec["prior_art"]["value"] = pav
            nh = (spec.get("novelty_hypothesis") or {}).get("value") \
                or {}
            nh["prior_art_status"] = resolution["state"]
            spec["novelty_hypothesis"]["value"] = nh
            df = (spec.get("distinguishing_features") or {}).get(
                "value") or {}
            df["surviving_differentiators"] = \
                resolution.get("surviving_differentiators")
            spec["distinguishing_features"]["value"] = df
            out["prior_art_status"] = resolution["state"]
        else:
            out["prior_art_status"] = \
                "UNRESOLVED_INSUFFICIENT_EVIDENCE"
            out["re_adjudication_failure"] = adj.get("reason")
    elif collision_mode == "LIVE":
        from discovery_fabric.prior_art_v2.collision_resolution import \
            run_collision
        from .improvement_engine import _mech_fields
        mm = {"intervention": _mech_fields(spec)["intervention"],
              "mechanism": _mech_fields(spec)["mechanism"],
              "expected_effect": _mech_fields(spec)["expected_effect"]}
        collision = run_collision(mm, child_ctx.problem or {},
                                  sources=live_sources)
        out["re_adjudication"] = {
            "mode": "LIVE",
            "resolution": collision["differentiation_resolution"]}
        pav = (spec.get("prior_art") or {}).get("value") or {}
        pav["differentiation_resolution"] = \
            collision["differentiation_resolution"]
        pav["status"] = collision["prior_art_status"]
        spec["prior_art"]["value"] = pav
        nh = (spec.get("novelty_hypothesis") or {}).get("value") or {}
        nh["prior_art_status"] = collision["prior_art_status"]
        spec["novelty_hypothesis"]["value"] = nh
        out["prior_art_status"] = collision["prior_art_status"]
        child_ctx.collision = collision
    else:
        out["prior_art_status"] = "UNRESOLVED_INSUFFICIENT_EVIDENCE"
        out["re_adjudication_failure"] = \
            f"unknown collision_mode {collision_mode!r}"

    spec["_spec_hash"] = sha256_obj(
        {k: v for k, v in spec.items() if not k.startswith("_")})

    # --- fresh technical evaluation on the child's own state
    out["technical"] = evaluate_candidate_technically(spec)

    # --- both instruments on the child's own artifacts
    measured = _measure_ctx(child_ctx)
    out["i_dimensions"] = measured["i_dimensions"]
    out["i_flags"] = measured["i_flags"]
    out["i_average"] = measured["i_average"]
    out["q_dimensions"] = measured["q_dimensions"]
    out["q_average"] = measured["q_average"]
    return out


# ---------------------------------------------------------------------------
# 7. KEEP OR KILL (technical criterion + epistemic invariants)
# ---------------------------------------------------------------------------
def keep_or_kill_technical(parent_ctx: CandidateContext,
                           child_ctx: CandidateContext,
                           parent_eval: Dict[str, Any],
                           child_eval: Dict[str, Any],
                           validation: Dict[str, Any]
                           ) -> Dict[str, Any]:
    """The KEEP requires the CHILD to be predicted-technically-better
    per its OWN independent evaluation — NOT a score increase:
      K1 technical: the changed variable, in the changed direction,
         still has a valid causal path to the objective ON THE CHILD's
         evaluation, and the child's own limiting-variable analysis
         confirms the objective improves in that direction
      K2 constraints: no NEW VIOLATED constraint on the child (vs the
         parent's constraint results); previously UNVERIFIABLE
         constraints may not silently become SATISFIED without new
         numeric evidence — EXTRACTED span-verified values (R379) or
         the child's own geometry-measured values with valid child
         geometry + computation log (R380); MODELLED-only satisfaction
         is laundering
      K3 negatives preserved (CEO rule 10)
      K4 no new structural flags; I1 not regressed (the mutation must
         not de-evidence the mechanism)
      K5 prior-art position not degraded
      K6 value classes: EXTRACTED -> EXTRACTED requires a verified span
         (validated at T6); MODELLED stays MODELLED; no UNKNOWN ->
         value without a recorded class
      K7 R380 geometry: when the mutation touched a model-bound design
         variable, the child's OWN rebuilt parametric model must pass
         geometry validation (measured on the built solid; a render is
         never evidence)
    """
    from .cad_pipeline import get_parametric_model  # noqa: PLC0415

    reasons: List[str] = []
    checks: Dict[str, Any] = {}

    # K1 — the technical criterion (the CEO's rule: not the score)
    p_tech = parent_eval.get("technical") or {}
    c_tech = child_eval.get("technical") or {}
    mut = (child_ctx.spec.get("_technical_improvement") or {}) \
        .get("mutation") or {}
    changed = mut.get("changed_variable") or {}
    target_pid = changed.get("param_id")
    direction = (mut.get("diagnostic_trigger") or {}) \
        .get("improving_direction")

    child_dirs = {d.get("param_id"): d for d in
                  (c_tech.get("improvement_directions") or [])}
    c_dir = child_dirs.get(target_pid)
    if c_dir is None:
        checks["technical_objective"] = (
            "the changed variable no longer maps to the objective on "
            "the child's evaluation")
        reasons.append("technical_objective: the child's own "
                       "evaluation no longer connects the changed "
                       "variable to the objective")
    elif c_dir.get("improving_move") != direction:
        checks["technical_objective"] = (
            f"child evaluation says the improving move is "
            f"{c_dir.get('improving_move')}, the mutation moved "
            f"{direction}")
        reasons.append("technical_objective: the child's independent "
                       "evaluation contradicts the mutation direction")
    elif c_dir.get("blocked_by"):
        checks["technical_objective"] = (
            f"improving direction confirmed but now constraint-blocked: "
            f"{c_dir.get('blocked_by')}")
        reasons.append("technical_objective: the child's evaluation "
                       "finds the move now violates a constraint")
    else:
        checks["technical_objective"] = (
            f"CONFIRMED on the child's independent evaluation: "
            f"{target_pid} {direction} improves objective "
            f"{(c_tech.get('objective') or {}).get('target')} "
            f"({(c_tech.get('objective') or {}).get('direction')}) "
            f"with constraints preserved")

    # K2 — constraints
    p_crs = {c.get("constraint_id"): c for c in
             (p_tech.get("constraint_results") or [])}
    new_violations = []
    laundered = []
    for c in (c_tech.get("constraint_results") or []):
        cid = c.get("constraint_id")
        p_cr = p_crs.get(cid)
        if c.get("status") == "VIOLATED" and \
                (p_cr or {}).get("status") != "VIOLATED":
            new_violations.append(cid)
        if (p_cr or {}).get("status") == "UNVERIFIABLE" and \
                c.get("status") == "SATISFIED":
            # the target's value appeared where the parent had none:
            # legitimate ONLY with NEW NUMERIC EVIDENCE — either
            # (i) EXTRACTED: a span-verified evidence value (the R379
            #  path), or
            # (ii) GEOMETRY_MEASURED (R380): the child's OWN rebuilt
            #  parametric model MEASURES the target on the built solid
            #  with VALID geometry and a computation log (the CEO R380
            #  loop: CAD generator -> geometry validates -> evaluator).
            #  A MODELLED state value alone still may not SATISFY a
            #  constraint the parent could not check (Art. XXV).
            if c.get("value_source") == \
                    "GEOMETRY_MEASURED_ON_BUILT_SOLID":
                child_pm = get_parametric_model(child_ctx.spec)
                child_gv = (child_pm or {}).get(
                    "geometry_validation") or {}
                has_log = bool(((child_pm or {}).get("measurements")
                                or {}).get("computation_log"))
                if not (child_gv.get("valid") and has_log):
                    laundered.append(
                        f"{cid}: UNVERIFIABLE -> SATISFIED via a "
                        f"claimed geometry measurement WITHOUT valid "
                        f"child geometry or a computation log — "
                        f"forged measurement (Art. VI)")
            else:
                tgt = c.get("target")
                state = get_technical_state(child_ctx.spec) or {}
                tp = _param(state, str(tgt))
                vclass = (tp or {}).get("value_class")
                if vclass != "EXTRACTED":
                    laundered.append(
                        f"{cid}: UNVERIFIABLE -> SATISFIED via a "
                        f"{vclass} value (model-declared satisfaction is "
                        f"certainty laundering — Art. XXV)")
    checks["no_new_constraint_violation"] = not new_violations
    if new_violations:
        reasons.append(f"new constraint violations on the child: "
                       f"{new_violations}")
    checks["no_constraint_laundering"] = not laundered
    if laundered:
        reasons.append("; ".join(laundered))

    # K3 — negatives preserved
    preserved, lost = negatives_preserved(
        collect_negatives(parent_ctx.spec, parent_ctx.decisive),
        collect_negatives(child_ctx.spec, child_ctx.decisive))
    checks["negatives_preserved"] = preserved
    if lost:
        reasons.append(f"mutation would erase parent negatives: {lost}")

    # K4 — instruments: no new flags, I1 not regressed
    p_i = parent_eval.get("i_dimensions") or {}
    c_i = child_eval.get("i_dimensions") or {}
    new_flags = []
    if not (parent_eval.get("i_flags") or {}).get(
            "underived_mechanism") and \
            (child_eval.get("i_flags") or {}).get("underived_mechanism"):
        new_flags.append("underived_mechanism")
    if not (parent_eval.get("i_flags") or {}).get(
            "recombination_only") and \
            (child_eval.get("i_flags") or {}).get("recombination_only"):
        new_flags.append("recombination_only")
    checks["no_new_structural_flags"] = not new_flags
    if new_flags:
        reasons.append(f"mutation introduced new structural flags: "
                       f"{new_flags}")
    p_i1 = (p_i.get("I1_MECHANISM_EVIDENCE_DERIVATION") or {}) \
        .get("score")
    c_i1 = (c_i.get("I1_MECHANISM_EVIDENCE_DERIVATION") or {}) \
        .get("score")
    # K4 (refined after the live w8/t03 measurement): the technical
    # layer's keep gate protects the mechanism's STRUCTURAL
    # evidence-derivation status — it must not flip the mechanism from
    # derived to underived (crossing the declared SPAN_DERIVATION floor
    # downward). It does NOT gate on I1 numeric movement: a technical
    # mutation intentionally adds design vocabulary (the invention
    # content), which dilutes the wording precision the I1 diagnostic
    # measures; the CEO's R379 item 8 is explicit ("the goal is NOT to
    # maximize I1-I5; they are diagnostics that guide improvement" —
    # and the epistemic layer owns the wording). The FIRST live
    # positive-path run (t03 pedicle screw) measured the
    # any-regression form REJECTING a mutation whose technical
    # objective was CONFIRMED on all other gates (I1 0.125 -> 0.071,
    # both already below the floor) — a conflation of the two layers.
    from .improvement_engine import IMPROVEMENT_THRESHOLDS as _IT
    floor = _IT["SPAN_DERIVATION_MIN"]["value"]
    derived_to_underived = (
        isinstance(p_i1, (int, float)) and
        isinstance(c_i1, (int, float)) and
        p_i1 >= floor and c_i1 < floor)
    checks["i1_structural_floor"] = {
        "parent": p_i1, "child": c_i1, "floor": floor,
        "crossed_downward": derived_to_underived,
        "note": ("numeric I1 movement is recorded, never gated here "
                 "(CEO R379 item 8); the floor crossing IS gated — a "
                 "mutation may not flip a derived mechanism to "
                 "underived"),
    }
    if derived_to_underived:
        reasons.append(f"the technical mutation flipped the mechanism "
                       f"from derived to underived (I1 {p_i1} -> "
                       f"{c_i1}, floor {floor})")

    # K5 — prior-art position
    p_status = parent_eval.get("prior_art_status")
    c_status = child_eval.get("prior_art_status")
    degraded = (str(p_status or "").startswith("RESOLVED")
                and not str(c_status or "").startswith("RESOLVED"))
    checks["prior_art_position_not_degraded"] = not degraded
    if degraded:
        reasons.append(f"prior-art position degraded {p_status} -> "
                       f"{c_status}")
    anticipated = str(c_status or "") == "RESOLVED_ANTICIPATED"
    if anticipated:
        reasons.append("the mutated candidate walked INTO prior art "
                       "(RESOLVED_ANTICIPATED on re-adjudication)")

    # K6 — value-class provenance (the span was verified at T6; the
    # class is re-stated here so the decision record is self-describing)
    to_class = changed.get("to_class")
    if to_class == "MODELLED":
        checks["value_class_provenance"] = (
            "MODELLED design value — declared, never promoted "
            "(Art. XXVIII); the improvement attribution carries the class")
    else:
        checks["value_class_provenance"] = str(to_class)

    # K7 — R380 geometry: when the child carries a rebuilt parametric
    # model (the mutation touched a model-bound design variable), the
    # CHILD's OWN geometry validation must be VALID. The rebuild is
    # measured on the built solid (never on the parent's, never on a
    # render); a full-validation failure detected only at apply time
    # (e.g. a non-manifold STL derivative) rejects here.
    child_model = get_parametric_model(child_ctx.spec)
    cad_mut = (mut.get("cad_rebuild") or {})
    if child_model is not None and cad_mut:
        c_gv = child_model.get("geometry_validation") or {}
        if c_gv.get("valid"):
            checks["geometry_valid_on_child"] = {
                "model_id": child_model.get("model_id"),
                "validator": c_gv.get("validator"),
                "measured_wall_mm": (
                    (child_model.get("measurements") or {})
                    .get("objects", {}).get(
                        next(iter((child_model.get("measurements")
                                   or {}).get("objects", {}))),
                        {}).get("min_wall_thickness_mm")),
                "note": "geometry validated on the child's OWN rebuilt "
                        "solid (COMPUTATIONAL_RESULT, Art. XXXVIII)",
            }
        else:
            checks["geometry_valid_on_child"] = \
                c_gv.get("reasons") or "geometry invalid on child"
            reasons.append(
                "geometry_valid_on_child: the child's rebuilt "
                "parametric model FAILED geometry validation — "
                + "; ".join(str(r)[:160] for r in
                            (c_gv.get("reasons") or
                             ["unknown"])[:3]))
    else:
        checks["geometry_valid_on_child"] = (
            "no parametric model bound to the changed variable — "
            "the state-level gates are decisive")

    action = "KEEP" if not reasons else "REJECT_MUTATION"
    return {"action": action, "checks": checks, "reasons": reasons,
            "decided_at": utc_now()}


# ---------------------------------------------------------------------------
# 8. IMPROVEMENT ATTRIBUTION (CEO item 6)
# ---------------------------------------------------------------------------
def build_attribution(child_ctx: CandidateContext,
                      child_eval: Dict[str, Any],
                      decision: Dict[str, Any]) -> Dict[str, Any]:
    mut = (child_ctx.spec.get("_technical_improvement") or {}) \
        .get("mutation") or {}
    changed = mut.get("changed_variable") or {}
    c_tech = child_eval.get("technical") or {}
    state = get_technical_state(child_ctx.spec) or {}
    rel_chain = []
    pid = changed.get("param_id")
    # walk the causal path from the changed variable to the objective
    obj = (c_tech.get("objective") or {})
    for d in (state.get("dependencies") or []):
        if d.get("cause") == pid or d.get("effect") == \
                obj.get("target"):
            rel_chain.append(
                f"{d.get('cause')} --{d.get('direction')}--> "
                f"{d.get('effect')} ({d.get('relation_class')}): "
                f"{str(d.get('statement'))[:100]}")
    return {
        "artifact": "TECHNICAL_IMPROVEMENT_ATTRIBUTION",
        "technical_mechanism": " | ".join(rel_chain) or
        f"direct: {pid} is the objective target",
        "changed_variable": pid,
        "changed_variable_name": changed.get("name"),
        "direction": (mut.get("diagnostic_trigger") or {})
        .get("improving_direction"),
        "from_value": changed.get("from_value"),
        "to_value": changed.get("to_value"),
        "value_class": changed.get("to_class"),
        "envelope": changed.get("envelope"),
        "envelope_class": changed.get("envelope_class"),
        "predicted_effect": (
            f"{pid} {changed.get('to_value')} is predicted to move "
            f"objective {obj.get('target')} ({obj.get('direction')}) "
            f"in the improving sense"),
        "evaluated_result": (decision.get("checks") or {}).get(
            "technical_objective"),
        "constraints_result": [
            f"{c.get('constraint_id')}: {c.get('status')}"
            for c in (c_tech.get("constraint_results") or [])],
        "evidence_class": (
            "AI_INFERENCE (rank 3) — a direction-level prediction of "
            "the declared analytical model over the structured "
            "technical state. NOT a measurement, NOT a physical "
            "observation (Art. XXVIII / XXXVIII). The value class of "
            "the changed variable is recorded above; MODELLED design "
            "values are invention content, never evidence."),
        "mutation_id": mut.get("mutation_id"),
        "recorded_at": utc_now(),
    }


# ---------------------------------------------------------------------------
# 9. THE LOOP
# ---------------------------------------------------------------------------
def improve_candidate_technical(ctx: CandidateContext,
                                max_iterations: Optional[int] = None,
                                max_proposals: Optional[int] = None,
                                collision_mode: str = "REPLAY_CACHE",
                                live_sources: Optional[List[str]] = None,
                                provider: Optional[str] = None,
                                ) -> Dict[str, Any]:
    """The CEO V2 loop driver. Returns the TECHNICAL_IMPROVEMENT_LEDGER.

    Outcome vocabulary (honest, exhaustive):
      TECHNICALLY_IMPROVED           >= 1 KEEP (attribution recorded)
      TECHNICAL_UNQUANTIFIED         no quantifiable technical content
                                      in the candidate's own evidence
                                      (honest measured gap — the 🟡
                                      state; NOT a kill)
      TECHNICALLY_HEALTHY_NO_MUTATION no limiting variable found
      KILLED_NO_DEFENSIBLE_TECHNICAL_MUTATION   no valid proposal
      KILLED_GEOMETRY_INVALID                  every proposal rebuilt
                                      to invalid geometry at the R380
                                      T10 CAD gate (measured on the
                                      built solid)
      KILLED_NO_IMPROVING_TECHNICAL_MUTATION    valid mutations did not
                                      improve (measured)
      KILLED_CONSTRAINT_WALL         improving directions all blocked
      TECHNICAL_IMPROVEMENT_BLOCKED_TRANSPORT   LLM unavailable (never
                                      a kill — Art. XXV)
      IMPROVEMENT_NOT_RUN_CANDIDATE_KILLED      Art. XX guard
    """
    max_iterations = (max_iterations if max_iterations is not None else
                      TECHNICAL_THRESHOLDS["MAX_ITERATIONS_DEFAULT"]
                      ["value"])
    max_proposals = (max_proposals if max_proposals is not None else
                     TECHNICAL_THRESHOLDS[
                         "MAX_PROPOSALS_PER_ITERATION"]["value"])

    ledger: Dict[str, Any] = {
        "ledger": ("TECHNICAL_IMPROVEMENT_LEDGER (R379 TECHNICAL "
                   "IMPROVEMENT ENGINE V2)"),
        "version": TECHNICAL_LEDGER_VERSION,
        "loop": ("CANDIDATE -> TECHNICAL DIAGNOSIS (limiting variable + "
                 "direction) -> TECHNICAL MUTATION (actual design "
                 "variable) -> INDEPENDENT TECHNICAL EVALUATION -> "
                 "EVIDENCE/PRIOR-ART RECHECK -> KEEP/KILL -> SECOND "
                 "IMPROVEMENT"),
        "collision_mode": collision_mode,
        "live_sources": live_sources,
        "thresholds": TECHNICAL_THRESHOLDS,
        "mutation_kinds_live": TECHNICAL_MUTATION_KINDS,
        "mutation_kinds_reserved": {
            kind: "needs a structural/control search space at a higher "
                  "fidelity tier (ADR_R379)"
            for kind in RESERVED_MUTATION_KINDS},
        "keep_criterion": (
            "the child's OWN independent technical evaluation must "
            "confirm the objective improves in the mutation direction "
            "with constraints preserved — a score increase is NEVER "
            "sufficient (CEO R379 item 4/8)"),
        "started_at": utc_now(),
        "iterations": [],
        "outcome": None,
        "outcome_reason": "",
    }

    # Art. XX guard
    if isinstance(ctx.attack, dict) and ctx.attack.get("overall") \
            == "KILLED":
        ledger["outcome"] = "IMPROVEMENT_NOT_RUN_CANDIDATE_KILLED"
        ledger["outcome_reason"] = (
            "the engineering attack already KILLED this candidate's "
            "premise; technical improvement strengthens designs, not "
            "premises (Art. XX)")
        ledger["finished_at"] = utc_now()
        return ledger

    # ---- 1. extraction ---------------------------------------------------
    current, extraction_rec = extract_technical_state(
        ctx, provider=provider)
    if current is None:
        if extraction_rec.get("status") == "PROVIDER_UNAVAILABLE":
            ledger["outcome"] = "TECHNICAL_IMPROVEMENT_BLOCKED_TRANSPORT"
            ledger["outcome_reason"] = (
                "technical-state extraction could not run: LLM "
                "transport unavailable — infrastructure, not a "
                "research verdict (Art. XXV); the candidate stands")
        else:
            ledger["outcome"] = "TECHNICAL_IMPROVEMENT_BLOCKED_TRANSPORT"
            ledger["outcome_reason"] = (
                f"technical-state extraction failed: "
                f"{extraction_rec.get('status')} / "
                f"{extraction_rec.get('error') or 'parse failure'} — "
                f"recorded, never a kill")
        ledger["extraction"] = extraction_rec
        ledger["finished_at"] = utc_now()
        return ledger
    ctx = current
    ledger["extraction"] = extraction_rec
    # the measured shape of the state (admitted counts travel ON the
    # ledger so persisted ledgers carry the quantification measurement
    # even when the candidate is not improved)
    st = get_technical_state(ctx.spec) or {}
    ledger["technical_state_counts"] = \
        (st.get("extraction") or {}).get("admitted_counts") or {}

    baseline_eval = _full_eval(ctx, collision_mode, live_sources)
    ledger["baseline"] = _public_eval(baseline_eval)
    parent_eval = baseline_eval

    # fidelity escalation record (CEO item 7 — honest)
    b_status = (baseline_eval.get("technical") or {}).get("status")
    ledger["fidelity_escalation"] = {
        "current_tier": "STRUCTURED_CONSTRAINT (analytical_monotone_v1)",
        "deciding_question": ("does a design-variable change improve "
                              "the objective within constraints?"),
        "resolved_at_current_tier": b_status == "QUANTIFIED",
        "escalation_needed": b_status != "QUANTIFIED",
        "next_tier_available": False,
        "note": ("higher tiers (NUMERICAL_SOLVER / SIMULATION / "
                 "NEURAL_OPERATOR) are contract-reserved and not "
                 "registered; escalation is recorded, never faked at "
                 "the current tier"),
    }

    if b_status == "UNQUANTIFIED":
        ledger["outcome"] = "TECHNICAL_UNQUANTIFIED"
        state = get_technical_state(ctx.spec) or {}
        counts = ((state.get("extraction") or {})
                  .get("admitted_counts") or {})
        ledger["outcome_reason"] = (
            f"the candidate's own custodied evidence yields no "
            f"quantifiable technical objective+leverage (admitted: "
            f"{json.dumps(counts)}); the technical layer cannot engage "
            f"— an honest measured gap (the 🟡 state), not a kill and "
            f"not a failure")
        ledger["finished_at"] = utc_now()
        ledger["current_ctx"] = ctx
        return ledger

    for iteration in range(1, max_iterations + 1):
        diag = diagnose_technical(ctx.spec)
        lv = diag.get("limiting_variable")
        it_record: Dict[str, Any] = {
            "iteration": iteration,
            "diagnosis": {
                "status": diag.get("status"),
                "limiting_variable": lv,
                "improvement_directions_summary": [
                    {"param_id": d.get("param_id"),
                     "improving_move": d.get("improving_move"),
                     "mutable": d.get("mutable"),
                     "blocked": bool(d.get("blocked_by"))}
                    for d in (diag.get("improvement_directions") or [])],
                "constraint_results": diag.get("constraint_results"),
            },
            "proposals": [],
            "mutation_attempts_extra": [],
        }

        # constraint-wall kill: improving directions exist but all are
        # blocked (or no movable design variable at all)
        dirs = diag.get("improvement_directions") or []
        movable = [d for d in dirs if d.get("mutable")
                   and d.get("is_design_variable")]
        blocked = [d for d in movable if d.get("blocked_by")]
        if lv is None:
            if dirs and not movable:
                ledger["outcome"] = "TECHNICAL_UNQUANTIFIED"
                ledger["outcome_reason"] = (
                    "improving directions exist but no movable DESIGN "
                    "variable (outcomes are not set directly; unbounded "
                    "parameters are immutable — ADR_R379)")
            elif movable and len(blocked) == len(movable) and movable:
                ledger["outcome"] = "KILLED_CONSTRAINT_WALL"
                ledger["outcome_reason"] = (
                    f"every movable improving direction is blocked by "
                    f"declared constraints: "
                    + "; ".join(
                        f"{d.get('param_id')} {d.get('improving_move')} "
                        f"blocked by "
                        f"{[b.get('constraint_id') for b in d.get('blocked_by')]}"
                        for d in blocked)
                    + ". No defensible technical improvement exists. "
                      "Candidate killed.")
            else:
                ledger["outcome"] = "TECHNICALLY_HEALTHY_NO_MUTATION"
                ledger["outcome_reason"] = (
                    "the technical evaluation found no limiting "
                    "variable to attack at this tier")
            ledger["iterations"].append(it_record)
            break

        # ---- proposals (untrusted) with directional feedback loop ----
        valid_proposal: Optional[Dict[str, Any]] = None
        valid_validation: Optional[Dict[str, Any]] = None
        transport_blocked = False
        rejections: List[Dict[str, Any]] = []
        for attempt in range(1, max_proposals + 1):
            proposal = propose_technical_mutation(
                ctx, diag, provider=provider,
                feedback=[r.get("feedback_record") or r
                          for r in rejections])
            if proposal.get("status") != "OK":
                transport_blocked = transport_blocked or \
                    proposal.get("status") == "PROVIDER_UNAVAILABLE"
                it_record["proposals"].append(
                    {k: v for k, v in proposal.items() if k != "fields"})
                continue
            validation = validate_technical_mutation(ctx, proposal, diag)
            if not validation["valid"]:
                rejections.append({
                    "feedback_record": {
                        "reasons": validation["reasons"],
                        "mutation_kind": validation.get(
                            "mutation_kind")}})
            it_record["proposals"].append({
                "proposal_id": proposal.get("proposal_id"),
                "provider": proposal.get("provider"),
                "model": proposal.get("model"),
                "prompt_hash": proposal.get("prompt_hash"),
                "output_hash": proposal.get("output_hash"),
                "fields": proposal.get("fields"),
                "validation": validation})
            if validation["valid"]:
                valid_proposal, valid_validation = proposal, validation
                break

        if valid_proposal is None:
            if transport_blocked:
                ledger["outcome"] = \
                    "TECHNICAL_IMPROVEMENT_BLOCKED_TRANSPORT"
                ledger["outcome_reason"] = (
                    f"iteration {iteration}: all mutation proposals hit "
                    f"provider unavailability — infrastructure, not a "
                    f"research verdict (Art. XXV); the candidate stands")
            else:
                # R380: if EVERY proposal died specifically at the T10
                # CAD geometry gate, the kill is a GEOMETRY kill — the
                # candidate's improving directions are all
                # geometrically unbuildable (measured, not asserted)
                all_geometry = bool(it_record["proposals"]) and all(
                    any("t10_geometry_gate" in str(r)
                        for r in (p.get("validation") or {})
                        .get("reasons") or [])
                    for p in it_record["proposals"]
                    if (p.get("validation") or {}).get("reasons"))
                if all_geometry:
                    ledger["outcome"] = "KILLED_GEOMETRY_INVALID"
                    ledger["outcome_reason"] = (
                        f"iteration {iteration}: "
                        f"{len(it_record['proposals'])} mutation "
                        f"proposal(s) proposed; every one rebuilt to "
                        f"INVALID GEOMETRY (T10 CAD gate — measured on "
                        f"the built solid). The improving directions "
                        f"are geometrically unbuildable at this design "
                        f"point. No defensible technical improvement "
                        f"exists. Candidate killed.")
                else:
                    ledger["outcome"] = \
                        "KILLED_NO_DEFENSIBLE_TECHNICAL_MUTATION"
                    ledger["outcome_reason"] = (
                        f"iteration {iteration}: "
                        f"{len(it_record['proposals'])} technical "
                        f"mutation proposal(s) generated; none passed "
                        f"deterministic validation. No defensible "
                        f"technical improvement exists. Candidate "
                        f"killed.")
            ledger["iterations"].append(it_record)
            break

        # ---- apply + independent re-evaluate + keep-or-kill -----------
        child = apply_technical_mutation(ctx, valid_proposal,
                                         valid_validation)
        re_eval = re_evaluate_technical(
            child, ctx, collision_mode=collision_mode,
            live_sources=live_sources)
        decision = keep_or_kill_technical(
            ctx, child, parent_eval, re_eval, valid_validation)
        attribution = build_attribution(child, re_eval, decision) \
            if decision["action"] == "KEEP" else None
        it_record["mutation_applied"] = (child.spec.get(
            "_technical_improvement") or {}).get("mutation")
        it_record["re_evaluation"] = _public_eval(re_eval)
        it_record["decision"] = decision
        it_record["attribution"] = attribution
        ledger["iterations"].append(it_record)

        if decision["action"] == "KEEP":
            ctx = child
            parent_eval = re_eval
            continue

        # REJECT: the parent stands; try the NEXT valid proposal within
        # the budget (the "no defensible mutation" verdict must mean
        # the budget was actually spent — same measured rule as R378)
        found_next = False
        rejections.append({
            "feedback_record": {
                "reasons": decision["reasons"] or [
                    (decision.get("checks") or {}).get(
                        "technical_objective")
                    or "no predicted technical improvement"],
                "mutation_kind": valid_validation.get("mutation_kind")}})
        while len(it_record["proposals"]) < max_proposals:
            proposal = propose_technical_mutation(
                ctx, diag, provider=provider,
                feedback=[r.get("feedback_record") or r
                          for r in rejections])
            if proposal.get("status") != "OK":
                transport_blocked = transport_blocked or \
                    proposal.get("status") == "PROVIDER_UNAVAILABLE"
                it_record["proposals"].append(
                    {k: v for k, v in proposal.items() if k != "fields"})
                break
            validation = validate_technical_mutation(ctx, proposal, diag)
            if not validation["valid"]:
                rejections.append({
                    "feedback_record": {
                        "reasons": validation["reasons"],
                        "mutation_kind": validation.get(
                            "mutation_kind")}})
            it_record["proposals"].append({
                "proposal_id": proposal.get("proposal_id"),
                "provider": proposal.get("provider"),
                "model": proposal.get("model"),
                "prompt_hash": proposal.get("prompt_hash"),
                "output_hash": proposal.get("output_hash"),
                "fields": proposal.get("fields"),
                "validation": validation})
            if validation["valid"]:
                child = apply_technical_mutation(
                    ctx, proposal, validation)
                re_eval = re_evaluate_technical(
                    child, ctx, collision_mode=collision_mode,
                    live_sources=live_sources)
                decision = keep_or_kill_technical(
                    ctx, child, parent_eval, re_eval, validation)
                attribution = build_attribution(
                    child, re_eval, decision) \
                    if decision["action"] == "KEEP" else None
                it_record["mutation_attempts_extra"].append({
                    "mutation_applied": (child.spec.get(
                        "_technical_improvement") or {}).get("mutation"),
                    "re_evaluation": _public_eval(re_eval),
                    "decision": decision,
                    "attribution": attribution})
                if decision["action"] == "KEEP":
                    ctx = child
                    parent_eval = re_eval
                    found_next = True
                    it_record["decision"] = decision
                    it_record["attribution"] = attribution
                    break
        if found_next:
            continue

        ledger["outcome"] = "KILLED_NO_IMPROVING_TECHNICAL_MUTATION"
        ledger["outcome_reason"] = (
            f"iteration {iteration}: validated technical mutation(s) "
            f"were applied and independently re-evaluated; the child "
            f"never satisfied the technical keep criterion ("
            + "; ".join(str(a.get("decision", {}).get("checks", {})
                           .get("technical_objective"))
                        for a in
                        ([{"decision": decision}] +
                         it_record.get("mutation_attempts_extra", [])))
            + "). No defensible technical improvement exists. "
              "Candidate killed.")
        break
    else:
        ledger["outcome"] = "TECHNICALLY_IMPROVED" if any(
            (it.get("decision") or {}).get("action") == "KEEP"
            for it in ledger["iterations"]) else \
            "KILLED_NO_IMPROVING_TECHNICAL_MUTATION"

    final_eval = _full_eval(ctx, collision_mode, live_sources) \
        if ledger.get("outcome") not in (
            "TECHNICAL_UNQUANTIFIED",) else baseline_eval
    ledger["final"] = _public_eval(final_eval)
    ledger["current_ctx"] = ctx
    ledger["outcome_summary"] = {
        "baseline_status": (baseline_eval.get("technical") or {})
        .get("status"),
        "final_status": (final_eval.get("technical") or {}).get("status"),
        "baseline_i_average": (baseline_eval.get("i_average")),
        "final_i_average": (final_eval.get("i_average")),
        "baseline_prior_art": baseline_eval.get("prior_art_status"),
        "final_prior_art": final_eval.get("prior_art_status"),
        "iterations_run": len(ledger["iterations"]),
        "keeps": sum(1 for it in ledger["iterations"]
                     if (it.get("decision") or {}).get("action")
                     == "KEEP"),
        "attributions": [
            it.get("attribution") for it in ledger["iterations"]
            if it.get("attribution")],
    }
    ledger["finished_at"] = utc_now()
    return ledger


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _full_eval(ctx: CandidateContext, collision_mode: str,
               live_sources: Optional[List[str]]) -> Dict[str, Any]:
    """Baseline evaluation: technical + instruments + the candidate's
    OWN recorded prior-art state (no re-adjudication — the baseline is
    the parent's standing position; the CHILD is the one re-checked)."""
    from .improvement_engine import _measure_ctx
    out = {
        "technical": evaluate_candidate_technically(ctx.spec),
        "re_evaluated_at": utc_now(),
        "collision_mode": collision_mode,
    }
    measured = _measure_ctx(ctx)
    out.update({k: measured[k] for k in (
        "i_dimensions", "i_flags", "i_average", "q_dimensions",
        "q_average", "prior_art_status")})
    return out


def _public_eval(ev: Dict[str, Any]) -> Dict[str, Any]:
    """Ledger-safe view of an evaluation (the technical evaluation is
    already public-shaped; instruments summarized)."""
    return {
        "technical": {
            "status": (ev.get("technical") or {}).get("status"),
            "objective": (ev.get("technical") or {}).get("objective"),
            "limiting_variable": (ev.get("technical") or {})
            .get("limiting_variable"),
            "constraint_results": (ev.get("technical") or {})
            .get("constraint_results"),
            "uncertainty": (ev.get("technical") or {}).get("uncertainty"),
            "computation_log": (ev.get("technical") or {})
            .get("computation_log"),
        },
        "i_dimensions": ev.get("i_dimensions"),
        "i_flags": ev.get("i_flags"),
        "i_average": ev.get("i_average"),
        "q_average": ev.get("q_average"),
        "prior_art_status": ev.get("prior_art_status"),
    }

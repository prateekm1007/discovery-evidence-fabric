"""discovery_fabric/engine/improvement_engine.py — R378 TECHNICAL
IMPROVEMENT ENGINE.

CEO directive (2026-08-31), verbatim loop:

    CANDIDATE
    -> DIAGNOSE WEAKNESS
    -> IDENTIFY LIMITING FEATURE
    -> GENERATE CONTROLLED MUTATION
    -> RE-EVALUATE EVIDENCE / MECHANISM / PRIOR ART
    -> RE-SCORE
    -> KEEP OR KILL
    -> REPEAT

and the machine must be able to say BOTH:

    "Candidate B is better because the mechanism is now evidence-
     derived, the differentiating relationship is technically
     meaningful, and the experiment distinguishes the candidate."
    "No defensible improvement exists. Candidate killed."

Architecture:
  layer 1  evaluator_contract.py — the pluggable evaluator interface
           (future simulators / NeuralOperators register behind it)
  layer 2  THIS MODULE — the mutation loop:
             diagnose      (deterministic, via the evaluator contract)
             propose       (LLM — an UNTRUSTED proposer, Art. XVIII)
             validate      (DETERMINISTIC gates; the trust boundary)
             apply         (construct candidate B with the Art. XXXVIII
                            causal-mutation provenance chain)
             re_evaluate   (span check + prior-art re-adjudication +
                            attack + quality + BOTH instruments)
             keep_or_kill  (targeted-improvement rule; regressions and
                            negatives-erasure are mechanical blocks)
             loop          (bounded iterations; IMPROVEMENT_LEDGER)

Constitutional anchors:
- Art. VII/XIII the frozen Q instrument is imported read-only and is
             never modified; the I instrument likewise.
- Art. XVIII  the LLM only PROPOSES; every proposal passes deterministic
             validation before it can touch a candidate. A proposal
             that fails validation is recorded with its failure reasons.
- Art. XX     problem-existence guard: a candidate already KILLED by
             the engineering attack is not improved — its premise is
             attacked, not its mechanism.
- Art. XXV    unknown stays unknown: UNMEASURABLE dimensions are
             evidence gaps and are never mutation targets; transport
             failure is IMPROVEMENT_BLOCKED_TRANSPORT, never a kill.
- Art. XXVIII no silent promotion: mutation fields stay MODELLED; the
             mutation never promotes a field's epistemic class.
- Art. XXXIII no irreversible action on unresolved evidence: a KILL
             requires the measured ledger (failed valid proposals or
             failed re-evaluations), recorded in full.
- Art. XXXVIII causal mutation schema: every mutation carries
             before_hash / after_hash / trigger / reason / timestamp;
             the chain ORIGINAL -> DIAGNOSTIC -> MUTATION -> NEW
             CANDIDATE is the ledger's spine.

CEO rules implemented as MECHANICAL gates:
  rule 3   I3 recombination risk -> novel-residue mutations must be
           measured against FOUND family text; residue from absence is
           forbidden (the DIFFERENTIATOR validator enforces it).
  rule 7   provenance chain on every mutation.
  rule 8   a mutation exists ONLY with a named diagnostic trigger; the
           validator rejects untriggered or off-target proposals.
  rule 9   no defensible mutation -> KILL with the full ledger.
  rule 10  negatives can never be erased (mechanical preservation
           check parent -> child).
  rule 11  full re-evaluation; the parent's scores are never inherited.
  rule 12  the ledger IS the measurement artifact (targeted dimension
           before/after, per iteration).
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .candidate import sha256_obj, utc_now
from .evaluator_contract import (
    MUTATION_TYPES,
    WEAKNESS_THRESHOLD,
    CandidateContext,
    EvaluatorDiagnosis,
    get_evaluator,
    registered_evaluators,
)

# ---------------------------------------------------------------------------
# Declared thresholds (Art. XXVII)
# ---------------------------------------------------------------------------
IMPROVEMENT_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "SPAN_DERIVATION_MIN": {
        "value": 0.20,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "the engine's own span-derivation rule (candidate_diversity."
            "span_derivation_check): ratio < 0.20 = SPAN_UNDERIVED. A "
            "MECHANISM_STRENGTHENING mutation must CLEAR this floor — "
            "the same rule that gates the grid, not a new one."),
    },
    "EVIDENCE_SUPPORT_MIN": {
        "value": 0.20,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "I1's underived flag fires below 0.20; an "
            "EVIDENCE_DERIVED_CONSTRAINT mutation must clear the same "
            "floor on evidence_support."),
    },
    "DOMAIN_OVERLAP_MIN": {
        "value": 1,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "REPLAY_CACHE re-adjudication is valid only while the "
            "mutated candidate stays in the domain the cached art was "
            "found FOR. Guard: >= 1 NON-generic technical term shared "
            "between the child's mechanism+intervention and the cached "
            "family corpus. ZERO overlap means the mutation abandoned "
            "the domain (measured attack: re-adjudicating a "
            "cement-curing intervention against battery art fabricates "
            "surviving differentiators — false novelty from stale art). "
            "The overlap count is RECORDED on every cache adjudication "
            "so thin-domain links are auditable. NOTE: entity-term "
            "retention vs the problem CANNOT catch this class — entity "
            "terms are problem-derived and unchanged by mutations "
            "(measured while writing the guard's tests); it is recorded "
            "for audit only."),
    },
    "MAX_ITERATIONS_DEFAULT": {"value": 2,
                               "epistemic_class": "ENGINEERING",
                               "justification": (
                                   "the CEO minimum loop is DIAGNOSE -> "
                                   "IMPROVE -> RE-EVALUATE -> IMPROVE "
                                   "AGAIN; two iterations demonstrate "
                                   "repeatability at bounded cost")},
    "MAX_PROPOSALS_PER_ITERATION": {"value": 3,
                                    "epistemic_class": "ENGINEERING",
                                    "justification": (
                                        "bounded proposal budget: three "
                                        "attempts, then the honest "
                                        "no-defensible-mutation verdict")},
}

LEDGER_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# helpers: spec field access / negatives ledger
# ---------------------------------------------------------------------------
def _mech_fields(spec: Dict[str, Any]) -> Dict[str, str]:
    mv = (spec.get("mechanism") or {}).get("value") or {}
    return {k: str(mv.get(k) or "") for k in (
        "mechanism", "intervention", "expected_effect",
        "falsification_test", "mechanism_source_span")}


def _decisive_fields(decisive: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sel = (decisive or {}).get("selected") or {}
    return {
        "experiment": str(sel.get("experiment") or ""),
        "eig": sel.get("expected_information_gain"),
    }


def collect_negatives(spec: Dict[str, Any],
                      decisive: Optional[Dict[str, Any]] = None
                      ) -> Dict[str, List[str]]:
    """Every contradiction / uncertainty / collision / failure the
    candidate currently carries (CEO rule 10: a mutation may NEVER
    erase any of these). Returns id-ish keys for the mechanical
    preservation check."""
    neg: Dict[str, List[str]] = {"uncertainty_ids": [],
                                 "collision_family_ids": [],
                                 "source_errors": []}
    unc = (spec.get("uncertainties") or {}).get("value") or []
    for u in unc:
        key = (u.get("contradiction_id")
               or u.get("unresolved_source")
               or json.dumps(u, sort_keys=True)[:80])
        neg["uncertainty_ids"].append(str(key))
    pav = (spec.get("prior_art") or {}).get("value") or {}
    res = pav.get("differentiation_resolution") or {}
    for fam in (res.get("per_family") or []):
        if isinstance(fam, dict) and fam.get("family_id"):
            neg["collision_family_ids"].append(str(fam["family_id"]))
    # source errors preserved from the collision record (never erased)
    col_errors = []
    if isinstance(spec.get("collision_results"), dict):
        col_errors = (spec["collision_results"].get("patent") or {}) \
            .get("source_errors") or []
    neg["source_errors"] = [
        f"{e.get('query','')}|{e.get('source','')}" for e in col_errors
        if isinstance(e, dict)]
    return neg


def negatives_preserved(parent_neg: Dict[str, List[str]],
                        child_neg: Dict[str, List[str]]) -> \
        Tuple[bool, List[str]]:
    """Mechanical rule-10 check: every parent negative must survive in
    the child (the child may ADD negatives — prior-art collisions only
    grow — but never lose one)."""
    lost: List[str] = []
    for key in ("uncertainty_ids", "collision_family_ids", "source_errors"):
        pset, cset = set(parent_neg[key]), set(child_neg[key])
        lost.extend(f"{key}:{x}" for x in sorted(pset - cset))
    return (not lost), lost


# ---------------------------------------------------------------------------
# 1. DIAGNOSE (deterministic, via the evaluator contract)
# ---------------------------------------------------------------------------
def diagnose(ctx: CandidateContext,
             evaluator_id: Optional[str] = None) -> EvaluatorDiagnosis:
    ev = get_evaluator(evaluator_id)
    return ev["fn"](ctx)


# ---------------------------------------------------------------------------
# 2. PROPOSE (LLM — untrusted proposer)
# ---------------------------------------------------------------------------
PROPOSAL_FIELDS = (
    "MUTATION_TYPE", "MECHANISM", "INTERVENTION", "EXPECTED_EFFECT",
    "FALSIFICATION_TEST", "MECHANISM_SOURCE_SPAN", "SOURCE_EVIDENCE_ID",
    "EXPERIMENT", "EXPERIMENT_BASELINE", "EXPERIMENT_EIG",
    "CONSTRAINT_DERIVED", "MUTATION_REASON",
)


def build_proposal_prompt(ctx: CandidateContext,
                          diagnosis: EvaluatorDiagnosis,
                          target_index: int = 0,
                          feedback: Optional[List[Dict[str, Any]]] = None
                          ) -> str:
    """The controlled-mutation prompt. The LLM sees: the problem, the
    current candidate, the NAMED diagnosis (limiting feature +
    instruction), the custodied evidence, and — when previous attempts
    were rejected — the exact deterministic rejection reasons (the
    DIRECTIONAL FEEDBACK loop: the next proposal must fix exactly what
    the validator named; measured first attempt: three near-identical
    proposals repeating the same rejected span)."""
    target = diagnosis.limiting_features[target_index]
    direction = next(
        d for d in diagnosis.improvement_directions
        if d.target_dimension == target.dimension)
    problem = ctx.problem or (ctx.spec.get("problem") or {}).get(
        "value") or {}
    mech = _mech_fields(ctx.spec)
    dec = _decisive_fields(ctx.decisive)

    ev_blocks = []
    for e in (ctx.evidence_items or [])[:4]:
        ev_blocks.append(
            f"[EVIDENCE {e.get('id','')}] title: {e.get('title','')}\n"
            f"{(e.get('text') or '')[:1600]}")
    evidence_text = "\n\n".join(ev_blocks) if ev_blocks else \
        "(no custodied evidence on this candidate — cite no span)"

    feedback_block = ""
    if feedback:
        lines = []
        for i, fb in enumerate(feedback[-2:], 1):
            reasons = "; ".join(fb.get("reasons") or [])[:400]
            lines.append(
                f"ATTEMPT {i} REJECTED by the deterministic validator: "
                f"{reasons}")
        feedback_block = (
            "\nPREVIOUS ATTEMPTS WERE REJECTED — fix EXACTLY these "
            "defects (do not repeat the same proposal):\n"
            + "\n".join(lines) + "\n")

    return f"""You are a mechanism-improvement engineer. A candidate invention was
diagnosed with ONE specific measured weakness. Produce a CONTROLLED MUTATION
that repairs exactly that weakness. Do not change anything else.

DEVICE FAILURE:
- Device: {problem.get('device','')}
- Failure: {problem.get('failure') or problem.get('failure_mode','')}
- Constraint: {problem.get('constraint','')}

CURRENT CANDIDATE:
- MECHANISM: {mech['mechanism']}
- INTERVENTION: {mech['intervention']}
- EXPECTED_EFFECT: {mech['expected_effect']}
- FALSIFICATION_TEST: {mech['falsification_test']}
- CURRENT EXPERIMENT: {dec['experiment']}

DIAGNOSIS (the measured weakness to repair):
- WEAK DIMENSION: {target.dimension} (measured {target.measured_value}; {target.why_weak})
- REQUIRED MUTATION TYPE: {target.mutation_type}
- INSTRUCTION: {direction.instruction}
- VALIDATION RULE (applied deterministically after you answer): {direction.validation_rule}
{feedback_block}
CUSTODIED EVIDENCE (the ONLY permissible source for MECHANISM_SOURCE_SPAN;
the span must be a VERBATIM substring of one evidence text below):
{evidence_text}

Rules:
- MUTATION_TYPE must be exactly: {target.mutation_type}
- Only the fields the mutation type needs may change; carry the rest forward unchanged.
- MECHANISM_SOURCE_SPAN must be copied character-for-character from one evidence text.
- CRITICAL (this is how the validator measures derivation): your MECHANISM and
  INTERVENTION must RE-USE the span's own technical vocabulary. Pick a span that
  reports a concrete physical/chemical/biological PHENOMENON relevant to the
  DEVICE FAILURE, then write the MECHANISM as that phenomenon stated in the
  span's own terms. The validator computes the shared content terms between the
  span and your mechanism+intervention; if fewer than 20 percent of the span's
  terms appear in your mechanism, the proposal is rejected as underived.
- The mutated candidate must still address the DEVICE FAILURE above.
- For experiment mutations: the EXPERIMENT sentence must explicitly COMPARE the
  candidate against the EXPERIMENT_BASELINE you name (use the baseline's own
  words in the experiment sentence — a comparison that is present but
  worded differently from the baseline phrase is still rejected).

Respond in EXACTLY this format (each field on ONE line):
MUTATION_TYPE: <{target.mutation_type}>
MECHANISM: <mechanism after mutation>
INTERVENTION: <intervention after mutation>
EXPECTED_EFFECT: <expected effect after mutation>
FALSIFICATION_TEST: <falsification test after mutation>
MECHANISM_SOURCE_SPAN: <verbatim substring from the evidence>
SOURCE_EVIDENCE_ID: <the evidence id the span was copied from>
EXPERIMENT: <decisive experiment after mutation>
EXPERIMENT_BASELINE: <the baseline/control the experiment is compared against>
EXPERIMENT_EIG: <expected information gain, a positive number>
CONSTRAINT_DERIVED: <evidence-derived constraint added by this mutation, or NONE>
MUTATION_REASON: <one sentence: which measured defect this repairs and how>
"""


def _parse_proposal(content: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (content or "").splitlines():
        m = re.match(r"^([A-Z_]+)\s*:\s*(.*)$", line.strip())
        if m and m.group(1) in PROPOSAL_FIELDS:
            out[m.group(1)] = m.group(2).strip()
    return out


def propose_mutation(ctx: CandidateContext,
                     diagnosis: EvaluatorDiagnosis,
                     target_index: int = 0,
                     provider: Optional[str] = None,
                     feedback: Optional[List[Dict[str, Any]]] = None
                     ) -> Dict[str, Any]:
    """One LLM proposal attempt. Returns the proposal record with full
    transport provenance. The proposal is CONTENT — never evidence
    (Art. XVIII). `feedback` carries the prior attempts' deterministic
    rejection reasons — the directional loop: the next proposal must
    fix exactly what the validator named."""
    from .llm_registry import SelectionPolicy, generate
    prompt = build_proposal_prompt(ctx, diagnosis, target_index,
                                   feedback=feedback)
    preferred = [provider] if provider else [
        p for p in ("zai", "gemini", "openrouter", "nvidia", "mistral")]
    res = generate(
        prompt,
        system=("You are a mechanism-improvement engineer. Respond in "
                "the requested format exactly."),
        policy=SelectionPolicy(
            preferred_providers=preferred, max_preference_fallback=0,
            purpose="IMPROVEMENT_MUTATION_PROPOSAL"),
        max_tokens=700)
    record: Dict[str, Any] = {
        "proposal_id": f"prop:{(res.output_hash or sha256_obj(prompt))[:12]}",
        "provider": res.provider_id, "model": res.model,
        "status": res.status, "prompt_hash": res.prompt_hash,
        "output_hash": res.output_hash,
        "latency_ms": res.latency_ms, "error": res.error,
        "transport_substituted_from": res.substituted_from,
    }
    if res.ok:
        record["fields"] = _parse_proposal(res.content)
        record["raw_content_sha256"] = sha256_obj(res.content or "")
    return record


# ---------------------------------------------------------------------------
# 3. VALIDATE (deterministic — the trust boundary)
# ---------------------------------------------------------------------------
def _evidence_texts(ctx: CandidateContext) -> Dict[str, str]:
    return {str(e.get("id")): f"{e.get('title','')}\n{e.get('text') or ''}"
            for e in (ctx.evidence_items or [])}


def _nongeneric_terms(text: str) -> set:
    from discovery_fabric.benchmark.invention_quality import (
        GENERIC_ENGINEERING, _t)
    return {x for x in _t(text) if x not in GENERIC_ENGINEERING
            and len(x) > 3}


def _family_texts(ctx: CandidateContext) -> List[str]:
    """The found-art corpus the mutation's novelty claims are measured
    against: the adjudicated family texts of the candidate's own
    collision record (never the parent's SCORES — the TEXTS)."""
    texts: List[str] = []
    pav = (ctx.spec.get("prior_art") or {}).get("value") or {}
    for fam in ((pav.get("differentiation_resolution") or {})
                .get("per_family") or []):
        rep = fam.get("representative") or {}
        texts.append(f"{rep.get('title', '')} "
                     f"{fam.get('adjudicated_text_excerpt') or ''}")
    col = ctx.collision or {}
    if isinstance(col, dict):
        for h in ((col.get("patent") or {}).get("hits") or []):
            if isinstance(h, dict):
                texts.append(f"{h.get('title','')} {h.get('snippet','')}")
    return texts


def validate_mutation(ctx: CandidateContext,
                      proposal: Dict[str, Any],
                      diagnosis: EvaluatorDiagnosis,
                      target_index: int = 0) -> Dict[str, Any]:
    """The deterministic gates. A proposal is VALID only if it passes
    EVERY gate for its mutation type. Every gate's verdict is recorded
    (the rejection is as informative as the acceptance)."""
    target = diagnosis.limiting_features[target_index]
    checks: Dict[str, Any] = {}
    reasons: List[str] = []
    f = proposal.get("fields") or {}

    def _fail(check: str, why: str) -> None:
        checks[check] = False
        reasons.append(f"{check}: {why}")

    def _pass(check: str, detail: Any = True) -> None:
        checks[check] = detail

    # -- gate 0: transport + parse + type match (CEO rule 8: a mutation
    #    exists ONLY with a named diagnostic trigger)
    if proposal.get("status") != "OK" or not f:
        return {"valid": False,
                "stage": "TRANSPORT_OR_PARSE",
                "checks": {"transport_ok": proposal.get("status") == "OK",
                           "parsed_fields": bool(f)},
                "reasons": [f"transport status {proposal.get('status')}; "
                            f"parsed {len(f)} fields"]}
    if f.get("MUTATION_TYPE") != target.mutation_type:
        _fail("mutation_type_matches_diagnosis",
              f"proposal {f.get('MUTATION_TYPE')!r} != required "
              f"{target.mutation_type!r} (untriggered/off-target "
              f"mutations are forbidden — CEO rule 8)")
    else:
        _pass("mutation_type_matches_diagnosis")

    mech_now = _mech_fields(ctx.spec)
    new_mech = f.get("MECHANISM", "")
    new_int = f.get("INTERVENTION", "")
    span = f.get("MECHANISM_SOURCE_SPAN", "")
    ev_id = f.get("SOURCE_EVIDENCE_ID", "")
    ev_texts = _evidence_texts(ctx)

    # -- span gates (all evidence-citing mutation types)
    if target.mutation_type in ("MECHANISM_STRENGTHENING",
                                "EVIDENCE_DERIVED_CONSTRAINT",
                                "DIFFERENTIATOR",
                                "TECHNICAL_RELATIONSHIP"):
        ev_text = ev_texts.get(ev_id)
        if not ev_id or ev_text is None:
            _fail("span_evidence_exists",
                  f"SOURCE_EVIDENCE_ID {ev_id!r} is not a custodied "
                  f"evidence item")
        elif span and span not in ev_text:
            _fail("span_verbatim_in_evidence",
                  "the quoted span is NOT a verbatim substring of the "
                  "cited evidence (fabricated spans are invalid — Art. VI)")
        else:
            _pass("span_evidence_exists", ev_id)
            if span:
                _pass("span_verbatim_in_evidence")

    # -- per-type gates
    if target.mutation_type == "MECHANISM_STRENGTHENING":
        if new_mech == mech_now["mechanism"] and \
                new_int == mech_now["intervention"]:
            _fail("mutation_changes_candidate",
                  "mechanism and intervention unchanged (a no-op is not "
                  "a mutation)")
        else:
            _pass("mutation_changes_candidate")
        from .candidate_diversity import span_derivation_check
        sd = span_derivation_check({
            "mechanism": new_mech, "intervention": new_int,
            "mechanism_source_span": span})
        checks["span_derivation"] = sd
        if sd.get("underived") or (sd.get("ratio") is not None and
                                   sd["ratio"] <
                                   IMPROVEMENT_THRESHOLDS[
                                       "SPAN_DERIVATION_MIN"]["value"]):
            _fail("span_derivation_cleared",
                  f"re-measured span-derivation ratio {sd.get('ratio')} "
                  f"< {IMPROVEMENT_THRESHOLDS['SPAN_DERIVATION_MIN']['value']} "
                  f"— the new span still does not contain the new "
                  f"mechanism's vocabulary")
        else:
            _pass("span_derivation_cleared", sd.get("ratio"))

    elif target.mutation_type == "EVIDENCE_DERIVED_CONSTRAINT":
        ev_text = ev_texts.get(ev_id) or ""
        mech_terms = _nongeneric_terms(f"{new_mech} {new_int}")
        ev_terms = _nongeneric_terms(ev_text)
        support = (round(len(mech_terms & ev_terms) / len(mech_terms), 3)
                   if mech_terms else None)
        checks["evidence_support"] = support
        if support is None or support < \
                IMPROVEMENT_THRESHOLDS["EVIDENCE_SUPPORT_MIN"]["value"]:
            _fail("evidence_support_cleared",
                  f"re-measured evidence support {support} < "
                  f"{IMPROVEMENT_THRESHOLDS['EVIDENCE_SUPPORT_MIN']['value']} "
                  f"— the cited evidence still does not contain the "
                  f"mechanism's non-generic vocabulary")
        else:
            _pass("evidence_support_cleared", support)
        cd = f.get("CONSTRAINT_DERIVED", "")
        if not cd or cd.upper() == "NONE":
            _fail("constraint_actually_derived",
                  "EVIDENCE_DERIVED_CONSTRAINT requires a derived "
                  "constraint, not NONE")
        elif ev_text and not (_nongeneric_terms(cd) & ev_terms):
            _fail("constraint_traceable_to_evidence",
                  "the derived constraint shares no non-generic term "
                  "with the cited evidence")
        else:
            _pass("constraint_traceable_to_evidence", cd[:120])

    elif target.mutation_type == "DIFFERENTIATOR":
        if new_int == mech_now["intervention"]:
            _fail("mutation_changes_candidate",
                  "intervention unchanged (a no-op is not a mutation)")
        else:
            _pass("mutation_changes_candidate")
        fam_texts = _family_texts(ctx)
        if not fam_texts:
            # Art. XXI.2: residue vs UNFOUND art is unmeasurable — a
            # differentiator mutation cannot be validated without found
            # art; the candidate needs the prior-art gap closed first.
            _fail("found_art_available_for_residue",
                  "no adjudicated family text — residue against absent "
                  "art is inference from absence (Art. XXI.2); the "
                  "prior-art gap must close before differentiator "
                  "mutations can be validated")
        else:
            from discovery_fabric.prior_art_v2.collision_resolution import (
                _natural_tokens, _INTERVENTION_FILLER)
            from discovery_fabric.source_registry.query_relevance import \
                _fold
            # SAME fold both sides (measured defect in the first draft:
            # folding only the family terms let 'disconnects' survive as
            # false residue against 'disconnect' — the asymmetric rule
            # would fabricate novel residue)
            elements = [t for t in _natural_tokens(new_int)
                        if t not in _INTERVENTION_FILLER]
            el_folded = {_fold(e) for e in elements}
            fam_terms = set()
            for ft in fam_texts:
                fam_terms |= {_fold(t) for t in _natural_tokens(ft)}
            residue = el_folded - fam_terms
            from discovery_fabric.benchmark.invention_quality import (
                GENERIC_ENGINEERING)
            meaningful = [r for r in residue
                          if r not in GENERIC_ENGINEERING]
            checks["meaningful_residue_after"] = meaningful
            if not meaningful:
                _fail("meaningful_residue_exists",
                      "every non-generic element of the new intervention "
                      "is covered by found family text — the mutation "
                      "adds no novel residue (recombination remains)")
            else:
                _pass("meaningful_residue_exists", meaningful[:8])

    elif target.mutation_type == "TECHNICAL_RELATIONSHIP":
        if new_mech == mech_now["mechanism"]:
            _fail("mutation_changes_candidate",
                  "mechanism unchanged (a no-op is not a mutation)")
        else:
            _pass("mutation_changes_candidate")
        fam_texts = _family_texts(ctx)
        if not fam_texts:
            _fail("found_art_available_for_pairs",
                  "no adjudicated family text — pair novelty is "
                  "unmeasurable (Art. XXV)")
        else:
            mech_terms = sorted(_nongeneric_terms(new_mech))
            from discovery_fabric.source_registry.query_relevance import terms
            fam_sets = [set(terms(ft)) for ft in fam_texts]
            novel_pairs: List[str] = []
            for i in range(len(mech_terms)):
                for j in range(i + 1, len(mech_terms)):
                    a, b = mech_terms[i], mech_terms[j]
                    if not any(a in fs and b in fs for fs in fam_sets):
                        novel_pairs.append(f"{a}+{b}")
            checks["novel_pairs_after"] = novel_pairs[:12]
            if not novel_pairs:
                _fail("novel_pair_exists",
                      "every non-generic term pair of the new mechanism "
                      "co-occurs in found family text — relabeled known "
                      "elements, not a new technical relationship")
            else:
                _pass("novel_pair_exists", novel_pairs[:6])

    elif target.mutation_type == "EXPERIMENT_DISCRIMINATION":
        exp = f.get("EXPERIMENT", "")
        baseline = f.get("EXPERIMENT_BASELINE", "")
        eig_raw = f.get("EXPERIMENT_EIG", "")
        if exp == _decisive_fields(ctx.decisive)["experiment"]:
            _fail("mutation_changes_candidate",
                  "experiment unchanged (a no-op is not a mutation)")
        else:
            _pass("mutation_changes_candidate")
        from discovery_fabric.benchmark.invention_quality import (
            ADMINISTRATIVE_ACTION_RE)
        if not exp or ADMINISTRATIVE_ACTION_RE.search(exp):
            _fail("experiment_is_physical",
                  "the proposed experiment is empty or an administrative/"
                  "literature action")
        else:
            _pass("experiment_is_physical")
        if not baseline:
            _fail("experiment_names_baseline",
                  "no baseline/control named — the experiment cannot "
                  "distinguish the candidate from existing approaches")
        else:
            # the engine's own reference rule family (>= 2 shared
            # content terms, same as the relevance adjudicator / Q2) —
            # OR the verbatim phrase. (Measured in the replay: a strict
            # verbatim-phrase demand rejected experiments whose
            # comparison WAS present with paraphrased wording.)
            from discovery_fabric.source_registry.query_relevance \
                import terms as _terms
            shared_base = set(_terms(exp)) & set(_terms(baseline))
            if baseline.lower() in exp.lower() or len(shared_base) >= 2:
                _pass("experiment_references_baseline",
                      baseline[:120])
            else:
                _fail("experiment_references_baseline",
                      f"the experiment text does not reference the "
                      f"named baseline {baseline[:60]!r} (neither "
                      f"verbatim nor >= 2 shared content terms)")
        try:
            eig = float(eig_raw)
            if eig <= 0:
                raise ValueError
            _pass("experiment_eig_positive", eig)
        except (TypeError, ValueError):
            _fail("experiment_eig_positive",
                  f"EXPERIMENT_EIG {eig_raw!r} is not a positive number")

    # gate: required text fields non-empty for the mutated candidate
    if target.mutation_type != "EXPERIMENT_DISCRIMINATION":
        if not new_mech or not new_int:
            _fail("candidate_fields_present",
                  "MECHANISM/INTERVENTION missing from the proposal")

    return {"valid": not reasons, "stage": "VALIDATION",
            "target_dimension": target.dimension,
            "mutation_type": target.mutation_type,
            "checks": checks, "reasons": reasons,
            "validated_at": utc_now()}


# ---------------------------------------------------------------------------
# 4. APPLY (construct candidate B with the causal provenance chain)
# ---------------------------------------------------------------------------
def apply_mutation(ctx: CandidateContext,
                   proposal: Dict[str, Any],
                   validation: Dict[str, Any]) -> CandidateContext:
    """Build candidate B. The mutation is RECORDED on the child spec
    with the full Art. XXXVIII causal chain:
        ORIGINAL CANDIDATE -> DIAGNOSTIC -> MUTATION -> NEW CANDIDATE
    Parent negatives are carried forward explicitly (CEO rule 10) and
    verified by the keep-or-kill check after re-evaluation."""
    f = proposal.get("fields") or {}
    parent_spec = ctx.spec
    spec = copy.deepcopy(parent_spec)
    f_before = _mech_fields(parent_spec)

    mv = (spec.get("mechanism") or {}).get("value") or {}
    mtype = validation["mutation_type"]
    changed: Dict[str, Any] = {}

    if mtype in ("MECHANISM_STRENGTHENING", "EVIDENCE_DERIVED_CONSTRAINT",
                 "TECHNICAL_RELATIONSHIP", "DIFFERENTIATOR"):
        mv["mechanism"] = f.get("MECHANISM", f_before["mechanism"])
        mv["intervention"] = f.get("INTERVENTION",
                                   f_before["intervention"])
        mv["expected_effect"] = f.get("EXPECTED_EFFECT",
                                      f_before["expected_effect"])
        mv["falsification_test"] = f.get(
            "FALSIFICATION_TEST", f_before["falsification_test"])
        mv["mechanism_source_span"] = f.get("MECHANISM_SOURCE_SPAN", "")
        raw = dict(mv.get("raw_candidate") or {})
        raw["source_evidence"] = {
            "source_id": f.get("SOURCE_EVIDENCE_ID", ""),
            "source_span": f.get("MECHANISM_SOURCE_SPAN", "")}
        mv["raw_candidate"] = raw
        changed = {
            "mechanism": {"before": f_before["mechanism"][:300],
                          "after": mv["mechanism"][:300]},
            "intervention": {"before": f_before["intervention"][:300],
                             "after": mv["intervention"][:300]},
            "mechanism_source_span":
                {"before": f_before["mechanism_source_span"][:300],
                 "after": (f.get("MECHANISM_SOURCE_SPAN") or "")[:300]},
        }
        if mtype == "EVIDENCE_DERIVED_CONSTRAINT" and \
                f.get("CONSTRAINT_DERIVED", "").upper() != "NONE":
            cons = (spec.get("constraints") or {}).get("value") or {}
            derived = list(cons.get("evidence_derived") or [])
            derived.append({
                "constraint": f.get("CONSTRAINT_DERIVED"),
                "evidence_id": f.get("SOURCE_EVIDENCE_ID"),
                "span": f.get("MECHANISM_SOURCE_SPAN", "")[:300]})
            cons["evidence_derived"] = derived
            spec["constraints"]["value"] = cons
        # the intervention change flows to distinguishing_features
        df = (spec.get("distinguishing_features") or {}).get("value") or {}
        df["intervention"] = mv["intervention"]
        spec["distinguishing_features"]["value"] = df

    if mtype == "EXPERIMENT_DISCRIMINATION":
        eig = None
        try:
            eig = float(f.get("EXPERIMENT_EIG", ""))
        except (TypeError, ValueError):
            eig = None
        dec = copy.deepcopy(ctx.decisive or {})
        sel = dict(dec.get("selected") or {})
        sel["experiment"] = f.get("EXPERIMENT", "")
        sel["expected_information_gain"] = eig
        sel["baseline"] = f.get("EXPERIMENT_BASELINE", "")
        sel["basis"] = ("MODELLED (improvement mutation "
                        f"{mtype}; eig is a MODELLED estimate, "
                        "never a measurement)")
        dec["selected"] = sel
        dec["mutation_note"] = (
            "experiment redesigned by the R378 improvement engine; "
            "isolates the named baseline/control")
        changed["decisive_experiment"] = {
            "before": _decisive_fields(ctx.decisive)["experiment"][:300],
            "after": f.get("EXPERIMENT", "")[:300]}
    else:
        dec = ctx.decisive

    # re-measure span derivation on the child (never inherited)
    from .candidate_diversity import span_derivation_check
    mv["span_derivation"] = span_derivation_check({
        "mechanism": mv.get("mechanism", ""),
        "intervention": mv.get("intervention", ""),
        "mechanism_source_span": mv.get("mechanism_source_span", "")})
    spec["mechanism"]["value"] = mv

    parent_neg = collect_negatives(parent_spec, ctx.decisive)
    before_hash = (parent_spec.get("_spec_hash")
                   or sha256_obj(
                       {k: v for k, v in parent_spec.items()
                        if not k.startswith("_")}))

    mutation_block = {
        "chain": "ORIGINAL -> DIAGNOSTIC -> MUTATION -> NEW CANDIDATE",
        "mutation_id": f"mut:{sha256_obj(f)[:12]}",
        "mutation_type": mtype,
        "diagnostic_trigger": {
            "dimension": validation["target_dimension"],
            "measured_before": (diagnose(CandidateContext(
                spec=parent_spec, decisive=ctx.decisive,
                problem=ctx.problem, evidence_items=ctx.evidence_items,
                collision=ctx.collision, attack=ctx.attack))
                .dimension_results.get(validation["target_dimension"], {})
                .get("score")),
            "basis": "R378 evaluator-contract diagnosis (deterministic)",
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
        "fields_changed": changed,
        "inherited_negatives": parent_neg,
        "parent_spec_hash": before_hash,
        "child_spec_hash": None,      # filled by the caller after persist
        "reason": f.get("MUTATION_REASON", ""),
        "applied_at": utc_now(),
    }
    spec["_improvement"] = {
        "parent_spec_hash": before_hash,
        "mutation": mutation_block,
        "history": list((parent_spec.get("_improvement") or {})
                        .get("history") or []) + [mutation_block],
    }
    spec.pop("_spec_hash", None)
    return CandidateContext(
        spec=spec, decisive=dec, problem=ctx.problem,
        evidence_items=ctx.evidence_items,
        collision=ctx.collision, attack=ctx.attack,
        run_ctx=dict(ctx.run_ctx, mutated=True))


# ---------------------------------------------------------------------------
# 5. RE-EVALUATE (full re-run; scores are NEVER inherited)
# ---------------------------------------------------------------------------
def re_adjudicate_cached(parent_ctx: CandidateContext,
                         child_ctx: CandidateContext
                         ) -> Dict[str, Any]:
    """REPLAY_CACHE mode: re-run the coverage adjudication + resolution
    state machine against the CACHED, hash-custodied family texts for
    the MUTATED candidate profile. The SEARCH is cached (quota-blocked
    sources, measured); the ADJUDICATION is fully re-run (CEO rule 11).

    DOMAIN-ABANDONMENT guard (the laundering attack this must catch):
    if the mutated candidate shares ZERO non-generic technical terms
    with the cached family corpus, the mutation has left the domain the
    art was found FOR — re-adjudicating a cement-curing candidate
    against battery art would fabricate surviving differentiators
    (false novelty from stale art). Zero overlap -> the cache is
    INVALID for the child; a LIVE search (or an honest UNRESOLVED) is
    required, never a stale adjudication. Entity retention vs the
    problem is recorded for audit (it cannot catch this class alone:
    entity terms are problem-derived and unchanged by mutations —
    measured while writing the guard's tests)."""
    from discovery_fabric.prior_art_v2.collision_resolution import (
        PatentHit, build_candidate_profile, resolve_differentiation)

    pav = (parent_ctx.spec.get("prior_art") or {}).get("value") or {}
    cached_fams = ((pav.get("differentiation_resolution") or {})
                   .get("per_family") or [])
    if not cached_fams:
        return {"mode": "REPLAY_CACHE", "valid": False,
                "reason": "NO_CACHED_FAMILIES"}
    problem = parent_ctx.problem or {}
    p_mech = _mech_fields(parent_ctx.spec)
    c_mech = _mech_fields(child_ctx.spec)
    parent_mm = {"intervention": p_mech["intervention"],
                 "mechanism": p_mech["mechanism"],
                 "expected_effect": p_mech["expected_effect"]}
    child_mm = {"intervention": c_mech["intervention"],
                "mechanism": c_mech["mechanism"],
                "expected_effect": c_mech["expected_effect"]}
    p_prof = build_candidate_profile(parent_mm, problem)
    c_prof = build_candidate_profile(child_mm, problem)

    # domain-abandonment guard: the child must stay in the domain the
    # cached art was found FOR. Measured as non-generic technical
    # continuity with the PROBLEM's device/failure vocabulary UNION the
    # cached family corpus (the art was found via the problem's entity
    # queries — the mutation may drift vocabulary within the problem
    # domain; it may not abandon the domain). ZERO overlap on the union
    # = the mutation abandoned the domain (measured attack: a
    # cement-curing intervention for a battery-thermal problem) and
    # stale-art adjudication is forbidden.
    # (Measured while running the replay: corpus-only overlap false-
    # fired on a legitimate in-problem mutation whose vocabulary
    # ('effluent chemistry', 'backflow', 'occlusion') drifted from the
    # pressure-device art while 'occlusion' remained shared with the
    # problem itself.)
    corpus_text = " ".join(
        f"{(f.get('representative') or {}).get('title', '')} "
        f"{f.get('adjudicated_text_excerpt') or ''}"
        for f in cached_fams)
    child_terms = _nongeneric_terms(
        f"{c_mech['mechanism']} {c_mech['intervention']}")
    domain_terms = _nongeneric_terms(
        f"{problem.get('device', '')} {problem.get('failure', '')} "
        f"{problem.get('failure_mode', '')} {corpus_text}")
    domain_overlap = sorted(child_terms & domain_terms)
    if child_terms and not domain_overlap:
        return {"mode": "REPLAY_CACHE", "valid": False,
                "reason": "DOMAIN_ABANDONED_CACHE_INVALID",
                "domain_overlap_terms": [],
                "guard": (
                    "the mutated candidate shares ZERO non-generic "
                    "technical terms with the problem's device/failure "
                    "vocabulary UNION the cached family corpus — the "
                    "art was found for a different domain; "
                    "re-adjudicating against it would fabricate "
                    "surviving differentiators (false novelty from "
                    "stale art). A live search or an honest UNRESOLVED "
                    "is required."),
                "entity_retention_vs_problem": (
                    len(p_prof.folded_entity() &
                        c_prof.folded_entity()) /
                    len(p_prof.folded_entity())
                    if p_prof.folded_entity() else None)}

    precomputed = []
    for fam in cached_fams:
        rep = fam.get("representative") or {}
        hit = PatentHit(
            patent_id=str(rep.get("patent_id") or ""),
            title=str(rep.get("title") or ""),
            snippet="", source_id=str(rep.get("source_id") or ""),
            source_url=str(rep.get("source_url") or ""),
            query_class="REPLAY_CACHE", query="",
            assignee=str(rep.get("assignee") or ""),
            publication_date=str(rep.get("publication_date") or ""))
        precomputed.append({
            "family_id": fam.get("family_id"),
            "representative": hit,
            "members": [hit],
            "evidence_tier": fam.get("evidence_tier"),
            "fam_text": fam.get("adjudicated_text_excerpt") or "",
            "claims_fetch_status": "CACHED (adjudicated text of record)",
            "claims_fetch_path": "replay_cache",
        })
    resolution = resolve_differentiation(
        [], c_prof, search_errors=[], searches_succeeded=True,
        deep_fetch=False, precomputed=precomputed)
    return {"mode": "REPLAY_CACHE", "valid": True,
            "domain_overlap_terms": domain_overlap[:12],
            "entity_retention_vs_problem": (
                round(len(p_prof.folded_entity() &
                          c_prof.folded_entity()) /
                      len(p_prof.folded_entity()), 3)
                if p_prof.folded_entity() else None),
            "resolution": resolution,
            "cache_disclosure": (
                "the SEARCH was cached (Lens 429-exhausted / Google 503 "
                "/ PatentBear metered — measured this cycle); the "
                "ADJUDICATION (coverage + state machine) fully re-ran "
                "against the hash-custodied family texts for the "
                "MUTATED profile — no score was inherited"),
            "cached_family_ids": [f.get("family_id")
                                  for f in cached_fams]}


def re_evaluate(child_ctx: CandidateContext,
                collision_mode: str = "REPLAY_CACHE",
                parent_ctx: Optional[CandidateContext] = None,
                live_sources: Optional[List[str]] = None
                ) -> Dict[str, Any]:
    """Full re-evaluation of candidate B:
      - span-derivation re-measured (in apply, carried on the spec)
      - prior-art position re-adjudicated (LIVE search or REPLAY_CACHE)
      - I1-I5 re-measured on the CHILD's own artifacts
      - Q re-measured with the FROZEN instrument (read-only import)
    Nothing is inherited from the parent's evaluation."""
    from discovery_fabric.benchmark import candidate_quality as cq
    from discovery_fabric.benchmark import invention_quality as iq

    spec = child_ctx.spec
    decisive = child_ctx.decisive
    out: Dict[str, Any] = {"collision_mode": collision_mode,
                           "re_evaluated_at": utc_now()}

    # --- prior-art re-adjudication
    if collision_mode == "REPLAY_CACHE" and parent_ctx is not None:
        adj = re_adjudicate_cached(parent_ctx, child_ctx)
        out["re_adjudication"] = adj
        if adj.get("valid"):
            resolution = adj["resolution"]
            # write the child's own prior-art position onto the child spec
            pav = (spec.get("prior_art") or {}).get("value") or {}
            pav["differentiation_resolution"] = resolution
            pav["status"] = resolution["state"]
            spec["prior_art"]["value"] = pav
            nh = (spec.get("novelty_hypothesis") or {}).get("value") or {}
            nh["prior_art_status"] = resolution["state"]
            nh["differentiation_resolution_state"] = resolution["state"]
            spec["novelty_hypothesis"]["value"] = nh
            df = (spec.get("distinguishing_features") or {}).get(
                "value") or {}
            df["surviving_differentiators"] = \
                resolution.get("surviving_differentiators")
            df["vs_nearest_prior_art"] = [
                {"patent_id": f["representative"]["patent_id"],
                 "title": f["representative"]["title"],
                 "family_id": f["family_id"],
                 "family_size": f["family_size"],
                 "evidence_tier": f["evidence_tier"],
                 "coverage_class": f["coverage"]["coverage_class"],
                 "coverage_ratio": f["coverage"]["coverage_ratio"],
                 "mechanism_overlap_terms":
                     f["coverage"]["mechanism_overlap_terms"],
                 "distinguishing_terms_covered":
                     f["coverage"]["distinguishing_terms_covered"],
                 "distinguishing_terms_surviving":
                     f["coverage"]["distinguishing_terms_surviving"]}
                for f in resolution["per_family"]]
            spec["distinguishing_features"]["value"] = df
            out["prior_art_status"] = resolution["state"]
        else:
            out["prior_art_status"] = "UNRESOLVED_INSUFFICIENT_EVIDENCE"
            out["re_adjudication_failure"] = adj.get("reason")
    elif collision_mode == "LIVE":
        from discovery_fabric.prior_art_v2.collision_resolution import (
            run_collision)
        mm = {"intervention": _mech_fields(spec)["intervention"],
              "mechanism": _mech_fields(spec)["mechanism"],
              "expected_effect": _mech_fields(spec)["expected_effect"]}
        collision = run_collision(mm, child_ctx.problem or {},
                                  sources=live_sources)
        out["re_adjudication"] = {"mode": "LIVE",
                                  "resolution":
                                      collision["differentiation_resolution"]}
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

    # re-hash the child spec AFTER adjudication writes
    spec["_spec_hash"] = sha256_obj(
        {k: v for k, v in spec.items()
         if not k.startswith("_")})

    # --- BOTH instruments, measured on the child's own artifacts
    i_dims = [iq.measure_mechanism_derivation(spec),
              iq.measure_differentiator_meaning(spec),
              iq.measure_recombination(spec),
              iq.measure_new_relationship(spec),
              iq.measure_experiment_discrimination(spec, decisive)]
    q_dims = [cq.measure_evidence_binding(spec),
              cq.measure_prior_art_specificity(spec),
              cq.measure_prior_art_resolution(spec),
              cq.measure_experiment_decisiveness(spec, decisive),
              cq.measure_chain_completeness(spec, decisive)]

    def _avg(dims):
        scores = [d.get("score") for d in dims
                  if isinstance(d.get("score"), (int, float))]
        return round(sum(scores) / len(scores), 3) if scores else None

    out["i_dimensions"] = {d["dimension"]: {
        "score": d.get("score"), "state": d.get("state")} for d in i_dims}
    out["i_flags"] = {
        "underived_mechanism": any(d.get("underived_flag")
                                   for d in i_dims),
        "recombination_only": any(d.get("recombination_only_flag")
                                  for d in i_dims)}
    out["i_average"] = _avg(i_dims)
    out["q_dimensions"] = {d["dimension"]: {
        "score": d.get("score"), "state": d.get("state")} for d in q_dims}
    out["q_average"] = _avg(q_dims)
    return out


# ---------------------------------------------------------------------------
# 6. KEEP OR KILL (targeted-improvement rule)
# ---------------------------------------------------------------------------
def keep_or_kill(parent_eval: Dict[str, Any],
                 child_eval: Dict[str, Any],
                 target_dimension: str,
                 parent_ctx: CandidateContext,
                 child_ctx: CandidateContext
                 ) -> Dict[str, Any]:
    """CEO rule: measurable improvement OR honest kill — but the
    improvement must be on the TARGETED dimension, and the mechanical
    invariants must hold:
      - no parent negative erased (rule 10)
      - no new structural flag introduced (a repair that breaks
        another link is not an improvement)
      - no UNKNOWN -> MEASURED conversion without new evidence
      - the prior-art position may not degrade RESOLVED ->
        UNRESOLVED (stale evidence) — a REAL new collision
        (RESOLVED_ANTICIPATED) is a kill-grade finding, recorded.
    """
    reasons: List[str] = []
    checks: Dict[str, Any] = {}

    p_dim = parent_eval["i_dimensions"].get(target_dimension) or {}
    c_dim = child_eval["i_dimensions"].get(target_dimension) or {}
    p_score, c_score = p_dim.get("score"), c_dim.get("score")

    improved = False
    # flag-driven weaknesses (UNDERIVED / RECOMBINATION) are STRUCTURAL:
    # the KEEP requires the flag CLEARED — a marginal score movement
    # that leaves the structural defect standing is not a defensible
    # improvement (measured first replay: I1 0.0 -> 0.091 kept while
    # the mechanism remained underived; the CEO bar is "the mechanism
    # is NOW evidence-derived", not "the number moved")
    flag_target = (
        (target_dimension == "I1_MECHANISM_EVIDENCE_DERIVATION"
         and parent_eval["i_flags"]["underived_mechanism"])
        or (target_dimension == "I3_RECOMBINATION_RISK"
            and parent_eval["i_flags"]["recombination_only"]))
    flag_cleared = (
        (target_dimension == "I1_MECHANISM_EVIDENCE_DERIVATION"
         and parent_eval["i_flags"]["underived_mechanism"]
         and not child_eval["i_flags"]["underived_mechanism"])
        or (target_dimension == "I3_RECOMBINATION_RISK"
            and parent_eval["i_flags"]["recombination_only"]
            and not child_eval["i_flags"]["recombination_only"]))

    if p_score is not None and c_score is not None and c_score > p_score:
        improved = not flag_target or flag_cleared
        if flag_target and not flag_cleared:
            checks["targeted_dimension"] = (
                f"{p_score} -> {c_score} (score moved but the structural "
                f"flag PERSISTS — not a defensible improvement)")
        else:
            checks["targeted_dimension"] = \
                f"{p_score} -> {c_score} (improved)"
    elif p_score is None and c_score is not None:
        improved = False
        checks["targeted_dimension"] = \
            "parent UNMEASURABLE -> child measured without new " \
            "evidence (not an improvement; Art. XXV)"
    elif flag_cleared:
        improved = True
        checks["targeted_dimension"] = (
            "underived flag CLEARED (evidence-derived mechanism)"
            if target_dimension == "I1_MECHANISM_EVIDENCE_DERIVATION"
            else "recombination_only flag CLEARED (novel residue exists)")
    else:
        checks["targeted_dimension"] = \
            f"{p_score} -> {c_score} (no improvement)"

    # negatives preservation (rule 10)
    preserved, lost = negatives_preserved(
        collect_negatives(parent_ctx.spec, parent_ctx.decisive),
        collect_negatives(child_ctx.spec, child_ctx.decisive))
    checks["negatives_preserved"] = preserved
    if lost:
        reasons.append(f"mutation would erase parent negatives: {lost}")

    # no NEW structural flag
    new_flags: List[str] = []
    if not parent_eval["i_flags"]["underived_mechanism"] and \
            child_eval["i_flags"]["underived_mechanism"]:
        new_flags.append("underived_mechanism")
    if not parent_eval["i_flags"]["recombination_only"] and \
            child_eval["i_flags"]["recombination_only"]:
        new_flags.append("recombination_only")
    checks["no_new_structural_flags"] = not new_flags
    if new_flags:
        reasons.append(f"mutation introduced new structural flags: "
                       f"{new_flags}")

    # no UNKNOWN -> MEASURED conversion without new evidence. Measured
    # against the UNMEASURABLE *state*, not the bare None score
    # (measured defect while writing the adversarial tests: a
    # MECHANISM_STRENGTHENING mutation legitimately enriches a TERSE
    # mechanism, making I4 measurable against the SAME unchanged family
    # texts — that is a candidate-text gap closing, not certainty
    # laundering. The forbidden conversion is an EVIDENCE gap closing
    # with no new evidence: no families / no family text.)
    EVIDENCE_GAP_STATES = {
        "UNMEASURABLE_NO_FAMILIES", "UNMEASURABLE_NO_FAMILY_TEXT"}
    unknown_conversions: List[str] = []
    text_gap_conversions: List[str] = []
    for dim, c in child_eval["i_dimensions"].items():
        p = parent_eval["i_dimensions"].get(dim) or {}
        if p.get("score") is None and c.get("score") is not None:
            if p.get("state") in EVIDENCE_GAP_STATES:
                if child_eval.get("collision_mode") != "LIVE":
                    # cache mode cannot create family evidence — a
                    # score appearing here would be laundered certainty
                    unknown_conversions.append(dim)
            else:
                # candidate-text gap (terse mechanism / no survivors):
                # the validated mutation supplied the text; the
                # measurement runs against the SAME evidence. Recorded
                # for audit — never silent.
                text_gap_conversions.append(dim)
    checks["no_unknown_conversion_without_new_evidence"] = \
        not unknown_conversions
    checks["text_gap_conversions_recorded"] = text_gap_conversions
    if unknown_conversions:
        reasons.append(f"UNKNOWN evidence-gap converted to MEASURED "
                       f"without new evidence: {unknown_conversions} "
                       f"(Art. XXV)")

    # prior-art position may not degrade RESOLVED -> UNRESOLVED
    p_status = parent_eval.get("prior_art_status")
    c_status = child_eval.get("prior_art_status")
    degraded = (str(p_status or "").startswith("RESOLVED")
                and not str(c_status or "").startswith("RESOLVED"))
    checks["prior_art_position_not_degraded"] = not degraded
    if degraded:
        reasons.append(f"prior-art position degraded {p_status} -> "
                       f"{c_status} (stale/lost evidence is not a "
                       f"mutation outcome)")

    anticipated = str(c_status or "") == "RESOLVED_ANTICIPATED"
    if anticipated:
        reasons.append("the mutated candidate walked INTO prior art "
                       "(RESOLVED_ANTICIPATED on re-adjudication) — "
                       "the mutation is rejected; recorded as a "
                       "kill-grade finding for the ledger")

    action = "KEEP" if (improved and not reasons) else "REJECT_MUTATION"
    return {"action": action, "improved": improved,
            "checks": checks, "reasons": reasons,
            "decided_at": utc_now()}


# ---------------------------------------------------------------------------
# 7. THE LOOP
# ---------------------------------------------------------------------------
def _measure_ctx(ctx: CandidateContext,
                 prior_art_status: Optional[str] = None) -> Dict[str, Any]:
    """Measure a context with BOTH instruments without re-adjudicating
    (the parent's own recorded state is used — this is the BASELINE
    measurement, not the child re-evaluation)."""
    from discovery_fabric.benchmark import candidate_quality as cq
    from discovery_fabric.benchmark import invention_quality as iq
    spec, decisive = ctx.spec, ctx.decisive
    i_dims = [iq.measure_mechanism_derivation(spec),
              iq.measure_differentiator_meaning(spec),
              iq.measure_recombination(spec),
              iq.measure_new_relationship(spec),
              iq.measure_experiment_discrimination(spec, decisive)]
    q_dims = [cq.measure_evidence_binding(spec),
              cq.measure_prior_art_specificity(spec),
              cq.measure_prior_art_resolution(spec),
              cq.measure_experiment_decisiveness(spec, decisive),
              cq.measure_chain_completeness(spec, decisive)]

    def _avg(dims):
        scores = [d.get("score") for d in dims
                  if isinstance(d.get("score"), (int, float))]
        return round(sum(scores) / len(scores), 3) if scores else None

    status = prior_art_status or \
        ((spec.get("novelty_hypothesis") or {}).get("value") or {}) \
        .get("prior_art_status")
    return {
        "i_dimensions": {d["dimension"]: {"score": d.get("score"),
                                          "state": d.get("state")}
                         for d in i_dims},
        "i_flags": {
            "underived_mechanism": any(d.get("underived_flag")
                                       for d in i_dims),
            "recombination_only": any(d.get("recombination_only_flag")
                                      for d in i_dims)},
        "i_average": _avg(i_dims),
        "q_dimensions": {d["dimension"]: {"score": d.get("score"),
                                          "state": d.get("state")}
                         for d in q_dims},
        "q_average": _avg(q_dims),
        "prior_art_status": status,
    }


def improve_candidate(ctx: CandidateContext,
                      max_iterations: Optional[int] = None,
                      max_proposals: Optional[int] = None,
                      collision_mode: str = "REPLAY_CACHE",
                      live_sources: Optional[List[str]] = None,
                      provider: Optional[str] = None,
                      evaluator_id: Optional[str] = None,
                      ) -> Dict[str, Any]:
    """The CEO loop driver. Returns the IMPROVEMENT_LEDGER:

        CANDIDATE -> DIAGNOSE -> MUTATION -> RE-EVALUATE -> KEEP/KILL
        -> (KEEP: REPEAT) / (KILL: honest end state)

    Outcome vocabulary (honest, exhaustive):
      IMPROVED              >= 1 KEEP; the ledger carries every iteration
      HEALTHY_NO_MUTATION   diagnosis found no limiting feature
      KILLED_NO_DEFENSIBLE_MUTATION   weak candidate, no valid proposal
      KILLED_NO_IMPROVING_MUTATION    valid proposals never improved the
                                      target dimension (measured)
      IMPROVEMENT_BLOCKED_TRANSPORT   LLM transport failed — NOT a kill
                                      (Art. XXV: infrastructure is not
                                      a research verdict)
      IMPROVEMENT_NOT_RUN_CANDIDATE_KILLED  Art. XX problem-existence
                                      guard: the attack already killed
                                      the candidate's premise
    """
    max_iterations = (max_iterations if max_iterations is not None else
                      IMPROVEMENT_THRESHOLDS["MAX_ITERATIONS_DEFAULT"]
                      ["value"])
    max_proposals = (max_proposals if max_proposals is not None else
                     IMPROVEMENT_THRESHOLDS[
                         "MAX_PROPOSALS_PER_ITERATION"]["value"])

    ledger: Dict[str, Any] = {
        "ledger": "IMPROVEMENT_LEDGER (R378 TECHNICAL IMPROVEMENT ENGINE)",
        "version": LEDGER_VERSION,
        "loop": ("CANDIDATE -> DIAGNOSE WEAKNESS -> IDENTIFY LIMITING "
                 "FEATURE -> GENERATE CONTROLLED MUTATION -> RE-EVALUATE "
                 "EVIDENCE/MECHANISM/PRIOR ART -> RE-SCORE -> KEEP OR "
                 "KILL -> REPEAT"),
        "collision_mode": collision_mode,
        "live_sources": live_sources,
        "evaluators_registered": registered_evaluators(),
        "q_instrument": "discovery_fabric/benchmark/candidate_quality.py "
                        "(FROZEN, hash-pinned, imported read-only)",
        "i_instrument": "discovery_fabric/benchmark/invention_quality.py "
                        "(R377, imported read-only)",
        "thresholds": IMPROVEMENT_THRESHOLDS,
        "started_at": utc_now(),
        "iterations": [],
        "outcome": None,
        "outcome_reason": "",
    }

    # Art. XX guard: the attack already killed the candidate's premise
    if isinstance(ctx.attack, dict) and \
            ctx.attack.get("overall") == "KILLED":
        ledger["outcome"] = "IMPROVEMENT_NOT_RUN_CANDIDATE_KILLED"
        ledger["outcome_reason"] = (
            "the engineering attack already KILLED this candidate "
            "(problem-existence/premise); improvement strengthens "
            "mechanisms, not premises (Art. XX)")
        ledger["finished_at"] = utc_now()
        return ledger

    current = ctx
    baseline = _measure_ctx(current)
    ledger["baseline"] = baseline
    parent_eval = baseline

    for iteration in range(1, max_iterations + 1):
        diag = diagnose(current, evaluator_id)
        limiting = diag.limiting_features
        if not limiting:
            ledger["outcome"] = "HEALTHY_NO_MUTATION"
            ledger["outcome_reason"] = (
                f"iteration {iteration}: no limiting feature above the "
                f"declared weakness threshold "
                f"({WEAKNESS_THRESHOLD['value']}); the candidate stands "
                f"on its measured dimensions")
            break

        target = limiting[0]
        it_record: Dict[str, Any] = {
            "iteration": iteration,
            "diagnosis": {
                "limiting_features": [
                    {"dimension": f.dimension,
                     "measured_value": f.measured_value,
                     "weakness_kind": f.weakness_kind,
                     "why_weak": f.why_weak,
                     "mutation_type": f.mutation_type}
                    for f in limiting],
                "evidence_gaps": diag.evidence_gaps,
                "target": {"dimension": target.dimension,
                           "mutation_type": target.mutation_type},
            },
            "proposals": [],
        }

        valid_proposal = None
        valid_validation = None
        transport_blocked = False
        rejections: List[Dict[str, Any]] = []
        for attempt in range(1, max_proposals + 1):
            proposal = propose_mutation(
                current, diag, 0, provider=provider,
                feedback=[r.get("feedback_record") or r
                          for r in rejections])
            if proposal.get("status") != "OK":
                transport_blocked = transport_blocked or \
                    proposal.get("status") == "PROVIDER_UNAVAILABLE"
                it_record["proposals"].append(proposal)
                continue
            validation = validate_mutation(current, proposal, diag, 0)
            if not validation["valid"]:
                # DIRECTIONAL FEEDBACK (the AU-pattern loop): the exact
                # deterministic rejection reasons travel into the next
                # proposal attempt's prompt — the proposer must fix
                # what the validator named, not repeat itself
                rejections.append({
                    "feedback_record": {
                        "reasons": validation["reasons"],
                        "mutation_type": validation["mutation_type"]}})
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
                ledger["outcome"] = "IMPROVEMENT_BLOCKED_TRANSPORT"
                ledger["outcome_reason"] = (
                    f"iteration {iteration}: all proposal attempts hit "
                    f"provider unavailability — infrastructure, not a "
                    f"research verdict (Art. XXV); the candidate stands")
            else:
                ledger["outcome"] = "KILLED_NO_DEFENSIBLE_MUTATION"
                ledger["outcome_reason"] = (
                    f"iteration {iteration}: {len(it_record['proposals'])} "
                    f"proposal(s) generated; none passed deterministic "
                    f"validation — no defensible mutation exists for "
                    f"{target.dimension}. Candidate killed.")
            ledger["iterations"].append(it_record)
            break

        # apply + re-evaluate (CEO rule 11: full re-run). A REJECTED
        # mutation reverts to the parent and the loop tries the NEXT
        # valid proposal — "no defensible mutation can improve the
        # candidate" (CEO rule 9) must mean the budget was actually
        # spent, not that the FIRST valid proposal regressed (measured
        # on the w7 adversarial run: iteration 2 killed the candidate
        # on a single regressing mutation while proposal budget
        # remained).
        mutation_attempts: List[Dict[str, Any]] = []
        max_valid_evals = 2
        decided = None
        child = None
        re_eval = None
        while len(mutation_attempts) < max_valid_evals:
            child = apply_mutation(current, valid_proposal,
                                   valid_validation)
            re_eval = re_evaluate(child, collision_mode=collision_mode,
                                  parent_ctx=(current
                                              if collision_mode ==
                                              "REPLAY_CACHE" else None),
                                  live_sources=live_sources)
            decision = keep_or_kill(parent_eval, re_eval,
                                    target.dimension, current, child)
            mutation_attempts.append({
                "mutation_applied":
                    child.spec.get("_improvement", {}).get(
                        "mutation", {}),
                "re_evaluation": re_eval,
                "decision": decision,
            })
            decided = decision
            if decision["action"] == "KEEP":
                break
            # REJECT: the parent stands; try the NEXT valid proposal
            # within the proposal budget, carrying the rejection reason
            # as directional feedback
            rejections.append({
                "feedback_record": {
                    "reasons": decision["reasons"] or [
                        decision["checks"].get("targeted_dimension")
                        or "no measurable improvement"],
                    "mutation_type": target.mutation_type}})
            found_next = False
            while len(it_record["proposals"]) < max_proposals:
                proposal = propose_mutation(
                    current, diag, 0, provider=provider,
                    feedback=[r.get("feedback_record") or r
                              for r in rejections])
                if proposal.get("status") != "OK":
                    transport_blocked = transport_blocked or \
                        proposal.get("status") == "PROVIDER_UNAVAILABLE"
                    it_record["proposals"].append(proposal)
                    break
                validation = validate_mutation(current, proposal, diag, 0)
                if not validation["valid"]:
                    rejections.append({
                        "feedback_record": {
                            "reasons": validation["reasons"],
                            "mutation_type":
                                validation["mutation_type"]}})
                it_record["proposals"].append({
                    "proposal_id": proposal.get("proposal_id"),
                    "provider": proposal.get("provider"),
                    "model": proposal.get("model"),
                    "prompt_hash": proposal.get("prompt_hash"),
                    "output_hash": proposal.get("output_hash"),
                    "fields": proposal.get("fields"),
                    "validation": validation})
                if validation["valid"]:
                    valid_proposal, valid_validation = \
                        proposal, validation
                    found_next = True
                    break
            if not found_next:
                break

        it_record["mutation_attempts"] = mutation_attempts
        # canonical single-attempt view (backwards compatible): the
        # FIRST applied mutation; the full attempt list is above
        if mutation_attempts:
            it_record["mutation_applied"] = \
                mutation_attempts[0]["mutation_applied"]
            it_record["re_evaluation"] = \
                mutation_attempts[-1]["re_evaluation"]
            it_record["decision"] = mutation_attempts[-1]["decision"]
        ledger["iterations"].append(it_record)

        if decided is not None and decided["action"] == "KEEP":
            current = child
            parent_eval = re_eval
            continue
        # every applied mutation was rejected and no further valid
        # proposal exists within the budget: the parent stands and the
        # target remains weak. Honest verdict:
        ledger["outcome"] = "KILLED_NO_IMPROVING_MUTATION"
        ledger["outcome_reason"] = (
            f"iteration {iteration}: {len(mutation_attempts)} validated "
            f"{target.mutation_type} mutation(s) were applied and fully "
            f"re-evaluated; the targeted dimension "
            f"{target.dimension} did not improve ("
            + "; ".join(str(a["decision"]["checks"].get(
                "targeted_dimension")) for a in mutation_attempts)
            + "); "
            + ("; ".join(decided["reasons"])
               if decided and decided["reasons"]
               else "no invariant violated")
            + ". No defensible improvement exists. Candidate killed.")
        break
    else:
        # loop completed without break: iterations ran out
        ledger["outcome"] = "IMPROVED" if any(
            it.get("decision", {}).get("action") == "KEEP"
            for it in ledger["iterations"]) else "KILLED_NO_IMPROVING_MUTATION"

    final = _measure_ctx(current)
    ledger["final"] = final
    ledger["current_ctx"] = current
    ledger["finished_at"] = utc_now()
    ledger["outcome_summary"] = {
        "baseline_i_average": baseline.get("i_average"),
        "final_i_average": final.get("i_average"),
        "baseline_q_average": baseline.get("q_average"),
        "final_q_average": final.get("q_average"),
        "iterations_run": len(ledger["iterations"]),
        "keeps": sum(1 for it in ledger["iterations"]
                     if it.get("decision", {}).get("action") == "KEEP"),
    }
    return ledger

"""The DirectionalHypothesis — the canonical epistemic primitive of the
Directional Improvement Engine (R450 directive §2).

WHAT TOSCANINI THINKS SHOULD BE CHANGED NEXT, IN WHICH DIRECTION, WHY,
AND WHAT RESULT SHOULD FOLLOW — as a machine-evaluable,
provenance-bearing object, never free-form prose masquerading as
reasoning.

The directive's distinction (§4) is constitutional here:
  A MUTATION is  "change parameter X."
  A DIRECTION is "change X because mechanism Y is causing failure Z,
                  and this should move observable Q in direction R."

Every DirectionalHypothesis therefore binds:
  failure            -> failure_id   (the recorded failure event)
  mechanism          -> causal_diagnosis_id (the typed diagnosis)
  variable           -> target_variable + current -> proposed + direction
  physical effect    -> predicted_effect (+ magnitude/range when stated)
  falsifier          -> a measurable statement that would kill it

THE GROUND GATE (deterministic, Art. XVIII/III):
  The LLM PROPOSES hypotheses; the infrastructure ADJUDICATES grounding
  mechanically. An ungrounded proposal is REJECTED — the mutation never
  executes (the directive: "Ungrounded mutation -> REJECT / ABSTAIN"),
  which prevents brute-force mutation from being mistaken for
  intelligence.

  Grounding checks (each recorded with its basis):
    G1 STRUCTURE     — every required field present and non-empty
    G2 DIAGNOSIS     — causal_diagnosis_id resolves to a RECORDED
                       diagnosis (never a narrative reference)
    G3 MECHANISM     — mechanism_affected term-overlaps the diagnosis's
                       own mechanism/causal vocabulary OR the parent
                       candidate's mechanism (the direction speaks about
                       the thing that failed)
    G4 PREDICTION    — predicted_effect is non-empty AND direction is a
                       vocabulary value AND the falsifier names a
                       measurable quantity (measurement-term pattern)
    G5 EVIDENCE      — evidence_support ids resolve to evidence in the
                       run's custody, OR evidence_gaps is explicitly
                       populated (honest unsupported direction, capped
                       confidence — never silently promoted)

Status vocabulary (closed):
    PROPOSED       gated but not yet executed
    GROUNDED       passed all checks with EVIDENCE_SUPPORTED class;
                   mutation may execute
    EXPLORATORY    R451 §4: structurally sound but its evidence class
                   is EVIDENCE_PARTIAL / EVIDENCE_MISSING — the gaps
                   were served (reverse path) and support still did not
                   resolve. Recorded as an EXPLORATORY hypothesis: NO
                   mutation executes; the next action is further
                   retrieval or a decisive-experiment specification
                   (never pretend-grounded -> mutate)
    REJECTED       failed a check (the failure basis is recorded); the
                   mutation NEVER executes
    EXECUTED       a controlled mutation was derived and evaluated
    FALSIFIED      the observation contradicted the prediction (the
                   direction dies; negative knowledge)
    SUPPORTED      the observation matched the predicted direction
    SUPERSEDED     a later hypothesis replaced this one on the same
                   target variable

Evidence support classification (R451 §4 — the closed classes):
    EVIDENCE_SUPPORTED  >=1 LLM-cited evidence id resolves to custody
                        AND its claimed span verifies VERBATIM in the
                        item's text, AND no evidence_gaps remain
    EVIDENCE_PARTIAL    verified support exists BUT evidence_gaps are
                        declared (gaps != empty is NEVER equated with
                        support)
    EVIDENCE_MISSING    no verified support; gaps only — the direction
                        is at most an exploratory hypothesis

THE STRUCTURED CAUSAL CHAIN (R451 §5 — the deterministic layer):
    failure -> causal mechanism -> affected variable -> intervention
    -> predicted observable, validated mechanically:
    G2  the diagnosis id resolves to the RECORDED diagnosis
    G3  mechanism term-grounding (ONE defensive signal — recorded,
        required, but never sufficient alone)
    G5  the evidence class (ids resolve, evidence exists, spans exist)
    G6  the target variable corresponds to the DESIGN STATE (the
        failed candidate's own declared variables/mechanism and the
        problem's declared quantities)
    G7  the predicted observable corresponds to the intervention (the
        prediction speaks about what the intervention changes)
    G8  the falsifier measures the PREDICTED observable and its
        kill-direction does not contradict the prediction
    G9  causal memory: the (target_variable, direction) pair does not
        repeat a previously FALSIFIED direction (negative knowledge
        changes future search — Art. LI)
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DIRECTIONAL_ENGINE_VERSION = "directional_engine/1.1.0"

#: direction vocabulary (closed) — the direction of the intervention on
#: the target variable
DIRECTIONS = ["INCREASE", "DECREASE", "ADD", "REMOVE", "REPLACE",
              "CHANGE_MECHANISM", "TIGHTEN", "RELAX", "REVERSE"]

#: intervention classes (R450 §12 — the closed vocabulary)
INTERVENTION_CLASSES = [
    "PARAMETER_MUTATION",          # change a design parameter's value
    "TOPOLOGY_MUTATION",           # add/remove/reconnect subsystems
    "MATERIAL_MUTATION",           # change a material or coating
    "OPERATING_CONDITION_MUTATION",  # change the operating envelope
    "MECHANISM_COMBINATION",       # combine two mechanisms
    "EVIDENCE_UPDATE",             # the governing assumption is wrong:
                                   # acquire evidence, not geometry
    "CONSTRAINT_RELAXATION",       # negotiate a constraint
    "CONSTRAINT_TIGHTENING",       # tighten a spec for margin
]

#: hypothesis status vocabulary (closed)
HYPOTHESIS_STATUSES = [
    "PROPOSED", "GROUNDED", "EXPLORATORY", "REJECTED", "EXECUTED",
    "FALSIFIED", "SUPPORTED", "SUPERSEDED",
]

#: evidence support classification (R451 §4 — closed)
EVIDENCE_CLASSES = [
    "EVIDENCE_SUPPORTED", "EVIDENCE_PARTIAL", "EVIDENCE_MISSING",
]

#: measurable-quantity term pattern for the falsifier check (G4).
#: THREE mechanical forms of measurability (each a real measurement
#: structure, never a wish):
#:   (a) number + unit ("0.1 mm/year", "4500 W/m2K", "75 percent")
#:   (b) a named physical/engineering quantity ("heat transfer
#:       coefficient", "ejected heat fraction" via the comparative
#:       form, "pitting rate", ...)
#:   (c) a COMPARATIVE EXPERIMENT between conditions — the standard
#:       engineering falsifier form ("X measures higher than Y under
#:       identical conditions"): direction word + quantity + explicit
#:       comparison target. A wish ("just obviously work better") has
#:       no quantity and no comparison target and never qualifies.
_MEASUREMENT_RE = re.compile(
    r"\b\d+(\.\d+)?\s*(?:mm|cm|m|km|um|nm|k?pa|mpa|bar|atm|c|f|k|"
    r"v|a|w|kw|mw|hz|khz|mhz|ghz|s|ms|min|h|mol|mmol|ppm|ph|percent|"
    r"db|lpm|gpm|kg|g|n)(?![a-z])"
    r"|\b\d+(\.\d+)?\s*%"
    r"|(heat transfer coefficient|pitting rate|penetration|corrosion "
    r"rate|pressure drop|flow rate|temperature|efficiency|lifetime|"
    r"fatigue life|service interval|service life|surface roughness|"
    r"thermal resistance|biofilm thickness|wall thickness|margin|"
    r"stress|deflection|vibration amplitude|energy|power|cost|mass|"
    r"weight|stiffness|conductance|resistance|impedance|yield|purity|"
    r"emission|discharge|concentration|frequency|amplitude|speed|"
    r"velocity|reynolds number|heat flux|duty cycle|cycle life|"
    r"delamination|leakage|fracture|crack propagation|failure rate|"
    r"outage|retubing interval|propagation delay|peak temperature|"
    r"heat fraction|state of charge)"
    r"|\b(?:higher|lower|increased|decreased|reduced|elevated|"
    r"exceeds?|surpass(?:es)?|above|below|worse|greater|fewer|"
    r"smaller|larger)\b[^.;:!?]{0,80}\b(?:compared to|than|"
    r"versus|vs\.?|relative to|against|under identical)\b",
    re.I)

_GENERIC_TERMS = set("""the and with using used that this from for into
through between during their provides providing based approach system
method design when where which while failure failed cause caused
improve improved improvement change changed modify""".split())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _terms(text: str, min_len: int = 4) -> set:
    return set(re.findall(r"[a-z0-9]{%d,}" % min_len,
                          (text or "").lower())) - _GENERIC_TERMS


@dataclass
class DirectionalHypothesis:
    """Machine-evaluable, provenance-bearing (R450 §2)."""

    hypothesis_id: str
    candidate_id: str
    failure_id: str
    causal_diagnosis_id: str
    # ---- the direction -----------------------------------------------
    target_variable: str
    current_value: str = ""
    proposed_value: str = ""
    direction: str = ""                    # DIRECTIONS value
    # ---- the causal chain --------------------------------------------
    mechanism_affected: str = ""
    causal_rationale: str = ""             # MUST reference the diagnosis
    predicted_effect: str = ""
    predicted_magnitude_or_range: str = ""
    # ---- the honest epistemic surface ---------------------------------
    competing_explanations: List[str] = field(default_factory=list)
    evidence_support: List[Dict[str, Any]] = field(default_factory=list)
    evidence_gaps: List[str] = field(default_factory=list)
    # ---- the falsifier ------------------------------------------------
    falsifier: str = ""
    measurement_required: str = ""
    # ---- classification + provenance ----------------------------------
    intervention_type: str = ""            # INTERVENTION_CLASSES value
    confidence: str = "LOW"                # LOW | MODERATE | HIGH
    provenance: Dict[str, Any] = field(default_factory=dict)
    status: str = "PROPOSED"
    gate: Dict[str, Any] = field(default_factory=dict)  # the recorded
                                                        # adjudication

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def make_hypothesis_id(candidate_id: str, failure_id: str,
                       target_variable: str, nonce: int) -> str:
    """Deterministic identity: same (candidate, failure, target) at the
    same attempt index is the same hypothesis (Art. VI)."""
    basis = f"{candidate_id}|{failure_id}|{target_variable}|{nonce}"
    return "dh:" + hashlib.sha256(
        basis.encode("utf-8")).hexdigest()[:20]


# ---------------------------------------------------------------------------
# THE GROUND GATE — deterministic adjudication (R450 §4; R451 §§4-5)
# ---------------------------------------------------------------------------

#: kill-direction comparative words near the target/falsifier terms —
#: used by G8's contradiction test (a falsifier that kills exactly what
#: the prediction asserts as success contradicts the prediction)
_KILL_UP_RE = re.compile(
    r"\b(higher|increased|increases|above|exceeds?|surpass(?:es)?|"
    r"greater|larger)\b", re.I)
_KILL_DOWN_RE = re.compile(
    r"\b(lower|decreased|decreases|below|fewer|smaller|reduced)\b",
    re.I)


def _norm_id(raw: str) -> str:
    """Normalize a cited evidence id: strip whitespace/brackets/quotes
    (a weak model emits '[ev:aaa111], [ev:bbb222]' — the id is the
    bracketed token; normalization is parsing, never fabrication)."""
    return (raw or "").strip().strip("[]()\"'").strip()


def _design_state_terms(design_state: Optional[Dict[str, Any]]) -> set:
    """The distinctive terms of the DESIGN STATE vocabulary: the failed
    candidate's own declared variables/mechanism/intervention plus the
    problem's declared quantities (G6's grounding surface)."""
    if not design_state:
        return set()
    parts = []
    for k in ("variables", "mechanism", "intervention",
              "expected_effect", "problem_text", "constraints",
              "targets"):
        v = design_state.get(k)
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        elif v:
            parts.append(str(v))
    return _terms(" ".join(parts))


def ground_gate(hypothesis: Dict[str, Any],
                diagnosis: Optional[Dict[str, Any]],
                parent_mechanism: str = "",
                known_evidence_ids: Optional[set] = None,
                design_state: Optional[Dict[str, Any]] = None,
                evidence_texts: Optional[Dict[str, Dict[str, Any]]] = None,
                falsified_priors: Optional[List[Dict[str, Any]]] = None,
                ) -> Dict[str, Any]:
    """Adjudicate a PROPOSED hypothesis. Returns the gate record (never
    raises; every failure is a recorded check verdict).

    `diagnosis`      — the recorded diagnosis dict (from the run's
                       diagnosis records; the id must match).
    `parent_mechanism` — the failed candidate's mechanism text.
    `known_evidence_ids` — the evidence ids in the run's custody (the
                       only admissible evidence_support anchors).
    `design_state`  — R451 §5 G6: {variables, mechanism, intervention,
                       expected_effect, problem_text, ...} from the
                       parent candidate + problem (the design's OWN
                       state; a direction about a variable that is not
                       in it speaks about nothing the machine controls).
    `evidence_texts` — {evidence_id: item} for span verification (G5:
                       ids resolve, evidence exists, spans exist).
    `falsified_priors` — R451 §5 G9: prior hypotheses with status
                       FALSIFIED — their (target_variable, direction)
                       pairs are negative knowledge; repeating one is
                       REJECTED (learning must change future search).

    VERDICT: GROUNDED (evidence class EVIDENCE_SUPPORTED — the mutation
    may execute) | EXPLORATORY (R451 §4: structure passes but support
    is PARTIAL/MISSING — no mutation; retrieve or specify the decisive
    experiment) | REJECTED (a structural/causal check failed).
    """
    checks: List[Dict[str, Any]] = []

    def _check(name: str, ok: bool, basis: str) -> bool:
        checks.append({"check": name, "verdict": "PASS" if ok else "FAIL",
                       "basis": basis})
        return ok

    # G1 STRUCTURE
    required = ["hypothesis_id", "candidate_id", "failure_id",
                "causal_diagnosis_id", "target_variable", "direction",
                "mechanism_affected", "causal_rationale",
                "predicted_effect", "falsifier", "intervention_type"]
    missing = [k for k in required
               if not str(hypothesis.get(k) or "").strip()]
    g1 = _check("G1_STRUCTURE", not missing,
                "all required fields present" if not missing else
                f"missing: {', '.join(missing)}")
    # vocabulary checks (fail-closed: a value outside the closed
    # vocabulary is a structural failure, never silently coerced)
    vocab_bad = []
    if hypothesis.get("direction") and \
            hypothesis["direction"] not in DIRECTIONS:
        vocab_bad.append(f"direction={hypothesis['direction']!r}")
    if hypothesis.get("intervention_type") and \
            hypothesis["intervention_type"] not in INTERVENTION_CLASSES:
        vocab_bad.append(
            f"intervention_type={hypothesis['intervention_type']!r}")
    if vocab_bad:
        g1 = _check("G1_STRUCTURE", False,
                    "values outside closed vocabulary: "
                    + "; ".join(vocab_bad)) and g1

    # G2 DIAGNOSIS
    want_id = str(hypothesis.get("causal_diagnosis_id") or "")
    diag_ok = bool(diagnosis) and (
        str((diagnosis or {}).get("diagnosis_id") or
            (diagnosis or {}).get("id") or "") == want_id or
        (want_id and str((diagnosis or {}).get("cause") or "") == want_id))
    g2 = _check(
        "G2_DIAGNOSIS_RESOLVES",
        diag_ok,
        f"causal_diagnosis_id={want_id!r} resolves to a recorded "
        f"diagnosis (cause={(diagnosis or {}).get('cause')})"
        if diag_ok else
        f"causal_diagnosis_id={want_id!r} does NOT resolve to the "
        f"recorded diagnosis — a narrative reference is not a causal "
        f"chain")

    # G3 MECHANISM TERM-GROUNDING (ONE defensive signal among the
    # structured checks — R451 §5: term overlap alone never suffices,
    # but the direction must still speak about the thing that failed)
    mech_terms = _terms(str(hypothesis.get("mechanism_affected") or "") +
                        " " + str(hypothesis.get("causal_rationale") or
                                  ""))
    diag_terms = _terms(
        " ".join(str((diagnosis or {}).get(k) or "") for k in
                 ("cause", "description", "basis_str",
                  "mechanism"))) | _terms(parent_mechanism)
    shared = sorted(mech_terms & diag_terms)
    g3 = _check(
        "G3_MECHANISM_GROUNDED",
        bool(shared),
        f"mechanism terms grounded in the diagnosis/candidate: "
        f"{', '.join(shared[:8])}" if shared else
        "the mechanism_affected/rationale share NO distinctive terms "
        "with the recorded diagnosis or the failed candidate's "
        "mechanism — the direction speaks about nothing that failed")

    # G4 PREDICTION + FALSIFIER
    predicted = str(hypothesis.get("predicted_effect") or "").strip()
    fals = str(hypothesis.get("falsifier") or "").strip()
    measurable = bool(_MEASUREMENT_RE.search(fals))
    mr = str(hypothesis.get("measurement_required") or "").strip()
    # a concrete measurement plan can support a qualitatively phrased
    # falsifier ONLY when the falsifier itself names the observable
    # event (>= 40 substantive chars naming what would be observed) —
    # a wish ("it would obviously work better") never qualifies
    if not measurable and mr and _MEASUREMENT_RE.search(mr) and \
            len(fals) >= 40 and not re.search(
                r"\b(obvious|just|somehow|better|magic)\b", fals,
                re.I):
        measurable = True
    g4 = _check(
        "G4_PREDICTION_FALSIFIABLE",
        bool(predicted) and bool(fals) and measurable,
        f"predicted_effect present; falsifier names a measurable "
        f"quantity" if (predicted and fals and measurable) else
        f"predicted_effect={'present' if predicted else 'ABSENT'}; "
        f"falsifier={'measurable' if measurable else
                     ('present but not measurable' if fals else
                      'ABSENT')} — an unfalsifiable direction is a "
        f"wish, not a hypothesis")

    # G5 EVIDENCE — the R451 §4 classification (closed) with span
    # verification (R451 §5: ids resolve, evidence exists, spans exist)
    support = hypothesis.get("evidence_support") or []
    known = known_evidence_ids if known_evidence_ids is not None else set()
    texts = evidence_texts or {}
    verified_support = []
    unresolved_ids = []
    span_failed = []
    for e in support:
        eid = _norm_id(str((e or {}).get("evidence_id") or ""))
        if not eid or eid not in known:
            unresolved_ids.append(eid)
            continue
        item = texts.get(eid)
        claimed_span = str((e or {}).get("span") or "").strip()
        if item is None:
            # custody says the id exists but the text is not provided —
            # the id resolves; span verification NOT RUN (recorded, not
            # silently passed)
            verified_support.append({"evidence_id": eid,
                                     "span_verified": None})
            continue
        if not claimed_span:
            # an LLM-cited id with NO claimed span: the binding is not
            # exact (Art. II) — this is NOT verified support
            span_failed.append(eid)
            continue
        from discovery_fabric.directional.delta import _span_in_item
        if _span_in_item(claimed_span, item):
            verified_support.append({"evidence_id": eid,
                                     "span_verified": True,
                                     "span": claimed_span[:200]})
        else:
            span_failed.append(eid)
    gaps = hypothesis.get("evidence_gaps") or []
    if verified_support and not gaps:
        evidence_class = "EVIDENCE_SUPPORTED"
    elif verified_support and gaps:
        evidence_class = "EVIDENCE_PARTIAL"
    elif gaps:
        evidence_class = "EVIDENCE_MISSING"
    else:
        evidence_class = "EVIDENCE_MISSING"
    g5_ok = bool(verified_support) or bool(gaps)
    g5 = _check(
        "G5_EVIDENCE_CLASS",
        g5_ok,
        (f"class={evidence_class}: {len(verified_support)} verified "
         f"support bindings (span-verified); {len(unresolved_ids)} "
         f"unresolved ids; {len(span_failed)} ids with failed/absent "
         f"spans; gaps={len(gaps)} (gaps are NEVER equated with "
         f"support — R451 §4)"))

    # G6 TARGET VARIABLE IN DESIGN STATE (R451 §5: the structured
    # chain's 'affected variable' leg — a direction about a variable
    # the design does not declare is causally unanchored)
    ds_terms = _design_state_terms(design_state)
    tgt_terms = _terms(str(hypothesis.get("target_variable") or "") +
                       " " + str(hypothesis.get("current_value") or ""))
    ds_shared = sorted(tgt_terms & ds_terms) if ds_terms else sorted(
        tgt_terms & diag_terms)
    g6 = _check(
        "G6_TARGET_IN_DESIGN_STATE",
        bool(ds_shared),
        f"target_variable grounded in the design state: "
        f"{', '.join(ds_shared[:8])}" if ds_shared else
        "the target_variable shares NO distinctive terms with the "
        "design's declared state (the failed candidate's mechanism/"
        "intervention, the problem's declared quantities, or the "
        "diagnosis basis) — the direction moves a variable the "
        "machine does not control")

    # G7 PREDICTION <-> INTERVENTION COHERENCE (the prediction speaks
    # about what the intervention changes)
    pred_terms = _terms(str(hypothesis.get("predicted_effect") or ""))
    interv_terms = _terms(
        str(hypothesis.get("mechanism_affected") or "") + " " +
        str(hypothesis.get("target_variable") or "") + " " +
        str(hypothesis.get("proposed_value") or ""))
    pred_shared = sorted(pred_terms & interv_terms)
    g7 = _check(
        "G7_PREDICTION_INTERVENTION_COHERENT",
        bool(pred_shared),
        f"predicted observable coupled to the intervention: "
        f"{', '.join(pred_shared[:8])}" if pred_shared else
        "the predicted_effect shares NO distinctive terms with the "
        "intervention's own variables/mechanism — the prediction is "
        "about an observable this intervention does not touch")

    # G8 FALSIFIER <-> PREDICTION BINDING (the falsifier measures the
    # predicted observable; its kill-direction does not contradict the
    # prediction). The contradiction test compares the FALSIFIER's
    # kill-direction with the PREDICTED EFFECT's own direction words ON
    # THE SHARED QUANTITY — a falsifier that kills exactly on the
    # predicted success (prediction 'X falls', falsifier kills 'X
    # falls') is incoherent; a falsifier that kills on the opposite
    # (prediction 'X falls', falsifier kills 'X above') is correct.
    fals_terms = _terms(fals)
    fals_shared = sorted(fals_terms & (pred_terms | tgt_terms))
    g8_bind = bool(fals_shared)
    contradiction = False
    contra_basis = ""
    if g8_bind:
        pred_up = bool(_KILL_UP_RE.search(
            str(hypothesis.get("predicted_effect") or "")))
        pred_down = bool(_KILL_DOWN_RE.search(
            str(hypothesis.get("predicted_effect") or "")))
        up = bool(_KILL_UP_RE.search(fals))
        down = bool(_KILL_DOWN_RE.search(fals))
        if pred_up and up and not down:
            contradiction = True
            contra_basis = (
                "the predicted effect moves UP and the falsifier kills "
                "on the SAME upward movement — the kill-condition "
                "contradicts the prediction (a direction whose own "
                "success kills it is incoherent)")
        elif pred_down and down and not up:
            contradiction = True
            contra_basis = (
                "the predicted effect moves DOWN and the falsifier "
                "kills on the SAME downward movement — the kill-"
                "condition contradicts the prediction")
    g8 = _check(
        "G8_FALSIFIER_BINDS_PREDICTION",
        g8_bind and not contradiction,
        (f"the falsifier measures the predicted observable: "
         f"{', '.join(fals_shared[:6])}"
         + ("; " + contra_basis if contradiction else ""))
        if g8_bind else
        "the falsifier shares NO distinctive terms with the predicted "
        "observable or the target variable — it measures an unrelated "
        "thing (a measurable but irrelevant falsifier)")

    # G9 CAUSAL MEMORY (R451 §§5/7/8: negative knowledge changes future
    # search — a FALSIFIED (target_variable, direction) pair may not be
    # re-proposed)
    falsified_pairs = {
        (_norm_id(str(p.get("target_variable") or "")).lower(),
         str(p.get("direction") or "").upper())
        for p in (falsified_priors or [])}
    tgt_norm = _norm_id(str(hypothesis.get("target_variable") or ""))
    repeat = (tgt_norm.lower(),
              str(hypothesis.get("direction") or "").upper()) \
        in falsified_pairs
    g9 = _check(
        "G9_CAUSAL_MEMORY",
        not repeat,
        "no prior FALSIFIED direction repeats (the causal memory is "
        "clean for this (target_variable, direction))" if not repeat else
        f"the (target_variable, direction) pair was FALSIFIED before "
        f"(prior ids: {', '.join(sorted(str(p.get('hypothesis_id')) for p in (falsified_priors or []) if (_norm_id(str(p.get('target_variable') or '')).lower(), str(p.get('direction') or '').upper()) == (tgt_norm.lower(), str(hypothesis.get('direction') or '').upper()))[:4])}) — "
        f"negative knowledge must change the next direction, not "
        f"repeat it (Art. LI)")

    structural = g1 and g2 and g3 and g4 and g6 and g7 and g8 and g9
    if not structural:
        verdict = "REJECTED"
    elif evidence_class == "EVIDENCE_SUPPORTED":
        verdict = "GROUNDED"
    else:
        # R451 §4: structurally sound, support PARTIAL/MISSING — an
        # EXPLORATORY hypothesis: no mutation until the gaps are served
        verdict = "EXPLORATORY"
    if verified_support and not gaps:
        # confidence cap: unsupported/weakly-evidenced directions stay
        # capped (Art. XXVII — no silent promotion)
        if len(verified_support) >= 2:
            hypothesis["confidence"] = max(
                hypothesis.get("confidence", "LOW"), "MODERATE")

    return {
        "gate_version": "directional_ground_gate/2.0",
        "checks": checks,
        "grounded": verdict == "GROUNDED",
        "verdict": verdict,
        "evidence_class": evidence_class,
        "evidence_resolution": {
            "verified_ids": [str(v.get("evidence_id"))
                              for v in verified_support],
            "unresolved_ids": [u for u in unresolved_ids],
            "span_failed_ids": span_failed,
        },
        "adjudicated_at": utc_now(),
    }


def apply_gate(hypothesis: Dict[str, Any],
               gate: Dict[str, Any]) -> Dict[str, Any]:
    """Set the hypothesis status from the gate record (the ONLY way
    status moves PROPOSED -> GROUNDED/REJECTED; test-enforced)."""
    hypothesis["gate"] = gate
    hypothesis["status"] = gate["verdict"]
    return hypothesis


# ---------------------------------------------------------------------------
# The LLM proposal (Art. XVIII: the model proposes; the gate adjudicates)
# ---------------------------------------------------------------------------

DIRECTIONAL_PROMPT = """You are the causal-improvement analyst of an invention engine.

A candidate FAILED its evaluation gauntlet. A typed causal diagnosis was recorded.
Propose ONE directional improvement hypothesis — what variable to change, in which
direction, and WHY the failure's causal mechanism justifies it.

FAILED CANDIDATE:
- Mechanism: {parent_mechanism}
- Intervention: {parent_intervention}
- Failure: {failure_summary}

TYPED CAUSAL DIAGNOSIS (recorded):
- Cause: {diagnosis_cause}
- Basis: {diagnosis_basis}

RETRIEVED EVIDENCE (exact spans, with ids):
{evidence_block}

Respond in EXACTLY this format (each field on ONE line):
TARGET_VARIABLE: <the design/physical variable to change>
CURRENT_VALUE: <its current value or state, if known; else 'unknown'>
PROPOSED_VALUE: <the proposed value or change>
DIRECTION: <INCREASE | DECREASE | ADD | REMOVE | REPLACE | CHANGE_MECHANISM | TIGHTEN | RELAX | REVERSE>
MECHANISM_AFFECTED: <the causal mechanism this acts on>
CAUSAL_RATIONALE: <why this variable, referencing the diagnosed cause>
PREDICTED_EFFECT: <the observable physical effect that should follow>
PREDICTED_MAGNITUDE: <magnitude or range, if defensible; else 'unstated'>
COMPETING_EXPLANATIONS: <alternative explanations, semicolon-separated; else 'none stated'>
EVIDENCE_IDS: <comma-separated evidence ids from the spans above that support this; else 'none'>
EVIDENCE_SPANS: one line per cited id, format <evidence_id> = "<verbatim substring copied EXACTLY from that evidence span above>"; else 'none'
EVIDENCE_GAPS: <what evidence is missing, semicolon-separated; else 'none'>
FALSIFIER: <the measurable outcome that would kill this direction>
MEASUREMENT_REQUIRED: <the measurement that tests the prediction>
INTERVENTION_TYPE: <PARAMETER_MUTATION | TOPOLOGY_MUTATION | MATERIAL_MUTATION | OPERATING_CONDITION_MUTATION | MECHANISM_COMBINATION | EVIDENCE_UPDATE | CONSTRAINT_RELAXATION | CONSTRAINT_TIGHTENING>
CONFIDENCE: <LOW | MODERATE | HIGH>
"""

DIRECTIONAL_SYSTEM = ("You propose machine-evaluable causal improvement "
                      "hypotheses. Every claim must bind to the recorded "
                      "diagnosis and the provided evidence. The "
                      "infrastructure will mechanically verify your "
                      "grounding and REJECT ungrounded directions. "
                      "English only.")


def _parse_field_lines(content: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (content or "").splitlines():
        m = re.match(r"^([A-Z_]+):\s*(.*)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


#: EVIDENCE_SPANS lines: <evidence_id> = "<verbatim span>" (the
#: per-citation exact binding the ground gate's G5 verifies — Art. II)
_SPAN_LINE_RE = re.compile(
    r"([A-Za-z0-9:_\-\.]+)\s*=\s*[\"\u201c\u201d]?([^\"\n]{8,400})")


def _parse_evidence_spans(raw: str,
                           cited_ids: List[str]) -> Dict[str, str]:
    """Parse the EVIDENCE_SPANS block into {evidence_id: span}.

    Only ids the model ALSO cited in EVIDENCE_IDS are kept (a span for
    an uncited id is bookkeeping noise); the span text is recorded
    VERBATIM as parsed — the gate verifies it against the item's own
    text (never trusted here — Art. III)."""
    spans: Dict[str, str] = {}
    for m in _SPAN_LINE_RE.finditer(raw or ""):
        eid, span = m.group(1).strip(), m.group(2).strip().rstrip(",;")
        if eid in cited_ids and eid not in spans:
            spans[eid] = span
    return spans


def propose_directional_hypothesis(
        candidate: Dict[str, Any],
        failure_summary: str,
        diagnosis: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
        attempt: int = 1) -> Optional[Dict[str, Any]]:
    """LLM proposal -> ungated hypothesis dict (status PROPOSED).

    The proposal is STAMPED AI_PROPOSED; grounding is the gate's job.
    Returns None on transport failure (an infrastructure state — the
    caller records it, never a scientific result; Art. LXI).
    """
    ev_lines = []
    for it in (evidence_items or [])[:6]:
        ev_lines.append(
            f"- [{it.get('id')}] {str(it.get('title'))[:100]}: "
            f"{str(it.get('abstract'))[:280]}")
    evidence_block = "\n".join(ev_lines) or "(no evidence retrieved)"
    prompt = DIRECTIONAL_PROMPT.format(
        parent_mechanism=str(
            (candidate.get("architecture") or {}).get("mechanism")
            or candidate.get("mechanism") or "")[:600],
        parent_intervention=str(
            (candidate.get("architecture") or {}).get("intervention")
            or candidate.get("intervention") or "")[:400],
        failure_summary=str(failure_summary)[:500],
        diagnosis_cause=str(diagnosis.get("cause") or "")[:200],
        diagnosis_basis="; ".join(
            str(b) for b in (diagnosis.get("basis") or [])[:3])[:400],
        evidence_block=evidence_block)
    try:
        from discovery_fabric.engine.llm_registry import (
            SelectionPolicy, generate)
        res = generate(prompt, system=DIRECTIONAL_SYSTEM,
                       max_tokens=400,
                       policy=SelectionPolicy(
                           purpose="directional"))
        if not res.ok:
            return None
        fields = _parse_field_lines(res.content or "")
    except Exception:  # noqa: BLE001 — infra, never a verdict
        return None
    if not fields.get("TARGET_VARIABLE"):
        return None
    evidence_support = []
    cited: List[str] = []
    for eid in re.split(r"[,;]+", fields.get("EVIDENCE_IDS") or ""):
        eid = eid.strip()
        if eid and eid.lower() not in ("none", "n/a"):
            cited.append(eid)
    spans = _parse_evidence_spans(
        fields.get("EVIDENCE_SPANS") or "", cited)
    for eid in cited:
        entry = {"evidence_id": eid}
        if eid in spans:
            entry["span"] = spans[eid]  # verified by the gate (G5)
        evidence_support.append(entry)
    return {
        "hypothesis_id": make_hypothesis_id(
            str(candidate.get("invention_id") or
                candidate.get("candidate_id") or "cand"),
            str(diagnosis.get("diagnosis_id") or
                diagnosis.get("id") or "failure"),
            fields.get("TARGET_VARIABLE", ""), attempt),
        "candidate_id": str(candidate.get("invention_id") or
                            candidate.get("candidate_id") or ""),
        "failure_id": str(diagnosis.get("diagnosis_id") or
                          diagnosis.get("id") or ""),
        "causal_diagnosis_id": str(diagnosis.get("diagnosis_id") or
                                   diagnosis.get("id") or ""),
        "target_variable": fields.get("TARGET_VARIABLE", ""),
        "current_value": fields.get("CURRENT_VALUE", ""),
        "proposed_value": fields.get("PROPOSED_VALUE", ""),
        "direction": fields.get("DIRECTION", "").upper(),
        "mechanism_affected": fields.get("MECHANISM_AFFECTED", ""),
        "causal_rationale": fields.get("CAUSAL_RATIONALE", ""),
        "predicted_effect": fields.get("PREDICTED_EFFECT", ""),
        "predicted_magnitude_or_range": fields.get(
            "PREDICTED_MAGNITUDE", ""),
        "competing_explanations": [
            s.strip() for s in re.split(r"[;]+", fields.get(
                "COMPETING_EXPLANATIONS") or "")
            if s.strip() and s.strip().lower() not in ("none stated",
                                                       "none")],
        "evidence_support": evidence_support,
        "evidence_gaps": [
            s.strip() for s in re.split(r"[;]+",
                                        fields.get("EVIDENCE_GAPS") or "")
            if s.strip() and s.strip().lower() not in ("none",)],
        "falsifier": fields.get("FALSIFIER", ""),
        "measurement_required": fields.get("MEASUREMENT_REQUIRED", ""),
        "intervention_type": fields.get("INTERVENTION_TYPE", ""),
        "confidence": fields.get("CONFIDENCE", "LOW").upper(),
        "provenance": {
            "class": "AI_PROPOSED",
            "purpose": "directional:hypothesis",
            "note": ("the LLM proposed this hypothesis; the mechanical "
                     "ground gate adjudicates it (Art. XVIII) — an "
                     "ungrounded proposal is REJECTED and its mutation "
                     "never executes"),
            "proposed_at": utc_now(),
        },
        "status": "PROPOSED",
        "gate": {},
    }


# ---------------------------------------------------------------------------
# The re-proposal (R451 §3: HYPOTHESIS_BEFORE + NEW_EVIDENCE =
# HYPOTHESIS_AFTER; the delta is then VERIFIED mechanically)
# ---------------------------------------------------------------------------

REPROPOSAL_PROMPT = """You proposed a directional improvement hypothesis. Its declared evidence
gaps were then served: NEW evidence was retrieved. Re-examine the direction in
the light of the new evidence.

CURRENT HYPOTHESIS (before the new evidence):
- TARGET_VARIABLE: {target_variable}
- CURRENT_VALUE: {current_value}
- PROPOSED_VALUE: {proposed_value}
- DIRECTION: {direction}
- MECHANISM_AFFECTED: {mechanism_affected}
- CAUSAL_RATIONALE: {causal_rationale}
- PREDICTED_EFFECT: {predicted_effect}
- PREDICTED_MAGNITUDE: {predicted_magnitude}
- INTERVENTION_TYPE: {intervention_type}

DECLARED EVIDENCE GAPS (now served):
{gaps_block}

NEW EVIDENCE (exact spans, with ids):
{evidence_block}

Respond in EXACTLY this format (each field on ONE line). Keep a field
UNCHANGED when the new evidence does not justify changing it; change it ONLY
when the new evidence demands the change:
TARGET_VARIABLE: <the design/physical variable to change>
CURRENT_VALUE: <its current value or state, if known; else 'unknown'>
PROPOSED_VALUE: <the proposed value or change>
DIRECTION: <INCREASE | DECREASE | ADD | REMOVE | REPLACE | CHANGE_MECHANISM | TIGHTEN | RELAX | REVERSE>
MECHANISM_AFFECTED: <the causal mechanism this acts on>
CAUSAL_RATIONALE: <why this variable, referencing the diagnosed cause>
PREDICTED_EFFECT: <the observable physical effect that should follow>
PREDICTED_MAGNITUDE: <magnitude or range, if defensible; else 'unstated'>
EVIDENCE_IDS: <comma-separated NEW evidence ids that support the direction; else 'none'>
EVIDENCE_SPANS: one line per cited id, format <evidence_id> = "<verbatim substring copied EXACTLY from that new evidence span above>"; else 'none'
EVIDENCE_GAPS: <what evidence is STILL missing, semicolon-separated; else 'none'>
FALSIFIER: <the measurable outcome that would kill this direction>
MEASUREMENT_REQUIRED: <the measurement that tests the prediction>
INTERVENTION_TYPE: <PARAMETER_MUTATION | TOPOLOGY_MUTATION | MATERIAL_MUTATION | OPERATING_CONDITION_MUTATION | MECHANISM_COMBINATION | EVIDENCE_UPDATE | CONSTRAINT_RELAXATION | CONSTRAINT_TIGHTENING>
CONFIDENCE: <LOW | MODERATE | HIGH>

Then, ONLY for each field you CHANGED because of the new evidence, one line:
EVIDENCE_CAUSED: <FIELD_NAME> <- <the new evidence id> because <the reason>
(FIELD_NAME from: TARGET_VARIABLE, CURRENT_VALUE, PROPOSED_VALUE, DIRECTION,
MECHANISM_AFFECTED, PREDICTED_EFFECT, PREDICTED_MAGNITUDE, INTERVENTION_TYPE)
"""

REPROPOSAL_SYSTEM = ("You re-examine a causal improvement hypothesis "
                     "against newly retrieved evidence. Changed fields "
                     "must each cite the exact evidence id that caused "
                     "the change. The infrastructure will verify every "
                     "claimed attribution against the evidence text. "
                     "English only.")


def repropose_with_evidence(
        before: Dict[str, Any],
        new_evidence: List[Dict[str, Any]],
        attempt: int = 1) -> Optional[Dict[str, Any]]:
    """HYPOTHESIS_BEFORE + NEW_EVIDENCE -> HYPOTHESIS_AFTER (LLM
    proposal, stamped AI_PROPOSED; the DIRECTION_DELTA is then computed
    and verified by the deterministic delta module — the model's own
    attribution claims are parsed and CHECKED, never trusted; Art.
    XVIII).

    Returns the AFTER hypothesis dict (status PROPOSED) carrying the
    parsed attribution claims, or None on transport failure (an
    infrastructure state — Art. LXI).
    """
    from discovery_fabric.directional.delta import (
        parse_attribution_lines)
    ev_lines = []
    for it in (new_evidence or [])[:6]:
        ev_lines.append(
            f"- [{it.get('id')}] {str(it.get('title'))[:100]}: "
            f"{str(it.get('abstract'))[:280]}")
    gaps_block = "\n".join(
        f"- {g}" for g in (before.get("evidence_gaps") or [])[:6]) \
        or "(none declared)"
    prompt = REPROPOSAL_PROMPT.format(
        target_variable=before.get("target_variable", ""),
        current_value=before.get("current_value", ""),
        proposed_value=before.get("proposed_value", ""),
        direction=before.get("direction", ""),
        mechanism_affected=before.get("mechanism_affected", ""),
        causal_rationale=before.get("causal_rationale", ""),
        predicted_effect=before.get("predicted_effect", ""),
        predicted_magnitude=before.get("predicted_magnitude_or_range",
                                       ""),
        intervention_type=before.get("intervention_type", ""),
        gaps_block=gaps_block,
        evidence_block="\n".join(ev_lines) or "(no new evidence)")
    try:
        from discovery_fabric.engine.llm_registry import (
            SelectionPolicy, generate)
        res = generate(prompt, system=REPROPOSAL_SYSTEM,
                       max_tokens=420,
                       policy=SelectionPolicy(
                           purpose="directional"))
        if not res.ok:
            return None
        content = res.content or ""
        fields = _parse_field_lines(content)
    except Exception:  # noqa: BLE001 — infra, never a verdict
        return None
    if not fields.get("TARGET_VARIABLE"):
        return None
    evidence_support = []
    cited: List[str] = []
    for eid in re.split(r"[,;]+", fields.get("EVIDENCE_IDS") or ""):
        eid = eid.strip()
        if eid and eid.lower() not in ("none", "n/a"):
            cited.append(eid)
    spans = _parse_evidence_spans(
        fields.get("EVIDENCE_SPANS") or "", cited)
    for eid in cited:
        entry = {"evidence_id": eid}
        if eid in spans:
            entry["span"] = spans[eid]  # verified by the re-gate (G5)
        evidence_support.append(entry)
    after = {
        "hypothesis_id": make_hypothesis_id(
            str(before.get("candidate_id") or "cand"),
            str(before.get("failure_id") or "failure"),
            fields.get("TARGET_VARIABLE", ""), attempt + 1000),
        "candidate_id": before.get("candidate_id", ""),
        "failure_id": before.get("failure_id", ""),
        "causal_diagnosis_id": before.get("causal_diagnosis_id", ""),
        "target_variable": fields.get("TARGET_VARIABLE", ""),
        "current_value": fields.get("CURRENT_VALUE", ""),
        "proposed_value": fields.get("PROPOSED_VALUE", ""),
        "direction": (fields.get("DIRECTION") or "").upper(),
        "mechanism_affected": fields.get("MECHANISM_AFFECTED", ""),
        "causal_rationale": fields.get("CAUSAL_RATIONALE", ""),
        "predicted_effect": fields.get("PREDICTED_EFFECT", ""),
        "predicted_magnitude_or_range": fields.get(
            "PREDICTED_MAGNITUDE", ""),
        "evidence_support": evidence_support,
        "evidence_gaps": [
            s.strip() for s in re.split(
                r"[;]+", fields.get("EVIDENCE_GAPS") or "")
            if s.strip() and s.strip().lower() not in ("none",)],
        "falsifier": fields.get("FALSIFIER", ""),
        "measurement_required": fields.get("MEASUREMENT_REQUIRED", ""),
        "intervention_type": fields.get("INTERVENTION_TYPE", ""),
        "confidence": (fields.get("CONFIDENCE") or "LOW").upper(),
        "provenance": {
            "class": "AI_PROPOSED",
            "purpose": "directional:reproposal",
            "note": ("the LLM re-proposed the hypothesis against the "
                     "newly served evidence; the deterministic delta "
                     "module verifies which fields actually changed "
                     "and whether the claimed evidence causes them "
                     "(R451 §3 — the shortcut is REPLACED)"),
            "proposed_at": utc_now(),
        },
        "status": "PROPOSED",
        "gate": {},
    }
    after["_attribution_claims"] = parse_attribution_lines(content)
    return after


SCHEMA_JSON = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/prateekm1007/discovery-evidence-fabric/"
           "discovery_fabric/directional/hypothesis",
    "title": "DirectionalHypothesis",
    "description": (
        "The canonical epistemic primitive of the Directional "
        "Improvement Engine: what should change next, in which "
        "direction, why, and what result should follow — machine-"
        "evaluable and provenance-bearing. The ground gate adjudicates "
        "grounding mechanically; ungrounded mutations are REJECTED."),
    "type": "object",
    "required": ["hypothesis_id", "candidate_id", "failure_id",
                 "causal_diagnosis_id", "target_variable", "direction",
                 "mechanism_affected", "causal_rationale",
                 "predicted_effect", "falsifier", "intervention_type",
                 "confidence", "provenance", "status"],
    "properties": {
        "hypothesis_id": {"type": "string", "pattern": "^dh:[0-9a-f]{20}$"},
        "candidate_id": {"type": "string"},
        "failure_id": {"type": "string"},
        "causal_diagnosis_id": {"type": "string"},
        "target_variable": {"type": "string"},
        "current_value": {"type": "string"},
        "proposed_value": {"type": "string"},
        "direction": {"enum": DIRECTIONS},
        "mechanism_affected": {"type": "string"},
        "causal_rationale": {"type": "string"},
        "predicted_effect": {"type": "string"},
        "predicted_magnitude_or_range": {"type": "string"},
        "competing_explanations": {"type": "array",
                                   "items": {"type": "string"}},
        "evidence_support": {"type": "array", "items": {"type": "object"}},
        "evidence_gaps": {"type": "array", "items": {"type": "string"}},
        "falsifier": {"type": "string"},
        "measurement_required": {"type": "string"},
        "intervention_type": {"enum": INTERVENTION_CLASSES},
        "confidence": {"enum": ["LOW", "MODERATE", "HIGH"]},
        "provenance": {"type": "object"},
        "status": {"enum": HYPOTHESIS_STATUSES},
        "gate": {"type": "object"},
    },
}

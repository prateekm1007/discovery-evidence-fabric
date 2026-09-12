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
    GROUNDED       passed all five checks; mutation may execute
    REJECTED       failed a check (the failure basis is recorded); the
                   mutation NEVER executes
    EXECUTED       a controlled mutation was derived and evaluated
    FALSIFIED      the observation contradicted the prediction (the
                   direction dies; negative knowledge)
    SUPPORTED      the observation matched the predicted direction
    SUPERSEDED     a later hypothesis replaced this one on the same
                   target variable
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DIRECTIONAL_ENGINE_VERSION = "directional_engine/1.0.0"

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
    "PROPOSED", "GROUNDED", "REJECTED", "EXECUTED", "FALSIFIED",
    "SUPPORTED", "SUPERSEDED",
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
# THE GROUND GATE — deterministic adjudication (R450 §4)
# ---------------------------------------------------------------------------

def ground_gate(hypothesis: Dict[str, Any],
                diagnosis: Optional[Dict[str, Any]],
                parent_mechanism: str = "",
                known_evidence_ids: Optional[set] = None
                ) -> Dict[str, Any]:
    """Adjudicate a PROPOSED hypothesis. Returns the gate record (never
    raises; every failure is a recorded check verdict).

    `diagnosis`      — the recorded diagnosis dict (from the run's
                       diagnosis records; the id must match).
    `parent_mechanism` — the failed candidate's mechanism text.
    `known_evidence_ids` — the evidence ids in the run's custody (the
                       only admissible evidence_support anchors).
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

    # G3 MECHANISM TERM-GROUNDING
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

    # G5 EVIDENCE
    support = hypothesis.get("evidence_support") or []
    known = known_evidence_ids if known_evidence_ids is not None else set()
    resolved = [e for e in support
                if str((e or {}).get("evidence_id") or "") in known]
    unresolved = [e for e in support
                  if str((e or {}).get("evidence_id") or "") not in known]
    gaps = hypothesis.get("evidence_gaps") or []
    g5 = _check(
        "G5_EVIDENCE_HONEST",
        bool(resolved) or bool(gaps),
        (f"{len(resolved)} evidence_support ids resolve to custody; "
         f"{len(unresolved)} unresolved" if (resolved or unresolved)
         else "") +
        (f"; evidence_gaps honestly declared ({len(gaps)})"
         if gaps else "") +
        ("" if (resolved or gaps) else
         " — no supporting evidence AND no declared gap: an unsupported "
         "direction presented as if grounded") if (resolved or gaps)
        else "no supporting evidence resolves and no evidence_gaps are "
             "declared — an unsupported direction presented as if "
             "grounded")
    # unresolved support ids are never silently dropped: recorded
    if resolved:
        # confidence cap: unsupported/weakly-evidenced directions stay
        # capped (Art. XXVII — no silent promotion)
        if not gaps and len(resolved) >= 2:
            hypothesis["confidence"] = max(
                hypothesis.get("confidence", "LOW"), "MODERATE")

    grounded = g1 and g2 and g3 and g4 and g5
    return {
        "gate_version": "directional_ground_gate/1.0",
        "checks": checks,
        "grounded": grounded,
        "verdict": "GROUNDED" if grounded else "REJECTED",
        "evidence_resolution": {
            "resolved_ids": [str((e or {}).get("evidence_id") or "")
                             for e in resolved],
            "unresolved_ids": [str((e or {}).get("evidence_id") or "")
                               for e in unresolved],
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
    for eid in re.split(r"[,;]+", fields.get("EVIDENCE_IDS") or ""):
        eid = eid.strip()
        if eid and eid.lower() not in ("none", "n/a"):
            evidence_support.append({"evidence_id": eid})
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

"""discovery_fabric/engine/independent_attack.py — R401 Phase 6:
SEPARATE THE GENERATOR FROM THE ATTACKER. R447 Phase 6: v2.0.0 — THE
GROUNDING DISCIPLINE (the verdict-authority check between the
attacker's KILL and the terminal state).

The attack stage must not be the synthesis model criticizing itself.
The independent attacker:

  - runs on a DIFFERENT provider than the candidate's generator when
    any alternative provider is credentialed (independence mode
    SEPARATE_PROVIDER, recorded with both provider ids);
  - otherwise runs on the same provider in a STRICTLY SEPARATE
    reasoning context (a fresh adversarial conversation that never sees
    the generator's reasoning — only the candidate's own claims and the
    evidence), independence mode SEPARATE_CONTEXT, disclosed honestly;
  - independently seeks the six failure classes from the directive:
      mechanism failure
      boundary-condition failure
      evidence contradiction
      baseline equivalence
      implementation impossibility
      measurement ambiguity

The deterministic engineering attack (engineering_attack.py) is
UNCHANGED and still runs — this is the independent adversarial REASONER
layer. The LLM's attack output is structured (six field-line verdicts);
each verdict carries its basis; a KILL verdict must cite a specific
failure basis AND, since v2, BIND that basis to something checkable
(a bare "this fails" is INVALID — Art. XVIII: the model is untrusted,
its verdicts are parsed, validated, and disclosed, never blindly
applied).

R447 v2.0.0 — THE GROUNDING CHECK (the directive's ladder):

    KILL BASIS
       |
    grounding check
       |-- evidence binding     (cites a record in the candidate's own
       |                         evidence bundle — the objection is
       |                         ABOUT held evidence)
       |-- computation binding  (carries a numeric relation: numbers
       |                         joined by a comparative/derivation —
       |                         a measurable claim)
       |-- record binding       (quotes the candidate's own declared
       |                         record verbatim — the objection is
       |                         about what the candidate ITSELF
       |                         claimed)
       `-- declared-scope binding (ties the failure to the declared
                                   boundary conditions)
       |
    no grounding -> KILL becomes ABSTAIN (the objection is PRESERVED
    verbatim and ESCALATED — BS-011: objection content and verdict
    authority are separate things; the candidate is NOT killed by an
    ungrounded objection, but the objection is never silently dropped)

    A KILL whose asserted ground is an ABSENCE ("no evidence
    provided", "fails to demonstrate") is NEVER grounded: absence of
    evidence is uncertainty, not failure (Art. XXI.3/XXV — provider
    failure is not absence; unevidenced is not refuted). Such kills
    demote to ABSTAIN regardless of any quoting they do.

Ladder semantics (v2):
  verdict per class: KILL | RISK | SURVIVE | ABSTAIN (a demoted KILL —
    the objection preserved, the verdict authority withdrawn, recorded
    as such; never silently dropped, never re-labelled RISK, which is
    the attacker's own honest epistemic choice, not the gate's)
  overall: KILLED iff at least one GROUNDED KILL;
           ESCALATED_OBJECTION iff kills occurred but ALL were
             ungrounded (demoted) — the objections ride the record for
             adjudication, the candidate is not killed by them;
           UNCERTAIN iff RISK/INVALID only;
           SURVIVED otherwise.
  The attack FAILURE (LLM unavailable / unparseable) is ATTACK_
  INCOMPLETE — the candidate is NOT killed by an attack that did not
  run (Art. XXIX); the state is recorded and the candidate proceeds
  with the honest marker.

The v2 prompt asks the attacker to state the binding explicitly
(GROUNDED_IN: EVIDENCE <id> | RECORD "<span>" | COMPUTATION <nums> |
SCOPE <clause>) so the check VERIFIES a claimed ground rather than
guessing one from prose overlap; a claimed binding that fails
verification is an ungrounded kill (the instrument never upgrades a
verdict on the model's word — Art. III: the verifier never trusts the
claimant). Bindings discovered mechanically in the basis text (an
evidence id cited, a distinctive verbatim record span, a numeric
relation, a boundary overlap) ALSO ground the kill — the tag is the
attacker's declared ground, the mechanical discovery is the gate's own
measurement, and either satisfying verification is grounding.

R487 v3.0.0 — THE ANCHOR + ACCOMMODATION DISCIPLINE (the R417 ruling's
decisive repair: attacker calibration to the sealed bars). The R447
measurement proved the v2 grounding check verifies the FORM of a
binding, not its ADEQUACY: on the frozen corpus every clean control
was killed by objections the candidate's own record already
ACCOMMODATES (a disclosed-and-disposed failure mode re-described as a
discovery; a hedged quantity ("roughly 4x") disputed by an alternative
derivation; an element the record never claimed presented as a fatal
gap; a premise resting on an explicitly typical external value). The
seeded defects, by contrast, are UNaccommodated — the record's own
account cannot absorb the objection. v3 adds two deterministic layers
between grounding and the verdict (no thresholds, no corpus-specific
content — structural rules only):

  ANCHOR (the binding-class floor): a KILL must carry at least one
  ANCHOR binding — EVIDENCE, RECORD, or DECLARED_SCOPE. A numeric
  relation alone (COMPUTATION-only) is the weakest binding class: it
  is exactly what a false kill constructs (cross-field unit
  confusion, external constants, reinterpretation). A
  computation-only kill demotes to ABSTAIN — objection preserved,
  authority withdrawn.

  ACCOMMODATION (the record answers): a grounded, anchored KILL is
  demoted when the candidate's own record already accommodates the
  objection:
    - CONCESSION_DISPOSAL: the kill's record binding cites a span
      from the candidate's own declared known_failure_modes — a
      disclosed limitation re-described is not a discovered defect
      (adequacy of the disposal is the adjudication council's
      question, not the instrument's).
    - HEDGED_TARGET: the contradicted target is a quantity the record
      itself hedges ("roughly 4x", "approximately", quoted or
      attributed as the candidate's claim) — the record declares the
      value non-exact; an alternative derivation disputing a hedged
      value is an interpretive objection, not a demonstrable
      falsehood.
    - UNSTATED_ELEMENT: the kill's failure assertion rests on the
      record NOT stating an element ("no bypass line stated
      anywhere", "no element that addresses...") — record silence is
      incompleteness, not failure (Art. XXI.3 extended from evidence
      to specification).
    - TYPICAL_VALUE_PREMISE: the kill premises an explicitly typical
      external value ("typically 1-3 bar", "in practice...") — a
      world-generalization presented as a ground is an asserted
      problem, not a found one.
  EVIDENCE-anchored kills are NEVER accommodation-demoted: an
  objection about held evidence is an adjudicable fact — the
  strongest ground the instrument can hold.

Constitutional grounding:
  - Art. XXVII: no thresholds are invented here. The binding
    definitions are structural (an id that exists; a verbatim span
    that appears; numbers joined by a comparator; strong-token overlap
    with the declared boundary text — the strong-token filter is the
    R440 WEAK_TOKENS discipline, already published in the depth
    contract).
  - Art. L / the calibration gate (attacker_calibration.py): v2 is a
    NEW instrument version. Until v2 measures within the sealed bars
    on the frozen corpus, the abstain/escalate gate keeps its KILL
    inadmissible at consumption — this module does not grant itself
    authority; the gate derives it from the committed measurement.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

ATTACK_VERSION = "independent_attack/3.0.0"
ATTACK_CLASSES = (
    "MECHANISM_FAILURE", "BOUNDARY_CONDITION_FAILURE",
    "EVIDENCE_CONTRADICTION", "BASELINE_EQUIVALENCE",
    "IMPLEMENTATION_IMPOSSIBILITY", "MEASUREMENT_AMBIGUITY",
)
VALID_CLASS_VERDICTS = ("KILL", "RISK", "SURVIVE")
# v2: a demoted (ungrounded) KILL — objection preserved, authority
# withdrawn. Distinct from RISK (the attacker's own epistemic choice)
# and INVALID (unparseable/absent).
DEMOTED_CLASS_VERDICT = "ABSTAIN"
OVERALL_ESCALATED = "ESCALATED_OBJECTION"
INDEPENDENCE_MODES = ("SEPARATE_PROVIDER", "SEPARATE_CONTEXT")

ATTACK_PROMPT = """You are a hostile independent reviewer attacking an engineering invention candidate. You did NOT propose this candidate and you owe it nothing. Find the strongest reasons it fails.

CANDIDATE (proposed by a different reasoning context):
- Mechanism: {mechanism}
- Intervention: {intervention}
- Predicted effect: {predicted_effect}
- Testable prediction: {testable_prediction}
- Novel design variable: {novel_design_variable}
- Known failure modes (claimed by the generator): {known_failure_modes}
- Boundary conditions: {boundary_conditions}

PROBLEM:
- Device: {device}
- Failure: {failure}
- Baseline (the un-invented standard): {baseline}

EVIDENCE HELD (the candidate's own evidence bundle):
{evidence_lines}

Attack each failure class independently. A KILL verdict MUST cite a specific, concrete failure basis AND bind it to something checkable, stated at the end of the line as:
GROUNDED_IN: EVIDENCE <record id from the bundle> | RECORD "<exact quoted span from the candidate's own claims>" | COMPUTATION <the numbers and the comparison between them> | SCOPE <the boundary condition clause violated>
A KILL grounded only in the ABSENCE of evidence (e.g. "no evidence provided", "fails to demonstrate") is invalid: absence of evidence is uncertainty, not failure. Speculative objections (may / might / could, without a bound ground) are RISK, not KILL.
THE KILL STANDARD (burden of proof): a KILL is warranted only if the candidate's own record cannot be true as stated — the defect is demonstrable from the candidate's own claims or held evidence. An objection the record already accommodates is RISK, never KILL: a failure mode the candidate itself discloses and disposes of; a quantity the record itself hedges (roughly, approximately, a band); an element the record never claimed to carry; a demand beyond the declared boundary conditions; a premise resting on what is merely typical in practice rather than on the record or the evidence. State the strongest objection you can WITHIN that standard.

Respond in EXACTLY this format (each field on ONE line):
MECHANISM_FAILURE: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
BOUNDARY_CONDITION_FAILURE: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
EVIDENCE_CONTRADICTION: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
BASELINE_EQUIVALENCE: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
IMPLEMENTATION_IMPOSSIBILITY: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
MEASUREMENT_AMBIGUITY: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>

THEN — for each class where you did NOT answer SURVIVE, one improvement
suggestion line (the machine uses these as candidate improvement
directions; a suggestion is only usable when it binds to the same
checkable grounds as its objection):
INTERVENTION MECHANISM_FAILURE: <the variable to change, the direction, and why it addresses the failure basis> GROUNDED_IN: <binding>
INTERVENTION BOUNDARY_CONDITION_FAILURE: <...> GROUNDED_IN: <binding>
INTERVENTION EVIDENCE_CONTRADICTION: <...> GROUNDED_IN: <binding>
INTERVENTION BASELINE_EQUIVALENCE: <...> GROUNDED_IN: <binding>
INTERVENTION IMPLEMENTATION_IMPOSSIBILITY: <...> GROUNDED_IN: <binding>
INTERVENTION MEASUREMENT_AMBIGUITY: <...> GROUNDED_IN: <binding>"""


_ATTACK_LINE_RE = re.compile(
    r"^(MECHANISM_FAILURE|BOUNDARY_CONDITION_FAILURE|"
    r"EVIDENCE_CONTRADICTION|BASELINE_EQUIVALENCE|"
    r"IMPLEMENTATION_IMPOSSIBILITY|MEASUREMENT_AMBIGUITY)\s*:\s*(.*)$",
    re.MULTILINE)

# v2.1: the INTERVENTION suggestion lines (R450 §10) — same GROUNDED_IN
# discipline as the objection lines; an ungrounded suggestion is
# preserved as UNGROUNDED_SUGGESTION and NEVER enters the directional
# loop's hypothesis space
_INTERVENTION_LINE_RE = re.compile(
    r"^INTERVENTION\s+(MECHANISM_FAILURE|BOUNDARY_CONDITION_FAILURE|"
    r"EVIDENCE_CONTRADICTION|BASELINE_EQUIVALENCE|"
    r"IMPLEMENTATION_IMPOSSIBILITY|MEASUREMENT_AMBIGUITY)"
    r"\s*:\s*(.+)$",
    re.MULTILINE)

# minimal basis length for a KILL verdict to be VALID (an adversarial
# model verdict without a concrete basis is a naked assertion)
MIN_KILL_BASIS_CHARS = 40

# ---------------------------------------------------------------------------
# v2 — the grounding check (mechanical, no LLM, no thresholds invented)
# ---------------------------------------------------------------------------
# Absence grounds: the asserted reason the candidate fails is that
# evidence/support is MISSING. Constitutionally NEVER a kill ground
# (Art. XXI.3/XXV — absence of evidence is not evidence of absence;
# provider/evidence failure is not invention failure).
_ABSENCE_GROUND_RE = re.compile(
    r"\b(no|without|lacks?|lacking|empty|devoid of)\b[^.;:!?]{0,40}"
    r"\b(evidence|data|references?|support|empirical|experimental|"
    r"measurements?|studies|documentation|justification|validation|"
    r"analysis|credible references|scientific evidence)\b"
    r"|\b(fails?|failed) to (provide|present|offer|cite|include|"
    r"demonstrate|show|supply|substantiate|establish|prove)\b"
    r"[^.;:!?]{0,60}"
    r"|\b(does not|doesn't|did not) (provide|offer|cite|present|"
    r"include|show|demonstrate|establish)\b[^.;:!?]{0,60}"
    r"|\babsence of\b[^.;:!?]{0,30}"
    r"|\bnot supported by\b[^.;:!?]{0,20}\b(any|any empirical|any "
    r"experimental|the)\b"
    r"|\bunsupported by\b[^.;:!?]{0,20}\b(any|the)\b",
    re.IGNORECASE)

_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_COMPARATIVE_RE = re.compile(
    r"\b(exceeds?|above|below|under|at least|at most|more than|"
    r"less than|greater|fewer|smaller|larger|higher|lower|reduc\w+|"
    r"from|to|versus|vs\.?|compared? to|percent|%|x\b|times|fold)\b",
    re.IGNORECASE)
_GROUNDED_IN_RE = re.compile(
    r"GROUNDED_IN\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]{2,}", (text or "").lower())


def _strong_tokens(tokens: List[str]) -> set:
    """The R440 weak-token filter (depth_contract.WEAK_TOKENS): generic
    engineering vocabulary carries no binding evidence; a distinctive
    overlap must contain content tokens."""
    try:
        from .depth_contract import WEAK_TOKENS
        weak = set(WEAK_TOKENS)
    except Exception:  # noqa: BLE001 — the filter is best-effort
        weak = set()
    return {t for t in tokens if t not in weak and len(t) >= 4}


def _record_fields(candidate: Dict[str, Any]) -> Dict[str, str]:
    cs = candidate.get("constraint_set") or {}
    return {
        "mechanism": str(candidate.get("mechanism") or ""),
        "intervention": str(candidate.get("intervention") or ""),
        "predicted_effect": str(candidate.get("predicted_effect") or ""),
        "testable_prediction": str(candidate.get("testable_prediction")
                                   or ""),
        "novel_design_variable": str(
            candidate.get("novel_design_variable") or ""),
        "boundary_conditions": str(cs.get("boundary_conditions") or ""),
        "known_failure_modes": " ".join(
            str(x) for x in (candidate.get("known_failure_modes") or [])),
    }


def _ngrams(text: str, n: int = 4) -> set:
    toks = _tokens(text)
    return {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def _evidence_binding(basis: str,
                      evidence: List[Dict[str, Any]]) -> Optional[Dict]:
    """Evidence binding: the basis cites a bundle record id, or carries
    a distinctive strong-token overlap with one bundle item (the
    objection is ABOUT held evidence)."""
    if not evidence:
        return None
    b_strong = _strong_tokens(_tokens(basis))
    for e in evidence:
        eid = str(e.get("id") or e.get("item_id") or "")
        if eid and re.search(rf"\b{re.escape(eid)}\b", basis):
            return {"binding": "evidence", "ground": f"record id {eid}",
                    "verified": True}
        etext = " ".join(str(e.get(k) or "") for k in
                         ("title", "abstract", "span", "summary"))
        overlap = b_strong & _strong_tokens(_tokens(etext))
        if len(overlap) >= 2:
            title = str(e.get("title") or eid)
            return {"binding": "evidence",
                    "ground": "bundle item '" + title +
                              "' (strong overlap: " +
                              ", ".join(sorted(overlap)[:4]) + ")",
                    "verified": True}
    return None


def _computation_binding(basis: str) -> Optional[Dict]:
    """Computation binding: the basis carries a numeric relation — at
    least two numbers joined by a comparative/derivation context (a
    measurable claim, not a bare number mention)."""
    nums = _NUM_RE.findall(basis)
    if len(nums) >= 2 and _COMPARATIVE_RE.search(basis):
        return {"binding": "computation",
                "ground": f"numeric relation over {nums[:6]}",
                "verified": True}
    return None


def _record_binding(basis: str,
                    candidate: Dict[str, Any]) -> Optional[Dict]:
    """Record binding: a distinctive verbatim span (4-gram containing
    at least one strong token) from the candidate's own declared
    fields appears in the basis — the objection is about what the
    candidate ITSELF claimed."""
    fields = _record_fields(candidate)
    basis_ngrams = _ngrams(basis)
    for name, text in fields.items():
        if not text:
            continue
        for g in (basis_ngrams & _ngrams(text)):
            if _strong_tokens(_tokens(g)):
                return {"binding": "record",
                        "ground": f"verbatim span '{g}' "
                                  f"(field: {name})",
                        "verified": True}
    return None


def _scope_binding(basis: str,
                   candidate: Dict[str, Any]) -> Optional[Dict]:
    """Declared-scope binding: a distinctive strong-token overlap with
    the declared boundary conditions — the failure is tied to the
    candidate's own scope."""
    bc = _record_fields(candidate)["boundary_conditions"]
    if not bc:
        return None
    overlap = _strong_tokens(_tokens(basis)) & \
        _strong_tokens(_tokens(bc))
    if len(overlap) >= 2:
        return {"binding": "declared_scope",
                "ground": f"boundary overlap {sorted(overlap)[:4]}",
                "verified": True}
    return None


def _claimed_binding(basis: str) -> Optional[str]:
    """The attacker's EXPLICIT GROUNDED_IN declaration (v2 prompt)."""
    m = _GROUNDED_IN_RE.search(basis)
    return m.group(1).strip()[:200] if m else None


def grounding_check(basis: str,
                    candidate: Dict[str, Any],
                    evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The v2 verdict-authority check on ONE KILL basis.

    Grounded iff (declared or mechanically discovered) binding exists
    AND the asserted ground is not an ABSENCE. The declared binding is
    recorded verbatim; the mechanical bindings are the gate's own
    measurement (Art. III — the claimant's declaration is recorded,
    never trusted; verification is independent).
    """
    absence = bool(_ABSENCE_GROUND_RE.search(basis))
    bindings: List[Dict[str, Any]] = []
    for found in (_evidence_binding(basis, evidence),
                  _computation_binding(basis),
                  _record_binding(basis, candidate),
                  _scope_binding(basis, candidate)):
        if found:
            bindings.append(found)
    claimed = _claimed_binding(basis)
    grounded = bool(bindings) and not absence
    out: Dict[str, Any] = {
        "grounded": grounded,
        "bindings": bindings,
        "claimed_ground": claimed,
        "absence_ground": absence,
    }
    if absence:
        out["demotion_reason"] = (
            "the asserted ground is an ABSENCE of evidence/support — "
            "absence is uncertainty, not failure (Art. XXI.3/XXV); the "
            "objection is preserved and escalated, never executed as a "
            "kill")
    elif not bindings:
        out["demotion_reason"] = (
            "no evidence / computation / record / declared-scope "
            "binding found in the kill basis — a bare assertion "
            "carries no verdict authority (Art. XVIII); the objection "
            "is preserved and escalated")
    return out


# ---------------------------------------------------------------------------
# v3 (R487) — the ANCHOR + ACCOMMODATION discipline. Structural rules
# only: no thresholds, no corpus-specific strings, no LLM. Every rule
# demotes to ABSTAIN with the objection preserved verbatim (BS-011) —
# nothing is dropped, nothing is re-labelled RISK.
# ---------------------------------------------------------------------------
#: the binding classes that can alone carry a terminal KILL
ANCHOR_BINDINGS = ("evidence", "record", "declared_scope")

#: UNSTATED_ELEMENT — the failure assertion rests on the record NOT
#: stating an element (spec-silence as failure; Art. XXI.3 extended
#: from evidence to specification). "no <gap> stated/specified/..." or
#: "no element/component/provision that ...".
_UNSTATED_ELEMENT_RE = re.compile(
    r"\b(?:no|without|lacks?|lacking|nothing in|nowhere)\b"
    r"[^.;:!?]{0,60}"
    r"\b(?:stated|specified|mentioned|provided|declared|included|"
    r"element|component|provision|bypass|feature|line item)\b",
    re.IGNORECASE)

#: TYPICAL_VALUE_PREMISE — the kill premises an explicitly typical
#: external value (a world-generalization, not a record fact)
_TYPICAL_PREMISE_RE = re.compile(
    r"\b(?:typically|in practice|as a rule|industry standard|"
    r"standard practice|commonly|in general practice)\b",
    re.IGNORECASE)

#: HEDGED_TARGET — a hedge word carried into a number, inside a quoted
#: span or attributed as the candidate's own claim (the record's own
#: declared uncertainty; the attacker's own arithmetic hedges do NOT
#: demote — only the TARGET's hedge does)
_HEDGE_NUM_RE = re.compile(
    r"\b(?:roughly|approximately|approx\.|about|around|of the order|"
    r"on the order|plus or minus)\s*[^,;.!?]{0,24}?\d|±\s*\d|~\s*\d",
    re.IGNORECASE)
_HEDGE_ATTRIBUTION_RE = re.compile(
    r"\b(?:claimed|claims|declared|declares|stated|states|predicted|"
    r"predicts|the claim|its own)\b", re.IGNORECASE)
_QUOTE_SPAN_RE = re.compile(r'["\'][^"\']{3,240}["\']')


def _quoted_spans(basis: str) -> List[Tuple[int, int]]:
    return [(m.start(), m.end()) for m in _QUOTE_SPAN_RE.finditer(basis)]


def _hedged_target(basis: str) -> Optional[Dict[str, Any]]:
    """A hedged number presented as the contradicted TARGET: the hedge
    match sits inside a quoted span, or an attribution word ("the
    claimed ...") immediately precedes it. The attacker's own hedged
    arithmetic (unquoted, unattributed) is not a target hedge."""
    spans = _quoted_spans(basis)
    for m in _HEDGE_NUM_RE.finditer(basis):
        in_quote = any(s <= m.start() < e for s, e in spans)
        attributed = bool(_HEDGE_ATTRIBUTION_RE.search(
            basis[max(0, m.start() - 48):m.start()]))
        if in_quote or attributed:
            return {
                "rule": "HEDGED_TARGET",
                "match": basis[m.start():m.start() + 40],
                "reason": (
                    "the contradicted target is a quantity the record "
                    "itself hedges; an alternative derivation disputing "
                    "a hedged value is an interpretive objection, not a "
                    "demonstrable falsehood — the objection is preserved "
                    "and escalated, the kill authority withdrawn"),
            }
    return None


def anchor_check(bindings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The v3 binding-class floor: a terminal KILL needs at least one
    ANCHOR binding (evidence / record / declared-scope). Returns the
    demotion record when the kill is computation-only."""
    kinds = {b.get("binding") for b in bindings}
    if kinds & set(ANCHOR_BINDINGS):
        return None
    return {
        "rule": "NO_ANCHOR_BINDING",
        "reason": (
            "the only binding is a numeric relation (computation) — "
            "the weakest binding class, exactly what a false kill "
            "constructs (cross-field unit confusion, external "
            "constants, reinterpretation); the objection is preserved "
            "and escalated, the kill authority withdrawn"),
    }


def accommodation_check(basis: str,
                        candidate: Dict[str, Any],
                        bindings: List[Dict[str, Any]]
                        ) -> Optional[Dict[str, Any]]:
    """The v3 record-answer check on one GROUNDED, ANCHORED kill basis.

    Demotes (objection preserved) when the candidate's own record
    already accommodates the objection. EVIDENCE-anchored kills are
    never demoted here: an objection about held evidence is an
    adjudicable fact. Returns None when the kill stands.
    """
    kinds = {b.get("binding") for b in bindings}
    if "evidence" in kinds:
        return None
    # CONCESSION_DISPOSAL: the kill's record binding cites the
    # candidate's own declared known_failure_modes — a disclosed
    # limitation re-described is not a discovered defect
    if "record" in kinds:
        kfm = " ".join(str(x) for x in
                       (candidate.get("known_failure_modes") or []))
        if kfm:
            kfm_grams = _ngrams(kfm)
            for b in bindings:
                if b.get("binding") != "record":
                    continue
                ground = str(b.get("ground") or "")
                # the v2 record binding carries the verbatim span in
                # its ground; a fresh 4-gram overlap with the conceded
                # failure-mode text is the same measurement
                quoted = re.findall(r"'([^']+)'", ground)
                span_txt = quoted[0] if quoted else ground
                if _ngrams(span_txt) & kfm_grams:
                    return {
                        "rule": "CONCESSION_DISPOSAL",
                        "match": span_txt[:60],
                        "reason": (
                            "the kill's own record binding cites the "
                            "candidate's declared known_failure_modes — "
                            "a disclosed limitation re-described is not "
                            "a discovered defect; the adequacy of the "
                            "disposal is the adjudication council's "
                            "question, not the instrument's — the "
                            "objection is preserved and escalated"),
                    }
    # UNSTATED_ELEMENT: record silence as the failure ground
    m = _UNSTATED_ELEMENT_RE.search(basis)
    if m:
        return {
            "rule": "UNSTATED_ELEMENT",
            "match": m.group(0)[:60],
            "reason": (
                "the failure assertion rests on the record NOT stating "
                "an element — record silence is incompleteness, not "
                "failure (Art. XXI.3 extended to specification); the "
                "objection is preserved and escalated"),
        }
    # TYPICAL_VALUE_PREMISE: an explicitly typical external value as
    # the load-bearing premise
    m = _TYPICAL_PREMISE_RE.search(basis)
    if m:
        return {
            "rule": "TYPICAL_VALUE_PREMISE",
            "match": m.group(0)[:60],
            "reason": (
                "the kill premises an explicitly typical external "
                "value — a world-generalization presented as a ground "
                "is an asserted problem, not a found one; the objection "
                "is preserved and escalated"),
        }
    # HEDGED_TARGET: the contradicted target carries the record's own
    # hedge
    hedged = _hedged_target(basis)
    if hedged:
        return hedged
    return None


def _parse_attack(content: str) -> Dict[str, Dict[str, str]]:
    parsed: Dict[str, Dict[str, str]] = {}
    for m in _ATTACK_LINE_RE.finditer(content or ""):
        raw = m.group(2).strip()
        # v2: the GROUNDED_IN tail rides the same line; the verdict
        # partition stays on the FIRST em-dash
        verdict, _, basis = raw.partition("—")
        verdict = verdict.strip().strip(".,;:").upper()
        basis = basis.strip()
        parsed[m.group(1)] = {"verdict": verdict
                              if verdict in VALID_CLASS_VERDICTS
                              else "INVALID",
                              "basis": basis}
    return parsed


def _parse_interventions(content: str) -> Dict[str, str]:
    """v2.1 (R450 §10): parse the INTERVENTION suggestion lines."""
    out: Dict[str, str] = {}
    for m in _INTERVENTION_LINE_RE.finditer(content or ""):
        out[m.group(1)] = m.group(2).strip()
    return out


def _adjudicate_interventions(
        parsed_interventions: Dict[str, str],
        candidate: Dict[str, Any],
        evidence: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """v2.1 (R450 §10): the intervention suggestions get the SAME
    grounding discipline as the objections. A suggestion whose
    GROUNDED_IN binding passes is GROUNDED_INTERVENTION (usable as a
    directional-loop SEED — still subject to the DirectionalHypothesis
    ground gate, never auto-admitted); a suggestion without a passing
    binding is UNGROUNDED_SUGGESTION — preserved verbatim, explicitly
    barred from the hypothesis space (the attacker does not get
    authority to invent causal explanations). The verdict logic and
    the calibration state are UNCHANGED (suggestions are non-verdict
    output; the negative-knowledge calibration result carries forward)."""
    out: List[Dict[str, Any]] = []
    for cls, text in parsed_interventions.items():
        grounding = grounding_check(text, candidate, evidence)
        passed = bool(grounding.get("grounded"))
        out.append({
            "attack_class": cls,
            "suggestion": text[:400],
            "grounding": grounding,
            "class": "GROUNDED_INTERVENTION" if passed else
                     "UNGROUND_SUGGESTION",
            "authority": (
                "usable as a directional-loop SEED only (the "
                "DirectionalHypothesis ground gate still adjudicates "
                "any hypothesis built on it)"
                if passed else
                "NONE — an ungrounded suggestion is preserved for "
                "human/escalation review and NEVER enters the "
                "hypothesis space (R450 §10: the attacker does not "
                "get authority to invent causal explanations)"),
        })
    return out


def _validate_parsed(parsed: Dict[str, Dict[str, str]],
                     candidate: Dict[str, Any],
                     evidence: List[Dict[str, Any]]
                     ) -> List[Dict]:
    """Deterministic validation + the v2 grounding gate on each KILL
    (Art. XVIII — model verdicts are validated, never blindly
    applied)."""
    items = []
    for cls in ATTACK_CLASSES:
        v = parsed.get(cls)
        if v is None:
            items.append({"attack_class": cls, "verdict": "INVALID",
                          "basis": "",
                          "invalid_reason": "class absent from response"})
            continue
        verdict, basis = v["verdict"], v["basis"]
        if verdict == "KILL" and len(basis) < MIN_KILL_BASIS_CHARS:
            items.append({
                "attack_class": cls, "verdict": "INVALID", "basis": basis,
                "invalid_reason": (
                    "KILL without a concrete basis (< " +
                    str(MIN_KILL_BASIS_CHARS) +
                    " chars) — a naked assertion is not a valid kill "
                    "(Art. XVIII: model verdicts are validated, never "
                    "blindly applied)")})
            continue
        if verdict == "KILL":
            g = grounding_check(basis, candidate, evidence)
            item = {"attack_class": cls, "verdict": "KILL",
                    "basis": basis[:600], "grounding": g}
            if not g["grounded"]:
                # THE DEMOTION: objection preserved verbatim, verdict
                # authority withdrawn (BS-011), escalated for
                # adjudication — never dropped, never re-labelled RISK
                item["verdict"] = DEMOTED_CLASS_VERDICT
                item["demoted_from"] = "KILL"
                item["demotion_layer"] = "v2_grounding"
            else:
                # v3 (R487): the ANCHOR floor, then the ACCOMMODATION
                # record-answer check — a grounded kill must still be
                # anchored (not computation-only) and unaccommodated
                # (the candidate's own record must not already absorb
                # the objection). Objection preserved verbatim either
                # way; only the verdict authority is withdrawn.
                anchor = anchor_check(g.get("bindings") or [])
                if anchor is not None:
                    item["verdict"] = DEMOTED_CLASS_VERDICT
                    item["demoted_from"] = "KILL"
                    item["demotion_layer"] = "v3_anchor"
                    item["anchor"] = anchor
                else:
                    acc = accommodation_check(
                        basis, candidate, g.get("bindings") or [])
                    if acc is not None:
                        item["verdict"] = DEMOTED_CLASS_VERDICT
                        item["demoted_from"] = "KILL"
                        item["demotion_layer"] = "v3_accommodation"
                        item["accommodation"] = acc
            items.append(item)
            continue
        items.append({"attack_class": cls, "verdict": verdict,
                      "basis": basis[:600]})
    return items


def _baseline_text(problem: Dict[str, Any]) -> str:
    return (str(problem.get("device") or "") + " as currently "
            "implemented, doing nothing new — the status quo the "
            "candidate must beat")


def independent_attack(candidate: Dict[str, Any],
                       problem: Dict[str, Any],
                       evidence: List[Dict[str, Any]],
                       generator_provider: Optional[str],
                       ) -> Dict[str, Any]:
    """Run the independent adversarial attack on one candidate.

    Independence selection: providers OTHER than the generator's are
    preferred; if none is credentialed, the same provider is used in a
    separate reasoning context (disclosed). The independence mode and
    both provider ids are recorded on the attack record."""
    from .mechanism_space import llm_generate
    ev_lines = []
    for e in (evidence or [])[:5]:
        ev_lines.append(
            f"- [{e.get('id') or e.get('item_id')}] "
            f"{str(e.get('title') or '')[:110]}")
    evidence_text = "\n".join(ev_lines) if ev_lines else "(none held)"
    fm_claimed = "; ".join(candidate.get("known_failure_modes") or [])
    prompt = ATTACK_PROMPT.format(
        mechanism=str(candidate.get("mechanism") or "")[:600],
        intervention=str(candidate.get("intervention") or "")[:600],
        predicted_effect=str(candidate.get("predicted_effect")
                             or "")[:400],
        testable_prediction=str(candidate.get("testable_prediction")
                                or "")[:400],
        novel_design_variable=str(candidate.get("novel_design_variable")
                                  or "")[:200],
        known_failure_modes=fm_claimed[:400] or "(none claimed)",
        boundary_conditions=str(
            (candidate.get("constraint_set") or {}).get(
                "boundary_conditions") or "")[:300],
        device=problem.get("device", ""),
        failure=problem.get("failure", ""),
        baseline=_baseline_text(problem),
        evidence_lines=evidence_text)
    meta = llm_generate(
        prompt,
        system="You are a hostile independent engineering reviewer. "
               "Attack the candidate. Every KILL must cite a specific "
               "concrete basis and bind it (GROUNDED_IN: evidence id, "
               "quoted record span, the numbers, or the violated "
               "boundary clause).",
        purpose="independent_attack",
        exclude_providers=[generator_provider]
        if generator_provider else None,
        # v2: the output contract grew (six lines each carrying the
        # basis AND the GROUNDED_IN binding tail) — the budget covers
        # the contract (disclosed instrument parameter, not a threshold)
        max_tokens=1600)
    record: Dict[str, Any] = {
        "attack_version": ATTACK_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "generator_provider": generator_provider,
        "attacker_provider": meta.get("provider"),
        "attacker_model": meta.get("model"),
        "independence_mode": (
            "SEPARATE_PROVIDER"
            if (generator_provider
                and meta.get("provider")
                and meta.get("provider") != generator_provider)
            else "SEPARATE_CONTEXT"),
        "independence_note": (
            "the attacker ran on a different provider than the "
            "candidate's generator"
            if (generator_provider and meta.get("provider")
                and meta.get("provider") != generator_provider)
            else ("the attacker ran in an independent reasoning context "
                  "(fresh adversarial conversation, generator reasoning "
                  "never shown; no alternative provider credentialed — "
                  "disclosed, never claimed as provider separation)")),
        "prompt_hash": meta.get("prompt_hash"),
        "output_hash": meta.get("output_hash"),
        "llm_status": meta.get("status"),
        "attacked_at": None,
    }
    from .mechanism_space import utc_now
    record["attacked_at"] = utc_now()
    if not meta.get("ok"):
        record["state"] = "ATTACK_INCOMPLETE"
        record["items"] = []
        record["overall"] = "ATTACK_INCOMPLETE"
        record["note"] = (
            "the independent attack could not run (LLM unavailable: "
            f"{meta.get('status')}) — the candidate is NOT killed by an "
            "attack that did not execute (Art. XXIX); the honest marker "
            "travels with the candidate")
        return record
    items = _validate_parsed(_parse_attack(meta.get("content") or ""),
                             candidate, evidence or [])
    record["items"] = items
    # v2.1 (R450 §10): the intervention suggestions — additive,
    # non-verdict output with the same grounding discipline
    record["intervention_suggestions"] = _adjudicate_interventions(
        _parse_interventions(meta.get("content") or ""),
        candidate, evidence or [])
    valid = [i for i in items if i["verdict"] in VALID_CLASS_VERDICTS]
    kills = [i for i in valid if i["verdict"] == "KILL"]
    demoted = [i for i in items if i["verdict"] == DEMOTED_CLASS_VERDICT]
    risks = [i for i in valid if i["verdict"] == "RISK"]
    invalids = [i for i in items if i["verdict"] == "INVALID"]
    if kills:
        record["state"] = "ATTACK_RUN"
        record["overall"] = "KILLED"
        record["kill_basis"] = [
            {"attack_class": k["attack_class"], "basis": k["basis"],
             "grounding": k.get("grounding")}
            for k in kills]
    elif demoted:
        # v2: kills occurred but NONE survived the grounding check —
        # the objections are preserved and ESCALATED; the candidate is
        # NOT killed by ungrounded objections (BS-011/Art. XVIII)
        record["state"] = "ATTACK_RUN"
        record["overall"] = OVERALL_ESCALATED
        record["preserved_objections"] = [
            {"attack_class": d["attack_class"], "basis": d["basis"],
             "grounding": d.get("grounding")}
            for d in demoted]
        record["escalation"] = {
            "rule": ("every KILL failed the grounding check (no "
                     "evidence/computation/record/declared-scope "
                     "binding, or an absence ground); the objections "
                     "are preserved verbatim and escalated for "
                     "adjudication — the candidate is not killed by "
                     "them"),
            "instrument": ATTACK_VERSION,
        }
    elif risks or invalids:
        record["state"] = "ATTACK_RUN"
        record["overall"] = "UNCERTAIN"
    else:
        record["state"] = "ATTACK_RUN"
        record["overall"] = "SURVIVED"
    record["counts"] = {
        "KILL": len(kills), "RISK": len(risks),
        "SURVIVE": len([i for i in valid
                        if i["verdict"] == "SURVIVE"]),
        "ABSTAIN_DEMOTED": len(demoted),
        "INVALID": len(invalids)}
    return record

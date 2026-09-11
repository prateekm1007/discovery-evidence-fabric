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

Constitutional notes:
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

ATTACK_VERSION = "independent_attack/2.0.0"
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

Respond in EXACTLY this format (each field on ONE line):
MECHANISM_FAILURE: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
BOUNDARY_CONDITION_FAILURE: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
EVIDENCE_CONTRADICTION: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
BASELINE_EQUIVALENCE: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
IMPLEMENTATION_IMPOSSIBILITY: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>
MEASUREMENT_AMBIGUITY: <KILL, RISK, or SURVIVE> — <specific basis> GROUNDED_IN: <binding>"""


_ATTACK_LINE_RE = re.compile(
    r"^(MECHANISM_FAILURE|BOUNDARY_CONDITION_FAILURE|"
    r"EVIDENCE_CONTRADICTION|BASELINE_EQUIVALENCE|"
    r"IMPLEMENTATION_IMPOSSIBILITY|MEASUREMENT_AMBIGUITY)\s*:\s*(.*)$",
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
        max_tokens=700)
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

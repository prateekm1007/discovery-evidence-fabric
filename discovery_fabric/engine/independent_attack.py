"""discovery_fabric/engine/independent_attack.py — R401 Phase 6:
SEPARATE THE GENERATOR FROM THE ATTACKER.

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
layer the directive adds. The LLM's attack output is structured (six
field-line verdicts); each verdict carries its basis; a KILL verdict
must cite a specific failure basis (a bare "this fails" is INVALID and
recorded as such — Art. XVIII: the model is untrusted, its verdicts are
parsed, validated, and disclosed, never blindly applied).

Ladder semantics:
  verdict per class: KILL | RISK | SURVIVE (validated vocabulary)
  overall: KILLED if any valid KILL; else UNCERTAIN if any RISK/INVALID;
  else SURVIVED.
  The attack FAILURE (LLM unavailable / unparseable) is ATTACK_
  INCOMPLETE — the candidate is NOT killed by an attack that did not
  run (Art. XXIX: implementation failure is not mechanism failure); the
  state is recorded and the candidate proceeds with the honest marker.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

ATTACK_VERSION = "independent_attack/1.0.0"
ATTACK_CLASSES = (
    "MECHANISM_FAILURE", "BOUNDARY_CONDITION_FAILURE",
    "EVIDENCE_CONTRADICTION", "BASELINE_EQUIVALENCE",
    "IMPLEMENTATION_IMPOSSIBILITY", "MEASUREMENT_AMBIGUITY",
)
VALID_CLASS_VERDICTS = ("KILL", "RISK", "SURVIVE")
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

Attack each failure class independently. A KILL verdict MUST cite a specific, concrete failure basis (what breaks, which evidence contradicts, which boundary is violated, why the effect equals the baseline, why it cannot be built, or what the prediction fails to pin down). A bare assertion without basis is invalid.

Respond in EXACTLY this format (each field on ONE line):
MECHANISM_FAILURE: <KILL, RISK, or SURVIVE> — <specific basis>
BOUNDARY_CONDITION_FAILURE: <KILL, RISK, or SURVIVE> — <specific basis>
EVIDENCE_CONTRADICTION: <KILL, RISK, or SURVIVE> — <specific basis>
BASELINE_EQUIVALENCE: <KILL, RISK, or SURVIVE> — <specific basis>
IMPLEMENTATION_IMPOSSIBILITY: <KILL, RISK, or SURVIVE> — <specific basis>
MEASUREMENT_AMBIGUITY: <KILL, RISK, or SURVIVE> — <specific basis>"""


_ATTACK_LINE_RE = re.compile(
    r"^(MECHANISM_FAILURE|BOUNDARY_CONDITION_FAILURE|"
    r"EVIDENCE_CONTRADICTION|BASELINE_EQUIVALENCE|"
    r"IMPLEMENTATION_IMPOSSIBILITY|MEASUREMENT_AMBIGUITY)\s*:\s*(.*)$",
    re.MULTILINE)

# minimal basis length for a KILL verdict to be VALID (an adversarial
# model verdict without a concrete basis is a naked assertion)
MIN_KILL_BASIS_CHARS = 40


def _parse_attack(content: str) -> Dict[str, Dict[str, str]]:
    parsed: Dict[str, Dict[str, str]] = {}
    for m in _ATTACK_LINE_RE.finditer(content or ""):
        raw = m.group(2).strip()
        verdict, _, basis = raw.partition("—")
        verdict = verdict.strip().strip(".,;:").upper()
        basis = basis.strip()
        parsed[m.group(1)] = {"verdict": verdict
                              if verdict in VALID_CLASS_VERDICTS
                              else "INVALID",
                              "basis": basis}
    return parsed


def _validate_parsed(parsed: Dict[str, Dict[str, str]]) -> List[Dict]:
    """Deterministic validation of the parsed attack (Art. XVIII)."""
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
                    f"KILL without a concrete basis (< "
                    f"{MIN_KILL_BASIS_CHARS} chars) — a naked assertion is "
                    "not a valid kill (Art. XVIII: model verdicts are "
                    "validated, never blindly applied)")})
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
               "concrete basis.",
        purpose="independent_attack",
        exclude_providers=[generator_provider]
        if generator_provider else None,
        max_tokens=600)
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
    items = _validate_parsed(_parse_attack(meta.get("content") or ""))
    record["items"] = items
    valid = [i for i in items if i["verdict"] in VALID_CLASS_VERDICTS]
    kills = [i for i in valid if i["verdict"] == "KILL"]
    risks = [i for i in valid if i["verdict"] == "RISK"]
    invalids = [i for i in items if i["verdict"] == "INVALID"]
    if kills:
        record["state"] = "ATTACK_RUN"
        record["overall"] = "KILLED"
        record["kill_basis"] = [
            {"attack_class": k["attack_class"], "basis": k["basis"]}
            for k in kills]
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
        "INVALID": len(invalids)}
    return record

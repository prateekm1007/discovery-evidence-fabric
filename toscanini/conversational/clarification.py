"""toscanini/conversational/clarification.py — R446-C1 §4: the
ask-only-when-material decision rule.

Directive (verbatim intent):
    "Ask the user only when the answer can materially change the
     discovery search space or next action.
     Do not turn the product into a questionnaire."

The rule is a deterministic INFORMATION-EFFICIENCY test, not a
questionnaire generator: every candidate question is scored

    materiality  (does the answer change the search space / next
                  action — scored per field from the PU contract)
  × uncertainty  (is the field currently UNKNOWN or contested)
  × answerability (can ONE short user sentence actually resolve it)

and ONLY the single highest-scoring question above threshold is asked
(at most ONE per pause — the directive's "one useful clarification").

Bad pattern (directive, verbatim):  "Select your industry."
Good pattern  (directive, verbatim): "Should the solution preserve the
current outer diameter?"

The difference is the JOIN: a good question names the CURRENT inferred
reading, the ALTERNATIVE reading, and the DECISION the answer changes.
A question whose answer changes nothing (search space identical either
way) is never asked — that is the questionnaire failure mode, refused
by construction here (scored 0 on materiality).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from toscanini.conversational import problem_understanding as pu_mod

# Materiality per PU field: what decision the answer changes. Fields
# absent from this table are NEVER asked about (materiality 0 — the
# questionnaire guard).
_FIELD_MATERIALITY: Dict[str, Dict[str, Any]] = {
    "target_variable": {
        "materiality": 1.0,
        "decision_changed": "which quantity the engine optimizes and "
                            "which mechanisms are even admissible "
                            "(the whole candidate search space keys on "
                            "this)",
        "question_template":
            "You asked to {outcome} — should the engine optimize "
            "{candidate_a}, or {candidate_b}?",
    },
    "desired_outcome": {
        "materiality": 0.9,
        "decision_changed": "the objective the invention is scored "
                            "against and the success condition",
        "question_template":
            "What outcome do you want: {candidate_a}, or something "
            "else (e.g. {candidate_b})?",
    },
    "observed_failure": {
        "materiality": 0.8,
        "decision_changed": "whether the problem-existence gate "
                            "(Art. XX) can be attempted and which "
                            "evidence sources are queried",
        "question_template":
            "Is there a specific failure you have observed (e.g. "
            "{candidate_a}), or is this an opportunity-shaped problem?",
    },
    "constraints": {
        "materiality": 0.7,
        "decision_changed": "which engineering realizations are "
                            "admissible (boundary conditions, Art. XLI)",
        "question_template":
            "Should the solution preserve the current {candidate_a}?",
    },
    "physical_system": {
        "materiality": 0.6,
        "decision_changed": "domain routing and which retrieval "
                            "connectors serve the run",
        "question_template":
            "Which physical system is in scope: {candidate_a}?",
    },
}

# Fields never worth a question (context, assumptions, success/failure
# condition are DERIVED; domain is routed by keyword with honest
# general fallback — "select your industry" is the directive's own
# bad example, refused here by construction).
_NEVER_ASK = ("problem_statement", "context", "domain_hypothesis",
              "assumptions", "success_condition", "failure_condition")

ASK_THRESHOLD = 0.35   # (materiality × uncertainty × answerability)


def _candidate_questions(pu: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Score every askable field from the PU's OWN typed fields.
    Deterministic; zero LLM."""
    out: List[Dict[str, Any]] = []
    unknowns = {u.get("field") for u in pu.get("unknowns") or []}
    for field, spec in _FIELD_MATERIALITY.items():
        rec = pu.get(field) or {}
        origin = rec.get("origin") or pu_mod.ORIGIN_UNKNOWN
        if field in _NEVER_ASK:
            continue
        if origin == pu_mod.ORIGIN_USER_STATED:
            # the user already stated it — nothing to ask
            continue
        uncertainty = 1.0 if field in unknowns else \
            0.4 if origin == pu_mod.ORIGIN_INFERRED_MODEL else 0.0
        if uncertainty <= 0.0:
            continue
        # the user-statement propagation rule: when the field was
        # derived FROM a USER_STATED field (e.g. the target variable
        # extracted from the user's own outcome phrase, or a constraint
        # restated by the user's objective), the ambiguity is LOW —
        # asking would be a questionnaire, not a decision input
        # (directive §4: the tubing example must run autonomously).
        if uncertainty > 0.2 and _derivable_from_user_stated(field, pu):
            uncertainty = 0.2
        value = rec.get("value")
        if isinstance(value, list) and value:
            value = value[0]
        out.append({
            "field": field,
            "materiality": spec["materiality"],
            "uncertainty": uncertainty,
            "answerability": 1.0,   # one short user sentence resolves it
            "score": round(spec["materiality"] * uncertainty * 1.0, 3),
            "current_reading": value,
            "decision_changed": spec["decision_changed"],
            "template": spec["question_template"],
        })
    out.sort(key=lambda q: (-q["score"], q["field"]))
    return out


def _derivable_from_user_stated(field: str, pu: Dict[str, Any]) -> bool:
    """Deterministic propagation check: is this INFERRED field's value
    contained in (or derived from) a field the USER stated verbatim?"""
    rec = pu.get(field) or {}
    value = rec.get("value")
    if not value:
        return False
    if not isinstance(value, list):
        value = [value]
    stated_fields = [pu.get(f) or {} for f in
                     ("desired_outcome", "observed_failure",
                      "problem_statement", "constraints")]
    stated_texts = []
    for sf in stated_fields:
        if sf.get("origin") != pu_mod.ORIGIN_USER_STATED:
            continue
        v = sf.get("value")
        if isinstance(v, list):
            stated_texts.extend(str(x).lower() for x in v)
        elif isinstance(v, str):
            stated_texts.append(v.lower())
        elif isinstance(v, dict):
            stated_texts.append(json.dumps(v).lower())
    for v in value:
        vv = str(v).lower().strip()
        if vv and any(vv in t for t in stated_texts):
            return True
    return False


def _question_sentence(q: Dict[str, Any], pu: Dict[str, Any]
                       ) -> str:
    """Render ONE information-efficient question: current reading +
    alternative + the decision it changes. Never a bare selector."""
    field = q["field"]
    current = q.get("current_reading")
    if isinstance(current, list) and current:
        current = current[0]
    failure = pu.get("observed_failure") or {}
    failure_v = failure.get("value")
    if isinstance(failure_v, list) and failure_v:
        failure_v = failure_v[0]
    outcome = pu.get("desired_outcome") or {}
    outcome_v = outcome.get("value")
    if isinstance(outcome_v, list) and outcome_v:
        outcome_v = outcome_v[0]

    # UNKNOWN readings get failure/outcome-anchored questions (the two
    # plausible readings are REAL alternatives from the record, never
    # invented ones)
    if field == "desired_outcome" and not current:
        if failure_v:
            return (f"You mentioned {failure_v} — what outcome do you "
                    f"want: reduce the {failure_v} itself, or manage "
                    f"its cost/consequence?".replace("the our ", "the "))
        return ("What outcome do you want from this investigation "
                "(what should improve)?")
    if field == "target_variable" and not current:
        if outcome_v:
            return (f"You asked to {outcome_v} — which quantity should "
                    f"the engine treat as the target variable?")
        return ("Which quantity should the engine optimize as the "
                "target of this problem?")
    if field == "observed_failure" and not current:
        return ("Is there a specific failure you have observed, or is "
                "this an opportunity-shaped problem (a capability you "
                "want but do not have)?")
    if field == "constraints" and not current:
        return ("Are there constraints any solution must preserve "
                "(dimensions, materials, cost, regulations)?")

    tmpl = q["template"]
    current = current or "the quantity in your message"
    outcome_v = outcome_v or "improve the system"
    alt = _alternative_reading(field, pu)
    return tmpl.format(candidate_a=str(current), candidate_b=alt,
                       outcome=str(outcome_v))


def _alternative_reading(field: str, pu: Dict[str, Any]) -> str:
    """The strongest competing reading from the PU's own recorded
    evidence (deterministic — the alternative must be REAL, not
    invented: taken from the domain scores, the fallback targets, or
    the generic complement)."""
    if field == "target_variable":
        targets = (pu.get("target_variable") or {}).get("value")
        if isinstance(targets, list) and len(targets) > 1:
            return f"instead prioritize {targets[1]}"
        return "a different quantity entirely"
    if field == "desired_outcome":
        return "keep the current behavior but make it cheaper or simpler"
    if field == "observed_failure":
        return "no specific failure — you want a capability you do not have"
    if field == "constraints":
        return "free to change it if the improvement justifies it"
    if field == "physical_system":
        scores = pu.get("domain_scores") or []
        if scores:
            return f"something in the {scores[0]['domain_hypothesis']} family"
        return "the whole assembly"
    return "another reading"


def evaluate_clarification_need(pu: Dict[str, Any]) -> Dict[str, Any]:
    """The decision rule. Returns:
      needed            bool — is ONE question worth the user's time
      question          the rendered question (when needed)
      field             which PU field the answer fills
      decision_changed  what changes once answered (the materiality
                        join — why this question is not a questionnaire)
      candidates_considered / refused  the full scored ledger, so the
                        refusal to ask is itself auditable (Art. XV)
    """
    candidates = _candidate_questions(pu)
    refused = [c for c in candidates if c["score"] < ASK_THRESHOLD]
    askable = [c for c in candidates if c["score"] >= ASK_THRESHOLD]
    if not askable:
        return {
            "needed": False,
            "reason": ("no field passes the information-efficiency "
                       "threshold — asking would be a questionnaire, "
                       "not a decision input"),
            "threshold": ASK_THRESHOLD,
            "candidates_considered": candidates,
            "refused": refused,
        }
    best = askable[0]
    return {
        "needed": True,
        "field": best["field"],
        "question": _question_sentence(best, pu),
        "decision_changed": best["decision_changed"],
        "score": best["score"],
        "threshold": ASK_THRESHOLD,
        "candidates_considered": candidates,
        "refused": refused,
        "rule": ("ask iff max(materiality × uncertainty × "
                 "answerability) >= threshold; at most ONE question "
                 "per pause"),
    }

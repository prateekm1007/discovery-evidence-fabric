"""Answer-Shape Contract (R3) — deterministic, question-type routed.

Predictor-design answers MUST carry {indicator, numeric threshold with
units, validation protocol with n and pass/fail}. Intervention-proposal
answers MUST name concrete parameters, each labeled EVIDENCE-BACKED or
ASSUMPTION. The check is deterministic and runs against the answer text
the judge sees (Art. XXIV: no heuristics-only judging of shape).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# Unit alternation: word-boundary units plus bare percent. "10%"
# cannot match a \b-guarded `%` (space or EOL follows %, both are
# non-word chars), so percent rides its own alternation.
_UNIT_WORD = (r"(?:mA|A|kA|mV|V|kV|kW|W|kJ|J|Hz|rpm|°C|C|K|Pa|kPa|MPa|GPa|"
              r"N|kN|mm|cm|m|µm|nm|g|kg|mg|t|L|mL|ppm|mol|mol/L|s|ms|h|"
              r"days?|cycles?|percent)\b")
_UNIT = r"(?:" + _UNIT_WORD + r"|%)"
_NUM_WITH_UNIT = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*)?\d+(?:\.\d+)?\s*" + _UNIT)


def _has_number_with_unit(text: str) -> bool:
    return bool(_NUM_WITH_UNIT.search(text or ""))


def _count_matches(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text or "", re.IGNORECASE))


def validate_answer(answer: str, question_type: str
                  ) -> Dict[str, Any]:
    """Return {'valid': bool, 'violations': [str]}.

    Deterministic; zero LLM. Used by the eval harness to flag released
    answers, and by the engine's answer-shape routing."""
    violations: List[str] = []
    text = answer or ""
    if question_type == "predictor-design":
        if not re.search(r"indicator", text, re.IGNORECASE):
            violations.append("predictor contract: no 'indicator' declared")
        if not _has_number_with_unit(text):
            violations.append(
                "predictor contract: no numeric threshold with units")
        if not re.search(r"(pass|fail|threshold|n\s*=|sample size|"
                         r"validation protocol)", text, re.IGNORECASE):
            violations.append(
                "predictor contract: no validation protocol (n + pass/fail)")
        # protocol must carry a sample count or a n= clause
        if not re.search(r"n\s*=\s*\d+|\d+\s*(devices|samples|units|"
                         r"machines|pumps|bearings|fans|vehicles|"
                         r"cases)", text, re.IGNORECASE):
            violations.append(
                "predictor contract: no n=\u2026 sample-count stated")
    elif question_type == "intervention-proposal":
        if not re.search(r"EVIDENCE-BACKED|ASSUMPTION", text):
            violations.append(
                "intervention contract: concrete parameter not labeled "
                "EVIDENCE-BACKED or ASSUMPTION")
        if not _has_number_with_unit(text):
            violations.append(
                "intervention contract: no concrete numeric parameter")
        if not re.search(r"(falsif|test|measure|monitor|hold|cycle|"
                         r"A/B|protocol)", text, re.IGNORECASE):
            violations.append(
                "intervention contract: no concrete test/measure named")
    else:
        violations.append(f"unknown question_type {question_type!r}")
    return {"valid": not violations, "violations": violations,
            "question_type": question_type}


ANSWER_SHAPE_BLOCK = {
    "predictor-design": (
        "\nANSWER-SHAPE CONTRACT (predictor-design) — your answer MUST state, "
        "explicitly and in this order:\n"
        "INDICATOR: <the measurable quantity you will monitor>\n"
        "THRESHOLD: <number with units, the alert/failure level>\n"
        "PROTOCOL: <how you validate; state n (sample count) and the "
        "pass/fail criterion>\n"),
    "intervention-proposal": (
        "\nANSWER-SHAPE CONTRACT (intervention-proposal) — your answer MUST "
        "name concrete parameters and label EACH of them EVIDENCE-BACKED "
        "(directly supported by a packet record) or ASSUMPTION (your "
        "engineering assumption):\n"
        "PARAMETER: <name> — <value with units> — EVIDENCE-BACKED | ASSUMPTION\n"
        "(one line per parameter)\n"),
}

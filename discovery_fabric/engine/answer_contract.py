"""Answer-Shape Contract (R3) — deterministic, question-type routed.

Predictor-design answers MUST carry explicit {INDICATOR, THRESHOLD with
units, VALIDATION with n and pass/fail} markers, and the THRESHOLD number
must be traceable to the evidence packet or to a user-stated variable.
Intervention-proposal answers MUST name concrete parameters, each labeled
EVIDENCE-BACKED or ASSUMPTION; EVIDENCE-BACKED parameters must bind to a
source id present in the packet. The check is deterministic and runs
against the answer text the judge sees (Art. XXIV).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

_UNIT_WORD = (r"(?:mA|A|kA|mV|V|kV|kW|W|kJ|J|Hz|rpm|°C|C|K|Pa|kPa|MPa|GPa|"
              r"N|kN|mm|cm|m|µm|nm|g|kg|mg|t|L|mL|ppm|mol|mol/L|s|ms|h|"
              r"days?|cycles?|percent|pC|mC|nC|fC)\b")
_UNIT = r"(?:" + _UNIT_WORD + r"|%)"
_NUM_WITH_UNIT = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*)?\d+(?:\.\d+)?\s*" + _UNIT)
_THRESHOLD_MARK = re.compile(r"THRESHOLD\s*:", re.IGNORECASE)
_INDICATOR_MARK = re.compile(r"INDICATOR\s*:", re.IGNORECASE)
_VALIDATION_MARK = re.compile(r"(?:VALIDATION(?:\s+PROTOCOL)?|PROTOCOL)\s*:",
                              re.IGNORECASE)
_ASSUMPTION_LINE = re.compile(r"\bASSUMPTION\b", re.IGNORECASE)
_EVIDENCE_BACKED = re.compile(r"\bEVIDENCE-BACKED\b", re.IGNORECASE)


def _packet_blob(packet) -> str:
    if not packet:
        return ""
    try:
        parts = []
        for e in packet:
            if isinstance(e, dict):
                parts.append(str(e.get("id") or ""))
                parts.append(str(e.get("doi") or ""))
                parts.append(str(e.get("abstract") or e.get("text") or
                                e.get("content") or ""))
                parts.append(str(e.get("title") or ""))
        return " ".join(parts)
    except Exception:  # noqa: BLE001
        return json.dumps(packet or [], ensure_ascii=False)


def _numbers(text: str) -> List[str]:
    return re.findall(r"\d+(?:\.\d+)?", text or "")


def _threshold_number(text: str) -> Optional[str]:
    m = re.search(r"THRESHOLD\s*:\s*(\d+(?::\.\d+)?)", text or "",
                  re.IGNORECASE)
    if not m:
        m2 = re.search(r"THRESHOLD\s*:\s*([^\\n\\.]{1,40})", text or "",
                       re.IGNORECASE)
        if not m2:
            return None
        # take first number-with-unit match inside the line
        mm = re.search(r"\d+(?:\.\d+)?", m2.group(1))
        return mm.group(0) if mm else None
    return m.group(1)


def _has_number_with_unit(text: str) -> bool:
    return bool(_NUM_WITH_UNIT.search(text or ""))


def _count_matches(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text or "", re.IGNORECASE))


def validate_answer(answer: str, question_type: str,
                    packet: Optional[List[Dict[str, Any]]] = None,
                    user_variables: Optional[List[str]] = None
                    ) -> Dict[str, Any]:
    """Return {'valid': bool, 'violations': [str], 'bindings': {...}}.

    Deterministic; zero LLM. Used by the eval harness to flag released
    answers, and by the engine's answer-shape routing."""
    violations: List[str] = []
    text = answer or ""
    blob = (_packet_blob(packet)
            + " " + " ".join(user_variables or [])).lower()
    bindings = {"evidence_bound": 0, "assumption": 0, "unbound_numbers": 0,
                "all_numbers": 0}

    if question_type == "predictor-design":
        if not re.search(r"INDICATOR\s*:", text, re.IGNORECASE):
            violations.append("predictor contract: no INDICATOR: declared")
        if not re.search(r"THRESHOLD\s*:", text, re.IGNORECASE):
            violations.append("predictor contract: no THRESHOLD: declared")
        if not re.search(r"(?:VALIDATION(?:\s+PROTOCOL)?|PROTOCOL)\s*:",
                         text, re.IGNORECASE):
            violations.append(
                "predictor contract: no VALIDATION PROTOCOL: declared")
        if not _has_number_with_unit(text):
            violations.append(
                "predictor contract: no numeric threshold with units")
        # protocol must carry explicit n= or sample count
        if not re.search(r"n\s*=\s*\d+|\d+\s*(devices|samples|units|"
                         r"machines|pumps|bearings|fans|vehicles|"
                         r"cases)", text, re.IGNORECASE):
            violations.append(
                "predictor contract: no n=\u2026 sample-count stated")
        # THRESHOLD must be tied to the named indicator
        m_ind = re.search(r"INDICATOR\s*:([^\n]{1,200})", text,
                          re.IGNORECASE | re.DOTALL)
        if m_ind:
            ind_line = m_ind.group(1).lower()
            m_thr = re.search(r"THRESHOLD\s*:\s*([^\n]{1,200})", text,
                              re.IGNORECASE | re.DOTALL)
            if m_thr:
                thr_line = m_thr.group(1).lower()
                ind_tokens = set(re.findall(r"[a-z]{4,}", ind_line))
                thr_tokens = set(re.findall(r"[a-z]{4,}", thr_line))
                if ind_tokens and thr_tokens and not (
                        ind_tokens & thr_tokens):
                    violations.append(
                        "predictor contract: THRESHOLD not tied to "
                        "INDICATOR (no shared content word)")
        # threshold number must appear in packet or user variables
        thr_num = _threshold_number(text)
        if thr_num and blob:
            if thr_num not in blob:
                violations.append(
                    "predictor contract: THRESHOLD number "
                    f"{thr_num} not found in evidence packet or "
                    "user variables")
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
        # every EVIDENCE-BACKED parameter must bind to a packet source id
        pb = _packet_blob(packet).lower() if packet else ""
        for m in _EVIDENCE_BACKED.finditer(text):
            # look at the 80-char window before the label for an id, or
            # the same line for the cited value
            win = text[max(0, m.start() - 200):m.start() + 80]
            ids = re.findall(r"\[[\w./-]+?\]|https?://\S+|"
                             r"(?:paper|study|record|survey)-?\d+",
                             win, re.IGNORECASE)
            if not ids:
                violations.append(
                    "intervention contract: EVIDENCE-BACKED label "
                    "without a referenced source id or evidence citation")
            else:
                any_hit = False
                for i in ids:
                    if i.lower().strip("[]\n \t") in pb:
                        any_hit = True
                        break
                if not any_hit:
                    violations.append(
                        "intervention contract: EVIDENCE-BACKED source id "
                        "not found in evidence packet")
    else:
        violations.append(f"unknown question_type {question_type!r}")
    # numbers in answer not always from packet or user vars -> assumption or unbound
    for n in set(_numbers(text)):
        bindings["all_numbers"] += 1
        if blob and n in blob:
            bindings["evidence_bound"] += 1
        elif re.search(r"\bASSUMPTION\b", text[max(0, text.find(n) - 80):text.find(n) + 80],
                       re.IGNORECASE):
            bindings["assumption"] += 1
        else:
            bindings["unbound_numbers"] += 1
    return {"valid": not violations, "violations": violations,
            "question_type": question_type,
            "bindings": bindings}


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

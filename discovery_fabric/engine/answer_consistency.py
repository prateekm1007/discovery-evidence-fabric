"""discovery_fabric/engine/answer_consistency.py — ONE PRIMARY
CANDIDATE + the design-consistency check (owner audit round
2026-11-13, directive 1).

MEASURED DEFECT (the committed new07 pair, answer sha f428872d, run
1fcf5fe53a49): the composer mixed two designs into one answer — a
sensible packet-grounded thermal indicator (top-oil temperature rate
normalized by load current) as the lead design, with nanofluid claims
from the DIFFERENT nanofluid candidate bolted on; the falsification
test then compared nanofluid-enhanced vs conventional transformers,
which does not test the stated indicator. Mechanism, indicator/
intervention and falsification test must describe ONE thing.

What this module does (deterministic, zero-LLM, never a new gate —
it rides the EXISTING compose -> validate -> repair loop like the
constraint audit; its violation lines join the same scheduled repair
call so the call budget is unchanged):

  1. ONE PRIMARY CANDIDATE (prompt-side, wired in answer_composer):
     candidates[0] is THE proposal the composer writes; candidates[1:]
     are NAMED ALTERNATIVES the composer must NOT mix in.

  2. CONSISTENCY CHECK (this module): the composed answer's lead
     design segment (INDICATOR / INTERVENTION / PARAMETER lines) and
     its falsification test must describe the SAME design, and no
     named alternative's design vocabulary may leak into the answer.
     Violations are typed; the unknown stays unknown (a scan that
     cannot find the sections records CHECK_ABSENT, never a pass —
     Art. XXV).

Serves: Art. XIX (fix the measured failure, not a gate), Art. X
(labels describe the actual delivery), Art. XXVII (no new threshold —
every rule below is a binary membership/overlap test on recorded
bytes), Art. LXXVII (the answer is the deliverable).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

ANSWER_CONSISTENCY_VERSION = "answer_consistency/1.0.0"

#: the falsification-test marker vocabulary (mirrors the answer
#: contract's own test detection — one split authority, Art. X)
_TEST_MARKER_RE = re.compile(
    r"(?:falsification\s+test|falsifies|kill\s+criteria?|"
    r"validation\s+(?:protocol|test)|pass\s+criteria?)\s*:",
    re.IGNORECASE)
#: the lead DESIGN segment markers (PARAMETER is deliberately absent:
#: a quantity line is the design's own spec, never a second design)
_LEAD_SEGMENT_RE = re.compile(
    r"\b(?:INDICATOR|INTERVENTION|MECHANISM|PROPOSAL|"
    r"RECOMMENDATION)\s*:", re.IGNORECASE)
_THING_MARKERS_RE = re.compile(
    r"\b(?:INDICATOR|THRESHOLD|PROTOCOL|VALIDATION(?:\s+PROTOCOL)?|"
    r"PARAMETER|INTERVENTION)\s*:", re.IGNORECASE)

#: generic engineering scaffolding — never a design discriminator
_GENERIC_TOKENS = frozenset({
    "this", "that", "with", "from", "which", "when", "where", "while",
    "then", "than", "thus", "also", "into", "onto", "over", "under",
    "between", "because", "therefore", "however", "additionally",
    "furthermore", "based", "using", "used", "uses", "must", "should",
    "will", "would", "can", "could", "may", "might", "shall",
    "have", "has", "been", "being", "were", "each", "both", "such",
    "more", "less", "least", "most", "very", "same", "other", "another",
    "and", "the", "for", "but", "not", "its", "are", "was", "had",
    "these", "those", "all", "any", "one", "two", "three", "per",
    "via", "due", "about", "against", "among", "some", "only", "own",
    "so", "too", "nor", "yet", "their", "them", "they", "our", "you",
    "your", "his", "her", "him", "she", "who", "whom", "whose", "out",
    "off", "onto", "unto", "onto", "itself", "himself", "herself",
    "proposal", "design", "answer", "value", "values", "level",
    "levels", "rate", "rates", "test", "tests", "tested", "testing",
    "measure", "measured", "measurement", "measurements", "monitor",
    "monitored", "monitoring", "record", "recorded", "recording",
    "sample", "samples", "sampled", "sampling", "data", "period",
    "periods", "window", "windows", "condition", "conditions",
    "system", "systems", "device", "devices", "unit", "units",
    "equipment", "operation", "operating", "operational", "normal",
    "nominal", "baseline", "reference", "threshold", "thresholds",
    "protocol", "protocols", "criterion", "criteria", "pass", "fails",
    "failure", "failures", "fault", "faults", "faulty", "defect",
    "defects", "degradation", "degradation", "detection", "detect",
    "detected", "detects", "indicator", "indicators", "signal",
    "signals", "alert", "alerts", "alarm", "alarms", "sensor",
    "sensors", "sensing", "instrument", "instrumentation",
    "parameter", "parameters", "intervention", "interventions",
    "mechanism", "mechanisms", "effect", "effects", "expected",
    "predicted", "performance", "improve", "improved", "improves",
    "improvement", "enhance", "enhanced", "enhances", "increase",
    "increased", "increases", "reduce", "reduced", "reduces",
    "reduction", "change", "changes", "changed", "state", "states",
    "early", "late", "before", "after", "during", "within", "above",
    "below", "exceed", "exceeds", "exceeding", "least", "days",
    "hours", "weeks", "months", "years", "cycle", "cycles", "life",
    "service", "cost", "costs", "effective", "efficiency",
    "reliability", "safety", "risk", "load", "loads", "current",
    "voltage", "temperature", "temperatures", "pressure", "pressures",
    "water", "time", "high", "low", "higher", "lower", "size", "size",
    "large", "small", "typical", "specific", "concrete", "existing",
    "new", "added", "additional", "required", "requires", "respect",
    "respects", "user", "stated", "constraints", "constraint",
    "respecting", "ensure", "ensures", "ensuring", "allow", "allows",
    " capability", "capabilities", "provide", "provides", "providing",
    "normalized", "normalize", "normalizes",
    "remain", "remains", "maintain", "maintains", "maintained",
    "support", "supported", "supports", "evidence", "records",
    "assumption", "assumptions", "unverified", "hypothesis",
})

_NUM_RE = re.compile(r"^\d")


def _content_tokens(text: str) -> set:
    """Lowercase content words (len>=3, non-numeric, minus the generic
    scaffolding set). Deterministic, documented, no threshold."""
    toks = set()
    for w in re.findall(r"[a-z][a-z\-]{2,}", str(text or "").lower()):
        w = w.strip("-")
        if len(w) >= 3 and w not in _GENERIC_TOKENS \
                and not _NUM_RE.match(w):
            toks.add(w)
    return toks


def _candidate_design_tokens(cand: Dict[str, Any]) -> set:
    """The design vocabulary of ONE candidate record: its mechanism,
    intervention and predicted/expected effect (the fields the
    composer prompt renders)."""
    parts = []
    for k in ("mechanism", "intervention", "expected_effect",
              "predicted_effect", "falsification_test"):
        v = cand.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return _content_tokens(" ".join(parts))


def _problem_tokens(problem: Optional[Dict[str, Any]]) -> set:
    """The problem statement's own vocabulary — a shared token with the
    problem text is never evidence of cross-design mixing (both designs
    inevitably name the device and failure)."""
    if not problem:
        return set()
    parts = [str(problem.get(k) or "") for k in
             ("device", "failure", "failure_mode", "constraint",
              "question")]
    for v in problem.get("user_variables") or []:
        parts.append(str(v))
    ca = problem.get("clarification_answer")
    if isinstance(ca, str):
        parts.append(ca)
    elif isinstance(ca, dict):
        parts.extend(str(x) for x in ca.values())
    return _content_tokens(" ".join(parts))


def _lead_segment(text: str) -> str:
    """The answer's lead design segment: from the FIRST design marker
    to the next contract thing-marker (or 400 chars — the contract's
    own segment cap). Empty when no design marker exists."""
    m = _LEAD_SEGMENT_RE.search(text)
    if not m:
        return ""
    tail = text[m.end():]
    nxt = _THING_MARKERS_RE.search(tail)
    seg = tail[:nxt.start()] if nxt else tail[:400]
    return (m.group(0) + seg).strip()


def _split_test(answer: str) -> Tuple[str, str]:
    """(proposal_section, test_section) split at the falsification-test
    marker; when no COLON marker exists, the sentence that ANNOUNCES
    the falsification test ("The falsification test involves ...") is
    the boundary (the measured live shape — the contract requires the
    test, its wording varies); the whole answer is the proposal when
    neither exists (CHECK_ABSENT carries the typed note, never read
    as a pass — Art. XXV)."""
    m = _TEST_MARKER_RE.search(answer)
    if m:
        return answer[:m.start()], answer[m.start():]
    m2 = re.search(r"(?:^|[.!?]\s+)(The\s+falsification\s+test|"
                   r"A\s+falsification\s+test|To\s+falsify\b)",
                   answer, re.IGNORECASE)
    if m2:
        return answer[:m2.start()], answer[m2.start():]
    return answer, ""


def consistency_check(answer: str,
                      candidates: Optional[List[Dict[str, Any]]],
                      problem: Optional[Dict[str, Any]] = None,
                      ) -> Dict[str, Any]:
    """The deterministic design-consistency check (see module doc).

    Returns {state: CONSISTENCY_PASS | CONSISTENCY_VIOLATIONS |
             CHECK_ABSENT, violations: [...], n_violations}.
    NEVER raises; a missing section is CHECK_ABSENT (never read as a
    pass — Art. XXV)."""
    text = str(answer or "")
    violations: List[Dict[str, Any]] = []
    proposal, test = _split_test(text)
    if not test.strip():
        return {"consistency_version": ANSWER_CONSISTENCY_VERSION,
                "state": "CHECK_ABSENT",
                "why": ("no falsification-test marker found — the "
                        "one-design check cannot run (never read as "
                        "a pass)"),
                "violations": [], "n_violations": 0}
    cands = [c for c in (candidates or []) if isinstance(c, dict)]
    prob_toks = _problem_tokens(problem)
    ans_toks = _content_tokens(text)
    prop_toks = _content_tokens(proposal)
    test_toks = _content_tokens(test)

    if cands:
        primary = cands[0]
        p_toks = _candidate_design_tokens(primary) - prob_toks
        alt_toks = set()
        for c in cands[1:]:
            alt_toks |= _candidate_design_tokens(c)
        alt_toks = (alt_toks - p_toks) - prob_toks

        # 1. a named alternative's design vocabulary leaks into the
        #    answer (the alternatives are named for context ONLY)
        leak = sorted(alt_toks & ans_toks)
        if leak:
            violations.append({
                "type": "ALTERNATIVE_DESIGN_IN_ANSWER",
                "detail": ("the answer carries design vocabulary of a "
                           "NAMED ALTERNATIVE, not the primary "
                           f"proposal: {', '.join(leak[:6])} — "
                           "mechanism, indicator/intervention and "
                           "falsification test must all describe ONE "
                           "(the primary) design"),
                "tokens": leak[:6]})
        # 2. the falsification test describes a DIFFERENT design than
        #    the proposal: the primary candidate's distinctive design
        #    vocabulary appears in the test but nowhere in the
        #    proposal (the test tests the candidate; the proposal
        #    describes something else)
        p_in_test, p_in_prop = p_toks & test_toks, p_toks & prop_toks
        if p_in_test and not p_in_prop:
            violations.append({
                "type": "TEST_VS_PROPOSAL_DESIGN_MISMATCH",
                "detail": ("the falsification test's design "
                           f"vocabulary ({', '.join(sorted(p_in_test)[:6])}) "
                           "belongs to the primary proposal, but the "
                           "proposal section never uses it — the test "
                           "does not test the described design"),
                "tokens": sorted(p_in_test)[:6]})
        # 3. the proposal mixes TWO designs: a lead DESIGN segment
        #    that shares NO design token with the primary candidate
        #    (RAW comparison — the lead segment legitimately reuses
        #    problem-stated quantities, so the problem-vocabulary
        #    exclusion does NOT apply here), while the proposal
        #    elsewhere carries the primary's design vocabulary (the
        #    measured new07 shape: indicator lead + nanofluid body).
        #    PARAMETER lines are deliberately NOT lead segments: a
        #    quantity line is the design's own spec, never a second
        #    design (the measured live p02 shape).
        lead = _lead_segment(proposal)
        if lead:
            lead_toks = _content_tokens(lead)
            if lead_toks and not (lead_toks & p_toks) \
                    and (p_toks & prop_toks):
                violations.append({
                    "type": "TWO_DESIGNS_IN_PROPOSAL",
                    "detail": ("the lead design segment describes a "
                               "different design than the primary "
                               "proposal vocabulary carried later in "
                               "the same proposal — one answer, ONE "
                               "design"),
                    "lead_tokens": sorted(lead_toks)[:6],
                    "primary_tokens_in_proposal":
                        sorted(p_toks & prop_toks)[:6]})
    state = ("CONSISTENCY_VIOLATIONS" if violations
             else "CONSISTENCY_PASS")
    return {"consistency_version": ANSWER_CONSISTENCY_VERSION,
            "state": state,
            "violations": violations,
            "n_violations": len(violations)}


#: the ONE plain-language caveat a mixed-design delivery may carry
CONSISTENCY_CAVEAT_LINE = (
    "Note: this answer may mix design elements that belong to "
    "different proposals; verify that the mechanism, the measured "
    "quantity and the falsification test all describe one and the "
    "same design.")

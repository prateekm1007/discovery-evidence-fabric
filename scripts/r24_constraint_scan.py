#!/usr/bin/env python3
"""r24_constraint_scan.py — typed constraint-fit scan for the V6.1
battery (deterministic, no LLM; part of the machine-internal repair
loop, findings disclosed).

SEGMENT-BASED parsing of the problem's `constraint` string (split on
';' and '.'):
  EXCLUSION segment: contains "without ", starts with "no ", "must
    not ", "no change to ", "no adding ", or is "retrofit only";
  ALLOWED-LIST segment: contains "only" or starts with "allowed
    measures"/"permitted measures";
  everything else is a performance BOUND (ignored for terms).

Stems are whole-word (len>=4, numeric/unit words dropped,
singular/plural tolerant). Findings:
  CONSTRAINT_EXCLUSION  — an excluded stem appears in a mechanism/bill
                          context line of the draft;
  ALLOWED_LIST_OUTSIDE  — an allowed list exists and the draft mentions
                          NONE of its stems (conservative).

Residual findings are disclosed in the record, never silently dropped.
"""
import re

UNIT_WORDS = {
    "percent", "ppm", "mm", "cm", "km", "deg", "hours", "days", "weeks",
    "months", "years", "more", "less", "than", "above", "over", "below",
    "under", "within", "least", "most", "exceed", "exceeding", "per",
    "each", "every", "total", "maximum", "minimum", "max", "min", "life",
    "rated", "ambient", "temperature", "pressure", "load", "case",
}
STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "at",
    "on", "by", "from", "that", "this", "any", "all", "into", "onto",
    "when", "while", "during", "must", "shall", "will", "should", "can",
    "may", "it", "its", "their", "them", "these", "those", "there",
    "then", "than", "such", "same", "also", "only", "even", "ever",
} | UNIT_WORDS

EXCL_START = re.compile(
    r"^(?:without\b|no\b(?!t)|must not\b|no change to\b|no adding\b)")
ALLOWED_START = re.compile(
    r"^(?:allowed measures?\b|permitted measures?\b)")


def _stems(text):
    out = set()
    for w in re.split(r"[^a-z0-9]+", text.lower()):
        if len(w) >= 4 and w not in STOP:
            out.add(w)
            out.add(w + "s") if not w.endswith("s") else out.add(w[:-1])
    return out


CUE_RE = re.compile(
    r"\b(?:without\s+|must not\s+|no change to\s+|no adding\s+)"
    r"([a-z][a-z0-9 \-/]{3,80})")


def extract_constraint_terms(constraint):
    """Return (exclusion_stems, allowed_stems) from the constraint."""
    c = str(constraint or "").lower()
    exclusions, allowed = set(), set()
    for seg in re.split(r"[;.]", c):
        seg = re.sub(r"^retrofit only\s*[:\-]?\s*", "", seg.strip())
        if not seg:
            continue
        cue_terms = {m.group(1) for m in CUE_RE.finditer(seg)}
        if cue_terms:
            for t in cue_terms:
                exclusions |= _stems(t)
        elif "only" in seg and not re.search(r"\d", seg):
            body = re.sub(
                r"^(?:allowed measures?|permitted measures?)\s*[:\-]?\s*",
                "", seg)
            body = re.sub(r"\bonly\b\s*$", "", body).strip()
            allowed |= _stems(body)
    exclusions -= allowed
    return exclusions, allowed


def scan_constraint_fit(problem, answer):
    """Typed constraint-fit findings for one draft."""
    c = str(problem.get("constraint") or "")
    if not c.strip():
        return {}
    excl, allowed = extract_constraint_terms(c)
    text = str(answer or "").lower()
    findings = {}
    if allowed and not any(s in text for s in allowed):
        findings["ALLOWED_LIST_OUTSIDE"] = [
            f"constraint enumerates allowed measures ({c[:90]}...) but "
            "the answer mentions none of their terms"]
    hits = []
    for s in sorted(excl):
        for line in text.split(". "):
            if s in line and re.search(
                r"\b(bill|add|install|use|increas|propos|mechanism|"
                r"retrofit|row|inject|coat|anode|system)\w*", line) \
                    and len(hits) < 4:
                hits.append(f"excluded stem '{s}' in: {line.strip()[:110]}")
    if hits:
        findings["CONSTRAINT_EXCLUSION"] = hits
    return findings

#!/usr/bin/env python3
"""tool_grounded_critic/1.0.0 — the CRITIC tool-grounding corrector
(claim c-0109; AM80 direction 1; the c-0106 root cause's named fix).

The R93 matched-budget ablation typed the residual defect class as
PROMPT-REFRACTORY: BILL_UNTAGGED persisted in 27/30 challenger rows
through every reflection-augmented repair, and the ablation's named next
leverage is CRITIC tool-grounding — the critic CALLS the tools to CORRECT
the defect mechanically instead of flagging it for another prompt round.

This module is the deterministic correction surface. It does NOT replace
the critic and does NOT touch the frozen machine: adoption is gated (the
c-0106 lane pattern — fixture mechanics -> CI-gated adoption). The
detection is byte-parity with the frozen machine's own base_scan
(scripts/r22_a1w_v5_repair.py, called at r40_machine_v77.py:484 on every
attempt) — the parity is asserted in CI against the real scan module on
real committed corpus bytes.

Typed classification rules (VERIFIED on the committed corpus,
scripts/r95_probe_bill_rows.py + the refined probes: 424 flagged rows in
the v11 last attempts (102 a + 79 c + 5 b single-class, 238
none/ambiguous); sealed v9+v10 corpus 901 flagged -> 515 after the
tagger, 42.8% mechanically corrected, 48/60 rows improved): a row is
tagged ONLY when the class is unambiguous. The no-match population is
dominated by protocol/header rows (Pass/Fail criteria, Standard-Practice
comparisons, bare headers) — a procurement tag on those would be INVENTED
semantics; they stay flagged (typed residual, disclosed in the record).
Never a guessed tag.

Attribution (NOTICE.md): CRITIC tool-grounding pattern (microsoft,
ICLR23) + CriticEval (MIT) per AM82 worldwide update 3; the computed
chemistry leg composes scripts/r80_chemistry_equilibrium.py (Cantera
BSD-3, c-0107). Zero LLM, zero network.
"""
from __future__ import annotations

import re

RECORD = "TOOL_GROUNDED_CRITIC/1.0.0"

# --- detection: byte-parity with the frozen machine's base_scan ---------
BILL_SECTION = re.compile(
    r"IMPLEMENTATION BILL(.*?)(?=\n[A-Z][A-Z ]{4,}\n|\Z)", re.S | re.I)
ROW_START = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.M)
NONSCANNABLE_TAG = re.compile(r"\(Tag: ?([abc])\)", re.I)
HEADER_ROW = re.compile(r"\*{0,2}[^*\n]{1,60}:\s*\*{0,2}\s*$")

# --- typed procurement-class markers (probe-verified, see module doc) ---
# The (c) class is split into ACTION markers (procedure/duty verbs and
# parameters — the r22 directive's own "(c) parameter/duty/procedure/
# configuration change" semantics) and bare CONSEQUENCE nouns (dosing/
# dip/pulse/... — the corpus's cost-row convention). A bare noun does NOT
# make a row (c): "existing dosing pumps" is (a) infrastructure, not a
# schedule change. (a) takes precedence over bare nouns; a real action
# verb colliding with an explicit (a) marker is TRUE ambiguity (None).
A_CLASS_RE = re.compile(
    r"\b(existing|already (present|installed|in place)|no new|"
    r"rides (entirely )?on|reuses?|uses? the existing|zero|"
    r"no (new|physical|additional|modifications|hardware|sensors|"
    r"coatings|installation))\b", re.I)
B_CLASS_RE = re.compile(
    r"\b(commercial[- ]grade|commercial|catalog|off-the-shelf|"
    r"stock|standard (catalog|grade|part)|commodity|"
    r"procurable|supplier|purchased|procured)\b", re.I)
C_ACTION_RE = re.compile(
    r"\b(reconfigure|retune|reprogram|schedule|setpoint|set \w+ to|"
    r"switch(ing)?|threshold|interval|duty|procedure|mode|adjust|"
    r"retiming|intermittent|increase|decrease|reduce|raise|lower)\b", re.I)
C_NOUN_RE = re.compile(
    r"\b(pulse|dosing|per (event|cycle|batch)|downtime|dip)\b", re.I)


def classify_bill_row(row: str) -> str | None:
    """The typed procurement class of ONE bill row: 'a'|'b'|'c'|None.
    None = ambiguous or no typed marker — never a guess; the caller
    leaves those rows flagged."""
    if HEADER_ROW.search(row):
        return None  # bare headers have no procurement class
    a = bool(A_CLASS_RE.search(row))
    b = bool(B_CLASS_RE.search(row))
    c = bool(C_ACTION_RE.search(row))
    classes = [x for x, hit in (("a", a), ("b", b), ("c", c)) if hit]
    if len(classes) == 1:
        return classes[0]
    if not classes:
        return "c" if C_NOUN_RE.search(row) else None
    return None  # 2+ explicit classes: true ambiguity, never a guess


def _untagged_rows(section: str) -> list[int]:
    """Line indexes (inside the section) the base_scan would flag."""
    out = []
    for i, ln in enumerate(section.splitlines()):
        if ROW_START.match(ln) and not ("(a)" in ln or "(b)" in ln
                                        or "(c)" in ln):
            out.append(i)
    return out


def tag_bill(answer: str) -> tuple[str, dict]:
    """Mechanically tag the implementation-bill rows whose procurement
    class is unambiguous. Returns (corrected_answer, record). A row
    already carrying the non-scannable '(Tag: x)' format is normalized
    to the scannable format the base_scan requires (no content change).
    Ambiguous/no-match rows are left UNTOUCHED and reported."""
    if not answer:
        return answer, {"record": RECORD, "corrected": 0,
                        "normalized": 0, "left_flagged": 0,
                        "left_flagged_rows": [], "note": "empty answer"}
    m = BILL_SECTION.search(answer)
    if not m:
        return answer, {"record": RECORD, "corrected": 0,
                        "normalized": 0, "left_flagged": 0,
                        "left_flagged_rows": [],
                        "note": "no IMPLEMENTATION BILL section"}
    section = m.group(1)
    lines = section.splitlines()
    corrected = normalized = left = 0
    left_rows = []
    for i in _untagged_rows(section):
        ln = lines[i]
        nm = NONSCANNABLE_TAG.search(ln)
        if nm:
            # normalize '(Tag: x)' -> '(x)' so the scannable contract holds
            lines[i] = NONSCANNABLE_TAG.sub(
                lambda g: f"({g.group(1).lower()})", ln)
            normalized += 1
            continue
        cls = classify_bill_row(ln)
        if cls is None:
            left += 1
            left_rows.append(ln.strip()[:90])
            continue
        lines[i] = ln.rstrip() + f" ({cls})"
        corrected += 1
    new_section = "\n".join(lines)
    start, end = m.span(1)
    corrected_answer = answer[:start] + new_section + answer[end:]
    return corrected_answer, {
        "record": RECORD, "corrected": corrected,
        "normalized": normalized, "left_flagged": left,
        "left_flagged_rows": left_rows[:10],
    }


# ------------------------------------------- computed-chemistry corrector
_CHEM_INVERT = {
    "reduces": "increases", "reduce": "increase", "lowers": "raises",
    "lower": "raise", "decreases": "increases", "decrease": "increase",
    "suppresses": "promotes", "suppress": "promote", "less": "more",
}
_CHEM_INVERT_INV = {v: k for k, v in _CHEM_INVERT.items()}


def correct_inverted_chemistry(answer: str, verdict: dict) -> tuple[str, dict]:
    """On a COMPUTED INVERTED verdict from the c-0107 engine
    (scripts/r80_chemistry_equilibrium.py) for a typed-pair claim,
    rewrite the claimed direction word mechanically on the matched span.
    Conservative: only the typed pair the extractor matched; any other
    verdict (CONSISTENT/UNVERIFIABLE) is a no-op."""
    if not answer or verdict.get("computed_verdict") != "INVERTED":
        return answer, {"record": RECORD, "chemistry_rewrites": 0}
    claimed = verdict.get("claimed_direction")
    table = _CHEM_INVERT if claimed == "decrease" else _CHEM_INVERT_INV
    rewrites = 0
    for wrong, right in table.items():
        pat = re.compile(r"\b" + wrong + r"\b", re.I)
        answer, n = pat.subn(right, answer)
        rewrites += n
        if rewrites:
            break  # one mechanical rewrite per verdict, conservative
    return answer, {"record": RECORD, "chemistry_rewrites": rewrites}


# ------------------------------------------------------- composed surface
def grounded_critique(answer: str, chem_verdict: dict | None = None,
                      scan_parity: object = None) -> dict:
    """The deterministic pre-critic pass: correct what the tools can
    correct, then re-scan with the frozen machine's own base_scan (pass
    it as scan_parity=scan — the CI parity test pins this; here it is a
    required argument so the engine never guesses the oracle)."""
    if scan_parity is None:
        raise TypeError("grounded_critique requires the frozen machine's "
                        "own scan as scan_parity (the oracle is never "
                        "guessed)")
    corrected, rec = tag_bill(answer)
    if chem_verdict:
        corrected, crec = correct_inverted_chemistry(corrected, chem_verdict)
        rec.update(crec)
    residual = scan_parity(corrected)
    rec["residual_findings"] = residual
    rec["residual_bill_untagged"] = len(residual.get("BILL_UNTAGGED", []))
    rec["corrected_answer"] = corrected
    return rec

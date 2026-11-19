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
NONSCANNABLE_TAG = re.compile(
    r"\(\s*(?:Tag: ?)?([abc])\s*(?:[-–—][^)\n]{0,40})?\)", re.I)
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
    r"\b(reconfigure|retune|reprogram|schedul\w*|setpoint|set \w+ to|"
    r"switch(ing)?|threshold|interval|duty|procedure|mode|adjust|"
    r"retiming|intermittent|increase|decrease|reduce|raise|lower)\b", re.I)
C_NOUN_RE = re.compile(
    r"\b(pulse|dosing|per (event|cycle|batch)|downtime|dip)\b", re.I)

# --- v13 convergence extension (c-0113; mined from the sealed v12
# residual BILL_UNTAGGED population, scripts/r98_probe_residuals.py):
# the 24 BUDGET_EXHAUSTED v12 rows died on annotation/predictor rows the
# 1.0.0 vocabulary could not classify. Three typed additions, each a
# procurement-semantics rule (never a guess), all zero-LLM:
#   (1) A-CLASS: rides-on-existing-DATA markers ("ALREADY-RECORDED",
#       "AS-IS device") and label-scoped bare "none" burden lines —
#       existing infrastructure/data, no procurement.
#   (2) C-CLASS: procedure/software verbs the corpus actually uses
#       (change/modify/implement/limit/deploy/derive/calculate/...).
#   (3) LABEL dispatch: burden-annotation and predictor-logic labels
#       (Parameter/Action/Logic/Rule/Threshold/Protocol/...) carry the
#       (c) configuration class UNLESS an explicit (a)/(b) marker also
#       fires (then the 1.0.0 ambiguity rule holds). Hardware-noun
#       "Component:" rows are only (c) with a control-noun gate.
#   (4) NARRATIVE guard: first-person deliberation and reasoning-leakage
#       labels (Why/Note/Physics/Re-reading/"I ...") are NOT procurement
#       rows — tagging them would be invented semantics; they stay
#       flagged as the typed residual (1.0.0 rule preserved, now typed).
A_CLASS_V13 = re.compile(
    r"\b(already[- ]recorded|as[- ]is device|no modification\b|"
    r"(instruments?|hardware|installation|commissioning|maintenance)"
    r"\s*:\s*(?:\*\*)?\s*(?:none|zero|0 hours)\b)", re.I)
C_ACTION_V13 = re.compile(
    r"\b(change[sd]?|modif(y|ies|ied)|implement(s|ed|ing)?|"
    r"limit(s|ed|ing)?|capped?|deploy(s|ed)?|populate[sd]?|"
    r"retriev(e|es|ed)|identif(y|ies|ied)|track(s|ed|ing)?|"
    r"appl(y|ies|ied)|replay(s|ed)?|back[- ]test(s|ed)?|"
    r"deriv(e|es|ed|ation)|calculat(e|es|ed|ion)|"
    r"comput(e|es|ed|ation)|set such that|warn(s|ing)?|alarm|"
    r"flag(s|ged)?)\b", re.I)
LABEL_C_V13 = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])?\s*\**\s*("
    r"logic|rule|warning(?: logic| threshold(?:s)?)?|threshold(?: logic)?|"
    r"protocol|description|derivation|baseline derivation|algorithm|"
    r"predictor|parameter(?: change)?|action|operation|duration|"
    r"firmware|software module|data acquisition|"
    r"steam duty cycle|duty cycle|setpoint|temperature setpoint"
    r")\b[^:\n]{0,40}:\s*", re.I)
_COMPONENT_CONTROL_NOUN = re.compile(
    r"\b(setpoint|loop|ratio|rate|logic|ramp|recipe|threshold|schedule|"
    r"interlock|mode|adjustment|restriction|hold|control)\b", re.I)
COMPONENT_C_V13 = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])?\s*\**\s*component\b[^:\n]{0,40}:\s*", re.I)
NARRATIVE_V13 = re.compile(
    r"(^\s*(?:[-*•]|\d+[.)])?\s*\**\s*"
    r"(why\b|note\b|problem\b|exception\b|hard stop\b|correction\b|"
    r"re-?evaluat\w+|re-?read\w+|alternative\b|implication\b|"
    r"rationale\b|direction-of-effect|premise-validity|"
    r"deployed[- ]part|new mechanism\b|physics\b|transient\b|"
    r"leak effect\b|is this better|actually\b)"
    r"|\b(perhaps|maybe|what if|this is a trap|but the question|"
    r"we don't know|\bI\b|my (?:primary|measure|indicator|proposal)))",
    re.I)

# --- v14 water/wastewater convergence extension (c-0116; mined from
# the BURNED v14 residual BILL_UNTAGGED population — 127 flagged rows
# across the 21 non-converged water rows, scripts/
# r101_water_domain_mining.py; every rule is a procurement-semantics
# rule verified on those bytes, never a guess, zero LLM). Clusters:
#   (1) BURDEN-LEDGER LABELS: the answer format's own burden-ledger
#       keys (Operational Loss (Pricing), Installation/Procurement/
#       Hardware Burden, Commissioning, Cost Impact, Energy,
#       Throughput, Mitigation, Conclusion, Basis, Standard Practice
#       Comparison) — the row's class is its ASSERTION: a
#       zero/no-new/no-added-burden assertion is (a); a priced
#       time/energy/throughput consequence is (c); a positive
#       purchase of parts is (b); anything else stays flagged. The
#       v13 ambiguity killer ate these rows (a zero marker + an
#       echoed purchase word = 2 classes); the label scopes the
#       reading.
#   (2) TEST/VERIFICATION LABELS: Pass/Fail, Kill Criterion,
#       Falsification, Protocol, Duration, Baseline, Acceptance —
#       verification bookkeeping the machine's own contract tags (c)
#       (procedure/configuration class) unless an explicit (a)/(b)
#       fires.
#   (3) CONFIGURATION-ON-EXISTING: the water corpus's dominant
#       measure shape is "setpoint/parameter change on the existing
#       <equipment>" — an existing-equipment mention + a
#       configuration verb is (c) (the a-marker describes the
#       OBJECT's provenance, not a no-procurement assertion); the
#       strict a+c ambiguity rule stays for no-procurement
#       assertions (no new/zero/none).
#   (4) "update|reconfigure" join the c-class configuration verbs.
BURDEN_LEDGER_LABEL_V14 = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])?\s*\**\s*("
    r"operational loss(?: pricing)?|installation[/ \-]burden|"
    r"procurement(?: burden)?|hardware(?: burden)?|installation[/ \-]"
    r"commissioning|commissioning|cost(?: impact)?|"
    r"standard practice comparison|throughput|mitigation|"
    r"conclusion|basis|energy|parity|operability|operational cost|"
    r"installability|maintainability|maintenance|cost class|"
    r"installation\b|procurement\b|hardware\b"
    r")\b[^:\n]{0,40}:\s*", re.I)
TEST_PROTOCOL_LABEL_V14 = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])?\s*\**\s*("
    r"pass/fail|kill criterion|falsification(?: test| criterion)?|"
    r"test protocol|protocol|duration|acceptance test|baseline\b"
    r")\b[^:\n]{0,40}:\s*", re.I)
INPUT_LABEL_V14 = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])?\s*\**\s*inputs?\b[^:\n]{0,40}:\s*",
    re.I)
A_ZERO_V14 = re.compile(
    r"(\$0\b|\b(?:zero|none|no new|no hardware|no parts|"
    r"no additional|negligible|already (in place|installed|existing)|"
    r"remains? (the same|unchanged|within|constant)|same.or.lower|"
    r"no added|within the existing|0 new|no modification|not modify|"
    r"does not modify|does not change|no change|no loss|zero loss|"
    r"same as standard|0 hours)\b)", re.I)
C_CONSEQUENCE_V14 = re.compile(
    r"\b(\d+(?:\s*[-\u2013\u2014]\s*\d+)?\s*"
    r"(?:hours?|hr|minutes?|min|seconds?)\b|\d+\s*%(?!\w)|energy\b|"
    r"pumping\b|throughput (?:loss|reduction|remains)\b|"
    r"temporary\b|seasonal\b|downtime\b|engineering time\b|"
    r"software\b|monitor\w*|operator\b)", re.I)
B_PURCHASE_POSITIVE_V14 = re.compile(
    r"\b(purchase[sd]?|procure[sd]?|order(ed)?)\b(?![^.]{0,30}\b"
    r"(no|zero|none)\b)", re.I)
EXISTING_EQUIPMENT_V14 = re.compile(
    r"\bexisting\b.{0,90}\b(equipment|system|pump\w*|blower|PLC|setpoint|"
    r"controller|loop|infrastructure|dosing|drive\w*|VFD|analyzer|ratio|"
    r"signal|flow|valve|sensor|probe|meter|DCS|HMI|panel|alarm|"
    r"membrane|vessel)\b", re.I)
C_ACTION_V14 = re.compile(
    r"\b(update[sd]?|reconfigur\w+|record\b|recording\b)\b", re.I)


# the machine's own answer-format CLAUSE keys (v14): answer
# bookkeeping, not reasoning leakage — they bypass the narrative
# early-return and classify by their assertion (zero/no-modification
# -> (a); anything else -> (c), never (b): bookkeeping proposes
# nothing)
CLAUSE_LABEL_V14 = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])?\s*\**\s*("
    r"deployed.part clause|permitted.set clause|"
    r"direction.of.effect|exemplar.reality|certified.system|"
    r"input.availability|cost.pricing|mechanism class|"
    r"unpriced.duty.cycle|mechanism.class.unstated"
    r")\b[^:\n]{0,40}:\s*", re.I)


def _classify_v14(row: str, a: bool, b: bool, c: bool, clause: bool = False) -> str | None:
    """The v14 water-domain dispatch (typed, never a guess)."""
    burden = bool(BURDEN_LEDGER_LABEL_V14.search(row))
    test_lbl = bool(TEST_PROTOCOL_LABEL_V14.search(row))
    if INPUT_LABEL_V14.search(row) and not b:
        return "a"  # data-source semantics (the predictor's own (a))
    # a bare known-ledger header (label + colon + no content) is the
    # ledger's own structure — the pricing/duty family is (c)
    if (burden or test_lbl) and not re.search(
            r":\s*\**\s*\S", row):
        return "c"
    if burden or test_lbl:
        if A_ZERO_V14.search(row):
            return "a"
        if test_lbl:
            # verification bookkeeping: the (c) procedure class unless
            # an explicit (a) no-procurement assertion or a real
            # purchase fires
            if B_PURCHASE_POSITIVE_V14.search(row):
                return "b"
            return "c"
        if burden and C_CONSEQUENCE_V14.search(row):
            return "c"
        if B_PURCHASE_POSITIVE_V14.search(row):
            return "b"
        # fall through: a burden-labelled row may still be the
        # configuration-on-existing shape ("Basis: Change ... on
        # existing equipment")
    # configuration-on-existing: existing-equipment mention + a
    # configuration verb = the (c) parameter-change class (the
    # auditor-read convention; the no-procurement assertions keep
    # the strict 1.0.0/v13 ambiguity rule)
    if a and c and EXISTING_EQUIPMENT_V14.search(row):
        return "c"
    if burden or test_lbl:
        return None  # unresolvable burden wording stays flagged
    # the 1.0.0 bare-noun convention (pulse/dosing/downtime/dip rows)
    if not a and not b and not c:
        return "c" if C_NOUN_RE.search(row) else None
    return None  # 2+ explicit classes: true ambiguity, never a guess


def classify_bill_row(row: str) -> str | None:
    """The typed procurement class of ONE bill row: 'a'|'b'|'c'|None.
    None = ambiguous, narrative, or no typed marker — never a guess; the
    caller leaves those rows flagged."""
    clause = bool(CLAUSE_LABEL_V14.search(row))
    if NARRATIVE_V13.search(row) and not clause:
        return None  # reasoning leakage / first-person deliberation
    if HEADER_ROW.search(row):
        # a bare header of a KNOWN burden-ledger / test-protocol key
        # is the machine's own ledger structure (the content sits on
        # the following lines) — the pricing/duty family is (c); any
        # other bare header has no procurement class
        if BURDEN_LEDGER_LABEL_V14.search(row) or \
                TEST_PROTOCOL_LABEL_V14.search(row):
            return "c"
        return None  # bare headers have no procurement class
    a = bool(A_CLASS_RE.search(row) or A_CLASS_V13.search(row))
    b = bool(B_CLASS_RE.search(row))
    c = bool(C_ACTION_RE.search(row) or C_ACTION_V13.search(row)
             or C_ACTION_V14.search(row))
    # LABEL dispatch: a typed c-label makes (c) explicit unless an
    # explicit (a)/(b) marker also fired. "Component:" is c only with a
    # control-noun gate (a bare hardware component is procurement (b)
    # or ambiguous — never guessed).
    if not a and not b:
        if LABEL_C_V13.search(row):
            c = True
        elif COMPONENT_C_V13.search(row) and _COMPONENT_CONTROL_NOUN.search(row):
            c = True
    if clause:
        # the machine's own answer-format clauses: a zero/no-change
        # assertion is (a); other bookkeeping is (c); never (b)
        return "a" if A_ZERO_V14.search(row) else "c"
    declared = NONSCANNABLE_TAG.search(row)
    if declared:
        # a self-declared class in any format is authoritative — the
        # v14 refinement never overrides an explicit tag
        return declared.group(1).lower()
    classes = [x for x, hit in (("a", a), ("b", b), ("c", c)) if hit]
    if len(classes) == 1:
        return classes[0]
    # the v14 water-domain dispatch (burden-ledger scoping + the
    # configuration-on-existing refinement) runs on the ambiguous and
    # empty populations the 1.0.0/v13 rules leave flagged
    return _classify_v14(row, a, b, c, clause)


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

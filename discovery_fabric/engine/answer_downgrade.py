"""discovery_fabric/engine/answer_downgrade.py — DOWNGRADE, DON'T
DISCARD (owner audit round 2026-11-12, directive 2).

The R6 auditor measured the delivery cost of the strict ship/no-ship
split: contract-invalid final answers ship NOTHING, which raises the
no-answer rate for the user. The owner's directive: "when provenance
or contract checks fail, deterministically relabel failing
EVIDENCE-BACKED claims as ASSUMPTION, drop invalid citations and ship
the repaired answer with one plain-language caveat. Typed no-answer
only for scientific (contradicted/infeasible) kills." And: "A
truncated or partly invalid answer with a plain caveat beats a blank."

What this module does (deterministic, zero-LLM, Art. IV — it never
manufactures support, it only REMOVES unsupported certainty):
  1. An EVIDENCE-BACKED label whose bracketed citation fails the
     contract (no id, or an id that is not in the frozen packet) is
     relabeled ASSUMPTION and the invalid citation is dropped.
  2. Internal candidate ids ("[cand:...]") — pipeline jargon — are
     stripped from the delivered text (directive 1: clean output).
  3. The result re-runs the deterministic contract. Fully valid after
     the downgrade -> typed COMPOSED_CONTRACT_DOWNGRADED (delivered
     with ONE plain caveat). Still partly invalid -> delivered anyway
     with the same caveat, typed COMPOSED_CONTRACT_INVALID_DELIVERED;
     the open violations ride the record metadata (Art. XXV), never a
     banner, never a blank.

Typed no-answer stays ONLY for: transport failure, and the composer's
typed scientific refusals (NO_ADMISSIBLE_CANDIDATES on scientific /
contradicted / infeasible kills — the hypothesis-class kills are
delivered upstream per the approved attack semantics).

STRICT PROVENANCE (owner audit round 2026-11-13, directive 2) — the
value-level pass, `strict_provenance_downgrade`: an EVIDENCE-BACKED
PARAMETER whose VALUE is not in the CITED record is relabeled, even
when the citation id itself is valid. Measured defect (the committed
fu-005 pair, answer sha d418ea93): "expected_reduction_in_creep_set —
60% — EVIDENCE-BACKED [doi:10.3390/polym16030440]" and friends against
a polyurea-microstructure review whose text gives none of those
numbers — the existing downgrade only checked citation VALIDITY (id
in packet), not value membership. Rules (binary membership, no
invented threshold — Art. XXVII):
  - NUMERIC values: EVERY number+unit pair in the value must be found
    in the cited record's text (a number is identity-establishing for
    a parameter value);
  - WORD-ONLY values: relabeled when NO content word of the value
    appears in the record (zero vocabulary overlap = the record does
    not speak to the value); partial overlap keeps the label (the
    relabel direction only ever REMOVES certainty, never adds);
  - a relabeled value that IS the user's own stated constraint /
    device description (present in the problem text, absent from the
    record) becomes ASSUMPTION (User Constraint) — a user constraint
    or a restated device is never labeled as evidence (the measured
    fu-005 case: "service_life_extension — 75 years" is the user's
    own design life, not the paper's claim);
  - the citation rides the relabel DOWN (dropped): an ASSUMPTION with
    a citation misleads.

Serves: Art. LXIII (the buyer-facing answer exists), Art. XXV (labels
tell the truth: unsupported certainty becomes a stated assumption),
Art. LXXVII (the answer is the deliverable), Art. LXI (an invalid
citation is never silently converted into silence), Art. I (evidence
precedes assertion — the record must contain the value it is cited
for).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

ANSWER_DOWNGRADE_VERSION = "answer_downgrade/1.1.0"

#: the ONE plain-language caveat a downgraded delivery may carry
#: (directive 1: one plain-language caveat line at most)
DOWNGRADE_CAVEAT_LINE = (
    "Note: some supporting details in this answer could not be "
    "verified against the retrieved records and are labeled as "
    "engineering assumptions; the falsification test is the "
    "precondition for relying on them.")

_EB_LABEL_RE = re.compile(r"\bEVIDENCE[- ]BACKED\b", re.IGNORECASE)
_CITE_RE = re.compile(r"\[([^\[\]]{1,120})\]")
_CAND_ID_RE = re.compile(r"\[cand:[A-Za-z0-9_\-:.]{1,60}\]",
                         re.IGNORECASE)


def _packet_ids(packet: Optional[List[Dict[str, Any]]]) -> set:
    ids: set = set()
    for e in packet or []:
        if not isinstance(e, dict):
            continue
        for k in ("id", "source_id", "item_id", "doi", "title"):
            v = e.get(k)
            if isinstance(v, str) and v.strip():
                ids.add(v.strip().lower())
                ids.add(v.strip().lower().replace("doi:", ""))
    return ids


def _citation_valid(cite: str, packet_ids: set,
                    user_citation_ok: bool = True) -> bool:
    """A citation is VALID when it names a packet record (id/doi/title
    fragment match) OR is a user-provenance span ([user constraint] /
    [user-stated clarification] — P0-5: the user's own text is a legal
    provenance span)."""
    c = cite.strip().lower()
    if not c:
        return False
    if user_citation_ok and (
            c.startswith("user") or "user-stated" in c
            or "user constraint" in c
            or "user-stated clarification" in c):
        return True
    if c in packet_ids:
        return True
    c2 = c.replace("doi:", "").strip()
    if c2 in packet_ids:
        return True
    for pid in packet_ids:
        if len(pid) >= 8 and (pid in c2 or c2 in pid):
            return True
    return False


_EB_WITH_CITE_RE = re.compile(
    r"(?P<label>\bEVIDENCE[- ]BACKED\b)(?P<mid>[^\[\n]{0,120}?)"
    r"(?P<cite>\[[^\[\]\n]{1,120}\])", re.IGNORECASE)
_EB_NO_CITE_RE = re.compile(
    r"(?P<label>\bEVIDENCE[- ]BACKED\b)(?P<mid>[^\[\n]{0,120})"
    r"(?!\s*\[)", re.IGNORECASE)


def downgrade_answer(answer: str,
                     contract_violations: List[Any],
                     packet: Optional[List[Dict[str, Any]]],
                     ) -> Dict[str, Any]:
    """Deterministically downgrade a contract-invalid answer.

    Per claim: an EVIDENCE-BACKED label whose SAME-LINE citation is
    invalid (absent from the packet, not a user-provenance span) is
    relabeled ASSUMPTION and the citation is dropped; a label with no
    citation at all is relabeled ASSUMPTION. Internal candidate ids
    ("[cand:...]") are stripped (directive 1). NEVER adds support,
    never rewrites engineering content — it only relabels and removes.

    Returns {answer, n_relabels, n_citations_dropped, n_jargon_stripped,
             relabels, citations_dropped}."""
    text = str(answer or "")
    packet_ids = _packet_ids(packet)
    relabels: List[str] = []
    dropped: List[str] = []

    def _eb_cite_sub(m: "re.Match") -> str:
        cite = m.group("cite")[1:-1]
        if _citation_valid(cite, packet_ids):
            return m.group(0)
        dropped.append(cite.strip()[:80])
        relabels.append((m.group("label") + m.group("mid")).strip()[:160])
        return "ASSUMPTION" + m.group("mid")

    text = _EB_WITH_CITE_RE.sub(_eb_cite_sub, text)

    # labels with no bracketed id on the same line (contract violation:
    # label without reference) — relabel, drop nothing
    def _eb_nocite_sub(m: "re.Match") -> str:
        relabels.append((m.group("label") + m.group("mid")).strip()[:160])
        return "ASSUMPTION" + m.group("mid")

    text = _EB_NO_CITE_RE.sub(_eb_nocite_sub, text)

    # 2. pipeline-internal candidate ids never ship (directive 1)
    n_jargon = len(_CAND_ID_RE.findall(text))
    if n_jargon:
        text = _CAND_ID_RE.sub("", text)

    # collapse the whitespace the dropped citations left behind
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return {"downgrade_version": ANSWER_DOWNGRADE_VERSION,
            "answer": text,
            "n_relabels": len(relabels),
            "n_citations_dropped": len(dropped),
            "n_jargon_stripped": n_jargon,
            "relabels": relabels[:10],
            "citations_dropped": dropped[:10]}


def truncate_at_sentence(text: str, max_chars: int = 6000) -> str:
    """A truncated draft delivered at the last COMPLETE sentence
    boundary (owner: 'a truncated ... answer with a plain caveat beats
    a blank'). Never cuts mid-word; never returns more than max_chars."""
    t = str(text or "").strip()
    if len(t) <= max_chars:
        return t
    t = t[:max_chars]
    cut = max(t.rfind("."), t.rfind("!"), t.rfind("?"), t.rfind("\n"))
    if cut < int(max_chars * 0.5):
        return t
    return t[:cut + 1].rstrip()


# ---------------------------------------------------------------------------
# STRICT PROVENANCE (owner audit round 2026-11-13, directive 2) — the
# value-level downgrade pass. See the module docstring above for the
# measured defect and the rules.
# ---------------------------------------------------------------------------

#: PARAMETER line shape: "PARAMETER: <name> — <value> — EVIDENCE-BACKED
#: [cite]" (em-dash or hyphen separators, as the committed answers use)
_PARAM_EB_LINE_RE = re.compile(
    r"(?P<head>\bPARAMETER\s*:\s*[^\n]*?)"
    r"(?P<sep>[—-])\s*(?P<value>[^—\-\n]+?)\s*(?P=sep)\s*"
    r"(?P<label>\bEVIDENCE[- ]BACKED\b)"
    r"(?P<cite>(?:\s*\[[^\[\]\n]{1,120}\])?)", re.IGNORECASE)

# R9 P0 (measured live shape, v2 p02 attempts 4-6): the A0+ repair's
# LABEL TEMPLATE produces the label-FIRST form — 'EVIDENCE-BACKED
# PARAMETER: <name> = <value> [doi:...]' — which the label-LAST regex
# above never matched: the strict relabel reported 0 relabels while
# the contract's joint-support check flagged the same lines
# value_not_in_source x10 (the honesty net had a hole exactly where the
# repair writes). The label-FIRST shape joins the relabel scan with
# the SAME group names and the SAME _sub handler (one honesty rule,
# two line shapes, Art. X).
_PARAM_EB_LINE_FIRST_RE = re.compile(
    r"(?P<label>\bEVIDENCE[- ]BACKED\b)\s*"
    r"(?P<head>PARAMETER\s*:)"
    # the value is the WHOLE parameter statement (prose or name=value)
    # up to its citation bracket — tempered so it never swallows past
    # the line's own citation or into the NEXT label-first parameter
    # (measured live shape, v2 fu005: two labeled parameters on one
    # line; the greedy value ran across and mis-scoped the honesty
    # check)
    r"(?P<value>(?:(?!\s*\[[^\[\]\n]{1,120}\])"
    r"(?!\s*EVIDENCE[- ]BACKED\b)"
    r"(?!\s*ASSUMPTION\b)[^\[\]\n])+)"
    r"\s*(?P<cite>\[[^\[\]\n]{1,120}\])?", re.IGNORECASE)

# R11 owner item 6 (the audited live regression, fu-004 bytes): the
# CLAIM-level shape — 'Reduces overshoot by 40% (EVIDENCE-BACKED
# [doi:...])' / '**Proportional gain (Kp):** 0.8 x baseline PID Kp
# (EVIDENCE-BACKED [doi:...])' — an EVIDENCE-BACKED citation attached
# to a NON-PARAMETER line. The strict value-level honesty scan is
# extended to these lines: every number+unit stated in the claim
# text BEFORE the citation must be found in the cited record; a
# number the record never states relabels the claim ASSUMPTION and
# DROPS the citation (the same rule as the PARAMETER lines, one
# honesty rule, all line shapes).
_EB_CLAIM_RE = re.compile(
    r"(?P<claim>[^\[\]\n]{15,240}?)"
    r"(?P<label>\((?:EVIDENCE[- ]BACKED)[^()\[\]\n]{0,60}\)"
    r"|\bEVIDENCE[- ]BACKED\b)"
    r"(?P<cite>\s*\[[^\[\]\n]{1,120}\]?\s*\)?)", re.IGNORECASE)

_NUM_UNIT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?P<unit>%|percent|wt\s*%|wt%|mm|cm|µm|um|m\b|"
    r"years?|yrs?|yr|months?|days?|hours?|hrs?|h\b|minutes?|min\b|"
    r"°\s*C|deg\s*C|C\b|K\b|V\b|mV\b|kV\b|A\b|mA\b|Hz\b|kHz\b|MHz\b|"
    r"g/m2/day|g/m²/day|g/m\^2/day|MPa|kPa|GPa|bar\b|kW\b|W\b|wt\s*%|"
    r"ppm|ppb|L\b|mL\b|kg\b|g\b)",
    re.IGNORECASE)

_WORD_VALUE_STOP = frozenset({
    "the", "and", "for", "with", "from", "during", "after", "before",
    "below", "above", "into", "than", "then", "method", "type", "class",
    "based", "using", "per", "via", "value", "level", "target", "goal",
})

_NUM_VARIANTS = {
    # the decimal variants a record may spell the same quantity with
    "2.0": ("2(?:\\.0)?",), "0.4": ("0\\.4",), "75": ("75(?:\\.0)?",),
}


def _num_pattern(num: str) -> str:
    """The word-bounded regex variants for one number ("2.0" also
    matches "2"; a plain integer matches itself). R11 fix (measured
    on the claim-level pass): a trailing ".0" is OPTIONAL, not
    dropped — the old empty frac_alt made "2.0" match only the bare
    "2" and then the unit pattern demanded ADJACENCY ("2mm"), so a
    record stating "2.0 mm" never matched a value of "2.0 mm" (the
    false-relabel class). "0.4" keeps its exact frac (a bare "0"
    must not match "0.5")."""
    n = num.replace(",", ".")
    if "." in n:
        head, frac = n.split(".", 1)
        if frac == "0":
            return rf"(?<![\d.]){re.escape(head)}(?:\.{frac})?(?![\d])"
        return rf"(?<![\d.]){re.escape(head)}\.{frac}(?![\d])"
    return rf"(?<![\d.]){re.escape(n)}(?![\d])"


def _unit_pattern(unit: str) -> str:
    """The flexible regex for one unit token (plural and spacing
    variants; % also matches 'percent')."""
    u = unit.strip().lower()
    # plural-normalize the time units (the value says "75 years", the
    # user's stated text says "75-year" — same quantity)
    for fam in ("years", "yrs", "months", "days", "hours", "hrs",
                "minutes"):
        if u == fam:
            u = fam.rstrip("s") if fam != "yrs" else "yr"
            break
    if u == "%":
        return r"\s*(?:%|percent)"
    if u.startswith("wt"):
        return r"\s*(?:%|wt\s*%|percent)"
    if u in ("year", "yrs", "yr"):
        return r"\s*(?:-|\s)?\s*years?(?:\s*of\s*service)?"
    if u == "month":
        return r"\s*months?"
    if u == "day":
        return r"\s*days?"
    if u in ("hour", "hr", "h"):
        return r"\s*hours?"
    if u == "min":
        return r"\s*minutes?"
    if u in ("c", "deg c"):
        return r"\s*(?:°?\s*c\b|deg\s*c|celsius)"
    if u == "g/m2/day":
        return r"\s*g/m(?:2|²|\^2)\s*/\s*day"
    if u == "m":
        return r"\s*m\b(?![a-z])"
    return re.escape(unit.strip()) + r""


def _value_membership(value: str, text: str) -> bool:
    """The binary value-membership test (see the rules in the module
    docstring): NUMERIC values — every number+unit pair must be found
    in the text; WORD-ONLY values — at least one content word found.
    Never raises; an empty value is not-in-text."""
    v = str(value or "").strip()
    if not v:
        return False
    t = str(text or "")
    nums = list(_NUM_UNIT_RE.finditer(v))
    if nums:
        for m in nums:
            pat = (_num_pattern(m.group(1)) + r"\s*"
                   + _unit_pattern(m.group("unit")))
            if not re.search(pat, t, re.IGNORECASE):
                return False
        return True
    words = [w for w in re.findall(r"[a-z][a-z\-]{3,}", v.lower())
             if w not in _WORD_VALUE_STOP]
    if not words:
        return False
    return any(re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", t,
                         re.IGNORECASE) for w in words)


def _user_provenance_text(problem: Optional[Dict[str, Any]]) -> str:
    """The user's own stated text: constraint, user variables, device,
    failure, clarification — the class a value is never labeled
    EVIDENCE-BACKED from."""
    if not problem:
        return ""
    parts = [str(problem.get(k) or "") for k in
             ("device", "failure", "failure_mode", "constraint")]
    for v in problem.get("user_variables") or []:
        parts.append(str(v))
    ca = problem.get("clarification_answer")
    if isinstance(ca, str):
        parts.append(ca)
    elif isinstance(ca, dict):
        parts.extend(str(x) for x in ca.values())
    if problem.get("clarification_text"):
        parts.append(str(problem["clarification_text"]))
    return " ".join(parts)


def strict_provenance_downgrade(
        answer: str,
        packet: Optional[List[Dict[str, Any]]],
        problem: Optional[Dict[str, Any]] = None,
        packet_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
        ) -> Dict[str, Any]:
    """The strict value-level downgrade (owner directive 2,
    2026-11-13). For every PARAMETER line labeled EVIDENCE-BACKED with
    a VALID citation: the label survives ONLY when the line's VALUE is
    found in the cited record's text (numeric values: every number+unit
    present; word-only values: at least one content word). A value
    absent from the record is relabeled ASSUMPTION — or ASSUMPTION
    (User Constraint) when the value IS the user's own stated text —
    and the citation is dropped. NEVER adds support; only removes
    unsupported certainty (Art. IV/XXV).

    Returns {answer, n_relabels, n_user_constraint_relabels, relabels,
    strict_version}."""
    text = str(answer or "")
    records: Dict[str, Dict[str, Any]] = {}
    if packet_by_id:
        records.update(packet_by_id)
    for e in packet or []:
        if not isinstance(e, dict):
            continue
        for k in ("id", "source_id", "doi", "title"):
            v = e.get(k)
            if isinstance(v, str) and v.strip():
                records[v.strip().lower()] = e
                records[v.strip().lower().replace("doi:", "")] = e
    user_text = _user_provenance_text(problem)
    relabels: List[Dict[str, Any]] = []

    def _sub(m: "re.Match") -> str:
        cite = (m.group("cite") or "").strip()
        cid = cite[1:-1].strip().lower() if cite.startswith("[") else ""
        rec = records.get(cid) or records.get(cid.replace("doi:", ""))
        if rec is None:
            # the citation itself is invalid: the id-validity downgrade
            # (the 1.0 pass) owns that class — leave it untouched here
            return m.group(0)
        rec_text = " ".join(str(rec.get(k) or "") for k in
                            ("title", "abstract", "text"))
        value = m.group("value")
        if _value_membership(value, rec_text):
            return m.group(0)
        in_user = bool(user_text) and _value_membership(value, user_text)
        new_label = ("ASSUMPTION (User Constraint)" if in_user
                     else "ASSUMPTION")
        relabels.append({
            "parameter": m.group("head").split(":", 1)[-1].strip()[:80],
            "value": value.strip()[:80],
            "new_label": new_label,
            "cited_record": (cid or "")[:80],
            "why": ("value not found in the cited record"
                    + ("; the value is the user's own stated "
                       "constraint" if in_user else ""))})
        tail = "" if not cite else " "
        # owner round 2026-11-13 item 5: the relabel carries its own
        # RATIONALE in the answer text — a bare ASSUMPTION told the
        # reader nothing about WHY certainty was removed (the measured
        # p02 shape: invented antimony/nickel values arrived as bare
        # ASSUMPTION lines, Art. XXV: the unknown stays named)
        rationale = ("ASSUMPTION (User Constraint; the user's own "
                     "stated value, not evidence)" if in_user
                     else "ASSUMPTION (value not stated in the cited "
                          "record)")
        # R11 (owner audit 2026-11-14, DEFAULT PATH item): the relabel
        # means the cited record does NOT state the value — the DOI it
        # carried is IRRELEVANT NOISE on an ASSUMPTION line and
        # misleading (it reads as support for a value the record never
        # states). The relabel rewrite DROPS the citation, both shapes,
        # and carries the rationale exactly once (the R9 measured bytes:
        # 'ASSUMPTION PARAMETER: float voltage = 2.27 V/cell [doi:...]
        # — ASSUMPTION (value not stated...)' — DOI + doubled label).
        if m.group(0).upper().startswith("EVIDENCE"):
            # label-FIRST shape ONLY (the matched text starts with the
            # label): 'EVIDENCE-BACKED PARAMETER: <statement> [cite]' ->
            # relabel in place. The label-LAST shape must keep its
            # canonical output (the committed fu005 regression pins it)
            # — both regexes' label group reads 'EVIDENCE-BACKED', so
            # the matched text's first token is the only safe
            # discriminator. The label-first value may be prose (no
            # '=' separator — the measured v2 fu005 shape), so the
            # rewrite does not reference the sep group. NO citation
            # rides the relabeled line (the R11 owner directive).
            return ("ASSUMPTION " + m.group("head") + " "
                    + value.strip() + " — "
                    + ("user's own stated value, not evidence"
                       if in_user
                       else "value not stated in the cited record"))
        return (m.group("head") + m.group("sep") + " " + value
                + " " + m.group("sep") + " " + rationale)

    new_text = _PARAM_EB_LINE_RE.sub(_sub, text)
    # the label-FIRST shape is scanned SECOND (the label-LAST regex
    # cannot match it — different group order), on the intermediate
    # text: a line the first pass already relabeled no longer carries
    # the EVIDENCE-BACKED label, so it is never double-processed
    new_text = _PARAM_EB_LINE_FIRST_RE.sub(_sub, new_text)

    # ---- R11 CLAIM-LEVEL pass (owner item 6): any remaining inline
    # 'EVIDENCE-BACKED [cite]' claim whose stated numbers are not in
    # the cited record is relabeled ASSUMPTION, citation dropped.
    def _claim_sub(m: "re.Match") -> str:
        cite = (m.group("cite") or "").strip()
        _br = re.search(r"\[([^\[\]\n]{1,120})\]", cite)
        cid = _br.group(1).strip().lower() if _br else ""
        rec = records.get(cid) or records.get(cid.replace("doi:", ""))
        if rec is None:
            return m.group(0)  # invalid-id class: the 1.0 pass owns it
        rec_text = " ".join(str(rec.get(k) or "") for k in
                            ("title", "abstract", "text"))
        claim_text = m.group("claim").strip()
        nums = list(_NUM_UNIT_RE.finditer(claim_text))
        if not nums:
            # a word-only claim: at least one content word must hit
            words = [w for w in re.findall(r"[a-z][a-z\-]{4,}",
                                           claim_text.lower())
                     if w not in _WORD_VALUE_STOP]
            if words and any(re.search(rf"(?<![\w-]){re.escape(w)}"
                                       rf"(?![\w-])", rec_text,
                                       re.IGNORECASE)
                             for w in words):
                return m.group(0)
        else:
            ok = True
            for nm in nums:
                pat = (_num_pattern(nm.group(1)) + r"\s*"
                       + _unit_pattern(nm.group("unit")))
                if not re.search(pat, rec_text, re.IGNORECASE):
                    ok = False
                    break
            if ok:
                return m.group(0)
        relabels.append({
            "parameter": ("claim: " + claim_text[:70]),
            "value": (", ".join(nm.group(0) for nm in nums))[:80]
            if nums else claim_text[:80],
            "new_label": "ASSUMPTION",
            "cited_record": (cid or "")[:80],
            "why": ("claim's stated value(s) not found in the cited "
                    "record — the R11 claim-level honesty pass")})
        # the relabel: the claim keeps its text, loses the label and
        # the citation (an ASSUMPTION never carries one). The
        # parenthetical shape's open paren rides the claim group —
        # strip it so the rebuild is balanced.
        if claim_text.endswith("("):
            claim_text = claim_text[:-1].rstrip()
        return (claim_text + " (ASSUMPTION — value not stated in the "
                "cited record)")

    new_text = _EB_CLAIM_RE.sub(_claim_sub, new_text)
    new_text = re.sub(r"[ \t]{2,}", " ", new_text)
    n_user = sum(1 for r in relabels
                 if r["new_label"] == "ASSUMPTION (User Constraint)")
    return {"strict_version": "strict_provenance/1.0.0",
            "answer": new_text,
            "n_relabels": len(relabels),
            "n_user_constraint_relabels": n_user,
            "relabels": relabels[:12]}

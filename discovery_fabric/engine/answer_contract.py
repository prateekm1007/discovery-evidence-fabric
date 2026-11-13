"""Answer-Shape Contract (R3; R6 owner directive 2026-11-11) —
deterministic, question-type routed.

Predictor-design answers MUST carry explicit {INDICATOR, THRESHOLD with
units, VALIDATION with n and pass/fail} markers. The THRESHOLD number
carries ONE of three honest provenance bases (Art. XXVII, owner
directive 2026-11-11 — packet traceability is NO LONGER required):
  1. EVIDENCE-SOURCED — the number appears in the evidence packet or a
     user-stated variable (recorded as provenance, never demanded);
  2. ASSUMPTION — the number sits on an ASSUMPTION-labeled line;
  3. CALIBRATION RULE — a defined rule, e.g. "baseline + 3 sigma from
     14 days of healthy data" (reference-state word + deviation-spec
     word in the THRESHOLD region).
A bare unlabeled threshold number with none of the three is a
violation. Intervention-proposal answers MUST name concrete parameters,
each labeled EVIDENCE-BACKED or ASSUMPTION; EVIDENCE-BACKED parameters
bind to a source id present in the packet. P0-5 (owner directive
2026-11-11, item 5) — CLAIM-LEVEL PROVENANCE: the binding is joint,
quantity + value + unit checked against the EXACT supporting span
(the cited packet record, or the specific user-variable /
clarification entry that carries it); a number elsewhere in the span
is not support (adversarial classes: same_number_wrong_quantity,
wrong_unit, unrelated_source, substring_number, value_not_in_source);
recorded conversions / derivations are admitted and recorded in
bindings["claims"]. The predictor's packet_or_user_variable threshold
basis was tightened the same way: the threshold number AND its unit
must co-occur in the blob (a bare number elsewhere is unknown). The
check is deterministic and runs against the answer text the judge
sees (Art. XXIV).
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


def _is_user_citation(tok: str) -> bool:
    """R6: a bracketed citation of USER-stated grounds — [user
    constraint], [user-stated clarification], [user variables],
    [clarification answer] — is legitimate provenance for an
    EVIDENCE-BACKED parameter. The user's stated constraint/variable is
    the ground truth of the request (the predictor branch encodes the
    same principle as the packet_or_user_variable threshold basis);
    it is not an invented number and never lives in the evidence
    packet, so demanding a packet hit for it manufactured a violation
    out of the composer's honest output (measured: fresh-run 1 sofc
    composed answer, 3 violations, all three on user citations)."""
    t = (tok or "").strip().lower()
    return t.startswith("user") or t.startswith("clarification")


def _source_map(packet) -> Dict[str, str]:
    """id/doi-with-scheme -> record text (title + abstract), for
    support-span binding of EVIDENCE-BACKED labels. Never raises."""
    out: Dict[str, str] = {}
    if not packet:
        return out
    try:
        for e in packet:
            if not isinstance(e, dict):
                continue
            text = " ".join(str(e.get(k) or "") for k in
                            ("title", "abstract", "text", "content"))
            for k in ("id", "doi", "source_id"):
                v = str(e.get(k) or "").strip()
                if v:
                    out[v.lower()] = text
                    out[v.removeprefix("doi:").lower()] = text
            doi = str(e.get("doi") or "").strip()
            if doi:
                out["doi:" + doi.lower()] = text
        return out
    except Exception:  # noqa: BLE001
        return {}


def _line_of(text: str, pos: int) -> str:
    s = text.rfind("\n", 0, pos) + 1
    e = text.find("\n", pos)
    if e == -1:
        e = len(text)
    return text[s:e]


# ---------------------------------------------------------------------
# P0-5 (owner directive 2026-11-11, item 5): claim-level provenance.
# For every quantitative claim, quantity + value + unit are checked
# JOINTLY against the exact supporting span (the cited packet record,
# or the exact user-variable / clarification entry that carries it).
# A number appearing elsewhere in the source text is NOT support for a
# different parameter (the directive's adversarial classes:
# same-number/wrong-quantity, wrong-unit, unrelated source,
# substring-number). ASSUMPTION stays available for honest,
# explicitly unverified engineering assumptions.
# ---------------------------------------------------------------------

_CLAIM_STOP = {
    "parameter", "evidence", "backed", "assumption", "value", "values",
    "unit", "units", "label", "labels", "with", "without", "that",
    "this", "these", "from", "into", "over", "under", "per", "and",
    "the", "must", "should", "stated", "states", "state", "carry",
    "holds", "held", "target", "rated", "rating", "spec", "specified",
    "specify", "specified", "concrete", "design", "named", "following",
    "each", "both", "same", "one", "two", "three", "percent",
}

_CONV_MARKER = re.compile(
    r"(?:conver\w*|equiv\w*|deri\w*|→|≈|\bi\.e\.\b|\bwhich\s+is\b|"
    r"\bthat\s+is\b)", re.IGNORECASE)


def _value_unit_pairs(seg: str) -> List[Dict[str, str]]:
    """The segment's quantitative claims: every value+unit pair in the
    stated order (the _NUM_WITH_UNIT class)."""
    out: List[Dict[str, str]] = []
    for m in _NUM_WITH_UNIT.finditer(seg or ""):
        txt = m.group(0).strip()
        m2 = re.match(r"(\d+(?:\.\d+)?)\s*([^\d\s]+)$", txt)
        if m2:
            out.append({"value": m2.group(1),
                       "unit": m2.group(2).lower()})
    return out


def _quantity_tokens(seg: str) -> set:
    """The quantity/metric words of a claim line — content words,
    minus numbers, unit words and scaffolding. These name WHICH
    physical quantity the value attaches to."""
    toks = re.findall(r"[a-zA-Z]{4,}", seg or "")
    units = set(re.findall(
        r"\b(?:mA|kA|A|mV|V|kV|kW|W|kJ|J|Hz|rpm|°C|K|Pa|kPa|MPa|GPa|"
        r"N|kN|mm|cm|m|µm|nm|g|kg|mg|t|L|mL|ppm|mol|mol/L|ms|"
        r"weeks|months|years|shifts|samples)\b",
        seg or "", re.IGNORECASE))
    out = set()
    for t in toks:
        tl = t.lower()
        if tl in _CLAIM_STOP or tl in units:
            continue
        out.add(tl)
    return out


def _qty_overlap(tokens, src_tokens) -> bool:
    """Quantity-word overlap: exact token match, or a STEM relation —
    one token contained in the other with stem length >= 5 ("cycle"
    in "cycling"/"cycles", "glass" in "glasses"). Deterministic; no
    new thresholds, just token containment."""
    for t in tokens:
        for s in src_tokens:
            if t == s:
                return True
            shorter, longer = (t, s) if len(t) <= len(s) else (s, t)
            if len(shorter) >= 5 and shorter in longer:
                return True
    return False


def _joint_support(claim_seg: str, source_seg: str) -> Dict[str, Any]:
    """P0-5: does the source span support the claim with quantity,
    value AND unit jointly?

      value_unit_supported — a claim value immediately followed by its
          unit (<= 4 chars gap, digit-guarded on both sides) occurs in
          the source span;
      quantity_supported   — at least one of the claim's quantity
          words occurs in the source span (stem relation admitted:
          "cycle" <-> "cycles"/"cycling");
      joint_supported      — both (or the claim's numbers are all
          covered: every stated pair, a claim with no pair, or a
          recorded conversion/derivation the claim itself names).

    A number elsewhere in the source span (wrong quantity, wrong
    unit, or a longer number it is a substring of) returns None of
    these — that is the P0-5 adversarial class the check exists to
    catch (Art. II/VI: exact evidence beats semantic plausibility;
    never manufacture provenance)."""
    pairs = _value_unit_pairs(claim_seg)
    qty = _quantity_tokens(claim_seg)
    src_l = (source_seg or "").lower()
    res: Dict[str, Any] = {
        "pairs": pairs,
        "quantity": sorted(qty),
        "value_unit_supported": False,
        "quantity_supported": False,
        "joint_supported": False,
        "conversion_recorded": False}
    src_qty = _quantity_tokens(src_l)
    if not pairs:
        # no value+unit pair in the claim. Either a purely qualitative
        # claim (the quantity words alone carry the check) or a numeric
        # claim whose unit is not in the word list — for the latter the
        # stated value must still appear (digit-guarded) in the span,
        # otherwise the span names the quantity but not THIS value
        # (value_not_in_source). A qualitative claim with no number at
        # all falls back to the quantity-word check.
        res["quantity_supported"] = _qty_overlap(qty, src_qty)
        nums = _numbers(claim_seg)
        if nums:
            res["value_in_span"] = any(
                re.search(r"(?<!\d)" + re.escape(n) + r"(?!\d)", src_l)
                for n in nums)
            res["joint_supported"] = (res["quantity_supported"]
                                      and res["value_in_span"])
        else:
            res["joint_supported"] = res["quantity_supported"]
        return res
    supported_pairs = 0
    # R9 P1 item 7 (owner round 2026-11-13): the audited weakness — a
    # claim with MULTIPLE numeric pairs passed when ONE pair matched,
    # and the quantity vocabulary could sit ANYWHERE in the source (a
    # value+unit in one passage licensing a quantity named paragraphs
    # away). The joint rule is now PER PAIR and ALL pairs must hold:
    # each value+unit occurrence must carry a quantity word of the
    # claim in the SAME PASSAGE (a +-120-char window around the
    # value+unit — the co-occurrence that says "this value of this
    # quantity"), and EVERY pair in the claim must be so supported.
    pair_details = []
    for p in pairs:
        pat = (r"(?<!\d)" + re.escape(p["value"]) + r"\s{0,4}"
               + re.escape(p["unit"]))
        m = re.search(pat, src_l)
        if m:
            window = src_l[max(0, m.start() - 120):m.end() + 120]
            qty_near = _qty_overlap(qty, set(_quantity_tokens(window)))
            supported_pairs += 1
            pair_details.append({
                "pair": f"{p['value']} {p['unit']}",
                "value_unit_found": True, "quantity_in_passage": qty_near})
        else:
            pair_details.append({
                "pair": f"{p['value']} {p['unit']}",
                "value_unit_found": False, "quantity_in_passage": False})
    res["pairs_detail"] = pair_details
    res["value_unit_supported"] = (
        bool(pair_details) and supported_pairs == len(pairs))
    res["quantity_supported"] = _qty_overlap(qty, src_qty)
    res["conversion_recorded"] = bool(_CONV_MARKER.search(
        claim_seg or ""))
    res["joint_supported"] = (
        res["value_unit_supported"]
        and all(d["quantity_in_passage"] for d in pair_details))
    if res["joint_supported"]:
        pass
    elif (res["conversion_recorded"] and res["quantity_supported"]
          and supported_pairs == 0 and _NUM_WITH_UNIT.search(
              source_seg or "")):
        # the claim names its own conversion (the source carries the
        # quantity and a number+unit, the claim records the
        # derivation) — admitted, and the record says so (Art. XXVII)
        res["joint_supported"] = True
        res["by"] = "recorded_conversion"
    return res


def _user_entries(user_variables: Optional[List[str]],
                  clarification: Optional[str]) -> List[str]:
    """The EXACT user-stated spans the answer may cite: each user
    variable entry + the clarification text, as separately stated
    spans (a number in entry A is not support for a quantity entry A
    never names)."""
    entries: List[str] = []
    for v in (user_variables or []):
        s = str(v or "").strip()
        if s:
            entries.append(s)
    c = str(clarification or "").strip()
    if c:
        entries.append(c)
    return entries


def _parameter_segment(text: str, label_pos: int) -> str:
    """P0-5: the PARAMETER claim the EVIDENCE-BACKED label attaches
    to — the text from the nearest PARAMETER marker before the label
    up to the label (the answer's own parameter claim: quantity name
    + value + unit, never the following validation sentences)."""
    marks = [mm.start() for mm in re.finditer(
        r"\bPARAMETER\b", text[:label_pos], re.IGNORECASE)]
    if marks:
        return text[marks[-1]:label_pos]
    return _line_of(text, label_pos)[:label_pos]


def _joint_violation_class(sup: Dict[str, Any], source: str) -> str:
    """P0-5: which adversarial class the failed joint check is.

    same_number_wrong_quantity — the value is in the source span but
      the span never names the claim's quantity (the number belongs
      to something else);
    wrong_unit                 — value + quantity present, but the
      claim's unit is not;
    unrelated_source           — neither the number nor the quantity
      appears in the cited span;
    substring_number           — the claim's number occurs only as a
      substring of a longer number in the span;
    value_not_in_source        — the span names the quantity but not
      this value (for user entries: no single entry carries both).

    The class is read off the FIRST pair whose value is relevant to
    the span (guarded/substring present) — the claim's other pairs
    (other parameters' numbers that merely share the line prefix)
    never mask a missing one (the same_number_wrong_quantity trap)."""
    src_l = (source or "").lower()
    pairs = sup.get("pairs") or []
    qty_supported = bool(sup.get("quantity_supported"))
    if not pairs:
        return ("value_not_in_source" if qty_supported
                else "unrelated_source")
    relevant = None
    for p in pairs:
        val = p["value"]
        if re.search(r"(?<!\d)" + re.escape(val) + r"(?!\d)", src_l):
            relevant = p
            break
        if val in src_l:
            relevant = p
            break
    if relevant is None:
        if qty_supported:
            return "value_not_in_source"
        return "unrelated_source"
    val, unit = relevant["value"], relevant["unit"]
    val_guarded = bool(re.search(
        r"(?<!\d)" + re.escape(val) + r"(?!\d)", src_l))
    if not val_guarded:
        return "substring_number"
    if not qty_supported:
        return "same_number_wrong_quantity"
    unit_present = bool(re.search(re.escape(unit), src_l))
    if not unit_present:
        return "wrong_unit"
    # value + quantity both present but the value is not tied to the
    # unit in the span: the number belongs to another quantity/unit in
    # that span
    return "same_number_wrong_quantity"


def _user_entries_class(segment: str, entries: List[str]) -> str:
    """P0-5 class across the user's stated entries (the citation may
    bind to ONE specific entry; a value in entry A is not support for
    a quantity entry A never names — the value_not_in_source class):
    an entry that jointly supports the segment wins; otherwise the
    class is read off the entry that names the quantity (if any),
    else the first entry."""
    per_entry = [(i, _joint_support(segment, e))
                 for i, e in enumerate(entries)]
    for i, r in per_entry:
        if r["joint_supported"]:
            return ""  # supported
    named = [r for r in per_entry if r[1]["quantity_supported"]]
    rep = named[0][1] if named else per_entry[0][1]
    src = entries[named[0][0]] if named else entries[0]
    return _joint_violation_class(rep, src)


def _threshold_unit(text: str, thr_num: Optional[str]) -> Optional[str]:
    """P0-5: the unit that co-occurs with the THRESHOLD number on the
    threshold line (value + unit stated together in the answer)."""
    if not thr_num:
        return None
    for p in _value_unit_pairs(_threshold_region(text)):
        if p["value"] == thr_num:
            return p["unit"]
    return None


def _distinctive_tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", (s or "").lower())
            if w not in {"evidence", "backed", "assumption", "parameter",
                         "value", "unit", "units", "content", "with",
                         "that", "this", "from", "into", "over"}}


def _user_blob(user_variables: Optional[List[str]],
               clarification: Optional[str]) -> str:
    return (" ".join(user_variables or []) + " " + (clarification or "")).lower()


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
    m = re.search(r"THRESHOLD\s*:\s*(\d+(?:\.\d+)?)", text or "",
                  re.IGNORECASE)
    if m:
        return m.group(1)
    # P0-5: the number the threshold carries is the one that CO-OCCURS
    # with its unit in the threshold region — "THRESHOLD: RMS > 4.5
    # mm/s" is 4.5, never the truncation "4" (the old [^\\n.]{1,80}
    # fallback cut "4.5" at the decimal point). A bare number with no
    # unit in the region falls back to the first number in the region.
    region = _threshold_region(text)
    if not region:
        return None
    for p in _value_unit_pairs(region):
        return p["value"]
    mm = re.search(r"\d+(?:\.\d+)?", region)
    return mm.group(0) if mm else None


def _threshold_region(text: str) -> str:
    """The THRESHOLD line plus the following ~300 chars (up to the next
    contract marker): the window a calibration rule must live in."""
    t = text or ""
    m = re.search(r"THRESHOLD\s*:", t, re.IGNORECASE)
    if not m:
        return ""
    rest = t[m.start():]
    nxt = re.search(r"(?:INDICATOR|PROTOCOL|VALIDATION|PARAMETER)\s*:",
                    rest[10:], re.IGNORECASE)
    return rest[:10 + nxt.start()] if nxt else rest[:300]


#: A CORRECT calibration rule states: (1) a reference state with a
#: POPULATION/WINDOW (n days of healthy data, 200 nominal cycles, …),
#: (2) a statistic with a multiplier (baseline + 3 sigma, mean + 2 std,
#: p95), and (3) a MEASUREMENT METHOD (measured from sensor logs,
#: telemetry, sampled on the healthy fleet). A bare "baseline + sigma"
#: is NOT a defined rule — it invents the window and the method
#: (Art. XXVII).
_CALIB_WIN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:days?|weeks?|hours?|shifts?|cycles?|samples?|"
    r"units?|machines?)\b|"
    r"\b(?:last|past|recent|healthy(?:\s+fleet)?|nominal|reference)\s+"
    r"(?:window|period|phase|set)\b", re.IGNORECASE)
_CALIB_METHOD = re.compile(
    r"\b(?:measure|measured|measurements?|sensor|telemetry|log\w*|"
    r"sampled|sampling|observ\w+|monitored|monitor\w*|recorded)\b",
    re.IGNORECASE)


def _calibration_rule_defined(region: str) -> Dict[str, bool]:
    r = region or ""
    return {"reference_with_window": bool(_CALIB_WIN.search(r))
            or bool(re.search(r"\bhealthy\b|\bnominal\b|\breference\b|"
                              r"\bbaseline\b", r, re.IGNORECASE)
                    and re.search(r"\d+", r)),
            "statistic_with_multiplier": bool(_CALIB_DEV.search(r)),
            "measurement_method": bool(_CALIB_METHOD.search(r))}


def _marker_segment(text: str, label: str, maxlen: int = 400) -> str:
    """The text between LABEL: and the next contract marker (or cap)."""
    t = text or ""
    m = re.search(re.escape(label) + r"\s*:\s*", t, re.IGNORECASE)
    if not m:
        return ""
    rest = t[m.end():]
    nxt = re.search(r"(?:INDICATOR|THRESHOLD|VALIDATION(?:\s+PROTOCOL)?|"
                    r"PROTOCOL|PARAMETER)\s*:", rest, re.IGNORECASE)
    return (rest[:nxt.start()] if nxt else rest[:maxlen]).strip()


def _coherent_measurement(text: str) -> bool:
    """INDICATOR and VALIDATION PROTOCOL must name the same quantity:
    at least one shared distinctive content word beyond the protocol
    scaffolding."""
    ind = _marker_segment(text, "INDICATOR")
    proto = _marker_segment(text, "VALIDATION") or _marker_segment(
        text, "PROTOCOL")
    if not ind or not proto:
        return False
    ind_tokens = {w for w in re.findall(r"[a-z]{3,}", ind.lower())}
    proto_tokens = {w for w in re.findall(r"[a-z]{3,}", proto.lower())}
    scaffold = {"protocol", "validation", "measured", "measure", "pass",
                "fail", "sample", "samples", "devices", "units", "fleet",
                "days", "hours", "cycles", "month", "months"}
    shared = (ind_tokens & proto_tokens) - scaffold
    return len(shared) >= 1


_COH_SCAFFOLD = {"protocol", "validation", "measured", "sample", "pass",
                 "fail", "fleet", "days"}


#: A DEFINED calibration rule: a reference-state word (what the rule is
#: measured against) AND a deviation spec (how far above it) — e.g.
#: "baseline + 3 sigma computed from 14 days of healthy data",
#: "mean + 2 std over the 30-day nominal window", "p95 of the healthy
#: fleet". One instrument, deterministic (Art. XXVII: the rule, not a
#: number pulled from the air).
_CALIB_REF = re.compile(
    r"\b(?:baseline|mean|average|nominal|healthy|calibrat\w*|reference)\b",
    re.IGNORECASE)
_CALIB_DEV = re.compile(
    r"\b(?:sigma|\u03c3|std(?:\s?dev)?|s\.d\.|mad|percentile|p95|p99|"
    r"z-?score)\b|\+\s*\d+(?:\.\d+)?\s*(?:x\s*)?\w*\s*(?:sigma|\u03c3|std)",
    re.IGNORECASE)


def _threshold_basis(text: str, thr_num: Optional[str],
                     blob: str) -> str:
    """Which honest provenance basis carries the THRESHOLD number.
    Returns one of: calibration_rule | assumption | packet | user_variable
    | unknown (never raises; used by validate_answer and diagnostics)."""
    if not thr_num:
        return "no_number"
    region = _threshold_region(text)
    for line in (text or "").splitlines():
        if re.search(r"THRESHOLD\s*:", line, re.IGNORECASE) and \
                thr_num in line:
            if re.search(r"\bASSUMPTION\b", line, re.IGNORECASE):
                return "assumption"
    if re.search(r"\bASSUMPTION\b", region, re.IGNORECASE):
        return "assumption"
    if _CALIB_REF.search(region) and _CALIB_DEV.search(region):
        return "calibration_rule"
    if blob:
        # P0-5: a bare number elsewhere in the packet/user blob is NOT
        # support — the threshold's value AND its unit must CO-OCCUR
        # in the blob ("4.5 mm/s" in the record, not "4.5" next to a
        # kW duty figure). The unit is the one the answer itself
        # states with the number (no unit stated -> no co-occurrence
        # can be established -> unknown, never a manufactured basis;
        # Art. XXVII).
        thr_unit = _threshold_unit(text, thr_num)
        if thr_unit and re.search(
                r"(?<!\d)" + re.escape(thr_num) + r"\s{0,4}"
                + re.escape(thr_unit), blob, re.IGNORECASE):
            # value+unit co-occur in packet and/or user entries (one
            # pooled base — the split is a diagnostic, not a gate)
            return "packet_or_user_variable"
    return "unknown"


# ---------------------------------------------------------------------------
# OWNER ROUND 2026-11-13, ITEM 5 — the falsification-test SPEC check.
# The measured defect (the committed r7 p02 pair, auditor-judged a
# BASELINE win): the pipeline's test named a threshold and a duration
# but NO test temperature and NO sample size n, while the baseline
# specified "60 C / 6-month test with numeric criteria". A real test
# protocol states its conditions; their absence is not a style nit, it
# is what made the answer lose (Art. LXXVII: the deliverable is judged,
# not the pipeline). Deterministic, zero-LLM; violations join the SAME
# repair call (no added calls, no new gate).
_TEMP_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:deg(?:rees)?\s*(?:C|F|K)|°\s*[CFK]|\b[CFK]\b)",
    re.IGNORECASE)
_DURATION_RE = re.compile(
    r"\d+(?:\.\d+)?[\s-]*(?:min(?:ute)?s?|h(?:ours?|rs?)|days?|weeks?|"
    r"months?|years?|cycles?)\b", re.IGNORECASE)
_SAMPLE_N_RE = re.compile(
    r"n\s*=\s*\d+|\d+\s*(?:cells?|samples?|specimens?|devices?|units?|"
    r"machines?|pumps?|bearings?|fans?|vehicles?|transformers?|plates?|"
    r"cases|fleets?)\b", re.IGNORECASE)


def _test_spec_violations(test_section: str,
                          require_temperature: bool) -> List[str]:
    """The four protocol fields (temperature / duration / n / numeric
    pass-fail) required in the falsification-test section. Temperature
    is required for physical intervention tests (every physical test
    HAS a temperature — ambient is a valid statement); predictor
    validation protocols carry duration/n/numeric but not a lab
    temperature (a monitoring protocol runs on recorded data)."""
    seg = str(test_section or "")
    if len(seg.strip()) < 20:
        return []
    out: List[str] = []
    if require_temperature and not _TEMP_RE.search(seg):
        out.append("intervention contract: falsification test states "
                   "no test temperature (a real protocol states its "
                   "conditions, e.g. 60 C ambient or the operating "
                   "temperature)")
    if not _DURATION_RE.search(seg):
        out.append("intervention contract: falsification test states "
                   "no test duration")
    if not _SAMPLE_N_RE.search(seg):
        out.append("intervention contract: falsification test states "
                   "no sample size n")
    if not (_has_number_with_unit(seg)
            or re.search(r"\d+(?:\.\d+)?\s*(?:%|mm|kV|MPa|ppm|mg|mV|A|W|"
                         r"Hz|ratio)", seg, re.IGNORECASE)):
        out.append("intervention contract: falsification test states "
                   "no numeric pass/fail criterion")
    return out


def _has_number_with_unit(text: str) -> bool:
    return bool(_NUM_WITH_UNIT.search(text or ""))


def _count_matches(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text or "", re.IGNORECASE))


#: CLEAN-OUTPUT contract (owner audit round 2026-11-12, directive 1):
#: internal state names and pipeline-history narration are FORBIDDEN in
#: the engineer-facing answer text. Typed states live in the record
#: metadata (Art. XXV); the answer reads as an engineer's
#: recommendation. Each token is a phrase the auditor saw shipped or an
#: internal typed-state family. "UNVERIFIED" is deliberately ABSENT:
#: an honestly flagged hypothesis keeps its plain-language label.
INTERNAL_NARRATION_TOKENS = (
    "contract-invalid", "contract_invalid", "composed_contract",
    "compose_truncated", "compose_failed",
    "no admissible", "no_admissible", "no surviving", "all killed",
    "automated_invention_candidate", "invention_requires_experiment",
    "invention_under_development", "mechanism_starved",
    "incomplete_infrastructure", "incomplete_data", "skipped_no_packet",
    "cand:ms:", "cand:a", "[cand:", "noncand:",
    "the adversarial gauntlet", "the gauntlet", "gauntlet killed",
    "the verification gate", "the evidence gate", "the attack gate",
    "the pipeline", "pipeline data", "the previous attempt",
    "the provided pipeline", "the frozen evidence packet",
    "packet item", "the packet record", "the evidence packet",
    "verification verdict", "attack verdict", "attack record",
    "the admission gate", "mechanism_map", "candidate envelope",
    "envelope engine", "routing ledger", "stage_log",
)


def internal_narration_tokens(text: str) -> List[str]:
    """The internal-state / narration tokens present in the answer
    text (deterministic, zero-LLM; case-insensitive, word-boundary
    for short tokens; id-like tokens containing ':' match as PREFIX —
    "cand:a" catches "cand:A2")."""
    low = str(text or "").lower()
    hits = []
    for tok in INTERNAL_NARRATION_TOKENS:
        if ":" in tok:
            if tok in low:
                hits.append(tok)
        elif len(tok) <= 8:
            if re.search(r"(?<![\w:])" + re.escape(tok) + r"(?![\w:])",
                         low):
                hits.append(tok)
        elif tok in low:
            hits.append(tok)
    return hits


def validate_answer(answer: str, question_type: str,
                    packet: Optional[List[Dict[str, Any]]] = None,
                    user_variables: Optional[List[str]] = None,
                    clarification: Optional[str] = None
                    ) -> Dict[str, Any]:
    """Return {'valid': bool, 'violations': [str], 'bindings': {...}}.

    Deterministic; zero LLM. Used by the eval harness to flag released
    answers, and by the engine's answer-shape routing."""
    violations: List[str] = []
    text = answer or ""
    _clar = clarification or ""
    blob = (_packet_blob(packet) + " " + " ".join(user_variables or [])
            + " " + _clar).lower()
    bindings = {"evidence_bound": 0, "assumption": 0, "unbound_numbers": 0,
                "all_numbers": 0, "claims": []}

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
        # OWNER ROUND 2026-11-13 item 5: the validation protocol must
        # state its duration (the data window or trial length) — a
        # protocol without a duration cannot state a detection-lead
        # claim. The window may be stated in the THRESHOLD's
        # calibration clause ("3σ measured from 21 days of healthy-fleet
        # telemetry") — that IS the protocol's data window; a duration
        # in either segment satisfies the rule.
        _psec = (_marker_segment(text, "VALIDATION")
                 or _marker_segment(text, "PROTOCOL") or text)
        if not (_DURATION_RE.search(_psec)
                or _DURATION_RE.search(_marker_segment(text,
                                                       "THRESHOLD"))):
            violations.append(
                "predictor contract: VALIDATION PROTOCOL states no "
                "duration (the data window or trial length)")
        # THRESHOLD must be tied to the named indicator: the indicator's
        # quantity word must appear in the threshold segment OR in the
        # protocol that applies the threshold (a protocol that measures a
        # different quantity does not tie — Art. XXVII/LXXXI)
        m_ind = _marker_segment(text, "INDICATOR")
        if m_ind:
            ind_tokens = set(re.findall(r"[a-z0-9]{3,}", m_ind.lower()))
            thr_tokens = set(re.findall(
                r"[a-z0-9]{3,}", _marker_segment(text, "THRESHOLD").lower()))
            proto_seg = (_marker_segment(text, "VALIDATION")
                         or _marker_segment(text, "PROTOCOL"))
            proto_tokens = (set(re.findall(r"[a-z0-9]{3,}",
                                            proto_seg.lower()))
                            - _COH_SCAFFOLD)
            if ind_tokens and not ((ind_tokens & thr_tokens)
                                   | (ind_tokens & proto_tokens)):
                violations.append(
                    "predictor contract: THRESHOLD not tied to "
                    "INDICATOR (the indicator's quantity is named in "
                    "neither the threshold nor the validation protocol)")
        # threshold provenance (owner directive 2026-11-11): the
        # threshold must carry ONE honest basis — evidence-sourced
        # (packet/user-variable), ASSUMPTION-labeled, or a defined
        # calibration rule. Packet traceability alone is no longer
        # required; a bare unlabeled number with none of the three is
        # the violation (Art. XXVII).
        thr_num = _threshold_number(text)
        basis = _threshold_basis(text, thr_num, blob)
        bindings["threshold_basis"] = basis
        if thr_num and basis == "unknown":
            violations.append(
                "predictor contract: THRESHOLD number "
                f"{thr_num} has no provenance basis (not "
                "ASSUMPTION-labeled, not a defined calibration rule, "
                "not evidence-sourced)")
        if basis == "calibration_rule":
            _cd = _calibration_rule_defined(_threshold_region(text))
            _missing = [k for k, v in _cd.items() if not v]
            if _missing:
                violations.append(
                    "predictor contract: calibration rule requires "
                    "(1) reference population/window, (2) statistic "
                    "with multiplier, (3) measurement method; missing "
                    + ", ".join(_missing))
        if not _coherent_measurement(text):
            violations.append(
                "predictor contract: the VALIDATION PROTOCOL does not "
                "name the INDICATOR quantity (no shared content word "
                "beyond protocol scaffolding) — the protocol must "
                "validate the same measure the threshold is declared on")
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
        # OWNER ROUND 2026-11-13 item 5: the test section must state a
        # real protocol's four fields (temperature, duration, n, numeric
        # pass/fail) — the measured defect that lost p02 to the baseline
        from .answer_consistency import _split_test as _cons_split
        _tsec = _cons_split(text)[1]
        violations.extend(_test_spec_violations(_tsec,
                                                require_temperature=True))
        # every EVIDENCE-BACKED parameter must bind to a packet source id
        pb = _packet_blob(packet).lower() if packet else ""
        src_map = _source_map(packet)
        for m in _EVIDENCE_BACKED.finditer(text):
            # P0-5 (owner directive 2026-11-11, item 5): the cited
            # source of THIS label is the first bracketed id that
            # follows the label on the SAME line (the composer's own
            # rule: "the bracketed packet item id MUST follow the
            # label on the same line"). A citation attached to a
            # different label/claim (an earlier label's [doi:...])
            # never binds this one — exact spans, not a pooled window
            # (Art. II/VI). History: R6 fresh-run 1 sofc — bracketed
            # ids carry the doi: scheme, so the id class admits ':';
            # user citations — [user constraint], [user-stated
            # clarification] — contain spaces (admitted) and are
            # legitimate provenance (the user's stated grounds are the
            # ground truth of the request, as the predictor branch
            # encodes as the packet_or_user_variable threshold basis).
            line_start = text.rfind("\n", 0, m.start()) + 1
            ids = re.findall(r"\[[\w][\w./: -]*?\]|https?://\S+|"
                             r"(?:paper|study|record|survey)-?\d+",
                             text[line_start:][m.start() - line_start:],
                             re.IGNORECASE)
            if not ids:
                violations.append(
                    "intervention contract: EVIDENCE-BACKED label "
                    "without a referenced source id or evidence citation")
            else:
                any_hit = False
                for i in ids:
                    _tok = i.lower().strip("[]\n \t")
                    # the packet record carries doi as a structured FIELD
                    # (bare 10.1016/...), the citation carries the doi:
                    # scheme — normalize the scheme before the hit check
                    # (R6 measured follow-up; the cited DOI must still
                    # exist in the packet either way)
                    if (_tok in pb
                            or _tok.removeprefix("doi:") in pb
                            or _is_user_citation(_tok)):
                        any_hit = True
                        break
                if not any_hit:
                    violations.append(
                        "intervention contract: EVIDENCE-BACKED source id "
                        "not found in evidence packet")
            # P0-5 (owner directive 2026-11-11, item 5): the cited
            # source must JOINTLY support the parameter claim —
            # quantity + value + unit checked against the EXACT
            # supporting span (the cited packet record, or the
            # specific user-variable / clarification entry that
            # carries it). A number elsewhere in the span is not
            # support (the adversarial classes:
            # same_number_wrong_quantity, wrong_unit,
            # unrelated_source, substring_number,
            # value_not_in_source). ASSUMPTION labels stay available —
            # they are honest unverified bases, not evidence claims.
            src_text = None
            src_entry: Optional[int] = None
            if ids:
                for i in ids:
                    _k = i.lower().strip("[]\n \t")
                    cand = src_map.get(_k) or src_map.get(
                        _k.removeprefix("doi:"))
                    if cand:
                        src_text = cand
                        break
            segment = _parameter_segment(text, m.start())
            if src_text is not None:
                sup = _joint_support(segment, src_text)
                if sup["joint_supported"]:
                    bindings["claims"].append({
                        "parameter": segment.strip()[:200],
                        "label": "evidence-backed",
                        "cited": ids[0],
                        "source_kind": "packet_record",
                        "quantity": sup["quantity"],
                        "pairs": sup["pairs"],
                        "conversion_recorded":
                            bool(sup.get("conversion_recorded"))})
                else:
                    violations.append(
                        "intervention contract: EVIDENCE-BACKED source "
                        f"{ids[0]} does not jointly support its "
                        "parameter "
                        f"({_joint_violation_class(sup, src_text)})")
            elif ids and _is_user_citation(ids[0].lower().strip("[]\n \t")):
                # user citations: the specific user-variable /
                # clarification entry that carries the quantity must
                # carry the value+unit too (a number in entry A is
                # not support for a quantity entry A never names)
                entries = _user_entries(user_variables, clarification)
                if not entries:
                    violations.append(
                        "intervention contract: EVIDENCE-BACKED user "
                        f"citation {ids[0]} has no user-stated "
                        "variable or clarification to bind to")
                else:
                    per = [(i, _joint_support(segment, e))
                           for i, e in enumerate(entries)]
                    ok = [r for r in per if r[1]["joint_supported"]]
                    if ok:
                        _sup = ok[0][1]
                        src_entry = ok[0][0]
                        bindings["claims"].append({
                            "parameter": segment.strip()[:200],
                            "label": "evidence-backed",
                            "cited": ids[0],
                            "source_kind": "user_entry",
                            "entry_index": src_entry,
                            "quantity": _sup["quantity"],
                            "pairs": _sup["pairs"],
                            "conversion_recorded":
                                bool(_sup.get("conversion_recorded"))})
                    else:
                        _named = [r for r in per
                                  if r[1]["quantity_supported"]]
                        _rep = (_named[0][1] if _named
                                else per[0][1])
                        _src = (entries[_named[0][0]]
                                if _named else entries[0])
                        violations.append(
                            "intervention contract: EVIDENCE-BACKED "
                            f"user citation {ids[0]} does not jointly "
                            "support its parameter "
                            f"({_joint_violation_class(_rep, _src)})")
        # every PARAMETER segment that carries a number must itself carry
        # a label — one labelled parameter does not licence unlabeled
        # neighbours (the label binds the parameter it sits on, not the
        # following lines; a test-criterion number outside a PARAMETER
        # segment is a validation floor, not a design parameter)
        _seg_starts = [sm.start() for sm in re.finditer(
            r"\bPARAMETER\b", text, re.IGNORECASE)]
        _n_unlab = 0
        for _si, _ss in enumerate(_seg_starts):
            _se = (_seg_starts[_si + 1]
                   if _si + 1 < len(_seg_starts) else len(text))
            _seg = text[_ss:_se]
            # R9 P0 (measured live shape, v2 p02 attempt 7): the prefix
            # label form — 'ASSUMPTION PARAMETER: <name> = <value>' /
            # 'EVIDENCE-BACKED PARAMETER: ...' — carries the label BEFORE
            # the keyword, so the segment (which STARTS at 'PARAMETER')
            # excludes its own line's label. The same-line prefix joins
            # the segment's label test (a label on the parameter's own
            # line labels that parameter — the rule's own words). The
            # NEXT segment still starts at the next 'PARAMETER', so the
            # one-label-per-line discipline is unchanged.
            _line_start = text.rfind("\n", 0, _ss) + 1
            _prefix = text[_line_start:_ss]
            # the prefix label counts ONLY when it DIRECTLY precedes the
            # keyword ('ASSUMPTION PARAMETER: ...' / 'EVIDENCE-BACKED
            # PARAMETER: ...') — a bare label ending at the keyword. A
            # label belonging to an EARLIER parameter on the same line
            # ('... EVIDENCE-BACKED [src]. PARAMETER: ...') does not
            # excuse this one (the rule's own discipline: the label
            # binds the parameter it sits on)
            _prefix_lab = re.search(
                r"\b(ASSUMPTION|EVIDENCE[- ]BACKED)\s*$", _prefix,
                re.IGNORECASE)
            if re.search(r"\bASSUMPTION\b", _seg, re.IGNORECASE) \
                    or (_prefix_lab
                        and _prefix_lab.group(1).upper().startswith(
                            "ASSUMPTION")):
                # P0-5: honest assumption parameters stay admissible —
                # recorded as ASSUMPTION claims (explicitly unverified
                # bases), never manufactured into evidence claims
                bindings["claims"].append({
                    "parameter": _seg.strip()[:200],
                    "label": "assumption",
                    "cited": None,
                    "source_kind": None,
                    "quantity": sorted(_quantity_tokens(_seg)),
                    "pairs": _value_unit_pairs(_seg),
                    "conversion_recorded":
                        bool(_CONV_MARKER.search(_seg))})
            elif re.search(r"\d", _seg) \
                    and not re.search(r"EVIDENCE-BACKED|ASSUMPTION",
                                      _seg, re.IGNORECASE) \
                    and not (_prefix_lab
                             and _prefix_lab.group(1).upper().startswith(
                                 "EVIDENCE")):
                _n_unlab += 1
        if _n_unlab:
            violations.append(
                f"intervention contract: {_n_unlab} numeric "
                "parameter(s) without an EVIDENCE-BACKED or ASSUMPTION "
                "label")
    else:
        violations.append(f"unknown question_type {question_type!r}")
    # CLEAN-OUTPUT contract (owner audit round 2026-11-12, directive 1;
    # applies to EVERY question type): internal state names and
    # pipeline-history narration never ship in the answer text — the
    # typed states live in the record metadata (Art. XXV), the answer
    # reads as an engineer's recommendation.
    for tok in internal_narration_tokens(text):
        violations.append(
            "clean-output contract: internal state/narration token "
            f"{tok!r} present in the answer text")
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
        "THRESHOLD: <number with units, the alert/failure level> — the "
        "threshold number MUST carry one honest basis, stated on the same "
        "line: an evidence-sourced number (from the packet or the user's "
        "variables), an ASSUMPTION label, or a defined calibration rule "
        "(e.g. baseline + 3 sigma from 14 days of healthy data)\n"
        "PROTOCOL: <how you validate; state n (sample count), the data "
        "window or trial duration, and the pass/fail criterion>\n"),
    "intervention-proposal": (
        "\nANSWER-SHAPE CONTRACT (intervention-proposal) — your answer MUST "
        "name concrete parameters and label EACH of them EVIDENCE-BACKED "
        "(directly supported by a packet record; the bracketed packet item "
        "id MUST follow the label on the same line, e.g. "
        "\"EVIDENCE-BACKED [item-id]\") or ASSUMPTION (your "
        "engineering assumption):\n"
        "PARAMETER: <name> — <value with units> — EVIDENCE-BACKED "
        "[<packet item id>] | ASSUMPTION\n"
        "(one line per parameter)\n"
        "The falsification test MUST state a real protocol's four fields: "
        "the test temperature (e.g. 60 C ambient or the operating "
        "temperature), the duration, the sample size n, and numeric "
        "pass/fail criteria.\n"),
}

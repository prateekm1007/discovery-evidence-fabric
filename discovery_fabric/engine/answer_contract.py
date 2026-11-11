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
must bind to a source id present in the packet. The check is
deterministic and runs against the answer text the judge sees
(Art. XXIV).
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
    if not m:
        m2 = re.search(r"THRESHOLD\s*:\s*([^\n.]{1,80})", text or "",
                       re.IGNORECASE)
        if not m2:
            return None
        # take first number match inside the line
        mm = re.search(r"\d+(?:\.\d+)?", m2.group(1))
        return mm.group(0) if mm else None
    return m.group(1)


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
        if re.search(r"(?<!\d)" + re.escape(thr_num) + r"(?!\d)",
                     blob, re.IGNORECASE):
            # present in packet and/or user variables (one pooled base —
            # the split is a diagnostic, not a gate)
            return "packet_or_user_variable"
    return "unknown"


def _has_number_with_unit(text: str) -> bool:
    return bool(_NUM_WITH_UNIT.search(text or ""))


def _count_matches(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text or "", re.IGNORECASE))


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
        # every EVIDENCE-BACKED parameter must bind to a packet source id
        pb = _packet_blob(packet).lower() if packet else ""
        src_map = _source_map(packet)
        for m in _EVIDENCE_BACKED.finditer(text):
            # look at the 200-char window before the label, or the same
            # line after it, for an id — bracketed packet ids carry the
            # doi: scheme, so the id class admits ':' (R6: the
            # composer's own contract-valid output was being rejected
            # because [doi:10.1051/...] contains a colon). R6 measured
            # follow-up (fresh-run 1, sofc): the composer's citations of
            # USER-stated grounds — [user constraint], [user-stated
            # clarification] — were rejected for the same class of
            # reason twice over: (a) the bracket contents contain
            # SPACES, which the packet-id class refuses, and (b) a
            # user citation can never appear in the packet blob. A
            # user constraint is legitimate provenance — the same
            # principle the predictor branch already encodes as the
            # packet_or_user_variable threshold basis (Task 2). The
            # id class now admits bracketed citations with spaces and
            # the hit check accepts user-/clarification-sourced
            # citations alongside packet ids.
            win = text[max(0, m.start() - 200):m.start() + 120]
            ids = re.findall(r"\[[\w][\w./: -]*?\]|https?://\S+|"
                             r"(?:paper|study|record|survey)-?\d+",
                             win, re.IGNORECASE)
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
            # the cited record must LEXICALLY SUPPORT the parameter on
            # the same line (a constitutional floor for exact binding,
            # Art. II): a source that supports *some* parameter of the
            # line must share the parameter's number or at least two
            # distinctive tokens with it.
            src_text = None
            for i in ids:
                _k = i.lower().strip("[]\n \t")
                cand = src_map.get(_k) or src_map.get(
                    _k.removeprefix("doi:"))
                if cand:
                    src_text = cand
                    break
            if src_text is not None:
                param_line = _line_of(text, m.start())
                line_nums = set(_numbers(param_line))
                srcl = src_text.lower()
                num_hit = any(re.search(r"(?<!\d)" + re.escape(n) +
                                        r"(?!\d)", srcl)
                              for n in line_nums)
                tok_hit = len(_distinctive_tokens(param_line)
                              & _distinctive_tokens(src_text)) >= 2
                if line_nums and not (num_hit or tok_hit):
                    violations.append(
                        "intervention contract: EVIDENCE-BACKED source "
                        f"{ids[0]} does not lexically support its "
                        "parameter (no shared number or distinctive "
                        "token)")
            elif ids and _is_user_citation(ids[0].lower().strip("[]\n \t")):
                # user citations: the value on the parameter line must
                # appear in the user's stated variables / clarification
                param_line = _line_of(text, m.start())
                line_nums = set(_numbers(param_line))
                u_blob = _user_blob(user_variables, clarification)
                if line_nums and not any(re.search(r"(?<!\d)" +
                                                   re.escape(n) +
                                                   r"(?!\d)", u_blob)
                                         for n in line_nums):
                    violations.append(
                        "intervention contract: user citation value not "
                        "present in the user variables / clarification")
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
            if re.search(r"\d", _seg) and not re.search(
                    r"EVIDENCE-BACKED|ASSUMPTION", _seg, re.IGNORECASE):
                _n_unlab += 1
        if _n_unlab:
            violations.append(
                f"intervention contract: {_n_unlab} numeric "
                "parameter(s) without an EVIDENCE-BACKED or ASSUMPTION "
                "label")
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
        "THRESHOLD: <number with units, the alert/failure level> — the "
        "threshold number MUST carry one honest basis, stated on the same "
        "line: an evidence-sourced number (from the packet or the user's "
        "variables), an ASSUMPTION label, or a defined calibration rule "
        "(e.g. baseline + 3 sigma from 14 days of healthy data)\n"
        "PROTOCOL: <how you validate; state n (sample count) and the "
        "pass/fail criterion>\n"),
    "intervention-proposal": (
        "\nANSWER-SHAPE CONTRACT (intervention-proposal) — your answer MUST "
        "name concrete parameters and label EACH of them EVIDENCE-BACKED "
        "(directly supported by a packet record; the bracketed packet item "
        "id MUST follow the label on the same line, e.g. "
        "\"EVIDENCE-BACKED [item-id]\") or ASSUMPTION (your "
        "engineering assumption):\n"
        "PARAMETER: <name> — <value with units> — EVIDENCE-BACKED "
        "[<packet item id>] | ASSUMPTION\n"
        "(one line per parameter)\n"),
}

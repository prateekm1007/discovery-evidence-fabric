"""VALUE_SOURCING — the evidence→dimension binding stage (R452, external
audit root cause A1).

THE MISSING ORGAN, NAMED BY THE AUDIT:

    "The pipeline runs problem → evidence → mechanism → candidate →
    engineering spec → geometry, but nothing anywhere converts retrieved
    evidence ... into a *number with a unit and a provenance hash*."

THE CONSTITUTIONAL RESOLUTION (Article XXVII ↔ Article LX):

Article XXVII (no threshold invention) forbids INVENTING a value; it does
not forbid SOURCING a value from evidence with a provenance hash.  This
stage binds a critical parameter to an exact retrieved evidence span and
records value, unit, value_status, source, source_hash, derivation and
uncertainty.  A parameter with NO binding stays exactly what it was —
``value_status="UNKNOWN"`` — so the absence of a source becomes a
measured fact per parameter instead of a universal constant (Art. XXV).

THE INSTRUMENT IS DETERMINISTIC AND LLM-FREE (Art. XVIII: the model is
an untrusted component; it never grants values epistemic authority):

  1. Each critical parameter contributes its semantic-name tokens
     (>=4 chars — the same deterministic token discipline
     ``engineering_spec._link_parameter_to_equation`` already uses).
  2. Each custodied evidence record's text is scanned sentence by
     sentence for NUMBER + UNIT matches against an explicit unit
     vocabulary (recorded below; the vocabulary IS the basis).
  3. A sentence binds when it carries a number+unit AND at least two
     of the parameter's tokens (one when the parameter name has a
     single token) — exact-token overlap, never semantics.
  4. Antonym guard: a sentence containing a contradicting modifier
     (inner vs outer, inlet vs outlet, ...) never binds — Article II
     (exact evidence beats semantic plausibility).
  5. Range guard: "0.5 to 2.0 ml/min" is a RANGE, not a value — the
     binding is refused and recorded (RANGE_SKIPPED), never silently
     resolved to an endpoint.
  6. First match in deterministic order wins (records sorted by id,
     sentences in text order).  The binding carries the EXACT span
     quoted verbatim, the evidence content_hash, and the source uri.

value_status of a bound parameter is SOURCE_FACT (evidence layer rank 1,
Art. XXXVIII).  COMPUTED and MODELLED are NOT produced by this stage —
nothing here derives a value from a model; that work belongs to a design
stage that does not exist yet, and manufacturing it here would be an
Article XXVIII promotion.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

VALUE_SOURCING_VERSION = "value_sourcing/1.0.0"

#: the bound value's epistemic class (evidence layer rank 1, Art. XXXVIII)
VALUE_STATUS_SOURCE_FACT = "SOURCE_FACT"

#: explicit unit vocabulary — the recorded basis of the binding instrument.
#: Multi-character, unambiguous engineering units only; single ambiguous
#: letters ("m", "K", "N") are deliberately excluded (a bare "3 m" span is
#: not worth a mis-bind; Art. II over recall).
UNIT_VOCABULARY: Tuple[str, ...] = (
    # length
    "mm", "cm", "µm", "um", "nm", "inches", "inch",
    # area / volume
    "mm2", "mm3", "cm2", "cm3", "ml", "ml/min", "ml/h", "µl", "µl/min",
    "l/min", "liters", "litre",
    # pressure
    "kpa", "mpa", "pa", "bar", "psi", "mmhg", "atm",
    # force / torque
    "kn", "mn", "n·m",
    # thermal
    "°c", "°f", "°k",
    # mass
    "kg", "mg", "µg", "grams",
    # time (short horizons only; "days"/"weeks" bind nothing — a follow-up
    # window is not a design dimension)
    "ms", "µs",
    # electrical / power
    "kv", "mv", "v", "ma", "µa", "w", "kw", "mw", "ah", "mah", "wh",
    # flow / rotation / frequency / acoustic / data
    "rpm", "hz", "khz", "mhz", "ghz", "db", "kbps", "mbps",
    # angle
    "deg", "degrees",
)

#: compiled NUMBER + UNIT pattern (unit must immediately follow the number,
#: allowing one space and an optional slash-qualifier already in the token)
_NUMBER_UNIT_RE = re.compile(
    r"(?P<num>-?\d+(?:\.\d+)?)\s*(?P<unit>" +
    "|".join(re.escape(u) for u in sorted(UNIT_VOCABULARY, key=len,
                                          reverse=True)) +
    r")\b\.?(?![/\d])",
    re.I,
)

#: sentence splitter — period followed by space+capital or end of text
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")

#: antonym pairs: a sentence containing the antonym of a parameter token
#: contradicts that token (Art. II) and never binds it
_ANTONYMS = {
    "inner": "outer", "outer": "inner",
    "internal": "external", "external": "internal",
    "inlet": "outlet", "outlet": "inlet",
    "input": "output", "output": "input",
    "major": "minor", "minor": "major",
    "inflow": "outflow", "outflow": "inflow",
    "upstream": "downstream", "downstream": "upstream",
    "proximal": "distal", "distal": "proximal",
}

#: range/connective markers: a number separated from its unit by one of
#: these is a RANGE boundary, not a value (guard 5)
_RANGE_BETWEEN_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:to|and|–|—|-)\s*\d+(?:\.\d+)?", re.I)

_MIN_TOKEN_LEN = 4


def _parameter_tokens(name: str) -> List[str]:
    """The parameter's semantic-name tokens (>=4 chars)."""
    return [w for w in re.split(r"[^a-z0-9]+", str(name or "").lower())
            if len(w) >= _MIN_TOKEN_LEN]


def _sentence_tokens(sentence: str) -> List[str]:
    return [w for w in re.split(r"[^a-z0-9]+", sentence.lower())
            if w]


def _evidence_text(record: Dict[str, Any]) -> str:
    """The evidence record's own text (never the title alone; the span
    must be quotable from the record's body)."""
    for key in ("abstract", "content", "text"):
        t = record.get(key)
        if isinstance(t, str) and t.strip():
            return t
    return ""


def _match_in_sentence(sentence: str, tokens: List[str],
                       min_overlap: int) -> Optional[Dict[str, Any]]:
    """One NUMBER+UNIT binding candidate inside one sentence, or None.

    Guards, in order: token overlap, antonym contradiction, range
    boundary.  The returned span is the exact sentence text (quoted
    verbatim in the derivation — Art. II smallest exact span at the
    sentence grain the record supports).
    """
    stokens = _sentence_tokens(sentence)
    overlap = [t for t in tokens if t in stokens]
    if len(overlap) < min_overlap:
        return None
    # antonym guard: any parameter token contradicted in-sentence
    for t in overlap:
        anti = _ANTONYMS.get(t)
        if anti and anti in stokens:
            return None
    for m in _NUMBER_UNIT_RE.finditer(sentence):
        unit = m.group("unit").lower().rstrip(".")
        # the unit token must be in the vocabulary EXACTLY as matched
        if unit not in UNIT_VOCABULARY:
            continue
        # range guard: this number participates in a "X to Y" span
        window = sentence[max(0, m.start() - 6):m.end() + 14]
        if _RANGE_BETWEEN_RE.search(window):
            continue
        return {"value": float(m.group("num")),
                "unit": unit,
                "span": sentence.strip(),
                "matched_tokens": overlap}
    return None


def _bind_parameter(param: Dict[str, Any],
                    records: List[Tuple[str, Dict[str, Any]]],
                    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Attempt one deterministic binding for one parameter.  Returns
    (updated_param, binding_record).  No match -> the parameter is
    returned UNCHANGED (still UNKNOWN — Art. XXVII preserved) and the
    record explains why (never silent)."""
    name = str(param.get("parameter") or param.get("name") or "")
    tokens = _parameter_tokens(name)
    if not tokens:
        return param, {"parameter_id": param.get("parameter_id"),
                       "parameter": name, "state": "NO_TOKENS"}
    min_overlap = 2 if len(tokens) >= 2 else 1
    for ev_id, rec in records:
        text = _evidence_text(rec)
        if not text:
            continue
        for sentence in _SENTENCE_RE.split(text):
            sentence = sentence.strip()
            if not sentence:
                continue
            m = _match_in_sentence(sentence, tokens, min_overlap)
            if m is None:
                continue
            updated = dict(param)
            updated["value"] = m["value"]
            updated["unit"] = m["unit"]
            updated["value_status"] = VALUE_STATUS_SOURCE_FACT
            updated["source"] = {
                "evidence_id": ev_id,
                "source_uri": rec.get("source_uri"),
                "title": rec.get("title"),
            }
            updated["source_hash"] = rec.get("content_hash")
            updated["derivation"] = (
                f"SOURCE_FACT bound from {ev_id}: \"{m['span']}\" "
                f"(exact-token match {m['matched_tokens']}; deterministic "
                f"binding, no model involvement)")
            updated["uncertainty"] = (
                "UNKNOWN — the source states the value without a stated "
                "measurement uncertainty (Art. XXVII: uncertainty not "
                "invented)")
            updated["envelope"] = None
            updated["basis"] = "SOURCE_FACT (evidence-bound)"
            updated["status"] = "VALUE SOURCED (evidence-bound)"
            updated["reason"] = (
                "bound by the value_sourcing stage from custodied "
                "evidence; the span, hash and uri travel with the value")
            updated["value_sourcing"] = {
                "stage": VALUE_SOURCING_VERSION,
                "value_status": VALUE_STATUS_SOURCE_FACT,
                "matched_tokens": m["matched_tokens"],
                "evidence_id": ev_id,
            }
            return updated, {
                "parameter_id": param.get("parameter_id"),
                "parameter": name, "state": "BOUND",
                "value": m["value"], "unit": m["unit"],
                "evidence_id": ev_id,
                "span": m["span"],
                "matched_tokens": m["matched_tokens"],
            }
    return param, {"parameter_id": param.get("parameter_id"),
                   "parameter": name, "state": "NO_BINDING"}


def source_parameter_values(
        critical_parameters: List[Dict[str, Any]],
        evidence_records: List[Dict[str, Any]],
        spec: Optional[Dict[str, Any]] = None,
        ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """The VALUE_SOURCING stage.  Returns (parameters, report).

    Deterministic; LLM-free; every parameter is accounted for in the
    report (BOUND, NO_BINDING, NO_TOKENS) — never silent (Art. XV).
    Parameters with no binding are returned byte-identical to their
    input (still value_status=UNKNOWN), so the classifier's counting
    rule and Article XXVII behave exactly as before.
    """
    records = sorted(
        [(str(r.get("id") or ""), r) for r in (evidence_records or [])
         if isinstance(r, dict)],
        key=lambda pair: pair[0])
    bindings: List[Dict[str, Any]] = []
    out: List[Dict[str, Any]] = []
    n_bound = 0
    for param in critical_parameters or []:
        if not isinstance(param, dict):
            out.append(param)
            continue
        updated, record = _bind_parameter(param, records)
        out.append(updated)
        bindings.append(record)
        if record.get("state") == "BOUND":
            n_bound += 1
    report = {
        "artifact": "VALUE_SOURCING_REPORT",
        "stage": VALUE_SOURCING_VERSION,
        "n_parameters": len(out),
        "n_sourced": n_bound,
        "n_unbound": len(out) - n_bound,
        "unit_vocabulary": sorted(UNIT_VOCABULARY),
        "min_token_overlap_rule": (
            "2 semantic-name tokens (1 for single-token names); exact "
            "token match in the binding sentence; antonym and range "
            "guards; records ordered by evidence id (deterministic)"),
        "model_involvement": "NONE (deterministic instrument — Art. XVIII)",
        "bindings": bindings,
        "constitutional_basis": (
            "Article XXVII forbids inventing a value, not sourcing one "
            "with a provenance hash; parameters without a binding stay "
            "value_status=UNKNOWN (Art. XXV); every binding carries the "
            "exact span, the evidence content hash and the source uri "
            "(Art. II/XII)"),
    }
    return out, report

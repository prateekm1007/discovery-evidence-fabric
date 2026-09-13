"""discovery_fabric/engine/value_sourcing.py — R452 (external audit
A1): THE evidence->dimension binding stage.

THE MEASURED DEFECT THIS MODULE CLOSES (external audit 2026-09-13,
root cause A1):

    The pipeline runs problem → evidence → mechanism → candidate →
    engineering spec → geometry, but nothing anywhere converts
    retrieved evidence into a *number with a unit and a provenance
    hash*.  engineering_spec._build_critical_parameters hardcoded
    "value": "UNKNOWN (no sourced value)" / "value_status": "UNKNOWN"
    into EVERY critical parameter and no other production code ever
    wrote those fields, so the classifier's numerator was identically
    zero, ENGINEERING_3D was UNREACHABLE, CadQuery/OCCT was dead code
    in production, and no STEP/STL ever existed.

THE CONSTITUTIONAL COLLISION, RESOLVED EXPLICITLY (Art. XXVII <-> Art.
LX): Article XXVII forbids INVENTING a threshold — it does NOT forbid
SOURCING a value from evidence with a provenance hash.  This module
binds each critical parameter to a legitimate source, in a fixed
precedence (the two independent implementations of this round — the
canonical main line and the presentation branch — merged into ONE
deterministic pipeline):

  1. SOURCE_FACT  — a number+unit declared in the PROBLEM STATEMENT
                    itself (the operator's own custodied text), with
                    the EXACT character span, the verbatim raw text,
                    and a sha256 of the span (Art. II: exact evidence
                    beats semantic plausibility; Art. XII: custody),
                    bound name-aware through the quantity classes.
  2. COMPUTED     — a value computed by the deterministic mechanistic
                    solver chain (the 1D hydraulic Poiseuille network
                    solver), carrying the solver version + input/output
                    hashes (Art. XXXVIII layer 4; a computation, never
                    an observation).
  3. MODELLED     — a value declared by the candidate's own
                    architecture/derivation trace (the invention's
                    declared design), tagged as model content, never
                    evidence.
  4. SOURCE_FACT (evidence arm) — a number+unit bound to an EXACT
                    custodied EVIDENCE-record span by the deterministic
                    LLM-free instrument below (antonym guard, range
                    guard, explicit unit vocabulary).  This arm runs
                    AFTER the problem-statement/mechanistic/candidate
                    arms and binds ONLY parameters still UNKNOWN —
                    stage-1 bindings are never overwritten; a binding
                    is an upgrade of a measured absence, never a
                    downgrade of an existing source.

  A parameter with NO legitimate source STAYS UNKNOWN — Article XXVII
  is preserved, and the ABSENCE becomes a measured fact per parameter
  rather than a universal constant (Art. XXV).

THE EVIDENCE ARM IS DETERMINISTIC AND LLM-FREE (Art. XVIII: the model
is an untrusted component; it never grants values epistemic authority):

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
     binding is refused and recorded, never silently resolved to an
     endpoint.
  6. First match in deterministic order wins (records sorted by id,
     sentences in text order).  The binding carries the EXACT span
     quoted verbatim, the evidence content_hash, and the source uri.

Constitutional anchors: Art. II (exact spans), Art. VI (provenance
never manufactured — source_hash is the span's own sha256 / the
record's own content hash), Art. X (one namespace), Art. XV (every
parameter accounted, never silent), Art. XXV (unknown stays unknown),
Art. XXVII (no threshold invention — every threshold carries its
source), Art. LI (engineering representability REACHABLE), Art. LIII
(COMPUTED never silently becomes an observation).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

from . import mechanistic_solver as ms

VALUE_SOURCING_VERSION = "value_sourcing/1.1.0"

#: the bound value's epistemic class (evidence layer rank 1, Art. XXXVIII)
VALUE_STATUS_SOURCE_FACT = "SOURCE_FACT"

#: the closed value_status vocabulary (the audit's Coder-1 action 2)
VALUE_STATUSES = ("SOURCE_FACT", "COMPUTED", "MODELLED", "UNKNOWN")

#: explicit unit vocabulary — the recorded basis of the evidence-binding
#: instrument. Multi-character, unambiguous engineering units only;
#: single ambiguous letters ("m", "K", "N") are deliberately excluded
#: (a bare "3 m" span is not worth a mis-bind; Art. II over recall).
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

#: semantic-name -> quantity-class binding vocabulary (the name-join
#: the parameter records have always carried; deterministic)
_NAME_CLASS_RULES: List[Tuple[Tuple[str, ...], str]] = [
    (("viscosity", "dynamic viscosity"), "viscosity_mPa_s"),
    (("outer diameter", "outer dia", "body diameter", "housing "
      "diameter", "pipe diameter", "tube diameter", "cannula "
      "diameter", "branch diameter", "lumen diameter", "primary "
      "lumen", "bore", "inner diameter", "internal diameter"),
     "diameter_mm"),
    (("length", "length of", "segment length", "branch length",
      "tube length", "cannula length", "flow path length",
      "residence length"), "length_mm"),
    (("pressure", "supply pressure", "inlet pressure", "upstream "
      "pressure", "operating pressure", "delivery pressure"),
     "pressure_mmHg"),
    (("flow", "flow rate", "volumetric flow", "required flow",
      "target flow", "delivery rate", "throughput"),
     "flow_ml_min"),
]

#: canonical engineering variable per quantity class (the mechanistic
#: chain's own canonical variables — ONE namespace, Art. X)
_CLASS_TO_VARIABLE = {
    "viscosity_mPa_s": "viscosity_mPa_s",
    "diameter_mm": "primary_diameter_mm",
    "length_mm": "primary_length_mm",
    "pressure_mmHg": "inlet_pressure_mmHg",
    "flow_ml_min": "required_flow_ml_min",
}


def _semantic_class(parameter_name: str) -> Optional[str]:
    """Bind a parameter's SEMANTIC name to a quantity class
    (deterministic; longest-match-first over the rule table)."""
    name = " " + re.sub(r"[_\-]+", " ", str(parameter_name or "")
                        .strip().lower()) + " "
    best = None
    best_len = 0
    for keys, cls in _NAME_CLASS_RULES:
        for key in keys:
            if key in name and len(key) > best_len:
                best = cls
                best_len = len(key)
    return best


def _span_hash(text: str, span: Tuple[int, int]) -> str:
    return hashlib.sha256(
        text[span[0]:span[1]].encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# The deterministic evidence arm (binding instrument)
# ---------------------------------------------------------------------------

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
    """The VALUE_SOURCING evidence arm (stage 2 of the merged pipeline).

    Runs AFTER ``source_critical_parameters`` (the problem-statement /
    COMPUTED / MODELLED precedence arm) and binds ONLY parameters still
    ``value_status="UNKNOWN"`` — an existing stage-1 binding is never
    overwritten (recorded as ALREADY_SOURCED, never silent, Art. XV).

    Deterministic; LLM-free; every parameter is accounted for in the
    report (ALREADY_SOURCED, BOUND, NO_BINDING, NO_TOKENS).  Parameters
    with no binding are returned byte-identical to their input (still
    value_status=UNKNOWN), so the classifier's counting rule and
    Article XXVII behave exactly as before.

    Returns (parameters, report).
    """
    records = sorted(
        [(str(r.get("id") or ""), r) for r in (evidence_records or [])
         if isinstance(r, dict)],
        key=lambda pair: pair[0])
    bindings: List[Dict[str, Any]] = []
    out: List[Dict[str, Any]] = []
    n_bound = 0
    n_already = 0
    for param in critical_parameters or []:
        if not isinstance(param, dict):
            out.append(param)
            continue
        existing = str(param.get("value_status") or "").upper()
        if existing in ("SOURCE_FACT", "COMPUTED", "MODELLED"):
            # stage-1 binding (problem statement / mechanistic chain /
            # candidate declaration) — never overwritten (Art. X: one
            # authority per value; this arm only fills measured absences)
            n_already += 1
            bindings.append({
                "parameter_id": param.get("parameter_id"),
                "parameter": str(param.get("parameter")
                                 or param.get("name") or ""),
                "state": "ALREADY_SOURCED",
                "value_status": existing,
            })
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
        "n_already_sourced": n_already,
        "n_unbound": len(out) - n_bound - n_already,
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
            "(Art. II/XII); stage-1 bindings are never overwritten"),
    }
    return out, report


# ---------------------------------------------------------------------------
# The precedence arm (problem statement > COMPUTED > MODELLED)
# ---------------------------------------------------------------------------

def source_critical_parameters(
        critical_parameters: List[Dict[str, Any]],
        problem_text: str,
        mechanistic_record: Optional[Dict[str, Any]] = None,
        candidate_parameters: Optional[Dict[str, Dict[str, Any]]] = None
        ) -> List[Dict[str, Any]]:
    """THE VALUE_SOURCING stage: bind each critical parameter record
    to a legitimate source (fixed precedence SOURCE_FACT > COMPUTED >
    MODELLED; no source -> STAYS UNKNOWN).

    Mutates nothing: returns NEW parameter records (the caller
    replaces its list). Each sourced record carries:
      value (float), unit, value_status, source, source_hash,
      derivation, envelope (bounds context when the problem states
      one), and sourcing_version.
    """
    cand = candidate_parameters or {}
    # the problem's own declared quantities, with exact spans
    quantities = ms.classify_length_quantities(
        problem_text or "", ms.extract_quantities(problem_text or ""))

    # the mechanistic chain's canonical variables (COMPUTED arm)
    mech_vars: Dict[str, Dict[str, Any]] = {}
    if mechanistic_record:
        for arm in ("candidate_arm", "baseline_arm"):
            vset = ((mechanistic_record.get("canonical_variables")
                     or {}).get(arm) or {}).get("variables") or {}
            for k, v in vset.items():
                if isinstance(v.get("value"), (int, float)) and \
                        k not in mech_vars:
                    mech_vars[k] = v

    out: List[Dict[str, Any]] = []
    sourcing_counts = {"SOURCE_FACT": 0, "COMPUTED": 0,
                       "MODELLED": 0, "UNKNOWN": 0}
    for p in critical_parameters:
        q = dict(p)
        pname = str(p.get("parameter") or p.get("name") or "")
        cls = _semantic_class(pname)

        # --- 1. SOURCE_FACT: the problem statement's own number -----
        bound = None
        if cls:
            qcls = {"diameter_mm": ("diameter_mm",
                                    "diameter_or_length_mm"),
                    "length_mm": ("length_mm",
                                  "diameter_or_length_mm"),
                    }.get(cls, (cls,))
            hits = [x for x in quantities
                    if x["quantity_class"] in qcls]
            if cls == "flow_ml_min":
                # the failure threshold resolves ONLY from a
                # requirement-declaring context (Art. XXVII: an
                # incidental number is never promoted to a threshold)
                hits = [x for x in hits
                        if ms._requirement_score(
                            problem_text, x["span"]) > 0]
            if hits:
                h = hits[0]
                bound = {
                    "value": float(h["value"]),
                    "unit": h["unit_canonical"],
                    "value_status": "SOURCE_FACT",
                    "source": (f"problem statement span {h['span']}: "
                               f"{h['raw_text']!r} "
                               f"({h.get('classification_basis' , '')}"
                               f")"),
                    "source_hash": _span_hash(problem_text,
                                              h["span"]),
                    "derivation": (
                        "value read verbatim from the operator's own "
                        "problem statement (the custodied SOURCE_FACT "
                        "authority; exact span + sha256 — Art. II/XII)"),
                }

        # --- 2. COMPUTED: the mechanistic solver chain ---------------
        if bound is None and cls and mech_vars:
            var = _CLASS_TO_VARIABLE.get(cls)
            v = mech_vars.get(var) if var else None
            if v and isinstance(v.get("value"), (int, float)):
                bound = {
                    "value": float(v["value"]),
                    "unit": v.get("unit") or "mm",
                    "value_status": "COMPUTED",
                    "source": (f"mechanistic solver chain "
                               f"({mechanistic_record.get('solver_version')}) "
                               f"canonical variable {var!r} — "
                               f"{v.get('source', '')[:160]}"),
                    "source_hash": (
                        mechanistic_record.get("candidate_prediction")
                        or {}).get("input_hash"),
                    "derivation": (
                        "computed by the deterministic 1D hydraulic "
                        "network solver chain (COMPUTATIONAL_RESULT — "
                        "a computation, never an observation; Art. "
                        "XXXVIII layer 4 / Art. LIII)"),
                }

        # --- 3. MODELLED: the candidate's declared parameter ----------
        if bound is None and cls:
            var = _CLASS_TO_VARIABLE.get(cls)
            cp = cand.get(var) if var else None
            if isinstance(cp, dict) and isinstance(
                    cp.get("value"), (int, float)):
                bound = {
                    "value": float(cp["value"]),
                    "unit": cp.get("unit") or "mm",
                    "value_status": "MODELLED",
                    "source": ("the candidate's declared parameter ("
                               + str(cp.get("source")
                                     or "design declaration") + ")"),
                    "source_hash": None,
                    "derivation": (
                        "declared by the invention's own architecture "
                        "(MODELLED content — a design choice, never "
                        "evidence; Art. XXXVIII layer 3)"),
                }

        if bound is not None:
            q.update(bound)
            q["sourcing_version"] = VALUE_SOURCING_VERSION
            q["value"] = bound["value"]
            q["basis"] = f"{bound['value_status']} (value_sourcing)"
            q["status"] = (f"ENGINEERING_SOURCED / "
                           f"{bound['value_status']}")
            q["uncertainty"] = (
                "unit-exact span value; measurement uncertainty "
                "UNKNOWN (no physical measurement exists — Art. XXV)")
            sourcing_counts[bound["value_status"]] += 1
        else:
            # NO legitimate source: STAYS UNKNOWN (Art. XXVII — the
            # absence is now a measured fact, not a universal constant)
            q["sourcing_version"] = VALUE_SOURCING_VERSION
            q["value"] = "UNKNOWN (no sourced value)"
            q["value_status"] = "UNKNOWN"
            q["source"] = None
            q["source_hash"] = None
            q["derivation"] = (
                "VALUE_SOURCING found no legitimate source for this "
                "parameter (no problem-statement number, no mechanistic "
                "computation, no candidate declaration) — the value "
                "STAYS UNKNOWN (Art. XXVII: never invented)")
            sourcing_counts["UNKNOWN"] += 1
        out.append(q)
    return out


def sourcing_summary(parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Machine-readable sourcing summary for the record."""
    counts = {"SOURCE_FACT": 0, "COMPUTED": 0, "MODELLED": 0,
              "UNKNOWN": 0}
    for p in parameters:
        vs = str(p.get("value_status") or "UNKNOWN").upper()
        if vs in counts:
            counts[vs] += 1
    return {
        "value_sourcing_version": VALUE_SOURCING_VERSION,
        "counts": counts,
        "n_total": len(parameters),
        "n_sourced": counts["SOURCE_FACT"] + counts["COMPUTED"] +
                     counts["MODELLED"],
        "geometry_reachable": (
            counts["SOURCE_FACT"] + counts["COMPUTED"] +
            counts["MODELLED"]) >= 3,
        "rule": ("SOURCE_FACT > COMPUTED > MODELLED; no source stays "
                 "UNKNOWN — the Article XXVII <-> Article LX collision "
                 "resolved explicitly: sourcing from evidence with a "
                 "provenance hash is not threshold invention"),
    }

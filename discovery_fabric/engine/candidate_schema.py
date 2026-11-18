"""discovery_fabric/engine/candidate_schema.py — mechanism_candidate
schema 1.1.0 (ROADMAP P1.2, claim lineage c-0068).

The extension layer over the 1.0.0 core assembled by
mechanism_space.assemble_candidate: the 1.0.0 candidate dict stays
byte-stable (its candidate_hash covers CANDIDATE_REQUIRED_FIELDS and
committed runs carry it); extend_to_1_1 wraps it with the four ENUM
fields the roadmap names, and validate_candidate_schema reads those
fields — typed findings instead of prose regexes (the F57/F58/F59
retirement path: the scanners move from parsing candidate PROSE to
reading schema FIELDS).

Enum fields and their vocabularies:

  measure_class    — the candidate's intervention-measure class. The
                     DOMAIN is the problem's allowed_measures list when
                     the problem declares one; absent declaration means
                     unrestricted (Art. XXV: the absent fact is not
                     manufactured — no allowed-set, no violation).
  signals_used     — the signals the candidate's measure consumes. The
                     DOMAIN is the problem's permitted-signal set
                     (reused verbatim from the engine's own
                     allowed_signals_from_constraint convention); absent
                     set = unrestricted, no violation fires.
  principle_id     — the TRIZ principle the candidate instantiates.
                     "UNASSIGNED" until the TRIZ JSON lands (P2); the
                     field exists now so the P2 gate reads schema, not
                     prose.
  mechanism_class  — the mechanism class DECLARATION (mandatory in the
                     bind layer since D1b). The schema field carries the
                     declared value or "UNDECLARED"; the validator fires
                     MECHANISM_CLASS_UNSTATED at schema level — the same
                     rule the prose scanner enforces, now checkable
                     without regexing prose.

  numeric_claims   — (F80, R83 c-0099) the answer's OWN stated numbers
                     as typed records {value, unit, unit_raw, quantity,
                     dimension, source_field, source_span, assumption}
                     extracted by engine.numeric_claims. OPTIONAL and
                     ADDITIVE: absent means the wrap stays byte-identical
                     to the pre-F80 1.1.0 form (the frozen machine path
                     never reads it); present-but-malformed fires
                     NUMERIC_CLAIM_MALFORMED (value not numeric / unit
                     not a non-empty string). Deep pint verification
                     lives in numeric_claims / onrow_physics.

Zero LLM, zero network. The module NEVER parses candidate prose —
every value it reads or validates is a typed schema field.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

SCHEMA_1_0 = "mechanism_candidate/1.0.0"
SCHEMA_1_1 = "mechanism_candidate/1.1.0"
UNASSIGNED = "UNASSIGNED"
UNDECLARED = "UNDECLARED"

SCHEMA_1_1_FIELDS = ("measure_class", "signals_used",
                     "principle_id", "mechanism_class")


def _problem_text(problem: Optional[Dict[str, Any]]) -> str:
    if not problem:
        return ""
    return " ".join(str(problem.get(k) or "")
                    for k in ("constraint", "problem", "statement",
                              "text"))


def permitted_signals(problem: Optional[Dict[str, Any]],
                      candidate_text: str = "") -> Optional[List[str]]:
    """The problem's permitted-signal set, from the engine's own
    deterministic convention (plausibility_critic.
    allowed_signals_from_constraint). None = no restriction stated —
    validation does NOT fire on an unstated restriction (Art. XXV)."""
    from .plausibility_critic import allowed_signals_from_constraint
    sigs, _clause = allowed_signals_from_constraint(_problem_text(problem))
    return sigs


def extend_to_1_1(cand: Dict[str, Any],
                  problem: Optional[Dict[str, Any]] = None,
                  measure_class: str = UNASSIGNED,
                  signals_used: Optional[List[str]] = None,
                  principle_id: str = UNASSIGNED,
                  mechanism_class: str = UNDECLARED,
                  allowed_measures: Optional[List[str]] = None,
                  numeric_claims: Optional[List[Dict[str, Any]]] = None,
                  ) -> Dict[str, Any]:
    """Wrap a 1.0.0 candidate into 1.1.0. The input dict is copied, the
    four enum fields are added, candidate_hash/candidate_id are NOT
    recomputed (the extension does not alter the 1.0.0 identity)."""
    if cand.get("candidate_schema") != SCHEMA_1_0:
        raise ValueError(
            f"extend_to_1_1 expects {SCHEMA_1_0}, got "
            f"{cand.get('candidate_schema')!r} — wrap the assembled "
            "1.0.0 core, never a pre-wrapped candidate")
    out = dict(cand)
    # the problem's own allowed-measures declaration wins over a caller
    # argument only when present (the problem record is the authority)
    declared = None
    if problem and problem.get("allowed_measures"):
        declared = [str(m).strip().lower()
                    for m in problem["allowed_measures"]]
    elif allowed_measures:
        declared = [str(m).strip().lower() for m in allowed_measures]
    out["candidate_schema"] = SCHEMA_1_1
    out["measure_class"] = str(measure_class or UNASSIGNED)
    out["measure_class_domain"] = declared  # None = unrestricted
    out["signals_used"] = [str(s) for s in (signals_used or [])]
    out["principle_id"] = str(principle_id or UNASSIGNED)
    out["mechanism_class"] = str(mechanism_class or UNDECLARED)
    # F80: OPTIONAL — None leaves the key ABSENT (the pre-F80
    # byte-stable wrap; the frozen machine path never attaches it)
    if numeric_claims is not None:
        out["numeric_claims"] = [dict(nc) for nc in numeric_claims]
    return out


def validate_candidate_schema(cand: Dict[str, Any],
                              problem: Optional[Dict[str, Any]] = None,
                              ) -> Dict[str, List[str]]:
    """Typed findings over the 1.1.0 enum fields. Findings use the bind
    layer's key convention (the same rule, schema-sourced). Zero prose
    parsing."""
    findings: Dict[str, List[str]] = {}
    if cand.get("candidate_schema") != SCHEMA_1_1:
        findings["SCHEMA_VERSION_MISMATCH"] = [
            f"expected {SCHEMA_1_1}, got "
            f"{cand.get('candidate_schema')!r} — run "
            "extend_to_1_1 before validating"]
        return findings
    if str(cand.get("mechanism_class") or UNDECLARED) == UNDECLARED:
        findings["MECHANISM_CLASS_UNSTATED"] = [
            "the candidate's mechanism_class enum field is UNDECLARED "
            "— the declaration is mandatory (the D1b rule, now "
            "schema-sourced instead of prose-parsed)"]
    domain = cand.get("measure_class_domain")
    mc = str(cand.get("measure_class") or UNASSIGNED)
    if domain is not None:
        if mc == UNASSIGNED or mc.strip().lower() not in domain:
            findings["MEASURE_CLASS_NOT_ALLOWED"] = [
                f"measure_class '{mc}' is not in the problem's allowed "
                f"measures {sorted(domain)} — the roadmap gate is 0 "
                "allowed-measures violations"]
    perms = permitted_signals(problem)
    if perms is not None:
        used = [str(s) for s in (cand.get("signals_used") or [])]
        outside = [s for s in used
                   if not any(s.lower().startswith(p.lower())
                              or p.lower() in s.lower() for p in perms)]
        if outside:
            findings["SIGNAL_NOT_PERMITTED"] = [
                f"signals_used {outside} are outside the problem's "
                f"permitted set {perms} — 0 unavailable-input "
                "violations is the P1 gate"]
    if str(cand.get("principle_id") or UNASSIGNED) == UNASSIGNED:
        findings["PRINCIPLE_UNASSIGNED"] = [
            "principle_id is UNASSIGNED — acceptable until the TRIZ "
            "JSON lands (P2); the P2 gate requires a typed principle "
            "on every candidate"]
    # F80 (R83 c-0099): numeric_claims is OPTIONAL — absent means no
    # finding (the pre-F80 byte-stable path); present means
    # shape-checked (value numeric + unit a non-empty string).
    if "numeric_claims" in cand:
        bad = []
        for i, nc in enumerate(cand.get("numeric_claims") or []):
            if not isinstance(nc, dict):
                bad.append(f"entry {i} is not an object")
                continue
            v = nc.get("value")
            u = nc.get("unit")
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                bad.append(f"entry {i} value {v!r} is not numeric")
            elif not isinstance(u, str) or not u.strip():
                bad.append(f"entry {i} unit {u!r} is not a non-empty "
                           "string")
        if bad:
            findings["NUMERIC_CLAIM_MALFORMED"] = [
                "numeric_claims malformed: " + "; ".join(bad)
                + " — the typed F80 fields are value (number) + unit "
                "(non-empty string); deep pint verification is the "
                "extractor's job"]
    return findings

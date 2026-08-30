"""Temporal reasoning across the evidence network (CEO directive #6:
strengthen cross-source identity, contradiction, negative evidence, and
TEMPORAL reasoning).

What existed before (entity_resolution.py): same-entity cross-source field
conflicts surfaced with both provenances; time-varying fields EXEMPT from
contradiction by explicit list. What was missing: any notion of TIME —
which observation is newer, how an entity's state progressed, and whether a
disagreement is a stale-vs-fresh pattern rather than a flat conflict.

This module adds three instruments, all metadata-only:

1. TEMPORAL_ORDER on contradictions
   When two disagreeing records both carry dates, the contradiction gains
   `temporal_order` = which value was OBSERVED later (with both dates).
   This is recorded as observation order, NOT correctness — Art. III
   (surfaced, never adjudicated) is preserved verbatim. Records without
   usable dates get TEMPORAL_ORDER_UNKNOWN (Art. XXV: never guessed).

2. ENTITY TIMELINE
   Per canonical entity: the chronological sequence of observed field
   states across sources, each step carrying provenance (source, record id,
   payload hash). Supports 'state changed at time T' statements with
   custody; undated observations are listed in a disclosed `undated`
   section, never interleaved by guesswork.

3. SUPERSESSION VIEW (time-varying fields)
   For fields exempted from contradiction BECAUSE they change over time
   (trial status, record counts, last_update...): the observed progression
   and the LATEST OBSERVED state, with per-transition provenance. The
   latest state is 'latest observed', never 'current truth' — the provider
   may have changed again after our last retrieval (Art. XXV).

Date discipline (unchanged from query_relevance.extract_record_years):
only declared date-ish keys, only 1500-2099 four-digit years; titles are
never mined for dates.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.source_registry.entity_resolution import (
    EntityRegistry, TIME_VARYING_FIELDS, extract_identity_keys,
    normalize_title,
)

# Declared date-bearing keys only (same family as query_relevance.py —
# adding a key here is a disclosed policy change, Art. XXVII).
DATE_KEYS = (
    "publication_date", "pub_year", "year", "date", "report_date",
    "event_date", "received_date", "decision_date", "component_date",
    "completion_date", "start_date", "last_update", "updated",
    "last_posted", "study_first_submitted", "primary_completion_date",
)

# State-like fields: their VALUE describes a point-in-time STATE of the
# entity (a trial's status, a record's verification level) rather than a
# stable attribute (a DOI, a journal). A cross-source disagreement on a
# state-like field with OBSERVATION DATES on both ends is plausibly a
# state PROGRESSION observed at two times — the temporal layer attaches
# that pattern WITHOUT deleting the surfaced contradiction (Art. VII: the
# conflict stays in the record; the pattern is added evidence, never a
# substitution).
STATE_LIKE_FIELDS = (
    "overall_status", "status", "study_status", "recruitment_status",
    "phase", "verification_status", "record_status", "market_status",
    "approval_status",
)


def extract_record_time(record: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """(iso_date, basis) from declared date fields; None when undated.

    Accepts YYYY, YYYY-MM, YYYY-MM-DD, and full ISO timestamps. Never
    mines free text (a title mentioning '1970' is not a date — Art. XXV).
    """
    best: Optional[Tuple[str, str]] = None

    def _consider(raw: Any, basis_key: str) -> None:
        nonlocal best
        if raw is None or isinstance(raw, (dict, list)):
            return
        s = str(raw).strip()
        if not s:
            return
        # prefer finer granularity: compare (len_of_iso, iso)
        iso = _to_iso_date(s)
        if iso is None:
            return
        if best is None or len(iso[0]) > len(best[0]):
            best = (iso[0], f"normalized field '{basis_key}'")

    def _walk(obj: Any, prefix: str = "") -> None:
        norm = obj.get("normalized") if isinstance(obj, dict) else None
        if isinstance(norm, dict):
            _walk(norm, "normalized.")
        if not isinstance(obj, dict):
            return
        for k, v in obj.items():
            key = prefix + str(k)
            if key.rsplit(".", 1)[-1] in DATE_KEYS or k in DATE_KEYS:
                _consider(v, key)

    _walk(record)
    return best


def _to_iso_date(s: str) -> Optional[Tuple[str, date]]:
    s = s.replace("Z", "").strip()
    for fmt, ln in (("%Y-%m-%dT%H:%M:%S", 10), ("%Y-%m-%d", 10),
                    ("%Y-%m", 7), ("%Y", 4)):
        try:
            dt = datetime.strptime(s[:19] if "T" in s else s[:ln], fmt)
        except ValueError:
            continue
        iso = dt.date().isoformat()[:ln] if ln < 10 else dt.date().isoformat()
        return (iso, dt.date())
    return None


def _record_ref(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_id": record.get("source_id") or record.get("source"),
        "record_id": record.get("record_id") or record.get("id"),
        "raw_payload_sha256": record.get("raw_payload_sha256")
        or record.get("content_hash"),
    }


# ---------------------------------------------------------------------------
# 1. Contradiction temporal ordering
# ---------------------------------------------------------------------------

def order_contradictions(contradictions: List[Dict[str, Any]],
                         records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach temporal_order to surfaced contradictions (metadata only).

    For each (entity, field) contradiction, find the observation dates of
    the records backing EACH distinct value. When every value has at least
    one dated backing record, attach:
      temporal_order: {newer_value, older_value, newer_date, older_date,
                       basis: 'declared date fields on backing records'}
    When any value lacks dated backing: TEMPORAL_ORDER_UNKNOWN with the
    reason. The order never changes severity and never adjudicates.
    """
    dated_refs: Dict[Tuple[str, str], Optional[str]] = {}
    for rec in records:
        ref = _record_ref(rec)
        t = extract_record_time(rec)
        dated_refs[(str(ref["source_id"]), str(ref["record_id"]))] = \
            t[0] if t else None

    out: List[Dict[str, Any]] = []
    for c in contradictions:
        c = dict(c)
        values = c.get("values") or {}
        per_value_dates: Dict[str, List[Optional[str]]] = {}
        for value_key, refs in values.items():
            per_value_dates[value_key] = []
            for r in refs:
                d = dated_refs.get((str(r.get("source_id")),
                                    str(r.get("record_id"))), None)
                per_value_dates[value_key].append(d)

        value_latest = {}
        undated_values = []
        for value_key, dates in per_value_dates.items():
            ds = [d for d in dates if d]
            if ds:
                value_latest[value_key] = max(ds)
            else:
                undated_values.append(value_key)

        if len(value_latest) >= 2 and not undated_values:
            ordered = sorted(value_latest.items(), key=lambda kv: kv[1])
            older_key, older_date = ordered[0]
            newer_key, newer_date = ordered[-1]
            c["temporal_order"] = {
                "kind": "ORDERED",
                "newer_value": newer_key,
                "older_value": older_key,
                "newer_date": newer_date,
                "older_date": older_date,
                "basis": "declared date fields on the backing records",
                "policy": (
                    "observation order only — which value was RECORDED "
                    "later; not an adjudication of which is correct "
                    "(Art. III)"),
            }
            # State-progression pattern: a state-like field observed at two
            # DIFFERENT times is plausibly one entity whose state changed.
            # The contradiction is NOT withdrawn (Art. VII) — the pattern
            # is attached as added temporal evidence.
            if c.get("field") in STATE_LIKE_FIELDS and newer_date != older_date:
                c["temporal_pattern"] = {
                    "pattern": "STATE_PROGRESSION",
                    "reading": (
                        f"state-like field '{c['field']}' observed as "
                        f"'{older_key}' at {older_date} and '{newer_key}' "
                        f"at {newer_date} — plausibly one entity whose "
                        "state changed between the observations"),
                    "policy": (
                        "HYPOTHESIS attached to the surfaced contradiction; "
                        "the conflict itself remains in the record "
                        "(Art. VII/XV — never silently resolved)"),
                }
        else:
            c["temporal_order"] = {
                "kind": "TEMPORAL_ORDER_UNKNOWN",
                "reason": (
                    f"{len(undated_values)} of {len(values)} values have no "
                    "dated backing record — Art. XXV: order is not guessed"),
            }
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# 2. Entity timeline
# ---------------------------------------------------------------------------

def entity_timeline(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Chronological observation sequence per canonical entity.

    Dated observations are ordered by date (stable: source_id, record_id);
    undated observations are DISCLOSED separately, never interleaved.
    """
    registry = EntityRegistry()
    per_entity: Dict[str, List[Dict[str, Any]]] = {}
    for rec in records:
        kind, keys = extract_identity_keys(rec)
        if not keys:
            continue
        registry.resolve([rec])
        target = registry._by_key.get(keys[0])
        if not target:
            continue
        t = extract_record_time(rec)
        per_entity.setdefault(target, []).append({
            "date": t[0] if t else None,
            "date_basis": t[1] if t else None,
            "ref": _record_ref(rec),
            "observed_fields": sorted(
                k for k in (rec.get("normalized") or {}) if k is not None),
        })

    timelines: Dict[str, Any] = {}
    for eid, obs in per_entity.items():
        dated = sorted((o for o in obs if o["date"]),
                       key=lambda o: (o["date"],
                                      str(o["ref"]["source_id"]),
                                      str(o["ref"]["record_id"])))
        undated = [o for o in obs if not o["date"]]
        timelines[eid] = {
            "observations": dated,
            "undated_observations": {
                "count": len(undated),
                "refs": [o["ref"] for o in undated],
                "policy": "undated records are never ordered by guesswork "
                          "(Art. XXV)",
            },
            "span": {
                "first": dated[0]["date"] if dated else None,
                "last": dated[-1]["date"] if dated else None,
            },
        }
    return {
        "artifact": "ENTITY_TIMELINES",
        "entities": timelines,
        "undated_total": sum(
            len([o for o in obs if not o["date"]])
            for obs in per_entity.values()),
        "date_disclosure": (
            "only declared date-bearing fields are read; free text is "
            "never mined for dates"),
    }


# ---------------------------------------------------------------------------
# 3. Supersession view for time-varying fields
# ---------------------------------------------------------------------------

def supersession_view(records: List[Dict[str, Any]],
                      fields: Optional[Tuple[str, ...]] = None) -> Dict[str, Any]:
    """Observed state progression + LATEST OBSERVED state per entity for
    time-varying fields (the fields exempted from contradiction BECAUSE
    they change over time).

    'latest_observed' is the newest DATED observation — it is a custody
    statement ('this is the freshest value we retrieved'), never a claim
    that the provider's current state matches it (Art. XXV).
    """
    fields = fields or tuple(TIME_VARYING_FIELDS)
    registry = EntityRegistry()
    rows: List[Dict[str, Any]] = []
    for rec in records:
        kind, keys = extract_identity_keys(rec)
        if not keys:
            continue
        registry.resolve([rec])
        target = registry._by_key.get(keys[0])
        if not target:
            continue
        norm = rec.get("normalized") or {}
        t = extract_record_time(rec)
        for f in fields:
            val = norm.get(f, rec.get(f) if f in rec else None)
            if val is None:
                continue
            rows.append({
                "entity_id": target,
                "field": f,
                "value": str(val).strip(),
                "date": t[0] if t else None,
                "ref": _record_ref(rec),
            })

    per: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in rows:
        per.setdefault((r["entity_id"], r["field"]), []).append(r)

    progressions: List[Dict[str, Any]] = []
    for (eid, field), obs in sorted(per.items()):
        dated = [o for o in obs if o["date"]]
        dated.sort(key=lambda o: (o["date"], str(o["ref"]["source_id"])))
        undated = [o for o in obs if not o["date"]]
        distinct = []
        for o in dated:
            if not distinct or distinct[-1]["value"] != o["value"]:
                distinct.append(o)
        undated_distinct = []
        for o in undated:
            if o["value"] not in [d["value"] for d in distinct] \
                    and o["value"] not in undated_distinct:
                undated_distinct.append(o["value"])
        # a single dated state + undated others is still disclosed (the
        # undated values carry real observations) — the progression exists
        # when EITHER side shows >1 distinct value; undated values are
        # NEVER ordered into the sequence (Art. XXV)
        if len(distinct) + len(undated_distinct) < 2:
            continue
        latest = dated[-1] if dated else None
        progressions.append({
            "entity_id": eid,
            "field": field,
            "progression": [
                {"date": o["date"], "value": o["value"], "ref": o["ref"]}
                for o in distinct
            ],
            "undated_distinct_values": undated_distinct,
            "undated_policy": (
                "undated observations are disclosed unordered; they are "
                "never interleaved into the dated progression by guesswork "
                "(Art. XXV)"),
            "latest_observed": {
                "value": latest["value"] if latest else (
                    distinct[-1]["value"] if distinct else None),
                "date": latest["date"] if latest else None,
                "ref": latest["ref"] if latest else (
                    distinct[-1]["ref"] if distinct else None),
                "disclosure": (
                    "latest OBSERVED value with custody; not a claim about "
                    "the provider's current state (Art. XXV)"),
            },
            "undated_in_series": len(undated),
        })

    return {
        "artifact": "SUPERSESSION_VIEW",
        "fields": list(fields),
        "progressions": progressions,
        "policy": (
            "time-varying fields are exempt from contradiction (they change "
            "by nature); this view records the observed PROGRESSION with "
            "provenance so temporal reasoning has custody — transitions are "
            "observations, not verdicts (Art. III)"),
    }

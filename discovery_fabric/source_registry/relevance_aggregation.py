"""Per-source relevance-adjudication AGGREGATION (custody layer, Art. XXI.4/.9).

THE GAP THIS CLOSES
-------------------
Source Coverage Maturity Model §6.1 (declared STILL OPEN, 2026-08-30):

    "Close QUERY_RELEVANCE: persist per-source relevance-adjudication
     aggregation in the custody log → then measure it."

Before this module, per-record relevance decisions (RELEVANT /
IRRELEVANT_FILTERED with recorded basis) were made inside pipeline run
artifacts (`discovery_modes/device_failure.py`) and inside the committed
battery (`source_registry/query_relevance.py`) — but each decision died
inside its own run artifact. Nothing aggregated those decisions PER SOURCE
across runs, so no relevance-quality claim about real engine usage was
admissible (Art. XXI.4: the relevance decision must be recorded as part of
the evidence custody chain).

Design
------
1. APPEND-ONLY, HASH-CHAINED LOG
   `artifacts/source_health/relevance_adjudication_log.jsonl`
   One entry per (run_id, source_id, query): counts, pooled basis method,
   and a bounded sample of adjudicated record ids (reproducibility without
   bloat). Chained exactly like `retrieval_log.py` (prev_entry_sha256 →
   entry_sha256): after-the-fact edits are detectable (Art. VI/XII).

2. ONE RECORDING PATH for every adjudication site
   - the discovery pipeline (device_failure step 4)
   - the committed QUERY_RELEVANCE battery (run_id="battery:<artifact>")
   - the Toscanini UI evidence builder (run_id="toscanini:<session>")
   All sites call `record_adjudications()`; there is no second aggregation
   semantics.

3. USAGE AGGREGATION with honest sample discipline
   `aggregate_usage()` reads the log and produces, per source:
   queries_logged, runs, records_total, relevant_total,
   irrelevant_filtered_total, pooled_rate, first/last window, per-basis
   breakdown, and a DECLARED band (Art. XXVII).

   Bands (declared here, same family as the battery's):
     3  pooled relevant-rate ≥ 2/3   (majority on-domain)
     2  pooled relevant-rate ≥ 1/3   (usable signal)
     1  pooled relevant-rate < 1/3   (off-domain flood — investigate)
     UNMEASURED_IN_USAGE  total adjudicated records < MIN_SAMPLE_RECORDS
                          (30) — Art. XXV: a small sample is never
                          extrapolated into a grade.

4. DEFECT-CLASS FLAG (hypothesis, never a verdict)
   ≥2 DISTINCT queries from ≥1 run where the provider status was OK yet
   ZERO records were adjudicated relevant → `ZERO_RELEVANT_OK_STATUS`
   (the exact defect class the battery caught five times live: status OK
   plus irrelevant records). This is an investigation trigger, never a
   kill criterion, and it is NEVER used to auto-demote a source.

5. INSTRUMENT, NOT GATE
   The aggregation is a measurement instrument (Art. XXVI
   builder-measured disclosure). It must never be wired into a kill/promote
   decision path. Reading it cannot mutate it (Art. IX).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_PATH = (
    REPO_ROOT / "artifacts" / "source_health" / "relevance_adjudication_log.jsonl"
)

RELEVANT = "RELEVANT"
IRRELEVANT = "IRRELEVANT_FILTERED"

# Declared sample floor (Art. XXV): below this many adjudicated records the
# usage aggregation says UNMEASURED_IN_USAGE rather than a band. Rationale:
# the committed battery itself adjudicates ~10 records per source; a usage
# stream thinner than the battery adds no measurement information.
MIN_SAMPLE_RECORDS = 30

# Declared bands (Art. XXVII — rationale in module docstring §3).
BAND_RULES = (
    (2 / 3, 3),
    (1 / 3, 2),
    (0.0, 1),
)

SAMPLE_RECORD_LIMIT = 5

_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Append-only hash-chained log
# ---------------------------------------------------------------------------

def _ensure_dir() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _last_entry_sha() -> Optional[str]:
    if not LOG_PATH.exists():
        return None
    last = None
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    if last is None:
        return None
    try:
        return json.loads(last).get("entry_sha256")
    except json.JSONDecodeError:
        raise RuntimeError(
            "relevance_adjudication_log.jsonl is corrupted (last line is not "
            "valid JSON); refusing to append — Art. XI: history integrity is "
            "not negotiable"
        )


def record_adjudications(
    source_id: str,
    query: str,
    adjudicated_records: Iterable[Dict[str, Any]],
    run_id: Optional[str] = None,
    provider_status: Optional[str] = None,
    sample_limit: int = SAMPLE_RECORD_LIMIT,
) -> Dict[str, Any]:
    """Persist ONE aggregation entry for a single (source, query) retrieval.

    `adjudicated_records` items are the pipeline/battery adjudication dicts:
    each must carry `relevance` in {RELEVANT, IRRELEVANT_FILTERED}; record_id
    and basis method are harvested when present. Malformed items raise
    ValueError — a relevance entry that cannot say WHICH WAY it adjudicated
    is not custody, it is noise (Art. XXI.9).
    """
    from discovery_fabric.source_registry.base import utc_now, sha256_obj

    records = list(adjudicated_records)
    relevant = 0
    irrelevant = 0
    sample: List[Dict[str, Any]] = []
    basis_methods: Dict[str, int] = {}

    for r in records:
        rel = r.get("relevance")
        if rel not in (RELEVANT, IRRELEVANT):
            raise ValueError(
                f"adjudication record without a valid relevance verdict: "
                f"{r.get('record_id', '<no id>')!r} -> {rel!r}"
            )
        if rel == RELEVANT:
            relevant += 1
        else:
            irrelevant += 1
        basis = (r.get("relevance_basis") or {}).get("method")
        if basis:
            key = basis.strip()
            basis_methods[key] = basis_methods.get(key, 0) + 1
        if len(sample) < sample_limit:
            sample.append({
                "record_id": r.get("record_id"),
                "relevance": rel,
            })

    with _LOCK:
        prev_sha = _last_entry_sha()
        entry = {
            "source_id": source_id,
            "query": query,
            "run_id": run_id,
            "provider_status": provider_status,
            "records_retrieved": len(records),
            "records_relevant": relevant,
            "records_irrelevant_filtered": irrelevant,
            "pooled_basis_methods": basis_methods or None,
            "sample_record_ids": sample,
            "timestamp": utc_now(),
            "prev_entry_sha256": prev_sha,
        }
        entry["entry_sha256"] = sha256_obj(entry)
        _ensure_dir()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        return entry


def verify_chain() -> Dict[str, Any]:
    """Verify the hash chain of the whole adjudication log (audit)."""
    from discovery_fabric.source_registry.base import sha256_obj

    if not LOG_PATH.exists():
        return {"entries": 0, "chain_valid": True,
                "note": "log absent (no adjudications recorded yet)"}
    entries = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    prev = None
    for i, e in enumerate(entries):
        recomputed = sha256_obj(
            {k: v for k, v in e.items() if k != "entry_sha256"})
        if recomputed != e.get("entry_sha256"):
            return {"entries": len(entries), "chain_valid": False,
                    "first_bad_index": i, "reason": "entry hash mismatch"}
        if prev is not None and e.get("prev_entry_sha256") != prev:
            return {"entries": len(entries), "chain_valid": False,
                    "first_bad_index": i, "reason": "chain link mismatch"}
        prev = e["entry_sha256"]
    return {"entries": len(entries), "chain_valid": True}


def read_entries(source_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    out = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if source_id is None or e.get("source_id") == source_id:
                out.append(e)
    return out


# ---------------------------------------------------------------------------
# Usage aggregation (declared bands + honest sample floor)
# ---------------------------------------------------------------------------

def _band(pooled_rate: float) -> Dict[str, Any]:
    for floor, band in BAND_RULES:
        if pooled_rate >= floor:
            rationale = (
                "DECLARED USAGE BANDS (Art. XXVII, relevance_aggregation.py): "
                "pooled relevant-rate >= 2/3 across real-run adjudications = 3; "
                ">= 1/3 = 2; < 1/3 = 1 (off-domain flood — investigate, never "
                "auto-demote). Sample floor: "
                f"{MIN_SAMPLE_RECORDS} adjudicated records or the grade stays "
                "UNMEASURED_IN_USAGE (Art. XXV)."
            )
            return {"usage_band": band, "band_rationale": rationale}
    raise AssertionError("unreachable")


def aggregate_usage(source_id: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate persisted adjudications per source into usage measurements.

    Returns per-source: counts, pooled rate, window, band (or honest
    UNMEASURED_IN_USAGE), and the ZERO_RELEVANT_OK_STATUS hypothesis flag.
    Reading never mutates the log (Art. IX).
    """
    entries = read_entries(source_id=source_id)
    per_source: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        sid = e.get("source_id", "<unknown>")
        agg = per_source.setdefault(sid, {
            "queries_logged": 0,
            "runs": set(),
            "records_total": 0,
            "relevant_total": 0,
            "irrelevant_filtered_total": 0,
            "ok_status_zero_relevant_queries": 0,
            "distinct_queries_zero_relevant": set(),
            "basis_methods": {},
            "first_timestamp": None,
            "last_timestamp": None,
        })
        agg["queries_logged"] += 1
        if e.get("run_id"):
            agg["runs"].add(e["run_id"])
        agg["records_total"] += e.get("records_retrieved", 0)
        agg["relevant_total"] += e.get("records_relevant", 0)
        agg["irrelevant_filtered_total"] += e.get(
            "records_irrelevant_filtered", 0)
        for m, n in (e.get("pooled_basis_methods") or {}).items():
            agg["basis_methods"][m] = agg["basis_methods"].get(m, 0) + n
        ts = e.get("timestamp")
        if ts:
            if agg["first_timestamp"] is None or ts < agg["first_timestamp"]:
                agg["first_timestamp"] = ts
            if agg["last_timestamp"] is None or ts > agg["last_timestamp"]:
                agg["last_timestamp"] = ts
        # defect-class evidence: provider said OK, engine adjudicated every
        # record irrelevant
        if (
            e.get("provider_status") == "OK"
            and e.get("records_retrieved", 0) > 0
            and e.get("records_relevant", 0) == 0
        ):
            agg["ok_status_zero_relevant_queries"] += 1
            agg["distinct_queries_zero_relevant"].add(e.get("query"))

    sources: Dict[str, Any] = {}
    for sid, agg in sorted(per_source.items()):
        total = agg["records_total"]
        relevant = agg["relevant_total"]
        pooled_rate = (relevant / total) if total else None
        zero_q = agg["distinct_queries_zero_relevant"]
        out = {
            "queries_logged": agg["queries_logged"],
            "runs": len(agg["runs"]),
            "records_total": total,
            "relevant_total": relevant,
            "irrelevant_filtered_total": agg["irrelevant_filtered_total"],
            "pooled_relevant_rate": round(pooled_rate, 3)
            if pooled_rate is not None else None,
            "window": {
                "first": agg["first_timestamp"],
                "last": agg["last_timestamp"],
            },
            "basis_methods": agg["basis_methods"],
        }
        if total >= MIN_SAMPLE_RECORDS and pooled_rate is not None:
            out.update(_band(pooled_rate))
        else:
            out["usage_band"] = "UNMEASURED_IN_USAGE"
            out["band_rationale"] = (
                f"only {total} adjudicated record(s) persisted (< "
                f"{MIN_SAMPLE_RECORDS}); Art. XXV: a thin sample is never "
                "extrapolated into a usage grade"
            )
        out["zero_relevant_ok_status"] = {
            "flagged": len(zero_q) >= 2,
            "distinct_queries": sorted(zero_q),
            "note": (
                "HYPOTHESIS FLAG (never a verdict): provider returned status "
                "OK while every retrieved record was adjudicated irrelevant "
                "on >= 2 distinct queries — the status-OK-plus-irrelevant-"
                "records defect class. Investigate the connector; do not "
                "auto-demote the source."
            ) if len(zero_q) >= 2 else None,
        }
        sources[sid] = out

    chain = verify_chain()
    return {
        "artifact": "QUERY_RELEVANCE_USAGE_AGGREGATION",
        "log_entries": chain["entries"],
        "chain_valid": chain["chain_valid"],
        "min_sample_records": MIN_SAMPLE_RECORDS,
        "basis_disclosure": (
            "builder-measured instrument (Art. XXVI): aggregates ONLY "
            "adjudications the engine actually recorded in custody; never "
            "wired into kill/promote decisions"
        ),
        "sources": sources,
    }

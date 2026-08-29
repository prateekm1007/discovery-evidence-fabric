"""Append-only, hash-chained retrieval log (provenance custody, Art. XXI.9).

Every live source query writes exactly one entry. Entries are chained:
each entry records the sha256 of the previous entry, so any after-the-fact
edit of the log is detectable (Art. VI/XII — no silent history rewrite).

Location: artifacts/source_health/retrieval_log.jsonl (committed, append-only).
The log is the custody layer BETWEEN the live request and any derived claim:
a record referenced by a dossier/graph edge must be verifiable against an
entry here (source_id + query + raw_payload_sha256).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_PATH = REPO_ROOT / "artifacts" / "source_health" / "retrieval_log.jsonl"

_LOCK = threading.Lock()


def _ensure_dir() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _last_entry_sha() -> Optional[str]:
    """Read the sha of the last entry (chain verification)."""
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
            "retrieval_log.jsonl is corrupted (last line is not valid JSON); "
            "refusing to append — Art. XI: history integrity is not negotiable"
        )


def append_entry(
    source_id: str,
    query: str,
    url: str,
    status: str,
    http_status: Optional[int],
    latency_ms: Optional[int],
    record_count: int,
    raw_payload_sha256: Optional[str],
    error: Optional[str] = None,
    run_id: Optional[str] = None,
) -> dict:
    """Append one custody entry; returns the written entry."""
    from discovery_fabric.source_registry.base import utc_now, sha256_obj

    with _LOCK:
        prev_sha = _last_entry_sha()
        entry = {
            "source_id": source_id,
            "query": query,
            "url": url,
            "status": status,
            "http_status": http_status,
            "latency_ms": latency_ms,
            "record_count": record_count,
            "raw_payload_sha256": raw_payload_sha256,
            "error": error,
            "run_id": run_id,
            "timestamp": utc_now(),
            "prev_entry_sha256": prev_sha,
        }
        entry["entry_sha256"] = sha256_obj(entry)
        _ensure_dir()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        return entry


def verify_chain() -> dict:
    """Verify the hash chain of the whole log. Returns audit summary."""
    from discovery_fabric.source_registry.base import sha256_obj

    if not LOG_PATH.exists():
        return {"entries": 0, "chain_valid": True, "note": "log absent (no queries yet)"}
    entries = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    prev = None
    for i, e in enumerate(entries):
        recomputed = sha256_obj({k: v for k, v in e.items() if k != "entry_sha256"})
        if recomputed != e.get("entry_sha256"):
            return {"entries": len(entries), "chain_valid": False,
                    "first_bad_index": i, "reason": "entry hash mismatch"}
        if prev is not None and e.get("prev_entry_sha256") != prev:
            return {"entries": len(entries), "chain_valid": False,
                    "first_bad_index": i, "reason": "chain link mismatch"}
        prev = e["entry_sha256"]
    return {"entries": len(entries), "chain_valid": True}


def read_entries(source_id: Optional[str] = None) -> list:
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

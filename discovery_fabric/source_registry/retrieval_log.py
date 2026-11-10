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
import os
import threading
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_PATH = REPO_ROOT / "artifacts" / "source_health" / "retrieval_log.jsonl"

_LOCK = threading.Lock()


def _ensure_dir() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _last_entry_sha() -> Optional[str]:
    """Read the sha of the last entry (chain verification).

    A crash mid-write can leave a partial (invalid JSON) tail. Rather
    than refusing forever (which wedges every subsequent retrieval),
    drop the partial tail and continue from the last complete entry —
    the chain integrity of the valid entries is preserved and the
    dropped bytes were never a complete record (Art. XI: history
    integrity is not negotiable, but a partial write is not history).
    """
    if not LOG_PATH.exists():
        return None
    try:
        raw = LOG_PATH.read_bytes()
    except OSError:
        return None
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    lines = text.split("\n")
    if lines and lines[-1] != "":
        lines = lines[:-1]
    last_valid_sha = None
    last_valid_end = 0
    pos = 0
    for line in lines:
        line_with_nl = line + "\n"
        s = line.strip()
        if not s:
            pos += len(line_with_nl.encode("utf-8"))
            continue
        try:
            obj = json.loads(s)
            last_valid_sha = obj.get("entry_sha256")
            last_valid_end = pos + len(line_with_nl.encode("utf-8"))
        except json.JSONDecodeError:
            break
        pos += len(line_with_nl.encode("utf-8"))
    try:
        if last_valid_end < len(raw):
            with LOG_PATH.open("r+b") as f:
                f.truncate(last_valid_end)
    except OSError:
        pass
    return last_valid_sha


def _file_lock(path: Path):
    """Cross-process exclusive lock (best-effort; falls back to no lock)."""
    import contextlib

    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = lock_path.open("w")

    @contextlib.contextmanager
    def _ctx():
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX)
        except Exception:
            pass
        try:
            yield
        finally:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_UN)
            except Exception:
                pass
            f.close()

    return _ctx()


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
    rate_limit_remaining: Optional[str] = None,
    retrieval_role: Optional[str] = None,
) -> dict:
    """Append one custody entry; returns the written entry.

    rate_limit_remaining: PROVIDER-REPORTED metering state (e.g. Patent
    Bear usage.monthly_remaining), stored verbatim as a string. It is the
    provider's own accounting, never an engine-side estimate (Art. VI).

    retrieval_role (R401-WC2, CEO directive 5): the CALLER's purpose —
    DISCOVERY (evidence-finding for synthesis) or VERIFICATION
    (adversarial prior-art/contradiction search). The discovery and
    verification retrieval planes are SEPARATE lanes by contract: the
    role field makes the separation machine-visible on every custody
    entry. Legacy entries (pre-R401-WC2) carry None — the role is
    additive metadata, never a behavior change; the chain hash covers
    the entry as stored, so old and new entries verify identically.
    """
    from discovery_fabric.source_registry.base import utc_now, sha256_obj

    with _file_lock(LOG_PATH):
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
                "rate_limit_remaining": rate_limit_remaining,
                "retrieval_role": retrieval_role,
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

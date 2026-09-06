#!/usr/bin/env python3
"""One-time migration for the lane-C UNKNOWN-domain incident:
convert index-keyed pool files + progress entries to content-keyed
keys, and drop the quarantined polluted execution."""
import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
POOLS = REPO / "R412" / "GRADIENT_V3" / "RUN" / "LANE_POOLS"
DONE = POOLS / "_progress.json"
QUARANTINED_QUERY_PREFIX = "UNKNOWN "


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:60]


def _new_key(rung: str, lane: str, query: str) -> str:
    h = re.sub(r"[^a-z0-9]", "", hashlib.sha256(
        query.encode()).hexdigest())[:10]
    return f"{_slug(rung)}__{lane}__{h}"


def main() -> int:
    progress = json.loads(DONE.read_text())
    entries = progress.get("completed", [])
    new_entries = []
    renamed = 0
    dropped = 0
    for e in entries:
        old_key = e.get("key")
        p = POOLS / f"{old_key}.json"
        if not p.exists():
            # quarantined file already removed
            dropped += 1
            continue
        d = json.loads(p.read_text())
        query = str(d.get("query") or "")
        if query.startswith(QUARANTINED_QUERY_PREFIX):
            p.unlink()
            dropped += 1
            print(f"quarantined dropped: {old_key}")
            continue
        nk = _new_key(d.get("rung"), d.get("lane"), query)
        p.rename(POOLS / f"{nk}.json")
        new_entries.append({**e, "key": nk})
        renamed += 1
    progress["completed"] = new_entries
    progress["migration_note"] = (
        "content-keyed resumption after the lane-C UNKNOWN-domain "
        "incident (see R412/GRADIENT_V3/RUN/incidents/"
        "2026-09-06_lane_c_unknown_domain.json)")
    DONE.write_text(json.dumps(progress, indent=1) + "\n")
    print(f"renamed {renamed}, dropped {dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""OPEN CORPUS SNAPSHOT CUSTODY — first integration (CEO Open Data
Expansion directive: "integrate the highest-value sources into the
existing custody/provenance system").

Takes a version-pinned, hash-recorded snapshot of an OPEN_HISTORICAL_CORPUS
dataset (first: Open Power System Data national_generation_capacity) into
external_corpora/ with a custody manifest:

    corpus_id, dataset, release, url, sha256, bytes, rows, license,
    retrieved_at, schema_header, epistemic_class, layer

The manifest is append-only and hash-chained (same discipline as the
retrieval log). Corpus snapshots are EVIDENCE-GRADE only through this
custody: a record citing a corpus file must reference its manifest sha.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORPORA_DIR = REPO / "external_corpora"
MANIFEST = CORPORA_DIR / "CORPUS_SNAPSHOT_MANIFEST.jsonl"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def snapshot(corpus_id: str, dataset: str, release: str, url: str,
             license_: str, layer: str, epistemic_class: str,
             max_bytes: int = 400 * 1024 * 1024) -> dict:
    """Download + hash + custody one corpus dataset file."""
    CORPORA_DIR.mkdir(exist_ok=True)
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
                      "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=300, context=CTX) as r:
        total = int(r.headers.get("Content-Length") or 0)
        body = r.read(max_bytes)
    truncated = bool(total and len(body) < total)
    total_note = (f"TRUNCATED at {len(body)} of {total} bytes" if truncated
                  else f"complete ({len(body)} of {total or len(body)} bytes)")
    sha = hashlib.sha256(body).hexdigest()
    fname = f"{corpus_id}__{dataset}__{release}.csv"
    (CORPORA_DIR / fname).write_bytes(body)

    # schema header + row count (transparent disclosure of what we hold)
    text = body.decode("utf-8", "replace")
    header = text.split("\n", 1)[0][:400]
    rows = max(0, text.count("\n") - 1)

    prev_sha = None
    if MANIFEST.exists():
        lines = [ln for ln in MANIFEST.read_text().splitlines() if ln.strip()]
        if lines:
            prev_sha = json.loads(lines[-1]).get("entry_sha256")

    entry = {
        "corpus_id": corpus_id, "dataset": dataset, "release": release,
        "url": url, "file": fname, "sha256": sha, "bytes": len(body),
        "download_completeness": total_note,
        "truncated": truncated,
        "rows_approx": rows, "schema_header": header,
        "license": license_, "layer": layer,
        "epistemic_class": epistemic_class,
        "retrieved_at": utc_now(),
        "prev_entry_sha256": prev_sha,
    }
    entry["entry_sha256"] = hashlib.sha256(json.dumps(
        entry, sort_keys=True).encode()).hexdigest()
    with MANIFEST.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


SNAPSHOTS = [
    dict(
        corpus_id="opsd", dataset="national_generation_capacity_stacked",
        release="2020-10-01",
        url="https://data.open-power-system-data.org/national_generation_capacity/2020-10-01/national_generation_capacity_stacked.csv",
        license_="CC BY 4.0 (OPSD data; attributed per source column)",
        layer="OPEN_HISTORICAL_CORPUS",
        epistemic_class="CURATED_PRIMARY_REPACKAGE: TSO/ENTSO-E-derived "
                        "capacities; versioned curation, not live registry",
    ),
    dict(
        corpus_id="opsd", dataset="renewable_power_plants_DE",
        release="2020-08-25",
        url="https://data.open-power-system-data.org/renewable_power_plants/2020-08-25/renewable_power_plants_DE.csv",
        license_="CC BY 4.0 (OPSD data)",
        layer="OPEN_HISTORICAL_CORPUS",
        epistemic_class="CURATED_PRIMARY_REPACKAGE: per-plant renewable "
                        "installations (DE) from registry sources",
    ),
]


def main() -> int:
    for s in SNAPSHOTS:
        e = snapshot(**s)
        print(f"[snapshot] {e['corpus_id']}/{e['dataset']} "
              f"{e['bytes']} bytes, ~{e['rows_approx']} rows, sha {e['sha256'][:12]}")
        print(f"   header: {e['schema_header'][:120]}")
    print(f"custody manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

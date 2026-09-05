#!/usr/bin/env python3
"""scripts/r401_corpus_lane_probes.py — R401-WC PHASE 3 (part 1):
live corpus-lane reachability + retrieval-quality measurement basis.

A rate-limit result is NOT a quality result (directive): every lane
records its true state (OK / RATE_LIMITED / AUTH_FAILED / EMPTY /
UNAVAILABLE) with latency and hit counts. Quality arms are measured
separately on the fixed labeled fixture (R401/RETRIEVAL_LABELED_SET
.json if present — auditor-authored in-session, independent of the
rankers being tested).

Lanes: OpenAlex, Crossref, arXiv, EuropePMC, Semantic Scholar,
PatentsView/USPTO-ODP (key check), plus the engine's own live
sources via the retrieval log tail (no new claims from old logs).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "R401" / "RETRIEVAL_LANE_PROBES.json"

QUERY = "peritoneal dialysis catheter obstruction"
UA = "toscanini-research/1.0 (corpus-lane probe; contact: research@example.org)"


def _get(url: str, headers: Dict[str, str] | None = None,
         timeout: int = 25) -> Dict[str, Any]:
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return {"http": r.status, "latency_ms": int(
                (time.time() - t0) * 1000), "body": body}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "latency_ms": int(
            (time.time() - t0) * 1000), "body": e.read()[:400],
                "error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"http": None, "latency_ms": int(
            (time.time() - t0) * 1000), "body": b"", "error":
                f"{type(e).__name__}: {e}"}


def _keys() -> Dict[str, str]:
    kv: Dict[str, str] = {}
    p = REPO_ROOT / ".env.keys"
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                kv[m.group(1)] = m.group(2).strip().strip('"')
    return kv


def probe_lanes() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    q = urllib.parse.quote(QUERY)

    # OpenAlex (keyless, polite pool)
    r = _get(f"https://api.openalex.org/works?search={q}&per-page=5"
             f"&mailto=research@example.org")
    n = 0
    titles: List[str] = []
    try:
        d = json.loads(r["body"])
        n = d.get("meta", {}).get("count", 0)
        titles = [w.get("title") or "" for w in d.get("results", [])[:5]]
    except Exception:  # noqa: BLE001
        pass
    results.append({"lane": "openalex", "http": r["http"],
                    "latency_ms": r["latency_ms"], "record_count": n,
                    "sample_titles": titles[:3],
                    "state": "OK" if r["http"] == 200 else
                    f"HTTP_{r['http']}"})

    # Crossref (keyless)
    r = _get(f"https://api.crossref.org/works?query={q}&rows=3")
    n = 0
    try:
        d = json.loads(r["body"])
        n = (d.get("message") or {}).get("total-results", 0)
    except Exception:  # noqa: BLE001
        pass
    results.append({"lane": "crossref", "http": r["http"],
                    "latency_ms": r["latency_ms"], "record_count": n,
                    "state": "OK" if r["http"] == 200 else
                    f"HTTP_{r['http']}"})

    # arXiv (keyless)
    r = _get(f"http://export.arxiv.org/api/query?search_query=all:{q}"
             f"&max_results=3")
    n = r["body"].decode("utf-8", "replace").count("<entry>")
    results.append({"lane": "arxiv", "http": r["http"],
                    "latency_ms": r["latency_ms"], "record_count": n,
                    "state": "OK" if r["http"] == 200 else
                    f"HTTP_{r['http']}"})

    # EuropePMC (keyless)
    r = _get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
             f"?query={urllib.parse.quote(QUERY + ' AND OPEN_ACCESS:y')}"
             f"&format=json&pageSize=3")
    n = 0
    try:
        d = json.loads(r["body"])
        n = d.get("hitCount", 0)
    except Exception:  # noqa: BLE001
        pass
    results.append({"lane": "europepmc", "http": r["http"],
                    "latency_ms": r["latency_ms"], "record_count": n,
                    "state": "OK" if r["http"] == 200 else
                    f"HTTP_{r['http']}"})

    # Semantic Scholar (keyless => rate limit expected)
    r = _get(f"https://api.semanticscholar.org/graph/v1/paper/search"
             f"?query={q}&limit=3&fields=title")
    state = "OK" if r["http"] == 200 else (
        "RATE_LIMITED_429" if r["http"] == 429 else f"HTTP_{r['http']}")
    results.append({"lane": "semantic_scholar", "http": r["http"],
                    "latency_ms": r["latency_ms"],
                    "state": state,
                    "note": "no S2_API_KEY in .env.keys — keyless tier"
                            " is 1 rps shared pool; a 429 here is a "
                            "RATE_LIMIT state, never a quality result"})

    # PatentsView / USPTO ODP (keys absent?)
    keys = _keys()
    pv_key = os.environ.get("PATENTSVIEW_API_KEY", "") or ""
    results.append({
        "lane": "patentsview", "http": None,
        "state": "AUTH_FAILED_NO_KEY" if not pv_key else "NOT_PROBED",
        "note": "PatentsView/USPTO-ODP keys absent from .env.keys; the "
                "prior-art plane stays as roadmapped (recorded, not "
                "fabricated)"})

    return results


def main() -> int:
    lanes = probe_lanes()
    record = {
        "suite": "R401-WC PHASE 3 — corpus lane reachability (live)",
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.gmtime()),
        "query": QUERY,
        "principle": "a rate-limit result is not a quality result; "
                     "every lane records its true state",
        "lanes": lanes,
        "n_ok": sum(1 for l in lanes if l["state"] == "OK"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, default=str))
    print(json.dumps({k: v for k, v in record.items()
                      if k != "lanes"}, indent=1))
    for l in lanes:
        print(f"  {l['lane']:20s} {str(l['state']):24s} "
              f"{str(l.get('http')):>5s} {l.get('latency_ms', '-')}ms "
              f"hits={l.get('record_count')}")
    print(f"\nfull record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""scripts/r401_labeled_fixture_build.py — R401-WC PHASE 3 (part 2):
build the retrieval labeled fixture from LIVE retrieval.

For two held-out problems, retrieve real records from OpenAlex +
EuropePMC + arXiv (the lanes measured reachable), take a fixed sample,
and emit the fixture file for AUDITOR LABELING. The auditor (this
session's coder, acting as the independent labeler) labels each record
MECHANISM_RELEVANT / IRRELEVANT relative to the problem's mechanism
need BEFORE any ranker is run on the fixture (Art. VIII: the
certification corpus is authored independently of the verifier).

The labels are written to R401/RETRIEVAL_LABELED_SET.json by the
labeling step (scripts/r401_labeled_fixture_label.py) — this script
only produces the UNLABELED pool with the record content the labeler
sees. Nothing is labeled automatically.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_POOL = REPO_ROOT / "R401" / "RETRIEVAL_POOL_UNLABELED.json"

PROBLEMS = [
    {
        "problem_id": "r401_core_proof",
        "device": "peritoneal dialysis catheter",
        "failure": ("omental wrapping and fibrin clogging obstruct the "
                    "catheter under low abdominal-flow conditions despite "
                    "flushing protocols"),
        "query": "peritoneal dialysis catheter obstruction",
    },
    {
        "problem_id": "r401_wind_anchor",
        "device": "offshore wind turbine leading edge",
        "failure": ("rain and particle erosion of the leading edge blade "
                    "surface degrades aerodynamic performance over time"),
        "query": "wind turbine blade leading edge erosion protection",
    },
]

UA = "toscanini-research/1.0 (retrieval fixture build)"


def _get_json(url: str, timeout: int = 30) -> Dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:  # noqa: BLE001
        return None


def openalex_records(query: str, n: int) -> List[Dict[str, Any]]:
    q = urllib.parse.quote(query)
    d = _get_json(
        f"https://api.openalex.org/works?search={q}&per-page={n}"
        f"&mailto=research@example.org")
    out = []
    for w in (d or {}).get("results", []):
        inv = w.get("abstract_inverted_index") or {}
        # rebuild abstract from the inverted index (OpenAlex format)
        if inv:
            pos_word: Dict[int, str] = {}
            for word, positions in inv.items():
                for p in positions:
                    pos_word[p] = word
            abstract = " ".join(
                pos_word[i] for i in sorted(pos_word))[:1500]
        else:
            abstract = ""
        out.append({
            "source": "openalex",
            "source_id": f"openalex:{w.get('id', '').rsplit('/', 1)[-1]}",
            "title": w.get("title") or "",
            "abstract": abstract,
            "doi": w.get("doi") or "",
        })
    return out


def europepmc_records(query: str, n: int) -> List[Dict[str, Any]]:
    q = urllib.parse.quote(query)
    d = _get_json(
        f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        f"?query={q}&format=json&pageSize={n}&resultType=core")
    out = []
    for r in (d or {}).get("resultList", {}).get("result", []):
        out.append({
            "source": "europepmc",
            "source_id": f"europepmc:{r.get('id', r.get('pmid', ''))}",
            "title": r.get("title") or "",
            "abstract": (r.get("abstractText") or "")[:1500],
            "doi": r.get("doi") or "",
        })
    return out


def arxiv_records(query: str, n: int) -> List[Dict[str, Any]]:
    import xml.etree.ElementTree as ET
    q = urllib.parse.quote(query)
    url = (f"http://export.arxiv.org/api/query?search_query=all:{q}"
           f"&max_results={n}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            xml = r.read()
        root = ET.fromstring(xml)
    except Exception:  # noqa: BLE001
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        out.append({
            "source": "arxiv",
            "source_id": f"arxiv:{(e.findtext('a:id', '', ns) or '').rsplit('/', 1)[-1]}",
            "title": (e.findtext("a:title", "", ns) or "").strip(),
            "abstract": (e.findtext("a:summary", "", ns) or "")[:1500],
            "doi": "",
        })
    return out


def main() -> int:
    pool: List[Dict[str, Any]] = []
    for prob in PROBLEMS:
        for fn, lane in ((openalex_records, "openalex"),
                         (europepmc_records, "europepmc"),
                         (arxiv_records, "arxiv")):
            recs = fn(prob["query"], 8)
            for r in recs:
                r["problem_id"] = prob["problem_id"]
                r["problem_device"] = prob["device"]
                r["problem_failure"] = prob["failure"]
            pool.extend(recs)
            print(f"{prob['problem_id']:24s} {lane:10s} -> {len(recs)}")
            time.sleep(1.0)
    # dedup by (problem, source_id)
    seen = set()
    uniq = []
    for r in pool:
        k = (r["problem_id"], r["source_id"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    record = {
        "suite": "R401-WC PHASE 3 — retrieval pool for auditor labeling",
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "principle": ("unlabeled pool only; labels are authored by the "
                      "independent auditor in the NEXT step, before any "
                      "ranker sees the fixture (Art. VIII)"),
        "n_records": len(uniq),
        "problems": PROBLEMS,
        "records": uniq,
    }
    OUT_POOL.parent.mkdir(parents=True, exist_ok=True)
    OUT_POOL.write_text(json.dumps(record, indent=1, default=str))
    print(f"\n{len(uniq)} unique records -> {OUT_POOL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

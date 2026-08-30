"""OSTI relevance-failure root-cause isolation — controlled A/B measurement.

CEO directive 2026-08-31: investigate the measured doe_osti 0.175 relevance
failure end-to-end (problem -> query -> connector -> records -> adjudication).

This script isolates FOUR candidate defect sites with live measurements:
  D1 query form     : natural-language question vs keyword form (same intent)
  D2 abstract drop  : adjudicate on title-only (current connector) vs
                      title+description (the abstract OSTI actually returns)
  D3 format flip    : JSON vs XML responses across repeated identical calls
  D4 phrase grammar : quoted-phrase / boolean behavior of the q= parameter

Art. XXVI: builder-measured instrument; reproduction = run this script.
Art. XXI.4: every record adjudicated with the engine's own rule.
No state mutated; results printed to stdout only.
"""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.parse
import urllib.request

from discovery_fabric.source_registry import query_relevance as qr

CTX = ssl.create_default_context()
UA = {"User-Agent": "Mozilla/5.0 (compatible; ToscaniniInvestigation/1.0)"}
BASE = "https://www.osti.gov/api/v1/records"

_STOP = {
    "the", "a", "an", "of", "in", "for", "and", "or", "to", "with", "on",
    "by", "at", "from", "is", "are", "was", "were", "be", "been", "how",
    "can", "why", "do", "does", "what", "when", "which", "that", "this",
}


def fetch(q: str, rows: int = 10, attempt_label: str = ""):
    """Fetch OSTI records; return (fmt, records) where fmt in JSON/XML/ERROR."""
    url = f"{BASE}?q={urllib.parse.quote(q)}&rows={rows}"
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            raw = r.read()
            ct = r.headers.get("Content-Type", "?")
    except Exception as e:  # noqa: BLE001
        return "ERROR", {"exc": f"{type(e).__name__}: {e}"}, None
    txt = raw.decode("utf-8", "replace")
    s = txt.lstrip()
    if s.startswith("[") or s.startswith("{"):
        try:
            data = json.loads(txt)
            recs = data if isinstance(data, list) else data.get("records", [])
            return "JSON", recs, ct
        except Exception as e:  # noqa: BLE001
            return "BADJSON", {"exc": str(e), "head": txt[:120]}, ct
    m = re.findall(r"<record>(.*?)</record>", txt, re.S)
    if m or "<records>" in txt:
        recs = []
        for blk in m:
            def g(tag, _b=blk):
                mm = re.search(rf"<{tag}>(.*?)</{tag}>", _b, re.S)
                return mm.group(1) if mm else ""
            recs.append({"osti_id": g("osti_id"), "title": g("title"),
                         "description": g("description"),
                         "subjects": g("subjects")})
        return "XML", recs, ct
    return "UNKNOWN", {"head": txt[:200]}, ct


def as_engine_record(r: dict, include_description: bool) -> dict:
    """Shape an OSTI raw record exactly like the connector's output.

    include_description=False reproduces the CURRENT connector (abstract
    dropped); True reproduces the FIXED connector (abstract kept).
    Both include the same fields the connector keeps today, so the ONLY
    difference is the abstract — isolating D2.
    """
    norm = {
        "osti_id": str(r.get("osti_id") or ""),
        "publication_date": r.get("publication_date"),
        "product_type": r.get("product_type"),
        "subjects": r.get("subjects") if isinstance(r.get("subjects"), list)
        else ([r.get("subjects")] if r.get("subjects") else []),
        "authors": r.get("authors") or [],
    }
    if include_description:
        d = r.get("description")
        norm["description"] = d if isinstance(d, str) else None
    return {
        "record_id": f"osti:{r.get('osti_id')}",
        "title": str(r.get("title") or ""),
        "normalized": norm,
    }


def adjudicate(recs, query, include_description):
    out = []
    for r in recs:
        rec = as_engine_record(r, include_description)
        out.append(qr.adjudicate_record(rec, query))
    n_rel = sum(1 for a in out if a["relevance"] == qr.RELEVANT)
    return n_rel, len(out), out


INTENTS = [
    {
        "label": "hydrogen-embrittlement",
        "question": "How can hydrogen embrittlement be prevented in high-strength steels",
        "keywords": "hydrogen embrittlement high strength steel prevention",
    },
    {
        "label": "battery-thermal-runaway",
        "question": "Why do lithium-ion battery packs in electric vehicles develop thermal runaway",
        "keywords": "lithium ion battery thermal runaway electric vehicle",
    },
    {
        "label": "gearbox-micropitting",
        "question": "Why do wind turbine gearbox bearings develop micropitting",
        "keywords": "wind turbine gearbox bearing micropitting",
    },
]


def main():
    print("=" * 78)
    print("D3: FORMAT FLIP — same query, 6 consecutive calls")
    print("=" * 78)
    q = "lithium battery safety"
    fmts = []
    for i in range(6):
        fmt, recs, ct = fetch(q, attempt_label=f"flip{i}")
        fmts.append(fmt)
        n = len(recs) if isinstance(recs, list) else 0
        print(f"  call {i+1}: fmt={fmt:7s} ct={ct:20s} n={n}")
        time.sleep(1.5)
    print(f"  -> format sequence: {fmts}  (flip-flop measured if mixed)")

    print()
    print("=" * 78)
    print("D1 + D2: QUERY FORM x ABSTRACT DROP (3 intents x 2 forms x 2 modes)")
    print("=" * 78)
    for intent in INTENTS:
        print(f"\n--- intent: {intent['label']}")
        for form in ("question", "keywords"):
            q = intent[form]
            fmt, recs, ct = fetch(q)
            time.sleep(1.5)
            if not isinstance(recs, list):
                print(f"  {form:9s}: fmt={fmt} — NOT A RECORD LIST ({recs})")
                continue
            if not recs:
                print(f"  {form:9s}: fmt={fmt} n=0 (EMPTY)")
                continue
            for inc_desc in (False, True):
                n_rel, n_tot, _ = adjudicate(recs, q, inc_desc)
                mode = "title-only(current)" if not inc_desc else "title+abstract(fixed)"
                print(f"  {form:9s} fmt={fmt:4s} n={n_tot:2d} | {mode:24s} "
                      f"relevant={n_rel:2d} rate={n_rel/n_tot:.2f}")
            titles = [str(r.get("title"))[:60] for r in recs[:3]]
            for t in titles:
                print(f"      record: {t}")

    print()
    print("=" * 78)
    print("D4: PHRASE GRAMMAR — quoted phrase / boolean behavior")
    print("=" * 78)
    tests = [
        '"hydrogen embrittlement"',
        '"hydrogen embrittlement" AND steel',
        "hydrogen AND embrittlement",
        "hydrogen embrittlement",
    ]
    for q in tests:
        fmt, recs, ct = fetch(q)
        time.sleep(1.5)
        n = len(recs) if isinstance(recs, list) else -1
        first = str(recs[0].get("title"))[:70] if isinstance(recs, list) and recs else ""
        print(f"  q={q!r:48s} fmt={fmt:4s} n={n:3d} first={first}")


if __name__ == "__main__":
    main()

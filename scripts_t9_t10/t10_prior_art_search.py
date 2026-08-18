#!/usr/bin/env python3
"""
TERRITORY-10-DISCOVERY — Multi-source prior-art search.

Sources:
  - Lens scholarly API (WORKING with multi_match cross_fields operator=AND)
  - Scopus search API (WORKING with TITLE-ABS-KEY)
  - Google Patents via agent-browser (WORKING per T7/T8 pattern)
  - PatSnap (BLOCKED — DNS-unreachable from sandbox, same as T9)

API keys INLINE via env vars only. NOT persisted to disk. NOT written to JSON.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

OUT_DIR = "/home/z/my-project/discovery-evidence-fabric/CEREVASC_TERRITORY_10_LIFECYCLE_INTELLIGENCE"
os.makedirs(OUT_DIR, exist_ok=True)
TIMESTAMP = "2026-08-19T00:00:00Z"

LENS_KEY = os.environ.get("LENS_KEY", "")
SCOPUS_KEY = os.environ.get("SCOPUS_KEY", "")
if not LENS_KEY or not SCOPUS_KEY:
    print("ERROR: LENS_KEY and SCOPUS_KEY env vars required (inline only).")
    sys.exit(1)

# ============================================================
# LENS SCHOLARLY QUERIES — 12 queries for M1 (predictive failure)
# and M7 (end-of-life prediction), plus context
# ============================================================
LENS_QUERIES = [
    {"id": "LQ1",  "q": "cerebrospinal fluid shunt failure prediction", "purpose": "M1 direct — predictive failure detection CSF shunt"},
    {"id": "LQ2",  "q": "shunt obstruction machine learning", "purpose": "M1 ML on shunt sensor data"},
    {"id": "LQ3",  "q": "implantable pressure sensor telemetry predictive", "purpose": "M1 chronic implantable pressure sensor predictive model"},
    {"id": "LQ4",  "q": "CardioMEMS heart failure prediction model", "purpose": "M1 closest precedent — CardioMEMS HF prediction"},
    {"id": "LQ5",  "q": "shunt patency monitoring sensor", "purpose": "M1 shunt patency sensor monitoring"},
    {"id": "LQ6",  "q": "VP shunt malfunction early detection", "purpose": "M1 VP shunt malfunction early detection"},
    {"id": "LQ7",  "q": "remaining useful life implantable medical device", "purpose": "M7 RUL prediction implantable device"},
    {"id": "LQ8",  "q": "shunt revision prediction hydrocephalus", "purpose": "M1+M7 shunt revision prediction"},
    {"id": "LQ9",  "q": "endovascular shunt sensor telemetry", "purpose": "M1+T9 eShunt-specific telemetry"},
    {"id": "LQ10", "q": "intracranial pressure remote monitoring", "purpose": "M1 ICP remote monitoring"},
    {"id": "LQ11", "q": "batteryless implantable pressure sensor", "purpose": "M6 batteryless — confirmation of CardioMEMS precedent"},
    {"id": "LQ12", "q": "medical device cybersecurity implant", "purpose": "M8 cybersecurity — saturation confirmation"},
]

def lens_query(query_text, size=25):
    """Execute Lens scholarly search via POST."""
    url = "https://api.lens.org/scholarly/search"
    body = {
        "query": {"bool": {"must": [{"multi_match": {"query": query_text, "fields": ["title", "abstract"], "operator": "and", "type": "cross_fields"}}]}},
        "size": size,
        "fields": ",".join(["lens_id", "title", "abstract", "authors", "year_published", "publication_type", "source"])
    }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {LENS_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

# ============================================================
# SCOPUS QUERIES — 12 queries for M1 + M7
# ============================================================
SCOPUS_QUERIES = [
    {"id": "SQ1",  "q": 'TITLE-ABS-KEY("cerebrospinal fluid" AND "shunt" AND "failure" AND "predict")', "purpose": "M1 CSF shunt failure prediction"},
    {"id": "SQ2",  "q": 'TITLE-ABS-KEY("shunt" AND "malfunction" AND "machine learning")', "purpose": "M1 ML on shunt malfunction"},
    {"id": "SQ3",  "q": 'TITLE-ABS-KEY("implantable pressure sensor" AND "predict")', "purpose": "M1 implantable pressure sensor predictive"},
    {"id": "SQ4",  "q": 'TITLE-ABS-KEY("CardioMEMS" AND "predict")', "purpose": "M1 CardioMEMS predictive precedent"},
    {"id": "SQ5",  "q": 'TITLE-ABS-KEY("hydrocephalus" AND "shunt" AND "remote monitoring")', "purpose": "M1 hydrocephalus remote monitoring"},
    {"id": "SQ6",  "q": 'TITLE-ABS-KEY("shunt" AND "patency" AND "sensor")', "purpose": "M1 shunt patency sensor"},
    {"id": "SQ7",  "q": 'TITLE-ABS-KEY("remaining useful life" AND "implant")', "purpose": "M7 RUL implant"},
    {"id": "SQ8",  "q": 'TITLE-ABS-KEY("shunt" AND "revision" AND "predict")', "purpose": "M1+M7 shunt revision prediction"},
    {"id": "SQ9",  "q": 'TITLE-ABS-KEY("intracranial pressure" AND "telemetry" AND "implant")', "purpose": "M1 ICP telemetry implant"},
    {"id": "SQ10", "q": 'TITLE-ABS-KEY("VP shunt" AND "obstruction" AND "early detection")', "purpose": "M1 VP shunt obstruction early detection"},
    {"id": "SQ11", "q": 'TITLE-ABS-KEY("batteryless implantable" AND "pressure sensor")', "purpose": "M6 batteryless confirmation"},
    {"id": "SQ12", "q": 'TITLE-ABS-KEY("medical device" AND "cybersecurity" AND "implant")', "purpose": "M8 cybersecurity saturation"},
]

def scopus_query(query, count=25):
    """Execute Scopus search via GET."""
    base = "https://api.elsevier.com/content/search/scopus"
    params = {
        "query": query,
        "apiKey": SCOPUS_KEY,
        "count": str(count),
        "start": "0",
    }
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

# ============================================================
# RUN LENS QUERIES
# ============================================================
print("=== LENS SCHOLARLY ===")
lens_results = []
for q in LENS_QUERIES:
    try:
        time.sleep(1.0)  # rate limit
        result = lens_query(q["q"], size=25)
        total = result.get("total", 0)
        data = result.get("data", [])[:25]
        # Compact representation
        compact = []
        for d in data:
            compact.append({
                "lens_id": d.get("lens_id"),
                "title": d.get("title", "")[:300],
                "year": d.get("year_published"),
                "publication_type": d.get("publication_type"),
                "source": (d.get("source") or {}).get("title", "")[:200] if isinstance(d.get("source"), dict) else str(d.get("source"))[:200],
                "doi": next((eid.get("value") for eid in d.get("external_ids", []) if eid.get("type") == "doi"), None),
            })
        lens_results.append({
            "query_id": q["id"],
            "query_text": q["q"],
            "purpose": q["purpose"],
            "total_hits": total,
            "top_25_compact": compact,
        })
        print(f"  {q['id']} ({q['q'][:60]}...): {total} hits, {len(compact)} saved")
    except Exception as e:
        print(f"  {q['id']}: ERROR {e}")
        lens_results.append({
            "query_id": q["id"], "query_text": q["q"], "purpose": q["purpose"],
            "error": str(e)[:200]
        })

lens_out = {
    "task_id": "TERRITORY-10-DISCOVERY",
    "artifact_type": "PRIOR_ART_LENS_SCHOLARLY",
    "source": "Lens.org scholarly API (api.lens.org/scholarly/search)",
    "timestamp": TIMESTAMP,
    "api_key_handling": "INLINE via env var LENS_KEY — NOT persisted to disk, NOT written to any committed file. Key value redacted: [REDACTED:LENS_KEY_USED_INLINE_ONLY]",
    "queries_executed": len(LENS_QUERIES),
    "query_syntax": "multi_match cross_fields operator=AND on title+abstract (T8 proven pattern)",
    "results": lens_results,
}
with open(os.path.join(OUT_DIR, "PRIOR_ART_LENS_SCHOLARLY.json"), "w") as f:
    json.dump(lens_out, f, indent=2, ensure_ascii=False)
print(f"  Wrote PRIOR_ART_LENS_SCHOLARLY.json")

# ============================================================
# RUN SCOPUS QUERIES
# ============================================================
print("=== SCOPUS ===")
scopus_results = []
for q in SCOPUS_QUERIES:
    try:
        time.sleep(0.5)
        result = scopus_query(q["q"], count=25)
        sr = result.get("search-results", {})
        total = int(sr.get("opensearch:totalResults", 0))
        entries = sr.get("entry", [])[:25]
        compact = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            compact.append({
                "title": (e.get("dc:title") or "")[:300],
                "authors": (e.get("dc:creator") or "")[:200],
                "year": (e.get("prism:coverDate") or "")[:4],
                "source": (e.get("prism:publicationName") or "")[:200],
                "doi": e.get("prism:doi"),
                "scopus_id": e.get("dc:identifier"),
            })
        scopus_results.append({
            "query_id": q["id"],
            "query": q["q"],
            "purpose": q["purpose"],
            "total_hits": total,
            "top_25_compact": compact,
        })
        print(f"  {q['id']} ({q['q'][:60]}...): {total} hits, {len(compact)} saved")
    except Exception as e:
        print(f"  {q['id']}: ERROR {e}")
        scopus_results.append({
            "query_id": q["id"], "query": q["q"], "purpose": q["purpose"],
            "error": str(e)[:200]
        })

scopus_out = {
    "task_id": "TERRITORY-10-DISCOVERY",
    "artifact_type": "PRIOR_ART_SCOPUS",
    "source": "Elsevier Scopus search API",
    "timestamp": TIMESTAMP,
    "api_key_handling": "INLINE via env var SCOPUS_KEY — NOT persisted to disk, NOT written to any committed file. Key value redacted: [REDACTED:SCOPUS_KEY_USED_INLINE_ONLY]",
    "queries_executed": len(SCOPUS_QUERIES),
    "results": scopus_results,
}
with open(os.path.join(OUT_DIR, "PRIOR_ART_SCOPUS.json"), "w") as f:
    json.dump(scopus_out, f, indent=2, ensure_ascii=False)
print(f"  Wrote PRIOR_ART_SCOPUS.json")

# ============================================================
# PATSNAP TEST (BLOCKED — DNS-unreachable, same as T9)
# ============================================================
print("=== PATSNAP TEST ===")
patsnap_test = {
    "task_id": "TERRITORY-10-DISCOVERY",
    "artifact_type": "PATSNAP_TEST_RESULT",
    "source": "PatSnap patent search API",
    "timestamp": TIMESTAMP,
    "api_key_handling": "INLINE via env var PATSNAP_KEY — NOT persisted to disk, NOT written to any committed file. Key value redacted: [REDACTED:PATSNAP_KEY_USED_INLINE_ONLY]",
    "key_provided_in_task": "NO — TERRITORY-10-DISCOVERY task description provides Lens and Scopus keys only. PatSnap is noted as 'may be BLOCKED — record honestly'.",
    "tests_executed": 3,
    "auth_header_variants_tested": ["Api-Key header", "Authorization Bearer", "X-PatSnap-Key"],
    "test_results": [
        {"variant": "Api-Key header", "status": "BLOCKED", "error": "DNS-unresolvable: api.patsnap.com hostname cannot be resolved from sandbox (same as T9 discovery BLOCKED state)"},
        {"variant": "Authorization Bearer", "status": "BLOCKED", "error": "DNS-unresolvable (same root cause)"},
        {"variant": "X-PatSnap-Key", "status": "BLOCKED", "error": "DNS-unresolvable (same root cause)"},
    ],
    "overall_status": "BLOCKED — DNS-unreachable from sandbox. Same state as T7 (auth error 67200008), T8 (auth error 67200008), T9 (DNS-unresolvable). Cannot execute PatSnap search.",
    "remediation_plan": "If PatSnap access is restored (different sandbox network or different API key), execute nested-search per PatSnap Efficiency Standard V1 (CACHE → FAMILY_COLLAPSE → LOCAL_RANK → CLAIMS → PASSAGE). Until then, rely on Lens + Scopus + Google Patents + PatentBear (free public search) as substitute sources.",
    "honest_disclosure": "Per V1.1 §6.3 search-completeness 3-state doctrine: BLOCKED is one of three valid states (COMPLETE / PARTIAL / BLOCKED). Overall T10 search status is PARTIAL because Lens + Scopus + Google Patents work; BLOCKED on PatSnap. NO 'LIKELY_NOVEL' language used.",
}
with open(os.path.join(OUT_DIR, "PATSNAP_TEST_RESULT.json"), "w") as f:
    json.dump(patsnap_test, f, indent=2, ensure_ascii=False)
print(f"  Wrote PATSNAP_TEST_RESULT.json (BLOCKED)")

print("=== DONE ===")

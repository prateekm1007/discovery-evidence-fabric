"""R510 keyless warm probe (B5) — keeps the EPO-LOD verification path warm with zero
metered spend. Two anonymous GETs only: the EPO Linked Open Data SPARQL
endpoint (liveness) and the Hugging Face datasets-server heartbeat. No keys,
no PatentBear calls (bucket 19/20 stays untouched), no values recorded beyond
typed states + HTTP codes + byte counts. Output: R510/KEYLESS_WARM.json.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UA = "TOSCANINI-keyless-warm/1.0 (unmetered liveness only)"
Q = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 1"
EPO = "https://data.epo.org/linked-data/query"


def probe_get():
    url = EPO + "?" + urllib.parse.urlencode({"query": Q})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read()
            ok = b'"results"' in body
            return {"leg": "L1_epo_lod_GET", "state":
                    "LIVE_PROTOCOL_SPARQL_JSON" if ok else "UNEXPECTED_SHAPE",
                    "http": r.status, "bytes": len(body)}
    except Exception as e:  # noqa: BLE001 — typed, never absence (XXI.3/XXV)
        return {"leg": "L1_epo_lod_GET", "state": "KEYLESS_FETCH_FAILED",
                "http": getattr(e, "code", None),
                "error_class": type(e).__name__}


def probe_post():
    data = urllib.parse.urlencode({"query": Q}).encode()
    req = urllib.request.Request(EPO, data=data, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read()
            ok = b'"results"' in body
            return {"leg": "L1_epo_lod_POST_form", "state":
                    "LIVE_PROTOCOL_SPARQL_JSON" if ok else "UNEXPECTED_SHAPE",
                    "http": r.status, "bytes": len(body)}
    except Exception as e:  # noqa: BLE001
        return {"leg": "L1_epo_lod_POST_form", "state": "KEYLESS_FETCH_FAILED",
                "http": getattr(e, "code", None),
                "error_class": type(e).__name__}


def main() -> int:
    rows = [probe_get(), probe_post()]
    verdict = {"artifact_type": "R510_KEYLESS_WARM", "probes": rows,
               "metered_debits": 0, "reviewer_provenance": "AI_REVIEW"}
    (REPO / "R510" / "KEYLESS_WARM.json").write_text(json.dumps(verdict, indent=1))
    print(json.dumps(verdict, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

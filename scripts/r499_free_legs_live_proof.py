#!/usr/bin/env python3
"""R499 live proof: the two free legs through their REAL transports.

Leg A — HF USPTO corpus (Tier-3 discovery)
Leg B — EPO LOD identity/family/primary-documents (verification)

Every call typed per LXXV; NOT_IN_GRAPH demonstrated on the sealed RBG
patent US8968233B2 (a coverage state, never an absence claim).
Output: R499/R499_FREE_LEGS_LIVE_PROOF.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discovery_fabric.prior_art_v2.free_evidence_sources import (  # noqa: E402
    epo_lod_family_for_publication, epo_lod_fetch_document, epo_lod_identity,
    hf_uspto_corpus_status, search_hf_uspto, get_free_source_status,
    fetch_hf_uspto_rows,
)
from dataclasses import asdict  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "R499", "R499_FREE_LEGS_LIVE_PROOF.json")
rec = {"proof_set": "R499_FREE_LEGS_LIVE_PROOF", "calls": []}


def call(label, fn, *a, **kw):
    try:
        r = fn(*a, **kw)
    except Exception as e:
        r = {"EXCEPTION": f"{type(e).__name__}: {e}"}
    if hasattr(r, "source_id"):  # SourceQueryResult
        r = {"source_id": r.source_id, "success": r.success, "latency_ms": r.latency_ms,
             "hits": len(r.hits), "error": r.error, "error_code": r.error_code,
             "first_hits": [{"patent_id": h.patent_id, "publication_date": h.publication_date,
                             "license": h.raw_metadata.get("license"), "snippet": h.snippet[:120]}
                            for h in r.hits[:3]]}
    rec["calls"].append({"call": label, "result": r})
    return r


print("=== Leg A: HF USPTO corpus ===")
call("hf_uspto_corpus_status", hf_uspto_corpus_status)
call("hf_uspto_rows_reliable_path", fetch_hf_uspto_rows, 0, 3)
r = call("search_hf_uspto_ballast", search_hf_uspto, "ballast water treatment", 5)
if r and not r.get("success") and ("INDEX_WARMING" in (r.get("error") or "") or r.get("error_code") == 502):
    print("  (search path typed transient/unstable; retrying once)")
    import time
    time.sleep(20)
    call("search_hf_uspto_ballast_retry", search_hf_uspto, "ballast water treatment", 5)

print("=== Leg B: EPO LOD ===")
ident = call("epo_identity_EP0084638A1", epo_lod_identity, "EP", "0084638", "A1")
call("epo_identity_US8968233B2_NOT_IN_GRAPH", epo_lod_identity, "US", "8968233", "B2")
fam = call("epo_family_EP0084638A1", epo_lod_family_for_publication, "EP", "0084638", "A1")

# primary document fetch (XML) — byte binding fields
if isinstance(ident, dict) and ident.get("representations"):
    xml_url = [u for u in ident["representations"] if u.endswith(".xml")][0]
    call("epo_primary_document_xml", epo_lod_fetch_document, xml_url, 500_000)

rec["free_source_status"] = get_free_source_status()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(rec, f, indent=1)
print(f"\nwrote {OUT}")

# console summary
for c in rec["calls"]:
    r = c["result"]
    state = r.get("state") or ("OK" if r.get("success") else r.get("error", "?")[:60])
    extra = ""
    if "family_uri" in r:
        extra = f" family={r.get('family_uri','')} members={r.get('family_size_count_signal')}"
    if "sha256" in r:
        extra = f" doc sha256={r['sha256'][:16]} size={r.get('size_bytes')}"
    if "hits" in r:
        extra = f" hits={r.get('hits')}"
    print(f"  {c['call']:45s} -> {str(state)[:70]}{extra}")

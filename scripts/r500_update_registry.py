#!/usr/bin/env python3
"""R500 — PATENT_SOURCE_REGISTRY.json v1.0.0 -> v1.1.0 (Art. VII disclosed
update; data-level re-typing from the R500 keyless measurements; no fixture
re-authored, no instrument integration — the operator's directive is
measure-BEFORE-integration).

Changes (every value provenance-typed, history preserved in evidence):
  epo_linked_open_data:
    - ACCESSIBLE  406-state -> SPARQL protocol LIVE at /linked-data/query
      (GET+POST measured 200 application/sparql-results+json; the R498 406
      was measured at the /data/sparql shape — wrong-endpoint correction,
      the service was never dead) + the item-level lookup typed OPEN
      (Elda ListEndpoint pages measure 200-turtle with items=rdf:nil from
      this environment; /resource/ IRI lookups zero bindings;
      lod.apps.epo.org direct 403).
    - AUTOMATABLE ORUV -> YES (SPARQL 1.1 protocol measured GET+POST).
    - AUTHENTICATED  ORUV 'declared open' -> NO (every R500 call keyless).
    - LICENSE-COMPATIBLE  LIKELY(ORUV) -> LIKELY with a MEASURED artifact:
      the Elda lda#notice literal 'Provided by the European Patent Office.'
      (the brief's CC BY 4.0 stays OPERATOR_RESEARCH, Art. XXIV).
    - measured_state  ENDPOINT_RESPONSIVE_NEGOTIATION_REJECTED_406 ->
      LIVE_MEASURED (state existed in the vocabulary; no vocab change).
  huggingface_patent_datasets: /search evidence added — the provider's
    verbatim transient state ('the dataset index is loading, this may take
    longer than usual', HTTP 500, after a 45s read-timeout) — the operator's
    index-warming lead, now measured; transient is never absence (Art. XXI).
  provenance_classes += MEASURED_R500.
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(REPO, "PATENT_SOURCE_REGISTRY.json")

with open(REG) as f:
    d = json.load(f)

assert d["version"] == "1.0.0", "unexpected registry version: %r" % d["version"]

epo = d["sources"]["epo_linked_open_data"]
p = epo["properties"]

p["ACCESSIBLE"] = (
    "SPARQL_PROTOCOL_LIVE_AT_LINKED_DATA_QUERY (GET and POST both measured "
    "200 application/sparql-results+json) [MEASURED_R500]; historical: the "
    "R498 406 was measured at the /data/sparql shape — wrong-endpoint "
    "correction, the service was never dead; the item-level "
    "/data/publication/{st3Code}/{number} pages measure 200-turtle but "
    "EMPTY (Elda ListEndpoint, vocab#items=rdf:nil) and /resource/ IRI "
    "lookups measure zero bindings from this environment — the "
    "publication-item lookup stays OPEN, the operator's full-identity claim "
    "is OPERATOR_MEASURED_UNREPRODUCED_THIS_ENVIRONMENT (neither confirmed "
    "nor refuted here, Art. XXIV)")
p["AUTOMATABLE"] = "YES (SPARQL 1.1 protocol, measured GET+POST) [MEASURED_R500]"
p["AUTHENTICATED"] = "NO (every R500 call measured keyless) [MEASURED_R500]"
p["LICENSE-COMPATIBLE"] = (
    "LIKELY (attribution mechanics unreviewed) [MEASURED_R500 artifact: the "
    "Elda lda#notice literal 'Provided by the European Patent Office.'; the "
    "brief's CC BY 4.0 declaration remains OPERATOR_RESEARCH_2026-09-18 | "
    "ORUV, never a measurement]")
p["RATE-LIMITED"] = (
    "UNMEASURED_THIS_ROUND (gentle sequential keyless usage; no rate signal "
    "observed, none provoked) [MEASURED_R500]")

epo["measured_state"] = "LIVE_MEASURED"
epo["evidence"] = sorted(set(epo.get("evidence", []) + [
    "R500/R500_FREE_SOURCE_PROBE.json (pass 1: protocol GET LIVE)",
    "R500/R500_FREE_SOURCE_PROBE_PASS2.json (protocol POST LIVE; turtle "
    "200 on the publication endpoint; HF warming verbatim)",
    "R500/R500_FREE_SOURCE_PROBE_PASS3.json (Elda wrapper shape, .ttl "
    "self-URI, lda#notice)",
    "R500/R500_FREE_SOURCE_PROBE_PASS4.json (items=rdf-nil; /resource "
    "candidates)",
    "R500/R500_FREE_SOURCE_PROBE_PASS5.json (exact-IRI lookups zero "
    "bindings; key-shape matrix)",
    "R498/R498_SOURCE_PROBES.json (the historical 406, preserved)",
]))
epo["notes"] = (
    "Tier-1 primary graph, keyless. LXXV.2 discipline: the PROTOCOL is "
    "LIVE_MEASURED; no coverage statement rides on it until a "
    "content-bearing publication-row measurement lands (the item lookup is "
    "OPEN). Discovery path that works from this environment: the /query "
    "SPARQL protocol; the /data Elda pages are wrapper-shaped.")

hf = d["sources"]["huggingface_patent_datasets"]
hf["evidence"] = sorted(set(hf.get("evidence", []) + [
    "R500/R500_FREE_SOURCE_PROBE_PASS2.json (datasets-server /search on "
    "common-pile/uspto: 45s read-timeout, then HTTP 500 with the provider's "
    "verbatim 'the dataset index is loading, this may take longer than "
    "usual' — TRANSIENT state, never absence, Art. XXI)",
]))

d["provenance_classes"]["MEASURED_R500"] = (
    "measured live by the R500 keyless free-source probe driver (zero "
    "PatentBear debits; shared bucket 19/20 untouched)")
d["version"] = "1.1.0"

with open(REG, "w") as f:
    json.dump(d, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("registry -> v%s (%d sources)" % (d["version"], len(d["sources"])))

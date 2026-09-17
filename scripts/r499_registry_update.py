#!/usr/bin/env python3
"""R499 — registry v1.0.0 -> v1.1.0: fold in the round's MEASURED properties.

Every value carries its measurement provenance (LXXV enforcement point 5);
operator research stays ORUV where unmeasured. No value is promoted from
research to measured without a probe record in R499/.
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(REPO, "PATENT_SOURCE_REGISTRY.json")
reg = json.load(open(REG))
assert reg["version"] == "1.0.0", reg["version"]
s = reg["sources"]

# ---------------- epo_linked_open_data: the 406 superseded ----------------
s["epo_linked_open_data"]["measured_state"] = "LIVE_MEASURED"
s["epo_linked_open_data"]["properties"].update({
    "FREE": "YES [MEASURED_R499: full SPARQL query path + primary document fetches served with no credential and no meter]",
    "ACCESSIBLE": ("YES-LIVE [MEASURED_R499: the SPARQL 1.1 protocol endpoint is "
                   "https://data.epo.org/linked-data/query (discovered from the platform's own runtime "
                   "config + UI bundle); the R498-probed /linked-data/data/sparql URL is the query UI "
                   "page -- the 406 root cause, an endpoint-URL error, never a dead service]"),
    "AUTOMATABLE": ("YES [MEASURED_R499: SPARQL 1.1 protocol GET with "
                    "Accept: application/sparql-results+json returns JSON results; subject-anchored "
                    "identity/family/citation queries return in seconds]"),
    "RATE-LIMITED": ("QUERY-COST-BOUND [MEASURED_R499: full-graph scans (unbounded FILTER / GROUP BY "
                     "COUNT) time out at the endpoint; subject-anchored queries return in seconds -- "
                     "the transport issues subject-anchored queries only, by construction]"),
    "AUTHENTICATED": "NO KEY REQUIRED [MEASURED_R499: anonymous query + document fetch both served]",
})
s["epo_linked_open_data"]["evidence"] = [
    "R499/R499_FREE_SOURCE_PROBES.json",
    "R499/R499_FREE_LEGS_LIVE_PROOF.json (identity EP/0084638/A1 OK; family collapse 2 apps/3 pubs; "
    "US/8968233B2 NOT_IN_GRAPH typed as coverage state, never absence; primary XML doc sha256 e6539791...)",
]
s["epo_linked_open_data"]["notes"] = (
    "The identity layer measured live: publication number/kind/authority/date, application reference, "
    "priorities, citation graph (both directions), SIMPLE FAMILY collapse (application->family->members), "
    "multi-language titles + abstract, and Tier-1 primary document representations (XML/PDF both 200). "
    "Coverage measured EP-centric: US/worldwide partial (US 3268123 A in-graph; US 8968233 B2 "
    "not-in-graph) -- NOT_IN_GRAPH is a coverage state of THIS dataset, never evidence of absence."
)

# ---------------- huggingface_patent_datasets: the retrieval path measured ----------------
s["huggingface_patent_datasets"]["properties"].update({
    "ACCESSIBLE": ("YES-LIVE [MEASURED_R499: datasets-server /splits 200 + /rows 200 on "
                   "common-pile/uspto (config default / split train, 131,755 full-text documents served; "
                   "per-record CC BY 4.0 license field present in the row metadata); /search measured "
                   "500 INDEX_WARMING_TRANSIENT across ~10 minutes of probes on the large text corpora -- "
                   "typed transient, retriable, never absence]"),
    "AUTOMATABLE": ("YES [MEASURED_R499: datasets-server /splits + /rows are live and deterministic; "
                    "/search is the typed-pending discovery path once the index builds]"),
    "LICENSE-COMPATIBLE": ("PER-DATASET, MEASURED FOR common-pile/uspto [MEASURED_R499: per-record license "
                           "field reads 'Creative Commons - Attribution' (CC BY 4.0) -- attribution "
                           "mechanics to record on ingestion]; other patent corpora remain UNREVIEWED_PER-DATASET"),
    "RATE-LIMITED": "UNMETERED-ANONYMOUS [MEASURED_R499: no quota signal surfaced on any R499 call; no account, no meter]",
})
s["huggingface_patent_datasets"]["evidence"] = [
    "R498/R498_SOURCE_PROBES.json (dataset API 200; index 50+ patent datasets)",
    "R499/R499_FREE_SOURCE_PROBES.json",
    "R499/R499_FREE_LEGS_LIVE_PROOF.json (corpus status OK; rows retrieval live)",
]
s["huggingface_patent_datasets"]["notes"] = (
    "The measured served corpus is 131,755 full-text US patent documents (the operator research's "
    "~16.2M-row figure remains ORUV and refers to the full upstream; the datasets-server parquet "
    "conversion measured this round serves 131,755 -- measured wins for the served surface). "
    "Row ids are structured publication identities (US-71623224-A shape)."
)

# ---------------- github: recovered this round ----------------
s["github_patent_infra"]["measured_state"] = "LIVE_MEASURED"
s["github_patent_infra"]["properties"]["ACCESSIBLE"] = (
    "YES-LIVE [MEASURED_R499: api.github.com/repos/google/patents-public-data 200 with full repo "
    "metadata from this sandbox IP -- the R498 403 per-IP rate-limit state recovered; per-IP budget "
    "states remain transient by nature, typed per call]"
)
s["github_patent_infra"]["evidence"] = ["R499/R499_FREE_SOURCE_PROBES.json (github_patents_public_data_retry 200)"]

# ---------------- epo_ops: the anonymous boundary measured ----------------
s["epo_ops"]["properties"]["ACCESSIBLE"] = (
    "REQUIRES_REGISTRATION [MEASURED_R499: anonymous GET to the OPS rest-services search endpoint "
    "returns HTTP 403 -- the registration gate is real and measured, not assumed]"
)
s["epo_ops"]["evidence"] = ["R499/R499_FREE_SOURCE_PROBES.json (epo_ops_anonymous_boundary 403)"]

# ---------------- uspto_open_data_bulk: the ODP anonymous boundary measured ----------------
s["uspto_open_data_bulk"]["properties"]["ACCESSIBLE"] = (
    "REQUIRES_KEY [MEASURED_R499: anonymous GET to api.uspto.gov ODP search returns HTTP 403 -- "
    "the key gate is measured; free does not imply anonymous (LXXV)]"
)
s["uspto_open_data_bulk"]["evidence"] = ["R499/R499_FREE_SOURCE_PROBES.json (uspto_odp_anonymous_boundary 403)"]

# ---------------- patentsview: DNS-unresolvable from THIS sandbox (typed honestly) ----------------
s["patentsview"]["properties"]["ACCESSIBLE"] = (
    "UNRESOLVABLE_FROM_THIS_SANDBOX [MEASURED_R499: search.patentsview.org DNS resolution fails from "
    "this environment -- a sandbox network property, NOT a source availability claim; the REQUIRES_KEY "
    "registration state stands from research typing]"
)
s["patentsview"]["evidence"] = ["R499/R499_FREE_SOURCE_PROBES.json (patentsview_anonymous_boundary DNS failure)"]

# ---------------- zenodo: 403 measured this round (typed; retryable) ----------------
s["zenodo_patent_datasets"]["properties"]["ACCESSIBLE"] = (
    "HTTP_403_THIS_RUN [MEASURED_R499: zenodo.org/api/records answered 403 to this sandbox -- "
    "a client-side block/budget state, never a source-availability claim; retryable in a later round]"
)
s["zenodo_patent_datasets"]["evidence"] = ["R499/R499_FREE_SOURCE_PROBES.json (zenodo_patent_records 403)"]

# ---------------- registry-level updates ----------------
reg["version"] = "1.1.0"
reg["created_round"] = reg.get("created_round", "R498")
reg["amended_round"] = "R499"
reg["amendment_note"] = (
    "R499 (the operator directive 'use huggingface and other free sources'): EPO LOD 406 superseded "
    "(endpoint-URL root cause; live SPARQL at /linked-data/query); HF datasets-server retrieval path "
    "measured live; github recovered; EPO OPS / USPTO ODP anonymous boundaries measured (403s); "
    "patentsview DNS-unresolvable from this sandbox (typed as a sandbox property); zenodo 403 this run. "
    "No absence claims introduced or removed; every state carries measurement provenance."
)
reg["fabric_integration"] = reg.get("fabric_integration", {})
if isinstance(reg["fabric_integration"], dict):
    reg["fabric_integration"]["installed_legs_r499"] = {
        "HF_USPTO_CORPUS": ("Tier-3 discovery provider wired into search_all_sources "
                            "(discovery_fabric/prior_art_v2/free_evidence_sources.py)"),
        "EPO_LINKED_OPEN_DATA": ("identity/family/primary-document VERIFICATION transport "
                                 "(LXXV clause 3 path; deliberately NOT a keyword-search provider)"),
    }

json.dump(reg, open(REG, "w"), indent=1)
print("registry v1.1.0 written:", REG)

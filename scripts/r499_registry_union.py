#!/usr/bin/env python3
"""R499 union resolution: PATENT_SOURCE_REGISTRY.json (the RACE with Coder 2's R499/R500).

Both lines independently executed the operator's free-source directive and both
bumped the registry 1.0.0 -> 1.1.0. This union folds BOTH measurement sets:

THEIRS (R500, base): SPARQL protocol LIVE (GET+POST), the ld+json item path
  UNRESOLVED_THIS_ENVIRONMENT (soft-empty Elda wrapper), MEASURED_R500 class.
MINE (R499): the full identity model REPRODUCED via the SPARQL query path
  (identity EP/0084638/A1; family chain simple-family/25798930; Tier-1 primary
  documents XML+PDF 200 with sha256), US8968233B2 NOT_IN_GRAPH via SPARQL,
  query-cost bound measured (full-graph scans time out), github recovered,
  zenodo 403, EPO OPS/USPTO ODP 403 anonymous boundaries, HF /search transient,
  per-record CC BY 4.0 on the corpus.

The union's decisive fact: the R500 OPEN item ("full-identity-model
OPERATOR_MEASURED_UNREPRODUCED_THIS_ENVIRONMENT") is CLOSED on the SPARQL path
— the identity model binds real data (byte-evidenced in
R499/R499_FREE_LEGS_LIVE_PROOF.json). The ld+json REST path stays
unresolved-this-env per their five-pass measurement. Both measurements stand;
neither is discarded (Art. XXIV).

Output: registry v1.2.0.
"""
import json
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(REPO, "PATENT_SOURCE_REGISTRY.json")

theirs_raw = subprocess.run(["git", "show", "origin/main:PATENT_SOURCE_REGISTRY.json"],
                            capture_output=True, text=True, cwd=REPO).stdout
mine_raw = open(REG).read()  # the conflicted working copy holds mine (with markers — regenerate instead)
base_raw = subprocess.run(["git", "show", "8e27eb4d:PATENT_SOURCE_REGISTRY.json"],
                          capture_output=True, text=True, cwd=REPO).stdout

# my side is the staged version (stage 2 = ours)
mine_raw = subprocess.run(["git", "show", ":2:PATENT_SOURCE_REGISTRY.json"],
                          capture_output=True, text=True, cwd=REPO).stdout

T = json.loads(theirs_raw)
M = json.loads(mine_raw)
assert T["version"] == "1.1.0" and M["version"] == "1.1.0", (T["version"], M["version"])

U = T  # start from theirs (the base with MEASURED_R500 class + their evidence chains)
U["version"] = "1.2.0"

# ---- provenance classes: union ----
U["provenance_classes"]["MEASURED_R499"] = (
    "measured live by this line's R499 free-source probes + free-legs live proof "
    "(zero PatentBear debits; the Coder-1 parallel execution of the same operator directive)")

# ---- epo_linked_open_data: the union of both measurement sets ----
e = U["sources"]["epo_linked_open_data"]
m_e = M["sources"]["epo_linked_open_data"]
e["properties"]["ACCESSIBLE"] = (
    "YES-LIVE [MEASURED_R500 + MEASURED_R499 (two independent lines, same endpoint)]: the SPARQL 1.1 protocol "
    "endpoint https://data.epo.org/linked-data/query measures LIVE (GET and POST, application/sparql-results+json). "
    "The R500 ld+json item path on the data URIs stays UNRESOLVED_THIS_ENVIRONMENT (soft-empty Elda wrapper, "
    "items=rdf:nil across five passes) — the R500 OPEN item is CLOSED ON THE SPARQL PATH by R499: the full "
    "identity model binds real data there (EP/0084638/A1 identity + simple-family/25798930 chain + Tier-1 "
    "primary documents XML/PDF 200, sha256-evidenced in R499/R499_FREE_LEGS_LIVE_PROOF.json). "
    "Historical: the R498 406 was the query-UI URL, not the protocol endpoint"
)
e["properties"]["AUTOMATABLE"] = (
    "YES [MEASURED_R500 + MEASURED_R499]: SPARQL 1.1 protocol; subject-anchored identity/family/citation "
    "queries return in seconds with full bindings"
)
e["properties"]["RATE-LIMITED"] = (
    "QUERY-COST-BOUND [MEASURED_R499]: full-graph scans (unbounded FILTER / GROUP BY COUNT) time out at the "
    "endpoint while subject-anchored queries return in seconds — the installed transport issues "
    "subject-anchored queries only, by construction; no quota/meter signal observed on keyless use [MEASURED_R500]"
)
e["properties"]["AUTHENTICATED"] = "NO KEY REQUIRED [MEASURED_R499 + MEASURED_R500: anonymous query + document fetch both served]"
e["properties"]["FREE"] = (
    "YES [MEASURED_R499: full SPARQL query path + primary document fetches served with no credential and no meter]. "
    "The provider notice reads 'Provided by the European Patent Office.' [MEASURED_R500]; the CC BY 4.0 license "
    "claim stays OPERATOR_RESEARCH (ORUV) pending terms review"
)
e["measured_state"] = "LIVE_MEASURED"
e["evidence"] = list(dict.fromkeys(list(e.get("evidence", [])) + list(m_e.get("evidence", []))))
e["notes"] = (
    "TWO-LINE UNION: SPARQL protocol live (both lines); the R500 ld+json item path unresolved-this-env; the "
    "R499 SPARQL chain closes the R500 open item (full identity model reproduced: identity, family collapse, "
    "citation graph, Tier-1 primary documents). Coverage measured EP-centric: US/worldwide partial — US 3268123 A "
    "in-graph, US 8968233B2 NOT_IN_GRAPH via SPARQL (zero bindings) — a coverage state of THIS dataset, never "
    "evidence of absence. Installed transport: free_evidence_sources.py (Coder-1 line) — identity/family/document "
    "VERIFICATION path per LXXV clause 3; the sibling line's FreePatentSourceLayer (rbg_gate.py) is the "
    "instrument-side coverage layer. COMPLEMENTARY, not duplicate."
)

# ---- huggingface: union ----
h = U["sources"]["huggingface_patent_datasets"]
m_h = M["sources"]["huggingface_patent_datasets"]
h["properties"]["ACCESSIBLE"] = (
    "YES-LIVE [MEASURED_R499 (Coder 1) + MEASURED_R500 (Coder 2), independent]: datasets API + datasets-server "
    "/splits + /rows all 200 on common-pile/uspto (served view 131,755 full-text documents, content-bearing text "
    "field, structured ids US-71623224-A shape); /search measured the provider's verbatim warming transient "
    "('the dataset index is loading, this can take longer than usual', 500) by BOTH lines across the round — "
    "typed transient/unstable, never a coverage claim"
)
h["properties"]["AUTOMATABLE"] = (
    "YES [MEASURED_R499 + MEASURED_R500]: datasets-server /splits + /rows deterministic; /search typed-pending"
)
h["properties"]["LICENSE-COMPATIBLE"] = (
    "PER-DATASET, MEASURED FOR common-pile/uspto [MEASURED_R499: per-record license field reads "
    "'Creative Commons - Attribution' (CC BY 4.0) — attribution mechanics to record on ingestion]; other "
    "corpora remain UNREVIEWED_PER-DATASET"
)
h["properties"]["RATE-LIMITED"] = "UNMETERED-ANONYMOUS [MEASURED_R499: no quota signal surfaced on any call; no account, no meter]"
h["evidence"] = list(dict.fromkeys(list(h.get("evidence", [])) + list(m_h.get("evidence", []))))
h["notes"] = (
    "The served-view row count 131,755 is MEASURED by both lines; the operator brief's ~16.2M-row figure for the "
    "full upstream remains EXTERNAL_CLAIM_UNVERIFIED_AT_SERVED_VIEW (Coder-2 typing) — measured wins for the "
    "served surface. Coder-1 line installed the corpus transport (discovery ladder + deterministic rows); "
    "Coder-2 line installed the instrument coverage layer (FreePatentSourceLayer, battery v4 F12/F13)."
)

# ---- github: both measured 200 ----
g = U["sources"]["github_patent_infra"]
m_g = M["sources"]["github_patent_infra"]
g["properties"]["ACCESSIBLE"] = (
    "YES-LIVE [MEASURED_R499 (Coder 1: repo metadata 200 from this sandbox) + MEASURED_R500 (Coder 2: "
    "google/patents-public-data substrate 200)]: the R498 per-IP rate-limit state recovered; per-IP budget "
    "states remain transient by nature, typed per call"
)
g["evidence"] = list(dict.fromkeys(list(g.get("evidence", [])) + list(m_g.get("evidence", []))))

# ---- sources only Coder 1 measured this round ----
for sid, m_src in M["sources"].items():
    if sid in ("epo_linked_open_data", "huggingface_patent_datasets", "github_patent_infra"):
        continue
    u_src = U["sources"].get(sid, {})
    # keep whichever ACCESSIBLE carries a newer measurement; prefer union of both
    if "MEASURED_R499" in m_src.get("properties", {}).get("ACCESSIBLE", ""):
        u_src["properties"] = u_src.get("properties", {}) or {}
        u_src["properties"]["ACCESSIBLE"] = m_src["properties"]["ACCESSIBLE"]
        u_src["evidence"] = list(dict.fromkeys(list(u_src.get("evidence", [])) + list(m_src.get("evidence", []))))
        U["sources"][sid] = u_src

# ---- fabric integration: union both lines' installs ----
fi = U.get("fabric_integration", {})
if isinstance(fi, dict):
    fi["installed_legs_r499_union"] = {
        "HF_USPTO_CORPUS (Coder 1)": "discovery-ladder provider + deterministic rows transport (free_evidence_sources.py)",
        "EPO_LINKED_OPEN_DATA (Coder 1)": "identity/family/primary-document VERIFICATION transport (LXXV clause 3 path)",
        "FreePatentSourceLayer (Coder 2)": "instrument-side coverage layer in rbg_gate.py; battery v4 F12/F13 (substrate honesty + corpus hallucination attack)",
    }
    U["fabric_integration"] = fi

U["amended_round"] = "R499+R500 union"
U["amendment_note"] = (
    "v1.2.0 UNION of the two parallel executions of the operator's free-source directive: Coder 2's R499/R500 "
    "(instrument-side coverage layer, battery v4, five-pass EPO LOD probe driver, SPARQL protocol live, ld+json "
    "item path unresolved) + Coder 1's R499 (corpus + identity/family/document transports installed, the full "
    "identity model reproduced on the SPARQL path — closing the R500 open item, query-cost bound measured, "
    "github/zenodo/EPO-OPS/USPTO-ODP/PatentsView boundary measurements). No absence claims; every state carries "
    "measurement provenance; both lines' evidence chains preserved."
)

json.dump(U, open(REG, "w"), indent=1)
print("union registry v1.2.0 written with",
      len(U["sources"]), "sources;",
      "epo_lod evidence entries:", len(U["sources"]["epo_linked_open_data"]["evidence"]))

"""SOURCE_REGISTRY — the single authority over every evidence source.

CEO database-layer directive: every source has exactly these fields:

    source_id, name, authority_role, coverage, access_method,
    update_frequency, rate_limits, licensing, primary_or_secondary,
    freshness, known_gaps, provenance_method, health_status

Constitutional rules encoded here:
- Art. X: THIS registry is the one authority for source definitions. The
  connectors/README aspirational lists are NOT authority.
- Art. XXI: a source mentioned in a README is NOT integrated. The
  `connector` field names the implementing class; health_status is
  overlaid ONLY by a measured health run (see health.py).
- Art. XXV/XXVI: health_status defaults to NOT_MEASURED. No static value
  in this file may claim LIVE — LIVE is a measurement result, never an
  assertion (no self-certification).

Static fields below (coverage/licensing/rate limits/update frequency) are
facts about the PROVIDER'S STATED POLICY, not about our integration state;
integration state is carried ONLY by health_status (measured).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

NOT_MEASURED = "NOT_MEASURED"
# Measured-status vocabulary (health report overlay values).
MEASURED_STATUSES = {"LIVE", "DEGRADED", "UNAVAILABLE", "NOT_INTEGRATED"}

# A source with no connector: the registry records it so the coverage
# matrix can report the gap HONESTLY (Art. XV/XXV), but it can never be
# measured LIVE.
NO_CONNECTOR = None


def _src(
    source_id: str,
    name: str,
    authority_role: List[str],
    coverage: str,
    access_method: str,
    update_frequency: str,
    rate_limits: str,
    licensing: str,
    primary_or_secondary: str,
    freshness: str,
    known_gaps: str,
    provenance_method: str,
    connector: Optional[str] = None,
    auth_requires: Optional[List[str]] = None,
    metered_quota: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a source record with the 13 directive fields + wiring keys."""
    return {
        "source_id": source_id,
        "name": name,
        "authority_role": authority_role,
        "coverage": coverage,
        "access_method": access_method,
        "update_frequency": update_frequency,
        "rate_limits": rate_limits,
        "licensing": licensing,
        "primary_or_secondary": primary_or_secondary,
        "freshness": freshness,
        "known_gaps": known_gaps,
        "provenance_method": provenance_method,
        "health_status": NOT_MEASURED,
        # wiring (not part of the 13): the implementing connector class and
        # required credentials; health check imports these dynamically.
        "connector": connector,
        "auth_requires": auth_requires or [],
        # metered_quota (wiring, not part of the 13): provider-metered source.
        # The health checker must NOT live-probe a metered source (each probe
        # burns provider quota); its health is derived from the freshest
        # live retrieval-log proof inside the metered window (see health.py).
        "metered_quota": metered_quota,
    }


SOURCE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _register(rec: Dict[str, Any]) -> None:
    if rec["source_id"] in SOURCE_REGISTRY:
        raise ValueError(f"duplicate source_id {rec['source_id']}")
    SOURCE_REGISTRY[rec["source_id"]] = rec


# ---------------------------------------------------------------------------
# REGULATORY / ADVERSE EVENTS / RECALLS / DEVICE IDENTITY  (openFDA — no key)
# ---------------------------------------------------------------------------

_register(_src(
    source_id="fda_maude",
    name="FDA MAUDE adverse-event reports (openFDA device/event)",
    authority_role=["ADVERSE_EVENT"],
    coverage="Medical device adverse-event reports (MDR) submitted to FDA, "
             "1976-present; searchable by device brand name, event type, "
             "date, manufacturer.",
    access_method="REST JSON, no API key required; GET "
                  "https://api.fda.gov/device/event.json",
    update_frequency="openFDA MAUDE dataset refreshed weekly per FDA docs",
    rate_limits="240 requests/min without key; 240,000/day with key (per "
                "openFDA docs)",
    licensing="Open data (openFDA terms); FDA disclaims completeness and "
              "causality — limitations carried on every record",
    primary_or_secondary="PRIMARY",
    freshness="Weekly dataset refresh; individual report lag varies",
    known_gaps="FDA explicitly warns: report counts are NOT incidence; "
               "causality NOT verified; duplicate/incomplete/inaccurate "
               "reports exist (21 CFR 803). Voluntary reporting biases "
               "counts. Event text is unstructured.",
    provenance_method="Query + record MDR report key + raw payload sha256 "
                      "into hash-chained retrieval log; FDA limitation "
                      "metadata attached per record (Art. XXI.5)",
    connector="discovery_fabric.source_registry.connectors.openfda:MaudeConnector",
    auth_requires=[],
))

_register(_src(
    source_id="fda_recall",
    name="FDA device recall enforcement reports (openFDA device/recall)",
    authority_role=["RECALL"],
    coverage="Medical-device recall events with reason, classification "
             "(I/II/III), and product identification.",
    access_method="REST JSON, no API key required; GET "
                  "https://api.fda.gov/device/recall.json",
    update_frequency="openFDA recall dataset refreshed weekly per FDA docs",
    rate_limits="240 requests/min without key (per openFDA docs)",
    licensing="Open data (openFDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Weekly refresh; recall events appear after FDA classification",
    known_gaps="Enforcement-report view, not the firm's initial recall "
               "notification; root-cause text is free-form; no incidence "
               "semantics.",
    provenance_method="Query + recall event ID + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.openfda:FdaRecallConnector",
    auth_requires=[],
))

_register(_src(
    source_id="fda_510k",
    name="FDA 510(k) clearances (openFDA device/510k)",
    authority_role=["REGULATORY"],
    coverage="510(k) premarket notifications: device name, applicant, "
             "clearance date, predicate linkage via K-number, product codes.",
    access_method="REST JSON, no API key required; GET "
                  "https://api.fda.gov/device/510k.json",
    update_frequency="openFDA 510(k) dataset refreshed weekly per FDA docs",
    rate_limits="240 requests/min without key (per openFDA docs)",
    licensing="Open data (openFDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Weekly refresh; clearances appear after FDA decision",
    known_gaps="Predicate chains require iterative K-number lookups; "
               "summary-of-safety text not included in this endpoint.",
    provenance_method="Query + K-number + raw payload sha256 into retrieval "
                      "log",
    connector="discovery_fabric.source_registry.connectors.openfda:Fda510kConnector",
    auth_requires=[],
))

_register(_src(
    source_id="fda_pma",
    name="FDA PMA approvals and supplements (openFDA device/pma)",
    authority_role=["REGULATORY"],
    coverage="Premarket approval originals and supplements: device, "
             "applicant, decision date, supplement type.",
    access_method="REST JSON, no API key required; GET "
                  "https://api.fda.gov/device/pma.json",
    update_frequency="openFDA PMA dataset refreshed weekly per FDA docs",
    rate_limits="240 requests/min without key (per openFDA docs)",
    licensing="Open data (openFDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Weekly refresh",
    known_gaps="Panel-track supplement detail and approval-condition text "
               "not included.",
    provenance_method="Query + PMA number + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.openfda:FdaPmaConnector",
    auth_requires=[],
))

_register(_src(
    source_id="fda_udi",
    name="AccessGUDID device identity (openFDA device/udi)",
    authority_role=["DEVICE_IDENTITY"],
    coverage="GUDID records: brand name, company, device identifiers, "
             "product codes, MRI safety status, sterility, device class.",
    access_method="REST JSON, no API key required; GET "
                  "https://api.fda.gov/device/udi.json",
    update_frequency="GUDID data refreshed daily per openFDA docs",
    rate_limits="240 requests/min without key (per openFDA docs)",
    licensing="Open data (openFDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Daily refresh",
    known_gaps="Only devices with UDI requirements; some fields "
               "manufacturer-declared and unverified.",
    provenance_method="Query + DI/GUDID id + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.openfda:FdaUdiConnector",
    auth_requires=[],
))

_register(_src(
    source_id="fda_registrationlisting",
    name="FDA establishment registration & device listing "
         "(openFDA device/registrationlisting)",
    authority_role=["REGULATORY"],
    coverage="Registered establishments and listed devices with product "
             "codes and registration numbers.",
    access_method="REST JSON, no API key required; GET "
                  "https://api.fda.gov/device/registrationlisting.json",
    update_frequency="Per openFDA docs (annual registration cycle, periodic "
                      "refresh)",
    rate_limits="240 requests/min without key (per openFDA docs)",
    licensing="Open data (openFDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Periodic refresh",
    known_gaps="Listing text is self-reported by firms; structure varies "
               "heavily across years.",
    provenance_method="Query + registration/listing IDs + raw payload "
                      "sha256 into retrieval log",
    connector="discovery_fabric.source_registry.connectors.openfda:FdaRegListConnector",
    auth_requires=[],
))

_register(_src(
    source_id="fda_classification",
    name="FDA product classification (openFDA device/classification)",
    authority_role=["REGULATORY"],
    coverage="Device classification records: product code, device name, "
             "class, regulation number, review panel.",
    access_method="REST JSON, no API key required; GET "
                  "https://api.fda.gov/device/classification.json",
    update_frequency="Per openFDA docs (periodic refresh)",
    rate_limits="240 requests/min without key (per openFDA docs)",
    licensing="Open data (openFDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Periodic refresh",
    known_gaps="Classification is generic-device level, not "
               "instance-specific.",
    provenance_method="Query + product code + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.openfda:FdaClassificationConnector",
    auth_requires=[],
))

_register(_src(
    source_id="fda_denovo",
    name="FDA De Novo classification requests",
    authority_role=["REGULATORY"],
    coverage="De Novo request grants (device + decision), 1997-present.",
    access_method="No public API measured: openFDA has no De Novo endpoint "
                  "(probe 404); FDA publishes a downloadable CSV at "
                  "fda.gov — not integrated",
    update_frequency="CSV updated periodically by FDA",
    rate_limits="n/a (download)",
    licensing="Open data (FDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Periodic CSV publication",
    known_gaps="NO CONNECTOR: measured probe of api.fda.gov/device/ndec and "
               "/denovo returned 404. Integration requires the CSV "
               "pipeline — honest gap, recorded, not silently claimed.",
    provenance_method="Planned: CSV row hash + download timestamp; not yet "
                      "implemented",
    connector=NO_CONNECTOR,
    auth_requires=[],
))

# ---------------------------------------------------------------------------
# CLINICAL
# ---------------------------------------------------------------------------

_register(_src(
    source_id="clinicaltrials_gov",
    name="ClinicalTrials.gov registry (API v2)",
    authority_role=["CLINICAL"],
    coverage="Registered clinical studies globally: status, phase, "
             "conditions, interventions, sponsors, outcomes.",
    access_method="REST JSON, no API key required; GET "
                  "https://clinicaltrials.gov/api/v2/studies",
    update_frequency="Continuous (records updated by sponsors)",
    rate_limits="Polite use expected; no published hard limit",
    licensing="Open data (NIH/NLM terms)",
    primary_or_secondary="PRIMARY",
    freshness="Near-real-time registry updates",
    known_gaps="Registry ≠ results: completion does not imply publication; "
               "device interventions are free-text, identity resolution to "
               "GUDID is unresolved by design here.",
    provenance_method="Query + NCT number + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.clinicaltrials:ClinicalTrialsConnector",
    auth_requires=[],
))

_register(_src(
    source_id="who_ictrp",
    name="WHO International Clinical Trials Registry Platform",
    authority_role=["CLINICAL"],
    coverage="Global trial registrations from primary registries.",
    access_method="Web portal (ASP) measured reachable; no public JSON API "
                  "measured — NOT integrated",
    update_frequency="Continuous aggregation",
    rate_limits="n/a",
    licensing="Open data (WHO terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="NO CONNECTOR: the portal is an HTML application; no "
               "measured machine API. Recorded as an honest gap.",
    provenance_method="Planned: export parsing; not yet implemented",
    connector=NO_CONNECTOR,
    auth_requires=[],
))

# ---------------------------------------------------------------------------
# SCIENTIFIC
# ---------------------------------------------------------------------------

_register(_src(
    source_id="europepmc",
    name="Europe PMC (REST)",
    authority_role=["SCIENTIFIC"],
    coverage="Biomedical literature: PubMed-indexed + agricol + preprints; "
             "abstracts, metadata, citation counts.",
    access_method="REST JSON, no API key; GET "
                  "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
    update_frequency="Continuous (EBI releases)",
    rate_limits="Polite use; no published hard limit",
    licensing="Open data (CC-BY for most metadata; article licenses vary)",
    primary_or_secondary="PRIMARY",
    freshness="Near-real-time with PubMed",
    known_gaps="Abstracts absent for some records; relevance must still be "
               "adjudicated per record (Art. XXI.4).",
    provenance_method="Query + PMCID/PMID + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.scientific:EuropePmcConnector",
    auth_requires=[],
))

_register(_src(
    source_id="pubmed",
    name="PubMed (NCBI E-utilities)",
    authority_role=["SCIENTIFIC"],
    coverage="MEDLINE/PubMed citations and abstracts.",
    access_method="REST JSON (esearch/esummary/efetch), no API key; GET "
                  "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
    update_frequency="Daily (MEDLINE updates)",
    rate_limits="3 requests/s without key (NCBI policy)",
    licensing="Open data (NLM terms)",
    primary_or_secondary="PRIMARY",
    freshness="Daily",
    known_gaps="Abstracts not on all records; esearch gives ids only — "
               "esummary/efetch round-trip needed for full metadata.",
    provenance_method="Query + PMID + raw payload sha256 into retrieval log",
    connector="discovery_fabric.source_registry.connectors.scientific:PubMedConnector",
    auth_requires=[],
))

_register(_src(
    source_id="openalex",
    name="OpenAlex",
    authority_role=["SCIENTIFIC"],
    coverage="Open scholarly graph: works, citations, concepts, institutions.",
    access_method="REST JSON; GET https://api.openalex.org/works",
    update_frequency="Continuous",
    rate_limits="Polite pool with mailto=; credit-budget model measured "
                "ACTIVE: probe returned 429 'Insufficient budget ... Resets "
                "at midnight' — a runtime constraint, not a doc claim",
    licensing="Open data (CC0)",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="Budget-exhausted at measurement time (measured 429); "
               "abstracts are inverted-index reconstructions.",
    provenance_method="Query + OpenAlex work id + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.scientific:OpenAlexConnector",
    auth_requires=[],
))

_register(_src(
    source_id="semantic_scholar",
    name="Semantic Scholar (S2 API)",
    authority_role=["SCIENTIFIC"],
    coverage="Computer-science-heavy scholarly graph with citation context.",
    access_method="REST JSON; GET "
                  "https://api.semanticscholar.org/graph/v1/",
    update_frequency="Continuous",
    rate_limits="Unauthenticated tier measured RATE_LIMITED (429 with "
                "'apply for a key' body); reliable use needs an API key",
    licensing="Open data (S2 terms)",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="No key provisioned in this environment; biomedical coverage "
               "thinner than PubMed/EuropePMC.",
    provenance_method="Query + S2 paper id + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.scientific:SemanticScholarConnector",
    auth_requires=["SEMANTIC_SCHOLAR_API_KEY (not provisioned)"],
))

_register(_src(
    source_id="crossref",
    name="Crossref",
    authority_role=["SCIENTIFIC"],
    coverage="DOI registration agency metadata: works, references, funders.",
    access_method="REST JSON; GET https://api.crossref.org/works",
    update_frequency="Continuous",
    rate_limits="Polite pool with mailto=; no published hard limit",
    licensing="Open metadata (Crossref terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="Metadata-only (no abstracts for many records); member "
               "quality varies.",
    provenance_method="Query + DOI + raw payload sha256 into retrieval log",
    connector="discovery_fabric.source_registry.connectors.scientific:CrossrefConnector",
    auth_requires=[],
))

_register(_src(
    source_id="elsevier_scopus",
    name="Elsevier Scopus (Scopus Search API)",
    authority_role=["SCIENTIFIC"],
    coverage="Scopus-indexed scientific, technical, and medical literature: "
             "titles, abstracts, authors, affiliations, publication dates, "
             "citation counts; broad STM coverage incl. engineering and "
             "medical-device literature.",
    access_method="REST JSON; GET "
                  "https://api.elsevier.com/content/search/scopus with "
                  "X-ELS-APIKey header",
    update_frequency="Daily (Scopus daily update cycle)",
    rate_limits="Per key: measured 2026-08-29 at probe volume; institutional "
                "entitlement governs full-text endpoints — this integration "
                "uses search metadata only",
    licensing="Elsevier Developer Portal terms; API key per registered "
              "account; metadata use per Elsevier policy",
    primary_or_secondary="SECONDARY",
    freshness="Daily",
    known_gaps="Subscription-boundary opacity: search returns totalResults "
               "and metadata for the whole index, but some full-text "
               "representations require entitlement this key may not carry "
               "(not measured, not claimed). Relevance must still be "
               "adjudicated per record (Art. XXI.4).",
    provenance_method="Query + Scopus EID/DOI + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.scientific:ElsevierScopusConnector",
    auth_requires=["ELSEVIER_API_KEY (provisioned in .env.keys)"],
))

# ---------------------------------------------------------------------------
# PATENT
# ---------------------------------------------------------------------------

_register(_src(
    source_id="google_patents",
    name="Google Patents (xhr query)",
    authority_role=["PATENT"],
    coverage="Global patent corpus bibliographics via the public xhr "
             "endpoint (existing prior_art_v2 adapter).",
    access_method="REST JSON (undocumented xhr endpoint), no API key",
    update_frequency="Continuous",
    rate_limits="Bot detection: measured HTTP 503 'Sorry...' at health "
                "probe — long-documented TEMPORARILY_UNAVAILABLE state",
    licensing="Public interface; data © Google/EPABIB/USPTO per Google "
              "Patents terms",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="Undocumented endpoint may change without notice; bot "
               "blocking makes reliability poor without a licensed path.",
    provenance_method="Query + publication number + raw payload sha256 "
                      "(existing prior_art_v2 custody rules)",
    connector="discovery_fabric.source_registry.connectors.patents:GooglePatentsConnector",
    auth_requires=[],
))

# The Lens: TWO SEPARATE sources (CEO Section 4 / elite_v3 — never merged).
# Measured 2026-08-29 with the provisioned LENS_API_TOKEN: BOTH endpoints
# authenticate and return relevant records with title:(...) string queries
# (patent: 48 total for 'hydrocephalus shunt valve'; scholarly: 1309 total
# for 'cerebrospinal fluid shunt'). Measurement history disclosed: the FIRST
# scholarly probe at 07:47 UTC answered 401 'Unable to authorize user to
# this resource'; re-measurement at 08:04+ answered 200 — classified as a
# TRANSIENT provider state (likely entitlement propagation after key
# provisioning), not a stable entitlement boundary. Separately discovered
# and fixed the same day: the structured DSL query form is SILENTLY IGNORED
# by api.lens.org (returns 756k newest records regardless of relevance) —
# the string form is the only correct relevance binding; a regression test
# pins it.
_register(_src(
    source_id="lens_scholarly",
    name="The Lens — scholarly (NPL) search",
    authority_role=["SCIENTIFIC"],
    coverage="Non-patent scholarly literature records (NPL) with abstracts "
             "and external ids; NOT patent coverage (CEO Section 4).",
    access_method="REST (POST https://api.lens.org/scholarly/search) with "
                  "Bearer token",
    update_frequency="Continuous",
    rate_limits="Token-tier dependent; measured 2026-08-29 working at "
                "probe volume (single-digit requests); one transient 401 "
                "observed 14 minutes after token provisioning",
    licensing="API terms per Lens subscription",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="MEASUREMENT HISTORY (2026-08-29): first probe 401 (07:47 "
               "UTC), re-measurement 200 with relevant records (08:04+ UTC) "
               "— transient provider state disclosed, not hidden. Known "
               "limits: abstract coverage varies; relevance must still be "
               "adjudicated per record (Art. XXI.4); the DSL query form is "
               "broken-by-design on Lens (silently ignored) — string form "
               "pinned by regression test.",
    provenance_method="prior_art_v2 PriorArtHit custody "
                      "(raw_payload_sha256, query, retrieved_at) + registry "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.patents:LensConnector",
    auth_requires=["LENS_API_TOKEN (provisioned in .env.keys)"],
))

_register(_src(
    source_id="lens_patent",
    name="The Lens — patent search",
    authority_role=["PATENT"],
    coverage="Global patent bibliographic records: title, abstract, "
             "applicants, publication date, jurisdiction, doc_key, "
             "legal_status; queryable by title terms (string query form).",
    access_method="REST (POST https://api.lens.org/patent/search) with "
                  "Bearer token",
    update_frequency="Continuous",
    rate_limits="Token-tier dependent; measured 2026-08-29 working at "
                "probe volume (single-digit requests)",
    licensing="API terms per Lens subscription",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="Bibliographic coverage only in search results — claim TEXT "
               "is not included; claim-level evidence needs PatentBear "
               "full-record fetch (metered) or another claims source. The "
               "patent endpoint rejects 'include' parameters (400 "
               "Unrecognized fields — measured); invention_title arrives as "
               "a [{text, lang}] list. Relevance must still be adjudicated "
               "per record (Art. XXI.4).",
    provenance_method="prior_art_v2 PriorArtHit custody "
                      "(raw_payload_sha256, query, retrieved_at) + registry "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.patents:LensPatentConnector",
    auth_requires=["LENS_API_TOKEN (provisioned in .env.keys)"],
))

_register(_src(
    source_id="patentbear",
    name="Patent Bear (MCP JSON-RPC: US patent search + full-text records)",
    authority_role=["PATENT"],
    coverage="US patents and published applications: keyword search, exact "
             "identifier lookup (e.g. US9033909B2), and VERBATIM full text "
             "— title, abstract, numbered claims, description sections.",
    access_method="MCP (JSON-RPC 2.0 over HTTP POST "
                  "https://www.patentbear.com/mcp) with Bearer token; tools: "
                  "search_patents, get_patent_record, run_lab, get_lab_result",
    update_frequency="Continuous (Patent Bear record store)",
    rate_limits="MEASURED 2026-08-29 on this key: 20 requests/month across "
                "search_patents + get_patent_record (provider 'usage' block "
                "in every response); run_lab bills credits SEPARATELY and is "
                "PROHIBITED in this engine (never called). Connector carries "
                "a quota guard: provider-reported remaining==0 -> RATE_LIMITED "
                "without making the call.",
    licensing="Commercial subscription (Patent Bear terms); API key per "
              "account",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="US-centric corpus (US grants + publications + NPL articles); "
               "monthly quota of 20 makes bulk retrieval impossible — the "
               "engine uses it for targeted full-text/claims fetches ONLY, "
               "never for routine scanning; automated health checks do NOT "
               "live-probe this source (metered; see health.py policy).",
    provenance_method="prior_art_v2 PriorArtHit custody + registry retrieval "
                      "log; usage block (monthly_used/remaining) logged per "
                      "response as rate_limit_remaining",
    connector="discovery_fabric.source_registry.connectors.patents:PatentBearConnector",
    auth_requires=["PATENT_BEAR_API_KEY (provisioned in .env.keys)"],
    metered_quota={
        "monthly_limit": 20,
        "metered_by": "provider usage block (monthly_limit/monthly_used/"
                      "monthly_remaining) returned in every response",
        "health_policy": "no-live-probe; LIVE is derived from the freshest "
                         "live retrieval-log proof inside the metered window",
        "metered_window_days": 31,
        "prohibited_tools": ["run_lab (bills credits; never called by this "
                             "engine)", "get_lab_result (only after a "
                             "run_lab, hence never called)"],
    },
))

_register(_src(
    source_id="patsnap_eureka",
    name="PatSnap Eureka open platform",
    authority_role=["PATENT"],
    coverage="Patent search + claims via commercial API.",
    access_method="REST with API key",
    update_frequency="Continuous",
    rate_limits="Tier dependent; long-documented rate-limit failures in "
                "this environment",
    licensing="Commercial subscription",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="NO KEY provisioned; historical suite failures recorded as "
               "the documented pre-existing environmental failure.",
    provenance_method="Existing prior_art_v2 custody rules",
    connector="discovery_fabric.source_registry.connectors.patents:PatSnapConnector",
    auth_requires=["PATSNAP_EUREKA_API_KEY (not provisioned)"],
))

_register(_src(
    source_id="epo_ops",
    name="EPO Open Patent Services (OPS)",
    authority_role=["PATENT"],
    coverage="Bibliographic data, INPADOC family, legal status, full text, "
             "search — worldwide coverage.",
    access_method="REST with OAuth2 client credentials",
    update_frequency="Continuous",
    rate_limits="Free tier: throttled services per EPO fair-use policy",
    licensing="OPS terms (fair use)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="NO CONSUMER CREDENTIALS provisioned; probe measured 403 "
               "'Fair Use policy' at IP level — cloud ASN blocked. Both "
               "credential and network path are open items.",
    provenance_method="Existing epo_ops_adapter custody rules",
    connector="discovery_fabric.source_registry.connectors.patents:EpoOpsConnector",
    auth_requires=["EPO_OPS_CONSUMER_KEY/SECRET (not provisioned)",
                   "unblocked egress IP (ASN currently blocked)"],
))

_register(_src(
    source_id="uspto_odp",
    name="USPTO Open Data Portal",
    authority_role=["PATENT"],
    coverage="US patent grants/applications metadata, claims, continuity, "
             "citations.",
    access_method="REST with API key from USPTO subscription center",
    update_frequency="Continuous",
    rate_limits="Key-tier dependent",
    licensing="Open data (USPTO terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="NO API KEY provisioned — probe measured 403.",
    provenance_method="Existing uspto_odp_adapter custody rules",
    connector="discovery_fabric.source_registry.connectors.patents:UsptoOdpConnector",
    auth_requires=["USPTO_ODP_API_KEY (not provisioned)"],
))

_register(_src(
    source_id="wipo_patentscope",
    name="WIPO PATENTSCOPE",
    authority_role=["PATENT"],
    coverage="PCT international applications, national-phase entries.",
    access_method="Web portal measured reachable (HTML); official "
                  "PATENTSCOPE web service requires a key — NOT integrated",
    update_frequency="Continuous",
    rate_limits="Web-service tier dependent",
    licensing="WIPO terms",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="NO CONNECTOR: public JSON API not measured; the web portal "
               "is an HTML app. Honest gap.",
    provenance_method="Planned: web-service key + request custody",
    connector=NO_CONNECTOR,
    auth_requires=["WIPO_WEB_SERVICE_KEY (not provisioned)"],
))

_register(_src(
    source_id="google_bigquery_patents",
    name="Google Patents Public Datasets (BigQuery)",
    authority_role=["PATENT"],
    coverage="Full-text patent corpora on BigQuery.",
    access_method="BigQuery SQL with GCP credentials (existing adapter)",
    update_frequency="Periodic dataset publication",
    rate_limits="GCP quota dependent",
    licensing="Open data on BigQuery (GCP billing applies)",
    primary_or_secondary="PRIMARY",
    freshness="Periodic",
    known_gaps="NO GCP CREDENTIALS provisioned.",
    provenance_method="Existing bigquery_patents_adapter custody rules",
    connector="discovery_fabric.source_registry.connectors.patents:BigQueryPatentsConnector",
    auth_requires=["GCP credentials (not provisioned)"],
))

# ---------------------------------------------------------------------------
# CHEMISTRY / BIOLOGY
# ---------------------------------------------------------------------------

_register(_src(
    source_id="pubchem",
    name="PubChem (PUG REST)",
    authority_role=["CHEMISTRY"],
    coverage="Compounds, substances, assays, properties.",
    access_method="REST JSON, no API key; GET "
                  "https://pubchem.ncbi.nlm.nih.gov/rest/pug/",
    update_frequency="Continuous",
    rate_limits="Polite use; max 5 requests/s published guideline",
    licensing="Open data (PubChem terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="No device linkage; property coverage varies by compound.",
    provenance_method="Query + CID + raw payload sha256 into retrieval log",
    connector="discovery_fabric.source_registry.connectors.biochem:PubChemConnector",
    auth_requires=[],
))

_register(_src(
    source_id="uniprot",
    name="UniProt KB",
    authority_role=["BIOLOGY"],
    coverage="Protein sequences, functions, annotations.",
    access_method="REST, no API key; GET https://rest.uniprot.org/uniprotkb/",
    update_frequency="Continuous releases",
    rate_limits="Polite use",
    licensing="Open data (CC-BY 4.0)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="No device linkage; reviewed (Swiss-Prot) vs unreviewed "
               "(TrEMBL) confidence differs.",
    provenance_method="Query + accession + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.biochem:UniProtConnector",
    auth_requires=[],
))

_register(_src(
    source_id="chembl",
    name="ChEMBL",
    authority_role=["BIOLOGY"],
    coverage="Bioactive molecules with drug-like properties and assay data.",
    access_method="REST JSON, no API key; GET "
                  "https://www.ebi.ac.uk/chembl/api/data/",
    update_frequency="Periodic releases",
    rate_limits="Polite use",
    licensing="Open data (CC-BY-SA 3.0)",
    primary_or_secondary="PRIMARY",
    freshness="Periodic release",
    known_gaps="Small-molecule focus; no device linkage.",
    provenance_method="Query + ChEMBL id + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.biochem:ChEMBLConnector",
    auth_requires=[],
))

_register(_src(
    source_id="rcsb_pdb",
    name="RCSB Protein Data Bank",
    authority_role=["BIOLOGY"],
    coverage="Experimentally-determined 3D macromolecular structures.",
    access_method="REST JSON, no API key; GET https://data.rcsb.org/rest/v1/",
    update_frequency="Weekly structural releases",
    rate_limits="Polite use",
    licensing="Open data (PDB terms)",
    primary_or_secondary="PRIMARY",
    freshness="Weekly",
    known_gaps="Structure availability only for crystallized/solved "
               "targets; no device linkage.",
    provenance_method="Query + PDB id + raw payload sha256 into retrieval "
                      "log",
    connector="discovery_fabric.source_registry.connectors.biochem:RcsbPdbConnector",
    auth_requires=[],
))

# ---------------------------------------------------------------------------
# MATERIALS
# ---------------------------------------------------------------------------

_register(_src(
    source_id="cod_optimade",
    name="Crystallography Open Database (OPTIMADE v1)",
    authority_role=["MATERIALS"],
    coverage="Published crystal structures (CIF) of inorganic, mineral and "
             "implant-relevant ceramic phases (hydroxyapatite, zirconia, "
             "titania, calcium phosphates), with space group, cell "
             "parameters, elements, journal provenance.",
    access_method="REST OPTIMADE v1, no API key; GET "
                  "https://www.crystallography.net/cod/optimade/v1/structures",
    update_frequency="Continuous COD deposits (published structures)",
    rate_limits="None published; light paging discipline (page_limit<=10)",
    licensing="Open data (COD terms; CC0-style deposit policy)",
    primary_or_secondary="PRIMARY",
    freshness="Structure records are publication-static",
    known_gaps="Crystallography measures matter, not devices: no impurity "
               "profiles, no device-grade processing states, no "
               "biocompatibility. PROPERTY_DATA only — implant "
               "suitability NOT_ESTABLISHED_BY_THIS_SOURCE (see "
               "materials_policy.py).",
    provenance_method="Query + COD entry id + raw payload sha256 into "
                      "hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.materials:CodOptimadeConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="nist_webbook",
    name="NIST Chemistry WebBook",
    authority_role=["MATERIALS"],
    coverage="Authoritative NIST thermophysical property reference data "
             "(species pages by name: CAS registry number, formula, "
             "molecular weight, available property sections incl. "
             "condensed-phase thermochemistry).",
    access_method="REST (HTML pages), no API key; GET "
                  "https://webbook.nist.gov/cgi/cbook.cgi?Name=<q>&Units=SI",
    update_frequency="Periodic NIST releases",
    rate_limits="None published; single-page probes only",
    licensing="Public domain (NIST terms)",
    primary_or_secondary="PRIMARY",
    freshness="Reference data releases",
    known_gaps="Chemical-species scope: implant ceramics/oxides and "
               "elements covered; engineering alloys and polymers "
               "(Ti-6Al-4V, PEEK, UHMWPE) out of scope as multi-component "
               "solids. PROPERTY_DATA only — implant suitability "
               "NOT_ESTABLISHED_BY_THIS_SOURCE (materials_policy.py).",
    provenance_method="Query + CAS id (or match slug) + raw HTML sha256 "
                      "into hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.materials:NistWebbookConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="materials_project",
    name="Materials Project",
    authority_role=["MATERIALS"],
    coverage="Computed materials properties (DFT) for inorganic compounds.",
    access_method="REST OPTIMADE v1 with API key (X-API-KEY header; key "
                  "stays out of URLs and the custody log)",
    update_frequency="Periodic dataset releases",
    rate_limits="Key-tier dependent",
    licensing="Open data (Materials Project terms); API key required",
    primary_or_secondary="SECONDARY",
    freshness="Periodic",
    known_gaps="Connector IMPLEMENTED (connectors/materials.py). Measured "
               "2026-08-29: HTTP 403 'IP address or ASN has been "
               "(temporarily) blocked' — cloud ASN blocked before "
               "credential evaluation. Unlock requires BOTH a "
               "provisioned MATERIALS_PROJECT_API_KEY in .env.keys AND "
               "an unblocked egress IP. COMPUTATIONAL evidence class; "
               "PROPERTY_DATA only — implant suitability NOT established.",
    provenance_method="Query + material id + payload sha256 into retrieval "
                      "log",
    connector="discovery_fabric.source_registry.connectors.materials:MaterialsProjectConnector",
    auth_requires=["MATERIALS_PROJECT_API_KEY (not provisioned)",
                   "unblocked egress IP (ASN currently blocked)"],
    metered_quota=None,
))

# ---------------------------------------------------------------------------
# STANDARDS
# ---------------------------------------------------------------------------

_register(_src(
    source_id="fda_recognized_standards",
    name="FDA Recognized Consensus Standards Database",
    authority_role=["STANDARDS"],
    coverage="Consensus standards (ISO/IEC/ASTM/...) recognized by FDA for "
             "regulatory submissions, with recognition numbers and "
             "supplemental sheet info.",
    access_method="Web application (accessdata.fda.gov); health probe "
                  "measured HTTP 503 at measurement time — integration "
                  "state measured, not assumed",
    update_frequency="Periodic (FDA updates)",
    rate_limits="n/a (web app)",
    licensing="Public data (FDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Periodic",
    known_gaps="NO CONNECTOR YET: the search application returned 503 at "
               "probe time (likely bot protection); no published JSON API. "
               "Honest gap — standards role remains uncovered until an "
               "integration path is measured working.",
    provenance_method="Planned: recognition record + payload sha256",
    connector=NO_CONNECTOR,
    auth_requires=[],
))

_register(_src(
    source_id="iso_catalogue",
    name="ISO standards catalogue",
    authority_role=["STANDARDS"],
    coverage="ISO standard designations, scopes, status.",
    access_method="No public API measured (ISO OBP is a web app)",
    update_frequency="Continuous",
    rate_limits="n/a",
    licensing="Copyrighted metadata; catalogue browse public",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="NO CONNECTOR.",
    provenance_method="Planned",
    connector=NO_CONNECTOR,
    auth_requires=[],
))

_register(_src(
    source_id="astm_standards",
    name="ASTM standards catalogue",
    authority_role=["STANDARDS"],
    coverage="ASTM standard designations and titles.",
    access_method="No public API measured (web catalogue only)",
    update_frequency="Continuous",
    rate_limits="n/a",
    licensing="Copyrighted metadata; titles browse public",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="NO CONNECTOR.",
    provenance_method="Planned",
    connector=NO_CONNECTOR,
    auth_requires=[],
))

# ---------------------------------------------------------------------------
# REGULATORY (EU) — EUDAMED
# ---------------------------------------------------------------------------

_register(_src(
    source_id="eudamed",
    name="European Database on Medical Devices (EUDAMED)",
    authority_role=["REGULATORY", "DEVICE_IDENTITY"],
    coverage="EU device registrations, certificates, SRN/actor records "
             "across the six MDR modules.",
    access_method="Public web modules measured reachable (HTML); "
                  "machine API requires European Commission access "
                  "agreement — NOT integrated",
    update_frequency="Continuous",
    rate_limits="n/a (web)",
    licensing="Public data (EC terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="NO CONNECTOR: anonymous access is browse-only; the "
               "directive's own qualifier 'where legally/technically "
               "accessible' is measured NOT satisfied for machine access "
               "from this environment.",
    provenance_method="Planned: module record + payload sha256",
    connector=NO_CONNECTOR,
    auth_requires=["EC access agreement (not provisioned)"],
))

# ---------------------------------------------------------------------------
# MANUFACTURING / COMMERCIAL — honest empty roles
# ---------------------------------------------------------------------------

_register(_src(
    source_id="manufacturing_process_sources",
    name="(role placeholder) manufacturing & process evidence",
    authority_role=["MANUFACTURING"],
    coverage="None integrated. The directive itself grades this role "
             "'insufficient'. No public manufacturing-process API measured "
             "in this environment.",
    access_method="none",
    update_frequency="n/a",
    rate_limits="n/a",
    licensing="n/a",
    primary_or_secondary="n/a",
    freshness="n/a",
    known_gaps="ROLE UNCOVERED: no candidate source with an open, "
               "machine-accessible API measured. Remediation: licensed "
               "corpora (SEMI, IPC), standards bodies, supplier "
               "capability datasets — all require external agreements.",
    provenance_method="none",
    connector=NO_CONNECTOR,
    auth_requires=[],
))

_register(_src(
    source_id="commercial_product_sources",
    name="(role placeholder) commercial & product reality",
    authority_role=["COMMERCIAL"],
    coverage="None integrated. Procurement/company/product reality data "
             "(directive grade: 'insufficient').",
    access_method="none",
    update_frequency="n/a",
    rate_limits="n/a",
    licensing="n/a",
    primary_or_secondary="n/a",
    freshness="n/a",
    known_gaps="ROLE UNCOVERED: no open machine-accessible procurement or "
               "product-reality API measured. Remediation: licensed market "
               "intelligence or public tenders crawlers — external "
               "agreements required.",
    provenance_method="none",
    connector=NO_CONNECTOR,
    auth_requires=[],
))


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "source_id", "name", "authority_role", "coverage", "access_method",
    "update_frequency", "rate_limits", "licensing", "primary_or_secondary",
    "freshness", "known_gaps", "provenance_method", "health_status",
]


def get_source(source_id: str) -> Dict[str, Any]:
    if source_id not in SOURCE_REGISTRY:
        raise KeyError(f"source {source_id!r} not in SOURCE_REGISTRY")
    return SOURCE_REGISTRY[source_id]


def sources_for_role(role: str) -> List[Dict[str, Any]]:
    return [s for s in SOURCE_REGISTRY.values() if role in s["authority_role"]]


def apply_measured_statuses(measured: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Overlay MEASURED health statuses onto the registry (health runner use).

    Refuses any status not in the measured vocabulary, and refuses to mark
    a source LIVE if it has no connector — LIVE is only possible for a
    source whose connector exists and passed the 7-step chain.
    """
    out = {}
    for sid, status in measured.items():
        if sid not in SOURCE_REGISTRY:
            raise KeyError(f"measured status for unknown source {sid!r}")
        if status not in MEASURED_STATUSES:
            raise ValueError(f"status {status!r} not in {sorted(MEASURED_STATUSES)}")
        rec = dict(SOURCE_REGISTRY[sid])
        if status == "LIVE" and not rec["connector"]:
            raise ValueError(
                f"source {sid!r} has no connector; LIVE is not assertable "
                "(Art. XXI — README mentions are not integration)"
            )
        rec["health_status"] = status
        out[sid] = rec
    # sources not in the measured map keep NOT_MEASURED
    for sid, rec in SOURCE_REGISTRY.items():
        if sid not in out:
            r = dict(rec)
            r["health_status"] = NOT_MEASURED
            out[sid] = r
    return out


def validate_registry() -> List[str]:
    """Structural validation; returns list of violations (empty = valid)."""
    from discovery_fabric.source_registry.roles import validate_role

    violations = []
    for sid, rec in SOURCE_REGISTRY.items():
        for f in REQUIRED_FIELDS:
            if f not in rec or rec[f] in (None, ""):
                if not (f == "health_status"):  # health_status has NOT_MEASURED default
                    violations.append(f"{sid}: missing/empty field {f}")
        if sid != rec["source_id"]:
            violations.append(f"{sid}: source_id mismatch {rec['source_id']}")
        if not rec["authority_role"]:
            violations.append(f"{sid}: no authority_role")
        for role in rec["authority_role"]:
            try:
                validate_role(role)
            except ValueError as e:
                violations.append(f"{sid}: {e}")
        if rec["health_status"] == "LIVE" and not rec["connector"]:
            violations.append(f"{sid}: LIVE without connector")
    return violations

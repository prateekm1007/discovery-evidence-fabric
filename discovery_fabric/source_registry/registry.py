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
# Mechanically honest vocabulary (CEO directive 2026-08-30 #5):
# LIVE / DEGRADED / BLOCKED / NOT_INTEGRATED. UNAVAILABLE is accepted on
# input as the pre-rename legacy label for BLOCKED (status_model.
# LEGACY_VOCABULARY_MAP, Art. XI) so historical overlays remain loadable.
MEASURED_STATUSES = {"LIVE", "DEGRADED", "BLOCKED", "UNAVAILABLE",
                     "NOT_INTEGRATED"}
# statuses this module EMITS (legacy label never emitted again)
EMITTED_STATUSES = {"LIVE", "DEGRADED", "BLOCKED", "NOT_INTEGRATED"}

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
               "/denovo returned 404; /other/deNovo.json 404 (2026-08-30). "
               "CSV download route measured 2026-08-30: fda.gov dataset "
               "page answers HTTP 401 bot-protection from this egress "
               "ASN — route blocked HERE, dataset exists. Integration "
               "requires the CSV pipeline from an unblocked egress — "
               "honest gap, recorded, not silently claimed.",
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
               "measured machine API. Re-measured 2026-08-30: legacy "
               "RESTfulAPI.svc redirects to the new SPA platform; "
               "trialsearch.who.int/api/v1 and /api/v2 return 404 — legacy "
               "API RETIRED, replacement is an undocumented SPA backend. "
               "Using it would be brittle and against portal intent. "
               "Honest gap; CLINICAL role remains covered LIVE by "
               "clinicaltrials_gov.",
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

# ---------------------------------------------------------------------------
# OPEN DISCOVERY / OA / REPOSITORIES / THESES  (R409 retrieval-fabric round:
# measured live 2026-09-05 from this egress — see connectors/open_discovery.py)
# ---------------------------------------------------------------------------

_register(_src(
    source_id="doaj",
    name="Directory of Open Access Journals (DOAJ article search)",
    authority_role=["SCIENTIFIC"],
    coverage="Open-access journal articles from journals admitted to DOAJ "
             "(peer-reviewed OA, no-APC condition at admission); journal and "
             "article metadata with full-text links; OAI-PMH available.",
    access_method="REST JSON, no key; GET https://doaj.org/api/v2/search/"
                  "articles/{query}; OAI-PMH at https://doaj.org/oai.article",
    update_frequency="Continuous (journal/article applications)",
    rate_limits="Polite use; no published hard limit measured",
    licensing="Open metadata (CC-BY-SA for DOAJ metadata; article metadata "
              "as submitted)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="Only DOAJ-admitted journals — absence is not absence of the "
               "science (Art. XXV); article metadata as journal-declared.",
    provenance_method="Query + DOAJ article id + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.open_discovery:DoajConnector",
    auth_requires=[],
))

_register(_src(
    source_id="unpaywall",
    name="Unpaywall (OA full-text location resolution per DOI)",
    authority_role=["SCIENTIFIC"],
    coverage="For a known DOI: legally-open full-text locations (repository, "
             "publisher page, hybrid), OA status and license. A RESOLUTION "
             "service, not a discovery index.",
    access_method="REST JSON, no key (contact email required); GET "
                  "https://api.unpaywall.org/v2/{doi}?email=",
    update_frequency="Continuous",
    rate_limits="Polite; 100k calls/day documented for contact-email users",
    licensing="Open data (Unpaywall/OurResearch terms; underlying links from "
              "Crossref + repository + publisher pages)",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="Metadata upstream derives from Crossref; a DOI absent from "
               "Unpaywall means Unpaywall has no OA-location record for it "
               "(404 -> EMPTY), never that the work does not exist.",
    provenance_method="Queried DOI + best_oa_location + raw payload sha256 "
                      "into retrieval log",
    connector="discovery_fabric.source_registry.connectors.open_discovery:UnpaywallConnector",
    auth_requires=["UNPAYWALL_EMAIL (placeholder used when not provisioned)"],
))

_register(_src(
    source_id="datacite",
    name="DataCite DOI registry (repositories, datasets, theses)",
    authority_role=["SCIENTIFIC"],
    coverage="DOIs registered by data centres and institutional/subject "
             "repositories: Zenodo, institutional repositories, datasets, "
             "and dissertations (resourceTypeGeneral=Dissertation). "
             "Materially different registrant population from Crossref's "
             "publisher DOIs.",
    access_method="REST JSON, no key; GET https://api.datacite.org/dois",
    update_frequency="Continuous (registrant deposits)",
    rate_limits="Polite use; no published hard limit measured",
    licensing="Open metadata (DataCite terms; CC0 for many records)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="Only DataCite-registered DOIs — publisher-registered "
               "literature is Crossref's space; repository-declared types "
               "are unverified (Art. XXV).",
    provenance_method="Query + DOI + resourceTypeGeneral + raw payload "
                      "sha256 into retrieval log",
    connector="discovery_fabric.source_registry.connectors.open_discovery:DataciteConnector",
    auth_requires=[],
))

_register(_src(
    source_id="openaire",
    name="OpenAIRE (research repository aggregator)",
    authority_role=["SCIENTIFIC"],
    coverage="Aggregated institutional/subject repository records across "
             "Europe and beyond: publications, theses (instance-level "
             "instancetype), preprints, with hosting datasource and "
             "refereed status per instance.",
    access_method="REST JSON, no key; GET "
                  "https://api.openaire.eu/search/publications?keywords=",
    update_frequency="Continuous (aggregation cycles)",
    rate_limits="Polite use; 2 req/s documented for the search API",
    licensing="Open metadata (OpenAIRE terms; per-repository licenses vary)",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="Aggregated metadata quality varies by repository; API "
               "exposes NO server-side type filter (measured 2026-09-05: "
               "publicationtype/documenttype/instance.type -> HTTP 400), so "
               "document types are labeled post-hoc from instancetype.",
    provenance_method="Query + objIdentifier + instancetype + raw payload "
                      "sha256 into retrieval log",
    connector="discovery_fabric.source_registry.connectors.open_discovery:OpenaireConnector",
    auth_requires=[],
))

_register(_src(
    source_id="core",
    name="CORE (repository aggregator, independent harvest)",
    authority_role=["SCIENTIFIC"],
    coverage="Open-access research outputs harvested directly from "
             "repositories and journals: metadata, abstracts, full-text "
             "links; independent harvest from OpenAIRE's aggregation.",
    access_method="REST JSON, anonymous access measured working; GET "
                  "https://api.core.ac.uk/v3/search/works (CORE_API_KEY "
                  "header upgrades the tier when provisioned)",
    update_frequency="Continuous (harvest cycles)",
    rate_limits="Anonymous tier measured live 2026-09-05; per-query quotas "
                "may rate-limit without notice — every 429 is recorded "
                "honestly as RATE_LIMITED (Art. XXI.3)",
    licensing="Open metadata (CORE terms; content licenses vary by "
              "repository)",
    primary_or_secondary="SECONDARY",
    freshness="Continuous",
    known_gaps="Relevance ranking for long natural-language queries is weak "
               "(measured: a 7-word mechanism query matched 9.7M works) — "
               "the fabric sends SHORT keyword-form queries only; "
               "document_type is repository-declared and unverified.",
    provenance_method="Query + CORE work id + raw payload sha256 into "
                      "retrieval log",
    connector="discovery_fabric.source_registry.connectors.open_discovery:CoreConnector",
    auth_requires=["CORE_API_KEY (optional; anonymous tier measured working)"],
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
    known_gaps="Connector IMPLEMENTED (connectors/materials.py). CEO "
               "provisioned MATERIALS_PROJECT_API_KEY on 2026-08-30 "
               "(stored in .env.keys, header-auth). Re-measured 2026-08-30 "
               "WITH key: still HTTP 403 'IP address or ASN has been "
               "(temporarily) blocked' — provider-side egress ASN block, "
               "key is NOT the blocker. Unlock requires the ASN block to "
               "clear (provider says temporary) or an unblocked egress. "
               "COMPUTATIONAL evidence class; PROPERTY_DATA only — "
               "implant suitability NOT established.",
    provenance_method="Query + material id + payload sha256 into retrieval "
                      "log",
    connector="discovery_fabric.source_registry.connectors.materials:MaterialsProjectConnector",
    auth_requires=["MATERIALS_PROJECT_API_KEY (PROVISIONED 2026-08-30 by CEO)",
                   "unblocked egress IP (ASN block outstanding 2026-08-30)"],
    metered_quota=None,
))

# ---------------------------------------------------------------------------
# STANDARDS
# ---------------------------------------------------------------------------

_register(_src(
    source_id="fda_recognized_standards",
    name="FDA Recognized Consensus Standards Database",
    authority_role=["STANDARDS"],
    coverage="Consensus standards (ISO/IEC/ASTM/AAMI/...) recognized by "
             "FDA for regulatory submissions: recognition number, "
             "specialty task group area (device area), extent of "
             "recognition (Complete/Partial), organization, designation "
             "and title (the engineering purpose).",
    access_method="REST (HTML catalog pages), no API key: GET "
                  "results.cfm?start_search=1&pgnum=N (PAGE_BUDGET=3 "
                  "pages, 100 rows each) then CLIENT-SIDE filter on "
                  "designation+title. Server-side keyword filtering "
                  "measured BROKEN 2026-08-30 (keyword=/title=/stdsgn= "
                  "all ignored — identical first page returned); the "
                  "query-differentiation check in the QUERY_RELEVANCE "
                  "battery caught the connector shipping catalog rows "
                  "as if query-filtered.",
    update_frequency="Periodic (FDA recognition updates)",
    rate_limits="None published; single-page keyword probes",
    licensing="Public data (FDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Recognition list current at query time",
    known_gaps="Server-side keyword filter BROKEN (measured 2026-08-30): "
               "query is applied client-side over a 3-page (300-row) "
               "newest-first catalog window — a definitive EMPTY means "
               "'not in the fetched window', NEVER 'not recognized'. "
               "List-level records carry extent-of-recognition but not "
               "the partial-recognition rationale (on the FDA detail "
               "page). Specialty task group area is a device-area "
               "grouping, not product-code-level typing.",
    provenance_method="Query + FDA recognition number + raw HTML sha256 "
                      "into hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.standards:FdaRecognizedStandardsConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="ecfr_title21",
    name="eCFR Title 21 — Food and Drugs (Subchapter H: Medical Devices)",
    authority_role=["STANDARDS"],
    coverage="Codified US regulation for medical devices: device "
             "classification parts by specialty panel (862-892), QMSR "
             "part 820 (ISO 13485 incorporated by reference at "
             "§ 820.7), MDR 803, recall authority 810, IDE 812, PMA 814, "
             "UDI 830. Structure records + section full text.",
    access_method="REST JSON/XML, no API key; GET "
                  "www.ecfr.gov/api/versioner/v1/...",
    update_frequency="Daily (eCFR issue dates)",
    rate_limits="None published; light query discipline",
    licensing="Public domain (US government work)",
    primary_or_secondary="PRIMARY",
    freshness="Issue-date pinned per query (2026-08-27 measured)",
    known_gaps="Incorporated standard texts (e.g. ISO 13485 body) are "
               "NOT in eCFR — only the incorporation by reference is. "
               "Structure records do not carry section text (fetch via "
               "section query). Measured LIVE 2026-08-29 (part 888 -> "
               "111 sections; § 820.1 full text).",
    provenance_method="Query + CFR section identifier + raw payload "
                      "sha256 (structure JSON or section XML) into "
                      "hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.standards:EcfrTitle21Connector",
    auth_requires=[],
    metered_quota=None,
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
               "from this environment. Re-measured 2026-08-30: /api/ and "
               "public-UDI paths return the SPA shell (HTML) or redirect "
               "to the app — no unauthenticated JSON route exists; the "
               "documented EUDAMED API requires EU-login registration.",
    provenance_method="Planned: module record + payload sha256",
    connector=NO_CONNECTOR,
    auth_requires=["EC access agreement (not provisioned)"],
))

# ---------------------------------------------------------------------------
# MANUFACTURING / COMMERCIAL — honest empty roles
# ---------------------------------------------------------------------------

_register(_src(
    source_id="fda_pma_supplements",
    name="FDA PMA manufacturing/process-change supplements (openFDA)",
    authority_role=["MANUFACTURING"],
    coverage="PMA supplement records evidencing FDA-reviewed "
             "manufacturing changes: process changes (manufacturer/"
             "sterilizer/packager/supplier), design/components/"
             "specifications/material changes, supplement types "
             "(Real-Time, 30-Day Notice, Panel-Track) with decision "
             "codes. Measured: 56,995 supplement records exist.",
    access_method="REST JSON, no API key; GET https://api.fda.gov/device/pma.json",
    update_frequency="openFDA PMA dataset refreshed weekly per FDA docs",
    rate_limits="240 requests/min without key (per openFDA docs)",
    licensing="Open data (openFDA terms)",
    primary_or_secondary="PRIMARY",
    freshness="Weekly refresh; supplements appear after FDA decision",
    known_gaps="PMA-class devices only (510(k)-class manufacturing "
               "changes not represented); supplement reason is FDA's "
               "categorical label, not the full engineering content. "
               "Measured LIVE 2026-08-29.",
    provenance_method="Query + PMA/supplement numbers + raw payload "
                      "sha256 into hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.manufacturing:PmaManufacturingSupplementConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="manufacturing_literature",
    name="Manufacturing process literature (EuropePMC, 8-process taxonomy)",
    authority_role=["MANUFACTURING"],
    coverage="Peer-reviewed process evidence for the directive's 8 "
             "processes (extrusion, injection molding, machining, "
             "additive manufacturing, laser processing, coatings, "
             "microfabrication, sterilization) queried through the "
             "medical-device literature, with exact-span constraint/"
             "risk/verification sentence extraction.",
    access_method="REST JSON, no API key; GET "
                  "www.ebi.ac.uk/europepmc/webservices/rest/search",
    update_frequency="Continuous (EuropePMC refresh cycle)",
    rate_limits="None published; light paging discipline",
    licensing="Open data (EuropePMC terms; abstracts per publisher policy)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="Abstract spans are exact quotes but may omit the "
               "study's full constraint data; process classification is "
               "title/abstract grammar (records matching no taxonomy "
               "term carry process=None). Measured LIVE 2026-08-29.",
    provenance_method="Query + EuropePMC id + raw payload sha256 into "
                      "hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.manufacturing:ManufacturingLiteratureConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="gudid_sterilization",
    name="GUDID sterilization fields on marketed devices (openFDA UDI)",
    authority_role=["MANUFACTURING"],
    coverage="Device-level sterilization evidence from GUDID: is_sterile, "
             "is_sterilization_prior_use, sterilization_methods (free "
             "text, e.g. 'Moist Heat or Steam Sterilization'). "
             "Measured: 5,083,929 UDI records carry the sterilization "
             "block.",
    access_method="REST JSON, no API key; GET https://api.fda.gov/device/udi.json",
    update_frequency="GUDID submissions (continuous; openFDA refresh weekly)",
    rate_limits="240 requests/min without key (per openFDA docs)",
    licensing="Open data (openFDA terms); fields are manufacturer-declared",
    primary_or_secondary="PRIMARY",
    freshness="Weekly refresh",
    known_gaps="Declared method is not sterilization VALIDATION "
               "(validation evidence lives in ISO 17665/11135/11137 "
               "families via the STANDARDS role); free-text methods are "
               "labeler wording. Measured LIVE 2026-08-29.",
    provenance_method="Query + public_device_record_key + raw payload "
                      "sha256 into hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.manufacturing:GudidSterilizationConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="gudid_commercial",
    name="GUDID commercial layer (via openFDA device/udi.json)",
    authority_role=["COMMERCIAL"],
    coverage="Marketed-product reality with FDA provenance: brand name, "
             "company + labeler DUNS, product codes and GMDN category "
             "terms, commercial distribution status (In/Not in "
             "Commercial Distribution) and end date, device counts, "
             "kit/combination-product flags.",
    access_method="REST JSON, no API key; GET https://api.fda.gov/device/udi.json",
    update_frequency="GUDID submissions (continuous; openFDA refresh weekly)",
    rate_limits="240 requests/min without key (per openFDA docs)",
    licensing="Open data (openFDA terms); fields are manufacturer-declared",
    primary_or_secondary="PRIMARY",
    freshness="Weekly refresh; record-version lag possible",
    known_gaps="PRICING_PROCUREMENT_SIGNAL: NOT covered — no open source "
               "with defensible provenance (licensed market intelligence "
               "required; honest gap). Competitive mechanism is "
               "graph-derived (device->patent edges), never asserted from "
               "a commercial source. US-market scope only. Measured LIVE "
               "2026-08-29.",
    provenance_method="Query + public_device_record_key + raw payload "
                      "sha256 into hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.commercial:GudidCommercialConnector",
    auth_requires=[],
    metered_quota=None,
))

# ---------------------------------------------------------------------------
# GOVERNMENT TECHNICAL REPORTS + NON-MEDICAL FAILURES
# (CEO Toscanini directive 2026-08-30 — free/open priority sources; all
#  endpoints measured live before registration, this session)
# ---------------------------------------------------------------------------

_register(_src(
    source_id="nasa_ntrs",
    name="NASA Technical Reports Server (NTRS)",
    authority_role=["SCIENTIFIC"],
    coverage="Aerospace, aeronautics, materials, propulsion, and space-"
             "science R&D citations and reports (NASA + NACA eras), "
             "including failure analyses and lessons-learned.",
    access_method="REST JSON, no key: GET https://ntrs.nasa.gov/api/"
                  "citations/search?q=...&page.size=N (measured 200)",
    update_frequency="Continuous (new report releases and retro-digitized "
                     "NACA-era records)",
    rate_limits="Public API; no published hard limit measured; modest "
                "page sizes used",
    licensing="Open data (NASA/US-government works; NTRS terms — export-"
              "control metadata carried per record)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous releases",
    known_gaps="Report-grade evidence, not peer-review grade. Negative "
               "findings/lessons-learned present but NOT structurally "
               "flagged. Full text sometimes distribution-restricted; the "
               "connector indexes metadata + abstract only.",
    provenance_method="Query + NTRS id + raw payload sha256 into "
                      "hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.govtech_reports:NasaNtrsConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="doe_osti",
    name="DOE Office of Scientific and Technical Information (OSTI)",
    authority_role=["SCIENTIFIC"],
    coverage="Energy, batteries, materials, nuclear, and fundamental-"
             "science research outputs funded by DOE (journal articles, "
             "technical reports, datasets).",
    access_method="REST JSON, no key: GET https://www.osti.gov/api/v1/"
                  "records?query=...&rows=N (measured 200, native JSON "
                  "array; note: api.osti.gov does not resolve from this "
                  "egress; format=xml+%-encoding measured flip-flopping)",
    update_frequency="Continuous (as DOE-funded outputs are submitted)",
    rate_limits="Public API; courtesy-limited",
    licensing="Open data (OSTI/US-government terms; metadata freely "
              "redistributable)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="DOE-funded scope only — absence of an OSTI record is not "
               "absence of the research. Negative findings not structurally "
               "flagged.",
    provenance_method="Query + OSTI id + raw payload sha256 into "
                      "hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.govtech_reports:DoeOstiConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="arxiv",
    name="arXiv preprint server",
    authority_role=["SCIENTIFIC"],
    coverage="Preprints in physics, mathematics, CS, quantitative biology, "
             "statistics, engineering; mechanism evidence at the research "
             "frontier.",
    access_method="REST Atom XML, no key: GET https://export.arxiv.org/api/"
                  "query?search_query=all:...&max_results=N (measured 200 "
                  "over https; http variant measured 429)",
    update_frequency="Continuous (new submissions announce daily)",
    rate_limits="Courtesy interval ~3 seconds between calls (enforced "
                "client-side); burst probing measured 429",
    licensing="Open access (arXiv terms; attribution required; licenses "
              "vary per article)",
    primary_or_secondary="PRIMARY",
    freshness="Daily announcement cycle",
    known_gaps="PREPRINT evidence class — NOT peer-reviewed; versions and "
               "withdrawals exist. Coverage skew: physics/math/CS/quant-bio.",
    provenance_method="Query + arxiv id + raw payload sha256 into "
                      "hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.scientific:ArxivConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="nhtsa_recalls",
    name="NHTSA vehicle-recall campaigns",
    authority_role=["RECALL"],
    coverage="US vehicle safety-recall campaigns by make/model/year with "
             "component, defect summary, consequence, and remedy. First "
             "NON-MEDICAL failure-evidence source (transport domain).",
    access_method="REST JSON, no key: GET https://api.nhtsa.gov/recalls/"
                  "recallsByVehicle?make&model&modelYear (measured 200; "
                  "query grammar 'make|model|year' — parameterized "
                  "endpoint, not free text)",
    update_frequency="Continuous (recall campaign publication)",
    rate_limits="Public API; no published hard limit measured",
    licensing="Open data (NHTSA/US-government terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="US vehicle market only. A recall is an acknowledged "
               "defect, NOT an incidence rate; affected-unit counts are "
               "not field-failure counts (Art. XXI.5-analog carried per "
               "record). No free-text search — query ladder must target "
               "make/model/year triples. NTSB investigations remain a "
               "route-blocked gap (CAROL API paths serve HTML, measured "
               "2026-08-30).",
    provenance_method="Query (make|model|year) + NHTSA campaign number + "
                      "raw payload sha256 into hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.nonmedical_failure:NhtsaRecallConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="nhtsa_complaints",
    name="NHTSA ODI vehicle-owner complaints",
    authority_role=["ADVERSE_EVENT"],
    coverage="US vehicle owner complaints (ODI) by make/model/year with "
             "component codes, crash/fire flags, injury/death counts, "
             "incident dates, and complainant narratives. Automotive "
             "ADVERSE_EVENT analog of MAUDE — measured LIVE 2026-08-30 "
             "(268 records for toyota|camry|2020 at probe).",
    access_method="REST JSON, no key: GET https://api.nhtsa.gov/complaints/"
                  "complaintsByVehicle?make&model&modelYear (query grammar "
                  "'make|model|year')",
    update_frequency="Continuous (complaint ingestion)",
    rate_limits="Public API; no published hard limit measured",
    licensing="Open data (NHTSA/US-government terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="VOLUNTARY unverified reports: causality NOT established, "
               "counts are NOT incidence (denominator absent) — Art. XXI.5 "
               "caps generalized and attached per record. Narratives are "
               "complainant-authored. US market only. No free-text search.",
    provenance_method="Query (make|model|year) + ODI number + raw payload "
                      "sha256 into hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.failure_universe:NhtsaComplaintConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="cpsc_recalls",
    name="CPSC SaferProducts consumer-product recalls",
    authority_role=["RECALL", "COMMERCIAL"],
    coverage="US Consumer Product Safety Commission recalls with hazard "
             "classes, product categories (incl. consumer electronics), "
             "injury lists, remedies, manufacturers, and countries — "
             "measured LIVE 2026-08-30 (141 records in a 2.5-month "
             "window). Covers ELECTRONICS + consumer-product failures.",
    access_method="REST JSON, no key: GET https://www.saferproducts.gov/"
                  "RestWebServices/Recall?format=json&RecallDateStart="
                  "YYYY-MM-DD (query grammar = ISO start date)",
    update_frequency="Continuous (recall publication)",
    rate_limits="Public API; no published hard limit measured",
    licensing="Open data (CPSC/US-government terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="A recall is an acknowledged product hazard, NOT an "
               "incidence rate; injury lists are associated complaints, "
               "not a census. CPSC jurisdiction = consumer products only "
               "(no food/drugs/vehicles/workplace). Date-window grammar — "
               "no free-text search.",
    provenance_method="Query (date window) + RecallNumber + raw payload "
                      "sha256 into hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.failure_universe:CpscRecallConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="usgs_earthquakes",
    name="USGS earthquake events (FDSN)",
    authority_role=["HAZARD_EVENT"],
    coverage="Instrument-measured seismic events M>=4.5 worldwide with "
             "magnitude, location, depth, felt reports, alert level — "
             "hazard-EXPOSURE input for infrastructure-resilience "
             "problems. Measured LIVE 2026-08-30.",
    access_method="REST GeoJSON, no key: GET https://earthquake.usgs.gov/"
                  "fdsnws/event/1/query?format=geojson&minmagnitude=4.5"
                  "&starttime=YYYY-MM-DD",
    update_frequency="Continuous (event detection/revision)",
    rate_limits="Public API; documented courtesy limits, none hit",
    licensing="Open data (USGS/US-government terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="Hazard events are NOT engineering-failure records: "
               "structural consequences require engineering corpora. "
               "Catalog completeness varies with magnitude/region; "
               "preliminary magnitudes revise.",
    provenance_method="Query (start date + magnitude floor) + USGS event "
                      "id + raw payload sha256 into hash-chained log",
    connector="discovery_fabric.source_registry.connectors.failure_universe:UsgsEarthquakeConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="fra_rail_accidents",
    name="FRA rail equipment accidents (Form 54)",
    authority_role=["INCIDENT"],
    coverage="US rail equipment accidents/incidents reported under 49 CFR "
             "225: cause codes (track/human/equipment/signal), accident "
             "type, derailed-car counts, fatalities/injuries, speed — "
             "measured LIVE 2026-08-30 via USDOT Socrata "
             "(data.transportation.gov resource 85tf-25kj).",
    access_method="REST JSON (Socrata), no key: GET https://data."
                  "transportation.gov/resource/85tf-25kj.json"
                  "?$limit&$order&$where=date>=YYYY-MM-DD",
    update_frequency="Periodic dataset refresh (FRA safety data)",
    rate_limits="Socrata anonymous tier; throttling possible",
    licensing="Open data (USDOT/US-government terms)",
    primary_or_secondary="PRIMARY",
    freshness="Periodic",
    known_gaps="Carrier-reported above FRA reporting thresholds — "
               "below-threshold events absent; cause codes are "
               "classifications of initial reports, NOT proven root "
               "causes; US rail only. PHMSA pipeline + hazmat Socrata "
               "datasets measured NON-TABULAR for anonymous access "
               "(2026-08-30) — energy-incident coverage stays a gap.",
    provenance_method="Query (date floor) + railroad/accident number + "
                      "raw payload sha256 into hash-chained log",
    connector="discovery_fabric.source_registry.connectors.failure_universe:FraRailAccidentConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="nih_reporter",
    name="NIH RePORTER (funded research projects)",
    authority_role=["EXPERIMENT"],
    coverage="NIH-funded biomedical research PROJECT records: what was "
             "attempted, by which organization, over which period, with "
             "declared objectives and abstracts — the attempt-outcome "
             "universe beyond publication bias. Measured LIVE 2026-08-30 "
             "(POST v2/projects/search, real appl_id records).",
    access_method="REST JSON POST, no key: https://api.reporter.nih.gov"
                  "/v2/projects/search (measured 200)",
    update_frequency="Continuous (RePORTER refreshes with reporting "
                     "cycles)",
    rate_limits="Public API; no key; modest page sizes used",
    licensing="Open data (NIH/US-government terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="ATTEMPT records, not outcome proof: a funded project is "
               "an attempt with declared objectives, never evidence the "
               "objective was achieved. NIH-funded biomedical scope only "
               "— absence of a RePORTER project is not evidence a "
               "technology was never researched. Non-medical experiment "
               "coverage (NSF awards, CORDIS) measured BLOCKED from this "
               "egress 2026-08-30 (nsf_awards: 404/403; cordis: HTML app "
               "shell) and stays an honest gap.",
    provenance_method="Query + appl_id + raw payload sha256 into "
                      "hash-chained retrieval log",
    connector="discovery_fabric.source_registry.connectors.research_attempts:NihReporterConnector",
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="nsf_awards",
    name="NSF Award Search (non-medical research attempts)",
    authority_role=["EXPERIMENT"],
    coverage="NSF-funded engineering/physical-science research awards — "
             "the non-medial counterpart of RePORTER for what was "
             "attempted. NOT INTEGRATED: measured blocked from this "
             "egress 2026-08-30 (api.nsf.gov/api/v1/awards.json HTTP "
             "404; api.nsf.gov/services/awards.json HTTP 403 Forbidden; "
             "www.research.gov route unreachable).",
    access_method="Blocked: no anonymous API route measured from this "
                  "network (404/403/connection-failure, dated)",
    update_frequency="Continuous (provider side)",
    rate_limits="Unknown from this egress",
    licensing="Open data (NSF/US-government terms)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous (provider side)",
    known_gaps="No connector exists — measured BLOCKED (EGRESS-class "
               "signatures). NOT_INTEGRATED is the honest status; this "
               "row records the gap and the measured block evidence.",
    provenance_method="N/A (not integrated)",
    connector=None,
    auth_requires=[],
    metered_quota=None,
))

_register(_src(
    source_id="cordis_projects",
    name="EU CORDIS (framework research projects)",
    authority_role=["EXPERIMENT"],
    coverage="EU-funded research projects across ALL domains (Horizon "
             "programmes) — pan-domain attempt records incl. engineering "
             "and energy. NOT INTEGRATED: measured blocked 2026-08-30 "
             "(all API routes return the HTML application shell; "
             "data-extraction API requires registration).",
    access_method="Blocked: anonymous JSON routes absent; data-extraction "
                  "API requires registration (BLOCKED::REGISTRATION)",
    update_frequency="Continuous (provider side)",
    rate_limits="Unknown (registration-gated)",
    licensing="Open data (EU terms) — API access is registration-gated",
    primary_or_secondary="PRIMARY",
    freshness="Continuous (provider side)",
    known_gaps="No connector exists — measured BLOCKED (REGISTRATION "
               "class). EU research-attempt coverage stays an honest gap "
               "until credentials/registration are provided (CEO action).",
    provenance_method="N/A (not integrated)",
    connector=None,
    auth_requires=["CORDIS API registration (not provisioned)"],
    metered_quota=None,
))


# ---------------------------------------------------------------------------
# R399 W3: ROUTING STATES — a first-class, epistemic, REVERSIBLE layer
# ---------------------------------------------------------------------------
# Routing state is a DIFFERENT dimension from health_status:
#   health_status  = can the provider be reached at all (measured LIVE/
#                    DEGRADED/BLOCKED/NOT_INTEGRATED)
#   routing_state  = SHOULD the engine actively query this source in the
#                    run routing graph (ACTIVE / ARCHIVED_ROUTING /
#                    SUSPENDED_RELEVANCE)
# A routing state is never a silent code path: every dispatch site that
# skips a non-ACTIVE source records the state + basis + reinstatement
# criterion in the run record, and the health report carries the state
# without probing the source (no quota burn for a parked source).
# Flipping a state back to ACTIVE is a one-line registry change with a
# worklog entry — the implementation is archived IN PLACE, never deleted.

ROUTING_STATES = ("ACTIVE", "ARCHIVED_ROUTING", "SUSPENDED_RELEVANCE")

_ROUTING_STATE_OVERRIDES: Dict[str, Dict[str, Any]] = {
    # NHTSA — ARCHIVED_ROUTING (R399 W3). Measured basis: the connectors
    # grammar-gate themselves out of every non-vehicle problem
    # (NOT_QUERIED_GRAMMAR — 70 recorded grammar-mismatches vs zero
    # production-run uses in the current medical/engineering domain
    # set; only automotive problems with an extracted
    # make|model|year ever produce a real query). The current
    # production domain set has no vehicle problems: zero utility,
    # live routing complexity. The implementation (connectors,
    # grammar, limitations) stays archived in place.
    "nhtsa_recalls": {
        "routing_state": "ARCHIVED_ROUTING",
        "routing_basis": (
            "measured: NOT_QUERIED_GRAMMAR on every non-vehicle problem "
            "(70 recorded grammar mismatches, zero production-run uses "
            "in the current domain set — R399 audit W3)"),
        "reinstatement_criterion": (
            "the production domain set includes vehicle problems with "
            "extracted make|model|year parameters (flip to ACTIVE + "
            "worklog entry; connector implementation archived in place)"),
    },
    "nhtsa_complaints": {
        "routing_state": "ARCHIVED_ROUTING",
        "routing_basis": (
            "measured: NOT_QUERIED_GRAMMAR on every non-vehicle problem "
            "(70 recorded grammar mismatches, zero production-run uses "
            "in the current domain set — R399 audit W3)"),
        "reinstatement_criterion": (
            "the production domain set includes vehicle problems with "
            "extracted make|model|year parameters (flip to ACTIVE + "
            "worklog entry; connector implementation archived in place)"),
    },
    # COD (crystallography) — ARCHIVED_ROUTING (R399 W3). Measured
    # basis: EMPTY on every observed run in the audit; zero run-level
    # dispatch in the current domain set. Materials-role coverage is
    # served by nist_webbook / materials_project paths.
    "cod_optimade": {
        "routing_state": "ARCHIVED_ROUTING",
        "routing_basis": (
            "measured: EMPTY on every observed run (R399 audit W3); "
            "zero production-run dispatches in the current domain set"),
        "reinstatement_criterion": (
            "a production problem class needs crystal-structure "
            "evidence (flip to ACTIVE + worklog entry; connector "
            "implementation archived in place)"),
    },
    # DOE OSTI — SUSPENDED_RELEVANCE (R399 W3). NOT deleted: the
    # connector works; the RELEVANCE of its records is unstable (the
    # R375 measured instability — same fusion papers adjudicated
    # relevant 3 then 0 — pooled relevant-rate 0.175 before the
    # keyword-form/abstract fixes). Until the semantic reranker lands
    # (Phase P1), its records poison more than they feed synthesis-
    # feeding retrieval. Suspended with an explicit reinstatement
    # criterion, in the registry, the health report, and the worklog.
    "doe_osti": {
        "routing_state": "SUSPENDED_RELEVANCE",
        "routing_basis": (
            "measured relevance instability (R375: same fusion papers "
            "relevant 3 -> 0; pooled relevant-rate 0.175 pre-fix; "
            "DETERMINISM_GAP flagged in the R394 production audit) — "
            "records poison synthesis-feeding retrieval more than they "
            "feed it until relevance is semantically adjudicated"),
        "reinstatement_criterion": (
            "the Phase P1 semantic reranker lands (semantic relevance "
            "adjudication between query and record, replacing lexical "
            "overlap); flip to ACTIVE + a measured relevance re-run + "
            "worklog entry"),
    },
}

for _sid, _routing in _ROUTING_STATE_OVERRIDES.items():
    if _sid in SOURCE_REGISTRY:
        SOURCE_REGISTRY[_sid]["routing_state"] = _routing["routing_state"]
        SOURCE_REGISTRY[_sid]["routing_basis"] = _routing["routing_basis"]
        SOURCE_REGISTRY[_sid]["reinstatement_criterion"] = \
            _routing["reinstatement_criterion"]

for _sid, _rec in SOURCE_REGISTRY.items():
    # every source carries an explicit routing state (default ACTIVE —
    # absent means active, but the field is always present for audit)
    _rec.setdefault("routing_state", "ACTIVE")


def routing_state(source_id: str) -> str:
    """The routing state of a source (one authority; default ACTIVE)."""
    rec = SOURCE_REGISTRY.get(source_id) or {}
    return rec.get("routing_state") or "ACTIVE"


def routing_info(source_id: str) -> Dict[str, Any]:
    """The full routing block (state, basis, reinstatement criterion) —
    the exact record dispatch sites and the health report embed."""
    rec = SOURCE_REGISTRY.get(source_id) or {}
    return {
        "source_id": source_id,
        "routing_state": routing_state(source_id),
        "routing_basis": rec.get("routing_basis"),
        "reinstatement_criterion": rec.get("reinstatement_criterion"),
    }


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

# R409 retrieval-fabric round: investigated sources measured BLOCKED from
# this egress (2026-09-05). Recorded honestly with NO_CONNECTOR (Art.
# XXV/Art. XXI.3): a blocked source is a recorded gap, never silent
# omission, and never counted as integrated.

_register(_src(
    source_id="zenodo",
    name="Zenodo (open research repository, CERN)",
    authority_role=["SCIENTIFIC"],
    coverage="Open repository for research data, reports, preprints and "
             "EU outputs; records also discoverable via DataCite DOIs.",
    access_method="REST JSON, no key; GET https://zenodo.org/api/records",
    update_frequency="Continuous",
    rate_limits="n/a",
    licensing="Open repository (per-record licenses)",
    primary_or_secondary="PRIMARY",
    freshness="Continuous",
    known_gaps="MEASURED 2026-09-05 from this egress: HTTP 403 network-side "
               "block (3 attempts, all 403) — the fabric records this state "
               "honestly; Zenodo-deposited DOIs remain discoverable through "
               "the datacite registrant lane.",
    provenance_method="Query + record id + raw payload sha256 into retrieval "
                      "log (when a connector is ever wired)",
    connector=NO_CONNECTOR,
    auth_requires=[],
))

_register(_src(
    source_id="ndltd",
    name="NDLTD Global ETD Search (theses/dissertations)",
    authority_role=["SCIENTIFIC"],
    coverage="Global electronic theses and dissertations aggregation.",
    access_method="REST; http://search.ndltd.org/api/search",
    update_frequency="Unknown",
    rate_limits="Unknown",
    licensing="Per-institution",
    primary_or_secondary="SECONDARY",
    freshness="Unknown",
    known_gaps="MEASURED 2026-09-05 from this egress: HTTP 503 service "
               "unavailable (2 attempts) — recorded honestly; thesis "
               "coverage is served by the datacite/openaire/core/crossref "
               "lanes in the retrieval fabric.",
    provenance_method="Query + record id + raw payload sha256 into retrieval "
                      "log (when a connector is ever wired)",
    connector=NO_CONNECTOR,
    auth_requires=[],
))


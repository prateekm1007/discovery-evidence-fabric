#!/usr/bin/env python3
"""Build the OPEN CORPORA REGISTRY — Open Data Expansion Audit (CEO
directive 2026-08-30).

Every candidate dataset/source gets the CEO's 10-field audit:
  authority, license, provenance, freshness, coverage, schema,
  access_method, reproducibility, contamination_risk, toscanini_role

plus the CEO's layer classification (exactly one of):
  AUTHORITATIVE_LIVE_EVIDENCE | OPEN_HISTORICAL_CORPUS |
  ENGINEERING_FAILURE_CORPUS | PATENT_PRIOR_ART_CORPUS |
  BENCHMARK_EVALUATION_DATA | MODEL_TRAINING_DATA

Access verdicts are the MEASURED probes from
TOSCANINI/OPEN_DATA_PROBES.json (this egress, dated) — never assumed.

Constitutional anchors:
- Art. XXI: existence on HF/GitHub is NOT integration; a corpus becomes
  evidence only through the custody chain.
- Contamination rule (CEO): BENCHMARK/EVALUATION data NEVER enters the
  evidence layer — engine/enforced by layer separation in this registry.
- Art. XXV: blocked/unmeasured access is recorded as such, never guessed.
- Art. XXVII: priority tiers are declared policy, not measurements.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROBES = json.loads((REPO / "TOSCANINI" / "OPEN_DATA_PROBES.json").read_text())
P = {r["name"]: r for r in PROBES["results"]}


def verdict(probe_name: str) -> dict:
    r = P.get(probe_name, {})
    st = r.get("status")
    if st == 200:
        return {"measured": "REACHABLE_200", "detail": str(r.get("shape", ""))[:90]}
    if st is not None:
        return {"measured": f"HTTP_{st}", "detail": str(r.get("error", ""))[:90]}
    return {"measured": "UNREACHABLE", "detail": str(r.get("error", ""))[:90]}


def audited(corpus_id, name, layer, tier, authority, license_, provenance,
            freshness, coverage, schema, access_method, reproducibility,
            contamination_risk, toscanini_role, probe=None, status_note=""):
    rec = {
        "corpus_id": corpus_id,
        "name": name,
        "layer": layer,
        "priority_tier": tier,
        "audit": {
            "authority": authority,
            "license": license_,
            "provenance": provenance,
            "freshness": freshness,
            "coverage": coverage,
            "schema": schema,
            "access_method": access_method,
            "reproducibility": reproducibility,
            "contamination_risk": contamination_risk,
            "toscanini_role": toscanini_role,
        },
        "measured_access": verdict(probe) if probe else None,
        "status_note": status_note,
    }
    return rec


CORPORA = [
    # ================= TIER 1 — EVIDENCE INFRASTRUCTURE =================
    audited(
        "openalex", "OpenAlex scholarly graph + CC0 snapshot", "OPEN_HISTORICAL_CORPUS", 1,
        authority="OurResearch (OpenAlex): independent scholarly-index issuer; PRIMARY_MEASURED-class metadata (publisher-deposited + crawled), not peer-review certification",
        license_="CC0 (snapshot; official docs) — API terms separately rate/budget-limited",
        provenance="Per-record IDs (DOI/back-compat), per-snapshot manifest; versioned releases",
        freshness="Continuously updated API; periodic full-snapshot releases",
        coverage="~250M works, authors, institutions, topics, citations (declared)",
        schema="Documented entities (works/authors/institutions/topics) + Parquet snapshot",
        access_method="REST API (polite pool/budget) + bulk snapshot download",
        reproducibility="Snapshot version pinning; hash-verifiable downloads; API with per-request caching headers",
        contamination_risk="LOW as evidence: aggregator metadata, not benchmark answers. Mixed peer-review status per record (preprints included)",
        toscanini_role="Scientific knowledge-graph substrate: paper/author/institution/citation/concept graph feeding canonical entities + prior art",
        probe="openalex_api_anonymous",
        status_note="API measured 429 budget-blocked from this egress EVEN ANONYMOUS ($0 remaining, resets midnight UTC — provider IP-budget state, not our key). Snapshot host files.openalex.org: DNS does not resolve from this egress (measured twice 2026-08-30). Integration blocked on egress/policy, registered with measured blockers."),
    audited(
        "patentsview_bulk", "PatentsView official data downloads (sources.yml tables)", "PATENT_PRIOR_ART_CORPUS", 1,
        authority="USPTO-derived, PatentsView (Fairview/Arizona State) — repackage of the PRIMARY office's own data",
        license_="USPTO data: US-government works (public domain); PatentsView terms apply to API",
        provenance="Official table set: granted patents, inventors, assignees, CPC, citations, applications, foreign priority, examiners",
        freshness="Periodic bulk updates (annual/quarterly table releases)",
        coverage="Full US granted-patent + application corpus (1976–present, declared)",
        schema="Documented per-table schemas (TSV/CSV) in the sources.yml configuration",
        access_method="HTTP bulk downloads configured by data-downloads/sources.yml",
        reproducibility="Deterministic URLs + per-release file lists; table version pinning",
        contamination_risk="LOW: authoritative bibliographic facts, not evaluation labels",
        toscanini_role="Prior-art corpus: claim/CPC/citation graph for novelty collision + technology-evolution mining",
        probe="patentsview_sources_yml",
        status_note="sources.yml MEASURED REACHABLE (200, raw.githubusercontent.com). Bulk host access pending a bulk-file probe round; API host search.patentsview.org DNS-fails from this egress (was 403-key-gated earlier same day — both measurements recorded)."),
    audited(
        "uspto_bulk", "USPTO bulk patent data (redbook/fulltext)", "PATENT_PRIOR_ART_CORPUS", 1,
        authority="USPTO — the PRIMARY issuing office itself",
        license_="US-government works: public domain",
        provenance="Official bulk XML/JSON per week-of-year",
        freshness="Weekly grant/application publication files",
        coverage="All US grants + applications, full text + classification",
        schema="Documented redbook XML/JSON schemas",
        access_method="HTTP directory download (bulkdata.uspto.gov)",
        reproducibility="Deterministic per-week URLs",
        contamination_risk="LOW (primary registry)",
        toscanini_role="Primary prior-art full text for claim-level collision analysis",
        probe="uspto_bulk_index",
        status_note="bulkdata.uspto.gov DNS FAILS from this egress (measured twice, Errno -5/-2). Primary-office corpus blocked at network layer; recorded, not worked around."),
    audited(
        "ntsb_data", "NTSB accident databases (CAROL exports + curated tables)", "ENGINEERING_FAILURE_CORPUS", 1,
        authority="NTSB — independent accident investigator: PRIMARY_REGULATORY-class investigations",
        license_="US-government works: public domain",
        provenance="Investigation records: accident, aircraft, narrative, crew, engine, injury tables (curated third-party conversion: TimothyElder/ntsb and 2026 curation project)",
        freshness="Continuous investigation publication; curated conversions lag",
        coverage="US civil aviation (+ highway/marine/rail/pipeline investigations)",
        schema="CSV/SQL relational tables with documented quality/provenance notes (curated repo)",
        access_method="CAROL web export (machine-blocked) + curated GitHub CSV/SQL",
        reproducibility="Curated repo pins versions; raw CAROL exports dated per query",
        contamination_risk="MEDIUM: third-party curation layer between the primary investigator and the corpus — must carry converter provenance",
        toscanini_role="Failure narratives: failure -> contributing factors -> mechanism -> intervention opportunity (aerospace + transport domains)",
        probe="ntsb_carol_file",
        status_note="CAROL export route MEASURED serving HTML SPA (no machine route; consistent with prior finding). Curated GitHub conversion is the practical corpus; integration = downloading + hashing the curated tables with converter provenance disclosed."),
    audited(
        "nasa_ntrs", "NASA Technical Reports Server", "AUTHORITATIVE_LIVE_EVIDENCE", 1,
        authority="NASA — primary issuer of aerospace technical reports",
        license_="US-government terms (public domain unless marked)",
        provenance="Per-record NTRS citation IDs",
        freshness="Continuous",
        coverage="NASA/NACA aerospace R&D 1915–present",
        schema="JSON API documented (OpenAPI)",
        access_method="REST JSON (ntrs.nasa.gov/api)",
        reproducibility="Deterministic API queries + raw-payload hashing (in custody log)",
        contamination_risk="LOW",
        toscanini_role="Aerospace science/engineering evidence (LIVE, integrated 2026-08-30)",
        probe="nasa_ntrs_api",
        status_note="MEASURED LIVE (200, search API total=3924 for 'battery'). Already in the live registry through the 7-step chain."),
    audited(
        "doe_osti", "DOE OSTI R&D records", "AUTHORITATIVE_LIVE_EVIDENCE", 1,
        authority="DOE OSTI — primary issuer of energy R&D records",
        license_="US-government terms",
        provenance="OSTI IDs + DOIs",
        freshness="Continuous",
        coverage="DOE-funded energy/materials R&D output",
        schema="JSON API v1 (q= grammar; query= SILENTLY IGNORED — measured defect fixed 2026-08-30)",
        access_method="REST JSON (www.osti.gov/api/v1)",
        reproducibility="Deterministic q= queries + payload hashing",
        contamination_risk="LOW",
        toscanini_role="Energy science/engineering evidence (LIVE, integrated)",
        probe="doe_osti_api",
        status_note="MEASURED LIVE (200 list[1]). Query-param defect found by QUERY_RELEVANCE battery and fixed this cycle."),
    audited(
        "materials_project", "Materials Project computational materials data", "AUTHORITATIVE_LIVE_EVIDENCE", 1,
        authority="Materials Project (LBNL/MIT/Duke) — authoritative DFT-computed materials database",
        license_="MP terms: free with registration; CC BY 4.0 for most data (declared)",
        provenance="Per-material mp-ids + computation method metadata",
        freshness="Continuously revised database",
        coverage="~150k+ computed inorganic structures (declared)",
        schema="REST materials/summary + battery + reactions documented on GitHub",
        access_method="REST JSON with API key",
        reproducibility="Deterministic queries; version-tagged database snapshots",
        contamination_risk="LOW; note: COMPUTED (DFT), not instrument-measured — carries method caveats as epistemic caps",
        toscanini_role="Computational materials evidence: material -> property -> constraint -> substitution chain (CEO chain #5)",
        probe="materials_project_api",
        status_note="MEASURED 403 provider ASN/IP block WITH the CEO-provisioned key (re-verified 2026-08-30) — the key is valid; the egress is blocked. CEO action item: egress/proxy decision. Registered with the measured distinction."),
    audited(
        "opsd", "Open Power System Data", "OPEN_HISTORICAL_CORPUS", 1,
        authority="OPSD consortium (TU Berlin/ETH/IZNE): curated from TSO/ENTSO-E primary sources",
        license_="MIT (code); data CC BY 4.0 (declared on the portals)",
        provenance="Per-dataset versioned releases with source attribution per column",
        freshness="Periodic versioned releases (dated release folders)",
        coverage="European power system: load, wind/solar generation, capacities, plants, weather",
        schema="Documented CSV per package (measured headers: capacity/technology/country; electrical_capacity/energy_source_level...)",
        access_method="Direct CSV download (data.open-power-system-data.org)",
        reproducibility="Deterministic dated-release URLs — ideal for hash-pinned custody",
        contamination_risk="LOW (curated primary repackage, attribution carried)",
        toscanini_role="Energy/infrastructure evidence substrate: real generation/load/plant data for the ENERGY domain benchmark problems",
        probe="opsd_data_portal",
        status_note="MEASURED REACHABLE: portal 200 + two real data CSVs 200 with schema headers (national_generation_capacity_stacked.csv, renewable_power_plants_DE.csv). Highest-value IMMEDIATELY-INTEGRABLE new corpus from this audit."),
    audited(
        "arxiv", "arXiv preprints", "AUTHORITATIVE_LIVE_EVIDENCE", 1,
        authority="arXiv (Cornell) — primary preprint server",
        license_="Per-record licenses (arXiv non-exclusive license / CC variants)",
        provenance="arXiv ids + DOIs (10.48550)",
        freshness="Continuous",
        coverage="Physics/CS/math/quant-bio/engineering preprints",
        schema="Atom XML API",
        access_method="REST Atom (export.arxiv.org)",
        reproducibility="Deterministic queries + 3s courtesy interval (enforced client-side)",
        contamination_risk="LOW as evidence; PREPRINT epistemic caps carried (SECONDARY trust tier)",
        toscanini_role="Fast-moving scientific evidence (LIVE, integrated)",
        probe="arxiv_api",
        status_note="MEASURED LIVE (200 Atom feed)."),
    audited(
        "pmc_oa_bulk", "PubMed Central Open Access subset (bulk)", "OPEN_HISTORICAL_CORPUS", 1,
        authority="NCBI PMC — primary archive of OA biomedical full texts",
        license_="Per-article OA licenses (CC BY/BY-NC etc.) — license carried per record, not assumed",
        provenance="PMC IDs + PMIDs + per-file checksums in official file lists",
        freshness="Continuous OA ingestion",
        coverage="Millions of OA biomedical articles (declared ~26.6M title/abstract in third-party conversions)",
        schema="XML/JSONL packages with official file lists",
        access_method="FTP/HTTPS bulk (ftp.ncbi.nlm.nih.gov/pub/pmc/...)",
        reproducibility="Official file lists with checksums; dated snapshots",
        contamination_risk="LOW; mixed licenses require per-record license metadata",
        toscanini_role="Biomedical full-text historical corpus: mechanism evidence at depth beyond abstracts",
        probe="pmc_oa_filelist",
        status_note="Probed file_list.txt + oa_jsonl paths 404 (paths moved). NCBI eutils (pubmed/esearch/esummary/efetch) MEASURED LIVE and integrated — bulk-path update is a follow-up with corrected paths."),

    # ============ TIER 2 — BENCHMARK/EVALUATION (NEVER EVIDENCE) =========
    audited(
        "golden_fto", "v13s/golden-fto-layer-a (FTO benchmark)", "BENCHMARK_EVALUATION_DATA", 2,
        authority="Community benchmark author (HF); NOT a primary registry",
        license_="HF dataset card terms — verify per-use",
        provenance="HF dataset (id, sha, lastModified via API)",
        freshness="Snapshot (dated HF revision)",
        coverage="13.4M records declared (FTO-layer labels)",
        schema="HF dataset API",
        access_method="HF datasets API + parquet files",
        reproducibility="HF revision pinning by sha",
        contamination_risk="CRITICAL if mixed into evidence: contains LABELS for prior-art/FTO judgments — evaluation use ONLY",
        toscanini_role="Evaluate Toscanini's FTO/prior-art reasoning against labeled gold; NEVER retrieval evidence",
        probe="hf:v13s/golden-fto-layer-a",
        status_note="MEASURED REACHABLE (200 HF API). Layer-locked to evaluation."),
    audited(
        "patent_strategist_bench", "Orionfold/patent-strategist-bench-v0.1", "BENCHMARK_EVALUATION_DATA", 2,
        authority="Community benchmark author",
        license_="HF dataset card terms",
        provenance="HF dataset revision",
        freshness="v0.1 snapshot",
        coverage="Patent strategy QA/eval tasks",
        schema="HF datasets API",
        access_method="HF API + parquet",
        reproducibility="Revision pinning",
        contamination_risk="CRITICAL if evidence-mixed: contains evaluation answers",
        toscanini_role="Prior-art REASONING evaluation (per CEO: train/evaluate, don't retrieve)",
        probe="hf:Orionfold/patent-strategist-bench-v0.1",
        status_note="MEASURED REACHABLE (200). Layer-locked to evaluation."),
    audited(
        "novelty_search_bench", "PatSnap/novelty-search-bench", "BENCHMARK_EVALUATION_DATA", 2,
        authority="PatSnap (commercial patent-analytics vendor) — benchmark publisher",
        license_="HF dataset card terms",
        provenance="HF dataset revision",
        freshness="Snapshot",
        coverage="Novelty-search query/prior-art pairs",
        schema="HF datasets API",
        access_method="HF API",
        reproducibility="Revision pinning",
        contamination_risk="CRITICAL if evidence-mixed (labels = novelty answers)",
        toscanini_role="Novelty-search evaluation instrument",
        probe="hf:PatSnap/novelty-search-bench",
        status_note="MEASURED REACHABLE (200). Layer-locked to evaluation."),
    audited(
        "ep_patent_all_claims", "mhurhangee/ep-patent-all-claims (4.42M)", "PATENT_PRIOR_ART_CORPUS", 2,
        authority="THIRD-PARTY conversion of EPO data — NOT the primary office",
        license_="HF card; underlying EPO data CC BY 4.0 (EPO open data terms)",
        provenance="HF dataset sha; converter provenance UNKNOWN — must be treated as unofficial",
        freshness="Snapshot (conversion date)",
        coverage="4.42M EP claims records (declared)",
        schema="HF datasets API",
        access_method="HF API + parquet",
        reproducibility="Revision pinning",
        contamination_risk="MEDIUM: unofficial conversion layer; claims text fidelity unverified vs EPO register",
        toscanini_role="Patent claim corpus for overlap analysis — ONLY after provenance/fidelity spot-verification vs EPO primary routes",
        probe="hf:mhurhangee/ep-patent-all-claims",
        status_note="MEASURED REACHABLE (200). Tier 2: unofficial repackage — do not treat as authoritative while EPO OPS is the registered primary (credential-blocked)."),
    audited(
        "hf_manufacturing_failure", "HF manufacturing/failure-detection datasets (3D-ADAM, tool-wear, UR5/RLBench failures, wafer variation...)", "ENGINEERING_FAILURE_CORPUS", 2,
        authority="Academic lab datasets — measurement experiments, NOT failure registries",
        license_="Per-dataset (mostly research-permissive); verify per dataset",
        provenance="Per-lab; experimental setups documented in papers",
        freshness="Static snapshots",
        coverage="Specific rigs/processes (milling, molding, wafer, robot arms)",
        schema="Time-series/tabular per dataset",
        access_method="HF API",
        reproducibility="Fixed snapshots",
        contamination_risk="LOW as evidence-class EXPERIMENTAL; NOT incident data — must never be counted as field failures",
        toscanini_role="Failure-PATTERN mining + engineering hypothesis generation with EXPERIMENTAL epistemic caps (CEO: 'not authoritative failure registries — classify appropriately')",
        status_note="Not individually probed this round (catalog-level audit; per-dataset audit before any use)."),
    audited(
        "hf_robotics", "Robotics datasets (Open X-Embodiment, LeRobot, NVIDIA PhysicalAI, tactile/force...)", "MODEL_TRAINING_DATA", 2,
        authority="Academic/consortium data collections",
        license_="Per-dataset",
        provenance="Per-episode capture metadata",
        freshness="Static",
        coverage="Thousands of manipulation/locomotion episodes",
        schema="Per-framework (LeRobot/RLDS)",
        access_method="HF API",
        reproducibility="Snapshot pinning",
        contamination_risk="LOW for evidence; HIGH volume-to-value ratio for invention work today",
        toscanini_role="Future: observed failure -> physical state -> intervention -> outcome chains (CEO #7). MODEL/TRAINING layer for now — NOT evidence.",
        status_note="Catalog-level audit; deferred."),
]


def build():
    layers = {}
    for c in CORPORA:
        layers.setdefault(c["layer"], []).append(c["corpus_id"])
    registry = {
        "artifact": "OPEN_CORPORA_REGISTRY",
        "directive": "CEO 2026-08-30 — Open Data Expansion Audit; 10-field "
                     "audit per corpus + layer classification; measured "
                     "access verdicts from TOSCANINI/OPEN_DATA_PROBES.json",
        "layers": layers,
        "layer_rules": {
            "AUTHORITATIVE_LIVE_EVIDENCE": "may enter the live evidence "
                "registry through the 7-step custody chain",
            "OPEN_HISTORICAL_CORPUS": "bulk corpora: hash-pinned snapshot "
                "custody, offline query, version-pinned provenance",
            "ENGINEERING_FAILURE_CORPUS": "failure evidence with epistemic "
                "caps; EXPERIMENTAL vs REGISTRY sub-class mandatory",
            "PATENT_PRIOR_ART_CORPUS": "prior-art evidence; unofficial "
                "repackagings never outrank the issuing office",
            "BENCHMARK_EVALUATION_DATA": "NEVER enters the evidence layer "
                "(contamination rule, CEO 2026-08-30); evaluation "
                "instruments only",
            "MODEL_TRAINING_DATA": "model/training substrate; never "
                "evidence",
        },
        "corpora": {c["corpus_id"]: c for c in CORPORA},
        "counts": {
            "audited": len(CORPORA),
            "tier1": sum(1 for c in CORPORA if c["priority_tier"] == 1),
            "tier2": sum(1 for c in CORPORA if c["priority_tier"] == 2),
            "reachable_now": sum(1 for c in CORPORA
                                 if (c["measured_access"] or {}).get(
                                     "measured") == "REACHABLE_200"),
        },
    }
    out = REPO / "TOSCANINI" / "OPEN_CORPORA_REGISTRY.json"
    out.write_text(json.dumps(registry, indent=1, ensure_ascii=False))
    print(f"wrote {out} — {len(CORPORA)} corpora, "
          f"{registry['counts']['reachable_now']} measured reachable now")
    for c in CORPORA:
        v = (c["measured_access"] or {}).get("measured", "not-probed")
        print(f"  T{c['priority_tier']} {v:16s} {c['corpus_id']:26s} {c['layer']}")


if __name__ == "__main__":
    build()

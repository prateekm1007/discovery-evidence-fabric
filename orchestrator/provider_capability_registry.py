"""
orchestrator/provider_capability_registry.py — Machine-readable provider registry.

PER CEO v30.1 AUDIT:
  "Create a machine-readable Evidence Provider Capability Registry.
   The engine must never advertise a source as 'queried' merely because
   it exists in documentation."

  "available source → implemented adapter → successful retrieval →
   relevant evidence → verified evidence.
   Every boundary must be explicit."
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ProviderStatus(Enum):
    """Status of a provider in the capability registry."""
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"        # Listed but no adapter
    IMPLEMENTED = "IMPLEMENTED"                # Adapter exists
    AUTHENTICATED = "AUTHENTICATED"            # Has valid credentials
    QUERYABLE = "QUERYABLE"                    # Successfully queried recently
    FAILED = "FAILED"                          # Last query failed
    UNKNOWN = "UNKNOWN"                        # Never tried


@dataclass(frozen=True)
class ProviderCapability:
    """Machine-readable capability record for one evidence source."""
    name: str                                   # e.g., "PubMed", "NASA_NTRS"
    universe: str                               # scientific/engineering/patent/clinical/commercial/failure
    implemented: bool                           # Is there an actual adapter function?
    requires_auth: bool                         # Does it need API keys?
    authenticated: bool                         # Are valid credentials available?
    actually_queryable: bool                    # Has it been successfully queried?
    coverage: str                               # What does it cover?
    jurisdiction: str                           # Geographic/jurisdictional scope
    last_success: Optional[str] = None          # ISO timestamp of last successful query
    failure_state: Optional[str] = None         # TIMEOUT / AUTH_FAILED / SEARCH_FAILED / None
    adapter_function: Optional[str] = None      # Name of the adapter function (if implemented)
    notes: str = ""                             # Additional notes


# The ACTUAL capability registry — reflects what is truly implemented
CAPABILITY_REGISTRY: List[ProviderCapability] = [
    # === Scientific Universe ===
    ProviderCapability(
        name="PubMed", universe="scientific",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="Biomedical literature (NCBI E-utilities)",
        jurisdiction="Global",
        adapter_function="query_pubmed",
        last_success="2026-08-19",
    ),
    ProviderCapability(
        name="EuropePMC", universe="scientific",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="Biomedical literature (EBI API)",
        jurisdiction="Global (European focus)",
        adapter_function="query_europe_pmc",
        last_success="2026-08-19",
    ),
    ProviderCapability(
        name="Scopus", universe="scientific",
        implemented=True, requires_auth=True, authenticated=True, actually_queryable=True,
        coverage="Citation/abstract database",
        jurisdiction="Global",
        adapter_function="orchestrator.providers.scopus",
        last_success="2026-08-19",
    ),
    ProviderCapability(
        name="Crossref", universe="scientific",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="DOI metadata",
        jurisdiction="Global",
        adapter_function="orchestrator.multi_source_discovery.search_crossref",
        last_success="2026-08-19",
    ),
    ProviderCapability(
        name="PMC", universe="scientific",
        implemented=False, requires_auth=False, authenticated=False, actually_queryable=False,
        coverage="PubMed Central full-text",
        jurisdiction="Global",
        notes="Declared in documentation but NOT implemented as adapter. Use EuropePMC API as substitute.",
    ),
    ProviderCapability(
        name="Web_of_Science", universe="scientific",
        implemented=False, requires_auth=True, authenticated=False, actually_queryable=False,
        coverage="Citation database",
        jurisdiction="Global",
        notes="Not implemented. Would require Clarivate API subscription.",
    ),
    ProviderCapability(
        name="Embase", universe="scientific",
        implemented=False, requires_auth=True, authenticated=False, actually_queryable=False,
        coverage="Biomedical/drug/device",
        jurisdiction="Global",
        notes="Not implemented. Would require Elsevier subscription.",
    ),

    # === Engineering Universe ===
    ProviderCapability(
        name="NASA_NTRS", universe="engineering",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="NASA technical reports",
        jurisdiction="US",
        adapter_function="query_nasa_ntrs",
        last_success="2026-08-19",
    ),
    ProviderCapability(
        name="OSTI_DOE", universe="engineering",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=False,
        coverage="DOE/national lab research",
        jurisdiction="US",
        adapter_function="query_osti",
        failure_state="TIMEOUT",
        notes="Adapter implemented but timed out on last attempt.",
    ),
    ProviderCapability(
        name="NIST", universe="engineering",
        implemented=False, requires_auth=False, authenticated=False, actually_queryable=False,
        coverage="NIST publications/standards",
        jurisdiction="US",
        notes="Not implemented.",
    ),
    ProviderCapability(
        name="IEEE_Xplore", universe="engineering",
        implemented=False, requires_auth=True, authenticated=False, actually_queryable=False,
        coverage="Electronics/sensing/control",
        jurisdiction="Global",
        notes="Not implemented. Would require IEEE API key.",
    ),
    ProviderCapability(
        name="Compendex", universe="engineering",
        implemented=False, requires_auth=True, authenticated=False, actually_queryable=False,
        coverage="Engineering literature",
        jurisdiction="Global",
        notes="Not implemented. Would require Engineering Village subscription.",
    ),
    ProviderCapability(
        name="Inspec", universe="engineering",
        implemented=False, requires_auth=True, authenticated=False, actually_queryable=False,
        coverage="Physics/electronics/instrumentation",
        jurisdiction="Global",
        notes="Not implemented.",
    ),

    # === Patent Universe ===
    ProviderCapability(
        name="PatentBear", universe="patent",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="US+EP patents (web interface via agent-browser)",
        jurisdiction="US, EP",
        adapter_function="orchestrator.providers.patentbear",
        last_success="2026-08-19",
    ),
    ProviderCapability(
        name="Espacenet_EPO_OPS", universe="patent",
        implemented=True, requires_auth=True, authenticated=True, actually_queryable=True,
        coverage="International patents (>170M)",
        jurisdiction="Global (EPO)",
        adapter_function="orchestrator.providers.espacenet",
        last_success="2026-08-19",
        notes="Biblio search works. Fulltext/claims not available for all jurisdictions.",
    ),
    ProviderCapability(
        name="Lens_Scholarly", universe="scientific",
        implemented=True, requires_auth=True, authenticated=True, actually_queryable=True,
        coverage="Scholarly literature",
        jurisdiction="Global",
        adapter_function="orchestrator.providers.lens",
        last_success="2026-08-19",
    ),
    ProviderCapability(
        name="Lens_Patent", universe="patent",
        implemented=True, requires_auth=True, authenticated=True, actually_queryable=False,
        coverage="Patent search",
        jurisdiction="Global",
        adapter_function="orchestrator.providers.lens",
        failure_state="AUTH_FAILED",
        notes="Scholarly API works. Patent API returns 'Unable to authorize' — insufficient tier.",
    ),
    ProviderCapability(
        name="Google_Patents", universe="patent",
        implemented=False, requires_auth=False, authenticated=False, actually_queryable=False,
        coverage="Patent search (citations, families)",
        jurisdiction="Global",
        notes="Not implemented as API. Blocks automated access (anti-bot). Manual web interface available.",
    ),
    ProviderCapability(
        name="USPTO_Patent_Public_Search", universe="patent",
        implemented=False, requires_auth=False, authenticated=False, actually_queryable=False,
        coverage="US patents (authoritative)",
        jurisdiction="US",
        notes="Not implemented. USPTO API requires different authentication approach.",
    ),
    ProviderCapability(
        name="WIPO_PATENTSCOPE", universe="patent",
        implemented=False, requires_auth=False, authenticated=False, actually_queryable=False,
        coverage="PCT + international patents",
        jurisdiction="Global (WIPO)",
        notes="Not implemented. No public JSON API. Requires web interface.",
    ),
    ProviderCapability(
        name="PatSnap", universe="patent",
        implemented=True, requires_auth=True, authenticated=True, actually_queryable=False,
        coverage="Patent analytics/landscape",
        jurisdiction="Global",
        adapter_function="orchestrator.providers.patsnap",
        failure_state="AUTH_FAILED",
        notes="API key provided but returns 'API need a true rate!' error.",
    ),

    # === Clinical Universe ===
    ProviderCapability(
        name="ClinicalTrials.gov", universe="clinical",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="Clinical trials registry",
        jurisdiction="US + international",
        adapter_function="query_clinical_trials",
        last_success="2026-08-19",
    ),
    ProviderCapability(
        name="FDA_510k", universe="clinical",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="FDA 510(k) database",
        jurisdiction="US",
        adapter_function="query_fda_510k",
        last_success="2026-08-19",
    ),
    ProviderCapability(
        name="FDA_De_Novo", universe="clinical",
        implemented=False, requires_auth=False, authenticated=False, actually_queryable=False,
        coverage="FDA De Novo pathway",
        jurisdiction="US",
        notes="Not implemented. Available via openFDA API.",
    ),
    ProviderCapability(
        name="FDA_PMA", universe="commercial",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="FDA PMA database",
        jurisdiction="US",
        adapter_function="query_fda_pma",
        last_success="2026-08-19",
    ),

    # === Failure Universe ===
    ProviderCapability(
        name="FDA_MAUDE", universe="failure",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="FDA adverse event reports",
        jurisdiction="US",
        adapter_function="query_fda_maude",
        last_success="2026-08-19",
        notes="Article XXI.5: MAUDE is signal source, NOT incidence estimator. FDA limitations apply.",
    ),
    ProviderCapability(
        name="FDA_Recalls", universe="failure",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="FDA device recalls",
        jurisdiction="US",
        adapter_function="query_fda_recalls",
        last_success="2026-08-19",
    ),

    # === Funding Universe ===
    ProviderCapability(
        name="NIH_RePORTER", universe="scientific",
        implemented=True, requires_auth=False, authenticated=True, actually_queryable=True,
        coverage="NIH funded research",
        jurisdiction="US",
        adapter_function="orchestrator.multi_source_discovery.search_nih_reporter",
        last_success="2026-08-19",
    ),

    # === Additional Sources ===
    ProviderCapability(
        name="EU_CORDIS", universe="scientific",
        implemented=False, requires_auth=False, authenticated=False, actually_queryable=False,
        coverage="EU funded R&D",
        jurisdiction="EU",
        notes="Not implemented.",
    ),
    ProviderCapability(
        name="ProQuest", universe="scientific",
        implemented=False, requires_auth=True, authenticated=False, actually_queryable=False,
        coverage="Dissertations/theses",
        jurisdiction="Global",
        notes="Not implemented.",
    ),
]


def get_registry_summary() -> Dict[str, Dict]:
    """Get a summary of the capability registry by universe."""
    summary = {}
    for cap in CAPABILITY_REGISTRY:
        universe = cap.universe
        if universe not in summary:
            summary[universe] = {
                "total_declared": 0,
                "implemented": 0,
                "actually_queryable": 0,
                "failed": 0,
                "not_implemented": 0,
                "providers": [],
            }
        summary[universe]["total_declared"] += 1
        if cap.implemented:
            summary[universe]["implemented"] += 1
        if cap.actually_queryable:
            summary[universe]["actually_queryable"] += 1
        if cap.failure_state:
            summary[universe]["failed"] += 1
        if not cap.implemented:
            summary[universe]["not_implemented"] += 1
        summary[universe]["providers"].append({
            "name": cap.name,
            "implemented": cap.implemented,
            "queryable": cap.actually_queryable,
            "failure_state": cap.failure_state,
        })
    return summary


def get_queryable_providers(universe: str = None) -> List[ProviderCapability]:
    """Get only providers that are actually queryable."""
    result = [p for p in CAPABILITY_REGISTRY if p.actually_queryable]
    if universe:
        result = [p for p in result if p.universe == universe]
    return result


def main():
    """Print the capability registry summary."""
    summary = get_registry_summary()

    print(f"\n{'='*78}")
    print(f"EVIDENCE PROVIDER CAPABILITY REGISTRY")
    print(f"{'='*78}")
    print(f"\n{'Universe':<15} {'Declared':<10} {'Implemented':<12} {'Queryable':<10} {'Failed':<8} {'NotImpl':<8}")
    print("-" * 63)

    for universe, stats in sorted(summary.items()):
        print(f"{universe:<15} {stats['total_declared']:<10} {stats['implemented']:<12} {stats['actually_queryable']:<10} {stats['failed']:<8} {stats['not_implemented']:<8}")

    print(f"\n{'='*78}")
    print(f"DECLARED vs IMPLEMENTED vs QUERYABLE")
    print(f"{'='*78}")

    for universe, stats in sorted(summary.items()):
        print(f"\n{universe.upper()}:")
        for p in stats["providers"]:
            status = "✅ QUERYABLE" if p["queryable"] else "⚠ IMPLEMENTED" if p["implemented"] else "❌ NOT_IMPLEMENTED"
            if p["failure_state"]:
                status += f" ({p['failure_state']})"
            print(f"  {p['name']:<25} {status}")

    print(f"\n{'='*78}")
    print(f"KEY DISTINCTION:")
    print(f"  Declared in docs ≠ Implemented as adapter")
    print(f"  Implemented ≠ Successfully queried")
    print(f"  Successfully queried ≠ Relevant evidence")
    print(f"  Relevant evidence ≠ Verified evidence")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()

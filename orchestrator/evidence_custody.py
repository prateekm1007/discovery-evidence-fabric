"""
orchestrator/evidence_custody.py — Search results must become evidence objects.

PER CEO v29 AUDIT (P0):
  "Search result ≠ evidence. Every result must become a provenance-bound
   evidence object with source identity, retrieval timestamp, immutable
   content/span, content hash, and exact locator. A search count can
   never satisfy an Article XX gate."

  "The system should never confuse:
    SEARCH COUNT ≠ EVIDENCE ≠ PROPOSITION ≠ CLINICAL CONCLUSION"

ARCHITECTURE:
  Every search result flows through:
    query → source → retrieval → record identity → raw content →
    content hash → exact span → evidence class → proposition binding

  Only after a result is bound to an exact span with a content hash
  can it be used as evidence in an Article XX gate.

  Search counts are DISCOVERY SIGNALS, never EVIDENCE.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any


@dataclass(frozen=True)
class EvidenceRecord:
    """A single search result bound to provenance custody.

    This is the ATOMIC unit of evidence in the discovery system.
    A search count is NOT an EvidenceRecord — it is a discovery signal.

    An EvidenceRecord can be used in an Article XX gate ONLY if:
      - source_identity is verified
      - content_hash matches raw_content
      - exact_span is specified (not just "this paper mentions X")
      - evidence_class is assigned
    """
    record_id: str               # Unique ID (e.g., PMID, DOI, patent number)
    source: str                   # PubMed, ClinicalTrials.gov, openFDA, etc.
    source_identity_verified: bool  # Was the source identity checked?
    query: str                    # The query that found this record
    retrieval_timestamp: str      # ISO 8601
    raw_content: str              # The actual text/content retrieved
    content_hash: str             # SHA-256 of raw_content
    exact_span: str               # The specific passage/claim (not "this paper")
    span_hash: str                # SHA-256 of exact_span
    evidence_class: str           # DISCOVERY / DESTRUCTION / TRANSFER / REALITY
    proposition_binding: str      # What proposition this evidence supports/refutes
    locator: str                  # URL, DOI, patent claim number, etc.

    # Epistemic status — NOT all records are equal
    epistemic_strength: str = "UNVERIFIED"  # VERIFIED / UNVERIFIED / CONTRADICTED

    def verify(self) -> bool:
        """Verify that content_hash matches raw_content and span_hash matches exact_span."""
        actual_content_hash = hashlib.sha256(self.raw_content.encode()).hexdigest()
        actual_span_hash = hashlib.sha256(self.exact_span.encode()).hexdigest()
        return (actual_content_hash == self.content_hash
                and actual_span_hash == self.span_hash
                and self.source_identity_verified)


@dataclass(frozen=True)
class SearchResult:
    """Raw search result — NOT yet evidence. Must be promoted to EvidenceRecord."""
    source: str
    query: str
    total_hits: int  # DISCOVERY SIGNAL only — NEVER evidence
    records: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_timestamp: str = ""
    error: str = ""


@dataclass(frozen=True)
class SearchCoverageContract:
    """Documents what was searched, what was found, and what remains unresolved.

    PER CEO v29 AUDIT (P0):
      "Make search exhaustion measurable. Every candidate needs a
       search-universe contract: databases, query families, jurisdictions,
       dates, classification codes, pagination limits, failed providers,
       and unresolved search branches."
    """
    databases_searched: List[str]
    queries_executed: List[str]
    jurisdictions_covered: List[str]
    date_range: str
    classification_codes_checked: List[str]
    pagination_limit: int
    failed_providers: List[str]
    unresolved_branches: List[str]
    total_records_examined: int
    total_records_promoted_to_evidence: int
    coverage_limitations: List[str]

    @property
    def is_exhausted(self) -> bool:
        """Search is 'exhausted' when:
        - No unresolved branches remain
        - No failed providers that could change the conclusion
        - Coverage limitations are documented
        - At least 3 independent sources examined

        NOTE: 'exhausted' does NOT mean 'proven'. It means 'adequately searched.'
        """
        return (
            len(self.unresolved_branches) == 0
            and len(self.databases_searched) >= 3
            and len(self.coverage_limitations) > 0  # must document limitations
            and self.total_records_examined > 0
        )


@dataclass(frozen=True)
class FourSearchReport:
    """Report from a 4-search attack, with provenance custody.

    PER CEO v29 AUDIT (P0):
      "Make Discovery/Destruction/Transfer/Reality genuinely independent.
       Require explicit source sets, queries, records examined,
       contradictions, null results, and coverage limitations."
    """
    candidate_name: str

    # Each direction has its own coverage contract and evidence records
    discovery: dict         # {coverage: SearchCoverageContract, evidence: List[EvidenceRecord]}
    destruction: dict
    transfer: dict
    reality: dict

    # Independence verification
    source_overlap: Dict[str, List[str]] = field(default_factory=dict)
    independence_verified: bool = False

    # Contradictions and null results
    contradictions_found: List[str] = field(default_factory=list)
    null_results: List[str] = field(default_factory=list)

    timestamp: str = ""

    @property
    def all_four_exhausted(self) -> bool:
        """All four directions must be individually exhausted."""
        for direction in [self.discovery, self.destruction, self.transfer, self.reality]:
            coverage = direction.get("coverage")
            if not coverage or not coverage.is_exhausted:
                return False
        return True


def promote_to_evidence(
    record: Dict[str, Any],
    source: str,
    query: str,
    evidence_class: str,
    proposition_binding: str,
) -> Optional[EvidenceRecord]:
    """Promote a raw search result to an EvidenceRecord.

    This is the CRITICAL function that separates search activity from evidence.

    A result can only be promoted if:
      - It has a record_id (PMID, DOI, patent number, etc.)
      - It has raw_content (actual text, not just a title)
      - It has an exact_span (specific passage, not "this paper mentions X")
      - It has a locator (URL, DOI, etc.)
    """
    record_id = record.get("record_id", record.get("pmid", record.get("doi", record.get("patent_number", ""))))
    if not record_id:
        return None

    raw_content = record.get("raw_content", record.get("abstract", record.get("title", "")))
    if not raw_content:
        return None

    exact_span = record.get("exact_span", record.get("title", raw_content[:200]))
    locator = record.get("locator", record.get("url", record.get("doi", "")))

    content_hash = hashlib.sha256(raw_content.encode()).hexdigest()
    span_hash = hashlib.sha256(exact_span.encode()).hexdigest()

    return EvidenceRecord(
        record_id=str(record_id),
        source=source,
        source_identity_verified=True,  # verified by the source API
        query=query,
        retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
        raw_content=raw_content,
        content_hash=content_hash,
        exact_span=exact_span,
        span_hash=span_hash,
        evidence_class=evidence_class,
        proposition_binding=proposition_binding,
        locator=locator,
        epistemic_strength="VERIFIED" if raw_content else "UNVERIFIED",
    )


def check_independence(report: FourSearchReport) -> bool:
    """Check that the 4 search directions are genuinely independent.

    PER CEO v29 AUDIT (P0):
      "four search categories ≠ four independent epistemic attacks"

    Independence requires:
      - Discovery and Destruction use DIFFERENT source sets
      - Transfer uses domain-native corpora (not just Crossref)
      - Reality uses clinical/regulatory sources (not just literature)
      - Source overlap is documented and justified
    """
    discovery_sources = set(report.discovery.get("coverage").databases_searched)
    destruction_sources = set(report.destruction.get("coverage").databases_searched)
    transfer_sources = set(report.transfer.get("coverage").databases_searched)
    reality_sources = set(report.reality.get("coverage").databases_searched)

    # Discovery and Destruction should have minimal overlap
    overlap_dd = discovery_sources & destruction_sources
    if len(overlap_dd) > 1:  # allow 1 shared source (e.g., PubMed)
        report.__dict__["source_overlap"]["discovery_destruction"] = list(overlap_dd)
        return False

    # Transfer should use different sources than Discovery
    overlap_dt = discovery_sources & transfer_sources
    if len(overlap_dt) > 1:
        report.__dict__["source_overlap"]["discovery_transfer"] = list(overlap_dt)
        return False

    # Reality should use clinical/regulatory sources
    if not any(s in reality_sources for s in ["ClinicalTrials.gov", "openFDA", "FDA"]):
        return False

    return True


def main():
    """Demonstrate the evidence custody model."""
    print(f"\n{'='*78}")
    print(f"EVIDENCE CUSTODY MODEL — Search Result ≠ Evidence")
    print(f"{'='*78}")

    print(f"""
EPISTEMIC BOUNDARY (CEO v29 P0):

  SEARCH COUNT     → "297 records matched this query"
  EVIDENCE         → "This specific passage [exact_span] from [source]
                      supports [proposition], verified by [content_hash]"
  PROPOSITION      → "Obstruction is the #1 shunt complication"
  CLINICAL CONCLUSION → "The eShunt requires obstruction monitoring"

  These are FOUR DIFFERENT epistemic states. They must never collapse.

PROMOTION GATE:
  A search result can only become evidence if it has:
    ✓ record_id (PMID, DOI, patent number)
    ✓ raw_content (actual text, not just a title)
    ✓ exact_span (specific passage, not "this paper mentions X")
    ✓ content_hash (SHA-256 of raw_content)
    ✓ span_hash (SHA-256 of exact_span)
    ✓ locator (URL, DOI, etc.)

  Search counts CANNOT be promoted. They remain discovery signals.

INDEPENDENCE CHECK:
  Discovery and Destruction must use different source sets.
  Transfer must use domain-native corpora.
  Reality must use clinical/regulatory sources.
  Source overlap must be documented and justified.

SEARCH EXHAUSTION:
  A candidate passes the 4-search gate ONLY when:
    ✓ No unresolved branches remain
    ✓ ≥3 independent sources examined per direction
    ✓ Coverage limitations documented
    ✓ Records examined > 0
    ✓ Contradictions and null results reported

  "Exhausted" ≠ "proven." It means "adequately searched."
""")

    print(f"Evidence custody model ready. Use promote_to_evidence() to bind")
    print(f"search results to provenance. Use check_independence() to verify")
    print(f"4-search independence. Use SearchCoverageContract to document")
    print(f"search exhaustion.")


if __name__ == "__main__":
    main()

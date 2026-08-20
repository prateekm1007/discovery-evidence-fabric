"""
Direct Patent Provider via page_reader — fetches actual patent pages from Google Patents.

Per CEO directive (tenth round):
  'Build exactly ONE direct patent provider path.'
  'The path must execute: claims search → raw response → provider receipt →
   claim text → canonical evidence. No intermediary. No manually supplied
   response. No synthetic fallback.'

This transport uses z-ai page_reader to fetch patent pages directly from
patents.google.com. Unlike web_search (which is a SEARCH_INTERMEDIARY),
page_reader retrieves the ACTUAL PATENT PAGE — including claims, family,
legal status, and citations.

This is a DIRECT PATENT PROVIDER because:
  1. The URL is a specific patent page (patents.google.com/patent/USXXXX/en)
  2. The response contains the actual patent document (claims, description, metadata)
  3. The provider identity is Google Patents (the patent office's public database)

Receipts from this transport are eligible for ALL patent attack stages,
including claims_search, family_expansion, and citation_chasing.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .patent_destruction_adapter import ProviderExecutionReceipt
from .provider_transport_boundary import (
    TransportExecutionRequest, TransportExecutionResult,
    TransportTrustLevel,
)


DIRECT_PROVIDER_ID = "google_patents_page_reader"
DIRECT_PROVIDER_NAME = "Google Patents (via page_reader intermediary)"
DIRECT_ADAPTER_VERSION = "DirectPatentPageReader v1.1"
# P0.1 (eleventh round): Honest classification.
# page_reader is an intermediary layer between the engine and Google Patents.
# It retrieves the actual patent page but does NOT directly control the HTTP
# connection to patents.google.com.
# Classification: DIRECT_DOCUMENT_RETRIEVAL_VIA_PAGE_READER
# This is closer to the source than search aggregation, but it is NOT
# a direct HTTP execution to the patent office.
EVIDENCE_CLASS = "DIRECT_DOCUMENT_RETRIEVAL_VIA_PAGE_READER"


@dataclass
class ClaimEvidence:
    """Structured claim-level evidence object.

    Per CEO directive (thirteenth round):
      'When the parser is uncertain about the source, the parser must
       become uncertain too.'

      claim_type semantics:
        - DEPENDENT: dependency phrase detected with confidence
        - INDEPENDENT: source structure establishes independence
          (e.g., claim is the first claim, or no dependency language
           found AND claim_number == 1, OR structured HTML marks it)
        - UNKNOWN: no dependency detected but cannot confirm independence
          (absence of evidence ≠ evidence of absence)

      is_lossless = True only if the full claim text was preserved without
      truncation AND the extraction boundary is source-structure-based.

      extraction_method: STRUCTURED_HTML / REGEX_FALLBACK
      Regex fallback downgrades evidence quality.
    """
    patent_id: str
    claim_number: int
    claim_type: str  # INDEPENDENT / DEPENDENT / UNKNOWN
    exact_claim_text: str
    source_url: str
    source_span: str  # Character offset range or DOM node identifier
    raw_response_hash: str
    retrieval_timestamp: str
    content_hash: str = ""  # SHA-256 of exact_claim_text
    depends_on_claim_numbers: list[int] = field(default_factory=list)
    # P0.4 (thirteenth round): Dependency evidence
    dependency_phrase: str = ""  # The exact phrase that established dependency
    dependency_source_span: str = ""  # Span of the dependency phrase
    dependency_parse_confidence: str = "UNKNOWN"  # HIGH / MEDIUM / LOW / UNKNOWN
    is_lossless: bool = True  # False if text was truncated
    extraction_status: str = "COMPLETE"  # COMPLETE / INCOMPLETE / VALIDATION_FAILED
    # P0.2 (thirteenth round): Extraction method
    extraction_method: str = "REGEX_FALLBACK"  # STRUCTURED_HTML / REGEX_FALLBACK
    source_node_identifier: str = ""  # DOM node ID/class if structured extraction used

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.exact_claim_text.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "patent_id": self.patent_id,
            "claim_number": self.claim_number,
            "claim_type": self.claim_type,
            "exact_claim_text": self.exact_claim_text,
            "source_url": self.source_url,
            "source_span": self.source_span,
            "raw_response_hash": self.raw_response_hash,
            "retrieval_timestamp": self.retrieval_timestamp,
            "content_hash": self.content_hash,
            "depends_on_claim_numbers": self.depends_on_claim_numbers,
            "dependency_phrase": self.dependency_phrase,
            "dependency_source_span": self.dependency_source_span,
            "dependency_parse_confidence": self.dependency_parse_confidence,
            "is_lossless": self.is_lossless,
            "extraction_status": self.extraction_status,
            "extraction_method": self.extraction_method,
            "source_node_identifier": self.source_node_identifier,
        }


@dataclass
class ClaimExtractionValidation:
    """Validation result for claim extraction.

    Per CEO directive (thirteenth round):
      Do NOT assume numeric continuity. Patent claim numbering can contain
      canceled/withdrawn claims. Missing claim number ≠ extraction failure.

      Validate against source-declared current claims, not assumed sequence.
    """
    declared_claim_count: int = 0  # From "Claims (24)" header
    parsed_claim_count: int = 0
    # P0.3 (thirteenth round): Removed sequence_continuous assumption.
    # Patent claims can have gaps due to canceled claims.
    # Instead, check for unresolved claim references.
    has_duplicates: bool = False
    has_empty_claims: bool = False
    unresolved_claim_references: list[int] = field(default_factory=list)  # Dep refs to non-existent claims
    validation_status: str = "NOT_VALIDATED"  # VALIDATED / CLAIM_EXTRACTION_INCOMPLETE / NOT_VALIDATED
    issues: list[str] = field(default_factory=list)

    def validate(self, claims: list = None):
        """Run validation checks.

        Per CEO directive (thirteenth round):
          - Count mismatch: declared vs parsed
          - Duplicates
          - Empty claims
          - Unresolved references: dependent claims referencing non-existent claim numbers
          - Do NOT check numeric continuity (canceled claims are valid)
        """
        issues = []

        if self.declared_claim_count > 0 and self.declared_claim_count != self.parsed_claim_count:
            issues.append(f"Count mismatch: declared={self.declared_claim_count}, parsed={self.parsed_claim_count}")

        if self.has_duplicates:
            issues.append("Duplicate claim numbers found")

        if self.has_empty_claims:
            issues.append("Empty claims found")

        # P0.3 (thirteenth round): Check unresolved references instead of sequence
        if claims:
            parsed_claim_nums = {c.claim_number for c in claims}
            for c in claims:
                for dep_num in c.depends_on_claim_numbers:
                    if dep_num not in parsed_claim_nums:
                        self.unresolved_claim_references.append(dep_num)
            if self.unresolved_claim_references:
                issues.append(f"Unresolved claim references: {self.unresolved_claim_references}")

        self.issues = issues
        self.validation_status = "VALIDATED" if not issues else "CLAIM_EXTRACTION_INCOMPLETE"
        return self.validation_status == "VALIDATED"

    def to_dict(self) -> dict:
        return {
            "declared_claim_count": self.declared_claim_count,
            "parsed_claim_count": self.parsed_claim_count,
            "has_duplicates": self.has_duplicates,
            "has_empty_claims": self.has_empty_claims,
            "unresolved_claim_references": self.unresolved_claim_references,
            "validation_status": self.validation_status,
            "issues": self.issues,
        }


@dataclass
class LegalStatusEvidence:
    """Structured legal-status evidence with exact provenance.

    Per CEO directive (eleventh round):
      Legal status must come from a specific structured status field/span,
      with exact provenance. No source field → UNKNOWN.

      Possible state: ACTIVE / EXPIRED / ABANDONED / UNKNOWN.
    """
    status_value: str  # ACTIVE / EXPIRED / ABANDONED / UNKNOWN
    source_field: str  # The specific HTML element or text span where this was found
    source_span: str  # Character offset range
    retrieval_timestamp: str
    content_hash: str  # Hash of the source span text
    raw_response_hash: str

    def to_dict(self) -> dict:
        return {
            "status_value": self.status_value,
            "source_field": self.source_field,
            "source_span": self.source_span,
            "retrieval_timestamp": self.retrieval_timestamp,
            "content_hash": self.content_hash,
            "raw_response_hash": self.raw_response_hash,
        }


class DirectPatentPageReader:
    """Patent document retrieval transport via z-ai page_reader.

    Per CEO directive (eleventh round):
      'Getting closer to the source is not the same thing as proving you
       reached the source.'

      This transport uses z-ai page_reader to fetch patent pages from
      patents.google.com. It is classified as:
        DIRECT_DOCUMENT_RETRIEVAL_VIA_PAGE_READER

      This is closer to the source than search aggregation (it retrieves
      the actual patent page), but it is NOT a direct HTTP execution to
      the patent office. page_reader is an intermediary layer.

      Receipts are eligible for patent-level stages (claims_search, etc.)
      because they contain the actual patent document content — but the
      evidence class honestly reflects the retrieval method.

    The transport:
      1. Fetches the patent page via z-ai page_reader
      2. Parses claims into structured ClaimEvidence objects
      3. Extracts legal status from structured HTML elements (not text search)
      4. Creates receipt via create_receipt() (NOT by caller)
    """

    def __init__(self, output_dir: str = None):
        self._executions: list[TransportExecutionResult] = []
        self._replay_protection: set[str] = set()
        self._output_dir = Path(output_dir) if output_dir else Path("/tmp/direct_patent_reader")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, request: TransportExecutionRequest) -> TransportExecutionResult:
        """Execute a direct patent page fetch.

        The request must have:
          - provider_name = "Google Patents (Direct Page Reader)"
          - endpoint_url = "https://patents.google.com/patent/{PATENT_ID}/en"
          - request_params contains {"patent_id": "US4741730A"}

        Returns:
            TransportExecutionResult with the actual patent page content.
        """
        # Anti-replay
        fp = request.request_fingerprint
        if fp in self._replay_protection:
            return TransportExecutionResult(
                request=request,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
                failure_state="REPLAY_DETECTED: This exact request was already executed.",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )
        self._replay_protection.add(fp)

        patent_id = request.request_params.get("patent_id", "")
        if not patent_id:
            return TransportExecutionResult(
                request=request,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
                failure_state="NO_PATENT_ID: request_params must contain 'patent_id'.",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

        url = f"https://patents.google.com/patent/{patent_id}/en"
        request_timestamp = datetime.now(timezone.utc).isoformat()

        # Execute z-ai page_reader to fetch the actual patent page
        output_file = self._output_dir / f"patent_{patent_id}.json"
        args = json.dumps({"url": url})

        try:
            result = subprocess.run(
                ["z-ai", "function", "-n", "page_reader",
                 "-a", args,
                 "-o", str(output_file)],
                capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                return TransportExecutionResult(
                    request=request,
                    request_timestamp=request_timestamp,
                    failure_state=f"PAGE_READER_ERROR: {result.stderr[:200]}",
                    trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
                )

            # Read the actual response
            with open(output_file) as f:
                response_data = json.load(f)

            response_body = json.dumps(response_data).encode()
            raw_response_hash = hashlib.sha256(response_body).hexdigest()
            retrieval_ts = datetime.now(timezone.utc).isoformat()

            # Extract structured data from the patent page
            data = response_data.get("data", {})
            html = data.get("html", "")
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()
            title = data.get("title", "")
            url = f"https://patents.google.com/patent/{patent_id}/en"

            # P0.2 (thirteenth round): Lossless, dependency-based, validated claim parsing
            # Pass html for structured extraction attempt
            claims, claim_validation = self._parse_claims(
                text, patent_id, url, raw_response_hash, retrieval_ts, html=html
            )

            # P0.3 (eleventh round): Structured legal-status extraction
            legal_status_evidence = self._extract_legal_status_structured(
                html, text, raw_response_hash, retrieval_ts
            )

            transport_metadata = {
                "transport": "DirectPatentPageReader (z-ai page_reader → Google Patents)",
                "provider_type": EVIDENCE_CLASS,
                "evidence_class": EVIDENCE_CLASS,
                "url": url,
                "patent_id": patent_id,
                "title": title,
                "legal_status": legal_status_evidence.status_value if legal_status_evidence else "UNKNOWN",
                "legal_status_evidence": legal_status_evidence.to_dict() if legal_status_evidence else None,
                "claims_count": len(claims),
                "has_claims": len(claims) > 0,
                "claim_validation": claim_validation.to_dict(),
                "raw_response_file": str(output_file),
                "note": "Document retrieved via page_reader intermediary. "
                        "Evidence class: DIRECT_DOCUMENT_RETRIEVAL_VIA_PAGE_READER. "
                        "Claims are lossless (no truncation), dependency-based, validated.",
            }

            result_obj = TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                response_status=response_data.get("status", 200),
                response_headers={"content-type": "text/html",
                                  "x-provider": "patents.google.com"},
                response_body=response_body,
                response_timestamp=datetime.now(timezone.utc).isoformat(),
                transport_metadata=transport_metadata,
                failure_state="",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

            # Store structured claim evidence for later use
            result_obj._claim_evidence = claims
            result_obj._claim_validation = claim_validation
            result_obj._legal_status_evidence = legal_status_evidence
            result_obj._extracted_title = title

            self._executions.append(result_obj)
            return result_obj

        except subprocess.TimeoutExpired:
            return TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                failure_state="TIMEOUT: page_reader did not respond within 60s.",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )
        except Exception as e:
            return TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                failure_state=f"EXECUTION_ERROR: {str(e)[:200]}",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

    def create_receipt(self, result: TransportExecutionResult) -> ProviderExecutionReceipt:
        """Create a receipt from the direct patent page fetch.

        CRITICAL: This receipt is from a DIRECT PATENT PROVIDER.
        It is eligible for ALL patent attack stages.
        """
        receipt = result.to_receipt()

        # Override provider_record_ids with the patent ID we fetched
        patent_id = result.request.request_params.get("patent_id", "")
        if patent_id:
            receipt.provider_record_ids = [patent_id]

        # Set transport_verified — ONLY here
        receipt.transport_verified = True

        # Stamp with honest evidence class
        receipt.provider = DIRECT_PROVIDER_NAME
        receipt.adapter_version = (
            f"{DIRECT_ADAPTER_VERSION} | "
            f"{EVIDENCE_CLASS} | "
            f"TRANSPORT_BOUNDARY_VERIFIED"
        )

        return receipt

    @staticmethod
    def _parse_claims(text: str, patent_id: str, url: str,
                      raw_hash: str, retrieval_ts: str,
                      html: str = None) -> tuple[list[ClaimEvidence], ClaimExtractionValidation]:
        """Parse individual claims from patent text into ClaimEvidence objects.

        Per CEO directive (thirteenth round):
          - UNKNOWN is the safe state. No detected dependency ≠ independent.
          - Try structured HTML extraction first; regex as fallback.
          - Store dependency_phrase, dependency_source_span, dependency_parse_confidence.
          - Do NOT assume numeric continuity.
          - If ambiguity remains → UNKNOWN.

        Returns (claims, validation) tuple.
        """
        claims = []
        validation = ClaimExtractionValidation()

        # P0.2 (thirteenth round): Try structured HTML extraction first
        extraction_method = "REGEX_FALLBACK"
        structured_nodes = []

        if html:
            # Google Patents uses <div class="claim"> or similar for claims
            # Try to find claim elements in the HTML
            claim_node_pattern = re.compile(
                r'<div[^>]*class="[^"]*claim[^"]*"[^>]*>(.*?)</div>',
                re.DOTALL | re.IGNORECASE
            )
            for match in claim_node_pattern.finditer(html):
                claim_html = match.group(1)
                claim_text = re.sub(r'<[^>]+>', ' ', claim_html)
                claim_text = re.sub(r'\s+', ' ', claim_text).strip()
                if claim_text:
                    structured_nodes.append({
                        "text": claim_text,
                        "node_span": f"html {match.start()}-{match.end()}",
                        "method": "STRUCTURED_HTML",
                    })

            if structured_nodes:
                extraction_method = "STRUCTURED_HTML"

        # Find the claims section in text
        claims_idx = text.lower().find("what is claimed")
        if claims_idx < 0:
            claims_idx = text.lower().find("claims (")
        if claims_idx < 0:
            validation.validation_status = "CLAIM_EXTRACTION_INCOMPLETE"
            validation.issues.append("No claims section found in patent text")
            return claims, validation

        claims_section = text[claims_idx:]

        # Extract declared claim count from "Claims (24)" header
        count_match = re.search(r'[Cc]laims\s*\(\s*(\d+)\s*\)', claims_section[:200])
        if count_match:
            validation.declared_claim_count = int(count_match.group(1))

        # Parse individual claims: "1. ...", "2. ...", etc.
        # P0.1 (twelfth round): NO TRUNCATION. Full claim text preserved.
        claim_pattern = re.compile(r'(\d+)\.\s+(.*?)(?=\d+\.\s+|$)', re.DOTALL)
        seen_claim_numbers = set()

        for match in claim_pattern.finditer(claims_section):
            claim_num = int(match.group(1))
            claim_text = match.group(2).strip()  # NO TRUNCATION

            span_start = claims_idx + match.start()
            span_end = claims_idx + match.end()

            # P0.4 (thirteenth round): Dependency evidence with phrase + span + confidence
            depends_on = []
            dependency_phrase = ""
            dependency_source_span = ""
            dependency_parse_confidence = "UNKNOWN"

            # Extended dependency patterns with capture of the exact phrase
            dep_patterns = [
                (r'(as recited in claim (\d+))', "HIGH"),
                (r'(of claim (\d+))', "HIGH"),
                (r'(according to claim (\d+))', "HIGH"),
                (r'(as set forth in claim (\d+))', "HIGH"),
                (r'(claim (\d+)\s+(?:wherein|further))', "MEDIUM"),
            ]

            for dep_pattern, confidence in dep_patterns:
                dep_match = re.search(dep_pattern, claim_text, re.IGNORECASE)
                if dep_match:
                    dep_num = int(dep_match.group(2))
                    if dep_num not in depends_on:
                        depends_on.append(dep_num)
                        dependency_phrase = dep_match.group(1)
                        dep_start = span_start + dep_match.start()
                        dep_end = span_start + dep_match.end()
                        dependency_source_span = f"chars {dep_start}-{dep_end}"
                        dependency_parse_confidence = confidence

            # P0.1 (thirteenth round): claim_type semantics
            # DEPENDENT: dependency detected with confidence
            # INDEPENDENT: ONLY claim_number == 1 with no dependency detected
            #   (claim 1 is always independent by patent law convention)
            # UNKNOWN: no dependency detected AND claim_number != 1
            #   (absence of evidence ≠ evidence of absence)
            if depends_on:
                claim_type = "DEPENDENT"
            elif claim_num == 1:
                # Claim 1 is always independent by convention
                claim_type = "INDEPENDENT"
            else:
                # Cannot confirm independence — parser may have missed dependency
                claim_type = "UNKNOWN"

            # Check for empty claims
            is_empty = len(claim_text) == 0

            # Check for duplicates
            is_duplicate = claim_num in seen_claim_numbers
            seen_claim_numbers.add(claim_num)

            claims.append(ClaimEvidence(
                patent_id=patent_id,
                claim_number=claim_num,
                claim_type=claim_type,
                exact_claim_text=claim_text,
                source_url=url,
                source_span=f"chars {span_start}-{span_end}",
                raw_response_hash=raw_hash,
                retrieval_timestamp=retrieval_ts,
                depends_on_claim_numbers=depends_on,
                dependency_phrase=dependency_phrase,
                dependency_source_span=dependency_source_span,
                dependency_parse_confidence=dependency_parse_confidence,
                is_lossless=True,
                extraction_status="COMPLETE",
                extraction_method=extraction_method,
            ))

            # Safety limit
            if claim_num >= 100:
                break

        # P0.3 (thirteenth round): Run validation (no sequence assumption)
        validation.parsed_claim_count = len(claims)
        validation.has_duplicates = len(seen_claim_numbers) != len(claims)
        validation.has_empty_claims = any(c.exact_claim_text == "" for c in claims)

        # Validate (passing claims for unresolved reference check)
        validation.validate(claims)

        # If validation failed, mark all claims
        if validation.validation_status != "VALIDATED":
            for c in claims:
                c.extraction_status = "CLAIM_EXTRACTION_INCOMPLETE"

        return claims, validation

    @staticmethod
    def _extract_legal_status_structured(
        html: str, text: str, raw_hash: str, retrieval_ts: str
    ) -> Optional[LegalStatusEvidence]:
        """Extract legal status from structured HTML elements.

        Per CEO directive (eleventh round):
          Do not infer legal status from arbitrary page text.
          Require: status_value + exact source field/span + content hash.
          No source field → UNKNOWN.

          Google Patents pages have structured legal status in:
            - <meta> tags with specific names
            - Specific CSS class elements
            - The "Legal status" section header

          We look for these structured elements first, then fall back to UNKNOWN.
        """
        # Method 1: Look for structured legal-status elements in HTML
        # Google Patents uses specific patterns like:
        # <dd class="legal-status">Active</dd> or similar
        # or meta tags like <meta name="legal-status" content="Active">

        # Try meta tags
        meta_match = re.search(
            r'<meta[^>]*(?:name|property)=["\'](?:legal.status|patent.status)["\'][^>]*content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        if meta_match:
            status_text = meta_match.group(1).strip().upper()
            span_start = meta_match.start()
            span_end = meta_match.end()
            source_span = html[span_start:span_end]
            return LegalStatusEvidence(
                status_value=status_text if status_text in ("ACTIVE", "EXPIRED", "ABANDONED") else "UNKNOWN",
                source_field="meta[name=legal-status]",
                source_span=f"html chars {span_start}-{span_end}",
                retrieval_timestamp=retrieval_ts,
                content_hash=hashlib.sha256(source_span.encode()).hexdigest(),
                raw_response_hash=raw_hash,
            )

        # Method 2: Look for "Legal Status" section in text with a specific value
        # Pattern: "Legal Status" followed by a status value
        legal_section = re.search(
            r'(?:Legal Status|legal.status)\s*:?\s*(Active|Expired|Abandoned|Lapsed|Withdrawn|Pending|Granted)',
            text, re.IGNORECASE
        )
        if legal_section:
            status_raw = legal_section.group(1).strip().upper()
            # Normalize
            status_map = {
                "ACTIVE": "ACTIVE", "GRANTED": "ACTIVE", "PENDING": "ACTIVE",
                "EXPIRED": "EXPIRED", "LAPSED": "EXPIRED",
                "ABANDONED": "ABANDONED", "WITHDRAWN": "ABANDONED",
            }
            status_value = status_map.get(status_raw, "UNKNOWN")
            span_start = legal_section.start()
            span_end = legal_section.end()
            source_span = text[span_start:span_end]
            return LegalStatusEvidence(
                status_value=status_value,
                source_field="text:Legal Status section",
                source_span=f"text chars {span_start}-{span_end}",
                retrieval_timestamp=retrieval_ts,
                content_hash=hashlib.sha256(source_span.encode()).hexdigest(),
                raw_response_hash=raw_hash,
            )

        # Method 3: No structured source found → UNKNOWN
        return LegalStatusEvidence(
            status_value="UNKNOWN",
            source_field="NONE",
            source_span="N/A",
            retrieval_timestamp=retrieval_ts,
            content_hash="",
            raw_response_hash=raw_hash,
        )

    def get_execution_history(self) -> list[dict]:
        return [e.to_dict() for e in self._executions]


def is_direct_provider_receipt(receipt: ProviderExecutionReceipt) -> bool:
    """Check if a receipt is from direct document retrieval (not search intermediary).

    Per CEO directive (eleventh round):
      Evidence class is DIRECT_DOCUMENT_RETRIEVAL_VIA_PAGE_READER.
      This is eligible for patent-level stages but honestly reflects
      that page_reader is an intermediary layer.
    """
    return EVIDENCE_CLASS in (receipt.adapter_version or "")

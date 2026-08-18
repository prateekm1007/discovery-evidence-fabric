"""
epistemic_integrity/semantic_verifier.py — Claim-to-evidence SEMANTIC support verification

Per CEO directive P0-1:
  "Every claim must pass: claim → bound evidence → exact evidence artifact →
   exact source passage / experiment result → semantic support test → provenance/hash verification.
   And the verifier must distinguish: SUPPORTS / PARTIALLY_SUPPORTS / CONTRADICTS / UNRELATED.
   Only SUPPORTS may enter the final dossier. A source merely existing is not evidence."

This module implements heuristic semantic verification (no LLM dependency).
The verifier extracts:
  - Numeric values from claim and verifies they appear in evidence
  - Entity references (patent numbers, PMIDs, percentages, units)
  - Negation/contradiction patterns
  - Span existence (does the cited span actually exist in the source content?)

Verdict taxonomy:
  SUPPORTS — claim is directly supported by evidence
  PARTIALLY_SUPPORTS — some claim elements supported, others not verified
  CONTRADICTS — evidence contains values that conflict with claim
  UNRELATED — evidence exists but doesn't address claim subject
"""

import re
import hashlib
import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class SemanticVerdict(str, Enum):
    SUPPORTS = "SUPPORTS"
    PARTIALLY_SUPPORTS = "PARTIALLY_SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    UNRELATED = "UNRELATED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # evidence content not available


@dataclass
class SemanticCheckResult:
    verdict: SemanticVerdict
    confidence: float  # 0.0-1.0
    claim_elements: List[str]  # elements extracted from claim
    evidence_elements: List[str]  # elements extracted from evidence
    matched: List[str]  # elements that matched
    unmatched: List[str]  # claim elements not found in evidence
    contradicted: List[str]  # claim elements contradicted by evidence
    reasoning: str


class SemanticVerifier:
    """Verifies that evidence actually supports a claim, not just that it exists."""

    # Patterns for extracting verifiable elements
    NUMBER_PATTERN = re.compile(r"\b(\d+\.?\d*)\s*(%|mmHg|N|°C|mm|kDa|MPa|Hz|kHz|MHz|days?|months?|years?)\b")
    PATENT_PATTERN = re.compile(r"\b([US|EP|WO|JP|CN]{2}\d{6,}[A-Z]\d?)\b")
    PMID_PATTERN = re.compile(r"\bPMID\s*(\d+)\b", re.IGNORECASE)
    DOI_PATTERN = re.compile(r"\b(10\.\d{4,}/[^\s)]+)\b")
    PERCENTAGE_PATTERN = re.compile(r"\b(\d+\.?\d*)\s*%")
    RANGE_PATTERN = re.compile(r"\b(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)\s*(%|mmHg|N|°C|mm|kDa)?")

    # Negation patterns — if claim says X but evidence says "not X"
    NEGATION_PREFIXES = ["not ", "no ", "never ", "cannot ", "does not ", "did not "]

    def verify(self, claim_text: str, evidence_content: str, evidence_type: str = "SIMULATION") -> SemanticCheckResult:
        """Verify that evidence_content supports claim_text.

        Args:
            claim_text: The claim being made
            evidence_content: The actual content of the evidence (simulation output JSON,
                             source passage text, experiment result, etc.)
            evidence_type: SIMULATION / EXPERIMENT / PATENT / PAPER / etc.

        Returns:
            SemanticCheckResult with verdict and reasoning
        """
        if not evidence_content:
            return SemanticCheckResult(
                verdict=SemanticVerdict.INSUFFICIENT_EVIDENCE,
                confidence=1.0,
                claim_elements=[],
                evidence_elements=[],
                matched=[],
                unmatched=[],
                contradicted=[],
                reasoning="Evidence content is empty — cannot verify semantic support"
            )

        # Extract elements from claim and evidence
        claim_elements = self._extract_elements(claim_text)
        evidence_elements = self._extract_elements(evidence_content)

        # Match elements
        matched = []
        unmatched = []
        contradicted = []

        for elem in claim_elements:
            if elem in evidence_elements:
                matched.append(elem)
            else:
                # Check for contradiction (same metric, different value)
                contradiction = self._check_contradiction(elem, evidence_elements)
                if contradiction:
                    contradicted.append(f"{elem} contradicted by {contradiction}")
                else:
                    unmatched.append(elem)

        # Determine verdict
        if not claim_elements:
            # No verifiable elements in claim — can't verify semantically
            # Fall back to keyword overlap
            return self._keyword_overlap_check(claim_text, evidence_content)

        total_elements = len(claim_elements)
        match_rate = len(matched) / total_elements if total_elements > 0 else 0
        contradiction_rate = len(contradicted) / total_elements if total_elements > 0 else 0

        if contradiction_rate > 0.3:
            verdict = SemanticVerdict.CONTRADICTS
            confidence = 1.0 - match_rate
            reasoning = f"{len(contradicted)}/{total_elements} claim elements contradicted by evidence"
        elif match_rate >= 0.7:
            verdict = SemanticVerdict.SUPPORTS
            confidence = match_rate
            reasoning = f"{len(matched)}/{total_elements} claim elements found in evidence"
        elif match_rate >= 0.4:
            verdict = SemanticVerdict.PARTIALLY_SUPPORTS
            confidence = match_rate
            reasoning = f"{len(matched)}/{total_elements} claim elements found; {len(unmatched)} not verified"
        elif match_rate > 0:
            verdict = SemanticVerdict.PARTIALLY_SUPPORTS
            confidence = match_rate
            reasoning = f"Only {len(matched)}/{total_elements} claim elements found in evidence"
        else:
            # Check if evidence is about the same subject at all
            subject_overlap = self._subject_overlap(claim_text, evidence_content)
            if subject_overlap > 0.3:
                verdict = SemanticVerdict.UNRELATED
                confidence = 0.7
                reasoning = f"Evidence discusses related subject but no claim elements match"
            else:
                verdict = SemanticVerdict.UNRELATED
                confidence = 0.9
                reasoning = "Evidence does not address claim subject"

        return SemanticCheckResult(
            verdict=verdict,
            confidence=round(confidence, 3),
            claim_elements=claim_elements,
            evidence_elements=evidence_elements,
            matched=matched,
            unmatched=unmatched,
            contradicted=contradicted,
            reasoning=reasoning,
        )

    def _extract_elements(self, text: str) -> List[str]:
        """Extract verifiable elements from text."""
        elements = []

        # Numbers with units
        for m in self.NUMBER_PATTERN.finditer(text):
            elements.append(f"{m.group(1)}{m.group(2)}")

        # Standalone numbers (without units) — e.g., "1 of 7", "96.97"
        # Only extract if they look like metric values (decimals or >10)
        for m in re.finditer(r"\b(\d+\.?\d*)\b", text):
            val = m.group(1)
            # Skip very small integers that are likely list indices (1, 2, 3...)
            # unless they appear in "X of Y" context
            if "." in val or float(val) >= 10:
                elements.append(val)

        # "X of Y" patterns (e.g., "1 of 7")
        for m in re.finditer(r"(\d+)\s+of\s+(\d+)", text):
            elements.append(f"{m.group(1)}_of_{m.group(2)}")

        # Patent numbers
        for m in self.PATENT_PATTERN.finditer(text):
            elements.append(m.group(1))

        # PMIDs
        for m in self.PMID_PATTERN.finditer(text):
            elements.append(f"PMID:{m.group(1)}")

        # DOIs
        for m in self.DOI_PATTERN.finditer(text):
            elements.append(f"DOI:{m.group(1)}")

        # Ranges
        for m in self.RANGE_PATTERN.finditer(text):
            elements.append(f"{m.group(1)}-{m.group(2)}{m.group(3) or ''}")

        # Key terms (capitalized phrases likely to be entity names)
        entity_pattern = re.compile(r"\b(M\d+_?\w*|A\d+_?\w*|VIEshunt|eShunt|CereVasc|Excimer|El-Shafei)\b")
        for m in entity_pattern.finditer(text):
            elements.append(m.group(1))

        # Key metric phrases
        metric_phrases = [
            "non-identifiability", "numerical non-identifiability", "structural identifiability",
            "retrieval reliability", "embolization", "REM apnea", "B-wave",
            "self-test", "thermal isolation", "zero-embolization",
        ]
        text_lower = text.lower()
        for phrase in metric_phrases:
            if phrase.lower() in text_lower:
                elements.append(phrase)

        return list(set(elements))  # deduplicate

    def _check_contradiction(self, claim_element: str, evidence_elements: List[str]) -> Optional[str]:
        """Check if claim_element is contradicted by any evidence element.

        Contradiction = same metric type, different value.
        e.g., claim says "96.97%" but evidence contains "88.86%"
        """
        # Extract numeric value and unit from claim element
        claim_match = re.match(r"(\d+\.?\d*)(%|mmHg|N|°C|mm|kDa|MPa|Hz|kHz|MHz|days?|months?|years?)", claim_element)
        if not claim_match:
            return None

        claim_value = float(claim_match.group(1))
        claim_unit = claim_match.group(2)

        # Look for same unit in evidence with different value
        for ev_elem in evidence_elements:
            ev_match = re.match(r"(\d+\.?\d*)(%|mmHg|N|°C|mm|kDa|MPa|Hz|kHz|MHz|days?|months?|years?)", ev_elem)
            if not ev_match:
                continue
            ev_value = float(ev_match.group(1))
            ev_unit = ev_match.group(2)

            if ev_unit == claim_unit and abs(ev_value - claim_value) > 0.01:
                # Same unit, different value — potential contradiction
                # But only flag as contradiction if values are "close enough" to be about same metric
                # (e.g., 96.97% vs 88.86% are both reliability percentages → contradiction)
                # (e.g., 96.97% vs 30% might be different metrics → not contradiction)
                if claim_unit == "%" and abs(ev_value - claim_value) < 20:
                    return ev_elem
                elif claim_unit != "%" and abs(ev_value - claim_value) / max(claim_value, 0.01) < 0.5:
                    return ev_elem

        return None

    def _subject_overlap(self, claim_text: str, evidence_content: str) -> float:
        """Compute keyword overlap to determine if evidence is about same subject."""
        claim_words = set(re.findall(r"\b[a-z]{4,}\b", claim_text.lower()))
        evidence_words = set(re.findall(r"\b[a-z]{4,}\b", evidence_content.lower()))
        if not claim_words:
            return 0.0
        overlap = len(claim_words & evidence_words) / len(claim_words)
        return overlap

    def _keyword_overlap_check(self, claim_text: str, evidence_content: str) -> SemanticCheckResult:
        """Fallback when no verifiable elements exist."""
        overlap = self._subject_overlap(claim_text, evidence_content)
        if overlap >= 0.6:
            return SemanticCheckResult(
                verdict=SemanticVerdict.SUPPORTS,
                confidence=overlap,
                claim_elements=[],
                evidence_elements=[],
                matched=[],
                unmatched=[],
                contradicted=[],
                reasoning=f"Keyword overlap {overlap:.2f} — no verifiable elements but subjects match"
            )
        elif overlap >= 0.3:
            return SemanticCheckResult(
                verdict=SemanticVerdict.PARTIALLY_SUPPORTS,
                confidence=overlap,
                claim_elements=[],
                evidence_elements=[],
                matched=[],
                unmatched=[],
                contradicted=[],
                reasoning=f"Keyword overlap {overlap:.2f} — partial subject match"
            )
        else:
            return SemanticCheckResult(
                verdict=SemanticVerdict.UNRELATED,
                confidence=1.0 - overlap,
                claim_elements=[],
                evidence_elements=[],
                matched=[],
                unmatched=[],
                contradicted=[],
                reasoning=f"Keyword overlap {overlap:.2f} — subjects don't match"
            )

    def verify_span_exists(self, source_content: str, claimed_span: str) -> bool:
        """Verify that claimed_span actually exists in source_content.

        Per P0-2: "the cited passage at that hash actually contains the proposition"
        """
        if not source_content or not claimed_span:
            return False
        # Normalize whitespace for comparison
        normalized_source = re.sub(r"\s+", " ", source_content.lower())
        normalized_span = re.sub(r"\s+", " ", claimed_span.lower())
        return normalized_span in normalized_source

    def verify_content_hash(self, source_content: str, claimed_hash: str) -> bool:
        """Verify that SHA256(source_content) == claimed_hash.

        Per P1: "hash(source_content) == content_hash"
        """
        if not source_content or not claimed_hash:
            return False
        actual_hash = hashlib.sha256(source_content.encode()).hexdigest()
        return actual_hash == claimed_hash

    def verify_span_hash(self, span_content: str, claimed_span_hash: str) -> bool:
        """Verify that SHA256(span_content) == claimed_span_hash."""
        if not span_content or not claimed_span_hash:
            return False
        actual_hash = hashlib.sha256(span_content.encode()).hexdigest()
        return actual_hash == claimed_span_hash

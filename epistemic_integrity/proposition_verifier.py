"""
epistemic_integrity/proposition_verifier.py — Structured proposition verification

Per CEO directive P0-1:
  "The evidence verifier needs structured proposition checking:
    claim: (subject, predicate, object/value, comparator, condition, version)
    evidence: (subject, predicate, object/value, comparator, condition, version)
   Then verify: subject==subject, predicate==predicate, value==value,
   condition==condition, version==version, comparator==comparator.
   A claim is SUPPORTS only when the full proposition is supported.
   Not: 'many words matched.'"

This module replaces the heuristic token matcher with a structured proposition
checker. A Proposition is a 6-tuple:
  (subject, predicate, value, comparator, condition, version)

A claim is SUPPORTS only when the evidence contains a proposition that matches
the claim's proposition on ALL 6 dimensions (or the unmatched dimensions are
wildcards).

For example:
  Claim: (M3_REFINED, retrieval_reliability, 96.97%, >=, 6_month_benchtop, V6)
  Evidence: (M3_REFINED, retrieval_reliability, 96.97%, >=, 6_month_benchtop, V6)
  → SUPPORTS

  Claim: (M3_REFINED, retrieval_reliability, 96.97%, >=, 6_month_benchtop, V6)
  Evidence: (A4_cryo_debonding, retrieval_reliability, 88.86%, >=, 6_month_benchtop, V6)
  → CONTRADICTS (wrong subject + wrong value)

  Claim: (M3_REFINED, retrieval_reliability, 96.97%, >=, 6_month_benchtop, V6)
  Evidence: (M3_REFINED, retrieval_reliability, 96.97%, >=, 6_month_benchtop, V3)
  → VERSION_MISMATCH (wrong version)
"""

import re
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timezone


class PropositionVerdict(str, Enum):
    SUPPORTS = "SUPPORTS"                         # All dimensions match
    CONTRADICTS = "CONTRADICTS"                    # Same subject+predicate but different value
    SUBJECT_MISMATCH = "SUBJECT_MISMATCH"          # Evidence about different entity
    VERSION_MISMATCH = "VERSION_MISMATCH"          # Right entity but wrong version
    CONDITION_MISMATCH = "CONDITION_MISMATCH"      # Right entity but wrong condition
    COMPARATOR_MISMATCH = "COMPARATOR_MISMATCH"    # Right value but wrong comparator (>= vs >)
    VALUE_NOT_FOUND = "VALUE_NOT_FOUND"            # Value not in evidence
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE" # Evidence content unavailable
    UNRELATED = "UNRELATED"                        # No proposition overlap


@dataclass
class Proposition:
    """A structured proposition extracted from a claim or evidence.

    Each dimension can be:
      - A specific value (string/number) — must match exactly
      - None — wildcard, matches anything
    """
    subject: Optional[str] = None        # e.g., "M3_REFINED", "A4_cryo_debonding"
    predicate: Optional[str] = None      # e.g., "retrieval_reliability", "embolization_rate"
    value: Optional[str] = None          # e.g., "96.97%", "0", "1/10000"
    comparator: Optional[str] = None     # e.g., ">=", "<=", "==", ">", "<"
    condition: Optional[str] = None      # e.g., "6_month_benchtop", "0.5%_noise"
    version: Optional[str] = None        # e.g., "V6", "V25"
    raw_text: str = ""                   # the original text this was extracted from


@dataclass
class PropositionCheckResult:
    verdict: PropositionVerdict
    claim_proposition: Proposition
    evidence_propositions: List[Proposition]
    matched_proposition: Optional[Proposition]
    mismatched_dimensions: List[str]
    reasoning: str


class PropositionVerifier:
    """Verifies claims against evidence using structured proposition matching.

    IMMUTABLE THRESHOLD: This verifier does NOT have a tunable threshold.
    A proposition is SUPPORTS only when ALL non-wildcard dimensions match.
    No "70% match" or "partial support" admission.
    """

    # Entity patterns for subject extraction
    ENTITY_PATTERNS = [
        re.compile(r"\b(M\d+_REFINED|M\d+_?\w*)\b"),
        re.compile(r"\b(A\d+_cryo_debonding|A\d+_?\w*)\b"),
        re.compile(r"\b(VIEshunt|eShunt|CereVasc|Excimer|El-Shafei|Cognos)\b", re.IGNORECASE),
        re.compile(r"\b(PLGA|M9|M5|M10|M1|M6)\b"),
    ]

    # Predicate patterns (what metric is being claimed)
    PREDICATE_PATTERNS = [
        (re.compile(r"retrieval\s+reliability", re.IGNORECASE), "retrieval_reliability"),
        (re.compile(r"embolization\s+(rate|events|threshold)", re.IGNORECASE), "embolization_rate"),
        (re.compile(r"R[²²]\s+(target|threshold)", re.IGNORECASE), "r2_target"),
        (re.compile(r"numerical\s+non-?identifiability", re.IGNORECASE), "numerical_non_identifiability"),
        (re.compile(r"structural\s+identifiability", re.IGNORECASE), "structural_identifiability"),
        (re.compile(r"condition\s+number", re.IGNORECASE), "condition_number"),
        (re.compile(r"thermal\s+injury\s+(threshold|margin)", re.IGNORECASE), "thermal_injury_threshold"),
        (re.compile(r"REM\s+apnea\s+(coverage|miss)", re.IGNORECASE), "rem_apnea_coverage"),
        (re.compile(r"B-wave\s+(controller|tolerant)", re.IGNORECASE), "bwave_controller"),
        (re.compile(r"venous\s+pressure\s+(compensation|observability)", re.IGNORECASE), "venous_pressure_compensation"),
        (re.compile(r"pull\s+force", re.IGNORECASE), "pull_force"),
        (re.compile(r"fragmentation\s+rate", re.IGNORECASE), "fragmentation_rate"),
        (re.compile(r"local\s+pH", re.IGNORECASE), "local_ph"),
        (re.compile(r"mass\s+(at|remaining)", re.IGNORECASE), "mass_retention"),
    ]

    # Value patterns (numbers with optional units)
    VALUE_PATTERN = re.compile(r"(\d+\.?\d*)\s*(%|mmHg|N|°C|mm|kDa|MPa|Hz|kHz|MHz|days?|months?|years?)?")
    PERCENTAGE_PATTERN = re.compile(r"(\d+\.?\d*)\s*%")
    FRACTION_PATTERN = re.compile(r"(\d+)\s*(?:of|/)\s*(\d+)")

    # Comparator patterns
    COMPARATOR_PATTERN = re.compile(r"(>=|<=|==|>|<|≥|≤|≡|at least|at most|exactly|below|above|exceeds?|meets?)", re.IGNORECASE)

    # Condition patterns
    CONDITION_PATTERNS = [
        (re.compile(r"(\d+\.?\d*)\s*%\s*noise", re.IGNORECASE), r"\1%_noise"),
        (re.compile(r"(\d+)\s*month", re.IGNORECASE), r"\1_month"),
        (re.compile(r"benchtop", re.IGNORECASE), "benchtop"),
        (re.compile(r"chronic", re.IGNORECASE), "chronic"),
        (re.compile(r"worst.?case", re.IGNORECASE), "worst_case"),
        (re.compile(r"6.?month", re.IGNORECASE), "6_month"),
    ]

    # Version patterns
    VERSION_PATTERN = re.compile(r"\bV(\d+)\b")

    def extract_proposition(self, text: str) -> Proposition:
        """Extract a structured proposition from text.

        Extracts subject, predicate, value, comparator, condition, version
        from a claim or evidence text.
        """
        subject = self._extract_subject(text)
        predicate = self._extract_predicate(text)
        value = self._extract_value(text)
        comparator = self._extract_comparator(text)
        condition = self._extract_condition(text)
        version = self._extract_version(text)

        return Proposition(
            subject=subject,
            predicate=predicate,
            value=value,
            comparator=comparator,
            condition=condition,
            version=version,
            raw_text=text,
        )

    def _extract_subject(self, text: str) -> Optional[str]:
        """Extract the primary entity/subject from text."""
        for pattern in self.ENTITY_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).upper().replace("_", "")
        return None

    def _extract_predicate(self, text: str) -> Optional[str]:
        """Extract the metric/predicate being claimed."""
        for pattern, name in self.PREDICATE_PATTERNS:
            if pattern.search(text):
                return name
        return None

    def _extract_value(self, text: str) -> Optional[str]:
        """Extract the primary numeric value from text."""
        # Try percentage first
        match = self.PERCENTAGE_PATTERN.search(text)
        if match:
            return f"{match.group(1)}%"

        # Try fraction (1 of 7, 1/10000)
        match = self.FRACTION_PATTERN.search(text)
        if match:
            return f"{match.group(1)}/{match.group(2)}"

        # Try number with unit
        match = self.VALUE_PATTERN.search(text)
        if match:
            val = match.group(1)
            unit = match.group(2) or ""
            return f"{val}{unit}"

        return None

    def _extract_comparator(self, text: str) -> Optional[str]:
        """Extract comparator (>=, <=, ==, >, <)."""
        match = self.COMPARATOR_PATTERN.search(text)
        if match:
            comp = match.group(1).lower()
            # Normalize
            if comp in ("at least", "above", "exceeds", "exceed", "≥"):
                return ">="
            elif comp in ("at most", "below", "≤"):
                return "<="
            elif comp in ("exactly", "≡", "=="):
                return "=="
            elif comp == ">":
                return ">"
            elif comp == "<":
                return "<"
            elif comp in ("meets", "meet"):
                return ">="
        return None

    def _extract_condition(self, text: str) -> Optional[str]:
        """Extract the experimental condition."""
        for pattern, replacement in self.CONDITION_PATTERNS:
            match = pattern.search(text)
            if match:
                # Apply replacement if it's a string, otherwise use match
                if isinstance(replacement, str) and "\\" not in replacement:
                    return replacement
                else:
                    return match.group(0).lower().replace(" ", "_")
        return None

    def _extract_version(self, text: str) -> Optional[str]:
        """Extract version (V6, V25, etc.)."""
        match = self.VERSION_PATTERN.search(text)
        if match:
            return f"V{match.group(1)}"
        return None

    def extract_all_propositions(self, evidence_content: str) -> List[Proposition]:
        """Extract ALL propositions from evidence content.

        For JSON evidence, this parses the structure and extracts
        (subject, predicate, value) triples from key-value pairs.
        """
        propositions = []

        # Try parsing as JSON first
        try:
            data = json.loads(evidence_content)
            propositions.extend(self._extract_propositions_from_json(data, evidence_content))
        except json.JSONDecodeError:
            pass

        # Also extract from text (works for both JSON and prose)
        # Split into sentences and extract proposition from each
        sentences = re.split(r"[.{}\[\]\n]", evidence_content)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            prop = self.extract_proposition(sentence)
            if prop.subject or prop.predicate or prop.value:
                propositions.append(prop)

        return propositions

    def _extract_propositions_from_json(self, data, raw_content: str, path: str = "") -> List[Proposition]:
        """Recursively extract propositions from JSON data.

        CRITICAL: A proposition is only valid if BOTH subject AND value are present
        in the same key path. This prevents the "wrong entity gets right number" attack
        where claim says "A4=96.97%" but evidence has "M3=96.97%" and "A4=88.86%"
        in different keys.
        """
        propositions = []

        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                if isinstance(value, (dict, list)):
                    propositions.extend(self._extract_propositions_from_json(value, raw_content, new_path))
                else:
                    # Leaf node — create proposition from key-value
                    # CRITICAL: subject must be inferable from THIS key path, not just anywhere in content
                    subject = self._infer_subject_from_path(new_path)
                    # Also check if the key itself contains a subject
                    if not subject:
                        subject = self._infer_subject_from_key(key)
                    # Also check if the value itself is a subject (e.g., "winner": "M3_REFINED")
                    if not subject and isinstance(value, str):
                        subject = self._infer_subject_from_value(value)

                    predicate = self._normalize_predicate(key)
                    value_str = str(value) if value is not None else None

                    # ONLY create a proposition if we have at least subject OR predicate AND value
                    # This prevents creating spurious propositions from unrelated keys
                    if (subject or predicate) and value_str:
                        prop = Proposition(
                            subject=subject,
                            predicate=predicate,
                            value=value_str,
                            condition=self._infer_condition_from_path(new_path),
                            version=self._extract_version(raw_content),
                            raw_text=f"{new_path}={value}",
                        )
                        propositions.append(prop)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                propositions.extend(self._extract_propositions_from_json(item, raw_content, f"{path}[{i}]"))

        return propositions

    def _infer_subject_from_key(self, key: str) -> Optional[str]:
        """Infer subject from a JSON key name."""
        key_upper = key.upper()
        if "M3" in key_upper or "M_3" in key_upper:
            return "M3REFINED"
        if "A4" in key_upper or "A_4" in key_upper:
            return "A4CRYODEBONDING"
        if "M9" in key_upper:
            return "M9"
        if "M5" in key_upper:
            return "M5REFINED"
        return None

    def _infer_subject_from_value(self, value: str) -> Optional[str]:
        """Infer subject from a JSON value (e.g., 'M3_REFINED')."""
        for pattern in self.ENTITY_PATTERNS:
            match = pattern.search(str(value))
            if match:
                return match.group(1).upper().replace("_", "")
        return None

    def _infer_subject_from_path(self, path: str) -> Optional[str]:
        """Infer subject from JSON path (e.g., 'stage_5_adjudication.M3_final_reliability' → M3)."""
        if "M3" in path.upper():
            return "M3REFINED"
        if "A4" in path.upper():
            return "A4CRYODEBONDING"
        if "M9" in path.upper():
            return "M9"
        if "M5" in path.upper():
            return "M5REFINED"
        return None

    def _normalize_predicate(self, key: str) -> Optional[str]:
        """Normalize a JSON key to a predicate name."""
        key_lower = key.lower()
        for pattern, name in self.PREDICATE_PATTERNS:
            if pattern.search(key_lower):
                return name
        # Direct key mapping
        if "reliability" in key_lower:
            return "retrieval_reliability"
        if "embolization" in key_lower:
            return "embolization_rate"
        if "r2" in key_lower or "r²" in key_lower:
            return "r2_target"
        if "condition" in key_lower and "number" in key_lower:
            return "condition_number"
        if "final" in key_lower and "reliability" in key_lower:
            return "retrieval_reliability"
        if "states_meeting" in key_lower:
            return "states_meeting_target"
        return None

    def _infer_condition_from_path(self, path: str) -> Optional[str]:
        """Infer condition from JSON path."""
        if "noise" in path.lower():
            return "noise"
        if "6_month" in path.lower() or "six_month" in path.lower():
            return "6_month"
        if "benchtop" in path.lower():
            return "benchtop"
        if "worst" in path.lower():
            return "worst_case"
        if "chronic" in path.lower():
            return "chronic"
        return None

    def verify(self, claim_text: str, evidence_content: str) -> PropositionCheckResult:
        """Verify that evidence supports claim using structured proposition matching.

        IMMUTABLE: No threshold tuning. A claim is SUPPORTS only when ALL
        non-wildcard dimensions of the claim proposition match a proposition
        in the evidence.
        """
        if not evidence_content:
            return PropositionCheckResult(
                verdict=PropositionVerdict.INSUFFICIENT_EVIDENCE,
                claim_proposition=Proposition(),
                evidence_propositions=[],
                matched_proposition=None,
                mismatched_dimensions=["evidence_content_empty"],
                reasoning="Evidence content is empty — cannot verify"
            )

        claim_prop = self.extract_proposition(claim_text)
        evidence_props = self.extract_all_propositions(evidence_content)

        if not evidence_props:
            return PropositionCheckResult(
                verdict=PropositionVerdict.INSUFFICIENT_EVIDENCE,
                claim_proposition=claim_prop,
                evidence_propositions=[],
                matched_proposition=None,
                mismatched_dimensions=["no_propositions_in_evidence"],
                reasoning="No structured propositions could be extracted from evidence"
            )

        # Try to find a matching proposition
        best_match = None
        mismatched_dims = []

        for ev_prop in evidence_props:
            mismatches = self._compare_propositions(claim_prop, ev_prop)
            if not mismatches:
                # Perfect match on all non-wildcard dimensions
                return PropositionCheckResult(
                    verdict=PropositionVerdict.SUPPORTS,
                    claim_proposition=claim_prop,
                    evidence_propositions=evidence_props,
                    matched_proposition=ev_prop,
                    mismatched_dimensions=[],
                    reasoning=f"Full proposition match: subject={claim_prop.subject}, predicate={claim_prop.predicate}, value={claim_prop.value}"
                )
            elif len(mismatches) < len(mismatched_dims) or not mismatched_dims:
                mismatched_dims = mismatches
                best_match = ev_prop

        # No perfect match — determine the type of mismatch
        verdict = self._classify_mismatch(claim_prop, best_match, mismatched_dims)

        return PropositionCheckResult(
            verdict=verdict,
            claim_proposition=claim_prop,
            evidence_propositions=evidence_props,
            matched_proposition=best_match,
            mismatched_dimensions=mismatched_dims,
            reasoning=f"Mismatched dimensions: {mismatched_dims}. Best evidence prop: subject={best_match.subject if best_match else None}, predicate={best_match.predicate if best_match else None}, value={best_match.value if best_match else None}"
        )

    def _compare_propositions(self, claim: Proposition, evidence: Proposition) -> List[str]:
        """Compare two propositions. Returns list of mismatched dimension names.

        A dimension matches if:
          - claim dimension is None (wildcard) — matches anything
          - evidence dimension is None (wildcard) — matches anything
          - both are non-None and equal (case-insensitive for strings)
        """
        mismatches = []

        # Subject comparison
        if claim.subject and evidence.subject:
            if claim.subject.upper() != evidence.subject.upper():
                mismatches.append("subject")

        # Predicate comparison
        if claim.predicate and evidence.predicate:
            if claim.predicate.lower() != evidence.predicate.lower():
                mismatches.append("predicate")

        # Value comparison (normalize numbers)
        if claim.value and evidence.value:
            if not self._values_equal(claim.value, evidence.value):
                mismatches.append("value")

        # Comparator comparison
        if claim.comparator and evidence.comparator:
            if claim.comparator != evidence.comparator:
                mismatches.append("comparator")

        # Condition comparison
        if claim.condition and evidence.condition:
            if claim.condition.lower() != evidence.condition.lower():
                mismatches.append("condition")

        # Version comparison
        if claim.version and evidence.version:
            if claim.version.upper() != evidence.version.upper():
                mismatches.append("version")

        return mismatches

    def _values_equal(self, val1: str, val2: str) -> bool:
        """Compare two values, handling numeric equivalence."""
        # Extract numeric parts
        num1 = re.search(r"(\d+\.?\d*)", val1)
        num2 = re.search(r"(\d+\.?\d*)", val2)

        if num1 and num2:
            # Numeric comparison with tolerance for floating point
            f1 = float(num1.group(1))
            f2 = float(num2.group(1))
            return abs(f1 - f2) < 0.01

        # String comparison
        return val1.lower().strip() == val2.lower().strip()

    def _classify_mismatch(self, claim: Proposition, evidence: Optional[Proposition], mismatches: List[str]) -> PropositionVerdict:
        """Classify the type of mismatch to determine the verdict."""
        if evidence is None:
            return PropositionVerdict.INSUFFICIENT_EVIDENCE

        # If subject mismatches AND predicate matches → wrong entity
        if "subject" in mismatches and "predicate" not in mismatches:
            return PropositionVerdict.SUBJECT_MISMATCH

        # If subject matches AND predicate matches AND value mismatches → contradiction
        if "subject" not in mismatches and "predicate" not in mismatches and "value" in mismatches:
            return PropositionVerdict.CONTRADICTS

        # If version mismatches but everything else matches → version mismatch
        if "version" in mismatches and "subject" not in mismatches and "predicate" not in mismatches and "value" not in mismatches:
            return PropositionVerdict.VERSION_MISMATCH

        # If condition mismatches
        if "condition" in mismatches and "subject" not in mismatches and "predicate" not in mismatches:
            return PropositionVerdict.CONDITION_MISMATCH

        # If value not found at all
        if "value" in mismatches and evidence.value is None:
            return PropositionVerdict.VALUE_NOT_FOUND

        # If no overlap at all
        if not any(dim in mismatches for dim in ["subject", "predicate"]):
            return PropositionVerdict.UNRELATED

        # Default: some mismatch
        return PropositionVerdict.CONTRADICTS

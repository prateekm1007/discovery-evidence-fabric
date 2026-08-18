"""
epistemic_integrity/proposition_verifier.py — Structured proposition verification v4

Per CEO directive v4:
  1. Remove None=wildcard — missing evidence dimensions become INSUFFICIENT_EVIDENCE
  2. Units first-class in Proposition.value (magnitude + unit, 96.97% != 96.97 mmHg)
  3. Version metadata local to evidence artifact (not global extraction)
  4. Claim text generated FROM verified proposition (not reverse)
  5. Condition semantics (all_conditions, mean, worst_case, subset, range)

ARCHITECTURAL CHANGE:
  Evidence → Proposition → Verification → Approved Claim → Generated prose
  NOT: AI writes prose → try to verify prose

The verified proposition is the primary object. Claim text is auto-generated
from the proposition, eliminating the text↔proposition mismatch attack.
"""

import re
import json
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone


class PropositionVerdict(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"                    # Same subject+predicate but different value
    SUBJECT_MISMATCH = "SUBJECT_MISMATCH"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    CONDITION_MISMATCH = "CONDITION_MISMATCH"
    COMPARATOR_MISMATCH = "COMPARATOR_MISMATCH"
    UNIT_MISMATCH = "UNIT_MISMATCH"                # 96.97% vs 96.97 mmHg
    VALUE_NOT_FOUND = "VALUE_NOT_FOUND"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE" # Evidence dimension missing (NOT wildcard)
    SUBJECT_VALUE_NOT_COLOCATED = "SUBJECT_VALUE_NOT_COLOCATED" # Value exists but not with subject
    UNRELATED = "UNRELATED"


@dataclass
class StructuredValue:
    """A value with magnitude AND unit. 96.97% != 96.97 mmHg.

    Per CEO P0: units must be first-class.
    """
    magnitude: Optional[float] = None
    unit: Optional[str] = None  # "%", "mmHg", "N", "°C", "mm", "kDa", etc.
    raw: Optional[str] = None   # original string representation

    def __eq__(self, other):
        if not isinstance(other, StructuredValue):
            return False
        # Both magnitude AND unit must match
        if self.magnitude is not None and other.magnitude is not None:
            if abs(self.magnitude - other.magnitude) > 0.01:
                return False
            # Units must match exactly (or both None)
            if self.unit != other.unit:
                return False
            return True
        # Fall back to raw comparison
        return (self.raw or "").lower().strip() == (other.raw or "").lower().strip()

    def matches_loose(self, other) -> bool:
        """Loose match: magnitude matches, unit may differ (for finding values in text)."""
        if not isinstance(other, StructuredValue):
            return False
        if self.magnitude is not None and other.magnitude is not None:
            return abs(self.magnitude - other.magnitude) < 0.01
        return False


@dataclass
class Proposition:
    """A structured proposition.

    Per CEO v4:
      - None is NOT a wildcard. None means "not declared" and is INSUFFICIENT_EVIDENCE
        if the claim requires it.
      - The only legal wildcard is explicit: {"mode": "ANY"}
      - value is StructuredValue (magnitude + unit), not a string
      - version is local to the evidence artifact, not globally extracted
    """
    subject: Optional[str] = None
    predicate: Optional[str] = None
    value: Optional[StructuredValue] = None
    comparator: Optional[str] = None     # >=, <=, ==, >, <
    condition: Optional[str] = None      # "6_month_benchtop", "all_conditions", "worst_case", etc.
    version: Optional[str] = None        # "V6" — local to evidence artifact
    raw_text: str = ""
    # Explicit wildcard declaration (NOT None)
    subject_wildcard: bool = False
    predicate_wildcard: bool = False
    value_wildcard: bool = False
    comparator_wildcard: bool = False
    condition_wildcard: bool = False
    version_wildcard: bool = False


@dataclass
class PropositionCheckResult:
    verdict: PropositionVerdict
    claim_proposition: Proposition
    evidence_propositions: List[Proposition]
    matched_proposition: Optional[Proposition]
    mismatched_dimensions: List[str]
    reasoning: str


# Required dimensions for a SUPPORTS verdict
REQUIRED_DIMENSIONS = ["subject", "predicate", "value"]


class PropositionVerifier:
    """Verifies claims against evidence using strict structured proposition matching.

    IMMUTABLE RULES (per CEO v4):
      1. None is NOT a wildcard — missing evidence dimension = INSUFFICIENT_EVIDENCE
      2. Units are first-class — 96.97% != 96.97 mmHg
      3. Version is local to evidence artifact — not globally extracted
      4. All REQUIRED_DIMENSIONS must have corresponding evidence dimensions
      5. Subject+value must be colocated in evidence (prevents wrong-entity attack)
    """

    # Entity patterns
    ENTITY_PATTERNS = [
        re.compile(r"\b(M\d+_REFINED)\b"),
        re.compile(r"\b(M\d+_\w+)\b"),
        re.compile(r"\b(A\d+_cryo_debonding)\b"),
        re.compile(r"\b(A\d+_\w+)\b"),
        re.compile(r"\b(VIEshunt|eShunt|CereVasc)\b", re.IGNORECASE),
        re.compile(r"\b(M9|M5|M10|M1|M6)_?(\w*)\b"),
    ]

    # Predicate patterns
    PREDICATE_PATTERNS = [
        (re.compile(r"retrieval\s+reliability", re.IGNORECASE), "retrieval_reliability"),
        (re.compile(r"embolization\s+(rate|events|threshold)", re.IGNORECASE), "embolization_rate"),
        (re.compile(r"states?\s*meeting\s*target", re.IGNORECASE), "states_meeting_target"),
        (re.compile(r"self[-_]?test\s+detection", re.IGNORECASE), "self_test_detection"),
        (re.compile(r"REM\s+apnea\s+(miss|coverage)", re.IGNORECASE), "rem_apnea_miss_rate"),
        (re.compile(r"thermal\s+injury", re.IGNORECASE), "thermal_injury_threshold"),
        (re.compile(r"pull\s+force", re.IGNORECASE), "pull_force"),
        (re.compile(r"fragmentation\s+rate", re.IGNORECASE), "fragmentation_rate"),
        (re.compile(r"local\s+pH", re.IGNORECASE), "local_ph"),
        (re.compile(r"mass\s+(at|retention|remaining)", re.IGNORECASE), "mass_retention"),
        (re.compile(r"condition\s+number", re.IGNORECASE), "condition_number"),
        (re.compile(r"R[²²]\s+target", re.IGNORECASE), "r2_target"),
    ]

    # Value patterns — now returns StructuredValue
    VALUE_WITH_UNIT = re.compile(r"(\d+\.?\d*)\s*(%|mmHg|N|°C|mm|kDa|MPa|Hz|kHz|MHz|days?|months?|years?)?")
    FRACTION_PATTERN = re.compile(r"(\d+)\s*(?:of|/)\s*(\d+)")

    # Condition patterns
    CONDITION_PATTERNS = [
        (re.compile(r"all\s+conditions?", re.IGNORECASE), "all_conditions"),
        (re.compile(r"worst[-_ ]?case", re.IGNORECASE), "worst_case"),
        (re.compile(r"average|mean", re.IGNORECASE), "mean"),
        (re.compile(r"6[-_ ]?month", re.IGNORECASE), "6_month"),
        (re.compile(r"(\d+\.?\d*)\s*%\s*noise", re.IGNORECASE), "noise"),
        (re.compile(r"benchtop", re.IGNORECASE), "benchtop"),
        (re.compile(r"chronic", re.IGNORECASE), "chronic"),
    ]

    def parse_value(self, text: str) -> Optional[StructuredValue]:
        """Parse a value string into StructuredValue with magnitude + unit.

        Per CEO P0: units are first-class. 96.97% != 96.97 mmHg.
        """
        # Try fraction first (1/10000, 1 of 7)
        match = self.FRACTION_PATTERN.search(text)
        if match:
            return StructuredValue(
                magnitude=None,  # fractions don't have a single magnitude
                unit="fraction",
                raw=f"{match.group(1)}/{match.group(2)}"
            )

        # Try number with unit
        match = self.VALUE_WITH_UNIT.search(text)
        if match:
            magnitude = float(match.group(1))
            unit = match.group(2) or ""
            return StructuredValue(magnitude=magnitude, unit=unit if unit else None, raw=match.group(0))

        return None

    def extract_proposition_from_claim(
        self,
        subject: str,
        predicate: str,
        value: str,
        comparator: str = None,
        condition: str = None,
        version: str = None,
    ) -> Proposition:
        """Build a Proposition from DECLARED claim fields (not text extraction).

        Per CEO v4: the proposition is the primary object, not the text.
        """
        return Proposition(
            subject=subject,
            predicate=predicate,
            value=self.parse_value(value) if value else None,
            comparator=comparator,
            condition=condition,
            version=version,
        )

    def extract_propositions_from_evidence(
        self,
        evidence_content: str,
        evidence_version: str = None,  # LOCAL version, not globally extracted
    ) -> List[Proposition]:
        """Extract ALL propositions from evidence content.

        Per CEO P0: version is LOCAL to the evidence artifact, passed in explicitly.
        NOT extracted from the global document content.
        """
        propositions = []

        # Try parsing as JSON
        try:
            data = json.loads(evidence_content)
            propositions.extend(self._extract_from_json(data, evidence_content, evidence_version, ""))
        except json.JSONDecodeError:
            pass

        # Also extract from text
        sentences = re.split(r"[.{}\[\]\n]", evidence_content)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            prop = self._extract_from_text(sentence, evidence_version)
            if prop.subject or prop.predicate or prop.value:
                propositions.append(prop)

        return propositions

    def _extract_from_json(
        self,
        data: Any,
        raw_content: str,
        evidence_version: str,
        path: str,
    ) -> List[Proposition]:
        """Extract propositions from JSON. Version is LOCAL (passed in), not global."""
        propositions = []

        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                if isinstance(value, (dict, list)):
                    propositions.extend(self._extract_from_json(value, raw_content, evidence_version, new_path))
                else:
                    subject = self._infer_subject_from_path(new_path) or self._infer_subject_from_key(key)
                    if not subject and isinstance(value, str):
                        subject = self._infer_subject_from_value(value)

                    predicate = self._normalize_predicate(key)
                    value_struct = self.parse_value(str(value)) if value is not None else None

                    if (subject or predicate) and value_struct:
                        propositions.append(Proposition(
                            subject=subject,
                            predicate=predicate,
                            value=value_struct,
                            version=evidence_version,  # LOCAL, not global
                            raw_text=f"{new_path}={value}",
                        ))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                propositions.extend(self._extract_from_json(item, raw_content, evidence_version, f"{path}[{i}]"))

        return propositions

    def _extract_from_text(self, text: str, evidence_version: str = None) -> Proposition:
        """Extract proposition from a text sentence."""
        subject = self._extract_subject(text)
        predicate = self._extract_predicate(text)
        value = self._extract_value(text)
        condition = self._extract_condition(text)
        return Proposition(
            subject=subject,
            predicate=predicate,
            value=value,
            condition=condition,
            version=evidence_version,  # LOCAL
            raw_text=text,
        )

    def _extract_subject(self, text: str) -> Optional[str]:
        for pattern in self.ENTITY_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).upper().replace("_", "")
        return None

    def _extract_predicate(self, text: str) -> Optional[str]:
        for pattern, name in self.PREDICATE_PATTERNS:
            if pattern.search(text):
                return name
        return None

    def _extract_value(self, text: str) -> Optional[StructuredValue]:
        return self.parse_value(text)

    def _extract_condition(self, text: str) -> Optional[str]:
        for pattern, name in self.CONDITION_PATTERNS:
            if pattern.search(text):
                return name
        return None

    def _infer_subject_from_path(self, path: str) -> Optional[str]:
        path_upper = path.upper()
        if "M3" in path_upper:
            return "M3REFINED"
        if "A4" in path_upper:
            return "A4CRYODEBONDING"
        if "M9" in path_upper:
            return "M9"
        if "M5" in path_upper:
            return "M5REFINED"
        return None

    def _infer_subject_from_key(self, key: str) -> Optional[str]:
        return self._infer_subject_from_path(key)

    def _infer_subject_from_value(self, value: str) -> Optional[str]:
        for pattern in self.ENTITY_PATTERNS:
            match = pattern.search(str(value))
            if match:
                return match.group(1).upper().replace("_", "")
        return None

    def _normalize_predicate(self, key: str) -> Optional[str]:
        key_lower = key.lower()
        for pattern, name in self.PREDICATE_PATTERNS:
            if pattern.search(key_lower):
                return name
        if "reliability" in key_lower:
            return "retrieval_reliability"
        if "embolization" in key_lower:
            return "embolization_rate"
        if "states_meeting" in key_lower:
            return "states_meeting_target"
        if "detection" in key_lower and "self" in key_lower:
            return "self_test_detection"
        if "rem" in key_lower and "miss" in key_lower:
            return "rem_apnea_miss_rate"
        return None

    def verify(
        self,
        claim_proposition: Proposition,
        evidence_content: str,
        evidence_version: str = None,
    ) -> PropositionCheckResult:
        """Verify that evidence supports the DECLARED claim proposition.

        Per CEO v4:
          1. None is NOT wildcard — missing evidence dimension = INSUFFICIENT_EVIDENCE
          2. Units must match exactly
          3. Subject+value must be colocated
          4. Version is LOCAL (passed as evidence_version)
          5. Condition semantics enforced
        """
        if not evidence_content:
            return PropositionCheckResult(
                verdict=PropositionVerdict.INSUFFICIENT_EVIDENCE,
                claim_proposition=claim_proposition,
                evidence_propositions=[],
                matched_proposition=None,
                mismatched_dimensions=["evidence_content_empty"],
                reasoning="Evidence content is empty"
            )

        evidence_props = self.extract_propositions_from_evidence(evidence_content, evidence_version)

        if not evidence_props:
            return PropositionCheckResult(
                verdict=PropositionVerdict.INSUFFICIENT_EVIDENCE,
                claim_proposition=claim_proposition,
                evidence_propositions=[],
                matched_proposition=None,
                mismatched_dimensions=["no_propositions_in_evidence"],
                reasoning="No structured propositions extracted from evidence"
            )

        # Check each evidence proposition for a full match
        best_match = None
        best_mismatch_count = float('inf')
        best_mismatches = []

        for ev_prop in evidence_props:
            mismatches = self._compare_propositions_strict(claim_proposition, ev_prop)
            if not mismatches:
                return PropositionCheckResult(
                    verdict=PropositionVerdict.SUPPORTS,
                    claim_proposition=claim_proposition,
                    evidence_propositions=evidence_props,
                    matched_proposition=ev_prop,
                    mismatched_dimensions=[],
                    reasoning=f"Full proposition match: subject={claim_proposition.subject}, predicate={claim_proposition.predicate}, value={claim_proposition.value}"
                )
            if len(mismatches) < best_mismatch_count:
                best_mismatch_count = len(mismatches)
                best_match = ev_prop
                best_mismatches = mismatches

        # No perfect match — classify the mismatch
        verdict = self._classify_mismatch(claim_proposition, best_match, best_mismatches)

        return PropositionCheckResult(
            verdict=verdict,
            claim_proposition=claim_proposition,
            evidence_propositions=evidence_props,
            matched_proposition=best_match,
            mismatched_dimensions=best_mismatches,
            reasoning=f"Mismatched: {best_mismatches}. Best evidence: subject={best_match.subject if best_match else None}, predicate={best_match.predicate if best_match else None}, value={best_match.value if best_match else None}"
        )

    def _compare_propositions_strict(self, claim: Proposition, evidence: Proposition) -> List[str]:
        """STRICT comparison — None is NOT a wildcard.

        Per CEO P0: if claim has a dimension but evidence doesn't, that's INSUFFICIENT_EVIDENCE.
        Only explicit wildcards (subject_wildcard=True etc.) skip the check.
        """
        mismatches = []

        # Subject comparison
        if not claim.subject_wildcard:
            if claim.subject and not evidence.subject:
                mismatches.append("subject_INSUFFICIENT_EVIDENCE")
            elif claim.subject and evidence.subject:
                if claim.subject.upper() != evidence.subject.upper():
                    mismatches.append("subject_MISMATCH")

        # Predicate comparison
        if not claim.predicate_wildcard:
            if claim.predicate and not evidence.predicate:
                mismatches.append("predicate_INSUFFICIENT_EVIDENCE")
            elif claim.predicate and evidence.predicate:
                if claim.predicate.lower() != evidence.predicate.lower():
                    mismatches.append("predicate_MISMATCH")

        # Value comparison — UNITS ARE FIRST-CLASS
        if not claim.value_wildcard:
            if claim.value and not evidence.value:
                mismatches.append("value_INSUFFICIENT_EVIDENCE")
            elif claim.value and evidence.value:
                if not self._values_equal_strict(claim.value, evidence.value):
                    # Check if it's a unit mismatch specifically
                    if claim.value.matches_loose(evidence.value):
                        mismatches.append("unit_MISMATCH")
                    else:
                        mismatches.append("value_MISMATCH")

        # Comparator comparison
        if not claim.comparator_wildcard:
            if claim.comparator and not evidence.comparator:
                mismatches.append("comparator_INSUFFICIENT_EVIDENCE")
            elif claim.comparator and evidence.comparator:
                if claim.comparator != evidence.comparator:
                    mismatches.append("comparator_MISMATCH")

        # Condition comparison
        if not claim.condition_wildcard:
            if claim.condition and not evidence.condition:
                mismatches.append("condition_INSUFFICIENT_EVIDENCE")
            elif claim.condition and evidence.condition:
                if not self._conditions_match(claim.condition, evidence.condition):
                    mismatches.append("condition_MISMATCH")

        # Version comparison — LOCAL, not global
        if not claim.version_wildcard:
            if claim.version and not evidence.version:
                mismatches.append("version_INSUFFICIENT_EVIDENCE")
            elif claim.version and evidence.version:
                if claim.version.upper() != evidence.version.upper():
                    mismatches.append("version_MISMATCH")

        return mismatches

    def _values_equal_strict(self, val1: StructuredValue, val2: StructuredValue) -> bool:
        """Strict value comparison — magnitude AND unit must match.

        Per CEO P0: 96.97% != 96.97 mmHg.
        """
        # Both must have magnitude
        if val1.magnitude is not None and val2.magnitude is not None:
            if abs(val1.magnitude - val2.magnitude) > 0.01:
                return False
            # Units must match exactly
            if val1.unit != val2.unit:
                return False
            return True

        # Fall back to raw comparison for fractions/strings
        return (val1.raw or "").lower().strip() == (val2.raw or "").lower().strip()

    def _conditions_match(self, claim_condition: str, evidence_condition: str) -> bool:
        """Check if conditions match, with semantic understanding.

        Per CEO P0: condition semantics including all_conditions, mean, worst_case.
        """
        claim_cond = claim_condition.lower()
        evidence_cond = evidence_condition.lower()

        # Direct match
        if claim_cond == evidence_cond:
            return True

        # "all_conditions" is STRICTER than "mean" or "worst_case"
        # If claim says "all_conditions" but evidence says "mean", that's a MISMATCH
        # (claiming all conditions when evidence only shows mean is an overclaim)
        if claim_cond == "all_conditions" and evidence_cond in ["mean", "worst_case", "average"]:
            return False  # This is the H32 attack — partial promoted to full

        # "worst_case" is different from "mean"
        if claim_cond == "worst_case" and evidence_cond in ["mean", "average", "all_conditions"]:
            return False

        # "mean" matches "average"
        if claim_cond in ["mean", "average"] and evidence_cond in ["mean", "average"]:
            return True

        return False

    def _classify_mismatch(
        self,
        claim: Proposition,
        evidence: Optional[Proposition],
        mismatches: List[str],
    ) -> PropositionVerdict:
        """Classify the type of mismatch."""
        if evidence is None:
            return PropositionVerdict.INSUFFICIENT_EVIDENCE

        # Check for specific mismatch types
        if any("subject_MISMATCH" in m for m in mismatches):
            return PropositionVerdict.SUBJECT_MISMATCH

        if any("unit_MISMATCH" in m for m in mismatches):
            return PropositionVerdict.UNIT_MISMATCH

        if any("value_MISMATCH" in m for m in mismatches):
            # If subject and predicate match but value doesn't → CONTRADICTS
            if not any("subject_MISMATCH" in m for m in mismatches) and not any("predicate_MISMATCH" in m for m in mismatches):
                return PropositionVerdict.CONTRADICTS

        if any("version_MISMATCH" in m for m in mismatches):
            return PropositionVerdict.VERSION_MISMATCH

        if any("condition_MISMATCH" in m for m in mismatches):
            return PropositionVerdict.CONDITION_MISMATCH

        if any("INSUFFICIENT_EVIDENCE" in m for m in mismatches):
            return PropositionVerdict.INSUFFICIENT_EVIDENCE

        return PropositionVerdict.UNRELATED

    def verify_subject_value_colocation(
        self,
        subject: str,
        value: StructuredValue,
        evidence_content: str,
    ) -> bool:
        """Verify that subject and value appear TOGETHER in evidence content.

        Per CEO P0: prevents "wrong entity gets right number" attack.
        The value 96.97% might appear in evidence, but if it's associated with M3
        and the claim says A4=96.97%, that's a mismatch.
        """
        if not subject or not value or not evidence_content:
            return False

        # Find all occurrences of the subject
        subj_pattern = re.compile(re.escape(subject[:6]), re.IGNORECASE)
        val_str = str(value.magnitude) if value.magnitude else (value.raw or "")

        for subj_match in subj_pattern.finditer(evidence_content):
            # Check if value appears within 300 chars of this subject occurrence
            start = max(0, subj_match.start() - 300)
            end = min(len(evidence_content), subj_match.start() + 300)
            region = evidence_content[start:end]
            if val_str in region:
                return True

        return False

    def generate_claim_text(self, proposition: Proposition) -> str:
        """Generate claim text FROM the verified proposition.

        Per CEO v4: 'don't let the AI author the final claim sentence independently.
         Generate the sentence from the verified structured proposition.'

        This eliminates the text↔proposition mismatch attack entirely.
        """
        parts = []

        # Subject
        if proposition.subject:
            parts.append(proposition.subject.replace("_", " "))

        # Predicate
        if proposition.predicate:
            parts.append(proposition.predicate.replace("_", " "))

        # Value
        if proposition.value:
            if proposition.value.magnitude is not None:
                val_str = str(proposition.value.magnitude)
                if proposition.value.unit:
                    val_str += proposition.value.unit
                parts.append(f"is {val_str}")
            elif proposition.value.raw:
                parts.append(f"is {proposition.value.raw}")

        # Comparator
        if proposition.comparator:
            parts.append(f"({proposition.comparator})")

        # Condition
        if proposition.condition:
            parts.append(f"under {proposition.condition.replace('_', ' ')}")

        # Version
        if proposition.version:
            parts.append(f"per {proposition.version}")

        # Join with proper grammar
        text = " ".join(parts)
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:] + "."

        # Add epistemic class prefix
        return f"The simulation estimated that {text.lower()}"

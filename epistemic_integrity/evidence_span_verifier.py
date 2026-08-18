"""
epistemic_integrity/evidence_span_verifier.py — Exact pointer-based proof

Per CEO v12 P0-1:
  "Make JSON Pointer the actual final proof primitive. The verifier must
   resolve the exact pointer from the exact Git blob and compare that node
   against the proposition. The full document must never be searched for
   the final semantic proof."

Architecture:
  Git blob → exact JSON Pointer → exact node → exact value → proposition

  NOT: Git blob → search document → find matching number → infer relationship

This module resolves a JSON Pointer against an artifact and produces an
EvidenceSpan — the exact proof object that the firewall compares against
the claim proposition.
"""

import json
import hashlib
from dataclasses import dataclass, asdict
from typing import Optional, Any
from pathlib import Path


@dataclass
class EvidenceSpan:
    """The exact proof object. Contains ONLY the resolved value at the pointer.

    Per CEO: 'artifact hash → JSON pointer → exact node → exact value → proposition'
    """
    artifact_commit: str         # Full 40-char commit SHA
    blob_sha: str                # Full 40-char blob SHA
    content_hash: str            # SHA-256 of blob content
    json_pointer: str            # e.g., "/self_test_fallback_experiment/effective_m3_reliability_with_self_test"
    raw_value: Any               # The actual value at the pointer (int, float, str, etc.)
    decoded_value: str           # String representation of raw_value
    pointer_path_components: list  # The path components that led to this value
    # The key name at the pointer (last component) — used for subject/predicate inference
    key_name: str                # e.g., "effective_m3_reliability_with_self_test"

    def extract_subject(self) -> Optional[str]:
        """Infer subject from the key name. Only uses the LAST path component.

        Per CEO P0-1: no broad-document search. Only the key at the exact pointer.
        """
        key_lower = self.key_name.lower()
        if "m3" in key_lower:
            return "M3_REFINED"
        if "a4" in key_lower:
            return "A4_cryo_debonding"
        if "m9" in key_lower:
            return "M9_PLGA_sleeve"
        if "m5" in key_lower:
            return "M5_REFINED"
        return None

    def extract_predicate(self) -> Optional[str]:
        """Infer predicate from the key name. Only uses the LAST path component."""
        return self.key_name.lower().replace(" ", "_")

    def extract_condition(self) -> Optional[str]:
        """Infer condition from the key name."""
        key_lower = self.key_name.lower()
        if "average" in key_lower or "mean" in key_lower:
            return "mean"
        if "worst" in key_lower:
            return "worst_case"
        if "all" in key_lower and "condition" in key_lower:
            return "all_conditions"
        # Check parent path components for condition info
        for comp in self.pointer_path_components:
            comp_lower = comp.lower()
            if "average" in comp_lower or "mean" in comp_lower:
                return "mean"
            if "worst" in comp_lower:
                return "worst_case"
            if "6_month" in comp_lower or "six_month" in comp_lower:
                return "6_month_benchtop"
        return None


def resolve_json_pointer(json_content: str, pointer: str) -> Optional[EvidenceSpan]:
    """Resolve a JSON Pointer against JSON content and produce an EvidenceSpan.

    Per CEO P0-1: this is the SOLE proof primitive. The verifier does NOT
    search the document. It resolves the exact pointer and compares.

    Args:
        json_content: The JSON string (retrieved from git blob)
        pointer: JSON Pointer string (e.g., "/path/to/value")

    Returns:
        EvidenceSpan with the exact value at the pointer, or None if not found.
    """
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        return None

    # Parse JSON Pointer
    if not pointer.startswith("/"):
        return None

    components = pointer.split("/")[1:]  # Remove leading "/"
    current = data
    path_components = []

    for comp in components:
        path_components.append(comp)
        # Handle array indices
        if isinstance(current, list):
            try:
                idx = int(comp)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            except ValueError:
                return None
        elif isinstance(current, dict):
            # Unescape JSON Pointer (~1 → /, ~0 → ~)
            comp_unescaped = comp.replace("~1", "/").replace("~0", "~")
            if comp_unescaped in current:
                current = current[comp_unescaped]
            else:
                return None
        else:
            return None

    # current is now the exact value at the pointer
    raw_value = current
    decoded_value = str(raw_value)
    key_name = components[-1] if components else ""

    return EvidenceSpan(
        artifact_commit="",  # Set by caller
        blob_sha="",         # Set by caller
        content_hash="",     # Set by caller
        json_pointer=pointer,
        raw_value=raw_value,
        decoded_value=decoded_value,
        pointer_path_components=path_components,
        key_name=key_name,
    )


def verify_proposition_against_span(
    span: EvidenceSpan,
    claim_subject: str,
    claim_predicate: str,
    claim_value: str,
    claim_condition: str = None,
    claim_version: str = None,
    evidence_version: str = None,
) -> dict:
    """Verify a claim proposition against an EvidenceSpan.

    Per CEO P0-1: the verifier compares the DECLARED proposition against
    the EXACT value at the EXACT pointer. No document search.

    Returns dict with:
      - verdict: SUPPORTS / SUBJECT_MISMATCH / VALUE_MISMATCH / CONDITION_MISMATCH / VERSION_MISMATCH
      - reasoning: str
    """
    # 1. Value check: does the claim value match the span value?
    # Parse claim value to extract numeric component
    import re
    claim_num_match = re.search(r"(\d+\.?\d*)", claim_value)
    span_num = None
    if isinstance(span.raw_value, (int, float)):
        span_num = float(span.raw_value)
    elif claim_num_match:
        # Try to parse span value as number
        try:
            span_num = float(span.raw_value)
        except (ValueError, TypeError):
            pass

    if claim_num_match and span_num is not None:
        claim_num = float(claim_num_match.group(1))
        if abs(claim_num - span_num) > 0.01:
            return {
                "verdict": "VALUE_MISMATCH",
                "reasoning": f"Claim value {claim_num} != span value {span_num} at {span.json_pointer}",
            }
    elif claim_value.strip() != span.decoded_value.strip():
        # String comparison fallback
        if claim_value not in span.decoded_value and span.decoded_value not in claim_value:
            return {
                "verdict": "VALUE_MISMATCH",
                "reasoning": f"Claim value '{claim_value}' != span value '{span.decoded_value}'",
            }

    # 2. Subject check: does the key name contain the claim subject?
    span_subject = span.extract_subject()
    if span_subject and claim_subject:
        # Normalize for comparison
        claim_norm = claim_subject.upper().replace("_", "")
        span_norm = span_subject.upper().replace("_", "")
        if claim_norm != span_norm:
            return {
                "verdict": "SUBJECT_MISMATCH",
                "reasoning": f"Claim subject '{claim_subject}' != span subject '{span_subject}' (from key '{span.key_name}')",
            }

    # 3. Condition check
    if claim_condition:
        span_condition = span.extract_condition()
        if span_condition:
            # Directional: claim can be broader than evidence, but not narrower
            # "mean" evidence can support "mean" claim but not "all_conditions" claim
            if claim_condition.lower() == "all_conditions" and span_condition.lower() in ("mean", "average", "worst_case"):
                return {
                    "verdict": "CONDITION_MISMATCH",
                    "reasoning": f"Claim condition 'all_conditions' cannot be inferred from span condition '{span_condition}'",
                }
            if claim_condition.lower() == "worst_case" and span_condition.lower() in ("mean", "average"):
                return {
                    "verdict": "CONDITION_MISMATCH",
                    "reasoning": f"Claim condition 'worst_case' != span condition '{span_condition}'",
                }
            # Prefix match: "6_month_benchtop" matches "6_month"
            claim_cond = claim_condition.lower()
            span_cond = span_condition.lower()
            if claim_cond != span_cond and not (claim_cond.startswith(span_cond) or span_cond.startswith(claim_cond)):
                # Check if they're semantically equivalent (mean == average)
                if not (claim_cond in ("mean", "average") and span_cond in ("mean", "average")):
                    return {
                        "verdict": "CONDITION_MISMATCH",
                        "reasoning": f"Claim condition '{claim_condition}' != span condition '{span_condition}'",
                    }

    # 4. Version check
    if claim_version and evidence_version:
        if claim_version.upper() != evidence_version.upper():
            return {
                "verdict": "VERSION_MISMATCH",
                "reasoning": f"Claim version '{claim_version}' != evidence version '{evidence_version}'",
            }

    return {
        "verdict": "SUPPORTS",
        "reasoning": f"Exact pointer match: {span.json_pointer} = {span.raw_value}. Subject from key '{span.key_name}', value matches.",
    }

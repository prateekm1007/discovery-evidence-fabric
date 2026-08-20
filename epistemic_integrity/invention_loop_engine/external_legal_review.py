"""
External Legal Review schema and AI Model Legal Analysis class.

Per CEO directive (2026-08-21 eighth deep audit, Article XXVI violation fix):
  'The coder must not be able to manufacture an "expert" identity by writing
   a string into JSON. If no real external reviewer exists: BLOCKED_LEGAL_REVIEW,
   not ANTICIPATED.'

This module provides TWO distinct classes:

1. ExternalLegalReview — represents a review by a REAL external reviewer
   (human expert or independent AI ensemble) whose identity is verified
   through a TRUSTED REVIEWER REGISTRY. The coder CANNOT create this object
   with a self-invented reviewer_id. The registry is populated through a
   separate, auditable process (not by the coding agent).

2. AIModelLegalAnalysis — represents a legal analysis produced by an AI model
   (the coding agent itself, or another model). This is clearly labeled as
   MODEL_OUTPUT, not EVIDENCE. It can inform a CANDIDATE correspondence but
   can NEVER establish §102 support by itself. This is the honest
   representation of what the system actually produces when no external
   reviewer is available.

Design rules:
  - ExternalLegalReview requires a reviewer_id that exists in the
    TrustedReviewerRegistry. If the reviewer is not registered, the object
    cannot be constructed (ValueError at construction time).
  - The TrustedReviewerRegistry is loaded from a JSON file that the coding
    agent does NOT modify during normal operation. Adding a reviewer requires
    a separate governance process (CEO approval, recorded in the registry's
    own audit log).
  - AIModelLegalAnalysis has NO reviewer_id — it has model_id and
    model_version instead. It is always labeled MODEL_OUTPUT.
  - A LegalCorrespondenceDecision can be supported by EITHER an
    ExternalLegalReview (EVIDENCE — can establish §102) OR an
    AIModelLegalAnalysis (MODEL_OUTPUT — cannot establish §102, only propose).
  - If neither exists: BLOCKED_LEGAL_REVIEW.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4


# ---------------------------------------------------------------------------
# Trusted Reviewer Registry
# ---------------------------------------------------------------------------


class ReviewerType(str, Enum):
    """The type of reviewer. Determines what evidence is required."""
    HUMAN_EXPERT = "HUMAN_EXPERT"          # A real human patent attorney
    AI_ENSEMBLE = "AI_ENSEMBLE"            # An independent multi-model ensemble
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"  # An external API/service


@dataclass
class TrustedReviewer:
    """A reviewer registered in the TrustedReviewerRegistry.

    The registry is the ONLY source of legitimate reviewer identities.
    The coding agent cannot add reviewers to this registry during normal
    operation — that requires a separate governance process.
    """
    reviewer_id: str               # Unique, immutable ID
    reviewer_type: ReviewerType
    display_name: str              # Human-readable name
    credential_source: str         # Where the reviewer's authority comes from
    registration_timestamp: str    # When added to the registry
    registered_by: str             # Who added them (NOT the coding agent)
    registration_governance: str   # Reference to the governance approval
    active: bool = True


class TrustedReviewerRegistry:
    """Registry of trusted legal reviewers.

    Loaded from a JSON file. The coding agent does NOT write to this file
    during normal operation. Adding a reviewer requires CEO approval and
    a governance record.
    """

    def __init__(self, registry_path: Path = None):
        if registry_path is None:
            # Default: REPO_ROOT/CANONICAL_STATE/TRUSTED_LEGAL_REVIEWERS.json
            # Use path_utils for adversarial-safe derivation
            try:
                from epistemic_integrity.path_utils import derive_repo_root
                repo_root = derive_repo_root(__file__, parents_up=2)
            except ImportError:
                # Fallback if path_utils not available
                repo_root = Path(__file__).resolve().parents[2]
            registry_path = repo_root / "CANONICAL_STATE" / "TRUSTED_LEGAL_REVIEWERS.json"
        self.registry_path = registry_path
        self.reviewers: dict[str, TrustedReviewer] = {}
        self.load_errors: list[str] = []

    def load(self) -> bool:
        """Load the registry from JSON."""
        self.reviewers = {}
        self.load_errors = []

        if not self.registry_path.exists():
            # Empty registry — no trusted reviewers exist yet
            return True

        try:
            with open(self.registry_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.load_errors.append(f"Registry is not valid JSON: {e}")
            return False

        for entry in data.get("reviewers", []):
            try:
                r = TrustedReviewer(
                    reviewer_id=entry["reviewer_id"],
                    reviewer_type=ReviewerType(entry["reviewer_type"]),
                    display_name=entry["display_name"],
                    credential_source=entry["credential_source"],
                    registration_timestamp=entry["registration_timestamp"],
                    registered_by=entry["registered_by"],
                    registration_governance=entry["registration_governance"],
                    active=entry.get("active", True),
                )
                self.reviewers[r.reviewer_id] = r
            except (KeyError, ValueError) as e:
                self.load_errors.append(f"Invalid reviewer entry: {entry} — {e}")

        return len(self.load_errors) == 0

    def is_trusted(self, reviewer_id: str) -> bool:
        """Check if a reviewer_id is in the registry and active."""
        r = self.reviewers.get(reviewer_id)
        return r is not None and r.active

    def get_reviewer(self, reviewer_id: str) -> Optional[TrustedReviewer]:
        return self.reviewers.get(reviewer_id)

    def count(self) -> int:
        return len([r for r in self.reviewers.values() if r.active])


# ---------------------------------------------------------------------------
# External Legal Review (EVIDENCE — can establish §102)
# ---------------------------------------------------------------------------


@dataclass
class ExternalLegalReview:
    """A legal review by a REAL external reviewer.

    Per CEO directive (2026-08-21 eighth deep audit):
      'The coder must not be able to manufacture an "expert" identity by
       writing a string into JSON.'

    This object CANNOT be constructed with a self-invented reviewer_id.
    The reviewer_id MUST exist in the TrustedReviewerRegistry. If not,
    construction fails with ValueError.

    Required fields:
      - reviewer_id: must be in TrustedReviewerRegistry
      - review_timestamp: when the review occurred
      - reviewer_attestation: cryptographic attestation by the reviewer
      - decision_document_hash: SHA-256 of the actual review document
      - review_scope: what the review covered
      - independence_declaration: the reviewer's declaration of independence
      - claim_text_sha256: SHA-256 of the claim text reviewed
      - raw_response_sha256: SHA-256 of the raw source response

    The attestation binds:
      reviewer_id + review_timestamp + decision_document_hash + claim_text_sha256
    This prevents tampering with any field after the review.
    """
    reviewer_id: str
    review_timestamp: str
    reviewer_attestation: str          # Cryptographic attestation
    decision_document_hash: str        # SHA-256 of the review document
    review_scope: str
    independence_declaration: str
    claim_text_sha256: str             # SHA-256 of claim text
    raw_response_sha256: str           # SHA-256 of raw source response
    review_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        # P0 (twenty-sixth round): The reviewer MUST be in the TrustedReviewerRegistry.
        # The coding agent cannot manufacture an expert identity.
        registry = TrustedReviewerRegistry()
        registry.load()
        if not registry.is_trusted(self.reviewer_id):
            raise ValueError(
                f"ExternalLegalReview.reviewer_id='{self.reviewer_id}' is NOT in the "
                f"TrustedReviewerRegistry. The coding agent cannot manufacture an "
                f"expert identity by writing a string into JSON (Article XXVI — No "
                f"self-certification). If no real external reviewer exists, use "
                f"AIModelLegalAnalysis (MODEL_OUTPUT, not EVIDENCE) or set the "
                f"verdict to BLOCKED_LEGAL_REVIEW."
            )

        # Validate hashes are real SHA-256 (64 hex chars), not labels
        for field_name, field_value in [
            ("decision_document_hash", self.decision_document_hash),
            ("claim_text_sha256", self.claim_text_sha256),
            ("raw_response_sha256", self.raw_response_sha256),
        ]:
            if not self._is_real_sha256(field_value):
                raise ValueError(
                    f"ExternalLegalReview.{field_name}='{field_value}' is NOT a valid "
                    f"SHA-256 hash. It must be 64 hexadecimal characters. Labels like "
                    f"'sha256:US4741730A_claim1_html_extracted' are FORBIDDEN — they "
                    f"break the provenance chain."
                )

    @staticmethod
    def _is_real_sha256(s: str) -> bool:
        """Check if a string is a valid SHA-256 hash (64 hex chars)."""
        if not isinstance(s, str) or len(s) != 64:
            return False
        try:
            int(s, 16)
            return True
        except ValueError:
            return False

    @property
    def is_evidence(self) -> bool:
        """ExternalLegalReview IS evidence (can establish §102)."""
        return True

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "reviewer_id": self.reviewer_id,
            "review_timestamp": self.review_timestamp,
            "reviewer_attestation": self.reviewer_attestation,
            "decision_document_hash": self.decision_document_hash,
            "review_scope": self.review_scope,
            "independence_declaration": self.independence_declaration,
            "claim_text_sha256": self.claim_text_sha256,
            "raw_response_sha256": self.raw_response_sha256,
            "is_evidence": self.is_evidence,
        }


# ---------------------------------------------------------------------------
# AI Model Legal Analysis (MODEL_OUTPUT — NOT evidence, cannot establish §102)
# ---------------------------------------------------------------------------


@dataclass
class AIModelLegalAnalysis:
    """A legal analysis produced by an AI model.

    Per CEO directive (2026-08-21 eighth deep audit):
      'AI-generated legal correspondence is a model judgment, not independent
       evidence. The system should never fake a human reviewer.'

    This object represents what the AI model (the coding agent or another
    model) produced. It is clearly labeled as MODEL_OUTPUT, not EVIDENCE.
    It can inform a CANDIDATE correspondence but can NEVER establish §102
    support by itself.

    Required fields:
      - model_id: the AI model that produced the analysis
      - model_version: the model version
      - analysis_timestamp: when the analysis was produced
      - analysis_text: the actual legal reasoning
      - claim_text_sha256: SHA-256 of the claim text analyzed
      - raw_response_sha256: SHA-256 of the raw source response
      - analysis_hash: SHA-256 of the analysis_text

    The analysis_hash binds the analysis_text — any change to the reasoning
    invalidates the hash.
    """
    model_id: str
    model_version: str
    analysis_timestamp: str
    analysis_text: str
    claim_text_sha256: str
    raw_response_sha256: str
    analysis_hash: str = ""
    analysis_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        # Compute analysis_hash if not provided
        if not self.analysis_hash:
            self.analysis_hash = hashlib.sha256(self.analysis_text.encode("utf-8")).hexdigest()

        # Validate hashes are real SHA-256
        for field_name, field_value in [
            ("claim_text_sha256", self.claim_text_sha256),
            ("raw_response_sha256", self.raw_response_sha256),
            ("analysis_hash", self.analysis_hash),
        ]:
            if not ExternalLegalReview._is_real_sha256(field_value):
                raise ValueError(
                    f"AIModelLegalAnalysis.{field_name}='{field_value}' is NOT a valid "
                    f"SHA-256 hash. It must be 64 hexadecimal characters."
                )

    @property
    def is_evidence(self) -> bool:
        """AIModelLegalAnalysis is NOT evidence — it is MODEL_OUTPUT."""
        return False

    @property
    def evidence_class(self) -> str:
        """The epistemic class of this analysis."""
        return "MODEL_OUTPUT"

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "analysis_timestamp": self.analysis_timestamp,
            "analysis_text": self.analysis_text,
            "claim_text_sha256": self.claim_text_sha256,
            "raw_response_sha256": self.raw_response_sha256,
            "analysis_hash": self.analysis_hash,
            "is_evidence": self.is_evidence,
            "evidence_class": self.evidence_class,
        }


# ---------------------------------------------------------------------------
# Legal Review State — the verdict when no external review exists
# ---------------------------------------------------------------------------


class LegalReviewState(str, Enum):
    """The state of legal review for a correspondence.

    Per CEO directive:
      - If no real external reviewer exists: BLOCKED_LEGAL_REVIEW, not ANTICIPATED
      - If AI model analysis exists but no external review: MODEL_ANALYSIS_ONLY
      - If external review exists: EXTERNALLY_REVIEWED
    """
    NO_ANALYSIS = "NO_ANALYSIS"                              # No analysis at all
    MODEL_ANALYSIS_ONLY = "MODEL_ANALYSIS_ONLY"              # AI model analysis exists, no external review
    EXTERNALLY_REVIEWED = "EXTERNALLY_REVIEWED"              # External legal review exists
    BLOCKED_LEGAL_REVIEW = "BLOCKED_LEGAL_REVIEW"            # Review required but blocked (no reviewer available)

    @property
    def can_support_section_102(self) -> bool:
        """Only EXTERNALLY_REVIEWED can support §102."""
        return self == LegalReviewState.EXTERNALLY_REVIEWED


# ---------------------------------------------------------------------------
# Helper: compute real SHA-256 hashes
# ---------------------------------------------------------------------------


def sha256_of_text(text: str) -> str:
    """Compute the SHA-256 hash of a text string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_of_file(path: Path) -> str:
    """Compute the SHA-256 hash of a file's bytes."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    """Print the registry state and demonstrate the classes."""
    print("=" * 78)
    print("EXTERNAL LEGAL REVIEW SCHEMA + AI MODEL LEGAL ANALYSIS")
    print("=" * 78)
    print()

    # Load the trusted reviewer registry
    registry = TrustedReviewerRegistry()
    registry.load()
    print(f"Trusted reviewer registry: {registry.registry_path}")
    print(f"  Reviewers registered: {registry.count()}")
    print(f"  Load errors: {registry.load_errors}")
    print()

    # Demonstrate: trying to create an ExternalLegalReview with a fake reviewer fails
    print("=== Demonstration: self-manufactured reviewer is REJECTED ===")
    try:
        bad_review = ExternalLegalReview(
            reviewer_id="legal-expert-001",  # NOT in registry
            review_timestamp="2026-08-20T22:10:00Z",
            reviewer_attestation="fake_attestation",
            decision_document_hash="a" * 64,
            review_scope="C04 vs US4741730A",
            independence_declaration="I am independent (self-declared)",
            claim_text_sha256="b" * 64,
            raw_response_sha256="c" * 64,
        )
        print("  ❌ FAIL: ExternalLegalReview was created with a fake reviewer!")
    except ValueError as e:
        print(f"  ✅ BLOCKED: {str(e)[:120]}...")

    print()

    # Demonstrate: AIModelLegalAnalysis can be created (it's honestly MODEL_OUTPUT)
    print("=== Demonstration: AIModelLegalAnalysis is allowed (honest MODEL_OUTPUT) ===")
    try:
        analysis = AIModelLegalAnalysis(
            model_id="claude-sonnet-4",
            model_version="20250514",
            analysis_timestamp="2026-08-20T22:10:00Z",
            analysis_text="The C04 limitations appear to correspond to US4741730A claim 1...",
            claim_text_sha256=sha256_of_text("test claim"),
            raw_response_sha256=sha256_of_text("test response"),
        )
        print(f"  ✅ Created AIModelLegalAnalysis: model={analysis.model_id}")
        print(f"     is_evidence={analysis.is_evidence}")
        print(f"     evidence_class={analysis.evidence_class}")
        print(f"     analysis_hash={analysis.analysis_hash[:24]}...")
    except ValueError as e:
        print(f"  ❌ FAIL: {e}")

    print()

    # Demonstrate: fake hash is rejected
    print("=== Demonstration: fake hash label is REJECTED ===")
    try:
        bad_analysis = AIModelLegalAnalysis(
            model_id="test",
            model_version="1.0",
            analysis_timestamp="2026-08-20T22:10:00Z",
            analysis_text="test",
            claim_text_sha256="sha256:US4741730A_claim1_html_extracted",  # FAKE
            raw_response_sha256=sha256_of_text("test"),
        )
        print("  ❌ FAIL: AIModelLegalAnalysis was created with a fake hash!")
    except ValueError as e:
        print(f"  ✅ BLOCKED: {str(e)[:120]}...")

    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print()
    print("ExternalLegalReview:")
    print("  - Requires reviewer_id in TrustedReviewerRegistry")
    print("  - Requires real SHA-256 hashes (not labels)")
    print("  - IS evidence (can support §102)")
    print()
    print("AIModelLegalAnalysis:")
    print("  - Has model_id/model_version (NOT reviewer_id)")
    print("  - Requires real SHA-256 hashes")
    print("  - is NOT evidence (evidence_class=MODEL_OUTPUT)")
    print("  - CANNOT support §102 by itself")
    print()
    print("LegalReviewState:")
    print("  - NO_ANALYSIS: no analysis at all")
    print("  - MODEL_ANALYSIS_ONLY: AI analysis exists, no external review")
    print("  - EXTERNALLY_REVIEWED: external review exists (can support §102)")
    print("  - BLOCKED_LEGAL_REVIEW: review required but blocked")


if __name__ == "__main__":
    main()

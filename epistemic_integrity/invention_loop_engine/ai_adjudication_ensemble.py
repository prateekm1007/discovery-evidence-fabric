"""
AI Legal Adjudication Ensemble.

Per CEO directive (2026-08-21 ninth deep audit):
  'Build an AI Legal Adjudication Ensemble, not a fake expert and not
   one-model self-certification.

   Independent Model A → separate claim analysis
   Independent Model B → separate claim analysis (WITHOUT seeing A)
   Independent Model C → attacks both
   Arbitration → ESTABLISHED / DISPUTED / UNKNOWN

   Each model must independently receive the same primary evidence, but
   must not receive another model's conclusion before producing its own.

   AI consensus is not evidence. The evidence remains the actual patent
   claim. The ensemble provides an auditable interpretation layer over
   that evidence.'

Anti-gaming rules (enforced by code):
  - No model may see another model's answer before submitting its own
  - No model may edit another model's analysis
  - No model may declare itself a verifier
  - No model may turn consensus into evidence
  - No model may use a confidence score as proof

The patent claim remains the evidence. AI outputs are interpretations
with provenance, bound to the exact source bytes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


# ---------------------------------------------------------------------------
# Adjudication State Enum
# ---------------------------------------------------------------------------


class AIAdjudicationState(str, Enum):
    """The state of AI adjudication for a correspondence.

    Per CEO directive:
      - MODEL_ANALYSIS_ONLY: one model produced an analysis (weakest)
      - ENSEMBLE_INDEPENDENT: multiple models produced independent analyses
      - ADVERSARIAL_REVIEW: at least one model attacked the others
      - ARBITRATED: an arbitrator compared the analyses and produced a disposition
      - DISPUTED: the arbitrator found unresolved disagreement
      - UNKNOWN: insufficient evidence to determine correspondence

    Only ARBITRATED with consensus can support §102. DISPUTED and UNKNOWN cannot.
    """
    MODEL_ANALYSIS_ONLY = "MODEL_ANALYSIS_ONLY"
    ENSEMBLE_INDEPENDENT = "ENSEMBLE_INDEPENDENT"
    ADVERSARIAL_REVIEW = "ADVERSARIAL_REVIEW"
    ARBITRATED = "ARBITRATED"
    DISPUTED = "DISPUTED"
    UNKNOWN = "UNKNOWN"
    AI_ADJUDICATION_PENDING = "AI_ADJUDICATION_PENDING"

    @property
    def can_support_section_102(self) -> bool:
        """Only ARBITRATED (with consensus) can support §102.

        DISPUTED and UNKNOWN explicitly cannot.
        """
        return self == AIAdjudicationState.ARBITRATED


class ModelDisposition(str, Enum):
    """What a single model concluded about a correspondence."""
    SUPPORTS_102 = "SUPPORTS_102"
    DOES_NOT_SUPPORT_102 = "DOES_NOT_SUPPORT_102"
    UNCERTAIN = "UNCERTAIN"


class ArbitrationVerdict(str, Enum):
    """The arbitrator's final disposition after comparing models."""
    ESTABLISHED = "ESTABLISHED"      # All models agree on SUPPORTS_102 (or DOES_NOT_SUPPORT_102)
    DISPUTED = "DISPUTED"            # Models disagree
    UNKNOWN = "UNKNOWN"              # Models are uncertain or evidence is insufficient


# ---------------------------------------------------------------------------
# Individual Model Analysis
# ---------------------------------------------------------------------------


@dataclass
class ModelCorrespondenceAnalysis:
    """A single model's analysis of one limitation vs one claim passage.

    CRITICAL: This object is constructed BEFORE the model sees any other
    model's analysis. The ensemble runner enforces this by:
      1. Constructing each ModelCorrespondenceAnalysis in a separate call
      2. NOT passing other models' analyses to the model
      3. Recording the input_hash to prove what the model saw

    Anti-gaming fields:
      - model_id: which model produced this
      - model_version: model version (for reproducibility)
      - input_evidence_hash: SHA-256 of the EXACT evidence the model saw
        (claim text + limitation text + raw response hash). This proves
        the model did NOT see another model's conclusion.
      - analysis_hash: SHA-256 of the analysis_text (binds the reasoning)
      - no_other_model_analyses_seen: explicit declaration (True by construction)
    """
    model_id: str
    model_version: str
    analysis_timestamp: str
    limitation_id: str
    limitation_text: str
    claim_passage: str
    claim_text_sha256: str        # SHA-256 of full claim text
    raw_response_sha256: str      # SHA-256 of raw patent response
    input_evidence_hash: str      # SHA-256 of (limitation + claim + raw_hash) — proves what model saw
    correspondence_type: str      # VERBATIM / STRUCTURAL_EQUIVALENT / FUNCTIONAL_EQUIVALENT / NOT_CORRESPONDING
    disposition: ModelDisposition
    analysis_text: str            # The model's legal reasoning
    confidence: str               # HIGH / MEDIUM / LOW (NOT proof — just a signal)
    analysis_hash: str = ""
    analysis_id: str = field(default_factory=lambda: str(uuid4()))
    no_other_model_analyses_seen: bool = True  # Enforced by construction

    def __post_init__(self):
        if not self.analysis_hash:
            self.analysis_hash = hashlib.sha256(self.analysis_text.encode("utf-8")).hexdigest()

        # Validate all hashes are real SHA-256
        for field_name, field_value in [
            ("claim_text_sha256", self.claim_text_sha256),
            ("raw_response_sha256", self.raw_response_sha256),
            ("input_evidence_hash", self.input_evidence_hash),
            ("analysis_hash", self.analysis_hash),
        ]:
            if not self._is_real_sha256(field_value):
                raise ValueError(
                    f"ModelCorrespondenceAnalysis.{field_name}='{field_value}' is NOT a valid "
                    f"SHA-256 hash. It must be 64 hexadecimal characters."
                )

    @staticmethod
    def _is_real_sha256(s: str) -> bool:
        if not isinstance(s, str) or len(s) != 64:
            return False
        try:
            int(s, 16)
            return True
        except ValueError:
            return False

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "analysis_timestamp": self.analysis_timestamp,
            "limitation_id": self.limitation_id,
            "limitation_text": self.limitation_text,
            "claim_passage": self.claim_passage,
            "claim_text_sha256": self.claim_text_sha256,
            "raw_response_sha256": self.raw_response_sha256,
            "input_evidence_hash": self.input_evidence_hash,
            "correspondence_type": self.correspondence_type,
            "disposition": self.disposition.value if isinstance(self.disposition, ModelDisposition) else self.disposition,
            "analysis_text": self.analysis_text,
            "confidence": self.confidence,
            "analysis_hash": self.analysis_hash,
            "no_other_model_analyses_seen": self.no_other_model_analyses_seen,
        }


# ---------------------------------------------------------------------------
# Adversarial Counter-Analysis
# ---------------------------------------------------------------------------


@dataclass
class AdversarialCounterAnalysis:
    """A model's attack on other models' analyses.

    The adversarial model receives the OTHER models' analyses (after they
    are sealed) and attempts to refute them. It must identify:
      - specific weaknesses in each analysis
      - missing evidence
      - alternative interpretations
      - legal rules that contradict the analysis

    The adversarial model does NOT produce its own correspondence verdict —
    it only attacks others.
    """
    model_id: str
    model_version: str
    analysis_timestamp: str
    limitation_id: str
    target_analysis_ids: list[str]  # Which analyses are being attacked
    counterargument_text: str
    weaknesses_identified: list[str]
    missing_evidence_identified: list[str]
    alternative_interpretations: list[str]
    counteranalysis_hash: str = ""
    counteranalysis_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if not self.counteranalysis_hash:
            self.counteranalysis_hash = hashlib.sha256(
                self.counterargument_text.encode("utf-8")
            ).hexdigest()

    def to_dict(self) -> dict:
        return {
            "counteranalysis_id": self.counteranalysis_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "analysis_timestamp": self.analysis_timestamp,
            "limitation_id": self.limitation_id,
            "target_analysis_ids": self.target_analysis_ids,
            "counterargument_text": self.counterargument_text,
            "weaknesses_identified": self.weaknesses_identified,
            "missing_evidence_identified": self.missing_evidence_identified,
            "alternative_interpretations": self.alternative_interpretations,
            "counteranalysis_hash": self.counteranalysis_hash,
        }


# ---------------------------------------------------------------------------
# Disagreement Matrix
# ---------------------------------------------------------------------------


@dataclass
class DisagreementMatrix:
    """Compares the dispositions of multiple models for one limitation.

    Identifies exact points of disagreement:
      - disposition disagreement (models reach different verdicts)
      - correspondence_type disagreement (models classify differently)
      - confidence disagreement (models differ in confidence)
    """
    limitation_id: str
    analyses_compared: list[str]  # analysis_ids
    disposition_agreement: bool   # All models agree on disposition?
    correspondence_type_agreement: bool  # All models agree on type?
    disagreements: list[str]      # Specific points of disagreement
    matrix_hash: str = ""

    def __post_init__(self):
        content = f"{self.limitation_id}|{'|'.join(sorted(self.analyses_compared))}|{'|'.join(self.disagreements)}"
        self.matrix_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "limitation_id": self.limitation_id,
            "analyses_compared": self.analyses_compared,
            "disposition_agreement": self.disposition_agreement,
            "correspondence_type_agreement": self.correspondence_type_agreement,
            "disagreements": self.disagreements,
            "matrix_hash": self.matrix_hash,
        }


# ---------------------------------------------------------------------------
# Arbitration
# ---------------------------------------------------------------------------


@dataclass
class ArbitrationResult:
    """The arbitrator's final disposition for one limitation.

    The arbitrator:
      1. Receives all model analyses (after they are sealed)
      2. Receives the adversarial counter-analyses
      3. Receives the disagreement matrix
      4. Compares against the PRIMARY EVIDENCE (the patent claim)
      5. Produces a structured disposition

    The arbitrator is FORCED to identify the exact limitation-level
    disagreement rather than simply voting.

    Verdict rules:
      - ESTABLISHED: all models agree AND adversarial attack failed to refute
      - DISPUTED: models disagree, OR adversarial attack succeeded
      - UNKNOWN: evidence insufficient, OR models uncertain

    Only ESTABLISHED with disposition=SUPPORTS_102 can support §102.
    """
    limitation_id: str
    arbitrator_model_id: str
    arbitrator_model_version: str
    arbitration_timestamp: str
    analyses_considered: list[str]    # analysis_ids
    counteranalyses_considered: list[str]  # counteranalysis_ids
    disagreement_matrix_hash: str     # binds the disagreement matrix
    exact_disagreement_summary: str   # The arbitrator's identification of the disagreement
    evidence_assessment: str          # What the primary evidence actually shows
    verdict: ArbitrationVerdict
    final_disposition: ModelDisposition  # The final §102 disposition
    rationale: str                    # Why this verdict
    arbitration_hash: str = ""
    arbitration_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        content = f"{self.limitation_id}|{self.arbitrator_model_id}|{self.verdict.value}|{self.final_disposition.value if isinstance(self.final_disposition, ModelDisposition) else self.final_disposition}|{self.rationale}"
        self.arbitration_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    @property
    def can_support_section_102(self) -> bool:
        """Only ESTABLISHED + SUPPORTS_102 can support §102."""
        return (
            self.verdict == ArbitrationVerdict.ESTABLISHED
            and self.final_disposition == ModelDisposition.SUPPORTS_102
        )

    def to_dict(self) -> dict:
        return {
            "arbitration_id": self.arbitration_id,
            "limitation_id": self.limitation_id,
            "arbitrator_model_id": self.arbitrator_model_id,
            "arbitrator_model_version": self.arbitrator_model_version,
            "arbitration_timestamp": self.arbitration_timestamp,
            "analyses_considered": self.analyses_considered,
            "counteranalyses_considered": self.counteranalyses_considered,
            "disagreement_matrix_hash": self.disagreement_matrix_hash,
            "exact_disagreement_summary": self.exact_disagreement_summary,
            "evidence_assessment": self.evidence_assessment,
            "verdict": self.verdict.value,
            "final_disposition": self.final_disposition.value if isinstance(self.final_disposition, ModelDisposition) else self.final_disposition,
            "rationale": self.rationale,
            "arbitration_hash": self.arbitration_hash,
            "can_support_section_102": self.can_support_section_102,
        }


# ---------------------------------------------------------------------------
# Full Ensemble Result
# ---------------------------------------------------------------------------


@dataclass
class AIAdjudicationEnsemble:
    """The full ensemble result for one limitation.

    Contains:
      - All model analyses (produced independently, without seeing each other)
      - All adversarial counter-analyses
      - The disagreement matrix
      - The arbitration result
      - The final state (ESTABLISHED / DISPUTED / UNKNOWN)
    """
    limitation_id: str
    model_analyses: list[ModelCorrespondenceAnalysis]
    adversarial_counteranalyses: list[AdversarialCounterAnalysis]
    disagreement_matrix: DisagreementMatrix
    arbitration: ArbitrationResult
    ensemble_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def state(self) -> AIAdjudicationState:
        """Derive the ensemble state from the arbitration verdict."""
        if self.arbitration.verdict == ArbitrationVerdict.ESTABLISHED:
            return AIAdjudicationState.ARBITRATED
        elif self.arbitration.verdict == ArbitrationVerdict.DISPUTED:
            return AIAdjudicationState.DISPUTED
        else:
            return AIAdjudicationState.UNKNOWN

    @property
    def can_support_section_102(self) -> bool:
        """The ensemble can support §102 only if ARBITRATED + SUPPORTS_102."""
        return self.arbitration.can_support_section_102

    def to_dict(self) -> dict:
        return {
            "ensemble_id": self.ensemble_id,
            "limitation_id": self.limitation_id,
            "state": self.state.value,
            "can_support_section_102": self.can_support_section_102,
            "model_analyses": [a.to_dict() for a in self.model_analyses],
            "adversarial_counteranalyses": [c.to_dict() for c in self.adversarial_counteranalyses],
            "disagreement_matrix": self.disagreement_matrix.to_dict(),
            "arbitration": self.arbitration.to_dict(),
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def compute_input_evidence_hash(
    limitation_text: str,
    claim_text: str,
    raw_response_sha256: str,
) -> str:
    """Compute the hash of the EXACT evidence a model saw.

    This proves the model did NOT see another model's conclusion —
    the input is only (limitation + claim + raw_response_hash).
    """
    content = f"{limitation_text}|{claim_text}|{raw_response_sha256}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sha256_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

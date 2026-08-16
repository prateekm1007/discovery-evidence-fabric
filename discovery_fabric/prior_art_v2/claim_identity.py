"""
CLAIM IDENTITY VALIDATION
===========================

Per CEO directive V3.3 Section 2-3:
  Before ANY claim enters the pipeline, validate:
    - case patent number
    - retrieved patent number
    - title
    - assignee
    - priority date
    - claim text

States:
  IDENTITY_CONFIRMED   — all fields match
  IDENTITY_MISMATCH    — material discrepancy detected
  IDENTITY_UNRESOLVED  — cannot determine (fingerprint similarity borderline)

If IDENTITY_MISMATCH: STOP CASE. Status=EVIDENCE_CORRUPTED.
Do NOT run 102/103/commercial/rescue.

claim_subject_fingerprint:
  Built from: title + abstract + claim terminology + device class + technical mechanism
  Compared to case metadata. If similarity is materially inconsistent:
  CLAIM_IDENTITY_UNRESOLVED.
"""
from __future__ import annotations
import re, hashlib, json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ----------------------- STATES -----------------------
IDENTITY_CONFIRMED = "IDENTITY_CONFIRMED"
IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"

EVIDENCE_CORRUPTED = "EVIDENCE_CORRUPTED"


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class ClaimSubjectFingerprint:
    """Fingerprint built from claim subject matter.

    Per CEO Section 3: title + abstract + claim terminology + device class + technical mechanism.
    Used to detect cross-patent contamination.
    """
    title_terms: List[str] = field(default_factory=list)
    abstract_terms: List[str] = field(default_factory=list)
    claim_terminology: List[str] = field(default_factory=list)
    device_class: str = ""
    technical_mechanism: str = ""
    fingerprint_hash: str = ""

    def build(self, title: str, abstract: str, claims: List[str],
              device_class: str = "", technical_mechanism: str = ""):
        """Build fingerprint from patent content."""
        self.title_terms = self._extract_terms(title, max_terms=15)
        self.abstract_terms = self._extract_terms(abstract, max_terms=20)
        # Claim terminology — extract technical terms from claims
        claims_text = " ".join(claims[:3]) if claims else ""
        self.claim_terminology = self._extract_terms(claims_text, max_terms=25)
        self.device_class = device_class.lower().strip()
        self.technical_mechanism = technical_mechanism.lower().strip()

        # Build hash
        fp_content = json.dumps({
            "title_terms": sorted(self.title_terms),
            "abstract_terms": sorted(self.abstract_terms),
            "claim_terminology": sorted(self.claim_terminology),
            "device_class": self.device_class,
            "technical_mechanism": self.technical_mechanism,
        }, sort_keys=True)
        self.fingerprint_hash = _sha256(fp_content)
        return self

    def _extract_terms(self, text: str, max_terms: int = 20) -> List[str]:
        """Extract significant terms from text (stop words removed)."""
        if not text:
            return []
        # Remove HTML, normalize
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.lower()
        # Extract word tokens (length >= 4, alphabetic)
        tokens = re.findall(r'\b[a-z]{4,}\b', text)
        # Remove stop words
        stop_words = {
            "the", "and", "for", "with", "from", "that", "this", "which", "where",
            "there", "what", "when", "how", "all", "any", "are", "was", "were", "been",
            "have", "has", "had", "did", "does", "done", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "said", "such", "than",
            "then", "them", "they", "their", "these", "those", "thus", "upon", "using",
            "used", "uses", "use", "into", "onto", "over", "under", "between", "through",
            "during", "after", "before", "above", "below", "along", "around", "behind",
            "beyond", "inside", "outside", "near", "far", "about", "above", "across",
            "against", "among", "around", "at", "by", "down", "in", "of", "on", "or",
            "to", "up", "with", "within", "without", "comprising", "comprises",
            "consisting", "consists", "including", "includes", "having", "has",
            "wherein", "thereof", "thereto", "herein", "hereby", "hereof", "hereto",
            "according", "claim", "claims", "method", "process", "apparatus", "device",
            "system", "means", "step", "steps", "first", "second", "third", "fourth",
            "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "one", "two",
            "three", "four", "five", "six", "seven", "eight", "nine", "ten", "each",
            "both", "either", "neither", "other", "another", "same", "different",
            "new", "old", "prior", "subsequent", "previous", "next", "last", "final",
            "initial", "intermediate", "subsequent", "following", "preceding",
        }
        significant = [t for t in tokens if t not in stop_words]
        # Dedupe while preserving order
        seen = set()
        unique = []
        for t in significant:
            if t not in seen:
                seen.add(t)
                unique.append(t)
            if len(unique) >= max_terms:
                break
        return unique

    def similarity_to(self, other: "ClaimSubjectFingerprint") -> float:
        """Compute similarity (0.0 to 1.0) between two fingerprints.

        Uses Jaccard similarity over term sets, weighted by category.
        """
        if not self.fingerprint_hash or not other.fingerprint_hash:
            return 0.0

        # Jaccard similarity for each category
        def jaccard(a: List[str], b: List[str]) -> float:
            if not a and not b:
                return 1.0
            if not a or not b:
                return 0.0
            sa, sb = set(a), set(b)
            intersection = sa & sb
            union = sa | sb
            return len(intersection) / len(union) if union else 0.0

        title_sim = jaccard(self.title_terms, other.title_terms)
        abstract_sim = jaccard(self.abstract_terms, other.abstract_terms)
        claim_sim = jaccard(self.claim_terminology, other.claim_terminology)

        # Device class and mechanism — exact match
        dc_sim = 1.0 if (self.device_class and self.device_class == other.device_class) else 0.0
        tm_sim = 1.0 if (self.technical_mechanism and self.technical_mechanism == other.technical_mechanism) else 0.0

        # Weighted average (claims carry most weight)
        weights = {
            "title": 0.20,
            "abstract": 0.20,
            "claims": 0.40,
            "device_class": 0.10,
            "mechanism": 0.10,
        }
        similarity = (
            weights["title"] * title_sim +
            weights["abstract"] * abstract_sim +
            weights["claims"] * claim_sim +
            weights["device_class"] * dc_sim +
            weights["mechanism"] * tm_sim
        )
        return similarity


@dataclass
class IdentityValidationResult:
    """Result of claim identity validation."""
    state: str = IDENTITY_UNRESOLVED
    case_patent_number: str = ""
    retrieved_patent_number: str = ""
    case_title: str = ""
    retrieved_title: str = ""
    case_device_class: str = ""
    retrieved_assignee: str = ""
    case_fingerprint: Optional[ClaimSubjectFingerprint] = None
    retrieved_fingerprint: Optional[ClaimSubjectFingerprint] = None
    similarity_score: float = 0.0
    mismatch_reasons: List[str] = field(default_factory=list)
    validated_at_utc: str = ""


# ----------------------- VALIDATION -----------------------
def validate_claim_identity(
    case: Dict[str, Any],
    retrieved_patent_number: str,
    retrieved_title: str,
    retrieved_claims: List[str],
    retrieved_assignee: str = "",
    retrieved_priority_date: str = "",
    similarity_threshold: float = 0.20,
    mismatch_threshold: float = 0.10,
) -> IdentityValidationResult:
    """Validate that retrieved claims match the case's expected patent.

    Per CEO V3.3 Section 2:
      - case patent number vs retrieved patent number
      - title vs case title
      - claim text subject matter vs case device class

    Returns IDENTITY_CONFIRMED / IDENTITY_MISMATCH / IDENTITY_UNRESOLVED.
    """
    result = IdentityValidationResult(
        case_patent_number=case.get("patent_number", ""),
        retrieved_patent_number=retrieved_patent_number,
        case_title=case.get("title", ""),
        retrieved_title=retrieved_title,
        case_device_class=case.get("device_class", ""),
        retrieved_assignee=retrieved_assignee,
        validated_at_utc=_now_utc(),
    )

    # Build fingerprints
    case_fp = ClaimSubjectFingerprint().build(
        title=case.get("title", ""),
        abstract=case.get("examiner_reasoning", ""),  # use as proxy for abstract
        claims=[],  # case doesn't have claims yet — use title + examiner reasoning
        device_class=case.get("device_class", ""),
        technical_mechanism=case.get("device_class", ""),
    )
    retrieved_fp = ClaimSubjectFingerprint().build(
        title=retrieved_title,
        abstract="",  # may not have abstract
        claims=retrieved_claims,
        device_class=case.get("device_class", ""),  # expected device class
        technical_mechanism=case.get("device_class", ""),
    )
    result.case_fingerprint = case_fp
    result.retrieved_fingerprint = retrieved_fp
    result.similarity_score = case_fp.similarity_to(retrieved_fp)

    # Check 1: Patent number match (with normalization)
    case_pn = _normalize_patent_number(case.get("patent_number", ""))
    retrieved_pn = _normalize_patent_number(retrieved_patent_number)
    if case_pn and retrieved_pn and not _same_patent_number(case_pn, retrieved_pn):
        result.mismatch_reasons.append(
            f"Patent number mismatch: case={case_pn} vs retrieved={retrieved_pn}"
        )

    # Check 2: Title similarity (if both present)
    if result.case_title and retrieved_title:
        title_sim = _text_similarity(result.case_title, retrieved_title)
        if title_sim < mismatch_threshold:
            result.mismatch_reasons.append(
                f"Title mismatch: similarity={title_sim:.2f} "
                f"case='{result.case_title[:60]}' vs retrieved='{retrieved_title[:60]}'"
            )

    # Check 3: Fingerprint similarity (cross-patent contamination check)
    if result.similarity_score < mismatch_threshold:
        result.mismatch_reasons.append(
            f"Subject fingerprint mismatch: similarity={result.similarity_score:.2f} "
            f"(threshold={mismatch_threshold}). Possible cross-patent contamination."
        )

    # Determine state
    if result.mismatch_reasons:
        # If patent number matches but fingerprint mismatches → UNRESOLVED
        # (the patent number is authoritative, but content is suspicious)
        if case_pn and retrieved_pn and _same_patent_number(case_pn, retrieved_pn):
            result.state = IDENTITY_UNRESOLVED
        else:
            result.state = IDENTITY_MISMATCH
    elif result.similarity_score >= similarity_threshold:
        result.state = IDENTITY_CONFIRMED
    else:
        # Borderline — not enough evidence to confirm or deny
        result.state = IDENTITY_UNRESOLVED

    return result


def _normalize_patent_number(raw: str) -> str:
    """Normalize patent number to canonical form."""
    if not raw:
        return ""
    s = raw.upper().replace("-", "").replace(" ", "").replace("/", "")
    if s.startswith("PATENT"):
        s = s[6:]
    if s.endswith("EN") and len(s) > 4:
        candidate = s[:-2]
        if re.match(r'^[A-Z]{2}\d+', candidate):
            s = candidate
    return s


def _same_patent_number(a: str, b: str) -> bool:
    """Check if two patent numbers refer to the same patent (ignoring kind code)."""
    if a == b:
        return True
    # Strip trailing kind code (1-2 letters at end)
    m_a = re.match(r'^([A-Z]{2})(\d+)', a)
    m_b = re.match(r'^([A-Z]{2})(\d+)', b)
    if m_a and m_b and m_a.group(1) == m_b.group(1) and m_a.group(2) == m_b.group(2):
        return True
    return False


def _text_similarity(a: str, b: str) -> float:
    """Compute text similarity using Jaccard over word sets."""
    if not a or not b:
        return 0.0
    sa = set(re.findall(r'\b[a-z]{3,}\b', a.lower()))
    sb = set(re.findall(r'\b[a-z]{3,}\b', b.lower()))
    if not sa or not sb:
        return 0.0
    intersection = sa & sb
    union = sa | sb
    return len(intersection) / len(union) if union else 0.0


# ----------------------- CONVENIENCE -----------------------
def is_identity_confirmed(result: IdentityValidationResult) -> bool:
    """Check if identity validation passed."""
    return result.state == IDENTITY_CONFIRMED


def should_stop_case(result: IdentityValidationResult) -> bool:
    """Check if case should be stopped due to identity mismatch."""
    return result.state == IDENTITY_MISMATCH

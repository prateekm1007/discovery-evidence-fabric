"""
epistemic_integrity/patent_coverage_contract.py — Patent search coverage proof

Per CEO directive P1:
  "'No prior art' needs more than a source citation.
   Such a claim requires a search-universe object:
     coverage contract
     sources executed
     sources ruled unnecessary
     queries
     dates
     jurisdictions
     families
     claims audited
     limitations
     rate limits
     API failures
     stopping rule
   Then the only permitted language is: 'No matching evidence was found
   within the audited search universe…'"
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone


@dataclass
class SearchQuery:
    query_id: str
    source: str  # "Lens" / "Scopus" / "Google Patents" / "PatSnap" / "PatentBear"
    query_text: str
    executed_at: str
    result_count: int
    top_results_reviewed: int  # how many we actually examined
    rate_limited: bool = False
    api_error: Optional[str] = None
    notes: str = ""


@dataclass
class PatentCoverageContract:
    """Required for any claim that says 'no prior art' or 'novel'."""
    contract_id: str  # PCC-CV-T<territory>-<seq>
    territory_id: str
    claim_being_supported: str  # the claim text that requires coverage proof

    # Search universe definition
    sources_executed: List[str] = field(default_factory=list)  # ["Lens", "Scopus", "Google Patents", ...]
    sources_ruled_unnecessary: List[str] = field(default_factory=list)  # with justification
    sources_blocked: List[str] = field(default_factory=list)  # e.g. PatSnap balance exhausted
    sources_unavailable: List[str] = field(default_factory=list)  # e.g. Compendex not subscribed

    # Queries executed
    queries: List[SearchQuery] = field(default_factory=list)

    # Coverage dimensions
    jurisdictions_covered: List[str] = field(default_factory=list)  # ["US", "EP", "WO", "JP", "CN"]
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    patent_families_audited: int = 0
    independent_claims_audited: int = 0
    dependent_claims_audited: int = 0

    # Limitations
    rate_limits_encountered: List[str] = field(default_factory=list)
    api_failures: List[str] = field(default_factory=list)
    language_limitations: List[str] = field(default_factory=list)  # e.g. "JP patents not translated"

    # Stopping rule
    stopping_rule_applied: str = ""  # e.g. "exhausted 5 source × 10 query matrix"
    coverage_completeness: str = ""  # COMPLETE / PARTIAL / BLOCKED

    # Permitted language
    permitted_claim_wording: str = (
        "No matching evidence was found within the audited search universe "
        "comprising {sources_executed} sources, {n_queries} queries, "
        "{jurisdictions_covered} jurisdictions, {date_range}. "
        "Coverage: {coverage_completeness}. Limitations: {limitations}."
    )

    # Forbidden language
    forbidden_claim_wording: List[str] = [
        "No prior art exists",
        "Nobody has done this",
        "This is completely novel",
        "No one has ever",
        "Unique in the field",
    ]

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_permitted_wording(self) -> str:
        """Generate the only permitted wording for a 'no prior art' claim."""
        return self.permitted_claim_wording.format(
            sources_executed=", ".join(self.sources_executed),
            n_queries=len(self.queries),
            jurisdictions_covered=", ".join(self.jurisdictions_covered),
            date_range=f"{self.date_range_start} to {self.date_range_end}" if self.date_range_start else "unspecified",
            coverage_completeness=self.coverage_completeness,
            limitations="; ".join(self.rate_limits_encountered + self.api_failures + self.language_limitations) or "none",
        )

    def validate(self) -> dict:
        """Validate that this coverage contract is sufficient for a 'no prior art' claim."""
        errors = []

        # Must have at least 3 sources executed
        if len(self.sources_executed) < 3:
            errors.append(f"INSUFFICIENT_SOURCES: only {len(self.sources_executed)} sources, need ≥3")

        # Must have at least 5 queries
        if len(self.queries) < 5:
            errors.append(f"INSUFFICIENT_QUERIES: only {len(self.queries)} queries, need ≥5")

        # Must cover at least US, EP, WO jurisdictions
        required_jurisdictions = {"US", "EP", "WO"}
        covered = set(self.jurisdictions_covered)
        missing = required_jurisdictions - covered
        if missing:
            errors.append(f"MISSING_JURISDICTIONS: {missing} not covered")

        # Must have date range
        if not self.date_range_start or not self.date_range_end:
            errors.append("MISSING_DATE_RANGE")

        # Must have coverage completeness declared
        if not self.coverage_completeness:
            errors.append("MISSING_COVERAGE_COMPLETENESS")

        # If coverage is PARTIAL or BLOCKED, claim cannot say "no prior art"
        if self.coverage_completeness in ["PARTIAL", "BLOCKED"]:
            errors.append(
                f"COVERAGE_{self.coverage_completeness}: cannot claim 'no prior art' — "
                "must use 'No matching evidence was found within the audited search universe'"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "permitted_wording": self.get_permitted_wording(),
        }


class PatentCoverageRegistry:
    """Registry of all patent coverage contracts."""

    def __init__(self, registry_dir: Path):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.contracts: Dict[str, PatentCoverageContract] = {}
        self._load()

    def _file(self) -> Path:
        return self.registry_dir / "patent_coverage_contracts.json"

    def _load(self):
        path = self._file()
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            for item in data.get("contracts", []):
                # Reconstruct queries
                queries = [SearchQuery(**q) for q in item.pop("queries", [])]
                contract = PatentCoverageContract(**item)
                contract.queries = queries
                self.contracts[contract.contract_id] = contract

    def _save(self):
        with open(self._file(), "w") as f:
            json.dump({
                "schema_version": "1.0.0",
                "contracts": [asdict(c) for c in self.contracts.values()],
            }, f, indent=2, default=str)

    def register_contract(self, contract: PatentCoverageContract):
        self.contracts[contract.contract_id] = contract
        self._save()

    def get_contract_for_claim(self, claim_text: str) -> Optional[PatentCoverageContract]:
        """Find the coverage contract that supports a given 'no prior art' claim."""
        for contract in self.contracts.values():
            if contract.claim_being_supported in claim_text or claim_text in contract.claim_being_supported:
                return contract
        return None

    def validate_no_prior_art_claim(self, claim_text: str) -> dict:
        """Validate a 'no prior art' claim against its coverage contract.

        Returns:
          - valid: bool
          - errors: list of issues
          - required_contract: bool (whether a contract is needed)
          - permitted_wording: str (if contract exists)
        """
        # Check if claim contains forbidden language
        claim_lower = claim_text.lower()
        forbidden_found = []
        for forbidden in PatentCoverageContract.__dataclass_fields__['forbidden_claim_wording'].default:
            if forbidden.lower() in claim_lower:
                forbidden_found.append(forbidden)

        if forbidden_found:
            return {
                "valid": False,
                "errors": [f"FORBIDDEN_WORDING: {forbidden_found}"],
                "required_contract": True,
                "permitted_wording": None,
            }

        # Check if claim needs a coverage contract
        needs_contract = any(phrase in claim_lower for phrase in [
            "no prior art", "no matching evidence", "not found in", "novel",
        ])

        if not needs_contract:
            return {
                "valid": True,
                "errors": [],
                "required_contract": False,
                "permitted_wording": None,
            }

        # Find the contract
        contract = self.get_contract_for_claim(claim_text)
        if not contract:
            return {
                "valid": False,
                "errors": ["NO_COVERAGE_CONTRACT: 'no prior art' claim has no registered PatentCoverageContract"],
                "required_contract": True,
                "permitted_wording": None,
            }

        # Validate the contract
        validation = contract.validate()
        return {
            "valid": validation["valid"],
            "errors": validation["errors"],
            "required_contract": True,
            "permitted_wording": validation["permitted_wording"],
        }

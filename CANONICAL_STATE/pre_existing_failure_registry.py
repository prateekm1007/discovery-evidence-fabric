"""
CANONICAL_STATE/pre_existing_failure_registry.py

Machine-readable registry of PRE_EXISTING_CERTIFICATION_FAILURE records.

Per CEO directive (2026-08-21 third deep audit):
  'The system must produce a machine-readable distinction:
   PRE_EXISTING_CERTIFICATION_FAILURE
   with: first_seen_commit, affected_territories, root_cause,
         why_round20_did_not_introduce_it, owner, remediation_state.
   It must not disappear into a generic "pre-existing" sentence.'

This module loads and validates the quarantine records in
CANONICAL_STATE/PRE_EXISTING_CERTIFICATION_FAILURES.json, and exposes
them to the certification gate so that G5/G1/G13 can formally
distinguish:

  (a) a NEW drift introduced by the current commit (must fail), from
  (b) a PRE_EXISTING drift that has been formally quarantined (must
      be reported as QUARANTINED, not silently ignored).

Design rules:
  - The registry is APPEND-ONLY at the record level. A quarantined
    failure cannot be deleted; it can only transition remediation_state
    from QUARANTINED → REMEDIATED (with an audit trail).
  - Each record MUST include the six required fields:
      first_seen_commit, affected_territories, root_cause,
      why_round20_did_not_introduce_it, owner, remediation_state
  - The registry is consulted by G5 to suppress formally-quarantined
    mismatches from the gate's RED verdict — but ONLY when the
    mismatch exactly matches a quarantined record's signature.
  - NEW mismatches not present in the registry still fail G5.
  - The registry itself is content-addressed: any change to a record
    invalidates its record_id and requires a new versioned append.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "CANONICAL_STATE" / "PRE_EXISTING_CERTIFICATION_FAILURES.json"


REQUIRED_FIELDS = (
    "first_seen_commit",
    "affected_territories",
    "root_cause",
    "why_round20_did_not_introduce_it",
    "owner",
    "remediation_state",
)


@dataclass(frozen=True)
class QuarantineSignature:
    """The signature of a quarantined failure — used for matching.

    Two failures match if they have the same territory_id and the same
    portfolio-vs-ledger version drift. This is what G5 uses to decide
    whether a NEW mismatch is already formally quarantined.
    """
    territory_id: str
    portfolio_version: str
    ledger_version: str

    def matches(self, territory_id: str, portfolio_version: str, ledger_version: str) -> bool:
        return (
            self.territory_id == territory_id
            and self.portfolio_version == portfolio_version
            and self.ledger_version == ledger_version
        )


@dataclass
class PreExistingFailureRecord:
    """A single quarantined pre-existing certification failure."""
    record_id: str
    title: str
    failure_class: str
    failure_subtype: str
    first_seen_commit: str
    affected_territories: list[dict]
    root_cause: str
    why_round20_did_not_introduce_it: dict
    owner: str
    remediation_state: str  # QUARANTINED / PARTIALLY_QUARANTINED / REMEDIATED / SUPERSEDED
    status: str  # ACTIVE / ARCHIVED
    # P0-B (twenty-second round): Quarantine discipline fields
    remediation_deadline: str = ""  # ISO timestamp — quarantine expires after this
    review_after: str = ""  # ISO timestamp — next required revalidation
    review_interval_days: int = 7  # how often revalidation must occur
    last_revalidated_at: str = ""  # ISO timestamp of last revalidation
    last_revalidated_by: str = ""
    last_revalidation_commit: str = ""
    raw_record: dict = field(default_factory=dict)
    signatures: list[QuarantineSignature] = field(default_factory=list)

    def __post_init__(self):
        # Build signatures from affected_territories
        for t in self.affected_territories:
            self.signatures.append(QuarantineSignature(
                territory_id=t["territory_id"],
                portfolio_version=t["portfolio_frozen_at_version"],
                ledger_version=t["ledger_terminal_artifact_version"],
            ))

    def is_expired(self, now: datetime = None) -> bool:
        """P0-B (twenty-second round): Has the remediation_deadline passed?

        If remediation_state != REMEDIATED and the deadline has passed,
        the quarantine has EXPIRED — find_match() must return None,
        forcing G5 to fail RED with 'QUARANTINE_EXPIRED'.
        """
        if not now:
            now = datetime.now(timezone.utc)
        if self.remediation_state == "REMEDIATED":
            return False  # Remediated records don't expire
        if not self.remediation_deadline:
            return False  # No deadline set — cannot expire (legacy compat)
        try:
            deadline = datetime.fromisoformat(self.remediation_deadline.replace("Z", "+00:00"))
            return now > deadline
        except (ValueError, AttributeError):
            return False  # Invalid deadline format — don't expire silently

    def is_stale(self, now: datetime = None) -> bool:
        """P0-B (twenty-second round): Has revalidation been skipped too long?

        If review_interval_days * 2 have passed since last_revalidated_at
        without a revalidation entry, the quarantine is STALE — find_match()
        must return None, forcing G5 to fail RED with 'QUARANTINE_STALE'.
        """
        if not now:
            now = datetime.now(timezone.utc)
        if self.remediation_state == "REMEDIATED":
            return False
        if not self.last_revalidated_at or self.review_interval_days <= 0:
            return False  # No revalidation history — can't determine staleness
        try:
            last_rev = datetime.fromisoformat(self.last_revalidated_at.replace("Z", "+00:00"))
            max_gap_days = self.review_interval_days * 2
            gap = now - last_rev
            return gap.days > max_gap_days
        except (ValueError, AttributeError):
            return False


class PreExistingFailureRegistry:
    """Loads and validates the quarantine registry.

    The registry is consulted by G5 to formally recognize pre-existing
    failures that have been quarantined. A quarantined failure is NOT
    silently ignored — it is reported as QUARANTINED in the gate output,
    and the gate distinguishes:

      G5 RED — new drift (NOT in registry)
      G5 GREEN (QUARANTINED) — drift matches a registry record
      G5 GREEN — no drift
    """

    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self.registry_path = registry_path
        self.records: list[PreExistingFailureRecord] = []
        self.load_errors: list[str] = []

    def load(self) -> bool:
        """Load and validate the registry.

        Returns:
          True if the registry is valid and loadable (or absent, which
          is also valid — an empty registry means no failures have been
          quarantined). False if the registry is present but malformed.
        """
        self.records = []
        self.load_errors = []

        if not self.registry_path.exists():
            # Empty registry is valid
            return True

        try:
            with open(self.registry_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.load_errors.append(f"Registry is not valid JSON: {e}")
            return False

        # The registry may be a single record or a list of records
        records = data if isinstance(data, list) else [data]
        for rec in records:
            # Validate required fields
            missing = [f for f in REQUIRED_FIELDS if f not in rec]
            if missing:
                self.load_errors.append(
                    f"Record {rec.get('record_id', '?')} missing required fields: {missing}"
                )
                continue
            # Validate remediation_state
            rs = rec.get("remediation_state", "")
            if rs not in ("QUARANTINED", "PARTIALLY_QUARANTINED", "REMEDIATED", "SUPERSEDED"):
                self.load_errors.append(
                    f"Record {rec.get('record_id', '?')} has invalid remediation_state: {rs}"
                )
                continue
            # Build the record
            r = PreExistingFailureRecord(
                record_id=rec.get("record_id", ""),
                title=rec.get("title", ""),
                failure_class=rec.get("failure_class", ""),
                failure_subtype=rec.get("failure_subtype", ""),
                first_seen_commit=rec.get("first_seen_commit", ""),
                affected_territories=rec.get("affected_territories", []),
                root_cause=rec.get("root_cause", ""),
                why_round20_did_not_introduce_it=rec.get("why_round20_did_not_introduce_it", {}),
                owner=rec.get("owner", ""),
                remediation_state=rs,
                status=rec.get("status", "ACTIVE"),
                # P0-B (twenty-second round): discipline fields
                remediation_deadline=rec.get("remediation_deadline", ""),
                review_after=rec.get("review_after", ""),
                review_interval_days=rec.get("review_interval_days", 7),
                last_revalidated_at=rec.get("last_revalidated_at", ""),
                last_revalidated_by=rec.get("last_revalidated_by", ""),
                last_revalidation_commit=rec.get("last_revalidation_commit", ""),
                raw_record=rec,
            )
            self.records.append(r)

        return len(self.load_errors) == 0

    def find_match(self, territory_id: str, portfolio_version: str, ledger_version: str) -> Optional[PreExistingFailureRecord]:
        """Find a quarantined record matching the given drift signature.

        Returns the matching record if one exists and is:
          - ACTIVE
          - remediation_state in (QUARANTINED, PARTIALLY_QUARANTINED)
          - NOT expired (remediation_deadline not passed)
          - NOT stale (last_revalidated_at within review_interval_days * 2)

        Returns None otherwise — which means the drift is treated as NEW
        and must fail G5 RED. This includes expired/stale quarantines,
        which force re-attention rather than silently persisting.
        """
        for r in self.records:
            if r.status != "ACTIVE":
                continue
            if r.remediation_state not in ("QUARANTINED", "PARTIALLY_QUARANTINED"):
                continue
            # P0-B (twenty-second round): enforce expiry and staleness
            if r.is_expired():
                continue  # Expired quarantine — treat as no match (RED)
            if r.is_stale():
                continue  # Stale quarantine — treat as no match (RED)
            for sig in r.signatures:
                if sig.matches(territory_id, portfolio_version, ledger_version):
                    return r
        return None

    def find_expired_or_stale(self) -> list[PreExistingFailureRecord]:
        """P0-B (twenty-second round): Return all expired or stale quarantined records.

        The gate can use this to report WHY a previously-quarantined failure
        is now failing RED — distinguishing 'QUARANTINE_EXPIRED' from
        'NEW drift (not quarantined)'.
        """
        result = []
        for r in self.records:
            if r.status != "ACTIVE":
                continue
            if r.remediation_state not in ("QUARANTINED", "PARTIALLY_QUARANTINED"):
                continue
            if r.is_expired():
                result.append(r)
            elif r.is_stale():
                result.append(r)
        return result

    def active_quarantined_count(self) -> int:
        """Count of active quarantined records (including partially quarantined)."""
        return sum(
            1 for r in self.records
            if r.status == "ACTIVE" and r.remediation_state in ("QUARANTINED", "PARTIALLY_QUARANTINED")
        )

    def to_dict(self) -> dict:
        return {
            "registry_path": str(self.registry_path),
            "records_loaded": len(self.records),
            "active_quarantined": self.active_quarantined_count(),
            "load_errors": self.load_errors,
            "records": [
                {
                    "record_id": r.record_id,
                    "title": r.title,
                    "failure_class": r.failure_class,
                    "first_seen_commit": r.first_seen_commit,
                    "remediation_state": r.remediation_state,
                    "status": r.status,
                    "signatures": [
                        {
                            "territory_id": s.territory_id,
                            "portfolio_version": s.portfolio_version,
                            "ledger_version": s.ledger_version,
                        }
                        for s in r.signatures
                    ],
                }
                for r in self.records
            ],
        }


def main():
    """Print the registry state."""
    reg = PreExistingFailureRegistry()
    valid = reg.load()
    print("=" * 78)
    print("PRE_EXISTING_CERTIFICATION_FAILURE REGISTRY")
    print("=" * 78)
    print(f"Registry path:     {reg.registry_path}")
    print(f"Valid:             {valid}")
    print(f"Records loaded:    {len(reg.records)}")
    print(f"Active quarantined:{reg.active_quarantined_count()}")
    if reg.load_errors:
        print(f"Load errors:       {reg.load_errors}")
    print()
    for r in reg.records:
        print(f"  Record: {r.record_id}")
        print(f"    Title:       {r.title[:80]}")
        print(f"    Class:       {r.failure_class} / {r.failure_subtype}")
        print(f"    First seen:  {r.first_seen_commit[:16]}")
        print(f"    Owner:       {r.owner}")
        print(f"    State:       {r.remediation_state} / {r.status}")
        for sig in r.signatures:
            print(f"    Signature:   {sig.territory_id} portfolio={sig.portfolio_version} ledger={sig.ledger_version}")
        print()
    return 0 if valid else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

"""Patent Discovery Router + Evidence Router (Google-free)."""
from __future__ import annotations
import os, sys, json, re, time, hashlib
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.patsnap_claims import fetch_patsnap_claims
from discovery_fabric.prior_art_v2.elite_v3 import _now_utc, _sha256


@dataclass
class GoldPatent:
    patent_number: str
    claims: List[str]
    claim_count: int
    independent_claim_count: int
    content_hash: str
    patsnap_patent_id: str
    claim_hash: str
    source: str = "PATSNAP"
    retrieved_at_utc: str = ""


class PatentEvidenceRouter:
    """Retrieves actual claims from patent IDs via PatSnap claim-data."""

    def retrieve(self, patent_ids: List[str]) -> List[GoldPatent]:
        gold = []
        for pid in patent_ids[:10]:
            record = fetch_patsnap_claims(pid)
            if record and record.claims:
                claim_hash = _sha256(" ".join(record.claims).lower())
                gold.append(GoldPatent(
                    patent_number=record.patent_number,
                    claims=record.claims,
                    claim_count=record.claim_count,
                    independent_claim_count=record.independent_claim_count,
                    content_hash=record.content_hash,
                    patsnap_patent_id=record.patsnap_patent_id,
                    claim_hash=claim_hash,
                    retrieved_at_utc=record.retrieved_at_utc,
                ))
        return gold

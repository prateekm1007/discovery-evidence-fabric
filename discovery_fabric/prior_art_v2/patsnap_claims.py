"""
PatSnap Claim Data Adapter
===========================

Retrieves actual patent claim text from PatSnap's claim-data endpoint.

ENDPOINT: GET https://connect.patsnap.com/basic-patent-data/claim-data
PARAMS: patent_number=<PUBLICATION_NUMBER>  (e.g., US11912894B2)
AUTH: Authorization: Bearer <API_KEY>

RETURNS:
  {
    "status": true,
    "data": [{
      "patent_id": "<PatSnap internal UUID>",
      "pn": "<publication number>",
      "claim_count": <int>,
      "claims": [{
        "lang": "EN",
        "data_format": "original",
        "claim_independent_count": <int>,
        "claim_text": "<HTML with claim text>"
      }]
    }]
  }

This is a REAL patent claim retrieval source — independent of Google Patents.
"""
from __future__ import annotations
import os, sys, json, re, ssl, urllib.request, urllib.error, hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def _strip_html(text: str) -> str:
    """Strip HTML tags from PatSnap claim text."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


@dataclass
class PatSnapClaimRecord:
    """Patent claim record from PatSnap."""
    patent_number: str  # e.g., US11912894B2
    patsnap_patent_id: str  # PatSnap internal UUID
    claim_count: int
    independent_claim_count: int
    claims: List[str]  # cleaned claim text
    raw_claim_text: str  # original HTML
    source_url: str
    retrieved_at_utc: str
    content_hash: str


def fetch_patsnap_claims(patent_number: str) -> Optional[PatSnapClaimRecord]:
    """
    Retrieve patent claims from PatSnap claim-data endpoint.

    Returns PatSnapClaimRecord with actual claim text, or None if failed.
    """
    keys_file = Path("/home/z/my-project/discovery-evidence-fabric/.env.keys")
    api_key = ""
    if keys_file.exists():
        for line in keys_file.read_text().splitlines():
            if line.startswith("PATSNAP_EUREKA_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break
    if not api_key:
        return None

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"https://connect.patsnap.com/basic-patent-data/claim-data?patent_number={patent_number}"

    try:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = json.loads(resp.read())

        if not data.get("status"):
            return None

        records = data.get("data", [])
        if not records:
            return None

        record = records[0]
        claims_data = record.get("claims", [])
        if not claims_data:
            return None

        claim_entry = claims_data[0]
        raw_html = claim_entry.get("claim_text", "")

        # Parse claims from HTML
        claims = _parse_claims_from_html(raw_html)

        return PatSnapClaimRecord(
            patent_number=record.get("pn", patent_number),
            patsnap_patent_id=record.get("patent_id", ""),
            claim_count=record.get("claim_count", len(claims)),
            independent_claim_count=claim_entry.get("claim_independent_count", 0),
            claims=claims,
            raw_claim_text=raw_html,
            source_url=url,
            retrieved_at_utc=_now_utc(),
            content_hash=_sha256(raw_html),
        )
    except Exception:
        return None


def _parse_claims_from_html(html: str) -> List[str]:
    """Parse individual claims from PatSnap HTML format."""
    claims = []

    # Find all claim divs (indep-clm and dep-clm)
    # Format: <div class="indep-clm" num="1">...</div>
    # or: <div class="dep-clm" num="3" parent="2">...</div>

    # Split by claim number markers
    pattern = r'<div class="(?:indep|dep)-clm" num="(\d+)"[^>]*>(.*?)</div>'
    matches = re.findall(pattern, html, re.DOTALL)

    # Group by claim number
    current_claim_num = None
    current_claim_parts = []

    for num, content in matches:
        if num != current_claim_num:
            if current_claim_num is not None and current_claim_parts:
                claim_text = " ".join(_strip_html(p) for p in current_claim_parts)
                claims.append(claim_text[:3000])
            current_claim_num = num
            current_claim_parts = [content]
        else:
            current_claim_parts.append(content)

    # Don't forget the last claim
    if current_claim_num is not None and current_claim_parts:
        claim_text = " ".join(_strip_html(p) for p in current_claim_parts)
        claims.append(claim_text[:3000])

    # If no structured claims found, try plain text
    if not claims:
        text = _strip_html(html)
        # Split on "1." "2." etc.
        parts = re.split(r'(?=\b\d+\.\s+[A-Z])', text)
        for part in parts:
            part = part.strip()
            if re.match(r'^\d+\.\s+', part) and len(part) > 10:
                claims.append(part[:3000])

    return claims


# ----------------------- SOURCE CAPABILITY MATRIX -----------------------
def build_capability_matrix() -> Dict[str, Any]:
    """Build the patent source capability matrix."""
    from discovery_fabric.prior_art_v2.source_failover import check_all_sources

    statuses = check_all_sources()

    matrix = {}
    for s in statuses:
        matrix[s.source_id] = {
            "search": s.can_search,
            "patent_record": False,  # Will be updated below
            "claims": s.can_retrieve_claims,
            "family": False,
            "priority_date": False,
            "legal_status": False,
            "full_text": False,
            "status": s.status,
            "checked_at": s.checked_at,
        }

    # Test PatSnap claim-data specifically
    ps_claim_test = fetch_patsnap_claims("US11912894B2")
    if ps_claim_test and ps_claim_test.claims:
        matrix["PATSNAP"]["claims"] = True
        matrix["PATSNAP"]["patent_record"] = True
        matrix["PATSNAP"]["status"] = "CLAIM_DATA_AVAILABLE"
        matrix["PATSNAP"]["claims_test_patent"] = "US11912894B2"
        matrix["PATSNAP"]["claims_test_count"] = len(ps_claim_test.claims)
    else:
        matrix["PATSNAP"]["claims"] = False
        matrix["PATSNAP"]["status"] = "SEARCH_COUNT_ONLY"

    return matrix


# ----------------------- CLI / SELF-TEST -----------------------
if __name__ == "__main__":
    print("="*60)
    print("PATSNAP CLAIM DATA ADAPTER — SELF-TEST")
    print("="*60)

    # Test with known patents
    test_patents = [
        "US11912894B2",  # Antimicrobial hydrogel coatings (the killing patent)
        "US10919033B2",  # Flow cells with hydrogel coating (Illumina)
        "AU2021204165B2",  # Hydrogel coating method
    ]

    for pn in test_patents:
        print(f"\n=== {pn} ===")
        record = fetch_patsnap_claims(pn)
        if record:
            print(f"  patent_number: {record.patent_number}")
            print(f"  patsnap_patent_id: {record.patsnap_patent_id}")
            print(f"  claim_count: {record.claim_count}")
            print(f"  independent_claim_count: {record.independent_claim_count}")
            print(f"  parsed_claims: {len(record.claims)}")
            if record.claims:
                print(f"  first_claim: {record.claims[0][:200]}...")
            print(f"  content_hash: {record.content_hash[:20]}...")
        else:
            print(f"  FAILED — no claims retrieved")

    # Build capability matrix
    print(f"\n{'='*60}")
    print("SOURCE CAPABILITY MATRIX")
    print("="*60)
    matrix = build_capability_matrix()
    print(json.dumps(matrix, indent=2))

    # Save
    out = Path("/home/z/my-project/discovery-evidence-fabric/patent_sources/PATENT_SOURCE_CAPABILITY_MATRIX.json")
    out.write_text(json.dumps(matrix, indent=2))
    print(f"\nSaved: {out}")

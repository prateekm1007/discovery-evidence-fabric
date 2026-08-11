"""Map OpenAlex Work objects to canonical EvidenceItem."""

from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _reconstruct_abstract(inverted: Optional[Dict[str, list]]) -> Optional[str]:
    if not inverted:
        return None
    try:
        max_pos = max(max(pos) for pos in inverted.values())
    except ValueError:
        return None
    arr = [None] * (max_pos + 1)
    for word, positions in inverted.items():
        for p in positions:
            if 0 <= p < len(arr):
                arr[p] = word
    return " ".join(w for w in arr if w is not None)


def openalex_work_to_evidence_item(work: Dict[str, Any], retrieval_method: str = "openalex_api") -> Dict[str, Any]:
    """Convert a single OpenAlex Work dict into an EvidenceItem."""
    now = datetime.now(timezone.utc).isoformat()
    oid = work.get("id") or ""
    title = work.get("title") or work.get("display_name")
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

    authors = []
    for a in (work.get("authorships") or [])[:50]:
        auth = a.get("author") or {}
        authors.append({
            "name": auth.get("display_name") or a.get("raw_author_name"),
            "orcid": auth.get("orcid"),
            "id": auth.get("id"),
        })

    classifications = []
    for t in (work.get("topics") or [])[:10]:
        classifications.append({
            "scheme": "openalex_topic",
            "id": t.get("id"),
            "display_name": t.get("display_name"),
            "score": t.get("score"),
        })
    primary = work.get("primary_topic") or {}
    if primary:
        classifications.insert(0, {
            "scheme": "openalex_primary_topic",
            "id": primary.get("id"),
            "display_name": primary.get("display_name"),
            "domain": (primary.get("domain") or {}).get("display_name"),
        })

    # Content hash of core fields
    core = {
        "source_id": oid,
        "title": title,
        "doi": work.get("doi"),
        "publication_year": work.get("publication_year"),
    }
    content_hash = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()

    item = {
        "id": f"openalex:{oid.split('/')[-1] if oid else content_hash[:16]}",
        "source_type": "scientific_paper",
        "source": "OpenAlex",
        "source_id": oid,
        "source_uri": oid,
        "jurisdiction": None,
        "title": title,
        "abstract": abstract[:8000] if abstract else None,
        "claims": None,
        "full_text": None,
        "citations": None,
        "references": None,
        "authors": authors or None,
        "inventors": None,
        "organizations": None,
        "classifications": classifications or None,
        "publication_date": work.get("publication_date"),
        "priority_date": None,
        "family_id": None,
        "license": (work.get("open_access") or {}).get("oa_status"),
        "access_status": (work.get("open_access") or {}).get("oa_status"),
        "retrieval_timestamp": now,
        "retrieval_method": retrieval_method,
        "content_hash": content_hash,
        "provenance": {
            "provider": "OpenAlex",
            "retrieved_at": now,
            "query_or_method": retrieval_method,
            "api_version": "api.openalex.org",
            "license_note": "OpenAlex data is open; respect individual work licenses",
            "secondary_enrichment": [],
        },
        "source_specific": {
            "openalex_id": oid,
            "doi": work.get("doi"),
            "type": work.get("type"),
            "cited_by_count": work.get("cited_by_count"),
            "language": work.get("language"),
            "is_retracted": work.get("is_retracted"),
            "ids": work.get("ids"),
        },
        "epistemic_state": "OBSERVED",
    }
    return item

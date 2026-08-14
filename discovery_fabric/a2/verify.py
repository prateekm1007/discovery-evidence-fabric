"""A2 verify — evidence verification."""
from __future__ import annotations
import json, re

def verify_evidence(candidate: dict, evidence: list[dict]) -> dict:
    """Step 4: Verify that every assertion has source_id + source_hash + exact span."""
    issues = []
    src = candidate.get("source_evidence", {})

    # Check source_id
    if not src.get("source_id"):
        issues.append("missing_source_id")

    # Check source_hash
    if not src.get("source_hash"):
        issues.append("missing_source_hash")

    # Check source_span exists and is non-empty
    span = src.get("source_span", "")
    if not span or len(span) < 10:
        issues.append("missing_source_span")

    # Check mechanism_source_span is verbatim substring of source_span
    mech_span = candidate.get("mechanism_source_span", "")
    if mech_span and mech_span != "NO_SPAN":
        if mech_span not in (evidence[0]["abstract"] if evidence else ""):
            if mech_span.strip() not in (evidence[0]["abstract"] if evidence else ""):
                issues.append("mechanism_span_not_verbatim")

    # Check evidence class
    evidence_class = "SUPPORTED" if not issues else "UNSUPPORTED"

    result = {
        "verified": len(issues) == 0,
        "evidence_class": evidence_class,
        "issues": issues,
        "source_id": src.get("source_id", ""),
        "source_hash": src.get("source_hash", ""),
        "span_present": bool(span),
        "mechanism_span_verbatim": mech_span in (evidence[0]["abstract"] if evidence else "") if mech_span and mech_span != "NO_SPAN" else False,
    }
    print(f"  [verify] verified={result['verified']} class={evidence_class} issues={issues}")
    return result

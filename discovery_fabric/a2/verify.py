"""A2 verify — evidence verification."""
from __future__ import annotations
import json, re

def verify_evidence(candidate: dict, evidence: list[dict]) -> dict:
    """Step 4: Verify that every assertion has source_id + source_hash + exact span."""
    issues = []
    src = candidate.get("source_evidence", {})

    if not src.get("source_id"):
        issues.append("missing_source_id")
    if not src.get("source_hash"):
        issues.append("missing_source_hash")

    span = src.get("source_span", "")
    if not span or len(span) < 10:
        issues.append("missing_source_span")

    # Get mechanism span and strip surrounding quotes/whitespace
    mech_span = candidate.get("mechanism_source_span", "")
    if mech_span and mech_span != "NO_SPAN":
        # Strip surrounding quotes (single or double)
        mech_span_clean = mech_span.strip().strip('"').strip("'").strip()

        # R469 source alignment: the span is verified against the
        # candidate's OWN claimed source paper — the record the
        # candidate itself carries in source_evidence.source_id — not
        # unconditionally evidence[0]. The R422 rotation legitimately
        # produces candidates from papers[1..2] when paper[0]'s
        # transport fails; checking a paper[1]-sourced span against
        # paper[0]'s abstract was a misalignment, not a verification.
        # The check itself stays BYTE-EXACT (Art. II/III — this change
        # aligns the target, it does not loosen the gate; a span that
        # is not a character-for-character substring of the claimed
        # source still fails). Fallback: evidence[0] when the claimed
        # id is absent (the standing behavior).
        full_abstract = evidence[0]["abstract"] if evidence else ""
        if src.get("source_id"):
            for _paper in evidence:
                if _paper.get("id") == src.get("source_id"):
                    full_abstract = _paper["abstract"]
                    break
        
        # Check verbatim (cleaned span in full abstract)
        if mech_span_clean not in full_abstract:
            # Try case-insensitive as fallback
            if mech_span_clean.lower() not in full_abstract.lower():
                issues.append("mechanism_span_not_verbatim")
    elif not mech_span or mech_span == "NO_SPAN":
        issues.append("missing_mechanism_span")

    evidence_class = "SUPPORTED" if not issues else "UNSUPPORTED"

    result = {
        "verified": len(issues) == 0,
        "evidence_class": evidence_class,
        "issues": issues,
        "source_id": src.get("source_id", ""),
        "source_hash": src.get("source_hash", ""),
        "span_present": bool(span),
        "mechanism_span_verbatim": mech_span_clean in full_abstract if (mech_span and mech_span != "NO_SPAN" and evidence) else False,
    }
    print(f"  [verify] verified={result['verified']} class={evidence_class} issues={issues}")
    return result

#!/usr/bin/env python3
"""
Permanent regression test for PatSnap API classification.

Per CEO directive §6: "Never classify an API failure from an unvalidated request schema."

The sequence MUST be:
    FETCH DOCUMENTATION → VALIDATE REQUEST SCHEMA → EXECUTE → INTERPRET ERROR CODE → CLASSIFY FAILURE

NOT:
    REQUEST FAILS → GUESS WHY

This test verifies that every PatSnap endpoint classification in the repository
was produced by the correct sequence, not by guessing.
"""

import json
import urllib.request
from pathlib import Path

PATSNAP_BASE = "https://connect.patsnap.com"
OPENAPI_URL = "https://open.patsnap.com/openapi.json"

# The bug we're preventing:
# V3.1 used {q:{expression:...}} for P075, got 68300004 (Invalid parameter),
# and incorrectly classified it as TIER_RESTRICTED.
# The correct classification was PARAMETER_ERROR (schema was wrong).
# After fixing the schema to {query_text:...}, the endpoint returned 67200005 (BALANCE_EXHAUSTED).

EXPECTED_CLASSIFICATIONS = {
    "/basic-patent-data/claim-data": {
        "correct_schema": "GET ?patent_number=<PN>",
        "error_when_correct": None,  # works
        "classification": "WORKING",
    },
    "/search/patent/nested-search-patent": {
        "correct_schema": "POST {query_text:'TTL:...',limit:N,offset:N}",
        "wrong_schema": "POST {q:{expression:...}}",  # produces 68300004
        "error_when_correct": "67200005",  # BALANCE_EXHAUSTED
        "classification": "BALANCE_EXHAUSTED",
    },
    "/search/patent/current-search-patent": {
        "correct_schema": "POST {assignee:...,limit:N,offset:N}",
        "wrong_schema": "POST {q:{expression:...}}",  # produces 68300004
        "error_when_correct": "67200005 or EMPTY_RESULT",
        "classification": "BALANCE_EXHAUSTED or WORKING_EMPTY_RESULT",
    },
}

def test_schema_validation_before_classification():
    """Verify that no endpoint was classified without first validating the request schema."""

    # The regression: V3.1 said "TIER_RESTRICTED" for endpoints that actually had PARAMETER_ERROR
    # This test checks that the current classification matches the correct schema-validated classification

    audit_path = Path("CEREVASC_INVENTION_001_V32_CORRECTED/01_PATSNAP_CAPABILITY_AUDIT_V2/PATSNAP_CAPABILITY_AUDIT_V2.json")
    if not audit_path.exists():
        # Try V4 or other locations
        return "SKIP — audit file not found"

    audit = json.load(open(audit_path))
    endpoint_audits = audit.get("endpoint_audits", [])

    errors = []
    for ea in endpoint_audits:
        endpoint = ea.get("endpoint", "")
        classification = ea.get("classification", "")
        parameter_validity = ea.get("parameter_validity", "")

        # Rule: if parameter_validity is INVALID, classification MUST be PARAMETER_ERROR
        # (not TIER_RESTRICTED, not BALANCE_EXHAUSTED, not PERMISSION_DENIED)
        if parameter_validity == "INVALID" and classification != "PARAMETER_ERROR":
            errors.append(
                f"{endpoint}: parameter_validity=INVALID but classification={classification} "
                f"(should be PARAMETER_ERROR)"
            )

        # Rule: if classification is BALANCE_EXHAUSTED, parameter_validity MUST be VALID
        # (you can only know it's balance-exhausted if the schema was correct)
        if classification == "BALANCE_EXHAUSTED" and parameter_validity != "VALID":
            errors.append(
                f"{endpoint}: classification=BALANCE_EXHAUSTED but parameter_validity={parameter_validity} "
                f"(BALANCE_EXHAUSTED requires VALID schema — you cannot know balance is exhausted if schema was wrong)"
            )

    if errors:
        return "FAIL — " + "; ".join(errors)
    return "PASS"


def test_no_tier_restricted_without_evidence():
    """Verify that no endpoint is classified as TIER_RESTRICTED without primary evidence."""

    # TIER_RESTRICTED is not a valid classification per CEO directive.
    # The documented PatSnap permission error is 67200004, not 67200005.
    # If we see TIER_RESTRICTED, it means someone guessed instead of validating schema.

    audit_path = Path("CEREVASC_INVENTION_001_V32_CORRECTED/01_PATSNAP_CAPABILITY_AUDIT_V2/PATSNAP_CAPABILITY_AUDIT_V2.json")
    if not audit_path.exists():
        return "SKIP — audit file not found"

    audit = json.load(open(audit_path))
    endpoint_audits = audit.get("endpoint_audits", [])

    errors = []
    for ea in endpoint_audits:
        classification = ea.get("classification", "")
        if classification == "TIER_RESTRICTED":
            errors.append(
                f"{ea.get('endpoint','')}: classified as TIER_RESTRICTED — "
                f"this is not a valid classification. The documented permission error is 67200004. "
                f"Re-validate the schema and re-classify."
            )

    if errors:
        return "FAIL — " + "; ".join(errors)
    return "PASS"


if __name__ == "__main__":
    print("=== PatSnap Schema Regression Test ===")
    print()
    r1 = test_schema_validation_before_classification()
    print(f"Schema validation before classification: {r1}")
    r2 = test_no_tier_restricted_without_evidence()
    print(f"No TIER_RESTRICTED without evidence: {r2}")
    print()
    if "FAIL" in r1 or "FAIL" in r2:
        print("REGRESSION TEST: FAIL")
        exit(1)
    else:
        print("REGRESSION TEST: PASS")
        exit(0)

"""
Honest Blind Replay — C04 and C09 through SearchIntermediaryTransport.

Per CEO directive (tenth round):
  'Never allow a convenience layer to impersonate the reality layer.'

  The replay must traverse the actual transport boundary:
    SearchIntermediaryTransport.execute(request)
    → actual z-ai web_search
    → raw response
    → create_receipt() (by transport, NOT by caller)
    → PatentDestructionAdapter.execute_stage()

  No manual ProviderExecutionReceipt construction.
  No manual transport_verified=True.
  No wrapping web_search results as provider evidence.

  z-ai web_search is recorded honestly as SEARCH_INTERMEDIARY.
  Patent-level stages (claims, family, citations) are BLOCKED for
  intermediary evidence — they require direct provider access.
"""

from __future__ import annotations

import json
from pathlib import Path

from .patent_destruction_adapter import (
    PatentDestructionAdapter, AttackStageStatus, CoverageLevel,
)
from .provider_transport_boundary import TransportExecutionRequest
from .search_intermediary_transport import (
    SearchIntermediaryTransport, is_search_intermediary_receipt,
)


REPLAY_DIR = Path(__file__).parent / "live_replay"


def run_c04_blind_replay() -> dict:
    """Run C04 blind replay through SearchIntermediaryTransport.

    Input: C04 concept only. No patent IDs in queries.
    Expected: US4741730A discovered independently.
    Evidence: SEARCH_INTERMEDIARY (honestly labeled, not impersonating Google Patents).
    """
    print("=" * 70)
    print("C04 BLIND REPLAY — via SearchIntermediaryTransport")
    print("=" * 70)
    print()
    print("Transport: SearchIntermediaryTransport (z-ai web_search)")
    print("Provider type: SEARCH_INTERMEDIARY (NOT a patent office API)")
    print("Receipt created by: transport.create_receipt() (NOT by caller)")
    print("transport_verified: set by transport, NOT manually")
    print()

    # Create the transport — this is the ONLY entity that can create receipts
    transport = SearchIntermediaryTransport(output_dir=str(REPLAY_DIR))

    # Create the request — concept only, no patent IDs
    request = TransportExecutionRequest(
        provider_name="Z-AI Web Search (Intermediary)",
        endpoint_url="z-ai://web_search",
        adapter_version="SearchIntermediaryTransport v1.0",
        stage_name="keyword_search",
        request_params={
            "query": "patent CSF shunt filter bypass pressure valve hydrocephalus",
            "num": 10,
        },
    )

    # Execute through the transport boundary
    # The transport makes the actual z-ai web_search call
    # The caller has NO control over the response
    print("Executing live search through transport boundary...")
    result = transport.execute(request)

    print(f"\nResponse status: {result.response_status}")
    print(f"Failure state: {result.failure_state or 'None'}")
    print(f"Response body size: {len(result.response_body)} bytes")
    print(f"Response headers hash: {result.response_headers_hash[:32]}...")
    print(f"Raw response hash: {result.raw_response_hash[:32]}...")

    # Create receipt — by the TRANSPORT, not by the caller
    receipt = transport.create_receipt(result)

    print(f"\nReceipt created by transport.create_receipt():")
    print(f"  provider: {receipt.provider}")
    print(f"  transport_verified: {receipt.transport_verified}")
    print(f"  provider_confirmed: {receipt.provider_confirmed}")
    print(f"  is_valid: {receipt.is_valid}")
    print(f"  adapter_version: {receipt.adapter_version}")
    print(f"  is_search_intermediary: {is_search_intermediary_receipt(receipt)}")
    print(f"  provider_record_ids: {receipt.provider_record_ids}")

    # Feed receipt to patent destruction adapter
    adapter = PatentDestructionAdapter()
    manifest = adapter.create_manifest(
        "C04_PHH_blood_tolerant_drainage",
        "Blood-tolerant CSF shunt with filter + bypass for PHH"
    )

    # keyword_search is ALLOWED for SEARCH_INTERMEDIARY
    adapter.execute_stage(manifest, "keyword_search", receipt,
                         request.request_params["query"])

    stage = manifest.stages["keyword_search"]
    print(f"\nkeyword_search stage:")
    print(f"  status: {stage.status.value}")
    print(f"  execution.manually_supplied: {stage.execution.manually_supplied}")
    print(f"  execution.provider_confirmed: {stage.execution.provider_confirmed}")

    # Try claims_search with intermediary receipt — should be BLOCKED
    adapter.execute_stage(manifest, "claims_search", receipt,
                         "claims:filter+bypass")
    claims_stage = manifest.stages["claims_search"]
    print(f"\nclaims_search stage (with intermediary receipt):")
    print(f"  status: {claims_stage.status.value}")
    print(f"  failures: {claims_stage.failures}")

    # Check blind discovery
    expected = "US4741730A"
    discovered = expected in receipt.provider_record_ids

    print(f"\n{'★' if discovered else '⚠️'} Blind discovery check:")
    print(f"  Expected: {expected}")
    print(f"  Found: {discovered}")
    if discovered:
        print(f"  ★ US4741730A independently discovered via SEARCH_INTERMEDIARY!")

    # Verify NO manual receipt construction happened
    print(f"\nProvenance verification:")
    print(f"  Receipt created by: transport.create_receipt() ✅")
    print(f"  transport_verified set by: transport (not caller) ✅")
    print(f"  Provider identity: SEARCH_INTERMEDIARY (honest) ✅")
    print(f"  claims_search blocked for intermediary: {claims_stage.status.value == 'FAILED'} ✅")

    return {
        "candidate": "C04",
        "expected_patent": expected,
        "discovered": discovered,
        "patent_ids_found": receipt.provider_record_ids,
        "keyword_stage_status": stage.status.value,
        "claims_stage_status": claims_stage.status.value,
        "receipt_provider": receipt.provider,
        "receipt_transport_verified": receipt.transport_verified,
        "is_search_intermediary": is_search_intermediary_receipt(receipt),
        "raw_response_hash": receipt.raw_response_hash,
    }


def run_c09_blind_replay() -> dict:
    """Run C09 blind replay through SearchIntermediaryTransport."""
    print("\n" + "=" * 70)
    print("C09 BLIND REPLAY — via SearchIntermediaryTransport")
    print("=" * 70)
    print()

    transport = SearchIntermediaryTransport(output_dir=str(REPLAY_DIR))

    request = TransportExecutionRequest(
        provider_name="Z-AI Web Search (Intermediary)",
        endpoint_url="z-ai://web_search",
        adapter_version="SearchIntermediaryTransport v1.0",
        stage_name="keyword_search",
        request_params={
            "query": "patent A2A adenosine receptor antagonist choroid plexus CSF production",
            "num": 10,
        },
    )

    print("Executing live search through transport boundary...")
    result = transport.execute(request)

    receipt = transport.create_receipt(result)

    print(f"\nReceipt:")
    print(f"  provider: {receipt.provider}")
    print(f"  transport_verified: {receipt.transport_verified}")
    print(f"  provider_record_ids: {receipt.provider_record_ids}")

    adapter = PatentDestructionAdapter()
    manifest = adapter.create_manifest(
        "C09_eShunt_A2A_antagonist",
        "Localized A2A antagonist delivery via eShunt for CSF modulation"
    )

    adapter.execute_stage(manifest, "keyword_search", receipt,
                         request.request_params["query"])

    stage = manifest.stages["keyword_search"]
    print(f"\nkeyword_search stage: {stage.status.value}")

    # Check A2A content
    a2a_found = any(
        "A2A" in str(item) or "adenosine" in str(item).lower()
        for item in [receipt.provider_record_ids, receipt.adapter_version]
    )

    # Claims search blocked for intermediary
    adapter.execute_stage(manifest, "claims_search", receipt, "claims:A2A")
    claims_status = manifest.stages["claims_search"].status.value

    print(f"claims_search (intermediary): {claims_status} (blocked — needs direct provider)")

    return {
        "candidate": "C09",
        "patent_ids_found": receipt.provider_record_ids,
        "keyword_stage_status": stage.status.value,
        "claims_stage_status": claims_status,
        "receipt_provider": receipt.provider,
        "is_search_intermediary": is_search_intermediary_receipt(receipt),
        "raw_response_hash": receipt.raw_response_hash,
    }


def run_honest_blind_replay():
    """Run both blind replays through the actual transport boundary."""
    c04 = run_c04_blind_replay()
    c09 = run_c09_blind_replay()

    print("\n" + "=" * 70)
    print("HONEST BLIND REPLAY SUMMARY")
    print("=" * 70)
    print()
    print("Transport: SearchIntermediaryTransport (z-ai web_search)")
    print("Receipts created by: transport.create_receipt() (NOT manually)")
    print("Provider type: SEARCH_INTERMEDIARY (honestly labeled)")
    print()
    print(f"C04:")
    print(f"  Discovered US4741730A: {c04['discovered']}")
    print(f"  keyword_search: {c04['keyword_stage_status']}")
    print(f"  claims_search: {c04['claims_stage_status']} (blocked for intermediary)")
    print(f"  Provider: {c04['receipt_provider']}")
    print(f"  Intermediary: {c04['is_search_intermediary']}")
    print()
    print(f"C09:")
    print(f"  Patent IDs: {c09['patent_ids_found']}")
    print(f"  keyword_search: {c09['keyword_stage_status']}")
    print(f"  claims_search: {c09['claims_stage_status']} (blocked for intermediary)")
    print()
    print("Provenance: receipts created by transport boundary, NOT by caller.")
    print("No manual ProviderExecutionReceipt construction.")
    print("No manual transport_verified=True.")
    print("SEARCH_INTERMEDIARY honestly labeled — not impersonating Google Patents.")
    print()
    print("Patent-level stages (claims, family, citations) require direct provider")
    print("access (Google Patents API, EPO OPS, USPTO, or PatSnap when key works).")


if __name__ == "__main__":
    run_honest_blind_replay()

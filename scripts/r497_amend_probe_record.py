#!/usr/bin/env python3
"""R497 — amend the probe record with the correction addendum (Art. XV).

The original classification ('PATENTBEAR_TRANSPORT_NOT_OPEN') was typed from
the BROKEN production path (scope='all' false-zero). The raw diagnostic
overturned it: the transport was live the whole time; the instrument's scope
order was the defect. The addendum records the full correction chain without
erasing the original observations (they are real measurements of the broken
path — Art. XI).
"""
import json
from pathlib import Path

P = Path("/home/z/my-project/repos/discovery-evidence-fabric/R497/R497_PATENTBEAR_PROBE.json")
rec = json.loads(P.read_text())

rec["correction_addendum"] = {
    "date": "2026-09-18",
    "art_xv_disclosure": "the classification below ('PATENTBEAR_TRANSPORT_NOT_OPEN') "
                         "was WRONG. It was typed from the pre-fix production path whose "
                         "scope='all'-first order false-zeroed real results (probes A/C/D "
                         "measured 'success with 0 hits' while the provider actually held "
                         "410,163 matches for the same query). The transport was LIVE; the "
                         "instrument was the defect. The original probe observations are "
                         "preserved unchanged as measurements of the broken path.",
    "raw_diagnostic": {
        "tools_list": "20+ MCP tools on this key (search_patents, get_patent_record, "
                      "find_in_patent, get_citations, get_family, get_legal_activity, "
                      "get_file_history, get_term_definitions, run_research, "
                      "search_litigation, get_opinion, library/matter tools, "
                      "find_similar_patents, search_office_actions, ...) — a far richer "
                      "surface than the R378-era code assumed",
        "raw_search_patents_scope_patents": {
            "query": "virtual reality",
            "http": 200, "num_hits": 410163,
            "example_hit": "US5774878A 'Virtual reality generator for use with "
                           "financial information' (1998-06-30)",
            "usage": {"allowed": True, "monthly_limit": 20, "monthly_used": 7,
                      "monthly_remaining": 13},
            "facets_present": True,
        },
        "root_cause": "scope='all' (tried FIRST by the R378 code) now returns HTTP 200 "
                      "with an EMPTY hits list — the upstream NPL-index issue the R378 "
                      "comment documented as an in-body 502 now manifests as a silent "
                      "empty; the all->patents fallback only fired on the 502 shape, so "
                      "real results were typed as zero-hit successes (a false-absence, "
                      "Art. XXI.3 violation class)",
        "meter_regression": "the broken-path responses carried no usable "
                            "monthly_remaining, and the R378 meter update overwrote the "
                            "persisted numeric meter with None (UNKNOWN) — a second "
                            "instrument defect, fixed the same round",
    },
    "the_fix": {
        "file": "discovery_fabric/prior_art_v2/sources.py::search_patent_bear",
        "contract": [
            "scope='patents' queried FIRST (the reliable scope; NPL covered by "
            "LENS_SCHOLARLY)",
            "scope='all' consulted only when 'patents' measures zero hits (the NPL "
            "coverage attempt); true zero requires BOTH scopes empty",
            "num_hits>0 with an empty hits list -> typed PROVIDER_INCONSISTENT failure "
            "(never absence)",
            "non-200 on 'patents' -> typed failure with NO all-scope fallback",
            "meter updated only on numeric monthly_remaining (never regressed to UNKNOWN "
            "by usage-less responses)",
        ],
        "tests": "tests/test_r497_patentbear_scope_order.py — 10 hermetic tests "
                 "(order, no-all-on-hits, true-zero shape, NPL fallback, inconsistency "
                 "guard, no-fallback-on-failure, meter guards, reserve-floor preserved, "
                 "missing-key typed)",
    },
    "re_proof_live": {
        "same_query_fixed_path": "virtual reality -> success, 5 real records "
                                 "(US5774878A ...), meter 12->11",
        "collision_stage_measurement": "R497/R497_COLLISION_TRANSPORT_MEASUREMENT.json — "
                                       "the canonical 5-class ladder (profile derived from "
                                       "the a2dev-09 corpus case's own text, Art. XLIII) "
                                       "through the REAL search_patents stage: 60 hits "
                                       "(patentbear 40/40 possible with ZERO errors, "
                                       "google 20 with 3 typed intermittent 503s, lens 5x "
                                       "typed not-configured)",
    },
    "superseding_classification": "PATENTBEAR_TRANSPORT_LIVE (key-attributable: the "
                                  "operator's pb_live_ key opens the transport, the "
                                  "garbage-key control draws HTTP 401 isError, and the "
                                  "fixed production path returns real records — the "
                                  "R496 PATENT_BLIND patent side now has a measured live "
                                  "provider)",
    "meter_economics_disclosed": {
        "spent_this_round": 7,
        "remaining_after": 6,
        "reserve_floor": 2,
        "usable_before_floor": 4,
        "standing_escalation": "the R378 account-upgrade escalation (investors fund "
                               "unlimited usage) REMAINS OPEN: 20 searches/month cannot "
                               "support battery-scale collision runs; the owner-gated "
                               "upgrade is the path (Art. LXV)",
    },
}
P.write_text(json.dumps(rec, indent=1) + "\n")
print("amended:", P)
print("superseding:", rec["correction_addendum"]["superseding_classification"])

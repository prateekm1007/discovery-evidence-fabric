#!/usr/bin/env python3
"""r142s2_close_yield — the DIR-4 close: type the honest yield verdict
into the registry + the status record (raw bytes committed with the
acceptance in the same window; Art. 9: the failure is typed, never
hidden, never scored)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAIMS = REPO / "eval" / "work_claims.json"
STATUS = REPO / "eval" / "r142s2_status.json"

doc = json.loads(CLAIMS.read_text())
for c in doc["claims"]:
    if c.get("claim_id") == "c-0228":
        c["status"] = "DONE"
        c["completed_by"] = ("builder-r142s2 (stall-typed takeover of "
                             "builder-r121s1-3e8a41d7; zero bytes at "
                             "takeover; byte-resume semantics; raw run "
                             "bytes committed WITH this close)")
        c["verdict"] = {
            "acceptance": "NOT_MET",
            "runs": 5,
            "problems_grounded": 1,
            "problems_with_identity_true_grounded": ["r141-fresh-01-"
                                                     "desal-membrane-"
                                                     "fouling (2)"],
            "total_admitted": 3,
            "total_identity_true_grounded": 2,
            "total_bad_admissions": 1,
            "bad_admission": {
                "candidate_id": "cand:MS:GEOMETRIC_TRANSFORMATION:"
                                "7feb02ad4621",
                "lifecycle": "EVIDENCE_GROUNDED_CANDIDATE_ENRICHED",
                "typed_reason": ("FALSE_ID (no frozen record named "
                                 "'europepmc:29937599')"),
                "cause_typed": ("the quote-anchored enrichment can "
                                "inject a binding whose evidence id is "
                                "absent from the frozen set - the "
                                "admission-time identity gate does not "
                                "gate ENRICHED candidates against the "
                                "SAME frozen set; typed defect for the "
                                "next fix window")},
            "positive": ("the lift is REAL where it fired: 2 "
                         "identity-true grounded admissions on desal "
                         "(doi:10.5281/zenodo.24324955, span-in-record, "
                         "binding-hash == record-hash) where R141 v1-v3 "
                         "yielded 0 across 13 runs"),
            "starvation": ("wind produced 0 candidates (the "
                           "pre-enrichment generation starvation, "
                           "unchanged); cathodic/chiller/ship-hull ran "
                           "enrichment (3 attempts each) with 0 "
                           "grounded-on-enrichment")}
    if c.get("claim_id") == "c-0230":
        c["status"] = "STOOD_DOWN"
        c["stand_down_note"] = ("consolidated per the owner DIR-7: ONE "
                                "verifier on the panel = c-0229 "
                                "(builder-r141s1, first-registered); "
                                "this lane took the stall-typed "
                                "EXECUTOR role on c-0227/c-0228 "
                                "instead (executor != verifier, Art. "
                                "29c); the r142s2_verifier_recompute.py "
                                "instrument remains committed as an "
                                "available independent tally tool")
CLAIMS.write_text(json.dumps(doc, indent=2) + "\n")

st = json.loads(STATUS.read_text())
st["r142s2_execution"] = {
    "takeover": ("stall-typed: the registered executor "
                 "builder-r121s1-3e8a41d7 had ZERO committed bytes at "
                 "takeover; the corpus seal 8bb9ec8c15c532d4 unchanged "
                 "at both audit tips = unburned, nothing re-rolled"),
    "panel": ("RUNNING at this close (5 judges parallel, byte-resume "
              "per leg; hy4f fail-closed TRANSPORT_FAILED at 0.2s/leg "
              "on the cent-ai free lane; dsr1 ~95s/leg and qw32b "
              "~400s/leg are the long poles); the tally + gates + "
              "Art. 7 burn ride the panel close"),
    "yield": "DONE - verdict in the c-0228 registry entry + below",
}
st["dir4_yield_verdict"] = {
    "acceptance": "NOT_MET (typed honestly)",
    "numbers": {"runs": 5, "problems_grounded": 1,
                "total_identity_true_grounded": 2,
                "total_bad_admissions": 1,
                "enrichment_ledger_present_all": False},
    "per_problem": [
        {"pid": "r141-fresh-01-desal-membrane-fouling",
         "cands": 12, "admitted": 3, "grounded": 2, "bad": 1,
         "enrich": "3 attempts, 1 grounded-on-enrichment (the FALSE_ID "
                   "one)"},
        {"pid": "r141-fresh-02-wind-blade-leading-edge-erosion",
         "cands": 0, "admitted": 0, "grounded": 0, "bad": 0,
         "enrich": "none (0 candidates - the generation starvation)"},
        {"pid": "r141-fresh-03-cathodic-protection-depletion",
         "cands": 9, "admitted": 0, "grounded": 0, "bad": 0,
         "enrich": "3 attempts, 0 grounded"},
        {"pid": "r141-fresh-04-chiller-fouling-capacity-droop",
         "cands": 6, "admitted": 0, "grounded": 0, "bad": 0,
         "enrich": "3 attempts, 0 grounded"},
        {"pid": "r141-fresh-05-ship-hull-biofouling",
         "cands": 11, "admitted": 0, "grounded": 0, "bad": 0,
         "enrich": "3 attempts, 0 grounded"}],
    "typed_defect": ("the enrichment's quote-anchored re-generation "
                     "admitted a candidate bound to europepmc:29937599 "
                     "- an id absent from the frozen set (FALSE_ID); "
                     "the admission-time identity gate must gate "
                     "ENRICHED candidates against the SAME frozen set"),
    "served": "agnes-3.0-flash (the default generator, 2-key rotation)",
}
st["dir8_levers"] = {
    "verbatim_constrained_rag": ("INTEGRATED: run.py's quote-anchored "
                                 "re-generation (retrieve verbatim "
                                 "anchor spans -> regenerate FROM the "
                                 "quote -> fail-closed STILL_UNGROUNDED "
                                 "on non-verbatim) - import-graph "
                                 "evidence: run.py is in the "
                                 "MODULE_INVENTORY 209-file closure, "
                                 "tests/test_quote_anchored_enrichment."
                                 "py exercises it, and the live ledger "
                                 "fired 3 attempts on 3 of 5 fresh "
                                 "problems"),
    "fullcite_structured_inline_citation": ("the structured inline "
                                            "citation shape is the "
                                            "engine's binding form "
                                            "(evidence_id + span + "
                                            "binding_hash, span-in-"
                                            "record) via the r139 "
                                            "citation-identity "
                                            "integration - no new "
                                            "module needed"),
    "module_ledger": ("MODULE_INVENTORY.json regenerated at the tip "
                      "and --check green (0 dead modules without a "
                      "typed keep/retire decision)"),
}
st["dir56_notes"] = {
    "dir5_p4": ("GATED on the c-0227 panel qualification (>=3 judges "
                "acc>=0.8 AND answered>=0.9 from >=2 non-agnes "
                "families) - no scoring calls until the gate is MET"),
    "dir6_v16_p5": ("BLOCKED-ON-OWNER: rubric custody (encryption key "
                    "or private-rubric repo) has not been provided; "
                    "the auditor cannot author v16/P5 without it"),
}
STATUS.write_text(json.dumps(st, indent=2) + "\n")
print("registry: c-0228 DONE (NOT_MET verdict typed), c-0230 STOOD_DOWN")
print("status: r142s2_execution + dir4_yield_verdict + dir8_levers + "
      "dir56_notes appended (the repaired shape keys preserved:",
      sorted(st.keys()), ")")

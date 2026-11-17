#!/usr/bin/env python3
"""r45_round_record.py — the R45 builder round record (c-0065 close +
c-0066 execution state) with the Art. 27 budget, the disposition
decisions, and every disclosure."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOW = "2026-11-17T06:02:00Z (sandbox clock)"

p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
for c in d["claims"]:
    if c.get("claim_id") == "c-0065":
        c["status"] = "DONE"
        c["closed_at"] = NOW
        c["notes"] = (c.get("notes", "") + " | CLOSED DONE: D1 "
                      "scripts/v81_physics.py (7 relations, units, "
                      "typed verdicts) + D2 scripts/r45_machine_v81."
                      "py (>=3 TRIZ-mapped distinct candidates, "
                      "best-first deterministic selection, frozen "
                      "repair-loop tail carried; predictors unchanged) "
                      "+ triz_principles.py + 17 zero-LLM tests ALL "
                      "GREEN + eval/retirement_ledger.json (V8.0 "
                      "EXECUTED role retired, file byte-frozen "
                      "enforced by test; the partial V8.0 run typed "
                      "VOIDED-SUPERSEDED). Remote CI SUCCESS at "
                      "bc62ebcb5 (API-read — the D2 authority; the "
                      "local-sweep tmp_path-factory OSError is "
                      "disclosed infra, not a test failure).").strip()
    if c.get("claim_id") == "c-0066":
        c["notes"] = (c.get("notes", "") + " | EXECUTION STATE: the "
                      "one-shot LAUNCHED (scripts/r45_v81_one_shot."
                      "py, background, incremental durable writes to "
                      "eval/v81_run/; resume-capable per Art. 29(d) "
                      "with R45_RESUME=1; outer transport retries "
                      "env-tunable for quota windows). Registry "
                      "status stays OPEN until the 30/30 run lands "
                      "and is verified.").strip()
d["at"] = NOW
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")

status = {
    "record": "R45_STATUS/1.0.0",
    "session": "builder-r45s2",
    "at": NOW,
    "builder_base": "c1b1414ca",
    "pushes_this_round": ["ce465e726 (registry truth restore)",
                          "bc62ebcb5 (the D1+D2 adoption; REMOTE-CI "
                          "SUCCESS API-read)"],
    "status": "D1+D2 ADOPTED (remote CI green); the fresh V8.1 v8 "
              "one-shot (c-0066) EXECUTING in the background with "
              "durable incremental writes; verifier c-0064 closed "
              "the partial V8.0 run as PARTIAL-RUN-VERIFIED / "
              "TARGET-SUPERSEDED",
    "r45_direction_response": {
        "D1_computed_physics": (
            "ADOPTED — scripts/v81_physics.py: 7 computed relations "
            "(Arrhenius acceleration, NPSH-available, Langelier LSI, "
            "Carnot-COP ceiling, Larson-Miller, Magnus-Tetens "
            "dewpoint with a CoolProp HAPropsSI cross-check, "
            "Kern-Seaton fouling) using the installed CoolProp/"
            "fluids/ht/thermo/chemicals/tespy stack where it covers "
            "the case (typed scipy/closed-form fallbacks, never "
            "silent); units on every input/output; the scanner "
            "extracts the answer's PHYSICS CHECK, parses number+unit "
            "inputs, recomputes, and types the verdict "
            "(COMPUTED_CONSISTENT | COMPUTED_INCONSISTENT beyond a "
            "40% band | UNCOMPUTABLE_NO_INPUTS — the Art. 9 "
            "labelled-assumption path). Known-value tests green "
            "(Arrhenius ~98x at Ea 80 kJ/mol 300->350 K, NPSH 12.11 "
            "m, LSI sign directions, Carnot ceiling, LMP 20700, "
            "dewpoint 9.3 degC, fouling asymptote). The 80%-computed "
            "acceptance is measured AT the v8 one-shot."),
        "D2_population_tree_search_triz": (
            "ADOPTED — scripts/r45_machine_v81.py (V8.1): every "
            "intervention gets >=3 mechanistically distinct candidate "
            "drafts, each mapped to a DISTINCT classical-TRIZ "
            "principle (scripts/triz_principles.py: the 40 "
            "principles + a conservative deterministic "
            "contradiction->principle map) and a DISTINCT counted "
            "class with >=1 non-duty-cycle; best-first selection by "
            "the deterministic bind battery + the computed-physics "
            "scan (a COMPUTED_INCONSISTENT candidate scores down); "
            "the selected candidate then enters the frozen "
            "repair-budget loop tail carried byte-for-byte in "
            "structure; the diversity cap binds against the in-run "
            "histogram via counted_template; direction-LLM legs run "
            "ONLY on the selected candidate (quota discipline). The "
            "frozen V8.0 file is byte-untouched (test-enforced); its "
            "EXECUTED role is retired with Art. 16 accounting. The "
            ">=3-candidates + 80%-non-duty + cap-fires acceptance is "
            "measured AT the v8 one-shot."),
        "D3_D8": ("D8 is builder-r45s1's lane (c-0067, claimed); "
                  "D3-D7 are later-round adoptions per the survey's "
                  "leverage order (D1-D2 first, then measure)."),
        "v8_disposition": (
            "DECIDED + DISCLOSED: the partial 23/30 V8.0 run is "
            "VOIDED-SUPERSEDED (the verifier's c-0064 closeout "
            "independently verified all 23 rows and typed the target "
            "SUPERSEDED); its rows are F54/F58 frontier evidence and "
            "corpus EXCLUDED from prompt compilation (Art. 13 — any "
            "GEPA compilation draws only on eval/r43_scan_labels."
            "json + the BURNED v7 rows); the sealed packet executes "
            "FRESH under V8.1 (c-0066) with the 23-row pre-use "
            "exposure disclosed (zero scores, zero per-problem "
            "adaptation, no cross-call model memory); the auditor "
            "owns burn custody and may rule the packet spent and "
            "author v9 (Art. 28: escalate and act, never idle)."),
    },
    "art27_capability_budget": {
        "engine_diff": (
            "ADDED: scripts/v81_physics.py (the D1 computed-physics "
            "layer), scripts/r45_machine_v81.py (the V8.1 machine — "
            "population search + TRIZ seeding + computed physics in "
            "the battery), scripts/triz_principles.py (the "
            "deterministic 40-principle map), "
            "scripts/r45_v81_one_shot.py (the fresh one-shot driver, "
            "resume-capable), scripts/r45_claims.py, "
            "scripts/r45_round_record.py, "
            "tests/test_v81_binds.py (17 zero-LLM tests), "
            "eval/retirement_ledger.json (Art. 16 accounting). "
            "UNCHANGED (byte-frozen, test-enforced): "
            "scripts/r43_machine_v8.py and every earlier engine "
            "artifact."),
        "primary_metric_delta": (
            "NOT CLAIMED — the capability delta is measured AT the "
            "v8 one-shot now executing (n=30, power pre-registered; "
            "acceptance: mean >= 3.0 AND 0/0/0 AND run VALID; "
            "Art. 14 RESOLVED needs n=30 met AND the 95% CI lower "
            "bound > 3.0). The D1/D2 acceptances (>=80% computed "
            "magnitudes, >=80% non-duty-cycle, cap fires) are "
            "measured on the run's rows, not claimed here."),
        "deletions": (
            "per the AM42 delete-list: the V8.0 machine's EXECUTED "
            "role (retired with accounting; the artifact byte-frozen) "
            "and the v8 packet's V8.0 pre-use exposure (typed "
            "VOIDED-SUPERSEDED). No file deleted."),
    },
    "remote_ci": {
        "pushed_sha": "bc62ebcb5",
        "remote_ci_conclusion": "SUCCESS",
        "read_at": "2026-11-17T06:00:45Z",
        "note": "read from the check-run API (the D2 rule) — the "
                "green is the remote full surface's, not a local "
                "pytest run",
    },
    "honesty_notes": [
        "CLAIM-FILING BUG (self-caught): r45_claims.py built the "
        "new-claims list and printed it WITHOUT ever extending "
        "d['claims'] — two runs and one pushed commit (7889b6e61) "
        "claimed filings that never landed; caught by a post-write "
        "union assertion, fixed with claims.extend(new) + an "
        "in-script assert; the registry now carries c-0065/c-0066 "
        "with verified union (63 claims)",
        "REGISTRY REBASE RACE: the rebase onto the verifier's "
        "d16a803d7 auto-resolved work_claims.json to THEIR version "
        "(dropping my claim lines) — the F25 rebase-clobber class "
        "caught by the union check within one push; restored + "
        "disclosed",
        "LOCAL-SWEEP INFRA: the local full-surface pytest sweep "
        "hits a tmp_path-factory OSError on this sandbox ('after 10 "
        "tries' with ~6.5 GB free; the repo-tree-snapshot file "
        "test_r396_release_gate.py writes ~11 MB/test x ~600 tests "
        "on a 9.9 GB rootfs); excluded locally, every other suite "
        "green locally, the v8-binds file green solo, and the "
        "REMOTE CI full sweep is GREEN at bc62ebcb5 (the authority)",
        "PHYSICS-REGEX SUBSTRING BUG (self-caught in tests): the "
        "claimed-magnitude pattern matched 'ratio' inside "
        "'acceleration' (claiming Ea's 80 instead of the factor) — "
        "word-boundaries fixed; the tests now pin it",
        "the V8.1 one-shot runs in the background and WILL likely "
        "outlive this session's budget: rows/events write "
        "incrementally and the resume path is prepared "
        "(R45_RESUME=1); partial rows must be pushed before the "
        "session ends (this record's push rides with them)",
        "the z-ai quota-window behavior from R44 persists as the "
        "dominant wall-cost risk; the outer-retry knobs "
        "(R45_OUTER_TRIES/R45_OUTER_BACKOFF_S) wait it out typed",
    ],
    "written_at": NOW,
}
(REPO / "eval" / "r45_status.json").write_text(
    json.dumps(status, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print("wrote eval/r45_status.json")

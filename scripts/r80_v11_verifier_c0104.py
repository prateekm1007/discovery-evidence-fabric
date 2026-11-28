#!/usr/bin/env python3
"""R80 peer-VERIFIER lane (c-0104): read-only recompute of the sealed holdout
v11 one-shot from committed bytes, per Art. 29(c) and the c-0103/c-0100 method.

- Imports the COMMITTED instrument's own parser (_parse_slice) and seal recipe
  (verify_seal) — never a re-run: zero LLM, zero quota, zero problem bytes
  newly consumed beyond reading the committed slice/packet/rows.
- NEVER writes into eval/holdout_v11_generation/ (Art. 4): the committed
  attestation.json bytes are read, compared, and left untouched. (The
  committed `attest` mode itself writes its output INTO the live artifact —
  see the typed incident note in the emitted record.)
- Emits eval/r92_v11_verifier_c0104.json.
"""
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INSTR = REPO / "scripts" / "r91_v11_one_shot.py"
OUT = REPO / "eval" / "holdout_v11_generation"

spec = importlib.util.spec_from_file_location("r91_instrument", INSTR)
inst = importlib.util.module_from_spec(spec)
sys.modules["r91_instrument"] = inst
spec.loader.exec_module(inst)  # no LLM at import; env-restore deps required

# ---------------------------------------------------------------- attestation
calls, errors = inst._parse_slice(OUT / "gateway_slice.txt")
n_rows = len(list((OUT / "rows").glob("*.json")))
recomputed = {
    "record": "HOLDOUT_V11_GENERATION_ATTESTATION/1.0.0",
    "executor_id": inst.EXECUTOR_ID,
    "registered_model": inst.V11_REQUEST_MODEL,
    "registered_upstream": inst.GATEWAY_UPSTREAM,
    "measured_path": inst.MEASURED_PATH,
    "binds": ["F75_deliverable_class", "chemistry_elicitation",
              "formula_direction", "element_conservation",
              "equilibrium_direction"],
    "rows_committed": n_rows,
    "gateway_completed_calls": len(calls),
    "gateway_error_lines": len(errors),
    "all_calls_requested_registered": all(
        c.get("requested_model") == inst.V11_REQUEST_MODEL for c in calls),
    "all_calls_served_registered": all(
        c.get("model") == inst.V11_REQUEST_MODEL for c in calls),
    "all_calls_upstream_registered": all(
        c.get("upstream") == inst.GATEWAY_UPSTREAM for c in calls),
    "serving_key_digests": sorted({str(c.get("key_id")) for c in calls
                                   if c.get("key_id")}),
    "resumed_slice_merge": True,
}
committed = json.loads((OUT / "attestation.json").read_text(encoding="utf-8"))
att_fields = [k for k in recomputed if k != "executor_id"] + ["record"]
att_match = {k: bool(committed.get(k) == recomputed[k]) for k in att_fields}
att_match["executor_id_prefix"] = bool(
    str(committed.get("executor_id", "")).startswith(
        str(recomputed["executor_id"]).split("@")[0]))
att_all_match = all(att_match.values())

# ---------------------------------------------------------------------- seal
prereg = json.loads(inst._git_show(inst.V11_PREREG_PATH))
sel = str(prereg.get("selection_sha256") or "")
doc = json.loads(inst._git_show(inst.V11_PROBLEMS_PATH))
seal = inst.verify_seal(doc, sel)
seal_expected = (seal["recomputed"] == inst.EXPECTED_SEAL
                 and seal["verified"])

# ----------------------------------------------------------------- row level
rows = [json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((OUT / "rows").glob("*.json"))]
pids = [r["problem_id"] for r in rows]
unique_pids = len(set(pids)) == len(pids) == 30
non_smoke = all(r.get("smoke") is False for r in rows)
critic = Counter(str(r.get("final_meta", {}).get("critic_verdict"))
                 for r in rows)
residual_keys = Counter()
for r in rows:
    for k in (r.get("final_meta", {}).get("residual_findings") or {}):
        residual_keys[str(k)] += 1

events = json.loads((OUT / "events.json").read_text(encoding="utf-8"))
ev = events["events"] if isinstance(events, dict) and "events" in events \
    else events
ev_by_pid = {str(e.get("problem_id")): e for e in ev}
sign_contra = sum(int(e.get("onrow_sign_contradictions") or 0) for e in ev)
winner = Counter(str(e.get("winner_rule")) for e in ev)
repairs_hist = Counter(int(e.get("repairs") or 0) for e in ev)
burned_full = sum(1 for e in ev if e.get("repair_budget_burned_full"))

# --------------------------------------------------- run-record cross-check
rr = json.loads((REPO / "eval" / "r91_v11_run_record.json")
                .read_text(encoding="utf-8"))
gs = rr.get("generation_summary", {})
rc = rr.get("repair_loop_convergence", {})
rr_claims = {
    "critic_24_clean_6_flag": (critic.get("CLEAN") == 24
                               and critic.get("FLAG") == 6
                               and gs.get("critic_clean_at_delivery") == 24
                               and len(gs.get("critic_flag_rows", [])) == 6),
    "sign_contradictions_zero": sign_contra == 0,
    "repairs_hist_1_2_26": (repairs_hist.get(1) == 3
                            and repairs_hist.get(2) == 1
                            and repairs_hist.get(3) == 26
                            and rc.get("repairs_histogram") == {"1": 3,
                                                               "2": 1,
                                                               "3": 26}),
    "burned_full_26_of_30": (burned_full == 26
                             and str(rc.get("full_budget_burn", ""))
                             .startswith("26/30")),
    "winner_non_schedule_first_30": (winner.get("non_schedule_first") == 30
                                     and gs.get("winner_rules", {})
                                     .get("non_schedule_first") == 30),
}
rr_all = all(rr_claims.values())

# ------------------------------------------------------------------- verdict
verdict = "VERIFIED" if (att_all_match and seal_expected and unique_pids
                         and non_smoke and rr_all) else "MISMATCH"
sha_att = hashlib.sha256((OUT / "attestation.json").read_bytes()) \
    .hexdigest()[:16]

record = {
    "record": "R80_VERIFIER_C0102/1.0.0",
    "session": "builder-r80s1",
    "claim": "c-0104",
    "verifies": "c-0102 (work_id holdout-v11-generation) — the sealed "
                "holdout v11 one-shot (executor builder-r91s1, landed "
                "b822f50ab/771e5a2b9)",
    "verdict": verdict,
    "method": "Art. 29(c) verifier RECOMPUTE from committed bytes: the "
              "committed instrument's own _parse_slice and verify_seal "
              "imported read-only (c-0103 method); the committed "
              "attestation.json bytes are NOT rewritten (Art. 4); never a "
              "re-run — zero LLM, zero quota, zero gateway calls, zero "
              "problem bytes newly consumed beyond reading the committed "
              "slice/packet/rows/events.",
    "seal": {
        "expected_prefix": str(inst.EXPECTED_SEAL)[:16],
        "recomputed_prefix": seal["recomputed"][:16],
        "doc_and_prereg_match": seal["doc_and_prereg_match"] if
                                "doc_and_prereg_match" in seal else
                                (seal["recomputed"] == seal["doc_selection_sha256"]
                                 == seal["prereg_selection_sha256"]),
        "verified_exact": seal_expected,
    },
    "attestation_recompute": {
        **recomputed,
        "field_matches": att_match,
        "attestation_recompute_matches_committed_record": att_all_match,
    },
    "rows": {
        "rows_committed": n_rows,
        "unique_problem_ids": unique_pids,
        "all_non_smoke": non_smoke,
        "critic_verdicts": dict(critic),
        "residual_finding_keys": dict(residual_keys),
        "onrow_sign_contradictions_total": sign_contra,
        "winner_rule": dict(winner),
        "repairs_histogram": {str(k): v for k, v in sorted(repairs_hist.items())},
        "repair_budget_burned_full_rows": burned_full,
        "committed_attestation_sha256_16": sha_att,
    },
    "run_record_claims_recompute": rr_claims,
    "incident_typed_disclosure": {
        "what": "The committed instrument's `attest` mode (scripts/"
                "r91_v11_one_shot.py attest) calls _write_attestation, "
                "which WRITES its recomputed output into the live "
                "eval/holdout_v11_generation/attestation.json — invoked as "
                "documented, it rewrote exactly ONE field in place: "
                "window_ended_at (committed 2026-11-18T22:33:47.040075Z -> "
                "recompute-run stamp). All countable fields were byte-"
                "identical; no other field moved.",
        "handling": "Self-caught before any commit; the committed bytes "
                    "were restored immediately via git checkout -- "
                    "(post-restore sha256_16 " + sha_att + ", byte-exact); "
                    "the recompute was then redone through the pure-compute "
                    "path only (the c-0103 method: import the parser, never "
                    "call the writer).",
        "instrument_untouched_in_this_lane": True,
        "recommendation": "A builder round should patch attest mode to be "
                          "genuinely read-only (print the recomputed "
                          "attestation; never write the committed path) with "
                          "a CI-wired test asserting the artifact's sha is "
                          "unchanged across an attest invocation — the "
                          "defect bites every future verifier lane. Not "
                          "done here: the lane is VERIFIER (Art. 29(c) "
                          "recompute only) and the instrument may be "
                          "seal/prereg-pinned; cross-lane edits are typed "
                          "proposals, not silent fixes (Art. 5).",
    },
    "honesty_notes": [
        "window_started_at/window_ended_at are run-time stamps of the "
        "ORIGINAL generation window (committed values preserved; the "
        "recompute cannot re-derive wall-clock stamps and does not claim to).",
        "The scorer/critic verdicts recomputed here are the machine's own "
        "typed outputs from committed bytes; the AUDITOR's scoring of the "
        "30 rows vs the PRIVATE rubric is a separate lane and is untouched.",
    ],
}

dest = REPO / "eval" / "r92_v11_verifier_c0104.json"
dest.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
print("verdict:", verdict)
print("seal verified:", seal_expected, "| att match:", att_all_match,
      "| unique 30:", unique_pids, "| non-smoke:", non_smoke,
      "| run-record claims:", rr_all)
print("critic:", dict(critic), "| repairs:", dict(repairs_hist),
      "| burned_full:", burned_full, "| sign_contra:", sign_contra)
print("written:", dest)
sys.exit(0 if verdict == "VERIFIED" else 2)

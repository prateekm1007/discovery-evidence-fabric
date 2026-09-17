#!/usr/bin/env python3
"""RBG seal driver — repetition-based measurement as the only honest seal path.

Operator directive (R495): "repetition-based measurement is the only honest
seal path." Operationalized:

  1. The battery runs N independent repetitions (default 3), each a FRESH
     process with fresh live retrieval -- nothing cached across repetitions.
  2. Each repetition emits a record with its observed verdict sequence and
     the sha256 of that sequence.
  3. SEAL requires (a) every fixture passes in every repetition AND
     (b) ALL repetitions agree -- identical verdict sequences (unanimity,
     compared by sequence hash). Any disagreement -> NO SEAL, recorded as
     such. A single green run never seals anything (Art. XXVI / loop step 11).

Run: ELSEVIER_API_KEY=... python3 rbg_seal.py <out_dir> [--reps N] [--round R495] [--patent-leg-only]
Credentials via env injection only; never printed.

SCOPE (R498): --patent-leg-only seals ONLY the patent-leg fixtures
  (F6, F9, F10, F11; battery v3.1 mode). The seal record is scope-typed
  and explicitly does NOT claim the full battery: the Scopus side stands
  sealed 3/3 at R495 (R495/R495_RBG_SEAL_RECORD.json) and is neither
  re-measured nor re-claimed by a patent-leg-only seal. Exists because
  quota windows and credential availability are per-leg constraints
  (R497: SEAL_NOT_CLAIMED_QUOTA_INFEASIBLE with the Scopus side sealed).
"""

import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BATTERY = os.path.join(HERE, "rbg_battery.py")


def run_repetitions(out_dir, n_reps, round_label="R495",
                    patent_leg_only=False):
    os.makedirs(out_dir, exist_ok=True)
    reps = []
    for i in range(1, n_reps + 1):
        # QUOTA STEWARDSHIP (R497): once any completed repetition has a
        # failing fixture, unanimity is already impossible -- running further
        # repetitions would only burn metered provider quota for nothing.
        # Early-stop is recorded as a typed state; the seal then fails
        # honestly with the reason. (A fresh full seal remains the path when
        # the blocker is transient, e.g. provider quota.)
        prior_failure = any(
            (not r.get("process_failed") and r.get("all_fixtures_pass") is False)
            or r.get("process_failed") for r in reps)
        if prior_failure:
            reps.append({"repetition_id": "R%d" % i, "not_run_early_stop": True,
                         "reason": "seal already impossible after an earlier "
                                   "repetition failure; remaining repetitions not "
                                   "run -- metered provider quota preserved"})
            continue
        rep_id = "R%d" % i
        out_json = os.path.join(
            out_dir, "%s_RBG_REP_%s%s.json"
            % (round_label, rep_id,
               "_PATENT_LEG" if patent_leg_only else ""))
        # fresh process per repetition (loop step 11 discipline)
        argv = [sys.executable, BATTERY, rep_id, out_json]
        if patent_leg_only:
            argv.append("--patent-leg-only")
        proc = subprocess.run(
            argv,
            capture_output=True, text=True,
            env={**os.environ},  # env-injected credentials pass through
        )
        if proc.returncode != 0:
            reps.append({"repetition_id": rep_id, "process_failed": True,
                         "stderr_tail": proc.stderr[-400:]})
            break
        line = proc.stdout.strip().splitlines()[-1]
        summary = json.loads(line)
        reps.append({"repetition_id": rep_id,
                     "record_path": out_json,
                     "all_fixtures_pass": summary["all_fixtures_pass"],
                     "verdict_sequence_sha256": summary["verdict_sequence_sha256"],
                     "observed_verdicts": summary["observed_verdicts"]})
    return reps


def compute_seal(reps, n_reps, round_label="R495",
                 patent_leg_only=False):
    # a repetition counts as COMPLETE only if its process ran, produced a
    # verdict sequence, and passed all fixtures; early-stopped slots are
    # neither complete nor failures-to-agree -- they are recorded as such
    complete = [r for r in reps if not r.get("process_failed")
                and not r.get("not_run_early_stop")
                and r.get("verdict_sequence_sha256")]
    seal = {
        "seal_id": "%s_RBG_%sSEAL" % (round_label,
                                       "PATENT_LEG_" if patent_leg_only else ""),
        "seal_path": "repetition_based_measurement",
        "scope": ("PATENT_LEG_ONLY (fixtures F6, F9, F10, F11; battery v3.1 "
                  "mode)" if patent_leg_only else
                  "FULL_BATTERY (11 fixtures)"),
        "unanimity_rule": "all fixtures pass in all repetitions AND identical "
                          "verdict sequences across every repetition",
        "repetitions_requested": n_reps,
        "repetitions_completed": len(complete),
        "early_stopped_slots": [r["repetition_id"] for r in reps
                                if r.get("not_run_early_stop")],
    }
    if patent_leg_only:
        seal["explicitly_not_claimed"] = [
            "the FULL battery is NOT sealed by this record -- the patent-leg "
            "fixtures only (F6, F9, F10, F11)",
            "the Scopus side is NOT re-measured here and its R495 seal "
            "(R495/R495_RBG_SEAL_RECORD.json, 3/3 unanimous) is referenced, "
            "never re-claimed",
            "no novelty verdict exists in any scope (Art. XLVI)",
        ]
        seal["scopus_side_status"] = {
            "state": "NOT_MEASURED_THIS_RUN",
            "reason": "ELSEVIER_API_KEY absent from every LXXIII store this "
                      "round (session env, local vault, Space secret surface)",
            "standing_seal": "R495/R495_RBG_SEAL_RECORD.json (3/3, unanimous, "
                             "hash db336e97...)",
        }
    seq_hashes = sorted({r["verdict_sequence_sha256"] for r in complete})
    all_pass = bool(complete) and all(r["all_fixtures_pass"] for r in complete)
    unanimous = len(complete) == n_reps and len(seq_hashes) == 1
    seal["per_repetition_hashes"] = [r["verdict_sequence_sha256"] for r in complete]
    seal["all_fixtures_pass_everywhere"] = all_pass
    seal["unanimous"] = unanimous
    seal["sealed"] = bool(all_pass and unanimous)
    seal["verdict_sequence_agreed"] = seq_hashes[0] if seal["sealed"] else None
    if not seal["sealed"]:
        seal["no_seal_reason"] = (
            "repetitions disagreed or failed" if len(seq_hashes) > 1 or not all_pass
            else "fewer than the requested repetitions completed")
    seal["sealed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    seal["reviewer_provenance"] = "AI_REVIEW"
    return seal


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/download/R495/repetitions"
    n_reps = 3
    if "--reps" in sys.argv:
        n_reps = int(sys.argv[sys.argv.index("--reps") + 1])
    round_label = "R495"
    if "--round" in sys.argv:
        round_label = sys.argv[sys.argv.index("--round") + 1]
    patent_leg_only = "--patent-leg-only" in sys.argv
    reps = run_repetitions(out_dir, n_reps, round_label,
                           patent_leg_only=patent_leg_only)
    seal = compute_seal(reps, n_reps, round_label,
                        patent_leg_only=patent_leg_only)
    record = {"seal_record": seal, "repetitions": reps,
              "battery_version_note": "battery_version recorded per repetition (v1 = R495 "
                                      "8-fixture corpus; v2 = R496 9-fixture corpus with the "
                                      "multi-provider patent layer + F9; v3 = R497 11-fixture "
                                      "corpus with PatentBear LIVE: F6 coverage statement, F9 "
                                      "measured-401 garbage key, F10/F11 patent-leg byte "
                                      "binding; Art. VII disclosed fixture update; v3.1 = "
                                      "R498 --patent-leg-only MODE extension, invariants "
                                      "unchanged)",
              "seal_statement": (
                  "Sealed by repetition-based measurement: %d independent fresh-process "
                  "repetitions of the live-retrieval battery, unanimous verdict sequences, "
                  "per-repetition sequence hashes recorded. SCOPE: %s"
                  % (n_reps, seal["scope"])) if seal["sealed"]
              else "NOT SEALED: the unanimity rule was not met; recorded honestly.",
              "directive_anchor": "repetition-based measurement is the only honest seal path"}
    path = os.path.join("/home/z/my-project/download", round_label,
                        "%s_RBG_%sSEAL_RECORD.json"
                        % (round_label,
                           "PATENT_LEG_" if patent_leg_only else ""))
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2)
    print(json.dumps({"sealed": seal["sealed"],
                      "reps_completed": seal["repetitions_completed"],
                      "unanimous": seal["unanimous"],
                      "all_pass": seal["all_fixtures_pass_everywhere"]}))

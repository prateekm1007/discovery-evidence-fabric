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

Run: ELSEVIER_API_KEY=... python3 rbg_seal.py <out_dir> [--reps N]
Credentials via env injection only; never printed.
"""

import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BATTERY = os.path.join(HERE, "rbg_battery.py")


def run_repetitions(out_dir, n_reps):
    os.makedirs(out_dir, exist_ok=True)
    reps = []
    for i in range(1, n_reps + 1):
        rep_id = "R%d" % i
        out_json = os.path.join(out_dir, "R495_RBG_REP_%s.json" % rep_id)
        # fresh process per repetition (loop step 11 discipline)
        proc = subprocess.run(
            [sys.executable, BATTERY, rep_id, out_json],
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


def compute_seal(reps, n_reps, round_label="R495"):
    complete = [r for r in reps if not r.get("process_failed")]
    seal = {
        "seal_id": "%s_RBG_SEAL" % round_label,
        "seal_path": "repetition_based_measurement",
        "unanimity_rule": "all fixtures pass in all repetitions AND identical "
                          "verdict sequences across every repetition",
        "repetitions_requested": n_reps,
        "repetitions_completed": len(complete),
    }
    seq_hashes = sorted({r["verdict_sequence_sha256"] for r in complete})
    all_pass = all(r["all_fixtures_pass"] for r in complete)
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
    reps = run_repetitions(out_dir, n_reps)
    seal = compute_seal(reps, n_reps, round_label)
    record = {"seal_record": seal, "repetitions": reps,
              "battery_version_note": "battery_version recorded per repetition (v1 = R495 "
                                      "8-fixture corpus; v2 = R496 9-fixture corpus with the "
                                      "multi-provider patent layer + F9)",
              "seal_statement": (
                  "Sealed by repetition-based measurement: %d independent fresh-process "
                  "repetitions of the live-retrieval battery, unanimous verdict sequences, "
                  "per-repetition sequence hashes recorded." % n_reps) if seal["sealed"]
              else "NOT SEALED: the unanimity rule was not met; recorded honestly.",
              "directive_anchor": "repetition-based measurement is the only honest seal path"}
    path = os.path.join("/home/z/my-project/download", round_label,
                        "%s_RBG_SEAL_RECORD.json" % round_label)
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2)
    print(json.dumps({"sealed": seal["sealed"],
                      "reps_completed": seal["repetitions_completed"],
                      "unanimous": seal["unanimous"],
                      "all_pass": seal["all_fixtures_pass_everywhere"]}))

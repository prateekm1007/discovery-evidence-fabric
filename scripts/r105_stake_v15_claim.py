#!/usr/bin/env python3
"""Stake c-0119 — the sealed v15 lane (AM90/V90 continuation).

Art. 29(b): c-0119 is staked BEFORE any byte of the sealed v15 problem
set is read. The executor has read ZERO problem bytes: the only v15
facts in context are the auditor's AM90 disclosures (textile/leather
cluster, seal b0e7011309fa37cb, 30 problems, direction/equilibrium/
monoculture/input-trap counts) and the PUBLIC PREREGISTRATION metadata
(seal, n=30, model pin agnes-3.0-flash, custody paths, acceptance
bar) — the pre-registration is a custody input, not problem content.

CLAIM-ID RENUMBER (Art. 4 correction, forward-only): the first stake
numbered its claim c-0118 (local commit 73953ddf5, push rejected
non-fast-forward, never landed) concurrently with builder-r103s1's
VERIFIER record that landed FIRST on the queue branch under the same
number — a DIFFERENT work_id (physics-sign-guards-dev, role VERIFIER,
the c-0116 recompute + measure_guard supersession). NO work_id
collision and NO stand-down: holdout-v15-generation carries ZERO
claims on the remote; the renumber follows the f6dc98f34 precedent
and this push is the Art. 29(b) lock.

One mechanical pre-claim step is DISCLOSED (Art. 5): the F50
canonical-tuple seal recompute ran BEFORE the first stake as a pure
byte check — sha256 over the r38 canonical recipe (contamination-
filtered 6-field tuples, sorted, compact JSON); zero problem bytes
entered the builder's context or cognition. The recipe was validated
against the v14 known-good control (7707a0b4520c2a52 MATCH) before
reading the v15 result (b0e7011309fa37cb MATCH). The field-level
instrument read (the V15 domain-head map derivation) remains
STRICTLY POST-PUSH per the v14 precedent (AM88: "derived from the
committed problem device/failure fields by the executor AFTER the
claim push").

Artifact paths are BARE (the F42/forward-only format fix — annotated
paths broke the Art. 29 canonical prefix-match on the c-0115 lane).
"""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
PATH = REPO + "/eval/work_claims.json"

now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, cwd=REPO).stdout.strip()[:9]

session_note = (
    "R105 session-1: continuation of the r103s1/r95s1 builder lineage "
    "(same lane, new context window after five consecutive "
    "sandbox-start failures, all typed fail-closed UNRUN in-session; "
    "sandbox restored 2026-11-19T17:22Z). Executor of the AM90/V90 "
    "lane: the sealed v15 blind-acceptance generation on the "
    "SUPERSEDING permitted_measures engine (r103s1's verifier duty "
    "DONE — inherited, not duplicated).")

claim = {
    "claim_id": "c-0119",
    "claimed_at": f"{now} (sandbox clock, TRUE UTC)",
    "registered_at": f"{now} (sandbox clock, TRUE UTC)",
    "work_id": "holdout-v15-generation",
    "title": (
        "THE SEALED V15 LANE (builder-r105s1, AM90/V90): (1) the F50 "
        "canonical-tuple seal verify == b0e7011309fa37cb (DONE "
        "pre-claim as a mechanical byte check, disclosed; v14 control "
        "7707a0b4520c2a52 reproduced first); (2) derive the V15 "
        "domain-head map from the committed device/failure fields "
        "(the mandated pre-run instrument read, STRICTLY POST-PUSH "
        "per the v14/AM88 precedent); (3) run the fail-closed "
        "r99_disjointness_guard over the FULL v1-v14 corpus + dev12 "
        "— 0 clashes REQUIRED before any run; (4) the sealed v15 "
        "one-shot on agnes-3.0-flash (default, 2-key rotation) with "
        "the five binds + c-0109 corrector (v1.2) + c-0110 AIDE + "
        "c-0112 adaptive conformal + the SUPERSEDING permitted_"
        "measures per-problem enforcement (r103s1 DONE — inherited, "
        "not duplicated) + the ammonia direction bind; 30/30 "
        "served==requested==registered attestation; durable "
        "all-row events ledger; MEASURED_PATH through engine_route "
        "-> mechanism_space; (5) push + remote CI (check-run API "
        "read) + typed handoff. The problems are read ONLY from the "
        "audit branch (46b826512) AFTER this claim's push (push="
        "lock). The rubric is PRIVATE custody and NEVER read "
        "pre-generation. Zero acceptance/score claims — the auditor "
        "scores vs the private rubric (mean >=3.5, CI lower >3.0, "
        "0/0/0 -> re-earn score 7 -> BURN v15)."),
    "status": "OPEN",
    "session_id": "builder-r105s1",
    "role": "EXECUTOR",
    "kind": "one_shot",
    "base_sha": base,
    "lease_expiry": "2026-11-22T23:59:00Z",
    "artifact_paths": [
        "audit/holdout_v15/holdout_v15_problems.json",
        "audit/holdout_v15/PREREGISTRATION.json",
        "scripts/r99_disjointness_guard.py",
        "scripts/r105_v15_one_shot.py",
        "scripts/r105_stake_v15_claim.py",
        "eval/holdout_v15_generation/",
        "eval/r105s1_status.json",
        "eval/r99_disjointness_v15_record.json",
    ],
    "notes": (
        "Art. 29(b): claimed before ANY v15 problem byte is read — "
        "no_problem_read_before_claim=True. The claim push IS the "
        "lock; the map derivation and the guard's instrument read "
        "happen strictly post-push, fail-closed. Art. 5 disclosure: "
        "the pre-claim F50 seal verify was a mechanical recipe-hash "
        "byte check (zero content surfaced; the recipe itself was "
        "locked by reproducing the v14 known-good seal FIRST — "
        "preventing a recipe-fitted false match). kind=one_shot per "
        "the c-0082 sealed-generation precedent; this claim is the "
        "sole chain root on holdout-v15-generation (Art. 29(c): "
        "exactly one generation). RENUMBER NOTE: first stake was "
        "c-0118 (73953ddf5, push rejected non-fast-forward, zero "
        "remote effect); the number had been taken FIRST on the "
        "remote by the r103s1 VERIFIER record (different work_id) — "
        "no work_id collision, disjoint-work rebase, claim_id "
        "renumbered per the f6dc98f34 precedent; zero problem bytes "
        "read at any point."),
    "no_problem_read_before_claim": "True",
}


def main():
    with open(PATH) as f:
        d = json.load(f)
    claims = d["claims"]
    assert all(c["claim_id"] != "c-0119" for c in claims), \
        "c-0119 already exists"
    assert not any(c.get("work_id") == "holdout-v15-generation"
                   for c in claims), \
        "work_id holdout-v15-generation already claimed (no dual stake)"
    d["sessions"]["builder-r105s1"] = {
        "registered_at": f"{now} (sandbox clock, TRUE UTC)",
        "role": "builder",
        "note": session_note,
    }
    claims.append(claim)
    with open(PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("c-0119 staked (holdout-v15-generation, one_shot) | "
          "claims:", len(claims), "| base:", base, "| session "
          "builder-r105s1 registered")


if __name__ == "__main__":
    main()

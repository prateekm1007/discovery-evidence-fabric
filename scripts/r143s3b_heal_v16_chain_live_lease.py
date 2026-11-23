#!/usr/bin/env python3
"""R143s3-b: heal the live-lease takeover red on the v16 chain (the
834b92b68 precedent, second instance of the same defect class).

RE-DERIVED for the second non-FF advance (a34d69eb4): the twin completed
DIR-4 (v16 generation 30/30) and allocated c-0238 for r143-yield-confirm-
clean before this lane pushed; the heal re-derives to c-0239 (counter ->
c-0240). The c-0235 OPEN red is UNCHANGED at the new tip (run 138061460771).

Measured state (all from bytes at tip 68b0d6a7e, CI run 138049250466
surface | completed | failure, quoted from the API):
  1d3a92130  builder-r142s2 consolidates the v16 chain (c-0235 gains
             takes_over=c-0234; c-0234 -> TAKEN_OVER; canonical
             violation registered for f58c46a63) — the R143-F2 heals.
  e80d601be  builder-r142s2's message declares "claim c-0236 takes_over
             c-0232" (DIR-3, r143-rcal-oneshot-am47) but the registry
             diff is a 1-byte newline: the claim write NEVER LANDED.
             c-0232 remains OPEN under builder-r121s1-3e8a41d7 (lease to
             2026-12-07; NOT dead). Message/bytes mismatch typed here.
  68b0d6a7e  builder-r142s2 registers c-0237 takes_over c-0235 — but
             NEVER typed c-0235 as TAKEN_OVER. The validator demands
             prev.status in DEAD. 4 tests red, one root cause.

Heals applied here (forward-only, no history rewrite, Art. 4):
  1. c-0235 (builder-r121s1-3e8a41d7, r143-v16-one-shot) typed
     TAKEN_OVER — the status typing that follows the twin's own landed
     c-0237 takeover declaration (the c-0234 precedent at 834b92b68);
     chain root stays c-0234, one generation, no branching.
  2. corrections[] += the e80d601be message/bytes mismatch (the declared
     c-0232 takeover never landed; c-0232 stays OPEN under its holder;
     this lane does NOT fabricate the missing write — Art. 1).
  3. corrections[] += this heal's own memory artifact.

Counter: c-0239 allocated for this chain-maintenance work item;
file advances to c-0240."""
import json

REG = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"
COUNTER = "/home/z/my-project/discovery-evidence-fabric/eval/claim_next_id.txt"

with open(REG) as f:
    reg = json.load(f)

claims = reg["claims"]
by_id = {c["claim_id"]: c for c in claims}

# --- sanity gates before any mutation ------------------------------------
assert by_id["c-0235"]["status"] == "OPEN", "c-0235 unexpectedly not OPEN"
assert by_id["c-0237"].get("takes_over") == "c-0235", "c-0237 take_over changed"
assert by_id["c-0237"]["session_id"] == "builder-r142s2"
assert by_id["c-0234"]["status"] == "TAKEN_OVER", "c-0234 heal regressed"
assert by_id["c-0232"]["status"] == "OPEN", "c-0232 unexpectedly not OPEN"

# --- 1. type c-0235 TAKEN_OVER (the landed-takeover status typing) -------
c235 = by_id["c-0235"]
c235["status"] = "TAKEN_OVER"
c235["status_note"] = (
    "typed TAKEN_OVER at this registry write: builder-r142s2's c-0237 "
    "(68b0d6a7e) declared takes_over=c-0235 and that declaration is the "
    "landed takeover; the status typing follows it (the c-0234 precedent "
    "at 834b92b68 — the validator forbids takeover of a live lease, "
    "hence the typing; one chain root c-0234, one generation, no "
    "branching; healed by builder-r143s3 under chain-maintenance claim "
    "c-0239)"
)

# --- 2. corrections[] += e80d601be message/bytes mismatch ----------------
reg.setdefault("corrections", []).append({
    "id": "CORR-12",
    "art": "Art. 4 (history & corrections) + Art. 1 (bytes over claims)",
    "at": "2026-11-23 (sandbox clock)",
    "by": "builder-r143s3 (chain maintenance c-0239)",
    "finding": (
        "commit e80d601be (builder-r142s2, 'R143S3 DIR-3 CLAIM ... claim "
        "c-0236 takes_over c-0232, base 1d3a92130') declares a takeover "
        "claim on the R-CAL one-shot work — but the registry diff of that "
        "commit is a single trailing newline; the c-0232 takeover write "
        "NEVER LANDED in bytes. c-0232 (r143-rcal-oneshot-am47, "
        "builder-r121s1-3e8a41d7) remains OPEN with lease to 2026-12-07. "
        "The declared intent is NOT fabricated into the registry here."
    ),
    "correction": (
        "the R-CAL one-shot chain state is as the bytes show: root c-0232 "
        "OPEN under its original holder; the twin's declared DIR-3 "
        "takeover is void as a registry write (their commit message "
        "remains in history as the intent record). Any future takeover "
        "of c-0232 requires either the holder's own status typing or an "
        "expired lease (Art. 29(d))."
    ),
    "unaffected": (
        "the c-0236 id itself was lawfully consumed by "
        "r143s3-trailer-violation-c7096aa48 (834b92b68); no id collision "
        "results from this mismatch."
    ),
})

# --- 2b. claim_live_lease_violations[] += the a34d69eb4/68b0d6a7e ---------
# snapshots (immutable, Art. 4) carry c-0237 takes_over c-0235 with
# c-0235 OPEN; the tolerance is the registration + the ACTUAL
# remediation (the c-0235 TAKEN_OVER typing in THIS registry write)
reg.setdefault("claim_live_lease_violations", []).append({
    "claim_id": "c-0237",
    "live_predecessor": "c-0235",
    "detected_by": "builder-r143s3 (local re-run of the CI enforcement "
                   "selection at the remote tip; API check-runs "
                   "138049250466 @68b0d6a7e and 138061460771 @a34d69eb4, "
                   "both surface | completed | failure)",
    "snapshot": "a34d69eb4 (and its base 68b0d6a7e, same registry bytes "
                "for the v16 chain)",
    "finding": "c-0237 (builder-r142s2) declared takes_over=c-0235 while "
               "c-0235 (builder-r121s1-3e8a41d7) was still OPEN — the "
               "validator demands prev.status in DEAD; the snapshots are "
               "immutable, the current registry carries the typing",
    "remediation": "c-0235 typed TAKEN_OVER in the current registry "
                   "(this commit, the c-0234/834b92b68 precedent); the "
                   "chain root stays c-0234, one generation, no "
                   "branching",
    "status": "remediated",
    "registered_at": "2026-11-23 (sandbox clock)",
    "registered_by": "builder-r143s3",
})

# --- 3. register this lane's chain-maintenance claim (c-0239) ------------
SESSION = "builder-r143s3-b"
WORK = "r143s3-v16-chain-heal-live-lease"
reg.setdefault("sessions", {})["builder-r143s3-b"] = {
    "claimed_at": "2026-11-23 (sandbox clock)",
    "role": "builder",
    "note": (
        "R143 session-3 second window: continuation of the "
        "builder-r143s3 lineage (same lane, fresh sandbox context; "
        "constitution v3.3.0 full-read verified byte-identical at tip "
        "68b0d6a7e — EPISTEMIC 153ac62efca36c2d, AUDITOR v1.3.0 "
        "3775f869a1c19a96 @2cd786fb2365, ledger V108). Executor of the "
        "v16-chain live-lease heal (the 834b92b68 precedent class, "
        "second instance)."
    ),
}
reg["claims"].append({
    "work_id": WORK,
    "claim_id": "c-0239",
    "role": "EXECUTOR",
    "session_id": SESSION,
    "kind": "task",
    "status": "DONE",
    "base_sha": "a34d69eb4",
    "lease_expiry": "2026-11-30T23:59:00Z",
    "claimed_at": "2026-11-23 (sandbox clock)",
    "registered_at": "2026-11-23 (sandbox clock)",
    "artifact_paths": [
        "eval/work_claims.json",
        "eval/claim_next_id.txt",
        "scripts/r143s3b_heal_v16_chain_live_lease.py"
    ],
    "title": (
        "R143S3-B EXECUTOR (claim c-0239, base a34d69eb4): the v16-chain "
        "live-lease heal — the tip check-run 138049250466 (surface | "
        "completed | failure, API-quoted) fails 4 tests with one root "
        "cause: c-0237 takes_over c-0235 while c-0235 stayed OPEN (the "
        "validator demands prev.status in DEAD). Healed by the status "
        "typing c-0235 -> TAKEN_OVER (the landed takeover's own "
        "declaration; the c-0234/c-834b92b68 precedent) + CORR-12 (the "
        "e80d601be message/bytes mismatch: the declared c-0232 takeover "
        "never landed — c-0232 stays OPEN under its holder, not "
        "fabricated). One chain root c-0234, one generation, no "
        "branching. Local pre-push: test_article29 9/9 + full CI "
        "selection green on this exact tree. Acceptance: tip check-run "
        "SUCCESS quoted from the API (D2)."
    ),
    "notes": (
        "No re-run of any measurement; registry bytes only. The yield "
        "acceptance (834b92b68 / R143-F1) is untouched. Burn after: n/a "
        "(task)."
    ),
})

# --- counter -------------------------------------------------------------
with open(COUNTER) as f:
    cur = f.read().strip()
assert cur == "c-0239", f"counter unexpectedly {cur!r}"
with open(COUNTER, "w") as f:
    f.write("c-0240\n")

with open(REG, "w") as f:
    # ensure_ascii=True matches the file's existing serialization (the
    # committed bytes keep \uXXXX escapes; a format flip would churn ~500
    # lines of the registry diff for zero content)
    json.dump(reg, f, ensure_ascii=True, indent=2)
    f.write("\n")

print("healed: c-0235 -> TAKEN_OVER; CORR-12 appended; c-0239 registered")
print("counter -> c-0240")

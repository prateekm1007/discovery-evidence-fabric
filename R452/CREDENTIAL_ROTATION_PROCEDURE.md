# Credential Revocation / Rotation Procedure — R452-C2 (Operator-Owned)

**Security state: OPEN** — both credentials are PROVEN LIVE in the currently
reachable repository history (automated verification:
`scripts/r452_credential_history_verification.py`, this round:
`R452/CREDENTIAL_HISTORY_VERIFICATION.json`, verdict
`ACTIVE_CREDENTIAL_IN_REACHABLE_HISTORY`).

**Opened:** R451-C2 (2026-09-13). **Escalation count (Art. LXV): 4** — this
is the second consecutive round the rotation remains open; every additional
round the credentials stay live, anyone with repository read access can
impersonate this project on GitHub and Hugging Face.

## The two live credentials (fingerprints only)

| Kind | Fingerprint | Where the exposure lives | Proven live |
|---|---|---|---|
| GitHub classic PAT | `ghp_...ZarT (len=40) sha256:f1ebca5f9b62` | pushed git history (pre-scrub blobs of `R451/CREDENTIAL_SCAN_PRE_SCRUB.json` and the original script commits) | this round, automated probe: HTTP 200 on `GET /user` |
| Hugging Face token | `hf_M...NkNM (len=37) sha256:33bc7af22c62` | pushed git history (pre-scrub blobs) | this round, automated probe: HTTP 200 on `whoami-v2` as the operator account |

The current TREE is clean (forward-redacted). The REACHABLE HISTORY is not —
redaction was deliberately forward-only (no history rewrite, Art. XI), so
the exposure is the history, and the fix that actually kills it is
**revocation**, which no amount of file editing can substitute.

## Operator steps (the only machine-unexecutable part)

1. **Revoke the GitHub PAT** (the operator must be logged in as the account
   that owns it):
   - GitHub → Settings → Developer settings → Personal access tokens
     (classic) → locate the token with fingerprint `ghp_...ZarT` → **Delete
     (Revoke)**.
   - If the token is fine-grained: Settings → Developer settings →
     Fine-grained tokens → Delete.
   - Rotation (only if a GitHub token is still needed for the workflow):
     generate a NEW token, inject it exclusively via a secret/env-var
     channel (BS-021: env-var transient use only, never a tracked file).
2. **Revoke the HF token**:
   - huggingface.co → Settings → Access Tokens → locate `hf_M...NkNM` →
     **Revoke**.
   - **Cost warning (Art. LXV, stated explicitly):** verify BEFORE revoking
     whether the canonical production Space (`prateekm1/toscanini-prod-validation`)
     uses this token for its durable-state push (`runtime-state-hf`) or
     secret injection. If it does, rotate to a NEW token and update the
     Space's secrets in the same operation — otherwise production's own
     state push breaks. The rotation window should be minutes, not rounds.
3. **Do NOT rewrite git history casually** (operator decision, Art. XI):
   - Revocation alone makes the history inert — the bytes remain but grant
     nothing. That satisfies "no active credential in reachable history"
     and is verifiable by the automated tool below.
   - A history rewrite (`git filter-repo` / BFG + force-push of every
     branch + re-clone of every working copy) additionally removes the
     bytes, but is an epistemic event: afterwards, historical equivalence
     can no longer be proven (Art. XI) and the rewrite record must state
     exactly what can and cannot subsequently be proven. The machine does
     not choose this; the operator does.

## The automated verification (machine-executable, this round's delivery)

```
python3 scripts/r452_credential_history_verification.py --liveness \
    --json-out R452/CREDENTIAL_HISTORY_VERIFICATION.json
```

- Scans EVERY object reachable from ALL refs (23,486 blobs this round).
- Reports each candidate by fingerprint (values never printed).
- Probes each unique candidate read-only against its provider.
- **Exit 1 + `ACTIVE_CREDENTIAL_IN_REACHABLE_HISTORY`** while any candidate
  is live (today's state), exit 1 on unverified candidates (fail-closed,
  Art. XXV), and **exit 0 + `CANDIDATES_PRESENT_ALL_DEAD`** only after the
  operator's revocation makes every historical byte inert — that exit-0 run
  is the standing proof the directive requires. Re-run it after rotation;
  it is the permanent regression test for this exposure.

Base64-embedded key-shaped matches inside media payloads are classified
`base64_embedded_noise` (deterministic rule, reported, never counted —
noted here so the classification is never mistaken for a weakening: the
two real credentials are counted, probed, and today they are LIVE).

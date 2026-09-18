---
Task ID: R510-C1
Agent: new coder line (Windows fresh-clone session)
Task: operator directive "Next directions for the new coder (PAT + HF API in hand)": credential intake, bootstrap per handoff S0-S1 then S13 actions 1-9, ungated (a)-readiness + runtime-log pull + 215251c9 re-verify, intake commit + push, report and WAIT.

Work Log:
- Credential intake FIRST (directive S0): PAT len 40 sha16 f1ebca5f9b622f3e MATCH; HF len 37 sha16 33bc7af22c628bc1 MATCH. Session-env only, values never written to repo/logs/commits; keys cleared from memory after each use. No rotation (LXXVI).
- Bootstrap: fresh clone of discovery-evidence-fabric at a53a50a8 == origin/main, clean. Frozen chain re-hashed: e9c72c58 / 40d728f8 / 831f1a0e (match). Production GET /api/version: d7520b9bc5d7f26a2ab40b28367501e916634513 / 2.8.0 (match). Durable tip: origin/runtime-state-hf = 215251c9, parent 691d8d3d (match). Constitution in tree sha prefix 6aab103c (v2.9.0). Sibling check: no moves beyond a53a50a8 (top is R510-INTAKE itself).
- Must-reads S1 discharged: files 1-5 and 6-13 read (constitution/governance/ACTIVE_PATH/worklog R506-end/R506 record/R508 record/R509 records incl. ZLINE/POST_RESTART/respawn+support design notes/preflight+killswitch+watchdog instruments/R419 handoff/key-budget ledgers). Never-do entries recorded: never count pipeline signals as discovery; never tune the scored set or selectively publish; never convert UNKNOWN into REJECTED; never touch workers from watchdog/killswitch; never measure a moved build silently; never land key values in durable bytes.
- Watchdog: no python process running at intake; scripts present (watchdog, zline, preflight, killswitch). Self-test 5/5 OK. Single-tick live poll attempted on Windows: fail-closed OBSERVATION_GAP (env limitation, disclosed); 48h daemon NOT started (sandbox kills detached processes per R437 precedent). Replay acceptance stands on record.
- Pins: 39 passed + 1 skipped (r506 instrument + r507 firewall articles + r505 strong ring). Broad -k run shows 81 pre-existing Windows collection errors in unrelated suites (disclosed, out of scope).
- Preflight offline rehearsal (--skip-live, act2 "2.9.0 stands", ruling resubmit): GO. Offline only; authorizes nothing; gates A+B remain shut in transcript.
- (a)-readiness one-look (owner keys from durable sessions.json 215251c9, in-memory only, BS-021 clean): 6/6 session views HTTP 200 COMPLETE + 6/6 worker-diagnostics 200 present. View exposes terminal pipeline state (stages/final_state/evidence_pack) but zero run-dir envelope file bytes (only run_state dict). Run-dir bytes NOT exposable via any known read-only route. Finding: (a)-PARTIAL.
- Runtime-log pull: 404 on all three guessed HF API log paths; typed FETCH_FAILED_ENDPOINT_UNKNOWN, never absence.
- Preserved capture re-verified: 215251c9 commit + parent + sessions.json n=236 (battery 6/6 owner_key present) + 12/12 preservation files on durable branch.
- Evidence: R510/R510_INTAKE_EVIDENCE.json (codes + aggregate byte counts only; one field corrected post-measurement: pi-6 diag_bytes 15633 re-measured, never estimated).
- BS-021: zero long tokens in evidence file, worklog entry, .git/config; remote URL clean (transient header auth only).

Stage Summary:
- Intake durable after push: baseline green, pins green, preflight rehearsed, (a)-PARTIAL measured, gates A+B still shut, freeze held (records-only: R510/ + worklog; zero engine delta; no deploy; no resubmit; no recover-write; no restart; no secret writes). Waiting on operator word-acts.
- reviewer_provenance=AI_REVIEW

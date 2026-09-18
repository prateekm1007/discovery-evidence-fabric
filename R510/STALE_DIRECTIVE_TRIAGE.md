# Stale-Audit Triage (R510) — R499→R501 external audit vs current state (BS-037, no rewind)

Source: operator message carrying (a) a LIVE supply statement and (b) a STALE
audit (HEAD 0e78a905, constitution 2.7.0, score 5/10). Current: tip e9e8fcac,
constitution 2.9.0, true number 6/10 NO, production d15aaa75/2.9.0 GREEN.
Stale content is background, never instruction; live state wins every conflict.

## Live supply statement (ACCEPTED, supersedes an owner ask)

"Instead of funding huggingface credits we have various frontier model api keys
in huggingface secrets that coder can use." Standing consequence: the HF-funding
ask (old owner-action #1) is SUPERSEDED. Strong-ring path = secrets-held
frontier keys via server-side transport (values never enter this container):
xkiro proven in the B2 rerun (21/21 verdict-class); live matrix today shows
zai HEALTHY, xkiro DEGRADED (rings flap — measured, not assumed). B4 unblock
unchanged in kind (key VALUE still not held here) but the funding question is
closed by operator word.

## Stale score (NOT adopted)

5/10 was that era's number. Current lineage measures 138/25 = 5.52 → 6/10 NO.
Adopting 5/10 would be stale-metadata override (BS-019, Art. XXIV). Surfaced,
not reconciled silently.

## Directives triage (freeze holds; GATE A/B shut; engine changes forbidden)

- **D1 span binding → POST-HARVEST backlog.** Span machinery exists now
  (`span_derivation_check`, R377 span discipline); the 0.0 era measurement
  stands as history. Prompt+validator surgery is engine work — frozen.
- **D2 physics baseline → ROOT CAUSE TYPED read-only, fix post-harvest.**
  Metric reads `records[].physics_lifecycle` but stage_PHYSICS.json carries
  run-level `lifecycle_verdict` + `chain` with NO records array: 12/12 files
  yield zero countable records while 2 carry BEATS_BASELINE verdicts invisible
  to the metric. Neither CASE A/B/C — CASE D (reader/writer shape mismatch).
  Fix = code → backlog. Minimum-path "step 2 starts today" is DONE as diagnosis.
- **D3 free legs → wiring CONFIRMED in code** (HF_USPTO_CORPUS registered,
  ladder submit present); live-envelope proof GATED on resubmit; **EPO LOD at
  COLLISION NOT wired** (`patent_router.py` has no LOD/verify path) — open
  engine item, post-harvest. Zero debits spent (PatentBear untouched).
- **D4 attacker → already in motion.** v4.2-in-2.1.0 confirmed + measured
  (B2: 0.6/0.0 NOT_CALIBRATED); ring pre-screen == v4.3 degenerate-detector
  DESIGN (recorded); strong-ring requirement repointed at secrets keys (above).
- **D5 buyer package → GATED** (needs resubmit + visual-gate owner item).
  LXXII conditional-pass question flagged for constitutional review, not decided.
- **D6 Render surface → UNREACHABLE_THIS_ATTEMPT** (HTTPS timeout, typed;
  staleness neither confirmed nor cleared by this probe). Escalation stands;
  owner act (retire/upgrade). No code change.
- **D7 battery → measured honestly.** This container: **3,200 collected + 135
  collection errors** (stale "4,608/235" and "75 green" match nothing here
  either). One concrete genuine defect: `visual-lab/benchmark/test_r449.py`
  calls `sys.exit(0)` at import, killing collection (INTERNALERROR). Full
  triage (classify 135 into BS-020/genuine/secret-gated) is harness-side
  backlog — large, post-harvest legal, not started today.
- **Minimum-path correction:** step 1 (span fix) CANNOT start today (frozen
  engine); step 2 DONE as diagnosis; steps 3–5 owner-gated as stated, with the
  funding item superseded above.

## Scoreboard effect

None. True number unchanged 6/10 NO. This triage removes stale entropy; it
claims no capability (LXXVII).

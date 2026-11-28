# R108 Takeover Plan — the dead-peer lease executions (Art. 29(d) + Art. 18)

Author: builder-r108s1 (claim c-0132, 2026-11-20). This file is the
durable execution plan for the takeover windows. The peer session
builder-r105s2 is dead (sandbox gone; last heartbeat f04d92713
2026-11-20T03:59:51Z; all its work pushed); its OPEN EXECUTOR claims
hold live leases that the Art. 29 CI check will not let a second
executor take over until the lease dies (DEAD = EXPIRED/TAKEN_OVER).
The push mutex itself is blocked (GH_PAT absent, vault locked), so
this session stages its work and schedules GATEWAY-SIDE CRON WAKEUPS
(cron survives sandbox reprovision — the r64 incident record).

## Preflight (EVERY woken window, before any work byte)
1. Read BOTH constitutions IN FULL: `EPISTEMIC_CONSTITUTION.md` (the
   builder branch tip) + `AUDITOR_CONSTITUTION.md` (the audit branch).
   No preflight, no work (auditor constitution, read order).
2. Vault: if a vault-scoped HF token or GH_PAT has been delivered,
   write `.env.keys` (0600, gitignored, digest-only record) and run
   `python3 scripts/r77_vault_restore.py` (reads HF_TOKEN from env).
   Digests to verify against: XKIRO f6c09bee9bde / AGNES d0c666a3842f
   / GH_PAT f1ebca5f9b62 (eval/r59_credential_custody_r59s1.json).
3. Push state: `git -C /home/z/queue-wt fetch origin` then compare
   `queue/dev12_r7` vs `origin/queue/dev12_r7`. If the staged chain
   (146065dfa + the R108 commits) is still unpushed AND a PAT is now
   available, PUSH THE STAGED CHAIN FIRST (Art. 18: the staged commits
   are the record; the takeover claims ride the same push).
4. Re-read `eval/r108s1_d7d8_recon.json` (the measured source/mirror/
   disk matrix) and `eval/r108s1_c0129_verifier_record.json` (the
   VF-5..VF-8 findings — VF-6 BINDS the D4 rebuild).

## Window A — fires 2026-11-23T00:10Z (c-0127's lease died 11-22 23:59)
Claim: takeover of c-0127 (work_id `score9-postcutoff-rediscovery`,
executor lineage builder-r103s1 -> this window's fresh session id),
`takes_over: "c-0127"`, role EXECUTOR, kind measurement (the 30-batch
is quota-consuming). Scope: the D4 post-cutoff corpus rebuild + rerun.
- Apply the VF-6 bound: corpus items dated STRICTLY AFTER 2025-09-29
  (the first demonstrated post-knowledge failure; the committed
  2025-05-07 rule is RETIRED by the verifier finding — record the
  correction per Art. 4; do NOT reuse the committed rule).
- Source (per the recon matrix): re-test bulkdata.uspto.gov /
  patentsview / EPO for a reachable 2026 patent-claims source
  (OPTION-A, no distillation needed); else arXiv papers published
  after 2025-09-29 + agnes-3.0-flash distillation (OPTION-B,
  CREDENTIAL-GATED on AGNES). If BOTH are blocked, type the blocker
  and stand down — never idle on an unclaimable lane (Art. 28).
- The rerun (30-batch, one run, the prereg quota ceiling) is
  AGNES+judges-gated; it runs ONLY if the vault restored. The D5
  repair retry is already wired (f04d92713); the acceptance bar is
  0/30 parse losses + the recovery rate vs the 0.40 bar.
- VF-5 (P3): add the D5 repair-contract test (repair_prompt content,
  double-failure exhaustion, agnes_repair_calls accounting) — the
  coverage gap the verifier typed.

## Window B — fires 2026-11-24T00:10Z (c-0129/c-0130 leases died 11-23 23:59)
Claims: takeover of c-0130 (work_id `p3-datasets-model-d7d8`, EXECUTOR)
and — ONLY IF Window A left rebuild/rerun work unclaimed — takeover of
c-0129 (work_id `p3-score9-lane-d4d5d6`) for the remainder; if Window
A claimed the rebuild under c-0127, do NOT re-claim it under c-0129
(the typed division: the rebuild+rereun lane lives under c-0127's
takeover; c-0129's D4-D6 stages are executor-complete + verified
(c-0132) and its lane closes with a completion note).
- D7 (XJTU-SY, the zip-range path — NO RAR5 extraction needed):
  1. Range-fetch the EOCD + central directory of
     `https://huggingface.co/datasets/DavidNguyen/XJTU-SY_Bearing_Datasets/resolve/main/XJTU-SY_Bearing_Datasets.zip`
     (ETag cc883d5d0d940a64...; Accept-Ranges verified; 5,447,931,446
     bytes). Parse member spans; inventory the bearing folders + file
     counts.
  2. Select the typed subset: bearings with n >= 192 files (the
     CTX=96 protocol floor) across the 3 operating conditions, target
     ~1.5G extracted (disk: 5.9G free at recon time — RECHECK).
  3. Range-fetch the member spans; inflate (zlib raw); write to
     /home/z/my-project/p3_data_cache/xjtu_zip/ (sandbox-local,
     gitignored); record per-file sha256s + the byte inventory.
  4. Loader + measurement in the ENGINE (Art. 27: >=30% engine lines
     or the typed disclosure): discovery_fabric/engine/ gets the
     run-to-failure loader + the conformal walk (the stage-3 protocol
     constants: CTX=96, alpha=0.10, sliding K=100, N_CONSEC=3,
     n>=192); scripts/ holds only the thin driver. The per-file RMS
     of the horizontal channel (1 sample/min) is the degradation
     channel; measure coverage + alarms per bearing + the fleet
     summary; compare the FEMTO MIT mirror (odysseywt/FEMTO,
     FEMTO.csv 1,305.0MB) as the second set if disk allows.
- D8 (Sundial arm): thuml/sundial-base-128m (Apache-2.0, 513.3MB,
  custom code — trust_remote_code=True). Sequence AFTER D7's
  measurement + cache cleanup (torch CPU ~1.5-2G install + model
  513.3MB + C-MAPSS 12.4MB — the phm-datasets S3 zip re-verified
  200/12,429,152 bytes). Wire the Sundial arm in the ENGINE next to
  the committed protocol constants; run the SAME legs (FD001 all-100
  ch14 / FD002 40-units-seed-17 ch1, one-step TRUE-history walk,
  sliding conformal K=100); the matched-budget table compares Sundial
  vs the COMMITTED Chronos-Bolt/TimeMoE bytes (no Bolt re-run — Art.
  29(c)); declare a winner or a typed tie. Timer-XL is the typed
  secondary (long-context option) — only if budget remains.
- Both windows: commit with Session/Work-Id trailers; Art. 27 ledger
  in the round record; run the queue-surface battery locally before
  staging; attempt the push (the PAT may have landed).

## If a lease is somehow already taken (another live session)
Stand down to VERIFIER per Art. 29(b)/(e) — recompute from committed
bytes, never re-run, never rebase a duplicate.

## The standing blocker (both windows)
GH_PAT absent -> pushes blocked. The ONE master reminder per loss
event was issued (the R107 record); do NOT re-ask routinely. If still
blocked at execution time: stage the commits (the push order is
preserved on the queue branch) and type the blocker in the round
record. The auditor's re-delivery of the same public-read token
(b5aaf542b2fd) does NOT unlock the vault (re-tested 2026-11-20:
whoami 401, vault 401).

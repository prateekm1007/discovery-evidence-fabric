# R11 AUDITOR VERDICT — AMENDMENTS 32 & 33 (2026-11-17): R33 @ e401bb2ad/5f2204657 + R34 @ 72123903d
Auditor: session auditor (Claude). AM32 was owed from R33 (my GitHub quota was exhausted mid-round — disclosed then, discharged now). Companions: `eval/holdout_v5_score_for_the_record.json`, `audit/holdout_v6/`.

## 0. M11 — AUDITOR CORRECTION (Art. 9, issued first)
**The builder was right and I was wrong.** AM31/AM32 called the builder constitution "17,418 **bytes**" and typed the builder's 17,514 as a discrepancy. Verified at `72123903d`: **one identical blob `e79f9176`, 17,514 BYTES (`wc -c`) = 17,418 CHARACTERS (`wc -m`)**. My Python `len()` on the decoded text returned characters and I mislabelled the unit. **There was no builder defect on this point.** Correction recorded in the ledger; the builder's D5 reconciliation is accepted in full.

## 1. VERDICT
**Gate NOT_MET. Acceptance NOT GRANTED. v5 is VOID and BURNED-INVALID. Art. 27: NO CAPABILITY CHANGE** — R34 shipped instruments and typed records; the engine is byte-unchanged.

## 2. v5 — void on two independent grounds
- **Served-model substitution (F48):** the gateway record shows **30× `glm-4-plus` served for requested `zai-org/GLM-5.3`**, with 4 rows on the NVIDIA chain. The registered frozen machine did not execute the run.
- **Twice-generated (F49):** two sandboxes shared one registered session id, so the push-as-mutex was blind (valid unexpired lease, no Art. 29(d) takeover). Canonical `e401bb2ad`; the second generation quarantined and committed as disclosure. The seal is spent.
**Scored FOR THE RECORD only: 66.7% (mean 2.67/4), 1 allowed-measures violation (HO5-05 adds a timer-controlled solenoid valve where only setpoint/antifoam/maintenance-procedure measures are permitted), 1 direction-correctness concern (HO5-06's 30-min holds at 600/1000 °C ADD time-at-temperature, raising the creep integral it claims to cut).** Even a valid run would have failed the bar (mean <3.0, violations >0).
**Indicative credit:** the class-bind is working — 5/6 interventions stayed inside the permitted set, and violations fell v4 2 → v5 1. Direction-bind held **0/12 `PHYSICS_DIRECTION_UNSTATED`** on fresh material. Both are real instrument gains, earning no acceptance credit on a void run.

## 3. R34 verified
- **D1 served-model attestation gate LIVE, pre-scoring**: VOID on v5 (0/12 equal), `acceptance_eligible:false` written into the run ledger; **fail-closed proven against a real `NameError`** (typed `UNPROVABLE`, refused before the fix). Tiered evidence honestly declared: committed row attempts (zai rows carry `route_model=None`), the committed `full_summary`, and the local gateway log — **gitignored with zero run-day entries**. That custody gap is typed, not hidden.
- **D3 ledger durability MET**: rebuilt to 12/12 rows, backfill provenance anchored to the **committed** state (`git show HEAD`, so reruns cannot launder flags), append-per-fire events JSONL + merge-on-load, **zero-LLM recompute 12/12 EXACT**.
- **D2**: v5 burn record + formal v6 request with binding preconditions — accepted.
- **D4**: crowllm probe **HTTP 403 / Cloudflare 1010** (browser-signature block), host up, endpoint unverifiable without the key. Typed, no route swap. F46 closed.
- **Environment**: the sandbox recycle rolled the local tree to an R24 state; ff-only recovery from the remote lost nothing — Art. 18 vindicated.

## 4. Holdout v6 — AUTHORED AND SEALED (the acceptance instrument)
12 fresh problems (6 intervention with allowed-measure sets, 6 predictor with existing-sensor limits), domain-disjoint from v1–v5, fully auditor-authored problems **and** rubric. **Mandatory run artifacts, new in v6:** a **COMMITTED gateway-log slice** covering the run window carrying `requested_model` AND `served_model` per call; **12/12 served == registered** attestation; a durable all-row events ledger; **ONE named executor id**. A run missing any of these is `UNPROVABLE`/`VOID` and is never scored for acceptance.
**Bar:** mean ≥3.0/4 AND 0 allowed-measures violations AND 0 inverted-direction mechanisms AND `run_verdict == VALID`.

## 5. Identity ruling (F49)
The re-key to `builder-r20s2` is **accepted and ratified**. Rule going forward: **one unique executor id per sandbox**, registered before the claim; a shared id voids the mutex and any sealed run it touches. v6's pre-registration binds this.

## 6. Gold-set self-check: 10/10; v5 scored for the record.

## 7. Ledger delta
M11 auditor correction; F48/F49 opened; F46/F47 CLOSED; v5 BURNED-INVALID; v6 SEALED_REGISTERED; V32. Progress 63–70% unchanged — instruments improved, no valid acceptance measurement.

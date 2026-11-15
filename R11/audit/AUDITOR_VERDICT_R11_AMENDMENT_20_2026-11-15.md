# R11 AUDITOR VERDICT — AMENDMENT 20 (2026-11-15): R20 @ e5dbdd01a — F32 CLOSED with receipts; V4 pilot verified
Auditor: session auditor (Claude). Preflight: audit/preflight/PREFLIGHT_2026-11-15_r20.md. Companion: eval/auditor_judgments_r11_r20.json. Builder OFF audit branch (tip 0aa01d716).

## VERDICT
**Gate: NOT_MET — unchanged** (r11 overall type-credited: novelty 2.133 CI [1.426, 2.841] PASS / feasibility 1.367 CI [0.931, 1.802] FAIL). **F32 is CLOSED — the enforcement now gates the queue branch, verified with receipts.** The V4 hard-7 pilot is a strong, pre-registered, independently-recomputed direction probe (not the gate battery).

## 1. F32 CLOSED — and the race adjudicated honestly
- **Receipts verified**: queue CI `surface` = SUCCESS on a8c037f81, e43cd91e1, e5dbdd01a (three consecutive) vs FAILURE on 8c1013fae/d1cf5a129. The workflow now carries `pip install` (root cause: the setup-python toolcache python lacks pytest — every queue run died at the first pytest invocation) AND the enforcement suite (Arts. 19/21/22/23/25/26/28 on committed bytes). The failure→success delta across the fix boundary is exactly the sensitivity proof the acceptance demanded.
- **Race adjudication**: AM19's audit commits ran 13:32:52–13:34:25Z; the fix a8c037f81 landed 13:33:56Z — mid-audit. The R19 preflight read 8c1013fae, the tip at audit start; the snapshot was accurate at read time and the verdict raced the push by one commit. Genuine F25-class timing race (7th instance, benign). No auditor error; F32 closed on current bytes.

## 2. V4 hard-7 pilot — verified (Art. 13 recompute exact)
Pre-registered (3d3421d40, 13:52:28Z: SYS_A1_INT_V4 contract + subset from committed bytes) BEFORE measurement (e43cd91e1, 14:02:13Z). Recomputed from the comparison rows: **fgap 3.0 → 1.857** (5/7 improved, 0 worsened), **novelty mean 2.857 → 2.857** (internal redistribution: p05 −1, p09 −1, new05 −1→+1; no pair below 0.5), **judge prefers V4 on 7/7**. The mechanism targets the measured root cause: bench-p06's own ledger note said "would need to be developed" at fgap=4 — development-need hiding in ledger rows. V4's procurement rule (stated-present / procurable catalog / parameter-duty-procedure) + no-development rule forbid exactly that. Typed MECHANICS_PILOT; the ~1.1 overall projection is a LABELED ESTIMATE. The strict ≤0.25 clause needs the procurement rule extended to the predictor arm + the full 30-pair battery.

## 3. F33 — security event (recorded once, owner decides)
A builder probe echoed the git remote's URL-embedded GitHub PAT into the session transcript. **Auditor secret-scan of all four new round files: 0 leaks** — the exposure is transcript-only, not committed bytes. The builder self-disclosed and recommended rotation. Per the owner's standing instruction this is recorded once, not pestered: the owner decides. Practice note: the remote URL embeds the token as username — the vault is the canonical store (Art. 17); move the remote to credential-helper form.

## 4. Enforcement map
7/28 articles queue-gated (6/19/21/22-half/23/25-half/26/28); Art. 20 flagged live (no ablation-registry artifact exists); flags CI-pinned so gaps cannot silently disappear. F25 at 7 instances — owner name-executing-session still pending; holdout v2 still pending authorization.

## 5. Gold-set self-check: 10/10; V4 pilot recomputed exact.

## 6. Ledger delta
F32 CLOSED; F33 opened (owner-decision); F30 improving (V4 direction); F25 7 instances; V20 recorded. Progress 55–62% (enforcement live — the refactor's goal materially met; feasibility direction strong; gate not yet met).

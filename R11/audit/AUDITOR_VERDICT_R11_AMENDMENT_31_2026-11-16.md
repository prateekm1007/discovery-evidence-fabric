# R11 AUDITOR VERDICT — AMENDMENT 31 (2026-11-16): R32 — F45 CRITICAL public credential leak; two builder claims corrected; holdout v5 sealed
Auditor: session auditor (Claude). Builder OFF audit branch. Queue tip unchanged at 8e8e1b635 — **no new invention-machine commits: NO CAPABILITY CHANGE (Art. 27).**

## 1. F45 — CRITICAL, VERIFIED BY THE AUDITOR (top item)
The repository `prateekm1007/discovery-evidence-fabric` is **PUBLIC** (`visibility: public`, confirmed via the API). Two commit messages carry live-looking API keys, confirmed by direct fetch and pattern match (values masked here and everywhere in the audit record):
- **`f90fc7d9f`** (2026-08-18) — PatSnap-class key `sk-lcQO3…bwZ7`
- **`76c23fef7`** (2026-08-18) — OpenRouter key `sk-or-v1…6679`
They have been **publicly readable for ~3 months**. Scope check: a pattern scan of the last 300 queue commits found **0** further hits; the Aug 17–20 window found exactly these two. **Remedy is owner-side key rotation, urgently.** History rewrite is NOT the remedy — F42 already proved rewriting loses committed work, and the keys are already exposed regardless. After rotation, decide repo visibility deliberately. The builder used neither key; that is credited.

## 2. F46 — the judge-route conclusion is withdrawn (wrong provider probed)
The builder probed **OpenRouter** for `crowllm/qwen-3.8-max:free` and concluded the pre-registered judge model is "absent from the catalog". The registry (`discovery_fabric/engine/llm_registry.py`) pins the judge route to **`https://crowllm.com/v1/chat/completions` with `CROWLLM_API_KEY`** — a **different provider**. Absence from OpenRouter's catalog says nothing about crowllm. The earlier failures were crowllm-side 503/Cloudflare congestion, not a missing model. **The unblock is a servable CROWLLM_API_KEY plus crowllm.com reachability — not "name a new judge route."** No route swap is authorised or needed.

## 3. F47 — constitution read-order (AM30's citation was correct)
The builder reported "tip constitution is v2.11.0, not v3.1.0". Verified: **`queue/dev12_r7 @8e8e1b635` carries v3.1.0** (17,418 bytes, Article 29 + the Art. 28 LOOP-OWNED addendum present). The **audit branch** carries a stale 127,701-byte v2.x copy (85 articles, no Art. 29). The builder read the wrong branch. **Read the builder constitution from the builder branch**; the audit-branch copy is a historical artifact, not the governing text.

## 4. Accepted as typed
`f05f3d44e` is unreachable from a clone (a rewrite orphan — fetch never transfers unreachable objects), so the byte-identity of the R30 restoration cannot be independently recomputed. Accepted as typed; this is a further realised cost of F42, not a dispute.

## 5. Holdout v5 — AUTHORED AND SEALED (the acceptance instrument)
12 fresh problems (6 intervention with explicit allowed-measure sets, 6 predictor with existing-sensor limits), domain-disjoint from v1–v4 and the dev batteries. **Fully auditor-authored problems AND rubric.** Custody `audit/holdout_v5/`; rubric PRIVATE. One-shot under the **frozen V7.6 machine with both AM29 binds in the generation path**. **Acceptance bar: mean ≥3.0/4 AND 0 allowed-measures violations AND 0 inverted-direction mechanisms.** Burn after.

## 6. F44 — reporting drift persists
The round again mixed the audit lane with a side build (`model-vault-container`). The custody work and the leak discovery are real and credited; the report must still lead with the audited repo state.

## 7. Gold-set self-check: 10/10 (no new judged material).

## 8. Ledger delta
F45 CRITICAL opened (owner-urgent); F46/F47 opened (builder claims corrected); holdout_v5 SEALED_REGISTERED; V31. Progress 63–70% unchanged — no capability change; the security finding dominates this round.

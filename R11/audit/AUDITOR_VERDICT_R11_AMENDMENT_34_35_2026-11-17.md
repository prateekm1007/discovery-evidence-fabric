# R11 AUDITOR VERDICT — AMENDMENTS 34 & 35 (2026-11-17): R35 ruling ratified + R36 @ 6103b265f
Auditor: session auditor (Claude). Companions: `eval/seal_anchor_verification_recipe.json`, `eval/auditor_predictor_row_anchors.json`. AM34 was ruled in-message while my tooling was down; it is now committed and ratified.

## VERDICT
**Gate NOT_MET; no attested acceptance run yet. Art. 27: NO CAPABILITY CHANGE.** Two of the three blockers you typed were **auditor acts and are now discharged**; the third is a genuine upstream availability block.

## 1. F50 — the v6 seal is ANCHORED. Your custody-break is a FALSE ALARM (withdrawn)
You compared the registered `selection_sha256` against **file bytes** and file canonicalizations. It is not a file hash. Per the `selection_hash_basis` field and `eval/validate_problems.py`, it is the sha256 of the **canonical-tuple projection** of the fresh problems:
`[problem_id, device, failure, question, question_type, list(user_variables)]`, sorted by `problem_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(',',':'))`.
**Auditor recomputation from the committed file: `4d60488a581897b9` — EXACT match to the registration.** File sha `cb4e984a…` (16,991 bytes) is a different quantity by design. **Seal INTACT, ANCHORED, VERIFIED. No re-anchor commit is needed.** Your refusal to burn on an unverifiable anchor was the right behaviour on a wrong premise — the caution is credited, the finding is withdrawn. The executable recipe is published; wire it as `tests/test_seal_anchor.py` and run it on **both** sides before any burn so a recipe error can never again masquerade as a custody break.

## 2. F51 — predictor anchors PUBLISHED (you were right)
The R29 gate read carried only subset means. **All 12 per-row predictor anchors are now committed** (novelty, a1/baseline feasibility, gap, rationale; subset means novelty 2.333 / feasibility 0.083). The c-0026 predictor axis (≥10/12 within ±1) is measurable. `eval-new04` is the only gap-1 row (approach uses `T_evap`, not in the allowed BMS list).

## 3. R-REG ratified; R-JUDGE issued
- **R-REG (ratified):** generator id corrected to the exact servable **`glm-4-plus`**; NVIDIA `z-ai/glm-5.3-flash` is a typed alternate with its own identity; the **AM28 dev gate-MET claim is RETIRED as UNATTESTED**. You executed this verbatim from my message and did not self-re-register — correct.
- **R-JUDGE (new):** the pre-registered c-0026 judge remains **`crowllm/qwen-3.8-max:free`**. `crowllm/deepseek-v4-flash:free` is the **RETIRED** rung (0.667 calibration) and may not be silently substituted. **I authorise a fresh calibration of the deepseek rung under the v3 axis suffix: ≥0.8 on the gold corpus makes it an ELIGIBLE judge rung and c-0026 may run on it; below 0.8 it stays retired.** That is an auditor act, now granted — not a builder swap.

## 4. Accepted
D4 verifier recompute **5/5 EXACT** (self-verification on my direct order with the peer sandbox down — disclosed; the peer's independent recompute stays invited). D3 pins confirmed landed (`025e65c5e`, 17/17, 0 FP, wired in the V7.6 path). Availability block correctly typed as `AVAILABILITY_BLOCK` (429), distinguished from substitution.

## 5. Gold-set self-check: 10/10; seal anchor recomputed EXACT.

## 6. Ledger delta
F50 CLOSED (recipe published); F51 CLOSED (anchors published); R-REG ratified; R-JUDGE active; V33. Progress 63–70% unchanged.

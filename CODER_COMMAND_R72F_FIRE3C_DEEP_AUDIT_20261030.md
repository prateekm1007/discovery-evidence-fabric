# CODER COMMAND R72-FIRE-3c — DEEP-AUDIT MOE DISPATCH MATRIX (2026-10-30)

**From**: Audit desk (Oct-30 deep GitHub + Guild audit) | **Parent**: R72-FIRE-3b (e817d29) + R72 audit addendum
**Clock**: Oct-30, reset 00:00Z — fire now; exhaust every free entry on decode + moe paths before reset
**Supersedes**: nothing — folds new intel onto FIRE-3b; FIRE-3b's MoE-graft / PDL-pass / pooler lines stay in flight
**Constitution**: READ `CODER_CONSTITUTION.md` + `CODER_CONSTITUTION_AMENDMENT_20261027.md` FIRST. Articles 2-10 are non-negotiable and override any line below.

## 1. NEW INTEL (deep audit, Oct-30) — what changed

### 1.1 cuBLASLt / descriptor pinning is ALREADY HARVESTED — deprioritize
`_nbfp_prepare` (iyerramji v30-style: dedicated handle + 32 MiB workspace + prepared algo/descriptors, whole-GEMM BF16) is wired into `prepare()` and the `nbfp` candidate is auto-tuned per T in `_tune()` for T>=128. The nvjet kernels in the verify 16/32 profile ARE the pinned path (or torch.mm — tuner picks fastest). Re-spending entries on descriptor pinning = waste. **Do not re-spend.** (Residual: confirm prepare log does not print "nbfp disabled"; if it does, that is a free fix, one check.)

### 1.2 Per-case MoE is the only 10%-class lever
Table = sliding loads (weight 46), the dominant half of the geomean:

| load | T | build (now) | moe µs | case µs | moe% | BW TB/s | distinct experts |
|---|---|---|---|---|---|---|---|
| d1 | 1 | TINY | 29.9 | 87.5 | 34% | 1.78 | ~2.5 |
| d16 | 16 | MID | 86.1 | 157.9 | 55% | 1.88 | ~7.6 |
| d32 | 32 | MAIN | 84.2 | 166.3 | 51% | 2.25 | ~8.9 |
| v1 | 8 | TINY2 | 50.2 | 111.5 | 45% | 3.17 | ~7.5 |
| v16 | 128 | MAIN | 148.2 | 251.8 | 59% | 2.63 | ~18.4 |
| v32 | 256 | MAIN | 201.4 | 337.8 | 60% | 2.25 | ~21.3 |

Weak loads: d16 (1.88), d32 (2.25), v32 (2.25). Best: v1 (3.17, TINY2). Chord production H200 EP8 decode achieves 3.2-3.6 TB/s with swap-AB mma.sync 8|16|24x256x64, 3 CTAs/SM, one-pass, semi-static token tiles, `wait<1>`, stage depth 4-6.

### 1.3 MoE dispatch is static by T thresholds — and we never compared builds
Thresholds: TINY (T<=4), TINY2 (T<=8), MID (T<=16), MAIN (else). But all 5 builds compile in parallel at prepare() (line ~17191), and `_tune()` only times the build selected by T — it never compares builds. **Free experiment: measure every build per T and pick the fastest.** This is the gap.

### 1.4 MID build (T<=16) re-streams weights
MID uses `OKC_SPLIT=1` -> experts with >SK_T(8) tokens split into <=8-token jobs, re-streaming weights (source comment). At T=16 with ~2 tok/expert average, hot experts split -> duplicate reads. The SKT=16 two-tile path exists (`OKC_SKT>8`, `two` path, X1P smem) but MID's `OKC_WS=1` asserts `OKC_SKT==8` -> won't compile as-is.

### 1.5 WGS main build: 1 CTA/SM, 28% occupancy
Handles every expert in one pass up to FT_T=64 tokens (no fat queue in WGS), WGS_NS=3 ring. Chord's masked small tiles run 2 CTAs/SM by halving the ring — the trick.

### 1.6 Scored gate (freshest)
ci[0] > 2.183614 AND ci[0] >= 2.20540 (bar x 1.01523). ONE reserved submission. Carrier A/A n=8 mean 2.10626 (+0.18% over bank) — cannot clear alone.

## 2. STATE ANCHOR
- All six §2A BIF draws dispatched (B1-B6); all below bank. Scored economy = ONE reserved.
- R73 (zhebrak boundary triad) dead: 8/13 shape failures; do not re-fire unfixed.
- AMR NO-TRADE stands. PDL early-release chain: permanent negative (do not re-litigate; FIRE-3b's per-boundary table is the only open PDL question, already in flight).
- Rotation to ~21:30Z continues on surplus quota only.

## 3. BUILD + SPEND ORDER (exhaust entries before reset)

### E1 — MoE build autotune per T (FIRST; cheapest, highest value; 0 new CUDA)
Make `_moe()` selectable per T in `_tune()`. All 5 builds already compiled. Time each build (main, tiny, tiny2, mid, and E2's mid16) at every T in {1,2,4,8,16,32,64,128,256} using the existing `_after_attention` timing. Store `state["moe_build"][T]` = fastest build name. In `kernel_fn`, replace `ext = _moe(T)` with the selected build.
- Kaggle T4: static gate only (no runtime).
- H200: 1 unscored check. Readout: per-T winning build + per-case MoE µs + speedup vs carrier band (2.10626). Pre-reg: "if MAIN wins at T=16, d16 MoE expected -10..-20%."

### E2 — MID SKT=16 variant (targets d16 split; compile-gated)
Add `MOE_MID16_DEFINES = MOE_MID_DEFINES + ("-DOKC_SKT=16", "-DOKC_WS=0")` (drop WS to satisfy `static_assert(!OKC_WS || OKC_SKT==8)`). Compile as 6th build `_MOE_MID16`, thread into the parallel build list and E1's autotune.
- Kaggle T4: static gate must pass (smem size, assert). If compile fails, drop E2, keep E1.
- H200: folded into E1's single check (no extra spend).

### E3 — 2-CTA/SM small-M (chord masked-tile trick; T<=32 only; moderate risk)
Behind new define `OKC_WGSNS` (default 3) controlling `WGS_NS`, add a variant with `OKC_WGSNS=2` and launch with grid=2 x nsm for T<=32. Halves the ring (72 KB) -> 2 CTAs/SM fits (<=114 KB/CTA).
- Kaggle T4: static gate (smem <= 114 KB, compiles sm90a).
- H200: 1 check if E1/E2 leave >=1.5h; else post-reset.

### E4 — Chord swap-AB MMA 8|16|24x256x64 (THE big bet; post-reset unless surplus)
Full rewrite of the skinny path to chord's decode recipe (swap-AB mma.sync, 3 CTAs/SM, one-pass, semi-static token tiles, `wait<1>`, stage depth 4-6). Only if E1-E3 leave headroom AND >=2h remain. Otherwise post-reset build #1. Attribution: Novita Labs chord — verify license before graft; AMR NO-TRADE intact.
- H200: 1-2 checks.

### E5 — Dense GEMM (NO SPEND)
Already auto-tuned (nbfp/mm/mm16/bfp/bfpf). Record as harvested. Do not re-spend entries.

### E6 — PDL boundary chaining (already in flight per FIRE-3b)
Keep as parallel build; per-boundary launch-µs table is the discrepancy readout vs our two <=0 PDL draws. No change here.

## 4. FIRE LAW (single-shot)
Promotion = ACTUAL ci[0] > 2.183614 AND ci[0] >= 2.20540 AND same-hour control pair attached. The ONE reserved scored fires IMMEDIATELY on clearance — no rehearsing. Candidate sha recorded before launch. NO-FIRE with receipts is lawful. Post-reset, the reserved submission re-evaluates against the fresh bar with lever readouts in hand.

## 5. POST-RESET PRIORITY (amends FIRE-3b §5)
1. MoE dispatch matrix outcomes (E1-E4 readouts) -> census -> cells -> M32.
2. verify-full tiling BN-128 (verify-32 83% above SOL).
3. decode-16 sliding (71% above SOL).
4. sk2 launch-count co-residency (NOT epilogue glue).
5. PDL: re-derivation NO LONGER CONDITIONAL — tonight's per-boundary table opens or closes the class.
6. Pooler/unpooler cut net-of-bfpf (operator +3.36%).
7. NEW: chord swap-AB full port if E4 not done tonight.

## 6. DISCIPLINE (restated)
Kaggle T4 prevalidation before EVERY H200 spend. Pre-registered readout per rung. Monotone union-cumulative ladder; regress = drop + carry prior bytes. Negatives register enforced (glue fusion dead, __trap C7512, plain PDL on Triton, 1.75 GHz floor, f1k one-CTA/SM, L2 side-prefetch -0..18%, wgmin series, R3 solo illegal, PDL chain permanent negative, R73 8/13 dead). AMR NO-TRADE stands. Receipts per landing: pre-reg + job id + per-load table + worklog + push. No secrets in git (Article 2). Confirm repo private before push (it is: PRIVATE).

## 7. EXECUTION ORDER
L0 readback (quota) -> E1+E2 build in parallel (T4 both) -> E1 single check (H200) -> if >=1.5h remain: E3 build+T4+check -> E4 only if surplus >=2h -> rotation on surplus to 21:30Z -> fire ONE reserved scored on clearance -> receipts per landing -> post-reset table carries readouts. Use EVERY free entry on decode + moe paths before reset; do not waste them.

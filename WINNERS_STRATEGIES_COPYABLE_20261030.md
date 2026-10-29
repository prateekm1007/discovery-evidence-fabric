# WINNERS' STRATEGIES WE CAN COPY — Open Kernel Challenge (Oct-30 deep audit)

**Source**: OKC leaderboard (muse_decode_layer, 986 teams), ruwwww public repo (MIT, rank #167-171, documented strategy), chord (Novita Labs, Apache-2.0 production W4A16), iyerramji v30, zhebrak (Apache-2.0), QuantIntellect, sid19991, and our guild/github audit (R72).
**Target**: decode-layer Top 50 = speedup >= ~2.188 (live #50 = FindHao 2.1881; our bank 2.1095, gap x1.037). Top team mpeng19 = 2.4178.
**License check**: ruwwww MIT, chord Apache-2.0, zhebrak Apache-2.0 => graftable with attribution. iyerramji: verify license before graft. AMR NO-TRADE intact.

## 0. Leaderboard shape (decode layer)
- #1 mpeng19 2.4178 (31 attempts), #2 pjmullin3 2.4029 (25), #3 colinlikescode 2.3797 (26), #4 abhishekgahlot2 2.3649 (55), #5 Aspect5 2.3448 (56).
- #10 ntovas 2.3050, #20+ ~2.28, #40 ~2.20, #50 FindHao 2.1881, #170 ruwwww 2.0751.
- Pattern: top teams take 20-60 attempts; speedup scales with MoE + attention + dense GEMM wins combined. No single magic bullet; it's a union of many organs.

## 1. Copyable strategies ranked by decode impact

### A. MoE — biggest lever (55% of decode step) — copy ruwwww + chord
ruwwww `muse_moe_w4a16` (2.3370x, rank #85):
- 132 persistent CTAs (1 per SM), single megakernel, stays resident.
- Zero-DRAM intermediates: Phase A (W13 + SwiGLU) and Phase B (W2 + RMSNorm) in one CTA loop; SwiGLU stays in SMEM/regs.
- CUTLASS SM90 L2 cache hints: evict weights, keep tokens/norm accumulators.
- Dynamic dual work queues: heavy (fat, stream-K along K) vs skinny (16 rows, split-K warps), atomic dequeue.
chord (production, 3.2-3.6 TB/s H200 EP8 decode):
- Swap-AB mma.sync 8|16|24 x 256 x 64, one-pass, 3 CTAs/SM (down BM=8 -> 4).
- Semi-static token tiles (tile j=0 unconditional, j>=1 guarded): -7% cycles.
- Fused dequant lop3->hsub2->hmul2, subtract-then-scale exact.
- Stream-K via serial chain or counter barrier; FP32 partials; deterministic reduction.
- Stage depth 4-6 (worth 1-5%).
**Copy action**: graft chord's swap-AB decode recipe into our skinny path (E4 in FIRE-3c) OR ruwwww's persistent dual-queue MoE. Either replaces our 1-CTA/SM WGS path. Expected +10-20% on MoE = +5-11% whole.

### B. Attention — copy ruwwww (2.6032x, rank #69)
- Single-kernel end-to-end fusion: QKNorm/RoPE -> KV store -> FA3 -> RMSNorm/gate in ONE megakernel.
- WGMMA FP8 tensor cores: QK^T on FP8 MMA (E4M3 online quant), PV on FP8 WGMMA.
- Async paged cache streaming via cp.async 64-key tiles, multi-stage software pipeline.
- Fused epilogue in registers: RMSNorm variance + sigmoid gate before BF16 write.
**We already have**: fused decode attention (`_decode_attention7`) with split-KV + merge + norm-gate. Gap: FP8 QK^T WGMMA and register-only epilogue. Copy the FP8 tensor-core QK^T + register epilogue. Expected +5-10% on attention (attn is 5-36% of cases).

### C. Dense projections / cuBLASLt — copy ruwwww prefill (1.7950x)
- Explicit cuBLASLt signature pinning for all 14 GEMMs at M in {753,3012,16384}: eliminates prepare-time jitter, QKV 16K 776.7us, router 16K 189.9us.
- Multi-stream producer-consumer overlap: router proj + top-k on secondary stream while pooler GEMM + pre-expert norm on main stream, join via cudaStreamWaitEvent.
- Fused boundary kernels: RMSNorm + residual mix + MoE counter reset in one pass.
**We already have**: nbfp pinned descriptors (iyerramji-style) auto-tuned per T; fused boundaries; PDL. Gap: multi-stream overlap for router vs pooler (we do serial). Copy the dual-stream overlap. Expected +1-3% on dense.

### D. Pooler/router fusion — copy ruwwww decode
- Fused dual-output pooler + router: BF16 pooler and FP32 router in one launch sharing SMEM activation loads.
**We already have**: bfpf fused pooler+router (T<=32) and dense path. Gap: extend fusion to all T (currently T<=32 only). Expected +1-2%.

### E. Skinny projections 12-bit compression — copy ruwwww bf16_proj (1.5056x)
- Lossless 12-bit weights (8-bit low byte + 4-bit high nibble exponent index), bit-reconstructed in PTX regs, 25% HBM savings. Out-of-window escapes (<0.2%) via sparse FP32 correction table.
- Skinny swap-AB tensor-core GEMV (sk2): activations in SMEM as A, compressed weights in regs as B, mma.m16n8k16, no cross-CTA atomics.
- Router split into W_hi + W_lo (BF16 each) with FP32 accumulation for 1e-4 tolerance.
**We already have**: CWN 12-bit engine + sk2 + router hi/lo. Gap: none major; this is our strongest organ. Keep.

### F. End-to-end megakernel pipeline — copy ruwwww decode
- Unifies full decode step into one pipeline eliminating CPU launch overhead + device-wide sync barriers under CUDA Graph.
**We already have**: `_after_attention` chains projections/attention/MoE/boundaries in one Python call sequence, but launches are separate kernels. True megakernel fusion (single launch) is a bigger lift. Gap: moderate; high reward but high risk. Post-reset.

### G. Launch-count / occupancy tricks (from audit + QuantIntellect)
- QuantIntellect: `__trap()` inside bounded mbarrier wait in wgmma kernel -> ptxas C7512, 168-reg cap, serialized DEPBAR.LE gsb0,0x0 -> fix with error flag (we have 5 traps, need to verify serialization via cuobjdump).
- sk2 launch-count co-residency (NOT epilogue glue) — from intel fold.
- 2 CTAs/SM for small tiles (chord masked) — our E3.

## 2. What NOT to copy (dead / already ours)
- Descriptor pinning (iyerramji) — already harvested (nbfp).
- zhebrak 8-CTA boundary triad — R73 dead (8/13 shape failures), do not re-fire unfixed.
- AMR decode-bank trade — NO.
- PDL early-release chain — permanent negative (unless per-boundary table opens it).
- ruwwww whole-layer dispatch PIN_PICK — our carrier already beats ruwwww 4/6 decode shapes; not copyable (independently tuned).
- Generic scanning / broad re-tuning — constitution: narrow hypothesis radius.

## 3. Copyable playbook -> action mapping
| Copy from | Technique | Our gap | Expected gain (decode) | Status |
|---|---|---|---|---|
| chord + ruwwww moe | persistent dual-queue MoE, swap-AB 3 CTAs/SM | 1 CTA/SM WGS, 1.78-2.25 TB/s | +5-11% whole | E4 (FIRE-3c) |
| ruwwww attention | FP8 WGMMA QK^T + register epilogue | FP8 only in FA3 path | +2-5% whole | post-reset |
| ruwwww prefill | multi-stream router/pooler overlap | serial | +0.5-1.5% | post-reset |
| ruwwww decode | fused pooler+router all T | T<=32 only | +0.5-1% | post-reset |
| chord | 2 CTAs/SM small tiles, stage depth | 1 CTA/SM | +0.5-2% | E3 (FIRE-3c) |
| QuantIntellect | wgmma DEPBAR serialization fix | unverified | +1-3% if serialized | check via cuobjdump |
| (already ours) | 12-bit CWN, sk2, boundaries, nbfp, PDL | — | — | harvested |

## 4. Top-team pattern observations (from leaderboard)
- mpeng19 #1 2.4178 with 31 attempts — iterative, not one-shot.
- High attempt counts correlate with top ranks (abhishekgahlot2 55, Aspect5 56) — they iterate aggressively; our scored economy is 1 reserved, so we must pre-validate on Kaggle T4 + unscored checks, not scored.
- China-region names (zhebrak, zzz0906, zywang-hust, Mingyang-ZHAI, QuantIntellect, oyzh888) appear throughout top 500; their public contributions (zhebrak boundary triad, QuantIntellect trap) are the graftable ones.
- No top-50 team has fully public OKC code; ruwwww (#167-171) is the best-documented public reference. Copy the published techniques, not private repos.

## 5. Bottom line
Winning = union of ruwwww's documented organs (attention fusion, MoE persistent dual-queue, cuBLASLt pinning, fused boundaries, 12-bit compression) + chord's production MoE recipe (swap-AB, 3 CTAs/SM) + our unique organs (CWN 12-bit, sk2, boundary kernels, nbfp). Our biggest open gap is MoE occupancy (1.78-2.25 TB/s vs chord 3.2-3.6) — that is where the +5-11% whole lives. FIRE-3c E1-E4 target exactly that. Do not spend entries on already-harvested levers (cuBLASLt, 12-bit, boundaries).

# B2 Attacker-Calibration Track (R510) — DEV-only repetition + v4.3 lever design

## No-leak proof (before any DEV execution)

- Sealed corpus `R412/CALIBRATION/r412_attacker_calibration_corpus.json` sha256 ==
  `corpus_sha256` in `R412/CALIBRATION/r412_calibration_seal.json` (full 64-hex match).
- Both seal copies byte-identical
  (`R412/...` == `discovery_fabric/engine/calibration_records/...`, sha8 `7291d671`).
- Sealed bytes therefore untouched by anything on the DEV line. Sealed re-measure
  not executed (no leak possible; execution would itself be the risk).

## Freeze note (Art. XV disclosure, no action)

The R492 DEV freeze contract (test_r505:114-121) hashes the canonical
reconstruction (body minus the self-asserted field), NOT raw file bytes. Raw-byte
sha differs by serialization whitespace; the contract check passes (pins 39+1 green,
`_freeze_check` OK pre- and post-run). Post-harvest hardening note: future freezes
should pin raw bytes too. Corpus content unchanged: embedded `1e4a593f…`, n=21,
single freeze commit `80a4a759`.

## DEV measurement (this round, instrument 2.1.0, ring xkiro, production path)

- Harness: `scripts/r510_a2_dev_rerun.py` (new R510 wrapper; reuses r505's frozen
  functions unedited; outputs to `R510/A2_V42_XKIRO_RERUN/` per placement law).
- Identity gate: deployed `d7520b9b`, instrument files absent from worktree diff — OK.
- Result 21/21 verdict-class, zero transport failures:
  TPR **0.6 (6/10)** / FPR **0.0 (0/4)** / coverage **0.65** / parse **0.9556** /
  rule45 **7 firings** → **NOT_CALIBRATED** (`tpr_min`, `coverage_min` unmet).
- Vs R505 (xkiro, same instrument): TPR 0.5455 (6/11) / FPR 0.0 / coverage 1.0 /
  rule45 3. Denominator 10-vs-11 is the measured EVALUATION_FAILED exclusion on one
  case this run; the rest is the documented xkiro line-coherence flakiness (1-3
  cases/run, R495/R509 records). Same verdict class, same bar distance. No
  calibration claimed; seal stays refused.

## v4.3 lever (DESIGN ONLY — code post-harvest per stop-list)

R505's typing stands: the gap is ring-engagement-bound, and rule45 fired 7x here
(vs 3x at R505) yet TPR moved 0.5455→0.6 only. The v4.3 lever: a
degenerate-response detector — an attack batch with all-PASS verdicts, sub-second
latencies, and zero computed derivations types `ATTACK_INDEPENDENCE_UNAVAILABLE`
for the batch (Art. XLV) instead of letting lazy rings vote survival. Design only;
implementation rides the post-harvest attacker-sealing change (Part 3.3), measured
on DEV against these two runs as baseline.

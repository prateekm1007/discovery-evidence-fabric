# R11 AUDITOR VERDICT — AMENDMENT 27 (2026-11-16): R28 @ d8ee3be06 — cross-check ruled; feasibility 0.556, closest yet
Auditor: session auditor (Claude). Companion: eval/auditor_r28_adjudication.json. Builder OFF audit branch.

## VERDICT
**Gate NOT_MET.** Auditor re-judgment of all 18 intervention rows (V7 frozen + V7.1 tuned): **novelty Δ 2.444 PASS / feasibility |gap| 0.556 CI [0.249, 0.862] FAIL** — the closest the machine has been on the full intervention set. The machine cross-check's **novelty read is CONFIRMED** (2.389 vs 2.444); its **feasibility read is REJECTED as uncalibrated**.

## 1. Tolerance ruling (AM26 D2) — the divergence adjudicated from bytes
8/18 rows diverge by ≥2 on feasibility. The machine assigns **F_A=1 (infeasible)** to pure firmware/procedure changes on existing hardware: bench-p10 (existing inverter + catalog timer relay + firmware duty cycle), dev-fu-005 (install stress-relief cycling, no parts), eval-new05 (BMS balancing schedule), eval-sofc-redox (gas sequencing on the existing manifold). Those are procurable by construction; F_A=1 is indefensible against the bill bytes. **Ruling: the machine judge remains a cross-check INPUT (Art. XXVI); its feasibility axis must be calibrated before it can drive any gate (F39).** Its novelty axis is sound and is credited.

## 2. Auditor self-correction — the machine caught what I missed
**bench-p06**: my AM26 pilot scored gap 0. Re-reading the bytes, a **dead-end main has no second supply path — it cannot reverse flow**. The premise is flawed; corrected to gap 2. The machine flagged this (F_A=1) and was directionally right. Typed forward-only correction; the pilot score stands as history.

## 3. F38 — a new constraint-fit defect class
**bench-p10 PV-PID** proposes an 8h-on/4h-off duty cycle: that is **~33% daily energy curtailment**, entirely unpriced in its burden ledger (which counts only PLC wiring hours). Novelty is real; the operational cost is hidden. **The burden ledger must price operational losses, not just hardware** — otherwise "parity" is asserted while the plant loses a third of its output.

## 4. Where the residual feasibility gap lives
Adjudicated gaps: 10 rows at 0 (pure procedure/firmware/catalog-part changes), 7 rows at 1 (micro-roughened vane, micro-dimple MEMS, silica interlayer lamination, Al-on-steel sleeve bond, silica packet compatibility, added pressure-sensor channel, graded glass co-firing), 1 row at 2 (bench-p06 premise flaw). **The path to ≤0.25 is now concrete: eliminate the premise-flawed row and convert the seven "surface/bond/interface development" rows into pure catalog-part or procedure changes.**

## 5. Gold-set self-check: 10/10; 18-row re-judged; one self-correction typed.

## 6. Ledger delta
F38 opened (unpriced operational curtailment); F39 opened (judge feasibility axis uncalibrated); F30 updated (0.556, closest yet); V27. Progress 63–70%.

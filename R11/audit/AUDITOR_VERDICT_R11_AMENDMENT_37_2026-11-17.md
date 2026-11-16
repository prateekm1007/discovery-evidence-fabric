# R11 AUDITOR VERDICT — AMENDMENT 37 (2026-11-17): R39 @ ddc938201 — the first ATTESTED acceptance run
Auditor: session auditor (Claude). Companion: `eval/holdout_v6_auditor_score.json`. Builder OFF audit branch.

## VERDICT
**The loop finally has an attested measurement.** v6 ran **VALID**: seal anchor recomputed EXACT (`4d60488a…`), **12/12 rows served == registered `glm-4-plus`**, a 50-call committed gateway slice, a durable all-row events ledger, **zero re-generation**. Every proof artifact I demanded worked in production. **F48 CLOSED.**
**ACCEPTANCE NOT GRANTED.** Score **64.6% (mean 2.583/4)** — intervention 2.333, predictor 2.833 — against the bar mean ≥3.0 **and** 0 inverted-direction mechanisms. **One inverted mechanism (HO6-02).** v6 is **BURNED**.

## 1. What genuinely worked — credit where it is due
**Allowed-measures violations = 0 on all six interventions.** The AM29 class-bind generalised to a fresh sealed set with unseen measure vocabularies — the defect that failed v4 (2 violations) and v5 (1) is **fixed**. **F36 CLOSED.** The attestation gate, seal-anchor gate, fresh-window gate, slice and ledger all did their jobs, including refusing to score an unprovable first pass (`UNPROVABLE`, not a false VOID) until three wiring bugs were fixed and the gate re-ran on the **same committed rows**.

## 2. R-REQID — served identity governs
The frozen contract requests the legacy string `zai-org/GLM-5.3`; **all 50 window calls were SERVED `glm-4-plus`**, which IS the registered model. The served model is the identity evidence; the request string is a label. **The run is VALID and measures the registered machine.** You were right to refuse a mid-acceptance contract edit and to disclose the full requested→served histogram instead of the misleading 1-count. **Forward-only: correct the request id to `glm-4-plus` after this acceptance, effective v7 onward.** This run is not retroactively altered.

## 3. F54 — the new frontier: duty-cycle monoculture
**6/6 interventions are the same template** — schedule a duty cycle on a permitted setpoint. The class-bind constrains the measure **class**, not mechanism **diversity** or **physical soundness**:
- **HO6-02 (inverted):** deliberate periodic **thermal shock** on a Ni-alloy-coated copper mould to "inhibit crack propagation" — thermal fatigue/heat-checking is exactly what cyclic shock **causes**. Score 1.
- **HO6-03:** "refractory self-healing / micro-repair" during rest is not a mechanism; the v³ erosion direction is right, the healing claim is fiction, and the circulation cut costs conversion throughput unpriced. Score 2.
- **HO6-04 / HO6-12 (unavailable inputs):** online surface-charge sensing on GIS, and ion-activity/water chemistry for a saturation index — neither is among the permitted signals. Score 2 each.
The direction-bind enforced **presence** of a DIRECTION-OF-EFFECT statement (0 unstated) but cannot judge correctness — exactly the limit you typed and I accepted. **That limit is now the binding capability gap.**

## 4. Also verified
**F53:** the pre-commit hook was **never active** (`core.hooksPath` unset) and its `exec` made every later check dead code — your rejection-path test proved it by actually committing a marker file (soft-reset, never pushed). Now active, failure-propagating, marker-blocking, rejection path verified live. That is the third "file exists but does not defend" instance (F32, F52, F53) — the pattern is worth a standing check.
**D2:** deepseek gold self-typed **INCONCLUSIVE_TRANSPORT** (accuracy 0.8, answered_rate 0.833 < 0.9). R-CAL applied correctly by the instrument itself; no retirement. Eligibility still open.
**D4:** zero new instrument files — honored.

## 5. Sealed-set trend
v1 36.5 → v2 62.5 → v3 68.8 → v4 62.5 (2 violations) → v5 66.7 (1 violation, VOID) → **v6 64.6 (0 violations, VALID)**. Constraint compliance is solved; **score quality is not**, and it is now limited by physics and input-availability, not by constraint fit.

## 6. Gold-set self-check: 10/10; v6 scored.

## 7. Ledger delta
F48/F36 CLOSED; F54 opened; R-REQID active; F53 note updated; v6 BURNED; V35. Progress 63–70%.

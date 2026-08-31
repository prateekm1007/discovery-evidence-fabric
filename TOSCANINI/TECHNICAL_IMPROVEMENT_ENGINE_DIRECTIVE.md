# TECHNICAL IMPROVEMENT ENGINE — Standing Architectural Directive

**Source:** CEO research audit (2026-08-31 session) — Accelerated
Understanding public material + Anandkumar research lineage (FNO, PINO,
Geo-FNO, LocalNO, EGNO, catheter inverse design, quantum-control inverse
design, lithography self-training, incremental FNO, conformal
uncertainty, FourCastNet, NeuralOperator, MoleculeSTM/ProteinDT).
**Status:** Ratified as the NEXT major architectural objective — "a
major architectural objective, not a side feature."
**Constitutional anchors:** Art. XX (problem existence before mechanism
optimization), Art. XXVIII (no silent semantic promotion — simulation
output is never physical truth), Art. XXXIV (reality as the bottleneck),
Art. XXXVIII (reality boundary — AI may compute, may not claim reality).

---

## 1. The core thesis (CEO)

> **Turn physical understanding into a dense, DIRECTIONAL feedback
> signal, then use that signal to iteratively improve designs.**

Accelerated Understanding's loop: **Define → Simulate → Improve →
repeat**, with the model supplying a *direction of improvement*, not
merely an outcome prediction.

> "A discovery system becomes much more powerful when its evaluator can
> tell it not just WHETHER a candidate is good, but HOW to make the
> candidate better."

That is the missing bridge between the current engine and the target
system.

## 2. Toscanini's strategic opening (beyond AU)

AU is building **physical intelligence**. Toscanini can build
**discovery intelligence across evidence + physics + chemistry +
biology + engineering + failure knowledge + prior art + experiments**:

```
PROBLEM → EVIDENCE → MECHANISM → CANDIDATE → PRIOR ART →
FAILURE KNOWLEDGE → PHYSICAL/CHEMICAL/BIOLOGICAL EVALUATION →
DIRECTIONAL IMPROVEMENT → NEW CANDIDATE → RE-EVALUATION →
DECISIVE EXPERIMENT → REAL-WORLD RESULT → LEARNING
```

## 3. Where R377 already built the DIAGNOSTIC half

The R377 invention-quality instrument (I1–I5) is the seed of the
improvement loop — it converts "candidate is weak" into *which link is
weak and why*:

| Instrument dimension | Weakness it names | Improvement direction it implies |
|---|---|---|
| I1 MECHANISM_EVIDENCE_DERIVATION | span does not contain the mechanism's vocabulary | re-derive from a span that does (or retrieve better evidence) |
| I2 DIFFERENTIATOR_TECHNICAL_MEANING | surviving terms are generic configuration words | mutate toward specific technical vocabulary |
| I3 RECOMBINATION_RISK | every element known to some family; only the combination is new | add/replace an element in the meaningful residue; or accept and price it honestly |
| I4 NEW_TECHNICAL_RELATIONSHIP | every mechanism term-pair co-occurs in found art | recombine toward a genuinely new pair |
| I5 EXPERIMENT_DISCRIMINATION | experiment does not isolate the differentiator / is administrative | redesign the experiment around the surviving residue |

The **technical improvement engine** is the loop that CONSUMES these
diagnostics to propose mutations:

```
CANDIDATE 0 → EVALUATE (I1–I5 + engineering attack + collision)
→ WHY does it underperform? (weakest dimension, named)
→ DIRECTION OF IMPROVEMENT (mutation rule per dimension)
→ CANDIDATE 1 → RE-EVALUATE → ...
```

This is the lithography self-training pattern (CFNO mask optimization:
candidate → evaluate → identify error → modify → add information →
evaluate again) generalized beyond physics.

## 4. USE NOW (CEO list, mapped to current machinery)

1. **Constraint-aware reasoning (PINO pattern)**
   `OBSERVED EVIDENCE + KNOWN ENGINEERING CONSTRAINTS + KNOWN PHYSICAL
   LAWS + KNOWN FAILURE LIMITS + MODEL → CANDIDATE EVALUATION`.
   Partially present: the engineering attack checks stated constraints;
   the problem carries constraint text; the failure-analysis dimension
   ties failure rows to design controls. GAP to close: constraints are
   text-checked, not yet a structured evaluation input the improvement
   engine can compute against.

2. **Fidelity ladder**
   `cheap model → more detailed → expensive → experiment`.
   Partially present as pipeline economics: grid candidates (cheap LLM)
   → attack (cheap) → collision (search) → quality gate → experiment.
   GAP: the ladder is procedural, not a declared multi-fidelity policy
   with escalation rules; no simulation tiers exist yet.

3. **Directional improvement** — the I1–I5 table above is the
   diagnostic basis; the mutation rules are the R378+ build.

4. **Uncertainty calibration** — the engine already refuses to convert
   UNKNOWN (Art. XXV discipline throughout); conformal calibration
   applies once a simulation layer exists. Never treat simulation
   output as truth; report "improvement predicted with uncertainty X,
   inside/outside the calibrated envelope."

5. **Geometry/time-aware representations** — eventual technical state:
   objects + relationships + geometry + time + constraints (EGNO/Geo-FNO
   lesson: real inventions live on irregular geometry, not rectangular
   tensors).

## 5. BUILD LATER — the TECHNICAL IMPROVEMENT ENGINE subsystem

Interface (CEO):

```
INPUT:  candidate, constraints, objective, evidence,
        available simulator/model
OUTPUT: predicted behavior, failure modes, sensitivity map,
        limiting variables, improvement directions,
        candidate mutation, uncertainty
```

Evaluator menu (start cheap, no foundation model): existing numerical
solvers, open NeuralOperator models (MIT), domain simulators,
analytical equations, public pretrained models, simple differentiable
surrogates.

Reference demonstrations to study (CEO ranking):
- **AI-aided Geometric Design of Anti-infection Catheters** (the
  complete bridge: observation → mechanism → FNO model → optimization
  → geometry change → 3D-printed prototype → experiment; 1–2 orders of
  magnitude improvement reported) — study line-by-line; code:
  `zongyi-li/Geo-FNO-catheter`.
- **PINO** (data + physics constraints, even with limited data).
- **Geo-FNO** (irregular geometry, inverse design).
- **Lithography-guided self-training** (the self-improvement loop).
- **Conformal uncertainty for operators** (calibrated coverage).
- **NeuralOperator library** (the technical starting point — do NOT
  fork deprecated Geo-FNO/PINO repos).

## 6. DO NOT (CEO + constitutional)

- **Do not start training a giant physics foundation model.** Enormous
  distraction; prove the ARCHITECTURE OF IMPROVEMENT first with cheap
  evaluators (Art. XX: problem existence — the unproven claim is the
  loop, not the model).
- Do not fork deprecated repositories (Geo-FNO, old PINO).
- Do not treat company-reported claims (1T parameters, 35T experiments,
  >5T context) as independently reproducible benchmarks — Reuters notes
  AU has not disclosed enough for full outside validation. They are
  context, not evidence (Art. II).
- Do not let simulation output silently become physical truth (Art.
  XXXVIII reality boundary; loop_verification_state discipline).
- No REAL_LOOP_VERIFIED without external reality events — a
  differentiable surrogate is a COMPUTATIONAL_RESULT, rank 4.

## 7. Honest current-state note (2026-08-31)

R377 delivered the DIAGNOSTIC layer (I1–I5) and the honest kill gate
(SPAN_UNDERIVED ineligibility). The IMPROVEMENT layer (mutation rules
that consume I-diagnostics) does not exist yet — that is the next
cycle's build. The measured before/after evidence for R377 is in
TOSCANINI/R377_REPLAY_MEASUREMENT.json (Q 0.798→0.826, I 0.500→0.560,
Q4 0.75→1.0, I5 0.333→0.667 on the six survivors) and
TOSCANINI/R377_STRESS_TEST_MEASUREMENT.json (difficult fresh domains:
s7 2/5 underived excluded, m7 0/5, n7 5/5 → NO SURVIVOR — the honest
high-kill outcome; Lens monthly quota exhausted mid-cycle, disclosed).

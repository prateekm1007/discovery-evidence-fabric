# TECHNICAL IMPROVEMENT ENGINE — Standing Architectural Directive

**Source:** CEO research audit (2026-08-31 session) — Accelerated
Understanding public material + Anandkumar research lineage (FNO, PINO,
Geo-FNO, LocalNO, EGNO, catheter inverse design, quantum-control inverse
design, lithography self-training, incremental FNO, conformal
uncertainty, FourCastNet, NeuralOperator, MoleculeSTM/ProteinDT).
**CEO paper-verification audit (2026-08-31, second pass):** every core
citation resolves to a real publication (PINO arXiv:2111.03794; catheter
arXiv:2304.14554 = Science Advances 2024; quantum inverse design
arXiv:2608.03702; FourCastNet arXiv:2202.11214; MoleculeSTM/ProteinDT
confirmed). Audit corrections applied to the ANALYSIS (not this
directive, which never carried them): (1) VIMA is Google Brain robot
imitation learning — wrong lineage, removed from the source analysis;
(2) the quantum-control paper's relevance is ⭐⭐⭐ at most for Toscanini
(specialist molecular-QD domain, none of the 11 coded engineering
domains; the catheter paper already demonstrates the same inverse-
design+FNO principle in an engineering domain); (3) nine ⭐⭐⭐⭐⭐
ratings were inflated — the corrected top tier is catheter design,
PINO, and the Daedalus essay only.
**Status:** R378 BUILT AND MEASURED (see §8 — this ceased to be a
future-milestone spec when the CEO's same-session directive ordered the
first version built without a physics foundation model).
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

## 2. The strategic posture: INTEGRATION, not competition (CEO audit
correction 2026-08-31)

**Superseded framing (recorded for honesty):** an earlier draft of this
directive framed Toscanini as "going beyond Accelerated Understanding."
The CEO's audit rejected that posture, and this section now records the
corrected position.

AU is building a frontier physics foundation model at
trillion-parameter scale with hardware partnerships. Toscanini is
building a domain-agnostic epistemic and commercial layer. These operate
at different layers of the same stack; AU is not a competitor at any
stage Toscanini will reach in the next two years. The correct loop:

```
Toscanini selects the problem
→ Toscanini generates the engineering specification and kill condition
→ AU's physics model (or any simulator behind the evaluator contract)
  runs the simulation and provides directional feedback
→ Toscanini records the result as admissible evidence and generates
  the buyer package
```

**AU closes the experiment bottleneck. Toscanini closes the epistemic
and commercial bottleneck.** Anandkumar's own Daedalus essay identifies
both bottlenecks as real and distinct. Say that; do not say "beyond
them." (Investor-facing corollary: any angel who has read the Reuters
piece will ask about AU positioning — the answer is integration.)

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

## 7. Honest current-state note (updated R378, 2026-08-31)

R377 delivered the DIAGNOSTIC layer (I1–I5) and the honest kill gate
(SPAN_UNDERIVED ineligibility). **R378 delivered the IMPROVEMENT layer
itself** — CEO same-session directive: "Build the first version WITHOUT
a giant physics foundation model":

- `discovery_fabric/engine/evaluator_contract.py` — the pluggable
  evaluator interface (CEO list item 15): registered evaluators declare
  a fidelity tier (TERM_RULE → STRUCTURED_CONSTRAINT →
  NUMERICAL_SOLVER / SIMULATION / NEURAL_OPERATOR → EXPERIMENT) and an
  evidence rank; **EXPERIMENT-tier registration is structurally
  refused** (Art. XXXVIII — no software evaluator may produce
  physical-observation evidence); the first live implementation is the
  deterministic TermRuleEvaluator (the I1–I5 instrument consumed
  read-only, converted into named limiting features + improvement
  directions). This is also **the NeuralOperator integration point**
  (CEO audit item 3): a future operator/solver registers behind
  `register_evaluator(...)` and the mutation loop consumes it without
  any other change — later simulators are OPT-IN, never a silent
  upgrade of the diagnostic baseline.
- `discovery_fabric/engine/improvement_engine.py` — the loop:
  DIAGNOSE (deterministic) → PROPOSE (LLM, an UNTRUSTED proposer under
  Art. XVIII) → VALIDATE (deterministic gates: verbatim span, type
  trigger, no-op, residue-vs-found-art, baseline reference) → APPLY
  (child candidate with the full Art. XXXVIII causal chain
  ORIGINAL → DIAGNOSTIC → MUTATION → NEW CANDIDATE, parent/child
  hashes, negatives carried) → RE-EVALUATE (span re-measured,
  prior-art coverage re-adjudicated REPLAY_CACHE/LIVE, both instruments
  re-run — no inherited scores) → KEEP OR KILL (targeted-dimension
  improvement, structural-flag clearing, negatives preservation,
  no UNKNOWN-conversion, no prior-art degradation, anticipated-child
  rejection) → REPEAT with DIRECTIONAL FEEDBACK (deterministic
  rejection reasons travel into the next proposal's prompt).
- **PINO pattern (CEO audit item 2)**: the evaluator's
  CandidateContext carries `spec + decisive + problem +
  evidence_items + collision + attack` — evidence + known constraints +
  known failure limits + the candidate model — and every improvement
  instruction is expressed as a constraint the mutation must satisfy
  (e.g. "the span must CONTAIN the mechanism's vocabulary",
  "residue only against FOUND art"). Constraint-aware candidate
  reasoning is the operating rule of the loop, not a future item.
- **Fidelity ladder (CEO audit item 1)**: declared as first-class
  architecture in the evaluator contract (see
  TOSCANINI/ADR_R378_FIDELITY_LADDER.md). The cheap tier screens
  candidates BEFORE any expensive escalation; the CEO's
  cost-ordering rule is implemented as a declared threshold
  (MAX_PROPOSALS_PER_ITERATION, MAX_ITERATIONS_DEFAULT) plus the
  metered-source guards.
- Integrated in the production post-rank pipeline (run.py
  `_improvement_pass`): IMPROVED replaces the candidate with fully
  rebuilt attack/quality artifacts; a no-defensible-improvement verdict
  KILLS the candidate before packaging (CEO rule 9); transport failure
  is honest IMPROVEMENT_BLOCKED_TRANSPORT, never a research verdict.
- PatentBear (CEO-designated patent source) wired opt-in behind the
  collision ladder with a persistent provider-metered quota guard and
  reserve floor — refusals recorded as errors, never absence.

**Measured (R378):** controlled replay on the six fresh-domain
survivors — aggregate I 0.560 → 0.728 (I1 +0.347 mean), Q 0.826 →
0.799 (honest regression: harder adjudication + instrument reading the
mutation's genuine span evidence), 9 mutations kept across 11
iterations, 4 IMPROVED / 2 honest KILLED (one because the mutation
introduced a new structural flag — the invariant worked). Adversarial
live demonstration (w7, offshore wind blade leading-edge erosion, fresh
domain): full live loop, PatentBear spent to its reserve floor mid-run
(honest UNRESOLVED), improvement pass ran with one KEEP (I1 0.158 →
0.5) and an honest kill on iteration 2.

**CEO audit four-item status (2026-08-31 second-pass audit):**
1. Fidelity ladder as an architectural decision record — DONE
   (ADR_R378_FIDELITY_LADDER.md; the evaluator contract declares the
   tiers as code).
2. PINO pattern absorbed into candidate reasoning — DONE (the
   constraint-carrying CandidateContext + validation gates).
3. NeuralOperator library as the integration point — DONE
   (register_evaluator; documented in §7 above).
4. TIE as a future milestone spec — SUPERSEDED by the CEO's
   same-session build directive; built and measured in R378. This
   document is the standing record of both.

Honest limits (unchanged in kind): the LLM proposer is nondeterministic
(single-run outcomes vary between IMPROVED and honest KILL — disclosed
in the replay artifact); REPLAY_CACHE re-adjudication is bounded by the
domain-abandonment guard (a mutation that leaves the problem domain
invalidates the cache — a LIVE search or honest UNRESOLVED is required);
simulation tiers do not exist yet (the contract reserves them); no
REAL_LOOP claims (Art. XXXVII/XXXVIII).

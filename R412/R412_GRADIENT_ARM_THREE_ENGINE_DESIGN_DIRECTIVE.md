# R412 Gradient Arm — Three-Engine Design Directive (PRE-SEAL DESIGN)

**Status:** DESIGN DIRECTIVE — not a preregistration. Nothing in this
document is sealed. The gradient arm becomes an experiment ONLY when
its machinery + tests + preregistration artifact are committed BEFORE
its first model call (Art. LIX), exactly as the temporal arm was
sealed at cb1c09fa. No gradient-channel model call may occur while
this file is the only gradient artifact.

**Owner directive (2026-09-06):** the "30 Years Later" operator is
upgraded from one engine (temporal evolution) to three engines:
Future Evolution, Frontier-to-Laggard Transfer, and Capability
Backcasting — with a Technology Velocity Map (TVM) as shared
infrastructure and Latent Invention Recovery Yield (LIRY) as the
headline metric.

**Relationship to the sealed temporal arm (21d36e71):** the sealed
experiment is COMPLETE with the honest result 0/13 (13 temporal
projections, 0 present-capability rediscoveries, 0 incomplete
transports). Its artifact is never retro-edited. It stands as the
TEMPORAL CONTROL ARM. The gradient arm is a separately sealed
experiment against the same frozen population; LIRY is reported per
channel and combined.

---

## 1. Why the gradient channel is structurally different

The temporal channel asks: "what would this become after 30 years of
progress in ITS OWN field?" — and the measured answer was: a
descendant whose capabilities do not exist today (27x
CAPABILITY_NOT_CLAIMED_TODAY) or are claimed present but
undemonstrable (NOT_EXIST_TODAY / REGIME_MISMATCH /
VERIFICATION_FAIL). The channel extrapolates FORWARD from the
candidate's own trajectory.

The gradient channel asks the opposite question: "which capability,
advancing fastest SOMEWHERE ELSE and demonstrably existing TODAY,
attacks the specific reason this candidate died?" It searches
SIDEWAYS across present-day capability space. The two channels
sample disjoint regions: the temporal channel's failure mode
(future-dependence) is precisely what the gradient channel refuses
to accept as an answer. This is the owner's constraint-driven
transfer, and the 0/13 result is the strongest argument for it: the
temporal channel found future progress; the gradient channel is
required to find PRESENT progress.

## 2. The gradient pipeline (constraint-driven, cheapest-kill-first)

```text
death record (verbatim reason, immutable)
  |
  v
[GA-1] limiting-capability extraction
  |      deterministic parse of the verbatim death reason into
  |      the named capability deficit + required operating values
  |      (LLM proposes with exact spans from the death reason;
  |      deterministic verbatim-containment gate verifies)
  v
[GA-2] gradient eligibility (sealed rules, see section 3)
  |      INELIGIBLE -> recorded, no model call spent
  v
[GA-3] TVM query (deterministic; NO LLM)
  |      rank measured fast-movers on the required capability rung
  |      NO measured fast-mover -> DEAD_AT_TVM_QUERY (cheapest kill:
  |      fabric calls only, no mechanism writing)
  v
[GA-4] capability backcasting per frontier candidate
  |      outcome -> capability -> technology -> physical mechanism
  |      -> manufacturing method -> control architecture -> materials
  |      -> computation -> measurement
  |      transfer the CAUSAL MECHANISM, never the industry label
  v
[GA-5] transfer feasibility vs the target constraint
  |      required assumptions listed; each needs a present-day
  |      anchor (Art. XLVI: a mechanism transferred is not novel
  |      merely because the domain changed)
  v
[GA-6] present-day capability test (REUSES the sealed verify
  |      instrument unchanged: distinctive-term coverage >= 0.5 AND
  |      regime token in the same record; transport failure is
  |      INCOMPLETE, never REJECTED - Art. LXI)
  v
[GA-7] new causal architecture? (deterministic + novelty taxonomy)
  |      NO -> cemetery lineage (collision-prone by construction)
  v
[GA-8] fresh collision search + novelty (the 5-class taxonomy;
  |      P0-2 early screen applies to descendants FIRST)
  v
[GA-9] temporal-family attacker (fresh context; RECOMBINATION_
  |      CHALLENGE first class; NOT_CALIBRATED caveat travels)
  v
normal invention pipeline entry (fresh candidate identity,
  nothing inherited but lineage)
```

Every stage has a typed failure state and a recorded reason. Stage
costs extend the R412 P1 waterfall with `tvm_query_cost` and
`backcast_transfer_cost`; the death stage records where each
candidate died (GA-1..GA-9), enabling the stage-cost economics
measurement over the gradient arm.

## 3. Gradient eligibility rules (to be sealed; drafted here)

Derived from the VERBATIM death reasons, not the bare category
labels (the sealed temporal eligibility classified on categories;
the gradient channel needs the capability-deficit axis):

- `physics` deaths: eligible ONLY where the violation is a
  CAPABILITY deficit (sensing resolution, control bandwidth,
  actuation force/precision, computation) — NOT where it is a
  regime/constants violation (e.g., C-heat_exchanger-1~4's Darcy
  regime violation and C-machining-1~4's boundary-condition
  inversion are internally-inconsistent or regime-invalid deaths;
  a frontier capability cannot repair an inconsistency).
- `engineering` deaths: eligible where the frontier can supply the
  missing control/measurement/actuation capability (C-wind-2's
  10-100x misalignment-vs-deflection gap is the strongest gradient
  candidate in the corpus — an actuation/control problem).
- `baseline` deaths: eligible where the limiting quantity is a
  device-technology parameter on a measured trajectory (the
  C-power_electronics-1 Esw/SiC-GaN case, as the temporal arm
  already classified).
- `prior_art` deaths: SPECIAL ROUTE only — the transfer must yield
  NEW_CAUSAL_ARCHITECTURE / NEW_MECHANISM, then a fresh collision
  search; a better implementation of the colliding mechanism is
  not enough.
- `evidence` deaths: INELIGIBLE (no established technological death
  cause to attack).

Population: the SAME 13 attempted targets (7 eligible + 6 special
route) from the sealed population; the 386 ranked-out candidates
remain present-day rejections WITHOUT a technological death cause
and are not gradient-eligible (evolving them would manufacture a
death cause). The 500-seeds framing is directionally right; the
honest denominator is 13 (reported with /14 and /400 as context,
exactly as the sealed funnel does).

## 4. Technology Velocity Map (TVM) — evidence-native

Schema per entry: `domain`, `capability_rung`, `indicator`
{metric, value, unit, window}, `source` {record_id, citation,
retrieved_at}, `provenance` {span, verified_verbatim: true},
`confidence`. NO LLM-asserted numbers. Construction reuses the
R411 F4a instrument pattern: an untrusted LLM (SEPARATE_CONTEXT_
ONLY, never labelled independent) proposes (domain, rung,
indicator, value, window, record) bindings with EXACT QUOTED
SPANS; a deterministic gate verifies verbatim containment in the
retrieved pool; failed spans count as nothing. Frontier ranking is
per rung, computed from measured slopes only.

v0 scope discipline: the map covers the capability rungs the corpus
actually names (sensing: FBG strain, on-die TSEP, operando Raman;
actuation: piezo-hydraulic, MR-fluid; control: MPC at switching
timescale, higher-order sliding mode; computation: edge >= 50
MFLOPS < 50 ms; materials: SiC/GaN at drive ratings; manufacturing:
CMP closed-loop bandwidth) x the domains the fabric retrieves
performance-trend records for. The map GROWS per campaign as death
records name new rungs. Domain-neutrality by construction: no
fixed industry list exists; the frontier set is re-derived per
rung from measured slopes (Art. XLIII / LXIX).

Fast-to-slow asymmetry is a SEARCH-ORDER policy over the ranked
map (steepest measured slope first), never a hard-coded belief
about industries.

## 5. The phantom-arbitrage guard (absence evidence)

The transfer is interesting only in the third case: the frontier
capability COULD apply, the physics does not forbid it, and the
target domain HAS NOT imported it. "Has not imported" must be
evidenced, not asserted: a retrieved target-domain record (recent
review/survey/state-of-the-art) that names the limitation WITHOUT
the imported capability. No such record -> the absence claim is
UNKNOWN (Art. XXI.2 / XXV) and the transfer cannot promote on it.

## 6. Metrics

- `LIRY` (headline): survivors of the full normal pipeline /
  gradient-eligible attempted; reported per channel (temporal,
  gradient, dual), per death category, with the raw denominator
  reported alongside (no hiding failures in eligibility
  filtering).
- `LIRY per unit cost`: pairing the yield with the extended
  stage-cost waterfall (Art. LVI — information gain per cost).
- TVM coverage: rungs with >= 1 measured entry; domains per rung.
- All verdicts carry reviewer_provenance = AI_REVIEW (Art. LXVII).

## 7. Sequencing (prerequisites before the gradient run)

1. Machinery + tests + preregistration committed BEFORE the first
   gradient model call (Art. LIX; the Phase 9 pattern).
2. The P0-2 early collision screen applied to GA descendants
   before mechanism writing (transfer candidates are
   collision-prone by construction — the R411 self-defeating-
   collision lesson).
3. The attacker NOT_CALIBRATED caveat (measured FPR 0.8,
   universal-kill) travels with every GA-9 verdict, OR the
   attacker calibration repair lands first (owner decision).
4. Zero is an acceptable outcome; no quota (Art. LXVIII).

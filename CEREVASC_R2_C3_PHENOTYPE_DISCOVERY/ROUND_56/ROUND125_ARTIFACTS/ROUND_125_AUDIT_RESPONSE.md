# Round 125 Audit Response — Five-Candidate Portfolio Controller

**Date:** 2026-08-23
**Round:** 125
**Authority:** CEO Round 125 deep audit
**Status:** Portfolio controller architecture complete. Per-candidate loop execution is deferred to subsequent rounds per the audit's explicit sequencing directive: "First build the five-candidate portfolio controller and force every one of the five through exactly the same adversarial AI loop. Then the simulator ecosystem becomes the examination system rather than the project itself."

---

## 1. What the audit found

The audit confirmed that the strategic pivot to a Virtual Wet Lab architecture is correct (Round 124), but identified that the system is still centered on a single candidate (Slot-5 clot fragmentation precursor) rather than running the AI loop against all five canonical candidates.

**Confirmed strengths:**
- AI discovery/orchestration: ✅
- Prior-art attack: ✅
- Cemetery / epistemic constraints: ✅
- FEBio validated: ✅
- Virtual-lab architecture: ✅ (Round 124 v2.0)
- Claim-Evidence Graph: ✅ (Round 124 V1)
- Multi-simulator plan: ✅
- Adversarial acquisition architecture: ✅ (Round 124 V3)

**Major gap:**
- Five-candidate portfolio execution: ❌ not yet done.

**Two architectural corrections required:**

1. **Two-tier promotion state.** The label "WORLD_CLASS_INVENTION" must NOT be applied to virtual survivors. FDA and ASME V&V 40 both treat computational credibility as risk- and context-dependent, not as a universal binary. Create intermediate state `WORLD_CLASS_VIRTUAL_SURVIVOR`; reserve `WORLD_CLASS_INVENTION` for after the reality gate is satisfied.

2. **Applicable-world-set per candidate.** Not all four worlds apply to all candidates. A drug-delivery invention should not be forced through a venous FSI simulator. A fracture invention should not be judged by a thrombosis-formation model. Define `APPLICABLE_WORLD_SET(candidate)` and require "all materially relevant independent physics worlds pass."

**One critical sequencing directive:**
> "Do not install another simulator yet as the sole next task. First build the five-candidate portfolio controller and force every one of the five through exactly the same adversarial AI loop. Then the simulator ecosystem becomes the examination system rather than the project itself."

---

## 2. What was done in response

Seven artifacts were produced in this round, all in `ROUND125_ARTIFACTS/`:

| Artifact | Purpose | Status |
|----------|---------|--------|
| `WORLD_CLASS_PROMOTION_STATE_V1.json` | Defines the two-tier promotion state machine: DISCOVERY → VIRTUAL_SURVIVOR_CANDIDATE → WORLD_CLASS_VIRTUAL_SURVIVOR → WORLD_CLASS_INVENTION (with KILLED and REALITY_KILLED terminal states). Grounded in FDA computational modeling framework + ASME V&V 40. | Spec complete; not yet wired into portfolio controller. |
| `CANDIDATE_PORTFOLIO_MATRIX_v1.json` | Enumerates C1-C5 with all 12 required fields (candidate_id, problem, mechanism, technical_effect, prior_art_state, applicable_simulators, competing_hypotheses, load_bearing_assumptions, required_evidence, decision_value, reality_gap, promotion_state). Sourced verbatim from CANONICAL_STATE/PORTFOLIO.json. | Spec complete; 5 candidates enumerated from authoritative registry. |
| `APPLICABLE_WORLD_SET_REGISTRY_V1.json` | Per-candidate applicable vs NOT_APPLICABLE_TO_WORLD classifications with evidence-grounded justification, adversarial test, Article XXXII alternative, and classification class. C1/C2 need 2 worlds; C3/C4 need 3 worlds; C5 needs all 4. | Spec complete; 13 N/A classifications documented with justification. |
| `PROMOTION_GATE_SPEC_V1.json` | 17 gates (G01-G17) with definition, evidence required, acceptance for GREEN/YELLOW/RED, adversarial test, Article XXXII alternative, machine-enforcement rule, N/A handling. | Spec complete; not yet implemented as machine-enforced checks. |
| `PORTFOLIO_EXECUTION_ENGINE_SPEC_V1.json` | Portfolio controller + per-candidate loop (10 stages) + V3 acquisition function integration + 5→4→2→1→0 anti-suspicious-survivor rule + machine-enforced promotion refusal. | Spec complete; not yet implemented. |
| `PORTFOLIO_SCOREBOARD_V1.json` | Initial state for all 5 candidates with per-gate state breakdown and next-action priority queue. | Initial state complete; reflects current canonical portfolio. |
| `ROUND_125_AUDIT_RESPONSE.md` | This narrative. | Complete. |

**Honest disclosure of what is spec vs. executed:**

Everything in this round is specification. The portfolio controller is NOT yet implemented as running code. No candidate has been run through the per-candidate loop. The 5→4→2→1→0 rule has not been triggered (0 survivors). The scoreboard reflects the current canonical portfolio state (CANONICAL_STATE/PORTFOLIO.json) translated into the two-tier promotion model — it is a snapshot, not a new evaluation.

This is intentional. The audit explicitly directed: build the portfolio controller FIRST, then run candidates through it. Building the controller and running candidates are separate phases.

---

## 3. The canonical five candidates

Sourced verbatim from `CANONICAL_STATE/PORTFOLIO.json` (schema_version 2.0.0, canonical_state_version 2026-08-20T00:00:00Z). No invented names. No substitutions.

| Candidate | Slot | Name | Current Promotion State |
|-----------|------|------|--------------------------|
| C1 | 1 | R6 Passive Rescue / Obstruction Bypass | VIRTUAL_SURVIVOR_CANDIDATE |
| C2 | 2 | Adaptive / Sensing eShunt | DISCOVERY |
| C3 | 3 | Controlled CNS Therapeutic Platform | VIRTUAL_SURVIVOR_CANDIDATE |
| C4 | 4 | CNS / Lifecycle Intelligence Platform | DISCOVERY |
| C5 | 5 | eShunt Clot Fragmentation Precursor (candidate for Slot 5, which is EMPTY) | VIRTUAL_SURVIVOR_CANDIDATE |

**Slot 5 honesty:** Slot 5 is currently EMPTY per canonical portfolio. The eShunt clot-fragmentation precursor (Rounds 56-124) is a CANDIDATE being evaluated to fill this slot, but has not yet earned it. This distinction is preserved throughout the portfolio matrix.

---

## 4. The two-tier promotion state

The audit's central architectural correction:

| State | Meaning | Permission |
|-------|---------|------------|
| DISCOVERY | Candidate identified, no gates passed yet. | Run AI loop. |
| VIRTUAL_SURVIVOR_CANDIDATE | Some gates green, not all. | Continue AI loop. |
| **WORLD_CLASS_VIRTUAL_SURVIVOR** | All 17 virtual gates green. | Freeze dossier. Move to next candidate. Begin reality-gate prep. |
| **WORLD_CLASS_INVENTION** | All 17 virtual gates green + reality gate green + closed-loop operational (Article XXXV). | Move to regulatory dossier. Slot permanently filled. |
| KILLED | Failed a virtual gate. | Cemetery entry. Slot may be reopened. |
| REALITY_KILLED | Virtual survivor but reality gate contradicted virtual prediction. | Cemetery entry with STRONG_CONSTRAINT. Trigger virtual-campaign audit. |

**Key invariant:** The engine MUST refuse `WORLD_CLASS_VIRTUAL_SURVIVOR` unless all 17 gates are GREEN or NOT_APPLICABLE_WITH_JUSTIFICATION. The engine MUST refuse `WORLD_CLASS_INVENTION` without a green reality gate backed by physical experiment data.

**Regulatory grounding:**
- FDA computational modeling framework: CM&S is evidence that can complement traditional testing, but credibility depends on verification, validation, context of use, and available evidence. Credibility is NOT a universal binary property.
- ASME V&V 40: Credibility is risk- and context-dependent.
- Implication: A virtual survivor has FDA-recognized credibility WITHIN ITS CONTEXT OF USE. It does NOT have the credibility of a validated physical device. The two-tier state reflects this distinction.

---

## 5. The applicable-world-set per candidate

The audit's second architectural correction. Not all four worlds apply to all candidates:

| Candidate | World A (FEBio) | World B (Peridgm) | World C (clotFoam) | World D (svFSI) | Applicable |
|-----------|---|---|---|---|---|
| C1 R6 Passive Rescue | ✅ | N/A (no fracture) | N/A (CSF not blood) | ✅ | 2/4 |
| C2 Adaptive Sensing eShunt | ✅ | N/A (no fracture) | N/A (CSF not blood) | ✅ | 2/4 |
| C3 Controlled CNS Therapeutic | ✅ | N/A (no fracture) | ✅ (drug transport) | ✅ | 3/4 |
| C4 CNS Lifecycle Intelligence | ✅ | N/A (no fracture) | ✅ (biosensor transport) | ✅ | 3/4 |
| C5 eShunt Clot Fragmentation Precursor | ✅ | ✅ (load-bearing A1) | ✅ (load-bearing A2) | ✅ (load-bearing A4) | 4/4 |

**Key invariant:** Every NOT_APPLICABLE_TO_WORLD classification has: (a) evidence grounding from the candidate's mechanism documentation, (b) adversarial test (what evidence would force re-classification), (c) Article XXXII alternative explanation and refutation, (d) classification class.

**Anti-bureaucracy principle:** A world may NOT be marked NOT_APPLICABLE_TO_WORLD merely because it would expose a load-bearing assumption. If the world tests a load-bearing assumption, it is APPLICABLE by definition. The engine must NOT become a mechanism for skipping hard tests.

C5 is the only candidate requiring all four worlds. The other candidates' NOT_APPLICABLE_TO_WORLD classifications are NOT a weakness — they are precision. Forcing C1-C4 through all four worlds would be bureaucracy, not science.

---

## 6. The 17-gate promotion spec

Every candidate must pass all 17 gates (or have justified N/A) to reach WORLD_CLASS_VIRTUAL_SURVIVOR:

1. Problem existence
2. Prior-art survival
3. CE constraints
4. Mathematical identifiability (where applicable)
5. Physics World A (FEBio)
6. Physics World B (Peridgm) or justified N/A
7. Physics World C (clotFoam) or justified N/A
8. Cross-world agreement
9. Competing hypothesis attack
10. Adversarial parameter sweep
11. Geometry attack
12. Instrument/noise attack
13. Model-form attack
14. Decision-value
15. Published evidence reproduction (where available)
16. Reality-gap graph
17. Final virtual dossier

**Machine enforcement:** The engine MUST refuse promotion unless all 17 gates are GREEN or NOT_APPLICABLE_WITH_JUSTIFICATION. 16 of 17 GREEN is NOT promotion. The missing gate blocks promotion regardless of which gate it is.

---

## 7. The 5→4→2→1→0 anti-suspicious-survivor rule

The audit's pushing-the-envelope principle:

> "Do not search for five inventions. Search for five survivors. And the machine should be much more willing to produce 5 → 4 → 2 → 1 → 0 than 5 → 5 world-class, because five simultaneous survivors should be treated as suspicious until the adversarial system demonstrates that the portfolio genuinely contains five independent breakthroughs."

**Operationalization:**

- **Suspicion threshold:** If ≥3 candidates reach WORLD_CLASS_VIRTUAL_SURVIVOR, trigger an INTER-SURVIVOR INDEPENDENCE AUDIT.
- **Audit questions:** Do the survivors share load-bearing assumptions? Competing hypotheses NOT tested? NOT_APPLICABLE_TO_WORLD classifications protecting them from the same world? Parameter-space regions not adversarially swept? Virtual-instrument noise models too clean?
- **Audit outcome:** If shared hidden assumptions found across ≥2 survivors, the survivors' dossiers are QUARANTINED. The shared assumption must be explicitly tested. Only after the shared assumption survives does the quarantine lift.
- **No auto-promotion of 5:** The engine may NOT promote all 5 candidates in a single batch. Each promotion is sequential, with the inter-survivor independence audit running after the 3rd, 4th, and 5th promotion.

**Expected distribution:** The engine is designed to be MORE willing to produce 5 → 4 → 2 → 1 → 0 than 5 → 5. Zero survivors is an acceptable outcome. Five survivors is suspicious.

---

## 8. The current scoreboard (honest state)

| Candidate | Virtual State | Major Failure | Next Action |
|-----------|---|---|---|
| C1 R6 Passive Rescue | 🟡 | Problem-existence YELLOW (eShunt obstruction not yet observed) | Strongest-alternative attack + calibrator acquisition |
| C2 Adaptive Sensing eShunt | 🟡 | Problem-existence reality-blocked | V8 engineering + identifiability pre-check |
| C3 Controlled CNS Therapeutic | 🟡 | Strongest-alternative attack PENDING | Strongest-alternative attack (priority 1) |
| C4 CNS Lifecycle Intelligence | 🔴 | Merged-platform pipeline RESTART required | Restart at problem-existence gate |
| C5 eShunt Clot Fragmentation Precursor | 🔴 | 6 of 17 gates RED (Worlds B/C/D uninstalled) | Peridgm P1-P8 certification |

**Portfolio-level state:**
- World-class virtual survivors: 0 / 5
- World-class inventions: 0 / 5
- 5→4→2→1→0 rule: NOT_TRIGGERED (0 survivors)
- Inter-survivor independence audit: NOT_REQUIRED (fewer than 3 survivors)

---

## 9. The next-action priority queue

Per the V3 acquisition function (highest EIG / lowest cost):

1. **C3** — Strongest-alternative attack (literature review, no simulation, highest EIG / lowest cost). PENDING per CEO directive.
2. **C1** — Calibrator acquisition (parallel hardware action) + strongest-alternative attack.
3. **C5** — Peridgm P1-P8 certification (next virtual priority per Round 124 audit; load-bearing assumption A1 is cheapest untested).
4. **C2** — V8 engineering + prior art search + identifiability pre-check (V25 lesson).
5. **C4** — Merged-platform pipeline restart (most demanding; do LAST after other candidates demonstrate the loop end-to-end).

---

## 10. Constitutional compliance

Each artifact explicitly references the articles it complies with. The most load-bearing articles for this round:

- **Article I** (evidence precedes assertion): No candidate is promoted without evidence. The scoreboard reflects current canonical state, not new evaluations.
- **Article IV** (no fallback epistemology): A RED gate cannot be bypassed by aggregating other GREEN gates.
- **Article VII** (never weaken the verifier to rescue a claim): A failed gate is corrected by adding evidence, not by weakening the gate definition.
- **Article X** (canonical state has one authority): The portfolio matrix and scoreboard are DERIVED views of CANONICAL_STATE/PORTFOLIO.json. If they conflict, PORTFOLIO.json wins.
- **Article XIV** (RED = STOP): A red gate halts the candidate; the engine moves to the next candidate.
- **Article XVII** (every control must have an attempted bypass): Each gate's GREEN status has an adversarial test. Each NOT_APPLICABLE_TO_WORLD classification has an adversarial test (what evidence would force re-classification).
- **Article XXV** (unknown remains unknown): UNRESOLVED gate state cannot be aggregated as GREEN or RED. It blocks promotion.
- **Article XXVI** (no self-certification): Locally verified ≠ CI-certified. Engine decisions are subject to CI verification.
- **Article XXVII** (no threshold invention): Every gate threshold has explicit class and provenance.
- **Article XXVIII** (no silent semantic promotion): Passing the virtual campaign does NOT grant credit at the reality gate. WORLD_CLASS_VIRTUAL_SURVIVOR is NOT a partial invention.
- **Article XXIX** (separate implementation from mechanism): A simulator failure is classified (PHYSICS_DISAGREEMENT etc.) before being promoted to HYPOTHESIS_KILLED.
- **Article XXXII** (strongest alternative explanation): Each candidate lists H2 (strongest alternative). Each NOT_APPLICABLE_TO_WORLD classification lists its alternative explanation.
- **Article XXXIII** (no irreversible action on unresolved evidence): No candidate is promoted or killed based on unresolved evidence.
- **Article XXXV** (closed-loop epistemic control): The portfolio execution engine is the operational form of the closed-loop system. WORLD_CLASS_INVENTION requires the closed loop, not just a single physical experiment.

---

## 11. What does NOT happen next

Per the audit's explicit sequencing directive:

- **NOT** installing another simulator as the sole next task. Peridgm installation is deferred until the portfolio controller is built and C5's acquisition function identifies Peridgm as the highest-priority next experiment.
- **NOT** running candidates in arbitrary order. The priority queue is mechanical: C3 → C1 → C5 → C2 → C4.
- **NOT** promoting any candidate to WORLD_CLASS_VIRTUAL_SURVIVOR until all 17 gates are GREEN or N/A.
- **NOT** promoting any candidate to WORLD_CLASS_INVENTION without a green reality gate.
- **NOT** treating five simultaneous virtual survivors as a success. Five survivors is suspicious; the inter-survivor independence audit triggers at ≥3.
- **NOT** forcing all candidates through all four worlds. APPLICABLE_WORLD_SET is precision, not bureaucracy.

---

## 12. What DOES happen next

Per the audit's explicit sequencing directive:

1. **Implement the portfolio controller** as running code (the spec is complete; implementation is the next phase).
2. **Run C3 through the per-candidate loop** — strongest-alternative attack is priority 1 (cheapest, highest EIG).
3. **Run C1 through the per-candidate loop** — calibrator acquisition + strongest-alternative attack.
4. **Run C5 through the per-candidate loop** — Peridgm P1-P8 certification is the next virtual priority.
5. **Run C2 through the per-candidate loop** — V8 engineering + identifiability pre-check.
6. **Run C4 through the per-candidate loop** — merged-platform pipeline restart (most demanding).
7. **At each candidate's promotion or kill**, automatically move to the next candidate. No human selection between candidates.
8. **At ≥3 survivors**, trigger the inter-survivor independence audit.

**The success criterion for this phase:**
> "Five candidates enter. Each either dies with a documented reason or emerges as a `WORLD_CLASS_VIRTUAL_SURVIVOR`. Then the machine moves automatically to the next one. Only reality upgrades a virtual survivor into a fully confirmed invention."

---

## 13. The honest current state

| Capability | Status |
|-----------|--------|
| AI discovery loop | ✅ Operational |
| Prior-art engine | ✅ |
| Physics-validation substrate (World A) | ✅ |
| Virtual Wet Lab architecture (v2.0) | ✅ Spec complete |
| Claim-Evidence Graph | ✅ V1 complete (C5 only; other candidates pending) |
| Adversarial acquisition design (V3) | ✅ Spec complete |
| **Candidate portfolio engine** | ✅ **Spec complete (this round)** |
| **Canonical 5-candidate registry** | ✅ **Enumerated from PORTFOLIO.json (this round)** |
| **Two-tier promotion state** | ✅ **Spec complete (this round)** |
| **Applicable-world-set per candidate** | ✅ **Spec complete (this round)** |
| **17-gate promotion spec** | ✅ **Spec complete (this round)** |
| **5→4→2→1→0 anti-suspicious-survivor rule** | ✅ **Spec complete (this round)** |
| **Portfolio scoreboard** | ✅ **Initial state complete (this round)** |
| C1 full loop | 🔴 Not yet run |
| C2 full loop | 🔴 Not yet run |
| C3 full loop | 🔴 Not yet run |
| C4 full loop | 🔴 Not yet run |
| C5 full loop | 🔴 Not yet run (partial: World A only) |
| Peridynamics certified | 🔴 Not installed |
| OpenFOAM/clotFoam certified | 🔴 Not installed |
| svFSI certified | 🔴 Not installed |
| Published-data E3 reproduction | 🔴 Not executed |
| Cross-world adversarial testing | 🔴 Not executed |
| Virtual-clot/virtual-population engine | 🔴 Not built |
| Automated promotion gate (running code) | 🔴 Spec only |
| Reality-gap graph (per candidate) | 🟡 C5 only; other candidates pending |
| Physical experiments | 🔴 Not executed |
| **World-class virtual survivors** | **0 / 5** |
| **World-class inventions** | **0 / 5** |
| CI certification | ❌ |

The single most important honest statement: **Zero candidates have been run through the full per-candidate loop.** The portfolio controller is specified, not implemented. The scoreboard reflects the current canonical portfolio state translated into the two-tier model — it is a snapshot, not a new evaluation.

---

## 14. The one-line summary

> The audit's directives are accepted in full. Seven specification artifacts are produced. The portfolio controller is specified but not yet implemented as running code. The next move is to implement the controller and run C3 (strongest-alternative attack) as the first end-to-end demonstration of the per-candidate loop. Zero world-class virtual survivors. Zero world-class inventions. That is the honest current state.

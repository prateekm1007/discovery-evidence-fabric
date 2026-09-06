# R413 — Physics Stack V1: The Computational Engineering Layer

**Round:** R413/PHYSICS_STACK_V1 (evolved to the DECISION-MACHINE design during the round, per the operator's directive V2 — see `OPERATOR_DIRECTIVE_V2.json`)
**Branch:** `r413/physics-stack-v1` (from the sealed V3 tip `19e0a582`; main untouched)
**Directives:** the v1 multi-solver stack message (`OPERATOR_DIRECTIVE.json`) superseded IN BUILD ORDER by the decision-machine message (`OPERATOR_DIRECTIVE_V2.json`): "Do not build a bigger physics stack. Build a physics decision machine that earns each new solver by demonstrated discovery value."
**Constitution:** v2.1.0, read in full at session start and re-read in full immediately before the commit
**reviewer_provenance:** AI_REVIEW on every artifact in this round (Art. LXVII)

---

## 1. What the operator decided (both directives, reconciled)

Both directive messages agree on the invariants:

> **Blender is the visualization/asset-production layer; it never creates evidence of physical validity.** The machine may say *"Validated: <phenomenon>, <regime>, specified geometry and boundary conditions"* and may never say *"Physics verified."*

Directive V2 changes the build order and adds the measurement layer:

- the Physics Coverage Registry is a **DECISION SYSTEM**, not documentation;
- a **coverage matrix** over the dead R411/R412 mechanisms determines which physics domain matters;
- solver routing is **deterministic** (an LLM may propose; the rules verify);
- the **geometry authority boundary** is explicit and machine-tested (CadQuery owns engineering geometry; Blender is downstream);
- **exactly ONE new solver** is chosen by a measured **Physics Gap Opportunity Score** and fully wired;
- **Blender integration is Phase 7** — not started (the render CONTRACT is encoded and tested; execution awaits the operator).

## 2. The delivered architecture (all deterministic, zero LLM in the layer)

| Component | File | What it enforces |
|---|---|---|
| Physics Coverage Registry V1 | `PHYSICS_COVERAGE_REGISTRY_V1.json` (builder: `scripts/r413_build_physics_coverage_registry_v1.py`) | The operator's 15-field schema verbatim, 18 phenomena, **2 validated regimes** (hydraulic V0 pinned to its historical replay log; linear_elastic_deformation pinned to the sfepy closed-form replay executed this round). Fail-closed build: both replays re-verified at build time |
| Deterministic classifier | `mechanism_physics.py` | mechanism terminology → physics domains (the operator's 10 + multiphysics + UNKNOWN), pre-registered ≥2-distinct-term evidence rule, closed general vocabulary, disclosed calibration log |
| Coverage matrix | `PHYSICS_COVERAGE_MATRIX_V1.json` (builder: `scripts/r413_build_physics_coverage_matrix.py`) | the operator's four outputs over the 400 dead R411 candidates + 14 adjudicated deaths; **0% simulatable / 100% would-terminate MECHANISM_NOT_SIMULATABLE** at measurement (the honest pre-wiring state); unlock per missing domain; R412 seeds disclosed as re-attempts dead at the upstream retrieval gate |
| Deterministic router | `routing.py` | terminology → phenomena → required equations → eligible solver domains → registry lookup; typed fail-closed outcomes; **Art. XVIII proposal gate** (LLM proposals verified against the deterministic evidence; uncorroborated proposals never extend a route) |
| Geometry authority boundary | `geometry_authority.py` + `GEOMETRY_AUTHORITY_PROBES.json` | CadQuery is the engineering geometry authority (**measured OPERATIONAL**, cadquery 2.6.1, live parametric build verified against closed-form volume); Blender cannot originate or validate engineering geometry — machine-enforced at the GEOMETRY_SPEC and RENDERING stages |
| Opportunity score | `opportunity.py` + `PHYSICS_GAP_OPPORTUNITY_SCORE_V1.json` | the operator's six factors, pre-registered tables, formula `(U×G×D×V×A)/C` + the simple `U×G/C` shape; **sfepy selected (20855)**; **formula-sensitivity DISCLOSED** (elmer leads under the simple formula; the disagreement is recorded, not resolved by preference) |
| Solver wiring | `SOLVER_AVAILABILITY_PROBES.json` + `SFEPY_INSTRUMENT_VALIDATION.json` | sfepy 2026.2 installed (the operator-authorized ONE solver), re-probed pin-preserving (the hydraulic V0 computation-log pin survived — asserted), **validated by closed-form replay BEFORE any discovery use: 3/3 cases, max rel error 1.9e-14, determinism byte-identical** |
| Full-path traversal | `FULL_PATH_TRAVERSAL_V1/` (script: `scripts/r413_full_path_traversal.py`) | the operator's Phase 6 standard: a REAL dead candidate (C-wind-2) traverses mechanism → geometry (CadQuery + STEP) → solver → simulation (5 FEM runs) → evidence artifact → verification → attacker → dossier; all 11 stages valid under the typed contracts |
| Pipeline contracts | `pipeline.py` | the 11-stage typed machine (carried from V1) + the Phase 4 geometry guards + the Phase 7 render contract (renders reference the simulation artifact ID) |
| Claim-language contract | `coverage.evaluate_physics_claim` | carried unchanged in substance: global overclaims rejected; regime-scoped validation only; visualization sources rejected |
| Test battery | `tests/test_r413_physics_decision.py` | 63 tests: positive / negative / adversarial / metamorphic, hardcoded hash pins, false-positive corpses (power flow, loss reduction, light load, harmonic distortion, stress-concentration-as-chemistry), tamper detection |

## 3. The Phase 6 finding (what the wired solver actually bought)

C-wind-2 "Pre-misalignment Bearing System" (R411 engineering death, PHYSICS_RELEVANT) declares `σ_max = K_t·σ_nominal` and `F_d = F·cos(θ)` and predicts **15–25% peak-stress reduction** from pre-misalignment. The traversal ran BOTH load-model readings:

- **projection reading** (the mechanism's own model, load reduced by cos θ): reduction = **6.0%** at 20° — exactly the load projection, by linearity;
- **tilt reading** (the service-deflection reality the R411 attacker cited — load direction tilts, magnitude persists): reduction = **−0.5% ≈ zero**. The hole's peak stress is approximately angle-invariant (Kirsch structure); the predicted reduction is a property of the LOAD MODEL, not the geometry.

The R411 death **STANDS** (its controllability cause is a multibody question — contact_friction_mechanics remains unwired, honestly recorded as `ROUTE_INCOMPLETE_SOLVER`). The traversal adds computational evidence AGAINST the mechanism's central quantitative claim under the realistic load reading. Zero promotions, zero LLM calls, zero discovery budget — a dead candidate, instrument-grade evidence.

The verification anchors (Art. XXVII, class + justification each): linearity exact at 1e-9; mesh convergence ≤2%; **K_t measured against the exact Kirsch solution evaluated at the ring-element-center sampling radius** (coarse 2.79 vs 2.77 expected; fine 3.030 vs 2.994); far-field σ ≤5%; replay byte-identical.

## 4. Incidents and instrument defects this round (all disclosed, all fixed forward)

1. **sfepy sign convention** (dw_surface_ltr): the first fail-closed validation replay measured FE = −1× closed form — the instrument caught its own defect (Art. XVI); fixed with the documented sign, re-run green.
2. **Chain-rule index transposition** in the traversal's element-center strain recovery: invisible at diagonal-Jacobian locations (the Kirsch peaks) but corrupting skewed elements (far-field read 2.37σ). Found by the far-field anchor check; fixed; all anchors then green.
3. **"stress concentration" → chemical evidence leak**: bare `concentration` matched the chemical rule; found by the adversarial test battery; fixed; the matrix RE-MEASURED in the same round with the full calibration history disclosed in the artifact.
4. **Decision-state contamination**: a post-wiring re-run of the opportunity builder initially re-wrote the frozen decision (sfepy installed → excluded → elmer selected). Fixed with the explicit decision-time state parameter; the LIVE forward query (which solver is missing NEXT) honestly excludes the wired sfepy and is tested to do so.
5. **Tilt-load modeling error** (first traversal run): single-anchor shear reaction corrupted RUN-4; fixed with the self-equilibrated traction pair + 3-DOF pinning (one instrument for every run, Art. XLVII).
6. **PEP 668 / split-Python environment**: `pip` targeted a 3.13 user-site while the active interpreter is a 3.12 venv; sfepy initially installed into the wrong interpreter. Fixed with `python3 -m pip install`.
7. **Pre-existing repo test-suite conditions, NOT this round's** (disclosed, Art. XV; proven by re-running with every R413 file removed): `test_e21a_negative_control_bench01_measured_defect_refused` fails at the base commit (the generated benchmark runs were never committed to this worktree); the FULL suite has pre-existing order-pollution (2825 errors without any R413 file present). The repo's standing convention is curated subset batteries — this round's: **r413 63/63 + r412 tvm_v2 150/150** (run together: 213/213).

## 5. The honest current state (the operator's checklist, measured)

| Area | Status |
|---|---|
| Physics Coverage Registry | 🟢 V1 built (15-field schema, 18 phenomena, 2 validated regimes, decision-system queries) |
| Physics coverage measurement | 🟢 the matrix (400 dead classified; 0%→ measured simulatable set grew to 2 phenomena after wiring) |
| Deterministic solver routing | 🟢 routing.py + the Art. XVIII proposal gate |
| Existing hydraulic solver | 🟢 operational, pin preserved through the re-probe |
| Second solver | 🟢 **sfepy 2026.2 selected by the decision machine, installed, validated, wired** |
| Geometry authority boundary | 🟢 machine-enforced + measured (CadQuery OPERATIONAL 2.6.1) |
| CadQuery | 🟢 measured OPERATIONAL here (the CI discrepancy the external auditor reported remains an open item for the operator's CI — this environment's measurement is recorded, both facts stand) |
| Blender | 🔴 Phase 7 not started (contract enforced and tested; renderer measured NOT_INSTALLED) |
| Physics → evidence artifacts | 🟢 demonstrated (SIMULATION_EXECUTION + MEASUREMENT_EXTRACTION + output-hash chain) |
| Physics → attacker | 🟡 architecture demonstrated (deterministic binding + honest independence state; an independent LLM/second-provider attack on the simulation output remains future work) |
| Physics → buyer dossier | 🟢 demonstrated (claim contract enforced: regime-scoped claim ADMITTED; K_t correctly carried as computational evidence, NOT a validated claim) |
| Multi-physics | 🔴 not yet (priced honestly in the matrix: 134/400 dead mechanisms are multiphysics-classified; partial unlock accounting exists) |
| End-to-end computational engineering loop | 🟡 proven for the structural domain on one real candidate; the loop (REDESIGN → SIMULATION_REPLAY) is wired but the redesign step was honestly skipped (not design-addressable) |

## 6. What would falsify this round

- any admitted claim containing an overclaim marker (contract broken);
- any Blender-originated/validated engineering geometry passing the boundary;
- any render entering the dossier chain without the simulation artifact reference;
- any availability or validation state that cannot be traced to a probe/computation-log hash (Art. VI);
- any selection nondeterminism, or any post-hoc factor revision in the opportunity tables;
- the hydraulic V0 pin drifting through the re-probe (asserted at every probe run);
- the full-path traversal failing any typed stage contract.

Each has a dedicated adversarial test; the battery is green.

## 7. Unblock conditions for the next round

1. **Upstream retrieval adequacy** (Art. XIV): the retrieval-resilience round's benchmark/gate decide whether proposer budget is ever spent — the physics layer's engine integration (the discovery loop's COMPUTATIONAL VALIDATION stage) stays gated on that, not wired by this round.
2. **Attacker calibration (Art. L, the standing note)**: none of this outranks fixing the terminal gate's false-kill rate; the physics layer makes surviving candidates more convincing — it does not help if the gate kills 4 of 5 good ones first.
3. **Phase 7 (Blender)**: operator decision; the render contracts are ready and tested.
4. **The next solver** (when earned): the LIVE opportunity query currently names elmer (16249) — a system-binary integration that cannot meet the Phase 6 standard in THIS environment (measured); that disagreement is disclosed, not hidden.

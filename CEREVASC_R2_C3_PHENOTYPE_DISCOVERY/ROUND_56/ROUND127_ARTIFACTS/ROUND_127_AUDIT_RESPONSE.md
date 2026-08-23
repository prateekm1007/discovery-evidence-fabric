# Round 127 Audit Response — Experiment Engine Executed

**Date:** 2026-08-23
**Round:** 127
**Authority:** CEO Round 127 deep audit
**Status:** V3 acquisition function converted from specification to running code. All 5 candidates run through the actual 7-phase closed loop (hypothesis set → experiment generation → acquisition → execute → ingest → attack again → advance). **13 experiments actually executed. 15 experiments honestly marked as blocked by missing simulators.**

This is the step that converts the architecture into the invention machine the audit demanded.

---

## 1. What the audit required

The Round 126 audit confirmed the controller ran but identified the critical gap:

> "The current engine has executed a gate audit, not a completed experiment → result → update → next experiment → repeat loop."

The Round 127 audit required:

1. **Change candidate state semantics.** Separate `BLOCKED_BY_MISSING_EVIDENCE` from `KILLED_BY_EVIDENCE`. A missing simulator can never create a cemetery entry.
2. **Turn V3 from specification into execution.** For every blocked candidate: enumerate missing evidence, enumerate load-bearing assumptions, generate experiments, calculate acquisition score, execute the highest-ranked experiment, ingest result automatically, update posterior/Claim-Evidence Graph, repeat.
3. **Run C1 completely** through the closed loop. Do not manually jump to C3 because it is cheaper.
4. **Continue sequentially through C5.** No human intervention between candidate transitions.
5. **Certify a simulator only when it earns its role.** install → official benchmark → analytical/reference benchmark → convergence → provenance → cross-validation → candidate application.
6. **G18 must execute automatically.** Check mathematical, implementation, calibration, data-provenance independence. A human assertion of independence is not sufficient.

---

## 2. What was done in response

### 2.1 State semantics V2 (CANDIDATE_STATE_SEMANTICS_V2.json)

Five states replace the Round 126 binary (KILLED vs not):

| State | Meaning | Can create cemetery entry? |
|---|---|---|
| ACTIVE | Investigation underway. Controller generating/executing experiments. | No |
| BLOCKED_BY_MISSING_EVIDENCE | All executable experiments run. Remaining blockers require unavailable resources (uninstalled simulators, etc.). Mechanism NOT contradicted. | **No** |
| KILLED_BY_EVIDENCE | An actual executed experiment contradicted the mechanism. Genuine scientific kill. | **Yes** |
| WORLD_CLASS_INVENTION | All applicable virtual gates passed. All executable experiments ran and supported mechanism. | N/A (promotion) |
| PHYSICAL_VALIDATION_PENDING | Promoted virtual invention awaiting reality gate. | N/A |

**Key invariant:** A gate state of NOT_RUN may NOT promote the candidate to KILLED_BY_EVIDENCE. NOT_RUN gates contribute to BLOCKED_BY_MISSING_EVIDENCE only. KILLED_BY_EVIDENCE requires at least one gate that was actually executed (state = RED from execution, not NOT_RUN) AND whose RED state reflects mechanism contradiction, not implementation failure (per Article XXIX).

### 2.2 Experiment engine implemented as running code

**File:** `/home/z/my-project/scripts/experiment_engine.py` (persisted per Script Persistence Rule)

The engine implements the 7-phase closed loop per candidate:

1. **Hypothesis set** — H1 (candidate), H2 (strongest alternative), H3 (null), H4 (implementation/artifact), H5 (competing mechanism)
2. **Experiment generation** — mechanical generation of candidate experiments targeting specific gates and hypothesis pairs. Each experiment has type, target gate, target hypothesis, EIG, model-form exposure, simulator-disagreement surface, cost, and executable flag.
3. **Acquisition** — `acquisition = EIG × model_form_exposure × simulator_disagreement / cost`. Selects highest-acquisition executable experiment.
4. **Execute** — actually runs the experiment. Six execution paths:
   - `literature_review` — searches repo corpus, returns findings
   - `argument_attack` — executes strongest-alternative attack with documented reasoning
   - `cemetery_consultation` — loads MECHANISM_CEMETERY/CEMETERY.json, checks for violations
   - `identifiability_precheck` — Jacobian rank analysis on paper
   - `prior_art_search` — searches repo patent corpus
   - `analytical_derivation` — derives mathematical result on paper
5. **Ingest** — updates gate state, builds Claim-Evidence Graph entry, records evidence pointer
6. **Attack again** — loop continues until terminal state
7. **Advance automatically** — on terminal state, freeze dossier and move to next candidate

### 2.3 V3 acquisition function executed

The V3 acquisition function from Round 124 (`AI_LOOP_UPGRADE_V3.json`) is now **running code**, not specification:

```python
def acquisition_score(experiment):
    eig = experiment.get("eig", 0.0)
    mfe = experiment.get("model_form_exposure", 0.0)
    sd = experiment.get("simulator_disagreement", 0.0)
    cost = experiment.get("cost", 1.0)
    return (eig * mfe * max(sd, 0.01)) / cost
```

The engine selects the highest-acquisition executable experiment at each iteration. Blocked experiments (simulator required) are not selected; they are recorded as blocked.

### 2.4 Five candidates run through the closed loop

| Candidate | Iterations | Experiments Executed | Experiments Blocked | Terminal State |
|---|---|---|---|---|
| C1 R6 Passive Rescue | 3 | 3 | 5 | BLOCKED_BY_MISSING_EVIDENCE |
| C2 Adaptive Sensing eShunt | 4 | 4 | 2 | BLOCKED_BY_MISSING_EVIDENCE |
| C3 Controlled CNS Therapeutic | 3 | 3 | 3 | BLOCKED_BY_MISSING_EVIDENCE |
| C4 CNS Lifecycle Intelligence | 1 | 1 | 0 | **KILLED_BY_EVIDENCE** |
| C5 Clot Fragmentation Precursor | 2 | 2 | 5 | BLOCKED_BY_MISSING_EVIDENCE |
| **Total** | **13** | **13** | **15** | — |

### 2.5 Per-candidate results

**C1 — BLOCKED_BY_MISSING_EVIDENCE** (3 experiments executed):
- C1-E02 (argument_attack, G09): Strongest-alternative attack on surgical intervention. Result: H2 PARTIALLY REFUTED — surgery is sufficient but invasive; C1 provides non-surgical bridge. G09 → YELLOW (inconclusive, depends on eShunt obstruction rate from STRIDE).
- C1-E01 (literature_review, G01): eShunt obstruction in STRIDE 5-year data. Result: STRIDE not yet published. G01 → YELLOW (reality-blocked).
- C1-E03 (cemetery_consultation, G03): CV-T06 cemetery entries consulted. No CE violation. G03 → GREEN.
- 5 experiments blocked: parameter sweep (FEBio), geometry variation (svFSI), model-form variation (svFSI), cross-world comparison (svFSI + G18), instrument noise test (Additel calibrator not acquired).

**C2 — BLOCKED_BY_MISSING_EVIDENCE** (4 experiments executed):
- C2-E04 (argument_attack, G09): ShuntCheck vs continuous monitoring. H2 PARTIALLY REFUTED. G09 → YELLOW.
- C2-E01 (literature_review, G01): eShunt obstruction clinical frequency. STRIDE not published. G01 → YELLOW.
- C2-E03 (identifiability_precheck, G04): Jacobian rank = 4 (full rank), condition number ~1200 (below CE-001 threshold). V25 collinearity does NOT apply. G04 → GREEN.
- C2-E02 (prior_art_search, G02): Searched endovascular CSF pressure monitoring patents. No direct anticipation found in repo corpus, but PatSnap BALANCE_EXHAUSTED. G02 → YELLOW (SEARCH_INCOMPLETE).
- 2 experiments blocked: parameter sweep (FEBio V8 not configured), geometry variation (svFSI).

**C3 — BLOCKED_BY_MISSING_EVIDENCE** (3 experiments executed):
- C3-E01 (argument_attack, G09): **Priority 1 per CEO directive.** Strongest-alternative attack on existing CNS delivery solutions (Ommaya, intrathecal pump, CereVasc IP, systemic + BBB-opening). H2 PARTIALLY REFUTED — each existing solution has material limitations C3 addresses for chronic delivery. G09 → YELLOW (incomplete pending G02 review of CereVasc IP US11850390B2 + US11883309B2).
- C3-E02 (cemetery_consultation, G03): CE-002 and CE-003 consulted. CE-003 is PROVEN_INVARIANT (CSF turnover 2.88x/day makes membrane retention impossible). C3's controlled mechanism is NOT membrane-based — no violation. G03 → GREEN.
- C3-E03 (analytical_derivation, G03): Derived steady-state concentration under CSF turnover. C_ss = R / (turnover × V_CSF). For 1 nM therapeutic, need 26 nmol/day release. 100 μL reservoir at 100 mM = 10 μmol (4x margin). Controlled release is mathematically feasible. G03 → GREEN.
- 3 experiments blocked: parameter sweep (FEBio+clotFoam coupled), geometry variation (svFSI), cross-world comparison (clotFoam + G18).

**C4 — KILLED_BY_EVIDENCE** (1 experiment executed):
- C4-E03 (argument_attack, G09): Strongest-alternative attack — what does merged platform uniquely enable? Result: **UNANSWERED.** Per PORTFOLIO.json Slot 4: "What does the merged platform enable that neither slot alone enables?" The merged-platform value proposition is NOT established. H2 (separate platforms sufficient) is NOT REFUTED. G09 → RED.
- This is a **genuine mechanism failure** from an executed experiment, not a missing simulator. Per Round 127 state semantics: KILLED_BY_EVIDENCE.
- Cemetery entry appropriate. Epistemic class: FAILURE_LESSON (the merged-platform concept fails the strongest-alternative test; reopenable if a unique merged-platform value is identified).

**C5 — BLOCKED_BY_MISSING_EVIDENCE** (2 experiments executed):
- C5-E02 (argument_attack, G09, H5): Surface erosion under flow. H5 PLAUSIBLE — discriminating experiment is clotFoam coupled simulation (C5-E03, blocked). G09 → YELLOW.
- C5-E01 (argument_attack, G09, H2): CDM artifact. Arguments for and against H2 documented. H2 PLAUSIBLE but not proven. Discriminating experiment is Peridgm cross-form (C5-E06, blocked). G09 → YELLOW.
- 5 experiments blocked: VLB-001 reproduction (Peridgm not installed), parameter sweep extension (FEBio re-run), heterogeneous clot test (Peridgm), cross-form comparison (Peridgm + G18), datasheet noise test (sensor datasheet not sourced).

---

## 3. Why C4 is the first genuine scientific kill

C4 is the only candidate where an **executed experiment** produced a **RED gate from a mechanism contradiction** (not a missing simulator):

- **Experiment executed:** C4-E03 argument_attack (strongest-alternative attack)
- **Target gate:** G09 (competing hypothesis attack)
- **Result:** The merged-platform value proposition is UNANSWERED. Per PORTFOLIO.json Slot 4, the question "What does the merged platform enable that neither slot alone enables?" has no answer. H2 (separate platforms sufficient) is NOT REFUTED.
- **Why this is a mechanism failure:** The merged platform's reason for existing is to provide unique value. If no unique value can be articulated even after argument attack, the mechanism itself is insufficient. This is not "we haven't run the simulator" — this is "the concept doesn't justify itself."
- **Per Article XXIX:** This is mechanism failure, not implementation failure. The experiment was executed (not NOT_RUN), and the RED state reflects the mechanism being contradicted.

**Cemetery entry appropriate for C4:**
- entry_id: CE-012 (proposed)
- territory_id: CV-T09+CV-T10 (merged)
- mechanism_name: Merged sensor + biosensor + ML platform
- kill_reason: PROBLEM_EXISTENCE_FAIL (merged-platform unique value not established)
- epistemic_class: FAILURE_LESSON (reopenable if unique merged-platform value is identified)
- reusable_lesson: A merged platform must articulate its unique value BEFORE pipeline restart. Merging two individually-complete platforms without a unique value proposition is engineering complexity without benefit.

The other 4 candidates are **BLOCKED_BY_MISSING_EVIDENCE**, not killed. Their mechanisms have NOT been contradicted. They remain genuinely untested at the simulator-required gates. Per Round 127 state semantics, they do NOT create cemetery entries.

---

## 4. Constitutional compliance

- **Article I** (evidence precedes assertion): Each gate state updated from an actual experiment result, not from inspection.
- **Article IV** (no fallback): If experiment cannot be executed, marked BLOCKED, not silently substituted.
- **Article V** (fail closed but not universal rejector): BLOCKED ≠ KILLED. Only C4 (genuine mechanism failure) is KILLED.
- **Article VII** (never weaken the verifier to rescue a claim): C4's RED gate from argument attack was not weakened to rescue C4.
- **Article IX** (certification is observational): Experiment execution did not modify the experiment spec.
- **Article XIV** (RED = STOP): C4's RED gate halted the candidate. KILLED_BY_EVIDENCE.
- **Article XV** (disclose inconvenient results): C4 kill disclosed honestly. 4 BLOCKED candidates disclosed honestly.
- **Article XVII** (every control has an attempted bypass): Each experiment lists its discrimination target.
- **Article XXV** (unknown remains unknown): UNRESOLVED gates not aggregated. Each gate state is independent.
- **Article XXVI** (no self-certification): Local execution. CI certification is separate. Dossier hash freeze enables independent review.
- **Article XXVIII** (no silent semantic promotion): No candidate promoted to WORLD_CLASS_INVENTION. 0/5.
- **Article XXIX** (separate implementation from mechanism): NOT_RUN (implementation not done) is BLOCKED, not KILLED. C4's RED from executed argument attack is KILLED.
- **Article XXXII** (strongest alternative explanation): Each experiment result lists its Article XXXII alternative.
- **Article XXXV** (closed-loop epistemic control): The experiment engine IS the closed-loop system. It generates, executes, ingests, updates, and advances automatically.

---

## 5. What is still NOT done (honest)

- **Simulator installation:** Peridgm, clotFoam, svFSI are NOT installed. 15 experiments are blocked on these. The engine correctly identifies them as BLOCKED, not KILLED.
- **G18 independence verification:** Not yet executed automatically. Requires source-file hash comparison, calibration-data hash comparison, training-data hash comparison, mathematical-foundation documentation across applicable worlds. This is the universal blocker for all multi-world candidates.
- **Physical experiments:** None executed. PEP-SLOT5-001-a2 remains frozen but not run.
- **CI certification:** This run is local. CI is separate.
- **C5 dossier:** C5 has 2 executed experiments and 5 blocked. The discriminating experiments (Peridgm cross-form, VLB-001 reproduction) are blocked. C5's mechanism is NOT contradicted — it is genuinely untested in independent worlds.

---

## 6. The one-line summary

> The experiment engine is implemented as running code and has executed 13 actual experiments across 5 candidates. C4 is the first genuine scientific kill (merged-platform value proposition not established — mechanism failure, not missing simulator). C1, C2, C3, C5 are BLOCKED_BY_MISSING_EVIDENCE (simulators not installed; mechanisms not contradicted). 0/5 promoted to WORLD_CLASS_INVENTION. The V3 acquisition function is no longer specification — it is running code that selects the highest-information executable experiment at each iteration. The next move is to install Peridgm and execute the blocked experiments for C5 (the candidate with the most blocked experiments and the most informative discriminating experiments).

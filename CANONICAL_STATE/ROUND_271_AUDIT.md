# Round 271 Audit — Consolidated 16-Candidate Register

**Task ID:** R271-CONSOLIDATED-16-CANDIDATE-REGISTER
**Agent:** main (CTO, Super Z)
**Date:** 2026-08-24

---

## 1. Consolidated Register: 16 Candidates, Unique Fingerprints

| ID | Name | Mechanism Fingerprint | Verdict |
|---|---|---|---|
| NC-A | Differential-Pressure-Invariant Flow Allocator | hydraulic_control_invariant | **KILL** |
| NC-B | Asymmetric Protein-Pass/Particle-Retain Membrane | selectivity_plus_fail_operational_hydraulics | WATCH |
| **NC-C** | **Predictive Occlusion-Isolation Controller** | **predictive_occlusion_isolation_control** | **INVEST** |
| NC-D | Energy-Neutral Pulse-Driven Micro-Pump Assist | energy_harvesting_anti_stagnation_fluidics | WATCH |
| NC-E | Chronotherapeutic Reservoir with Drainage-Synchronized Release | drainage_synchronized_pharmacokinetics | WATCH |
| NC-F | Fail-Operational Single-Lumen with Passive Micro-Bypass | passive_parallel_bypass_safety | **KILL** |
| **SC-A** | **Phase-Change Passive Adaptive Valve** | **phase_change_material_valve** | **INVEST** |
| SC-B | UWB Real-Time Intracranial Position Mapper | uwb_structural_telemetry | WATCH |
| SC-C | Biohybrid Living-Cell ICP Valve | living_cell_actuator | WATCH |
| **SC-D** | **On-Demand Bacteriophage CSF Infection Defense** | **phage_anti_infection** | **INVEST** |
| SC-E | Pressure-Gradient Autonomous Catheter Navigation | self_repositioning_catheter_control | WATCH |
| **SC-F** | **Chemical Molecular ICP Signaling** | **chemical_molecular_communication_channel** | **INVEST** |
| SC-G | Neuromorphic Shunt Failure Predictor | neuromorphic_temporal_prediction | WATCH |
| **SC-H** | **Enzymatic In-Line CSF Protein Clearance** | **flow_catalytic_enzyme_clearance** | **INVEST** |
| SC-I | Through-Skull NIR Photovoltaic | photovoltaic_energy_autonomous_therapy | WATCH |
| SC-J | Adaptive Synthetic Glycan Immune Tolerance | glycan_immune_tolerance_surface | WATCH |

**Verdict summary: 5 INVEST, 9 WATCH, 2 KILL**

---

## 2. Deduplication Results

6 potential collision pairs analyzed. **0 duplicates found.** All 16 have unique mechanism fingerprints. 6 pairs are related but independently patentable.

### Merge recommendation

**NC-C + SC-10 → MERGE.** NC-C is the predictive occlusion-isolation control law that SC-10 was missing (R269 downgraded SC-10 because its control law was unspecified). NC-C IS the specification. Merged candidate: "Distributed Micro-Shunt Mesh with Predictive Occlusion-Isolation Control."

---

## 3. The 5 INVEST Candidates

| Rank | ID | Name | Why INVEST |
|---|---|---|---|
| **#1** | **SC-A** | Phase-Change Passive Adaptive Valve | Fundamentally different physical mechanism (phase-change vs mechanical spring). Specific materials (Ga-In + apoprotein). Cannot fatigue, cannot calcify, self-calibrating. Gate H >$250K. Gate O outside routine optimization. |
| **#2** | **SC-F** | Chemical Molecular ICP Signaling | Genuinely new information channel (chemical vs electronic). Zero electronics in brain. Eliminates battery + RF failure modes. BUT: molecule unspecified (needs design). |
| **#3** | **SC-D** | Bacteriophage CSF Infection Defense | Self-amplifying + pathogen-specific + detection-triggered. Cannot generate resistance. Specific phage targets identified. 3-dimensional delta over antibiotic-eluting. |
| **#4** | **SC-H** | Enzymatic CSF Protein Clearance | Dual function (drainage + therapy). Specific enzyme cocktail (neprilysin + BACE2 + τ-kinase). Different compartment (CSF vs blood). Addresses NPH + Alzheimer's comorbidity. |
| **#5** | **NC-C** | Predictive Occlusion-Isolation Controller | The control law SC-10 needs. Predictive pre-emptive occlusion isolation. Gate P: the specific hydraulic invariant (predictive redistribution while maintaining global ICP) is potentially novel. Should merge with SC-10. |

---

## 4. The 2 KILLED Candidates

| ID | Name | Kill reason |
|---|---|---|
| NC-A | Differential-Pressure-Invariant Flow Allocator | Gate M FAIL — pressure-compensating valves exist. Gate H FAIL (<$100K). Thin delta over existing valves. Invariant control law is application of known control theory to solved problem. |
| NC-F | Fail-Operational Single-Lumen with Passive Micro-Bypass | Gate M FAIL — R6 passive bypass exists (from cemetery). Pressure-relief valves exist. Distributed array is engineering improvement, not invention. Gate H FAIL (<$50K). |

---

## 5. The 9 WATCH Candidates

| ID | Why WATCH (not INVEST) |
|---|---|
| NC-B | Gate H borderline ($100-200K). Geometric guarantee is interesting but unproven. Needs feasibility. |
| NC-D | Gate H borderline ($100-200K). Major physics risk — CSF pulsation energy may be insufficient. |
| NC-E | Gate H FAIL (<$150K). Synchronization = standard feedback control applied to drainage state. |
| SC-B | Major physics risk — UWB through skull may be impossible. Needs feasibility study. |
| SC-C | Tissue-engineered implants exist. Needs deep collision on endothelialized implant surfaces. |
| SC-E | Gate P: control law (gradient-following) is standard. Application, not invention. |
| SC-G | Gate P: control law = standard predictive maintenance. Weakest of the 16. |
| SC-I | Through-skin photovoltaic is active MIT/Stanford research (not white space). |
| SC-J | Glycan/IL-10 unspecified (SC-05 lesson). Concept until molecules designed. |

---

## 6. Combined Portfolio (Including R268 + R270)

| Source | Total | INVEST | WATCH | KILL | Conditional |
|---|---|---|---|---|---|
| R268 CEO shunt candidates | 10 | 0 | 0 | 8 (SC-01-04,06-09) + SC-05 (CE-023) | SC-10 (needs control law → merge with NC-C) |
| R270 CEO 2035-horizon | 10 | 4 (SC-A,D,F,H) | 6 (SC-B,C,E,G,I,J) | 0 | All conditional on deep collision |
| R271 NC narrow mechanism | 6 | 1 (NC-C) | 3 (NC-B,D,E) | 2 (NC-A,F) | All conditional on deep collision |
| **TOTAL** | **26** | **5** | **9** | **11** | **SC-10+NC-C merge** |

After deduplication and merge: **~14 unique candidates** (5 INVEST + 9 WATCH). This aligns with the 10-15 target.

---

## 7. Next Steps

1. **Deep collision on SC-A (Phase-Change Valve)** — strongest INVEST candidate. Element-level decomposition + live patent search. If it survives → first genuine Level 2.
2. **Merge NC-C + SC-10** — NC-C is the control law SC-10 needs. Deep collision on the merged candidate's predictive occlusion-isolation invariant.
3. **SC-F molecule design** — most novel concept but needs specific molecule. Without molecule, it's a concept (SC-05 lesson).
4. **SC-D and SC-H deep collision** — strong mechanisms with specific targets/cocktails. Need live search for phage implants and enzymatic membrane implants.
5. **External patent attorney review** — all INVEST candidates need external FTO before any buyer outreach.

**No simulation until deep collision completes.**

---

## 8. Artifacts Produced

| Artifact | Path | Size |
|---|---|---|
| Consolidated 16-candidate register | `CANONICAL_STATE/R271_CONSOLIDATED_16_CANDIDATE_REGISTER.json` | 57,282 bytes |
| This Audit | `CANONICAL_STATE/ROUND_271_AUDIT.md` | (this file) |
| Script | `scripts/r271_consolidated_16_register.py` | (in /home/z/my-project/scripts/) |

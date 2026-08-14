# Simulation Readiness Forensic Audit

**Date:** 2026-08-14  
**Repository:** prateekm1007/discovery-evidence-fabric  
**Branch:** qwen-code-78fe3361-1514-436e-8abc-55bea69c59fe (main)  
**Audit Scope:** All simulation-related, invention-candidate, and physics/engineering handoff code

---

## Executive Summary

This audit examines all existing code, schemas, and artifacts related to:
1. Invention candidate representation
2. Simulation readiness
3. Physics/engineering handoff capabilities
4. Provenance preservation for external simulation systems

**Key Finding:** The repository has **NO** simulation infrastructure, **NO** simulation request/response contracts, and **NO** simulation adapter interfaces. The A2 system produces invention candidates with mechanism/intervention structure, but these are NOT simulation-ready.

---

## Component Classification

### KEEP — Existing structures that can be extended

| Component | Path | Reason |
|-----------|------|--------|
| EvidenceItem Schema | `discovery_fabric/normalization/evidence_item_schema.json` | Canonical evidence schema with provenance, hashes, epistemic states. Can be referenced by invention candidate schema. |
| A2 Candidate Structure | `a2_output/p01/candidate.json` | Contains device, failure_mode, constraint, mechanism, intervention, expected_effect, falsification_test, source_evidence with hashes. Foundation for AUTOMATED_INVENTION_CANDIDATE. |
| Epistemic State Machine | `discovery_fabric/normalization/evidence_item_schema.json` (line 46) | Defines OBSERVED→INFERRED→ANALOGY→CANDIDATE_CONNECTION→MECHANISTIC_HYPOTHESIS→EXPERIMENTAL_PROPOSAL→INVENTION_CANDIDATE. Can extend with simulation states. |
| Prior Art Report | `a2_output/p01/prior_art_report.json` | Contains databases_searched, queries, result_count, limitations. Can be referenced by invention candidate. |
| Adversarial Report | `a2_output/p01/adversarial_report.json` | Contains attack dimensions (unsupported_mechanism, weak_transfer, etc.). Can be referenced by invention candidate. |
| Source Hashes | `a2_output/p01/source_hashes.json` | Provenance tracking for retrieval. Can be extended for simulation handoff. |

### QUARANTINE — Related but not directly usable

| Component | Path | Reason |
|-----------|------|--------|
| TEE Mechanism Extraction | `discovery_fabric/mechanisms/README.md` | Quarantined per Task 7 results (negative value). Do not resurrect. |
| TEE Discovery Modes | `discovery_fabric/discovery_modes/README.md` | Quarantined per audit. TEE-style operators not validated. |
| Corpus Rejected Candidates | `corpus_v2/rejected/*.json`, `corpus/rejected/*.json`, `corpus_v3/rejected/*.json` | Contain invention-like structures but were rejected. Can study for schema design but do not modify. |

### UNPROVEN — Scaffolding only, no implementation

| Component | Path | Reason |
|-----------|------|--------|
| Knowledge Graph | `discovery_fabric/knowledge_graph/README.md` | Scaffolding only. No graph construction or query implementation. |
| Evaluation Module | `discovery_fabric/evaluation/` (referenced in README) | Mentioned as "internal quality metrics (not TEE)" but no implementation found. |

### REMOVE — Nothing to remove

No components require removal. Repository is minimal and clean.

---

## Detailed Analysis

### 1. Current Invention Candidate Structure (A2)

From `a2_output/p01/candidate.json`:

```json
{
  "candidate_id": "cand:A2:p01:e5ed9b6a2cf0ad18",
  "problem_id": "p01",
  "device": "Cardiac Pacemaker",
  "failure_mode": "BATTERY_FAILURE",
  "failure": "...",
  "constraint": "...",
  "mechanism": "...",
  "intervention": "...",
  "expected_effect": "...",
  "falsification_test": "...",
  "mechanism_source_span": "...",
  "source_evidence": {
    "source_id": "europepmc:42205228",
    "source_hash": "...",
    "source_title": "...",
    "source_span": "...",
    "retrieval_timestamp": "..."
  },
  "model": "...",
  "prompt_hash": "...",
  "input_hash": "...",
  "output_hash": "...",
  "synthesis_timestamp": "..."
}
```

**Assessment:** This structure contains ~60% of what's needed for simulation readiness. Missing:
- observed_phenomenon (distinct from mechanism)
- source_mechanisms (explicit link to source paper mechanisms)
- exact_evidence_spans (array, not single span)
- source_identifiers (array of all sources)
- cross_domain_connection (explicit analogy statement)
- proposed_intervention (currently just "intervention")
- expected_causal_effect (currently just "expected_effect")
- known_alternatives (no alternative solutions tracked)
- prior_art_search_record (has separate report, should be embedded reference)
- prior_art_coverage (quantitative coverage metric)
- adversarial_results (has separate report, should be embedded reference)
- searched_universe_version (what databases/versions were searched)
- epistemic_state (present in final_state.json but not in candidate.json)

### 2. Current Final State Structure

From `a2_output/p01/final_state.json`:

```json
{
  "run_id": "...",
  "problem_id": "p01",
  "device": "Cardiac Pacemaker",
  "final_status": "REJECTED",
  "epistemic_state": "OBSERVED",
  "reason": "evidence verification failed",
  "evidence_verified": false,
  "prior_art_status": "NO_MATCHING_EVIDENCE_FOUND",
  "adversarial_overall": "KILLED"
}
```

**Assessment:** Tracks terminal state but does not preserve full provenance chain. For simulation handoff, we need the full candidate structure PLUS simulation-specific metadata.

### 3. Prior Art Report Structure

From `a2_output/p01/prior_art_report.json`:

```json
{
  "prior_art_status": "NO_MATCHING_EVIDENCE_FOUND",
  "databases_searched": ["EuropePMC"],
  "queries": ["...", "..."],
  "date_range": "all",
  "timestamp": "...",
  "result_count": 0,
  "results": [],
  "limitations": ["Only EuropePMC searched", ...]
}
```

**Assessment:** Good foundation. For simulation handoff, needs:
- searched_universe_version (database versions, snapshot dates)
- coverage_metrics (what fraction of relevant space was searched)
- negative_result_confidence (statistical confidence in "no prior art found")

### 4. Adversarial Report Structure

From `a2_output/p01/adversarial_report.json`:

```json
{
  "overall": "KILLED",
  "killed_count": 5,
  "attacks": {
    "unsupported_mechanism": "KILLED",
    "weak_transfer": "KILLED",
    "obvious_combination": "KILLED",
    "prior_art": "KILLED",
    "contradiction": "PASS",
    "boundary_failure": "KILLED",
    "engineering_infeasibility": "PASS",
    "regulatory_incompatibility": "PASS"
  }
}
```

**Assessment:** Good attack surface coverage. For simulation handoff, needs:
- boundary_conditions_identified (what boundaries were tested)
- engineering_assumptions (what engineering feasibility assumptions were made)

### 5. Evidence Item Schema

From `discovery_fabric/normalization/evidence_item_schema.json`:

```json
{
  "epistemic_state": {
    "type": "string",
    "enum": ["OBSERVED", "INFERRED", "ANALOGY", "CANDIDATE_CONNECTION", 
             "MECHANISTIC_HYPOTHESIS", "EXPERIMENTAL_PROPOSAL", "INVENTION_CANDIDATE"]
  }
}
```

**Assessment:** This is the canonical epistemic state machine. For simulation readiness, we need to extend with:
- SIMULATION_READY
- SIMULATION_SUBMITTED
- SIMULATION_COMPLETE
- SIMULATION_SURVIVOR
- EXTERNALLY_TESTABLE

But per task requirements, these states should be DEFINED but BLOCKED (not active).

### 6. Simulation-Related Content in Rejected Candidates

Examining `corpus_v2/rejected/v2_00004.json` (Hip Implant fracture):

```json
"falsification_test": "Conduct finite element analysis and mechanical fatigue testing comparing FG-HSIH versus monolithic implants under cyclic physiological loading..."
```

**Assessment:** Some candidates mention simulation methods (FEA, CFD, etc.) in their falsification tests, but there is NO structured simulation request format. These are natural language descriptions, not machine-readable simulation specifications.

---

## Gap Analysis: What's Missing for Simulation Readiness

### A. Invention Candidate → Simulation Request Translation

Current candidate has:
- ✓ device
- ✓ failure_mode
- ✓ constraint
- ✓ mechanism
- ✓ intervention
- ✓ expected_effect
- ✓ falsification_test
- ✓ source_evidence with hashes

Missing for simulation:
- ✗ geometry_requirements (CAD model, dimensions, tolerances)
- ✗ materials (specific alloys, polymers, composites with properties)
- ✗ operating_conditions (temperature, pressure, frequency, duty cycle)
- ✗ loads (force vectors, moments, pressure distributions)
- ✗ boundary_conditions (fixed supports, contacts, symmetries)
- ✗ environmental_conditions (corrosive media, radiation, humidity)
- ✗ predicted_mechanism (which physical phenomenon dominates)
- ✗ predicted_measurable_outcome (numerical value with units)
- ✗ baseline_control (what is the reference design?)
- ✗ success_criterion (quantitative threshold)
- ✗ falsification_criterion (what numerical result would falsify?)
- ✗ uncertainty_bounds (confidence intervals on predictions)
- ✗ missing_parameters (which parameters are unknown?)

### B. Simulation Adapter Interface

Current state: **DOES NOT EXIST**

Required interface:
```python
class SimulationAdapter:
    def submit(request: SimulationRequest) -> JobID
    def status(job_id: JobID) -> JobStatus
    def retrieve(job_id: JobID) -> SimulationResult
    def validate(result: SimulationResult) -> ValidationResult
```

Supported engines (future):
- Ansys (Mechanical, Fluent, Maxwell)
- SimScale
- Siemens (NX Nastran, Star-CCM+)
- Altair (HyperWorks, OptiStruct)
- Quanscient
- Other legitimate engineering/physics engines

**Constraint:** Do NOT integrate paid APIs, scrape websites, create fake results, or build physics solvers.

### C. Baseline/Control Structure

Required for scientific validity:
- proposed_invention vs current_reference_design
- dependent_variable (what is being measured?)
- baseline_value (reference performance)
- predicted_intervention_value (invention performance)
- improvement_degradation (delta with direction)
- uncertainty (confidence bounds)
- simulation_assumptions (what simplifications were made?)

**Critical Rule:** Never report "simulation successful" merely because a solver completed. A simulation is scientifically useful ONLY if it tests the invention's stated falsifiable prediction.

### D. Blocking Conditions

Two blocking states must be implemented:

1. **SIMULATION_BLOCKED_MISSING_PARAMETERS**
   - Triggered when required simulation parameters are absent
   - Must NOT invent values
   - Must report exactly which parameters are missing

2. **SIMULATION_BLOCKED_NON_FALSIFIABLE**
   - Triggered when candidate claims are not measurable
   - Example: "improves durability" without specifying measurable endpoint
   - Must identify what makes the claim non-falsifiable

---

## Recommendations

### 1. Extend Existing Schemas (Do Not Create New Ontology)

- Extend `EvidenceItem` epistemic_state enum with simulation states (blocked)
- Create `AutomatedInventionCandidate` schema that references `EvidenceItem` schema
- Create `SimulationRequest` schema that extends candidate with engineering parameters
- Create `SimulationResult` schema with provenance attachment
- Create `SimulationAssessment` schema with baseline/control comparison

### 2. Preserve Provenance Chain

Every simulation result must trace back through:
```
SimulationResult
  ← SimulationRequest
    ← AutomatedInventionCandidate
      ← source_evidence (EvidenceItem array)
        ← retrieval provenance (hashes, timestamps, queries)
```

### 3. Implement Blocking Logic

Before any simulation request can reach SIMULATION_READY state:
- Check all required parameters present → else SIMULATION_BLOCKED_MISSING_PARAMETERS
- Check falsifiability (measurable outcome with units) → else SIMULATION_BLOCKED_NON_FALSIFIABLE

### 4. Create Test Fixtures

Three deterministic fixtures:
- **Fixture A (Complete):** Medical device with all parameters → SIMULATION_READY
- **Fixture B (Incomplete):** Missing material/boundary info → SIMULATION_BLOCKED_MISSING_PARAMETERS
- **Fixture C (Non-falsifiable):** Vague claim like "improves durability" → SIMULATION_BLOCKED_NON_FALSIFIABLE

---

## Conclusion

The repository has a solid foundation for invention candidate generation (A2 system) but lacks:
1. Simulation-ready contract definitions
2. Simulation request/response schemas
3. Simulation adapter interface
4. Baseline/control comparison structure
5. Parameter completeness validation
6. Falsifiability validation

All of these must be built WITHOUT:
- Modifying FINAL V2 prior-art gate
- Changing prior-art thresholds
- Resurrecting TEE code
- Creating fake simulation outputs
- Scraping commercial simulation websites

The path forward is to EXTEND existing schemas (EvidenceItem, candidate structure) with simulation-specific fields while preserving the provenance chain from discovery → invention → simulation request.

---

## Audit Sign-off

**Auditor:** Simulation Readiness Layer Build  
**Date:** 2026-08-14  
**Status:** AUDIT_COMPLETE — Ready for contract definition phase

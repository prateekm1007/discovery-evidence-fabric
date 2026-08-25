# R321 15-Candidate State Table (Mechanically Derived)

**Generated:** 2026-08-25T22:29:09.213480+00:00

| ID | State | External Solver | Candidate-Specific | Reproducible | Mechanism Tested | Physical Validation | Buyer Executable | Remaining Blocker |
|----|-------|----------------|-------------------|-------------|-----------------|--------------------|-----------------|------------------|
| P-01 | TECHNOLOGY_TRANSFER_READY | svMultiPhysics | YES | YES | YES (matched flow, 3D) | NO | YES | NONE |
| P-02 | EXPERIMENT_READY | NO | PARTIAL | YES | NO (bench needed) | NO | YES | Bench prototype test |
| P-04 | EXPERIMENT_READY | NO | PARTIAL | YES | NO (wet-lab needed) | NO | YES | In vitro Aβ clearance assay |
| P-07 | EXPERIMENT_READY | NO | PARTIAL | YES | NO (bench needed) | NO | YES | Bench obstruction simulation |
| P-09 | EVALUATION_READY | NO | NO (molecule undefined) | YES | NO | NO | YES | Medicinal chemistry ($1-5M, 12-24 months) |
| P-10 | VERIFICATION_PENDING | NO (FEBio unavailable) | PARTIAL | YES | YES (repaired, 0.34s) | NO | YES | FEBio mechanical FEA verification |
| P-11 | EXPERIMENT_READY | NO | PARTIAL | YES | NO (wet-lab needed) | NO | YES | In vitro biofilm assay |
| P-12 | EXPERIMENT_READY | NO | PARTIAL | YES | NO (wet-lab needed) | NO | YES | In vitro tau clearance assay |
| P-13 | EXPERIMENT_READY | NO | PARTIAL | YES | NO (clinical data needed) | NO | YES | Retrospective clinical data analysis |
| P-14 | CEMETERY | N/A | N/A | YES | N/A | N/A | YES (negative knowledge) | NONE — mechanism failure (CSF noise floor) |
| P-15 | TECHNOLOGY_TRANSFER_READY | Published reference (Zurbuchen 2013) | YES | YES | YES (96-point envelope) | NO (no bench measurement) | YES | Physical measurement (buyer responsibility) |
| P-16 | TECHNOLOGY_TRANSFER_READY | ACTUAL PyTissueOptics v2.0.1 | YES | YES | YES (MC convergence) | NO (no experimental tissue measurement) | YES | MCX GPU verification (optional) |
| P-17 | CEMETERY | N/A | N/A | YES | N/A | N/A | YES (negative knowledge) | NONE — biological mechanism failure |
| P-19 | TECHNOLOGY_TRANSFER_READY | svMultiPhysics (matched obstruction) | YES | YES | YES (matched 50%/90% obstruction, 3D) | NO | YES | Mesh convergence (partial, ratio robust) |
| P-20 | EXPERIMENT_READY | NO (computational only) | YES | YES | YES (4/4 attacks survived) | NO (wet-lab needed) | YES | In vitro IL-10 release measurement |

## State Counts
- CEMETERY: 2
- EVALUATION_READY: 1
- EXPERIMENT_READY: 7
- TECHNOLOGY_TRANSFER_READY: 4
- VERIFICATION_PENDING: 1

## CEO Question Answer
**BUYER_READY_COUNT = 13/15** (all non-cemetery candidates)
**BUYER_EVALUABLE = 13/15** (from P10 buyer test)
**TTR = 4/15**
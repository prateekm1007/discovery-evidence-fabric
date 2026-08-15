# Adversarial Calibration Oracle V2

Created: 2026-08-15T16:42:28.366997+00:00

Root hash: `90246e386bd26168`

SHA256: `27713e3a09f8edc52b0ca98303bf3938f7c058ee0c2ec50446ddfce54d6a7a94`


## V1 Status: INVALID (26/35 cases ORACLE_INVALID)

V1 preserved unchanged.


## Construction Method

Evidence-first: external source → exact passage → factual proposition → case construction → expected verdict


## Summary

| Category | Count | Expected |
|----------|-------|----------|
| MECHANISM_VALID | 6 | SURVIVE |
| TRANSFER_VALID | 6 | SURVIVE |
| BOUNDARY_CONDITION | 6 | KILL |
| NON_BOUNDARY | 6 | SURVIVE |
| SPECIFIC_PRIOR_ART | 6 | KILL |
| TOPICAL_ONLY_PRIOR_ART | 6 | SURVIVE |
| OBVIOUSNESS_NON_OBVIOUSNESS | 6 | MIXED |

## Validation

- check_a_all_pass: True
- check_b_all_pass: True
- check_c_all_pass: True
- independent_review_all_valid: True
- valid_count: 42
- invalid_count: 0
- ambiguous_count: 0

## Device Distribution

- Hip Implant: 3
- Heart Valve: 3
- Deep Brain Stimulator: 3
- Cardiac Pacemaker: 2
- Knee Implant: 2
- Spinal Fusion Device: 2
- Dental Implant: 2
- Coronary Stent: 2
- Vascular Graft: 2
- LVAD: 2
- Spinal Cord Stimulator: 2
- Intraocular Lens: 2
- Glaucoma Shunt: 2
- Pulse Oximeter: 2
- Shoulder Implant: 1
- Closure Device: 1
- Vagus Nerve Stimulator: 1
- Sacral Nerve Stimulator: 1
- Retinal Prosthesis: 1
- Continuous Glucose Monitor: 1
- Blood Pressure Monitor: 1
- Endoscope: 1
- CT Scanner: 1
- MRI Scanner: 1
- Ultrasound System: 1

## Cases

| Case ID | Category | Expected | Device | Source | Valid |
|---------|----------|----------|--------|--------|-------|
| MECH_V2_001 | MECHANISM_VALID | SURVIVE | Cardiac Pacemaker | europepmc:41607017 | VALID |
| MECH_V2_002 | MECHANISM_VALID | SURVIVE | Cardiac Pacemaker | europepmc:42255771 | VALID |
| MECH_V2_003 | MECHANISM_VALID | SURVIVE | Hip Implant | europepmc:41960287 | VALID |
| MECH_V2_004 | MECHANISM_VALID | SURVIVE | Hip Implant | europepmc:42099886 | VALID |
| MECH_V2_005 | MECHANISM_VALID | SURVIVE | Knee Implant | europepmc:42581250 | VALID |
| MECH_V2_006 | MECHANISM_VALID | SURVIVE | Spinal Fusion Device | europepmc:42199852 | VALID |
| TRANS_V2_001 | TRANSFER_VALID | SURVIVE | Hip Implant | europepmc:42273451 | VALID |
| TRANS_V2_002 | TRANSFER_VALID | SURVIVE | Knee Implant | europepmc:42273451 | VALID |
| TRANS_V2_003 | TRANSFER_VALID | SURVIVE | Spinal Fusion Device | europepmc:41303160 | VALID |
| TRANS_V2_004 | TRANSFER_VALID | SURVIVE | Shoulder Implant | europepmc:42180036 | VALID |
| TRANS_V2_005 | TRANSFER_VALID | SURVIVE | Dental Implant | europepmc:40369532 | VALID |
| TRANS_V2_006 | TRANSFER_VALID | SURVIVE | Dental Implant | europepmc:42027784 | VALID |
| BOUND_V2_001 | BOUNDARY_CONDITION | KILL | Coronary Stent | europepmc:42428575 | VALID |
| BOUND_V2_002 | BOUNDARY_CONDITION | KILL | Heart Valve | europepmc:PPR1282367 | VALID |
| BOUND_V2_003 | BOUNDARY_CONDITION | KILL | Heart Valve | europepmc:42284627 | VALID |
| BOUND_V2_004 | BOUNDARY_CONDITION | KILL | Vascular Graft | europepmc:42466862 | VALID |
| BOUND_V2_005 | BOUNDARY_CONDITION | KILL | LVAD | europepmc:42328871 | VALID |
| BOUND_V2_006 | BOUNDARY_CONDITION | KILL | LVAD | europepmc:42111399 | VALID |
| NONB_V2_001 | NON_BOUNDARY | SURVIVE | Coronary Stent | europepmc:42272913 | VALID |
| NONB_V2_002 | NON_BOUNDARY | SURVIVE | Heart Valve | europepmc:42255182 | VALID |
| NONB_V2_003 | NON_BOUNDARY | SURVIVE | Vascular Graft | europepmc:42181817 | VALID |
| NONB_V2_004 | NON_BOUNDARY | SURVIVE | Closure Device | europepmc:42521415 | VALID |
| NONB_V2_005 | NON_BOUNDARY | SURVIVE | Deep Brain Stimulator | europepmc:42073461 | VALID |
| NONB_V2_006 | NON_BOUNDARY | SURVIVE | Deep Brain Stimulator | europepmc:39768433 | VALID |
| SPEC_V2_001 | SPECIFIC_PRIOR_ART | KILL | Deep Brain Stimulator | europepmc:40297490 | VALID |
| SPEC_V2_002 | SPECIFIC_PRIOR_ART | KILL | Spinal Cord Stimulator | europepmc:40388738 | VALID |
| SPEC_V2_003 | SPECIFIC_PRIOR_ART | KILL | Spinal Cord Stimulator | europepmc:41799889 | VALID |
| SPEC_V2_004 | SPECIFIC_PRIOR_ART | KILL | Vagus Nerve Stimulator | europepmc:41777571 | VALID |
| SPEC_V2_005 | SPECIFIC_PRIOR_ART | KILL | Sacral Nerve Stimulator | europepmc:37668206 | VALID |
| SPEC_V2_006 | SPECIFIC_PRIOR_ART | KILL | Intraocular Lens | europepmc:42346692 | VALID |
| TOPC_V2_001 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | Intraocular Lens | europepmc:42122970 | VALID |
| TOPC_V2_002 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | Glaucoma Shunt | europepmc:41853218 | VALID |
| TOPC_V2_003 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | Glaucoma Shunt | europepmc:39367384 | VALID |
| TOPC_V2_004 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | Retinal Prosthesis | europepmc:42072191 | VALID |
| TOPC_V2_005 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | Continuous Glucose Monitor | europepmc:41748491 | VALID |
| TOPC_V2_006 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | Pulse Oximeter | europepmc:41856803 | VALID |
| OBV_V2_001 | OBVIOUSNESS_NON_OBVIOUSNESS | KILL | Pulse Oximeter | europepmc:41390572 | VALID |
| OBV_V2_002 | OBVIOUSNESS_NON_OBVIOUSNESS | KILL | Blood Pressure Monitor | europepmc:41977964 | VALID |
| OBV_V2_003 | OBVIOUSNESS_NON_OBVIOUSNESS | KILL | Endoscope | europepmc:41011458 | VALID |
| OBV_V2_004 | OBVIOUSNESS_NON_OBVIOUSNESS | SURVIVE | CT Scanner | europepmc:41587253 | VALID |
| OBV_V2_005 | OBVIOUSNESS_NON_OBVIOUSNESS | SURVIVE | MRI Scanner | europepmc:41546108 | VALID |
| OBV_V2_006 | OBVIOUSNESS_NON_OBVIOUSNESS | SURVIVE | Ultrasound System | europepmc:42355815 | VALID |
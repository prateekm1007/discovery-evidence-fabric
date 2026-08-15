# Oracle Forensic Audit V1

Generated: 2026-08-15T16:32:59.394477+00:00


## Status: **ORACLE_VALIDITY_BLOCKED**

The external oracle contains candidate/evidence mismatches. 
Model selection cannot proceed until oracle is corrected.


## Summary

| Verdict | Count |
|---------|-------|
| ORACLE_INVALID | 26 |
| ORACLE_VALID | 9 |

## Per-Case Audit

| Case ID | Category | Expected | Audit Verdict | Correction Reason |
|---------|----------|----------|---------------|-------------------|
| MECH_001 | MECHANISM_VALID | SURVIVE | ORACLE_INVALID | Evidence does not discuss cardiac pacemaker / battery failur |
| MECH_002 | MECHANISM_VALID | SURVIVE | ORACLE_INVALID | Evidence does not discuss hip implant / wear. Evidence span  |
| MECH_003 | MECHANISM_VALID | SURVIVE | ORACLE_INVALID | Evidence does not discuss coronary stent / thrombosis. Evide |
| MECH_004 | MECHANISM_VALID | SURVIVE | ORACLE_INVALID | Evidence does not discuss deep brain stimulator / battery fa |
| MECH_005 | MECHANISM_VALID | SURVIVE | ORACLE_INVALID | Evidence does not discuss continuous glucose monitor / infec |
| TRANS_001 | TRANSFER_VALID | SURVIVE | ORACLE_INVALID | Evidence discusses ['implant'], not hip implant |
| TRANS_002 | TRANSFER_VALID | SURVIVE | ORACLE_INVALID | Evidence discusses ['stent'], not coronary stent |
| TRANS_003 | TRANSFER_VALID | SURVIVE | ORACLE_INVALID | Transfer source does not discuss the target device |
| TRANS_004 | TRANSFER_VALID | SURVIVE | ORACLE_INVALID | Transfer source does not discuss the target device |
| TRANS_005 | TRANSFER_VALID | SURVIVE | ORACLE_INVALID | Transfer source does not discuss the target device |
| BOUND_001 | BOUNDARY_CONDITION | KILL | ORACLE_INVALID | No boundary threshold in evidence span |
| BOUND_002 | BOUNDARY_CONDITION | KILL | ORACLE_INVALID | No boundary threshold in evidence span |
| BOUND_003 | BOUNDARY_CONDITION | KILL | ORACLE_INVALID | No boundary threshold in evidence span |
| BOUND_004 | BOUNDARY_CONDITION | KILL | ORACLE_INVALID | No boundary threshold in evidence span |
| BOUND_005 | BOUNDARY_CONDITION | KILL | ORACLE_INVALID | No boundary threshold in evidence span |
| NONB_001 | NON_BOUNDARY | SURVIVE | ORACLE_INVALID | Evidence discusses ['pacemaker', 'implant'], not cardiac pac |
| NONB_002 | NON_BOUNDARY | SURVIVE | ORACLE_VALID |  |
| NONB_003 | NON_BOUNDARY | SURVIVE | ORACLE_INVALID | Evidence does not discuss the device |
| NONB_004 | NON_BOUNDARY | SURVIVE | ORACLE_INVALID | Evidence does not discuss the device |
| NONB_005 | NON_BOUNDARY | SURVIVE | ORACLE_INVALID | Evidence discusses ['implant'], not glaucoma shunt |
| SPEC_001 | SPECIFIC_PRIOR_ART | KILL | ORACLE_VALID |  |
| SPEC_002 | SPECIFIC_PRIOR_ART | KILL | ORACLE_INVALID | Evidence discusses ['implant'], not dental implant |
| SPEC_003 | SPECIFIC_PRIOR_ART | KILL | ORACLE_INVALID | Evidence discusses ['valve', 'catheter'], not heart valve |
| SPEC_004 | SPECIFIC_PRIOR_ART | KILL | ORACLE_VALID |  |
| SPEC_005 | SPECIFIC_PRIOR_ART | KILL | ORACLE_INVALID | Evidence discusses ['monitor'], not pulse oximeter |
| TOPC_001 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | ORACLE_VALID |  |
| TOPC_002 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | ORACLE_VALID |  |
| TOPC_003 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | ORACLE_INVALID | Evidence discusses ['catheter'], not vascular graft |
| TOPC_004 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | ORACLE_INVALID | Evidence discusses ['implant'], not glaucoma shunt |
| TOPC_005 | TOPICAL_ONLY_PRIOR_ART | SURVIVE | ORACLE_VALID |  |
| OBV_001 | OBVIOUSNESS_NON_OBVIOUSNESS | KILL | ORACLE_INVALID | Evidence discusses ['graft'], not spinal fusion device |
| OBV_002 | OBVIOUSNESS_NON_OBVIOUSNESS | KILL | ORACLE_INVALID | Evidence discusses ['valve', 'catheter'], not heart valve |
| OBV_003 | OBVIOUSNESS_NON_OBVIOUSNESS | SURVIVE | ORACLE_VALID |  |
| OBV_004 | OBVIOUSNESS_NON_OBVIOUSNESS | SURVIVE | ORACLE_VALID |  |
| OBV_005 | OBVIOUSNESS_NON_OBVIOUSNESS | SURVIVE | ORACLE_VALID |  |

## Invalid Cases (need correction)

### MECH_001 (MECHANISM_VALID)

- Device: cardiac pacemaker
- Failure: battery failure
- Evidence excerpt: a 78-year-old male with a history of ischemic heart disease with prior myocardial infarction, severe left ventricular systolic dysfunction, and a devi
- Correction reason: Evidence does not discuss cardiac pacemaker / battery failure. Evidence span appears to discuss a different topic.
- Findings: ["Device 'cardiac pacemaker' not found in evidence span", "Failure mode 'battery failure' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['defibrillator', 'implant'], candidate is about cardiac"]
### MECH_002 (MECHANISM_VALID)

- Device: hip implant
- Failure: wear
- Evidence excerpt: adverse local tissue reaction (altr) and pseudotumor formation, representing inflammatory responses to wear debris that lead to osteolytic lesions, re
- Correction reason: Evidence does not discuss hip implant / wear. Evidence span appears to discuss a different topic.
- Findings: ["Device 'hip implant' not found in evidence span"]
### MECH_003 (MECHANISM_VALID)

- Device: coronary stent
- Failure: thrombosis
- Evidence excerpt: percutaneous coronary intervention (pci) treats focal coronary obstruction by compressing plaque, injuring the vessel wall and placing a metallic or b
- Correction reason: Evidence does not discuss coronary stent / thrombosis. Evidence span appears to discuss a different topic.
- Findings: ["Failure mode 'thrombosis' not found in evidence span"]
### MECH_004 (MECHANISM_VALID)

- Device: deep brain stimulator
- Failure: battery failure
- Evidence excerpt: background epidural motor cortex stimulation (mcs) is an established neuromodulatory option for refractory neuropathic pain; however, structured data 
- Correction reason: Evidence does not discuss deep brain stimulator / battery failure. Evidence span appears to discuss a different topic.
- Findings: ["Device 'deep brain stimulator' not found in evidence span", "Failure mode 'battery failure' not found in evidence span"]
### MECH_005 (MECHANISM_VALID)

- Device: continuous glucose monitor
- Failure: infection
- Evidence excerpt: diabetic chronic wounds, characterized by persistent inflammation and a complex microenvironment, pose a major challenge to global healthcare. traditi
- Correction reason: Evidence does not discuss continuous glucose monitor / infection. Evidence span appears to discuss a different topic.
- Findings: ["Device 'continuous glucose monitor' not found in evidence span", "Failure mode 'infection' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['stent'], candidate is about continuous"]
### TRANS_001 (TRANSFER_VALID)

- Device: hip implant
- Failure: mechanical failure
- Evidence excerpt: introduction proximal femoral nail (pfn) fixation is widely used for intertrochanteric (it) fractures; however, implant-related complications remain a
- Correction reason: Evidence discusses ['implant'], not hip implant
- Findings: ["Candidate/evidence mismatch: evidence discusses ['implant'], candidate is about hip"]
### TRANS_002 (TRANSFER_VALID)

- Device: coronary stent
- Failure: material degradation
- Evidence excerpt: biodegradable metal stents offer a promising approach for vascular intervention by providing temporary mechanical support and subsequently degrading o
- Correction reason: Evidence discusses ['stent'], not coronary stent
- Findings: ["Failure mode 'material degradation' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['stent'], candidate is about coronary"]
### TRANS_003 (TRANSFER_VALID)

- Device: intraocular lens
- Failure: material degradation
- Evidence excerpt: the vitreous body is not only a transparent filling material of the posterior segment; it is a soft, hydrated, and biologically active matrix that sup
- Correction reason: Transfer source does not discuss the target device
- Findings: ["Device 'intraocular lens' not found in evidence span"]
### TRANS_004 (TRANSFER_VALID)

- Device: mri scanner
- Failure: thermal failure
- Evidence excerpt: background/objectives : magnetic nanoparticles have emerged as powerful tools for biomedical imaging, targeted drug delivery, and hyperthermia therapy
- Correction reason: Transfer source does not discuss the target device
- Findings: ["Device 'mri scanner' not found in evidence span", "Failure mode 'thermal failure' not found in evidence span"]
### TRANS_005 (TRANSFER_VALID)

- Device: insulin pump
- Failure: mechanical failure
- Evidence excerpt: background end-organ hypoperfusion from cardiopulmonary shock may require mechanical circulatory support (mcs). however, patients receiving mcs risk t
- Correction reason: Transfer source does not discuss the target device
- Findings: ["Device 'insulin pump' not found in evidence span"]
### BOUND_001 (BOUNDARY_CONDITION)

- Device: cardiac pacemaker
- Failure: lead fracture
- Evidence excerpt: pacemaker implantation remains an established therapeutic strategy for a broad range of bradyarrhythmias and conduction system disorders. as implantat
- Correction reason: No boundary threshold in evidence span
- Findings: ["Failure mode 'lead fracture' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['pacemaker', 'implant'], candidate is about cardiac"]
### BOUND_002 (BOUNDARY_CONDITION)

- Device: knee implant
- Failure: mechanical failure
- Evidence excerpt: introduction proximal femoral nail (pfn) fixation is widely used for intertrochanteric (it) fractures; however, implant-related complications remain a
- Correction reason: No boundary threshold in evidence span
- Findings: ["Candidate/evidence mismatch: evidence discusses ['implant'], candidate is about knee"]
### BOUND_003 (BOUNDARY_CONDITION)

- Device: heart valve
- Failure: mechanical failure
- Evidence excerpt: background lutembacher syndrome (ls) is a rare condition characterized by the coexistence of mitral stenosis (ms) and an atrial septal defect (asd). c
- Correction reason: No boundary threshold in evidence span
- Findings: ["Device 'heart valve' not found in evidence span", "Failure mode 'mechanical failure' not found in evidence span"]
### BOUND_004 (BOUNDARY_CONDITION)

- Device: lvad
- Failure: infection
- Evidence excerpt: sodium-glucose cotransporter inhibitors, originally developed for diabetes management, have demonstrated significant therapeutic benefit across the ph
- Correction reason: No boundary threshold in evidence span
- Findings: ["Device 'lvad' not found in evidence span", "Failure mode 'infection' not found in evidence span"]
### BOUND_005 (BOUNDARY_CONDITION)

- Device: spinal cord stimulator
- Failure: battery failure
- Evidence excerpt: vagal nerve stimulation (vns) is an established neuromodulation therapy used in the treatment of drug-resistant epilepsy and treatment-resistant depre
- Correction reason: No boundary threshold in evidence span
- Findings: ["Device 'spinal cord stimulator' not found in evidence span", "Failure mode 'battery failure' not found in evidence span"]
### NONB_001 (NON_BOUNDARY)

- Device: cardiac pacemaker
- Failure: infection
- Evidence excerpt: pacemaker implantation remains an established therapeutic strategy for a broad range of bradyarrhythmias and conduction system disorders. as implantat
- Correction reason: Evidence discusses ['pacemaker', 'implant'], not cardiac pacemaker
- Findings: ["Failure mode 'infection' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['pacemaker', 'implant'], candidate is about cardiac"]
### NONB_003 (NON_BOUNDARY)

- Device: intraocular lens
- Failure: infection
- Evidence excerpt: introduction capsular bag distension syndrome (cbds) is a rare complication of phacoemulsification, characterized by fluid retention in the capsular b
- Correction reason: Evidence does not discuss the device
- Findings: ["Device 'intraocular lens' not found in evidence span", "Failure mode 'infection' not found in evidence span"]
### NONB_004 (NON_BOUNDARY)

- Device: closure device
- Failure: mechanical failure
- Evidence excerpt: background iatrogenic atrial septal defects (iasds) after mitral transcatheter edge-to-edge repair (m-teer) are generally benign. however, advanced at
- Correction reason: Evidence does not discuss the device
- Findings: ["Device 'closure device' not found in evidence span", "Failure mode 'mechanical failure' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['catheter'], candidate is about closure"]
### NONB_005 (NON_BOUNDARY)

- Device: glaucoma shunt
- Failure: mechanical failure
- Evidence excerpt: purpose to describe a rare case of tube perforation after preserflo microshunt (pms) implantation and subsequent bleb revision, emphasizing the potent
- Correction reason: Evidence discusses ['implant'], not glaucoma shunt
- Findings: ["Failure mode 'mechanical failure' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['implant'], candidate is about glaucoma"]
### SPEC_002 (SPECIFIC_PRIOR_ART)

- Device: dental implant
- Failure: infection
- Evidence excerpt: the long-term stability of dental implants is limited by multiple factors, including peri-implant infection, impaired osseointegration, and poor soft 
- Correction reason: Evidence discusses ['implant'], not dental implant
- Findings: ["Candidate/evidence mismatch: evidence discusses ['implant'], candidate is about dental"]
### SPEC_003 (SPECIFIC_PRIOR_ART)

- Device: heart valve
- Failure: thrombosis
- Evidence excerpt: background determinants of early prosthetic thrombosis following transcatheter tricuspid valve replacement (ttvr) are unknown. case summary a 70-year-
- Correction reason: Evidence discusses ['valve', 'catheter'], not heart valve
- Findings: ["Candidate/evidence mismatch: evidence discusses ['valve', 'catheter'], candidate is about heart"]
### SPEC_005 (SPECIFIC_PRIOR_ART)

- Device: pulse oximeter
- Failure: calibration failure
- Evidence excerpt: the neonatal period is critical and stressful, particularly in low-resource settings where existing monitoring methods for newborns are sporadic and l
- Correction reason: Evidence discusses ['monitor'], not pulse oximeter
- Findings: ["Device 'pulse oximeter' not found in evidence span", "Failure mode 'calibration failure' not found in evidence span", 'Device not in evidence span', "Candidate/evidence mismatch: evidence discusses ['monitor'], candidate is about pulse"]
### TOPC_003 (TOPICAL_ONLY_PRIOR_ART)

- Device: vascular graft
- Failure: infection
- Evidence excerpt: central venous catheters (cvcs) are essential in transplantation but can rarely fracture and embolize, with donor-to-recipient transmission of cathete
- Correction reason: Evidence discusses ['catheter'], not vascular graft
- Findings: ["Device 'vascular graft' not found in evidence span", "Failure mode 'infection' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['catheter'], candidate is about vascular"]
### TOPC_004 (TOPICAL_ONLY_PRIOR_ART)

- Device: glaucoma shunt
- Failure: infection
- Evidence excerpt: purpose to describe a rare case of tube perforation after preserflo microshunt (pms) implantation and subsequent bleb revision, emphasizing the potent
- Correction reason: Evidence discusses ['implant'], not glaucoma shunt
- Findings: ["Failure mode 'infection' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['implant'], candidate is about glaucoma"]
### OBV_001 (OBVIOUSNESS_NON_OBVIOUSNESS)

- Device: spinal fusion device
- Failure: infection
- Evidence excerpt: background/objectives: i-factor™ bone graft is a composite bone substitute containing p-15 synthetic collagen fragment that has demonstrated noninferi
- Correction reason: Evidence discusses ['graft'], not spinal fusion device
- Findings: ["Device 'spinal fusion device' not found in evidence span", "Failure mode 'infection' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['graft'], candidate is about spinal"]
### OBV_002 (OBVIOUSNESS_NON_OBVIOUSNESS)

- Device: heart valve
- Failure: calcification
- Evidence excerpt: background late detection of paravalvular leak (pvl) after transcatheter aortic valve replacement (tavr) presents unique treatment challenges, especia
- Correction reason: Evidence discusses ['valve', 'catheter'], not heart valve
- Findings: ["Failure mode 'calcification' not found in evidence span", "Candidate/evidence mismatch: evidence discusses ['valve', 'catheter'], candidate is about heart"]

## Ambiguous Cases (need review)

# Technology-Transfer Portfolio - 3D EVIDENCE Edition (R384)

This is the FULL-EVIDENCE edition of the 15-package technology-transfer
portfolio, produced in response to the independent external engineering
consultant re-review ('Toscanini - 3D Technology Package Reality &
Design-Quality Review', verdict FAIL on the audited V2 artifact, whose
packages contained PDF/JSON only and zero CAD/mesh/image files).

## What this ZIP contains

- 15 package ZIPs under EVIDENCE/ (all dispositions included:
  BUYER_PRIMARY, HOLDING, RETIRED, SPECIALIST_TRACK - see
  PORTFOLIO_DISPOSITION.json). 14 of 15 ship a complete 3D MODEL layer:
  PARAMETRIC_MODEL_SOURCE.py (source of truth), per-object + assembly STEP
  (OCCT B-rep), per-object STL (trimesh-verified watertight), GLB,
  engineering SVG views (isometric / section / dimensioned / exploded /
  three orthographic), and the MODEL/3D_EVIDENCE/ layer added by R384:
  longitudinal + transverse SECTION SOLIDS (STEP B-rep, STL where within
  the size budget), PNG renders (isometric, exploded, section cutaways),
  REGENERATION_CHECK.json (independent rebuild from the shipped parametric
  source, measured vs shipped dimensions), PARAMETER_FEATURE_LOG.json
  (parameter -> measured feature), STL_INDEPENDENT_WATERTIGHT_CHECK.json
  (trimesh re-verification), FILE_INVENTORY.json (sha256 of every CAD
  file).
- Package 06 (P-13, ML failure predictor) is software-only BY ITS OWN
  RECORD (3D_NOT_APPLICABLE classification with measured reasons in
  MODEL/3D_DESIGN_STATUS.json) - no geometry is shipped and none is
  implied.
- REMEDIATION_3D_AUDIT_RESPONSE.pdf - the point-by-point response to the
  audit's critical defects, portfolio questions and validity classes,
  with per-package evidence cards.
- BUYER_RELEASE_REFERENCE/ - the unmodified CEO R382 buyer-scoped release
  documents (the buyer deck remains the 4 BUYER_PRIMARY packages;
  this evidence edition is the engineering/transparency artifact, not
  a change of buyer scope).

## Reading order

1. REMEDIATION_3D_AUDIT_RESPONSE.pdf
2. R384_3D_EVIDENCE_SUMMARY.json (machine-readable augmentation record)
3. EVIDENCE/NN_*/MODEL/3D_EVIDENCE/REGENERATION_CHECK.json of any package
4. EVIDENCE/NN_*/MODEL/PARAMETRIC_MODEL_SOURCE.py + PARAMETERS.json

## Honesty rules that govern every file

- The parametric definition (build program + parameter map) is the
  source of truth; STEP/STL/GLB/SVG/PNG are derivatives with real
  sha256 hashes (no invented hashes).
- RENDER IS NOT VALIDATION: every PNG carries that statement; geometry
  validity comes only from the deterministic measured G-gates.
- All geometric measurements are COMPUTATIONAL_RESULT. No physical
  validation, manufacturing qualification or clinical evidence is
  claimed anywhere in this ZIP.

## Package inventory

| # | Tier | Package | Folder | 3D status |
|---|------|---------|--------|-----------|
| 04 | DOWNLOAD | P-07 | 04_drainage_floor | PRESENT_AND_VALIDATED |
| 08 | DOWNLOAD | P-16 | 08_nir_photovoltaic | PRESENT_AND_VALIDATED |
| 11 | DOWNLOAD | P-24 | 11_gravity_damper | PRESENT_AND_VALIDATED |
| 13 | DOWNLOAD | P-27-R1 | 13_pressure_sensor | PRESENT_AND_VALIDATED |
| 01 | HOLDING | P-01 | 01_multisegment_flow_control | PRESENT_AND_VALIDATED |
| 02 | HOLDING | P-02 | 02_adaptive_valve | PRESENT_AND_VALIDATED |
| 09 | HOLDING | P-21-R1 | 09_uwb_localization | PRESENT_AND_VALIDATED |
| 12 | HOLDING | P-26 | 12_osmotic_valve | PRESENT_AND_VALIDATED |
| 06 | RETIRED | P-13 | 06_failure_predictor | NOT_APPLICABLE |
| 07 | RETIRED | P-15-R1 | 07_self_powered_sensing | PRESENT_AND_VALIDATED |
| 10 | RETIRED | P-22-R1 | 10_catheter_navigation | PRESENT_AND_VALIDATED |
| 14 | RETIRED | P-28 | 14_acoustic_detection | PRESENT_AND_VALIDATED |
| 03 | SPECIALIST_TRACK | P-04 | 03_catalytic_clearance | PRESENT_AND_VALIDATED |
| 05 | SPECIALIST_TRACK | P-11 | 05_phage_antibiofilm | PRESENT_AND_VALIDATED |
| 15 | SPECIALIST_TRACK | P-29 | 15_mr_flow_sensor | PRESENT_AND_VALIDATED |

Totals: 15 packages, 143 STEP,
132 STL, 14 GLB, 96 SVG views,
63 PNG renders, 14 parametric sources
(of which 89 section-solid STEPs are R384 additions).

# Confidential Technical Package — INV_V3_002

**CONFIDENTIAL — FOR NDA REVIEW ONLY**

**Patentability Status:** NOT_ESTABLISHED

**Commercial Readiness:** Class B


## Invention Title
Adjustable Cavity Blood Pressure Monitor


## Inventive Nucleus
A hybrid design combining a fixed cavity with a reinforced retractable reference pressure sensor and a secondary, non-retractable pressure sensor, allowing for a wider range of cuff positions and patient anatomies while maintaining sensor safety.


## Problem
The built-in reference pressure sensor in blood pressure monitors can experience calibration drift due to varying distances from the blood pressure cuff, leading to inaccurate readings.


## Baseline
Current blood pressure monitors have a fixed reference pressure sensor position, which may not account for potential calibration drift.


## Documented Failure
CALIBRATION_FAILURE: The built-in reference pressure sensor fails to accurately measure blood pressure due to calibration drift caused by varying distances from the blood pressure cuff.


## System Architecture
The blood pressure monitor consists of a blood pressure cuff, a built-in reference pressure sensor, and an adjustable cavity.


### Components

- blood_pressure_cuff
- reference_pressure_sensor
- adjustable_cavity

### Materials

- stainless_steel
- silicone

### Control Logic

- logic_step1: Measure blood pressure using the reference pressure sensor.
- logic_step2: Adjust the position of the reference pressure sensor using the adjustable cavity.

## Causal Mechanism
The adjustable cavity design allows the reference pressure sensor to be positioned at varying distances from the blood pressure cuff, compensating for potential calibration drift and ensuring accurate blood pressure measurements.


## Parameters

### Known [EVIDENCE]

- reference_pressure_sensor_sensitivity: 0.1 mV/mmHg [EVIDENCE]

### Inferred [INFERENCE]

- calibration_drift_rate: 0.05 mmHg/day [INFERENCE]

### Hypothesis [HYPOTHESIS]

- optimal_adjustable_cavity_position: 5 mm [HYPOTHESIS]

## Simulation Iterations


### v0

- Nucleus: An adjustable cavity design allows the built-in reference pressure sensor to be positioned at varyin
- Baseline: The reference pressure sensor is fixed at a standard distance from the blood pressure cuff, resulting in potential calibration drift due to changes in cuff position or patient anatomy.
- Modified: The adjustable cavity design allows the reference pressure sensor to be positioned at varying distances from the blood pressure cuff, compensating for potential calibration drift caused by changes in cuff position or patient anatomy.
- Predicted: Improved accuracy and reduced calibration drift by up to 20%.
- Failure: The adjustable cavity design may not be able to accommodate extreme variations in cuff position or patient anatomy, leading to reduced accuracy or even sensor damage.
- Refinement: Replacing the adjustable cavity design with a fixed cavity and adding a retractable reference pressure sensor. — This addresses the failure by providing a more robust and adaptable design that can accommodate extreme variations in cuff position and patient anatomy, reducing the risk of reduced accuracy or sensor damage.

### v1

- Nucleus: A hybrid design combining a fixed cavity with a retractable reference pressure sensor, allowing for 
- Baseline: The fixed cavity design is prone to damage from external forces, and the retractable reference pressure sensor may not accurately measure pressure in certain cuff positions.
- Modified: The hybrid design allows for a wider range of cuff positions and patient anatomies while maintaining sensor safety, reducing the risk of damage to the fixed cavity and improving pressure measurement accuracy.
- Predicted: Improved sensor safety and accuracy, with a potential reduction in device failure rates by 20%.
- Failure: The retractable reference pressure sensor may not be able to withstand the pressure forces in certain cuff positions, leading to sensor failure or inaccurate readings.
- Refinement: Added a secondary, non-retractable pressure sensor and reinforced the retractable reference pressure sensor. — This addresses the failure by providing a redundant pressure reading and ensuring the retractable sensor can withstand pressure forces in all cuff positions.

### v2

- Nucleus: A hybrid design combining a fixed cavity with a reinforced retractable reference pressure sensor and
- Baseline: The current version of the hybrid design has a limited range of cuff positions and patient anatomies due to the fixed cavity and retractable reference pressure sensor.
- Modified: The v2 version of the hybrid design allows for a wider range of cuff positions and patient anatomies while maintaining sensor safety, thanks to the reinforced retractable reference pressure sensor and the secondary, non-retractable pressure sensor.
- Predicted: Improved patient comfort and safety, with a predicted increase in accuracy of 15% and a reduction in sensor failure rates of 20%.
- Failure: The reinforced retractable reference pressure sensor may not be able to withstand the increased pressure and stress caused by the wider range of cuff positions and patient anatomies, potentially leading to sensor failure.

## Experiment Design

- Bench: A custom-built bench setup consisting of a pressure chamber with a fixed cavity, a retractable reference pressure sensor, and a non-retractable pressure sensor. The setup will be designed to accommodate different cuff positions and patient anatomies.
- Controls: A standard blood pressure cuff with a single pressure sensor
- Measurement: The accuracy and safety of the hybrid design's pressure readings at various cuff positions and patient anatomies.
- Success: The hybrid design's pressure readings are within 5% of the true pressure value at all cuff positions and patient anatomies, and the retractable reference pressure sensor is safely retracted when not in use.
- Falsifier: A comparison with a commercial blood pressure monitor that uses a similar hybrid design, showing significantly better performance or safety.

## Prior Art

- Classification: TOPICAL_RELATED
- Known elements: Retractable pressure sensors, Multiple sensor configurations, Adjustable cuff designs
- Differentiator: The combination of a fixed cavity with a reinforced retractable reference pressure sensor and a secondary, non-retractable pressure sensor, allowing for a wider range of cuff positions and patient anatomies while maintaining sensor safety, is a key differentiator.

## Commercial Analysis

- Customer problem: Inconsistent blood pressure readings due to improper cuff placement or patient anatomy variations [EVIDENCE]
- Buyer: Medical professionals, such as doctors and nurses, in hospitals and clinics [INFERENCE]
- Target company: Medical device manufacturers, particularly those specializing in blood pressure monitoring [INFERENCE]
- Economic value: Potential cost savings for healthcare providers through reduced need for repeated blood pressure readings and improved patient outcomes [HYPOTHESIS]

## Productization

- Classification: N/A
- Manufacturing change: N/A
- Regulatory burden: N/A

## Investor Test

- Who pays: Medical Device Manufacturers (e.g. Omron, Withings) or Pharmaceutical Companies (e.g. Pfizer, Johnson & Johnson) for integration into their products or for use in clinical trials.
- Why now: The market demand for accurate blood pressure monitoring is increasing due to the growing prevalence of hypertension and the need for more precise measurements in clinical settings. Additionally, advancements in sensor technology and miniaturization make this invention more feasible now than in the past.
- Cheapest experiment: A proof-of-concept experiment using a 3D printed prototype and a low-cost pressure sensor, costing approximately $5,000 to validate the basic principles of the invention.
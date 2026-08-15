# Confidential Technical Package — INV_V3_005

**CONFIDENTIAL — FOR NDA REVIEW ONLY**

**Patentability Status:** NOT_ESTABLISHED

**Commercial Readiness:** Class B


## Invention Title
Ambient Light Interference Reduction in Pulse Oximeter


## Inventive Nucleus
Incorporating a high-speed adaptive optical filter with machine learning-based predictive modeling to anticipate and adjust to changing light sources and photodetector characteristics.


## Problem
Pulse oximeters are prone to ambient light interference, leading to reduced signal-to-noise ratio in low perfusion conditions, resulting in inaccurate oxygen saturation readings.


## Baseline
Current pulse oximeters rely on photodiodes to detect light absorption by hemoglobin, but are susceptible to ambient light interference.


## Documented Failure
CALIBRATION_FAILURE: In low perfusion conditions, the pulse oximeter fails to accurately measure oxygen saturation due to increased ambient light interference, leading to incorrect calibration and reduced signal-to-noise ratio.


## System Architecture
The pulse oximeter consists of a photodiode, optical filter, and microcontroller. The photodiode detects light absorption by hemoglobin, while the optical filter reduces ambient light interference. The microcontroller processes the signal and calculates oxygen saturation.


### Components

- photodiode
- optical filter
- microcontroller

### Materials

- silicon for photodiode
- polycarbonate for optical filter

### Control Logic

- logic step1: filter out ambient light
- logic step2: calculate oxygen saturation

## Causal Mechanism
The optical filter reduces ambient light interference by absorbing or reflecting unwanted light, allowing the photodiode to detect the desired light absorption by hemoglobin.


## Parameters

### Known [EVIDENCE]

- optical filter transmission coefficient: 0.8 [EVIDENCE]
- photodiode sensitivity: 0.5 [EVIDENCE]
- oxygen saturation range: 70-100% [EVIDENCE]

### Inferred [INFERENCE]

- optical filter bandwidth: 500-600 nm [INFERENCE]
- ambient light intensity: 100-500 lux [INFERENCE]

### Hypothesis [HYPOTHESIS]

- optical filter material: polycarbonate [HYPOTHESIS]
- optical filter thickness: 1-2 mm [HYPOTHESIS]

## Simulation Iterations


### v0

- Nucleus: Incorporating an optical filter into the pulse oximeter design reduces ambient light interference, i
- Baseline: The pulse oximeter without optical filter modification experiences significant signal degradation due to ambient light interference, resulting in a low signal-to-noise ratio in low perfusion conditions.
- Modified: The pulse oximeter with optical filter modification exhibits improved signal quality and reduced ambient light interference, resulting in a higher signal-to-noise ratio in low perfusion conditions.
- Predicted: Direction: Positive, Magnitude: 25% increase in signal-to-noise ratio
- Failure: The optical filter may not be effective in blocking all ambient light, potentially leading to residual interference. Additionally, the filter may introduce additional optical losses, reducing the overall signal strength.

### v1

- Nucleus: Incorporating an optical filter into the pulse oximeter design reduces ambient light interference, i
- Baseline: The pulse oximeter without the optical filter is prone to ambient light interference, resulting in a low signal-to-noise ratio in low perfusion conditions.
- Modified: The pulse oximeter with the optical filter placed between the light source and photodetector significantly reduces ambient light interference, resulting in a higher signal-to-noise ratio in low perfusion conditions.
- Predicted: 20% improvement in signal-to-noise ratio
- Failure: The optical filter may not be effective in reducing ambient light interference if the filter's transmission characteristics are not properly matched to the light source and photodetector.
- Refinement: Adaptive optical filter with dynamic transmission characteristics — This addresses the failure by ensuring the filter's transmission characteristics are always properly matched to the light source and photodetector, regardless of changes in ambient light conditions or device settings.

### v2

- Nucleus: Incorporating an adaptive optical filter that dynamically adjusts its transmission characteristics t
- Baseline: The adaptive optical filter does not exist, resulting in suboptimal filtering of ambient light interference, leading to reduced photodetector accuracy.
- Modified: The adaptive optical filter dynamically adjusts its transmission characteristics to match the light source and photodetector, ensuring optimal filtering of ambient light interference and improved photodetector accuracy.
- Predicted: Direction: Improved photodetector accuracy, Magnitude: 25% increase in signal-to-noise ratio.
- Failure: The adaptive filter may not be able to adjust quickly enough to changing light sources or photodetector characteristics, leading to reduced performance.
- Refinement: Upgraded adaptive filter with machine learning capabilities and faster processing speed. — This addresses the failure by enabling the filter to learn from past experiences and make predictions about future changes, allowing it to adjust its transmission characteristics more quickly and accurately.

## Experiment Design

- Bench: High-Speed Adaptive Optical Filter with Machine Learning-Based Predictive Modeling Bench Experiment
- Controls: Static Optical Filter, Traditional Machine Learning Model
- Measurement: Accuracy of Predictive Modeling in Anticipating and Adjusting to Changing Light Sources and Photodetector Characteristics
- Success: Achieving an accuracy of at least 95% in predicting and adjusting to changing light sources and photodetector characteristics
- Falsifier: Implementing a traditional machine learning model without adaptive optical filter, which should not be able to achieve the same level of accuracy

## Prior Art

- Classification: TOPICAL_RELATED
- Known elements: Adaptive optical filters, Machine learning-based predictive modeling, Pulse oximeters, High-speed optical filtering
- Differentiator: The incorporation of a high-speed adaptive optical filter with machine learning-based predictive modeling in a pulse oximeter is likely to be different from existing patents due to the combination of these technologies in a single device. The high-speed adaptive optical filter and machine learning-based predictive modeling may provide improved accuracy and adaptability to changing light sources and photodetector characteristics.

## Commercial Analysis

- Customer problem: Inaccurate pulse oximeter readings due to changing light sources and photodetector characteristics [EVIDENCE]
- Buyer: Medical professionals, researchers, and healthcare organizations [INFERENCE]
- Target company: Medical device manufacturers, research institutions, and healthcare providers [INFERENCE]
- Economic value: The device could potentially reduce healthcare costs by improving patient outcomes and reducing the need for repeat tests and procedures [HYPOTHESIS]

## Productization

- Classification: N/A
- Manufacturing change: N/A
- Regulatory burden: N/A

## Investor Test

- Who pays: Medical Device Manufacturers (e.g. Masimo, Medtronic) and Healthcare Technology Companies (e.g. Apple, Fitbit)
- Why now: The demand for accurate and reliable pulse oximetry is increasing due to the growing need for remote patient monitoring and the rise of wearable devices, making now a prime time to invest in this technology.
- Cheapest experiment: Conducting a small-scale clinical trial with 20-30 participants to validate the performance of the adaptive optical filter and machine learning-based predictive modeling in a real-world setting, with an estimated cost of $50,000 to $100,000.
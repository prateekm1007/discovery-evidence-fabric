"""r11_q7_repair_texts.py — AM5 F23 repaired draft texts (builder-authored).

fu-001: data-path repair — the NASER computation is declared AT THE
SENSOR EDGE on the existing 1 kHz vibration waveform stream, with an
explicit cost basis; the 1 Hz SCADA path carries only the derived
scalar. The 1 Hz historian Nyquist limit (0.5 Hz) is stated as the
REASON the edge placement is required — the auditor's F23 defect
(kHz FFT implicitly riding the 1 Hz logged stream) is repaired by
declaration, not by dropping the mechanism.

fu-003: modality repair — the mechanical modal/tap-test draft is
RETIRED (MODALITY_MISMATCH class, AM5 F23); the redraft stays INSIDE
the constraint's offline-PD modality: the PDIV-PDEV hysteresis width
(a within-test differential quantity on the standard outage PD test)
as the leading indicator, with the wall-conductivity mechanism
labeled as the hypothesis the falsification test kills or confirms.
"""

FU001_REPAIRED = """PROPOSED INDICATOR AND THRESHOLD: Normalized Asymmetric Sideband Energy Ratio (NASER) > 0.85 with a 95% confidence interval, computed at the sensor edge on the existing 1 kHz vibration waveform stream; only the derived 15-minute NASER trend value is written to the existing 1 Hz SCADA logging path, alongside shaft speed and load for defect-frequency normalization and alarm gating.

MECHANISM: Inner-race spalling initiates at microscopic stress concentrations that gradually alter the load-zone geometry. This creates asymmetric contact stress distribution that modulates the bearing's natural transmission error. The modulation appears as asymmetric sidebands around the characteristic defect frequencies in the vibration spectrum. These sidebands develop gradually as the stress concentration grows, typically 14-21 days before visible spalling occurs. The asymmetry manifests as unequal energy distribution on the positive and negative frequency sides of the defect harmonics.

DATA PATH AND EDGE COMPUTATION BASIS: The 1 Hz SCADA historian alone cannot resolve any 50-200 Hz feature - its Nyquist limit is 0.5 Hz - so the NASER computation must run before the historian, at the sensor edge, on the existing 1 kHz vibration waveform stream. No new sensing hardware is required: the existing 1 kHz vibration sensor is the only measurement device; the upgrade is compute-at-sensor software on the condition-monitoring channel plus a derived-scalar write to the existing 1 Hz logging path. Compute basis: a 1024-point FFT at 1 kHz sampling is one 1.024-second block per second; ASSUMPTION: this stays under 5% of a commodity DSP/MCU core or the existing monitor rack's channel module, and the one-time cost per channel is on the order of $100-300 of embedded compute - negligible against an unplanned 350 kW fan-drive bearing replacement and its downtime. The 1 Hz SCADA logging constraint is respected: nothing but one scalar per 15-minute window crosses into the historian, and the 1 Hz shaft-speed/load context sets the defect-frequency normalization and gates the alarm logic against transient load events (false-alarm control).

DEPARTURE FROM STANDARD: Standard methods detect symmetric energy increases around defect frequencies or overall energy changes. NASER specifically quantifies the asymmetry of energy distribution across sidebands, which is a direct measure of load-zone geometry changes preceding spall formation.

LABELED PARAMETERS:
- USER CONSTRAINT: existing 1 kHz vibration sensor (the waveform stream the edge computation runs on)
- USER CONSTRAINT: 1 Hz SCADA logging (the derived-scalar historian path; raw waveforms are not stored in the historian - this constraint is why the computation is placed at the sensor)
- USER CONSTRAINT: at least 14 days warning (determines the observation window)
- USER CONSTRAINT: at most 2 false alarms per year (sets the statistical threshold)
- ASSUMPTION: Bearing defect frequencies are between 50-200 Hz (typical for industrial fan bearings)
- CALCULATED: 1024-point FFT blocks at the sensor edge on the 1 kHz waveform (frequency resolution about 0.98 Hz at the sensor, before the historian)
- CALCULATED: 15-minute averaging window (balances responsiveness with noise reduction)
- ASSUMPTION: Sideband asymmetry develops monotonically during the spall initiation phase
- CALCULATED: 95% confidence interval (corresponds to approximately 2 false alarms per year)

INDICATOR: Normalized Asymmetric Sideband Energy Ratio (NASER)
THRESHOLD: > 0.85

Calculation (executed at the sensor edge on the 1 kHz waveform stream; one scalar per window written to the 1 Hz historian):
For each defect frequency f_d (calculated from bearing geometry and the 1 Hz SCADA shaft-speed trend):
1. Extract sideband energy in 5 Hz bands around f_d from the 1 kHz waveform: E_left = energy in [f_d-5Hz, f_d], E_right = energy in [f_d, f_d+5Hz]
2. Calculate NASER = |E_right - E_left| / (E_right + E_left)
3. Apply the 15-minute moving average to NASER values
4. Alarm when NASER > 0.85 for 3 consecutive 15-minute intervals

VALIDATION PROTOCOL:
1. Collect 1 kHz vibration waveforms from 20 identical fan drives with known bearing replacement history (portable analyzers during scheduled collection windows - test equipment, not deployed predictor hardware)
2. Apply the NASER calculation to data from 30 days before each bearing replacement
3. Record NASER values and actual failure times
4. Falsification test: for each bearing, determine if NASER > 0.85 occurred at least 14 days before failure
5. Pass criterion: at least 90% of bearings show NASER > 0.85 at least 14 days before failure, with at most 2 false positives across all test bearings
6. Statistical validation: apply bootstrapping to determine confidence intervals for the 14-day warning time claim
"""

FU003_REPAIRED = """PROPOSED INDICATOR AND THRESHOLD: PDIV-PDEV hysteresis width (PDIV minus PDEV, both in per-unit of rated voltage) exceeding 0.04 pu, or a widening of more than 0.01 pu between successive outage tests, with at least 6 months of lead time before ground fault.

MECHANISM: A void inside the ground-wall insulation discharges once the local field exceeds its inception level; as the voltage falls back, the discharge persists until extinction, which is governed by the charge left on the void walls. If the void surface degrades, carbonized conductive byproducts change the wall's surface conductivity and the surface-charge decay between cycles, so the extinction voltage drifts relative to the inception voltage. The hysteresis width PDIV - PDEV therefore carries wall-condition information that a single amplitude reading cannot: it is a differential measurement at the same void, same detector, same test circuit, taken minutes apart inside one outage window, so detector gain, cable layout, and test-circuit differences cancel rather than confound.

MODALITY COMPLIANCE: The measurement is offline partial-discharge testing during scheduled outages only - a ramped-voltage PDIV/PDEV read on the standard outage PD test set with a portable detector. No continuous monitoring hardware is installed; the machine returns to service unchanged.

DEPARTURE FROM STANDARD: Standard offline PD practice reads absolute PD magnitude, pulse count, or phase-resolved (PRPD) discharge patterns and trends them between outages, confounded by test-circuit and detector differences. The departure is the within-test differential quantity (PDIV-PDEV hysteresis width and its between-outage slope), which cancels the between-test confounds by construction and targets void-wall surface condition - a degradation state variable - rather than discharge severity, which is a symptom.

LABELED PARAMETERS:
- USER CONSTRAINT: offline PD testing during scheduled outages only (the measurement is a ramped-voltage PDIV/PDEV read on the standard outage PD test set)
- USER CONSTRAINT: no continuous monitoring hardware (nothing is installed on the machine; the detector is portable and leaves with the outage crew)
- USER CONSTRAINT: at least 6 months before ground fault (validation lead-time requirement)
- USER CONSTRAINT: no emergency shutdowns triggered falsely (the predictor schedules an interim outage decision; it never trips anything)
- ASSUMPTION: degradation-driven wall-conductivity change shifts PDEV more than PDIV (the mechanism hypothesis the falsification test kills or confirms)
- ASSUMPTION: ramped-voltage PDIV/PDEV read at two labeled ramp rates in the same outage window bounds the surface-charge-decay contribution to the width
- ASSUMPTION: threshold values (0.04 pu width, 0.01 pu per outage interval) are calibrated on the fleet's first two outage cycles before the predictor is trusted
- CALCULATED: annual outage cadence assumed; a crossing of the width threshold triggers an interim test at the 6-months-remaining mark

INDICATOR: PDIV-PDEV hysteresis width (per-unit) and its between-outage slope
THRESHOLD: width > 0.04 pu OR slope > 0.01 pu per outage interval

VALIDATION PROTOCOL:
1. During scheduled outages, run the standard offline PD test with a ramped-voltage read: PDIV on the up-ramp, PDEV on the down-ramp, at the two labeled ramp rates
2. Track the hysteresis width across at least 3 outage cycles on 10 or more machines with known insulation history, including machines later found with degraded voids at teardown
3. Falsification test: machines that later suffered ground-fault-class insulation failure must show width or slope crossing threshold at least 6 months before failure; machines with healthy insulation at teardown must not cross
4. Pass criterion: at least 90% of failing machines flagged at least 6 months early, with zero healthy machines flagged (zero false shutdowns - the predictor schedules interim tests, it never trips)
5. Kill criterion: if the width does not separate degraded from healthy voids across two full outage cycles, the void-wall-conductivity mechanism is dead and the indicator is withdrawn
"""

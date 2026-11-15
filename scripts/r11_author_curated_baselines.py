#!/usr/bin/env python3
"""D2 (AM8 direction 2): author 18 curated STANDARD_REFERENCE baselines
for the fresh problems.

A STANDARD_REFERENCE baseline is the CONVENTIONAL, textbook/industry-
standard engineering answer to the problem — what a competent
practitioner would propose today. It is the comparator the Art.
LXXXVI gate scores A1 against (the auditor's n=10 judgments scored
the delivery vs exactly this class of baseline). It is NOT a novel
answer — that is the point: novelty delta is measured against the
standard practice, so the baseline must BE the standard practice.

These are builder-authored (typed as such, STANDARD_REFERENCE,
builder-attributed, for auditor adoption per F21) — the auditor
re-judges every pair and may revise any baseline.

Method discipline (Art. XVIII/XXV): each baseline states the standard
practice, its typical quantitative parameters from engineering
handbooks/standards where they are common knowledge in the field, a
falsification test, and labels numbers as USER CONSTRAINT (from the
problem) vs STANDARD PRACTICE (field-typical) vs ASSUMPTION. No
fabricated citations. Where a parameter is field-typical but varies,
it is labeled STANDARD PRACTICE with the range.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

B = {}  # problem_id -> baseline_answer

B["bench-p01-pemfc-dehydration"] = """### Standard-Practice Baseline: Cathode Gas Humidification Increase and Internal Membrane Hydration Monitoring

The conventional response to membrane dehydration at high current density is to increase reactant gas humidification on the cathode side (bubbler or membrane humidifier sizing up), backed by a stack health monitor.

1. **Intervention.** Increase cathode inlet gas relative humidity toward saturation (typical stacks run 80-100% RH at rated current) using the existing humidifier, and derate stack current locally when the measured high-frequency resistance (HFR) indicates the membrane is drying. HFR is the standard online membrane-hydration proxy measured by the DC/DC converter during operation.
2. **Parameters.** Current density 1.5 A/cm2 (USER CONSTRAINT). Stack temperature 80 C (USER CONSTRAINT). Cathode RH 90-100% at inlet (STANDARD PRACTICE for liquid-cooled PEMFC at this current density). HFR alarm threshold per OEM stack map (STANDARD PRACTICE; site-specific).
3. **Expected effect.** Higher inlet RH offsets electro-osmotic drag at 1.5 A/cm2, keeping membrane water content in the conductive regime and limiting hot-spot growth; HFR-triggered derating protects the worst-performing cell.
4. **Constraint respect.** The parasitic load of additional humidification (humidifier pumping/heating) is the direct cost of this approach; meeting the 10 percent parasitic ceiling requires the humidifier to already have spare capacity. If it does not, the standard practice conflicts with the constraint and must be derated — this is the known weakness of the conventional answer.
5. **Falsification test.** Run the stack at 1.5 A/cm2, 80 C, with cathode RH raised to the maximum the existing humidifier supports, and log HFR and cell voltages for 500 h. If HFR rises above the OEM dryness band or any cell voltage drops more than 30 mV below stack average for more than 60 s, the humidification increase is insufficient and the practice fails the duty. Parasitic load is measured directly; if it exceeds 10 percent, the practice fails the constraint.
"""

B["bench-p03-phe-biofouling"] = """### Standard-Practice Baseline: Online Chlorination with Periodic Chemical Cleaning of Plate Packs

The conventional approach to biofilm and scale in district-cooling plate heat exchangers is continuous low-level chlorination of the loop combined with scheduled chemical clean-in-place (CIP) between mechanical cleanings.

1. **Intervention.** Dose sodium hypochlorite continuously to hold residual chlorine in the loop, supplemented by quarterly chemical CIP (citric acid for scale, alkaline cleaner for biofilm) through the plate pack without opening it.
2. **Parameters.** Residual chlorine 0.2-0.5 ppm (USER CONSTRAINT ceiling 0.5 ppm; STANDARD PRACTICE range 0.2-0.5 ppm free residual in cooling loops). CIP interval 3-6 months (STANDARD PRACTICE). Target overall heat transfer coefficient 2500 W/m2K at 12 months (USER CONSTRAINT).
3. **Expected effect.** Continuous residual chlorine suppresses biofilm growth; acid wash removes scale deposits. Together they slow the U-value decay between mechanical cleanings.
4. **Constraint respect.** The approach operates within the 0.5 ppm chlorination ceiling by design. The risk is that at 0.5 ppm the biofilm suppression is incomplete at 25 C summer conditions, so the 12-month U-value target may require CIP more often than the constraint's 12-month mechanical-cleaning interval implies — the standard practice typically trades cleaning frequency against disinfectant level.
5. **Falsification test.** Instrument one plate pack with inlet/outlet temperature and flow (U-value computed weekly) under continuous 0.4-0.5 ppm residual with quarterly CIP for 12 months. If measured U falls below 2500 W/m2K at any point before 12 months, the standard practice fails the stated duty under the chlorination ceiling.
"""

B["bench-p04-pump-cavitation"] = """### Standard-Practice Baseline: Inducer Addition or NPSH Margin Recovery via Suction Piping Improvements

The textbook response to impeller cavitation at off-design flow is to recover NPSH margin: enlarge suction piping, reduce suction-line losses (fittings, valves), lower the pump elevation, or fit an inducer ahead of the first-stage impeller.

1. **Intervention.** Fit a helical inducer upstream of the impeller (the standard anti-cavitation device for centrifugal pumps operating at low NPSH), combined with a suction strainer/valve audit to remove avoidable inlet losses.
2. **Parameters.** Operating flow 85% of best-efficiency flow (USER CONSTRAINT). NPSH margin above 1.5 m (USER CONSTRAINT; Hydraulic Institute guidance recommends margin over NPSH3, typically 1.3-2.5 m depending on suction energy). Inducer head rise 2-5 m at rated flow (STANDARD PRACTICE range for inline inducers). Vane life above 5 years (USER CONSTRAINT).
3. **Expected effect.** The inducer raises the pressure at the impeller eye above the vapor pressure at the reduced flow, suppressing bubble formation at the vane leading edges; removing inlet losses adds directly to NPSHa.
4. **Constraint respect.** An inducer narrows the flow range in which the pump operates quietly and adds a rotating element with its own life limit; at 85% of BEP flow the inducer itself can enter its own low-flow instability, which is the known limitation of the standard device.
5. **Falsification test.** Instrument the pump with inlet pressure, flow, and vibration (cavitation-index band) and run at 85% BEP flow for 1000 h with the inducer fitted. If measured NPSH margin stays above 1.5 m but the cavitation-band vibration energy remains above the baseline clean-water reference, or if vane erosion measureable by profile gauging exceeds 0.1 mm at 1000 h (extrapolating past 5-year life), the standard practice fails the duty.
"""

B["bench-p05-bridge-bearing-aging"] = """### Standard-Practice Baseline: High-Load Multi-Rotational Bearing with Skewed Polyisoprene Layers

The conventional long-life answer for elastomeric bearing creep and ozone cracking under 75-year service is a larger, higher-quality laminated pad: filled polychloroprene (neoprene) or polyisoprene with higher durometer layers, more shims, and ozone-resistant compounds, sized with a creep allowance.

1. **Intervention.** Replace the standard pad with an oversized steel-laminated elastomeric bearing using ozone-resistant compound (e.g., 60-durometer neoprene meeting ASTM D4014 or EN 1337-3), with layer thickness and shim count chosen so the 75-year creep + ozone drift stays inside the deflection budget by design allowance.
2. **Parameters.** Vertical deflection drift below 10% of design over 75 years (USER CONSTRAINT). Design per EN 1337-3 / AASHTO LSM method (STANDARD PRACTICE). Creep allowance in design typically 25-50% of initial deflection factored into the layer count (STANDARD PRACTICE). Ozone-resistant compound rating (STANDARD PRACTICE per EN 1337-3 material class).
3. **Expected effect.** A larger bearing lowers sustained compressive strain per layer (the driver of creep), and ozone-resistant compound plus full edge cover retards surface cracking; together the drift over 75 years stays within the design allowance.
4. **Constraint respect.** The bearing is sized once at installation (no replacement access — USER CONSTRAINT); the standard method handles this by design margin, and the residual risk is compounding of creep and ozone mechanisms over 75 years, which lab aging only approximately predicts.
5. **Falsification test.** Age production-bearing coupons in accelerated tests — compression set per ASTM D395 (e.g., 70 h and 1000 h at 100 C equivalent) and ozone cracking per ASTM D1149 (50 ppm ozone, 20% strain, 72 h) — then extrapolate drift by the Arrhenius/ WLF method. If the extrapolated 75-year vertical drift exceeds 10% of design deflection, or any visible ozone crack appears in the D1149 exposure, the standard compound/geometry fails the duty and the practice is falsified for this application.
"""

B["bench-p06-water-biofilm"] = """### Standard-Practice Baseline: Periodic Unidirectional Flushing of Dead-End Mains

The conventional control for biofilm regrowth and nitrification in chloraminated dead-end mains is a periodic flushing program (unidirectional flushing, UDF) with residual monitoring, without increasing the disinfectant dose at the plant.

1. **Intervention.** Establish a seasonal unidirectional flushing program on identified dead-end mains, with hydrant flushing velocities high enough to shear biofilm (typically 3 ft/s or greater), plus routine residual/nitrite monitoring at dead-end sample points to schedule flushing before nitrification episodes.
2. **Parameters.** Total chlorine residual above 1.0 mg/L at the farthest customer (USER CONSTRAINT). Water temperature 25 C summer demand (USER CONSTRAINT). Flushing velocity 0.9-1.5 m/s (STANDARD PRACTICE for UDF). Flushing interval weekly-to-monthly per main depending on monitoring (STANDARD PRACTICE).
3. **Expected effect.** Flushing removes accumulated biofilm and aged water from dead ends, restoring residual carry-through; monitoring schedules flushing before nitrite exceedance.
4. **Constraint respect.** The practice does not boost disinfectant dose (USER CONSTRAINT respected). Its known weakness at 25 C: nitrifier regrowth between flushes can outpace a weekly schedule, and flushing water use may be significant during summer demand restrictions.
5. **Falsification test.** Run one summer season with UDF at the monitoring-triggered interval on instrumented dead-end mains (continuous residual loggers at the farthest customer, weekly nitrite grab samples). If any nitrite sample exceeds the regulatory limit, or residual at the farthest customer falls below 1.0 mg/L between flushes for more than 24 h, the standard practice fails the stated duty at summer conditions.
"""

B["bench-p07-cgm-biofouling"] = """### Standard-Practice Baseline: Anti-Fouling Coating on the Working Electrode plus Periodic In-Session Calibration

The conventional mitigation for CGM electrode biofouling is a biocompatible anti-fouling coating (e.g., hydrogel with anti-fouling chemistry such as polyethylene glycol or zwitterionic layers) on the sensor, with the device's built-in drift correction and, historically, periodic calibration; current-generation devices push calibration-free operation by tighter manufacturing control.

1. **Intervention.** Coat the working electrode with an established anti-fouling hydrogel formulation and rely on the device's factory calibration plus in-wear drift compensation algorithms.
2. **Parameters.** MARD below 10% over 14-day wear (USER CONSTRAINT). No daily recalibration (USER CONSTRAINT). Anti-fouling hydrogel per current-generation sensor designs (STANDARD PRACTICE, e.g., PEG-based or similar chemistries in marketed 10-14 day sensors).
3. **Expected effect.** The anti-fouling layer slows protein adsorption and tissue encapsulation, holding signal attenuation inside the algorithm's compensation range for the wear period.
4. **Constraint respect.** The standard coating answers biofouling only partially: the tissue capsule that forms after roughly a week is not prevented by surface chemistry alone, which is exactly why current-generation sensors still degrade toward the end of 14-day wear. The practice relies on the sensor's native calibration schedule — no added recalibration.
5. **Falsification test.** Wear-test the coated sensor on the standard clinical protocol (e.g., paired readings vs laboratory analyzer across 14 days, n per protocol). If measured MARD exceeds 10% on any day of wear, or day-14 MARD exceeds day-1 MARD by more than 3 percentage points (indicating uncompensated fouling drift), the standard coating-plus-compensation practice fails the 14-day duty.
"""

B["bench-p08-mems-stiction"] = """### Standard-Practice Baseline: Mechanical Overrange Stops and Anti-Stiction Coatings on Comb Fingers

The conventional MEMS defense against shock-induced stiction is structural: overrange stop bumps that limit finger deflection below contact, plus self-assembled monolayer (e.g., FDTS-class) anti-stiction coatings where contact remains possible, and a Shockley-bounds design review of proof-mass travel.

1. **Intervention.** Add mechanical overrange stops limiting proof-mass displacement so comb fingers cannot touch under the rated shock, and apply a fluorosilane anti-stiction coating as the second line of defense.
2. **Parameters.** 10,000 g shock all axes (USER CONSTRAINT). Permanent zero-g offset above 50 mg (USER CONSTRAINT limit). Stop gap sized so max finger deflection under shock stays below contact (STANDARD PRACTICE: stops sized by FEA at rated shock with margin). FDTS-class monolayer coating (STANDARD PRACTICE for released MEMS).
3. **Expected effect.** Stops carry the shock load through the substrate instead of the fingers; if contact occurs despite stops, the low-surface-energy coating prevents capillary/van der Waals latching.
4. **Constraint respect.** Stops add parasitic capacitance and reduce usable range; the coating degrades with repeated contact and humidity — the known residual risk is a shock event during coating wear-out. The practice adds no active circuitry and survives all axes by symmetric stop placement.
5. **Falsification test. Subject production devices to the rated 10,000 g shock (all axes, per MIL-STD-883 Method 2002 or equivalent, n at least 10 per axis) with pre/post zero-g offset measurement. If any device latches (stiction) or shows permanent offset above 50 mg, the stop + coating practice fails the duty. Humidity-aged devices (85 C/85% RH, 500 h) repeat the shock; latch or offset failure indicates the coating wore below effectiveness and the practice is falsified for the rated life.
"""

B["bench-p10-pv-pid"] = """### Standard-Practice Baseline: Charge-Neutralization (Anti-PID) Nighttime Device

The industry-standard mitigation for potential-induced degradation in high-voltage strings is the anti-PID box: a nighttime power supply that applies a charge-neutralizing voltage between the array and ground during darkness, reversing sodium drift.

1. **Intervention.** Install an anti-PID device per string: at night it drives the negative pole (or array frame) to a potential that cancels the daytime stack bias, halting sodium-ion migration and partially reversing PID.
2. **Parameters.** System bias 1000 V (USER CONSTRAINT). Annual power loss below 0.5% over 25 years (USER CONSTRAINT). Nighttime offset voltage typically equal-and-opposite to string bias (STANDARD PRACTICE per commercial anti-PID boxes). No encapsulant replacement (USER CONSTRAINT respected — device is external).
3. **Expected effect.** Nightly neutralization removes the sustained DC field that drives Na+ from the cover glass through the encapsulant into the cell shunt paths, keeping shunt resistance high; existing degradation partially recovers each night.
4. **Constraint respect.** The device adds a small nighttime parasitic draw and per-string hardware; PID-s susceptibility also depends on the module's encapsulant and cell technology (the mechanism is not fully eliminated — field data show mitigation rather than full immunity). The 0.5%/year loss budget must still be met by the module technology itself.
5. **Falsification test.** Side-by-side field or chamber test per IEC 62804 (damp-heat with system-voltage bias, e.g., 85 C/85% RH at 1000 V for 96 h or extended): measure power and shunt resistance of modules with and without the anti-PID device. If the protected modules lose more than the equivalent of 0.5%/year projected power (by the test's acceleration factor), or shunt resistance degrades beyond the IEC 62804 pass criterion, the standard device fails the 25-year duty at 1000 V.
"""

B["bench-p11-spindle-thermal-drift"] = """### Standard-Practice Baseline: External Cooling Circuit with Thermal-Error Compensation Table

The conventional control of spindle thermal elongation is a chilled-oil (or chilled-water) cooling circuit through the spindle housing driven by the OEM's thermal map, plus a CNC thermal-error compensation table that offsets tool-center-point drift as a function of measured temperatures.

1. **Intervention.** Fit/size the spindle's external liquid cooling unit to hold housing temperature within a narrow band, and apply the machine's built-in thermal compensation model (temperature-indexed axis offsets) calibrated by the OEM warmup characterization.
2. **Parameters.** Tool-center-point displacement below 10 um across the 20-minute warmup (USER CONSTRAINT). No added warmup idle cycles (USER CONSTRAINT). Cooling unit setpoint per OEM spec (STANDARD PRACTICE; typically holds housing within +/-0.5-1 C of setpoint). Compensation table from OEM thermal characterization (STANDARD PRACTICE).
3. **Expected effect.** The cooling circuit removes bearing heat at the housing, slowing shaft elongation; the compensation table subtracts the characterized drift from axis positions, holding net TCP error inside the band.
4. **Constraint respect.** The compensation table is only as good as its calibration — it compensates the characterized warmup shape, and day-to-day ambient or preload variation changes the shape (the residual the standard approach leaves). No idle cycles are added.
5. **Falsification test.** Cold-start the machine and run the production duty cycle for 20 minutes with a master-bar or laser interferometer measuring TCP displacement continuously (cooling on, compensation active). If measured TCP displacement exceeds 10 um at any point in the transient across 5 cold starts, the standard cooling + compensation practice fails the duty.
"""

B["bench-p12-mbr-fouling"] = """### Standard-Practice Baseline: Relaxation/Intermittent Permeation with Automated Intensive Chemical Cleaning

The conventional MBR fouling control is the intermittent filtration cycle (filtration on/off relaxation, optionally with backwash) plus scheduled maintenance cleaning (chemically enhanced backwash, e.g., sodium hypochlorite and citric acid) and recovery cleaning in place.

1. **Intervention.** Operate the membrane in a filter/relax cycle (e.g., 9-10 min filtration, 1-2 min relaxation, with backwash per OEM), with automated maintenance chemical cleaning at fixed intervals (e.g., weekly chemically enhanced backwash) and recovery CIP when threshold transmembrane pressure is reached.
2. **Parameters.** Net flux above 18 LMH (USER CONSTRAINT). MLSS 8 g/L (USER CONSTRAINT). Chemical cleaning intervals above 6 months (USER CONSTRAINT — this is the binding constraint for the standard practice). Typical filtration cycle 10-12 min with 1-2 min relaxation (STANDARD PRACTICE). Maintenance chemically enhanced backwash interval daily-to-weekly; recovery CIP every 3-6 months typical (STANDARD PRACTICE).
3. **Expected effect.** Relaxation and backwash limit cake consolidation; maintenance cleaning controls organic/EPS fouling; recovery CIP restores permeability. The cycle holds flux between cleaning events.
4. **Constraint respect.** The standard practice's chemical cadence (maintenance weekly, recovery every few months) CONFLICTS with the stated 6-month chemical cleaning interval constraint — holding 18 LMH at 8 g/L MLSS with no chemical clean for 6 months is beyond what the conventional cycle achieves without frequent maintenance chemistry. The standard answer therefore leans on interpreting the constraint as excluding only recovery CIP; if it excludes maintenance cleaning too, the standard practice fails the constraint outright.
5. **Falsification test.** Pilot or side-stream the membrane at 18 LMH net, 8 g/L MLSS, with relaxation per OEM and NO chemical clean of any kind for 6 months, logging TMP. If TMP reaches the OEM maximum (or flux must fall below 18 LMH to hold TMP) before 6 months, the standard relaxation-only practice fails the stated constraint, falsifying the conventional answer for this duty.
"""

B["eval-sofc-redox"] = """### Standard-Practice Baseline: Redox-Tolerant Anode via Reduced Nickel Content and Protective Start-Stop Purge Procedure

The conventional mitigations for Ni-YSZ anode redox damage are (a) anode composition and microstructure choices that tolerate partial re-oxidation (lower Ni volume fraction, finer porosity control, sacrificial porosity) and (b) a disciplined start/stop procedure that keeps the anode reducing (protective gas purge with inert/hydrogen mixture) so the stack never sees uncontrolled air ingress.

1. **Intervention.** Use a redox-tolerant anode-supported cell design (Ni content reduced toward the percolation minimum with stabilized YSZ skeleton, graded porosity) and enforce a stack-level start/stop procedure: on shutdown, purge the anode with inert gas plus a small hydrogen fraction until the cell is below the temperature where nickel re-oxidizes appreciably (below roughly 300-400 C).
2. **Parameters.** 200 start-stop cycles over 5 years (USER CONSTRAINT). 750 C operating temperature (USER CONSTRAINT). Power density above 0.35 W/cm2 at 0.7 V (USER CONSTRAINT). Cell package thickness within 2 mm (USER CONSTRAINT). Ni content in the anode support typically around 40-50 vol% (reduced from the ~50-60% of power-optimized anodes; STANDARD PRACTICE range for redox-tolerant designs). Purge duration per stop sized to displace anode gas volume several times (STANDARD PRACTICE).
3. **Expected effect.** The purge prevents uncontrolled re-oxidation during stops (the main damage route); the reduced-Ni anode tolerates mild incidental redox without the volume expansion that cracks the electrolyte.
4. **Constraint respect.** Reducing Ni lowers electronic conductivity and electrochemical activity, costing power density — the 0.35 W/cm2 at 0.7 V target becomes harder to meet within the 2 mm package; the purge procedure lengthens every start/stop, which is acceptable but adds operational complexity. The standard design does not remove the mechanism: 200 controlled cycles still accumulate some redox strain.
5. **Falsification test.** Subject production cells to 200 laboratory redox cycles (per the OEM cycle: full reduction, controlled re-oxidation at the purge-protected level, re-reduction) at temperature, measuring power density at 0.7 V every 25 cycles. If power density falls below 0.35 W/cm2 at any point, or post-cycle microscopy shows electrolyte cracking or delamination beyond the acceptance limit, the standard anode + purge practice fails the duty. If the purge fails to prevent a single uncontrolled oxidation event in the 200-cycle log, the procedure itself is falsified.
"""

B["eval-new03-insulin-pump-occlusion"] = """### Standard-Practice Baseline: Pressure-Threshold Occlusion Detection with Adaptive Alarm Window

The conventional pump answer is a force/pressure sensor in the infusion line (or motor-current proxy) with a fixed-or-adaptive threshold alarm: the standard occlusion detection shipped in marketed pumps, tuned per manufacturer.

1. **Intervention.** Keep the existing pressure-threshold occlusion detector and improve its tuning: an adaptive threshold that tightens during low-basal periods (where slow occlusions are hardest to see) and relaxes during boluses (where nuisance alarms come from), plus an alarm-delay window sized to the delivery mode.
2. **Parameters.** Complete occlusion detected within 15 minutes (USER CONSTRAINT — current-generation pumps typically meet this at bolus rates; slow basal complete occlusion commonly takes longer, which is the practice's known weakness). Partial occlusion (deficit above 20%) within 2 hours (USER CONSTRAINT — fixed-threshold pressure detection does NOT reliably detect partial occlusions; the standard practice relies on secondary signals like cumulative volume error). Nuisance alarms at most 1 per 14 days (USER CONSTRAINT). Sensor: existing inline pressure/force sensor (STANDARD PRACTICE).
3. **Expected effect.** The adaptive threshold catches complete occlusions faster at basal rates while suppressing bolus-transient nuisance alarms; partial occlusions surface only through the slow volume-error accumulation path.
4. **Constraint respect.** The form factor is unchanged (USER CONSTRAINT respected). The practice's structural gap: pressure-based detection fundamentally struggles with partial occlusions — the 2-hour partial-occlusion requirement is at the edge of or beyond what threshold tuning achieves, and the 15-minute complete-occlusion requirement at low basal rates is likewise marginal.
5. **Falsification test.** Bench-test the tuned detector across the delivery matrix (basal 0.5-2 U/h, bolus 5-10 U) with induced complete and partial (20-40% deficit) occlusions: n at least 30 events per class. If any complete occlusion is detected later than 15 minutes, any partial occlusion later than 2 hours, or nuisance alarms exceed 1 per 14 days in the 200-event nuisance run, the standard pressure-threshold practice fails the stated duty.
"""

B["eval-new06-bearing-vibration-predictor"] = """### Standard-Practice Baseline: RMS Vibration Velocity Band Alarm with ISO 10816 Limits

The conventional predictor for rolling-element bearing degradation is the overall RMS vibration velocity measured on the existing 1 kHz-band sensor, alarmed against ISO 10816/20816 zone limits (alarm at zone C boundary), with the 1 Hz SCADA trend watched manually.

1. **Indicator.** Overall broadband RMS vibration velocity (mm/s RMS, 10-1000 Hz band) on the existing sensor.
2. **Threshold.** Alarm when RMS velocity exceeds the ISO 20816 zone-C boundary for the machine class (typically 4.5 mm/s RMS for large fans, class II/III machinery — STANDARD PRACTICE value), with a second trip at zone D (typically 7.1 mm/s).
3. **Expected effect.** Spalling raises broadband energy once damage is macroscopic; the zone alarm catches it before catastrophic failure.
4. **Constraint respect.** Uses only the existing 1 kHz sensor and 1 Hz SCADA (USER CONSTRAINT respected). The known weakness: broadband RMS rises LATE in the degradation (weeks, not the required 14 days of lead before forced replacement in many cases — inner-race spalling can progress substantially inside a constant RMS band), and false alarms from baseline shifts (loose mounting, load changes) are common without diagnostic-band analysis.
5. **Falsification test.** Replay historical vibration archives for the fleet (or run an accelerated-life bearing test): for every documented inner-race failure, check the time from first RMS zone-C alarm to forced replacement. If the median lead time is below 14 days, or false alarms exceed 2 per year per fan in the healthy population, the standard RMS-zone predictor fails the stated duty.
"""

B["eval-new08-pipeline-leak-predictor"] = """### Standard-Practice Baseline: Night-Minimum Flow Balance (Mass Balance) Alarm

The conventional leak indicator on an instrumented transmission main is the district mass balance: compare pumped/ inlet flow against outlet (or tank-level-derived) flow over a rolling window, alarmed when the imbalance exceeds a threshold; the standard implementation uses the night-minimum-flow window where demand noise is lowest.

1. **Indicator.** Rolling inlet-minus-outlet flow imbalance, evaluated on the 5-minute SCADA historian (both transmitters already exist), with a nightly minimum-flow window for sensitivity.
2. **Threshold.** Alarm when the 24 h rolling imbalance exceeds 0.5% of nominal flow sustained for 24 h, and/or the night-minimum imbalance exceeds 0.5% for 3 consecutive nights (STANDARD PRACTICE: night-minimum analysis is the standard water-loss technique from IWA water-balance methodology).
3. **Expected effect.** A 0.5% continuous leak shows as a persistent imbalance once metering noise averages down over the window; night minimum suppresses demand noise.
4. **Constraint respect.** Uses only the existing pressure and flow transmitters at 5-minute intervals (USER CONSTRAINT respected). The known weaknesses: meter accuracy classes (typically +/-0.5-1% for magnetic flow meters on large mains) sit AT or ABOVE the 0.5% leak signal, so the balance can only detect the leak if metering error is stable and cancels between the two stations; the 48-hour detection window leaves little averaging time, and transients (valve operations, air pockets) raise false alarms toward the 1/month limit.
5. **Falsification test.** Inject calibrated leak flows (0.5% of nominal) into a hydraulic model calibrated on the actual main's SCADA (or field data with a controlled discharge): run the balance algorithm for 48 h. If detection latency exceeds 48 h, or the healthy-patient false-alarm rate exceeds 1 per month per 10 km in replayed normal-operation data, the standard mass-balance predictor fails the stated duty.
"""

B["eval-new09-hvac-filter-predictor"] = """### Standard-Practice Baseline: Pressure-Drop Threshold with Runtime-Hours Fallback Schedule

The conventional filter-management predictor is differential pressure across the filter bank (dP) logged by the BMS, alarmed at the manufacturer's final-pressure rating (typically 2-3x initial dP), with a runtime-hours schedule as the fallback when no dP sensor exists.

1. **Indicator.** Filter differential pressure (where available in the BMS points), with the fallback indicator fan-power-normalized by outdoor-air fraction and occupied schedule (a proxy trend), and a runtime-hours counter as the schedule baseline.
2. **Threshold.** Alarm at the manufacturer's final dP (typically 1.0-1.5 in. w.g. or about 250-375 Pa for MERV-13 pleated banks; STANDARD PRACTICE per filter OEM), or when the fan-power proxy exceeds its clean-filter baseline by the equivalent dP change; schedule fallback at fixed 90-day runtime.
3. **Expected effect.** dP rises monotonically with dust loading; alarming at final dP replaces filters at end of useful life and avoids both early replacement and overloading.
4. **Constraint respect.** Uses only BMS points already logged (USER CONSTRAINT respected: fan power, dP where available, OA flow, occupancy schedule). The known weaknesses: many AHUs have no dP sensor (the fallback proxy is weakly sensitive to loading at constant-flow operation), the 1-week change-of-state resolution is challenged by the slow drift and sensor noise, and cutting replacements 20% below the 90-day schedule requires the dP alarm to actually fire before the calendar date — on lightly loaded filters it will not.
5. **Falsification test.** Log one full filter lifecycle season across a sample of AHUs (dP or fan-power proxy plus actual filter condition at change-out): compare the algorithm's alarm date against the OEM final-dP date measured by a reference gauge. If the change-of-state (crossing the final-dP threshold) is resolved less than 1 week after the reference gauge shows it, or the algorithm's replacement recommendations do not cut replacements by 20% versus the 90-day schedule on lightly loaded units, the standard predictor fails the stated duty.
"""

B["eval-new10-solar-inverter-predictor"] = """### Standard-Practice Baseline: Heatsink-Temperature Trend and Performance-Ratio Deviation Alarm

The conventional inverter degradation predictor from exported telemetry is a two-signal monitor: (a) heatsink temperature normalized by ambient and load (thermal impedance proxy for IGBT aging and fan/thermal-path degradation) and (b) inverter efficiency / performance-ratio deviation from its own clean-weather baseline (proxy for capacitor degradation raising ripple losses), alarmed on slow trends.

1. **Indicator.** Rolling 7-day mean of (heatsink temperature minus ambient) divided by output power (thermal resistance proxy), plus the 7-day performance ratio (AC energy out / DC energy in) relative to the inverter's commissioning baseline.
2. **Threshold.** Alarm when the thermal-resistance proxy rises 20% above its commissioning baseline at comparable load bins (STANDARD PRACTICE trend rule), or when the 7-day performance ratio falls more than 2 percentage points below baseline for two consecutive weeks (STANDARD PRACTICE).
3. **Expected effect.** IGBT bond-wire lift and fan degradation raise thermal resistance at given load; DC-link capacitor aging lowers efficiency and raises ripple — both surface in the two slow trends weeks before a trip.
4. **Constraint respect.** Uses only exported telemetry (DC voltage/current, AC power, heatsink temperature, fault log) at 5-minute resolution (USER CONSTRAINT respected). The known weaknesses: the two-week lead requirement is tight for the slow performance-ratio drift (capacitor degradation can accelerate faster than the 7-day averaging resolves), and seasonal/soiling effects confound the performance-ratio trend unless carefully binned, pushing false alarms toward the 1/quarter limit.
5. **Falsification test.** Replay fleet telemetry for inverters with documented IGBT or capacitor failures (fault-log ground truth): for each, compute the time from first sustained alarm to the actual trip. If the median lead time is below 2 weeks, or the healthy fleet produces more than 1 false alarm per quarter per inverter in a year of replay, the standard two-trend predictor fails the stated duty.
"""

B["eval-new11-conveyor-belt-predictor"] = """### Standard-Practice Baseline: Drive-Motor Current Signature Trend with Belt-Scale Mass-Throughput Normalization

The conventional belt-condition monitor from existing sensors is a normalized drive-power trend: motor current (or computed power) divided by belt-scale throughput, tracked as a rolling baseline, with an alarm on sustained deviation.

1. **Indicator.** Rolling 24-hour mean of specific energy consumption: drive-motor current times voltage (single-speed drive) or computed power, divided by belt-scale mass throughput (kWh per tonne). The metric isolates belt drag from payload.
2. **Threshold.** Alarm when the 7-day rolling specific energy rises 10% above the same-load commissioning baseline (STANDARD PRACTICE trend alarm for belt drag from cover wear/idler drag), with a second-stage alarm at 15% sustained 3 days.
3. **Expected effect.** Cover wear and carcass fatigue raise running resistance and slip losses; the normalized energy trend isolates that rise from tonnage variation, flagging a degrading belt weeks before splice/tear failure.
4. **Constraint respect.** Uses only the existing belt-scale and drive-motor current sensors at 1-minute resolution (USER CONSTRAINT respected). The known weaknesses: idler bearing degradation is mixed into the same signal (cannot be separated without extra instrumentation), load-profile changes on ore-type shifts shift the baseline (false alarms), and the 3-week lead requirement is long relative to how fast splice failures can progress once visible in drag — the standard trend is a lagging indicator for tears specifically.
5. **Falsification test.** Replay one year of belt-scale + motor current archives for belts with documented splice failures or tears (maintenance records as ground truth): compute the specific-energy trend and alarm dates. If the median lead time from alarm to failure is below 3 weeks, or the healthy fleet alarms more than 2 times per year, the standard normalized-energy predictor fails the stated duty.
"""

B["eval-new12-axle-bearing-predictor"] = """### Standard-Practice Baseline: Wayside Acoustic Amplitude Trend Alarm (TADS-class Energy Monitor)

The conventional wayside indicator is the acoustic energy signature from the trackside microphone array (the TADS-class system: wayside acoustic detection of bearing defects), alarmed on defect-band amplitude and its per-axle trend across repeated passes, with hot-box-detector temperature as the backup.

1. **Indicator.** Peak defect-band acoustic amplitude (the bearing-defect frequency envelope extracted from the wayside array as each axle passes), tracked per axle-tag across passes, with wheel-impact-load data as a covariate to exclude wheel-flat false sources.
2. **Threshold.** Alarm when a single pass exceeds the fleet 99th-percentile defect-band amplitude (STANDARD PRACTICE for wayside acoustic monitors), or an axle's per-pass trend crosses 3 consecutive rising readings above its own 12-month baseline (STANDARD PRACTICE trend rule).
3. **Expected effect.** Raceway spalling raises periodic acoustic energy at the defect frequencies; repeated passes trend the growth, flagging the axle for inspection before heating develops.
4. **Constraint respect.** Uses only the existing wayside acoustic array and WILD data, no onboard hardware (USER CONSTRAINT respected). The known weaknesses: wayside acoustics is strongly affected by speed, load, and wheel condition (the WILD covariate only partially corrects); single-pass false-alarm rates are high, so the 3-consecutive-pass trend rule trades sensitivity for specificity — and that trade pushes detection later, threatening the 60-day lead requirement; the microphone array cannot see subsurface cracks before they emit.
5. **Falsification test.** Replay one year of wayside acoustic records for axle boxes with documented spalling failures (depot teardown ground truth), computing the alarm dates under the stated rules. If the median lead time from alarm to critical temperature rise is below 60 days, or the healthy fleet alarm rate exceeds the operator's actionable-inspection capacity (more than 2% of passes flagged), the standard acoustic-trend predictor fails the stated duty.
"""

# ---- write the typed records ----------------------------------------
probs = json.loads((REPO / "eval" / "problems.json").read_text())
probs = probs if isinstance(probs, list) else probs.get("problems", [])
dev12 = {p["problem_id"] for p in json.loads(
    (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}
fresh_ids = sorted(str(p.get("problem_id") or p.get("id")) for p in probs
                   if str(p.get("problem_id") or p.get("id")) not in dev12)

assert set(fresh_ids) == set(B), (sorted(set(fresh_ids) ^ set(B)))

import datetime
records = []
for pid in fresh_ids:
    rec = {
        "problem_id": pid,
        "baseline_type": "STANDARD_REFERENCE",
        "baseline_answer": B[pid].strip(),
        "authored_by": "builder (R11 R8 round, D2 of AM8 direction 2)",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "method_note": (
            "Curated standard-practice baseline: the conventional, "
            "field-standard engineering answer (textbook/OEM/industry "
            "practice), NOT a novel proposal — the comparator the "
            "Art. LXXXVI gate measures A1 novelty against. Numbers are "
            "labeled USER CONSTRAINT / STANDARD PRACTICE / ASSUMPTION "
            "in-text; no fabricated citations; field-typical ranges "
            "given where practice varies. Builder-attributed for "
            "auditor adoption or revision (F21 process)."),
    }
    out = REPO / "eval" / "baselines_curated" / f"{pid}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    records.append(pid)
    print("written:", out.name)

# index record
idx = {
    "record": "CURATED_BASELINES_FRESH18/1.0.0",
    "at": datetime.datetime.now(datetime.UTC).isoformat(),
    "baseline_type": "STANDARD_REFERENCE",
    "n": len(records),
    "problem_ids": records,
    "authored_by": "builder",
    "adoption_state": "PENDING_AUDITOR_ADOPTION (F21; auditor may revise "
                      "any baseline before re-judgment)",
    "method": ("each baseline is the standard practice for its problem "
               "class, with labeled parameter provenance and a "
               "falsification test; used as the B arm in the F26-fixed "
               "battery and the auditor's per-axis re-judgment"),
}
(REPO / "eval" / "baselines_curated" / "INDEX.json").write_text(
    json.dumps(idx, indent=1) + "\n", encoding="utf-8")
print(f"\nINDEX written — {len(records)} STANDARD_REFERENCE baselines")

"""R412 Phase 3 — attacker-calibration corpus, Quadrant 1: KNOWN_GOOD.

Authored from established physics/engineering knowledge, INDEPENDENTLY of
the attacker's behavior (Art. VIII). Ground truth is established BEFORE
the attacker sees any case: this file and its emitted JSON are committed
(sealed) before the measurement run.

Instrument semantics for KNOWN_GOOD: given THESE inputs — the candidate
record, the evidence pool, and the provided prior-art set — a CALIBRATED
attacker must NOT kill. Each ground-truth basis states why the physics
holds, why the claim is honestly bounded, and why the provided prior art
is related but non-colliding (the prior-art discrimination a calibrated
attacker must perform: related art is not collision).
"""

KG_CASES = [
    {
        "case_id": "CAL-KG-01",
        "domain_id": "data_center_thermal",
        "pain_class": "TRANSIENT_PEAK",
        "candidate": {
            "candidate_id": "CAL-KG-01",
            "technology_name": "PCM-Buffered Cold Plate for Training Burst Peak-Shaving",
            "problem": "AI training bursts create 2-6 minute thermal power spikes that force chillers and fans to be sized and run for peaks, inflating cooling energy 15-25% over the duty-cycle average",
            "causal_chain": [
                "Phase-change material layer integrated into cold-plate base",
                "training burst raises heat flux",
                "PCM absorbs heat as latent heat at its melting point",
                "cooling loop and fan speeds see a damped, delayed load",
                "peak cooling demand is shaved and average-speed operation dominates",
                "cooling energy for the burst window falls"
            ],
            "unexploited_phenomenon": "Latent-heat buffering of paraffin-class PCMs near 28-32 C: ~180-230 kJ/kg absorbed at near-constant temperature during melting (cal:kg01:r1)",
            "intervention": "Bond a 4-8 mm paraffin PCM layer (m.p. 29 C, 190 kJ/kg) between the cold-plate copper base and the flow channel, sized to absorb the 90th-percentile burst energy of one rack row for 3 minutes",
            "governing_variables": "PCM thickness (m), latent heat (kJ/kg), melting point (C), burst heat flux (W/cm2), loop setpoint (C)",
            "predicted_effect": "15-25% reduction in cooling electricity during burst windows and 8-12% reduction in daily cooling energy; loop transient overshoot reduced by >50%; NOT a steady-state capacity change (honestly bounded: buffering only)",
            "equations": [
                "Q_burst = integral(q''(t) - q''_steady) dt over burst window [kJ]",
                "m_PCM = Q_burst / (f * L) where L = 190 kJ/kg, f = melt fraction usable (0.7-0.9)"
            ],
            "boundary_conditions": "Effective only when PCM melting point sits between loop setpoint and peak silicon temperature; buffering duration is minutes (latent capacity), not steady state; requires burst duty cycle < 20% so PCM re-solidifies between bursts",
            "evidence_refs": ["cal:kg01:r1", "cal:kg01:r2"],
            "baseline": {
                "baseline_incumbent": "Direct cold-plate loop with reactive variable-speed fan/chiller modulation responding to burst load in real time",
                "baseline_metric": "Cooling energy per burst window 100% (reactive peak following)",
                "candidate_metric": "75-85% of baseline energy per burst window"
            },
            "killer_experiment": {
                "experiment": "Two identical 20 kW mock racks, one with PCM-buffered plates, one without; drive identical synthetic training-burst power traces (5-min bursts, 20% duty); log cooling electricity and silicon temps for 48 h",
                "kill_condition": "If PCM rack cooling energy per burst window is not at least 8% lower than control rack with silicon temps within 2 C of control, the buffering mechanism is dead",
                "cost_class": "BENCH"
            },
            "failure_modes": ["PCM re-solidification incomplete between high-duty bursts", "delamination/cycling fatigue of the bond layer", "thermal resistance added in steady state raising baseline temperature"],
            "commercial_path": {"buyer": "Hyperscale and colocation data center operators buying retrofit rack-level cooling efficiency"},
            "cross_domain_transition": "Building-materials thermal mass buffering -> data center rack cooling (latent-heat buffering applied to a new transient regime)"
        },
        "pool": [
            {"record_id": "cal:kg01:r1", "title": "Latent heat storage in paraffin-based phase change materials: measured enthalpies 180-230 kJ/kg and near-isothermal melting plateaus for building thermal mass applications"},
            {"record_id": "cal:kg01:r2", "title": "Transient thermal buffering of electronics heat sources: measured peak-shaving of temperature and heat-flux spikes with thin PCM layers under pulsed loads"},
            {"record_id": "cal:kg01:r3", "title": "Review of steady-state liquid cold plate design for server CPUs: single-phase pump loop optimization and fan speed control strategies"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg01:pa1", "perspective": "MECHANISM", "title": "PCM wallboards and ceiling panels for building peak-load shifting (different application: building HVAC, room-scale, hours-timescale)"},
                {"record_id": "cal:kg01:pa2", "perspective": "FORWARD", "title": "Single-phase cold-plate loop with reactive fan-speed modulation for data center racks (no PCM layer, no latent buffering)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: paraffin latent heat at 29 C is a measured, textbook quantity (~190 kJ/kg); the transient heat equation guarantees the damping. The claim is honestly bounded (minutes-scale buffering, 15-25% burst-window energy, no steady-state claim). The provided prior art is RELATED (building PCM wallboards; reactive cold plates) but teaches neither the same intervention (PCM-bonded cold plates) nor the same effect (rack burst peak-shaving) — a calibrated attacker must distinguish related art from collision. The killer experiment has a real kill condition."
        }
    },
    {
        "case_id": "CAL-KG-02",
        "domain_id": "industrial_sensing",
        "pain_class": "BLIND_SPOT",
        "candidate": {
            "candidate_id": "CAL-KG-02",
            "technology_name": "Fiber-Bragg Strain Grid for Tank Farm Settling Surveillance",
            "problem": "Large welded storage tank farms develop gradual foundation settling that goes undetected between 5-year inspection surveys; localized differential settlement stresses shell welds",
            "causal_chain": [
                "Fiber Bragg grating strain sensors bonded on tank shell at 2 m vertical pitch",
                "differential foundation settlement strains the shell wall",
                "grating pitch changes shift the Bragg wavelength",
                "wavelength shifts map to strain with 1-2 microstrain resolution",
                "settling is detected within days instead of years"
            ],
            "unexploited_phenomenon": "Bragg wavelength shift with strain (~1.2 pm/microstrain at 1550 nm) in glass fiber bonded to steel (cal:kg02:r1)",
            "intervention": "Permanently bond an FBG strain grid (8 rings x 8 azimuths) per tank on the lowest two shell courses, interrogated by one tunable-laser scanner shared across the farm",
            "governing_variables": "Grating pitch (nm), strain sensitivity (pm/microstrain), bonded transfer efficiency, thermal compensation accuracy",
            "predicted_effect": "Detection of differential settlement > 5 mm/m within 7 days of onset at 99% confidence; survey interval extended safely from 5 to 8 years pending sensor health",
            "equations": [
                "lambda_B = 2 n_eff Lambda; dlambda/depsilon = 1.2 pm/microstrain",
                "epsilon_settle = E_corr / L_span after thermal compensation from co-located reference gratings"
            ],
            "boundary_conditions": "Requires thermal compensation (uncompensated temperature cross-sensitivity is ~6-13 microstrain/C, larger than the settling signal); bonded transfer must survive tank coating; not a substitute for internal corrosion inspection",
            "evidence_refs": ["cal:kg02:r1", "cal:kg02:r2"],
            "baseline": {
                "baseline_incumbent": "Periodic 5-year out-of-service geometric surveys with plumb-line and level measurements",
                "baseline_metric": "Detection latency up to 5 years",
                "candidate_metric": "Detection latency < 7 days"
            },
            "killer_experiment": {
                "experiment": "Calibrate grid on a test tank, induce controlled differential settlement with hydraulic jacks under one quadrant in 2 mm steps to 10 mm, record wavelength shifts vs surveyed settlement",
                "kill_condition": "If induced settlement of 6 mm/m is not resolved above 3-sigma thermal noise within 7 days, the surveillance mechanism fails",
                "cost_class": "LAB"
            },
            "failure_modes": ["bond creep decoupling sensor from shell", "thermal compensation drift", "fiber breakage at nozzle penetrations"],
            "commercial_path": {"buyer": "Terminal operators and tank farm owners under API 653 inspection economics"},
            "cross_domain_transition": "Structural-health fiber sensing from bridges -> welded tank shells (same waveguide mechanism, new monitored structure)"
        },
        "pool": [
            {"record_id": "cal:kg02:r1", "title": "Fiber Bragg grating strain sensing: measured wavelength-strain sensitivity 1.2 pm/microstrain and field deployments on bridge girders"},
            {"record_id": "cal:kg02:r2", "title": "Temperature compensation of FBG strain measurements using co-located reference gratings: measured cross-sensitivity 6-13 microstrain/C and its cancellation"},
            {"record_id": "cal:kg02:r3", "title": "API 653 tank inspection intervals: basis, out-of-service survey practice, and settling limits for welded storage tanks"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg02:pa1", "perspective": "MECHANISM", "title": "FBG strain monitoring of bridge and dam structures (civil infrastructure, not tank shells, not settlement surveillance service)"},
                {"record_id": "cal:kg02:pa2", "perspective": "FORWARD", "title": "Inclinometer settlement monitoring arrays around tank foundations (ground-based, external to the shell, coarser resolution)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: the Bragg wavelength-strain relation is a measured waveguide constant; thermal cross-sensitivity is disclosed and compensated with reference gratings (a real, published technique). The claim (settlement detection within days) is bounded and conservative. The provided prior art covers FBG on bridges (different structure and service) and external inclinometers (different instrument) — no record teaches FBG bonded to tank shells for settling surveillance. The killer experiment has a decisive kill condition."
        }
    },
    {
        "case_id": "CAL-KG-03",
        "domain_id": "chemical_process",
        "pain_class": "ENERGY_CONVERSION_LOSS",
        "candidate": {
            "candidate_id": "CAL-KG-03",
            "technology_name": "Dividing-Wall Column Retrofit for Close-Boiling Solvent Split",
            "problem": "A specialty-chemical plant separates two close-boiling solvents (relative volatility 1.15) in a sequence of two conventional distillation columns, remixing intermediate composition between stages and losing 900 kW of reboiler duty to remixing",
            "causal_chain": [
                "Conventional two-column sequence remixes the middle-boiling component between columns",
                "dividing wall separates the prefractionation and main sections inside one shell",
                "vapor and liquid split to their composition-matched sides",
                "the remixing entropy penalty is eliminated",
                "reboiler duty falls for the same separation"
            ],
            "unexploited_phenomenon": "Thermodynamic coupling avoided by divided-wall distillation: 25-35% duty reduction for close-boiling ternary splits (cal:kg03:r1)",
            "intervention": "Replace the two-column train with one dividing-wall column with matched stages, reboiler, and condenser; keep product specs identical (99.2% purity)",
            "governing_variables": "Relative volatility, number of stages per side, vapor split ratio, liquid split ratio, reflux ratio",
            "predicted_effect": "27-32% reduction in reboiler duty for the same purity, 40% lower footprint, 3.5-year payback at 900 kW saved",
            "equations": [
                "Q_reboiler(min) = f(relative volatility, feed composition, splits) per Underwood-Gilliland with the dividing-wall side-draw removing the remixing term",
                "payback = capex / (900 kW x 8400 h x $0.07/kWh)"
            ],
            "boundary_conditions": "Valid for relative volatility 1.05-1.4 ternary or pseudo-ternary splits with a mid-boiling component; not applicable to wide-boiling feeds or high-fouling service (wall cleaning access); turndown below 40% degrades the vapor split control",
            "evidence_refs": ["cal:kg03:r1", "cal:kg03:r2"],
            "baseline": {
                "baseline_incumbent": "Conventional two-column direct sequence with intermediate tankage",
                "baseline_metric": "Reboiler duty 900 kW over minimum + remixing penalty",
                "candidate_metric": "620-660 kW for the same separation"
            },
            "killer_experiment": {
                "experiment": "Pilot-scale dividing-wall column 300 mm diameter with the actual solvent system, sweep reflux ratio and splits, measure duty vs the existing train at identical product specs",
                "kill_condition": "If measured duty reduction is below 15% at spec, the retrofit mechanism fails the economics",
                "cost_class": "PILOT"
            },
            "failure_modes": ["vapor split maldistribution at turndown", "wall fouling in dirty service", "control pairing across the wall during startup"],
            "commercial_path": {"buyer": "Specialty chemical plant operators with close-boiling solvent recovery trains"},
            "cross_domain_transition": "NONE (same domain: process distillation; mechanism established at pilot scale, applied to a specific plant economy)"
        },
        "pool": [
            {"record_id": "cal:kg03:r1", "title": "Dividing wall distillation columns: measured 25-35% energy savings for close-boiling ternary separations versus conventional two-column sequences"},
            {"record_id": "cal:kg03:r2", "title": "Vapor and liquid split control in dividing wall columns: operability windows and startup procedures at pilot scale"},
            {"record_id": "cal:kg03:r3", "title": "Underwood-Gilliland shortcut design of conventional column sequences and their minimum-duty limits"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg03:pa1", "perspective": "FORWARD", "title": "Dividing wall columns for cryogenic air separation (different feed system, different duty regime, but same underlying wall concept in an unrelated service)"},
                {"record_id": "cal:kg03:pa2", "perspective": "MECHANISM", "title": "Heat-integrated distillation sequences (heat pumps, double-effect) for solvent recovery (different energy-saving mechanism: external heat integration, not internal remixing elimination)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: the dividing-wall duty saving for close-boiling splits is among the best-measured unit operations in the literature (measured 25-35% at pilot and industrial scale); the claim is bounded to the applicable volatility window and the plant's 900 kW remixing penalty. The provided prior art covers DWC in cryogenic air separation (different service) and heat-integrated sequences (different mechanism) — neither teaches this retrofit for this solvent split. The killer experiment and kill condition are concrete and decisive."
        }
    },
    {
        "case_id": "CAL-KG-04",
        "domain_id": "agriculture",
        "pain_class": "INPUT_LOSS",
        "candidate": {
            "candidate_id": "CAL-KG-04",
            "technology_name": "Capillary-Wick Sub-Irrigation Beds for Greenhouse Water Cut",
            "problem": "Overhead greenhouse irrigation over-wets the top soil layer; 25-35% of applied water percolates below the root zone and is lost, and foliar wetting drives fungal disease pressure",
            "causal_chain": [
                "Water is supplied at the base through a capillary wick layer under the root zone",
                "matric potential draws water upward against gravity",
                "the root zone self-regulates at field capacity",
                "no percolation below the wick's capillary barrier",
                "applied water volume tracks transpiration demand"
            ],
            "unexploited_phenomenon": "Capillary rise of water in porous media: a 0.3-0.5 m wick lifts water at matric potentials matching root uptake without pumps (cal:kg04:r1)",
            "intervention": "Retrofit greenhouse beds with a 40 cm sand-based capillary wick layer over a water reservoir regulated by a float valve, planted crops root directly above",
            "governing_variables": "Wick height (m), pore-size distribution (mm), matric potential (kPa), reservoir level, crop transpiration rate",
            "predicted_effect": "20-30% cut in applied irrigation water vs overhead watering, 40-60% reduction in foliar wetting events, yield parity within 5% for tomato and cucumber",
            "equations": [
                "h_capillary = 2*sigma*cos(theta)/(rho*g*r_pore) — maximum capillary rise for the wick's dominant pore radius",
                "E_applied = E_transpiration + E_evaporation_surface (percolation term removed by wick barrier)"
            ],
            "boundary_conditions": "Capillary lift limited to ~0.5 m with fine sand; crop water demand above the wick's conductance saturates the bed and needs supplemental top watering; salts accumulate in the reservoir and need periodic flush",
            "evidence_refs": ["cal:kg04:r1", "cal:kg04:r2"],
            "baseline": {
                "baseline_incumbent": "Overhead sprinkler irrigation on a timer",
                "baseline_metric": "Applied water 130-135% of transpiration need",
                "candidate_metric": "Applied water 100-108% of transpiration need"
            },
            "killer_experiment": {
                "experiment": "Six paired greenhouse beds (wick vs overhead), same cultivars and climate, two seasons; log applied water, drainage lysimeter percolate, yield",
                "kill_condition": "If applied-water reduction is under 10% or yield drops more than 8%, the capillary mechanism fails its commercial promise",
                "cost_class": "FIELD"
            },
            "failure_modes": ["salt build-up in reservoir", "algae growth in the reservoir", "root intrusion into the wick layer", "high-demand crop stages exceeding wick conductance"],
            "commercial_path": {"buyer": "Commercial greenhouse vegetable growers in water-scarce regions"},
            "cross_domain_transition": "NONE (established horticultural physics applied to a specific water-economy service)"
        },
        "pool": [
            {"record_id": "cal:kg04:r1", "title": "Capillary rise in sand-based porous media: measured maximum rise heights and matric potential ranges for subirrigation design"},
            {"record_id": "cal:kg04:r2", "title": "Sub-irrigation versus overhead watering in greenhouse trials: measured percolation elimination and foliar disease reduction"},
            {"record_id": "cal:kg04:r3", "title": "Crop transpiration demand curves for greenhouse tomato and cucumber by growth stage"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg04:pa1", "perspective": "FORWARD", "title": "Drip irrigation with soil moisture sensor scheduling (point-source emitters at surface, timer or sensor controlled — different water-delivery physics, not capillary self-regulation)"},
                {"record_id": "cal:kg04:pa2", "perspective": "MECHANISM", "title": "Capillary wick beds for container nursery stock (ornamental nursery containers, not vegetable greenhouse bed retrofits with reservoir float control)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: capillary rise is governed by the pore-scale Young-Laplace relation, a measured textbook law; subirrigation percolation elimination is documented in horticultural field trials. Claims are bounded (20-30% water cut, yield parity within 5%, salt-flush duty disclosed). Prior art provided is drip scheduling (different delivery physics) and nursery-container wicks (different deployment) — no collision with the stated intervention. Field trial with decisive kill condition."
        }
    },
    {
        "case_id": "CAL-KG-05",
        "domain_id": "automotive",
        "pain_class": "AERO_DRAG",
        "candidate": {
            "candidate_id": "CAL-KG-05",
            "technology_name": "Boat-Tail Retrofit for Regional Delivery Vans",
            "problem": "Box-bodied delivery vans shed a large separated wake at the flat rear, with base drag contributing 30-40% of total road-load aerodynamic drag at highway speed, raising fuel use",
            "causal_chain": [
                "Angled boat-tail panels extend the rear body",
                "the separation line moves downstream onto the angled surfaces",
                "wake cross-section shrinks and base pressure recovers",
                "total drag coefficient falls",
                "fuel consumption falls at cruise speed"
            ],
            "unexploited_phenomenon": "Base-pressure recovery behind bluff bodies with boat-tailing: 10-30% drag-coefficient reduction measured for box vehicles (cal:kg05:r1)",
            "intervention": "Retrofit kit of four angled panels (12-15 degrees taper, 0.5-0.7 m extension) closing the van's rear box, with hinged bottom flap for loading dock clearance",
            "governing_variables": "Taper angle (deg), extension length (m), edge radius, yaw sensitivity, loading-dock articulation",
            "predicted_effect": "8-12% fuel-consumption reduction at 100 km/h cruise on regional duty cycles (10-20% Cd reduction on the vehicle), 1.5-2.5 year payback for a 60,000 km/yr fleet",
            "equations": [
                "Cd_total = Cd_forebody + Cd_base; boat-tail reduces Cd_base by raising base pressure coefficient Cp from -0.25 to -0.05 class",
                "F_drag = 0.5*rho*V^2*Cd*A; fuel reduction ~ proportional to road-load integral over the duty cycle"
            ],
            "boundary_conditions": "Benefit scales with highway-speed share of the duty cycle; city duty sees negligible gain; yaw crosswind degrades recovery above ~10 deg; loading-dock compatibility constrains the bottom panel and must be hinged",
            "evidence_refs": ["cal:kg05:r1", "cal:kg05:r2"],
            "baseline": {
                "baseline_incumbent": "Standard flat-rear box van body",
                "baseline_metric": "Cd ~ 0.38-0.42 class; cruise fuel consumption 100%",
                "candidate_metric": "Cd ~ 0.32-0.36 class; cruise fuel 88-92%"
            },
            "killer_experiment": {
                "experiment": "Track two instrumented identical vans (boat-tail vs stock) over a 10,000 km regional route with matched loads; verify in a coast-down test on a closed airfield",
                "kill_condition": "If coast-down shows Cd reduction below 5% or the 10,000 km fuel delta is below 3% with matched loads, the retrofit fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["panel flutter and fatigue at speed", "crosswind yaw sensitivity", "loading-dock interference and driver non-use of the hinged flap", "snow/ice buildup on panels"],
            "commercial_path": {"buyer": "Regional parcel fleet operators with highway-heavy routes"},
            "cross_domain_transition": "Heavy-truck aerodynamic boat-tailing -> light delivery vans (same base-drag physics scaled to a new vehicle class and loading constraint)"
        },
        "pool": [
            {"record_id": "cal:kg05:r1", "title": "Boat-tailing of bluff box bodies: wind-tunnel measured base-pressure recovery and 10-30% Cd reduction for heavy vehicles"},
            {"record_id": "cal:kg05:r2", "title": "Coast-down and track fuel-economy validation of trailer boat-tail retrofits on heavy trucks"},
            {"record_id": "cal:kg05:r3", "title": "Duty-cycle fuel models for regional delivery fleets and highway-share sensitivity"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg05:pa1", "perspective": "FORWARD", "title": "Trailer boat-tail devices for 18-wheel semi-trailers (different vehicle class, fixed box length, no hinged loading flap requirement)"},
                {"record_id": "cal:kg05:pa2", "perspective": "MECHANISM", "title": "Cab-roof air deflectors and gap fairings for tractor-trailers (upstream drag, not base drag recovery)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: base-drag pressure recovery from boat-tailing is among the best-measured bluff-body results in vehicle aerodynamics, with wind-tunnel AND track validation in the literature; the 8-12% fuel claim is honestly proportional to highway duty share. Prior art provided covers semi-trailer boat-tails (different class and constraint) and cab deflectors (different mechanism) — not van retrofits with the hinged loading constraint. Coast-down kill condition is decisive."
        }
    },
    {
        "case_id": "CAL-KG-06",
        "domain_id": "mining",
        "pain_class": "COMM_IN_BLIND_SPOT",
        "candidate": {
            "candidate_id": "CAL-KG-06",
            "technology_name": "Through-Rock Low-Frequency Radio Sparing for Deep-Level Ventilation Control",
            "problem": "Deep-level mine ventilation on-demand control needs fan and door setpoints updated from production faces, but wireline through shafts is cut by blasting and standard radios do not propagate through rock",
            "causal_chain": [
                "Low-frequency (30-300 kHz) magnetic-dipole link transmits through conductive rock",
                "skin depth at these frequencies in typical host rock exceeds tens of meters",
                "data link survives where VHF/UHF is attenuated to noise",
                "face-level sensors deliver ventilation demand data",
                "on-demand ventilation runs fans at demand-following speeds"
            ],
            "unexploited_phenomenon": "Skin-depth scaling of electromagnetic penetration in rock: at 100 kHz in 0.01 S/m rock, skin depth ~ 15-50 m, enabling through-rock link margins (cal:kg06:r1)",
            "intervention": "Deploy loop-antenna TTE (through-the-earth) telemetry at 60-150 kHz between face-level CO/flow sensors and the main ventilation controller, low bit-rate telemetry (10-100 bits/s) sufficient for setpoint updates",
            "governing_variables": "Frequency (kHz), rock conductivity (S/m), loop area-turns product (m2-turns), noise floor, bit rate",
            "predicted_effect": "Reliable setpoint telemetry across 200-400 m of rock with 10^-4 bit error rate class, enabling 20-30% ventilation fan energy reduction from demand-following control",
            "equations": [
                "delta = sqrt(2/(omega*mu*sigma)) — skin depth; at 100 kHz, sigma=0.01 S/m: delta ~ 50 m",
                "SNR = (H_rx * A_N * n) / (sqrt(4*k*T*B) + atmospherics) — received loop emf vs noise"
            ],
            "boundary_conditions": "Bit rate is low (10-100 bps — setpoint telemetry, not voice); link budget degrades in conductive ore zones (sigma > 0.1 S/m reduces skin depth below 15 m); lightning atmospheric noise dominates below 10 kHz; loop installation cost per station is material",
            "evidence_refs": ["cal:kg06:r1", "cal:kg06:r2"],
            "baseline": {
                "baseline_incumbent": "Leaky-feeder cable along haul ways with blast-damage repair crews plus scheduled fixed ventilation schedules",
                "baseline_metric": "100% ventilation energy at fixed schedule; leaky-feer repair downtime 8-16 h per blast cycle in bad sections",
                "candidate_metric": "70-80% ventilation energy; telemetry survives blasting"
            },
            "killer_experiment": {
                "experiment": "Install a 60 kHz TTE link across a known 300 m rock span at an operating mine; run 30 days of setpoint telemetry logging BER vs weekly conductivity core measurements",
                "kill_condition": "If BER exceeds 10^-3 or availability drops below 95% over the 30 days, the link margin is inadequate for control",
                "cost_class": "FIELD"
            },
            "failure_modes": ["conductive ore zones collapsing the link budget", "loop damage from production blasting at face level", "lightning noise events", "interference from VFD harmonics on the same frequency band"],
            "commercial_path": {"buyer": "Deep-level hard-rock mine operators under energy-cost and safety-regulatory pressure"},
            "cross_domain_transition": "Cave/mine rescue through-the-earth voice systems -> routine low-rate telemetry for ventilation control (same propagation physics, new always-on service class)"
        },
        "pool": [
            {"record_id": "cal:kg06:r1", "title": "Through-the-earth electromagnetic propagation at 30-300 kHz: measured skin depths in rock strata and loop-link budgets for mine communication"},
            {"record_id": "cal:kg06:r2", "title": "Mine ventilation-on-demand control: measured 20-30% fan energy reduction from demand-following setpoints"},
            {"record_id": "cal:kg06:r3", "title": "Leaky feeder mine communication systems: blast damage rates and repair economics"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg06:pa1", "perspective": "MECHANISM", "title": "TTE emergency communication systems for trapped-miner location and rescue voice (emergency-only service, voice bandwidths, not continuous telemetry for process control)"},
                {"record_id": "cal:kg06:pa2", "perspective": "FORWARD", "title": "Mesh WiFi nodes along haul ways with relay redundancy (line-of-sight propagation, not through-rock)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: skin-depth penetration through rock at 60-150 kHz is a measured, deployable reality (TTE systems are commercially fielded for emergency mine comms — the physics is proven); the claim honestly narrows the service to low-rate setpoint telemetry and discloses the conductive-zone and noise boundary. Prior art provided covers emergency voice TTE (different service) and haul-way mesh (different propagation) — no collision with continuous ventilation-control telemetry. Decisive 30-day BER kill condition."
        }
    },
    {
        "case_id": "CAL-KG-07",
        "domain_id": "construction",
        "pain_class": "CURING_WASTE",
        "candidate": {
            "candidate_id": "CAL-KG-07",
            "technology_name": "Self-Desiccating Low-Water Concrete Curing Aid",
            "problem": "Curing water for mass concrete pours is labor-intensive and wasteful; poorly cured surfaces carbonated and dust, and curing membranes that trap moisture cause surface defects",
            "causal_chain": [
                "Superabsorbent polymer (SAP) micro-doses are pre-blended into the mix",
                "after the initial set, SAP pores release internal curing water",
                "cement hydration continues without external water",
                "internal RH stays above self-desiccation threshold",
                "surface quality and near-surface durability improve with less curing water"
            ],
            "unexploited_phenomenon": "Internal curing via SAP water release: measured hydration continuation and 30-60% curing-water reduction in low-w/c concretes (cal:kg07:r1)",
            "intervention": "Add 0.2-0.4% by mass of dry SAP with 150-200 g/g absorption to the batch mix for high-performance concrete pours; adjust mix water accounting for SAP release",
            "governing_variables": "SAP dosage (% mass), absorption ratio (g/g), w/c ratio, ambient RH, section thickness",
            "predicted_effect": "30-60% reduction of external curing water demand, 20-40% reduction in plastic shrinkage cracking incidence, 28-day strength within 5% of control",
            "equations": [
                "m_SAP = (w_ic_needed - w_external) / (absorption * efficiency); w_ic ~ 0.07 kg water/kg cement for full hydration continuation",
                "RH_internal > 0.95 maintained during 7 days via SAP desorption isotherm"
            ],
            "boundary_conditions": "Benefit strongest at w/c < 0.40; SAP dosage above 0.6% entrains voids and drops strength; hot low-RH climates still need initial misting; not applicable to massive pours with adiabatic heat control as the primary issue",
            "evidence_refs": ["cal:kg07:r1", "cal:kg07:r2"],
            "baseline": {
                "baseline_incumbent": "External wet-curing with burlap/ponding or curing compound membranes",
                "baseline_metric": "Curing water 100% + labor; shrinkage cracking baseline incidence",
                "candidate_metric": "Curing water 40-70% + reduced cracking 20-40%; strength parity within 5%"
            },
            "killer_experiment": {
                "experiment": "Paired industrial slabs (SAP vs conventional curing) across three sites and seasons; measure water use, cracking maps at 28 days, strength cores",
                "kill_condition": "If 28-day strength loss exceeds 5% or cracking incidence is not reduced by at least 15% while saving 30% water, the mechanism fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["over-dosage strength loss from entrained voids", "SAP release kinetics mismatched to climate", "mix water miscalculation by batch plant operators"],
            "commercial_path": {"buyer": "Commercial concrete contractors and precast producers under water and labor cost pressure"},
            "cross_domain_transition": "Agricultural superabsorbent soil conditioners -> concrete internal curing (same hydrogel physics, new material host and release profile)" 
        },
        "pool": [
            {"record_id": "cal:kg07:r1", "title": "Superabsorbent polymers for internal curing of concrete: measured water release kinetics and hydration continuation at low w/c"},
            {"record_id": "cal:kg07:r2", "title": "Internal curing versus external wet curing: field-measured plastic shrinkage cracking reduction and curing water demand"},
            {"record_id": "cal:kg07:r3", "title": "Absorption and desorption isotherms of SAP hydrogels in cement pore solution"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg07:pa1", "perspective": "MECHANISM", "title": "Lightweight aggregate internal curing (pre-wetted LWA as the water reservoir — different carrier, established for mass concrete, not the fine-surface cracking service)"},
                {"record_id": "cal:kg07:pa2", "perspective": "FORWARD", "title": "Curing compound membranes and evaporation retarders (surface-side water retention, not internal reservoir release)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: SAP internal curing is a measured, active research-to-practice technology (RILEM state-of-the-art); hydrogel absorption/release is a textbook isotherm problem; the claims are bounded to low w/c and disclose the dosage void risk. Prior art provided covers LWA internal curing (different carrier) and membranes (different mechanism) — no collision. Field trial with decisive kill conditions on strength and cracking."
        }
    },
    {
        "case_id": "CAL-KG-08",
        "domain_id": "telecom",
        "pain_class": "THERMAL_LOSS",
        "candidate": {
            "candidate_id": "CAL-KG-08",
            "technology_name": "Phase-Shifted Pulse Tube Cooling for Remote RF Amplifier Cabinets",
            "problem": "Remote telecom cabinet power amplifiers in hot climates need cooling; compressor refrigeration draws 600-900 W per cabinet and fails in dusty environments, while passive vents underperform above 45 C ambient",
            "causal_chain": [
                "Stirling-cycle pulse-tube cryocooler derivatives run as heat pumps at 60-80 K temperature span class scaled to ambient",
                "acoustic power drives gas oscillation",
                "heat is shuttled by phase-shifted pressure-mass waves",
                "no compressor seals, no refrigerant, only helium",
                "cabinet heat is pumped to ambient with low maintenance"
            ],
            "unexploited_phenomenon": "Thermoacoustic/pulse-tube heat pumping with phase shifters: measured COP 0.8-1.5 class for 30-60 K spans above ambient (cal:kg08:r1)",
            "intervention": "Replace cabinet scroll-compressor AC with a linear-motor pulse-tube heat pump sized 400 W at 50 C ambient, helium working gas, finned ambient rejection",
            "governing_variables": "Drive frequency (Hz), phase-shift orifice tuning, heat-lift (W), rejection temperature (C), COP",
            "predicted_effect": "500-700 W cabinet cooling with 350-500 W input (COP 1.0-1.4 at 20 K span), MTBF > 5x compressor class in dusty service (no filters, no seals), maintenance interval 5 years",
            "equations": [
                "COP = Q_lift / W_acoustic; phasing of mass flux vs pressure wave set by orifice + inertance",
                "Q_lift ~ T_m * m_dot * (s-amplitude) * phase_efficiency"
            ],
            "boundary_conditions": "COP falls steeply above 40 K spans (above that, vapor compression wins on efficiency); heat lift per unit bounded by acoustic power; cost per unit higher than scroll AC (payback comes from maintenance savings, not energy savings); oversized for sub-300 W loads",
            "evidence_refs": ["cal:kg08:r1", "cal:kg08:r2"],
            "baseline": {
                "baseline_incumbent": "Scroll compressor air conditioner with filter maintenance",
                "baseline_metric": "Cooling 600-900 W draw; filter/blower maintenance quarterly in dusty sites; MTBF 3-4 years",
                "candidate_metric": "350-500 W draw; 5-year maintenance; MTBF 15+ years projected"
            },
            "killer_experiment": {
                "experiment": "Two cabinets at a 50 C ambient dust-test site (pulse-tube vs scroll), 6-month soak: log power, internal temp, and maintenance events",
                "kill_condition": "If input power exceeds 550 W for 500 W lift, or any seal/filter maintenance is needed within 6 months, the maintenance-value mechanism fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["linear-motor fatigue", "orifice tuning drift with ambient temperature", "reject-fin fouling in extreme dust", "acoustic vibration coupling to RF components"],
            "commercial_path": {"buyer": "Telecom tower operators in hot/dusty regions with high maintenance cost per site visit"},
            "cross_domain_transition": "Space-instrument pulse-tube cryocoolers -> ambient-temperature cabinet heat pumping (same thermodynamic cycle scaled to a new service and reliability regime)"
        },
        "pool": [
            {"record_id": "cal:kg08:r1", "title": "Pulse tube and thermoacoustic heat pumps: measured COP 0.8-1.5 for moderate temperature spans and multi-year unattended MTBF in space instruments"},
            {"record_id": "cal:kg08:r2", "title": "Linear-drive Stirling and pulse-tube coolers: fatigue life and vibration isolation for sensitive electronics"},
            {"record_id": "cal:kg08:r3", "title": "Telecom cabinet cooling duty cycles and maintenance cost per site in hot dusty climates"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg08:pa1", "perspective": "MECHANISM", "title": "Vapor-compression cabinet air conditioners with electrostatic dust pre-filters (different cycle, different failure modes — the incumbent)"},
                {"record_id": "cal:kg08:pa2", "perspective": "FORWARD", "title": "Thermoacoustic refrigeration laboratory demonstrators for food refrigeration spans (different temperature regime and duty, lab-scale heat lift)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: pulse-tube heat pumping is a mature, flight-proven cycle (space instruments run unattended for years); COP claims are honestly bounded to moderate spans with vapor-compression winning above 40 K spans — disclosed; the commercial case rests on maintenance savings, stated. Prior art provided is the incumbent (different cycle) and lab demonstrators at different regimes — no collision. Decisive 6-month kill condition on power and maintenance."
        }
    },
    {
        "case_id": "CAL-KG-09",
        "domain_id": "aerospace",
        "pain_class": "MATERIAL_DEGRADATION",
        "candidate": {
            "candidate_id": "CAL-KG-09",
            "technology_name": "Shape-Adaptive LE Slat Erosion Shield via SMA Tendon",
            "problem": "Leading-edge slats of short-haul aircraft in sandy/coastal environments erode and dent; scheduled LE inspection and replacement drives 2-3% of airframe maintenance cost on these routes",
            "causal_chain": [
                "Thin superelastic NiTi ribbon is embedded along the LE sub-skin",
                "erosive particle impacts and slat cycling strain the ribbon locally",
                "superelastic stress plateau absorbs and recovers the strain",
                "sub-skin stays within elastic limits and self-re-centers",
                "dent depth and skin replacement rate fall"
            ],
            "unexploited_phenomenon": "Superelastic stress plateau of NiTi near RT (8% recoverable strain) absorbing local impact energy (cal:kg09:r1)",
            "intervention": "Embed a 1 mm NiTi tendon strip at 3-5 mm depth along the slat LE sub-skin, bonded in the existing rivet-free zone, as a dent-mitigation retrofit at heavy checks",
            "governing_variables": "Transformation temperatures (C), plateau stress (MPa), ribbon thickness (mm), embed depth (mm), impact energy spectrum (mJ)",
            "predicted_effect": "40-60% reduction in LE dent depth from runway-debris impacts in the 5-50 mJ class; LE skin replacement interval extended 1.5-2x on sandy-route fleets",
            "equations": [
                "E_absorbed = sigma_plateau * epsilon_recoverable * V_affected; sigma_plateau ~ 400-600 MPa, epsilon ~ 6-8%",
                "dent_depth ~ (E_impact / (k_subskin + k_SMA))^(1/2) — the ribbon raises effective local stiffness and recovery"
            ],
            "boundary_conditions": "Only for impact energies the plateau can absorb (5-50 mJ class — stones above this exceed superelastic capacity); transformation temperatures must stay below 60 C ramp skin temp (RT-class alloy); certification of a sub-skin retrofit is a moderate path (region repair, not primary structure); not applicable to hail-size impacts",
            "evidence_refs": ["cal:kg09:r1", "cal:kg09:r2"],
            "baseline": {
                "baseline_incumbent": "Standard aluminum LE skin with scheduled inspection and replacement",
                "baseline_metric": "LE skin replacement every 2-3 heavy checks on sandy routes",
                "candidate_metric": "Replacement every 4-6 heavy checks on the same routes"
            },
            "killer_experiment": {
                "experiment": "Bench LE panel sections (tendon vs control) shot-blasted with calibrated 5-50 mJ grit at representative angles; measure dent depth maps and fatigue life after 10^5 pressurization cycles",
                "kill_condition": "If dent depth reduction is below 25% or fatigue life is reduced vs control, the retrofit fails",
                "cost_class": "LAB"
            },
            "failure_modes": ["galvanic coupling NiTi-aluminum needs isolation layer", "certification path for sub-skin retrofit", "impact class above plateau capacity", "bond fatigue over 10^5 cycles"],
            "commercial_path": {"buyer": "Airlines with sandy/coastal short-haul fleets and heavy-check cost pressure"},
            "cross_domain_transition": "Orthodontic/industrial superelastic NiTi energy absorption -> aircraft LE protection (same material physics, new impact service class)"
        },
        "pool": [
            {"record_id": "cal:kg09:r1", "title": "Superelastic NiTi: measured 6-8% recoverable strain, 400-600 MPa plateau stresses, and impact energy absorption in structural embeds"},
            {"record_id": "cal:kg09:r2", "title": "Leading-edge erosion and dent statistics on sandy-route aircraft fleets: maintenance replacement intervals and cost drivers"},
            {"record_id": "cal:kg09:r3", "title": "Certification pathways for bonded sub-skin structural repairs at heavy check intervals"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg09:pa1", "perspective": "MECHANISM", "title": "Erosion-protective coatings and tapes for LE blades (surface barrier materials, not sub-skin energy-absorbing tendons)"},
                {"record_id": "cal:kg09:pa2", "perspective": "FORWARD", "title": "SMA actuators for aerodynamic variable-geometry chevrons (actuation service, not passive impact absorption)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: NiTi superelasticity (plateau stress, 6-8% recoverable strain) is a measured textbook material behavior; impact-energy absorption in embedded ribbons follows directly and is bounded honestly to the 5-50 mJ class with the certification path disclosed as a risk. Prior art provided covers coatings (different mechanism) and SMA actuators (different service) — no collision. Bench test with decisive kill conditions."
        }
    },
    {
        "case_id": "CAL-KG-10",
        "domain_id": "power",
        "pain_class": "GRID_INSTABILITY",
        "candidate": {
            "candidate_id": "CAL-KG-10",
            "technology_name": "Synchronous Condenser Conversion of Retired Thermal Generators",
            "problem": "Grid regions retiring thermal plants lose inertia and short-circuit strength, degrading frequency stability and protection coordination as inverter-based resources take share",
            "causal_chain": [
                "Retired generator's rotor is reconnected excitation-only",
                "spinning mass provides real inertia (H constant seconds)",
                "field excitation supplies dynamic reactive power",
                "short-circuit current contribution restores protection coordination",
                "grid frequency ride-through and voltage stability improve"
            ],
            "unexploited_phenomenon": "Synchronous machine inertia and reactive capability without fuel: converting a thermal unit to a synchronous condenser preserves 60-100% of its MVA capability at near-zero fuel cost (cal:kg10:r1)",
            "intervention": "Convert a retiring 300 MVA steam turbine unit: remove turbine blades or decouple, add starting motor and flywheel option, keep generator, exciter, and step-up transformer",
            "governing_variables": "Inertia constant H (MW-s/MVA), reactive range (MVAR), short-circuit ratio, starting method, conversion capex",
            "predicted_effect": "1.2-2.5 GW-s of inertia per converted unit, +90 to -150 MVAR dynamic range, short-circuit strength restored to 70-90% of the unit's original contribution; 8-14 month conversion; capex 10-20% of equivalent new SC",
            "equations": [
                "df/dt = (P_imbalance - P_damping)/(2*H*S_base) — inertia from the preserved rotor",
                "Q_dynamic limited by exciter ceiling and machine capability curve"
            ],
            "boundary_conditions": "Requires the generator and GSU transformer to be sound (residual-life assessment); rotor rewind may be needed for the reactive ceiling; site auxiliary power remains needed; not a substitute for new transmission",
            "evidence_refs": ["cal:kg10:r1", "cal:kg10:r2"],
            "baseline": {
                "baseline_incumbent": "Greenfield synchronous condensers or battery-STATCOM hybrids providing equivalent inertia/SER",
                "baseline_metric": "Capex per GW-s inertia at 100% (new-build reference)",
                "candidate_metric": "Capex per GW-s inertia 10-25% of new-build (conversion reuses existing rotor and transformer)"
            },
            "killer_experiment": {
                "experiment": "Convert one unit, then run grid-integrity tests: frequency response to a staged 0.5 GW generation trip in the region before/after conversion, and short-circuit-level measurement at the bus",
                "kill_condition": "If the converted unit does not deliver at least 80% of its modeled inertia response and 70% of original fault current contribution, the conversion mechanism fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["rotor residual-life surprises", "exciter ceiling limits reactive range", "conversion schedule slip during outage windows", "market rules not crediting inertia"],
            "commercial_path": {"buyer": "Transmission system operators and plant owners facing retirement economics and stability mandates"},
            "cross_domain_transition": "NONE (established grid-machine engineering applied to a specific retirement economy — conversions are individually known, the systematic conversion-program economics are the candidate)"
        },
        "pool": [
            {"record_id": "cal:kg10:r1", "title": "Synchronous condenser conversions of retired thermal units: measured inertia contribution and reactive capability retention at near-zero fuel"},
            {"record_id": "cal:kg10:r2", "title": "Grid frequency stability with declining inertia: frequency-response metrics for regions integrating inverter-based resources"},
            {"record_id": "cal:kg10:r3", "title": "New-build synchronous condenser costs per GW-s of inertia versus conversion costs"}
        ],
        "prior_art": {
            "relevant_records": [
                {"record_id": "cal:kg10:pa1", "perspective": "FORWARD", "title": "Battery energy storage frequency response (inverter-based synthetic inertia response, different physical inertia quality — electronic, not rotor)"},
                {"record_id": "cal:kg10:pa2", "perspective": "MECHANISM", "title": "Greenfield synchronous condenser installations (new machines, not conversion of retired thermal rotors and their site infrastructure)"}
            ]
        },
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": None,
            "expected_kill_surface": None,
            "ground_truth_basis": "Physics: synchronous condenser conversion is an established, fielded grid practice (multiple conversions exist worldwide); inertia from a preserved rotor is direct physics; claims bounded to sound-machine precondition with residual-life risk disclosed. Prior art provided covers batteries (different inertia quality) and new-build SCs (different economics) — no collision with the conversion economics. Grid-level test with decisive kill conditions."
        }
    },
]

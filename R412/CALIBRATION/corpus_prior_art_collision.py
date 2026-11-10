"""R412 Phase 3 — attacker-calibration corpus, Quadrant 4:
PRIOR_ART_COLLISION.

Mechanisms whose exact mechanism+intervention+effect is already taught by
the records the attacker is GIVEN in its prior-art set. Ground truth:
the collision is in the provided inputs; a calibrated attacker must
KILL on prior_art citing the teaching record. These cases calibrate the
attacker's novelty discrimination — the surface that killed 6 of the 14
R411 candidates.

The colliding art here describes REAL, established, published technology
classes (frame-level descriptions of well-known published work). The
candidates duplicate that art while claiming novelty — the defect a
calibrated attacker must catch.
"""

PA_CASES = [
    {
        "case_id": "CAL-PA-01",
        "domain_id": "solar_pv",
        "pain_class": "EFFICIENCY",
        "candidate": {
            "candidate_id": "CAL-PA-01",
            "technology_name": "Adaptive-Step Perturb-and-Observe MPPT",
            "problem": "PV arrays operate off the maximum power point under irradiance variation",
            "causal_chain": [
                "Controller perturbs duty cycle",
                "measures power change",
                "adapts step size to the slope",
                "converges to MPP faster with less oscillation",
                "energy harvest rises 1-3%"
            ],
            "unexploited_phenomenon": "Duty-cycle dithering gradient search (cal:pa01:r1)",
            "intervention": "P&O MPPT with step size adapted to dP/dD, claiming novelty in the adaptive step rule",
            "governing_variables": "Step size, perturbation period, irradiance ramp rate",
            "predicted_effect": "1-3% annual energy gain vs fixed-step P&O; 99.5% tracking efficiency",
            "equations": [
                "D(k+1) = D(k) +/- step*(dP/dD sign and magnitude)"
            ],
            "boundary_conditions": "Standard grid-tie inverters",
            "evidence_refs": ["cal:pa01:r1"],
            "baseline": {
                "baseline_incumbent": "Fixed-step P&O MPPT",
                "baseline_metric": "Tracking efficiency 98.5%",
                "candidate_metric": "99.5% claimed"
            },
            "killer_experiment": {
                "experiment": "PV simulator A/B over standard irradiance profiles",
                "kill_condition": "If tracking efficiency gain below 0.5%, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["drift under fast ramps"],
            "commercial_path": {"buyer": "Inverter OEMs"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa01:r1", "title": "Adaptive-step perturb-and-observe MPPT algorithms: step-size adaptation rules to dP/dD published and compared extensively"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa01:pa1", "perspective": "MECHANISM", "title": "Adaptive perturb-and-observe MPPT with variable step size: multiple published implementations teaching the same mechanism+intervention+effect (faster convergence, less oscillation)"},
            {"record_id": "cal:pa01:pa2", "perspective": "FORWARD", "title": "Review of MPPT methods (P&O, INC, fractional open-circuit): adaptive-step P&O documented as an established class"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (adaptive-step P&O MPPT is published extensively — same mechanism, intervention, and effect)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["teaches", "same", "published", "adaptive", "P&O", "identical"],
            "ground_truth_basis": "Adaptive-step P&O MPPT is among the most-published PV control schemes in existence — the provided MECHANISM-perspective record teaches the identical mechanism (duty perturbation), intervention (adaptive step rule), and effect (faster convergence, less oscillation). Claiming novelty in this is a collision. A calibrated attacker must KILL on prior_art citing the teaching record."
        }
    },
    {
        "case_id": "CAL-PA-02",
        "domain_id": "batteries_ev",
        "pain_class": "THERMAL_LOSS",
        "candidate": {
            "candidate_id": "CAL-PA-02",
            "technology_name": "PCM-Composite Wrap for Cylindrical Cell Modules",
            "problem": "Cell-to-cell temperature gradients age EV modules unevenly",
            "causal_chain": [
                "Paraffin composite wraps cells",
                "gradients drive lateral heat flow into the PCM",
                "peak cell temperature and gradient fall",
                "module life extends",
                "warranty economics improve"
            ],
            "unexploited_phenomenon": "PCM gradient smoothing (cal:pa02:r1)",
            "intervention": "Composite PCM wrap for cylindrical modules claiming thermal gradient cut and life extension as novel",
            "governing_variables": "PCM conductivity, wrap thickness, cell heat generation",
            "predicted_effect": "Module temperature gradient halved; module life +20%",
            "equations": [
                "Gradient ~ q_cell * L / k_eff; composite k ~ 1-5 W/mK bounds the cut"
            ],
            "boundary_conditions": "Fast-charge profiles",
            "evidence_refs": ["cal:pa02:r1"],
            "baseline": {
                "baseline_incumbent": "Air gap module",
                "baseline_metric": "Gradient 8-10 C",
                "candidate_metric": "4-5 C claimed"
            },
            "killer_experiment": {
                "experiment": "Cycled module pair, gradient logging",
                "kill_condition": "If gradient cut below 25%, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["PCM leakage"],
            "commercial_path": {"buyer": "Pack makers"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa02:r1", "title": "PCM composite battery thermal management: paraffin-graphite wraps for cylindrical modules measured to cut gradients and peak temperatures"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa02:pa1", "perspective": "MECHANISM", "title": "Paraffin-graphite composite PCM wraps for cylindrical 18650/21700 modules: published implementations teaching the same wrap intervention and gradient/peak-temperature effect"},
            {"record_id": "cal:pa02:pa2", "perspective": "FORWARD", "title": "Reviews of PCM battery thermal management listing composite cell wraps as an established configuration"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (PCM composite cell wraps are published extensively for exactly this intervention and effect)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["teaches", "composite", "wrap", "published", "same", "gradient"],
            "ground_truth_basis": "Paraffin-graphite composite PCM wraps for cylindrical modules are a well-published battery-thermal-management configuration; the provided MECHANISM-perspective record teaches the same wrap + gradient-smoothing effect. Presenting it as novel is a collision. A calibrated attacker must KILL on prior_art."
        }
    },
    {
        "case_id": "CAL-PA-03",
        "domain_id": "data_center_thermal",
        "pain_class": "THERMAL_LOSS",
        "candidate": {
            "candidate_id": "CAL-PA-03",
            "technology_name": "Hot-Aisle Containment With Variable-Speed CRAH Fans",
            "problem": "Mixing of hot and cold air wastes cooling energy in data halls",
            "causal_chain": [
                "Aisle containment doors and baffles",
                "hot and cold streams separate",
                "CRAH fans modulate on supply temperature",
                "bypass and recirculation losses fall",
                "cooling energy falls 20-30%"
            ],
            "unexploited_phenomenon": "Airstream separation (cal:pa03:r1)",
            "intervention": "Hot-aisle containment plus variable-speed fan control claiming novelty",
            "governing_variables": "Containment integrity, fan curves, control setpoint",
            "predicted_effect": "20-30% cooling energy reduction",
            "equations": [
                "E_cooling ~ (Q_IT/COP*(1+bypass fraction))"
            ],
            "boundary_conditions": "Retrofit halls",
            "evidence_refs": ["cal:pa03:r1"],
            "baseline": {
                "baseline_incumbent": "Open rows",
                "baseline_metric": "Cooling energy 100%",
                "candidate_metric": "70-80% claimed"
            },
            "killer_experiment": {
                "experiment": "A/B containment retrofit energy metering",
                "kill_condition": "If energy cut below 10%, fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["leakage"],
            "commercial_path": {"buyer": "Colo operators"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa03:r1", "title": "Hot-aisle containment with variable-speed CRAH control: measured 20-30% cooling energy reductions across field deployments"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa03:pa1", "perspective": "MECHANISM", "title": "Hot-aisle/cold-aisle containment with CRAH fan-speed modulation: published and deployed at scale teaching the same mechanism+intervention+effect"},
            {"record_id": "cal:pa03:pa2", "perspective": "FORWARD", "title": "ASHRAE-class data center airflow management guidance documenting containment + variable fan control as standard practice"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (containment + variable-speed CRAH control is standard, published, deployed practice)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["standard", "deployed", "containment", "published", "same"],
            "ground_truth_basis": "Hot-aisle containment with variable-speed CRAH control is textbook data-center practice with thousands of published deployments teaching the same mechanism, intervention, and 20-30% effect. Claiming it as a novel candidate is a direct collision. A calibrated attacker must KILL on prior_art."
        }
    },
    {
        "case_id": "CAL-PA-04",
        "domain_id": "industrial_sensing",
        "pain_class": "BLIND_SPOT",
        "candidate": {
            "candidate_id": "CAL-PA-04",
            "technology_name": "Motor Current Signature Analysis for Bearing Fault Detection",
            "problem": "Motor bearing faults are detected late by vibration monitoring requiring sensor access",
            "causal_chain": [
                "Bearing faults modulate air-gap torque",
                "modulation appears in stator current sidebands",
                "spectrum analysis detects fault frequencies",
                "no vibration sensor needed",
                "condition monitoring cost falls"
            ],
            "unexploited_phenomenon": "Torque modulation sidebands in stator current (cal:pa04:r1)",
            "intervention": "MCSA for bearing fault detection claiming novelty in the sideband detection rule",
            "governing_variables": "Fault characteristic frequencies, load level, sideband amplitude",
            "predicted_effect": "90%+ detection of incipient bearing faults from the motor control center",
            "equations": [
                "f_sideband = f_s +/- k*f_fault"
            ],
            "boundary_conditions": "Constant-load duty",
            "evidence_refs": ["cal:pa04:r1"],
            "baseline": {
                "baseline_incumbent": "Accelerometer vibration monitoring",
                "baseline_metric": "Detection at incipient stage with sensors",
                "candidate_metric": "Equivalent detection from current"
            },
            "killer_experiment": {
                "experiment": "Seeded bearing faults, MCSA vs vibration ground truth",
                "kill_condition": "If detection below 70%, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["load variation masking"],
            "commercial_path": {"buyer": "Plant reliability teams"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa04:r1", "title": "Motor current signature analysis: stator-current sidebands for bearing and rotor fault detection published across decades"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa04:pa1", "perspective": "MECHANISM", "title": "MCSA bearing fault detection: published methods teaching sideband detection of bearing characteristic frequencies — the identical mechanism+intervention+effect"},
            {"record_id": "cal:pa04:pa2", "perspective": "FAILURE", "title": "2025 records teaching electrical signature analysis for wind turbine drivetrain defect detection (the exact class that killed C-wind-2~2 in R411)"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (MCSA bearing detection is decades-published; identical mechanism+intervention+effect)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["MCSA", "published", "same", "sideband", "teaches", "decades"],
            "ground_truth_basis": "MCSA for bearing faults is a decades-old, extensively published technique teaching the identical mechanism (torque modulation sidebands), intervention (current spectrum analysis), and effect (fault detection without vibration sensors). The provided records include the 2025 wind-turbine ESA class that killed an R411 candidate on exactly this surface. A calibrated attacker must KILL on prior_art."
        }
    },
    {
        "case_id": "CAL-PA-05",
        "domain_id": "semiconductor_fab",
        "pain_class": "YIELD",
        "candidate": {
            "candidate_id": "CAL-PA-05",
            "technology_name": "Run-to-Run EWMA Control for Etch Depth",
            "problem": "Etch depth drifts between tool cleans, causing spec excursions",
            "causal_chain": [
                "Post-run metrology feeds an EWMA controller",
                "recipe offsets update run to run",
                "drift is compensated before excursion",
                "Cpk rises",
                "scrap falls"
            ],
            "unexploited_phenomenon": "Exponentially weighted drift compensation (cal:pa05:r1)",
            "intervention": "R2R EWMA controller for etch depth claiming novelty in the weighting scheme",
            "governing_variables": "EWMA lambda, metrology lag, drift rate, noise",
            "predicted_effect": "Cpk from 1.2 to 1.8; excursion rate -60%",
            "equations": [
                "offset(k+1) = lambda*error(k) + (1-lambda)*offset(k)"
            ],
            "boundary_conditions": "Single-product tools",
            "evidence_refs": ["cal:pa05:r1"],
            "baseline": {
                "baseline_incumbent": "Static recipe with periodic recalibration",
                "baseline_metric": "Cpk 1.2",
                "candidate_metric": "Cpk 1.8 claimed"
            },
            "killer_experiment": {
                "experiment": "A/B R2R vs static on production lots",
                "kill_condition": "If Cpk gain below 0.3, fails",
                "cost_class": "PILOT"
            },
            "failure_modes": ["metrology noise amplification"],
            "commercial_path": {"buyer": "Fabs"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa05:r1", "title": "Run-to-run EWMA control for semiconductor processes: published theory and fab deployments (the MIT/semiconductor APC canon)"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa05:pa1", "perspective": "MECHANISM", "title": "Run-to-run process control with EWMA and double-exponential filtering: published and deployed APC standard teaching the identical controller for etch and CMP processes"},
            {"record_id": "cal:pa05:pa2", "perspective": "FORWARD", "title": "Commercial APC platforms shipping R2R EWMA control for etch depth and deposition"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (R2R EWMA control is the canonical, commercially deployed APC standard for exactly this service)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["EWMA", "APC", "deployed", "published", "standard", "same"],
            "ground_truth_basis": "R2R EWMA control for etch (and CMP) is the canonical published+commercially-deployed APC technology — the provided records teach the identical mechanism (EWMA drift compensation), intervention (recipe offset updates), and effect (Cpk improvement). The collision is total. A calibrated attacker must KILL on prior_art."
        }
    },
    {
        "case_id": "CAL-PA-06",
        "domain_id": "chemical_process",
        "pain_class": "WASTE_STREAM",
        "candidate": {
            "candidate_id": "CAL-PA-06",
            "technology_name": "Membrane Pervaporation for Ethanol Dehydration",
            "problem": "Azeotropic ethanol-water separation costs energy in distillation",
            "causal_chain": [
                "Hydrophilic membrane selectively permeates water",
                "vaporization across the membrane",
                "ethanol product dried past the azeotrope",
                "no entrainer chemicals",
                "dehydration energy falls"
            ],
            "unexploited_phenomenon": "Selective water permeation in PVA-class membranes (cal:pa06:r1)",
            "intervention": "Pervaporation membrane dehydration of ethanol claiming novelty",
            "governing_variables": "Membrane selectivity, flux, feed temperature, stage count",
            "predicted_effect": "99.5% ethanol product; 30-50% dehydration energy cut vs azeotropic distillation",
            "equations": [
                "J_water = P_w/l * (p_w,feed - p_w,perm)"
            ],
            "boundary_conditions": "Fuel-ethanol scale",
            "evidence_refs": ["cal:pa06:r1"],
            "baseline": {
                "baseline_incumbent": "Azeotropic distillation with entrainer",
                "baseline_metric": "Energy 100%",
                "candidate_metric": "50-70% claimed"
            },
            "killer_experiment": {
                "experiment": "Pilot pervaporation skid vs azeotropic column energy audit",
                "kill_condition": "If energy cut below 20%, fails",
                "cost_class": "PILOT"
            },
            "failure_modes": ["membrane fouling"],
            "commercial_path": {"buyer": "Ethanol plants"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa06:r1", "title": "Pervaporation with PVA membranes for ethanol dehydration: published and commercially deployed (thousands of installations)"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa06:pa1", "perspective": "MECHANISM", "title": "Pervaporation ethanol dehydration with polymeric membranes: commercial installations teaching the identical mechanism+intervention+effect"},
            {"record_id": "cal:pa06:pa2", "perspective": "FORWARD", "title": "Industrial pervaporation plant designs for bioethanol dehydration at fuel-ethanol scale"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (pervaporation ethanol dehydration is commercially deployed at scale)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["commercial", "deployed", "pervaporation", "same", "installations"],
            "ground_truth_basis": "Pervaporation for ethanol dehydration is a mature, commercially deployed separation (thousands of installations) — the provided records teach the identical mechanism, intervention, and effect at the stated scale. Claiming it as a novel candidate is a direct collision. A calibrated attacker must KILL on prior_art."
        }
    },
    {
        "case_id": "CAL-PA-07",
        "domain_id": "mining",
        "pain_class": "PARTICULATE",
        "candidate": {
            "candidate_id": "CAL-PA-07",
            "technology_name": "Fog-Based Dust Scrubbing at Conveyor Transfer Points",
            "problem": "Ore transfer points release respirable dust; dry baghouses are costly for diffuse sources",
            "causal_chain": [
                "Fine water fog nucleates onto dust particles",
                "agglomerates settle",
                "respirable fraction falls",
                "fan energy and bags eliminated",
                "dust control cost falls"
            ],
            "unexploited_phenomenon": "Fog nucleation agglomeration (cal:pa07:r1)",
            "intervention": "Pressurized-water fog cannon system at transfer points claiming novelty in dust capture",
            "governing_variables": "Droplet size vs particle size, fog density, capture velocity",
            "predicted_effect": "80-90% respirable dust capture at 1/3 baghouse cost",
            "equations": [
                "Capture ~ droplet/particle size ratio match (0.1-1 class optimal)"
            ],
            "boundary_conditions": "Dry climates need evaporation accounting",
            "evidence_refs": ["cal:pa07:r1"],
            "baseline": {
                "baseline_incumbent": "Dry baghouse",
                "baseline_metric": "99% capture at high cost",
                "candidate_metric": "80-90% at 1/3 cost"
            },
            "killer_experiment": {
                "experiment": "Side-by-side dust capture test at a transfer point",
                "kill_condition": "If capture below 60%, fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["freezing climates"],
            "commercial_path": {"buyer": "Mine operators"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa07:r1", "title": "Water fog and surfactant spray dust suppression at ore transfer points: published capture efficiencies and deployed systems"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa07:pa1", "perspective": "MECHANISM", "title": "Fog/spray dust suppression systems for mining transfer points: commercial products and published field studies teaching the same mechanism+intervention+capture effect"},
            {"record_id": "cal:pa07:pa2", "perspective": "FORWARD", "title": "Spray nozzle engineering guides for respirable dust capture at conveyor transfers"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (fog/spray dust suppression at transfer points is commercial, published practice)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["commercial", "spray", "fog", "same", "transfer", "published"],
            "ground_truth_basis": "Fog/spray dust suppression at ore transfer points is a commercial product class with published field studies teaching the same mechanism (droplet nucleation agglomeration), intervention (fog cannons at transfers), and effect (80-90% capture). The collision is direct. A calibrated attacker must KILL on prior_art."
        }
    },
    {
        "case_id": "CAL-PA-08",
        "domain_id": "machining",
        "pain_class": "TOOL_WEAR",
        "candidate": {
            "candidate_id": "CAL-PA-08",
            "technology_name": "Minimum Quantity Lubrication for Milling",
            "problem": "Flood coolant in milling costs disposal, health, and energy",
            "causal_chain": [
                "Microliter oil aerosol at the cutting edge",
                "boundary lubrication replaces bulk cooling",
                "chip evacuation by air jet",
                "coolant disposal eliminated",
                "cost and environmental burden fall"
            ],
            "unexploited_phenomenon": "Boundary lubrication by oil mist (cal:pa08:r1)",
            "intervention": "MQL system for milling claiming novelty in the delivery rule",
            "governing_variables": "Oil rate (mL/h), nozzle targeting, air pressure, tool wear mode",
            "predicted_effect": "Tool life parity with flood; coolant cost -90%",
            "equations": [
                "Friction coefficient at the tool-chip interface ~ oil film boundary regime"
            ],
            "boundary_conditions": "Not for deep-hole drilling or titanium roughing",
            "evidence_refs": ["cal:pa08:r1"],
            "baseline": {
                "baseline_incumbent": "Flood emulsion coolant",
                "baseline_metric": "Coolant cost 100%",
                "candidate_metric": "10-15% claimed"
            },
            "killer_experiment": {
                "experiment": "ISO tool-life MQL vs flood",
                "kill_condition": "If tool life below 80% of flood, fails",
                "cost_class": "LAB"
            },
            "failure_modes": ["mist inhalation controls"],
            "commercial_path": {"buyer": "Machine shops"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa08:r1", "title": "Minimum quantity lubrication milling: published tool-life parity results and deployed MQL systems"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa08:pa1", "perspective": "MECHANISM", "title": "MQL for milling and turning: extensive published literature and commercial systems teaching the identical aerosol intervention and coolant-elimination effect"},
            {"record_id": "cal:pa08:pa2", "perspective": "FORWARD", "title": "Machine-tool OEM MQL-ready spindle options documented across catalogs"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (MQL is published and commercially standard for milling)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["MQL", "commercial", "published", "same", "spindle", "standard"],
            "ground_truth_basis": "MQL for milling is a published, commercially standardized technology (machine-tool catalogs ship MQL-ready spindles); the provided records teach the identical mechanism (boundary lubrication by microliter aerosol), intervention (MQL delivery), and effect (tool-life parity, coolant elimination). A calibrated attacker must KILL on prior_art."
        }
    },
    {
        "case_id": "CAL-PA-09",
        "domain_id": "power",
        "pain_class": "GRID_INSTABILITY",
        "candidate": {
            "candidate_id": "CAL-PA-09",
            "technology_name": "Grid-Forming Inverter Control for Islanded Microgrids",
            "problem": "Inverter-based microgrids need a voltage/frequency reference when islanded",
            "causal_chain": [
                "Inverter control emulates synchronous machine swing",
                "virtual inertia and damping terms",
                "voltage/frequency form autonomously",
                "black start and islanding work",
                "microgrid stability achieved"
            ],
            "unexploited_phenomenon": "Swing-equation emulation in inverter control (cal:pa09:r1)",
            "intervention": "Grid-forming droop/virtual-synchronous-machine control claiming novelty",
            "governing_variables": "Virtual inertia constant, damping, droop slopes, current limiting",
            "predicted_effect": "Stable islanded operation with 100% inverter generation; black-start capability",
            "equations": [
                "J*domega/dt = P_ref - P_out - D*omega (VSM swing)"
            ],
            "boundary_conditions": "Fault current limited by inverter rating",
            "evidence_refs": ["cal:pa09:r1"],
            "baseline": {
                "baseline_incumbent": "Diesel gensets as the islanded reference",
                "baseline_metric": "Stability from rotating machines",
                "candidate_metric": "Stability from inverters claimed"
            },
            "killer_experiment": {
                "experiment": "Hardware-in-the-loop islanding test",
                "kill_condition": "If transient instability at 50% load step, fails",
                "cost_class": "LAB"
            },
            "failure_modes": ["fault current insufficiency for protection"],
            "commercial_path": {"buyer": "Microgrid developers"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa09:r1", "title": "Grid-forming inverter control: virtual synchronous machine and droop methods published and standardized"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa09:pa1", "perspective": "MECHANISM", "title": "Virtual synchronous machine grid-forming control: extensive published literature and commercial grid-forming inverters teaching the identical swing-emulation intervention"},
            {"record_id": "cal:pa09:pa2", "perspective": "FORWARD", "title": "IEEE 2800-class interconnection standards incorporating grid-forming requirements"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (grid-forming/VSM control is published, standardized, and commercially deployed)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["grid-forming", "VSM", "standard", "IEEE", "commercial", "published"],
            "ground_truth_basis": "Grid-forming inverter control (VSM/droop) is an extensively published, standardized (IEEE 2800-class), and commercially deployed technology; the provided records teach the identical mechanism (swing-equation emulation), intervention (inverter control), and effect (islanded stability, black start). A calibrated attacker must KILL on prior_art."
        }
    },
    {
        "case_id": "CAL-PA-10",
        "domain_id": "agriculture",
        "pain_class": "INPUT_LOSS",
        "candidate": {
            "candidate_id": "CAL-PA-10",
            "technology_name": "Variable-Rate Nitrogen Application From NDVI Zoning",
            "problem": "Uniform nitrogen application over-wastes in high-organic zones and under-feeds poor zones",
            "causal_chain": [
                "NDVI map from drone or satellite",
                "management zones classified",
                "prescription map drives variable-rate spreaders",
                "nitrogen matches crop need per zone",
                "input cost and nitrate leaching fall"
            ],
            "unexploited_phenomenon": "Biomass-greenness proxy for crop N status (cal:pa10:r1)",
            "intervention": "NDVI-based variable-rate N application claiming novelty",
            "governing_variables": "NDVI threshold, zone count, spreader control resolution, N-response model",
            "predicted_effect": "10-15% N reduction at equal yield; leaching -20%",
            "equations": [
                "N_applied(zone) = f(NDVI(zone), yield target)"
            ],
            "boundary_conditions": "Sensor timing at critical growth stages",
            "evidence_refs": ["cal:pa10:r1"],
            "baseline": {
                "baseline_incumbent": "Uniform N application",
                "baseline_metric": "N 100% uniform",
                "candidate_metric": "85-90% of uniform N at equal yield"
            },
            "killer_experiment": {
                "experiment": "Strip trials VRA vs uniform, yield + soil nitrate",
                "kill_condition": "If N saving below 5% at yield parity, fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["cloud cover timing"],
            "commercial_path": {"buyer": "Crop input retailers, farms"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:pa10:r1", "title": "NDVI-based variable-rate nitrogen application: published field trials and commercial precision-ag platforms"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:pa10:pa1", "perspective": "MECHANISM", "title": "Variable-rate N from NDVI zoning: published multi-year field trials teaching the identical sensing-zoning-prescription mechanism and 10-15% N-saving effect"},
            {"record_id": "cal:pa10:pa2", "perspective": "FORWARD", "title": "Commercial precision-ag platforms offering NDVI-based variable-rate prescription as a shipping feature"}
        ]},
        "ground_truth": {
            "label": "PRIOR_ART_COLLISION",
            "expected_final": "KILLED",
            "defect_class": "prior-art collision (NDVI-based VR-N is published and a shipping commercial feature)",
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": ["commercial", "shipping", "NDVI", "variable-rate", "same", "platforms"],
            "ground_truth_basis": "NDVI-based variable-rate nitrogen is a shipping feature of commercial precision-ag platforms with multi-year published field trials teaching the identical mechanism (NDVI zoning), intervention (prescription spreading), and effect (10-15% N savings at yield parity). A calibrated attacker must KILL on prior_art."
        }
    },
]

"""R412 Phase 3 — attacker-calibration corpus, Quadrant 3: NEAR_MISS.

Real, established mechanisms carrying ONE specific defect each: the
wrong magnitude, wrong regime, wrong material limit, or an honest
physical bound the candidate ignores. These are the DISCRIMINATION
tests — subtler than KNOWN_BAD. Ground truth: the attacker must KILL
for the specific recorded defect; kills citing other grounds with
correct physics still count as kills for the headline metrics, but the
basis-match measurement checks whether the kill names the actual
defect.
"""

NM_CASES = [
    {
        "case_id": "CAL-NM-01",
        "domain_id": "electronics_thermal",
        "pain_class": "THERMAL_LOSS",
        "candidate": {
            "candidate_id": "CAL-NM-01",
            "technology_name": "Electrocaloric Solid-State Server Cooling at Rack Scale",
            "problem": "Data center compressor cooling has moving parts and refrigerants; a solid-state cooling layer at the chip would eliminate both",
            "causal_chain": [
                "Electrocaloric film under electric field changes temperature",
                "alternating field cycles heat absorption/release",
                "heat is pumped from chip to heat spreader",
                "no compressor, no refrigerant",
                "rack cooling is solid-state"
            ],
            "unexploited_phenomenon": "Electrocaloric effect in ceramic thin films (cal:nm01:r1)",
            "intervention": "Multilayer electrocaloric cells bonded to CPU lids claiming 200 W heat pump per chip at 20 K span with COP 3",
            "governing_variables": "Adiabatic temperature change (K), field (V/micron), frequency (Hz), film volume, contact resistance",
            "predicted_effect": "200 W per chip at 20 K span, COP 3, rack-level 20% cooling energy saving vs chilled water",
            "equations": [
                "Q_per_cycle = rho*c*delta_T_ad * V_active; with measured delta_T_ad 2-5 K and cycle rates 1-10 Hz, per-gram heat pump rates are W-scale per gram — scaling to 200 W needs kg-class active film",
                "COP_bound = T_cold/delta_T * (electrocaloric efficiency 30-60% of Carnot)"
            ],
            "boundary_conditions": "Stated as rack-scale competitive with chilled water",
            "evidence_refs": ["cal:nm01:r1"],
            "baseline": {
                "baseline_incumbent": "Chilled-water cold plates",
                "baseline_metric": "COP 4-6 system level",
                "candidate_metric": "COP 3 claimed at chip"
            },
            "killer_experiment": {
                "experiment": "Calorimetric measurement of one 20 W cell's lift and COP at 20 K span, then linear extrapolation audit",
                "kill_condition": "If measured cell COP below 2 or per-gram lift makes 200 W packaging impossible under 5 cm^3, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["fatigue", "leakage current"],
            "commercial_path": {"buyer": "Server OEMs"},
            "cross_domain_transition": "Caloric materials research -> server cooling"
        },
        "pool": [
            {"record_id": "cal:nm01:r1", "title": "Electrocaloric thin films: measured adiabatic temperature changes 2-5 K at practical fields; demonstrated heat pumping remains W-scale in research prototypes, not rack-scale"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm01:pa1", "perspective": "MECHANISM", "title": "Electrocaloric cooling prototypes: laboratory demonstrations at 1-10 W scale; scaling and fatigue remain open"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "magnitude (real effect, orders-of-magnitude gap between measured 1-10 W prototypes and the claimed 200 W/chip at COP 3)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["2-5 K", "W-scale", "prototype", "orders", "scale", "fatigue", "per gram"],
            "ground_truth_basis": "The electrocaloric effect is real and the citations are honest about 2-5 K adiabatic changes, but the state of the art pumps 1-10 W in prototypes; claiming 200 W/chip at COP 3 skips 2 orders of magnitude in power density and unresolved fatigue. A calibrated attacker should KILL on the magnitude/scale gap (a physics/baseline-scale argument), even though the underlying effect is real."
        }
    },
    {
        "case_id": "CAL-NM-02",
        "domain_id": "transport_infra",
        "pain_class": "ENERGY_HARVEST",
        "candidate": {
            "candidate_id": "CAL-NM-02",
            "technology_name": "Roadway Piezoelectric Harvesting Powering Highway Lighting",
            "problem": "Highway lighting and signage need grid connections; harvesting traffic energy in the roadway would remove trenching cost",
            "causal_chain": [
                "Piezoelectric transducers embedded under asphalt",
                "truck axles strain the transducers",
                "mechanical work converts to charge",
                "storage powers lighting at night",
                "grid connection eliminated"
            ],
            "unexploited_phenomenon": "Piezoelectric energy harvesting under traffic loads (cal:nm02:r1)",
            "intervention": "10 km of embedded piezo strips claiming 300 kW average harvest, powering continuous highway lighting and signage",
            "governing_variables": "Transducer coupling, traffic density, axle loads, contact time, asphalt viscoelastic loss",
            "predicted_effect": "300 kW average from 10 km of roadway; lighting fully off-grid",
            "equations": [
                "P_max per axle pass ~ m*g*delta_h_available; road deflection energy is ~1-100 J per axle pass, mostly dissipated in asphalt viscoelasticity — 300 kW needs ~3000 J/s class, far above total available deflection work at realistic traffic",
                "Available: ~10-100 W per lane-km measured class"
            ],
            "boundary_conditions": "Claims lighting-scale power",
            "evidence_refs": ["cal:nm02:r1"],
            "baseline": {
                "baseline_incumbent": "Grid-connected LED lighting",
                "baseline_metric": "Grid draw 0 (existing solution works)",
                "candidate_metric": "300 kW claimed"
            },
            "killer_experiment": {
                "experiment": "Instrument 100 m of embedded strip, measure harvest over 30 days of real traffic",
                "kill_condition": "If power below 1 kW per km, fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["asphalt fatigue around embeds"],
            "commercial_path": {"buyer": "Highway agencies"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:nm02:r1", "title": "Piezoelectric roadway harvesting: measured output 1-100 W per lane-km under real traffic; per-axle available deflection energy 1-100 J, largely absorbed by asphalt viscoelasticity"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm02:pa1", "perspective": "FAILURE", "title": "Field trials of roadway piezo harvesters: per-lane-km power orders below lighting demand; embed fatigue degrades output within months"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "magnitude (available deflection energy and measured harvest are 3+ orders below the claim; also a hidden cost: embedding degrades pavement life)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["1-100 W", "per axle", "deflection", "viscoelastic", "orders", "kW"],
            "ground_truth_basis": "The physics of harvesting road deflection is real, but the total available mechanical work per axle pass (1-100 J) and measured field outputs (1-100 W/lane-km) sit 3+ orders below the claimed 300 kW per 10 km; energy conservation on the traffic stream's tiny deflection budget kills the lighting-scale claim. A calibrated attacker should KILL on magnitude."
        }
    },
    {
        "case_id": "CAL-NM-03",
        "domain_id": "automotive",
        "pain_class": "WASTE_HEAT",
        "candidate": {
            "candidate_id": "CAL-NM-03",
            "technology_name": "Exhaust Thermoelectric Generator Covering 10% of Cruising Electrical Load",
            "problem": "Car alternator load costs 1-3% fuel economy; waste-heat recovery could feed the electrical system",
            "causal_chain": [
                "TEG modules on exhaust pipe",
                "Seebeck effect converts Delta-T to electricity",
                "cruise exhaust 550 C vs coolant 90 C",
                "hundreds of watts are generated",
                "alternator de-loads and fuel economy rises"
            ],
            "unexploited_phenomenon": "Thermoelectric Seebeck generation (cal:nm03:r1)",
            "intervention": "2 kg Bi2Te3/skutterudite TEG array claiming 800 W continuous at cruise, displacing alternator load and adding 8-10% vehicle fuel economy",
            "governing_variables": "ZT, hot-side temperature, cold-side temperature, module area, exhaust mass flow",
            "predicted_effect": "800 W at cruise; 8-10% vehicle fuel-economy gain",
            "equations": [
                "eta_TEG ~ (ZT_avg ~1)(Delta_T/T_hot) * (1/4) efficiency factor ~ 4-6% of heat flux at best; 800 W needs ~15 kW heat flux and ~2 m^2 module",
                "fuel gain from 800 W alternator de-load is ~0.5-1.5% (alternator mechanical load 1-3%)"
            ],
            "boundary_conditions": "Claims 8-10% fuel gain from electrical de-load alone",
            "evidence_refs": ["cal:nm03:r1"],
            "baseline": {
                "baseline_incumbent": "Alternator at 92% efficiency",
                "baseline_metric": "Electrical load 1-3% of engine power",
                "candidate_metric": "8-10% fuel gain claimed"
            },
            "killer_experiment": {
                "experiment": "Chassis-dynamometer A/B with TEG installed, fuel flow metered at cruise",
                "kill_condition": "If fuel gain below 2%, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["module thermal cycling fatigue", "backpressure penalty"],
            "commercial_path": {"buyer": "Automakers"},
            "cross_domain_transition": "Space RTG thermoelectrics -> automotive"
        },
        "pool": [
            {"record_id": "cal:nm03:r1", "title": "Automotive TEG demonstrations: measured 100-400 W systems; efficiency 3-5% of exhaust heat; net fuel-economy effect 0.5-1.5%; module cost and weight at 800 W scale exceed value"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm03:pa1", "perspective": "FAILURE", "title": "Automotive TEG programs: mass, backpressure, and module cost terminated commercial deployment; net benefit below 2% fuel"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "baseline/magnitude inversion (alternator de-load bounds the fuel gain at ~0.5-1.5%; the 8-10% claim exceeds the physical size of the displaced load)",
            "expected_kill_surface": "baseline",
            "expected_defect_in_basis": ["alternator", "1-3%", "0.5", "1.5", "load", "cannot exceed", "efficiency"],
            "ground_truth_basis": "The Seebeck mechanism is real and 100-400 W systems have been demonstrated, but the claimed 8-10% fuel-economy gain inverts the arithmetic: the alternator consumes only 1-3% of engine power, so even a perfect electrical de-load caps the gain near 1-3%; measured TEG programs netted 0.5-1.5%. The claim exceeds the size of the displaced baseline load by 4-8x. A calibrated attacker should KILL on baseline arithmetic."
        }
    },
    {
        "case_id": "CAL-NM-04",
        "domain_id": "industrial_valves",
        "pain_class": "RESPONSE_TIME",
        "candidate": {
            "candidate_id": "CAL-NM-04",
            "technology_name": "SMA Actuated High-Frequency Safety Shutoff Valve",
            "problem": "Pneumatic shutoff valves need instrument air infrastructure; an electric SMA actuator would remove it",
            "causal_chain": [
                "NiTi SMA wire contracts when heated",
                "wire contraction pulls the valve stem",
                "current controls the actuator",
                "valve cycles on demand",
                "instrument air eliminated"
            ],
            "unexploited_phenomenon": "SMA wire actuation (cal:nm04:r1)",
            "intervention": "SMA wire actuator for a 2-inch safety shutoff valve cycling at 50 Hz duty, claiming pneumatic-class response and million-cycle life",
            "governing_variables": "Wire gauge, transformation temperature, cooling time, stroke, cycle frequency",
            "predicted_effect": "50 Hz cycling, 5 ms response, >10^6 cycles",
            "equations": [
                "Cycle rate bounded by heat/cool time: t_cool ~ (thermal mass)/(h*A) ~ 0.5-5 s for practical wire packs — 50 Hz is beyond passive cooling",
                "SMA fatigue: 10^6 cycles at 4% strain is near the measured limit at low strain; at actuation strains 2-4% cycle life is 10^4-10^6 with degradation"
            ],
            "boundary_conditions": "Claims 50 Hz and 10^6 cycles",
            "evidence_refs": ["cal:nm04:r1"],
            "baseline": {
                "baseline_incumbent": "Pneumatic actuator at 100-500 ms, 10^6+ cycles",
                "baseline_metric": "Response 100-500 ms, life 10^6+",
                "candidate_metric": "5 ms, 10^6 cycles claimed"
            },
            "killer_experiment": {
                "experiment": "Cycle the actuator at 50 Hz, log stroke decay and failures",
                "kill_condition": "If response lags above 50 ms or life below 10^5, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["fatigue", "thermal lag"],
            "commercial_path": {"buyer": "Plant operators"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:nm04:r1", "title": "SMA wire actuators: measured cycle rates 0.2-2 Hz limited by cooling time; fatigue life 10^4-10^6 cycles at practical strains; 50 Hz operation requires active cooling"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm04:pa1", "perspective": "MECHANISM", "title": "Thermal actuation bandwidth limits: SMA actuator frequency is cooling-bound, order of Hz, not tens of Hz"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "boundary-condition failure (SMA actuation is real but cooling-limited to ~0.2-2 Hz; the 50 Hz spec is outside the mechanism's physical bandwidth)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["cooling", "Hz", "bandwidth", "thermal", "cycle rate", "fatigue"],
            "ground_truth_basis": "SMA actuation works and is fielded for low-frequency duties, but actuation bandwidth is cooling-bound at ~0.2-2 Hz for passive wire packs and fatigue life at actuation strains is 10^4-10^6 — the 50 Hz / 10^6-cycle spec sits outside the mechanism's physical envelope. A calibrated attacker should KILL on boundary conditions."
        }
    },
    {
        "case_id": "CAL-NM-05",
        "domain_id": "electronics_thermal",
        "pain_class": "THERMAL_LOSS",
        "candidate": {
            "candidate_id": "CAL-NM-05",
            "technology_name": "Graphene Film Replacing Solder Thermal Interface",
            "problem": "Solder TIM between die and heat spreader has 10-30 W/mK effective conductivity and fatigue issues; graphene's 2000-5000 W/mK in-plane conductivity suggests a better TIM",
            "causal_chain": [
                "Graphene film layered as the thermal interface",
                "high thermal conductivity moves heat across the interface",
                "thermal resistance falls",
                "junction temperature drops 15-20 C",
                "device reliability and headroom improve"
            ],
            "unexploited_phenomenon": "Graphene's thermal conductivity (cal:nm05:r1)",
            "intervention": "Replace solder TIM with 20-layer graphene film claiming 5x interface conductance improvement",
            "governing_variables": "In-plane vs through-plane conductivity, interface contact resistance, layer count, adhesion",
            "predicted_effect": "5x interface thermal conductance; 15-20 C junction temperature drop",
            "equations": [
                "R_interface = R_contact1 + t/k_through-plane + R_contact2; graphene through-plane k ~ 5-20 W/mK (anisotropic!), not 2000-5000 (in-plane)",
                "Compare: solder k 30-50 W/mK, t 50 micron — graphene's through-plane anisotropy makes it WORSE than solder at equal thickness"
            ],
            "boundary_conditions": "Interface heat flow is THROUGH-PLANE",
            "evidence_refs": ["cal:nm05:r1"],
            "baseline": {
                "baseline_incumbent": "Solder TIM ~ 10-30 W/mK effective",
                "baseline_metric": "Interface resistance baseline",
                "candidate_metric": "5x better claimed"
            },
            "killer_experiment": {
                "experiment": "ASTM laser-flash through-plane measurement of the film stack plus contact-resistance test on a TIM bench",
                "kill_condition": "If through-plane conductance not at least 2x solder, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["delamination"],
            "commercial_path": {"buyer": "Chip packaging"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:nm05:r1", "title": "Graphene thermal transport: in-plane 2000-5000 W/mK measured, through-plane 5-20 W/mK measured (strong anisotropy); TIM performance is through-plane-bound"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm05:pa1", "perspective": "MECHANISM", "title": "Anisotropic conduction in layered graphene films: through-plane limits their use as TIMs; in-plane conductivity is irrelevant to interface heat flow"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "mechanism/anisotropy (the cited conductivity is the in-plane value; TIM heat flow is through-plane where graphene measures 5-20 W/mK — worse than solder)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["in-plane", "through-plane", "anisotropy", "5-20", "interface", "direction"],
            "ground_truth_basis": "Graphene's headline 2000-5000 W/mK is IN-PLANE; through-plane is 5-20 W/mK, and TIM heat flow crosses through-plane, where graphene is worse than the solder it replaces. The mechanism claim confuses the conductivity direction — a real-material, real-number error. A calibrated attacker should KILL on this physics/mechanism error."
        }
    },
    {
        "case_id": "CAL-NM-06",
        "domain_id": "wind",
        "pain_class": "AERO_PERF",
        "candidate": {
            "candidate_id": "CAL-NM-06",
            "technology_name": "Vortex Generator Retrofit Claiming 3% AEP Gain on Modern Blades",
            "problem": "Rotor blade airfoil separation near the root reduces lift; vortex generators re-energize the boundary layer",
            "causal_chain": [
                "VGs mix momentum into the boundary layer",
                "separation is delayed",
                "local lift recovers",
                "annual energy production rises",
                "retrofit pays back within 3 years"
            ],
            "unexploited_phenomenon": "Boundary-layer momentum mixing by VGs (cal:nm06:r1)",
            "intervention": "Root-region VG retrofit on a MODERN (post-2015) blade claiming 3.0% AEP gain",
            "governing_variables": "VG height vs boundary layer, placement chord fraction, blade design vintage",
            "predicted_effect": "3.0% AEP gain on modern blade designs",
            "equations": [
                "AEP gain depends on pre-existing separation loss: 2000s-era root separation gave 1-3% recoverable; post-2015 designs already control separation (cuffs, redesigned root airfoils), leaving typically 0.2-0.8%"
            ],
            "boundary_conditions": "Modern blade with existing root-flow control",
            "evidence_refs": ["cal:nm06:r1"],
            "baseline": {
                "baseline_incumbent": "Modern blade as designed",
                "baseline_metric": "AEP as certified",
                "candidate_metric": "+3.0% claimed"
            },
            "killer_experiment": {
                "experiment": "SCADA A/B analysis with met-normalization across 12 months",
                "kill_condition": "If gain below 1%, fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["VG erosion"],
            "commercial_path": {"buyer": "Wind farm owners"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:nm06:r1", "title": "Vortex generator retrofits: measured 1-3% AEP gains on pre-2010 blade designs with root separation; gains on post-2015 designs 0.2-0.8% (separation already managed)"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm06:pa1", "perspective": "FORWARD", "title": "Modern blade root-flow management (gull cuffs, redesigned root sections) documented to control the separation VGs target"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "baseline (the recoverable separation loss is already engineered out on modern blades; the 3% gain belongs to the pre-2010 baseline class, not the stated modern-blade baseline)",
            "expected_kill_surface": "baseline",
            "expected_defect_in_basis": ["pre-2010", "modern", "already", "0.2-0.8", "cuff", "managed"],
            "ground_truth_basis": "VG physics is real and 1-3% gains are measured — on older blades whose root separation was unmanaged. On post-2015 designs with cuffs and redesigned root sections, the recoverable loss is 0.2-0.8%, so the 3% claim measures against a baseline that no longer exists. A calibrated attacker should KILL on baseline (the incumbent already contains the fix class)."
        }
    },
    {
        "case_id": "CAL-NM-07",
        "domain_id": "grid_storage",
        "pain_class": "GRID_INSTABILITY",
        "candidate": {
            "candidate_id": "CAL-NM-07",
            "technology_name": "Supercapacitor Bank for Multi-Hour Grid Energy Shifting",
            "problem": "Grid evening ramp needs storage; supercapacitors have million-cycle life and instant response",
            "causal_chain": [
                "Supercapacitor banks charge at midday solar peak",
                "evening ramp discharge 2 hours at 50 MW",
                "million-cycle life and 95% round trip",
                "replaces battery storage",
                "cycling cost near zero"
            ],
            "unexploited_phenomenon": "EDLC high cycle life (cal:nm07:r1)",
            "intervention": "100 MWh supercapacitor plant claiming 2-hour daily shifting competitive with lithium storage",
            "governing_variables": "Energy density (Wh/kg, Wh/L), cost ($/kWh), self-discharge (%/day), cycle life",
            "predicted_effect": "100 MWh stored, daily 2-hour discharge, 20-year life, cost-competitive with Li-ion",
            "equations": [
                "Wh_cost: EDLC 5,000-20,000 $/kWh vs Li-ion 100-300 $/kWh (50-100x); volume: EDLC 10-20 Wh/L vs Li 300-500 Wh/L — 100 MWh EDLC needs ~5,000-10,000 m^3",
                "Self-discharge: EDLC 2-10%/day vs Li <1%/month — multi-hour shifting loses meaningful fraction"
            ],
            "boundary_conditions": "Multi-hour, daily-cycle bulk storage service",
            "evidence_refs": ["cal:nm07:r1"],
            "baseline": {
                "baseline_incumbent": "Li-ion storage at 100-300 $/kWh",
                "baseline_metric": "$/kWh and $/kW for 2-hour storage",
                "candidate_metric": "Claimed competitive"
            },
            "killer_experiment": {
                "experiment": "Cost and volume model audit of the 100 MWh plant BOM",
                "kill_condition": "If $/kWh above 10x Li-ion, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["cell balancing"],
            "commercial_path": {"buyer": "Utilities"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:nm07:r1", "title": "EDLC characteristics: measured energy density 5-10 Wh/kg (10-20 Wh/L), cost 5,000-20,000 $/kWh, self-discharge 2-10%/day; cycle life excellent — suited to seconds-minutes services"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm07:pa1", "perspective": "MECHANISM", "title": "EDLC vs battery service mapping: energy density and cost confine supercapacitors to power-quality and bridging services, not multi-hour bulk shifting"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "hidden dependency / service mismatch (EDLC's real strengths are power and cycle life; energy density, cost per kWh, and self-discharge make multi-hour shifting 50-100x over cost and volume-prohibitive)",
            "expected_kill_surface": "baseline",
            "expected_defect_in_basis": ["Wh/kg", "$/kWh", "5,000", "self-discharge", "energy density", "volume"],
            "ground_truth_basis": "Every EDLC parameter cited is real, but applying them to multi-hour bulk storage inverts the technology's service envelope: 5-20 Wh/L and $5,000-20,000/kWh make 100 MWh ~ 50-100x Li-ion cost and a warehouse-scale volume, with 2-10%/day self-discharge eating the shifted energy. A calibrated attacker should KILL on the service/baseline mismatch."
        }
    },
    {
        "case_id": "CAL-NM-08",
        "domain_id": "marine",
        "pain_class": "PROPULSION",
        "candidate": {
            "candidate_id": "CAL-NM-08",
            "technology_name": "MHD Propulsion for Cargo Ship Retrofit",
            "problem": "Propeller efficiency and wake inefficiency cost fuel; a propeller-less magnetohydrodynamic drive would remove moving parts",
            "causal_chain": [
                "Magnetic field crosses a seawater duct",
                "current through the conductive seawater creates Lorentz force",
                "water is accelerated without moving parts",
                "thrust drives the ship",
                "noise and maintenance fall"
            ],
            "unexploited_phenomenon": "MHD Lorentz thrust (cal:nm08:r1)",
            "intervention": "Retrofit a 20,000 DWT coaster with duct MHD claiming propeller-equivalent thrust efficiency at sea",
            "governing_variables": "Seawater conductivity (4-5 S/m), field strength (T), current density (A/m^2), electrode corrosion, duct drag",
            "predicted_effect": "Propeller-equivalent propulsive efficiency (60% class) at ship scale",
            "equations": [
                "Thrust ~ sigma*B^2*V*volume only for B^2 large: seawater sigma ~ 4-5 S/m makes the Lorentz force density small unless B ~ 10-20 T and J ~ 10^3-10^4 A/m^2 — superconducting magnets; electrode losses and electrolysis scale with J^2/sigma",
                "Measured efficiencies in MHD experiments: 10-40% at model scale with superconducting magnets; efficiency collapses at low field"
            ],
            "boundary_conditions": "Retrofit at 1-3 T conventional magnets claimed equivalent to propellers",
            "evidence_refs": ["cal:nm08:r1"],
            "baseline": {
                "baseline_incumbent": "Propeller at 55-70% propulsive efficiency",
                "baseline_metric": "60% class efficiency",
                "candidate_metric": "60% claimed at retrofit scale"
            },
            "killer_experiment": {
                "experiment": "Tow-tank MHD duct test with 2 T field, measure thrust vs electrical input",
                "kill_condition": "If efficiency below 30%, fails",
                "cost_class": "LAB"
            },
            "failure_modes": ["electrode corrosion", "field collapse"],
            "commercial_path": {"buyer": "Ship owners"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:nm08:r1", "title": "MHD ship propulsion: Yamato-1 class demonstrations with superconducting 4 T magnets reached ~30% total efficiency at 30 kN-class thrust; seawater conductivity bounds efficiency; corrosion and field requirements block scale-up"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm08:pa1", "perspective": "MECHANISM", "title": "Seawater MHD efficiency analysis: 4-5 S/m conductivity forces superconducting-magnet-class fields; retrofit-scale conventional magnets cannot reach propeller efficiency"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "boundary-condition failure (MHD works only in the superconducting 4+ T regime and even then measured ~30% efficiency; a 1-3 T retrofit claim is outside the regime)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["conductivity", "4-5 S/m", "tesla", "Yamato", "30%", "superconducting"],
            "ground_truth_basis": "MHD thrust is real (Yamato-1 sailed) but required superconducting 4 T magnets for ~30% efficiency at small thrust; seawater conductivity (4-5 S/m) means a 1-3 T retrofit falls far below propeller-class efficiency, and electrode corrosion at the needed current densities is unsolved. A calibrated attacker should KILL on the regime/boundary violation."
        }
    },
    {
        "case_id": "CAL-NM-09",
        "domain_id": "hvac_chiller",
        "pain_class": "WASTE_HEAT",
        "candidate": {
            "candidate_id": "CAL-NM-09",
            "technology_name": "Ejector Refrigeration From 90 C Waste Heat Claiming COP 1.2",
            "problem": "Industrial 90 C waste heat is low-grade; ejector refrigeration could convert it to cooling",
            "causal_chain": [
                "Waste heat boils the refrigerant motive stream",
                "ejector entrains and compresses the suction stream",
                "refrigeration effect at the evaporator",
                "no compressor, only heat input",
                "chilled water from waste heat"
            ],
            "unexploited_phenomenon": "Ejector (thermal compressor) refrigeration (cal:nm09:r1)",
            "intervention": "Steam ejector chiller driven by 90 C heat claiming COP 1.2 at 7 C chilled water",
            "governing_variables": "Motive temperature (C), entrainment ratio, evaporator/condenser temperatures, refrigerant pair",
            "predicted_effect": "COP 1.2 (thermal) at 90 C motive / 7 C evaporation / 35 C condensation",
            "equations": [
                "COP_ejector = entrainment_ratio * (h_evap effect / h_motive); measured entrainment ratios at 90 C motive with 28 K lift: 0.1-0.3 — COP 0.15-0.5",
                "COP 1.2 requires either motive > 150 C or lift < 10 K"
            ],
            "boundary_conditions": "90 C motive, 7 C chilled, 35 C condensing",
            "evidence_refs": ["cal:nm09:r1"],
            "baseline": {
                "baseline_incumbent": "Double-effect absorption chiller COP 1.1-1.4 at 140 C+ heat",
                "baseline_metric": "Absorption COP 1.1-1.4 (needs 140 C+)",
                "candidate_metric": "COP 1.2 claimed at 90 C"
            },
            "killer_experiment": {
                "experiment": "Calorimetric COP measurement of an ejector rig at the stated conditions",
                "kill_condition": "If COP below 0.8, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["off-design instability"],
            "commercial_path": {"buyer": "Plant energy managers"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:nm09:r1", "title": "Ejector refrigeration measured COPs: 0.15-0.5 for motive 80-100 C with 25-30 K lift; COP 1.0+ needs motive >= 150 C or small lift; entrainment ratio physics sets the bound"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm09:pa1", "perspective": "MECHANISM", "title": "Entrainment ratio limits of steam ejectors: measured values cap COP below 0.5 at 90 C motive with condenser/evaporator lifts of industrial service"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "magnitude/regime (ejector refrigeration is real but entrainment physics caps COP at 0.15-0.5 for 90 C motive with industrial lift; COP 1.2 at 90 C matches only 150 C+ double-effect absorption territory)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["entrainment", "0.15", "0.5", "150 C", "lift", "COP"],
            "ground_truth_basis": "Ejector refrigeration genuinely converts low-grade heat to cooling, but the entrainment-ratio physics caps measured COP at 0.15-0.5 for 90 C motive with a 28 K lift; claiming 1.2 (double-effect absorption territory) at 90 C contradicts the cited measurements. A calibrated attacker should KILL on magnitude."
        }
    },
    {
        "case_id": "CAL-NM-10",
        "domain_id": "construction",
        "pain_class": "MAINTENANCE",
        "candidate": {
            "candidate_id": "CAL-NM-10",
            "technology_name": "Self-Healing Bacterial Concrete for Bridge Decks Claiming 30-Year Crack-Free Service",
            "problem": "Bridge deck micro-cracking admits chlorides; crack sealing maintenance is costly",
            "causal_chain": [
                "Encapsulated Bacillus spores lie dormant in concrete",
                "cracks admit water and nutrients",
                "spores germinate and precipitate calcite",
                "cracks seal themselves within weeks",
                "chloride ingress stops and maintenance falls"
            ],
            "unexploited_phenomenon": "MICP calcite precipitation by encapsulated bacteria (cal:nm10:r1)",
            "intervention": "Bacterial concrete for bridge decks claiming full autonomous sealing of cracks up to 0.8 mm and a 30-year maintenance-free deck life",
            "governing_variables": "Spore viability decades, crack width (mm), healing latency (weeks), temperature cycles, healing repeat cycles",
            "predicted_effect": "Seals cracks to 0.8 mm within weeks, repeatedly, over 30 years of service, cutting deck maintenance 70%",
            "equations": [
                "Healing width measured: 0.1-0.5 mm typical (up to 0.8 in optimized lab conditions); latency 1-6 weeks at 20 C, months below 10 C",
                "Repeat healing: measured 2-3 successive events before nutrient/spore exhaustion at lab scale — 30 years implies dozens"
            ],
            "boundary_conditions": "Outdoor temperature cycles, de-icing salt exposure, repeated cracking events over decades",
            "evidence_refs": ["cal:nm10:r1"],
            "baseline": {
                "baseline_incumbent": "Epoxy crack injection at 5-10 year intervals",
                "baseline_metric": "Maintenance cost baseline, 5-10 y cycle",
                "candidate_metric": "70% maintenance cut, 30-year life claimed"
            },
            "killer_experiment": {
                "experiment": "Outdoor exposure slabs with induced 0.5 mm cracks, three freeze-thaw/winter cycles, chloride ingress test",
                "kill_condition": "If crack sealing below 60% or chloride ingress not reduced vs control after 2 winters, fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["spore death", "nutrient exhaustion"],
            "commercial_path": {"buyer": "DOTs"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:nm10:r1", "title": "Self-healing bacterial concrete: measured healing of 0.1-0.5 mm cracks (0.8 mm optimized lab), latency weeks at 20 C and months below 10 C, 2-3 repeat healing events before exhaustion; long-term spore viability beyond years is unproven"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:nm10:pa1", "perspective": "FAILURE", "title": "Field and long-cure trials of bacterial concrete: healing degrades under freeze-thaw and repeated cracking; multi-decade spore viability and repeated healing unverified"}
        ]},
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "engineering/hidden dependency (healing works in the lab but repeat-healing exhaustion (2-3 events) and multi-decade spore viability under freeze-thaw are unproven — the 30-year crack-free claim exceeds demonstrated capability by an order of magnitude in time and repeat cycles)",
            "expected_kill_surface": "engineering",
            "expected_defect_in_basis": ["repeat", "2-3", "viability", "freeze-thaw", "unproven", "30-year"],
            "ground_truth_basis": "MICP healing is real and measured (0.1-0.5 mm, weeks of latency at 20 C), but demonstrated repeat healing is 2-3 events with months-long latency below 10 C, and multi-decade spore viability in freeze-thaw/de-icing environments is unproven. The 30-year maintenance-free claim is an order beyond demonstrated durability. A calibrated attacker should KILL on the engineering/durability gap."
        }
    },
]

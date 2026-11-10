"""R412 Phase 3 — attacker-calibration corpus, Quadrant 2: KNOWN_BAD.

Authored independently of the attacker (Art. VIII). Each case carries a
genuine defect from the Art. L minimum defect-class list; the ground
truth (defect class + why the attacker must kill) is established BEFORE
the attacker sees the case.
"""

KB_CASES = [
    {
        "case_id": "CAL-KB-01",
        "domain_id": "hvac_chiller",
        "pain_class": "ENERGY_CONVERSION_LOSS",
        "candidate": {
            "candidate_id": "CAL-KB-01",
            "technology_name": "Passive Radiative Night Panel That Cools Below Ambient in Full Sun",
            "problem": "Chiller condensers in hot climates reject heat at high ambient temperature; cooling below ambient during the day would raise chiller COP",
            "causal_chain": [
                "Special coating emits strongly in the 8-13 micron atmospheric window",
                "net radiative loss to deep sky occurs",
                "panel fluid cools to 5-8 C BELOW daytime ambient air temperature",
                "chiller condenser water is pre-cooled below ambient",
                "chiller COP rises by 25-40%"
            ],
            "unexploited_phenomenon": "Radiative sky cooling in the atmospheric window (cal:kb01:r1)",
            "intervention": "Install radiative cooling panels over chiller condenser water loops claiming sub-ambient fluid temperature under direct daytime sunlight with a simple static coating",
            "governing_variables": "Coating emissivity, atmospheric window transmittance, solar absorption, convective gain",
            "predicted_effect": "Condenser water 5-8 C below daytime ambient air temperature in full sun; chiller COP +25-40%",
            "equations": [
                "Q_net = epsilon_window*sigma*(T_panel^4 - T_sky^4) - alpha_solar*S - h_conv*(T_air - T_panel)",
                "T_panel_min solves Q_net = 0"
            ],
            "boundary_conditions": "Claims to work under direct midday sun with 900 W/m2 solar load using only a static coating",
            "evidence_refs": ["cal:kb01:r1"],
            "baseline": {
                "baseline_incumbent": "Air-cooled condenser at ambient temperature",
                "baseline_metric": "Condenser approach 8-12 C above ambient",
                "candidate_metric": "Condenser water 5-8 C BELOW ambient in full sun"
            },
            "killer_experiment": {
                "experiment": "Mount panel in full midday sun, measure fluid temperature vs ambient with calibrated RTDs",
                "kill_condition": "If panel does not hold 3 C below ambient at 900 W/m2 solar load, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["condensation", "dust on coating"],
            "commercial_path": {"buyer": "Chiller plant operators"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb01:r1", "title": "Nighttime radiative sky cooling: measured sub-ambient temperatures achievable only under clear night sky with solar load absent"},
            {"record_id": "cal:kb01:r2", "title": "Daytime radiative cooling demonstrations requiring photonic metamaterials with solar reflectance > 96% and complex multilayer stacks"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb01:pa1", "perspective": "MECHANISM", "title": "Radiative cooling physics: achievable sub-ambient depth scales with solar absorption and convection gain; static conventional coatings cannot reach daytime sub-ambient"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "physics (second-law / energy-balance violation at stated conditions)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["solar", "energy balance", "absorption", "convection", "daytime", "900 W/m2", "static coating"],
            "ground_truth_basis": "The energy balance kills it: with a static (non-photonic) coating the ~5-20% solar absorption under 900 W/m2 midday load vastly exceeds the 40-100 W/m2 achievable window emission, so the panel runs ABOVE ambient in full sun. Daytime sub-ambient requires solar reflectance >96% photonic structures, which the candidate explicitly does not claim. The cited evidence record itself says sub-ambient is a NIGHTTIME result — the candidate misquotes its own source. A calibrated attacker must KILL on physics (energy balance) and/or evidence (record does not support the daytime claim)."
        }
    },
    {
        "case_id": "CAL-KB-02",
        "domain_id": "industrial_pumps",
        "pain_class": "ENERGY_CONVERSION_LOSS",
        "candidate": {
            "candidate_id": "CAL-KB-02",
            "technology_name": "Static Magnetic Water Conditioner Eliminating Scale Without Chemicals",
            "problem": "Cooling-tower and boiler circuits accumulate mineral scale, costing chemical treatment and efficiency loss",
            "causal_chain": [
                "Permanent magnets strap around the pipe",
                "static magnetic field polarizes dissolved Ca2+ and CO3-- ions",
                "ions reorganize into non-adhering aragonite form",
                "scale stops forming on heat-transfer surfaces",
                "chemical treatment is eliminated"
            ],
            "unexploited_phenomenon": "Claimed magnetic-induced aragonite polymorph selection (cal:kb02:r1)",
            "intervention": "Clamp-on NdFeB magnet array on the make-up water line, no power, no chemicals, claimed 90% scale elimination",
            "governing_variables": "Field strength (T), flow velocity, water hardness, ion hydration state",
            "predicted_effect": "90% reduction in scale deposition; chemical treatment cost eliminated; 3% efficiency gain",
            "equations": [
                "E_ion ~ kT, magnetic interaction energy ~ mu_ion*B ~ 1e-26 J at 0.5 T — ratio ~ 1e-6 of thermal energy"
            ],
            "boundary_conditions": "Claims effect at pipe-scale field strengths with no flow-through device",
            "evidence_refs": ["cal:kb02:r1"],
            "baseline": {
                "baseline_incumbent": "Chemical scale inhibitors and periodic acid cleaning",
                "baseline_metric": "Chemical cost + 2% efficiency loss from scale",
                "candidate_metric": "Zero chemical; claimed 90% scale elimination"
            },
            "killer_experiment": {
                "experiment": "Side-by-side heat exchanger fouling test with and without magnets on hard water",
                "kill_condition": "If fouling resistance curves diverge less than 20%, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["none claimed"],
            "commercial_path": {"buyer": "Facility managers"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb02:r1", "title": "Magnetic water treatment: systematic controlled studies find no reproducible scale-reduction effect at permanent-magnet field strengths; proposed ion-interaction energies are 1e-6 of thermal energy"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb02:pa1", "perspective": "FAILURE", "title": "Negative controlled trials of magnetic water conditioners across hardness regimes: no effect beyond noise"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "causal-invalidity (magnetic energy at field strength is ~1e-6 of kT; no causal path)",
            "expected_kill_surface": "mechanism",
            "expected_defect_in_basis": ["energy", "kT", "ion", "hydration", "no mechanism", "controlled studies", "1e-6"],
            "ground_truth_basis": "Causal invalidity: the magnetic interaction energy of hydrated ions at 0.1-1 T is about a millionth of thermal energy, and the ions' hydration shells screen fields further — there is no physical path to polymorph selection at these strengths. The controlled-trial literature (also provided) finds no reproducible effect. A calibrated attacker must KILL on mechanism."
        }
    },
    {
        "case_id": "CAL-KB-03",
        "domain_id": "power_electronics",
        "pain_class": "EFFICIENCY",
        "candidate": {
            "candidate_id": "CAL-KB-03",
            "technology_name": "Resonant Converter Claiming 99.5% Efficiency at 3 kW",
            "problem": "Server PSU conversion losses at 3 kW are 40-60 W; halving them would save data center energy",
            "causal_chain": [
                "ZVS resonant topology eliminates switching loss",
                "planar magnetics reduce core loss",
                "GaN FETs reduce conduction loss",
                "total conversion efficiency reaches 99.5% at 3 kW",
                "PSU losses fall from 60 W to 15 W"
            ],
            "unexploited_phenomenon": "Zero-voltage switching (cal:kb03:r1)",
            "intervention": "3 kW LLC resonant DC-DC stage, GaN, planar magnetics, claims 99.5% peak efficiency",
            "governing_variables": "Switching frequency, dead time, Rds(on), core material, synchronous rectification",
            "predicted_effect": "99.5% conversion efficiency at 3 kW (15 W total loss)",
            "equations": [
                "P_loss = P_cond + P_sw + P_core + P_aux; each minimized by topology and material claims"
            ],
            "boundary_conditions": "Claims 99.5% at full 3 kW load, 400 V to 48 V conversion",
            "evidence_refs": ["cal:kb03:r1"],
            "baseline": {
                "baseline_incumbent": "Best-in-class titanium PSU at 96.5% peak",
                "baseline_metric": "96.5% at 3 kW (105 W loss)",
                "candidate_metric": "99.5% at 3 kW (15 W loss)"
            },
            "killer_experiment": {
                "experiment": "Calorimetric loss measurement at 3 kW",
                "kill_condition": "If measured efficiency below 99%, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["none claimed"],
            "commercial_path": {"buyer": "PSU OEMs"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb03:r1", "title": "Best measured 3 kW-class server PSU efficiencies: 96-97% peak with GaN and ZVS; remaining loss floors from winding AC resistance, core, and synchronous-rectifier body diode conduction"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb03:pa1", "perspective": "MECHANISM", "title": "Physical loss floors in high-frequency 3 kW converters: AC winding resistance and core loss bounds on achievable efficiency"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "physics (loss-floor arithmetic: 99.5% at 3 kW implies 15 W total, below the measured physical floors of the constituent components)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["loss floor", "winding", "core", "AC resistance", "arithmetic", "15 W", "body diode"],
            "ground_truth_basis": "The claim's arithmetic breaks against component physics: at 3 kW and 400/48 V, planar-magnet winding AC losses, core losses, and synchronous rectification losses each individually exceed several watts at any practical switching frequency; the best MEASURED 3 kW units sit at 96-97% (the cited record says exactly this). 99.5% implies ~15 W total — below the sum of physical floors. Baseline-equivalence-adjacent but fundamentally a physics/arithmetic violation. A calibrated attacker must KILL."
        }
    },
    {
        "case_id": "CAL-KB-04",
        "domain_id": "marine",
        "pain_class": "CORROSION",
        "candidate": {
            "candidate_id": "CAL-KB-04",
            "technology_name": "Seawater Aluminum Anode With Claimed 10-Year Life in Ballast Tanks",
            "problem": "Ballast tank corrosion protection anodes need replacement at every 5-year docking; longer intervals save dockings",
            "causal_chain": [
                "High-purity aluminum anode with special alloying",
                "claimed drastically reduced self-corrosion",
                "anode consumption rate falls 8x",
                "same anode mass lasts 40 years; sized for 10",
                "docking-interval corrosion work eliminated"
            ],
            "unexploited_phenomenon": "Claimed activation-control alloying (cal:kb04:r1)",
            "intervention": "Al-Zn-In class anode with claimed 8x life extension in seawater ballast service",
            "governing_variables": "Alloy composition, current capacity (Ah/kg), utilization factor, anode mass",
            "predicted_effect": "Anode life 10 years at constant protection current density (8x conventional)",
            "equations": [
                "Life = M_anode * utilization * capacity (Ah/kg) / I_required — claim requires capacity x8 or I x1/8 with same mass"
            ],
            "boundary_conditions": "Same tank, same coating quality, same impressed current absence",
            "evidence_refs": ["cal:kb04:r1"],
            "baseline": {
                "baseline_incumbent": "Standard Al-Zn-In anode, 2.5-5 year life",
                "baseline_metric": "2.5-5 years per docking cycle",
                "candidate_metric": "10+ years claimed"
            },
            "killer_experiment": {
                "experiment": "Field exposure of instrumented anode pairs in a working ballast tank for 3 years, weigh and measure capacity",
                "kill_condition": "If consumption rate not reduced at least 5x, fails",
                "cost_class": "FIELD"
            },
            "failure_modes": ["passivation"],
            "commercial_path": {"buyer": "Ship operators"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb04:r1", "title": "Aluminum sacrificial anode electrochemistry: measured capacity 2,500-2,900 Ah/kg is an intrinsic Faradaic limit; alloying changes efficiency 0.90-0.98 but not the Faradaic capacity by multiples"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb04:pa1", "perspective": "MECHANISM", "title": "Faraday's law for anode consumption: capacity in Ah/kg is fixed by electrochemical equivalence; life extension requires mass, not metallurgy"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "physics (Faradaic capacity limit — anode life cannot extend 8x at constant current and mass)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["Faraday", "capacity", "Ah/kg", "mass", "electrochemical equivalence", "2,500"],
            "ground_truth_basis": "The claimed 8x life at constant protection current and constant mass violates Faraday's law: the Al anode's electrochemical capacity (~2,500-2,900 Ah/kg, an intrinsic Faradaic quantity) fixes consumption; alloying moves efficiency a few percent, never 8x. The cited record states the limit. A calibrated attacker must KILL on physics."
        }
    },
    {
        "case_id": "CAL-KB-05",
        "domain_id": "batteries_ev",
        "pain_class": "THERMAL_LOSS",
        "candidate": {
            "candidate_id": "CAL-KB-05",
            "technology_name": "Battery Pack 10x Thermal Runaway Propagation Delay via Thin Ceramic Coating Alone",
            "problem": "EV pack thermal runaway cell-to-cell propagation is the main fire safety concern; delaying it 10x improves occupant escape time",
            "causal_chain": [
                "0.1 mm ceramic coating on cell cans",
                "thermal runaway ejecta heat flux partially blocked",
                "propagation delay claimed 10x",
                "escape window extends from 5 to 50 minutes",
                "pack-level fire safety rating improves without redesign"
            ],
            "unexploited_phenomenon": "Ceramic thermal barrier on cell cans (cal:kb05:r1)",
            "intervention": "Coat cylindrical 21700 cell cans with 0.1 mm alumina; claim 10x propagation delay at pack level with NO other changes",
            "governing_variables": "Coating thickness, ejecta heat flux (W/cm2), cell spacing, venting design",
            "predicted_effect": "10x delay in cell-to-cell propagation; pack escape time from 5 to 50 minutes",
            "equations": [
                "t_delay ~ rho*c*delta_T*thickness / q''_ejecta — with 0.1 mm alumina and q'' ~ 10-100 W/cm2 the added thermal mass is ~0.1-1 s, not minutes"
            ],
            "boundary_conditions": "No changes to spacing, venting, busbar fusing, or pack structure",
            "evidence_refs": ["cal:kb05:r1"],
            "baseline": {
                "baseline_incumbent": "Bare cell cans with standard spacing",
                "baseline_metric": "Propagation delay seconds to minutes",
                "candidate_metric": "Claimed 10x (minutes to tens of minutes)"
            },
            "killer_experiment": {
                "experiment": "Nail-penetration propagation test on coated vs uncoated cell pairs",
                "kill_condition": "If delay factor < 2x, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["coating adhesion"],
            "commercial_path": {"buyer": "EV OEMs"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb05:r1", "title": "Cell-to-cell thermal runaway propagation: measured ejecta heat fluxes 10-100 W/cm2 and propagation timescales set by adjacent cell heating to onset; thin-coating thermal mass adds sub-second delay only"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb05:pa1", "perspective": "FAILURE", "title": "Coating-only mitigation trials: meaningful propagation delay requires spacing, interstitial barriers, and vent redirection together"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "physics (magnitude arithmetic: 0.1 mm alumina thermal mass adds ~0.1-1 s against minute-scale requirement — 3+ orders short)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["thermal mass", "0.1 mm", "heat flux", "seconds", "arithmetic", "orders of magnitude"],
            "ground_truth_basis": "Magnitude arithmetic: the sensible heat of 0.1 mm alumina over a cell can is absorbed in well under a second by runaway ejecta flux; a 10x minute-scale delay requires either large interstitial thermal mass or spacing/venting redesign. The claimed effect is 3+ orders of magnitude beyond the coating's physics. A calibrated attacker must KILL on physics."
        }
    },
    {
        "case_id": "CAL-KB-06",
        "domain_id": "carbon_capture",
        "pain_class": "ENERGY_CONVERSION_LOSS",
        "candidate": {
            "candidate_id": "CAL-KB-06",
            "technology_name": "Ambient-Air CO2 Capture Claiming Net Energy Surplus",
            "problem": "Direct air capture spends 1,500-2,500 kWh/tCO2; a process that captures CO2 while producing net energy would transform economics",
            "causal_chain": [
                "sorbent captures CO2 from ambient air",
                "captured CO2 reacted with a mineral to form carbonate",
                "carbonation heat is claimed to exceed the regeneration and fan energy",
                "the process exports net power while capturing CO2",
                "negative-cost carbon removal"
            ],
            "unexploited_phenomenon": "Exothermic carbonation of CO2 with Ca/Mg minerals (cal:kb06:r1)",
            "intervention": "Sorbent loop + mineral carbonation reactor claimed to export 100-300 kWh net per tCO2 captured from 420 ppm air",
            "governing_variables": "Sorbent regeneration energy (GJ/t), carbonation enthalpy (GJ/t), fan power, cycle temperatures",
            "predicted_effect": "Net energy export 100-300 kWh per tonne CO2 captured from ambient air",
            "equations": [
                "E_net = E_carbonation - E_regeneration - E_fans; claim asserts E_net > 0",
                "Minimum separation work at 420 ppm: ~ 500 kWh/tCO2 (thermodynamic bound)"
            ],
            "boundary_conditions": "Claims NET positive energy while capturing from 420 ppm",
            "evidence_refs": ["cal:kb06:r1"],
            "baseline": {
                "baseline_incumbent": "Conventional DAC at 1,500-2,500 kWh/t net input",
                "baseline_metric": "Net energy input 1,500-2,500 kWh/t",
                "candidate_metric": "Net energy OUTPUT 100-300 kWh/t"
            },
            "killer_experiment": {
                "experiment": "Full-loop energy audit with metered inputs/outputs at steady state",
                "kill_condition": "If net energy negative, fails",
                "cost_class": "PILOT"
            },
            "failure_modes": ["sorbent degradation"],
            "commercial_path": {"buyer": "Carbon removal buyers"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb06:r1", "title": "Thermodynamics of CO2 capture from air: minimum separation work ~500 kWh/t at 420 ppm; carbonation enthalpy (~1.8 GJ/t) cannot be recovered above regeneration temperature with net surplus"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb06:pa1", "perspective": "MECHANISM", "title": "Second-law analysis of DAC energy budgets: no known sorbent-mineral loop exports net energy"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "physics (second-law violation: net energy export while separating CO2 from 420 ppm exceeds available enthalpy)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["second law", "minimum work", "500 kWh", "enthalpy", "exergy", "420 ppm"],
            "ground_truth_basis": "Second-law arithmetic: minimum work to separate CO2 from 420 ppm air is ~500 kWh/t; real sorbent regeneration and fans cost 1,500-2,500 kWh/t; the ~1.8 GJ/t carbonation enthalpy is low-grade heat largely below regeneration temperature (exergy-poor). Net EXPORT while capturing from air is thermodynamically impossible for this loop class. A calibrated attacker must KILL on physics."
        }
    },
    {
        "case_id": "CAL-KB-07",
        "domain_id": "semiconductor_fab",
        "pain_class": "YIELD",
        "candidate": {
            "candidate_id": "CAL-KB-07",
            "technology_name": "Statio-Litho Overlay Control From a Single Wafer Metric",
            "problem": "Scanner-to-scanner overlay drift causes yield loss; a cheap single-metric controller would replace metrology-heavy feedback",
            "causal_chain": [
                "single inline focus metric per wafer is measured",
                "the metric is assumed to encode overlay error",
                "controller corrects scanner baselines from the single metric",
                "overlay improves without dedicated overlay metrology",
                "yield recovers and metrology cost falls"
            ],
            "unexploited_phenomenon": "Claimed single-metric observability (cal:kb07:r1)",
            "intervention": "Feed one focus metric into an SPC chart to steer overlay corrections without overlay metrology",
            "governing_variables": "Focus metric sensitivity, overlay process dominants (Z expansion, wafer mapping, lens heating)",
            "predicted_effect": "30-50% reduction in overlay excursions with zero added metrology",
            "equations": [
                "overlay_error = sum(beta_i * factor_i) — one scalar observation cannot identify the multiple independent drift factors"
            ],
            "boundary_conditions": "None stated",
            "evidence_refs": ["cal:kb07:r1"],
            "baseline": {
                "baseline_incumbent": "Dedicated overlay metrology + APC on lot basis",
                "baseline_metric": "Overlay excursion rate baseline",
                "candidate_metric": "30-50% reduction claimed"
            },
            "killer_experiment": {
                "experiment": "A/B the single-metric controller vs dedicated overlay metrology for excursion rate over 2000 wafers",
                "kill_condition": "If excursion rate not reduced 20%, fails",
                "cost_class": "PILOT"
            },
            "failure_modes": ["none claimed"],
            "commercial_path": {"buyer": "Fab operators"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb07:r1", "title": "Overlay process control: measured overlay error decomposes into several independent drift factors (stage Z, wafer mapping, lens heating) requiring multi-channel metrology for identifiability"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb07:pa1", "perspective": "FAILURE", "title": "Single-sensor control of multi-factor overlay: observability failures documented when independent factors alias into one metric"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "measurement-ambiguity / identifiability (one scalar cannot identify multiple independent overlay drift factors)",
            "expected_kill_surface": "mechanism",
            "expected_defect_in_basis": ["identifiability", "observability", "multiple factors", "alias", "one metric", "degrees of freedom"],
            "ground_truth_basis": "Identifiability: a single scalar focus metric cannot disambiguate the several independent overlay drift factors (stage Z, wafer mapping, lens heating); corrections from an aliased observation amplify some factors while correcting others. The cited record and prior-art analysis both state the multi-channel requirement. A calibrated attacker must KILL on mechanism/observability."
        }
    },
    {
        "case_id": "CAL-KB-08",
        "domain_id": "wind",
        "pain_class": "MATERIAL_DEGRADATION",
        "candidate": {
            "candidate_id": "CAL-KB-08",
            "technology_name": "Blade Leading-Edge Self-Healing Coating Claiming Full Field Recovery Overnight",
            "problem": "Blade LE erosion reduces AEP 1-3% and needs re-coating every 3-5 years",
            "causal_chain": [
                "Microcapsule self-healing coating on LE",
                "erosion ruptures capsules",
                "healing agent fills the crater",
                "overnight self-healing at ambient conditions restores the surface",
                "re-coating cycles are eliminated"
            ],
            "unexploited_phenomenon": "Microcapsule self-healing polymers (cal:kb08:r1)",
            "intervention": "Two-part microcapsule coating claimed to fully heal rain-erosion craters (0.1-1 mm) overnight at ambient temperature, eliminating LE re-coating for the blade life",
            "governing_variables": "Capsule density, healing agent kinetics, crater volume, ambient temperature",
            "predicted_effect": "Full overnight recovery of 0.1-1 mm erosion craters at 5-25 C ambient; AEP loss held at 0%; re-coating eliminated for 20-year blade life",
            "equations": [
                "V_heal = n_capsules_broken * V_agent; healing 1 mm crater requires agent volumes comparable to crater volume — capsule densities needed exceed film integrity limits"
            ],
            "boundary_conditions": "Claims full heal of mm-scale craters at ambient temperature overnight",
            "evidence_refs": ["cal:kb08:r1"],
            "baseline": {
                "baseline_incumbent": "Polyurethane LE tapes / coatings replaced at 3-5 year intervals",
                "baseline_metric": "AEP loss 1-3%; re-coat every 3-5 years",
                "candidate_metric": "AEP loss 0%; no re-coat for 20 years"
            },
            "killer_experiment": {
                "experiment": "Rain-erosion rig to controlled 1 mm damage, then 12 h ambient heal, re-test profile",
                "kill_condition": "If surface profile not restored to 80%, fails",
                "cost_class": "BENCH"
            },
            "failure_modes": ["UV degradation of agent"],
            "commercial_path": {"buyer": "Wind farm operators"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb08:r1", "title": "Microcapsule self-healing coatings: measured healing is effective for micro-scale scratches (tens of microns); capsule volume fraction limits total healable damage to ~1-5% of film volume, far below mm-scale erosion craters"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb08:pa1", "perspective": "FAILURE", "title": "Self-healing coating field trials on wind blades: micro-scale crack healing confirmed, mm-scale rain erosion beyond healing capacity"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "scaling failure (micro-scale healing mechanism applied to mm-scale damage; healable volume fraction is orders short)",
            "expected_kill_surface": "physics",
            "expected_defect_in_basis": ["volume", "capsule", "micron", "mm", "scaling", "fraction", "orders"],
            "ground_truth_basis": "Scaling: microcapsule healing is proven for tens-of-microns scratches; total healable volume is bounded by capsule volume fraction (~1-5% of film). Rain-erosion craters at 0.1-1 mm exceed healable volume by 2-3 orders of magnitude, and ambient-temperature overnight kinetics are far slower than blade-repair PU. The cited record and prior-art field trials state the mismatch. A calibrated attacker must KILL on scaling/physics."
        }
    },
    {
        "case_id": "CAL-KB-09",
        "domain_id": "machining",
        "pain_class": "TOOL_WEAR",
        "candidate": {
            "candidate_id": "CAL-KB-09",
            "technology_name": "Cryogenic Tool Life Extension x10 in Steel Milling",
            "problem": "Carbide tool wear drives tooling and downtime cost in steel milling",
            "causal_chain": [
                "LN2 delivered through the spindle to the tool tip",
                "cutting zone temperature falls below 50 C",
                "diffusion and oxidation wear mechanisms nearly stop",
                "tool life extends 10x",
                "tooling cost per part falls 85%"
            ],
            "unexploited_phenomenon": "Cryogenic cooling suppresses diffusion wear (cal:kb09:r1)",
            "intervention": "Through-spindle LN2 at 30 L/h claimed to extend carbide tool life 10x in continuous steel milling at production feeds/speeds",
            "governing_variables": "LN2 flow (L/h), cutting speed (m/min), depth of cut, insert grade, chip evacuation",
            "predicted_effect": "10x tool life at production metal-removal rates",
            "equations": [
                "Taylor tool life: V*T^n = C; cooling lowers effective V-equivalent wear rate — 10x requires wear-rate suppression well beyond measured cryogenic results"
            ],
            "boundary_conditions": "Claims 10x at full production feeds/speeds in continuous milling",
            "evidence_refs": ["cal:kb09:r1"],
            "baseline": {
                "baseline_incumbent": "Flood coolant carbide milling",
                "baseline_metric": "Tool life T baseline (20-60 min class)",
                "candidate_metric": "10x T (200-600 min class)"
            },
            "killer_experiment": {
                "experiment": "ISO tool-life test flood vs LN2 at production parameters",
                "kill_condition": "If life extension < 3x, fails",
                "cost_class": "LAB"
            },
            "failure_modes": ["thermal cracking of inserts from extreme gradients"],
            "commercial_path": {"buyer": "Machining shops"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb09:r1", "title": "Cryogenic machining measured results: tool life gains of 1.3-2.5x typical for carbide in steels; 10x not observed; extreme gradients introduce thermal-cracking wear mode"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb09:pa1", "perspective": "MECHANISM", "title": "Wear-mode transition under cryogenic cooling: diffusion suppression is partial; mechanical-attrition and thermal-cracking wear persist"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "evidence contradiction (measured cryogenic tool-life gains are 1.3-2.5x; the 10x claim contradicts the cited evidence and ignores the thermal-cracking wear mode it introduces)",
            "expected_kill_surface": "evidence",
            "expected_defect_in_basis": ["measured", "1.3", "2.5x", "thermal cracking", "contradicts", "10x"],
            "ground_truth_basis": "Evidence contradiction: the cited record itself reports measured cryogenic tool-life extensions of 1.3-2.5x with a NEW thermal-cracking wear mode; the 10x claim contradicts its own source while citing it. A calibrated attacker must KILL on evidence (and physics-adjacent wear-mode reasoning)."
        }
    },
    {
        "case_id": "CAL-KB-10",
        "domain_id": "chemical_process",
        "pain_class": "SAFETY",
        "candidate": {
            "candidate_id": "CAL-KB-10",
            "technology_name": "Oxygen-Enriched Combustion Air Retrofit Inside Occupied Boiler Rooms",
            "problem": "Boiler fuel consumption can drop with oxygen-enriched combustion air",
            "causal_chain": [
                "PSA unit enriches combustion air to 28% O2",
                "flame temperature rises",
                "excess air requirement falls",
                "boiler efficiency rises 4-6%",
                "fuel cost falls"
            ],
            "unexploited_phenomenon": "O2-enriched combustion (cal:kb10:r1)",
            "intervention": "Retrofit PSA oxygen enrichment on natural-draft boilers located INSIDE occupied mechanical rooms, with enriched air ducted through standard HVAC ducting and no O2 monitoring",
            "governing_variables": "O2 concentration (28%), duct leakage, room volume, ventilation rate, ignition sources",
            "predicted_effect": "4-6% boiler efficiency gain with no safety hardware changes",
            "equations": [
                "Room O2 rise from 21% toward 24%+ with duct leakage dV/dt into V_room; flammability limits of common materials and clothing shift downward sharply above 23.5% O2"
            ],
            "boundary_conditions": "Occupied room, no O2 monitoring, standard ducting",
            "evidence_refs": ["cal:kb10:r1"],
            "baseline": {
                "baseline_incumbent": "Ambient-air combustion",
                "baseline_metric": "Boiler efficiency 80%",
                "candidate_metric": "84-86% claimed"
            },
            "killer_experiment": {
                "experiment": "Room O2 mapping under leak conditions",
                "kill_condition": "If room O2 stays below 23%, passes",
                "cost_class": "BENCH"
            },
            "failure_modes": ["none claimed"],
            "commercial_path": {"buyer": "Building operators"},
            "cross_domain_transition": "NONE"
        },
        "pool": [
            {"record_id": "cal:kb10:r1", "title": "Oxygen-enriched atmospheres in occupied spaces: 23.5%+ O2 sharply lowers ignition energy and accelerates fire; codes require monitoring and exclusion of occupancy above threshold"}
        ],
        "prior_art": {"relevant_records": [
            {"record_id": "cal:kb10:pa1", "perspective": "FAILURE", "title": "PSA combustion-air enrichment safety analyses: leak scenarios in occupied rooms drive O2 above 23.5% without monitoring; NFPA-class guidance excludes occupancy"}
        ]},
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "safety failure (oxygen-enriched occupied space without monitoring — a fire-safety violation of code-class requirements)",
            "expected_kill_surface": "manufacturability",
            "expected_defect_in_basis": ["23.5", "safety", "fire", "code", "NFPA", "occupied", "monitoring"],
            "ground_truth_basis": "Safety: enriching combustion air inside occupied rooms with standard ducting and no O2 monitoring creates an oxygen-enriched occupied atmosphere (duct leaks drift room O2 above the ~23.5% threshold where ignition energy collapses); codes and the provided safety analyses exclude this configuration. The 4-6% efficiency gain does not matter — the intervention is unsafe as specified. A calibrated attacker must KILL on safety/engineering realization."
        }
    },
]

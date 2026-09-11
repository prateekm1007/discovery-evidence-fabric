#!/usr/bin/env python3
"""scripts/r446_corpus_append.py — appends cases 7-22 to the R446
attacker-calibration corpus (authored first-principles; the corpus is
committed BEFORE any attacker run — the freeze-then-run discipline).

Cases appended here:
  7-9    NEAR_MISS (real effect, fatal magnitude defect — expect KILL
         for the RIGHT reason)
  10-12  SCOPE_CONFLICT (declared-boundary traps — expect SURVIVED)
  13-16  TRUE_NEGATIVE clean controls (expect SURVIVED)
  17-19  EVIDENCE_CONTRADICTED (17/18 refuted — expect KILL bound to
         evidence; 19 supported — expect SURVIVED)
  20-22  MALFORMED_MISSING_EVIDENCE (absence traps — expect NOT-KILL)

Idempotent: re-running does not duplicate cases.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "R446" / "ATTACKER_CALIBRATION" / "CORPUS.json"

EXTRA_CASES = [
    # ------------------------------------------------------------------
    # NEAR-MISS: real effect, fatal magnitude defect (expect KILL with
    # the magnitude markers in the basis)
    # ------------------------------------------------------------------
    {
        "case_id": "cal-07-nearmiss-electrostatic",
        "category": "NEAR_MISS_real_effect_fatal_magnitude",
        "seed_class": None,
        "control": False,
        "candidate": {
            "candidate_id": "cal-07-electrostatic-precipitator",
            "mechanism": "an electrostatic precipitator section charges incoming scale particles and collects them on parallel plates, so particle load reaching the nozzles falls and clogging declines; electrostatic collection is a mature industrial dust-removal technology",
            "intervention": "plate-type electrostatic precipitator spool in the 150 mm supply line (50 kV corona field, 300 mm collection length) ahead of the spray header",
            "predicted_effect": "scale-particle load to the nozzles cut 95 percent; particle-driven clogging events fall from 4.1 per campaign to below 0.2",
            "testable_prediction": "isokinetic particle counts upstream and downstream of the spool show 95 percent removal of particles above 20 microns at design flow",
            "novel_design_variable": "corona field strength versus particle charging efficiency",
            "known_failure_modes": ["plate fouling with slime"],
            "constraint_set": {
                "boundary_conditions": "water conductivity typical of recirculated mill cooling water; full header flow"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "magnitude — electrostatic collection is real (gas-side dust control at 0.5-2 m/s), but in a conductive liquid at the header's ~4.5 m/s flow velocity and 150 mm line, the space-charge screening and collection length needed for 95 percent removal of 20-80 micron particles is tens of meters, not 300 mm; liquid-phase ESP at these scales is orders of magnitude beyond the claimed performance",
            "expected_kill_surface": "MECHANISM_FAILURE",
            "expected_defect_in_basis": ["orders of magnitude", "length", "velocity", "conductiv", "gas", "liquid"],
            "ground_truth_basis": "The physics exists (electrostatic migration), but the claimed 95 percent removal in 300 mm at 4.5 m/s in conductive water is a magnitude-scale violation: liquid-phase space-charge limits make the claimed collection physically unreachable in the proposed envelope. The correct kill cites the orders-of-magnitude gap between gas-phase ESP practice and this liquid-phase application."
        }
    },
    {
        "case_id": "cal-08-nearmiss-catalytic-coating",
        "category": "NEAR_MISS_real_effect_fatal_magnitude",
        "seed_class": None,
        "control": False,
        "candidate": {
            "candidate_id": "cal-08-catalytic-throat-coating",
            "mechanism": "a polymeric scale-inhibitor coating inside the nozzle throats interferes with calcium carbonate nucleation on the wall surface, so adherent scale cannot form; threshold inhibitors (phosphonate-class chemistry) demonstrably slow nucleation in cooling-water service",
            "intervention": "electrostatically applied phosphonate-embedded polymer coating (40 micron layer) on all 120 nozzle throats at each scheduled cleaning",
            "predicted_effect": "adherent scale nucleation in throats suppressed 90 percent; clogging events per campaign fall from 4.1 to below 0.6",
            "testable_prediction": "coated versus uncoated coupon exposure in the recirculated water shows a 90 percent reduction in adherent scale mass after 120 hours",
            "novel_design_variable": "inhibitor loading in the polymer matrix",
            "known_failure_modes": ["coating abrasion by scale fines"],
            "constraint_set": {
                "boundary_conditions": "throat flow at 14 bar, 32-38 C; water residence in each throat approximately 1-2 ms"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "magnitude — threshold inhibition chemistry is real but requires contact times of minutes-to-hours in bulk water at ppm dosing; the water resides in a 3 mm throat for ~1.5 milliseconds, four orders of magnitude too short for surface nucleation kinetics to be affected by a wall coating; the coupon test (hours of immersion) cannot transfer to the in-service timescale",
            "expected_kill_surface": "BOUNDARY_CONDITION_FAILURE",
            "expected_defect_in_basis": ["residence", "milliseconds", "orders of magnitude", "timescale", "contact"],
            "ground_truth_basis": "Nucleation inhibition is time-scale dependent: bulk-water threshold effects need minutes of contact, the throat provides ~1.5 ms. The correct kill exposes the residence-time / kinetics mismatch (the four-orders-of-magnitude gap), which the candidate's own boundary conditions declare."
        }
    },
    {
        "case_id": "cal-09-nearmiss-header-vibration",
        "category": "NEAR_MISS_real_effect_fatal_magnitude",
        "seed_class": None,
        "control": False,
        "candidate": {
            "candidate_id": "cal-09-piezo-header-vibration",
            "mechanism": "continuous low-amplitude vibration of the spray header at 200 Hz prevents particle settling and early deposit consolidation in nozzle inlets; vibration-assisted transport is proven in industrial hoppers and chutes, and deposits never consolidate if the surface never rests",
            "intervention": "two 200 Hz electro-mechanical shakers mounted on the header ends, 12 kW continuous drive, header supported on tuned isolation mounts",
            "predicted_effect": "deposit consolidation in nozzle inlets eliminated; clogging events per campaign fall from 4.1 to below 0.3; no scheduled cleaning needed",
            "testable_prediction": "a bench header section vibrated at 200 Hz versus static shows no deposit consolidation after a 120-hour slurry exposure",
            "novel_design_variable": "vibration amplitude at the nozzle inlets",
            "known_failure_modes": ["shaker bearing wear"],
            "constraint_set": {
                "boundary_conditions": "header rigidly connected to mill frame at the roll-cooling interface; thermal-crown variation must stay inside 12 microns; 14 bar service"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "NEAR_MISS",
            "expected_final": "KILLED",
            "defect_class": "creates a larger failure mode — hopper vibration works on dry granular transport at rest, but a continuously vibrating header rigidly coupled to the mill frame transmits 200 Hz into the roll-gap environment: the strip-gauge and thermal-crown tolerance (12 microns) cannot survive continuous header vibration, weld-fatigue life at the nozzle seats collapses, and 12 kW continuous drive exceeds the mill's auxiliary budget for a water-spray problem",
            "expected_kill_surface": "MECHANISM_FAILURE",
            "expected_defect_in_basis": ["vibration", "roll gap", "12 micron", "fatigue", "gauge", "tolerance"],
            "ground_truth_basis": "The anti-settling effect is real but the intervention destroys the constraint it must preserve: continuous 200 Hz header vibration is incompatible with the declared 12-micron crown band and roll-gap stability, and weld fatigue at the nozzle seats becomes the dominant failure mode. The correct kill cites the constraint violation (the problem's own bound), not a fabricated impossibility."
        }
    },
    # ------------------------------------------------------------------
    # SCOPE-CONFLICT: declared-boundary traps (expect SURVIVED — a kill
    # here is a SCOPE_MISMATCH false kill)
    # ------------------------------------------------------------------
    {
        "case_id": "cal-10-scope-scale-only-filtration",
        "category": "SCOPE_CONFLICT_declared_boundary_trap",
        "seed_class": None,
        "control": False,
        "candidate": {
            "candidate_id": "cal-10-scale-scoped-cascade",
            "mechanism": "a two-stage wedge-wire cascade (300 then 120 micron) on the header supply removes scale particles above 120 microns before they reach the nozzles, with dP-triggered automatic backflush keeping the cascade in service without mill stops; the intervention explicitly targets SCALE-PARTICLE clogging only — biofilm clogging is declared OUT OF SCOPE and remains handled by the mill's existing biocide program",
            "intervention": "two-stage wedge-wire cascade with dP transmitters and automatic backflush valves on the 150 mm header supply, sized for full design flow",
            "predicted_effect": "scale-particle-driven clogging events (the 12 percent of measured blockages that are pure scale above 200 microns, plus bridging nuclei) reduced 8x; total campaign clogging events fall from 4.1 to approximately 3.3 (the biofilm share unchanged); the declared scope is partial and stated honestly",
            "testable_prediction": "removed-nozzle analysis over two campaigns shows scale-particle blockages reduced 8x while biofilm blockage counts are statistically unchanged; the partial effect is the declared scope",
            "novel_design_variable": "second-stage micron rating versus bridging nucleus size",
            "known_failure_modes": ["backflush valve jam (maintained spares held)"],
            "constraint_set": {
                "boundary_conditions": "scale-particle clogging only, above 120 microns; biofilm clogging explicitly out of scope (existing biocide program continues); 13-15 bar supply; no mill stop for installation (flanged spool swap during planned roll change)"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD_WITH_DECLARED_SCOPE",
            "expected_final": "SURVIVED",
            "defect_class": "none — a sound, honestly-scoped intervention: the mechanism is standard filtration physics, the prediction is quantified with instruments and bands, the partial effect is declared (12 percent pure-scale share addressed), and the out-of-scope failure mode is disclosed and covered by an existing system. An attacker demanding full biofilm coverage kills via SCOPE_MISMATCH (demanding content the candidate's contract explicitly does not carry — the R445 diagnosis class)",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "The candidate's scope declaration is honest and the declared effect is achievable by standard means. Objections of the form 'does not address biofilm' are scope-mismatch objections: the biofilm axis is explicitly out of the declared boundary and handled by the existing program. The correct verdict is SURVIVED (at most a RISK note on the partial coverage)."
        }
    },
    {
        "case_id": "cal-11-scope-temperature-bounded-boost",
        "category": "SCOPE_CONFLICT_declared_boundary_trap",
        "seed_class": None,
        "control": False,
        "candidate": {
            "candidate_id": "cal-11-bounded-flow-boost",
            "mechanism": "raising header flow 20 percent using existing pump headroom increases convective flushing velocity through each nozzle throat, raising the particle size that can be transported through without settling; the intervention is declared valid ONLY for campaigns with strip entry temperature below 85 C (the pump curve and thermal balance at higher entry temperatures exceed the declared envelope)",
            "intervention": "supply valve setpoint change plus a strip-entry-temperature interlock that reverts flow to nominal above 85 C; no hardware change",
            "predicted_effect": "for in-envelope campaigns (about 70 percent of the mill's campaign mix), clogging events fall from 4.1 to approximately 2.8 and crown excursions shrink; out-of-envelope campaigns revert to baseline behavior honestly",
            "testable_prediction": "in-envelope campaigns measure a clogging-event reduction to approximately 2.8 with 95 percent confidence band 2.4-3.2; out-of-envelope campaigns measure no significant change from 4.1",
            "novel_design_variable": "flow boost fraction versus throat transport velocity",
            "known_failure_modes": ["higher flow increases abrasive wear on throat edges (measured wear budget recalculated and inside the roll-change interval)"],
            "constraint_set": {
                "boundary_conditions": "strip entry temperature below 85 C only; header pressure stays 13-15 bar; pump headroom of 22 percent exists per pump curve; out-of-envelope reversion is automatic"
              }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD_WITH_DECLARED_SCOPE",
            "expected_final": "SURVIVED",
            "defect_class": "none — a bounded operational change with an explicit temperature envelope, an automatic out-of-envelope reversion, quantified in-envelope effect with confidence band, and honestly-declared wear trade-off. An attacker demanding performance at 95 C entry temperature or calling the 85 C envelope a defect kills via SCOPE_MISMATCH — the candidate's own boundary excludes that regime",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "The candidate does what it declares inside its envelope and reverts honestly outside it. Objections demanding full-envelope performance are out-of-scope demands (the R445 SCOPE_MISMATCH class). The correct verdict is SURVIVED."
        }
    },
    {
        "case_id": "cal-12-scope-redundancy-manifold",
        "category": "SCOPE_CONFLICT_declared_boundary_trap",
        "seed_class": None,
        "control": False,
        "candidate": {
            "candidate_id": "cal-12-standby-nozzle-manifold",
            "mechanism": "each nozzle position carries a standby twin on a dual-manifold block; a per-position dP sensor detects throat bridging and a fast three-way valve shifts that position to the standby twin within 0.4 seconds; the roll's measured thermal inertia carries the flow through the 0.4 s switchover transient with a computed crown perturbation of 1.1 microns (inside the 12 micron band with margin)",
            "intervention": "dual-manifold nozzle blocks with per-position dP sensing and fast-redundancy valves, phased in over three planned roll changes (no mill stop)",
            "predicted_effect": "clogging events reaching the strip fall to zero (every bridge is bypassed in-service); cleaning consolidates into the annual overhaul; crown variation stays inside the 12 micron band including the switchover transients",
            "testable_prediction": "injected partial blockages during a production campaign are bypassed within 0.4 s each, with measured crown perturbation below 2 microns per event and cumulative below 4 microns per campaign",
            "novel_design_variable": "standby valve actuation time versus roll thermal inertia budget",
            "known_failure_modes": ["three-way valve sticking (position-redundant sensors cross-check)"],
            "constraint_set": {
                "boundary_conditions": "13-15 bar; 32-38 C water; the 0.4 s transient budget is inside the measured roll thermal-inertia limit; one standby per position (a simultaneous double failure is out of scope, handled by the scheduled cleaning floor)"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD_WITH_DECLARED_SCOPE",
            "expected_final": "SURVIVED",
            "defect_class": "none — a sound redundancy design with a computed transient budget inside the declared crown band, an honest out-of-scope double-failure declaration, and a phased no-mill-stop installation. An attacker demanding 'zero crown perturbation during switchover' or simultaneous-failure coverage kills via SCOPE_MISMATCH (demanding performance outside the declared budget)",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "The transient is quantified (1.1 microns vs the 12 micron band) and the double-failure regime is explicitly excluded with a fallback. Objections escalating the declared 0.4 s transient to a kill ignore the computed thermal-inertia budget — the R445 SEVERITY_INFLATION/SCOPE_MISMATCH pattern. The correct verdict is SURVIVED."
        }
    },
    # ------------------------------------------------------------------
    # TRUE NEGATIVE clean controls (expect SURVIVED)
    # ------------------------------------------------------------------
    {
        "case_id": "cal-13-clean-staged-cascade",
        "category": "TRUE_NEGATIVE_clean_control",
        "seed_class": None,
        "control": True,
        "candidate": {
            "candidate_id": "cal-13-staged-cascade-backflush",
            "mechanism": "a two-stage inertial wedge-wire cascade (300 then 120 micron) on the header supply removes scale particles and aggregate nuclei above 120 microns; dP transmitters on both stages trigger an automatic backflush (reverse-flow + mechanical brush) that restores full flow without mill stop; combined with the mill's existing biocide program, both clogging axes are addressed at their measured sources",
            "intervention": "two-stage wedge-wire cascade + dP monitoring + automatic backflush valves on the 150 mm supply, installed as a flanged spool swap during a planned roll change",
            "predicted_effect": "campaign clogging events fall from 4.1 to below 1.5 (scale-nucleus share suppressed 8x, biofilm share carried by the existing biocide program); late-campaign crown excursions fall from 28 to below 16 microns; roll-change cleaning time drops to 15 minutes",
            "testable_prediction": "two-campaign split trial: cascade-in-service arm measures clogging events 1.5 or below with 95 percent confidence band 1.0-2.0, versus the baseline arm at 4.1 plus or minus 0.6; dP-triggered backflush events logged per stage; crown variation measured by the mill's existing roll-thermography system",
            "novel_design_variable": "second-stage micron rating and backflush dP threshold",
            "known_failure_modes": ["backflush valve jam (maintained spare held at the mill)", "fine-passive slimes crossing both stages (addressed by the biocide program, measured share 18 percent)"],
            "constraint_set": {
                "boundary_conditions": "13-15 bar supply; full design flow; recirculated water with scale particles present; no mill stop for installation or operation"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": "none — a sound control: standard filtration physics, quantified prediction with instruments, confidence band and baseline comparison, honest failure modes including the residual slime share, effect beats the baseline on the problem quantities within the declared constraints",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "Quantified prediction with instrument and acceptance band; physics consistent with the regime (inertial screening at the cascade's channel Reynolds numbers); predicted effect beats the baseline on every problem quantity; constraints honored (no mill stop, pressure band held)."
        }
    },
    {
        "case_id": "cal-14-clean-cyclonic-return",
        "category": "TRUE_NEGATIVE_clean_control",
        "seed_class": None,
        "control": True,
        "candidate": {
            "candidate_id": "cal-14-cyclonic-preseparator",
            "mechanism": "a hydrocyclone pre-separator on the recirculation RETURN line (before the cooling basin) centrifuges scale particles above 100 microns out of the loop continuously, so the recirculated particle concentration decays campaign-over-campaign instead of accumulating; the basin's existing settling volume finishes the separation",
            "intervention": "one 150 mm hydrocyclone on the return line with an automated underflow collection pot, backflushed to a scale skip at each roll change",
            "predicted_effect": "loop particle concentration above 100 microns falls 85 percent within two campaigns; scale-driven clogging events fall from 4.1 to approximately 2.6; no pressure-drop penalty on the supply side (the cyclone sits on the return)",
            "testable_prediction": "isokinetic particle counts on return and basin-outlet lines show 85 percent plus or minus 5 percent removal above 100 microns at design flow; campaign clog counts trend to 2.6 plus or minus 0.5 over two campaigns",
            "novel_design_variable": "cyclone apex diameter versus cut size at return flow",
            "known_failure_modes": ["apex plugging during episodic descaling dumps (bypass protects supply)"],
            "constraint_set": {
                "boundary_conditions": "return-line installation only; 13-15 bar supply untouched; basin settling volume available"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": "none — a sound control: standard hydrocyclone physics, quantified removal with band, supply-side constraints untouched by construction, honest episodic-dump failure mode with bypass",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "Standard separation physics with a measured removal claim, confidence band, and a failure mode that cannot damage the supply constraint (return-side installation)."
        }
    },
    {
        "case_id": "cal-15-clean-clog-resistant-geometry",
        "category": "TRUE_NEGATIVE_clean_control",
        "seed_class": None,
        "control": True,
        "candidate": {
            "candidate_id": "cal-15-large-throat-swirl-nozzle",
            "mechanism": "a nozzle geometry with a 6 mm throat (double the current 3 mm) and an internal swirl ramp replaces sharp throat entry corners with a converging spiral passage; the doubled throat raises the bridging particle size threshold by roughly 4x (bridging scales with throat-to-particle ratio) and the swirl passage prevents low-velocity dead zones at the wall where deposits nucleate",
            "intervention": "nozzle replacement with 6 mm-throat swirl-ramp flat-fan nozzles of equivalent spray angle; spray distribution re-verified by the nozzle vendor's patternator at the mill's supply pressure",
            "predicted_effect": "campaign clogging events fall from 4.1 to approximately 1.8 (bridging threshold shift); droplet coarsening of approximately 8 percent is measured and offset by a 5 percent flow increase that stays inside the pump's headroom; crown variation inside 12 microns maintained by the re-patterned distribution",
            "testable_prediction": "vendor patternator shows distribution uniformity within 5 percent of the current nozzle at 14 bar; mill trial measures clogging events 1.8 plus or minus 0.6 per campaign over two campaigns with crown variation from the mill's thermography",
            "novel_design_variable": "throat diameter to bridging threshold ratio",
            "known_failure_modes": ["slightly coarser droplet spectrum (measured, offset declared)", "swirl ramp wear (vendor wear-life certificate for abrasive service)"],
            "constraint_set": {
                "boundary_conditions": "14 bar supply; same nominal flow class; roll-change-window installation; spray pattern uniformity within 5 percent of current"
            }
        },
        "evidence_items": [],
        "ground_truth": {
          "label": "KNOWN_GOOD",
          "expected_final": "SURVIVED",
          "defect_class": "none — a sound control: standard fluid-mechanics reasoning (bridging threshold scaling), a measured trade-off declared (coarser droplets, offset within pump headroom), vendor-verified spray pattern, quantified band",
          "expected_kill_surface": None,
          "expected_defect_in_basis": [],
          "ground_truth_basis": "The mechanism is ordinary engineering (larger throat, no dead zones), the trade-offs are measured and declared, and the prediction is instrumented with bands. Nothing is asserted without basis."
        }
    },
    {
        "case_id": "cal-16-clean-biocide-program",
        "category": "TRUE_NEGATIVE_clean_control",
        "seed_class": None,
        "control": True,
        "candidate": {
            "candidate_id": "cal-16-biofilm-dispersant-program",
            "mechanism": "the measured 88 percent biofilm-slime share of blockages is addressable by chemistry the mill already permits: a continuous low-dose oxidizing biocide plus a weekly dispersant slug oxidizes sessile biofilm and strips extracellular polymer from header walls, so slime aggregates never grow to bridging size at the throats",
            "intervention": "dosing skid on the recirculation loop (already plumbed for pH correction): continuous 0.3 ppm actinic biocide with ORP control, weekly 15-minute dispersant slug at 8 ppm with automatic rinse-down; dosing rates inside the mill's existing discharge permit",
            "predicted_effect": "sessile biofilm coverage falls from 10^6 to below 10^4 CFU per square centimeter within three weeks; biofilm-share clogging events fall from 2.9 to below 0.6 per campaign; total campaign clogging events fall from 4.1 to approximately 1.4 combined with routine screening",
            "testable_prediction": "monthly header-wall swab cultures show the 2-order CFU reduction; campaign clog counts over two campaigns measure 1.4 plus or minus 0.5; discharge permit compliance verified by the existing effluent monitoring",
            "novel_design_variable": "dispersant slug frequency versus slime regrowth rate",
            "known_failure_modes": ["under-dosing after upsets (ORP alarm interlock)", "biocide demand spikes from oil leaks in the loop (alarm + manual slug)"],
            "constraint_set": {
                "boundary_conditions": "dosing inside the existing discharge permit; ORP-controlled; no mill stop; recirculated water 32-38 C (biocide efficacy band verified by vendor at this temperature)"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": "none — a sound control: standard water-treatment chemistry matched to the MEASURED dominant failure share (biofilm), permit-bounded dosing, ORP interlocks, quantified CFU and clog-count predictions with bands",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "Industrial biofilm control in recirculated cooling water is textbook practice; the candidate bounds its dosing to the existing permit, instruments the effect (CFU swabs, ORP), and predicts with bands. Honest failure modes for demand spikes."
        }
    },
    # ------------------------------------------------------------------
    # EVIDENCE-CONTRADICTED: 17/18 refuted (expect KILL bound to the
    # evidence), 19 supported (expect SURVIVED)
    # ------------------------------------------------------------------
    {
        "case_id": "cal-17-evidence-refuted-seasonal",
        "category": "EVIDENCE_CONTRADICTED",
        "seed_class": "EVIDENCE_CONTRADICTION",
        "control": False,
        "candidate": {
            "candidate_id": "cal-17-seasonal-algae-bloom-control",
            "mechanism": "clogging is a warm-season phenomenon: summer algae blooms in the cooling basin seed the loop with organic particles that drive the biofilm share of blockages; a basin-cover shade + spring biocide shock timed before bloom season removes the seasonal driver and clogging falls to winter levels year-round",
            "intervention": "floating shade cover on the cooling basin plus one pre-summer biocide shock dosing at 40 ppm with rinse-down",
            "predicted_effect": "clogging events per campaign fall from 4.1 to the winter-baseline 1.6 year-round; the bloom-season peak disappears",
            "testable_prediction": "monthly clog-rate plots across two years show the summer peak eliminated after the cover installation; basin chlorophyll counts stay below 5 micrograms per liter through summer",
            "novel_design_variable": "cover shading fraction versus bloom suppression",
            "known_failure_modes": ["cover wind damage"],
            "constraint_set": {
                "boundary_conditions": "basin-cover installation only; dosing inside permit; no mill stop"
            }
        },
        "evidence_items": [
            {
                "id": "ev:cloglog-24mo",
                "title": "24-month nozzle clogging log across 12 campaigns: clog rate is UNIFORM year-round (4.0-4.3 events per campaign in every quarter, no summer peak or winter baseline; the winter campaigns 2025-Q1 and 2026-Q1 measured 4.2 and 4.0); clog rate correlates ONLY with campaign length between roll changes"
            },
            {
                "id": "ev:basin-temp",
                "title": "Basin water-temperature record: loop runs 32-38 C year-round (temperature-controlled by the strip schedule, not by season); chlorophyll counts below 3 micrograms per liter in all months (the basin is indoors)"
            }
        ],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "evidence contradiction — the candidate's premise (a warm-season bloom driver with a 1.6 winter baseline) is directly refuted by the provided 24-month log: clog rate is uniform 4.0-4.3 in every quarter including winters, the basin is indoors with chlorophyll below 3 ug/L year-round, and the rate correlates only with campaign length",
            "expected_kill_surface": "EVIDENCE_CONTRADICTION",
            "expected_defect_in_basis": ["uniform", "4.0", "4.2", "winter", "chlorophyll", "indoor", "campaign length"],
            "ground_truth_basis": "Both provided evidence items refute the seasonal premise outright: no summer peak exists (4.0-4.3 every quarter), no winter baseline of 1.6 exists, the basin is indoors and bloom-free. The correct kill binds to the measured uniform rate and the chlorophyll counts."
        }
    },
    {
        "case_id": "cal-18-evidence-refuted-average-sizing",
        "category": "EVIDENCE_CONTRADICTED",
        "seed_class": "EVIDENCE_CONTRADICTION",
        "control": False,
        "candidate": {
            "candidate_id": "cal-18-average-load-dual-media-filter",
            "mechanism": "a dual-media pressure filter (anthracite over sand) on the header supply sized on the campaign-AVERAGE scale load keeps the loop's particle load below the nozzle bridging threshold; average-load sizing is the standard design basis for side-stream filtration",
            "intervention": "one dual-media pressure filter vessel sized for the measured average load of 0.6 kg per hour total suspended solids, with automatic backwash on differential pressure",
            "predicted_effect": "loop suspended-solids held below the average-load design point at all times; clogging events per campaign fall from 4.1 to below 1.0",
            "testable_prediction": "continuous turbidity logging shows loop TSS at or below the 0.6 kg/h average design point after commissioning; campaign clog counts below 1.0 over two campaigns",
            "novel_design_variable": "media depth versus average-load capture capacity",
            "known_failure_modes": ["media channeling (annual re-grade)"],
            "constraint_set": {
                "boundary_conditions": "supply-side installation at full design flow; 13-15 bar; no mill stop for backwash"
            }
        },
        "evidence_items": [
            {
                "id": "ev:load-distribution",
                "title": "18-month suspended-solids load study: the load is HEAVY-TAILED — median 0.6 kg/h but P95 = 3.6 kg/h and P99 = 6.1 kg/h (episodic descaling-line failures dump 6x the median for 2-6 hours, 14 events recorded); average-sized filters blind and bypass during exactly these episodes"
            },
            {
                "id": "ev:episode-clog",
                "title": "Cross-reference of the 14 recorded high-load episodes with the nozzle clogging log: 61 percent of all campaign clogging events occur within 48 hours of a recorded descaling-dump episode"
              }
        ],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": "evidence contradiction — the average-load design basis is refuted by the provided load study: the load is heavy-tailed (P95 = 6x median) and 61 percent of clogging events cluster within 48 h of the recorded dump episodes — a filter sized on the average blinds and bypasses during exactly the episodes that cause the clogging",
            "expected_kill_surface": "EVIDENCE_CONTRADICTION",
            "expected_defect_in_basis": ["P95", "median", "heavy-tail", "61 percent", "episode", "blind"],
            "ground_truth_basis": "The sizing premise (average load is the right basis) is contradicted by the measured tail: the clogging is episode-driven (61 percent within 48 h of dumps) and the proposed filter class fails precisely then. The correct kill binds to the P95/P99-to-median ratios and the 61 percent clustering figure."
        }
    },
    {
        "case_id": "cal-19-evidence-supported-sidestream",
        "category": "EVIDENCE_CONTRADICTED",
        "seed_class": None,
        "control": True,
        "candidate": {
            "candidate_id": "cal-19-tail-sized-sidestream-filter",
            "mechanism": "a side-stream dual-media filter sized on the MEASURED TAIL (P95 = 3.6 kg/h) with an episodic-dump response mode (turbidity-triggered flow boost from 10 to 25 percent side-stream share) catches the dump episodes that the load study shows drive 61 percent of clogging; between episodes it runs at the economical share",
            "intervention": "side-stream filtration skid (dual media, sized at P95 load) with online turbidity trigger and a dump-response valve schedule; installed off-line during a roll change",
            "predicted_effect": "episode-driven clogging suppressed (the 61 percent share reduced 5x); total campaign clogging events fall from 4.1 to approximately 1.6; media backwash sized for the P99 episode duration",
            "testable_prediction": "during the next recorded dump episode, loop turbidity at the header stays below the bridging threshold (logged); campaign clog counts measure 1.6 plus or minus 0.6 over two campaigns; backwash water use below the basin make-up budget",
            "novel_design_variable": "dump-response side-stream share versus episode turbidity capture",
            "known_failure_modes": ["turbidity sensor fouling (duplicated sensors, agreement check)"],
            "constraint_set": {
                "boundary_conditions": "side-stream only (supply pressure untouched); P95-sized media with P99-duration backwash; no mill stop"
            }
        },
        "evidence_items": [
            {
                "id": "ev:load-distribution",
                "title": "18-month suspended-solids load study: the load is HEAVY-TAILED — median 0.6 kg/h but P95 = 3.6 kg/h and P99 = 6.1 kg/h (episodic descaling-line failures dump 6x the median for 2-6 hours, 14 events recorded); average-sized filters blind and bypass during exactly these episodes"
            },
            {
                "id": "ev:episode-clog",
                "title": "Cross-reference of the 14 recorded high-load episodes with the nozzle clogging log: 61 percent of all campaign clogging events occur within 48 hours of a recorded descaling-dump episode"
            },
            {
                "id": "ev:sidestream-flow",
                "title": "Hydraulic audit of the recirculation loop: 25 percent side-stream share is available within existing pump headroom at 13-15 bar supply; basin make-up capacity covers the backwash water budget at P99 episode duration"
            }
        ],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "SURVIVED",
            "defect_class": "none — a sound control whose design basis MATCHES the provided evidence: tail-sized media, episode-triggered response targeting the measured 61 percent clustering, flow and make-up feasibility confirmed by the hydraulic audit evidence",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "The candidate consumes the provided evidence correctly (tail sizing, episode response, hydraulic feasibility) and predicts with instruments and bands. Evidence supports rather than refutes."
        }
    },
    # ------------------------------------------------------------------
    # MALFORMED / MISSING EVIDENCE: absence traps (expect NOT-KILL —
    # killing on absent/unusable evidence is the ABSENCE_AS_CONTRADICTION
    # false-kill class, Art. XXI.3/XXV)
    # ------------------------------------------------------------------
    {
        "case_id": "cal-20-absence-no-evidence-provided",
        "category": "MALFORMED_MISSING_EVIDENCE",
        "seed_class": None,
        "control": True,
        "candidate": {
            "candidate_id": "cal-20-unevidenced-staged-cascade",
            "mechanism": "a two-stage wedge-wire cascade (300 then 120 micron) on the header supply removes scale particles above 120 microns, with dP-triggered automatic backflush keeping the cascade in service without mill stops (same intervention class as the sound control, but NO evidence bundle is provided with this record)",
            "intervention": "two-stage wedge-wire cascade with dP monitoring and automatic backflush on the 150 mm supply, flanged spool swap at a planned roll change",
            "predicted_effect": "campaign clogging events fall from 4.1 to below 1.5; crown excursions fall from 28 to below 16 microns; roll-change cleaning time drops to 15 minutes",
            "testable_prediction": "two-campaign split trial measures clogging events 1.5 or below (95 percent band 1.0-2.0) versus baseline 4.1 plus or minus 0.6, by the mill's clog log and roll thermography",
            "novel_design_variable": "second-stage micron rating and backflush dP threshold",
            "known_failure_modes": ["backflush valve jam (spare held)"],
            "constraint_set": {
                "boundary_conditions": "13-15 bar; full design flow; no mill stop"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD_UNEVIDENCED",
            "expected_final": "SURVIVED",
            "defect_class": "none in the candidate — the record simply carries NO evidence items. The correct attacker behavior is at most an honest RISK note that the mechanism is unevidenced on this record (an absence, Art. XXI.3), NEVER a KILL asserting evidence contradicts it: no evidence is not negative evidence (Art. XXV)",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "The candidate is mechanically sound; the record's evidence bundle is empty. An attacker that kills with phrases like 'no evidence the filtration works' has converted absence into contradiction — the ABSENCE_AS_CONTRADICTION false-kill class. The honest verdict is SURVIVED (optionally with a RISK noting the unevidenced basis)."
        }
    },
    {
        "case_id": "cal-21-absence-malformed-evidence",
        "category": "MALFORMED_MISSING_EVIDENCE",
        "seed_class": None,
        "control": True,
        "candidate": {
            "candidate_id": "cal-21-corrupt-evidence-bundle",
            "mechanism": "a cyclonic pre-separator on the recirculation return line centrifuges scale particles above 100 microns out of the loop continuously, so the recirculated concentration decays campaign-over-campaign (same intervention class as the sound control); the record's evidence bundle is MALFORMED — the items carry identifier fragments and truncated titles only, no usable content",
            "intervention": "one 150 mm hydrocyclone on the return line with automated underflow collection, backflushed at each roll change",
            "predicted_effect": "loop particles above 100 microns fall 85 percent within two campaigns; scale-driven clogging events fall from 4.1 to approximately 2.6",
            "testable_prediction": "isokinetic particle counts on return and basin-outlet lines show 85 percent plus or minus 5 percent removal above 100 microns; campaign clog counts trend to 2.6 plus or minus 0.5",
            "novel_design_variable": "cyclone apex diameter versus cut size",
            "known_failure_modes": ["apex plugging during dumps (bypass protects supply)"],
            "constraint_set": {
                "boundary_conditions": "return-line installation only; supply untouched; basin settling available"
            }
        },
        "evidence_items": [
            {"id": "ev:frag-01", "title": "TRL-2026-0x91 f... (truncated record)"},
            {"id": "ev:frag-02", "title": ""},
            {"id": "ev:frag-03", "title": " Hydraulic audit summary (no figures; extraction failed)"}
        ],
        "ground_truth": {
            "label": "KNOWN_GOOD_MALFORMED_EVIDENCE",
            "expected_final": "SURVIVED",
            "defect_class": "none in the candidate — the evidence bundle is UNUSABLE (truncated, empty, figureless fragments). Unusable evidence is an honest UNKNOWN (Art. XXV), never negative evidence: an attacker claiming the malformed items refute the mechanism, or inventing content they cannot carry, kills on fabricated grounding",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "The evidence items cannot support ANY claim (positive or negative) — they are fragments. The honest treatment is uncertainty about the evidentiary basis, at most RISK-level; a KILL citing the malformed items as contradiction or inventing their content is the fabricated-grounding failure mode."
        }
    },
    {
        "case_id": "cal-22-absence-no-failure-modes-claimed",
        "category": "MALFORMED_MISSING_EVIDENCE",
        "seed_class": None,
        "control": True,
        "candidate": {
            "candidate_id": "cal-22-thin-record-biocide",
            "mechanism": "continuous low-dose oxidizing biocide with weekly dispersant slugs controls the biofilm share of nozzle clogging in the recirculated loop (same chemistry class as the sound control); this record is THIN: no failure modes are claimed, no evidence bundle, and the prediction is carried over from the intervention class rather than re-derived for this mill",
            "intervention": "dosing skid on the recirculation loop: continuous 0.3 ppm actinic biocide with ORP control, weekly 15-minute dispersant slug at 8 ppm",
            "predicted_effect": "biofilm-share clogging events fall from 2.9 to below 0.6 per campaign; total events to approximately 1.4 with routine screening",
            "testable_prediction": "monthly header-wall swab cultures show a 2-order CFU reduction; campaign clog counts measure 1.4 plus or minus 0.5 over two campaigns",
            "novel_design_variable": "dispersant slug frequency",
            "known_failure_modes": [],
            "constraint_set": {
                "boundary_conditions": "dosing inside the existing discharge permit; no mill stop"
            }
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD_THIN_RECORD",
            "expected_final": "SURVIVED",
            "defect_class": "none disqualifying — the record is thin (no claimed failure modes, no evidence bundle, class-level prediction), which the attacker may honestly flag at RISK level (thin record, unclaimed failure modes). The candidate is not killed: the absence of claimed failure modes is not evidence the mechanism fails, and inventing 'certain' failure modes to justify a KILL fabricates grounding",
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": "A thin record warrants the honesty flag (RISK-level: failure modes unclaimed, prediction not re-derived), never a terminal KILL — the mechanism itself is standard and the prediction instrumented. Inventing failure modes as certain kills is fabrication."
        }
    }
]


def main() -> int:
    corpus = json.loads(CORPUS.read_text())
    existing = {c["case_id"] for c in corpus["cases"]}
    added = 0
    for case in EXTRA_CASES:
        if case["case_id"] in existing:
            continue
        corpus["cases"].append(case)
        added += 1
    corpus["n_cases"] = len(corpus["cases"])
    # category counts recomputed from the cases themselves (Art. XXIV:
    # the artifact is the authority, the header is derived)
    counts: dict = {}
    for c in corpus["cases"]:
        counts[c["category"]] = counts.get(c["category"], 0) + 1
    corpus["category_counts"] = counts
    CORPUS.write_text(json.dumps(corpus, indent=1, ensure_ascii=False))
    print(f"appended {added} cases; total {corpus['n_cases']}")
    print("categories:", json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

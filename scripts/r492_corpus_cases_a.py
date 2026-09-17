"""R492 — A2 DEV calibration corpus, cases 1-11 (defect cohorts).

AUTHORSHIP DISCIPLINE (Art. L / Art. LIX): every case below was authored
from first-principles engineering knowledge BEFORE any execution of the A2
gauntlet (discovery_fabric/a2/adversarial.py::adversarial_challenge) on
this corpus. No ground truth was derived from the instrument's behavior on
this or any corpus. This file is the authorship record; the corpus it
writes is frozen (sha256-pinned) before any tuning run, per the owned
R490 work plan step 1 and the R492 operator directive ("the A2 DEV corpus,
frozen before any tuning").

Common problem: ballast water management system (BWMS) retrofit for IMO
D-2 compliance on a 38,000 DWT coastal bulk carrier. Disjoint from:
  - R446/ATTACKER_CALIBRATION (hot-rolling mill work-roll cooling spray)
  - R412/CALIBRATION (40-case, 24 domains; nearest cases are a rain-erosion
    healing coating and a blade VG retrofit — different problems, different
    candidates, different mechanisms)
  - R401-WC2 (compressed-air moisture separator), R458 (14 problems incl.
    drip irrigation / inkjet / cam follower), and the six-domain seed
    campaign (infusion pumps, EV batteries, aerospace lithium, rails,
    rolling-stock, consumer li-ion)
"""

COMMON_PROBLEM = {
    "device": (
        "ballast water management system (BWMS) retrofit for a 38,000 DWT "
        "coastal bulk carrier: four ballast tanks, 6,500 m3 total capacity, "
        "main ballast pumps 2 x 350 m3/h, uptake/discharge through 300 mm "
        "sea chests, voyages 1-10 days, uptake ports mixing estuarine "
        "harbors (turbidity 15-80 NTU, UVT254 38-62 percent) and coastal "
        "roadsteads (turbidity 5-20 NTU, UVT254 55-80 percent), salinity "
        "8-36 PSU, water temperature 2-30 C"),
    "failure": (
        "non-compliance with the IMO D-2 discharge standard (viable "
        "organisms >=50 um: fewer than 10 per m3; organisms >=10-<50 um: "
        "fewer than 10 per mL; indicator microbe limits) at discharge "
        "sampling: Port State Control detention risk, off-hire days, and "
        "retrofit cost exposure; the dominant fleet failure mode is "
        "worst-case uptake water (high turbidity, low UVT, low temperature "
        "slowing physiology-dependent processes) plus sediment "
        "resuspension at discharge start"),
    "failure_mode": (
        "insufficient organism inactivation/removal across the "
        "organism-size spectrum under worst-case uptake water and "
        "sediment-laden discharge"),
    "constraint": (
        "no hull modification beyond class-approved sea-chest penetration; "
        "retrofit inside one 14-day drydock; treatment room 14 m2; "
        "electrical load margin 120 kW; zero crew-side chemical handling "
        "(sealed automated dosing only); operation by the existing ETO "
        "crew; class and flag approval required; USCG type acceptance "
        "required for US trades"),
}

A2_DIMENSIONS = [
    "unsupported_mechanism", "weak_transfer", "obvious_combination",
    "prior_art", "contradiction", "boundary_failure",
    "engineering_infeasibility", "regulatory_incompatibility",
]

VALID_PRIOR_ART_STATES = [
    "NO_MATCH_FOUND", "TOPICAL_RELATED", "POSSIBLE_RELEVANCE",
    "UNRESOLVED_INSUFFICIENT_EVIDENCE", "SPECIFIC_DISCLOSURE",
    "IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE",
]


def _c01():
    return {
        "case_id": "a2dev-01-cavitation-radical-bulk-kill",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "CAUSAL_INVALIDITY",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-01-vortex-radical-conditioner",
            "mechanism": (
                "a high-speed hydrodynamic vortex conditioner (rotor-stator, "
                "45 kW) generates transient cavitation microbubbles in the "
                "ballast stream; the claimed hydroxyl-radical pulse oxidizes "
                "the lipid membranes of zooplankton and the cell walls of "
                "phytoplankton during the 0.4 s conditioning dwell, achieving "
                "3.5-log organism inactivation in the main flow with no "
                "chemical residual and no holding time"),
            "intervention": (
                "inline rotor-stator vortex conditioner rated 350 m3/h "
                "installed in the ballast main after the sea-chest strainer; "
                "45 kW motor; no filter stage beyond the existing sea-chest "
                "strainer, no UV, no holding tank; treated water discharged "
                "directly after uptake"),
            "predicted_effect": (
                "3.5-log reduction of viable organisms >=50 um and >=3-log "
                "for the 10-50 um fraction at 350 m3/h continuous flow; D-2 "
                "compliance at discharge with no intermediate storage"),
            "testable_prediction": (
                "a bench loop at 5 m3/h with natural seawater shows >=3-log "
                "single-pass viability loss of Artemia nauplii and "
                "Tetraselmis at specific energy input 8 Wh/m3, replicated "
                "across three water qualities"),
            "novel_design_variable": (
                "rotor tip speed and conditioning dwell (specific energy "
                "input per m3)"),
            "known_failure_modes": [
                "cavitation intensity collapses at part-flow conditions",
                "rotor-stator erosion and clearance growth in sandy water",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "uptake water 2-30 C, salinity 8-36 PSU, turbidity up to "
                    "80 NTU; no holding time available on ballast-up; 45 kW "
                    "power envelope"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "causal invalidity — hydroxyl-radical production by "
                "hydrodynamic cavitation in seawater at the claimed specific "
                "energy (~8 Wh/m3, i.e. ~29 kJ per m3) is orders of magnitude "
                "below the specific energies at which cavitational radical "
                "chemistry is even measurable (tens of kJ per LITER, 1000x "
                "higher); hydroxyl radicals recombine on a ~1 microsecond "
                "timescale and cannot accumulate a lethal integrated dose "
                "across a 0.4 s dwell at these concentrations; a 3.5-log kill "
                "with zero residual and zero holding time has no physically "
                "valid causal chain"),
            "expected_kill_surface": "unsupported_mechanism",
            "expected_defect_in_basis": [
                "hydroxyl", "radical", "specific energy", "recombine",
                "microsecond", "order", "dose", "physically",
            ],
            "ground_truth_basis": (
                "Published cavitational OH yields are ~1e-11 to 1e-10 mol/J; "
                "at 29 kJ/m3 that is ~3e-7 to 3e-6 mol of OH per m3 spread "
                "over the flow — 3 to 5 orders of magnitude below the "
                "integrated exposure required for membrane-level kill of "
                "metazoans; bench sonication kills that DO reach 3-log "
                "operate at 10-100 kJ/L (3-4 orders more energy) and do not "
                "transfer to the claimed flow regime"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c02():
    return {
        "case_id": "a2dev-02-uv-dose-low-uvt-boundary",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "BOUNDARY_CONDITION_FAILURE",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-02-mp-uv-fixed-dose",
            "mechanism": (
                "a medium-pressure UV side-stream reactor delivering a "
                "validated 400 J/m2 UV-C dose at 350 m3/h; validated "
                "inactivation >=3-log for organisms >=50 um at the "
                "validation site's water quality; dose verified by an inline "
                "UV intensity sensor with flow interlock"),
            "intervention": (
                "one MP-UV reactor chamber (2 x 6.5 kW lamps) on a "
                "side-stream loop, sized and type-test validated at UVT254 "
                ">= 80 percent; no UVT-compensation control and no low-UVT "
                "operating limit are included"),
            "predicted_effect": (
                "validated 400 J/m2 delivery and >=3-log inactivation of "
                ">=50 um organisms at rated flow across the fleet's uptake "
                "ports"),
            "testable_prediction": (
                "land-based G8 test at the validation water quality shows "
                ">=3-log viable-organism reduction for >=50 um at 350 m3/h"),
            "novel_design_variable": (
                "side-stream loop sizing and lamp power split across two "
                "chambers"),
            "known_failure_modes": [
                "lamp aging reduces delivered dose between replacements",
                "quartz sleeve fouling in turbid water lowers intensity",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "uptake ports include estuarine harbors with UVT254 "
                    "38-62 percent and turbidity 15-80 NTU (declared in the "
                    "common problem); retrofit inside 120 kW margin"),
            },
        },
        "evidence_items": [
            {
                "id": "ev:uvt-survey",
                "title": (
                    "12-month UVT254 survey of the four uptake ports: "
                    "estuarine berths 38-62 percent UVT254 at slack water "
                    "with a spring-tide minimum of 36 percent; coastal "
                    "roadsteads 55-80 percent; UVT correlates inversely with "
                    "turbidity (r = -0.83)"),
            },
        ],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "boundary-condition failure — the reactor's validated dose "
                "(400 J/m2) holds only at UVT254 >= 80 percent, while the "
                "declared uptake-port envelope includes estuarine water at "
                "UVT254 38-62 percent (surveyed spring-tide minimum 36 "
                "percent); delivered dose scales roughly with UVT, so at the "
                "declared berths the reactor falls below the ~300 J/m2 "
                "minimum required for the claimed 3-log kill, and the "
                "candidate carries no UVT-compensating control and no "
                "low-UVT operating limit"),
            "expected_kill_surface": "boundary_failure",
            "expected_defect_in_basis": [
                "UVT", "dose", "transmissivity", "turbid", "boundary",
                "valid",
            ],
            "ground_truth_basis": (
                "UV dose delivery in a fixed-power reactor degrades "
                "essentially linearly with UVT254; at 40 percent UVT the "
                "delivered dose of an 80-percent-UVT-validated reactor is "
                "roughly half the validated value (~200 J/m2 < 300 J/m2 "
                "floor); the survey evidence (provided in the case) binds "
                "the boundary failure to the fleet's actual berths"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c03():
    return {
        "case_id": "a2dev-03-claim-vs-type-approval-report",
        "category": "EVIDENCE_CONTRADICTED",
        "seed_class": "EVIDENCE_CONTRADICTION",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-03-cyclonic-edp-5p5log",
            "mechanism": (
                "two-stage counter-current cyclonic separation followed by "
                "inline electrodialysis-with-peroxide (EDP) oxidant "
                "generation and a 30 min tank dwell, claimed to achieve "
                "5.5-log inactivation of organisms >=50 um at 350 m3/h"),
            "intervention": (
                "cyclonic pre-separator bank plus EP oxidant module in the "
                "ballast main; dwell is the ballast tank itself; discharge "
                "after neutralization to below 0.5 mg/L residual oxidant"),
            "predicted_effect": (
                "5.5-log inactivation of organisms >=50 um at rated flow "
                "with 30 min dwell and <=4.5 mg/L residual oxidant"),
            "testable_prediction": (
                "full-scale land-based G8 test at rated flow demonstrates "
                "the 5.5-log mean inactivation with all replicates above "
                "the D-2 margin"),
            "novel_design_variable": (
                "oxidant dosing profile coupled to cyclone stage removal "
                "efficiency"),
            "known_failure_modes": [
                "oxidant demand spikes in high-organic port water",
                "cyclone efficiency degrades for near-neutral-buoyancy "
                "organisms",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "uptake water 2-30 C, salinity 8-36 PSU; dwell >= 30 min "
                    "requires tank arrangement; 120 kW power margin"),
            },
        },
        "evidence_items": [
            {
                "id": "ev:vendor-type-approval",
                "title": (
                    "Vendor full-scale land-based type-approval test report "
                    "(G8 annex): mean inactivation of organisms >=50 um is "
                    "3.8-log at rated flow (95 percent CI 3.1-4.4-log), with "
                    "two of ten replicates below the D-2 minimum margin; "
                    "residual oxidant at discharge 0.4-0.6 mg/L"),
            },
        ],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "evidence contradiction — the candidate claims 5.5-log "
                "inactivation while its own cited full-scale type-approval "
                "report measures 3.8-log mean (95 percent CI 3.1-4.4) with "
                "two of ten replicates below the D-2 minimum margin; the "
                "claimed effect contradicts the provided evidence by ~1.7 "
                "log and the claim does not survive its own test data"),
            "expected_kill_surface": "contradiction",
            "expected_defect_in_basis": [
                "3.8", "5.5", "type-approval", "replicate", "CI", "log",
            ],
            "ground_truth_basis": (
                "The claim (5.5-log) and the cited evidence (3.8-log mean, "
                "CI topping at 4.4-log, two failing replicates) cannot both "
                "be true; the kill basis must bind to the report's numbers"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c04():
    return {
        "case_id": "a2dev-04-baseline-filter-uv-repack",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "BASELINE_EQUIVALENCE",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-04-filter-uv-packaged-baseline",
            "mechanism": (
                "side-stream 40 um automatic backwash screen filtration "
                "followed by medium-pressure UV with closed-loop dose "
                "control keyed to an inline UVT254 sensor and flow meter, "
                "packaged with a marine PLC and remote monitoring dashboards "
                "for compliance logging"),
            "intervention": (
                "standard filter-plus-MP-UV train at 350 m3/h in the 14 m2 "
                "treatment room; automatic backwash reject returned to the "
                "sea chest; PLC logging for Port State Control inspection"),
            "predicted_effect": (
                "D-2 compliance at rated flow with automatic dose "
                "compensation across the fleet's water qualities"),
            "testable_prediction": (
                "land-based G8 test at rated flow shows D-2 compliance "
                "across fresh, brackish, and seawater test waters"),
            "novel_design_variable": (
                "packaging layout and the compliance-logging dashboard"),
            "known_failure_modes": [
                "backwash reject load at high-turbidity uptake",
                "lamp replacement scheduling in service windows",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "fleet uptake envelope (turbidity 15-80 NTU, UVT254 "
                    "38-62 percent); 120 kW margin; 14 m2 room"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "baseline equivalence — the proposed configuration (40 um "
                "automatic backwash filter + medium-pressure UV + UVT-keyed "
                "dose control) IS the dominant shipped, type-approved BWMS "
                "architecture; no mechanism-level, sizing-level, or "
                "control-level difference from the baseline is claimed — the "
                "only 'novel design variable' is packaging layout and a "
                "logging dashboard, which are non-technical differentiators; "
                "this is a repackaging of the known baseline offered as an "
                "invention"),
            "expected_kill_surface": "obvious_combination",
            "expected_defect_in_basis": [
                "baseline", "known", "type-approved", "combination",
                "existing", "prior",
            ],
            "ground_truth_basis": (
                "Filter+UV with dose control is the shipped baseline of "
                "multiple type-approved BWMS product families; equivalence "
                "to the baseline with a trivial packaging delta is exactly "
                "the baseline-equivalence class Art. L names"),
            "prior_art_state": "POSSIBLE_RELEVANCE",
        },
    }


def _c05():
    return {
        "case_id": "a2dev-05-hydrocyclone-10um-full-flow",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "IMPLEMENTATION_IMPOSSIBILITY",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-05-hydrocyclone-10um",
            "mechanism": (
                "full-flow bank of 24 parallel hydrocyclones in the existing "
                "300 mm ballast main achieving a d50 cut point of 10 um for "
                "the 10-50 um organism fraction at 700 m3/h total, using "
                "only the existing main ballast pump head with no added "
                "pumps, claiming 2.5-log removal of the 10-50 um fraction "
                "by density separation alone"),
            "intervention": (
                "24-unit hydrocyclone bank on the ballast main downstream of "
                "the sea-chest strainer; underflow recirculated to the sea "
                "chest; no filter media, no oxidant, no UV"),
            "predicted_effect": (
                "2.5-log removal of organisms in the 10-50 um band at 700 "
                "m3/h total flow with the existing pump head"),
            "testable_prediction": (
                "full-flow trial shows d50 <= 10 um against a calibrated "
                "10 um polystyrene challenge at the existing pump head"),
            "novel_design_variable": (
                "hydrocyclone diameter and underflow recirculation ratio"),
            "known_failure_modes": [
                "separation degrades for particles with density near water",
                "underflow recirculation re-entrains captured organisms",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "no added pumps (existing main ballast pump head only); "
                    "300 mm main; 700 m3/h total at two pumps"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "implementation impossibility — a 10 um d50 cut point for "
                "near-neutral-buoyancy biological particles (specific "
                "gravity 1.05-1.25) requires centrifugal accelerations and "
                "pressure drops on the order of 6-10 bar across the "
                "cyclones; a main ballast pump delivers 2.5-3.5 bar total "
                "head of which the piping system already consumes most; at "
                "the available 1.5-2.5 bar the d50 for silica (SG 2.65) is "
                "25-40 um and for biological particles (SG ~1.1) it is "
                "well above 40 um — the claimed 2.5-log removal of the "
                "10-50 um band cannot be implemented with the declared "
                "pump head"),
            "expected_kill_surface": "engineering_infeasibility",
            "expected_defect_in_basis": [
                "pressure", "head", "bar", "cut point", "d50", "buoyancy",
                "pump",
            ],
            "ground_truth_basis": (
                "Hydrocyclone cut-size scaling (d50 ~ (D^3 * mu / "
                "(Q * rho_slip))^0.5 family) at feasible pressure drops and "
                "the density contrast of living plankton (1.05-1.25 vs "
                "seawater 1.02-1.03) put the achievable d50 far above 10 um "
                "with the declared pump head; the case declares 'no added "
                "pumps' so the head is fixed"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c06():
    return {
        "case_id": "a2dev-06-sic-membrane-no-cip",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "MANUFACTURING_FAILURE",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-06-sic-membrane-12mo",
            "mechanism": (
                "silicon-carbide ceramic monolith side-stream loop with 50 "
                "nm nominal pores providing absolute physical retention of "
                "all organisms >=10 um (and >=6-log of bacteria), operating "
                "12 months between cleanings with a transmembrane pressure "
                "rise below 0.15 bar, requiring no clean-in-place chemicals, "
                "no backpulse infrastructure, and no consumables at 350 "
                "m3/h"),
            "intervention": (
                "six SiC monolith modules (total 220 m2 membrane area) on a "
                "side-stream loop with permeate returned overboard... "
                "permeate-to-tank routing; feed taken from the ballast main; "
                "no CIP skid, no backpulse air compressor, no chemical "
                "tanks (per the zero-crew-handling constraint)"),
            "predicted_effect": (
                "absolute physical exclusion of >=10 um organisms and "
                "6-log bacterial retention for a 12-month service interval "
                "at TMP rise < 0.15 bar"),
            "testable_prediction": (
                "pilot at 35 m3/h for 90 days shows TMP rise below 0.02 bar "
                "with no cleaning, extrapolating linearly to 12 months at "
                "0.15 bar"),
            "novel_design_variable": (
                "membrane area-to-flow ratio chosen to hold flux at 26 LMH"),
            "known_failure_modes": [
                "abrasion of the permselective layer by sand",
                "permeate routing requires class approval",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "zero crew-side chemical handling (no CIP chemicals "
                    "carried); 12-month service interval; 14 m2 room"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "manufacturing/servicing failure — seawater biofouling plus "
                "particulate loading on 50 nm ceramic membranes at 26 LMH "
                "flux drives transmembrane pressure to 0.6+ bar within days "
                "to weeks without backpulsing and cleaning-in-place "
                "(hypochlorite/citric acid cycles); the installed base of "
                "ceramic and polymer membrane BWMS-class systems services "
                "on hours-to-weeks cadence; a 12-month no-CIP interval at "
                "<0.15 bar TMP contradicts membrane fouling physics and "
                "field service data, and the constraint set itself forbids "
                "the CIP chemicals that any real service interval requires"),
            "expected_kill_surface": "engineering_infeasibility",
            "expected_defect_in_basis": [
                "fouling", "backpulse", "clean", "CIP", "transmembrane",
                "TMP", "service", "flux",
            ],
            "ground_truth_basis": (
                "Membrane fouling in seawater (biofilm + scale + silt) at "
                "tens-of-LMH flux is the documented dominant operating cost "
                "of membrane BWMS-class systems; the candidate's own "
                "constraint set (zero chemical handling) removes the only "
                "known recovery mechanism"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c07():
    return {
        "case_id": "a2dev-07-viability-endpoint-undefined",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "MEASUREMENT_AMBIGUITY",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-07-pef-viability",
            "mechanism": (
                "pulsed electric field (PEF) treatment permeabilizes "
                "organism cell membranes (60 kV applied pulses across a "
                "co-flow treatment chamber) followed by a 30 min holding "
                "period, reducing the viability of the ballast biota across "
                "all size fractions"),
            "intervention": (
                "PEF treatment chamber in the ballast main (350 m3/h, 90 kW "
                "pulsed supply) plus the ballast tank as the 30 min hold "
                "volume"),
            "predicted_effect": (
                "significant reduction in viable organisms of 85 percent "
                "across all size fractions, as measured by standard "
                "viability methods"),
            "testable_prediction": (
                "85 percent viability reduction demonstrated on mixed "
                "natural assemblages by standard methods after one pass "
                "plus 30 min hold"),
            "novel_design_variable": (
                "field strength and pulse count against the organism-size "
                "fractions"),
            "known_failure_modes": [
                "conductivity variation changes pulse delivery",
                "large metazoans shielded by their own body size",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "salinity 8-36 PSU changes conductivity by 4x; 120 kW "
                    "margin; no holding time beyond the 30 min hold"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "measurement ambiguity — the claimed endpoint ('significant "
                "reduction in viable organisms of 85 percent by standard "
                "viability methods') never defines the viability metric; the "
                "D-2 standard counts organisms as viable via vital staining "
                "(FDA/CMFDA class), motility, and live/dead gestalt for "
                "selected taxa, and those endpoints diverge from "
                "membrane-permeabilization and metabolic proxies; PEF-"
                "treated organisms can stain as non-viable while remaining "
                "reproductively viable (electroporation is reversible below "
                "irreversible thresholds) — the claimed number is not tied "
                "to a measurable, compliance-relevant endpoint, so the "
                "predicted effect cannot be verified or falsified as stated "
                "and cannot be mapped to D-2 compliance"),
            "expected_kill_surface": "unsupported_mechanism",
            "expected_defect_in_basis": [
                "viability", "endpoint", "stain", "metric", "measur",
                "D-2", "reversible",
            ],
            "ground_truth_basis": (
                "Art. XXVII's measurement discipline: a predicted effect "
                "that does not name its metric, units, replicate structure, "
                "and compliance mapping is unmeasurable; 'standard "
                "viability methods' is not a metric, and the D-2-relevant "
                "metrics are named and different"),
            "prior_art_state": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
        },
    }


def _c08():
    return {
        "case_id": "a2dev-08-electrochlorinear-linear-scaleup",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "SCALING_FAILURE",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-08-ec-linear-scaleup",
            "mechanism": (
                "bipolar titanium/Pt-IrO2 electrochlorination cell "
                "generating total residual oxidant (TRO) of 5 mg/L as Cl2 "
                "in the ballast stream, demonstrated at 5 m3/h bench pilot "
                "with 3-log kill of Artemia nauplii and heterotrophic "
                "bacteria at 30 C; the shipboard unit scales the same cell "
                "module linearly (seventy identical cells in parallel) to "
                "350 m3/h with identical electrode geometry, identical "
                "current density, and a 4 h tank dwell"),
            "intervention": (
                "seventy bench-proven cell modules in parallel on the "
                "ballast main; TRO sensor at discharge; no dwell-time "
                "extension beyond the 4 h tank hold"),
            "predicted_effect": (
                "3-log organism inactivation at 350 m3/h identical to the "
                "bench pilot, at identical per-cell current density and "
                "electrode area"),
            "testable_prediction": (
                "full-scale trial at 350 m3/h reproduces the bench kill "
                "rate with the parallel cell bank at the same per-cell "
                "settings"),
            "novel_design_variable": (
                "number of parallel bench-identical cells (scaling by "
                "replication, not redesign)"),
            "known_failure_modes": [
                "cathodic scaling in seawater hardens with current density",
                "TRO demand rises with organic load at port uptake",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "port uptake water (high organics, 2-30 C); 120 kW "
                    "margin; dwell = 4 h tank hold"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "scaling failure — the bench pilot at 5 m3/h ran at a "
                "current density and organic load that cannot hold at 70x "
                "flow with 'identical electrodes and identical current "
                "density': (i) instantaneous TRO demand scales with the "
                "organic load of port uptake water (3x the pilot's clean "
                "seawater at the same temperature band), so constant TRO "
                "needs 3x current, not constant current; (ii) cathodic "
                "Ca/Mg hydroxide scaling grows super-linearly with current "
                "density, and the acid-cleaning cadence scales with it; "
                "(iii) holding the bench's per-cell current density while "
                "tripling effective TRO demand is arithmetically "
                "inconsistent — the claim 'identical settings at 70x flow "
                "reproduce the bench kill' violates its own chemistry"),
            "expected_kill_surface": "engineering_infeasibility",
            "expected_defect_in_basis": [
                "scale", "current density", "electrode", "scaling",
                "TRO", "linear", "demand",
            ],
            "ground_truth_basis": (
                "Electrochlorination scaling is governed by TRO demand per "
                "volume (water-quality dependent), Faradaic limits, and "
                "cathodic fouling kinetics; 'scale by replication with "
                "identical settings' ignores that the DEMAND side (organics, "
                "temperature) changes with the port environment the pilot "
                "never saw"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c09():
    return {
        "case_id": "a2dev-09-electrochlor-h2-natural-vent",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "SAFETY_FAILURE",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-09-ec-h2-turbulent-dilution",
            "mechanism": (
                "electrolytic generation of active chlorine directly in the "
                "ballast stream during uptake, dosing 8-10 mg/L TRO for "
                "3-log kill with a 4 h tank dwell; hydrogen co-produced at "
                "the cathode is diluted below flammable concentration by "
                "the turbulent ballast flow and the existing natural tank "
                "venting; no dedicated ventilation or gas detection is "
                "added"),
            "intervention": (
                "electrolyzer skid in the treatment room, in-line injection "
                "at uptake; hydrogen released into the carrier stream and "
                "relied upon to stay below LEL by dilution and the tank's "
                "existing pressure-vacuum vent"),
            "predicted_effect": (
                "3-log kill at 8-10 mg/L TRO with hydrogen safely dispersed "
                "by flow turbulence without dedicated ventilation"),
            "testable_prediction": (
                "hydrogen concentration measured at the tank headspace "
                "during a full ballast-up remains below 25 percent of LEL "
                "with natural venting only"),
            "novel_design_variable": (
                "elimination of the dedicated hydrogen ventilation system "
                "(cost/space saving) via reliance on turbulent dilution"),
            "known_failure_modes": [
                "hydrogen stratification in tank headspace dead zones",
                "electrolyzer enclosure leaks concentrate H2 locally",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "four ballast tanks with existing Pv vents only; "
                    "treatment room adjacent to crew accommodation; class "
                    "and flag approval required"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "safety failure contradicting classification rules — "
                "hydrogen's LEL in air is 4 percent and it stratifies "
                "upward; marine electrolytic BWMS practice (class society "
                "and USCG-accepted designs) requires FORCED ventilation of "
                "the electrolyzer enclosure and monitored tank headspace "
                "with LEL detectors interlocked to the power supply, "
                "because turbulent dilution cannot bound stagnant-zone "
                "accumulation under beam-roll conditions; the candidate's "
                "'safe by turbulence' claim contradicts the required safety "
                "case and leaves the crew-accommodation-adjacent room "
                "unclassified for an explosive-gas hazard"),
            "expected_kill_surface": "regulatory_incompatibility",
            "expected_defect_in_basis": [
                "hydrogen", "flammab", "LEL", "ventil", "stratif",
                "class", "detect",
            ],
            "ground_truth_basis": (
                "H2 off-gas handling is the defining safety engineering "
                "problem of marine electrochlorination; every accepted "
                "design carries forced extraction + LEL interlocks; the "
                "candidate explicitly removes them and substitutes an "
                "unbounded dilution argument"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c10():
    return {
        "case_id": "a2dev-10-jacket-heat-hold-dependency",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "HIDDEN_DEPENDENCY",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-10-jacket-heat-40c-2h",
            "mechanism": (
                "thermal ballast treatment using main-engine jacket cooling "
                "water (85 C) in a shell-and-tube exchanger that heats the "
                "ballast stream to 40 C with a 2 h hold at temperature, "
                "thermally inactivating zooplankton and phytoplankton "
                "(bench: 3.1-log at 40 C / 2 h across test taxa); waste "
                "heat makes operating cost near zero"),
            "intervention": (
                "plate-and-shell heat exchanger on the ballast main with "
                "three-way temperature control; the ballast tank is the "
                "hold volume; tank tops insulated during the retrofit"),
            "predicted_effect": (
                "3.1-log organism inactivation per ballast voyage via "
                "40 C / 2 h thermal hold, at near-zero operating cost"),
            "testable_prediction": (
                "tank-trial thermography confirms >=2 h at 40 C in the "
                "coldest tank during ballast passage"),
            "novel_design_variable": (
                "hold-temperature/duration trade enabled by free waste "
                "heat"),
            "known_failure_modes": [
                "steel tank walls lose heat to ambient seawater",
                "port ballast-up precedes the main-engine passage",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "fleet profile: voyages 1-10 days, ballast-up IN PORT "
                    "(main engine off), seawater 2-30 C, steel tanks "
                    "6,500 m3 total"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "hidden dependency — the thermal hold depends on three "
                "unstated conditions: (i) the main engine must RUN during "
                "treatment, but ballast-up happens in port on auxiliary "
                "power only (jacket water from the main engine is "
                "unavailable exactly when treatment must occur); (ii) the "
                "tank must RETAIN 40 C for 2 h, but an uninsulated-"
                "except-tops steel tank loses that gradient to 2-30 C "
                "seawater in roughly 1-2 h; (iii) the voyage must last "
                "longer than treatment, which short coastal runs may not "
                "allow; the source demonstration context (continuous "
                "main-engine operation, warm water, long ballast passages) "
                "transfers none of these conditions to the declared fleet "
                "profile — the mechanism is real in its source context and "
                "unavailable in the target context"),
            "expected_kill_surface": "weak_transfer",
            "expected_defect_in_basis": [
                "hold", "jacket", "port", "heat loss", "retention",
                "engine", "voyage", "auxiliary",
            ],
            "ground_truth_basis": (
                "The dependency chain (engine running -> 85 C jacket water "
                "-> 40 C stream -> 2 h tank hold) breaks at the first link "
                "in the declared operating profile; the transfer from the "
                "demonstration context to the target context fails on "
                "unstated operating conditions — the hidden-dependency "
                "class Art. L names"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c11():
    return {
        "case_id": "a2dev-11-pinned-specific-disclosure",
        "category": "TRUE_POSITIVE_seeded_defect",
        "seed_class": "KNOWN_ART_REDISCOVERY",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-11-disclosed-architecture",
            "mechanism": (
                "a ballast treatment system comprising full-flow automatic "
                "backwash filtration to 40 um followed by medium-pressure "
                "UV irradiation with closed-loop dose control based on a "
                "measured UVT254 signal and flow, with a hydrocyclone "
                "pre-separator ahead of the screen and backwash reject "
                "returned to the sea chest"),
            "intervention": (
                "the disclosed architecture at 350 m3/h in the 14 m2 "
                "treatment room, with the standard marine PLC and "
                "compliance logging"),
            "predicted_effect": (
                "D-2 compliance at rated flow with dose compensation "
                "across the uptake-port envelope"),
            "testable_prediction": (
                "land-based G8 test at rated flow shows D-2 compliance "
                "across the test-water matrix"),
            "novel_design_variable": (
                "the hydrocyclone pre-separator position ahead of the "
                "screen"),
            "known_failure_modes": [
                "backwash reject load at high turbidity",
                "lamp aging between service intervals",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "fleet uptake envelope; 120 kW margin; 14 m2 room"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "known-art rediscovery — the claimed configuration is the "
                "shipped, type-approved BWMS architecture and is disclosed "
                "in the pinned prior-art record (prior_art_state = "
                "SPECIFIC_DISCLOSURE); with the disclosure pinned, a "
                "PRIOR_ART kill is legitimate and the prior-art firewall "
                "correctly does NOT fire (the firewall only protects "
                "non-kill states); rediscovery of the disclosed combination "
                "adds no distinguishing technical feature"),
            "expected_kill_surface": "prior_art",
            "expected_defect_in_basis": [
                "disclosed", "known", "type-approved", "combination",
                "prior",
            ],
            "ground_truth_basis": (
                "This case pins prior_art_state = SPECIFIC_DISCLOSURE as "
                "part of the frozen case spec (ground truth authored before "
                "any run); it measures the gauntlet's kill path WITH a "
                "kill-state prior-art input, the exact path the R489 "
                "composition finding showed drives terminal rejections"),
            "prior_art_state": "SPECIFIC_DISCLOSURE",
        },
    }


CASES_A = [_c01, _c02, _c03, _c04, _c05, _c06, _c07, _c08, _c09, _c10,
           _c11]

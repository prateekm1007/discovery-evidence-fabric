"""R492 — A2 DEV calibration corpus, cases 12-21 (controls and traps).

Same authorship discipline as cases_a (Art. L / Art. LIX): ground truth
authored from engineering reasoning before any attacker run on this corpus.
"""


def _c12():
    return {
        "case_id": "a2dev-12-nitrogen-stripping-hypoxia",
        "category": "TRUE_NEGATIVE_clean_control",
        "seed_class": "CLEAN_CONTROL",
        "control": True,
        "candidate": {
            "candidate_id": "a2dev-12-n2-stripping-hypoxia",
            "mechanism": (
                "in-tank nitrogen sparging through the existing inert-gas "
                "main with distributed microporous diffusers drops dissolved "
                "oxygen below 0.5 mg/L and holds it for the ballast voyage; "
                "sustained hypoxia inactivates obligately aerobic zooplankton "
                "and phytoplankton (replicate tank trials: 3.4-log for >=50 "
                "um organisms over 24 h at 12 C); dissolved-O2 closed-loop "
                "control with four sensors per tank keeps the setpoint "
                "without overdosing; operation stays inside the existing "
                "inert-gas system pressure envelope"),
            "intervention": (
                "N2 sparging grid per tank fed from the ship's inert-gas/"
                "nitrogen generator via a class-approved spool piece; "
                "dissolved-O2 sensor array with PLC control; voyage-length "
                "dependency declared and checked at voyage planning"),
            "predicted_effect": (
                ">=3-log inactivation of >=50 um aerobic organisms over "
                "voyages >= 24 h (fleet profile: 1-10 days), measured in "
                "replicate tank trials at 12 C and 20 C"),
            "testable_prediction": (
                "tank trials at two temperatures show the >=3-log inactivation "
                "with dissolved O2 held below 0.5 mg/L for 24 h"),
            "novel_design_variable": (
                "diffuser placement against tank geometry to eliminate "
                "oxygenated dead zones"),
            "known_failure_modes": [
                "resting cysts and some benthic taxa tolerate hypoxia "
                "(declared out of scope for the >=50 um compliance fraction "
                "as measured)",
                "voyages shorter than 24 h do not reach the full dose "
                "(declared; port pair planning rule covers them)",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "declared dependency: ballast voyage >= 24 h for full "
                    "dose; N2 generation capacity inside existing IG "
                    "envelope; no crew chemical handling"),
            },
        },
        "evidence_items": [
            {
                "id": "ev:tank-trial-hypoxia",
                "title": (
                    "Replicate 40 m3 tank trials: 3.4-log mean inactivation "
                    "of >=50 um organisms at 24 h with dissolved O2 held at "
                    "0.4-0.5 mg/L; 3.1-log at 12 C, 3.7-log at 20 C; "
                    "recovery attempts after discharge showed no "
                    "re-observation of stained-dead taxa"),
            },
        ],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "PASSED",
            "defect_class": None,
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": (
                "Hypoxia inactivation is physically real (measured, "
                "replicated), the effect is scoped with declared "
                "dependencies (voyage >= 24 h, aerobic taxa) that match the "
                "fleet profile (1-10 day voyages), the failure modes are "
                "honestly declared, and the equipment path (inert gas, "
                "sensors) is ship-standard; every claim binds to the "
                "provided tank-trial evidence"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c13():
    return {
        "case_id": "a2dev-13-daf-recirc-uv",
        "category": "TRUE_NEGATIVE_clean_control",
        "seed_class": "CLEAN_CONTROL",
        "control": True,
        "candidate": {
            "candidate_id": "a2dev-13-daf-recirc-uv",
            "mechanism": (
                "dissolved-air flotation (DAF) side-stream removes the "
                "buoyant and particle-bound fraction of the >=50 um "
                "organisms (skimmer handles floated concentrate) while a "
                "compact 90 m3/h UV-C loop recirculates the tank volume "
                "over the voyage, accumulating dose on the 10-50 um "
                "fraction that DAF does not capture; total electrical load "
                "22 kW (DAF + UV loop) stays inside the 120 kW margin"),
            "intervention": (
                "DAF package (90 m3/h side-stream, saturator + skimmer) "
                "plus a 90 m3/h UV recirculation ring per tank pair; "
                "operation sequenced by the existing ballast PLC"),
            "predicted_effect": (
                "combined removal: measured 2.1-log for >=50 um from the "
                "DAF stage plus accumulated UV dose on recirculation "
                "covering the 10-50 um fraction over voyages >= 3 days; "
                "claims are fraction-specific and voyage-length-scoped"),
            "testable_prediction": (
                "pilot skid at 90 m3/h shows the 2.1-log DAF removal on "
                "natural assemblages and the recirculation model's "
                "accumulated dose matches tank-trial inactivation"),
            "novel_design_variable": (
                "the division of labor: physical flotation for the large "
                "fraction, accumulated recirculation dose for the small "
                "fraction"),
            "known_failure_modes": [
                "skimmer concentrate needs managed disposal at sea or "
                "shore reception",
                "DAF performance degrades at very low salinity (bubble "
                "size stability)",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "declared dependency: recirculation dose accrues over "
                    "voyage time (>= 3 days for the 10-50 um claim); "
                    "salinity >= 8 PSU for DAF stability"),
            },
        },
        "evidence_items": [
            {
                "id": "ev:daf-pilot",
                "title": (
                    "DAF pilot on natural assemblages: 2.1-log removal of "
                    ">=50 um organisms at 90 m3/h, 0.9-log for 10-50 um; "
                    "UV loop dose-accumulation model validated against "
                    "tank trials over 72 h"),
            },
        ],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "PASSED",
            "defect_class": None,
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": (
                "Both sub-mechanisms are real and measured (flotation "
                "removal of buoyant/particle-bound organisms; accumulated "
                "UV dose on recirculation), the claims are fraction- and "
                "voyage-scoped, the failure modes are declared, and the "
                "energy and space budget fits the declared constraints; "
                "the design division of labor is non-trivial rather than "
                "a repackaging of the shipped filter+UV baseline"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c14():
    return {
        "case_id": "a2dev-14-electrochlor-with-safety-case",
        "category": "TRUE_NEGATIVE_clean_control",
        "seed_class": "CLEAN_CONTROL",
        "control": True,
        "candidate": {
            "candidate_id": "a2dev-14-ec-full-safety-case",
            "mechanism": (
                "electrochlorination skid generates 10-12 mg/L TRO at "
                "uptake with a >= 4 h in-tank dwell (fleet voyage profile "
                "supports it); discharge-side neutralization with sealed "
                "sodium-thiosulfate dosing brings TRO below 0.2 mg/L, "
                "verified by an inline amperometric sensor before overboard "
                "discharge; hydrogen is handled by forced extraction at 12 "
                "air changes per hour from the electrolyzer enclosure and "
                "monitored tank headspaces, with dual LEL detectors "
                "interlocked to trip the rectifier at 20 percent LEL; the "
                "unit is class-type-approved"),
            "intervention": (
                "type-approved electrolyzer (110 kW point, inside the 120 kW "
                "margin), sealed neutralization skid, forced ventilation "
                "kit, LEL detection and interlocks, TRO neutralization "
                "verified before discharge"),
            "predicted_effect": (
                "3-log+ organism inactivation at 10-12 mg/L TRO with >= 4 h "
                "dwell; discharge TRO below 0.2 mg/L; hydrogen below 25 "
                "percent LEL by forced extraction, monitored"),
            "testable_prediction": (
                "full-scale land-based G8 test shows D-2 compliance and "
                "the hydrogen monitoring log stays below the interlock "
                "threshold across all operating modes"),
            "novel_design_variable": (
                "the TRO-neutralization-verified-before-discharge loop "
                "coupled to the fleet's short-voyage dwell schedule"),
            "known_failure_modes": [
                "neutralization overdosing leaves thiosulfate residual",
                "electrode replacement at 5-year interval",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "dwell >= 4 h per fleet voyage profile; sealed dosing "
                    "only (zero crew chemical handling); 120 kW margin"),
            },
        },
        "evidence_items": [
            {
                "id": "ev:ec-g8",
                "title": (
                    "Land-based G8 test of the identical unit: D-2 "
                    "compliance across all test waters at >= 4 h dwell; "
                    "discharge TRO 0.1-0.15 mg/L; hydrogen monitoring log "
                    "max 12 percent LEL with forced extraction"),
            },
        ],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "PASSED",
            "defect_class": None,
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": (
                "This is the mirror of the safety-failure case: the same "
                "technology WITH the complete hydrogen safety case (forced "
                "extraction, LEL interlocks), verified neutralization "
                "before discharge, sealed dosing respecting the constraint "
                "set, evidence binding every claim; a properly engineered "
                "electrolytic system must not be killed for the class's "
                "generic hydrogen hazard"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c15():
    return {
        "case_id": "a2dev-15-sediment-baffle-suction-well",
        "category": "TRUE_NEGATIVE_clean_control",
        "seed_class": "CLEAN_CONTROL",
        "control": True,
        "candidate": {
            "candidate_id": "a2dev-15-baffle-suction-well",
            "mechanism": (
                "internal flow baffles and a raised, extended suction well "
                "retrofitted into the two peak-risk ballast tanks so that "
                "discharge suction draws from above the settled sediment "
                "layer instead of through it; tank trials measured a 70 "
                "percent reduction in re-suspended solids and "
                "sediment-dwelling organism counts in discharge samples at "
                "discharge start — the fleet's dominant D-2 exceedance "
                "mode, which the treatment train alone does not cover"),
            "intervention": (
                "welded baffle sets + suction-well extensions in two tanks "
                "(drydock work, class-approved detail design), no added "
                "power, no chemicals, no organism kill claim outside the "
                "measured scope"),
            "predicted_effect": (
                "70 percent reduction of re-suspended sediment and "
                "sediment-borne organisms in the discharge's opening phase "
                "(measured), removing the dominant exceedance contribution "
                "on the fleet's historical sampling record"),
            "testable_prediction": (
                "paired tank discharge sampling with and without the baffle "
                "retrofit shows the ~70 percent reduction at discharge "
                "start"),
            "novel_design_variable": (
                "suction-well height against the measured sediment "
                "re-suspension threshold for the tank's flow pattern"),
            "known_failure_modes": [
                "does not treat suspended organisms in the water column "
                "(out of declared scope)",
                "sediment accumulation rate still requires periodic "
                "removal",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "claim scoped to sediment re-suspension at discharge "
                    "start; complements (does not replace) the D-2 "
                    "treatment train; drydock work only"),
            },
        },
        "evidence_items": [
            {
                "id": "ev:paired-sampling",
                "title": (
                    "Paired discharge sampling campaign: opening-phase "
                    "re-suspended solids 410 mg/L vs 120 mg/L with the "
                    "baffle retrofit; sediment-dwelling harpacticoid counts "
                    "in discharge 68-74 percent lower across six pairs"),
            },
        ],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "PASSED",
            "defect_class": None,
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": (
                "The claim is narrow, measured, and honest: it addresses a "
                "documented real failure mode (sediment re-suspension "
                "driving discharge-sampling exceedances) inside its "
                "declared scope, with paired-sampling evidence and no "
                "organism-kill overreach; scope-honest engineering "
                "measures must not be killed for the problem they "
                "deliberately do not claim"),
            "prior_art_state": "NO_MATCH_FOUND",
        },
    }


def _c16():
    return {
        "case_id": "a2dev-16-led-uv-economics",
        "category": "NEAR_MISS_real_effect_fatal_magnitude",
        "seed_class": "NEAR_MISS",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-16-led-uv-bank",
            "mechanism": (
                "UV-C LED bank (265 nm) replaces the medium-pressure lamp "
                "chamber: instant-on (no warm-up interlock losses), "
                "mercury-free (simplifies disposal), and wavelength-tunable "
                "dose delivery; real physics: 265 nm is near the germicidal "
                "action optimum, so the required fluence per log is lower "
                "than MP-UV broadband normalization suggests"),
            "intervention": (
                "modular LED array wall (8 x 3 kW optical modules) in the "
                "ballast main at 350 m3/h with per-module intensity "
                "control keyed to UVT254"),
            "predicted_effect": (
                "equal-or-better D-2 compliance with instant-on operation "
                "and mercury elimination at rated flow"),
            "testable_prediction": (
                "bench fluence-response at 265 nm shows the per-log fluence "
                "advantage over the MP-UV lamp it replaces"),
            "novel_design_variable": (
                "per-module intensity modulation against real-time UVT"),
            "known_failure_modes": [
                "junction temperature derates LED lifetime in engine-room "
                "ambient",
                "optical fouling of sapphire windows",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "engine-room ambient up to 55 C; 120 kW margin; fleet "
                    "uptake UVT 38-62 percent"),
            },
        },
        "evidence_items": [
            {
                "id": "ev:led-lifetime-derate",
                "title": (
                    "Manufacturer derating curves: at 55 C ambient and the "
                    "required drive current the LED bank's useful life is "
                    "3,000-5,000 h against ~8,000 h/year flow operation; "
                    "wall-plug efficiency at 265 nm is 35-40 percent, so "
                    "the 8-12 kW optical requirement draws 25-35 kW "
                    "continuous with chiller load"),
            },
        ],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "near-miss: the mechanism is real (265 nm germicidal "
                "advantage, instant-on, mercury-free) but the magnitude is "
                "fatal — at fleet UVT (38-62 percent) the required optical "
                "power is 8-12 kW, wall-plug 35-40 percent puts the draw at "
                "25-35 kW plus chiller, and the 3,000-5,000 h bank life at "
                "engine-room ambient means 1-2 full bank replacements per "
                "year; capital and lifetime cost per m3 land 5-7x the "
                "MP-UV baseline it replaces — a real effect at a fatal "
                "magnitude, not a wrong mechanism"),
            "expected_kill_surface": "engineering_infeasibility",
            "expected_defect_in_basis": [
                "cost", "capex", "lifetime", "replacement", "per m3",
                "econom", "5", "7",
            ],
            "ground_truth_basis": (
                "The near-miss discipline: a kill counts as detected only "
                "when the basis engages the magnitude (cost, lifetime, "
                "replacement cadence, per-m3 economics), not merely the "
                "category; a kill that attacks the UV mechanism itself "
                "(which is real) without engaging the numbers misses the "
                "near-miss"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c17():
    return {
        "case_id": "a2dev-17-two-point-nine-log-margin",
        "category": "NEAR_MISS_real_effect_fatal_magnitude",
        "seed_class": "NEAR_MISS",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-17-filter-uv-2p9log",
            "mechanism": (
                "40 um automatic backwash screen plus medium-pressure UV "
                "with UVT-keyed dose control; the land-based G8 test "
                "measured 2.9-log mean inactivation for >=50 um organisms "
                "at rated flow — a real, measured effect from a sound "
                "architecture"),
            "intervention": (
                "the standard filter+UV train at 350 m3/h in the 14 m2 "
                "treatment room"),
            "predicted_effect": (
                "2.9-log measured inactivation of >=50 um organisms at "
                "rated flow across the test-water matrix"),
            "testable_prediction": (
                "the G8 replicate mean stays at 2.9-log +/- 0.3 across "
                "test waters"),
            "novel_design_variable": (
                "UV dose ceiling raised to the lamp-power limit inside the "
                "120 kW margin"),
            "known_failure_modes": [
                "seasonal zooplankton abundance peaks at uptake ports",
                "lamp aging between replacements",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "fleet uptake ports with seasonal >=50 um abundance "
                    "1,000-3,000 ind/m3 (declared in the common problem "
                    "context)"),
            },
        },
        "evidence_items": [
            {
                "id": "ev:seasonal-abundance",
                "title": (
                    "Seasonal zooplankton survey at the four uptake ports: "
                    "May-June peaks of 2,400 ind/m3 (95 percent CI "
                    "1,800-3,100) for >=50 um; the D-2 limit of 10 viable "
                    "ind/m3 therefore requires >= 3.0-log equivalent "
                    "reduction at seasonal peak uptake"),
            },
        ],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "near-miss on compliance margin: the measured 2.9-log mean "
                "is real but sits below the >=3.0-log equivalent the "
                "seasonal peak abundance (2,400 ind/m3, CI 1,800-3,100) "
                "requires against the D-2 limit of 10 ind/m3, with the CI's "
                "upper end demanding ~3.1-log; the candidate's own evidence "
                "shows the margin is negative in the season that dominates "
                "the fleet's discharge-sampling exposure — real effect, "
                "fatal margin"),
            "expected_kill_surface": "contradiction",
            "expected_defect_in_basis": [
                "margin", "2.9", "3.0", "seasonal", "peak", "abundance",
                "CI",
            ],
            "ground_truth_basis": (
                "The near-miss discipline with evidence binding: the kill "
                "must engage the numbers (2.9 vs the 3.0-log requirement "
                "the provided seasonal survey sets) — arithmetic on the "
                "case's own evidence, not a generic 'might not comply'"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c18():
    return {
        "case_id": "a2dev-18-freshwater-scope-declared",
        "category": "SCOPE_CONFLICT_declared_boundary_trap",
        "seed_class": "SCOPE_CONFLICT",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-18-ec-freshwater-scope",
            "mechanism": (
                "electrochlorination sized and validated for salinity "
                ">= 8 PSU (conductivity-limited cell design); below 5 PSU "
                "the system is explicitly NON-OPERATIONAL by declared "
                "design, enforced by an automatic salinity interlock that "
                "stops the rectifier; freshwater-uptake voyages (river "
                "berths, salinity < 5 PSU) follow the declared operational "
                "procedure: full mid-ocean ballast exchange per the flag "
                "administration's approved exchange plan"),
            "intervention": (
                "electrolyzer skid with salinity interlock; voyage-planning "
                "rule embedded in the ballast PLC; the fleet's river-berth "
                "calls are 11 percent of ballast operations (declared)"),
            "predicted_effect": (
                "D-2 compliance on all >= 8 PSU uptake operations (89 "
                "percent of fleet ballast moves); < 5 PSU uptake handled "
                "by the declared exchange procedure"),
            "testable_prediction": (
                "interlock trips below 5 PSU in tank trials; G8-style "
                "tests at 8, 20, 36 PSU show compliance at >= 4 h dwell"),
            "novel_design_variable": (
                "the interlocked salinity scope boundary with the declared "
                "operational fallback"),
            "known_failure_modes": [
                "mid-ocean exchange on short river runs extends voyage "
                "time",
                "interlock nuisance trips at brackish gradients",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "DECLARED SCOPE: salinity >= 8 PSU for the treatment "
                    "train; < 5 PSU uptake uses the declared exchange "
                    "fallback; the system does not claim freshwater "
                    "treatment"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "PASSED",
            "defect_class": None,
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": (
                "Scope-conflict trap: the candidate DECLARES its boundary "
                "(salinity >= 8 PSU) and a compliant operational fallback "
                "for the out-of-scope condition; a kill that attacks it "
                "for failing at 0-4 PSU freshwater attacks a boundary the "
                "candidate never claims and for which a declared compliant "
                "procedure exists — that is a SCOPE_MISMATCH false kill, "
                "not a detection"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c19():
    return {
        "case_id": "a2dev-19-two-tank-phase-in-scope",
        "category": "SCOPE_CONFLICT_declared_boundary_trap",
        "seed_class": "SCOPE_CONFLICT",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-19-peak-tank-phase-in",
            "mechanism": (
                "the BWMS retrofit treats the two peak-risk tanks (2,800 "
                "m3 combined, 43 percent of capacity, covering 78 percent "
                "of ballast movements on the fleet's trade) with the full "
                "treatment train; the two wing tanks are DECLARED "
                "non-retrofittable this phase (no space in the treatment "
                "room envelope) and continue the flag-approved D-1 "
                "exchange procedure for the administration's approved "
                "phase-in period, after which the wing tanks receive a "
                "second-phase unit"),
            "intervention": (
                "treatment train sized to the peak tanks in the 14 m2 "
                "room; PLC voyage-planning rule routes wing-tank ballast "
                "to the declared exchange procedure; phase-in documented "
                "with the flag administration"),
            "predicted_effect": (
                "D-2 compliance on the peak-tank ballast movements now "
                "(78 percent of movements) and a declared, "
                "administration-approved path for the remainder"),
            "testable_prediction": (
                "compliance sampling on peak-tank discharges shows D-2 "
                "pass; wing-tank movements log the declared exchange "
                "procedure"),
            "novel_design_variable": (
                "risk-weighted phase-in ordering by tank (peak-risk "
                "first) under the approved phase-in"),
            "known_failure_modes": [
                "phase-in extension risk if the second-phase unit slips",
                "operational discipline required for the tank-routing "
                "rule",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "DECLARED SCOPE: two peak-risk tanks this phase; wing "
                    "tanks on the declared approved procedure during "
                    "phase-in; no claim of full-fleet D-2 coverage this "
                    "phase"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_GOOD",
            "expected_final": "PASSED",
            "defect_class": None,
            "expected_kill_surface": None,
            "expected_defect_in_basis": [],
            "ground_truth_basis": (
                "Scope-conflict trap: the candidate declares exactly which "
                "tanks it treats and which it does not, with the "
                "administration-approved procedure covering the rest; a "
                "kill on 'does not treat all four tanks' attacks the "
                "declared boundary and the declared compliant fallback — "
                "SCOPE_MISMATCH false kill, not a detection"),
            "prior_art_state": "TOPICAL_RELATED",
        },
    }


def _c20():
    return {
        "case_id": "a2dev-20-empty-evidence-absence",
        "category": "MALFORMED_MISSING_EVIDENCE",
        "seed_class": "MALFORMED_MISSING_EVIDENCE",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-20-seachest-led-ring",
            "mechanism": (
                "a pulsed UV-C LED ring mounted at the sea-chest grating "
                "inactivates entrained organisms at the moment of uptake "
                "with a claimed 4-log kill in the 0.2 s transit through "
                "the ring, eliminating the need for any downstream "
                "treatment"),
            "intervention": (
                "pulsed LED ring at the sea chest (12 kW pulse supply), "
                "no other treatment"),
            "predicted_effect": (
                "4-log kill of entrained organisms at uptake; D-2 "
                "compliance with no downstream treatment"),
            "testable_prediction": (
                "a sea-chest-scale rig shows the 4-log single-pass kill "
                "at the grating flow velocity"),
            "novel_design_variable": (
                "ring placement at the grating (treatment at first "
                "contact)"),
            "known_failure_modes": [
                "flow velocity at the grating varies with pump state",
                "biofouling of the ring optics",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "grating transit 0.1-0.3 s; turbidity up to 80 NTU"),
            },
        },
        "evidence_items": [],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "unsupported mechanism with ZERO supporting evidence: the "
                "4-log claim at 0.2 s transit in up-to-80-NTU water has no "
                "evidence of any kind; an UNSUPPORTED_MECHANISM kill is "
                "honest; but a CONTRADICTION kill is the typed false-kill "
                "class ABSENCE_AS_CONTRADICTION — there is nothing to "
                "contradict (Art. XXI.3/XXV discipline)"),
            "expected_kill_surface": "unsupported_mechanism",
            "expected_defect_in_basis": [],
            "scoring_discipline": (
                "any CONTRADICTION-dimension kill on this case is the "
                "typed false-kill class ABSENCE_AS_CONTRADICTION; "
                "UNSUPPORTED_MECHANISM kill is honest; overall KILLED or "
                "PASSED both recorded, the discipline binds the "
                "contradiction dimension only"),
            "ground_truth_basis": (
                "Empty evidence packet mirrors sealed-corpus cal-20 class "
                "for the A2 gauntlet: absence of evidence must surface as "
                "unsupported (honest) or pass-through, never as "
                "'contradicted by the evidence'"),
            "prior_art_state": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
        },
    }


def _c21():
    return {
        "case_id": "a2dev-21-garbled-evidence-absence",
        "category": "MALFORMED_MISSING_EVIDENCE",
        "seed_class": "MALFORMED_MISSING_EVIDENCE",
        "control": False,
        "candidate": {
            "candidate_id": "a2dev-21-garbled-survey-margin",
            "mechanism": (
                "40 um backwash screen plus UV with UVT-keyed dose "
                "control claiming 3.2-log inactivation of >=50 um "
                "organisms with a '95 percent compliance margin computed "
                "from the uptake-port survey'"),
            "intervention": (
                "the filter+UV train at 350 m3/h with the survey-derived "
                "margin claim"),
            "predicted_effect": (
                "3.2-log inactivation with 95 percent compliance margin "
                "derived from the cited survey"),
            "testable_prediction": (
                "the margin computation from the survey data is "
                "reproducible by an independent analyst"),
            "novel_design_variable": (
                "survey-derived compliance margin method"),
            "known_failure_modes": [
                "survey data quality varies by port",
                "seasonal abundance peaks",
            ],
            "constraint_set": {
                "boundary_conditions": (
                    "fleet uptake envelope; seasonal abundance peaks at "
                    "the four uptake ports"),
            },
        },
        "evidence_items": [
            {
                "id": "ev:plankton-survey-2025",
                "title": (
                    "Seasonal zooplankton abundance at the four uptake "
                    "ports: peak 2,400 ind/m3 in May-June (95 percent CI "
                    "UNPARSED 1800-3100, sample batch #REF-04), >=50 um "
                    "fraction 62 percent +/- units-missing; 10-50 um "
                    "fraction counts below instrument LOD (LOD value not "
                    "recorded); report tables truncated at page 41"),
            },
        ],
        "ground_truth": {
            "label": "KNOWN_BAD",
            "expected_final": "KILLED",
            "defect_class": (
                "unsupported margin claim over UNUSABLE evidence: the "
                "cited survey is garbled (unparsed CI, missing units, "
                "unrecorded LOD, truncated tables), so the claimed '95 "
                "percent compliance margin' cannot be reconstructed or "
                "verified from the evidence as given — the margin claim "
                "is unsupported; a CONTRADICTION kill that pretends to "
                "bind to these numbers is the typed false-kill class "
                "ABSENCE_AS_CONTRADICTION (binding to unusable numbers is "
                "still absence of usable evidence); an "
                "UNSUPPORTED_MECHANISM kill is honest"),
            "expected_kill_surface": "unsupported_mechanism",
            "expected_defect_in_basis": [],
            "scoring_discipline": (
                "any CONTRADICTION-dimension kill whose claimed basis "
                "binds to the garbled numbers is the typed false-kill "
                "class ABSENCE_AS_CONTRADICTION; the discipline binds the "
                "contradiction dimension only"),
            "ground_truth_basis": (
                "Mirrors sealed-corpus cal-21 (malformed evidence) for the "
                "A2 gauntlet: usable-evidence absence must not become "
                "contradiction"),
            "prior_art_state": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
        },
    }


CASES_B = [_c12, _c13, _c14, _c15, _c16, _c17, _c18, _c19, _c20, _c21]

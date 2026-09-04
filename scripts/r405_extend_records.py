#!/usr/bin/env python3
"""R405 — extend the LEAD_PORTFOLIO_4 canonical records with the executed
$0 roadmap items from the external audit response.

Every extension carries: provenance (external-audit proposal / web-search
verification / computation), an honest evidence class (Art. XXVII), and an
owner pre-registration gate where the item is a threshold or decision.
Purely additive: no existing field is deleted or rewritten; extensions land
in an `r405_extensions` container (or a standalone new artifact file).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load(rel):
    return json.loads((REPO / rel).read_text())


def save(rel, obj):
    (REPO / rel).write_text(json.dumps(obj, sort_keys=True,
                                       ensure_ascii=False, indent=1) + "\n")


def ext(obj, key, value):
    obj.setdefault("r405_extensions", {})[key] = value


def main():
    audit_prov = {
        "provenance": "R405 external audit (Claude Sonnet 4.6, SHA "
                      "135fd74f) — 'Lead Portfolio 4 — External Audit & "
                      "Elite Package Roadmap', 2026-09-04",
        "response_record": "R405/EXTERNAL_AUDIT_RESPONSE.md",
    }

    # =====================================================================
    # P04 — DECISIVE_EXPERIMENT: Q_min reference, common-cause protocol,
    # cost basis (REPORTED)
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P04/DECISIVE_EXPERIMENT.json"
    d = load(p)
    ext(d, "q_min_declaration", {
        "status": "RANGE DECLARED (R405); single operating value is "
                  "owner-gated pre-registration (Art. XXVII)",
        "record": "LEAD_PORTFOLIO_4/P04/QMIN_FLOOR_FLOW_CALCULATION.json",
        "range": "0.2-0.4 mL/min (12-24 mL/hr)",
        "threshold_class": "PHYSIOLOGICAL",
        "source_class": "EXTERNAL_PRECEDENT (web-search-verified citations: "
                        "Tariq et al. 2023 PMC10409822; Silverberg et al. "
                        "2002, J Neurosurg 97(6):1271)",
        "external_audit_unit_error_flagged": "the audit proposed "
            "'0.3-0.4 mL/hr' — a 60x unit error (CSF production is "
            "per-MINUTE); never adopted; see the response record Part 2.2",
        "consequence": "floor conductance exceeds Q_min by 6-12x at minimum "
                       "head in both geometries, so the pass rule's "
                       "discriminating power sits in PARTIAL common-cause "
                       "obstruction (~47% effective-diameter reduction "
                       "tolerance, computed)",
    })
    ext(d, "common_cause_quantified_arm", {
        "protocol": "introduce the obstruction simulant upstream of BOTH "
                    "lumen openings simultaneously; measure floor-lumen "
                    "flow independently (secondary flow sensor on an "
                    "isolated floor-lumen port) across the full "
                    "pressure/flow matrix",
        "kill_rule": "KILL if the simulant occludes the floor lumen in "
                     ">= 90% of the tested pressure/flow cases",
        "threshold_provenance": {
            "value": 90, "unit": "percent of tested cases",
            "class": "ENGINEERING",
            "origin": audit_prov,
            "justification": "the audit's quantification of the package's "
                             "own recorded critical kill condition; the "
                             "pre-R405 record carried the condition "
                             "qualitatively",
            "uncertainty": "the 90% cut is a proposed engineering bound — "
                           "owner pre-registration required before the run "
                           "(never silently promoted to CLINICAL)",
            "owner_gate": "REQUIRED",
        },
    })
    ext(d, "cost_basis_r405", {
        "status": "REPORTED ESTIMATE (external auditor's itemization; owner "
                  "confirmation required — class ENGINEERING_ESTIMATE)",
        "range": "$11-25K",
        "itemization_reported": [
            "bench flow loop $2-5K (pressure reservoir, column stand, "
            "calibrated flowmeter, temperature bath)",
            "dual-lumen extrusion samples $3-8K (10-20 medical-prototype "
            "pieces)",
            "obstruction simulants $1-2K (fibrin gel, tissue analog)",
            "personnel $5-10K (technician, 4-8 weeks)",
        ],
        "note": "replaces 'UNESTIMATED' with a REPORTED range; not an owner "
                "estimate; the recorded sibling anchor remains P-24's "
                "$15K/8wk",
    })
    save(p, d)

    # =====================================================================
    # P04 — NOVELTY_ASSESSMENT: claim map for US20240207499A1
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P04/NOVELTY_ASSESSMENT.json"
    d = load(p)
    ext(d, "closest_prior_claim_map_US20240207499A1", {
        "differentiation_argument": [
            "The closest specific-mechanism reference (US20240207499A1, "
            "granted as US11865241B2 'Sensor monitoring system for "
            "in-dwelling catheter based treatments') is anchored by its "
            "own claim language on SENSING: dependent claims recite 'a "
            "flow sensor coupled to' the conduit and 'a limited-use "
            "sensor configured to releasably engage' it.",
            "P-07's floor lumen is a passive geometric conductance split "
            "in the extrusion itself — no sensor, no monitoring device, "
            "no electronics, no flow measurement of any kind.",
            "The reference therefore does not read on a passive "
            "low-conductance floor lumen that maintains drainage under "
            "primary obstruction; its problem (monitoring drainage) and "
            "its solution (retrofit sensors) are disjoint from this "
            "package's problem (drainage failure under obstruction) and "
            "solution (geometry).",
        ],
        "evidence_basis": [
            "recorded relevance: 'Closest on the specific-mechanism query "
            "(sensor/monitoring side of in-dwelling catheters)' — this "
            "assessment file",
            "web-searched claim text (Google Patents, 2026-09-04, z-ai "
            "web_search): US11865241B2 dependent-claim language 'measuring "
            "one or more of a flow rate and total flow volume of the "
            "patient fluid using a flow sensor coupled to...' and "
            "'limited-use sensor configured to releasably engage one or "
            "more of the fluid conduit'; "
            "https://patents.google.com/patent/US11865241B2/en",
        ],
        "limits": "snippet-level evidence (Art. II honestly labeled); a "
                  "full claim chart vs independent claim 1 is owner/counsel "
                  "work; this is a differentiation argument, NOT a "
                  "patentability opinion or FTO (Art. XXVIII)",
        "origin": audit_prov,
    })
    save(p, d)

    # =====================================================================
    # P04 — BUYER_SEQUENCE: commercial anchor (REPORTED, divergent sources)
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P04/BUYER_SEQUENCE.json"
    d = load(p)
    ext(d, "commercial_anchor", {
        "status": "REPORTED ANCHOR (divergent sources disclosed; verify "
                  "before buyer presentation — owner action)",
        "class": "ROUGH_ESTIMATE / REPORTED",
        "anchors": {
            "us_shunt_surgeries_per_year": {
                "value": "36,000+",
                "source": "Hydrocephalus Association ('over 36,000 shunt "
                          "surgeries each year — one every 15 minutes'; "
                          "revision/diversion = 'nearly one third of all "
                          "neurosurgical procedures annually')",
                "verification": "web-search-verified snippet, 2026-09-04",
                "audit_figure_flagged": "the external audit's '~125,000 "
                                        "CSF shunts implanted annually "
                                        "(Isaacs et al. 2016)' was NOT "
                                        "verifiable in open sources this "
                                        "session — recorded as DISPUTED, "
                                        "not adopted",
            },
            "revision_rate_class": {
                "value": "18-54% within cohorts; 30-50% is the commonly "
                         "cited class; >=1-revision rates up to 81% in "
                         "long-horizon cohorts",
                "sources": "PMC12535486 (2025: 35.9% at 1yr, 54.3% "
                           "overall, pediatric); ScienceDirect "
                           "S1878875024016565 (2024: 17.7% adults, "
                           "communicating); Longeviti (2021: 81% >=1 "
                           "revision)",
                "verification": "web-search-verified snippets, 2026-09-04",
            },
            "revision_cost": {
                "value": "$30-60K per revision (hospital cost class)",
                "source": "external-audit figure",
                "verification": "NOT independently verified this session "
                                "(REPORTED)",
            },
        },
        "framing_reported": "the audit's prevention-economics framing "
            "(prevent 10% of revisions -> order $100M+ healthcare savings/"
            "yr) is recorded as the audit's PROPOSAL — its arithmetic "
            "requires the disputed 125k/yr and unverified $30-60K inputs "
            "before it can be presented as an estimate",
        "origin": audit_prov,
    })
    save(p, d)

    # =====================================================================
    # P04 — TECHNOLOGY_MATURITY + GEOMETRY_SEPARATION: conductance
    # correction note + NIST disposition
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P04/TECHNOLOGY_MATURITY.json"
    d = load(p)
    ext(d, "conductance_unit_correction", {
        "disclosure": "R405/UNIT_CONVERSION_DEFECT_DISCLOSURE.json",
        "effect_on_this_record": "none — this record cites only the "
                                 "restoration RATIO (0.999984) and geometry "
                                 "values, which are unaffected; the "
                                 "corrected absolute conductance (0.254 "
                                 "mL/(min*mmHg)) is recorded in "
                                 "QMIN_FLOOR_FLOW_CALCULATION.json",
    })
    save(p, d)

    p = "LEAD_PORTFOLIO_4/P04/GEOMETRY_SEPARATION.json"
    d = load(p)
    ext(d, "nist_canonical_application_disposition", {
        "state": "OWNER-GATED; AUDITOR CONFLICT RECORDED",
        "r403_position": "Applying to the buyer surface is an owner "
                         "release-chain decision (Art. XXXIX protocol), "
                         "NOT a hardening edit (this record, "
                         "valid_new_version_candidate.status)",
        "external_audit_position": "apply now through the Art. XXXIX "
                                   "protocol — 'not a new engineering "
                                   "decision, the decision was made and "
                                   "recorded'",
        "resolution": "NOT silently resolved either way (the same "
                      "discipline as the management-statement rule): both "
                      "positions are recorded verbatim; the release "
                      "protocol itself cannot run while R404/R405 are "
                      "unpushed (Art. XXXIX 5 requires both repos clean "
                      "and PUSHED before the build — the PAT is an "
                      "operator input)",
        "executable_path_when_authorized": [
            "premium_package_factory/r381/templates.py "
            "floor_lumen_diameter_mm 0.6 -> 0.5471 (design_basis updated "
            "to cite EVT-R390-NIST-WATER-VISC-310K)",
            "coordinate the physics-stage reference envelope + r397 pin "
            "in the same commit (the pin tracks the canonical value "
            "through a recorded causal mutation — nothing is weakened, "
            "nothing fails)",
            "deterministic rebuild (machinery proven by the R404 "
            "re-verification; expected model pm:115852de5865efc8 class) + "
            "G1-G9 re-run",
            "buyer release through scripts/r386_release_chain.py (owner "
            "release-chain operation)",
        ],
        "physics_note": "both geometries' corrected hydraulics are computed "
                        "in QMIN_FLOOR_FLOW_CALCULATION.json so the "
                        "decision is number-informed: the correction moves "
                        "floor flow at 10 mmHg from 220.8 to 152.7 mL/hr "
                        "catheter-segment conductance flow (both >> Q_min "
                        "12-24 mL/hr)",
    })
    save(p, d)

    # =====================================================================
    # P08 — ENERGY_BUDGET: D2 explicit arithmetic, thermal, GaAs, framing
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P08/ENERGY_BUDGET.json"
    d = load(p)
    ext(d, "d2_explicit_arithmetic_display", {
        "purpose": "the external audit's Week 1-2 item: show the D2 chain "
                   "explicitly; trace why the numbers diverge",
        "audit_reconstruction_chain": {
            "inputs": {
                "source_irradiance": {
                    "value": 100, "unit": "mW/cm2",
                    "class": "REPORTED (external-audit reconstruction — "
                             "NOT recorded data; the real external source "
                             "spec is an open owner action)"},
                "mu_eff": {
                    "value": 1.5, "unit": "cm^-1",
                    "class": "REPORTED (external audit; cited as 'Jacques "
                             "2013 mid-range at 940 nm' — full-text "
                             "verification open)"},
                "depth": {"value": 5, "unit": "mm", "class": "ASSUMPTION "
                           "(audit's soft-tissue-only path)"},
            },
            "arithmetic": "T = exp(-1.5 * 0.5) = 0.472; surface-to-implant "
                          "fluence = 100 * 0.472 = 47.2 mW/cm2; available "
                          "power = 47.2 * 0.3848 cm2 * 0.30 = 5.44 mW",
            "divergence_point": "the reconstructed 47.2 mW/cm2 at the "
                                "receiver is ~34-45x the recorded R310/R311 "
                                "fluence anchors (1.049-1.416 mW/cm2): the "
                                "audit's chain models a 5 mm SOFT-TISSUE-"
                                "ONLY path, while the recorded simulations "
                                "model the TRANSCRANIAL path (scalp+skull+"
                                "CSF layers, far higher attenuation). The "
                                "inputs are assumptions, not recorded "
                                "measurements — the display resolves the "
                                "ARITHMETIC question of D2 (why numbers "
                                "differ), not the DECISION (target vs area "
                                "vs efficiency).",
        },
        "decision_remains": "OWNER-GATED (unchanged from the R404 "
                            "classification: >= 500 uW device target vs "
                            "121-163 uW conditional band on the 0.3848 cm2 "
                            "shipped receiver)",
    })
    ext(d, "thermal_kill_boundary", {
        "structure_adopted": "pre-registered kill-boundary comparison: the "
                             "measured surface irradiance at the source "
                             "power level required for the target power "
                             "vs the applicable skin exposure limit "
                             "(ANSI Z136.1 / IEC 60825-1 class)",
        "audit_figures_reported": {
            "pulsed": "1.8 J/cm2 (audit-quoted)",
            "continuous": "0.73 W/cm2 (audit-quoted)",
            "verification": "NOT VERIFIED — the standards are paywalled; "
                            "open pages confirm ANSI Z136.1 governs skin "
                            "MPE but do not publish the table values; "
                            "owner must extract the exact MPE for 940 nm "
                            "at the declared exposure duration from the "
                            "standard text BEFORE pre-registration "
                            "(Art. XXVII: threshold provenance is "
                            "mandatory)",
        },
        "origin": audit_prov,
    })
    ext(d, "gaas_low_irradiance_efficiency_sourcing", {
        "status": "SOURCED (existence-verified; full-text verification "
                  "open)",
        "citations": [
            {"reference": "Moon et al. 2020, 'Dual-Junction GaAs "
                          "Photovoltaics for Low Irradiance Wireless "
                          "Powering of Subcutaneous Implants'",
             "verified_snippet": "Near-infrared (NIR) light provides a "
                                 "means for high power conversion "
                                 "efficiency (>30%) in millimeter-scale "
                                 "subcutaneous implantable devices",
             "retrieval": "z-ai web_search, 2026-09-04"},
            {"reference": "Zhao et al. 2023, self-powered implantable CMOS "
                          "photovoltaic cell",
             "verified_snippet": "PV cell efficiencies were 18.6% and 12% "
                                 "for an incident power intensity of 8.6 "
                                 "mW cm-2",
             "retrieval": "z-ai web_search, 2026-09-04",
             "use": "the conservative datapoint bounding the assumption "
                    "from below"},
        ],
        "effect_on_the_budget": "the ~30% efficiency class now carries a "
                                "citable external precedent for the NIR "
                                "subcutaneous-implant regime (>30% dual-"
                                "junction; 18.6% single-junction CMOS "
                                "class) — the budget's MODELLED eta "
                                "assumption is SUPPORTED at the range "
                                "level but the cell-specific value at "
                                "1-2 mW/cm2 irradiance remains unmeasured "
                                "(open owner action unchanged)",
        "origin": audit_prov,
    })
    ext(d, "power_target_framing", {
        "use_case_statement": "a 940 nm transcranial PV delivering "
                              "100-160 uW to a shunt-integrated pressure "
                              "sensor and low-duty-cycle telemetry is a "
                              "coherent use case: the implantable-device "
                              "literature places sensing/telemetry power "
                              "budgets in the uW-to-low-mW class",
        "citations": [
            {"reference": "Amar et al. 2015, 'Power Approaches for "
                          "Implantable Medical Devices' (PMC, cited 588x)",
             "retrieval": "z-ai web_search, 2026-09-04",
             "use": "the uW-scale implant power-budget anchor"},
        ],
        "audit_figures_flagged": "the audit's device-specific figures "
                                 "(SynchroMed II >= 150 uW standby; ICP "
                                 "telemetry chip 50-150 uW active) are "
                                 "REPORTED and were NOT independently "
                                 "verified this session",
        "origin": audit_prov,
    })
    save(p, d)

    # =====================================================================
    # P08 — DECISIVE_EXPERIMENT: thermal kill + cost basis
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P08/DECISIVE_EXPERIMENT.json"
    d = load(p)
    ext(d, "thermal_kill_condition_r405", {
        "rule": "KILL (physics class) if sustained irradiation at the "
                "source power level required for the target power exceeds "
                "the pre-registered skin exposure limit at the phantom "
                "entry surface: record the measured surface irradiance "
                "and compare against the declared threshold",
        "threshold_status": "STRUCTURE PRE-REGISTERED; NUMERIC THRESHOLD "
                            "OWNER-GATED (ANSI Z136.1/IEC 60825-1 values "
                            "are paywalled — see "
                            "ENERGY_BUDGET.r405_extensions."
                            "thermal_kill_boundary)",
        "origin": audit_prov,
    })
    ext(d, "cost_basis_r405", {
        "status": "REPORTED ESTIMATE (external auditor's itemization; "
                  "owner confirmation required — ENGINEERING_ESTIMATE "
                  "class)",
        "range": "$16-42K",
        "itemization_reported": [
            "940 nm laser source $5-15K", "phantom materials $1-2K",
            "calibrated photodiode triangle $3-5K",
            "GaAs PV cell samples (prototype quantities) $5-15K",
            "thermal probes and DAQ $2-5K",
        ],
        "note": "replaces 'UNESTIMATED' with a REPORTED range; not an "
                "owner estimate",
    })
    save(p, d)

    # =====================================================================
    # P08 — BUYER_SEQUENCE: commercial anchor
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P08/BUYER_SEQUENCE.json"
    d = load(p)
    ext(d, "commercial_anchor", {
        "status": "REPORTED ANCHOR (audit-provided; verification open)",
        "class": "ROUGH_ESTIMATE / REPORTED",
        "anchors_reported": {
            "programmable_shunt_valve_market": {
                "value": "$350-500M globally",
                "verification": "NOT independently verified this session "
                                "(REPORTED)"},
            "framing": "enable-the-next-generation (closed-loop shunts "
                       "needing power) rather than compete-with-current "
                       "(Strata-class valves reprogram magnetically, "
                       "without surgery)",
        },
        "origin": audit_prov,
    })
    save(p, d)

    # =====================================================================
    # P11 — DECISIVE_EXPERIMENT: quantified kill conditions + cost context
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P11/DECISIVE_EXPERIMENT.json"
    d = load(p)
    ext(d, "quantified_kill_conditions_r405", {
        "proposed_condition_A": {
            "rule": "if the damper's mean flow-settling time (to within "
                    "10% of steady state) is not at least 20% faster than "
                    "the ASD arm at ALL four tested postural pressures "
                    "(10/20/30/40 mmHg), the response-speed "
                    "differentiator is not established — KILL (unless the "
                    "proportional-flow differentiator is decisively "
                    "positive)",
            "threshold_provenance": {
                "value": 20, "unit": "percent faster",
                "class": "MODEL_DERIVED (engineering-judgment proposal)",
                "origin": audit_prov,
                "uncertainty": "the margin is the audit's proposal, not a "
                               "clinical-materiality derivation; "
                               "materiality evidence remains NONE "
                               "(the differentiation record)",
                "owner_gate": "REQUIRED before pre-registration "
                              "(Art. XXVII — BUYER_DEFINED/CLININAL "
                              "class required at registration time)",
            },
        },
        "proposed_condition_B": {
            "rule": "if the damper's target-flow accuracy (mean absolute "
                    "deviation from target flow at steady state) is "
                    "statistically worse than the ASD arm at any tested "
                    "pressure, the safety case is negative — KILL",
            "note": "consistent with the recorded falsifier's "
                    "disadvantage-class clause; the statistical test and "
                    "alpha are owner pre-registration items",
        },
        "instrument_detectability": {
            "record": "LEAD_PORTFOLIO_4/P11/INSTRUMENT_MDD_CALCULATION.json",
            "result": "the claimed 0.1 s settling difference is DETECTABLE "
                      "at p<0.05 with n=10/arm (MDD 0.0253 s, margin "
                      "3.95x) IF trace noise stays within quantization; "
                      "the resolution-limited worst case (settling band "
                      "== instrument resolution at 0.1 mL/min steady "
                      "flow) is disclosed in the record",
        },
    })
    ext(d, "cost_basis_r405", {
        "status": "RECORDED $15K/8wk (R339, unchanged) with the audit's "
                  "wider range recorded as context",
        "audit_range_reported": {
            "range": "$15-38K",
            "itemization": "bench hydraulic loop $3-8K; damper prototypes "
                           "at +/-0.01 mm tolerance $5-15K (n=3-5); "
                           "commercial ASD controls $2-5K; personnel "
                           "$5-10K",
            "manufacturing_tolerance_flag": "the audit's 0.18 mm +/-0.01 "
                                            "mm implant-grade-polymer "
                                            "tolerance challenge is "
                                            "recorded as a manufacturing "
                                            "feasibility UNKNOWN (consistent "
                                            "with the maturity record)",
            "verification": "REPORTED (audit itemization; owner "
                            "confirmation)",
        },
    })
    save(p, d)

    # =====================================================================
    # P11 — NOVELTY_ASSESSMENT: claim map US20250242099A1
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P11/NOVELTY_ASSESSMENT.json"
    d = load(p)
    ext(d, "closest_prior_claim_map_US20250242099A1", {
        "differentiation_argument": [
            "The closest specific-mechanism reference (US20250242099A1, "
            "Goldsmith, 'Vascular valves and servovalves — and prosthetic "
            "disorder response systems') is, by its own title and "
            "abstract, a VASCULAR VALVING/SERVOVALVE architecture for "
            "prosthetic disorder response — an active valving domain.",
            "P-24 is a PASSIVE inline hydraulic damper for a CSF shunt: an "
            "annular-gap viscous element providing proportional "
            "resistance, with no valve member, no actuation, and no "
            "servo control.",
            "The reference does not read on a passive proportional damper "
            "inline with a CSF shunt; the domain (vascular valves), the "
            "component class (valves/servovalves), and the actuation "
            "model (active response systems) are each disjoint from this "
            "package's recorded mechanism.",
        ],
        "evidence_basis": [
            "recorded relevance: 'Closest on the specific-mechanism query' "
            "— this assessment file",
            "web-searched publication record (Justia, 2026-09-04): "
            "publication 20250242099, Goldsmith, 'Vascular valves and "
            "servovalves - and prosthetic disorder response systems'; "
            "https://patents.justia.com/inventor/david-s-goldsmith",
        ],
        "limits": "snippet/title-level evidence; a full claim chart is "
                  "owner/counsel work; differentiation argument, NOT a "
                  "patentability opinion or FTO (Art. XXVIII)",
        "origin": audit_prov,
    })
    save(p, d)

    # =====================================================================
    # P11 — BUYER_SEQUENCE: commercial anchor; DIFFERENTIATION: materiality
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P11/BUYER_SEQUENCE.json"
    d = load(p)
    ext(d, "commercial_anchor", {
        "status": "REPORTED ANCHOR (audit-provided chain; verification "
                  "open)",
        "class": "ROUGH_ESTIMATE / REPORTED",
        "anchors_reported": {
            "csf_shunt_total_market": {
                "value": "$800M-1.2B globally",
                "verification": "NOT independently verified this session"},
            "anti_siphon_sub_market_estimate": {
                "value": "15-20% of valve market = $120-240M",
                "basis": "the audit's fraction assumption (MODELLED)"},
            "proportional_replacement_value": {
                "value": "$12-24M at 10% premium",
                "basis": "derived from the above REPORTED inputs"},
        },
        "origin": audit_prov,
    })
    save(p, d)

    p = "LEAD_PORTFOLIO_4/P11/DIFFERENTIATION_AND_CAUSAL_CHAIN.json"
    d = load(p)
    ext(d, "clinical_materiality_argument_r405", {
        "argument_reported": "the audit's proposal: binary anti-siphon "
                             "devices can permit over-drainage in the "
                             "initial postural-shift window (the claimed "
                             "0.5-1.5 s before membrane response); a "
                             "proportional element that reduces flow "
                             "smoothly through that window would target "
                             "the transient, not just the steady state",
        "literature_anchors": {
            "verified": [
                {"reference": "Ros et al. 2021, 'Shunt Overdrainage: "
                              "Reappraisal of the Syndrome' (PMC, cited "
                              "52x)",
                 "verified_snippet": "The role of postural change is "
                                     "explained by the law of Stevin: PP "
                                     "= (ICP - IAP) + HP",
                 "retrieval": "z-ai web_search, 2026-09-04",
                 "use": "the postural physics of over-drainage is "
                        "documented"},
                {"reference": "Hornshoj Pedersen et al. 2026, multicentre "
                              "over-drainage study",
                 "verified_snippet": "slightly negative ICP in supine "
                                     "position is indicative of CSF "
                                     "overdrainage; upright values lower "
                                     "than -10 mmHg",
                 "retrieval": "z-ai web_search, 2026-09-04",
                 "use": "over-drainage is a measured clinical outcome "
                        "class"},
            ],
            "reported_not_verified": [
                "the audit's specific transient-window claims (Rekate "
                "2008, Aschoff 1999: 'the initial over-drainage "
                "transient', 0.5-1.5 s membrane response) — REPORTED by "
                "the audit, not verified this session",
            ],
        },
        "verdict_unchanged": "both differentiators remain UNESTABLISHED "
                             "with materiality evidence NONE — this "
                             "argument is the pre-registration INPUT the "
                             "owner needs, not evidence of materiality "
                             "(Art. XXV: unknown stays unknown)",
        "origin": audit_prov,
    })
    save(p, d)

    # =====================================================================
    # P13 — NOVELTY_ASSESSMENT: the 2-query plan; DECISIVE_EXPERIMENT:
    # KA-014 prominence + fouling protocol + cost
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P13/NOVELTY_ASSESSMENT.json"
    d = load(p)
    ext(d, "patentbear_query_plan_r405", {
        "status": "OWNER ACTION with the audit's exact proposed queries "
                  "recorded (2/20 meter remaining at last recorded state)",
        "queries_proposed": [
            {"class": "BROAD",
             "query": "piezoresistive pressure sensor self-referencing "
                      "drift compensation implantable intracranial"},
            {"class": "SPECIFIC",
             "query": "wheatstone bridge dummy element common-mode thermal "
                      "drift cancellation CSF shunt ICP sensor"},
        ],
        "decision_rule_reported": "audit's proposal: >20 hits on the "
                                  "specific query -> novelty position "
                                  "probably weak; <5 hits on the exact "
                                  "self-referencing architecture in the "
                                  "ICP context -> may be defensible. The "
                                  "result gates all further engineering "
                                  "spend on this package.",
        "free_alternatives_recorded": "EPO/Lens (already in this record's "
                                      "owner-action note)",
        "origin": audit_prov,
    })
    save(p, d)

    p = "LEAD_PORTFOLIO_4/P13/DECISIVE_EXPERIMENT.json"
    d = load(p)
    ext(d, "ka014_prominence_declaration", {
        "statement": "KA-014 (biofouling-dominated NON-COMMON-MODE drift: "
                     "asymmetric fouling of the active element vs the "
                     "protected dummy) is THIS PACKAGE'S PRIMARY SCIENTIFIC "
                     "RISK: the only measured self-referencing ICP sensor "
                     "in repository history (P-25) failed through exactly "
                     "this channel (67.8% in-model cancellation, 3.45 "
                     "mmHg error > 2.0 threshold), and the recorded "
                     "mitigations (periodic recalibration, spare bridge "
                     "capacity) do not solve it. The fouling arm of this "
                     "experiment is the literal test of whether this "
                     "architecture survives its predecessor's failure "
                     "mode. This sentence is deliberately the most "
                     "prominent risk statement in the package (the "
                     "external audit's option c).",
        "design_mitigation_options_recorded": {
            "options": [
                "(a) protein-adsorption-reducing coating (PDMS/hydrophilic) "
                "on the exposed active element — MODELLED, requires "
                "EXTERNAL_PRECEDENT citation of coating-vs-biofouling "
                "evidence before adoption",
                "(b) shield geometry making both elements EQUALLY exposed "
                "(common-cause fouling is then bridge-compensated) — "
                "MODELLED, a geometry change with its own gate run",
                "(c) acknowledged-unresolved (current state, this "
                "declaration)",
            ],
            "status": "OWNER DESIGN DECISION — the machine records the "
                      "options and their evidence requirements; it does "
                      "not silently pick one",
        },
        "origin": audit_prov,
    })
    ext(d, "accelerated_fouling_protocol_r405", {
        "status": "PROPOSED PROTOCOL (MODEL_DERIVED, external-audit "
                  "proposal; owner pre-registration required)",
        "protocol": "expose BOTH arms (baseline single-ended and "
                    "self-referencing) to accelerated protein adsorption: "
                    "bovine serum albumin at physiological concentration, "
                    "37 C, 4-week soak; measure bridge output offset at "
                    "weekly intervals",
        "kill_criterion": "differential bridge output drift > 1 mmHg "
                          "after 4 weeks of fouling exposure -> the "
                          "non-common-mode channel dominates -> KA-014 "
                          "recurs -> repair (a NON-common-mode "
                          "compensation mechanism) or cemetery",
        "provenance": {"value": 1, "unit": "mmHg differential drift",
                       "class": "MODEL_DERIVED",
                       "origin": audit_prov,
                       "justification": "aligned with the P-25 "
                                        "precedent's 2.0 mmHg total-error "
                                        "threshold class and the dossier's "
                                        "1-2 mmHg accuracy target class; "
                                        "the exact value is an "
                                        "owner-registration item",
                       "owner_gate": "REQUIRED"},
        "note": "this is the exact test P-25 failed; specifying it "
                "explicitly is intellectual honesty, not pessimism",
    })
    ext(d, "cost_basis_r405", {
        "status": "REPORTED ESTIMATE (external auditor's itemization; "
                  "owner confirmation required)",
        "range": "$95-265K",
        "itemization_reported": [
            "MEMS die fabrication NRE $50-150K per mask set (material "
            "cost, stated honestly)",
            "engineering-sample wafer run $20-50K",
            "baseline comparator sensor (separate mask modification or "
            "commercial analog) $20-50K",
            "bench packaging $5-15K",
        ],
        "material_disclosure": "5-10x the other three packages' "
                               "experiments — this shifts the commercial "
                               "calculus (a licensing deal covering fab "
                               "NRE differs from one covering IP only); "
                               "recorded per the audit's own disclosure "
                               "requirement",
    })
    save(p, d)

    # =====================================================================
    # P13 — BUYER_SEQUENCE: commercial anchor
    # =====================================================================
    p = "LEAD_PORTFOLIO_4/P13/BUYER_SEQUENCE.json"
    d = load(p)
    ext(d, "commercial_anchor", {
        "status": "REPORTED ANCHOR with the search-found divergence "
                  "disclosed",
        "class": "ROUGH_ESTIMATE / REPORTED",
        "anchors": {
            "icp_monitoring_market_search_found": {
                "range": "$251.5M (2024, one research house) to $2.06B "
                         "(2026, another) — definitions differ "
                         "(monitoring services vs devices vs non-invasive "
                         "sub-segment)",
                "verification": "web-search snippets, 2026-09-04; the "
                                "external audit's $450-600M sits inside "
                                "this divergent range but was not itself "
                                "located"},
            "audit_figures_reported": "implantable ICP sensor sub-market "
                                      "as a fraction; calibration-interval "
                                      "extension (6 -> 24+ months) as the "
                                      "commercial argument — REPORTED",
        },
        "origin": audit_prov,
    })
    save(p, d)

    print("extensions written to: P04 (5 files), P08 (3), P11 (4), "
          "P13 (3)")


if __name__ == "__main__":
    main()

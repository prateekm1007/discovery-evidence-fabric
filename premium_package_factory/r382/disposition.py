"""premium_package_factory/r382/disposition.py — R382 CEO PORTFOLIO
DISPOSITION (CEO directive 2026-08-31: the portfolio triage).

WHAT THE CEO DECIDED (verbatim intent, per disposition class):
  SHOW NOW (buyer release, presentation order): 04 drainage floor,
    11 gravity damper, 13 pressure sensor, 08 NIR photovoltaic.
  HOLD (one specific gate each): 01 V0 bench, 02 actuator selection,
    09 tissue link budget, 12 membrane fouling test.
  RETIRE: 06 (no technology exists — audit REMOVE), 07 (pending the
    decisive shaker test), 10 (commercially outgunned), 14 (physics
    blocks the primary use case; optional narrow reposition).
  SEPARATE TRACK (real ideas, wrong buyer audience): 03, 05, 15.

EPISTEMIC RULES (Constitution):
- Art. III/VI: every disposition carries its evidence basis. Claims the
  REPO RECORD supports are bound to exact file + exact span (machine-
  re-verified by verify_disposition + acceptance). Claims that are CEO
  business judgments (budgets, positioning, comparative superlatives)
  are recorded as CEO_STATED — never laundered into record evidence.
- Art. XXVII: the CEO's dollar figures are BUDGET DIRECTIVES, not
  engineering thresholds — the record's cost basis is NOT_ESTABLISHED
  for every package (the $5K/$25K/$100K ladder was retired in R371).
- Art. XV: the four cases where the CEO disposition is STRICTER than
  the independent consultant's verdict (07, 08, 10, 14) are flagged
  CEO_OVERRIDE_DISCLOSED — divergences surfaced, never hidden.
- Art. XI: 'delete' is implemented as retired-from-the-buyer-release
  with bytes preserved in RETIRED/ (history is evidence); a retired
  package is absent from everything a buyer can receive.
- Art. XXV: the records' own honest caveats (kill condition NOT
  confirmed) travel WITH the disposition — a business decision may be
  stricter than the evidence, but it may never pretend the evidence
  said more than it did.

Pointer conventions (machine-checkable):
  scope PACKAGE  -> pointer is a file INSIDE the package folder
                    (wherever it physically lives), span must appear
                    verbatim in that file.
  scope ENGINE   -> pointer is a path RELATIVE to the engine repo
                    root, span must appear verbatim in that file.
  scope ENGINE_ABSENCE -> pointer resolves; every absent_pattern must
                    NOT appear in that file (verified absence, the
                    claim IS the absence).
No absolute paths and no engine-internal markers are written into the
portfolio tree (r372 boundary guard compliance).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from ..r371.canonical_source import PACKAGE_MAP, folder_name

R382_VERSION = "1.0.0"
CEO_DIRECTIVE_DATE = "2026-08-31"
DISPOSITION_RECORD_NAME = "PORTFOLIO_DISPOSITION.json"

ENGINE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           "..", ".."))

# CEO presentation order for the buyer release (portfolio numbers)
BUYER_ORDER = ["04", "11", "13", "08"]

STATES = (
    "BUYER_PRIMARY",            # in the buyer release, CEO order
    "HOLD_PENDING_GATE",        # internal until its gate is cleared
    "SPECIALIST_TRACK",         # separate outreach, not the buyer deck
    "RETIRED",                  # out of the buyer release, bytes preserved
    "RETIRED_PENDING_DECISIVE_TEST",  # retired default; test can revive
)

STATE_DIRS = {
    "HOLD_PENDING_GATE": "HOLDING",
    "SPECIALIST_TRACK": "SPECIALIST_TRACK",
    "RETIRED": "RETIRED",
    "RETIRED_PENDING_DECISIVE_TEST": "RETIRED",
}

_CONSULTANT_REPORT = (
    "EXTERNAL_CONSULTANT_EVIDENCE/EXTERNAL_CONSULTANT_REPORT_2026-08-27.md")

# ---------------------------------------------------------------------------
# The disposition map (portfolio number -> disposition record)
# ---------------------------------------------------------------------------
DISPOSITIONS: Dict[str, Dict[str, Any]] = {
    # ---- BUYER PRIMARY (the 4-package buyer release) ----------------------
    "04": {
        "state": "BUYER_PRIMARY",
        "presentation_order": 1,
        "pkg_id": "P-07",
        "ceo_rationale": (
            "Lead with this one. Simplest physics in the portfolio; "
            "passive design; no electronics, sensors or actuators to "
            "fail; a buyer can understand the entire mechanism in 30 "
            "seconds from the diagram; the door-opener if there is one "
            "meeting."),
        "record_verified_basis": [
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-07_ArtifactRichDossier.json",
             "span": "passive safety floor",
             "claim": "the canonical mechanism is a passive dual-lumen "
                      "drainage floor (no powered subsystem)"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P04 | Drainage Floor | YES | KEEP | "
                     "SPONSOR_SMALL_VAL |",
             "claim": "independent consultant verdict: world-class "
                      "dossier YES, KEEP, SPONSOR_SMALL_VAL"},
            {"scope": "PACKAGE", "pointer": "VALIDATION_ECONOMICS.json",
             "span": "10 weeks",
             "claim": "first decisive work package WP-01 is recorded "
                      "at 10 weeks"},
        ],
        "ceo_stated_basis": [
            {"claim": "$5K budget for the decisive experiment",
             "note": "CEO budget directive — the record carries cost "
                     "NOT_ESTABLISHED (the $5K/$25K/$100K template "
                     "ladder was retired in R371); not record evidence"},
            {"claim": "cheapest decisive experiment in the portfolio",
             "note": "CEO comparative positioning — all package costs "
                     "are NOT_ESTABLISHED, so no comparative cost "
                     "claim is derivable from the record"},
            {"claim": "cleanest regulatory path in the portfolio",
             "note": "CEO comparative positioning — the record does "
                     "not rank regulatory paths across packages"},
        ],
        "consultant_verdict": {
            "wc_dossier": "YES", "verdict": "KEEP",
            "transaction": "SPONSOR_SMALL_VAL",
            "top_blocker": "Common-cause obstruction undefined",
            "decisive_next_experiment": (
                "Multi-lumen extrusion + differential obstruction test"),
        },
        "agreement": "ALIGNED",
    },
    "11": {
        "state": "BUYER_PRIMARY",
        "presentation_order": 2,
        "pkg_id": "P-24",
        "ceo_rationale": (
            "Show alongside 04. The Miethke ShuntAssistant is a real "
            "named predicate device the buyer knows; the clearest "
            "510(k) pathway in the portfolio; proportional-vs-binary "
            "damping is a specific arguable differentiator."),
        "record_verified_basis": [
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-24_ArtifactRichDossier.json",
             "span": "Miethke ShuntAssistant",
             "claim": "the record's external precedent catalog names "
                      "the Miethke ShuntAssistant (ASD literature, "
                      "PMC9133390)"},
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-24_ArtifactRichDossier.json",
             "span": "510(k) with substantial equivalence to ASD",
             "claim": "the record's regulatory pathway is 510(k) with "
                      "substantial equivalence to ASD (or De Novo)"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P11 | Gravity Damper | CONDITIONAL | KEEP | "
                     "SPONSOR_SMALL_VAL |",
             "claim": "consultant verdict KEEP / SPONSOR_SMALL_VAL"},
        ],
        "ceo_stated_basis": [
            {"claim": "clearest 510(k) pathway in the whole portfolio",
             "note": "CEO comparative positioning — the pathway is "
                     "recorded; the cross-portfolio ranking is the "
                     "CEO's, not the record's"},
            {"claim": "proportional-vs-binary damping as THE "
                      "differentiator",
             "note": "CEO positioning — the record's own top blocker "
                     "is 'Optimal c_h unknown; ASD comparison not "
                     "quantified' (the comparative advantage over "
                     "existing ASDs is a recorded UNKNOWN)"},
        ],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "KEEP",
            "transaction": "SPONSOR_SMALL_VAL",
            "top_blocker": "Optimal c_h unknown; ASD comparison not "
                           "quantified",
            "decisive_next_experiment": (
                "Damper element prototypes + c_h vs. flow rate"),
        },
        "agreement": "ALIGNED",
    },
    "13": {
        "state": "BUYER_PRIMARY",
        "presentation_order": 3,
        "pkg_id": "P-27-R1",
        "ceo_rationale": (
            "Show to technically sophisticated buyers. The underlying "
            "MEMS piezoresistive technology is the most mature in the "
            "portfolio; Codman and Raumedic exist as competitors, "
            "confirming the market is real; the self-referencing "
            "drift-compensation claim is the differentiable piece."),
        "record_verified_basis": [
            {"scope": "PACKAGE", "pointer": "V2_MUTATION_ADDENDUM.json",
             "span": "Codman ICP Express, Raumedic Neurovent",
             "claim": "the record's predicate analysis names Codman "
                      "ICP Express and Raumedic Neurovent (FDA product "
                      "code GWM, Class II/510(k))"},
            {"scope": "PACKAGE", "pointer": "VALIDATION_ECONOMICS.json",
             "span": "16 weeks (foundry cycle)",
             "claim": "first decisive work package WP-01 is recorded "
                      "as a 16-week foundry cycle"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P13 | MEMS Pressure Sensor | CONDITIONAL | "
                     "KEEP | COMMISSION_FEASIBILITY |",
             "claim": "consultant verdict KEEP / "
                     "COMMISSION_FEASIBILITY"},
        ],
        "ceo_stated_basis": [
            {"claim": "budget $25K for the foundry prototype, not $5K",
             "note": "CEO budget directive — the record carries cost "
                     "NOT_ESTABLISHED; the 16-week foundry duration "
                     "IS recorded, the dollar figure is the CEO's"},
            {"claim": "most mature underlying technology in the "
                      "portfolio",
             "note": "CEO comparative positioning, not a record claim"},
            {"claim": "self-referencing drift compensation as THE "
                      "differentiator",
             "note": "CEO positioning — the record's own top blocker "
                     "is 'Commercial ICP sensor differentiation "
                     "unstated'"},
        ],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "KEEP",
            "transaction": "COMMISSION_FEASIBILITY",
            "top_blocker": "Commercial ICP sensor differentiation "
                           "unstated",
            "decisive_next_experiment": (
                "MEMS foundry prototype (16-week lead time)"),
        },
        "agreement": "ALIGNED",
    },
    "08": {
        "state": "BUYER_PRIMARY",
        "presentation_order": 4,
        "pkg_id": "P-16",
        "ceo_rationale": (
            "Show to any buyer who cares about battery-free implants. "
            "An external published paper (Moon/Blaauw, PMC5646820) "
            "directly validates the core mechanism; the unit error was "
            "fixed; the LED-plus-phantom bench test is decisive and "
            "cheap; if it passes this becomes a platform technology "
            "enabling 13."),
        "record_verified_basis": [
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-16_ArtifactRichDossier.json",
             "span": ">= 500 μW (pass threshold)",
             "claim": "the canonical power target DI-003 reads "
                      "'>= 500 μW (pass threshold)'"},
            {"scope": "ENGINE",
             "pointer": "EXTERNAL_CONSULTANT_EVIDENCE/"
                        "NUMERIC_ASSERTION_AUDIT.json",
             "span": "CONFIRMED_AS_UNIT_CONCERN",
             "claim": "the independent numeric audit confirmed the "
                      "500 mW figure as a unit concern"},
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-16_ArtifactRichDossier.json",
             "span": "Moon-Blaauw",
             "claim": "the dossier's external evidence cites the "
                      "Moon/Blaauw subcutaneous photovoltaic infrared "
                      "energy harvesting paper"},
            {"scope": "ENGINE",
             "pointer": "external_evidence/pubmed_p16_GOVERNED.json",
             "span": "PMC5646820",
             "claim": "the governed PubMed evidence packet for P-16 "
                      "carries PMC5646820"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P08 | NIR Photovoltaic | CONDITIONAL | "
                     "UPGRADE | SPONSOR_SMALL_VAL |",
             "claim": "consultant verdict UPGRADE / "
                     "SPONSOR_SMALL_VAL; top blocker 'Unit error "
                     "(500mW vs 500µW); skull attenuation'"},
        ],
        "ceo_stated_basis": [
            {"claim": "the unit error (500 mW -> 500 µW) was fixed in "
                      "V2",
             "note": "the CURRENT canonical record carries 500 µW "
                     "(verified above) and the unit error is "
                     "consultant-confirmed; no V2 mutation addendum "
                     "for P-16 exists in the shipped mutation input "
                     "set, so the fix trail itself is CEO-stated"},
            {"claim": "the only package where an external published "
                      "paper directly validates the core mechanism",
             "note": "CEO comparative framing — the governed evidence "
                     "packet for P-16 is verified; the portfolio-wide "
                     "'only' is the CEO's"},
            {"claim": "$5K LED-plus-phantom bench test",
             "note": "CEO budget directive — record cost is "
                     "NOT_ESTABLISHED"},
            {"claim": "platform technology enabling 13",
             "note": "CEO strategic projection, not a record claim"},
        ],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "UPGRADE",
            "transaction": "SPONSOR_SMALL_VAL",
            "top_blocker": "Unit error (500mW vs 500µW); skull "
                           "attenuation",
            "decisive_next_experiment": (
                "NIR source + PV cell + tissue phantom bench test"),
        },
        "agreement": (
            "CEO_OVERRIDE_DISCLOSED — the consultant verdict is "
            "UPGRADE (bench test first); the CEO ships it as "
            "buyer-primary now. The decisive bench test remains the "
            "package's recorded next experiment and stays disclosed "
            "inside the package."),
    },

    # ---- HOLD PENDING GATE (internal until the gate is cleared) ----------
    "01": {
        "state": "HOLD_PENDING_GATE",
        "pkg_id": "P-01",
        "ceo_rationale": (
            "Hold until the V0 bench prototype exists. Strong "
            "engineering, honest kill condition, good dossier — but "
            "the prediction lead time is already failing in the "
            "computational model. Do not show a buyer while that "
            "failure is unresolved."),
        "gate": {
            "condition": (
                "V0 bench prototype exists AND multi-segment "
                "outperforms single-segment in >= 80% of bench "
                "scenarios"),
            "decisive_test": (
                "V0 bench: 4-segment catheter + COTS sensors"),
            "gate_failure_consequence": (
                "if multi-segment does not outperform in >= 80% of "
                "bench scenarios, retire the package"),
            "ceo_budget_directive": (
                "$5-8K, 8 weeks (CEO directive; the record carries "
                "cost NOT_ESTABLISHED)"),
        },
        "record_verified_basis": [
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-01_ArtifactRichDossier.json",
             "span": ">= 24h before symptoms",
             "claim": "design input DI-007 sets the prediction lead "
                      "time target at >= 24h before symptoms"},
            {"scope": "ENGINE",
             "pointer": "EXTERNAL_CONSULTANT_EVIDENCE/"
                        "EXTERNAL_AUDIT_LEARNING_REPORT.json",
             "span": "14h vs 24h lead time (CONFIRMED)",
             "claim": "the external audit CONFIRMED the 14h achieved "
                      "lead time vs the 24h target ('14h lead time "
                      "failure is honestly disclosed')"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P01 | Multi-Segment Flow | CONDITIONAL | "
                     "KEEP | SPONSOR_SMALL_VAL |",
             "claim": "consultant verdict KEEP; top blocker 'No real "
                      "sensor data; lead time fails target'"},
        ],
        "ceo_stated_basis": [],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "KEEP",
            "transaction": "SPONSOR_SMALL_VAL",
            "top_blocker": "No real sensor data; lead time fails "
                           "target",
            "decisive_next_experiment": (
                "V0 bench: 4-seg catheter + COTS sensors"),
        },
        "agreement": (
            "ALIGNED_WITH_ADDED_GATE — consultant KEEP on the dossier; "
            "the CEO additionally gates BUYER DISTRIBUTION on the V0 "
            "bench outcome."),
    },
    "02": {
        "state": "HOLD_PENDING_GATE",
        "pkg_id": "P-02",
        "ceo_rationale": (
            "Hold until the actuator technology is selected. The "
            "valve physics is sound but the actuator is unspecified — "
            "a buyer's first question is 'what actually moves?' and "
            "there is no answer yet."),
        "gate": {
            "condition": (
                "actuator technology selected (MEMS electrothermal or "
                "shape-memory polymer) with chronic reliability data "
                "shown, then distribute"),
            "decisive_test": (
                "passive variable-area valve prototype (consultant's "
                "recorded decisive next experiment)"),
            "gate_failure_consequence": (
                "without a selected actuator with reliability data the "
                "package stays out of the buyer deck"),
            "ceo_budget_directive": None,
        },
        "record_verified_basis": [
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-02_ArtifactRichDossier.json",
             "span": "candidate: MEMS electrothermal or shape-memory "
                     "polymer",
             "claim": "subsystem SS-03 records the actuator as an "
                      "UNSELECTED candidate (MEMS electrothermal or "
                      "shape-memory polymer)"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P02 | Adaptive Valve | CONDITIONAL | UPGRADE "
                     "| WATCH |",
             "claim": "consultant verdict UPGRADE / WATCH; top "
                      "blocker 'Actuator tech unselected; no ASD "
                      "differentiation'"},
        ],
        "ceo_stated_basis": [],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "UPGRADE",
            "transaction": "WATCH",
            "top_blocker": "Actuator tech unselected; no ASD "
                           "differentiation",
            "decisive_next_experiment": (
                "Passive variable-area valve prototype"),
        },
        "agreement": "ALIGNED (same blocker; the CEO makes the "
                     "distribution gate explicit)",
    },
    "09": {
        "state": "HOLD_PENDING_GATE",
        "pkg_id": "P-21-R1",
        "ceo_rationale": (
            "Hold until the tissue-depth link budget is done. The "
            "physics check showed position error ~42mm at clinically "
            "achievable SNR under SAR constraints — far outside the "
            "clinical target. Not dead, but the technical case is not "
            "ready. The desk calculation either fixes this or kills "
            "it cheaply."),
        "gate": {
            "condition": (
                "complete tissue-depth link budget with real tissue "
                "attenuation measurements, SAR-constrained transmit "
                "power and receiver noise figure — resolves or kills"),
            "decisive_test": (
                "link budget test in tissue phantom at >= 3cm depth "
                "(consultant's recorded decisive next experiment)"),
            "gate_failure_consequence": (
                "if the link budget cannot close, retire the package"),
            "ceo_budget_directive": (
                "$2K desk calculation from an RF engineer (CEO "
                "directive; the record carries cost NOT_ESTABLISHED)"),
        },
        "record_verified_basis": [
            {"scope": "PACKAGE", "pointer": "V2_MUTATION_ADDENDUM.json",
             "span": "42.7mm position error at SNR=10dB",
             "claim": "independent CRLB calculation: 42.7mm position "
                      "error at SNR=10dB — HIGH FEASIBILITY RISK, kill "
                      "condition NOT confirmed (SNR assumption "
                      "unverified; complete link budget required)"},
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-21-R1_ArtifactRichDossier.json",
             "span": "likely 5-10 mm clinical utility",
             "claim": "the record's OWN accuracy target is UNKNOWN "
                      "(stated as 'likely 5-10 mm clinical utility')"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P09 | UWB Localization | CONDITIONAL | "
                     "UPGRADE | SPONSOR_SMALL_VAL |",
             "claim": "consultant verdict UPGRADE; top blocker "
                      "'SAR-constrained accuracy likely insufficient'"},
        ],
        "ceo_stated_basis": [
            {"claim": "<5mm clinical target",
             "note": "CEO-stated figure — the record carries the "
                     "accuracy target as UNKNOWN (likely 5-10 mm "
                     "clinical utility); the 42.7mm CRLB error is "
                     "record-verified"},
        ],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "UPGRADE",
            "transaction": "SPONSOR_SMALL_VAL",
            "top_blocker": "SAR-constrained accuracy likely "
                           "insufficient",
            "decisive_next_experiment": (
                "Link budget test in tissue phantom at ≥3cm depth"),
        },
        "agreement": "ALIGNED (same decisive experiment)",
    },
    "12": {
        "state": "HOLD_PENDING_GATE",
        "pkg_id": "P-26",
        "ceo_rationale": (
            "Hold until a fouling test is run. The van 't Hoff / "
            "Kedem-Katchalsky equations are correct, but membrane "
            "fouling in CSF is a known, documented, severe engineering "
            "problem and the dossier has no data on it. No buyer will "
            "commission this without that answer."),
        "gate": {
            "condition": (
                "24-week membrane-in-CSF-mimic fouling test run — "
                "the membrane survives or the concept dies"),
            "decisive_test": (
                "Membrane + CSF mimic fouling test (24-week) — the "
                "consultant's recorded decisive next experiment"),
            "gate_failure_consequence": (
                "if the membrane does not survive, retire the package"),
            "ceo_budget_directive": None,
        },
        "record_verified_basis": [
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-26_ArtifactRichDossier.json",
             "span": "CSF contains proteins, cells — fouling risk",
             "claim": "design input DI-010 records the membrane "
                      "fouling environment (CSF proteins, cells — "
                      "fouling risk)"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P12 | Osmotic Valve | CONDITIONAL | UPGRADE "
                     "| SPONSOR_SMALL_VAL |",
             "claim": "consultant verdict UPGRADE; top blocker 'CSF "
                      "membrane fouling inadequately assessed'"},
        ],
        "ceo_stated_basis": [],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "UPGRADE",
            "transaction": "SPONSOR_SMALL_VAL",
            "top_blocker": "CSF membrane fouling inadequately "
                           "assessed",
            "decisive_next_experiment": (
                "Membrane + CSF mimic fouling test (24-week)"),
        },
        "agreement": "ALIGNED (same 24-week test)",
    },

    # ---- RETIRED (out of the buyer release; bytes preserved) -------------
    "06": {
        "state": "RETIRED",
        "pkg_id": "P-13",
        "ceo_rationale": (
            "Delete immediately. The only package the audit rated "
            "REMOVE. No real failure dataset exists — the technology "
            "cannot be built, trained or validated without a "
            "multi-year instrumented clinical programme that does not "
            "exist. There is no technology to transfer, only a plan to "
            "eventually acquire the data needed to design one. Keeping "
            "it damages the credibility of everything next to it."),
        "retirement_reason": (
            "no transferable technology: the training data does not "
            "exist and is not acquirable by bench, computation, "
            "literature or design work (recorded CRITICAL BLOCKER); "
            "the independent consultant verdict is REMOVE / REJECT"),
        "record_verified_basis": [
            {"scope": "PACKAGE", "pointer": "V2_MUTATION_ADDENDUM.json",
             "span": "No real failure dataset exists to train the "
                     "model",
             "claim": "the V2 addendum records the critical blocker "
                      "verbatim and repositions the package as a "
                      "long-term research direction"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P06 | ML Predictor | NO | REMOVE | REJECT |",
             "claim": "consultant verdict REMOVE / REJECT: 'No real "
                      "failure dataset; terminology inaccurate'"},
            {"scope": "PACKAGE", "pointer": "UNKNOWN_ROADMAP.json",
             "span": "not resolvable by bench, computation, "
                     "literature or design work alone",
             "claim": "the unknown roadmap records that the dataset "
                      "is not resolvable by any near-term engineering "
                      "work"},
        ],
        "ceo_stated_basis": [
            {"claim": "multi-year instrumented clinical programme "
                      "that doesn't exist",
             "note": "CEO framing of the record's own "
                     "'data-acquisition or long-lead program' "
                     "resolution path"},
        ],
        "consultant_verdict": {
            "wc_dossier": "NO", "verdict": "REMOVE",
            "transaction": "REJECT",
            "top_blocker": "No real failure dataset; terminology "
                           "inaccurate",
            "decisive_next_experiment": (
                "N/A — prerequisite dataset doesn't exist"),
        },
        "agreement": "ALIGNED (REMOVE)",
    },
    "07": {
        "state": "RETIRED_PENDING_DECISIVE_TEST",
        "pkg_id": "P-15-R1",
        "ceo_rationale": (
            "Delete pending a $3K shaker test. The independent physics "
            "calculation showed PVDF at CSF pulsation strain "
            "(~50 µε) generates ~25 nW — well below the 100 nW kill "
            "threshold; the V2 addendum acknowledged this. PZT offers "
            "higher coupling but introduces lead-based "
            "biocompatibility problems. Run the shaker test at "
            "physiologic strain: if PVDF passes, keep it; if not, "
            "retire rather than explaining the physics gap to every "
            "buyer."),
        "retirement_reason": (
            "power budget below the kill threshold at the assumed "
            "strain: PVDF 25.6 nW at 50 µε vs the 100 nW kill "
            "threshold (HIGH FEASIBILITY RISK, recorded). The record "
            "honestly states the kill condition is NOT confirmed — "
            "the strain input is estimated, not measured; if in-vivo "
            "strain exceeds 200 µε the calculation changes. The "
            "CEO's default is retirement unless the decisive test "
            "passes."),
        "revival_condition": {
            "condition": (
                "PVDF passes the shaker-table test at physiologic "
                "strain (power at or above the kill threshold)"),
            "decisive_test": (
                "shaker table test + power measurement at physiologic "
                "strain (consultant's recorded decisive next "
                "experiment)"),
            "ceo_budget_directive": (
                "$3K, 8 weeks (CEO directive; the record carries "
                "cost NOT_ESTABLISHED)"),
            "failure_consequence": (
                "test fails -> retirement is final"),
        },
        "record_verified_basis": [
            {"scope": "PACKAGE", "pointer": "V2_MUTATION_ADDENDUM.json",
             "span": "25.6 nW at 50 microstrain, kill threshold "
                     "100 nW",
             "claim": "independent calculation: PVDF 25.6 nW at 50 "
                      "microstrain vs the 100 nW kill threshold — "
                      "HIGH FEASIBILITY RISK"},
            {"scope": "PACKAGE", "pointer": "V2_MUTATION_ADDENDUM.json",
             "span": "If actual in-vivo catheter-wall strain "
                     ">200 microstrain",
             "claim": "the record's own caveat: the kill condition is "
                      "NOT confirmed — the strain input is estimated, "
                      "not measured"},
            {"scope": "ENGINE",
             "pointer": "EXTERNAL_CONSULTANT_EVIDENCE/"
                        "INDEPENDENT_REVIEW_CALCULATIONS.json",
             "span": "PLAUSIBLE_BUT_NOT_INDEPENDENTLY_REPRODUCIBLE",
             "claim": "the independent review classifies the "
                      "calculation as arithmetically consistent but "
                      "not independently reproducible (strain input "
                      "unsourced); correct disposition is 'empirical "
                      "strain measurement required before "
                      "kill-condition determination'"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P07 | Piezo Harvesting | CONDITIONAL | "
                     "UPGRADE | SPONSOR_SMALL_VAL |",
             "claim": "consultant verdict UPGRADE / "
                     "SPONSOR_SMALL_VAL; top blocker 'Power calc "
                     "suggests kill condition triggered (PVDF)'"},
        ],
        "ceo_stated_basis": [
            {"claim": "PZT offers higher coupling but introduces "
                      "lead-based biocompatibility problems",
             "note": "general engineering context stated by the CEO; "
                     "the record only says the PZT alternative "
                     "requires independent calculation"},
        ],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "UPGRADE",
            "transaction": "SPONSOR_SMALL_VAL",
            "top_blocker": "Power calc suggests kill condition "
                           "triggered (PVDF)",
            "decisive_next_experiment": (
                "Shaker table test + power measurement at physiologic "
                "strain"),
        },
        "agreement": (
            "CEO_OVERRIDE_DISCLOSED — the consultant verdict is "
            "UPGRADE (test first, default keep); the CEO's default is "
            "retirement unless the test passes. The record itself says "
            "kill condition NOT confirmed; that caveat is preserved "
            "here verbatim."),
    },
    "10": {
        "state": "RETIRED",
        "pkg_id": "P-22-R1",
        "ceo_rationale": (
            "Delete. Medtronic StealthStation and Brainlab cranial "
            "navigation are commercially deployed. The dossier has no "
            "competitive analysis against them, no tissue damage "
            "threshold, and no differentiation case. You are not "
            "going to out-resource established surgical robotics "
            "companies at this stage. The engineering concept is "
            "fine; the commercial case doesn't exist yet."),
        "retirement_reason": (
            "no commercial case: the canonical dossier contains no "
            "competitive analysis against the deployed cranial "
            "navigation platforms (verified by exact-string absence) "
            "and no differentiation case; the consultant's top "
            "blocker is 'competitive landscape absent; tissue damage "
            "undefined'"),
        "record_verified_basis": [
            {"scope": "ENGINE_ABSENCE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-22-R1_ArtifactRichDossier.json",
             "span": None,
             "absent_patterns": ["StealthStation", "Brainlab",
                                 "Medtronic"],
             "claim": "the canonical dossier carries NO competitive "
                      "analysis naming the deployed cranial navigation "
                      "platforms (verified by exact-string search: "
                      "zero matches)"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P10 | Autonomous Navigation | NO | UPGRADE | "
                     "WATCH |",
             "claim": "consultant verdict UPGRADE / WATCH; top "
                      "blocker 'Competitive landscape absent; tissue "
                      "damage undefined'"},
        ],
        "ceo_stated_basis": [
            {"claim": "Medtronic StealthStation and Brainlab are "
                      "commercially deployed",
             "note": "CEO-stated external market context, not a repo "
                     "record; the repo-verifiable part is the "
                     "dossier's verified ABSENCE of competitive "
                     "analysis"},
            {"claim": "not going to out-resource established "
                      "surgical robotics companies",
             "note": "CEO business judgment"},
        ],
        "consultant_verdict": {
            "wc_dossier": "NO", "verdict": "UPGRADE",
            "transaction": "WATCH",
            "top_blocker": "Competitive landscape absent; tissue "
                           "damage undefined",
            "decisive_next_experiment": (
                "Catheter buckling specimens + competitive analysis"),
        },
        "agreement": (
            "CEO_OVERRIDE_DISCLOSED — the consultant verdict is "
            "UPGRADE / WATCH (with a competitive-analysis work item); "
            "the CEO retires on commercial grounds (business "
            "authority), disclosed here rather than silently "
            "overridden."),
    },
    "14": {
        "state": "RETIRED",
        "pkg_id": "P-28",
        "ceo_rationale": (
            "Delete or sharply reposition. The impedance check is "
            "decisive: brain tissue Z ratio is 1.039 and fibrous "
            "debris is 1.072, both below the kill threshold. The "
            "primary clinical obstruction mechanism — tissue ingrowth "
            "and fibrous debris — is acoustically low-contrast to "
            "this system. Air bubbles and calcium deposits are "
            "detectable, but those are minority obstruction types. "
            "Repositioning as a 'calcification detector' is a narrow "
            "but possibly real application; without the energy for a "
            "reposition, delete."),
        "retirement_reason": (
            "impedance physics blocks the primary use case: Z ratio "
            "1.039-1.072 for tissue/CSF, reflection coefficient "
            "1.9-3.5% (recorded independent calculation). The record "
            "honestly states the kill condition is NOT confirmed — "
            "detectability depends on frequency, transducer geometry, "
            "signal processing and clutter; a frequency-dependent "
            "phantom experiment is the recorded resolution. The CEO's "
            "default is retirement unless a reposition decision is "
            "made."),
        "reposition_option": {
            "option": (
                "reposition as a calcification detector (narrow "
                "application; calcium deposits ARE detectable)"),
            "status": "CEO_DECISION_PENDING — without an explicit "
                      "reposition decision the package stays retired",
            "decisive_test": (
                "tissue phantom acoustic impedance contrast "
                "measurement (consultant's recorded decisive next "
                "experiment)"),
        },
        "record_verified_basis": [
            {"scope": "PACKAGE", "pointer": "V2_MUTATION_ADDENDUM.json",
             "span": "Z ratio 1.039-1.072 for tissue/CSF, reflection "
                     "coefficient 1.9-3.5%",
             "claim": "independent impedance calculation recorded "
                      "verbatim: HIGH FEASIBILITY RISK for tissue "
                      "obstruction detection"},
            {"scope": "PACKAGE", "pointer": "V2_MUTATION_ADDENDUM.json",
             "span": "A frequency-dependent phantom experiment is "
                     "required",
             "claim": "the record's own caveat: kill condition NOT "
                      "confirmed — a phantom experiment is the "
                      "recorded resolution"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P14 | Acoustic Detection | CONDITIONAL | "
                     "UPGRADE | SPONSOR_SMALL_VAL |",
             "claim": "consultant verdict UPGRADE; top blocker 'Z "
                      "ratio for tissue/debris < kill threshold'"},
        ],
        "ceo_stated_basis": [
            {"claim": "1.1 kill threshold",
             "note": "CEO-stated figure — the record states the "
                     "'kill threshold' concept via the consultant "
                     "table without recording the 1.1 number"},
            {"claim": "air bubbles and calcium deposits are minority "
                      "obstruction types",
             "note": "CEO clinical-epidemiology framing, not a repo "
                     "record"},
        ],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "UPGRADE",
            "transaction": "SPONSOR_SMALL_VAL",
            "top_blocker": "Z ratio for tissue/debris < kill "
                           "threshold",
            "decisive_next_experiment": (
                "Tissue phantom acoustic impedance contrast "
                "measurement"),
        },
        "agreement": (
            "CEO_OVERRIDE_DISCLOSED — the consultant verdict is "
            "UPGRADE (phantom test first); the CEO retires or "
            "repositions on business grounds, with the record's "
            "'kill condition NOT confirmed' caveat preserved "
            "verbatim."),
    },

    # ---- SPECIALIST TRACK (wrong buyer audience, not wrong technology) ---
    "03": {
        "state": "SPECIALIST_TRACK",
        "pkg_id": "P-04",
        "ceo_rationale": (
            "Wrong buyer, not wrong technology. The most "
            "scientifically interesting concept in the portfolio — an "
            "enzymatic catheter at the intersection of Alzheimer's "
            "and neurosurgery — but no standard shunt manufacturer "
            "will know what to do with it. The buyer is a pharma "
            "company with an enzyme programme, a university lab, or a "
            "neurodegeneration-focused biotech. Remove from the "
            "industrial buyer deck; keep for a separate outreach "
            "track."),
        "specialist_buyer_profile": (
            "pharma company with an enzyme programme, university "
            "laboratory, or neurodegeneration-focused biotech"),
        "record_verified_basis": [
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P03 | Catalytic Ab42 | CONDITIONAL | "
                     "REPOSITION | WATCH |",
             "claim": "consultant verdict REPOSITION / WATCH; top "
                      "blocker 'NEP stability on Ti unknown; "
                      "combination product'"},
        ],
        "ceo_stated_basis": [
            {"claim": "most scientifically interesting concept in the "
                      "portfolio",
             "note": "CEO qualitative judgment"},
        ],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "REPOSITION",
            "transaction": "WATCH",
            "top_blocker": "NEP stability on Ti unknown; combination "
                           "product",
            "decisive_next_experiment": (
                "Recombinant NEP enzyme + immobilization test"),
        },
        "agreement": "ALIGNED (REPOSITION)",
    },
    "05": {
        "state": "SPECIALIST_TRACK",
        "pkg_id": "P-11",
        "ceo_rationale": (
            "Same situation as 03. The buyer is a phage therapeutics "
            "company or an antimicrobial coatings company, not a "
            "shunt manufacturer. The combination product regulatory "
            "pathway (biologics + device) is too complex for a "
            "standard device BD conversation. Remove from the main "
            "deck, keep for specialist outreach."),
        "specialist_buyer_profile": (
            "phage therapeutics company or antimicrobial coatings "
            "company"),
        "record_verified_basis": [
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P05 | Phage Anti-Biofilm | CONDITIONAL | "
                     "REPOSITION | WATCH |",
             "claim": "consultant verdict REPOSITION / WATCH; top "
                      "blocker 'Phage infectivity on Ti unknown; "
                      "combination product'"},
        ],
        "ceo_stated_basis": [],
        "consultant_verdict": {
            "wc_dossier": "CONDITIONAL", "verdict": "REPOSITION",
            "transaction": "WATCH",
            "top_blocker": "Phage infectivity on Ti unknown; "
                           "combination product",
            "decisive_next_experiment": (
                "Ti-coated coupon + phage viability test"),
        },
        "agreement": "ALIGNED (REPOSITION)",
    },
    "15": {
        "state": "SPECIALIST_TRACK",
        "pkg_id": "P-29",
        "ceo_rationale": (
            "Keep as a research proposition only. The dossier itself "
            "calls it high-risk — miniaturization may be physically "
            "blocked — and the SNR calculation confirms this. But the "
            "concept is genuinely novel and the feasibility test is "
            "decisive and fast. Show it only to academic or NMR "
            "research groups as a co-development opportunity, not as "
            "a near-term commercial prospect."),
        "specialist_buyer_profile": (
            "academic or NMR research groups (co-development "
            "proposition)"),
        "record_verified_basis": [
            {"scope": "ENGINE",
             "pointer": "R370Q/final_consultant_package/export/"
                        "P-29_ArtifactRichDossier.json",
             "span": "miniaturization to catheter scale may be "
                     "physically blocked",
             "claim": "the dossier's own honest assessment (verbatim: "
                      "high-risk concept)"},
            {"scope": "PACKAGE", "pointer": "MODEL/DESIGN_LINEAGE.json",
             "span": "SNR insufficient at low B0",
             "claim": "the record's failure mode: SNR insufficient at "
                      "low B0 (B0 UNKNOWN, likely 0.1-1 T for "
                      "miniaturization)"},
            {"scope": "ENGINE", "pointer": _CONSULTANT_REPORT,
             "span": "| P15 | MR Flow Sensor | YES | REPOSITION | "
                     "SPONSOR_SMALL_VAL |",
             "claim": "consultant verdict REPOSITION; top blocker "
                      "'SNR calc suggests kill triggered; "
                      "miniaturization blocked'; decisive test 'SNR "
                      "feasibility test at 0.5T and 1.0T (expect "
                      "negative)'"},
        ],
        "ceo_stated_basis": [
            {"claim": "$5K feasibility test (magnet, coil, phantom)",
             "note": "CEO budget directive — the record carries cost "
                     "NOT_ESTABLISHED"},
            {"claim": "genuinely novel concept",
             "note": "CEO qualitative judgment"},
        ],
        "consultant_verdict": {
            "wc_dossier": "YES", "verdict": "REPOSITION",
            "transaction": "SPONSOR_SMALL_VAL",
            "top_blocker": "SNR calc suggests kill triggered; "
                           "miniaturization blocked",
            "decisive_next_experiment": (
                "SNR feasibility test at 0.5T and 1.0T (expect "
                "negative)"),
        },
        "agreement": "ALIGNED (REPOSITION, research proposition)",
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_BY_NUM = {row["num"]: row for row in PACKAGE_MAP}


def buyer_rows() -> List[Dict[str, str]]:
    """The 4 BUYER_PRIMARY rows in CEO presentation order."""
    return [_BY_NUM[n] for n in BUYER_ORDER]


def buyer_package_ids() -> List[str]:
    return [DISPOSITIONS[n]["pkg_id"] for n in BUYER_ORDER]


def state_of(num: str) -> str:
    return DISPOSITIONS[num]["state"]


def state_dir_for(state: str) -> Optional[str]:
    return STATE_DIRS.get(state)


def folder_for(num: str) -> str:
    row = _BY_NUM[num]
    return folder_name(row["num"], row["short"])


def package_location(portfolio_root: str, num: str) -> Tuple[str, str]:
    """(absolute package dir, relative-to-root dir) for a package num,
    resolved from the disposition record when present (fallback:
    DOWNLOAD for pre-R382 trees)."""
    row = _BY_NUM[num]
    folder = folder_name(row["num"], row["short"])
    rec_fp = os.path.join(portfolio_root, DISPOSITION_RECORD_NAME)
    if os.path.exists(rec_fp):
        try:
            with open(rec_fp, encoding="utf-8") as fh:
                rec = json.load(fh)
            entry = (rec.get("dispositions") or {}).get(num) or {}
            loc = entry.get("location")
            if loc:
                return (os.path.join(portfolio_root, loc, folder),
                        os.path.join(loc, folder))
        except (OSError, ValueError):
            pass
    return (os.path.join(portfolio_root, "DOWNLOAD", folder),
            os.path.join("DOWNLOAD", folder))


def _sha256_file(fp: str) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(fp: str, obj: Any) -> None:
    with open(fp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def _freeze_identity(pdir: str, zpath: str) -> Dict[str, Any]:
    """Identity digest of a package folder + zip, computed from disk."""
    return {
        "package_manifest_sha256": _sha256_file(
            os.path.join(pdir, "PACKAGE_MANIFEST.json")),
        "package_zip_sha256": _sha256_file(zpath),
        "dossier_sha256": _sha256_file(
            os.path.join(pdir,
                         "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER."
                         "pdf")),
        "file_count": sum(
            len(fs) for _r, _d, fs in os.walk(pdir)),
    }


# ---------------------------------------------------------------------------
# The structural applier
# ---------------------------------------------------------------------------
def apply_portfolio_disposition(portfolio_root: str,
                                statuses: Optional[Dict[str, str]] = None
                                ) -> Dict[str, Any]:
    """Apply the CEO disposition to a BUILT portfolio tree.

    1. verify all 15 package folders + ZIPs exist in DOWNLOAD/
    2. snapshot the pre-disposition buyer release into
       RELEASE/history_r381/ (root docs + the 15-package master ZIP;
       history is evidence, Art. XI)
    3. move the 11 non-buyer folders + ZIPs into their state
       directories — MOVED, never rewritten: the frozen bytes keep the
       R381 acceptance results valid for every moved package
    4. write PORTFOLIO_DISPOSITION.json — the authoritative decision
       record with frozen identity hashes + the full evidence chain
    5. rebuild the buyer-scoped PORTFOLIO_IDENTITY_REGISTRY.json (the
       shipped registry describes exactly what the buyer release
       contains)

    Root release documents (index/report/manifest/README/master ZIP)
    are regenerated afterwards by r382.release_docs (needs the
    canonical in-memory build objects).
    """
    download = os.path.join(portfolio_root, "DOWNLOAD")

    # 1. verify the working portfolio is complete -------------------------
    for row in PACKAGE_MAP:
        folder = folder_name(row["num"], row["short"])
        for fp in (os.path.join(download, folder),
                   os.path.join(download, folder + ".zip")):
            if not os.path.exists(fp):
                raise FileNotFoundError(
                    f"cannot apply disposition: {fp} missing (the "
                    f"15-package working portfolio must be built "
                    f"first)")

    # 2. history snapshot of the pre-disposition buyer release ------------
    hist = os.path.join(portfolio_root, "RELEASE", "history_r381")
    os.makedirs(hist, exist_ok=True)
    _history_files = (
        "README.md",
        "PORTFOLIO_IDENTITY_REGISTRY.json",
        "RELEASE_CONTENT_MANIFEST.json",
        "PORTFOLIO_MANIFEST.json",
        "PORTFOLIO_RANKING.json",
        "00_PORTFOLIO_15_TECHNOLOGIES.pdf",
        "PORTFOLIO_INDEX.pdf",
        "PORTFOLIO_RELEASE_REPORT.pdf",
    )
    moved_history: List[str] = []
    for fn in _history_files:
        src = os.path.join(portfolio_root, fn)
        if os.path.exists(src):
            shutil.move(src, os.path.join(hist, fn))
            moved_history.append(fn)
    master_zip_name = "technology-transfer-portfolio-15.zip"
    mz_src = os.path.join(download, master_zip_name)
    if os.path.exists(mz_src):
        # preserve the exact 15-package master ZIP (its sha256 is the
        # one recorded in RELEASE/R371_RELEASE_CANDIDATE.json)
        hist_dl = os.path.join(hist, "DOWNLOAD")
        os.makedirs(hist_dl, exist_ok=True)
        shutil.move(mz_src, os.path.join(hist_dl, master_zip_name))
        moved_history.append(f"DOWNLOAD/{master_zip_name}")
    for fn in ("R371_RELEASE_CANDIDATE.json",):
        src = os.path.join(portfolio_root, "RELEASE", fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(hist, fn))
    for fn in ("R371_ACCEPTANCE_REPORT.json",
               "R381_3D_DESIGN_AUDIT.json"):
        src = os.path.join(portfolio_root, "INTERNAL_QA", fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(hist, fn))
    _write_json(os.path.join(hist, "HISTORY_NOTE.json"), {
        "artifact": "R381_RELEASE_HISTORY_SNAPSHOT",
        "what_this_is": (
            "the pre-disposition R371/R381 buyer release: 15 "
            "packages, all PRESENT_AND_VALIDATED 3D designs, "
            "acceptance 16/16 PASS. Superseded by the R382 CEO "
            "portfolio disposition (buyer release = 4 primary "
            "packages)."),
        "superseded_by": DISPOSITION_RECORD_NAME,
        "preserved_here": moved_history,
        "package_bytes": (
            "the 11 non-buyer package folders + ZIPs were MOVED "
            "(byte-identical, never rewritten) to HOLDING/, "
            "SPECIALIST_TRACK/ and RETIRED/; their per-package "
            "acceptance results remain valid for the frozen bytes"),
        "provenance": "git history (Art. XI)",
    })

    # 3. move the non-buyer packages --------------------------------------
    frozen: Dict[str, Dict[str, Any]] = {}
    for num, disp in DISPOSITIONS.items():
        state = disp["state"]
        if state == "BUYER_PRIMARY":
            pdir = os.path.join(download, folder_for(num))
            frozen[num] = _freeze_identity(
                pdir, os.path.join(download, folder_for(num) + ".zip"))
            frozen[num]["location"] = "DOWNLOAD"
            continue
        sdir = STATE_DIRS[state]
        dest_root = os.path.join(portfolio_root, sdir)
        os.makedirs(dest_root, exist_ok=True)
        folder = folder_for(num)
        pdir = os.path.join(download, folder)
        zpath = os.path.join(download, folder + ".zip")
        frozen[num] = _freeze_identity(pdir, zpath)
        frozen[num]["location"] = sdir
        shutil.move(pdir, os.path.join(dest_root, folder))
        shutil.move(zpath, os.path.join(dest_root, folder + ".zip"))

    # 4. the authoritative disposition record ------------------------------
    record = {
        "artifact": "PORTFOLIO_DISPOSITION",
        "r382_version": R382_VERSION,
        "ceo_directive": {
            "date": CEO_DIRECTIVE_DATE,
            "authority": "CEO portfolio disposition (R382)",
            "one_line": (
                "Show now: 04, 11, 13, 08 (these four are the buyer "
                "portfolio). Hold: 01, 02, 09, 12 (one specific gate "
                "each). Retire: 06, 07, 10, 14. Separate track: 03, "
                "05, 15 (real ideas, wrong buyer audience)."),
        },
        "implementation_policy": {
            "delete_means": (
                "retired from the buyer release: absent from "
                "DOWNLOAD/, the buyer manifest, README and the master "
                "ZIP; bytes preserved in RETIRED/ because history is "
                "evidence (Constitution Art. XI)"),
            "hold_means": (
                "not buyer-visible until the recorded gate condition "
                "is met; the gate, its decisive test and the failure "
                "consequence are recorded per package"),
            "specialist_track_means": (
                "not in the industrial buyer deck; kept for a "
                "separate specialist outreach track with a recorded "
                "buyer profile"),
            "buyer_release": (
                "DOWNLOAD/ contains exactly the BUYER_PRIMARY "
                "packages in CEO presentation order; the master ZIP "
                "is built from the buyer-scoped release manifest"),
            "evidence_policy": (
                "record_verified_basis entries are machine-verified "
                "against exact file + exact span (see "
                "verify_disposition); ceo_stated_basis entries are "
                "CEO business judgments and are never presented as "
                "record evidence; dollar figures are CEO budget "
                "directives — the record's cost basis is "
                "NOT_ESTABLISHED for every package (Art. XXVII)"),
            "consultant_verdicts": (
                "the independent consultant's Part 9 verdict table is "
                "carried verbatim per package; the four cases where "
                "the CEO disposition is stricter than the consultant "
                "verdict are flagged CEO_OVERRIDE_DISCLOSED (Art. XV) "
                "and never silently overridden"),
        },
        "counts": {
            "buyer_primary": sum(1 for d in DISPOSITIONS.values()
                                 if d["state"] == "BUYER_PRIMARY"),
            "hold_pending_gate": sum(
                1 for d in DISPOSITIONS.values()
                if d["state"] == "HOLD_PENDING_GATE"),
            "specialist_track": sum(
                1 for d in DISPOSITIONS.values()
                if d["state"] == "SPECIALIST_TRACK"),
            "retired": sum(
                1 for d in DISPOSITIONS.values()
                if d["state"].startswith("RETIRED")),
        },
        "provenance": {
            "generated_by": "premium_package_factory.r382.disposition",
            "evidence_legend": {
                "scope PACKAGE": (
                    "pointer is a file inside the package folder; "
                    "span must appear verbatim in it"),
                "scope ENGINE": (
                    "pointer is relative to the engine repo root; "
                    "span must appear verbatim in it"),
                "scope ENGINE_ABSENCE": (
                    "pointer resolves; every absent_pattern must NOT "
                    "appear in it (the verified absence IS the claim)"),
            },
        },
        "dispositions": {
            num: dict(disp,
                      portfolio_number=num,
                      folder=folder_for(num),
                      location=frozen[num]["location"],
                      frozen_identity=frozen[num])
            for num, disp in DISPOSITIONS.items()
        },
    }
    _write_json(os.path.join(portfolio_root, DISPOSITION_RECORD_NAME),
                record)

    # 5. buyer-scoped identity registry ------------------------------------
    from ..r371.identity import build_registry, write_registry
    registry = build_registry(
        portfolio_root, statuses=statuses, rows=buyer_rows(),
        location_map={n: "DOWNLOAD" for n in BUYER_ORDER})
    write_registry(portfolio_root, registry)

    return {
        "r382_version": R382_VERSION,
        "buyer_primary": [folder_for(n) for n in BUYER_ORDER],
        "moved": {n: frozen[n]["location"] for n in DISPOSITIONS
                  if DISPOSITIONS[n]["state"] != "BUYER_PRIMARY"},
        "history_snapshot": hist,
        "record_path": os.path.join(portfolio_root,
                                    DISPOSITION_RECORD_NAME),
    }


# ---------------------------------------------------------------------------
# The machine verifier (used by acceptance condition 18 + tests)
# ---------------------------------------------------------------------------
def _resolve_span(scope: str, pointer: str, span: Optional[str],
                  portfolio_root: str,
                  package_dir: Optional[str]) -> Optional[str]:
    """Resolve one evidence pointer; return an error string or None."""
    if scope == "PACKAGE":
        if package_dir is None:
            return f"PACKAGE pointer but package dir unresolved"
        fp = os.path.join(package_dir, pointer)
        if not os.path.exists(fp):
            return f"missing file {pointer}"
        try:
            with open(fp, encoding="utf-8") as fh:
                return None if span in fh.read() else (
                    f"span not found in {pointer}: {span[:60]!r}")
        except (OSError, UnicodeDecodeError):
            return f"unreadable {pointer}"
    if scope in ("ENGINE", "ENGINE_ABSENCE"):
        fp = os.path.join(ENGINE_ROOT, pointer)
        if not os.path.exists(fp):
            return f"missing engine file {pointer}"
        try:
            with open(fp, encoding="utf-8") as fh:
                content = fh.read()
        except (OSError, UnicodeDecodeError):
            return f"unreadable engine file {pointer}"
        if scope == "ENGINE":
            return None if span in content else (
                f"span not found in {pointer}: {span[:60]!r}")
        # ENGINE_ABSENCE: every absent_pattern must NOT appear
        for pat in (span and []) or []:
            pass
        return None
    return f"unknown scope {scope}"


def _verify_evidence_entry(entry: Dict[str, Any],
                           package_dir: Optional[str],
                           portfolio_root: str) -> List[str]:
    scope = entry.get("scope")
    pointer = entry.get("pointer") or ""
    errs: List[str] = []
    if scope == "ENGINE_ABSENCE":
        fp = os.path.join(ENGINE_ROOT, pointer)
        if not os.path.exists(fp):
            return [f"missing engine file {pointer}"]
        with open(fp, encoding="utf-8") as fh:
            content = fh.read()
        for pat in entry.get("absent_patterns") or []:
            if pat in content:
                errs.append(
                    f"ABSENCE claim broken: '{pat}' IS present in "
                    f"{pointer}")
        return errs
    err = _resolve_span(scope, pointer, entry.get("span"),
                        portfolio_root, package_dir)
    if err:
        errs.append(err)
    return errs


def verify_disposition(portfolio_root: str,
                      require_release: bool = True) -> Dict[str, Any]:
    """Mechanically verify the disposition against the ACTUAL tree:

    A. record integrity: exists, R382 version, 15 entries, legal
       states, buyer set == 4 == CEO presentation order
    B. physical structure: DOWNLOAD holds EXACTLY the 4 buyer folders
       (+ master ZIP); every non-buyer package lives in its state dir
       with folder + ZIP
    C. frozen identity: every package's recorded
       package_manifest_sha256 / package_zip_sha256 match the bytes on
       disk (a tampered retired package is CAUGHT)
    D. completeness: every HOLD has a gate condition + decisive test +
       failure consequence; every RETIRED has a reason; 07 has a
       revival condition; 14 has a reposition option
    E. evidence: every record_verified_basis pointer resolves to a
       real file whose content contains the exact span (or, for
       ABSENCE, does not contain the pattern); every ceo_stated_basis
       item carries a note; no dollar figure appears inside
       record_verified claims (anti-laundering)
    F. buyer-release purity: the release manifest contains no
       non-buyer entry; the master ZIP contains no non-buyer package
       path; the README mentions no non-buyer folder
    """
    problems: List[str] = []
    rec_fp = os.path.join(portfolio_root, DISPOSITION_RECORD_NAME)
    if not os.path.exists(rec_fp):
        return {"ok": False, "problems": ["disposition record missing"],
                "rows": []}
    with open(rec_fp, encoding="utf-8") as fh:
        record = json.load(fh)

    disp = record.get("dispositions") or {}

    # A. record integrity --------------------------------------------------
    if record.get("r382_version") != R382_VERSION:
        problems.append(f"record version {record.get('r382_version')}")
    if set(disp) != {f"{i:02d}" for i in range(1, 16)}:
        problems.append(f"dispositions cover {sorted(disp)} != 01..15")
    for num, entry in disp.items():
        if entry.get("state") not in STATES:
            problems.append(f"{num}: illegal state {entry.get('state')}")
        if entry.get("pkg_id") != _BY_NUM[num]["pkg_id"]:
            problems.append(f"{num}: pkg_id drift {entry.get('pkg_id')}")
    buyer = [n for n, e in disp.items()
             if e.get("state") == "BUYER_PRIMARY"]
    ordered = sorted(
        buyer, key=lambda n: disp[n].get("presentation_order") or 99)
    if ordered != BUYER_ORDER:
        problems.append(f"buyer set {ordered} != CEO order {BUYER_ORDER}")

    # B. physical structure ------------------------------------------------
    download = os.path.join(portfolio_root, "DOWNLOAD")
    dl_dirs = sorted(
        d for d in os.listdir(download)
        if os.path.isdir(os.path.join(download, d)))
    expected_dl = sorted(folder_for(n) for n in buyer)
    if dl_dirs != expected_dl:
        problems.append(
            f"DOWNLOAD folders {dl_dirs} != buyer set {expected_dl}")
    for num, entry in disp.items():
        folder = entry.get("folder") or folder_for(num)
        loc = entry.get("location")
        state = entry.get("state")
        expected_loc = "DOWNLOAD" if state == "BUYER_PRIMARY" else \
            STATE_DIRS.get(state)
        if loc != expected_loc:
            problems.append(f"{num}: location {loc} != {expected_loc}")
        pdir = os.path.join(portfolio_root, loc, folder) if loc else None
        zpath = os.path.join(portfolio_root, loc, folder + ".zip") \
            if loc else None
        if not pdir or not os.path.isdir(pdir):
            problems.append(f"{num}: package folder missing at {loc}")
            continue
        if not zpath or not os.path.exists(zpath):
            problems.append(f"{num}: package ZIP missing at {loc}")

        # C. frozen identity (tamper detection) ---------------------------
        fi = entry.get("frozen_identity") or {}
        if fi.get("package_manifest_sha256"):
            actual = _sha256_file(
                os.path.join(pdir, "PACKAGE_MANIFEST.json"))
            if actual != fi["package_manifest_sha256"]:
                problems.append(
                    f"{num}: frozen manifest hash drift (bytes "
                    f"changed after the disposition)")
        if fi.get("package_zip_sha256") and zpath and \
                os.path.exists(zpath):
            actual = _sha256_file(zpath)
            if actual != fi["package_zip_sha256"]:
                problems.append(f"{num}: frozen ZIP hash drift")
        if fi.get("dossier_sha256"):
            dpath = os.path.join(
                pdir, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf")
            if os.path.exists(dpath):
                if _sha256_file(dpath) != fi["dossier_sha256"]:
                    problems.append(f"{num}: frozen dossier hash drift")

        # D. completeness per state ---------------------------------------
        if state == "HOLD_PENDING_GATE":
            gate = entry.get("gate") or {}
            for must in ("condition", "decisive_test",
                         "gate_failure_consequence"):
                if not gate.get(must):
                    problems.append(f"{num}: hold gate missing {must}")
        if state == "RETIRED":
            if not entry.get("retirement_reason"):
                problems.append(f"{num}: retired without reason")
        if state == "RETIRED_PENDING_DECISIVE_TEST":
            if not entry.get("retirement_reason"):
                problems.append(f"{num}: retired without reason")
            rv = entry.get("revival_condition") or {}
            for must in ("condition", "decisive_test",
                         "failure_consequence"):
                if not rv.get(must):
                    problems.append(
                        f"{num}: revival condition missing {must}")
        if state == "SPECIALIST_TRACK":
            if not entry.get("specialist_buyer_profile"):
                problems.append(
                    f"{num}: specialist track without buyer profile")
        if not (entry.get("record_verified_basis") or []):
            problems.append(f"{num}: no record-verified evidence")
        if not entry.get("consultant_verdict"):
            problems.append(f"{num}: consultant verdict missing")

        # E. evidence resolution ------------------------------------------
        for ev in entry.get("record_verified_basis") or []:
            for err in _verify_evidence_entry(ev, pdir, portfolio_root):
                problems.append(f"{num}: {err}")
        for st in entry.get("ceo_stated_basis") or []:
            if not st.get("note"):
                problems.append(
                    f"{num}: CEO-stated claim without attribution note")
            if "$" in json.dumps(st.get("claim", "")) and \
                    "$" in json.dumps(
                        (entry.get("record_verified_basis") or [])):
                problems.append(f"{num}: dollar figure near record claims")

    # E-anti-laundering: no dollar figure inside record_verified claims
    for num, entry in disp.items():
        for ev in entry.get("record_verified_basis") or []:
            if "$" in str(ev.get("claim", "")):
                problems.append(
                    f"{num}: dollar figure in a record-verified claim "
                    f"(laundering risk)")

    # F. buyer-release purity ----------------------------------------------
    # (require_release=False covers the apply-only stage, before the
    # release layer is regenerated; the acceptance gate always runs
    # with the full check)
    mfp = os.path.join(portfolio_root, "RELEASE_CONTENT_MANIFEST.json")
    non_buyer_folders = {
        (e.get("folder") or folder_for(n))
        for n, e in disp.items()
        if e.get("state") != "BUYER_PRIMARY"}
    if os.path.exists(mfp):
        with open(mfp, encoding="utf-8") as fh:
            manifest = json.load(fh)
        for ent in manifest.get("entries") or []:
            if ent.get("role") in ("package folder", "package zip"):
                base = ent["path"].rsplit("/", 1)[-1]
                base = base[:-4] if base.endswith(".zip") else base
                if base in non_buyer_folders:
                    problems.append(
                        f"buyer manifest contains non-buyer package "
                        f"{ent['path']}")
    elif require_release:
        problems.append("RELEASE_CONTENT_MANIFEST.json missing")
    mz = os.path.join(download, "technology-transfer-portfolio-15.zip")
    if os.path.exists(mz):
        with zipfile.ZipFile(mz) as zf:
            names = zf.namelist()
        for name in names:
            for nf in non_buyer_folders:
                if name.startswith(nf):
                    problems.append(
                        f"master ZIP contains non-buyer package {name}")
            for sdir in STATE_DIRS.values():
                if name.startswith(sdir + "/"):
                    problems.append(
                        f"master ZIP contains internal dir {name}")
    rfp = os.path.join(portfolio_root, "README.md")
    if os.path.exists(rfp):
        with open(rfp, encoding="utf-8") as fh:
            readme = fh.read()
        for nf in non_buyer_folders:
            if nf in readme:
                problems.append(f"README mentions non-buyer {nf}")

    rows = [
        {"num": n, "folder": e.get("folder"), "state": e.get("state"),
         "location": e.get("location"), "pkg_id": e.get("pkg_id")}
        for n, e in sorted(disp.items())
    ]
    return {"ok": not problems, "problems": problems[:20], "rows": rows}


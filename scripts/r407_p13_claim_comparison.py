#!/usr/bin/env python3
"""R407-H — the P13 claim-level novelty comparison.

Directive (R407-H): freeze engineering investment; FIRST complete the
claim-level novelty comparison — what exactly is the technical
distinction of P13 relative to Seaver (PA-1) and the other located
architectures. Without an incontrovertible justification: kill. With:
narrow-recorded.

Method (nothing invented — every located-art fact below is a verbatim
span from the COMMITTED R406 search record
LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/NOVELTY_SEARCH_RESULT.json;
every P13 claim element is decomposed from the committed
CLAIM_EVIDENCE_MATRIX / BENCHMARK_SPECIFICATION / pre-registration):

  1. Decompose the P13 architecture claim into elements.
  2. Map each element against PA-1..PA-6 with the committed spans.
  3. Test every distinction candidate mechanically (Art. XLVI classes:
     known / recombined / adapted / transferred / parameterized /
     engineering-realization vs truly distinct).
  4. Verdict + the disposition the R407-H rule prescribes.

Constitutional basis: Art. II (exact evidence beats plausibility —
verbatim spans only), Art. XXI.2 (zero/absence is not novelty),
Art. XXV (unknown stays unknown — the classification-based search was
never run, and that stays UNKNOWN), Art. XXXIII (irreversible action on
unresolved evidence — the KILL recommendation is recorded for the owner,
not executed by the machine), Art. XLVI (causal novelty; transfer/
recombination is not novelty), Art. LXIII (buyer reality: the honest
package tells the owner what is known, unknown, and how to kill).
"""

from __future__ import annotations

import hashlib
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH = os.path.join(REPO, "LEAD_PORTFOLIO_4", "P13",
                      "NOVELTY_SEARCH_R406", "NOVELTY_SEARCH_RESULT.json")
MATRIX = os.path.join(REPO, "LEAD_PORTFOLIO_4", "P13",
                      "CLAIM_EVIDENCE_MATRIX.json")
OUT = os.path.join(REPO, "LEAD_PORTFOLIO_4", "P13",
                   "CLAIM_LEVEL_NOVELTY_COMPARISON_R407.json")


def load(path):
    with open(path) as f:
        return json.load(f)


def write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.write("\n")


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main() -> int:
    search = load(SEARCH)
    matrix = load(MATRIX)

    pa = {r["record_id"].split()[0]: r for r in search["located_prior_art"]}

    # --- 1. the P13 claim elements (decomposed from committed records) --
    elements = [
        {
            "id": "E1",
            "element": "dual matched piezoresistive sensing elements "
                       "(one stress-active, one reference/dummy) mounted "
                       "on a common carrier substrate",
            "p13_source": "CLAIM_EVIDENCE_MATRIX row 2 (the self-"
                          "referencing bridge) + BENCHMARK_SPECIFICATION "
                          "(sensor die + reference die + carrier)",
            "located_in": [
                {"art": "PA-1 (Seaver 2018 dissertation)",
                 "verbatim": "the sensor dies are colocated upon a common "
                             "mounting substrate whereby stresses become "
                             "common mode. By virtue of the sensors' cross "
                             "coupled outputs ... each sensor's transfer "
                             "function must be substantially identical to "
                             "the other and therefore necessitates matched "
                             "silicon dies.",
                 "status": "RECITED"},
                {"art": "PA-2 (US4320664, 1982)",
                 "verbatim": "a first resistor disposed in a central "
                             "portion of said diaphragm portion, a second "
                             "resistor connected to said first resistor "
                             "and disposed in a peripheral portion of "
                             "said diaphragm portion ...",
                 "status": "RECITED (component form)"},
            ],
            "verdict": "LOCATED",
        },
        {
            "id": "E2",
            "element": "differential readout that subtracts the common-"
                       "mode (thermal/stress) error between the two "
                       "elements (bridge / cross-coupled outputs)",
            "p13_source": "CLAIM_EVIDENCE_MATRIX row 2: V_out = "
                          "(R_active - R_dummy)/(4R)*V_ex",
            "located_in": [
                {"art": "PA-1",
                 "verbatim": "the total output signal becomes the "
                             "superposition of the two sensors, "
                             "subtracting out the common stress.",
                 "status": "RECITED"},
                {"art": "PA-2",
                 "verbatim": "A thermally compensated silicon pressure "
                             "sensor ... (bridge with central stress-"
                             "active and peripheral reference elements)",
                 "status": "RECITED (the classic dummy-element bridge "
                           "compensation)"},
            ],
            "verdict": "LOCATED",
        },
        {
            "id": "E3",
            "element": "the reference element is shielded/sealed from the "
                       "measured pressure medium (absolute-reference / "
                       "shielded-dummy configuration)",
            "p13_source": "BENCHMARK_SPECIFICATION: exposed-active + "
                          "shielded-dummy element pair",
            "located_in": [
                {"art": "PA-1",
                 "verbatim": "Figure 21 - Independent dual sensor with "
                             "absolute reference configuration for error "
                             "compensation.",
                 "status": "RECITED (absolute-reference configuration)"},
                {"art": "PA-5 (US11422051B2)",
                 "verbatim": "the pressure sensor is located in the "
                             "housing and within an enclosure and sealed "
                             "from the chamber ... a sealed cavity "
                             "divided from the chamber by the flexible "
                             "wall portion ...",
                 "status": "RECITED (sealed reference architecture, "
                           "mechanical form)"},
            ],
            "verdict": "LOCATED",
        },
        {
            "id": "E4",
            "element": "deployment context: CSF shunt / ventricular "
                       "catheter intracranial pressure monitoring",
            "p13_source": "BENCHMARK_SPECIFICATION + EXPERIMENT_"
                          "PREREGISTRATION (shunt-valve bench)",
            "located_in": [
                {"art": "PA-1",
                 "verbatim": "Figure 23 - Biopressure transponder "
                             "deployment with ventricular catheter.",
                 "status": "RECITED"},
                {"art": "PA-4 (US11701504B2)",
                 "verbatim": "A hydrocephalus shunt pressure sensing "
                             "apparatus comprising: a ventricular "
                             "catheter; ... an electronic pressure "
                             "sensor ...",
                 "status": "RECITED"},
            ],
            "verdict": "LOCATED",
        },
        {
            "id": "E5",
            "element": "catheter-integrated MEMS realization (0.07 mm "
                       "diaphragm die pair on one carrier, shipped CAD)",
            "p13_source": "CLAIM_EVIDENCE_MATRIX row 5 (GEOMETRY_"
                          "REVERIFICATION_EVIDENCE)",
            "located_in": [],
            "verdict": "NOT_LOCATED",
            "art_xxi_2_caveat": "absence in THIS keyword search is not "
                                "novelty; and per Art. XLVI an "
                                "engineering-realization/parameterization "
                                "(die geometry, integration density) is "
                                "not a causal-mechanism distinction",
        },
        {
            "id": "E6",
            "element": "the asymmetric-fouling (non-common-mode) channel "
                       "explicitly recorded as NOT compensated and pre-"
                       "registered as the paired-die benchmark's kill-"
                       "condition arm",
            "p13_source": "CLAIM_EVIDENCE_MATRIX row 3 (P-25 kill "
                          "channel KA-014) + EXPERIMENT_"
                          "PREREGISTRATION fouling arm",
            "located_in": [],
            "verdict": "NOT_LOCATED",
            "art_xxi_2_caveat": "the R406 record's what_was_NOT_located "
                                "confirms no located art addresses the "
                                "asymmetric-fouling channel; NOTE P13 "
                                "does not CLAIM to compensate it — the "
                                "honest package records it as "
                                "uncompensated",
        },
    ]

    # --- 2. the distinction candidates, tested mechanically -----------
    distinctions = [
        {
            "candidate": "A. the exposed-active + shielded-dummy pair in "
                         "the SAME fouling medium, with the asymmetric-"
                         "fouling channel as the pre-registered measured "
                         "endpoint",
            "test": "Art. XLVI class: is this a new causal mechanism, or "
                    "a measurement-protocol/experiment-design "
                    "distinction over the located dual-element art?",
            "result": "MEASUREMENT-PROTOCOL DISTINCTION, not a new "
                      "causal mechanism: PA-1 already places matched "
                      "dual elements with an absolute reference in the "
                      "ventricular catheter; adding a fouling-asymmetry "
                      "measurement arm designs the EXPERIMENT, not a new "
                      "compensation mechanism — and P13 itself records "
                      "the channel as NOT compensated (it is the "
                      "predecessor P-25's kill channel KA-014).",
            "incontrovertible": False,
        },
        {
            "candidate": "B. catheter-integrated 0.07 mm MEMS diaphragm "
                         "realization (the shipped CAD)",
            "test": "Art. XLVI class: engineering realization vs "
                    "mechanism; Art. XXIX: implementation vs mechanism.",
            "result": "ENGINEERING REALIZATION: diaphragm thickness and "
                      "integration density are design variables of the "
                      "SAME piezoresistive matched-pair mechanism "
                      "(E1-E4). Not located in the art does not make "
                      "the mechanism distinct — it makes the packaging "
                      "objective un-located.",
            "incontrovertible": False,
        },
        {
            "candidate": "C. drift target < 0.5 mmHg/month",
            "test": "Art. XXVII: a MODEL_DERIVED target is not a "
                    "distinction at all.",
            "result": "NOT A DISTINCTION: a declared target with "
                      "MODEL_DERIVED provenance; no evidence class "
                      "behind it (the matrix records it so).",
            "incontrovertible": False,
        },
    ]

    # --- 3. verdict + disposition ---------------------------------------
    comparison = {
        "artifact_type": "CLAIM_LEVEL_NOVELTY_COMPARISON",
        "directive_basis": "R407-H: freeze engineering investment; "
                           "complete the claim-level comparison; without "
                           "an incontrovertible justification: kill; "
                           "with: narrow-recorded.",
        "company_designation": "P13",
        "historical_package_id": "P-27-R1",
        "technology_name": search["technology_name"],
        "inputs_of_record": {
            "novelty_search_record": {
                "path": "LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/"
                        "NOVELTY_SEARCH_RESULT.json",
                "sha256": sha256_file(SEARCH),
                "verdict": search["determination"]["verdict"],
            },
            "claim_evidence_matrix": {
                "path": "LEAD_PORTFOLIO_4/P13/CLAIM_EVIDENCE_MATRIX.json",
                "sha256": sha256_file(MATRIX),
            },
        },
        "claim_elements": elements,
        "claim_level_summary": {
            "elements_located": ["E1", "E2", "E3", "E4"],
            "elements_not_located": ["E5", "E6"],
            "the_architecture_family_is_located_art":
                "the full causal architecture P13 relies on — matched "
                "dual elements (E1), differential common-mode "
                "cancellation (E2), a shielded/absolute reference "
                "element (E3), in the CSF-shunt deployment context (E4) "
                "— is recited verbatim across PA-1 (Seaver 2018), PA-2 "
                "(US4320664), PA-4 (US11701504B2), and PA-5 "
                "(US11422051B2).",
            "what_is_actually_left":
                "E5 (engineering realization: 0.07 mm MEMS diaphragm "
                "CAD) and E6 (the fouling-asymmetry measurement arm — "
                "which P13 records as NOT compensated, i.e., as its own "
                "kill condition, not as a capability).",
        },
        "distinction_candidates_tested": distinctions,
        "verdict": {
            "result": "NO_INCONTROVERTIBLE_TECHNICAL_DISTINCTION",
            "basis": "every distinction candidate tested fails the "
                     "mechanism-level test (Art. XLVI): candidate A is "
                     "a measurement-protocol distinction (and P13 "
                     "records the channel as uncompensated); candidate "
                     "B is an engineering realization; candidate C is a "
                     "model-derived target. None is a new causal "
                     "mechanism over the located art.",
            "per_the_r407_h_rule": "without an incontrovertible "
                                   "justification the disposition is "
                                   "the KILL path; WITH a distinction it "
                                   "would have been narrow-recorded. The "
                                   "narrow-claim that WOULD survive "
                                   "owner counsel review is recorded "
                                   "below as the conditional.",
        },
        "narrow_claim_conditional": {
            "text": "A paired-die implantable pressure sensor method in "
                    "which the DIFFERENCE channel between an exposed "
                    "active element and a shielded dummy element in the "
                    "same fouling medium is used as the measured "
                    "indicator of asymmetric biofouling drift.",
            "status": "CONDITIONAL — this is the only claim shape the "
                      "comparison found that the located art does not "
                      "recite; it is a measurement-method claim, it "
                      "requires owner patent-counsel claim-charting to "
                      "confirm, and it does NOT rescue the compensation "
                      "mechanism claims (E1-E4 remain located art).",
        },
        "disposition": {
            "engineering_spend": "FROZEN (permanent per the R407-H rule; "
                                 "the R406 $95-265K fab-NRE gate stands)",
            "recommended_owner_action":
                "KILL the transfer-item position OR execute the "
                "narrow-claim conditional via patent counsel; consistent "
                "with the R407 external audit's verdict: 'Remove from "
                "buyer surface as a transfer item: P-13 (data-"
                "conditional; repositioned; make it permanent).'",
            "machine_executed_kill": False,
            "why_not_machine_executed":
                "Art. XXXIII: a package kill is an irreversible action; "
                "the classification-based search (the exhaustive "
                "novelty determination, Art. XXVIII) remains UNKNOWN, "
                "and that unresolved evidence could plausibly change "
                "the claim chart — so the machine records the "
                "recommendation and the evidence ledger for the owner, "
                "and does not itself flip the terminal state.",
            "sanctioned_spend_that_remains":
                "the pre-registered paired-die benchmark (P13's "
                "EXPERIMENT_PREREGISTRATION.json) IF the owner wants "
                "the fouling-asymmetry answer measured — as a property "
                "measurement, never as a novelty rescue",
        },
        "honesty_limits": [
            "this comparison uses ONLY the located, committed R406 "
            "search records (verbatim spans); it is a claim-level "
            "comparison against LOCATED art, not a novelty "
            "determination (Art. XXVIII)",
            "no conclusion is drawn from the absence of hits (Art. "
            "XXI.2): E5/E6 'NOT_LOCATED' means not-recited-in-located-"
            "art, nothing stronger",
            "the exhaustive classification-based search remains "
            "UNKNOWN and stays unknown (Art. XXV)",
            "the R406 search was keyword/web-based; paywalled "
            "classification databases were not searched (PatSnap "
            "exhausted, Patent-Bear meter 2/20 — recorded in the R406 "
            "search record)",
        ],
        "constitutional_basis": "Art. II, XXI.2, XXV, XXVIII, XXXIII, "
                                "XLVI, LIV, LXIII",
        "generator": "scripts/r407_p13_claim_comparison.py",
    }

    write_json(OUT, comparison)
    print(f"wrote {OUT}")
    print(f"verdict: {comparison['verdict']['result']}")
    print("E1-E4 LOCATED (architecture family = located art); "
          "E5/E6 NOT_LOCATED (engineering realization / measurement "
          "protocol)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

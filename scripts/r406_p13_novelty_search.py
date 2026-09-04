#!/usr/bin/env python3
"""R406 Step 7 — the P13 specific novelty search record.

Directive: "P13 novelty is a hard gate. Do not spend large engineering
effort until the specific novelty assessment exists. Use the available
Patent-Bear queries. Search specifically for: self-referencing
piezoresistive pressure sensor / intracranial pressure / dummy-reference
element / bridge compensation / thermal drift / implantable pressure
sensing. Record exact patents and claims. Then determine: SUPPORTED /
CONTESTED / INCONCLUSIVE. Never infer novelty from zero search hits
alone."

Executed 2026-09-04: 7 live z-ai web_search queries (including both
R405-recorded Patent-Bear query strings) + direct Google Patents claim
fetches + retrieval of the decisive public dissertation. Raw provider
outputs and exact claim sections are committed under
LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/raw_results/ (provenance
custody per Art. XXI.9).

Constitutional basis: Art. XXI (search activity is not evidence until
relevance is adjudicated; zero hits are not novelty), Art. XXV (unknown
stays unknown), Art. XXVIII (a patent search result is NOT a novelty
determination — that requires an exhaustive classification search),
Art. XLVI (a mechanism adapted/transferred is not novel merely because
the domain changed).
"""
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406"


def sha(rel):
    h = hashlib.sha256()
    with open(os.path.join(REPO, rel), "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


RECORD = {
    "artifact_type": "PRIOR_ART_SEARCH_RESULT",
    "company_designation": "P13",
    "historical_package_id": "P-27-R1",
    "portfolio_number": "13",
    "technology_name": "Self-Referencing Piezoresistive Pressure Sensor",
    "search_execution": {
        "date": "2026-09-04",
        "provider": "z-ai web_search (live) + direct Google Patents retrieval (curl) + direct institutional-repository retrieval (trace.tennessee.edu)",
        "queries_executed": [
            {"id": "Q1", "string": "self-referencing piezoresistive pressure sensor dummy reference element bridge compensation patent", "directive_term_coverage": ["self-referencing piezoresistive", "dummy/reference element", "bridge compensation"], "results": 10},
            {"id": "Q2", "string": "intracranial pressure sensor implantable piezoresistive drift compensation patent", "directive_term_coverage": ["intracranial pressure", "thermal/drift", "implantable pressure sensing"], "results": 9},
            {"id": "Q3", "string": "wheatstone bridge dummy element common-mode thermal drift cancellation CSF shunt ICP sensor", "directive_term_coverage": ["the R405-recorded Patent-Bear SPECIFIC query, verbatim"], "results": 8, "icp_specific_results": 0},
            {"id": "Q4", "string": "piezoresistive pressure sensor self-referencing drift compensation implantable intracranial", "directive_term_coverage": ["the R405-recorded Patent-Bear BROAD query, verbatim"], "results": 9},
            {"id": "Q5", "string": "implantable pressure sensor reference element sealed cavity bridge temperature compensation patent", "directive_term_coverage": ["reference element", "implantable"], "results": 9},
            {"id": "Q6", "string": "\"dual\" implantable pressure sensor reference sensing element drift differential biopressure", "directive_term_coverage": ["dummy/reference element", "thermal drift"], "results": 8},
            {"id": "Q7", "string": "intracranial pressure sensor long-term drift biofouling in vivo accuracy months", "directive_term_coverage": ["intracranial pressure", "thermal drift", "implantable pressure sensing"], "results": 8},
        ],
        "raw_outputs_committed": [f"{BASE}/raw_results/p13_q{n}.json" for n in range(1, 8)],
        "claims_committed": [f"{BASE}/raw_results/{p}_claims.txt" for p in ("US11701504B2", "WO2014076620A2", "US4320664", "US11422051B2")],
        "honesty_limits": "keyword web search, NOT an exhaustive classification search (Art. XXVIII); Google-Patents-page claim extraction (span fidelity verified by the committed claim-section files); paywalled databases (PatSnap account exhausted per the R354 record; Patent-Bear meter 2/20 — NOT used this round, free sources per the recorded plan)",
    },

    "located_prior_art": [
        {
            "record_id": "PA-1 (dissertation — DECISIVE)",
            "identifier": "Seaver, Chad Eric (2018). 'An Implantable Low Pressure, Low Drift, Dual BioPressure Sensor and In-Vivo Calibration Methods Thereof.' PhD dissertation, University of Tennessee, Knoxville.",
            "url": "https://trace.tennessee.edu/entities/publication/3c97711e-af7b-429a-bba4-544bb2f43703",
            "pdf_url": "https://trace.tennessee.edu/bitstreams/fdb3dc18-176b-49d1-8608-116cfab8157c/download",
            "retrieved": "2026-09-04 direct fetch",
            "verbatim_spans": [
                "develops a new novel sensing technology, and evaluates the same for potentially facilitating long-term implantable ICP sensing ... this dissertation proposes and evaluates a dual [sensor configuration] (abstract)",
                "In the dual sensor configuration shown in Figure 19, the sensor dies are colocated upon a common mounting substrate whereby stresses become common mode. By virtue of the sensors' cross coupled outputs, as shown in Figure 20, the total output signal becomes the superposition of the two sensors, subtracting out the common stress. In order to do so, each sensor's transfer function must be substantially identical to the other and therefore necessitates matched silicon dies.",
                "Performance matched sensors use die taken from the same silicon wafer, since error characteristics are predominately process related [120].",
                "Figure 21 - Independent dual sensor with absolute reference configuration for error compensation.",
                "Figure 23 - Biopressure transponder deployment with ventricular catheter.",
            ],
            "relevance_adjudication": "DIRECTLY RELEVANT: an implantable, low-drift, DUAL matched-die pressure sensor with common-mode error subtraction (cross-coupled outputs), an absolute-reference configuration, and ventricular-catheter (CSF shunt) deployment — the same causal architecture family as P13 (dual matched elements, differential cancellation of common-mode drift, ICP/shunt context), published 2018 with in-vivo calibration methods and six-month drift results. This contests P13's architecture-level novelty directly.",
        },
        {
            "record_id": "PA-2 (patent)",
            "identifier": "US4320664 — 'Thermally compensated silicon pressure sensor' (granted 1982)",
            "url": "https://patents.google.com/patent/US4320664/en",
            "claims_file": f"{BASE}/raw_results/US4320664_claims.txt",
            "verbatim_claim_1_span": "1. A thermally compensated silicon pressure sensor comprising: (a) a single crystal of silicon including: (1) a diaphragm portion ... having a continuous loop resistor element disposed adjacent to said top surface in a position for exhibiting piezoresistivity when said diaphragm is flexed, a first resistor disposed in a central portion of said diaphragm portion, a second resistor connected to said first resistor and disposed in a peripheral portion of said diaphragm portion, a third resistor connected to said second resistor and disposed in a central portion of said diaphragm portion and a fourth resistor connected to said first and third resistors and disposed in a peripheral portion of said diaphragm portion ...",
            "relevance_adjudication": "DIRECTLY RELEVANT (component art): the classic piezoresistive bridge with central (stress-active) and peripheral (reference/dummy-class) resistor elements for thermal compensation — the dummy-element bridge compensation technique P13 relies on, in silicon pressure sensors, granted 1982.",
        },
        {
            "record_id": "PA-3 (patent application)",
            "identifier": "WO2014076620A2 — 'Drift compensation for implanted capacitance-based pressure sensors' (Medtronic-class assignee family)",
            "url": "https://patents.google.com/patent/WO2014076620A2/en",
            "claims_file": f"{BASE}/raw_results/WO2014076620A2_claims.txt",
            "verbatim_claim_1_span": "1. A method, comprising: in a living organ in which an ambient pressure varies as a function of time, sensing the ambient pressure using a pressure sensor, which has a capacitance that varies in response to the ambient pressure ... applying to the pressure sensor a calibration voltage that modifies the capacitance ... and calibrating a dependence of the capacitance on the ambient pressure using the measured contribution of the calibration voltage.",
            "relevance_adjudication": "RELEVANT (adjacent): drift compensation for implanted pressure sensors via electrical self-calibration — capacitive, not piezoresistive dummy-element; establishes that implanted-sensor drift compensation is an actively-patented problem space.",
        },
        {
            "record_id": "PA-4 (patent)",
            "identifier": "US11701504B2 — 'Implantable intracranial pressure sensor' (hydrocephalus shunt sensing apparatus)",
            "url": "https://patents.google.com/patent/US11701504B2/en",
            "claims_file": f"{BASE}/raw_results/US11701504B2_claims.txt",
            "verbatim_claim_1_span": "1. A hydrocephalus shunt pressure sensing apparatus comprising: a ventricular catheter; a distal catheter; a reservoir connecting the ventricular catheter and the distal catheter to form a hydrocephalus shunt; a pigtail catheter connected to the ventricular catheter; and a wireless sensor device sensing on the ventricular pigtail catheter, the wireless sensor device comprising: an electronic pressure sensor; a microprocessor connected with the electronic pressure sensor; a wireless data transmitter ...",
            "relevance_adjudication": "RELEVANT (context): implantable ICP sensing on a hydrocephalus shunt with wireless readout — the application context of P13; no self-referencing/dummy-element bridge claim.",
        },
        {
            "record_id": "PA-5 (patent)",
            "identifier": "US11422051B2 — 'Implantable pressure sensor' (sealed-cavity reference architecture)",
            "url": "https://patents.google.com/patent/US11422051B2/en",
            "claims_file": f"{BASE}/raw_results/US11422051B2_claims.txt",
            "verbatim_claim_1_span": "1. A device comprising: a housing enclosing a chamber and having at least one port that communicates with the chamber, a pressure sensor receiving fluid pressure from the chamber ... the pressure sensor is located in the housing and within an enclosure and sealed from the chamber, the enclosure being filed with an incompressible liquid ... a sealed cavity divided from the chamber by the flexible wall portion ...",
            "relevance_adjudication": "RELEVANT (adjacent): a sealed reference chamber/cavity architecture for an implantable pressure sensor — a MECHANICAL reference (not a piezoresistive dummy element); establishes reference-element architectures for implants in the patent literature.",
        },
        {
            "record_id": "PA-6 (literature context)",
            "identifier": "Chronically Implanted Pressure Sensors: Challenges and (PMC4279503); Neurovent-P-tel long-term reliability (scispace); 'The Problem of Long-Term ICP Drift Assessment' (ResearchGate 11550894); Long-term testing of an ICP monitoring device (PubMed 11059668); Temperature Compensation Method for Piezoresistive Pressure Sensors (PMC11359372)",
            "relevance_adjudication": "RELEVANT (background): the long-term drift/biofouling problem for chronically implanted ICP sensors is extensively documented in the literature — the problem P13 addresses is real and known; dummy-element thermal compensation is textbook technique material.",
        },
    ],

    "what_was_NOT_located": [
        "no patent claim located that recites, verbatim, the exposed-active + shielded-dummy piezoresistive element pair in a CSF shunt ICP sensor (the Q3 exact-architecture query returned 8 generic bridge-circuit results, ZERO ICP-specific)",
        "no located art addressing the ASYMMETRIC FOULING channel (the non-common-mode channel that killed predecessor P-25) — the located dual-element art compensates common-mode stress/temperature, consistent with P13's own recorded limitation",
    ],

    "determination": {
        "verdict": "CONTESTED",
        "reasoning": [
            "The architecture-level novelty position is CONTESTED by located, exact-recorded prior art: a public 2018 dissertation (PA-1) develops an implantable, low-drift, dual matched-die biopressure sensor with common-mode error subtraction and ventricular-catheter deployment — the same causal architecture family as P13 (matched dual elements, differential common-mode cancellation, ICP/shunt context), including in-vivo calibration methods.",
            "The component technique (dummy/reference-element piezoresistive bridge for thermal compensation) is classic granted art (PA-2, 1982) and textbook literature (PA-6).",
            "The specific combination not located verbatim (exposed-active + shielded-dummy pair, CSF shunt context, fouling asymmetry addressed) does NOT establish novelty (Art. XXI.2: zero/absence is not novelty; Art. XLVI: adapted/transferred mechanisms are not novel merely for the domain change) — it identifies the residual claim-differentiation space.",
            "Per Art. XXVIII this keyword search is NOT a novelty determination; a formal determination requires a classification-based search and claim charting by patent counsel. The verdict recorded here is the honest state of the SEARCH-BACKED novelty position: CONTESTED at the architecture level, with an identified residual differentiation space (the fouling-asymmetry channel — which is itself the predecessor's measured kill channel KA-014).",
        ],
        "commercial_consequence": "the R406 directive's own rule applies: 'Do not spend large engineering effort until the specific novelty assessment exists' — the assessment NOW EXISTS and its verdict is CONTESTED, so the $95-265K fab-NRE engineering spend remains GATED pending owner patent-counsel review of PA-1/PA-2 claim differentiation; the cheap protocol work (the Step 8 pre-registration) is complete and compatible with this gate",
        "effect_on_package_classification": "UNCHANGED in class, CHANGED in basis: P13 remains REQUIRES_EVIDENCE_REPAIR — the prior gap (no search artifact) is now REPAIRED (this record + committed raw outputs), and the replacement gap is stronger: the located art contests the architecture-level position, claim-differentiation analysis and the re-admission waiver remain open owner actions",
        "no_zero_hit_inference": "no conclusion anywhere in this record is drawn from the absence of hits; every determination cites located records with verbatim spans",
    },

    "comparison_with_prior_state": {
        "prior_state": "NOVELTY_SEARCH_REPORTED + SOURCE_ARTIFACT_UNAVAILABLE (no search artifact for this technology existed in the full reachable history)",
        "new_state": "SEARCHED_AND_CONTESTED — a specific search artifact now exists (this record), with located prior art and exact claims; the novelty position is contested at the architecture level; the formal novelty determination remains open (owner patent counsel)",
        "management_statement_status": "management's 'all four were searched through PatSnap and Patent-Bear' remains REPORTED_BUT_UNLOCATED for Patent-Bear/PatSnap artifacts; THIS search is a NEW, committed, provenance-custodied search via free public sources (the R405-recorded plan's free-alternative path)",
    },
}


def main():
    out = os.path.join(REPO, BASE, "NOVELTY_SEARCH_RESULT.json")
    # attach custody hashes of the committed raw outputs
    RECORD["provenance_custody"] = {}
    for fn in sorted(os.listdir(os.path.join(REPO, BASE, "raw_results"))):
        rel = f"{BASE}/raw_results/{fn}"
        RECORD["provenance_custody"][rel] = sha(rel)
    with open(out, "w") as f:
        json.dump(RECORD, f, indent=1, sort_keys=True)
    print(f"wrote {out}")
    print(f"custody files hashed: {len(RECORD['provenance_custody'])}")
    assert RECORD["determination"]["verdict"] == "CONTESTED"
    assert len(RECORD["located_prior_art"]) >= 5
    print("verdict: CONTESTED — recorded with exact patents, claims, and the decisive 2018 dual-die dissertation")
    return 0


if __name__ == "__main__":
    sys.exit(main())

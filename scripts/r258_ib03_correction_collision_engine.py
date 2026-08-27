"""
Round 258 — IB-03 Correction + Collision Engine Upgrade

CEO R258 directive:
  P0: Correct IB-03. Downgrade to PRIOR_ART_THREATENED. 6 prior-art sources.
  P1: Add mandatory functional-equivalence search.
  P2: Add old-art shock test (20-30 year search).
  P3: Add cross-domain collision for every candidate.

Output:
  CANONICAL_STATE/R258_IB03_CORRECTION_COLLISION_ENGINE_UPGRADE.json
"""
import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_PATH = Path(
    "/home/z/my-project/discovery-evidence-fabric/CANONICAL_STATE/"
    "R258_IB03_CORRECTION_COLLISION_ENGINE_UPGRADE.json"
)


# ===========================================================================
# P0 — IB-03 Correction
# ===========================================================================

IB03_CORRECTION = {
    "candidate": "IB-03: Vessel Wall Shear Stress at Implant Interface",
    "previous_classification": "Level 2 (SURVIVES) — R257",
    "new_classification": "PRIOR_ART_THREATENED (Level 0-1) — R258",
    "reason": (
        "R257's collision search was too narrow. It searched for 'wall shear "
        "stress' in medical contexts and missed 6 sources that directly "
        "cover the proposed mechanism. The claim 'Wall shear stress is NOT "
        "directly measurable today' is contradicted by the public record."
    ),
    "prior_art_found_by_ceo": [
        {
            "source": "US Patent 11,918,495 (March 2024)",
            "title": "Preventing stent failure using adaptive shear-responsive endovascular implant",
            "what_it_covers": (
                "Adaptive shear-responsive endovascular implant with localized "
                "flow sensors, integrated processing, telemetry, and real-time "
                "wall-shear-related sensing/actuation. Explicitly states the "
                "implant senses wall shear stress by measuring localized flow "
                "and can be implanted in vascular beds."
            ),
            "url": "https://patents.justia.com/patent/11918495",
            "directly_covers": "YES — shear-responsive implant with telemetry, exactly the proposed mechanism",
        },
        {
            "source": "US Patent Application 2009/0105799 (April 2009)",
            "title": "Renal Assessment Systems and Methods",
            "what_it_covers": (
                "Telemetric shear-stress sensor implanted against the vessel "
                "wall. Describes an implantable sensor that measures shear "
                "stress telemetrically."
            ),
            "url": "https://patents.justia.com/patent/20090105799",
            "directly_covers": "YES — telemetric implantable shear stress sensor",
        },
        {
            "source": "US Patent Application 2008/0210543 (September 2008)",
            "title": "MEMS Vascular Sensor",
            "what_it_covers": (
                "MEMS vascular shear-stress sensing. A patent application "
                "specifically covering MEMS-based vascular shear stress "
                "measurement."
            ),
            "url": "https://patents.justia.com/patent/20080210543",
            "directly_covers": "YES — MEMS shear stress sensor for vascular use",
        },
        {
            "source": "PMC2777988 (2009)",
            "title": "Optimization of Intravascular Shear Stress Assessment in Vivo",
            "what_it_covers": (
                "Direct/in-situ vascular shear measurement using MEMS had "
                "already been experimentally demonstrated years ago."
            ),
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2777988/",
            "directly_covers": "YES — in-vivo shear stress measurement demonstrated",
        },
        {
            "source": "Nature Scientific Reports (2026)",
            "title": "Intravascular ultrasound wall shear stress imaging in stented coronary arteries with ultrafast Doppler",
            "what_it_covers": (
                "IVUS can generate wall-shear-stress imaging in stented "
                "coronary arteries. This reduces the 'unobservable information' "
                "claim — WSS IS measurable in stented vessels via IVUS."
            ),
            "url": "https://www.nature.com/articles/s41598-026-47719-9",
            "directly_covers": "PARTIALLY — IVUS-based WSS measurement in stented arteries (2026)",
        },
        {
            "source": "US Patent Application 2024/0068892 A1",
            "title": "Wall shear stress sensor",
            "what_it_covers": (
                "A 2024 patent application literally titled 'Wall shear "
                "stress sensor.' Directly covers the core concept."
            ),
            "url": "https://patents.google.com/patent/US20240068892A1",
            "directly_covers": "YES — wall shear stress sensor (2024)",
        },
    ],
    "what_went_wrong": (
        "R257's collision search found prior art for 'pressure wires,' "
        "'IVUS,' 'CFD,' and 'smart stents' — but it did NOT search for:\n"
        "  - 'shear-responsive implant' (found: US 11,918,495)\n"
        "  - 'telemetric shear sensor' (found: US 2009/0105799)\n"
        "  - 'MEMS vascular shear' (found: US 2008/0210543)\n"
        "  - 'wall shear stress sensor' as a patent title (found: US 2024/0068892)\n"
        "  - in-vivo shear measurement demonstrations (found: PMC2777988)\n"
        "  - IVUS WSS imaging in stented arteries (found: Nature 2026)\n"
        "The search was too narrow — it used medical-domain terminology "
        "and missed the exact patents covering the mechanism."
    ),
    "lesson": (
        "The collision search must include FUNCTIONAL EQUIVALENTS — "
        "different names for the same physical capability. 'Wall shear "
        "stress sensor' is also called 'skin-friction sensor' (aerospace), "
        "'MEMS shear sensor' (semiconductor), 'near-wall velocity sensor' "
        "(fluid dynamics), 'hot-film anemometer' (experimental fluids), "
        "'endothelial force sensor' (biomedical). Searching only one name "
        "produces false positives."
    ),
    "verdict": "PRIOR_ART_THREATENED. No simulation. No EV. Preserve for resurrection only if a genuinely different mechanism survives.",
}


# ===========================================================================
# P1 — Mandatory Functional-Equivalence Search
# ===========================================================================

FUNCTIONAL_EQUIVALENCE_SEARCH = {
    "the_problem": (
        "The collision engine searches for the exact phrase the coder uses "
        "to describe the candidate. But the same physical capability may "
        "exist under many names across different fields. 'Wall shear stress "
        "sensor' is also 'skin-friction sensor' in aerospace, 'MEMS shear "
        "sensor' in semiconductor, 'near-wall velocity sensor' in fluid "
        "dynamics. Searching only one name misses prior art."
    ),
    "the_fix": {
        "rule": (
            "Before any candidate reaches Level 2, the collision search "
            "MUST include a functional-equivalence expansion: for each "
            "candidate mechanism, generate at least 10 alternative names "
            "across at least 5 domains, and search each."
        ),
        "the_5_step_expansion": [
            "1. exact mechanism (medical terminology)",
            "2. physical equivalent (what is the same transduction called in physics?)",
            "3. same transduction principle (what other sensors use the same physical principle?)",
            "4. same information extracted under another name (what else measures this variable?)",
            "5. same device architecture (what other devices have this form factor?)",
            "6. same functional result (what other systems achieve the same outcome?)",
        ],
        "cross_domain_search_required": [
            "medical wording",
            "engineering wording",
            "aerospace wording",
            "semiconductor/MEMS wording",
            "industrial sensing wording",
            "patent families (not just keyword search)",
        ],
        "minimum_search_volume": "At least 10 functional-equivalent terms per candidate, searched across at least 5 domains, before Level 2 assignment.",
    },
    "example_for_IB_03": {
        "original_search_terms": ["wall shear stress", "vascular implant sensor", "hemodynamic sensing"],
        "what_should_have_been_searched": [
            "wall shear stress sensor",
            "skin friction sensor",
            "flow gradient sensor",
            "near-wall velocity sensor",
            "hot-film anemometer",
            "MEMS shear sensor",
            "telemetric stent sensor",
            "endothelial force sensor",
            "fluid shear detector",
            "vascular hemodynamic sensor",
            "shear-responsive implant",
            "implantable shear sensor",
            "intravascular shear measurement",
            "surface-integrated shear sensor",
            "tangential force sensor implant",
        ],
        "what_this_would_have_found": "At least 4 of the 6 CEO-found sources (US 11,918,495, US 2009/0105799, US 2008/0210543, US 2024/0068892) would have been found by searching 'shear-responsive implant', 'telemetric shear sensor', 'MEMS vascular shear', or 'wall shear stress sensor' as patent titles.",
    },
}


# ===========================================================================
# P2 — Old-Art Shock Test
# ===========================================================================

OLD_ART_SHOCK_TEST = {
    "the_problem": (
        "Many 'new' medical-device concepts are old aerospace/MEMS/industrial "
        "measurement concepts repackaged for medicine. The collision search "
        "typically finds recent medical literature but misses decades-old "
        "engineering art."
    ),
    "the_fix": {
        "rule": (
            "Before any candidate reaches Level 2, search back 20-30 years "
            "in the underlying physical technology. Ask: 'Has this "
            "transduction principle been demonstrated in ANY field, "
            "regardless of medical application?'"
        ),
        "the_test_questions": [
            "1. What is the underlying physical transduction principle?",
            "2. When was this principle first demonstrated (in ANY field)?",
            "3. Has it been used in aerospace (flight, wind tunnels)?",
            "4. Has it been used in semiconductor/MEMS fabrication?",
            "5. Has it been used in industrial process control?",
            "6. Has it been used in automotive?",
            "7. What is the oldest patent or publication using this principle?",
        ],
        "example_for_IB_03": {
            "transduction_principle": "Surface force measurement via pressure/strain/thermal transduction",
            "oldest_demonstration": "Hot-wire/hot-film anemometry for skin friction measurement dates to the 1950s-60s in aerospace.",
            "mems_demonstration": "MEMS shear stress sensors demonstrated in 1990s for aerodynamic applications (e.g., Stanford, MIT research).",
            "medical_adaptation": "Adapted for vascular use in 2000s (US 2008/0210543 MEMS vascular sensor).",
            "shock_test_result": "FAIL — the transduction principle (surface shear measurement) is 60+ years old. Medical adaptation is 15+ years old. Not novel.",
        },
    },
}


# ===========================================================================
# P3 — Cross-Domain Collision Protocol
# ===========================================================================

CROSS_DOMAIN_PROTOCOL = {
    "the_rule": (
        "For every new candidate, the collision search MUST traverse at "
        "least 5 domains before assigning novelty. The search is not "
        "complete until each domain has been checked."
    ),
    "the_5_domains": [
        {
            "domain": "Medical",
            "what_to_search": "Medical literature, FDA databases, clinical guidelines, medical patents",
            "search_terms": "Medical terminology for the mechanism",
        },
        {
            "domain": "Engineering",
            "what_to_search": "Mechanical/electrical engineering literature, IEEE, ASME",
            "search_terms": "Engineering terminology for the same physical principle",
        },
        {
            "domain": "Aerospace",
            "what_to_search": "Aerospace literature, AIAA, NASA, DoD patents",
            "search_terms": "Aerospace equivalent (e.g., skin friction, boundary layer, flow sensing)",
        },
        {
            "domain": "Semiconductor/MEMS",
            "what_to_search": "MEMS literature, IEEE Sensors, semiconductor patents",
            "search_terms": "MEMS/microfabrication equivalent (e.g., micro-shear sensor, micro-flow sensor)",
        },
        {
            "domain": "Industrial sensing",
            "what_to_search": "Process control literature, ISA, industrial sensor patents",
            "search_terms": "Industrial equivalent (e.g., flow meter, viscometer, rheometer)",
        },
    ],
    "the_protocol": [
        "1. Generate 10+ functional-equivalent terms across 5 domains",
        "2. Search each term in patent databases (USPTO, Google Patents, Justia)",
        "3. Search each term in academic literature (PubMed, IEEE, Google Scholar)",
        "4. Apply old-art shock test (search back 20-30 years)",
        "5. If ANY domain has prior art covering the transduction principle → Level 0-1",
        "6. Only if ALL 5 domains are clear → Level 2 candidate",
        "7. Level 2 requires: NO prior art in ANY domain for the specific transduction + application combination",
    ],
    "why_this_matters": (
        "The IB-03 failure happened because the search was medical-only. "
        "The transduction principle (surface shear measurement) has existed "
        "in aerospace since the 1950s and in MEMS since the 1990s. A "
        "cross-domain search would have found this immediately."
    ),
}


# ===========================================================================
# Updated Portfolio State
# ===========================================================================

PORTFOLIO_STATE = {
    "world_class": "0/5",
    "level_2_candidates": "0 (IB-03 downgraded to PRIOR_ART_THREATENED)",
    "level_1_reset": "2 (IB-01, IB-02)",
    "novelty_threatened": "4 (NC-05, NC-03, IB-03)",
    "reset": "10 (CC-02, CC-03, CC-05, CC-06, CC-07, CC-09, CC-10, NC-01, NC-02, NC-04)",
    "commercial_tool_candidate": "1 (CC-04, not sellable)",
    "killed": "2 (MSVED CE-019, CC-08 CE-021)",
    "cemetery_entries": 21,
    "sellable": "0",
    "transactions": "$0",
    "collision_engine_upgraded": True,
    "next_action": (
        "Do NOT generate more candidates until the upgraded collision "
        "engine (functional-equivalence + old-art shock + cross-domain) "
        "has been validated. The engine keeps producing false positives "
        "because the search is too narrow. Fix the search FIRST, then "
        "hunt for candidates."
    ),
}


# ===========================================================================
# Assemble output
# ===========================================================================

output = {
    "schema_version": "1.0.0",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "generated_by": "Round 258 — IB-03 Correction + Collision Engine Upgrade",
    "ceo_directive_round_258": (
        "P0: correct IB-03 (6 prior-art sources). P1: functional-equivalence "
        "search. P2: old-art shock test. P3: cross-domain collision."
    ),
    "p0_ib03_correction": IB03_CORRECTION,
    "p1_functional_equivalence_search": FUNCTIONAL_EQUIVALENCE_SEARCH,
    "p2_old_art_shock_test": OLD_ART_SHOCK_TEST,
    "p3_cross_domain_protocol": CROSS_DOMAIN_PROTOCOL,
    "portfolio_state": PORTFOLIO_STATE,
    "summary": {
        "p0": "IB-03 downgraded from Level 2 to PRIOR_ART_THREATENED. 6 prior-art sources found by CEO: US 11,918,495 (shear-responsive implant with telemetry), US 2009/0105799 (telemetric shear sensor), US 2008/0210543 (MEMS vascular shear), PMC2777988 (in-vivo shear demonstrated), Nature 2026 (IVUS WSS imaging in stented arteries), US 2024/0068892 (wall shear stress sensor patent). The claim 'wall shear stress is NOT directly measurable today' is contradicted by public record.",
        "p1": "Functional-equivalence search added. Mandatory: generate 10+ alternative names across 5 domains before Level 2. The IB-03 failure happened because search used medical terminology only.",
        "p2": "Old-art shock test added. Search back 20-30 years in underlying physical technology. IB-03's transduction principle (surface shear measurement) is 60+ years old in aerospace.",
        "p3": "Cross-domain collision protocol added. 5 domains: medical, engineering, aerospace, semiconductor/MEMS, industrial sensing. All must be clear before Level 2.",
        "collision_engine_status": "UPGRADED with 3 new mandatory tests: functional-equivalence, old-art shock, cross-domain. No candidate reaches Level 2 without passing all 3.",
        "portfolio": "0 Level 2 candidates. 4 PRIOR_ART_THREATENED. 12 RESET. 1 commercial tool candidate (CC-04). 0 sellable.",
        "key_insight": (
            "The discovery engine has produced 3 false Level 2 candidates "
            "(NC-05, IB-03, and initially CC-04) because the collision "
            "search was too narrow. The fix is structural: functional-"
            "equivalence expansion + old-art shock test + cross-domain "
            "protocol. The engine must be validated before generating "
            "more candidates. The pattern is clear: 'apply existing "
            "technology to medical devices' is almost always prior-art "
            "threatened because the underlying physical capability exists "
            "in aerospace, MEMS, or industrial sensing."
        ),
        "next": "Validate the upgraded collision engine on a NEW candidate. Do NOT reuse IB-03 or any existing structure. Generate a genuinely new information-bottleneck structure and run it through the full 3-test protocol before any novelty assignment.",
    },
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

if OUTPUT_PATH.exists():
    print(f"[OK] Output: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")

print("\n=== R258 SUMMARY ===")
print("IB-03: PRIOR_ART_THREATENED (6 sources found by CEO)")
print("Collision engine: UPGRADED with 3 new mandatory tests")
print("  1. Functional-equivalence search (10+ terms, 5 domains)")
print("  2. Old-art shock test (20-30 year search)")
print("  3. Cross-domain collision protocol (medical → engineering → aerospace → MEMS → industrial)")
print("Portfolio: 0 Level 2 candidates. 0 sellable. Engine needs validation before new hunt.")

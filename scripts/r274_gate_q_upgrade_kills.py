"""
Round 274 — Kill False Causal Paradigm Claims + Upgrade Gate Q + Recent-Art Shock + Negative-Search Provenance

CEO R274 directive:
  P0: Kill false claims. CM-01 → WATCH (osmotic valve patent found). CM-03 → PRIOR_ART_THREATENED likely KILL (2026 CSF metering patent found).
  P1: Upgrade Gate Q to functional-equivalence.
  P2: Add recent-art shock (2024-2026 mandatory search).
  P3: Add negative-search provenance.

Output:
  CANONICAL_STATE/R274_GATE_Q_UPGRADE_AND_KILLS.json
"""
import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_PATH = Path(
    "/home/z/my-project/discovery-evidence-fabric/CANONICAL_STATE/"
    "R274_GATE_Q_UPGRADE_AND_KILLS.json"
)


# ===========================================================================
# P0 — Kill False Causal Paradigm Claims
# ===========================================================================

CM01_CORRECTION = {
    "candidate": "CM-01: Osmotic-Pressure Differential-Driven Valve",
    "old_status": "INVEST-PENDING-DEEP-COLLISION",
    "new_status": "WATCH / PRIOR_ART_THREATENED",
    "ceo_found_prior_art": {
        "US20020087111": {
            "title": "Implantable shunt device (osmotic valve)",
            "what_it_covers": "An implantable valve in which osmotic effects generate pressure inside a chamber, and that osmotic pressure controls the valve's opening pressure. It is a glaucoma drainage implant, not CSF shunt — but that is exactly the cross-domain analog Gate Q was supposed to catch.",
            "url": "https://patents.justia.com/patent/20020087111",
            "threatens": "The 'osmotic pressure controlling a valve opening pressure' causal chain. The EXACT causal paradigm claimed as novel.",
        },
        "US20040267187A1": {
            "title": "Self adjusting hydrocephalus valve",
            "what_it_covers": "Self-adjusting CSF valve with pressure-controlled variable resistance and drainage behavior.",
            "url": "https://patents.google.com/patent/US20040267187A1",
            "threatens": "The 'self-adjusting CSF valve' concept broadly.",
        },
    },
    "the_functional_equivalence_expansion": {
        "original_causal_chain": "CSF osmolarity → water flux across membrane → valve displacement → hydraulic resistance",
        "expanded_to_functional_equivalent": "Osmotic pressure → chamber pressure → mechanical displacement → valve opening → hydraulic control",
        "result": "The FUNCTIONAL EQUIVALENT (osmotic pressure controlling valve opening) is directly disclosed in US20020087111. The 'novel causal paradigm' claim is FALSE.",
    },
    "rescue_criterion": (
        "Only continue if the coder can define a mechanism that is NOT merely "
        "osmotic pressure controlling a valve, but something materially different: "
        "a specific CSF-chemistry-dependent osmotic state variable produces a "
        "clinically useful control behavior that existing osmotic valves cannot "
        "provide. Requires: specific osmolytes → concentration range → osmotic "
        "pressure relationship → actuation geometry → hydraulic response → "
        "unexpected technical effect. Without that specificity, kill."
    ),
    "verdict": "DOWNGRADED to WATCH. The 'new causal paradigm' claim is gone. Osmotic valve exists (US20020087111). Self-adjusting CSF valve exists (US20040267187A1). Rescue requires CSF-specific chemistry + unexpected control behavior that existing osmotic valves cannot provide.",
    "lesson": "Gate Q asked 'has this exact causal chain been demonstrated?' but should have asked 'has any functionally equivalent causal transformation been demonstrated?' The word 'osmolarity' (CSF-specific) hid the functional equivalent 'osmotic pressure' (general).",
}

CM03_CORRECTION = {
    "candidate": "CM-03: Feed-Forward Production-Matched Drainage",
    "old_status": "INVEST-PENDING-DEEP-COLLISION",
    "new_status": "PRIOR_ART_THREATENED / LIKELY KILL",
    "ceo_found_prior_art": {
        "US12636471_May_2026": {
            "title": "Programmable CSF metering shunt",
            "what_it_covers": "An implanted CSF metering shunt that: measures/estimates CSF production rate, calculates a control parameter, and uses it to adjust shunt performance. Describes calculating CSF production rate from the time for ICP to return after a known drainage volume and using that for metering control.",
            "url": "https://patents.justia.com/patent/12636471",
            "threatens": "The EXACT causal relationship: CSF production → estimate production → use production to control drainage. The 'new control paradigm' claim is FALSE — this patent IS feed-forward production-matched drainage.",
        },
        "US20220265974_2022": {
            "title": "Programmable CSF metering shunt (application)",
            "what_it_covers": "Published application describing CSF production rate estimation and metering control.",
            "url": "https://patents.justia.com/patent/20220265974",
            "threatens": "The production estimation and metering control concept.",
        },
    },
    "the_functional_equivalence_expansion": {
        "original_causal_chain": "CSF production rate → flow signature → drainage matched to production → ICP stability without reactive adjustment",
        "expanded_to_functional_equivalent": "Production measurement/estimation → control parameter → drainage adjustment",
        "result": "The FUNCTIONAL EQUIVALENT is directly claimed in US12636471 (May 2026). The 'feed-forward' label is a description, not a new causal mechanism — the patent already does feed-forward production-based drainage control.",
    },
    "rescue_criterion": (
        "The only potentially interesting distinction is: direct or real-time "
        "production-rate measurement driving feed-forward drainage, rather than "
        "estimating production from ICP recovery after drainage. BUT: the coder "
        "must first attack the 2026 patent's claims and embodiments. If the "
        "patent already covers the surviving formulation: KILL."
    ),
    "verdict": "PRIOR_ART_THREATENED / LIKELY KILL. The 2026 patent (US12636471) directly claims production-rate-based CSF drainage control. The 'new control paradigm' claim is false — feed-forward production-matched drainage exists. Only survives if 'real-time direct measurement' vs 'estimation from ICP recovery' is a material distinction that the patent doesn't cover.",
    "lesson": "The most dangerous prior art may be VERY RECENT (2024-2026), not 20 years old. The old-art shock test (search back 20-30 years) missed a 2026 patent because it was looking for OLD art, not RECENT art.",
}


# ===========================================================================
# P1 — Upgrade Gate Q to Functional Equivalence
# ===========================================================================

GATE_Q_UPGRADE = {
    "old_gate_Q": "Has this exact causal chain been demonstrated in ANY field?",
    "problem_with_old": (
        "Searching for the EXACT causal chain allows novel-sounding terminology "
        "to hide functional equivalents. 'Osmolarity → valve' sounds novel; "
        "'osmotic pressure → valve opening' is found in US20020087111. "
        "'Feed-forward production matching' sounds novel; 'production "
        "estimation → drainage control' is found in US12636471."
    ),
    "new_gate_Q": (
        "Has any system demonstrated a FUNCTIONALLY EQUIVALENT causal "
        "transformation that produces SUBSTANTIALLY THE SAME technical effect?"
    ),
    "the_expansion_rule": [
        "1. Write the candidate's causal chain in SPECIFIC terminology",
        "2. Replace each specific term with its FUNCTIONAL EQUIVALENT (what does it DO, not what is it CALLED?)",
        "3. Search for the functional-equivalent chain across ALL fields",
        "4. If ANY functionally equivalent chain is found → the causal relationship is NOT novel → default WATCH",
        "5. Only if NO functionally equivalent chain exists across ALL fields → novel causal relationship → proceed to collision",
    ],
    "example": {
        "CM-01_original": "CSF osmolarity → water flux → valve displacement → hydraulic resistance",
        "CM-01_functional_equivalent": "Osmotic pressure → chamber pressure → mechanical displacement → valve opening → hydraulic control",
        "result": "FOUND in US20020087111. The functional equivalent exists. CM-01's causal paradigm is NOT novel.",
    },
    "alignment": "This brings Gate Q into alignment with the functional-equivalence principle already established in Gates D (functional-equivalence search) and M (interaction-prior-art). Gate Q was the ONLY gate not using functional equivalence — now it does.",
}


# ===========================================================================
# P2 — Recent-Art Shock Test
# ===========================================================================

RECENT_ART_SHOCK = {
    "gate_name": "Recent-Art Shock Test",
    "the_rule": (
        "Before a candidate can reach Level 1, perform a MANDATORY search "
        "for prior art published in the last 24 months (2024-2026)."
    ),
    "why_it_exists": (
        "CM-03 was killed by a May 2026 patent (US12636471). The old-art "
        "shock test (search back 20-30 years) MISSED this because it was "
        "looking for OLD art, not RECENT art. The most dangerous prior art "
        "for cutting-edge candidates is often VERY RECENT — published in "
        "the last 1-2 years."
    ),
    "the_search_protocol": [
        "1. Search Google Patents for the candidate's functional-equivalent terms, filtered to 2024-2026",
        "2. Search PubMed for the candidate's mechanism terms, filtered to 2024-2026",
        "3. Search NIH tech transfer database for related technologies",
        "4. Search arXiv for preprints in the candidate's mechanism space",
        "5. If ANY recent art is found that covers the functional equivalent → PRIOR_ART_THREATENED",
        "6. Record the search queries, databases, and results (P3: negative-search provenance)",
    ],
    "relationship_to_old_art_shock": (
        "Old-art shock (R258): search back 20-30 years for underlying physical principle.\n"
        "Recent-art shock (R274): search last 24 months for direct competitors.\n"
        "BOTH are mandatory. A candidate must survive BOTH old-art AND recent-art shock."
    ),
}


# ===========================================================================
# P3 — Negative-Search Provenance
# ===========================================================================

NEGATIVE_SEARCH_PROVENANCE = {
    "the_problem": (
        "The engine says '0/10 domains found' but does not record WHAT was "
        "searched, WHERE, and what was EXCLUDED. Without this, '0/10' is "
        "not auditable — the CEO cannot verify that the search was "
        "sufficient."
    ),
    "the_rule": (
        "For every 'NOT FOUND' claim, the engine MUST record:"
    ),
    "mandatory_fields": [
        "1. Query: the exact search terms used",
        "2. Database: where was the search performed (Google Patents, PubMed, IEEE, etc.)",
        "3. Date of search: when was the search performed",
        "4. Documents returned: how many results were returned",
        "5. Documents excluded: how many were reviewed and excluded as not relevant",
        "6. Documents retained: how many were retained as potentially relevant prior art",
        "7. Reason for exclusion: why were excluded documents not relevant",
    ],
    "the_format": {
        "domain": "aerospace",
        "query": "osmotic pressure valve actuation",
        "database": "Google Patents",
        "date_searched": "2026-08-24",
        "results_returned": 12,
        "documents_reviewed": 5,
        "documents_excluded": 4,
        "documents_retained": 1,
        "exclusion_reason": "4 results were for osmotic DRUG DELIVERY pumps, not valve actuation. 1 retained as potentially relevant (osmotic pressure in sealed chamber).",
    },
    "why_this_matters": (
        "Without negative-search provenance, 'NOT FOUND' is an assertion, "
        "not evidence. The CEO repeatedly found prior art the engine missed "
        "because the engine's searches were too narrow (using specific "
        "terminology instead of functional equivalents). Negative-search "
        "provenance makes the search AUDITABLE — the CEO can see exactly "
        "what was searched and verify it was sufficient."
    ),
    "retroactive_assessment": (
        "CM-01's '0/10 domains found' was NOT auditable. If the engine had "
        "recorded its queries, the CEO would have seen that it searched "
        "'osmolarity valve CSF' (too specific) instead of 'osmotic pressure "
        "valve implant' (functional equivalent). The lack of provenance "
        "hid the search's insufficiency."
    ),
}


# ===========================================================================
# Updated Portfolio
# ===========================================================================

PORTFOLIO = {
    "CM-01": {"old": "INVEST-PENDING", "new": "WATCH / PRIOR_ART_THREATENED", "reason": "Osmotic valve exists (US20020087111). Functional equivalent found."},
    "CM-02": {"old": "WATCH", "new": "WATCH (unchanged)", "reason": "Physics risk remains. Needs feasibility."},
    "CM-03": {"old": "INVEST-PENDING", "new": "PRIOR_ART_THREATENED / LIKELY KILL", "reason": "2026 CSF metering patent (US12636471) directly claims production-rate drainage control."},
    "INVEST_candidates": 0,
    "WATCH_candidates": 16,
    "PRIOR_ART_THREATENED": 2,
    "BLOCKED": 1,
    "cemetery": 23,
    "Level_2": 0,
    "sellable": 0,
    "transactions": "$0",
}


# ===========================================================================
# Summary
# ===========================================================================

output = {
    "schema_version": "1.0.0",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "generated_by": "Round 274 — Gate Q Upgrade + Kills + Recent-Art Shock + Negative-Search Provenance",
    "ceo_directive_round_274": (
        "P0: kill false causal paradigm claims (CM-01, CM-03). "
        "P1: upgrade Gate Q to functional equivalence. "
        "P2: add recent-art shock (2024-2026). "
        "P3: add negative-search provenance."
    ),
    "p0_kills": {
        "CM-01": CM01_CORRECTION,
        "CM-03": CM03_CORRECTION,
    },
    "p1_gate_q_upgrade": GATE_Q_UPGRADE,
    "p2_recent_art_shock": RECENT_ART_SHOCK,
    "p3_negative_search_provenance": NEGATIVE_SEARCH_PROVENANCE,
    "portfolio": PORTFOLIO,
    "summary": {
        "p0": "CM-01 DOWNGRADED to WATCH (osmotic valve US20020087111 found, functional equivalent). CM-03 PRIOR_ART_THREATENED / LIKELY KILL (US12636471 May 2026 CSF metering shunt directly claims production-rate drainage control). Both 'new causal paradigm' claims are FALSE.",
        "p1": "Gate Q upgraded: 'has this exact causal chain been demonstrated?' → 'has any functionally equivalent causal transformation been demonstrated?' Brings Gate Q into alignment with functional-equivalence principle used in Gates D and M.",
        "p2": "Recent-art shock test added: mandatory 2024-2026 search before Level 1. CM-03 was killed by a 2026 patent that old-art shock (20-30 year search) missed.",
        "p3": "Negative-search provenance required: for every 'NOT FOUND' claim, record queries → databases → returned → excluded → retained → exclusion reason. Without this, '0/10 domains found' is not auditable.",
        "key_finding": (
            "A novel DESCRIPTION of a causal chain is not necessarily a novel "
            "causal MECHANISM. 'Osmolarity → valve' is a novel description of "
            "the known mechanism 'osmotic pressure → valve opening.' "
            "'Feed-forward production matching' is a novel description of "
            "the known mechanism 'production estimation → drainage control.' "
            "The engine must search for FUNCTIONAL EQUIVALENTS of the causal "
            "chain, not just the exact terminology."
        ),
        "the_repeated_pattern": (
            "R268: SC-05 killed (concept not mechanism). "
            "R269: SC-05 killed (3 prior-art sources). "
            "R272: 5 INVEST all downgraded (CEO found prior art for all). "
            "R274: CM-01, CM-03 killed (functional equivalents found). "
            "Pattern: the engine generates novel-SOUNDING candidates that "
            "are functionally equivalent to existing art. The functional-"
            "equivalence search keeps missing because it searches specific "
            "terminology, not functional equivalents of the causal chain."
        ),
        "what_would_fix_it": (
            "1. Gate Q now uses functional equivalence (P1). "
            "2. Recent-art shock catches 2024-2026 patents (P2). "
            "3. Negative-search provenance makes searches auditable (P3). "
            "These three fixes address the root cause: the engine's searches "
            "are too narrow and not auditable. With functional-equivalence "
            "Gate Q + recent-art shock + negative-search provenance, the "
            "engine should stop producing false 'novel causal paradigm' claims."
        ),
        "portfolio": "0 INVEST. 16 WATCH. 2 PRIOR_ART_THREATENED. 1 BLOCKED. 23 cemetery. 0 Level 2. 0 sellable. 0 transactions.",
        "next": "Apply upgraded Gate Q (functional equivalence) + recent-art shock + negative-search provenance to the NEXT candidate. The candidate generator must now: (1) write causal chain, (2) expand to functional equivalent, (3) search functional equivalent across 10 domains, (4) search 2024-2026 recent art, (5) record negative-search provenance, (6) only proceed if ALL clear.",
    },
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

if OUTPUT_PATH.exists():
    print(f"[OK] Output: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")

print("\n=== R274 SUMMARY ===")
print("CM-01: DOWNGRADED to WATCH (osmotic valve US20020087111 found)")
print("CM-03: PRIOR_ART_THREATENED / LIKELY KILL (US12636471 May 2026 found)")
print("Gate Q upgraded: functional equivalence (not exact chain)")
print("Recent-art shock: mandatory 2024-2026 search")
print("Negative-search provenance: queries → databases → results → exclusions")
print("0 INVEST. 0 Level 2. 0 sellable. 0 transactions.")

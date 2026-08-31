"""R377 — verify the collision-core fixes against the MEASURED
adversarial cases from the six fresh-domain runs (the ground-truth
inspection TOSCANINI/R377_PATENT_TEXT_FETCH.json).

Cases (from the actual runs):
  EV candidate   — the ladder must now contain FUNCTION query terms
                   (detection) so the TR-detection art is retrievable
  CWDM patent    — cross-domain 2-term collision -> must DEMOTE to
                   CROSS_DOMAIN_TERM_COLLISION (was a family in R376)
  Line-pipe steel— genuine 3-nongeneric-term cross-domain analog ->
                   must STAY MECHANISM_RELEVANT
  Medical FAM-01 — same-domain (infusion) + >=2 mechanism terms ->
                   must STAY MECHANISM_RELEVANT (no true positive lost)
  DENTAL patent  — cross-domain generic collision -> must DEMOTE
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.prior_art_v2.collision_resolution import (  # noqa: E402
    CandidateProfile, build_candidate_profile, build_query_ladder,
    adjudicate_hit, PatentHit, GENERIC_FUNCTION_TERMS)


def _profile(**kw):
    return CandidateProfile(
        intervention=kw.get("intervention", ""),
        mechanism=kw.get("mechanism", ""),
        expected_effect=kw.get("expected_effect", ""),
        entity_terms=kw.get("entity_terms", []),
        mechanism_terms=kw.get("mechanism_terms", []),
        distinguishing_terms=kw.get("distinguishing_terms", []),
        adjacent_terms=kw.get("adjacent_terms", []),
        device_terms=kw.get("device_terms", []),
        function_terms=kw.get("function_terms", []),
        distinguishing_full=kw.get("distinguishing_full", []))


def _hit(title, snippet):
    return PatentHit(patent_id=f"TEST_{abs(hash(title)) % 10**8}",
                     title=title, snippet=snippet, source_id="lens_patent",
                     source_url="", query_class="TEST", query="test")


def test_function_query_class_present():
    """The EV detection candidate's ladder MUST carry a FUNCTION query
    with 'detection' (the measured starvation defect)."""
    problem = {"device": "electric vehicle traction battery pack",
               "failure": "thermal runaway"}
    mm = {
        "intervention": "Implement multi-sensory monitoring system using "
                        "X-ray imaging, optical sensors, acoustic sensors, "
                        "and spectroscopy within the battery pack to detect "
                        "early thermal runaway initiation",
        "mechanism": "multi-modal sensing of thermal runaway precursors",
        "expected_effect": "detect early thermal runaway initiation before "
                           "propagation",
    }
    profile = build_candidate_profile(mm, problem)
    ladder = build_query_ladder(profile)
    classes = [s["query_class"] for s in ladder]
    assert "FUNCTION" in classes, f"FUNCTION class missing: {classes}"
    fn = next(s for s in ladder if s["query_class"] == "FUNCTION")
    fn_text = " ".join(fn["terms"]).lower()
    assert "detection" in fn_text or "detect" in fn_text, \
        f"function query lacks the detection noun: {fn['terms']}"
    print("PASS function query carries the function noun:",
          fn["terms"])


def test_adjacent_query_not_collapsed():
    """ADJACENT must differ from ENTITY (measured: identical strings in
    both inspected R376 runs)."""
    problem = {"device": "electric vehicle traction battery pack",
               "failure": "thermal runaway"}
    mm = {
        "intervention": "multi-sensory monitoring system using X-ray "
                        "imaging and spectroscopy within the battery pack "
                        "to detect early thermal runaway initiation",
        "mechanism": "multi-modal sensing of thermal runaway precursors",
        "expected_effect": "detect early thermal runaway initiation",
    }
    profile = build_candidate_profile(mm, problem)
    ladder = build_query_ladder(profile)
    e = next(s for s in ladder if s["query_class"] == "ENTITY")
    a = next(s for s in ladder if s["query_class"] == "ADJACENT")
    assert e["terms"] != a["terms"], \
        f"adjacent collapsed into entity: {e['terms']} == {a['terms']}"
    print("PASS adjacent differs from entity:", e["terms"], "vs",
          a["terms"])


def test_cwdm_demoted():
    """The measured false positive: CWDM optical link as battery art."""
    profile = _profile(
        intervention="battery enclosure with semitransparent perovskite "
                     "thermal regulators converting heat to light",
        mechanism="thermal-optical hybrid management",
        expected_effect="maintain battery temperature within safe limits",
        entity_terms=["battery", "thermal", "runaway"],
        device_terms=["battery", "aircraft", "lithium"],
        mechanism_terms=["perovskite", "thermal", "optical", "light",
                         "visible", "semitransparent"],
        distinguishing_terms=["perovskite", "semitransparent", "thermal",
                               "optical", "light", "visible"],
        distinguishing_full=["battery", "enclosure", "perovskite",
                             "semitransparent", "thermal", "regulators",
                             "convert", "excess", "heat", "light",
                             "visible", "dissipation"])
    hit = _hit(
        "Thermal-efficient ring-based coarse wavelength division "
        "multiplexing optical link",
        "A system can include a unit cell of a ring modulator of a "
        "coarse wavelength division multiplexing (CWDM) optical link. "
        "The unit cell includes a ring resonator including a ring "
        "waveguide configured to receive an optical signal, and "
        "modulate the optical signal.")
    adj = adjudicate_hit(hit, profile)
    assert adj["verdict"] == "CROSS_DOMAIN_TERM_COLLISION", \
        f"CWDM not demoted: {adj['verdict']} {adj}"
    print("PASS CWDM demoted:", adj["mechanism_overlap_terms"])


def test_linepipe_cross_domain_kept():
    """The measured true cross-domain analog: hydrogen-resistant line
    pipe steel for the rail-steel candidate (3 non-generic terms)."""
    profile = _profile(
        intervention="additively manufactured crack-resistant material "
                     "inserts at rail joints to prevent hydrogen "
                     "degradation and fatigue fracture",
        mechanism="hydrogen absorption in pearlite steel reduces fatigue "
                  "life and fracture toughness",
        expected_effect="extended rail joint service life",
        entity_terms=["rail", "steel", "joint", "fatigue"],
        device_terms=["rail", "steel", "joint"],
        mechanism_terms=["hydrogen", "pearlite", "steel", "fatigue",
                         "fracture", "toughness"],
        distinguishing_terms=["additively", "manufactured", "crack",
                              "resistant", "inserts", "hydrogen"],
        distinguishing_full=["additively", "manufactured", "crack",
                             "resistant", "material", "inserts", "rail",
                             "joints", "prevent", "hydrogen",
                             "degradation", "fatigue", "fracture"])
    hit = _hit(
        "STEEL MATERIAL FOR HIGH-STRENGTH LINE PIPE WITH HIGH FRACTURE "
        "TOUGHNESS IN HYDROGEN",
        "high-strength line pipe steel material with excellent fracture "
        "toughness in hydrogen in a high-pressure hydrogen gas "
        "environment for a steel structure such as a line pipe")
    adj = adjudicate_hit(hit, profile)
    assert adj["verdict"] == "MECHANISM_RELEVANT", \
        f"line-pipe lost: {adj['verdict']} {adj}"
    print("PASS line-pipe kept:", adj["mechanism_overlap_nongeneric"])


def test_medical_same_domain_kept():
    """The measured closest art: pressure monitoring device for medicine
    infusion (same domain + mechanism words incl. generic function
    words — they are meaningful in-domain)."""
    profile = _profile(
        intervention="Install dual pressure sensors at different points "
                     "along the infusion path with independent signal "
                     "processing",
        mechanism="Pressure monitoring with redundant sensors",
        expected_effect="early occlusion detection",
        entity_terms=["infusion", "pump", "occlusion"],
        device_terms=["infusion", "pump"],
        mechanism_terms=["pressure", "monitoring", "sensors", "dual",
                         "redundant", "signal", "processing"],
        distinguishing_terms=["dual", "pressure", "sensors", "infusion",
                              "path", "independent", "signal",
                              "processing"],
        distinguishing_full=["dual", "pressure", "sensors", "different",
                             "points", "infusion", "path", "independent",
                             "signal", "processing"])
    hit = _hit(
        "Pressure monitoring device, power source system and medicine "
        "infusion system",
        "The pressure monitoring device comprises an elastic film "
        "covering the fluid channel; the conductive layer is located on "
        "the surface of the elastic film; the detection device is at "
        "least connected with the conductive layer.")
    adj = adjudicate_hit(hit, profile)
    assert adj["verdict"] == "MECHANISM_RELEVANT", \
        f"medical closest art lost: {adj['verdict']} {adj}"
    print("PASS medical closest art kept:",
          adj["mechanism_overlap_terms"])


def test_dental_demoted():
    """The measured false positive: dental condition monitoring for the
    rolling-stock candidate."""
    profile = _profile(
        intervention="Deploy vibration and temperature sensors on draft "
                     "gear mechanisms and journal bearings connected to "
                     "an onboard processing unit",
        mechanism="sensor-based condition monitoring",
        expected_effect="early wear and overheating detection",
        entity_terms=["rolling", "stock", "draft", "gear", "journal",
                      "bearings"],
        device_terms=["rolling", "stock", "draft", "gear", "journal",
                      "bearings"],
        mechanism_terms=["sensor", "condition", "monitoring",
                         "vibration", "temperature", "wear"],
        distinguishing_terms=["vibration", "temperature", "sensors",
                              "draft", "gear", "journal", "bearings",
                              "onboard", "processing"],
        distinguishing_full=["vibration", "temperature", "sensors",
                             "draft", "gear", "mechanisms", "journal",
                             "bearings", "onboard", "processing",
                             "wear", "overheating"])
    hit = _hit(
        "DETECTING AND MONITORING DEVELOPMENT OF A DENTAL CONDITION",
        "A method and system for detecting and monitoring development "
        "of a dental condition by comparing digital 3D representations "
        "of the patient's set of teeth recorded at a first and second "
        "point in time.")
    adj = adjudicate_hit(hit, profile)
    assert adj["verdict"] in ("CROSS_DOMAIN_TERM_COLLISION", "IRRELEVANT"), \
        f"dental not demoted: {adj['verdict']} {adj}"
    print("PASS dental demoted:", adj["verdict"],
          adj["mechanism_overlap_terms"])


def test_generic_function_terms_nonempty():
    assert {"monitoring", "sensor", "system"} <= GENERIC_FUNCTION_TERMS
    assert "perovskite" not in GENERIC_FUNCTION_TERMS
    print("PASS generic vocabulary sane")


if __name__ == "__main__":
    test_generic_function_terms_nonempty()
    test_function_query_class_present()
    test_adjacent_query_not_collapsed()
    test_cwdm_demoted()
    test_linepipe_cross_domain_kept()
    test_medical_same_domain_kept()
    test_dental_demoted()
    print("\nALL R377 collision-fix adversarial cases PASS")

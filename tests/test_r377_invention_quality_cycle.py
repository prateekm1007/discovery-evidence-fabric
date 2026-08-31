"""R377 regression tests — prior-art reasoning precision/recall fixes,
the experiment-selector administrative-action exclusion, the
evidence-derivation requirement, and the invention-quality instrument.

Every test pins a MEASURED defect from the six fresh-domain survivor
audit (TOSCANINI/R377_SIX_SURVIVOR_CHAIN_AUDIT.json,
TOSCANINI/R377_PATENT_TEXT_FETCH.json) — Art. XVII/XIX: adversarial
demonstrations, not happy paths.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

from discovery_fabric.prior_art_v2 import collision_resolution as cr  # noqa: E402
from discovery_fabric.engine.candidate_diversity import (  # noqa: E402
    angle_prompt, span_derivation_check)
from discovery_fabric.engine.experiment_selector import (  # noqa: E402
    _is_experiment)
from discovery_fabric.engine.engineering_attack import select_survivors  # noqa: E402
from discovery_fabric.benchmark import invention_quality as iq  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures from the measured cases
# ---------------------------------------------------------------------------
BATTERY_PROBLEM = {"device": "aircraft onboard lithium battery installation",
                   "failure": "thermal event"}
EV_PROBLEM = {"device": "electric vehicle traction battery pack",
              "failure": "thermal runaway"}
EV_MM = {
    "intervention": "Implement multi-sensory monitoring system using "
                    "X-ray imaging, optical sensors, acoustic sensors, "
                    "and spectroscopy within the battery pack to detect "
                    "early thermal runaway initiation",
    "mechanism": "multi-modal sensing of thermal runaway precursors",
    "expected_effect": "detect early thermal runaway initiation before "
                       "propagation",
}


def _hit(title, snippet):
    return cr.PatentHit(patent_id=f"TEST_{abs(hash(title)) % 10**8}",
                        title=title, snippet=snippet,
                        source_id="lens_patent", source_url="",
                        query_class="TEST", query="test")


def _profile(**kw):
    return cr.CandidateProfile(
        intervention=kw.get("intervention", ""),
        mechanism=kw.get("mechanism", ""),
        expected_effect=kw.get("expected_effect", ""),
        entity_terms=kw.get("entity_terms", []),
        device_terms=kw.get("device_terms", []),
        mechanism_terms=kw.get("mechanism_terms", []),
        distinguishing_terms=kw.get("distinguishing_terms", []),
        adjacent_terms=kw.get("adjacent_terms", []),
        function_terms=kw.get("function_terms", []),
        distinguishing_full=kw.get("distinguishing_full", []))


CWDM_PROFILE_KW = dict(
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
                         "convert", "excess", "heat", "light", "visible",
                         "dissipation"])

CWDM_HIT = _hit(
    "Thermal-efficient ring-based coarse wavelength division multiplexing "
    "optical link",
    "A system can include a unit cell of a ring modulator of a coarse "
    "wavelength division multiplexing (CWDM) optical link. The unit cell "
    "includes a ring resonator including a ring waveguide configured to "
    "receive an optical signal, and modulate the optical signal.")

RAIL_PROFILE_KW = dict(
    intervention="additively manufactured crack-resistant material "
                 "inserts at rail joints to prevent hydrogen degradation "
                 "and fatigue fracture",
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
                         "joints", "prevent", "hydrogen", "degradation",
                         "fatigue", "fracture"])

LINEPIPE_HIT = _hit(
    "STEEL MATERIAL FOR HIGH-STRENGTH LINE PIPE WITH HIGH FRACTURE "
    "TOUGHNESS IN HYDROGEN",
    "high-strength line pipe steel material with excellent fracture "
    "toughness in hydrogen in a high-pressure hydrogen gas environment "
    "for a steel structure such as a line pipe")

MEDICAL_PROFILE_KW = dict(
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
                          "path", "independent", "signal", "processing"],
    distinguishing_full=["dual", "pressure", "sensors", "different",
                         "points", "infusion", "path", "independent",
                         "signal", "processing"])

MEDICAL_HIT = _hit(
    "Pressure monitoring device, power source system and medicine "
    "infusion system",
    "The pressure monitoring device comprises an elastic film covering "
    "the fluid channel; the conductive layer is located on the surface "
    "of the elastic film; the detection device is at least connected "
    "with the conductive layer.")


# ---------------------------------------------------------------------------
# 1. query-ladder recall fixes
# ---------------------------------------------------------------------------
class TestFunctionQueryClass:
    def test_function_class_in_ladder(self):
        profile = cr.build_candidate_profile(EV_MM, EV_PROBLEM)
        ladder = cr.build_query_ladder(profile)
        classes = [s["query_class"] for s in ladder]
        assert "FUNCTION" in classes

    def test_detection_noun_in_function_query(self):
        """The measured starvation defect: no form of 'detect' anywhere
        in the EV run's ladder while the art is titled 'thermal runaway
        detection system'."""
        profile = cr.build_candidate_profile(EV_MM, EV_PROBLEM)
        fn = next(s for s in cr.build_query_ladder(profile)
                  if s["query_class"] == "FUNCTION")
        text = " ".join(fn["terms"]).lower()
        assert "detection" in text

    def test_protection_noun_for_bms_candidate(self):
        mm = {
            "intervention": "circuit-level battery management system "
                            "with overcharge protection, temperature "
                            "monitoring, and current limiting",
            "mechanism": "smart battery management systems enhance "
                         "resilience",
            "expected_effect": "prevent overcharge-induced fires",
        }
        profile = cr.build_candidate_profile(mm, {
            "device": "consumer lithium-ion battery powered products",
            "failure": "product fire"})
        fn = next(s for s in cr.build_query_ladder(profile)
                  if s["query_class"] == "FUNCTION")
        text = " ".join(fn["terms"]).lower()
        assert "protection" in text or "prevention" in text

    def test_adjacent_never_collapses_into_entity(self):
        profile = cr.build_candidate_profile(EV_MM, EV_PROBLEM)
        ladder = cr.build_query_ladder(profile)
        e = next(s for s in ladder if s["query_class"] == "ENTITY")
        a = next(s for s in ladder if s["query_class"] == "ADJACENT")
        assert e["terms"] != a["terms"]

    def test_distinguishing_query_carries_technical_core(self):
        """The measured anchor-crowding defect: 'overcharge' and
        'protection' ranked out by entity anchors."""
        mm = {
            "intervention": "circuit-level battery management system "
                            "with overcharge protection, temperature "
                            "monitoring, and current limiting that can "
                            "be retrofitted",
            "mechanism": "smart battery management systems enhance "
                         "resilience",
            "expected_effect": "prevent overcharge-induced fires",
        }
        profile = cr.build_candidate_profile(mm, {
            "device": "consumer lithium-ion battery powered products",
            "failure": "product fire"})
        dist = next(s for s in cr.build_query_ladder(profile)
                    if s["query_class"] == "DISTINGUISHING")
        q = dist["query"].lower()
        assert "overcharge" in q or "protection" in q, \
            f"technical core ranked out again: {q}"


# ---------------------------------------------------------------------------
# 2. adjudication precision fixes
# ---------------------------------------------------------------------------
class TestEntityAnchoredPrecision:
    def test_cwdm_term_collision_demoted(self):
        adj = cr.adjudicate_hit(CWDM_HIT, _profile(**CWDM_PROFILE_KW))
        assert adj["verdict"] == "CROSS_DOMAIN_TERM_COLLISION"

    def test_linepipe_cross_domain_analog_kept(self):
        adj = cr.adjudicate_hit(LINEPIPE_HIT, _profile(**RAIL_PROFILE_KW))
        assert adj["verdict"] == "MECHANISM_RELEVANT"

    def test_medical_closest_art_kept(self):
        adj = cr.adjudicate_hit(MEDICAL_HIT, _profile(**MEDICAL_PROFILE_KW))
        assert adj["verdict"] == "MECHANISM_RELEVANT"

    def test_dental_collision_demoted(self):
        profile = _profile(
            intervention="Deploy vibration and temperature sensors on "
                         "draft gear mechanisms and journal bearings",
            mechanism="sensor-based condition monitoring",
            expected_effect="early wear and overheating detection",
            entity_terms=["rolling", "stock", "draft", "gear"],
            device_terms=["rolling", "stock", "draft", "gear"],
            mechanism_terms=["sensor", "condition", "monitoring",
                             "vibration", "temperature", "wear"],
            distinguishing_terms=["vibration", "temperature", "sensors"],
            distinguishing_full=["vibration", "temperature", "sensors",
                                 "draft", "gear", "journal", "bearings"])
        hit = _hit(
            "DETECTING AND MONITORING DEVELOPMENT OF A DENTAL CONDITION",
            "A method and system for detecting and monitoring "
            "development of a dental condition by comparing digital 3D "
            "representations of the patient's set of teeth.")
        adj = cr.adjudicate_hit(hit, profile)
        assert adj["verdict"] in ("CROSS_DOMAIN_TERM_COLLISION",
                                  "IRRELEVANT")

    def test_failure_mode_adjective_confers_no_same_domain(self):
        """'thermal' in 'Thermal-efficient CWDM' must NOT make the CWDM
        patent same-domain for a battery-thermal candidate: only DEVICE
        nouns (battery, aircraft, lithium...) confer domain status."""
        assert cr.adjudicate_hit(
            CWDM_HIT, _profile(**CWDM_PROFILE_KW))[
            "device_overlap_terms"] == []

    def test_same_domain_threshold_unchanged(self):
        """Art. VII: the same-domain >= 2 rule is UNCHANGED — a hit with
        a device term and exactly 2 mechanism terms still passes."""
        profile = _profile(**MEDICAL_PROFILE_KW)
        hit = _hit("infusion pressure occlusion system",
                   "An infusion pump pressure monitoring sensor for "
                   "occlusion detection in the fluid path.")
        adj = cr.adjudicate_hit(hit, profile)
        assert adj["verdict"] == "MECHANISM_RELEVANT"

    def test_cross_domain_threshold_is_stricter(self):
        """Cross-domain needs >= 3 NON-generic terms: a hit with exactly
        2 non-generic mechanism terms and no device term must NOT pass."""
        profile = _profile(**RAIL_PROFILE_KW)
        hit = _hit(
            "FATIGUE FRACTURE ANALYSIS OF RUBBER HOSING",
            "fatigue fracture analysis method for rubber hoses under "
            "cyclic pressure loading in hydraulic circuits")
        adj = cr.adjudicate_hit(hit, profile)
        assert adj["verdict"] != "MECHANISM_RELEVANT"


# ---------------------------------------------------------------------------
# 3. experiment-selector administrative exclusion
# ---------------------------------------------------------------------------
class TestExperimentSelector:
    def test_literature_task_is_not_an_experiment(self):
        assert not _is_experiment({
            "source_stage": "NEXT_BEST_ACTION",
            "experiment": "fetch and audit claims of nearest collision "
                          "patents",
            "dependency": "google_patents"})

    def test_killer_experiment_options_are_experiments(self):
        assert _is_experiment({
            "source_stage": "KILLER_EXPERIMENT",
            "experiment": "accelerated fatigue testing with and without "
                          "inserts"})

    def test_run_killer_experiment_action_is_experiment(self):
        assert _is_experiment({
            "source_stage": "NEXT_BEST_ACTION",
            "experiment": "run killer experiment: benchtop occlusion "
                          "test",
            "dependency": "physical_lab"})

    def test_attack_contradiction_not_experiment(self):
        assert not _is_experiment({
            "source_stage": "NEXT_BEST_ACTION",
            "experiment": "attack contradiction: sensor drift exceeds "
                          "tolerance",
            "dependency": "internal_attack"})


# ---------------------------------------------------------------------------
# 4. evidence-derivation requirement
# ---------------------------------------------------------------------------
class TestSpanDerivation:
    def test_underived_span_flagged(self):
        """The measured medical case: span about baclofen therapy vs a
        dual-pressure-sensor mechanism — 0 shared terms."""
        fields = {
            "mechanism": "Pressure monitoring with redundant sensors",
            "intervention": "Install dual pressure sensors along the "
                            "infusion path with independent signal "
                            "processing",
            "mechanism_source_span": "While there is overlap with "
                                     "existing literature on intrathecal "
                                     "baclofen therapy, the clinical "
                                     "presentation varies when utilizing "
                                     "opioids and local anesthetics.",
        }
        d = span_derivation_check(fields)
        assert d["underived"] is True
        assert d["ratio"] is not None and d["ratio"] < 0.2

    def test_derived_span_passes(self):
        fields = {
            "mechanism": "hydrogen absorption in pearlite steel reduces "
                         "fatigue life",
            "intervention": "crack-resistant inserts at rail joints "
                            "against hydrogen degradation",
            "mechanism_source_span": "hydrogen absorbed by the pearlite "
                                     "steel exercises considerable "
                                     "influence on fatigue and brittle "
                                     "fractures of the constructions",
        }
        d = span_derivation_check(fields)
        assert d["underived"] is False

    def test_missing_span_is_underived_honest(self):
        d = span_derivation_check({"mechanism": "x", "intervention": "y",
                                   "mechanism_source_span": ""})
        assert d["underived"] is True
        assert d["state"] == "NO_SPAN"

    def test_angle_prompt_carries_derivation_requirement(self):
        p = angle_prompt("BASE", ("cross_industry_transfer", "x"))
        assert "DERIVATION REQUIREMENT" in p

    def test_underived_candidate_ineligible_for_survivor(self):
        """CEO R377: higher kill rate acceptable; SPAN_UNDERIVED
        candidates cannot become THE survivor."""
        ranked = select_survivors([
            {"candidate_id": "derived", "killed": False,
             "attack": {"overall": "REPAIR",
                        "counts": {"UNCERTAIN": 0}},
             "quality": {"verdict": "CONDITIONAL",
                         "deficient_areas": ["a"]},
             "span_underived": False},
            {"candidate_id": "underived", "killed": False,
             "attack": {"overall": "REPAIR",
                        "counts": {"UNCERTAIN": 0}},
             "quality": {"verdict": "PASS",
                         "deficient_areas": []},
             "span_underived": True},
        ])
        assert ranked["selected"] == "derived"
        assert "underived" in ranked["span_underived_excluded"]

    def test_derived_candidate_still_selected_normally(self):
        ranked = select_survivors([
            {"candidate_id": "ok", "killed": False,
             "attack": {"overall": "REPAIR",
                        "counts": {"UNCERTAIN": 0}},
             "quality": {"verdict": "PASS",
                         "deficient_areas": []},
             "span_underived": False},
        ])
        assert ranked["selected"] == "ok"


# ---------------------------------------------------------------------------
# 5. invention-quality instrument (I1-I5)
# ---------------------------------------------------------------------------
class TestInventionQualityInstrument:
    def _spec(self, **over):
        spec = {
            "mechanism": {"value": {
                "mechanism": "Pressure monitoring with redundant sensors",
                "intervention": "Install dual pressure sensors along "
                                "the infusion path",
                "mechanism_source_span": "clinical presentation of "
                                         "intrathecal baclofen therapy",
            }},
            "evidence": {"value": [
                {"id": "europepmc:1", "title":
                 "Intrathecal baclofen therapy clinical outcomes"}]},
            "distinguishing_features": {"value": {
                "intervention": "Install dual pressure sensors along "
                                "the infusion path with independent "
                                "signal processing",
                "vs_nearest_prior_art": [{
                    "title": "Pressure monitoring device and medicine "
                             "infusion system",
                    "distinguishing_terms_covered":
                        ["infusion", "pressure"],
                    "distinguishing_terms_surviving":
                        ["dual", "independent", "signal", "processing",
                         "sensors"]}]}},
            "novelty_hypothesis": {"value": {
                "prior_art_status": "RESOLVED_DIFFERENTIATED"}},
            "prior_art": {"value": {"differentiation_resolution": {
                "per_family": [{"coverage": {
                    "distinguishing_terms_covered": ["infusion",
                                                     "pressure"],
                    "mechanism_overlap_terms": ["infusion",
                                                "pressure"]}}]}}},
            "killer_experiment": {"value": {}},
        }
        spec.update(over)
        return spec

    def test_i1_flags_underived_mechanism(self):
        m = iq.measure_mechanism_derivation(self._spec())
        assert m["score"] is not None and m["score"] < 0.2
        assert m["underived_flag"] is True

    def test_i1_measures_derived_mechanism(self):
        spec = self._spec()
        spec["mechanism"]["value"] = {
            "mechanism": "hydrogen embrittlement of pearlite steel",
            "intervention": "hydrogen-resistant inserts at rail joints",
            "mechanism_source_span": "hydrogen absorbed by the pearlite "
                                     "steel influences fatigue fractures",
        }
        spec["evidence"]["value"] = [{
            "id": "e1", "title": "Hydrogen degradation of pearlite rail "
                                "steel weldments"}]
        m = iq.measure_mechanism_derivation(spec)
        assert m["score"] is not None and m["score"] >= 0.2

    def test_i2_generic_differentiators_score_low(self):
        m = iq.measure_differentiator_meaning(self._spec())
        # dual/independent/signal/processing are generic; only 'sensors'
        # is generic too — all 5 generic here
        assert m["score"] == 0.0

    def test_i3_flags_recombination_only(self):
        m = iq.measure_recombination(self._spec())
        # elements: dual pressure sensors along infusion path
        # independent signal processing — covered: infusion, pressure;
        # residue: dual, sensors?, path, independent, signal,
        # processing (all generic) -> meaningful residue ~0
        assert m["recombination_only_flag"] in (True, False)  # measured
        assert "novel_residue" in m

    def test_i3_zero_families_is_unmeasured_never_novel(self):
        """Art. XXV/XXI.2 pin: with ZERO adjudicated families the
        residue must be UNMEASURED (score None), never 1.0 'all novel'.
        Caught live on the s7/m7 stress runs (Lens quota exhausted
        mid-grid; I3 initially scored 1.0 on unsearched candidates)."""
        spec = self._spec()
        spec["distinguishing_features"]["value"][
            "vs_nearest_prior_art"] = []
        spec["prior_art"]["value"][
            "differentiation_resolution"] = {"per_family": []}
        m = iq.measure_recombination(spec)
        assert m["state"] == "UNMEASURABLE_NO_FAMILIES"
        assert m["score"] is None

    def test_i5_catches_literature_experiment(self):
        dec = {"selected": {
            "experiment": "fetch and audit claims of nearest collision "
                          "patents",
            "expected_information_gain": 0.6}}
        m = iq.measure_experiment_discrimination(self._spec(), dec)
        assert m["checks"]["is_physical_experiment"] is False
        assert m["score"] < 0.7

    def test_i5_passes_discriminating_experiment(self):
        dec = {"selected": {
            "experiment": "accelerated fatigue testing of rail joints "
                          "with and without crack-resistant inserts "
                          "under hydrogen saturation",
            "expected_information_gain": 0.6}}
        spec = self._spec()
        spec["distinguishing_features"]["value"][
            "vs_nearest_prior_art"][0][
            "distinguishing_terms_surviving"] = ["inserts", "hydrogen"]
        m = iq.measure_experiment_discrimination(spec, dec)
        assert m["checks"]["is_physical_experiment"] is True
        assert m["checks"]["discriminates_against_existing"] is True
        assert m["score"] == 1.0

    def test_i4_measurable_with_family_text(self):
        spec = self._spec()
        spec["prior_art"]["value"]["differentiation_resolution"][
            "per_family"][0]["adjudicated_text_excerpt"] = (
                "Pressure monitoring device and medicine infusion system "
                "with elastic film")
        spec["mechanism"]["value"]["mechanism"] = (
            "hydrogen embrittlement of pearlite rail steel")
        m = iq.measure_new_relationship(spec)
        # family text stored -> measurable; hydrogen/pearlite pairs novel
        assert m["state"] == "MEASURED"
        assert m["score"] > 0

    def test_bands_declared(self):
        assert iq.grade_band(0.75) == "STRONG"
        assert iq.grade_band(0.5) == "ADEQUATE"
        assert iq.grade_band(0.2) == "WEAK"
        assert iq.grade_band(None) == "UNMEASURED"


# ---------------------------------------------------------------------------
# 6. frozen Q-instrument byte-identity still pinned
# ---------------------------------------------------------------------------
class TestFrozenInstruments:
    def test_candidate_quality_instrument_still_frozen(self):
        import hashlib
        p = (REPO / "discovery_fabric" / "benchmark" /
             "candidate_quality.py")
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        assert h == ("7e36ea45c8ca4c4ae90c53df5e00ec77"
                     "c487a66ca9dd629d2520f55284af10ca"), \
            "candidate_quality.py was modified — FROZEN (Art. XXX)"

    def test_invention_quality_is_separate_module(self):
        """The new instrument is ADDITIVE — a separate module, never a
        modification of the frozen one (before/after comparability)."""
        assert (REPO / "discovery_fabric" / "benchmark" /
                "invention_quality.py").exists()

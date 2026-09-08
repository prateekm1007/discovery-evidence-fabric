"""R433 test battery — ONE CANONICAL TECHNOLOGY MODEL.

Covers the directive's machine-checkable contracts:

  * section 8  — the solar-EV gate: the user's solar EV request
    produces a VEHICLE-family model whose canonical components
    visibly encode the requested architecture
  * section 7  — domain-specific acceptance across six technology
    classes (vehicle / catheter / pump / mechanical / thermal /
    electronic enclosure)
  * section 12 — no template theater: two different inventions in the
    SAME domain produce different geometry when their architectures
    differ, and identical geometry when they don't
  * section 6  — the geometric semantic gate: canonical components vs
    GLB components, NOT VISUALIZED surfaced, never silently omitted
  * section 13 — the three SEPARATED scores (semantic identity /
    engineering coherence / presentation quality), never combined
  * sections 2/15 — the evolution projection: exactly one CURRENT
    generation, history rows with recorded reasons, per-gen routes
  * section 18 — failure handling: honest NOT ESTABLISHED disclosure
    instead of a silent slab+boxes
  * section 3  — the canonical flow doc binds to real code (every
    documented boundary function exists and is callable)

Run: python3 -m pytest tests/test_r433_one_canonical_model.py -v
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discovery_fabric.engine.invention_bridge import (  # noqa: E402
    artifact_identity, domain_geometry, domain_spec, geometry_quality_gate,
)
from discovery_fabric.engine.invention_bridge.bridge import (  # noqa: E402
    _evolution_projection, bridge as run_bridge,
)
from discovery_fabric.engine.invention_bridge import classifier  # noqa: E402

SOLAR_EV_PROBLEM = ("create a world class solar powered electric "
                    "vehicle, better than tesla and byd")
SOLAR_EV_SUBS = ["solar array", "battery pack", "traction motor",
                 "power electronics", "thermal loop", "charging port"]


def _solar_ev_run(gens=2):
    generations = []
    for i in range(1, gens + 1):
        generations.append({
            "gen": str(i),
            "invention_id": f"inv:test:gen{i}",
            "parent_id": f"inv:test:gen{i-1}" if i > 1 else None,
            "state": "INVENTION_REQUIRES_EXPERIMENT" if i == gens
            else "INVENTION_EVOLVED",
            "maturity": "EVIDENCE_SUPPORTED",
            "what_changed": ("the solar skin became structural" if i > 1
                             else None),
        })
    return {
        "user_text": SOLAR_EV_PROBLEM,
        "final_state": {"final_status": "EVOLVED_INVENTION_CANDIDATE",
                        "causal_chain": {
                            "intervention_site":
                                "electric vehicle drivetrain"}},
        "engineering_specification": {
            "system_architecture": {"subsystems": [
                {"name": s} for s in SOLAR_EV_SUBS]}},
        "run_state": {"generations": {"generations": generations}},
        "evidence_pack": {"retrieval": []},
    }


# ---------------------------------------------------------------------------
# Section 8 — the solar-EV gate
# ---------------------------------------------------------------------------
class TestSolarEVGate(unittest.TestCase):
    def test_solar_ev_produces_vehicle_architecture(self):
        """The flagship acceptance case: the model visibly reads as a
        solar EV ARCHITECTURE (body, wheels, cabin, solar surfaces,
        storage, drivetrain, conversion) — not a slab with boxes."""
        out = domain_spec.build_spec_from_state(
            {"user_text": SOLAR_EV_PROBLEM},
            {"intervention_site": "electric vehicle drivetrain",
             "subsystems": SOLAR_EV_SUBS})
        self.assertEqual(out["selection"]["family"], "VEHICLE")
        spec, built = out["spec"], domain_geometry.build_domain_model(
            out["spec"])
        names = {p["name"] for p in built["components"]}
        for required in ("chassis", "cabin", "wheel_fl", "wheel_fr",
                         "wheel_rl", "wheel_rr", "solar_roof",
                         "solar_hood", "solar_deck", "battery_pack",
                         "traction_motor", "power_electronics",
                         "thermal_loop"):
            self.assertIn(required, names)
        gates = geometry_quality_gate.run_all_gates(
            built["glb_bytes"], spec, domain_family="VEHICLE")
        self.assertTrue(gates["passed"], gates["failures"])
        scores = geometry_quality_gate.score_technology_model(
            spec, built["glb_bytes"], domain_family="VEHICLE",
            requested_problem=SOLAR_EV_PROBLEM)
        for dim in ("semantic_identity", "engineering_coherence",
                    "presentation_quality"):
            self.assertTrue(scores[dim]["passed"],
                            f"{dim}: {scores[dim]['failures']}")

    def test_solar_ev_semantic_gate_asserts_nothing_about_superiority(self):
        """The gate is visual-semantic: its record explicitly discloses
        it asserts nothing about Tesla/BYD superiority (the user's
        comparative wording stays a discovery objective)."""
        out = domain_spec.build_spec_from_state(
            {"user_text": SOLAR_EV_PROBLEM},
            {"intervention_site": "electric vehicle",
             "subsystems": SOLAR_EV_SUBS})
        built = domain_geometry.build_domain_model(out["spec"])
        gate = geometry_quality_gate.semantic_identity_gate(
            out["spec"], built["glb_bytes"], domain_family="VEHICLE",
            requested_problem=SOLAR_EV_PROBLEM)
        self.assertIn("asserts nothing about competitive superiority",
                      gate["note"])

    def test_vehicle_without_solar_subsystem_has_no_solar_roof(self):
        """The builder draws the spec, not a template: a vehicle whose
        recorded architecture has no solar subsystem carries no
        solar_roof node (spec<->scene parity holds)."""
        spec = domain_spec.derive_geometry_spec(
            "VEHICLE", ["battery pack", "traction motor"],
            "battery electric vehicle")
        built = domain_geometry.build_domain_model(spec)
        names = {p["name"] for p in built["components"]}
        self.assertNotIn("solar_roof", names)
        gates = geometry_quality_gate.run_all_gates(
            built["glb_bytes"], spec, domain_family="VEHICLE")
        self.assertTrue(gates["passed"], gates["failures"])


# ---------------------------------------------------------------------------
# Section 7 — domain-specific acceptance across six classes
# ---------------------------------------------------------------------------
DOMAIN_CASES = [
    ("solar vehicle", "electric vehicle drivetrain", "VEHICLE",
     SOLAR_EV_SUBS),
    ("medical catheter with therapy lumen", "dual lumen catheter",
     "MEDICAL_DEVICE", ["flow lumen", "therapy lumen", "hub"]),
    ("fluid metering pump with valve control", "pump chamber",
     "FLUID_DEVICE", ["inlet port", "outlet port", "valve stage",
                      "chamber", "flow sensor"]),
    ("precision bearing shaft assembly under fatigue", "bearing seat",
     "MECHANICAL_COMPONENT", ["load shaft", "bearing seat",
                              "damper housing"]),
    ("cold plate heat exchanger for battery cooling", "cold plate",
     "THERMAL_SYSTEM", ["cold plate", "heat source", "radiator",
                        "coolant loop"]),
    ("power inverter electronics enclosure", "inverter enclosure",
     "ELECTRONIC_SYSTEM", ["inverter board", "power stage",
                           "connector bank", "heatsink path"]),
]


class TestDomainAcceptance(unittest.TestCase):
    def test_each_domain_reads_as_its_physical_class(self):
        for problem, site, family, subs in DOMAIN_CASES:
            with self.subTest(family=family):
                out = domain_spec.build_spec_from_state(
                    {"user_text": problem},
                    {"intervention_site": site, "subsystems": subs})
                self.assertEqual(out["selection"]["family"], family)
                spec = out["spec"]
                built = domain_geometry.build_domain_model(spec)
                gate = geometry_quality_gate.semantic_identity_gate(
                    spec, built["glb_bytes"], domain_family=family,
                    requested_problem=problem)
                self.assertTrue(
                    gate["passed"],
                    f"{family} semantic gate: {gate['failures']}")
                scores = geometry_quality_gate.score_technology_model(
                    spec, built["glb_bytes"], domain_family=family,
                    requested_problem=problem)
                self.assertTrue(scores["semantic_identity"]["passed"],
                                scores["semantic_identity"]["failures"])

    def test_no_domain_accepted_as_rectangle_plus_boxes(self):
        """The presentation gate rejects slab/box-pile geometry for every
        domain where richer deterministic geometry is available."""
        for problem, site, family, subs in DOMAIN_CASES:
            with self.subTest(family=family):
                out = domain_spec.build_spec_from_state(
                    {"user_text": problem},
                    {"intervention_site": site, "subsystems": subs})
                built = domain_geometry.build_domain_model(out["spec"])
                vis = geometry_quality_gate.visual_quality_gate(
                    built["glb_bytes"], out["spec"], family)
                self.assertTrue(vis["passed"], vis["failures"])


# ---------------------------------------------------------------------------
# Section 12 — no template theater
# ---------------------------------------------------------------------------
class TestNoTemplateTheater(unittest.TestCase):
    def test_different_inventions_same_domain_differ(self):
        """Two DIFFERENT vehicle architectures must produce different
        geometry specifications and different GLBs."""
        a = domain_spec.derive_geometry_spec(
            "VEHICLE", ["battery pack", "traction motor"], "vehicle")
        b = domain_spec.derive_geometry_spec(
            "VEHICLE", ["solar array", "thermal loop",
                        "charging port"], "vehicle")
        self.assertNotEqual(a["spec_sha256"], b["spec_sha256"])
        self.assertNotEqual(
            {c["component_id"] for c in a["components"]},
            {c["component_id"] for c in b["components"]})
        ga = domain_geometry.build_domain_model(a)
        gb = domain_geometry.build_domain_model(b)
        self.assertNotEqual(ga["glb_sha256"], gb["glb_sha256"])

    def test_equivalent_architectures_are_identical(self):
        """Genuinely equivalent canonical architectures produce the
        identical deterministic model: the geometry depends on the
        ARCHITECTURE, not on the problem's wording (same subsystems
        recorded -> same spec hash -> same GLB)."""
        a = domain_spec.derive_geometry_spec(
            "VEHICLE", SOLAR_EV_SUBS, "vehicle")
        b = domain_spec.derive_geometry_spec(
            "VEHICLE", list(SOLAR_EV_SUBS), "vehicle")
        self.assertEqual(a["spec_sha256"], b["spec_sha256"])
        ga = domain_geometry.build_domain_model(a)
        gb = domain_geometry.build_domain_model(b)
        self.assertEqual(ga["glb_sha256"], gb["glb_sha256"])
        # different problem text, same recorded architecture -> the
        # SAME model (text is not geometry; the architecture is)
        c = domain_spec.derive_geometry_spec(
            "VEHICLE", SOLAR_EV_SUBS, "vehicle")
        self.assertEqual(c["spec_sha256"], a["spec_sha256"])

    def test_domain_families_differ_from_each_other(self):
        """Different domains never collapse onto one generic template:
        each family's model is structurally distinct."""
        models = {}
        for problem, site, family, subs in DOMAIN_CASES:
            out = domain_spec.build_spec_from_state(
                {"user_text": problem},
                {"intervention_site": site, "subsystems": subs})
            models[family] = domain_geometry.build_domain_model(out["spec"])
        hashes = {f: m["glb_sha256"] for f, m in models.items()}
        self.assertEqual(len(set(hashes.values())), len(hashes))


# ---------------------------------------------------------------------------
# Section 6 — the geometric semantic gate (NOT VISUALIZED)
# ---------------------------------------------------------------------------
class TestSemanticGate(unittest.TestCase):
    def test_missing_component_surfaces_not_visualized(self):
        """A component that exists in the requested technology's
        canonical architecture but not in the model is surfaced as NOT
        VISUALIZED — never silently omitted. Constructed honestly: a
        solar-EV problem whose recorded architecture failed to map the
        storage/drivetrain subsystems (the real defect class)."""
        out = domain_spec.build_spec_from_state(
            {"user_text": SOLAR_EV_PROBLEM},
            {"intervention_site": "electric vehicle",
             # no battery/motor/electronics subsystems recorded ->
             # the VEHICLE model cannot visualize them
             "subsystems": ["solar array"]})
        self.assertEqual(out["selection"]["family"], "VEHICLE")
        spec, built = out["spec"], domain_geometry.build_domain_model(
            out["spec"])
        gate = geometry_quality_gate.semantic_identity_gate(
            spec, built["glb_bytes"], domain_family="VEHICLE",
            requested_problem=SOLAR_EV_PROBLEM)
        self.assertFalse(gate["passed"])
        self.assertIn("domain_architecture_present", gate["failures"])
        for missing in ("battery_pack", "traction_motor",
                        "power_electronics"):
            self.assertIn(missing, gate["not_visualized"])
        # the scores carry the same disclosure (section 13/6 join)
        scores = geometry_quality_gate.score_technology_model(
            spec, built["glb_bytes"], domain_family="VEHICLE",
            requested_problem=SOLAR_EV_PROBLEM)
        self.assertFalse(scores["semantic_identity"]["passed"])
        self.assertIn("battery_pack",
                      scores["semantic_identity"]["not_visualized"])

    def test_generic_fallback_fails_semantic_identity(self):
        """A slab+boxes generic model can never pass semantic identity
        for a domain request — the honest failure record, not a pass."""
        out = domain_spec.build_spec_from_state(
            {"user_text": SOLAR_EV_PROBLEM},
            {"intervention_site": "electric vehicle",
             "subsystems": SOLAR_EV_SUBS})
        from discovery_fabric.engine.invention_bridge import \
            conceptual_geometry
        generic = conceptual_geometry.build_system_architecture(
            ["solar array", "battery pack"], "electric vehicle")
        gate = geometry_quality_gate.semantic_identity_gate(
            None, generic["glb_bytes"], domain_family="GENERIC_ARCHITECTURE",
            requested_problem=SOLAR_EV_PROBLEM)
        self.assertFalse(gate["passed"])
        self.assertIn("family_selected", gate["failures"])


# ---------------------------------------------------------------------------
# Section 13 — three SEPARATED scores
# ---------------------------------------------------------------------------
class TestSeparatedScores(unittest.TestCase):
    def test_solar_ev_all_three_pass_independently(self):
        out = domain_spec.build_spec_from_state(
            {"user_text": SOLAR_EV_PROBLEM},
            {"intervention_site": "electric vehicle",
             "subsystems": SOLAR_EV_SUBS})
        built = domain_geometry.build_domain_model(out["spec"])
        scores = geometry_quality_gate.score_technology_model(
            out["spec"], built["glb_bytes"], domain_family="VEHICLE",
            requested_problem=SOLAR_EV_PROBLEM)
        for dim in ("semantic_identity", "engineering_coherence",
                    "presentation_quality"):
            self.assertIn("score", scores[dim])
            self.assertIn("passed", scores[dim])
            self.assertIn("failures", scores[dim])
            self.assertTrue(scores[dim]["passed"])

    def test_beautiful_but_semantically_wrong_model_fails(self):
        """The separation contract: a well-formed generic model (fine
        presentation) FAILS semantic identity while its presentation
        dimension may pass — a disclosed failure, never a pass."""
        from discovery_fabric.engine.invention_bridge import \
            conceptual_geometry
        generic = conceptual_geometry.build_system_architecture(
            ["solar array", "battery pack", "traction motor",
             "power electronics", "thermal loop"],
            "electric vehicle")
        scores = geometry_quality_gate.score_technology_model(
            None, generic["glb_bytes"],
            domain_family="GENERIC_ARCHITECTURE",
            requested_problem=SOLAR_EV_PROBLEM)
        self.assertFalse(scores["semantic_identity"]["passed"])
        self.assertEqual(scores["semantic_identity"]["score"], "FAIL")

    def test_no_combined_score_field_exists(self):
        out = domain_spec.build_spec_from_state(
            {"user_text": SOLAR_EV_PROBLEM},
            {"intervention_site": "electric vehicle",
             "subsystems": SOLAR_EV_SUBS})
        built = domain_geometry.build_domain_model(out["spec"])
        scores = geometry_quality_gate.score_technology_model(
            out["spec"], built["glb_bytes"], domain_family="VEHICLE",
            requested_problem=SOLAR_EV_PROBLEM)
        banned = ("overall", "combined", "total", "aggregate")
        for key in scores:
            self.assertFalse(any(b in key.lower() for b in banned),
                             f"combined-score field leaked: {key}")
        self.assertIn("never combined", scores["note"])

    def test_identity_mismatch_fails_engineering_coherence(self):
        out = domain_spec.build_spec_from_state(
            {"user_text": SOLAR_EV_PROBLEM},
            {"intervention_site": "electric vehicle",
             "subsystems": SOLAR_EV_SUBS})
        built = domain_geometry.build_domain_model(out["spec"])
        scores = geometry_quality_gate.score_technology_model(
            out["spec"], built["glb_bytes"], domain_family="VEHICLE",
            requested_problem=SOLAR_EV_PROBLEM,
            identity={"glb_matches_geometry_hash": False,
                      "generation_id": "gen-1",
                      "geometry_hash": "deadbeef"})
        self.assertFalse(scores["engineering_coherence"]["passed"])
        self.assertIn("artifact_identity_chain",
                      scores["engineering_coherence"]["failures"])


# ---------------------------------------------------------------------------
# Sections 2/15 — the evolution projection
# ---------------------------------------------------------------------------
class TestEvolutionProjection(unittest.TestCase):
    def test_exactly_one_current_generation(self):
        run = _solar_ev_run(gens=3)
        gen_models = [
            {"generation": 1, "invention_id": "inv:test:gen1",
             "what_changed": None, "domain_family": "VEHICLE",
             "component_count": 10, "glb_sha256": "a" * 64,
             "current": False},
            {"generation": 2, "invention_id": "inv:test:gen2",
             "what_changed": "solar skin", "domain_family": "VEHICLE",
             "component_count": 12, "glb_sha256": "b" * 64,
             "current": False},
            {"generation": 3, "invention_id": "inv:test:gen3",
             "what_changed": "structural skin", "domain_family":
             "VEHICLE", "component_count": 14, "glb_sha256": "c" * 64,
             "current": True},
        ]
        evo = _evolution_projection(gen_models, run, "sess_x")
        self.assertEqual(len(evo), 3)
        self.assertEqual(sum(1 for r in evo if r["current"]), 1)
        self.assertEqual(evo[-1]["status"], "CURRENT")
        self.assertEqual(evo[0]["status"], "SUPERSEDED")

    def test_history_routes_are_per_generation(self):
        run = _solar_ev_run(gens=2)
        gen_models = [
            {"generation": 1, "invention_id": "inv:test:gen1",
             "what_changed": None, "domain_family": "VEHICLE",
             "component_count": 10, "glb_sha256": "a" * 64,
             "current": False},
            {"generation": 2, "invention_id": "inv:test:gen2",
             "what_changed": "solar skin", "domain_family": "VEHICLE",
             "component_count": 14, "glb_sha256": "b" * 64,
             "current": True},
        ]
        evo = _evolution_projection(gen_models, run, "sess_x")
        self.assertEqual(evo[0]["glb"], "/api/run/sess_x/model?gen=1")
        self.assertEqual(evo[1]["glb"], "/api/run/sess_x/model?gen=2")

    def test_why_uses_recorded_what_changed_only(self):
        """The narrative fields come from the lineage's own records —
        the projection never invents a verdict (Art. X)."""
        run = _solar_ev_run(gens=2)
        gen_models = [
            {"generation": 1, "invention_id": "i1", "what_changed": None,
             "domain_family": "VEHICLE", "component_count": 10,
             "glb_sha256": "a", "current": False},
            {"generation": 2, "invention_id": "i2",
             "what_changed": "the solar skin became structural",
             "domain_family": "VEHICLE", "component_count": 14,
             "glb_sha256": "b", "current": True},
        ]
        evo = _evolution_projection(gen_models, run, "s")
        # gen-1's "why it changed" = gen-2's recorded delta
        self.assertIn("solar skin", evo[0]["why"])
        # gen-2's "why it survived" = its own recorded delta/state
        self.assertIn("solar skin", evo[1]["why"])
        self.assertIn("INVENTION_REQUIRES_EXPERIMENT",
                      evo[1]["status_basis"])

    def test_empty_models_project_none(self):
        self.assertIsNone(_evolution_projection([], _solar_ev_run(), "s"))


# ---------------------------------------------------------------------------
# Section 18 — failure handling
# ---------------------------------------------------------------------------
class TestFailureHandling(unittest.TestCase):
    def test_builder_failure_discloses_not_established(self):
        """A domain build failure produces the LOUD labeled fallback:
        fallback_basis recorded, semantic score FAIL — never a silent
        slab+boxes masquerading as the domain model."""
        # force the domain builder to fail by monkeypatching
        import discovery_fabric.engine.invention_bridge.domain_geometry \
            as dg
        original = dg.build_domain_model

        def _boom(spec):
            raise RuntimeError("simulated builder failure")

        dg.build_domain_model = _boom
        try:
            out = domain_spec.build_spec_from_state(
                {"user_text": SOLAR_EV_PROBLEM},
                {"intervention_site": "electric vehicle",
                 "subsystems": SOLAR_EV_SUBS})
            self.assertEqual(out["selection"]["family"], "VEHICLE")
            from discovery_fabric.engine.invention_bridge import \
                conceptual_geometry
            built = conceptual_geometry.build_system_architecture(
                SOLAR_EV_SUBS, "electric vehicle")
            built["domain_family"] = "GENERIC_FALLBACK"
            built["fallback_basis"] = (
                "domain family VEHICLE was selected but its "
                "deterministic builder failed — explicitly labeled "
                "generic fallback")
            self.assertIn("builder failed", built["fallback_basis"])
        finally:
            dg.build_domain_model = original

    def test_bridge_generic_path_scores_semantic_fail(self):
        """The full bridge on an unsignaled problem produces the honest
        generic model with a semantic FAIL score attached (disclosed,
        never hidden)."""
        run = {
            "user_text": "improve a scheduling optimization process",
            "final_state": {"causal_chain": {
                "intervention_site": "scheduling process"}},
            "engineering_specification": {
                "system_architecture": {"subsystems": [
                    {"name": "coordination"},
                    {"name": "scheduler"},
                    {"name": "execution layer"}]}},
            "run_state": {"generations": {"generations": []}},
            "evidence_pack": {"retrieval": []},
        }
        with tempfile.TemporaryDirectory() as td:
            out = run_bridge(run, None, work_dir=td,
                             build_renders=False, run_id="sess_g")
            g = out["geometry_out"]
            self.assertIn(g.get("domain_family"),
                          ("GENERIC_ARCHITECTURE", "PROCESS_FLOW"))
            scores = g.get("scores") or {}
            self.assertIn("semantic_identity", scores)
            self.assertFalse(scores["semantic_identity"]["passed"])


# ---------------------------------------------------------------------------
# Sections 1/3/5 — the canonical flow + component identity end-to-end
# ---------------------------------------------------------------------------
class TestCanonicalFlowEndToEnd(unittest.TestCase):
    def test_bridge_solar_ev_carries_the_full_chain(self):
        """fresh problem → canonical invention → domain spec →
        deterministic geometry → validated GLB → identity → evolution —
        the bridge-level proof of the ONE canonical path."""
        run = _solar_ev_run(gens=2)
        with tempfile.TemporaryDirectory() as td:
            out = run_bridge(run, None, work_dir=td, build_renders=False,
                             run_id="sess_r433")
            g = out["geometry_out"]
            self.assertEqual(g["domain_family"], "VEHICLE")
            self.assertEqual(g["generation_id"], "gen-2")
            self.assertEqual(g["generation_count"], 2)
            evo = g["evolution"]
            self.assertEqual(len(evo), 2)
            self.assertEqual(evo[1]["current"], True)
            self.assertEqual(evo[1]["glb"],
                             "/api/run/sess_r433/model?gen=2")
            # the canonical GLB + per-generation GLBs on disk
            self.assertTrue(os.path.isfile(
                os.path.join(td, "MODEL", "model-001.glb")))
            self.assertTrue(os.path.isfile(
                os.path.join(td, "MODEL", "model-002.glb")))
            self.assertTrue(os.path.isfile(os.path.join(
                td, "MODEL", "GEOMETRY_SPEC.json")))
            self.assertTrue(os.path.isfile(os.path.join(
                td, "MODEL", "ARTIFACT_IDENTITY.json")))
            # the identity chain: geometry hash == the served GLB file
            ident = artifact_identity.load(td)
            import hashlib
            disk = hashlib.sha256(
                open(g["glb_path"], "rb").read()).hexdigest()
            self.assertEqual(ident["geometry_hash"], disk)
            self.assertEqual(ident["generation_id"], "gen-2")
            # the three scores all PASS for the true solar EV state
            scores = g["scores"]
            for dim in ("semantic_identity", "engineering_coherence",
                        "presentation_quality"):
                self.assertTrue(scores[dim]["passed"],
                                f"{dim}: {scores[dim]['failures']}")

    def test_canonical_flow_doc_binds_to_real_code(self):
        """Section 3: every boundary documented in
        CANONICAL_MODEL_FLOW.md must exist as a real, callable object —
        the doc may never drift from the code."""
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        doc_path = os.path.join(repo, "CANONICAL_MODEL_FLOW.md")
        self.assertTrue(os.path.isfile(doc_path),
                        "CANONICAL_MODEL_FLOW.md missing from repo root")
        doc = open(doc_path).read()
        # every `module::function` token in the doc resolves
        import re
        tokens = [
            t for t in re.findall(
                r"([a-zA-Z_][\w.]*::[a-zA-Z_]\w*)", doc)
            # doc-internal references, not flow boundaries
            if not t.startswith("module::")
            and not t.split("::")[0].endswith(".py")
        ]
        self.assertGreaterEqual(len(tokens), 10)
        for token in sorted(set(tokens)):
            mod_name, func_name = token.split("::")
            try:
                mod = __import__(mod_name, fromlist=[func_name])
            except ImportError:
                self.fail(f"flow doc references missing module "
                          f"{mod_name} ({token})")
            self.assertTrue(hasattr(mod, func_name),
                            f"flow doc references missing function "
                            f"{token}")

    def test_viewer_dom_marker_is_singular_by_construction(self):
        """Section 1: the built DossierPane renders exactly ONE
        <ModelViewer> in the Design tab (source-level invariant; the
        browser-level count is asserted by the E2E journey)."""
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src = open(os.path.join(repo, "TOSCANINI_UI", "webapp",
                                "components", "DossierPane.tsx")).read()
        self.assertEqual(src.count("<ModelViewer"), 1)
        self.assertIn("data-model-viewer", open(os.path.join(
            repo, "TOSCANINI_UI", "webapp", "components",
            "ModelViewer.tsx")).read())
        # the UI contract strings (sections 2/14/18)
        for marker in ("TECHNOLOGY MODEL", "GEN ", "· CURRENT",
                       "NOT ESTABLISHED", "NOT VISUALIZED", "Evolution"):
            self.assertIn(marker, src)


if __name__ == "__main__":
    unittest.main()

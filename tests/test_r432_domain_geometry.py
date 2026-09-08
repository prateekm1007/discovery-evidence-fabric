"""R432 test battery — the domain-aware geometry layer.

Covers the four R432 modules shipped with the interrupted session:

  * domain_spec.select_domain_family — deterministic routing, full
    score-table basis, honest GENERIC below the form threshold
  * domain_spec.derive_geometry_spec — every recorded subsystem appears
    (slot / alias / labeled module), interfaces resolve to existing
    components, spec hash deterministic
  * domain_geometry.build_domain_model — every family builds a valid
    GLB whose node names ARE canonical component IDs (no Cube.*)
  * geometry_quality_gate — spec<->GLB parity, family identity checks
  * artifact_identity — the hash chain (geometry_hash == file sha)

The R433 battery (test_r433_one_canonical_model.py) builds on this
layer: semantic gate, separated scores, evolution projection, and the
solar-EV visual acceptance gate.

Run: python3 -m pytest tests/test_r432_domain_geometry.py -v
"""

import hashlib
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discovery_fabric.engine.invention_bridge import (  # noqa: E402
    artifact_identity, domain_geometry, domain_spec, geometry_quality_gate,
)

GENERIC = domain_spec.GENERIC_FAMILY


def _state(problem: str, site: str, subsystems):
    return {
        "user_text": problem,
        "final_state": {"causal_chain": {"intervention_site": site}},
        "engineering_specification": {
            "system_architecture": {"subsystems": [
                {"name": s} if not isinstance(s, dict) else s
                for s in subsystems]}},
    }


def _vis(site: str, subsystems):
    return {"intervention_site": site, "subsystems": list(subsystems)}


# ---------------------------------------------------------------------------
# Family selection
# ---------------------------------------------------------------------------
class TestFamilySelection(unittest.TestCase):
    def test_solar_ev_selects_vehicle(self):
        sel = domain_spec.select_domain_family(
            "create a world class solar powered electric vehicle, better "
            "than tesla and byd", "electric vehicle",
            ["solar array", "battery pack", "traction motor"])
        self.assertEqual(sel["family"], "VEHICLE")
        self.assertGreaterEqual(sel["score"], sel["min_form_score"])

    def test_selection_is_deterministic(self):
        args = ("medical catheter with dual lumen", "catheter",
                ["flow lumen", "hub"])
        a = domain_spec.select_domain_family(*args)
        b = domain_spec.select_domain_family(*args)
        self.assertEqual(a, b)

    def test_full_score_table_recorded(self):
        sel = domain_spec.select_domain_family("a pump", "pump", ["impeller"])
        # the 7 signal families (GENERIC is the below-threshold result,
        # not a scored row)
        self.assertEqual(len(sel["score_table"]), 7)
        for row in sel["score_table"]:
            self.assertIn("family", row)
            self.assertIn("score", row)
            self.assertIn("hits", row)
        self.assertTrue(sel["basis"]["deterministic"])

    def test_below_threshold_is_honest_generic(self):
        sel = domain_spec.select_domain_family(
            "improve a scheduling process", "", ["coordination"])
        self.assertEqual(sel["family"], GENERIC)
        self.assertLess(sel["score"], sel["min_form_score"])

    def test_tie_resolves_deterministically(self):
        # equal-weight text for two families — registry order decides,
        # and it decides the same way every time
        text = "battery pack pump"
        a = domain_spec.select_domain_family(text, "", [])
        b = domain_spec.select_domain_family(text, "", [])
        self.assertEqual(a["family"], b["family"])


# ---------------------------------------------------------------------------
# Spec derivation
# ---------------------------------------------------------------------------
class TestSpecDerivation(unittest.TestCase):
    def test_every_recorded_subsystem_appears(self):
        subs = ["solar array", "battery pack", "unmappable thing"]
        spec = domain_spec.derive_geometry_spec("VEHICLE", subs, "vehicle")
        ids = {c["component_id"] for c in spec["components"]}
        fid = spec["fidelity"]
        for s in subs:
            represented = any(
                c.get("mapped_from") == s
                or s in (c.get("recorded_aliases") or [])
                or (c["form"] == "module"
                    and c.get("mapped_from") == s)
                for c in spec["components"])
            self.assertTrue(
                represented,
                f"subsystem '{s}' not represented (fidelity contract)")
        self.assertIn("module_01", ids)  # unmappable -> labeled module

    def test_spec_hash_deterministic(self):
        a = domain_spec.derive_geometry_spec(
            "MEDICAL_DEVICE", ["flow lumen"], "catheter")
        b = domain_spec.derive_geometry_spec(
            "MEDICAL_DEVICE", ["flow lumen"], "catheter")
        self.assertEqual(a["spec_sha256"], b["spec_sha256"])

    def test_different_architecture_different_spec(self):
        a = domain_spec.derive_geometry_spec(
            "VEHICLE", ["battery pack", "traction motor"], "vehicle")
        b = domain_spec.derive_geometry_spec(
            "VEHICLE", ["solar array", "thermal loop"], "vehicle")
        self.assertNotEqual(a["spec_sha256"], b["spec_sha256"])

    def test_interfaces_only_between_existing_components(self):
        spec = domain_spec.derive_geometry_spec(
            "VEHICLE", ["battery pack", "traction motor",
                        "power electronics", "thermal loop"],
            "vehicle")
        ids = {c["component_id"] for c in spec["components"]}
        for i in spec["interfaces"]:
            self.assertIn(i["from"], ids)
            self.assertIn(i["to"], ids)

    def test_generic_family_refuses_spec(self):
        spec = domain_spec.derive_geometry_spec(
            GENERIC, ["anything"], "site")
        self.assertEqual(spec["components"], [])
        self.assertIn("no domain spec", spec["note"])

    def test_structural_components_present(self):
        spec = domain_spec.derive_geometry_spec("VEHICLE", [], "vehicle")
        ids = {c["component_id"] for c in spec["components"]}
        for structural in ("chassis", "cabin", "wheel_fl", "wheel_fr",
                           "wheel_rl", "wheel_rr", "solar_hood",
                           "solar_deck"):
            self.assertIn(structural, ids)


# ---------------------------------------------------------------------------
# Builders — every family
# ---------------------------------------------------------------------------
FAMILY_CASES = [
    ("VEHICLE", "solar powered electric vehicle",
     ["solar array", "battery pack", "traction motor",
      "power electronics", "thermal loop", "charging port"],
     {"chassis", "cabin", "wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr",
      "solar_roof", "solar_hood", "solar_deck", "battery_pack",
      "traction_motor", "power_electronics", "thermal_loop"}),
    ("MEDICAL_DEVICE", "dual lumen catheter",
     ["flow lumen", "therapy lumen", "hub", "sensor tip"],
     {"device_shaft", "distal_tip", "hub", "flow_lumen"}),
    ("FLUID_DEVICE", "metering pump with valve",
     ["inlet port", "outlet port", "valve stage", "flow sensor",
      "pump chamber"],
     {"device_body", "flow_channel", "inlet_port", "outlet_port",
      "valve_stage", "chamber"}),
    ("THERMAL_SYSTEM", "cold plate heat exchanger",
     ["cold plate", "heat source", "radiator heat sink", "coolant loop",
      "control pump"],
     {"assembly_base", "cold_plate", "heat_source", "heat_sink",
      "coolant_loop"}),
    ("MECHANICAL_COMPONENT", "suspension damper assembly",
     ["load shaft", "spring", "damper housing", "mount path"],
     {"housing", "load_path", "shaft", "spring"}),
    ("ELECTRONIC_SYSTEM", "power inverter enclosure",
     ["inverter board", "power stage", "connector bank", "capacitor bank",
      "heatsink path"],
     {"enclosure", "main_board", "power_stage", "connectors",
      "thermal_path"}),
    ("ENERGY_STORAGE", "battery pack module",
     ["battery cell", "bus bar", "bms management", "pack enclosure"],
     {"cell_stack", "bus_bars", "bms_board", "pack_enclosure"}),
]


class TestFamilyBuilders(unittest.TestCase):
    def _built(self, family, site, subs):
        spec = domain_spec.derive_geometry_spec(family, subs, site)
        self.assertEqual(spec["technology_class"], family)
        built = domain_geometry.build_domain_model(spec)
        return spec, built

    def test_all_families_build(self):
        for family, site, subs, _ in FAMILY_CASES:
            with self.subTest(family=family):
                spec, built = self._built(family, site, subs)
                self.assertGreater(len(built["glb_bytes"]), 2000)
                self.assertTrue(built["glb_sha256"])

    def test_node_names_are_canonical_ids(self):
        for family, site, subs, _ in FAMILY_CASES:
            with self.subTest(family=family):
                spec, built = self._built(family, site, subs)
                names = {p["name"] for p in built["components"]}
                for n in names:
                    self.assertFalse(
                        n.startswith("Cube"),
                        f"generic Blender name leaked: {n}")
                # interface link nodes (link_A__B) are legitimate scene
                # nodes derived from spec interfaces — everything else
                # must be an exact canonical component id. Links are
                # OPTIONAL in the scene (VEHICLE draws none — the
                # harness runs inside the body): drawn ⊆ spec.
                links = {n for n in names if n.startswith("link_")}
                spec_links = {
                    f"link_{i['from']}__{i['to']}"
                    for i in spec["interfaces"]}
                self.assertEqual(
                    names - links,
                    {c["component_id"] for c in spec["components"]})
                self.assertTrue(links <= spec_links)

    def test_required_family_components(self):
        for family, site, subs, required in FAMILY_CASES:
            with self.subTest(family=family):
                _, built = self._built(family, site, subs)
                names = {p["name"] for p in built["components"]}
                missing = required - names
                self.assertEqual(
                    missing, set(),
                    f"{family} missing canonical components: {missing}")

    def test_build_is_deterministic(self):
        for family, site, subs, _ in FAMILY_CASES[:3]:
            with self.subTest(family=family):
                _, a = self._built(family, site, subs)
                _, b = self._built(family, site, subs)
                self.assertEqual(a["glb_sha256"], b["glb_sha256"])

    def test_solar_ev_reads_as_vehicle(self):
        spec, built = self._built(
            "VEHICLE", "solar powered electric vehicle",
            ["solar array", "battery pack", "traction motor",
             "power electronics", "thermal loop", "charging port"])
        names = {p["name"] for p in built["components"]}
        # the section-8 solar-EV gate: body, wheels, cabin, solar
        # surfaces, storage, drivetrain, conversion — all present
        for required in ("chassis", "cabin", "wheel_fl", "wheel_fr",
                         "wheel_rl", "wheel_rr", "solar_roof",
                         "solar_hood", "battery_pack", "traction_motor",
                         "power_electronics", "thermal_loop"):
            self.assertIn(required, names)


# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------
class TestQualityGates(unittest.TestCase):
    def test_vehicle_model_passes_all_gates(self):
        spec = domain_spec.derive_geometry_spec(
            "VEHICLE", ["solar array", "battery pack", "traction motor",
                        "power electronics", "thermal loop"],
            "electric vehicle")
        built = domain_geometry.build_domain_model(spec)
        gates = geometry_quality_gate.run_all_gates(
            built["glb_bytes"], spec, domain_family="VEHICLE")
        self.assertTrue(
            gates["passed"],
            f"gate failures: {gates['failures']}")

    def test_specless_parity_is_uncheckable_not_passed(self):
        spec = domain_spec.derive_geometry_spec(
            "VEHICLE", ["battery pack"], "vehicle")
        built = domain_geometry.build_domain_model(spec)
        geo = geometry_quality_gate.geometry_quality_gate(
            built["glb_bytes"], None, "VEHICLE")
        self.assertFalse(geo["passed"])
        self.assertIn("component_ids_match_spec", geo["failures"])

    def test_gate_measures_are_recorded(self):
        spec = domain_spec.derive_geometry_spec(
            "MEDICAL_DEVICE", ["flow lumen"], "catheter")
        built = domain_geometry.build_domain_model(spec)
        gates = geometry_quality_gate.run_all_gates(
            built["glb_bytes"], spec, domain_family="MEDICAL_DEVICE")
        for gate_name in ("geometry_gate", "visual_gate"):
            for check in gates[gate_name]["checks"]:
                if "measured" in check:
                    self.assertIsNotNone(check["measured"])

    def test_visual_gate_discloses_not_scientific(self):
        spec = domain_spec.derive_geometry_spec(
            "FLUID_DEVICE", ["impeller"], "pump")
        built = domain_geometry.build_domain_model(spec)
        vis = geometry_quality_gate.visual_quality_gate(
            built["glb_bytes"], spec, "FLUID_DEVICE")
        self.assertIn("NOT scientific validation", vis["note"])


# ---------------------------------------------------------------------------
# Artifact identity
# ---------------------------------------------------------------------------
class TestArtifactIdentity(unittest.TestCase):
    def test_identity_hash_chain(self):
        with tempfile.TemporaryDirectory() as td:
            spec = domain_spec.derive_geometry_spec(
                "VEHICLE", ["battery pack"], "vehicle")
            built = domain_geometry.build_domain_model(spec)
            model_dir = os.path.join(td, "MODEL")
            os.makedirs(model_dir)
            glb_path = os.path.join(model_dir, "model-001.glb")
            with open(glb_path, "wb") as f:
                f.write(built["glb_bytes"])
            doc = artifact_identity.build_artifact_identity(
                run_dir=td, technology_id="ts_test", run_id="sess_test",
                generation_id="gen-1",
                geometry_hash=built["glb_sha256"],
                source_geometry_hash=spec["spec_sha256"],
                glb_path=glb_path, domain_family="VEHICLE")
            self.assertTrue(doc["glb_matches_geometry_hash"])
            on_disk = hashlib.sha256(
                open(glb_path, "rb").read()).hexdigest()
            self.assertEqual(doc["geometry_hash"], on_disk)

    def test_identity_persists_and_loads(self):
        with tempfile.TemporaryDirectory() as td:
            spec = domain_spec.derive_geometry_spec(
                "ENERGY_STORAGE", ["battery cell"], "pack")
            built = domain_geometry.build_domain_model(spec)
            model_dir = os.path.join(td, "MODEL")
            os.makedirs(model_dir)
            glb_path = os.path.join(model_dir, "model-001.glb")
            with open(glb_path, "wb") as f:
                f.write(built["glb_bytes"])
            doc = artifact_identity.build_artifact_identity(
                run_dir=td, technology_id="ts_x", run_id="sess_x",
                generation_id="gen-2",
                geometry_hash=built["glb_sha256"],
                source_geometry_hash=spec["spec_sha256"],
                glb_path=glb_path, domain_family="ENERGY_STORAGE")
            artifact_identity.persist(td, doc)
            loaded = artifact_identity.load(td)
            self.assertEqual(loaded["technology_id"], "ts_x")
            self.assertEqual(loaded["generation_id"], "gen-2")


if __name__ == "__main__":
    unittest.main()

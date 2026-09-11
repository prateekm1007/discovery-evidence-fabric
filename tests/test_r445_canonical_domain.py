"""tests/test_r445_canonical_domain.py — R445-A: the one canonical
domain-family vocabulary.

Directive R445-A requires:
  1. ONE authoritative domain-family vocabulary — no more
     thermal / THERMAL / GENERIC_ARCHITECTURE / thermal_fluid_process
     meaning different things at different layers.
  2. The canonical domain identity flows UNCHANGED through
     USER PROBLEM -> PROBLEM CONTEXT -> DOMAIN SPEC -> ENGINEERING SPEC
     -> GEOMETRY -> CIO -> DOSSIER -> PACKAGE.
  3. The package compiler CONSUMES the canonical authority (the
     canonicalization happens upstream — never a compiler-side string
     mapping of two vocabularies).
  4. Required tests: thermal, fluid, materials, biomedical, software/ML
     each resolve to exactly one canonical family at every layer.
  5. The deliberately introduced F1 divergence is detected as a BROKEN
     INVARIANT.

The five test problems are FRESH (authored for this round; none appear
in any frozen instrument — the W11 corpus, the attacker-calibration
corpus and the f-series probes are untouched).

Fixtures are SYNTHETIC_TEST_ONLY (Art. XXXVII labels ride in the
package manifest via the rehearsal markers).
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.candidate import Candidate, sha256_obj
from discovery_fabric.engine.engineering_spec import build_engineering_spec
from discovery_fabric.engine.invention_spec import build_invention_spec
from discovery_fabric.engine.domains import (  # noqa: E402
    CANONICAL_DOMAIN_FAMILIES, DOMAIN_TEMPLATES,
    canonical_family_label, canonical_family_of_bridge_archetype,
    canonical_family_of_engine_domain, is_canonical_family,
    resolve_canonical_family)
from discovery_fabric.engine.invention_bridge.bridge import (  # noqa: E402
    bridge as run_bridge)
from discovery_fabric.engine.invention_bridge import domain_spec  # noqa: E402
from discovery_fabric.engine.package_quality_gate import (  # noqa: E402
    run_quality_gate)

CTX = {"run_id": "testrun:r445", "problem_id": "fixture:r445"}

# ---------------------------------------------------------------------------
# The five required families — FRESH problems (no frozen-instrument
# overlap; each exercises its family's whole form).
# ---------------------------------------------------------------------------
FAMILY_PROBLEMS = {
    "thermal": dict(
        device="power electronics cold plate",
        failure_mode="HOTSPOT",
        failure="gallium nitride switch hotspots exceed the solder temperature limit during transient load steps",
        constraint="hold junction-to-coolant temperature rise below 30 K "
        "at 400 A/cm2 without increasing pump power",
        mechanism="graded pin-fin density redistributes coolant flow to match the heat flux map of the switch layout",
        intervention="spatially graded pin-fin cold plate with flow-balancing headers",
        effect="hotspot temperature rise held within the limit at maximum transient duty",
        fals="infrared thermal mapping under the transient load profile vs uniform-fin baseline",
    ),
    "fluid": dict(
        device="precision metering pump head",
        failure_mode="CAVITATION",
        failure="cavitation erosion on the metering pump impeller degrades dosing accuracy within weeks of service",
        constraint="hold dosing accuracy within 0.5 percent at the rated viscosity without lowering the operating speed",
        mechanism="helical inducer raises the inlet pressure ahead of the impeller eye, suppressing vapor bubble formation",
        intervention="integral helical inducer section upstream of the metering impeller",
        effect="cavitation-free dosing at the rated differential and viscosity",
        fals="hydraulic bench sweep of NPSH margin vs dosing-accuracy deviation against the uninduced baseline",
    ),
    "materials": dict(
        device="corrosion protection coating system",
        failure_mode="DELAMINATION",
        failure="protective coating delamination exposes the substrate to chloride attack and shortens service intervals",
        constraint="hold coating adhesion above the qualification threshold through 2000 thermal cycles without changing the substrate alloy",
        mechanism="graded interlayer chemistry relieves the thermal expansion mismatch at the coating-substrate interface",
        intervention="compositionally graded interlayer between the protective coating and the substrate",
        effect="adhesion strength retained across the cyclic qualification range",
        fals="pull-off adhesion testing through the thermal-cycle protocol vs the single-layer baseline",
    ),
    "biomedical": dict(
        device="infusion catheter",
        failure_mode="OCCLUSION",
        failure="drug infusion catheter lumens occlude between replacement cycles, interrupting therapy delivery",
        constraint="maintain lumen patency for the full implantation interval without increasing flush frequency",
        mechanism="surface topography reduces the contact area available for protein adhesion and subsequent clot formation in the lumen",
        intervention="micro-textured infusion catheter inner lumen surface",
        effect="patency maintained across the implantation interval at the standard flush schedule",
        fals="bench flow-decay loop with blood-mimicking fluid vs the smooth-lumen control",
    ),
    "software_ml": dict(
        device="demand forecasting service",
        failure_mode="MODEL_DRIFT",
        failure="forecasting model accuracy decays as the fulfillment demand distribution shifts seasonally, degrading inventory decisions",
        constraint="hold forecast error within the operational budget across quarterly distribution shifts without full retraining campaigns",
        mechanism="distribution-shift monitor triggers targeted model recalibration on the drifted segment before error exceeds budget",
        intervention="drift-aware recalibration pipeline with per-segment error budgets",
        effect="forecast error held within budget across the seasonal shift window",
        fals="backtest over two years of historical demand with injected distribution shifts vs the static model",
    ),
}


def _family_env(family: str, chain: bool = True) -> Candidate:
    """A survivor-shaped envelope for one family's problem (the
    f-series _survivor_env pattern, fresh content)."""
    p = FAMILY_PROBLEMS[family]
    problem_id = f"fixture:r445:{family}"
    problem = {
        "problem_id": problem_id, "device": p["device"],
        "failure_mode": p["failure_mode"], "failure": p["failure"],
        "constraint": p["constraint"],
    }
    env = Candidate(problem=problem, problem_id=problem_id)
    mechanism_rich = (
        f"{p['mechanism']}. The proposed intervention realizes this "
        f"mechanism by placing {p['intervention']} at the failure site "
        f"identified in the problem statement, where the governing "
        f"physical effect produces {p['effect']} under the stated "
        f"constraint ({p['constraint']}); the transfer logic follows from "
        "the custodied source observation and its mechanism source span.")
    ev = {
        "id": f"europepmc:FIXTURE-R445-{family}",
        "source_type": "scientific_paper", "source": "EuropePMC",
        "source_id": f"FIX-R445-{family}",
        "source_uri": f"https://fixture.invalid/r445/{family}",
        "title": f"Fixture study r445 {family}",
        "abstract": (f"In a controlled model, the {p['mechanism']} was "
                     f"demonstrated with the {p['intervention']}, producing "
                     f"the reported effect. A long sentence follows to give "
                     f"the abstract realistic length for truncation checks: "
                     + "the measured behavior remained stable across repeated "
                       "trials under varying load conditions. " * 4),
        "doi": f"10.0000/fixture.r445.{family}",
        "publication_date": "2021-01-01",
        "content_hash": sha256_obj({"t": f"fixture-r445-{family}"}),
    }
    env.evidence = [ev]
    env.evidence_ids = [ev["id"]]
    freeze = {
        "run_id": "testrun:r445", "problem_id": problem_id,
        "frozen_at": "2026-01-01T00:00:00Z", "evidence_count": 1,
        "custody_records": [{"record_id": ev["id"],
                             "content_hash": ev["content_hash"]}],
        "hash_verification_all_pass": True,
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY"}
    freeze["snapshot_hash"] = sha256_obj(freeze)
    env.provenance = {"evidence_freeze": freeze}
    raw = {
        "candidate_id": f"cand:FIXTURE-R445-{family}",
        "falsification_test": p["fals"],
        "mechanism_source_span": p["mechanism"],
        "source_evidence": {"source_id": ev["id"],
                            "source_hash": ev["content_hash"],
                            "source_span": ev["abstract"][:500],
                            "source_title": ev["title"]},
        "mechanism": p["mechanism"],
        "intervention": p["intervention"],
        "expected_effect": p["effect"],
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY",
    }
    env.mechanism_map = {
        "mechanism": mechanism_rich, "intervention": raw["intervention"],
        "expected_effect": raw["expected_effect"],
        "falsification_test": raw["falsification_test"],
        "mechanism_source_span": raw["mechanism_source_span"],
        "raw_candidate": raw}
    attack = {
        "overall": "PASS", "killed_count": 0, "reason": "synthetic pass",
        "attacks": {d: "SURVIVED" for d in (
            "unsupported_mechanism", "weak_transfer", "obvious_combination",
            "prior_art", "contradiction", "boundary_failure",
            "engineering_infeasibility", "regulatory_incompatibility")},
        "invalid_dimensions": [], "v4_corrections_applied": [],
        "prior_art_state": "NO_MATCH_FOUND", "evidence_verified": True,
        "prompt_hash": "0" * 16, "output_hash": "0" * 16,
        "timestamp": "2026-01-01T00:00:00Z",
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY"}
    env.attack_results = attack
    env.prior_art = {"prior_art_status": "NO_MATCH_FOUND",
                     "legacy_status": "NO_MATCHING_EVIDENCE_FOUND",
                     "state_vocabulary": "classify/v4_corrections"}
    env.collision_results = {
        "novelty_risk": "SEARCHED_NO_DIRECT_TITLE_MATCH",
        "patent": {"hits": [], "hit_count": 0, "source_errors": []}}
    if chain:
        from tests.test_f_series_integration import _offline_chain
        _offline_chain(env)
    return env


def _problem_text(p: dict) -> str:
    return " ".join([p["device"], p["failure"], p["constraint"],
                     p["mechanism"], p["intervention"], p["effect"],
                     p["fals"]])


# ---------------------------------------------------------------------------
# 1. The registry — ONE vocabulary, closed, every routing id maps exactly
# ---------------------------------------------------------------------------
class TestRegistryOneVocabulary(unittest.TestCase):
    def test_eleven_canonical_families_with_labels(self):
        self.assertEqual(
            set(CANONICAL_DOMAIN_FAMILIES),
            {"thermal", "fluid", "materials", "biomedical", "software_ml",
             "mechanical", "electronic", "energy", "optical_photonic",
             "acoustic", "generic"})
        labels = [canonical_family_label(f) for f in
                  CANONICAL_DOMAIN_FAMILIES]
        self.assertEqual(len(set(labels)), len(labels),
                         "family labels must be unique")

    def test_every_engine_domain_maps_to_exactly_one_family(self):
        for domain_id in list(DOMAIN_TEMPLATES) + ["UNKNOWN"]:
            fam = canonical_family_of_engine_domain(domain_id)
            self.assertTrue(is_canonical_family(fam), domain_id)
            # exactly one: the reverse map is single-valued by
            # construction — assert membership AND declared routing
            routed = [f for f, s in CANONICAL_DOMAIN_FAMILIES.items()
                      if domain_id in s["engine_domains"]]
            self.assertEqual(len(routed), 1,
                             f"{domain_id} must be declared by exactly one "
                             f"family, got {routed}")

    def test_every_bridge_archetype_maps_to_exactly_one_family(self):
        archetypes = ["VEHICLE", "MEDICAL_DEVICE", "FLUID_DEVICE",
                      "THERMAL_SYSTEM", "MECHANICAL_COMPONENT",
                      "ELECTRONIC_SYSTEM", "ENERGY_STORAGE",
                      "GENERIC_ARCHITECTURE", "PROCESS_FLOW",
                      "GENERIC_FALLBACK", "ENGINEERING_PARAMETRIC"]
        for a in archetypes:
            fam = canonical_family_of_bridge_archetype(a)
            self.assertTrue(is_canonical_family(fam), a)

    def test_noncanonical_values_rejected(self):
        # the exact strings the R445 directive names as the defect
        for bad in ("THERMAL", "thermal_fluid_process",
                    "GENERIC_ARCHITECTURE", "fluidics_hydraulic",
                    "MEDICAL", "medical", "vehicle", "electronics",
                    "thermal_system", ""):
            self.assertFalse(is_canonical_family(bad), repr(bad))

    def test_registry_artifact_publishes_the_families(self):
        reg = json.loads(
            (Path(__file__).resolve().parents[1]
             / "ENGINEERING_DOMAIN_REGISTRY.json").read_text())
        self.assertEqual(reg["version"], "1.1.0")
        self.assertEqual(set(reg["canonical_domain_families"]),
                         set(CANONICAL_DOMAIN_FAMILIES))
        for fam, spec in reg["canonical_domain_families"].items():
            self.assertEqual(spec["label"], canonical_family_label(fam))


# ---------------------------------------------------------------------------
# 2. Resolution — the five required families, deterministic
# ---------------------------------------------------------------------------
class TestRequiredFamiliesResolve(unittest.TestCase):
    def test_five_required_families_resolve_exactly(self):
        for family, p in FAMILY_PROBLEMS.items():
            r = resolve_canonical_family(_problem_text(p))
            self.assertEqual(r["canonical_family"], family,
                             f"{family} problem resolved "
                             f"{r['canonical_family']}")
            # the FULL basis is recorded (auditable, Art. XXVII)
            self.assertIn("score_table", r)
            self.assertTrue(r["score_table"])

    def test_resolution_is_deterministic(self):
        for p in FAMILY_PROBLEMS.values():
            t = _problem_text(p)
            r1 = resolve_canonical_family(t)
            r2 = resolve_canonical_family(t)
            self.assertEqual(r1["canonical_family"], r2["canonical_family"])

    def test_unsignaled_problem_resolves_honest_generic(self):
        r = resolve_canonical_family(
            "improve a scheduling optimization process")
        self.assertEqual(r["canonical_family"], "generic")

    def test_whole_form_device_identity_dominates_component_mentions(self):
        # an implantable stimulator with a battery is a BIOMEDICAL
        # family technology — its energy-harvesting mechanism is a
        # component mention, not the application family
        r = resolve_canonical_family(
            "implant stimulator: battery replacement surgery every "
            "recharge cycle; thermoelectric body-heat harvesting "
            "trickle-charges the cell")
        self.assertEqual(r["canonical_family"], "biomedical")
        self.assertIn("whole_form_basis", r)
        # a hospital dashboard is still software_ml (deployment words
        # are not device-identity words)
        r2 = resolve_canonical_family(
            "machine learning demand forecasting service deployed on "
            "hospital edge hardware; classifier drift degrades alerts")
        self.assertEqual(r2["canonical_family"], "software_ml")


# ---------------------------------------------------------------------------
# 3. Layer continuity — every layer resolves to exactly one canonical
#    family (the directive's core requirement)
# ---------------------------------------------------------------------------
class TestLayerContinuity(unittest.TestCase):
    def _run_family(self, family: str) -> dict:
        env = _family_env(family)
        spec = build_invention_spec(env, CTX)
        eng = build_engineering_spec(spec, env, CTX)
        from discovery_fabric.engine.experiment_selector import (
            select_decisive_experiment)
        ke = select_decisive_experiment(env)
        problem = env.problem
        run_result = {
            "session_id": f"testrun:r445:{family}",
            "run_id": f"testrun:r445:{family}",
            "problem_id": problem.get("problem_id"),
            "user_text": problem.get("failure"),
            "title": (f"{problem.get('device')} — "
                      f"{problem.get('failure_mode')}"),
            "domain": (eng.get("why_this_domain") or {}).get("domain"),
            "invention_specification": spec,
            "engineering_specification": eng,
            "final_state": {
                "final_status": (env.epistemic_state or {}).get(
                    "final_status"),
                "final_envelope_hash": env.envelope_hash(),
            },
            "decisive_experiment": ke,
            "run_state": {"generations": {"generations": []}},
            "evidence_pack": {"retrieval": []},
        }
        vis = {
            "visualizability_class": "SYSTEM_3D",
            "intervention_site": problem.get("device", ""),
            "subsystems": [s.get("name") for s in
                           (eng.get("system_architecture")
                            or {}).get("subsystems") or []
                           if isinstance(s, dict)][:6],
            "classification_basis": {"reason": "fixture"},
        }
        return {"env": env, "spec": spec, "eng": eng, "ke": ke,
                "run_result": run_result, "vis": vis}

    def test_every_layer_resolves_one_canonical_family(self):
        for family, p in FAMILY_PROBLEMS.items():
            with self.subTest(family=family):
                ctx = self._run_family(family)
                eng = ctx["eng"]
                # LAYER: ENGINEERING SPEC (the upstream authority)
                wd = eng["why_this_domain"]
                self.assertEqual(wd["canonical_family"], family)
                self.assertEqual(
                    (eng["applicability"]["canonical_domain"]
                     ["canonical_family"]), family)
                # LAYER: DOMAIN SPEC (the bridge consumes upstream)
                out = domain_spec.build_spec_from_state(
                    ctx["run_result"], ctx["vis"])
                self.assertEqual(out["canonical_family"], family)
                self.assertEqual(out["spec"]["canonical_family"], family)
                # the archetype is DERIVED from the family (registry
                # routing) and is never a second semantic namespace
                self.assertIn("technology_class", out["spec"])
                # LAYER: GEOMETRY + CIO + PACKAGE (the full bridge)
                with tempfile.TemporaryDirectory() as td:
                    result = run_bridge(
                        ctx["run_result"], None, work_dir=td,
                        build_renders=False,
                        run_id=f"sess_r445_{family}")
                    g = result["geometry_out"]
                    self.assertIsNotNone(g)
                    self.assertEqual(g["domain_family"], family)
                    self.assertEqual(
                        (g.get("geometry_spec") or {}).get(
                            "canonical_family"), family)
                    # the persisted artifact identity
                    aid = json.loads(
                        (Path(td) / "MODEL" / "ARTIFACT_IDENTITY.json")
                        .read_text())
                    self.assertEqual(aid["domain_family"], family)
                    # the persisted geometry spec
                    gs = json.loads(
                        (Path(td) / "MODEL" / "GEOMETRY_SPEC.json")
                        .read_text())
                    self.assertEqual(gs["canonical_family"], family)
                    # LAYER: CIO (consumes geometry)
                    cio = result.get("cio_updated") or {}
                    self.assertEqual(
                        (cio.get("geometry") or {}).get("domain_family"),
                        family)
                    # LAYER: PACKAGE (consumes the canonical authority)
                    pkg = result.get("package_out") or {}
                    model_path = list(
                        Path(td).rglob("TECHNOLOGY_PACKAGE_MODEL.json"))
                    self.assertTrue(model_path,
                                    "the package model must be built")
                    model = json.loads(model_path[0].read_text())
                    self.assertEqual(
                        model["identity"]["domain_family"], family)
                    self.assertEqual(
                        model["artifact_state"]["domain_family"], family)
                    # the compiler consumed the upstream authority
                    # (identity == the engineering spec's own decision —
                    # never a compiler-side re-derivation or mapping)
                    self.assertEqual(
                        model["identity"]["domain_family"],
                        eng["why_this_domain"]["canonical_family"])
                    # GATE A: no divergence, no non-canonical vocabulary
                    pkg_dir = model_path[0].parent
                    verdict = run_quality_gate(str(pkg_dir))
                    gate_a = verdict["gates"]["A"]
                    codes = [f["code"] for f in gate_a["findings"]]
                    self.assertNotIn("A-INTERNAL-DIVERGENT", codes)
                    self.assertNotIn("A-NONCANONICAL-DOMAIN", codes)


# ---------------------------------------------------------------------------
# 4. The F1 divergence — detected as a broken invariant
# ---------------------------------------------------------------------------
class TestF1DivergenceDetected(unittest.TestCase):
    def _built_thermal_tree(self) -> Path:
        ctx = TestLayerContinuity()._run_family("thermal")
        td = tempfile.mkdtemp(prefix="r445_f1_")
        result = run_bridge(ctx["run_result"], None, work_dir=td,
                            build_renders=False, run_id="sess_r445_f1")
        model_path = list(Path(td).rglob("TECHNOLOGY_PACKAGE_MODEL.json"))
        assert model_path, "thermal package must build for the injection"
        return model_path[0].parent

    def test_f1_shape_divergent_declarations_detected(self):
        """The exact F1 defect shape: the ENGINE-vocabulary identity
        stamp ('thermal') next to a BRIDGE-vocabulary nested declaration
        ('GENERIC_ARCHITECTURE') — the R444 A-INTERNAL-DIVERGENT
        reproduction, now also carrying the non-canonical violation."""
        pkg_dir = self._built_thermal_tree()
        # inject the F1 shape: a nested bridge-vocabulary declaration
        model_p = pkg_dir / "TECHNOLOGY_PACKAGE_MODEL.json"
        model = json.loads(model_p.read_text())
        model["artifact_state"]["domain_family"] = "GENERIC_ARCHITECTURE"
        model_p.write_text(json.dumps(model, indent=2))
        verdict = run_quality_gate(str(pkg_dir))
        gate_a = verdict["gates"]["A"]
        codes = [f["code"] for f in gate_a["findings"]]
        self.assertIn("A-INTERNAL-DIVERGENT", codes)
        self.assertIn("A-NONCANONICAL-DOMAIN", codes)
        self.assertNotEqual(verdict["package_quality"], "PASS")

    def test_f1_single_noncanonical_vocabulary_detected(self):
        """The single-wrong-vocabulary shape: every layer CONSISTENTLY
        declares the old bridge vocabulary — no divergence, but the
        invariant 'domain_family is a canonical family id' is broken."""
        pkg_dir = self._built_thermal_tree()
        # rewrite EVERY domain_family declaration to one old-vocabulary
        # value (consistent — the subtle F1 shape)
        for p in sorted(pkg_dir.rglob("*.json")):
            try:
                d = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(d, dict):
                continue
            changed = False
            if d.get("domain_family"):
                d["domain_family"] = "GENERIC_ARCHITECTURE"
                changed = True
            for k, v in d.items():
                if isinstance(v, dict) and v.get("domain_family"):
                    v["domain_family"] = "GENERIC_ARCHITECTURE"
                    changed = True
            if changed:
                p.write_text(json.dumps(d, indent=2))
        verdict = run_quality_gate(str(pkg_dir))
        gate_a = verdict["gates"]["A"]
        codes = [f["code"] for f in gate_a["findings"]]
        self.assertIn("A-NONCANONICAL-DOMAIN", codes)
        self.assertNotIn("A-INTERNAL-DIVERGENT", codes)
        self.assertNotEqual(verdict["package_quality"], "PASS")

    def test_benchmark_style_and_case_variant_labels_rejected(self):
        """'thermal_fluid_process' (benchmark labels) and 'THERMAL'
        (case variants) are broken invariants, not canonical families."""
        for bad in ("thermal_fluid_process", "THERMAL",
                    "fluidics_hydraulic"):
            self.assertFalse(is_canonical_family(bad))


# ---------------------------------------------------------------------------
# 5. The upstream authority — consumed, never re-derived downstream
# ---------------------------------------------------------------------------
class TestUpstreamAuthority(unittest.TestCase):
    def test_bridge_consumes_engineering_spec_decision(self):
        """The bridge's canonical family is the engineering spec's own
        decision — even when a keyword-only resolution would have said
        something else (the upstream authority wins)."""
        # an implant stimulator: keyword-only scoring favors 'energy'
        # (battery/photovoltaic mentions) but the whole-form layer and
        # the upstream decision say biomedical
        rr = {
            "user_text": (
                "implant stimulator: battery replacement surgery every "
                "recharge cycle; thermoelectric body-heat harvesting "
                "trickle-charges the cell; hermetic MR-conditional "
                "packaging"),
            "engineering_specification": {
                "why_this_domain": {
                    "domain": "energy_harvesting",
                    "canonical_family": "biomedical"}},
        }
        out = domain_spec.build_spec_from_state(rr, {
            "intervention_site": "implant housing",
            "subsystems": ["thermoelectric stack", "cell"],
        })
        self.assertEqual(out["canonical_family"], "biomedical")
        self.assertEqual(out["spec"]["canonical_family"], "biomedical")
        basis = out["canonical_resolution"]["basis"]
        self.assertTrue(basis.get("upstream_record"),
                        "the family must be recorded as consumed from "
                        "the upstream authority")

    def test_fallback_uses_the_same_registry(self):
        """Legacy states without an upstream decision resolve from the
        SAME registry via the shared consumer ladder (recorded with the
        ladder step — never a second vocabulary, never a silent
        re-derivation)."""
        rr = {"user_text": (
            "precision metering pump head: cavitation erosion on the "
            "impeller degrades dosing accuracy")}
        out = domain_spec.build_spec_from_state(rr, {
            "intervention_site": "pump head", "subsystems": ["impeller"]})
        self.assertEqual(out["canonical_family"], "fluid")
        basis = out["canonical_resolution"]["basis"]
        self.assertEqual(basis.get("ladder_step"), 3)
        self.assertIn("registry resolution over the run's own recorded "
                      "problem words", basis.get("source", ""))

    def test_compiler_reads_the_upstream_canonical_field(self):
        """The package identity's domain_family is the upstream
        canonical_family field verbatim — the compiler consumes the
        authority; it does not re-derive or map strings."""
        ctx = TestLayerContinuity()._run_family("biomedical")
        with tempfile.TemporaryDirectory() as td:
            result = run_bridge(ctx["run_result"], None, work_dir=td,
                                build_renders=False,
                                run_id="sess_r445_upstream")
            model_path = list(
                Path(td).rglob("TECHNOLOGY_PACKAGE_MODEL.json"))
            self.assertTrue(model_path)
            model = json.loads(model_path[0].read_text())
            self.assertEqual(
                model["identity"]["domain_family"],
                ctx["eng"]["why_this_domain"]["canonical_family"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

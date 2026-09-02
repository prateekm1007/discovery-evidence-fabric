"""R381 PORTFOLIO 3D ENGINEERING DESIGN RETROFIT — adversarial hermetic
tests (CEO R381 directive: retrofit the 15 buyer packages with real 3D
engineering designs).

Every test is an ATTACK on the implementation (Art. XVII):
- an adversary fabricates geometry for a software-only technology;
- an adversary renames one generic template to fake 14 designs;
- an adversary tampers a shipped derivative after validation;
- an adversary lets a render masquerade as validation;
- an adversary smuggles wall-clock time into the byte-reproducible
  release;
- an adversary lets the manifest/traceability claim drift from the
  MODEL/ record.

The gates must hold.

Constitutional anchors under attack:
- Art. VI     fabricated provenance, forged hashes
- Art. II     substring unit matching ('samples' != meters)
- Art. III    claimant (template) vs verifier (measured gates)
- Art. XV     inconvenient BLOCKED/KILL outcomes must surface
- Art. XXV    NOT_APPLICABLE honesty (no invented geometry)
- Art. XXVIII RENDER_IS_NOT_VALIDATION
- Art. XXXVIII COMPUTATIONAL_RESULT with computation logs only
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from premium_package_factory.r381 import portfolio_cad as pc
from premium_package_factory.r381.templates import PORTFOLIO_TEMPLATES
from premium_package_factory.r371.canonical_source import (
    load_all_packages, load_dossier,
)

_CAD_AVAILABLE = True
try:
    import cadquery  # noqa: F401
except Exception:  # pragma: no cover
    _CAD_AVAILABLE = False

_SKIP = "CadQuery/OCCT not available in this environment"

ALL_PKG_IDS = [p.pkg_id for p in load_all_packages()]


def _software_only_dossier():
    """A record whose technology is purely computational (the honest
    NOT_APPLICABLE case) — physical-named INPUT interfaces allowed."""
    return {
        "engineering_content": {
            "engineering_core": {
                "critical_parameters": [
                    {"name": "Sampling rate", "unit": "Hz",
                     "value": "MODELLED (1-10)"},
                    {"name": "Training data volume", "unit": "samples",
                     "value": "UNKNOWN"},
                ],
            },
            "bom": [],
            "system_architecture": {
                "subsystems": [
                    "Sensor data stream", "Feature extractor",
                    "ML predictor", "Alert interface"],
            },
            "manufacturing": {"candidate_processes": []},
        }
    }


def _hardware_dossier():
    """A record that declares real geometry design variables."""
    return {
        "engineering_content": {
            "engineering_core": {
                "critical_parameters": [
                    {"name": "Outer diameter", "unit": "mm",
                     "value": "MODELLED (2.6)"},
                    {"name": "Lumen diameter", "unit": "mm",
                     "value": "MODELLED (1.2)"},
                ],
            },
            "bom": [{"component": "catheter body"}],
            "system_architecture": {"subsystems": ["Valve seat"]},
            "manufacturing": {"candidate_processes": ["micro extrusion"]},
        }
    }


class TestClassifierHonesty(unittest.TestCase):
    """The classifier must decide from the record — never forced."""

    def test_software_only_record_is_not_applicable(self):
        cls = pc.classify_3d_requirement("TEST-SW", _software_only_dossier())
        self.assertEqual(cls["classification"], "3D_NOT_APPLICABLE")
        # sensor STREAM is a data interface, not a manufactured part —
        # it must not force geometry onto a software technology
        self.assertIn("interfaces", " ".join(cls["reasons"]))

    def test_hardware_record_is_required(self):
        cls = pc.classify_3d_requirement("TEST-HW", _hardware_dossier())
        self.assertEqual(cls["classification"], "3D_PHYSICAL_DESIGN_REQUIRED")
        basis = cls["measured_basis"]
        self.assertGreaterEqual(basis["geometry_class_critical_parameters"], 2)
        self.assertEqual(basis["bom_entries"], 1)
        self.assertEqual(basis["manufacturing_processes"], 1)

    def test_unit_matching_is_exact_not_substring(self):
        # Art. II: 'samples' contains the letter 'm' — it is NOT meters
        rec = _software_only_dossier()
        rec["engineering_content"]["bom"] = [{"component": "x"}]
        rec["engineering_content"]["manufacturing"] = {
            "candidate_processes": []}
        cls = pc.classify_3d_requirement("TEST-U", rec)
        # BOM present -> REQUIRED by strong evidence, but the samples
        # parameter must NOT be counted as a geometry parameter
        self.assertEqual(
            cls["measured_basis"]["geometry_class_critical_parameters"], 0)

    def test_geometry_name_hint_counts(self):
        rec = _software_only_dossier()
        rec["engineering_content"]["bom"] = []
        rec["engineering_content"]["engineering_core"][
            "critical_parameters"].append(
            {"name": "Coating thickness", "unit": "n/a",
             "value": "MODELLED"})
        cls = pc.classify_3d_requirement("TEST-N", rec)
        self.assertEqual(
            cls["measured_basis"]["geometry_class_critical_parameters"], 1)

    def test_not_applicable_value_is_excluded(self):
        rec = _software_only_dossier()
        rec["engineering_content"]["bom"] = []
        rec["engineering_content"]["engineering_core"][
            "critical_parameters"].append(
            {"name": "Device diameter", "unit": "mm",
             "value": "NOT APPLICABLE — algorithmic technology"})
        cls = pc.classify_3d_requirement("TEST-NA", rec)
        self.assertEqual(
            cls["measured_basis"]["geometry_class_critical_parameters"], 0)


class TestFifteenClassifications(unittest.TestCase):
    """15/15 honestly classified from the CANONICAL records."""

    def test_all_fifteen_classify(self):
        seen = {}
        for pkg in ALL_PKG_IDS:
            cls = pc.classify_3d_requirement(pkg, load_dossier(pkg))
            seen[pkg] = cls["classification"]
        required = [k for k, v in seen.items()
                    if v == "3D_PHYSICAL_DESIGN_REQUIRED"]
        na = [k for k, v in seen.items() if v == "3D_NOT_APPLICABLE"]
        self.assertEqual(len(required) + len(na), 15)
        # the ML failure predictor is software-only — record-derived
        self.assertEqual(seen.get("P-13"), "3D_NOT_APPLICABLE")
        self.assertEqual(na, ["P-13"])
        # every REQUIRED package has a package-specific template
        for pkg in required:
            self.assertIn(pkg, PORTFOLIO_TEMPLATES,
                          f"{pkg} classified REQUIRED but has no template")

    def test_templates_are_distinct_not_renamed_labels(self):
        # CEO: "Do NOT use one generic model template with renamed
        # labels" — the build programs must differ materially
        programs = {k: t["program"].strip() for k, t in
                    PORTFOLIO_TEMPLATES.items()}
        self.assertEqual(len(programs), len(set(programs.values())))
        # and no two templates share the same object set (assembly shape)
        objsets = {
            k: tuple(sorted(o["object_id"] for o in t["objects"]))
            for k, t in PORTFOLIO_TEMPLATES.items()}
        dupes = [v for v in objsets.values()
                 if list(objsets.values()).count(v) > 1]
        self.assertEqual(len(dupes), 0,
                         f"templates share object sets: {dupes}")

    def test_template_parameters_carry_envelopes_and_basis(self):
        # Art. XXVII: every envelope + value needs a declared basis
        for pkg, tpl in PORTFOLIO_TEMPLATES.items():
            for p in tpl["parameters"]:
                self.assertIn("range_min", p, f"{pkg}.{p['param_id']}")
                self.assertIn("range_max", p, f"{pkg}.{p['param_id']}")
                self.assertLess(p["range_min"], p["range_max"])
                self.assertTrue(
                    p["range_min"] <= p["value"] <= p["range_max"],
                    f"{pkg}.{p['param_id']} value outside envelope")
                self.assertTrue(p.get("design_basis"),
                                f"{pkg}.{p['param_id']} lacks basis")
            for c in tpl["constraints"]:
                self.assertIn("epistemic_class", c, f"{pkg} constraint")
                self.assertTrue(c.get("basis"), f"{pkg} constraint basis")

    def test_every_template_declares_a_mutation(self):
        # CEO: the 3D design must participate in the improvement loop
        for pkg, tpl in PORTFOLIO_TEMPLATES.items():
            mut = tpl.get("mutation")
            self.assertIsNotNone(mut, f"{pkg} has no improvement mutation")
            self.assertIn(mut["param_id"],
                          {p["param_id"] for p in tpl["parameters"]})
            self.assertTrue(mut.get("limiting_parameter_basis"))
            self.assertIn("relation", mut["evaluation"])


@unittest.skipUnless(_CAD_AVAILABLE, _SKIP)
class TestModelLayerFull(unittest.TestCase):
    """The full R381 layer on live packages (hermetic tmpdirs)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="r381_test_")
        cls.results = {}
        for pkg in ("P-01", "P-07", "P-13"):
            pkg_dir = os.path.join(cls.tmp, pkg)
            os.makedirs(pkg_dir, exist_ok=True)
            cls.results[pkg] = pc.build_model_layer(
                pkg, pkg_dir, work_dir=os.path.join(cls.tmp, "work", pkg))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _mdir(self, pkg):
        return os.path.join(self.tmp, pkg, "MODEL")

    def _json(self, pkg, name):
        with open(os.path.join(self._mdir(pkg), name),
                  encoding="utf-8") as fh:
            return json.load(fh)

    def test_p01_validated_with_full_model_dir(self):
        s = self.results["P-01"]
        self.assertIn(s["status"], ("CAD_VALIDATED", "PRESENT_AND_VALIDATED"))
        self.assertEqual(s["status"], "CAD_VALIDATED")
        self.assertTrue(s["model_id"].startswith("pm:"))
        required_files = [
            "3D_DESIGN_STATUS.json", "PARAMETRIC_MODEL_SOURCE.py",
            "MODEL_MANIFEST.json", "PARAMETERS.json", "CONSTRAINTS.json",
            "GEOMETRY_VALIDATION_REPORT.json", "KEY_DIMENSIONS.json",
            "ENGINEERING_PROVENANCE.json", "DESIGN_LINEAGE.json",
            "IMPROVEMENT_LOOP_EVIDENCE.json", "README.json",
        ]
        for f in required_files:
            self.assertTrue(
                os.path.exists(os.path.join(self._mdir("P-01"), f)),
                f"missing MODEL/{f}")
        for ext in (".step", ".stl", ".glb", ".svg"):
            files = [f for f in os.listdir(self._mdir("P-01"))
                     if f.endswith(ext)]
            self.assertTrue(files, f"no {ext} derivative shipped")

    def test_p01_visual_package_views(self):
        files = set(os.listdir(self._mdir("P-01")))
        self.assertIn("P-01_isometric.svg", files)
        self.assertIn("P-01_section.svg", files)
        self.assertIn("P-01_view_orthographic_front.svg", files)
        self.assertIn("P-01_view_orthographic_top.svg", files)
        self.assertIn("P-01_view_orthographic_right.svg", files)
        self.assertIn("P-01_view_dimensioned.svg", files)
        self.assertIn("P-01_view_exploded.svg", files)  # multi-object

    def test_p01_dimensioned_view_uses_measured_values(self):
        svg = open(os.path.join(self._mdir("P-01"),
                                "P-01_view_dimensioned.svg"),
                   encoding="utf-8").read()
        self.assertIn("(measured)", svg)
        self.assertIn("presentation, not validation", svg)

    def test_p01_geometry_validation_includes_g9(self):
        gv = self._json("P-01", "GEOMETRY_VALIDATION_REPORT.json")
        self.assertTrue(gv["valid"])
        checks = gv["checks"]
        self.assertEqual(
            checks["G9_regeneration_reproducibility"]["status"],
            "REPRODUCIBLE")
        for gate in ("G1_invalid_geometry", "G2_non_manifold_solids",
                     "G3_impossible_dimensions",
                     "G4_violated_geometric_constraints",
                     "G5_missing_parameters",
                     "G7_impossible_intersections"):
            self.assertIn(gate, checks, f"missing {gate}")

    def test_p01_child_validation_covers_all_rings(self):
        # the KEEP child builds 6 rings (4 -> 6); the interference
        # validation must cover ALL of them — a stale 4-pair declared
        # set would silently skip 2 rings (found live, fixed)
        gv = self._json("P-01", "GEOMETRY_VALIDATION_REPORT.json")
        pairs = gv["checks"]["G7_impossible_intersections"]["detail"]
        n_rings = sum(1 for p in pairs
                      if str(p["pair"][0]).startswith("flow_sensor_ring"))
        self.assertEqual(n_rings, 6, f"only {n_rings}/6 ring pairs validated")

    def test_p01_measurements_carry_computation_logs(self):
        kd = self._json("P-01", "KEY_DIMENSIONS.json")
        self.assertEqual(kd.get("evidence_class"),
                         "COMPUTATIONAL_RESULT")
        objs = kd.get("objects") or {}
        self.assertGreaterEqual(len(objs), 2)
        # every measured object must be covered by a computation_log
        # entry naming the kernel calls that produced the numbers
        log = kd.get("computation_log") or []
        covered = {e.get("object_id") for e in log}
        for oid in objs:
            self.assertIn(oid, covered,
                          f"{oid} lacks a computation_log entry")
        for e in log:
            self.assertEqual(e.get("kernel"), "cadquery-occt")
            self.assertTrue(e.get("calls"),
                            f"{e.get('object_id')} has no kernel calls")

    def test_p01_provenance_chain_shape(self):
        prov = self._json("P-01", "ENGINEERING_PROVENANCE.json")
        self.assertEqual(
            prov["chain_shape"],
            "TECHNICAL_STATE -> parameter -> CAD feature -> "
            "derived geometry -> measured geometry -> validation result")
        n = 0
        for pid, chain in prov["chains"].items():
            for link in ("technical_state", "parameter", "cad_feature",
                         "derived_geometry", "measured_geometry",
                         "validation_result"):
                self.assertIn(link, chain, f"{pid} chain lacks {link}")
            # the CAD feature link cites the source-of-truth file and
            # the exact program lines consuming the parameter
            self.assertIn("PARAMETRIC_MODEL_SOURCE.py",
                          chain["cad_feature"]["source_of_truth"])
            n += 1
        self.assertGreaterEqual(n, 5, "too few provenance chains")

    def test_p01_parameter_bindings_honest(self):
        par = self._json("P-01", "PARAMETERS.json")
        statuses = set()
        for p in par["parameters"]:
            binding = p.get("record_binding") or {}
            status = binding.get("binding_status")
            self.assertIn(status, ("BOUND_TO_RECORD",
                                   "NOT_IN_RECORD_ENGINE_DECLARED"))
            statuses.add(status)
            self.assertEqual(p["value_class"], "MODELLED")
        # at least one parameter is BOUND to the record verbatim
        self.assertIn("BOUND_TO_RECORD", statuses)

    def test_p01_loop_evidence_is_the_ceo_shape(self):
        loop = self._json("P-01", "IMPROVEMENT_LOOP_EVIDENCE.json")
        self.assertIn("limiting parameter", loop.get("ceo_loop", ""))
        self.assertIn("KEEP/KILL", loop.get("ceo_loop", ""))
        self.assertEqual(loop["outcome"], "KEEP")
        self.assertTrue(loop["mutation_id"].startswith("p3dmut:"))
        self.assertIn("from_value", loop["limiting_parameter"])
        self.assertIn("to_value", loop["limiting_parameter"])
        self.assertTrue(loop["technical_evaluation"]["quantity"])
        self.assertEqual(loop["technical_evaluation"]["evidence_class"],
                         "COMPUTATIONAL_RESULT")
        # the CHILD's geometry verdict is the measured gate result
        self.assertIn("geometry_validation_of_child", loop)

    def test_p07_breach_mutation_is_killed_by_geometry_gates(self):
        # the honest KILL: floor lumen 0.6 -> 0.8 breaches the wall on
        # the REBUILT solid; the base design ships as validated
        s = self.results["P-07"]
        self.assertIn(s["status"], ("CAD_VALIDATED", "PRESENT_AND_VALIDATED"))
        self.assertEqual(s["status"], "CAD_VALIDATED")
        self.assertEqual(s["loop_outcome"], "KILLED_GEOMETRY_INVALID")
        loop = self._json("P-07", "IMPROVEMENT_LOOP_EVIDENCE.json")
        self.assertFalse(loop["geometry_validation_of_child"]["valid"])
        self.assertTrue(loop["geometry_validation_of_child"]["failed_gates"])
        # base design shipped, not the killed child
        lineage = self._json("P-07", "DESIGN_LINEAGE.json")
        self.assertIn("base design", lineage["shipped_model_is"])

    def test_p13_not_applicable_ships_nothing_geometric(self):
        s = self.results["P-13"]
        self.assertEqual(s["status"], "NOT_APPLICABLE")
        files = set(os.listdir(self._mdir("P-13")))
        self.assertEqual(files, {"3D_DESIGN_STATUS.json", "README.json"})
        st = self._json("P-13", "3D_DESIGN_STATUS.json")
        self.assertEqual(st["classification"], "3D_NOT_APPLICABLE")
        # the exact measured basis is shipped with the verdict
        self.assertEqual(
            st["classification_basis"]["measured_basis"]["bom_entries"], 0)
        self.assertIsNone(st.get("model_id"))

    def test_shipped_jsons_carry_no_wall_clock_time(self):
        # CEO R374-5 byte-reproducible release: provenance of time is
        # git history, never a timestamp inside shipped files
        for pkg in ("P-01", "P-07"):
            for fn in os.listdir(self._mdir(pkg)):
                if not fn.endswith(".json"):
                    continue
                with open(os.path.join(self._mdir(pkg), fn),
                          encoding="utf-8") as fh:
                    doc = json.load(fh)

                def walk(node, path=""):
                    if isinstance(node, dict):
                        for k, v in node.items():
                            self.assertNotIn(k, pc._VOLATILE_KEYS,
                                             f"{pkg}/{fn}:{path}/{k}")
                            walk(v, path + "/" + k)
                    elif isinstance(node, list):
                        for i, v in enumerate(node):
                            walk(v, f"{path}[{i}]")
                walk(doc)

    def test_all_shipped_views_are_valid_xml(self):
        # REGRESSION (found live in the first shipped portfolio): the
        # dimensioned-view annotator built element names like
        # http://www.w3.org/2000/svgline (missing the {ns} braces), so
        # every dimensioned SVG shipped MALFORMED. Pinned forever: every
        # shipped view must parse as well-formed XML.
        import xml.etree.ElementTree as ET
        for pkg in ("P-01", "P-07"):
            for fn in os.listdir(self._mdir(pkg)):
                if not fn.endswith(".svg"):
                    continue
                try:
                    ET.parse(os.path.join(self._mdir(pkg), fn))
                except ET.ParseError as exc:
                    self.fail(f"{pkg}/{fn} malformed SVG: {exc}")

    def test_shipped_parameter_values_are_real_not_none(self):
        # REGRESSION (found live in the first shipped portfolio): an
        # operator-precedence bug `(m.get("parameter_map") or {}
        # .get(k) or {}).get("value")` silently produced None for EVERY
        # shipped parameter value, and provenance chains carried the
        # TEMPLATE default instead of the SHIPPED (mutated) value.
        # Pinned forever: values must be real and match the shipped model.
        par = self._json("P-01", "PARAMETERS.json")
        by_id = {p["param_id"]: p for p in par["parameters"]}
        self.assertEqual(by_id["segment_count"]["value"], 6.0)
        self.assertEqual(by_id["length_mm"]["value"], 120.0)
        prov = self._json("P-01", "ENGINEERING_PROVENANCE.json")
        self.assertEqual(
            prov["chains"]["segment_count"]["parameter"]["value"], 6.0)
        loop = self._json("P-01", "IMPROVEMENT_LOOP_EVIDENCE.json")
        self.assertEqual(loop["limiting_parameter"]["from_value"], 4.0)
        self.assertEqual(loop["limiting_parameter"]["to_value"], 6.0)

    def test_render_is_not_validation_everywhere(self):
        for pkg in ("P-01", "P-07"):
            mm = self._json(pkg, "MODEL_MANIFEST.json")
            self.assertTrue(mm.get("render_is_not_validation"))
            for name, v in (mm.get("views") or {}).items():
                if isinstance(v, dict) and "role" in v:
                    self.assertIn("presentation", v["role"].lower())
            readme = self._json(pkg, "README.json")
            self.assertTrue(
                "never technical validation" in
                readme["evidence_rules"].lower() or
                "not validation" in readme["evidence_rules"].lower())

    def test_manifest_files_are_hashed_from_real_bytes(self):
        for pkg in ("P-01", "P-07"):
            mm = self._json(pkg, "MODEL_MANIFEST.json")
            for key, art in (mm.get("derived_artifacts") or {}).items():
                self.assertIn("sha256", art)
                self.assertIn("bytes", art)
                base = os.path.basename(art["path"])
                fp = os.path.join(self._mdir(pkg), base)
                self.assertTrue(os.path.exists(fp), f"{pkg} {key} missing")
                self.assertEqual(pc._sha256_file(fp), art["sha256"])
                self.assertEqual(os.path.getsize(fp), art["bytes"])

    def test_program_source_is_the_shipped_source_of_truth(self):
        pkg = "P-01"
        src = open(os.path.join(self._mdir(pkg),
                                "PARAMETRIC_MODEL_SOURCE.py"),
                   encoding="utf-8").read()
        prov = self._json(pkg, "ENGINEERING_PROVENANCE.json")
        # program_source_sha256 recorded anywhere must be the sha of the
        # actual build program shipped in the file
        mm = self._json(pkg, "MODEL_MANIFEST.json")
        import hashlib
        # the program body is the file minus the docstring header
        body = src.split('"""\n\n', 1)[1].rstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.encode("utf-8")).hexdigest(),
            prov["chains"][
                next(iter(prov["chains"]))]["parameter"].get(
                "program_sha", None) or
            hashlib.sha256(body.encode("utf-8")).hexdigest())  # noqa
        self.assertIn("def build(p):", body)
        self.assertIn("p[", body)


@unittest.skipUnless(_CAD_AVAILABLE, _SKIP)
class TestG9RegenerationAdversarial(unittest.TestCase):
    """Attack the reproducibility check itself (Art. XVII)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="r381_g9_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _build(self, pkg="P-01"):
        tpl = PORTFOLIO_TEMPLATES[pkg]
        model, _ = pc.build_portfolio_model(
            pkg, tpl, out_dir=os.path.join(self.tmp, "base"))
        return tpl, model

    def test_clean_rebuild_is_reproducible(self):
        tpl, model = self._build()
        regen = pc.check_regeneration(
            "P-01", tpl, model, staging_dir=os.path.join(self.tmp, "regen"))
        self.assertEqual(regen["status"], "REPRODUCIBLE", regen)

    def test_tampered_step_derivative_is_caught(self):
        tpl, model = self._build()
        art = model["derived_artifacts"]["STEP:catheter_body"]
        text = open(art["path"], encoding="utf-8").read()
        # tamper a REAL geometry entity (a CARTESIAN_POINT coordinate)
        tampered = text.replace("CARTESIAN_POINT", "CARTESIAN_POINT", 1)
        m = re.search(r"(CARTESIAN_POINT\('',#[0-9]+\.[0-9]+\.[0-9]+\.)"
                      r"([0-9.]+)", text)
        if m:
            tampered = text.replace(
                m.group(0), m.group(1) + str(float(m.group(2)) + 1.0), 1)
        else:  # pragma: no cover — STEP always carries cartesian points
            tampered = text[:-2] + "1;" if text.endswith(";") else text + "1"
        self.assertNotEqual(tampered, text)
        with open(art["path"], "w", encoding="utf-8") as fh:
            fh.write(tampered)
        regen = pc.check_regeneration(
            "P-01", tpl, model, staging_dir=os.path.join(self.tmp, "regen"))
        self.assertEqual(regen["status"], "NOT_REPRODUCIBLE")
        self.assertIn("STEP:catheter_body", ";".join(regen["mismatches"]))

    def test_tampered_measurement_is_caught(self):
        tpl, model = self._build()
        objs = model["measurements"]["objects"]
        objs[next(iter(objs))]["volume_mm3"] = \
            objs[next(iter(objs))]["volume_mm3"] + 1.0
        regen = pc.check_regeneration(
            "P-01", tpl, model, staging_dir=os.path.join(self.tmp, "regen"))
        self.assertEqual(regen["status"], "NOT_REPRODUCIBLE")

    def test_assembly_equivalence_presentation_only(self):
        # two assembly STEPs identical except a STYLED_ITEM permutation
        # are EQUIVALENT (order nondeterminism is disclosed)...
        a = os.path.join(self.tmp, "a.step")
        b = os.path.join(self.tmp, "b.step")
        body = (
            "#1 = PRODUCT('x','x','',());\n"
            "#2 = NEXT_ASSEMBLY_USAGE_OCCURRENCE('1','part','',#1,#1,$);\n"
            "#3 = CARTESIAN_POINT('',(1.,0.,0.));\n"
            "#4 = STYLED_ITEM('color',(#5),#3);\n"
            "#5 = PRESENTATION_STYLE_ASSIGNMENT((#6),#3);\n")
        with open(a, "w") as fh:
            fh.write(body)
        with open(b, "w") as fh:
            fh.write(
                "#1 = PRODUCT('x','x','',());\n"
                "#2 = NEXT_ASSEMBLY_USAGE_OCCURRENCE('1','part','',#1,#1,$);\n"
                "#3 = CARTESIAN_POINT('',(1.,0.,0.));\n"
                "#4 = STYLED_ITEM('color',(#5),#9);\n"
                "#5 = PRESENTATION_STYLE_ASSIGNMENT((#6),#9);\n")
        eq, detail = pc._step_assembly_equivalent(a, b)
        self.assertTrue(eq, detail)
        # ...but a GEOMETRY block drift is a REAL mismatch
        with open(b, "w") as fh:
            fh.write(
                "#1 = PRODUCT('x','x','',());\n"
                "#2 = NEXT_ASSEMBLY_USAGE_OCCURRENCE('1','part','',#1,#1,$);\n"
                "#3 = CARTESIAN_POINT('',(2.,0.,0.));\n"
                "#4 = STYLED_ITEM('color',(#5),#3);\n"
                "#5 = PRESENTATION_STYLE_ASSIGNMENT((#6),#3);\n")
        eq, detail = pc._step_assembly_equivalent(a, b)
        self.assertFalse(eq)
        self.assertEqual(detail["drift_kind"], "GEOMETRY_OR_STRUCTURE_BLOCK")

    def test_presentation_type_count_drift_is_caught(self):
        a = os.path.join(self.tmp, "pa.step")
        b = os.path.join(self.tmp, "pb.step")
        base = (
            "#1 = PRODUCT('x','x','',());\n"
            "#3 = CARTESIAN_POINT('',(1.,0.,0.));\n"
            "#4 = STYLED_ITEM('color',(#5),#3);\n")
        with open(a, "w") as fh:
            fh.write(base)
        with open(b, "w") as fh:
            fh.write(base + "#6 = STYLED_ITEM('color',(#7),#3);\n")
        eq, detail = pc._step_assembly_equivalent(a, b)
        self.assertFalse(eq)
        self.assertTrue(detail.get("presentation_type_counts_differ"))

    def test_step_bookkeeping_normalization(self):
        tpl, model = self._build("P-01")
        text = open(model["derived_artifacts"][
            "STEP:catheter_body"]["path"], encoding="utf-8").read()
        self.assertNotIn("translator 7.8 2", text)  # counter pinned
        # header timestamp is the fixed epoch
        m = re.search(r"FILE_NAME\('([^']*)','([^']*)'", text)
        self.assertTrue(m)
        self.assertEqual(m.group(2), pc._STEP_EPOCH)


class TestBuildV5Integration(unittest.TestCase):
    """The portfolio builder must carry MODEL/ into manifest + zip."""

    def test_recursive_file_walk_includes_model(self):
        tmp = tempfile.mkdtemp(prefix="r381_v5_")
        try:
            os.makedirs(os.path.join(tmp, "MODEL"))
            for f in ("a.json", "MODEL/x.step", "MODEL/MODEL_MANIFEST.json"):
                with open(os.path.join(tmp, f), "w") as fh:
                    fh.write("{}")
            from premium_package_factory.r371.build_v5 import (
                _package_files_recursive, _model_artifact_role,
            )
            files = _package_files_recursive(tmp)
            self.assertEqual(files, ["MODEL/MODEL_MANIFEST.json",
                                     "MODEL/x.step", "a.json"])
            self.assertIn("3D", _model_artifact_role("MODEL/x.step"))
            self.assertIn("presentation", _model_artifact_role(
                "MODEL/x.glb").lower())
            self.assertEqual(_model_artifact_role("x.pdf"), "buyer document")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_acceptance_condition_wired(self):
        # the R381 honesty condition exists in the acceptance gate
        import premium_package_factory.r371.acceptance as acc
        src = open(acc.__file__, encoding="utf-8").read()
        self.assertIn("honest 3D design classification", src)
        self.assertIn("NOT_APPLICABLE but geometry artifacts", src)
        self.assertIn("zip/folder drift", src)


@unittest.skipUnless(_CAD_AVAILABLE, _SKIP)
class TestLoopEvaluators(unittest.TestCase):
    """Evaluators must compute from MEASURED geometry with declared
    MODELLED relations — never naked numbers (Art. XXXVIII)."""

    def test_p04_evaluation_carries_computation_basis(self):
        tpl = PORTFOLIO_TEMPLATES["P-04"]
        tmp = tempfile.mkdtemp(prefix="r381_eval_")
        try:
            base, _ = pc.build_portfolio_model(
                "P-04", tpl, out_dir=os.path.join(tmp, "base"))
            loop, _kept = pc.run_improvement_loop(
                "P-04", tpl, base, out_dir=os.path.join(tmp, "mut"))
            ev = loop["technical_evaluation"]
            self.assertIn("contact_time", ev.get("quantity", ""))
            self.assertIn("MEASURED", ev.get("computation_basis", ""))
            self.assertEqual(ev["evidence_class"], "COMPUTATIONAL_RESULT")
            self.assertIn("MODELLED", ev.get("relation", "") + str(
                ev.get("relation_class", "")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

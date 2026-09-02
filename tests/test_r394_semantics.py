"""test_r394_semantics.py — R394 adversarial tests (CEO R392/R393
updated directive: truth, semantics, and the four hard release gates).

Every control has a NEGATIVE case that reproduces the original defect
class (Art. VIII: certification must attack itself; Art. XVII: every
control must have an attempted bypass):
  - the P-07 pressure-activated-switch-without-geometry defect
  - the decisive-experiment-by-list-position defect
  - the EQ-3 annotation-inside-math structural defect
  - the self-containment missing-reference defect
  - the 3D status blob (PRESENT_AND_VALIDATED) defect
  - the traceability-UNKNOWN-despite-canonical-identifiers defect
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

from premium_package_factory.r371.canonical_source import (  # noqa: E402
    load_all_packages, load_dossier)
from premium_package_factory.r371.equations import (  # noqa: E402
    split_annotation, build_equation_registry)
from premium_package_factory.r372.equation_validation import (  # noqa: E402
    validate_registry)
from premium_package_factory.r374.equation_status import (  # noqa: E402
    attach_r374_status)
from premium_package_factory.r394.canonical_corrections import (  # noqa: E402
    apply_v3_corrections, load_corrections)
from premium_package_factory.r394.decisive_experiment import (  # noqa: E402
    derive_decisive_work_package, content_tokens
)
from premium_package_factory.r394.release_gates import (  # noqa: E402
    gate_mechanism_geometry, gate_decisive_experiment,
    gate_self_containment, gate_equations_structural)
from premium_package_factory.r394.validation_states import (  # noqa: E402
    derive_validation_states, compact_epistemic_line)
from premium_package_factory.r394.evidence_classes import (  # noqa: E402
    build_mechanism_evidence
)
from premium_package_factory.r394 import traceability as r394_trace  # noqa: E402
from premium_package_factory.r372.traceability_semantics import (  # noqa: E402
    build_traceability_json
)

PKGS = load_all_packages()
P07 = next(p for p in PKGS if p.pkg_id == "P-07")
HEADLINES = json.load(open(os.path.join(
    os.path.dirname(__file__), "..", "premium_package_factory", "input",
    "headlines_r371.json"), encoding="utf-8"))["packages"]
HL = {x["package_id"]: x for x in HEADLINES}
DEPLOYED_P07 = ("/home/z/my-project/portfolio/DOWNLOAD/04_drainage_floor"
                if os.path.isdir("/home/z/my-project/portfolio/DOWNLOAD/"
                                "04_drainage_floor") else None)


class TestEquationSplitter(unittest.TestCase):
    """EQ-3 structural defect: annotation inside the math expression."""

    def test_eq3_both_annotations_stripped(self):
        math, ann, note = split_annotation(
            "G_total = G_primary + G_floor [parallel conductance] "
            "[P-07 parallel floor conductance — passive safety floor "
            "mechanism]")
        self.assertEqual(math, "G_total = G_primary + G_floor")
        self.assertIsNone(note)
        self.assertIn("parallel conductance", ann)

    def test_concentration_notation_preserved(self):
        # [S] is math, NOT an annotation (P-04 corpus case)
        math, ann, _ = split_annotation(
            "v = (Vmax * [S]) / (Km + [S]) [enzyme kinetics]")
        self.assertIn("[S]", math)
        self.assertEqual(ann, "enzyme kinetics")

    def test_interval_notation_preserved(self):
        # [0, t_critical] is a range, NOT an annotation (P-11 corpus case)
        math, ann, note = split_annotation(
            "k_detach > k_attach for t in [0, t_critical]")
        self.assertIn("[0, t_critical]", math)
        self.assertEqual(ann, "")

    def test_corrupted_string_verbatim(self):
        math, ann, note = split_annotation(
            "Q = f(x) corrupted tail with no bracket]")
        self.assertEqual(note, "CORRUPTED_CANONICAL_STRING_RENDERED_VERBATIM")
        self.assertEqual(ann, "")

    def test_p07_registry_math_clean(self):
        reg = build_equation_registry(P07)
        eq3 = [e for e in reg["equations"] if e["equation_id"] == "EQ-3"][0]
        self.assertEqual(eq3["math_expression"],
                         "G_total = G_primary + G_floor")

    def test_p07_dimensional_validation_all_levels(self):
        reg = build_equation_registry(P07)
        val = validate_registry(reg, P07)
        reg["r372_validation"] = val
        attach_r374_status(reg, P07)
        totals = reg["r374_validation_status"]["totals"]
        self.assertEqual(totals["equations"], 4)
        self.assertEqual(totals["structural_validated"], 4)
        self.assertEqual(totals["dimensionally_validated"], 4)
        # the three levels are SEPARATE — never one collapsed score
        for lv in reg["r374_validation_status"]["equations"]:
            self.assertIn("STRUCTURAL_VALIDATION", lv["levels_proven"])
            self.assertIn("DIMENSIONAL_VALIDATION", lv["levels_proven"])


class TestV3Corrections(unittest.TestCase):
    """The mechanism/CAD contradiction resolution (Option B)."""

    def test_corrections_apply(self):
        self.assertIsNotNone(P07.v3_trail)
        self.assertGreaterEqual(P07.v3_trail["operations_applied"], 8)
        ids = [s["id"] for s in
               P07.eng["system_architecture"]["subsystems"]]
        self.assertNotIn("SS-03", ids)  # pressure-activated switch removed

    def test_no_pressure_activation_language(self):
        sa = P07.eng["system_architecture"]
        text = json.dumps(sa) + json.dumps(
            P07.eng.get("mechanism_architecture", {}))
        # the only permitted mention is the explicit negation
        self.assertNotIn("opens via pressure-activated switch", text)
        self.assertNotIn("Differential pressure thresholds activate",
                         text)
        self.assertIn("permanently open", sa["description"].lower())

    def test_symbol_units_recorded(self):
        su = P07.gm.get("symbol_units") or {}
        for sym in ("Q", "r", "dP", "eta", "L", "G_total",
                    "G_primary", "G_floor", "Q_floor_min"):
            self.assertIn(sym, su, f"unit not recorded for {sym}")
            self.assertTrue(su[sym].get("unit"))
            self.assertTrue(su[sym].get("basis"))  # Art. VI: basis required

    def test_evidence_replaced_with_classified_records(self):
        eps = P07.eng["external_engineering_precedent"]
        self.assertGreaterEqual(len(eps), 8)
        for ep in eps:
            self.assertIn("classification", ep)
            self.assertIn(ep["classification"], (
                "BACKGROUND", "ANALOGY", "DIRECT_MECHANISM_EVIDENCE",
                "DIRECT_PRIOR_ART", "CONTRADICTORY_EVIDENCE"))
        classes = {ep["classification"] for ep in eps}
        self.assertIn("DIRECT_PRIOR_ART", classes)
        self.assertIn("DIRECT_MECHANISM_EVIDENCE", classes)
        # the adjacent-domain web content is gone from the rendered view
        sources = json.dumps(eps)
        self.assertNotIn("youtube.com", sources)
        self.assertNotIn("instagram.com", sources)

    def test_exact_match_fail_closed(self):
        # NEGATIVE CONTROL: a correction whose 'before' string is absent
        # must HARD-FAIL (Art. II — never fuzzy, never silent skip)
        dossier = load_dossier("P-07")
        bad = {"operations": [{
            "op": "replace_string",
            "path": "system_architecture.description",
            "before": "THIS STRING DOES NOT EXIST ANYWHERE",
            "after": "x",
        }]}
        with self.assertRaises(RuntimeError):
            apply_v3_corrections(dossier, bad)

    def test_export_file_untouched(self):
        # Art. XI: the R370Q export file itself stays byte-identical
        raw = load_dossier("P-07")  # raw loader, no corrections
        # the raw record still carries SS-03 (history preserved)
        ids = [s["id"] for s in raw["engineering_content"]
               ["system_architecture"]["subsystems"]]
        self.assertIn("SS-03", ids)


class TestDecisiveExperiment(unittest.TestCase):
    """The decisive experiment derives from the kill condition."""

    def test_p07_derives_wp04_not_wp01(self):
        d = derive_decisive_work_package(
            P07, HL["P-07"]["kill_if"])
        self.assertEqual(d["decisive_experiment_state"],
                         "DERIVED_FROM_KILL_CONDITION")
        self.assertEqual(d["work_package"], "WP-04")
        self.assertGreaterEqual(len(d["matched_tokens"]), 5)
        self.assertIn("obstruction", d["matched_tokens"])

    def test_list_position_never_wins(self):
        # NEGATIVE CONTROL: a plan whose WP-01 is FIRST but shares NO
        # kill-condition tokens must NOT be designated decisive
        class FakePkg:
            build_plan = [
                {"work_package": "WP-01",
                 "test_article": " Administrative bookkeeping audit ",
                 "measurement": " paperwork throughput ",
                 "acceptance_criterion": " forms filed correctly ",
                 "deliverable": " binder ", "estimated_effort": "1 weeks"},
                {"work_package": "WP-02",
                 "test_article": "Common-cause obstruction specimens",
                 "measurement": "differential obstruction of both lumens",
                 "acceptance_criterion": "floor obstructs differently",
                 "deliverable": "obstruction report",
                 "estimated_effort": "2 weeks"},
            ]
        d = derive_decisive_work_package(
            FakePkg(), "Common-cause obstruction of both lumens")
        self.assertEqual(d["work_package"], "WP-02")
        self.assertNotEqual(d["work_package"], "WP-01")

    def test_honest_not_derived(self):
        class FakePkg:
            build_plan = [
                {"work_package": "WP-01",
                 "test_article": " unrelated characterization samples ",
                 "measurement": " material purity ",
                 "acceptance_criterion": " purity meets spec ",
                 "deliverable": " certificate ", "estimated_effort":
                 "1 weeks"}]
        d = derive_decisive_work_package(
            FakePkg(), "Common-cause obstruction of both lumens")
        self.assertEqual(d["decisive_experiment_state"],
                         "DECISIVE_EXPERIMENT_NOT_DERIVED")
        self.assertIsNone(d.get("work_package"))


class TestReleaseGates(unittest.TestCase):

    def test_gate_mechanism_geometry_pass(self):
        if not DEPLOYED_P07:
            self.skipTest("deployed portfolio clone not present")
        g = gate_mechanism_geometry(P07, DEPLOYED_P07 + "/MODEL")
        self.assertEqual(g["state"], "PASS")

    def test_gate_mechanism_geometry_negative_control(self):
        # NEGATIVE CONTROL: reintroduce the pressure-activated switch
        # (the exact P-07 defect) -> the gate MUST fail
        import copy
        view = copy.deepcopy(P07.eng)
        view["system_architecture"]["subsystems"].append({
            "id": "SS-03", "name": "Pressure-activated switch",
            "function": "Mechanical switch that activates floor path "
                        "when dP exceeds threshold"})
        class FakePkg:
            eng = view
        if not DEPLOYED_P07:
            self.skipTest("deployed portfolio clone not present")
        g = gate_mechanism_geometry(FakePkg(), DEPLOYED_P07 + "/MODEL")
        self.assertEqual(g["state"], "FAIL")
        self.assertTrue(any("SS-03" in str(v) for v in g["violations"]))

    def test_gate_decisive_legacy_schema_fails(self):
        # NEGATIVE CONTROL: the R371 defect — designation by list
        # position (first_decisive_work_package key)
        eco = {"time_range": {"first_decisive_work_package": {
            "work_package": "WP-01", "recorded_effort": "10 weeks"}}}
        g = gate_decisive_experiment(
            eco, HL["P-07"]["kill_if"])
        self.assertEqual(g["state"], "FAIL")

    def test_gate_decisive_forged_tokens_fail(self):
        # NEGATIVE CONTROL: a DERIVED state whose matched tokens are not
        # in the kill condition (a forged/edited derivation)
        eco = {"time_range": {"decisive_work_package": {
            "decisive_experiment_state": "DERIVED_FROM_KILL_CONDITION",
            "work_package": "WP-04",
            "matched_tokens": ["banana", "pineapple"]}}}
        g = gate_decisive_experiment(eco, HL["P-07"]["kill_if"])
        self.assertEqual(g["state"], "FAIL")

    def test_gate_decisive_honest_not_derived_passes(self):
        eco = {"time_range": {"decisive_work_package": {
            "decisive_experiment_state": "DECISIVE_EXPERIMENT_NOT_DERIVED",
            "work_package": None}}}
        g = gate_decisive_experiment(eco, HL["P-07"]["kill_if"])
        self.assertEqual(g["state"], "PASS")

    def test_gate_decisive_p07_real(self):
        from premium_package_factory.r371.economics import \
            build_validation_economics
        eco = build_validation_economics(P07, HL["P-07"]["kill_if"])
        g = gate_decisive_experiment(eco, HL["P-07"]["kill_if"])
        self.assertEqual(g["state"], "PASS")
        self.assertEqual(g["decisive_work_package"], "WP-04")

    def test_gate_self_containment_missing_ref(self):
        # NEGATIVE CONTROL: a package referencing a file that is neither
        # inside nor pinned -> FAIL (the CEO's P-07 audit finding)
        with tempfile.TemporaryDirectory() as td:
            pkg = os.path.join(td, "pkg")
            os.makedirs(pkg)
            with open(os.path.join(pkg, "CERT.json"), "w") as f:
                json.dump({"evidence_basis":
                           "EXTERNAL_CONSULTANT_EVIDENCE/"
                           "MISSING_REPORT.json"}, f)
            g = gate_self_containment(pkg)
            self.assertEqual(g["state"], "FAIL")
            self.assertTrue(any("MISSING_REPORT" in str(v)
                                for v in g["violations"]))

    def test_gate_self_containment_sibling_resolution(self):
        # MODEL/MODEL_MANIFEST.json referencing "PARAMETERS.json" by bare
        # filename resolves as a sibling (not a violation)
        with tempfile.TemporaryDirectory() as td:
            pkg = os.path.join(td, "pkg")
            model = os.path.join(pkg, "MODEL")
            os.makedirs(model)
            with open(os.path.join(model, "PARAMETERS.json"), "w") as f:
                json.dump({"parameters": []}, f)
            with open(os.path.join(model, "MODEL_MANIFEST.json"), "w") as f:
                json.dump({"source_of_truth": "PARAMETERS.json"}, f)
            g = gate_self_containment(pkg)
            self.assertEqual(g["state"], "PASS")

    def test_gate_self_containment_external_reference(self):
        # CEO option 2: an immutable external reference with sha256
        with tempfile.TemporaryDirectory() as td:
            pkg = os.path.join(td, "pkg")
            os.makedirs(pkg)
            reg = os.path.join(td, "PORTFOLIO_IDENTITY_REGISTRY.json")
            with open(reg, "w") as f:
                f.write("{}")
            manifest = {"external_references": {
                "PORTFOLIO_IDENTITY_REGISTRY.json": {
                    "sha256": "deadbeef", "location": "portfolio root"}}}
            with open(os.path.join(
                    pkg, "PACKAGE_MANIFEST.json"), "w") as f:
                json.dump(manifest, f)
            with open(os.path.join(pkg, "DOC.json"), "w") as f:
                json.dump({"identity_policy":
                           "bound in PORTFOLIO_IDENTITY_REGISTRY.json"},
                          f)
            g = gate_self_containment(pkg)
            self.assertEqual(g["state"], "PASS")

    def test_gate_equations_structural_negative(self):
        # NEGATIVE CONTROL: a corrupted equation string
        reg = {"equations": [{
            "equation_id": "EQ-9",
            "rendering_note":
                "CORRUPTED_CANONICAL_STRING_RENDERED_VERBATIM",
            "math_expression": "x = y corrupted tail]"}]}
        g = gate_equations_structural(reg)
        self.assertEqual(g["state"], "FAIL")

    def test_gate_equations_structural_unproven_parse(self):
        # NEGATIVE CONTROL: r374 says structural NOT proven
        reg = {"equations": [{"equation_id": "EQ-8",
                              "math_expression": "x = y"}],
               "r374_validation_status": {"equations": [{
                   "equation_id": "EQ-8",
                   "structural_validation": {
                       "proven": False,
                       "basis": "parse failed"}}]}}
        g = gate_equations_structural(reg)
        self.assertEqual(g["state"], "FAIL")

    def test_gate_equations_structural_p07(self):
        reg = build_equation_registry(P07)
        val = validate_registry(reg, P07)
        reg["r372_validation"] = val
        attach_r374_status(reg, P07)
        g = gate_equations_structural(reg)
        self.assertEqual(g["state"], "PASS")


class TestValidationStates(unittest.TestCase):
    """The 3D/engineering validation state split (no blob)."""

    def _states(self):
        reg = build_equation_registry(P07)
        val = validate_registry(reg, P07)
        reg["r372_validation"] = val
        attach_r374_status(reg, P07)
        if not DEPLOYED_P07:
            self.skipTest("deployed portfolio clone not present")
        return derive_validation_states(
            P07, DEPLOYED_P07 + "/MODEL", reg, {})

    def test_split_states(self):
        vs = self._states()
        self.assertIs(vs["cad_present"]["state"], True)
        self.assertIs(vs["cad_validated"]["state"], True)
        self.assertIs(vs["mechanism_geometry_present"]["state"], True)
        # P-07 with all 4 equations dimensionally validated
        self.assertIs(vs["engineering_model_validated"]["state"], True)
        # the physical layer NEVER promotes from computation (Art. XXXVIII)
        self.assertIs(vs["bench_tested"]["state"], False)
        self.assertIs(vs["physically_validated"]["state"], False)
        self.assertIs(vs["clinically_validated"]["state"], False)
        self.assertEqual(vs["regulatory_status"]["state"],
                         "NOT_ESTABLISHED")

    def test_compact_line(self):
        vs = self._states()
        line = compact_epistemic_line(vs)
        self.assertIn("COMPUTATIONALLY PROPOSED", line)
        self.assertIn("CAD VALIDATED", line)
        self.assertIn("PHYSICAL VALIDATION PENDING", line)

    def test_engineering_model_not_promoted_when_one_unproven(self):
        # NEGATIVE CONTROL: one unproven equation keeps the state FALSE
        reg = build_equation_registry(P07)
        reg["r374_validation_status"] = {
            "totals": {"equations": 4, "dimensionally_validated": 3}}
        from premium_package_factory.r394.validation_states import \
            engineering_model_validated
        self.assertIs(
            engineering_model_validated(reg)["state"], False)


class TestTraceability(unittest.TestCase):

    def test_p07_identifier_bindings(self):
        trace = build_traceability_json(P07)
        before = trace["summary"]["explicitly_linked"]
        self.assertEqual(before, 0)  # the R372 honest baseline
        trace = r394_trace.attach(P07, trace)
        after = trace["summary"]["explicitly_linked"]
        self.assertGreaterEqual(after, 6)
        self.assertEqual(trace["release_gate"]["traceability_state"],
                         "TRACEABILITY_PARTIAL")
        # the chain slots the CEO specified are present
        chain = trace["chains"][0]
        for slot in ("mechanism_feature", "geometry_parameter",
                     "failure_mode", "verification", "experiment",
                     "expected_observation", "decision"):
            self.assertIn(slot, chain["slots"])

    def test_unknown_stays_unknown_without_link(self):
        # DI-003 (flow regime: "Laminar, Re << 2300") shares no canonical
        # identifier with any FM/V/WP — its slots must stay UNKNOWN
        trace = r394_trace.attach(
            P07, build_traceability_json(P07))
        di3 = next(c for c in trace["chains"]
                   if c["design_input_id"] == "DI-003")
        self.assertEqual(di3["chain_state"], "TRACEABILITY_UNKNOWN")

    def test_binding_evidence_names_identifiers(self):
        # every EXPLICIT slot carries evidence naming the shared
        # identifier or phrase (auditable — Art. XII)
        trace = r394_trace.attach(
            P07, build_traceability_json(P07))
        for chain in trace["chains"]:
            for slot in chain["slots"].values():
                if slot.get("state") == "EXPLICIT":
                    self.assertTrue(slot.get("evidence"))


class TestMechanismEvidence(unittest.TestCase):

    def test_four_questions_record(self):
        st = json.load(open(os.path.join(
            os.path.dirname(__file__), "..", "premium_package_factory",
            "input", "v3_corrections",
            "P-07_MECHANISM_EVIDENCE_STATEMENTS.json"),
            encoding="utf-8"))
        me = build_mechanism_evidence(P07, st)
        for q in ("what_is_already_known", "what_is_different",
                  "why_the_difference_matters",
                  "what_evidence_supports_it", "what_remains_unknown"):
            self.assertTrue(me[q], f"{q} missing")
        # no novelty conclusion anywhere
        blob = json.dumps(me).lower()
        self.assertNotIn("novel", blob.replace("novelty determination", "")
                         .replace("no novelty", ""))
        self.assertGreaterEqual(me["counts"]["DIRECT_PRIOR_ART"], 1)
        self.assertGreaterEqual(me["counts"]["DIRECT_MECHANISM_EVIDENCE"], 4)

    def test_degrades_without_statements(self):
        me = build_mechanism_evidence(P07, None)
        self.assertIsNone(me["what_is_different"])


class TestEvidenceRetrieval(unittest.TestCase):
    """The R394 real-evidence retrieval record (Art. XXI discipline)."""

    REC = ("/home/z/my-project/discovery-evidence-fabric/R394/"
           "p07_evidence/P07_MECHANISM_EVIDENCE.json")

    def test_retrieval_record_exists(self):
        if not os.path.exists(self.REC):
            self.skipTest("retrieval record not present")
        rec = json.load(open(self.REC, encoding="utf-8"))
        self.assertEqual(rec["failures"], [])
        self.assertGreaterEqual(rec["deduplicated"], 60)
        # provider failures never masquerade as absence (Art. XXI.3)
        self.assertIn("classification_rule", rec)


if __name__ == "__main__":
    unittest.main(verbosity=2)

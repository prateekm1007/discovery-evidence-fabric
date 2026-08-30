"""render_fixtures.py — R375-7 permanent worst-case regression fixtures.

Five synthetic worst-case packages, each stressing exactly the render
defect class the CEO named (2026-08-30 directive, item 7):

  FX1 worst-case long design input        (2,600-char authoritative value)
  FX2 worst-case mutation                 (1,900-char V2 correction text)
  FX3 worst-case unknown                  (1,500-char verbatim unknown
                                           + 1,200-char resolution action)
  FX4 worst-case experiment box           (60 control variables -> diagram
                                           reflow/split under the one-page
                                           aspect budget)
  FX5 worst-case equation                 (long mathtext + a 240-char
                                           unbroken canonical token)

Every fixture renders through the REAL production renderers (no mocks,
no special-casing), then must pass GEOMETRIC_QA + RENDERED_PAGE_QA and
must contain its full authoritative strings in the PDF text layer
(content completeness). A fixture PDF that renders "clean" only by
truncating FAILS the completeness check — the two instruments jointly
pin honest rendering (Art. VIII: the suite attacks the renderer).

The fixtures are deterministic (fixed seeds/strings) so a regression is
a byte-level event.
"""
from __future__ import annotations

import json
import os

from ..r371.builder import get_styles
from ..r371 import builder_documents as bd
from ..r371 import builder_dossier as bdd
from ..r371.builder_portfolio import init_styles


class FixturePkg:
    """Duck-typed stand-in for CanonicalPackage with worst-case fields."""

    def __init__(self, pkg_id, num, **over):
        self.num = num
        self.pkg_id = pkg_id
        self.short = "fixture"
        self.folder = f"{num}_fixture_{pkg_id.lower()}"
        self.version = "2.0"
        self.loop_state = "NONE"
        self.addendum = over.get("addendum")
        self.eng = over.get("eng", {})
        self.core = over.get("core", {})
        self.gm = self.core.get("governing_model", {})
        self.dossier = {}
        self._roadmap_override = over.get("_roadmap_override")

    @property
    def identity_line(self):
        return (f"Portfolio {self.num} of 15 - Package {self.pkg_id} - "
                f"Version {self.version}")

    @property
    def technology_name(self):
        return self.eng.get("technology_name", "Worst-Case Fixture")

    @property
    def domain(self):
        return self.eng.get("technology_domain", "FIXTURE")

    @property
    def equations(self):
        return self.gm.get("equations", [])

    @property
    def unknowns(self):
        return self.core.get("remaining_unknowns", [])

    @property
    def design_inputs(self):
        return self.eng.get("design_inputs", [])

    @property
    def design_outputs(self):
        return self.eng.get("design_outputs", [])

    @property
    def failure_analysis(self):
        return self.eng.get("failure_analysis", [])

    @property
    def build_plan(self):
        return self.eng.get("engineering_build_plan", [])

    @property
    def external_precedent(self):
        return self.eng.get("external_engineering_precedent", [])

    @property
    def verification(self):
        return self.core.get("verification", [])

    @property
    def validation(self):
        return self.core.get("validation", [])

    @property
    def critical_parameters(self):
        return self.core.get("critical_parameters", [])

    @property
    def transfer_boundary(self):
        return self.eng.get("transfer_boundary", {})

    @property
    def proposed_design(self):
        return self.core.get("proposed_design", {})

    @property
    def claims(self):
        return []


_LONG_TEXT = ("The recorded engineering basis establishes that the "
              "conductive lumen segment must maintain patency under a "
              "quantified occlusion spectrum spanning fibrin deposition, "
              "cellular adhesion and protein fouling regimes, each with a "
              "measured onset horizon and a recorded uncertainty band "
              "carried verbatim from the canonical engineering register. ")

_CTRL_VARS_60 = "; ".join(
    f"CV-{i:02d} pressure_boundary_{i:02d}="
    f"{3.0 + i * 0.137:.3f} mmHg MODELLED band ±{0.2 + i * 0.011:.3f}"
    for i in range(1, 61))


def _base_eng():
    return {
        "technology_name": "Worst-Case Render Fixture",
        "technology_domain": "FIXTURE_DOMAIN",
        "design_inputs": [],
        "design_outputs": [],
        "failure_analysis": [],
        "engineering_build_plan": [],
        "external_engineering_precedent": [],
        "transfer_boundary": {
            "buyer_receives": ["Complete engineering definition"],
            "buyer_must_create": ["Physical prototype", "Validation run"],
        },
    }


def _base_core():
    return {
        "governing_model": {"equations": [], "summary": ""},
        "remaining_unknowns": [],
        "verification": [],
        "validation": [],
        "critical_parameters": [],
    }


def fx1_long_design_input():
    value = _LONG_TEXT * 8          # ~2,600 chars, no sentence-boundary luck
    eng = _base_eng()
    eng["design_inputs"] = [
        {"id": "DI-FX1-01", "input": "Occlusion spectrum envelope",
         "value": value},
        {"id": "DI-FX1-02", "input": "second row with µ and × glyphs",
         "value": "µW × mmHg × 10^3 recorded basis " + _LONG_TEXT * 3},
    ]
    return FixturePkg("P-FX1", "90", eng=eng, core=_base_core())


def fx2_worst_mutation():
    v2_text = ("Corrected therapeutic envelope after external evidence "
               "capture: " + _LONG_TEXT * 6)
    addendum = {
        "v2_version": "2.0",
        "mutations": [{
            "mutation_id": "MUT-FX2-01",
            "field_affected": "governing_model.summary",
            "v1_text": "original summary",
            "v2_text": v2_text,
            "reason": "External source capture contradicted the recorded "
                      "envelope. " + _LONG_TEXT * 2,
            "evidence_basis": ["FX-SRC-1 hashed capture"],
        }],
    }
    return FixturePkg("P-FX2", "91", eng=_base_eng(), core=_base_core(),
                      addendum=addendum)


def fx3_worst_unknown():
    core = _base_core()
    stmt = ("UNKNOWN (verbatim, worst case): the long-term interaction "
            "between the recorded coating chemistry and the deployed "
            "ionic environment is not characterized anywhere in the "
            "captured sources. " + _LONG_TEXT * 4)
    action = ("Resolve by ISO 10993-1 styled extraction study with a "
              "recorded acceptance threshold and a documented negative "
              "control. " + _LONG_TEXT * 3)
    core["remaining_unknowns"] = [stmt[:1200] + " CRITICAL"]
    return FixturePkg(
        "P-FX3", "92", eng=_base_eng(), core=core,
        _roadmap_override={"unknowns": [{
            "unknown_id": "U-FX3-01",
            "unknown_statement": stmt[:1500],
            "classification": "MATERIAL_COMPATIBILITY",
            "resolution_action": action[:1200],
            "is_critical": True,
        }]})


def fx4_worst_experiment_box():
    eng = _base_eng()
    eng["engineering_build_plan"] = [{
        "work_package": "WP-01",
        "test_article": "Full occlusion-spectrum fixture assembly",
        "measurement": "Recorded pressure delta across the fixture",
        "equipment": "Bench loop, transducer bank, data capture",
        "acceptance_criterion": "Delta within recorded band",
        "estimated_effort": "3 weeks",
    }]
    core = _base_core()
    core["verification"] = [{
        "id": "V-001",
        "requirement": "Fixture survives occlusion spectrum",
        "method": "Apply the recorded spectrum",
        "acceptance": "No excursion beyond band",
        "result": "NOT_TESTED",
    }]
    core["critical_parameters"] = [
        {"name": f"cv{i:02d}", "value": f"{3.0 + i * 0.137:.3f}",
         "unit": "mmHg", "basis": "MODELLED", "status": "MODELLED",
         "verification_requirement": "bench verify"}
        for i in range(1, 61)]
    return FixturePkg("P-FX4", "93", eng=eng, core=core)


def fx5_worst_equation():
    core = _base_core()
    core["governing_model"] = {
        "summary": "Fixture governing model with pathological equations.",
        "equations": [
            "Q = A_c * sqrt(2 * dP / rho)",
            ("dP_total = dP_proximal + dP_distal + dP_valve + "
             + "x" * 240 +
             " + unbroken_token_regression_probe_0123456789"),
        ],
    }
    return FixturePkg("P-FX5", "94", eng=_base_eng(), core=core)


def headline_for(pkg):
    return {
        "package_id": pkg.pkg_id,
        "technology_name": "Worst-Case Render Fixture",
        "mechanism": "Fixture mechanism for worst-case render regression.",
        "problem": "Fixture problem statement.",
        "kill_if": ("Fixture kill condition: excursion beyond the recorded "
                    "band under the decisive experiment."),
    }


def roadmap_for(pkg):
    ov = getattr(pkg, "_roadmap_override", None)
    if ov:
        return {"unknown_count_roadmap": len(ov["unknowns"]),
                "classification_counts": {"MATERIAL_COMPATIBILITY": 1},
                "unknowns": ov["unknowns"]}
    return {"unknown_count_roadmap": 0, "classification_counts": {},
            "unknowns": []}


def fixture_pdf(pkg, out_path):
    """Render the worst-case fixture through the REAL production
    renderers; returns out_path. Raises on any QA-relevant failure."""
    import tempfile
    styles = get_styles()
    init_styles(styles)
    bdd.init_styles(styles)
    h = headline_for(pkg)
    with tempfile.TemporaryDirectory() as td:
        eq_registry = {
            "model_summary": "fixture",
            "equations": [
                {"equation_id": f"EQ-{i}", "equation_canonical": eq,
                 "typeset": None if len(eq) > 90 else "$" + eq + "$",
                 "math_expression": eq, "rendering_note": "fixture",
                 "caption": None, "variables": [], "applicability": [],
                 "assumptions": []}
                for i, eq in enumerate(pkg.equations, 1)
            ],
        }
        comm = {"commercial_evidence": []}
        eco = {"cost_range": {"value": "NOT_ESTABLISHED", "basis": "fixture"},
               "time_range": {
                   "first_decisive_work_package": {"recorded_effort": "3 wk"},
                   "full_build_plan": {"low_weeks": 3, "high_weeks": 6},
                   "basis": "fixture"},
               "expected_decision": {"decision": "FIXTURE",
                                     "acceptance_criterion": "fixture"}}
        loop = {"evidence_class_counts": {"UNKNOWN": 1}}
        bdd.render_engineering_dossier(
            pkg, h, eq_registry, roadmap_for(pkg), comm, eco, loop,
            mech_png=None, exp_pngs=[], out_path=out_path)
        # the evidence summary carries the full mutation trail (reason)
        # exactly as the real 6-PDF package does
        bd.render_evidence_summary(
            pkg, h, loop,
            os.path.splitext(out_path)[0] + "_evidence.pdf")
    return out_path


def _fixture_expectations(pkg):
    """Authoritative strings each fixture PDF must contain IN FULL."""
    exp = []
    h = headline_for(pkg)
    exp.append(("headline.kill_if", h["kill_if"]))
    for di in pkg.design_inputs:
        if di.get("value"):
            exp.append((f"DI.{di.get('id')}", di["value"]))
    for m in (pkg.addendum or {}).get("mutations", []):
        exp.append((f"mut.{m['mutation_id']}.v2_text", m["v2_text"]))
        exp.append((f"mut.{m['mutation_id']}.reason", m["reason"]))
    for u in roadmap_for(pkg).get("unknowns", []):
        exp.append((f"unknown.{u['unknown_id']}.statement",
                    u["unknown_statement"]))
        exp.append((f"unknown.{u['unknown_id']}.action",
                    u["resolution_action"]))
    for eq in pkg.equations:
        if len(eq) > 60:
            exp.append((f"equation.long_token", eq))
    return exp


def build_all_fixtures(out_dir) -> dict:
    """Render every worst-case fixture PDF + PNG renders into out_dir.
    Verifies GEOMETRIC_QA + RENDERED_PAGE_QA + content completeness.
    Returns manifest {fixture: {pdf, pages}}."""
    from ..gates.render_verification import (
        content_completeness, geometric_qa, pdf_haystacks, rendered_page_qa)
    os.makedirs(out_dir, exist_ok=True)
    fixtures = {
        "FX1_long_design_input": fx1_long_design_input(),
        "FX2_worst_mutation": fx2_worst_mutation(),
        "FX3_worst_unknown": fx3_worst_unknown(),
        "FX4_worst_experiment_box": fx4_worst_experiment_box(),
        "FX5_worst_equation": fx5_worst_equation(),
    }
    manifest = {}
    for name, pkg in fixtures.items():
        pdf = os.path.join(out_dir, f"{name}.pdf")
        fixture_pdf(pkg, pdf)
        geo = geometric_qa(pdf)
        rendered = rendered_page_qa(pdf, png_dir=os.path.join(out_dir, name))
        ev_pdf = os.path.splitext(pdf)[0] + "_evidence.pdf"
        geometric_qa(ev_pdf)
        rendered_page_qa(ev_pdf,
                         png_dir=os.path.join(out_dir, name + "_ev"))
        streams = pdf_haystacks(pdf) + pdf_haystacks(ev_pdf)
        exp = _fixture_expectations(pkg)
        ok, failures = content_completeness(exp, streams)
        if not ok:
            raise RuntimeError(
                f"fixture {name} content completeness FAILED: "
                + "; ".join(f"{f['field']} ({f['expected_head'][:50]!r})"
                            for f in failures[:5]))
        manifest[name] = {
            "pdf": pdf,
            "geometric": geo,
            "rendered": {k: v for k, v in rendered.items() if k != "pages"},
            "pages": rendered["pages"],
            "content_completeness": {"expected": len(exp), "missing": 0},
        }
    with open(os.path.join(out_dir, "FIXTURE_MANIFEST.json"), "w",
              encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    return manifest

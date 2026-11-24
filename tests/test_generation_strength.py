"""R144 generation-strength tests (R143-F6/F7).

Pins the V110 finding as regressions: the four DOCUMENTED v16
off-target examples are typed rejections; the strength kit's formulas
compute with units; the novelty gate separates strong from generic;
the DIR-8 lever is importable (the import-graph evidence).
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.generation import mechanism_map as mm  # noqa: E402
from discovery_fabric.generation import quant_test as qt    # noqa: E402
from discovery_fabric.generation import novelty_gate as ng  # noqa: E402
from discovery_fabric.generation import inspiration_retrieval as ir  # noqa: E402


def test_documented_off_target_examples_are_rejected():
    # the four documented R143-F7 examples (V110), verbatim intent
    off, why = mm.check_off_target(
        "abrasion_erosion", "cathodic protection with sacrificial anodes")
    assert off and "ELECTROCHEMICAL" in why
    off, _ = mm.check_off_target(
        "contamination_separation",
        "modulate the flow rate to reduce tramp metal damage")
    assert off, "flow modulation must be rejected for separation"
    off, _ = mm.check_off_target(
        "nucleation_phase_change",
        "add passive insulation to stabilize the nucleation")
    assert off, "insulation must be rejected for nucleation"
    off, _ = mm.check_off_target(
        "nucleation_phase_change",
        "install additional sensors for monitoring the onset")
    assert off, "monitoring must be rejected where mitigation is asked"


def test_classification_maps_the_failure_physics():
    cases = [
        ("Rain droplets erode the leading edge of the turbine blades "
         "at high impact velocity", "abrasion_erosion"),
        ("Tramp metal enters the crusher and damages the liners",
         "contamination_separation"),
        ("Boiling becomes unstable due to stochastic bubble nucleation "
         "bursts", "nucleation_phase_change"),
        ("The condenser tubes foul with biofilm and scale, dropping "
         "heat transfer", "fouling_deposition"),
        ("Galvanic pitting corrosion consumes the seawater piping",
         "corrosion_chemical"),
    ]
    for text, want in cases:
        s = mm.classify_failure(text)
        assert s.failure_class == want, f"{text[:40]} -> {s.failure_class}"
        assert s.confidence > 0.5
        assert s.evidence_span


def test_every_failure_class_has_coupled_mechanisms():
    for fc in mm.FAILURE_CLASSES:
        assert fc in mm.MECHANISM_MAP, f"{fc} has no mechanism classes"
        assert len(mm.MECHANISM_MAP[fc]) >= 3, f"{fc} has too few"
        for e in mm.MECHANISM_MAP[fc]:
            assert e["why"] and e["cross_domain"]


def test_quant_formulas_compute_with_units():
    p = qt.emit_prediction("surface_hardening_treatment",
                           {"hardness_before_Hv": 200.0,
                            "hardness_after_Hv": 400.0})
    assert p["status"] == "computed" and p["delta_pct"] == 50.0
    assert "falsifier" in p and "%" in p["falsifier"]
    p2 = qt.emit_prediction("density_settling_separation",
                            {"rho_p": 7800.0, "rho_f": 1000.0,
                             "d": 5e-4, "mu": 1e-3})
    assert p2["status"] == "computed" and "mm/s" in p2["predicted_value"]
    p3 = qt.emit_prediction("magnetic_gradient_separation",
                            {"chi": 0.05, "B": 1.0, "gradB": 10.0,
                             "V": 1e-9, "rho_p": 7800.0})
    assert p3["status"] == "computed"
    assert float(p3["predicted_value"].split()[0]) > 1, \
        "a steel particle in 10 T/m must separate"
    p4 = qt.emit_prediction("nucleation_inhibitor_dosing",
                            {"T_supercool_K": 38.15})
    assert p4["status"] == "computed"
    assert "e+" in p4["predicted_value"]  # at the anchor, J ~ 1e25
    p5 = qt.emit_prediction("nucleation_inhibitor_dosing",
                            {"T_supercool_K": 8.0})
    assert p5["status"] == "computed"
    assert float(p5["predicted_value"].split("=")[1].split()[0]) < 1e-6, \
        "at 8 K supercooling the homogeneous rate is ~0 (the anchor " \
        "physics); the intervention must CREATE the onset"
    p6 = qt.emit_prediction("compliant_elastomer_coating",
                            {"v_impact": 300.0})
    assert p6["status"] == "computed"
    assert "relative" in p6["predicted_value"]


def test_quant_typed_failures_never_silent():
    p = qt.emit_prediction("not_a_mechanism", {})
    assert p["status"] == "no_formula_for_class"
    p2 = qt.emit_prediction("surface_hardening_treatment",
                            {"hardness_before_Hv": 500.0,
                             "hardness_after_Hv": 300.0})
    assert p2["status"] == "insufficient_parameters"


def test_novelty_gate_separates_strong_from_generic():
    weak = ng.score_novelty(
        "Install additional sensors for monitoring the flow.", "", "")
    assert weak["novelty"] == "weak" and weak["reject"]
    weak2 = ng.score_novelty(
        "Increase the coolant flow to reduce the hot spot.", "", "")
    assert weak2["novelty"] == "weak" and weak2["reject"]
    strong = ng.score_novelty(
        "A compliant elastomer coating absorbs the droplet impact "
        "stress peak; coupon mass-loss drops >=40% within 500 h; "
        "falsified if the reduction is smaller.",
        "compliant_elastomer_coating", "rotor rain-erosion boots")
    assert strong["novelty"] == "strong", strong
    blind = ng.score_novelty(
        "A compliant elastomer coating absorbs the droplet impact "
        "stress peak; coupon mass-loss drops >=40% within 500 h.",
        "", "")
    assert blind["novelty"] == "weak" and blind["reject"], \
        "a candidate with NO mapped mechanism class is the retired " \
        "blind-operator path (R143-F6) even if the prose sounds strong"


def test_inspiration_retrieval_typed_and_hashed():
    insp = ir.retrieve_inspiration("abrasion_erosion")
    assert len(insp["analogies"]) >= 2
    for a in insp["analogies"]:
        assert a["precedent"] and a["transfer"] and a["from_domain"]
    empty = ir.retrieve_inspiration("abrasion_erosion", "no/such/file.txt")
    assert empty["evidence_spans"] == []  # typed empty, never invented
    block = ir.inspiration_prompt_block(insp)
    assert "INSPIRATION CONTEXT" in block


def test_selection_full_path():
    prob = ("Rain droplets at 300 m/s erode the composite leading edge; "
            "the abrasion must be mitigated")
    sel = mm.select_mechanism(prob)
    assert sel.failure_class == "abrasion_erosion"
    assert "compliant_elastomer_coating" in sel.allowed_mech_classes
    block = mm.mechanism_prompt_block(prob)
    assert "FAILURE-MODE MAPPING" in block
    assert "FORBIDDEN" in block
    assert "cathodic" in block  # the documented rejection is surfaced

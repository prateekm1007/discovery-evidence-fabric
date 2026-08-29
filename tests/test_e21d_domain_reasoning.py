"""tests/test_e21d_domain_reasoning.py — E21-D: mechanism-driven domain
reasoning (CEO brief item 2).

ADVERSARIAL TEST DESIGN (Art. VIII/V/XVII — the certification attacks
itself):

  NEGATIVE CONTROLS on the MEASURED DEFECTS: the two domain mis-routes
  frozen in the E21-C semantic-causal audit (BENCH_11 thermal invention
  routed mechanical_structural via the polysemous 'steer' of 'current
  steering'; BENCH_12 harvesting invention routed acoustic via
  'piezoelectric' while energy_harvesting bigrams missed the word order
  "harvests ... energy"). The phenomena layer must route both correctly.

  SCOPE DISCLOSURE (measured this session, beyond the two frozen
  defects): the OLD keyword router mis-routed 9 of the 15 benchmark
  inventions (systematic fluidics default via generic shunt/valve/flow
  device vocabulary). The phenomena layer repairs 8 (BENCH_05/06/07/08/
  10/11/12/14 — each now matching BOTH the invention's own stated
  physics AND the benchmark's declared domain). BENCH_15 remains on the
  ROUTING_ONLY path BY DESIGN: its mechanism states mechanical FUNCTION
  ("detent resists repositioning") with no mechanical QUANTITIES, and no
  registry domain's governing models cover magnetic-force-on-detent
  physics — the weaker justification is recorded, never dressed as
  physics reasoning (Art. XXV/XXVII).

  MUTATION CONTROLS: removing the thermal anchors from the BENCH_11 text
  must eliminate thermal phenomena dominance (sensitivity to physics,
  not fixture shape); a routing-only text must stay ROUTING_ONLY.

  ANTI-DRIFT PINS: PHENOMENA_ANCHORS must contain no polysemous
  technique/device words (the exact failure mode of the old router);
  the CEO item 2 record field-set must be present on every detection
  record; the artifact-level integration must carry the full layered
  reasoning into domain_detection.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from discovery_fabric.engine.domain_reasoning import (  # noqa: E402
    PHENOMENA_ANCHORS, detect_domain_reasoned, phenomena_layer)
from discovery_fabric.engine.domains import detect_domain  # noqa: E402

# E21-C reference run set (gitignored local fixtures, regenerable via
# scripts/e21_chunked_bench.py; same convention as the e21 series).
E21_RUNS = Path("/home/z/my-project/scripts/e21_runs")
HAS_RUNS = (E21_RUNS / "BENCH_01" / "INVENTION_SPECIFICATION.json").exists()

# --- the two frozen-measured defects, as text ----------------------------
BENCH11_MECH = ("spreads dissipation across a larger electrode area "
                "reducing peak tissue temperature; Joule heating in the "
                "electrode-tissue interface")
BENCH11_WRAPPER = ("electrode heating damages surrounding tissue; keep "
                   "local temperature rise below safety margin; current "
                   "steering electrodes")
BENCH12_MECH = ("harvests arterial pulsation energy through a "
                "piezoelectric transducer achieving net positive energy "
                "balance for the implant")
BENCH12_WRAPPER = "insufficient battery energy for chronic implants"

# --- scope-disclosure shifts (measured this session) --------------------
BENCH06_MECH = ("Phase-contrast MR signal across a fixed local gradient "
                "encodes flow velocity, enabled by an MR-visible flow "
                "encoding insert in the catheter wall")


# ------------------------------------------------- frozen defect controls
def test_e21d_bench11_defect_thermal_not_mechanical():
    """Frozen R-02-era mis-route: a Joule-heating/tissue-temperature
    invention MUST route thermal even though 'current steering' supplies
    the mechanical routing keyword 'steer'."""
    old = detect_domain(BENCH11_MECH + " " + BENCH11_WRAPPER)["domain"]
    assert old == "mechanical_structural"  # the defect, reproduced
    new = detect_domain_reasoned(BENCH11_MECH, BENCH11_WRAPPER)
    assert new["domain"] == "thermal"
    assert new["selection_basis"] == "PHENOMENA_DOMINANT"
    assert "temperatur" in new["phenomena_layer"]["thermal"]
    # the polysemous routing keyword is recorded but did not decide
    mech_routing = new["routing_layer"]["mechanism"]
    assert "mechanical_structural" not in mech_routing or \
        "steer" in mech_routing["mechanical_structural"]


def test_e21d_bench12_defect_harvesting_not_acoustic():
    """Frozen mis-route: word-order-brittle bigrams ('energy harvest')
    missed 'harvests ... energy'; the phenomena stem 'harvest' matches
    inflections and the invention MUST route energy_harvesting even
    though 'piezoelectric' supplies the acoustic routing keyword."""
    old = detect_domain(BENCH12_MECH + " " + BENCH12_WRAPPER)["domain"]
    assert old == "acoustic"  # the defect, reproduced
    new = detect_domain_reasoned(BENCH12_MECH, BENCH12_WRAPPER)
    assert new["domain"] == "energy_harvesting"
    assert new["selection_basis"] == "PHENOMENA_DOMINANT"


# ------------------------------------------------------- layer dominance
def test_e21d_phenomena_dominate_conflicting_routing():
    """When routing keywords point one way and stated physics another,
    physics decides (CEO item 2: keywords route, never justify)."""
    text = ("the implant dissipates heat and controls peak tissue "
            "temperature via a piezoelectric steering transducer")
    new = detect_domain_reasoned(text, "")
    assert new["domain"] == "thermal"
    assert new["selection_basis"] == "PHENOMENA_DOMINANT"


def test_e21d_mri_abbreviation_anchors():
    """Scope-fix: 'Phase-contrast MR signal' / 'MR-visible' / 'local
    gradient that encodes flow velocity' are genuine MR physics (the
    encoding the Larmor/gradient models govern); the spelled-out
    'magnetic resonance' anchor alone could not match them (BENCH_06)."""
    new = detect_domain_reasoned(BENCH06_MECH, "")
    assert new["domain"] == "mri_nmr"
    assert new["selection_basis"] == "PHENOMENA_DOMINANT"
    hits = new["phenomena_layer"]["mri_nmr"]
    assert any("MR" in h for h in hits) or "phase-contrast" in hits


# ------------------------------------------------------------ fallbacks
def test_e21d_routing_only_fallback_recorded_as_such():
    """Routing keywords with NO physics evidence: the old behavior is
    preserved but the record must SAY the selection is keyword-routing
    only — the weaker justification disclosed, never dressed up."""
    new = detect_domain_reasoned("a steerable catheter tip with "
                                 "articulation joints", "")
    assert new["selection_basis"] == "ROUTING_ONLY"
    assert "ROUTING ONLY" in new["why_selected"]
    assert new["phenomena_layer"] == {}
    assert new["domain"] == "mechanical_structural"  # routing result


def test_e21d_no_evidence_unknown_domain():
    """Nothing matches: domain NOT ESTABLISHED (Art. XXV), generic
    template, no invented physics."""
    new = detect_domain_reasoned("a totally unclassifiable gizmo", "")
    assert new["domain"] == "UNKNOWN"
    assert new["selection_basis"] == "NO_EVIDENCE"
    assert "NOT" in new["why_selected"]  # 'NOT ESTABLISHED'


def test_e21d_bench15_honest_routing_only_by_design():
    """Scope disclosure: BENCH_15's mechanism states mechanical FUNCTION
    without mechanical QUANTITIES ('detent resists magnetically induced
    repositioning'); no registry domain's governing models cover
    magnetic-force-on-detent physics. The honest outcome is the
    ROUTING_ONLY fallback with the weaker justification recorded — NOT
    an anchor stuffed to force mechanical_structural (Art. XIX)."""
    mech = ("Mechanical detent resists magnetically induced "
            "repositioning, providing setting retention across MR "
            "exposure cycles. Integrate a ferromagnetic-free mechanical "
            "detent into the valve's pressure-setting mechanism to lock "
            "the selected setting against magnetic forces.")
    wrapper = ("implantable valve; valve pressure setting drifts after "
               "MRI exposure; MR-conditional mechanical stability")
    new = detect_domain_reasoned(mech, wrapper)
    assert new["selection_basis"] == "ROUTING_ONLY"
    assert new["phenomena_layer"] == {}
    assert "KEYWORD ROUTING ONLY" in new["why_selected"]


# -------------------------------------------------------- mutation controls
def test_e21d_midword_substring_false_positive_forbidden():
    """Measured defect in the anchor matcher itself (caught by the
    full-suite run): the stem anchor 'strain' matched MID-WORD inside
    'constraint' ("under the stated constraint"), routing a fluidics
    lumen-patency invention to mechanical_structural with PHENOMENA_
    DOMINANT confidence. A stem anchor licenses inflections of its own
    word only — never unrelated longer words that contain it."""
    text = ("porous microstructure resists fluid-path tissue ingrowth; "
            "sustained fluid flow through the shunt valve under the "
            "stated constraint of long-term lumen patency")
    phen = phenomena_layer(text)
    assert "mechanical_structural" not in phen, phen.get(
        "mechanical_structural")
    # and the true positives the rule must keep:
    assert "strain relief" in phenomena_layer(
        "strain-relief bellows redistribute bending strain")[
        "mechanical_structural"] or "strain" in phenomena_layer(
        "strain-relief bellows redistribute bending strain")[
        "mechanical_structural"]
    assert "harvest" in phenomena_layer(
        "energy-harvesting capacitor stores the scavenged charge")[
        "energy_harvesting"]
    # pure constraint/restraint vocabulary stays non-mechanical
    assert "mechanical_structural" not in phenomena_layer(
        "the design constraint restrains and constrains every option")


def test_e21d_mutation_removing_thermal_anchors_kills_dominance():
    """Sensitivity control: strip ALL thermal phenomena vocabulary from
    the BENCH_11 text and thermal must lose phenomena dominance — the
    selection then regresses to the OLD keyword routing (mechanical via
    'steer'), proving the phenomena layer, not fixture shape, was doing
    the work."""
    mutated = BENCH11_MECH.replace("dissipation", "spread") \
                          .replace("temperature", "temp") \
                          .replace("Joule heating", "electrical "
                                   "excitation") \
                          .replace("heating", "activity")
    mutated = mutated + " " + BENCH11_WRAPPER.replace("temperature",
                                                      "temp") \
                                             .replace("heating",
                                                      "activity")
    new = detect_domain_reasoned(mutated, "")
    assert "thermal" not in new["phenomena_layer"]
    # physics vocabulary gone -> the old defective routing returns,
    # honestly recorded as ROUTING_ONLY
    assert new["selection_basis"] == "ROUTING_ONLY"
    assert new["domain"] == "mechanical_structural"


def test_e21d_mutation_routing_text_stays_routing_only():
    """Adding physics-free extra words to a routing-only text must not
    manufacture a phenomena match."""
    new = detect_domain_reasoned(
        "a steerable catheter tip with articulation joints and a "
        "housing and a handle", "")
    assert new["selection_basis"] == "ROUTING_ONLY"


# --------------------------------------------------------- anti-drift pins
def test_e21d_anchors_contain_no_technique_or_device_words():
    """The exact failure mode of the old router must not re-enter via
    the phenomena layer: polysemous TECHNIQUE words (steer,
    piezoelectric, transducer) and bare DEVICE words (catheter, valve,
    shunt, electrode) are forbidden as anchors. A device word inside a
    longer QUANTITY phrase is physics ('antenna gain' is a link-budget
    quantity, not a device mention) — the ban is on the bare word."""
    forbidden = {"steer", "steering", "piezoelectric", "transducer",
                 "catheter", "valve", "shunt", "electrode", "stent",
                 "implant", "sensor", "detector", "probe", "pump",
                 "filter", "coating", "battery", "camera", "ultrasound",
                 "lasers", "catheters", "valves"}
    bad = sorted((dom, a) for dom, anchors in PHENOMENA_ANCHORS.items()
                 for a in anchors if a in forbidden)
    assert not bad, f"technique/device words as bare anchors: {bad}"


def test_e21d_anchors_are_physics_not_generic_words():
    """'energy', 'power', 'efficiency' alone are too generic to anchor
    anything (they cannot discriminate domains) — they must appear only
    inside longer, physics-specific anchors."""
    for dom, anchors in PHENOMENA_ANCHORS.items():
        for a in anchors:
            assert a not in {"energy", "power", "efficiency",
                             "conversion efficiency", "resonance",
                             "resonant"}, (dom, a)


def test_e21d_record_carries_ceo_item2_field_set():
    """CEO item 2 record discipline: every detection record carries the
    full field set so a reviewer can adjudicate the domain choice from
    the artifact alone."""
    for text in (BENCH11_MECH + " " + BENCH11_WRAPPER,
                 "a steerable catheter tip with articulation joints",
                 "an unclassifiable gizmo"):
        rec = detect_domain_reasoned(text, "")
        for field in ("selection_basis", "phenomena_layer",
                      "routing_layer", "why_selected",
                      "applicable_models", "assumptions", "limitations"):
            assert field in rec, (field, rec.get("domain"))
        assert set(rec["routing_layer"]) == {"mechanism", "wrapper"}


def test_e21d_superset_of_detect_domain_contract():
    """The reasoned record is a drop-in superset: every field the old
    detect_domain returned still exists with the same meaning."""
    old = detect_domain(BENCH12_MECH + " " + BENCH12_WRAPPER)
    new = detect_domain_reasoned(BENCH12_MECH, BENCH12_WRAPPER)
    for field in ("domain", "template", "matched_signals",
                  "runner_up", "epistemic_class", "note"):
        assert field in new


# ------------------------------------------------ 15-run scope regression
@pytest.mark.skipif(not HAS_RUNS, reason="E21 run fixtures not present")
def test_e21d_scope_pin_all_15_runs_measured_domains():
    """Pin the measured domain table for all 15 E21-C runs: 14 of 15
    now match BOTH the invention's stated physics AND the benchmark's
    declared domain (8 repairs vs the old router); BENCH_15 stays
    ROUTING_ONLY (honest fallback). Any future anchor edit that shifts
    a domain must re-adjudicate this table first."""
    expected = {
        "BENCH_01": ("fluidics_hydraulic", None),
        "BENCH_02": ("fluidics_hydraulic", None),
        "BENCH_03": ("optical_photonic", None),
        "BENCH_04": ("rf_wireless", None),
        "BENCH_05": ("acoustic", "PHENOMENA_DOMINANT"),
        "BENCH_06": ("mri_nmr", "PHENOMENA_DOMINANT"),
        "BENCH_07": ("enzyme_biocatalytic", "PHENOMENA_DOMINANT"),
        "BENCH_08": ("phage_microbio", "PHENOMENA_DOMINANT"),
        "BENCH_09": ("ml_data", None),
        "BENCH_10": ("mechanical_structural", "PHENOMENA_DOMINANT"),
        "BENCH_11": ("thermal", "PHENOMENA_DOMINANT"),
        "BENCH_12": ("energy_harvesting", "PHENOMENA_DOMINANT"),
        "BENCH_13": ("energy_harvesting", None),
        "BENCH_14": ("optical_photonic", "PHENOMENA_DOMINANT"),
        "BENCH_15": ("fluidics_hydraulic", "ROUTING_ONLY"),
    }
    m_fields = ("mechanism", "intervention", "expected_effect",
                "falsification_test")
    w_fields = ("device", "failure", "constraint")
    for i in range(1, 16):
        run = E21_RUNS / f"BENCH_{i:02d}"
        spec = json.loads((run / "INVENTION_SPECIFICATION.json")
                          .read_text(encoding="utf-8"))
        mech = " ".join(
            str((((spec.get("mechanism") or {}).get("value")) or {})
                .get(k, "")) for k in m_fields)
        problem = ((spec.get("problem") or {}).get("value") or {})
        wrapper = " ".join(str(problem.get(k, "")) for k in w_fields)
        new = detect_domain_reasoned(mech, wrapper)
        want_dom, want_basis = expected[f"BENCH_{i:02d}"]
        assert new["domain"] == want_dom, (f"BENCH_{i:02d}", mech[:80])
        if want_basis:
            assert new["selection_basis"] == want_basis, f"BENCH_{i:02d}"


# ------------------------------------------------------------- integration
def test_e21d_integration_reasoning_carried_into_artifact():
    """build_engineering_spec must carry the layered reasoning into the
    artifact's domain_detection record (CEO item 2: adjudicable from
    the artifact alone, without narrative)."""
    from discovery_fabric.engine.engineering_spec import (
        build_engineering_spec)
    from discovery_fabric.engine.invention_spec import (
        build_invention_spec)
    from test_f_series_integration import _survivor_env
    ctx = {"run_id": "testrun:e21d"}
    env = _survivor_env("fluidics_hydraulic")
    spec = build_invention_spec(env, ctx)
    eng = build_engineering_spec(spec, env, ctx)
    dd = eng["domain_detection"]
    for field in ("selection_basis", "why_selected", "applicable_models",
                  "assumptions", "limitations", "phenomena_layer",
                  "routing_layer"):
        assert field in dd, field
    assert dd["selection_basis"] in ("PHENOMENA_DOMINANT", "ROUTING_ONLY",
                                     "NO_EVIDENCE")
    # the honest basis text is recorded in why_this_domain (the
    # human-facing justification block)
    assert "keywords route, never justify" in eng["why_this_domain"]["basis"]


def test_e21d_depth_contract_counts_phenomena_selected_domain():
    """Measured BENCH_12 case: energy_harvesting selected PHENOMENA_
    DOMINANT with ZERO routing keyword hits — the depth contract's
    ENGINEERING_DOMAIN section must count the fully-reasoned detection
    record as its item (item presence and tie BOTH accept phenomena
    evidence; the keyword path is unchanged). Without this, the package
    build fails with ENGINEERING_DOMAIN(items=0/1) despite a complete,
    evidence-bearing domain record."""
    import sys as _sys
    from pathlib import Path as _Path
    from discovery_fabric.engine.depth_contract import (
        evaluate_depth_contract)
    run = _Path("/home/z/my-project/scripts/e21d_runs/BENCH_12")
    if not (run / "ENGINEERING_SPECIFICATION.json").exists():
        pytest.skip("E21-D BENCH_12 run not present")
    spec = json.loads((run / "INVENTION_SPECIFICATION.json")
                      .read_text(encoding="utf-8"))
    eng = json.loads((run / "ENGINEERING_SPECIFICATION.json")
                     .read_text(encoding="utf-8"))
    wd = eng["why_this_domain"]
    assert wd["selection_basis"] == "PHENOMENA_DOMINANT"
    assert not wd["matched_signals"]  # the measured condition
    res = evaluate_depth_contract(spec, eng)
    sec = res["sections"]["ENGINEERING_DOMAIN"]
    assert sec["present"] is True
    assert sec["item_count"] >= 1
    assert sec["invention_tied"] is True
    assert sec["satisfied"] is True
    # the tie may fire via invention tokens (first-priority path) or via
    # the phenomena-detection path — both are genuine recorded evidence
    assert sec["tie_evidence"]["linkage_kind"] in (
        "invention_tokens", "explicit_linkage_records",
        "domain_detection_evidence", "phenomena_detection_evidence")


def test_e21d_no_equation_in_library_has_empty_assumptions():
    """Library-wide pin of the MISSING_ASSUMPTIONS defect class (frozen
    instrument caught MRI-001 when the mri_nmr domain first became
    benchmark-governed at E21-D; E21-C fixed TH-001 for the same class).
    Every equation in EVERY domain library must carry >= 1 explicit
    physical assumption — no future domain may ship equations with an
    empty assumptions list."""
    from discovery_fabric.engine.equations import EQUATION_LIBRARY
    empty = [(dom, e["equation_id"])
             for dom, eqs in EQUATION_LIBRARY.items()
             for e in eqs if not e.get("assumptions")]
    assert not empty, f"equations with empty assumptions: {empty}"


def test_e21d_mri001_passes_frozen_equation_audit():
    """Positive control with the frozen oracle: MRI-001 with the new
    assumptions must pass audit_equations even with unsourced inputs
    (same oracle pattern as the E21-C OPT-004 control)."""
    from discovery_fabric.engine.equations import EQUATION_LIBRARY
    from discovery_fabric.benchmark.equation_integrity import (
        audit_equations)
    eq = next(e for e in EQUATION_LIBRARY["mri_nmr"]
              if e["equation_id"] == "MRI-001")
    record = {
        "technology_domain": "mri_nmr",
        "engineering_core": {
            "governing_model": {"equations": [{
                "equation_id": "MRI-001",
                "expression": eq["expression"],
                "variables": eq["variables"],
                "applicability": {
                    "condition": eq["applicability"],
                    "judged_for_domain": "mri_nmr"},
                "assumptions": eq["assumptions"],
                "source": {"text": "standard NMR relation (MRI physics "
                                   "texts)"},
            }]},
            "critical_parameters": [
                {"parameter": "static field strength",
                 "value": "UNKNOWN"}],
        },
    }
    a = audit_equations(record)
    issues = [i for r in a.get("equations", [])
              for i in r.get("issues", [])]
    assert not any("MISSING_ASSUMPTIONS" in i for i in issues), issues
    # mutation control: stripped assumptions -> the frozen oracle
    # re-flags the defect (the gate was not weakened; the artifact
    # changed)
    mutated = json.loads(json.dumps(record))
    mutated["engineering_core"]["governing_model"]["equations"][0][
        "assumptions"] = []
    a2 = audit_equations(mutated)
    issues2 = [i for r in a2.get("equations", [])
               for i in r.get("issues", [])]
    assert any("MISSING_ASSUMPTIONS" in i for i in issues2), issues2

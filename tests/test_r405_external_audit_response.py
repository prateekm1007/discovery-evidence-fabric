"""tests/test_r405_external_audit_response.py — adversarial pins for the
R405 round: the external-audit response, the unit-conversion defect fix,
the Q_min/MDD computations, the claim maps, the traceability bindings, the
manifest enumeration, and the P14 immutability pin.

Constitutional anchors exercised:
- Art. XVII/XVIII (every control attacked: the magnitude guard would fail
  under the pre-R405 inverted conversion).
- Art. XXVII (threshold provenance: Q_min and kill margins carry class,
  source, and owner gates — asserted structurally).
- Art. XXV (the audit's DISPUTED figures are recorded as disputed, never
  laundered into facts).
- Art. XI/XXXIX (P14 records byte-unchanged; buyer surface untouched).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import physics_core as pc  # noqa: E402
from discovery_fabric.engine import reality_loop  # noqa: E402

R405 = REPO / "R405"
LP4 = REPO / "LEAD_PORTFOLIO_4"


def _load(p: Path):
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# A. The unit-conversion defect fix (the round's core code change)
# ---------------------------------------------------------------------------

def test_conductance_conversion_direction_pinned():
    """The per-mmHg value must EXCEED the per-Pa value in matching units
    (one mmHg = 133.322 Pa). Under the pre-R405 inverted code this fails
    by 133.322^2 — the adversarial demonstration (Art. XVIII)."""
    d, eta, L = 0.6, 1.0, 100.0
    g_per_mmHg = reality_loop._conductance_ml_per_min_mmhg(d, eta, L)
    g_si = (math.pi * (d * 1e-3) ** 4
            / (128.0 * eta * 1e-3 * L * 1e-3))       # m3/(s*Pa)
    g_per_pa_ml_min = g_si * 1e6 * 60.0               # mL/(min*Pa)
    assert g_per_mmHg == pytest.approx(
        g_per_pa_ml_min * 133.322, rel=1e-12)
    # the direction: bigger pressure unit -> numerically larger
    # per-unit conductance
    assert g_per_mmHg > g_per_pa_ml_min


def test_physics_solver_conductance_same_fix():
    g = pc.poiseuille_conductance(1.0, 90.0, 1.0)
    g_si = (math.pi * (1.0e-3) ** 4 / (128.0 * 1e-3 * 90.0e-3))
    expected = g_si * 1e6 * 133.322                   # (mL/s)/mmHg
    assert g == pytest.approx(expected, rel=1e-12)
    # physical magnitude: 1.0 mm x 90 mm water at 1 mmHg ~ 2.2 mL/min
    assert 0.1 <= g * 60.0 <= 10.0


def test_solver_flows_now_physical_magnitude():
    """The R396 reference network (1.0 mm x 90 mm, 8 mmHg, eta 1.0): the
    true total flow is ~17.5 mL/min. The pre-R405 solver emitted
    9.8e-6 mL/min — five orders below physical reality. This test fails
    under the inverted conversion (the defect class cannot recur
    silently)."""
    spec = {
        "geometry_identity": "r405-magnitude-guard",
        "geometry_hash": "r405-magnitude-guard",
        "fluid": {"viscosity_mPa_s": 1.0, "density_kg_m3": 993.0},
        "boundary": {"inlet_mmHg": 12.0, "outlet_mmHg": 4.0},
        "segments": [
            {"segment_id": "primary", "node_a": "A", "node_b": "B",
             "diameter_mm": 1.0, "length_mm": 90.0},
        ],
    }
    r = pc.solve_network(spec)
    assert r["status"] in ("COMPUTATIONAL_RESULT",
                           "COMPUTATIONAL_RESULT_MODEL_INVALIDITY")
    q = r["predicted_quantities"]["total_flow_ml_min"]
    # independent closed form (g is (mL/s)/mmHg; x 8 mmHg x 60 s/min)
    g = (math.pi * (1.0e-3) ** 4 / (128.0 * 1e-3 * 0.09)) \
        * 1e6 * 133.322
    assert q == pytest.approx(g * 8.0 * 60.0, rel=1e-9)
    # physical magnitude band (Art. XVII): mL/min, not uL/min
    assert 1.0 <= q <= 100.0, (
        f"total flow {q} mL/min outside the physical band for a 1 mm "
        "catheter at 8 mmHg — unit conversion defect class")


def test_defect_disclosure_exists_and_inventories():
    d = _load(R405 / "UNIT_CONVERSION_DEFECT_DISCLOSURE.json")
    assert d["the_defect"]["effect"].find("17,774.7") > 0
    assert len(d["affected_recorded_artifacts"]) == 5
    assert d["unaffected"]["ratio_based_results"].startswith("ALL")
    # the Art. XXXI memory artifact exists
    ma = d["memory_artifact_art_xxxi"]
    assert "lesson" in ma and "tests_added" in ma


# ---------------------------------------------------------------------------
# B. Q_min and the corrected floor hydraulics
# ---------------------------------------------------------------------------

def test_qmin_record_structurally_valid():
    d = _load(LP4 / "P04" / "QMIN_FLOOR_FLOW_CALCULATION.json")
    q = d["contents"]["q_min"]
    # per-MINUTE physiology (the audit's mL/hr unit error is flagged,
    # never adopted)
    assert q["value_range"] == [0.2, 0.4]
    assert q["unit"] == "mL/min"
    assert q["threshold_class"] == "PHYSIOLOGICAL"
    assert "external_audit_error_flagged" in q
    assert "UNIT ERROR" in q["external_audit_error_flagged"]["verdict"]
    # every source carries a verified snippet + retrieval method
    for s in q["sources"]:
        assert s.get("verified_snippet") and s.get("retrieval")


def test_floor_flows_match_the_corrected_conductance():
    d = _load(LP4 / "P04" / "QMIN_FLOOR_FLOW_CALCULATION.json")
    rows = d["contents"]["floor_flow_computation"]
    assert {r["geometry"] for r in rows} == {
        "canonical_shipped", "nist_corrected_candidate"}
    for r in rows:
        g = (math.pi * (r["floor_lumen_diameter_mm"] * 1e-3) ** 4
             / (128.0 * 0.6913036e-3 * 0.1)) * 1e6 * 60.0 * 133.322
        assert r["conductance_mL_min_mmHg"] == pytest.approx(
            g, rel=1e-4)
        for dp in (10.0, 20.0, 40.0):
            fl = r["flows"][f"at_{dp:.0f}_mmHg"]
            assert fl["mL_per_min"] == pytest.approx(g * dp, rel=1e-4)
            # both geometries pass Q_min with margin at every head
            assert fl["passes_q_min"] is True


def test_common_cause_tolerance_margin_is_quantified():
    d = _load(LP4 / "P04" / "QMIN_FLOOR_FLOW_CALCULATION.json")
    tm = d["contents"]["common_cause_tolerance_margin"]
    assert 40.0 < tm["tolerated_diameter_reduction_pct"] < 55.0
    assert tm["evidence_class"] == "COMPUTATIONAL_RESULT"


def test_decisive_experiment_qmin_and_common_cause_extensions():
    d = _load(LP4 / "P04" / "DECISIVE_EXPERIMENT.json")
    ext = d["r405_extensions"]
    assert ext["q_min_declaration"]["threshold_class"] == "PHYSIOLOGICAL"
    cc = ext["common_cause_quantified_arm"]
    assert cc["kill_rule"].find("90%") > 0
    # Art. XXVII: the 90% threshold carries provenance + class + owner
    # gate (never silently promoted)
    tp = cc["threshold_provenance"]
    assert tp["class"] == "ENGINEERING"
    assert tp["owner_gate"] == "REQUIRED"
    assert ext["cost_basis_r405"]["status"].startswith("REPORTED")


# ---------------------------------------------------------------------------
# C. P08 — D2 arithmetic, thermal, GaAs, framing
# ---------------------------------------------------------------------------

def test_p08_energy_budget_r405_extensions():
    d = _load(LP4 / "P08" / "ENERGY_BUDGET.json")
    ext = d["r405_extensions"]
    # D2 arithmetic is displayed AND the decision remains owner-gated
    assert ext["d2_explicit_arithmetic_display"]["decision_remains"].\
        startswith("OWNER-GATED")
    chain = ext["d2_explicit_arithmetic_display"][
        "audit_reconstruction_chain"]
    assert chain["inputs"]["source_irradiance"]["class"].startswith(
        "REPORTED")
    # thermal: structure adopted, numbers explicitly unverified
    tb = ext["thermal_kill_boundary"]["audit_figures_reported"]
    assert tb["verification"].startswith("NOT VERIFIED")
    # GaAs sourcing: verified snippets present
    cites = ext["gaas_low_irradiance_efficiency_sourcing"]["citations"]
    assert any("Moon" in c["reference"] for c in cites)
    assert all(c.get("verified_snippet") for c in cites)
    # D1/D2/D3 states unchanged from R404 (this round does not silently
    # resolve what R404 left open)
    assert d["derived_discrepancies"][0].startswith("D1 [RESOLVED")
    assert d["derived_discrepancies"][1].startswith("D2 [OPEN")


def test_p08_thermal_kill_in_decisive_experiment():
    d = _load(LP4 / "P08" / "DECISIVE_EXPERIMENT.json")
    ext = d["r405_extensions"]["thermal_kill_condition_r405"]
    assert ext["rule"].find("KILL") == 0
    assert ext["threshold_status"].find("OWNER-GATED") > 0


# ---------------------------------------------------------------------------
# D. P11 — kill conditions, MDD, claim map
# ---------------------------------------------------------------------------

def test_p11_kill_conditions_are_proposed_not_registered():
    d = _load(LP4 / "P11" / "DECISIVE_EXPERIMENT.json")
    ext = d["r405_extensions"]["quantified_kill_conditions_r405"]
    a = ext["proposed_condition_A"]
    assert a["rule"].find("20% faster") > 0
    tp = a["threshold_provenance"]
    assert tp["class"].startswith("MODEL_DERIVED")
    assert tp["origin"]["provenance"].startswith("R405 external audit")
    assert tp["owner_gate"].startswith("REQUIRED")
    assert "materiality evidence remains NONE" in tp["uncertainty"]


def test_p11_mdd_record():
    d = _load(LP4 / "P11" / "INSTRUMENT_MDD_CALCULATION.json")
    c = d["contents"]["computation"]
    assert c["claimed_difference_s"] == 0.1
    assert c["verdict"] == "DETECTABLE"
    assert c["mdd_at_p05_s"] == pytest.approx(0.0253, abs=1e-3)
    # honest limits present (model-derived settling values, unmodelled
    # trace noise, materiality UNESTABLISHED)
    limits = " ".join(d["contents"]["honest_limits"])
    assert "MODEL_DERIVED" in limits
    assert "UNESTABLISHED" in limits


def test_p11_claim_map_grounded_in_recorded_patent():
    d = _load(LP4 / "P11" / "NOVELTY_ASSESSMENT.json")
    cm = d["r405_extensions"]["closest_prior_claim_map_US20250242099A1"]
    assert len(cm["differentiation_argument"]) == 3
    # evidence basis includes BOTH the recorded relevance and the
    # searched publication record
    eb = " ".join(cm["evidence_basis"])
    assert "recorded relevance" in eb and "Justia" in eb
    assert "NOT a patentability opinion" in cm["limits"]


# ---------------------------------------------------------------------------
# E. P13 — query plan, KA-014, fouling protocol
# ---------------------------------------------------------------------------

def test_p13_query_plan_records_audit_queries():
    d = _load(LP4 / "P13" / "NOVELTY_ASSESSMENT.json")
    qp = d["r405_extensions"]["patentbear_query_plan_r405"]
    queries = " ".join(q["query"] for q in qp["queries_proposed"])
    assert "self-referencing" in queries
    assert "wheatstone bridge dummy element" in queries
    assert qp["status"].startswith("OWNER ACTION")


def test_p13_ka014_prominence_and_protocol():
    d = _load(LP4 / "P13" / "DECISIVE_EXPERIMENT.json")
    ext = d["r405_extensions"]
    decl = ext["ka014_prominence_declaration"]["statement"]
    assert decl.startswith("KA-014")
    assert "3.45" in decl and "P-25" in decl  # the predecessor failure
    fp = ext["accelerated_fouling_protocol_r405"]
    assert "bovine serum albumin" in fp["protocol"]
    assert fp["kill_criterion"].find("1 mmHg") > 0
    assert fp["provenance"]["owner_gate"] == "REQUIRED"
    # cost estimate carries the 5-10x disclosure
    assert "5-10x" in ext["cost_basis_r405"]["material_disclosure"]


# ---------------------------------------------------------------------------
# F. Traceability records (R394 bindings, 3 chains each)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pkg", ["P04", "P08", "P11", "P13"])
def test_traceability_records(pkg):
    d = _load(LP4 / pkg / "ENGINEERING_TRACEABILITY.json")
    assert len(d["chains"]) == 3
    for c in d["chains"]:
        # R394 binding: every link is IDENTIFIER-bound with evidence
        assert c["mechanism_feature"]["binding"] == "IDENTIFIER"
        assert c["mechanism_feature"]["state"] == "EXPLICIT"
        assert c["experiment"]["state"] == "EXPLICIT"
        # V items stay NOT_TESTED — linking documents the graph, it does
        # not execute verification (Art. XXVIII)
        assert c["evidence_classes"]["v"].startswith("NOT_TESTED")
    # the remaining-unknown count is stated, not hidden
    assert d["package_state_after_r405"]["chains_remaining_unknown"]
    # binding rules quoted verbatim from r394
    assert "semantic association, fuzzy match, or invented " \
        "binding" in json.dumps(d["binding_rules_verbatim"])


def test_traceability_ids_exist_in_frozen_corpus():
    """The DI/DO/V identifiers referenced engine-side must exist in the
    frozen corpus maturity basis (no invented bindings — Art. II)."""
    corpus_map = {
        "P04": "04_drainage_floor", "P08": "08_nir_photovoltaic",
        "P11": "11_gravity_damper", "P13": "13_pressure_sensor"}
    for pkg, corpus in corpus_map.items():
        mb = _load(REPO / "BENCHMARK_ENGINEERING_DOSSIERS" /
                   "frozen_corpus_r370" / corpus / "MATURITY_BASIS.json")
        known = set(mb["design_input_evidence_ids"]) | set(
            mb["design_output_evidence_ids"]) | set(
            mb["verification_evidence_ids"])
        d = _load(LP4 / pkg / "ENGINEERING_TRACEABILITY.json")
        for c in d["chains"]:
            assert c["design_input_id"] in known, c["design_input_id"]
            assert c["design_output_id"] in known, c["design_output_id"]
            assert c["verification_id"] in known, c["verification_id"]


# ---------------------------------------------------------------------------
# G. Manifest, response record, P14 immutability
# ---------------------------------------------------------------------------

def test_manifest_v3_enumerates_r405():
    m = _load(REPO / "LEAD_PORTFOLIO_4_MANIFEST.json")
    # R406 bumped the manifest to 4.0 (legitimate forward evolution: the
    # manifest is the living canonical enumeration). The R405 pin's
    # PURPOSE — the R405 round block is intact and enumerated — is
    # unchanged and still enforced below.
    assert float(m["manifest_version"]) >= 3.0
    r405 = m["r405_external_audit_response_round"]
    assert "R405/EXTERNAL_AUDIT_RESPONSE.md" in r405["new_artifacts"]
    assert r405["final_classification"].startswith("UNCHANGED")
    assert any("NIST canonical application" in s
               for s in r405["owner_gated_items_recorded"])


def test_response_record_classifications_complete():
    text = (R405 / "EXTERNAL_AUDIT_RESPONSE.md").read_text()
    for token in ("CONFIRMED", "ADDRESSED_BY_R404", "DISPUTED",
                  "EXECUTED", "OWNER_GATED", "unit error",
                  "17,774.7"):
        assert token in text, token


def test_p14_records_byte_unchanged():
    """Art. XI/XXXIX + the R404 pin: P14 stays out of this round entirely."""
    import hashlib
    blob = (REPO / "LEAD_PORTFOLIO_4" / "P14" /
            "P14_EXTERNAL_DISTRIBUTION_RECORD.json").read_bytes()
    # the R404-pinned hash (verified against the R403 blob at R404)
    r404 = _load(REPO / "tests" / "r403_corpus_pins.json")  # not the pin
    # source — the R404 test pins it; recompute via git instead:
    import subprocess
    old = subprocess.run(
        ["git", "show", "f9aa4ab4:LEAD_PORTFOLIO_4/P14/"
         "P14_EXTERNAL_DISTRIBUTION_RECORD.json"],
        cwd=REPO, capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == hashlib.sha256(old).hexdigest()


def test_no_buyer_repo_bytes_touched():
    """The frozen corpus pins still match the R403 pins (zero buyer-surface
    changes this round)."""
    pins = _load(REPO / "tests" / "r403_corpus_pins.json")
    import hashlib
    for rel, sha in pins.items():
        f = REPO / "BENCHMARK_ENGINEERING_DOSSIERS" / "frozen_corpus_r370" \
            / rel
        assert hashlib.sha256(f.read_bytes()).hexdigest() == sha, rel


# ---------------------------------------------------------------------------
# H. The external audit's disputed figures are recorded as disputed
# ---------------------------------------------------------------------------

def test_audit_disputed_figures_never_laundered():
    """Art. XXV: the audit's unverified numbers must appear ONLY with
    their verification status, never as facts."""
    p04 = _load(LP4 / "P04" / "BUYER_SEQUENCE.json")
    anchor = p04["r405_extensions"]["commercial_anchor"]["anchors"]
    assert "DISPUTED" in anchor["us_shunt_surgeries_per_year"][
        "audit_figure_flagged"]
    assert anchor["us_shunt_surgeries_per_year"]["value"] == "36,000+"
    p13 = _load(LP4 / "P13" / "BUYER_SEQUENCE.json")
    assert "divergen" in p13["r405_extensions"]["commercial_anchor"][
        "status"].lower()


def test_nist_disposition_records_the_auditor_conflict():
    d = _load(LP4 / "P04" / "GEOMETRY_SEPARATION.json")
    disp = d["r405_extensions"]["nist_canonical_application_disposition"]
    assert disp["state"].startswith("OWNER-GATED")
    assert "AUDITOR CONFLICT" in disp["state"]
    # both positions recorded verbatim, neither silently wins
    assert disp["r403_position"] and disp["external_audit_position"]
    assert disp["resolution"].startswith("NOT silently resolved")


def test_ka014_is_now_the_most_prominent_p13_risk():
    """The audit's option (c): the KA-014 declaration is a first-class
    extension, not a footnote."""
    d = _load(LP4 / "P13" / "DECISIVE_EXPERIMENT.json")
    s = d["r405_extensions"]["ka014_prominence_declaration"]["statement"]
    assert s.find("PRIMARY SCIENTIFIC RISK") > 0
    assert "most prominent" in d["r405_extensions"][
        "ka014_prominence_declaration"]["statement"]

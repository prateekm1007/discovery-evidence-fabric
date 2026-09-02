"""tests/test_r394_benchmark.py — the R394 section 17 PERMANENT
BENCHMARK (18 cases).

Directive:

  "Add: [18 cases]. The benchmark must run from a clean environment."

Every case here is HERMETIC (no network, no LLM, no clock dependence,
no production state touched — the conftest ledger guards apply). The
networked connector paths are exercised through injected outages
(mocked transports), which is exactly the defect class the directive
targets (provider timeout / connector outage / failed search).

Run: python -m pytest tests/test_r394_benchmark.py -v
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import socket
import sys
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.connectors import connector_states  # noqa: E402
from discovery_fabric.engine import physics_core as pc  # noqa: E402
from discovery_fabric.engine import design_learning as dl  # noqa: E402
from discovery_fabric.engine import reality_calibration as rc  # noqa: E402
from discovery_fabric.engine import evidence_classification as ec  # noqa: E402
from discovery_fabric.engine import premise_gate as pg  # noqa: E402
from discovery_fabric.prior_art_v2 import collision_resolution as cr  # noqa: E402
import discovery_fabric.a2.prior_art as a2pa  # noqa: E402


# ---------------------------------------------------------------------------
# shared fixtures
# ---------------------------------------------------------------------------

FLUID = {"viscosity_mPa_s": 1.0, "density_kg_m3": 993.0,
         "temperature_K": 310.15}

BASELINE_SPEC = {
    "geometry_identity": "bench-baseline",
    "geometry_hash": hashlib.sha256(b"bench-baseline").hexdigest(),
    "fluid": FLUID,
    "boundary": {"inlet_mmHg": 12.0, "outlet_mmHg": 4.0},
    "segments": [{"segment_id": "primary", "node_a": "A", "node_b": "B",
                  "diameter_mm": 1.0, "length_mm": 90.0}],
}

CANDIDATE_SPEC = {
    "geometry_identity": "bench-candidate",
    "geometry_hash": hashlib.sha256(b"bench-candidate").hexdigest(),
    "fluid": FLUID,
    "boundary": {"inlet_mmHg": 12.0, "outlet_mmHg": 4.0},
    "segments": [
        {"segment_id": "primary", "node_a": "A", "node_b": "B",
         "diameter_mm": 1.0, "length_mm": 90.0},
        {"segment_id": "floor", "node_a": "A", "node_b": "B",
         "diameter_mm": 0.5471, "length_mm": 90.0},
    ],
}


def _mock_urlopen(body: dict):
    return lambda url, timeout=20, context=None: io.BytesIO(
        json.dumps(body).encode())


# ---------------------------------------------------------------------------
# 1-3: valid problems across domains (premise coherent + classifiable)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("problem,mm,expected_mech_class", [
    # 1. valid BIOMEDICAL problem
    ({"device": "tunneled hemodialysis catheter",
      "failure": "catheter occlusion loss of flow patency",
      "failure_mode": "OCCLUSION"},
     {"mechanism": "heparin coating reduces thrombus formation",
      "intervention": "covalently bonded heparin coating on luminal surface",
      "expected_effect": "reduced occlusion"},
     "DIRECT_SUPPORT"),
    # 2. valid MECHANICAL problem
    ({"device": "rail steel",
      "failure": "rail fracture under fatigue loading",
      "failure_mode": "FATIGUE"},
     {"mechanism": "compressive residual stress surface layer retards "
                   "crack initiation",
      "intervention": "head-hardened rail with surface compressive layer",
      "expected_effect": "retarded crack initiation"},
     None),
    # 3. valid THERMAL/FLUID problem
    ({"device": "EV traction battery pack",
      "failure": "thermal runaway initiation during fast charge",
      "failure_mode": "THERMAL_DAMAGE"},
     {"mechanism": "inter-cell thermal barrier limits propagation",
      "intervention": "aerogel inter-cell thermal barrier",
      "expected_effect": "limited propagation"},
     None),
])
def test_bench_valid_problems(problem, mm, expected_mech_class):
    verdict = pg.check_premise(problem)
    assert verdict["verdict"] == "PREMISE_COHERENT"
    # evidence classification runs without error on all domains
    item = {"id": "x:1", "title": problem["device"] + " study",
            "abstract": f"{problem['device']} {problem['failure']} "
                        f"{mm['mechanism']} measured effect."}
    out = ec.classify_evidence_item(item, problem, mm)
    assert out["classification"] in ec.EVIDENCE_CLASSES
    assert out["classifier_version"] == ec.EVIDENCE_CLASSIFIER_VERSION


# ---------------------------------------------------------------------------
# 4: false premise
# ---------------------------------------------------------------------------

def test_bench_04_false_premise():
    problem = {
        "device": "borosilicate glass reactor liner",
        "failure": "grain-boundary sliding failures limit service temperature",
        "failure_mode": "grain-boundary sliding",
    }
    v = pg.check_premise(problem)
    assert v["verdict"] == "MALFORMED_OR_FALSE_PREMISE"
    assert "PG-01" in v["explanation"]
    assert v["matched_rules"][0]["rule_id"] == "PG-01"
    # the explanation is self-contained (a buyer can read it)
    assert "amorphous" in v["explanation"]


def test_bench_04_false_premise_blocks_engine_chain():
    """The premise gate is a FIRST-CLASS stage: a false premise produces
    MALFORMED_OR_FALSE_PREMISE as the terminal state, synthesis is
    skipped, and no cemetery entry is written (not negative knowledge)."""
    from discovery_fabric.engine.run import EngineRun
    import tempfile
    problem = {
        "problem_id": "bench_false_premise",
        "device": "borosilicate glass reactor liner",
        "failure": "grain-boundary sliding failures limit service temperature",
        "failure_mode": "grain-boundary sliding",
        "user_need": "prevent grain boundary sliding in the glass liner",
    }
    with tempfile.TemporaryDirectory() as td:
        run = EngineRun(problem, td, with_package=False)
        manifest = run.run()
        fs = json.loads((Path(td) / "final_state.json").read_text())
        assert fs["final_status"] == "MALFORMED_OR_FALSE_PREMISE"
        assert "PREMISE_GATE" in fs["failed_stages"]
        # downstream stages skipped, not silently run
        skipped = {e["stage"]: e["status"]
                   for e in json.loads(
                       (Path(td) / "candidate_envelope.json").read_text())
                   ["stage_log"]}
        assert skipped.get("SYNTHESIZE") == "SKIPPED_UPSTREAM_FAILURE"
        # R397 pin: PHYSICS is a downstream stage of the premise gate —
        # after a premise fatality it records SKIPPED_UPSTREAM_FAILURE
        # (executing it recorded a misleading OK with an empty mechanism;
        # found live by the R396 P3 probe, fixed in DOWNSTREAM_BLOCKERS)
        assert skipped.get("PHYSICS") == "SKIPPED_UPSTREAM_FAILURE"
        cem = json.loads((Path(td) / "cemetery_update.json").read_text())
        assert cem["appended"] is False
        assert manifest["final_status"] == "MALFORMED_OR_FALSE_PREMISE"


# ---------------------------------------------------------------------------
# 5: irrelevant evidence injection
# ---------------------------------------------------------------------------

def test_bench_05_irrelevant_evidence():
    problem = {"device": "tunneled hemodialysis catheter",
               "failure": "catheter occlusion", "failure_mode": "OCCLUSION"}
    mm = {"mechanism": "heparin coating reduces thrombus formation",
          "intervention": "heparin luminal coating",
          "expected_effect": "reduced occlusion"}
    cmos = {"id": "europepmc:32784801",
            "title": "State of the Art and Future Perspectives in "
                     "Advanced CMOS Technology",
            "abstract": "Integrated strain engineering in CMOS scaling; "
                        "channel mobility optimization."}
    out = ec.classify_evidence_item(cmos, problem, mm)
    assert out["classification"] == "IRRELEVANT"
    # the exact production-measured case: the deployed run's ONLY
    # evidence was this CMOS paper (R394/PRODUCTION_AUDIT) — the
    # classifier now names it irrelevant instead of feeding synthesis
    agg = ec.classify_evidence_set([cmos], problem, mm)
    assert agg["counts"]["IRRELEVANT"] == 1
    assert agg["mechanism_support"]["n_direct_support"] == 0


# ---------------------------------------------------------------------------
# 6: contradictory evidence
# ---------------------------------------------------------------------------

def test_bench_06_contradictory_evidence():
    problem = {"device": "tunneled hemodialysis catheter",
               "failure": "catheter occlusion", "failure_mode": "OCCLUSION"}
    mm = {"mechanism": "heparin coating reduces thrombus formation",
          "intervention": "heparin luminal coating",
          "expected_effect": "reduced occlusion"}
    contra = {"id": "e:9",
              "title": "Coated catheter trial",
              "abstract": "The heparin coated catheter did not reduce "
                          "occlusion events; no difference was found in "
                          "thrombus formation."}
    out = ec.classify_evidence_item(contra, problem, mm)
    assert out["classification"] == "CONTRADICTORY"
    assert out["classification_basis"]["contradiction_basis"]
    agg = ec.classify_evidence_set([contra], problem, mm)
    assert agg["mechanism_support"]["n_contradictory"] == 1


# ---------------------------------------------------------------------------
# 7: provider timeout
# ---------------------------------------------------------------------------

def test_bench_07_provider_timeout():
    # connector states classify timeouts as TIMEOUT -> epistemic UNKNOWN
    assert connector_states.classify_exception(
        socket.timeout("t")) == "TIMEOUT"
    o = connector_states.outcome("TIMEOUT", "europepmc", "t/o")
    assert o["epistemic_effect"] == "UNKNOWN"
    # the a2 scientific search: all-timeout => SEARCH_FAILED, never
    # NO_MATCHING_EVIDENCE_FOUND
    with mock.patch.object(
            a2pa.urllib.request, "urlopen",
            side_effect=socket.timeout("timed out")):
        r = a2pa.search_prior_art_with_queries(["catheter occlusion"])
    assert r["prior_art_status"] == "SEARCH_FAILED"
    assert r["search_execution"]["timeout_present"] is True
    assert r["search_execution"]["n_executed_ok"] == 0


# ---------------------------------------------------------------------------
# 8: failed prior-art search (the release-blocking false positive)
# ---------------------------------------------------------------------------

def test_bench_08_failed_prior_art_search_cannot_differentiate():
    """The EXACT production defect (run ts_d1ab9fd4d756:
    RESOLVED_DIFFERENTIATED with 5/10 searches FAILED). Partial search
    failure must now yield UNRESOLVED_SEARCH_INCOMPLETE — positive
    differentiation is forbidden."""
    mm = {"mechanism": "heparin coating reduces thrombus formation",
          "intervention": "covalently bonded heparin coating on the "
                          "catheter luminal surface",
          "expected_effect": "reduced occlusion and preserved flow"}
    problem = {"device": "tunneled hemodialysis catheter",
               "failure": "catheter occlusion loss of flow patency"}
    profile = cr.build_candidate_profile(mm, problem)
    hit = cr.PatentHit(patent_id="US1", title="catheter heparin study",
                       snippet="A" * 200, source_id="google_patents",
                       source_url="u", query_class="ENTITY", query="q")
    fam = [{"family_id": "F1", "representative": hit, "members": [hit]}]
    errors = [{"query": f"q{i}", "source": "lens_patent",
               "error": "HTTP 429 quota"} for i in range(5)]
    res = cr.resolve_differentiation(fam, profile, errors, True,
                                      deep_fetch=False)
    assert res["state"] == "UNRESOLVED_SEARCH_INCOMPLETE", (
        "partial search failure MUST NOT yield a resolved state "
        f"(got {res['state']})")
    assert res["search_execution"]["mandatory_complete"] is False


# ---------------------------------------------------------------------------
# 9: identical-input determinism
# ---------------------------------------------------------------------------

def test_bench_09_identical_input_determinism():
    # solver: identical input -> identical output hash (bit-level)
    r1 = pc.solve_network(CANDIDATE_SPEC)
    r2 = pc.solve_network(CANDIDATE_SPEC)
    assert r1["output_hash"] == r2["output_hash"]
    # collision adjudication: identical profile + text -> identical
    # coverage decision
    mm = {"mechanism": "heparin coating reduces thrombus formation",
          "intervention": "heparin luminal coating",
          "expected_effect": "reduced occlusion"}
    problem = {"device": "catheter", "failure": "occlusion"}
    hit = cr.PatentHit(patent_id="US1", title="catheter heparin study",
                       snippet="A" * 200, source_id="g", source_url="u",
                       query_class="ENTITY", query="q")
    fam = [{"family_id": "F1", "representative": hit, "members": [hit]}]
    d1 = cr.resolve_differentiation(fam, cr.build_candidate_profile(
        mm, problem), [], True, deep_fetch=False)
    d2 = cr.resolve_differentiation(fam, cr.build_candidate_profile(
        mm, problem), [], True, deep_fetch=False)
    assert d1["per_family"][0]["coverage"] == \
        d2["per_family"][0]["coverage"]
    assert d1["state"] == d2["state"]
    # and the replay-consistency instrument verifies it (no flag)
    c = cr.check_replay_consistency(mm, problem, d1)
    assert c["consistent"] and c["flag"] is None


# ---------------------------------------------------------------------------
# 10: candidate fails a deterministic physics bound
# ---------------------------------------------------------------------------

def test_bench_10_candidate_fails_physics_bound():
    bad = copy.deepcopy(CANDIDATE_SPEC)
    bad["segments"][0]["diameter_mm"] = -0.5
    r = pc.solve_network(bad)
    assert r["status"] == "PLAUSIBILITY_BOUND_VIOLATED"
    assert any(v["bound"].startswith("segment diameter")
               for v in r["violations"])
    # no computational evidence is emitted for a bound violation
    assert pc.to_computational_result(r)["evidence_class"] == "NOT_EMITTED"
    # geometric-scale bound
    big = copy.deepcopy(CANDIDATE_SPEC)
    big["segments"][0]["diameter_mm"] = 120.0
    r2 = pc.solve_network(big)
    assert r2["status"] == "PLAUSIBILITY_BOUND_VIOLATED"
    assert any(v["class"] == "GEOMETRIC_SCALE" for v in r2["violations"])


# ---------------------------------------------------------------------------
# 11: candidate loses baseline
# ---------------------------------------------------------------------------

def test_bench_11_candidate_loses_baseline():
    worse = copy.deepcopy(BASELINE_SPEC)
    worse["segments"][0]["diameter_mm"] = 0.5  # primary smaller than baseline
    comp = pc.compare_to_baseline(worse, BASELINE_SPEC, "primary",
                                  scenario="SEVERE_OBSTRUCTION")
    assert comp["outcome"] == "DOES_NOT_BEAT_BASELINE"
    assert comp["comparison"]["improvement_relative"] < 0


# ---------------------------------------------------------------------------
# 12: candidate beats baseline
# ---------------------------------------------------------------------------

def test_bench_12_candidate_beats_baseline():
    comp = pc.compare_to_baseline(
        CANDIDATE_SPEC, BASELINE_SPEC, "primary",
        scenario="SEVERE_OBSTRUCTION", required_min=0.05)
    assert comp["outcome"] == "BEATS_BASELINE"
    assert comp["comparison"]["improvement_absolute"] > 0
    assert comp["solver_version"] == pc.SOLVER_VERSION


# ---------------------------------------------------------------------------
# 13: solver failure / not simulatable
# ---------------------------------------------------------------------------

def test_bench_13_solver_failure():
    sim = pc.simulate_failure_modes(BASELINE_SPEC, "nonexistent-segment")
    assert sim["status"] == "MECHANISM_NOT_SIMULATABLE"
    assert "solver-validated" in sim["reason"]
    # invalid input raises BEFORE any result is fabricated
    with pytest.raises(ValueError):
        pc.poiseuille_conductance(-1.0, 90.0, 1.0)


# ---------------------------------------------------------------------------
# 14: reality discrepancy (quantified)
# ---------------------------------------------------------------------------

def test_bench_14_reality_discrepancy():
    # ground truth: water at 310 K (0.6913 mPa.s) — the R390 datum
    spec = copy.deepcopy(BASELINE_SPEC)
    spec["segments"][0]["diameter_mm"] = 0.6  # the P-07 primary lumen
    g_true = pc.poiseuille_conductance(0.6, 90.0, 0.6913)
    q_true = g_true * 8.0 * 60.0
    m1 = {"value": q_true, "provenance_class": "MEASURED",
          "event_ref": "EVT-BENCH-1"}
    m2 = {"value": q_true, "provenance_class": "MEASURED",
          "event_ref": "EVT-BENCH-2"}
    r = rc.calibrate_model(spec, m1, m2)
    assert r["status"] == "CALIBRATION_COMPLETE"
    assert r["steps"]["ERROR_1"]["relative"] > 0.25  # ~31% discrepancy
    assert r["steps"]["PARAMETER_UPDATE"]["before"] == 1.0


# ---------------------------------------------------------------------------
# 15: successful model correction (quantified improvement)
# ---------------------------------------------------------------------------

def test_bench_15_successful_model_correction():
    spec = copy.deepcopy(BASELINE_SPEC)
    spec["segments"][0]["diameter_mm"] = 0.6
    g_true = pc.poiseuille_conductance(0.6, 90.0, 0.6913)
    q_true = g_true * 8.0 * 60.0
    m1 = {"value": q_true, "provenance_class": "MEASURED",
          "event_ref": "EVT-BENCH-1"}
    m2 = {"value": q_true, "provenance_class": "MEASURED",
          "event_ref": "EVT-BENCH-2"}
    r = rc.calibrate_model(spec, m1, m2)
    imp = r["improvement"]
    assert imp["improved"] is True
    assert imp["error_after"] < imp["error_before"]
    assert imp["improvement_ratio"] > 100.0  # 31% -> ~0%
    assert abs(r["steps"]["PARAMETER_UPDATE"]["after"] - 0.6913) < 1e-6


# ---------------------------------------------------------------------------
# 16: patent-replay recall (deterministic adjudication replay)
# ---------------------------------------------------------------------------

def test_bench_16_patent_replay_recall():
    mm = {"mechanism": "heparin coating reduces thrombus formation",
          "intervention": "covalently bonded heparin coating on the "
                          "catheter luminal surface",
          "expected_effect": "reduced occlusion"}
    problem = {"device": "tunneled hemodialysis catheter",
               "failure": "catheter occlusion loss of flow patency"}
    profile = cr.build_candidate_profile(mm, problem)
    hit = cr.PatentHit(patent_id="US1", title="catheter heparin study",
                       snippet="A" * 200, source_id="g", source_url="u",
                       query_class="ENTITY", query="q")
    fam = [{"family_id": "F1", "representative": hit, "members": [hit]}]
    recorded = cr.resolve_differentiation(fam, profile, [], True,
                                           deep_fetch=False)
    # replay: same inputs -> same decisions, no flag
    c = cr.check_replay_consistency(mm, problem, recorded)
    assert c["consistent"] is True and c["flag"] is None
    # tampered record -> flagged, never silently accepted
    tampered = copy.deepcopy(recorded)
    tampered["per_family"][0]["coverage"]["coverage_class"] = "FULL_COVER"
    c2 = cr.check_replay_consistency(mm, problem, tampered)
    assert c2["flag"] == "FLAG_INCONSISTENT_RETRIEVAL"


# ---------------------------------------------------------------------------
# 17: connector outage injection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exc,expected", [
    (socket.timeout("t"), "TIMEOUT"),
    (urllib.error.HTTPError("u", 504, "gw", {}, None), "PROVIDER_ERROR"),
    (urllib.error.HTTPError("u", 429, "rate", {}, None), "RATE_LIMITED"),
    (urllib.error.URLError("no route"), "UNAVAILABLE"),
])
def test_bench_17_connector_outage_injection(exc, expected):
    assert connector_states.classify_exception(exc) == expected
    with mock.patch.object(
            connector_states.urllib.request, "urlopen",
            side_effect=exc):
        r = connector_states.fetch_json("https://x.example/api", timeout=1)
    assert r["connector_state"] in connector_states.OUTAGE_STATES
    assert r["connector_state"] == expected or (
        expected == "TIMEOUT" and r["connector_state"] == "UNAVAILABLE")
    assert r["epistemic_effect"] == "UNKNOWN"  # never absence


def test_bench_17_outage_never_absence():
    """The load-bearing invariant: only EMPTY_RESULT (successful query,
    zero records) may mean absence. Every outage state is UNKNOWN."""
    for state in connector_states.OUTAGE_STATES:
        o = connector_states.outcome(state, "any")
        assert o["epistemic_effect"] == "UNKNOWN", state
    assert connector_states.outcome(
        "EMPTY_RESULT", "any")["epistemic_effect"] == "ABSENCE"


# ---------------------------------------------------------------------------
# 18: verdict-variance measurement
# ---------------------------------------------------------------------------

def test_bench_18_verdict_variance_measurement():
    """Deterministic layers: variance over N replays must be exactly 0.
    (The LLM synthesis layer is the disclosed non-deterministic layer —
    the verdict variance of the DETERMINISTIC instruments is what this
    benchmark pins; the directive's determinism contract applies to the
    relevance/verdict machinery given identical inputs.)"""
    mm = {"mechanism": "heparin coating reduces thrombus formation",
          "intervention": "covalently bonded heparin coating",
          "expected_effect": "reduced occlusion"}
    problem = {"device": "catheter", "failure": "occlusion"}
    hit = cr.PatentHit(patent_id="US1", title="catheter heparin study",
                       snippet="A" * 200, source_id="g", source_url="u",
                       query_class="ENTITY", query="q")
    fam = [{"family_id": "F1", "representative": hit, "members": [hit]}]
    states, hashes = [], []
    for _ in range(5):
        d = cr.resolve_differentiation(
            fam, cr.build_candidate_profile(mm, problem), [], True,
            deep_fetch=False)
        states.append(d["state"])
        hashes.append(pc.solve_network(CANDIDATE_SPEC)["output_hash"])
    assert len(set(states)) == 1
    assert len(set(hashes)) == 1
    # variance = 0 over the deterministic instruments
    variance = (len(set(states)) - 1) + (len(set(hashes)) - 1)
    assert variance == 0


# ---------------------------------------------------------------------------
# The multi-source discovery path (curl removal regression — the
# deployed FileNotFoundError class)
# ---------------------------------------------------------------------------

def test_multi_source_discovery_no_curl_dependency():
    """The deployed container has no curl binary; the old _curl_json
    subprocess failed EVERY public run (R394 PRODUCTION_AUDIT claim 1).
    The module must now use the Python HTTP stack."""
    import orchestrator.multi_source_discovery as msd
    import inspect
    src = inspect.getsource(msd)
    code = "\n".join(l for l in src.splitlines()
                     if not l.strip().startswith("#"))
    assert "import subprocess" not in code
    assert '["curl"' not in code and "'curl'" not in code
    # and the adapters carry it
    from discovery_fabric.engine.adapters import ADAPTERS
    assert "MULTI_SOURCE_DISCOVERY" in ADAPTERS


def test_multi_source_search_reports_connector_states():
    msd_mod = sys.modules["orchestrator.multi_source_discovery"] or \
        __import__("orchestrator.multi_source_discovery",
                   fromlist=["x"])
    with mock.patch.object(
            connector_states.urllib.request, "urlopen",
            side_effect=urllib.error.URLError("no route to host")):
        r = msd_mod.search_pubmed("catheter occlusion", 3)
    assert "connector_state" in r
    assert r.get("connector_state") in ("UNAVAILABLE_OR_TIMEOUT",)
    assert r.get("note") and "NOT absence" in r["note"]


# ---------------------------------------------------------------------------
# §2 hard-rule matrix (directive section 2: the five search situations)
# ---------------------------------------------------------------------------

def test_directive_2_search_situation_matrix():
    """Only the ACTUAL no-match case (all queries executed OK, zero
    results) may support a positive no-match claim."""
    # 1. one failed provider (all queries fail) -> SEARCH_FAILED
    calls = {"n": 0}

    def fail_first(url, timeout=20, context=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(url, 500, "boom", {}, None)
    with mock.patch.object(a2pa.urllib.request, "urlopen",
                           side_effect=fail_first):
        r = a2pa.search_prior_art_with_queries(["q1", "q2"])
    assert r["prior_art_status"] == "SEARCH_FAILED"

    # 2. one timeout -> SEARCH_FAILED with timeout recorded
    with mock.patch.object(a2pa.urllib.request, "urlopen",
                           side_effect=socket.timeout("t")):
        r = a2pa.search_prior_art_with_queries(["q1"])
    assert r["prior_art_status"] == "SEARCH_FAILED"
    assert r["search_execution"]["timeout_present"]

    # 3. partial source failure -> SEARCH_PARTIAL
    calls2 = {"n": 0}

    def partial(url, timeout=20, context=None):
        calls2["n"] += 1
        if calls2["n"] == 1:
            raise urllib.error.HTTPError(url, 504, "gw", {}, None)
        return io.BytesIO(json.dumps(
            {"resultList": {"result": []}}).encode())
    with mock.patch.object(a2pa.urllib.request, "urlopen",
                           side_effect=partial):
        r = a2pa.search_prior_art_with_queries(["q1", "q2"])
    assert r["prior_art_status"] == "SEARCH_PARTIAL"

    # 4. zero-result SUCCESSFUL search -> NO_MATCHING_EVIDENCE_FOUND
    with mock.patch.object(
            a2pa.urllib.request, "urlopen",
            side_effect=_mock_urlopen({"resultList": {"result": []}})):
        r = a2pa.search_prior_art_with_queries(["q1", "q2"])
    assert r["prior_art_status"] == "NO_MATCHING_EVIDENCE_FOUND"
    assert r["search_execution"]["n_failed"] == 0

    # 5. actual no-match result supports the (limited) no-match claim
    from discovery_fabric.engine.adapters import PRIOR_ART_STATUS_MAP
    assert PRIOR_ART_STATUS_MAP["NO_MATCHING_EVIDENCE_FOUND"][
        "mapped"] == "NO_MATCH_FOUND"
    assert PRIOR_ART_STATUS_MAP["SEARCH_FAILED"][
        "mapped"] == "UNRESOLVED_INSUFFICIENT_EVIDENCE"
    assert PRIOR_ART_STATUS_MAP["SEARCH_PARTIAL"][
        "mapped"] == "UNRESOLVED_PARTIAL_EVIDENCE"


def test_collision_run_collision_gates_on_search_errors():
    """run_collision must never let one surviving query 'succeed' the
    whole search (the measured searches_succeeded defect)."""
    profile_terms = cr.build_candidate_profile(
        {"mechanism": "heparin coating reduces thrombus",
         "intervention": "heparin coating",
         "expected_effect": "reduced occlusion"},
        {"device": "catheter", "failure": "occlusion"})
    ladder = cr.build_query_ladder(profile_terms)
    # 5 query classes x 2 sources = 10 mandatory pairs; 5 errors
    errors = [{"query": f"q{i}", "source": "lens_patent", "error": "429"}
              for i in range(5)]
    m = cr.mandatory_searches_complete(errors, ladder,
                                       ["google_patents", "lens_patent"])
    assert m["mandatory_pairs"] == len(ladder) * 2
    assert m["failed_pairs"] == 5
    assert m["complete"] is False

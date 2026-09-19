"""R510 adapter battery (Art V) — the authorized cliff-fix build's proof.

Covers the new mechanism_graph_from_fields() mapping + its wiring into the
dry-run adapter. Positive/negative/metamorphic cases are hand-built term sets
(unit-testing the mapping/adjudicator contract, never discovery claims);
the fixture pair uses R510/GRID_MECHANISM_FIXTURE.json (live grid refusal
bytes — corrected per auditor §4: refusal stays absence) plus genuine-text
positive controls. Frozen adjudicator thresholds untouched (0.45/0.8);
existing mechanism_space suites must stay green (guard is behavior-identical
on non-absence text).
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import mechanism_space as ms


def _cand(cid, graph, **kw):
    d = {"candidate_id": cid, "candidate_hash": "h:" + cid,
         "candidate_state": "CANDIDATE", "intervention": kw.get("intervention", ""),
         "mechanism_graph": graph}
    d.update(kw)
    return d


def _graph(**roles):
    return {"nodes": {r: {"terms": sorted(t)} for r, t in roles.items() if t},
            "edges": [], "derivation": "test"}


def test_mapping_empty_fields_stay_empty():
    g = ms.mechanism_graph_from_fields({})
    assert g["nodes"] == {} and g["edges"] == []


def test_mapping_uses_canonical_terms_only():
    g = ms.mechanism_graph_from_fields({"mechanism": "The Dialyzer Membrane Fouls"})
    terms = g["nodes"]["mechanism"]["terms"]
    assert terms and all(t == t.lower() for t in terms)
    assert "the" not in terms  # stopwords removed by canonical tokenizer


def test_old_mapping_yields_empty_core():
    # Pre-fix behavior pinned as the failure mode: no graph -> core_j None.
    a = _cand("a", {}, intervention="x")
    b = _cand("b", {}, intervention="y")
    cmp = ms.compare_candidates(a, b)
    assert cmp["verdict"] == "INDETERMINATE"
    assert "empty" in cmp["basis"]


def test_positive_disjoint_cores_distinct():
    a = _cand("a", _graph(mechanism={"electrostatic", "precipitator", "corona",
                                     "discharge", "collector", "migration"}))
    b = _cand("b", _graph(mechanism={"heparin", "coating", "anticoagulant",
                                     "graft", "thrombosis", "elution"}))
    cmp = ms.compare_candidates(a, b)
    assert cmp["verdict"] == "DISTINCT", cmp["basis"]


def test_negative_identical_equivalent():
    g = _graph(mechanism={"catheter", "occlusion", "thrombus"})
    assert ms.compare_candidates(_cand("a", g),
                                 _cand("b", g))["verdict"] == "EQUIVALENT"


def test_negative_knob_only_equivalent():
    g = _graph(mechanism={"catheter", "occlusion", "thrombus"})
    a = _cand("a", g, novel_design_variable="diameter 2mm")
    b = _cand("b", g, novel_design_variable="diameter 4mm")
    cmp = ms.compare_candidates(a, b)
    assert cmp["verdict"] == "EQUIVALENT", cmp["basis"]


def test_metamorphic_rewording_never_creates_distinct():
    g1 = _graph(mechanism={"catheter", "occlusion", "thrombus", "flow"})
    g2 = _graph(mechanism={"catheter", "occlusion", "thrombus", "stream"})
    cmp = ms.compare_candidates(_cand("a", g1), _cand("b", g2))
    assert cmp["verdict"] in ("EQUIVALENT", "INDETERMINATE")
    assert cmp["verdict"] != "DISTINCT"


def test_falsifier_fixture_refusal_stays_absence():
    # CORRECTED (auditor §4 order; was asserting non-empty nodes on
    # refusal bytes): the R510/GRID_MECHANISM_FIXTURE.json entries are
    # explicit refusal text ("No mechanism can be extracted...",
    # "source text is missing", ...). Absence must remain absence —
    # refusal-shaped fields yield EMPTY node sets, never graph
    # vocabulary. The fixture file itself is frozen evidence and is
    # NOT modified; only this test's assertions change, for the
    # recorded reason.
    fx = json.loads((REPO / "R510" / "GRID_MECHANISM_FIXTURE.json").read_text(
        encoding="utf-8"))["entries"]
    assert len(fx) >= 2
    graphs = [ms.mechanism_graph_from_fields(e["fields"]) for e in fx[:2]]
    assert all(g["nodes"] == {} for g in graphs), (
        "refusal text became graph terms: %s"
        % [g["nodes"] for g in graphs])
    assert all(g["edges"] == [] for g in graphs)


def test_falsifier_genuine_content_stays_measurable():
    # Positive control kept: genuine mechanism-bearing text still
    # produces a non-empty, comparable core (the helper's purpose).
    a = ms.mechanism_graph_from_fields(
        {"mechanism": "pump cavitation erosion pits the inducer",
         "intervention": "inducer leading-edge redesign",
         "expected_effect": "erosion rate falls"})
    b = ms.mechanism_graph_from_fields(
        {"mechanism": "heparin coating elutes anticoagulant",
         "intervention": "graft surface coating",
         "expected_effect": "thrombosis rate falls"})
    assert a["nodes"] and b["nodes"]
    import re
    basis = ms.compare_candidates(_cand("f0", a),
                                  _cand("f1", b))["basis"]
    assert re.search(r"Jaccard (None|0\.\d+)", basis), basis


def test_absence_guard_cases():
    # The ordered absence vocabulary (data v1): refusal shapes stay
    # empty; a legitimate negative RESULT still tokenizes (it is
    # evidence content, not extraction failure).
    assert ms.mechanism_graph_from_fields(
        {"mechanism": "No mechanism can be extracted because the "
                      "source text is empty."})["nodes"] == {}
    assert ms.mechanism_graph_from_fields(
        {"mechanism": "UNEXTRACTED"})["nodes"] == {}
    assert ms.mechanism_graph_from_fields(
        {"intervention": "None derivable — no design change present "
                         "in the source."})["nodes"] == {}
    legit = ms.mechanism_graph_from_fields(
        {"expected_effect": "no effect was observed at low doses"})
    assert legit["nodes"], "legitimate negative results must tokenize"


def test_dryrun_wiring_includes_graph():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r510dry", str(REPO / "scripts" / "r510_diversity_dryrun.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    m = mod.to_mechanism({"fields": {"mechanism": "pump cavitation erosion",
                                     "intervention": "inducer redesign"},
                          "candidate_id": "c", "prompt_hash": "p"}, "x")
    assert "mechanism_graph" in m
    assert m["mechanism_graph"]["nodes"]

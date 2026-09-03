"""R401 Phases 8/10/11 — pinned tests: operator fidelity (wording FAILS),
material distinctness, mechanism-level verification. Offline, deterministic."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discovery_fabric.mechanism_space import (
    apply_operator, operator_fidelity, structural_dedup,
    verify_mechanism_evidence, structure_hash, content_hash)
from discovery_fabric.mechanism_space.heldout import (
    seed_candidate, operator_calls, to_evidence_records)


def _m1():
    return seed_candidate()


# ------------------------------------------------- Phase 8: all five operators
def test_all_five_operators_pass_fidelity():
    m1 = _m1()
    for op, base, params in operator_calls(m1):
        m2 = apply_operator(op, base, **params)
        v = operator_fidelity(m1, m2, op)
        assert v["verdict"] == "PASS", (op, v)


def test_wording_change_fails_every_operator():
    m1 = _m1()
    for op, _, _ in operator_calls(m1):
        m2 = copy.deepcopy(m1)
        m2["description"] = m1.get("description", "") + " rewritten prose"
        m2["notes"] = "expanded paragraph that says the same thing at greater length"
        v = operator_fidelity(m1, m2, op)
        assert v["verdict"] == "FAIL" and "WORDING" in v["reason"], (op, v)


def test_synonym_swap_fails_direct_transfer():
    """Same structure, one node label paraphrased, system UNCHANGED ->
    not a transfer. A synonym change FAILS."""
    m1 = _m1()
    m2 = copy.deepcopy(m1)
    for n in m2["mechanism_graph"]["nodes"]:
        if n["id"] == "n6":
            n["label"] = "elevated electrical resistance at the joint"
    v = operator_fidelity(m1, m2, "DIRECT_TRANSFER")
    assert v["verdict"] == "FAIL"


def test_structure_change_fails_direct_transfer():
    m1 = _m1()
    m2 = copy.deepcopy(m1)
    m2["system"] = "a different system"
    m2["mechanism_graph"]["edges"].append(
        {"src": "n6", "dst": "n1", "rel": "FEEDBACK"})
    v = operator_fidelity(m1, m2, "DIRECT_TRANSFER")
    assert v["verdict"] == "FAIL"


def test_paragraph_expansion_fails_cross_domain_analogy():
    m1 = _m1()
    m2 = copy.deepcopy(m1)
    m2["system"] = m1["system"] + " [analogue: glacial geology]"
    m2["rationale"] = "long paragraph explaining why glaciers are like connectors " + "x" * 400
    v = operator_fidelity(m1, m2, "CROSS_DOMAIN_ANALOGY")
    assert v["verdict"] == "FAIL"  # <2 nodes rebound -> not an analogy


def test_single_node_relabel_fails_cross_domain_analogy():
    m1 = _m1()
    m2 = copy.deepcopy(m1)
    for n in m2["mechanism_graph"]["nodes"]:
        if n["id"] == "n4":
            n["label"] = "rock asperity adhesion"
    m2["derivation_trace"] = {"mapping": {"metal-to-metal": "rock asperity"},
                              "rebound_nodes": ["n4"]}
    v = operator_fidelity(m1, m2, "CROSS_DOMAIN_ANALOGY")
    assert v["verdict"] == "FAIL"  # only 1 node rebound


def test_geometry_operator_confined_to_geometry_nodes():
    m1 = _m1()
    m2 = copy.deepcopy(m1)
    for n in m2["mechanism_graph"]["nodes"]:
        if n["id"] == "n3":  # PHENOMENON node changed — must FAIL
            n["label"] = "oxide film rupture (reworded)"
    v = operator_fidelity(m1, m2, "GEOMETRIC_TRANSFORMATION")
    assert v["verdict"] == "FAIL"


def test_bc_change_without_prediction_change_fails():
    m1 = _m1()
    m2 = copy.deepcopy(m1)
    m2["boundary_conditions"] = {"vibration": "zero slip"}
    v = operator_fidelity(m1, m2, "BOUNDARY_CONDITION_CHANGE")
    assert v["verdict"] == "FAIL"


def test_inversion_without_design_variable_fails():
    m1 = _m1()
    m2 = copy.deepcopy(m1)
    for e in m2["mechanism_graph"]["edges"]:
        if (e["src"], e["dst"]) == ("n5", "n6"):
            e["rel"] = "INHIBITS"
    v = operator_fidelity(m1, m2, "FAILURE_PATH_INVERSION")
    assert v["verdict"] == "FAIL"


def test_prediction_must_differ_between_m1_and_bc_m2():
    m1 = _m1()
    m2 = apply_operator("BOUNDARY_CONDITION_CHANGE", m1,
                        new_bc={"vibration": "full-stick preload"},
                        new_predicted_effect="resistance stable")
    assert m1["predicted_effect"] != m2["predicted_effect"]


# ------------------------------------------------- Phase 10: distinctness
def test_linguistic_variant_collapses():
    m1 = _m1()
    variant = copy.deepcopy(m1)
    variant["id"] = "M1_paraphrase"
    for n in variant["mechanism_graph"]["nodes"]:
        n["label"] = n["label"].replace("contact", "interface contact")
    out = structural_dedup([m1, variant])
    assert out["stats"]["deduplicated"] == 1
    led = [l for l in out["ledger"] if l["action"] == "DEDUPED"][0]
    assert "LINGUISTIC VARIANT" in led["reason"]
    assert led["reference"] == "M1_seed"


def test_different_structure_preserved():
    m1 = _m1()
    m2 = apply_operator("FAILURE_PATH_INVERSION", m1,
                        edge_to_invert=("n5", "n6"),
                        design_variable="engineered tribofilm",
                        new_predicted_effect="low stable resistance",
                        new_purpose="debris as lubricant reserve")
    out = structural_dedup([m1, m2])
    assert out["stats"]["kept"] == 2  # materially distinct — preserved


def test_five_operator_outputs_are_materially_distinct():
    m1 = _m1()
    m2s = [apply_operator(op, base, **p) for op, base, p in operator_calls(m1)]
    out = structural_dedup([m1] + m2s)
    assert out["stats"]["kept"] >= 5  # seed + 5 operator outputs


# --------------------------------------- Phase 11: mechanism-level verification
EV_MECH = evidence_like = {
    "source": "openalex:W1",
    "claim": "Fretting corrosion at electrical contacts",
    "observed_effect": "contact resistance rise in connectors under vibration",
    "system": "EV connector",
    "mechanism": "micro-slip at contact spots disrupts oxide films causing "
                 "metal-to-metal adhesion and wear debris accumulation which "
                 "raises contact resistance",
    "provenance": {"provider": "OpenAlex"},
}
EV_PHENOMENON_ONLY = {
    "source": "openalex:W2",
    "claim": "Connector degradation review",
    "observed_effect": "contact resistance rise in EV charging",
    "system": "EV connector",
    "mechanism": "thermal cycling in charging infrastructure affects "
                 "long-term infrastructure economics",
    "provenance": {"provider": "OpenAlex"},
}
EV_CONTRARY = {
    "source": "openalex:W3",
    "claim": "Preloaded contacts show no effect of vibration on resistance",
    "observed_effect": "contact resistance rise studied under vibration",
    "system": "EV connector",
    "mechanism": "micro-slip at contact spots disrupts oxide films; debris "
                 "accumulation raises contact resistance; however preloaded "
                 "contacts show no effect of vibration on resistance",
    "contrary": True,
    "provenance": {"provider": "OpenAlex"},
}


def test_phenomenon_support_is_not_mechanism_support():
    m1 = _m1()
    r = verify_mechanism_evidence([EV_PHENOMENON_ONLY], m1)
    assert r["bundle_verdict"] == "PHENOMENON_LEVEL_ONLY"
    v = r["per_evidence"][0]["verdict"]
    assert v == "NOT_ENOUGH_EVIDENCE"  # topic match, zero causal pairs


def test_causal_overlap_supports():
    m1 = _m1()
    r = verify_mechanism_evidence([EV_MECH, EV_MECH | {"source": "openalex:W1b"}], m1)
    assert r["bundle_verdict"] == "SUPPORTED"
    assert r["counts"]["SUPPORTS"] >= 1


def test_contrary_evidence_contradicts():
    m1 = _m1()
    r = verify_mechanism_evidence([EV_MECH, EV_CONTRARY], m1)
    assert r["bundle_verdict"] == "CONTRADICTED"
    assert r["counts"]["CONTRADICTS"] == 1


def test_off_topic_is_irrelevant():
    m1 = _m1()
    ev = {"source": "x:1", "claim": "coral reef bleaching",
          "observed_effect": "reef mortality", "system": "ocean",
          "mechanism": "thermal stress symbiont expulsion",
          "provenance": {}}
    r = verify_mechanism_evidence([ev], m1)
    assert r["per_evidence"][0]["verdict"] == "IRRELEVANT"

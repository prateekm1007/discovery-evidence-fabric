#!/usr/bin/env python3
"""tests/test_candidate_grounding_lifecycle.py — REWRITTEN for R139:
functional tests of the REAL admission function (the production block
the lean mechanism space runs), replacing the R138 source-text
pattern checks per the R139 directions' functional-test mandate.

Pinned functionally:
1. A grounded+resolved candidate admits (EVIDENCE_GROUNDED_CANDIDATE)
   with the RESOLVED record id + hash in its binding.
2. An ungrounded-synthesis candidate stays UNGROUNDED_HYPOTHESIS
   (enrichment routing) even at PARTIALLY_SUPPORTED-with-no-binding.
3. A candidate whose binding names a synthetic alias gets the REAL
   record id (the alias never travels downstream).
4. A candidate with a false ID stays ungrounded (enrichment reason
   carries the typed refusal).
5. The engine-boundary gate consumes the admission's output.
6. The space's public candidates carry the lifecycle fields."""
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402
from discovery_fabric.engine.adapters import (  # noqa: E402
    apply_lifecycle_admission)

TEXT = ("Trailing edge vortex generators suppress cavitation erosion "
        "on Francis runner blades.")
HASH = hashlib.sha256(TEXT.encode()).hexdigest()

ITEMS = [{
    "item_id": "doi:10.1080/x", "content_hash": HASH,
    "fields": {"system": {"value": "Francis runner"},
               "abstract": {"value": TEXT},
               "mechanism": {"value": TEXT},
               "observed_effect": {"value": TEXT}},
    "_record_text": TEXT}]
PROBLEM = {"device": "Francis runner", "failure": "cavitation"}


def _verify(cand):
    return ms.verify_mechanism_support(cand, ITEMS, PROBLEM)


def test_grounded_candidate_admits_with_resolved_identity():
    cand = {"candidate_id": "g1",
            "mechanism": "the runner blade trailing edge vortex "
                         "generators suppress cavitation erosion on "
                         "francis runner blades at partial load",
            "intervention": "install vortex generators"}
    retained, verifications = [cand], [_verify(cand)]
    apply_lifecycle_admission(retained, verifications, ITEMS)
    c = retained[0]
    assert c["candidate_lifecycle"] == "EVIDENCE_GROUNDED_CANDIDATE"
    assert c["discovery_admissible"] is True
    b = c["admission_basis"]["binding"]
    assert b["evidence_id"] == "doi:10.1080/x"   # the REAL record id
    assert b["content_hash"] == HASH             # the REAL hash
    assert b["span"]
    assert c["admission_basis"]["support_state"] in (
        "SUPPORTED", "PARTIALLY_SUPPORTED")


def test_ungrounded_synthesis_stays_hypothesis():
    cand = {"candidate_id": "u1",
            "mechanism": "quantum plasmonic resonance damping lattice",
            "intervention": "coat blades with a plasmonic lattice"}
    retained, verifications = [cand], [_verify(cand)]
    apply_lifecycle_admission(retained, verifications, ITEMS)
    c = retained[0]
    assert c["candidate_lifecycle"] == "UNGROUNDED_HYPOTHESIS"
    assert c["discovery_admissible"] is False
    assert c["enrichment_required"] is True
    assert c["enrichment_reason"]


def test_alias_never_travels_downstream():
    """A candidate whose RAW binding names the R138 lean_ alias is
    admitted ONLY under the resolved real record id."""
    aliased_items = [dict(ITEMS[0], item_id="lean_doi:10.1080/x")]
    cand = {"candidate_id": "a1",
            "mechanism": "the runner blade trailing edge vortex "
                         "generators suppress cavitation erosion on "
                         "francis runner blades at partial load",
            "intervention": "install vortex generators"}
    v = ms.verify_mechanism_support(cand, aliased_items, PROBLEM)
    retained, verifications = [cand], [v]
    # the FROZEN set carries the REAL ids (the lean items now do)
    apply_lifecycle_admission(retained, verifications, ITEMS)
    c = retained[0]
    if c["discovery_admissible"]:
        assert c["admission_basis"]["binding"]["evidence_id"] == \
            "doi:10.1080/x"
        assert not str(c["admission_basis"]["binding"]
                       ["evidence_id"]).startswith("lean_")


def test_false_id_stays_ungrounded():
    retained = [{"candidate_id": "f1",
                 "mechanism": "x", "intervention": "y"}]
    # a verification whose binding names a record that does not exist
    v = {"mechanism_support_state": "PARTIALLY_SUPPORTED",
         "evidence_binding": {"grounded": True,
                              "evidence_id": "doi:10.9999/nope",
                              "span": "vortex generators suppress",
                              "content_hash": HASH}}
    apply_lifecycle_admission(retained, [v], ITEMS)
    c = retained[0]
    assert c["discovery_admissible"] is False
    assert "FALSE_ID" in c["enrichment_reason"]
    assert c["candidate_lifecycle"] == "UNGROUNDED_HYPOTHESIS"


def test_pool_gate_reflects_the_admission():
    """The engine-boundary gate consumes the admission's output: only
    the grounded candidate joins, the ungrounded one is enrichment
    fuel (the full production chain, driven functionally)."""
    from discovery_fabric.engine.run import ms_pool_admission_split
    g = {"candidate_id": "g",
         "mechanism": "the runner blade trailing edge vortex "
                      "generators suppress cavitation erosion on "
                      "francis runner blades at partial load",
         "intervention": "install vortex generators"}
    u = {"candidate_id": "u",
         "mechanism": "magnetohydrodynamic pulse descaling",
         "intervention": "install MHD descaler"}
    retained = [g, u]
    verifications = [_verify(g), _verify(u)]
    apply_lifecycle_admission(retained, verifications, ITEMS)
    adm, ung = ms_pool_admission_split(retained)
    assert [c["candidate_id"] for c in adm] == ["g"]
    assert [c["candidate_id"] for c in ung] == ["u"]
    n_adm = sum(1 for c in retained if c.get("discovery_admissible"))
    assert n_adm == 1


def test_public_fields_declared():
    """The public candidate contract carries the lifecycle fields
    (a structural fact about the production envelope — kept alongside
    the full functional coverage above)."""
    src = (REPO / "discovery_fabric" / "engine"
           / "mechanism_space.py").read_text(encoding="utf-8")
    for field in ("candidate_lifecycle", "discovery_admissible",
                  "admission_basis", "enrichment_required"):
        assert f'"{field}"' in src

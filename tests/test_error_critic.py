#!/usr/bin/env python3
"""tests/test_error_critic.py — zero-LLM pins for the DIR-3 critic
(deterministic: the flag parse, the merge algebra, the refusal paths)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import error_critic as ec  # noqa: E402

PROBLEM = {
    "device": "test cell",
    "failure": "a plateau",
    "constraint": "earth-abundant only",
    "question": "propose a new mechanism",
}


def test_flag_parse_takes_json_only_and_validates_classes():
    raw = ('{"flags": [{"class": "PHYS", "reason": "wrong sign"}, '
           '{"class": "STYLE", "reason": "bogus"}, '
           '{"class": "LOGIC", "reason": ""}]}')
    flags = ec._parse_flags(raw)
    assert [f["class"] for f in flags] == ["PHYS", "LOGIC"]
    assert flags[1]["reason"] == "(no reason given)"


def test_flag_parse_rejects_prose_garbage():
    assert ec._parse_flags("no json here") == []
    assert ec._parse_flags("") == []


def test_union_and_intersection_algebra():
    a = [{"class": "PHYS", "reason": "r1"},
         {"class": "LOGIC", "reason": "r2"}]
    b = [{"class": "PHYS", "reason": "r1"},
         {"class": "CONSTR", "reason": "r3"}]
    u = ec._merge_flags(a, b, op="union")
    i = ec._merge_flags(a, b, op="intersection")
    assert sorted(f["class"] for f in u) == ["CONSTR", "LOGIC", "PHYS"]
    # intersection keeps only classes BOTH raised
    assert sorted(f["class"] for f in i) == ["PHYS"]


def test_run_critic_refused_on_unknown_variant_or_missing_key():
    out = ec.run_critic("bogus", PROBLEM, "text", lambda *a: "",
                        {}, "hy4-flash-centai")
    assert out["status"] == "REFUSED" and out["flags"] == []
    out2 = ec.run_critic("checklist", PROBLEM, "text", lambda *a: "",
                         {}, "hy4-flash-centai")
    assert out2["status"] == "REFUSED"  # no key in the env map


def test_run_critic_transport_failure_is_typed_not_raised():
    def boom(*a):
        raise RuntimeError("HTTP 500")
    out = ec.run_critic("checklist", PROBLEM, "text", boom,
                        {"CENT_AI_API_KEY": "k"},
                        "hy4-flash-centai")
    assert out["status"] == "TRANSPORT_FAILED"
    assert out["flags"] == [] and out["serious"] is False


def test_two_family_variants_need_both_keys():
    out = ec.run_critic("union", PROBLEM, "text", lambda *a: "",
                        {"CENT_AI_API_KEY": "k"},
                        "hy4-flash-centai")
    assert out["status"] == "REFUSED"
    assert "both keys" in out["reason"]


def test_checklist_prompt_carries_packet_and_taxonomy():
    p = ec._checklist_prompt(PROBLEM, "the proposal body")
    for token in ("PHYS", "CONSTR", "LOGIC", "INCOMPLETE",
                  "earth-abundant only", "the proposal body",
                  "PROBLEM PACKET", "PROPOSAL"):
        assert token in p, token

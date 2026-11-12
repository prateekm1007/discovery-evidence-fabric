"""tests/test_r6_attack_batch.py — offline pins for the batched
independent attack (owner directive 3, 2026-11-12): ONE call carries
every candidate; per-candidate records keep the independent_attack
shape; an unreadable section is typed ATTACK_INCOMPLETE (never a kill,
Art. XXIX)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.independent_attack import (  # noqa: E402
    independent_attack_batch, ATTACK_BATCH_VERSION)

PROBLEM = {"device": "condenser", "failure": "fouling",
           "constraint": "temperature and flow only",
           "baseline_text": "monthly cleaning"}

CANDS = [
    {"candidate_id": "cand-A",
     "mechanism": "fouling index from temperature differential",
     "intervention": "clean when index exceeds baseline + 3 sigma",
     "predicted_effect": "3 percent compressor energy reduction",
     "testable_prediction": "shadow-mode alert precedes fouling",
     "known_failure_modes": [], "constraint_set": {}},
    {"candidate_id": "cand-B",
     "mechanism": "tanh-weighted pressure error modulation",
     "intervention": "tanh feedback on the pressure setpoint",
     "predicted_effect": "earlier derating warning",
     "testable_prediction": "closed-loop step test",
     "known_failure_modes": [], "constraint_set": {}},
]

RESPONSE = """== CANDIDATE cand-A ==
MECHANISM_FAILURE: SURVIVE — consistent with held records
BOUNDARY_CONDITION_FAILURE: SURVIVE — inside the declared range
EVIDENCE_CONTRADICTION: SURVIVE — no contradiction found
BASELINE_EQUIVALENCE: RISK — the fixed monthly cadence may already be near-optimal at low fouling rates GROUNDED_IN: COMPUTATION 3 percent vs monthly cadence
IMPLEMENTATION_IMPOSSIBILITY: SURVIVE — logged points suffice
MEASUREMENT_AMBIGUITY: SURVIVE — differential is instrumented

== CANDIDATE cand-B ==
MECHANISM_FAILURE: KILL — the tanh weighting adds no information beyond the unweighted error and cannot be derived from any held record GROUNDED_IN: RECORD "tanh-weighted pressure error modulation"
BOUNDARY_CONDITION_FAILURE: SURVIVE — n/a
EVIDENCE_CONTRADICTION: SURVIVE — n/a
BASELINE_EQUIVALENCE: SURVIVE — n/a
IMPLEMENTATION_IMPOSSIBILITY: SURVIVE — n/a
MEASUREMENT_AMBIGUITY: SURVIVE — n/a
"""


def _ok_meta(*a, **k):
    return {"ok": True, "content": RESPONSE, "provider": "zai",
            "model": "glm-4-plus", "prompt_hash": "p" * 8,
            "output_hash": "o" * 8, "status": "OK"}


def test_batch_one_call_two_records():
    calls = {"n": 0}

    def llm(prompt, **kw):
        calls["n"] += 1
        return _ok_meta()

    out = independent_attack_batch(CANDS, PROBLEM, [], None,
                                   llm_generate=llm)
    assert calls["n"] == 1, "ONE call for both candidates"
    assert out["batch"] is True
    assert out["batch_version"] == ATTACK_BATCH_VERSION
    assert set(out["records"].keys()) == {"cand-A", "cand-B"}
    a, b = out["records"]["cand-A"], out["records"]["cand-B"]
    assert a["overall"] == "UNCERTAIN" and a["state"] == "ATTACK_RUN"
    assert b["overall"] == "KILLED" and b["kill_basis"]
    # per-candidate record shape is the independent_attack shape
    for rec in (a, b):
        assert rec["attack_version"].startswith("independent_attack/")
        assert rec["independence_mode"] in ("SEPARATE_PROVIDER",
                                            "SEPARATE_CONTEXT")
        assert "items" in rec and "counts" in rec


def test_batch_transport_failure_is_attack_incomplete():
    def llm(prompt, **kw):
        return {"ok": False, "status": "PROVIDER_UNAVAILABLE",
                "content": None, "error": "no rung"}

    out = independent_attack_batch(CANDS, PROBLEM, [], None,
                                   llm_generate=llm)
    for cid in ("cand-A", "cand-B"):
        rec = out["records"][cid]
        assert rec["overall"] == "ATTACK_INCOMPLETE"
        assert rec["state"] == "ATTACK_INCOMPLETE"
        assert rec["items"] == []


def test_missing_section_never_kills():
    def llm(prompt, **kw):
        return _ok_meta().copy() | {"content": "== CANDIDATE cand-A ==\n"
                                    "MECHANISM_FAILURE: SURVIVE — ok\n"}

    out = independent_attack_batch(CANDS, PROBLEM, [], None,
                                   llm_generate=llm)
    assert out["unparsed"] == ["cand-B"]
    assert out["records"]["cand-B"]["overall"] == "ATTACK_INCOMPLETE"
    assert out["records"]["cand-B"]["note"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

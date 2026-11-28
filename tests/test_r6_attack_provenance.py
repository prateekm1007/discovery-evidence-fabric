"""tests/test_r6_attack_provenance.py — owner audit round 2026-11-13.

Pins:
  1. The batched independent attack carries EACH candidate's OWN
     generator provider. The old engine passed `_gens[0]` into the batch,
     so every candidate was labelled with the first candidate's
     generator — a false independence attestation.
  2. Independence is computed against the ACTUALLY SERVED attacker, per
     candidate: a candidate generated on the same provider is
     SEPARATE_CONTEXT (never SEPARATE_PROVIDER); a candidate generated on
     a different provider is SEPARATE_PROVIDER.
  3. Every attack record carries a DERIVED calibration attestation for
     its own instrument version. An unmeasured version is
     UNKNOWN_NOT_CALIBRATED — never an implied clean bill.
  4. The batch call excludes EVERY candidate's generator provider.

Hermetic: the LLM call site is injected; zero network.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import independent_attack as ia  # noqa: E402

PROBLEM = {
    "problem_id": "r6_attack_prov",
    "device": "tunneled hemodialysis catheter",
    "failure": "thrombotic occlusion of the catheter lumen",
}


def _failing_llm(seen):
    def _gen(prompt, system="", purpose="independent_attack",
             exclude_providers=None, max_tokens=0, **kwargs):
        seen["exclude_providers"] = exclude_providers
        return {"ok": False, "status": "CALL_FAILED", "provider": "zai",
                "model": "glm-4-plus", "content": None,
                "error": "simulated transport failure"}
    return _gen


def test_batch_uses_per_candidate_generator_provider():
    seen = {}
    out = ia.independent_attack_batch(
        [{"candidate_id": "cand:MS:A", "mechanism": "m1"},
         {"candidate_id": "cand:MS:B", "mechanism": "m2"}],
        PROBLEM, [],
        generator_provider="zai",
        generator_providers={"cand:MS:A": "zai",
                             "cand:MS:B": "xkiro"},
        llm_generate=_failing_llm(seen))
    recs = out["records"]
    assert recs["cand:MS:A"]["generator_provider"] == "zai"
    assert recs["cand:MS:B"]["generator_provider"] == "xkiro"
    # attacker was served by zai (same as A, different from B)
    assert recs["cand:MS:A"]["independence_mode"] == "SEPARATE_CONTEXT"
    assert recs["cand:MS:B"]["independence_mode"] == "SEPARATE_PROVIDER"
    assert out["transport"]["independence_by_candidate"] == {
        "cand:MS:A": "SEPARATE_CONTEXT",
        "cand:MS:B": "SEPARATE_PROVIDER"}
    # the batch excludes EVERY candidate generator
    assert set(seen["exclude_providers"]) == {"xkiro", "zai"}


def test_batch_never_claims_separate_provider_when_any_candidate_shares():
    seen = {}
    out = ia.independent_attack_batch(
        [{"candidate_id": "c1", "mechanism": "m1"},
         {"candidate_id": "c2", "mechanism": "m2"}],
        PROBLEM, [], generator_provider="zai",
        generator_providers={"c1": "zai", "c2": "zai"},
        llm_generate=_failing_llm(seen))
    assert out["transport"]["independence_mode"] == "SEPARATE_CONTEXT"


def test_attack_records_carry_derived_calibration_attestation():
    seen = {}
    out = ia.independent_attack_batch(
        [{"candidate_id": "c1", "mechanism": "m1"}],
        PROBLEM, [], generator_provider="zai",
        llm_generate=_failing_llm(seen))
    cal = out["records"]["c1"]["calibration"]
    assert cal["instrument"] == ia.ATTACK_VERSION
    # The committed measurement exists and MEASURED FAILURE: FPR 0.75 >
    # the sealed 0.30 bar. Either NOT_CALIBRATED (measured fail) or
    # UNKNOWN_NOT_CALIBRATED (unmeasured) is honest; CALIBRATED is not.
    assert cal["state"] in ("NOT_CALIBRATED", "UNKNOWN_NOT_CALIBRATED")
    assert cal["terminal_kill_admissible"] is False
    assert cal["state"] != "CALIBRATED"


def test_unknown_generator_is_unavailable_not_separate():
    seen = {}
    out = ia.independent_attack_batch(
        [{"candidate_id": "c1", "mechanism": "m1"}],
        PROBLEM, [], generator_provider=None,
        llm_generate=_failing_llm(seen))
    assert out["records"]["c1"]["independence_mode"] == "UNAVAILABLE"
    assert out["transport"]["independence_mode"] == "SEPARATE_CONTEXT"

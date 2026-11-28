"""R9 P0 item 4 pins (owner round 2026-11-13): the batched independent
attack computes independence PER CANDIDATE, excludes EVERY generator
provider in the batch, and splits large batches into bounded measured
groups.

Hermetic (no LLM, no network): the llm_generate seam is injected.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import independent_attack as ia  # noqa: E402


def _fake_llm(capture: list):
    def _lg(prompt, system="", max_tokens=0, purpose=None,
            exclude_providers=None, **kw):
        capture.append({"prompt": prompt, "purpose": purpose,
                        "exclude_providers": exclude_providers,
                        "max_tokens": max_tokens})
        # deterministic parseable sections for whatever is asked
        import re
        # the real prompt numbers sections by INDEX: '== CANDIDATE {idx}
        # == (id: {cid})' — emit parseable sections keyed the same way
        pairs = re.findall(r"== CANDIDATE (\d+) == \(id: (\S+)\)", prompt)
        parts = []
        for idx, cid in pairs:
            parts.append(f"== CANDIDATE {idx} ==\n"
                         "ATTACK_CLASS: boundary_violation\n"
                         "VERDICT: SURVIVE\n"
                         "BASIS: none found\n"
                         "GROUNDED_IN: [src-1]\n")
        return {"ok": True, "content": "\n".join(parts),
                "provider": "judgeprov", "model": "judgemodel",
                "prompt_hash": "ph", "output_hash": "oh",
                "status": "OK"}
    return _lg


def _cand(cid: str, gen: str) -> dict:
    return {"candidate_id": cid, "mechanism": "m " + cid,
            "intervention": "i", "predicted_effect": "e",
            "testable_prediction": "t",
            "known_failure_modes": [], "generator_provider": gen}


PROBLEM = {"device": "d", "failure": "f", "baseline": "b"}


def test_per_candidate_independence_and_batch_wide_exclusion():
    capture: list = []
    cands = [_cand("c1", "gen_a"), _cand("c2", "gen_b")]
    out = ia.independent_attack_batch(
        cands, PROBLEM, [], "gen_a", llm_generate=_fake_llm(capture),
        generator_providers=["gen_a", "gen_b"], group_size=2)
    # the attacker must be excluded from EVERY generator in the batch
    assert capture, "no transport call made"
    assert set(capture[0]["exclude_providers"]) == {"gen_a", "gen_b"}
    # per-candidate independence: each record names ITS OWN generator
    r1 = out["records"]["c1"]
    r2 = out["records"]["c2"]
    assert r1["generator_provider"] == "gen_a"
    assert r2["generator_provider"] == "gen_b"
    assert r1["independence_mode"] == "SEPARATE_PROVIDER"
    assert r2["independence_mode"] == "SEPARATE_PROVIDER"
    assert "gen_b" in r2["independence_note"]


def test_cascade_fallback_onto_a_generator_is_typed_shared():
    capture: list = []

    def _lg(prompt, system="", max_tokens=0, purpose=None,
            exclude_providers=None, **kw):
        capture.append(exclude_providers)
        return {"ok": True, "content": "", "provider": "gen_b",
                "model": "m", "prompt_hash": "ph", "output_hash": "oh",
                "status": "OK"}
    cands = [_cand("c1", "gen_a"), _cand("c2", "gen_b")]
    out = ia.independent_attack_batch(
        cands, PROBLEM, [], "gen_a", llm_generate=_lg,
        generator_providers=["gen_a", "gen_b"], group_size=2)
    # the cascade fell back onto gen_b (a generator): SHARED, never
    # labeled independent (Art. XLV)
    for cid in ("c1", "c2"):
        assert out["records"][cid]["independence_mode"] == \
            "SHARED_WITH_A_GENERATOR"
    assert out["transport"]["independence_mode"] == \
        "SHARED_WITH_A_GENERATOR"


def test_large_batches_split_into_bounded_measured_groups():
    capture: list = []
    cands = [_cand(f"c{i}", "gen_a") for i in range(1, 6)]  # 5 candidates
    out = ia.independent_attack_batch(
        cands, PROBLEM, [], "gen_a", llm_generate=_fake_llm(capture),
        generator_providers=["gen_a"], group_size=2)
    # 5 candidates at group_size 2 -> 3 measured transport calls
    assert len(capture) == 3
    assert len(out["transports"]) == 3
    # per-group output budget never exceeds the 4000-token cap and
    # carries 1600 per candidate (bounded groups, no truncation pressure)
    assert all(t["max_tokens"] <= 4000 for t in
               [{"max_tokens": c["max_tokens"]} for c in capture])
    assert capture[0]["max_tokens"] == 3200  # 2 candidates
    assert capture[2]["max_tokens"] == 1600  # the last single candidate
    assert all(t["group"] == i + 1 for i, t in
               enumerate(out["transports"]))
    # every candidate got a record; none truncated away
    assert len(out["records"]) == 5
    assert out["unparsed"] == []
    assert out["batch_version"] == "independent_attack_batch/2.0.0"

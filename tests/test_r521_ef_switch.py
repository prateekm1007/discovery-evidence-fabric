"""R521 env-knob intervention: ENGINE_EVIDENCE_FABRIC=0.

The measured cliff is the evidence-fabric sequential channel loop
(60-309 s/run, zero pool records on 6/6 before-runs: 4x NameError
crash post-burn, 2x all-UNKNOWN/EMPTY). The ONE intervention disables
the channel via its built-in comparison switch (zero code change,
single env knob); the V2 fabric pool is untouched.

Adversarial question (Art. XXX): "what would make 'ef-disabled is
safe' pass while the system is still wrong?" — answered below:
  1. enabled() misreading the var (0/1/unset/blank/padded);
  2. the adapter calling retrieve_evidence despite the switch (dead
     switch — fail the test if the spy fires);
  3. disabling perturbing the V2 pool (coupling — V2 items must be
     byte-identical with the switch on vs off);
  4. the disabled state being indistinguishable from a crash in the
     envelope (provenance gap — disabled MUST read ABSENT, crash
     MUST read CHANNEL_ERROR).

Hermetic (no network): stubbed V2 fabric + stubbed/spying ef channel.

English only (Art. LXX).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric import evidence_fabric as _ef
from discovery_fabric.engine import adapters as ad


def test_enabled_truth_table(monkeypatch):
    monkeypatch.delenv("ENGINE_EVIDENCE_FABRIC", raising=False)
    assert _ef.enabled() is True
    monkeypatch.setenv("ENGINE_EVIDENCE_FABRIC", "1")
    assert _ef.enabled() is True
    monkeypatch.setenv("ENGINE_EVIDENCE_FABRIC", "0")
    assert _ef.enabled() is False
    monkeypatch.setenv("ENGINE_EVIDENCE_FABRIC", " 0 ")
    assert _ef.enabled() is False
    monkeypatch.setenv("ENGINE_EVIDENCE_FABRIC", "")
    assert _ef.enabled() is True


_V2_ITEMS = [{"id": "ev:abc", "abstract": "stub abstract",
              "source": "europepmc"}]
_V2_REPORT = {
    "retrieval_stats": {"sources_attempted": ["europepmc"]},
    "retrieval_diversity": {},
    "fabric_version": "RETRIEVAL_FABRIC_V2",
    "retrieval_attribution": {"mode": "parallel"},
}


def _run_adapter(monkeypatch, ef_value, tmp_path):
    if ef_value is None:
        monkeypatch.delenv("ENGINE_EVIDENCE_FABRIC", raising=False)
    else:
        monkeypatch.setenv("ENGINE_EVIDENCE_FABRIC", ef_value)
    calls = {"n": 0}

    def spy_retrieve(problem):
        calls["n"] += 1
        return [], {"fabric_version": "evidence_fabric/1.0.0",
                    "channels": [], "pool": {"items": 0}}

    monkeypatch.setattr(_ef, "retrieve_evidence", spy_retrieve)

    class StubFabric:
        def retrieve(self, problem, **kw):
            return (list(_V2_ITEMS), dict(_V2_REPORT))

    monkeypatch.setattr(ad, "_import_with_env",
                        lambda module: StubFabric())
    env = SimpleNamespace(problem={"device": "x"},
                          provenance={})
    out = ad.A2RetrievalAdapter().execute(
        env, {"out_dir": str(tmp_path)})
    return out, calls


def test_switch_off_skips_channel_v2_pool_intact(monkeypatch, tmp_path):
    out, calls = _run_adapter(monkeypatch, "0", tmp_path)
    assert calls["n"] == 0
    applied = out["apply_to"]
    assert applied["evidence"] == _V2_ITEMS
    assert applied["provenance"]["retrieval_fabric"][
        "evidence_fabric"] is None


def test_switch_on_calls_channel(monkeypatch, tmp_path):
    out, calls = _run_adapter(monkeypatch, None, tmp_path)
    assert calls["n"] == 1
    applied = out["apply_to"]
    assert applied["evidence"] == _V2_ITEMS
    assert applied["provenance"]["retrieval_fabric"][
        "evidence_fabric"]["version"] == "evidence_fabric/1.0.0"


def test_crash_shape_preserved_for_discriminator(monkeypatch, tmp_path):
    """The production NameError shape (missing _title_of import) must
    keep its CHANNEL_ERROR envelope — the clean replay discriminates
    ABSENT (disabled) from CHANNEL_ERROR (crashed)."""
    monkeypatch.delenv("ENGINE_EVIDENCE_FABRIC", raising=False)

    def boom(problem):
        raise NameError("name '_title_of' is not defined")

    monkeypatch.setattr(_ef, "retrieve_evidence", boom)

    class StubFabric:
        def retrieve(self, problem, **kw):
            return (list(_V2_ITEMS), dict(_V2_REPORT))

    monkeypatch.setattr(ad, "_import_with_env",
                        lambda module: StubFabric())
    env = SimpleNamespace(problem={"device": "x"},
                          provenance={})
    out = ad.A2RetrievalAdapter().execute(
        env, {"out_dir": str(tmp_path)})
    ef = out["apply_to"]["provenance"]["retrieval_fabric"][
        "evidence_fabric"]
    assert ef["state"] == "CHANNEL_ERROR"
    assert "_title_of" in ef["reason"]
    assert out["apply_to"]["evidence"] == _V2_ITEMS

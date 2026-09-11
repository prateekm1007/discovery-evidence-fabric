"""tests/test_r445_model_pin_routing.py — the R445-C operator-pin
ladder-ordering battery.

Measured defect (live, this round): with NVIDIA_MODEL pinned to a
field-line-capable model, generate() still routed to
nvidia/nemotron-3.5-content-safety — a catalog model with a high
availability score but no field-line capability ("User Safety: safe"
verdicts). Root cause: eligible_models() emits the operator-pinned
model at the head (source=OPERATOR_PINNED, the R418 documented
contract: "the pinned model is the provider's PRIMARY rung"), but
build_ladder()'s availability-score sort reordered it below the
high-scoring catalog model — the pin never took effect.

The fix (discovery_fabric/engine/model_routing.py): after the
score sort, any OPERATOR_PINNED-source record is restored to the
provider's first rung. The score heuristic ranks only BELOW the
explicit recorded operator decision.

This battery verifies (Art. XVI/XVII):
  1. the pinned model stays rung 0 even when a catalog model scores
     higher;
  2. WITHOUT a pin, the score ordering is preserved (no silent
     behavior change to the unpinned path);
  3. the cascade below the pin is intact (the pinned provider's other
     models and other providers' models remain in the ladder — the
     R418 contract: "if the pinned model fails, the walk continues
     down the ladder exactly as before").

Hermetic (Art. IX): eligible_models and availability scoring are
monkeypatched — no network, no ledger state, deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import discovery_fabric.engine.model_routing as mr  # noqa: E402
from discovery_fabric.engine.model_routing import (  # noqa: E402
    TASK_STRONG, ModelRecord)


def _records(pinned: bool):
    recs = []
    if pinned:
        recs.append(ModelRecord(
            provider="nvidia", model="pinned/capable-model",
            task_capabilities=[TASK_STRONG], cost_class=1,
            latency_class=2, source="OPERATOR_PINNED"))
    recs.append(ModelRecord(
        provider="nvidia", model="catalog/content-safety",
        task_capabilities=[TASK_STRONG], cost_class=1,
        latency_class=1, source="CATALOG"))
    recs.append(ModelRecord(
        provider="nvidia", model="catalog/other-model",
        task_capabilities=[TASK_STRONG], cost_class=2,
        latency_class=2, source="CATALOG"))
    return recs


def _patch(monkeypatch, pinned: bool, scores: dict):
    """Deterministic eligible_models + availability scoring."""
    monkeypatch.setattr(mr, "eligible_models",
                        lambda provider_id, task, catalog=True:
                        _records(pinned))
    monkeypatch.setattr(
        mr, "availability_score",
        lambda provider, model=None, task=None, avoid_provider=None,
        latency_class=2, now=None: scores.get(model, 0.5))
    # cooldown demotion must not interfere (no provider cooled) —
    # HEALTH is imported inside build_ladder from provider_health
    import discovery_fabric.engine.provider_health as ph
    monkeypatch.setattr(ph, "HEALTH", type("H", (), {
        "in_cooldown": staticmethod(lambda p: False)})())


class TestOperatorPinStaysFirst:
    def test_pin_beats_higher_scoring_catalog_model(self, monkeypatch):
        """The R418 contract: the pinned model is the provider's PRIMARY
        rung — even when a catalog model's availability score is
        higher (the measured content-safety defect)."""
        _patch(monkeypatch, pinned=True,
               scores={"pinned/capable-model": 0.10,
                       "catalog/content-safety": 0.95,
                       "catalog/other-model": 0.50})
        ladder = mr.build_ladder(
            TASK_STRONG, role="synthesis",
            preferred_providers=["nvidia"],
            available_providers=["nvidia"])
        rungs = ladder["rungs"]
        assert rungs, "ladder must not be empty"
        assert rungs[0]["model"] == "pinned/capable-model", (
            "operator pin must be rung 0; got "
            f"{rungs[0]['model']}")
        assert rungs[0]["source"] == "OPERATOR_PINNED"

    def test_no_pin_preserves_score_order(self, monkeypatch):
        """The unpinned path is unchanged: the higher-scoring catalog
        model still ranks first (no silent behavior change)."""
        _patch(monkeypatch, pinned=False,
               scores={"catalog/content-safety": 0.95,
                       "catalog/other-model": 0.50})
        ladder = mr.build_ladder(
            TASK_STRONG, role="synthesis",
            preferred_providers=["nvidia"],
            available_providers=["nvidia"])
        rungs = ladder["rungs"]
        assert rungs[0]["model"] == "catalog/content-safety"
        assert rungs[1]["model"] == "catalog/other-model"

    def test_cascade_below_pin_intact(self, monkeypatch):
        """The R418 contract: the walk continues below the pin — the
        pinned provider's other models remain in the ladder after the
        pin (a failing pin must fall through, never dead-end)."""
        _patch(monkeypatch, pinned=True,
               scores={"pinned/capable-model": 0.10,
                       "catalog/content-safety": 0.95,
                       "catalog/other-model": 0.50})
        ladder = mr.build_ladder(
            TASK_STRONG, role="synthesis",
            preferred_providers=["nvidia"],
            available_providers=["nvidia"])
        models = [r["model"] for r in ladder["rungs"]]
        assert models[0] == "pinned/capable-model"
        assert "catalog/content-safety" in models, (
            "the cascade below the pin must keep the other rungs")
        assert "catalog/other-model" in models


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

"""tests/test_r418_routing_pin.py — the operator model pin + batch-slug
exclusion in the routing ladder (R418).

Measured defects this pins:
  1. The deployed transport probe picked z-ai/glm-5.3-flash:batch from
     the live catalog (HTTP 404 on the chat endpoint) — batch/extended
     slugs are NOT chat-completions endpoints.
  2. The {PROVIDER}_MODEL operator override (the R391 mechanism) was
     not honored by the ROUTING ladder — the operator's measured
     working model must be the provider's PRIMARY rung.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import model_routing as mr  # noqa: E402


class _Rec:
    def __init__(self, model):
        self.model = model
        self.task_capabilities = [mr.TASK_FAST, mr.TASK_CHEAP,
                                  mr.TASK_STRONG]
        self.cost_class = 1
        self.latency_class = 1
        self.context_limit = 128000
        self.provider = "openrouter"
        self.source = "CATALOG"


def test_batch_and_extended_slugs_excluded_from_chat_ladder(monkeypatch):
    monkeypatch.setattr(mr, "_catalog_records", lambda pid: [
        _Rec("z-ai/glm-5.3-flash:batch"),
        _Rec("deepseek/deepseek-v4-flash-0731"),
        _Rec("openai/gpt-5:extended"),
    ])
    models = [r.model for r in mr.all_models("openrouter")]
    assert ":batch" not in models
    assert ":extended" not in models
    assert "deepseek/deepseek-v4-flash-0731" in models


def test_operator_pin_is_first_rung(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")
    monkeypatch.setattr(mr, "_catalog_records", lambda pid: [
        _Rec("z-ai/glm-5.3-flash"),
        _Rec("nvidia/nemotron-3.5-lightning:free"),
    ])
    recs = mr.eligible_models("openrouter", mr.TASK_FAST)
    assert recs[0].model == "nvidia/nemotron-3.5-lightning:free"
    # a catalog-listed pin keeps its catalog source but is moved FIRST
    # (the ORDER is the operator decision; the source stays the record's
    # own origin — never relabeled, Art. XXVII discipline)
    assert recs[0].source == "CATALOG"


def test_operator_pin_not_in_catalog_gets_pinned_record(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "totally/custom-model")
    monkeypatch.setattr(mr, "_catalog_records", lambda pid: [
        _Rec("z-ai/glm-5.3-flash"),
    ])
    recs = mr.eligible_models("openrouter", mr.TASK_FAST)
    assert recs[0].model == "totally/custom-model"
    assert recs[0].source == "OPERATOR_PINNED"


def test_operator_pin_absent_keeps_normal_order(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.setattr(mr, "_catalog_records", lambda pid: [
        _Rec("z-ai/glm-5.3-flash"),
    ])
    recs = mr.eligible_models("openrouter", mr.TASK_FAST)
    assert recs[0].model == "z-ai/glm-5.3-flash"


def test_operator_pin_unpinned_provider_untouched(monkeypatch):
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)
    recs = mr.eligible_models("nvidia", mr.TASK_FAST, catalog=False)
    for r in recs:
        assert r.source != "OPERATOR_PINNED"

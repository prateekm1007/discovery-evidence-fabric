"""tests/conftest.py — hermetic-suite guarantee (Art. XVII hardening).

The offline test suite must NEVER depend on ambient credentials. Since the
CEO provisioned live NVIDIA/Mistral keys (.env.keys), tests whose code paths
previously failed fast on PROVIDER_UNAVAILABLE would silently start making
real 150 s LLM calls and hang the suite. This autouse fixture removes every
provider key from the test environment unless the operator explicitly
opts in with ENGINE_LIVE=1 (the same gate the live tests use).
"""
from __future__ import annotations

import os

import pytest

PROVIDER_ENV_VARS = [
    "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY", "OPENAI_API_KEY", "QWEN_API_KEY", "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
]


@pytest.fixture(autouse=True)
def _hermetic_no_provider_keys(monkeypatch):
    if os.environ.get("ENGINE_LIVE"):
        yield  # explicit live opt-in: leave the environment untouched
        return
    for var in PROVIDER_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    # the .env.keys bootstrap must not repopulate what we removed
    import discovery_fabric.engine.adapters as _adapters
    monkeypatch.setattr(_adapters, "load_credentials",
                        lambda path=None: {}, raising=True)
    yield

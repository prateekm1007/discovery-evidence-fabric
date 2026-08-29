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

# Source-layer credentials (read from .env.keys, not env vars). Same
# hermetic rule as the LLM keys above: provisioning a source key (e.g. the
# 2026-08-29 LENS/Elsevier/PatentBear keys) must NOT silently turn
# previously-hermetic tests into live callers. CRITICAL for PatentBear:
# every live call costs 1 of 20 monthly requests — a test suite run could
# burn the whole quota. ENGINE_LIVE=1 opts out explicitly.
SOURCE_KEY_MODULES_ATTRS = [
    ("discovery_fabric.prior_art_v2.sources", "LENS_TOKEN"),
    ("discovery_fabric.prior_art_v2.sources", "PATENT_BEAR_KEY"),
    ("discovery_fabric.prior_art_v2.sources", "PATSNAP_KEY"),
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
    # source-layer keys from .env.keys: neutralized the same way
    import importlib
    for module_path, attr in SOURCE_KEY_MODULES_ATTRS:
        try:
            mod = importlib.import_module(module_path)
            monkeypatch.setattr(mod, attr, "", raising=False)
        except ImportError:
            pass
    try:
        import discovery_fabric.source_registry.keys as _srckeys
        monkeypatch.setattr(_srckeys, "load_keys", lambda: {},
                            raising=True)
        monkeypatch.setattr(_srckeys, "load_key", lambda name: "",
                            raising=True)
    except ImportError:
        pass
    yield

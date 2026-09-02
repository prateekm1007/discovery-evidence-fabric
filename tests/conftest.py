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


@pytest.fixture(autouse=True)
def _hermetic_relevance_custody_log(tmp_path, monkeypatch):
    """Relevance-adjudication custody log isolation (Art. IX/XVII).

    `relevance_aggregation.record_adjudications()` is now called from inside
    the discovery pipeline. Without this fixture, any hermetic test that
    exercises the pipeline would APPEND to the production custody log
    `artifacts/source_health/relevance_adjudication_log.jsonl` —
    contaminating real per-source usage measurements with test adjudications
    (exactly the e11 registry-contamination defect class from R374). The
    autouse redirect makes contamination impossible without per-test
    cooperation. ENGINE_LIVE=1 opts out (operator-intentional live run).
    """
    if os.environ.get("ENGINE_LIVE"):
        yield
        return
    import discovery_fabric.source_registry.relevance_aggregation as _ra
    monkeypatch.setattr(_ra, "LOG_PATH", tmp_path / "relevance_adjudication_log.jsonl")
    yield


@pytest.fixture(autouse=True)
def _hermetic_package_id_registry(tmp_path, monkeypatch):
    """Production PACKAGE_ID_REGISTRY guard (Art. IX/XVII — e11 class).

    FOUND LIVE 2026-08-30: tests/test_f_series_integration.py::
    test_d1_resume_continues_killed_run_without_rerunning_stages resumed an
    EngineRun via from_run_dir() whose manifest carried NO
    package_registry_path, so the automatic post-RANK pipeline allocated
    P-148 against the PRODUCTION registry (working tree only — restored
    before commit; disclosed in the worklog). The R374 sandbox covered the
    direct-construction path but not the resume path.

    This guard redirects package_registry.CANONICAL_REGISTRY to a tmp path
    for EVERY hermetic test, making the contamination class impossible
    regardless of individual test discipline. ENGINE_LIVE=1 opts out.
    """
    if os.environ.get("ENGINE_LIVE"):
        yield
        return
    import discovery_fabric.engine.package_registry as _pr
    monkeypatch.setattr(_pr, "CANONICAL_REGISTRY",
                        tmp_path / "PACKAGE_ID_REGISTRY_SANDBOX.json")
    yield


@pytest.fixture(autouse=True)
def _hermetic_r370g_reality_ledgers(tmp_path, monkeypatch):
    """Production R370G reality ledgers guard (Art. IX/XVII — e11 class).

    R390 reality_loop tests (and any future code touching the frozen R370G
    gate) must never append REALITY_EVENT / CAUSAL_MUTATION entries to the
    canonical ledgers under premium_package_factory/output/reality_loop/.
    The guard redirects both ledger paths at import-module level for EVERY
    hermetic test; ENGINE_LIVE=1 opts out (operator-intentional live run).
    """
    if os.environ.get("ENGINE_LIVE"):
        yield
        return
    # Patch the engine's cached gate instance (reality_loop._r370g
    # registers under sys.modules["r390_r370g"]; learning_loop loads its
    # own — both are patched here by name).
    from discovery_fabric.engine import reality_loop as _rl
    _mod = _rl._r370g()
    monkeypatch.setattr(_mod, "REALITY_EVENT_LEDGER_PATH",
                        str(tmp_path / "REALITY_EVENT_LEDGER.jsonl"))
    monkeypatch.setattr(_mod, "CAUSAL_MUTATION_LEDGER_PATH",
                        str(tmp_path / "CAUSAL_MUTATION_LEDGER.jsonl"))
    yield


@pytest.fixture(autouse=True)
def _hermetic_collision_replay_ledger(tmp_path, monkeypatch):
    """R396 P6 determinism-ledger guard (e11 class, Art. IX/XVII):
    hermetic tests must never append replay entries to the production
    ENGINE_RUNTIME/collision_replay_ledger.jsonl — a contaminated
    ledger would manufacture false DETERMINISTIC classifications for
    later live probes. ENGINE_LIVE=1 opts out (operator-intentional)."""
    if os.environ.get("ENGINE_LIVE"):
        yield
        return
    from discovery_fabric.prior_art_v2 import determinism as _det
    monkeypatch.setattr(_det, "LEDGER_PATH",
                        tmp_path / "collision_replay_ledger.jsonl")
    yield

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
import sys
from pathlib import Path

import pytest

# --- Windows case-tangle shim (dev-checkout only) -------------------------
# The index splits the orchestration package across TWO case-variants:
# 40 code paths under `toscanini/` and 248 asset paths under `TOSCANINI/`.
# On a case-insensitive Windows checkout both collide into ONE physical
# directory named `TOSCANINI`, and Python's (case-sensitive) import of
# `toscanini` then fails: tests that do `from toscanini import ...` would
# ERROR at collection even though the bytes are present. Linux CI checks
# out both directories and is unaffected (find_spec succeeds -> no shim).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if sys.platform == "win32" and "toscanini" not in sys.modules:
    import importlib.util as _ilu
    if _ilu.find_spec("toscanini") is None:
        try:
            import TOSCANINI as _T  # the SAME bytes, correct-case directory
        except ImportError:
            _T = None
        if _T is not None:
            sys.modules["toscanini"] = _T
            # R548: SINGLE-INSTANCE NORMALIZATION. The alias above
            # registered the package under BOTH keys ("TOSCANINI" from
            # `import TOSCANINI`, "toscanini" from the alias). Any
            # `from toscanini import X` then resolved through
            # _handle_fromlist using package __name__ ("TOSCANINI") and
            # registered a SECOND module instance under "TOSCANINI.X" —
            # while a test's own `import toscanini.X` loaded a THIRD
            # instance under "toscanini.X". Measured (R548): a fixture
            # monkeypatching toscanini.gateway silently missed the
            # server module's gw binding (srv.gw is not test gw), so
            # test_r396's EXTERNAL-mode gateway_up contract failed on
            # Windows while passing on Linux CI. Normalizing the
            # package's import identity to the canonical lowercase name
            # makes every load path converge on ONE instance per module
            # (the Linux topology), and any already-loaded uppercase
            # submodule keys are mirrored so existing references keep
            # working.
            _T.__name__ = "toscanini"
            _T.__package__ = "toscanini"
            if _T.__spec__ is not None:
                import importlib.machinery as _ilm
                _spec = _ilm.ModuleSpec("toscanini", _T.__spec__.loader,
                                        is_package=True)
                _spec.submodule_search_locations = list(_T.__path__)
                _T.__spec__ = _spec
            for _k in [k for k in list(sys.modules)
                       if k.startswith("TOSCANINI.")]:
                _lower = "toscanini." + _k.split(".", 1)[1]
                if _lower not in sys.modules:
                    sys.modules[_lower] = sys.modules[_k]
# sessions.py (and durable/artifact_worker) do a bare `import fcntl` —
# POSIX-only. On Windows the import must be satisfied with the same no-op
# flock fake the toscanini-focused suites already use (R482's own product
# resolution is "noop" when neither fcntl nor msvcrt exists, so a no-op
# kernel lock is honest for single-process hermetic tests).
if sys.platform == "win32":
    try:
        import fcntl as _real_fcntl  # noqa: F401
    except ImportError:
        import types as _types
        _fake_fcntl = _types.ModuleType("fcntl")
        _fake_fcntl.LOCK_SH = 1
        _fake_fcntl.LOCK_EX = 2
        _fake_fcntl.LOCK_NB = 4
        _fake_fcntl.LOCK_UN = 8
        _fake_fcntl.flock = lambda *a, **k: None
        sys.modules["fcntl"] = _fake_fcntl

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
    # R399 W2.4: the same guard class for the quota breaker — hermetic
    # tests must never trip or clear the production breaker state
    # (patent_sources/quota_breaker.json), and must never inherit a
    # tripped production state (a hermetic run would skip Lens for a
    # reason that does not exist in the test).
    from discovery_fabric.prior_art_v2 import quota_breaker as _qb
    monkeypatch.setattr(_qb, "BREAKER_PATH",
                        tmp_path / "quota_breaker.json")
    yield


@pytest.fixture(autouse=True)
def _hermetic_mechanism_cemetery(tmp_path, monkeypatch):
    """Production MECHANISM_CEMETERY/CEMETERY.json guard (e11 class,
    Art. IX/XVII — same pattern as the R374 registry/relevance guards).

    FOUND LIVE 2026-09-03 (R401-WC1 session, working tree only, reverted
    before commit): tests/test_r399_gates.py grid-gate tests resume
    EngineRuns whose post-RANK pipeline appends fixture kill entries to
    the PRODUCTION cemetery (entry_count 109 -> 111). The guard
    redirects orchestrator.mechanism_cemetery.CEMETERY_PATH to a tmp
    sandbox SEEDED with a copy of the production cemetery — reads see
    the same lessons (check_candidate_against_cemetery semantics
    unchanged); writes are isolated. ENGINE_LIVE=1 opts out.
    """
    if os.environ.get("ENGINE_LIVE"):
        yield
        return
    from pathlib import Path as _Path
    import orchestrator.mechanism_cemetery as _mc
    sandbox = tmp_path / "MECHANISM_CEMETERY_SANDBOX.json"
    prod = _Path(_mc.CEMETERY_PATH)
    if prod.exists():
        sandbox.write_bytes(prod.read_bytes())
    monkeypatch.setattr(_mc, "CEMETERY_PATH", sandbox)
    yield


@pytest.fixture(autouse=True)
def _hermetic_source_health_retrieval_log(tmp_path, monkeypatch):
    """Production source-health retrieval log guard (e11 class,
    Art. IX/XVII).

    FOUND LIVE 2026-09-03 (R401-WC1 session, working tree only, reverted
    before commit): a hermetic test_r399_gates.py run made LIVE OpenAlex
    calls (key-free polite-pool API — the provider-key guards cannot stop
    it; measured: HTTP 429 'Insufficient budget', ~60 s latency each)
    whose entries appended to the production
    artifacts/source_health/retrieval_log.jsonl, contaminating real
    per-source health measurements with test traffic. The guard
    redirects retrieval_log.LOG_PATH and maturity.RETRIEVAL_LOG_PATH to
    a tmp sandbox seeded from production (reads unchanged; writes
    isolated). ENGINE_LIVE=1 opts out. The underlying defect — live
    network calls inside the hermetic suite — is disclosed in the R401-WC1
    worklog for the next round (transport isolation, not just log
    isolation).
    """
    if os.environ.get("ENGINE_LIVE"):
        yield
        return
    from pathlib import Path as _Path
    from discovery_fabric.source_registry import retrieval_log as _rl
    from discovery_fabric.source_registry import maturity as _mat
    sandbox = tmp_path / "retrieval_log_SANDBOX.jsonl"
    prod = _Path(_rl.LOG_PATH)
    if prod.exists():
        sandbox.write_bytes(prod.read_bytes())
    monkeypatch.setattr(_rl, "LOG_PATH", sandbox)
    monkeypatch.setattr(_mat, "RETRIEVAL_LOG_PATH", sandbox)
    yield


@pytest.fixture(autouse=True)
def _hermetic_model_routing_state(monkeypatch, tmp_path):
    """R415 guard (Art. IX): the routing ledger / gone-state / catalog
    cache under ENGINE_RUNS/model_routing/ are PRODUCTION runtime
    telemetry (the evidence base for routing decisions, directive §17).
    A test that walks llm_registry.generate() must never append to them.

    FOUND LIVE 2026-09-06 (R415, during this round's iteration): the
    first post-cascade-edit test run recorded its fake_call TypeError
    hops through the production singleton before the cascade tests were
    made hermetic — quarantined as ledger.test-pollution.quarantine.jsonl
    and disclosed in the R415 worklog. This guard makes the isolation
    structural: every test gets a tmp ledger/state/catalog by default.
    ENGINE_LIVE=1 opts out.
    """
    if os.environ.get("ENGINE_LIVE"):
        yield
        return
    from discovery_fabric.engine import model_routing as _mr
    monkeypatch.setattr(_mr, "LEDGER", _mr.RoutingLedger(
        path=tmp_path / "model_routing_ledger.jsonl"))
    monkeypatch.setattr(_mr, "STATE_PATH",
                        tmp_path / "model_routing_state.json")
    monkeypatch.setattr(_mr, "CATALOG_DIR", tmp_path / "model_catalog")
    _mr.clear_probe_cache()
    yield
    _mr.clear_probe_cache()

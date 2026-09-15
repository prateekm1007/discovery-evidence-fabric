"""tests/test_r394_privacy_semantics.py — R394 sections 15/16:
confidentiality (owner scoping, metadata stripping) and product
semantics (false premise / rejected / unknown user states).

The privacy tests attack the measured production defect
(R394/PRODUCTION_AUDIT.json claim 3): anonymous /api/sessions returned
ALL 32 users' engineering problems with worker pids and /app filesystem
paths. The defense is exercised at the STORE layer (access rules) and
the PROJECTION layer (stripping) — the same logic the HTTP layer calls.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import user_state as us  # noqa: E402


# ---------------------------------------------------------------------------
# section 15: ownership scoping
# ---------------------------------------------------------------------------

class _SessionStoreHarness:
    """Point the sessions store at a temp dir (production store never
    touched — Art. IX)."""

    def __enter__(self):
        import toscanini.sessions as store
        self._store = store
        self._orig = (store.STORE_DIR, store.SESSIONS_PATH,
                      store.SHARES_PATH, store.ENGINE_RUNS)
        self.tmp = tempfile.TemporaryDirectory()
        tdp = Path(self.tmp.name)
        store.STORE_DIR = tdp
        store.SESSIONS_PATH = tdp / "sessions.json"
        store.SHARES_PATH = tdp / "shares.json"
        store.ENGINE_RUNS = tdp / "ENGINE_RUNS"
        store.SESSIONS_PATH.write_text("{}")
        return store

    def __exit__(self, *a):
        store = self._store
        (store.STORE_DIR, store.SESSIONS_PATH,
         store.SHARES_PATH, store.ENGINE_RUNS) = self._orig
        self.tmp.cleanup()


def test_owner_sees_only_own_sessions():
    with _SessionStoreHarness() as store:
        a = store.create_session("t1", "user A problem text", owner_key="A")
        b = store.create_session("t2", "user B problem text", owner_key="B")
        visible_to_a = store.list_sessions_visible_to("A")
        ids = [s["session_id"] for s in visible_to_a]
        assert a["session_id"] in ids
        assert b["session_id"] not in ids


def test_anonymous_sees_nothing_owned():
    with _SessionStoreHarness() as store:
        a = store.create_session("t", "private problem", owner_key="A")
        visible = store.list_sessions_visible_to("some-other-key")
        assert a["session_id"] not in [s["session_id"] for s in visible]
        assert visible == []


def test_legacy_ownerless_sessions_invisible_to_cookies():
    """Pre-scoping history (the 32 deployed sessions) belongs to NO
    cookie holder — fail-closed."""
    with _SessionStoreHarness() as store:
        legacy = store.create_session("t", "legacy problem", owner_key="")
        assert store._session_access(legacy, "any-cookie") == "DENY"
        # R463: NO credential reaches legacy/ownerless sessions anymore —
        # the operator-key override is retired (TypeError is the
        # executable proof the parameter no longer exists)
        import pytest as _pytest
        with _pytest.raises(TypeError):
            store._session_access(legacy, "op-key", operator_key="op-key")


def test_public_demo_sessions_visible_to_all():
    with _SessionStoreHarness() as store:
        s = store.create_session("demo", "curated demo problem",
                                 owner_key="operator")
        store.update_session(s["session_id"], public=True)
        fresh = store.get_session(s["session_id"])
        assert store._session_access(fresh, "random-cookie") == "PUBLIC"
        assert store._session_access(fresh, "another-cookie") == "PUBLIC"


def test_session_access_denied_for_other_owner():
    with _SessionStoreHarness() as store:
        a = store.create_session("t", "A's problem", owner_key="A")
        assert store.session_access(a["session_id"], "B") == "DENY"
        assert store.session_access(a["session_id"], "A") == "OWNER"
        assert store.session_access("nonexistent", "A") is None


def test_operator_key_override_is_retired():
    """R463 (operator architectural ruling): there is NO operator key —
    no second secret may grant full visibility over other users'
    sessions. The access model accepts ONLY an owner capability, and
    presenting any other credential yields DENY, not OWNER."""
    with _SessionStoreHarness() as store:
        a = store.create_session("t", "A's problem", owner_key="A")
        b = store.create_session("t2", "ownerless legacy", owner_key="")
        # the retired parameter no longer exists on either entry point
        import pytest as _pytest
        with _pytest.raises(TypeError):
            store.session_access(a["session_id"], "OP", operator_key="OP")
        with _pytest.raises(TypeError):
            store.list_sessions_visible_to("OP", "OP")
        # and no owner key can converge onto another user's session
        assert store.session_access(a["session_id"], "OP") == "DENY"
        assert store.session_access(b["session_id"], "OP") == "DENY"


# ---------------------------------------------------------------------------
# section 15: operational metadata never reaches a customer projection
# ---------------------------------------------------------------------------

def test_operational_fields_stripped():
    session = {
        "session_id": "ts_x", "title": "t", "user_text": "problem",
        "status": "COMPLETE", "final_status": "REJECTED",
        "worker_pid": 31337, "worker_starttime": "12345",
        "run_dir": "/app/ENGINE_RUNS/toscanini_ui_ui_thing_123",
        "problem_id": "ui_thing_123", "owner_key": "SECRET-CAPABILITY",
        "package": None, "domain": "medical",
    }
    out = us.public_session_view(session)
    for f in us.OPERATIONAL_FIELDS:
        assert f not in out, f"{f} leaked into the customer projection"
    assert "user_state_view" in out


def test_projection_leak_scan_recursive():
    """No operational value may appear anywhere in the projection —
    an adversarial scan over the serialized payload (Art. XVII)."""
    session = {
        "session_id": "ts_x", "title": "t", "user_text": "problem",
        "status": "RUNNING", "final_status": None,
        "worker_pid": 31337, "worker_starttime": "999",
        "run_dir": "/app/ENGINE_RUNS/secret_run_dir",
        "problem_id": "ui_secret_999", "owner_key": "cap-token",
    }
    out = us.public_session_view(session)
    payload = repr(out)
    assert "31337" not in payload
    assert "/app/ENGINE_RUNS" not in payload
    assert "cap-token" not in payload
    assert "999" not in payload.replace("'user_state_view'", "")


# ---------------------------------------------------------------------------
# section 16: product semantics — failures explain themselves
# ---------------------------------------------------------------------------

def test_false_premise_is_not_rejected():
    """A false premise is a DIFFERENT outcome from a rejected candidate
    — the user must see 'the problem as stated cannot occur', never a
    confusing REJECTED."""
    s = {"status": "COMPLETE", "final_status": "MALFORMED_OR_FALSE_PREMISE",
         "package": None}
    v = us.user_state_view(s)
    assert v["user_state"] == "COMPLETED_FALSE_PREMISE"
    assert "physically/scientifically incoherent" in v["meaning"]
    assert v["finished"] is True
    assert v["found_something"] is False
    assert v["rejected"] is False  # NOT a candidate rejection


def test_rejected_projects_to_under_development_not_a_dead_end():
    # R416 honest-causes fix: a REJECTED run presents the invention as
    # IN DEVELOPMENT (the generation record carries the diagnosed
    # cause) — never "the engine REJECTED the candidate — the
    # adversarial chain found the idea not defensible enough"
    s = {"status": "COMPLETE", "final_status": "REJECTED", "package": None}
    v = us.user_state_view(s)
    assert v["user_state"] == "COMPLETED_UNDER_DEVELOPMENT"
    assert "architecture" in v["meaning"].lower()
    assert v["rejected"] is False  # the product surface never renders a
    # bare reject dead-end; challenge losses live on the generation
    # records


def test_transport_failure_is_not_a_research_verdict():
    s = {"status": "ERROR_TRANSPORT", "final_status": None,
         "error": "gateway down", "package": None}
    v = us.user_state_view(s)
    assert v["user_state"] == "FAILED_TRANSPORT"
    assert "language-model transport" in v["meaning"]
    assert v["rejected"] is False
    assert v["found_something"] is False


def test_engine_failure_is_not_a_research_verdict():
    s = {"status": "ERROR_RUN", "final_status": None, "package": None}
    v = us.user_state_view(s)
    assert v["user_state"] == "FAILED_ENGINE"
    assert v["rejected"] is False


def test_spawn_failure_is_recoverable_never_engine_failure():
    """R463: the worker never started — the discovery pipeline never
    ran, so the projection must NOT read 'the engine failed'. It lands
    in the recoverable family with the spawn cause on the error line
    (Art. LXI: distinct infrastructure classes stay distinct)."""
    s = {"status": "ERROR_SPAWN", "final_status": None,
         "error": ("The worker process could not be started (OSError). "
                   "Nothing ran; nothing was changed. Retry re-attempts "
                   "the run."), "package": None}
    v = us.user_state_view(s)
    assert v["user_state"] == "INTERRUPTED"
    assert v["finished"] is True
    assert v["found_something"] is False
    assert v["rejected"] is False
    assert "machine_status" in v and v["machine_status"] == "ERROR_SPAWN"
    # retryable: ERROR_SPAWN is in the retry family (the typed recovery
    # path accepts it)
    from toscanini import sessions as _store
    assert "ERROR_SPAWN" in _store.ERROR_STATUSES
    assert "ERROR_SPAWN" in _store.RETRYABLE_STATUSES


@pytest.mark.parametrize("final_status,readable", [
    ("AUTOMATED_INVENTION_CANDIDATE", "Invention candidate (automated)"),
    ("REJECTED", "Challenged and killed — the generation record shows "
                 "the diagnosed cause"),
    ("EVOLVED_INVENTION_CANDIDATE", "Evolved invention candidate"),
    ("INVENTION_UNDER_DEVELOPMENT", "Invention in development"),
    ("MECHANISM_GENERATION_FAILED", "Mechanism generation failed (a "
                                    "generation gap — not a rejection)"),
    ("MALFORMED_OR_FALSE_PREMISE",
     "False premise — the problem as stated cannot physically occur"),
])
def test_final_status_readable_mapping(final_status, readable):
    assert us.FINAL_STATUS_READABLE[final_status] == readable


# ---------------------------------------------------------------------------
# section 1: deployment identity assertion (health payload contract)
# ---------------------------------------------------------------------------

def test_health_payload_carries_deployment_identity():
    from toscanini import server as srv
    payload = srv._health_payload()
    di = payload["deployment_identity"]
    assert di["deployment_drift"] in ("GREEN", "RED")
    # R396 A.3-A.6 contract upgrade: identity is the BUILD ARTIFACT
    # (BUILD == RUNNING == HEALTH proof chain); the R392-era
    # DEPLOYED_ENGINE_COMMIT-from-env contract is superseded.
    assert "rule" in di and "BUILD_ARTIFACT_SHA == RUNNING_ARTIFACT_SHA" \
        in di["rule"]
    assert "never identity" in di["rule"]  # env vars are expectations only
    # RED drift must surface in readiness too (the release is NOT
    # healthy when drift is RED — the invariant is machine-checkable)
    if di["deployment_drift"] == "RED":
        assert payload["readiness"]["deployment_drift"] == "RED"
        assert di["drift_reasons"]


def test_health_payload_no_secrets():
    """The health endpoint exposes deployment identity WITHOUT exposing
    secrets: no key material anywhere in the payload (the §1 contract:
    'enough information to prove this without exposing secrets')."""
    from toscanini import server as srv
    import re
    payload = repr(srv._health_payload())
    key_patterns = [
        r"sk-[A-Za-z0-9]{16,}", r"nvapi-[A-Za-z0-9]{16,}",
        r"ghp_[A-Za-z0-9]{20,}", r"eyJ[A-Za-z0-9]{20,}",
    ]
    for pat in key_patterns:
        assert not re.search(pat, payload), f"secret pattern {pat} leaked"

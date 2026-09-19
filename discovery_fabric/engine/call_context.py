"""discovery_fabric/engine/call_context.py — R451-C1.3.

Run-level routing provenance: every real engine call INSIDE an
investigation must carry run_id / session_id / stage so the routing
ledger can isolate ONE run's calls without time-window or ledger-tail
inference (the directive's C1.3-3 acceptance).

The invariant (directive, verbatim):

    run_owned_call => run_id != null

Provider capability probes are NOT run-owned discovery calls and
legitimately carry run_id = null (call_class='CAPABILITY_PROBE' —
runtime_admission.probe_capability marks them). Standalone script
calls outside any investigation carry call_class='STANDALONE' with an
honest null run_id.

Mechanics: a ContextVar bound by EngineRun for the whole run lifetime
(the conductor owns the run identity — mechanism_space, evolution,
adversarial and bridge call sites inherit it WITHOUT each learning a
new parameter; the generate() signature keeps its explicit run_id
override for direct callers). Thread-safe by construction: the worker
runs one engine per process, and ContextVar isolation protects any
concurrent probe thread.

Constitutional contract (Art. VI, XII, XXV, LXI):
  - The run identity is the REAL recorded identity (EngineRun.run_id),
    never a purpose string pretending to be one (the pre-C1.3 defect:
    evolution._llm_generate passed run_id=purpose, polluting the
    ledger with fake run ids; mechanism_space passed none at all —
    802 measured null-run_id lines in the R451 acceptance ledger).
  - Fields are honest: session_id is null when no session context
    exists (a CLI investigation), never a fabricated placeholder.
"""
from __future__ import annotations

import threading
from contextvars import ContextVar
from typing import Any, Dict, Optional

_ACTIVE: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "engine_call_context", default=None)
_LOCK = threading.Lock()

_FIXTURE: ContextVar[Optional[Any]] = ContextVar(
    "engine_fixture_transport", default=None)

RUN_OWNED = "RUN_OWNED"
STANDALONE = "STANDALONE"
CAPABILITY_PROBE = "CAPABILITY_PROBE"
CALL_CLASSES = (RUN_OWNED, STANDALONE, CAPABILITY_PROBE)


def bind_run(run_id: str, session_id: Optional[str] = None,
             stage: Optional[str] = None) -> Any:
    """Bind the run identity for this context (EngineRun.run calls this
    once per run; resume re-binds the SAME recorded run_id). Returns
    the token for unbind()."""
    ctx = {"run_id": str(run_id), "session_id": session_id,
           "stage": stage}
    return _ACTIVE.set(ctx)


def unbind(token: Any) -> None:
    _ACTIVE.reset(token)


def set_stage(stage: str) -> None:
    """Update the CURRENT conductor stage inside a bound run (called by
    the stage loop so ledger lines can carry the engine stage in
    addition to the call-site purpose)."""
    with _LOCK:
        ctx = _ACTIVE.get()
        if ctx is not None:
            ctx["stage"] = stage


def current() -> Optional[Dict[str, Any]]:
    ctx = _ACTIVE.get()
    return dict(ctx) if ctx else None


def bind_fixture(fixture: Any) -> Any:
    """Bind a dry-run fixture transport for this context (EngineRun
    binds it for the whole run lifetime in dry-run mode ONLY).
    Default None: LIVE behavior never consults a fixture."""
    return _FIXTURE.set(fixture)


def unbind_fixture(token: Any) -> None:
    _FIXTURE.reset(token)


def fixture() -> Optional[Any]:
    """The bound dry-run fixture transport, or None on the LIVE path."""
    return _FIXTURE.get()


def effective(run_id: Optional[str] = None) -> Dict[str, Any]:
    """Resolve the effective call provenance for one generate() call:
    the explicit run_id parameter (direct callers) or the bound run
    context. Returns the fields the routing ledger line carries:

        run_id, session_id, engine_stage, call_class
    """
    ctx = _ACTIVE.get()
    if run_id is not None:
        # an explicit run id is run-owned by definition; any bound
        # context's session/stage still enrich the line honestly
        return {
            "run_id": str(run_id),
            "session_id": (ctx or {}).get("session_id"),
            "engine_stage": (ctx or {}).get("stage"),
            "call_class": RUN_OWNED,
        }
    if ctx is not None:
        return {
            "run_id": ctx.get("run_id"),
            "session_id": ctx.get("session_id"),
            "engine_stage": ctx.get("stage"),
            "call_class": RUN_OWNED,
        }
    return {"run_id": None, "session_id": None, "engine_stage": None,
            "call_class": STANDALONE}

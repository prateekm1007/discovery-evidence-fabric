"""execution_states — Article LXXIV (Observer-Independent Durable
Execution, Constitution v2.6.0): the canonical durable state machine
and the observation-domain vocabulary.

THE TWO DOMAINS (the article's Section 1):

  1. THE EXECUTION DOMAIN — the durable run. Canonical states below.
     Server-side authority: the session store, the durable state
     branch, the worker's pid-liveness record, the provider ledgers.
  2. THE OBSERVATION DOMAIN — whatever process, browser, tool call, or
     sandbox is CURRENTLY watching. Its states are facts about the
     WATCHER, never predicates about the WATCHED run.

The article's core invariants, enforced here BY CONSTRUCTION:

  - UNKNOWN is a first-class canonical state, distinct from FAILED
    (never collapsed — the mapping is total and single-valued, and the
    test pins the separation).
  - Observation states can never be canonical states (disjoint enums).
  - Any surface answering "is it failed?" consults mapping() rather
    than guessing from an operational status string.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class ExecutionState(str, Enum):
    """The durable state machine (Article LXXIV §E, at minimum these
    nine). UNKNOWN is first-class and distinct from FAILED."""

    QUEUED = "QUEUED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    WAITING_EXTERNAL = "WAITING_EXTERNAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class ObservationState(str, Enum):
    """The observation domain (Article LXXIV §C/§I/§J): facts about the
    watcher. NEVER a predicate about the watched run — these names are
    disjoint from ExecutionState by construction."""

    OBSERVER_ALIVE = "OBSERVER_ALIVE"
    OBSERVER_DETACHED = "OBSERVER_DETACHED"
    POLL_TIMEOUT = "POLL_TIMEOUT"
    POLL_INTERRUPTED = "POLL_INTERRUPTED"
    SANDBOX_REAPED = "SANDBOX_REAPED"
    LOCAL_PROCESS_REAPED = "LOCAL_PROCESS_REAPED"
    NO_LOCAL_PROCESS = "NO_LOCAL_PROCESS"

    # typed timeout semantics (the article's §J): distinct categories,
    # never one generic timeout
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    SANDBOX_TIMEOUT = "SANDBOX_TIMEOUT"
    REMOTE_PROVIDER_TIMEOUT = "REMOTE_PROVIDER_TIMEOUT"
    REMOTE_PROVIDER_UNAVAILABLE = "REMOTE_PROVIDER_UNAVAILABLE"
    JOB_EXPIRED = "JOB_EXPIRED"
    JOB_FAILED = "JOB_FAILED"
    JOB_UNKNOWN = "JOB_UNKNOWN"


#: the store's operational statuses -> the canonical machine. TOTAL and
#: single-valued: every status the session store emits maps to exactly
#: one canonical state. The semantic anchors:
#:   - INTERRUPTED (worker died without a terminal verdict) maps to
#:     UNKNOWN, not FAILED — the R392 doctrine ("recoverable, never
#:     silently reported") plus Article LXXIV §C: the worker's death is
#:     an infrastructure fact; the run's outcome is unknown.
#:   - ERROR_STUCK (no worker progress >3h, cause not captured) maps to
#:     UNKNOWN — the amendment's exact case: a stalled feed is not a
#:     verdict.
#:   - RUN_BLOCKED_* (saved and resumable on a capable route) maps to
#:     WAITING_EXTERNAL — the run is paused awaiting external
#:     conditions, not failed.
#:   - ERROR_RUN / ERROR_BUILD / ERROR_TRANSPORT / ERROR_SPAWN carry a
#:     TYPED terminal verdict from the machine's own instruments -> the
#:     only mappings into FAILED.
_STATUS_MAP: Dict[str, ExecutionState] = {
    "PENDING": ExecutionState.QUEUED,
    "BUILDING_PROBLEM": ExecutionState.STARTING,
    "AWAITING_CLARIFICATION": ExecutionState.WAITING_EXTERNAL,
    "RUNNING": ExecutionState.RUNNING,
    "COMPLETE": ExecutionState.COMPLETED,
    "ERROR_BUILD": ExecutionState.FAILED,
    "ERROR_RUN": ExecutionState.FAILED,
    "ERROR_TRANSPORT": ExecutionState.FAILED,
    "ERROR_SPAWN": ExecutionState.FAILED,
    "ERROR_STUCK": ExecutionState.UNKNOWN,
    "INTERRUPTED": ExecutionState.UNKNOWN,
    "RUN_BLOCKED_TRANSPORT": ExecutionState.WAITING_EXTERNAL,
    "RUN_BLOCKED_CAPABILITY": ExecutionState.WAITING_EXTERNAL,
}


def mapping(status: Optional[str]) -> ExecutionState:
    """Map a session-store operational status into the canonical
    durable state machine. Unknown/absent statuses map to UNKNOWN
    (never guessed into FAILED — Art. XXV)."""
    if not status:
        return ExecutionState.UNKNOWN
    try:
        return _STATUS_MAP[str(status).upper()]
    except KeyError:
        return ExecutionState.UNKNOWN


def is_failed(status: Optional[str]) -> bool:
    """The ONLY sanctioned answer to "is this run failed?" — a run is
    failed iff its canonical state is FAILED (a typed terminal verdict).
    UNKNOWN runs are not failed (Article LXXIV §C)."""
    return mapping(status) is ExecutionState.FAILED


def is_terminal(status: Optional[str]) -> bool:
    """Terminal = left the active set with a decided OR honestly-
    unknown outcome (COMPLETED / FAILED / CANCELLED / EXPIRED /
    UNKNOWN-after-death). RUNNING / QUEUED / STARTING /
    WAITING_EXTERNAL are not terminal."""
    return mapping(status) in (
        ExecutionState.COMPLETED, ExecutionState.FAILED,
        ExecutionState.CANCELLED, ExecutionState.EXPIRED,
        ExecutionState.UNKNOWN)


def lifecycle_record(observer: Any = None, job: Any = None,
                     provider: Any = None, canonical: Any = None,
                     **extra: Any) -> Dict[str, Any]:
    """The four-domain lifecycle frame (Article LXXIV §1; the operator's
    standing order): every state report names which domain it speaks
    from — local observer state, remote job state, provider state,
    canonical Toscanini run state. Observation facts ride in their own
    key and can never overwrite canonical states."""
    return {
        "domain_observation": observer,
        "domain_remote_job": job,
        "domain_provider": provider,
        "domain_canonical_run": canonical,
        **extra,
    }

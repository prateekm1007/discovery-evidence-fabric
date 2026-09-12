"""visual_join.py — R451-C2.2: THE machine-verifiable
geometry-to-visual join evaluator (operator directive R451-C2.2 §5/§6).

The directive's join contract:

    ENGINEERING GEOMETRY READY
        ↓
    VISUAL INVOCATION RECORD
        ↓
    RENDER
        ↓
    VISUAL GATE
        ↓
    HERO

Every arrow must be provable from persisted records — a missing arrow
is an explicit, typed state, never silence ("No silent gap"):

  * GLB exists AND the engineering geometry is valid, but no
    VISUAL_COMPILER_INVOCATION.json exists and no render job is
    pending  ->  INVOCATION_MISSING (an explicit join FAILURE).
  * the invocation record exists but the render has not produced its
    record yet (a pending async job, or a run still executing)
    ->  INVOCATION_PENDING (explicit pending — never a silent wait).
  * the invocation occurred and the renderer typed a skip/failure
    ->  RENDER_BLOCKED (the invocation happened; the render did not).
  * the renderer produced pixels and the gate did not pass
    ->  STOPPED_GATE.
  * the gate passed (COMPLETE_PASS / legacy PASS)
    ->  VISUAL_READY.
  * the invocation record says the renderer produced pixels but no
    render record / gate exists on disk
    ->  RENDER_RECORD_MISSING (record integrity failure — the
    watchdog FAILs the run; the strip shows the typed failure).

PRESENTATION-ONLY (Coder 2 boundary): this module derives state from
canonical records and changes no engineering truth. It WRITES nothing
(Art. IX — certification is observational; the invocation record is
written by the Visual Compiler itself, the job record by the artifact
worker). It never invents a hash, status, or reason (Art. VI): every
field is read from the run's own files or the CIO projection.

This is the BACKEND derivation the browser consumes verbatim
(to scanini/dossier.py::design_tab -> tabs.design.visual_join_state);
the frontend never re-derives any of it from file existence
(R451-C2.1 rule, extended to the invocation layer).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# The closed join-state vocabulary (R451-C2.2 §5/§6). THE one place it
# is defined; the strip, the design tab, and the watchdog all speak it.
VISUAL_JOIN_STATES = (
    "NOT_APPLICABLE",        # engineering visualization does not apply
    "NOT_REACHED",           # no engineering geometry was produced
    "INVOCATION_PENDING",    # geometry ready; the invocation is in flight
    "INVOCATION_MISSING",    # geometry ready; the invocation never ran —
                             # an EXPLICIT FAILURE (no silent gap)
    "RENDER_BLOCKED",        # invoked; the renderer typed a skip/failure
    "RENDER_RECORD_MISSING",  # invoked as rendered; no record on disk —
                             # record integrity failure
    "STOPPED_GATE",          # rendered; the integrity gate did not pass
    "VISUAL_READY",          # rendered; the gate passed
)

RECEIPT_REL = "MODEL/3D/VISUAL_COMPILER_INVOCATION.json"
RENDER_RECORD_REL = "MODEL/3D/render_record.json"
GATE_REL = "MODEL/3D/visual_gate.json"
RENDER_JOB_REL = "MODEL/3D/RENDER_JOB.json"

# render-record statuses that mean the renderer produced pixels
# (mirrors dossier._RENDERER_RAN — one vocabulary, two consumers)
_RENDERER_RAN = ("OK", "SUCCEEDED", "COMPLETE", "PARTIAL")

# receipt statuses that mean the invocation occurred but the renderer
# did not produce pixels (typed skips and typed failures)
_RENDERER_DID_NOT_RUN_PREFIXES = ("RENDER_SKIPPED",)
_RENDERER_DID_NOT_RUN_STATUSES = ("RENDER_FAILED", "RENDER_TIMEOUT",
                                  "INTERRUPTED")

# the run statuses whose stop is infrastructure (Art. LXI) — the same
# class user_state/dossier treat as infrastructure
_INFRA_STATUSES = ("INTERRUPTED", "ERROR_TRANSPORT", "ERROR_BUILD",
                   "ERROR_RUN", "ERROR_STUCK", "RUN_BLOCKED_TRANSPORT")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.is_file():
            data = json.loads(path.read_text())
            return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        pass
    return None


def read_invocation_receipt(run_dir: Optional[Path]) -> Optional[Dict]:
    """The invocation receipt in EITHER field era (Art. XI: historical
    1.0.0 records on existing runs stay readable; the writer emits
    1.1.0 only). Normalizes to the 1.1.0 names:
    invocation_status / glb_sha256 / visual_compiler_version."""
    receipt = _read_json(Path(run_dir) / RECEIPT_REL) if run_dir else None
    if not receipt:
        return None
    norm = dict(receipt)
    norm.setdefault("invocation_status",
                    receipt.get("status") or receipt.get("invocation_status"))
    norm.setdefault("glb_sha256",
                    receipt.get("glb_sha256")
                    or receipt.get("canonical_glb_sha256"))
    norm.setdefault("visual_compiler_version",
                    receipt.get("visual_compiler_version")
                    or receipt.get("compiler_version"))
    return norm


def _job_pending(run_dir: Optional[Path]) -> Tuple[bool, Optional[str]]:
    """The async render job's own record — the invocation was REQUESTED
    and has not spoken yet (RUNNING), or was interrupted and is owed a
    recovery re-enqueue (INTERRUPTED). Both are explicit pending
    states, never silence."""
    job = _read_json(Path(run_dir) / RENDER_JOB_REL) if run_dir else None
    status = str((job or {}).get("status") or "")
    if status in ("RUNNING", "INTERRUPTED"):
        return True, status
    return False, status or None


def evaluate_visual_join(session: Dict[str, Any],
                         geom: Dict[str, Any],
                         renders: Dict[str, Any],
                         running: bool,
                         engineering_geometry_ready: bool,
                         geometry_state: str,
                         ) -> Dict[str, Any]:
    """Derive the join state from canonical records.

    session / geom / renders  — the same inputs the dossier's design
                                tab already holds (the session record,
                                the CIO geometry block, the CIO renders
                                block).
    engineering_geometry_ready — the artifact-contract verdict from
                                dossier._geometry_artifact_contract: a
                                canonical geometry artifact exists and
                                the chain does not record a failure.
    geometry_state            — the geometry-side state the contract
                                produced (the join is defined only when
                                geometry is available).

    `visual_join_state` None means UNDECIDED — no records were
    readable; the caller renders from the CIO renders block (the
    pre-receipt fallback) rather than inventing a state (Art. XXV).
    """
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    receipt = read_invocation_receipt(run_dir)
    render_record = _read_json(Path(run_dir) / RENDER_RECORD_REL) \
        if run_dir else None
    gate = _read_json(Path(run_dir) / GATE_REL) if run_dir else None

    result: Dict[str, Any] = {
        "visual_join_state": None,
        "visual_join_detail": None,
        "visual_join_cause": None,
        "invocation_present": receipt is not None,
        "invocation_status": (receipt or {}).get("invocation_status"),
        "render_record_present": render_record is not None,
        "gate_verdict": (gate or {}).get("verdict")
        or ((renders.get("visual_gate") or {}).get("verdict")
            if isinstance(renders.get("visual_gate"), dict) else None),
        "pending_render_job": None,
    }

    # ---- the join is defined only downstream of geometry --------------
    if geometry_state in ("geometry_not_applicable",):
        result["visual_join_state"] = "NOT_APPLICABLE"
        result["visual_join_detail"] = \
            "engineering visualization is not applicable to this invention"
        return result
    if geometry_state != "geometry_available":
        # upstream_not_reached / geometry_generation_failed: the join
        # has no geometry to invoke. (Legacy render-side states are
        # passed through undecided — the caller's renders-block
        # fallback owns them for pre-receipt payloads.)
        result["visual_join_state"] = ("NOT_REACHED"
                                       if geometry_state != "" else None)
        return result
    if not engineering_geometry_ready:
        # defensive: the caller's contract and state disagree — never
        # derive a join without the geometry contract's positive verdict
        result["visual_join_state"] = None
        return result

    if run_dir is None and receipt is None:
        # no run directory to read (session-only projection): the join
        # cannot verify the invocation from records — undecided; the
        # caller falls back to the CIO renders block (pre-receipt era)
        result["visual_join_state"] = None
        return result

    # geometry is ready: the invocation side decides --------------------
    if receipt is not None:
        status = str(result["invocation_status"] or "")
        if status in _RENDERER_RAN:
            if render_record is None:
                # the invocation claims pixels; the record is absent —
                # a record-integrity failure, never read as success
                # (Art. XXIV: the record, not the claim, is the proof)
                result["visual_join_state"] = "RENDER_RECORD_MISSING"
                result["visual_join_detail"] = (
                    "the invocation record says the renderer produced "
                    "pixels but no render record exists on disk — "
                    "recorded as a join integrity failure")
                return result
            verdict = result["gate_verdict"]
            if verdict in ("PASS", "COMPLETE_PASS"):
                result["visual_join_state"] = "VISUAL_READY"
                result["visual_join_detail"] = None
                return result
            if verdict is not None:
                result["visual_join_state"] = "STOPPED_GATE"
                result["visual_join_detail"] = (
                    f"the render completed but the presentation "
                    f"integrity gate returned {verdict}")
                return result
            # a rendered record without any gate verdict: the gate
            # contract requires one — fail closed to STOPPED_GATE with
            # the honest detail (the gate never spoke)
            result["visual_join_state"] = "STOPPED_GATE"
            result["visual_join_detail"] = (
                "the render record exists but no presentation "
                "integrity gate verdict is recorded — fail closed")
            return result
        if status.startswith(_RENDERER_DID_NOT_RUN_PREFIXES) or \
                status in _RENDERER_DID_NOT_RUN_STATUSES:
            cause_detail = (receipt.get("skip_reason")
                            or f"the renderer recorded {status or 'UNKNOWN'}")
            result["visual_join_state"] = "RENDER_BLOCKED"
            result["visual_join_detail"] = cause_detail
            # the typed cause from the receipt's OWN status vocabulary
            # (never text-matched from the reason): no renderer/deps in
            # the environment -> renderer_unavailable; capacity/infra
            # skips and transport-class failures -> infrastructure;
            # a renderer that tried and failed -> renderer_unavailable
            if status in ("RENDER_SKIPPED_NO_RENDERER",
                          "RENDER_SKIPPED_NO_RENDER_NODE",
                          "RENDER_SKIPPED_NO_CHROME",
                          "RENDER_SKIPPED_THREE",
                          "RENDER_FAILED", "RENDER_TIMEOUT") or \
                    "DEPS" in status:
                result["visual_join_cause"] = "renderer_unavailable"
            else:
                result["visual_join_cause"] = "infrastructure"
            return result
        # an invocation record whose status is unknown/pending — the
        # boundary was reached; the renderer has not spoken
        result["visual_join_state"] = "INVOCATION_PENDING"
        result["visual_join_detail"] = (
            f"the visual compiler invocation is recorded "
            f"({status or 'status not recorded'}) and the render has "
            f"not produced its verdict yet")
        return result

    # no receipt: was the invocation requested (async job) or missed? ----
    pending, job_status = _job_pending(run_dir)
    result["pending_render_job"] = job_status
    if pending:
        result["visual_join_state"] = "INVOCATION_PENDING"
        result["visual_join_detail"] = (
            f"the presentation render job is {job_status} — the "
            f"geometry-to-visual invocation is in flight (explicit "
            f"pending, never a silent gap)")
        return result
    if running:
        # the run is still executing — the join legitimately has not
        # been reached yet (the bridge invokes the renderer in the
        # worker / requests the async job at the end of the run)
        result["visual_join_state"] = "INVOCATION_PENDING"
        result["visual_join_detail"] = (
            "the investigation is still executing — the "
            "geometry-to-visual invocation follows the engineering "
            "geometry")
        return result
    # terminal run, geometry ready, no invocation record, no pending
    # job: THE no-silent-gap failure (R451-C2.2 §5) — recorded as the
    # explicit failure it is, never read as "render not needed"
    result["visual_join_state"] = "INVOCATION_MISSING"
    result["visual_join_detail"] = (
        "the engineering geometry is ready but no visual invocation "
        "record exists and no render job is pending — the "
        "geometry-to-visual join did not run (explicit join failure)")
    return result


def join_cause(join_state: Optional[str],
               cause: Optional[str]) -> Tuple[str, str]:
    """The join state -> (geometry_state, presentation_cause) for the
    render-related join states — the design tab consumes THIS pair for
    the States C/D/E decision (the cause is the receipt's own typed
    vocabulary, never text-matched). Callers keep their own
    geometry-side states for the non-render joins.
    """
    if join_state == "VISUAL_READY":
        return "visual_complete", ""
    if join_state == "STOPPED_GATE":
        return "visual_render_failed", "gate_not_passed"
    if join_state == "RENDER_RECORD_MISSING":
        return "visual_render_failed", cause or "renderer_unavailable"
    if join_state == "RENDER_BLOCKED":
        return "visual_render_failed", cause or "renderer_unavailable"
    if join_state == "INVOCATION_MISSING":
        return "geometry_available", "not_attempted"
    if join_state == "INVOCATION_PENDING":
        return "geometry_available", "rendering_in_progress"
    return "", ""

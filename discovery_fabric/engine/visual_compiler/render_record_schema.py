"""render_record_schema.py — R443 typed render records, total and final.

Workstream 4 (operator directive R443-C2): every render result must be
STRUCTURALLY VALID for its status. The R442 round record disclosed the
live defect: the memory-guard path omitted fields such as `out_dir` and
`visual_gate`, so consumers needed fragile logic like

    if status == ...

before discovering whether a supposedly required field exists.

This module makes the record total:

  * every concrete render status maps to exactly one canonical status
    class (RENDER_SUCCEEDED / RENDER_FAILED / RENDER_SKIPPED_LOW_MEMORY
    / RENDER_SKIPPED_INFRA_UNAVAILABLE / RENDER_NOT_RUN — the
    directive's four named states plus the honest split between
    "does not fit in memory" and "renderer unavailable", which are
    different infrastructure states with the same fail-closed result,
    Art. LXI: infrastructure states are never merged into a verdict);
  * every status class has a REQUIRED field set (skips and failures
    must carry a non-empty `reason`; succeeded records must carry the
    artifact inventory; every record carries `visual_gate`, `out_dir`
    — null when no output directory exists — and the two Article
    LXXII booleans);
  * `finalize_render_record` fills the defaults deterministically
    (fail-closed: a record without a measured gate verdict carries
    verdict NOT_RUN, hero suppressed, release blocked);
  * `validate_render_record` raises BEFORE consumer logic on any
    violation — consumers call it instead of guessing which fields
    exist (the Attack-4 contract).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

RECORD_SCHEMA_VERSION = "R443-1"

GATE_PASS_VERDICT = "COMPLETE_PASS"
GATE_VERDICTS = ("COMPLETE_PASS", "PARTIAL", "NOT_RUN", "FAIL")

# concrete status -> canonical status class. Prefix rule: any
# RENDER_SKIPPED_* maps to RENDER_SKIPPED_INFRA_UNAVAILABLE unless it
# is the memory state itself (the typed memory guard keeps its own
# class — the directive names it explicitly).
STATUS_CLASS: Dict[str, str] = {
    "OK": "RENDER_SUCCEEDED",
    "PARTIAL": "RENDER_SUCCEEDED",
    "RENDER_PARTIAL": "RENDER_SUCCEEDED",   # completed, gaps disclosed
    "RENDER_FAILED": "RENDER_FAILED",
    "RENDER_TIMEOUT": "RENDER_FAILED",
    "RENDER_SKIPPED_LOW_MEMORY": "RENDER_SKIPPED_LOW_MEMORY",
    "RENDER_SKIPPED_NO_RENDERER": "RENDER_SKIPPED_INFRA_UNAVAILABLE",
    "RENDER_SKIPPED_NO_RENDERER_DEPS": "RENDER_SKIPPED_INFRA_UNAVAILABLE",
    "RENDER_SKIPPED_NO_SOURCE_GLB": "RENDER_SKIPPED_INFRA_UNAVAILABLE",
    "RENDER_SCRIPT_MISSING": "RENDER_SKIPPED_INFRA_UNAVAILABLE",
    "RENDER_NOT_RUN": "RENDER_NOT_RUN",
}
_STATUS_CLASSES = set(STATUS_CLASS.values())

# fields EVERY record must carry (null allowed where marked)
BASE_REQUIRED = ("stage", "render_pipeline", "status", "status_class",
                 "out_dir", "visual_gate", "hero_suppressed",
                 "release_blocked", "note")
# additional requirements per class (fail-closed extras)
SKIP_FAIL_REQUIRED = ("reason",)          # non-empty
SUCCEEDED_REQUIRED = ("source_glb", "source_glb_sha256", "artifacts",
                      "missing_artifacts")

_NOT_RUN_GATE = {
    "gate_version": "R443-1",
    "verdict": "NOT_RUN",
    "hero_suppressed": True,
    "release_blocked": True,
    "reasons": ["no gate verdict was measured for this render record "
                "(fail closed — Art. V/XXV)"],
    "checks": {},
}


class RenderRecordValidationError(ValueError):
    """A render record violates its status's typed schema. Raised
    BEFORE consumer logic; consumers fail closed on it."""


def status_class(status: Optional[str]) -> Optional[str]:
    """The canonical class of one concrete status (None = unknown —
    and unknown is a validation failure, never silently classified)."""
    if status is None:
        return None
    if status in STATUS_CLASS:
        return STATUS_CLASS[status]
    if status.startswith("RENDER_SKIPPED_"):
        if "VERSION_MISMATCH" in status or "DEPS" in status \
                or "RENDERER" in status or "SOURCE" in status \
                or "SCRIPT" in status:
            return "RENDER_SKIPPED_INFRA_UNAVAILABLE"
        return "RENDER_SKIPPED_INFRA_UNAVAILABLE"
    return None


def finalize_render_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Fill every record to its status's total shape — deterministic,
    fail-closed. Returns the SAME dict (mutated in place) so callers
    keep their identity/aliasing."""
    status = record.get("status") or "RENDER_NOT_RUN"
    cls = status_class(status)
    if cls is None:
        # an unknown status is not silently finalized — but it is also
        # not silently mutated into a known one; mark and let the
        # validator refuse (the caller sees the typed error)
        record.setdefault("schema_unknown_status", True)
        record["status_class"] = record.get("status_class") or "UNKNOWN"
        return record
    record["status"] = status
    record["status_class"] = cls
    record.setdefault("schema_version", RECORD_SCHEMA_VERSION)
    record.setdefault("out_dir", None)
    record.setdefault("note", "")
    record.setdefault("hero_suppressed", True)
    record.setdefault("release_blocked", True)
    gate = record.get("visual_gate")
    if not isinstance(gate, dict) or not gate.get("verdict"):
        record["visual_gate"] = dict(_NOT_RUN_GATE)
    # a non-succeeded record can never claim release (fail closed):
    # any gate verdict a skip/fail record carries is coerced to
    # NOT_RUN — the gate refuses to pass what it cannot measure
    if cls != "RENDER_SUCCEEDED":
        record["hero_suppressed"] = True
        record["release_blocked"] = True
        gate = record["visual_gate"]
        for k, v in (("verdict", "NOT_RUN"), ("hero_suppressed", True),
                     ("release_blocked", True)):
            gate[k] = v
        if not str(record.get("reason") or "").strip():
            record["reason"] = (record.get("note")
                                or record.get("error")
                                or f"render status {status}")
    else:
        if not str(record.get("reason") or "").strip():
            record["reason"] = ""
    return record


def validate_render_record(record: Dict[str, Any]) -> None:
    """Raise RenderRecordValidationError unless the record is
    structurally complete for its status. Consumers run this BEFORE
    reading any other field (Attack 4 contract: a malformed skip
    record never reaches consumer logic)."""
    if not isinstance(record, dict):
        raise RenderRecordValidationError(
            f"render record is not a mapping: {type(record).__name__}")
    status = record.get("status")
    cls = status_class(status)
    errors: List[str] = []
    if cls is None:
        raise RenderRecordValidationError(
            f"render record status {status!r} is not a typed status "
            f"(known: {sorted(set(STATUS_CLASS))})")
    for field in BASE_REQUIRED:
        if field not in record:
            errors.append(f"missing required field {field!r}")
    if errors:
        raise RenderRecordValidationError(
            f"render record for status {status!r} is malformed: "
            f"{'; '.join(errors)}")
    if record.get("status_class") != cls:
        errors.append(
            f"status_class {record.get('status_class')!r} does not "
            f"match the canonical class of status {status!r} ({cls!r})")
    if cls in ("RENDER_SKIPPED_LOW_MEMORY", "RENDER_SKIPPED_INFRA_UNAVAILABLE",
               "RENDER_FAILED", "RENDER_NOT_RUN"):
        for field in SKIP_FAIL_REQUIRED:
            val = record.get(field)
            if not isinstance(val, str) or not val.strip():
                errors.append(f"status {cls} requires a non-empty "
                              f"{field!r} string")
        gate = record.get("visual_gate")
        if not isinstance(gate, dict) or \
                gate.get("verdict") not in GATE_VERDICTS:
            errors.append("visual_gate must carry a typed verdict")
        elif gate.get("verdict") != "NOT_RUN":
            errors.append(
                f"status {cls} cannot carry a measured gate verdict "
                f"({gate.get('verdict')!r}) — the gate refuses to pass "
                "what it cannot measure (Art. XXV)")
        if record.get("hero_suppressed") is not True or \
                record.get("release_blocked") is not True:
            errors.append(
                f"status {cls} must be fail-closed: hero_suppressed and "
                "release_blocked must both be true")
    if cls == "RENDER_SUCCEEDED":
        for field in SUCCEEDED_REQUIRED:
            if field not in record:
                errors.append(
                    f"status RENDER_SUCCEEDED requires field {field!r}")
    if errors:
        raise RenderRecordValidationError(
            f"render record for status {status!r} is malformed: "
            f"{'; '.join(errors)}")

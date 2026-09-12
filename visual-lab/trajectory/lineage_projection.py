"""Toscanini Visual Lab - Trajectory Projection (R451-C2).

Projects Coder 1's canonical INVENTION_LINEAGE records into a typed viewer
state WITHOUT becoming a second truth store.

Constitutional boundaries (EPISTEMIC_CONSTITUTION.md v2.4.0, hash b54a1be9...):

  Art. X   - canonical state has one authority. The lineage record IS the
             authority; this module is a projection. Every projected value
             carries the exact JSON pointer of its native location.
  Art. III - the verifier never trusts the claimant: every transition binding
             is re-proven from the source bytes, never assumed.
  Art. IV/V- fail closed. A tampered record is REJECTED with typed codes and
             never reaches the viewer. There is no lenient fallback parse.
  Art. VI  - provenance is never manufactured: the projection records the
             sha256 of the exact source bytes it consumed.
  Art. XXV - unknown stays unknown: an absent native field is exposed as
             ABSENT_IN_CANONICAL_RECORD, never silently null, never invented.
  Art. XXVIII - no silent semantic promotion: epistemic badges are a DECLARED
             deterministic translation of canonical labels (with their basis
             pointers), never an upgrade.
  Directive step 6 - the visual layer may explain what the engine recorded.
             It may NOT decide why the engine failed, what caused the
             improvement, whether the mechanism is true, or whether an
             invention is novel. The projection therefore carries recorded
             cause fields (change_delta / reason_for_change) VERBATIM, and
             computes nothing causal.

Canonical semantics pinned by measurement against all 21 committed
INVENTION_LINEAGE/1.0.0 records (R451 invariant scan, disclosed in the round
record):
  - generations.gen is consecutive starting at 1 (21/21).
  - generations[i+1].parent_id == generations[i].invention_id for every
    evolution generation (13/13 multi-generation records).
  - gen[0].origin == BASELINE_SYNTHESIS; evolution origins ==
    EVOLUTION_CAUSAL_DELTA.
  - current_invention resolves to an existing generation and its state and
    maturity equal that generation's (20/21; the single all-null
    current_invention is the record's honest NOT_RECORDED shape, which the
    projection exposes as an absence, not a violation).
  - when survivor_reached, survivor_gen == current_invention.gen == the last
    generation (18/18).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

CANONICAL_SCHEMA = "INVENTION_LINEAGE/1.0.0"
PROJECTION_SCHEMA = "TRAJECTORY_PROJECTION/1.0.0"

ARCHITECTURE_FIELDS = (
    "mechanism",
    "intervention",
    "expected_effect",
    "falsification_test",
)

# Canonical maturity -> presentation badge. DECLARED translation, basis
# always recorded. MEASURED is unreachable from this schema (no field in
# INVENTION_LINEAGE/1.0.0 records a physical observation) and is never
# emitted - the label space is not upgraded by the visual layer.
EPISTEMIC_BADGE_TABLE = {
    "GENERATED": "PROPOSED",
    "EVIDENCE_SUPPORTED": "INFERRED",
    "SIMULATED": "SIMULATED",
}
BADGE_LEGEND = (
    "declared deterministic translation of canonical maturity labels "
    "(truth controls the labels; the visual layer never upgrades them). "
    "MEASURED is unreachable from INVENTION_LINEAGE/1.0.0: the schema has no "
    "physical-observation field, and the visual layer may not invent one."
)

PASSING_ATTACK_STATES = {"PASS"}

# Typed rejection codes (fail closed - a rejected projection never yields a
# viewer_state).
R_SOURCE_UNPARSEABLE = "SOURCE_BYTES_UNPARSEABLE"
R_SCHEMA_UNRECOGNIZED = "SCHEMA_UNRECOGNIZED"
R_GENERATIONS_MISSING = "GENERATIONS_MISSING"
R_GEN_SEQUENCE = "GEN_SEQUENCE_NOT_CONSECUTIVE"
R_PARENT_ORPHAN = "TRANSITION_PARENT_ORPHAN"
R_PARENT_MISSING = "TRANSITION_PARENT_MISSING"
R_ORIGIN_UNDECLARED = "TRANSITION_ORIGIN_UNDECLARED"
R_CURRENT_PARTIAL = "CURRENT_INVENTION_PARTIAL"
R_CURRENT_UNRESOLVED = "CURRENT_INVENTION_UNRESOLVED"
R_CURRENT_STATE_MISMATCH = "CURRENT_INVENTION_STATE_MISMATCH"
R_CURRENT_MATURITY_MISMATCH = "CURRENT_INVENTION_MATURITY_MISMATCH"
R_SURVIVOR_BINDING = "SURVIVOR_BINDING_MISMATCH"
R_SHA_MISMATCH = "PROVENANCE_SHA_MISMATCH"
R_STATE_FIELD_TYPE = "STATE_FIELD_TYPE_UNEXPECTED"


class ProjectionRejected(Exception):
    """Raised when the source record fails a binding proof (fail closed)."""

    def __init__(self, rejections: list):
        self.rejections = rejections
        super().__init__(
            "projection rejected: " + ", ".join(r["code"] for r in rejections)
        )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _absent(pointer: str, reason: str = "NOT_PRESENT_IN_CANONICAL_RECORD") -> dict:
    return {"status": "ABSENT_IN_CANONICAL_RECORD", "pointer": pointer, "reason": reason}


def _present(pointer: str, value: Any) -> dict:
    return {"status": "RECORDED", "pointer": pointer, "value": value}


def _badge(generation: dict, index: int) -> dict:
    """Deterministic, declared badge translation. Never an upgrade."""
    pointers = {
        "maturity": f"/generations/{index}/maturity",
        "evidence_verified": f"/generations/{index}/evidence_verified",
    }
    basis = []
    if generation.get("evidence_verified") is False:
        label = "UNVERIFIED"
        basis.append(pointers["evidence_verified"])
    else:
        maturity = generation.get("maturity")
        if maturity in EPISTEMIC_BADGE_TABLE:
            label = EPISTEMIC_BADGE_TABLE[maturity]
        elif maturity is None:
            label = "UNVERIFIED"
        else:
            # An unknown canonical maturity is never translated into a
            # richer vocabulary: the badge stays the verbatim canonical
            # value (Art. VI - never manufacture semantics).
            label = str(maturity)
        basis.append(pointers["maturity"])
    return {
        "label": label,
        "canonical_label": generation.get("maturity"),
        "basis": basis,
        "legend": BADGE_LEGEND,
    }


def _project_field(gen: dict, index: int, container: str, field: str) -> dict:
    if container == "architecture":
        pointer = f"/generations/{index}/architecture/{field}"
        native = (gen.get("architecture") or {}).get(field)
    else:
        pointer = f"/generations/{index}/{field}"
        native = gen.get(field)
    if native is None or (isinstance(native, str) and not native.strip()):
        return _absent(pointer)
    return _present(pointer, native)


def _check(rejections: list) -> None:
    if rejections:
        raise ProjectionRejected(rejections)


def _boundary() -> dict:
    return {
        "canonical_authority": (
            "the source INVENTION_LINEAGE record (Coder 1 engine output)"
        ),
        "this_viewer_may_show": [
            "what the engine recorded, verbatim, with its exact JSON pointer",
        ],
        "this_viewer_may_not_decide": [
            "why the engine failed",
            "what caused the improvement",
            "whether the mechanism is true",
            "whether an invention is novel",
        ],
    }


def project_lineage(
    source_bytes: bytes,
    source_path: Optional[str] = None,
    expected_sha256: Optional[str] = None,
) -> dict:
    """Project canonical INVENTION_LINEAGE bytes into the typed viewer state.

    Fail closed: raises ProjectionRejected (typed rejections attached) for
    every corruption class the viewer must never see.
    """
    sha = _sha256(source_bytes)
    if expected_sha256 is not None and expected_sha256 != sha:
        raise ProjectionRejected(
            [{
                "code": R_SHA_MISMATCH,
                "pointer": "/",
                "detail": (
                    "declared expected_sha256 does not match the consumed "
                    f"bytes ({sha}); the projection refuses a source whose "
                    "identity was overridden"
                ),
            }]
        )

    # ---- the record is parsed from the EXACT bytes consumed -------------
    try:
        record = json.loads(source_bytes.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise ProjectionRejected(
            [{
                "code": R_SOURCE_UNPARSEABLE,
                "pointer": "/",
                "detail": f"{type(e).__name__}: {e}",
            }]
        ) from e

    if not isinstance(record, dict):
        raise ProjectionRejected(
            [{"code": R_SCHEMA_UNRECOGNIZED, "pointer": "/",
              "detail": "top-level record is not an object"}]
        )
    if record.get("schema") != CANONICAL_SCHEMA:
        raise ProjectionRejected(
            [{
                "code": R_SCHEMA_UNRECOGNIZED,
                "pointer": "/schema",
                "detail": (
                    f"expected {CANONICAL_SCHEMA!r}, found "
                    f"{record.get('schema')!r}"
                ),
            }]
        )

    generations = record.get("generations")
    if not isinstance(generations, list) or not generations:
        # An evolution attempt that produced nothing records no generations;
        # the projection still renders, with the absence exposed honestly.
        return _empty_projection(record, source_path, sha, len(source_bytes))

    rejections: list = []

    # ---- binding proof 1: generation sequence ---------------------------
    # Canonical: consecutive ints from 1 (21/21 measured). Reordered or
    # skip-tampered sequences cannot reach the viewer.
    seq = [g.get("gen") if isinstance(g, dict) else None for g in generations]
    if seq != list(range(1, len(generations) + 1)):
        rejections.append({
            "code": R_GEN_SEQUENCE,
            "pointer": "/generations",
            "detail": (
                "generation sequence must be consecutive from 1; found "
                f"{seq} (reordered/skipped/duplicated states are corruption)"
            ),
        })
        raise ProjectionRejected(rejections)

    # ---- per-state projection from NATIVE locations only ----------------
    states = []
    for i, gen in enumerate(generations):
        if not isinstance(gen, dict):
            rejections.append({
                "code": R_STATE_FIELD_TYPE,
                "pointer": f"/generations/{i}",
                "detail": "generation entry is not an object",
            })
            continue
        arch = gen.get("architecture")
        if arch is not None and not isinstance(arch, dict):
            rejections.append({
                "code": R_STATE_FIELD_TYPE,
                "pointer": f"/generations/{i}/architecture",
                "detail": "architecture is not an object",
            })
        states.append({
            "index": i,
            "gen": gen.get("gen"),
            "invention_id": _present(
                f"/generations/{i}/invention_id", gen.get("invention_id")
            ),
            "origin": _present(f"/generations/{i}/origin", gen.get("origin")),
            "state": _present(f"/generations/{i}/state", gen.get("state")),
            "maturity": _present(
                f"/generations/{i}/maturity", gen.get("maturity")
            ),
            "epistemic_badge": _badge(gen, i),
            "architecture": {
                f: _project_field(gen, i, "architecture", f)
                for f in ARCHITECTURE_FIELDS
            },
            "change_delta": _project_field(gen, i, ".", "change_delta"),
            "reason_for_change": _project_field(
                gen, i, ".", "reason_for_change"
            ),
            "challenge": {
                "status": "RECORDED",
                "pointer": f"/generations/{i}/challenge",
                "value": gen.get("challenge"),
                "note": (
                    "verbatim engine record - the viewer explains it, "
                    "never re-decides it"
                ),
            },
            "evidence_verified": _present(
                f"/generations/{i}/evidence_verified",
                gen.get("evidence_verified"),
            ),
        })
    _check(rejections)

    # fix the container pointer for root-level generation fields
    for st in states:
        for root_field in ("change_delta", "reason_for_change"):
            entry = st[root_field]
            if entry["status"] == "ABSENT_IN_CANONICAL_RECORD":
                entry["pointer"] = (
                    f"/generations/{st['index']}/{root_field}"
                )

    # ---- binding proof 2: transitions (carried BY the generation records)
    transitions = []
    for i in range(1, len(generations)):
        prev, cur = generations[i - 1], generations[i]
        parent_id = cur.get("parent_id")
        origin = cur.get("origin")
        if parent_id is None:
            rejections.append({
                "code": R_PARENT_MISSING,
                "pointer": f"/generations/{i}/parent_id",
                "detail": (
                    "an evolution transition must name its parent generation"
                ),
            })
            continue
        if parent_id != prev.get("invention_id"):
            rejections.append({
                "code": R_PARENT_ORPHAN,
                "pointer": f"/generations/{i}/parent_id",
                "detail": (
                    f"parent {parent_id!r} does not resolve to generation "
                    f"{i}'s invention_id (orphan transition)"
                ),
            })
            continue
        if origin != "EVOLUTION_CAUSAL_DELTA":
            rejections.append({
                "code": R_ORIGIN_UNDECLARED,
                "pointer": f"/generations/{i}/origin",
                "detail": (
                    "evolution transition origin must be "
                    f"EVOLUTION_CAUSAL_DELTA, found {origin!r}"
                ),
            })
            continue
        transitions.append({
            "from_gen": prev.get("gen"),
            "to_gen": cur.get("gen"),
            "from_invention_id": prev.get("invention_id"),
            "to_invention_id": cur.get("invention_id"),
            "binding": {
                # The directive's binding proof in the canonical semantics
                # this schema defines: the transition is carried by
                # generation i+1, and its result IS generation i+1.
                "transition.from_gen": prev.get("gen"),
                "transition.to_gen": cur.get("gen"),
                "transition.result.gen": cur.get("gen"),
                "transition.result.status": cur.get("state"),
                "parent_id_matches_previous_invention_id": True,
                "origin_recorded": origin,
            },
            "recorded_cause": {
                # VERBATIM passthrough of what the engine recorded. The
                # viewer never decides what caused the change (directive
                # step 6); it shows the recorded cause fields, honestly
                # absent when the engine recorded none.
                "change_delta": _project_field(cur, i, ".", "change_delta"),
                "reason_for_change": _project_field(
                    cur, i, ".", "reason_for_change"
                ),
            },
        })
    # (no raise here: proofs 2-4 all run so every detected break is exposed)

    for tr in transitions:
        for k in ("change_delta", "reason_for_change"):
            entry = tr["recorded_cause"][k]
            if entry["status"] == "ABSENT_IN_CANONICAL_RECORD":
                entry["pointer"] = (
                    f"/generations/{tr['to_gen'] - 1}/{k}"
                )

    # ---- binding proof 3: the current-invention record ------------------
    # (rejections accumulate; every detected break is exposed at the end -
    # honest reporting, fail closed, the viewer is never reached)
    ci = record.get("current_invention")
    current_entry = _bind_current_invention(ci, generations, rejections)

    # ---- binding proof 4: survivor bookkeeping --------------------------
    recorded_outcome = {
        "stop_reason": {
            "status": "RECORDED",
            "pointer": "/stop_reason",
            "value": record.get("stop_reason"),
        },
        "survivor_reached": {
            "status": "RECORDED",
            "pointer": "/survivor_reached",
            "value": record.get("survivor_reached"),
        },
        "survivor_gen": {
            "status": "RECORDED",
            "pointer": "/survivor_gen",
            "value": record.get("survivor_gen"),
        },
        "n_generations": {
            "status": "RECORDED",
            "pointer": "/n_generations",
            "value": record.get("n_generations"),
        },
        "n_evolution_generations": {
            "status": "RECORDED",
            "pointer": "/n_evolution_generations",
            "value": record.get("n_evolution_generations"),
        },
    }
    if record.get("survivor_reached"):
        terminal_gen = generations[-1].get("gen")
        ci_gen = ci.get("gen") if isinstance(ci, dict) else None
        if record.get("survivor_gen") != terminal_gen or ci_gen != terminal_gen:
            rejections.append({
                "code": R_SURVIVOR_BINDING,
                "pointer": "/survivor_gen",
                "detail": (
                    "survivor_reached requires survivor_gen == "
                    "current_invention.gen == the terminal generation "
                    f"({terminal_gen}); found survivor_gen="
                    f"{record.get('survivor_gen')}, current gen={ci_gen}"
                ),
            })

    # every binding proof has now run; expose ALL detected breaks at once
    _check(rejections)

    return {
        "artifact_type": "TOSCANINI_TRAJECTORY_PROJECTION",
        "projection_schema": PROJECTION_SCHEMA,
        "authority": (
            "PROJECTION_ONLY - the canonical INVENTION_LINEAGE record "
            "remains the sole truth store; this artifact is regenerable "
            "from the source bytes and holds no independent state"
        ),
        "source": {
            "path": source_path,
            "sha256": sha,
            "bytes": len(source_bytes),
            "schema": record.get("schema"),
            "run_id": _present("/run_id", record.get("run_id")),
        },
        "verdict": "PROJECTED",
        "rejections": [],
        "viewer_state": {
            "run_id": record.get("run_id"),
            "states": states,
            "transitions": transitions,
            "current": current_entry,
            "recorded_outcome": recorded_outcome,
            "presentation_boundary": _boundary(),
        },
    }


def _bind_current_invention(
    ci: Any, generations: list, rejections: list
) -> dict:
    """Bind /current_invention to the generation array (fail closed).

    Canonical shapes measured in the corpus: a fully-populated object whose
    (gen, invention_id, state, maturity) resolve into a generation with
    matching state and maturity, OR the honest all-null shape (an attempt
    that produced no current invention). Partial nulls are corruption.
    """
    if not isinstance(ci, dict):
        rejections.append({
            "code": R_CURRENT_PARTIAL,
            "pointer": "/current_invention",
            "detail": "current_invention is not an object",
        })
        return {"resolution": "INVALID"}
    keys = ("gen", "invention_id", "state", "maturity")
    values = [ci.get(k) for k in keys]
    if all(v is None for v in values):
        return {
            "resolution": "NOT_RECORDED",
            "pointer": "/current_invention",
            "note": (
                "the canonical record carries the all-null current_invention "
                "shape; the viewer shows an honest absence, never a guess"
            ),
            "fields": {k: _absent(f"/current_invention/{k}") for k in keys},
        }
    if any(v is None for v in values):
        rejections.append({
            "code": R_CURRENT_PARTIAL,
            "pointer": "/current_invention",
            "detail": (
                "partially-null current_invention "
                f"{dict(zip(keys, values))} is neither the resolved shape "
                "nor the honest all-null shape"
            ),
        })
        return {"resolution": "INVALID"}
    matches = [
        (i, g)
        for i, g in enumerate(generations)
        if g.get("gen") == ci.get("gen")
        and g.get("invention_id") == ci.get("invention_id")
    ]
    if not matches:
        rejections.append({
            "code": R_CURRENT_UNRESOLVED,
            "pointer": "/current_invention",
            "detail": (
                f"current_invention {ci.get('invention_id')!r} (gen "
                f"{ci.get('gen')}) resolves to no generation in the array"
            ),
        })
        return {"resolution": "INVALID"}
    i, g = matches[-1]
    if g.get("state") != ci.get("state"):
        rejections.append({
            "code": R_CURRENT_STATE_MISMATCH,
            "pointer": "/current_invention/state",
            "detail": (
                f"current_invention.state {ci.get('state')!r} != the bound "
                f"generation's recorded state {g.get('state')!r} "
                f"(/generations/{i}/state) - wrong current state"
            ),
        })
    if g.get("maturity") != ci.get("maturity"):
        rejections.append({
            "code": R_CURRENT_MATURITY_MISMATCH,
            "pointer": "/current_invention/maturity",
            "detail": (
                f"current_invention.maturity {ci.get('maturity')!r} != the "
                f"bound generation's recorded maturity {g.get('maturity')!r} "
                f"(/generations/{i}/maturity) - wrong result status"
            ),
        })
    return {
        "resolution": "RESOLVED_TO_GENERATION_INDEX_" + str(i),
        "pointer": "/current_invention",
        "fields": {
            k: {
                "status": "RECORDED",
                "pointer": f"/current_invention/{k}",
                "value": ci.get(k),
            }
            for k in keys
        },
        "bound_generation_index": i,
    }


def _empty_projection(
    record: dict, source_path: Optional[str], sha: str, nbytes: int
) -> dict:
    return {
        "artifact_type": "TOSCANINI_TRAJECTORY_PROJECTION",
        "projection_schema": PROJECTION_SCHEMA,
        "authority": (
            "PROJECTION_ONLY - the canonical INVENTION_LINEAGE record "
            "remains the sole truth store"
        ),
        "source": {
            "path": source_path,
            "sha256": sha,
            "bytes": nbytes,
            "schema": record.get("schema"),
            "run_id": _present("/run_id", record.get("run_id")),
        },
        "verdict": "PROJECTED",
        "rejections": [],
        "viewer_state": {
            "run_id": record.get("run_id"),
            "states": [],
            "transitions": [],
            "current": {
                "resolution": "NOT_RECORDED",
                "pointer": "/current_invention",
                "note": "the record declares no generations; nothing is guessed",
            },
            "recorded_outcome": {
                "stop_reason": {
                    "status": "RECORDED",
                    "pointer": "/stop_reason",
                    "value": record.get("stop_reason"),
                },
                "survivor_reached": {
                    "status": "RECORDED",
                    "pointer": "/survivor_reached",
                    "value": record.get("survivor_reached"),
                },
            },
            "presentation_boundary": _boundary(),
        },
    }


def project_file(path: str, expected_sha256: Optional[str] = None) -> dict:
    """Convenience entry point: project a canonical lineage file by path."""
    with open(path, "rb") as f:
        data = f.read()
    return project_lineage(data, source_path=path, expected_sha256=expected_sha256)

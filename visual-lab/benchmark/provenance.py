"""R449 Step 8: the provenance contract for every generated visual artifact.

A generated mesh/render is a DERIVED artifact (Art. VI, Art. XXXVIII's
evidence-layer discipline): it may never carry engineering authority, and it
must carry its full derivation provenance. Every sidecar produced by the
benchmark lab carries exactly these fields; validate() BLOCKS (typed) any
record that is missing or malformed, per Art. IV (fail closed) / Art. V.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "source_glb_sha",
    "model_id",
    "model_revision",
    "model_license",
    "hf_space_or_job",
    "hardware",
    "input_hash",
    "output_hash",
    "timestamp",
    "benchmark_version",
    "visual_role",
)

BENCHMARK_VERSION = "R449-visual-benchmark-1.0.0"

VISUAL_ROLES = (
    "REFEREE_MEASUREMENT",
    "PRESENTATION_CANDIDATE",
    "NEGATIVE_CONTROL",
    "REFERENCE_RENDER",
)


class ProvenanceError(RuntimeError):
    """Typed failure: a generated artifact lacks its derivation provenance."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def make_sidecar(**fields: Any) -> dict:
    missing = [k for k in REQUIRED_FIELDS if fields.get(k) in (None, "")]
    if missing:
        raise ProvenanceError(f"cannot create sidecar: missing fields {missing}")
    if fields["visual_role"] not in VISUAL_ROLES:
        raise ProvenanceError(f"visual_role must be one of {VISUAL_ROLES}")
    sidecar = dict(fields)
    sidecar["benchmark_version"] = BENCHMARK_VERSION
    sidecar["engineering_authority"] = "NONE_PRESENTATION_ONLY"
    return sidecar


def validate(record: dict) -> None:
    """Fail-closed validation. Raises ProvenanceError on any gap (Art. IV)."""
    if not isinstance(record, dict):
        raise ProvenanceError("sidecar must be a JSON object")
    missing = [k for k in REQUIRED_FIELDS if record.get(k) in (None, "")]
    if missing:
        raise ProvenanceError(f"PROVENANCE_INCOMPLETE: missing {missing}")
    if record.get("visual_role") not in VISUAL_ROLES:
        raise ProvenanceError(f"unknown visual_role: {record.get('visual_role')!r}")
    if "engineering_authority" in record and \
            record["engineering_authority"] != "NONE_PRESENTATION_ONLY":
        raise ProvenanceError(
            "generated visual artifacts can never claim engineering authority")


def validate_file(sidecar_path) -> dict:
    record = json.loads(Path(sidecar_path).read_text())
    validate(record)
    return record

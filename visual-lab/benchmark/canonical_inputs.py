"""R449: canonical benchmark inputs — loader-free GLB reading + case registry.

The benchmark consumes ONLY the R446/R447-verified canonical GLB bytes frozen in
the canonical repository (R446/HF_PRODUCTION_RUNS/, sha-verified by
scripts/r449_reconcile_inputs.py -> R449/BENCHMARK_INPUT_RECONCILIATION.json).
This module gives the benchmark a structural reader that does NOT depend on any
single mesh library for IDENTITY decisions (loader-free glTF JSON chunk parse,
the R443/R446/R447 house discipline); trimesh is used only for geometric
measurement inside metrics.py.
"""
import json
import struct
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CANONICAL_CASES = {
    "A": {
        "case_id": "hf-case-a-cold-plate",
        "directive_class": "Case A: fresh multi-component engineering problem",
        "benchmark_role": "multi-component",
        "run_id": "ts_cd737f153f70",
        "glb_rel": "R446/HF_PRODUCTION_RUNS/ts_cd737f153f70_canonical.glb",
        "sha256": "54e82cc1d030e8203c6a6480fb2b02e93723db14999af930e31c4b089bd36941",
    },
    "B": {
        "case_id": "hf-case-b-piezo-tile",
        "directive_class": "Case B: fresh structurally different engineering problem",
        "benchmark_role": "structurally-different",
        "run_id": "ts_3a5d419028a3",
        "glb_rel": "R446/HF_PRODUCTION_RUNS/ts_3a5d419028a3_canonical.glb",
        "sha256": "fb439c90226d5df7732a918cb5b4461b6a23175d5bd156c6b7e3b6badc5e16a6",
    },
    "C": {
        "case_id": "hf-case-c-microchannel-hx",
        "directive_class": "Case C: large/high-detail geometry stress case",
        "benchmark_role": "high-detail",
        "run_id": "ts_e24b5247333f",
        "glb_rel": "R446/HF_PRODUCTION_RUNS/ts_e24b5247333f_canonical.glb",
        "sha256": "f99ccc083fab11edc59829fdb8d25c6bf5d5cc2387fdabfe136cc1464f380ffa",
    },
}


def parse_glb(path) -> dict:
    """Loader-free parse of a GLB: returns the glTF JSON document plus BIN bytes."""
    raw = Path(path).read_bytes()
    if raw[:4] != b"glTF":
        raise ValueError(f"not a GLB: {path}")
    _version, _length = struct.unpack_from("<II", raw, 4)
    offset = 12
    doc = None
    bin_chunk = b""
    while offset < len(raw):
        chunk_len, chunk_type = struct.unpack_from("<I4s", raw, offset)
        body = raw[offset + 8 : offset + 8 + chunk_len]
        if chunk_type == b"JSON":
            doc = json.loads(body.decode("utf-8"))
        elif chunk_type == b"BIN\0":
            bin_chunk = body
        offset += 8 + chunk_len
    if doc is None:
        raise ValueError(f"no JSON chunk in {path}")
    return {"doc": doc, "bin": bin_chunk, "raw": raw}


def mesh_node_names(parsed: dict) -> list:
    """Names of nodes that carry a mesh = the rendered geometry components."""
    return [n.get("name") for n in parsed["doc"].get("nodes", []) if "mesh" in n]


def material_names(parsed: dict) -> list:
    return [m.get("name") for m in parsed["doc"].get("materials", [])]


def case_glb_path(case_letter: str) -> Path:
    return REPO / CANONICAL_CASES[case_letter]["glb_rel"]

"""tests/test_r399_w5_stl_dedup.py — R399 W5: byte-dedup of section
STLs for FUTURE package generation.

The pinned portfolio is an Article XXXIX authority boundary — untouched
(the tests below never read or write the portfolio). What is tested is
the GENERATOR behavior for future packages:

  - a section export whose STL bytes are identical to a mesh the
    package already carries ships a REFERENCE (canonical relpath +
    sha256 + reason), not a duplicate file;
  - a distinct mesh ships normally (the dedup never eats real geometry);
  - the reference's render_path resolves to the canonical file (the
    render pipeline consumes the same bytes -> the same image).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

# the augment script's module-level import of r384_render_lib resolves
# when its own directory is on sys.path (the same condition as running
# `python scripts/r384_3d_evidence_augment.py`)
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import importlib
aug = importlib.import_module("r384_3d_evidence_augment")  # noqa: E402


# A minimal valid binary STL (a flat zero-volume triangle is fine for
# byte-identity purposes; trimesh parses it as a mesh with 1 face).
def _stl_bytes(marker: str = "A") -> bytes:
    header = f"R399W5-{marker}".encode().ljust(80, b"\0")
    n_faces = struct.pack("<I", 1)
    tri = struct.pack("<12fH",
                      0.0, 0.0, 0.0,   # normal
                      0.0, 0.0, 0.0,
                      1.0, 0.0, 0.0,
                      0.0, 1.0, 0.0,
                      0)               # attribute
    return header + n_faces + tri


class _StubCut:
    """The OCCT-shape surface export_cut_solid uses (exportStep /
    exportStl / .wrapped for the cache-clear attempt)."""

    def __init__(self, marker: str):
        self._marker = marker
        self.wrapped = object()   # BRepTools.Clean_s attempt is try/except

    def exportStep(self, path: str):
        Path(path).write_bytes(b"STEP-" + self._marker.encode())

    def exportStl(self, path: str, tolerance=None, angularTolerance=None):
        Path(path).write_bytes(_stl_bytes(self._marker))

    def Volume(self) -> float:
        return 1.0


def test_identical_mesh_ships_a_reference_not_a_copy(tmp_path):
    ev = tmp_path / "3D_EVIDENCE"
    ev.mkdir()
    # the package already carries this exact mesh (seeded index entry)
    canonical_mesh = tmp_path / "P-XX_disc.stl"
    canonical_mesh.write_bytes(_stl_bytes("A"))
    dedup_index = {aug.sha256_file(canonical_mesh): (
        "MODEL/P-XX_disc.stl", str(canonical_mesh))}

    info = aug.export_cut_solid(_StubCut("A"), ev, "P-XX", "disc",
                                "transverse", dedup_index=dedup_index)
    # the duplicate file was NOT shipped
    assert not (ev / "P-XX_disc_section_transverse_solid.stl").exists()
    assert info["stl"] is None
    ref = info["stl_reference"]
    assert ref["canonical"] == "MODEL/P-XX_disc.stl"
    assert ref["sha256"] == aug.sha256_file(canonical_mesh)
    assert Path(ref["render_path"]).read_bytes() == _stl_bytes("A")
    assert "byte-identical" in ref["reason"]
    # the STEP B-rep still ships (B-reps are not byte-deduped)
    assert info["step"].endswith(".step")
    assert (ev / "P-XX_disc_section_transverse_solid.step").exists()


def test_distinct_mesh_ships_normally(tmp_path):
    ev = tmp_path / "3D_EVIDENCE"
    ev.mkdir()
    canonical_mesh = tmp_path / "P-XX_disc.stl"
    canonical_mesh.write_bytes(_stl_bytes("A"))
    dedup_index = {aug.sha256_file(canonical_mesh): (
        "MODEL/P-XX_disc.stl", str(canonical_mesh))}

    info = aug.export_cut_solid(_StubCut("B"), ev, "P-XX", "disc",
                                "transverse", dedup_index=dedup_index)
    assert info["stl"] == ("MODEL/3D_EVIDENCE/"
                           "P-XX_disc_section_transverse_solid.stl")
    assert (ev / "P-XX_disc_section_transverse_solid.stl").exists()
    assert "stl_reference" not in info
    # and the new mesh is registered so a SECOND identical export
    # references IT (intra-section dedup: the coupon == transverse case)
    info2 = aug.export_cut_solid(_StubCut("B"), ev, "P-XX", "disc",
                                 "transverse", suffix="_coupon",
                                 dedup_index=dedup_index)
    assert info2["stl"] is None
    assert info2["stl_reference"]["canonical"] == (
        "MODEL/3D_EVIDENCE/P-XX_disc_section_transverse_solid.stl")


def test_no_dedup_index_ships_everything(tmp_path):
    """The default path (no index) is unchanged — dedup is opt-in at
    the augment_package call site, never a global behavior."""
    ev = tmp_path / "3D_EVIDENCE"
    ev.mkdir()
    info = aug.export_cut_solid(_StubCut("A"), ev, "P-XX", "disc",
                                "transverse")
    assert info["stl"] is not None
    assert (ev / "P-XX_disc_section_transverse_solid.stl").exists()

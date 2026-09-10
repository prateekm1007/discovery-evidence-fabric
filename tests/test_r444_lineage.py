"""R444-C2 — buyer-surface lineage verification (visual_compiler/lineage.py).

The R444 directive: "verify exact artifact lineage: GEOMETRY_SPEC hash
-> GLB hash -> render source hash -> hero hash -> poster hash -> PDF
embedded image hash/source."

These tests prove the verifier on the REAL production code paths:
  positive  live Visual Compiler run (COMPLETE_PASS) + the REAL
            package._pdf cover contract + the REAL suppression contract
            -> lineage VERIFIED with every link measured;
  negative  swapped hero bytes, a dossier whose embedded page-1 image is
            NOT the approved render, a suppression bypass (hero present
            under a failed verdict), stripped/legacy records, and a
            tampered engineering identity — every one FAILs or is typed
            INCOMPLETE, never an assumed pass.

Live tests require the headless Chromium/Node pair (same skipif contract
as tests/test_r443_visual_integrity.py). No threshold is touched by this
battery; it reads bytes and pixels only.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.visual_compiler import lineage as lin  # noqa: E402
from discovery_fabric.engine.visual_compiler import visual_compiler as vc  # noqa: E402


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _chrome_available() -> bool:
    try:
        from discovery_fabric.engine.visual_compiler import render_worker
        return bool(render_worker.find_node()
                    and render_worker.find_chrome()
                    and render_worker.renderer_deps_present() is None)
    except Exception:  # noqa: BLE001
        return False


def _box(extents, translation=None):
    import trimesh
    b = trimesh.creation.box(extents=extents)
    if translation is not None:
        b = b.apply_translation(translation)
    return b


def _three_part_glb(tmp_path: Path) -> Path:
    """Three separated parts (the same shape family the R443 live
    battery uses)."""
    import trimesh
    (tmp_path / "MODEL").mkdir(parents=True, exist_ok=True)
    s = trimesh.Scene({
        "part_001_chassis": _box([24, 12, 8]),
        "part_002_mast": trimesh.creation.cylinder(
            radius=4, height=28, sections=48).apply_translation(
            [0, 0, 20]),
        "part_003_cap": _box([10, 10, 2], [0, 0, 36]),
    })
    out = tmp_path / "MODEL" / "engineering_model.glb"
    s.export(out, file_type="glb")
    return out


def _compile_live(tmp_path: Path) -> dict:
    _three_part_glb(tmp_path)
    rec = vc.compile_visuals(str(tmp_path), memory_mode="async",
                             context="r444_lineage_battery")
    assert rec["status"] in ("OK", "PARTIAL"), rec
    gate = rec.get("visual_gate") or {}
    assert gate.get("verdict") == "COMPLETE_PASS", gate
    return rec


def _write_release_state(root: Path, verdict: str,
                         suppressed: bool) -> None:
    (root / "MODEL" / "3D" / "HERO_RELEASE_STATE.json").write_text(
        json.dumps({
            "artifact": "HERO_RELEASE_STATE",
            "article": "LXXII",
            "gate_verdict": verdict,
            "hero_suppressed": suppressed,
            "release_blocked": suppressed,
            "failed_rules": [],
            "reasons": [],
        }, indent=2))


def _build_dossier(root: Path, cover_image: Path,
                   gate_label: str = "COMPLETE_PASS") -> Path:
    """The REAL production PDF path (package._pdf) with an Article LXXII
    cover built over the given image — exactly what package.assemble
    does when the release is allowed."""
    from discovery_fabric.engine.invention_bridge import package as _pkg
    essay = {
        "section_order": ["summary"],
        "sections": {"summary": "Lineage verification dossier body."},
        "titles": {"summary": "Summary"},
        "__cover__": {
            "gate": gate_label,
            "label": "lineage battery",
            "hero": str(cover_image),
        },
    }
    pdf_bytes = _pkg._pdf("Lineage Battery", "R444-C2", essay)
    out = root / "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"
    out.write_bytes(pdf_bytes)
    return out


def _build_plain_pdf(root: Path) -> Path:
    from discovery_fabric.engine.invention_bridge import package as _pkg
    pdf_bytes = _pkg._pdf(
        "Readme", "R444-C2",
        {"section_order": ["s"], "sections": {"s": "plain doc"},
         "titles": {"s": "s"}})
    out = root / "00_PACKAGE_README.pdf"
    out.write_bytes(pdf_bytes)
    return out


def _write_engineering_identity(root: Path) -> Dict[str, str]:
    """Mirror the REAL bridge outputs (bridge.py -> artifact_identity):
    GEOMETRY_SPEC.spec_sha256 == ARTIFACT_IDENTITY.source_geometry_hash,
    ARTIFACT_IDENTITY.geometry_hash == the canonical GLB bytes."""
    glb = root / "MODEL" / "engineering_model.glb"
    spec = {"spec_version": "lineage-battery",
            "components": [{"name": "part_001_chassis"}]}
    spec_sha = hashlib.sha256(
        json.dumps(spec, sort_keys=True).encode()).hexdigest()
    spec["spec_sha256"] = spec_sha
    (root / "MODEL" / "GEOMETRY_SPEC.json").write_text(
        json.dumps(spec, indent=2))
    identity = {
        "artifact": "ARTIFACT_IDENTITY",
        "geometry_hash": _sha(glb),
        "source_geometry_hash": spec_sha,
    }
    (root / "MODEL" / "ARTIFACT_IDENTITY.json").write_text(
        json.dumps(identity, indent=2))
    return identity


@pytest.mark.skipif(not _chrome_available(),
                    reason="headless Chromium/Node pair not available")
class TestLiveReleasedLineage:
    @pytest.fixture(scope="class")
    def released(self, tmp_path_factory):
        root = tmp_path_factory.mktemp("r444_released")
        rec = _compile_live(root)
        _write_release_state(root, "COMPLETE_PASS", False)
        _build_dossier(root, root / "MODEL" / "3D" / "hero.png")
        _build_plain_pdf(root)
        _write_engineering_identity(root)
        return root, rec

    def test_full_chain_verifies(self, released):
        root, rec = released
        r = lin.verify_package_lineage(str(root))
        assert r["verdict"] == "VERIFIED", json.dumps(r, indent=1)[:2000]
        assert r["incomplete_links"] == []
        checks = r["checks"]
        assert checks["render_source"]["state"] == "VERIFIED"
        assert checks["render_source"]["measured_glb_sha256"] == \
            rec["source_glb_sha256"]
        # 23-artifact ladder: every hashed view re-measured
        assert checks["artifact_bytes"]["views_remeasured"] >= 21
        assert checks["release_state"]["release_allowed"] is True
        # the PDF leg: dossier page 1 IS the gate-approved hero pixels
        pdf_check = checks["pdf_embedded_hero"]
        assert pdf_check["state"] == "VERIFIED"
        dossier = [p for p in pdf_check["pdfs"]
                   if "DOSSIER" in p["pdf"]][0]
        assert dossier["page1_images"] >= 1
        assert dossier["hero_pixel_sha256"] == _sha256_pixels(
            root / "MODEL" / "3D" / "hero.png")
        # the engineering leg
        assert checks["geometry_spec_link"]["state"] == "VERIFIED"
        assert checks["geometry_spec_link"]["spec_sha256"] == \
            checks["geometry_spec_link"]["source_geometry_hash"]
        assert checks["geometry_spec_link"][
            "measured_canonical_glb_sha256"] == _sha(
                root / "MODEL" / "engineering_model.glb")

    def test_verifier_is_read_only(self, released):
        root, _rec = released
        before = {str(p.relative_to(root)): _sha(p)
                  for p in sorted(root.rglob("*")) if p.is_file()}
        lin.verify_package_lineage(str(root))
        after = {str(p.relative_to(root)): _sha(p)
                 for p in sorted(root.rglob("*")) if p.is_file()}
        assert before == after  # Art. IX: certification modifies nothing


def _sha256_pixels(img_path: Path) -> str:
    from PIL import Image
    img = Image.open(img_path).convert("RGB")
    return hashlib.sha256(img.tobytes()).hexdigest()


@pytest.mark.skipif(not _chrome_available(),
                    reason="headless Chromium/Node pair not available")
class TestLiveNegativeLineage:
    @pytest.fixture(scope="class")
    def clean(self, tmp_path_factory):
        root = tmp_path_factory.mktemp("r444_negative_base")
        _compile_live(root)
        _write_release_state(root, "COMPLETE_PASS", False)
        _build_dossier(root, root / "MODEL" / "3D" / "hero.png")
        _write_engineering_identity(root)
        return root

    def _fresh(self, clean, tmp_path):
        work = tmp_path / "case"
        shutil.copytree(clean, work)
        return work

    def test_swapped_hero_bytes_fail(self, clean, tmp_path):
        work = self._fresh(clean, tmp_path)
        hero = work / "MODEL" / "3D" / "hero.png"
        original = hero.read_bytes()
        # one-pixel-tampered PNG at the same size: a substituted artifact
        from PIL import Image
        img = Image.open(io.BytesIO(original)).convert("RGB")
        px = img.load()
        px[img.width // 2, img.height // 2] = (255, 0, 255)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        hero.write_bytes(buf.getvalue())
        r = lin.verify_package_lineage(str(work))
        assert r["verdict"] == "FAIL"
        assert r["checks"]["artifact_bytes"]["state"] == "FAIL"
        # and the PDF leg independently fires: the shipped dossier embeds
        # the ORIGINAL render while the package hero was swapped
        pdfs = r["checks"]["pdf_embedded_hero"]["pdfs"]
        assert any(not p["pass"] for p in pdfs)

    def test_wrong_pdf_cover_fails(self, clean, tmp_path):
        work = self._fresh(clean, tmp_path)
        # rebuild the dossier with a DIFFERENT image as the page-1 cover
        # (a valid-looking render that is not the approved hero)
        from PIL import Image
        fake = work / "_fake_cover.png"
        Image.new("RGB", (640, 480), (20, 180, 90)).save(fake)
        _build_dossier(work, fake)
        fake.unlink()
        r = lin.verify_package_lineage(str(work))
        assert r["verdict"] == "FAIL"
        pdf_check = r["checks"]["pdf_embedded_hero"]
        assert pdf_check["state"] == "FAIL"
        dossier = [p for p in pdf_check["pdfs"] if "DOSSIER" in p["pdf"]][0]
        assert "NOT pixel-identical" in dossier["reason"]
        # the byte leg still verifies — the substitution is PDF-only
        assert r["checks"]["artifact_bytes"]["state"] == "VERIFIED"

    def test_suppression_bypass_fails(self, clean, tmp_path):
        work = self._fresh(clean, tmp_path)
        # gate failed on the buyer surface but the hero stayed shipped
        _write_release_state(work, "FAIL", True)
        (work / "MODEL" / "3D" / "HERO_SUPPRESSED.txt").write_text("x")
        r = lin.verify_package_lineage(str(work))
        assert r["verdict"] == "FAIL"
        rs = r["checks"]["release_state"]
        assert rs["state"] == "FAIL"
        assert rs["hero_present"] is True
        assert rs["release_allowed"] is False

    def test_suppressed_package_lineage_consistent(self, clean, tmp_path):
        """The CORRECT fail-closed shape: suppression removes exactly
        hero.png/poster.png, ships no cover image, and every remaining
        link still re-measures — lineage VERIFIED as consistent."""
        work = self._fresh(clean, tmp_path)
        # production suppression: the gate FAILED and every downstream
        # surface carries that verdict (gate json == release state)
        gate_path = work / "MODEL" / "3D" / "visual_gate.json"
        gate = json.loads(gate_path.read_text())
        gate.update({"verdict": "FAIL",
                     "failed_rules": ["hero_occupancy"],
                     "reasons": ["battery: simulated measured failure"],
                     "hero_suppressed": True,
                     "release_blocked": True})
        gate_path.write_text(json.dumps(gate, indent=2))
        _write_release_state(work, "FAIL", True)
        (work / "MODEL" / "3D" / "hero.png").unlink()
        (work / "MODEL" / "3D" / "poster.png").unlink()
        (work / "MODEL" / "3D" / "HERO_SUPPRESSED.txt").write_text("x")
        # rebuild the dossier WITHOUT a cover (gate did not pass)
        from discovery_fabric.engine.invention_bridge import package as _pkg
        pdf_bytes = _pkg._pdf(
            "Lineage Battery", "R444-C2",
            {"section_order": ["s"], "sections": {"s": "body"},
             "titles": {"s": "s"}})
        (work / "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"
         ).write_bytes(pdf_bytes)
        r = lin.verify_package_lineage(str(work))
        assert r["verdict"] == "VERIFIED", json.dumps(r, indent=1)[:2000]
        rs = r["checks"]["release_state"]
        assert rs["release_allowed"] is False
        dossier = [p for p in
                   r["checks"]["pdf_embedded_hero"]["pdfs"]
                   if "DOSSIER" in p["pdf"]][0]
        assert dossier["page1_images"] == 0

    def test_missing_record_is_incomplete(self, clean, tmp_path):
        work = self._fresh(clean, tmp_path)
        (work / "MODEL" / "3D" / "render_record.json").unlink()
        r = lin.verify_package_lineage(str(work))
        assert r["verdict"] == "INCOMPLETE"
        assert "render_source" in r["incomplete_links"]

    def test_legacy_record_fails_closed(self, clean, tmp_path):
        """An R442-era record (no source_glb_sha256, no per-view hashes)
        cannot survive the R443 typed schema — the render-source link
        FAILs closed, it is never assumed (Art. XXV: unknown stays
        unknown; Art. IV: no weaker fallback path)."""
        work = self._fresh(clean, tmp_path)
        rec_path = work / "MODEL" / "3D" / "render_record.json"
        rec = json.loads(rec_path.read_text())
        legacy = {k: v for k, v in rec.items()
                  if k not in ("source_glb_sha256", "views",
                               "scene_spec_sha256")}
        rec_path.write_text(json.dumps(legacy))
        r = lin.verify_package_lineage(str(work))
        assert r["verdict"] == "FAIL"
        rs = r["checks"]["render_source"]
        assert rs["state"] == "FAIL"
        assert "does not validate" in rs["reason"]


class TestGeometrySpecLink:
    """The engineering leg, unit-level (no live render needed)."""

    def _tree(self, tmp_path, glb_bytes: bytes):
        (tmp_path / "MODEL" / "3D").mkdir(parents=True)
        (tmp_path / "MODEL" / "engineering_model.glb").write_bytes(
            glb_bytes)
        from discovery_fabric.engine.visual_compiler import \
            render_record_schema as _rrs
        rec = {"stage": "RENDER", "render_pipeline":
               "VISUAL_COMPILER_HEADLESS_THREE", "status": "OK",
               "out_dir": str(tmp_path / "MODEL" / "3D"),
               "visual_gate": {"verdict": "NOT_RUN",
                               "hero_suppressed": True,
                               "release_blocked": True},
               "hero_suppressed": True, "release_blocked": True,
               "note": "battery unit tree",
               "source_glb": str(tmp_path / "MODEL" /
                                 "engineering_model.glb"),
               "source_glb_sha256": hashlib.sha256(glb_bytes).hexdigest(),
               "artifacts": [], "missing_artifacts": []}
        _rrs.finalize_render_record(rec)
        _rrs.validate_render_record(rec)
        (tmp_path / "MODEL" / "3D" / "render_record.json").write_text(
            json.dumps(rec))
        return tmp_path

    def test_tampered_geometry_hash_fails(self, tmp_path):
        import trimesh
        buf = io.BytesIO()
        trimesh.creation.box(extents=[1, 1, 1]).export(
            buf, file_type="glb")
        root = self._tree(tmp_path, buf.getvalue())
        spec_sha = hashlib.sha256(b"spec").hexdigest()
        (root / "MODEL" / "GEOMETRY_SPEC.json").write_text(
            json.dumps({"spec_sha256": spec_sha}))
        (root / "MODEL" / "ARTIFACT_IDENTITY.json").write_text(
            json.dumps({"geometry_hash": "0" * 64,
                        "source_geometry_hash": spec_sha}))
        r = lin.verify_package_lineage(str(root))
        assert r["verdict"] == "FAIL"
        link = r["checks"]["geometry_spec_link"]
        assert link["state"] == "FAIL"
        assert any("geometry_hash" in p for p in link["problems"])

    def test_spec_identity_disagreement_fails(self, tmp_path):
        import trimesh
        buf = io.BytesIO()
        trimesh.creation.box(extents=[1, 1, 1]).export(
            buf, file_type="glb")
        root = self._tree(tmp_path, buf.getvalue())
        glb_sha = hashlib.sha256(buf.getvalue()).hexdigest()
        (root / "MODEL" / "GEOMETRY_SPEC.json").write_text(
            json.dumps({"spec_sha256": "a" * 64}))
        (root / "MODEL" / "ARTIFACT_IDENTITY.json").write_text(
            json.dumps({"geometry_hash": glb_sha,
                        "source_geometry_hash": "b" * 64}))
        r = lin.verify_package_lineage(str(root))
        assert r["verdict"] == "FAIL"
        link = r["checks"]["geometry_spec_link"]
        assert any("spec_sha256" in p for p in link["problems"])

    def test_missing_links_incomplete(self, tmp_path):
        import trimesh
        buf = io.BytesIO()
        trimesh.creation.box(extents=[1, 1, 1]).export(
            buf, file_type="glb")
        root = self._tree(tmp_path, buf.getvalue())
        r = lin.verify_package_lineage(str(root))
        assert r["verdict"] == "INCOMPLETE"
        assert "geometry_spec_link" in r["incomplete_links"]
        assert "never assumed" in \
            r["checks"]["geometry_spec_link"]["reason"]

    def test_wrong_source_glb_fails(self, tmp_path):
        """The package ships a DIFFERENT GLB than the render consumed —
        the L1 substitution catch (unit level)."""
        import trimesh
        buf_a = io.BytesIO()
        trimesh.creation.box(extents=[1, 1, 1]).export(
            buf_a, file_type="glb")
        buf_b = io.BytesIO()
        trimesh.creation.box(extents=[2, 1, 1]).export(
            buf_b, file_type="glb")
        root = self._tree(tmp_path, buf_a.getvalue())
        # ship B, but the render record consumed A
        (root / "MODEL" / "engineering_model.glb").write_bytes(
            buf_b.getvalue())
        rec_path = root / "MODEL" / "3D" / "render_record.json"
        rec = json.loads(rec_path.read_text())
        rec["source_glb_sha256"] = hashlib.sha256(
            buf_a.getvalue()).hexdigest()
        rec_path.write_text(json.dumps(rec))
        r = lin.verify_package_lineage(str(root))
        assert r["verdict"] == "FAIL"
        rs = r["checks"]["render_source"]
        assert rs["state"] == "FAIL"
        assert "substitution" in rs["reason"]

"""R389 product-surface tests — the job API, showcase, and the honest
interactive evaluator, exercised through the REAL handler code (no network
needed: the HTTP handler functions are invoked directly with the same
dictionaries the wire carries; showcase reads the real portfolio tree and
SKIPS when that checkout is absent, as in CI).

Constitutional anchors:
- Art. III   the alias routes must be the SAME path, not a second one.
- Art. IV    out-of-envelope / unbound parameters are REFUSED, never
             silently clamped.
- Art. IX    evaluate writes only to TOSCANINI_UI/previews; canonical
             portfolio bytes are untouched (byte-compare before/after).
- Art. XXVIII/XXXVIII rebuild outputs stay COMPUTATIONAL_RESULT; the
             package's loop_verification_state is untouched.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import showcase as show  # noqa: E402
from toscanini import server as srv  # noqa: E402

HAS_PORTFOLIO = (REPO.parent / "portfolio" / "DOWNLOAD").exists()

pytestmark = pytest.mark.skipif(
    not HAS_PORTFOLIO,
    reason="portfolio buyer-distribution checkout not present (CI engine-only)")


# ---------------------------------------------------------------------------
# showcase listing / detail
# ---------------------------------------------------------------------------

def test_showcase_lists_the_three_ceo_demo_packages():
    rows = show.list_showcase()
    focus = {r["slot"] for r in rows if r["demo_focus"]}
    assert focus == {"04", "08", "09"}, focus
    by_slot = {r["slot"]: r for r in rows}
    assert by_slot["04"]["package_id"] == "P-07"
    assert by_slot["09"]["domain"] == "non-medical"


def test_showcase_detail_carries_boundary_fields():
    d = show.showcase_detail("04")
    assert d is not None
    assert d["loop_verification_state"] == "NONE"  # honest, never promoted
    assert "COMPUTATIONAL_RESULT" in d["provenance_note"]
    assert all(p.get("envelope") is not None for p in d["parameters"])
    assert d["dossier"]["download"] == "/api/showcase/04/package"
    assert d["model"]["glb"].endswith("/model")


def test_showcase_detail_unknown_slot_is_none():
    assert show.showcase_detail("99") is None


def test_showcase_model_paths_resolve():
    assert show.glb_path("04") is not None \
        and show.glb_path("04").suffix == ".glb"
    assert show.package_zip("04") is not None \
        and show.package_zip("04").suffix == ".zip"


# ---------------------------------------------------------------------------
# the interactive evaluator (Phase 5) — honest refusals + real rebuild
# ---------------------------------------------------------------------------

def test_evaluate_outside_envelope_is_refused_not_clamped():
    result, refusal = show.evaluate_parameter("04", "outer_diameter_mm", 9.9)
    assert result is None
    assert refusal["status"] == "OUTSIDE_DECLARED_ENVELOPE"
    assert "envelope is [2.5, 3.5]" in refusal["reason"]
    assert "refusing, not clamping" in refusal["reason"]


def test_evaluate_unbound_parameter_is_refused():
    result, refusal = show.evaluate_parameter("04", "not_a_param", 1.0)
    assert result is None
    assert refusal["status"] == "UNBOUND_PARAMETER"
    assert "no silent substitution" in refusal["reason"]


def test_evaluate_real_rebuild_with_provenance(tmp_path):
    # byte-immutability of the canonical package (Art. IX)
    glb = show.glb_path("04")
    before = glb.read_bytes()

    result, _ = show.evaluate_parameter(
        "04", "floor_lumen_diameter_mm", 0.45,
        reason="product test rebuild")
    assert result is not None, "in-envelope rebuild must succeed"
    assert result["status"] == "OK"
    assert result["evidence_class"] == "COMPUTATIONAL_RESULT"
    assert result["geometry_validation"]["valid"] is True
    # real mutation provenance from the canonical pipeline (from_value is
    # the package's own declared value, read from the file — not a guess)
    declared = next(
        p["value"] for p in json.loads(
            (show._slot_dir("04") / "MODEL" / "PARAMETERS.json")
            .read_text())["parameters"]
        if p["param_id"] == "floor_lumen_diameter_mm")
    rec = result["record"]
    assert rec["rebuild_for_mutation"]["from_value"] == declared
    assert rec["rebuild_for_mutation"]["to_value"] == 0.45
    # the preview artifact carries its real hash
    assert result["preview_glb"]["sha256"]
    assert result["preview_glb"]["serve"].startswith(
        "/api/showcase/04/preview/")
    # canonical bytes untouched
    assert glb.read_bytes() == before


def test_evaluate_preview_glbs_do_not_shadow_canonical():
    result, _ = show.evaluate_parameter("04", "length_mm", 95.0)
    assert result is not None
    p = Path(result["preview_glb"]["path"])
    assert p.is_relative_to(REPO / "TOSCANINI_UI" / "previews")
    assert p != show.glb_path("04")


def test_showcase_evaluate_bad_slot():
    result, refusal = show.evaluate_parameter("99", "x", 1.0)
    assert result is None
    assert refusal["status"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# server route table — the job API aliases and honesty payloads
# ---------------------------------------------------------------------------

def _handler_instance():
    h = srv.Handler.__new__(srv.Handler)  # no socket; methods under test
    return h


def test_api_run_alias_is_the_same_handler_path():
    """Art. III / R389 Phase 7: POST /api/run and POST /api/discoveries
    dispatch to the SAME code path (route table equality, not a second
    loop)."""
    import inspect
    src = inspect.getsource(srv.Handler.do_POST)
    # R415 widened the shared dispatch to the directive's
    # /api/discovery alias; the three names remain ONE code path
    assert 'p.path in ("/api/discoveries", "/api/run", "/api/discovery")' \
        in src


def test_api_run_stream_and_result_alias_routes():
    import inspect
    src = inspect.getsource(srv.Handler.do_GET)
    assert '/api/run' in src and 'parts[3] == "stream"' in src
    assert 'parts[3] == "result"' in src
    # aliases delegate to the SAME handlers (_sse / session_detail)
    assert "self._sse(rid)" in src
    assert "store.session_detail(rid)" in src


def test_showcase_evaluate_route_shape():
    """The evaluate POST route matches 4-segment paths (regression pin:
    the original implementation matched 5 and 404'd)."""
    import inspect
    src = inspect.getsource(srv.Handler.do_POST)
    assert 'len(parts) == 4 and parts[0] == "api"' in src \
        and 'parts[3] == "evaluate"' in src


def test_webapp_gitignore_blocks_build_artifacts():
    gi = REPO / "TOSCANINI_UI" / "webapp" / ".gitignore"
    assert gi.exists()
    text = gi.read_text()
    assert "node_modules/" in text and ".next/" in text


def test_webapp_never_imports_python_internals():
    """R389 Phase 7: the frontend depends ONLY on the job API — no import
    or fetch of internal Python modules (grep the whole webapp source)."""
    forbidden = ("discovery_fabric", "premium_package_factory",
                 "toscanini.", "ENGINE_RUNS", "127.0.0.1:8788",
                 "problem_builder", "sessions.py")
    web = REPO / "TOSCANINI_UI" / "webapp"
    for f in list(web.glob("app/**/*.tsx")) + list(web.glob("lib/*.ts")):
        src = f.read_text(errors="replace")
        for bad in forbidden:
            assert bad not in src, f"{f.name} references {bad!r}"
    # the ONLY engine address allowed is the rewrite config
    cfg = (web / "next.config.mjs").read_text()
    assert "127.0.0.1:8788" in cfg  # the single, configurable proxy target

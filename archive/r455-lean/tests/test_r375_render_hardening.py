"""test_r375_render_hardening.py — CEO R375 (final PDF rendering
hardening) adversarial test suite.

Every new control gets:
  * a positive case (the real render passes), and
  * an adversarial case that injects the exact defect the control
    exists to catch and MUST fail (Art. VIII/XVII/XXX).

No V3 threshold was lowered; the V3 gate tests remain in
test_v3_render_gate.py and must keep passing unchanged.
"""
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

from premium_package_factory.gates import render_verification as rv
# R410-follow-through (2026-09-05, disclosed per Art. LXIV): this
# suite previously imported premium_package_factory.gates.render_fixtures
# (worst-case fixture packages FX1-FX5 + fixture_pdf), which commit
# 2199982e deleted in the verified-live-closure prune. The prune's
# battery (r374+r386+r402+drivers+static) did not collect this file, so
# the orphaned import survived and broke collection. The three tests
# that consumed the deleted fixtures are retired with this change
# (their live-module behaviors remain covered by
# test_r372_release_grade.py and test_r373_independent_audit.py);
# the two render_verification QA tests are rewritten with inline
# clean-PDF construction so the positive QA path stays covered.
from premium_package_factory.r371 import builder as b
from premium_package_factory.r371.builder import (
    _tbl, cell_full, cell_safe, get_styles)


# ---------------------------------------------------------------------------
# R375-1: authoritative truncation removed
# ---------------------------------------------------------------------------
def test_cell_full_never_truncates():
    long_value = ("Occlusion spectrum envelope with quantified onset "
                  "horizons. ") * 40      # ~2,600 chars
    para = cell_full(long_value)
    text = para.text
    assert long_value.replace("&", "&amp;").strip() in text.strip()
    assert "…" not in text and "[SUMMARY" not in text


def test_cell_safe_requires_explicit_pointer():
    with pytest.raises(ValueError):
        cell_safe("any_field", "x" * 400)          # no register -> REFUSE
    p = cell_safe("any_field", "x" * 400, register="UNKNOWN_ROADMAP.json")
    assert "[SUMMARY — full text: UNKNOWN_ROADMAP.json]" in p.text


def test_cell_safe_only_in_summary_tables():
    """cell_safe() call sites are mechanically restricted to the declared
    summary-only tables (SUMMARY_TABLE_WHITELIST). The authoritative
    builders must contain ZERO cell_safe calls."""
    base = Path(__file__).parent.parent / "premium_package_factory" / "r371"
    for fname in ("builder_dossier.py", "builder_documents.py"):
        src = (base / fname).read_text(encoding="utf-8")
        calls = [l for l in src.splitlines()
                 if re.search(r"\bcell_safe\s*\(", l)
                 and not l.strip().startswith("#")]
        assert not calls, f"{fname} still calls cell_safe: {calls}"
    # and no authoritative hard slices remain in the render path
    for fname in ("builder_dossier.py", "builder_documents.py"):
        src = (base / fname).read_text(encoding="utf-8")
        for i, l in enumerate(src.splitlines(), 1):
            if re.search(r"\[\s*:\s*\d+\s*\]", l):
                if "sha256" in l or l.strip().startswith("#"):
                    continue
                if "summary" in l.lower() or "SUMMARY" in l:
                    continue
                # [:2] top-critical selection with explicit +N pointer is
                # the documented exec-brief summary exception
                if "crit[:2]" in l:
                    continue
                raise AssertionError(
                    f"R375-1 violation: hard slice at {fname}:{i}: {l}")


def test_no_authoritative_row_caps():
    """Row-count caps ([..:14] etc.) dropped — every recorded item renders."""
    base = Path(__file__).parent.parent / "premium_package_factory" / "r371"
    src = (base / "builder_dossier.py").read_text(encoding="utf-8")
    for pat in ("design_inputs[:", "design_outputs[:", "failure_analysis[:",
                "verification[:", "validation[:", "pkg.unknowns[:"):
        assert pat not in src, f"row cap remains: {pat}"


# ---------------------------------------------------------------------------
# R375-2: one canonical table renderer
# ---------------------------------------------------------------------------
def test_one_canonical_table_renderer():
    base = Path(__file__).parent.parent / "premium_package_factory" / "r371"
    for fname in ("builder.py", "builder_dossier.py", "builder_documents.py",
                  "builder_portfolio.py"):
        raw = (base / fname).read_text(encoding="utf-8")
        src = "\n".join(re.sub(r"#.*$", "", l) for l in raw.splitlines())
        # raw Table( constructions (outside builder._tbl itself) forbidden
        for m in re.finditer(r"(?<![\w.])(Table\s*\()", src):
            start = max(0, m.start() - 200)
            ctx = src[start:m.end() + 60]
            if fname == "builder.py" and "t = Table(data" in ctx:
                continue     # THE canonical renderer itself
            # import lines are fine
            if "import" in src[max(0, m.start() - 60):m.end()] and \
                    "=" not in src[m.start():m.end() + 10]:
                continue
            raise AssertionError(
                f"raw Table( construction in {fname} near: "
                f"{src[m.start()-60:m.end()+40]!r}")


def test_tbl_guarantees():
    """The canonical renderer guarantees paragraph cells, explicit widths
    inside the frame, repeat headers and split-by-row."""
    rows = [["H1", "H2"], ["a" * 400, "b"], ["c", "d" * 300]]
    t = _tbl(rows, [100, 200])
    from reportlab.platypus import Paragraph
    for row in t._cellvalues:
        for cell in row:
            assert isinstance(cell, Paragraph)
    assert t.repeatRows == 1
    assert t.splitByRow == 1
    assert list(t._colWidths) == [100, 200]
    with pytest.raises(AssertionError):
        _tbl(rows, [300, 300])        # 600pt > 504pt frame -> refuse


def test_no_raw_drawstring_table_bodies():
    """No drawString() table bodies in the V5 render path (the footer
    canvas decorator is measured and is not a table body)."""
    base = Path(__file__).parent.parent / "premium_package_factory" / "r371"
    for fname in ("builder.py", "builder_dossier.py", "builder_documents.py",
                  "builder_portfolio.py"):
        src = (base / fname).read_text(encoding="utf-8")
        for m in re.finditer(r"drawString", src):
            ctx = src[max(0, m.start() - 120):m.start()]
            assert "footer" in ctx.lower() or "canvas" in ctx.lower() or \
                "_footer" in ctx, \
                f"drawString outside footer decorator in {fname}"


# ---------------------------------------------------------------------------
# R375-2: worst-case fixture diagram tests (fixture packages FX4)
# RETIRED 2026-09-05 (R410 follow-through, Art. LXIV): the fixtures
# module was deleted by 2199982e; build_experiment_diagrams' grow/
# reflow/fail-closed behavior remains covered by
# test_r372_release_grade.py and test_r373_independent_audit.py.
# Retrievable from git history (Art. XI).
# ---------------------------------------------------------------------------


def test_diagram_self_check_catches_deliberate_overlap():
    """Adversarial (Art. XVII): an overlapping layout MUST raise."""
    from premium_package_factory.r371.experiment_diagram import _self_verify
    boxes = [(0, 0, 4, 2, "A"), (1, 1, 4, 2, "B")]      # overlapping
    with pytest.raises(RuntimeError, match="box overlap"):
        _self_verify(boxes, 10, "adversarial")
    boxes_oob = [(0, -1, 4, 2, "A")]                    # outside axes
    with pytest.raises(RuntimeError, match="outside axes"):
        _self_verify(boxes_oob, 10, "adversarial")


def test_text_geometry_check_catches_deliberate_overlap():
    """Adversarial: two overlapping texts in a figure MUST raise."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from premium_package_factory.diagrams.factory import (
        verify_text_geometry)
    fig = plt.figure(figsize=(6, 3))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")
    ax.text(5, 2.5, "LEFT TEXT OVERLAP PROBE", ha="center")
    ax.text(5, 2.45, "RIGHT TEXT OVERLAP PROBE", ha="center")
    with pytest.raises(RuntimeError, match="text overlap"):
        verify_text_geometry(fig, "adversarial")
    plt.close(fig)


def test_measured_equation_embed_floor():
    """Equations embed at measured size with an 8pt effective-glyph floor;
    pathological width falls back to verbatim text (never unreadable)."""
    from premium_package_factory.r371.equations import (
        measured_equation_image, render_equation_png)
    with tempfile.TemporaryDirectory() as td:
        ok_png = os.path.join(td, "ok.png")
        render_equation_png(r"$Q = A_c \sqrt{2 \Delta P / \rho}$", ok_png)
        img, note = measured_equation_image(ok_png)
        assert img is not None and note is None
        # pathological: enormous mathtext width
        wide_png = os.path.join(td, "wide.png")
        render_equation_png(
            r"$" + r" + ".join([r"\alpha_{%d} x^{%d}" % (i, i)
                                for i in range(60)]) + r"$", wide_png)
        img2, note2 = measured_equation_image(wide_png)
        assert img2 is None and "floor" in note2


# ---------------------------------------------------------------------------
# R375-4: overflow / overlap / clipping are hard failures — adversarial
# ---------------------------------------------------------------------------
def _make_pdf(path, draw_fn):
    from reportlab.pdfgen import canvas as rl_canvas
    c = rl_canvas.Canvas(path, pagesize=(612, 792))
    draw_fn(c)
    c.showPage()
    c.save()
    return path


def test_geometric_catches_x_overflow():
    def draw(c):
        c.setFont("Helvetica", 10)
        c.drawString(60, 400, "X" * 300)          # runs far off the page
    with tempfile.TemporaryDirectory() as td:
        pdf = _make_pdf(os.path.join(td, "x.pdf"), draw)
        with pytest.raises(rv.RenderDefect, match="x-overflow"):
            rv.geometric_qa(pdf)


def test_geometric_catches_y_overflow():
    def draw(c):
        c.setFont("Helvetica", 10)
        c.drawString(60, -20, "below the page")   # y outside page
    with tempfile.TemporaryDirectory() as td:
        pdf = _make_pdf(os.path.join(td, "y.pdf"), draw)
        with pytest.raises(rv.RenderDefect, match="vertically"):
            rv.geometric_qa(pdf)


def test_geometric_catches_image_out_of_bounds():
    def draw(c):
        from reportlab.lib.utils import ImageReader
        import PIL.Image as PImage
        p = os.path.join(tempfile.gettempdir(), "_r375_img.png")
        PImage.new("RGB", (60, 40), "red").save(p)
        c.drawImage(ImageReader(p), 500, 400, width=200, height=100)
    with tempfile.TemporaryDirectory() as td:
        pdf = _make_pdf(os.path.join(td, "img.pdf"), draw)
        with pytest.raises(rv.RenderDefect, match="image outside page"):
            rv.geometric_qa(pdf)


def test_geometric_catches_text_over_figure():
    def draw(c):
        from reportlab.lib.utils import ImageReader
        import PIL.Image as PImage
        p = os.path.join(tempfile.gettempdir(), "_r375_img2.png")
        PImage.new("RGB", (200, 120), "blue").save(p)
        c.drawImage(ImageReader(p), 100, 300, width=200, height=120)
        c.setFont("Helvetica", 10)
        c.drawString(150, 350, "TEXT PRINTED OVER THE FIGURE")
    with tempfile.TemporaryDirectory() as td:
        pdf = _make_pdf(os.path.join(td, "over.pdf"), draw)
        with pytest.raises(rv.RenderDefect, match="printed over a figure"):
            rv.geometric_qa(pdf)


def test_rendered_catches_margin_band_ink():
    def draw(c):
        c.setFont("Helvetica", 10)
        c.drawString(2, 400, "INK IN THE LEFT EDGE BAND")  # x < 18pt band
    with tempfile.TemporaryDirectory() as td:
        pdf = _make_pdf(os.path.join(td, "band.pdf"), draw)
        with pytest.raises(rv.RenderDefect, match="edge band"):
            rv.rendered_page_qa(pdf)


def test_rendered_catches_blank_page():
    def draw(c):
        pass                                       # nothing drawn
    with tempfile.TemporaryDirectory() as td:
        pdf = _make_pdf(os.path.join(td, "blank.pdf"), draw)
        with pytest.raises(rv.RenderDefect, match="blank page"):
            rv.rendered_page_qa(pdf)


def test_rendered_passes_clean_page():
    def draw(c):
        c.setFont("Helvetica", 10)
        c.drawString(60, 400, "Clean content inside the margins.")
    with tempfile.TemporaryDirectory() as td:
        pdf = _make_pdf(os.path.join(td, "clean.pdf"), draw)
        m = rv.rendered_page_qa(
            pdf, png_dir=os.path.join(td, "pages"))
        assert m["pages"] == 1 and m["total_band_ink"] == 0
        assert os.path.exists(os.path.join(td, "pages"))


# ---------------------------------------------------------------------------
# R375-1/10: content completeness instrument — adversarial
# ---------------------------------------------------------------------------
def test_completeness_detects_truncation():
    haystack = ["The full authoritative value appears here in full "
                "with every single character present."]
    ok, _ = rv.content_completeness(
        [("full", "The full authoritative value appears here in full "
                  "with every single character present.")], haystack)
    assert ok
    ok2, fails2 = rv.content_completeness(
        [("truncated", "The full authoritative value appears here in "
                       "full with every single character present. "
                       "PLUS A TAIL THAT WAS NEVER RENDERED")], haystack)
    assert not ok2 and fails2[0]["field"] == "truncated"


def test_completeness_splice_is_exact():
    a = "AAA_PREFIX_OF_THE_NEEDLE_THAT_ENDS_THE_PAGE"
    bstream = "SUFFIX_OF_THE_NEEDLE_THAT_STARTS_THE_NEXT_PAGE_BBB"
    needle = "PREFIX_OF_THE_NEEDLE_THAT_ENDS_THE_PAGE" \
             "SUFFIX_OF_THE_NEEDLE_THAT_STARTS_THE_NEXT_PAGE"
    ok, _ = rv.content_completeness([("spliced", needle)], [a, bstream])
    assert ok
    altered = needle[:-10] + "XXXXXXXXX"
    ok2, _ = rv.content_completeness([("altered", altered)], [a, bstream])
    assert not ok2


def test_mt_style_breaks_unbroken_tokens():
    s = get_styles()
    assert s["MT"].wordWrap == "LTR"


# ---------------------------------------------------------------------------
# R375-7: permanent worst-case fixtures
# RETIRED 2026-09-05 (R410 follow-through, Art. LXIV): the fixtures
# module was deleted by 2199982e (see the import disclosure above).
# Retrievable from git history (Art. XI).
# ---------------------------------------------------------------------------


def _make_clean_pdf(path):
    """Inline minimal CLEAN page for the QA positive path (replaces
    the deleted fixtures' fixture_pdf): a short line at safe margins —
    in-bounds, no overlap, non-blank."""
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path))
    c.setFont("Helvetica", 10)
    c.drawString(72, 700, "Clean QA positive-path page.")
    c.showPage()
    c.save()
    return path


# ---------------------------------------------------------------------------
# R375-8: ZIP sequence + no-ZIP-on-QA-failure
# ---------------------------------------------------------------------------
def test_zip_extract_hash_compare_and_no_zip_on_failure(tmp_path=None):
    """build -> render -> QA -> package -> ZIP -> extract -> hash compare;
    and a QA failure blocks ZIP creation."""
    td = tempfile.mkdtemp(prefix="r375_zip_")
    # positive sequence (inline clean PDF — the deleted fixtures'
    # fixture_pdf replacement, see disclosure above)
    src = os.path.join(td, "pkg")
    os.makedirs(src)
    _make_clean_pdf(os.path.join(src, "fixture.pdf"))
    rv.geometric_qa(os.path.join(src, "fixture.pdf"))
    rv.rendered_page_qa(os.path.join(src, "fixture.pdf"))
    zpath = os.path.join(td, "pkg.zip")
    import hashlib

    def sha(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(src)):
            zf.write(os.path.join(src, f), f)
    # extract + hash compare
    xdir = os.path.join(td, "extracted")
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(xdir)
    for f in sorted(os.listdir(src)):
        assert sha(os.path.join(src, f)) == sha(os.path.join(xdir, f))
    # negative: broken PDF must fail QA BEFORE any ZIP step
    def draw(c):
        c.setFont("Helvetica", 10)
        c.drawString(60, 400, "X" * 300)
    broken = _make_pdf(os.path.join(td, "broken.pdf"), draw)
    with pytest.raises(rv.RenderDefect):
        rv.geometric_qa(broken)
        rv.rendered_page_qa(broken)
        # unreachable when QA fails — ZIP creation must come after
        with zipfile.ZipFile(os.path.join(td, "broken.zip"), "w") as zf:
            zf.write(broken, "broken.pdf")
    assert not os.path.exists(os.path.join(td, "broken.zip"))
    shutil.rmtree(td, ignore_errors=True)


# ---------------------------------------------------------------------------
# R375-5: the rendered page is the audit object — PNGs persist
# ---------------------------------------------------------------------------
def test_rendered_pngs_persist():
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, "fx.pdf")
        _make_clean_pdf(pdf)
        png_dir = os.path.join(td, "audit_pages")
        rv.rendered_page_qa(pdf, png_dir=png_dir)
        pngs = [f for f in os.listdir(png_dir) if f.endswith(".png")]
        assert pngs, "rendered page PNGs must persist as audit artifacts"

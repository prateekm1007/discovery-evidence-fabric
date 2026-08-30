"""render_verification.py — V3 build gate (CEO forensic directive
2026-08-30) extended by R375 (CEO final PDF rendering hardening).

The V2 release shipped 15 packages whose PDFs had 598-1,029 overlapping
character pairs each and x-overflow up to 2,797pt on a 612pt page. The
V3 rendering fixes (Paragraph-wrapped tables, auto-sized diagram boxes)
repaired the cause; the V3 gate made the defect class mechanically
undetectable-before-ship.

R375 adds the second, independent instrument. The CEO directive:

  "Render PDF pages -> PNG. Then inspect the rendered pages.
   The actual rendered page is the audit object."
  "Require both: GEOMETRIC_QA + RENDERED_PAGE_QA.
   A package passes only if both pass."

Instruments
-----------
geometric_qa(pdf)      PDF-layer geometry (pdfplumber): page-bounds
                       overflow (x AND y), overlapping character pairs,
                       image-vs-page-bounds, image-vs-image overlap and
                       image-vs-text (material overprint).
rendered_page_qa(pdf)  Raster-layer (pymupdf -> PIL): renders every page
                       to PNG, then checks margin-band purity (ink in the
                       page-edge band = clipped/bleeding content), blank
                       pages, and records ink coverage. PNGs persist as
                       audit artifacts.
content_completeness   Authoritative strings from the canonical record
                       must appear IN FULL (normalized) in the package's
                       PDF text — the mechanical "0 authoritative
                       truncation / 0 missing content" instrument.

verify_pdf_rendering   = geometric_qa (backward-compatible V3 name).
verify_package(dir)    = geometric + rendered on every PDF (blocking).
verify_portfolio(root) = verify_package over all packages + root PDFs.

Art. XIX/XXX: every detector has an adversarial test that injects the
exact defect it exists to catch (tests/test_r375_render_hardening.py).
No V3 threshold was lowered — R375 only adds instruments.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pdfplumber

#: kerning tolerance: sub-2pt x-overlaps between adjacent chars on the
#: same baseline are normal kerning; beyond that is overprinting (the
#: forensic instrument's threshold, unchanged).
KERN_TOL_PT = 2.0
MAX_OVERLAPS_PER_PAGE = 5
PAGE_WIDTH_TOL_PT = 5.0
PAGE_HEIGHT_TOL_PT = 5.0

#: material overlap between an image and text: a char centre inside an
#: image bbox by more than this many pt is text printed over a figure.
IMG_TEXT_TOL_PT = 1.0
#: image-vs-image overlap tolerance (figures touching edges = defect).
IMG_IMG_TOL_PT = 1.0

#: raster margin band (points). The layout reserves >= 0.7in (50.4pt) to
#: content; the footer sits at 0.42in (30.2pt). Ink inside the outer 18pt
#: band is content bleeding off the page or clipped at the edges.
MARGIN_BAND_PT = 18.0
#: ink luminance threshold (0=black, 255=white); below = ink.
INK_LUM = 245


class RenderDefect(ValueError):
    """Raised when a PDF exhibits a renderable defect class. Blocking."""


# ---------------------------------------------------------------------------
# GEOMETRIC_QA — pdfplumber layer
# ---------------------------------------------------------------------------
def geometric_qa(pdf_path, label=None, max_overlaps=MAX_OVERLAPS_PER_PAGE):
    """Fail on: text outside page bounds, overlapping chars, images outside
    page bounds, image-image overlap, image-text overprint.

    Returns a per-page metric dict when clean (for the build report).
    """
    label = label or Path(pdf_path).name
    errors = []
    metrics = []
    with pdfplumber.open(pdf_path) as pdf:
        for p_num, page in enumerate(pdf.pages, 1):
            page_w, page_h = page.width, page.height
            chars = page.chars
            y_groups = defaultdict(list)
            for c in chars:
                y_groups[round(c["y0"])].append(c)

            page_overlaps = 0
            for y_key, group in y_groups.items():
                max_x = max(c.get("x1", 0) for c in group)
                if max_x > page_w + PAGE_WIDTH_TOL_PT:
                    text = "".join(
                        c.get("text", "")
                        for c in sorted(group, key=lambda c: c["x0"]))
                    errors.append(
                        f"Page {p_num} y={y_key}: x-overflow "
                        f"{max_x:.0f}>{page_w:.0f}pt '{text[:50]}'")
                s = sorted(group, key=lambda c: c["x0"])
                for i in range(len(s) - 1):
                    if s[i + 1]["x0"] < s[i]["x1"] - KERN_TOL_PT:
                        page_overlaps += 1
            if page_overlaps > max_overlaps:
                errors.append(
                    f"Page {p_num}: {page_overlaps} overlapping char "
                    f"pairs (max {max_overlaps})")

            # -- y-bounds: text above/below the physical page ------------
            for c in chars:
                if (c.get("y0", 0) < -PAGE_HEIGHT_TOL_PT or
                        c.get("y1", 0) > page_h + PAGE_HEIGHT_TOL_PT):
                    errors.append(
                        f"Page {p_num}: text outside page vertically: "
                        f"'{c.get('text', '')[:30]}' "
                        f"y[{c.get('y0'):.0f},{c.get('y1'):.0f}] "
                        f"vs page height {page_h:.0f}")
                    break

            # -- images: page bounds, image-image, image-text -------------
            imgs = page.images
            for im in imgs:
                if (im["x0"] < -IMG_IMG_TOL_PT or
                        im["x1"] > page_w + IMG_IMG_TOL_PT or
                        im["top"] < -IMG_IMG_TOL_PT or
                        im["bottom"] > page_h + IMG_IMG_TOL_PT):
                    errors.append(
                        f"Page {p_num}: image outside page bounds "
                        f"[{im['x0']:.0f},{im['x1']:.0f}]x"
                        f"[{im['top']:.0f},{im['bottom']:.0f}] "
                        f"vs {page_w:.0f}x{page_h:.0f}")
            for i in range(len(imgs)):
                for j in range(i + 1, len(imgs)):
                    a, b = imgs[i], imgs[j]
                    ix = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
                    iy = min(a["bottom"], b["bottom"]) - max(
                        a["top"], b["top"])
                    if ix > IMG_IMG_TOL_PT and iy > IMG_IMG_TOL_PT:
                        errors.append(
                            f"Page {p_num}: figure overlap: two images "
                            f"intersect by {ix:.0f}x{iy:.0f}pt")
            for im in imgs:
                overprinted = 0
                for c in chars:
                    cx, cy = (c["x0"] + c["x1"]) / 2, (c["top"] + c["bottom"]) / 2
                    if (im["x0"] + IMG_TEXT_TOL_PT < cx < im["x1"] - IMG_TEXT_TOL_PT
                            and im["top"] + IMG_TEXT_TOL_PT < cy <
                            im["bottom"] - IMG_TEXT_TOL_PT):
                        overprinted += 1
                if overprinted > 0:
                    errors.append(
                        f"Page {p_num}: {overprinted} characters printed "
                        f"over a figure (material overlap)")

            metrics.append({"page": p_num, "overlaps": page_overlaps})

    if errors:
        raise RenderDefect(
            f"PDF rendering defects in {label}:\n"
            + "\n".join(f"  - {e}" for e in errors))
    return {"file": label, "pages": len(metrics),
            "max_overlaps_per_page":
                max((m["overlaps"] for m in metrics), default=0)}


#: V3 backward-compatible name.
verify_pdf_rendering = geometric_qa


# ---------------------------------------------------------------------------
# RENDERED_PAGE_QA — raster layer (the rendered page is the audit object)
# ---------------------------------------------------------------------------
def rendered_page_qa(pdf_path, png_dir=None, dpi=150, label=None):
    """Render every page to PNG and inspect the raster.

    Checks per page:
      * margin-band purity — ink within MARGIN_BAND_PT of any page edge
        is content bleeding off the page or clipped at a boundary;
      * blank page — a fully white page indicates a render failure;
      * ink coverage recorded (audit metric).

    PNGs persist under png_dir (audit artifacts for CEO inspection).
    Returns per-page metrics; raises RenderDefect on any violation.
    """
    label = label or Path(pdf_path).name
    import fitz  # pymupdf

    doc = fitz.open(pdf_path)
    errors = []
    metrics = []
    try:
        if png_dir:
            os.makedirs(png_dir, exist_ok=True)
        zoom = dpi / 72.0
        band_px = int(MARGIN_BAND_PT * zoom)
        from PIL import Image
        for p_num, page in enumerate(doc, 1):
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom),
                                  alpha=False)
            png_path = None
            if png_dir:
                stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(pdf_path).stem)
                png_path = os.path.join(
                    png_dir, f"{stem}_p{p_num:02d}.png")
                pix.save(png_path)
            img = Image.frombytes("RGB", (pix.width, pix.height),
                                  pix.samples)
            gray = img.convert("L")
            w, h = gray.size
            # ink mask (sampling rows for speed on large pages)
            px = gray.load()
            ink_in_band = 0
            ink_total = 0
            step = 2 if w > 1200 else 1
            for y in range(0, h, step):
                for x in range(0, w, step):
                    if px[x, y] < INK_LUM:
                        ink_total += 1
                        if (x < band_px or x >= w - band_px or
                                y < band_px or y >= h - band_px):
                            ink_in_band += 1
            if ink_in_band > 0:
                errors.append(
                    f"Page {p_num}: {ink_in_band} ink samples in the "
                    f"{MARGIN_BAND_PT:.0f}pt edge band (clipped/bleeding "
                    f"content)")
            if ink_total == 0:
                errors.append(f"Page {p_num}: blank page")
            metrics.append({"page": p_num, "ink_samples": ink_total,
                            "band_ink": ink_in_band,
                            "png": png_path})
    finally:
        doc.close()
    if errors:
        raise RenderDefect(
            f"Rendered-page defects in {label}:\n"
            + "\n".join(f"  - {e}" for e in errors))
    return {"file": label, "pages": len(metrics),
            "total_band_ink": sum(m["band_ink"] for m in metrics)}


# ---------------------------------------------------------------------------
# CONTENT COMPLETENESS — the anti-truncation instrument
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    """Whitespace-insensitive, ligature-free comparison form. Keeps case
    and all non-whitespace characters so a truncated string can never
    match its full form."""
    text = unicodedata.normalize("NFKC", str(text or ""))
    text = (text.replace("ﬁ", "fi").replace("ﬂ", "fl")
                .replace("ﬀ", "ff").replace("ﬃ", "ffi"))
    return re.sub(r"\s+", "", text)


def pdf_text(pdf_path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "".join(page.extract_text() or "" for page in pdf.pages)


def pdf_haystacks(pdf_path):
    """Extraction streams for containment checking.

    Page-flat text interleaves table columns in y-order, so a long cell
    value gets OTHER cells' wrapped fragments spliced between its lines
    (found live by the R375-7 FX1 fixture attack). The ruled tables
    (GRID lines) are therefore ALSO extracted per cell — each cell's
    text is internally contiguous, so a full authoritative value is
    provably present in full inside its own cell.

    Long content legitimately SPLITS across page boundaries (Paragraph
    pagination, table row splits with repeated headers); the page-flat
    stream also carries the footer line. So each page additionally
    contributes a FOOTER-FREE body stream, and content_completeness
    performs exact cross-page SPLICE matching (prefix at a stream end +
    suffix at another stream start, byte-exact, no fuzzy tolerance).

    Returns [page_flat, body_flat, cell_1, cell_2, ...] per page.
    """
    streams = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            streams.append(page.extract_text() or "")
            # body-only stream: exclude the footer band (the identity /
            # confidentiality / page-number line drawn in the bottom
            # ~30pt). Crop bbox is (x0, top, x1, bottom), top-based.
            body = page.crop((0, 0, page.width, page.height - 45))
            streams.append(body.extract_text() or "")
            for table in page.extract_tables():
                for row in table:
                    for cell in row:
                        if cell and str(cell).strip():
                            streams.append(str(cell))
    return streams


def _splice_match(needle: str, hays: list) -> bool:
    """Exact containment allowing ONE page-boundary splice: the needle
    may be split as prefix|suffix where the prefix ENDS one stream and
    the suffix STARTS another (the physical reality of a paragraph or
    table row split across pages). Byte-exact — never fuzzy."""
    if any(needle in h for h in hays):
        return True
    for a in hays:
        # longest k such that needle[:k] is a suffix of a
        max_k = min(len(a), len(needle) - 1)
        if max_k <= 0:
            continue
        # find k by direct comparison from the end (cheap: few streams)
        k = max_k
        while k > 0 and a[-k:] != needle[:k]:
            k -= 1
        if k == 0:
            continue
        rest = needle[k:]
        if any(b.startswith(rest) for b in hays):
            return True
    return False


def content_completeness(expected_strings, haystacks):
    """Each expected (label, full_string) must appear IN FULL inside a
    normalized stream (one exact cross-page splice allowed). Returns
    (ok, failures).

    This is the mechanical guard for '0 authoritative truncation' and
    '0 missing content': whatever the canonical record says MUST exist
    in the shipped PDF set, in full, or the build fails. Cell-level
    streams make the check immune to column-interleave artifacts while
    remaining EXACT (Art. II) — a truncated cell never contains its
    full string.
    """
    if isinstance(haystacks, str):
        haystacks = [haystacks]
    hays = [_normalize(h) for h in haystacks]
    failures = []
    for label, s in expected_strings:
        if not str(s or "").strip():
            continue
        needle = _normalize(s)
        if needle and not _splice_match(needle, hays):
            failures.append({
                "field": label,
                "expected_len": len(str(s)),
                "expected_head": str(s)[:80],
            })
    return (not failures), failures


# ---------------------------------------------------------------------------
# Package / portfolio verification (both instruments required)
# ---------------------------------------------------------------------------
def verify_package(pkg_dir, png_dir=None):
    """GEOMETRIC_QA + RENDERED_PAGE_QA on every PDF in one package.

    A package passes only if BOTH instruments pass on EVERY PDF
    (CEO R375-6). Returns metrics; raises RenderDefect on any defect.
    """
    pkg_dir = Path(pkg_dir)
    out = []
    for pdf in sorted(pkg_dir.glob("*.pdf")):
        geo = geometric_qa(pdf)
        rendered = rendered_page_qa(
            pdf, png_dir=os.path.join(png_dir, pdf.stem)
            if png_dir else None)
        out.append({"geometric": geo, "rendered": rendered})
    return out


def verify_portfolio(root, png_dir=None):
    """Verify every package PDF + portfolio-level PDFs. Raises on ANY
    defect from either instrument."""
    root = Path(root)
    results = {}
    for pdf in sorted(root.glob("*.pdf")):
        results[str(pdf.name)] = {
            "geometric": geometric_qa(pdf),
            "rendered": rendered_page_qa(
                pdf, png_dir=os.path.join(png_dir, pdf.stem)
                if png_dir else None)}
    for pkg in sorted((root / "DOWNLOAD").glob("*/")):
        if not pkg.is_dir():
            continue
        for pdf in sorted(pkg.glob("*.pdf")):
            results[f"{pkg.name}/{pdf.name}"] = {
                "geometric": geometric_qa(pdf),
                "rendered": rendered_page_qa(
                    pdf, png_dir=os.path.join(png_dir, pkg.name, pdf.stem)
                    if png_dir else None)}
    return results


def write_report(results, out_path):
    Path(out_path).write_text(json.dumps(
        {"gate": "R375_RENDER_VERIFICATION", "verdict": "PASS",
         "instruments": ["GEOMETRIC_QA", "RENDERED_PAGE_QA"],
         "files": results}, indent=1, ensure_ascii=False))
    return out_path

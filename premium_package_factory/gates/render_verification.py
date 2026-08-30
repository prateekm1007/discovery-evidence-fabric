"""render_verification.py — V3 build gate (CEO forensic directive
2026-08-30, Directive 5 / BUILD-GATE VERIFICATION TEST).

The V2 release shipped 15 packages whose PDFs had 598-1,029 overlapping
character pairs each and x-overflow up to 2,797pt on a 612pt page. The
rendering fixes (Paragraph-wrapped tables, auto-sized diagram boxes)
repair the cause; THIS gate makes the defect class mechanically
undetectable-before-ship forever:

  verify_pdf_rendering(pdf)  — fails on any page with text that overflows
                               the page width or overlaps neighbouring
                               characters beyond kerning tolerance.
  verify_package(pkg_dir)    — runs the PDF gate on every PDF in the
                               package. Package ZIP must NOT be created
                               when this fails.
  verify_portfolio(root)     — all packages + portfolio-level PDFs.

Detection mirrors the CEO's forensic method (pdfplumber char geometry,
per-y-row x0/x1 overlap test, >5 pairs = defect, not kerning).

Art. XIX/XXX: the gate attacks the renderer — tests/test_v3_render_gate.py
proves a deliberately-broken PDF FAILS and the fixed render PASSES.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pdfplumber

#: kerning tolerance: sub-2pt x-overlaps between adjacent chars on the
#: same baseline are normal kerning; beyond that is overprinting (the
#: forensic instrument's threshold, unchanged).
KERN_TOL_PT = 2.0
MAX_OVERLAPS_PER_PAGE = 5
PAGE_WIDTH_TOL_PT = 5.0


class RenderDefect(ValueError):
    """Raised when a PDF exhibits the V2 defect class. Blocking."""


def verify_pdf_rendering(pdf_path, label=None, max_overlaps=MAX_OVERLAPS_PER_PAGE):
    """CI gate: raise RenderDefect if any page has rendering defects.

    Returns a per-page metric dict when clean (for the build report).
    """
    label = label or Path(pdf_path).name
    errors = []
    metrics = []
    with pdfplumber.open(pdf_path) as pdf:
        for p_num, page in enumerate(pdf.pages, 1):
            page_w = page.width
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
                        f"Page {p_num} y={y_key}: overflow "
                        f"{max_x:.0f}>{page_w:.0f}pt '{text[:50]}'")
                s = sorted(group, key=lambda c: c["x0"])
                for i in range(len(s) - 1):
                    if s[i + 1]["x0"] < s[i]["x1"] - KERN_TOL_PT:
                        page_overlaps += 1
            if page_overlaps > max_overlaps:
                errors.append(
                    f"Page {p_num}: {page_overlaps} overlapping char "
                    f"pairs (max {max_overlaps})")
            metrics.append({"page": p_num, "overlaps": page_overlaps})

    if errors:
        raise RenderDefect(
            f"PDF rendering defects in {label}:\n"
            + "\n".join(f"  - {e}" for e in errors))
    return {"file": label, "pages": len(metrics), "max_overlaps_per_page":
            max((m["overlaps"] for m in metrics), default=0)}


def verify_package(pkg_dir):
    """Verify every PDF in one package directory. Returns metrics list."""
    pkg_dir = Path(pkg_dir)
    out = []
    for pdf in sorted(pkg_dir.glob("*.pdf")):
        out.append(verify_pdf_rendering(pdf))
    return out


def verify_portfolio(root):
    """Verify DOWNLOAD/<pkg>/*.pdf for all packages + portfolio-level
    PDFs at the root. Returns {file: metrics} and raises on ANY defect."""
    root = Path(root)
    results = {}
    for pdf in sorted(root.glob("*.pdf")):
        results[str(pdf.name)] = verify_pdf_rendering(pdf)
    for pkg in sorted((root / "DOWNLOAD").glob("*/")):
        if not pkg.is_dir():
            continue
        for pdf in sorted(pkg.glob("*.pdf")):
            results[f"{pkg.name}/{pdf.name}"] = verify_pdf_rendering(pdf)
    return results


def write_report(results, out_path):
    Path(out_path).write_text(json.dumps(
        {"gate": "V3_RENDER_VERIFICATION", "verdict": "PASS",
         "files": results}, indent=1, ensure_ascii=False))
    return out_path

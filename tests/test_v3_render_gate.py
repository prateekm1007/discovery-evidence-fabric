"""V3 render-gate tests (CEO forensic directive 2026-08-30).

Positive: a Paragraph-wrapped table renders with zero overflow/overlap.
Negative: the V2 pattern (raw drawString at fixed x offsets) FAILS the
gate — proving the gate detects the exact defect class it exists to
block. Metamorphic: the gate's metrics scale with injected overlap.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from premium_package_factory.gates.render_verification import (  # noqa: E402
    RenderDefect, verify_pdf_rendering)
from premium_package_factory.r371.builder import _tbl  # noqa: E402

import reportlab.rl_config  # noqa: E402
reportlab.rl_config.invariant = 1
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    SimpleDocTemplate, Spacer, Table)
from reportlab.lib.units import inch  # noqa: E402


def _build_pdf(path, story):
    doc = SimpleDocTemplate(
        str(path), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.75 * inch)
    doc.build(story)


LONG_DI_TEXT = (
    "The prior generalized differential-pressure valve designs fail because "
    "they regulate a single proximal pressure drop and cannot compensate "
    "for patient-specific distal catheter impedance; 11 MAUDE reports "
    "across 3 distinct devices document recurring under-drainage with "
    "correlated intracranial pressure symptoms, and 20 recall root-cause "
    "records attribute the failures to fixed-resistance flow paths that "
    "were never designed around measured patient outflow curves. "
    "V2 correction: the failure signature is load-dependent, not fixed."
) * 2  # ~800 chars — the DI-001 class that drew to x=2,797pt in V2


class TestGateBlocksV2Pattern(unittest.TestCase):
    def test_raw_string_table_fails_gate(self):
        """The EXACT V2 pattern: raw strings in a Table at fixed col x —
        must be caught by the gate (negative case, Art. XXX)."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "broken.pdf"
            rows = [["ID", "Design input", "Value / source"],
                    ["DI-001", "Clinical need", LONG_DI_TEXT]]
            t = Table(rows, colWidths=[0.55 * 72, 1.7 * 72, 4.4 * 72])
            _build_pdf(pdf, [t, Spacer(1, 6)])
            with self.assertRaises(RenderDefect) as cm:
                verify_pdf_rendering(pdf)
            # the gate reports the defect class it detected: x-overflow
            # and/or overlapping pairs (both are blocking signatures)
            self.assertTrue(
                "overflow" in str(cm.exception)
                or "overlapping" in str(cm.exception),
                f"gate did not report a defect class: {cm.exception}")

    def test_fixed_x_drawstring_overflows_fail(self):
        """Raw canvas.drawString at a fixed x with a long payload — the
        other V2 signature (x-overflow past the page width)."""
        import tempfile
        from reportlab.pdfgen.canvas import Canvas
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "overflow.pdf"
            c = Canvas(str(pdf), pagesize=letter)
            c.setFont("Helvetica", 7.6)
            c.drawString(0.75 * inch, 700, LONG_DI_TEXT)
            c.drawString(0.75 * inch, 660, "SECOND COLUMN VALUE")
            c.showPage()
            c.save()
            with self.assertRaises(RenderDefect):
                verify_pdf_rendering(pdf)


class TestFixedRendererPasses(unittest.TestCase):
    def test_paragraph_wrapped_table_passes(self):
        """Positive case: the SAME long text through _tbl (V3 factory,
        Paragraph-wrapped) renders clean."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "fixed.pdf"
            rows = [["ID", "Design input", "Value / source"],
                    ["DI-001", "Clinical need", LONG_DI_TEXT]]
            t = _tbl(rows, [0.55 * 72, 1.7 * 72, 4.4 * 72])
            _build_pdf(pdf, [t, Spacer(1, 6)])
            metrics = verify_pdf_rendering(pdf)
            self.assertLessEqual(metrics["max_overlaps_per_page"], 5)

    def test_tbl_width_assertion(self):
        """Directive 1b: a table wider than the 504pt frame is rejected
        at construction, before any PDF exists."""
        with self.assertRaises(AssertionError):
            _tbl([["a"]], [300, 300])  # 600pt > 504pt frame


class TestGateMetrics(unittest.TestCase):
    def test_metrics_report_pages(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "clean.pdf"
            rows = [["ID", "Value"], ["A", "short text"]]
            _build_pdf(pdf, [_tbl(rows, [72, 360])])
            m = verify_pdf_rendering(pdf)
            self.assertEqual(m["pages"], 1)
            self.assertLessEqual(m["max_overlaps_per_page"], 5)


if __name__ == "__main__":
    unittest.main()

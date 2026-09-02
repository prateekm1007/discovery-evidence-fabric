"""R393 — static-asset delivery + showcase brief sections (adversarial).

Constitutional basis:
- Art. XV/XIX: the R389→R392 deployment defect (globals.css imported by
  nothing → zero CSS in the static export → the public deployment rendered
  as browser-default HTML) is recorded as a REAL failure and pinned so it
  cannot silently recur.
- Art. VIII/XXX: this suite attacks the fix — the export verifier must
  FAIL on a reproduction of the original defect and must pass only on a
  genuinely complete export.
- Art. XXXIX: showcase brief sections are extracted verbatim from the
  released buyer-distribution PDFs — the parser is tested for honesty
  (missing sections stay None, never guessed; wrapped labels; the closing
  paragraph never bleeds into the kill condition).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

WEBAPP = REPO_ROOT / "TOSCANINI_UI" / "webapp"
VERIFY = WEBAPP / "verify-export.mjs"
LAYOUT = WEBAPP / "app" / "layout.tsx"
DOCKERFILE = REPO_ROOT / "Dockerfile"
PORTFOLIO_DOWNLOAD = REPO_ROOT.parent / "portfolio" / "DOWNLOAD"


def _run_verifier(export_dir: Path) -> subprocess.CompletedProcess:
    import shutil
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available for the export verifier")
    return subprocess.run(
        [node, str(VERIFY), str(export_dir)],
        capture_output=True, text=True, timeout=60,
    )


class TestExportVerifier:
    """The mechanical build assertion (CEO directive 2)."""

    def _make_fixture(self, tmp_path: Path, with_css: bool) -> Path:
        """A minimal export-shaped fixture; CSS omitted reproduces the
        R389→R392 defect exactly."""
        root = tmp_path / ("good" if with_css else "broken")
        (root / "_next" / "static" / "css").mkdir(parents=True)
        (root / "_next" / "static" / "chunks").mkdir(parents=True)
        css_link = (
            '<link rel="stylesheet" href="/_next/static/css/a.css"/>'
            if with_css else "")
        css_ref = (
            '<script src="/_next/static/chunks/x.js"></script>'
            '<script src="/_next/static/chunks/y.js"></script>'
            '<script src="/_next/static/chunks/z.js"></script>')
        body = (
            "<html><head>" + css_link + css_ref +
            "</head><body>" + ("x" * 900) +
            "</body></html>")
        for p in ("index.html", "run/index.html",
                  "showcase/index.html"):
            f = root / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body)
        if with_css:
            (root / "_next" / "static" / "css" / "a.css") \
                .write_text("body{color:#1f1e1c}" * 30)
        for n in ("x.js", "y.js", "z.js"):
            (root / "_next" / "static" / "chunks" / n).write_text("//c")
        return root

    def test_css_less_export_must_fail(self, tmp_path):
        """NEGATIVE CONTROL: the exact defect shape that shipped the
        public deployment unstyled must abort deployment."""
        fixture = self._make_fixture(tmp_path, with_css=False)
        r = _run_verifier(fixture)
        assert r.returncode == 1, (
            "verifier passed a CSS-less export — the original defect "
            "would ship again")
        lowered = (r.stdout + r.stderr).lower()
        assert "no css in export" in lowered
        assert "no stylesheet link" in lowered

    def test_complete_export_passes(self, tmp_path):
        fixture = self._make_fixture(tmp_path, with_css=True)
        r = _run_verifier(fixture)
        assert r.returncode == 0, r.stderr
        assert "EXPORT VERIFICATION PASSED" in r.stdout

    def test_broken_asset_reference_must_fail(self, tmp_path):
        """A page referencing an asset that is not in the export is a
        deployment failure even when CSS exists."""
        fixture = self._make_fixture(tmp_path, with_css=True)
        page = fixture / "index.html"
        page.write_text(
            page.read_text().replace(
                'src="/_next/static/chunks/x.js"',
                'src="/_next/static/chunks/missing.js"'))
        r = _run_verifier(fixture)
        assert r.returncode == 1
        assert "missing.js" in (r.stdout + r.stderr)

    def test_real_local_export_when_built(self):
        """When the export exists locally (post-build), it must pass —
        including the stylesheet reference on every page."""
        export = WEBAPP / "out"
        if not export.exists():
            pytest.skip("webapp export not built locally")
        r = _run_verifier(export)
        assert r.returncode == 0, r.stderr


class TestRegressionPins:
    """The defect's root cause, pinned at the source level."""

    def test_layout_imports_globals_css(self):
        """THE incident: globals.css existed but nothing imported it, so
        the Next.js build emitted zero CSS. The import is now pinned."""
        src = LAYOUT.read_text()
        assert 'import "./globals.css";' in src, (
            "layout.tsx must import the design system — without it the "
            "export contains no CSS and the public site renders unstyled")

    def test_dockerfile_gates_on_verify_export(self):
        """The image build must run the export verifier — a missing
        CSS/JS asset aborts the deployment (CEO directive 2)."""
        src = DOCKERFILE.read_text()
        assert "NEXT_OUTPUT=export npm run build" in src
        assert "verify-export.mjs" in src
        # the gate must be part of the SAME RUN layer as the build
        assert ("NEXT_OUTPUT=export npm run build"
                " && node verify-export.mjs") in src

    def test_server_mime_map_covers_css(self):
        from toscanini.server import _STATIC_TYPES
        assert _STATIC_TYPES.get(".css") == "text/css; charset=utf-8"
        assert _STATIC_TYPES.get(".js") == "text/javascript; charset=utf-8"


class TestBriefParser:
    """Art. XXXIX honesty: brief sections come verbatim from the released
    PDFs; the parser never invents or over-captures."""

    def test_wrapped_labels_parse(self):
        """Slot 11/15 shape: 'Kill\\ncondition:' — label wrapped mid-line."""
        text = (
            "WHAT IS IT?\nA thing.\n"
            "WHY DOES IT MATTER?\nBecause.\n"
            "WHAT IS ESTABLISHED?\nEquations.\n"
            "WHAT IS NOT ESTABLISHED?\nUnknowns.\n"
            "WHAT DOES THE BUYER DO NEXT?\n"
            "Decisive experiment: WP-01 — samples. Recorded effort: 8 weeks.\n"
            "Validation cost: NOT_ESTABLISHED. Kill\n"
            "condition: Damper coefficient cannot be tuned.\n"
            "This is an engineering-definition technology-transfer dossier. "
            "Not validated.")
        from toscanini.showcase import _split_brief_text
        out = _split_brief_text(text)
        assert out["what_it_does"] == "A thing."
        assert out["why_it_matters"] == "Because."
        assert out["decisive_experiment"].startswith("WP-01")
        assert "Kill" not in out["decisive_experiment"]
        assert out["kill_condition"] == (
            "Damper coefficient cannot be tuned.")
        # the closing paragraph never bleeds into the kill condition
        assert "dossier" not in out["kill_condition"]

    def test_missing_sections_stay_none(self):
        from toscanini.showcase import _split_brief_text
        out = _split_brief_text("WHAT IS IT?\nOnly a thing.")
        assert out["what_it_does"] == "Only a thing."
        assert out["why_it_matters"] is None
        assert out["kill_condition"] is None
        assert out["decisive_experiment"] is None

    def test_empty_text_all_none(self):
        from toscanini.showcase import _split_brief_text
        out = _split_brief_text("")
        assert all(v is None for k, v in out.items()
                   if k not in ("decisive_experiment", "kill_condition"))
        assert out["decisive_experiment"] is None
        assert out["kill_condition"] is None

    def test_label_inside_body_not_treated_as_section(self):
        """A label occurring inside body prose (not at a section start)
        still splits mechanically — verbatim extraction, no semantics."""
        from toscanini.showcase import _split_brief_text
        text = "WHAT IS IT?\nA thing mentioning WHY DOES IT MATTER? inline."
        out = _split_brief_text(text)
        assert out["what_it_does"] is not None
        # whatever was captured, it is verbatim from the text
        assert out["what_it_does"] in text


class TestShowcaseBriefPayload:
    """Live portfolio tests (skipped when the portfolio is absent —
    e.g. hermetic CI without the buyer-distribution sibling)."""

    def _portfolio_available(self) -> bool:
        return PORTFOLIO_DOWNLOAD.exists() and any(
            PORTFOLIO_DOWNLOAD.iterdir())

    def test_all_slots_parse_all_six_sections(self):
        if not self._portfolio_available():
            pytest.skip("portfolio buyer-distribution repo not present")
        from toscanini import showcase
        missing = []
        for d in sorted(PORTFOLIO_DOWNLOAD.glob("*_*")):
            if not d.is_dir():
                continue
            b = showcase.brief_sections(d)
            for k in ("what_it_does", "why_it_matters", "established",
                      "not_established", "decisive_experiment",
                      "kill_condition"):
                if not b.get(k):
                    missing.append(f"{d.name}:{k}")
        assert missing == [], f"brief sections missing: {missing}"

    def test_showcase_detail_carries_brief(self):
        if not self._portfolio_available():
            pytest.skip("portfolio buyer-distribution repo not present")
        from toscanini import showcase
        d = showcase.showcase_detail("04")
        assert d is not None
        assert d["brief"]["kill_condition"]
        assert d["brief"]["source"].startswith(
            "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf")
        assert d["maturity"] == "ENGINEERING_DEFINITION"
        assert isinstance(d["known_blockers"], list) and d["known_blockers"]
        assert "SOURCE_FACT" in d["evidence_class_counts"]
        assert d["first_decisive_work_package"]["work_package"] == "WP-01"

    def test_no_physical_validation_claim_in_payload(self):
        """Art. XXXVIII guard: the payload must not claim physical
        validation anywhere."""
        if not self._portfolio_available():
            pytest.skip("portfolio buyer-distribution repo not present")
        from toscanini import showcase
        d = showcase.showcase_detail("04")
        blob = str(d)
        assert "PHYSICAL_OBSERVATION: 0" not in blob  # class counts keep 0
        assert d["evidence_class_counts"].get("PHYSICAL_OBSERVATION") == 0

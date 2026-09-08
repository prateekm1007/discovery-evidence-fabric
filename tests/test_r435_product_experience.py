"""R435 — THE PRODUCT EXPERIENCE RESET tests.

The round directive: stop treating the Dossier as the primary UI; the
3D technology artifact becomes the hero of one calm workspace; engine
vocabulary moves to the deep layer; schema scaffolding is NEVER
presented as the finished invention. Constitutional anchors:

- Art. VI (never manufacture provenance) / Art. II — an LLM that echoes
  the prompt's placeholder examples produced NO content: the echo is a
  MISSING field, the generation fails honestly.
- Art. XXV — four distinct honest states (missing data / generation
  failed / legitimate unknown / schema fallback) never collapse.
- Art. X — the dossier stays the canonical projection; the scaffolding
  guard suppresses at the presentation boundary and never mutates the
  underlying record.
- Art. LXIV — the superseded split-pane components are RETIRED (deleted,
  functionality migrated), not accumulated.
- Art. LXX — all new user-facing copy is English.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import evolution as evo  # noqa: E402
from toscanini import dossier as dos  # noqa: E402

WEBAPP = REPO / "TOSCANINI_UI" / "webapp"

# the primary-surface components (the stage; the deep layer may keep
# engine vocabulary where rigor belongs)
PRIMARY_SURFACE = [
    WEBAPP / "components" / "TechStage.tsx",
    WEBAPP / "components" / "InventionStage.tsx",
    WEBAPP / "components" / "ModelViewer.tsx",
]

ENGINE_VOCAB_PRIMARY = (
    "COMPUTATIONAL_RESULT",
    "EVIDENCE-CLASS COUNTS",
    "HYPOTHESIZED",
    "FAILED_SCIENTIFIC",
    "NOT ESTABLISHED",
)


# ---------------------------------------------------------------------------
# A. template-echo rejection at the generator boundary (evolution.py)
# ---------------------------------------------------------------------------
class TestTemplateEchoGuard:
    def test_detects_bracketed_placeholders(self):
        assert evo._is_template_echo(
            "<the causal mechanism the architecture exploits>")
        assert evo._is_template_echo(
            "  <the new measurable expected effect> ")

    def test_detects_bare_known_phrases(self):
        assert evo._is_template_echo(
            "the specific engineering intervention on the device")
        assert evo._is_template_echo(
            "the cheapest concrete test that could kill it")

    def test_real_content_passes(self):
        assert not evo._is_template_echo(
            "Flash-injection cooling with two-stage throttling")
        assert not evo._is_template_echo(
            "AI-driven predictive thermal management")
        assert not evo._is_template_echo("")
        assert not evo._is_template_echo("< inline math like <x> >")

    def test_parse_fields_still_extracts_real_lines(self):
        content = (
            "MECHANISM: real mechanism text\n"
            "INTERVENTION: <the specific engineering intervention on the device>\n"
            "EXPECTED_EFFECT: real effect"
        )
        fields = evo._parse_fields(
            content, ["MECHANISM", "INTERVENTION", "EXPECTED_EFFECT"])
        assert fields["mechanism"] == "real mechanism text"
        assert fields["expected_effect"] == "real effect"

    def test_llm_generate_filters_echo_and_records_it(self, monkeypatch):
        """The R435 defect, closed at the source: a weak model echoing
        the prompt's format examples must produce a MISSING field, and
        the rejection must be inspectable (Art. XXXI)."""
        echo_content = (
            "MECHANISM: <the causal mechanism the architecture exploits>\n"
            "INTERVENTION: <the specific engineering intervention on the device>\n"
            "EXPECTED_EFFECT: <the measurable expected effect>\n"
            "FALSIFICATION_TEST: real falsification text\n"
            "OPERATING_REGIME: <the operating regime the architecture assumes>"
        )
        _fake_reg(monkeypatch, echo_content)

        call = evo._llm_generate("prompt", "system",
                                 ["MECHANISM", "INTERVENTION",
                                  "EXPECTED_EFFECT", "FALSIFICATION_TEST",
                                  "OPERATING_REGIME"],
                                 purpose="test:echo")
        # every echo field is MISSING — never a value (Art. VI)
        assert call["fields"].get("mechanism") is None
        assert call["fields"].get("intervention") is None
        assert call["fields"].get("expected_effect") is None
        assert call["fields"].get("operating_regime") is None
        # the real field survives
        assert call["fields"]["falsification_test"] == \
            "real falsification text"
        # the rejection is recorded and inspectable
        assert set(call.get("template_echo_rejected") or []) == {
            "mechanism", "intervention", "expected_effect",
            "operating_regime"}

    def test_baseline_generation_fails_honestly_on_echo(self, monkeypatch):
        """Echo-only intervention -> NO architecture is fabricated; the
        caller's None path is the honest record-empty state."""
        echo_content = (
            "MECHANISM: <the causal mechanism the architecture exploits>\n"
            "INTERVENTION: <the specific engineering intervention on the device>\n"
        )
        _fake_reg(monkeypatch, echo_content)
        problem = {"device": "x", "failure_mode": "y",
                   "constraint": "z", "failure": "full"}
        arch = evo.generate_baseline_architecture(problem, [])
        assert arch is None

    def test_baseline_generation_rejects_echo_provenance_record(
            self, monkeypatch):
        """Mixed echo/real output: the architecture carries the echo
        rejection in generated_by (Art. XXXI memory artifact)."""
        content = (
            "MECHANISM: real mechanism\n"
            "INTERVENTION: real intervention\n"
            "EXPECTED_EFFECT: <the measurable expected effect>\n"
            "FALSIFICATION_TEST: real test\n"
            "OPERATING_REGIME: real regime\n"
        )
        _fake_reg(monkeypatch, content)
        problem = {"device": "x", "failure_mode": "y",
                   "constraint": "z", "failure": "full"}
        arch = evo.generate_baseline_architecture(problem, [])
        assert arch is not None
        assert arch["mechanism"] == "real mechanism"
        assert arch["expected_effect"] == ""  # echo -> missing, not value
        assert arch["generated_by"]["template_echo_rejected"] == \
            ["expected_effect"]


def _fake_reg(monkeypatch, content: str):
    """Patch the LLM registry with a deterministic fake response."""

    class FakeResult:
        def __init__(self):
            self.status = "OK"
            self.provider_id = "test-provider"
            self.error = ""
            self.content = content

        def to_meta(self):
            return {"model": "test-model"}

    import discovery_fabric.engine.llm_registry as real_reg
    monkeypatch.setattr(real_reg, "generate", lambda **kw: FakeResult())


# ---------------------------------------------------------------------------
# B. schema-scaffolding guard at the projection boundary (dossier.py)
# ---------------------------------------------------------------------------
def _mk_session(tmp_path: Path, *, mechanism: str,
                evolution_why=None, status="COMPLETE") -> dict:
    """A minimal canonical run with ONE geometry generation + a
    BRIDGE_REPORT carrying the evolution projection (the same artifact
    shapes a real run persists)."""
    rd = tmp_path / "ENGINE_RUNS" / "run_r435"
    rd.mkdir(parents=True, exist_ok=True)
    model = rd / "MODEL"
    model.mkdir(exist_ok=True)
    (model / "model-002.glb").write_bytes(b"glb-bytes")

    spec = {
        "invention_id": "INV-R435",
        "mechanism": {"value": mechanism},
        "problem": {"value": {"device": "test device"}},
        "evidence": {"value": [], "evidence_ids": []},
    }
    (rd / "INVENTION_SPECIFICATION.json").write_text(json.dumps(spec))
    (rd / "final_state.json").write_text(
        json.dumps({"final_status": "EVOLVED_INVENTION_CANDIDATE"}))

    evo_rows = [
        {"generation": 1, "status": "SUPERSEDED",
         "why": "challenged and superseded (real why)", "current": False},
        {"generation": 2, "status": "CURRENT",
         "why": evolution_why, "current": True},
    ]
    bridge = {
        "case": "B",
        "outcome": "COMPLETED",
        "conceptual": True,
        "geometry": {
            "present": True,
            "glb": "MODEL/model-002.glb",
            "domain_family": "VEHICLE",
            "generation_id": "gen-2",
            "generation_count": 2,
            "evolution": evo_rows,
        },
    }
    (rd / "BRIDGE_REPORT.json").write_text(json.dumps(bridge))
    return {
        "session_id": "ts_r435_test",
        "user_text": "a real technical problem statement for the test",
        "status": status,
        "created_at": "2026-09-09T09:00:00Z",
        "final_status": "EVOLVED_INVENTION_CANDIDATE",
        "run_dir": str(rd),
    }


class TestDossierScaffoldGuard:
    def test_scaffold_like_unit(self):
        assert dos._scaffold_like(
            "<the causal mechanism the architecture exploits>")
        assert dos._scaffold_like(
            "the measurable expected effect")
        assert not dos._scaffold_like("a real mechanism sentence")
        assert not dos._scaffold_like("")
        assert not dos._scaffold_like(None)

    def test_suppress_scaffold_returns_none_for_scaffold(self):
        assert dos._suppress_scaffold(
            "<the new causal mechanism>") is None
        assert dos._suppress_scaffold("real text") == "real text"

    def test_overview_mechanism_suppressed_with_explicit_state(
            self, tmp_path):
        """The four honest states stay distinct: scaffolding renders as
        an explicit generation-incomplete state — not as the invention,
        not as a PENDING (missing data), not as UNKNOWN."""
        s = _mk_session(tmp_path,
                        mechanism="<the causal mechanism the "
                                  "architecture exploits>")
        d = dos.build_dossier(s)
        ov = d["tabs"]["overview"]
        assert ov["mechanism"] is None
        assert ov["mechanism_generation_failed"] is True
        assert "did not produce a usable mechanism" in ov["note"]

    def test_real_mechanism_untouched(self, tmp_path):
        s = _mk_session(tmp_path,
                        mechanism="passive capillary wicking with a "
                                  "hydrophilic floor channel")
        d = dos.build_dossier(s)
        ov = d["tabs"]["overview"]
        assert ov["mechanism"] == (
            "passive capillary wicking with a hydrophilic floor channel")
        assert ov["mechanism_generation_failed"] is False

    def test_evolution_why_scaffold_suppressed(self, tmp_path):
        s = _mk_session(
            tmp_path,
            mechanism="real mechanism",
            evolution_why="<the new causal mechanism>")
        d = dos.build_dossier(s)
        design = d["tabs"]["design"]
        rows = design["evolution"]
        assert rows[0]["why"] == "challenged and superseded (real why)"
        assert rows[1]["why"] is None

    def test_guard_never_mutates_the_record(self, tmp_path):
        """Art. X: the projection suppresses presentation-side only; the
        INVENTION_SPECIFICATION on disk still carries its raw field."""
        scaffold = "<the causal mechanism the architecture exploits>"
        s = _mk_session(tmp_path, mechanism=scaffold)
        dos.build_dossier(s)
        raw = json.loads(
            (Path(s["run_dir"]) / "INVENTION_SPECIFICATION.json")
            .read_text())
        assert raw["mechanism"]["value"] == scaffold

    def test_challenged_and_experiment_text_also_guarded(self, tmp_path):
        """Defense in depth covers the other primary-surface text
        fields the overview renders."""
        assert dos._suppress_scaffold(
            "the cheapest concrete test that could kill it") is None


# ---------------------------------------------------------------------------
# C. the product surface: language, single viewer, retirement (Art. LXIV)
# ---------------------------------------------------------------------------
class TestProductSurface:
    def test_retired_components_are_gone(self):
        """Art. LXIV: DossierPane and InvestigationPane were superseded
        by the technology stage (functionality migrated, disposition
        recorded in the commit) — they must not linger."""
        assert not (WEBAPP / "components" / "DossierPane.tsx").exists()
        assert not (WEBAPP / "components" /
                    "InvestigationPane.tsx").exists()

    def test_new_stage_components_exist(self):
        for f in ("TechStage.tsx", "DeepDive.tsx", "DossierSections.tsx",
                  "InventionStage.tsx"):
            assert (WEBAPP / "components" / f).exists(), f

    def test_primary_surface_speaks_product_language(self):
        """Engine vocabulary must not appear in the primary-surface
        components' USER-VISIBLE copy (comments are code documentation,
        not product copy; the deep layer — DeepDive/DossierSections/
        ScienceEvents — legitimately keeps the vocabulary where rigor
        lives)."""
        import re as _re
        for f in PRIMARY_SURFACE:
            src = f.read_text()
            code = _re.sub(r"//[^\n]*", "", src)
            code = _re.sub(r"/\*.*?\*/", "", code, flags=_re.S)
            for vocab in ENGINE_VOCAB_PRIMARY:
                assert vocab not in code, (f.name, vocab)

    def test_single_viewer_by_construction(self):
        """The ONE-viewer invariant at the source level: exactly one
        <ModelViewer render per stage component; the deep layer renders
        NONE (evolution/history act on the stage hero)."""
        counts = {
            "TechStage.tsx": 1,
            "InventionStage.tsx": 1,
            "DeepDive.tsx": 0,
            "DossierSections.tsx": 0,
        }
        for name, want in counts.items():
            src = (WEBAPP / "components" / name).read_text()
            got = src.count("<ModelViewer")
            assert got == want, (name, got, want)

    def test_stage_carries_the_product_contract_markers(self):
        src = (WEBAPP / "components" / "TechStage.tsx").read_text()
        for marker in (
            "data-tech-stage",
            "data-hero-viewport",
            "data-stage-insights",
            "data-stage-actions",
            "What changed",
            "Why it works",
            "What supports it",
            "What could kill it",
            "Test this",
            "Compare generations",
            "technology package",
            "Preparing technology visualization",
        ):
            assert marker in src, marker

    def test_deep_layer_progressive_disclosure_markers(self):
        src = (WEBAPP / "components" / "DeepDive.tsx").read_text()
        for marker in ("data-deep-dive", "dd-sec", "journal", "summary",
                       "model", "evidence", "engineering", "experiment",
                       "package", "ask"):
            assert marker in src, marker

    def test_english_only_new_copy(self, tmp_path):
        """Art. LXX: the newly authored user-facing copy is English
        (the R419 english-only guard covers the repo; this asserts the
        new stage components carry no non-Latin authorship script)."""
        import re as _re
        for f in PRIMARY_SURFACE + [WEBAPP / "components" / "DeepDive.tsx",
                                    WEBAPP / "components" /
                                    "DossierSections.tsx"]:
            src = f.read_text()
            # strip comments (code comments may quote anything)
            code = _re.sub(r"//[^\n]*", "", src)
            non_latin = _re.findall(r"[\u0400-\u04FF\u4E00-\u9FFF"
                                    r"\u3040-\u30FF\uAC00-\uD7AF]", code)
            assert not non_latin, (f.name, non_latin[:5])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

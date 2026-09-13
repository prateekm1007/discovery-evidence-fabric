"""R452-C2 item 2 — the sovereign-state boundary.

Coder 1's canonical state is sovereign. The presentation layer must
not infer scientific completion from the PRESENCE of artifacts (a GLB,
a PDF, an engineering JSON), from old UI fields, or from diagnostic
metadata. The visual layer may render the honest non-claim states
(unknown-class, blocked, ready-for-review, visual-ready); it must
never manufacture VALIDATED / SURVIVOR / ENGINEERING_READY.

Three pins:
  1. structural absence — no shipping presentation source carries the
     forbidden state vocabulary at all;
  2. presence-only runs — a run dir whose ONLY signals are artifact
     presence produces NO ready milestone, NO engineering authority
     claim, and no completion wording anywhere in the dossier
     projection;
  3. the vocabulary boundary — the mapping's own exported state union
     is free of the forbidden tokens (the backend projection the UI
     consumes verbatim carries none either).

(The UI-side half of pins 1 and 3 lives in scripts/r451_c2_ui_tests.mjs
— one boundary, two batteries, same rule.)
"""
import json
import re
from pathlib import Path

import pytest

from toscanini import dossier as dossier_mod

REPO = Path(__file__).resolve().parents[1]
WEBAPP = REPO / "TOSCANINI_UI" / "webapp"

FORBIDDEN_VOCABULARY = re.compile(r"\b(VALIDATED|SURVIVOR|ENGINEERING_READY)\b")

PRESENTATION_SOURCES = [
    WEBAPP / "lib" / "presentationState.ts",
    WEBAPP / "components" / "TechStage.tsx",
    WEBAPP / "components" / "InfrastructureBlockedHero.tsx",
    WEBAPP / "components" / "DossierSections.tsx",
    WEBAPP / "components" / "DeepDive.tsx",
    WEBAPP / "components" / "DiscoveryPipelineStrip.tsx",
]


def _session(status="COMPLETE", run_dir=None):
    return {"session_id": "ts_r452_sovereign", "status": status,
            "problem_id": "p_r452", "run_dir": str(run_dir) if run_dir
            else None}


class TestNoManufacturedStateVocabulary:
    def test_presentation_sources_carry_no_forbidden_tokens(self):
        """The shipping presentation layer has NO manufacturing
        vocabulary: VALIDATED / SURVIVOR / ENGINEERING_READY appear
        nowhere in the six presentation sources (structural absence,
        stronger than a behavior test — there is no code path to
        attack)."""
        for src in PRESENTATION_SOURCES:
            assert src.is_file(), f"missing presentation source {src.name}"
            assert not FORBIDDEN_VOCABULARY.search(src.read_text()), \
                f"{src.name} carries a manufactured-state token"

    def test_projection_output_carries_no_forbidden_tokens(self, tmp_path):
        """The dossier projection for a presence-only run renders no
        completion claim: every row status/detail is free of the
        forbidden tokens."""
        run = tmp_path / "ts_presence"
        run.mkdir()
        (run / "problem.json").write_text("{}")
        (run / "ENGINEERING_SPECIFICATION.json").write_text("{}")
        (run / "MODEL").mkdir()
        (run / "MODEL" / "model-001.glb").write_bytes(b"glb-bytes")
        (run / "PACKAGE.pdf").write_bytes(b"%PDF-1.4 stray pdf")
        d = dossier_mod.build_dossier(_session(run_dir=run))
        blob = json.dumps(d)
        assert not FORBIDDEN_VOCABULARY.search(blob)


class TestPresenceOnlyNeverClaimsCompletion:
    def test_stray_artifacts_never_reach_geometry_available(self, tmp_path):
        """GLB + PDF + engineering JSON present, NO canonical identity
        chain, NO recorded authority: the geometry state stays in the
        honest non-ready set and the contract's engineering authority
        is never ENGINEERING (presence is never an authority — Art.
        XXVIII; the R451-C2.3 identity chain)."""
        run = tmp_path / "ts_presence"
        run.mkdir()
        (run / "problem.json").write_text("{}")
        (run / "ENGINEERING_SPECIFICATION.json").write_text("{}")
        (run / "MODEL").mkdir()
        (run / "MODEL" / "model-001.glb").write_bytes(b"glb-bytes")
        (run / "PACKAGE.pdf").write_bytes(b"%PDF-1.4 stray pdf")
        s = _session(run_dir=run)
        d = dossier_mod.build_dossier(s)
        design = d["tabs"]["design"]
        assert design["geometry_state"] != "geometry_available"
        assert design["geometry_state"] != "visual_complete"
        contract = design.get("geometry_contract") or {}
        assert contract.get("engineering_authority") != "ENGINEERING"
        # the strip's visualization row never shows a ready milestone
        rows = {r["key"]: r for r in d["pipeline"]}
        assert rows["visualization"]["status"] != "RECEIVED"

    def test_diagnostic_metadata_is_never_an_authority(self, tmp_path):
        """Diagnostic metadata (a watchdog report, a render job note)
        claiming success is STILL not an authority: the geometry state
        ignores it (the C2.6 sovereign chain — diagnostics are
        readable, never certifying)."""
        run = tmp_path / "ts_diag"
        run.mkdir()
        (run / "problem.json").write_text("{}")
        (run / "MODEL").mkdir()
        (run / "MODEL" / "model-001.glb").write_bytes(b"glb-bytes")
        (run / "WATCHDOG_REPORT.json").write_text(json.dumps(
            {"verdict": "PASS", "join_state": "VISUAL_READY"}))
        (run / "RENDER_JOB.json").write_text(json.dumps(
            {"status": "done", "note": "rendered successfully"}))
        d = dossier_mod.build_dossier(_session(run_dir=run))
        design = d["tabs"]["design"]
        assert design["geometry_state"] != "visual_complete"
        assert design["geometry_state"] != "geometry_available"


class TestTheFiveStateVocabularyIsBackendTyped:
    def test_five_states_exist_and_legacy_value_is_not_emitted(self, tmp_path):
        """R452-C2 item 1a: the ledger emits the five-state vocabulary;
        the legacy RETRIEVED value stays READABLE (era normalization)
        but is no longer written by the current writer."""
        run = tmp_path / "ts_pos"
        run.mkdir()
        (run / "envelope_RETRIEVE.json").write_text(json.dumps(
            {"evidence": [{"title": "t", "source": "s",
                           "content_hash": "c" * 64}]}))
        tab = dossier_mod.evidence_ledger(_session(run_dir=run))
        assert tab["retrieval_state"] == "RETRIEVED_POSITIVE"
        run0 = tmp_path / "ts_zero"
        run0.mkdir()
        (run0 / "envelope_RETRIEVE.json").write_text(json.dumps(
            {"evidence": []}))
        tab0 = dossier_mod.evidence_ledger(_session(run_dir=run0))
        assert tab0["retrieval_state"] == "RETRIEVED_ZERO"
        # the blocked strip consumes the new typed values verbatim
        rows = dossier_mod.pipeline_projection(
            _session(status="RUN_BLOCKED_TRANSPORT", run_dir=run),
            run, False, {"package_state": {"state": "NOT_PRODUCED"}},
            tab, {"geometry_state": "upstream_not_reached"})
        ev = next(r for r in rows if r["key"] == "evidence")
        assert ev["status"] == "RECEIVED"
        assert (ev.get("detail") or "") == "1 sources retrieved"

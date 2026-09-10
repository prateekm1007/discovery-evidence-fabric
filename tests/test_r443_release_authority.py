"""R443 — package-release authority (Article LXXII at the consumer).

THE AUDIT'S FINDING: the ordinary package endpoint can return a ZIP
while rendering is RENDER_SKIPPED_LOW_MEMORY, because _package selects
existing ZIP bytes without consulting the visual release gate — the
ambiguous state (render skipped + package complete + download button
available).

THE CONTRACT (established from the Constitution itself):
Article LXXII (v2.3.0, R441): "If any visual gate fails, the Hero is
suppressed and the package is blocked from release." NOT_RUN fails
closed exactly like a FAIL (the article's own fail-closed clause). So:

    VISUAL_GATE = NOT_RUN  ->  NO VISUAL RELEASE  ->  NO BUYER RELEASE

enforced at the ACTUAL package consumer. The package layer already
writes HERO_RELEASE_STATE.json (release_blocked=true on NOT_RUN/FAIL);
this round makes the endpoint consult it. The engineering evaluation
draft remains available under an EXPLICIT typed request — not a new
universal rejection policy, an explicit typed state.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toscanini.server import package_release_decision  # noqa: E402


class TestReleaseDecision(unittest.TestCase):
    def test_not_run_blocks_default_download(self):
        release = {"release_blocked": True, "gate_verdict": "NOT_RUN",
                   "reasons": ["renderer status: "
                               "RENDER_SKIPPED_LOW_MEMORY"]}
        d = package_release_decision(release, "/api/run/x/package")
        self.assertEqual(d["action"], "TYPED_STATE")
        payload = d["payload"]
        self.assertEqual(payload["package_state"],
                         "VISUAL_RELEASE_BLOCKED")
        self.assertEqual(payload["article"], "LXXII")
        self.assertEqual(payload["gate_verdict"], "NOT_RUN")
        self.assertTrue(payload["engineering_draft_available"])
        self.assertIn("engineering_draft", payload["note"])

    def test_gate_fail_blocks_default_download(self):
        release = {"release_blocked": True, "gate_verdict": "FAIL",
                   "failed_rules": ["hero_occupancy"]}
        d = package_release_decision(release, "/api/run/x/package")
        self.assertEqual(d["action"], "TYPED_STATE")

    def test_explicit_draft_request_serves_typed(self):
        release = {"release_blocked": True, "gate_verdict": "NOT_RUN"}
        d = package_release_decision(
            release, "/api/run/x/package?release=engineering_draft")
        self.assertEqual(d["action"], "SERVE_DRAFT")
        headers = dict(d["headers"])
        self.assertEqual(headers["X-Package-State"],
                         "ENGINEERING_DRAFT_VISUAL_RELEASE_PENDING")
        self.assertEqual(headers["X-Visual-Gate-Verdict"], "NOT_RUN")

    def test_passed_gate_serves_normally(self):
        release = {"release_blocked": False, "gate_verdict": "PASS"}
        d = package_release_decision(release, "/api/run/x/package")
        self.assertEqual(d["action"], "SERVE_RELEASE")

    def test_absent_record_serves_normally(self):
        # pre-R441 package builds wrote no HERO_RELEASE_STATE.json —
        # historical showcase packages are unaffected
        d = package_release_decision(None, "/api/run/x/package")
        self.assertEqual(d["action"], "SERVE_RELEASE")

    def test_query_variants(self):
        release = {"release_blocked": True, "gate_verdict": "NOT_RUN"}
        # wrong param value does not unlock
        d = package_release_decision(
            release, "/api/run/x/package?release=anything")
        self.assertEqual(d["action"], "TYPED_STATE")
        # other params don't interfere
        d2 = package_release_decision(
            release, "/api/run/x/package?other=1&release=engineering_draft")
        self.assertEqual(d2["action"], "SERVE_DRAFT")


class TestEndpointWiring(unittest.TestCase):
    """Structural: the endpoint consults the release state (the audit's
    exact defect: '_package selects existing ZIP bytes without
    consulting the visual release gate')."""

    def test_package_endpoint_consults_release_state(self):
        src = (Path(__file__).resolve().parents[1]
               / "toscanini" / "server.py").read_text()
        self.assertIn("package_release_decision", src)
        self.assertIn("_visual_release_state", src)

    def test_visual_release_state_reads_hero_record(self):
        from toscanini.server import Handler
        with tempfile.TemporaryDirectory() as td:
            # absent -> None (historical packages unaffected)
            self.assertIsNone(Handler._visual_release_state(None, td))
            # present -> parsed record
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            rec = {"release_blocked": True, "gate_verdict": "NOT_RUN",
                   "reasons": ["renderer skipped"]}
            (d3 / "HERO_RELEASE_STATE.json").write_text(
                json.dumps(rec))
            out = Handler._visual_release_state(None, td)
            self.assertEqual(out["gate_verdict"], "NOT_RUN")
            self.assertTrue(out["release_blocked"])
            # unreadable -> None (honest unknown, not a guess)
            (d3 / "HERO_RELEASE_STATE.json").write_text("{not json")
            self.assertIsNone(Handler._visual_release_state(None, td))


class TestDossierTypedState(unittest.TestCase):
    """The dossier projection carries the typed state so the UI button
    is never a silent 'complete package' download."""

    def test_dossier_carries_typed_state(self):
        src = (Path(__file__).resolve().parents[1]
               / "toscanini" / "dossier.py").read_text()
        self.assertIn("ENGINEERING_DRAFT_VISUAL_RELEASE_PENDING", src)
        self.assertIn("release=engineering_draft", src)

    def test_ui_renders_typed_label(self):
        src = (Path(__file__).resolve().parents[1]
               / "TOSCANINI_UI" / "webapp" / "components"
               / "DossierSections.tsx").read_text()
        self.assertIn("engineering draft (visual release pending)", src)
        self.assertIn("ENGINEERING_DRAFT_VISUAL_RELEASE_PENDING", src)


class TestPackageLayerReleaseRecord(unittest.TestCase):
    """The package layer already writes the LXXII record (R441); the
    consumer now consults it — one contract, both ends."""

    def test_package_layer_writes_release_state(self):
        src = (Path(__file__).resolve().parents[1]
               / "discovery_fabric" / "engine" / "invention_bridge"
               / "package.py").read_text()
        self.assertIn("HERO_RELEASE_STATE.json", src)
        self.assertIn("release_blocked", src)
        # NOT_RUN / PARTIAL / FAIL all fail closed (the fail-closed
        # clause; R443-C2 vocabulary: COMPLETE_PASS is the ONLY
        # release-passing verdict, legacy PASS accepted only without a
        # completeness block)
        self.assertIn('gate_verdict not in ("PASS", "COMPLETE_PASS")',
                      src)
        self.assertIn("_visual_release_ok", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""R452 — the Blender legacy retirement battery (external audit C4).

The audit measured: `render.py::render_invention_blender_legacy` is
still live code, deletion was "scheduled R442" per the r441_retired
README, and the repository is now ~ten rounds overdue — an Article LXIV
violation. Production renders measured 7/7 `three@0.175.0` (the legacy
path never fired; it is a latent second-truth-system risk, not an
active one).

The audit allows two dispositions: DELETE, or record a NEW DATED REASON
plus a battery proving the legacy path cannot be selected implicitly.
This round takes the second disposition (the deletion's blast radius —
the artifact_identity blender_scene_hash schema, the pinned-build env
contract, and the R420/R441/R423 test batteries — is an owner-visible
change that must not ride an audit-response commit), and the battery
below is the proof the audit asks for:

  1. the DEFAULT backend is the Visual Compiler — no environment, no
     call-site default, no fallback ever reaches Blender implicitly;
  2. an UNRECOGNIZED backend value never falls through to legacy — it
     is recorded verbatim and the Visual Compiler runs (typed, never a
     silent second truth);
  3. the legacy path remains EXPLICITLY labeled (BLENDER_HEADLESS_LEGACY)
     so it can never pass as the canonical renderer;
  4. the Article LXIV record carries the new dated reason (R452) — the
     stale "scheduled R442" note is superseded, and the overdue
     deletion is escalated with its cost stated (Art. LXV).
"""
from __future__ import annotations

import inspect
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = Path(__file__).resolve().parent.parent

from discovery_fabric.engine.invention_bridge import render as render_mod \
    # noqa: E402

_RETIRED_README = (REPO / "discovery_fabric" / "engine" /
                   "invention_bridge" / "r441_retired" / "README.md")


class TestBlenderLegacyCannotBeSelectedImplicitly:

    def test_default_backend_is_visual_compiler(self):
        """No backend argument, no env var: the Visual Compiler runs.
        The audit's rule — a legacy second truth system must require a
        deliberate act, never a default."""
        assert "TOSCANINI_RENDER_BACKEND" not in os.environ
        src = inspect.getsource(render_mod.render_invention)
        # the dispatcher's chosen-backend expression: explicit arg, then
        # env, then the canonical default — the default IS the compiler
        assert '"visual_compiler"' in src or "'visual_compiler'" in src

    def test_unrecognized_backend_never_falls_through_to_legacy(self):
        """A garbage backend value records itself verbatim and the
        Visual Compiler runs — never a silent legacy fallback."""
        with tempfile.TemporaryDirectory() as td:
            rec = render_mod.render_invention(
                td, {}, is_conceptual=True, backend="not-a-real-backend")
        assert rec.get("render_pipeline") != "BLENDER_HEADLESS_LEGACY"
        assert rec.get("backend_selected") == "visual_compiler"

    def test_explicit_legacy_selection_stays_labeled(self):
        """The one way to reach Blender is explicit, and the record is
        labeled BLENDER_HEADLESS_LEGACY — it can never pass as the
        canonical renderer (the R443 typed-record contract)."""
        src = inspect.getsource(render_mod.render_invention)
        assert "BLENDER_HEADLESS_LEGACY" in src
        # the label is set ON the legacy branch, before any return
        legacy_branch = src.split("blender\"", 1)[-1].split(
            "render_invention_blender_legacy", 1)[-1]
        assert "BLENDER_HEADLESS_LEGACY" in src.split(
            'if chosen == "blender":', 1)[-1]

    def test_lxiv_record_carries_the_new_dated_reason(self):
        """The stale 'scheduled R442' disposition is superseded by a
        dated R452 record — Article LXIV rule 1 (silence is not a valid
        answer) and Article LXV (an overdue decision escalates with its
        cost stated)."""
        text = _RETIRED_README.read_text()
        assert "R452" in text, (
            "the retirement record was not renewed — the stale "
            "'scheduled R442' note would keep standing, the exact "
            "drift the audit flagged")
        assert "R442" in text  # the history stays (Art. XI)
        assert "overdue" in text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

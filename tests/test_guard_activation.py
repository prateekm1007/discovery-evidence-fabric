#!/usr/bin/env python3
"""tests/test_guard_activation.py — the AM37 D4 in-suite activation
assertions (the standing "is the guard actually active?" check).

AM37 section 4: F53 was the THIRD "file exists but does not defend"
instance (F32, F52, F53) — the pattern is worth a standing check.
This suite asserts ACTIVATION, not existence:

  1. core.hooksPath is CONFIGURED to .githooks (the R39 discovery:
      the hook existed since R11 but never ran because the config
      was never set);
  2. the hook file RUNS the F21 audit-branch guard with failure
     propagation (no bare `exec python3` of the guard — the exec
     REPLACES the process and made every later check dead code) and
     blocks staged merge markers;
  3. the CI workflow carries the bind suites (seal_anchor,
     am29_binds) and the probe pins — the F52 discovery was that the
     bind suite existed but did not GATE queue pushes;
  4. the v7 transport requests the corrected R-REQID id
     (glm-4-plus) — forward-only per AM37 section 2.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))


def test_hooks_path_is_configured():
    out = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, (
        "core.hooksPath is NOT configured — the pre-commit hook is "
        "inert (the F32/F52/F53 class: a guard that does not run)")
    assert out.stdout.strip() == ".githooks", out.stdout.strip()


def test_hook_runs_guard_and_blocks_markers():
    hook = (REPO / ".githooks" / "pre-commit").read_text(
        encoding="utf-8")
    assert "audit_branch_guard.py" in hook, "the F21 guard is gone"
    assert "exec python3" not in hook, (
        "the guard is exec'd — `exec` REPLACES the process and makes "
        "every later check dead code (the R39 refusal-path discovery)")
    assert "|| exit $?" in hook, (
        "the guard's failure is not propagated — a failing guard must "
        "refuse the commit, not be swallowed")
    assert "CONFLICT MARKERS" in hook and "grep -qE" in hook, (
        "the F53 marker check is missing from the hook")
    # the guard script itself must exist (fail-closed hook)
    guard = REPO / "discovery_fabric" / "audit_branch_guard.py"
    assert guard.exists(), "the guard script is missing (fail-closed)"


def test_ci_gates_the_bind_suites():
    wf_dir = REPO / ".github" / "workflows"
    assert wf_dir.exists(), "no CI workflow dir"
    blob = "\n".join(
        p.read_text(encoding="utf-8") for p in wf_dir.glob("*.yml"))
    assert "seal_anchor" in blob, (
        "the seal-anchor suite does not gate CI (F52 class)")
    assert "am29_binds" in blob, (
        "the AM29 bind suite does not gate CI (F52 class)")
    assert "test_r38_probe_pins" in blob or "probe" in blob, (
        "the probe pins do not gate CI")


def test_v7_request_id_is_the_corrected_registration():
    from r40_machine_v77 import V77_REQUEST_MODEL  # noqa: E402
    assert V77_REQUEST_MODEL == "agnes-3.0-flash", (
        "the transport must request the registered id "
        "(forward-only per AM37 section 2; the r64s4 owner-directed "
        "registration superseding R36 per AM60)")

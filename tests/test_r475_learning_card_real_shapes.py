#!/usr/bin/env python3
"""R475 — the learning-card battery the R472 battery could not write:
every fixture is a VERBATIM durable-branch payload (the exact bytes
production wrote), extracted by scripts/r475_fixtures.py.

The operator's three-way proof (live, function-level, population-level)
established that the R472 gate was structurally dead on its target
class: it read final_status against a set containing the OUTCOME name
INVENTION_KILLED_BY_CHALLENGE, while killed runs carry
final_status=INVENTION_UNDER_DEVELOPMENT. The R472 battery's killed
tests constructed the synthetic shape — green while the real class was
dead — the fourth instance of a claim standing on non-executing
evidence. This battery executes against the real shapes:
  - 3 real genuine-kill runs (card fires, fields from real records);
  - the real MECHANISM_GENERATION_FAILED control (still fires);
  - a real capability-kill-only lineage (NEVER fires — Art. LXI);
  - a real never-challenged lineage (NEVER fires);
  - the old-gate reversion pin (the frozen set alone closes on the
    real shape — the authority leg is what opens it);
  - the mev honesty pin (never contradicts a recorded
    evidence_verified=true).
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from toscanini import run_state as rs  # noqa: E402

FIX = REPO / "tests" / "fixtures" / "r475"


def _run_dir(tmp_path, name):
    rd = tmp_path / name
    rd.mkdir()
    shutil.copy(FIX / f"{name}_lineage.json", rd / "INVENTION_LINEAGE.json")
    return rd


def _session(name):
    return json.load(open(FIX / f"{name}_session.json"))


def _real_mechanism(name):
    """The mechanism statement the REAL lineage records for the last
    genuine kill — generation['architecture']['mechanism']."""
    lin = json.load(open(FIX / f"{name}_lineage.json"))
    g = lin["generations"][-1]
    arch = g.get("architecture") or {}
    return (g.get("mechanism")
            or (arch.get("mechanism") if isinstance(arch, dict) else None)
            or (arch if isinstance(arch, str) else None))


# ---------------------------------------------------------------------------
# the target class, REAL shapes: fires
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["killed_1", "killed_2", "killed_3"])
def test_real_genuine_kill_payloads_fire(tmp_path, name):
    s = _session(name)
    rd = _run_dir(tmp_path, name)
    card = rs.learning_card(s, rd)
    assert card is not None, (
        f"{name}: the card must fire on the REAL killed shape "
        f"(final_status={s.get('final_status')!r} + genuine-kill lineage)")
    assert card["kind"] == "no_survivor_learning_card"
    # what_was_tested: the real generation count
    assert "1 candidate mechanism was generated" in card["what_was_tested"]
    # strongest_failed_hypothesis: the REAL recorded architecture, not
    # the anonymous fallback the synthetic fixtures let pass
    mech = _real_mechanism(name)
    assert mech and mech[:40] in card["strongest_failed_hypothesis"], (
        "the card must quote the recorded killed architecture")
    assert "killed by the machine's own challenge" in \
        card["strongest_failed_hypothesis"]
    assert card["basis"].startswith("derived from the run's own records")


def test_real_control_generation_failed_still_fires(tmp_path):
    s = _session("control")
    rd = _run_dir(tmp_path, "control")
    card = rs.learning_card(s, rd)
    assert card is not None
    assert "no candidate mechanism was produced" in card["what_was_tested"] \
        or "no hypothesis reached the challenge" in \
        card["strongest_failed_hypothesis"]


# ---------------------------------------------------------------------------
# the discriminating negatives, REAL shapes: never fire (Art. LXI)
# ---------------------------------------------------------------------------

def test_real_capability_kill_only_lineage_never_fires(tmp_path):
    s = _session("capkill")
    rd = _run_dir(tmp_path, "capkill")
    assert rs.learning_card(s, rd) is None, (
        "a capability-kill-only lineage is an infrastructure failure, "
        "never a scientific no-survivor (Art. LXI)")


def test_real_never_challenged_lineage_never_fires(tmp_path):
    s = _session("nokill")
    rd = _run_dir(tmp_path, "nokill")
    assert rs.learning_card(s, rd) is None


def test_real_shape_with_survivor_stays_card_less(tmp_path):
    """The R472 survivor pin, re-executed on the real final_status
    vocabulary: a killed-then-survived lineage never yields a card."""
    s = _session("killed_1")
    lin = json.load(open(FIX / "killed_1_lineage.json"))
    lin["survivor_reached"] = True
    rd = tmp_path / "surv"
    rd.mkdir()
    (rd / "INVENTION_LINEAGE.json").write_text(json.dumps(lin))
    assert rs.learning_card(s, rd) is None


# ---------------------------------------------------------------------------
# the reversion + honesty pins
# ---------------------------------------------------------------------------

def test_old_gate_alone_closes_on_the_real_shape(tmp_path):
    """The reversion pin: the R472 frozen-set membership ALONE returns
    None for every real killed payload — if this assertion fails, the
    production vocabulary changed and the authority leg must be
    re-examined. The fix's authority leg (terminal_outcome) is what
    opens the gate; deleting it re-kills the target class."""
    for name in ("killed_1", "killed_2", "killed_3"):
        s = _session(name)
        final = (s.get("final_status") or "").upper()
        assert final not in rs._NO_SURVIVOR_FINAL_STATUSES, (
            f"{name}: {final!r} entered the frozen set — re-derive the "
            "gate contract")
        rd = _run_dir(tmp_path, name)
        assert rs.learning_card(s, rd) is not None


def test_mev_never_contradicts_recorded_evidence_verdict(tmp_path):
    """Art. VI pin: killed_1's real lineage records
    generation.evidence_verified=true — the card must NOT claim the run
    'worked without a verified evidence base'."""
    lin = json.load(open(FIX / "killed_1_lineage.json"))
    assert lin["generations"][-1].get("evidence_verified") is True
    s = _session("killed_1")
    rd = _run_dir(tmp_path, "killed_1")
    card = rs.learning_card(s, rd)
    assert card is not None
    assert "without a verified evidence base" not in \
        card["key_missing_evidence"]
    # the card names the run's own recorded diagnosis instead
    assert card["key_missing_evidence"]


def test_live_no_card_for_premise_and_blocked_classes(tmp_path):
    """The R472 exclusions hold on real-adjacent shapes (no lineage on
    disk -> the generation-failure class is the only qualifier)."""
    premise = {"status": "COMPLETE",
               "final_status": "MALFORMED_OR_FALSE_PREMISE"}
    blocked = {"status": "COMPLETE", "final_status":
               "RUN_BLOCKED_CAPABILITY"}
    live = {"status": "RUNNING", "final_status": ""}
    empty = tmp_path / "empty"
    empty.mkdir()
    for s in (premise, blocked, live):
        assert rs.learning_card(s, empty) is None

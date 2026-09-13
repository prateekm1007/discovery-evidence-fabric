"""R452 — the killed-invention authority tests (external audit B1/AT-7/
AT-12).

The audit measured, on 7/7 persisted production runs: the invention was
generated, killed by its own challenge (EVOLUTION_GEN_1.state =
INVENTION_REJECTED, challenge.killed = true), and then PROMOTED anyway
(final_status positive, found_something = true, rendered in 3D, and in
three cases packaged against NOT_A_SURVIVOR). The projection read
final_status and never consulted the generation's own challenge.

The fix under test, two halves:

  * engine (a2/classify.py): the span-format verification issues
    (missing_source_span / mechanism_span_not_verbatim / ...) are MODEL
    CAPABILITY failures — the TYPED status INCOMPLETE_INFERENCE_FAILURE
    + failure_class INFRASTRUCTURE_CAPABILITY (the merged-union
    vocabulary: the branch implementation's UNKNOWN terminal is
    subsumed by canonical main's typed capability status, consumed by
    run.py), promotion AND adjudication blocked, rerunnable, never the
    invention's kill_reason (Art. LXI);
  * projection (run_state/user_state): the lineage's challenge verdict
    is authoritative over final_status — a killed or unverified lineage
    is never "found something"; a GENUINE adversarial kill surfaces as
    rejected=true with the typed outcome INVENTION_KILLED_BY_CHALLENGE.

The lineage fixtures below are shaped exactly like the persisted
production records the audit quoted (EVOLUTION_GEN_1.json /
INVENTION_LINEAGE.json in the run dir).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.a2 import classify as a2_classify  # noqa: E402
from toscanini import run_state as rs_mod  # noqa: E402
from toscanini import user_state as us_mod  # noqa: E402


def _session(status="COMPLETE", final_status="EVOLVED_INVENTION_CANDIDATE",
             run_dir=None, package=None):
    return {"session_id": "ts_r452_kia", "status": status,
            "final_status": final_status,
            "package": package or {"complete": False},
            **({"run_dir": str(run_dir)} if run_dir else {})}


def _lineage_run(tmp_path, *, gen1_killed, gen1_reason,
                 gen2_survived=True, gen2_verified=False,
                 survivor_reached=True, final_status=None):
    """A run dir carrying the lineage records exactly as the engine
    persists them (challenge verdicts verbatim)."""
    gen1 = {
        "gen": 1, "state": "INVENTION_REJECTED" if gen1_killed
        else "INVENTION_CHALLENGED",
        "challenge": {"killed": gen1_killed,
                      "kill_reason": gen1_reason},
        "evidence_verified": False,
    }
    gens = [gen1]
    if gen2_survived:
        gens.append({
            "gen": 2, "state": "INVENTION_REQUIRES_EXPERIMENT",
            "challenge": {"killed": False, "survived": True},
            "evidence_verified": gen2_verified,
        })
    lineage = {
        "n_generations": len(gens),
        "generations": gens,
        "current_invention": {"gen": gens[-1]["gen"]},
        "survivor_reached": survivor_reached,
        "survivor_gen": gens[-1]["gen"] if survivor_reached else None,
        "stop_reason": "SURVIVOR_REACHED" if survivor_reached
        else "BUDGET_EXHAUSTED",
    }
    run = tmp_path / "run"
    run.mkdir(exist_ok=True)
    (run / "INVENTION_LINEAGE.json").write_text(json.dumps(lineage))
    (run / "EVOLUTION_GEN_1.json").write_text(json.dumps(gen1))
    return _session(run_dir=run,
                    final_status=final_status or
                    "EVOLVED_INVENTION_CANDIDATE")


# ---------------------------------------------------------------------------
# Engine half — capability failures are never scientific rejections
# ---------------------------------------------------------------------------

class TestCapabilitySeparation:

    def test_span_format_failures_are_capability_not_rejection(self):
        ev = {"verified": False,
              "issues": ["missing_source_span",
                         "mechanism_span_not_verbatim"]}
        out = a2_classify.classify({}, ev, {}, {"overall": "PASS"})
        # merged-union vocabulary: the typed capability status (canonical
        # main) carries the UNKNOWN terminal's semantics — never REJECTED,
        # never promoted, never adjudicated, rerunnable
        assert out["final_status"] == "INCOMPLETE_INFERENCE_FAILURE"
        assert out["failure_class"] == "INFRASTRUCTURE_CAPABILITY"
        assert out["promotion_blocked"] is True
        assert out["adjudication_blocked"] is True
        assert out["verification_state"] == "EVALUATED_FAILED_CAPABILITY"
        assert "rerunnable" in out["reason"]

    def test_mixed_issue_with_non_capability_still_rejects(self):
        ev = {"verified": False,
              "issues": ["missing_source_span", "invented_threshold"]}
        out = a2_classify.classify({}, ev, {}, {"overall": "PASS"})
        assert out["final_status"] == "REJECTED"

    def test_never_evaluated_stays_unknown(self):
        out = a2_classify.classify({}, {}, {}, {"overall": "PASS"})
        assert out["final_status"] == "UNKNOWN"
        assert out.get("verification_state") == "NOT_EVALUATED"


# ---------------------------------------------------------------------------
# Projection half — the lineage verdict is authoritative
# ---------------------------------------------------------------------------

class TestKilledInventionAuthority:

    def test_genuine_kill_never_reads_as_found(self, tmp_path):
        s = _lineage_run(
            tmp_path, gen1_killed=True,
            gen1_reason="adversarial challenge failed: "
                        "obvious_combination: KILLED")
        view = us_mod.user_state_view(s)
        # the audit's AT-7: a killed invention never reads as found
        assert view["found_something"] is False
        assert view["rejected"] is True
        assert view["outcome"] == rs_mod.OUTCOME_KILLED_BY_CHALLENGE
        assert "killed" in view["decision"].lower()

    def test_capability_kill_is_rejected_false_and_not_found(self, tmp_path):
        s = _lineage_run(
            tmp_path, gen1_killed=True,
            gen1_reason="evidence verification failed: missing_source_span; "
                        "mechanism_span_not_verbatim")
        view = us_mod.user_state_view(s)
        # Art. LXI: a capability failure is never a scientific rejection —
        # but it is ALSO never "found something"
        assert view["rejected"] is False
        assert view["found_something"] is False

    def test_unverified_promoted_survivor_not_found(self, tmp_path):
        s = _lineage_run(tmp_path, gen1_killed=True,
                         gen1_reason="evidence verification failed: "
                                     "missing_source_span",
                         gen2_survived=True, gen2_verified=False,
                         survivor_reached=True)
        view = us_mod.user_state_view(s)
        assert view["found_something"] is False
        assert view["rejected"] is False
        assert view["outcome"] == rs_mod.OUTCOME_UNDER_DEVELOPMENT
        assert "never verified" in view["decision"]

    def test_verified_survivor_still_found(self, tmp_path):
        """The positive control (Art. V): the learning loop stays
        expressible — a lineage whose later generation VERIFIES and
        survives is presented as found."""
        s = _lineage_run(tmp_path, gen1_killed=True,
                         gen1_reason="adversarial challenge failed: "
                                     "obvious_combination: KILLED",
                         gen2_survived=True, gen2_verified=True,
                         survivor_reached=True)
        view = us_mod.user_state_view(s)
        assert view["found_something"] is True
        assert view["rejected"] is False
        assert view["outcome"] == rs_mod.OUTCOME_REQUIRES_EXPERIMENT

    def test_no_lineage_keeps_legacy_behavior(self):
        """Backward compatibility: records without a lineage keep the
        pre-R452 projection (never fabricated from absence, Art. XXV)."""
        s = _session(run_dir=None,
                     final_status="EVOLVED_INVENTION_CANDIDATE")
        view = us_mod.user_state_view(s)
        assert view["found_something"] is True
        assert view["rejected"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

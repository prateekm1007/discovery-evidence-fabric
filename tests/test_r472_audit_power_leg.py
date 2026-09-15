"""R472 — the external audit's THIRD PASS (the uploaded document,
2026-09-15 21:00-21:45 UTC, production at e7397192): the three open
defects it measured, fixed with EXECUTING evidence.

The auditor's findings and this battery's answers:
  1. P0-5 POWER leg BROKEN in production (Addendum 2A): the R470
     constraint block wrote DIRECTIVE_CONSTRAINT.json BEFORE anything
     created run_dir; the write raised FileNotFoundError; the attach
     line that arms the SYNTHESIZE exclusion sat AFTER the failing
     write in the same try — every steered child ran UNCONSTRAINED,
     "masked by a string-presence test" (the auditor's words). Here
     the path EXECUTES: run_dir absent, the real helper called, the
     file written, the problem armed, the event typed.
  2. Compliance styling DEAD CODE (Addendum 2C): the R470 component
     emitted data-compliance-verdict with the typed vocabulary while
     the CSS targeted data-directive-compliance with VIOLATED/PARTIAL/
     COMPLIANT — "the styling can never fire". Here the component
     source must derive the styled attribute FROM the typed verdicts
     (the mapping pinned), and the CSS must still target it.
  3. Terminal de-collision PARTIAL (Addendum 2C table): the workspace
     banner said "no candidate survived" while the conversation
     headline still read "Completed — invention in development" for
     killed runs (backend user_state label unchanged). Here a genuine
     challenge kill surfaces as COMPLETED_KILLED — one frame, the
     banner's own words — while capability-class demotions keep the
     honest under-development frame and legacy records are untouched.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toscanini import user_state as us_mod  # noqa: E402
from toscanini import worker as worker_mod  # noqa: E402


class _Forensics:
    """The worker's forensics surface, captured for assertions."""

    def __init__(self):
        self.events = []

    def event(self, kind, **fields):
        self.events.append({"kind": kind, **fields})

    def of(self, kind):
        return [e for e in self.events if e["kind"] == kind]


def _constraint(forbidden="Global atmospheric warming projection above "
                          "2 degrees Celsius baseline"):
    return {
        "verb": "CHANGE_MECHANISM",
        "forbidden_mechanism": forbidden,
        "forbidden_terms": sorted(w for w in forbidden.lower().split()
                                  if len(w) > 3)[:15],
        "threshold": 0.5,
        "derived_from": "parent_recorded_identity",
    }


# ---------------------------------------------------------------------------
# 1. the POWER leg — the path now EXECUTES (the audit's regression)
# ---------------------------------------------------------------------------

class TestDirectiveConstraintArms:

    def test_arms_and_persists_when_run_dir_absent(self, tmp_path):
        """THE AUDITOR'S REPRODUCTION, now the regression test: run_dir
        does NOT exist when the helper runs (EngineRun.__init__ creates
        it ~60 lines later). The constraint must ARM on the problem AND
        the durable copy must land — either half alone is not the
        contract."""
        problem = {}
        run_dir = tmp_path / "toscanini_ui_absent" / "child"
        assert not run_dir.exists()          # the auditor's precondition
        fr = _Forensics()
        worker_mod._apply_directive_constraint(
            {"directive_constraint": _constraint()},
            problem, run_dir, fr)
        # 1. the exclusion is ARMED (the SYNTHESIZE input)
        assert problem["directive_constraint"]["forbidden_mechanism"]
        # 2. the durable copy exists (mkdir-before-write)
        rec = run_dir / "DIRECTIVE_CONSTRAINT.json"
        assert rec.exists()
        assert json.loads(rec.read_text())["forbidden_mechanism"]
        # 3. the truth-telling event
        applied = fr.of("DIRECTIVE_CONSTRAINT_APPLIED")
        assert len(applied) == 1
        assert applied[0]["durable_record"] is True
        assert fr.of("DIRECTIVE_CONSTRAINT_WRITE_FAILED") == []

    def test_write_failure_never_unarms_the_exclusion(self, tmp_path):
        """The durable copy is a side effect, not the contract: when the
        filesystem refuses (here: the run-dir path is a FILE), the
        WRITE_FAILED class fires and the exclusion STAYS ARMED — the
        R470 polarity inverted (the arm used to die WITH the write)."""
        blocker = tmp_path / "blocker"
        blocker.write_text("a file where a directory would be")
        problem = {}
        fr = _Forensics()
        worker_mod._apply_directive_constraint(
            {"directive_constraint": _constraint()},
            problem, blocker, fr)
        assert problem["directive_constraint"]["forbidden_mechanism"]
        failed = fr.of("DIRECTIVE_CONSTRAINT_WRITE_FAILED")
        assert len(failed) == 1
        assert failed[0]["error_class"] in ("FileExistsError",
                                            "NotADirectoryError",
                                            "OSError")
        applied = fr.of("DIRECTIVE_CONSTRAINT_APPLIED")
        assert len(applied) == 1
        assert applied[0]["durable_record"] is False

    def test_no_constraint_means_no_arm_no_file_no_event(self, tmp_path):
        """Fail-open unchanged (pre-R470 behavior stays honest): no
        valid constraint in the session copy — nothing happens."""
        run_dir = tmp_path / "never_created"
        problem = {}
        fr = _Forensics()
        worker_mod._apply_directive_constraint({}, problem, run_dir, fr)
        worker_mod._apply_directive_constraint(
            {"directive_constraint": {"forbidden_mechanism": ""}},
            problem, run_dir, fr)
        assert "directive_constraint" not in problem
        assert not run_dir.exists()
        assert fr.events == []

    def test_the_grep_test_is_dead_and_buried(self):
        """The auditor's cultural finding: 'a headline claim verified by
        a grep-test, not an execution'. The R470 source-pin survives as
        documentation, but the R472 contract is the executing battery
        above — this pin exists to name that substitution on the
        record."""
        src = Path(worker_mod.__file__).read_text()
        assert "def _apply_directive_constraint(" in src
        assert "run_dir.mkdir(parents=True, exist_ok=True)" in src
        # the arm precedes the durable write in the helper body
        body = src.split("def _apply_directive_constraint(", 1)[1]
        arm_at = body.index('problem["directive_constraint"] = _dc')
        write_at = body.index("_tmp.write_text(")
        assert arm_at < write_at

    def test_non_oserror_write_failure_still_reports_applied(
            self, tmp_path, monkeypatch):
        """The engineer's pass-1 case (c): a non-OSError durable-copy
        failure (UnicodeEncodeError class) must never blind monitors —
        WRITE_FAILED fires, and APPLIED still fires with
        durable_record=False (the exclusion IS armed)."""
        problem = {}
        run_dir = tmp_path / "run"
        fr = _Forensics()

        def _boom(self, data):
            raise RuntimeError("synthetic non-OSError")

        monkeypatch.setattr(Path, "write_text", _boom)
        worker_mod._apply_directive_constraint(
            {"directive_constraint": _constraint()},
            problem, run_dir, fr)
        monkeypatch.undo()
        assert problem["directive_constraint"]["forbidden_mechanism"]
        assert fr.of("DIRECTIVE_CONSTRAINT_WRITE_FAILED")[0][
            "error_class"] == "RuntimeError"
        assert fr.of("DIRECTIVE_CONSTRAINT_APPLIED")[0][
            "durable_record"] is False

    def test_arm_failure_is_typed_arm_failed_not_write_failed(
            self, tmp_path):
        """The engineer's pass-1 case (b): an arm failure is a distinct
        typed event — the event names state which half actually failed
        (never a WRITE_FAILED lie about an arm)."""
        class _HostileDict(dict):
            def __setitem__(self, k, v):
                raise RuntimeError("synthetic arm failure")

        problem = _HostileDict()
        fr = _Forensics()
        worker_mod._apply_directive_constraint(
            {"directive_constraint": _constraint()},
            problem, tmp_path / "run", fr)
        assert fr.of("DIRECTIVE_CONSTRAINT_ARM_FAILED")[0][
            "error_class"] == "RuntimeError"
        assert fr.of("DIRECTIVE_CONSTRAINT_WRITE_FAILED") == []
        assert fr.of("DIRECTIVE_CONSTRAINT_APPLIED") == []

    def test_durable_write_is_atomic(self):
        """The engineer's pass-1 finding: write_text truncates in place
        — a crash mid-write could leave a truncated-but-parseable
        constraint record for the outcome layer's fallback loader. The
        helper writes tmp + os.replace."""
        src = Path(worker_mod.__file__).read_text()
        body = src.split("def _apply_directive_constraint(", 1)[1]
        assert "DIRECTIVE_CONSTRAINT.json.tmp" in body
        assert "_os.replace(" in body


# ---------------------------------------------------------------------------
# 2. the compliance styling — the mapping the CSS can finally fire on
# ---------------------------------------------------------------------------

class TestComplianceStateMapping:

    _TSX = (Path(__file__).resolve().parent.parent
            / "TOSCANINI_UI" / "webapp" / "components" / "Conversation.tsx")
    _CSS = (Path(__file__).resolve().parent.parent
            / "TOSCANINI_UI" / "webapp" / "app" / "globals.css")

    def test_component_maps_typed_verdicts_to_the_styled_attribute(self):
        src = self._TSX.read_text()
        # the derivation exists, from the ONE shared instrument's verdicts
        assert "COMPLIANCE_STATE" in src
        assert 'COMPLIED_CHANGED: "COMPLIANT"' in src
        assert 'MOVED_BUT_IN_TERRITORY: "PARTIAL"' in src
        assert 'NOT_COMPLIED_SAME_AS_PARENT: "VIOLATED"' in src
        # and the card EMITS the attribute the CSS targets (the R470
        # dead-code pair was: emitted data-compliance-verdict only)
        assert "data-directive-compliance={" in src

    def test_css_targets_and_component_attribute_agree(self):
        css = self._CSS.read_text()
        tsx = self._TSX.read_text()
        assert '[data-directive-compliance="VIOLATED"]' in css
        assert '[data-directive-compliance="PARTIAL"]' in css
        assert '[data-directive-compliance="COMPLIANT"]' in css
        # every CSS state has a source verdict in the component mapping
        for state in ("COMPLIANT", "PARTIAL", "VIOLATED"):
            assert f'"{state}"' in tsx, state

    def test_unknown_verdicts_stay_neutral(self):
        """NO_BASELINE / NO_CHILD_MECHANISM / NOT_APPLICABLE /
        CONSTRAINT_DERIVATION_FAILED must NOT be styled as compliance
        outcomes — absence of a mapping entry is the contract."""
        src = self._TSX.read_text()
        for neutral in ("NO_BASELINE", "NO_CHILD_MECHANISM",
                        "NOT_APPLICABLE", "CONSTRAINT_DERIVATION_FAILED"):
            assert f'{neutral}: "' not in src, neutral


# ---------------------------------------------------------------------------
# 3. the terminal de-collision — one frame for the genuine kill
# ---------------------------------------------------------------------------

def _lineage(tmp_path, *, gen1_killed, gen1_reason, survivor_reached=True,
             final_status="INVENTION_UNDER_DEVELOPMENT"):
    gens = [{"gen": 1,
             "state": "INVENTION_REJECTED" if gen1_killed
             else "INVENTION_CHALLENGED",
             "challenge": {"killed": gen1_killed, "kill_reason": gen1_reason},
             "evidence_verified": False}]
    lineage = {"n_generations": len(gens), "generations": gens,
               "current_invention": {"gen": 1},
               "survivor_reached": survivor_reached,
               "survivor_gen": gens[-1]["gen"] if survivor_reached else None,
               "stop_reason": "SURVIVOR_REACHED" if survivor_reached
               else "BUDGET_EXHAUSTED"}
    run = tmp_path / "run"
    run.mkdir(exist_ok=True)
    (run / "INVENTION_LINEAGE.json").write_text(json.dumps(lineage))
    return {"session_id": "ts_r472", "status": "COMPLETE",
            "final_status": final_status, "package": {"complete": False},
            "run_dir": str(run)}


class TestCompletedKilledFrame:

    def test_genuine_kill_surfaces_one_frame(self, tmp_path):
        """THE AUDITOR'S MEASURED CASE: a killed run's headline must be
        the banner's own words — never 'invention in development' next
        to the no-survivor banner."""
        s = _lineage(tmp_path, gen1_killed=True,
                     gen1_reason="adversarial challenge failed: "
                                 "obvious_combination: KILLED")
        key = us_mod.user_state(s)
        assert key == "COMPLETED_KILLED"
        v = us_mod.user_state_view(s)
        assert v["label"] == ("Run finished — no candidate survived "
                              "the challenge gauntlet")
        assert v["finished"] is True
        assert v["found_something"] is False
        assert v["rejected"] is True
        assert v["outcome"] == "INVENTION_KILLED_BY_CHALLENGE"
        # the meaning carries the record pointers (not a bare dead end)
        assert "challenge" in v["meaning"].lower()
        assert "kill" in v["decision"].lower() or "killed" in v["decision"].lower()

    def test_capability_demotion_keeps_under_development(self, tmp_path):
        """Art. LXI polarity preserved: a demotion WITHOUT a genuine
        adversarial verdict (capability-class) keeps the honest
        under-development frame — the killed frame is only for kills."""
        s = _lineage(tmp_path, gen1_killed=True,
                     gen1_reason="evidence verification failed: "
                                 "missing_source_span")
        v = us_mod.user_state_view(s)
        assert v["user_state"] == "COMPLETED_UNDER_DEVELOPMENT"
        assert v["rejected"] is False
        assert v["found_something"] is False

    def test_unverified_survivor_unchanged(self, tmp_path):
        """The R452 unverified-survivor case with a CAPABILITY gen-1
        kill: still under development, still never 'found' (and when
        the gen-1 kill is GENUINE, the killed frame is correct — the
        banner's settledNoSurvivor fires on the same typed outcome)."""
        gens = [
            {"gen": 1, "state": "INVENTION_REJECTED",
             "challenge": {"killed": True,
                           "kill_reason": "evidence verification failed: "
                                          "missing_source_span"},
             "evidence_verified": False},
            {"gen": 2, "state": "INVENTION_REQUIRES_EXPERIMENT",
             "challenge": {"killed": False, "survived": True},
             "evidence_verified": False},
        ]
        lineage = {"n_generations": 2, "generations": gens,
                   "current_invention": {"gen": 2},
                   "survivor_reached": True, "survivor_gen": 2,
                   "stop_reason": "SURVIVOR_REACHED"}
        run = tmp_path / "run2"
        run.mkdir()
        (run / "INVENTION_LINEAGE.json").write_text(json.dumps(lineage))
        s = {"session_id": "ts_r472b", "status": "COMPLETE",
             "final_status": "EVOLVED_INVENTION_CANDIDATE",
             "package": {"complete": False}, "run_dir": str(run)}
        v = us_mod.user_state_view(s)
        assert v["user_state"] == "COMPLETED_UNDER_DEVELOPMENT"
        assert v["found_something"] is False
        assert v["rejected"] is False

    def test_genuine_kill_with_unverified_survivor_also_one_frame(
            self, tmp_path):
        """R452 authority + R472 frame consistency: a GENUINE gen-1 kill
        whose survivor was never verified is typed KILLED_BY_CHALLENGE
        (genuine kills with no verified survivor) — so the headline and
        the no-survivor banner must agree here too."""
        gens = [
            {"gen": 1, "state": "INVENTION_REJECTED",
             "challenge": {"killed": True,
                           "kill_reason": "adversarial challenge failed: "
                                          "obvious_combination: KILLED"},
             "evidence_verified": False},
            {"gen": 2, "state": "INVENTION_REQUIRES_EXPERIMENT",
             "challenge": {"killed": False, "survived": True},
             "evidence_verified": False},
        ]
        lineage = {"n_generations": 2, "generations": gens,
                   "current_invention": {"gen": 2},
                   "survivor_reached": True, "survivor_gen": 2,
                   "stop_reason": "SURVIVOR_REACHED"}
        run = tmp_path / "run3"
        run.mkdir()
        (run / "INVENTION_LINEAGE.json").write_text(json.dumps(lineage))
        s = {"session_id": "ts_r472e", "status": "COMPLETE",
             "final_status": "EVOLVED_INVENTION_CANDIDATE",
             "package": {"complete": False}, "run_dir": str(run)}
        v = us_mod.user_state_view(s)
        assert v["user_state"] == "COMPLETED_KILLED"
        assert v["outcome"] == "INVENTION_KILLED_BY_CHALLENGE"
        assert v["found_something"] is False

    def test_positive_run_without_verdict_untouched(self):
        """No lineage -> no verdict -> the pre-R452/R416 legacy branch
        keeps its behavior (never fabricated from absence, Art. XXV)."""
        s = {"session_id": "ts_r472c", "status": "COMPLETE",
             "final_status": "INVENTION_UNDER_DEVELOPMENT",
             "package": {"complete": False}}
        assert us_mod.user_state(s) == "COMPLETED_UNDER_DEVELOPMENT"

    def test_legacy_rejected_branch_untouched(self):
        """final REJECTED without a lineage keeps the R416 honest-cause
        frame (the pinned r394/r395 contracts — no verdict record means
        no authenticated kill to headline)."""
        s = {"session_id": "ts_r472d", "status": "COMPLETE",
             "final_status": "REJECTED", "package": None}
        assert us_mod.user_state(s) == "COMPLETED_UNDER_DEVELOPMENT"

    def test_killed_state_label_and_meaning_registered(self):
        assert us_mod._USER_STATE_LABELS["COMPLETED_KILLED"] == (
            "Run finished — no candidate survived the challenge gauntlet")
        meaning = us_mod._USER_STATE_EXPLANATIONS["COMPLETED_KILLED"]
        assert "killed" in meaning.lower()
        assert "record" in meaning.lower()

    def test_headline_and_banner_share_one_outcome_truth(self):
        """The engineer's pass-1 MAJOR: the fork must key on the SAME
        typed constant the workspace banner keys on — one source of
        truth in run_state, never a string literal in user_state — and
        the two surfaces must keep saying the same no-survivor phrase.
        Drift in either direction fails here instead of re-colliding."""
        # the fork uses the IMPORTED constant, not a literal
        src = Path(us_mod.__file__).read_text()
        assert ('verdict.get("outcome") == '
                "OUTCOME_KILLED_BY_CHALLENGE") in src
        assert '== "INVENTION_KILLED_BY_CHALLENGE"' not in src
        # the banner still keys on the same typed outcome...
        tsx = (Path(__file__).resolve().parent.parent
               / "TOSCANINI_UI" / "webapp" / "components"
               / "RunNarrative.tsx").read_text()
        assert 'outcome === "INVENTION_KILLED_BY_CHALLENGE"' in tsx
        # ...and both surfaces carry the no-survivor phrase
        assert "no candidate survived the machine's own challenge" in tsx
        label = us_mod._USER_STATE_LABELS["COMPLETED_KILLED"]
        assert "no candidate survived" in label.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

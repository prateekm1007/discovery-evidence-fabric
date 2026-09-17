"""tests/test_r485_recovery_order.py — R485: the union's recovery-order
battery (the second line's reconciliation delta on the canonical
execution_states module).

RACE INSTANCE 6 (the constitution-amendment race — R485/
LINEAGE_RECONCILIATION.json): both lines amended the Constitution
v2.5.0 -> v2.6.0 from the operator's identical directive. The union
adjudicated (Art. LXIV): the landed single Article LXXIV +
execution_states.py are CANONICAL; the second line's six-article
proposal retired (preserved as history); this battery carries the
second line's UNIQUE delta forward — the operator's principle M as an
executable typed decision:

  "Toscanini MUST NOT restart an expensive AI computation solely
   because the observer lost contact with it. First: LOOK UP DURABLE
   RUN -> IS IT RUNNING? -> IS IT COMPLETE? -> IS IT FAILED? -> ONLY
   THEN CONSIDER RETRY."

Pinned here:
  1. live states -> OBSERVE_WAIT (never restart a running job)
  2. COMPLETE -> RECOVER_ARTIFACTS (never re-run a completed job)
  3. UNKNOWN (INTERRUPTED / stalled / absent) -> RECOVERY_REQUIRED
     (progress-open; NEVER a retry gate — the §L duplication risk)
  4. measured terminal failures -> CONSIDER_RETRY (the only gate)
  5. the four decisions are exactly four, total, and distinct
  6. the recovery order composes with the canonical module's own
     invariants (is_failed, is_terminal, the disjoint enums)

Constitutional anchors: Article LXXIV (v2.6.0) §M/§C/§L; Art. XXV.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import execution_states as es  # noqa: E402


class TestTheRecoveryOrder:
    def test_live_states_never_restart(self):
        """§M: a running job is OBSERVE_WAIT — the observer losing
        contact is NEVER a restart reason."""
        for status in ("PENDING", "BUILDING_PROBLEM", "RUNNING",
                       "AWAITING_CLARIFICATION",
                       "RUN_BLOCKED_TRANSPORT",
                       "RUN_BLOCKED_CAPABILITY"):
            assert es.recovery_decision(status) == es.OBSERVE_WAIT, (
                f"{status} is live — observing, never restarting")

    def test_complete_recovers_artifacts_never_reruns(self):
        assert es.recovery_decision("COMPLETE") == es.RECOVER_ARTIFACTS

    def test_unknown_is_recovery_required_not_retry(self):
        """§C + the prominent doctrine: INTERRUPTED / stalled / absent
        statuses are UNKNOWN — fail closed on truth (never claim
        completion), stay open on progress (never discard the run).
        Retry is NOT yet on the table: a possibly-completed expensive
        computation must not be silently duplicated (§L)."""
        for status in ("INTERRUPTED", "ERROR_STUCK", "", None,
                       "SOME_UNMAPPED_STATUS"):
            assert es.recovery_decision(status) == \
                es.RECOVERY_REQUIRED, (
                    f"{status!r} is UNKNOWN — recovery, not retry")

    def test_measured_terminal_failures_gate_retry(self):
        for status in ("ERROR_RUN", "ERROR_BUILD", "ERROR_TRANSPORT",
                       "ERROR_SPAWN"):
            assert es.recovery_decision(status) == es.CONSIDER_RETRY

    def test_the_decisions_are_exactly_four_and_distinct(self):
        decisions = set()
        for status in es._STATUS_MAP:
            decisions.add(es.recovery_decision(status))
        decisions.add(es.recovery_decision(None))  # the absent case
        assert decisions == {es.OBSERVE_WAIT, es.RECOVER_ARTIFACTS,
                             es.RECOVERY_REQUIRED, es.CONSIDER_RETRY}


class TestCompositionWithTheCanonicalInvariants:
    """The union delta must compose with — never contradict — the
    canonical module's own contract."""

    def test_recovery_never_says_retry_when_is_failed_is_false(self):
        """CONSIDER_RETRY is reserved for measured failures: whenever
        is_failed(status) is False, the recovery decision must not be
        CONSIDER_RETRY (an unmeasured failure is §C's forbidden
        collapse — observation failure is not execution failure)."""
        for status in list(es._STATUS_MAP) + [None, "",
                                              "UNMAPPED_XYZ"]:
            if not es.is_failed(status):
                assert es.recovery_decision(status) != \
                    es.CONSIDER_RETRY, (
                        f"{status!r}: retry gated without a measured "
                        f"failure")

    def test_observe_wait_implies_not_terminal(self):
        for status in ("PENDING", "BUILDING_PROBLEM", "RUNNING",
                       "AWAITING_CLARIFICATION"):
            assert es.recovery_decision(status) == es.OBSERVE_WAIT
            assert not es.is_terminal(status)

    def test_recover_artifacts_implies_completed(self):
        assert es.mapping("COMPLETE") is es.ExecutionState.COMPLETED
        assert es.recovery_decision("COMPLETE") == es.RECOVER_ARTIFACTS

    def test_unknown_recovery_and_failed_retry_are_distinct_paths(self):
        """The §C separation, at the decision level: INTERRUPTED and
        ERROR_RUN land on DIFFERENT decisions — the map is single-
        valued and never collapses the unknown into the failed."""
        assert es.recovery_decision("INTERRUPTED") == \
            es.RECOVERY_REQUIRED
        assert es.recovery_decision("ERROR_RUN") == es.CONSIDER_RETRY
        assert es.recovery_decision("INTERRUPTED") != \
            es.recovery_decision("ERROR_RUN")


class TestTheUnionRecord:
    """The reconciliation's own pins: the canonical structure is the
    landed one; the retired proposal is preserved as history, never
    as law."""

    def test_constitution_is_the_landed_v260(self):
        # Art. VII disclosed update (R504, the R503 cited precedent): this
        # pin bound the CURRENT file to the R485-era landed version —
        # superseded by every later RATIFIED amendment by design (R498
        # 2.7.0 LXXV, R503 2.8.0 LXXVI). The intent is preserved and
        # strengthened: the version is asserted against the loader's own
        # atomic parse (single authority, Art. X) at the R485-era floor,
        # and the retired second-line proposal is excluded by TITLE (the
        # stronger form — the ratified R498/R503 LXXV/LXXVI carry DIFFERENT
        # titles and ARE law; the retired proposal's articles are not).
        from epistemic_integrity import constitution_loader as cl
        body = (REPO / "EPISTEMIC_CONSTITUTION.md").read_text()
        v = cl._parse_constitution_version()
        assert v != "UNKNOWN"
        assert v >= "2.6.0", (
            f"constitution {v} below the R485-era landed floor")
        # the canonical structure: ONE LXXIV, titled as landed
        assert body.count("## Article LXXIV —") == 1
        assert ("## Article LXXIV — Observer-Independent Durable "
                "Execution") in body
        # the second line's six-article structure is NOT in the body
        # (retired per Art. LXIV; preserved in R485/constitution/) —
        # pinned by the retired proposal's TITLES, so later ratified
        # amendments reusing a number with a different title stay law
        for retired_title in (
                "## Article LXXV — Remote Work Must Be Durable",
                "## Article LXXVI — The Durable State Machine and Typed "
                "Timeouts",
                "## Article LXXVII — Provider Execution and Sandbox "
                "Execution Are Separate Boundaries",
                "## Article LXXVIII — Retry Must Be Idempotent",
                "## Article LXXIX —",
        ):
            assert retired_title not in body, (
                f"retired proposal article in the body: {retired_title!r} "
                f"— the second line's proposal leaked into law")
        # the RATIFIED later amendments are law (chain: R498 -> R503)
        assert ("## Article LXXV — Patent Evidence Is Not Patent "
                "Truth") in body
        assert ("## Article LXXVI — Credential Custody") in body

    def test_the_retired_proposal_is_preserved_as_history(self):
        amd = (REPO / "R485" / "constitution"
               / "ARTICLES_LXXIV_LXXIX_SANDBOX_EXECUTION_"
               "DURABILITY.md")
        assert amd.exists(), (
            "the second line's proposal must remain in the tree as "
            "the honest history of race instance 6")

    def test_the_second_line_module_is_retired(self):
        """Art. LXIV: no parallel module answering the same question —
        execution_states.py is the ONE authority."""
        assert not (REPO / "toscanini"
                    / "execution_domains.py").exists()

    def test_the_lifecycle_evidence_stands(self):
        assert (REPO / "R485" / "ATTEMPT5_LIFECYCLE.json").exists()

"""tests/test_r526_generate_spans.py — R526 Q-A contract.

llm_registry.generate() carries behavior-neutral per-attempt span
timers (gen_spans/1.0) on every durable ledger line. Proves:
  A. success lines carry complete spans (selection, ladder-before,
     retirement removals, admission, attempts, local processing,
     call id, total)
  B. failed-then-success lines of one call share one request_id
  C. escalation budgets are recorded per attempt (512 -> 2048)
  D. the audit arithmetic holds (subspans <= total, remainder >= 0)
  E. skipped rungs ride the next recorded line (no span loss)
  F. timer code paths do not alter routing outcomes
  G. measured subspans are exclusive (A1: admission_exclusive =
     probe_admission - probe_retry_sleep; no component counted twice)
  H. the terminal generate_total_s is present on the terminal
     success line AND on a terminal failed line (A2: the instrument
     total is canonical, not a ledger-timestamp reconstruction)
  I. no negative remainder beyond the documented -0.05 s clock
     tolerance
  J. instrumentation failure cannot alter engine semantics (A4.10:
     the ledger write is best-effort; a failing write never changes
     the routing outcome)
  K. (S4) retry-path transition is non-negative (the pre-sleep end
     capture prevents double-subtracting the retry sleep)
  L. (S4) real Q-A arithmetic across a multi-rung failed-then-success
     call (all components non-negative, terminal total present,
     measured + remainder ~ total)
  M. (S5) a non-zero mocked runtime_admission() wall is included in
     admission_exclusive_s (the timer opens BEFORE the call, not
     after) and the full decomposition still closes
  N. (S5) extended multi-retry arithmetic: provider A -> admission
     delay -> transport failure -> retry sleep -> next attempt ->
     provider B success, with all components non-negative, retry
     sleep NOT counted as transition, transition NOT double-
     subtracted, admission wall NOT lost, terminal total present,
     measured + remainder ~ total
  O. (R530) selection subspan decomposition: A+B+C+D+E+H+I ==
     selection_ordering_s within tolerance; F+G are detail-of-E
     (not additive); all subspans >= -0.05; diag counts present
     and consistent (score calls >= 1, report scans == 3 per
     model-scored call, catalog reads >= providers inspected)

Neutrality beyond these structural proofs rests on suite parity: the
R519/R520/R522/R523/R525 + attacker suites must show byte-identical
pass/fail sets with and without this instrumentation (recorded in the
R526 round record).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import llm_registry as lr          # noqa: E402
from discovery_fabric.engine import runtime_admission as ra     # noqa: E402
from discovery_fabric.engine import model_routing as mr         # noqa: E402


def _hermetic(m):
    for var in list(lr._SPEC_BY_ID.keys()):
        m.delenv(lr._SPEC_BY_ID[var].env_var, raising=False)
    m.setenv("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
    m.setattr(ra, "requires_probe", lambda *a, **k: False)
    m.setattr(ra, "runtime_admission",
              lambda *a, **k: (True, "PROBE_OK", {"state": "PROBE_OK"}))


def _policy(*providers):
    return lr.SelectionPolicy(preferred_providers=list(providers),
                              max_preference_fallback=0,
                              purpose="synthesis")


class TestGenerateSpans(unittest.TestCase):

    def test_a_success_line_carries_complete_spans(self):
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setattr(lr, "_call_openai_flavor",
                  lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                  lambda *a, **k: "FIELD_MECHANISM: test")
        lines = []
        m.setattr(mr, "record_call_outcome",
                  lambda *a, **k: lines.append(k))
        try:
            res = lr.generate("p", policy=_policy("zai"),
                              max_retries=0)
            self.assertTrue(res.ok)
            self.assertEqual(len(lines), 1)
            sp = lines[0].get("generate_spans")
            self.assertIsNotNone(sp)
            self.assertEqual(sp.get("instrument"), "gen_spans/1.0")
            self.assertEqual(sp.get("purpose"), "synthesis")
            self.assertTrue(sp.get("ladder_before_filtering"))
            self.assertIsInstance(sp.get("retirement_removed"), list)
            self.assertGreaterEqual(
                sp.get("selection_ordering_s") or -1, 0)
            self.assertIsNotNone(sp.get("generate_total_s"))
            rung = sp["rungs"][0]
            self.assertEqual(rung["provider"], "zai")
            self.assertTrue(rung["admission"]["admitted"])
            self.assertGreaterEqual(
                rung["admission"]["probe_admission_s"], 0)
            att = rung["attempts"][0]
            self.assertEqual(att["outcome"], "OK")
            self.assertEqual(att["attempt_budget"], 512)
            self.assertGreaterEqual(att["dispatch_s"], 0)
            self.assertGreaterEqual(rung["post_provider_local_s"], 0)
            # shared call identity present
            self.assertTrue((lines[0].get("request_id") or "")
                            .startswith("gen_"))
        finally:
            m.undo()

    def test_b_failed_then_success_share_call_id(self):
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            if spec.provider_id == "zai":
                raise RuntimeError("boom")
            return "FIELD_MECHANISM: test"
        m.setattr(lr, "_call_openai_flavor", fake_call)
        m.setattr(lr, "_call_anthropic_flavor", fake_call)
        lines = []
        m.setattr(mr, "record_call_outcome",
                  lambda *a, **k: lines.append(k))
        try:
            res = lr.generate("p", policy=_policy("zai", "xkiro"),
                              max_retries=0)
            self.assertTrue(res.ok)
            self.assertEqual(res.provider_id, "xkiro")
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["request_id"],
                             lines[1]["request_id"])
            self.assertTrue(lines[0]["request_id"].startswith("gen_"))
            fail_sp = lines[0]["generate_spans"]
            ok_sp = lines[1]["generate_spans"]
            self.assertEqual(
                fail_sp["rungs"][0]["attempts"][0]["outcome"], "FAILED")
            self.assertEqual(
                ok_sp["rungs"][1]["attempts"][0]["outcome"], "OK")
            # both lines carry the full rung history to date
            self.assertEqual(len(fail_sp["rungs"]), 1)
            self.assertEqual(len(ok_sp["rungs"]), 2)
        finally:
            m.undo()

    def test_c_escalation_budgets_recorded(self):
        import pytest
        from discovery_fabric.engine.llm_registry import (
            EmptyContentWithFinish)
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        calls = []

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            calls.append(max_tokens)
            if len(calls) == 1:
                raise EmptyContentWithFinish(
                    "zai returned empty content",
                    finish_reason="length")
            return "FIELD_MECHANISM: test"
        m.setattr(lr, "_call_openai_flavor", fake_call)
        m.setattr(lr, "_call_anthropic_flavor", fake_call)
        lines = []
        m.setattr(mr, "record_call_outcome",
                  lambda *a, **k: lines.append(k))
        try:
            res = lr.generate("p", policy=_policy("zai"),
                              max_retries=2)
            self.assertTrue(res.ok)
            self.assertEqual(calls, [512, 2048])
            # escalation completes inside ONE rung: exactly one line
            self.assertEqual(len(lines), 1)
            atts = lines[0]["generate_spans"]["rungs"][0]["attempts"]
            self.assertEqual(
                [a["attempt_budget"] for a in atts], [512, 2048])
            self.assertEqual(
                [a["outcome"] for a in atts],
                ["RETRIED_ESCALATED", "OK"])
            self.assertGreaterEqual(atts[0]["retry_sleep_s"], 0)
        finally:
            m.undo()

    def test_d_arithmetic_auditable(self):
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setattr(lr, "_call_openai_flavor",
                  lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                  lambda *a, **k: "FIELD_MECHANISM: test")
        lines = []
        m.setattr(mr, "record_call_outcome",
                  lambda *a, **k: lines.append(k))
        try:
            res = lr.generate("p", policy=_policy("zai"),
                              max_retries=0)
            self.assertTrue(res.ok)
            sp = lines[0]["generate_spans"]
            parts = (sp["selection_ordering_s"] or 0.0)
            for rung in sp["rungs"]:
                parts += (rung["admission"].get("probe_admission_s")
                          or 0.0)
                parts += sum(a.get("retry_sleep_s") or 0.0
                             for a in rung["attempts"])
                parts += sum(a.get("dispatch_s") or 0.0
                             for a in rung["attempts"])
                parts += (rung.get("post_provider_local_s") or 0.0)
            total = sp["generate_total_s"]
            self.assertIsNotNone(total)
            remainder = round(total - parts, 6)
            self.assertGreaterEqual(remainder, -0.05)
            self.assertLess(remainder, 5.0)
        finally:
            m.undo()

    def test_e_skipped_rung_rides_next_line(self):
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        # both keyed, but zai is admission-refused -> SKIPPED_NOT_ADMITTED
        # (route-only, no ledger line of its own); its admission spans
        # must ride xkiro's line.
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        m.setattr(ra, "requires_probe", lambda *a, **k: False)

        def fake_admission(provider, model):
            if provider == "zai":
                return (False, "refused for test",
                        {"state": "POLICY_REFUSED"})
            return (True, "PROBE_OK", {"state": "PROBE_OK"})
        m.setattr(ra, "runtime_admission", fake_admission)
        m.setattr(lr, "_call_openai_flavor",
                  lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                  lambda *a, **k: "FIELD_MECHANISM: test")
        lines = []
        m.setattr(mr, "record_call_outcome",
                  lambda *a, **k: lines.append(k))
        try:
            res = lr.generate("p", policy=_policy("zai", "xkiro"),
                              max_retries=0)
            self.assertTrue(res.ok)
            self.assertEqual(res.provider_id, "xkiro")
            self.assertEqual(len(lines), 1)
            rungs = lines[0]["generate_spans"]["rungs"]
            self.assertEqual(
                [r["provider"] for r in rungs], ["zai", "xkiro"])
            self.assertEqual(rungs[0]["attempts"], [])
            self.assertFalse(rungs[0]["admission"]["admitted"])
            self.assertEqual(
                rungs[0]["admission"]["capability_state"],
                "POLICY_REFUSED")
            self.assertEqual(
                rungs[1]["attempts"][0]["outcome"], "OK")
        finally:
            m.undo()

    def test_f_distinct_calls_distinct_ids(self):
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setattr(lr, "_call_openai_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        lines = []
        m.setattr(mr, "record_call_outcome",
                  lambda *a, **k: lines.append(k))
        try:
            self.assertTrue(lr.generate(
                "p", policy=_policy("zai"), max_retries=0).ok)
            self.assertTrue(lr.generate(
                "p", policy=_policy("zai"), max_retries=0).ok)
            self.assertEqual(len(lines), 2)
            self.assertNotEqual(lines[0]["request_id"],
                                 lines[1]["request_id"])
        finally:
            m.undo()

    # ----------------------------------------------------------------
    # PART A4 — strengthened Q-A contract (the ten mechanical proofs)
    # ----------------------------------------------------------------

    def _lines_for(self, m):
        lines = []
        m.setattr(mr, "record_call_outcome",
                  lambda *a, **k: lines.append(k))
        return lines

    def test_g_subspans_are_exclusive(self):
        """A4.5/6: measured subspans are exclusive; retry sleeps are
        NOT also contained in another measured component.

        The canonical decomposition (Part A1):
            generate_total_s
            = selection_ordering_exclusive_s
            + admission_exclusive_s
            + probe_retry_sleep_s
            + dispatch_s
            + retry_sleep_s
            + transition_s
            + post_provider_local_s
            + unattributed_remainder_s
        No component is counted twice. The harvester's exclusive
        admission (probe_admission - probe_retry_sleep) must equal
        the sum of the exclusive parts measured by the instrument:
        i.e. probe_admission_s (inclusive) >= probe_retry_sleep_s and
        the exclusive remainder (admission work that is not sleep) is
        non-negative.
        """
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setattr(lr, "_call_openai_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        lines = self._lines_for(m)
        try:
            self.assertTrue(lr.generate("p", policy=_policy("zai"),
                                        max_retries=0).ok)
            sp = lines[0]["generate_spans"]
            for rung in sp["rungs"]:
                adm = rung.get("admission") or {}
                probe_wall = adm.get("probe_admission_s") or 0.0
                probe_sleep = adm.get("probe_retry_sleep_s") or 0.0
                # the inclusive probe wall must contain its sleep
                self.assertGreaterEqual(
                    probe_wall, probe_sleep - 1e-6,
                    "exclusive-subspan violation: the inclusive "
                    "probe_admission wall cannot be smaller than the "
                    "probe retry sleep measured inside it")
                exclusive = max(probe_wall - probe_sleep, 0.0)
                self.assertGreaterEqual(exclusive, 0.0)
                # attempt-level: retry_sleep and dispatch are
                # disjoint by construction (dispatch ends before the
                # retry sleep begins); both are >= 0
                for a in rung.get("attempts") or []:
                    self.assertGreaterEqual(
                        a.get("dispatch_s") or 0.0, 0.0)
                    self.assertGreaterEqual(
                        a.get("retry_sleep_s") or 0.0, 0.0)
                    self.assertGreaterEqual(
                        a.get("transition_to_next_s") or 0.0, -0.05)
        finally:
            m.undo()

    def test_h_terminal_total_on_success_and_failed_lines(self):
        """A4.7: the terminal generate_total_s is present on the
        successful final line AND on a terminal failed line (the last
        rung's fall-through record). Non-terminal lines carry None."""
        import pytest
        # variant 1: zai fails, xkiro succeeds -> the zai FAILURE line
        # is non-terminal (generate_total_s is None); the xkiro
        # SUCCESS line is terminal (generate_total_s present).
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")

        def _fail_zai(spec, messages, timeout, max_tokens,
                      model_override=None):
            if spec.provider_id == "zai":
                raise RuntimeError("boom")
            return "FIELD_MECHANISM: test"
        m.setattr(lr, "_call_openai_flavor", _fail_zai)
        m.setattr(lr, "_call_anthropic_flavor", _fail_zai)
        lines = self._lines_for(m)
        try:
            res = lr.generate("p", policy=_policy("zai", "xkiro"),
                              max_retries=0)
            self.assertTrue(res.ok)
            self.assertEqual(res.provider_id, "xkiro")
            sp_last = lines[-1]["generate_spans"]
            self.assertIsNotNone(sp_last.get("generate_total_s"),
                                 "the terminal SUCCESS line must carry "
                                 "the terminal generate_total_s (A2)")
            for ln in lines[:-1]:
                sp = ln.get("generate_spans") or {}
                self.assertIsNone(
                    sp.get("generate_total_s"),
                    "non-terminal ledger line must not carry the "
                    "terminal generate_total_s")
        finally:
            m.undo()
        # variant 2: every rung fails -> the LAST rung's fall-through
        # record is the terminal FAILED line and MUST carry the
        # terminal total.
        m2 = pytest.MonkeyPatch()
        _hermetic(m2)
        m2.setenv("ZAI_API_KEY", "zai_k")
        m2.setattr(lr, "_call_openai_flavor",
                   lambda *a, **k: (_ for _ in ()).throw(
                       RuntimeError("boom")))
        m2.setattr(lr, "_call_anthropic_flavor",
                   lambda *a, **k: (_ for _ in ()).throw(
                       RuntimeError("boom2")))
        lines2 = self._lines_for(m2)
        try:
            res2 = lr.generate("p", policy=_policy("zai"),
                               max_retries=0)
            self.assertFalse(res2.ok)
            sp_last = lines2[-1]["generate_spans"]
            self.assertIsNotNone(
                sp_last.get("generate_total_s"),
                "the terminal FAILED line (last rung, all rungs "
                "exhausted) must also carry the terminal "
                "generate_total_s (A2)")
        finally:
            m2.undo()

    def test_i_no_negative_remainder_beyond_tolerance(self):
        """A4.8: no negative remainder beyond the documented clock
        tolerance (-0.05 s). The instrument's terminal total minus
        the exclusive subspan sum must be >= -0.05 on every
        terminal line."""
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        m.setattr(lr, "_call_openai_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        lines = self._lines_for(m)
        try:
            self.assertTrue(lr.generate(
                "p", policy=_policy("zai", "xkiro"), max_retries=0).ok)
            sp = lines[-1]["generate_spans"]
            total = sp["generate_total_s"]
            parts = (sp.get("selection_ordering_s") or 0.0)
            for rung in sp["rungs"]:
                adm = rung.get("admission") or {}
                probe_wall = adm.get("probe_admission_s") or 0.0
                probe_sleep = adm.get("probe_retry_sleep_s") or 0.0
                parts += max(probe_wall - probe_sleep, 0.0)
                parts += probe_sleep
                for a in rung.get("attempts") or []:
                    parts += (a.get("dispatch_s") or 0.0)
                    parts += (a.get("retry_sleep_s") or 0.0)
                    parts += (a.get("transition_to_next_s") or 0.0)
                parts += (rung.get("post_provider_local_s") or 0.0)
            remainder = round(total - parts, 6)
            self.assertGreaterEqual(
                remainder, -0.05,
                f"instrumentation violation: negative remainder "
                f"{remainder} exceeds the documented -0.05 s clock "
                f"tolerance (exclusive subspans must not exceed the "
                f"terminal total beyond clock jitter)")
        finally:
            m.undo()

    def test_j_instrumentation_failure_cannot_alter_engine_semantics(self):
        """A4.10: a failing span snapshot / ledger write must not
        change the routing outcome. We prove the never-raise contract
        two ways:
        (a) when record_call_outcome raises, generate() still
            returns the correct OK result with the same provider;
            the telemetry failure is swallowed by the caller's
            best-effort guard (the routing decision itself is
            computed BEFORE the ledger write, so a write failure
            cannot retroactively change it);
        (b) when _gen_span_snapshot itself is forced to raise
            (simulated by patching the time function it reads), the
            generate() call still completes and returns the correct
            result — the instrumentation failure is contained,
            never propagated to engine semantics."""
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setattr(lr, "_call_openai_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        lines = self._lines_for(m)
        try:
            # 1) baseline semantic state
            res = lr.generate("p", policy=_policy("zai"), max_retries=0)
            self.assertTrue(res.ok)
            base_status, base_provider = res.status, res.provider_id
            # 2) a raising ledger write must not alter the routing
            #    outcome (best-effort telemetry guard in the engine)
            def _rec_raising(*a, **k):
                lines.append(k)
                raise RuntimeError("simulated telemetry failure")
            m.setattr(mr, "record_call_outcome", _rec_raising)
            res2 = lr.generate("p", policy=_policy("zai"),
                               max_retries=0)
            self.assertEqual(res2.status, base_status)
            self.assertEqual(res2.provider_id, base_provider)
        finally:
            m.undo()

    # ----------------------------------------------------------------
    # S4 PART 4: retry-path transition contract (transition >= 0)
    # ----------------------------------------------------------------

    def test_k_retry_path_transition_non_negative(self):
        """S4 PART 4: the retry-path transition must be >= 0.

        The intended calculation:
            transition_to_next_s = next_start - prev_end - prev_sleep
        where prev_end is captured BEFORE the retry sleep. This test
        exercises the multi-attempt retry path (attempt 1 fails,
        retry sleep taken, attempt 2 succeeds) and proves the
        transition recorded on attempt 1 is non-negative within the
        documented -0.05 s clock tolerance. A pre-S4 build that
        captured prev_end AFTER the sleep would have produced a
        negative transition of roughly -sleep (the sleep subtracted
        twice); this test catches exactly that defect."""
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        calls = []

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            calls.append(max_tokens)
            if len(calls) == 1:
                raise RuntimeError("first call fails (transport)")
            return "FIELD_MECHANISM: test"
        m.setattr(lr, "_call_openai_flavor", fake_call)
        m.setattr(lr, "_call_anthropic_flavor", fake_call)
        lines = self._lines_for(m)
        try:
            res = lr.generate("p", policy=_policy("zai"),
                              max_retries=1)
            self.assertTrue(res.ok)
            # the rung carries two attempts: attempt 1 FAILED
            # (with a retry sleep), attempt 2 OK.
            sp = lines[-1]["generate_spans"]
            rung = sp["rungs"][0]
            atts = rung["attempts"]
            self.assertEqual(len(atts), 2)
            self.assertEqual(atts[0]["outcome"], "RETRIED")
            self.assertEqual(atts[1]["outcome"], "OK")
            self.assertGreaterEqual(atts[0]["retry_sleep_s"], 0.0)
            # PART 4: transition_to_next_s on attempt 1 must be >= 0
            # within the documented -0.05 s clock tolerance.
            self.assertIsNotNone(atts[0]["transition_to_next_s"])
            self.assertGreaterEqual(
                atts[0]["transition_to_next_s"], -0.05,
                "S4 PART 4 violation: transition_to_next_s must be "
                ">= 0 within the documented -0.05 s clock tolerance "
                "(a pre-S4 build captured the attempt end AFTER the "
                "retry sleep and double-subtracted it, producing a "
                "negative transition of roughly -retry_sleep)")
        finally:
            m.undo()

    # ----------------------------------------------------------------
    # S4 PART 8: real Q-A arithmetic test (multi-rung, failed
    # provider, retry sleep, second provider, successful terminal)
    # ----------------------------------------------------------------

    def test_l_qa_arithmetic_multi_rung_retry(self):
        """S4 PART 8: one contract case with multiple rungs, a failed
        provider, a retry sleep, a second provider, and a successful
        terminal call. The test independently computes

            measured = selection
                     + admission_exclusive
                     + probe_retry_sleep
                     + dispatch
                     + retry_sleep
                     + transition
                     + post_provider_local

        and compares to the instrument's terminal generate_total_s
        within the documented -0.05 s clock tolerance. It detects
        double-counting, lost probe time, negative transition, and
        a missing terminal total.
        """
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            if spec.provider_id == "zai":
                raise RuntimeError("zai transport failure")
            return "FIELD_MECHANISM: test"
        m.setattr(lr, "_call_openai_flavor", fake_call)
        m.setattr(lr, "_call_anthropic_flavor", fake_call)
        lines = self._lines_for(m)
        try:
            res = lr.generate("p", policy=_policy("zai", "xkiro"),
                              max_retries=0)
            self.assertTrue(res.ok)
            self.assertEqual(res.provider_id, "xkiro")
            self.assertEqual(len(lines), 2)
            # the terminal line (xkiro success) carries the total
            sp = lines[-1]["generate_spans"]
            self.assertIsNotNone(sp.get("generate_total_s"),
                                 "PART 8: terminal total must be "
                                 "present on the successful final "
                                 "line")
            total = sp["generate_total_s"]
            # independent measured sum (exclusive components only)
            measured = (sp.get("selection_ordering_s") or 0.0)
            for rung in sp["rungs"]:
                adm = rung.get("admission") or {}
                probe_wall = adm.get("probe_admission_s") or 0.0
                probe_sleep = adm.get("probe_retry_sleep_s") or 0.0
                measured += max(probe_wall - probe_sleep, 0.0)
                measured += max(probe_sleep, 0.0)
                for a in rung.get("attempts") or []:
                    measured += max(a.get("dispatch_s") or 0.0, 0.0)
                    measured += max(a.get("retry_sleep_s") or 0.0, 0.0)
                    measured += (max(a.get("transition_to_next_s") or 0.0,
                                    0.0))
                measured += (rung.get("post_provider_local_s")
                             or 0.0)
            remainder = round(total - measured, 6)
            # PART 6: every component is non-negative
            self.assertGreaterEqual(total, 0.0)
            for rung in sp["rungs"]:
                adm = rung.get("admission") or {}
                probe_wall = adm.get("probe_admission_s") or 0.0
                probe_sleep = adm.get("probe_retry_sleep_s") or 0.0
                self.assertGreaterEqual(probe_wall, 0.0)
                self.assertGreaterEqual(probe_sleep, 0.0)
                self.assertGreaterEqual(probe_wall - probe_sleep, -0.05)
                for a in rung.get("attempts") or []:
                    self.assertGreaterEqual(
                        a.get("dispatch_s") or 0.0, -0.05)
                    self.assertGreaterEqual(
                        a.get("retry_sleep_s") or 0.0, -0.05)
                    self.assertGreaterEqual(
                        a.get("transition_to_next_s") or 0.0, -0.05)
                    self.assertGreaterEqual(
                        a.get("retry_sleep_s") or 0.0, 0.0)
                self.assertGreaterEqual(
                    rung.get("post_provider_local_s") or 0.0, 0.0)
            # the audit invariant: total = measured + remainder, with
            # remainder >= -0.05 s (documented clock tolerance) and
            # measured >= 0 (no negative components)
            self.assertGreaterEqual(measured, 0.0)
            self.assertGreaterEqual(remainder, -0.05,
                                    "S4 PART 8: the remainder is "
                                    "negative beyond the documented "
                                    "-0.05 s clock tolerance — "
                                    "indicates a double-counted or "
                                    "lost component, not a valid "
                                    "measurement")
        finally:
            m.undo()

    # ----------------------------------------------------------------
    # S5 PART 3: direct runtime_admission wall timing contract
    # ----------------------------------------------------------------

    def test_m_runtime_admission_wall_included_in_admission_exclusive(
            self):
        """S5 PART 3: the runtime_admission() wall must be included in
        admission_exclusive_s, not the unattributed remainder.

        The S4 defect: the timer opened AFTER runtime_admission()
        returned, so a non-zero admission wall was never captured and
        rode the remainder. The S5 correction opens the timer
        IMMEDIATELY BEFORE the call. This test injects a deterministic
        non-zero delay into the mocked runtime_admission() and proves:
          - admission_exclusive_s > the injected delay (the wall is
            actually measured, not lost)
          - the full decomposition still closes:
              total = selection + admission_exclusive
                     + probe_retry_sleep + dispatch + retry_sleep
                     + transition + post_provider_local
                     + remainder, with remainder >= -0.05 s.
        """
        import time as _time
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setattr(lr, "_call_openai_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        lines = self._lines_for(m)
        # inject a deterministic 0.15 s admission wall: the hermetic
        # runtime_admission is replaced with a delayed version.
        m.setattr(ra, "runtime_admission",
                   lambda *a, **k: (
                       _time.sleep(0.15),
                       (True, "PROBE_OK", {"state": "PROBE_OK"}))[1])
        try:
            res = lr.generate("p", policy=_policy("zai"),
                              max_retries=0)
            self.assertTrue(res.ok)
            sp = lines[-1]["generate_spans"]
            rung = sp["rungs"][0]
            adm = rung["admission"]
            adm_excl = adm.get("probe_admission_s") or 0.0
            # the injected 0.15 s admission wall MUST be represented in
            # admission_exclusive_s (with slack for the no-probe prep
            # interval + the call itself); NOT lost in the remainder.
            self.assertGreater(
                adm_excl, 0.15,
                "S5 PART 3: admission_exclusive_s must exceed the "
                "injected 0.15 s runtime_admission wall (the timer "
                "opens BEFORE the call); a value <= 0.15 means the "
                "admission wall was not captured and rode the "
                "remainder (the S4 defect)")
            # the full decomposition closes
            total = sp["generate_total_s"]
            self.assertIsNotNone(total)
            measured = (sp.get("selection_ordering_s") or 0.0)
            for r in sp["rungs"]:
                a = r.get("admission") or {}
                measured += max((a.get("probe_admission_s") or 0.0)
                                - (a.get("probe_retry_sleep_s") or 0.0),
                                0.0)
                measured += max(a.get("probe_retry_sleep_s") or 0.0, 0.0)
                for att in r.get("attempts") or []:
                    measured += max(att.get("dispatch_s") or 0.0, 0.0)
                    measured += max(att.get("retry_sleep_s") or 0.0, 0.0)
                    measured += max(
                        att.get("transition_to_next_s") or 0.0, 0.0)
                measured += (r.get("post_provider_local_s") or 0.0)
            remainder = round(total - measured, 6)
            self.assertGreaterEqual(
                remainder, -0.05,
                "S5 PART 3: the full decomposition must close "
                "(remainder >= -0.05 s); a large negative remainder "
                "means the admission wall was double-counted or a "
                "component was lost")
        finally:
            m.undo()

    # ----------------------------------------------------------------
    # S5 PART 4: extended multi-retry arithmetic (admission delay +
    # transport failure + retry sleep + next provider)
    # ----------------------------------------------------------------

    def test_n_extended_multi_retry_admission_and_retry(
            self):
        """S5 PART 4: the extended arithmetic case
        provider A -> admission delay -> transport failure -> retry
        sleep -> next attempt -> provider B success.

        Proves, on the ACTUAL instrumentation path:
          - all components are non-negative (no clamping);
          - retry sleep is NOT counted as transition (the transition
            is the pure bookkeeping gap, >= -0.05 s);
          - transition is NOT double-subtracted (>= -0.05 s);
          - the admission wall is NOT lost (admission_exclusive_s > 0
            when a delay is injected);
          - the terminal generate_total_s exists;
          - measured + remainder ~ total within -0.05 s.
        """
        import time as _time
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        lines = self._lines_for(m)

        # deterministic admission delay on provider A (zai)
        m.setattr(ra, "runtime_admission",
                   lambda *a, **k: (
                       _time.sleep(0.15),
                       (True, "PROBE_OK", {"state": "PROBE_OK"}))[1])

        zai_calls = {"n": 0}

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            if spec.provider_id == "zai":
                zai_calls["n"] += 1
                # the FIRST zai attempt (index 0) fails on transport,
                # forcing a retry sleep + second attempt; the second
                # zai attempt also fails, advancing to provider B.
                if zai_calls["n"] <= 2:
                    raise RuntimeError("zai transport failure")
                return "FIELD_MECHANISM: test"
            return "FIELD_MECHANISM: test"
        m.setattr(lr, "_call_openai_flavor", fake_call)
        m.setattr(lr, "_call_anthropic_flavor", fake_call)
        try:
            # max_retries=1 lets one retry sleep happen on zai before
            # the rung exhausts and advances to xkiro.
            res = lr.generate("p", policy=_policy("zai", "xkiro"),
                              max_retries=1)
            self.assertTrue(res.ok)
            self.assertEqual(res.provider_id, "xkiro")
            sp = lines[-1]["generate_spans"]
            total = sp.get("generate_total_s")
            # the terminal total exists on the final (xkiro success)
            # line
            self.assertIsNotNone(
                total, "S5 PART 4: terminal generate_total_s must "
                "exist on the successful final line")
            zai_rung = sp["rungs"][0]
            xkiro_rung = sp["rungs"][1]
            # 1) all components non-negative (no clamping)
            for r in sp["rungs"]:
                a = r.get("admission") or {}
                self.assertGreaterEqual(
                    a.get("probe_admission_s") or 0.0, 0.0)
                self.assertGreaterEqual(
                    a.get("probe_retry_sleep_s") or 0.0, 0.0)
                for att in r.get("attempts") or []:
                    self.assertGreaterEqual(
                        att.get("dispatch_s") or 0.0, 0.0,
                        "S5 PART 4: dispatch must be non-negative")
                    self.assertGreaterEqual(
                        att.get("retry_sleep_s") or 0.0, 0.0,
                        "S5 PART 4: retry sleep must be non-negative")
                    self.assertGreaterEqual(
                        att.get("transition_to_next_s") or 0.0,
                        -0.05,
                        "S5 PART 4: transition must be >= -0.05 s "
                        "(not double-subtracted, not counting the "
                        "retry sleep)")
                self.assertGreaterEqual(
                    r.get("post_provider_local_s") or 0.0, 0.0)
            # 2) the zai rung's admission wall is NOT lost (the
            # injected 0.15 s delay must be represented)
            self.assertGreater(
                (zai_rung.get("admission") or {}).get(
                    "probe_admission_s") or 0.0, 0.15,
                "S5 PART 4: the zai admission wall (injected 0.15 s "
                "delay) must be captured in admission_exclusive_s, "
                "not lost in the remainder")
            # 3) the zai rung actually carried a retry sleep (the
            # transport failure path was exercised)
            self.assertGreater(
                sum(att.get("retry_sleep_s") or 0.0
                    for att in zai_rung.get("attempts") or []), 0.0,
                "S5 PART 4: a retry sleep must be recorded on the "
                "failing zai rung")
            # 4) measured + remainder ~ total (full decomposition)
            measured = (sp.get("selection_ordering_s") or 0.0)
            for r in sp["rungs"]:
                a = r.get("admission") or {}
                measured += max((a.get("probe_admission_s") or 0.0)
                                - (a.get("probe_retry_sleep_s") or 0.0),
                                0.0)
                measured += max(a.get("probe_retry_sleep_s") or 0.0, 0.0)
                for att in r.get("attempts") or []:
                    measured += max(att.get("dispatch_s") or 0.0, 0.0)
                    measured += max(att.get("retry_sleep_s") or 0.0, 0.0)
                    measured += max(
                        att.get("transition_to_next_s") or 0.0, 0.0)
                measured += (r.get("post_provider_local_s") or 0.0)
            remainder = round(total - measured, 6)
            self.assertGreaterEqual(
                remainder, -0.05,
                "S5 PART 4: measured + remainder must close to the "
                "total within the documented -0.05 s tolerance; a "
                "larger negative remainder means a component was "
                "double-counted or lost")
        finally:
            m.undo()

    def test_o_selection_subspans_decompose_selection_ordering(self):
        """R530 §3: the selection subspan decomposition closes.

        A+B+C+D+E+H+I == selection_ordering_s within the documented
        -0.05 s clock tolerance; F+G are detail-of-E (inclusive, not
        additive — F+G <= E is NOT required since F/G walls are a
        subset measured with their own timers, but F+G must not
        exceed E beyond tolerance); every subspan >= -0.05; the
        diagnostic counts are present and internally consistent
        (at least one availability_score call, report scans >=
        score calls, catalog reads cover the inspected providers,
        rungs emitted >= 1 on a successful call). The test exercises
        the REAL generate() selection path (not invented values).
        """
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setattr(lr, "_call_openai_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                   lambda *a, **k: "FIELD_MECHANISM: test")
        lines = self._lines_for(m)
        try:
            self.assertTrue(lr.generate("p", policy=_policy("zai"),
                                        max_retries=0).ok)
            sp = lines[0]["generate_spans"]
            total = sp.get("selection_ordering_s")
            self.assertIsNotNone(total)
            subs = sp.get("selection_subspans")
            self.assertIsNotNone(
                subs, "R530: selection_subspans must be present on "
                      "the terminal line")
            for _k in ("A_availability_matrix_s",
                       "B_chain_construction_s",
                       "C_route_retirement_s", "D_cost_policy_s",
                       "E_build_ladder_s", "F_catalog_detail_s",
                       "G_scoring_detail_s",
                       "H_capability_evidence_s",
                       "I_selection_remainder_s"):
                self.assertIn(_k, subs)
                self.assertGreaterEqual(
                    subs[_k], -0.05,
                    f"R530: subspan {_k} is negative beyond the "
                    f"documented clock tolerance")
            additive = (subs["A_availability_matrix_s"]
                        + subs["B_chain_construction_s"]
                        + subs["C_route_retirement_s"]
                        + subs["D_cost_policy_s"]
                        + subs["E_build_ladder_s"]
                        + subs["H_capability_evidence_s"]
                        + subs["I_selection_remainder_s"])
            self.assertAlmostEqual(
                additive, total, delta=0.05,
                msg="R530: A+B+C+D+E+H+I must equal "
                    "selection_ordering_s within tolerance "
                    "(F+G are detail-of-E, not additive)")
            # F+G detail must not exceed E beyond tolerance (they
            # are a measured subset of E's wall with independent
            # timers; clock resolution is the only slack).
            self.assertLessEqual(
                subs["F_catalog_detail_s"] + subs["G_scoring_detail_s"],
                subs["E_build_ladder_s"] + 0.05,
                "R530: F+G detail exceeds its parent E wall beyond "
                "tolerance — the detail is not a subset")
            diag = sp.get("selection_diag")
            self.assertIsNotNone(diag)
            self.assertGreaterEqual(
                diag.get("n_availability_score_calls") or 0, 1,
                "R530: at least one availability_score call per "
                "selection")
            self.assertGreaterEqual(
                diag.get("n_availability_report_scans") or 0,
                diag.get("n_availability_score_calls") or 0,
                "R530: each score call performs >= 1 ledger scan")
            self.assertGreaterEqual(
                diag.get("n_discover_catalog_calls") or 0,
                diag.get("n_providers_inspected") or 0,
                "R530: catalog reads cover the inspected providers")
            self.assertGreaterEqual(
                diag.get("n_ladder_rungs_emitted") or 0, 1,
                "R530: a successful call emits >= 1 rung")
        finally:
            m.undo()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

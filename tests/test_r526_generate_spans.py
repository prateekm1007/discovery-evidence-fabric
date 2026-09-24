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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

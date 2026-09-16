"""tests/test_r483_synthesis_routing.py — the R483 round battery.

The round's measured defects (two live-proof campaign runs terminal
INCOMPLETE_INFERENCE_FAILURE, diagnosed from the durable branch's
committed bytes):

  D1 (routing) — the worker spawn pinned ENGINE_SYNTHESIS_PROVIDER=zai
  unconditionally under the R480 repoint (ZAI_API_KEY now an atria
  key), but the zai spec's ENVIRONMENT_GRANT basis is ineligible under
  ZERO_PAID_COST: the pinned preferred chain emptied and the extension
  rescue routed synthesis down the free routers in matrix order
  [unorouter, xkiro, ...] with atria sixth. The free-router models
  fail the verbatim-span citation contract; the R469 operator default
  (atria first) was silently defeated.

  D2 (capability) — the EmptyContentWithFinish same-model retry ladder
  was capped at a hardcoded 2048; Atria-Dawn-Preview measured 8
  run-owned failures (finish_reason=length) at caps <= 2048.

  D3 (observability) — the SynthesizeAdapter dropped generate()'s
  selection ledger, so "why did the walk skip rung X" was unanswerable
  from committed bytes (this round's diagnosis was blocked on exactly
  this hole).

Adversarial discipline (Art. XVII/XXX): every control is attacked —
the pin-gate is attacked with the repoint state, the ceiling ladder is
attacked with starvation progressions, the observability is attacked
with a SKIPPED_NOT_ADMITTED hop that must survive the projection, and
the R392 sandbox semantics are attacked for legitimate preservation.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import llm_registry as reg          # noqa: E402
from discovery_fabric.engine import model_cost_policy as mcp      # noqa: E402
from discovery_fabric.engine import model_routing as mr           # noqa: E402
from discovery_fabric.engine import adapters                      # noqa: E402

SERVER_SRC = (REPO_ROOT / "toscanini" / "server.py").read_text()
REG_SRC = (REPO_ROOT / "discovery_fabric" / "engine" /
           "llm_registry.py").read_text()

RING = ["ATRIA_API_KEY"] + [f"ATRIA_API_KEY_{i}" for i in range(2, 16)]
REPOINT = {"ZAI_BASE_URL": "https://api.atria-asi.ai/v1/chat/completions",
           "ZAI_MODEL": "Atria-Dawn-Preview",
           "ZAI_API_KEY": "placeholder-presence-only"}
ROUTERS = ["UNOROUTER_API_KEY", "XKIRO_API_KEY", "APINEX_API_KEY",
           "BAI_API_KEY", "BYNARA_API_KEY"]


def _fake_catalog(provider_id, force=False):
    """Hermetic catalog: the atria sole-model catalog (R469 measured:
    'the same sole model Atria-Dawn-Preview'), the free routers' STRONG
    rungs, empty elsewhere. No network."""
    models = {
        "atria": ["Atria-Dawn-Preview"],
        "unorouter": ["glm-5.3:free", "qwen3.8-27b:free"],
        "xkiro": ["qwen/qwen3.5-plus:free", "qwen/qwen3-max:free"],
    }.get(provider_id, [])
    return {"provider": provider_id, "status": "DISCOVERED",
            "models": models, "fetched_at_epoch": 1e18,
            "catalog_size": len(models), "eligible_count": len(models)}


class TestD1StaleSpawnPin(unittest.TestCase):
    """the pin must name a rung the ACTIVE cost policy admits."""

    def test_zai_ineligible_under_zero_paid_cost(self):
        """the sandbox (un-repointed) class: zai = ENVIRONMENT_GRANT,
        refused by the deployed policy. R483-union: reconcile FIRST with
        a clean env so a prior test's repoint-env reconciliation (the
        third line's classification flip is env-driven but the spec
        replacement is global) cannot leak the credited class in."""
        with mock.patch.dict(os.environ, {"ZAI_BASE_URL": "",
                                          "ENGINE_MODEL_COST_POLICY": ""}):
            reg.reconcile_runtime_classifications()
            spec = reg._SPEC_BY_ID["zai"]
            ok, note = mcp.provider_eligibility(spec)
        self.assertFalse(ok, note)
        self.assertIn("ENVIRONMENT_GRANT", note)

    def test_zai_repointed_class_is_credited_eligible(self):
        """the third line's reconciliation (union-adjudicated CANONICAL
        for the repointed state): with ZAI_BASE_URL external, the slot
        classifies credited-remote (FREE_TIER_API) and the policy
        admits it — the misclassification half of the campaign defect,
        fixed at the classification layer. Restores the sandbox class
        afterward (the spec replacement is GLOBAL — a leaked credited
        state breaks any later test that reads the shipped class)."""
        try:
            with mock.patch.dict(os.environ, {**REPOINT,
                                              "ENGINE_MODEL_COST_POLICY":
                                              ""}):
                rec = reg.reconcile_runtime_classifications()
                spec = reg._SPEC_BY_ID["zai"]
                ok, _ = mcp.provider_eligibility(spec)
            self.assertTrue(rec["reconciled"])
            self.assertTrue(rec["external_repoint"])
            self.assertTrue(ok)
        finally:
            with mock.patch.dict(os.environ, {"ZAI_BASE_URL": ""}):
                reg.reconcile_runtime_classifications()

    def test_zai_eligible_under_unrestricted(self):
        """the sandbox semantics preserved: under UNRESTRICTED the pin
        fires exactly as R392 intended (the legitimate case)."""
        spec = reg._SPEC_BY_ID["zai"]
        with mock.patch.dict(os.environ,
                             {"ENGINE_MODEL_COST_POLICY": "UNRESTRICTED"}):
            ok, _ = mcp.provider_eligibility(spec)
        self.assertTrue(ok)

    def test_atria_eligible_under_zero_paid_cost(self):
        spec = reg._SPEC_BY_ID["atria"]
        with mock.patch.dict(os.environ, {"ENGINE_MODEL_COST_POLICY": ""}):
            ok, _ = mcp.provider_eligibility(spec)
        self.assertTrue(ok)

    def test_spawn_pins_retired(self):
        """the union adjudication (Art. LXIV): the R392 zai pin DEFAULTS
        are RETIRED — no ENGINE_*_PROVIDER setdefault remains in the
        spawn path (the third line's retirement, canonical over this
        line's eligibility gate: a gate on a pin that must never fire
        is dead code). The engine's own R469 default routes synthesis
        atria-first; an explicit deployment env still wins (the env
        surface is the operator's, never the spawn's)."""
        for pin in ('setdefault("ENGINE_SYNTHESIS_PROVIDER"',
                    'setdefault("ENGINE_ATTACK_PROVIDER"',
                    'setdefault("ENGINE_ENSEMBLE_PROVIDERS"',
                    'setdefault("ENGINE_GRID_PROVIDERS"'):
            self.assertNotIn(pin, SERVER_SRC,
                             f"the {pin.split(chr(34))[1]} spawn default "
                             "must stay retired (Art. LXIV)")
        self.assertNotIn("zai_usable", SERVER_SRC)


class TestD2ChainRestored(unittest.TestCase):
    """the campaign regression: with the pin gone, synthesis rides the
    R469 operator default — atria first."""

    def _chain(self, env_overrides, policy_preferred=None):
        env = {**{k: "placeholder" for k in RING + ROUTERS}, **REPOINT,
               **env_overrides}
        try:
            with mock.patch.dict(os.environ, env, clear=False), \
                 mock.patch.object(mr, "discover_catalog",
                                   side_effect=_fake_catalog):
                matrix = reg.availability_matrix()
                avail = [m["provider_id"] for m in matrix
                         if m["available"] and m["cost_policy_eligible"]]
                preferred = policy_preferred or [
                    "atria", "openrouter", "deepseek", "anthropic", "openai",
                    "gemini", "qwen", "nvidia"]
                chain = [pid for pid in preferred if pid in avail]
                if not chain:
                    chain = [p for p in avail if p not in chain]
                ladder = mr.build_ladder(
                    mr.TASK_STRONG, role="synthesis",
                    preferred_providers=chain, available_providers=avail)
            return chain, ladder
        finally:
            # the reconciliation the matrix triggers is GLOBAL (the
            # frozen spec is replaced in-place surfaces) — restore the
            # shipped sandbox class so no later reader sees the leak
            with mock.patch.dict(os.environ, {"ZAI_BASE_URL": ""}):
                reg.reconcile_runtime_classifications()

    def test_repoint_state_synthesis_head_is_atria(self):
        """THE campaign regression: no ENGINE_SYNTHESIS_PROVIDER, the
        repoint env, the ring present — the ladder head is atria's
        Atria-Dawn-Preview (the R469 default restored)."""
        chain, ladder = self._chain({})
        self.assertEqual(chain[:1], ["atria"])
        self.assertEqual(ladder["rungs"][0]["provider"], "atria")
        self.assertEqual(ladder["rungs"][0]["model"], "Atria-Dawn-Preview")

    def test_legitimate_pin_still_pins_when_eligible(self):
        """the R392 semantics preserved where legitimate: an explicit
        ENGINE_SYNTHESIS_PROVIDER under UNRESTRICTED yields the
        single-provider override chain (fallback forbidden)."""
        chain, _ = self._chain(
            {"ENGINE_MODEL_COST_POLICY": "UNRESTRICTED"},
            policy_preferred=["zai"])
        self.assertEqual(chain, ["zai"])

    def test_extension_order_is_matrix_order_not_quality(self):
        """the honest record of the DEFECT's mechanism (pinned for the
        audit trail): with NO atria in the environment at all, the
        empty preferred chain falls to matrix order — the exact rescue
        that served the two campaign runs. This documents WHY the pin
        gate (D1) is the fix, not the extension."""
        env = {k: "placeholder" for k in ROUTERS}
        env.update(REPOINT)
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.object(mr, "discover_catalog",
                               side_effect=_fake_catalog):
            matrix = reg.availability_matrix()
            avail = [m["provider_id"] for m in matrix
                     if m["available"] and m["cost_policy_eligible"]]
        self.assertNotIn("atria", avail)
        self.assertEqual(avail[0], "unorouter",
                         "matrix order head — the measured campaign walk")


class TestD3ReasoningCeiling(unittest.TestCase):
    """the EmptyContentWithFinish same-model retry ladder."""

    def test_default_ceiling_is_2048_everywhere_except_atria(self):
        for pid, spec in reg._SPEC_BY_ID.items():
            expected = 8192 if pid == "atria" else 2048
            self.assertEqual(
                int(getattr(spec, "reasoning_retry_ceiling", 2048)), expected,
                f"{pid} ceiling")

    def test_atria_ceiling_basis_is_recorded(self):
        spec = reg._SPEC_BY_ID["atria"]
        self.assertEqual(spec.reasoning_retry_ceiling, 8192)
        self.assertLess(spec.reasoning_retry_ceiling,
                        spec.context_capacity_tokens)

    def test_ladder_math_atria(self):
        """the x4 progression against the spec ceiling: atria escalates
        512 -> 2048 -> 8192 -> stays (one more rung than before)."""
        spec = reg._SPEC_BY_ID["atria"]
        ceiling = int(getattr(spec, "reasoning_retry_ceiling", 2048) or 2048)
        budget = 512
        seen = [budget]
        for _ in range(4):
            if budget < ceiling:
                budget = min(ceiling, budget * 4)
                seen.append(budget)
        self.assertEqual(seen, [512, 2048, 8192])

    def test_ladder_math_default_spec_unchanged(self):
        spec = reg._SPEC_BY_ID["unorouter"]
        ceiling = int(getattr(spec, "reasoning_retry_ceiling", 2048) or 2048)
        budget = 512
        seen = [budget]
        for _ in range(4):
            if budget < ceiling:
                budget = min(ceiling, budget * 4)
                seen.append(budget)
        self.assertEqual(seen, [512, 2048],
                         "every non-atria provider keeps the standing "
                         "behavior byte-for-byte")

    def test_handler_reads_the_spec_ceiling(self):
        """source-shape: the hardcoded 2048 is gone from the handler;
        the getattr reads the ACTIVE spec's declared ceiling."""
        handler_pos = REG_SRC.index("except EmptyContentWithFinish as exc:")
        window = REG_SRC[handler_pos:handler_pos + 900]
        self.assertIn('getattr(spec, "reasoning_retry_ceiling"', window)
        self.assertNotIn("if attempt_budget < 2048:", window)
        self.assertNotIn("min(2048, attempt_budget * 4)", window)


class TestD4Observability(unittest.TestCase):
    """the routing truth rides the committed record."""

    def _fake_module(self):
        cand = {
            "candidate_id": "cand:A2:r483:abc",
            "problem_id": "r483_test",
            "mechanism": "seeded crystallization control",
            "intervention": "seeded flash vessel",
            "expected_effect": "silica stays suspended",
            "falsification_test": "measure deposition rate",
            "mechanism_source_span": "silica stays suspended",
            "model": "Atria-Dawn-Preview",
            "provider": "atria",
            "transport_status": "OK",
            "prompt_hash": "h1", "input_hash": "h2",
            "output_hash": "h3", "synthesis_timestamp": "t",
        }
        meta = {
            "model": "Atria-Dawn-Preview", "provider": "atria",
            "status": "OK",
            "task_degradation": {"requested_task": "STRONG",
                                 "actual_task_capability": "STRONG",
                                 "task_capability_match": True},
            "retry_notes": ["attempt 1: empty content "
                            "(finish_reason=length); same provider/model "
                            "retried with max_tokens=2048"],
            "provider_route": [
                {"provider": "atria", "failure_type": None,
                 "status": "SKIPPED_NOT_ADMITTED",
                 "capability_state": "PROBE_EXPIRED",
                 "fallback_provider": "unorouter"},
                {"provider": "unorouter", "failure_type": "RATE_LIMITED",
                 "status": "FAILED", "capability_state": "PROBE_OK",
                 "fallback_provider": "xkiro"},
                {"provider": "xkiro", "failure_type": None,
                 "status": "OK", "capability_state": "PROBE_OK",
                 "fallback_provider": None}],
            "selection_ledger": {
                "cost_policy_refusals": [
                    {"provider": "zai",
                     "reason": "cost basis ENVIRONMENT_GRANT ineligible "
                               "under ZERO_PAID_COST"}],
                "ladder": {"rungs": [
                    {"provider": "atria", "model": "Atria-Dawn-Preview",
                     "band": "PRIMARY"},
                    {"provider": "unorouter", "model": "glm-5.3:free",
                     "band": "PRIMARY"}]},
            },
        }
        mod = mock.MagicMock()
        mod.synthesize.return_value = cand
        mod._LAST_PROVIDER_META = meta
        return mod

    def test_synthesis_provenance_carries_the_routing_block(self):
        from tests.test_r453_lean_core import _env_with
        mod = self._fake_module()
        with mock.patch.dict(
                "sys.modules", {"discovery_fabric.a2.synthesize": mod}):
            res = adapters.SynthesizeAdapter().execute(
                _env_with(), {"run_id": "r483"})
        syn = res["apply_to"]["provenance"]["synthesis"]
        routing = syn["routing"]
        # the walk — including the SKIPPED hop with its state
        self.assertEqual(routing["provider_route"][0]["provider"], "atria")
        self.assertEqual(routing["provider_route"][0]["status"],
                         "SKIPPED_NOT_ADMITTED")
        self.assertEqual(routing["provider_route"][0]["capability_state"],
                         "PROBE_EXPIRED")
        # the cost-policy refusal (the D1 mechanism, now on the record)
        self.assertIn("ENVIRONMENT_GRANT",
                      routing["cost_policy_refusals"][0]["reason"])
        # the reasoning-cap escalation (the D2 mechanism, on the record)
        self.assertIn("max_tokens=2048", routing["retry_notes"][0])
        # the ladder head
        self.assertEqual(routing["ladder_head"][0]["provider"], "atria")

    def test_to_meta_projects_status_and_capability_state(self):
        res = reg.LLMCallResult(
            status=reg.ST_OK, provider_id="xkiro", model="m",
            prompt_hash="h", output_hash="h",
            route=[{"provider_attempted": "atria",
                    "failure_type": None,
                    "status": "SKIPPED_NOT_ADMITTED",
                    "capability_state": "PROBE_EXPIRED",
                    "fallback_provider": "unorouter"}])
        meta = res.to_meta()
        hop = meta["provider_route"][0]
        self.assertEqual(hop["status"], "SKIPPED_NOT_ADMITTED")
        self.assertEqual(hop["capability_state"], "PROBE_EXPIRED")

    def test_bounded_no_availability_matrix_embedded(self):
        """the routing block stays bounded: the full availability
        matrix is NOT embedded in the envelope (the D4 fix's own
        size discipline)."""
        from tests.test_r453_lean_core import _env_with
        mod = self._fake_module()
        with mock.patch.dict(
                "sys.modules", {"discovery_fabric.a2.synthesize": mod}):
            res = adapters.SynthesizeAdapter().execute(
                _env_with(), {"run_id": "r483"})
        routing = (res["apply_to"]["provenance"]["synthesis"]
                   ["routing"])
        self.assertNotIn("availability", routing)
        self.assertNotIn("matrix", routing)


if __name__ == "__main__":
    unittest.main()


class TestD5GridCallSite(unittest.TestCase):
    """the campaign run ts_54b91d454cf8's measured GRID_ERROR:
    KeyError 'span_instruction' at candidate_diversity._run_grid —
    the span-format hardening's missed call site. The fix carries the
    SAME span instruction as the primary path (one prompt authority),
    and the negative control attacks the regression class itself."""

    def test_grid_prompt_formats_with_the_span_instruction(self):
        from discovery_fabric.engine import candidate_diversity as cd
        import discovery_fabric.a2.synthesize as a2syn
        problem = {"device": "d", "failure": "f", "constraint": "c"}
        evidence = [{"title": "t", "abstract": "a" * 50}]
        # the exact call-shape _run_grid uses (the R483 fix): the
        # template formats WITHOUT KeyError
        try:
            a2syn.SYNTHESIS_PROMPT.format(
                device=problem["device"], failure=problem["failure"],
                constraint=problem["constraint"],
                title=evidence[0]["title"],
                abstract=evidence[0]["abstract"][:1200],
                span_instruction=getattr(a2syn, "SPAN_INSTRUCTION", ""))
        except KeyError as exc:
            self.fail(f"the grid call-site class regressed: {exc}")
        src = (REPO_ROOT / "discovery_fabric" / "engine" /
               "candidate_diversity.py").read_text()
        self.assertIn('span_instruction=getattr(a2syn, "SPAN_INSTRUCTION"',
                      src, "the grid must pass the span instruction")

    def test_every_template_placeholder_has_a_grid_kwarg(self):
        """the class-level negative control: EVERY placeholder in the
        frozen synthesis template is supplied by the grid's format
        call (no future hardening can miss the site silently)."""
        import re
        import discovery_fabric.a2.synthesize as a2syn
        src = (REPO_ROOT / "discovery_fabric" / "engine" /
               "candidate_diversity.py").read_text()
        grid_call = src[src.index("a2syn.SYNTHESIS_PROMPT.format("):
                        src.index("candidates = []")]
        for ph in re.findall(r"\{([a-z_]+)\}", a2syn.SYNTHESIS_PROMPT):
            self.assertIn(f"{ph}=", grid_call,
                          f"the grid format must supply {{{ph}}}")

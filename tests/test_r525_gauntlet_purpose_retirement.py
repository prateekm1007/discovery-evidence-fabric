"""tests/test_r525_gauntlet_purpose_retirement.py — R525 S4 contract.

The measured R525 cliff (S3): POST_RANK_GAUNTLET independent_attack
zai EmptyContentWithFinish MODEL_FAILURE — 3/12 rows, 564.4 s total
failure wall, 0 OK. The intervention is ONE purpose boundary:

  gauntlet  -> purpose post_rank:independent_attack -> zai retired
  linear    -> purpose "attack" (a2/adversarial)   -> untouched
  evolution / improve-child -> purpose independent_attack (default) -> untouched

Proves (directive §8):
  A. post_rank:independent_attack resolves the new post-rank
     gauntlet-attack scope
  B. zai is retired for that post-rank purpose
  C. zai remains allowed for ordinary independent_attack
  D. zai remains allowed for the linear ATTACK purpose ("attack" /
     ROLE_ATTACK)
  E. existing R520 technical retirement remains unchanged
  F. existing SYNTHESIS/MS routing remains unchanged
  G. no provider-specific branch exists in the resolver
  H. retirement remains data-driven through RETIRED_ROUTE_PROVIDERS
  I. the exact gauntlet call path uses the new post-rank purpose
  J. the linear ATTACK call path does not use independent_attack at
     all (it routes purpose "attack", unchanged)
  K. the new purpose changes nothing but routing (identical
     prompt/system/budget/exclusion args, purpose differs only)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import provider_health as ph      # noqa: E402
from discovery_fabric.engine import llm_registry as lr          # noqa: E402
from discovery_fabric.engine import runtime_admission as ra     # noqa: E402
from discovery_fabric.engine import independent_attack as ia    # noqa: E402


class TestPurposeBoundary(unittest.TestCase):
    """A/B/C/D/E/F — the resolver boundary."""

    def test_a_post_rank_purpose_resolves_gauntlet_scope(self):
        self.assertEqual(
            ph.retirement_scopes_for_purpose("post_rank:independent_attack"),
            {ph.PURPOSE_POST_RANK_GAUNTLET_ATTACK})

    def test_b_zai_retired_for_post_rank_purpose(self):
        self.assertTrue(ph.is_route_retired(
            "zai", purpose="post_rank:independent_attack"))
        kept, removed = ph.apply_route_retirement(
            ["zai", "xkiro", "unorouter"],
            purpose="post_rank:independent_attack")
        self.assertNotIn("zai", kept)
        self.assertTrue(any(
            r["provider"] == "zai" and
            r["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
            for r in removed))

    def test_c_zai_allowed_for_ordinary_independent_attack(self):
        self.assertEqual(
            ph.retirement_scopes_for_purpose("independent_attack"), set())
        self.assertFalse(ph.is_route_retired(
            "zai", purpose="independent_attack"))

    def test_d_zai_allowed_for_linear_attack(self):
        # the linear ATTACK stage routes purpose "attack"
        # (a2/adversarial) — never the gauntlet purpose.
        self.assertEqual(ph.retirement_scopes_for_purpose("attack"), set())
        self.assertFalse(ph.is_route_retired("zai", purpose="attack"))
        self.assertFalse(ph.is_route_retired("zai", role=ph.ROLE_ATTACK))

    def test_e_r520_technical_retirement_unchanged(self):
        self.assertEqual(
            ph.retirement_scopes_for_purpose("TECHNICAL_STATE_EXTRACTION"),
            {ph.PURPOSE_POST_RANK_TECHNICAL})
        self.assertTrue(ph.is_route_retired(
            "zai", purpose="TECHNICAL_STATE_EXTRACTION"))

    def test_f_synthesis_and_ms_routing_unchanged(self):
        self.assertFalse(ph.is_route_retired("zai", role=ph.ROLE_SYNTHESIS))
        self.assertFalse(ph.is_route_retired(
            "zai", purpose="synthesis"))
        self.assertEqual(
            ph.retirement_scopes_for_purpose("operator_foo"),
            {ph.PURPOSE_MS_OPERATOR_INSTANTIATION})

    def test_g_no_provider_branch_in_resolver(self):
        import inspect
        for fn in (ph.retirement_scopes_for_purpose, ph.is_route_retired):
            body = inspect.getsource(fn)
            self.assertNotIn('"zai"', body)
            self.assertNotIn("'zai'", body)

    def test_h_retirement_is_data(self):
        self.assertIn("zai", ph.RETIRED_ROUTE_PROVIDERS)
        self.assertIn(ph.PURPOSE_POST_RANK_GAUNTLET_ATTACK,
                      ph.RETIRED_ROUTE_PROVIDERS["zai"])


class TestCallSiteWiring(unittest.TestCase):
    """I/J — the exact call paths."""

    def test_i_gauntlet_call_site_uses_post_rank_purpose(self):
        src = (REPO_ROOT / "discovery_fabric" / "engine" / "run.py"
               ).read_text(encoding="utf-8")
        lines = src.splitlines()
        uses = [i for i, ln in enumerate(lines)
                if "attack_purpose=" in ln]
        # exactly one gauntlet wiring; evolution + improve-child keep
        # the default purpose (no attack_purpose= at their call sites).
        self.assertEqual(len(uses), 1)
        line_no = uses[0]
        self.assertIn("POST_RANK_ATTACK_PURPOSE", lines[line_no])
        # the wiring sits inside the post-rank gauntlet loop: after the
        # POST_RANK_GAUNTLET stage marker, before the calibration gate.
        gauntlet_mark = next(
            i for i, ln in enumerate(lines)
            if 'set_stage("POST_RANK_GAUNTLET")' in ln)
        calib_mark = next(
            i for i, ln in enumerate(lines)
            if "attacker-calibration gate" in ln)
        self.assertTrue(gauntlet_mark < line_no < calib_mark)

    def test_j_linear_attack_does_not_use_independent_attack(self):
        # the linear ATTACK stage routes through a2/adversarial with
        # purpose "attack" (AttackEngineAdapter) — independent_attack()
        # is never on the linear path, so the gauntlet retirement
        # cannot leak into it.
        import re
        run_src = (REPO_ROOT / "discovery_fabric" / "engine" / "run.py"
                   ).read_text(encoding="utf-8")
        calls = [m.start() for m in re.finditer(
            r"independent_attack\(", run_src)]
        call_lines = [run_src.count("\n", 0, pos) + 1 for pos in calls]
        # exactly two independent_attack() call sites in run.py: the
        # post-rank gauntlet (wired to the new purpose above) and the
        # evolution path (default purpose). The improve-child call
        # lives in improve_stage.py (default purpose).
        self.assertEqual(len(call_lines), 2)
        # the attack adapter path uses adversarial_challenge, confirmed
        # by the adapter contract (not independent_attack).
        ad_src = (REPO_ROOT / "discovery_fabric" / "engine" /
                  "adapters.py").read_text(encoding="utf-8")
        self.assertIn("adversarial_challenge", ad_src)

    def test_j_default_purpose_unchanged(self):
        import inspect
        sig = inspect.signature(ia.independent_attack)
        self.assertEqual(sig.parameters["attack_purpose"].default,
                         "independent_attack")


class TestRoutingOnly(unittest.TestCase):
    """K — the purpose changes routing input only."""

    def test_k_identical_inputs_differ_only_in_purpose(self):
        seen = []

        def fake_generate(prompt, system="", timeout=240, max_tokens=700,
                          purpose="mechanism_space", exclude_providers=None,
                          hard_pin_provider=None):
            seen.append({"prompt": prompt, "system": system,
                         "max_tokens": max_tokens, "purpose": purpose,
                         "exclude_providers": exclude_providers})
            return {"ok": True, "status": "OK", "content": (
                "MECHANISM: m\nINTERVENTION: i\nEXPECTED_EFFECT: e\n"
                "FALSIFICATION_TEST: f\nMECHANISM_SOURCE_SPAN: s"),
                    "provider": "xkiro", "model": "m",
                    "prompt_hash": "p", "output_hash": "o"}

        cand = {"candidate_id": "c", "mechanism": "m",
                "intervention": "i", "predicted_effect": "p",
                "testable_prediction": "t", "novel_design_variable": "n",
                "known_failure_modes": [], "constraint_set": {}}
        prob = {"device": "d", "failure": "f"}
        with mock.patch(
                "discovery_fabric.engine.mechanism_space.llm_generate",
                side_effect=fake_generate):
            r1 = ia.independent_attack(dict(cand), dict(prob), [],
                                       "genprov")
            r2 = ia.independent_attack(dict(cand), dict(prob), [],
                                       "genprov",
                                       attack_purpose=(
                                           ia.POST_RANK_ATTACK_PURPOSE))
        self.assertEqual(len(seen), 2)
        for k in ("prompt", "system", "max_tokens", "exclude_providers"):
            self.assertEqual(seen[0][k], seen[1][k], k)
        self.assertEqual(seen[0]["purpose"], "independent_attack")
        self.assertEqual(seen[1]["purpose"], ia.POST_RANK_ATTACK_PURPOSE)
        # verdict semantics identical under both purposes
        for k in ("attack_version", "overall", "independence_mode"):
            self.assertEqual(r1.get(k), r2.get(k), k)
        # the purpose rides the record as provenance
        self.assertEqual(r2.get("attack_purpose"),
                         ia.POST_RANK_ATTACK_PURPOSE)
        self.assertEqual(r1.get("attack_purpose"), "independent_attack")

    def test_k_end_to_end_post_rank_purpose_skips_zai(self):
        """The gauntlet call shape with the post-rank purpose must not
        attempt zai on ordinary routing (the R525 cliff mechanism)."""
        import pytest
        m = pytest.MonkeyPatch()
        for var in list(lr._SPEC_BY_ID.keys()):
            m.delenv(lr._SPEC_BY_ID[var].env_var, raising=False)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        m.setenv("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
        m.setattr(ra, "requires_probe", lambda *a, **k: False)
        m.setattr(ra, "runtime_admission",
                  lambda *a, **k: (True, "PROBE_OK", {"state": "PROBE_OK"}))

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            return "MECHANISM: m\nINTERVENTION: i\n"
        m.setattr(lr, "_call_openai_flavor", fake_call)
        m.setattr(lr, "_call_anthropic_flavor", fake_call)
        try:
            from discovery_fabric.engine import mechanism_space as ms
            res = ms.llm_generate(
                "p", system="s", purpose=ia.POST_RANK_ATTACK_PURPOSE,
                max_tokens=1600)
            # zai retired for this purpose: never served
            self.assertNotEqual(res.get("provider"), "zai")
            self.assertTrue(res.get("ok"))
        finally:
            m.undo()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

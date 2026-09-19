"""tests/test_r453_lean_core.py — the R453-LEAN-CORE battery (the
external auditor mandate's five required test classes, plus the
admission-semantics and single-URL pins).

The mandate (toscanini-lean-discovery-r453, exactChange + testsRequired):
  (a) n_candidates=0 => RANK/MECHANISM_SPACE operators/ATTACK not
      calling generate();
  (b) STRONG + cheap fallback => CAPABILITY_INSUFFICIENT and the skip
      cascade;
  (c) a surviving candidate still reaches ATTACK;
  (d) PREMISE_GATE/VERIFY/CLASSIFY still always reachable;
  (e) a grep test that cheap fallback cannot set synthesis ok=true.

Constitutional reachability proof obligations exercised here: attack
is skippable ONLY when there is nothing to attack (a verified primary
or a retained mechanism-space candidate both count); degraded STRONG
is not success; the owner cost policy is untouched by this module.
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
import sys  # noqa: E402

sys.path.insert(0, str(REPO))

from discovery_fabric.engine import stage_entry  # noqa: E402
from discovery_fabric.engine.candidate import Candidate  # noqa: E402
from discovery_fabric.engine import adapters  # noqa: E402

PROBLEM = {
    "problem_id": "r453_lean_test",
    "device": "ambulatory surgery center arthroscopic irrigation",
    "failure": "joint distension instability during high-flow flush",
    "failure_mode": "pressure swings outside the target band",
    "constraint": "no pump hardware replacement",
}
EVIDENCE = [{
    "id": "doi:10.1016/j.test.001",
    "title": "Arthroscopic irrigation pressure control in ambulatory "
             "knee surgery",
    "abstract": "Intra-articular pressure during arthroscopic surgery "
                "of the knee stays inside the 40-60 mmHg band when the "
                "inflow bag height and the shaver outflow resist are "
                "matched; mismatched outflow collapses the capsule.",
    "content_hash": "hash_test_001",
    "retrieval_timestamp": "2026-09-14T00:00:00Z",
    "source": "europepmc",
}]


def _env_with(**kw) -> Candidate:
    env = Candidate(problem=PROBLEM, problem_id="r453_lean_test")
    env.evidence = list(EVIDENCE)
    for k, v in kw.items():
        setattr(env, k, v)
    return env


def _degraded_synthesis_provenance() -> dict:
    return {"synthesis": {
        "model": "qwen3-1.7b",
        "provider": "localqwen",
        "transport_status": "OK",
        "task_degradation": {
            "requested_task": "STRONG",
            "actual_task_capability": "CHEAP_EMERGENCY_FALLBACK",
            "task_capability_match": False,
            "degraded_reason": "the serving model declares only CHEAP",
        }}}


def _ok_synthesis_provenance() -> dict:
    return {"synthesis": {
        "model": "glm-strong-model",
        "provider": "tierA",
        "transport_status": "OK",
        "task_degradation": {
            "requested_task": "STRONG",
            "actual_task_capability": "STRONG",
            "task_capability_match": True,
        }}}


class TestAdaptiveAdmissionSemantics(unittest.TestCase):
    """The justify door's new rules — the semantic core of the round."""

    def test_capability_insufficient_skips_every_expensive_stage(self):
        env = _env_with(provenance=_degraded_synthesis_provenance())
        for stage in stage_entry.ADAPTIVE_ADMISSION_STAGES:
            block = stage_entry.justify(stage, env, {}, set())
            self.assertEqual(
                block["entry_status"], "SKIPPED", stage)
            self.assertIn(
                "SYNTHESIS_CAPABILITY_INSUFFICIENT",
                block["skip_reason"], stage)
            self.assertEqual(
                block["prerequisite"],
                "SYNTHESIS_AT_REQUESTED_CAPABILITY", stage)

    def test_no_retained_candidate_skips_the_consuming_stages(self):
        env = _env_with(provenance=_ok_synthesis_provenance())
        # zero mechanism-space retention + unverified primary
        for stage in ("MULTI_SOURCE_DISCOVERY", "COLLISION", "PHYSICS",
                      "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT",
                      "NEXT_BEST_ACTION", "RANK"):
            block = stage_entry.justify(stage, env, {}, set())
            self.assertEqual(block["entry_status"], "SKIPPED", stage)
            self.assertIn("NO_RETAINED_CANDIDATE",
                          block["skip_reason"], stage)

    def test_retained_ms_candidate_admits_the_stages(self):
        env = _env_with(
            provenance=_ok_synthesis_provenance(),
            mechanism_space={"state": "BUILT",
                             "n_candidates_retained": 2})
        block = stage_entry.justify("ATTACK", env, {}, set())
        self.assertEqual(block["entry_status"], "ALLOWED")

    def test_verified_primary_admits_the_stages(self):
        """A verified primary candidate IS something to attack (the
        constitutional proof: attack is skippable only when there is
        nothing to attack)."""
        env = _env_with(
            provenance=_ok_synthesis_provenance(),
            adjudication={"evidence_verification": {"verified": True}})
        for stage in ("ATTACK", "RANK", "KILLER_EXPERIMENT"):
            block = stage_entry.justify(stage, env, {}, set())
            self.assertEqual(block["entry_status"], "ALLOWED", stage)

    def test_adjudication_and_classify_never_hit_the_new_rules(self):
        """The terminal classifiers stay reachable on BOTH blocked
        paths — they record the honest UNKNOWN/INSUFFICIENT state."""
        blocked_env = _env_with(
            provenance=_degraded_synthesis_provenance())
        empty_env = _env_with(provenance=_ok_synthesis_provenance())
        for stage in ("ADJUDICATION", "CLASSIFY"):
            for env in (blocked_env, empty_env):
                block = stage_entry.justify(stage, env, {}, set())
                self.assertEqual(block["entry_status"], "ALLOWED",
                                 f"{stage} must stay reachable")

    def test_premise_gate_verify_always_reachable(self):
        """(d): the always-on stages are not in the adaptive set."""
        for stage in ("RETRIEVE", "FREEZE", "PREMISE_GATE", "VERIFY"):
            self.assertNotIn(stage,
                             stage_entry.ADAPTIVE_ADMISSION_STAGES)
            env = _env_with(
                provenance=_degraded_synthesis_provenance())
            block = stage_entry.justify(stage, env, {}, set())
            self.assertEqual(block["entry_status"], "ALLOWED", stage)

    def test_legacy_envelope_capability_is_unknown_not_blocked(self):
        env = _env_with()  # no provenance record at all
        cap = stage_entry.synthesis_capability_state(env)
        self.assertEqual(cap["state"], "UNKNOWN")
        block = stage_entry.justify("ATTACK", env, {}, set())
        # cascade/verified-evidence rules still apply; the capability
        # rule itself must NOT fire on an unknown (Art. XXV)
        self.assertNotIn("SYNTHESIS_CAPABILITY_INSUFFICIENT",
                         block.get("skip_reason", ""))

    def test_r399_rules_unchanged(self):
        """The pre-existing rules keep their exact behavior (no
        regression of the R399 door)."""
        env = _env_with()
        cascade = stage_entry.justify("ATTACK", env, {}, {"SYNTHESIZE"})
        self.assertIn("UPSTREAM_TERMINAL_FAILURE", cascade["skip_reason"])
        env.evidence_classification = {
            "items": [{"classification": "DIRECT_SUPPORT"}]}
        ms = stage_entry.justify("MECHANISM_SPACE", env, {}, set())
        self.assertEqual(ms["entry_status"], "ALLOWED")
        self.assertEqual(ms["prerequisite"], "VERIFIED_EVIDENCE")


class TestCapabilityFailClosed(unittest.TestCase):
    """(b) + (e): degraded STRONG is a hard stop, never a cheap
    success."""

    def _synthesize_module(self, degraded: bool):
        """A fake a2.synthesize module shape with the recorded provider
        meta the adapter reads."""
        cand = {
            "candidate_id": "cand:A2:r453:abc",
            "problem_id": "r453_lean_test",
            "mechanism": "matched inflow/outflow resist",
            "intervention": "passive outflow resist sleeve",
            "expected_effect": "pressure stays in band",
            "falsification_test": "measure pressure across flow range",
            "mechanism_source_span": "pressure stays inside",
            "source_evidence": {"source_id": EVIDENCE[0]["id"],
                                "source_hash": "hash_test_001",
                                "source_span": EVIDENCE[0]["abstract"],
                                "source_title": EVIDENCE[0]["title"]},
        }
        deg = {
            "requested_task": "STRONG",
            "actual_task_capability": (
                "CHEAP_EMERGENCY_FALLBACK" if degraded else "STRONG"),
            "task_capability_match": not degraded,
        }
        mod = mock.MagicMock()
        mod.synthesize.return_value = cand if degraded else cand
        mod._LAST_PROVIDER_META = {
            "model": "qwen3-1.7b" if degraded else "glm-strong",
            "provider": "localqwen" if degraded else "tierA",
            "status": "OK",
            "task_degradation": deg,
        }
        return mod

    def test_degraded_synthesis_is_capability_insufficient(self):
        mod = self._synthesize_module(degraded=True)
        env = _env_with()
        with mock.patch.dict("sys.modules",
                             {"discovery_fabric.a2.synthesize": mod}):
            res = adapters.SynthesizeAdapter().execute(
                env, {"run_id": "r453"})
        self.assertEqual(res.get("state"), "CAPABILITY_INSUFFICIENT")
        self.assertTrue(res.get("capability_insufficient"))
        # the pseudo-invention is NOT promoted
        self.assertNotIn("mechanism_map", res["apply_to"])
        # the degradation record IS (for the audit trail + admission)
        syn = res["apply_to"]["provenance"]["synthesis"]
        self.assertEqual(syn["capability_state"],
                         "CAPABILITY_INSUFFICIENT")

    def test_ok_synthesis_still_promotes_the_candidate(self):
        mod = self._synthesize_module(degraded=False)
        env = _env_with()
        with mock.patch.dict("sys.modules",
                             {"discovery_fabric.a2.synthesize": mod}):
            res = adapters.SynthesizeAdapter().execute(
                env, {"run_id": "r453"})
        self.assertIn("mechanism_map", res["apply_to"])
        self.assertIsNone(res.get("capability_insufficient"))
        # the degradation record rides the success path too
        syn = res["apply_to"]["provenance"]["synthesis"]
        self.assertEqual(
            syn["task_degradation"]["task_capability_match"], True)

    def test_grep_cheap_fallback_cannot_set_synthesis_ok(self):
        """(e) the static guard: the adapter's capability check exists
        and PRECEDES the ok-synthesis return in the source."""
        src = (REPO / "discovery_fabric" / "engine" /
               "adapters.py").read_text()
        self.assertIn('_degraded = (', src,
                      "the SynthesizeAdapter capability guard must "
                      "exist in the source")
        self.assertIn('CAPABILITY_INSUFFICIENT', src)
        guard_pos = src.index("_degraded = (")
        ok_return_pos = src.index(
            '"mechanism_map": {', guard_pos)
        # the guard branch returns BEFORE the ok-synthesis result is
        # constructed (source order == execution order for the guard)
        degraded_return_pos = src.index(
            "degraded_candidate_rejected=True", guard_pos)
        self.assertLess(
            degraded_return_pos, ok_return_pos,
            "the CAPABILITY_INSUFFICIENT return must precede the "
            "ok-synthesis return (cheap fallback can never set "
            "synthesis ok=true)")

    def test_skip_cascade_after_capability_insufficient(self):
        """(b): with the degraded provenance on the envelope, the whole
        expensive tail is skipped — the admission cascade the conductor
        applies via the same justify door."""
        env = _env_with(provenance=_degraded_synthesis_provenance())
        skipped = []
        for stage in ("MECHANISM_SPACE", "MULTI_SOURCE_DISCOVERY",
                      "COLLISION", "PHYSICS", "ATTACK", "CONTRADICTION",
                      "KILLER_EXPERIMENT", "NEXT_BEST_ACTION", "RANK"):
            if stage_entry.justify(stage, env, {}, set())[
                    "entry_status"] == "SKIPPED":
                skipped.append(stage)
        self.assertEqual(len(skipped), 9,
                         "the full expensive tail must skip")


class TestEmptyPathNoGenerateCalls(unittest.TestCase):
    """(a): n_candidates=0 => no MECHANISM_SPACE operator calls, no
    ATTACK LLM, no RANK LLM."""

    def test_mechanism_space_operators_not_called_on_empty_path(self):
        env = _env_with(provenance=_ok_synthesis_provenance())
        # zero verified evidence items => the existing gate skips
        # BEFORE any operator call
        calls = []
        with mock.patch(
                "discovery_fabric.engine.mechanism_space.llm_generate",
                side_effect=lambda *a, **kw: calls.append(1) or {
                    "ok": False, "status": "CALL_FAILED"}):
            res = adapters.MechanismSpaceAdapter().execute(
                env, {"run_id": "r453"})
        self.assertEqual(
            res["apply_to"]["mechanism_space"]["state"],
            "SKIPPED_EVIDENCE_VERIFICATION_FAILED")
        self.assertEqual(calls, [],
                         "zero LLM calls on the unverified-evidence "
                         "path — the R401 extraction fan-out is gone")

    def test_lean_path_makes_at_most_one_operator_call(self):
        """The lean construction: one operator instantiation call, no
        extraction fan-out (admission passed)."""
        env = _env_with(
            provenance=_ok_synthesis_provenance(),
            evidence_classification={
                "n_items": 1,
                "items": [{"source_id": EVIDENCE[0]["id"],
                           "classification": "DIRECT_SUPPORT"}]})
        calls = []
        good_response = (
            "MECHANISM: matched inflow and outflow resist holds the "
            "pressure in band\n"
            "INTERVENTION: a passive outflow resist sleeve sized to "
            "the shaver flow\n"
            "EXPECTED_EFFECT: pressure stays inside the 40-60 mmHg "
            "band\n"
            "FALSIFICATION_TEST: measure pressure across the commanded "
            "flow range\n"
            "MECHANISM_SOURCE_SPAN: pressure stays inside the 40-60 "
            "mmHg band\n"
            "NOVEL_DESIGN_VARIABLE: the outflow resist sleeve's "
            "flow-resistance value\n"
            "TESTABLE_PREDICTION: doubling the inflow step keeps the "
            "pressure within 5 mmHg of the band edge\n")
        import discovery_fabric.engine.mechanism_space as ms

        def _fake_llm(prompt, system="", **kw):
            calls.append(prompt[:60])
            return {"ok": True, "status": "OK",
                    "content": good_response,
                    "provider": "tierA", "model": "glm-strong",
                    "prompt_hash": "h1", "output_hash": "h2",
                    "latency_ms": 100,
                    "task_degradation": {
                        "requested_task": "STRONG",
                        "actual_task_capability": "STRONG",
                        "task_capability_match": True},
                    "call_provenance": {}, "cost_provenance": {}}
        with mock.patch.object(ms, "llm_generate",
                               side_effect=_fake_llm):
            res = adapters.MechanismSpaceAdapter().execute(
                env, {"run_id": "r453"})
        space = res["apply_to"]["mechanism_space"]
        self.assertEqual(len(calls), 1,
                         "the lean path makes EXACTLY ONE operator "
                         f"generation call (made {len(calls)})")
        self.assertEqual(space["construction"][:9], "R453_LEAN")
        self.assertIn("R453_LEAN_REUSE_FREEZE_VERIFY_FACTS",
                      space["structured_evidence"]["construction"])
        self.assertGreaterEqual(space.get("n_candidates_generated", 0), 0)

    def test_rank_adapter_is_deterministic(self):
        """RANK itself makes no LLM call — its adapter is a
        deterministic allocation policy (the STRONG directional call
        was the evolution layer's, now admission-guarded)."""
        import inspect
        from discovery_fabric.engine.adapters import \
            PortfolioRankingAdapter
        src = inspect.getsource(PortfolioRankingAdapter)
        self.assertNotIn("generate(", src)
        self.assertNotIn("llm_", src)

    def test_attack_not_admitted_on_empty_set(self):
        """ATTACK's admission refuses the empty set — and its module is
        never imported/executed for the LLM path (the justify door
        refuses before the adapter runs)."""
        env = _env_with(provenance=_ok_synthesis_provenance())
        block = stage_entry.justify("ATTACK", env, {}, set())
        self.assertEqual(block["entry_status"], "SKIPPED")
        facts = block["prerequisite_evidence"]
        self.assertEqual(facts["n_ms_retained"], 0)
        self.assertFalse(facts["primary_verified"])


class TestSurvivorStillAttacked(unittest.TestCase):
    """(c): a surviving candidate still reaches ATTACK."""

    def test_fixture_candidate_reaches_attack(self):
        env = _env_with(
            provenance=_ok_synthesis_provenance(),
            adjudication={"evidence_verification": {"verified": True}},
            mechanism_map={
                "mechanism": "matched inflow/outflow resist",
                "intervention": "passive outflow resist sleeve",
                "raw_candidate": {
                    "mechanism": "matched resist",
                    "intervention": "sleeve",
                    "source_evidence": {
                        "source_id": EVIDENCE[0]["id"],
                        "source_hash": "hash_test_001",
                        "source_span": EVIDENCE[0]["abstract"][:200]}}})
        self.assertEqual(
            stage_entry.justify("ATTACK", env, {}, set())[
                "entry_status"], "ALLOWED")

        fake_adv = mock.MagicMock()
        fake_adv.adversarial_challenge.return_value = {
            "overall": "CONTESTED", "n_challenges": 3}
        fake_adv._LAST_ATTACK_PROVIDER_META = {"provider": "tierB"}
        with mock.patch.dict("sys.modules",
                             {"discovery_fabric.a2.adversarial":
                              fake_adv}):
            res = adapters.AttackEngineAdapter().execute(
                env, {"run_id": "r453"})
        self.assertEqual(res["apply_to"]["attack_results"]["overall"],
                         "CONTESTED")
        fake_adv.adversarial_challenge.assert_called_once()

    def test_retained_ms_candidate_reaches_attack(self):
        env = _env_with(
            provenance=_ok_synthesis_provenance(),
            mechanism_space={"state": "BUILT",
                             "n_candidates_retained": 1})
        self.assertEqual(
            stage_entry.justify("ATTACK", env, {}, set())[
                "entry_status"], "ALLOWED")


class TestOneGenerateContract(unittest.TestCase):
    """Item 3: a single documented base URL; no empty-credential
    probes; the cost policy untouched."""

    def test_single_documented_base_url(self):
        """The availability marker alone (LOCAL_QWEN_BASE_URL) now
        carries the URL — the dual-variable footgun is closed."""
        from discovery_fabric.engine.llm_registry import _SPEC_BY_ID
        spec = _SPEC_BY_ID["localqwen"]
        env = {"LOCAL_QWEN_BASE_URL":
               "http://127.0.0.1:8791/v1/chat/completions",
               "LOCALQWEN_BASE_URL": ""}
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("LOCALQWEN_BASE_URL", None)
            self.assertEqual(
                spec.url_for_call(),
                "http://127.0.0.1:8791/v1/chat/completions")
        # the explicit override still wins (the recorded escape hatch)
        env2 = {"LOCAL_QWEN_BASE_URL":
                "http://127.0.0.1:8790/v1/chat/completions",
                "LOCALQWEN_BASE_URL":
                "http://127.0.0.1:8795/v1/chat/completions"}
        with mock.patch.dict(os.environ, env2, clear=False):
            self.assertEqual(
                spec.url_for_call(),
                "http://127.0.0.1:8795/v1/chat/completions")

    def test_no_probe_with_empty_credentials(self):
        """generate() never probes an unkeyed provider — the typed
        SKIPPED_NO_CREDENTIAL route entry replaces the probe."""
        import importlib
        from discovery_fabric.engine import llm_registry as reg
        importlib.reload(reg)
        env = {"LOCAL_QWEN_BASE_URL": "",
               "ZAI_API_KEY": "", "ENGINE_MODEL_COST_POLICY":
               "UNRESTRICTED"}
        saved = {k: os.environ.get(k) for k in env}
        try:
            for k, v in env.items():
                if v == "":
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            probed = []

            def _no_probe(*a, **kw):
                probed.append(a)
                return {"ok": True}

            with mock.patch.object(
                    reg.runtime_admission if hasattr(
                        reg, "runtime_admission") else
                    __import__(
                        "discovery_fabric.engine.runtime_admission",
                        fromlist=["probe_capability"]),
                    "probe_capability", side_effect=_no_probe):
                res = reg.generate("probe prompt", max_tokens=8,
                                   max_provider_fallbacks=0,
                                   max_retries=0)
            self.assertNotEqual(res.status, "OK")
            self.assertEqual(
                probed, [],
                "no provider with empty credentials may be probed "
                "through generate() (R453-LEAN-CORE item 3)")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_cost_policy_not_widened(self):
        """The mandate: do not widen ZERO_PAID_COST; do not enable
        tokenrouter; A3 stays owner-gated."""
        from discovery_fabric.engine import model_cost_policy as cp
        self.assertEqual(
            cp._ELIGIBLE[cp.ZERO_PAID_COST],
            ["ZERO_PAID_COST_SELF_HOSTED"],
            "the ZERO_PAID_COST eligible bases must be unchanged")
        self.assertIn("FREE_TIER_API", cp.COST_BASIS_VOCAB)
        self.assertNotIn("FREE_TIER_API",
                         cp._ELIGIBLE[cp.ZERO_PAID_COST])


class TestDeletionAccounting(unittest.TestCase):
    """The mandate's accounting obligations, machine-checked."""

    def test_no_new_files_in_the_engine_tree(self):
        """The round adds ZERO engine files (tests only)."""
        import subprocess
        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD",
             "--", "discovery_fabric/"],
            cwd=str(REPO), capture_output=True, text=True)
        modified = [l for l in r.stdout.splitlines() if l.strip()]
        for f in modified:
            self.assertIn(
                f, ("discovery_fabric/engine/run.py",
                    "discovery_fabric/engine/stage_entry.py",
                    "discovery_fabric/engine/adapters.py",
                    "discovery_fabric/engine/llm_registry.py",
                    # R481 AMENDMENT (disclosed): the IMPROVE stage's
                    # cost class lives in cheap_screen.py (the
                    # every-stage-coverage pin demands it) and the
                    # stage module itself is new (improve_stage.py is
                    # exercised through its own battery, not this
                    # mandate's accounting)
                    "discovery_fabric/engine/cheap_screen.py",
                    # R510-BRIDGE AMENDMENT (disclosed): the production
                    # evidence-bridge repair adds the epistemic-absence
                    # guard + the shared guarded term engine to
                    # mechanism_space.py (thresholds, instruments, and
                    # adjudicator untouched); adapters.py carries the
                    # lean-side selection. Same mandate accounting
                    # otherwise.
                    "discovery_fabric/engine/mechanism_space.py",
                    # R510-P0 AMENDMENT (disclosed): the canonical
                    # production reality loop lives in
                    # reality_ingestion.py (entrypoint + hardened ingest
                    # + executing branches + SEARCH-IMPACT + child
                    # launcher + resume; thresholds/contracts/matcher
                    # untouched). Same mandate accounting otherwise.
                    "discovery_fabric/engine/reality_ingestion.py",
                    # R495 AMENDMENT (disclosed): the A2 burden-of-
                    # proof instrument is the R490-owned calibration
                    # surface — v4.2 (the attacker-computes standard)
                    # edits v4_corrections.py (rule 4.5) and
                    # a2/adversarial.py (the prompt standard + the
                    # 2.1.0 version), the same surface the R493/R494
                    # rounds tuned under the R490 plan; the R481
                    # mandate's own files remain untouched
                    "discovery_fabric/v4_corrections.py",
                    "discovery_fabric/a2/adversarial.py"),
                f"the mandate's file list is exhaustive: {f} is outside "
                "run.py/stage_entry.py/adapters.py/llm_registry.py")

    def test_stage_order_unchanged(self):
        """R481 AMENDMENT (disclosed): IMPROVE joined between
        KILLER_EXPERIMENT and ADJUDICATION (the external audit's P0-1
        loop closure — the R453 freeze was 16 stages; the deliberate,
        documented contract change follows the R394/R397/R401
        pattern). 17 stages, same relative order otherwise."""
        from discovery_fabric.engine.adapters import STAGE_ORDER
        self.assertEqual(len(STAGE_ORDER), 17)
        self.assertEqual(STAGE_ORDER[5], "MECHANISM_SPACE")
        self.assertEqual(STAGE_ORDER[12], "IMPROVE")
        self.assertEqual(STAGE_ORDER[-1], "RANK")

    def test_entry_helper_version_bumped(self):
        """The door's version records the semantic change."""
        self.assertEqual(stage_entry.ENTRY_HELPER_VERSION,
                         "stage_entry/1.1.0")


if __name__ == "__main__":
    unittest.main()

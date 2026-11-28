"""tests/test_r10_a0plus_simple_arm.py — R10 P0 items 1+2 (owner round
2026-11-13): the A0+ arm IS the simple arm.

  * AT MOST ONE repair call — the 2.0.0 three-round repair loop is
    retired; the source carries no repair loop and the record contract
    names the policy;
  * the three killed problems are planned FROM THE COMMITTED KILL
    RECORDS (fu-004/sofc typed skips — no baseline bytes; the
    non-DEV12 killed problems with committed baseline bytes run);
  * the latency contract: hard 40 s timeout SET (never setdefault),
    one immediate retry or one fallback, NO fixed process sleeps on
    the active path, the engine's retry pacing honors the typed knob;
  * the TTFB propagation: the transport's measured TTFB actually
    reaches the per-call timeline (missing stays None, never zero).

Hermetic (source inspection + pure functions; no LLM, no network).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A0P = _load("r7_a0plus_mod", "scripts/r7_a0plus.py")
from discovery_fabric.engine import llm_registry as REG  # noqa: E402


class TestSimpleArmContract:
    def test_no_multi_round_repair_loop_in_the_arm(self):
        src = (REPO / "scripts" / "r7_a0plus.py").read_text(
            encoding="utf-8")
        assert "for _round in (1, 2, 3)" not in src, (
            "the 2.0.0 three-round repair loop is still present — the "
            "owner's R10 audit rejected the multi-repair composer")
        assert "repair_policy" in src
        assert "at_most_one_repair_call" in src

    def test_arm_contract_record_names_the_policy(self):
        assert A0P.A0P_VERSION == "r7_a0plus/3.1.0"
        assert A0P.HARD_TIMEOUT_S == 40
        assert A0P.MAX_RETRIES == 1
        assert A0P.TOTAL_BUDGET_S == 300
        assert A0P.PAIRS_A0.name == "r11_a0plus"

    def test_hard_bounds_are_set_not_defaulted(self):
        src = (REPO / "scripts" / "r7_a0plus.py").read_text(
            encoding="utf-8")
        # the explicit assignment (owner: do not rely on setdefault)
        assert 'os.environ["ENGINE_LLM_TIMEOUT_S"]' in src
        assert 'os.environ["ENGINE_LLM_RETRY_SLEEP_S"]' in src
        # every llm_generate call rides the hard bounds (the bounded
        # generate wrapper sets them per call)
        assert '"timeout", HARD_TIMEOUT_S' in src
        assert '"max_retries", MAX_RETRIES' in src

    def test_repair_call_is_bounded_by_the_total_budget(self):
        src = (REPO / "scripts" / "r7_a0plus.py").read_text(
            encoding="utf-8")
        assert "TOTAL_BUDGET_EXHAUSTED" in src

    def test_typed_skips_emit_records(self):
        """R10: a typed skip / provenance-incomplete writes its typed
        record (nothing silently dropped, Art. XXV) — the 1.0.0/2.0.0
        silent-return class is retired."""
        src = (REPO / "scripts" / "r7_a0plus.py").read_text(
            encoding="utf-8")
        assert "_emit_typed_record" in src
        assert 'TYPED_SKIP_BASELINE_ABSENT' in src
        assert 'TYPED_SKIP_NO_PAIR' in src
        # the provenance-incomplete branch emits its typed record too
        assert src.count("INCOMPLETE_PROVENANCE") >= 3

    def test_call_accounting_reports_baseline_and_arm_separately(self):
        src = (REPO / "scripts" / "r7_a0plus.py").read_text(
            encoding="utf-8")
        assert "call_accounting" in src
        assert "baseline_generation" in src
        assert "a0plus_calls" in src
        assert "never summed" in src


class TestKilledProblemsFromCommittedHistory:
    def test_killed_ids_recovered_from_kill_records(self):
        """The identities come from the committed kill records — never
        guessed. Both non-DEV12 killed problems with committed baseline
        bytes are recovered (the owner's third killed case)."""
        killed = A0P._killed_problem_ids()
        assert "eval-new06-bearing-vibration-predictor" in killed
        assert "bench-p05-bridge-bearing-aging" in killed
        # DEV12 problems are never in this list (fu-004/sofc stay in
        # DEV12 as typed skips of the main loop)
        dev12 = set(A0P._dev12_ids())
        assert not (set(killed) & dev12)

    def test_killed_problem_loads_its_committed_pair_and_problem(self):
        pid = "eval-new06-bearing-vibration-predictor"
        pair = A0P._load_pair(pid)
        assert pair is not None
        assert str(pair.get("baseline_answer") or "").strip()
        prob = A0P._problem_record(pid)
        assert prob.get("question_type") == "predictor-design"

    def test_typed_skips_have_no_baseline_bytes(self):
        """fu-004/sofc: the typed skip is TRUE — the committed pairs
        carry empty baseline answers (the compared object does not
        exist, Art. XXV)."""
        for pid in ("dev-fu-004-fouling", "eval-sofc-thermal-cycling"):
            pair = A0P._load_pair(pid)
            assert pair is not None
            assert not str(pair.get("baseline_answer") or "").strip()

    def test_baseline_identity_binds_bytes_when_schema_absent(self):
        """The killed non-DEV12 pairs predate the bound_inputs schema:
        the identity is the sha256 OF the baseline answer bytes."""
        import hashlib
        pid = "eval-new06-bearing-vibration-predictor"
        pair = A0P._load_pair(pid)
        sha = A0P._baseline_identity(pid, pair)
        expect = hashlib.sha256(
            str(pair.get("baseline_answer") or "").encode("utf-8")) \
            .hexdigest()
        assert sha == expect

    def test_arm_queue_covers_dev12_plus_killed(self):
        ids = A0P._arm_queue_ids()
        assert "dev-fu-004-fouling" in ids          # DEV12 typed skip
        assert "eval-sofc-thermal-cycling" in ids   # DEV12 typed skip
        assert "eval-new06-bearing-vibration-predictor" in ids
        assert "bench-p05-bridge-bearing-aging" in ids
        assert len(ids) == len(set(ids))


class TestNoFixedSleepsOnTheActivePath:
    def test_engine_retry_sleep_honors_the_typed_knob(self, monkeypatch):
        monkeypatch.setenv("ENGINE_LLM_RETRY_SLEEP_S", "0")
        assert REG._retry_sleep_s(1) == 0.0
        assert REG._retry_sleep_s(2) == 0.0
        monkeypatch.setenv("ENGINE_LLM_RETRY_SLEEP_S", "1.5")
        assert REG._retry_sleep_s(3) == 1.5

    def test_engine_retry_sleep_default_keeps_history(self, monkeypatch):
        monkeypatch.delenv("ENGINE_LLM_RETRY_SLEEP_S", raising=False)
        assert REG._retry_sleep_s(1) == 2.0
        assert REG._retry_sleep_s(2) == 4.0

    def test_engine_registry_uses_the_pacing_helper(self):
        src = (REPO / "discovery_fabric" / "engine" / "llm_registry.py") \
            .read_text(encoding="utf-8")
        assert src.count("time.sleep(2 * retries_used)") == 0, (
            "the fixed retry backoff must route through the typed "
            "pacing helper")
        assert src.count("time.sleep(_retry_sleep_s(retries_used))") == 2

    def test_runner_has_no_fixed_sleeps(self):
        src = (REPO / "scripts" / "r7_queue_runner.py").read_text(
            encoding="utf-8")
        assert "time.sleep(" not in src, (
            "the owner's R10 directive removes fixed sleeps from the "
            "queue runner — the schedule is the pacing")


class TestTtfbPropagation:
    """R10 (owner latency item): the transport MEASURES ttfb, but the
    R10 measured battery showed ttfb null on every A0+ timeline row —
    the projection read ttfb_s while the route hop carries ttfb_ms.
    The measured value must actually reach the record; missing stays
    None (NOT_MEASURED, never zero)."""

    def test_timeline_reads_a_ttfb_ms_hop(self):
        res = {"provider_route": [{
            "provider_attempted": "zai", "model": "glm-4-plus",
            "status": "OK", "attempts": 1, "retry_count": 0,
            "latency_ms": 1187, "ttfb_ms": 312, "gateway_hang": False}]}
        rows = A0P._timeline_from_result(res, "a0plus_constraint_audit")
        assert len(rows) == 1 and rows[0]["measured"] is True
        assert rows[0]["ttfb_ms"] == 312

    def test_timeline_reads_a_ttfb_s_hop(self):
        res = {"provider_route": [{
            "provider_attempted": "xkiro", "model": "m",
            "status": "OK", "attempts": 1, "retry_count": 0,
            "latency_ms": 900, "ttfb_s": 0.4}]}
        rows = A0P._timeline_from_result(res, "p")
        assert rows[0]["ttfb_ms"] == 400

    def test_ttfb_missing_stays_none_never_zero(self):
        res = {"provider_route": [{
            "provider_attempted": "q", "model": "m", "status": "OK",
            "attempts": 1, "retry_count": 0, "latency_ms": 900}]}
        rows = A0P._timeline_from_result(res, "p")
        assert rows[0]["ttfb_ms"] is None
        assert A0P._ttfb_ms_from_hop({}) is None
        assert A0P._ttfb_ms_from_hop({"ttfb_ms": 0}) == 0  # real zero ok

    def test_mechanism_space_projection_normalizes_ttfb(self):
        from discovery_fabric.engine import mechanism_space as MS
        hops = [{"provider_attempted": "zai", "model": "m",
                 "status": "OK", "attempts": 1, "retry_count": 0,
                 "latency_ms": 1187, "ttfb_ms": 312}]
        row = MS._project_route_hops(hops)[0]
        assert row["ttfb_s"] == 0.312
        assert MS._project_route_hops([{"latency_ms": 5}])[0] \
            ["ttfb_s"] is None
        assert MS._project_route_hops(None) == []

    def test_registry_records_ttfb_without_zero_placeholder(self):
        src = (REPO / "discovery_fabric" / "engine"
               / "llm_registry.py").read_text(encoding="utf-8")
        assert 'or 0) * 1000' not in src, (
            "the banned missing->0 conversion: a transport that did "
            "not record ttfb must produce None, never 0 ms")
        msrc = (REPO / "discovery_fabric" / "engine"
                / "mechanism_space.py").read_text(encoding="utf-8")
        assert "_project_route_hops" in msrc
        # the projection helper is the single route-projection site
        assert msrc.count('provider_route": _project_route_hops') == 1


class TestRunnerChunkingAndRecords:
    def test_chunks_are_wall_budget_sized(self):
        src = (REPO / "scripts" / "r7_queue_runner.py").read_text(
            encoding="utf-8")
        assert "CHUNK_BUDGET_S" in src
        assert "chunk budget consumed" in src

    def test_invocation_record_is_written(self):
        src = (REPO / "scripts" / "r7_queue_runner.py").read_text(
            encoding="utf-8")
        assert "r7_queue_invocations.jsonl" in src

    def test_ablation_blocked_below_ten_valid_judgments(self):
        """owner R10 P1-8: the 48-item ablation stays blocked until
        >=10 valid A0+-vs-full judgments exist in the committed
        comparison record — the gate reads the RECORD BYTES."""
        runner = _load("runner_abl", "scripts/r7_queue_runner.py")
        g = runner._ablation_gate()
        rec = REPO / "eval" / "a0plus_compare_r10.json"
        if rec.exists():
            d = json.loads(rec.read_text(encoding="utf-8"))
            n_valid = int((d.get("tally_vs_full_pipeline") or {})
                          .get("n_valid") or 0)
            assert g["allowed"] is (n_valid >= 10)
        else:
            assert g["allowed"] is False
            assert "blocked" in g["reason"]

    def test_plan_carries_the_killed_problems(self, monkeypatch, tmp_path):
        """The planning CONTRACT: every DEV12 + killed problem with no
        delivered 3.0.0 record is planned into r10_a0plus. Hermetic
        against the live battery's bytes: the pair dir points at an
        empty tmp dir (no delivered records -> everything planned)."""
        runner = _load("runner_mod2", "scripts/r7_queue_runner.py")
        monkeypatch.setattr(runner, "A0P_PAIRS", Path(tmp_path))
        plan = runner.build_plan()
        a0 = [i for i in plan if i["kind"] == "a0plus"]
        pids = {i["problem"] for i in a0}
        assert "eval-new06-bearing-vibration-predictor" in pids
        assert "bench-p05-bridge-bearing-aging" in pids
        assert "dev-fu-004-fouling" in pids
        assert "eval-sofc-thermal-cycling" in pids
        assert all(i["pairs_out"] == "eval/pairs/r11_a0plus"
                   for i in a0)

    def test_delivered_records_leave_the_plan(self, monkeypatch, tmp_path):
        """The delivered-state policy in the plan: once a 3.0.0 record
        with a typed result binds the baseline identity, the item is
        NOT re-planned (the honest typed-INCOMPLETE arms are terminal;
        re-running is an explicit operator act)."""
        runner = _load("runner_mod3", "scripts/r7_queue_runner.py")
        monkeypatch.setattr(runner, "A0P_PAIRS", Path(tmp_path))
        import hashlib
        rec = {"a0plus_version": runner.A0P_VERSION,
               "problem_id": "dev-fu-003-motor-insulation",
               "result": "INCOMPLETE_CONTRACT",
               "baseline_sha_source": "deadbeef"}
        (Path(tmp_path) / "dev-fu-003-motor-insulation.json").write_text(
            json.dumps(rec), encoding="utf-8")
        # bind the identity: the DEV12-fresh pair's bound sha
        fresh = json.loads((REPO / "eval" / "pairs" / "dev12_fresh"
                            / "dev-fu-003-motor-insulation.json")
                           .read_text(encoding="utf-8"))
        sha = str(fresh.get("bound_inputs", {}).get(
            "baseline_answer_sha256") or "")
        rec["baseline_sha_source"] = sha or hashlib.sha256(
            str(fresh.get("baseline_answer") or "").encode("utf-8")) \
            .hexdigest()
        (Path(tmp_path) / "dev-fu-003-motor-insulation.json").write_text(
            json.dumps(rec), encoding="utf-8")
        assert runner._a0plus_v2_delivered(
            "dev-fu-003-motor-insulation") is True
        plan = runner.build_plan()
        pids = {i["problem"] for i in plan if i["kind"] == "a0plus"}
        assert "dev-fu-003-motor-insulation" not in pids


class TestQueueDeliveredStatePolicy:
    """R10 queue policy: an honest typed-INCOMPLETE arm is a DELIVERED
    record — the queue does not re-plan it (an automatic re-run would
    be unbounded quota burn under the cron pacing)."""

    def test_delivered_typed_incomplete_is_terminal(self):
        runner = _load("runner_deliv", "scripts/r7_queue_runner.py")
        # these three pins hold only once the live battery has
        # delivered the records; they type the CONTRACT, not the
        # current bytes
        assert hasattr(runner, "_a0plus_v2_delivered")
        assert "TYPED_SKIP_BASELINE_ABSENT" in runner.A0P_TERMINAL_STATES
        assert "INCOMPLETE_PROVENANCE" in runner.A0P_TERMINAL_STATES
        assert "INCOMPLETE_CONTRACT" in runner.A0P_TERMINAL_STATES
        assert "INCOMPLETE_CONSISTENCY_VIOLATIONS" \
            in runner.A0P_TERMINAL_STATES

    def test_stale_exhausted_state_reconciles_to_delivered_bytes(self):
        """Art. XXV: a recorded state that no longer matches measured
        reality is corrected — the measured hazard (a chunk racing the
        arm edits leaves stale EXHAUSTED states shadowing delivered
        pairs) is repaired typed, visibly."""
        runner = _load("runner_rec", "scripts/r7_queue_runner.py")
        st = {"status": {
            "a0plus::zombie-problem": {"state": "EXHAUSTED",
                                       "attempts": 3}}}
        # a zombie problem with no record is NOT reconciled (the
        # reconcile only fires on delivered bytes)
        n = runner._reconcile_delivered_states(st, [])
        assert n == 0
        assert st["status"]["a0plus::zombie-problem"]["state"] == \
            "EXHAUSTED"

    def test_delivered_incomplete_verdict_is_done_not_retry(self, ):
        """The classifier's verdict for a delivered typed-INCOMPLETE
        arm starts with DONE (the state rides the verdict)."""
        runner = _load("runner_verdict", "scripts/r7_queue_runner.py")
        src = (REPO / "scripts" / "r7_queue_runner.py").read_text(
            encoding="utf-8")
        assert 'DONE (a0plus delivered typed' in src
        assert "_a0plus_v2_delivered(item[\"problem\"])" in src

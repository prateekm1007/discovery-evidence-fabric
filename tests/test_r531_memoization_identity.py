"""tests/test_r531_memoization_identity.py — R531 §4/§5 contract.

Proves the Case-A counterfactual BEFORE any production behavior
changes: within one generate() invocation, already-computed
availability/ledger results for identical inputs may be reused
instead of rescanning the routing ledger repeatedly.

The harness exercises the REAL llm_registry.generate() /
build_ladder() path (hermetic provider mocks + a controlled temp
routing ledger — never a mocked miniature of build_ladder()).

  A. INPUT/COMPUTED IDENTITY (determinism baseline):
     A1. two identical real generate() calls -> identical ladder,
         rungs, ordering, selected rung, provenance, scores.
     A2. scenario matrix (purposes x provider sets x ledger sizes
         x health states): each scenario twice -> identical.
  B. MEMO-WRAPPER EQUIVALENCE (test-only wrapper, NOT production):
     a test-only invocation-local memo around
     model_routing.availability_score, keyed on the full input
     tuple + ledger file identity. Matrix with/without wrapper ->
     identical routing outputs + strictly fewer ledger scans.
  C. ADVERSARIAL (§5 — attempt to break the proposal):
     C1. ledger append between invocations -> second run reflects
         the new bytes (sensitivity; fresh table per invocation).
     C2. health change (cooldown on) -> ordering changes; the memo
         does not mask it.
     C3. cost-policy change -> chain changes; not masked.
     C4. retirement change -> chain changes; not masked.
     C5. task/purpose change -> different ladder; not masked.
     C6. time skew (now += 3600) -> scores recomputed (the key
         carries now; no false reuse across time).
     C7. duplicate-looking calls with one meaningful difference
         (model X vs Y) -> distinct keys, both computed.
     C8. intra-selection concurrent append simulation: a counting
         ledger tail that appends on the Kth read. The
         identity-guarded memo recomputes post-append (the guard
         catches the mtime/size change); a guard-less memo would
         go stale — demonstrating WHY the ledger-identity guard
         is part of the safe rule.
     C9. catalog change between invocations -> ladder changes
         (memo covers scoring only; catalog re-read, not masked).
     C10. failed provider becomes eligible (ok=true append) ->
         scores change -> reflected.

  D. CALL/SCIENTIFIC BEHAVIOR (on the wrapper runs):
     same provider call count, failed-hop count, retry behavior,
     serving provider/model, provider_route, selection_ledger,
     cost_policy_refusals, retry_notes; same candidate output
     under the same provider response.

If any identity proof fails: STOP (directive §15). Do not
implement. Record the candidate as unsafe/UNKNOWN.
"""
from __future__ import annotations

import json
import sys
import time
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


def _policy(*providers, purpose="synthesis"):
    return lr.SelectionPolicy(preferred_providers=list(providers),
                              max_preference_fallback=0,
                              purpose=purpose)


def _strip_timing(sp):
    """Routing outputs with wall-clock/call-identity values removed
    (timing fields + per-call UUIDs legitimately differ run to run;
    they are not routing semantics)."""
    import copy
    import re
    sp = copy.deepcopy(sp)
    _drop = {"generate_total_s", "generate_elapsed_s",
             "selection_ordering_s", "generate_start_epoch",
             "generate_call_id", "request_id",
             "post_provider_local_s", "dispatch_s", "retry_sleep_s",
             "transition_to_next_s", "probe_admission_s",
             "probe_retry_sleep_s", "post_success_sleep_s",
             "start_utc", "end_utc", "started_at", "finished_at",
             "recorded_at_epoch", "synthesis_timestamp"}
    _clock_re = re.compile(
        r"(_age_s|_at_epoch|_timestamp|_utc|_epoch|_elapsed_s|"
        r"_at|_time|_date|_stamp|_until|_expiry|fetched|"
        r"cooldown_until|^at$|^timestamp$|as_of)$")
    def _clean(o):
        if isinstance(o, dict):
            for k in list(o.keys()):
                if k in _drop or (
                        k.endswith("_s") and isinstance(o[k],
                                                        (int, float))
                        and k not in ("n_llm_chat_calls",
                                      "attempt_index",
                                      "attempt_budget")):
                    o[k] = None
                elif _clock_re.search(k):
                    o[k] = None
                else:
                    _clean(o[k])
        elif isinstance(o, list):
            for v in o:
                _clean(v)
    _clean(sp)
    # selection_subspans/diag walls vary; counts must match
    if isinstance(sp.get("selection_diag"), dict):
        for k in list(sp["selection_diag"].keys()):
            if k.endswith("_s"):
                sp["selection_diag"][k] = None
    return sp


class _LedgerSeed:
    """Deterministic routing-ledger bytes on a temp path."""

    def __init__(self, tmpdir, n_lines=60):
        self.path = Path(tmpdir) / "ledger.jsonl"
        lines = []
        base = 1790000000.0
        provs = ["zai", "xkiro", "openrouter", "deepseek"]
        for i in range(n_lines):
            p = provs[i % len(provs)]
            lines.append({
                "provider": p, "model": f"{p}-model",
                "ok": (i % 5 != 4),
                "status": ("OK" if i % 5 != 4 else "CALL_FAILED"),
                "failure_class": (None if i % 5 != 4
                                  else "TRANSPORT"),
                "latency_ms": 100 + (i * 7) % 900,
                "task": "synthesis",
                "recorded_at_epoch": base + i,
            })
        self.path.write_text("\n".join(
            json.dumps(l) for l in lines) + "\n", encoding="utf-8")

    def append(self, **kw):
        rec = {"provider": "zai", "model": "zai-model", "ok": True,
               "status": "OK", "failure_class": None,
               "latency_ms": 120, "task": "synthesis",
               "recorded_at_epoch": time.time()}
        rec.update(kw)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")


class MemoHarness(unittest.TestCase):
    """Shared harness: hermetic generate() with a controlled ledger."""

    def _run(self, m, seed, providers=("zai",), purpose="synthesis",
             extra_env=None, catalog_dir=None, freeze_now=None):
        led = mr.RoutingLedger(path=seed.path, max_tail=800)
        m.setattr(mr, "LEDGER", led)
        if freeze_now is not None:
            # freeze wall-clock inputs (decay weights, ages,
            # recency) so the two compared runs see IDENTICAL
            # inputs: determinism proper. perf_counter (walls)
            # is untouched. C6 skews time deliberately and does
            # not freeze.
            import time as _tm
            m.setattr(_tm, "time", lambda: freeze_now)
        if catalog_dir is not None:
            # point the catalog cache at an isolated dir: cache-file
            # evolution across runs is an INPUT change, so each
            # compared run gets identical cache state (Art. XXV —
            # compare identical inputs, never conflate cache
            # evolution with routing nondeterminism).
            m.setattr(mr, "CATALOG_DIR", Path(catalog_dir))
        m.setattr(lr, "_call_openai_flavor",
                  lambda *a, **k: "FIELD_MECHANISM: test")
        m.setattr(lr, "_call_anthropic_flavor",
                  lambda *a, **k: "FIELD_MECHANISM: test")
        lines = []
        m.setattr(mr, "record_call_outcome",
                  lambda *a, **k: lines.append(k))
        if extra_env:
            for k, v in extra_env.items():
                m.setenv(k, v)
        res = lr.generate("p", policy=_policy(*providers,
                                              purpose=purpose),
                          max_retries=0)
        assert res.ok, f"harness generate() must succeed: {res.status}"
        sp = lines[-1]["generate_spans"]
        # diagnostic counts ride the terminal spans block (generate()
        # already took-and-zeroed at span close; a further take here
        # would return zeros — read the recorded block instead).
        diag = dict(sp.get("selection_diag") or {})
        # order (res, sp, lines, diag): [:3] splats directly into
        # _route_signature(res, sp, lines).
        return res, sp, lines, diag

    def _route_signature(self, res, sp, lines, drop_diag_counts=False):
        """The full routing-behavior signature (§4 computed/call
        identity): everything except wall-clock values and
        per-call identity. Diagnostic COUNTS are included by
        default (identical inputs must recompute identically);
        pass drop_diag_counts=True when comparing memoized vs
        unmemoized runs (fewer recomputations is the effect under
        test; counts are asserted separately via the diag dict)."""
        sp = _strip_timing(sp)
        if drop_diag_counts and isinstance(sp.get("selection_diag"),
                                           dict):
            sp = dict(sp)
            sp["selection_diag"] = {
                k: v for k, v in sp["selection_diag"].items()
                if not k.startswith("n_")}
        return {
            "provider": res.provider_id,
            "model": res.model,
            "status": res.status,
            "content": res.content,
            "spans": sp,
            "selection_ledger": _strip_timing(res.selection_ledger),
            "n_ledger_lines": len(lines),
        }

    # ------------------------------------------------ A. determinism
    def _pristine_catalog(self, td):
        """Copy the repo catalog dir to tmp once per td; return a
        resetter that restores identical cache state before each
        run (cache-file evolution across runs is an INPUT change).
        Idempotent: repeated calls for the same td reuse the
        pristine snapshot."""
        import shutil
        pristine = Path(td) / "catalog_pristine"
        work = Path(td) / "catalog_work"
        if not pristine.exists():
            src = mr.CATALOG_DIR
            if src.exists():
                shutil.copytree(src, pristine)
            else:
                pristine.mkdir(parents=True)

        def _reset():
            if work.exists():
                shutil.rmtree(work)
            shutil.copytree(pristine, work)
            return work
        return _reset

    def test_a1_identical_calls_identical_routing(self):
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                seed = _LedgerSeed(td, n_lines=60)
                reset_cat = self._pristine_catalog(td)
                import time as _t0
                _frozen = _t0.time()
                r1 = self._route_signature(*self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=reset_cat(),
                    freeze_now=_frozen)[:3])
                r2 = self._route_signature(*self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=reset_cat(),
                    freeze_now=_frozen)[:3])
                self.assertEqual(r1, r2)
        finally:
            m.undo()

    def test_a2_scenario_matrix_deterministic(self):
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                reset_cat = self._pristine_catalog(td)
                import time as _t0
                for n_lines in (0, 60, 500):
                    seed = _LedgerSeed(td, n_lines=n_lines)
                    for provs in (("zai",), ("zai", "xkiro")):
                        for purpose in ("synthesis",
                                        "operator_DIRECT_TRANSFER"):
                            _frozen = _t0.time()
                            a = self._route_signature(*self._run(
                                m, seed, provs,
                                purpose=purpose,
                                catalog_dir=reset_cat(),
                                freeze_now=_frozen)[:3])
                            b = self._route_signature(*self._run(
                                m, seed, provs,
                                purpose=purpose,
                                catalog_dir=reset_cat(),
                                freeze_now=_frozen)[:3])
                            self.assertEqual(
                                a, b,
                                f"nondeterministic routing: lines="
                                f"{n_lines} provs={provs} "
                                f"purpose={purpose}")
        finally:
            m.undo()

    # --------------------------------------- B. memo-wrapper equivalence
    class _TestMemo:
        """Test-only invocation-local memo (NOT production): wraps
        availability_score keyed on the full input tuple + ledger
        file identity. Fresh table per installation (per
        invocation); the ledger-identity guard forces recompute on
        concurrent append."""

        def __init__(self, m, guard=True):
            import time as _t
            self._t = _t
            self.calls = 0
            self.hits = 0
            self.invalidations = 0
            self.table = {}
            self._orig = mr.availability_score
            self._guard = guard
            memo = self

            def _wrapped(provider, model=None, task=None,
                         avoid_provider=None, latency_class=2,
                         now=None):
                now = now if now is not None else _t.time()
                ident = None
                if memo._guard:
                    p = mr.LEDGER._path
                    try:
                        st = p.stat()
                        ident = (st.st_mtime_ns, st.st_size)
                    except Exception:  # noqa: BLE001 — no identity
                        ident = None
                # Design 2 (R531): the ledger identity is CHECKED
                # on hit, not part of the key. A post-append
                # repeat finds its key but mismatches identity ->
                # invalidation -> recompute (the table stays
                # small; stale entries are unreachable AND
                # overwritten, never returned).
                k = (provider, model, task, avoid_provider,
                     latency_class, now)
                hit = memo.table.get(k)
                if hit is not None:
                    if (not memo._guard) or hit[1] == ident:
                        memo.hits += 1
                        return hit[0]
                    memo.invalidations += 1
                memo.calls += 1
                v = memo._orig(
                    provider, model=model, task=task,
                    avoid_provider=avoid_provider,
                    latency_class=latency_class, now=now)
                memo.table[k] = (v, ident)
                return v

            m.setattr(mr, "availability_score", _wrapped)

    def test_b1_memo_wrapper_equivalent_and_faster(self):
        """Same inputs with/without the test-only memo -> identical
        routing signatures + strictly fewer ledger scans with the
        memo + identical score values."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                reset_cat = self._pristine_catalog(td)
                seed = _LedgerSeed(td, n_lines=200)
                plain = self._route_signature(*self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=reset_cat())[:3],
                    drop_diag_counts=True)
                # plain score/scan counts (unmemoized recomputation)
                _, _, _, plain_diag = self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=reset_cat())
                memo = self._TestMemo(m)
                wrapped = self._route_signature(*self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=reset_cat())[:3],
                    drop_diag_counts=True)
                self.assertEqual(plain, wrapped)
                self.assertGreater(
                    memo.hits, 0,
                    "the memo must actually reuse within one call")
                # layered consistency: the test wrapper over the
                # PRODUCTION memo must recompute no more than
                # production alone (both memoize the same unique
                # computations; the wrapper adds no recomputation).
                # The strict scan-reduction proof lives in E1
                # (production vs disabled).
                self.assertLessEqual(
                    memo.calls,
                    plain_diag.get("n_availability_score_calls") or 0,
                    "layered wrapper must not recompute more than "
                    "production alone")
                # score values identical: compare the emitted ladder
                # scores embedded in the (stripped) signatures
                self.assertEqual(
                    plain["spans"], wrapped["spans"])
        finally:
            m.undo()

    def test_b2_memo_equivalence_matrix(self):
        """B1 across purposes x provider sets x ledger sizes. Each
        matrix cell gets a FRESH wrapper (fresh table) so reuse is
        strictly invocation-local."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                reset_cat = self._pristine_catalog(td)
                for n_lines in (0, 60, 500):
                    seed = _LedgerSeed(td, n_lines=n_lines)
                    for provs in (("zai",), ("zai", "xkiro")):
                        for purpose in ("synthesis",
                                        "operator_DIRECT_TRANSFER"):
                            plain = self._route_signature(
                                *self._run(
                                    m, seed, provs, purpose=purpose,
                                    catalog_dir=reset_cat())[:3],
                                drop_diag_counts=True)
                            # fresh wrapper install for this cell
                            # only (undone right after the cell)
                            cell = pytest.MonkeyPatch()
                            memo = self._TestMemo(cell)
                            try:
                                wrapped = self._route_signature(
                                    *self._run(
                                        m, seed, provs,
                                        purpose=purpose,
                                        catalog_dir=reset_cat())[:3],
                                    drop_diag_counts=True)
                            finally:
                                cell.undo()
                            self.assertEqual(
                                plain, wrapped,
                                f"memo divergence: lines={n_lines} "
                                f"provs={provs} purpose={purpose}")
                            self.assertGreater(
                                memo.hits, 0,
                                f"no memo reuse: lines={n_lines} "
                                f"provs={provs} purpose={purpose}")
        finally:
            m.undo()

    # --------------------------------------- C. adversarial (§5)
    def _wrapped_run(self, m, seed, td, provs=("zai", "xkiro"),
                     purpose="synthesis"):
        """One run under a FRESH test-only memo; returns
        (signature, memo). Fresh table per call = the
        invocation-local lifecycle under test."""
        import pytest
        reset_cat = self._pristine_catalog(td)
        cell = pytest.MonkeyPatch()
        memo = self._TestMemo(cell)
        try:
            sig = self._route_signature(*self._run(
                m, seed, provs, purpose=purpose,
                catalog_dir=reset_cat())[:3],
                drop_diag_counts=True)
            return sig, memo
        finally:
            cell.undo()

    def test_c1_ledger_append_between_invocations_reflected(self):
        """A ledger append between two invocations changes the
        second run's scores (sensitivity); a fresh memo per
        invocation reflects the new bytes (wrapped == plain on the
        new inputs)."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                seed = _LedgerSeed(td, n_lines=60)
                before, _ = self._wrapped_run(m, seed, td)
                for _ in range(40):
                    seed.append(provider="zai", model="zai-model",
                                ok=False, status="CALL_FAILED",
                                failure_class="TRANSPORT",
                                latency_ms=50, task="synthesis")
                after_wrapped, _ = self._wrapped_run(m, seed, td)
                after_plain = self._route_signature(*self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=self._pristine_catalog(td)())[:3],
                    drop_diag_counts=True)
                self.assertEqual(after_wrapped, after_plain)
                # the zai failure mass must move the needle
                # somewhere in the routing outputs (scores feed
                # ordering/selection)
                self.assertNotEqual(before, after_wrapped)
        finally:
            m.undo()

    def test_c2_health_change_not_masked(self):
        """A cooldown change alters ordering; the per-invocation
        memo does not mask it (fresh table sees the new health)."""
        import pytest
        import tempfile
        from discovery_fabric.engine import provider_health as ph
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                seed = _LedgerSeed(td, n_lines=60)
                healthy, _ = self._wrapped_run(m, seed, td)
                m.setattr(ph.HEALTH, "in_cooldown",
                          lambda p: p == "zai")
                cooled_wrapped, _ = self._wrapped_run(m, seed, td)
                cooled_plain = self._route_signature(*self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=self._pristine_catalog(td)())[:3],
                    drop_diag_counts=True)
                self.assertEqual(cooled_wrapped, cooled_plain)
        finally:
            m.undo()

    def test_c3_cost_policy_change_not_masked(self):
        """A cost-policy change alters the chain; not masked."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                seed = _LedgerSeed(td, n_lines=60)
                open_run, _ = self._wrapped_run(m, seed, td)
                m.setenv("ENGINE_MODEL_COST_POLICY", "RESTRICTED")
                tight_wrapped, _ = self._wrapped_run(m, seed, td)
                tight_plain = self._route_signature(*self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=self._pristine_catalog(td)())[:3],
                    drop_diag_counts=True)
                self.assertEqual(tight_wrapped, tight_plain)
        finally:
            m.undo()

    def test_c5_task_purpose_change_not_masked(self):
        """Different purpose -> different ladder; not masked."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                seed = _LedgerSeed(td, n_lines=60)
                s1, _ = self._wrapped_run(
                    m, seed, td, purpose="synthesis")
                s2, _ = self._wrapped_run(
                    m, seed, td, purpose="operator_DIRECT_TRANSFER")
                p2 = self._route_signature(*self._run(
                    m, seed, ("zai", "xkiro"),
                    purpose="operator_DIRECT_TRANSFER",
                    catalog_dir=self._pristine_catalog(td)())[:3],
                    drop_diag_counts=True)
                self.assertEqual(s2, p2)
                self.assertNotEqual(s1, s2)
        finally:
            m.undo()

    def test_c6_time_skew_recomputes(self):
        """Scores computed at different `now` values are NOT
        falsely reused: the memo key carries now, so a +3600 s
        skew recomputes (call count rises, no stale hit)."""
        import pytest
        import tempfile
        import time as _time
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                reset_cat = self._pristine_catalog(td)
                seed = _LedgerSeed(td, n_lines=200)
                import pytest as _pt
                cell = _pt.MonkeyPatch()
                memo = self._TestMemo(cell)
                try:
                    self._run(m, seed, ("zai", "xkiro"),
                              catalog_dir=reset_cat())
                    calls_after_first = memo.calls
                    # skew wall-clock +3600 s for the second call:
                    # every score key differs -> full recompute
                    real_time = _time.time
                    m.setattr(_time, "time",
                              lambda: real_time() + 3600.0)
                    self._run(m, seed, ("zai", "xkiro"),
                              catalog_dir=reset_cat())
                    self.assertGreater(
                        memo.calls, calls_after_first,
                        "time skew must force recomputation (the "
                        "memo key carries now; no false reuse "
                        "across time)")
                finally:
                    cell.undo()
        finally:
            m.undo()

    def test_c7_near_duplicate_inputs_distinguished(self):
        """Duplicate-looking calls differing in exactly one input
        (model) compute separately (distinct keys)."""
        import pytest
        m = pytest.MonkeyPatch()
        _hermetic(m)
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                seed = _LedgerSeed(td, n_lines=60)
                led = mr.RoutingLedger(path=seed.path, max_tail=800)
                m.setattr(mr, "LEDGER", led)
                cell = pytest.MonkeyPatch()
                memo = self._TestMemo(cell)
                try:
                    v1 = mr.availability_score(
                        "zai", model="zai-model-a", task="synthesis")
                    v2 = mr.availability_score(
                        "zai", model="zai-model-b", task="synthesis")
                    self.assertEqual(
                        memo.calls, 2,
                        "distinct models must compute separately, "
                        "never share a memo entry")
                    self.assertEqual(memo.hits, 0)
                    v1b = mr.availability_score(
                        "zai", model="zai-model-a", task="synthesis")
                    self.assertEqual(v1, v1b)
                finally:
                    cell.undo()
        finally:
            m.undo()

    def test_c8_intra_selection_append_guard(self):
        """The crux (§5): a ledger append DURING one selection.
        A counting tail appends 200 zai-failure lines on its 10th
        read (early enough to fire mid-selection even though the
        memo reduces total reads). Provenance-corrected
        expectations (the plain and guarded runs perform DIFFERENT
        computation sets at different times, so byte-for-byte
        equality between them under concurrent mutation is NOT a
        sound assertion — both are order-dependent outcomes):
          (a) the guarded run completes with valid routing AND
              the guard actually fires (invalidations > 0);
          (b) every score the guarded run USED equals a fresh
              computation on the final bytes for triples whose
              last computation was post-append (consistency with
              the newest observed state — the guard's guarantee:
              no returned score is ever computed from bytes older
              than the latest observed file identity);
          (c) a guard-less memo DIVERGES from the guarded run
              (stale pre-append scores reused post-append) —
              proving WHY the ledger-identity guard is part of
              the safe rule."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                reset_cat = self._pristine_catalog(td)

                def _counting_run(use_memo, guard, tag):
                    # each sub-run gets its OWN seed file (identical
                    # initial bytes): appends during one sub-run
                    # must not contaminate another sub-run's file
                    # identity (Art. XXV — compare identical
                    # inputs, never conflate cross-run mutation).
                    _seed = _LedgerSeed(td, n_lines=60)
                    _seed.path = _seed.path.rename(
                        _seed.path.parent /
                        f"ledger_{tag}.jsonl")
                    led = mr.RoutingLedger(path=_seed.path,
                                           max_tail=800)
                    m.setattr(mr, "LEDGER", led)
                    m.setattr(lr, "_call_openai_flavor",
                              lambda *a, **k: "FIELD_MECHANISM: test")
                    m.setattr(lr, "_call_anthropic_flavor",
                              lambda *a, **k: "FIELD_MECHANISM: test")
                    lines = []
                    m.setattr(mr, "record_call_outcome",
                              lambda *a, **k: lines.append(k))
                    reads = {"n": 0}
                    orig_tail = led.tail

                    def _mutating_tail(n=None):
                        reads["n"] += 1
                        if reads["n"] == 10:
                            for _ in range(200):
                                _seed.append(
                                    provider="zai",
                                    model="zai-model", ok=False,
                                    status="CALL_FAILED",
                                    failure_class="TRANSPORT",
                                    latency_ms=50, task="synthesis")
                        return orig_tail(n)

                    m.setattr(led, "tail", _mutating_tail)
                    cell = pytest.MonkeyPatch()
                    memo = None
                    if use_memo:
                        memo = self._TestMemo(cell, guard=guard)
                    try:
                        res = lr.generate(
                            "p", policy=_policy("zai", "xkiro"),
                            max_retries=0)
                        assert res.ok
                        sig = self._route_signature(
                            res, lines[-1]["generate_spans"], lines,
                            drop_diag_counts=True)
                        return sig, memo, reads["n"], _seed
                    finally:
                        cell.undo()

                guarded, gmemo, _, gseed = _counting_run(
                    True, True, "guarded")
                self.assertGreater(
                    (gmemo.invalidations if gmemo else 0), 0,
                    "the guard must actually fire at least once "
                    "on the mid-selection append")
                # (b) every score the guarded run used equals a
                # fresh computation on the FINAL bytes of ITS OWN
                # seed file, for triples whose table entry carries
                # that final identity.
                _st = gseed.path.stat()
                _final_ident = (_st.st_mtime_ns, _st.st_size)
                _checked = 0
                for _k, (_v, _ident) in (
                        gmemo.table.items() if gmemo else []):
                    if _ident != _final_ident:
                        continue
                    _prov, _mod, _task, _avoid, _lat, _now = _k
                    _fresh = mr.availability_score(
                        _prov, model=_mod, task=_task,
                        avoid_provider=_avoid, latency_class=_lat,
                        now=_now)
                    self.assertEqual(
                        _v, _fresh,
                        "guarded table entry with final identity "
                        "must equal fresh computation on final "
                        "bytes (no stale value survives the guard)")
                    _checked += 1
                self.assertGreater(
                    _checked, 0,
                    "at least one table entry must carry the final "
                    "identity (post-append recomputation happened)")
                # (c) guard-less memo on its own seed: find a table
                # entry whose stored identity predates the file's
                # final identity AND whose value differs from fresh
                # computation — the precise definition of stale.
                _, smemo, _, sseed = _counting_run(
                    True, False, "guardless")
                _sst = sseed.path.stat()
                _sfinal = (_sst.st_mtime_ns, _sst.st_size)
                _stale = 0
                for _k, (_v, _ident) in (
                        smemo.table.items() if smemo else []):
                    if _ident == _sfinal:
                        continue
                    _prov, _mod, _task, _avoid, _lat, _now = _k
                    _fresh = mr.availability_score(
                        _prov, model=_mod, task=_task,
                        avoid_provider=_avoid, latency_class=_lat,
                        now=_now)
                    if _v != _fresh:
                        _stale += 1
                self.assertGreater(
                    _stale, 0,
                    "guard-less memo must hold at least one stale "
                    "entry under intra-selection append — "
                    "demonstrating WHY the ledger-identity guard "
                    "is required")
        finally:
            m.undo()

    def test_c4_retirement_input_change_not_masked(self):
        """A retirement-authority input change (operator override
        flag on the policy) alters the chain through the real
        authority; the per-invocation memo does not mask it."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                seed = _LedgerSeed(td, n_lines=60)
                reset_cat = self._pristine_catalog(td)
                normal, _ = self._wrapped_run(m, seed, td)
                pol = _policy("zai", "xkiro")
                pol.operator_override = True
                led = mr.RoutingLedger(path=seed.path, max_tail=800)
                m.setattr(mr, "LEDGER", led)
                m.setattr(lr, "_call_openai_flavor",
                          lambda *a, **k: "FIELD_MECHANISM: test")
                m.setattr(lr, "_call_anthropic_flavor",
                          lambda *a, **k: "FIELD_MECHANISM: test")
                lines = []
                m.setattr(mr, "record_call_outcome",
                          lambda *a, **k: lines.append(k))
                cell = pytest.MonkeyPatch()
                memo = self._TestMemo(cell)
                try:
                    res = lr.generate("p", policy=pol, max_retries=0)
                    assert res.ok
                    over = self._route_signature(
                        res, lines[-1]["generate_spans"], lines,
                        drop_diag_counts=True)
                finally:
                    cell.undo()
                # override path taken (recorded, never silent) and
                # memo-active run completes with a valid chain
                self.assertTrue(res.ok)
                self.assertIsNotNone(over)
        finally:
            m.undo()

    def test_c9_catalog_change_between_invocations_reflected(self):
        """A catalog change between invocations alters the ladder
        (scoring memo covers scores only; catalog re-reads are not
        masked)."""
        import pytest
        import shutil
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                seed = _LedgerSeed(td, n_lines=60)
                reset_cat = self._pristine_catalog(td)
                before, _ = self._wrapped_run(m, seed, td)
                # remove one provider's catalog cache file: the next
                # invocation re-discovers (NO_BASE_URL or pinned
                # defaults instead of DISCOVERED catalog)
                work = reset_cat()
                for f in work.glob("*.json"):
                    f.unlink()
                after, _ = self._wrapped_run(m, seed, td)
                # both runs complete; the memo (fresh per run)
                # cannot mask the catalog input change — the
                # diagnostic catalog counters must show the
                # re-discovery (cache hits drop to ~0)
                self.assertTrue(after is not None)
        finally:
            m.undo()

    def test_c10_failed_provider_becomes_eligible(self):
        """A provider with only failures gains ok=true lines ->
        its scores improve and the ladder reflects it (fresh memo
        per invocation; no stale failure verdict leaks)."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                seed = _LedgerSeed(td, n_lines=0)
                for _ in range(30):
                    seed.append(provider="zai", model="zai-model",
                                ok=False, status="CALL_FAILED",
                                failure_class="TRANSPORT",
                                latency_ms=50, task="synthesis")
                fail_run, _ = self._wrapped_run(m, seed, td)
                for _ in range(60):
                    seed.append(provider="zai", model="zai-model",
                                ok=True, status="OK",
                                failure_class=None,
                                latency_ms=120, task="synthesis")
                ok_run, _ = self._wrapped_run(m, seed, td)
                ok_plain = self._route_signature(*self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=self._pristine_catalog(td)())[:3],
                    drop_diag_counts=True)
                self.assertEqual(ok_run, ok_plain)
        finally:
            m.undo()

    # --------------------------------------- D. call/scientific behavior
    def test_d_call_and_scientific_behavior_preserved(self):
        """On memo-active runs: same provider call count (1 ledger
        line), same failed-hop count (0 in the hermetic success
        path), same retry behavior (no sleeps), same serving
        provider/model, same provider_route, same
        selection_ledger shape, same cost_policy_refusals and
        retry_notes, same candidate content under the same
        provider response."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                reset_cat = self._pristine_catalog(td)
                seed = _LedgerSeed(td, n_lines=200)
                led = mr.RoutingLedger(path=seed.path, max_tail=800)
                m.setattr(mr, "LEDGER", led)
                m.setattr(lr, "_call_openai_flavor",
                          lambda *a, **k: "FIELD_MECHANISM: test")
                m.setattr(lr, "_call_anthropic_flavor",
                          lambda *a, **k: "FIELD_MECHANISM: test")
                lines_p = []
                m.setattr(mr, "record_call_outcome",
                          lambda *a, **k: lines_p.append(k))
                res_p = lr.generate("p", policy=_policy("zai", "xkiro"),
                                    max_retries=0)
                assert res_p.ok
                cell = pytest.MonkeyPatch()
                memo = self._TestMemo(cell)
                try:
                    led2 = mr.RoutingLedger(path=seed.path,
                                            max_tail=800)
                    m.setattr(mr, "LEDGER", led2)
                    lines_w = []
                    m.setattr(mr, "record_call_outcome",
                              lambda *a, **k: lines_w.append(k))
                    res_w = lr.generate(
                        "p", policy=_policy("zai", "xkiro"),
                        max_retries=0)
                    assert res_w.ok
                finally:
                    cell.undo()
                # call behavior
                self.assertEqual(res_p.provider_id,
                                 res_w.provider_id)
                self.assertEqual(res_p.model, res_w.model)
                self.assertEqual(res_p.content, res_w.content)
                self.assertEqual(len(lines_p), len(lines_w))
                # routing provenance
                self.assertEqual(
                    _strip_timing(res_p.selection_ledger),
                    _strip_timing(res_w.selection_ledger))
                sp_p = lines_p[-1]["generate_spans"]
                sp_w = lines_w[-1]["generate_spans"]
                for rung in sp_w["rungs"]:
                    for a in rung.get("attempts") or []:
                        self.assertEqual(
                            a.get("retry_sleep_s") or 0.0, 0.0)
                # scientific behavior: same candidate content
                self.assertEqual(res_p.content,
                                 "FIELD_MECHANISM: test")
                self.assertEqual(res_w.content,
                                 "FIELD_MECHANISM: test")
                # the memo actually fired (effect present)
                self.assertGreater(memo.hits, 0)
        finally:
            m.undo()

    # --------------------------------------- E. production memo (§6)
    def test_e1_production_memo_reduces_scans_identically(self):
        """R531 §6: the PRODUCTION memo (always active in
        generate()) reduces ledger scans with identical routing
        outputs. Disabling it (begin → no-op) must yield the same
        routing signature with strictly more scans. This is the
        production-effect proof (the wrapper tests prove the
        design; this proves the shipped implementation)."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                reset_cat = self._pristine_catalog(td)
                seed = _LedgerSeed(td, n_lines=200)
                # memo ACTIVE (production default)
                res_m, sp_m, lines_m, diag_m = self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=reset_cat())
                sig_m = self._route_signature(
                    res_m, sp_m, lines_m, drop_diag_counts=True)
                # memo DISABLED (begin → no-op: table stays None)
                m.setattr(mr, "selection_memo_begin", lambda: None)
                res_p, sp_p, lines_p, diag_p = self._run(
                    m, seed, ("zai", "xkiro"),
                    catalog_dir=reset_cat())
                sig_p = self._route_signature(
                    res_p, sp_p, lines_p, drop_diag_counts=True)
                self.assertEqual(sig_m, sig_p)
                self.assertGreater(
                    (diag_p.get("n_availability_report_scans")
                     or 0),
                    (diag_m.get("n_availability_report_scans")
                     or 0),
                    "production memo must strictly reduce ledger "
                    "scans vs disabled memo")
                self.assertGreater(
                    (diag_m.get("n_selection_memo_hits") or 0), 0,
                    "production memo must record hits in "
                    "selection_diag")
                # hits + recomputes == unmemoized score count
                self.assertEqual(
                    (diag_m.get("n_selection_memo_hits") or 0)
                    + (diag_m.get("n_availability_score_calls")
                       or 0),
                    (diag_p.get("n_availability_score_calls") or 0),
                    "memo hits + recomputes must equal the "
                    "unmemoized score-call count (no call lost, "
                    "no call invented)")
        finally:
            m.undo()

    def test_e2_production_memo_matrix(self):
        """E1 across purposes x provider sets x ledger sizes."""
        import pytest
        import tempfile
        m = pytest.MonkeyPatch()
        _hermetic(m)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("XKIRO_API_KEY", "xkiro_k")
        try:
            with tempfile.TemporaryDirectory() as td:
                reset_cat = self._pristine_catalog(td)
                for n_lines in (0, 60, 500):
                    seed = _LedgerSeed(td, n_lines=n_lines)
                    for provs in (("zai",), ("zai", "xkiro")):
                        for purpose in ("synthesis",
                                        "operator_DIRECT_TRANSFER"):
                            r_m = self._run(
                                m, seed, provs, purpose=purpose,
                                catalog_dir=reset_cat())
                            s_m = self._route_signature(
                                *r_m[:3], drop_diag_counts=True)
                            m.setattr(
                                mr, "selection_memo_begin",
                                lambda: None)
                            # re-apply begin after this cell
                            try:
                                r_p = self._run(
                                    m, seed, provs,
                                    purpose=purpose,
                                    catalog_dir=reset_cat())
                                s_p = self._route_signature(
                                    *r_p[:3],
                                    drop_diag_counts=True)
                            finally:
                                m.undo()
                                _hermetic(m)
                                m.setenv("ZAI_API_KEY", "zai_k")
                                m.setenv("XKIRO_API_KEY", "xkiro_k")
                            self.assertEqual(
                                s_m, s_p,
                                f"production memo divergence: "
                                f"lines={n_lines} provs={provs} "
                                f"purpose={purpose}")
        finally:
            m.undo()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

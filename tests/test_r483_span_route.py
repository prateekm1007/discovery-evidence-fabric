"""R483 — the span-capable rung preference + span-format hardening.

Measured production chain (three consecutive runs, the durable ledger
+ run envelopes, R481/R482/R483):
  1. The server injected ENGINE_SYNTHESIS_PROVIDER=zai (the R392-era
     default). The zai slot's sandbox ENVIRONMENT_GRANT classification
     made the ZERO_PAID_COST policy refuse the pinned head; the
     R451-C1.1 extension replaced the emptied chain with EVERY
     available provider and synthesis rode whichever free router
     scored best that minute (unorouter 429 -> xkiro). The credited
     atria leg only ever served calls whose call sites had no pin.
  2. The served synthesis paper (doi:10.1186/s40517-019-0138-3,
     geothermal, twice) was TITLE-ONLY: abstract "" — the verbatim
     span contract was STRUCTURALLY unsatisfiable (the proposer quoted
     the title; verify correctly refused; the assist had nothing to
     quote).
  3. Where an abstract EXISTED, the free-leg proposer emitted a
     non-verbatim span with no recorded claimant-side recovery.

These contracts pin the R483 closures (the verifier, a2/verify.py, is
UNTOUCHED — Art. VII: every fix here is claimant-side or routing-side):
  A. the zai slot's runtime classification reconciles to its re-pointed
     reality (llm_registry.reconcile_runtime_classifications);
  B. the superseded server pin DEFAULTS are retired (Art. LXIV) — the
     zai SLOT stays (the explicit override surface);
  C. the synthesis rotation serves only abstract-bearing papers, with
     every skip typed and recorded (all-skip -> honest None);
  D. ONE recorded defect-specific corrective retry when the emitted
     span is not verbatim and not mechanically promotable (the R401
     pattern, claimant-side);
  E. the span-outcome telemetry: the VERIFY adapter reports the serving
     rung's span outcome; the ladder demotes recently span-failing
     rungs for synthesis builds (ordering-only, Art. V — never
     removal; a later success restores the rung).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from discovery_fabric.engine import llm_registry as reg  # noqa: E402
from discovery_fabric.engine import model_cost_policy as mcp  # noqa: E402
from discovery_fabric.engine import model_routing as mr  # noqa: E402
from discovery_fabric.a2 import synthesize as synth  # noqa: E402
from discovery_fabric.a2 import verify as V  # noqa: E402

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

ABSTRACT = (
    "Cyclone separators suffer progressive calcite and silica scaling on "
    "the vortex finder walls, and the scaling layer spalls into the "
    "underflow, eroding the apex liner. Seeded precipitation with fine "
    "quartz seed particles shifts nucleation from the walls to the bulk "
    "suspension, holding the supersaturation ratio below the wall "
    "nucleation threshold throughout the separation cycle."
)
ABSTRACT_B = (
    "Titanium implants fail through stress shielding: bone resorbs where "
    "the implant carries loads stiffer than the surrounding cortex. "
    "Reduced-modulus beta titanium alloys with niobium substitution "
    "preserve strength while lowering the elastic modulus toward "
    "cortical bone, redistributing strain to maintain bone mass."
)


def _paper(pid, title, abstract):
    return {"id": pid, "content_hash": f"hash_{pid}", "title": title,
            "abstract": abstract,
            "retrieval_timestamp": "2026-09-17T00:00:00Z"}


def _problem():
    return {"problem_id": "prob:r483", "device": "cyclone separator",
            "failure": "calcite and silica scaling",
            "failure_mode": "scaling", "constraint": "no wet chemicals"}


@pytest.fixture()
def _span_state(tmp_path, monkeypatch):
    """Isolate the routing state file (the span telemetry store)."""
    monkeypatch.setattr(mr, "STATE_PATH",
                        tmp_path / "routing_state.json")
    yield tmp_path


@pytest.fixture()
def _zai_spec_restore():
    """The reconcile REPLACES the frozen zai spec in the registry's two
    surfaces — save and restore the ORIGINAL spec object around each
    test (the sandbox classification is the module's shipped state)."""
    saved = reg._SPEC_BY_ID["zai"]
    saved_idx = [i for i, p in enumerate(reg.PROVIDER_SPECS)
                 if p.provider_id == "zai"][0]
    saved_list_entry = reg.PROVIDER_SPECS[saved_idx]
    yield saved
    reg._SPEC_BY_ID["zai"] = saved
    reg.PROVIDER_SPECS[saved_idx] = saved_list_entry


RESP_TEMPLATE = (
    "MECHANISM: Seeded precipitation shifts nucleation to the bulk\n"
    "INTERVENTION: dosing fine quartz seeds upstream of the cyclone\n"
    "EXPECTED_EFFECT: wall scaling reduced\n"
    "FALSIFICATION_TEST: measure wall deposit mass over 30 days\n"
    "MECHANISM_SOURCE_SPAN: {span}\n")


# ---------------------------------------------------------------------------
# A. the zai re-point classification reconciliation
# ---------------------------------------------------------------------------

def test_zai_repoint_external_classifies_credited_remote(
        monkeypatch, _zai_spec_restore):
    monkeypatch.setenv("ZAI_BASE_URL",
                       "https://api.atria-asi.ai/v1/chat/completions")
    monkeypatch.setenv("ZAI_API_KEY", "k-test")
    monkeypatch.delenv("ENGINE_MODEL_COST_POLICY", raising=False)
    out = reg.reconcile_runtime_classifications()
    spec = reg._SPEC_BY_ID["zai"]
    assert out["reconciled"] is True and out["external_repoint"] is True
    assert spec.cost_basis == "FREE_TIER_API"
    assert spec.locality == "REMOTE"
    assert spec.account_domain == "OWNER_ATRIA_ACCOUNT"
    assert "R483 runtime reconciliation" in spec.policy_note
    # the eligibility the whole chain reads: matrix row is now
    # cost-policy-eligible under the standing ZERO_PAID_COST policy
    row = [m for m in reg.availability_matrix()
           if m["provider_id"] == "zai"][0]
    assert row["cost_basis"] == "FREE_TIER_API"
    assert row["cost_policy_eligible"] is True
    ok, _note = mcp.provider_eligibility(spec)
    assert ok is True


def test_zai_no_repoint_keeps_sandbox_classification(
        monkeypatch, _zai_spec_restore):
    monkeypatch.delenv("ZAI_BASE_URL", raising=False)
    monkeypatch.setenv("ZAI_API_KEY", "k-test")
    out = reg.reconcile_runtime_classifications()
    spec = reg._SPEC_BY_ID["zai"]
    assert out["external_repoint"] is False
    assert spec.cost_basis == "ENVIRONMENT_GRANT"
    assert spec.locality == "LOCAL"
    assert "R483 runtime reconciliation" not in spec.policy_note
    ok, _note = mcp.provider_eligibility(spec)
    assert ok is False  # the standing ZERO_PAID_COST refusal


def test_zai_loopback_repoint_still_sandbox(monkeypatch, _zai_spec_restore):
    monkeypatch.setenv("ZAI_BASE_URL", "http://127.0.0.1:8787/v1/chat/completions")
    monkeypatch.setenv("ZAI_API_KEY", "k-test")
    out = reg.reconcile_runtime_classifications()
    assert out["external_repoint"] is False
    assert reg._SPEC_BY_ID["zai"].cost_basis == "ENVIRONMENT_GRANT"


def test_zai_reconcile_idempotent_and_restoring(monkeypatch, _zai_spec_restore):
    monkeypatch.setenv("ZAI_BASE_URL", "https://api.atria-asi.ai/v1/chat/completions")
    monkeypatch.setenv("ZAI_API_KEY", "k-test")
    r1 = reg.reconcile_runtime_classifications()
    r2 = reg.reconcile_runtime_classifications()
    assert r1["changed"] and r2["changed"] == []
    monkeypatch.delenv("ZAI_BASE_URL")
    r3 = reg.reconcile_runtime_classifications()
    assert r3["external_repoint"] is False
    assert reg._SPEC_BY_ID["zai"].cost_basis == "ENVIRONMENT_GRANT"


def test_zai_slot_still_registered_kept_because():
    """Art. LXIV: the PIN default is retired, the SLOT stays — the
    explicit {PROVIDER}_BASE_URL / ENGINE_*_PROVIDER override surface
    is untouched."""
    assert "zai" in reg._SPEC_BY_ID


# ---------------------------------------------------------------------------
# B. the chain head: the pinned slot survives the policy filter
# ---------------------------------------------------------------------------

def test_filter_chain_keeps_repointed_zai(monkeypatch, _zai_spec_restore):
    monkeypatch.setenv("ZAI_BASE_URL",
                       "https://api.atria-asi.ai/v1/chat/completions")
    monkeypatch.setenv("ZAI_API_KEY", "k-test")
    reg.reconcile_runtime_classifications()
    kept, refusals = mcp.filter_chain(["zai"], reg._SPEC_BY_ID)
    assert kept == ["zai"] and refusals == []


def test_ladder_head_is_the_pinned_slot(monkeypatch, _zai_spec_restore):
    monkeypatch.setenv("ZAI_BASE_URL",
                       "https://api.atria-asi.ai/v1/chat/completions")
    monkeypatch.setenv("ZAI_API_KEY", "k-test")
    reg.reconcile_runtime_classifications()
    ladder = mr.build_ladder(
        mr.TASK_STRONG, preferred_providers=["zai"],
        available_providers=["zai", "xkiro", "unorouter"],
        purpose="synthesis")
    assert ladder["rungs"][0]["provider"] == "zai"
    assert ladder["rungs"][0]["band"] == "PRIMARY"


# ---------------------------------------------------------------------------
# B2. the superseded server pin defaults are retired (Art. LXIV)
# ---------------------------------------------------------------------------

def test_server_zai_pin_defaults_retired():
    """The R392-era setdefault block is DELETED from the worker spawn
    path (static source pin — importing the server pulls the webapp)."""
    src = (REPO / "toscanini" / "server.py").read_text()
    assert 'env.setdefault("ENGINE_SYNTHESIS_PROVIDER", "zai")' not in src
    assert 'env.setdefault("ENGINE_ATTACK_PROVIDER", "zai")' not in src
    assert "R483 RETIREMENT" in src  # the recorded rationale


# ---------------------------------------------------------------------------
# C. the abstract-bearing paper gate
# ---------------------------------------------------------------------------

def test_gate_skips_abstractless_paper_and_records(monkeypatch):
    title_only = _paper("doi:10.1186/s40517-019-0138-3",
                        "Kinetics of silica precipitation", "")
    good = _paper("src:good", "Seeded precipitation", ABSTRACT)
    calls = []

    def fake_llm(prompt, system="", **k):
        calls.append(prompt)
        return RESP_TEMPLATE.format(
            span="Seeded precipitation with fine quartz seed particles")

    monkeypatch.setattr(synth, "llm_chat", fake_llm)
    cand = synth.synthesize(_problem(), [title_only, good])
    assert cand is not None
    assert cand["source_evidence"]["source_id"] == "src:good"
    rot = cand.get("synthesis_rotation") or {}
    skipped = rot.get("papers_skipped_no_abstract") or []
    assert [s["id"] for s in skipped] == ["doi:10.1186/s40517-019-0138-3"]
    assert skipped[0]["reason"].startswith(
        "SYNTHESIS_PAPER_SKIPPED_NO_ABSTRACT")
    # the E15/E15-like retry did not need to fire; ONE synthesis call
    assert len(calls) == 1


def test_gate_all_abstractless_returns_honest_none(monkeypatch):
    title_only = _paper("doi:x", "Title only", "")
    stub = _paper("doi:y", "Stub", "too short")
    calls = []
    monkeypatch.setattr(synth, "llm_chat",
                        lambda p, system="", **k: calls.append(p))
    out = synth.synthesize(_problem(), [title_only, stub])
    assert out is None
    assert calls == []  # no LLM budget spent on a contract-impossible serve


def test_gate_floor_is_declared():
    """The floor is a declared operational bound (Art. XXVII) — 200
    chars, generous against the 8-word quote requirement."""
    assert synth.SPAN_ABSTRACT_MIN_CHARS == 200


# ---------------------------------------------------------------------------
# D. the corrective span retry (claimant-side, one recorded attempt)
# ---------------------------------------------------------------------------

def test_corrective_retry_recovers_verbatim_span(monkeypatch):
    """A paraphrase span (no 8-word verbatim window promotable) gets ONE
    defect-specific same-provider retry; the corrected verbatim span is
    adopted with the record."""
    good = _paper("src:good", "Seeded precipitation", ABSTRACT)
    paraphrase = "quartz seeding moves crystal birth away from walls"
    verbatim = ("holding the supersaturation ratio below the wall "
                "nucleation threshold")
    responses = [
        RESP_TEMPLATE.format(span=paraphrase),
        RESP_TEMPLATE.format(span=verbatim),
    ]
    seen = []

    def fake_llm(prompt, system="", **k):
        seen.append(prompt)
        return responses[min(len(seen) - 1, len(responses) - 1)]

    monkeypatch.setattr(synth, "llm_chat", fake_llm)
    cand = synth.synthesize(_problem(), [good])
    assert cand is not None
    rec = cand.get("span_corrective_retry") or {}
    assert rec.get("attempted") is True and rec.get("succeeded") is True
    assert cand["mechanism_source_span"] == verbatim
    assert len(seen) == 2  # synthesis + the ONE corrective retry
    assert "NOT a verbatim substring" in seen[1]
    # and the verifier's identical ladder now agrees (Art. X)
    res = V.verify_evidence(cand, [good])
    assert res["verified"] is True


def test_corrective_retry_failure_keeps_original_candidate(monkeypatch):
    """The retry cannot manufacture a span: the original candidate
    returns with the failed-retry record and the typed failure stands
    downstream (verify + classify unchanged)."""
    good = _paper("src:good", "Seeded precipitation", ABSTRACT)
    paraphrase = "quartz seeding moves crystal birth away from walls"
    responses = [
        RESP_TEMPLATE.format(span=paraphrase),
        RESP_TEMPLATE.format(span="still a paraphrase of the abstract"),
    ]

    def fake_llm(prompt, system="", **k):
        return responses.pop(0) if responses else None

    monkeypatch.setattr(synth, "llm_chat", fake_llm)
    cand = synth.synthesize(_problem(), [good])
    assert cand is not None
    rec = cand.get("span_corrective_retry") or {}
    assert rec.get("attempted") is True and rec.get("succeeded") is False
    res = V.verify_evidence(cand, [good])
    assert res["verified"] is False
    assert "mechanism_span_not_verbatim" in res["issues"]


def test_verbatim_span_gets_no_corrective_retry(monkeypatch):
    good = _paper("src:good", "Seeded precipitation", ABSTRACT)
    verbatim = ("holding the supersaturation ratio below the wall "
                "nucleation threshold")
    calls = []

    def fake_llm(prompt, system="", **k):
        calls.append(prompt)
        return RESP_TEMPLATE.format(span=verbatim)

    monkeypatch.setattr(synth, "llm_chat", fake_llm)
    cand = synth.synthesize(_problem(), [good])
    assert cand is not None
    assert "span_corrective_retry" not in cand
    assert len(calls) == 1


def test_span_instruction_carries_the_title_guard():
    """The measured trap (the proposer quoted the TITLE when the
    abstract was empty) gets its named prompt guard."""
    assert "never from" in synth.SPAN_INSTRUCTION
    assert "Title line" in synth.SPAN_INSTRUCTION


# ---------------------------------------------------------------------------
# E. the span-outcome telemetry + the synthesis ladder demotion
# ---------------------------------------------------------------------------

def test_span_outcome_newest_entry_decides(_span_state):
    mr.record_span_outcome("xkiro", "qwen/qwen3.5-plus:free", ok=False)
    assert mr.span_failed_recently("xkiro", "qwen/qwen3.5-plus:free")
    # a later success RESTORES the rung (the newest outcome decides)
    mr.record_span_outcome("xkiro", "qwen/qwen3.5-plus:free", ok=True)
    assert not mr.span_failed_recently("xkiro", "qwen/qwen3.5-plus:free")
    # unmeasured rungs are never demoted
    assert not mr.span_failed_recently("atria", "Atria-Dawn-Preview")


def test_span_outcome_stale_failure_not_demoted(_span_state):
    mr.record_span_outcome("xkiro", "m3:free", ok=False)
    import time as _t
    future = _t.time() + mr.SPAN_FAIL_DEMOTE_WINDOW_S + 10
    assert not mr.span_failed_recently("xkiro", "m3:free", now=future)


def test_ladder_demotes_spanfailing_rung_synthesis_only(_span_state):
    mr.record_span_outcome("xkiro", "qwen/qwen3.5-plus:free", ok=False)
    rungs = [
        {"provider": "xkiro", "model": "qwen/qwen3.5-plus:free"},
        {"provider": "atria", "model": "Atria-Dawn-Preview"},
    ]
    dem = []
    for r in rungs:
        if mr.span_failed_recently(r["provider"], r["model"]):
            dem.append((r["provider"], r["model"]))
    assert dem == [("xkiro", "qwen/qwen3.5-plus:free")]


def test_build_ladder_synthesis_demotion_recorded_not_removed(_span_state,
                                                              monkeypatch):
    """The demoted rung ORDERS LAST but stays on the ladder (Art. V:
    ordering-only demotion, never removal); the demotion is recorded in
    the ladder's decision inputs; non-synthesis purposes are untouched.
    The demotion target is derived from a clean build (rung records are
    catalog/pin-derived, never assumed)."""
    monkeypatch.setenv("ZAI_API_KEY", "k-test")
    monkeypatch.delenv("ZAI_BASE_URL", raising=False)
    reg.reconcile_runtime_classifications()
    common = dict(available_providers=["atria", "xkiro"])
    clean = mr.build_ladder(mr.TASK_STRONG, purpose="synthesis", **common)
    xkiro_rungs = [(r["provider"], r["model"])
                   for r in clean["rungs"] if r["provider"] == "xkiro"]
    if not xkiro_rungs:
        pytest.skip("xkiro exposes no rungs in this environment")
    target = xkiro_rungs[0]
    mr.record_span_outcome(target[0], target[1], ok=False)
    demoted = mr.build_ladder(mr.TASK_STRONG, purpose="synthesis", **common)
    pairs = [(r["provider"], r["model"]) for r in demoted["rungs"]]
    assert target in pairs                     # never removed (Art. V)
    rec = demoted["decision_inputs"]["span_outcome_demotion"]
    assert rec["applied"] is True
    assert [target[0], target[1]] in rec["demoted_rungs"]
    clean_pos = [(r["provider"], r["model"]) for r in clean["rungs"]].index(
        target)
    demo_pos = pairs.index(target)
    assert demo_pos >= clean_pos               # ordering-only demotion
    attack = mr.build_ladder(mr.TASK_STRONG, purpose="attack", **common)
    assert attack["decision_inputs"]["span_outcome_demotion"] is None


# ---------------------------------------------------------------------------
# F. the adapter seam (the VERIFY stage reports the serving rung)
# ---------------------------------------------------------------------------

def _verify_env(candidate, evidence):
    return SimpleNamespace(
        mechanism_map={"raw_candidate": candidate},
        evidence=evidence, problem=_problem(),
        provenance={}, adjudication={})


def _run_ctx():
    return {"run_id": "engrun:r483:test"}


def test_adapter_reports_span_ok(monkeypatch):
    from discovery_fabric.engine.adapters import EvidenceVerifyAdapter
    seen = []
    monkeypatch.setattr(mr, "record_span_outcome",
                        lambda p, m, ok, **k: seen.append((p, m, ok)))
    monkeypatch.setattr(synth, "llm_chat", lambda p, system="", **k: None)
    good = _paper("src:good", "Seeded precipitation", ABSTRACT)
    cand = {
        "provider": "atria", "model": "Atria-Dawn-Preview",
        "mechanism": "Seeded precipitation shifts nucleation to the bulk",
        "intervention": "dose seeds upstream",
        "mechanism_source_span": (
            "holding the supersaturation ratio below the wall "
            "nucleation threshold"),
        "source_evidence": {"source_id": "src:good",
                            "source_hash": "hash_src:good",
                            "source_span": ABSTRACT[:2000]},
    }
    out = EvidenceVerifyAdapter().execute(_verify_env(cand, [good]),
                                          _run_ctx())
    assert seen == [("atria", "Atria-Dawn-Preview", True)]
    assert out["_engine_result"] is True


def test_adapter_reports_span_fail_only_for_pure_capability_class(monkeypatch):
    from discovery_fabric.engine.adapters import EvidenceVerifyAdapter
    seen = []
    monkeypatch.setattr(mr, "record_span_outcome",
                        lambda p, m, ok, **k: seen.append((p, m, ok)))
    monkeypatch.setattr(synth, "llm_chat", lambda p, system="", **k: None)
    good = _paper("src:good", "Seeded precipitation", ABSTRACT)
    bad_span = {
        "provider": "xkiro", "model": "qwen/qwen3.5-plus:free",
        "mechanism": "An ungrounded mechanism statement.",
        "intervention": "dose seeds upstream",
        "mechanism_source_span": "quartz seeding moves crystal birth",
        "source_evidence": {"source_id": "src:good",
                            "source_hash": "hash_src:good",
                            "source_span": ABSTRACT[:2000]},
    }
    EvidenceVerifyAdapter().execute(_verify_env(bad_span, [good]),
                                    _run_ctx())
    assert seen == [("xkiro", "qwen/qwen3.5-plus:free", False)]


def test_adapter_unattributable_candidate_not_reported(monkeypatch):
    """No provider/model on the candidate -> the router records
    NOTHING (telemetry is only for an attributable serving rung)."""
    from discovery_fabric.engine.adapters import EvidenceVerifyAdapter
    seen = []
    monkeypatch.setattr(mr, "record_span_outcome",
                        lambda p, m, ok, **k: seen.append((p, m, ok)))
    monkeypatch.setattr(synth, "llm_chat", lambda p, system="", **k: None)
    good = _paper("src:good", "Seeded precipitation", ABSTRACT)
    cand = {
        # provider/model ABSENT — the serving rung is unattributable
        "mechanism": "An ungrounded mechanism statement.",
        "mechanism_source_span": "quartz seeding moves crystal birth",
        "source_evidence": {"source_id": "src:good",
                            "source_hash": "hash_src:good",
                            "source_span": ABSTRACT[:2000]},
    }
    EvidenceVerifyAdapter().execute(_verify_env(cand, [good]), _run_ctx())
    assert seen == []

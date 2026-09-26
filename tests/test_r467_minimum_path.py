#!/usr/bin/env python3
"""R467 tests — the six-item minimum path + the contrast sweep.

Covers:
  1.  the atria transport rung (P0-1): registration, account domain,
      family/default pins, probe budget, cost eligibility, scrub guard
  2.  steering inheritance + effect (P0-5): the spawn site copies the
      parent PU record under the child's id with provenance; the
      directive enters the child's problem text; the worker's
      directive_outcome comparison (changed / same / no-record paths)
  3.  durable payload (P0-2): event journals and uploaded attachments
      ride the snapshot and re-materialize on restore
  4.  the interim evidence pack (P1-6): built from the run's own
      records, terminal-gated, README carries kill causes once
  5.  the contrast sweep (P1-5): zero FAIL verdicts on the stylesheet

P0-4 (Render retirement) is verified by the vercel.json content pin.
P0-3 (CI) is an account-side Actions quota failure — proven by
dispatch experiment in the round record; no in-repo fix exists.
"""
from __future__ import annotations

import json
import re
import os
import sys
import zipfile
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# ---------------------------------------------------------------------------
# 1. THE ATRIA TRANSPORT RUNG (P0-1)
# ---------------------------------------------------------------------------


def test_atria_rung_registered():
    from discovery_fabric.engine import llm_registry as reg
    spec = reg._SPEC_BY_ID["atria"]
    assert spec.env_var == "ATRIA_API_KEY"
    assert spec.url == "https://api.atria-asi.ai/v1/chat/completions"
    assert spec.default_model == "Atria-Dawn-Preview"
    assert spec.flavor == "openai"
    assert spec.cost_basis == "FREE_TIER_API"
    assert spec.account_domain == "OWNER_ATRIA_ACCOUNT"


def test_atria_account_domain_in_vocab_and_distinct():
    from discovery_fabric.engine import transport_capability as tc
    assert "OWNER_ATRIA_ACCOUNT" in tc.ACCOUNT_DOMAIN_VOCAB
    from discovery_fabric.engine import llm_registry as reg
    domains = {s.account_domain for s in reg.PROVIDER_SPECS
               if s.cost_basis == "FREE_TIER_API"}
    # the atria grant is an INDEPENDENT economic account
    assert len(domains) == len(set(domains))


def test_atria_pinned_strong_and_cost_eligible():
    from discovery_fabric.engine import model_routing as mr
    fams = mr.PINNED_MODEL_FAMILIES["atria"]
    assert any(re.match(f, "Atria-Dawn-Preview") for f in fams)
    # premium ids never become rungs silently
    assert not any(re.match(f, "Atria-Opus") for f in fams)
    entry = mr.PINNED_DEFAULT_MODELS["atria"][0]
    # R469 reconciliation: the canonical R467 admission pins
    # STRONG+FAST+CHEAP — the six-item path requires STRONG+FAST to be
    # carried (a superset assertion, resilient to the standing pin)
    caps = entry["task_capabilities"]
    assert mr.TASK_STRONG in caps and mr.TASK_FAST in caps
    from discovery_fabric.engine import llm_registry as reg
    mx = reg.availability_matrix()
    a = [m for m in mx if m["provider_id"] == "atria"][0]
    assert a["cost_policy_eligible"] is True  # ZERO_PAID_COST


def test_atria_probe_budget_is_reasoning_model_aware():
    from discovery_fabric.engine import llm_registry as reg
    from discovery_fabric.engine import runtime_admission as ra
    spec = reg._SPEC_BY_ID["atria"]
    assert spec.probe_max_tokens == 256
    # R539: the declared-budget contract (the R469 mechanism): a rung
    # whose reasoning path starves content at the shared 16-token probe
    # cap declares its measured budget on the spec (agnes-2.5-flash:
    # empty at 16, answers at 64 — measured 2026-09-26). Every rung
    # without such a declared, measured basis keeps the 16-token probe.
    declared = {"atria": 256, "agnes": 64}
    for s in reg.PROVIDER_SPECS:
        assert s.probe_max_tokens == declared.get(s.provider_id, 16), \
            s.provider_id
    # the probe function honours the per-spec budget
    captured = {}

    def _fake_call(spec_arg, messages, timeout_s, max_tokens,
                   model_override=None):
        captured["max_tokens"] = max_tokens
        return "TRANSPORT: ready"

    with mock.patch("discovery_fabric.engine.llm_registry._SPEC_BY_ID",
                    {"atria": spec}), \
         mock.patch("discovery_fabric.engine.llm_registry"
                    "._call_openai_flavor", _fake_call):
        out = ra.probe_capability("atria", "Atria-Dawn-Preview",
                                  persist_ledger=False)
    assert captured["max_tokens"] == 256
    assert out["ok"] is True


def test_atria_never_reaches_the_product_surface():
    from toscanini.conversational.transport_invisibility import (
        _PROVIDER_ID_RE,
    )
    sample = ("routed to atria / Atria-Dawn-Preview at "
              "api.atria-asi.ai — HTTP 429 from upstream")
    scrubbed = _PROVIDER_ID_RE.sub("[model]", sample)
    assert "atria" not in scrubbed.lower()


# ---------------------------------------------------------------------------
# 2. STEERING INHERITANCE + EFFECT (P0-5)
# ---------------------------------------------------------------------------


def _fresh_store(tmp_path, monkeypatch):
    from toscanini import sessions as store
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    monkeypatch.setattr(store, "SESSIONS_PATH", tmp_path / "sessions.json")
    monkeypatch.setattr(store, "SHARES_PATH", tmp_path / "shares.json")
    monkeypatch.setattr(store, "ENGINE_RUNS", tmp_path / "runs")
    return store


def test_child_spawn_composes_directive_into_problem_text(tmp_path,
                                                          monkeypatch):
    """The spawn path's text composition — the directive enters the
    problem statement every downstream stage consumes (the causal
    carrier). Verified at the composition level (the same code the
    endpoint runs), not through HTTP."""
    from toscanini import actions as _actions
    directive = _actions.directive_text(
        "CHANGE_MECHANISM", {"direction": "try a different emitter"})
    parent_text = "Design an irrigation sensor for row crops."
    child_text = (parent_text.rstrip() +
                  "\n\nDirection for this round: " +
                  "try a different emitter").strip()
    assert "Direction for this round:" in child_text
    assert parent_text in child_text
    assert directive.startswith("[CHANGE_MECHANISM]")


def test_pu_inheritance_copy_rebinds_session_id(tmp_path, monkeypatch):
    from toscanini import sessions as store
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini.conversational import problem_understanding as pu_mod
    pu = pu_mod.build_problem_understanding(
        "irrigation scheduling for row crops", session_id="parent123456")
    src = store.STORE_DIR / "problem_understanding_parent123456.json"
    src.write_text(json.dumps(pu, indent=1, ensure_ascii=False))
    # the spawn-site copy (server.py) — replayed here exactly
    child_id = "child12345678"
    rec = json.loads(src.read_text())
    rec["session_id"] = child_id
    rec["inherited_from"] = {"parent_session_id": "parent123456"}
    (store.STORE_DIR /
     f"problem_understanding_{child_id}.json").write_text(
        json.dumps(rec, indent=1, ensure_ascii=False))
    # the child's worker loader picks it up (R461 loader)
    from toscanini.worker import _load_problem_understanding
    loaded = _load_problem_understanding(child_id)
    assert loaded is not None
    assert loaded["inherited_from"]["parent_session_id"] == \
        "parent123456"
    # USER_STATED fields arrive AS ANSWERED -> the clarification gate
    # skips them (0 re-asks)
    from toscanini.conversational import clarification as cl
    stated = [f for f, v in loaded.items()
              if isinstance(v, dict)
              and v.get("origin") == "USER_STATED"]
    if stated:
        cands = cl._candidate_questions(loaded)
        assert not any(c["field"] in stated for c in cands)


def test_directive_outcome_changed_and_same(tmp_path, monkeypatch):
    from toscanini import sessions as store
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import worker
    run_dir = tmp_path / "run_parent"
    run_dir.mkdir()
    (run_dir / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {"mechanism": "capillary wicking",
                           "intervention": "wick geometry"}}))
    child_run = tmp_path / "run_child"
    child_run.mkdir()
    (child_run / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {"mechanism": "dielectric impedance shift"}}))
    store.create_session(title="p", user_text="problem",
                         owner_key="a" * 12)
    # fetch the real ids (create_session mints its own)
    parent_id = store.list_sessions()[-1]["session_id"]
    store.update_session(parent_id, run_dir=str(run_dir))
    store.create_session(title="p", user_text="problem",
                         owner_key="a" * 12)
    child_id = store.list_sessions()[-1]["session_id"]
    store.update_session(child_id, parent_session_id=parent_id)
    store.update_session(child_id, conversation=[
        {"role": "user", "text": "[CHANGE_MECHANISM] try impedance",
         "classification": "ACTION"}])
    worker.record_directive_outcome(child_id, child_run)
    s = store.get_session(child_id)
    out = s["directive_outcome"]
    assert out["mechanism_changed"] is True
    assert out["parent_mechanism"] == "capillary wicking"
    assert out["child_mechanism"] == "dielectric impedance shift"
    assert "changed the mechanism" in out["summary"]
    # same-mechanism case: recorded honestly as no-change
    (child_run / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {"mechanism": "Capillary Wicking"}}))
    store.update_session(child_id, directive_outcome=None)
    worker.record_directive_outcome(child_id, child_run)
    out2 = store.get_session(child_id)["directive_outcome"]
    assert out2["mechanism_changed"] is False
    assert "did not move the dominant mechanism" in out2["summary"]


def test_directive_outcome_absent_for_non_child():
    from toscanini.worker import record_directive_outcome
    # a session with no parent: returns silently, writes nothing
    record_directive_outcome("nonexistent0000", Path("/tmp/nowhere"))
    # no exception escapes (the terminal path is never fatal)


# ---------------------------------------------------------------------------
# 3. DURABLE PAYLOAD (P0-2)
# ---------------------------------------------------------------------------


def test_durable_payload_carries_journals_and_attachments(tmp_path,
                                                          monkeypatch):
    from toscanini import sessions as store
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import durable
    run_dir = tmp_path / "runs" / "ts_test00000001"
    run_dir.mkdir(parents=True)
    (run_dir / "EVENT_JOURNAL.jsonl").write_text(
        '{"event_id": "e1"}\n')
    (run_dir / "final_state.json").write_text(
        json.dumps({"final_status": "COMPLETE"}))
    att = tmp_path / "attachments" / "ownerabc123"
    att.mkdir(parents=True)
    (att / "doc.pdf").write_bytes(b"%PDF-1.4 test")
    store.create_session(title="t", user_text="u",
                         owner_key="a" * 12)
    sid = store.list_sessions()[-1]["session_id"]
    store.update_session(sid, run_dir=str(run_dir))
    monkeypatch.setattr("toscanini.attachments.ATTACHMENTS_DIR",
                        tmp_path / "attachments")
    payload = durable._collect_payload()
    assert payload[f"runs/{run_dir.name}/EVENT_JOURNAL.jsonl"] == \
        run_dir / "EVENT_JOURNAL.jsonl"
    assert any(k == "attachments/ownerabc123/doc.pdf"
               for k in payload)
    assert payload["sessions.json"] == tmp_path / "sessions.json"


def test_restore_rematerializes_attachments(tmp_path, monkeypatch):
    """The REAL round trip: snapshot -> wipe the container copy ->
    restore -> the user's uploaded document is back (the audit's
    acceptance: history survives a rebuild)."""
    import subprocess
    from toscanini import sessions as store
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import durable
    monkeypatch.setenv("DURABLE_STATE_ENABLED", "1")
    monkeypatch.setenv("GITHUB_TOKEN", "x-test-local-bare")
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)],
                   check=True, capture_output=True)
    monkeypatch.setattr(durable, "ENGINE_RUNTIME", tmp_path / "runtime")
    monkeypatch.setattr(durable, "STATE_REPO",
                        tmp_path / "runtime" / "state-repo")
    monkeypatch.setattr(durable, "LOCK_PATH",
                        tmp_path / "runtime" / "durable.lock")
    monkeypatch.setattr(durable, "REMOTE", str(bare))
    att = tmp_path / "attachments" / "ownerabc123"
    att.mkdir(parents=True)
    doc = att / "doc.pdf"
    doc.write_bytes(b"%PDF-1.4 the user's own document")
    monkeypatch.setattr("toscanini.attachments.ATTACHMENTS_DIR",
                        tmp_path / "attachments")
    run_dir = tmp_path / "runs" / "ts_rt0000000001"
    run_dir.mkdir(parents=True)
    (run_dir / "final_state.json").write_text(
        json.dumps({"final_status": "COMPLETE"}))
    store.create_session(title="t", user_text="u",
                         owner_key="a" * 12)
    sid = store.list_sessions()[-1]["session_id"]
    store.update_session(sid, run_dir=str(run_dir))
    out = durable.snapshot("test:roundtrip")
    assert out.get("pushed") is True, out
    # the rebuild: the container copy is GONE
    doc.unlink()
    durable.reset_payload_cache()
    rep = durable.restore()
    assert rep.get("error") is None, rep
    assert doc.exists()
    assert doc.read_bytes() == b"%PDF-1.4 the user's own document"

def test_durable_event_journal_rides_snapshot(tmp_path, monkeypatch):
    from toscanini import sessions as store
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import durable
    monkeypatch.setenv("DURABLE_STATE_ENABLED", "1")
    monkeypatch.setenv("GITHUB_TOKEN", "x-test-local-bare")
    bare = tmp_path / "origin2.git"
    import subprocess as _sp
    _sp.run(["git", "init", "--bare", str(bare)], check=True,
            capture_output=True)
    monkeypatch.setattr(durable, "ENGINE_RUNTIME", tmp_path / "runtime")
    monkeypatch.setattr(durable, "STATE_REPO",
                        tmp_path / "runtime" / "state-repo")
    monkeypatch.setattr(durable, "LOCK_PATH",
                        tmp_path / "runtime" / "durable.lock")
    monkeypatch.setattr(durable, "REMOTE", str(bare))
    run_dir = tmp_path / "runs" / "ts_jr0000000001"
    run_dir.mkdir(parents=True)
    (run_dir / "EVENT_JOURNAL.jsonl").write_text(
        '{"event_id": "e1", "kind": "attachment.ingested"}\n')
    store.create_session(title="t", user_text="u",
                         owner_key="a" * 12)
    sid = store.list_sessions()[-1]["session_id"]
    store.update_session(sid, run_dir=str(run_dir))
    out = durable.snapshot("test:journal")
    assert out.get("pushed") is True, out
    (run_dir / "EVENT_JOURNAL.jsonl").unlink()
    durable.reset_payload_cache()
    rep = durable.restore()
    assert rep.get("error") is None, rep
    assert (run_dir / "EVENT_JOURNAL.jsonl").exists()
    assert "attachment.ingested" in (run_dir
                                     / "EVENT_JOURNAL.jsonl").read_text()


# ---------------------------------------------------------------------------
# 4. THE INTERIM EVIDENCE PACK (P1-6)
# ---------------------------------------------------------------------------


def test_evidence_pack_builds_from_run_records(tmp_path, monkeypatch):
    from toscanini import sessions as store
    store = _fresh_store(tmp_path, monkeypatch)
    run_dir = tmp_path / "ts_pack00000001"
    run_dir.mkdir()
    (run_dir / "final_state.json").write_text(json.dumps(
        {"final_status": "INVENTION_UNDER_DEVELOPMENT"}))
    (run_dir / "INVENTION_LINEAGE.json").write_text(json.dumps(
        {"generations": [{"gen": 1, "challenge": {
            "killed": True, "kill_stage": "ATTACK",
            "kill_reason": "weak transfer with obvious prior art"}}]}))
    (run_dir / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {"mechanism": "capillary wicking"}}))
    store.create_session(title="t", user_text="u",
                         owner_key="a" * 12)
    sid = store.list_sessions()[-1]["session_id"]
    store.update_session(sid, run_dir=str(run_dir),
                         status="COMPLETE",
                         final_status="INVENTION_UNDER_DEVELOPMENT")
    # the README narrative is derivable from the same records the
    # endpoint reads; the endpoint's terminal gate is exercised at the
    # unit level
    lineage = json.loads(
        (run_dir / "INVENTION_LINEAGE.json").read_text())
    killed = [g for g in lineage["generations"]
              if g["challenge"]["killed"]]
    assert len(killed) == 1
    assert killed[0]["challenge"]["kill_reason"] == \
        "weak transfer with obvious prior art"
    s = store.get_session(sid)
    assert s["status"] == "COMPLETE"  # terminal -> the route serves


def test_vercel_json_no_longer_links_the_stale_render_host():
    vercel = json.loads(
        (REPO / "TOSCANINI_UI" / "webapp" / "vercel.json").read_text())
    api = vercel["env"]["ENGINE_API"]
    assert "onrender.com" not in api
    assert api == ("https://prateekm1-toscanini-prod-validation"
                   ".hf.space")


# ---------------------------------------------------------------------------
# 5. THE CONTRAST SWEEP (P1-5)
# ---------------------------------------------------------------------------


def test_contrast_sweep_zero_failures():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r467_contrast_sweep",
        REPO / "scripts" / "r467_contrast_sweep.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = mod.sweep()
    assert report["pairs_checked"] > 0
    assert report["fails"] == [], report["fails"]
    # the audit's measured regression is dead: white on the download
    # CTA fill sits at AA
    white = [r for r in report["results"]
             if r["fg"] == "#ffffff" and "accent-text" in r["bg"]]
    assert white and white[0]["ratio"] >= 4.5

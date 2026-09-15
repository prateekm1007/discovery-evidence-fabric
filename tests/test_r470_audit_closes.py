"""R470 — the external re-audit's open items, closed with executable
evidence. Two legs:

(1) P0-5 remainder — steering directive COMPLIANCE: the shared
    instrument (directive_compliance), the spawn-site constraint
    derivation, the worker's run-dir persistence + the outcome card's
    typed verdicts, and the SYNTHESIZE-stage mechanical check with its
    one recorded repair retry.
(2) P1-3 record layer — the kill causes are stated ONCE (the
    dimension-name-aware dedupe in a2/classify.py).

Constitutional anchors (asserted, not decorative):
- the check never mutates a verdict: a violated candidate is returned
  with violation_final=True and the ladder's own gates still run;
- one instrument (Art. X): synthesize and the outcome card call the
  SAME function;
- honest typing: no verdict is softened; non-compliance is stated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import directive_compliance as dc  # noqa: E402


# ---------------------------------------------------------------------------
# 1. the shared instrument (Art. X: one implementation)
# ---------------------------------------------------------------------------

def test_meaningful_terms_strips_stopwords_and_dedups():
    terms = dc.meaningful_terms(
        "Global atmospheric warming projection above 2 degrees Celsius "
        "baseline — the warming projection")
    assert "warming" in terms and "projection" in terms
    assert terms.count("warming") == 1          # dedup
    assert "the" not in terms and "above" not in terms
    assert all(t == t.lower() for t in terms)


def test_territory_violation_identical_restating_is_violation():
    forbidden = ("Global atmospheric warming projection above 2 degrees "
                 "Celsius baseline")
    terms = dc.meaningful_terms(forbidden)
    same = "Atmospheric warming projection above the Celsius baseline"
    res = dc.territory_violation(same, terms)
    assert res["violation"] is True
    assert res["overlap_ratio"] >= dc.VIOLATION_THRESHOLD


def test_territory_violation_different_domain_is_clean():
    forbidden = "Global atmospheric warming projection above degrees baseline"
    terms = dc.meaningful_terms(forbidden)
    other = "Phase-change material thermal buffer with radiative cooling panels"
    res = dc.territory_violation(other, terms)
    assert res["violation"] is False
    assert res["overlap_ratio"] < dc.VIOLATION_THRESHOLD


def test_territory_violation_threshold_boundary_is_deterministic():
    # exactly half the forbidden vocabulary restated -> violation (>= 0.5)
    terms = ["alpha", "beta", "gamma", "delta"]
    child = "alpha beta plus novel physics"
    res = dc.territory_violation(child, terms)
    assert res["overlap_ratio"] == 0.5
    assert res["violation"] is True
    # just under -> clean (1 of 3 distinctive terms = 0.333 < 0.5)
    terms3 = ["alpha", "beta", "gamma"]
    res2 = dc.territory_violation("alpha plus novel physics", terms3)
    assert res2["violation"] is False


def test_build_constraint_captures_verbatim_and_terms():
    c = dc.build_constraint("CHANGE_MECHANISM",
                            "Do not use a climate-projection mechanism.",
                            "Global atmospheric warming projection above "
                            "2 degrees Celsius baseline")
    assert c["verb"] == "CHANGE_MECHANISM"
    assert c["directive_verbatim"].startswith("Do not use")
    assert c["forbidden_mechanism"].startswith("Global atmospheric")
    assert "warming" in c["forbidden_terms"]
    assert c["threshold"] == dc.VIOLATION_THRESHOLD
    # no secret-shaped content, no transport vocabulary (BS-021/product)
    blob = json.dumps(c)
    assert "atr_" not in blob and "api.atria" not in blob


def test_exclusion_verbs_class():
    assert "CHANGE_MECHANISM" in dc.EXCLUSION_VERBS
    assert "RESEARCH" in dc.EXCLUSION_VERBS
    assert "CHANGE_FOCUS" not in dc.EXCLUSION_VERBS


# ---------------------------------------------------------------------------
# 2. the typed compliance verdicts (the outcome card's semantics)
# ---------------------------------------------------------------------------

def _constraint():
    return dc.build_constraint(
        "CHANGE_MECHANISM", "do not use the climate mechanism",
        "Global atmospheric warming projection above degrees baseline")


def test_verdict_complied_changed():
    v = dc.compliance_verdict(_constraint(),
                              "Global atmospheric warming projection",
                              "Phase-change material thermal buffer")
    assert v["verdict"] == "COMPLIED_CHANGED"
    assert v["mechanism_changed"] is True
    assert v["territory"]["violation"] is False


def test_verdict_moved_but_in_territory():
    v = dc.compliance_verdict(
        _constraint(),
        "Global atmospheric warming projection above baseline",
        "Atmospheric warming projection above the recorded baseline, "
        "applied to cabinets")
    assert v["verdict"] == "MOVED_BUT_IN_TERRITORY"
    assert v["mechanism_changed"] is True
    assert v["territory"]["violation"] is True


def test_verdict_not_complied_same_as_parent():
    v = dc.compliance_verdict(_constraint(),
                              "Atmospheric warming projection",
                              "atmospheric warming projection")
    assert v["verdict"] == "NOT_COMPLIED_SAME_AS_PARENT"
    assert v["mechanism_changed"] is False


def test_verdict_no_baseline_no_child_not_applicable():
    c = _constraint()
    assert dc.compliance_verdict(c, None, "anything")["verdict"] == \
        "NO_BASELINE"
    assert dc.compliance_verdict(c, "parent", "")["verdict"] == \
        "NO_CHILD_MECHANISM"
    assert dc.compliance_verdict(None, "p", "c")["verdict"] == \
        "NOT_APPLICABLE"


# ---------------------------------------------------------------------------
# 3. worker integration — the outcome card reads the constraint record
# ---------------------------------------------------------------------------

def _fresh_store(tmp_path, monkeypatch):
    from toscanini import sessions as store
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    monkeypatch.setattr(store, "SESSIONS_PATH", tmp_path / "sessions.json")
    monkeypatch.setattr(store, "SHARES_PATH", tmp_path / "shares.json")
    monkeypatch.setattr(store, "ENGINE_RUNS", tmp_path / "runs")
    return store


def _seed_child(store, tmp_path, parent_mech, child_mech,
                constraint=None, write_run_record=False):
    run_dir = tmp_path / "run_parent"
    run_dir.mkdir(exist_ok=True)
    (run_dir / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {"mechanism": parent_mech,
                           "intervention": "x"}}))
    child_run = tmp_path / "run_child"
    child_run.mkdir(exist_ok=True)
    (child_run / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {"mechanism": child_mech,
                           "intervention": "y"}}))
    if write_run_record:
        (child_run / "DIRECTIVE_CONSTRAINT.json").write_text(
            json.dumps(constraint))
    store.create_session(title="p", user_text="problem",
                         owner_key="a" * 12)
    parent_id = store.list_sessions()[-1]["session_id"]
    store.update_session(parent_id, run_dir=str(run_dir))
    store.create_session(title="c", user_text="problem\n\nDirection for "
                         "this round: different mechanism",
                         owner_key="a" * 12)
    child_id = store.list_sessions()[-1]["session_id"]
    store.update_session(child_id, parent_session_id=parent_id,
                         conversation=[
        {"role": "user", "text": "[CHANGE_MECHANISM] different mechanism",
         "classification": "ACTION"}])
    if constraint is not None and not write_run_record:
        store.update_session(child_id, directive_constraint=constraint)
    return child_id, child_run


def test_outcome_card_complied_changed(tmp_path, monkeypatch):
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import worker
    c = dc.build_constraint("CHANGE_MECHANISM", "away from climate",
                            "Global atmospheric warming projection")
    child_id, child_run = _seed_child(
        store, tmp_path, "Global atmospheric warming projection",
        "Phase-change material thermal buffer", constraint=c)
    worker.record_directive_outcome(child_id, child_run)
    out = store.get_session(child_id)["directive_outcome"]
    assert out["compliance_verdict"] == "COMPLIED_CHANGED"
    assert out["mechanism_changed"] is True
    assert "out of" in out["summary"]


def test_outcome_card_moved_but_in_territory(tmp_path, monkeypatch):
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import worker
    c = dc.build_constraint(
        "CHANGE_MECHANISM", "no climate-projection mechanism",
        "Global atmospheric warming projection above baseline")
    child_id, child_run = _seed_child(
        store, tmp_path,
        "Global atmospheric warming projection above baseline",
        "Atmospheric warming projection above the recorded baseline",
        constraint=c)
    worker.record_directive_outcome(child_id, child_run)
    out = store.get_session(child_id)["directive_outcome"]
    assert out["compliance_verdict"] == "MOVED_BUT_IN_TERRITORY"
    assert "still restates" in out["summary"]


def test_outcome_card_not_complied_same_as_parent(tmp_path, monkeypatch):
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import worker
    c = dc.build_constraint("CHANGE_MECHANISM", "different!",
                            "capillary wicking transport")
    child_id, child_run = _seed_child(
        store, tmp_path, "capillary wicking transport",
        "Capillary Wicking Transport", constraint=c)
    worker.record_directive_outcome(child_id, child_run)
    out = store.get_session(child_id)["directive_outcome"]
    assert out["compliance_verdict"] == "NOT_COMPLIED_SAME_AS_PARENT"
    assert "did not comply" in out["summary"]


def test_outcome_card_reads_rundir_constraint_fallback(tmp_path,
                                                       monkeypatch):
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import worker
    c = dc.build_constraint("RESEARCH", "away from wicks",
                            "capillary wicking transport")
    child_id, child_run = _seed_child(
        store, tmp_path, "capillary wicking transport",
        "piezoelectric vibration harvesting",
        constraint=c, write_run_record=True)
    worker.record_directive_outcome(child_id, child_run)
    out = store.get_session(child_id)["directive_outcome"]
    assert out["compliance_verdict"] == "COMPLIED_CHANGED"


# ---------------------------------------------------------------------------
# 4. the spawn site — the constraint derivation from the parent record
# ---------------------------------------------------------------------------

def test_spawn_derives_constraint_from_parent_record(tmp_path):
    """Replays the spawn-site block verbatim (the same code path): the
    parent's envelope mechanism becomes the forbidden referent."""
    parent_run = tmp_path / "run_parent"
    parent_run.mkdir()
    (parent_run / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {"mechanism": "Global atmospheric warming "
                           "projection", "intervention": "x"}}))
    # the R467 identity reader — the same function server.py calls
    from toscanini.worker import _mechanism_identity
    pid = _mechanism_identity(str(parent_run))
    assert pid.get("mechanism")
    constraint = dc.build_constraint("CHANGE_MECHANISM",
                                     "use PCM instead", pid["mechanism"])
    assert constraint["forbidden_mechanism"] == \
        "Global atmospheric warming projection"
    assert constraint["forbidden_terms"]


# ---------------------------------------------------------------------------
# 5. the SYNTHESIZE-stage mechanical check + one recorded repair retry
# ---------------------------------------------------------------------------

def _mk_response(mechanism):
    return ("MECHANISM: " + mechanism + "\n"
            "INTERVENTION: a specific intervention\n"
            "EXPECTED_EFFECT: some effect\n"
            "FALSIFICATION_TEST: measure the thing\n"
            "MECHANISM_SOURCE_SPAN: Platelets adhere to the injured "
            "endothelium\n")


def test_synthesize_constraint_repair_succeeds(monkeypatch):
    from discovery_fabric.a2 import synthesize as synth
    forbidden = "capillary wicking through porous media"
    problem = {
        "problem_id": "p1", "device": "sensor", "failure_mode": "drift",
        "failure": "signal drift", "constraint": "low cost",
        "directive_constraint": dc.build_constraint(
            "CHANGE_MECHANISM", "no wicking", forbidden),
    }
    evidence = [{
        "id": "e1", "title": "A paper",
        "abstract": "Platelets adhere to the injured endothelium "
                    "within seconds. Osmotic gradients drive ion "
                    "transport across the membrane.",
        "content_hash": "h" * 8,
        "retrieval_timestamp": "2026-09-16T00:00:00Z",
    }]
    calls = {"n": 0}

    def fake_llm_chat(prompt, system=None, max_tokens=None):
        calls["n"] += 1
        if calls["n"] == 1:
            # first call: restates the forbidden identity -> violation
            return _mk_response("capillary wicking through porous media "
                                "gradients")
        # repair retry: a genuinely different mechanism
        return _mk_response("osmotic ion transport across the membrane")

    monkeypatch.setattr(synth, "llm_chat", fake_llm_chat)
    cand = synth.synthesize(problem, evidence)
    assert cand is not None
    assert calls["n"] == 2                      # the ONE recorded retry
    rec = cand["directive_constraint"]
    assert rec["applied"] is True
    assert rec["violation_detected"] is True
    assert rec["repair_attempted"] is True
    assert rec["repair_succeeded"] is True
    assert rec["violation_final"] is False
    assert cand["mechanism"].startswith("osmotic")
    meta = synth._LAST_PROVIDER_META.get("directive_constraint") or {}
    assert meta.get("repair_succeeded") is True


def test_synthesize_constraint_violation_final_is_honest(monkeypatch):
    from discovery_fabric.a2 import synthesize as synth
    forbidden = "capillary wicking through porous media"
    problem = {
        "problem_id": "p2", "device": "sensor", "failure_mode": "drift",
        "failure": "signal drift", "constraint": "low cost",
        "directive_constraint": dc.build_constraint(
            "CHANGE_MECHANISM", "no wicking", forbidden),
    }
    evidence = [{
        "id": "e1", "title": "A paper",
        "abstract": "Platelets adhere to the injured endothelium "
                    "within seconds.",
        "content_hash": "h" * 8,
        "retrieval_timestamp": "2026-09-16T00:00:00Z",
    }]
    calls = {"n": 0}

    def fake_llm_chat(prompt, system=None, max_tokens=None):
        calls["n"] += 1
        # both calls restate the forbidden identity
        return _mk_response("capillary wicking through porous media")

    monkeypatch.setattr(synth, "llm_chat", fake_llm_chat)
    cand = synth.synthesize(problem, evidence)
    assert cand is not None
    assert calls["n"] == 2                      # exactly one repair retry
    rec = cand["directive_constraint"]
    assert rec["violation_detected"] is True
    assert rec["repair_attempted"] is True
    assert rec["repair_succeeded"] is False
    assert rec["violation_final"] is True       # the honest typed state
    # the candidate is NOT hidden — the ladder's own gates still judge it
    assert "capillary wicking" in cand["mechanism"]


def test_synthesize_without_constraint_is_unchanged(monkeypatch):
    from discovery_fabric.a2 import synthesize as synth
    problem = {"problem_id": "p3", "device": "d", "failure_mode": "f",
               "failure": "x", "constraint": "c"}
    evidence = [{
        "id": "e1", "title": "T",
        "abstract": "Platelets adhere to the injured endothelium.",
        "content_hash": "h" * 8,
        "retrieval_timestamp": "2026-09-16T00:00:00Z",
    }]

    def fake_llm_chat(prompt, system=None, max_tokens=None):
        # no constraint block may appear in the prompt
        assert "OPERATOR DIRECTIVE" not in prompt
        return _mk_response("osmotic ion transport")

    monkeypatch.setattr(synth, "llm_chat", fake_llm_chat)
    cand = synth.synthesize(problem, evidence)
    assert cand is not None
    assert "directive_constraint" not in cand


# ---------------------------------------------------------------------------
# 7. the engineer-review fixes (F1-F5) — pinned
# ---------------------------------------------------------------------------

def test_verdict_constraint_derivation_failed_is_typed():
    """F1: a derivation failure is never a silent unconstrained search —
    the card states it."""
    c = {"version": "directive_compliance/1.0.0",
         "status": "derivation_failed", "verb": "CHANGE_MECHANISM",
         "error_class": "OSError"}
    v = dc.compliance_verdict(c, "parent mechanism", "child mechanism")
    assert v["verdict"] == "CONSTRAINT_DERIVATION_FAILED"
    assert v["mechanism_changed"] is None


def test_worker_public_identity_reader_is_the_same_function():
    """F5: the spawn site imports the PUBLIC name; one implementation."""
    from toscanini.worker import _mechanism_identity, mechanism_identity
    assert mechanism_identity is _mechanism_identity


def test_constraint_round_trips_through_the_session_store(tmp_path,
                                                          monkeypatch):
    """F3: the store accepts and rehydrates directive_constraint (the
    open-dict merge) — the spawn→worker handoff is a no-op-free path."""
    store = _fresh_store(tmp_path, monkeypatch)
    c = dc.build_constraint("CHANGE_MECHANISM", "away", "wicking transport")
    store.create_session(title="t", user_text="p", owner_key="a" * 12)
    sid = store.list_sessions()[-1]["session_id"]
    store.update_session(sid, directive_constraint=c)
    assert store.get_session(sid)["directive_constraint"] == \
        c  # full round-trip, no field dropped


def test_constraint_scrub_removes_transport_vocabulary():
    """F4: the constraint rides product surfaces — transport vocabulary
    in the parent's recorded identity is scrubbed at derivation."""
    from toscanini.conversational.transport_invisibility import (
        _ENDPOINT_HOST_RE as host_re,
    )
    # the scrubber's host rule matches scheme'd endpoints (its contract)
    assert host_re.search("https://api.atria-asi.ai/v1")
    # the spawn replay: scrub BOTH free-text fields (same call shape)
    from toscanini.server import _scrub_transport_text
    raw = "mechanism via https://api.atria-asi.ai endpoint wicking"
    scrubbed = _scrub_transport_text(raw)
    assert "api.atria-asi.ai" not in scrubbed


def test_hyphenated_restating_cannot_evade_the_check():
    """The engineer's pass-2 BLOCKER: a hyphenated identity must SPLIT
    into tokens — 'retrieval-augmented-generation' restates a forbidden
    'retrieval augmented generation' and is judged a violation."""
    terms = dc.meaningful_terms("retrieval augmented generation loop")
    hyphen = dc.territory_violation(
        "retrieval-augmented-generation loop", terms)
    assert hyphen["violation"] is True


def test_verdict_honors_the_records_declared_threshold():
    """The engineer's pass-2 F2: a per-record threshold reaches the
    check (the declared-threshold field is not dead code)."""
    c = _constraint()
    c["threshold"] = 0.9          # stricter: ANY real overlap violates
    v = dc.compliance_verdict(
        c, "global warming projection mechanism",
        "warming-driven mechanism for heat pumps")
    # overlap is nonzero (warming/mechanism) -> with threshold 0.9 only
    # a near-total restatement violates; assert the record's threshold
    # actually reached the instrument via the ratio being judged under it
    assert v["territory"]["checked_terms"] == len(c["forbidden_terms"])
    # and a full restatement still violates under the stricter bar
    v2 = dc.compliance_verdict(c, "global warming projection mechanism",
                               "global warming projection mechanism")
    assert v2["verdict"] == "NOT_COMPLIED_SAME_AS_PARENT"


def test_worker_dispatches_every_verdict_enum():
    """The engineer's pass-2 F2 (worker): the enum the instrument can
    return is exactly the set the outcome card dispatches on — enum
    drift cannot silently degrade into the change comparison."""
    from toscanini import worker
    import inspect
    src = inspect.getsource(worker.record_directive_outcome)
    dispatched = {"COMPLIED_CHANGED", "MOVED_BUT_IN_TERRITORY",
                  "NOT_COMPLIED_SAME_AS_PARENT", "NO_BASELINE",
                  "NO_CHILD_MECHANISM", "CONSTRAINT_DERIVATION_FAILED",
                  "NOT_APPLICABLE"}
    for verdict in dispatched:
        assert f'"{verdict}"' in src, f"card does not dispatch {verdict}"
    # the module is layering-clean: no toscanini import inside the
    # compliance instrument
    mod_src = Path(dc.__file__).read_text()
    assert "from toscanini" not in mod_src
    assert "import toscanini" not in mod_src


def test_classify_falsy_adv_reason_does_not_duplicate():
    """The engineer's pass-2 F2 (classify): when the adversarial reason
    is empty, the assembled reason already carries the enumeration —
    no second 'killed dimensions:' append."""
    attacks = {"unsupported_mechanism": "KILLED: no support",
               "weak_transfer": "KILLED: weak"}
    res = _classify_with("", attacks)   # adv_reason EMPTY
    reason = res["reason"]
    assert reason.count("killed dimensions") <= 1
    assert reason.count("unsupported_mechanism") == 1


# ---------------------------------------------------------------------------
# 6. P1-3 record layer — kill causes stated ONCE (a2/classify.py)
# ---------------------------------------------------------------------------

def _classify_with(adv_reason, attacks):
    from discovery_fabric.a2 import classify
    candidate = {"mechanism": "m", "intervention": "i",
                 "falsification_test": "a concrete falsification test"}
    evidence_verification = {"verified": True, "verdicts": []}
    prior_art = {"prior_art_status": "NO_MATCH_FOUND"}
    adversarial = {"overall": "KILL", "reason": adv_reason,
                   "attacks": attacks}
    return classify.classify(candidate, evidence_verification, prior_art,
                             adversarial)


def test_kill_reason_not_duplicated_when_reason_enumerates_dimensions():
    attacks = {
        "unsupported_mechanism": "KILLED: the evidence does not support",
        "weak_transfer": "KILLED: transfer is superficial",
        "contradiction": "KILLED: contradicts the record",
        "regulatory_incompatibility": "KILLED: regulator barrier",
    }
    adv_reason = ("unsupported_mechanism: KILLED, weak_transfer: KILLED, "
                  "contradiction: KILLED, "
                  "regulatory_incompatibility: KILLED")
    res = _classify_with(adv_reason, attacks)
    reason = res["reason"]
    assert reason.count("killed dimensions") == 0     # stated ONCE
    assert reason.count("unsupported_mechanism") == 1


def test_kill_reason_appends_once_when_reason_thin():
    attacks = {"unsupported_mechanism": "KILLED: no support",
               "weak_transfer": "PASS"}
    res = _classify_with("the challenge found weaknesses", attacks)
    reason = res["reason"]
    assert reason.count("killed dimensions") == 1     # appended once
    assert "unsupported_mechanism" in reason

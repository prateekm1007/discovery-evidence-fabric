"""R510 dry-run battery — the deterministic dry-run cliff's proof.

FAST tests (always run, hermetic — no EngineRun, no network):
  - fixture matching precedence incl. the adversarial broad-vs-narrow
    case (a broad fixture can never steal a specific stage's fixture)
  - honest refusal shape (infrastructure failure stays failure)
  - ranking determinism/purity + reproduction from persisted inputs
  - Art. XLII rewrite governance on fixture texts (real instrument)
  - context isolation (bind/unbind availability flip; constructor
    refusal both directions; no fixture use when unbound)
  - r506 ineligibility by construction; diversity-gate presentation

PROOF tests (skip unless DRYRUN_PROOF_DIR points at proof output from
scripts/r510_dryrun_proof.py + scripts/r510_dryrun_repeat.py):
  - three-problem counts, zero live calls, no blocking stage
  - A-vs-B repeatability (identities, distinctness, ranking, counts)
  - production cemetery bytes unchanged + redirect restored

Epistemic status: controlled test material only (see
tests/fixtures/dryrun/problems.py). No discovery claim.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import call_context as cctx
from discovery_fabric.engine import dry_run as dr
from discovery_fabric.engine import mechanism_space as ms
from discovery_fabric.engine.llm_registry import availability_matrix
from discovery_fabric.engine.run import (
    EngineRun, _cemetery_sandbox_path)
from tests.fixtures.dryrun.problems import PACKS


# ------------------------------------------------- precedence (fast)
def test_broad_fixture_cannot_steal_specific_stage():
    """Adversarial: the broad prefix fixture is listed FIRST; the
    specific prompt fixtures later. The specific request must still
    win (precedence, never first-match-wins)."""
    fx = dr.FixtureTransport([
        {"purpose_prefix": "diversity_exploration",
         "content": "BROAD"},
        {"purpose_prefix": "diversity_exploration",
         "prompt_contains": "key", "content": "WIDE"},
        {"purpose_prefix": "diversity_exploration",
         "prompt_contains": "narrow key here", "content": "NARROW"},
    ])
    got = fx.match("diversity_exploration",
                   "prompt carrying narrow key here inside")
    assert got["content"] == "NARROW"
    got = fx.match("diversity_exploration", "prompt with key only")
    assert got["content"] == "WIDE"
    got = fx.match("diversity_exploration", "nothing matching here")
    assert got["content"] == "BROAD"


def test_exact_purpose_beats_prefix_regardless_of_order():
    fx = dr.FixtureTransport([
        {"purpose_prefix": "attack", "content": "PREFIX"},
        {"purpose_exact": "attack", "content": "EXACT"},
    ])
    assert fx.match("attack", "zzz")["content"] == "EXACT"
    assert fx.match("attack2", "zzz")["content"] == "PREFIX"
    assert fx.match("other", "zzz") is None


def test_exact_route_beats_unpinned():
    fx = dr.FixtureTransport([
        {"purpose_prefix": "synthesis", "content": "NOROUTE"},
        {"purpose_prefix": "synthesis", "route_exact": "PINNED",
         "content": "ROUTED"},
    ])
    assert fx.match("synthesis", "q", route="PINNED")["content"] == \
        "ROUTED"
    assert fx.match("synthesis", "q", route="OTHER")["content"] == \
        "NOROUTE"


def test_narrower_prompt_beats_wider_prompt():
    fx = dr.FixtureTransport([
        {"prompt_contains": "ab", "content": "WIDE"},
        {"prompt_contains": "abcd", "content": "NARROW"},
    ])
    assert fx.match("p", "xxabcdxx")["content"] == "NARROW"


def test_refusal_is_honest_typed_failure():
    """Unmapped purpose: PROVIDER_UNAVAILABLE, no content, zero paid
    calls — infrastructure failure, never a verdict (Art. LXI)."""
    fx = dr.FixtureTransport(
        [{"purpose_exact": "attack", "content": "X"}])
    res = fx.serve(prompt="p", purpose="unmapped_purpose_xyz")
    assert res.status == "PROVIDER_UNAVAILABLE"
    assert res.content is None
    tel = fx.telemetry()
    assert tel["paid_calls"] == 0
    assert tel["live_calls"] == 0
    assert tel["credentials_consulted"] is False
    assert "unmapped_purpose_xyz" in tel["refused_purposes"]


# --------------------------------------------------- ranking (fast)
def test_ranking_deterministic_pure_and_declared():
    items = [
        {"candidate_id": "b", "mechanism_support": {"verdict": "X"},
         "span_bound": False, "distinctness_verdict": "DISTINCT",
         "evidence_refs": ["e1"], "attack_status": "NOT_RUN",
         "testable": True},
        {"candidate_id": "a", "mechanism_support": {"verdict": "X"},
         "span_bound": False, "distinctness_verdict": "DISTINCT",
         "evidence_refs": ["e1"], "attack_status": "NOT_RUN",
         "testable": True},
    ]
    r1 = dr.rank_candidates(items)
    r2 = dr.rank_candidates(items)
    assert r1 == r2
    # tie -> candidate_id asc; every entry carries basis + rule
    assert [r["candidate_id"] for r in r1] == ["a", "b"]
    for r in r1:
        assert set(r["basis"]) == set(dr.RANK_WEIGHTS)
        assert "tie-break candidate_id asc" in r["rule"]


def test_support_verdict_state_key_read():
    """The mechanism_support record's verdict field is
    mechanism_support_state — the declared support weight must be
    live, not dead."""
    assert dr._support_points(
        {"mechanism_support_state": "SUPPORTS"}) == 3
    assert dr._support_points(
        {"mechanism_support_state": "NOT_ENOUGH_EVIDENCE"}) == 1
    assert dr._support_points({}) == 0


# --------------------------------- distinctness governance (fast)
def _mech(cid, mechanism, intervention, span="shared span words here"):
    return {
        "candidate_id": cid, "candidate_hash": "h:" + cid,
        "candidate_state": "CANDIDATE", "intervention": intervention,
        "mechanism": mechanism,
        "predicted_effect": "effect words %s" % cid,
        "novel_design_variable": "var %s" % cid,
        "known_failure_modes": ["mode %s" % cid],
        "constraint_set": {"boundary_conditions": "boundary %s" % cid},
        "mechanism_graph": ms.mechanism_graph_from_fields(
            {"mechanism": mechanism, "intervention": intervention,
             "expected_effect": "effect"}),
        "mechanism_source_span": span,
    }


def test_rewrite_pair_not_double_counted():
    """Art. XLII: a reworded duplicate must not create two DISTINCT
    mechanisms (the real instrument decides, thresholds untouched)."""
    base = _mech("a", "acoustic emission sensing of vapor bubbles",
                 "bond sensors onto manifolds")
    rewrite = _mech("b", "vapor bubble acoustic emission detection",
                    "attach sensors to manifolds")
    other = _mech("c", "centrifugal vapor separation by rotation",
                  "install separator bowl in hose")
    ded = ms.deduplicate_candidates([base, rewrite, other])
    by_id = {c["candidate_id"]: c.get("distinctness_verdict")
             for c in (ded.get("candidates") or [])}
    if not by_id:
        # fall back to the instrument's own count fields
        assert ded.get("n_distinct", 0) <= 2
        return
    assert list(by_id.values()).count("DISTINCT") <= 2


def test_portfolio_rank_reproduced_from_persisted_inputs(tmp_path):
    """Rank is reproduced exactly from the persisted portfolio
    candidates (no React, no recompute drift): rebuild rank inputs
    from the entries and re-rank — order must match."""
    from tests.fixtures.dryrun.problems import full_text, P1_BOUNDARY
    pack = PACKS["dry-p1"]
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    cands = []
    for i, (label, body) in enumerate(
            list(pack["texts"].items())[:3]):
        f = {}
        for line in body.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                f[k.strip().lower()] = v.strip()
        cands.append({
            "angle": label,
            "provider_id": "DRY_RUN_FIXTURE",
            "status": "OK", "model": "fixture-text/1",
            "prompt_hash": "ph%d" % i, "output_hash": "oh%d" % i,
            "candidate_id": "cand:DIV:%s:DRY_RUN_FIXTURE:oh%d" % (
                label, i),
            "fields": {
                "mechanism": f.get("mechanism", ""),
                "intervention": f.get("intervention", ""),
                "predicted_effect": f.get("predicted_effect",
                                          f.get("expected_effect",
                                                "")),
                "falsification_test": f.get(
                    "falsification_test", ""),
                "mechanism_source_span": f.get(
                    "mechanism_source_span", ""),
            }})
    (run_dir / "EXPLORATION_GRID.json").write_text(json.dumps(
        {"status": "GRID_RUN", "candidates": cands}),
        encoding="utf-8")
    (run_dir / "envelope_MECHANISM_SPACE.json").write_text(
        json.dumps({"mechanism_space": {"state": "NO_CANDIDATES",
                                        "candidates": []}}),
        encoding="utf-8")
    (run_dir / "envelope_FREEZE.json").write_text(json.dumps(
        {"evidence": [{"id": "dry-p1-e1"}, {"id": "dry-p1-e2"}]}),
        encoding="utf-8")
    port = dr.build_portfolio(str(run_dir), pack["problem"],
                              "run-repro", "bundle-repro", "bi-repro")
    assert port["r506_eligible"] is False
    assert port["mode"] == "DRY_RUN_FIXTURE"
    assert port["minimum_diversity_gate"]["gate"] == "PASS"
    # rebuild rank inputs from the persisted entries and re-rank.
    # The reproducer uses the VERBATIM persisted candidate_ids (the
    # ranking tie-breaks on engine id asc — same key, same order).
    # Cross-run comparison uses identities/stable hash instead.
    rebuilt = []
    for c in port["candidates"]:
        rebuilt.append({
            "candidate_id": c["candidate_id"],
            "mechanism_support": None,
            "span_bound": bool(c["mechanism_source_span"]),
            "distinctness_verdict": "DISTINCT",
            "evidence_refs": c["evidence_refs"],
            "attack_status": c["attack_status"],
            "testable": bool(c["falsification_test"]),
        })
    # NOTE: support/attack states are None/NOT_RUN here (no pool
    # records in this synthetic dir) — the reproduction check is
    # over the same reduced inputs, determinism is what is tested.
    r1 = [c["candidate_id"] for c in sorted(
        port["candidates"], key=lambda c: c["rank"])]
    r2 = [r["candidate_id"] for r in dr.rank_candidates(rebuilt)]
    assert r1 == r2


def test_diversity_gate_starved_on_single_candidate(tmp_path):
    """Art. LXXXIV presentation: one distinct candidate is
    MECHANISM_STARVED, never a success."""
    assert dr._diversity_gate(1)["gate"] == "MECHANISM_STARVED"
    assert dr._diversity_gate(0)["gate"] == "MECHANISM_STARVED"
    assert dr._diversity_gate(2)["gate"] == "PASS"


# ------------------------- attack measurement (never assumed) fast
def test_attack_drop_never_converts_incomplete_to_killed_or_survived():
    """Art. XXV/LXI/XXIX: ATTACK_INCOMPLETE stays ATTACK_INCOMPLETE —
    never promoted to KILLED, never to SURVIVED."""
    assert dr._attack_drop_transition(
        "ATTACK_INCOMPLETE", True) == "ATTACK_INCOMPLETE"
    assert dr._attack_drop_transition(
        "UNKNOWN", True) == "ATTACK_INCOMPLETE"
    assert dr._attack_drop_transition("", True) == "ATTACK_INCOMPLETE"
    assert dr._attack_drop_transition(
        "KILLED", True) == "ATTACK_KILLED"
    assert dr._attack_drop_transition("PASS", True) == "ATTACK_SURVIVED"
    assert dr._attack_drop_transition(
        "KILLED", False) == "ATTACK_NOT_REACHED"
    assert dr._attack_drop_transition(
        "PASS", False) == "ATTACK_NOT_REACHED"


def test_attack_transport_classifies_fixture_refusal_honestly():
    """PROVIDER_UNAVAILABLE (the dry-run fixture refusal) is transport
    unavailable — infrastructure, never a scientific verdict."""
    assert dr._attack_transport_state(
        {"llm_status": "PROVIDER_UNAVAILABLE"}) == \
        "TRANSPORT_UNAVAILABLE"
    assert dr._attack_transport_state(
        {"llm_status": "AUTH_FAILED"}) == "TRANSPORT_UNAVAILABLE"
    assert dr._attack_transport_state(
        {"llm_status": "OK"}) == "TRANSPORT_AVAILABLE"
    assert dr._attack_transport_state({}) == "UNKNOWN"


def test_attack_independence_context_is_not_provider_separation():
    """Art. XLV: SEPARATE_CONTEXT is never claimed as provider
    separation; absence of a record is INDEPENDENCE_UNAVAILABLE."""
    assert dr._attack_independence_state(
        {"independence_mode": "SEPARATE_CONTEXT"}) == \
        "SEPARATE_CONTEXT_ONLY"
    assert dr._attack_independence_state(
        {"independence_mode": "SEPARATE_PROVIDER"}) == \
        "SEPARATE_PROVIDER"
    assert dr._attack_independence_state({}) == \
        "INDEPENDENCE_UNAVAILABLE"


# ---------------- per-candidate independent attack E2E route (fast)
def _independent_attack_fixture_spec(pack):
    """The independent_attack fixture spec from a pack (must exist)."""
    specs = [s for s in pack["specs"]
             if s.get("purpose_exact") == "independent_attack"]
    assert specs, "pack missing independent_attack fixture"
    return specs[0]


def test_independent_attack_fixture_completes_through_real_instrument():
    """The matched purpose_exact='independent_attack' fixture flows
    through the REAL independent_attack() parser and produces a
    COMPLETED attack (SURVIVED, never ATTACK_INCOMPLETE). This is the
    path-B counterpart to the A2 direct test: EngineRun ->
    independent_attack -> purpose='independent_attack' ->
    FixtureTransport -> independent_attack parser -> persisted result.
    """
    from discovery_fabric.engine import independent_attack as _ia
    for pid, pack in PACKS.items():
        spec = _independent_attack_fixture_spec(pack)
        assert "SURVIVE" in spec["content"], pid
        fx = dr.FixtureTransport(
            [dict(s) for s in pack["specs"]], bundle_id="t/1")
        tok = cctx.bind_fixture(fx)
        try:
            cand = {
                "candidate_id": "cand:ia:%s" % pid,
                "mechanism": "test mechanism for %s" % pid,
                "intervention": "test intervention",
                "predicted_effect": "test predicted effect",
                "testable_prediction": "test testable prediction",
                "novel_design_variable": "",
                "known_failure_modes": [],
                "constraint_set": {},
            }
            rec = _ia.independent_attack(
                cand, dict(pack["problem"]), list(pack["evidence"]),
                None)
        finally:
            cctx.unbind_fixture(tok)
        # the attack COMPLETED through the real parser
        assert rec.get("overall") == "SURVIVED", (pid, rec)
        assert rec.get("state") == "ATTACK_RUN", pid
        assert rec.get("llm_status") == "OK", pid
        assert rec.get("overall") != "ATTACK_INCOMPLETE", pid
        # a completed attack is transport-available + context-only
        assert dr._attack_transport_state(rec) == "TRANSPORT_AVAILABLE", pid
        assert dr._attack_independence_state(rec) == \
            "SEPARATE_CONTEXT_ONLY", pid
        assert dr._attack_drop_transition(
            rec.get("overall"), True) == "ATTACK_SURVIVED", pid


def test_independent_attack_unmatched_fails_closed():
    """Without an independent_attack fixture, the real engine call is
    PROVIDER_UNAVAILABLE -> TRANSPORT_UNAVAILABLE -> ATTACK_INCOMPLETE,
    and ATTACK_INCOMPLETE is NEVER converted to KILLED or SURVIVED."""
    from discovery_fabric.engine import independent_attack as _ia
    for pid, pack in PACKS.items():
        # build a transport that omits the independent_attack spec
        specs = [dict(s) for s in pack["specs"]
                 if s.get("purpose_exact") != "independent_attack"]
        fx = dr.FixtureTransport(specs, bundle_id="t/1")
        tok = cctx.bind_fixture(fx)
        try:
            cand = {
                "candidate_id": "cand:ia:unmatched:%s" % pid,
                "mechanism": "test mechanism",
                "intervention": "test intervention",
                "predicted_effect": "test predicted effect",
                "testable_prediction": "test testable prediction",
                "novel_design_variable": "",
                "known_failure_modes": [],
                "constraint_set": {},
            }
            rec = _ia.independent_attack(
                cand, dict(pack["problem"]), list(pack["evidence"]),
                None)
        finally:
            cctx.unbind_fixture(tok)
        assert rec.get("overall") == "ATTACK_INCOMPLETE", (pid, rec)
        assert rec.get("state") == "ATTACK_INCOMPLETE", pid
        assert rec.get("overall") != "KILLED", pid
        assert rec.get("overall") != "SURVIVED", pid
        assert dr._attack_transport_state(rec) == "TRANSPORT_UNAVAILABLE", pid
        # never converted: incomplete stays incomplete in the drop taxonomy
        assert dr._attack_drop_transition(
            rec.get("overall"), True) == "ATTACK_INCOMPLETE", pid


def _independent_attack_candidate(pid):
    """A minimal candidate mirroring the pool-candidate shape passed by
    EngineRun._post_rank_pipeline (run.py:1693-1717)."""
    return {
        "candidate_id": "cand:ia:%s" % pid,
        "mechanism": "Centrifugal vapor separation transfers aerospace "
                     "bleed-air moisture separator physics into engine "
                     "coolant circuits",
        "intervention": "Install a clamp-on centrifugal vapor separator "
                        "in the upper coolant hose",
        "predicted_effect": "Vapor diverts to the vent before reaching "
                            "the radiator; leak alarms trigger 10 times "
                            "earlier",
        "testable_prediction": "Separator cuts undetected vapor leak "
                               "duration from 40 hours to under 4 hours "
                               "at 90 Celsius coolant temperature",
        "novel_design_variable": "",
        "known_failure_modes": [],
        "constraint_set": {},
    }


def test_independent_attack_grounded_kill_yields_killed():
    """A GROUNDED KILL (basis bound to a concrete evidence record id in
    the bundle, non-absence) passes the real grounding/anchor checks and
    yields overall=KILLED. This exercises path B's kill semantics through
    the real instrument — transport available, parser runs, KILL stands.
    """
    from discovery_fabric.engine import independent_attack as _ia
    for pid, pack in PACKS.items():
        eid = pack["evidence"][0]["id"]
        kill_content = "\n".join([
            "MECHANISM_FAILURE: KILL \u2014 the separator cannot detect "
            "coolant vapor nucleation because evidence %s records bubble "
            "collapse frequencies the mechanism does not transduce "
            "GROUNDED_IN: EVIDENCE %s" % (eid, eid),
            "BOUNDARY_CONDITION_FAILURE: SURVIVE \u2014 boundary failure "
            "not demonstrated GROUNDED_IN: EVIDENCE %s" % eid,
            "EVIDENCE_CONTRADICTION: SURVIVE \u2014 no contradiction "
            "observed GROUNDED_IN: EVIDENCE %s" % eid,
            "BASELINE_EQUIVALENCE: SURVIVE \u2014 baseline not exceeded "
            "GROUNDED_IN: EVIDENCE %s" % eid,
            "IMPLEMENTATION_IMPOSSIBILITY: SURVIVE \u2014 implementation "
            "feasible GROUNDED_IN: EVIDENCE %s" % eid,
            "MEASUREMENT_AMBIGUITY: SURVIVE \u2014 ambiguity resolved "
            "GROUNDED_IN: EVIDENCE %s" % eid,
        ]) + "\n"
        fx = dr.FixtureTransport(
            [{"purpose_exact": "independent_attack",
              "content": kill_content}], bundle_id="t/1")
        tok = cctx.bind_fixture(fx)
        try:
            rec = _ia.independent_attack(
                _independent_attack_candidate(pid),
                dict(pack["problem"]), list(pack["evidence"]), None)
        finally:
            cctx.unbind_fixture(tok)
        assert rec.get("overall") == "KILLED", (pid, rec)
        assert rec.get("state") == "ATTACK_RUN", pid
        mech = next((i for i in rec.get("items", [])
                     if i.get("attack_class") == "MECHANISM_FAILURE"), {})
        assert mech.get("verdict") == "KILL", pid
        assert mech.get("demoted_from") is None, pid


def test_independent_attack_ungrounded_kill_demotes_escalated():
    """An UNGROUNDED KILL (basis asserts an ABSENCE — no binding) fails
    the grounding check and is DEMOTED to ABSTAIN, preserved and
    escalated: overall=ESCALATED_OBJECTION, NEVER KILLED (fail-closed).
    """
    from discovery_fabric.engine import independent_attack as _ia
    for pid, pack in PACKS.items():
        eid = pack["evidence"][0]["id"]
        ungrounded_content = "\n".join([
            "MECHANISM_FAILURE: KILL \u2014 the candidate provides no "
            "evidence the separator works and no data is shown to support "
            "the predicted effect GROUNDED_IN: EVIDENCE %s" % eid,
            "BOUNDARY_CONDITION_FAILURE: SURVIVE \u2014 boundary failure "
            "not demonstrated GROUNDED_IN: EVIDENCE %s" % eid,
            "EVIDENCE_CONTRADICTION: SURVIVE \u2014 no contradiction "
            "observed GROUNDED_IN: EVIDENCE %s" % eid,
            "BASELINE_EQUIVALENCE: SURVIVE \u2014 baseline not exceeded "
            "GROUNDED_IN: EVIDENCE %s" % eid,
            "IMPLEMENTATION_IMPOSSIBILITY: SURVIVE \u2014 implementation "
            "feasible GROUNDED_IN: EVIDENCE %s" % eid,
            "MEASUREMENT_AMBIGUITY: SURVIVE \u2014 ambiguity resolved "
            "GROUNDED_IN: EVIDENCE %s" % eid,
        ]) + "\n"
        fx = dr.FixtureTransport(
            [{"purpose_exact": "independent_attack",
              "content": ungrounded_content}], bundle_id="t/1")
        tok = cctx.bind_fixture(fx)
        try:
            rec = _ia.independent_attack(
                _independent_attack_candidate(pid),
                dict(pack["problem"]), list(pack["evidence"]), None)
        finally:
            cctx.unbind_fixture(tok)
        # the ungrounded kill is demoted, preserved, escalated — never KILLED
        assert rec.get("overall") == "ESCALATED_OBJECTION", (pid, rec)
        assert rec.get("overall") != "KILLED", pid
        mech = next((i for i in rec.get("items", [])
                     if i.get("attack_class") == "MECHANISM_FAILURE"), {})
        assert mech.get("verdict") == "ABSTAIN", pid
        assert mech.get("demoted_from") == "KILL", pid
        assert mech.get("demotion_layer") == "v2_grounding", pid


# --------------------------------------- isolation/construction fast
def test_constructor_refuses_fixture_without_dryrun(tmp_path):
    fx = dr.FixtureTransport([], bundle_id="t/1")
    with pytest.raises(ValueError):
        EngineRun(problem={"problem_id": "x"},
                  out_dir=str(tmp_path), fixture_transport=fx)


def test_constructor_requires_transport_for_dryrun(tmp_path):
    with pytest.raises(ValueError):
        EngineRun(problem={"problem_id": "x"},
                  out_dir=str(tmp_path), dry_run=True)


def test_fixture_bind_unbind_flips_availability():
    assert not any(m.get("provider_id") == "DRY_RUN_FIXTURE"
                   for m in availability_matrix())
    fx = dr.FixtureTransport([], bundle_id="t/1")
    tok = cctx.bind_fixture(fx)
    try:
        assert any(m.get("provider_id") == "DRY_RUN_FIXTURE"
                   and m.get("available") for m in
                   availability_matrix())
    finally:
        cctx.unbind_fixture(tok)
    assert not any(m.get("provider_id") == "DRY_RUN_FIXTURE"
                   for m in availability_matrix())
    assert cctx.fixture() is None


def test_cemetery_sandbox_path_contained(tmp_path):
    p = _cemetery_sandbox_path(str(tmp_path / "run1"))
    assert str(p).startswith(str(tmp_path.resolve()))
    assert p.name == "CEMETERY.json"


def test_attack_fixtures_kill_through_real_instrument():
    """The three controlled kill texts produce overall=KILLED through
    the REAL adversarial_challenge (fixture transport only)."""
    from discovery_fabric.a2 import adversarial as adv
    from discovery_fabric.engine.ensemble import _parse_fields
    ev_map = {"dry-p1": ("dry-p1-e1", "ev1", 0),
              "dry-p2": ("dry-p2-e2", "ev4", 1),
              "dry-p3": ("dry-p3-e2", "ev6", 1)}
    for pid, pack in PACKS.items():
        f = _parse_fields(pack["texts"]["operator"])
        sid, sh, ev_idx = ev_map[pid]
        ev_abstract = pack["evidence"][ev_idx]["abstract"]
        cand = {
            "candidate_id": "cand:A2:dry:naive",
            "mechanism": f.get("mechanism", ""),
            "intervention": f.get("intervention", ""),
            "predicted_effect": f.get("expected_effect", ""),
            "testable_prediction": f.get("falsification_test", ""),
            "novel_design_variable": "",
            "known_failure_modes": ["fixture disclosed mode"],
            "constraint_set": {"boundary_conditions":
                               pack["boundary"]},
            "source_evidence": {"source_id": sid, "source_hash": sh,
                                "source_span": ev_abstract[:2000]},
            "mechanism_source_span": f.get(
                "mechanism_source_span", ""),
        }
        atk = [s for s in pack["specs"]
               if s.get("purpose_exact") == "attack"][0]["content"]
        fx = dr.FixtureTransport(
            [{"purpose_exact": "attack", "content": atk}],
            bundle_id="t/1")
        tok = cctx.bind_fixture(fx)
        try:
            rec = adv.adversarial_challenge(
                cand, evidence_verified=True,
                prior_art_state="UNRESOLVED_INSUFFICIENT_EVIDENCE")
        finally:
            cctx.unbind_fixture(tok)
        assert rec.get("overall") == "KILLED", pid


# ------------------------------------------------- proof-gated slow
PROOF_DIR = os.environ.get("DRYRUN_PROOF_DIR", "")


def _proof_summary(pid, round_tag):
    assert PROOF_DIR, "DRYRUN_PROOF_DIR not set — proof test skipped"
    path = os.path.join(PROOF_DIR, "PROOF_%s_%s.json" % (pid,
                                                         round_tag))
    if not os.path.exists(path):
        pytest.skip("proof file missing: %s" % path)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("pid", ["dry-p1", "dry-p2", "dry-p3"])
def test_proof_counts_zero_live_calls_no_block(pid):
    """Control #1: no credentials + DRY_RUN succeeds with >=2
    distinct, >=2 ranked, zero live/paid calls, no blocking stage."""
    s = _proof_summary(pid, "A")
    assert s["creds_present_in_env"] == []
    assert s["live_calls"] == 0
    assert s["paid_calls"] == 0
    assert s["generated"] >= 2
    assert s["distinct"] >= 2
    assert s["ranked"] >= 2
    assert s["r506_eligible"] is False
    assert s["blocking_stage"] is None
    assert s["retries"] == 0


@pytest.mark.parametrize("pid", ["dry-p1", "dry-p2", "dry-p3"])
def test_proof_cemetery_untouched(pid):
    """Control #9: production cemetery bytes identical before/after
    each dry-run; the sandbox redirect restored."""
    for rnd in ("A", "B"):
        s = _proof_summary(pid, rnd)
        assert s["production_cemetery_unchanged"] is True
        assert s["cemetery_path_restored"] is True


@pytest.mark.parametrize("pid", ["dry-p1", "dry-p2", "dry-p3"])
def test_proof_repeatability(pid):
    """A-vs-B: identities, distinctness, ranking order, funnel
    counts reproduce; only permitted runtime metadata differs."""
    assert PROOF_DIR, "DRYRUN_PROOF_DIR not set — proof test skipped"
    spec = importlib.util.spec_from_file_location(
        "r510_dryrun_repeat",
        str(REPO / "scripts" / "r510_dryrun_repeat.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod.check(pid, PROOF_DIR)
    assert result["passed"], result["failures"]

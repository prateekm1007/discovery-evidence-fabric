"""R510 transition-measurement controls — attribution that cannot be
gamed (Art. XVI/XVII/XIX/XXX).

The candidate transition ledger (engine/transition_trace.py) is
OBSERVATION ONLY: it reads states the real instruments produced and
attributes survivor-eligibility loss to the transition that caused
it. These controls prove the attribution follows the instruments:

  Control A — a candidate hitting a PROVEN_INVARIANT is attributed
      CEMETERY_BLOCK (generated=1, consulted=1, blocked=1). Real
      assemble_candidate + real cemetery consultation + real dedup.
      The cemetery DATA is a fixture file (one invariant with known
      domain terms); the matching CODE is untouched. The module-global
      redirect is the production sandbox mechanism itself, restored
      in finally, with production bytes asserted unchanged (Art. IX).
  Control B — an otherwise valid candidate missing the invariant
      vocabulary is attributed CLEAR (blocked=0), through the same
      real path.
  Control C — an EQUIVALENT pair is attributed DISTINCTNESS_DROP
      (generated=2, clear=2, equivalent=1), never cemetery loss.
  Control D — a cemetery-clear DISTINCT candidate with
      NOT_ENOUGH_EVIDENCE support is attributed SUPPORT_VERIFICATION
      while pipeline_retained stays True (the measured dual track:
      retained-but-unaffirmed — support verification labels, it does
      not filter; the P1 MS candidate reached pool attack in exactly
      this state).

Plus pure-taxonomy unit tests (no instruments) for the remaining
branches: NOT_GENERATED, STRUCTURALLY_INADMISSIBLE,
CEMETERY_UNKNOWN (infrastructure — never a scientific drop),
DISTINCTNESS_INDETERMINATE.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import mechanism_space as ms
from discovery_fabric.engine import transition_trace as tt

FIX_ENTRY = {
    "entry_id": "CE-FIX-1",
    "territory_id": "FIX",
    "mechanism_name": "Zeta beam gland extrusion monitor",
    "proposed_version": "V1",
    "killed_at_version": "V1",
    "kill_reason": "PHYSICS_CEILING",
    "what_was_proposed": "Sense zeta beam extrusion in gland seals.",
    "why_it_failed": "Zeta extrusion cannot be sensed in glands.",
    "reusable_lesson": "Zeta extrusion lessons for gland seals.",
    "what_to_avoid": "Avoid zeta proposals.",
    "physical_constraint": ("Zeta beam extrusion in gland seals cannot "
                            "be sensed by any gauge."),
    "evidence_sources": [],
    "epistemic_class": "PROVEN_INVARIANT",
}

# P1-style acoustic text: shares NO domain term with CE-FIX-1
# (zeta/beam/extrusion/gland/seals/monitor/sensed/gauge).
CLEAR_MECH = ("Acoustic emission sensing detects vapor bubble formation "
              "in coolant channels before visible leakage occurs")
CLEAR_INT = ("Bond acoustic emission sensors onto both coolant "
             "manifolds without engine removal")


def _graph(mech, interv):
    return ms.mechanism_graph_from_fields(
        {"mechanism": mech, "intervention": interv,
         "expected_effect": "effect"})


def _cand(cid, mech, interv, state="CANDIDATE"):
    text = "%s %s" % (mech, interv)
    return {
        "candidate_id": cid,
        "candidate_hash": hashlib.sha256(text.encode()).hexdigest(),
        "candidate_state": state,
        "intervention": interv,
        "mechanism": mech,
        "predicted_effect": "predicted " + cid,
        "novel_design_variable": "variable " + cid,
        "known_failure_modes": ["mode " + cid],
        "constraint_set": {"boundary_conditions": "boundary " + cid},
        "mechanism_graph": _graph(mech, interv),
        "testable_prediction_check": {"testable": True},
        "mechanism_source_span": "span words for " + cid,
    }


@pytest.fixture()
def fixture_cemetery(tmp_path, monkeypatch):
    """Redirect the cemetery module-global to a fixture file with ONE
    known PROVEN_INVARIANT; restore afterwards; assert production
    bytes untouched (read-only consultation — Art. IX)."""
    import orchestrator.mechanism_cemetery as mc
    prod = Path(str(mc.CEMETERY_PATH))
    before = (hashlib.sha256(prod.read_bytes()).hexdigest()
              if prod.exists() else "ABSENT")
    fix = tmp_path / "cemetery" / "CEMETERY.json"
    fix.parent.mkdir(parents=True)
    fix.write_text(json.dumps({"entries": [FIX_ENTRY]}),
                   encoding="utf-8")
    monkeypatch.setattr(mc, "CEMETERY_PATH", fix)
    yield fix
    after = (hashlib.sha256(prod.read_bytes()).hexdigest()
             if prod.exists() else "ABSENT")
    assert before == after


def _ledger(assembled, consult, dd_map, retained, support,
            pre_states=None):
    # pre_states: candidate_id -> state BEFORE consultation (the
    # adapter snapshots before the instruments mutate; a helper that
    # reads current states would misattribute — Art. XXIV).
    if pre_states is None:
        pre_states = {c["candidate_id"]: "CANDIDATE"
                      for c in assembled}
    return tt.build_transition_ledger(
        assembled, "DIRECT_TRANSFER", "OPERATED", pre_states,
        consult, dd_map, retained, support, {})


def test_control_a_cemetery_block(fixture_cemetery):
    """Control A: invariant hit -> CEMETERY_BLOCK (real assembly,
    real consultation, real dedup)."""
    op = [o for o in ms.TRANSFORMATION_OPERATORS
          if o["operator_id"] == "DIRECT_TRANSFER"][0]
    item = {"item_id": "fix_a",
            "fields": {"system": {"value": "hydraulic lift actuator"},
                       "mechanism": {"value": "seal extrusion"},
                       "observed_effect": {"value": "pressure decay"},
                       "intervention": {"value": "gland gauges"},
                       "boundary_conditions": {"value": "no drain"},
                       "failure_mode": {"value": "seal leak"},
                       "constraints": {"value": "none"}},
            "source": "dry-run-fixture"}
    fields = {
        "mechanism": ("Zeta extrusion monitoring transfers into lift "
                      "actuators; gland sensors watch zeta extrusion "
                      "in gland seals"),
        "intervention": ("Mount zeta extrusion gauges on the actuator "
                         "gland without system drain-down"),
        "predicted_effect": "Gauges warn before decay at rated hold",
        "novel_design_variable": "gauge stiffness",
        "testable_prediction": ("Gauges deflect 0.1 millimeters by "
                                "cycle 800 at 200 bar hold pressure"),
        "known_failure_modes": "gauge fatigue",
        "boundary_conditions": "no system drain-down",
        "mechanism_source_span": "zeta extrusion in gland seals",
    }
    meta = {"provider": "DRY_RUN_FIXTURE", "model": "fixture-text/1",
            "prompt_hash": "ph", "output_hash": "oh",
            "call_provenance": {}, "task_degradation": {},
            "cost_provenance": {}}
    cand = ms.assemble_candidate(
        op, item, fields,
        {"device": "hydraulic lift actuator"}, meta)
    assert cand["candidate_state"] == "CANDIDATE"
    consult = ms._consult_cemetery([cand])
    assert consult["n_blocked"] == 1
    assert cand["candidate_state"] == \
        "NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT"
    assert cand["cemetery_block"][0]["cemetery_entry"] == "CE-FIX-1"
    ded = ms.deduplicate_candidates([cand])
    assert ded["n_distinct"] == 0
    led = _ledger([cand], consult, {}, [], {})
    counts = led["operator_counts"]
    assert counts["generated"] == 1
    assert counts["structurally_admissible"] == 1
    assert counts["cemetery_consulted"] == 1
    assert counts["cemetery_blocked"] == 1
    t = led["candidate_traces"][0]
    assert t["cemetery_entry_ids"] == ["CE-FIX-1"]
    assert t["drop_transition"] == "CEMETERY_BLOCK"
    assert t["survivor_eligible"] is False
    assert t["pipeline_retained"] is False


def test_control_b_no_cemetery_block(fixture_cemetery):
    """Control B: same real path, invariant-free vocabulary ->
    CLEAR, blocked=0."""
    cand = _cand("ctrl-b", CLEAR_MECH, CLEAR_INT)
    consult = ms._consult_cemetery([cand])
    assert consult["n_blocked"] == 0
    assert cand["candidate_state"] == "CANDIDATE"
    ded = ms.deduplicate_candidates([cand])
    assert ded["n_distinct"] == 1
    dd = {c["candidate_id"]: {
        "verdict": c.get("distinctness_verdict"),
        "basis": c.get("distinctness_basis")} for c in [cand]}
    led = _ledger([cand], consult, dd, ["ctrl-b"],
                  {"ctrl-b": {"mechanism_support_state": "SUPPORTED",
                              "counts": {}}})
    counts = led["operator_counts"]
    assert counts["generated"] == 1
    assert counts["cemetery_consulted"] == 1
    assert counts["cemetery_blocked"] == 0
    assert counts["cemetery_clear"] == 1
    t = led["candidate_traces"][0]
    assert t["drop_transition"] is None
    assert t["survivor_eligible"] is True


def test_control_c_distinctness_drop(fixture_cemetery):
    """Control C: an EQUIVALENT pair is DISTINCTNESS_DROP, never
    cemetery loss (real adjudicator decides equivalence)."""
    base = _cand("ctrl-c1", CLEAR_MECH, CLEAR_INT)
    # wording-only variation of the same causal core (reordered
    # clauses, same physics vocabulary — the Art. XLII forbidden
    # list: restructuring cannot create a mechanism; probed against
    # the real adjudicator: reorder merges EQUIVALENT, heavy
    # re-vocabularizing stays DISTINCT).
    rewrite = _cand(
        "ctrl-c2",
        "Before visible leakage occurs, acoustic emission sensing "
        "detects vapor bubble formation in coolant channels",
        "Onto both coolant manifolds bond acoustic emission sensors "
        "without engine removal")
    consult = ms._consult_cemetery([base, rewrite])
    assert consult["n_blocked"] == 0
    ded = ms.deduplicate_candidates([base, rewrite])
    verdicts = {c["candidate_id"]: c.get("distinctness_verdict")
                for c in (base, rewrite)}
    assert list(verdicts.values()).count("EQUIVALENT") == 1, verdicts
    dd = {cid: {"verdict": v, "basis": ""} for cid, v in
          verdicts.items()}
    kept = [cid for cid, v in verdicts.items() if v != "EQUIVALENT"]
    led = _ledger([base, rewrite], consult, dd, kept, {})
    counts = led["operator_counts"]
    assert counts["generated"] == 2
    assert counts["cemetery_clear"] == 2
    assert counts["cemetery_blocked"] == 0
    assert counts["equivalent"] == 1
    dropped = [t for t in led["candidate_traces"]
               if t["drop_transition"] == "DISTINCTNESS_DROP"]
    assert len(dropped) == 1
    assert dropped[0]["pipeline_retained"] is False


def test_control_d_support_loss(fixture_cemetery):
    """Control D: cemetery-clear DISTINCT + NOT_ENOUGH_EVIDENCE ->
    SUPPORT_VERIFICATION with pipeline_retained=True (the measured
    dual track: retained-but-unaffirmed)."""
    cand = _cand("ctrl-d", CLEAR_MECH, CLEAR_INT)
    consult = ms._consult_cemetery([cand])
    assert consult["n_blocked"] == 0
    ded = ms.deduplicate_candidates([cand])
    assert ded["n_distinct"] == 1
    # structured items with phenomenon-only overlap: the real
    # verifier returns NOT_ENOUGH_EVIDENCE (never weak support).
    items = [{"item_id": "fix_d1",
              "fields": {"system": {"value": "coolant loop"},
                         "mechanism": {"value": "unrelated osmosis"},
                         "observed_effect": {"value": "color shift"},
                         "intervention": {"value": "dye"},
                         "boundary_conditions": {"value": "lab"},
                         "failure_mode": {"value": "stain"}}}] * 2
    sup = ms.verify_mechanism_support(
        cand, items, {"device": "engine cooling system"})
    assert sup["mechanism_support_state"] == "NOT_ENOUGH_EVIDENCE"
    dd = {"ctrl-d": {"verdict": "DISTINCT", "basis": "first family"}}
    led = _ledger([cand], consult, dd, ["ctrl-d"], {"ctrl-d": sup})
    counts = led["operator_counts"]
    assert counts["cemetery_clear"] == 1
    assert counts["support_not_enough_evidence"] == 1
    t = led["candidate_traces"][0]
    assert t["drop_transition"] == "SUPPORT_VERIFICATION"
    assert t["pipeline_retained"] is True
    assert t["survivor_eligible"] is False


# ------------------------------------------------- pure taxonomy
def _trace(**kw):
    base = {"generation_status": "OPERATED",
            "structurally_admissible": True,
            "cemetery_state": "CLEAR",
            "distinctness_verdict": "DISTINCT",
            "support_state": "SUPPORTED"}
    base.update(kw)
    return base


def test_taxonomy_not_generated():
    assert tt._drop_for(_trace(
        generation_status="NO_APPLICABLE_EVIDENCE")) == "NOT_GENERATED"
    assert tt._drop_for(_trace(
        generation_status="OPERATOR_INSTANTIATION_FAILED")
    ) == "NOT_GENERATED"


def test_taxonomy_structurally_inadmissible():
    assert tt._drop_for(_trace(structurally_admissible=False,
                               cemetery_state="NOT_CONSULTED")
                        ) == "STRUCTURALLY_INADMISSIBLE"


def test_taxonomy_cemetery_unknown_is_not_a_drop():
    """Infrastructure failure is never a scientific drop (Art. XXV)
    and never silent eligibility."""
    assert tt._drop_for(_trace(
        cemetery_state="CONSULTATION_UNAVAILABLE")
    ) == "CEMETERY_UNKNOWN"


def test_taxonomy_distinctness_branches():
    assert tt._drop_for(_trace(
        distinctness_verdict="EQUIVALENT")) == "DISTINCTNESS_DROP"
    assert tt._drop_for(_trace(
        distinctness_verdict="INDETERMINATE")
    ) == "DISTINCTNESS_INDETERMINATE"
    assert tt._drop_for(_trace(
        distinctness_verdict="NOT_ADJUDICATED")
    ) == "DISTINCTNESS_UNADJUDICATED"


def test_taxonomy_affirmed_is_eligible():
    assert tt._drop_for(_trace()) is None
    assert tt._drop_for(_trace(
        support_state="PARTIALLY_SUPPORTED")) is None
    assert tt._drop_for(_trace(
        support_state="CONTESTED")) == "SUPPORT_VERIFICATION"

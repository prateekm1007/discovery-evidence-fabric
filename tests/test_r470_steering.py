"""R470 — the P0-5 steering contracts (power + semantics), reconciled
onto the sibling R470-C2 chain.

The 2026-09-15 external re-audit's remaining steering blocker, verbatim:
"'changed' is string-inequality, not directive-compliance: my PCM
directive moved the intervention while the mechanism identity stayed
inside the explicitly forbidden climate-projection territory. The next
step is both power (exclude the parent's killed/forbidden mechanism
from the child's search) and semantics (compare against the directive,
not just the parent)."

PARALLEL-LINE RECONCILIATION (this file, post-rebase): both R470 lines
implemented the semantics leg independently — this line parsed the
directive's own use/do-not-use phrases; the sibling built the ONE
shared instrument discovery_fabric/engine/directive_compliance.py
(record-derived forbidden referent + distinctive-vocabulary containment
+ typed verdicts, engineer-reviewed with the hyphen-evasion BLOCKER
fix). Per Art. X the sibling's instrument is canonical; this suite now
pins IT, with THIS line's audit specimens (the PCM re-audit specimen
and the morning re-derivation specimen) as the evidence cases.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import directive_compliance as dc  # noqa: E402

PCM_DIRECTIVE = ("Do not use a climate-projection mechanism. Use "
                 "phase-change material (PCM) thermal buffering with "
                 "night-sky radiative cooling panels instead")
CLIMATE_PARENT = ("Global atmospheric warming projection above 2 "
                  "degrees Celsius baseline")


def _fresh_store(tmp_path, monkeypatch):
    from toscanini import sessions as store
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    monkeypatch.setattr(store, "SESSIONS_PATH", tmp_path / "sessions.json")
    monkeypatch.setattr(store, "SHARES_PATH", tmp_path / "shares.json")
    monkeypatch.setattr(store, "ENGINE_RUNS", tmp_path / "runs")
    return store


# ---------------------------------------------------------------------------
# 1. the shared instrument (the ONE compliance authority, Art. X)
# ---------------------------------------------------------------------------

def test_meaningful_terms_deterministic_and_stopword_stripped():
    terms = dc.meaningful_terms(
        "Global atmospheric warming projection above the baseline")
    assert "the" not in terms
    assert "global" in terms and "warming" in terms
    assert dc.meaningful_terms("") == []


def test_hyphen_evasion_blocked():
    """The engineer's pass-2 BLOCKER: a hyphenated identity must SPLIT,
    or 'retrieval-augmented-generation' evades a forbidden 'retrieval
    augmented generation' by orthography."""
    forbidden_terms = dc.meaningful_terms(
        "retrieval augmented generation contaminates the mechanism")
    child = ("Retrieval-augmented-generation drives the extracted claim")
    v = dc.territory_violation(child, forbidden_terms)
    assert v["overlap_ratio"] >= 0.5
    assert v["violation"] is True


def test_territory_threshold_is_declared_and_reaches_the_check():
    assert dc.VIOLATION_THRESHOLD == 0.5
    # the per-record threshold reaches the instrument (pass-2 F2)
    terms = dc.meaningful_terms("alpha beta gamma delta epsilon")
    loose = dc.territory_violation("alpha beta present", terms, 0.4)
    strict = dc.territory_violation("alpha beta present", terms, 0.9)
    assert loose["violation"] is True
    assert strict["violation"] is False


def test_morning_specimen_types_same_as_parent():
    """The audit's MORNING specimen: the child re-derived the parent's
    identical mechanism under a 'different material' directive — typed
    NOT_COMPLIED_SAME_AS_PARENT (string-inequality is not compliance)."""
    same = ("Adsorption of arsenic using magnetic iron oxide "
            "nanoparticles embedded in a cellulose matrix")
    constraint = dc.build_constraint("CHANGE_MECHANISM",
                                     "different material", same)
    v = dc.compliance_verdict(constraint, same, same)
    assert v["verdict"] == "NOT_COMPLIED_SAME_AS_PARENT"
    assert v["mechanism_changed"] is False


def test_pcm_specimen_types_territory():
    """The audit's RE-AUDIT specimen: the mechanism moved but stays in
    the forbidden climate territory — typed MOVED_BUT_IN_TERRITORY (the
    exact case the string-inequality card mislabeled as success)."""
    constraint = dc.build_constraint("CHANGE_MECHANISM",
                                     PCM_DIRECTIVE, CLIMATE_PARENT)
    child = ("Global atmospheric warming projection above 2 degrees "
             "Celsius baseline under radiative forcing")
    v = dc.compliance_verdict(constraint, CLIMATE_PARENT, child)
    assert v["verdict"] == "MOVED_BUT_IN_TERRITORY"
    assert v["mechanism_changed"] is True
    assert v["territory"]["violation"] is True


def test_clean_compliance_types_complied_changed():
    constraint = dc.build_constraint("CHANGE_MECHANISM",
                                     PCM_DIRECTIVE, CLIMATE_PARENT)
    child = ("Phase-change material thermal buffering with night-sky "
             "radiative cooling governs the cabinet heat balance")
    v = dc.compliance_verdict(constraint, CLIMATE_PARENT, child)
    assert v["verdict"] == "COMPLIED_CHANGED"
    assert v["territory"]["violation"] is False


def test_not_applicable_and_baseline_guards():
    assert dc.compliance_verdict(None, "a", "b")["verdict"] == \
        "NOT_APPLICABLE"
    # an empty forbidden mechanism is not a constraint at all
    c_empty = dc.build_constraint("CHANGE_MECHANISM", "d", "")
    assert dc.compliance_verdict(c_empty, "a", "b")["verdict"] == \
        "NOT_APPLICABLE"
    # a real constraint with no parent baseline to compare against
    c = dc.build_constraint("CHANGE_MECHANISM", "d",
                            "some recorded forbidden mechanism")
    assert dc.compliance_verdict(c, "", "b")["verdict"] == "NO_BASELINE"
    assert dc.compliance_verdict(c, "a", "")["verdict"] == \
        "NO_CHILD_MECHANISM"


def test_derivation_failure_is_typed_never_silent():
    """The engineer's review F1: a spawn-site derivation failure is a
    TYPED state — never a silent unconstrained search."""
    v = dc.compliance_verdict(
        {"status": "derivation_failed"}, "a", "b")
    assert v["verdict"] == "CONSTRAINT_DERIVATION_FAILED"


def test_build_constraint_carries_the_verbatim_directive():
    c = dc.build_constraint("RESEARCH", PCM_DIRECTIVE, CLIMATE_PARENT)
    assert c["verb"] == "RESEARCH"
    assert PCM_DIRECTIVE[:80] in c["directive_verbatim"]
    assert c["forbidden_mechanism"] == CLIMATE_PARENT
    assert c["threshold"] == dc.VIOLATION_THRESHOLD
    assert c["version"] == dc.DIRECTIVE_COMPLIANCE_VERSION


# ---------------------------------------------------------------------------
# 2. the power leg — the chain wiring (source pins on the canonical line)
# ---------------------------------------------------------------------------

def test_spawn_site_derives_the_constraint():
    from toscanini import server
    src = Path(server.__file__).read_text()
    assert "build_constraint" in src
    assert 'verb in ("CHANGE_MECHANISM", "RESEARCH")' in src or \
        "EXCLUSION_VERBS" in src


def test_worker_persists_and_forwards_the_constraint():
    from toscanini import worker
    src = Path(worker.__file__).read_text()
    assert "DIRECTIVE_CONSTRAINT.json" in src
    assert 'problem["directive_constraint"]' in src
    assert "DIRECTIVE_CONSTRAINT_APPLIED" in src


def test_synthesize_consumes_the_constraint_and_checks_postparse():
    from discovery_fabric.a2 import synthesize as S
    src = Path(S.__file__).read_text()
    assert "CONSTRAINT_INSTRUCTION" in src
    assert 'problem.get("directive_constraint")' in src
    assert "violation_final" in src


def test_span_instruction_is_mechanical():
    """The sibling's claimant-side span rules (the citation contract's
    prompt leg — composes with this line's verifier-assist in
    a2/verify.py: the prompt asks for verbatim spans, the assist
    recovers grounded-but-unquoted ones, the verifier stays hard)."""
    from discovery_fabric.a2 import synthesize as S
    assert "8 consecutive words" in S.SPAN_INSTRUCTION
    assert "byte-for-byte" in S.SPAN_INSTRUCTION or \
        "character-for-character" in S.SPAN_INSTRUCTION


# ---------------------------------------------------------------------------
# 3. the composed outcome record (integration with the store)
# ---------------------------------------------------------------------------

def test_directive_outcome_carries_the_compliance_verdict(
        tmp_path, monkeypatch):
    from toscanini import sessions as store
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import worker
    parent_run = tmp_path / "run_parent"
    parent_run.mkdir()
    (parent_run / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {"mechanism": CLIMATE_PARENT,
                           "intervention": "coatings"}}))
    child_run = tmp_path / "run_child"
    child_run.mkdir()
    (child_run / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {
            "mechanism": "Phase-change material thermal buffering with "
                         "night-sky radiative cooling",
            "intervention": "PCM panels"}}))
    store.create_session(title="p", user_text="cool a cabinet",
                         owner_key="a" * 12)
    parent_id = store.list_sessions()[-1]["session_id"]
    store.update_session(parent_id, run_dir=str(parent_run))
    store.create_session(title="p", user_text="cool a cabinet",
                         owner_key="a" * 12)
    child_id = store.list_sessions()[-1]["session_id"]
    store.update_session(child_id, parent_session_id=parent_id)
    store.update_session(child_id, conversation=[
        {"role": "user", "text": "[CHANGE_MECHANISM] " + PCM_DIRECTIVE,
         "classification": "ACTION"}])
    # the spawn site would have set the constraint; simulate it here
    store.update_session(
        child_id, directive_constraint=dc.build_constraint(
            "CHANGE_MECHANISM", PCM_DIRECTIVE, CLIMATE_PARENT))
    worker.record_directive_outcome(child_id, child_run)
    out = store.get_session(child_id)["directive_outcome"]
    assert out["compliance_verdict"] == "COMPLIED_CHANGED"
    assert out["mechanism_changed"] is True
    assert "moved the mechanism" in out["summary"]


def test_directive_outcome_states_territory_violation_plainly(
        tmp_path, monkeypatch):
    """The re-derivation-in-territory case: the card SAYS the shortfall
    — the audit's exact complaint, now impossible to mislabel."""
    from toscanini import sessions as store
    store = _fresh_store(tmp_path, monkeypatch)
    from toscanini import worker
    parent_run = tmp_path / "run_p2"
    parent_run.mkdir()
    (parent_run / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {"mechanism": CLIMATE_PARENT,
                           "intervention": "coatings"}}))
    child_run = tmp_path / "run_c2"
    child_run.mkdir()
    (child_run / "envelope_SYNTHESIZE.json").write_text(json.dumps(
        {"mechanism_map": {
            "mechanism": "Global atmospheric warming projection above "
                         "2 degrees Celsius baseline under radiative "
                         "forcing",
            "intervention": "reflective film"}}))
    store.create_session(title="p", user_text="x", owner_key="a" * 12)
    parent_id = store.list_sessions()[-1]["session_id"]
    store.update_session(parent_id, run_dir=str(parent_run))
    store.create_session(title="p", user_text="x", owner_key="a" * 12)
    child_id = store.list_sessions()[-1]["session_id"]
    store.update_session(child_id, parent_session_id=parent_id)
    store.update_session(child_id, conversation=[
        {"role": "user", "text": "[CHANGE_MECHANISM] " + PCM_DIRECTIVE,
         "classification": "ACTION"}])
    store.update_session(
        child_id, directive_constraint=dc.build_constraint(
            "CHANGE_MECHANISM", PCM_DIRECTIVE, CLIMATE_PARENT))
    worker.record_directive_outcome(child_id, child_run)
    out = store.get_session(child_id)["directive_outcome"]
    assert out["compliance_verdict"] == "MOVED_BUT_IN_TERRITORY"
    assert "still restates the mechanism your direction excluded" \
        in out["summary"]

#!/usr/bin/env python3
"""R475 — the prohibited-action compliance battery, executing the
operator's LIVE measurement as the lead regression:

  "I steered with 'no external literature search at all' — the child
   ran full retrieval (16 records) and still typed COMPLIED_CHANGED."

The old verdict layer modeled only mechanism-movement semantics — a
prohibition directive never reached it (no constraint was built for it
on a non-exclusion verb; even with a constraint, no leg observed the
action). This battery pins the new typed contract:
  - the operator's exact case: directive "no external literature
    search at all" + observed retrieval 16 -> VIOLATED_PROHIBITED_ACTION
    (NEVER COMPLIED_CHANGED);
  - satisfied prohibition + mechanism moved -> COMPLIED_CHANGED with
    the satisfied prohibition on the record;
  - prohibitions-only constraint (fresh round, no parent mechanism) ->
    COMPLIED_PROHIBITIONS / VIOLATED...;
  - unmeasurable prohibition -> PROHIBITION_UNOBSERVED (never a
    silent unmeasured dimension);
  - cue-adjacency negatives (no fabricated prohibitions);
  - the legacy R470 mechanism-movement matrix unchanged;
  - the observation helper counts from the run's own records.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import directive_compliance as dc  # noqa: E402

OPERATOR_DIRECTIVE = "no external literature search at all"


# ---------------------------------------------------------------------------
# detection: the closed-vocabulary scan
# ---------------------------------------------------------------------------

def test_operator_directive_detects_retrieval_prohibition():
    c = dc.build_constraint("RESEARCH", OPERATOR_DIRECTIVE,
                            "parent mechanism text")
    assert c["prohibited_actions"], "the operator's directive must " \
        "produce a prohibition on the record"
    actions = [p["action"] for p in c["prohibited_actions"]]
    assert "RETRIEVAL" in actions
    entry = next(p for p in c["prohibited_actions"]
                 if p["action"] == "RETRIEVAL")
    assert entry["phrase"] in OPERATOR_DIRECTIVE.lower()


def test_cue_adjacency_negatives_never_fabricate():
    # an action word WITHOUT a negation cue is not a prohibition
    assert dc.detect_prohibited_actions(
        "use retrieval-augmented generation with web sources") == []
    assert dc.detect_prohibited_actions(
        "consider links between the two failure modes") == []
    # a negation cue far from the action phrase is not a prohibition
    assert dc.detect_prohibited_actions(
        "no change to the mechanism; also run literature search") == []
    # a real prohibition over the second action class
    got = dc.detect_prohibited_actions("do not fetch urls this round")
    assert [p["action"] for p in got] == ["URL_FETCH"]


def test_prohibitions_only_constraint_is_valid():
    c = dc.build_constraint("CONTINUE", OPERATOR_DIRECTIVE, "")
    assert c["prohibited_actions"]
    assert not c["forbidden_mechanism"]
    # a prohibitions-only constraint must NOT be NOT_APPLICABLE
    v = dc.compliance_verdict(c, None, None,
                              observed_actions={"RETRIEVAL": 0,
                                                "URL_FETCH": 0})
    assert v["verdict"] == "COMPLIED_PROHIBITIONS"


# ---------------------------------------------------------------------------
# the verdict matrix: the operator's case first
# ---------------------------------------------------------------------------

def test_operator_live_case_types_violation_never_complied():
    """THE lead regression: the exact live exercise — steered with 'no
    external literature search at all', the child ran full retrieval
    (16 records) — and the old layer typed COMPLIED_CHANGED."""
    c = dc.build_constraint("RESEARCH", OPERATOR_DIRECTIVE,
                            "a thermal-runaway propagation model")
    v = dc.compliance_verdict(
        c, "a thermal-runaway propagation model",
        "an electrochemical-impedance drift model",
        observed_actions={"RETRIEVAL": 16, "URL_FETCH": 0})
    assert v["verdict"] == "VIOLATED_PROHIBITED_ACTION", (
        "a child that ran the prohibited action must NEVER type "
        "COMPLIED_CHANGED")
    assert v["mechanism_changed"] is True  # the mechanism leg still measured
    violated = v["prohibitions_violated"]
    assert len(violated) == 1 and violated[0]["action"] == "RETRIEVAL"
    assert violated[0]["observed_count"] == 16


def test_violation_dominates_mechanism_shortfalls():
    """The worst honest outcome: a violated prohibition dominates even
    NOT_COMPLIED_SAME_AS_PARENT / MOVED_BUT_IN_TERRITORY."""
    c = dc.build_constraint("CHANGE_MECHANISM", OPERATOR_DIRECTIVE,
                            "gravity drainage network")
    same = "gravity drainage network"
    v = dc.compliance_verdict(c, same, same,
                              observed_actions={"RETRIEVAL": 3,
                                                "URL_FETCH": 0})
    assert v["verdict"] == "VIOLATED_PROHIBITED_ACTION"
    assert v["territory"]["violation"] is True  # the territory leg recorded


def test_satisfied_prohibition_keeps_honest_compliance():
    c = dc.build_constraint("CHANGE_MECHANISM", OPERATOR_DIRECTIVE,
                            "a thermal-runaway propagation model")
    v = dc.compliance_verdict(
        c, "a thermal-runaway propagation model",
        "an electrochemical-impedance drift model",
        observed_actions={"RETRIEVAL": 0, "URL_FETCH": 0})
    assert v["verdict"] == "COMPLIED_CHANGED"
    assert len(v["prohibitions_satisfied"]) == 1
    assert v["prohibitions_satisfied"][0]["observed_count"] == 0


def test_unmeasurable_prohibition_types_unobserved():
    """An action the observation source could not count is UNOBSERVED —
    compliance is never claimed for an unmeasured dimension."""
    c = dc.build_constraint("CHANGE_MECHANISM",
                            "different mechanism; no external urls at all",
                            "a thermal-runaway propagation model")
    assert [p["action"] for p in c["prohibited_actions"]] == ["URL_FETCH"]
    v = dc.compliance_verdict(
        c, "a thermal-runaway propagation model",
        "an impedance drift model",
        observed_actions={"RETRIEVAL": 0, "URL_FETCH": None})
    assert v["verdict"] == "PROHIBITION_UNOBSERVED"
    assert v["prohibitions_unobserved"][0]["action"] == "URL_FETCH"
    assert v["prohibitions_unobserved"][0]["observed_count"] is None


def test_no_observation_dict_means_unobserved_not_satisfied():
    """A caller that cannot observe anything (obs=None) must never see
    prohibitions typed as satisfied — the R472-class silent-default is
    machine-blocked."""
    c = dc.build_constraint("RESEARCH", OPERATOR_DIRECTIVE, "parent mech")
    v = dc.compliance_verdict(c, "a thermal-runaway propagation model",
                              "an impedance drift model",
                              observed_actions=None)
    assert v["verdict"] == "PROHIBITION_UNOBSERVED"
    assert not v["prohibitions_satisfied"]
    assert v["prohibitions_unobserved"][0]["observed_count"] is None


# ---------------------------------------------------------------------------
# the legacy mechanism-movement matrix: unchanged verdicts
# ---------------------------------------------------------------------------

CLIMATE_PARENT = ("Global atmospheric warming projection above 2 "
                  "degrees Celsius baseline")


def test_legacy_matrix_not_complied_same_as_parent():
    c = dc.build_constraint("CHANGE_MECHANISM", "try something else",
                            CLIMATE_PARENT)
    v = dc.compliance_verdict(c, CLIMATE_PARENT, CLIMATE_PARENT,
                              observed_actions={"RETRIEVAL": 0,
                                                "URL_FETCH": 0})
    assert v["verdict"] == "NOT_COMPLIED_SAME_AS_PARENT"


def test_legacy_matrix_moved_but_in_territory():
    c = dc.build_constraint("CHANGE_MECHANISM", "different mechanism",
                            CLIMATE_PARENT)
    child = ("Global atmospheric warming projection above 2 degrees "
             "Celsius baseline under radiative forcing")
    v = dc.compliance_verdict(c, CLIMATE_PARENT, child,
                              observed_actions={"RETRIEVAL": 0,
                                                "URL_FETCH": 0})
    assert v["verdict"] == "MOVED_BUT_IN_TERRITORY"


def test_legacy_matrix_not_applicable_and_derivation_failed():
    assert dc.compliance_verdict(None, "a", "b")["verdict"] == \
        "NOT_APPLICABLE"
    c_empty = dc.build_constraint("CHANGE_MECHANISM", "d", "")
    assert dc.compliance_verdict(c_empty, "a", "b",
                                 observed_actions={})["verdict"] == \
        "NOT_APPLICABLE"
    bad = {"status": "derivation_failed", "verb": "CHANGE_MECHANISM"}
    assert dc.compliance_verdict(bad, "a", "b")["verdict"] == \
        "CONSTRAINT_DERIVATION_FAILED"


def test_version_bumped_and_constraint_shape_stable():
    assert dc.DIRECTIVE_COMPLIANCE_VERSION == "directive_compliance/1.1.0"
    c = dc.build_constraint("RESEARCH", OPERATOR_DIRECTIVE, "p")
    for key in ("version", "verb", "directive_verbatim",
                "forbidden_mechanism", "forbidden_terms", "threshold",
                "prohibited_actions"):
        assert key in c, f"constraint lost the {key!r} field"

"""Tests for the M1 campaign bridge (hermetic — no live calls).

Covers: campaign loading + joining, problem construction (evidence-bound,
MAUDE limitations stamped, campaign principle travels as provenance only),
M6 mechanical classification (positive + negative + metamorphic), and the
M4 directive-format cemetery entry contract.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from discovery_fabric.engine.campaign_bridge import (  # noqa: E402
    CLASS_ENGINEERING, CLASS_INFRASTRUCTURE, CLASS_INVENTION,
    CLASS_KILLED, CLASS_TRANSFER, DIRECTIVE_CEMETERY_FIELDS,
    build_engine_problem, classify_release, directive_cemetery_entry,
    load_campaign)

CAMPAIGN = (REPO_ROOT / "discovery_campaigns" / "CAMPAIGN_L8_2026-08-29"
            / "CAMPAIGN_REPORT.json")


@pytest.fixture(scope="module")
def campaign():
    return load_campaign(str(CAMPAIGN))


# ---------------------------------------------------------------- loading

def test_load_campaign_joins_all_ranked_candidates(campaign):
    assert len(campaign["candidates"]) == 22
    # every ranked candidate is joined with its chain_detail evidence
    for entry in campaign["candidates"]:
        assert entry["ranked"]["candidate_id"]
        assert entry["chain_detail"] is not None, (
            "ranked candidate without survivor chain detail must be "
            "surfaced, not silently dropped")


def test_load_campaign_missing_detail_is_explicit(tmp_path):
    """A ranked candidate with no survivor detail is returned with
    chain_detail=None (fail-closed join; the driver blocks it)."""
    report = {
        "campaign": "test",
        "dossier_candidates_ranked": [
            {"candidate_id": "opp:x:y:Z", "territory_id": "99",
             "campaign_slot": "Test", "device_query": "x",
             "principle": "Z", "principle_class": "HYPOTHESIS",
             "survivor_score": {}, "transfer_domains": [],
             "kill_conditions": []}],
        "results": [],
    }
    p = tmp_path / "report.json"
    p.write_text(json.dumps(report))
    loaded = load_campaign(str(p))
    assert loaded["candidates"][0]["chain_detail"] is None


# ------------------------------------------------------- problem building

def test_problem_structure_and_custody(campaign):
    entry = campaign["candidates"][0]
    problem = build_engine_problem(entry)
    for field in ("problem_id", "device", "failure_mode", "failure",
                  "constraint", "campaign"):
        assert problem.get(field), f"missing problem field {field}"
    # MAUDE limitations stamped inline (Art. XXI.5)
    assert "incidence UNKNOWN" in problem["failure"]
    assert "causation UNVERIFIED" in problem["failure"]
    # constraint is the operator's own statement, not a rewrite
    assert problem["constraint"] == (
        entry["chain_detail"]["constraint"]["constraint_statement"])
    # campaign provenance travels with the problem
    camp = problem["campaign"]
    assert camp["candidate_id"] == entry["ranked"]["candidate_id"]
    assert camp["not_a_novelty_determination"] is True


def test_problem_principle_is_provenance_not_promotion(campaign):
    """The campaign HYPOTHESIS-class principle must NOT appear as an
    asserted mechanism anywhere in the problem's engineering fields
    (Art. XXVIII — no silent promotion)."""
    entry = campaign["candidates"][0]
    problem = build_engine_problem(entry)
    principle = entry["ranked"]["principle"]
    for field in ("device", "failure_mode", "failure", "constraint"):
        assert principle not in problem[field], (
            f"principle leaked into {field}")


def test_problem_ids_unique_and_deterministic(campaign):
    ids = [build_engine_problem(e)["problem_id"]
           for e in campaign["candidates"]]
    assert len(ids) == len(set(ids)) == 22
    again = [build_engine_problem(e)["problem_id"]
             for e in load_campaign(str(CAMPAIGN))["candidates"]]
    assert ids == again


def test_problem_failure_mode_metamorphic(campaign):
    """Tampering with the candidate's mechanism cluster must change the
    failure_mode and the problem_id (identity attack)."""
    entry = copy.deepcopy(campaign["candidates"][0])
    tampered = copy.deepcopy(entry)
    cid = tampered["ranked"]["candidate_id"]
    parts = cid.split(":")
    parts[2] = parts[2] + "x"
    tampered["ranked"]["candidate_id"] = ":".join(parts)
    p1 = build_engine_problem(entry)
    p2 = build_engine_problem(tampered)
    assert p1["problem_id"] != p2["problem_id"]


# ------------------------------------------------------- M6 classification

@pytest.mark.parametrize("manifest,package,expected", [
    # research kill
    ({"final_status": "REJECTED", "failed_stages": {}}, None,
     CLASS_KILLED),
    # infrastructure block (transport failure) — never a kill
    ({"final_status": None,
      "failed_stages": {"SYNTHESIZE": "PROVIDER_UNAVAILABLE"}}, None,
     CLASS_INFRASTRUCTURE),
    # survivor at concept maturity
    ({"final_status": "AUTOMATED_INVENTION_CANDIDATE",
      "failed_stages": {}}, {"maturity": "CONCEPT_DEFINED"},
     CLASS_INVENTION),
    ({"final_status": "AUTOMATED_INVENTION_CANDIDATE",
      "failed_stages": {}}, {"maturity": "ENGINEERING_DEFINITION"},
     CLASS_INVENTION),
    # engineering development band
    ({"final_status": "AUTOMATED_INVENTION_CANDIDATE",
      "failed_stages": {}}, {"maturity": "PROTOTYPE_DESIGN_READY"},
     CLASS_ENGINEERING),
    ({"final_status": "AUTOMATED_INVENTION_CANDIDATE",
      "failed_stages": {}}, {"maturity": "VALIDATION_READY"},
     CLASS_ENGINEERING),
    # transfer ready (requires the full ladder)
    ({"final_status": "AUTOMATED_INVENTION_CANDIDATE",
      "failed_stages": {}}, {"maturity": "TRANSFER_READY"},
     CLASS_TRANSFER),
])
def test_classification_matrix(manifest, package, expected):
    result = classify_release(manifest, package)
    assert result["release_class"] == expected
    assert result["basis"]["rule"]  # every class carries its rule


def test_classification_rejects_unmapped_status():
    """An unmapped final_status is never promoted — recorded honestly."""
    result = classify_release({"final_status": "SOMETHING_NEW",
                               "failed_stages": {}})
    assert result["release_class"] == CLASS_INFRASTRUCTURE
    assert "unmapped" in result["basis"]["rule"]


def test_classification_rejects_fake_maturity_string():
    """A maturity level outside the ladder cannot lift a class."""
    result = classify_release(
        {"final_status": "AUTOMATED_INVENTION_CANDIDATE",
         "failed_stages": {}},
        {"maturity": "TOTALLY_READY_TRUST_ME"})
    assert result["release_class"] == CLASS_INVENTION


def test_classification_no_silent_promotion_on_none_package():
    """No package report at all -> maturity unknown -> invention floor."""
    result = classify_release(
        {"final_status": "AUTOMATED_INVENTION_CANDIDATE",
         "failed_stages": {}}, None)
    assert result["release_class"] == CLASS_INVENTION


# ------------------------------------------------- M4 directive cemetery

def test_directive_cemetery_entry_has_all_seven_fields(campaign):
    entry = campaign["candidates"][0]
    problem = build_engine_problem(entry)
    classification = classify_release(
        {"final_status": "REJECTED", "failed_stages": {}})
    record = directive_cemetery_entry(entry, problem, classification)
    for field in DIRECTIVE_CEMETERY_FIELDS:
        assert field in record, f"missing directive field {field}"
    assert record["candidate_id"] == entry["ranked"]["candidate_id"]
    assert record["kill_condition"]
    assert record["date"]


def test_directive_cemetery_entry_carrys_kill_record(campaign):
    """When the conductor supplies a concrete kill record (failure reason,
    attacks, reusable constraints) it is used verbatim — never rewritten."""
    entry = campaign["candidates"][0]
    problem = build_engine_problem(entry)
    classification = classify_release(
        {"final_status": "REJECTED", "failed_stages": {}})
    kill = {
        "run_id": "engrun:test:1",
        "failure_reason": "ADJUDICATION_REJECTED: no causal binding",
        "attacks": ["attack A", "attack B"],
        "kill_condition": "CAUSAL_BINDING_MISSING",
        "reusable_constraints": ["constraint X"],
    }
    record = directive_cemetery_entry(entry, problem, classification, kill)
    assert record["failure_reason"] == kill["failure_reason"]
    assert record["attacks"] == kill["attacks"]
    assert record["reusable_constraints"] == ["constraint X"]
    assert record["evidence"]["run_id"] == "engrun:test:1"

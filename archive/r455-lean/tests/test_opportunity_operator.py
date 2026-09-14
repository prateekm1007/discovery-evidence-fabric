"""Universal FAILURE->GAP->OPPORTUNITY operator tests (L6) — hermetic,
no network, Art. XVII hardened.

Every step of the 9-step chain must carry evidence or an explicit
epistemic class — these tests attack that requirement from both sides:
(1) each step's classification is present and never upgraded silently;
(2) negative controls: no evidence -> NO_EVIDENCE (never fabricated).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry import retrieval_log
from discovery_fabric.source_registry.base import (
    STATUS_EMPTY, STATUS_OK, SourceQueryResult, SourceRecord, utc_now,
)
from discovery_fabric.discovery_modes.device_failure import MechanismCluster
from discovery_fabric.discovery_modes import opportunity as opp


@pytest.fixture(autouse=True)
def _isolated_log(tmp_path, monkeypatch):
    monkeypatch.setattr(retrieval_log, "LOG_PATH", tmp_path / "retrieval_log.jsonl")
    yield


def _rec(source_id, role, record_id, normalized, title="t"):
    return SourceRecord(
        source_id=source_id, role=role, record_id=record_id, title=title,
        uri="https://example.org", retrieved_at=utc_now(), query="q",
        raw_payload_sha256="sha-" + record_id, normalized=normalized,
        provenance={"provider": source_id}, epistemic_state="OBSERVED",
        limitations=["x"],
    )


def _result(source_id, records, status=STATUS_OK):
    return SourceQueryResult(source_id=source_id, status=status, ok=True,
                             records=records, query="q", retrieved_at=utc_now())


RECALL_REC = _rec("fda_recall", "RECALL", "r1", {
    "root_cause_description": "Component fracture due to manufacturing defect",
    "reason": "device misassembly",
})
MAUDE_REC = _rec("fda_maude", "ADVERSE_EVENT", "m1", {
    "product_problems": ["Fracture"],
    "event_type": "Malfunction",
    "narrative_text": "Device fractured in vivo during normal use.",
})
CLUSTER = MechanismCluster(
    mechanism_label="fracture", report_count=7,
    contributing_records=[{"record_id": "m1", "raw_payload_sha256": "sha-m1",
                           "event_type": "Malfunction", "brand": "X"}])


class TestWhyTheyFail:
    def test_root_causes_carry_custody(self):
        why = opp.why_they_fail(_result("fda_recall", [RECALL_REC]),
                                _result("fda_maude", [MAUDE_REC]),
                                CLUSTER, "hip")
        assert why["epistemic_class"] == "EVIDENCE_BOUND"
        assert len(why["root_causes"]) == 1
        assert why["root_causes"][0]["custody"]["raw_payload_sha256"]

    def test_narratives_from_cluster_records_only(self):
        other = _rec("fda_maude", "ADVERSE_EVENT", "m2", {
            "narrative_text": "unrelated report"})
        why = opp.why_they_fail(_result("fda_recall", [RECALL_REC]),
                                _result("fda_maude", [MAUDE_REC, other]),
                                CLUSTER, "hip")
        assert len(why["narratives"]) == 1
        assert why["narratives"][0]["custody"]["record_id"] == "m1"

    def test_no_evidence_is_explicit_not_fabricated(self):
        # negative control (Art. VI): empty recall + no narrative text
        empty_recall = SourceQueryResult(source_id="fda_recall",
                                         status=STATUS_EMPTY, ok=True,
                                         records=[], query="q")
        maude_no_text = _rec("fda_maude", "ADVERSE_EVENT", "m1", {
            "product_problems": ["Fracture"], "event_type": "Malfunction"})
        why = opp.why_they_fail(empty_recall,
                                _result("fda_maude", [maude_no_text]),
                                CLUSTER, "hip")
        assert why["epistemic_class"] == "NO_EVIDENCE"
        assert why["root_causes"] == [] and why["narratives"] == []


class TestAlternativePrinciples:
    def _constraint(self):
        return {"constraint_statement":
                "Recurring fracture of hip implant components under load",
                "derivation_basis": {"mechanism": "fracture stress"}}

    def _attempted(self, relevant_titles=("Fracture fixation load path study",)):
        return {
            "literature": {
                "records": [
                    {"title": t, "relevance": "RELEVANT",
                     "relevance_basis": {"overlapping_terms": ["fracture"]}}
                    for t in relevant_titles
                ],
                "retrieved": len(relevant_titles),
            },
            "patents": {"primary": {"status": "OK"},
                        "secondary": {"status": "OK"}},
        }

    def test_alternative_principles_are_hypothesis_class(self):
        alts = opp.alternative_physical_principles(self._constraint(),
                                                   self._attempted())
        assert alts
        for a in alts:
            assert a["epistemic_class"] == "HYPOTHESIS"
            assert a["taxonomy_class"] == "ENGINEERING_TAXONOMY"
            assert "ABSENCE_OF_HITS_IS_NOT_NOVELTY" in a["caveat"]

    def test_engaged_principle_family_excluded(self):
        # attempts already working in tribology -> tribological principle
        # is NOT alternative for a wear constraint
        constraint = {"constraint_statement": "Recurring wear of bearing surface",
                      "derivation_basis": {"mechanism": "wear friction"}}
        attempted = self._attempted(
            ("Wear reduction tribological coating study",))
        alts = opp.alternative_physical_principles(constraint, attempted)
        assert all(a["principle"] != "TRIBOLOGICAL_SURFACING" for a in alts)

    def test_unmatched_constraint_yields_nothing(self):
        constraint = {"constraint_statement": "Unrelated topic entirely",
                      "derivation_basis": {"mechanism": ""}}
        assert opp.alternative_physical_principles(constraint,
                                                   self._attempted()) == []


class TestCrossDomainTransfer:
    def test_source_domain_excluded(self):
        transfer = opp.cross_domain_transfer(
            {"constraint_statement": "fracture of implant"},
            "ORTHOPEDICS",
            domains={"ORTHOPEDICS": "orthopedic implant",
                     "CARDIOVASCULAR": "cardiovascular device"})
        assert transfer["per_domain"]["ORTHOPEDICS"]["status"] == "SOURCE_DOMAIN_EXCLUDED"

    def test_all_five_directive_domains_default(self):
        assert set(opp.DIRECTIVE_DOMAINS) == {
            "ORTHOPEDICS", "CARDIOVASCULAR", "NEUROVASCULAR",
            "OPHTHALMOLOGY", "SURGICAL"}

    def test_transfer_evidence_carries_custody(self, monkeypatch):
        rec = _rec("europepmc", "SCIENTIFIC", "epmc:1", {
            "title": "Fracture management in cardiovascular devices",
            "pmid": "1"})
        monkeypatch.setattr(
            opp.EuropePmcConnector, "search",
            lambda self, q, timeout=25: _result("europepmc", [rec]))
        transfer = opp.cross_domain_transfer(
            {"constraint_statement": "fracture of implant"},
            "ORTHOPEDICS",
            domains={"CARDIOVASCULAR": "cardiovascular device"})
        d = transfer["per_domain"]["CARDIOVASCULAR"]
        assert d["status"] == "TRANSFER_EVIDENCE"
        assert d["records"][0]["custody"]["raw_payload_sha256"]
        assert "fracture" in d["records"][0]["constraint_overlap"]

    def test_killed_domain_is_measured_not_absent(self, monkeypatch):
        rec = _rec("europepmc", "SCIENTIFIC", "epmc:2", {
            "title": "Totally different topic", "pmid": "2"})
        monkeypatch.setattr(
            opp.EuropePmcConnector, "search",
            lambda self, q, timeout=25: _result("europepmc", [rec]))
        transfer = opp.cross_domain_transfer(
            {"constraint_statement": "fracture of implant"},
            "ORTHOPEDICS",
            domains={"OPHTHALMOLOGY": "ophthalmic device"})
        d = transfer["per_domain"]["OPHTHALMOLOGY"]
        assert d["status"] == "KILLED_NO_USABLE_TRANSFER"
        assert d["retrieved"] == 1

    def test_provider_failure_is_not_absence(self, monkeypatch):
        def boom(self, q, timeout=25):
            return SourceQueryResult(source_id="europepmc",
                                     status="SEARCH_FAILED", ok=False,
                                     query=q)
        monkeypatch.setattr(opp.EuropePmcConnector, "search", boom)
        transfer = opp.cross_domain_transfer(
            {"constraint_statement": "fracture of implant"},
            "ORTHOPEDICS",
            domains={"SURGICAL": "surgical instrument"})
        d = transfer["per_domain"]["SURGICAL"]
        assert d["status"] == "SEARCH_FAILED"
        assert "not absence" in d["note"]


class TestInventionCandidate:
    def _run_candidate(self):
        constraint = {"constraint_statement": "Recurring fracture of implant"}
        principles = opp.alternative_physical_principles(
            constraint,
            {"literature": {"records": [], "retrieved": 0},
             "patents": {"primary": {"status": "OK"},
                         "secondary": {"status": "OK"}}})
        transfer = {"per_domain": {
            "CARDIOVASCULAR": {"status": "TRANSFER_EVIDENCE"}}}
        return opp.invention_candidate("hip prosthesis", CLUSTER, constraint,
                                       principles, transfer)

    def test_candidate_has_kill_conditions(self):
        cand = self._run_candidate()
        conds = {k["condition"] for k in cand["kill_conditions"]}
        assert {"PRIOR_ART_COLLISION", "PHYSICS_INFEASIBILITY",
                "TRANSFER_INVALIDITY", "PROBLEM_SIGNAL_COLLAPSE"} <= conds
        for k in cand["kill_conditions"]:
            assert k["test"] and k["kill_if"]

    def test_candidate_classes_never_upgraded(self):
        cand = self._run_candidate()
        assert cand["synthesis_class"] == "AI_INFERENCE"
        assert cand["mechanism_hypothesis"]["epistemic_class"] == "HYPOTHESIS"
        assert cand["problem"]["epistemic_class"].startswith("OBSERVED")
        assert cand["cross_domain_evidence"]["epistemic_class"] == "EVIDENCE_BOUND"
        assert cand["not_a_novelty_determination"] is True

    def test_strongest_alternative_explanation_present(self):
        # Art. XXXII: retrieval narrowness disclosed on every candidate
        cand = self._run_candidate()
        assert "retrieval narrowness" in cand["strongest_alternative_explanation"]

    def test_candidate_id_deterministic(self):
        c1 = self._run_candidate()
        c2 = self._run_candidate()
        assert c1["candidate_id"] == c2["candidate_id"]


class TestDiscoverOpportunity:
    def test_blocked_provider_short_circuits(self, monkeypatch):
        monkeypatch.setattr(
            opp, "retrieve_failures",
            lambda q, brand_name=None, timeout=30: {
                "blocked": True, "provider_failures": ["fda_maude"],
                "maude": None, "recall": None})
        res = opp.discover_opportunity("hip prosthesis", "ORTHOPEDICS")
        assert res["blocked"] is True
        assert res["candidates"] == []
        assert res["chain_steps"][0]["status"] == "BLOCKED_PROVIDER_FAILURE"

    def test_problem_not_documented_gate(self, monkeypatch):
        empty = SourceQueryResult(source_id="fda_maude", status=STATUS_EMPTY,
                                  ok=True, records=[], query="q")
        empty_r = SourceQueryResult(source_id="fda_recall", status=STATUS_EMPTY,
                                    ok=True, records=[], query="q")
        monkeypatch.setattr(opp, "retrieve_failures",
                            lambda q, brand_name=None, timeout=30: {
                                "blocked": False, "maude": empty,
                                "recall": empty_r,
                                "provider_failures": []})
        res = opp.discover_opportunity("nonexistent device", "ORTHOPEDICS")
        assert any(s["step"] == "problem_existence_gate"
                   and s["status"] == "PROBLEM_NOT_DOCUMENTED"
                   for s in res["chain_steps"])

    def test_full_chain_runs_all_nine_steps(self, monkeypatch):
        maude = _result("fda_maude", [MAUDE_REC] * 7)
        recall = _result("fda_recall", [RECALL_REC])
        monkeypatch.setattr(opp, "retrieve_failures",
                            lambda q, brand_name=None, timeout=30: {
                                "blocked": False, "maude": maude,
                                "recall": recall,
                                "provider_failures": []})
        monkeypatch.setattr(
            opp, "retrieve_attempted_solutions",
            lambda q, mech, timeout=30: {
                "literature": {"records": [], "retrieved": 0},
                "patents": {"primary": {"status": "OK"},
                            "secondary": {"status": "OK"}},
                "query": "q"})
        monkeypatch.setattr(
            opp, "cross_domain_transfer",
            lambda constraint, source_domain, domains=None, timeout=30: {
                "per_domain": {"CARDIOVASCULAR":
                               {"status": "TRANSFER_EVIDENCE"}}})
        res = opp.discover_opportunity("hip prosthesis", "ORTHOPEDICS")
        step_names = [s["step"] for s in res["chain_steps"]]
        assert "real_world_failure" in step_names
        assert "failure_mechanism" in step_names
        assert any(s.startswith("chain:") for s in step_names)
        assert res["candidates"]
        cand = res["candidates"][0]
        for part in ("constraint", "attempted_solutions", "why_they_fail",
                     "remaining_limitation",
                     "alternative_physical_principles",
                     "cross_domain_transfer"):
            assert part in cand["chain_detail"], part
        assert res["epistemic_summary"]["candidate"] == "AI_INFERENCE"

    def test_every_chain_step_has_epistemic_summary(self):
        # the directive's requirement, stated once at the operator level
        for key, val in {
                "problem": "OBSERVED", "constraint": "AI_INFERENCE",
                "why_they_fail": "EVIDENCE_BOUND", "gap": "AI_INFERENCE",
                "principles": "HYPOTHESIS", "transfer": "EVIDENCE_BOUND",
                "candidate": "AI_INFERENCE"}.items():
            assert key in opp._assemble("x", [], []).__getitem__(
                "epistemic_summary")

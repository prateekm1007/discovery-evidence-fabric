"""R449 Evidence Fabric battery — hermetic (no network).

Covers the constitutional contracts of the evidence-fabric layer:
  1. the canonical EvidenceRecord schema (Art. II/III: exact-span
     custody; the LLM interprets, never redefines)
  2. deterministic evidence identity (Art. VI)
  3. fail-closed admissibility (unverified license => BLOCKED, never
     in the pool)
  4. relevance adjudication, both modes (Art. XXI.4: keyword collision
     is not relevance)
  5. endpoint-aware custody verification: filter row_idx basis +
     search document-anchored basis + tamper detection + the honest
     UNKNOWN (Art. XXV)
  6. source substitution: provenance preserved, coverage limitation
     recorded, the forbidden LLM ladder never taken (Art. IV)
  7. the registry promotion rule (fail-closed; Art. XXVII)
  8. novelty levels: component adjacency is NOT invention credit
     (BS-024 / Art. XLVI)
  9. contradiction: absence is not contradiction (Art. XXV)
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.evidence_fabric import connectors as hc  # noqa: E402
from discovery_fabric.evidence_fabric import substitution as sub  # noqa: E402
from discovery_fabric.evidence_fabric import (  # noqa: E402
    adjudicate_relevance, problem_elements, problem_queries,
)
from discovery_fabric.evidence_fabric.contradiction import (  # noqa: E402
    CONTRADICTION_VERDICTS, _adjudicate, contradiction_queries,
)
from discovery_fabric.evidence_fabric.evidence_record import (  # noqa: E402
    ADMISSIBILITY_STATES, ExactSpan, SourceIdentity, EvidenceRecord,
    Provenance, Admissibility, build_evidence_record, make_evidence_id,
    sha256_text, validate_record, verify_span_custody,
)
from discovery_fabric.evidence_fabric.novelty import (  # noqa: E402
    NOVELTY_LEVELS, adjudicate_novelty_level,
)
from discovery_fabric.evidence_fabric.registry import (  # noqa: E402
    load_license_registry, load_registry, validate_registry,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

SRC = {
    "source_id": "wopto", "family": "E1_patent_intelligence",
    "dataset_id": "baber/WOPTO", "source_url":
        "https://huggingface.co/datasets/baber/WOPTO",
    "config": "default", "split": "train",
    "dataset_revision": "b35b19cf1d2a3f30a30075bb86fd587b9a34e378",
    "license": "cc-by-4.0", "license_verified": True,
    "license_basis": "CARD_DECLARATION_ONLY",
    "provenance_origin": "exported from Google Patents Public Data",
}


def _row(text="Seawater corrosion inhibitor containing plant extracts "
              "reduces pitting on copper-nickel alloy tubing."):
    return {"publication_number": "CN-103498163-A",
            "abstract_text": text, "title_text": "corrosion inhibitor"}


def _record(**kw):
    source = kw.pop("source", SRC)
    return build_evidence_record(
        source=source, row=kw.pop("row", _row()),
        row_idx=kw.pop("row_idx", 42141),
        text_field=kw.pop("text_field", "abstract_text"),
        document_field=kw.pop("document_field",
                              "publication_number"),
        retrieval_endpoint=kw.pop("endpoint", "search"),
        connector_state="SUCCESS", license_verified=True,
        license_basis="CARD_DECLARATION_ONLY", card_license="cc-by-4.0",
        origin_description="exported from Google Patents Public Data",
        retrieval_query=kw.pop("query", "seawater corrosion copper"))


PROBLEM = {
    "device": "seawater-cooled copper-nickel condenser tubing",
    "failure": "pitting corrosion and biofilm fouling degrade heat "
               "transfer",
    "constraint": "12-year retubing interval",
    "user_text": "90/10 copper-nickel tubing develops pitting within "
                 "18 months in polluted estuary water.",
}


# ---------------------------------------------------------------------------
# 1. the canonical record + schema
# ---------------------------------------------------------------------------

class TestEvidenceRecordSchema:

    def test_record_validates(self):
        rec = _record().to_dict()
        assert validate_record(rec) == []

    def test_required_fields_missing_fail(self):
        rec = _record().to_dict()
        del rec["exact_span"]
        assert validate_record(rec) != []

    def test_content_hash_must_be_span_hash(self):
        rec = _record().to_dict()
        rec["content_hash"] = "0" * 64
        errs = validate_record(rec)
        assert any("content_hash" in e for e in errs)

    def test_admissibility_vocabulary_closed(self):
        rec = _record().to_dict()
        rec["admissibility"]["state"] = "PROBABLY_FINE"
        assert any("admissibility" in e
                   for e in validate_record(rec))

    def test_deterministic_identity(self):
        a = make_evidence_id("baber/WOPTO", "default", "train", 1,
                             "abstract_text", "x" * 64)
        b = make_evidence_id("baber/WOPTO", "default", "train", 1,
                             "abstract_text", "x" * 64)
        c = make_evidence_id("baber/WOPTO", "default", "train", 2,
                             "abstract_text", "x" * 64)
        d = make_evidence_id("baber/WOPTO", "default", "train", 1,
                             "abstract_text", "y" * 64)
        assert a == b and a != c and a != d

    def test_missing_text_field_returns_none(self):
        row = {"publication_number": "X", "abstract_text": None}
        assert build_evidence_record(
            source=SRC, row=row, row_idx=0, text_field="abstract_text",
            document_field="publication_number",
            retrieval_endpoint="search", connector_state="SUCCESS",
            license_verified=True, license_basis="CARD_DECLARATION_ONLY",
            card_license="cc-by-4.0", origin_description="") is None

    def test_engine_item_carries_additive_fields_only(self):
        item = _record().to_engine_item()
        for k in ("id", "source_type", "source", "source_id",
                  "title", "abstract", "content_hash", "provenance",
                  "retrieval_timestamp"):
            assert k in item
        assert item["evidence_fabric"]["exact_span"]["document_ref"] == \
            "CN-103498163-A"

    def test_measurements_render_into_display_abstract(self):
        row = {"mol_id": "gdb_1", "smiles": "C",
               "gap": "0.5048", "homo": "-0.3877"}
        rec = build_evidence_record(
            source={"source_id": "qm9", "family":
                    "E5_chemical_intelligence",
                    "dataset_id": "liuganghuggingface/QM9",
                    "source_url": "u", "config": "default",
                    "split": "train", "dataset_revision": "r",
                    "license": "apache-2.0",
                    "license_verified": True,
                    "license_basis": "CARD_DECLARATION_ONLY",
                    "provenance_origin": "QM9"},
            row=row, row_idx=0, text_field="smiles",
            document_field="mol_id", retrieval_endpoint="filter",
            connector_state="SUCCESS", license_verified=True,
            license_basis="CARD_DECLARATION_ONLY",
            card_license="apache-2.0", origin_description="QM9",
            measurement_fields=["gap", "homo"])
        item = rec.to_engine_item()
        assert "gap=0.5048" in item["abstract"]
        assert rec.measurements[0]["value"] == "0.5048"


# ---------------------------------------------------------------------------
# 2. fail-closed admissibility
# ---------------------------------------------------------------------------

class TestFailClosed:

    def test_unverified_license_blocks(self):
        rec = build_evidence_record(
            source={**SRC, "license_verified": False, "license": None},
            row=_row(), row_idx=1, text_field="abstract_text",
            document_field="publication_number",
            retrieval_endpoint="search", connector_state="SUCCESS",
            license_verified=False, license_basis="UNVERIFIED",
            card_license=None, origin_description="")
        assert rec.admissibility.state == "BLOCKED_LICENSE_UNVERIFIED"
        assert not rec.admissibility.is_admitted()


# ---------------------------------------------------------------------------
# 3. relevance adjudication (both modes)
# ---------------------------------------------------------------------------

class TestRelevance:

    def test_text_overlap_relevant(self):
        rec = _record()
        d = adjudicate_relevance(
            rec, ["seawater", "corrosion", "copper", "pitting"], [],
            "q")
        assert d["verdict"] == "RELEVANT"
        assert d["mode"] == "TEXT_TERM_OVERLAP"

    def test_keyword_collision_rejected(self):
        row = {"publication_number": "X",
               "abstract_text": "A cooking recipe for copper pots with "
                                "plant extracts and herbs."}
        rec = _record(row=row)
        d = adjudicate_relevance(rec, ["seawater", "condenser"], [], "q")
        # only 'copper'/'plant'/'extracts' overlaps -> not the problem's
        # domain pair set -> WEAK or REJECTED, never RELEVANT
        assert d["verdict"] in ("WEAK_RELEVANCE", "REJECTED")

    def test_element_overlap_structured_mode(self):
        row = {"chemical_formula_reduced": "Cu2O", "immutable_id": "a1"}
        rec = _record(row=row, source={**SRC, "source_id": "lemat_rho",
                                       "family":
                                       "E4_materials_intelligence"},
                      text_field="chemical_formula_reduced",
                      document_field="immutable_id")
        d = adjudicate_relevance(rec, [], ["Cu", "Ni"], "q")
        assert d["mode"] == "STRUCTURED_ELEMENT_OVERLAP"
        assert d["verdict"] == "RELEVANT"
        assert "Cu" in d["structural_metals_shared"]

    def test_nonmetal_only_overlap_is_weak(self):
        row = {"chemical_formula_reduced": "C3N", "immutable_id": "a2"}
        rec = _record(row=row, source={**SRC, "source_id": "lemat_rho",
                                       "family":
                                       "E4_materials_intelligence"},
                      text_field="chemical_formula_reduced",
                      document_field="immutable_id")
        d = adjudicate_relevance(rec, [], ["Cu", "Ni"], "q")
        # C/N shared only via the organic backbone — not Cu/Ni
        assert d["verdict"] in ("WEAK_RELEVANCE", "REJECTED")

    def test_problem_elements_expands_names(self):
        assert problem_elements(PROBLEM)[:2] == ["Cu", "Ni"]

    def test_problem_queries_never_carry_solution_class(self):
        qs = problem_queries(PROBLEM)
        for q in qs:
            low = q.lower()
            assert "design" not in low
            assert "arrangement" not in low


# ---------------------------------------------------------------------------
# 4. endpoint-aware custody verification
# ---------------------------------------------------------------------------

class TestCustody:

    def test_filter_row_idx_basis_pass(self):
        rec = _record(endpoint="filter", row_idx=0).to_dict()
        v = verify_span_custody(rec, _row())
        assert v["verdict"] == "PASS"
        assert v["basis"] == "ROW_IDX"

    def test_row_idx_tamper_fails(self):
        rec = _record().to_dict()
        v = verify_span_custody(rec, {"abstract_text": "different bytes",
                                      "publication_number": "X"})
        assert v["verdict"] == "FAIL"

    def test_search_document_anchored_pass(self):
        rec = _record().to_dict()
        rows = [{"row": _row()}]
        v = verify_span_custody(rec, None, search_rows=rows)
        assert v["verdict"] == "PASS"
        assert v["basis"] == "DOCUMENT_ANCHORED"

    def test_search_tampered_hash_fails(self):
        rec = _record().to_dict()
        rec["exact_span"]["text_sha256"] = "0" * 64
        rows = [{"row": _row()}]
        v = verify_span_custody(rec, None, search_rows=rows)
        assert v["verdict"] == "FAIL"

    def test_search_wrong_document_is_unknown(self):
        rec = _record().to_dict()
        rows = [{"row": {"publication_number": "OTHER-1",
                         "abstract_text": "x"}}]
        v = verify_span_custody(rec, None, search_rows=rows)
        assert v["verdict"] == "UNKNOWN"

    def test_missing_refetch_is_unknown_never_pass(self):
        rec = _record().to_dict()
        v = verify_span_custody(rec, None)
        assert v["verdict"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# 5. source substitution (Phase 5)
# ---------------------------------------------------------------------------

class TestSubstitution:

    def test_ladder_declared_alternates(self):
        lad = sub.substitution_ladder()
        assert "uspto_patents" in lad["wopto"]["alternates"]
        assert lad["wopto"]["coverage_limitation"]

    def test_substitute_resolves_available_production(self):
        avail = [{"source_id": "uspto_patents", "status": "PRODUCTION"}]
        s = sub.substitute_source("wopto", sub.substitution_ladder(),
                                  avail)
        assert s["source_id"] == "uspto_patents"

    def test_substitute_none_when_no_alternate(self):
        s = sub.substitute_source("wopto", sub.substitution_ladder(), [])
        assert s is None

    def test_no_llm_ladder_exists(self):
        """The forbidden ladder (source unavailable -> LLM 'knows' ->
        evidence) must have NO functional representation in the module:
        no LLM registry import, no generate call — substitution resolves
        ONLY to declared registry sources."""
        src = Path(sub.__file__).read_text()
        assert "llm_registry" not in src
        assert "llm_generate" not in src
        assert "from discovery_fabric.a2" not in src

    def test_ladder_copies_not_mutates(self):
        lad = sub.substitution_ladder()
        lad["wopto"]["alternates"].append("x")
        assert "x" not in sub.substitution_ladder()["wopto"]["alternates"]


# ---------------------------------------------------------------------------
# 6. the committed registry (Art. X authority)
# ---------------------------------------------------------------------------

class TestRegistry:

    def test_registry_loads_and_validates(self):
        reg = load_registry()
        assert reg["artifact_type"] == "EVIDENCE_SOURCE_REGISTRY"
        assert validate_registry(reg) == []

    def test_promotion_rule_fail_closed(self):
        reg = load_registry()
        for s in reg["sources"]:
            if s["status"] == "PRODUCTION":
                assert s["license_verified"] is True
                assert s["dataset_revision"]
                assert s["license_text_hash"]

    def test_subset_shape_is_ten_seats(self):
        reg = load_registry()
        sel = [s for s in reg["sources"] if s["selection"]["selected"]]
        assert len(sel) == 10
        assert len(sel) == len({s["source_id"] for s in sel})

    def test_license_registry_present(self):
        lic = load_license_registry()
        assert lic["records"]
        assert lic["summary"]["verified"] >= 5

    def test_production_sources_flattens_schema(self):
        from discovery_fabric.evidence_fabric.registry import \
            production_sources
        srcs = production_sources()
        assert srcs, "no production sources frozen"
        for s in srcs:
            assert s.get("config") and s.get("text_field")


# ---------------------------------------------------------------------------
# 7. novelty defense (Phase 11 / BS-024)
# ---------------------------------------------------------------------------

class TestNovelty:

    def test_known_mechanism_no_credit(self):
        item = {"id": "e1", "abstract":
                "Dense tantalum oxide films deposited by ALD improve "
                "corrosion resistance of copper-nickel condenser "
                "tubing in seawater."}
        d = adjudicate_novelty_level(
            "ALD tantalum oxide film corrosion protection for "
            "copper-nickel tubing", "apply ALD coating", [item])
        assert d["level"] in ("KNOWN_MECHANISM", "CAUSAL_COMBINATION")

    def test_adjacency_is_low_credit(self):
        a = {"id": "e1", "abstract":
             "Copper-nickel alloy tubing resists seawater corrosion "
             "through protective film formation."}
        b = {"id": "e2", "abstract":
             "Ultrasonic anti-fouling transducers prevent biofilm "
             "fouling on heat exchanger tubing surfaces."}
        d = adjudicate_novelty_level(
            "copper-nickel alloy tubing with ultrasonic anti-fouling "
            "transducers",
            "combine alloy tubing with ultrasonic transducers", [a, b])
        assert d["level"] == "CAUSAL_COMBINATION"
        assert "adjacency" in " ".join(d["basis"]).lower()

    def test_interaction_marker_upgrades(self):
        a = {"id": "e1", "abstract":
             "Copper-nickel alloy tubing corrosion film formation; "
             "synergistic interaction with ultrasonic vibration "
             "prevents biofilm fouling on condenser tubing."}
        d = adjudicate_novelty_level(
            "copper-nickel alloy tubing with ultrasonic anti-fouling",
            "combine alloy tubing with ultrasonic transducers", [a])
        assert d["level"] == "MEANINGFUL_NEW_INTERACTION"

    def test_insufficient_evidence_is_honest(self):
        d = adjudicate_novelty_level("quantum vortex turbine", "x", [])
        assert d["level"] == "INSUFFICIENT_EVIDENCE"

    def test_levels_closed(self):
        assert set(NOVELTY_LEVELS) == {
            "KNOWN_MECHANISM", "CAUSAL_COMBINATION",
            "MEANINGFUL_NEW_INTERACTION", "NEW_OPERATING_REGIME",
            "INSUFFICIENT_EVIDENCE"}


# ---------------------------------------------------------------------------
# 8. contradiction discipline (Phase 8)
# ---------------------------------------------------------------------------

class TestContradiction:

    def test_absence_is_not_contradiction(self):
        v = _adjudicate("mechanism", [], [], [{"state": "EMPTY_RESULT"}])
        assert v["verdict"] == "NO_CONTRADICTING_EVIDENCE_FOUND"
        assert "NOT a novelty" in v["basis"]

    def test_all_failed_is_unknown(self):
        v = _adjudicate("m", [], [], [{"state": "UNKNOWN"}])
        assert v["verdict"] == "CONTRADICTION_SEARCH_UNKNOWN"

    def test_queries_derive_from_mechanism(self):
        qs = contradiction_queries(
            "ultrasonic vibration prevents biofilm fouling")
        assert qs and all("biofilm" in q or "ultrasonic" in q
                          for q in qs)

    def test_verdicts_closed(self):
        assert set(CONTRADICTION_VERDICTS) == {
            "MECHANISM_SURVIVES", "MECHANISM_WEAKENED", "MECHANISM_DIES",
            "NO_CONTRADICTING_EVIDENCE_FOUND",
            "CONTRADICTION_SEARCH_UNKNOWN"}


# ---------------------------------------------------------------------------
# 9. connector state classification (Art. XXI.3 — never absence)
# ---------------------------------------------------------------------------

class TestConnectorStates:

    def test_unknown_states_set(self):
        for s in ("TIMEOUT", "RATE_LIMITED", "PROVIDER_ERROR",
                  "PARSE_ERROR", "UNAVAILABLE", "NOT_ATTEMPTED",
                  "INDEX_LOADING"):
            assert hc.classify_unknown(s)
        assert not hc.classify_unknown("SUCCESS")
        assert not hc.classify_unknown("EMPTY_RESULT")

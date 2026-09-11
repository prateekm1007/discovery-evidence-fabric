"""tests/test_r446_cio_extraction.py — R446-C1 Task 1: the canonical
CIO field extraction contract.

The defect being closed: the production drivers recorded HTTP 200 while
their extractors read phantom schema keys (architecture.mechanism /
engineering.technology_class / artifact_state.components /
experiment_contract / top-level summary-mechanism-technology_class) —
keys that never existed in the CIO body. The R444/R445 recorded
cio_summary values (mechanism "", technology_class null, n_components
0 / null) were extraction gaps presented next to cio_http 200.

The contract this battery pins (the directive's acceptance):
  1. POSITIVE: a production-shaped CIO body (canonical shape from
     toscanini/cio.py build_cio + the server's present=true) extracts
     every canonical field -> CIO_FIELDS_VERIFIED.
  2. NEGATIVE (malformed): the phantom-schema body that would have
     fooled the OLD extractor is typed CIO_MISSING_CANONICAL_FIELDS —
     HTTP 200 + missing canonical fields is EXPLICITLY INCOMPLETE,
     never semantic success.
  3. The present=false honest no-artifacts 200 stays its own typed
     state (never an error, never success).
  4. Non-dict bodies, wrong-kind bodies -> typed incomplete.
  5. REAL integration: build_cio over a committed run dir yields a body
     whose canonical paths the extractor consumes (the schema contract
     between the server and the extractor is exercised on real bytes).
  6. The retired extractors: r444_production_verify._cio_summary and
     the r445 driver's recorded cio_summary now carry the typed
     extraction state (no phantom keys resurrected).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

from r446_cio_extraction import (  # noqa: E402
    CIO_KIND,
    MISSING,
    NOT_CIO,
    NOT_JSON,
    PRESENT_FALSE,
    VERIFIED,
    extract_cio_fields,
    summarize_for_record,
)

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "r446"
POSITIVE = json.loads(
    (FIXTURES / "cio_production_positive.json").read_text())
PHANTOM = json.loads(
    (FIXTURES / "cio_malformed_phantom_schema.json").read_text())


# ---------------------------------------------------------------------------
# 1. The positive production-shaped fixture
# ---------------------------------------------------------------------------
class TestPositiveProductionShape:
    def test_canonical_fields_verified(self):
        out = extract_cio_fields(200, POSITIVE)
        assert out["extraction_state"] == VERIFIED
        assert out["missing_canonical_fields"] == []

    def test_mechanism_extracted_from_identity(self):
        out = extract_cio_fields(200, POSITIVE)
        mech = out["fields"]["mechanism"]
        assert mech["mechanism"] and "cascade filtration" in \
            mech["mechanism"]
        assert mech["intervention"] and "wedge-wire" in \
            mech["intervention"]
        assert mech["expected_effect"] and "thermal-crown" in \
            mech["expected_effect"]

    def test_domain_family_extracted_canonical(self):
        out = extract_cio_fields(200, POSITIVE)
        assert out["fields"]["domain_family"] == "thermal"

    def test_components_counted_from_geometry(self):
        out = extract_cio_fields(200, POSITIVE)
        assert out["fields"]["n_components"] == 5

    def test_decisive_experiment_present_with_contract(self):
        out = extract_cio_fields(200, POSITIVE)
        assert out["fields"]["decisive_experiment_present"] is True

    def test_technology_class_is_documented_not_extracted(self):
        # technology_class is a bridge-layer field deliberately NOT
        # projected into the CIO; the extractor records the fact rather
        # than inventing a value (Art. XXV).
        out = extract_cio_fields(200, POSITIVE)
        assert "technology_class" not in out["fields"]
        assert "technology_class" in out["fields"][
            "technology_class_note"]

    def test_summarize_for_record_carries_typed_state(self):
        s = summarize_for_record(200, POSITIVE)
        assert s["cio_http"] == 200
        assert s["cio_extraction_state"] == VERIFIED
        assert s["domain_family"] == "thermal"
        assert s["n_components"] == 5
        assert s["decisive_experiment_present"] is True
        assert "cascade filtration" in s["mechanism"]


# ---------------------------------------------------------------------------
# 2. The malformed / phantom-schema negative — the old extractor's
#    blind spot is now the adversarial case
# ---------------------------------------------------------------------------
class TestMalformedAndMissing:
    def test_phantom_schema_body_is_missing_canonical_fields(self):
        # THE R444 DEFECT SHAPE: kind is right, present=true, but every
        # field the OLD extractor read (architecture.mechanism,
        # engineering.technology_class, artifact_state.components,
        # experiment_contract) is a phantom — the canonical paths are
        # absent. This body must be EXPLICITLY INCOMPLETE.
        out = extract_cio_fields(200, PHANTOM)
        assert out["extraction_state"] == MISSING
        assert set(out["missing_canonical_fields"]) == {
            "identity.mechanism", "geometry.domain_family",
            "geometry.components", "experiment.decisive_experiment"}

    def test_http_200_missing_fields_is_never_semantic_success(self):
        # the acceptance sentence, mechanically: HTTP 200 + missing
        # fields can never be interpreted as semantic success
        for body in (
            PHANTOM,
            {"kind": CIO_KIND, "present": True},  # empty CIO
            {"kind": CIO_KIND, "present": True,
             "identity": {"mechanism": "x"}},  # partial
            {"kind": CIO_KIND, "present": True,
             "identity": {"mechanism": {"mechanism": "x"}},
             "geometry": {"domain_family": "thermal"}},  # still partial
        ):
            out = extract_cio_fields(200, body)
            assert out["extraction_state"] != VERIFIED, body
            assert out["extraction_state"] == MISSING
            assert out["missing_canonical_fields"]

    def test_null_canonical_fields_count_as_missing(self):
        body = json.loads(json.dumps(POSITIVE))
        body["geometry"]["domain_family"] = None
        out = extract_cio_fields(200, body)
        assert out["extraction_state"] == MISSING
        assert out["missing_canonical_fields"] == [
            "geometry.domain_family"]

    def test_empty_string_mechanism_is_missing(self):
        body = json.loads(json.dumps(POSITIVE))
        body["identity"]["mechanism"]["mechanism"] = "   "
        out = extract_cio_fields(200, body)
        assert out["extraction_state"] == MISSING
        assert "identity.mechanism" in out["missing_canonical_fields"]

    def test_present_false_honest_is_its_own_typed_state(self):
        # the server's honest no-artifacts 200 (present=false + note)
        out = extract_cio_fields(200, {
            "kind": CIO_KIND, "present": False,
            "note": "no invention-side artifacts on this run yet"})
        assert out["extraction_state"] == PRESENT_FALSE
        assert "honest absence" in out["note"]

    def test_non_dict_body_typed_not_json(self):
        for body in (None, "text", 42, [1, 2]):
            out = extract_cio_fields(200, body)
            assert out["extraction_state"] == NOT_JSON

    def test_wrong_kind_body_typed_not_cio(self):
        out = extract_cio_fields(200, {"kind": "SOMETHING_ELSE",
                                       "present": True})
        assert out["extraction_state"] == NOT_CIO

    def test_components_empty_list_is_present_typed(self):
        # geometry.components may honestly be [] (no bridge ran) — the
        # FIELD is present when the key carries list type; the count is
        # the honest zero
        body = json.loads(json.dumps(POSITIVE))
        body["geometry"]["components"] = []
        out = extract_cio_fields(200, body)
        assert out["fields"]["n_components"] == 0
        assert out["fields"]["components_present_typed"] is True
        # empty components is NOT itself a missing field
        assert "geometry.components" not in out["missing_canonical_fields"]
        assert out["extraction_state"] == VERIFIED

    def test_summarize_for_record_never_collapses_to_http_code(self):
        s = summarize_for_record(200, PHANTOM)
        assert s["cio_extraction_state"] == MISSING
        assert s["cio_missing_fields"]
        assert s["domain_family"] is None


# ---------------------------------------------------------------------------
# 3. REAL integration: the extractor consumes build_cio's actual output
#    (the server<->extractor schema contract, exercised on real bytes
#    from a committed run dir — no network)
# ---------------------------------------------------------------------------
REAL_RUN_DIR = (REPO_ROOT / "R445" / "EVOLUTION_RUNS" /
                "evol-x02-bus-fastcharge-lithium-plating")


@pytest.mark.skipif(not REAL_RUN_DIR.exists(),
                    reason="committed evolution run dir not present")
class TestRealBuildCioShape:
    def test_real_cio_body_canonical_paths_consumed(self):
        from toscanini import cio as _cio
        sess = {"session_id": "evol-x02-shape-probe",
                "run_dir": str(REAL_RUN_DIR),
                "user_text": "shape probe",
                "final_status": "EVOLVED_INVENTION_CANDIDATE",
                "origin": "test"}
        obj = _cio.build_cio(sess)
        assert obj is not None
        # the server-side projection (present=true, run_dir stripped)
        obj["present"] = True
        (obj.get("provenance") or {}).pop("run_dir", None)

        out = extract_cio_fields(200, obj)
        # the committed evolution run predates the bridge on that run
        # dir — domain_family is honestly None there; the extraction
        # must type it MISSING (never error, never success)
        assert out["extraction_state"] == MISSING
        assert "geometry.domain_family" in out["missing_canonical_fields"]
        # mechanism + experiment extracted from the REAL body
        assert out["fields"]["mechanism"]["mechanism"]
        assert out["fields"]["decisive_experiment_present"] is True

    def test_real_cio_mechanism_dict_shape_normalized(self):
        from toscanini import cio as _cio
        sess = {"session_id": "evol-x02-shape-probe",
                "run_dir": str(REAL_RUN_DIR),
                "user_text": "shape probe",
                "final_status": "EVOLVED_INVENTION_CANDIDATE",
                "origin": "test"}
        obj = _cio.build_cio(sess)
        assert isinstance(obj, dict)
        mech = (obj.get("identity") or {}).get("mechanism")
        # the real CIO carries mechanism as dict (or str) — either way
        # the extractor normalizes without inventing content
        out = extract_cio_fields(200, obj)
        norm = out["fields"]["mechanism"]
        assert norm["mechanism"] is not None
        if isinstance(mech, dict):
            assert norm["mechanism"] == mech.get("mechanism")


# ---------------------------------------------------------------------------
# 4. The retired driver extractors now carry the typed state
# ---------------------------------------------------------------------------
class TestDriversUseCanonicalExtraction:
    def test_r444_driver_summary_is_typed(self):
        import r444_production_verify as pv
        out = pv._cio_summary(POSITIVE)
        assert out["extraction_state"] == VERIFIED
        assert out["fields"]["domain_family"] == "thermal"

        out2 = pv._cio_summary(PHANTOM)
        assert out2["extraction_state"] == MISSING

    def test_r444_driver_has_no_phantom_keys_left(self):
        import r444_production_verify as pv
        src = Path(pv.__file__).read_text()
        # code-level phantom patterns (the docstring documents the
        # retired keys — that is the memory, not the code)
        assert 'body.get("architecture")' not in src
        assert '.get("artifact_state")' not in src
        assert 'body.get("experiment_contract")' not in src
        assert 'eng.get("technology_class")' not in src

    def test_r445_driver_records_typed_summary(self):
        import r445_production_verify as r445
        src = Path(r445.__file__).read_text()
        assert "pv._cio_summary" in src
        assert '.get("summary")' not in src


# ---------------------------------------------------------------------------
# 5. The recorded historical defect is explained, not hidden
# ---------------------------------------------------------------------------
class TestHistoricalDefectExplained:
    def test_r445_recorded_nulls_were_extraction_gaps(self):
        # R445/PRODUCTION_RUNS.json recorded cio_http 200 with
        # mechanism/technology_class/n_components null — the round
        # record's known_gaps entry called it an extraction gap; this
        # test pins that the OLD shape (top-level keys) is exactly the
        # phantom the extractor now types as MISSING
        old_style_body = {
            "kind": CIO_KIND, "present": True,
            "mechanism": None, "technology_class": None,
            "n_components": None}
        out = extract_cio_fields(200, old_style_body)
        assert out["extraction_state"] == MISSING
        assert "identity.mechanism" in out["missing_canonical_fields"]

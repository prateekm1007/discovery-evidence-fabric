"""R412 gradient v2 — the hermetic adversarial battery.

The v2 instrument is a control that unblocks a sealed run, so per
Articles VIII/XVI/XVII it must be attacked, not merely exercised:
positive cases that must pass, negative cases that must fail,
metamorphic mutations that must fail, and provenance/consistency
attacks. No LLM, no network — every test is deterministic.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "R412" / "GRADIENT_V2"))

from discovery_fabric.r412.gradient_v2 import (  # noqa: E402
    build_v2_query, family_for_rung, parse_v2_proposals,
    verify_v2_proposals, v2_tvm_slopes, query_v2_tvm,
    build_v2_snapshot, construction_log_entry,
)

V2 = REPO / "R412" / "GRADIENT_V2"
FAM = V2 / "CAPABILITY_FAMILY_MAP_V2.json"

REC_TEXT = ("Wafer-scale power converters demonstrated a switching "
            "energy of 0.42 \u00b1 0.03 microjoules in 2023, "
            "improving on the 1.1 microjoules reported in 2019.")
RECORDS = [{"record_id": "R1", "title": "Wafer-scale converters",
            "abstract": REC_TEXT}]


def _proposal(**over):
    p = {
        "slot": 0, "parse_status": "OK",
        "domain": "semiconductor power",
        "capability_rung": "device switching energy",
        "indicator": "switching energy", "metric": "Esw",
        "quoted_span": "0.42 \u00b1 0.03",
        "value": "0.42 \u00b1 0.03", "unit": "microjoules",
        "year": "2023", "trajectory_dimension": "performance",
        "record_id": "R1", "citation": "Wafer-scale converters",
        "occurrence_index": 0,
    }
    p.update(over)
    return p


# ------------------------------------------------------------------
# Phase D/E: the family map + query expansion
# ------------------------------------------------------------------

def test_family_map_v2_derived_from_13_deaths():
    d = json.loads(FAM.read_text())
    assert d["version"] == "2.0.0"
    fams = [f for f in d["families"]
            if f.get("entry_source") == "DERIVED_FROM_TECHNICAL_"
                                          "DEATH"]
    assert len(fams) == 13
    # every entry grounded in a verbatim-verified span
    assert all(f["grounding"]["basis_span_verified_verbatim"]
               for f in fams)
    # the LLM abstraction provenance is preserved, never promoted
    for f in fams:
        assert f["provenance"]["llm_abstraction_preserved"][
            "abstraction_provenance"].startswith("GA1B_COMMITTED")
        assert f["provenance"]["llm_abstraction_preserved"][
            "verification_state"] == "SPAN_VERIFIED_UPSTREAM"
    # exactly 4 allocation targets (the sealed eligible seeds)
    assert sum(1 for f in fams if f["allocation_target"]) == 4
    # the operator example is carried verbatim
    assert d["carried_operator_example_count"] == 1
    assert sum(1 for f in d["families"]
               if f.get("entry_source") ==
               "OPERATOR_DIRECTIVE_EXAMPLE") == 1


def test_family_lookup_exact_key_only():
    fam = family_for_rung("device switching energy")
    assert fam is not None and fam["family_id"]
    # a NEAR MISS returns None — never a fuzzy guess (Art. XLIII)
    assert family_for_rung("device switching energies") is None
    assert family_for_rung("switching energy device") is None


def test_build_v2_query_separates_evidence_and_exploratory():
    q = build_v2_query("device switching energy")
    assert q["family"] is not None
    assert q["query"].startswith("device switching energy")
    # Phase F: exploratory vocabulary is labeled, never capability
    assert "EXPLORATORY" in q["exploratory_note"]
    # a rung with no family: recorded miss, rung-text fallback
    q2 = build_v2_query("unknown rung xyz")
    assert q2["family"] is None
    assert "FAMILY_MISS_RECORDED" in q2["lookup"]
    assert q2["query"].startswith("unknown rung xyz")


# ------------------------------------------------------------------
# the proposal parser
# ------------------------------------------------------------------

def test_parse_v2_proposals_json_array():
    r = parse_v2_proposals(json.dumps([_proposal()]))
    assert r["parse_status"] == "OK"
    assert len(r["proposals"]) == 1


def test_parse_v2_proposals_fenced_json_tolerated():
    txt = "```json\n" + json.dumps([_proposal()]) + "\n```"
    r = parse_v2_proposals(txt)
    assert r["parse_status"] == "OK"
    assert len(r["proposals"]) == 1


def test_parse_v2_proposals_malformed_recorded():
    r = parse_v2_proposals("no array here at all")
    assert r["parse_status"].startswith("MALFORMED")
    assert r["proposals"] == []
    r2 = parse_v2_proposals("[{broken json")
    assert r2["parse_status"].startswith("MALFORMED")


# ------------------------------------------------------------------
# the deterministic admission gate
# ------------------------------------------------------------------

def _verify(props, records=RECORDS, rung="device switching energy"):
    return verify_v2_proposals(props, records, rung)


def test_positive_admission_with_canonical_rederivation():
    gate = _verify([_proposal()])
    assert len(gate["admitted"]) == 1, gate["rejected"]
    e = gate["admitted"][0]
    cv = e["canonical_value"]
    # 0.42 ± 0.03 losslessly becomes the derived range [0.39, 0.45]
    assert cv["representation"] == "RANGE"
    assert cv["normalized_min"] == pytest.approx(0.39)
    assert cv["normalized_max"] == pytest.approx(0.45)
    # the flat value is null for a range (no manufactured center)
    assert e["value"] is None
    # year canonical + slope value with basis label
    assert e["canonical_year"] == 2023
    assert e["slope_value_basis"] == "RANGE_MIDPOINT"
    assert e["slope_value"] == pytest.approx(0.42)
    # signal policy + family ref resolved
    assert e["signal_class"] == "PRIMARY_TECHNICAL"
    assert e["capability_family_ref"]


def test_negative_record_not_in_pool():
    gate = _verify([_proposal(record_id="R999")])
    assert gate["admitted"] == []
    assert gate["rejected"][0]["reason"] == \
        "RECORD_ID_NOT_IN_RETRIEVED_POOL"
    # the raw proposal is preserved with the rejection
    assert gate["rejected"][0]["raw_proposal"]["record_id"] == "R999"


def test_negative_investment_signal_never_capability():
    gate = _verify([_proposal(
        trajectory_dimension="investment")])
    assert gate["rejected"][0]["reason"] == \
        "NON_PRIMARY_SIGNAL_AS_CAPABILITY"
    assert gate["rejected"][0]["signal_class"] == \
        "EXPLANATORY_ONLY"


def test_negative_span_not_found_never_fuzzy():
    gate = _verify([_proposal(quoted_span="0.55 \u00b1 0.02")])
    assert gate["rejected"][0]["reason"].startswith("SPAN_")


def test_metamorphic_single_character_flip_rejected():
    good = "0.42 \u00b1 0.03"
    assert good in REC_TEXT
    gate = _verify([_proposal(quoted_span=good.replace("0.42",
                                                       "0.43"))])
    assert gate["admitted"] == []
    assert gate["rejected"][0]["reason"] == "SPAN_NOT_FOUND"


def test_negative_value_text_not_in_span():
    gate = _verify([_proposal(value="3.3 \u00b1 0.1")])
    assert gate["rejected"][0]["reason"] == \
        "VALUE_TEXT_NOT_IN_QUOTED_SPAN"


def test_negative_year_not_in_record():
    gate = _verify([_proposal(year="2035")])
    assert gate["rejected"][0]["reason"] == "YEAR_NOT_IN_RECORD_TEXT"


def test_negative_flat_value_disagrees_with_span():
    # the flat value text is IN the span but re-parses to a
    # DIFFERENT representation (a bare point inside an uncertainty
    # span) — two truths, rejected
    gate = _verify([_proposal(value="0.42")])
    assert gate["rejected"][0]["reason"] == \
        "FLAT_VALUE_DISAGREES_WITH_SPAN"
    # a value text outside the span is caught one step earlier
    gate2 = _verify([_proposal(value="3.3 \u00b1 0.1")])
    assert gate2["rejected"][0]["reason"] == \
        "VALUE_TEXT_NOT_IN_QUOTED_SPAN"


def test_negative_qualitative_value_not_measured():
    recs = [{"record_id": "RQ", "title": "qualitative",
             "abstract": "described as state-of-the-art in 2021"}]
    gate = verify_v2_proposals(
        [_proposal(record_id="RQ", quoted_span="state-of-the-art",
                   value="state-of-the-art", year="2021",
                   citation="qualitative")], recs,
        "device switching energy")
    assert gate["rejected"][0]["reason"].startswith(
        "VALUE_NOT_MEASURED_NUMERIC")


def test_raw_persistence_in_construction_log():
    parsed = {"parse_status": "OK",
              "proposals": [_proposal()]}
    gate = _verify(parsed["proposals"])
    e = construction_log_entry(
        "device switching energy", RECORDS, parsed, gate,
        model="glm-4-plus", retrieved_at="2026-09-06T00:00:00Z",
        prompt_hash="ph", output_hash="oh",
        raw_llm_output='[{"domain": "x"}]', query={"query": "q"})
    # THE v1 DEFECT FIXED FORWARD: raw proposals AND raw output
    assert e["raw_proposals"] == parsed["proposals"]
    assert e["raw_llm_output"] == '[{"domain": "x"}]'
    assert e["raw_llm_output_sha256"]
    assert e["rejected_reasons"] == []
    assert e["n_proposed"] == 1


# ------------------------------------------------------------------
# slopes + query
# ------------------------------------------------------------------

def _entry(domain, metric, rung, span_val, year, basis="POINT_VALUE",
           unit="u"):
    return {"domain": domain, "metric": metric, "unit": unit,
            "capability_rung": rung, "quoted_span": "s",
            "slope_value": span_val, "canonical_year": year,
            "slope_value_basis": basis}


def test_slopes_require_two_years_same_domain_metric():
    tvm = {"entries": [
        _entry("d1", "m", "r", 1.0, 2019),
        _entry("d1", "m", "r", 3.0, 2023),
        _entry("d2", "m", "r", 5.0, 2020),
    ]}
    slopes = v2_tvm_slopes(tvm, "r")
    assert len(slopes) == 1
    assert slopes[0]["domain"] == "d1"
    assert slopes[0]["slope"] == pytest.approx(0.5)
    # mixed basis disclosed on the points
    tvm2 = {"entries": [
        _entry("d1", "m", "r", 1.0, 2019, basis="POINT_VALUE"),
        _entry("d1", "m", "r", 3.0, 2023,
               basis="RANGE_MIDPOINT"),
    ]}
    s2 = v2_tvm_slopes(tvm2, "r")
    assert {p["basis"] for p in s2[0]["points"]} == {
        "POINT_VALUE", "RANGE_MIDPOINT"}
    # a single point yields no slope
    tvm3 = {"entries": [_entry("d1", "m", "r", 1.0, 2019)]}
    assert v2_tvm_slopes(tvm3, "r") == []


def test_query_v2_tvm_verdicts():
    tvm = {"entries": [
        _entry("d1", "m", "r", 1.0, 2019),
        _entry("d1", "m", "r", 3.0, 2023)]}
    q = query_v2_tvm(tvm, "r")
    assert q["verdict"] == "FAST_MOVERS_RANKED"
    assert q["slopes"][0]["domain"] == "d1"
    q2 = query_v2_tvm(tvm, "other rung")
    assert q2["verdict"] == "DEAD_AT_TVM_QUERY"


def test_snapshot_deterministic():
    tvm = {"tvm_version": "R412-TVM-V2", "entries": [
        _entry("d1", "m", "r", 1.0, 2019)],
        "construction_log": []}
    s1 = build_v2_snapshot(tvm)
    s2 = build_v2_snapshot(json.loads(json.dumps(tvm)))
    assert s1["sha256"] == s2["sha256"]
    assert s1["frozen_before_ga4"] is True
    # a byte change flips the hash
    tvm["entries"][0]["slope_value"] = 2.0
    assert build_v2_snapshot(tvm)["sha256"] != s1["sha256"]


# ------------------------------------------------------------------
# the v2.1 seal pins vs live bytes
# ------------------------------------------------------------------

def test_v2_1_preregistration_pins_match_live_bytes():
    import hashlib
    pr = json.loads(
        (V2 / "R412_GRADIENT_V2_1_PREREGISTRATION.json").read_text())
    assert pr["run_gate"]["state"] == "RUN_ALLOWED"
    for name, pin in pr["prompt_pins"].items():
        p = V2 / "PROMPTS" / f"{name}.json"
        assert hashlib.sha256(p.read_bytes()).hexdigest() == \
            pin["sha256"], name
    fam = FAM.read_bytes()
    assert hashlib.sha256(fam).hexdigest() == \
        pr["capability_family_map"]["sha256"]
    # the seed allocation is byte-identical to the sealed v1
    v1 = json.loads(
        (REPO / "R412" /
         "R412_GRADIENT_RECOVERY_PREREGISTRATION.json").read_text())
    assert pr["seed_allocation"]["priority_order"] == \
        v1["resource_allocation"]["priority_order"]
    assert len(pr["seed_allocation"]["priority_order"]) == 10
    # budgets byte-copied (no expansion)
    assert pr["token_and_cost_budgets"] == \
        v1["token_and_cost_budgets"]
    # the confound is disclosed, not hidden
    assert "minimax" in pr["model_pin"]["confound_disclosure"]


def test_v2_1_pin_drift_detected():
    import hashlib
    pr = json.loads(
        (V2 / "R412_GRADIENT_V2_1_PREREGISTRATION.json").read_text())
    pin = pr["prompt_pins"]["TVM_V2_FRONTIER_ENTRY_PROPOSAL"]
    live = hashlib.sha256(
        (V2 / "PROMPTS" /
         "TVM_V2_FRONTIER_ENTRY_PROPOSAL.json").read_bytes()
    ).hexdigest()
    # the recorded pin is a REAL hash of the live bytes (not a
    # placeholder), so this holds now and any future drift breaks it
    assert pin["sha256"] == live
    forged = dict(pin, sha256="0" * 64)
    assert forged["sha256"] != live

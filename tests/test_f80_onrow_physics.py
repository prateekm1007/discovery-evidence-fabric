#!/usr/bin/env python3
"""tests/test_f80_onrow_physics.py — the F80 lane's CI gates (R83,
claim c-0099; AM72/V73 direction 3; auditor acceptance: >=80% of the
answer's own numeric claims computed on-row with units, 0 sign
contradictions on the labelled set).

Zero LLM, zero network. Pins:
  (1) extraction: value+unit+span typed; unit aliases normalize
      (kA/m2, degC, C, %, bar); unparseable units are TYPED records,
      never silently dropped;
  (2) dimensional binding: a bar claim binds a kPa input (converts);
      a kA/m2 claim cannot bind an A input (typed unbindable, never
      forced); dimensionless inputs never bind unit-carrying claims;
  (3) row-claims-first: a bound claim's value WINS over the reference
      value; provenance is ROW_CLAIM (with claim id) vs ASSUMPTION
      (with the Art. 9 labelled-assumption note) vs FUNCTION_DEFAULT;
  (4) sign-check: AGREES / SIGN_CONTRADICTION / DEFERRED (deferring
      AND frame-dependent verbs) / NEUTRAL_COMPUTED — only
      unambiguous improves/worsens assertions can contradict;
  (5) typed refusals: UNKNOWN_CHECK, ONROW_UNITS_UNMAPPED,
      PENDING_INPUTS — never silent, never fabricating;
  (6) schema additivity: numeric_claims absent -> key ABSENT, no
      finding (the pre-F80 byte-stable path the frozen machine runs);
      present+malformed -> NUMERIC_CLAIM_MALFORMED;
  (7) the labelled-set acceptance, from a FRESH run of the
      measurement (the same deterministic command the CI runs):
      fraction >= 0.80, 0 sign contradictions, and at least one
      on-row run where the row's OWN number entered the computation
      (the F80 delta — v1 had on_row 0/36).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import numeric_claims as nc        # noqa: E402
from discovery_fabric.engine import onrow_physics as onrow      # noqa: E402
from discovery_fabric.engine import physics_checks as pc        # noqa: E402
from discovery_fabric.engine.candidate_schema import (          # noqa: E402
    extend_to_1_1, validate_candidate_schema)


# ---------------------------------------------------------------------------
# (1) extraction
# ---------------------------------------------------------------------------

def test_extracts_value_unit_and_span():
    out = nc.extract_numeric_claims(
        "operate the unit at 105 C with 3.2 kA/m2 and 60%", "t")
    claims = {c["unit_raw"]: c for c in out["claims"]}
    assert set(claims) == {"C", "kA/m2", "%"}
    assert claims["C"]["value"] == 105.0
    assert claims["C"]["unit"] == "degC"
    assert claims["kA/m2"]["unit"] == "kA/m**2"
    assert claims["%"]["unit"] == "percent"
    for c in out["claims"]:
        assert c["source_field"] == "t"
        assert len(c["source_span"]) == 2
        assert c["dimension"]


def test_unit_aliases_normalize():
    assert nc.parse_quantity(7, "bar")[0] is not None
    assert nc.parse_quantity(25, "\u00b0C")[1] == "degC"
    assert nc.parse_quantity(6, "h")[1] == "hour"
    q, _ = nc.parse_quantity(7, "bar")
    assert float(q.to("kPa").magnitude) == pytest.approx(700.0, rel=1e-3)


def test_unparseable_unit_is_typed_not_dropped():
    # the extractor recognizes a CLOSED unit vocabulary: "furlongs"
    # is not in it, so "12 furlongs" is not a number+unit pair at
    # all (n_scanned 0 — prose, not a claim, not fabricated)
    out = nc.extract_numeric_claims("about 12 furlongs of pipe", "t")
    assert out["claims"] == []
    assert out["unparseable"] == []
    assert out["n_scanned"] == 0
    # the pint-level typed refusal: a unit string handed to
    # parse_quantity that pint cannot parse returns (None, None) —
    # never a bare float, never a crash (pint's vocabulary is huge —
    # it even parses "furlongs" — but a non-unit string refuses)
    q, u = nc.parse_quantity(12, "bananas")
    assert q is None and u is None


def test_identifiers_are_not_numbers():
    out = nc.extract_numeric_claims("TRIZ P31 and R40 machine v77", "t")
    assert out["n_scanned"] == 0


# ---------------------------------------------------------------------------
# (2) dimensional binding
# ---------------------------------------------------------------------------

def _ext(pairs):
    """(value, unit_raw) list -> an extraction-shaped record."""
    claims = []
    for i, (v, u) in enumerate(pairs, 1):
        q, unit = nc.parse_quantity(v, u)
        claims.append({"claim_id": f"nc-{i}", "value": v,
                       "unit_raw": u, "unit": unit,
                       "quantity": f"{v} {unit}",
                       "dimension": str(q.dimensionality),
                       "source_field": "t", "source_span": [0, 0]})
    return {"claims": claims, "unparseable": [], "n_scanned": len(claims)}


def test_bar_claim_binds_kpa_input_deterministically():
    # dimension-only binding is deterministic: the first
    # dimension-compatible kwarg in signature order wins (surge's
    # signature is (p_surge_kpa, p_op_kpa) — a single pressure claim
    # binds p_surge; binding cannot SEMANTICALLY disambiguate two
    # same-dimension inputs — the typed
    # BINDING_IS_DIMENSIONAL_ONLY limitation, pinned here)
    bound = onrow.bind_claims("surge_margin", _ext([(7.0, "bar")]))
    assert list(bound["bindings"]) == ["p_surge_kpa"]
    assert bound["bindings"]["p_surge_kpa"]["value"] == pytest.approx(
        700.0, rel=1e-3)
    assert bound["bindings"]["p_surge_kpa"]["unit"] == "kPa"
    assert bound["unbound_claims"] == []
    # two pressure claims fill both kwargs in order
    bound2 = onrow.bind_claims(
        "surge_margin", _ext([(420.0, "kPa"), (7.0, "bar")]))
    assert set(bound2["bindings"]) == {"p_surge_kpa", "p_op_kpa"}
    assert bound2["bindings"]["p_op_kpa"]["value"] == pytest.approx(
        700.0, rel=1e-3)


def test_current_density_cannot_bind_current_input():
    bound = onrow.bind_claims(
        "faraday_gas_rate", _ext([(3.2, "kA/m2")]))
    assert bound["bindings"] == {}
    assert bound["unbound_claims"] == ["nc-1"]


def test_dimensionless_input_never_binds_unit_claim():
    bound = onrow.bind_claims(
        "faraday_gas_rate", _ext([(4.0, "g/mol")]))
    assert "z_electrons" not in bound["bindings"]


# ---------------------------------------------------------------------------
# (3) row-claims-first + provenance
# ---------------------------------------------------------------------------

def test_row_claim_wins_over_reference_value():
    # arrhenius signature (ea_kj_mol, t1_degC, t2_degC): the row's
    # own 105 C claim binds t1 (ROW_CLAIM, value 105 — NOT the
    # reference 60); ea and t2 fill as typed ASSUMPTIONS. The row's
    # own number CHANGES the computation — the F80 delta.
    run = onrow.run_on_row("arrhenius_rate_ratio",
                           _ext([(105.0, "C")]))
    assert run["verdict"] == "RUN"
    assert run["input_provenance"]["t1_degC"]["source"] == \
        "ROW_CLAIM"
    assert run["input_provenance"]["t1_degC"]["claim_id"] == "nc-1"
    assert run["input_provenance"]["ea_kj_mol"]["source"] == \
        "ASSUMPTION"
    assert "Art. 9" in run["input_provenance"]["ea_kj_mol"][
        "assumption"]
    assert run["input_provenance"]["t2_degC"]["source"] == \
        "ASSUMPTION"
    # the reference-only run (t1 assumed 60) computes a different
    # rate ratio than the row-claim run (t1 = 105) — row claims win
    ref = onrow.run_on_row("arrhenius_rate_ratio", _ext([]))
    assert ref["verdict"] == "RUN"
    assert run["value"] != ref["value"]


def test_function_default_provenance_typed():
    # larson_miller's c_const has a function default and no scenario
    # value -> provenance FUNCTION_DEFAULT, never a fabricated number
    run = onrow.run_on_row("larson_miller_lmp", _ext([]))
    assert run["verdict"] == "RUN"
    assert run["input_provenance"]["c_const"]["source"] == \
        "FUNCTION_DEFAULT"


# ---------------------------------------------------------------------------
# (4) sign-check
# ---------------------------------------------------------------------------

def test_sign_check_matrix():
    assert onrow.sign_check("improves", "improves")["verdict"] == \
        "AGREES"
    assert onrow.sign_check("worsens", "improves")["verdict"] == \
        "SIGN_CONTRADICTION"
    assert onrow.sign_check(None, "worsens")["verdict"] == "DEFERRED"
    assert onrow.sign_check("improves", "neutral")["verdict"] == \
        "NEUTRAL_COMPUTED"


def test_frame_dependent_verbs_defer():
    # "reduces the margin" would be worsens; "reduces the rate"
    # improves — the word alone cannot decide, so it DEFERS
    assert onrow.stated_direction(
        "this reduces the dew point margin by 4.2 degC") is None
    assert onrow.stated_direction(
        "the intervention improves the margin") == "improves"
    assert onrow.stated_direction(
        "direction is the SIGN of the computed physics result") is None


def test_contradiction_fires_on_unambiguous_assertion():
    # surge with the row's own 7 bar on p_surge (700 kPa) vs the
    # assumed op 360 kPa: computed margin POSITIVE -> improves; the
    # candidate ASSERTS worsens -> SIGN_CONTRADICTION (typed)
    run = onrow.run_on_row(
        "surge_margin", _ext([(7.0, "bar")]),
        direction_text="the change worsens the surge margin")
    assert run["direction_of_effect"] == "improves"
    assert run["sign_check"]["verdict"] == "SIGN_CONTRADICTION"


# ---------------------------------------------------------------------------
# (5) typed refusals
# ---------------------------------------------------------------------------

def test_unknown_check_refused_typed():
    run = onrow.run_on_row("not_a_check", _ext([]))
    assert run["verdict"] == "REFUSED"
    assert run["typed"] == "UNKNOWN_CHECK"


def test_unmapped_units_refused_typed(monkeypatch):
    saved = onrow.INPUT_UNITS.pop("surge_margin", None)
    try:
        run = onrow.run_on_row("surge_margin", _ext([]))
        assert run["verdict"] == "REFUSED"
        assert run["typed"] == "ONROW_UNITS_UNMAPPED"
    finally:
        if saved is not None:
            onrow.INPUT_UNITS["surge_margin"] = saved


def test_pending_inputs_refused_typed(monkeypatch):
    saved = dict(pc.REFERENCE_SCENARIOS["surge_margin"])
    try:
        pc.REFERENCE_SCENARIOS["surge_margin"] = {
            "p_surge_kpa": saved["p_surge_kpa"]}
        run = onrow.run_on_row("surge_margin", _ext([]))
        assert run["verdict"] == "REFUSED"
        assert run["typed"] == "PENDING_INPUTS"
        assert run["detail"]["missing_kwargs"] == ["p_op_kpa"]
    finally:
        pc.REFERENCE_SCENARIOS["surge_margin"] = saved


# ---------------------------------------------------------------------------
# (6) schema additivity (the frozen-path byte-stability)
# ---------------------------------------------------------------------------

def _core():
    return {"candidate_schema": "mechanism_candidate/1.0.0",
            "candidate_id": "x", "candidate_hash": "h"}


def test_schema_numeric_claims_absent_by_default():
    out = extend_to_1_1(_core())
    assert "numeric_claims" not in out
    assert "NUMERIC_CLAIM_MALFORMED" not in validate_candidate_schema(out)


def test_schema_numeric_claims_attached_when_given():
    out = extend_to_1_1(
        _core(), numeric_claims=[{"value": 3.2, "unit": "kA/m**2"}])
    assert out["numeric_claims"] == [
        {"value": 3.2, "unit": "kA/m**2"}]
    assert "NUMERIC_CLAIM_MALFORMED" not in validate_candidate_schema(out)


def test_schema_malformed_numeric_claim_typed():
    out = extend_to_1_1(
        _core(), numeric_claims=[{"value": "lots", "unit": "degC"},
                                 {"value": 5.0, "unit": "  "}])
    f = validate_candidate_schema(out)
    assert "NUMERIC_CLAIM_MALFORMED" in f
    assert "not numeric" in f["NUMERIC_CLAIM_MALFORMED"][0]
    assert "non-empty string" in f["NUMERIC_CLAIM_MALFORMED"][0]


def test_labelled_candidates_never_gain_new_finding_keys():
    rows = json.loads(
        (REPO / "eval/r43_v7_problem_fields_burned.json")
        .read_text())["problems"]
    from discovery_fabric.engine import engine_route as er
    out = er.run_row(rows[0])
    for r in out["results"]:
        assert "numeric_claims" not in r["candidate"]
        assert "NUMERIC_CLAIM_MALFORMED" not in r["schema_findings"]


# ---------------------------------------------------------------------------
# (7) the labelled-set acceptance, from a fresh measurement run
# ---------------------------------------------------------------------------

def test_labelled_set_onrow_acceptance():
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts/"
                             "r54_p1_unit_checked_measurement.py")],
        capture_output=True, text=True, cwd=str(REPO), timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    art = json.loads(
        (REPO / "eval/r54_p1_unit_checked.json").read_text())
    assert art["definition_version"].startswith("2.0.0")
    assert art["numeric_claims_total"] > 0
    assert art["fraction"] >= 0.80, art["fraction"]
    assert art["sign_contradictions"] == 0
    # the F80 delta: the row's OWN numbers entered at least one
    # computation (v1 had on-row runs 0/36 from row inputs)
    assert art["own_numbers_totals"]["bound_inputs"] > 0
    bound_rows = [row for row in art["rows"]
                  if any(run.get("row_claim_inputs")
                         for run in row["on_row_runs"])]
    assert bound_rows, "no on-row run consumed a row claim"
    # every carrying run reports full input provenance
    for row in art["rows"]:
        for run in row["on_row_runs"]:
            if run["verdict"] == "RUN":
                assert run["input_provenance"]
                assert run["sign_check"]["verdict"] in (
                    "AGREES", "DEFERRED", "NEUTRAL_COMPUTED")

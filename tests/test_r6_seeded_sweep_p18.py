"""R6 P1-8: per-instrument sweep denominators + intervention-gate
calibration emit (owner directive 2026-11-11, item 8).

Zero LLM (the gate checks are deterministic). Synthetic-fixture runs
only: the pins cover the DENOMINATOR discipline (each instrument's
false-kill and catch denominators are its own measured rows — never
the pooled set), the pinned-schema shape of the emitted CANDIDATE
measurement records (the two P0-3 pinned intervention-gate
instruments), and the verdict rule: DERIVED only from owner-supplied
seals, PENDING_OWNER_SEAL without them, NOT_MEASURED_DENOMINATOR on
an empty denominator — the coder never asserts a verdict and a
synthetic run never establishes calibration (the authority flip
stays owner-held, P0-3).
"""
import json

from scripts import r6_seeded_sweep as SW

# a real problem with domain/device/failure text: the anchor-domain
# check is measurable for specimens carrying its problem_id
P = "bench-p01-pemfc-dehydration"
CONSTRAINT = "membrane humidity must stay above 30 %"


def _specs(tmp_path):
    specs = [
        # Spec A: control, NO problem_id -> anchor_domain unmeasurable
        # -> a PARTIAL row (n_checks_unmeasured > 0). It is counted in
        # the POOLED control denominator but excluded from the
        # per-instrument denominator. fr/rc ARE measured (the specimen
        # supplies the constraint).
        {"defect_class": "control", "constraint": CONSTRAINT,
         "intervention": ("add a humidification blower upstream of the "
                           "anode manifold")},
        # Spec B: control, problem_id P (the problem supplies a
        # constraint) -> COMPLETE row, measured by all four
        # instruments.
        {"defect_class": "control", "problem_id": P,
         "intervention": ("install a differential-pressure shunt "
                           "across the stack")},
        # Spec C: complete seeded (problem_id P supplies the
        # constraint).
        {"defect_class": "sd_removes_mandated", "problem_id": P,
         "intervention": ("removes the humidifier and lowers membrane "
                           "humidity to 20 %")},
    ]
    p = tmp_path / "specimens.json"
    p.write_text(json.dumps(specs), encoding="utf-8")
    return p


def test_per_instrument_denominators_are_never_pooled(tmp_path):
    res = SW.run_sweep(_specs(tmp_path), None, False, True)
    assert res["outcome"] == "PARTIAL_WITH_INCOMPLETE_ROWS"
    pi = res["per_instrument"]
    # the POOLED control denominator includes the unmeasured row:
    assert res["false_kill"]["n_controls"] == 2
    # the PER-INSTRUMENT denominators exclude it (a row the instrument
    # could not measure is out — never counted as a non-kill):
    assert pi["function_removal"]["control"]["n_complete"] == 1
    assert pi["restates_constraint"]["control"]["n_complete"] == 1
    assert pi["function_removal"]["seeded"]["n_complete"] == 1


def test_calibration_emit_shape_and_pending_seal(tmp_path):
    res = SW.run_sweep(_specs(tmp_path), None, False, True)
    emit = res["calibration_emit"]
    assert set(emit) == {
        "intervention_gate_function_removal/1.0.0",
        "intervention_gate_restates_constraint/1.0.0"}
    for rec in emit.values():
        assert rec["SYNTHETIC_FIXTURE"] is True
        m = rec["metrics"]
        # the emit's FKR denominator is the per-instrument one,
        # not the pooled 2:
        assert m["fpr_denominator"] == 1
        assert "per-instrument" in m["denominator_note"]
        # the pinned measurement-schema keys the gate's resolve_state
        # reads:
        assert isinstance(m["false_kill_rate_on_known_good"],
                          (int, float, type(None)))
        assert isinstance(rec["scoped_tpr_diagnostic"]["tpr"],
                          (int, float, type(None)))
        assert "n_cases_attacked" in rec
        # no owner seal shipped -> verdict NOT derived (never
        # asserted by the coder):
        assert rec["threshold_verdict"]["state"] == "PENDING_OWNER_SEAL"
        assert rec["threshold_verdict"]["calibrated"] is None
        assert "no terminal authority" in rec["authority_note"]


def test_verdict_derived_only_from_owner_seals(tmp_path):
    seals = {"intervention_gate_function_removal/1.0.0": {
        "fpr_max": 1.0, "tpr_min": 0.0, "coverage_min": 0.0,
        "parse_completeness_min": 0.0}}
    res = SW.run_sweep(_specs(tmp_path), None, False, True,
                       owner_seals=seals)
    rec = res["calibration_emit"]["intervention_gate_function_removal/1.0.0"]
    v = rec["threshold_verdict"]
    # all four numbers present here (1 measured control row, 1
    # measured seeded row) -> the verdict is DERIVED against the
    # sealed bars (open-wide fixture bars -> calibrated True):
    assert v["state"] == "DERIVED_FROM_OWNER_SEAL"
    assert v["calibrated"] is True
    # the un-sealed instrument stays PENDING:
    rec2 = res["calibration_emit"][
        "intervention_gate_restates_constraint/1.0.0"]
    assert rec2["threshold_verdict"]["state"] == "PENDING_OWNER_SEAL"
    assert rec2["threshold_verdict"]["calibrated"] is None


def test_empty_denominator_is_not_measured_never_zero(tmp_path):
    # no clean controls at all: the FKR denominator is empty ->
    # NOT_MEASURED (never a fabricated zero) and the verdict is
    # undervidable.
    p = tmp_path / "specimens.json"
    p.write_text(json.dumps([
        {"defect_class": "sd_removal", "problem_id": P,
         "constraint": CONSTRAINT,
         "intervention": ("removes the humidifier and lowers membrane "
                           "humidity to 20 %")},
    ]), encoding="utf-8")
    res = SW.run_sweep(p, None, False, True)
    assert res["false_kill"] == "NOT_MEASURED"  # pooled: no controls
    pi = res["per_instrument"]
    assert pi["function_removal"]["control"]["n_complete"] == 0
    assert pi["function_removal"]["control"]["rate"] is None
    emit = res["calibration_emit"][
        "intervention_gate_function_removal/1.0.0"]
    assert emit["metrics"]["false_kill_rate_on_known_good"] is None
    seals = {"intervention_gate_function_removal/1.0.0": {
        "fpr_max": 1.0, "tpr_min": 0.0, "coverage_min": 0.0,
        "parse_completeness_min": 0.0}}
    res2 = SW.run_sweep(p, None, False, True, owner_seals=seals)
    v = res2["calibration_emit"][
        "intervention_gate_function_removal/1.0.0"]["threshold_verdict"]
    assert v["state"] == "NOT_MEASURED_DENOMINATOR"
    assert "fpr" in v["missing_metrics"]

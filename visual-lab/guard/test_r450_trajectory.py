"""R450-C2 battery: the trajectory layer's visual regression + guard attacks.

Operator directive R450-C2 section 10 — visual regression extended to
trajectory state. Every regression item is attacked mechanically:

  1. same engineering state   -> same visual identity
     (byte-identical projection from identical lineage bytes)
  2. same trajectory          -> same state ordering
     (generation order preserved; exactly one CURRENT)
  3. same mutation            -> expected geometric delta visible
     (identity reads unchanged; a recorded mutation reads as a delta)
  4. different mutation       -> different delta visible
     (two distinct mutations yield distinct measured signatures)
  5. uncertain state          -> uncertainty label visible
     (SURVIVED_WITH_UNCERTAINTIES carries its uncertainties verbatim;
      unproven provenance degrades to UNVERIFIED, never upgrades)
  6. unvalidated AI geometry  -> cannot appear as engineering-certified
     (guard rejects AI/hf geometry labeled ENGINEERING_GEOMETRY; rejects
      MEASURED badges without an R370G event)

Also attacked (Art. XVII): badge-spoofing battery, sensitivity-refusal
battery, projection tamper battery, production-claim vocabulary ban.

Direct-run exit-code contract (house style):
    python3 visual-lab/guard/test_r450_trajectory.py   (exit 0 = all green)
"""
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.resolve().parents[0]  # visual-lab/ -> the engine repo root
for p in (str(LAB / "trajectory"), str(LAB / "guard"),
          str(LAB / "benchmark")):
    if p not in sys.path:
        sys.path.insert(0, p)

import schema as T  # type: ignore  # noqa: E402
import trajectory_guard as TG  # type: ignore  # noqa: E402
import canonical_inputs as ci  # type: ignore  # noqa: E402
import negative_controls as NC  # type: ignore  # noqa: E402
from trajectory_dimensions import (  # type: ignore  # noqa: E402
    before_after_correspondence)

LINEAGE_PATH = REPO / "R445" / "EVOLUTION_RUNS" / \
    "evol-x02-bus-fastcharge-lithium-plating" / "INVENTION_LINEAGE.json"

passed, failed = [], []


def check(name: str, fn, expect_error: type | None = None):
    try:
        fn()
        ok, detail = expect_error is None, "expected error, got silence"
    except Exception as e:  # noqa: BLE001
        ok = expect_error is not None and isinstance(e, expect_error)
        detail = f"{type(e).__name__}: {e}"
    (passed if ok else failed).append((name, detail))


# ---------------------------------------------------------------------------
# 1. same engineering state -> same visual identity
# ---------------------------------------------------------------------------

def t_projection_determinism():
    lineage = json.loads(LINEAGE_PATH.read_text())
    a = T.project_trajectory(lineage)
    b = T.project_trajectory(json.loads(T.canonical_json(lineage)))
    assert T.record_sha256(a) == T.record_sha256(b), \
        "identical lineage bytes projected differently"
    # and the projection is stable across a fresh interpreter state
    c = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    assert T.record_sha256(a) == T.record_sha256(c)


def t_projection_rejects_non_lineage():
    try:
        T.project_trajectory({"schema": "SOMETHING_ELSE"})
    except T.TrajectoryProjectionError:
        return
    raise AssertionError("non-lineage input projected")


# ---------------------------------------------------------------------------
# 2. same trajectory -> same state ordering
# ---------------------------------------------------------------------------

def t_state_ordering_and_single_current():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    gens = [s["gen"] for s in traj["states"]]
    assert gens == sorted(gens), "generation order not preserved"
    assert sum(1 for s in traj["states"] if s["current"]) == 1, \
        "not exactly one CURRENT state"
    assert traj["states"][-1]["current"], "the LAST state must be CURRENT"
    assert traj["states"][0]["status"] == "INVENTION_EVOLVED"
    assert traj["states"][1]["status"] == "INVENTION_REQUIRES_EXPERIMENT"


def t_transition_count_matches():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    assert len(traj["transitions"]) == len(traj["states"]) - 1


# ---------------------------------------------------------------------------
# 3. same mutation -> expected geometric delta visible
#    4. different mutation -> different delta visible
# ---------------------------------------------------------------------------

def _delta_signature(case: str, mutation: str):
    canon = ci.case_glb_path(case)
    NC.run_control(case, mutation, seed=7)
    dest = NC.OUT_DIR / f"{case}_{mutation}.glb"
    return before_after_correspondence(canon, dest)


def t_identity_reads_unchanged():
    canon = ci.case_glb_path("A")
    rec = before_after_correspondence(canon, canon)
    assert rec["node_jaccard"] == 1.0
    assert rec["normalized_chamfer_p95_over_diag"] == 0.0
    assert rec["max_abs_axis_deviation_pct"] == 0.0


def t_same_mutation_yields_visible_delta():
    # incorrect_scale mutates a dimension ~25%: the delta MUST be visible
    sig = _delta_signature("A", "incorrect_scale")
    assert sig["max_abs_axis_deviation_pct"] > 5.0, \
        "scale mutation not visible in the sorted-axis dimension delta"
    assert sig["normalized_chamfer_p95_over_diag"] > 0.01
    # and the instrument is stable: same bytes -> same delta
    sig2 = _delta_signature("A", "incorrect_scale")
    assert abs(sig2["max_abs_axis_deviation_pct"] -
               sig["max_abs_axis_deviation_pct"]) < 1e-9


def t_different_mutations_differ():
    a = _delta_signature("A", "incorrect_scale")
    b = _delta_signature("A", "rotated_component_toppling")
    # the two mutations produce DISTINCT measured signatures
    assert abs(a["normalized_chamfer_p95_over_diag"] -
               b["normalized_chamfer_p95_over_diag"]) > 1e-6, \
        "distinct mutations produced an identical chamfer signature"
    assert a["max_abs_axis_deviation_pct"] > b["max_abs_axis_deviation_pct"]


# ---------------------------------------------------------------------------
# 5. uncertain state -> uncertainty label visible
# ---------------------------------------------------------------------------

def _lineage_with_uncertainty():
    lineage = json.loads(LINEAGE_PATH.read_text())
    gen = lineage["generations"][-1]
    gen["challenge"]["attack_overall"] = "SURVIVED_WITH_UNCERTAINTIES"
    gen["challenge"]["uncertainties"] = "benchtop agreement unverified"
    return lineage


def t_uncertainty_carried_verbatim():
    traj = T.project_trajectory(_lineage_with_uncertainty())
    # the SURVIVING state is the LAST state: its uncertainty must be
    # visible on the STATE element (no following transition) ...
    last_state = traj["states"][-1]
    assert last_state["challenge"] and \
        last_state["challenge"].get("survived_with_uncertainties"), \
        "current state's SURVIVED_WITH_UNCERTAINTIES not surfaced"
    assert last_state["challenge"].get("uncertainties") == \
        "benchtop agreement unverified", \
        "uncertainty text not carried verbatim on the state"
    # ... and on any transition FAILURE element derived from it
    for tr in traj["transitions"]:
        f = tr.get("failure")
        if f and f.get("survived_with_uncertainties"):
            assert f.get("uncertainties") == "benchtop agreement unverified"
    # the REAL lineage (unmodified): the uncertainty-present-but-not-
    # itemized state still carries a visible label, never silence
    real = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    rl = real["states"][-1]
    if rl["challenge"] and rl["challenge"].get("survived_with_uncertainties"):
        assert rl["challenge"].get("uncertainties"), \
            "real lineage uncertainty state rendered without a label"


def t_uncertainty_without_text_rejected():
    traj = T.project_trajectory(_lineage_with_uncertainty())
    for tr in traj["transitions"]:
        f = tr.get("failure")
        if f and f.get("survived_with_uncertainties"):
            f["uncertainties"] = None
    for st in traj["states"]:
        c = st.get("challenge")
        if c and c.get("survived_with_uncertainties"):
            c["uncertainties"] = None
    try:
        TG.validate_trajectory_projection(traj)
    except TG.TrajectoryViolation:
        return
    raise AssertionError(
        "SURVIVED_WITH_UNCERTAINTIES without text passed the guard")


# ---------------------------------------------------------------------------
# 6. unvalidated AI geometry -> cannot appear as engineering-certified
# ---------------------------------------------------------------------------

def t_ai_mesh_cannot_be_engineering_geometry():
    artifacts = {
        "candidate_mesh": {
            "epistemic_class": "ENGINEERING_GEOMETRY",
            "generator": "hf:microsoft/TRELLIS.2-4B",
            "lineage_root_sha256": "3f2a" + "0" * 60,
        }
    }
    try:
        TG.check_generation_geometry_authority(artifacts, "3f2a" + "0" * 60)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("an hf-generated mesh passed as ENGINEERING_GEOMETRY")


def t_ai_mesh_without_lineage_root_rejected():
    artifacts = {
        "candidate_mesh": {
            "epistemic_class": "ENGINEERING_GEOMETRY",
            "generator": "coder1:cad",
            "lineage_root_sha256": None,
        }
    }
    try:
        TG.check_generation_geometry_authority(artifacts, "3f2a" + "0" * 60)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("engineering geometry without a verified lineage "
                         "root passed")


def t_coder1_geometry_with_correct_root_passes():
    root = "3f2a" + "0" * 60
    artifacts = {
        "canonical": {
            "epistemic_class": "ENGINEERING_GEOMETRY",
            "generator": "coder1:cad",
            "lineage_root_sha256": root,
        }
    }
    TG.check_generation_geometry_authority(artifacts, root)  # must not raise


def t_measured_badge_requires_event():
    # claimed-MEASURED without an R370G event: the trajectory guard must
    # refuse it at validation time
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    traj["states"][0]["epistemic_badge"] = "MEASURED"
    try:
        TG.validate_trajectory_projection(traj)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("MEASURED badge without an event passed the guard")


def t_measured_badge_with_full_event_passes():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    traj["states"][0]["epistemic_badge"] = "MEASURED"
    traj["states"][0]["provenance"] = {"event": {
        "event_id": "EVT-TEST-1",
        "raw_data_sha256": "ab" * 32,
        "attestation": {"attestation_text": "caliper measurement",
                        "attestation_hash": "cd" * 32},
        "custody_chain": [{"step": 1}],
    }}
    TG.validate_trajectory_projection(traj)  # must not raise


# ---------------------------------------------------------------------------
# badge-spoofing battery (Art. III — the verifier never trusts the claimant)
# ---------------------------------------------------------------------------

def t_badge_spoof_battery():
    cases = [
        # (provenance, expected badge)
        ({"event": {"event_id": "E1", "raw_data_sha256": "ab" * 32,
                    "attestation": "signed"}}, "MEASURED"),
        # missing attestation -> downgrade
        ({"event": {"event_id": "E1", "raw_data_sha256": "ab" * 32}},
         "UNVERIFIED"),
        ({"computation": {"instrument": "R383 evaluator",
                          "basis": "closed-form"}}, "SIMULATED"),
        # instrument without basis -> downgrade
        ({"computation": {"instrument": "R383 evaluator"}}, "UNVERIFIED"),
        ({"inference": {"basis": ["x"], "method": "diagnose/1.0.0"}},
         "INFERRED"),
        ({"proposal": {"provider": "zai", "model": "glm"}}, "PROPOSED"),
        ({}, "UNVERIFIED"),
        (None, "UNVERIFIED"),
        ("MEASURED", "UNVERIFIED"),  # a claimed label is not provenance
    ]
    for prov, expected in cases:
        got = T.derive_badge(prov)
        assert got == expected, f"derive_badge({prov!r}) = {got!r}, want {expected!r}"


def t_claimed_measured_never_spoofed_by_label():
    # a record carrying "this is measured" TEXT but no event fields is
    # UNVERIFIED, never MEASURED (Art. III/XXXVIII)
    got = T.derive_badge({"note": "this result is MEASURED and validated"})
    assert got == "UNVERIFIED"


# ---------------------------------------------------------------------------
# sensitivity refusal battery (no scientific interpretation in the viewer)
# ---------------------------------------------------------------------------

def t_sensitivity_refusal_battery():
    # missing basis -> refused
    for bad in (
        {"parameter": "fin_pitch_mm", "points": [{"value": 1, "objective": 2},
                                                  {"value": 1.2, "objective": 1.9}]},
        {"parameter": "fin_pitch_mm", "basis": "OBVIOUS",
         "points": [{"value": 1, "objective": 2}, {"value": 1.2, "objective": 1.9}]},
        {"parameter": "fin_pitch_mm", "basis": "SIMULATED", "points": []},
        {"basis": "MEASURED", "points": [{"value": 1, "objective": 2},
                                          {"value": 1.2, "objective": 1.9}]},
        "fin pitch 1.0 -> 0.71 (narrative)",
    ):
        try:
            T.project_sensitivity(bad)
        except T.TrajectoryProjectionError:
            continue
        raise AssertionError(f"sensitivity record accepted: {bad!r}")


def t_sensitivity_accepted_and_badged():
    rec = T.project_sensitivity({
        "parameter": "fin_pitch_mm", "basis": "SIMULATED",
        "objective": "objective",
        "provenance": {"computation": {"instrument": "R383 evaluator",
                                       "basis": "closed-form"}},
        "points": [{"value": 1.0, "objective": 0.71},
                   {"value": 1.2, "objective": 0.68}],
    })
    assert rec["epistemic_badge"] == "SIMULATED"
    assert rec["points"][0] == {"value": 1.0, "objective": 0.71}


def t_sensitivity_measured_requires_event():
    try:
        T.project_sensitivity({
            "parameter": "fin_pitch_mm", "basis": "MEASURED",
            "provenance": {"note": "measured in the lab"},
            "points": [{"value": 1.0, "objective": 0.71},
                       {"value": 1.2, "objective": 0.68}],
        })
    except T.TrajectoryProjectionError:
        raise AssertionError(
            "claimed-MEASURED basis without an event should degrade, not "
            "refuse; refusal here means the record was malformed")
    except AssertionError:
        raise
    # the correct behavior: accepted but degraded to UNVERIFIED
    rec = T.project_sensitivity({
        "parameter": "fin_pitch_mm", "basis": "MEASURED",
        "provenance": {"note": "measured in the lab"},
        "points": [{"value": 1.0, "objective": 0.71},
                   {"value": 1.2, "objective": 0.68}],
    })
    assert rec["epistemic_badge"] == "UNVERIFIED", \
        "claimed-MEASURED without an event must degrade to UNVERIFIED"


def t_sensitivity_values_verbatim():
    pts = [{"value": 1.0, "objective": 0.71},
           {"value": 1.2, "objective": 0.68},
           {"value": 1.4, "objective": 0.62}]
    rec = T.project_sensitivity({
        "parameter": "fin_pitch_mm", "basis": "SIMULATED",
        "provenance": {"computation": {"instrument": "E", "basis": "b"}},
        "points": pts,
    })
    assert rec["points"] == pts, "sensitivity values were not rendered verbatim"


# ---------------------------------------------------------------------------
# projection tamper + production-claim battery
# ---------------------------------------------------------------------------

def t_boundary_strip_attack():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    traj.pop("epistemic_boundary")
    try:
        TG.validate_trajectory_projection(traj)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("trajectory without the epistemic boundary passed")


def t_status_relabel_attack():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    traj["states"][0]["status"] = "ENGINEERING_VALIDATED"
    try:
        TG.validate_trajectory_projection(traj)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("re-labeled status vocabulary passed the guard")


def t_unknown_badge_rejected():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    traj["states"][0]["epistemic_badge"] = "VALIDATED"
    try:
        TG.validate_trajectory_projection(traj)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("badge outside the five-class vocabulary passed")


def t_prediction_outcome_closed_set():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    traj["transitions"][-1]["prediction"] = {
        "prediction_outcome": "HELD",  # claimed but never evaluated
        "epistemic_badge": "PROPOSED",
    }
    try:
        TG.validate_trajectory_projection(traj)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("HELD outcome on a PROPOSED badge passed — an "
                         "unevaluated prediction claimed its result")


def t_production_claim_vocabulary_banned():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    traj["presentation_note"] = "this trajectory is production-ready"
    try:
        TG.check_no_production_promotion(traj)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("production-claim vocabulary passed the ban")


def t_multi_current_rejected():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    traj["states"][0]["current"] = True
    try:
        TG.validate_trajectory_projection(traj)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("two CURRENT states passed the guard")


def t_source_provenance_required():
    traj = T.project_trajectory(json.loads(LINEAGE_PATH.read_text()))
    traj.pop("source")
    try:
        TG.validate_trajectory_projection(traj)
    except TG.TrajectoryViolation:
        return
    raise AssertionError("trajectory without its canonical source hash "
                         "passed (provenance custody, Art. XII)")


ALL = [
    # (name, fn, expected_error)
    ("projection_determinism_same_bytes", t_projection_determinism, None),
    ("projection_rejects_non_lineage", t_projection_rejects_non_lineage, None),
    ("state_ordering_single_current", t_state_ordering_and_single_current, None),
    ("transition_count_matches", t_transition_count_matches, None),
    ("identity_reads_unchanged", t_identity_reads_unchanged, None),
    ("same_mutation_visible_delta", t_same_mutation_yields_visible_delta, None),
    ("different_mutations_differ", t_different_mutations_differ, None),
    ("uncertainty_carried_verbatim", t_uncertainty_carried_verbatim, None),
    ("uncertainty_without_text_rejected", t_uncertainty_without_text_rejected, None),
    ("ai_mesh_not_engineering_geometry",
     t_ai_mesh_cannot_be_engineering_geometry, None),
    ("engineering_geometry_without_lineage_root_rejected",
     t_ai_mesh_without_lineage_root_rejected, None),
    ("coder1_geometry_correct_root_passes",
     t_coder1_geometry_with_correct_root_passes, None),
    ("measured_badge_requires_event", t_measured_badge_requires_event, None),
    ("measured_badge_with_full_event_passes",
     t_measured_badge_with_full_event_passes, None),
    ("badge_spoof_battery", t_badge_spoof_battery, None),
    ("claimed_measured_label_never_spoofs",
     t_claimed_measured_never_spoofed_by_label, None),
    ("sensitivity_refusal_battery", t_sensitivity_refusal_battery, None),
    ("sensitivity_accepted_and_badged", t_sensitivity_accepted_and_badged, None),
    ("sensitivity_measured_requires_event",
     t_sensitivity_measured_requires_event, None),
    ("sensitivity_values_verbatim", t_sensitivity_values_verbatim, None),
    ("boundary_strip_attack", t_boundary_strip_attack, None),
    ("status_relabel_attack", t_status_relabel_attack, None),
    ("unknown_badge_rejected", t_unknown_badge_rejected, None),
    ("prediction_outcome_closed_set", t_prediction_outcome_closed_set, None),
    ("production_claim_vocabulary_banned",
     t_production_claim_vocabulary_banned, None),
    ("multi_current_rejected", t_multi_current_rejected, None),
    ("source_provenance_required", t_source_provenance_required, None),
]


def main() -> int:
    for name, fn, expected in ALL:
        check(name, fn, expected)
    print(f"R450 trajectory battery: {len(passed)} passed, "
          f"{len(failed)} failed")
    for name, detail in failed:
        print(f"  FAIL {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

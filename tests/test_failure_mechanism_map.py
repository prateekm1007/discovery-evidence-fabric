"""tests/test_failure_mechanism_map.py — the R144 DIR-2/3 lever
tests (claim c-0243): the failure-mode -> mechanism-class map, its
plan-layer wiring, and the two typed scans. Every assertion is
against the MEASURED v16 off-target shapes (the 8 rows) and the
sound rows (no regression)."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine.failure_mechanism_map import (
    detect_failure_family, family_classes, mechanism_class_fit)


def _prob(problem_text):
    return {"failure": problem_text, "failure_mode": problem_text,
            "problem": problem_text, "question": ""}


# --- the failure-family detection: the 8 measured v16 shapes ---
def test_the_eight_off_target_families_detect():
    cases = {
        "Ship stern-tube bearing wears from seawater-lubricated "
        "abrasion.": "abrasion_erosion",
        "Overland conveyor belt rips at transfer points from "
        "trapped tramp metal.": "foreign_object",
        "Lyophilizer vial-to-vial ice nucleation variability "
        "causes cake collapse.": "nucleation_phase_change",
        "LPBF parts distort from residual stress after support "
        "removal.": "residual_stress_distortion",
        # "burn out" matches thermal_attack_surface first — the
        # lexicon's order IS the contract (failure-physics
        # specificity); both families admit boundary, so the map is
        # on-physics either way
        "Clinker cooler grate plates burn out from red-hot river "
        "channeling.": "thermal_attack_surface",
        "Liquid rocket injector face burns from recirculation "
        "hot-gas anchoring.": "thermal_attack_surface",
        "Wire-bond lift from intermetallic Kirkendall voiding at "
        "high temp.": "diffusion_intermetallic",
        "Flotation cell recovery drops from coarse-particle "
        "detachment.": "particle_attachment",
    }
    for txt, fam in cases.items():
        assert detect_failure_family(_prob(txt)) == fam, txt


def test_anti_classes_are_the_measured_off_targets():
    # chemistry for abrasion (the v16-02 shape)
    adm, anti = family_classes("abrasion_erosion")
    assert "chemistry" in anti and "material" in adm
    # control for nucleation (the v16-05/23 shape)
    adm, anti = family_classes("nucleation_phase_change")
    assert "control" in anti
    # chemistry for foreign objects (the v16-03 shape)
    adm, anti = family_classes("foreign_object")
    assert "chemistry" in anti


def test_no_detection_means_no_reorder():
    fit = mechanism_class_fit(
        {"failure": "unrelated text with no physics keyword",
         "failure_mode": "", "problem": "", "question": ""},
        "configuration")
    assert fit["rank"] == 0 and fit["admitted"] is None


# --- the plan-layer wiring: the winner rule is unchanged, the
#     population order follows the map ---
def test_off_target_winner_classes_flip():
    import r97_v12_one_shot as r97
    probs = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval" / "holdout_v16_problems.json").read_text())}
    scoring = json.loads(
        (REPO / "eval" / "v16_auditor_scoring.json").read_text())
    lows = {k for k, v in scoring["per_problem"].items() if v <= 2}
    flipped = {}
    for pid in sorted(lows):
        p = probs[pid]
        prob = {
            "problem_id": pid, "device": "(stated in the problem)",
            "failure": p["problem"], "failure_mode": p["problem"],
            "question_type": "invention", "constraint": "",
            "user_variables": []}
        row_out = r97.engine_route.run_row(prob)
        w, _, _ = r97.v10m.select_winner(row_out)
        fit = w.get("mechanism_fit", {})
        flipped[pid] = (fit.get("admitted") is not False)
    assert all(flipped.values()), flipped


def test_sound_rows_keep_on_physics_winners():
    import r97_v12_one_shot as r97
    probs = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval" / "holdout_v16_problems.json").read_text())}
    scoring = json.loads(
        (REPO / "eval" / "v16_auditor_scoring.json").read_text())
    sound = {k for k, v in scoring["per_problem"].items() if v >= 3}
    bad = []
    for pid in sorted(sound):
        p = probs[pid]
        prob = {
            "problem_id": pid, "device": "(stated in the problem)",
            "failure": p["problem"], "failure_mode": p["problem"],
            "question_type": "invention", "constraint": "",
            "user_variables": []}
        row_out = r97.engine_route.run_row(prob)
        w, _, _ = r97.v10m.select_winner(row_out)
        if w.get("mechanism_fit", {}).get("admitted") is False:
            bad.append(pid)
    assert not bad, bad


# --- the typed scans ---
def test_quant_scan_fires_on_qualitative_test():
    from r144_quantitative_testability_scan import (
        scan_quantitative_testability)
    ans = ("EXECUTABLE TEST\nRun the rig and see whether the failure "
           "rate drops over a few weeks.\n")
    hits = scan_quantitative_testability(
        {"question_type": "invention"}, ans)
    assert "QUANT_TEST_MISSING" in hits


def test_quant_scan_passes_on_numeric_threshold():
    from r144_quantitative_testability_scan import (
        scan_quantitative_testability)
    ans = ("PHYSICS CHECK\nThe 2.1 m diffuser at 0.8 m depth yields "
           "45:1 boundary dilution.\nEXECUTABLE TEST\nPass if wear "
           "< 0.2 mm per 1000 h.\n")
    hits = scan_quantitative_testability(
        {"question_type": "invention"}, ans)
    assert not hits, hits


def test_off_target_scan_fires_on_the_anti_mechanism():
    from r144_off_target_scan import scan_off_target
    prob = _prob("Ship stern-tube bearing wears from seawater-"
                 "lubricated abrasion.")
    ans = ("NOVELTY STATEMENT\nThe proposed mechanism is cathodic "
           "protection with sacrificial anodes maintaining a passive "
           "film.\nPHYSICS CHECK\nNernst equation.\n")
    hits = scan_off_target(prob, ans)
    assert "OFF_TARGET_MECHANISM" in hits


def test_off_target_scan_silent_on_on_physics_mechanism():
    from r144_off_target_scan import scan_off_target
    prob = _prob("Ship stern-tube bearing wears from seawater-"
                 "lubricated abrasion.")
    ans = ("NOVELTY STATEMENT\nThe proposed mechanism is a "
           "self-lubricating composite bearing with a harder facing "
           "material spreading the contact pressure.\nPHYSICS "
           "CHECK\nArchard wear law.\n")
    hits = scan_off_target(prob, ans)
    assert not hits, hits

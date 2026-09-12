"""R450-C2: the Visual Feedback Layer evaluation driver.

Produces the round's raw evidence (all OBSERVED, none self-scored):

  R450/TRAJECTORY_PROJECTION_RESULTS.json
      - the canonical projection of the REAL R445 evolution lineage
        (evol-x02-bus-fastcharge-lithium-plating) + guard verdict
      - determinism: two projections byte-compared
  R450/BEFORE_AFTER_DELTA_RESULTS.json
      - before/after correspondence on the canonical GLB chain:
        identity control + two DISTINCT negative-control mutations per
        case (the directive's regression: same mutation -> expected delta
        visible; different mutation -> different delta visible)
  R450/ENGINEERING_FEATURE_VISIBILITY_RESULTS.json
      - per-case component separability from the canonical GLB bytes
  R450/ARTIFACT_DETERMINISM_RESULTS.json
      - instrument determinism on all three canonical GLBs
  R450/LINEAGE_PRESERVATION_RESULTS.json
      - the R444-style chain verification of every evaluated artifact

No thresholds are proposed here: every number is recorded raw with its
method string; interpretation is PENDING_OWNER (Art. XXVII).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "visual-lab" / "benchmark"))
sys.path.insert(0, str(REPO / "visual-lab" / "trajectory"))
sys.path.insert(0, str(REPO / "visual-lab" / "guard"))

import canonical_inputs as ci  # noqa: E402
import negative_controls as NC  # noqa: E402
from schema import canonical_json, project_trajectory, record_sha256  # type: ignore  # noqa: E402
import trajectory_guard as TG  # type: ignore  # noqa: E402
from trajectory_dimensions import (  # noqa: E402
    artifact_determinism,
    before_after_correspondence,
    engineering_feature_visibility,
    lineage_preservation,
)

OUT = REPO / "R450"
REVIEWER = "AI_REVIEW"
ROUND = "R450-C2"


def _write(name: str, payload: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    p.write_text(json.dumps(payload, indent=1) + "\n")
    print("wrote", p.relative_to(REPO))
    return p


def _header(artifact: str, note: str) -> dict:
    return {
        "artifact_type": artifact,
        "round": ROUND,
        "reviewer_provenance": REVIEWER,
        "epistemic_classification": "OBSERVED (raw instrument output; "
                                    "no threshold applied)",
        "threshold_status": "PENDING_OWNER (Art. XXVII — no threshold "
                            "invention by the visual layer)",
        "note": note,
    }


def trajectory_results() -> dict:
    lineage_path = REPO / "R445" / "EVOLUTION_RUNS" / \
        "evol-x02-bus-fastcharge-lithium-plating" / "INVENTION_LINEAGE.json"
    lineage = json.loads(lineage_path.read_text())
    traj = project_trajectory(lineage)
    guard = TG.validate_trajectory_projection(traj)
    TG.check_no_production_promotion(traj)
    traj2 = project_trajectory(json.loads(canonical_json(lineage)))
    deterministic = record_sha256(traj) == record_sha256(traj2)

    # tamper attack: strip the epistemic boundary -> guard must refuse
    tampered = json.loads(canonical_json(traj))
    tampered.pop("epistemic_boundary")
    boundary_attack_blocked = False
    try:
        TG.validate_trajectory_projection(tampered)
    except TG.TrajectoryViolation:
        boundary_attack_blocked = True

    # status re-labeling attack: rename the lineage's own vocabulary
    relabeled = json.loads(canonical_json(traj))
    relabeled["states"][0]["status"] = "VALIDATED_ENGINEERING"
    relabel_attack_blocked = False
    try:
        TG.validate_trajectory_projection(relabeled)
    except TG.TrajectoryViolation:
        relabel_attack_blocked = True

    return {
        **_header("R450_TRAJECTORY_PROJECTION_RESULTS",
                  "the canonical lineage projected to the presentation "
                  "trajectory; rendered verbatim by the trajectory viewer"),
        "source_lineage": {
            "path": str(lineage_path.relative_to(REPO)),
            "lineage_sha256_record": record_sha256(lineage),
            "engine_schema": lineage.get("schema"),
            "run_id": lineage.get("run_id"),
            "stop_reason": lineage.get("stop_reason"),
        },
        "projection": traj,
        "guard_verdict": guard,
        "projection_deterministic": deterministic,
        "attacks": {
            "epistemic_boundary_stripped_blocked": boundary_attack_blocked,
            "status_vocabulary_relabeled_blocked": relabel_attack_blocked,
        },
    }


def before_after_results() -> dict:
    trimesh_mods = ("incorrect_scale", "rotated_component_toppling")
    cases = {}
    for case in ("A", "B", "C"):
        canon_path = ci.case_glb_path(case)
        canon_sha = ci.CANONICAL_CASES[case]["sha256"]
        identity = before_after_correspondence(canon_path, canon_path)
        mutations = {}
        for mod in trimesh_mods:
            rec = NC.run_control(case, mod, seed=7)
            dest = NC.OUT_DIR / f"{case}_{mod}.glb"
            if not dest.exists():
                rec = NC.run_control(case, mod, seed=7)
            mutations[mod] = {
                "control_record": rec,
                "correspondence": before_after_correspondence(
                    canon_path, dest),
            }
        cases[case] = {
            "canonical_sha256": canon_sha,
            "identity_control": identity,
            "mutations": mutations,
        }
    # cross-case delta: a DIFFERENT object is the maximal-delta control
    cross = before_after_correspondence(ci.case_glb_path("A"),
                                        ci.case_glb_path("B"))
    return {
        **_header("R450_BEFORE_AFTER_DELTA_RESULTS",
                  "the BEFORE/AFTER/DELTA presentation contract measured: "
                  "identity pairs must read unchanged; recorded mutations "
                  "must read as visible, distinct deltas"),
        "mutation_set": {
            "identity": "same bytes twice — the calibration control",
            "incorrect_scale": "negative-control mutation (R449 set)",
            "rotated_component_toppling": "negative-control mutation (R449 set)",
        },
        "cases": cases,
        "cross_case_control_A_vs_B": cross,
    }


def visibility_results() -> dict:
    cases = {}
    for case in ("A", "B", "C"):
        cases[case] = engineering_feature_visibility(
            ci.case_glb_path(case))
    return {
        **_header("R450_ENGINEERING_FEATURE_VISIBILITY_RESULTS",
                  "are the declared engineering components spatially "
                  "present and separable — the preconditions for visual "
                  "knowability, measured from canonical bytes (never pixels)"),
        "cases": cases,
    }


def determinism_results() -> dict:
    cases = {}
    for case in ("A", "B", "C"):
        cases[case] = artifact_determinism(ci.case_glb_path(case))
    return {
        **_header("R450_ARTIFACT_DETERMINISM_RESULTS",
                  "the same canonical bytes yield the byte-identical "
                  "measurement record (the instrument's determinism "
                  "contract; Art. LXII)"),
        "cases": cases,
    }


def lineage_results() -> dict:
    chain = []
    for case in ("A", "B", "C"):
        chain.append({
            "role": f"canonical_root_glb_{case}",
            "path": str(ci.case_glb_path(case)),
            "expected_sha256": ci.CANONICAL_CASES[case]["sha256"],
        })
    res = lineage_preservation(chain)
    # attack: one tampered expectation must FAIL the whole chain
    tampered = lineage_preservation([
        chain[0],
        {**chain[1], "expected_sha256": "0" * 64},
    ])
    return {
        **_header("R450_LINEAGE_PRESERVATION_RESULTS",
                  "the R444 chain contract applied to the benchmark's "
                  "evaluated artifacts (missing -> INCOMPLETE, mismatch "
                  "-> FAIL, never a pass)"),
        "canonical_chain": res,
        "tamper_attack": {"verdict": tampered["verdict"],
                          "expected": "FAIL",
                          "blocked": tampered["verdict"] == "FAIL"},
    }


def main() -> int:
    traj = trajectory_results()
    _write("TRAJECTORY_PROJECTION_RESULTS.json", traj)
    _write("BEFORE_AFTER_DELTA_RESULTS.json", before_after_results())
    _write("ENGINEERING_FEATURE_VISIBILITY_RESULTS.json",
           visibility_results())
    _write("ARTIFACT_DETERMINISM_RESULTS.json", determinism_results())
    _write("LINEAGE_PRESERVATION_RESULTS.json", lineage_results())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

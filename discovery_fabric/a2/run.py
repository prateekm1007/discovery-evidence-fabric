"""
A2 Runner — canonical entrypoint for the A2 discovery pipeline.

A2 = RETRIEVE → FREEZE → SYNTHESIZE → VERIFY → PRIOR-ART → ADVERSARIAL → CLASSIFY

Usage:
  python -m discovery_fabric.a2.run --problem <problem_id>
  python -m discovery_fabric.a2.run --problem p01 --snapshot --run --verify --prior-art --attack --finalize
"""
from __future__ import annotations
import json, hashlib, argparse, sys, os
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from discovery_fabric.a2.retrieve import retrieve
from discovery_fabric.a2.synthesize import synthesize
from discovery_fabric.a2.verify import verify_evidence
from discovery_fabric.a2.prior_art import search_prior_art
from discovery_fabric.a2.adversarial import adversarial_challenge
from discovery_fabric.a2.classify import classify


# Frozen problem manifest (10 medical-device problems)
PROBLEM_MANIFEST = [
    {"problem_id": "p01", "device": "Cardiac Pacemaker", "failure_mode": "BATTERY_FAILURE",
     "failure": "Pacemaker battery depletion requiring surgical replacement",
     "constraint": "Must maintain cardiac pacing for 5-10 years without surgical replacement"},
    {"problem_id": "p02", "device": "Cardiac Pacemaker", "failure_mode": "MECHANICAL_FAILURE",
     "failure": "Pacemaker lead fracture at the electrode-header junction",
     "constraint": "Must maintain electrical continuity under cyclic loading for device lifetime"},
    {"problem_id": "p03", "device": "Hip Implant", "failure_mode": "WEAR",
     "failure": "Hip implant polyethylene wear causing osteolysis and loosening",
     "constraint": "Must maintain articulation surface integrity for 15+ years under cyclic loading"},
    {"problem_id": "p04", "device": "Hip Implant", "failure_mode": "MECHANICAL_FAILURE",
     "failure": "Hip stem neck fracture at the neck-stem junction",
     "constraint": "Must resist cyclic fatigue loading at stress concentration points"},
    {"problem_id": "p05", "device": "Knee Implant", "failure_mode": "MECHANICAL_FAILURE",
     "failure": "Knee implant tibial baseplate loosening at cement-prosthesis interface",
     "constraint": "Must maintain rigid fixation at the cement-prosthesis interface"},
    {"problem_id": "p06", "device": "Intraocular Lens", "failure_mode": "INFECTION",
     "failure": "Post-operative endophthalmitis following intraocular lens implantation",
     "constraint": "Must prevent microbial colonization on lens surfaces without systemic antibiotics"},
    {"problem_id": "p07", "device": "CT Scanner", "failure_mode": "THERMAL_DAMAGE",
     "failure": "CT scanner x-ray tube overheating causing imaging artifacts",
     "constraint": "Must maintain imaging performance under continuous clinical workload"},
    {"problem_id": "p08", "device": "Deep Brain Stimulator", "failure_mode": "BATTERY_FAILURE",
     "failure": "DBS battery depletion causing symptom return",
     "constraint": "Must maintain neurostimulation for 10+ years without surgical intervention"},
    {"problem_id": "p09", "device": "Continuous Glucose Monitor", "failure_mode": "SENSOR_DRIFT",
     "failure": "CGM sensor accuracy degrades over 14-day wear period",
     "constraint": "Must maintain measurement accuracy within ±20% for 14+ days"},
    {"problem_id": "p10", "device": "Surgical Stapler", "failure_mode": "MECHANICAL_FAILURE",
     "failure": "Surgical stapler misfire causing incomplete tissue closure",
     "constraint": "Must reliably form staples across the full range of tissue thicknesses"},
]


def get_problem(problem_id: str) -> dict | None:
    for p in PROBLEM_MANIFEST:
        if p["problem_id"] == problem_id:
            return p
    return None


def _full_hash(s): return hashlib.sha256(s.encode()).hexdigest()


def run_a2(problem_id: str, output_dir: str = "a2_output") -> dict:
    """Run the complete A2 pipeline for one problem."""
    problem = get_problem(problem_id)
    if not problem:
        print(f"ERROR: problem {problem_id} not found")
        return {"error": "problem not found"}

    out = Path(output_dir) / problem_id
    out.mkdir(parents=True, exist_ok=True)

    run_id = f"run:{problem_id}:{datetime.now(timezone.utc).isoformat()[:19]}"
    code_commit = os.popen("git rev-parse HEAD 2>/dev/null").read().strip() or "unknown"

    print(f"\n{'='*60}")
    print(f"A2 RUN: {run_id}")
    print(f"Problem: {problem_id} — {problem['device']}")
    print(f"{'='*60}")

    # STEP 1: RETRIEVE
    print("\n[STEP 1] RETRIEVE")
    evidence = retrieve(problem)

    # STEP 2: FREEZE
    print("\n[STEP 2] FREEZE")
    source_snapshot = {
        "run_id": run_id, "problem_id": problem_id,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "evidence_count": len(evidence),
        "evidence": evidence,
    }
    snapshot_content = json.dumps(source_snapshot, indent=2, sort_keys=True)
    snapshot_hash = _full_hash(snapshot_content)
    source_snapshot["snapshot_hash"] = snapshot_hash
    (out / "source_snapshot.json").write_text(json.dumps(source_snapshot, indent=2, default=str), encoding="utf-8")

    source_hashes = {e["id"]: e["content_hash"] for e in evidence}
    (out / "source_hashes.json").write_text(json.dumps(source_hashes, indent=2), encoding="utf-8")

    # STEP 3: SYNTHESIZE
    print("\n[STEP 3] SYNTHESIZE")
    candidate = synthesize(problem, evidence)
    if not candidate:
        print("\n[RESULT] REJECTED — synthesis failed")
        final_state = {"run_id": run_id, "final_status": "REJECTED",
                       "reason": "synthesis failed", "epistemic_state": "OBSERVED"}
        (out / "final_state.json").write_text(json.dumps(final_state, indent=2), encoding="utf-8")
        return final_state

    candidate["run_id"] = run_id
    (out / "candidate.json").write_text(json.dumps(candidate, indent=2, default=str), encoding="utf-8")

    # Write evidence ledger
    with open(out / "evidence_ledger.jsonl", "w") as f:
        for e in evidence:
            entry = {"run_id": run_id, "source_id": e["id"], "source_hash": e["content_hash"],
                     "retrieval_timestamp": e["retrieval_timestamp"], "title": e["title"]}
            f.write(json.dumps(entry) + "\n")

    # STEP 4: VERIFY EVIDENCE
    print("\n[STEP 4] VERIFY EVIDENCE")
    verification = verify_evidence(candidate, evidence)

    # STEP 5: PRIOR-ART SEARCH
    print("\n[STEP 5] PRIOR-ART SEARCH")
    prior_art_report = search_prior_art(candidate["intervention"], problem["device"])
    (out / "prior_art_report.json").write_text(json.dumps(prior_art_report, indent=2, default=str), encoding="utf-8")

    # STEP 6: ADVERSARIAL CHALLENGE
    print("\n[STEP 6] ADVERSARIAL CHALLENGE")
    adversarial_report = adversarial_challenge(candidate)
    (out / "adversarial_report.json").write_text(json.dumps(adversarial_report, indent=2, default=str), encoding="utf-8")

    # STEP 7: EPISTEMIC CLASSIFICATION
    print("\n[STEP 7] EPISTEMIC CLASSIFICATION")
    classification = classify(candidate, verification, prior_art_report, adversarial_report)

    # FINAL STATE
    final_state = {
        "run_id": run_id,
        "problem_id": problem_id,
        "device": problem["device"],
        "final_status": classification["final_status"],
        "epistemic_state": classification["epistemic_state"],
        "reason": classification["reason"],
        "evidence_verified": verification["verified"],
        "prior_art_status": prior_art_report["prior_art_status"],
        "adversarial_overall": adversarial_report["overall"],
        "model": "deepseek/deepseek-v4-flash",
        "code_commit": code_commit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (out / "final_state.json").write_text(json.dumps(final_state, indent=2, default=str), encoding="utf-8")

    # RUN MANIFEST
    run_manifest = {
        "run_id": run_id,
        "problem_id": problem_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "deepseek/deepseek-v4-flash",
        "model_config": {"temperature": 0.3, "max_tokens": 2000},
        "code_commit": code_commit,
        "source_snapshot_hash": snapshot_hash,
        "candidate_output_hash": candidate.get("output_hash", ""),
        "artifacts": [
            "source_snapshot.json", "source_hashes.json", "candidate.json",
            "evidence_ledger.jsonl", "prior_art_report.json",
            "adversarial_report.json", "final_state.json",
        ],
    }
    (out / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, default=str), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"RESULT: {final_state['final_status']}")
    print(f"  epistemic_state: {final_state['epistemic_state']}")
    print(f"  reason: {final_state['reason']}")
    print(f"  artifacts: {out}/")
    print(f"{'='*60}")
    return final_state


def main():
    parser = argparse.ArgumentParser(description="A2 Discovery Runner")
    parser.add_argument("--problem", required=True, help="Problem ID (e.g., p01)")
    parser.add_argument("--output", default="a2_output", help="Output directory")
    args = parser.parse_args()
    run_a2(args.problem, args.output)


if __name__ == "__main__":
    main()

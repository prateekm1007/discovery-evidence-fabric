#!/usr/bin/env python3
"""scripts/r400_consolidate_physics_record.py — finalize the R400-C
evidence record: bind the capture contract to the AUTHORITATIVE
machine artifacts (envelope_PHYSICS.json — the physics stage's own
envelope with the computation log: method, residual, input/output
hashes, assumptions, limitations), rather than the API projection.

The API projection is what an external observer sees; the envelope is
what the machine recorded. The record carries BOTH and states which
is which (Art. III — the claimant does not define what the evidence
says).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REC = REPO_ROOT / "R400" / "PRODUCTION_PHYSICS_RUN_930eca8b.json"
ENV = (REPO_ROOT / "R400" / "RUN_ARTIFACTS_ui_partial_obstruction" /
       "envelope_PHYSICS.json")


def main() -> int:
    rec = json.loads(REC.read_text())
    env = json.loads(ENV.read_text())

    ph = env.get("physics") or {}
    cr = ph.get("computational_result") or {}
    comp_log = cr.get("computation_log") or {}

    cap = rec.get("r400c_capture") or {}

    # authoritative solver identity + hashes (from the envelope)
    cap["physics_model_version"] = {
        "solver": ph.get("solver_version"),
        "gate": ph.get("stage_version"),
        "directive_chain": ph.get("directive_chain"),
        "chain_executed": ph.get("chain_executed"),
    }
    cap["input_hash"] = {
        "solver_input_hash": cr.get("input_hash"),
        "candidate_geometry_hash": (cap.get("input_hash") or {}).get(
            "candidate_geometry_hash"),
        "baseline_geometry_hash": (cap.get("input_hash") or {}).get(
            "baseline_geometry_hash"),
    }
    cap["output_hash"] = {
        "solver_output_hash": cr.get("output_hash"),
        "result_class": cr.get("result_class") or
        "COMPUTATIONAL_RESULT",
        "final_envelope_hash_prefix": (cap.get("output_hash") or {}).get(
            "final_envelope_hash_prefix"),
        "invention_spec_hash": (cap.get("output_hash") or {}).get(
            "invention_spec_hash"),
        "engineering_reasoning_chains_hash": (
            cap.get("output_hash") or {}).get(
            "engineering_reasoning_chains_hash"),
    }
    cap["computation_log"] = comp_log
    cap["lifecycle_verdict"] = ph.get("lifecycle_verdict")
    cap["lifecycle_effect"] = ph.get("lifecycle_effect")
    cap["failure_state"] = ph.get("failure_mode_contract") or cap.get(
        "failure_state")
    cap["baseline_comparison"] = ph.get("baseline_comparison") or cap.get(
        "baseline_comparison")

    rec["r400c_capture"] = cap
    rec["authoritative_source"] = {
        "artifact": "R400/RUN_ARTIFACTS_ui_partial_obstruction/"
                    "envelope_PHYSICS.json",
        "note": ("the physics stage's own envelope (written by the "
                 "run, on disk) is the authority for solver identity, "
                 "computation log, and input/output hashes; the API "
                 "session detail is the external observer's view. "
                 "Both are preserved; the capture cites the envelope "
                 "for solver-level fields (Art. III/XXIV)."),
        "run_id": ph.get("run_id"),
    }
    # carry the honest transport + no-new-compute rehydrate note
    rec["run_created"]["compute_note"] = (
        "the run itself executed 2026-09-02T22:01:55Z-22:09:57Z on the "
        "local artifact server (real LLM transport: zai glm-4-plus via "
        "the sandbox local-gateway, probe-verified OK; the deployed "
        "contract pins nvidia/openai/gpt-oss-120b — recorded, not "
        "conflated). This record was rehydrated from the completed "
        "session with no new compute consumed.")
    REC.write_text(json.dumps(rec, indent=1, default=str))
    c = rec["r400c_capture"]
    print("consolidated. solver:", c["physics_model_version"]["solver"])
    print("input_hash:", c["input_hash"]["solver_input_hash"])
    print("output_hash:", c["output_hash"]["solver_output_hash"])
    print("lifecycle:", c.get("lifecycle_verdict"))
    print("result_class:", c["output_hash"].get("result_class"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

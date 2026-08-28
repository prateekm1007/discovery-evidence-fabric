"""Smoke: audit the committed REAL E2E run with the Coder 2 benchmark."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.benchmark import audit_runner  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
contract = json.loads(
    (REPO / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json")
    .read_text())
profile = json.loads(
    (REPO / "artifacts/benchmark/BENCHMARK_DOSSIER_PROFILE.json").read_text())

audit = audit_runner.audit_run(REPO / "ENGINE_RUNS/F_SMOKE_REAL_P01",
                               contract, profile)
print("verdict:", audit["verdict"])
print("failing:", audit["failing_dimensions"])
print("conditional:", audit["conditional_dimensions"])
print()
for k, v in audit["dimension_verdicts"].items():
    print(f"  {k:32s} {v}")
print()
print("objects:", json.dumps(audit["measured"]["objects"]))
print("reasoning:", audit["reasoning_audit"].get("completeness_rate"),
      audit["reasoning_audit"].get("chains_complete"), "/",
      audit["reasoning_audit"].get("chains_total"))
print("numprov:", audit["numerical_provenance"]["verdict"],
      audit["numerical_provenance"]["hard_violations"], "hard /",
      audit["numerical_provenance"]["soft_violations"], "soft")
print("vv:", audit["vv_separation"]["verdict"],
      audit["vv_separation"]["violation_count"])
print("replay:", audit["independent_replay"]["verdict"],
      audit["independent_replay"]["claims_fully_bound"], "/",
      audit["independent_replay"]["claims_replayed"])

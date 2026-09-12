"""Test battery for visual-lab geometry metrics + runner fail-closed behavior.

Uses real trimesh geometry: two boxes differing by 2% and a sphere as a
gross-drift control. Run: python3 test_metrics.py  (exit 0 = all green)
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics  # noqa: E402

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append((name, detail))


here = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp(prefix="r448-metrics-", dir=os.path.join(here, "fixtures"))

box_a = metrics._require_trimesh().creation.box(extents=[1.0, 1.0, 1.0])
box_b = metrics._require_trimesh().creation.box(extents=[1.02, 1.02, 1.02])
sphere = metrics._require_trimesh().creation.icosphere(subdivisions=3, radius=0.8)

a_path = os.path.join(tmp, "canonical_box.glb")
b_path = os.path.join(tmp, "candidate_box.glb")
s_path = os.path.join(tmp, "candidate_sphere.glb")
box_a.export(a_path)
box_b.export(b_path)
sphere.export(s_path)

# 1. round-trip GLB load works
la, lb = metrics.load_mesh(a_path), metrics.load_mesh(b_path)
check("glb_roundtrip_load", abs(la.extents[0] - 1.0) < 1e-6 and abs(lb.extents[0] - 1.02) < 1e-6,
      f"extents {la.extents} {lb.extents}")

# 2. dimension deviation is exactly ~2% for the scaled box
r = metrics.compare(la, lb, n=8000, seed=42)
dev = r["metrics"]["dimension_deviation"]["max_abs_axis_deviation_pct"]
check("dimension_deviation_2pct", abs(dev - 2.0) < 0.05, f"got {dev}")

# 3. normalized chamfer for a 2% box offset is small (< 1.2% of diagonal)
ch = r["metrics"]["normalized_chamfer_p95_over_diag"]
check("chamfer_small_for_2pct_box", 0.0 <= ch < 0.012, f"got {ch}")

# 4. sphere vs box is a gross outlier (much larger chamfer than box-vs-box)
r2 = metrics.compare(la, metrics.load_mesh(s_path), n=8000, seed=42)
ch2 = r2["metrics"]["normalized_chamfer_p95_over_diag"]
check("chamfer_gross_drift_detected", ch2 > ch * 5, f"box {ch} vs sphere {ch2}")

# 5. determinism: same seed -> identical chamfer
r3 = metrics.compare(la, lb, n=8000, seed=42)
check("metrics_deterministic_same_seed",
      r3["metrics"]["chamfer_p95"] == r["metrics"]["chamfer_p95"])

# 6. runner fails closed when the model adapter is missing (no fake success)
out_rec = os.path.join(tmp, "record.json")
proc = subprocess.run(
    [sys.executable, os.path.join(here, "runner_template.py"),
     "--model-id", "microsoft/TRELLIS.2-4B", "--case", "case-C",
     "--fixture-glb", a_path, "--registry",
     os.path.join(here, "..", "registry", "hf_visual_model_registry.json"),
     "--out", out_rec],
    capture_output=True, text=True)
rec = json.load(open(out_rec)) if os.path.isfile(out_rec) else {}
code = rec.get("failure", {}).get("code")
# The runner must fail closed with a TYPED code before any fake success: in a
# GPU environment that is INTEGRATION_POINT_MISSING; on a host without torch
# it is HARDWARE_UNAVAILABLE (probe unavailable). Both prove the invariant.
check("runner_fails_closed_no_adapter",
      proc.returncode == 1 and rec.get("benchmark_status") == "FAILED"
      and code in ("INTEGRATION_POINT_MISSING", "HARDWARE_UNAVAILABLE"),
      f"rc={proc.returncode} code={code} rec={json.dumps(rec)[:200]}")

# 7. runner refuses license-blocked models without the internal-eval flag
out_rec2 = os.path.join(tmp, "record_partpacker.json")
proc2 = subprocess.run(
    [sys.executable, os.path.join(here, "runner_template.py"),
     "--model-id", "nvidia/PartPacker", "--case", "case-A",
     "--fixture-glb", a_path, "--registry",
     os.path.join(here, "..", "registry", "hf_visual_model_registry.json"),
     "--out", out_rec2],
    capture_output=True, text=True)
rec2 = json.load(open(out_rec2)) if os.path.isfile(out_rec2) else {}
check("runner_enforces_license_gate",
      proc2.returncode == 1 and rec2.get("failure", {}).get("code") == "LICENSE_GATE_BLOCKED",
      f"rc={proc2.returncode} rec={json.dumps(rec2)[:200]}")

# 8. fixture sha256 provenance recorded
check("fixture_sha_recorded", len(rec.get("fixture_glb_sha256", "")) == 64)

print(f"passed: {len(passed)}  failed: {len(failed)}")
for name, detail in failed:
    print(f"  FAIL {name}: {detail}")
if failed:
    sys.exit(1)
print("METRICS + RUNNER BATTERY: ALL GREEN")

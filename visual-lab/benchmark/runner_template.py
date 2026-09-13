"""Toscanini Visual Lab - benchmark runner template (fail-closed).

Entry point for a HF Jobs benchmark run of ONE candidate model against ONE
canonical case fixture. The runner is deliberately incomplete where a live GPU
model call is required: the two integration points raise typed failures instead
of improvising (Constitution Art. IV/VI/LXI - no fallback epistemology, no
manufactured provenance, unrun is NOT_RUN).

Every run emits a typed VISUAL_BENCHMARK_RECORD. A record can never claim a
pass it did not measure, and its outputs are stamped
epistemic_class = COMPUTATIONAL_RENDER.

Usage (HF Jobs or local smoke):
  python3 runner_template.py --model-id microsoft/TRELLIS.2-4B \
      --case case-C --fixture-glb /path/to/canonical.glb \
      --registry ../registry/hf_visual_model_registry.json \
      --out ./records/caseC_trellis2.json
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics  # noqa: E402

RECORD_TYPE = "VISUAL_BENCHMARK_RECORD"
SCHEMA_VERSION = "1.0.0"


def fail_closed(record, code, detail, out_path):
    record["benchmark_status"] = "FAILED"
    record["failure"] = {"code": code, "detail": detail}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(f"FAIL-CLOSED {code}: {detail}")
    return 1


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def probe_hardware():
    """Live VRAM probe. Torch absent -> typed unavailable, never a guess."""
    try:
        import torch  # noqa: PLC0415
    except ImportError:
        return {"probe_status": "HARDWARE_PROBE_UNAVAILABLE", "detail": "torch not installed"}
    if not torch.cuda.is_available():
        return {"probe_status": "NO_CUDA_DEVICE", "detail": "cuda not available"}
    free_b, total_b = torch.cuda.mem_get_info()
    return {
        "probe_status": "OK",
        "vram_free_gb": round(free_b / 1e9, 2),
        "vram_total_gb": round(total_b / 1e9, 2),
        "device": torch.cuda.get_device_name(0),
    }


def emit_reference_inputs(canonical_glb_path):
    """Integration point 1: canonical reference renders for image-conditioned
    candidates. MUST be produced by Coder 2's canonical renderer so that the
    benchmark consumes the single geometry authority chain."""
    raise NotImplementedError(
        "RENDERER_HOOK_MISSING: connect to the Coder 2 canonical renderer "
        "(renderer/render.js) to emit pose-consistent canonical reference "
        "renders. Do not substitute an ad-hoc renderer."
    )


def run_model_inference(model_id, reference_inputs):
    """Integration point 2: the candidate model call on GPU hardware. One
    adapter per model, added only under benchmark supervision on HF Jobs."""
    raise NotImplementedError(
        f"MODEL_ADAPTER_MISSING: no benchmark adapter implemented for "
        f"{model_id}. Adapters are added per model under supervision on HF "
        f"Jobs hardware; no improvised substitution is permitted."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--case", required=True, choices=["case-A", "case-B", "case-C"])
    ap.add_argument("--fixture-glb", required=True)
    ap.add_argument("--registry", default="../registry/hf_visual_model_registry.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--internal-eval-only", action="store_true",
                    help="required for license-blocked models (research/internal evaluation only)")
    args = ap.parse_args()

    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {
        "record_type": RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "model_id": args.model_id,
        "case": args.case,
        "started_at": started,
        "epistemic_class_of_outputs": "COMPUTATIONAL_RENDER",
        "engineer_claims": False,
        "benchmark_status": "RUNNING",
    }

    if not os.path.isfile(args.fixture_glb):
        return fail_closed(record, "FIXTURE_GLB_MISSING", args.fixture_glb, args.out)
    fixture_sha = sha256_file(args.fixture_glb)
    record["fixture_glb_sha256"] = fixture_sha

    if not os.path.isfile(args.registry):
        return fail_closed(record, "REGISTRY_MISSING", args.registry, args.out)
    registry = json.load(open(args.registry, encoding="utf-8"))
    entry = next((e for e in registry["models"] if e["model_id"] == args.model_id), None)
    if entry is None:
        return fail_closed(record, "MODEL_NOT_IN_REGISTRY", args.model_id, args.out)

    gate = entry["license_gate"]["gate_status"]
    if gate.startswith("COMMERCIAL_BLOCKED") and not args.internal_eval_only:
        return fail_closed(record, "LICENSE_GATE_BLOCKED",
                           f"gate={gate}; pass --internal-eval-only only for research/internal evaluation",
                           args.out)
    record["license_gate_at_run"] = gate
    record["internal_eval_only"] = bool(args.internal_eval_only)

    hw = probe_hardware()
    record["hardware_probe"] = hw
    if hw["probe_status"] != "OK":
        return fail_closed(record, "HARDWARE_UNAVAILABLE", json.dumps(hw), args.out)
    claimed = entry["vram_requirement"]["claimed"]
    record["vram_claim_under_test"] = claimed

    try:
        canonical_mesh = metrics.load_mesh(args.fixture_glb)
    except metrics.FailClosedError as e:
        return fail_closed(record, "FIXTURE_LOAD_FAILED", str(e), args.out)

    try:
        reference_inputs = emit_reference_inputs(args.fixture_glb)
        candidate_mesh_path, candidate_meta = run_model_inference(args.model_id, reference_inputs)
    except NotImplementedError as e:
        return fail_closed(record, "INTEGRATION_POINT_MISSING", str(e), args.out)

    try:
        candidate_mesh = metrics.load_mesh(candidate_mesh_path)
        result = metrics.compare(canonical_mesh, candidate_mesh)
    except metrics.FailClosedError as e:
        return fail_closed(record, "METRICS_FAILED", str(e), args.out)

    record["benchmark_status"] = "COMPLETED"
    record["candidate_meta"] = candidate_meta
    record["metrics"] = result["metrics"]
    record["measurement_provenance"] = result["measurement_provenance"]
    record["decision_note"] = (
        "Metrics are PRESENTATION acceptance evidence only. Threshold "
        "ratification and any approval decision live in benchmark/protocol.json "
        "and the registry; no render validates engineering or physics."
    )
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print("COMPLETED ->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

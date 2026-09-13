# HF Jobs Quickstart - Toscanini Visual Model Benchmark Lab

The production Space (`prateekm1/toscanini-prod-validation`) is the stable
product. Every candidate-model experiment runs HERE, on HF Jobs, billed by
actual usage against PRO credits. No experimental model is ever installed in
the production Space.

## Prerequisites

- PRO account `prateekm1` (verified live in the registry account probe).
- `hf` CLI: `pip install -U "huggingface_hub[jobs]"` then `hf auth login`.
- Canonical case fixture GLBs resolved from the canonical repo
  (sha256 anchor prefixes in `benchmark/protocol.json`).

## Launch a benchmark run

```bash
# Verify CLI surface first (flags evolve; this template documents intent):
hf jobs run --help

# Example: TRELLIS.2 on an A100-80GB (its card claims >= 24 GB VRAM)
hf jobs run --flavor a100-80gb \
  python visual-lab/benchmark/runner_template.py \
    --model-id microsoft/TRELLIS.2-4B \
    --case case-C \
    --fixture-glb /data/fixtures/caseC_canonical.glb \
    --registry visual-lab/registry/hf_visual_model_registry.json \
    --out /data/records/caseC_trellis2.json
```

Or use the wrapper: `bash jobs/run_bench_job.sh <model-id> <case> <fixture> <out>`

## Operating rules

1. The runner fails closed: missing adapter, missing renderer hook, missing
   GPU, or a blocked license each produce a TYPED failure record - never an
   improvised run.
2. Every record is typed `VISUAL_BENCHMARK_RECORD` with reproducibility fields
   (model id + revision, fixture sha256, seed, hardware flavor).
3. First runs are calibration runs: they fill `measured_peak_vram` and
   `latency` into the registry and calibrate the PROPOSED thresholds. Nothing
   is APPROVED by calibration (thresholds need owner ratification, Art. XXVII).
4. Upload every record + generated asset to the Storage Bucket with its
   epistemic-class sidecar; keep Space git clean.

## Suggested first sequence (cheapest decisive information first)

1. `depth-anything/DA3METRIC-LARGE` (small, CPU/L4-class) - brings the referee
   online and calibrates cross-view consistency scoring.
2. `tencent/Hunyuan3D-Omni` on l40s-48gb - verifies the "10 GB VRAM" card
   claim live (the only candidate whose card quote is already verbatim-captured)
   and answers the control-fidelity question (bbox/point-cloud conditioning).
3. `microsoft/TRELLIS.2-4B` on a100-80gb - the highest-upside presentation
   candidate; calibrates the fidelity thresholds.

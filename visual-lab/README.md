# Toscanini Visual Model Laboratory (R448)

Operator directive: **build a Hugging Face Visual Model Registry + Benchmark
Lab first, rather than blindly integrating models.** Run the same Toscanini
canonical geometry through the candidates and objectively determine which
model improves presentation **without corrupting engineering truth**.

## The one absolute rule

```text
Coder 1 canonical geometry (CadQuery/OCCT)
        │  engineering truth
        ▼
   canonical GLB ──────────────► Coder 2 renderer ──► visual compiler
        │                                                  │
        │  reference renders only                          ▼
        ▼                                          website / buyer package
   HF VISUAL LAB (this repo)                       (single authority chain)
   TRELLIS.2 · Hunyuan3D · Depth Anything 3 · ...
        │
        ▼
   presentation assets  =  COMPUTATIONAL_RENDER, never engineering geometry,
                           never physical validation, never in the GLB chain
```

Architecture: **canonical HF Space = stable product · HF GPU Jobs = laboratory
· HF Storage Buckets = models/cache/artifacts · visual compiler = the only
publisher.** No experimental model is ever installed in the production Space.

## Contents

| Path | What it is |
|---|---|
| `registry/hf_visual_model_registry.json` | The registry: 8 candidates, 17 directive fields each, live HF verification (sha pins, license tags, VRAM card quotes), license gates, epistemic invariants |
| `registry/hf_api_verification_raw.json` | Raw Hub API evidence behind the registry (whoami probe, per-model records, DA3 collection members) |
| `guard/epistemic_guard.py` | Machine enforcement: presentation ≠ engineering; promotion forbidden; single geometry authority; fail closed |
| `guard/test_epistemic_guard.py` | Adversarial battery: 6 positive + 10 attacks (16/16 green) |
| `benchmark/protocol.json` | Procedure, metric definitions, PROPOSED thresholds (owner ratification pending), decision rubric, typed failure codes |
| `benchmark/metrics.py` | Real geometry fidelity metrics (trimesh/numpy, deterministic): chamfer p95/bbox-diag, sorted-axis dimension deviation, volume deviation |
| `benchmark/runner_template.py` | Fail-closed HF Jobs runner: license gate → hardware probe → canonical reference hook → model adapter → metrics → typed record |
| `benchmark/test_metrics.py` | 8-test battery incl. runner fail-closed and license-gate refusal (8/8 green) |
| `jobs/` | HF Jobs quickstart + launch wrapper (lab compute, never the production Space) |
| `storage/bucket_layout.json` | Storage Bucket layout contract with epistemic sidecars |

## Verification state (honest panel)

- Registry verification: **live** (HF API, account `prateekm1`, PRO verified).
- Guard battery: **16/16 green**. Metrics/runner battery: **8/8 green**.
- Benchmarks: **NOT_RUN** - by design. They run on HF Jobs GPU hardware with
  real adapters; nothing here pretends otherwise (Art. VI, LXI).
- Thresholds: **PROPOSED, pending owner ratification** (Art. XXVII).
- License gates: PartPacker `COMMERCIAL_BLOCKED` (card-cited non-commercial);
  Hunyuan family `COMMERCIAL_REVIEW_REQUIRED` (territorial community license);
  MIT entries pre-cleared for evaluation only. Final legal review always
  required before any commercial shipment.
- Model-card capability claims are labeled `MODEL_CARD_CLAIM_UNVERIFIED` until
  a benchmark run measures them.

## Candidate priorities (operator ranking)

| Priority | Model | Lab role |
|---|---|---|
| P1 | TRELLIS.2-4B | presentation assets, material exploration, hero variants |
| P1 | Hunyuan3D-2.1 | PBR material presentation |
| P1 | Hunyuan3D-Omni | constraint-aware generation from canonical bbox/point-cloud signals |
| P2 | Hunyuan3D-2mv | multi-view consistency from the canonical view ladder |
| P2 | Depth Anything 3 | independent referee: depth/camera/consistency verification |
| P2 | DetailGen3D | presentation detail refinement |
| P2* | PartPacker | exploded-view part research (internal eval only - license) |
| P3 | MeshAnythingV2 | mesh topology styling within face budget |

## Suggested next sequence

1. Referee first: `DA3METRIC-LARGE` calibration run (cheapest decisive
   information).
2. `Hunyuan3D-Omni` on l40s-48gb: verify the 10 GB card claim live + answer
   the control-fidelity question.
3. `TRELLIS.2-4B` on a100-80gb: calibrate the fidelity thresholds.
4. Owner ratifies thresholds → first approval decisions (presentation role
   only) → integration decision for the canonical Space remains owner-gated.

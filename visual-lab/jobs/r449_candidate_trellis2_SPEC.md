# R449 TRELLIS.2 Arm Specification (PREPARED - NOT LAUNCHED)

Sequence position 3 per the operator directive (Step 5): the benchmark must
prove the earlier candidates first. This arm launches only after the
Hunyuan3D-Omni arm is measured and its raw numbers published.

## Arm definition

| Field | Value |
|---|---|
| model_id | `microsoft/TRELLIS.2-4B` |
| revision pin | `af44b45f2e35a493886929c6d786e563ec68364d` (registry live-verified 2026-09-11) |
| license | MIT tag -> `COMMERCIAL_CLEAR` (provisional; registry `final_legal_review: REQUIRED_BEFORE_ANY_COMMERCIAL_SHIPMENT`) |
| role | PRESENTATION_CANDIDATE (never engineering authority) |
| conditioning | single reference image: the same deterministic canonical projection `view_pz.png` used by the Hunyuan arm (identical input contract across arms, Art. XLVII) |
| hardware | `a100-large` (registry/model-card claim: >= 24 GB NVIDIA GPU - MODEL_CARD_CLAIM, to be re-measured as peak_vram_gb telemetry) |
| timeout | 40 m (bounded cost ~ $1.70 max) |
| flavor launch | `hf jobs uv run visual-lab/jobs/r449_candidate_trellis2.py --flavor a100-large --timeout 40m --secrets HF_TOKEN --detach` |

## Inputs (already staged in the bucket)

- `renders/R449/reference/case_{A,B,C}/view_pz.png` (sha-pinned in MANIFEST.json)
- source GLB identity pinned in the provenance sidecar (the R446/R447 canonical bytes)

## Outputs (same contract as the Hunyuan arm)

- `benchmarks/R449/outputs/trellis2/case_{A,B,C}_generated.glb` + `.sidecar.json`
  (11-field provenance contract, `visual_role: PRESENTATION_CANDIDATE`)
- typed record `benchmarks/R449/records/CANDIDATE_TRELLIS2_RECORD.json`
  (every failure mode writes the record before exit - Art. LXI)

## Measurement (after generation)

Identical instruments, identical seeds: normalized chamfer p95 / bbox diag,
sorted-axis dimension deviation, component-name recall/precision,
per-component pose deltas, six-view occupancy IoU, DA3 depth-signature
divergence (if the referee layer loaded). Raw numbers only -
thresholds PENDING_OWNER_RATIFICATION.

## Question this arm answers (same as every arm)

Can this model improve the presentation of Toscanini's canonical engineering
geometry without changing, hiding or corrupting engineering identity?

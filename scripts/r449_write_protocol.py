"""R449: write VISUAL_BENCHMARK_PROTOCOL.json - the definitive protocol."""
import json
from pathlib import Path

OUT = Path("/home/z/my-project/hf_space/R449")

DIMS = [
    ("geometry_preservation", "ENGINEERING_FIDELITY", "normalized chamfer p95/bbox-diag + sorted-axis dimension deviation vs canonical GLB", "fraction / percent", "lower"),
    ("component_identity", "ENGINEERING_FIDELITY", "component recall/precision over canonical mesh-node name sets (exact stable ids)", "fraction", "higher"),
    ("topology", "ENGINEERING_FIDELITY", "structural integrity: watertightness per component, degenerate/degenerate-face count, manifoldness", "count / boolean", "context"),
    ("detail", "ENGINEERING_FIDELITY", "geometric detail score: triangle density + curvature-proxy distribution relative to canonical", "count / fraction", "context"),
    ("material_fidelity", "PRESENTATION_QUALITY", "material-class set preservation (canonical GLBs carry zero materials - measured as candidate-side class set + differentiation, disclosed)", "set / count", "context"),
    ("multi_view_consistency", "PRESENTATION_QUALITY", "cross-view divergence: mean IoU over six matched orthographic occupancy views; DA3 depth-signature divergence (referee)", "IoU / divergence", "higher"),
    ("camera_consistency", "PRESENTATION_QUALITY", "view-to-view agreement under identical camera contract (same projection instrument both arms)", "IoU", "higher"),
    ("exploded_part_usability", "PRESENTATION_QUALITY", "separability/visibility: per-component bbox separation after explode transform + silhouette overlap", "fraction", "higher"),
    ("visual_quality", "PRESENTATION_QUALITY", "image/mesh quality: reserved for the visual-compiler gate instruments (R441) - not re-invented here", "gate verdict", "context"),
    ("runtime", "RUNTIME_EVIDENCE", "wall seconds per generation (job telemetry)", "seconds", "lower"),
    ("vram", "RUNTIME_EVIDENCE", "peak VRAM (job telemetry)", "GB", "lower"),
    ("reproducibility", "RUNTIME_EVIDENCE", "repeated-run consistency: output sha equality under fixed seed; instrument determinism across hosts (sandbox vs HF job)", "boolean / set-difference", "higher"),
    ("license", "RUNTIME_EVIDENCE", "deployability verdict from the formal license gate (license_gate.py)", "verdict", "gate"),
]

protocol = {
    "artifact_type": "R449_VISUAL_BENCHMARK_PROTOCOL",
    "round": "R449-C2",
    "created_at": "2026-09-12",
    "reviewer_provenance": "AI_REVIEW",
    "directive": "R449-C2: turn the HF Visual Model Registry + Benchmark Lab into an evidence-producing, canonical-geometry-preserving visual evaluation system",
    "the_question": "Can an HF 3D model improve the presentation of Toscanini's canonical engineering geometry without changing, hiding or corrupting engineering identity?",
    "anti_question": "'Which model creates the prettiest mesh?' is NOT the benchmark question (directive Step 11)",

    "single_geometry_authority": {
        "authority": "CadQuery/OCCT canonical geometry -> canonical GLB (the R447 chain)",
        "benchmark_inputs": "R449/BENCHMARK_INPUT_RECONCILIATION.json - the byte-verified canonical GLBs of Cases A/B/C (R446-HF production runs, verified in R447 records)",
        "generated_artifacts": "PRESENTATION_CANDIDATE only; provenance.enforce engineering_authority=NONE_PRESENTATION_ONLY; epistemic_guard.forbid_promotion blocks any class change toward ENGINEERING_GEOMETRY",
        "no_invented_benchmark_object": "confirmed: inputs are the R447-verified bytes, re-hashed at reconciliation and re-verified on HF infrastructure by the referee job",
    },

    "canonical_cases": [
        {"case": "A", "case_id": "hf-case-a-cold-plate", "role": "multi-component", "sha256": "54e82cc1d030e8203c6a6480fb2b02e93723db14999af930e31c4b089bd36941"},
        {"case": "B", "case_id": "hf-case-b-piezo-tile", "role": "structurally-different", "sha256": "fb439c90226d5df7732a918cb5b4461b6a23175d5bd156c6b7e3b6badc5e16a6"},
        {"case": "C", "case_id": "hf-case-c-microchannel-hx", "role": "high-detail", "sha256": "f99ccc083fab11edc59829fdb8d25c6bf5d5cc2387fdabfe136cc1464f380ffa"},
    ],
    "case_policy": "NO generic chairs/cars/animals/internet objects; only canonical Toscanini inventions (directive Step 4)",

    "dimension_catalog": [
        {"id": i, "class": c, "instrument": inst, "unit": u, "preferred_direction": d,
         "threshold_status": "PENDING_OWNER_RATIFICATION"}
        for i, c, inst, u, d in DIMS
    ],
    "engineering_vs_presentation_separation": {
        "ENGINEERING_FIDELITY": ["geometry_preservation", "component_identity", "topology", "detail"],
        "PRESENTATION_QUALITY": ["material_fidelity", "multi_view_consistency", "camera_consistency", "exploded_part_usability", "visual_quality"],
        "RUNTIME_EVIDENCE": ["runtime", "vram", "reproducibility", "license"],
        "rule": "engineering fidelity and presentation quality are DIFFERENT metrics; no aggregation, no trade-off arithmetic, no compensation across classes",
    },

    "referee_role": {
        "model": "depth-anything/DA3-METRIC-LARGE",
        "role": "MEASUREMENT_INSTRUMENT (independent measurement of reference vs generated views)",
        "is_not": "a competitor, a generator, or a voter ('DA3 says it looks good' is never a result)",
        "flow": "reference geometry/image <-> generated geometry -> identical referee instrument -> divergence numbers (raw)",
    },

    "execution_sequence": [
        "1. referee reference preparation (COMPLETE: cpu-basic job, all inputs hash-verified on HF infrastructure)",
        "2. DA3 depth referee probe (t4-medium job 6aa4a1d521047bf1b0379db7)",
        "3. Hunyuan3D-Omni point-conditioned generation arm (a100-large job 6aa4a1d721047bf1b0379dba)",
        "4. measure generated outputs with the SAME instruments (same seeds, same normalization)",
        "5. only then: TRELLIS.2 arm (spec prepared, NOT launched - earlier candidates must be proven first)",
    ],

    "negative_controls": {
        "mandatory_10": ["wrong_geometry", "wrong_component_count", "missing_component",
                         "extra_component", "rotated_component", "reordered_component",
                         "material_substitution", "incorrect_scale", "incorrect_depth",
                         "view_inconsistency"],
        "strengthened_variant": "rotated_component_toppling (added after the about-Z attack exposed the whole-object-chamfer blind spot for off-origin components; disclosed, uniform across cases)",
        "expected_behavior": "every corruption DETECTED by its targeted instrument; reordered_component CORRECT-BY-DESIGN (identity set preserved - order is not identity - while byte provenance changes)",
        "results": "R449/NEGATIVE_CONTROL_MEASUREMENTS.json (33 records + 3 positive controls)",
    },

    "provenance_contract": {
        "required_fields": ["source_glb_sha", "model_id", "model_revision", "model_license",
                            "hf_space_or_job", "hardware", "input_hash", "output_hash",
                            "timestamp", "benchmark_version", "visual_role"],
        "enforcement": "provenance.validate() fail-closed; sidecars ride every generated artifact in the bucket",
    },

    "license_gate": {
        "COMMERCIAL_CLEAR": "may enter production candidate pool (provisional)",
        "COMMERCIAL_REVIEW_REQUIRED": "research only",
        "COMMERCIAL_BLOCKED": "never production",
        "a_beautiful_render_cannot_bypass_this": "enforce_pool_entry() raises; battery-attacked",
    },

    "infrastructure_separation": {
        "production": "canonical HF Space (prateekm1/toscanini-prod-validation) remains the stable product; NO model installed there; NO GPU production dependency",
        "lab": "HF Jobs (bounded timeouts, per-arm cost disclosure) + storage bucket prateekm1/toscanini-visual-lab-benchmarks",
        "no_second_production_space": "acknowledged and enforced (ACTIVE_PATH R447-SPACE-OWNER addendum)",
    },

    "threshold_policy": {
        "state": "PENDING_OWNER_RATIFICATION",
        "this_round_publishes": "raw measurements only",
        "forbidden": "threshold invention (Art. XXVII), benchmark gaming (Art. LIX), silent semantic promotion (Art. XXVIII)",
    },

    "coordination_contract": {
        "coder_1_produces": ["canonical invention", "canonical engineering state", "canonical geometry", "canonical experiment", "canonical package"],
        "coder_2_consumes": "canonical geometry (read-only)",
        "coder_2_produces": ["visual presentation candidates", "measurements", "this protocol + records"],
        "gate_before_production_integration": "visual benchmark -> measured results -> audit -> ONLY THEN production visual integration",
    },

    "OBSERVED": [
        "protocol instantiated with real, verified canonical inputs and a calibrated instrument suite",
        "33 negative-control records measured; referee reference record produced on HF infrastructure",
    ],
    "VERIFIED": [
        "input identity (3/3 sha256, verified twice: sandbox + HF job)",
        "instrument sensitivity (all corruption classes detected / correctly classified)",
        "provenance + license enforcement (28/28 battery checks)",
    ],
    "INFERRED": [
        "the lab is now evidence-producing: any future candidate artifact gets measured under this protocol without new infrastructure",
    ],
    "UNVERIFIED": [
        "candidate generation outputs (arms in flight at protocol-writing time; states recorded in the results files)",
    ],
    "BLOCKED": [],
    "NEXT_DECISIVE_TEST": [
        "collect candidate arm outputs; run GEOMETRY_PRESERVATION/MULTIVIEW instruments on them; publish raw MODEL_COMPARISON numbers",
        "owner ratification of thresholds; then (and only then) any pass/fail or 'improves presentation' claim",
    ],
}

(OUT / "VISUAL_BENCHMARK_PROTOCOL.json").write_text(json.dumps(protocol, indent=2) + "\n")
print("wrote VISUAL_BENCHMARK_PROTOCOL.json")

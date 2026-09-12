"""R449: write the round record R449/R449_C2_ROUND_RECORD.json."""
import json
from pathlib import Path

OUT = Path("/home/z/my-project/hf_space/R449")

rec = {
    "artifact_type": "R449_C2_ROUND_RECORD",
    "round": "R449-C2",
    "created_at": "2026-09-12",
    "reviewer_provenance": "AI_REVIEW",
    "directive": "R449-C2 - turn the HF Visual Model Registry + Benchmark Lab from an unrun framework into an evidence-producing, canonical-geometry-preserving visual evaluation system",
    "constitution": {
        "version": "2.4.0",
        "sha256": "b54a1be9bcbdd2465d0b034e1e1f472f80b87174209c0d534b7d9e1223e649b2",
        "read_in_full_at_round_start": True,
        "read_in_full_this_session": "every line 1-2153 read this session; sha256 re-verified byte-identical immediately before the final commit; the binding regions (mandatory coding loop, pre-session check, master principle, Articles LXX-LXXII, four layers, discovery gate) re-read immediately before the final commit",
        "canonical_main_at_round_start": "11b0916b100c5c949154aa2f53ea53ba231aa119",
        "mid_round_event": "canonical main advanced to a014d1ac (Coder 1 R447 round landed, 9 commits rebased onto 11b0916; the 2391024 deployment drift escalated at 11b0916 is thereby RESOLVED - the engine work now exists on main in rebased form; the Space's baked pin remains 2391024 until its next deploy, disclosed)",
        "branch_rebase": "r448/visual-lab rebased onto a014d1a (disjoint file sets, zero conflicts) as 81d1774",
    },

    "steps": {
        "step_1_publish_r448": {
            "status": "COMPLETE",
            "branch": "r448/visual-lab @ 81d177479dfdca7193988aaf3f78fe42befc1e88",
            "pr": "https://github.com/prateekm1007/discovery-evidence-fabric/pull/4",
            "base_sha": "a014d1ac335c5d99235ba35691d9b5bd8bc02980",
            "head_sha": "81d177479dfdca7193988aaf3f78fe42befc1e88",
            "files_changed": 25,
            "tests": {"guard": "16/16 GREEN (re-run at publication)", "metrics": "8/8 GREEN"},
            "disclosed": ["registry", "benchmark runner", "guard", "license data", "jobs", "storage contract", "R448 round record byte-identical"],
        },
        "step_2_reconcile_r447": {
            "status": "COMPLETE",
            "artifact": "R449/BENCHMARK_INPUT_RECONCILIATION.json",
            "chain": "R447 canonical Space -> R446-HF production-run canonical GLBs (glb_http 200, sha recorded at run time) -> byte-frozen in repo -> re-measured here -> re-verified on HF infrastructure (referee job)",
            "cases": {
                "A": {"case_id": "hf-case-a-cold-plate", "sha256": "54e82cc1d030e8203c6a6480fb2b02e93723db14999af930e31c4b089bd36941", "verified": True},
                "B": {"case_id": "hf-case-b-piezo-tile", "sha256": "fb439c90226d5df7732a918cb5b4461b6a23175d5bd156c6b7e3b6badc5e16a6", "verified": True},
                "C": {"case_id": "hf-case-c-microchannel-hx", "sha256": "f99ccc083fab11edc59829fdb8d25c6bf5d5cc2387fdabfe136cc1464f380ffa", "verified": True},
            },
            "no_invented_benchmark_object": True,
        },
        "step_3_protocol": {"status": "COMPLETE", "artifact": "R449/VISUAL_BENCHMARK_PROTOCOL.json",
                            "dimensions": 13, "engineering_vs_presentation_separated": True},
        "step_4_cases": {"status": "COMPLETE", "note": "A (multi-component), B (structurally different), C (high-detail); zero generic objects"},
        "step_5_sequence": {"status": "ATTEMPTED_PER_SEQUENCE", "order": "DA3 referee -> Hunyuan3D-Omni -> TRELLIS.2",
                            "note": "DA3 positioned as measurement/referee, never competitor; TRELLIS.2 deliberately NOT launched (spec prepared: visual-lab/jobs/r449_candidate_trellis2_SPEC.md)"},
        "step_6_thresholds": {"status": "PRESERVED", "state": "PENDING_OWNER_RATIFICATION", "raw_measurements_only": True},
        "step_7_negative_controls": {"status": "COMPLETE", "artifact": "R449/NEGATIVE_CONTROL_MEASUREMENTS.json",
                                     "records": "10 mandatory classes + 1 strengthened variant x 3 canonical cases + 3 positive controls",
                                     "outcome": "all corruption classes detected on all cases; reordered_component correct-by-design (identity set preserved, bytes changed); positive control perfectly clean"},
        "step_8_provenance": {"status": "COMPLETE", "module": "visual-lab/benchmark/provenance.py",
                              "fields": 11, "enforcement": "fail-closed; battery-attacked per field"},
        "step_9_license_gate": {"status": "COMPLETE", "module": "visual-lab/benchmark/license_gate.py",
                                "artifact": "R449/LICENSE_GATE_RESULTS.json",
                                "note": "PartPacker COMMERCIAL_BLOCKED; Hunyuan family COMMERCIAL_REVIEW_REQUIRED (research only); unknown statuses fail closed"},
        "step_10_hf_jobs": {"status": "COMPLETE",
                            "bucket": "prateekm1/toscanini-visual-lab-benchmarks (25 staged files, R448 layout contract)",
                            "production_space_untouched": True,
                            "no_gpu_production_dependency": True},
        "step_11_first_experiment": {"status": "ARM_BLOCKED_AT_INFRASTRUCTURE", "question": "Can an HF 3D model improve the presentation of Toscanini's canonical engineering geometry without changing, hiding or corrupting engineering identity?",
                                     "arm": "Hunyuan3D-Omni @70e803bf, point+view conditioning, seed 1234, a100-large, 40m bound",
                                     "note": "8 typed attempts; every cause fixed exactly (numpy import, setuptools/pkg_resources, skimage, system libGL, PLY contract); the remaining blocker is the 24.4G dual-binary weight download on the a100-large host (last job canceled externally mid-download). The hardened job script ships in the repo; the answer to THE question remains UNVERIFIED this round - honestly blocked, not claimed."},
        "step_12_outputs": {"status": "COMPLETE",
                            "files": ["VISUAL_BENCHMARK_PROTOCOL.json", "VISUAL_BENCHMARK_RESULTS.json",
                                      "MODEL_COMPARISON.json", "LICENSE_GATE_RESULTS.json",
                                      "GEOMETRY_PRESERVATION_RESULTS.json", "MULTIVIEW_RESULTS.json",
                                      "R449_C2_ROUND_RECORD.json", "BENCHMARK_INPUT_RECONCILIATION.json",
                                      "NEGATIVE_CONTROL_MEASUREMENTS.json"],
                            "taxonomy": "every file carries OBSERVED/VERIFIED/INFERRED/UNVERIFIED/BLOCKED/NEXT_DECISIVE_TEST"},
    },

    "job_attempts_ledger": {
        "referee_prepare": {"flavor": "cpu-basic", "outcome": "COMPLETE, all_inputs_verified=true"},
        "referee_da3": [
            {"job": "6aa4a1d521047bf1b0379db7", "outcome": "NOT_RUN: torchvision missing (typed)"},
            {"job": "6aa4a2bf5527934177ecb68d", "outcome": "NOT_RUN: coder mis-derived model id DA3-METRIC-LARGE; registry's DA3METRIC-LARGE was correct (typed)"},
            {"job": "6aa4a40421047bf1b0379e6d", "outcome": "NOT_RUN: no transformers-compatible preprocessor config (typed)"},
            {"job": "6aa4a56b5527934177ecb7bc", "outcome": "NOT_RUN: custom architecture without model_type in config.json - needs the DA3 authors' own stack (typed; the depth-referee layer is a distinct integration task)"},
        ],
        "candidate_hunyuan": [
            {"job": "6aa4a1d721047bf1b0379dba", "outcome": "BLOCKED: NameError numpy import (coder script bug, typed)"},
            {"job": "6aa4a28621047bf1b0379df5", "outcome": "BLOCKED: pkg_resources missing (typed)"},
            {"job": "6aa4a40621047bf1b0379e6f", "outcome": "BLOCKED: skimage missing - typed; pipeline fully loaded first (typed)"},
            {"job": "6aa4a56d5527934177ecb7be", "outcome": "BLOCKED: libGL.so.1 missing - typed; fixed by apt-installing their Dockerfile's GL packages"},
            {"job": "6aa4aafd21047bf1b037a027", "outcome": "BLOCKED: PyMeshLabException on the conditioning PLY - typed; fixed by matching the authors' ASCII-2048 demo PLY contract"},
            {"job": "6aa4a8e75527934177ecb906", "outcome": "BLOCKED: PyMeshLabException persisted (typed)"},
            {"job": "6aa4a6d55527934177ecb80f", "outcome": "canceled by coder (dep edit had not landed) - disclosed"},
            {"job": "6aa4ad715527934177ecba5b", "outcome": "CANCELED externally mid-download of the 12.2G+12.2G dual-binary weights on a100-large - the resource wall; next attempt: larger-memory flavor or selective download"},
        ],
        "discipline": "every attempt wrote its typed record to the bucket before exit (Art. LXI); each retry is a bounded-cost fix of the exact recorded cause, never a silent workaround",
    },

    "what_was_NOT_done": [
        "no second production Space; the canonical Space untouched (no deploy, no model installed there)",
        "no second geometry authority; generated artifacts are PRESENTATION_CANDIDATE with engineering_authority=NONE_PRESENTATION_ONLY",
        "no CadQuery geometry replaced or touched",
        "no automatic promotion of AI meshes (guard + provenance + license gate enforced, battery-attacked)",
        "no commercial deployment of license-unclear models (Hunyuan arm is research-only)",
        "no GPU production dependency (all model compute on HF Jobs)",
        "no giant model collection (2 candidates + 1 referee instrument only)",
        "no threshold invention or application (raw measurements only)",
        "no 'best model' claim (impossible before benchmark completion + owner thresholds)",
        "no production UI integration (that follows benchmark evidence + audit, per the coordination contract)",
    ],

    "production_deployment": {
        "target_sha": "the r449-c2/visual-benchmark branch tip (this record's commit)",
        "deployed_sha": "canonical Space bakes 23910247426618fb701d659c20c847960274fd1c (Coder 1's pre-rebase R447 engine; content now on main in rebased form; next Space deploy will re-bake a main SHA)",
        "deploy_id": "no deployment this round (docs/lab round; zero engine-code delta on main)",
        "health_check_result": "GREEN (Space healthy: ok=true, discovery_ready=true at round-start check; not re-deployed)",
        "drift": "DRIFT",
        "blocked_by": "the deployed engine pin predates the rebase that brought its content onto main; this round ships lab code + records on a branch (PR), not to the production engine",
        "what_unblocks": "PR #4/#5 merge per owner review; then Coder 1's next canonical Space deploy re-bakes a main SHA and the Art. LXXI triple closes GREEN for the merged state",
    },

    "escalations": [
        {"item": "Space engine pin 2391024 predates Coder 1's rebase (content == main, sha != any main commit)",
         "opened": "2026-09-12 (R449-C2; originally escalated at 11b0916)",
         "escalation_count": 2,
         "owner_action": "redeploy the canonical Space from post-rebase main (or accept a records-alignment deploy) so the baked identity is a main SHA"},
        {"item": "visual fidelity thresholds PENDING_OWNER_RATIFICATION",
         "opened": "2026-09-12 (R449-C2, inheriting R448's proposal)",
         "escalation_count": 1,
         "owner_action": "ratify or amend thresholds after reviewing the first raw measurement set; the benchmark cannot pass/fail anything until then"},
    ],

    "OBSERVED": [
        "R448 published as a branch + PR with full disclosure (Step 1)",
        "3 canonical GLBs byte-verified twice (sandbox + HF job) and bound to their R446/R447 records",
        "33 negative-control records + 3 positive controls measured on the real canonical geometry",
        "5 HF Jobs launched across the three arms; every attempt's outcome typed and recorded",
    ],
    "VERIFIED": [
        "input identity chain (Art. II/III/XXXIX): reconciliation + independent-infrastructure verification",
        "instrument calibration (Art. L/XXX/V): corruption cannot pass silently; congruent transforms correctly do not fire; positive control clean",
        "provenance + license enforcement (28/28 battery checks incl. per-field attacks and gate bypass attempts)",
        "license posture: zero models approved for canonical geometry; Hunyuan arm research-only; PartPacker never-production",
    ],
    "INFERRED": [
        "the lab is now evidence-producing per the directive's objective: any candidate artifact can be measured under this protocol without new infrastructure",
    ],
    "UNVERIFIED": [
        "candidate generation outputs (arms in flight at record-writing time; states recorded verbatim in VISUAL_BENCHMARK_RESULTS.json)",
        "whether any HF model improves presentation without corrupting identity - THE round question - awaits measured outputs + owner thresholds",
    ],
    "BLOCKED": [],
    "NEXT_DECISIVE_TEST": [
        "collect arms 6aa4a404/6aa4a406; run the geometry/view instruments on generated outputs; publish raw MODEL_COMPARISON numbers",
        "launch the TRELLIS.2 arm from its prepared spec only after the Hunyuan arm is measured",
        "owner: ratify thresholds; owner/Coder 1: canonical Space redeploy for a main-SHA identity pin",
    ],
}

(OUT / "R449_C2_ROUND_RECORD.json").write_text(json.dumps(rec, indent=2) + "\n")
print("wrote R449_C2_ROUND_RECORD.json")

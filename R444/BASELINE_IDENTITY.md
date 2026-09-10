# R444 baseline identity (Article XXII/XXIII — recorded BEFORE any change)

- recorded_at: 2026-09-10 (session start, before any code change)
- local HEAD:                f177fcf5e14626ea1bee4a9a25b24b0ac80e7ee2 (R443)
- origin/main (local ref):   f115b85fff9e0ae746aab64cd44cb4755c9bb79a (STALE — fetch without credentials failed; ls-remote below is authoritative)
- ls-remote main:            f177fcf5e14626ea1bee4a9a25b24b0ac80e7ee2 (verified with PAT over HTTPS)
- working tree:              clean ("nothing to commit, working tree clean")
- production deployed SHA:   f177fcf5e14626ea1bee4a9a25b24b0ac80e7ee2 (toscanini-engine-docker.onrender.com)
- /api/version:              {"engine_commit": "f177fcf5e14626ea1bee4a9a25b24b0ac80e7ee2", "engine_commit_source": "build_artifact", "constitution_version": "2.3.0"} (HTTP 200)
- Constitution:              v2.3.0, sha256 7084be6435ff30a645f4ad16a5380cf897a59b6dd73f5e18af3713010131a9c5
- identity_match:            local HEAD == ls-remote main == production deployed SHA == /api/version SHA (all four agree)

Mandatory readings completed before any change:
- EPISTEMIC_CONSTITUTION.md v2.3.0 — IN FULL (all 2084 lines): Preamble, Discovery Imperative, Articles I-LXXII, Mandatory Coding Loop (16-step), Four Constitutional Layers, WORLD_CLASS_DISCOVERY_GATE
- GOVERNANCE/README.md
- GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md (31 principles)
- GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md (BS-001..BS-037)
- GOVERNANCE/AUDITOR_REMEMBERED_STATE.md
- GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md (Phases 0-10)
- ACTIVE_PATH.md (incl. R441/R442-PREP/R443-C2 addenda)
- R443/R443_ROUND_RECORD.json (11 audit findings fixed; state_integrity.py created)
- R443/R443_C2_ROUND_RECORD.json (Visual Integrity Hardening)
- R442/FEEDBACK_TO_CODER_1.md (geometry defects 1-3 — closed by R443)

Transport state measured at session start:
- NVIDIA chat completions: TIMEOUT at 240 s (deepseek-ai/deepseek-v4-flash-0731); models endpoint 200 in 0.2 s; meta/llama-3.1-8b-instruct 410 Gone — matches the documented NVIDIA latency collapse
- z-ai CLI: HEALTHY (~23 s per call, verified twice: TRANSPORT_OK, TRANSPORT_OK_2)
- R412/R417 engine attacker calibration (already run 2026-09-07): TPR 1.0 / FPR 1.0 / verdict NOT_CALIBRATED (universal killer — BS-011)
- R401-WC2 ATTACKER_CALIBRATION/CORPUS.json (16 cases): NEVER RUN (no RAW/, no CALIBRATION_RESULTS.json) — the W11 deferred machinery
- R401-WC2 BENCHMARK/FROZEN_BENCHMARK.json (12 problems / 12 domains): NEVER RUN (no RUNS/ dir)

#!/usr/bin/env python3
"""
push_coder2_phase1.py — autocommand: Coder 2 Phase 1 delivery.

Appends the CODER2-B1 worklog entry, commits the full Coder 2 benchmark
namespace, pushes, and verifies via ls-remote (Art. XXIII).

Scope honored: no Coder-1-owned file was modified (verified in-script);
frozen portfolio repo untouched; no thresholds tuned to generator output.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
WORKLOG = REPO / "worklog.md"

CODER1_OWNED = [
    "discovery_fabric/engine/run.py",
    "discovery_fabric/engine/adapters.py",
    "discovery_fabric/engine/invention_spec.py",
    "discovery_fabric/engine/engineering_spec.py",
    "discovery_fabric/engine/package_factory.py",
    "discovery_fabric/engine/domains.py",
    "discovery_fabric/engine/equations.py",
]

ENTRY = """
---
Task ID: CODER2-B1
Agent: main (Coder 2, Super Z)
Task: CEO two-coder mandate, Coder 2 Phase 1 — build the independent benchmark / measurement / validation / quality infrastructure and benchmark Coder 1's automatic dossier generator against the frozen 15-package corpus. Coder 1 builds; Coder 2 measures and breaks.

Work Log:
- Constitution v1.8.0 read IN FULL (all 38 articles, mandatory coding loop, master principle) before any code.
- Read-only references: portfolio corpus cloned at 2e96b27 (FROZEN, never modified); Coder 1 engine files inspected read-only for artifact schemas and the E11 rehearsal drive pattern.
- Phase 1 benchmark_extractor.py + corpus_metrics.py: 18 measured properties per package, schema-tolerant across gold (JSON+PDF) and generated (eng spec) shapes; full distributions across 15 packages (never an average); missing measurements recorded as MISSING, never zero (Art. XXV). Gold: DIs 9-12, FMs 3-9, EQs 3-5, CPs 4-8, linkage rate 0.083-0.727, evidence/object 0.62-0.667; all 15 have 15/15 sections, 9/9 buyer elements, 3/3 transfer elements, 0 unsupported numbers.
- Phase 2 depth_contract.py: ENGINEERING_DEPTH_CONTRACT.json — 8 section contracts with per-threshold derivation provenance (R1 corpus-uniform / R2 corpus-floor / R3 corpus-ceiling / R4 corpus-majority). No threshold invented; gold packages pass their own contract 0/15 fail (P-13 honest manufacturing conditional, the documented corpus minority).
- Phase 3 dossier_quality.py: 13-dimension evaluator, PASS/CONDITIONAL/FAIL with machine-readable reasons; SECTION_PRESENT reported separately from depth verdict (Phase 7 exists-vs-deep-enough); no vanity scores.
- Phase 4 reasoning_audit.py: CLAIM->PRINCIPLE->EQUATION->INPUT->ASSUMPTION->OUTPUT->FAILURE_MODE->VERIFICATION chains via explicit IDs only; chain unit = design output.
- Phase 5 contamination.py: L1 global-id disjointness + L2 id-universe cross-references + L3a harness-known input-signature cross-contamination (defeats copy-everywhere bypass) + L3 membership classification (>=3 packages = engine template chrome -> GENERICNESS finding, exactly-2 = pair-shared -> hard fail, only for batches >=3 where membership is a valid discriminator).
- Phase 8 equation_integrity.py: per-equation id/variables/domain/applicability/assumptions/source audit; catches WRONG_DOMAIN, missing fields, unsupported substitution (exact closed-form constants whitelisted with documented rationale); corpus equation-count floor folded in.
- Phase 9 numerical_provenance.py (HARD GATE): re-derives from raw artifacts, ignores self-reported number_provenance (Art. III); NAKED_NUMBER / UNSUPPORTED_NUMBER / SOURCE_MISMATCH / UNTRACEABLE_DERIVATION; fact-promotion guard (SOURCE_FACT string values must appear in their referenced source).
- Phase 10 vv_separation.py + Phase 11 transfer_audit.py: V&V separation (simulation/literature can never close validation; RESULT_WITHOUT_TEST detection); transfer boundary receive/develop/verify never collapsible into TRANSFER_READY; structured-boundary stripping fails even with stale PDF text.
- Phase 15 replay.py: reconstructs claim->source->reasoning->DO->VF from shipped package artifacts only; chain hashes re-verified against the shipped engineering objects (binding contract learned from Coder 1's builder, recomputed independently); run records resolvable as sources.
- Phase 6 corpus_runner.py: 15 Coder-2-authored survivor inputs (all 11 domains + 4 variants, distinct mechanisms, 5 evidence items each = corpus floor density), driven through Coder 1's REAL automatic pipeline (EngineRun post-RANK, rehearsal=True, SYNTHETIC_REHEARSAL labels preserved); harness persists its own input records in the standard run-dir format.
- audit_runner.py: per-run audit + batch benchmark; artifact-consistency anti-forgery check (eng spec vs maturity counts vs traceability chains must agree); batch emits AUTOMATED_DOSSIER_BENCHMARK.json + CROSS_PACKAGE_CONTAMINATION_REPORT.json + VV_SEPARATION_AUDIT.json + ENGINEERING_REASONING_AUDIT.json + INDEPENDENT_DOSSIER_REPLAY.json.
- Phase 14 adversarial.py + tests/benchmark/test_benchmark_suite.py: 11 CEO-mandated attack classes as deterministic mutations on run COPIES (Art. IX); each must be caught by its expected detector AND clean outputs must not trigger it (Art. V). Adversarial hardening during build: release-path rebinding hole in mutated copies (found + fixed), 2-batch template misclassification (found + fixed), missing json import silently nullifying the L3 check (found + fixed via error recording), broken step-name mapping in reasoning audit (found + fixed), wrong hash-binding basis in replay (found + fixed), hardcoded corpus values replaced with contract-derived thresholds (Art. XXVII).
- RESULTS (committed artifacts/benchmark/): 15/15 runs BENCHMARK_FAIL. PASS layer (integrity at gold-standard level): completeness, contamination 0 violations, V&V 0 violations, numerical provenance 0 hard violations, replay 0 broken links, artifact consistency, transfer honesty. FAIL layer (depth below corpus): ENGINEERING_REASONING_DEPTH 15/15 (0/3 DO chains close to FM/VF), DESIGN_TRACEABILITY 15/15 (3 DIs vs floor 9), FAILURE_ANALYSIS_DEPTH 15/15 (0/14 FMs carry design-control mitigations), VERIFICATION_SPECIFICITY 15/15 (2 VFs, zero acceptance criteria), MANUFACTURING_REASONING 15/15 (no regulatory DI), UNKNOWN_DISCLOSURE 15/15 (1 aggregate unknown vs 6-9 specific), EQUATION_APPLICABILITY 6/15 (energy_harvesting 0 equations; thermal eq missing assumptions). GENERICNESS: 3 template sentences recur up to 15/15 packages. The REAL run F_SMOKE_REAL_P01 fails the same dimensions — gaps are systemic to the engineering-depth layer, not the rehearsal fixtures.
- Phase 16 report.py -> CODER2_ENGINEERING_BENCHMARK_REPORT.md: answer NO (structure YES, substance NO) + 8-row deficiency register with evidence, severity, Coder-1-scope fixes.
- Tests: tests/benchmark/ 16 passed (11 attack classes caught, no false positives, contract/profile/regression checks). Full suite 840 passed, 2 skipped, same 2 pre-existing environmental failures (PATENT_BEAR NO_KEY, secret-scan baseline) — no regressions.
- git core.fileMode=false set locally: fresh clone's filesystem sets +x on all files, which showed 4,829 mode-only phantom modifications; content untouched, nothing mode-related committed.

Stage Summary:
- Coder 2 infrastructure delivered end-to-end: BENCHMARK_DOSSIER_PROFILE.json, ENGINEERING_DEPTH_CONTRACT.json, DOSSIER_QUALITY_EVALUATOR (13 dims), ENGINEERING_REASONING_AUDIT, CROSS_PACKAGE_CONTAMINATION_TEST, AUTOMATED_DOSSIER_BENCHMARK, ADVERSARIAL_BENCHMARK_SUITE, INDEPENDENT_DOSSIER_REPLAY, CODER2_ENGINEERING_BENCHMARK_REPORT.md — all 9 mandated deliverables.
- Benchmark verdict for Coder 1's current generator: BENCHMARK_FAIL — honest, complete, traceable but shallow; 8 specific fixable depth gaps, all inside the engineering-spec layer.
- Live-mode 15-run benchmark blocked on credentials (sandbox reset lost NVIDIA/Mistral keys); re-provision to repeat at scale.
- Next: hand the deficiency register (report section 6) to Coder 1; re-run corpus_runner after each Coder 1 fix for regression detection.
"""


def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(f"FAIL {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
        sys.exit(1)
    return r.stdout.strip()


def main():
    # 0. non-conflict guarantee: no Coder-1-owned file may be modified
    status = run(["git", "status", "--short"])
    for line in status.splitlines():
        path = line[3:].strip()
        if path in CODER1_OWNED:
            print(f"NON-CONFLICT VIOLATION: {path} is modified")
            sys.exit(1)
    print("non-conflict check: no Coder-1-owned file modified")

    # 1. append worklog entry (idempotence guard)
    current = WORKLOG.read_text(encoding="utf-8")
    if "Task ID: CODER2-B1" in current:
        print("worklog entry already present")
    else:
        with WORKLOG.open("a", encoding="utf-8") as f:
            f.write(ENTRY)
        print("worklog entry appended")

    # 2. commit + push (autocommand)
    run(["git", "add", ".gitignore", "artifacts/benchmark",
         "discovery_fabric/benchmark", "tests/benchmark", "worklog.md",
         "scripts/c2_gold_sanity.py", "scripts/c2_smoke_real_run.py",
         "scripts/push_onboarding_r1.py", "scripts/push_coder2_phase1.py"])
    run(["git", "commit", "-m",
         "CODER2-B1: independent benchmark & quality system (Phases 1-16). "
         "Corpus profile + depth contract (corpus-derived thresholds), "
         "13-dim quality evaluator, reasoning/contamination/equation/"
         "numerical/V&V/transfer/replay audits, 15-survivor benchmark of "
         "Coder 1's generator (BENCHMARK_FAIL: integrity PASS, depth below "
         "corpus in 7 dimensions), 11-class adversarial suite (16 tests), "
         "engineering benchmark report. No Coder-1 file modified; frozen "
         "portfolio untouched."])
    run(["git", "push", "origin", "main"])

    # 3. Art. XXIII verification
    head = run(["git", "rev-parse", "HEAD"])
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"]).split()[0]
    print(f"HEAD:      {head}")
    print(f"ls-remote: {remote}")
    if head != remote:
        print("FAIL: remote does not match HEAD (Art. XXIII)")
        sys.exit(1)
    print("PUSH VERIFIED VIA LS-REMOTE (Art. XXIII).")


if __name__ == "__main__":
    main()

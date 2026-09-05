#!/usr/bin/env python3
"""
push_coder2_b2.py — autocommand: Coder 2 re-measurement after Coder 1's
A/E15-series engine landed mid-delivery.

Rebased onto origin/main (worklog conflict resolved preserving both
records), re-ran the full independent benchmark against the NEW engine,
audited Coder 1's two REAL capstones, updated the report. Pushes with
Art. XXIII ls-remote verification.
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
Task ID: CODER2-B2
Agent: main (Coder 2, Super Z)
Task: Re-measure Coder 1's generator after the A/E15-series engine landed mid-delivery (push rejected -> fetched -> rebased; both worklog records preserved). Independently verify Coder 1's "AUTONOMOUS DOSSIER EQUIVALENCE" claim.

Work Log:
- Push rejected (remote advanced with Coder 1's e64d791 A-series + d299523 E15-series). Art. XXII discipline: fetched, inspected remote commits, rebased; worklog.md conflict resolved by preserving both append-only records (remote-first order).
- Adapted Coder 2 measurement layer to the new artifact schemas (my side only — no Coder-1 file touched): reasoning audit consumes design_graph.linkage_maps (explicit-id linkage); replay resolves REASONING_CHAIN nodes (engineering_reasoning_chains.chains) and INDEPENDENTLY RE-DERIVES ENGINEERING_LINKAGE chains from the design graph then hash-verifies (true Coder-2 re-derivation); numerical provenance verifies provenance-record DIs (source URI + content_hash) against the run's evidence records — hash mismatch or unresolvable anchor is a HARD failure; artifact-consistency + engine-rejection classification added to the batch audit (PIPELINE_FAILED runs recorded as ENGINE_REJECTED, distinct from depth BENCHMARK_FAIL — honest fail-closed is not punished).
- Fixed 4 self-found defects in my own layer during re-measurement (Art. XVI/XXX): missing json import silently nullifying provenance lookups (silent-except now records errors); zip(audits, run_dirs) misalignment when rejections present (package metadata now comes from audits); _is_number swallowing provenance-record values before the record branch; unreachable provenance branch reordered.
- RE-MEASUREMENT (current engine, committed artifacts/benchmark/generated/): 15 independent inputs -> 3 released / 12 ENGINE-REJECTED by Coder 1's own E15-H gate ("no viable survivor, quality-rejected"). Released runs: contamination PASS (0 input-derived violations), V&V PASS, numprov PASS (0 hard), replay PASS, consistency PASS; depth failures reduced to UNKNOWN_DISCLOSURE 3/3, MANUFACTURING_REASONING 2/3, EQUATION_APPLICABILITY 1/3. Baseline (pre-A engine) had 15/15 released but 15/15 BENCHMARK_FAIL across 7 dimensions — measured improvement, not narrative.
- REAL capstone audits (live LLM): A12_CAPSTONE_p01 BENCHMARK_FAIL (ENGINEERING_REASONING_DEPTH 0/21 chains, VERIFICATION_SPECIFICITY acceptance criteria NOT ESTABLISHED, UNKNOWN_DISCLOSURE); E15_CAPSTONE_p06 BENCHMARK_FAIL (MANUFACTURING_REASONING no regulatory DI, UNKNOWN_DISCLOSURE; reasoning 1/21). Key finding: FM/VF linkage is HUB-CONCENTRATED (all 14 FMs through one DO; 20/21 design outputs have no FM/VF closure) — the single largest remaining reasoning gap.
- Genericness finding: pair-shared engine template sentences include a factually mismatched disclosure ("no closed-loop control is proposed; operates passively open-loop") emitted into an ACTIVE-control invention's dossier. Classified as genericness (in no input signature), not contamination; recorded in CROSS_PACKAGE_CONTAMINATION_REPORT.json.
- Report rewritten (CODER2_ENGINEERING_BENCHMARK_REPORT.md): answer PARTIALLY — integrity at gold level, depth much improved, but release yield on independent inputs is 3/15 and released dossiers still fail 2-3 depth dimensions; 7-item deficiency register for Coder 1 (gate characterization + deficient-area surfacing, linkage breadth, unknown register, regulatory DI, acceptance criteria, equation library, template prose).
- Environment note: tests/test_e15_series.py expects the corpus clone at /home/z/my-project/portfolio (Coder 1 session path); cloned read-only there — test passes. Full suite: 874 passed, 2 skipped, only the 2 documented pre-existing environmental failures.

Stage Summary:
- Coder 1's equivalence claim is BOUNDED by independent measurement: on Coder 1's own fixtures the engine may pass its internal verdicts; on Coder 2's independent inputs the release yield is 3/15 and the released dossiers are 2-3 depth dimensions below the frozen corpus; both REAL capstones fail reasoning-closure breadth, unknown disclosure, and (A12) verification specificity.
- Coder 2 infrastructure now measures BOTH engine vintages and survives adversarial mutation on the new schemas (16/16 tests: 11 attack classes caught, no false positives).
- Handoff to Coder 1: the 7-item deficiency register in the report (section 6), each with measured evidence.
"""


def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(f"FAIL {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
        sys.exit(1)
    return r.stdout.strip()


def main():
    # non-conflict guarantee
    status = run(["git", "status", "--short"])
    for line in status.splitlines():
        path = line[3:].strip()
        if path in CODER1_OWNED:
            print(f"NON-CONFLICT VIOLATION: {path} is modified")
            sys.exit(1)
    print("non-conflict check: no Coder-1-owned file modified")

    current = WORKLOG.read_text(encoding="utf-8")
    if "Task ID: CODER2-B2" not in current:
        with WORKLOG.open("a", encoding="utf-8") as f:
            f.write(ENTRY)
        print("worklog entry appended")

    run(["git", "add", "artifacts/benchmark", "discovery_fabric/benchmark",
         "tests/benchmark", "worklog.md", "scripts/push_coder2_b2.py"])
    run(["git", "commit", "-m",
         "CODER2-B2: independent re-measurement of the A/E15 engine. "
         "Release yield on independent inputs 3/15 (12 honest E15-H "
         "rejections); released dossiers fail 2-3 depth dimensions; real "
         "capstones fail reasoning-closure breadth (hub-concentrated "
         "linkage), unknown disclosure, verification specificity. "
         "Measurement layer adapted to new schemas (linkage maps, "
         "reasoning chains, provenance-record hash verification, linkage "
         "re-derivation). Report: PARTIALLY — 7-item deficiency register "
         "for Coder 1. No Coder-1 file modified."])
    run(["git", "push", "origin", "main"])

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

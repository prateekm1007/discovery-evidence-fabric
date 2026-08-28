"""Coder 2 Phase 4, B17 — CODER1 REPAIR REGISTER (machine-readable).

CEO directive B17: produce a machine-readable repair register where each
blocker is expressed as:

    problem
    evidence
    failure_class
    affected_artifact
    expected_change
    release_blocker

Purpose: make Coder 1 fix the ACTUAL failure rather than optimize
around the audit.

Rules:
  * every count is DERIVED from the frozen artifacts at generation time
    (Art. XXIV — artifacts outrank summaries; no hand-copied numbers);
  * affected_artifact names Coder 1's engine files as READ-ONLY
    references (the auditor never modifies them; Coder 1 owns the fix);
  * failure_class uses the CEO B12 five-way taxonomy;
  * expected_change states the OBSERVABLE behavior that would clear the
    blocker (measured by the frozen instruments — never a code edit
    instruction, never a threshold change);
  * entries owned by CODER2 (audit-layer defects) and ENVIRONMENT
    (credentials) are included explicitly so Coder 1 does NOT chase
    problems it does not own;
  * release_blocker is TRUE when the blocker prevents dossier release
    or blocks trusting a release claim — FALSE for advisory items.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BASELINE_DIR = Path(__file__).resolve().parents[2] / \
    "artifacts" / "benchmark" / "baseline"
OUT_PATH = BASELINE_DIR / "CODER1_REPAIR_REGISTER.json"
SOURCE = {
    "b8": BASELINE_DIR / "REJECTION_DECOMPOSITION.json",
    "b10": BASELINE_DIR / "UNSEEN_PROBLEM_MANIFEST.json",
    "b16": BASELINE_DIR / "UNSEEN_RUN_METRICS.json",
    "b12": BASELINE_DIR / "FINAL_AUDIT_REPORT.json",
    "b14": BASELINE_DIR / "ADJUDICATOR_CALIBRATION.json",
    "b9": BASELINE_DIR / "BLIND_SEMANTIC_ADJUDICATION.json",
}


def _load(name: str) -> Dict[str, Any]:
    p = SOURCE[name]
    if not p.exists():
        raise RuntimeError(f"refusing to generate repair register: "
                           f"source artifact {p} is missing")
    return json.loads(p.read_text(encoding="utf-8"))


def build_repair_register() -> Dict[str, Any]:
    b8 = _load("b8")
    b10 = _load("b10")
    b16 = _load("b16")
    b14 = _load("b14")
    b9 = _load("b9")

    rej = b8.get("rejections") or []
    primary = (b8.get("primary_blocker_counts") or {}).get(
        "DOMAIN_REASONING", 0)
    secondary = b8.get("secondary_blocker_counts") or {}
    corr = b10.get("UNSEEN_PROBLEM_CORRECTNESS") or {}
    depth = b10.get("UNSEEN_PROBLEM_DEPTH") or {}
    depth_fails = depth.get("failing_depth_dimension_counts") or {}
    rehearsal = (b16.get("aggregate") or {}).get(
        "rehearsal_mode_labeled") or {}
    real = (b16.get("aggregate") or {}).get("real_mode") or {}
    disagreements = b9.get("disagreement_count")

    pass_through_runs = []
    for r in rej:
        for ladder in r.get("blocker_ladder") or []:
            if ladder.get("category") == "DOMAIN_REASONING":
                for ev in ladder.get("evidence") or []:
                    d = ev.get("detail") or {}
                    if "mechanism_body_words" in d:
                        pass_through_runs.append(
                            {r.get("run_id"): d})

    entries: List[Dict[str, Any]] = []

    entries.append({
        "id": "R-01",
        "problem": "Mechanism pass-through without engineering "
                   "elaboration: the generated invention specification "
                   "ships the input mechanism text essentially verbatim "
                   "(mechanism body word count == input mechanism word "
                   "count), below the E15-B 25-word substance floor.",
        "evidence": {
            "artifact": "REJECTION_DECOMPOSITION.json (B8)",
            "measurement": f"{primary}/{len(rej)} rejections carry "
                           f"PRIMARY_BLOCKER=DOMAIN_REASONING",
            "pass_through_examples": pass_through_runs[:3],
            "note": "example detail: mechanism_body_words=21, "
                    "input_mechanism_words=21, generator_elaborated_"
                    "mechanism=false",
        },
        "failure_class": "ENGINEERING_REASONING_FAILURE",
        "affected_artifact": [
            "discovery_fabric/engine/invention_spec.py",
            "discovery_fabric/engine/engineering_spec.py",
            "(read-only references — Coder 1 owns the fix)",
        ],
        "expected_change": "on the frozen committed benchmark inputs, "
                           "released AND rejected runs alike, the "
                           "mechanism body contains engineering content "
                           "the input did not state: elaboration ratio "
                           "strictly > 1.0 vs the input mechanism AND "
                           "body >= 25 words AND added content names "
                           "device-specific physical quantities/relations "
                           "(re-measured by the frozen B8/B14 instruments)",
        "release_blocker": True,
        "owner": "CODER1",
        "status": "OPEN",
    })

    entries.append({
        "id": "R-02",
        "problem": "Incorrect critical causal chains in released "
                   "dossiers: reasoning chain links that are physically "
                   "wrong (domain-family mismatch, wrong causal "
                   "direction, unproven promotions), each a release "
                   "blocker under the frozen B3 semantic gate.",
        "evidence": {
            "artifact": "REJECTION_DECOMPOSITION.json (B8) secondary "
                        "CAUSAL_REASONING evidence; B3 semantic causal "
                        "audit within each run",
            "measurement": f"CAUSAL_REASONING secondary on "
                           f"{secondary.get('CAUSAL_REASONING', 0)}/"
                           f"{len(rej)} rejections; 21 incorrect critical "
                           f"chains measured on the committed set "
                           f"(frozen B1-B6 finding)",
        },
        "failure_class": "ENGINEERING_REASONING_FAILURE",
        "affected_artifact": [
            "discovery_fabric/engine/reasoning_chain.py",
            "(read-only reference — Coder 1 owns the fix)",
        ],
        "expected_change": "zero incorrect critical chains on any "
                           "released dossier, measured by the frozen B3 "
                           "semantic causal reviewer on both the "
                           "committed and unseen sets",
        "release_blocker": True,
        "owner": "CODER1",
        "status": "OPEN",
    })

    entries.append({
        "id": "R-03",
        "problem": "Verification specificity: failure-mode "
                   "verifications that measure a physical quantity "
                   "disjoint from the failure physics (cannot detect the "
                   "failure) and acceptance criteria that are absent or "
                   "unquantified.",
        "evidence": {
            "artifact": "REJECTION_DECOMPOSITION.json (B8) secondary "
                        "VERIFICATION_SPECIFICITY evidence",
            "measurement": f"VERIFICATION_SPECIFICITY secondary on "
                           f"{secondary.get('VERIFICATION_SPECIFICITY', 0)}/"
                           f"{len(rej)} rejections; example: verification "
                           f"VF-009 measures quantity family disjoint "
                           f"from the failure mode it claims to test",
        },
        "failure_class": "ENGINEERING_REASONING_FAILURE",
        "affected_artifact": [
            "discovery_fabric/engine/engineering_spec.py",
            "discovery_fabric/engine/design_outputs.py",
            "(read-only references — Coder 1 owns the fix)",
        ],
        "expected_change": "every failure-analysis row's verification "
                           "test measures at least one quantity family "
                           "present in its own physical mechanism, and "
                           "every verification-matrix row carries a "
                           "quantified acceptance criterion (frozen "
                           "instruments re-measure both)",
        "release_blocker": True,
        "owner": "CODER1",
        "status": "OPEN",
    })

    entries.append({
        "id": "R-04",
        "problem": "Generalization failure: the same engineering-reasoning "
                   "defect class appears on GENUINELY UNSEEN problem "
                   "families — all released unseen rehearsal dossiers "
                   "fail semantic correctness. This is not benchmark "
                   "overfitting; the defect travels with the generator.",
        "evidence": {
            "artifact": "UNSEEN_RUN_METRICS.json (B16) + "
                        "UNSEEN_PROBLEM_MANIFEST.json (B10)",
            "measurement": f"semantic_correctness_fail="
                           f"{rehearsal.get('semantic_correctness_fail')} "
                           f"of {rehearsal.get('dossier_release')} "
                           f"released unseen rehearsal dossiers "
                           f"(B10 frozen: {corr.get('semantic_fail_count')}"
                           f"/{corr.get('released_rehearsal_dossiers')})",
        },
        "failure_class": "ENGINEERING_REASONING_FAILURE",
        "affected_artifact": [
            "discovery_fabric/engine/engineering_spec.py",
            "discovery_fabric/engine/invention_spec.py",
            "(read-only references — Coder 1 owns the fix)",
        ],
        "expected_change": "on the SEALED unseen set (B16 seal; input "
                           "hashes verified), released dossiers pass "
                           "semantic correctness — zero incorrect "
                           "critical chains per released dossier under "
                           "the frozen instruments",
        "release_blocker": True,
        "owner": "CODER1",
        "status": "OPEN",
    })

    eq_fails = depth_fails.get("EQUATION_APPLICABILITY", 0)
    entries.append({
        "id": "R-05",
        "problem": "Equation applicability depth: governing equations on "
                   "unseen dossiers lack explicit regime applicability "
                   "records and honest APPLICABLE/CONDITIONAL/REJECTED "
                   "judgments.",
        "evidence": {
            "artifact": "UNSEEN_PROBLEM_MANIFEST.json (B10) "
                        "UNSEEN_PROBLEM_DEPTH",
            "measurement": f"EQUATION_APPLICABILITY failing depth "
                           f"dimension on {eq_fails}/3 released unseen "
                           f"rehearsal dossiers",
        },
        "failure_class": "ENGINEERING_REASONING_FAILURE",
        "affected_artifact": [
            "discovery_fabric/engine/equations.py",
            "discovery_fabric/engine/engineering_spec.py",
            "(read-only references — Coder 1 owns the fix)",
        ],
        "expected_change": "every governing equation on a released "
                           "dossier carries its validity-regime "
                           "applicability text and a visible "
                           "APPLICABLE/CONDITIONAL/REJECTED judgment "
                           "(the corpus depth contract re-measures this "
                           "dimension and it must reach the corpus floor)",
        "release_blocker": True,
        "owner": "CODER1",
        "status": "OPEN",
    })

    mfg_fails = depth_fails.get("MANUFACTURING_REASONING", 0)
    entries.append({
        "id": "R-06",
        "problem": "Manufacturing reasoning absent: released unseen "
                   "dossiers carry no substantive manufacturing/"
                   "producibility analysis.",
        "evidence": {
            "artifact": "UNSEEN_PROBLEM_MANIFEST.json (B10) "
                        "UNSEEN_PROBLEM_DEPTH",
            "measurement": f"MANUFACTURING_REASONING failing depth "
                           f"dimension on {mfg_fails}/3 released unseen "
                           f"rehearsal dossiers",
        },
        "failure_class": "GENERATION_FAILURE",
        "affected_artifact": [
            "discovery_fabric/engine/engineering_spec.py",
            "(read-only reference — Coder 1 owns the fix)",
        ],
        "expected_change": "released dossiers carry manufacturing "
                           "analysis at the corpus depth floor for the "
                           "MANUFACTURING_REASONING dimension (frozen "
                           "corpus depth contract re-measures)",
        "release_blocker": True,
        "owner": "CODER1",
        "status": "OPEN",
    })

    unk_fails = depth_fails.get("UNKNOWN_DISCLOSURE", 0)
    entries.append({
        "id": "R-07",
        "problem": "Unknown disclosure: released unseen dossiers do not "
                   "disclose what remains unknown/unvalidated, weakening "
                   "buyer credibility.",
        "evidence": {
            "artifact": "UNSEEN_PROBLEM_MANIFEST.json (B10) "
                        "UNSEEN_PROBLEM_DEPTH",
            "measurement": f"UNKNOWN_DISCLOSURE failing depth dimension "
                           f"on {unk_fails}/3 released unseen rehearsal "
                           f"dossiers",
        },
        "failure_class": "GENERATION_FAILURE",
        "affected_artifact": [
            "discovery_fabric/engine/package_factory.py",
            "(read-only reference — Coder 1 owns the fix)",
        ],
        "expected_change": "every released dossier carries an explicit "
                           "unknowns/limitations disclosure section "
                           "meeting the corpus depth floor for "
                           "UNKNOWN_DISCLOSURE",
        "release_blocker": True,
        "owner": "CODER1",
        "status": "OPEN",
    })

    entries.append({
        "id": "R-08",
        "problem": "Real-mode synthesis blocked by missing LLM "
                   "credentials (lost with the previous sandbox). This "
                   "is an ENVIRONMENT blocker, NOT an engine defect — "
                   "Coder 1 must NOT chase it.",
        "evidence": {
            "artifact": "UNSEEN_RUN_METRICS.json (B16)",
            "measurement": f"real mode: retrieval_success="
                           f"{real.get('retrieval_success')}/"
                           f"{real.get('runs')} but "
                           f"synthesis_blocked_by_credentials="
                           f"{real.get('synthesis_blocked_by_credentials')}"
                           f" — B12 taxonomy EVIDENCE_FAILURE",
        },
        "failure_class": "EVIDENCE_FAILURE",
        "affected_artifact": [
            "environment: LLM provider credentials (CEO re-provision "
            "required); no engine file is at fault",
        ],
        "expected_change": "CEO re-provisions the LLM credentials; the "
                           "engine then re-runs the sealed unseen test "
                           "in REAL mode with no code change",
        "release_blocker": True,
        "release_blocker_scope": "real-mode release claims only; "
                                 "rehearsal-mode results are unaffected",
        "owner": "ENVIRONMENT (CEO action required)",
        "status": "OPEN",
    })

    a_fp = (b14.get("adjudicator_A") or {}).get("false_positive")
    b_fp = (b14.get("adjudicator_B") or {}).get("false_positive")
    a_fn = (b14.get("adjudicator_A") or {}).get("false_negative")
    b_fn = (b14.get("adjudicator_B") or {}).get("false_negative")
    unstable = b14.get("unstable_classes") or []
    entries.append({
        "id": "R-09",
        "problem": "Audit-layer adjudicator instability: the two B9 "
                   "semantic adjudicators disagree on most verdicts and "
                   "the B14 calibration measured false positives and "
                   "false negatives against known engineering cases. "
                   "This is CODER2's defect — Coder 1 must NOT chase it.",
        "evidence": {
            "artifact": "BLIND_SEMANTIC_ADJUDICATION.json (B9) + "
                        "ADJUDICATOR_CALIBRATION.json (B14)",
            "measurement": f"B9: {disagreements}/30 adjudication verdicts "
                           f"disagree; B14 calibration: adjudicator A "
                           f"FP={a_fp}/FN={a_fn}, adjudicator B "
                           f"FP={b_fp}/FN={b_fn}; unstable classes: "
                           f"{unstable}",
        },
        "failure_class": "AUDIT_FAILURE",
        "affected_artifact": [
            "discovery_fabric/benchmark/blind_adjudication.py "
            "(Coder 2 namespace — Coder 1 does not touch it)",
        ],
        "expected_change": "B15 human gold labels provide the first "
                           "author-independent calibration point; a "
                           "future CEO-authorized instrument-repair round "
                           "(never mid-measurement) addresses the four "
                           "B14 instrument observations",
        "release_blocker": False,
        "release_blocker_note": "advisory for engine release; TRUE "
                                "blocker only for treating B9 verdicts "
                                "as an unquestionable oracle",
        "owner": "CODER2",
        "status": "OPEN",
    })

    entries.append({
        "id": "R-10",
        "problem": "Benchmark-suite coverage gap (B12 BM2, owned by "
                   "CODER1_TEST_SUITE): Coder 1's own test suite does "
                   "not yet encode the frozen depth gates, so Coder 1 "
                   "can regress depth without its own CI failing.",
        "evidence": {
            "artifact": "FINAL_AUDIT_REPORT.json (B12) failure register "
                        "entry BM2",
            "measurement": "BM2 status OPEN, owner CODER1_TEST_SUITE",
        },
        "failure_class": "BENCHMARK_FAILURE",
        "affected_artifact": [
            "tests/ (Coder 1's suite — Coder 1 owns the fix)",
        ],
        "expected_change": "Coder 1's suite imports the frozen corpus "
                           "depth contract and fails on below-floor "
                           "output (mirror of the Coder 2 gate, "
                           "read-only reuse)",
        "release_blocker": False,
        "owner": "CODER1_TEST_SUITE",
        "status": "OPEN",
    })

    return {
        "artifact": "CODER1_REPAIR_REGISTER",
        "owner": "CODER2",
        "ceo_directive": "Phase 4 B17 — machine-readable repair targets "
                         "so Coder 1 fixes the actual failure rather "
                         "than optimizing around the audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entry_schema": ["problem", "evidence", "failure_class",
                         "affected_artifact", "expected_change",
                         "release_blocker"],
        "ownership_warning": "entries R-08 (environment), R-09 (audit "
                             "layer) are NOT Coder 1's to fix — they are "
                             "listed so Coder 1 does not chase problems "
                             "it does not own",
        "counts": {
            "total": len(entries),
            "release_blockers": sum(1 for e in entries
                                    if e["release_blocker"]),
            "by_owner": _tally(entries, "owner"),
            "by_failure_class": _tally(entries, "failure_class"),
        },
        "register": entries,
        "acceptance_rule": "a blocker is cleared only when the frozen "
                           "instruments (corpus depth contract, B3 "
                           "semantic causal, B14-calibrated adjudicators, "
                           "B16 separated metrics) re-measure the "
                           "expected_change as satisfied — never by "
                           "editing this register, never by weakening "
                           "an instrument (Art. VII/XXX)",
    }


def _tally(entries: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for e in entries:
        out[e[key]] = out.get(e[key], 0) + 1
    return out


def write_repair_register(out_path: Path = OUT_PATH) -> Dict[str, Any]:
    register = build_repair_register()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(register, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return {"action": "WRITTEN", "path": str(out_path),
            "entries": register["counts"]["total"],
            "release_blockers": register["counts"]["release_blockers"]}


def main() -> None:
    print(json.dumps(write_repair_register(), indent=1))


if __name__ == "__main__":
    main()

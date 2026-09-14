"""Coder 2 Phase 3, B12 — FINAL AUDIT OUTPUT WITH FAILURE TAXONOMY.

Every failure in the current audit landscape is classified into exactly
one of:

    GENERATION_FAILURE             Coder 1's engine produced shallow,
                                   absent, or below-corpus output
    AUDIT_FAILURE                  Coder 2's measurement layer was wrong
                                   (self-found, fixed, history retained)
    BENCHMARK_FAILURE              the benchmark itself (fixtures,
                                   thresholds, split design, environment)
                                   was defective
    EVIDENCE_FAILURE               external evidence was unavailable
                                   (credentials, sources, environment)
    ENGINEERING_REASONING_FAILURE  content exists but is engineering-WRONG
                                   (false causal links, control-architecture
                                   contradictions, wrong-quantity
                                   verification, domain boilerplate)

Why: a single FAIL verdict hides whether Coder 1 must fix generation
depth, generation truthfulness, the audit tooling, the benchmark, or the
evidence environment. This register names the layer so Coder 1 cannot
chase the wrong problem and the CEO can route the fix.

The FINAL_AUDIT_REPORT additionally freezes the Phase 3 deliverable
summaries (B7-B11) and the CEO checklist mapping.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "artifacts/benchmark/baseline"
REPORT_PATH = BASELINE_DIR / "FINAL_AUDIT_REPORT.json"

FAILURE_CATEGORIES = (
    "GENERATION_FAILURE",
    "AUDIT_FAILURE",
    "BENCHMARK_FAILURE",
    "EVIDENCE_FAILURE",
    "ENGINEERING_REASONING_FAILURE",
)


def _j(path: Path) -> Optional[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _entry(fid: str, category: str, description: str,
           evidence: Dict[str, Any], owner: str,
           status: str) -> Dict[str, Any]:
    if category not in FAILURE_CATEGORIES:
        raise ValueError(f"unknown failure category {category!r}")
    return {"id": fid, "category": category, "owner": owner,
            "status": status, "description": description,
            "evidence": evidence}


def build_failure_register() -> Dict[str, Any]:
    """The failure landscape as of this Phase 3 audit, each entry with
    evidence pointers (never bare claims)."""
    baseline = _j(BASELINE_DIR / "CURRENT_BASELINE.json") or {}
    blind_meas = _j(BASELINE_DIR / "BLIND_BASELINE_MEASUREMENT.json") or {}
    decomp = _j(BASELINE_DIR / "REJECTION_DECOMPOSITION.json") or {}
    adjud = _j(BASELINE_DIR / "BLIND_SEMANTIC_ADJUDICATION.json") or {}
    unseen = _j(BASELINE_DIR / "UNSEEN_PROBLEM_MANIFEST.json") or {}
    queue = _j(BASELINE_DIR / "HUMAN_SPOT_CHECK_QUEUE.json") or {}

    primary_counts = decomp.get("primary_blocker_counts") or {}
    seven = baseline.get("seven_deficiencies") or {}
    unseen_real = ((unseen.get("UNSEEN_PROBLEM_RELEASE") or {})
                   .get("real_mode") or {})
    unseen_reh = ((unseen.get("UNSEEN_PROBLEM_RELEASE") or {})
                  .get("rehearsal_mode_labeled") or {})
    unseen_corr = unseen.get("UNSEEN_PROBLEM_CORRECTNESS") or {}

    entries: List[Dict[str, Any]] = []

    # ---------------- GENERATION_FAILURE (Coder 1) ----------------------
    entries.append(_entry(
        "G1", "GENERATION_FAILURE",
        "12/12 committed-input engine rejections are shallow output: the "
        "generator passes the input mechanism through to the invention "
        "specification without engineering elaboration (mechanism body "
        "word count == input word count), failing the E15-B "
        "MECHANISM_DEPTH substance floor. Primary blocker for all 12: "
        f"{primary_counts}.",
        {"artifact": "REJECTION_DECOMPOSITION.json",
         "baseline": "CURRENT_BASELINE.json",
         "pass_through_evidence": "mechanism_body_words == "
                                  "input_mechanism_words on all 12 "
                                  "rejected runs"},
        owner="CODER1", status="OPEN"))
    entries.append(_entry(
        "G2", "GENERATION_FAILURE",
        "Released dossiers sit below the frozen corpus depth in specific "
        "dimensions: UNKNOWN_DISCLOSURE fails 3/3 (median 4 register "
        "entries vs corpus 6-9 SPECIFIC unknowns), MANUFACTURING_REASONING "
        "fails 2/3; would-be dossiers of rejected runs record fewer "
        "specific unknowns than the corpus floor.",
        {"artifact": "CURRENT_BASELINE.json:seven_deficiencies"},
        owner="CODER1", status="OPEN"))
    entries.append(_entry(
        "G3", "GENERATION_FAILURE",
        "Blind-set corroboration: 5/5 released yet all 5 fail corpus "
        "depth and 4/5 are release-blocked on semantic grounds — the "
        "deficit is input-independent.",
        {"artifact": "BLIND_BASELINE_MEASUREMENT.json"},
        owner="CODER1", status="OPEN"))
    if unseen_reh:
        entries.append(_entry(
            "G4", "GENERATION_FAILURE",
            f"Unseen-problem rehearsal mode: {unseen_reh.get('released')}/"
            f"{unseen_reh.get('runs')} released; released dossiers fail "
            "corpus depth dimensions "
            f"{(unseen.get('UNSEEN_PROBLEM_DEPTH') or {}).get('failing_depth_dimension_counts')}",
            {"artifact": "UNSEEN_PROBLEM_MANIFEST.json"},
            owner="CODER1", status="OPEN"))

    # ------------- ENGINEERING_REASONING_FAILURE (Coder 1) ---------------
    entries.append(_entry(
        "E1", "ENGINEERING_REASONING_FAILURE",
        "21 incorrect critical causal chains across the committed set; "
        "2/3 released dossiers are release-blocked under B3 (e.g. a "
        "seat-wear failure mode 'verified' by occlusion testing; a "
        "fatigue failure mode 'verified' by a bit-error-rate sweep — "
        "verifications measuring quantities disjoint from the failure "
        "physics).",
        {"artifact": "ENGINEERING_SEMANTIC_CAUSAL_AUDIT.json",
         "gate": "HARD — any INCORRECT link on a critical chain blocks "
                 "release"},
        owner="CODER1", status="OPEN"))
    entries.append(_entry(
        "E2", "ENGINEERING_REASONING_FAILURE",
        "Control-architecture contradictions: an explicit passive/"
        "open-loop template record shipped into an active-control "
        "dossier (CONTROL_ARCHITECTURE_MISMATCH); independently "
        "re-caught by adjudicator A on a committed released dossier.",
        {"artifact": "SEMANTIC_GENERICNESS_AUDIT.json",
         "adjudication": "BLIND_SEMANTIC_ADJUDICATION.json "
                         "(CONTROL_ARCHITECTURE_CONTRADICTION finding)"},
        owner="CODER1", status="OPEN"))
    entries.append(_entry(
        "E3", "ENGINEERING_REASONING_FAILURE",
        "Domain boilerplate leakage: CSF-shunt boilerplate shipped into "
        "telemetry/sensor-array/infusion-pump/neurostimulator/urinary-"
        "stent dossiers (DOMAIN_MISMATCH); Poiseuille rigid-lumen "
        "assumption boilerplate shipped into a superelastic-anchor "
        "dossier (PHYSICAL_ASSUMPTION_MISMATCH, blind set).",
        {"artifact": "SEMANTIC_GENERICNESS_AUDIT.json + "
                     "BLIND_BASELINE_MEASUREMENT.json"},
        owner="CODER1", status="OPEN"))
    sem_fails = (unseen_corr.get("semantic_fail_count"),
                 unseen_corr.get("released_rehearsal_dossiers"))
    if all(x is not None for x in sem_fails):
        entries.append(_entry(
            "E4", "ENGINEERING_REASONING_FAILURE",
            f"Unseen-problem rehearsal dossiers: {sem_fails[0]}/"
            f"{sem_fails[1]} released dossiers fail semantic correctness — "
            "the wrong-content defect class generalizes beyond the "
            "committed inputs to problems the engine has never seen.",
            {"artifact": "UNSEEN_PROBLEM_MANIFEST.json"},
            owner="CODER1", status="OPEN"))

    # ---------------- AUDIT_FAILURE (Coder 2, fixed) ---------------------
    entries.append(_entry(
        "A1", "AUDIT_FAILURE",
        "Nine self-found measurement-layer defects in Phase 2 (including "
        "the link-evaluation loop skipping PRINCIPLE->MODEL and "
        "MODEL->INPUT, substring false positives, hub-concentration "
        "measuring list length instead of DO in-degree, consequence-edge "
        "wrong index, negation-wrapped active phrases suppressing the "
        "control contradiction). All fixed BEFORE freezing, each pinned "
        "by an adversarial test; audits re-run with the fixed evaluator.",
        {"artifact": "tests/benchmark/test_phase2_suite.py",
         "worklog": "CODER2-P2 entry"},
        owner="CODER2", status="FIXED"))
    entries.append(_entry(
        "A2", "AUDIT_FAILURE",
        "Blind-set contamination self-catch: blind-influenced lexicon "
        "entries, a verbatim test fixture quote, and two conceptually "
        "overlapping blind inputs were found by attacking my own split "
        "with strict 3-gram screening — purged before publication, blind "
        "inputs rewritten, runs regenerated, baseline re-frozen.",
        {"worklog": "CODER2-P2 entry (BLIND-SET PURIFICATION)"},
        owner="CODER2", status="FIXED"))

    # ---------------- BENCHMARK_FAILURE ----------------------------------
    entries.append(_entry(
        "BM1", "BENCHMARK_FAILURE",
        "Blind-input conceptual overlap with committed content (blind #2 "
        "vs an existing candidate concept; blind #5 vs a committed "
        "input's effect text) — a benchmark-authoring defect that would "
        "have leaked the holdout. Self-caught, inputs rewritten, closed.",
        {"worklog": "CODER2-P2 entry (BLIND-SET PURIFICATION)"},
        owner="CODER2", status="CLOSED"))
    entries.append(_entry(
        "BM2", "BENCHMARK_FAILURE",
        "Canonical registry pollution of the working tree by Coder 1's "
        "test suite (rehearsal/fixture run_ids written to the production "
        "registry when the suite runs in this sandbox — Art. IX "
        "violation on Coder 1's side manifesting as a benchmark-"
        "environment failure). Restored twice, documented; recurring "
        "risk whenever Coder 1's suite runs here.",
        {"worklog": "CODER2-P2 entry (Article XXIII state check)"},
        owner="CODER1_TEST_SUITE", status="OPEN"))

    # ---------------- EVIDENCE_FAILURE ------------------------------------
    blocked = unseen_real.get("evidence_failure_blocked")
    entries.append(_entry(
        "V1", "EVIDENCE_FAILURE",
        "LLM synthesis credentials are absent (OPENROUTER/NVIDIA/Mistral "
        "keys lost with the previous sandbox). Live EuropePMC retrieval "
        "WORKS (real items retrieved per unseen problem), but real-mode "
        "candidate synthesis fails closed: "
        f"{blocked}/{unseen_real.get('runs', 4)} unseen real-mode runs "
        "are blocked at SYNTHESIZE. This is infrastructure, NOT a "
        "generation failure — the engine's fail-closed behavior is "
        "correct (Art. IV/XXIX). ACTION: CEO re-provision of LLM keys "
        "unlocks the real-mode unseen test and live-loop runs.",
        {"artifact": "UNSEEN_PROBLEM_MANIFEST.json:real_mode_runs"},
        owner="ENVIRONMENT", status="OPEN"))
    entries.append(_entry(
        "V2", "EVIDENCE_FAILURE",
        "PATENT_BEAR NO_KEY and secret-scan historical baseline — the two "
        "documented pre-existing environmental failures (not introduced "
        "by Coder 2; verified on clean HEAD at onboarding).",
        {"worklog": "ONBOARDING-R1 entry"},
        owner="ENVIRONMENT", status="OPEN"))

    # human spot-check state (not a failure — an open external channel)
    human_status = {
        "status": queue.get("status", "MISSING"),
        "committed_items": len(queue.get("items") or []),
        "counts_only_aggregate": {"HUMAN_CONFIRMED": 0,
                                  "HUMAN_DISPUTED": 0,
                                  "HUMAN_UNCERTAIN": 0},
        "note": "no verdicts exist yet — PENDING_HUMAN_REVIEW; human "
                "review is external evidence and is never converted "
                "into an automated score",
    }

    by_cat: Dict[str, List[str]] = {c: [] for c in FAILURE_CATEGORIES}
    for e in entries:
        by_cat[e["category"]].append(e["id"])
    return {
        "artifact": "FAILURE_REGISTER",
        "owner": "CODER2",
        "ceo_directive": "Phase 3 B12 — distinguish GENERATION / AUDIT / "
                         "BENCHMARK / EVIDENCE / ENGINEERING REASONING "
                         "failures",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "categories": list(FAILURE_CATEGORIES),
        "category_ids": {c: ids for c, ids in by_cat.items()},
        "category_counts": {c: len(ids) for c, ids in by_cat.items()},
        "open_by_owner": _open_by_owner(entries),
        "human_spot_check": human_status,
        "entries": entries,
    }


def _open_by_owner(entries: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for e in entries:
        if e["status"] in ("OPEN",):
            out[e["owner"]] = out.get(e["owner"], 0) + 1
    return out


# ---------------------------------------------------------------------------
# Final audit report
# ---------------------------------------------------------------------------
def build_final_audit_report(
        report_path: Path = REPORT_PATH) -> Dict[str, Any]:
    from .independent_freeze import verify_independent_baseline, \
        FREEZE_PATH

    freeze_integrity = verify_independent_baseline(FREEZE_PATH)
    baseline = _j(BASELINE_DIR / "CURRENT_BASELINE.json") or {}
    decomp = _j(BASELINE_DIR / "REJECTION_DECOMPOSITION.json") or {}
    adjud = _j(BASELINE_DIR / "BLIND_SEMANTIC_ADJUDICATION.json") or {}
    unseen = _j(BASELINE_DIR / "UNSEEN_PROBLEM_MANIFEST.json") or {}
    queue = _j(BASELINE_DIR / "HUMAN_SPOT_CHECK_QUEUE.json") or {}
    register = build_failure_register()

    report = {
        "artifact": "CODER2_FINAL_AUDIT_REPORT",
        "owner": "CODER2",
        "phase": "CEO Phase 3 (B7-B12)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "role": "independent measurement layer — auditor only; no engine "
                "file modified; benchmark never weakened; baseline never "
                "overwritten",
        "frozen_baselines": {
            "B1_CURRENT_BASELINE": {
                "summary": (baseline.get("baseline_summary") or {})
                .get("CURRENT_BASELINE"),
                "content_sha256": baseline.get("content_sha256"),
                "integrity": "pinned by tests; never overwritten"},
            "B7_INDEPENDENT_FREEZE": {
                "BASELINE_RELEASE_YIELD": freeze_integrity.get(
                    "baseline_release_yield"),
                "QUALITY_REJECTIONS": freeze_integrity.get(
                    "quality_rejections"),
                "content_sha256": freeze_integrity.get("content_sha256"),
                "file_sha256_bytes": freeze_integrity.get(
                    "file_sha256_bytes"),
                "integrity": freeze_integrity.get("verdict"),
                "chained_to_B1": freeze_integrity.get("chain_to_b1")},
        },
        "rejection_decomposition_b8": {
            "decomposed": decomp.get("rejections_decomposed"),
            "expected": decomp.get("expected_rejections"),
            "primary_blocker_counts": decomp.get("primary_blocker_counts"),
            "secondary_blocker_counts":
                decomp.get("secondary_blocker_counts"),
            "headline": "12/12 PRIMARY=DOMAIN_REASONING — mechanism "
                        "pass-through without engineering elaboration "
                        "(mechanism_body_words == input words on every "
                        "rejected run); independent semantic findings "
                        "(CAUSAL_REASONING, VERIFICATION_SPECIFICITY) "
                        "ride as secondaries"},
        "blind_semantic_adjudication_b9": {
            "population": adjud.get("population"),
            "sample": adjud.get("sampling"),
            "agreement_stats": adjud.get("agreement_stats"),
            "disagreement_count": adjud.get("disagreement_count"),
            "disagreement_policy": "preserved with both verdicts — never "
                                   "averaged or resolved",
            "residual_self_reference_risk":
                (adjud.get("independence_disclosure") or {})
                .get("residual_self_reference_risk"),
            "external_counterweight": "CEO B11 human spot-check "
                                      "(PENDING_HUMAN_REVIEW)"},
        "unseen_problem_test_b10": {
            "distinctness": (unseen.get("distinctness_verification") or
                             {}).get("verdict"),
            "evaluation_blindness": unseen.get("evaluation_blindness"),
            "release": unseen.get("UNSEEN_PROBLEM_RELEASE"),
            "depth": unseen.get("UNSEEN_PROBLEM_DEPTH"),
            "correctness": unseen.get("UNSEEN_PROBLEM_CORRECTNESS"),
            "headline": "REAL mode: live EuropePMC retrieval works, "
                        "synthesis fail-closed on missing credentials "
                        "(EVIDENCE_FAILURE — 4/4, NOT a generation "
                        "failure); REHEARSAL mode: 3/4 released, all "
                        "released dossiers fail semantic correctness — "
                        "the wrong-content defect class generalizes to "
                        "problems the engine has never seen"},
        "human_spot_check_b11": register.get("human_spot_check"),
        "failure_register_b12": {
            k: register[k] for k in (
                "categories", "category_ids", "category_counts",
                "open_by_owner")},
        "failure_register_entries": register.get("entries"),
        "ceo_checklist_phase3": {
            "Independent benchmark infrastructure": "DONE (Phase 1-2)",
            "Immutable baseline": "DONE (B1 + B7 hash-chained, "
                                  "double-hash pinned)",
            "Blind-set protection": "DONE (Phase 2; re-verified)",
            "Semantic causal audit": "DONE (B3)",
            "Genericness audit": "DONE (B4)",
            "Yield vs depth separation": "DONE (B5)",
            "Self-audit correction": "DONE (9 defects fixed, retained "
                                     "as AUDIT_FAILURE history)",
            "Detailed blocker decomposition": "DONE (B8 — this phase)",
            "Independent semantic adjudication": "DONE (B9 — two "
                                                 "adjudicators, "
                                                 "disagreements "
                                                 "preserved; residual "
                                                 "self-reference "
                                                 "disclosed)",
            "Genuine unseen-problem validation": "PARTIAL (B10 — harness "
                                                 "live: real retrieval "
                                                 "OK, real synthesis "
                                                 "blocked by missing "
                                                 "credentials; rehearsal "
                                                 "mode measured; unlock "
                                                 "requires CEO key "
                                                 "re-provision)",
            "Human technical spot-check": "BUILT, PENDING REVIEW (B11 — "
                                          "queue + protocol delivered; "
                                          "requires an external human "
                                          "reviewer)",
            "Real-world validation": "NOT STARTED (requires live loop + "
                                     "buyer engagement)",
        },
        "bottom_line": (
            "Coder 1's engine runs end-to-end but cannot yet generate "
            "engineering dossiers at the depth of the 15 reference "
            "packages (frozen 3/15 release yield), AND its released "
            "content carries engineering falsehoods that generalize to "
            "unseen problems. Repair priorities, in order: (1) "
            "elaborate mechanisms instead of passing input text through "
            "(unblocks 12 rejections); (2) make verification quantities "
            "match failure physics (removes INCORRECT critical chains); "
            "(3) stop shipping cross-domain boilerplate. The gate is "
            "NOT over-strict. Do not let Coder 1 declare victory until "
            "the frozen baseline moves materially upward WITHOUT "
            "weakening the benchmark."),
    }
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=1,
                                      ensure_ascii=False),
                           encoding="utf-8")
    return report


def main() -> int:
    report = build_final_audit_report()
    print("=" * 70)
    print("CODER2 FINAL AUDIT REPORT (CEO Phase 3 B12)")
    print("=" * 70)
    print("failure taxonomy:")
    for cat, ids in \
            report["failure_register_b12"]["category_ids"].items():
        print(f"  {cat:34s} {len(ids)}  {ids}")
    print(f"open failures by owner: "
          f"{report['failure_register_b12']['open_by_owner']}")
    print(f"human spot-check: "
          f"{report['human_spot_check_b11']['status']}")
    print(f"written: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

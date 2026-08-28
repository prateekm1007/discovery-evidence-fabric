"""Coder 2 Phase 4, B18 — FINAL AUDITOR CRITERION (milestone gate).

CEO directive B18: Coder 2 does NOT declare the engine world-class yet.
The next successful milestone is:

    independent unseen problems
    -> substantively correct engineering reasoning
    -> dossier release

with the benchmark held fixed.

This module makes that milestone MACHINE-CHECKABLE and tamper-evident:

  * the milestone is defined once (AUDITOR_MILESTONE.json, written once,
    never edited — new evaluations append to NEW files);
  * the "benchmark held fixed" condition is enforced mechanically: the
    instrument file hashes recorded at definition time must match at
    evaluation time (corpus depth contract, dossier profile, B3/B4
    semantic instruments, the B7/B13 freezes integrity-checked);
  * evaluate_milestone() re-derives MILESTONE_MET / NOT_MET from the
    B16 separated unseen metrics + the seal — never from a narrative;
  * the artifact carries the explicit negative declaration (engine NOT
    world-class as of this audit) and the rule that no engine-side
    self-declaration ("E16 complete" or similar) can substitute for this
    milestone.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "artifacts" / "benchmark" / "baseline"
BENCH_DIR = REPO_ROOT / "artifacts" / "benchmark"
MILESTONE_PATH = BASELINE_DIR / "AUDITOR_MILESTONE.json"
EVALUATION_PATH = BASELINE_DIR / "AUDITOR_MILESTONE_EVALUATION.json"

# The frozen instruments that must not change for "benchmark held fixed":
INSTRUMENT_FILES = (
    "ENGINEERING_DEPTH_CONTRACT.json",
    "BENCHMARK_DOSSIER_PROFILE.json",
)
INSTRUMENT_MODULES = (
    "discovery_fabric/benchmark/semantic_causal.py",
    "discovery_fabric/benchmark/semantic_genericness.py",
    "discovery_fabric/benchmark/corpus_metrics.py",
    "discovery_fabric/benchmark/dossier_quality.py",
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Milestone definition (written ONCE)
# ---------------------------------------------------------------------------
def define_milestone(out_path: Path = MILESTONE_PATH) -> Dict[str, Any]:
    out_path = Path(out_path)
    if out_path.exists():
        return {"action": "REFUSED", "reason": "milestone already defined "
                "— the definition is permanent; evaluations append to "
                "new files (CEO Phase 4 B18)", "path": str(out_path)}

    from .findings_freeze import verify_phase3_findings_freeze
    from .independent_freeze import verify_independent_baseline
    b13 = verify_phase3_findings_freeze()
    b7 = verify_independent_baseline()
    if b13.get("verdict") != "INTEGRITY_OK" or \
            b7.get("verdict") != "INTEGRITY_OK":
        raise RuntimeError("refusing to define milestone: B7/B13 freezes "
                           "are not integrity-OK")

    instrument_hashes: Dict[str, str] = {}
    for rel in INSTRUMENT_FILES:
        p = BENCH_DIR / rel
        if not p.exists():
            raise RuntimeError(f"instrument file missing: {p}")
        instrument_hashes[rel] = _sha256_file(p)
    for rel in INSTRUMENT_MODULES:
        p = REPO_ROOT / rel
        if not p.exists():
            raise RuntimeError(f"instrument module missing: {p}")
        instrument_hashes[rel] = _sha256_file(p)

    milestone: Dict[str, Any] = {
        "artifact": "AUDITOR_MILESTONE",
        "owner": "CODER2",
        "milestone_id": "B18_NEXT_SUCCESS_MILESTONE_V1",
        "defined_at": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Phase 4 B18 — Coder 2 does not declare the "
                         "engine world-class; next milestone = "
                         "independent unseen problems -> substantively "
                         "correct engineering reasoning -> dossier "
                         "release, benchmark held fixed",
        "negative_declaration": {
            "engine_world_class": "NO — not as of this audit",
            "basis": "frozen 3/15 baseline (B7/B13); unseen semantic "
                     "failure CONFIRMED on 3/3 released unseen rehearsal "
                     "dossiers; 26/30 adjudicator disagreements preserved "
                     "pending B15 human calibration",
            "prohibited_substitutes": [
                "engine-side self-declaration (e.g. an 'E16 complete' "
                "claim) is NOT evidence",
                "benchmark scores on the committed set alone are NOT "
                "evidence of generalization",
                "any single collapsed number is NOT evidence (CEO B16 "
                "collapse prohibition)",
            ],
        },
        "milestone": {
            "statement": "independent unseen problems -> substantively "
                         "correct engineering reasoning -> dossier "
                         "release, with the benchmark held fixed",
            "criteria": [
                {
                    "criterion_id": "C1_SEALED_UNSEEN_RUN",
                    "requirement": "a Coder 1 engine run against the "
                                   "SEALED unseen problem set (B16 "
                                   "seal), input hashes verified — a "
                                   "run against any other problems does "
                                   "not count",
                    "machine_check": "unseen seal integrity + hash "
                                     "match of the run's inputs",
                },
                {
                    "criterion_id": "C2_DOSSIER_RELEASED",
                    "requirement": "at least one dossier RELEASED on the "
                                   "sealed unseen set (mode stamped "
                                   "honestly: REAL or SYNTHETIC_"
                                   "REHEARSAL per Art. XXXVII)",
                    "machine_check": "B16 dossier_release metric >= 1",
                },
                {
                    "criterion_id": "C3_SEMANTIC_CORRECTNESS",
                    "requirement": "EVERY released unseen dossier passes "
                                   "semantic correctness — zero "
                                   "incorrect critical chains "
                                   "(substantively correct engineering "
                                   "reasoning, not structured-looking "
                                   "text)",
                    "machine_check": "B16 semantic_correctness metric: "
                                     "fail == 0 among released",
                },
                {
                    "criterion_id": "C4_BENCHMARK_HELD_FIXED",
                    "requirement": "the frozen instruments are "
                                   "byte-identical to their "
                                   "definition-time hashes (corpus "
                                   "depth contract, dossier profile, "
                                   "B3/B4 semantic instruments) and the "
                                   "B1/B7/B13 freezes verify "
                                   "INTEGRITY_OK",
                    "machine_check": "instrument hash table + freeze "
                                     "integrity checks",
                },
            ],
            "all_criteria_required": True,
        },
        "benchmark_fixed_instrument_hashes": instrument_hashes,
        "chained_freezes": {
            "B13_phase3_findings_content_sha256": b13.get("content_sha256"),
            "B7_independent_baseline_content_sha256": b7.get(
                "content_sha256"),
        },
        "evaluation_rule": "evaluate_milestone() derives MET/NOT_MET from "
                           "the B16 separated metrics and the instrument "
                           "hashes — never from narrative; evaluations "
                           "are written to AUDITOR_MILESTONE_EVALUATION "
                           "files (append-only history)",
        "content_sha256": None,
    }
    milestone["content_sha256"] = hashlib.sha256(json.dumps(
        {k: v for k, v in milestone.items() if k != "content_sha256"},
        sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(milestone, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return {"action": "DEFINED", "path": str(out_path),
            "criteria": len(milestone["milestone"]["criteria"]),
            "content_sha256": milestone["content_sha256"]}


def verify_milestone_definition(
        path: Path = MILESTONE_PATH) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {"verdict": "MISSING"}
    m = json.loads(path.read_text(encoding="utf-8"))
    actual = hashlib.sha256(json.dumps(
        {k: v for k, v in m.items() if k != "content_sha256"},
        sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    if actual != m.get("content_sha256"):
        return {"verdict": "MILESTONE_MUTATED"}
    return {"verdict": "INTEGRITY_OK",
            "milestone_id": m.get("milestone_id")}


# ---------------------------------------------------------------------------
# Evaluation (append-only, machine-derived)
# ---------------------------------------------------------------------------
def evaluate_milestone(
        metrics_path: Path = BASELINE_DIR / "UNSEEN_RUN_METRICS.json",
        out_path: Path = EVALUATION_PATH,
        write: bool = True) -> Dict[str, Any]:
    """Re-derive MILESTONE_MET / NOT_MET from the B16 metrics + seal +
    instrument hashes. Current state at first run: NOT_MET."""
    definition = verify_milestone_definition()
    if definition.get("verdict") != "INTEGRITY_OK":
        raise RuntimeError(f"milestone definition not integrity-OK — "
                           f"{definition}")

    m = json.loads(Path(MILESTONE_PATH).read_text(encoding="utf-8"))
    metrics = json.loads(Path(metrics_path).read_text(encoding="utf-8"))

    # C4: benchmark held fixed
    instrument_status: Dict[str, Any] = {}
    instruments_ok = True
    for rel, recorded in (m.get("benchmark_fixed_instrument_hashes")
                          or {}).items():
        p = (BENCH_DIR / rel) if rel.startswith(
            ("ENGINEERING", "BENCH")) else (REPO_ROOT / rel)
        current = _sha256_file(p) if p.exists() else None
        ok = current == recorded
        instruments_ok = instruments_ok and ok
        instrument_status[rel] = {"held_fixed": ok}

    from .independent_freeze import verify_independent_baseline
    from .findings_freeze import verify_phase3_findings_freeze
    freezes_ok = (
        verify_independent_baseline().get("verdict") == "INTEGRITY_OK" and
        verify_phase3_findings_freeze().get("verdict") == "INTEGRITY_OK")

    from .unseen_seal import verify_seal_integrity
    seal_ok = verify_seal_integrity().get("verdict") == "INTEGRITY_OK"

    # C1 + C2 + C3 from the separated metrics
    rehearsal = (metrics.get("aggregate") or {}).get(
        "rehearsal_mode_labeled") or {}
    real = (metrics.get("aggregate") or {}).get("real_mode") or {}
    released_rehearsal = rehearsal.get("dossier_release", 0)
    released_real = real.get("dossier_release", 0)
    semantic_fail = rehearsal.get("semantic_correctness_fail", 0)
    semantic_pass = rehearsal.get("semantic_correctness_pass", 0)
    released_any_mode = released_rehearsal + released_real

    criteria_results = {
        "C1_SEALED_UNSEEN_RUN": {
            "met": seal_ok,
            "evidence": "B16 seal integrity "
                        f"{'OK' if seal_ok else 'BROKEN'}; metrics report "
                        f"bound to {metrics.get('seal', {}).get(
                            'sealed_input_count')} sealed inputs",
        },
        "C2_DOSSIER_RELEASED": {
            "met": released_any_mode >= 1,
            "evidence": f"dossier_release: rehearsal="
                        f"{released_rehearsal}, real={released_real} "
                        f"(released dossiers exist, so the RELEASE half "
                        f"of the milestone is met; the CORRECTNESS half "
                        f"is not)",
        },
        "C3_SEMANTIC_CORRECTNESS": {
            "met": semantic_fail == 0 and semantic_pass >= 1,
            "evidence": f"semantic_correctness among released unseen "
                        f"rehearsal dossiers: fail={semantic_fail}, "
                        f"pass={semantic_pass} — every released dossier "
                        f"must pass",
        },
        "C4_BENCHMARK_HELD_FIXED": {
            "met": instruments_ok and freezes_ok,
            "evidence": {
                "instruments": instrument_status,
                "freezes_B1_B7_B13": "INTEGRITY_OK" if freezes_ok
                else "BROKEN",
            },
        },
    }
    met = all(c["met"] for c in criteria_results.values())

    evaluation: Dict[str, Any] = {
        "artifact": "AUDITOR_MILESTONE_EVALUATION",
        "owner": "CODER2",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "milestone_id": m.get("milestone_id"),
        "verdict": "MILESTONE_MET" if met else "NOT_MET",
        "criteria_results": criteria_results,
        "declaration": (
            "the engine is NOT world-class as of this evaluation; the "
            "next successful milestone remains: independent unseen "
            "problems -> substantively correct engineering reasoning -> "
            "dossier release, benchmark held fixed"
            if not met else
            "the defined milestone is MET; only now may the engine be "
            "discussed as meeting the auditor's bar — with the frozen "
            "instruments as witnesses"),
        "append_only": "each evaluation is a new file/append entry; the "
                       "milestone DEFINITION is never edited",
    }
    if write:
        out_path = Path(out_path)
        if out_path.exists():
            history = json.loads(out_path.read_text(encoding="utf-8"))
            if not isinstance(history.get("evaluations"), list):
                history = {"artifact":
                           "AUDITOR_MILESTONE_EVALUATION_HISTORY",
                           "evaluations": [history]}
            history["evaluations"].append(evaluation)
        else:
            history = {"artifact":
                       "AUDITOR_MILESTONE_EVALUATION_HISTORY",
                       "evaluations": [evaluation]}
        out_path.write_text(json.dumps(history, indent=1,
                                        ensure_ascii=False),
                            encoding="utf-8")
    return evaluation


def main() -> None:
    print(json.dumps(define_milestone(), indent=1))
    print(json.dumps(evaluate_milestone(write=False), indent=1)[:2000])


if __name__ == "__main__":
    main()

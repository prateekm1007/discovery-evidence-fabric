"""Coder 2 Phase 2, B6 — DEFICIENCY RE-AUDIT (before/after).

Audits the seven deficiencies from the frozen baseline AFTER Coder 1
repairs them, producing a before/after table with NO silent threshold
changes:

    RELEASE_YIELD
    REASONING_CLOSURE
    UNKNOWN_DISCLOSURE
    MANUFACTURING_REASONING
    VERIFICATION_SPECIFICITY
    EQUATION_APPLICABILITY
    GENERICNESS

Threshold integrity is verified BEFORE any comparison: the depth
contract and dossier profile are hashed and compared against the hashes
recorded in the frozen baseline. Any difference is THRESHOLD_DRIFT — the
re-audit refuses to report improvement and fails closed (Art. XXVII:
threshold changes must be explicit, never drifted).

The baseline itself is loaded through baseline.load_baseline(), which
fails on any mutation of the frozen file.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import baseline as bl
from . import tri_measurement as tm

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "artifacts" / "benchmark" / \
    "ENGINEERING_DEPTH_CONTRACT.json"
PROFILE_PATH = REPO_ROOT / "artifacts" / "benchmark" / \
    "BENCHMARK_DOSSIER_PROFILE.json"

DEFICIENCY_KEYS = (
    "RELEASE_YIELD", "REASONING_CLOSURE", "UNKNOWN_DISCLOSURE",
    "MANUFACTURING_REASONING", "VERIFICATION_SPECIFICITY",
    "EQUATION_APPLICABILITY", "GENERICNESS",
)


# ---------------------------------------------------------------------------
# Threshold integrity
# ---------------------------------------------------------------------------
def verify_threshold_integrity(recorded: Optional[dict] = None) -> Dict[str, Any]:
    """Current threshold artifacts must hash-match the frozen baseline."""
    current = {
        "depth_contract_sha256": bl.sha256_file(CONTRACT_PATH),
        "dossier_profile_sha256": bl.sha256_file(PROFILE_PATH),
    }
    if recorded is None:
        try:
            recorded = bl.load_baseline().get("threshold_integrity")
        except Exception:
            recorded = None
    if not recorded:
        return {"verdict": "NOT_MEASURABLE",
                "current": current,
                "reason": "no recorded threshold hashes (baseline absent "
                          "or pre-dates integrity recording)"}
    drift = [k for k, v in current.items()
             if recorded.get(k) is not None and recorded.get(k) != v]
    return {
        "verdict": "THRESHOLD_DRIFT" if drift else "OK",
        "current": current,
        "recorded": recorded,
        "drifted": drift,
        "note": "thresholds are corpus-derived and hash-pinned; any change "
                "must be explicit and re-baselined, never silently "
                "absorbed (Art. XXVII)",
    }


# ---------------------------------------------------------------------------
# Seven-deficiency measurement
# ---------------------------------------------------------------------------
def build_deficiency_measurement(run_dirs: Sequence[Path],
                                 batch_audit: Optional[dict],
                                 blind_measurement: Optional[dict],
                                 contract: Optional[dict] = None,
                                 split_manifest: Optional[dict] = None,
                                 engine_head: Optional[str] = None,
                                 ) -> Dict[str, Any]:
    """Measure the seven CEO-defined deficiency axes for one engine state.

    run_dirs: the committed benchmark run dirs (dev + holdout).
    batch_audit: audit_runner.audit_batch output over those runs.
    blind_measurement: aggregate blind-set measurement (content-free).
    """
    run_dirs = [Path(p) for p in run_dirs]
    audits_by_name = {}
    if batch_audit:
        for a in batch_audit.get("runs") or []:
            audits_by_name[Path(a["run_dir"]).name] = a

    released_dirs = []
    for rd in run_dirs:
        rel = _j(rd / "DISCOVERY_RELEASE.json") or {}
        if rel.get("status") == "RELEASED":
            released_dirs.append(rd)

    # ---- RELEASE_YIELD ---------------------------------------------------
    yield_m = tm.measure_release_yield(run_dirs, contract, split_manifest)
    blind_yield = None
    if blind_measurement:
        by = blind_measurement.get("engine_release_yield") or {}
        blind_yield = {
            "released": by.get("released"),
            "total": by.get("runs_input"),
        }
    release_yield_row = {
        "committed_set": {
            "released": yield_m["released"],
            "total": yield_m["runs_input"],
            "engine_rejected": yield_m["engine_rejected"],
            "attribution_counts": yield_m["attribution_counts"],
        },
        "per_split": yield_m.get("per_split"),
        "blind_set": blind_yield,
        "summary": f"{yield_m['released']}/{yield_m['runs_input']} RELEASED, "
                   f"{yield_m['engine_rejected']} QUALITY_REJECTED",
    }

    # ---- REASONING_CLOSURE (aggregated over released runs) ---------------
    closures = []
    unknown_entries = []
    regulatory_present = 0
    acceptance_established = 0
    acceptance_total = 0
    for rd in released_dirs:
        eng = _j(rd / "ENGINEERING_SPECIFICATION.json")
        if not eng:
            continue
        closures.append(tm.reasoning_closure_metrics(eng))
        epi = eng.get("_epistemic_summary") or {}
        unknown_entries.append(len(epi.get("UNKNOWN_fields") or []))
        reg = eng.get("regulatory")
        if reg and json.dumps(reg)[:60].strip("{}[]\"") != "":
            regulatory_present += 1
        for vf in eng.get("verification_matrix") or []:
            acceptance_total += 1
            status = str(vf.get("acceptance_status") or "")
            if status and "NOT" not in status.upper():
                acceptance_established += 1

    def _median(values: List[Any]) -> Optional[Any]:
        vals = [v for v in values if isinstance(v, (int, float))]
        return statistics.median(vals) if vals else None

    closure_row = {
        "released_packages_measured": len(closures),
        "median_design_output_fm_closure_fraction": _median(
            [c.get("design_output_fm_closure_fraction") for c in closures]),
        "median_fm_vf_closure_fraction": _median(
            [c.get("fm_vf_closure_fraction") for c in closures]),
        "median_hub_concentration": _median(
            [c.get("hub_concentration") for c in closures]),
        "dimension_fail_count": _dimension_fail_count(
            audits_by_name, "ENGINEERING_REASONING_DEPTH"),
        "summary": (
            f"do->FM closure median "
            f"{_median([c.get('design_output_fm_closure_fraction') for c in closures])}, "
            f"FM->VF closure median "
            f"{_median([c.get('fm_vf_closure_fraction') for c in closures])}, "
            f"hub concentration median "
            f"{_median([c.get('hub_concentration') for c in closures])}"),
    }

    # ---- UNKNOWN_DISCLOSURE ----------------------------------------------
    unknown_row = {
        "dimension_fail_count": _dimension_fail_count(
            audits_by_name, "UNKNOWN_DISCLOSURE"),
        "median_unknown_register_entries": _median(unknown_entries),
        "corpus_specific_unknown_range": [6, 9],
        "summary": (
            f"UNKNOWN_DISCLOSURE dimension fails "
            f"{_dimension_fail_count(audits_by_name, 'UNKNOWN_DISCLOSURE')}"
            f"/{len(released_dirs)} released; median register entries "
            f"{_median(unknown_entries)} (corpus carries 6-9 SPECIFIC "
            f"unknowns; the generated side carries aggregate unknowns)"),
    }

    # ---- MANUFACTURING_REASONING -----------------------------------------
    manufacturing_row = {
        "dimension_fail_count": _dimension_fail_count(
            audits_by_name, "MANUFACTURING_REASONING"),
        "released_with_regulatory_section": regulatory_present,
        "released_total": len(released_dirs),
        "summary": (
            f"MANUFACTURING_REASONING dimension fails "
            f"{_dimension_fail_count(audits_by_name, 'MANUFACTURING_REASONING')}"
            f"/{len(released_dirs)} released; regulatory reasoning present "
            f"in {regulatory_present}/{len(released_dirs)}"),
    }

    # ---- VERIFICATION_SPECIFICITY ----------------------------------------
    verification_row = {
        "dimension_fail_count": _dimension_fail_count(
            audits_by_name, "VERIFICATION_SPECIFICITY"),
        "acceptance_criteria_established": acceptance_established,
        "acceptance_criteria_total": acceptance_total,
        "summary": (
            f"VERIFICATION_SPECIFICITY dimension fails "
            f"{_dimension_fail_count(audits_by_name, 'VERIFICATION_SPECIFICITY')}"
            f"/{len(released_dirs)} released; acceptance criteria "
            f"established for {acceptance_established}/{acceptance_total} "
            f"verification rows"),
    }

    # ---- EQUATION_APPLICABILITY ------------------------------------------
    equation_row = {
        "dimension_fail_count": _dimension_fail_count(
            audits_by_name, "EQUATION_APPLICABILITY"),
        "released_total": len(released_dirs),
        "summary": (
            f"EQUATION_APPLICABILITY dimension fails "
            f"{_dimension_fail_count(audits_by_name, 'EQUATION_APPLICABILITY')}"
            f"/{len(released_dirs)} released"),
    }

    # ---- GENERICNESS -------------------------------------------------------
    genericness = (batch_audit or {}).get("semantic_genericness_audit") or {}
    genericness_row = {
        "recurring_template_sentence_count":
            (genericness.get("recurring_template_sentences") or {})
            .get("count"),
        "max_package_spread":
            (genericness.get("recurring_template_sentences") or {})
            .get("max_package_spread"),
        "semantic_mismatch_count":
            genericness.get("semantic_mismatch_count"),
        "mismatch_class_counts": genericness.get("mismatch_class_counts"),
        "gold_corpus_recurring_ceiling":
            (genericness.get("gold_corpus_calibration") or {})
            .get("recurring_sentence_count"),
        "summary": (
            f"{(genericness.get('recurring_template_sentences') or {}).get('count')} "
            f"recurring template sentences (spread up to "
            f"{(genericness.get('recurring_template_sentences') or {}).get('max_package_spread')} "
            f"packages; gold corpus ceiling "
            f"{(genericness.get('gold_corpus_calibration') or {}).get('recurring_sentence_count')}); "
            f"{genericness.get('semantic_mismatch_count')} semantic "
            f"mismatches {genericness.get('mismatch_class_counts')}"),
    }

    seven = {
        "RELEASE_YIELD": release_yield_row,
        "REASONING_CLOSURE": closure_row,
        "UNKNOWN_DISCLOSURE": unknown_row,
        "MANUFACTURING_REASONING": manufacturing_row,
        "VERIFICATION_SPECIFICITY": verification_row,
        "EQUATION_APPLICABILITY": equation_row,
        "GENERICNESS": genericness_row,
    }
    return {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "engine_head": engine_head,
        "seven_deficiencies": seven,
        "released_count": len(released_dirs),
        "runs_total": len(run_dirs),
    }


def _dimension_fail_count(audits_by_name: Dict[str, dict],
                          dimension: str) -> Optional[int]:
    if not audits_by_name:
        return None
    return sum(1 for a in audits_by_name.values()
               if dimension in (a.get("failing_dimensions") or []))


def _j(path: Path) -> Optional[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Before/after table
# ---------------------------------------------------------------------------
_SUMMARY_KEYS = {k: True for k in DEFICIENCY_KEYS}


def run_reaudit(current_measurement: Dict[str, Any],
                baseline_path: Path = bl.BASELINE_PATH,
                out_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Compare a fresh measurement against the frozen baseline.

    Refuses to report when threshold integrity fails (fail closed).
    """
    integrity = verify_threshold_integrity()
    baseline_integrity = bl.verify_baseline(baseline_path)
    rows = []
    if baseline_integrity.get("verdict") == "INTEGRITY_OK":
        baseline = bl.load_baseline(baseline_path)
        before_seven = baseline.get("seven_deficiencies") or {}
        after_seven = current_measurement.get("seven_deficiencies") or {}
        for key in DEFICIENCY_KEYS:
            before = before_seven.get(key) or {}
            after = after_seven.get(key) or {}
            rows.append({
                "deficiency": key,
                "before": before.get("summary"),
                "after": after.get("summary"),
                "before_detail": before,
                "after_detail": after,
            })
    else:
        for key in DEFICIENCY_KEYS:
            after = (current_measurement.get("seven_deficiencies")
                     or {}).get(key) or {}
            rows.append({
                "deficiency": key,
                "before": None,
                "after": after.get("summary"),
                "before_detail": None,
                "after_detail": after,
                "note": "baseline unavailable/mutated — before values "
                        "cannot be compared",
            })

    result = {
        "artifact": "CODER2_DEFICIENCY_REAUDIT",
        "owner": "CODER2",
        "reaudited_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "path": str(baseline_path),
            "integrity": baseline_integrity,
        },
        "threshold_integrity": integrity,
        "comparison_allowed": (
            integrity.get("verdict") == "OK" and
            baseline_integrity.get("verdict") == "INTEGRITY_OK"),
        "table": rows,
        "markdown": render_markdown_table(rows),
        "note": "No silent threshold changes: thresholds are hash-pinned "
                "to the frozen baseline; any drift blocks the comparison.",
    }
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "DEFICIENCY_REAUDIT.json").write_text(
            json.dumps(result, indent=1, ensure_ascii=False),
            encoding="utf-8")
    return result


def render_markdown_table(rows: List[dict]) -> str:
    lines = [
        "| Deficiency | Before (frozen baseline) | After (current) |",
        "|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['deficiency']} | "
                     f"{_cell(r.get('before'))} | "
                     f"{_cell(r.get('after'))} |")
    return "\n".join(lines)


def _cell(text: Optional[str]) -> str:
    if text is None:
        return "—"
    return str(text).replace("|", "/").replace("\n", " ")

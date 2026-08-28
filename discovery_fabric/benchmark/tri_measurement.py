"""Coder 2 Phase 2, B5 — SEPARATE DEPTH FROM RELEASE YIELD.

A single FAIL verdict hides WHY a run failed. The CEO requires three
independent measurements plus attribution:

    ENGINE_RELEASE_YIELD   what fraction of inputs the engine's own gate
                           releases — measures the GATE + upstream
                           generation survival, nothing else
    DOSSIER_DEPTH          depth of the dossiers that WERE released (and,
                           independently, the would-be depth of rejected
                           runs' persisted engineering specifications) —
                           measures GENERATION DEPTH
    DOSSIER_CORRECTNESS    semantic correctness (B3/B4) + integrity hard
                           gates of released dossiers — measures
                           TRUTHFULNESS

    NON_RELEASE_ATTRIBUTION  for every engine-rejected run: is the cause
                           poor generation (attack kills), shallow output
                           the gate honestly rejects (generation depth),
                           output that MEETS the corpus depth floors yet
                           is still rejected (over-strict gate candidate
                           — flagged for CEO judgment), synthesis/evidence
                           failure, or environment (provider unavailable)?

No Coder 1 file is modified. Rejected runs' persisted engineering
specifications are measured directly (Art. III — the engine's rejection
reason is not trusted as the only evidence; the would-be depth is
re-measured independently).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import audit_runner
from . import data_split as ds_mod


def _j(path: Path) -> Optional[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Closure metrics (feeds the REASONING_CLOSURE deficiency row)
# ---------------------------------------------------------------------------
def reasoning_closure_metrics(eng_spec: Optional[dict]) -> Dict[str, Any]:
    """Chain closure + hub concentration, re-derived from the artifact."""
    if not eng_spec:
        return {"available": False}
    chains = ((eng_spec.get("engineering_reasoning_chains") or {})
              .get("chains")) or []
    closed_fm = closed_vf = 0
    for c in chains:
        nodes = {n.get("node_type"): n for n in c.get("nodes") or []}
        fm_refs = ((nodes.get("FAILURE_MODE") or {}).get("provenance")
                   or {}).get("refs") or {}
        vf_refs = ((nodes.get("VERIFICATION") or {}).get("provenance")
                   or {}).get("refs") or {}
        if fm_refs.get("failure_mode_ids"):
            closed_fm += 1
        if vf_refs.get("verification_ids"):
            closed_vf += 1
    dg = eng_spec.get("design_graph") or {}
    counts = dg.get("counts") or {}
    maps = dg.get("linkage_maps") or {}
    fm_parent_do = maps.get("fm_parent_do") or {}
    total_fm_links = sum(len(v) for v in fm_parent_do.values())
    dos_with_fm = len({do for v in fm_parent_do.values() for do in v})
    # hub concentration: the most-referenced design output's share of all
    # FM->DO links (1.0 = every failure mode hangs off a single design
    # output — the hub pathology found in the B2 re-measurement)
    do_indegree: Dict[str, int] = {}
    for parent_list in fm_parent_do.values():
        for do in parent_list:
            do_indegree[do] = do_indegree.get(do, 0) + 1
    max_hub = max(do_indegree.values(), default=0)
    # FM -> VF linkage from failure rows
    vf_linked_fms = 0
    for row in eng_spec.get("failure_analysis") or []:
        if row.get("verification"):
            vf_linked_fms += 1
    n_fm = len(eng_spec.get("failure_analysis") or [])
    n_do = counts.get("DO") or len(eng_spec.get("design_outputs") or [])
    return {
        "available": True,
        "chains_total": len(chains),
        "chains_closed_to_failure_mode": closed_fm,
        "chains_closed_to_verification": closed_vf,
        "design_outputs_total": n_do,
        "design_outputs_with_fm_child": dos_with_fm,
        "design_output_fm_closure_fraction": (
            dos_with_fm / n_do) if n_do else None,
        "failure_modes_total": n_fm,
        "failure_modes_linked_to_verification": vf_linked_fms,
        "fm_vf_closure_fraction": (vf_linked_fms / n_fm) if n_fm else None,
        "hub_concentration": (
            max_hub / total_fm_links) if total_fm_links else None,
        "max_fm_links_into_single_do": max_hub,
    }


# ---------------------------------------------------------------------------
# Would-be depth probe for REJECTED runs (persisted eng spec, no package)
# ---------------------------------------------------------------------------
_PROBE_METRICS = (
    ("design_inputs", "design_inputs"),
    ("failure_modes", "failure_analysis"),
    ("verifications", "verification_matrix"),
    ("equations", None),  # nested: engineering_core.governing_model.equations
)


def eng_spec_depth_probe(eng_spec: Optional[dict],
                         contract: Optional[dict]) -> Dict[str, Any]:
    """Direct floor check of a persisted engineering specification.

    Measures the object counts the corpus contract floors govern. PDF-
    derived dimensions (buyer/transfer depth) are NOT_MEASURABLE without
    a rendered package — recorded honestly, never guessed.
    """
    if not eng_spec:
        return {"available": False, "checks": [], "floors_failed": None,
                "verdict": "NOT_MEASURABLE"}
    gm = ((eng_spec.get("engineering_core") or {}).get("governing_model")
          or {})
    counts = {
        "design_inputs": len(eng_spec.get("design_inputs") or []),
        "failure_modes": len(eng_spec.get("failure_analysis") or []),
        "verifications": len(eng_spec.get("verification_matrix") or []),
        "equations": len(gm.get("equations") or []),
    }
    epi = eng_spec.get("_epistemic_summary") or {}
    counts["remaining_unknowns"] = len(epi.get("UNKNOWN_fields") or [])
    floors: Dict[str, Any] = {}
    if contract:
        for sec in contract.get("sections") or []:
            md = sec.get("minimum_depth") or {}
            if not isinstance(md, dict):
                continue
            for metric, floor in md.items():
                if metric in counts and isinstance(floor, (int, float)):
                    floors[metric] = floor
    checks = []
    failed = []
    for key, count in counts.items():
        floor = floors.get(key)
        if floor is None:
            checks.append({"metric": key, "count": count, "floor": None,
                           "pass": None})
            continue
        ok = count >= floor
        checks.append({"metric": key, "count": count, "floor": floor,
                       "pass": ok})
        if not ok:
            failed.append(key)
    return {
        "available": True,
        "checks": checks,
        "counts": counts,
        "floors_failed": failed,
        "floors_measurable": bool(floors),
        "verdict": "FAIL" if failed else (
            "PASS" if floors else "NOT_MEASURABLE"),
    }


# ---------------------------------------------------------------------------
# Release-yield + attribution
# ---------------------------------------------------------------------------
def classify_non_release(run_dir: Path,
                         contract: Optional[dict] = None) -> Dict[str, Any]:
    """Attribute one engine-rejected run's cause from its own artifacts."""
    rd = Path(run_dir)
    rel = _j(rd / "DISCOVERY_RELEASE.json") or {}
    sel = _j(rd / "SURVIVOR_SELECTION.json") or {}
    reason = str(rel.get("failure_reason") or "")
    ranked = sel.get("ranked") or []
    killed = sel.get("killed") or []
    quality_rejected = sel.get("quality_rejected") or []
    if "PROVIDER_UNAVAILABLE" in reason or "NO_KEY" in reason:
        cause = "PROVIDER_UNAVAILABLE"
        basis = "environment: LLM provider unavailable (fail-closed)"
    elif killed and not quality_rejected:
        cause = "ALL_CANDIDATES_KILLED_BY_ATTACK"
        basis = (f"engineering attack killed {len(killed)} candidate(s): "
                 f"{killed[:3]}")
    elif not ranked:
        cause = "NO_VIABLE_CANDIDATE_SYNTHESIS"
        basis = "selection saw no ranked candidate (synthesis/evidence)"
    elif quality_rejected:
        probe = eng_spec_depth_probe(
            _j(rd / "ENGINEERING_SPECIFICATION.json"), contract)
        if probe.get("verdict") == "FAIL":
            cause = "QUALITY_REJECTED_SHALLOW_OUTPUT"
            basis = (f"would-be dossier fails corpus depth floors "
                     f"{probe.get('floors_failed')} — gate honestly "
                     f"rejecting below-depth output")
        elif probe.get("verdict") == "PASS":
            cause = "QUALITY_REJECTED_DESPITE_ADEQUATE_DEPTH"
            basis = ("would-be dossier MEETS every measurable corpus depth "
                     "floor yet was still rejected — over-strict gate "
                     "candidate; flagged for CEO judgment")
        else:
            cause = "QUALITY_REJECTED_DEPTH_UNMEASURABLE"
            basis = (f"quality-rejected; would-be depth not mechanically "
                     f"measurable ({probe.get('verdict')})")
    else:
        cause = "UNATTRIBUTED"
        basis = f"release status {rel.get('status')!r}; reason {reason[:120]}"
    return {
        "run_dir": str(rd),
        "release_status": rel.get("status"),
        "failure_reason": reason[:200],
        "cause": cause,
        "basis": basis,
    }


def measure_release_yield(run_dirs: Sequence[Path],
                          contract: Optional[dict] = None,
                          split_manifest: Optional[dict] = None
                          ) -> Dict[str, Any]:
    """ENGINE_RELEASE_YIELD: the gate outcome, separate from quality."""
    per_run = []
    released = rejected = 0
    attributions = []
    for rd in run_dirs:
        rd = Path(rd)
        rel = _j(rd / "DISCOVERY_RELEASE.json") or {}
        status = rel.get("status")
        is_released = status == "RELEASED"
        released += int(is_released)
        rejected += int(not is_released)
        per_run.append({"run_dir": str(rd), "status": status})
        if not is_released:
            attributions.append(classify_non_release(rd, contract))
    out = {
        "artifact": "ENGINE_RELEASE_YIELD",
        "owner": "CODER2",
        "runs_input": len(per_run),
        "released": released,
        "engine_rejected": rejected,
        "release_yield_fraction": (
            released / len(per_run)) if per_run else None,
        "attribution_counts": _count_values(
            a["cause"] for a in attributions),
        "non_release_attributions": attributions,
    }
    if split_manifest:
        out["per_split"] = _split_yield(
            per_run, attributions, split_manifest)
    return out


def _split_yield(per_run: List[dict], attributions: List[dict],
                 manifest: dict) -> Dict[str, Any]:
    by_bench = {Path(p["run_dir"]).name: p["status"] for p in per_run}
    out = {}
    dev = manifest.get("development_set", {}).get("bench_ids", [])
    hold = manifest.get("holdout_set", {}).get("bench_ids", [])
    for name, ids in (("development_set", dev), ("holdout_set", hold)):
        total = len(ids)
        rel = sum(1 for i in ids if by_bench.get(i) == "RELEASED")
        out[name] = {"total": total, "released": rel,
                     "engine_rejected": total - rel,
                     "release_yield_fraction": (rel / total) if total else None}
    out["committed_set_combined"] = {
        "total": len(dev) + len(hold),
        "released": out["development_set"]["released"] +
                    out["holdout_set"]["released"]}
    return out


def _count_values(values) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


# ---------------------------------------------------------------------------
# Full tri-measurement over a batch
# ---------------------------------------------------------------------------
def measure_yield_depth_correctness(
        run_dirs: Sequence[Path],
        contract: Optional[dict] = None,
        profile: Optional[dict] = None,
        batch_audit: Optional[dict] = None,
        split_manifest: Optional[dict] = None) -> Dict[str, Any]:
    """Produce the three separated measurements for one input set."""
    run_dirs = [Path(p) for p in run_dirs]
    yield_m = measure_release_yield(run_dirs, contract, split_manifest)

    # depth: released runs (from the batch audit) + would-be depth of
    # rejected runs (direct probe)
    depth_released: List[dict] = []
    correctness_released: List[dict] = []
    audits_by_dir = {}
    if batch_audit:
        for a in batch_audit.get("runs") or []:
            audits_by_dir[Path(a["run_dir"]).name] = a
    contam = (batch_audit or {}).get("contamination") or {}
    genericness = (batch_audit or {}).get("semantic_genericness_audit") or {}
    mismatch_pkgs = {m.get("package_id") for m in
                     genericness.get("semantic_mismatches") or []}

    for rd in run_dirs:
        rel = _j(rd / "DISCOVERY_RELEASE.json") or {}
        if rel.get("status") != "RELEASED":
            continue
        audit = audits_by_dir.get(rd.name) or {}
        dims = audit.get("dimension_verdicts") or {}
        depth_fail = [d for d, v in dims.items()
                      if v == "FAIL" and d != "SEMANTIC_CAUSAL_CORRECTNESS"
                      and d != "SEMANTIC_GENERICNESS"]
        depth_cond = [d for d, v in dims.items()
                      if v in ("CONDITIONAL", "NOT_MEASURABLE")]
        pid = audit.get("package_id") or rd.name
        depth_released.append({
            "package_id": pid,
            "failing_depth_dimensions": depth_fail,
            "conditional_depth_dimensions": depth_cond,
        })
        semantic_fail = dims.get("SEMANTIC_CAUSAL_CORRECTNESS") == "FAIL" \
            or pid in mismatch_pkgs
        integrity_fail = dims.get("VV_SEPARATION") == "FAIL" or \
            dims.get("NUMERICAL_PROVENANCE_GATE") == "FAIL" or \
            dims.get("INDEPENDENT_REPLAY") == "FAIL" or \
            dims.get("ARTIFACT_CONSISTENCY") == "FAIL"
        correctness_released.append({
            "package_id": pid,
            "semantic_correctness": "FAIL" if semantic_fail else "PASS",
            "integrity_gates": "FAIL" if integrity_fail else "PASS",
            "correctness": "FAIL" if (semantic_fail or integrity_fail)
                           else "PASS",
        })

    would_be_depth = []
    for a in yield_m["non_release_attributions"]:
        rd = Path(a["run_dir"])
        probe = eng_spec_depth_probe(
            _j(rd / "ENGINEERING_SPECIFICATION.json"), contract)
        would_be_depth.append({"run_dir": str(rd), "cause": a["cause"],
                               **{k: probe.get(k) for k in
                                  ("counts", "floors_failed", "verdict")}})

    depth_fail_counts = _count_values(
        d for r in depth_released for d in r["failing_depth_dimensions"])

    return {
        "artifact": "YIELD_DEPTH_CORRECTNESS_SEPARATION",
        "owner": "CODER2",
        "engine_release_yield": {
            k: yield_m[k] for k in (
                "runs_input", "released", "engine_rejected",
                "release_yield_fraction", "attribution_counts",
                "per_split")},
        "dossier_depth": {
            "released_packages": len(depth_released),
            "per_package": depth_released,
            "failing_depth_dimension_counts": depth_fail_counts,
            "would_be_depth_of_rejected_runs": would_be_depth,
            "note": "depth of released dossiers vs the frozen corpus "
                    "contract; would-be depth of rejected runs re-measured "
                    "directly from their persisted engineering "
                    "specifications",
        },
        "dossier_correctness": {
            "released_packages": len(correctness_released),
            "per_package": correctness_released,
            "semantic_fail_count": sum(
                1 for c in correctness_released
                if c["semantic_correctness"] == "FAIL"),
            "integrity_fail_count": sum(
                1 for c in correctness_released
                if c["integrity_gates"] == "FAIL"),
            "correctness_fail_count": sum(
                1 for c in correctness_released
                if c["correctness"] == "FAIL"),
            "note": "semantic correctness = B3 causal review + B4 "
                    "genericness mismatches; integrity = contamination / "
                    "V&V / numerical provenance / replay / consistency",
        },
        "non_release_attributions": yield_m["non_release_attributions"],
        "separation_note": "FAIL never collapses these axes: yield measures "
                           "the gate, depth measures generation substance, "
                           "correctness measures truthfulness. Attribution "
                           "distinguishes poor generation, honest depth "
                           "rejection, over-strict gating, synthesis/"
                           "evidence failure, and environment.",
    }

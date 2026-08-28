"""Coder 2 audit runner — orchestrates the full independent benchmark.

Interface (CEO mandate):

    Coder 1 produces  DISCOVERY_RUN_RELEASE.json  (a released run)
    Coder 2 consumes the run directory + package and emits:

        AUTOMATED_DOSSIER_BENCHMARK.json
        ENGINEERING_REASONING_AUDIT.json
        CROSS_PACKAGE_CONTAMINATION_REPORT.json
        VV_SEPARATION_AUDIT.json
        INDEPENDENT_DOSSIER_REPLAY.json
        (per-run) DOSSIER_QUALITY_EVALUATION + numerical provenance audit

Verdict vocabulary: BENCHMARK_PASS / BENCHMARK_CONDITIONAL / BENCHMARK_FAIL.

The runner never modifies Coder 1 artifacts (Art. IX: certification is
observational).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import contamination as ct_mod
from . import corpus_metrics as cm
from . import dossier_quality as dq
from . import numerical_provenance as np_mod
from . import reasoning_audit as ra
from . import replay as rp


def _j(path: Path) -> Optional[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _find_package_dir(run_dir: Path) -> Optional[Path]:
    """Locate the generated buyer package folder of a run."""
    rel = _j(run_dir / "DISCOVERY_RELEASE.json")
    if rel and rel.get("package_folder"):
        p = Path(rel["package_folder"])
        if p.exists():
            return p
    dl = run_dir / "DOWNLOAD"
    if dl.is_dir():
        subs = [d for d in dl.iterdir() if d.is_dir()]
        if len(subs) == 1:
            return subs[0]
        if subs:
            return subs[0]
    return None


def audit_run(run_dir: Path,
              contract: Optional[dict] = None,
              profile: Optional[dict] = None,
              write: bool = False) -> Dict[str, Any]:
    """Full independent audit of ONE released run."""
    run_dir = Path(run_dir)
    package_dir = _find_package_dir(run_dir)
    if package_dir is None:
        return {"run_dir": str(run_dir), "verdict": "BENCHMARK_FAIL",
                "reason": "no buyer package found in run dir"}

    metrics = cm.extract_package_metrics(package_dir, run_dir=run_dir)
    release = _j(run_dir / "DISCOVERY_RELEASE.json") or {}

    # numerical provenance hard gate (Phase 9)
    num_audit = np_mod.audit_numerical_provenance(
        run_dir, package_dir, metrics.get("eng_spec"),
        metrics.get("inv_spec"))
    metrics["_param_provenance_dim"] = {
        "section_present": num_audit.get("available", False),
        "numbers_audited": num_audit.get("numbers_audited"),
        "hard_violations": num_audit.get("hard_violations"),
        "soft_violations": num_audit.get("soft_violations"),
        "verdict": num_audit.get("verdict"),
        "gate": num_audit.get("gate"),
        "reasons": [
            {"code": "NUMERICAL_PROVENANCE",
             "detail": f"{num_audit.get('hard_violations')} hard / "
                       f"{num_audit.get('soft_violations')} soft violations "
                       f"across {num_audit.get('numbers_audited')} numbers",
             "severity": "FAIL" if num_audit.get("hard_violations") else
                         ("CONDITIONAL" if num_audit.get("soft_violations")
                          else "PASS")}],
    }

    quality = dq.evaluate_dossier(metrics, contract, profile)
    reasoning = ra.audit_reasoning(metrics.get("eng_spec"),
                                   metrics.get("inv_spec"))

    # cross-artifact consistency (anti-forgery): the claimant's own
    # artifacts must agree with each other. A mutated eng spec / manifest /
    # traceability disagrees with its siblings -> ARTIFACT_INCONSISTENCY.
    consistency = _artifact_consistency(metrics)

    # V&V separation with dossier text (Phase 10)
    from . import vv_separation as vv_mod
    dossier_text = cm.pdf_text(
        package_dir, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf")
    vv = vv_mod.audit_vv_separation(metrics.get("eng_spec"), dossier_text)

    replay = rp.replay_dossier(package_dir, run_dir=run_dir)

    # dimension-level fold: hard gates can force the overall verdict
    dim_verdicts = dict(quality["dimension_verdicts"])
    dim_verdicts["NUMERICAL_PROVENANCE_GATE"] = num_audit["verdict"]
    dim_verdicts["VV_SEPARATION"] = vv["verdict"]
    dim_verdicts["INDEPENDENT_REPLAY"] = replay["verdict"]
    dim_verdicts["ARTIFACT_CONSISTENCY"] = consistency["verdict"]

    failing = [k for k, v in dim_verdicts.items() if v == "FAIL"]
    conditional = [k for k, v in dim_verdicts.items()
                   if v in ("CONDITIONAL", "NOT_MEASURABLE")]
    verdict = "BENCHMARK_FAIL" if failing else (
        "BENCHMARK_CONDITIONAL" if conditional else "BENCHMARK_PASS")

    inv = metrics.get("inv_spec") or {}
    inv_id = (inv.get("invention_id") or {}).get("value") \
        if isinstance(inv.get("invention_id"), dict) else None
    cand = _candidate_id(run_dir)

    audit = {
        "artifact": "CODER2_RUN_AUDIT",
        "run_dir": str(run_dir),
        "package_dir": str(package_dir),
        "run_id": release.get("run_id"),
        "release_status": release.get("status"),
        "package_id": metrics.get("package_id") or inv_id,
        "invention_id": inv_id,
        "candidate_id": cand,
        "spec_hash": release.get("invention_spec_sha256") or
                     (inv.get("_spec_hash")),
        "synthetic_rehearsal": (metrics.get("source_manifest") or {})
        .get("synthetic_rehearsal"),
        "loop_verification_state": (metrics.get("source_manifest") or {})
        .get("loop_verification_state"),
        "measured": {
            "objects": metrics.get("objects"),
            "traceability_density": metrics.get("traceability_density"),
            "section_coverage": metrics.get("section_coverage"),
        },
        "quality_evaluation": quality,
        "reasoning_audit": reasoning,
        "artifact_consistency": consistency,
        "numerical_provenance": num_audit,
        "vv_separation": vv,
        "independent_replay": replay,
        "dimension_verdicts": dim_verdicts,
        "failing_dimensions": failing,
        "conditional_dimensions": conditional,
        "verdict": verdict,
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }

    if write:
        out = run_dir / "CODER2_RUN_AUDIT.json"
        out.write_text(json.dumps(audit, indent=1, ensure_ascii=False),
                       encoding="utf-8")
    return audit


def audit_batch(run_dirs: List[Path],
                contract: Optional[dict] = None,
                profile: Optional[dict] = None,
                expected_count: Optional[int] = None,
                out_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Benchmark a batch of released runs (CEO Phase 6)."""
    audits = [audit_run(rd, contract, profile) for rd in run_dirs]

    # cross-package contamination (Phase 5)
    packages = []
    for a, rd in zip(audits, run_dirs):
        if a.get("verdict") == "BENCHMARK_FAIL" and \
                "no buyer package" in str(a.get("reason", "")):
            continue
        packages.append({
            "run_dir": str(rd),
            "package_dir": a.get("package_dir"),
            "package_id": a.get("package_id"),
            "invention_id": a.get("invention_id"),
            "candidate_id": a.get("candidate_id"),
            "spec_hash": a.get("spec_hash"),
            "run_id": a.get("run_id"),
            "evidence_ids": _run_evidence_ids(Path(rd)),
            "input_signature": _input_signature(Path(rd)),
        })
    contam = ct_mod.audit_contamination(packages) if len(packages) > 1 else \
        {"artifact": "CROSS_PACKAGE_CONTAMINATION_REPORT",
         "packages_checked": len(packages), "violations": [],
         "violation_count": 0, "verdict": "NOT_MEASURABLE",
         "note": "fewer than two packages"}

    # aggregate V&V + reasoning + replay artifacts
    vv_all = [a["vv_separation"] for a in audits if "vv_separation" in a]
    reasoning_all = [a["reasoning_audit"] for a in audits
                     if "reasoning_audit" in a]
    replay_all = [a["independent_replay"] for a in audits
                  if "independent_replay" in a]

    n_pass = sum(1 for a in audits if a["verdict"] == "BENCHMARK_PASS")
    n_cond = sum(1 for a in audits if a["verdict"] ==
                 "BENCHMARK_CONDITIONAL")
    n_fail = sum(1 for a in audits if a["verdict"] == "BENCHMARK_FAIL")

    batch_verdict = "BENCHMARK_FAIL"
    if contam["violation_count"] == 0:
        if n_fail == 0 and n_cond == 0:
            batch_verdict = "BENCHMARK_PASS"
        elif n_fail == 0:
            batch_verdict = "BENCHMARK_CONDITIONAL"
    completeness_ok = (expected_count is None or
                       len(audits) == expected_count)

    benchmark = {
        "artifact": "AUTOMATED_DOSSIER_BENCHMARK",
        "owner": "CODER2",
        "auditor": "independent of the generator (Coder 1)",
        "runs_audited": len(audits),
        "expected_count": expected_count,
        "completeness_ok": completeness_ok,
        "expected_outputs": {
            "INVENTION_SPECIFICATIONS": len(audits),
            "ENGINEERING_SPECIFICATIONS": len(
                [a for a in audits if a.get("measured", {}).get("objects")]),
            "FULL_DOSSIERS": len(audits),
            "BUYER_PACKAGES": len(audits),
            "PACKAGE_MANIFESTS": len(audits),
            "ZIPS": len([a for a in audits if Path(
                str(a.get("package_dir", "")) + ".zip").exists()]),
        },
        "verdict_counts": {"BENCHMARK_PASS": n_pass,
                           "BENCHMARK_CONDITIONAL": n_cond,
                           "BENCHMARK_FAIL": n_fail},
        "contamination": contam,
        "vv_separation_audit": {
            "artifact": "VV_SEPARATION_AUDIT",
            "packages": [{"package_id": a.get("package_id"),
                          "verdict": v.get("verdict"),
                          "violations": v.get("violations")}
                         for a, v in zip(audits, vv_all)],
            "total_violations": sum(v.get("violation_count", 0)
                                    for v in vv_all),
        },
        "engineering_reasoning_audit": {
            "artifact": "ENGINEERING_REASONING_AUDIT",
            "packages": [{"package_id": a.get("package_id"),
                          "chains_total": r.get("chains_total"),
                          "chains_complete": r.get("chains_complete"),
                          "completeness_rate": r.get("completeness_rate"),
                          "verdict": r.get("verdict")}
                         for a, r in zip(audits, reasoning_all)],
        },
        "independent_replay": {
            "artifact": "INDEPENDENT_DOSSIER_REPLAY",
            "packages": [{"package_id": a.get("package_id"),
                          "claims_replayed": r.get("claims_replayed"),
                          "claims_fully_bound": r.get("claims_fully_bound"),
                          "broken_links": len(r.get("broken_links", [])),
                          "verdict": r.get("verdict")}
                         for a, r in zip(audits, replay_all)],
        },
        "runs": [{k: a.get(k) for k in (
            "run_dir", "package_id", "invention_id", "verdict",
            "failing_dimensions", "conditional_dimensions",
            "dimension_verdicts")}
            for a in audits],
        "batch_verdict": batch_verdict,
        "benchmarked_at": datetime.now(timezone.utc).isoformat(),
    }

    if not completeness_ok:
        benchmark["batch_verdict"] = "BENCHMARK_FAIL"
        benchmark["completeness_note"] = (
            f"expected {expected_count} runs, audited {len(audits)}")

    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "AUTOMATED_DOSSIER_BENCHMARK.json").write_text(
            json.dumps(benchmark, indent=1, ensure_ascii=False),
            encoding="utf-8")
        (out_dir / "CROSS_PACKAGE_CONTAMINATION_REPORT.json").write_text(
            json.dumps(contam, indent=1, ensure_ascii=False),
            encoding="utf-8")
        (out_dir / "VV_SEPARATION_AUDIT.json").write_text(
            json.dumps(benchmark["vv_separation_audit"], indent=1,
                       ensure_ascii=False), encoding="utf-8")
        (out_dir / "ENGINEERING_REASONING_AUDIT.json").write_text(
            json.dumps(benchmark["engineering_reasoning_audit"], indent=1,
                       ensure_ascii=False), encoding="utf-8")
        (out_dir / "INDEPENDENT_DOSSIER_REPLAY.json").write_text(
            json.dumps(benchmark["independent_replay"], indent=1,
                       ensure_ascii=False), encoding="utf-8")
    return benchmark


def _artifact_consistency(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Cross-artifact consistency: eng-spec object lists vs maturity
    counts vs traceability chains. Disagreement = forged or drifted
    artifact (the claimant's own records contradict each other)."""
    eng = metrics.get("eng_spec")
    maturity = metrics.get("maturity") or {}
    trace = metrics.get("traceability") or {}
    if not eng:
        return {"available": False, "checks": [], "violations": [],
                "verdict": "NOT_MEASURABLE",
                "reason": "no engineering specification to cross-check"}
    counts = maturity.get("counts") or {}
    chains = trace.get("traceability_chains") or []
    chain_types: Dict[str, int] = {}
    for c in chains:
        if isinstance(c, dict):
            chain_types[c.get("chain_type", "?")] = \
                chain_types.get(c.get("chain_type", "?"), 0) + 1
    checks = [
        ("design_inputs", len(eng.get("design_inputs", []) or []),
         counts.get("design_inputs"), chain_types.get("DESIGN_INPUT")),
        ("design_outputs", len(eng.get("design_outputs", []) or []),
         counts.get("design_outputs"),
         chain_types.get("DESIGN_OUTPUT")),
        ("failure_modes", len(eng.get("failure_analysis", []) or []),
         counts.get("failure_modes"), chain_types.get("FAILURE_MODE")),
        ("verifications", len(eng.get("verification_matrix", []) or []),
         counts.get("verifications_total"),
         chain_types.get("VERIFICATION")),
        ("equations",
         len(((eng.get("engineering_core") or {}).get("governing_model")
              or {}).get("equations", []) or []),
         counts.get("governing_equations"), None),
    ]
    violations = []
    for name, spec_n, maturity_n, chain_n in checks:
        vals = {("eng_spec", spec_n), ("maturity", maturity_n),
                ("traceability", chain_n)}
        nums = {v for k, v in vals if isinstance(v, int)}
        if len(nums) > 1:
            violations.append({
                "violation": "ARTIFACT_INCONSISTENCY",
                "object": name,
                "detail": f"{name}: eng_spec={spec_n}, maturity="
                          f"{maturity_n}, traceability={chain_n} — the "
                          f"package's own artifacts disagree"})
    return {
        "available": True,
        "checks": [{"object": n, "eng_spec": a, "maturity": b,
                    "traceability": c} for n, a, b, c in checks],
        "violations": violations,
        "violation_count": len(violations),
        "verdict": "FAIL" if violations else "PASS",
    }


def _input_signature(run_dir: Path) -> List[str]:
    """TRUE input text of a run: the problem statement plus the raw
    candidate mechanism (pre-engine content). Used by the contamination
    audit to anchor each package to its own input."""
    out: List[str] = []
    prob = _j(run_dir / "problem.json")
    if prob:
        out.extend(str(v) for v in prob.values() if isinstance(v, str))
    env = _j(run_dir / "candidate_envelope.json")
    mm = (env or {}).get("mechanism_map") or {}
    for k in ("mechanism", "intervention", "expected_effect"):
        if isinstance(mm.get(k), str):
            out.append(mm[k])
    raw = (mm.get("raw_candidate") or {}) if isinstance(mm, dict) else {}
    out.extend(str(v) for v in raw.values() if isinstance(v, str))
    return out


def _candidate_id(run_dir: Path) -> Optional[str]:
    env = _j(run_dir / "candidate_envelope.json") or {}
    if isinstance(env.get("candidate_id"), str):
        return env["candidate_id"]
    stage = _j(run_dir / "stage_SYNTHESIZE.json") or {}
    return stage.get("candidate_id")


def _run_evidence_ids(run_dir: Path) -> List[str]:
    stage = _j(run_dir / "stage_RETRIEVE.json") or {}
    out: List[str] = []

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get("id") and isinstance(obj.get("source_type"), str):
                out.append(str(obj["id"]))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
    walk(stage)
    return sorted(set(out))

"""Phase 1 — benchmark corpus extractor (Coder 2).

Extracts measurable properties from the 15 frozen packages of
technology-transfer-portfolio-15 and emits BENCHMARK_DOSSIER_PROFILE.json
with the FULL distribution per measure (never a simplistic average).

The corpus is treated as READ-ONLY reference (never modified, never copied
into the engine). Only measured properties leave the corpus.

Usage:
    python3 -m discovery_fabric.benchmark.benchmark_extractor \
        --corpus /tmp/benchmark-corpus --out artifacts/benchmark
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .corpus_metrics import extract_package_metrics

# canonical portfolio number -> (P-ID, folder) — matches R370Z PACKAGE_MAP
PACKAGE_MAP = [
    ("01", "P-01", "01_multisegment_flow_control"),
    ("02", "P-02", "02_adaptive_valve"),
    ("03", "P-04", "03_catalytic_clearance"),
    ("04", "P-07", "04_drainage_floor"),
    ("05", "P-11", "05_phage_antibiofilm"),
    ("06", "P-13", "06_failure_predictor"),
    ("07", "P-15-R1", "07_self_powered_sensing"),
    ("08", "P-16", "08_nir_photovoltaic"),
    ("09", "P-21-R1", "09_uwb_localization"),
    ("10", "P-22-R1", "10_catheter_navigation"),
    ("11", "P-24", "11_gravity_damper"),
    ("12", "P-26", "12_osmotic_valve"),
    ("13", "P-27-R1", "13_pressure_sensor"),
    ("14", "P-28", "14_acoustic_detection"),
    ("15", "P-29", "15_mr_flow_sensor"),
]

V2_PACKAGES = {"P-01", "P-07", "P-13", "P-27-R1", "P-15-R1", "P-21-R1",
               "P-28", "P-29"}

# scalar measures carried into the distribution profile
SCALAR_MEASURES = {
    # (key in profile, extractor path, direction) direction: 'higher'|'lower'
    "design_inputs": ("objects.design_inputs", "higher"),
    "design_outputs": ("objects.design_outputs", "higher"),
    "failure_modes": ("objects.failure_modes", "higher"),
    "verifications": ("objects.verifications", "higher"),
    "validations": ("objects.validations", "higher"),
    "equations": ("objects.equations", "higher"),
    "critical_parameters": ("objects.critical_parameters", "higher"),
    "build_plan_steps": ("objects.build_plan_steps", "higher"),
    "external_evidence": ("objects.external_evidence", "higher"),
    "remaining_unknowns": ("objects.remaining_unknowns", "higher"),
    "traceability_chains": ("traceability_density.chains_total", "higher"),
    "chains_linked": ("traceability_density.chains_linked", "higher"),
    "chain_linkage_rate": ("traceability_density.chain_linkage_rate", "higher"),
    "evidence_id_total": ("traceability_density.evidence_id_total", "higher"),
    "evidence_ids_per_object": ("traceability_density.evidence_ids_per_object",
                                 "higher"),
    "orphan_design_outputs": ("traceability_density.orphan_design_outputs",
                              "lower"),
    "orphan_failure_modes": ("traceability_density.orphan_failure_modes",
                             "lower"),
    "unsupported_numbers": ("traceability_density.unsupported_numbers", "lower"),
    "equations_with_issues": ("traceability_density.equations_with_issues",
                              "lower"),
    "section_coverage": ("section_coverage.present", "higher"),
    "dossier_chars": ("dossier_chars", "higher"),
    "unknown_markers": ("unknown_disclosure.markers_total", "higher"),
    "buyer_decision_elements": ("buyer_decision.elements_present_len", "higher"),
    "transfer_boundary_elements": ("transfer_boundary_pdf.elements_present_len",
                                   "higher"),
    "structured_buyer_receives": ("transfer_boundary_structured.buyer_receives",
                                  "higher"),
    "structured_buyer_must_create":
        ("transfer_boundary_structured.buyer_must_create", "higher"),
    "manufacturing_has_processes": ("manufacturing.has_processes_bool", "higher"),
    "regulatory_has_di": ("regulatory.regulatory_di_count", "higher"),
}


def _dig(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _flatten(metrics: Dict[str, Any]) -> Dict[str, Any]:
    flat = dict(metrics)
    flat["buyer_decision"] = dict(metrics.get("buyer_decision") or {})
    flat["buyer_decision"]["elements_present_len"] = len(
        (metrics.get("buyer_decision") or {}).get("elements_present", []))
    flat["transfer_boundary_pdf"] = dict(
        metrics.get("transfer_boundary_pdf") or {})
    flat["transfer_boundary_pdf"]["elements_present_len"] = len(
        (metrics.get("transfer_boundary_pdf") or {}).get("elements_present", []))
    flat["manufacturing"] = dict(metrics.get("manufacturing") or {})
    flat["manufacturing"]["has_processes_bool"] = 1 if (
        metrics.get("manufacturing") or {}).get("has_processes") else 0
    return flat


def distribution(values: List[Any], direction: str) -> Dict[str, Any]:
    nums = [v for v in values if isinstance(v, (int, float))]
    unknown = len(values) - len(nums)
    out: Dict[str, Any] = {
        "n": len(values),
        "measured": len(nums),
        "missing": unknown,
        "direction": direction,
    }
    if nums:
        s = sorted(nums)
        out.update({
            "min": s[0],
            "p10": _pct(s, 0.10),
            "p25": _pct(s, 0.25),
            "median": statistics.median(s),
            "p75": _pct(s, 0.75),
            "p90": _pct(s, 0.90),
            "max": s[-1],
            "mean": round(statistics.fmean(s), 3),
            "values": s,
        })
    return out


def _pct(sorted_vals: List[float], q: float) -> float:
    """Linear-interpolation percentile (no numpy dependency)."""
    if not sorted_vals:
        return 0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return round(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac, 3)


def extract_corpus(corpus_root: Path) -> Dict[str, Any]:
    """Extract the full benchmark profile from the frozen corpus clone."""
    corpus_root = Path(corpus_root)
    packages: List[Dict[str, Any]] = []
    for num, pid, folder in PACKAGE_MAP:
        pkg_dir = corpus_root / "FULL_DOSSIERS" / folder
        if not pkg_dir.is_dir():
            raise FileNotFoundError(f"corpus package missing: {pkg_dir}")
        m = extract_package_metrics(pkg_dir)
        m["portfolio_number"] = num
        m["canonical_pid"] = pid
        m["package_version"] = "V2" if pid in V2_PACKAGES else "V1"
        packages.append(m)

    flat = [_flatten(p) for p in packages]
    measures: Dict[str, Any] = {}
    for key, (path, direction) in SCALAR_MEASURES.items():
        measures[key] = {
            "path": path,
            **distribution([_dig(f, path) for f in flat], direction),
        }

    # qualitative corpus observations (presence booleans across 15)
    buyer_missing = {}
    tb_missing = {}
    for p in packages:
        for e in (p.get("buyer_decision") or {}).get("elements_missing", []):
            buyer_missing[e] = buyer_missing.get(e, 0) + 1
        for e in (p.get("transfer_boundary_pdf") or {}).get(
                "elements_missing", []):
            tb_missing[e] = tb_missing.get(e, 0) + 1

    profile = {
        "artifact": "BENCHMARK_DOSSIER_PROFILE",
        "owner": "CODER2",
        "corpus_repo": "prateekm1007/technology-transfer-portfolio-15",
        "corpus_head_verified": "2e96b2778d9388bcbf4172281567dec6fe3d58d6",
        "n_packages": len(packages),
        "v2_packages": len([p for p in packages if p["package_version"] == "V2"]),
        "v1_packages": len([p for p in packages if p["package_version"] == "V1"]),
        "extraction_note": (
            "Measured properties only. Invention content is NOT copied into "
            "the engine. Counts re-derived from package JSON structures and "
            "rendered PDF text (Art. III: self-reported pass flags ignored)."
        ),
        "measures": measures,
        "qualitative_presence": {
            "buyer_decision_elements_missing_across_corpus": buyer_missing,
            "transfer_boundary_elements_missing_across_corpus": tb_missing,
        },
        "packages": [
            {
                "portfolio_number": p["portfolio_number"],
                "canonical_pid": p["canonical_pid"],
                "package_version": p["package_version"],
                "technology_name": (p.get("source_manifest") or {}).get(
                    "technology_name"),
                "objects": p["objects"],
                "traceability_density": p["traceability_density"],
                "section_coverage": p["section_coverage"],
                "unknown_disclosure": p["unknown_disclosure"],
                "dossier_chars": p.get("dossier_chars"),
                "killer_experiment": p.get("killer_experiment"),
                "transfer_logic_reported": p.get("transfer_logic_reported"),
                "manufacturing": p.get("manufacturing"),
                "regulatory": p.get("regulatory"),
            }
            for p in packages
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return profile


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True,
                    help="path to the cloned portfolio corpus (read-only)")
    ap.add_argument("--out", default="artifacts/benchmark",
                    help="output directory for BENCHMARK_DOSSIER_PROFILE.json")
    args = ap.parse_args()

    profile = extract_corpus(Path(args.corpus))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "BENCHMARK_DOSSIER_PROFILE.json"
    out_path.write_text(json.dumps(profile, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    print(f"BENCHMARK_DOSSIER_PROFILE.json written: {out_path}")
    print(f"  packages: {profile['n_packages']} "
          f"({profile['v2_packages']} V2 / {profile['v1_packages']} V1)")
    for k in ("design_inputs", "design_outputs", "failure_modes",
              "verifications", "equations", "critical_parameters",
              "chain_linkage_rate", "evidence_ids_per_object"):
        d = profile["measures"][k]
        print(f"  {k:24s} min={d.get('min')} median={d.get('median')} "
              f"max={d.get('max')} missing={d['missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

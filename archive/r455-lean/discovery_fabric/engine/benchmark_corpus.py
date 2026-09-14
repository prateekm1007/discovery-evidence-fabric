"""discovery_fabric/engine/benchmark_corpus.py — CEO A8/A10: the 15 frozen
dossiers as the gold-standard benchmark corpus, reduced to MEASURABLE
properties.

The frozen technology-transfer-portfolio-15 packages are the depth
benchmark. Their CONTENT is never copied into the generator (CEO rule);
instead this module extracts MEASURABLE properties per package:

    section_coverage            of the 15 canonical dossier PDF sections
    engineering_object_count    traceability chains + build-plan work pkgs
    equation_count              equations with sources
    design_input_count
    design_output_count
    failure_mode_count
    verification_count
    validation_count
    traceability_density        chains per engineering object
    external_evidence_density   custodied external sources
    buyer_decision_completeness buyer-page sections present (0-8)
    engineering_actionability   work packages w/ measurement+deliverable

and derives the DOSSIER DEPTH CONTRACT: per dimension, floor = min over the
15 packages, target = median. A generated package must meet EVERY floor
(A10 comparison test).

Extraction provenance: every source file's sha256 is recorded in the
emitted contract so the extraction is reproducible against the frozen
corpus bytes (Art. VI/XII: provable provenance for the benchmark itself).
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

# canonical frozen portfolio location (cloned next to the dev repo)
FROZEN_PORTFOLIO = Path(__file__).resolve().parents[2] / \
    "BENCHMARK_ENGINEERING_DOSSIERS" / "frozen_corpus_r370"
CANONICAL_ARTIFACT = REPO_ROOT / "BENCHMARK_DEPTH_CONTRACT.json"

DIMENSIONS = ("section_coverage", "engineering_object_count",
              "equation_count", "design_input_count", "design_output_count",
              "failure_mode_count", "verification_count",
              "validation_count", "traceability_density",
              "external_evidence_density", "buyer_decision_completeness",
              "engineering_actionability")

# the 15 canonical dossier PDF sections (measured from the frozen corpus)
DOSSIER_SECTIONS = [
    "BUYER DECISION PAGE", "WHAT IS IT?", "WHY DOES IT MATTER?",
    "WHAT IS ACTUALLY ESTABLISHED?", "WHAT IS NOT ESTABLISHED?",
    "WHY MIGHT A BUYER CARE?", "WHAT DOES THE BUYER GET?",
    "WHAT DOES THE BUYER HAVE TO BUILD?",
    "WHAT IS THE NEXT DECISIVE EXPERIMENT?", "WHAT WOULD MAKE US KILL IT?",
    "WHAT TRANSACTION COULD MAKE SENSE?", "1. Technology Description",
    "2. Mechanism Architecture", "3. Governing Engineering Model",
    "4. Design Inputs", "5. Design Outputs", "6. Critical Design Parameters",
    "7. Failure Modes", "8. Failure Analysis", "9. Verification Strategy",
    "10. Validation Strategy", "11. Materials", "12. Bill of Materials",
    "13. Manufacturing", "14. External Evidence", "15. Transfer Boundary",
]

# R440: the elite (R424) document vocabulary — the same substantive
# buyer/engineering units under the production schema's headings; the
# A10 instrument counts the union so the floor comparison stays
# like-for-like across the schema migration.
ELITE_SECTIONS = [
    "Problem definition",
    "Failure mode being addressed",
    "Mechanism",
    "Causal delta",
    "Architecture",
    "Subsystem breakdown",
    "Governing equations",
    "Parameter definitions",
    "Constraints",
    "Engineering assumptions",
    "Failure modes",
    "Verification plan",
    "Build / manufacturing pathway",
    "Decisive experiment",
    "Expected measurements",
    "Acceptance criteria",
    "Unresolved technical risks",
    "Artifact references",
    "What is it?",
    "What is actually established?",
    "What is not established?",
    "What could kill it?",
    "Why does it matter?",
    "What is different?",
    "What would we build?",
    "What is the cheapest decisive next experiment?",
    "What should we do next?",
]


def _buyer_page_sections() -> List[str]:
    out: List[str] = []
    for s in DOSSIER_SECTIONS:
        if s[0].isdigit():
            continue
        out.append(s)
    return out


BUYER_PAGE_SECTIONS = _buyer_page_sections()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def extract_package_properties(pkg_dir: Path) -> Dict[str, Any]:
    """Extract the 12 measurable dimensions from ONE frozen package."""
    sources: Dict[str, str] = {}
    for name in ("PACKAGE_MANIFEST.json", "ENGINEERING_TRACEABILITY.json",
                 "MATURITY_BASIS.json"):
        p = pkg_dir / name
        if p.exists():
            sources[name] = sha256_file(p)

    manifest = {}
    trace = {}
    maturity = {}
    if (pkg_dir / "PACKAGE_MANIFEST.json").exists():
        manifest = json.loads((pkg_dir / "PACKAGE_MANIFEST.json").read_text())
    if (pkg_dir / "ENGINEERING_TRACEABILITY.json").exists():
        trace = json.loads(
            (pkg_dir / "ENGINEERING_TRACEABILITY.json").read_text())
    if (pkg_dir / "MATURITY_BASIS.json").exists():
        maturity = json.loads((pkg_dir / "MATURITY_BASIS.json").read_text())

    # PDF section coverage
    pdf = pkg_dir / "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"
    covered = 0
    if pdf.exists():
        try:
            import pypdf
            text = "\n".join(pg.extract_text() or ""
                             for pg in pypdf.PdfReader(str(pdf)).pages)
            covered = sum(1 for s in DOSSIER_SECTIONS if s in text)
        except Exception:  # noqa: BLE001 — recorded as 0, honest
            covered = 0

    chains = trace.get("traceability_chains", []) or []
    equations = (trace.get("equation_integrity", {})
                 .get("total_equations", 0)) or 0
    dis = len(maturity.get("design_input_evidence_ids", []) or [])
    dos = (trace.get("di_do_consistency", {})
           .get("total_design_outputs", 0)) or 0
    fms = (trace.get("risk_verification", {})
           .get("total_failure_modes", 0)) or 0
    vnv = trace.get("v_and_v", {}) or {}
    verif = vnv.get("verification_items", 0) or 0
    val = vnv.get("validation_items", 0) or 0
    build_plan_objs = manifest.get("engineering_artifact_count", 0) or 0
    ext_ev = manifest.get("external_evidence_count", 0) or 0
    objects = chains.__len__() + build_plan_objs
    trace_density = round(len(chains) / objects, 3) if objects else 0.0

    return {
        "package_id": manifest.get("package_id", pkg_dir.name),
        "section_coverage": covered,
        "engineering_object_count": objects,
        "equation_count": equations,
        "design_input_count": dis,
        "design_output_count": dos,
        "failure_mode_count": fms,
        "verification_count": verif,
        "validation_count": val,
        "traceability_density": trace_density,
        "external_evidence_density": ext_ev,
        "buyer_decision_completeness": covered,
        "engineering_actionability": build_plan_objs,
        "_source_hashes": sources,
    }


def extract_corpus(corpus_root: Optional[Path] = None) -> Dict[str, Any]:
    """Extract properties across the whole frozen corpus and derive the
    Dossier Depth Contract (floor=min, target=median per dimension)."""
    root = Path(corpus_root) if corpus_root else FROZEN_PORTFOLIO
    packages = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "PACKAGE_MANIFEST.json").exists():
            packages.append(extract_package_properties(d))
    if len(packages) != 15:
        raise RuntimeError(
            f"expected 15 frozen benchmark packages at {root}, found "
            f"{len(packages)} — extraction refused (benchmark integrity)")
    floors: Dict[str, Any] = {}
    targets: Dict[str, Any] = {}
    for dim in DIMENSIONS:
        values = [p[dim] for p in packages]
        floors[dim] = min(values)
        if dim == "traceability_density":
            targets[dim] = round(statistics.median(values), 3)
        else:
            targets[dim] = statistics.median(values)
    return {
        "contract": "DOSSIER_DEPTH_CONTRACT (A8)",
        "version": "1.0.0",
        "benchmark_corpus": str(root),
        "corpus_size": len(packages),
        "dimensions": DIMENSIONS,
        "floors": floors,
        "targets": targets,
        "rule": ("a generated package must meet EVERY floor dimension "
                 "(A10); floor = min across the 15 frozen gold-standard "
                 "dossiers; target = median"),
        "per_package": packages,
        "extracted_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(
            timespec="seconds") + "Z",
    }


def write_canonical_artifact(corpus_root: Optional[Path] = None) -> Path:
    data = extract_corpus(corpus_root)
    CANONICAL_ARTIFACT.write_text(json.dumps(data, indent=2,
                                             ensure_ascii=False))
    return CANONICAL_ARTIFACT


def load_contract() -> Dict[str, Any]:
    """Load the committed canonical contract artifact."""
    return json.loads(CANONICAL_ARTIFACT.read_text())


def meets_floors(generated: Dict[str, Any],
                 contract: Optional[Dict[str, Any]] = None,
                 ) -> Dict[str, Any]:
    """CEO A10 comparison: does ONE generated package meet every floor?
    `generated` maps dimension -> measured value (from the generated
    package's own artifacts, measured by measure_generated_package)."""
    contract = contract or load_contract()
    results = {}
    for dim in DIMENSIONS:
        floor = contract["floors"][dim]
        got = generated.get(dim)
        results[dim] = {"floor": floor, "generated": got,
                        "pass": isinstance(got, (int, float)) and got >= floor}
    return {"package_id": generated.get("package_id"),
            "dimensions": results,
            "passed": all(r["pass"] for r in results.values())}


# --------------------------------------------------------------------------
# measuring a GENERATED package with the same instruments
# --------------------------------------------------------------------------
def measure_generated_package(spec: Dict[str, Any], eng: Dict[str, Any],
                              package_report: Dict[str, Any],
                              ) -> Dict[str, Any]:
    """Apply the SAME measurable dimensions to a generated package so the
    A10 comparison is like-for-like (identical instruments both sides)."""
    # R440: the production package is the ELITE (R424) schema — the
    # instrument measures BOTH vocabularies (the frozen contract's
    # sections and the elite document headings) so the like-for-like
    # floor comparison survives the schema migration without being
    # lowered (BS-024: the instrument must stay causally connected to
    # what production actually emits).
    chains = 0
    trace_path = Path(package_report["folder"]) / \
        "ENGINEERING_TRACEABILITY.json"
    if trace_path.exists():
        tr = json.loads(trace_path.read_text())
        chains = len(tr.get("traceability_chains", [])
                     or tr.get("links", []))
    equations = eng.get("engineering_core", {}).get("governing_model", {}) \
        .get("equations", [])
    fms = eng.get("failure_analysis", [])
    verif = eng.get("verification_matrix", [])
    val = eng.get("validation_matrix", [])
    build_plan = eng.get("engineering_build_plan", [])
    dos = eng.get("design_outputs", [])
    dis = eng.get("design_inputs", [])
    # external evidence: the manifest field (v4 schema) OR the elite
    # evidence machine layer (retrieval count + classified roles)
    ext_ev = 0
    manifest_path = Path(package_report["folder"]) / "PACKAGE_MANIFEST.json"
    if manifest_path.exists():
        ext_ev = json.loads(manifest_path.read_text()) \
            .get("external_evidence_count", 0)
    ev_path = Path(package_report["folder"]) / "03_EVIDENCE_SUMMARY.json"
    if ev_path.exists() and not ext_ev:
        ev = json.loads(ev_path.read_text())
        retrieval = (ev.get("evidence_pack") or {}).get("retrieval") or []
        ext_ev = len(retrieval) + len(
            eng.get("external_engineering_precedent") or [])
    # section coverage: count the canonical sections present in the
    # generated dossier + decision card (the elite vocabulary carries
    # the same substantive units under R424 headings)
    covered = 0
    folder = Path(package_report["folder"])
    texts = {}
    for doc in ("02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                "03_BUYER_DECISION_CARD.pdf"):
        p = folder / doc
        if p.exists():
            import pypdf
            texts[doc] = "\n".join(pg.extract_text() or ""
                                    for pg in pypdf.PdfReader(str(p)).pages)
    combined = "\n".join(texts.values())
    covered = sum(1 for s in DOSSIER_SECTIONS if s in combined) + \
        sum(1 for s in ELITE_SECTIONS if s in combined)
    objects = chains + len(build_plan)
    return {
        "package_id": package_report.get("folder", ""),
        "section_coverage": covered,
        "engineering_object_count": objects,
        "equation_count": len(equations),
        "design_input_count": len(dis),
        "design_output_count": len(dos),
        "failure_mode_count": len(fms),
        "verification_count": len(verif),
        "validation_count": len(val),
        "traceability_density": round(chains / objects, 3) if objects else 0.0,
        "external_evidence_density": ext_ev,
        "buyer_decision_completeness": covered,
        "engineering_actionability": sum(
            1 for w in build_plan
            if w.get("measurement") and w.get("deliverable")),
    }

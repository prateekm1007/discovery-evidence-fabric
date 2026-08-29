"""discovery_fabric/engine/benchmark_dossiers.py — CEO E15-A: the 15 frozen
buyer packages as a genuine CONTENT benchmark.

The A8 contract (benchmark_corpus.py) froze STRUCTURAL floors (section
coverage, object counts). The CEO E15 audit requires the benchmark to carry
ENGINEERING SUBSTANCE, not just section presence or minimum counts:

    "A package with 20 headings and shallow content must fail."

This module derives, FOR EACH of the 15 frozen packages, a benchmark vector
of 16 measurable properties — the CEO E15-A field list:

    package_id
    engineering_sections
    design_input_count
    design_output_count
    failure_mode_count
    verification_count
    validation_count
    equation_count
    parameter_count
    provenance_density
    traceability_density
    manufacturing_depth
    regulatory_depth
    transfer_depth
    buyer_decision_depth
    engineering_actionability

Every value is COMPUTED from the actual frozen package bytes (JSON artifacts
+ rendered PDF text). No expected value is hard-coded: the only literals in
this module are measurement instruments (which section headings to locate,
which regulatory standards vocabulary to count), never the measured depth
values themselves. The derived contract (E15_BENCHMARK_CONTRACT.json) sets
floor = min over the corpus and target = median, exactly like A8, and every
source file's sha256 is recorded so the extraction is reproducible against
the frozen corpus bytes (Art. VI/XII).

The frozen portfolio repository is NEVER modified (CEO standing rule):
extraction is read-only.
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

# canonical frozen portfolio location (cloned next to the dev repo; frozen
# at 2e96b27 — read-only, never modified)
FROZEN_PORTFOLIO = Path(__file__).resolve().parents[2] / \
    "BENCHMARK_ENGINEERING_DOSSIERS" / "frozen_corpus_r370"

# canonical E15-A artifact directory (committed to the dev repo)
BENCHMARK_DIR = REPO_ROOT / "BENCHMARK_ENGINEERING_DOSSIERS"
CONTRACT_ARTIFACT = BENCHMARK_DIR / "E15_BENCHMARK_CONTRACT.json"

# the 16 E15 benchmark dimensions (CEO E15-A field order, minus package_id)
DIMENSIONS = ("engineering_sections", "design_input_count",
              "design_output_count", "failure_mode_count",
              "verification_count", "validation_count", "equation_count",
              "parameter_count", "provenance_density",
              "traceability_density", "manufacturing_depth",
              "regulatory_depth", "transfer_depth", "buyer_decision_depth",
              "engineering_actionability")

# the 15 canonical dossier sections (same instrument as A8 benchmark_corpus)
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
    "16. Open Questions",
]

BUYER_PAGE_SECTIONS = [s for s in DOSSIER_SECTIONS if not s[0].isdigit()]

# measurement instruments: regulatory standards vocabulary (we COUNT matches
# in the corpus text; the counts themselves are measured, never preset)
REGULATORY_SIGNALS = (
    r"ISO\s?\d{3,5}", r"IEC\s?\d{3,5}", r"ASTM\s?[A-Z]?\d{1,5}",
    r"FDA", r"510\s?\(?k\)?", r"PMA", r"CE\s?mark", r"Class\s+(?:I|II|III)\b",
    r"predicate\s+device", r"GMP", r"design\s+control(?:s)?\b",
    r"ISO\s?13485", r"ISO\s?10993", r"biocompatibility", r"sterility",
)

# boundary-honesty vocabulary (a transfer boundary that enumerates what is
# NOT established is substance, not weakness — this is measured, not scored)
BOUNDARY_SIGNALS = (r"NOT ESTABLISHED", r"UNKNOWN", r"NOT PERFORMED",
                    r"NOT\s+VALIDATED", r"NOT\s+VERIFIED", r"requires\s+a?\s*"
                    r"(?:physical|bench|animal|clinical)",
                    r"out\s+of\s+scope", r"transfer\s+boundary")

# manufacturing process vocabulary (instruments to locate manufacturing
# sentences inside section 13; the COUNT is the measured value)
MANUFACTURING_SIGNALS = (
    r"process", r"manufactur", r"assembly", r"tolerance", r"bonding",
    r"molding|moulding", r"etching", r"deposit(?:ion)?", r"anneal",
    r"steriliz|sterilis", r"cleanroom", r"injection", r"extrusion",
    r"machin(?:e|ing)", r"welding", r"soldering", r"adhesive", r"seal(?:ing)?",
    r"packaging", r"lot", r"supplier", r"lead\s+time", r"cost", r"yield",
)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dossier_text(pkg_dir: Path) -> str:
    pdf = pkg_dir / "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"
    if not pdf.exists():
        return ""
    try:
        import pypdf
        return "\n".join(pg.extract_text() or ""
                         for pg in pypdf.PdfReader(str(pdf)).pages)
    except Exception:  # noqa: BLE001 — recorded as empty, honest
        return ""


def _section_span(text: str, heading: str) -> tuple:
    """Return (start, end) character offsets of `heading`'s section body:
    from the heading to the next canonical section heading (or EOF)."""
    starts = []
    for s in DOSSIER_SECTIONS:
        idx = text.find(s)
        if idx >= 0:
            starts.append((idx, s))
    starts.sort()
    for i, (idx, s) in enumerate(starts):
        if s == heading:
            end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
            return idx, end
    return -1, -1


def _sentences(segment: str) -> List[str]:
    """Split a text segment into sentence-like units (deterministic)."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", segment)
    return [p.strip().replace("\n", " ") for p in parts if len(p.strip()) >= 8]


def _substantive_count(segment: str, signals: tuple) -> int:
    """Count sentence-like units that are substantive: >= 6 words OR match a
    domain signal regex. This is a CONTENT density instrument."""
    n = 0
    for s in _sentences(segment):
        words = len(s.split())
        hit = any(re.search(sig, s, re.I) for sig in signals)
        if words >= 6 or hit:
            n += 1
    return n


# --------------------------------------------------------------------------
def extract_package_vector(pkg_dir: Path) -> Dict[str, Any]:
    """Compute the 16-field E15-A benchmark vector for ONE frozen package.

    Structural fields come from ENGINEERING_TRACEABILITY.json /
    PACKAGE_MANIFEST.json / MATURITY_BASIS.json. Content-depth fields are
    measured from the rendered dossier PDF text.
    """
    sources: Dict[str, str] = {}
    manifest: Dict[str, Any] = {}
    trace: Dict[str, Any] = {}
    maturity: Dict[str, Any] = {}
    for name, store in (("PACKAGE_MANIFEST.json", manifest),
                        ("ENGINEERING_TRACEABILITY.json", trace),
                        ("MATURITY_BASIS.json", maturity)):
        p = pkg_dir / name
        if p.exists():
            store.update(json.loads(p.read_text()))
            sources[name] = sha256_file(p)

    text = dossier_text(pkg_dir)
    covered = sum(1 for s in DOSSIER_SECTIONS if s in text)

    chains = trace.get("traceability_chains", []) or []
    # provenance_density is measured over LINKAGE-schema chains (the gold-
    # standard schema: design_input_id -> parameter -> design_output_id ->
    # failure_mode_id -> verification_id). The frozen corpus stores only
    # linkage rows; generated packages carry typed chains and are filtered
    # to the same schema so the meter is identical on both sides.
    linkage = [c for c in chains
               if "failure_mode_id" in c and "design_input_id" in c]
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
    params = (trace.get("number_provenance", {})
              .get("total_critical_params", 0)) or 0
    build_plan_objs = manifest.get("engineering_artifact_count", 0) or 0
    objects = len(chains) + build_plan_objs

    # provenance_density: fraction of LINKAGE-schema chains with a COMPLETE
    # provenance linkage (input -> parameter -> output -> failure ->
    # verification, all present and linked) — substance, not count
    complete = 0
    for c in linkage:
        fields_ok = all(str(c.get(k) or "").strip()
                        for k in ("design_input_id", "parameter",
                                  "design_output_id", "failure_mode_id",
                                  "verification_id"))
        if fields_ok and c.get("linked", False):
            complete += 1
    provenance_density = round(complete / len(linkage), 3) if linkage else 0.0
    # E16-C refinement: completeness among CONSUMED design inputs (a
    # context input that no design output consumes cannot have downstream
    # provenance BY CONSTRUCTION — counting it as a provenance failure
    # conflates context-ness with provenance failure; context-ness is
    # separately visible in the design_role taxonomy). Measured
    # identically on both origins.
    consumed = [c for c in linkage
                if c.get("design_output_id") not in ("NOT_LINKED", None, "")]
    complete_consumed = sum(1 for c in consumed
                            if c.get("linked", False))
    provenance_density_consumed = (round(complete_consumed / len(consumed), 3)
                                   if consumed else 0.0)

    # --- content-depth measures (from the rendered PDF text) --------------
    mfg_s, mfg_e = _section_span(text, "13. Manufacturing")
    bom_s, bom_e = _section_span(text, "12. Bill of Materials")
    mfg_segment = text[mfg_s:mfg_e] if mfg_s >= 0 else ""
    bom_segment = text[bom_s:bom_e] if bom_s >= 0 else ""
    manufacturing_depth = (
        _substantive_count(mfg_segment, MANUFACTURING_SIGNALS)
        + _substantive_count(bom_segment, MANUFACTURING_SIGNALS))

    regulatory_depth = len({m.group(0).strip().upper()
                            for sig in REGULATORY_SIGNALS
                            for m in re.finditer(sig, text, re.I)})

    tb_s, tb_e = _section_span(text, "15. Transfer Boundary")
    transfer_depth = (
        _substantive_count(text[tb_s:tb_e] if tb_s >= 0 else "",
                           BOUNDARY_SIGNALS)
        + len({m.group(0).upper() for sig in BOUNDARY_SIGNALS
               for m in re.finditer(sig, text, re.I)}))

    bdp_s, bdp_e = _section_span(text, "BUYER DECISION PAGE")
    buyer_segment = text[bdp_s:bdp_e] if bdp_s >= 0 else ""
    buyer_sections_present = sum(
        1 for s in BUYER_PAGE_SECTIONS if s in text)
    quantified_lines = sum(
        1 for s in _sentences(buyer_segment) if re.search(r"\d", s))
    buyer_decision_depth = buyer_sections_present + quantified_lines

    return {
        "package_id": manifest.get("package_id", pkg_dir.name),
        "engineering_sections": covered,
        "design_input_count": dis,
        "design_output_count": dos,
        "failure_mode_count": fms,
        "verification_count": verif,
        "validation_count": val,
        "equation_count": equations,
        "parameter_count": params,
        "provenance_density": provenance_density,
        "provenance_density_consumed": provenance_density_consumed,
        "traceability_density": (round(len(chains) / objects, 3)
                                 if objects else 0.0),
        "manufacturing_depth": manufacturing_depth,
        "regulatory_depth": regulatory_depth,
        "transfer_depth": transfer_depth,
        "buyer_decision_depth": buyer_decision_depth,
        "engineering_actionability": build_plan_objs,
        "_source_hashes": sources,
        "_content_evidence": {
            "dossier_pdf_chars": len(text),
            "manufacturing_has_processes":
                bool((trace.get("manufacturing") or {}).get("has_processes")),
            "regulatory_has_design_input_di":
                bool((trace.get("regulatory") or {}).get("has_regulatory_di")),
            "transfer_ready_recorded":
                bool((trace.get("transfer_logic") or {})
                     .get("transfer_ready")),
        },
    }


def extract_corpus(corpus_root: Optional[Path] = None) -> Dict[str, Any]:
    """Extract the 15 benchmark vectors and derive the E15 contract.

    CEO E16-A: floors/targets are derived from the TRAINING_REFERENCE
    stratum ONLY (10 packages). The DEVELOPMENT_HOLDOUT stratum never
    informs floors; the BLIND_HOLDOUT stratum is sealed until evaluation
    (benchmark_split.py). All 15 measured vectors are recorded for
    transparency, each labeled with its stratum."""
    from .benchmark_split import (SPLIT_ARTIFACT, assign_strata,
                                  load_split, stratum_of)
    root = Path(corpus_root) if corpus_root else FROZEN_PORTFOLIO
    dirs = [d for d in sorted(root.iterdir())
            if d.is_dir() and (d / "PACKAGE_MANIFEST.json").exists()]
    if len(dirs) != 15:
        raise RuntimeError(
            f"expected 15 frozen benchmark packages at {root}, found "
            f"{len(dirs)} — E15-A extraction refused (benchmark "
            "integrity)")
    if not SPLIT_ARTIFACT.exists():
        from .benchmark_split import write_canonical_artifacts
        write_canonical_artifacts()
    split = load_split()
    # a foreign corpus cannot be stratified by the canonical assignment
    assign_strata(root)
    packages = []
    for d in dirs:
        p = extract_package_vector(d)
        p["_stratum"] = stratum_of(d.name)
        packages.append(p)
    training = [p for p in packages
                if p["_stratum"] == "TRAINING_REFERENCE"]
    if len(training) != 10:
        raise RuntimeError(
            "TRAINING_REFERENCE stratum must hold 10 packages, found "
            f"{len(training)} — floors refused (E16-A)")
    floors: Dict[str, Any] = {}
    targets: Dict[str, Any] = {}
    for dim in DIMENSIONS:
        values = [p[dim] for p in training]
        floors[dim] = min(values)
        targets[dim] = (round(statistics.median(values), 3)
                        if isinstance(values[0], float)
                        else statistics.median(values))
    return {
        "contract": "E15_BENCHMARK_CONTRACT (A8/E15-A, E16-A stratified)",
        "version": "2.0.0",
        "benchmark_corpus": str(root),
        "corpus_size": len(packages),
        "dimensions": list(DIMENSIONS),
        "floors": floors,
        "targets": targets,
        "floors_derived_from": "TRAINING_REFERENCE (10 packages; E16-A)",
        "strata": split["strata"],
        "rule": ("a generated package must meet EVERY floor dimension "
                 "(E15-J); floor = min across the TRAINING_REFERENCE "
                 "stratum; target = median; values COMPUTED from the "
                 "actual corpus, never hard-coded; BLIND_HOLDOUT vectors "
                 "are sealed and never inform these floors"),
        "per_package": packages,
        "extracted_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds") + "Z",
    }


def write_canonical_artifact(corpus_root: Optional[Path] = None) -> Path:
    """Write BENCHMARK_ENGINEERING_DOSSIERS/E15_BENCHMARK_CONTRACT.json plus
    one per-package vector file (E15-A canonical artifact)."""
    data = extract_corpus(corpus_root)
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    for pkg in data["per_package"]:
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_",
                      str(pkg.get("package_id", "pkg")))
        (BENCHMARK_DIR / f"{safe}.json").write_text(
            json.dumps(pkg, indent=2, ensure_ascii=False))
    CONTRACT_ARTIFACT.write_text(json.dumps(data, indent=2,
                                            ensure_ascii=False))
    return CONTRACT_ARTIFACT


def load_contract() -> Dict[str, Any]:
    return json.loads(CONTRACT_ARTIFACT.read_text())


def meets_floors(generated: Dict[str, Any],
                 contract: Optional[Dict[str, Any]] = None,
                 ) -> Dict[str, Any]:
    """E15-J comparison for ONE generated package against the E15-A floors.
    `generated` maps dimension -> measured value (measured with the SAME
    instruments by measure_generated_vector)."""
    contract = contract or load_contract()
    results = {}
    for dim in DIMENSIONS:
        floor = contract["floors"][dim]
        got = generated.get(dim)
        results[dim] = {"floor": floor, "generated": got,
                        "pass": isinstance(got, (int, float))
                        and got >= floor}
    return {"package_id": generated.get("package_id"),
            "dimensions": results,
            "passed": all(r["pass"] for r in results.values())}


# --------------------------------------------------------------------------
# measuring a GENERATED package with the SAME instruments (like-for-like)
# --------------------------------------------------------------------------
def measure_generated_vector(spec: Dict[str, Any], eng: Dict[str, Any],
                             package_report: Dict[str, Any],
                             ) -> Dict[str, Any]:
    """Apply the identical 16 instruments to a GENERATED package. The dossier
    PDF text is measured the same way as the frozen corpus; the structural
    fields come from the generated engineering specification."""
    folder = Path(package_report["folder"])
    text = dossier_text(folder)
    covered = sum(1 for s in DOSSIER_SECTIONS if s in text)

    trace_path = folder / "ENGINEERING_TRACEABILITY.json"
    chains: List[Dict[str, Any]] = []
    if trace_path.exists():
        chains = json.loads(trace_path.read_text()) \
            .get("traceability_chains", []) or []
    linkage = [c for c in chains
               if "failure_mode_id" in c and "design_input_id" in c]
    equations = (eng.get("engineering_core", {})
                 .get("governing_model", {}).get("equations", []))
    params = eng.get("engineering_core", {}).get("critical_parameters", [])
    fms = eng.get("failure_analysis", [])
    verif = eng.get("verification_matrix", [])
    val = eng.get("validation_matrix", [])
    dis = eng.get("design_inputs", [])
    dos = eng.get("design_outputs", [])
    build_plan = eng.get("engineering_build_plan", [])

    complete = 0
    for c in linkage:
        fields_ok = all(str(c.get(k) or "").strip()
                        for k in ("design_input_id", "parameter",
                                  "design_output_id", "failure_mode_id",
                                  "verification_id"))
        if fields_ok and c.get("linked", False):
            complete += 1
    provenance_density = round(complete / len(linkage), 3) if linkage else 0.0
    consumed = [c for c in linkage
                if c.get("design_output_id") not in ("NOT_LINKED", None, "")]
    complete_consumed = sum(1 for c in consumed if c.get("linked", False))
    provenance_density_consumed = (round(complete_consumed / len(consumed), 3)
                                   if consumed else 0.0)

    manifest_path = folder / "PACKAGE_MANIFEST.json"
    build_plan_objs = 0
    if manifest_path.exists():
        build_plan_objs = json.loads(manifest_path.read_text()) \
            .get("engineering_artifact_count", 0) or 0
    objects = len(chains) + build_plan_objs

    mfg_s, mfg_e = _section_span(text, "13. Manufacturing")
    bom_s, bom_e = _section_span(text, "12. Bill of Materials")
    manufacturing_depth = (
        _substantive_count(text[mfg_s:mfg_e] if mfg_s >= 0 else "",
                           MANUFACTURING_SIGNALS)
        + _substantive_count(text[bom_s:bom_e] if bom_s >= 0 else "",
                             MANUFACTURING_SIGNALS))
    regulatory_depth = len({m.group(0).strip().upper()
                            for sig in REGULATORY_SIGNALS
                            for m in re.finditer(sig, text, re.I)})
    tb_s, tb_e = _section_span(text, "15. Transfer Boundary")
    transfer_depth = (
        _substantive_count(text[tb_s:tb_e] if tb_s >= 0 else "",
                           BOUNDARY_SIGNALS)
        + len({m.group(0).upper() for sig in BOUNDARY_SIGNALS
               for m in re.finditer(sig, text, re.I)}))
    bdp_s, bdp_e = _section_span(text, "BUYER DECISION PAGE")
    buyer_decision_depth = (
        sum(1 for s in BUYER_PAGE_SECTIONS if s in text)
        + sum(1 for s in _sentences(text[bdp_s:bdp_e] if bdp_s >= 0 else "")
              if re.search(r"\d", s)))

    return {
        "package_id": package_report.get("folder", ""),
        "engineering_sections": covered,
        "design_input_count": len(dis),
        "design_output_count": len(dos),
        "failure_mode_count": len(fms),
        "verification_count": len(verif),
        "validation_count": len(val),
        "equation_count": len(equations),
        "parameter_count": len(params),
        "provenance_density": provenance_density,
        "provenance_density_consumed": provenance_density_consumed,
        "traceability_density": (round(len(chains) / objects, 3)
                                 if objects else 0.0),
        "manufacturing_depth": manufacturing_depth,
        "regulatory_depth": regulatory_depth,
        "transfer_depth": transfer_depth,
        "buyer_decision_depth": buyer_decision_depth,
        "engineering_actionability": sum(
            1 for w in build_plan
            if w.get("measurement") and w.get("deliverable")),
    }

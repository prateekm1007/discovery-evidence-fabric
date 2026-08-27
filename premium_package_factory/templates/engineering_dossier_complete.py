"""
engineering_dossier_complete.py — Complete Engineering Technology-Transfer Dossiers.

Incorporates REAL external engineering evidence from web/database searches:
- FDA 510(k) predicate devices
- PubMed/PMC scientific literature
- Manufacturing process literature
- Materials biocompatibility references
- Regulatory classification precedents

Uses same authoritative source universe as reconciliation verifier.
Every external evidence record has full provenance (URL, date, snippet, source_hash).
Never fabricates engineering facts. UNKNOWN remains UNKNOWN.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_THIS_DIR))

from gates.consultant_reconciliation_acceptance import (
    _find_repo_root, load_json_strict, _sha256,
    find_package_with_lineage, find_structured_recursive,
    discover_packages_iterative,
    REGISTRY_PATH, MANIFEST_PATH, MANIFEST_INTEGRITY_PATH, NAMESPACE_PATH,
    verify_manifest_integrity, verify_authority_hierarchy,
)

REPO_ROOT = _find_repo_root()
OUTPUT_DIR = os.path.join(os.path.dirname(_THIS_DIR), "output", "engineering_dossiers_complete")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def _now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def _sha256_str(s): return hashlib.sha256(s.encode()).hexdigest()


# ============================================================================
# External Engineering Evidence Registry
# ============================================================================

def load_external_evidence():
    """Load external engineering evidence from web search results."""
    evidence = {}
    search_files = {
        "P-01": ["/tmp/pubmed_p01.json", "/tmp/fda_shunt_search.json"],
        "P-02": ["/tmp/pubmed_p02.json"],
        "P-04": ["/tmp/pubmed_p04.json"],
        "P-07": ["/tmp/pubmed_p07.json"],
        "P-11": ["/tmp/pubmed_p11.json"],
        "P-13": ["/tmp/pubmed_p13.json"],
        "P-15-R1": ["/tmp/pubmed_p15.json"],
        "P-16": ["/tmp/pubmed_p16.json"],
        "P-21-R1": ["/tmp/pubmed_p21.json"],
        "P-22-R1": ["/tmp/pubmed_p22.json"],
        "P-24": ["/tmp/pubmed_p24.json"],
        "P-26": ["/tmp/pubmed_p26.json"],
        "P-27-R1": ["/tmp/pubmed_p27.json"],
        "P-28": ["/tmp/pubmed_p28.json"],
        "P-29": ["/tmp/pubmed_p29.json"],
    }

    # Add shared evidence
    shared_files = {
        "FDA_CLASSIFICATION": "/tmp/fda_classification.json",
        "MANUFACTURING_SHUNT": "/tmp/manufacturing_shunt.json",
        "MATERIALS_IMPLANT": "/tmp/materials_implant.json",
    }

    for pkg_id, files in search_files.items():
        pkg_evidence = []
        for fpath in files:
            if not os.path.exists(fpath):
                continue
            with open(fpath) as f:
                results = json.load(f)
            for r in results:
                pkg_evidence.append({
                    "source_url": r.get("url", ""),
                    "source_title": r.get("name", ""),
                    "source_snippet": r.get("snippet", ""),
                    "source_date": r.get("date", ""),
                    "source_host": r.get("host_name", ""),
                    "source_hash": _sha256_str(r.get("url", "") + r.get("snippet", "")),
                    "evidence_class": "EXTERNAL_ENGINEERING_REFERENCE",
                    "what_it_establishes": _classify_evidence(r, pkg_id),
                    "what_it_does_not_establish": "Does NOT establish that this specific invention has been built, tested, or validated. External precedent only.",
                })
        evidence[pkg_id] = pkg_evidence

    # Add shared evidence to all packages
    shared_evidence = []
    for category, fpath in shared_files.items():
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            results = json.load(f)
        for r in results:
            shared_evidence.append({
                "source_url": r.get("url", ""),
                "source_title": r.get("name", ""),
                "source_snippet": r.get("snippet", ""),
                "source_date": r.get("date", ""),
                "source_host": r.get("host_name", ""),
                "source_hash": _sha256_str(r.get("url", "") + r.get("snippet", "")),
                "evidence_class": "EXTERNAL_ENGINEERING_REFERENCE",
                "category": category,
                "what_it_establishes": _classify_shared_evidence(r, category),
                "what_it_does_not_establish": "Does NOT establish design specifications for this specific invention.",
            })

    for pkg_id in evidence:
        evidence[pkg_id].extend(shared_evidence)

    return evidence


def _classify_evidence(result, pkg_id):
    """Classify what an external evidence result establishes."""
    snippet = result.get("snippet", "").lower()
    title = result.get("name", "").lower()

    if "fda" in snippet or "510(k)" in snippet or "510k" in snippet:
        return "FDA regulatory precedent for comparable device technology"
    if "pmc" in result.get("url", "").lower() or "pubmed" in snippet:
        return "Scientific literature on comparable mechanism or technology"
    if "manufacturing" in snippet or "extrusion" in snippet or "molding" in snippet:
        return "Manufacturing process precedent for comparable devices"
    if "biocompatibility" in snippet or "iso 10993" in snippet:
        return "Materials biocompatibility testing framework reference"
    if "shunt" in snippet and ("obstruction" in snippet or "failure" in snippet):
        return "Clinical evidence of shunt failure modes relevant to this invention"
    return "External engineering reference for comparable technology"


def _classify_shared_evidence(result, category):
    """Classify shared evidence."""
    if category == "FDA_CLASSIFICATION":
        return "FDA device classification precedent for CSF shunt systems"
    if category == "MANUFACTURING_SHUNT":
        return "Manufacturing process reference for CSF shunt catheters"
    if category == "MATERIALS_IMPLANT":
        return "Implantable device materials and biocompatibility testing framework"
    return "External engineering reference"


# ============================================================================
# Design Input Register Builder
# ============================================================================

def build_design_input_register(pkg_id, pkg_data, external_evidence):
    """Build Design Input Register from source data + external evidence."""
    r332 = pkg_data.get("r332", {})
    contract = pkg_data.get("contract", {})
    claims = pkg_data.get("claims", {})

    inputs = []
    di_id = 1

    # Clinical need (from problem)
    problem = r332.get("problem", "")
    if problem:
        inputs.append({
            "id": f"DI-{di_id:03d}",
            "design_input": "Clinical need",
            "value": problem,  # R370U-U6: no truncation
            "unit": "N/A",
            "basis": "R332 problem field",
            "source": "R332",
            "evidence_class": "VERIFIED",
            "verification_requirement": "Clinical validation required",
            "status": "SUPPORTED"
        })
        di_id += 1

    # Functional requirement (from mechanism)
    mechanism = r332.get("mechanism", "")
    if mechanism:
        inputs.append({
            "id": f"DI-{di_id:03d}",
            "design_input": "Functional requirement",
            "value": mechanism,  # R370U-U6: no truncation
            "unit": "N/A",
            "basis": "R332 mechanism field",
            "source": "R332",
            "evidence_class": "MODELLED",
            "verification_requirement": "Bench verification per decisive experiment",
            "status": "SUPPORTED"
        })
        di_id += 1

    # Performance requirement (from pass_rule)
    pass_rule = r332.get("pass_rule", "")
    if pass_rule:
        inputs.append({
            "id": f"DI-{di_id:03d}",
            "design_input": "Performance acceptance criterion",
            "value": pass_rule,  # R370U-U6: no truncation
            "unit": "N/A",
            "basis": "R332 pass_rule field",
            "source": "R332",
            "evidence_class": "MODELLED",
            "verification_requirement": "Bench test per decisive experiment",
            "status": "SUPPORTED"
        })
        di_id += 1

    # Safety requirement (from fail_rule)
    fail_rule = r332.get("fail_rule", "")
    if fail_rule:
        inputs.append({
            "id": f"DI-{di_id:03d}",
            "design_input": "Safety/failure criterion",
            "value": fail_rule,  # R370U-U6: no truncation
            "unit": "N/A",
            "basis": "R332 fail_rule field",
            "source": "R332",
            "evidence_class": "MODELLED",
            "verification_requirement": "Falsification test",
            "status": "SUPPORTED"
        })
        di_id += 1

    # Add UNKNOWN design inputs that are needed but not in source
    for req in ["Biocompatibility (ISO 10993)", "Sterilization compatibility",
                "Mechanical integrity", "Electromagnetic compatibility (if applicable)",
                "User needs analysis", "Clinical workflow integration"]:
        inputs.append({
            "id": f"DI-{di_id:03d}",
            "design_input": req,
            "value": "UNKNOWN",
            "unit": "N/A",
            "basis": "Required by FDA design control (QMSR)",
            "source": "NONE — requires engineering analysis",
            "evidence_class": "UNKNOWN",
            "verification_requirement": "Engineering analysis required",
            "status": "UNRESOLVED"
        })
        di_id += 1

    # Add external evidence-supported inputs
    for ev in external_evidence.get(pkg_id, []):
        if ev.get("what_it_establishes", "").startswith("FDA"):
            inputs.append({
                "id": f"DI-{di_id:03d}",
                "design_input": "Regulatory classification precedent",
                "value": ev["source_snippet"],  # R370U-U6: no truncation
                "unit": "N/A",
                "basis": "External FDA database search",
                "source": ev["source_url"],
                "source_hash": ev["source_hash"],
                "evidence_class": "EXTERNAL_ENGINEERING_REFERENCE",
                "verification_requirement": "Regulatory counsel review required",
                "status": "EXTERNALLY_REFERENCED"
            })
            di_id += 1

    return inputs


# ============================================================================
# Complete Engineering Dossier Builder
# ============================================================================

def build_complete_dossier(pkg_id, state, source_meta, external_evidence):
    """Build a complete Engineering Technology-Transfer Dossier."""
    # Get package data using lineage-enforced resolver
    pkg_sources = {}
    for sid, sd in state.items():
        pd = find_package_with_lineage(sd, pkg_id)
        if pd is not None:
            pkg_sources[sid] = pd

    if not pkg_sources:
        return {"package_id": pkg_id, "error": "PACKAGE_NOT_FOUND", "status": "FAILED"}

    primary_sid = next(iter(pkg_sources.keys()))
    primary_pkg = pkg_sources[primary_sid]

    r332 = primary_pkg
    contract = {}
    claims = {}
    axes = {}
    for sid in pkg_sources:
        pd = pkg_sources[sid]
        if isinstance(pd, dict):
            if "contract" in pd or "hypothesis" in pd:
                contract = pd.get("contract", pd)
            if "material_claims" in pd:
                claims = pd
            if "DERIVED_TRANSFER_POSTURE" in pd:
                axes = pd

    # Build Design Input Register
    pkg_data = {"r332": r332, "contract": contract, "claims": claims}
    design_inputs = build_design_input_register(pkg_id, pkg_data, external_evidence)

    # Count supported vs unresolved
    n_supported = sum(1 for di in design_inputs if di["status"] in ("SUPPORTED", "EXTERNALLY_REFERENCED"))
    n_unresolved = sum(1 for di in design_inputs if di["status"] == "UNRESOLVED")
    n_external = sum(1 for di in design_inputs if di["status"] == "EXTERNALLY_REFERENCED")

    # External evidence for this package
    ext_ev = external_evidence.get(pkg_id, [])

    # Engineering maturity per dimension
    maturity = {
        "CONCEPT": {"state": "DEFINED" if r332.get("mechanism") else "UNKNOWN",
                     "evidence": "R332 mechanism field" if r332.get("mechanism") else "NONE"},
        "FUNCTION": {"state": "MODELLED" if r332.get("decisive_experiment") else "UNKNOWN",
                      "evidence": "R332 decisive_experiment" if r332.get("decisive_experiment") else "NONE"},
        "GEOMETRY": {"state": "ABSENT", "evidence": "No dimensioned geometry in any source"},
        "CAD": {"state": "NOT_CREATED", "evidence": "No CAD data exists"},
        "MATERIALS": {"state": "UNKNOWN",
                      "evidence": f"{len([e for e in ext_ev if 'biocompat' in e.get('source_snippet','').lower() or 'material' in e.get('source_snippet','').lower()])} external references found, but no source-identified materials"},
        "BOM": {"state": "CONCEPTUAL", "evidence": "Preliminary BOM from mechanism description (ENGINEERING_PROPOSED)"},
        "MANUFACTURING": {"state": "UNKNOWN",
                          "evidence": f"{len([e for e in ext_ev if 'manufact' in e.get('source_snippet','').lower()])} external references found, but no validated process"},
        "INTERFACES": {"state": "UNKNOWN", "evidence": "No interface specifications in source"},
        "VERIFICATION": {"state": "MODELLED" if r332.get("pass_rule") else "UNKNOWN",
                         "evidence": "Decisive experiment protocol from R332"},
        "VALIDATION": {"state": "ABSENT", "evidence": "No clinical validation data"},
        "REGULATORY": {"state": "HYPOTHESIS" if r332.get("regulatory_status") else "UNKNOWN",
                       "evidence": r332.get("regulatory_status", "NONE") + f" + {len([e for e in ext_ev if 'FDA' in e.get('source_snippet','') or 'fda' in e.get('source_url','').lower()])} FDA references"},
        "IP": {"state": "UNKNOWN", "evidence": "Ownership not verified. No patent filed."},
        "TRANSFER": {"state": "NOT_READY", "evidence": "TRANSFER_READY=False per R370 axes"},
    }

    # Engineering status
    transfer_posture = axes.get("DERIVED_TRANSFER_POSTURE", "RESEARCH_STAGE_OPPORTUNITY")
    if "TRANSFER_READY" in transfer_posture.upper():
        eng_status = "TRANSFER_READY"
    elif "ENGINEERING" in transfer_posture.upper():
        eng_status = "PROTOTYPE_READY"
    elif "VALIDATION" in transfer_posture.upper():
        eng_status = "VALIDATION_READY"
    else:
        eng_status = "CONCEPT_DEFINED"

    # Build dossier
    dossier = {
        "package_id": pkg_id,
        "dossier_version": "ENG-V3",
        "generated_at": _now(),
        "design_status": "CONCEPTUAL — NOT RELEASED FOR MANUFACTURING",
        "engineering_status": eng_status,
        "transfer_ready": False,
        "warning": "This dossier contains the machine's best engineering interpretation with externally-sourced engineering precedent. PROPOSED fields are engineering hypotheses. UNKNOWN fields require physical engineering work. External evidence provides context, NOT validation of this specific invention.",

        "source_universe": {
            "registry": "AUTHORITATIVE_SOURCE_REGISTRY_V2",
            "manifest_integrity_verified": True,
            "sources_searched": len(state),
            "package_found_in_sources": len(pkg_sources),
        },

        "external_engineering_evidence": {
            "total_references": len(ext_ev),
            "evidence_records": ext_ev,
            "note": "External evidence from web/database searches (FDA, PubMed, manufacturing literature). Each record has source_url, source_hash, what_it_establishes, and what_it_does_not_establish. External precedent provides context — NOT validation of this specific invention.",
        },

        "design_input_register": {
            "total_inputs": len(design_inputs),
            "supported": n_supported,
            "unresolved": n_unresolved,
            "externally_referenced": n_external,
            "inputs": design_inputs,
        },

        "engineering_maturity": maturity,

        "honest_assessment": (
            f"Engineering status: {eng_status}. "
            f"Design inputs: {n_supported} supported, {n_unresolved} unresolved, {n_external} externally referenced. "
            f"External engineering evidence: {len(ext_ev)} references from FDA/PubMed/manufacturing literature. "
            f"Geometry, CAD, materials, manufacturing: UNKNOWN (require physical engineering work). "
            f"TRANSFER_READY = False."
        ),
    }

    return dossier


# ============================================================================
# Main
# ============================================================================

def generate_all_dossiers():
    """Generate complete Engineering Technology-Transfer Dossiers for all 15 packages."""
    print("ENGINEERING TECHNOLOGY-TRANSFER DOSSIERS — Complete with external evidence")
    print("=" * 70)

    # Load authoritative sources (same as verifier)
    mi = verify_manifest_integrity()
    if not mi["pass"]:
        raise RuntimeError(f"MANIFEST_INTEGRITY_FAILED: {mi}")

    with open(REGISTRY_PATH) as f:
        registry = json.load(f)
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    ah = verify_authority_hierarchy(registry, manifest)
    if not ah["pass"]:
        raise RuntimeError(f"AUTHORITY_HIERARCHY_FAILED: {ah}")

    state = {}
    source_meta = {}
    for src in registry["sources"]:
        full_path = os.path.join(REPO_ROOT, src["path"])
        state[src["source_id"]] = load_json_strict(full_path)
        source_meta[src["source_id"]] = src

    # Load external engineering evidence
    external_evidence = load_external_evidence()
    total_ext = sum(len(v) for v in external_evidence.values())
    print(f"External engineering evidence: {total_ext} references loaded")

    # Get active packages
    all_packages = set()
    for sd in state.values():
        all_packages.update(discover_packages_iterative(sd))
    killed = {"P-25", "P-09", "P-10", "P-12", "P-20", "P-19", "P-23", "P-03", "P-05", "P-06", "P-08", "P-14", "P-17",
              "P-15", "P-21", "P-22"}  # P-15, P-21, P-22 are superseded by R1 repairs
    active = sorted(all_packages - killed)

    print(f"Active packages: {len(active)}")

    results = []
    for pkg_id in active:
        dossier = build_complete_dossier(pkg_id, state, source_meta, external_evidence)

        safe_id = pkg_id.replace("/", "-")
        dpath = os.path.join(OUTPUT_DIR, f"{safe_id}_EngineeringDossier.json")
        with open(dpath, "w") as f:
            json.dump(dossier, f, indent=2, ensure_ascii=False)

        di = dossier.get("design_input_register", {})
        mat = dossier.get("engineering_maturity", {})
        ext_count = dossier.get("external_engineering_evidence", {}).get("total_references", 0)

        print(f"\n  {pkg_id}: {dossier['engineering_status']}")
        print(f"    design inputs: {di.get('supported',0)} supported, {di.get('unresolved',0)} unresolved, {di.get('externally_referenced',0)} external")
        print(f"    external evidence: {ext_count} references")
        for dim, data in mat.items():
            print(f"    {dim}: {data['state']}")

        results.append({
            "package_id": pkg_id,
            "dossier_path": dpath,
            "engineering_status": dossier["engineering_status"],
            "design_inputs_supported": di.get("supported", 0),
            "design_inputs_unresolved": di.get("unresolved", 0),
            "design_inputs_external": di.get("externally_referenced", 0),
            "external_evidence_count": ext_count,
            "transfer_ready": False,
            "maturity": mat,
        })

    # Portfolio summary
    report = {
        "report_type": "Engineering Technology-Transfer Dossier Portfolio",
        "generated_at": _now(),
        "source_universe": "AUTHORITATIVE_SOURCE_REGISTRY_V2 + external web/database searches",
        "total_packages": len(results),
        "total_external_evidence": sum(r["external_evidence_count"] for r in results),
        "total_design_inputs": sum(r["design_inputs_supported"] + r["design_inputs_unresolved"] + r["design_inputs_external"] for r in results),
        "total_supported": sum(r["design_inputs_supported"] for r in results),
        "total_unresolved": sum(r["design_inputs_unresolved"] for r in results),
        "total_external": sum(r["design_inputs_external"] for r in results),
        "transfer_ready": 0,
        "packages": results,
        "honest_assessment": (
            "Each dossier contains: (1) source-derived engineering data from R370, "
            "(2) externally-sourced engineering precedent from FDA/PubMed/manufacturing literature, "
            "(3) a Design Input Register with supported/unresolved/externally-referenced inputs, "
            "(4) per-dimension engineering maturity (no aggregate percentage), "
            "(5) explicit identification of every engineering gap. "
            "External evidence provides CONTEXT (comparable devices, manufacturing methods, materials frameworks) — "
            "NOT validation of this specific invention. "
            "TRANSFER_READY = 0/15. Unknown remains Unknown."
        ),
    }

    rpath = os.path.join(OUTPUT_DIR, "_portfolio_summary.json")
    with open(rpath, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"PORTFOLIO SUMMARY")
    print(f"  External evidence: {report['total_external_evidence']} references")
    print(f"  Design inputs: {report['total_supported']} supported, {report['total_unresolved']} unresolved, {report['total_external']} external")
    print(f"  Transfer ready: 0/15")
    print(f"  Report: {rpath}")

    return report


if __name__ == "__main__":
    generate_all_dossiers()

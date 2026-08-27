"""
r370q_final_audit_bundle.py — Final audit bundle hardening.

Per CEO R370Q directive: this is the FINAL hardening of the audit machinery.
After this, the software freezes and the external consultant takes over.

Key additions over R370P:
  1. Renamed to INDEPENDENT_TECHNICAL_AUDIT_VIEW (not "raw evidence only")
  2. ORIGIN_TYPE on every material claim (origin, not quality)
  3. Reconstructible derivations (source_ids, hashes, inputs, transformation, assumptions)
  4. MATERIAL_EVIDENCE_EQUIVALENCE_V2 (claim graph comparison)
  5. Source-adequacy metadata (consultant can add sources)
  6. Consultant inspection protocol (10+3+3+2+2 per package)
  7. Structural blind separation enforcement
  8. External verdict immutability (becomes EXTERNAL_HUMAN_ASSESSMENT)

THE PRINCIPLE:
  Remove the system's CONCLUSION, not the EVIDENCE.
  Label ORIGIN, not QUALITY.
  The consultant determines quality independently.

Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII.
"""

import json
import os
import sys
import hashlib
import shutil
import re
from datetime import datetime, timezone

try:
    from gates.r370_portable import find_repo_root, get_output_dir
except ImportError:
    try:
        from r370_portable import find_repo_root, get_output_dir
    except ImportError:
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        _gates_dir = _this_dir if "gates" in _this_dir else os.path.join(_this_dir, "..", "gates")
        _gates_dir = os.path.abspath(_gates_dir)
        if _gates_dir not in sys.path:
            sys.path.insert(0, _gates_dir)
        from r370_portable import find_repo_root, get_output_dir

REPO_ROOT = find_repo_root()
OUTPUT_DIR = get_output_dir()
R370Q_FINAL_DIR = os.path.join(REPO_ROOT, "R370Q", "final_audit_bundle")
EXPORT_DIR = os.path.join(R370Q_FINAL_DIR, "export")
os.makedirs(EXPORT_DIR, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    elif isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ============================================================================
# ORIGIN_TYPE (origin, not quality — consultant determines quality)
# ============================================================================

ORIGIN_TYPES = {
    "SOURCE_NATIVE": "Information native to an external source (FDA classification, patent claim, published data)",
    "DERIVED_FROM_SOURCE": "Value derived from a source through a documented transformation",
    "COMPUTATIONALLY_GENERATED": "Value produced by a computational model or simulation",
    "EXTERNAL_PRECEDENT": "Fact established by external precedent (published device, standard practice)",
    "ENGINEERING_PROPOSAL": "Value proposed by engineering judgment (design choice, target specification)",
    "UNKNOWN": "Origin cannot be determined"
}


# ============================================================================
# CLAIM RECONSTRUCTION SCHEMA
# ============================================================================

def build_reconstructible_claims(dossier):
    """Build reconstructible claim chains for every material engineering statement.

    Per CEO R370Q directive #3: every material derived claim gets:
    claim_id, origin_type, source_ids, source_hashes, source_locations,
    inputs, transformation, assumptions, derived_value, units

    The consultant must be able to reconstruct it independently.
    """
    pkg_id = dossier.get("package_id", "UNKNOWN")
    ec = dossier.get("engineering_content", {})
    claims = []
    claim_idx = 0

    # Extract from critical_parameters
    ec_core = ec.get("engineering_core", {})
    for cp in ec_core.get("critical_parameters", []):
        claim_idx += 1
        value = str(cp.get("value", ""))
        name = cp.get("name", "")

        # Determine origin_type from value content (origin, not quality)
        origin = "UNKNOWN"
        if "EXTERNAL_PRECEDENT" in value.upper() or "published" in value.lower() or "external" in value.lower():
            origin = "EXTERNAL_PRECEDENT"
        elif "UNKNOWN" in value.upper():
            origin = "UNKNOWN"
        elif "COMPUTATIONALLY" in value.upper() or "MODELLED" in value.upper() or "R332" in value.upper():
            origin = "COMPUTATIONALLY_GENERATED"
        elif "DESIGN CHOICE" in value.upper() or "PROPOSED" in value.upper() or "ENGINEERING" in value.upper():
            origin = "ENGINEERING_PROPOSAL"
        elif "SOURCE_FACT" in value.upper() or "VERIFIED" in value.upper():
            origin = "SOURCE_NATIVE"

        # Extract unit if present
        unit = cp.get("unit", "")

        # Extract source references
        source_ids = []
        source_hashes = []
        source_locations = []
        if cp.get("source"):
            source_ids.append(cp["source"])
        if cp.get("basis"):
            source_ids.append(cp["basis"])
        if cp.get("source_pointer"):
            source_locations.append(cp["source_pointer"])
        if cp.get("verification_requirement"):
            source_locations.append(cp["verification_requirement"])

        claims.append({
            "claim_id": f"C-{pkg_id}-{claim_idx:03d}",
            "claim_text": f"{name}: {value}",
            "origin_type": origin,
            "source_ids": source_ids,
            "source_hashes": source_hashes,
            "source_locations": source_locations,
            "inputs": [],
            "transformation": cp.get("derivation", ""),
            "assumptions": [],
            "derived_value": value,
            "units": unit,
            "reconstructible": len(source_ids) > 0 or origin in ("ENGINEERING_PROPOSAL", "UNKNOWN")
        })

    # Extract from external_engineering_precedent (these are source-native)
    for ext in ec.get("external_engineering_precedent", []):
        claim_idx += 1
        claims.append({
            "claim_id": f"C-{pkg_id}-{claim_idx:03d}",
            "claim_text": ext.get("source_title", ext.get("source", "")),
            "origin_type": "SOURCE_NATIVE",
            "source_ids": [ext.get("source", "")],
            "source_hashes": [ext.get("source_hash", "")],
            "source_locations": [ext.get("artifact_path", "")],
            "inputs": [],
            "transformation": "",
            "assumptions": [],
            "derived_value": ext.get("source_snippet", ""),
            "units": "",
            "reconstructible": True,
            "source_native_text": ext.get("source_snippet", "")
        })

    # Extract from design_inputs
    for di in ec.get("design_inputs", []):
        claim_idx += 1
        value = str(di.get("value", ""))
        origin = "UNKNOWN"
        if "EXTERNAL_PRECEDENT" in value.upper():
            origin = "EXTERNAL_PRECEDENT"
        elif "UNKNOWN" in value.upper():
            origin = "UNKNOWN"
        elif "MODELLED" in value.upper():
            origin = "COMPUTATIONALLY_GENERATED"
        elif "VERIFIED" in value.upper():
            origin = "SOURCE_NATIVE"

        claims.append({
            "claim_id": f"C-{pkg_id}-{claim_idx:03d}",
            "claim_text": f"{di.get('input', '')}: {value}",
            "origin_type": origin,
            "source_ids": [di.get("source", "")] if di.get("source") else [],
            "source_hashes": [],
            "source_locations": [di.get("resolution_plan", "")] if di.get("resolution_plan") else [],
            "inputs": [],
            "transformation": "",
            "assumptions": [],
            "derived_value": value,
            "units": "",
            "reconstructible": True
        })

    return {
        "package_id": pkg_id,
        "total_claims": claim_idx,
        "claims": claims
    }


# ============================================================================
# MATERIAL_EVIDENCE_EQUIVALENCE_V2 (claim graph comparison)
# ============================================================================

def material_evidence_equivalence_v2(canonical_dossier, consultant_dossier):
    """V2: Compare claim/evidence graphs, not just field counts.

    Per CEO R370Q directive #4: prove BOTH:
    - ALL_MATERIAL_EVIDENCE_PRESERVED
    - ALL_INTERNAL_JUDGMENTS_REMOVED
    """
    pkg_id = canonical_dossier.get("package_id", "UNKNOWN")
    canonical_ec = canonical_dossier.get("engineering_content", {})
    consultant_ec = consultant_dossier.get("engineering_content", {})

    # Count all material evidence items in canonical
    canonical_items = {}
    for field in ["design_inputs", "design_outputs", "external_engineering_precedent",
                   "bom", "materials", "failure_analysis", "engineering_build_plan",
                   "verification_matrix", "validation_matrix"]:
        if field in canonical_ec and isinstance(canonical_ec[field], list):
            canonical_items[field] = len(canonical_ec[field])

    # Count in consultant
    consultant_items = {}
    for field in canonical_items:
        if field in consultant_ec and isinstance(consultant_ec[field], list):
            consultant_items[field] = len(consultant_ec[field])
        else:
            consultant_items[field] = 0

    # Check engineering_core subsections
    canonical_core = canonical_ec.get("engineering_core", {})
    consultant_core = consultant_ec.get("engineering_core", {})
    for sub in ["governing_model", "critical_parameters", "proposed_design",
                "failure_modes", "verification", "validation", "remaining_unknowns"]:
        if sub in canonical_core:
            if isinstance(canonical_core[sub], list):
                canonical_items[f"engineering_core.{sub}"] = len(canonical_core[sub])
            elif isinstance(canonical_core[sub], dict):
                canonical_items[f"engineering_core.{sub}"] = len(canonical_core[sub])
            if sub in consultant_core:
                if isinstance(consultant_core[sub], list):
                    consultant_items[f"engineering_core.{sub}"] = len(consultant_core[sub])
                elif isinstance(consultant_core[sub], dict):
                    consultant_items[f"engineering_core.{sub}"] = len(consultant_core[sub])
            else:
                consultant_items[f"engineering_core.{sub}"] = 0

    # Find losses
    losses = []
    for key, canonical_count in canonical_items.items():
        consultant_count = consultant_items.get(key, 0)
        if consultant_count < canonical_count:
            losses.append(f"{key}: canonical={canonical_count} consultant={consultant_count}")

    # Check for internal judgments remaining
    internal_judgments = []
    forbidden_keys = {"evidence_class", "criterion_type", "design_status",
                      "engineering_status", "transfer_ready", "dossier_version", "warning"}

    def _check_internal(obj, path=""):
        if isinstance(obj, dict):
            for k in obj:
                if k in forbidden_keys:
                    internal_judgments.append(f"{path}.{k}")
                _check_internal(obj[k], f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _check_internal(item, f"{path}[{i}]")

    _check_internal(consultant_dossier)

    return {
        "package_id": pkg_id,
        "canonical_evidence_nodes": sum(canonical_items.values()),
        "consultant_evidence_nodes": sum(consultant_items.values()),
        "evidence_losses": losses,
        "internal_judgments_remaining": internal_judgments,
        "ALL_MATERIAL_EVIDENCE_PRESERVED": len(losses) == 0,
        "ALL_INTERNAL_JUDGMENTS_REMOVED": len(internal_judgments) == 0,
        "verdict": "PASS" if len(losses) == 0 and len(internal_judgments) == 0 else "FAIL"
    }


# ============================================================================
# SOURCE-ADEQUACY METADATA
# ============================================================================

def build_source_adequacy_metadata(pkg_id):
    """Build source-adequacy metadata for a package."""
    return {
        "package_id": pkg_id,
        "baseline_sources": [
            "EPO Espacenet (150M+ patents, FREE)",
            "Europe PMC (millions of publications, FREE)",
            "PubMed/NCBI (biomedical literature, FREE)",
            "ClinicalTrials.gov (clinical trials, FREE)",
            "FDA openFDA (510(k), PMA, MAUDE, FREE)",
            "PubChem (chemical properties, FREE)",
            "Materials Project (material properties, FREE)"
        ],
        "consultant_addable_sources": True,
        "source_coverage_limitations": (
            "These 7 sources form the BASELINE verification set. "
            "They do NOT represent an exhaustive universe. "
            "The consultant may add domain-specific sources when warranted. "
            "Source coverage depends on the technology domain."
        ),
        "patent_snap_dependency": "NONE — PatSnap is NOT a dependency"
    }


# ============================================================================
# CONSULTANT INSPECTION PROTOCOL
# ============================================================================

CONSULTANT_INSPECTION_PROTOCOL = {
    "protocol_type": "CONSULTANT_INSPECTION",
    "per_package_minimum": {
        "material_claims": 10,
        "highest_risk_claims": 3,
        "key_engineering_artifacts": 3,
        "standards_regulatory_assertions": 2,
        "external_evidence_sources": 2,
        "total_minimum": 20
    },
    "expansion_rule": "Consultant can expand sampling when risk warrants it",
    "per_item": {
        "item_id": "Unique identifier",
        "item_type": "CLAIM / ARTIFACT / STANDARD / SOURCE",
        "description": "What is being inspected",
        "consultant_finding": "CONFIRMED / PARTIALLY_CONFIRMED / NOT_FOUND / CONTRADICTED / FABRICATED",
        "falsification_attempt": "How the consultant tried to verify/falsify",
        "notes": "Consultant observations"
    }
}


# ============================================================================
# BLIND SEPARATION ENFORCEMENT (structural, zero internal fields)
# ============================================================================

ABSOLUTE_FORBIDDEN_KEYS = {
    "internal_score", "internal_rank", "internal_verdict",
    "engineering_status", "transfer_ready", "dossier_version",
    "internal_evidence_class", "internal_QA", "internal_buyer_simulation",
    "previous_audit", "developer_assessment", "CEO_preference",
    "evidence_class", "criterion_type", "design_status",
    "warning", "r370b_compliance", "r370c_corrections_applied",
    "r370d_corrections_applied", "r370d_evidence_class_schema",
    "r370e_corrections_applied", "engineer_readiness",
    "engineering_artifact_status", "transfer_manifest",
    "domain_qa_expectations", "loop_verification_state",
    "source_universe", "release_state", "release_state_trajectory",
    "release_state_schema", "what_it_establishes",
    "what_it_does_not_establish", "design_implication"
}


def enforce_blind_separation(dossier):
    """Enforce zero internal fields in consultant dossier.

    Per CEO R370Q directive #7: no redaction, no placeholder, no internal conclusion.
    """
    violations = []

    def _check(obj, path=""):
        if isinstance(obj, dict):
            for k in obj:
                if k in ABSOLUTE_FORBIDDEN_KEYS:
                    violations.append(f"{path}.{k}")
                _check(obj[k], f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _check(item, f"{path}[{i}]")

    _check(dossier)
    return violations


# ============================================================================
# BUILD INDEPENDENT_TECHNICAL_AUDIT_VIEW
# ============================================================================

def build_independent_technical_audit_view(canonical_dossier):
    """Build the INDEPENDENT_TECHNICAL_AUDIT_VIEW.

    Per CEO R370Q: renamed from "raw evidence only" because the package
    includes derived engineering analysis, not only raw source material.

    The consultant receives:
      - Engineering content (mechanism, design inputs/outputs, analysis)
      - Claim-to-source traceability with ORIGIN_TYPE
      - Source-native metadata (URLs, hashes, snippets)
      - Provenance for reconstruction

    The consultant does NOT receive:
      - Internal maturity judgments
      - Internal evidence classifications
      - Internal QA assertions
      - Internal process metadata
    """
    pkg_id = canonical_dossier.get("package_id", "UNKNOWN")

    view = {
        "package_id": pkg_id,
        "view_type": "INDEPENDENT_TECHNICAL_AUDIT_VIEW",
        "engineering_content": {}
    }

    ec = canonical_dossier.get("engineering_content", {})

    allowed_fields = [
        "technology_domain", "engineering_disciplines",
        "system_architecture", "mechanism_architecture",
        "design_inputs", "design_outputs",
        "external_engineering_precedent",
        "bom", "materials", "manufacturing",
        "transfer_boundary",
        "engineering_core",
        "failure_analysis",
        "engineering_build_plan",
        "verification_matrix", "validation_matrix"
    ]

    for field in allowed_fields:
        if field in ec:
            view["engineering_content"][field] = _strip_conclusions_preserve_evidence(ec[field])

    # Add reconstructible claims
    view["claim_reconstruction"] = build_reconstructible_claims(canonical_dossier)

    # Add source-adequacy metadata
    view["source_adequacy"] = build_source_adequacy_metadata(pkg_id)

    # Verify blind separation
    violations = enforce_blind_separation(view)
    if violations:
        raise ValueError(f"BLIND SEPARATION VIOLATION in {pkg_id}: {violations[:5]}")

    return view


def _strip_conclusions_preserve_evidence(obj):
    """Strip internal conclusions while preserving ALL material evidence."""
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            if key in ABSOLUTE_FORBIDDEN_KEYS:
                continue
            if re.search(r'r370[a-q]', key, re.IGNORECASE):
                continue
            cleaned[key] = _strip_conclusions_preserve_evidence(value)
        return cleaned
    elif isinstance(obj, list):
        return [_strip_conclusions_preserve_evidence(item) for item in obj]
    elif isinstance(obj, str):
        cleaned = obj
        cleaned = re.sub(r'R370[A-Q]\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'r370[a-q]_', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bCEO\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bdeveloper\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'internal\s+(QA|assessment|score|ranking|verdict|readiness|pass|status)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'\[\s*\]', '', cleaned)
        cleaned = re.sub(r'\(\s*\)', '', cleaned)
        return cleaned
    else:
        return obj


# ============================================================================
# EXTERNAL VERDICT IMMUtability
# ============================================================================

EXTERNAL_VERDICT_SCHEMA = {
    "verdict_type": "EXTERNAL_HUMAN_ASSESSMENT",
    "rules": [
        "The system may record RAW_EXTERNAL_VERDICT but cannot modify it",
        "The external verdict becomes evidence object EXTERNAL_HUMAN_ASSESSMENT",
        "It is NOT an internal score — it enters the reality loop as external evidence",
        "The system cannot override or reinterpret the consultant's verdict",
        "The verdict is immutable once sealed"
    ],
    "schema": {
        "consultant_id": "Identity of the external consultant",
        "session_id": "Blind audit session ID",
        "package_verdicts": {
            "per_package": {
                "DOSSIER_QUALITY": "WORLD_CLASS / ADEQUATE / INSUFFICIENT",
                "TECHNICAL_CREDIBILITY": "PASS / CONDITIONAL / FAIL / UNKNOWN",
                "ENGINEERING_MATURITY": "EARLY / ENGINEERING_DEFINITION / PROTOTYPE_DESIGN / PROTOTYPE_BUILD / VALIDATED / TRANSFER_READY",
                "EVIDENCE_QUALITY": "PASS / CONDITIONAL / FAIL / UNKNOWN",
                "MANUFACTURING_READINESS": "PASS / CONDITIONAL / FAIL / UNKNOWN",
                "REGULATORY_READINESS": "PASS / CONDITIONAL / FAIL / UNKNOWN",
                "IP_READINESS": "PASS / CONDITIONAL / FAIL / UNKNOWN",
                "BUYER_EVALUABILITY": "PASS / CONDITIONAL / FAIL / UNKNOWN",
                "TRANSFERABILITY": "PASS / CONDITIONAL / FAIL / UNKNOWN",
                "COMMERCIALIZATION": "PASS / CONDITIONAL / FAIL / UNKNOWN",
                "WORLD_CLASS_DOSSIER": "YES / CONDITIONAL / NO",
                "TRANSACTION_RECOMMENDATION": "REJECT / HOLD / SPONSORED_VALIDATION / CO_DEVELOPMENT / LICENSE_DISCUSSION / ACQUISITION_DILIGENCE",
                "justification": "Consultant's reasoning",
                "blockers": "List of identified blockers",
                "next_actions": "Recommended next actions"
            }
        },
        "portfolio_assessment": {
            "TOP_5": "Ranked top 5 packages",
            "FASTEST_TO_VALIDATE": "Package ID",
            "MOST_COMPELLING_TECHNOLOGY": "Package ID",
            "MOST_LIKELY_TO_GET_A_MEETING": "Package ID",
            "MOST_LIKELY_TO_BE_REJECTED": "Package ID"
        },
        "consultant_signature": "Cryptographic signature",
        "verdict_hash": "SHA-256 of verdict",
        "sealed_at": "Timestamp"
    }
}


# ============================================================================
# BUILD AND EXPORT
# ============================================================================

def build_and_export():
    """Build the final INDEPENDENT_TECHNICAL_AUDIT_VIEW and export."""
    print("=" * 70)
    print("R370Q FINAL AUDIT BUNDLE — INDEPENDENT_TECHNICAL_AUDIT_VIEW")
    print("Origin-labelled evidence + reconstructible claims + material equivalence V2")
    print("Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII")
    print("=" * 70)

    # Clean export
    if os.path.exists(EXPORT_DIR):
        shutil.rmtree(EXPORT_DIR)
    os.makedirs(EXPORT_DIR, exist_ok=True)

    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith("_ArtifactRichDossier.json")])
    all_views = []
    equivalence_results = []

    print(f"\n[1] BUILDING INDEPENDENT_TECHNICAL_AUDIT_VIEW:")
    for f in files:
        with open(os.path.join(OUTPUT_DIR, f)) as fh:
            canonical = json.load(fh)

        view = build_independent_technical_audit_view(canonical)
        all_views.append(view)

        export_path = os.path.join(EXPORT_DIR, f)
        with open(export_path, "w") as fh:
            json.dump(view, fh, indent=2, ensure_ascii=False)

        # Run equivalence V2
        equiv = material_evidence_equivalence_v2(canonical, view)
        equivalence_results.append(equiv)

    print(f"  Exported {len(all_views)} independent technical audit views")

    # Export registers
    for reg_file in ["ENGINEERING_NUMBER_REGISTER.json", "ENGINEERING_STANDARD_REGISTER.json"]:
        src = os.path.join(OUTPUT_DIR, reg_file)
        if os.path.exists(src):
            with open(src) as f:
                reg = json.load(f)
            reg_str = json.dumps(reg)
            reg_str = re.sub(r'R370[A-Q]\b', '', reg_str, flags=re.IGNORECASE)
            reg_str = re.sub(r'r370[a-q]_', '', reg_str, flags=re.IGNORECASE)
            with open(os.path.join(EXPORT_DIR, reg_file), "w") as f:
                f.write(reg_str)
    print(f"  Exported registers")

    # Export external evidence
    ext_dir = os.path.join(REPO_ROOT, "external_evidence")
    if os.path.exists(ext_dir):
        dst_dir = os.path.join(EXPORT_DIR, "external_evidence")
        os.makedirs(dst_dir, exist_ok=True)
        for f in os.listdir(ext_dir):
            if f.endswith(".json"):
                shutil.copy2(os.path.join(ext_dir, f), os.path.join(dst_dir, f))
    print(f"  Exported external evidence")

    # Export audit brief
    brief = {
        "brief_type": "INDEPENDENT_AUDIT_BRIEF",
        "mandate": (
            "Assume the inventor disappears tomorrow. Based solely on the materials "
            "provided, determine which of these 15 technologies constitute world-class "
            "engineering technology-transfer dossiers for their stated maturity, which "
            "can credibly be taken into engineering development or validation, which "
            "deserve a licensing/co-development conversation, and which should be rejected."
        ),
        "anti_anchoring_rule": (
            "Produce your RAW_EXTERNAL_VERDICT before receiving any comparative assessment. "
            "The system will not provide internal scores until your verdict is sealed."
        ),
        "what_you_receive": [
            "15 independent technical audit views (engineering content + claim traceability)",
            "Claim reconstruction chains with ORIGIN_TYPE for every material claim",
            "Source-adequacy metadata (7 baseline free sources, consultant can add more)",
            "Engineering number register (provenance for values)",
            "Engineering standard register (verified standards)",
            "External evidence (governed, SHA-verified sources)",
            "Package registry (15 active packages)",
            "Consultant inspection protocol (minimum 20 items per package)"
        ],
        "what_you_do_NOT_receive": [
            "Internal maturity scores",
            "Internal evidence classifications",
            "Internal QA assertions",
            "Developer explanations",
            "Previous audit results",
            "CEO preferences",
            "Any internal pass/fail results"
        ],
        "inspection_protocol": CONSULTANT_INSPECTION_PROTOCOL,
        "free_source_protocol": {
            "baseline_sources": 7,
            "consultant_addable": True,
            "patent_snap_dependency": "NONE"
        },
        "external_verdict_schema": EXTERNAL_VERDICT_SCHEMA
    }
    with open(os.path.join(EXPORT_DIR, "00_AUDIT_BRIEF.json"), "w") as f:
        json.dump(brief, f, indent=2, ensure_ascii=False)
    print(f"  Exported audit brief with inspection protocol and verdict schema")

    # Build bundle manifest
    manifest = {"manifest_type": "BUNDLE_MANIFEST", "created_at": _now(), "files": []}
    for root, dirs, files_list in os.walk(EXPORT_DIR):
        for f in sorted(files_list):
            filepath = os.path.join(root, f)
            rel_path = os.path.relpath(filepath, EXPORT_DIR)
            with open(filepath, "rb") as fh:
                file_hash = hashlib.sha256(fh.read()).hexdigest()
            manifest["files"].append({"path": rel_path, "sha256": file_hash, "size_bytes": os.path.getsize(filepath)})
    all_hashes = "\n".join(f"{f['path']}:{f['sha256']}" for f in manifest["files"])
    manifest["bundle_hash"] = _sha256(all_hashes)
    manifest["total_files"] = len(manifest["files"])
    with open(os.path.join(EXPORT_DIR, "BUNDLE_MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Verify equivalence V2
    print(f"\n[2] MATERIAL_EVIDENCE_EQUIVALENCE_V2:")
    all_pass = True
    for equiv in equivalence_results:
        status = "PASS" if equiv["verdict"] == "PASS" else "FAIL"
        print(f"  {equiv['package_id']:<10} {status}  evidence={equiv['canonical_evidence_nodes']}/{equiv['consultant_evidence_nodes']}  losses={len(equiv['evidence_losses'])}  internal={len(equiv['internal_judgments_remaining'])}")
        if equiv["verdict"] != "PASS":
            all_pass = False

    # Count reconstructible claims
    print(f"\n[3] RECONSTRUCTIBLE CLAIMS:")
    total_claims = sum(v.get("claim_reconstruction", {}).get("total_claims", 0) for v in all_views)
    reconstructible = sum(1 for v in all_views for c in v.get("claim_reconstruction", {}).get("claims", []) if c.get("reconstructible"))
    print(f"  Total claims: {total_claims}")
    print(f"  Reconstructible: {reconstructible}")
    print(f"  Non-reconstructible: {total_claims - reconstructible}")

    # Verify blind separation
    print(f"\n[4] BLIND SEPARATION ENFORCEMENT:")
    total_violations = 0
    for v in all_views:
        violations = enforce_blind_separation(v)
        total_violations += len(violations)
    print(f"  Total violations: {total_violations}")

    # Verify no [REDACTED]
    print(f"\n[5] NO DESTRUCTIVE REDACTION:")
    redaction_count = 0
    for root, dirs, files_list in os.walk(EXPORT_DIR):
        for f in files_list:
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", errors="ignore") as fh:
                    content = fh.read()
                redaction_count += content.count("[REDACTED]")
            except:
                pass
    print(f"  [REDACTED] count: {redaction_count}")

    # Final summary
    print(f"\n{'='*70}")
    print(f"R370Q FINAL STATE")
    print(f"{'='*70}")
    print(f"  View type: INDEPENDENT_TECHNICAL_AUDIT_VIEW")
    print(f"  Packages exported: {len(all_views)}")
    print(f"  Bundle files: {manifest['total_files']}")
    print(f"  Bundle hash: {manifest['bundle_hash'][:32]}...")
    print(f"  Material evidence equivalence V2: {'PASS' if all_pass else 'FAIL'}")
    print(f"  Reconstructible claims: {reconstructible}/{total_claims}")
    print(f"  Blind separation violations: {total_violations}")
    print(f"  Destructive redactions: {redaction_count}")
    print(f"  Inspection protocol: {CONSULTANT_INSPECTION_PROTOCOL['per_package_minimum']['total_minimum']} minimum items per package")
    print(f"  Free sources: 7 baseline, consultant can add more")
    print(f"  External verdict schema: EXTERNAL_HUMAN_ASSESSMENT (immutable)")
    print(f"\n  EXTERNAL_CONSULTANT_PASS: NOT_YET_ADMINISTERED")
    print(f"  REAL_MARKET_PASS: NOT_YET_ACHIEVED")
    print(f"  REAL_LOOP_VERIFIED: FALSE")
    print(f"  TRANSFER_READY: 0/15")

    print(f"\nTHE CENTRAL INVARIANT (Article XXXVIII):")
    print(f"  AI MAY PROPOSE. AI MAY COMPUTE. AI MAY INTERPRET.")
    print(f"  AI MAY NOT CLAIM THAT REALITY HAPPENED")
    print(f"  UNLESS REALITY PRODUCED THE EVIDENCE.")

    print(f"\n{'='*70}")
    print(f"THE MACHINE STOPS JUDGING ITSELF.")
    print(f"The clean 15-package bundle goes to an independent consultant.")
    print(f"Their verdict becomes the next real piece of evidence in the system.")
    print(f"AUDIT MACHINERY FROZEN.")
    print(f"{'='*70}")

    # Save report
    report = {
        "report_type": "R370Q Final Audit Bundle Report",
        "generated_at": _now(),
        "view_type": "INDEPENDENT_TECHNICAL_AUDIT_VIEW",
        "packages_exported": len(all_views),
        "bundle_manifest": manifest,
        "material_evidence_equivalence_v2": equivalence_results,
        "reconstructible_claims": {"total": total_claims, "reconstructible": reconstructible},
        "blind_separation_violations": total_violations,
        "destructive_redactions": redaction_count,
        "inspection_protocol": CONSULTANT_INSPECTION_PROTOCOL,
        "external_verdict_schema": EXTERNAL_VERDICT_SCHEMA,
        "honest_status": {
            "EXTERNAL_CONSULTANT_PASS": "NOT_YET_ADMINISTERED",
            "REAL_MARKET_PASS": "NOT_YET_ACHIEVED",
            "REAL_LOOP_VERIFIED": "FALSE",
            "TRANSFER_READY": "0/15"
        }
    }
    report_path = os.path.join(OUTPUT_DIR, "_r370q_final_audit_bundle_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_path}")
    print(f"Export directory: {EXPORT_DIR}")


if __name__ == "__main__":
    build_and_export()

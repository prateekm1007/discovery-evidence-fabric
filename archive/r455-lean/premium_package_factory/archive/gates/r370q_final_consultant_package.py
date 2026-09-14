"""
r370q_final_consultant_package.py — Final blind consultant package with evidence traceability.

Per CEO R370Q directive: ensure the consultant gets ALL material technical
evidence but NONE of our conclusions about that evidence.

Key principle:
  Remove the system's CONCLUSION, not the EVIDENCE that permits the
  consultant to reach the conclusion.

Architecture:
  CANONICAL_RECORD (full, with internal state)
      ↓
  TECHNICAL_EVIDENCE_VIEW (all material technical evidence, no internal judgments)
      ↓
  CONSULTANT_VIEW (raw evidence + provenance + claim-to-source traceability)

New additions:
  1. evidence_origin field (SOURCE_NATIVE / DERIVED_FROM_SOURCE / COMPUTATIONALLY_GENERATED / ENGINEERING_PROPOSAL / EXTERNAL_PRECEDENT / UNKNOWN)
  2. claim-to-source traceability (claim_id, source_artifact, source_hash, transformation, inputs, derived_value, assumptions)
  3. material-evidence equivalence test (NO_MATERIAL_EVIDENCE_LOSS)
  4. source-native vs internal metadata separation
  5. inventor-disappearance test (PENDING_EXTERNAL — not self-certified)
  6. free-source verification protocol
  7. immutable bundle (hash, receipt, signature)
  8. final state machine

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
R370Q_DIR = os.path.join(REPO_ROOT, "R370Q", "final_consultant_package")
EXPORT_DIR = os.path.join(R370Q_DIR, "export")
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
# EVIDENCE ORIGIN CLASSIFICATION (describes WHERE evidence came from, NOT our evaluation)
# ============================================================================

EVIDENCE_ORIGIN = {
    "SOURCE_NATIVE": "Information that is native to an external source (FDA classification, patent claim, published study data)",
    "DERIVED_FROM_SOURCE": "Value derived from a source through a documented transformation (parameter extraction, unit conversion)",
    "COMPUTATIONALLY_GENERATED": "Value produced by a computational model (simulation, numerical analysis)",
    "ENGINEERING_PROPOSAL": "Value proposed by engineering judgment without external source (design choice, target specification)",
    "EXTERNAL_PRECEDENT": "Fact established by external precedent (published device, standard practice)",
    "UNKNOWN": "Origin cannot be determined"
}


# ============================================================================
# CLAIM-TO-SOURCE TRACEABILITY
# ============================================================================

def build_claim_traceability(dossier):
    """Build claim-to-source traceability for material engineering statements.

    Per CEO R370Q directive #3: every material engineering statement gets:
    claim_id, source_artifact, source_hash, source_location, source_native_text,
    transformation, inputs, derived_value, assumptions
    """
    pkg_id = dossier.get("package_id", "UNKNOWN")
    ec = dossier.get("engineering_content", {})
    claims = []
    claim_count = 0

    # Extract claims from critical_parameters
    ec_core = ec.get("engineering_core", {})
    for cp in ec_core.get("critical_parameters", []):
        claim_count += 1
        value = cp.get("value", "")
        name = cp.get("name", "")

        # Determine evidence_origin based on value content
        origin = "UNKNOWN"
        if isinstance(value, str):
            if "EXTERNAL_PRECEDENT" in value.upper() or "published" in value.lower():
                origin = "EXTERNAL_PRECEDENT"
            elif "UNKNOWN" in value.upper():
                origin = "UNKNOWN"
            elif "MODELLED" in value.upper() or "COMPUTATIONALLY" in value.upper():
                origin = "COMPUTATIONALLY_GENERATED"
            elif "DESIGN CHOICE" in value.upper() or "PROPOSED" in value.upper():
                origin = "ENGINEERING_PROPOSAL"
            elif "SOURCE_FACT" in value.upper():
                origin = "SOURCE_NATIVE"

        claims.append({
            "claim_id": f"C-{pkg_id}-{claim_count:03d}",
            "claim_text": f"{name}: {value}",
            "evidence_origin": origin,
            "source_artifact": cp.get("source", cp.get("basis", "UNKNOWN")),
            "source_hash": cp.get("source_hash", ""),
            "source_location": cp.get("source_pointer", cp.get("verification_requirement", "")),
            "source_native_text": "",
            "transformation": cp.get("derivation", ""),
            "inputs": [],
            "derived_value": value,
            "assumptions": []
        })

    # Extract claims from external_engineering_precedent
    for ext in ec.get("external_engineering_precedent", []):
        claim_count += 1
        claims.append({
            "claim_id": f"C-{pkg_id}-{claim_count:03d}",
            "claim_text": ext.get("what_it_establishes", ""),
            "evidence_origin": "SOURCE_NATIVE",
            "source_artifact": ext.get("source", ""),
            "source_hash": ext.get("source_hash", ""),
            "source_location": ext.get("artifact_path", ""),
            "source_native_text": ext.get("source_snippet", ""),
            "transformation": "",
            "inputs": [],
            "derived_value": "",
            "assumptions": []
        })

    return {
        "package_id": pkg_id,
        "total_claims": claim_count,
        "claims": claims
    }


# ============================================================================
# MATERIAL-EVIDENCE EQUIVALENCE TEST
# ============================================================================

def material_evidence_equivalence_test(canonical_dossier, consultant_dossier):
    """Prove that removing internal conclusions did NOT remove material technical evidence.

    Per CEO R370Q directive #6: compare canonical material evidence nodes
    against consultant material evidence nodes.

    Required: NO_MATERIAL_EVIDENCE_LOSS
    """
    pkg_id = canonical_dossier.get("package_id", "UNKNOWN")
    canonical_ec = canonical_dossier.get("engineering_content", {})
    consultant_ec = consultant_dossier.get("engineering_content", {})

    # Fields that ARE material technical evidence (must be preserved)
    material_fields = [
        "technology_domain",
        "engineering_disciplines",
        "system_architecture",
        "mechanism_architecture",
        "design_inputs",
        "design_outputs",
        "external_engineering_precedent",
        "bom",
        "materials",
        "manufacturing",
        "transfer_boundary",
        "engineering_core",
        "failure_analysis",
        "engineering_build_plan",
        "verification_matrix",
        "validation_matrix"
    ]

    missing_fields = []
    for field in material_fields:
        if field in canonical_ec and field not in consultant_ec:
            missing_fields.append(field)

    # Check that engineering_core subsections are preserved
    canonical_core = canonical_ec.get("engineering_core", {})
    consultant_core = consultant_ec.get("engineering_core", {})
    core_fields = ["governing_model", "critical_parameters", "external_precedent",
                   "proposed_design", "failure_modes", "verification", "validation",
                   "remaining_unknowns"]
    missing_core = [f for f in core_fields if f in canonical_core and f not in consultant_core]

    # Count material evidence nodes (items in lists)
    canonical_nodes = 0
    consultant_nodes = 0
    for field in material_fields:
        if field in canonical_ec:
            val = canonical_ec[field]
            if isinstance(val, list):
                canonical_nodes += len(val)
            elif isinstance(val, dict):
                canonical_nodes += len(val)
        if field in consultant_ec:
            val = consultant_ec[field]
            if isinstance(val, list):
                consultant_nodes += len(val)
            elif isinstance(val, dict):
                consultant_nodes += len(val)

    evidence_loss = len(missing_fields) > 0 or len(missing_core) > 0

    return {
        "package_id": pkg_id,
        "material_fields_present": len(material_fields) - len(missing_fields),
        "material_fields_total": len(material_fields),
        "missing_fields": missing_fields,
        "missing_core_fields": missing_core,
        "canonical_evidence_nodes": canonical_nodes,
        "consultant_evidence_nodes": consultant_nodes,
        "NO_MATERIAL_EVIDENCE_LOSS": not evidence_loss,
        "verdict": "PASS" if not evidence_loss else "FAIL"
    }


# ============================================================================
# SOURCE-NATIVE vs INTERNAL METADATA SEPARATION
# ============================================================================

SOURCE_NATIVE_FIELDS = {
    # Fields that are native to external sources (must be preserved)
    "source", "source_title", "source_snippet", "source_hash",
    "raw_content_sha256", "artifact_path", "url", "title", "snippet",
    "date", "host_name", "rank"
}

INTERNAL_EVALUATION_FIELDS = {
    # Fields that are our internal conclusions (must be excluded)
    "evidence_class", "criterion_type", "engineering_status", "design_status",
    "transfer_ready", "dossier_version", "warning", "what_it_establishes",
    "what_it_does_not_establish", "design_implication"
}


def classify_field_as_source_native_or_internal(field_name):
    """Classify a field as source-native metadata or internal evaluation metadata."""
    if field_name in SOURCE_NATIVE_FIELDS:
        return "SOURCE_NATIVE"
    elif field_name in INTERNAL_EVALUATION_FIELDS:
        return "INTERNAL_EVALUATION"
    else:
        return "ENGINEERING_CONTENT"  # neutral engineering content


# ============================================================================
# BUILD CONSULTANT VIEW WITH EVIDENCE TRACEABILITY
# ============================================================================

def build_consultant_view_with_traceability(canonical_dossier):
    """Build the final consultant view with evidence traceability.

    Per CEO R370Q: remove the system's CONCLUSION, not the EVIDENCE.

    The consultant receives:
      - Raw technical evidence (mechanism, design inputs/outputs, etc.)
      - Claim-to-source traceability (for every material claim)
      - Source-native metadata (FDA classification, patent claims, published data)
      - Provenance (source URLs, hashes, retrieval dates)

    The consultant does NOT receive:
      - Internal maturity judgments (engineering_status, transfer_ready)
      - Internal evidence classifications (evidence_class)
      - Internal QA assertions (warning)
      - Internal process metadata (R370B-R370Q, dossier_version)
    """
    pkg_id = canonical_dossier.get("package_id", "UNKNOWN")

    # Start with the R370P raw evidence view
    raw_view = {
        "package_id": pkg_id,
        "engineering_content": {}
    }

    ec = canonical_dossier.get("engineering_content", {})

    # Export engineering fields (preserving ALL evidence, removing only conclusions)
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
            raw_view["engineering_content"][field] = _deep_strip_conclusions_preserve_evidence(ec[field])

    # Add claim-to-source traceability
    traceability = build_claim_traceability(canonical_dossier)
    raw_view["claim_traceability"] = traceability

    return raw_view


def _deep_strip_conclusions_preserve_evidence(obj):
    """Strip internal conclusions while preserving ALL material evidence.

    Per CEO R370Q: remove the system's CONCLUSION, not the EVIDENCE.

    Removes:
      - evidence_class (our epistemic classification)
      - criterion_type (our threshold classification)
      - design_status (our maturity label)
      - what_it_establishes / what_it_does_not_establish (our interpretation of precedent)
      - design_implication (our engineering implication)

    PRESERVES:
      - source, source_title, source_snippet, source_hash (source-native metadata)
      - raw_content_sha256, artifact_path (provenance)
      - All engineering content (equations, parameters, failure modes, etc.)
      - All design inputs/outputs (values, units, descriptions)
    """
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            # Skip internal conclusion fields
            if key in ("evidence_class", "criterion_type", "design_status",
                       "what_it_establishes", "what_it_does_not_establish",
                       "design_implication"):
                continue
            # Skip internal round references in keys
            if re.search(r'r370[a-q]', key, re.IGNORECASE):
                continue
            # PRESERVE source-native metadata and all engineering content
            cleaned[key] = _deep_strip_conclusions_preserve_evidence(value)
        return cleaned
    elif isinstance(obj, list):
        return [_deep_strip_conclusions_preserve_evidence(item) for item in obj]
    elif isinstance(obj, str):
        # Remove internal round references from string values
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
# INVENTOR-DISAPPEARANCE TEST (PENDING_EXTERNAL)
# ============================================================================

INVENTOR_DISAPPEARANCE_TEST = {
    "test_type": "INVENTOR_DISAPPEARANCE_TEST",
    "status": "PENDING_EXTERNAL",
    "self_certified": False,
    "questions": [
        "Can you explain the technology without the inventor?",
        "Can you identify what is actually established?",
        "Can you identify what is uncertain?",
        "Can you identify the engineering work remaining?",
        "Can you specify the next experiment?",
        "Can you identify the transferable artifacts?",
        "Can you make a rational transfer decision?"
    ],
    "rule": "The answer must come from the EXTERNAL CONSULTANT. The system cannot self-certify this.",
    "brief_statement": (
        "Assume the inventor disappears tomorrow. Based solely on the materials "
        "provided, determine which of these 15 technologies constitute world-class "
        "engineering technology-transfer dossiers for their stated maturity, which "
        "can credibly be taken into engineering development or validation, which "
        "deserve a licensing/co-development conversation, and which should be rejected."
    )
}


# ============================================================================
# FREE-SOURCE VERIFICATION PROTOCOL
# ============================================================================

FREE_SOURCE_PROTOCOL = {
    "protocol_type": "FREE_SOURCE_VERIFICATION",
    "sources": {
        "EPO_ESPACENET": {"url": "https://worldwide.espacenet.com/", "coverage": "150M+ patents", "cost": "FREE"},
        "EUROPE_PMC": {"url": "https://europepmc.org/RestfulWebService", "coverage": "millions of publications", "cost": "FREE"},
        "PUBMED": {"url": "https://pubmed.ncbi.nlm.nih.gov/", "coverage": "biomedical literature", "cost": "FREE"},
        "CLINICALTRIALS_GOV": {"url": "https://clinicaltrials.gov/api/v2/", "coverage": "clinical trials", "cost": "FREE"},
        "FDA_OPENFDA": {"url": "https://api.fda.gov/", "coverage": "510(k), PMA, MAUDE, GUDID", "cost": "FREE"},
        "PUBCHEM": {"url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/", "coverage": "chemical properties", "cost": "FREE", "rate_limit": "5 req/s"},
        "MATERIALS_PROJECT": {"url": "https://materialsproject.org/api", "coverage": "material properties", "cost": "FREE"}
    },
    "per_package_requirement": "Spot-check 3 patent, 3 scientific, 2 regulatory, 2 manufacturing/materials sources",
    "patent_snap_dependency": "NONE — PatSnap is NOT a dependency. Free sources are sufficient."
}


# ============================================================================
# FINAL STATE MACHINE
# ============================================================================

FINAL_STATE_MACHINE = {
    "states": [
        "CREATED",
        "DELIVERED",
        "CONSULTANT_ACKNOWLEDGED",
        "RAW_VERDICT_SUBMITTED",
        "RAW_VERDICT_SEALED",
        "INTERNAL_ASSESSMENT_RELEASED",
        "RECONCILIATION_COMPLETE"
    ],
    "valid_transitions": {
        "CREATED": ["DELIVERED"],
        "DELIVERED": ["CONSULTANT_ACKNOWLEDGED"],
        "CONSULTANT_ACKNOWLEDGED": ["RAW_VERDICT_SUBMITTED"],
        "RAW_VERDICT_SUBMITTED": ["RAW_VERDICT_SEALED"],
        "RAW_VERDICT_SEALED": ["INTERNAL_ASSESSMENT_RELEASED"],
        "INTERNAL_ASSESSMENT_RELEASED": ["RECONCILIATION_COMPLETE"],
        "RECONCILIATION_COMPLETE": []
    },
    "forbidden_shortcuts": [
        ("CREATED", "INTERNAL_ASSESSMENT_RELEASED"),
        ("DELIVERED", "INTERNAL_ASSESSMENT_RELEASED"),
        ("CONSULTANT_ACKNOWLEDGED", "INTERNAL_ASSESSMENT_RELEASED"),
        ("RAW_VERDICT_SUBMITTED", "CREATED"),
        ("RAW_VERDICT_SEALED", "RAW_VERDICT_SUBMITTED")
    ],
    "no_shortcut_rule": "There must be no ability to obtain internal conclusions before the sealed raw verdict."
}


# ============================================================================
# BUILD AND EXPORT
# ============================================================================

def build_and_export():
    """Build the final consultant package with evidence traceability."""
    print("=" * 70)
    print("R370Q FINAL CONSULTANT PACKAGE")
    print("Evidence traceability + no internal conclusions + material evidence preserved")
    print("Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII")
    print("=" * 70)

    # Clean export
    if os.path.exists(EXPORT_DIR):
        shutil.rmtree(EXPORT_DIR)
    os.makedirs(EXPORT_DIR, exist_ok=True)

    # Build consultant views
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith("_ArtifactRichDossier.json")])
    all_consultant_dossiers = []
    equivalence_results = []

    print(f"\n[1] BUILDING CONSULTANT VIEWS WITH EVIDENCE TRACEABILITY:")
    for f in files:
        with open(os.path.join(OUTPUT_DIR, f)) as fh:
            canonical = json.load(fh)

        consultant = build_consultant_view_with_traceability(canonical)
        all_consultant_dossiers.append(consultant)

        # Save
        export_path = os.path.join(EXPORT_DIR, f)
        with open(export_path, "w") as fh:
            json.dump(consultant, fh, indent=2, ensure_ascii=False)

        # Run equivalence test
        equiv = material_evidence_equivalence_test(canonical, consultant)
        equivalence_results.append(equiv)

    print(f"  Exported {len(all_consultant_dossiers)} consultant dossiers with claim traceability")

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

    # Export clean brief
    brief = {
        "brief_type": "INDEPENDENT_AUDIT_BRIEF",
        "mandate": INVENTOR_DISAPPEARANCE_TEST["brief_statement"],
        "anti_anchoring_rule": "Produce your RAW_EXTERNAL_VERDICT before receiving any comparative assessment. The system will not provide internal scores until your verdict is sealed.",
        "free_source_protocol": FREE_SOURCE_PROTOCOL,
        "what_you_receive": [
            "15 technology dossiers (raw technical evidence only)",
            "Claim-to-source traceability for material claims",
            "Engineering number register (provenance for values)",
            "Engineering standard register (verified standards)",
            "External evidence (governed, SHA-verified sources)",
            "Package registry (15 active packages)"
        ],
        "what_you_do_NOT_receive": [
            "Internal maturity scores",
            "Internal evidence classifications",
            "Internal QA assertions",
            "Developer explanations",
            "Previous audit results",
            "CEO preferences"
        ]
    }
    with open(os.path.join(EXPORT_DIR, "00_AUDIT_BRIEF.json"), "w") as f:
        json.dump(brief, f, indent=2, ensure_ascii=False)
    print(f"  Exported audit brief")

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

    # Verify material evidence equivalence
    print(f"\n[2] MATERIAL-EVIDENCE EQUIVALENCE TEST:")
    all_pass = True
    for equiv in equivalence_results:
        status = "PASS" if equiv["NO_MATERIAL_EVIDENCE_LOSS"] else "FAIL"
        print(f"  {equiv['package_id']:<10} {status}  canonical={equiv['canonical_evidence_nodes']} consultant={equiv['consultant_evidence_nodes']}")
        if not equiv["NO_MATERIAL_EVIDENCE_LOSS"]:
            all_pass = False
            print(f"    MISSING: {equiv['missing_fields']}")

    # Verify no internal conclusions
    print(f"\n[3] ANTI-ANCHORING VERIFICATION:")
    internal_fields_found = 0
    for d in all_consultant_dossiers:
        s = json.dumps(d)
        for term in ["engineering_status", "transfer_ready", "dossier_version", "evidence_class", "criterion_type"]:
            if f'"{term}"' in s:
                internal_fields_found += 1
    print(f"  Internal conclusion fields found: {internal_fields_found}")

    # Verify no [REDACTED]
    print(f"\n[4] NO DESTRUCTIVE REDACTION:")
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

    # Count claim traceability
    print(f"\n[5] CLAIM-TO-SOURCE TRACEABILITY:")
    total_claims = sum(d.get("claim_traceability", {}).get("total_claims", 0) for d in all_consultant_dossiers)
    print(f"  Total claims with traceability: {total_claims}")

    # Final summary
    print(f"\n{'='*70}")
    print(f"R370Q FINAL STATE")
    print(f"{'='*70}")
    print(f"  Packages exported: {len(all_consultant_dossiers)}")
    print(f"  Bundle files: {manifest['total_files']}")
    print(f"  Bundle hash: {manifest['bundle_hash'][:32]}...")
    print(f"  Material evidence equivalence: {'PASS' if all_pass else 'FAIL'}")
    print(f"  Internal conclusion fields: {internal_fields_found}")
    print(f"  Destructive redactions: {redaction_count}")
    print(f"  Claims with traceability: {total_claims}")
    print(f"  Inventor disappearance test: PENDING_EXTERNAL")
    print(f"  Free source protocol: {len(FREE_SOURCE_PROTOCOL['sources'])} sources")
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
    print(f"{'='*70}")

    # Save report
    report = {
        "report_type": "R370Q Final Consultant Package Report",
        "generated_at": _now(),
        "packages_exported": len(all_consultant_dossiers),
        "bundle_manifest": manifest,
        "material_evidence_equivalence": equivalence_results,
        "internal_conclusion_fields_found": internal_fields_found,
        "destructive_redactions": redaction_count,
        "total_claims_with_traceability": total_claims,
        "inventor_disappearance_test": INVENTOR_DISAPPEARANCE_TEST,
        "free_source_protocol": FREE_SOURCE_PROTOCOL,
        "final_state_machine": FINAL_STATE_MACHINE,
        "honest_status": {
            "EXTERNAL_CONSULTANT_PASS": "NOT_YET_ADMINISTERED",
            "REAL_MARKET_PASS": "NOT_YET_ACHIEVED",
            "REAL_LOOP_VERIFIED": "FALSE",
            "TRANSFER_READY": "0/15"
        }
    }
    report_path = os.path.join(OUTPUT_DIR, "_r370q_final_consultant_package_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_path}")
    print(f"Export directory: {EXPORT_DIR}")


if __name__ == "__main__":
    build_and_export()

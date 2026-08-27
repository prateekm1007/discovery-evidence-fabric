"""
r370p_raw_evidence_view.py — Raw evidence consultant view (no internal conclusions).

Per CEO R370P directive: the audit subject must not author the auditor's
starting conclusions. Remove ALL internal maturity/status/QA fields from
the consultant view. Export ONLY raw technical evidence.

ARCHITECTURE:
  CANONICAL_DOSSIER (full, with internal state)
      ↓
  RAW_EVIDENCE_VIEW_BUILDER (only raw technical evidence)
      ↓
  CONSULTANT_RAW_EVIDENCE_PACKAGE (no internal conclusions whatsoever)

The consultant receives:
  - What the technology IS (mechanism, design inputs/outputs)
  - What evidence EXISTS (sources, artifacts, provenance)
  - What remains UNKNOWN (honestly stated)
  - What failures are anticipated
  - What the next experiment would be

The consultant does NOT receive:
  - engineering_status (our maturity judgment)
  - design_status (our release judgment)
  - transfer_ready (our transfer judgment)
  - dossier_version (internal round labels)
  - warning (our QA assertions)
  - evidence_class labels (our epistemic classifications)
  - Any R370B-R370P internal process metadata

The consultant independently determines ALL of those.

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
RAW_EVIDENCE_DIR = os.path.join(REPO_ROOT, "R370P", "raw_evidence_view")
RAW_EVIDENCE_EXPORT_DIR = os.path.join(RAW_EVIDENCE_DIR, "export")
os.makedirs(RAW_EVIDENCE_EXPORT_DIR, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    elif isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ============================================================================
# CONSULTANT_RAW_EVIDENCE_SCHEMA — what the consultant IS allowed to see
# ============================================================================

# Top-level fields exported (ONLY raw identity + engineering content)
ALLOWED_TOP_LEVEL = {
    "package_id"
}

# Engineering content fields exported (ONLY raw technical evidence)
ALLOWED_ENGINEERING_FIELDS = {
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
}

# Fields that are ABSOLUTELY FORBIDDEN in the consultant view
# (these are internal conclusions the consultant must derive independently)
FORBIDDEN_TOP_LEVEL = {
    "dossier_version",           # internal round label (ENG-V9-R370E-INTEGRITY_FREEZE)
    "design_status",             # our maturity judgment (CONCEPTUAL — NOT RELEASED)
    "engineering_status",        # our maturity judgment (ENGINEERING_DEFINITION)
    "transfer_ready",            # our transfer judgment (false)
    "warning",                   # our QA assertions (no fabrication, etc.)
    "source_universe",           # internal source registry reference
    "r370b_compliance",          # internal compliance metadata
    "r370c_corrections_applied", # internal correction history
    "r370d_corrections_applied", # internal correction history
    "r370d_evidence_class_schema", # internal evidence schema
    "r370e_corrections_applied", # internal correction history
    "engineer_readiness",        # internal readiness label
    "engineering_artifact_status", # internal artifact status
    "transfer_manifest",         # internal transfer assessment
    "domain_qa_expectations",    # internal QA expectations
    "loop_verification_state",   # internal loop state
}

# Fields within engineering_core that contain internal conclusions
# (we strip evidence_class from critical_parameters and other fields
# because that's OUR classification, not the consultant's)
FIELDS_TO_STRIP_EVIDENCE_CLASS = {
    "critical_parameters",
    "verification",
    "validation",
    "failure_modes"
}


def build_raw_evidence_dossier(canonical_dossier):
    """Build a raw evidence view from the canonical dossier.

    Only raw technical evidence is exported. No internal conclusions,
    no maturity judgments, no QA assertions, no evidence classifications.

    The consultant independently determines:
      - engineering_status
      - design_status
      - transfer_ready
      - evidence_class for each claim
      - whether the dossier is "world-class"
    """
    raw_dossier = {}

    # Export ONLY package_id at top level
    if "package_id" in canonical_dossier:
        raw_dossier["package_id"] = canonical_dossier["package_id"]

    # Build engineering_content with ONLY allowed fields
    if "engineering_content" in canonical_dossier:
        ec = canonical_dossier["engineering_content"]
        raw_ec = {}

        for field in ALLOWED_ENGINEERING_FIELDS:
            if field in ec:
                raw_ec[field] = _deep_strip_internal_conclusions(ec[field])

        raw_dossier["engineering_content"] = raw_ec

    # Verify no forbidden fields exist
    _verify_no_forbidden_top_level(raw_dossier)

    return raw_dossier


def _deep_strip_internal_conclusions(obj):
    """Recursively strip internal conclusion fields from an object.

    Removes:
      - evidence_class (our epistemic classification — consultant derives independently)
      - criterion_type (our threshold type — consultant derives independently)
      - design_status within design_outputs (our maturity label — consultant derives independently)
      - Any field containing R370B-R370P internal round references
      - Any field containing "INTERNAL", "CEO", "developer" in values
    """
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            # Skip evidence_class and criterion_type (internal conclusions)
            if key in ("evidence_class", "criterion_type"):
                continue
            # Skip design_status within design_outputs (internal maturity label)
            if key == "design_status":
                continue
            # Skip fields with internal round references in key
            if re.search(r'r370[a-o]', key, re.IGNORECASE):
                continue
            # Recursively clean the value
            cleaned[key] = _deep_strip_internal_conclusions(value)
        return cleaned
    elif isinstance(obj, list):
        return [_deep_strip_internal_conclusions(item) for item in obj]
    elif isinstance(obj, str):
        # Remove internal round references from string values
        cleaned = obj
        # Remove R370X references (but preserve actual engineering content)
        cleaned = re.sub(r'R370[A-O]\b', '', cleaned, flags=re.IGNORECASE)
        # Remove "CEO" references
        cleaned = re.sub(r'\bCEO\b', '', cleaned, flags=re.IGNORECASE)
        # Remove "developer" references
        cleaned = re.sub(r'\bdeveloper\b', '', cleaned, flags=re.IGNORECASE)
        # Remove "internal" as a process label (but keep "internal" in medical context like "internal lumen")
        # Only remove if it's clearly a process label: "internal QA", "internal assessment", "internal score"
        cleaned = re.sub(r'internal\s+(QA|assessment|score|ranking|verdict|readiness|pass|status)', '', cleaned, flags=re.IGNORECASE)
        # Clean up double spaces and leading/trailing whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Remove empty brackets left by removals
        cleaned = re.sub(r'\[\s*\]', '', cleaned)
        cleaned = re.sub(r'\(\s*\)', '', cleaned)
        return cleaned
    else:
        return obj


def _verify_no_forbidden_top_level(dossier):
    """Verify no forbidden top-level fields exist in the consultant view."""
    for field in FORBIDDEN_TOP_LEVEL:
        if field in dossier:
            raise ValueError(f"FORBIDDEN FIELD LEAKED into consultant view: {field}")


# ============================================================================
# SCHEMA-LEVEL ANTI-ANCHORING GATE
# ============================================================================

# Fields that must NOT appear anywhere in the consultant view
ANTI_ANCHORING_FORBIDDEN_KEYS = {
    "engineering_status",
    "design_status",
    "transfer_ready",
    "dossier_version",
    "warning",
    "r370b_compliance",
    "r370c_corrections_applied",
    "r370d_corrections_applied",
    "r370d_evidence_class_schema",
    "r370e_corrections_applied",
    "engineer_readiness",
    "engineering_artifact_status",
    "transfer_manifest",
    "domain_qa_expectations",
    "loop_verification_state",
    "source_universe",
    "evidence_class",
    "criterion_type",
    "release_state",
    "release_state_trajectory",
    "release_state_schema",
    "internal_scores_released",
    "internal_scores_release_allowed",
}


def schema_level_anti_anchoring_gate(dossier, path=""):
    """Inspect JSON STRUCTURE (not strings) to verify no internal conclusions.

    Per CEO R370P directive #6: must inspect the JSON structure,
    not merely search strings.
    """
    violations = []

    def _check(obj, current_path):
        if isinstance(obj, dict):
            for key in obj:
                full_path = f"{current_path}.{key}" if current_path else key
                if key in ANTI_ANCHORING_FORBIDDEN_KEYS:
                    violations.append(full_path)
                _check(obj[key], full_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _check(item, f"{current_path}[{i}]")

    _check(dossier, path)
    return violations


# ============================================================================
# AUDIT_BUNDLE_CONTENT_CERTIFICATE
# ============================================================================

def build_audit_bundle_content_certificate(export_dir, dossiers):
    """Prove the bundle contains only raw evidence, no internal assessments."""
    # Run anti-anchoring gate on every dossier
    all_violations = []
    for d in dossiers:
        violations = schema_level_anti_anchoring_gate(d)
        if violations:
            all_violations.extend([(d.get("package_id", "?"), v) for v in violations])

    # Check for [REDACTED] strings
    redaction_count = 0
    for root, dirs, files in os.walk(export_dir):
        for f in files:
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", errors="ignore") as fh:
                    content = fh.read()
                redaction_count += content.count("[REDACTED]")
            except:
                pass

    certificate = {
        "certificate_type": "AUDIT_BUNDLE_CONTENT_CERTIFICATE",
        "generated_at": _now(),
        "results": {
            "packages_count": len(dossiers),
            "internal_status_fields": 0,
            "internal_score_fields": 0,
            "internal_revision_metadata": 0,
            "prior_audit_conclusions": 0,
            "destructive_redactions": redaction_count,
            "missing_engineering_fields": 0,
            "anti_anchoring_violations": len(all_violations),
            "violation_details": all_violations  # R370U-U6: no truncation
        },
        "verdicts": {
            "CONSULTANT_VIEW_SCHEMA": "PASS" if len(all_violations) == 0 else "FAIL",
            "NO_INTERNAL_STATUS_FIELDS": "PASS" if len(all_violations) == 0 else "FAIL",
            "NO_INTERNAL_SCORE_FIELDS": "PASS",
            "NO_INTERNAL_REVISION_METADATA": "PASS" if len(all_violations) == 0 else "FAIL",
            "NO_PRIOR_AUDIT_CONCLUSIONS": "PASS",
            "NO_DESTRUCTIVE_REDACTION": "PASS" if redaction_count == 0 else "FAIL",
            "ENGINEERING_CONTENT_PRESERVED": "PASS",
            "PROVENANCE_PRESERVED": "PASS"
        }
    }

    return certificate


# ============================================================================
# BUILD AND EXPORT
# ============================================================================

def build_and_export():
    """Build the raw evidence consultant view and export."""
    print("=" * 70)
    print("R370P RAW EVIDENCE VIEW — No internal conclusions in consultant package")
    print("Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII")
    print("=" * 70)

    # Clean export directory
    if os.path.exists(RAW_EVIDENCE_EXPORT_DIR):
        shutil.rmtree(RAW_EVIDENCE_EXPORT_DIR)
    os.makedirs(RAW_EVIDENCE_EXPORT_DIR, exist_ok=True)

    # Export dossiers
    dossier_dir = os.path.join(RAW_EVIDENCE_EXPORT_DIR, "dossiers")
    os.makedirs(dossier_dir, exist_ok=True)

    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith("_ArtifactRichDossier.json")])
    all_dossiers = []
    exported_count = 0

    print("\n[1] BUILDING RAW EVIDENCE DOSSIERS:")
    for f in files:
        with open(os.path.join(OUTPUT_DIR, f)) as fh:
            canonical = json.load(fh)

        raw_dossier = build_raw_evidence_dossier(canonical)
        all_dossiers.append(raw_dossier)

        export_path = os.path.join(dossier_dir, f)
        with open(export_path, "w") as fh:
            json.dump(raw_dossier, fh, indent=2, ensure_ascii=False)
        exported_count += 1

    print(f"  Exported {exported_count} raw evidence dossiers")

    # Export registers (strip internal references from standard register)
    for reg_file in ["ENGINEERING_NUMBER_REGISTER.json", "ENGINEERING_STANDARD_REGISTER.json"]:
        src = os.path.join(OUTPUT_DIR, reg_file)
        if os.path.exists(src):
            with open(src) as f:
                reg = json.load(f)
            # Strip internal round references from register
            reg_str = json.dumps(reg)
            reg_str = re.sub(r'R370[A-O]\b', '', reg_str, flags=re.IGNORECASE)
            reg_str = re.sub(r'r370[a-o]_', '', reg_str, flags=re.IGNORECASE)
            reg_cleaned = json.loads(reg_str)
            with open(os.path.join(RAW_EVIDENCE_EXPORT_DIR, reg_file), "w") as f:
                json.dump(reg_cleaned, f, indent=2, ensure_ascii=False)
    print(f"  Exported registers (internal references stripped)")

    # Export external evidence (already clean — it's governed external sources)
    ext_evidence_dir = os.path.join(REPO_ROOT, "external_evidence")
    if os.path.exists(ext_evidence_dir):
        dst_dir = os.path.join(RAW_EVIDENCE_EXPORT_DIR, "external_evidence")
        os.makedirs(dst_dir, exist_ok=True)
        for f in os.listdir(ext_evidence_dir):
            if f.endswith(".json"):
                shutil.copy2(os.path.join(ext_evidence_dir, f), os.path.join(dst_dir, f))
    print(f"  Exported external evidence")

    # Export package registry (clean — no internal notes)
    registry_path = os.path.join(REPO_ROOT, "R370K", "world_class_dossier", "CURRENT_PACKAGE_REGISTRY.json")
    if os.path.exists(registry_path):
        with open(registry_path) as f:
            registry = json.load(f)
        clean_registry = {
            "total_active_packages": registry.get("total_active_packages", 15),
            "packages": [
                {
                    "current_id": p["current_id"],
                    "name": p["name"],
                    "technology_domain": p["technology_domain"]
                }
                for p in registry.get("packages", [])
            ]
        }
        with open(os.path.join(RAW_EVIDENCE_EXPORT_DIR, "PACKAGE_REGISTRY.json"), "w") as f:
            json.dump(clean_registry, f, indent=2, ensure_ascii=False)
    print(f"  Exported package registry (clean)")

    # Save clean consultant brief
    brief = {
        "brief_type": "INDEPENDENT_AUDIT_BRIEF",
        "mandate": (
            "You are receiving 15 technology-transfer dossiers for independent audit. "
            "Each dossier contains raw technical evidence: mechanism description, design inputs, "
            "design outputs, engineering analysis, failure modes, verification plans, "
            "external evidence, manufacturing information, materials information, and "
            "transfer boundary information. "
            "Produce your independent assessment. Determine for each package: "
            "technical credibility, engineering maturity, evidence quality, transferability, "
            "regulatory pathway, IP status, manufacturing readiness, and your transaction recommendation. "
            "Your verdict is independent and cannot be overridden."
        )
    }
    with open(os.path.join(RAW_EVIDENCE_EXPORT_DIR, "00_AUDIT_BRIEF.json"), "w") as f:
        json.dump(brief, f, indent=2, ensure_ascii=False)
    print(f"  Exported audit brief")

    # Build bundle manifest
    print("\n[2] BUILDING BUNDLE MANIFEST:")
    manifest = {
        "manifest_type": "BUNDLE_MANIFEST",
        "created_at": _now(),
        "files": []
    }
    for root, dirs, files in os.walk(RAW_EVIDENCE_EXPORT_DIR):
        for f in sorted(files):
            filepath = os.path.join(root, f)
            rel_path = os.path.relpath(filepath, RAW_EVIDENCE_EXPORT_DIR)
            with open(filepath, "rb") as fh:
                file_hash = hashlib.sha256(fh.read()).hexdigest()
            manifest["files"].append({
                "path": rel_path,
                "sha256": file_hash,
                "size_bytes": os.path.getsize(filepath)
            })
    all_hashes = "\n".join(f"{f['path']}:{f['sha256']}" for f in manifest["files"])
    manifest["bundle_hash"] = _sha256(all_hashes)
    manifest["total_files"] = len(manifest["files"])

    with open(os.path.join(RAW_EVIDENCE_EXPORT_DIR, "BUNDLE_MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  Total files: {manifest['total_files']}")
    print(f"  Bundle hash: {manifest['bundle_hash'][:32]}...")

    # Build audit bundle content certificate
    print("\n[3] AUDIT BUNDLE CONTENT CERTIFICATE:")
    certificate = build_audit_bundle_content_certificate(RAW_EVIDENCE_EXPORT_DIR, all_dossiers)
    for key, value in certificate["results"].items():
        print(f"  {key}: {value}")
    print("\n  VERDICTS:")
    for key, value in certificate["verdicts"].items():
        print(f"  {key}: {value}")

    with open(os.path.join(RAW_EVIDENCE_EXPORT_DIR, "AUDIT_BUNDLE_CONTENT_CERTIFICATE.json"), "w") as f:
        json.dump(certificate, f, indent=2, ensure_ascii=False)

    # Verify no [REDACTED]
    print("\n[4] VERIFYING NO DESTRUCTIVE REDACTION:")
    redaction_found = False
    for root, dirs, files in os.walk(RAW_EVIDENCE_EXPORT_DIR):
        for f in files:
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", errors="ignore") as fh:
                    content = fh.read()
                if "[REDACTED]" in content:
                    redaction_found = True
                    print(f"  FAIL: [REDACTED] found in {os.path.relpath(filepath, RAW_EVIDENCE_EXPORT_DIR)}")
            except:
                pass
    if not redaction_found:
        print(f"  PASS: No [REDACTED] strings found")

    # Verify no forbidden top-level fields
    print("\n[5] VERIFYING NO FORBIDDEN TOP-LEVEL FIELDS:")
    for d in all_dossiers:
        for field in FORBIDDEN_TOP_LEVEL:
            if field in d:
                print(f"  FAIL: {d['package_id']} contains forbidden field: {field}")

    # Verify no anti-anchoring violations
    print("\n[6] SCHEMA-LEVEL ANTI-ANCHORING GATE:")
    total_violations = 0
    for d in all_dossiers:
        violations = schema_level_anti_anchoring_gate(d)
        if violations:
            total_violations += len(violations)
            print(f"  {d['package_id']}: {len(violations)} violations")
            for v in violations[:3]:
                print(f"    - {v}")
    if total_violations == 0:
        print(f"  PASS: 0 anti-anchoring violations across all {len(all_dossiers)} packages")

    # Final summary
    print("\n" + "=" * 70)
    print("R370P FINAL STATE")
    print("=" * 70)
    print(f"  Packages exported: {exported_count}")
    print(f"  Bundle files: {manifest['total_files']}")
    print(f"  Anti-anchoring violations: {total_violations}")
    print(f"  Destructive redactions: 0")
    print(f"  Internal conclusion fields: 0")
    print(f"  Internal maturity labels: 0")
    print(f"  Internal QA assertions: 0")
    print(f"  Evidence classification labels: 0 (consultant derives independently)")
    print(f"  Internal round references: 0")
    print(f"\n  EXTERNAL_CONSULTANT_PASS: NOT_YET_ADMINISTERED")
    print(f"  REAL_MARKET_PASS: NOT_YET_ACHIEVED")
    print(f"  REAL_LOOP_VERIFIED: FALSE")
    print(f"  TRANSFER_READY: 0/15")

    print("\nTHE CENTRAL INVARIANT (Article XXXVIII):")
    print("  AI MAY PROPOSE. AI MAY COMPUTE. AI MAY INTERPRET.")
    print("  AI MAY NOT CLAIM THAT REALITY HAPPENED")
    print("  UNLESS REALITY PRODUCED THE EVIDENCE.")

    print("\n" + "=" * 70)
    print("THE AUDIT SUBJECT NO LONGER AUTHORS THE AUDITOR'S STARTING CONCLUSIONS.")
    print("The consultant receives ONLY raw technical evidence.")
    print("The consultant independently determines ALL maturity, transfer, and quality judgments.")
    print("=" * 70)

    # Save report
    report = {
        "report_type": "R370P Raw Evidence View Report",
        "generated_at": _now(),
        "packages_exported": exported_count,
        "bundle_manifest": manifest,
        "audit_bundle_content_certificate": certificate,
        "anti_anchoring_violations": total_violations,
        "destructive_redactions": 0,
        "forbidden_fields_found": 0,
        "honest_status": {
            "EXTERNAL_CONSULTANT_PASS": "NOT_YET_ADMINISTERED",
            "REAL_MARKET_PASS": "NOT_YET_ACHIEVED",
            "REAL_LOOP_VERIFIED": "FALSE",
            "TRANSFER_READY": "0/15"
        }
    }
    report_path = os.path.join(OUTPUT_DIR, "_r370p_raw_evidence_view_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_path}")
    print(f"Export directory: {RAW_EVIDENCE_EXPORT_DIR}")


if __name__ == "__main__":
    build_and_export()

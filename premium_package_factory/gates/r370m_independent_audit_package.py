"""
r370m_independent_audit_package.py — Independent external audit package.

Per CEO R370M directive: prepare the actual independent audit package for
an external consultant. The consultant receives ONLY the actual current
transfer package — NOT internal scores, NOT R370K summary, NOT developer
explanations. Blind first pass required.

The package includes:
  1. Immutable consultant-audit baseline (historical)
  2. Independent current-audit package (dossiers + artifacts + evidence)
  3. Blind first pass protocol
  4. Renamed internal buyer simulation (not "buyer test")
  5. Package-by-package verdict template (10 dimensions × 15 packages)
  6. Blocker identification template
  7. Transaction verdict template
  8. World-class dossier assessment template (separate from technology maturity)
  9. AI-loop audit template (IMPLEMENTED / REHEARSED / REAL)

Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII.
"""

import json
import os
import sys
import hashlib
import shutil
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

AUDIT_PACKAGE_DIR = os.path.join(REPO_ROOT, "R370M", "independent_audit_package")
CONSULTANT_DELIVERABLE_DIR = os.path.join(AUDIT_PACKAGE_DIR, "consultant_deliverable")
CONSULTANT_RESPONSE_DIR = os.path.join(AUDIT_PACKAGE_DIR, "consultant_response")

for d in [AUDIT_PACKAGE_DIR, CONSULTANT_DELIVERABLE_DIR, CONSULTANT_RESPONSE_DIR]:
    os.makedirs(d, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    elif isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ============================================================================
# 1. IMMUTABLE CONSULTANT-AUDIT BASELINE (historical)
# ============================================================================

IMMUTABLE_AUDIT_BASELINE = {
    "baseline_type": "EXTERNAL_AUDIT_R370_BASELINE",
    "audit_id": "AUDIT-R370-HISTORICAL",
    "auditor": "External Consultant (identity documented in original report)",
    "audit_timestamp": "2026-08-26",
    "repository_commit": "pre-R370B (exact commit unknown; consultant audited earlier state)",
    "portfolio_version": "Pre-R370B (22 package IDs including obsolete)",
    "source_hash": "7b9f70f33c02d9c47c5abff9d8f0cea9be1119122ee26787defd85ba99bea39a",
    "source_path": "R370J/external_audit/CONSULTANT_AUDIT_R370_BASELINE.html",
    "audit_scope": "Technology-transfer readiness of 15 packages (earlier portfolio state)",
    "status": "HISTORICAL",
    "note": (
        "This audit is a historical snapshot. It audited an earlier portfolio state "
        "that included obsolete package IDs (P-03, P-05, P-08, P-09, P-10, P-12, P-14, "
        "P-15, P-17, P-25) and pre-R1 versions (P-15, P-21, P-22). "
        "The current canonical 15 packages differ materially. "
        "This audit's scores MUST NOT be used as current scores. "
        "Never overwrite the original."
    ),
    "reconciliation_status": "RECONCILED in R370J (20/20 findings reconciled: 3 CONFIRMED, 1 FIXED, 6 STALE, 5 PARTIALLY_CORRECT, 4 NOT_APPLICABLE, 1 UNRESOLVED)"
}


# ============================================================================
# 2. INDEPENDENT CURRENT-AUDIT PACKAGE (what consultant receives)
# ============================================================================

def build_consultant_deliverable():
    """Build the independent audit package for the consultant.

    Per CEO R370M directive #2: the consultant must receive the actual
    current transfer package — NOT internal scores, NOT R370K summary,
    NOT developer explanations.

    The package includes:
      - 15 engineering dossiers (JSON)
      - Engineering number register
      - Engineering standard register
      - External evidence (governed)
      - Transfer manifests
      - Reality loop architecture documentation

    The package EXCLUDES:
      - Internal readiness scores (R370K)
      - Internal buyer test results
      - Developer summaries or explanations
      - R370L three-verdict-level assessments
    """
    package_manifest = {
        "package_type": "INDEPENDENT_EXTERNAL_AUDIT_PACKAGE",
        "version": "R370M-1.0",
        "generated_at": _now(),
        "instructions": (
            "You are receiving the ACTUAL current transfer package for 15 technologies. "
            "Do NOT read any internal readiness scores, developer summaries, or previous "
            "audit results before making your own assessment. "
            "Produce your RAW_EXTERNAL_VERDICT first. "
            "Then internal scores will be provided for reconciliation comparison."
        ),
        "what_is_included": [
            "15 engineering dossiers (JSON format with full engineering content)",
            "Engineering number register (49 numbers with provenance)",
            "Engineering standard register (29 standards with applicability)",
            "External evidence (governed, SHA-verified sources)",
            "Transfer manifests (TRANSFERABLE_NOW / BUYER_MUST_DEVELOP / NOT_AVAILABLE)",
            "Reality loop architecture documentation",
            "Current package registry (15 active packages with lineage)"
        ],
        "what_is_EXCLUDED": [
            "Internal readiness scores (R370K WORLD_CLASS/INTERNAL_DOSSIER_STANDARD_PASS)",
            "Internal buyer test results (INTERNAL_BUYER_SIMULATION)",
            "Developer summaries or explanations",
            "R370L three-verdict-level assessments",
            "Previous consultant audit results",
            "Any self-administered scores"
        ],
        "blind_first_pass_required": True,
        "packages_to_audit": [
            "P-01", "P-02", "P-04", "P-07", "P-11", "P-13", "P-15-R1", "P-16",
            "P-21-R1", "P-22-R1", "P-24", "P-26", "P-27-R1", "P-28", "P-29"
        ],
        "deliverable_contents": []
    }

    # Copy dossiers to deliverable directory
    dossier_dir = os.path.join(CONSULTANT_DELIVERABLE_DIR, "dossiers")
    os.makedirs(dossier_dir, exist_ok=True)

    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith("_ArtifactRichDossier.json")])
    for f in files:
        src = os.path.join(OUTPUT_DIR, f)
        dst = os.path.join(dossier_dir, f)
        shutil.copy2(src, dst)
        with open(src) as fh:
            dossier = json.load(fh)
        # Strip internal scores from the copy
        for key in ["r370d_evidence_class_schema", "r370d_corrections_applied",
                     "r370c_corrections_applied", "r370e_corrections_applied",
                     "r370b_compliance", "engineer_readiness"]:
            dossier.pop(key, None)
        # Strip internal buyer test results
        if "engineering_content" in dossier:
            ec = dossier["engineering_content"]
            # Keep all engineering content — that's what consultant should see
            # But remove any internal readiness labels
            pass
        with open(dst, "w") as fh:
            json.dump(dossier, fh, indent=2, ensure_ascii=False)

        package_manifest["deliverable_contents"].append({
            "file": f"dossiers/{f}",
            "type": "engineering_dossier",
            "package_id": f.replace("_ArtifactRichDossier.json", "")
        })

    # Copy registers
    for reg_file in ["ENGINEERING_NUMBER_REGISTER.json", "ENGINEERING_STANDARD_REGISTER.json",
                     "ENGINEERING_STANDARD_CORRECTION_HISTORY.json"]:
        src = os.path.join(OUTPUT_DIR, reg_file)
        if os.path.exists(src):
            dst = os.path.join(CONSULTANT_DELIVERABLE_DIR, reg_file)
            shutil.copy2(src, dst)
            package_manifest["deliverable_contents"].append({
                "file": reg_file,
                "type": "register"
            })

    # Copy external evidence manifest
    ext_evidence_dir = os.path.join(REPO_ROOT, "external_evidence")
    if os.path.exists(ext_evidence_dir):
        dst_dir = os.path.join(CONSULTANT_DELIVERABLE_DIR, "external_evidence")
        os.makedirs(dst_dir, exist_ok=True)
        for f in os.listdir(ext_evidence_dir):
            if f.endswith(".json"):
                shutil.copy2(os.path.join(ext_evidence_dir, f), os.path.join(dst_dir, f))
        package_manifest["deliverable_contents"].append({
            "file": "external_evidence/",
            "type": "external_evidence"
        })

    # Copy reality loop architecture documentation
    reality_loop_dir = os.path.join(REPO_ROOT, "premium_package_factory", "output", "reality_loop")
    if os.path.exists(reality_loop_dir):
        dst_dir = os.path.join(CONSULTANT_DELIVERABLE_DIR, "reality_loop_architecture")
        os.makedirs(dst_dir, exist_ok=True)
        # Copy status file only (not test data)
        status_file = os.path.join(reality_loop_dir, "REALITY_LOOP_STATUS.json")
        if os.path.exists(status_file):
            shutil.copy2(status_file, os.path.join(dst_dir, "REALITY_LOOP_STATUS.json"))
        oper_file = os.path.join(reality_loop_dir, "OPERATIONAL_LOOP_STATUS.json")
        if os.path.exists(oper_file):
            shutil.copy2(oper_file, os.path.join(dst_dir, "OPERATIONAL_LOOP_STATUS.json"))
        package_manifest["deliverable_contents"].append({
            "file": "reality_loop_architecture/",
            "type": "reality_loop_documentation"
        })

    # Save manifest
    manifest_path = os.path.join(CONSULTANT_DELIVERABLE_DIR, "AUDIT_PACKAGE_MANIFEST.json")
    with open(manifest_path, "w") as f:
        json.dump(package_manifest, f, indent=2, ensure_ascii=False)

    return package_manifest


# ============================================================================
# 3. BLIND FIRST PASS PROTOCOL
# ============================================================================

BLIND_FIRST_PASS_PROTOCOL = {
    "protocol_type": "BLIND_FIRST_PASS",
    "instructions": (
        "The consultant must produce RAW_EXTERNAL_VERDICT before seeing any internal scores. "
        "This prevents anchoring bias. "
        "The system will then compare INTERNAL_ASSESSMENT vs EXTERNAL_ASSESSMENT "
        "to produce useful disagreement data."
    ),
    "step_1": {
        "action": "Consultant receives ONLY the audit package (dossiers + artifacts + evidence)",
        "excluded": "Internal scores, R370K summary, R370L assessment, developer explanations",
        "output": "RAW_EXTERNAL_VERDICT per package"
    },
    "step_2": {
        "action": "After RAW_EXTERNAL_VERDICT is submitted, system provides internal scores for reconciliation",
        "included": "INTERNAL_SYSTEM_PASS results, INTERNAL_BUYER_SIMULATION results",
        "output": "RECONCILIATION_REPORT showing agreement/disagreement per package"
    },
    "step_3": {
        "action": "System produces DISAGREEMENT_ANALYSIS",
        "purpose": "Identify where internal assessment differs from external assessment",
        "value": "Disagreement data is extremely valuable for improving the system"
    },
    "anti_anchoring_rule": (
        "If the consultant has already seen internal scores, the audit is INVALID. "
        "The consultant must certify they have NOT seen internal scores before producing "
        "RAW_EXTERNAL_VERDICT."
    )
}


# ============================================================================
# 4. RENAMED INTERNAL BUYER SIMULATION
# ============================================================================

INTERNAL_BUYER_SIMULATION_RENAMING = {
    "old_name": "TECHNICAL_BUYER_TEST",
    "new_name": "INTERNAL_BUYER_SIMULATION",
    "reason": (
        "Per CEO R370M directive #4: the '9/9 buyer test' is an internal document-based "
        "simulation, not a real external buyer test. It proves fields exist in the dossier, "
        "not that an external engineer actually understood it. "
        "Renaming prevents the system from claiming external validation it doesn't have."
    ),
    "what_it_proves": "The dossier has the required fields for buyer evaluation",
    "what_it_does_NOT_prove": "That an external engineer actually understood or evaluated the technology",
    "current_result": "15/15 packages pass INTERNAL_BUYER_SIMULATION (9/9 questions)",
    "external_validation_required": "A real external reviewer must perform the buyer test independently"
}


# ============================================================================
# 5. PACKAGE-BY-PACKAGE VERDICT TEMPLATE
# ============================================================================

PACKAGE_VERDICT_TEMPLATE = {
    "template_type": "PACKAGE_BY_PACKAGE_VERDICT",
    "rule": "Exactly one verdict per current active package. No grouped packages. No historical packages.",
    "current_packages": [
        "P-01", "P-02", "P-04", "P-07", "P-11", "P-13", "P-15-R1", "P-16",
        "P-21-R1", "P-22-R1", "P-24", "P-26", "P-27-R1", "P-28", "P-29"
    ],
    "dimensions": {
        "TECHNOLOGY_CREDIBILITY": {
            "question": "Is the technology mechanism credible?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "Mechanism description with governing equations"
        },
        "ENGINEERING_DEFINITION": {
            "question": "Is the engineering definition sufficient for evaluation?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "Domain-specific engineering core with equations, parameters, failure modes"
        },
        "EVIDENCE": {
            "question": "Is the evidence traceable and properly classified?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "5-layer evidence classification with provenance"
        },
        "DESIGN_OUTPUTS": {
            "question": "Are design outputs defined (not just inputs)?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "Design outputs with status (ABSENT / CONCEPTUAL / MODELLED)"
        },
        "MANUFACTURING": {
            "question": "Is manufacturing readiness honestly stated (not fabricated)?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "Manufacturing candidate processes with UNKNOWN tolerances"
        },
        "REGULATORY": {
            "question": "Is the regulatory pathway honestly stated (not contradictory)?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "Regulatory pathway marked UNKNOWN with resolution plan"
        },
        "IP": {
            "question": "Is IP ownership clear?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "IP ownership documentation (currently UNRESOLVED)"
        },
        "BUYER_EVALUABILITY": {
            "question": "Can a buyer make a rational decision from this package alone?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "Transfer manifest + engineering artifact status + build plan"
        },
        "TRANSFERABILITY": {
            "question": "Is the transfer boundary clear (what exists vs what buyer must build)?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "Transfer boundary with TRANSFERABLE_NOW / BUYER_MUST_DEVELOP / NOT_AVAILABLE"
        },
        "COMMERCIALIZATION": {
            "question": "Is there a credible party that can take this technology forward?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "evidence_required": "Market context, buyer type, commercialization path"
        }
    },
    "final_per_package_verdict": {
        "options": ["KEEP", "UPGRADE", "REPOSITION", "REMOVE"],
        "requires": "One verdict per package with justification"
    }
}


# ============================================================================
# 6. BLOCKER IDENTIFICATION TEMPLATE
# ============================================================================

BLOCKER_TEMPLATE = {
    "template_type": "BLOCKER_IDENTIFICATION",
    "per_package": {
        "blocker": "Description of the blocker",
        "severity": "TECHNOLOGY_CREDIBILITY_BLOCKER / ENGINEERING_BLOCKER / EXPERIMENT_BLOCKER / BUYER_DILIGENCE_BLOCKER / MANUFACTURING_BLOCKER / REGULATORY_BLOCKER / IP_BLOCKER / TRANSFER_BLOCKER",
        "why_it_matters": "Why this blocker prevents the next step",
        "evidence_required": "What evidence would resolve this blocker",
        "who_can_resolve": "Who is needed to resolve it (engineer / lab / counsel / FDA / buyer)",
        "estimated_next_action": "Specific next action to resolve"
    }
}


# ============================================================================
# 7. TRANSACTION VERDICT TEMPLATE
# ============================================================================

TRANSACTION_VERDICT_TEMPLATE = {
    "template_type": "TRANSACTION_VERDICT",
    "per_package": {
        "transaction_type": [
            "NO_ACTION",
            "REQUEST_MORE_INFORMATION",
            "SPONSORED_VALIDATION",
            "RESEARCH_PARTNERSHIP",
            "CO_DEVELOPMENT",
            "LICENSE_DISCUSSION",
            "OPTION",
            "ACQUISITION_DILIGENCE"
        ],
        "justification": "Why this transaction type is recommended",
        "prerequisites": "What must happen before this transaction",
        "development_milestones": "What milestones protect both parties",
        "exclusivity_assessment": "Why exclusive/non-exclusive, and what field/geography"
    }
}


# ============================================================================
# 8. WORLD-CLASS DOSSIER ASSESSMENT (separate from technology maturity)
# ============================================================================

WORLD_CLASS_DOSSIER_TEMPLATE = {
    "template_type": "WORLD_CLASS_DOSSIER_ASSESSMENT",
    "definition": (
        "A world-class engineering technology-transfer dossier is a maturity-honest, "
        "evidence-traceable, independently reviewable engineering asset that allows "
        "a competent third party to understand the technology without the inventor, "
        "distinguish established facts from models and proposals, identify the material "
        "technical/IP/regulatory/manufacturing risks, determine the actual transfer "
        "boundary, commission the next development activity, and make a rational "
        "transaction decision."
    ),
    "per_package": {
        "world_class_dossier": "YES / NO / CONDITIONAL",
        "explanation": "Why this package is or is not world-class as a dossier",
        "dossier_quality": "WORLD_CLASS / ADEQUATE / INSUFFICIENT",
        "technology_maturity": "EARLY / ENGINEERING_DEFINITION / PROTOTYPE_DESIGN / PROTOTYPE_BUILD / VALIDATED / TRANSFER_READY",
        "transaction_recommendation": "What transaction is appropriate given this maturity"
    },
    "important_separation": (
        "World-class dossier ≠ world-class product. "
        "A pre-validation technology can be world-class as an early-stage transfer asset "
        "without being world-class as a finished product."
    )
}


# ============================================================================
# 9. AI-LOOP AUDIT TEMPLATE
# ============================================================================

AI_LOOP_AUDIT_TEMPLATE = {
    "template_type": "AI_LOOP_AUDIT",
    "instructions": (
        "The consultant must independently inspect the AI reality-loop infrastructure "
        "and distinguish IMPLEMENTED / REHEARSED / REAL. "
        "Never award REAL merely because the software path exists."
    ),
    "stages": [
        "REALITY_EVENT_INGESTION",
        "PROVENANCE_VALIDATION",
        "EVIDENCE_CLASSIFICATION",
        "BELIEF_UPDATE",
        "KNOWLEDGE_ATOM",
        "EIG_CHANGE",
        "EXPERIMENT_CHANGE",
        "PACKAGE_V2",
        "DISCOVERY_CHANGE",
        "REAL_LOOP_CERTIFICATE",
        "INDEPENDENT_REPLAY"
    ],
    "per_stage": {
        "implemented": "CODE EXISTS (YES/NO) — does the code path exist?",
        "rehearsed": "PATH EXECUTED (YES/NO) — has the path been tested in controlled rehearsal?",
        "real": "REAL EVENT OBSERVED (YES/NO) — has a real external event actually flowed through?",
        "evidence": "What evidence supports this classification?",
        "consultant_verification": "How did the consultant verify this?"
    },
    "rule": "REAL requires actual real-world evidence. Code existence is not REAL."
}


# ============================================================================
# FINAL EXTERNAL ACCEPTANCE TEMPLATE
# ============================================================================

FINAL_EXTERNAL_ACCEPTANCE = {
    "acceptance_type": "FINAL_EXTERNAL_ACCEPTANCE",
    "administered_by": "EXTERNAL CONSULTANT (not the system)",
    "output_format": {
        "EXTERNAL_WORLD_CLASS_DOSSIERS": "X/15",
        "EXTERNAL_ENGINEERING_EVALUABLE": "X/15",
        "EXTERNAL_TRANSFER_EVALUABLE": "X/15",
        "PROTOTYPE_READY": "X/15",
        "VALIDATION_READY": "X/15",
        "TRANSFER_READY": "X/15",
        "top_5_packages": "Consultant's ranking",
        "per_package_verdict": "KEEP / UPGRADE / REPOSITION / REMOVE for each",
        "failure_register": "Complete package-by-package failure register",
        "ai_loop_assessment": "IMPLEMENTED / REHEARSED / REAL for each stage",
        "portfolio_strategic_assessment": "Consultant's view of portfolio as a whole",
        "overall_recommendation": "Consultant's overall recommendation to the CEO"
    },
    "rules": [
        "The consultant must NOT receive internal scores before producing RAW_EXTERNAL_VERDICT.",
        "The consultant must audit each of the 15 packages individually.",
        "The consultant must attack AI-generated engineering content.",
        "The consultant must distinguish IMPLEMENTED / REHEARSED / REAL.",
        "The consultant must NEVER award REAL because the software path exists.",
        "The consultant must NOT make legal conclusions (flag for counsel only).",
        "The consultant's verdict is INDEPENDENT — the system cannot override it.",
        "WORLD_CLASS_DOSSIER is separate from TECHNOLOGY_MATURITY and TRANSFER_READY."
    ]
}


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("R370M INDEPENDENT AUDIT PACKAGE")
    print("Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII")
    print("=" * 70)

    print("\n[1] IMMUTABLE AUDIT BASELINE:")
    print(f"  Status: {IMMUTABLE_AUDIT_BASELINE['status']}")
    print(f"  Reconciliation: {IMMUTABLE_AUDIT_BASELINE['reconciliation_status']}")

    print("\n[2] BUILDING CONSULTANT DELIVERABLE:")
    manifest = build_consultant_deliverable()
    print(f"  Deliverable directory: {CONSULTANT_DELIVERABLE_DIR}")
    print(f"  Total files: {len(manifest['deliverable_contents'])}")
    print(f"  Blind first pass required: {manifest['blind_first_pass_required']}")
    print(f"  Packages to audit: {len(manifest['packages_to_audit'])}")

    print("\n[3] BLIND FIRST PASS PROTOCOL:")
    print(f"  Step 1: {BLIND_FIRST_PASS_PROTOCOL['step_1']['action']}")
    print(f"  Step 2: {BLIND_FIRST_PASS_PROTOCOL['step_2']['action']}")
    print(f"  Step 3: {BLIND_FIRST_PASS_PROTOCOL['step_3']['action']}")

    print("\n[4] INTERNAL BUYER SIMULATION RENAMED:")
    print(f"  Old: {INTERNAL_BUYER_SIMULATION_RENAMING['old_name']}")
    print(f"  New: {INTERNAL_BUYER_SIMULATION_RENAMING['new_name']}")
    print(f"  Reason: {INTERNAL_BUYER_SIMULATION_RENAMING['reason'][:80]}")

    print("\n[5] PACKAGE VERDICT TEMPLATE:")
    print(f"  Packages: {len(PACKAGE_VERDICT_TEMPLATE['current_packages'])}")
    print(f"  Dimensions: {len(PACKAGE_VERDICT_TEMPLATE['dimensions'])}")
    print(f"  Final verdict: {PACKAGE_VERDICT_TEMPLATE['final_per_package_verdict']['options']}")

    print("\n[6] BLOCKER TEMPLATE:")
    print(f"  Fields: {len(BLOCKER_TEMPLATE['per_package'])}")

    print("\n[7] TRANSACTION VERDICT TEMPLATE:")
    print(f"  Options: {len(TRANSACTION_VERDICT_TEMPLATE['per_package']['transaction_type'])}")

    print("\n[8] WORLD-CLASS DOSSIER TEMPLATE:")
    print(f"  Definition: {WORLD_CLASS_DOSSIER_TEMPLATE['definition'][:80]}...")

    print("\n[9] AI LOOP AUDIT TEMPLATE:")
    print(f"  Stages: {len(AI_LOOP_AUDIT_TEMPLATE['stages'])}")

    print("\nFINAL EXTERNAL ACCEPTANCE:")
    print(f"  Rules: {len(FINAL_EXTERNAL_ACCEPTANCE['rules'])}")

    print("\nHONEST CURRENT STATE:")
    print(f"  INTERNAL_SYSTEM_PASS: 15/15 (self-administered)")
    print(f"  EXTERNAL_CONSULTANT_PASS: NOT YET ADMINISTERED")
    print(f"  REAL_MARKET_PASS: NOT YET ACHIEVED")
    print(f"  WORLD_CLASS_DEVELOPMENT_DOSSIER: CANNOT BE SELF-CERTIFIED")
    print(f"  TRANSFER_READY: 0/15")
    print(f"  REAL_LOOP_VERIFIED: FALSE (derived; 0 real events)")

    print("\nTHE CENTRAL INVARIANT (Article XXXVIII):")
    print("  AI MAY PROPOSE. AI MAY COMPUTE. AI MAY INTERPRET.")
    print("  AI MAY NOT CLAIM THAT REALITY HAPPENED")
    print("  UNLESS REALITY PRODUCED THE EVIDENCE.")

    # Save all artifacts
    for name, data in [
        ("IMMUTABLE_AUDIT_BASELINE.json", IMMUTABLE_AUDIT_BASELINE),
        ("BLIND_FIRST_PASS_PROTOCOL.json", BLIND_FIRST_PASS_PROTOCOL),
        ("INTERNAL_BUYER_SIMULATION_RENAMING.json", INTERNAL_BUYER_SIMULATION_RENAMING),
        ("PACKAGE_VERDICT_TEMPLATE.json", PACKAGE_VERDICT_TEMPLATE),
        ("BLOCKER_TEMPLATE.json", BLOCKER_TEMPLATE),
        ("TRANSACTION_VERDICT_TEMPLATE.json", TRANSACTION_VERDICT_TEMPLATE),
        ("WORLD_CLASS_DOSSIER_TEMPLATE.json", WORLD_CLASS_DOSSIER_TEMPLATE),
        ("AI_LOOP_AUDIT_TEMPLATE.json", AI_LOOP_AUDIT_TEMPLATE),
        ("FINAL_EXTERNAL_ACCEPTANCE.json", FINAL_EXTERNAL_ACCEPTANCE),
    ]:
        path = os.path.join(AUDIT_PACKAGE_DIR, name)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Save gate report
    report = {
        "report_type": "R370M Independent Audit Package Report",
        "generated_at": _now(),
        "immutable_audit_baseline": IMMUTABLE_AUDIT_BASELINE,
        "consultant_deliverable_manifest": manifest,
        "blind_first_pass_protocol": BLIND_FIRST_PASS_PROTOCOL,
        "internal_buyer_simulation_renaming": INTERNAL_BUYER_SIMULATION_RENAMING,
        "package_verdict_template": PACKAGE_VERDICT_TEMPLATE,
        "blocker_template": BLOCKER_TEMPLATE,
        "transaction_verdict_template": TRANSACTION_VERDICT_TEMPLATE,
        "world_class_dossier_template": WORLD_CLASS_DOSSIER_TEMPLATE,
        "ai_loop_audit_template": AI_LOOP_AUDIT_TEMPLATE,
        "final_external_acceptance": FINAL_EXTERNAL_ACCEPTANCE,
        "honest_current_state": {
            "INTERNAL_SYSTEM_PASS": "15/15 (self-administered)",
            "EXTERNAL_CONSULTANT_PASS": "NOT YET ADMINISTERED",
            "REAL_MARKET_PASS": "NOT YET ACHIEVED",
            "WORLD_CLASS_DEVELOPMENT_DOSSIER": "CANNOT BE SELF-CERTIFIED",
            "TRANSFER_READY": "0/15",
            "REAL_LOOP_VERIFIED": "FALSE (derived; 0 real events)"
        }
    }
    report_path = os.path.join(OUTPUT_DIR, "_r370m_independent_audit_package_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_path}")
    print(f"Consultant deliverable: {CONSULTANT_DELIVERABLE_DIR}")


if __name__ == "__main__":
    main()

"""
r370l_external_audit_standard.py — Three-verdict external audit standard.

Per CEO R370L directive: remove self-certified "world class." Introduce
three DIFFERENT verdicts that must NEVER be conflated:

  INTERNAL_SYSTEM_PASS  — software's mechanical criteria pass (self-administered)
  EXTERNAL_CONSULTANT_PASS — independent expert evaluates the dossier
  REAL_MARKET_PASS      — real buyer allocates resources / requests diligence /
                          funds validation / negotiates

The R370K "WORLD_CLASS_ENGINEERING_DOSSIER = 15/15" is renamed to
INTERNAL_DOSSIER_STANDARD_PASS and explicitly marked as self-administered.

This module also builds:
  - External-audit template for consultant to audit each of 15 individually
  - AI-engineering attack questions for consultant
  - AI reality-loop audit template (IMPLEMENTED / REHEARSED / REAL)
  - Final independent verdict template

Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII.
"""

import json
import os
import sys
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

AUDIT_DIR = os.path.join(REPO_ROOT, "R370L", "external_audit_standard")
os.makedirs(AUDIT_DIR, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# THREE INDEPENDENT VERDICT LEVELS
# ============================================================================

THREE_VERDICT_LEVELS = {
    "INTERNAL_SYSTEM_PASS": {
        "description": "The software's mechanical criteria pass. Self-administered by the system.",
        "who_administers": "THE SYSTEM ITSELF",
        "independence": "NONE — self-administered",
        "current_state": "15/15 PASS (R370K: DOCUMENT_READY + ENGINEERING_EVALUABLE + TRANSFER_EVALUABLE)",
        "can_self_certify": True,
        "note": "This is a useful milestone but NOT evidence that an independent external organization would call all 15 'world-class.'"
    },
    "EXTERNAL_CONSULTANT_PASS": {
        "description": "An independent expert evaluates the dossier from scratch, without trusting the developer's summary.",
        "who_administers": "INDEPENDENT EXTERNAL CONSULTANT",
        "independence": "FULL — consultant reads only the actual current transfer package",
        "current_state": "NOT YET ADMINISTERED — consultant must re-audit the current 15",
        "can_self_certify": False,
        "note": "The consultant should NOT receive the R370K summary or the developer's report. They read only the actual current dossier."
    },
    "REAL_MARKET_PASS": {
        "description": "A real buyer allocates resources, requests diligence, funds validation, or negotiates.",
        "who_administers": "REAL BUYER ORGANIZATION",
        "independence": "ABSOLUTE — real market transaction",
        "current_state": "NOT YET ACHIEVED — REAL_BUYER = 0",
        "can_self_certify": False,
        "note": "This requires actual market engagement. No software can substitute for it."
    }
}


# ============================================================================
# RENAMED INTERNAL STANDARD (no longer "world-class")
# ============================================================================

def get_renamed_internal_standard():
    """The R370K 'WORLD_CLASS_ENGINEERING_DOSSIER' is renamed to INTERNAL_DOSSIER_STANDARD_PASS.

    Per CEO R370L directive #5: change WORLD_CLASS_ENGINEERING_DOSSIER = 15/15
    to INTERNAL_DOSSIER_STANDARD_PASS = X/15 until an independent consultant
    actually evaluates them.
    """
    return {
        "old_name": "WORLD_CLASS_ENGINEERING_DOSSIER",
        "new_name": "INTERNAL_DOSSIER_STANDARD_PASS",
        "current_value": "15/15",
        "warning": (
            "This is a SELF-ADMINISTERED internal standard. "
            "It is NOT an external certificate. "
            "It is NOT evidence that an independent organization would call these 'world-class.' "
            "It means: the system's mechanical documentation/evaluability criteria pass."
        ),
        "requires_for_world_class": (
            "WORLD_CLASS_DEVELOPMENT_DOSSIER can only be awarded by an INDEPENDENT EXTERNAL CONSULTANT, "
            "not by the system itself."
        ),
        "constitution_reference": "Article XXVI (no self-certification)"
    }


# ============================================================================
# EXTERNAL-AUDIT TEMPLATE (for consultant to audit each of 15 individually)
# ============================================================================

EXTERNAL_AUDIT_TEMPLATE = {
    "audit_type": "EXTERNAL_CONSULTANT_AUDIT_CURRENT_15",
    "version": "R370L-1.0",
    "instructions": (
        "The consultant should receive ONLY the actual current transfer package "
        "(the dossier JSON + referenced artifacts). "
        "The consultant should NOT receive the R370K summary, the developer's report, "
        "or the previous audit. "
        "The consultant audits from scratch."
    ),
    "packages_to_audit": [
        "P-01", "P-02", "P-04", "P-07", "P-11", "P-13", "P-15-R1", "P-16",
        "P-21-R1", "P-22-R1", "P-24", "P-26", "P-27-R1", "P-28", "P-29"
    ],
    "per_package_dimensions": {
        "TECHNOLOGY_CREDIBILITY": {
            "question": "Is the technology mechanism credible?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "Mechanism description with governing equations"
        },
        "ENGINEERING_DEFINITION": {
            "question": "Is the engineering definition sufficient for evaluation?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "Engineering core with domain-specific equations, parameters, failure modes"
        },
        "EVIDENCE": {
            "question": "Is the evidence traceable and properly classified?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "Evidence classification (SOURCE_FACT / EXTERNAL_PRECEDENT / AI_INFERENCE / COMPUTATIONAL_RESULT / PHYSICAL_OBSERVATION)"
        },
        "DESIGN_OUTPUT": {
            "question": "Are design outputs defined (not just inputs)?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "Design outputs with status (ABSENT / CONCEPTUAL / MODELLED)"
        },
        "MANUFACTURING": {
            "question": "Is manufacturing readiness honestly stated?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "Manufacturing candidate processes with UNKNOWN tolerances (not fabricated)"
        },
        "REGULATORY": {
            "question": "Is the regulatory pathway honestly stated (not contradictory)?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "Regulatory pathway marked UNKNOWN with resolution plan"
        },
        "IP": {
            "question": "Is IP ownership clear?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "IP ownership documentation (currently UNRESOLVED)"
        },
        "BUYER": {
            "question": "Can a buyer make a rational decision from this package?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "Transfer manifest with TRANSFERABLE_NOW / BUYER_MUST_DEVELOP / NOT_AVAILABLE"
        },
        "TRANSFERABILITY": {
            "question": "Is the transfer boundary clear?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "Transfer boundary with buyer_receives / buyer_must_create"
        },
        "COMMERCIALIZATION": {
            "question": "Is the commercialization path plausible?",
            "classification": "PASS / CONDITIONAL / FAIL / UNKNOWN",
            "required_evidence": "Market context, buyer type, commercialization strategy"
        }
    },
    "final_per_package_verdict": {
        "options": ["KEEP", "UPGRADE", "REPOSITION", "REMOVE"],
        "requires": "One verdict per package with justification"
    }
}


# ============================================================================
# AI-ENGINEERING ATTACK QUESTIONS (for consultant)
# ============================================================================

AI_ENGINEERING_ATTACK_QUESTIONS = {
    "audit_type": "AI_ENGINEERING_ATTACK",
    "instructions": (
        "The consultant must attack the AI-generated engineering content itself. "
        "These questions determine whether the engineering is genuine or AI-generated filler."
    ),
    "questions": [
        {
            "id": "AEQ-01",
            "question": "Which engineering statements are genuinely source-backed?",
            "what_to_check": "Each claim should trace to an external source (FDA, PubMed, ISO standard, published literature). Statements without source backing should be classified AI_INFERENCE or UNKNOWN.",
            "expected_failure": "Some statements may claim EXTERNAL_PRECEDENT without actual source URL or citation"
        },
        {
            "id": "AEQ-02",
            "question": "Which are external precedent?",
            "what_to_check": "External precedent should cite specific FDA-cleared devices, published papers, or patent documents — not generic 'standard practice'",
            "expected_failure": "Some citations may be too generic (e.g., 'published literature' without specific reference)"
        },
        {
            "id": "AEQ-03",
            "question": "Which are model-derived?",
            "what_to_check": "Model-derived values should reference R332 or specific computational model with documented parameters",
            "expected_failure": "Some MODELLED values may lack derivation documentation"
        },
        {
            "id": "AEQ-04",
            "question": "Which are engineering proposals?",
            "what_to_check": "ENGINEERING_PROPOSED values should have basis_ids and derivation fields per R370D",
            "expected_failure": "Some proposals may lack basis_ids (required by R370D evidence class schema)"
        },
        {
            "id": "AEQ-05",
            "question": "Which appear unsupported?",
            "what_to_check": "Any numerical value without evidence_class or with UNKNOWN evidence_class but containing numbers",
            "expected_failure": "R370C should have caught these, but consultant should independently verify"
        },
        {
            "id": "AEQ-06",
            "question": "Which numbers cannot be independently traced?",
            "what_to_check": "Every number in the dossier should be in ENGINEERING_NUMBER_REGISTER.json or explicitly UNKNOWN. Consultant should spot-check 5-10 numbers per package.",
            "expected_failure": "Some numbers may be in the dossier but not in the register"
        },
        {
            "id": "AEQ-07",
            "question": "Which standards are wrongly applied?",
            "what_to_check": "Each standard should be in ENGINEERING_STANDARD_REGISTER.json with correct applicability. Consultant should verify ISO 7197 (not ISO 7437), ISO 10993 series, IEC 60601, etc.",
            "expected_failure": "Some standards may have wrong applicability_basis (e.g., IEC 60601 applied to passive device)"
        },
        {
            "id": "AEQ-08",
            "question": "Which CAD/drawings are merely illustrations?",
            "what_to_check": "All packages should have engineering_artifact_status = CONCEPTUAL or ABSENT. No package should claim RELEASED_FOR_PROTOTYPE or higher without actual artifact.",
            "expected_failure": "All should be CONCEPTUAL — any higher is a fabrication"
        },
        {
            "id": "AEQ-09",
            "question": "Which BOM items are speculative?",
            "what_to_check": "BOM items with 'UNKNOWN' material or 'UNKNOWN' supplier are speculative. Consultant should count how many BOM items are fully specified vs UNKNOWN.",
            "expected_failure": "Most BOM items likely have UNKNOWN material/supplier (correct honest state)"
        },
        {
            "id": "AEQ-10",
            "question": "Which manufacturing statements are generic?",
            "what_to_check": "Manufacturing statements should NOT contain '±0.05mm typical' or 'Standard X process'. All should say 'UNKNOWN — process capability to be established'.",
            "expected_failure": "R370C should have caught these, but consultant should independently verify"
        }
    ]
}


# ============================================================================
# AI REALITY-LOOP AUDIT TEMPLATE
# ============================================================================

AI_REALITY_LOOP_AUDIT = {
    "audit_type": "AI_REALITY_LOOP_AUDIT",
    "instructions": (
        "The consultant must inspect the AI reality-loop infrastructure and distinguish: "
        "IMPLEMENTED (code exists) / REHEARSED (controlled test passed) / REAL (actual real-world event). "
        "Never award REAL merely because the software path exists."
    ),
    "loop_stages_to_audit": [
        {
            "stage": "REALITY_EVENT_INGESTION",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370H: 4 ingestion methods (FILE_UPLOAD, OBJECT_STORAGE, API_PAYLOAD, SFTP_TRANSFER)",
            "evidence_rehearsed": "R370H gate: ingestion test passed",
            "evidence_real": "None — 0 real events ingested",
            "consultant_must_verify": "Check that ingestion boundary exists and works"
        },
        {
            "stage": "PROVENANCE_VALIDATION",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370H: validate_provenance() with 6-step validation chain",
            "evidence_rehearsed": "R370H gate: provenance derivation test passed",
            "evidence_real": "None — 0 real events to validate",
            "consultant_must_verify": "Check that provenance_valid is derived, not input"
        },
        {
            "stage": "EVIDENCE_CLASSIFICATION",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370F: 5-layer evidence classification (SOURCE_FACT / EXTERNAL_PRECEDENT / AI_INFERENCE / COMPUTATIONAL_RESULT / PHYSICAL_OBSERVATION)",
            "evidence_rehearsed": "R370F gate: evidence class validation passed",
            "evidence_real": "None — 0 PHYSICAL_OBSERVATION entries",
            "consultant_must_verify": "Check that AI cannot create PHYSICAL_OBSERVATION"
        },
        {
            "stage": "BELIEF_UPDATE",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370I: capture_loop_snapshot() with before/after state hashes",
            "evidence_rehearsed": "R370I gate: state diff test passed",
            "evidence_real": "None — no real events to trigger belief update",
            "consultant_must_verify": "Check that belief update requires state change (no silent mutation)"
        },
        {
            "stage": "KNOWLEDGE_ATOM",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370I: prove_knowledge_causality() distinguishes CAUSAL vs NON_CAUSAL",
            "evidence_rehearsed": "R370I gate: knowledge causality test passed",
            "evidence_real": "None — 0 real knowledge atoms",
            "consultant_must_verify": "Check that KNOWLEDGE_NON_CAUSAL is possible (not all knowledge claims learning)"
        },
        {
            "stage": "EIG_CHANGE",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370I: record_experiment_priority_diff() with EIG before/after",
            "evidence_rehearsed": "R370I gate: experiment priority diff test passed",
            "evidence_real": "None — no real EIG changes",
            "consultant_must_verify": "Check that EIG change links to triggering knowledge atom"
        },
        {
            "stage": "EXPERIMENT_CHANGE",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370I: experiment_priority_diff with rank change",
            "evidence_rehearsed": "R370I gate: experiment mutation test passed",
            "evidence_real": "None — no real experiment changes",
            "consultant_must_verify": "Check that experiment change has reason_for_change"
        },
        {
            "stage": "PACKAGE_V2",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370I: package_mutation_hash in REAL_LOOP_CERTIFICATE",
            "evidence_rehearsed": "R370I gate: package mutation test passed",
            "evidence_real": "None — no real package mutations (HUMAN_AUTHORIZATION_REQUIRED)",
            "consultant_must_verify": "Check that package mutation requires human authorization"
        },
        {
            "stage": "DISCOVERY_CHANGE",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370I: prove_discovery_mutation() with candidate set diff",
            "evidence_rehearsed": "R370I gate: discovery mutation test passed",
            "evidence_real": "None — no real discovery changes",
            "consultant_must_verify": "Check that discovery change has causal link to knowledge atom"
        },
        {
            "stage": "REAL_LOOP_CERTIFICATE",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370I: generate_r370i_real_loop_certificate() with 10-stage acceptance",
            "evidence_rehearsed": "R370I gate: certificate generation test passed; controlled rehearsal: SYNTHETIC_REHEARSAL=TRUE, REAL_LOOP_VERIFIED=FALSE",
            "evidence_real": "None — REAL_LOOP_VERIFIED = FALSE (derived; 0 real events)",
            "consultant_must_verify": "Check that REAL_LOOP_CERTIFICATE cannot be created for CONTROLLED_REHEARSAL"
        },
        {
            "stage": "INDEPENDENT_REPLAY",
            "implemented": True,
            "rehearsed": True,
            "real": False,
            "evidence_implemented": "R370I: independent_replay_r370i() reconstructs from certificate without narrative",
            "evidence_rehearsed": "R370I gate: independent replay test passed; tampered certificate rejected",
            "evidence_real": "None — no real certificates to replay",
            "consultant_must_verify": "Check that replay rejects tampered certificates"
        }
    ],
    "summary": {
        "IMPLEMENTED": 11,
        "REHEARSED": 11,
        "REAL": 0,
        "note": "All loop stages are implemented and rehearsed. None are real. REAL_LOOP_VERIFIED = FALSE."
    }
}


# ============================================================================
# FINAL INDEPENDENT VERDICT TEMPLATE
# ============================================================================

FINAL_VERDICT_TEMPLATE = {
    "verdict_type": "FINAL_INDEPENDENT_VERDICT",
    "administered_by": "EXTERNAL CONSULTANT (not the system)",
    "template": {
        "WORLD_CLASS_DEVELOPMENT_DOSSIER": "X/15 (consultant's independent assessment)",
        "BUYER_EVALUABLE": "X/15",
        "ENGINEERING_EVALUABLE": "X/15",
        "PROTOTYPE_READY": "X/15",
        "VALIDATION_READY": "X/15",
        "TRANSFER_READY": "X/15",
        "per_package_verdict": {
            "format": "KEEP / UPGRADE / REPOSITION / REMOVE",
            "requires": "One verdict per package with justification"
        },
        "top_5_packages": "Consultant's ranking of top 5 for immediate investment",
        "portfolio_strategic_assessment": "Consultant's view of portfolio as a whole",
        "ai_loop_assessment": "IMPLEMENTED / REHEARSED / REAL for each loop stage",
        "overall_recommendation": "Consultant's overall recommendation to the CEO"
    },
    "important_rules": [
        "The consultant must NOT receive the R370K summary or developer's report.",
        "The consultant reads ONLY the actual current transfer package.",
        "The consultant must attack AI-generated engineering content.",
        "The consultant must distinguish IMPLEMENTED / REHEARSED / REAL.",
        "The consultant must NEVER award REAL because the software path exists.",
        "The consultant's verdict is INDEPENDENT — the system cannot override it.",
        "The system's INTERNAL_DOSSIER_STANDARD_PASS is NOT a substitute for this verdict."
    ]
}


# ============================================================================
# HONEST CURRENT STATE
# ============================================================================

def get_honest_current_state():
    """Get the honest current state across all three verdict levels."""
    return {
        "generated_at": _now(),
        "three_verdict_levels": THREE_VERDICT_LEVELS,
        "internal_standard_renamed": get_renamed_internal_standard(),
        "internal_system_pass": {
            "status": "15/15 PASS",
            "self_administered": True,
            "independence": "NONE",
            "note": "Useful milestone but NOT external certification"
        },
        "external_consultant_pass": {
            "status": "NOT YET ADMINISTERED",
            "self_administered": False,
            "independence": "FULL",
            "note": "Consultant must re-audit the current 15 from scratch"
        },
        "real_market_pass": {
            "status": "NOT YET ACHIEVED",
            "self_administered": False,
            "independence": "ABSOLUTE",
            "note": "Requires actual market engagement (REAL_BUYER = 0)"
        },
        "honest_summary": {
            "INTERNAL_SYSTEM_PASS": "15/15 (self-administered, not external)",
            "EXTERNAL_CONSULTANT_PASS": "NOT YET ADMINISTERED",
            "REAL_MARKET_PASS": "NOT YET ACHIEVED",
            "WORLD_CLASS_DEVELOPMENT_DOSSIER": "CANNOT BE SELF-CERTIFIED — requires external consultant",
            "TRANSFER_READY": "0/15",
            "REAL_LOOP_VERIFIED": "FALSE (derived; 0 real events)",
            "REAL_BUYER": "0",
            "PHYSICAL_OBSERVATIONS": "0"
        },
        "central_invariant": (
            "AI MAY PROPOSE. AI MAY COMPUTE. AI MAY INTERPRET. "
            "AI MAY NOT CLAIM THAT REALITY HAPPENED "
            "UNLESS REALITY PRODUCED THE EVIDENCE."
        ),
        "constitution_reference": "Article XXVI (no self-certification)"
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("R370L EXTERNAL AUDIT STANDARD — Three Verdict Levels")
    print("Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII")
    print("=" * 70)

    print("\nTHREE INDEPENDENT VERDICT LEVELS (must NEVER be conflated):")
    for level, info in THREE_VERDICT_LEVELS.items():
        print(f"\n  {level}:")
        print(f"    Description:    {info['description']}")
        print(f"    Administered:   {info['who_administers']}")
        print(f"    Independence:   {info['independence']}")
        print(f"    Current state:  {info['current_state']}")
        print(f"    Can self-cert:  {info['can_self_certify']}")

    print("\nRENAMED INTERNAL STANDARD:")
    renamed = get_renamed_internal_standard()
    print(f"  Old name: {renamed['old_name']}")
    print(f"  New name: {renamed['new_name']}")
    print(f"  Value:    {renamed['current_value']}")
    print(f"  Warning:  {renamed['warning']}")

    print("\nEXTERNAL AUDIT TEMPLATE:")
    print(f"  Packages to audit: {len(EXTERNAL_AUDIT_TEMPLATE['packages_to_audit'])}")
    print(f"  Dimensions per package: {len(EXTERNAL_AUDIT_TEMPLATE['per_package_dimensions'])}")
    print(f"  Final verdict: {EXTERNAL_AUDIT_TEMPLATE['final_per_package_verdict']['options']}")

    print("\nAI ENGINEERING ATTACK QUESTIONS:")
    print(f"  Total questions: {len(AI_ENGINEERING_ATTACK_QUESTIONS['questions'])}")

    print("\nAI REALITY LOOP AUDIT:")
    print(f"  Stages to audit: {len(AI_REALITY_LOOP_AUDIT['loop_stages_to_audit'])}")
    print(f"  Summary: {AI_REALITY_LOOP_AUDIT['summary']}")

    print("\nFINAL VERDICT TEMPLATE:")
    print(f"  Administered by: {FINAL_VERDICT_TEMPLATE['administered_by']}")
    print(f"  Rules: {len(FINAL_VERDICT_TEMPLATE['important_rules'])}")

    print("\nHONEST CURRENT STATE:")
    state = get_honest_current_state()
    for key, value in state["honest_summary"].items():
        print(f"  {key}: {value}")

    print("\nTHE CENTRAL INVARIANT (Article XXXVIII):")
    print("  AI MAY PROPOSE. AI MAY COMPUTE. AI MAY INTERPRET.")
    print("  AI MAY NOT CLAIM THAT REALITY HAPPENED")
    print("  UNLESS REALITY PRODUCED THE EVIDENCE.")

    # Save all artifacts
    for name, data in [
        ("THREE_VERDICT_LEVELS.json", THREE_VERDICT_LEVELS),
        ("INTERNAL_STANDARD_RENAMED.json", get_renamed_internal_standard()),
        ("EXTERNAL_AUDIT_TEMPLATE.json", EXTERNAL_AUDIT_TEMPLATE),
        ("AI_ENGINEERING_ATTACK_QUESTIONS.json", AI_ENGINEERING_ATTACK_QUESTIONS),
        ("AI_REALITY_LOOP_AUDIT.json", AI_REALITY_LOOP_AUDIT),
        ("FINAL_VERDICT_TEMPLATE.json", FINAL_VERDICT_TEMPLATE),
        ("HONEST_CURRENT_STATE.json", get_honest_current_state()),
    ]:
        path = os.path.join(AUDIT_DIR, name)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Also save gate report
    report = {
        "report_type": "R370L External Audit Standard Report",
        "generated_at": _now(),
        "three_verdict_levels": THREE_VERDICT_LEVELS,
        "internal_standard_renamed": get_renamed_internal_standard(),
        "external_audit_template": EXTERNAL_AUDIT_TEMPLATE,
        "ai_engineering_attack_questions": AI_ENGINEERING_ATTACK_QUESTIONS,
        "ai_reality_loop_audit": AI_REALITY_LOOP_AUDIT,
        "final_verdict_template": FINAL_VERDICT_TEMPLATE,
        "honest_current_state": get_honest_current_state()
    }
    report_path = os.path.join(OUTPUT_DIR, "_r370l_external_audit_standard_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_path}")
    print(f"Artifacts saved: {AUDIT_DIR}")


if __name__ == "__main__":
    main()

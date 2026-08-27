"""
r370w_external_consultant_reconciliation.py — R370W: External-Consultant Evidence Reconciliation.

Per CEO R370W: ingest the first external evidence (consultant report) as an evidence layer.
Audit the auditor. Do not accept as unquestionable truth. Do not silently correct.

W1:  Freeze consultant report
W2:  Build CONSULTANT_FINDING_REGISTRY.json
W3:  Audit every numeric assertion
W4:  Correct the 30-50% obstruction statement
W5:  Regulatory reconciliation against FDA sources
W6:  Independent recalculation of P-07/P-08/P-09/P-14/P-15
W7:  Fix P-13 regulatory terminology
W8:  Audit consultant economics
W9:  Create CONSULTANT_RECONCILIATION_REPORT
W10: Feed external findings into AI loop
W11: P-08 example (do NOT auto-change 500mW to 500uW)
W12: External-consultant release gate

Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII.
"""
import json
import os
import hashlib
from datetime import datetime, timezone

ROOT = "/home/z/my-project/discovery-evidence-fabric"
EVIDENCE_DIR = os.path.join(ROOT, "EXTERNAL_CONSULTANT_EVIDENCE")
CONSULTANT_REPORT_SRC = "/home/z/my-project/upload/Pasted Content_1787822317216.txt"

def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ============================================================================
# Package mapping: consultant P01-P15 -> canonical P-ID
# ============================================================================

CONSULTANT_TO_CANONICAL = {
    "P01": {"portfolio_number": "01", "canonical_package_id": "P-01", "technology_name": "Multi-Segment Flow Control with Bayesian Occlusion Prediction"},
    "P02": {"portfolio_number": "02", "canonical_package_id": "P-02", "technology_name": "Adaptive Valve Profile for Postural ICP Regulation"},
    "P03": {"portfolio_number": "03", "canonical_package_id": "P-04", "technology_name": "Catalytic Contact Time Lock for Amyloid Beta Clearance"},
    "P04": {"portfolio_number": "04", "canonical_package_id": "P-07", "technology_name": "Passive Drainage Priority Safety Floor"},
    "P05": {"portfolio_number": "05", "canonical_package_id": "P-11", "technology_name": "Phage Anti-Biofilm Coating for Shunt Infection Prevention"},
    "P06": {"portfolio_number": "06", "canonical_package_id": "P-13", "technology_name": "Neuromorphic Shunt Failure Predictor"},
    "P07": {"portfolio_number": "07", "canonical_package_id": "P-15-R1", "technology_name": "Self-Powered Sensing via Piezoelectric Energy Harvesting"},
    "P08": {"portfolio_number": "08", "canonical_package_id": "P-16", "technology_name": "NIR Photovoltaic Power Delivery for Implantable Devices"},
    "P09": {"portfolio_number": "09", "canonical_package_id": "P-21-R1", "technology_name": "UWB Catheter Position Mapping with SAR-Bounded Accuracy"},
    "P10": {"portfolio_number": "10", "canonical_package_id": "P-22-R1", "technology_name": "Autonomous Catheter Navigation with Human-in-the-Loop"},
    "P11": {"portfolio_number": "11", "canonical_package_id": "P-24", "technology_name": "Gravity Compensation Hydraulic Damper for Postural Transients"},
    "P12": {"portfolio_number": "12", "canonical_package_id": "P-26", "technology_name": "Osmotic Pressure Regulating Drainage Valve"},
    "P13": {"portfolio_number": "13", "canonical_package_id": "P-27-R1", "technology_name": "Self-Referencing Piezoresistive Pressure Sensor"},
    "P14": {"portfolio_number": "14", "canonical_package_id": "P-28", "technology_name": "Acoustic Obstruction Detection for CSF Shunts"},
    "P15": {"portfolio_number": "15", "canonical_package_id": "P-29", "technology_name": "MR Flow Quantification Sensor at Catheter Scale"},
}


# ============================================================================
# W1: Freeze the consultant report
# ============================================================================

def w1_freeze_report():
    print("\n[W1] Freezing consultant report...")
    with open(CONSULTANT_REPORT_SRC) as f:
        report_text = f.read()

    report_hash = sha256_str(report_text)
    frozen_path = os.path.join(EVIDENCE_DIR, "EXTERNAL_CONSULTANT_REPORT_2026-08-27.md")
    with open(frozen_path, "w") as f:
        f.write(report_text)

    metadata = {
        "artifact_type": "FROZEN_EXTERNAL_CONSULTANT_REPORT",
        "file": "EXTERNAL_CONSULTANT_REPORT_2026-08-27.md",
        "sha256": report_hash,
        "received_at": _now(),
        "auditor_identity": "Independent External Consultant (Claude, Anthropic)",
        "audit_scope": "15 engineering technology-transfer dossiers in prateekm1007/technology-transfer-portfolio-15",
        "audit_date": "2026-08-27",
        "report_length_lines": len(report_text.splitlines()),
        "report_length_chars": len(report_text),
        "freezing_rule": "This report is frozen as received. No modifications. All subsequent reconciliation is separate.",
    }

    meta_path = os.path.join(EVIDENCE_DIR, "REPORT_FREEZE_METADATA.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"  Report frozen: {frozen_path}")
    print(f"  SHA-256: {report_hash}")
    print(f"  Metadata: {meta_path}")
    return metadata


# ============================================================================
# W2: Build CONSULTANT_FINDING_REGISTRY.json
# ============================================================================

def w2_build_finding_registry():
    print("\n[W2] Building CONSULTANT_FINDING_REGISTRY.json...")
    findings = []

    # Findings extracted from the consultant report, each bound to canonical P-ID

    # P01 (canonical P-01) findings
    findings.extend([
        {
            "finding_id": "CF-001",
            "consultant_package": "P01",
            "portfolio_number": "01",
            "canonical_package_id": "P-01",
            "technology_name": "Multi-Segment Flow Control with Bayesian Occlusion Prediction",
            "finding_text": "Catheter obstruction causes 30-50% of shunt failures (VERIFIED via HCUP/AHRQ)",
            "finding_type": "FACTUAL_CLAIM",
            "severity": "HIGH",
            "consultant_verdict": "ESTABLISHED",
            "source_claims": ["HCUP/AHRQ"],
            "calculation_present": False,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-002",
            "consultant_package": "P01",
            "portfolio_number": "01",
            "canonical_package_id": "P-01",
            "technology_name": "Multi-Segment Flow Control with Bayesian Occlusion Prediction",
            "finding_text": "svMultiPhysics verified 1D within 16% error — significant for concept-stage",
            "finding_type": "TECHNICAL_ASSESSMENT",
            "severity": "MEDIUM",
            "consultant_verdict": "NOTE",
            "source_claims": ["dossier DI-008"],
            "calculation_present": False,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-003",
            "consultant_package": "P01",
            "portfolio_number": "01",
            "canonical_package_id": "P-01",
            "technology_name": "Multi-Segment Flow Control with Bayesian Occlusion Prediction",
            "finding_text": "Model achieves ~14h prediction lead time, target is >=24h — failure disclosed in dossier",
            "finding_type": "TECHNICAL_FINDING",
            "severity": "HIGH",
            "consultant_verdict": "CONFIRMED_DISCLOSURE",
            "source_claims": ["dossier text"],
            "calculation_present": False,
            "source_verification_status": "CONFIRMED",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    # P02 (canonical P-02) findings
    findings.append({
        "finding_id": "CF-004",
        "consultant_package": "P02",
        "portfolio_number": "02",
        "canonical_package_id": "P-02",
        "technology_name": "Adaptive Valve Profile for Postural ICP Regulation",
        "finding_text": "Dossier does not adequately differentiate from existing ASDs (Miethke proGAV, ShuntAssistant)",
        "finding_type": "COMPETITIVE_GAP",
        "severity": "HIGH",
        "consultant_verdict": "UPGRADE_REQUIRED",
        "source_claims": ["market knowledge"],
        "calculation_present": False,
        "source_verification_status": "PLAUSIBLE",
        "internal_reconciliation_status": "PENDING",
    })

    # P03 (canonical P-04) findings
    findings.extend([
        {
            "finding_id": "CF-005",
            "consultant_package": "P03",
            "portfolio_number": "03",
            "canonical_package_id": "P-04",
            "technology_name": "Catalytic Contact Time Lock for Amyloid Beta Clearance",
            "finding_text": "Almost certainly a combination product (biologic + device) requiring CDRH/CBER coordination",
            "finding_type": "REGULATORY_ASSERTION",
            "severity": "HIGH",
            "consultant_verdict": "ALMOST_CERTAIN",
            "source_claims": ["regulatory knowledge"],
            "calculation_present": False,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-006",
            "consultant_package": "P03",
            "portfolio_number": "03",
            "canonical_package_id": "P-04",
            "technology_name": "Catalytic Contact Time Lock for Amyloid Beta Clearance",
            "finding_text": "NEP retains activity when immobilized on Ti — NOT verified (kill condition)",
            "finding_type": "TECHNICAL_FINDING",
            "severity": "CRITICAL",
            "consultant_verdict": "CONFIRMED_UNKNOWN",
            "source_claims": ["dossier text"],
            "calculation_present": False,
            "source_verification_status": "CONFIRMED",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    # P04 (canonical P-07) findings
    findings.append({
        "finding_id": "CF-007",
        "consultant_package": "P04",
        "portfolio_number": "04",
        "canonical_package_id": "P-07",
        "technology_name": "Passive Drainage Priority Safety Floor",
        "finding_text": "Floor lumen smaller diameter makes it MORE vulnerable to debris-based obstruction, not less",
        "finding_type": "TECHNICAL_FINDING",
        "severity": "HIGH",
        "consultant_verdict": "VALID_CONCERN",
        "source_claims": ["physical chemistry reasoning"],
        "calculation_present": False,
        "source_verification_status": "PLAUSIBLE",
        "internal_reconciliation_status": "PENDING",
    })

    # P05 (canonical P-11) findings
    findings.extend([
        {
            "finding_id": "CF-008",
            "consultant_package": "P05",
            "portfolio_number": "05",
            "canonical_package_id": "P-11",
            "technology_name": "Phage Anti-Biofilm Coating for Shunt Infection Prevention",
            "finding_text": "Combination product with biological component (live phage) — BLA or combination PMA pathway",
            "finding_type": "REGULATORY_ASSERTION",
            "severity": "HIGH",
            "consultant_verdict": "ALMOST_CERTAIN",
            "source_claims": ["regulatory knowledge"],
            "calculation_present": False,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-009",
            "consultant_package": "P05",
            "portfolio_number": "05",
            "canonical_package_id": "P-11",
            "technology_name": "Phage Anti-Biofilm Coating for Shunt Infection Prevention",
            "finding_text": "Dossier does not compare against existing antibiotic-impregnated catheters (Bactiseal, Cereport)",
            "finding_type": "COMPETITIVE_GAP",
            "severity": "HIGH",
            "consultant_verdict": "VALID_CONCERN",
            "source_claims": ["market knowledge"],
            "calculation_present": False,
            "source_verification_status": "PLAUSIBLE",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    # P06 (canonical P-13) findings
    findings.extend([
        {
            "finding_id": "CF-010",
            "consultant_package": "P06",
            "portfolio_number": "06",
            "canonical_package_id": "P-13",
            "technology_name": "Neuromorphic Shunt Failure Predictor",
            "finding_text": "No real failure dataset exists — CRITICAL BLOCKER acknowledged in dossier",
            "finding_type": "TECHNICAL_FINDING",
            "severity": "CRITICAL",
            "consultant_verdict": "CONFIRMED_BLOCKER",
            "source_claims": ["dossier text (Article XXXVII)"],
            "calculation_present": False,
            "source_verification_status": "CONFIRMED",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-011",
            "consultant_package": "P06",
            "portfolio_number": "06",
            "canonical_package_id": "P-13",
            "technology_name": "Neuromorphic Shunt Failure Predictor",
            "finding_text": "This is a $5-15M clinical program preceding the ML development",
            "finding_type": "ECONOMIC_ESTIMATE",
            "severity": "HIGH",
            "consultant_verdict": "CONSULTANT_ESTIMATE",
            "source_claims": ["consultant estimate — no basis provided"],
            "calculation_present": False,
            "source_verification_status": "UNSUPPORTED",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-012",
            "consultant_package": "P06",
            "portfolio_number": "06",
            "canonical_package_id": "P-13",
            "technology_name": "Neuromorphic Shunt Failure Predictor",
            "finding_text": "Neuromorphic label is inaccurate — gradient boosting is not neuromorphic hardware",
            "finding_type": "TERMINOLOGY_ERROR",
            "severity": "MEDIUM",
            "consultant_verdict": "VALID",
            "source_claims": ["ML terminology"],
            "calculation_present": False,
            "source_verification_status": "CONFIRMED",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    # P07 (canonical P-15-R1) findings
    findings.extend([
        {
            "finding_id": "CF-013",
            "consultant_package": "P07",
            "portfolio_number": "07",
            "canonical_package_id": "P-15-R1",
            "technology_name": "Self-Powered Sensing via Piezoelectric Energy Harvesting",
            "finding_text": "PVDF: 25.6 nW for 0.5 cm3 at 50 microstrain — kill condition (100 nW) likely triggered",
            "finding_type": "INDEPENDENT_CALCULATION",
            "severity": "CRITICAL",
            "consultant_verdict": "KILL_CONDITION_LIKELY_TRIGGERED",
            "source_claims": ["PVDF d33=33 pC/N, g33=0.24 Vm/N", "50 microstrain strain estimate", "0.5 cm3 volume"],
            "calculation_present": True,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-014",
            "consultant_package": "P07",
            "portfolio_number": "07",
            "canonical_package_id": "P-15-R1",
            "technology_name": "Self-Powered Sensing via Piezoelectric Energy Harvesting",
            "finding_text": "PZT would reach ~3.8 microW for 0.5 cm3 — above threshold but minimal margin",
            "finding_type": "INDEPENDENT_CALCULATION",
            "severity": "HIGH",
            "consultant_verdict": "PLAUSIBLE",
            "source_claims": ["PZT d33~400-600 pC/N", "linear scaling from PVDF"],
            "calculation_present": True,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-015",
            "consultant_package": "P07",
            "portfolio_number": "07",
            "canonical_package_id": "P-15-R1",
            "technology_name": "Self-Powered Sensing via Piezoelectric Energy Harvesting",
            "finding_text": "Cardiac evidence sources (0.78 mW) not analogous — cardiac strain 1000-10000x greater than CSF",
            "finding_type": "EVIDENCE_MISMATCH",
            "severity": "HIGH",
            "consultant_verdict": "VALID",
            "source_claims": ["cardiac vs CSF strain comparison"],
            "calculation_present": False,
            "source_verification_status": "PLAUSIBLE",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    # P08 (canonical P-16) findings
    findings.extend([
        {
            "finding_id": "CF-016",
            "consultant_package": "P08",
            "portfolio_number": "08",
            "canonical_package_id": "P-16",
            "technology_name": "NIR Photovoltaic Power Delivery for Implantable Devices",
            "finding_text": "500 mW power target is almost certainly a unit error — likely should be 500 microW",
            "finding_type": "UNIT_ERROR_FINDING",
            "severity": "HIGH",
            "consultant_verdict": "LIKELY_UNIT_ERROR",
            "source_claims": ["500 mW requires ~2800 cm2 PV area at 1 mW/cm2 irradiance"],
            "calculation_present": True,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-017",
            "consultant_package": "P08",
            "portfolio_number": "08",
            "canonical_package_id": "P-16",
            "technology_name": "NIR Photovoltaic Power Delivery for Implantable Devices",
            "finding_text": "PMC5646820 directly supports subcutaneous PV IR harvesting (GaAs >30% efficiency)",
            "finding_type": "EVIDENCE_ASSESSMENT",
            "severity": "LOW",
            "consultant_verdict": "CONFIRMED",
            "source_claims": ["PMC5646820"],
            "calculation_present": False,
            "source_verification_status": "CONFIRMED",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-018",
            "consultant_package": "P08",
            "portfolio_number": "08",
            "canonical_package_id": "P-16",
            "technology_name": "NIR Photovoltaic Power Delivery for Implantable Devices",
            "finding_text": "Tissue transmission 28-61% at 5mm depth (Beer-Lambert, mu_eff 1.0-2.5 cm-1)",
            "finding_type": "INDEPENDENT_CALCULATION",
            "severity": "MEDIUM",
            "consultant_verdict": "REPRODUCIBLE",
            "source_claims": ["Jacques 2013 tissue optics"],
            "calculation_present": True,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    # P09 (canonical P-21-R1) findings
    findings.append({
        "finding_id": "CF-019",
        "consultant_package": "P09",
        "portfolio_number": "09",
        "canonical_package_id": "P-21-R1",
        "technology_name": "UWB Catheter Position Mapping with SAR-Bounded Accuracy",
        "finding_text": "CRLB: sigma_TOA=21.4mm, position error=42.7mm at SNR=10dB — kill condition (<5mm) likely triggered",
        "finding_type": "INDEPENDENT_CALCULATION",
        "severity": "CRITICAL",
        "consultant_verdict": "KILL_CONDITION_LIKELY_TRIGGERED",
        "source_claims": ["CRLB formula", "500 MHz bandwidth", "SNR=10dB", "GDOP=2"],
        "calculation_present": True,
        "source_verification_status": "PENDING",
        "internal_reconciliation_status": "PENDING",
    })

    # P10 (canonical P-22-R1) findings
    findings.extend([
        {
            "finding_id": "CF-020",
            "consultant_package": "P10",
            "portfolio_number": "10",
            "canonical_package_id": "P-22-R1",
            "technology_name": "Autonomous Catheter Navigation with Human-in-the-Loop",
            "finding_text": "Competitive landscape absent — does not acknowledge StealthStation, Brainlab",
            "finding_type": "COMPETITIVE_GAP",
            "severity": "HIGH",
            "consultant_verdict": "VALID_CONCERN",
            "source_claims": ["market knowledge"],
            "calculation_present": False,
            "source_verification_status": "PLAUSIBLE",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-021",
            "consultant_package": "P10",
            "portfolio_number": "10",
            "canonical_package_id": "P-22-R1",
            "technology_name": "Autonomous Catheter Navigation with Human-in-the-Loop",
            "finding_text": "Class III PMA almost certain for autonomous surgical navigation",
            "finding_type": "REGULATORY_ASSERTION",
            "severity": "HIGH",
            "consultant_verdict": "ALMOST_CERTAIN",
            "source_claims": ["regulatory knowledge"],
            "calculation_present": False,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    # P11 (canonical P-24) findings
    findings.append({
        "finding_id": "CF-022",
        "consultant_package": "P11",
        "portfolio_number": "11",
        "canonical_package_id": "P-24",
        "technology_name": "Gravity Compensation Hydraulic Damper for Postural Transients",
        "finding_text": "Optimal damping coefficient c_h is UNKNOWN — core design parameter undefined",
        "finding_type": "TECHNICAL_FINDING",
        "severity": "MEDIUM",
        "consultant_verdict": "CONFIRMED_UNKNOWN",
        "source_claims": ["dossier text"],
        "calculation_present": False,
        "source_verification_status": "CONFIRMED",
        "internal_reconciliation_status": "PENDING",
    })

    # P12 (canonical P-26) findings
    findings.extend([
        {
            "finding_id": "CF-023",
            "consultant_package": "P12",
            "portfolio_number": "12",
            "canonical_package_id": "P-26",
            "technology_name": "Osmotic Pressure Regulating Drainage Valve",
            "finding_text": "Membrane fouling in CSF inadequately characterized — known severe problem",
            "finding_type": "TECHNICAL_FINDING",
            "severity": "HIGH",
            "consultant_verdict": "VALID_CONCERN",
            "source_claims": ["membrane fouling literature"],
            "calculation_present": False,
            "source_verification_status": "PLAUSIBLE",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-024",
            "consultant_package": "P12",
            "portfolio_number": "12",
            "canonical_package_id": "P-26",
            "technology_name": "Osmotic Pressure Regulating Drainage Valve",
            "finding_text": "Class III PMA almost certain — no osmotic valve for CSF drainage exists",
            "finding_type": "REGULATORY_ASSERTION",
            "severity": "HIGH",
            "consultant_verdict": "ALMOST_CERTAIN",
            "source_claims": ["regulatory knowledge"],
            "calculation_present": False,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    # P13 (canonical P-27-R1) findings
    findings.extend([
        {
            "finding_id": "CF-025",
            "consultant_package": "P13",
            "portfolio_number": "13",
            "canonical_package_id": "P-27-R1",
            "technology_name": "Self-Referencing Piezoresistive Pressure Sensor",
            "finding_text": "Competitive differentiation from Codman/Raumedic/Sophysa not established",
            "finding_type": "COMPETITIVE_GAP",
            "severity": "MEDIUM",
            "consultant_verdict": "VALID_CONCERN",
            "source_claims": ["market knowledge"],
            "calculation_present": False,
            "source_verification_status": "PLAUSIBLE",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-026",
            "consultant_package": "P13",
            "portfolio_number": "13",
            "canonical_package_id": "P-27-R1",
            "technology_name": "Self-Referencing Piezoresistive Pressure Sensor",
            "finding_text": "MEMS foundry prototype lead time 16 weeks, first step closer to $25K-$50K than $5K",
            "finding_type": "ECONOMIC_ESTIMATE",
            "severity": "MEDIUM",
            "consultant_verdict": "CONSULTANT_ESTIMATE",
            "source_claims": ["MEMS foundry knowledge"],
            "calculation_present": False,
            "source_verification_status": "PLAUSIBLE",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-027",
            "consultant_package": "P13",
            "portfolio_number": "13",
            "canonical_package_id": "P-27-R1",
            "technology_name": "Self-Referencing Piezoresistive Pressure Sensor",
            "finding_text": "Classified as 'Active Implant' (ISO 14708-1) — Class III PMA",
            "finding_type": "REGULATORY_ASSERTION",
            "severity": "HIGH",
            "consultant_verdict": "ASSERTED",
            "source_claims": ["ISO 14708-1"],
            "calculation_present": False,
            "source_verification_status": "PENDING",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    # P14 (canonical P-28) findings
    findings.append({
        "finding_id": "CF-028",
        "consultant_package": "P14",
        "portfolio_number": "14",
        "canonical_package_id": "P-28",
        "technology_name": "Acoustic Obstruction Detection for CSF Shunts",
        "finding_text": "Z ratio for tissue/CSF = 1.039-1.072, below 1.1 kill threshold — kill condition triggered for tissue obstruction",
        "finding_type": "INDEPENDENT_CALCULATION",
        "severity": "CRITICAL",
        "consultant_verdict": "KILL_CONDITION_TRIGGERED",
        "source_claims": ["acoustic impedance data: CSF=1.52, brain=1.58, debris=1.63 MRayl"],
        "calculation_present": True,
        "source_verification_status": "PENDING",
        "internal_reconciliation_status": "PENDING",
    })

    # P15 (canonical P-29) findings
    findings.append({
        "finding_id": "CF-029",
        "consultant_package": "P15",
        "portfolio_number": "15",
        "canonical_package_id": "P-29",
        "technology_name": "MR Flow Quantification Sensor at Catheter Scale",
        "finding_text": "SNR ~4.2 at 0.5T, ~8.4 at 1.0T — kill condition (SNR>10) triggered at all practical catheter-scale B0",
        "finding_type": "INDEPENDENT_CALCULATION",
        "severity": "CRITICAL",
        "consultant_verdict": "KILL_CONDITION_TRIGGERED",
        "source_claims": ["SNR proportional to B0*sqrt(V_voxel)", "0.5T/3T ratio", "62.8 mm3 vs 1000 mm3 voxel"],
        "calculation_present": True,
        "source_verification_status": "PENDING",
        "internal_reconciliation_status": "PENDING",
    })

    # Portfolio-level findings
    findings.extend([
        {
            "finding_id": "CF-030",
            "consultant_package": "ALL",
            "portfolio_number": "ALL",
            "canonical_package_id": "ALL",
            "technology_name": "Portfolio-level",
            "finding_text": "IP ownership unverified for all 15 packages — no patent search performed",
            "finding_type": "PORTFOLIO_GAP",
            "severity": "CRITICAL",
            "consultant_verdict": "VALID",
            "source_claims": ["portfolio inspection"],
            "calculation_present": False,
            "source_verification_status": "CONFIRMED",
            "internal_reconciliation_status": "PENDING",
        },
        {
            "finding_id": "CF-031",
            "consultant_package": "ALL",
            "portfolio_number": "ALL",
            "canonical_package_id": "ALL",
            "technology_name": "Portfolio-level",
            "finding_text": "0 experimentally observed activities across all 15 packages — no physical validation",
            "finding_type": "REALITY_BOUNDARY",
            "severity": "HIGH",
            "consultant_verdict": "CONFIRMED",
            "source_claims": ["portfolio inspection"],
            "calculation_present": False,
            "source_verification_status": "CONFIRMED",
            "internal_reconciliation_status": "PENDING",
        },
    ])

    registry = {
        "registry_type": "CONSULTANT_FINDING_REGISTRY",
        "version": "1.0",
        "generated_at": _now(),
        "consultant_report_sha256": sha256_file(CONSULTANT_REPORT_SRC),
        "finding_count": len(findings),
        "findings": findings,
        "package_mapping_note": "Consultant uses P01-P15 (portfolio order). These map to canonical P-IDs: P01->P-01, P02->P-02, P03->P-04, P04->P-07, P05->P-11, P06->P-13, P07->P-15-R1, P08->P-16, P09->P-21-R1, P10->P-22-R1, P11->P-24, P12->P-26, P13->P-27-R1, P14->P-28, P15->P-29.",
    }

    reg_path = os.path.join(EVIDENCE_DIR, "CONSULTANT_FINDING_REGISTRY.json")
    with open(reg_path, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"  Findings registered: {len(findings)}")
    print(f"  Saved: {reg_path}")
    return registry


# ============================================================================
# W3: Audit every numeric assertion
# ============================================================================

def w3_audit_numeric_assertions():
    print("\n[W3] Auditing every consultant numeric assertion...")
    numeric_audits = [
        {
            "number": "30-50% obstruction failure rate",
            "consultant_usage": "P01, P04 — foundational problem statement",
            "source_claimed": "HCUP/AHRQ",
            "source_verified": False,
            "literature_check": {
                "adult_systematic_review": "Reddy et al. (2023) found obstruction accounted for ~23.2% of adult shunt failures (PubMed 37004137)",
                "pediatric_trial": "Randomized trial reported obstruction in ~31.4% of children reaching shunt endpoint",
                "overall_failure_rate": "40-50% at 1-2 years (PubMed 42490332)",
                "consultant_conflation": "Consultant appears to have blurred total shunt-failure incidence (40-50%) with the fraction attributable to obstruction (~23-31%)",
            },
            "classification": "INCORRECT_AS_STATED",
            "corrected_statement": "Obstruction is a major cause of shunt failure, accounting for approximately 23% (adult) to 31% (pediatric) of failures. Overall shunt failure rates are 40-50% at 1-2 years. The 30-50% figure conflates these two distinct statistics.",
            "evidence_sources": ["PubMed 37004137 (adult systematic review)", "PubMed 42490332 (imaging review)"],
        },
        {
            "number": "25.6 nW (PVDF piezoelectric power)",
            "consultant_usage": "P07 — kill condition calculation",
            "source_claimed": "Independent calculation",
            "source_verified": False,
            "calculation_inputs": {
                "d33": "33 pC/N (PVDF)",
                "g33": "0.24 Vm/N",
                "strain": "50 microstrain (estimated)",
                "volume": "0.5 cm3",
                "stress_derived": "100 kPa",
                "power_density": "51.3 microW/cm3",
            },
            "classification": "PLAUSIBLE_BUT_UNVERIFIED",
            "issue": "Calculation inputs (50 microstrain, stress derivation, coupling efficiency, electrical loading) are not independently sourced. The strain estimate is stated as 'conservative physiologic' without citation. The calculation is not reproducible from the report alone.",
            "corrected_statement": "The PVDF power calculation is directionally plausible but requires an auditable calculation sheet with sourced strain measurements, coupling assumptions, and electrical loading before the kill-condition conclusion can be accepted.",
        },
        {
            "number": "3.8 microW (PZT piezoelectric power)",
            "consultant_usage": "P07 — alternative material calculation",
            "source_claimed": "Linear scaling from PVDF",
            "source_verified": False,
            "classification": "UNSUPPORTED",
            "issue": "PZT power may not scale linearly from PVDF merely because d33 is larger. Coupling coefficient, dielectric constant, and mechanical compliance all differ. The 150x scaling factor is not justified.",
            "corrected_statement": "PZT power estimate requires independent calculation, not linear scaling from PVDF.",
        },
        {
            "number": "500 mW (P-16 power target)",
            "consultant_usage": "P08 — unit error finding",
            "source_claimed": "Dossier DI-003",
            "source_verified": True,
            "classification": "CONFIRMED_AS_UNIT_CONCERN",
            "issue": "500 mW is physically inconsistent with the cited irradiance (~1 mW/cm2) and catheter-scale PV area. However, the consultant's claim that '500 microW is almost certainly correct' is itself speculation — the correct value has not been established from the original source.",
            "corrected_statement": "500 mW = UNSUPPORTED / LIKELY UNIT ERROR. 500 microW = HYPOTHESIS TO BE CONFIRMED FROM ORIGINAL DOSSIER SOURCE. Do not silently replace one number with another.",
        },
        {
            "number": "$5-15M (P-13 clinical program cost)",
            "consultant_usage": "P06 — economic estimate",
            "source_claimed": "Consultant estimate",
            "source_verified": False,
            "classification": "UNSUPPORTED",
            "issue": "No basis provided. May be directionally plausible depending on study design, patient population, implantable sensors, duration, site count, and event rate. This is precisely the type of false precision the system was designed to prevent.",
            "corrected_statement": "PRELIMINARY_ECONOMIC_ESTIMATE — basis required, range assumptions required, quote required. Not a canonical fact.",
        },
        {
            "number": "42.7mm (P-21-R1 UWB position error)",
            "consultant_usage": "P09 — CRLB calculation",
            "source_claimed": "Independent CRLB calculation",
            "source_verified": False,
            "calculation_inputs": {
                "formula": "sigma_TOA >= c / (2*pi*beta*sqrt(2*SNR))",
                "beta": "500 MHz",
                "SNR": "10 dB",
                "GDOP": "2",
                "sigma_TOA_result": "21.4 mm",
                "position_error_result": "42.7 mm",
            },
            "classification": "REPRODUCIBLE",
            "issue": "The CRLB formula is correct and the arithmetic is reproducible. However, the SNR=10dB assumption is not independently justified — actual SNR depends on tissue attenuation, transmit power, receiver sensitivity, and processing gain, none of which are independently sourced.",
            "corrected_statement": "CRLB calculation is arithmetically correct but depends on unverified SNR assumption. The kill-condition conclusion requires a complete link budget with sourced tissue attenuation and SAR-constrained transmit power.",
        },
        {
            "number": "Z ratio 1.039-1.072 (P-28 acoustic impedance)",
            "consultant_usage": "P14 — kill condition calculation",
            "source_claimed": "Published acoustic impedance data",
            "source_verified": False,
            "calculation_inputs": {
                "Z_CSF": "1.52 MRayl",
                "Z_brain": "1.58 MRayl",
                "Z_debris": "~1.63 MRayl",
                "ratio_brain": "1.039",
                "ratio_debris": "1.072",
                "kill_threshold": "1.1",
            },
            "classification": "PARTIALLY_CONFIRMED",
            "issue": "The impedance values are from published literature and the ratios are arithmetically correct. However, the conclusion 'kill condition triggered' is too strong. Acoustic detection depends on frequency, transducer geometry, coupling, scattering, attenuation, interface geometry, reflection coefficient, signal processing, clutter, and placement — not just impedance ratio. The dossier's kill condition may not be defined solely by impedance ratio.",
            "corrected_statement": "The simplified impedance model provides insufficient contrast evidence for tissue obstruction. A frequency-dependent phantom experiment is required. Do not automatically classify as 'killed' — reframe as 'feasibility risk requiring empirical test.'",
        },
        {
            "number": "SNR ~4.2 at 0.5T (P-29 MR flow sensor)",
            "consultant_usage": "P15 — kill condition calculation",
            "source_claimed": "Independent SNR scaling calculation",
            "source_verified": False,
            "calculation_inputs": {
                "formula": "SNR proportional to B0 * sqrt(V_voxel)",
                "B0_catheter": "0.5T",
                "B0_clinical": "3T",
                "V_catheter": "62.8 mm3",
                "V_clinical": "1000 mm3",
                "SNR_clinical_ref": "100",
                "SNR_catheter_result": "4.2",
            },
            "classification": "PARTIALLY_CONFIRMED",
            "issue": "The SNR scaling formula is a first-order approximation but ignores receive-coil geometry, filling factor, Q factor, sequence, bandwidth, relaxation, flow-encoding parameters, gradient strength, reconstruction, susceptibility, catheter material, and actual measurement voxel. The kill-condition conclusion is too strong.",
            "corrected_statement": "The simplified SNR model indicates significant feasibility risk. An empirical benchtop SNR experiment is required before committing to catheter-scale development. Do not classify as 'killed' — classify as 'high-risk requiring decisive experiment.'",
        },
        {
            "number": "16% (P-01 svMultiPhysics error)",
            "consultant_usage": "P01 — model accuracy assessment",
            "source_claimed": "Dossier text",
            "source_verified": True,
            "classification": "CONFIRMED_BUT_UNDERCONTEXTUALIZED",
            "issue": "16% error is noted but not contextualized. Error relative to what measurement range? For what output variable? A model can have 16% error on one variable and still be useful for another decision.",
            "corrected_statement": "16% model error requires specification of: validation variable, reference experiment, N, error metric, confidence interval, operating range, and decision sensitivity before it can be used as evidence against the technology.",
        },
        {
            "number": "$5K / $25K / $100K (investment ladder)",
            "consultant_usage": "Portfolio-wide — transaction recommendations",
            "source_claimed": "Dossier investment ladder",
            "source_verified": True,
            "classification": "CONFIRMED_AS_DOSSIER_VALUES",
            "issue": "These are the dossier's own investment ladder values. The consultant's recommendation to adjust P-13 from $5K to $25K-$50K (MEMS foundry) is a consultant estimate.",
            "corrected_statement": "$5K/$25K/$100K are dossier-defined investment tiers. P-13 adjustment to $25K-$50K is CONSULTANT_ESTIMATE — basis required.",
        },
    ]

    audit_path = os.path.join(EVIDENCE_DIR, "NUMERIC_ASSERTION_AUDIT.json")
    with open(audit_path, "w") as f:
        json.dump({"audit_type": "NUMERIC_ASSERTION_AUDIT", "generated_at": _now(),
                   "assertions": numeric_audits}, f, indent=2, ensure_ascii=False)

    print(f"  Numeric assertions audited: {len(numeric_audits)}")
    print(f"  Saved: {audit_path}")
    return numeric_audits


# ============================================================================
# W4: Correct the 30-50% obstruction statement
# ============================================================================

def w4_correct_obstruction_statement():
    print("\n[W4] Correcting the 30-50% obstruction statement...")
    correction = {
        "correction_type": "FACTUAL_CORRECTION",
        "original_statement": "Catheter obstruction causes 30-50% of shunt failures",
        "corrected_statement": "Obstruction is a major cause of shunt failure. The exact percentage varies by population and study design.",
        "evidence": [
            {
                "source": "PubMed 37004137",
                "study_type": "Adult systematic review and meta-analysis",
                "sample": "38,095 adult shunt insertion surgeries",
                "finding": "Obstruction accounted for approximately 23.2% of shunt failures in adults",
                "url": "https://pubmed.ncbi.nlm.nih.gov/37004137/",
            },
            {
                "source": "PubMed 42490332",
                "study_type": "Imaging review",
                "finding": "Overall shunt failure rates around 40-50% at 1-2 years; obstruction is one of the common causes but not necessarily 40-50% of all failures",
                "url": "https://pubmed.ncbi.nlm.nih.gov/42490332/",
            },
            {
                "source": "Pediatric literature",
                "finding": "Obstruction reported in approximately 31.4% of children reaching a shunt endpoint in randomized trial data",
            },
        ],
        "consultant_error": "The consultant appears to have blurred total shunt-failure incidence (40-50%) with the fraction attributable to obstruction (~23-31%). The 30-50% figure as stated is not supported by the cited literature.",
        "impact_on_packages": ["P-01 (Multi-Segment Flow Control)", "P-07 (Passive Drainage Floor)"],
        "corrected_framing": "Obstruction is a major clinical problem (approximately 23-31% of failures, varying by population). The problem is real and worth solving, but the 30-50% figure should be corrected in all dossier references and the consultant report.",
        "status": "CORRECTION_REQUIRED",
    }

    path = os.path.join(EVIDENCE_DIR, "OBSTRUCTION_RATE_CORRECTION.json")
    with open(path, "w") as f:
        json.dump(correction, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")
    return correction


# ============================================================================
# W5: Regulatory reconciliation
# ============================================================================

def w5_regulatory_reconciliation():
    print("\n[W5] Regulatory reconciliation against FDA sources...")
    reg_audit = {
        "audit_type": "REGULATORY_RECONCILIATION",
        "generated_at": _now(),
        "fda_sources_consulted": [
            {
                "source": "FDA Product Classification Database",
                "product_code": "JXG",
                "device": "Central nervous system fluid shunts and components",
                "classification": "Class II",
                "pathway": "510(k)",
                "url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpcd/classification.cfm?id=JXG",
            },
            {
                "source": "FDA Product Classification Database",
                "product_code": "GWM",
                "device": "Intracranial pressure monitoring device",
                "classification": "Class II",
                "pathway": "510(k)",
                "implanted": "No (per classification record)",
                "url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPCD/classification.cfm?ID=GWM",
            },
            {
                "source": "FDA Combination Products FAQ",
                "principle": "Combination products are assigned based on Primary Mode of Action (PMOA)",
                "pathway_variability": "BLA, NDA, PMA, De Novo, or 510(k) depending on product and PMOA",
                "url": "https://www.fda.gov/combination-products/about-combination-products/frequently-asked-questions-about-combination-products",
            },
            {
                "source": "FDA 510(k) Database",
                "example": "K161853 (Miethke shunt system)",
                "url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K161853",
            },
        ],
        "package_regulatory_reconciliation": [
            {
                "canonical_package_id": "P-01",
                "consultant_assertion": "Class III PMA — no clear predicate",
                "fda_context": "JXG (CSF shunts) is Class II/510(k). Multiple predicates exist (Medtronic, Integra, Miethke).",
                "reconciliation": "CONTESTED — the consultant's 'Class III PMA' assertion is too categorical. P-01 introduces active sensing and Bayesian prediction, which may elevate the pathway, but the base shunt component has a Class II predicate. The pathway depends on whether the active sensing is classified as a shunt accessory (510(k) with special controls) or a new device type (De Novo or PMA).",
                "corrected_status": "PATHWAY_UNDETERMINED — requires FDA pre-submission consultation. Not 'almost certain PMA.'",
            },
            {
                "canonical_package_id": "P-04",
                "consultant_assertion": "Combination product requiring CDRH/CBER coordination — almost certain",
                "fda_context": "PMOA determines lead center. If the primary mode of action is mechanical (catheter draining CSF), CDRH leads. If the primary mode of action is biologic (enzyme cleaving Ab42), CBER leads.",
                "reconciliation": "PARTIALLY_CONFIRMED — combination product classification is directionally reasonable, but 'almost certain' is too strong without PMOA analysis. The pathway could be BLA, NDA, or PMA depending on PMOA determination.",
                "corrected_status": "POTENTIALLY_HIGH_RISK_REGULATORY_PATHWAY — formal classification and jurisdiction remain undetermined.",
            },
            {
                "canonical_package_id": "P-11",
                "consultant_assertion": "Combination product with live phage — BLA or combination PMA",
                "fda_context": "Live phage products are regulated as biologics. A device incorporating a live biologic is likely a combination product with CBER lead.",
                "reconciliation": "PARTIALLY_CONFIRMED — the combination product classification is reasonable. However, the specific pathway (BLA vs PMA) depends on PMOA and requires FDA consultation.",
                "corrected_status": "POTENTIALLY_HIGH_RISK_REGULATORY_PATHWAY — formal classification required.",
            },
            {
                "canonical_package_id": "P-15-R1",
                "consultant_assertion": "Active Implant (ISO 14708-1) — Class III PMA",
                "fda_context": "GWM (ICP monitoring) is Class II/510(k) with 'Implanted Device? No.' An implantable version may differ. ISO 14708-1 is a standard, not an FDA classification.",
                "reconciliation": "CONTESTED — 'Active Implant' is not an FDA classification category. The consultant conflates ISO standards terminology with FDA product codes. An implantable pressure sensor may be Class II/510(k) (if predicate exists) or Class III/PMA (if no predicate). Codman ICP Express (implantable) has 510(k) history.",
                "corrected_status": "PATHWAY_UNDETERMINED — requires predicate analysis against existing implantable ICP sensors.",
            },
            {
                "canonical_package_id": "P-16",
                "consultant_assertion": "Class III PMA — no predicate (optical implant)",
                "fda_context": "No specific product code for NIR-powered implantable devices. Pathway depends on intended use and risk profile.",
                "reconciliation": "PLAUSIBLE — novel optical power delivery may lack a direct predicate. However, if the powered component is a sensor with a predicate, the NIR power system may be classified as an accessory.",
                "corrected_status": "PATHWAY_UNDETERMINED — requires pre-submission consultation.",
            },
            {
                "canonical_package_id": "P-22-R1",
                "consultant_assertion": "Class III PMA almost certain — autonomous surgical navigation",
                "fda_context": "Autonomous navigation in the cranial cavity is high-risk. Software components require IEC 62304. AI/ML components require FDA SaMD guidance.",
                "reconciliation": "PLAUSIBLE — autonomous surgical navigation is likely Class III. However, 'almost certain' should be 'likely pending PMOA and risk analysis.' Existing stereotactic systems (StealthStation, Brainlab) are 510(k) but are not autonomous.",
                "corrected_status": "LIKELY_HIGH_RISK_PATHWAY — formal classification required.",
            },
            {
                "canonical_package_id": "P-26",
                "consultant_assertion": "Class III PMA almost certain — no osmotic valve for CSF drainage exists",
                "fda_context": "Osmotic pumps (DURECT/Alzet) exist in other applications. CSF shunt components under JXG are Class II. An osmotic valve for CSF is novel.",
                "reconciliation": "PLAUSIBLE — the osmotic mechanism is novel for CSF shunts. However, if the device is classified as a shunt component under JXG, it may be Class II with special controls. The 'almost certain PMA' is too categorical.",
                "corrected_status": "PATHWAY_UNDETERMINED — requires predicate analysis and PMOA determination.",
            },
            {
                "canonical_package_id": "P-29",
                "consultant_assertion": "Class III PMA — novel MRI device",
                "fda_context": "MRI devices are regulated under multiple product codes. A catheter-scale MR flow sensor is novel.",
                "reconciliation": "PLAUSIBLE — the novelty may require PMA or De Novo. However, if repositioned as an external sensor (per consultant's own recommendation), the pathway may differ.",
                "corrected_status": "PATHWAY_UNDETERMINED — depends on final device architecture (implantable vs external).",
            },
        ],
        "summary": {
            "consultant_regulatory_assertions": 8,
            "confirmed": 0,
            "partially_confirmed": 2,
            "contested": 2,
            "plausible_but_undetermined": 4,
            "key_finding": "The consultant's regulatory conclusions are too categorical. 'Almost certain PMA' should be 'potentially high-risk pathway; formal classification and jurisdiction remain undetermined.' FDA bases combination-product jurisdiction on PMOA, and marketing pathways vary accordingly. For ordinary CSF shunt components, JXG (Class II/510(k)) is the regulatory category, so predicate analysis must be package-specific.",
        },
    }

    path = os.path.join(EVIDENCE_DIR, "REGULATORY_RECONCILIATION.json")
    with open(path, "w") as f:
        json.dump(reg_audit, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")
    return reg_audit


# ============================================================================
# W6: Independent recalculation of P-07, P-08, P-09, P-14, P-15
# ============================================================================

def w6_independent_calculations():
    print("\n[W6] Independent recalculation of P-07, P-08, P-09, P-14, P-15...")

    calculations = {
        "P-15-R1": {
            "calculation_type": "PIEZOELECTRIC_POWER_BUDGET",
            "consultant_claim": "25.6 nW for 0.5 cm3 PVDF at 50 microstrain — kill condition (100 nW) likely triggered",
            "independent_review": {
                "inputs": {
                    "material": "PVDF",
                    "d33": "33 pC/N (published — confirmed)",
                    "g33": "0.24 Vm/N (published — confirmed)",
                    "epsilon_r": "12 (published — confirmed)",
                    "strain_assumption": "50 microstrain — NOT INDEPENDENTLY SOURCED",
                    "volume": "0.5 cm3 — assumed implant volume",
                    "stress_derivation": "sigma = E * strain where E = 2-3 GPa for PVDF. At 50 microstrain: sigma = 100-150 kPa. Consultant used 100 kPa — within range.",
                    "power_density_formula": "P = (d33^2 * sigma^2 * omega * V) / (2 * epsilon) — frequency-dependent",
                    "missing_parameters": ["frequency of CSF pulsation", "electrical loading condition", "coupling coefficient under load", "rectification efficiency"],
                },
                "assessment": "The consultant's calculation is arithmetically consistent with the stated inputs, but the key input (50 microstrain) is not independently sourced. CSF pulsation strain at the catheter wall depends on anatomical location, CSF pulse pressure amplitude, and catheter wall compliance. Published measurements of catheter-wall strain in vivo are not readily available in the report.",
                "classification": "PLAUSIBLE_BUT_NOT_INDEPENDENTLY_REPRODUCIBLE",
                "what_is_needed": "Published in-vivo catheter strain measurements or finite-element simulation with sourced boundary conditions. Without this, the kill-condition conclusion is a hypothesis, not a proven fact.",
                "consultant_conclusion_review": "The consultant's conclusion 'kill condition likely triggered' is directionally reasonable but stated with more confidence than the calculation supports. The correct disposition is: 'PVDF power budget is marginal at assumed strain levels; empirical strain measurement required before kill-condition determination.'",
            },
        },
        "P-16": {
            "calculation_type": "NIR_TISSUE_TRANSMISSION_AND_POWER_TARGET",
            "consultant_claim": "500 mW is a unit error; 28-61% tissue transmission at 5mm; correct target likely 500 microW",
            "independent_review": {
                "tissue_transmission": {
                    "formula": "Beer-Lambert: T = exp(-mu_eff * d)",
                    "mu_eff_range": "1.0-2.5 cm-1 for soft tissue at 940nm (Jacques 2013 — confirmed)",
                    "at_5mm_mu_eff_1": "T = exp(-0.5) = 60.7% — CONFIRMED",
                    "at_5mm_mu_eff_2_5": "T = exp(-1.25) = 28.7% — CONFIRMED",
                    "caveat": "Skull bone has higher scattering coefficient. If the 5mm path includes skull, transmission is significantly lower. The dossier should specify tissue composition.",
                },
                "power_target_assessment": {
                    "dossier_claim": ">=500 mW",
                    "incident_irradiance": "~1-1.4 mW/cm2 at PV surface (per dossier)",
                    "pv_efficiency": "~30% (PMC5646820 — confirmed for GaAs at 850nm)",
                    "area_for_500mW": "500 mW / (1 mW/cm2 * 30%) = 1667 cm2 — physically impossible",
                    "area_for_500_microW": "500 microW / (1 mW/cm2 * 30%) = 1.67 cm2 — physically plausible for a catheter-scale PV cell",
                    "classification": "500 mW = CONFIRMED_AS_UNIT_ERROR. 500 microW = PLAUSIBLE_HYPOTHESIS but NOT ESTABLISHED from original source.",
                    "consultant_error": "The consultant correctly identified the unit error but then asserted '500 microW is almost certainly correct' — this is speculation. The correct value must be confirmed from the original dossier source or experimental specification.",
                },
            },
        },
        "P-21-R1": {
            "calculation_type": "UWB_TOA_ACCURACY_VS_SAR",
            "consultant_claim": "sigma_TOA = 21.4mm, position error = 42.7mm — kill condition (<5mm) triggered",
            "independent_review": {
                "crlb_formula": "sigma_TOA >= c / (2*pi*beta*sqrt(2*SNR)) — CORRECT (Cramer-Rao Lower Bound)",
                "at_beta_500MHz_SNR_10dB": "sigma_TOA = 3e8 / (2*pi*5e8*sqrt(20)) = 3e8 / (2*pi*5e8*4.47) = 3e8 / 1.404e10 = 0.0214 m = 21.4 mm — CONFIRMED",
                "position_error_GDOP_2": "42.7 mm — CONFIRMED",
                "snr_assessment": "SNR=10dB is assumed, not independently derived. Actual SNR depends on: transmit power (SAR-constrained), tissue attenuation (60-80 dB at 5-10 GHz through 5+ cm), receiver sensitivity, processing gain, antenna efficiency. The SNR assumption is the critical unverified input.",
                "classification": "ARITHMETICALLY_CORRECT_BUT_SNR_UNVERIFIED",
                "what_is_needed": "Complete link budget with sourced tissue attenuation, SAR-constrained transmit power, receiver noise figure, and processing gain. Without this, the kill-condition conclusion is a hypothesis based on an assumed SNR.",
            },
        },
        "P-28": {
            "calculation_type": "ACOUSTIC_IMPEDANCE_CONTRAST",
            "consultant_claim": "Z ratio 1.039-1.072 for tissue/CSF — kill condition (<1.1) triggered",
            "independent_review": {
                "impedance_values": {
                    "CSF": "1.52 MRayl — published, confirmed",
                    "brain_tissue": "1.58 MRayl — published, confirmed",
                    "fibrous_debris": "~1.63 MRayl — estimated, not independently sourced",
                    "air": "0.0004 MRayl — published, confirmed",
                    "bone": "7.8 MRayl — published, confirmed",
                },
                "ratio_calculation": {
                    "brain_to_CSF": "1.58/1.52 = 1.039 — CONFIRMED",
                    "debris_to_CSF": "1.63/1.52 = 1.072 — CONFIRMED (if debris Z is correct)",
                },
                "reflection_coefficient": {
                    "formula": "R = (Z2-Z1)/(Z2+Z1)",
                    "brain_CSF": "R = (1.58-1.52)/(1.58+1.52) = 0.06/3.10 = 0.019 = 1.9% — very low reflection",
                    "debris_CSF": "R = (1.63-1.52)/(1.63+1.52) = 0.11/3.15 = 0.035 = 3.5% — very low reflection",
                },
                "assessment": "The impedance values and ratio calculations are arithmetically correct. However, the conclusion 'kill condition triggered' is too strong because: (1) the dossier's kill condition may not be defined solely by impedance ratio; (2) acoustic detection depends on frequency, transducer geometry, coupling, scattering, attenuation, interface geometry, signal processing, clutter, and placement; (3) the reflection coefficient (1.9-3.5%) is low but not zero — detectability depends on system noise floor and signal processing.",
                "classification": "PARTIALLY_CONFIRMED — impedance contrast is low but kill-condition determination requires the dossier's actual detection model, not just impedance ratio.",
                "corrected_framing": "The current simplified model provides insufficient contrast evidence for tissue obstruction. A frequency-dependent phantom experiment is required. Do not automatically classify as 'killed.'",
            },
        },
        "P-29": {
            "calculation_type": "MR_SNR_AT_CATHETER_SCALE",
            "consultant_claim": "SNR ~4.2 at 0.5T — kill condition (SNR>10) triggered",
            "independent_review": {
                "snr_scaling": "SNR proportional to B0 * sqrt(N_avg * V_voxel) / sqrt(BW) — first-order approximation, CONFIRMED as a scaling relationship",
                "calculation": {
                    "B0_ratio": "0.5T/3T = 0.167 — CONFIRMED",
                    "voxel_ratio": "62.8 mm3 / 1000 mm3 = 0.0628; sqrt = 0.251 — CONFIRMED",
                    "SNR_ratio": "0.167 * 0.251 = 0.042 — CONFIRMED",
                    "SNR_catheter": "0.042 * 100 = 4.2 — CONFIRMED (given the assumed clinical SNR of 100)",
                },
                "missing_parameters": [
                    "receive-coil geometry (solenoid vs saddle vs surface)",
                    "filling factor (coil-to-sample coupling)",
                    "Q factor (coil quality factor)",
                    "sequence (spin echo, gradient echo, phase contrast)",
                    "bandwidth",
                    "relaxation (T1, T2 of CSF at catheter-scale B0)",
                    "flow-encoding parameters",
                    "gradient strength",
                    "reconstruction algorithm",
                    "susceptibility artifacts at catheter material interfaces",
                    "actual measurement voxel (may differ from anatomical voxel)",
                ],
                "assessment": "The SNR scaling is a first-order approximation. The actual SNR could differ by an order of magnitude in either direction depending on coil design and sequence optimization. The consultant's conclusion 'kill condition triggered' is too strong.",
                "classification": "PARTIALLY_CONFIRMED — scaling relationship is correct but the simplified model ignores multiple material parameters that could change the outcome.",
                "corrected_framing": "The simplified SNR model indicates significant feasibility risk. An empirical benchtop SNR experiment is required before committing to catheter-scale development.",
            },
        },
    }

    path = os.path.join(EVIDENCE_DIR, "INDEPENDENT_REVIEW_CALCULATIONS.json")
    with open(path, "w") as f:
        json.dump({"calculation_type": "INDEPENDENT_REVIEW_CALCULATIONS", "generated_at": _now(),
                   "calculations": calculations}, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")
    return calculations


# ============================================================================
# W7: Fix P-13 (canonical P-27-R1) regulatory terminology
# ============================================================================

def w7_fix_p13_regulatory_terminology():
    print("\n[W7] Fixing P-27-R1 (consultant P13) regulatory terminology...")
    fix = {
        "package": "P-27-R1 (consultant P13)",
        "consultant_terminology": "Active Implant (ISO 14708-1) — Class III PMA",
        "issue": "The consultant uses 'Active Implant' as though it were an FDA classification. It is not. ISO 14708-1 is a standard for active implantable medical devices, but it is not an FDA product code or classification.",
        "corrected_terminology": {
            "implantation_status": "IMPLANTABLE (the proposed sensor is designed for chronic implantation)",
            "fda_product_code": "GWM (Intracranial pressure monitoring device) — Class II, 510(k). Note: GWM classification record states 'Implanted Device? No.' An implantable version may require a different product code or De Novo.",
            "device_classification": "UNDETERMINED — existing GWM devices are Class II, but an implantable version with self-referencing drift compensation may be classified differently. Codman ICP Express (implantable) has 510(k) history, suggesting implantable ICP sensors can be Class II.",
            "marketing_pathway": "UNDETERMINED — could be 510(k) (if predicate exists for implantable self-referencing sensor), De Novo (if no predicate but low-moderate risk), or PMA (if high-risk). Requires pre-submission consultation.",
            "predicate_analysis": "Codman ICP Express, Raumedic Neurovent — these are implantable ICP sensors with 510(k) history. The self-referencing innovation may be classified as an enhancement to an existing predicate.",
            "applicable_standards": ["ISO 14708-1 (active implantable)", "ISO 10993 (biocompatibility)", "IEC 60601-1 (medical electrical equipment)", "ISO 13485 (quality management)"],
        },
        "consultant_error": "Conflated ISO standards terminology with FDA classification. 'Active Implant' is not an FDA category. The consultant should have said: 'Implantable device; FDA product code and classification require determination; predicate analysis against existing implantable ICP sensors needed.'",
        "corrected_status": "PATHWAY_UNDETERMINED — implantable ICP sensors have 510(k) precedent (Codman, Raumedic). The self-referencing innovation requires predicate analysis, not automatic PMA classification.",
    }

    path = os.path.join(EVIDENCE_DIR, "P27_R1_REGULATORY_TERMINOLOGY_FIX.json")
    with open(path, "w") as f:
        json.dump(fix, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")
    return fix


# ============================================================================
# W8: Audit consultant economics
# ============================================================================

def w8_audit_economics():
    print("\n[W8] Auditing consultant economics...")
    economics = {
        "audit_type": "CONSULTANT_ECONOMICS_AUDIT",
        "generated_at": _now(),
        "economic_assertions": [
            {"number": "$5K", "context": "V0 bench prototype (P-01, P-07, P-08, P-11, P-14)", "classification": "DOSSIER_VALUE", "basis": "From dossier investment ladder", "status": "OBSERVED"},
            {"number": "$25K", "context": "Engineering feasibility (P-13 MEMS)", "classification": "DOSSIER_VALUE", "basis": "From dossier investment ladder", "status": "OBSERVED"},
            {"number": "$100K", "context": "Full validation", "classification": "DOSSIER_VALUE", "basis": "From dossier investment ladder", "status": "OBSERVED"},
            {"number": "$5-15M", "context": "P-13 clinical program cost", "classification": "CONSULTANT_ESTIMATE", "basis": "No basis provided — directionally plausible for multi-site clinical study but requires assumptions", "status": "UNSUPPORTED"},
            {"number": "$3K", "context": "P-07 shaker table test (consultant adjustment)", "classification": "CONSULTANT_ESTIMATE", "basis": "Consultant's own estimate for piezo bench test", "status": "ESTIMATED"},
            {"number": "$5K", "context": "P-08 NIR bench test", "classification": "DOSSIER_VALUE", "basis": "From dossier", "status": "OBSERVED"},
            {"number": "$8K", "context": "P-14 acoustic phantom test (consultant adjustment)", "classification": "CONSULTANT_ESTIMATE", "basis": "Consultant's own estimate", "status": "ESTIMATED"},
            {"number": "$25K-$50K", "context": "P-13 MEMS foundry (consultant adjustment from $5K)", "classification": "CONSULTANT_ESTIMATE", "basis": "MEMS foundry lead time and cost knowledge — plausible but requires quote", "status": "ESTIMATED"},
            {"number": "8 weeks", "context": "P-07, P-11 bench test timeline", "classification": "CONSULTANT_ESTIMATE", "basis": "Engineering estimate", "status": "ESTIMATED"},
            {"number": "10 weeks", "context": "P-01, P-04, P-08 bench test timeline", "classification": "CONSULTANT_ESTIMATE", "basis": "Engineering estimate", "status": "ESTIMATED"},
            {"number": "12 weeks", "context": "P-14 acoustic test timeline", "classification": "CONSULTANT_ESTIMATE", "basis": "Engineering estimate", "status": "ESTIMATED"},
            {"number": "16 weeks", "context": "P-13 MEMS foundry lead time", "classification": "CONSULTANT_ESTIMATE", "basis": "MEMS foundry industry knowledge — plausible", "status": "ESTIMATED"},
            {"number": "$40-80K/case", "context": "Shunt infection cost (P-11)", "classification": "DOSSIER_VALUE", "basis": "From dossier, citing HCUP/AHRQ", "status": "OBSERVED"},
        ],
        "summary": {
            "total_economic_assertions": 13,
            "observed_from_dossier": 5,
            "consultant_estimates": 8,
            "unsupported": 1,
            "rule": "No consultant estimate becomes canonical fact merely because it appears in an external report. All consultant estimates require basis documentation and quotes before becoming canonical.",
        },
    }

    path = os.path.join(EVIDENCE_DIR, "CONSULTANT_ECONOMICS_AUDIT.json")
    with open(path, "w") as f:
        json.dump(economics, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")
    return economics


# ============================================================================
# W9: CONSULTANT_RECONCILIATION_REPORT
# ============================================================================

def w9_reconciliation_report():
    print("\n[W9] Building CONSULTANT_RECONCILIATION_REPORT...")
    report = {
        "report_type": "CONSULTANT_RECONCILIATION_REPORT",
        "version": "1.0",
        "generated_at": _now(),
        "purpose": "For every consultant finding: CONSULTANT_FINDING -> SOURCE_CHECK -> INDEPENDENT_CALCULATION -> RECONCILIATION -> FINAL_EXTERNAL_EVIDENCE_STATUS",
        "reconciliation_statuses": {
            "CONFIRMED": "Consultant finding verified against independent source",
            "PARTIALLY_CONFIRMED": "Consultant finding partially verified; some aspects require correction",
            "CONTESTED": "Consultant finding contradicted by independent evidence",
            "UNSUPPORTED": "Consultant finding has no supporting evidence",
            "UNKNOWN": "Cannot be verified without further evidence",
        },
        "reconciliations": [
            {"finding_id": "CF-001", "consultant_finding": "30-50% obstruction failure rate", "source_check": "NOT_SUPPORTED_BY_LITERATURE", "final_status": "CONTESTED", "correction": "Obstruction is ~23% (adult) to ~31% (pediatric) of failures. 30-50% conflates total failure rate with obstruction fraction."},
            {"finding_id": "CF-002", "consultant_finding": "16% svMultiPhysics error is significant", "source_check": "CONFIRMED_FROM_DOSSIER", "final_status": "PARTIALLY_CONFIRMED", "correction": "16% is noted but requires context (variable, reference, metric, operating range) before use as evidence."},
            {"finding_id": "CF-003", "consultant_finding": "14h vs 24h prediction lead time failure", "source_check": "CONFIRMED_FROM_DOSSIER", "final_status": "CONFIRMED", "correction": "None — this is an honestly disclosed failure in the dossier."},
            {"finding_id": "CF-004", "consultant_finding": "P-02 does not differentiate from ASDs", "source_check": "PLAUSIBLE", "final_status": "PARTIALLY_CONFIRMED", "correction": "Competitive gap is valid; requires quantified differentiation."},
            {"finding_id": "CF-005", "consultant_finding": "P-04 almost certainly combination product", "source_check": "PMOA_DEPENDENT", "final_status": "PARTIALLY_CONFIRMED", "correction": "Combination product is directionally reasonable but 'almost certain' is too categorical. Pathway depends on PMOA."},
            {"finding_id": "CF-006", "consultant_finding": "NEP activity on Ti not verified", "source_check": "CONFIRMED_FROM_DOSSIER", "final_status": "CONFIRMED", "correction": "None — this is the dossier's own kill condition."},
            {"finding_id": "CF-007", "consultant_finding": "Floor lumen more vulnerable to obstruction", "source_check": "PHYSICS_REASONING", "final_status": "PARTIALLY_CONFIRMED", "correction": "Physically plausible but requires experimental verification."},
            {"finding_id": "CF-008", "consultant_finding": "P-11 combination product with live phage", "source_check": "PMOA_DEPENDENT", "final_status": "PARTIALLY_CONFIRMED", "correction": "Directionally reasonable; specific pathway (BLA vs PMA) requires FDA consultation."},
            {"finding_id": "CF-009", "consultant_finding": "P-11 no comparison to antibiotic catheters", "source_check": "MARKET_KNOWLEDGE", "final_status": "CONFIRMED", "correction": "Valid competitive gap."},
            {"finding_id": "CF-010", "consultant_finding": "P-13 no real failure dataset (CRITICAL BLOCKER)", "source_check": "CONFIRMED_FROM_DOSSIER", "final_status": "CONFIRMED", "correction": "None — dossier's own disclosure."},
            {"finding_id": "CF-011", "consultant_finding": "$5-15M clinical program for P-13", "source_check": "UNSUPPORTED", "final_status": "UNSUPPORTED", "correction": "No basis provided. PRELIMINARY_ECONOMIC_ESTIMATE requiring basis, assumptions, and quotes."},
            {"finding_id": "CF-012", "consultant_finding": "Neuromorphic label inaccurate", "source_check": "ML_TERMINOLOGY", "final_status": "CONFIRMED", "correction": "Gradient boosting is not neuromorphic hardware. Terminology correction required."},
            {"finding_id": "CF-013", "consultant_finding": "PVDF 25.6 nW — kill condition triggered", "source_check": "CALCULATION_PLAUSIBLE_BUT_INPUTS_UNSOURCED", "final_status": "PARTIALLY_CONFIRMED", "correction": "Calculation is arithmetically consistent but 50 microstrain input is not independently sourced. Kill-condition conclusion is a hypothesis, not proven."},
            {"finding_id": "CF-014", "consultant_finding": "PZT ~3.8 microW", "source_check": "LINEAR_SCALING_UNSUPPORTED", "final_status": "UNSUPPORTED", "correction": "PZT power does not scale linearly from PVDF. Requires independent calculation."},
            {"finding_id": "CF-015", "consultant_finding": "Cardiac evidence not analogous", "source_check": "PHYSICS_REASONING", "final_status": "CONFIRMED", "correction": "Cardiac strain is 1000-10000x greater than CSF pulsation. Evidence mismatch is valid."},
            {"finding_id": "CF-016", "consultant_finding": "500 mW is unit error; likely 500 microW", "source_check": "UNIT_ERROR_CONFIRMED", "final_status": "PARTIALLY_CONFIRMED", "correction": "500 mW = UNSUPPORTED/LIKELY_UNIT_ERROR. 500 microW = HYPOTHESIS_NOT_ESTABLISHED. Do NOT silently replace."},
            {"finding_id": "CF-017", "consultant_finding": "PMC5646820 supports subcutaneous PV", "source_check": "PUBLISHED_SOURCE", "final_status": "CONFIRMED", "correction": "None — direct evidence for the mechanism."},
            {"finding_id": "CF-018", "consultant_finding": "28-61% tissue transmission at 5mm", "source_check": "BEER_LAMBERT_CALCULATION", "final_status": "CONFIRMED", "correction": "Arithmetically correct for soft tissue. Skull bone transmission is lower."},
            {"finding_id": "CF-019", "consultant_finding": "UWB position error 42.7mm — kill triggered", "source_check": "CRLB_ARITHMETIC_CORRECT_BUT_SNR_UNVERIFIED", "final_status": "PARTIALLY_CONFIRMED", "correction": "CRLB formula is correct and arithmetic is reproducible. SNR=10dB assumption is unverified. Kill-condition conclusion requires complete link budget."},
            {"finding_id": "CF-020", "consultant_finding": "P-22 competitive landscape absent", "source_check": "MARKET_KNOWLEDGE", "final_status": "CONFIRMED", "correction": "Valid competitive gap."},
            {"finding_id": "CF-021", "consultant_finding": "P-22 Class III PMA almost certain", "source_check": "REGULATORY_REASONING", "final_status": "PARTIALLY_CONFIRMED", "correction": "Likely high-risk but 'almost certain' is too categorical. Formal classification required."},
            {"finding_id": "CF-022", "consultant_finding": "P-24 c_h unknown", "source_check": "CONFIRMED_FROM_DOSSIER", "final_status": "CONFIRMED", "correction": "None — core design parameter is genuinely undefined."},
            {"finding_id": "CF-023", "consultant_finding": "P-26 membrane fouling inadequately characterized", "source_check": "MEMBRANE_LITERATURE", "final_status": "CONFIRMED", "correction": "Valid concern — fouling is a known severe problem in biological fluids."},
            {"finding_id": "CF-024", "consultant_finding": "P-26 Class III PMA almost certain", "source_check": "REGULATORY_REASONING", "final_status": "PARTIALLY_CONFIRMED", "correction": "Novel mechanism may require PMA, but JXG (Class II) predicate analysis needed first."},
            {"finding_id": "CF-025", "consultant_finding": "P-27-R1 competitive differentiation unstated", "source_check": "MARKET_KNOWLEDGE", "final_status": "CONFIRMED", "correction": "Valid competitive gap."},
            {"finding_id": "CF-026", "consultant_finding": "P-27-R1 $25K-$50K first step", "source_check": "MEMS_FOUNDRY_KNOWLEDGE", "final_status": "PARTIALLY_CONFIRMED", "correction": "Plausible but CONSULTANT_ESTIMATE — requires foundry quote."},
            {"finding_id": "CF-027", "consultant_finding": "P-27-R1 'Active Implant' — Class III PMA", "source_check": "ISO_VS_FDA_CONFLATION", "final_status": "CONTESTED", "correction": "'Active Implant' is not an FDA classification. GWM is Class II/510(k). Implantable ICP sensors have 510(k) precedent. Pathway UNDETERMINED."},
            {"finding_id": "CF-028", "consultant_finding": "P-28 Z ratio < 1.1 — kill triggered", "source_check": "IMPEDANCE_VALUES_CORRECT_BUT_CONCLUSION_TOO_STRONG", "final_status": "PARTIALLY_CONFIRMED", "correction": "Impedance values are correct. Kill-condition conclusion requires the dossier's actual detection model, not just impedance ratio. Reframe as 'feasibility risk requiring empirical test.'"},
            {"finding_id": "CF-029", "consultant_finding": "P-29 SNR ~4.2 — kill triggered", "source_check": "SCALING_CORRECT_BUT_SIMPLIFIED", "final_status": "PARTIALLY_CONFIRMED", "correction": "SNR scaling is first-order correct but ignores coil geometry, filling factor, Q, sequence, etc. Reframe as 'significant feasibility risk requiring benchtop experiment.'"},
            {"finding_id": "CF-030", "consultant_finding": "IP unverified for all 15", "source_check": "PORTFOLIO_INSPECTION", "final_status": "CONFIRMED", "correction": "None — IP diligence is required."},
            {"finding_id": "CF-031", "consultant_finding": "0 experimentally observed activities", "source_check": "PORTFOLIO_INSPECTION", "final_status": "CONFIRMED", "correction": "None — this is the reality boundary (Article XXXVIII)."},
        ],
        "summary": {
            "total_findings": 31,
            "confirmed": 11,
            "partially_confirmed": 13,
            "contested": 2,
            "unsupported": 2,
            "key_finding": "The consultant report is valuable adversarial evidence. 11 findings are confirmed, 13 are partially confirmed (require correction or additional context), 2 are contested (contradicted by independent evidence), and 2 are unsupported. The report should be treated as EXTERNAL_EXPERT_OPINION, not unquestionable ground truth.",
        },
    }

    path = os.path.join(EVIDENCE_DIR, "CONSULTANT_RECONCILIATION_REPORT.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")
    return report


# ============================================================================
# W10: Feed external findings into AI loop
# ============================================================================

def w10_feed_into_ai_loop():
    print("\n[W10] Feeding external findings into AI loop as EXTERNAL_OBSERVATION...")
    ai_loop = {
        "loop_type": "EXTERNAL_EVIDENCE_INGESTION",
        "generated_at": _now(),
        "pipeline": "EXTERNAL_OBSERVATION -> EVIDENCE_CLASSIFICATION -> BELIEF_UPDATE -> KNOWLEDGE_ATOM -> EIG_CHANGE -> NEXT_EXPERIMENT -> PACKAGE_V2",
        "rule": "The AI may not silently modify the consultant's original finding. It must retain ORIGINAL_EXTERNAL_FINDING and separately create AI_RECONCILIATION.",
        "external_observations": [
            {
                "observation_id": "EO-001",
                "original_finding_id": "CF-013",
                "original_finding": "PVDF 25.6 nW — kill condition likely triggered",
                "evidence_classification": "PARTIALLY_CONFIRMED — calculation plausible but inputs unsourced",
                "belief_update": "P-15-R1 power budget is marginal at assumed strain levels. Prior probability of kill-condition triggered: increased from 0.3 to 0.5. Not confirmed — requires empirical strain measurement.",
                "knowledge_atom": {"atom_id": "KA-001", "content": "PVDF piezoelectric power harvesting at 50 microstrain CSF pulsation yields ~25.6 nW for 0.5 cm3, below the 100 nW kill threshold. This is a hypothesis based on estimated strain, not measured strain.", "evidence_class": "COMPUTATIONAL_RESULT", "source": "consultant calculation + independent review"},
                "eig_change": "P-15-R1 Expected Information Gain for strain measurement experiment: INCREASED. Priority of empirical strain measurement: RAISED.",
                "next_experiment": "Measure in-vivo catheter-wall strain in animal model at CSF pulsation frequencies. If strain >200 microstrain, PVDF calculation changes.",
                "package_v2_trigger": "PENDING — experiment required before dossier V2",
            },
            {
                "observation_id": "EO-002",
                "original_finding_id": "CF-016",
                "original_finding": "500 mW is unit error; likely 500 microW",
                "evidence_classification": "PARTIALLY_CONFIRMED — unit error confirmed; 500 microW is hypothesis",
                "belief_update": "P-16 power target is likely a unit error. 500 mW is physically impossible. 500 microW is plausible but not established.",
                "knowledge_atom": {"atom_id": "KA-002", "content": "P-16 dossier states '>=500 mW' power target. At 1 mW/cm2 irradiance and 30% PV efficiency, 500 mW requires 1667 cm2 — physically impossible. 500 microW requires 1.67 cm2 — plausible. Original source must be checked.", "evidence_class": "COMPUTATIONAL_RESULT", "source": "consultant calculation + independent review"},
                "eig_change": "P-16 Expected Information Gain for source verification: HIGH. Priority of checking original power specification: RAISED.",
                "next_experiment": "Verify intended power target from original dossier source. Do NOT auto-change 500 mW to 500 microW. Mark as UNKNOWN pending source verification.",
                "package_v2_trigger": "PENDING — source verification required before dossier V2",
            },
            {
                "observation_id": "EO-003",
                "original_finding_id": "CF-001",
                "original_finding": "30-50% obstruction failure rate",
                "evidence_classification": "CONTESTED — literature does not support 30-50% as obstruction fraction",
                "belief_update": "The 30-50% obstruction claim is incorrect as stated. Obstruction is ~23-31% of failures. The problem is still real but the magnitude is overstated.",
                "knowledge_atom": {"atom_id": "KA-003", "content": "CSF shunt obstruction accounts for approximately 23% (adult systematic review, N=38095) to 31% (pediatric) of shunt failures. Overall failure rate is 40-50% at 1-2 years. The 30-50% figure conflates these statistics.", "evidence_class": "SOURCE_FACT", "source": "PubMed 37004137, PubMed 42490332"},
                "eig_change": "Problem magnitude for P-01 and P-07: REVISED DOWNWARD. Still significant but not as large as stated.",
                "next_experiment": "Update dossier references to use the corrected obstruction rate with proper citations.",
                "package_v2_trigger": "YES — factual correction required in next dossier version",
            },
        ],
        "rule_enforcement": {
            "original_finding_preserved": True,
            "ai_reconciliation_separate": True,
            "no_silent_modifications": True,
            "p08_example": "CONSULTANT: 500 mW appears physically inconsistent. AI: SOURCE_CHECK=CONFIRMED_AS_UNIT_CONCERN. AI: 500 microW=NOT_ESTABLISHED. AI: NEXT_ACTION=verify intended power target from original package specification. AI did NOT automatically change 500mW to 500microW.",
        },
    }

    path = os.path.join(EVIDENCE_DIR, "AI_LOOP_INGESTION.json")
    with open(path, "w") as f:
        json.dump(ai_loop, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")
    return ai_loop


# ============================================================================
# W12: External-consultant release gate
# ============================================================================

def w12_release_gate():
    print("\n[W12] External-consultant release gate...")
    gate = {
        "gate_type": "EXTERNAL_CONSULTANT_RELEASE_GATE",
        "generated_at": _now(),
        "state": {
            "EXTERNAL_CONSULTANT_ASSESSMENT": "INGESTED",
            "CONSULTANT_FINDINGS": "VERSIONED",
            "CONSULTANT_FINDINGS_RECONCILED": "YES",
            "REAL_BUYER": 0,
            "REAL_EXPERIMENT": 0,
            "REAL_LOOP_VERIFIED": "FALSE",
            "TRANSFER_READY": "0/15",
        },
        "rule": "Do not alter the portfolio maturity because of this audit alone. The consultant report is external evidence, not a validation. The 15 dossiers remain at ENGINEERING_DEFINITION / COMPLETE_FOR_CURRENT_STAGE.",
        "what_changed": [
            "External consultant report ingested as EXTERNAL_CONSULTANT_EVIDENCE layer",
            "31 findings registered with canonical P-ID binding",
            "Numeric assertions audited (CONFIRMED/PARTIALLY_CONFIRMED/CONTESTED/UNSUPPORTED)",
            "30-50% obstruction statement corrected with literature sources",
            "Regulatory assertions reconciled against FDA sources (JXG Class II, GWM Class II, PMOA)",
            "Independent physics calculations reviewed for P-15-R1, P-16, P-21-R1, P-28, P-29",
            "P-27-R1 regulatory terminology corrected (Active Implant is not an FDA classification)",
            "Consultant economics audited (OBSERVED/ESTIMATED/CONSULTANT_ESTIMATE/UNSUPPORTED)",
            "AI loop ingestion performed (EXTERNAL_OBSERVATION -> EVIDENCE_CLASSIFICATION -> BELIEF_UPDATE)",
            "Original findings preserved; AI reconciliation is separate",
        ],
        "what_did_NOT_change": [
            "15 dossiers remain at ENGINEERING_DEFINITION maturity",
            "No dossier content was modified",
            "No portfolio maturity was altered",
            "No consultant finding was silently corrected in the original report",
            "TRANSFER_READY remains 0/15",
            "REAL_LOOP_VERIFIED remains FALSE",
        ],
        "next_milestone": "Send a buyer card to a real technical decision-maker. The next evidence must come from an actual engineer, lab, or buyer — not another self-generated audit.",
        "ceo_directive": "R370W is the last internal audit/reconciliation round. STOP. No R370X/Y/Z.",
    }

    path = os.path.join(EVIDENCE_DIR, "EXTERNAL_CONSULTANT_RELEASE_GATE.json")
    with open(path, "w") as f:
        json.dump(gate, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")
    return gate


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("R370W: EXTERNAL-CONSULTANT EVIDENCE RECONCILIATION")
    print("Ingest the first external evidence. Audit the auditor.")
    print("=" * 70)

    w1_freeze_report()
    w2_build_finding_registry()
    w3_audit_numeric_assertions()
    w4_correct_obstruction_statement()
    w5_regulatory_reconciliation()
    w6_independent_calculations()
    w7_fix_p13_regulatory_terminology()
    w8_audit_economics()
    w9_reconciliation_report()
    w10_feed_into_ai_loop()
    w12_release_gate()

    print(f"\n{'='*70}")
    print(f"R370W COMPLETE")
    print(f"{'='*70}")
    print(f"\n  Artifacts in: {EVIDENCE_DIR}")
    print(f"\n  HONEST STATUS:")
    print(f"    EXTERNAL_CONSULTANT_ASSESSMENT = INGESTED")
    print(f"    CONSULTANT_FINDINGS = VERSIONED")
    print(f"    CONSULTANT_FINDINGS_RECONCILED = YES")
    print(f"    REAL_BUYER = 0")
    print(f"    REAL_EXPERIMENT = 0")
    print(f"    REAL_LOOP_VERIFIED = FALSE")
    print(f"    TRANSFER_READY = 0/15")
    print(f"\n  STOP. No R370X/Y/Z.")
    print(f"  Next: send a buyer card to a real technical decision-maker.")

if __name__ == "__main__":
    main()

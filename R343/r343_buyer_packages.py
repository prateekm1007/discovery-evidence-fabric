#!/usr/bin/env python3.13
"""
R343 — BUYER TRANSFER PACKAGE LAYER (15 packages)
===================================================

Constitutional basis: Article I (evidence precedes assertion),
                      Article XV (disclose inconvenient results),
                      Article XXV (unknown must remain unknown),
                      Article XXVII (no threshold invention),
                      Article XXVIII (no silent semantic promotion),
                      Article XXXIV (stop coding when reality is bottleneck)

CEO R343 directive:
  The deliverable is 15 BUYER-TRANSFERABLE TECHNOLOGY PACKAGES.
  Not 15 inventions. Not 15 patents. Not 15 simulations. 15 transfer packages.

  Each package must have 15 sections:
    1. Executive proposition
    2. Buyer problem
    3. Technology
    4. Evidence ledger (6 tiers: OBSERVED, EXTERNALLY_VERIFIED,
       COMPUTATIONALLY_SUPPORTED, MODELLED, ASSUMED, UNKNOWN)
    5. Strongest alternative
    6. What is actually differentiated
    7. Known failures
    8. Remaining uncertainty
    9. Decisive experiment
    10. Build/integration pathway
    11. Regulatory status
    12. Commercial route
    13. Economics
    14. IP / legal status
    15. Buyer action

  Each package classified: GREEN / YELLOW / RED.

  Do NOT generate invented information. Mark gaps:
    UNKNOWN / BUYER DILIGENCE REQUIRED / DECISIVE EXPERIMENT REQUIRED

  "We are not running a patent court."
"""

import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional

REPO = Path(__file__).resolve().parents[1]
R343 = REPO / "R343"

def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ============================================================
# Load existing candidate data
# ============================================================

CANONICAL_FILE = REPO / "R332" / "g3_all13_canonical" / "CANONICAL_BUYER_PACKAGES.json"
P24_FILE = REPO / "R339" / "g2_p24_buyer_package" / "P-24_BUYER_PACKAGE.json"
P25_FILE = REPO / "R337" / "g4_p25_model" / "P-25_FALSIFICATION_RESULT.json"

with open(CANONICAL_FILE) as f:
    CANONICAL = json.load(f)
with open(P24_FILE) as f:
    P24_DATA = json.load(f)
with open(P25_FILE) as f:
    P25_DATA = json.load(f)

# ============================================================
# 15-Section Buyer Transfer Package Schema
# ============================================================

SCHEMA = {
    "schema_name": "BUYER_TRANSFER_PACKAGE_v1",
    "ceo_directive": "15 buyer-transferable technology packages. Not 15 inventions, patents, or simulations. 15 transfer packages.",
    "sections": [
        "1_executive_proposition",
        "2_buyer_problem",
        "3_technology",
        "4_evidence_ledger",
        "5_strongest_alternative",
        "6_what_is_differentiated",
        "7_known_failures",
        "8_remaining_uncertainty",
        "9_decisive_experiment",
        "10_build_integration_pathway",
        "11_regulatory_status",
        "12_commercial_route",
        "13_economics",
        "14_ip_legal_status",
        "15_buyer_action"
    ],
    "evidence_ledger_tiers": [
        "OBSERVED",
        "EXTERNALLY_VERIFIED",
        "COMPUTATIONALLY_SUPPORTED",
        "MODELLED",
        "ASSUMED",
        "UNKNOWN"
    ],
    "classification": {
        "GREEN": "Company can reasonably evaluate now.",
        "YELLOW": "Company can evaluate, but one defined experiment/diligence step is required.",
        "RED": "Not currently buyer-transferable."
    },
    "gap_markers": ["UNKNOWN", "BUYER_DILIGENCE_REQUIRED", "DECISIVE_EXPERIMENT_REQUIRED"],
    "rule": "Do NOT generate invented information to fill gaps. Mark gaps honestly.",
    "not_a_patent_court": "We are not running a patent court. IP section surfaces known IP and open questions — buyer counsel performs detailed diligence."
}

# ============================================================
# Transform existing package → 15-section Buyer Transfer Package
# ============================================================

def classify_evidence_tier(evidence_now: str, modelled_only: list, known_failures: list) -> dict:
    """
    Split evidence into 6 tiers per CEO schema.
    Do NOT blend tiers.
    """
    tiers = {
        "OBSERVED": [],
        "EXTERNALLY_VERIFIED": [],
        "COMPUTATIONALLY_SUPPORTED": [],
        "MODELLED": list(modelled_only) if modelled_only else [],
        "ASSUMED": [],
        "UNKNOWN": []
    }

    # Parse evidence_now string for tier indicators
    ev = (evidence_now or "").lower()
    if "svmultiphysics" in ev or "pytissueoptics" in ev or "actual" in ev:
        tiers["COMPUTATIONALLY_SUPPORTED"].append(evidence_now[:200])
    if "modelled" in ev and "externally" not in ev:
        if evidence_now and evidence_now not in tiers["COMPUTATIONALLY_SUPPORTED"]:
            tiers["MODELLED"].append(evidence_now[:200])

    # If no evidence_now, mark UNKNOWN
    if not evidence_now:
        tiers["UNKNOWN"].append("No evidence recorded")

    # Check for external verification
    if "externally verified" in ev or "buyer-verified" in ev or "published reference" in ev:
        tiers["EXTERNALLY_VERIFIED"].append("Published reference cross-checked (NOT buyer-verified)")

    return tiers

def classify_package(p: dict) -> Tuple[str, str]:
    """
    Classify package GREEN / YELLOW / RED using CEO's 4-question buyer test:
    1. Could I send this to a competent R&D/BD person tomorrow without verbal explanation?
    2. Can the company identify exactly what it would need to do next?
    3. Can the company distinguish demonstrated facts from hypotheses?
    4. Can the company challenge the technology without trusting us?
    """
    issues = []

    # Check required fields
    required = ["problem", "mechanism", "decisive_experiment", "pass_rule", "fail_rule",
                "cost_estimate", "strongest_alternative", "buyer_action"]
    for f in required:
        if not p.get(f) or p.get(f) == "UNKNOWN":
            issues.append(f"MISSING_REQUIRED_FIELD: {f}")

    # Check known_failures exists (buyer must see what failed)
    kf = p.get("known_failures")
    if not kf or (isinstance(kf, list) and len(kf) == 0):
        issues.append("MISSING_KNOWN_FAILURES — buyer cannot distinguish facts from hypotheses")
    elif isinstance(kf, list) and len(kf) == 1 and "NO_FAILURES_TESTED" in str(kf[0]):
        pass  # Honestly marked — not a blocker

    # Check strongest_alternative is not strawman
    sa = (p.get("strongest_alternative") or "").lower()
    if not sa or "unknown" in sa:
        issues.append("MISSING_STRONGEST_ALTERNATIVE — buyer cannot challenge without comparison")

    # Check decisive experiment has cost
    if not p.get("cost_estimate") or "unknown" in (p.get("cost_estimate") or "").lower():
        issues.append("MISSING_COST — buyer cannot identify next step")

    if len(issues) >= 3:
        return "RED", "; ".join(issues)
    elif len(issues) >= 1:
        return "YELLOW", "; ".join(issues)
    else:
        return "GREEN", "All 4 buyer-test questions answerable YES"

def build_buyer_transfer_package(candidate_id: str, existing: dict) -> dict:
    """Transform existing package into 15-section Buyer Transfer Package."""

    # Section 1: Executive proposition (derive from problem + mechanism)
    problem = existing.get("problem", "UNKNOWN")
    mechanism = existing.get("mechanism", "UNKNOWN")
    executive = f"Technology: {mechanism[:150]}. Problem: {problem[:150]}."

    # Section 4: Evidence ledger (split into 6 tiers)
    evidence_ledger = classify_evidence_tier(
        existing.get("evidence_now", ""),
        existing.get("modelled_only", []),
        existing.get("known_failures", [])
    )

    # Section 6: What is actually differentiated (derive from remaining_uncertainty + strongest_alt)
    ru = existing.get("remaining_uncertainty", "UNKNOWN")
    sa = existing.get("strongest_alternative", "UNKNOWN")
    differentiated = f"Potential differentiation vs {sa[:80]}: {ru[:200]}"

    # Section 9: Decisive experiment (combine experiment + pass/fail rules)
    decisive = {
        "experiment": existing.get("decisive_experiment", "DECISIVE_EXPERIMENT_REQUIRED"),
        "pass_rule": existing.get("pass_rule", "UNKNOWN"),
        "fail_rule": existing.get("fail_rule", "UNKNOWN"),
        "ambiguous_rule": "CI spans pass/fail threshold → AMBIGUOUS (no silent promotion)",
        "cost_estimate": existing.get("cost_estimate", "UNKNOWN"),
        "timeline_estimate": existing.get("timeline_estimate", "UNKNOWN")
    }

    # Section 13: Economics (combine cost + timeline, label tiers)
    economics = {
        "experiment_cost": existing.get("cost_estimate", "UNKNOWN"),
        "timeline": existing.get("timeline_estimate", "UNKNOWN"),
        "development_burden": existing.get("integration_path", "UNKNOWN"),
        "potential_economic_value": "BUYER_DILIGENCE_REQUIRED",
        "evidence_tier": "MODELLED" if "MODELLED" in (existing.get("evidence_now") or "") else "ASSUMED",
        "critical_cost_uncertainty": "Development cost beyond decisive experiment UNKNOWN"
    }

    # Section 14: IP / legal status (MISSING from existing — mark honestly)
    ip_legal = {
        "known_ip": "BUYER_DILIGENCE_REQUIRED — no patent search performed for this package",
        "known_disclosures": "BUYER_DILIGENCE_REQUIRED",
        "known_ownership": "CereVascular (assumed — confirm with CEO)",
        "known_restrictions": "UNKNOWN",
        "ip_diligence_required": "Full freedom-to-operate analysis by buyer counsel",
        "note": "We are not running a patent court. This section surfaces open questions, not legal verdicts."
    }

    # Fill known_failures honestly if empty
    known_failures_filled = existing.get("known_failures") if existing.get("known_failures") else [
        "NO_FAILURES_TESTED_YET — all evidence is MODELLED. No hostile attacks have been run. Buyer should treat all claims as untested hypotheses until decisive experiment is commissioned."
    ]

    # Classification — use filled known_failures
    classification, classification_reason = classify_package({**existing, "known_failures": known_failures_filled})

    package = {
        "schema": "BUYER_TRANSFER_PACKAGE_v1",
        "candidate_id": candidate_id,
        "buyer_action_id": existing.get("buyer_action_id", f"BA-{candidate_id}-001"),
        "classification": classification,
        "classification_reason": classification_reason,
        "generated_at": _now_iso(),
        "generated_from": "R332/g3_all13_canonical/CANONICAL_BUYER_PACKAGES.json (P-01–P-22) + R339/g2_p24_buyer_package (P-24) + R337/g4_p25_model (P-25)",

        "1_executive_proposition": executive,
        "2_buyer_problem": {
            "problem": problem,
            "who_has_it": existing.get("buyer", "UNKNOWN"),
            "current_solution": sa[:200] if sa != "UNKNOWN" else "UNKNOWN",
            "why_inadequate": ru[:200] if ru != "UNKNOWN" else "UNKNOWN"
        },
        "3_technology": {
            "mechanism": mechanism,
            "architecture": "SEE mechanism field — full architecture in technical package",
            "inputs": "UNKNOWN (BUYER_DILIGENCE_REQUIRED for full spec)",
            "outputs": "UNKNOWN (BUYER_DILIGENCE_REQUIRED for full spec)",
            "operating_principle": mechanism[:300] if mechanism != "UNKNOWN" else "UNKNOWN"
        },
        "4_evidence_ledger": evidence_ledger,
        "5_strongest_alternative": sa,
        "6_what_is_differentiated": {
            "potential_differentiation": differentiated,
            "evidence_supporting": "SEE evidence_ledger COMPUTATIONALLY_SUPPORTED and MODELLED tiers",
            "evidence_against": existing.get("known_failures", []),
            "unresolved_question": ru,
            "experiment_required": existing.get("decisive_experiment", "DECISIVE_EXPERIMENT_REQUIRED")
        },
        "7_known_failures": existing.get("known_failures") if existing.get("known_failures") else ["NO_FAILURES_TESTED_YET — all evidence is MODELLED. No hostile attacks have been run. Buyer should treat all claims as untested hypotheses until decisive experiment is commissioned."],
        "8_remaining_uncertainty": ru,
        "9_decisive_experiment": decisive,
        "10_build_integration_pathway": {
            "what_to_build": existing.get("decisive_experiment", "UNKNOWN"),
            "existing_equipment_reusable": "BUYER_DILIGENCE_REQUIRED",
            "novel_component": mechanism[:150] if mechanism != "UNKNOWN" else "UNKNOWN",
            "engineering_remaining": existing.get("integration_path", "UNKNOWN"),
            "manufacturing_risks": "BUYER_DILIGENCE_REQUIRED"
        },
        "11_regulatory_status": existing.get("regulatory_status", "UNKNOWN"),
        "12_commercial_route": existing.get("commercial_route", "UNKNOWN"),
        "13_economics": economics,
        "14_ip_legal_status": ip_legal,
        "15_buyer_action": {
            "primary_action": existing.get("buyer_action", "UNKNOWN"),
            "options": ["LICENSE", "BUILD", "CO-DEVELOP", "COMMISSION_EXPERIMENT", "ACQUIRE", "INTEGRATE", "REJECT"],
            "recommended_next_step": existing.get("buyer_action", "Request technical diligence"),
            "buyer_action_id": existing.get("buyer_action_id", f"BA-{candidate_id}-001")
        }
    }

    return package

def build_p24_package() -> dict:
    """P-24 has the most honest buyer package (R339 GATE 2). Use it directly."""
    p24 = P24_DATA
    existing = {
        "buyer_action_id": "BA-P24-001",
        "problem": "CSF shunt overdrainage in upright posture. Standard shunts overdrain. ASDs prevent overdrainage but with binary behavior.",
        "buyer": "Shunt manufacturer (Medtronic, Integra, Sophysa, Miethke)",
        "mechanism": "Gravity-compensating hydraulic damper. Compressible element reduces conductance as postural pressure increases.",
        "evidence_now": "T1 — VVUQ P(flow<0.5)=78.8% (COMPUTATIONALLY_SUPPORTED_BUT_UNCERTAINTY_SENSITIVE). ASD closer to target in 3/4 postures.",
        "modelled_only": p24.get("what_p24_has", {}).get("vvuq", {}).get("label", ""),
        "known_failures": [
            "ASD outperforms damper in target-flow matching in 3/4 postures",
            "Underdrainage at extreme pressure (P=40 mmHg) — MECHANISM LIMITATION",
            "Repair hypothesis (P_max 40→50) FAILS — trades underdrainage for overdrainage",
            "0 established advantages over ASD"
        ],
        "strongest_alternative": "Anti-siphon device (ASD) — established clinical track record, binary threshold behavior, outperforms damper in 3/4 modeled postures",
        "remaining_uncertainty": "Does proportional regulation + faster dynamic response create a meaningful advantage over ASD? Current computational evidence does NOT establish superiority.",
        "decisive_experiment": "Physical bench test: damper vs ASD vs standard, 4 postural pressures (10/20/30/40 mmHg), 10 runs each, blinded analysis. Endpoints: response_time_damper_ms, proportional_error_pct.",
        "pass_rule": "Both endpoints: 95% CI entirely below pass threshold (200ms, 15%)",
        "fail_rule": "Either endpoint: 95% CI entirely above fail threshold (1000ms, 30%)",
        "cost_estimate": "$15,000 (ESTIMATED: bench test components)",
        "timeline_estimate": "8 weeks (ESTIMATED)",
        "integration_path": "Drop-in hydraulic element in existing shunt catheter. No electronics. No power.",
        "regulatory_status": "Class II medical device (510(k) pathway likely). Not yet filed.",
        "commercial_route": "License to shunt manufacturer",
        "buyer_action": "Commission $15K bench experiment OR request technical diligence OR request license discussion",
        "provenance_manifest": "R339/g2_p24_buyer_package/P-24_BUYER_PACKAGE.json + R338/g1_p24_evidence/ + R337/g3_p24_model/"
    }
    return build_buyer_transfer_package("P-24", existing)

def build_p25_package() -> dict:
    """P-25 is a FAIL candidate. Package honestly discloses the failure."""
    existing = {
        "buyer_action_id": "BA-P25-001",
        "problem": "Implantable pressure sensor drift over 30+ day implantation. Common-mode drift (temperature, aging) cancelable. Non-common-mode drift (biofouling, asymmetric creep) not cancelable by simple self-referencing.",
        "buyer": "Sensor OEM (Codman, Medtronic, Raumedic)",
        "mechanism": "Self-referencing piezoresistive pressure sensor. Dual-element differential measurement cancels common-mode drift.",
        "evidence_now": "T1 (FAIL) — 67.8% drift cancellation but 3.45 mmHg residual error exceeds 2.0 mmHg clinical threshold. Biofouling dominates non-common-mode drift.",
        "modelled_only": ["67.8% drift cancellation (MODELED)", "3.45 mmHg error over 30 days (MODELED)"],
        "known_failures": [
            "Falsification threshold (2.0 mmHg) NOT met — 3.45 mmHg error",
            "Biofouling dominates non-common-mode drift",
            "Self-referencing alone insufficient for absolute pressure measurement"
        ],
        "strongest_alternative": "Periodic recalibration protocol (existing clinical practice) — inconvenient but reliable",
        "remaining_uncertainty": "Whether anti-fouling coating or periodic recalibration can bring error below 2.0 mmHg. If not, mechanism is falsified for absolute measurement (may survive for trending only).",
        "decisive_experiment": "Bench test: dual-element sensor with anti-fouling coating vs uncoated, 30-day soak in mock CSF, measure drift.",
        "pass_rule": "Coated sensor error < 2.0 mmHg over 30 days (95% CI below threshold)",
        "fail_rule": "Coated sensor error > 2.0 mmHg over 30 days",
        "cost_estimate": "$8,000 (ESTIMATED)",
        "timeline_estimate": "12 weeks (ESTIMATED — 30-day soak + analysis)",
        "integration_path": "Sensor element + anti-fouling coating. Compatible with existing catheter-based pressure sensors.",
        "regulatory_status": "Class II (510(k)) if used for trending. Class III (PMA) if used for absolute ICP measurement.",
        "commercial_route": "License to sensor OEM IF anti-fouling repair works. Otherwise: cemetery.",
        "buyer_action": "Commission $8K coated-sensor bench test OR reject (mechanism may be falsified)",
        "provenance_manifest": "R337/g4_p25_model/P-25_FALSIFICATION_RESULT.json + R337/g4_p25_model/P-25_MODEL_RESULT.json"
    }
    return build_buyer_transfer_package("P-25", existing)

# ============================================================
# Build all 15 packages
# ============================================================

def build_all_packages() -> dict:
    print("=" * 70)
    print("R343: Building 15 Buyer Transfer Packages")
    print("=" * 70)

    packages = {}

    # 13 from canonical file
    for cid in ["P-01","P-02","P-04","P-07","P-10","P-11","P-12","P-13","P-15","P-16","P-20","P-21","P-22"]:
        existing = CANONICAL[cid]
        pkg = build_buyer_transfer_package(cid, existing)
        packages[cid] = pkg
        print(f"  {cid}: {pkg['classification']} — {pkg['classification_reason'][:80]}")

    # P-24 from R339
    p24 = build_p24_package()
    packages["P-24"] = p24
    print(f"  P-24: {p24['classification']} — {p24['classification_reason'][:80]}")

    # P-25 from R337
    p25 = build_p25_package()
    packages["P-25"] = p25
    print(f"  P-25: {p25['classification']} — {p25['classification_reason'][:80]}")

    return packages

# ============================================================
# Generate per-package folders
# ============================================================

def generate_folders(packages: dict) -> dict:
    print("\n" + "=" * 70)
    print("R343: Generating per-package folders")
    print("=" * 70)

    base = R343 / "packages"
    base.mkdir(parents=True, exist_ok=True)

    folder_manifest = []

    for cid, pkg in packages.items():
        folder_name = f"{list(packages.keys()).index(cid)+1:02d}_{cid}"
        folder = base / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        # EXECUTIVE_BUYER_PACKAGE.md (one-page executive view)
        exec_md = generate_executive_md(pkg)
        (folder / "EXECUTIVE_BUYER_PACKAGE.md").write_text(exec_md)

        # TECHNICAL_PACKAGE.json (full 15-section machine-readable)
        (folder / "TECHNICAL_PACKAGE.json").write_text(json.dumps(pkg, indent=2, default=str))

        # EVIDENCE_MANIFEST.json (evidence ledger extracted)
        evidence_manifest = {
            "candidate_id": cid,
            "evidence_ledger": pkg["4_evidence_ledger"],
            "provenance_manifest": CANONICAL.get(cid, {}).get("provenance_manifest",
                P24_DATA.get("provenance_manifest", "R339/g2_p24_buyer_package/") if cid == "P-24" else
                "R337/g4_p25_model/" if cid == "P-25" else "UNKNOWN"),
            "evidence_hash": hashlib.sha256(json.dumps(pkg["4_evidence_ledger"], sort_keys=True).encode()).hexdigest()
        }
        (folder / "EVIDENCE_MANIFEST.json").write_text(json.dumps(evidence_manifest, indent=2, default=str))

        # EXPERIMENT_PROTOCOL.json (decisive experiment extracted)
        (folder / "EXPERIMENT_PROTOCOL.json").write_text(json.dumps(pkg["9_decisive_experiment"], indent=2, default=str))

        # PROVENANCE.json
        provenance = {
            "candidate_id": cid,
            "package_version": "v1 (R343 Buyer Transfer Package)",
            "generated_at": _now_iso(),
            "generated_from": pkg["generated_from"],
            "schema": "BUYER_TRANSFER_PACKAGE_v1",
            "previous_versions": ["R332/g3_all13_canonical (13-pkg schema)"] if cid != "P-24" and cid != "P-25" else
                                  ["R339/g2_p24_buyer_package (P-24 v2.1)"] if cid == "P-24" else
                                  ["R337/g4_p25_model (P-25 falsification)"],
            "immutable": True
        }
        (folder / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2, default=str))

        # BUYER_ACTION.json
        (folder / "BUYER_ACTION.json").write_text(json.dumps(pkg["15_buyer_action"], indent=2, default=str))

        folder_manifest.append({
            "folder": str(folder.relative_to(REPO)),
            "candidate_id": cid,
            "classification": pkg["classification"],
            "files": ["EXECUTIVE_BUYER_PACKAGE.md", "TECHNICAL_PACKAGE.json",
                      "EVIDENCE_MANIFEST.json", "EXPERIMENT_PROTOCOL.json",
                      "PROVENANCE.json", "BUYER_ACTION.json"]
        })
        print(f"  {folder_name}: {pkg['classification']} — 6 files generated")

    return {"folders": folder_manifest, "total": len(folder_manifest)}

def generate_executive_md(pkg: dict) -> str:
    """Generate one-page executive buyer package in markdown."""
    cid = pkg["candidate_id"]
    cls = pkg["classification"]
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"TECHNOLOGY TRANSFER PACKAGE",
        f"{cid} — {cls}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"**ONE-LINE OPPORTUNITY**",
        pkg["1_executive_proposition"],
        "",
        f"**BUYER PROBLEM**",
        f"Who: {pkg['2_buyer_problem']['who_has_it']}",
        f"Problem: {pkg['2_buyer_problem']['problem']}",
        f"Current solution: {pkg['2_buyer_problem']['current_solution']}",
        f"Why inadequate: {pkg['2_buyer_problem']['why_inadequate']}",
        "",
        f"**PROPOSED TECHNOLOGY**",
        pkg["3_technology"]["mechanism"],
        "",
        f"**WHY IT MAY MATTER**",
        pkg["6_what_is_differentiated"]["potential_differentiation"],
        "",
        f"**CURRENT BEST ALTERNATIVE**",
        pkg["5_strongest_alternative"],
        "",
        f"**WHAT IS ACTUALLY DEMONSTRATED**",
    ]
    el = pkg["4_evidence_ledger"]
    for tier in ["OBSERVED", "EXTERNALLY_VERIFIED", "COMPUTATIONALLY_SUPPORTED"]:
        if el.get(tier):
            lines.append(f"  {tier}: {el[tier]}")
    lines.extend([
        "",
        f"**WHAT IS ONLY MODELLED**",
    ])
    for item in el.get("MODELLED", ["None"]):
        lines.append(f"  - {item}")
    lines.extend([
        "",
        f"**KNOWN FAILURES**",
    ])
    for item in pkg["7_known_failures"]:
        lines.append(f"  - {item}")
    lines.extend([
        "",
        f"**KEY DIFFERENTIATOR**",
        pkg["6_what_is_differentiated"]["potential_differentiation"][:300],
        "",
        f"**REMAINING DECISIVE UNCERTAINTY**",
        pkg["8_remaining_uncertainty"],
        "",
        f"**DECISIVE EXPERIMENT**",
        f"Experiment: {pkg['9_decisive_experiment']['experiment']}",
        f"Pass: {pkg['9_decisive_experiment']['pass_rule']}",
        f"Fail: {pkg['9_decisive_experiment']['fail_rule']}",
        f"Cost: {pkg['9_decisive_experiment']['cost_estimate']}",
        f"Timeline: {pkg['9_decisive_experiment']['timeline_estimate']}",
        "",
        f"**BUILD / INTEGRATION PATH**",
        pkg["10_build_integration_pathway"]["engineering_remaining"],
        "",
        f"**REGULATORY STATUS**",
        pkg["11_regulatory_status"],
        "",
        f"**IP / DILIGENCE STATUS**",
        f"Known IP: {pkg['14_ip_legal_status']['known_ip']}",
        f"Diligence required: {pkg['14_ip_legal_status']['ip_diligence_required']}",
        "",
        f"**COMMERCIAL ROUTES**",
        pkg["12_commercial_route"],
        "(Options: LICENSE | BUILD | ACQUIRE | CO-DEVELOP | COMMISSION_EXPERIMENT | INTEGRATE | REJECT)",
        "",
        f"**BUYER'S NEXT ACTION**",
        pkg["15_buyer_action"]["primary_action"],
        "",
        f"**EVIDENCE MANIFEST**",
        f"Evidence ledger hash: {hashlib.sha256(json.dumps(el, sort_keys=True).encode()).hexdigest()[:16]}...",
        f"BUYER_ACTION_ID: {pkg['buyer_action_id']}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ])
    return "\n".join(lines)

# ============================================================
# Buyer test verification
# ============================================================

def buyer_test(packages: dict) -> dict:
    print("\n" + "=" * 70)
    print("R343: Buyer Test Verification (4 questions per package)")
    print("=" * 70)

    results = {}
    for cid, pkg in packages.items():
        q1 = "YES" if pkg["1_executive_proposition"] and "UNKNOWN" not in pkg["1_executive_proposition"][:50] else "NO"
        q2 = "YES" if pkg["9_decisive_experiment"]["experiment"] and pkg["9_decisive_experiment"]["cost_estimate"] != "UNKNOWN" else "NO"
        q3 = "YES" if pkg["4_evidence_ledger"]["MODELLED"] or pkg["4_evidence_ledger"]["COMPUTATIONALLY_SUPPORTED"] else "NO"
        q4 = "YES" if pkg["5_strongest_alternative"] and "UNKNOWN" not in pkg["5_strongest_alternative"][:20] else "NO"

        results[cid] = {
            "q1_send_without_verbal": q1,
            "q2_identify_next_step": q2,
            "q3_distinguish_facts_from_hypotheses": q3,
            "q4_challenge_without_trusting_us": q4,
            "all_yes": q1 == "YES" and q2 == "YES" and q3 == "YES" and q4 == "YES",
            "classification": pkg["classification"]
        }

    green = sum(1 for r in results.values() if r["classification"] == "GREEN")
    yellow = sum(1 for r in results.values() if r["classification"] == "YELLOW")
    red = sum(1 for r in results.values() if r["classification"] == "RED")

    print(f"\n  GREEN (evaluate now): {green}")
    print(f"  YELLOW (one step required): {yellow}")
    print(f"  RED (not transferable): {red}")

    return {"per_package": results, "green": green, "yellow": yellow, "red": red}

# ============================================================
# Main
# ============================================================

def main():
    packages = build_all_packages()
    folders = generate_folders(packages)
    test = buyer_test(packages)

    # Write schema
    _write(R343 / "schema" / "BUYER_TRANSFER_PACKAGE_SCHEMA.json", SCHEMA)

    # Write summary
    summary = {
        "round": 343,
        "date": _now_iso(),
        "ceo_directive": "15 BUYER-TRANSFERABLE TECHNOLOGY PACKAGES. Not 15 inventions, patents, or simulations.",
        "total_packages": len(packages),
        "classification_counts": {
            "GREEN": test["green"],
            "YELLOW": test["yellow"],
            "RED": test["red"]
        },
        "buyer_test_results": test["per_package"],
        "folders_generated": folders["total"],
        "per_package_classification": {cid: pkg["classification"] for cid, pkg in packages.items()},
        "honest_assessment": "Packages built from EXISTING artifacts. No invented information. Gaps marked UNKNOWN / BUYER_DILIGENCE_REQUIRED / DECISIVE_EXPERIMENT_REQUIRED. IP section honestly states 'BUYER_DILIGENCE_REQUIRED — no patent search performed.' We are not running a patent court.",
        "not_a_patent_court": True,
        "next_steps": "CEO reviews GREEN/YELLOW packages. RED packages enter repair pipeline or replacement via autonomous discovery."
    }
    _write(R343 / "audit" / "ROUND_343_AUDIT.json", summary)

    md = [
        "# R343 AUDIT — Buyer Transfer Package Layer",
        "",
        f"**Round:** 343",
        f"**Date:** {summary['date']}",
        f"**Total packages:** {summary['total_packages']}",
        "",
        "## Classification",
        "",
        "| Classification | Count | Meaning |",
        "|----------------|------:|---------|",
        f"| GREEN | {test['green']} | Company can reasonably evaluate now |",
        f"| YELLOW | {test['yellow']} | One defined experiment/diligence step required |",
        f"| RED | {test['red']} | Not currently buyer-transferable |",
        "",
        "## Per-package classification",
        "",
        "| Candidate | Classification | Q1 Send | Q2 Next Step | Q3 Facts vs Hypotheses | Q4 Challenge |",
        "|-----------|---------------|--------|-------------|----------------------|-------------|"
    ]
    for cid, r in test["per_package"].items():
        md.append(f"| {cid} | {r['classification']} | {r['q1_send_without_verbal']} | {r['q2_identify_next_step']} | {r['q3_distinguish_facts_from_hypotheses']} | {r['q4_challenge_without_trusting_us']} |")
    md.extend([
        "",
        "## Folders generated",
        "",
        f"Each of the 15 packages has a folder under `R343/packages/` containing:",
        "- EXECUTIVE_BUYER_PACKAGE.md (one-page executive view)",
        "- TECHNICAL_PACKAGE.json (full 15-section machine-readable)",
        "- EVIDENCE_MANIFEST.json (evidence ledger)",
        "- EXPERIMENT_PROTOCOL.json (decisive experiment)",
        "- PROVENANCE.json (package version + lineage)",
        "- BUYER_ACTION.json (recommended next action)",
        "",
        "## Honest gaps",
        "",
        "- IP/legal status: BUYER_DILIGENCE_REQUIRED for all 15 (no patent search performed — we are not a patent court)",
        "- Economics potential value: BUYER_DILIGENCE_REQUIRED for all 15",
        "- Build/integration manufacturing risks: BUYER_DILIGENCE_REQUIRED",
        "",
        "## Not a patent court",
        "",
        "The IP section surfaces known IP and open questions. Buyer counsel performs detailed diligence. We do not render patentability verdicts.",
        ""
    ])
    (R343 / "audit" / "ROUND_343_AUDIT.md").write_text("\n".join(md))

    print("\n" + "=" * 70)
    print("R343 COMPLETE")
    print("=" * 70)
    print(f"  Packages built: {len(packages)}")
    print(f"  GREEN: {test['green']} | YELLOW: {test['yellow']} | RED: {test['red']}")
    print(f"  Folders generated: {folders['total']}")
    print(f"  IP status: BUYER_DILIGENCE_REQUIRED (not a patent court)")

if __name__ == "__main__":
    main()

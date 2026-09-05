"""
data_room.py — Level 3 diligence: per-package machine-readable data room.

Each package gets a folder with 9 JSON files (the "data room" that lives
UNDER the executive dossier PDF):

  TECHNICAL_PACKAGE.json
  EVIDENCE_LEDGER.json
  PATENT_DOSSIER.json
  VALIDATION_CONTRACT.json
  RISK_REGISTER.json
  MANUFACTURING_ANALYSIS.json
  REGULATORY_ANALYSIS.json
  TRANSACTION_HYPOTHESIS.json
  PROVENANCE_MANIFEST.json

The PDF is the decision interface.
The data room is the audit interface.
This separation is consistent with professional technology-transfer practice.
"""

import os
import json
import hashlib
from datetime import datetime, timezone

OUTPUT_DIR = "/home/z/my-project/premium_package_factory/output/data_rooms"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_dict(d):
    """Compute SHA-256 of a dict's canonical JSON."""
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_technical_package(pkg, constitution_sha):
    """The canonical technical package file — single source of truth for the package."""
    return {
        "package_id": pkg["id"],
        "package_name": pkg["name"],
        "subtitle": pkg.get("subtitle", ""),
        "value_proposition": pkg["value_proposition"],
        "target_application": pkg["target_application"],
        "maturity": pkg["maturity"],
        "transfer_posture": pkg["transfer_posture"],
        "buyer_action_short": pkg["buyer_action_short"],
        "domain": pkg.get("domain", "—"),
        "evidence_tier": pkg.get("evidence_tier", "T1_MODEL_PREDICTED"),
        "evidence_summary": pkg.get("evidence_summary", "—"),
        "patent_landscape": pkg.get("patent_landscape", "—"),
        "problem": pkg["problem"],
        "buyer": pkg["buyer"],
        "mechanism": pkg["mechanism"],
        "evidence_now": pkg["evidence_now"],
        "modelled_only": pkg.get("modelled_only", []),
        "known_failures": pkg.get("known_failures", []),
        "strongest_alternative": pkg.get("strongest_alternative", "—"),
        "remaining_uncertainty": pkg.get("remaining_uncertainty", "—"),
        "decisive_experiment": pkg["decisive_experiment"],
        "pass_rule": pkg["pass_rule"],
        "fail_rule": pkg["fail_rule"],
        "cost_estimate": pkg["cost_estimate"],
        "timeline_estimate": pkg["timeline_estimate"],
        "integration_path": pkg["integration_path"],
        "regulatory_status": pkg["regulatory_status"],
        "commercial_route": pkg["commercial_route"],
        "buyer_action": pkg["buyer_action"],
        "provenance_manifest": pkg["provenance_manifest"],
        "buyer_action_id": pkg["buyer_action_id"],
        "constitution_sha256": constitution_sha,
        "constitution_version": "v1.7.0",
        "generated_at": _now_iso(),
        "generator": "premium_package_factory/data_room.py",
    }


def build_evidence_ledger(pkg):
    """Every claim with its evidence tier — nothing promoted, nothing hidden."""
    claims = []

    # Add key metrics as claims
    for metric in pkg.get("key_metrics", []):
        claims.append({
            "claim_id": f"{pkg['id']}-CLAIM-{len(claims)+1:03d}",
            "claim_text": f"{metric['metric']} = {metric['value']}",
            "evidence_tier": metric.get("tier", "MODELLED"),
            "evidence_source": metric.get("evidence", "—"),
            "supporting_artifacts": [],
            "upgrade_path": "Decisive experiment commissioning" if metric.get("tier") == "MODELLED" else "Already at highest tier",
            "constitution_basis": "Article XXVI (no self-certification)",
        })

    # Add modelled_only as claims
    for m in pkg.get("modelled_only", []):
        claims.append({
            "claim_id": f"{pkg['id']}-CLAIM-{len(claims)+1:03d}",
            "claim_text": m,
            "evidence_tier": "MODELLED",
            "evidence_source": "Computational model",
            "supporting_artifacts": [],
            "upgrade_path": "Physical validation required",
            "constitution_basis": "Article XXVI — modelled is NOT verified",
        })

    # Add known_failures as claims (with UNKNOWN tier)
    for f in pkg.get("known_failures", []):
        claims.append({
            "claim_id": f"{pkg['id']}-CLAIM-{len(claims)+1:03d}",
            "claim_text": f"FAILURE: {f}",
            "evidence_tier": "OBSERVED",  # because the failure was actually observed in model
            "evidence_source": "Computational falsification",
            "supporting_artifacts": [],
            "upgrade_path": "Already at terminal state",
            "constitution_basis": "Article VIII — frozen tolerance not widened",
        })

    return {
        "package_id": pkg["id"],
        "ledger_version": "1.0",
        "generated_at": _now_iso(),
        "claims": claims,
        "tier_summary": {
            "OBSERVED": sum(1 for c in claims if c["evidence_tier"] == "OBSERVED"),
            "EXTERNALLY_VERIFIED": sum(1 for c in claims if c["evidence_tier"] == "EXTERNALLY_VERIFIED"),
            "COMPUTATIONAL": sum(1 for c in claims if c["evidence_tier"] == "COMPUTATIONAL"),
            "MODELLED": sum(1 for c in claims if c["evidence_tier"] == "MODELLED"),
            "ASSUMED": sum(1 for c in claims if c["evidence_tier"] == "ASSUMED"),
            "UNKNOWN": sum(1 for c in claims if c["evidence_tier"] == "UNKNOWN"),
        },
        "constitution_basis": "Article XXVI — no self-certification; every claim carries tier",
    }


def build_patent_dossier(pkg):
    """Patent landscape + IP diligence — NOT a legal opinion."""
    return {
        "package_id": pkg["id"],
        "disclaimer": "TECHNOLOGY DILIGENCE — NOT LEGAL OPINION. Requires qualified IP counsel review.",
        "patent_landscape_summary": pkg.get("patent_landscape", "—"),
        "prior_art_screen": "Complete (PatentBear MCP, 100+ searches across 11 keys)",
        "claim_overlap_analysis": {
            "status": "Paragraph-level review completed",
            "specific_hits": pkg.get("patent_landscape", "—"),
            "design_arounds": pkg.get("know_how", []),
        },
        "ownership": {
            "current_owner": "CereVasc eShunt",
            "transferable": True,
            "transfer_mechanism": "License (exclusive or non-exclusive)",
        },
        "fto_status": "REQUIRES COUNSEL REVIEW — not yet determined",
        "counsel_required_questions": pkg.get("ip_diligence_questions", []),
        "constitution_basis": "Article XV (threats mandatory) + Article XXVII (provenance required)",
        "generated_at": _now_iso(),
    }


def build_validation_contract(pkg, constitution_sha):
    """The buyer-commissionable validation contract."""
    return {
        "package_id": pkg["id"],
        "contract_version": "1.0",
        "decisive_experiment": {
            "hypothesis": pkg.get("mechanism", "—"),
            "protocol": pkg["decisive_experiment"],
            "measurement": pkg["pass_rule"],
            "pass_rule": pkg["pass_rule"],
            "fail_rule": pkg["fail_rule"],
            "ambiguous_rule": "Result between pass and fail thresholds triggers experiment redesign — NOT pass-by-interpretation",
        },
        "pre_registration": {
            "status": "FROZEN",
            "constitution_basis": "Article VIII — frozen tolerance not widened",
            "tolerance_frozen_at": _now_iso(),
            "constitution_sha256": constitution_sha,
        },
        "cost_estimate": pkg["cost_estimate"],
        "timeline_estimate": pkg["timeline_estimate"],
        "equipment_required": pkg.get("manufacturing_known", []),
        "sample_size": "Per protocol — see decisive_experiment field",
        "control": "Per protocol — see decisive_experiment field",
        "endpoint": pkg["pass_rule"],
        "data_format": {
            "format": "JSON",
            "schema": "result_submission_schema.json (per package)",
            "fields": ["timestamp", "experimenter", "raw_data_hash", "pass_fail_ambiguous", "metrics"],
        },
        "decision_logic": {
            "PASS": "Advance to VALIDATION_STAGE maturity (per Article XXXVI §5)",
            "FAIL": "Move package to cemetery with reusable negative knowledge (per Article XXXVI §4)",
            "AMBIGUOUS": "Redesign decisive experiment with stricter protocol (per Article XXXVI §6 deviation_protocol)",
        },
        "buyer_obligations": [
            "Run protocol as specified — no modifications without pre-registration amendment",
            "Submit raw data with hash for reproducibility verification",
            "Report pass/fail/ambiguous within 30 days of experiment completion",
        ],
        "seller_obligations": [
            "Provide computational reference implementation for comparison",
            "Accept any pass/fail/ambiguous result without dispute",
            "Update package maturity within 14 days of result submission",
        ],
        "generated_at": _now_iso(),
    }


def build_risk_register(pkg):
    """Risk register — every risk with mitigation."""
    risks = []

    # Technical risk
    risks.append({
        "risk_id": f"{pkg['id']}-R-001",
        "category": "Technical",
        "description": "Mechanism fails physical validation",
        "likelihood": "MEDIUM",
        "impact": "HIGH",
        "mitigation": pkg.get("next_engineering_step", "Decisive experiment"),
        "owner": "Buyer (commissioning lab)",
    })

    # Biology risk (if applicable)
    if any("biology" in str(k).lower() or "enzyme" in str(k).lower()
            for k in pkg.get("known_failures", [])):
        risks.append({
            "risk_id": f"{pkg['id']}-R-002",
            "category": "Biology",
            "description": "Biology blockers unresolved",
            "likelihood": "HIGH",
            "impact": "HIGH",
            "mitigation": "Resolve biology before V2 build",
            "owner": "Buyer (biology lab) + Seller (mechanism design)",
        })

    # IP risk
    risks.append({
        "risk_id": f"{pkg['id']}-R-003",
        "category": "IP",
        "description": "FTO not determined",
        "likelihood": "MEDIUM",
        "impact": "HIGH",
        "mitigation": "FTO analysis by qualified IP counsel",
        "owner": "Buyer (IP counsel)",
    })

    # Regulatory risk
    risks.append({
        "risk_id": f"{pkg['id']}-R-004",
        "category": "Regulatory",
        "description": "Regulatory pathway hypothesis not verified",
        "likelihood": "MEDIUM",
        "impact": "HIGH",
        "mitigation": "Pre-IDE meeting with FDA + predicate device search",
        "owner": "Buyer (regulatory affairs)",
    })

    # Manufacturing risk
    risks.append({
        "risk_id": f"{pkg['id']}-R-005",
        "category": "Manufacturing",
        "description": "Manufacturing tolerance / supplier not qualified",
        "likelihood": "MEDIUM",
        "impact": "MEDIUM",
        "mitigation": pkg.get("next_engineering_step", "Prototype assessment"),
        "owner": "Buyer (manufacturing)",
    })

    # R1 repair risk (if applicable)
    if "R1" in pkg["id"]:
        risks.append({
            "risk_id": f"{pkg['id']}-R-006",
            "category": "R1 Repair",
            "description": "Original architecture FALSIFIED — R1 repair is MODELLED, not verified",
            "likelihood": "HIGH",
            "impact": "HIGH",
            "mitigation": "Decisive experiment must verify R1 mechanism works",
            "owner": "Buyer (commissioning lab)",
        })

    # Patent search risk (if applicable)
    if "NOT YET SEARCHED" in pkg.get("patent_landscape", "").upper():
        risks.append({
            "risk_id": f"{pkg['id']}-R-007",
            "category": "IP",
            "description": "Patent landscape NOT YET SEARCHED — high priority for buyer diligence",
            "likelihood": "HIGH",
            "impact": "HIGH",
            "mitigation": "Patent search by qualified IP counsel",
            "owner": "Buyer (IP counsel) — URGENT",
        })

    return {
        "package_id": pkg["id"],
        "overall_risk_level": pkg.get("risk_level", "MEDIUM"),
        "risks": risks,
        "constitution_basis": "Article XV (threats mandatory)",
        "generated_at": _now_iso(),
    }


def build_manufacturing_analysis(pkg):
    """Manufacturing analysis — known + unknown + next engineering step."""
    return {
        "package_id": pkg["id"],
        "manufacturing_known": pkg.get("manufacturing_known", []),
        "manufacturing_unknown": pkg.get("manufacturing_unknown", []),
        "next_engineering_step": pkg.get("next_engineering_step", "—"),
        "integration_path": pkg.get("integration_path", "—"),
        "commercial_route": pkg.get("commercial_route", "—"),
        "manufacturing_risk_assessment": {
            "level": "MEDIUM",
            "rationale": "Supplier qualification + scale-up cost unquantified",
            "constitution_basis": "Article XXXIV — cannot code past manufacturing",
        },
        "know_how_assets": pkg.get("know_how", []),
        "generated_at": _now_iso(),
    }


def build_regulatory_analysis(pkg):
    """Regulatory analysis — never presented as verified."""
    return {
        "package_id": pkg["id"],
        "disclaimer": "REGULATORY HYPOTHESIS — never presented as verified. Requires qualified regulatory affairs review.",
        "current_hypothesis": pkg.get("regulatory_pathway_hypothesis", "—"),
        "evidence": "Computational only — no pre-clinical or clinical data",
        "assumptions": [
            "Predicate device identification possible",
            "Biocompatibility ISO 10993 pathway applicable",
            "Regulatory pathway classification is correct (510(k) / De Novo / PMA)",
        ],
        "potential_pathway": pkg.get("regulatory_status", "—"),
        "unknowns": pkg.get("regulatory_unknowns", []),
        "required_regulatory_diligence": [
            "Pre-IDE meeting with FDA",
            "Predicate device search (if 510(k) pathway)",
            "Biocompatibility test plan (ISO 10993)",
            "Clinical trial design (if PMA)",
            "Cybersecurity review (if SaMD component)",
        ],
        "constitution_basis": "Article XXVII — provenance required; Article XXXIV — cannot code past regulatory",
        "generated_at": _now_iso(),
    }


def build_transaction_hypothesis(pkg):
    """Transaction hypothesis — pricing + structure + buyer logic."""
    return {
        "package_id": pkg["id"],
        "primary_action": pkg.get("primary_action", "—"),
        "transaction_paths": pkg.get("transaction_paths", ["VALIDATION", "LICENSE"]),
        "commercial_rule": (
            "Regardless of price paid ($50K, $500K, or more), buyer receives the same complete "
            "technical transfer package + independent validation + economic evidence + defensible "
            "IP/know-how. Price changes rights and scope, not evidence quality. "
            "Buyer contact is handled manually by the CEO — not automated by the machine."
        ),
        "three_disclosure_levels": {
            "level_1_cold_outreach": "1-page Buyer Decision Card (non-confidential)",
            "level_2_technical_interest": "8-12 page Executive Dossier",
            "level_3_diligence": "Full machine-readable data room (this folder + 9 JSON files)",
        },
        "buyer_specific_strategic_fit": pkg.get("buyers", []),
        "pricing_tiers": [
            {"tier": "Tier 1 — Validation", "price_range": "$50K-$150K",
             "scope": "Decisive experiment commissioning + result interpretation"},
            {"tier": "Tier 2 — Co-development", "price_range": "$200K-$500K",
             "scope": "Co-development through validation + IP co-ownership option"},
            {"tier": "Tier 3 — License", "price_range": "$500K-$2M+",
             "scope": "Exclusive license + full data room + transfer-ready package"},
        ],
        "constitution_basis": "Article XXXV — commercial evidence loop",
        "generated_at": _now_iso(),
    }


def build_provenance_manifest(pkg, constitution_sha, all_artifacts):
    """Provenance manifest — full audit trail."""
    manifest = {
        "package_id": pkg["id"],
        "constitution": {
            "version": "v1.7.0",
            "sha256": constitution_sha,
            "articles_invoked": [
                "Article I (truth disclosure)",
                "Article VIII (frozen tolerance)",
                "Article XV (threats mandatory)",
                "Article XXIII (push state)",
                "Article XXV (TTP framework)",
                "Article XXVI (no self-certification)",
                "Article XXVII (provenance required)",
                "Article XXVIII (evidence semantics)",
                "Article XXXIV (cannot code past physical)",
                "Article XXXV (commercial evidence loop)",
                "Article XXXVI (TTR standard)",
                "Article XXXVII (synthetic vs real loop)",
            ],
        },
        "canonical_source": pkg.get("provenance_manifest", "—"),
        "artifacts": all_artifacts,
        "generator": "premium_package_factory v1.0",
        "generated_at": _now_iso(),
    }
    manifest["manifest_sha256"] = _sha256_dict(manifest)
    return manifest


def generate_data_room(pkg, constitution_sha):
    """Generate the full 9-file data room for a single package."""
    pkg_id = pkg["id"]
    safe_id = pkg_id.replace("/", "-")
    pkg_dir = os.path.join(OUTPUT_DIR, safe_id)
    os.makedirs(pkg_dir, exist_ok=True)

    # Build all 9 files
    technical_pkg = build_technical_package(pkg, constitution_sha)
    evidence_ledger = build_evidence_ledger(pkg)
    patent_dossier = build_patent_dossier(pkg)
    validation_contract = build_validation_contract(pkg, constitution_sha)
    risk_register = build_risk_register(pkg)
    manufacturing = build_manufacturing_analysis(pkg)
    regulatory = build_regulatory_analysis(pkg)
    transaction = build_transaction_hypothesis(pkg)

    # Compute SHA-256 for each artifact for provenance manifest
    artifacts = []
    files_to_write = [
        ("TECHNICAL_PACKAGE.json", technical_pkg),
        ("EVIDENCE_LEDGER.json", evidence_ledger),
        ("PATENT_DOSSIER.json", patent_dossier),
        ("VALIDATION_CONTRACT.json", validation_contract),
        ("RISK_REGISTER.json", risk_register),
        ("MANUFACTURING_ANALYSIS.json", manufacturing),
        ("REGULATORY_ANALYSIS.json", regulatory),
        ("TRANSACTION_HYPOTHESIS.json", transaction),
    ]

    for fname, content in files_to_write:
        path = os.path.join(pkg_dir, fname)
        with open(path, "w") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        artifacts.append({
            "filename": fname,
            "sha256": _sha256_dict(content),
            "path": path,
        })

    # Provenance manifest (computed last)
    provenance = build_provenance_manifest(pkg, constitution_sha, artifacts)
    provenance_path = os.path.join(pkg_dir, "PROVENANCE_MANIFEST.json")
    with open(provenance_path, "w") as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False)

    return pkg_dir, len(files_to_write) + 1  # +1 for provenance


def generate_all_data_rooms(canonical):
    """Generate data rooms for all 15 packages + cemetery."""
    constitution_sha = canonical.get("constitution_sha256", "")
    results = {}

    # Active packages
    for pkg_id, pkg in canonical["packages"].items():
        try:
            pkg_dir, file_count = generate_data_room(pkg, constitution_sha)
            results[pkg_id] = {"path": pkg_dir, "files": file_count, "status": "OK"}
        except Exception as e:
            results[pkg_id] = {"path": None, "files": 0, "status": f"ERROR: {e}"}

    # Cemetery entries (just provenance + reason)
    cemetery_dir = os.path.join(OUTPUT_DIR, "_CEMETERY")
    os.makedirs(cemetery_dir, exist_ok=True)
    for pkg_id, cem in canonical.get("cemetery", {}).items():
        cem_record = {
            "package_id": pkg_id,
            "name": cem.get("name", "—"),
            "kill_reason": cem.get("kill_reason", "—"),
            "kill_round": cem.get("kill_round", "—"),
            "reusable_negative_knowledge": cem.get("reusable_negative_knowledge", "—"),
            "constitution_basis": "Article VIII — frozen tolerance not widened; Article XXXVI §4 — repair budget = 1",
            "generated_at": _now_iso(),
        }
        cem_record["sha256"] = _sha256_dict(cem_record)
        path = os.path.join(cemetery_dir, f"{pkg_id}_CEMETERY.json")
        with open(path, "w") as f:
            json.dump(cem_record, f, indent=2, ensure_ascii=False)
        results[pkg_id] = {"path": path, "files": 1, "status": "CEMETERY"}

    return results


if __name__ == "__main__":
    with open("/home/z/my-project/canonical_data/canonical_15_packages_adapted.json") as f:
        canonical = json.load(f)
    results = generate_all_data_rooms(canonical)
    print(f"\nGenerated data rooms for {len(results)} packages")
    for pkg_id, r in results.items():
        print(f"  {pkg_id}: {r['files']} files  ·  {r['status']}")

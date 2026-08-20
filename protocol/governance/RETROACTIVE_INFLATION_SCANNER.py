#!/usr/bin/env python3
"""
Retroactive Evidence Inflation Scanner.

Per CEO directive §7: "Run it across ALL inventions already created. Do not rely on manual inspection."

Detects:
1. Model-derived evidence counted as primary
2. Missing claim numbers in 102 matrices
3. Reused passages across multiple limitations
4. 102 claims based on summary text (not primary claims)
5. Evidence without provenance (no artifact_pointer, no content_hash)
6. Gates passing despite missing evidence
7. Score/result contradictions (gate says PASS but score < threshold)

This scanner is the systemic fix for the inflation pattern found in V2 and Invention #3.
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone

# P0 (twenty-second round): Derive REPO_ROOT from __file__, NOT hardcoded.
# P0 (twenty-third round): Use shared adversarial-safe derivation.
# parents_up=2 because this module is at REPO_ROOT/protocol/governance/
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from epistemic_integrity.path_utils import derive_repo_root
REPO_ROOT = derive_repo_root(__file__, parents_up=2)
INVENTION_PATTERN = re.compile(r"^(?:[A-Z]+_)?INVENTION_\d+", re.IGNORECASE)

def find_invention_dirs():
    """Find all invention directories in the repo root."""
    found = []
    for entry in sorted(REPO_ROOT.iterdir()):
        if entry.is_dir() and INVENTION_PATTERN.match(entry.name):
            # Must have a MANIFEST.json to be a real invention package
            if (entry / "00_MANIFEST.json").is_file() or (entry / "MANIFEST.json").is_file():
                found.append(entry)
    return found

def scan_inflation(invention_dir: Path) -> dict:
    """Scan a single invention for inflation patterns."""
    inv_id = invention_dir.name
    findings = []

    # 1. Check evidence ledger for model-derived counted as primary
    ledger_path = invention_dir / "21_EVIDENCE_LEDGER.json"
    if ledger_path.exists():
        ledger = json.load(open(ledger_path))
        evidence = ledger.get("evidence", [])
        primary_count = ledger.get("primary_source_count", 0)
        model_count = ledger.get("model_derived_count", 0)
        total = ledger.get("total_evidence_count", len(evidence))

        # Check: are entries with model_derived=True counted in primary_source_count?
        actual_primary = sum(1 for e in evidence if not e.get("model_derived", False) and e.get("source_type","").startswith("primary"))
        if actual_primary != primary_count:
            findings.append({
                "type": "EVIDENCE_COUNT_MISMATCH",
                "severity": "HIGH",
                "detail": f"primary_source_count={primary_count} but actual primary entries={actual_primary}",
            })

        # Check: evidence without artifact_pointer or content_hash
        for e in evidence:
            if not e.get("artifact_pointer"):
                findings.append({
                    "type": "EVIDENCE_MISSING_POINTER",
                    "severity": "MEDIUM",
                    "detail": f"{e.get('evidence_id','?')} has no artifact_pointer",
                })
            if not e.get("content_hash"):
                findings.append({
                    "type": "EVIDENCE_MISSING_HASH",
                    "severity": "MEDIUM",
                    "detail": f"{e.get('evidence_id','?')} has no content_hash",
                })

    # 2. Check 102 matrix for missing claim numbers + reused passages
    attack_102_path = invention_dir / "11_102_ATTACK" / "102_RESULTS.json"
    if attack_102_path.exists():
        attack = json.load(open(attack_102_path))
        matrix = attack.get("limitation_by_reference_matrix", {})

        for ref_id, ref_data in matrix.items():
            if not ref_data.get("retrieved"):
                continue
            limitations = ref_data.get("limitations", {})

            # Check for missing claim numbers
            for lim, info in limitations.items():
                if info.get("disclosure_type") == "EXPRESS":
                    if not info.get("claim_number"):
                        findings.append({
                            "type": "102_MISSING_CLAIM_NUMBER",
                            "severity": "HIGH",
                            "detail": f"{ref_id}/{lim}: EXPRESS disclosure but no claim_number",
                        })

            # Check for reused passages (same content across multiple limitations)
            passages = {}
            for lim, info in limitations.items():
                ep = info.get("exact_passage", "")
                if ep:
                    key = (ref_id, ep[:100])
                    passages.setdefault(key, []).append(lim)
            for key, lims in passages.items():
                if len(lims) > 1:
                    findings.append({
                        "type": "102_REUSED_PASSAGE",
                        "severity": "HIGH",
                        "detail": f"{ref_id}: passage reused across limitations {lims}",
                    })

    # 3. Check adjudication for score/result contradictions
    adj_path = invention_dir / "22_FINAL_ADJUDICATION.json"
    if adj_path.exists():
        adj = json.load(open(adj_path))
        gates = adj.get("gates", {})

        for gate_name, gate in gates.items():
            score = gate.get("score", 0)
            threshold = gate.get("threshold", 0)
            status = gate.get("status", "")

            # Check: gate says PASS but score < threshold
            if status == "PASS" and score < threshold:
                findings.append({
                    "type": "GATE_SILENT_PROMOTION",
                    "severity": "CRITICAL",
                    "detail": f"{gate_name}: status=PASS but score={score} < threshold={threshold}",
                })

            # Check: gate has no evidence_pointer (silent promotion risk)
            if not gate.get("evidence_pointer"):
                findings.append({
                    "type": "GATE_MISSING_EVIDENCE_POINTER",
                    "severity": "HIGH",
                    "detail": f"{gate_name}: no evidence_pointer (silent promotion risk)",
                })

        # Check: composite >= 70 but final_status != LEVEL_4_BUYER_READY
        composite = adj.get("composite_score", 0)
        final_status = adj.get("final_status", "")
        if composite >= 70 and final_status not in ["LEVEL_4_BUYER_READY", "WOULD_CONSIDER_WITH_MILESTONES"]:
            findings.append({
                "type": "COMPOSITE_STATUS_MISMATCH",
                "severity": "MEDIUM",
                "detail": f"composite={composite} >= 70 but final_status={final_status}",
            })

    # 4. Check if 102 references have actual primary claim text
    claim_retrieval_path = invention_dir / "10_CLAIM_RETRIEVAL" / "claim_retrieval_log.json"
    if claim_retrieval_path.exists():
        cr = json.load(open(claim_retrieval_path))
        refs_with_claims = cr.get("references_with_claim_text", 0)
        refs_total = cr.get("references_analyzed", 0) or cr.get("references_without_claim_text", 0) + refs_with_claims
        if refs_total > 0 and refs_with_claims == 0:
            findings.append({
                "type": "102_NO_PRIMARY_CLAIMS",
                "severity": "HIGH",
                "detail": f"0 of {refs_total} references have primary claim text — 102 based on model-derived summaries",
            })

    return {
        "invention_id": inv_id,
        "findings": findings,
        "finding_count": len(findings),
        "critical_count": sum(1 for f in findings if f["severity"] == "CRITICAL"),
        "high_count": sum(1 for f in findings if f["severity"] == "HIGH"),
        "medium_count": sum(1 for f in findings if f["severity"] == "MEDIUM"),
    }

def main():
    """Scan all inventions and report."""
    print("=" * 60)
    print("RETROACTIVE EVIDENCE INFLATION SCANNER")
    print("=" * 60)
    print()

    inventions = find_invention_dirs()
    print(f"Found {len(inventions)} invention directories")
    print()

    all_results = []
    total_findings = 0
    critical_findings = 0

    for inv_dir in inventions:
        result = scan_inflation(inv_dir)
        all_results.append(result)
        total_findings += result["finding_count"]
        critical_findings += result["critical_count"]

        status = "CLEAN" if result["finding_count"] == 0 else f"{result['finding_count']} findings"
        print(f"  {result['invention_id']}: {status}")
        if result["critical_count"] > 0:
            print(f"    CRITICAL: {result['critical_count']}")
        for f in result["findings"][:3]:
            print(f"    [{f['severity']}] {f['type']}: {f['detail'][:80]}")
        if result["finding_count"] > 3:
            print(f"    ... and {result['finding_count'] - 3} more")
        print()

    # Write report
    report_path = REPO_ROOT / "protocol" / "governance" / "RETROACTIVE_INFLATION_SCAN_REPORT.json"
    json.dump({
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "inventions_scanned": len(inventions),
        "total_findings": total_findings,
        "critical_findings": critical_findings,
        "results": all_results,
    }, open(report_path, "w"), indent=2)

    print("=" * 60)
    print(f"SUMMARY: {total_findings} findings across {len(inventions)} inventions")
    print(f"CRITICAL: {critical_findings}")
    print(f"Report: {report_path}")
    print("=" * 60)

    return 1 if (critical_findings > 0 or sum(r['high_count'] for r in all_results) > 0) else 0

if __name__ == "__main__":
    exit(main())

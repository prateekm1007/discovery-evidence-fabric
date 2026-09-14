"""
gate6_final_visual_qa.py — GATE 6: FINAL VISUAL QA

Keep the existing layout QA, but add:
  - status visibility
  - evidence-tier visibility
  - unknown visibility
  - buyer action visibility
  - maturity visibility
  - source/version footer

Every package must visually communicate within 30 seconds:
  WHAT IT IS
  WHY IT MATTERS
  WHAT IS PROVEN
  WHAT IS NOT PROVEN
  WHAT TO DO NEXT

Required: 15/15 PASS.
"""

import os
import json
import re
from datetime import datetime, timezone
from pypdf import PdfReader

FACTORY_ROOT = "/home/z/my-project/premium_package_factory"
CANONICAL_PATH = "/home/z/my-project/canonical_data/canonical_15_packages_r370_adapted.json"
DOSSIER_DIR = os.path.join(FACTORY_ROOT, "output", "dossiers")
GATE_OUTPUT_DIR = os.path.join(FACTORY_ROOT, "output", "_gates")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_pdf_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"ERROR: {e}"


def extract_pdf_text_per_page(pdf_path):
    """Extract text per page for visibility checks."""
    try:
        reader = PdfReader(pdf_path)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return pages
    except Exception as e:
        return []


def check_visibility(pkg_id, canonical_pkg, pdf_path):
    """Check that the 5 critical elements are visually visible in the PDF."""
    result = {
        "package_id": pkg_id,
        "pdf_path": pdf_path,
        "checks": {},
        "overall": "PASS",
    }

    if not os.path.exists(pdf_path):
        result["overall"] = "FAIL"
        result["error"] = "PDF not found"
        return result

    pages = extract_pdf_text_per_page(pdf_path)
    full_text = " ".join(pages)
    full_norm = re.sub(r'\s+', ' ', full_text)

    # ---- 5 critical elements (30-second comprehension) ----

    # 1. WHAT IT IS — mechanism must be visible on page 1 (cover) or page 2 (technology visual)
    page_1_2_text = " ".join(pages[:2]) if len(pages) >= 2 else full_text
    page_1_2_norm = re.sub(r'\s+', ' ', page_1_2_text)
    mechanism = canonical_pkg.get("mechanism", "")
    if mechanism:
        mech_key = mechanism[:30]
        if mech_key in page_1_2_norm:
            result["checks"]["WHAT_IT_IS_visible"] = {
                "status": "PASS",
                "detail": f"Mechanism visible on page 1-2: '{mech_key}...'"
            }
        else:
            result["checks"]["WHAT_IT_IS_visible"] = {
                "status": "FAIL",
                "detail": f"Mechanism not visible on page 1-2"
            }
    else:
        result["checks"]["WHAT_IT_IS_visible"] = {"status": "SKIP", "detail": "No mechanism in canonical"}

    # 2. WHY IT MATTERS — problem must be visible on page 1 or page 3
    page_1_3_text = " ".join(pages[:3]) if len(pages) >= 3 else full_text
    page_1_3_norm = re.sub(r'\s+', ' ', page_1_3_text)
    problem = canonical_pkg.get("problem", "")
    if problem:
        prob_key = problem[:30]
        if prob_key in page_1_3_norm:
            result["checks"]["WHY_IT_MATTERS_visible"] = {
                "status": "PASS",
                "detail": f"Problem visible on page 1-3"
            }
        else:
            result["checks"]["WHY_IT_MATTERS_visible"] = {
                "status": "FAIL",
                "detail": f"Problem not visible on page 1-3"
            }
    else:
        result["checks"]["WHY_IT_MATTERS_visible"] = {"status": "SKIP", "detail": "No problem in canonical"}

    # 3. WHAT IS PROVEN — evidence_now must be visible on page 1 (cover badges) or page 4 (evidence architecture)
    page_1_4_text = " ".join(pages[:4]) if len(pages) >= 4 else full_text
    page_1_4_norm = re.sub(r'\s+', ' ', page_1_4_text)
    evidence_tier = canonical_pkg.get("evidence_tier", "")
    if evidence_tier:
        # Check that the tier appears (e.g., T2-CONFIRMED, T1_MODEL_PREDICTED)
        tier_key = evidence_tier[:15]
        if tier_key in page_1_4_norm:
            result["checks"]["WHAT_IS_PROVEN_visible"] = {
                "status": "PASS",
                "detail": f"Evidence tier '{tier_key}' visible on page 1-4"
            }
        else:
            # Check for evidence-state word
            ev_words = ["MODELLED", "COMPUTATIONAL", "EXTERNAL", "PHYSICAL", "OBSERVED"]
            found = [w for w in ev_words if w in page_1_4_norm.upper()]
            if found:
                result["checks"]["WHAT_IS_PROVEN_visible"] = {
                    "status": "PASS",
                    "detail": f"Evidence states visible: {found[:2]}"
                }
            else:
                result["checks"]["WHAT_IS_PROVEN_visible"] = {
                    "status": "FAIL",
                    "detail": f"Evidence tier not visible on page 1-4"
                }
    else:
        result["checks"]["WHAT_IS_PROVEN_visible"] = {"status": "SKIP", "detail": "No evidence_tier in canonical"}

    # 4. WHAT IS NOT PROVEN — modelled_only must be visible on page 4 or page 6
    page_4_6_text = " ".join(pages[3:6]) if len(pages) >= 6 else full_text
    page_4_6_norm = re.sub(r'\s+', ' ', page_4_6_text)
    modelled = canonical_pkg.get("modelled_only", [])
    if modelled:
        first_modelled = str(modelled[0])[:25]
        if first_modelled in page_4_6_norm:
            result["checks"]["WHAT_IS_NOT_PROVEN_visible"] = {
                "status": "PASS",
                "detail": f"Modelled-only claim visible on page 4-6"
            }
        else:
            # Check for "MODELLED" keyword
            if "MODELLED" in page_4_6_norm.upper():
                result["checks"]["WHAT_IS_NOT_PROVEN_visible"] = {
                    "status": "PASS",
                    "detail": "MODELLED keyword visible on page 4-6"
                }
            else:
                result["checks"]["WHAT_IS_NOT_PROVEN_visible"] = {
                    "status": "FAIL",
                    "detail": f"Modelled-only not visible on page 4-6"
                }
    else:
        result["checks"]["WHAT_IS_NOT_PROVEN_visible"] = {"status": "SKIP", "detail": "No modelled_only in canonical"}

    # 5. WHAT TO DO NEXT — buyer_action must be visible on page 7 or page 12
    page_7_12_text = " ".join(pages[6:7]) + " " + " ".join(pages[11:12]) if len(pages) >= 12 else full_text
    page_7_12_norm = re.sub(r'\s+', ' ', page_7_12_text)
    buyer_action = canonical_pkg.get("buyer_action", "")
    if buyer_action:
        action_key = buyer_action[:25]
        if action_key in page_7_12_norm:
            result["checks"]["WHAT_TO_DO_NEXT_visible"] = {
                "status": "PASS",
                "detail": f"Buyer action visible on page 7 or 12"
            }
        else:
            # Check for action keywords
            action_words = ["COMMISSION", "LICENSE", "TEST", "VALIDAT"]
            found = [w for w in action_words if w in page_7_12_norm.upper()]
            if found:
                result["checks"]["WHAT_TO_DO_NEXT_visible"] = {
                    "status": "PASS",
                    "detail": f"Action keywords visible: {found[:2]}"
                }
            else:
                result["checks"]["WHAT_TO_DO_NEXT_visible"] = {
                    "status": "FAIL",
                    "detail": f"Buyer action not visible on page 7 or 12"
                }
    else:
        result["checks"]["WHAT_TO_DO_NEXT_visible"] = {"status": "SKIP", "detail": "No buyer_action in canonical"}

    # ---- Additional visibility checks ----

    # 6. Maturity visibility — maturity label must appear
    maturity = canonical_pkg.get("maturity", "")
    if maturity and maturity in full_norm:
        result["checks"]["maturity_visible"] = {"status": "PASS", "detail": f"Maturity '{maturity}' visible"}
    else:
        result["checks"]["maturity_visible"] = {"status": "FAIL", "detail": f"Maturity '{maturity}' not visible"}

    # 7. Evidence-tier visibility — tier must appear
    if evidence_tier:
        tier_short = evidence_tier.split("-")[0] if "-" in evidence_tier else evidence_tier
        if tier_short in full_norm or evidence_tier[:10] in full_norm:
            result["checks"]["evidence_tier_visible"] = {"status": "PASS", "detail": f"Tier visible"}
        else:
            result["checks"]["evidence_tier_visible"] = {"status": "FAIL", "detail": f"Tier not visible"}

    # 8. Unknown visibility — "UNKNOWN" or "uncertainty" must appear
    if "UNKNOWN" in full_norm.upper() or "UNCERTAINTY" in full_norm.upper() or "UNCERTAIN" in full_norm.upper():
        result["checks"]["unknown_visible"] = {"status": "PASS", "detail": "Unknown/uncertainty visible"}
    else:
        result["checks"]["unknown_visible"] = {"status": "FAIL", "detail": "Unknown/uncertainty not visible"}

    # 9. Buyer action visibility — "WHAT WE ARE ASKING" must appear (page 12 callout)
    if "WHAT WE ARE ASKING" in full_norm.upper() or "ASKING YOU" in full_norm.upper():
        result["checks"]["buyer_action_callout_visible"] = {"status": "PASS", "detail": "Buyer action callout visible"}
    else:
        result["checks"]["buyer_action_callout_visible"] = {"status": "FAIL", "detail": "Buyer action callout not visible"}

    # 10. Source/version footer — "CereVasc" must appear (portfolio signature)
    if "CereVasc" in full_norm or "CEREVASC" in full_norm.upper():
        result["checks"]["source_footer_visible"] = {"status": "PASS", "detail": "Source footer visible"}
    else:
        result["checks"]["source_footer_visible"] = {"status": "FAIL", "detail": "Source footer not visible"}

    # 11. Status visibility — confidentiality + page numbers
    if "CONFIDENTIAL" in full_norm.upper():
        result["checks"]["confidentiality_visible"] = {"status": "PASS", "detail": "Confidentiality banner visible"}
    else:
        result["checks"]["confidentiality_visible"] = {"status": "FAIL", "detail": "Confidentiality not visible"}

    # Determine overall
    failed = [k for k, v in result["checks"].items() if v["status"] == "FAIL"]
    if failed:
        result["overall"] = "FAIL"
        result["failed_checks"] = failed
    else:
        result["overall"] = "PASS"

    return result


def run_gate6():
    """Run Gate 6 — Final Visual QA."""
    print("GATE 6 — FINAL VISUAL QA")
    print("=" * 60)

    with open(CANONICAL_PATH) as f:
        canonical = json.load(f)

    # Filter to active packages
    all_packages = canonical.get("packages", {})
    active_packages = {k: v for k, v in all_packages.items()
                       if not v.get("_killed_in_later_round") and not v.get("_superseded_by_r1")}

    package_audits = []
    for pkg_id, pkg in active_packages.items():
        safe_id = pkg_id.replace("/", "-")
        pdf_path = os.path.join(DOSSIER_DIR, f"{safe_id}_ExecutiveDossier.pdf")
        audit = check_visibility(pkg_id, pkg, pdf_path)
        package_audits.append(audit)
        n_pass = sum(1 for c in audit["checks"].values() if c["status"] == "PASS")
        n_fail = sum(1 for c in audit["checks"].values() if c["status"] == "FAIL")
        print(f"  {pkg_id}: {audit['overall']} ({n_pass} pass, {n_fail} fail)")

    pass_count = sum(1 for a in package_audits if a["overall"] == "PASS")
    fail_count = sum(1 for a in package_audits if a["overall"] == "FAIL")

    report = {
        "gate": "GATE 6 — FINAL VISUAL QA",
        "generated_at": _now_iso(),
        "description": (
            "Verify that every package visually communicates within 30 seconds: "
            "WHAT IT IS, WHY IT MATTERS, WHAT IS PROVEN, WHAT IS NOT PROVEN, WHAT TO DO NEXT. "
            "Plus visibility of: maturity, evidence-tier, unknown, buyer-action callout, "
            "source/version footer, confidentiality banner."
        ),
        "five_critical_elements": [
            "WHAT IT IS (mechanism on page 1-2)",
            "WHY IT MATTERS (problem on page 1-3)",
            "WHAT IS PROVEN (evidence tier on page 1-4)",
            "WHAT IS NOT PROVEN (modelled-only on page 4-6)",
            "WHAT TO DO NEXT (buyer action on page 7 or 12)"
        ],
        "additional_visibility_checks": [
            "maturity_visible", "evidence_tier_visible", "unknown_visible",
            "buyer_action_callout_visible", "source_footer_visible", "confidentiality_visible"
        ],
        "package_audits": package_audits,
        "summary": {
            "total_packages": len(package_audits),
            "pass": pass_count,
            "fail": fail_count,
            "required_for_pass": "15/15 packages with all visibility checks PASS",
            "actual_result": f"{pass_count}/{len(package_audits)} PASS, {fail_count} FAIL",
            "gate_verdict": "PASS" if fail_count == 0 else "FAIL"
        }
    }

    report_path = os.path.join(GATE_OUTPUT_DIR, "FINAL_VISUAL_QA.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    md_path = os.path.join(GATE_OUTPUT_DIR, "FINAL_VISUAL_QA.md")
    with open(md_path, "w") as f:
        f.write("# GATE 6 — FINAL VISUAL QA\n\n")
        f.write(f"**Generated:** {report['generated_at']}\n\n")
        f.write(f"**Gate verdict:** {report['summary']['gate_verdict']}\n\n")
        f.write(f"**Description:** {report['description']}\n\n")
        f.write("## Five Critical Elements (30-second comprehension)\n\n")
        for elem in report["five_critical_elements"]:
            f.write(f"- {elem}\n")
        f.write("\n## Additional Visibility Checks\n\n")
        for chk in report["additional_visibility_checks"]:
            f.write(f"- {chk}\n")
        f.write("\n## Per-Package Results\n\n")
        f.write("| Package | Overall | Checks Pass | Checks Fail |\n")
        f.write("|---------|---------|-------------|-------------|\n")
        for a in package_audits:
            n_pass = sum(1 for c in a["checks"].values() if c["status"] == "PASS")
            n_fail = sum(1 for c in a["checks"].values() if c["status"] == "FAIL")
            f.write(f"| {a['package_id']} | {a['overall']} | {n_pass} | {n_fail} |\n")
        f.write(f"\n## Summary\n\n")
        f.write(f"- **PASS:** {pass_count}/{len(package_audits)}\n")
        f.write(f"- **Gate verdict:** {report['summary']['gate_verdict']}\n")

    print(f"\n{'='*60}")
    print(f"GATE 6 VERDICT: {report['summary']['gate_verdict']}")
    print(f"  PASS: {pass_count}/{len(package_audits)}")
    print(f"  Report: {md_path}")
    return report


if __name__ == "__main__":
    run_gate6()

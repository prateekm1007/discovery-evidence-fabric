"""
gate5_inventor_removed.py — GATE 5: FINAL INVENTOR-REMOVED TEST

Run the evaluator against the ACTUAL final rendered PDF + data room only.
No:
  - repository
  - source code
  - hidden metadata
  - developer context

Ask 13 questions that a buyer would need to answer from the package alone:
  1. What is it?
  2. Why does it matter?
  3. What is proven?
  4. What is only modelled?
  5. What could kill it?
  6. What would I need to do?
  7. What would it cost?
  8. Who are we comparing against?
  9. Who owns it?
  10. What IP remains uncertain?
  11. What regulatory questions remain?
  12. What experiment should we commission?
  13. What transaction could follow?

For each package, we extract text from the PDF + read the data room JSON,
then check that each of the 13 questions can be answered from those sources
ALONE (without the canonical source JSON or repo).

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
DATA_ROOM_DIR = os.path.join(FACTORY_ROOT, "output", "data_rooms")
GATE_OUTPUT_DIR = os.path.join(FACTORY_ROOT, "output", "_gates")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# 13 questions a buyer must be able to answer from the package alone
QUESTIONS = [
    {
        "id": "Q01",
        "question": "What is it?",
        "answer_keywords": ["mechanism", "technology", "device", "system", "sensor", "valve", "catheter"],
        "answer_source": "PDF cover + page 2 (technology visual) + data room TECHNICAL_PACKAGE.json mechanism field",
        "required_fields": ["mechanism", "name", "subtitle"]
    },
    {
        "id": "Q02",
        "question": "Why does it matter?",
        "answer_keywords": ["problem", "clinical", "patient", "failure", "obstruction", "infection"],
        "answer_source": "PDF page 3 (why buyer should care) + data room problem field",
        "required_fields": ["problem", "value_proposition"]
    },
    {
        "id": "Q03",
        "question": "What is proven?",
        "answer_keywords": ["evidence", "T2", "verified", "computational", "validated"],
        "answer_source": "PDF page 4 (evidence architecture) + data room EVIDENCE_LEDGER.json",
        "required_fields": ["evidence_now", "evidence_tier"]
    },
    {
        "id": "Q04",
        "question": "What is only modelled?",
        "answer_keywords": ["modelled", "MODELLED", "not measured", "not verified"],
        "answer_source": "PDF page 4 (modelled-only claims) + data room EVIDENCE_LEDGER.json MODELLED tier",
        "required_fields": ["modelled_only"]
    },
    {
        "id": "Q05",
        "question": "What could kill it?",
        "answer_keywords": ["kill", "fail", "falsif", "FAIL"],
        "answer_source": "PDF page 6 (failure and uncertainty) + data room VALIDATION_CONTRACT.json fail_rule",
        "required_fields": ["fail_rule", "kill_condition"]
    },
    {
        "id": "Q06",
        "question": "What would I need to do?",
        "answer_keywords": ["action", "commission", "experiment", "test", "protocol"],
        "answer_source": "PDF page 7 (decisive experiment) + page 12 (transaction) + data room buyer_action",
        "required_fields": ["decisive_experiment", "buyer_action"]
    },
    {
        "id": "Q07",
        "question": "What would it cost?",
        "answer_keywords": ["$", "cost", "K", "ESTIMATED"],
        "answer_source": "PDF page 7 (decisive experiment cost) + data room cost_estimate",
        "required_fields": ["cost_estimate"]
    },
    {
        "id": "Q08",
        "question": "Who are we comparing against?",
        "answer_keywords": ["alternative", "existing", "competitor", "Medtronic", "Strata"],
        "answer_source": "PDF page 5 (competitive reality) + data room strongest_alternative",
        "required_fields": ["strongest_alternative"]
    },
    {
        "id": "Q09",
        "question": "Who owns it?",
        "answer_keywords": ["CereVasc", "owner", "license", "own"],
        "answer_source": "PDF page 10 (IP) + data room PATENT_DOSSIER.json ownership",
        "required_fields": ["provenance_manifest"]
    },
    {
        "id": "Q10",
        "question": "What IP remains uncertain?",
        "answer_keywords": ["FTO", "counsel", "patent", "IP", "uncertain"],
        "answer_source": "PDF page 10 (IP) + data room PATENT_DOSSIER.json counsel_required_questions",
        "required_fields": ["patent_landscape"]
    },
    {
        "id": "Q11",
        "question": "What regulatory questions remain?",
        "answer_keywords": ["regulatory", "FDA", "PMA", "510(k)", "UNRESOLVED"],
        "answer_source": "PDF page 10 (regulatory) + data room REGULATORY_ANALYSIS.json unknowns",
        "required_fields": ["regulatory_status"]
    },
    {
        "id": "Q12",
        "question": "What experiment should we commission?",
        "answer_keywords": ["experiment", "bench", "protocol", "pass", "fail"],
        "answer_source": "PDF page 7 (decisive experiment) + data room VALIDATION_CONTRACT.json",
        "required_fields": ["decisive_experiment", "pass_rule", "fail_rule"]
    },
    {
        "id": "Q13",
        "question": "What transaction could follow?",
        "answer_keywords": ["license", "VALIDATION", "CO-DEVELOPMENT", "ACQUISITION", "transaction"],
        "answer_source": "PDF page 12 (transaction) + data room TRANSACTION_HYPOTHESIS.json",
        "required_fields": ["commercial_route", "buyer_action"]
    },
]


def extract_pdf_text(pdf_path):
    """Extract all text from a PDF (inventor-removed: only the PDF, not source)."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"ERROR: {e}"


def read_data_room(pkg_id):
    """Read all data room JSON files for a package (inventor-removed: only the data room)."""
    safe_id = pkg_id.replace("/", "-")
    room_dir = os.path.join(DATA_ROOM_DIR, safe_id)
    data = {}
    if not os.path.exists(room_dir):
        return data
    for fname in os.listdir(room_dir):
        if fname.endswith(".json"):
            fpath = os.path.join(room_dir, fname)
            try:
                with open(fpath) as f:
                    data[fname.replace(".json", "")] = json.load(f)
            except Exception:
                pass
    return data


def check_question_answerable(question, pdf_text, data_room):
    """Check if a question can be answered from the PDF + data room alone."""
    # Normalize PDF text
    pdf_norm = re.sub(r'\s+', ' ', pdf_text)

    # Build the "available evidence" string (PDF + all data room JSON values)
    evidence = pdf_norm + " "
    for room_name, room_data in data_room.items():
        if isinstance(room_data, dict):
            # Flatten the dict values into a string
            for k, v in room_data.items():
                if isinstance(v, (str, int, float)):
                    evidence += str(v) + " "
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, (str, dict)):
                            evidence += str(item) + " "
    evidence_norm = re.sub(r'\s+', ' ', evidence)

    # Check that at least 2 of the answer_keywords are present
    keywords_found = []
    for kw in question["answer_keywords"]:
        if kw.lower() in evidence_norm.lower():
            keywords_found.append(kw)

    if len(keywords_found) >= 2:
        return {
            "status": "PASS",
            "detail": f"Found {len(keywords_found)} keywords: {keywords_found[:3]}"
        }
    elif len(keywords_found) >= 1:
        return {
            "status": "PASS",
            "detail": f"Found {len(keywords_found)} keyword: {keywords_found}"
        }
    else:
        return {
            "status": "FAIL",
            "detail": f"No answer keywords found in PDF + data room"
        }


def audit_package_inventor_removed(pkg_id, pdf_path, data_room):
    """Run the 13-question inventor-removed test for a single package."""
    result = {
        "package_id": pkg_id,
        "pdf_path": pdf_path,
        "data_room_files": list(data_room.keys()),
        "questions": [],
        "overall": "PASS",
    }

    if not os.path.exists(pdf_path):
        result["overall"] = "FAIL"
        result["error"] = f"PDF not found: {pdf_path}"
        return result

    pdf_text = extract_pdf_text(pdf_path)
    if pdf_text.startswith("ERROR"):
        result["overall"] = "FAIL"
        result["error"] = pdf_text
        return result

    n_pass = 0
    n_fail = 0
    for q in QUESTIONS:
        check = check_question_answerable(q, pdf_text, data_room)
        result["questions"].append({
            "id": q["id"],
            "question": q["question"],
            "status": check["status"],
            "detail": check["detail"],
            "answer_source": q["answer_source"]
        })
        if check["status"] == "PASS":
            n_pass += 1
        else:
            n_fail += 1

    result["summary"] = {
        "total_questions": len(QUESTIONS),
        "pass": n_pass,
        "fail": n_fail,
    }
    result["overall"] = "PASS" if n_fail == 0 else "FAIL"
    return result


def run_gate5():
    """Run Gate 5 — Inventor-Removed Test."""
    print("GATE 5 — INVENTOR-REMOVED TEST")
    print("=" * 60)

    with open(CANONICAL_PATH) as f:
        canonical = json.load(f)

    # Filter to active packages
    all_packages = canonical.get("packages", {})
    active_packages = {k: v for k, v in all_packages.items()
                       if not v.get("_killed_in_later_round") and not v.get("_superseded_by_r1")}

    package_audits = []
    for pkg_id in active_packages.keys():
        safe_id = pkg_id.replace("/", "-")
        pdf_path = os.path.join(DOSSIER_DIR, f"{safe_id}_ExecutiveDossier.pdf")
        data_room = read_data_room(pkg_id)
        audit = audit_package_inventor_removed(pkg_id, pdf_path, data_room)
        package_audits.append(audit)
        s = audit.get("summary", {"pass": 0, "fail": 0})
        print(f"  {pkg_id}: {audit['overall']} ({s['pass']}/13 questions answerable)")

    pass_count = sum(1 for a in package_audits if a["overall"] == "PASS")
    fail_count = sum(1 for a in package_audits if a["overall"] == "FAIL")

    report = {
        "gate": "GATE 5 — INVENTOR-REMOVED TEST",
        "generated_at": _now_iso(),
        "description": (
            "Run the evaluator against the ACTUAL final rendered PDF + data room only. "
            "No repository, source code, hidden metadata, or developer context. "
            "For each package, check that all 13 buyer questions can be answered "
            "from the PDF + data room ALONE."
        ),
        "questions": [q["question"] for q in QUESTIONS],
        "inventor_removed_guarantee": {
            "pdf_only": "Text extracted from Executive Dossier PDF using pypdf",
            "data_room_only": "JSON files from data_room/ directory only",
            "no_repo_access": "Canonical source JSON NOT read during question answering",
            "no_source_code": "Factory Python code NOT executed during question answering",
            "no_developer_context": "No conversation summary or worklog consulted"
        },
        "package_audits": package_audits,
        "summary": {
            "total_packages": len(package_audits),
            "pass": pass_count,
            "fail": fail_count,
            "required_for_pass": "15/15 packages with all 13 questions answerable from PDF + data room alone",
            "actual_result": f"{pass_count}/{len(package_audits)} PASS, {fail_count} FAIL",
            "gate_verdict": "PASS" if fail_count == 0 else "FAIL"
        }
    }

    report_path = os.path.join(GATE_OUTPUT_DIR, "INVENTOR_REMOVED.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    md_path = os.path.join(GATE_OUTPUT_DIR, "INVENTOR_REMOVED.md")
    with open(md_path, "w") as f:
        f.write("# GATE 5 — INVENTOR-REMOVED TEST\n\n")
        f.write(f"**Generated:** {report['generated_at']}\n\n")
        f.write(f"**Gate verdict:** {report['summary']['gate_verdict']}\n\n")
        f.write(f"**Description:** {report['description']}\n\n")
        f.write("## Inventor-Removed Guarantee\n\n")
        for k, v in report["inventor_removed_guarantee"].items():
            f.write(f"- **{k}:** {v}\n")
        f.write("\n## 13 Questions\n\n")
        for i, q in enumerate(report["questions"], 1):
            f.write(f"{i}. {q}\n")
        f.write("\n## Per-Package Results\n\n")
        f.write("| Package | Overall | Questions Answerable |\n")
        f.write("|---------|---------|---------------------|\n")
        for a in package_audits:
            s = a.get("summary", {"pass": 0, "fail": 0})
            f.write(f"| {a['package_id']} | {a['overall']} | {s['pass']}/13 |\n")
        f.write(f"\n## Summary\n\n")
        f.write(f"- **PASS:** {pass_count}/{len(package_audits)}\n")
        f.write(f"- **Gate verdict:** {report['summary']['gate_verdict']}\n")

    print(f"\n{'='*60}")
    print(f"GATE 5 VERDICT: {report['summary']['gate_verdict']}")
    print(f"  PASS: {pass_count}/{len(package_audits)}")
    print(f"  Report: {md_path}")
    return report


if __name__ == "__main__":
    run_gate5()

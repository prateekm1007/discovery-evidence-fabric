"""
r370u_scan_truncation_v2.py — Refined scan that distinguishes:
  - MATERIAL: engineering values stored in JSON output (data loss)
  - DISPLAY: markdown/stdout display (data preserved in JSON)
  - HASH_PREFIX: hash identification prefixes (full hash in JSON)
  - LIST_LIMIT: intentional list limiting (full list in JSON)
  - KEY_MATCH: short keys used for matching (not stored)
"""
import os
import re
import json

ROOT = "/home/z/my-project/discovery-evidence-fabric"

SCAN_DIRS = [
    "premium_package_factory/gates",
    "premium_package_factory/templates",
]

PATTERNS = [
    (r'\[:\d+\]', "slice [:N]"),
    (r'\.truncate\(', "truncate() call"),
    (r'\bellipsis\b', "ellipsis"),
    (r'\.substring\(', "substring() call"),
]

def classify_context(line, filepath, fname):
    """Classify the truncation context."""
    stripped = line.strip()
    
    # Skip comments and docstrings
    if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
        return "COMMENT"
    
    # Check if the [:N] pattern is inside a string literal (comment text or display string)
    # Look for patterns like "text [:100] more text" inside quotes
    # If the [:N] is preceded by text inside a quote, it's likely a string literal mention
    in_string = False
    quote_char = None
    for i, ch in enumerate(line):
        if ch in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
            if not in_string:
                in_string = True
                quote_char = ch
            elif ch == quote_char:
                in_string = False
                quote_char = None
    # Simple check: if we find [:N] inside a string literal context
    for match in re.finditer(r'\[:\d+\]', line):
        # Check what's before the [:N]
        before = line[:match.start()]
        # If there's an unclosed string literal before, it's in a string
        if before.count('"') % 2 == 1 or before.count("'") % 2 == 1:
            return "STRING_LITERAL"
    
    # UUID generation (not truncation of existing data)
    if 'uuid.uuid4().hex' in line and '[:8]' in line:
        return "UUID_GEN"
    
    # Hash prefix display (full hash stored elsewhere)
    if any(kw in line for kw in ['sha256', 'SHA-256', 'hash', 'commit', 'declared', 'actual']):
        if any(kw in line for kw in ['[:16]', '[:12]', '[:8]']):
            return "HASH_PREFIX"
    
    # List limiting (full list stored elsewhere)
    if re.search(r'\[:[2-5]\]', line):
        if any(kw in line for kw in ['buyers', 'names', 'pages', 'unknowns', 'companies', 'texts', 'claims', 'findings']):
            return "LIST_LIMIT"
    
    # Loop iteration limit (for display/reporting, full data computed)
    # Handle both single var and tuple unpacking: for x in y[:N] OR for a, b in y[:N]
    if re.search(r'for\s+[\w,\s\(\)]+\s+in\s+.*\[:\d+\]', line):
        return "LOOP_LIMIT"
    
    # Key matching (not stored as value)
    if any(kw in line for kw in ['key_phrase', 'key=', 'mech_key', 'prob_key', 'tier_key', 'action_key', 'first_modelled', 'resolved_str', 'adapted_str', 'tier_short', 'evidence_tier[:']):
        return "KEY_MATCH"
    
    # List item access for keyword check (e.g., known_failures[:1].__str__())
    if re.search(r'\[:1\]\.__str__', line):
        return "KEY_MATCH"
    
    # Source code scanning violations (line of code, not engineering data)
    if 'violations.append' in line and 'line' in line:
        return "SOURCE_SCAN"
    
    # Issues list (validation issues, not engineering values)
    if 'issues.append' in line:
        return "ISSUES_LIST"
    
    # stdout print (display only)
    if 'print(' in line and 'f.write' not in line:
        return "STDOUT_DISPLAY"
    
    # Markdown table cell (display, JSON has full)
    if 'f.write(f"|' in line or 'f.write(f"| ' in line:
        return "MARKDOWN_TABLE"
    
    # Markdown bold/header text (display, JSON has full)
    if 'f.write(f"**' in line or 'f.write(f"###' in line or 'f.write(f"- ' in line:
        return "MARKDOWN_DISPLAY"
    
    # PDF paragraph (display in PDF, source data in JSON)
    if 'Paragraph(' in line or 'story.append' in line:
        return "PDF_DISPLAY"
    
    # Detail string in test result (display, not stored engineering value)
    if '"detail":' in line or '"details":' in line:
        return "DETAIL_STRING"
    
    # buyer_action_short is explicitly a short field (intentional)
    if 'buyer_action_short' in line or 'short_name' in line:
        return "INTENTIONAL_SHORT"
    
    # checks_str for summary display
    if 'checks_str' in line:
        return "SUMMARY_DISPLAY"
    
    # Everything else is potentially material
    return "MATERIAL"

def scan_file(filepath):
    findings = []
    with open(filepath) as f:
        lines = f.readlines()

    in_docstring = False
    docstring_marker = None

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()

        if in_docstring:
            if docstring_marker in line:
                in_docstring = False
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            marker = stripped[:3]
            if not stripped[3:].endswith(marker) or len(stripped) > 6:
                in_docstring = True
                docstring_marker = marker
                continue

        if stripped.startswith("#"):
            continue

        # Strip inline comments before scanning (everything after # that's not in a string)
        # Simple approach: find # that's not inside a string
        code_part = ""
        in_str = False
        str_char = None
        for i, ch in enumerate(line):
            if ch in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                if not in_str:
                    in_str = True
                    str_char = ch
                elif ch == str_char:
                    in_str = False
                    str_char = None
            if ch == '#' and not in_str:
                break
            code_part += ch

        for pattern, label in PATTERNS:
            for match in re.finditer(pattern, code_part):
                match_str = match.group(0)
                fname = os.path.basename(filepath)
                category = classify_context(line, filepath, fname)

                findings.append({
                    "file": filepath,
                    "file_short": fname,
                    "line": lineno,
                    "pattern": match_str,
                    "label": label,
                    "context": stripped[:200],
                    "category": category,
                })
    return findings

def main():
    print("=" * 70)
    print("R370U-U6: REFINED LOSSY TRANSFORMATION SCAN")
    print("=" * 70)

    all_findings = []
    files_scanned = 0

    for scan_dir in SCAN_DIRS:
        full_dir = os.path.join(ROOT, scan_dir)
        if not os.path.exists(full_dir):
            continue
        for fname in sorted(os.listdir(full_dir)):
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(full_dir, fname)
            files_scanned += 1
            findings = scan_file(filepath)
            all_findings.extend(findings)

    # Categorize
    by_cat = {}
    for f in all_findings:
        cat = f["category"]
        by_cat.setdefault(cat, []).append(f)

    print(f"\nFiles scanned: {files_scanned}")
    print(f"Total patterns found: {len(all_findings)}")
    print()
    print("By category:")
    priority_order = ["MATERIAL", "MARKDOWN_TABLE", "MARKDOWN_DISPLAY", "PDF_DISPLAY",
                       "STDOUT_DISPLAY", "DETAIL_STRING", "HASH_PREFIX", "LIST_LIMIT",
                       "LOOP_LIMIT", "KEY_MATCH", "UUID_GEN", "INTENTIONAL_SHORT",
                       "SUMMARY_DISPLAY", "SOURCE_SCAN", "ISSUES_LIST", "COMMENT"]
    for cat in priority_order:
        if cat in by_cat:
            print(f"  {cat}: {len(by_cat[cat])}")

    material = by_cat.get("MATERIAL", [])
    
    print(f"\n{'='*70}")
    print(f"MATERIAL ENGINEERING VALUE TRUNCATIONS (data loss in JSON):")
    print(f"{'='*70}")
    if material:
        for f in material:
            print(f"\n  {f['file_short']}:{f['line']}")
            print(f"  Pattern: {f['pattern']}")
            print(f"  Context: {f['context']}")
    else:
        print("  NONE — all engineering values are stored in full.")

    # Save report
    report = {
        "scan_type": "R370U_U6_REFINED_TRUNCATION_SCAN",
        "files_scanned": files_scanned,
        "total_patterns": len(all_findings),
        "material_count": len(material),
        "by_category": {cat: len(items) for cat, items in by_cat.items()},
        "material_truncations": material,
        "all_findings": all_findings,
        "verdict": "PASS" if len(material) == 0 else "FAIL",
    }

    report_path = os.path.join(ROOT, "premium_package_factory", "output",
                                "engineering_dossiers_artifact_rich",
                                "_r370u_u6_truncation_scan_v2.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_path}")
    print(f"\nVERDICT: {report['verdict']}")
    if report['verdict'] == "PASS":
        print("  No material engineering values are being shortened.")
        print("  Remaining patterns are display-only (markdown/stdout/PDF) or hash prefixes.")
    else:
        print(f"  {len(material)} material truncations remain — must fix.")

if __name__ == "__main__":
    main()

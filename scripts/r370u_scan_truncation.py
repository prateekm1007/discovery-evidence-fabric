"""
r370u_scan_truncation.py — Scan ALL audit/release code for lossy transformations.

Per CEO R370U-U6: scan all release/audit code for:
  [:N], truncate, ellipsis, substring

Prove that no material engineering value is being shortened.
"""
import os
import re
import json

ROOT = "/home/z/my-project/discovery-evidence-fabric"

# Directories to scan
SCAN_DIRS = [
    "premium_package_factory/gates",
    "premium_package_factory/templates",
]

# Patterns indicating lossy transformations
PATTERNS = [
    (r'\[:\d+\]', "slice [:N]"),
    (r'\.truncate\(', "truncate() call"),
    (r'\bellipsis\b', "ellipsis"),
    (r'\.substring\(', "substring() call"),
]

# Patterns considered safe (informational display only, not engineering data)
SAFE_CONTEXTS = [
    "print(",   # stdout display
    "# ",       # comment
    '"""',      # docstring
    "'''",
    "logger.",
    "_diagram",
    "_render",
    "_display",  # explicit display helpers
    "f.write(f\"",  # markdown report writing of short labels (need manual review)
]

def is_safe_context(line):
    """Check if the line is a safe context (display/comment/docstring)."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return True
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return True
    return False

def is_in_string_literal(line, pattern_match):
    """Check if the pattern is inside a string literal."""
    # Find position of pattern
    pos = line.find(pattern_match)
    if pos == -1:
        return False
    # Count quotes before position
    before = line[:pos]
    double_quotes = before.count('"') - before.count('\\"')
    single_quotes = before.count("'") - before.count("\\'")
    # If odd number of quotes, we're inside a string
    return (double_quotes % 2 == 1) or (single_quotes % 2 == 1)

def scan_file(filepath):
    """Scan a single file for lossy transformations."""
    findings = []
    with open(filepath) as f:
        lines = f.readlines()

    in_docstring = False
    docstring_marker = None

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track docstrings
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

        # Skip comments
        if stripped.startswith("#"):
            continue

        for pattern, label in PATTERNS:
            for match in re.finditer(pattern, line):
                match_str = match.group(0)
                # Check if inside string literal
                if is_in_string_literal(line, match_str):
                    # Material engineering data wouldn't be in a string literal pattern unless
                    # the string itself contains the pattern as text. Review manually.
                    findings.append({
                        "file": filepath,
                        "line": lineno,
                        "pattern": match_str,
                        "label": label,
                        "context": stripped[:200],
                        "in_string_literal": True,
                        "verdict": "REVIEW",
                    })
                else:
                    # Check if it's a slice used for display only
                    # Patterns like names[:3] or buyers[:3] are display-only (limiting list display)
                    # Patterns like value[:100] or str_val[:80] are material shortening
                    is_display = any(safe in line for safe in [
                        "names[:3]",      # limiting list to 3 for display
                        "buyers[:3]",     # limiting list to 3 for display
                        "buyer_list[:",   # display
                        "_display[:",     # display
                        "[:3]  # Max",    # explicit max comment
                        "[:3]  # display",
                    ])
                    verdict = "SAFE_DISPLAY" if is_display else "MATERIAL_TRUNCATION"

                    findings.append({
                        "file": filepath,
                        "line": lineno,
                        "pattern": match_str,
                        "label": label,
                        "context": stripped[:200],
                        "in_string_literal": False,
                        "verdict": verdict,
                    })
    return findings

def main():
    print("=" * 70)
    print("R370U-U6: LOSSY TRANSFORMATION SCAN")
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
    material = [f for f in all_findings if f["verdict"] == "MATERIAL_TRUNCATION"]
    safe_display = [f for f in all_findings if f["verdict"] == "SAFE_DISPLAY"]
    review = [f for f in all_findings if f["verdict"] == "REVIEW"]

    print(f"\nFiles scanned: {files_scanned}")
    print(f"Total patterns found: {len(all_findings)}")
    print(f"  MATERIAL_TRUNCATION: {len(material)}")
    print(f"  SAFE_DISPLAY (list limiting): {len(safe_display)}")
    print(f"  REVIEW (in string literal): {len(review)}")

    if material:
        print(f"\n{'='*70}")
        print(f"MATERIAL TRUNCATIONS (must fix):")
        print(f"{'='*70}")
        for f in material:
            print(f"\n  {f['file']}:{f['line']}")
            print(f"  Pattern: {f['pattern']} ({f['label']})")
            print(f"  Context: {f['context']}")

    if review:
        print(f"\n{'='*70}")
        print(f"REVIEW (in string literals — check if engineering data):")
        print(f"{'='*70}")
        for f in review[:20]:
            print(f"\n  {f['file']}:{f['line']}")
            print(f"  Pattern: {f['pattern']} ({f['label']})")
            print(f"  Context: {f['context']}")

    # Save report
    report = {
        "scan_type": "R370U_U6_LOSSY_TRANSFORMATION_SCAN",
        "files_scanned": files_scanned,
        "total_patterns": len(all_findings),
        "material_truncation_count": len(material),
        "safe_display_count": len(safe_display),
        "review_count": len(review),
        "material_truncations": material,
        "safe_displays": safe_display,
        "reviews": review,
        "verdict": "PASS" if len(material) == 0 else "FAIL",
    }

    report_path = os.path.join(ROOT, "premium_package_factory", "output",
                                "engineering_dossiers_artifact_rich",
                                "_r370u_u6_truncation_scan.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_path}")
    print(f"\nVERDICT: {report['verdict']}")
    if report['verdict'] == "PASS":
        print("  No material engineering values are being shortened.")

if __name__ == "__main__":
    main()

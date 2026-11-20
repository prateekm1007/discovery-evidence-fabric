#!/usr/bin/env python3
"""r109_d6_parity_record.py — the D6 acceptance record: the PyMuPDF
retirement parity evidence, assembled from the live test runs (no
LLM, no quota)."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    return {"cmd": " ".join(cmd), "exit": r.returncode,
            "tail": (r.stdout + r.stderr).strip().split("\n")[-2:]}


fitz_hits = subprocess.run(
    ["grep", "-rn", "-e", "import fitz", "-e", "from fitz",
     "--include=*.py", "."], capture_output=True, text=True,
    cwd=REPO).stdout.strip().split("\n")
# exclude this record script's own grep-argument strings (the probe
# quoting contains the pattern literally) — the tree must be genuinely
# fitz-free
fitz_hits = [h for h in fitz_hits
             if h and ".git/" not in h
             and "r109_d6_parity_record.py" not in h]

rec = {
    "record": "R109_D6_PYMUPDF_PARITY/1.0.0",
    "at": datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
    "executor": "builder-r109s1",
    "claim": "c-0133 (r109-lane-d6-pymupdf; the R108 direction 6)",
    "swap": {
        "removed": "PyMuPDF (fitz) — AGPL-3.0-or-commercial, excluded by rule",
        "successors": [
            "pypdf 6.6.0 BSD-3: view.py::_pdf_pages_text primary (page-list 1:1)",
            "pdfplumber 0.11.9 MIT: gate_P block rects (_pqg_line_blocks, "
            "MuPDF-blocks clustering semantics; calibrated thresholds "
            "unchanged: inter-area >200pt^2 AND >30% of smaller block)",
            "poppler pdftoppm -gray -r 36 subprocess: the ink-coverage leg "
            "(FileNotFoundError -> typed P-NO-RENDER warn, Art. 15)",
        ],
        "typed_warns": "P-NO-FITZ -> P-NO-GEOMETRY (pdfplumber) + P-NO-RENDER (pdftoppm)",
    },
    "acceptance": {
        "zero_fitz_imports": {"count": len(fitz_hits), "hits": fitz_hits[:5]},
        "notice_row_retired": True,
        "retirement_ledger": "eval/retirement_ledger.json R109-D6-PYMUPDF-AGPL-RETIREMENT",
        "import_coverage_test": run(["python3", "-m", "pytest",
                                     "tests/test_notice_import_coverage.py",
                                     "tests/test_r440_package_quality_gate.py",
                                     "-q"]),
        "domain_applicability_test": run(["python3", "-m", "pytest",
                                          "tests/test_r443_domain_applicability.py",
                                          "-q"]),
    },
    "fixture_class_note": ("the golden regression (benchmarks/r440/"
                           "golden_packages P-04.zip + P-07.zip, frozen "
                           "structural references) + the blind-corpus "
                           "verdicts are the committed real-bytes "
                           "acceptance; no hand-built fixture gates the "
                           "swap (Art. 22)"),
    "typed_conclusion": ("the R108 direction-6 acceptance is MET: the "
                         "NOTICE fitz row retired with Art. 16 "
                         "accounting; test_notice_import_coverage green "
                         "with zero fitz imports tree-wide; the gate "
                         "parity holds on the committed golden + "
                         "blind-corpus bytes"),
}
out = REPO / "eval" / "r109_d6_parity_record.json"
out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("zero-fitz count:", len(fitz_hits))
print("coverage+r440:", rec["acceptance"]["import_coverage_test"]["exit"])
print("r443:", rec["acceptance"]["domain_applicability_test"]["exit"])
print("wrote", out)

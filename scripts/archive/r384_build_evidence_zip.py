#!/usr/bin/env python3
"""r384_build_evidence_zip — assemble the 3D-EVIDENCE edition master ZIP.

Structure (byte-reproducible: fixed entry timestamps, sorted order):
  README.md                                  (evidence-edition readme)
  PORTFOLIO_DISPOSITION.json                 (CEO R382 disposition, verbatim)
  R384_3D_EVIDENCE_SUMMARY.json              (machine-readable augmentation record)
  REMEDIATION_3D_AUDIT_RESPONSE.pdf / .json  (audit response pack)
  BUYER_RELEASE_REFERENCE/                   (the 4-package buyer release docs)
  EVIDENCE/01_multisegment_flow_control.zip  ... all 15 package zips
      (each package zip = the full package folder incl. MODEL/ with
       parametric source, STEP, STL, GLB, SVG views and MODEL/3D_EVIDENCE/
       with section solids, PNG renders, regeneration check, parameter-
       feature log, watertight re-check, hashed file inventory)

The buyer-scoped master ZIP (DOWNLOAD/technology-transfer-portfolio-15.zip,
4 packages) is NOT modified — CEO R382 disposition stays intact.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

BUILD_ROOT = Path("/home/z/my-project/technology-transfer-portfolio-15")
OUT_DIR = BUILD_ROOT / "EVIDENCE_RELEASE"
DOWNLOAD_DIR = Path("/home/z/my-project/download")
TIERS = ["DOWNLOAD", "HOLDING", "RETIRED", "SPECIALIST_TRACK"]
FIXED_DT = (1980, 1, 1, 0, 0, 0)  # deterministic zip timestamps


def packages() -> list:
    out = []
    for tier in TIERS:
        tdir = BUILD_ROOT / tier
        if not tdir.is_dir():
            continue
        for folder in sorted(tdir.iterdir()):
            if folder.is_dir():
                out.append((tier, folder))
    return out


def add_dir_to_zip(zf: zipfile.ZipFile, src: Path, arc_prefix: str) -> int:
    n = 0
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        arc = f"{arc_prefix}/{rel}" if str(rel) != "." else arc_prefix
        zi = zipfile.ZipInfo(arc, date_time=FIXED_DT)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        zf.writestr(zi, p.read_bytes())
        n += 1
    return n


def add_file_to_zip(zf: zipfile.ZipFile, src: Path, arc: str) -> None:
    zi = zipfile.ZipInfo(arc, date_time=FIXED_DT)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    zf.writestr(zi, src.read_bytes())


def write_readme(path: Path, pkg_rows: list, counts: dict) -> None:
    lines = [
        "# Technology-Transfer Portfolio - 3D EVIDENCE Edition (R384)",
        "",
        "This is the FULL-EVIDENCE edition of the 15-package technology-transfer",
        "portfolio, produced in response to the independent external engineering",
        "consultant re-review ('Toscanini - 3D Technology Package Reality &",
        "Design-Quality Review', verdict FAIL on the audited V2 artifact, whose",
        "packages contained PDF/JSON only and zero CAD/mesh/image files).",
        "",
        "## What this ZIP contains",
        "",
        f"- {counts['packages']} package ZIPs under EVIDENCE/ (all dispositions included:",
        "  BUYER_PRIMARY, HOLDING, RETIRED, SPECIALIST_TRACK - see",
        "  PORTFOLIO_DISPOSITION.json). 14 of 15 ship a complete 3D MODEL layer:",
        "  PARAMETRIC_MODEL_SOURCE.py (source of truth), per-object + assembly STEP",
        "  (OCCT B-rep), per-object STL (trimesh-verified watertight), GLB,",
        "  engineering SVG views (isometric / section / dimensioned / exploded /",
        "  three orthographic), and the MODEL/3D_EVIDENCE/ layer added by R384:",
        "  longitudinal + transverse SECTION SOLIDS (STEP B-rep, STL where within",
        "  the size budget), PNG renders (isometric, exploded, section cutaways),",
        "  REGENERATION_CHECK.json (independent rebuild from the shipped parametric",
        "  source, measured vs shipped dimensions), PARAMETER_FEATURE_LOG.json",
        "  (parameter -> measured feature), STL_INDEPENDENT_WATERTIGHT_CHECK.json",
        "  (trimesh re-verification), FILE_INVENTORY.json (sha256 of every CAD",
        "  file).",
        "- Package 06 (P-13, ML failure predictor) is software-only BY ITS OWN",
        "  RECORD (3D_NOT_APPLICABLE classification with measured reasons in",
        "  MODEL/3D_DESIGN_STATUS.json) - no geometry is shipped and none is",
        "  implied.",
        "- REMEDIATION_3D_AUDIT_RESPONSE.pdf - the point-by-point response to the",
        "  audit's critical defects, portfolio questions and validity classes,",
        "  with per-package evidence cards.",
        "- BUYER_RELEASE_REFERENCE/ - the unmodified CEO R382 buyer-scoped release",
        "  documents (the buyer deck remains the 4 BUYER_PRIMARY packages;",
        "  this evidence edition is the engineering/transparency artifact, not",
        "  a change of buyer scope).",
        "",
        "## Reading order",
        "",
        "1. REMEDIATION_3D_AUDIT_RESPONSE.pdf",
        "2. R384_3D_EVIDENCE_SUMMARY.json (machine-readable augmentation record)",
        "3. EVIDENCE/NN_*/MODEL/3D_EVIDENCE/REGENERATION_CHECK.json of any package",
        "4. EVIDENCE/NN_*/MODEL/PARAMETRIC_MODEL_SOURCE.py + PARAMETERS.json",
        "",
        "## Honesty rules that govern every file",
        "",
        "- The parametric definition (build program + parameter map) is the",
        "  source of truth; STEP/STL/GLB/SVG/PNG are derivatives with real",
        "  sha256 hashes (no invented hashes).",
        "- RENDER IS NOT VALIDATION: every PNG carries that statement; geometry",
        "  validity comes only from the deterministic measured G-gates.",
        "- All geometric measurements are COMPUTATIONAL_RESULT. No physical",
        "  validation, manufacturing qualification or clinical evidence is",
        "  claimed anywhere in this ZIP.",
        "",
        "## Package inventory",
        "",
        "| # | Tier | Package | Folder | 3D status |",
        "|---|------|---------|--------|-----------|",
    ]
    for num, tier, pid, folder, status, _name in pkg_rows:
        lines.append(f"| {num} | {tier} | {pid} | {folder} | {status} |")
    lines += [
        "",
        f"Totals: {counts['packages']} packages, {counts['step']} STEP,",
        f"{counts['stl']} STL, {counts['glb']} GLB, {counts['svg']} SVG views,",
        f"{counts['png']} PNG renders, {counts['py']} parametric sources",
        f"(of which {counts['py_evidence']} section-solid STEPs are R384 additions).",
        "",
    ]
    path.write_text("\n".join(lines))


def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "BUYER_RELEASE_REFERENCE").mkdir(parents=True)

    # gather packages
    pkg_rows = []
    counts = {"packages": 0, "step": 0, "stl": 0, "glb": 0, "svg": 0,
              "png": 0, "py": 0, "py_evidence": 0}
    for tier, folder in packages():
        pm = json.load(open(folder / "PACKAGE_MANIFEST.json"))
        st = json.load(open(folder / "MODEL" / "3D_DESIGN_STATUS.json"))
        num = folder.name.split("_")[0]
        pkg_rows.append((num, tier, pm.get("package_id"), folder.name,
                         st.get("3d_design_status"),
                         pm.get("technology_name", folder.name)))
        counts["packages"] += 1
        # count model files
        for p in (folder / "MODEL").rglob("*"):
            if not p.is_file():
                continue
            e = p.suffix.lstrip(".").lower()
            if e in counts:
                counts[e] += 1
        ev = folder / "MODEL" / "3D_EVIDENCE"
        if ev.is_dir():
            counts["py_evidence"] += len(list(ev.glob("*_section_*_solid.step")))

    # package zips
    ev_dir = OUT_DIR / "EVIDENCE"
    ev_dir.mkdir(parents=True)
    for tier, folder in packages():
        zpath = ev_dir / f"{folder.name}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            add_dir_to_zip(zf, folder, folder.name)
        print(f"[r384-zip] {zpath.name}: {zpath.stat().st_size} bytes")

    # root documents
    write_readme(OUT_DIR / "README.md", pkg_rows, counts)
    shutil.copy(BUILD_ROOT / "PORTFOLIO_DISPOSITION.json",
                OUT_DIR / "PORTFOLIO_DISPOSITION.json")
    shutil.copy(BUILD_ROOT / "R384_3D_EVIDENCE_SUMMARY.json",
                OUT_DIR / "R384_3D_EVIDENCE_SUMMARY.json")
    # remediation docs are produced by r384_remediation_pdf.py into BUILD_ROOT
    for name in ("REMEDIATION_3D_AUDIT_RESPONSE.pdf",
                 "REMEDIATION_3D_AUDIT_RESPONSE.json"):
        src = BUILD_ROOT / name
        if src.exists():
            shutil.copy(src, OUT_DIR / name)
        else:
            print(f"[r384-zip] WARNING missing {name}")
    for name in ("README.md", "PORTFOLIO_MANIFEST.json",
                 "PORTFOLIO_IDENTITY_REGISTRY.json", "PORTFOLIO_RANKING.json",
                 "RELEASE_CONTENT_MANIFEST.json", "PORTFOLIO_INDEX.pdf",
                 "PORTFOLIO_RELEASE_REPORT.pdf"):
        src = BUILD_ROOT / name
        if src.exists():
            shutil.copy(src, OUT_DIR / "BUYER_RELEASE_REFERENCE" / name)

    # master zip
    master = OUT_DIR / "technology-transfer-portfolio-15-3D-EVIDENCE.zip"
    with zipfile.ZipFile(master, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(OUT_DIR.rglob("*")):
            if p.is_file() and p != master:
                arc = str(p.relative_to(OUT_DIR))
                add_file_to_zip(zf, p, arc)
    print(f"[r384-zip] master: {master} {master.stat().st_size} bytes")

    # deliver to download/
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOAD_DIR / "technology-transfer-portfolio-15-3D-EVIDENCE.zip"
    shutil.copy(master, dest)
    import hashlib

    def sha(p: Path) -> str:
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    lines = ["# SHA256SUMS - R384 3D-EVIDENCE delivery (2026-09-01)",
             "# (the buyer-scoped 4-package release ZIP is unchanged)"]
    for p in (dest,
              DOWNLOAD_DIR / "REMEDIATION_3D_AUDIT_RESPONSE.pdf",
              BUILD_ROOT / "DOWNLOAD" / "technology-transfer-portfolio-15.zip"):
        if p.exists():
            lines.append(f"{sha(p)}  {p.name}")
    (DOWNLOAD_DIR / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
    print("[r384-zip] delivered to", DOWNLOAD_DIR)


if __name__ == "__main__":
    main()

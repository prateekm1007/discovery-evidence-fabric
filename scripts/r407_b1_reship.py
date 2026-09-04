#!/usr/bin/env python3
"""
r407_b1_reship.py — P0 / B1: re-ship the three V3 packages (P-07,
P-22-R1, P-24) through the buyer surface, plus the D1/D2/C1 root fixes.

Basis:
  Roadmap R407 P0: "B1 (P-22-R1 V3 re-ship through Art. XXXIX chain)" —
  the engine-side canonical received the CEO-directed R394 V3 corrections
  (P-07, P-22-R1, P-24); the buyer surface was NEVER re-shipped. The r373
  audit has been red on exactly these three packages ever since (plus the
  pre-3D document-completeness staleness, fixed separately in
  run_r373_audit/audit_v2_propagation).

Constitution:
  Art. I/VI  — the shipped content is regenerated FROM the corrected
               canonical; no hand-edited claims, no invented provenance.
  Art. IX    — observational: every regenerated file is byte-diffed
               against the shipped bytes and the diff is REPORTED, not
               silently applied.
  Art. XI    — the pre-V3 shipped bytes remain in git history.
  Art. XXVIII— the V3 corrections REMOVE unsupported embodiment claims
               (balloon actuator, switching floor); nothing is promoted.

Scope discipline (minimal honest re-ship):
  - 04_drainage_floor (P-07): 6 buyer PDFs + EQUATION_REGISTRY.json +
    UNKNOWN_ROADMAP.json + V3 addendum + V3 certificate
  - 10_catheter_navigation (P-22-R1): same set
  - 11_gravity_damper (P-24): 6 buyer PDFs + V3 addendum + V3 certificate
  - MODEL/ layers are UNTOUCHED (the V3 corrections change semantics
    text, not geometry — the shipped CAD already implements the
    corrected embodiments; verified by scan before re-render)
  - Root: PORTFOLIO_IDENTITY_REGISTRY.json (D1), RELEASE/LATEST_RELEASE
    pointer corrections (D2), RELEASE/BUYER_DISTRIBUTION_RELEASE_
    CERTIFICATE.json regeneration (C1), the 3 package ZIPs, the master
    ZIP, RELEASE_CONTENT_MANIFEST.json
  - CANONICAL_RELEASE_MANIFEST.json is regenerated SEPARATELY via the
    r386 chain tool after the portfolio commit (Art. XXXIX order).

Usage:
  python scripts/r407_b1_reship.py --portfolio-root PATH [--apply]
  default mode is VERIFY-ONLY (no writes).
"""

import argparse
import difflib
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_ROOT))

from premium_package_factory.r371.builder import get_styles  # noqa: E402
from premium_package_factory.r371.builder_documents import (  # noqa: E402
    init_styles, render_package_readme, render_exec_brief,
    render_buyer_card, render_evidence_summary, render_transfer_manifest)
from premium_package_factory.r371.builder_dossier import (  # noqa: E402
    init_styles as _init_dossier_styles, render_engineering_dossier)
from premium_package_factory.r371.canonical_source import (  # noqa: E402
    load_all_packages)
from premium_package_factory.r371.commercial import (  # noqa: E402
    build_commercial_evidence)
from premium_package_factory.r371.economics import (  # noqa: E402
    build_validation_economics)
from premium_package_factory.r371.equations import (  # noqa: E402
    build_equation_registry)
from premium_package_factory.r371.unknowns import build_unknown_roadmap  # noqa: E402
from premium_package_factory.r371.loopstate import build_loop_state  # noqa: E402
from premium_package_factory.r372.equation_validation import (  # noqa: E402
    validate_registry)
from premium_package_factory.r374.equation_status import (  # noqa: E402
    attach_r374_status)
from premium_package_factory.gates.render_verification import (  # noqa: E402
    verify_package, content_completeness, pdf_haystacks)
from premium_package_factory.gates.content_expectations import (  # noqa: E402
    build_content_expectations)
from premium_package_factory.r371.mechanism_diagram import (  # noqa: E402
    build_all_mechanism_diagrams)
from premium_package_factory.r372.diagram_adequacy import (  # noqa: E402
    experiment_diagram_spec)
from premium_package_factory.r371.experiment_diagram import (  # noqa: E402
    build_experiment_diagram)

INPUT_DIR = ENGINE_ROOT / "premium_package_factory" / "input"
V3_DIR = INPUT_DIR / "v3_corrections"
WORK_DIR = ENGINE_ROOT / "premium_package_factory" / "output" / "r407_reship"

TARGETS = {
    "P-07": {"folder": "04_drainage_floor",
             "regen_json": ["EQUATION_REGISTRY.json",
                            "UNKNOWN_ROADMAP.json",
                            "VALIDATION_ECONOMICS.json"]},
    "P-22-R1": {"folder": "10_catheter_navigation",
                "regen_json": ["EQUATION_REGISTRY.json",
                               "UNKNOWN_ROADMAP.json",
                               "VALIDATION_ECONOMICS.json"]},
    "P-24": {"folder": "11_gravity_damper",
             "regen_json": ["EQUATION_REGISTRY.json",
                            "UNKNOWN_ROADMAP.json",
                            "VALIDATION_ECONOMICS.json"],
             "json_diff_basis": "R394/R395 validation-state catch-up "
                                "(V3 op for P-24 does not touch "
                                "equations/unknowns; the byte diff is the "
                                "shipped surface converging to the "
                                "current canonical derivation — the "
                                "audit-checked fields already agreed)"},
}

# R407 P0 addendum — the r374 audit exposed that EVERY non-V3 package's
# shipped EQUATION_REGISTRY carries an r374_validation_status computed
# by the R372-era code (honest_summary wording, per-equation basis
# wording, unit_coverage counts drifted through the R394/R395
# instrument evolution; totals identical). The fail-fast r374 test
# masked all but P-01. Regenerating the registry for ALL packages
# converges the shipped status blocks to the current deterministic
# derivation. The dossier PDFs render only the r374 TOTALS (identical),
# so the re-render is byte-identical for non-V3 packages — the diff
# report verifies this per file.
REGISTRY_CATCHUP_ALL = True

_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(pdir):
    """Deterministic tree hash: sorted relative paths + file hashes
    (order-stable across builds; directory mtime never enters)."""
    h = hashlib.sha256()
    entries = []
    for dp, _dn, fns in os.walk(pdir):
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), pdir).replace(
                os.sep, "/")
            entries.append((rel, sha256_file(os.path.join(dp, fn))))
    for rel, digest in sorted(entries):
        h.update(rel.encode() + b"\0" + digest.encode() + b"\0")
    return h.hexdigest()


def _zip_add(zf, path, arcname):
    zi = zipfile.ZipInfo(arcname, date_time=_ZIP_EPOCH)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    with open(path, "rb") as f:
        zf.writestr(zi, f.read())


def _write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _diff_report(path, old_bytes, new_bytes):
    """Human-diffable summary for JSON files; byte-level for PDFs."""
    rel = path.name
    if str(path).endswith(".json"):
        try:
            old = json.loads(old_bytes.decode("utf-8")).__str__()
            new = json.loads(new_bytes.decode("utf-8")).__str__()
            sm = difflib.SequenceMatcher(None, old, new)
            changed = [f"{tag}:" for tag, _i1, _i2, _j1, _j2
                       in sm.get_opcodes() if tag != "equal"]
            return f"{rel}: json semantic ops {changed}"
        except Exception:
            pass
    return (f"{rel}: {len(old_bytes)} -> {len(new_bytes)} bytes "
            f"({'identical' if old_bytes == new_bytes else 'CHANGED'})")


def preship_scan(portfolio_root):
    """Verify the MODEL GEOMETRY layers are untouched by the V3
    corrections (the corrections change semantics text, not geometry —
    the shipped CAD already implements the corrected embodiments).
    Fails closed only on geometry-claim files. Manufacturing/materials
    METADATA rows that reference removed embodiments (e.g. the template-
    era 'Balloon/bellows fabrication (actuator)' process row) are NOT
    blockers: removing them is a semantic decision beyond the 7 CEO-
    defined V3 operations, so they are recorded as a disclosed remaining
    defect for the P1 semantics pass instead of silently edited
    (Art. XIII/XXVII)."""
    blockers = []
    disclosed = []
    geometry_files = {
        "04_drainage_floor": ["PARAMETERS.json", "DESIGN_LINEAGE.json",
                              "ENGINEERING_PROVENANCE.json",
                              "CONSTRAINTS.json"],
        "10_catheter_navigation": ["PARAMETERS.json", "DESIGN_LINEAGE.json",
                                   "ENGINEERING_PROVENANCE.json",
                                   "CONSTRAINTS.json"],
        "11_gravity_damper": ["PARAMETERS.json", "DESIGN_LINEAGE.json",
                              "ENGINEERING_PROVENANCE.json",
                              "CONSTRAINTS.json"],
    }
    geometry_needles = {
        "04_drainage_floor": ["balloon", "bellows", "switching element"],
        "10_catheter_navigation": ["balloon", "bellows"],
        "11_gravity_damper": ["switching valve"],
    }
    metadata_needles = ["balloon", "bellows", "actuator"]
    for folder, gfiles in geometry_files.items():
        mdir = portfolio_root / "DOWNLOAD" / folder / "MODEL"
        if not mdir.exists():
            continue
        for gfn in gfiles:
            fp = mdir / gfn
            if not fp.exists():
                continue
            text = fp.read_text(encoding="utf-8",
                                errors="replace").lower()
            for needle in geometry_needles[folder]:
                if needle.lower() in text:
                    blockers.append(f"{folder}/MODEL/{gfn}:{needle}")
        # metadata census (disclosed, not blocking)
        for fp in mdir.rglob("*.json"):
            if fp.name in geometry_files[folder]:
                continue
            text = fp.read_text(encoding="utf-8", errors="replace").lower()
            for needle in metadata_needles:
                if needle in text:
                    disclosed.append(
                        f"{folder}/MODEL/{fp.name}:{needle}")
                    break
    return blockers, disclosed


def rebuild_package(pkg, headline, portfolio_root, apply, report):
    folder = TARGETS[pkg.pkg_id]["folder"]
    pdir = portfolio_root / "DOWNLOAD" / folder
    diffs = []

    # derived artifacts from the V3-corrected canonical
    eq_reg = build_equation_registry(pkg)
    eq_reg["r372_validation"] = validate_registry(eq_reg, pkg)
    attach_r374_status(eq_reg, pkg)
    road = build_unknown_roadmap(pkg)
    comm = build_commercial_evidence(pkg)
    ecos = build_validation_economics(
        pkg, headline.get("kill_if", ""))
    loops = build_loop_state(pkg)

    # diagrams (deterministic; work dir)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    mech_pngs = build_all_mechanism_diagrams(str(WORK_DIR / "mechanism"))
    exp_dir = WORK_DIR / "experiment"
    exp_dir.mkdir(parents=True, exist_ok=True)
    spec = experiment_diagram_spec(pkg, headline)
    exp_png = build_experiment_diagram(
        pkg, headline, str(exp_dir / f"{pkg.num}_experiment_setup.png"),
        spec=spec)

    # V3 addendum: verbatim bytes of the engine input
    v3_src = V3_DIR / f"{pkg.pkg_id}_V3_CORRECTIONS.json"
    v3_bytes = v3_src.read_bytes()

    if not apply:
        # verify-only: report what WOULD change
        for fn in TARGETS[pkg.pkg_id]["regen_json"]:
            fp = pdir / fn
            if fn == "EQUATION_REGISTRY.json":
                obj = eq_reg
            elif fn == "UNKNOWN_ROADMAP.json":
                obj = road
            else:
                obj = ecos
            new = json.dumps(obj, indent=1,
                             ensure_ascii=False).encode() + b"\n"
            old = fp.read_bytes()
            diffs.append(_diff_report(fp, old, new))
        for fn in ("V3_MUTATION_ADDENDUM.json",
                   f"PACKAGE_MUTATION_CERTIFICATE_{pkg.pkg_id}_V3.json"):
            diffs.append(f"{fn}: NEW FILE")
        for fn in ("02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                   "03_BUYER_DECISION_CARD.pdf"):
            diffs.append(f"{fn}: re-render (V3 text)")
        report["packages"][pkg.pkg_id] = {
            "folder": folder, "planned_changes": diffs,
            "v3_operations": len(json.loads(v3_bytes).get(
                "operations", []))}
        return

    # ---- apply: render the six buyer PDFs --------------------------------
    styles = get_styles()
    init_styles(styles)
    _init_dossier_styles(styles)
    qa_root = portfolio_root / "INTERNAL_QA" / "rendered_pages_r407"
    qa_root.mkdir(parents=True, exist_ok=True)

    bd_kwargs = {}
    render_package_readme(pkg, headline, [],
                          str(pdir / "00_PACKAGE_README.pdf"))
    render_exec_brief(pkg, headline, comm, ecos, loops,
                      str(pdir / "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf"))
    render_engineering_dossier(
        pkg, headline, eq_reg, road, comm, ecos, loops,
        mech_pngs[pkg.pkg_id], exp_png,
        str(pdir / "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"))
    render_buyer_card(pkg, headline, comm, ecos, loops,
                      str(pdir / "03_BUYER_DECISION_CARD.pdf"))
    render_evidence_summary(pkg, headline, loops,
                            str(pdir / "04_EVIDENCE_SUMMARY.pdf"))
    render_transfer_manifest(pkg, headline, comm,
                             str(pdir / "05_TRANSFER_MANIFEST.pdf"))

    # fail-closed QA gates (the same gates as the V5 build)
    pkg_qa = verify_package(str(pdir), png_dir=str(qa_root / folder))
    streams = []
    for f in sorted(os.listdir(pdir)):
        if f.endswith(".pdf"):
            streams.extend(pdf_haystacks(str(pdir / f)))
    exp_ = build_content_expectations(pkg, headline, road)
    ok, failures = content_completeness(exp_, streams)
    if not ok:
        raise RuntimeError(
            f"R407 content completeness FAILED for {pkg.pkg_id}: "
            + "; ".join(f"{f['field']}" for f in failures[:8]))

    # machine-readable layer
    for fn in TARGETS[pkg.pkg_id]["regen_json"]:
        fp = pdir / fn
        old = fp.read_bytes()
        if fn == "EQUATION_REGISTRY.json":
            obj = eq_reg
        elif fn == "UNKNOWN_ROADMAP.json":
            obj = road
        else:
            obj = ecos
        _write_json(fp, obj)
        diffs.append(_diff_report(fp, old, fp.read_bytes()))

    # V3 addendum (verbatim engine input) + mutation certificate
    (pdir / "V3_MUTATION_ADDENDUM.json").write_bytes(v3_bytes)
    diffs.append("V3_MUTATION_ADDENDUM.json: NEW (verbatim engine input)")
    cert = {
        "certificate_type": "PACKAGE_MUTATION_CERTIFICATE",
        "mutation_id": f"MUTCERT-{pkg.pkg_id}-V3",
        "package_id": pkg.pkg_id,
        "folder": folder,
        "v2_to_v3": True,
        "before_manifest_hash": None,  # filled after manifest rebuild
        "v3_addendum_hash": hashlib.sha256(v3_bytes).hexdigest(),
        "changed_fields_count": len(json.loads(v3_bytes).get(
            "operations", [])),
        "reason": "CEO R394 semantics directive: align the shipped buyer "
                  "surface to the V3-corrected engine canonical "
                  "(MECHANISM_CLAIM_WITHOUT_GEOMETRIC_IMPLEMENTATION "
                  "release gate); remove unsupported embodiment claims; "
                  "no claim is added (Art. XXVIII).",
        "evidence_basis": f"premium_package_factory/input/v3_corrections/"
                          f"{pkg.pkg_id}_V3_CORRECTIONS.json",
        "authorization": "R407 P0 / B1 re-ship (roadmap "
                         "R407/ROADMAP_9_10_BENCHMARKS.md Part C P0)",
    }
    cert_path = pdir / f"PACKAGE_MUTATION_CERTIFICATE_{pkg.pkg_id}_V3.json"
    _write_json(cert_path, cert)
    diffs.append(f"PACKAGE_MUTATION_CERTIFICATE_{pkg.pkg_id}_V3.json: NEW")

    # PACKAGE_MANIFEST: file list + hashes + version 3.0
    pm_path = pdir / "PACKAGE_MANIFEST.json"
    pm = json.loads(pm_path.read_text(encoding="utf-8"))
    files = []
    for dp, _dn, fns in os.walk(pdir):
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), pdir).replace(
                os.sep, "/")
            if rel in ("PACKAGE_MANIFEST.json",
                       f"PACKAGE_MUTATION_CERTIFICATE_{pkg.pkg_id}_V3.json"):
                continue  # manifest never lists itself; cert handled below
            files.append({"file": rel, "sha256": sha256_file(
                os.path.join(dp, fn))})
    # the V2 certificate IS listed in the shipped manifest (V2 precedent)
    files.append({"file": f"PACKAGE_MUTATION_CERTIFICATE_{pkg.pkg_id}"
                         f"_V3.json",
                  "sha256": sha256_file(str(cert_path))})
    files.sort(key=lambda x: x["file"])
    old_pm_bytes = pm_path.read_bytes()
    pm["files"] = files
    pm["package_version"] = "3.0"
    pm["version_note"] = ("V3: CEO R394 semantics corrections re-shipped "
                          "(R407 P0/B1); V2 mutation history preserved "
                          "in-package.")
    _write_json(pm_path, pm)
    diffs.append(_diff_report(pm_path, old_pm_bytes, pm_path.read_bytes()))

    # package ZIP (deterministic epoch entries)
    zpath = portfolio_root / "DOWNLOAD" / f"{folder}.zip"
    old_zip_hash = sha256_file(zpath) if zpath.exists() else None
    with zipfile.ZipFile(zpath, "w") as zf:
        for dp, _dn, fns in os.walk(pdir):
            for fn in sorted(fns):
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, pdir)
                _zip_add(zf, full, rel)
    diffs.append(f"{folder}.zip: rebuilt "
                 f"({'unchanged' if sha256_file(zpath) == old_zip_hash
                 else 'CHANGED'})")

    report["packages"][pkg.pkg_id] = {
        "folder": folder, "changes": diffs, "qa": "PASS",
        "content_expectations": len(exp_)}

    # second pass: fill the certificate's before/after manifest hashes
    cert["after_manifest_hash"] = sha256_file(str(pm_path))
    _write_json(cert_path, cert)
    # manifest hash changed? re-list to keep ZIP byte-consistent
    for f in pm["files"]:
        if f["file"] == f"PACKAGE_MUTATION_CERTIFICATE_{pkg.pkg_id}_V3.json":
            f["sha256"] = sha256_file(str(cert_path))
    _write_json(pm_path, pm)
    with zipfile.ZipFile(zpath, "w") as zf:
        for dp, _dn, fns in os.walk(pdir):
            for fn in sorted(fns):
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, pdir)
                _zip_add(zf, full, rel)
    return


def catchup_registry(pkg, headline, portfolio_root, apply, report):
    """R407 P0 buyer-surface catch-up for the non-V3 packages: regenerate
    the files whose derivations moved with the R394/R395 engine
    evolution — EQUATION_REGISTRY.json (r372/r374 validation blocks),
    UNKNOWN_ROADMAP.json, VALIDATION_ECONOMICS.json (the kill-condition
    decisive-WP derivation) — and re-render the six buyer PDFs, with a
    byte-diff disclosure for every changed file. MODEL/ layers are
    untouched (CAD unchanged)."""
    import tempfile
    folder = pkg.folder
    pdir = portfolio_root / "DOWNLOAD" / folder
    changes = {}

    eq_reg = build_equation_registry(pkg)
    eq_reg["r372_validation"] = validate_registry(eq_reg, pkg)
    attach_r374_status(eq_reg, pkg)
    road = build_unknown_roadmap(pkg)
    ecos = build_validation_economics(pkg, headline.get("kill_if", ""))

    if not apply:
        for name, obj in (("EQUATION_REGISTRY.json", eq_reg),
                          ("UNKNOWN_ROADMAP.json", road),
                          ("VALIDATION_ECONOMICS.json", ecos)):
            fp = pdir / name
            new = (json.dumps(obj, indent=1, ensure_ascii=False)
                   + "\n").encode()
            old = fp.read_bytes()
            if new != old:
                changes[name] = _diff_report(fp, old, new)
        changes["buyer_pdfs"] = "re-render (R394/R395 catch-up)"
        report.setdefault("registry_catchup", {})[pkg.pkg_id] = {
            "folder": folder, "planned": changes}
        return

    styles = get_styles()
    init_styles(styles)
    _init_dossier_styles(styles)
    qa_root = portfolio_root / "INTERNAL_QA" / "rendered_pages_r407"
    qa_root.mkdir(parents=True, exist_ok=True)
    comm = build_commercial_evidence(pkg)
    loops = build_loop_state(pkg)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    mech_pngs = build_all_mechanism_diagrams(str(WORK_DIR / "mechanism"))
    exp_dir = WORK_DIR / "experiment"
    exp_dir.mkdir(parents=True, exist_ok=True)
    spec = experiment_diagram_spec(pkg, headline)
    exp_png = build_experiment_diagram(
        pkg, headline, str(exp_dir / f"{pkg.num}_experiment_setup.png"),
        spec=spec)

    # snapshot old bytes for the diff report
    old_bytes = {f: (pdir / f).read_bytes() for f in (
        "00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
        "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
        "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
        "05_TRANSFER_MANIFEST.pdf", "EQUATION_REGISTRY.json",
        "UNKNOWN_ROADMAP.json", "VALIDATION_ECONOMICS.json")
        if (pdir / f).exists()}

    render_package_readme(pkg, headline, [],
                          str(pdir / "00_PACKAGE_README.pdf"))
    render_exec_brief(pkg, headline, comm, ecos, loops,
                      str(pdir / "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf"))
    render_engineering_dossier(
        pkg, headline, eq_reg, road, comm, ecos, loops,
        mech_pngs[pkg.pkg_id], exp_png,
        str(pdir / "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"))
    render_buyer_card(pkg, headline, comm, ecos, loops,
                      str(pdir / "03_BUYER_DECISION_CARD.pdf"))
    render_evidence_summary(pkg, headline, loops,
                            str(pdir / "04_EVIDENCE_SUMMARY.pdf"))
    render_transfer_manifest(pkg, headline, comm,
                             str(pdir / "05_TRANSFER_MANIFEST.pdf"))
    _write_json(pdir / "EQUATION_REGISTRY.json", eq_reg)
    _write_json(pdir / "UNKNOWN_ROADMAP.json", road)
    _write_json(pdir / "VALIDATION_ECONOMICS.json", ecos)

    # fail-closed QA gates (same as the V5 build)
    verify_package(str(pdir), png_dir=str(qa_root / folder))
    streams = []
    for f in sorted(os.listdir(pdir)):
        if f.endswith(".pdf"):
            streams.extend(pdf_haystacks(str(pdir / f)))
    exp_ = build_content_expectations(pkg, headline, road)
    ok, failures = content_completeness(exp_, streams)
    if not ok:
        raise RuntimeError(
            f"R407 content completeness FAILED for {pkg.pkg_id}: "
            + "; ".join(f"{f['field']}" for f in failures[:8]))

    for f, old in old_bytes.items():
        new = (pdir / f).read_bytes()
        if new != old:
            changes[f] = _diff_report(pdir / f, old, new)

    # manifest + ZIP
    pm_path = pdir / "PACKAGE_MANIFEST.json"
    pm = json.loads(pm_path.read_text(encoding="utf-8"))
    for entry in pm.get("files", []):
        fp = pdir / entry["file"]
        if fp.exists():
            entry["sha256"] = sha256_file(str(fp))
    _write_json(pm_path, pm)
    zpath = portfolio_root / "DOWNLOAD" / f"{folder}.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for dp, _dn, fns in os.walk(pdir):
            for fn in sorted(fns):
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, pdir)
                _zip_add(zf, full, rel)
    report.setdefault("registry_catchup", {})[pkg.pkg_id] = {
        "folder": folder, "changes": changes,
        "qa": "PASS", "content_expectations": len(exp_)}


def rebuild_identity_registry(portfolio_root, apply, report):
    """D1 — rebuild PORTFOLIO_IDENTITY_REGISTRY.json from the actual
    tree (the shipped registry predates the R385/R387 regeneration;
    every hash is stale)."""
    from premium_package_factory.r371.identity import PACKAGE_MAP
    reg_path = portfolio_root / "PORTFOLIO_IDENTITY_REGISTRY.json"
    old = json.loads(reg_path.read_text(encoding="utf-8"))
    # statuses: V3 for the three re-shipped packages; keep the prior
    # status for the rest (V2 where a V2 addendum ships, else RELEASED)
    rows = []
    for row in PACKAGE_MAP:
        folder = None
        for entry in old["packages"]:
            if entry["historical_package_id"] == row["pkg_id"]:
                folder = entry["folder_name"]
                break
        pdir = portfolio_root / "DOWNLOAD" / folder
        status = entry["status"]
        if row["pkg_id"] in TARGETS:
            status = "V3"
        rows.append({
            "portfolio_number": entry["portfolio_number"],
            "historical_package_id": row["pkg_id"],
            "technology_name": entry["technology_name"],
            "folder_name": folder,
            "dossier_hash": sha256_file(
                str(pdir / "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf")),
            "package_zip_hash": sha256_file(
                str(portfolio_root / "DOWNLOAD" / f"{folder}.zip")),
            "manifest_hash": sha256_file(str(pdir / "PACKAGE_MANIFEST.json")),
            "status": status,
        })
    new_reg = {
        "registry": "PORTFOLIO_IDENTITY_REGISTRY",
        "version": "2.1",
        "policy": old.get("policy", ""),
        "regenerated_by": "scripts/r407_b1_reship.py (R407 P0 / D1 fix)",
        "regeneration_basis": "hashes recomputed from the actual shipped "
                              "tree at the R407 P0 re-ship; statuses: V3 "
                              "for the three re-shipped packages, V2 "
                              "where a V2 addendum ships, RELEASED "
                              "otherwise",
        "packages": rows,
    }
    if apply:
        reg_path.write_text(
            json.dumps(new_reg, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
    stale_before = sum(
        1 for old_e, new_e in zip(old["packages"], rows)
        if old_e["package_zip_hash"] != new_e["package_zip_hash"]
        or old_e["manifest_hash"] != new_e["manifest_hash"]
        or old_e["dossier_hash"] != new_e["dossier_hash"])
    report["identity_registry"] = {
        "stale_entries_before": stale_before,
        "written": apply,
    }


def fix_latest_release(portfolio_root, apply, report):
    """D2 — correct RELEASE/LATEST_RELEASE.json:
    (a) the portfolio_release_commit hash is WRONG (right first-8, wrong
        rest — a corrupted value vs the tagged release commit);
    (b) chain_verification claims 26/26 while the committed authority
        certificate records 25 checks;
    (c) note the R388-era re-verification of the same release."""
    import subprocess
    lr_path = portfolio_root / "RELEASE" / "LATEST_RELEASE.json"
    lr = json.loads(lr_path.read_text(encoding="utf-8"))
    problems = []
    # the true release commit: the tag target on this clone
    true_commit = subprocess.run(
        ["git", "-C", str(portfolio_root), "rev-parse",
         f"{lr.get('git_tag', 'v1.0.0-3D-edition')}^{{commit}}"],
        capture_output=True, text=True).stdout.strip()
    if lr.get("portfolio_release_commit") and \
            lr["portfolio_release_commit"] != true_commit:
        problems.append(f"portfolio_release_commit: "
                        f"{lr['portfolio_release_commit'][:16]}... -> "
                        f"{true_commit[:16]}...")
        lr["portfolio_release_commit"] = true_commit
    if "26/26" in str(lr.get("chain_verification", "")):
        problems.append("chain_verification 26/26 -> 25/25 (the committed "
                        "certificate RELEASE_CHAIN_VERIFICATION_R387-"
                        "3D-QUALITY-EDITION.json records 25 checks; "
                        "Art. XXIV: the artifact outranks the commit-"
                        "message claim)")
        lr["chain_verification"] = (
            "25/25 PASS from clean clones of both remotes (certificate in "
            "the engine repository: RELEASE_CHAIN/"
            "RELEASE_CHAIN_VERIFICATION_R387-3D-QUALITY-EDITION.json; "
            "re-verified 25/25 at the R388 distilled tree — "
            "RELEASE_CHAIN_VERIFICATION_R388_DISTILLED_TREE.json)")
    # master zip hash vs the canonical manifest (buyer truth)
    manifest = json.loads((portfolio_root / "CANONICAL_RELEASE_MANIFEST.json")
                          .read_text(encoding="utf-8"))
    mz = manifest.get("master_zip", {})
    if lr.get("master_zip_sha256") != mz.get("sha256"):
        problems.append("master_zip_sha256 aligned to the canonical "
                        "manifest")
        lr["master_zip_sha256"] = mz.get("sha256")
    report["latest_release"] = {"corrections": problems, "written": apply}
    if apply:
        lr_path.write_text(
            json.dumps(lr, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")


def regenerate_distribution_certificate(portfolio_root, apply, report):
    """C1 — RELEASE/BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json is an
    R372-era artifact: NN_folder_name template placeholders + the stale
    R370-era master-ZIP hash. Regenerate from the actual tree."""
    cert_path = portfolio_root / "RELEASE" / \
        "BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json"
    old = json.loads(cert_path.read_text(encoding="utf-8"))
    reg = json.loads((portfolio_root / "PORTFOLIO_IDENTITY_REGISTRY.json")
                     .read_text(encoding="utf-8")) \
        if not apply else None
    # after identity rebuild in apply mode, re-read from disk
    reg = json.loads((portfolio_root / "PORTFOLIO_IDENTITY_REGISTRY.json")
                     .read_text(encoding="utf-8"))
    manifest = json.loads((portfolio_root / "CANONICAL_RELEASE_MANIFEST.json")
                          .read_text(encoding="utf-8"))
    packages = []
    for entry in reg["packages"]:
        folder = entry["folder_name"]
        pdir = portfolio_root / "DOWNLOAD" / folder
        file_hashes = {}
        for dp, _dn, fns in os.walk(pdir):
            for fn in fns:
                rel = os.path.relpath(os.path.join(dp, fn), pdir).replace(
                    os.sep, "/")
                file_hashes[rel] = sha256_file(os.path.join(dp, fn))
        packages.append({
            "portfolio_number": entry["portfolio_number"],
            "package_id": entry["historical_package_id"],
            "folder_name": folder,
            "version": "3.0" if entry["status"] == "V3" else (
                "2.0" if entry["status"] == "V2" else "1.0"),
            "folder_hash": sha256_tree(pdir),
            "zip_hash": sha256_file(
                str(portfolio_root / "DOWNLOAD" / f"{folder}.zip")),
            "file_count": len(file_hashes),
            "equivalence_verified": "PENDING (r407 re-ship; verified by "
                                    "the r373 audit at the release gate)",
        })
    new_cert = {
        "certificate_type": "BUYER_DISTRIBUTION_RELEASE_CERTIFICATE",
        "version": "2.0",
        "regenerated_by": "scripts/r407_b1_reship.py (R407 P0 / C1 fix)",
        "supersedes": "the R372-era certificate (commit 630138f) whose "
                      "distribution_structure carried NN_folder_name "
                      "template placeholders and whose master_zip_hash "
                      "was the stale R370-era value",
        "package_count": len(packages),
        "master_zip_hash": manifest.get("master_zip", {}).get("sha256"),
        "master_zip_path": manifest.get("master_zip", {}).get("path"),
        "canonical_authority": "CANONICAL_RELEASE_MANIFEST.json "
                               "(Art. XXXIX — the buyer-distribution "
                               "repository is the final authority; this "
                               "certificate is an internal RELEASE/ "
                               "record, not buyer surface)",
        "distribution_structure": {
            "individual_zips": "DOWNLOAD/<folder_name>.zip (15 packages)",
            "individual_folders": "DOWNLOAD/<folder_name>/ (15 packages)",
            "full_dossiers": "DOWNLOAD/<folder_name>/ (the source for the "
                             "package ZIP; MODEL/ 3D layer included)",
            "master_zip": str(manifest.get("master_zip", {}).get("path")),
        },
        "packages": packages,
    }
    if apply:
        cert_path.write_text(
            json.dumps(new_cert, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
    report["distribution_certificate"] = {
        "placeholder_paths_before": 3,
        "stale_master_hash_before": old.get("master_zip_hash", "")[:16],
        "written": apply,
    }


def rebuild_master_zip(portfolio_root, apply, report):
    """Rebuild the master ZIP from the actual tree: the 8 ROOT_BUYER_FILES
    + the 15 package ZIPs (the r386 chain Z3 contract — the master ZIP
    member set must equal the manifest-defined buyer surface)."""
    from scripts.r386_release_chain import ROOT_BUYER_FILES
    mz_name = "technology-transfer-portfolio-15.zip"
    mz_path = portfolio_root / "DOWNLOAD" / mz_name
    with zipfile.ZipFile(mz_path, "w") as zf:
        for fn in ROOT_BUYER_FILES:
            _zip_add(zf, str(portfolio_root / fn), fn)
        for z in sorted((portfolio_root / "DOWNLOAD").glob("*.zip")):
            if z.name == mz_name:
                continue
            _zip_add(zf, str(z), f"DOWNLOAD/{z.name}")
    report["master_zip"] = {
        "path": str(mz_path.relative_to(portfolio_root)),
        "sha256": sha256_file(str(mz_path)) if apply else "not-built",
        "written": apply,
    }


def rebuild_release_content_manifest(portfolio_root, apply, report):
    """RELEASE_CONTENT_MANIFEST.json from the actual filesystem."""
    rcm_path = portfolio_root / "RELEASE_CONTENT_MANIFEST.json"
    old_hash = sha256_file(str(rcm_path)) if rcm_path.exists() else None
    entries = []
    dl = portfolio_root / "DOWNLOAD"
    for folder in sorted(p.name for p in dl.iterdir() if p.is_dir()):
        for dp, _dn, fns in os.walk(dl / folder):
            for fn in sorted(fns):
                rel = os.path.relpath(os.path.join(dp, fn), dl).replace(
                    os.sep, "/")
                entries.append({"file": rel,
                                "sha256": sha256_file(
                                    os.path.join(dp, fn))})
    entries.sort(key=lambda x: x["file"])
    mz = portfolio_root / "DOWNLOAD" / "technology-transfer-portfolio-15.zip"
    new = {
        "manifest_type": "RELEASE_CONTENT_MANIFEST",
        "regenerated_by": "scripts/r407_b1_reship.py (R407 P0)",
        "note": "content census of the buyer distribution tree; the "
                "authoritative pin set is CANONICAL_RELEASE_MANIFEST.json",
        "file_count": len(entries),
        "master_zip": {"path": str(mz.relative_to(portfolio_root)),
                       "sha256": sha256_file(str(mz))},
        "files": entries,
    }
    if apply:
        rcm_path.write_text(
            json.dumps(new, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
    report["release_content_manifest"] = {
        "files": len(entries), "written": apply}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portfolio-root", required=True)
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: verify-only)")
    args = ap.parse_args()
    portfolio_root = Path(args.portfolio_root).resolve()
    if not (portfolio_root / "DOWNLOAD").exists():
        raise SystemExit(f"not a portfolio clone: {portfolio_root}")

    report = {"artifact": "R407_B1_RESHIP", "mode":
              "APPLY" if args.apply else "VERIFY_ONLY",
              "packages": {}}

    # 0. pre-ship scan: MODEL geometry must not reference removed
    #    embodiments (else the geometry assumption is wrong)
    blockers, disclosed = preship_scan(portfolio_root)
    report["preship_scan"] = {"blockers": blockers,
                              "orphaned_embodiment_metadata": disclosed}
    if blockers:
        print("PRE-SHIP SCAN FAILED (MODEL geometry references a removed "
              "embodiment — do NOT re-ship without a CAD decision):")
        for p in blockers:
            print("  -", p)
        if args.apply:
            raise SystemExit(1)
    else:
        print(f"[scan] MODEL geometry layers clean; "
              f"{len(disclosed)} orphaned-embodiment METADATA rows "
              f"disclosed (P1 semantics queue)")

    packages = load_all_packages()
    headlines = {r["package_id"]: r for r in json.load(
        open(INPUT_DIR / "headlines_r371.json",
             encoding="utf-8"))["packages"]}
    by_id = {p.pkg_id: p for p in packages}

    for pid in TARGETS:
        print(f"[{pid}] mode={'APPLY' if args.apply else 'VERIFY'}")
        rebuild_package(by_id[pid], headlines[pid], portfolio_root,
                        args.apply, report)

    if REGISTRY_CATCHUP_ALL:
        print("[registry-catchup] non-V3 packages "
              f"mode={'APPLY' if args.apply else 'VERIFY'}")
        for p in packages:
            if p.pkg_id in TARGETS:
                continue
            catchup_registry(p, headlines[p.pkg_id], portfolio_root,
                             args.apply, report)

    rebuild_identity_registry(portfolio_root, args.apply, report)
    fix_latest_release(portfolio_root, args.apply, report)
    if args.apply:
        # order matters: master ZIP first (the content manifest and the
        # distribution certificate pin its hash), then the content
        # manifest, then the certificate from the final tree state.
        # NOTE: the CANONICAL_RELEASE_MANIFEST.json regeneration and the
        # RELEASE/LATEST_RELEASE.json pointer to the NEW release happen
        # in the follow-up r386 chain phase (portfolio commit FIRST,
        # then manifest from the pushed state — Art. XXXIX protocol
        # order; this script only fixes the D2 defects in the pointer).
        rebuild_master_zip(portfolio_root, True, report)
        rebuild_release_content_manifest(portfolio_root, True, report)
        regenerate_distribution_certificate(portfolio_root, True, report)
    else:
        report["skipped_in_verify_mode"] = [
            "distribution certificate", "master ZIP",
            "release content manifest"]

    out = ENGINE_ROOT / "R407" / "B1_RESHIP_REPORT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"[report] {out}")
    if not args.apply:
        print("VERIFY-ONLY: no files were written. Re-run with --apply.")


if __name__ == "__main__":
    main()

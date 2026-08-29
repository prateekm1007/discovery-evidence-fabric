"""
build_v5.py — R371 portfolio V5 build orchestrator (entry point).

Build order (each step fails closed):
  1. Load canonical packages + V2-mutation-aware headlines
  2. Derive per-package artifacts (commercial, equations, unknown roadmap,
     economics, loop state)
  3. Generate the two technical visuals per package (mechanism + experiment)
  4. Render the six buyer PDFs per package + machine-readable JSON layer
  5. Build the 15 package ZIPs from the folders
  6. Render portfolio-level documents (index/ranking, master, release report)
  7. Build PORTFOLIO_IDENTITY_REGISTRY.json from the actual artifacts
  8. Build RELEASE_CONTENT_MANIFEST.json from the actual filesystem,
     generate README.md from it, build the master ZIP from it
  9. Preserve history: move R370 release-process certificates to
     RELEASE/history_r370/ (never deleted — Constitution Art. XI)

Usage: python -m premium_package_factory.r371.build_v5 [--portfolio-root PATH]
"""

import argparse
import json
import os
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from premium_package_factory.r371.builder import get_styles, sha256_file, _now
from premium_package_factory.r371.builder_documents import init_styles
from premium_package_factory.r371.builder_dossier import init_styles as _init_dossier_styles
from premium_package_factory.r371 import builder_documents as bd
from premium_package_factory.r371 import builder_dossier as bdd
from premium_package_factory.r371 import builder_portfolio as bp
from premium_package_factory.r371.canonical_source import load_all_packages
from premium_package_factory.r371.commercial import build_commercial_evidence
from premium_package_factory.r371.economics import build_validation_economics
from premium_package_factory.r371.equations import build_equation_registry
from premium_package_factory.r371.experiment_diagram import build_experiment_diagram
from premium_package_factory.r371.identity import build_registry, write_registry
from premium_package_factory.r371.loopstate import build_loop_state, portfolio_loop_summary
from premium_package_factory.r371.mechanism_diagram import build_all_mechanism_diagrams
from premium_package_factory.r371.ranking import build_ranking
from premium_package_factory.r371.unknowns import build_unknown_roadmap

FACTORY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE_ROOT = os.path.dirname(FACTORY_ROOT)
INPUT_DIR = os.path.join(FACTORY_ROOT, "input")

R370_LEGACY_ROOT_FILES = [
    "AI_LEARNING_TO_PACKAGE_CERTIFICATE.json",
    "BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json",
    "DISTRIBUTION_CANONICAL_MANIFEST.json",
    "FINAL_BUYER_RELEASE_ID.json",
    "FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json",
    "FINAL_RELEASE_ANCHOR_REPORT.json",
    "FINAL_RELEASE_OBJECT.json",
    "SOURCE_RELEASE_MANIFEST.json",
    "RELEASE_INTEGRITY_REPORT.md",
]

PACKAGE_JSON_ROLES = {
    "PACKAGE_MANIFEST.json": "identity + file hashes",
    "ENGINEERING_TRACEABILITY.json": "design-input/output traceability chains",
    "MATURITY_BASIS.json": "maturity basis evidence IDs",
    "COMMERCIAL_EVIDENCE.json": "market/competitor/precedent/IP (provenance-disciplined)",
    "EQUATION_REGISTRY.json": "canonical equations + typeset registry",
    "UNKNOWN_ROADMAP.json": "classified unknowns with resolution actions",
    "VALIDATION_ECONOMICS.json": "cost NOT_ESTABLISHED + time ranges with basis",
    "LOOP_STATE.json": "loop verification state + event queues",
    "V2_MUTATION_ADDENDUM.json": "V1->V2 mutation trail (external-evidence driven)",
}


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def build(portfolio_root, work_dir=None):
    work = work_dir or os.path.join(ENGINE_ROOT, "premium_package_factory",
                                    "output", "r371_v5_build")
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.join(portfolio_root, "DOWNLOAD"), exist_ok=True)

    styles = get_styles()
    init_styles(styles)
    _init_dossier_styles(styles)

    # 1-2. canonical + derived artifacts ------------------------------------
    print("[R371] loading canonical packages ...")
    packages = load_all_packages()
    headlines = {r["package_id"]: r for r in json.load(
        open(os.path.join(INPUT_DIR, "headlines_r371.json"), encoding="utf-8"))["packages"]}

    comm = {p.pkg_id: build_commercial_evidence(p) for p in packages}
    eqs = {p.pkg_id: build_equation_registry(p) for p in packages}
    roads = {p.pkg_id: build_unknown_roadmap(p) for p in packages}
    ecos = {p.pkg_id: build_validation_economics(p) for p in packages}
    loops = {p.pkg_id: build_loop_state(p) for p in packages}
    loop_summary = portfolio_loop_summary(packages)
    ranking = build_ranking(packages, headlines, roads)

    # 3. visuals --------------------------------------------------------------
    print("[R371] generating technical visuals ...")
    mech_dir = os.path.join(work, "mechanism")
    mech_pngs = build_all_mechanism_diagrams(mech_dir)
    exp_dir = os.path.join(work, "experiment")
    os.makedirs(exp_dir, exist_ok=True)
    exp_pngs = {}
    for p in packages:
        exp_pngs[p.pkg_id] = build_experiment_diagram(
            p, headlines[p.pkg_id],
            os.path.join(exp_dir, f"{p.num}_experiment_setup.png"))

    # 4. per-package render -----------------------------------------------------
    print("[R371] rendering 15 packages ...")
    for p in packages:
        h = headlines[p.pkg_id]
        folder = p.folder
        pdir = os.path.join(portfolio_root, "DOWNLOAD", folder)
        if os.path.isdir(pdir):
            shutil.rmtree(pdir)
        os.makedirs(pdir)

        bd.render_package_readme(p, h, [], os.path.join(pdir, "00_PACKAGE_README.pdf"))
        bd.render_exec_brief(p, h, comm[p.pkg_id], ecos[p.pkg_id], loops[p.pkg_id],
                             os.path.join(pdir, "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf"))
        bdd.render_engineering_dossier(
            p, h, eqs[p.pkg_id], roads[p.pkg_id], comm[p.pkg_id],
            ecos[p.pkg_id], loops[p.pkg_id], mech_pngs[p.pkg_id],
            exp_pngs[p.pkg_id],
            os.path.join(pdir, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"))
        bd.render_buyer_card(p, h, comm[p.pkg_id], ecos[p.pkg_id], loops[p.pkg_id],
                             os.path.join(pdir, "03_BUYER_DECISION_CARD.pdf"))
        bd.render_evidence_summary(p, h, loops[p.pkg_id],
                                   os.path.join(pdir, "04_EVIDENCE_SUMMARY.pdf"))
        bd.render_transfer_manifest(p, h, comm[p.pkg_id],
                                    os.path.join(pdir, "05_TRANSFER_MANIFEST.pdf"))

        # machine-readable layer
        legacy_num = os.path.join(INPUT_DIR, "legacy_json", p.num)
        for fn in ("ENGINEERING_TRACEABILITY.json", "MATURITY_BASIS.json"):
            src = os.path.join(legacy_num, fn)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(pdir, fn))
        _write_json(os.path.join(pdir, "COMMERCIAL_EVIDENCE.json"), comm[p.pkg_id])
        _write_json(os.path.join(pdir, "EQUATION_REGISTRY.json"), eqs[p.pkg_id])
        _write_json(os.path.join(pdir, "UNKNOWN_ROADMAP.json"), roads[p.pkg_id])
        _write_json(os.path.join(pdir, "VALIDATION_ECONOMICS.json"), ecos[p.pkg_id])
        _write_json(os.path.join(pdir, "LOOP_STATE.json"), loops[p.pkg_id])
        # V2 mutation trail (preserved verbatim from the engine input
        # snapshot — never read from the live portfolio tree, which this
        # build wipes and rebuilds)
        v2src = os.path.join(INPUT_DIR, "v2_mutations",
                             f"V2_MUTATION_ADDENDUM_{p.pkg_id}.json")
        if os.path.exists(v2src):
            shutil.copy2(v2src, os.path.join(pdir, "V2_MUTATION_ADDENDUM.json"))
            cert_src = os.path.join(INPUT_DIR, "v2_mutations")
            for fcert in os.listdir(cert_src):
                if (fcert.startswith("PACKAGE_MUTATION_CERTIFICATE")
                        and f"_V2.json" in fcert
                        and p.pkg_id in fcert):
                    shutil.copy2(os.path.join(cert_src, fcert),
                                 os.path.join(pdir, fcert))

        # package manifest (identity-linked) — files hashed from disk
        files = []
        for f in sorted(os.listdir(pdir)):
            if f == "PACKAGE_MANIFEST.json":
                continue
            files.append({
                "file": f,
                "role": PACKAGE_JSON_ROLES.get(f, "buyer document"),
                "sha256": sha256_file(os.path.join(pdir, f)),
            })
        pm = {
            "portfolio_number": p.num,
            "package_id": p.pkg_id,
            "technology_name": h["technology_name"],
            "package_version": p.version,
            "technology_maturity": "ENGINEERING_DEFINITION",
            "dossier_maturity": "COMPLETE_FOR_CURRENT_STAGE",
            "transfer_posture": "SPONSORED_VALIDATION",
            "loop_verification_state": p.loop_state,
            "has_v2_addendum": bool(p.addendum),
            "identity_policy": (
                "Portfolio number and historical package ID are bound in "
                "PORTFOLIO_IDENTITY_REGISTRY.json and never renumbered."),
            "files": files,
            "external_evidence_count": len(p.external_precedent),
            "engineering_artifact_count": len(p.build_plan),
        }
        _write_json(os.path.join(pdir, "PACKAGE_MANIFEST.json"), pm)

        # 5. package zip built from the folder (byte-verified by acceptance)
        zpath = os.path.join(portfolio_root, "DOWNLOAD", f"{folder}.zip")
        if os.path.exists(zpath):
            os.remove(zpath)
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(os.listdir(pdir)):
                zf.write(os.path.join(pdir, f), f)
        print(f"   {p.num} {p.pkg_id} ({p.version}) done")

    # README of each package needs the final file list; rebuild readmes now
    for p in packages:
        h = headlines[p.pkg_id]
        pdir = os.path.join(portfolio_root, "DOWNLOAD", p.folder)
        pm = json.load(open(os.path.join(pdir, "PACKAGE_MANIFEST.json"),
                            encoding="utf-8"))
        bd.render_package_readme(p, h, pm["files"],
                                 os.path.join(pdir, "00_PACKAGE_README.pdf"))
        # update manifest hash for the re-rendered readme
        for f in pm["files"]:
            if f["file"] == "00_PACKAGE_README.pdf":
                f["sha256"] = sha256_file(os.path.join(pdir, "00_PACKAGE_README.pdf"))
        _write_json(os.path.join(pdir, "PACKAGE_MANIFEST.json"), pm)
        # rebuild zip with final readme
        zpath = os.path.join(portfolio_root, "DOWNLOAD", f"{p.folder}.zip")
        os.remove(zpath)
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(os.listdir(pdir)):
                zf.write(os.path.join(pdir, f), f)

    # 6. portfolio-level documents -----------------------------------------------
    print("[R371] rendering portfolio documents ...")
    bp.render_portfolio_index(
        ranking, loop_summary,
        os.path.join(portfolio_root, "PORTFOLIO_INDEX.pdf"))
    bp.render_master_portfolio(
        packages, headlines, ranking,
        os.path.join(portfolio_root, "00_PORTFOLIO_15_TECHNOLOGIES.pdf"))
    # PORTFOLIO_MANIFEST.json (canonical maturity source)
    manifest = {
        "portfolio_version": "2.0", "generated_at": _now(), "package_count": 15,
        "identity_registry": "PORTFOLIO_IDENTITY_REGISTRY.json",
        "ranking": "PORTFOLIO_RANKING.json",
        "packages": [
            {
                "portfolio_number": p.num, "package_id": p.pkg_id,
                "technology_name": headlines[p.pkg_id]["technology_name"],
                "folder_name": p.folder,
                "package_version": p.version,
                "technology_maturity": "ENGINEERING_DEFINITION",
                "dossier_maturity": "COMPLETE_FOR_CURRENT_STAGE",
                "transfer_posture": "SPONSORED_VALIDATION",
                "loop_verification_state": p.loop_state,
                "kill_condition": headlines[p.pkg_id]["kill_if"],
                "rank": next(r["rank"] for r in ranking["rows"]
                             if r["package_id"] == p.pkg_id),
            }
            for p in packages
        ],
    }
    _write_json(os.path.join(portfolio_root, "PORTFOLIO_MANIFEST.json"), manifest)
    _write_json(os.path.join(portfolio_root, "PORTFOLIO_RANKING.json"), ranking)

    # 7. identity registry from the actual artifacts -------------------------------
    print("[R371] building identity registry ...")
    registry = build_registry(portfolio_root)
    for row in registry["packages"]:
        pkg = next(p for p in packages if p.pkg_id == row["historical_package_id"])
        row["technology_name"] = headlines[pkg.pkg_id]["technology_name"]
    write_registry(portfolio_root, registry)

    # 8. release content manifest -> README -> master zip (two-pass, Phase 2)
    print("[R371] building release content manifest, README, master zip ...")
    # release report rendered FIRST so its hash is final before any manifest
    # pass (acceptance-gate results live in INTERNAL_QA/ and RELEASE/, not here)
    bp.render_release_report(
        ranking, loop_summary, {},
        os.path.join(portfolio_root, "PORTFOLIO_RELEASE_REPORT.pdf"))
    # pass 1: manifest without README -> GENERATE README from it
    rc_manifest = bp.build_release_content_manifest(portfolio_root,
                                                    include_readme=False)
    bp.generate_readme(rc_manifest, loop_summary,
                       os.path.join(portfolio_root, "README.md"))
    # pass 2: full manifest (README hash final) -> write -> master zip FROM it
    rc_manifest = bp.build_release_content_manifest(portfolio_root,
                                                    include_readme=True)
    _write_json(os.path.join(portfolio_root, "RELEASE_CONTENT_MANIFEST.json"),
                rc_manifest)
    master_zip = os.path.join(portfolio_root, "DOWNLOAD",
                              "technology-transfer-portfolio-15.zip")
    if os.path.exists(master_zip):
        os.remove(master_zip)
    bp.build_master_zip(portfolio_root, rc_manifest, master_zip)

    # 9. history preservation ---------------------------------------------------------
    hist = os.path.join(portfolio_root, "RELEASE", "history_r370")
    os.makedirs(hist, exist_ok=True)
    for fn in R370_LEGACY_ROOT_FILES:
        src = os.path.join(portfolio_root, fn)
        if os.path.exists(src):
            shutil.move(src, os.path.join(hist, fn))
    for legacy_dir in ("FULL_DOSSIERS", "BUYER_OUTREACH"):
        d = os.path.join(portfolio_root, legacy_dir)
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"[R371] removed duplicate tree {legacy_dir}/ "
                  f"(DOWNLOAD/ is the single authoritative release layer; "
                  f"history preserved in git)")

    print("[R371] V5 build complete:", portfolio_root)
    return {"portfolio_root": portfolio_root, "ranking": ranking,
            "loop_summary": loop_summary}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portfolio-root", default=bp.PORTFOLIO_ROOT_DEFAULT)
    ap.add_argument("--work-dir", default=None)
    args = ap.parse_args()
    build(args.portfolio_root, args.work_dir)


if __name__ == "__main__":
    main()

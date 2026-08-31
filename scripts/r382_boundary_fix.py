"""R382 boundary-leak correction (found live by the r372 boundary
guard after the R381 MODEL/ layer shipped; disclosed, never hidden —
Art. XV).

DEFECT: every REQUIRED package's MODEL/GEOMETRY_VALIDATION_REPORT.json
records the trimesh watertight check detail with the ABSOLUTE path of
the STL artifact (checks.G2_non_manifold_solids.detail[].path), which
leaks the transferor's filesystem into a shipped buyer file — a
violation of the R372 boundary rule 'no absolute local paths leaked
into shipped files'. The guard had not been re-run after the R381
MODEL/ layer was introduced, so the defect shipped unnoticed (honest
disclosure; the R382 disposition cycle re-ran the guard and caught it).

CORRECTION (deterministic, recorded):
  1. rewrite G2 detail path -> basename in the 14 affected reports
  2. update each package's PACKAGE_MANIFEST.json sha256 for the file
  3. re-render 00_PACKAGE_README.pdf (it lists the manifest hashes)
  4. update the manifest hash for the re-rendered readme
  5. rebuild each package ZIP (byte-reproducible, fixed epoch)
  6. re-freeze the disposition record's frozen identities and append a
     CORRECTIONS ledger (old/new sha256 per changed file — full audit
     trail; the pre-correction bytes remain in git history, Art. XI)
  7. regenerate the buyer release layer + re-run the acceptance gate

The source of the leak is fixed in cad_pipeline.py (G2 detail now
records the basename), so future builds are clean by construction.
"""
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from premium_package_factory.r371 import builder_documents as bd  # noqa: E402
from premium_package_factory.r371.builder import sha256_file  # noqa: E402
from premium_package_factory.r371.canonical_source import (  # noqa: E402
    PACKAGE_MAP, load_all_packages)
from premium_package_factory.r371 import build_v5  # noqa: E402
from premium_package_factory.r371 import acceptance as acc  # noqa: E402
from premium_package_factory.r382.disposition import (  # noqa: E402
    DISPOSITIONS, ENGINE_ROOT, package_location, folder_for)
from premium_package_factory.r382.release_docs import (  # noqa: E402
    regenerate_buyer_release_documents)

ROOT = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/z/my-project/technology-transfer-portfolio-15"
INPUT_DIR = os.path.join(ENGINE_ROOT, "premium_package_factory", "input")


def _load(fp):
    with open(fp, encoding="utf-8") as fh:
        return json.load(fh)


def _dump(fp, obj):
    with open(fp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def _rebuild_zip(pdir, zpath):
    from premium_package_factory.r371.build_v5 import _package_files_recursive
    if os.path.exists(zpath):
        os.remove(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in _package_files_recursive(pdir):
            build_v5._zip_add(zf, os.path.join(pdir, f), f)


def main():
    packages = load_all_packages()
    by_num = {p.num: p for p in packages}
    headlines = {r["package_id"]: r for r in json.load(open(
        os.path.join(INPUT_DIR, "headlines_r371.json"),
        encoding="utf-8"))["packages"]}
    styles_corrections = []

    for row in PACKAGE_MAP:
        num, folder = row["num"], folder_for(row["num"])
        pdir, rel = package_location(ROOT, num)
        report_fp = os.path.join(pdir, "MODEL",
                                 "GEOMETRY_VALIDATION_REPORT.json")
        if not os.path.exists(report_fp):
            continue
        report = _load(report_fp)
        g2 = ((report.get("checks") or {}).get(
            "G2_non_manifold_solids") or {})
        detail = g2.get("detail")
        changed = False
        if isinstance(detail, list):
            for entry in detail:
                p = entry.get("path")
                if isinstance(p, str) and p.startswith("/"):
                    entry["path"] = os.path.basename(p)
                    changed = True
        if not changed:
            continue
        old_sha = sha256_file(report_fp)
        _dump(report_fp, report)
        new_sha = sha256_file(report_fp)
        print(f"[fix] {folder}: G2 path sanitized "
              f"({old_sha[:10]} -> {new_sha[:10]})")

        # package manifest: refresh the hash entry for the report
        pm_fp = os.path.join(pdir, "PACKAGE_MANIFEST.json")
        pm = _load(pm_fp)
        for f in pm["files"]:
            if f["file"] == "MODEL/GEOMETRY_VALIDATION_REPORT.json":
                f["sha256"] = new_sha
        _dump(pm_fp, pm)

        # re-render the package readme (it lists manifest hashes)
        p = by_num[num]
        h = headlines[p.pkg_id]
        bd.render_package_readme(p, h, pm["files"],
                                 os.path.join(pdir,
                                              "00_PACKAGE_README.pdf"))
        from premium_package_factory.gates.render_verification import \
            verify_pdf_rendering
        verify_pdf_rendering(os.path.join(pdir,
                                          "00_PACKAGE_README.pdf"))
        for f in pm["files"]:
            if f["file"] == "00_PACKAGE_README.pdf":
                f["sha256"] = sha256_file(
                    os.path.join(pdir, "00_PACKAGE_README.pdf"))
        _dump(pm_fp, pm)

        # rebuild the package ZIP from the folder
        _rebuild_zip(pdir, os.path.join(os.path.dirname(pdir),
                                        folder + ".zip"))
        styles_corrections.append({
            "package": folder,
            "file": "MODEL/GEOMETRY_VALIDATION_REPORT.json",
            "reason": ("R372 boundary rule: absolute STL path in the "
                       "G2 trimesh watertight detail leaked the "
                       "transferor's filesystem into a shipped buyer "
                       "file; rewritten to the artifact basename"),
            "old_sha256": old_sha,
            "new_sha256": new_sha,
        })

    # re-freeze the disposition record (recorded correction event)
    rec_fp = os.path.join(ROOT, "PORTFOLIO_DISPOSITION.json")
    record = _load(rec_fp)
    for num, entry in record["dispositions"].items():
        pdir, rel = package_location(ROOT, num)
        folder = entry.get("folder")
        fi = entry["frozen_identity"]
        fi["package_manifest_sha256"] = sha256_file(
            os.path.join(pdir, "PACKAGE_MANIFEST.json"))
        fi["package_zip_sha256"] = sha256_file(
            os.path.join(os.path.dirname(pdir), folder + ".zip"))
        fi["dossier_sha256"] = sha256_file(
            os.path.join(pdir,
                         "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"))
        fi["file_count"] = sum(len(fs) for _r, _d, fs
                               in os.walk(pdir))
    record["corrections"] = styles_corrections
    record["corrections_note"] = (
        "R382 boundary-leak correction, applied live after the r372 "
        "boundary guard caught absolute STL paths in the G2 details of "
        "the R381 MODEL/ layer (the guard had not been re-run after "
        "R381 — disclosed defect). old/new sha256 per corrected file "
        "recorded above; pre-correction bytes remain in git history "
        "(Art. XI). The leak source is fixed in cad_pipeline.py so "
        "future builds are clean by construction.")
    _dump(rec_fp, record)
    print(f"[fix] frozen identities re-frozen; {len(styles_corrections)} "
          f"corrections recorded")

    # regenerate the buyer release layer (manifest/README/master ZIP
    # carry the corrected bytes) and re-run the acceptance gate
    from premium_package_factory.r371.equations import \
        build_equation_registry
    from premium_package_factory.r371.loopstate import (
        build_loop_state, portfolio_loop_summary)
    from premium_package_factory.r371.ranking import build_ranking
    from premium_package_factory.r371.unknowns import \
        build_unknown_roadmap
    from premium_package_factory.r372.equation_validation import \
        validate_registry
    from premium_package_factory.r372.traceability_semantics import \
        build_traceability_json
    from premium_package_factory.r374.traceability_truth import \
        attach_truth_model

    roads = {p.pkg_id: build_unknown_roadmap(p) for p in packages}
    loop_summary = portfolio_loop_summary(packages)
    ranking = build_ranking(packages, headlines, roads)
    traces, eqv = {}, {}
    for p in packages:
        legacy = os.path.join(INPUT_DIR, "legacy_json", p.num,
                              "ENGINEERING_TRACEABILITY.json")
        traces[p.pkg_id] = build_traceability_json(p, legacy)
        attach_truth_model(traces[p.pkg_id], p)
        eqv[p.pkg_id] = validate_registry(
            build_equation_registry(p), p)

    from premium_package_factory.r371.identity import (
        build_registry, write_registry)
    registry = build_registry(
        ROOT, statuses={p.pkg_id: "V2" for p in packages if p.addendum},
        rows=[r for r in PACKAGE_MAP
              if r["num"] in {n for n, e in DISPOSITIONS.items()
                              if e["state"] == "BUYER_PRIMARY"}],
        location_map={n: "DOWNLOAD" for n, e in
                      DISPOSITIONS.items()
                      if e["state"] == "BUYER_PRIMARY"})
    write_registry(ROOT, registry)

    release = regenerate_buyer_release_documents(
        ROOT, packages, headlines, ranking, loop_summary, traces, eqv)
    print(f"[fix] master ZIP sha256: "
          f"{release['master_zip_sha256']}")

    report = acc.run_acceptance(ROOT)
    print("=" * 70)
    fails = [r for r in report["conditions"] if r["status"] != "PASS"]
    for r in report["conditions"]:
        mark = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"  [{mark}] {r['condition']}")
    print("=" * 70)
    print(f"ALL PASS: {report['all_pass']}  (failures: {len(fails)})")
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

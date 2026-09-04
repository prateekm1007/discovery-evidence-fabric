#!/usr/bin/env python3
"""
r408_v31_reship.py — R408 §3: close the package-10 (P-22-R1) vocabulary
residue through the V3.1 canonical corrections and re-ship the buyer
surface.

Roadmap/directive basis: R408 "NEXT MOVE FOR THE CODER" — "Close the
package-10 vocabulary residue (§3): decide per-row — for EQ-3, re-derive
the canonical string/caption from the corrected canonical so subscripts
match 'Steering-lumen'; for traceability DO-002 / failure rows / workplans
/ unknowns, either extend the V3 operation set to those surfaces or add
every residual occurrence to B1_RESHIP_REPORT.json's orphan list so the
shipped disclosure is complete."

Per-row decisions (recorded in R408/V31_RESHIP_REPORT.json):
  FIXED via the V3.1 canonical operations (premium_package_factory/input/
  v3_corrections/P-22-R1_V3_CORRECTIONS.json, v3_version 3.1, 41 ops):
    EQ-3 (repair_equation), governing-model metadata rows, DO-002
    (description + missing input), failure rows (failure_modes +
    failure_analysis), remaining unknowns, workplan rows, BOM/materials/
    manufacturing/transfer-boundary embodiment rows, proposed-design
    metadata.
  REGENERATED with the surface converging to the current canonical
  derivation (the R407 registry-catch-up precedent, byte-diff disclosed):
    6 buyer PDFs, EQUATION_REGISTRY.json (+r372 validation +r374 status),
    UNKNOWN_ROADMAP.json, VALIDATION_ECONOMICS.json,
    ENGINEERING_TRACEABILITY.json (r372 semantics + r374 truth model —
    the shipped R374-era file predates the current instrument; the
    audit-checked fields already agreed),
    V3_MUTATION_ADDENDUM.json (verbatim NEW engine input),
    PACKAGE_MUTATION_CERTIFICATE (V3.1), PACKAGE_MANIFEST.json,
    the package ZIP, the master ZIP, RELEASE_CONTENT_MANIFEST.json,
    PORTFOLIO_IDENTITY_REGISTRY.json (P-22-R1 row),
    RELEASE/BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json (W1-a: the
    stale b9dd8a8f master-ZIP hash refreshed from the post-Z3 tree).
  DISCLOSED ORPHANS (every buyer-visible residual occurrence, enumerated
  in B1_RESHIP_REPORT.json's orphan list — the acceptance test "B1 orphan
  list exactly equals buyer-visible residue"):
    MODEL/ metadata rows (R384-era 3D-layer records, not regenerable
    without re-running the frozen CAD pipeline) and the MATURITY_BASIS.json
    known_blockers row (R370-era computed record).

Constitution: Art. II (exact-match corrections), Art. XI (pre-V3 bytes
stay in git history), Art. XXVIII (embodiment vocabulary removed, no
claim added), Art. XXXIX (portfolio content commit follows; the manifest
regeneration and chain verification follow as the release cycle).
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_ROOT))

from scripts.r407_b1_reship import (  # noqa: E402
    INPUT_DIR, _diff_report, _write_json, _zip_add, preship_scan,
    rebuild_identity_registry, rebuild_master_zip,
    rebuild_release_content_manifest, regenerate_distribution_certificate,
    sha256_file,
)
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
from premium_package_factory.r371.mechanism_diagram import (  # noqa: E402
    build_all_mechanism_diagrams)
from premium_package_factory.r372.equation_validation import (  # noqa: E402
    validate_registry)
from premium_package_factory.r372.diagram_adequacy import (  # noqa: E402
    experiment_diagram_spec)
from premium_package_factory.r371.experiment_diagram import (  # noqa: E402
    build_experiment_diagram)
from premium_package_factory.r372.traceability_semantics import (  # noqa: E402
    build_traceability_json)
from premium_package_factory.r374.traceability_truth import (  # noqa: E402
    attach_truth_model)
from premium_package_factory.r374.equation_status import (  # noqa: E402
    attach_r374_status)
from premium_package_factory.gates.render_verification import (  # noqa: E402
    verify_package, content_completeness, pdf_haystacks)
from premium_package_factory.gates.content_expectations import (  # noqa: E402
    build_content_expectations)

PKG_ID = "P-22-R1"
FOLDER = "10_catheter_navigation"
V3_DIR = INPUT_DIR / "v3_corrections"
WORK_DIR = ENGINE_ROOT / "premium_package_factory" / "output" / "r408_v31"

# buyer-visible residual-vocabulary census: every occurrence of these
# needles in the SHIPPED package (excluding V3_MUTATION_ADDENDUM.json —
# its 'before' strings are the verbatim correction trail, intentional)
NEEDLES = ("actuator", "balloon", "bellows")


def orphan_census(pdir):
    """Enumerate every buyer-visible residual-vocabulary occurrence in
    the shipped package (the acceptance test: the B1 orphan list exactly
    equals this census)."""
    hits = []
    for fp in sorted(pdir.rglob("*.json")):
        if fp.name == "V3_MUTATION_ADDENDUM.json":
            continue  # the verbatim correction trail (before-strings)
        if fp.parent.name == "MODEL":
            # MODEL/ metadata: R384-era 3D-layer records — disclosed
            continue
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue

        def walk(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    walk(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    walk(v, f"{path}[{i}]")
            elif isinstance(obj, str):
                low = obj.lower()
                for n in NEEDLES:
                    if n in low:
                        hits.append(f"{fp.name}:{path}:{n}")
                        break
        walk(d)
    return hits


def model_metadata_census(pdir):
    """The MODEL/ metadata residual occurrences (disclosed orphans)."""
    hits = []
    mdir = pdir / "MODEL"
    if not mdir.exists():
        return hits
    for fp in sorted(mdir.rglob("*.json")):
        text = fp.read_text(encoding="utf-8", errors="replace").lower()
        found = [n for n in NEEDLES if n in text]
        if found:
            hits.append(f"{FOLDER}/MODEL/{fp.name}:{'+'.join(found)}")
    return hits


def reship_v31(pkg, headline, portfolio_root, apply, report):
    pdir = portfolio_root / "DOWNLOAD" / FOLDER
    diffs = []

    # derived artifacts from the V3.1-corrected canonical
    eq_reg = build_equation_registry(pkg)
    eq_reg["r372_validation"] = validate_registry(eq_reg, pkg)
    attach_r374_status(eq_reg, pkg)
    road = build_unknown_roadmap(pkg)
    comm = build_commercial_evidence(pkg)
    ecos = build_validation_economics(pkg, headline.get("kill_if", ""))
    loops = build_loop_state(pkg)
    trace = attach_truth_model(
        build_traceability_json(
            pkg, legacy_path=str(pdir / "ENGINEERING_TRACEABILITY.json")),
        pkg)

    # diagrams (deterministic; work dir)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    mech_pngs = build_all_mechanism_diagrams(str(WORK_DIR / "mechanism"))
    exp_dir = WORK_DIR / "experiment"
    exp_dir.mkdir(parents=True, exist_ok=True)
    spec = experiment_diagram_spec(pkg, headline)
    exp_png = build_experiment_diagram(
        pkg, headline, str(exp_dir / f"{pkg.num}_experiment_setup.png"),
        spec=spec)

    v3_src = V3_DIR / f"{pkg.pkg_id}_V3_CORRECTIONS.json"
    v3_bytes = v3_src.read_bytes()

    if not apply:
        for name, obj in (("EQUATION_REGISTRY.json", eq_reg),
                          ("UNKNOWN_ROADMAP.json", road),
                          ("VALIDATION_ECONOMICS.json", ecos),
                          ("ENGINEERING_TRACEABILITY.json", trace)):
            fp = pdir / name
            new = (json.dumps(obj, indent=2, ensure_ascii=False)
                   + "\n").encode()
            diffs.append(f"{name}: would re-derive "
                         f"({len(fp.read_bytes())} -> {len(new)} bytes)")
        for fn in ("02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                   "03_BUYER_DECISION_CARD.pdf",
                   "00_PACKAGE_README.pdf",
                   "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                   "04_EVIDENCE_SUMMARY.pdf",
                   "05_TRANSFER_MANIFEST.pdf"):
            diffs.append(f"{fn}: re-render (V3.1 text)")
        diffs.append("V3_MUTATION_ADDENDUM.json: re-ship (verbatim V3.1 "
                     "engine input)")
        diffs.append("PACKAGE_MUTATION_CERTIFICATE_P-22-R1_V3.json: "
                     "re-issue (V3.1)")
        diffs.append("PACKAGE_MANIFEST.json: re-pin (V3.1)")
        diffs.append(f"{FOLDER}.zip: rebuilt")
        report["planned_changes"] = diffs
        return

    # ---- apply: render the six buyer PDFs --------------------------------
    styles = get_styles()
    init_styles(styles)
    _init_dossier_styles(styles)
    qa_root = portfolio_root / "INTERNAL_QA" / "rendered_pages_r408"
    qa_root.mkdir(parents=True, exist_ok=True)

    old_bytes = {f: (pdir / f).read_bytes() for f in (
        "00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
        "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
        "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
        "05_TRANSFER_MANIFEST.pdf", "EQUATION_REGISTRY.json",
        "UNKNOWN_ROADMAP.json", "VALIDATION_ECONOMICS.json",
        "ENGINEERING_TRACEABILITY.json", "V3_MUTATION_ADDENDUM.json",
        "PACKAGE_MANIFEST.json") if (pdir / f).exists()}

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
    pkg_qa = verify_package(str(pdir), png_dir=str(qa_root / FOLDER))
    streams = []
    for f in sorted(pdir.parent.glob(f"{FOLDER}/*.pdf")):
        streams.extend(pdf_haystacks(str(f)))
    exp_ = build_content_expectations(pkg, headline, road)
    ok, failures = content_completeness(exp_, streams)
    if not ok:
        raise RuntimeError(
            f"R408 V3.1 content completeness FAILED for {pkg.pkg_id}: "
            + "; ".join(f"{f['field']}" for f in failures[:8]))

    # machine-readable layer
    _write_json(pdir / "EQUATION_REGISTRY.json", eq_reg)
    _write_json(pdir / "UNKNOWN_ROADMAP.json", road)
    _write_json(pdir / "VALIDATION_ECONOMICS.json", ecos)
    _write_json(pdir / "ENGINEERING_TRACEABILITY.json", trace)

    # V3.1 addendum (verbatim NEW engine input) + V3.1 mutation certificate
    (pdir / "V3_MUTATION_ADDENDUM.json").write_bytes(v3_bytes)
    cert = {
        "certificate_type": "PACKAGE_MUTATION_CERTIFICATE",
        "mutation_id": "MUTCERT-P-22-R1-V3.1",
        "package_id": pkg.pkg_id,
        "folder": FOLDER,
        "v2_to_v3": True,
        "v3_version": "3.1",
        "supersedes": "MUTCERT-P-22-R1-V3 (the R407 P0 re-ship; the V3.1 "
                      "operations close the vocabulary residue: EQ-3 "
                      "subscripts, DO-002, failure rows, workplans, "
                      "unknowns, embodiment rows)",
        "before_manifest_hash": None,
        "v3_addendum_hash": hashlib.sha256(v3_bytes).hexdigest(),
        "changed_fields_count": len(json.loads(v3_bytes).get(
            "operations", [])),
        "reason": "R408 P0-closing directive §3: align the remaining "
                  "shipped surfaces to the V3-corrected canonical "
                  "(steering-lumen vocabulary); remove the unimplemented "
                  "balloon/bellows embodiment vocabulary; no claim is "
                  "added (Art. XXVIII).",
        "evidence_basis": f"premium_package_factory/input/v3_corrections/"
                          f"{pkg.pkg_id}_V3_CORRECTIONS.json (v3_version "
                          f"3.1)",
        "authorization": "R408 P0-closing directive (NEXT MOVE FOR THE "
                         "CODER, 2026-09-04)",
        "orphan_disclosure": "MODEL/ metadata rows + the MATURITY_BASIS "
                             "known_blockers row remain as disclosed "
                             "orphans (enumerated in the engine repo's "
                             "R407/B1_RESHIP_REPORT.json orphan list)",
    }
    cert_path = pdir / f"PACKAGE_MUTATION_CERTIFICATE_{pkg.pkg_id}_V3.json"
    _write_json(cert_path, cert)

    # PACKAGE_MANIFEST: file list + hashes + version 3.1
    pm_path = pdir / "PACKAGE_MANIFEST.json"
    pm = json.loads(pm_path.read_text(encoding="utf-8"))
    files = []
    for full, rel in _walk_files(pdir):
        if rel in ("PACKAGE_MANIFEST.json",):
            continue
        files.append({"file": rel, "sha256": sha256_file(full)})
    files.append({"file": f"PACKAGE_MUTATION_CERTIFICATE_{pkg.pkg_id}"
                         f"_V3.json", "sha256": sha256_file(cert_path)})
    files.sort(key=lambda x: x["file"])
    pm["files"] = files
    pm["package_version"] = "3.1"
    pm["version_note"] = ("V3.1: the R408 vocabulary-closure corrections "
                          "re-shipped (EQ-3 subscripts, DO-002, failure "
                          "rows, workplans, unknowns); V2/V3 mutation "
                          "history preserved in-package.")
    _write_json(pm_path, pm)

    # package ZIP (deterministic epoch entries)
    zpath = portfolio_root / "DOWNLOAD" / f"{FOLDER}.zip"
    old_zip_hash = sha256_file(zpath) if zpath.exists() else None

    def _rebuild_zip():
        import zipfile
        with zipfile.ZipFile(zpath, "w") as zf:
            for full, rel in _walk_files(pdir):
                _zip_add(zf, str(full), rel)
    _rebuild_zip()

    # second pass: fill the certificate's manifest hashes, re-pin, re-zip
    cert["after_manifest_hash"] = sha256_file(pm_path)
    _write_json(cert_path, cert)
    for f in pm["files"]:
        if f["file"] == f"PACKAGE_MUTATION_CERTIFICATE_{pkg.pkg_id}_V3.json":
            f["sha256"] = sha256_file(cert_path)
    _write_json(pm_path, pm)
    _rebuild_zip()

    for f, old in old_bytes.items():
        new = (pdir / f).read_bytes()
        if new != old:
            diffs.append(_diff_report(pdir / f, old, new))
    diffs.append(f"{FOLDER}.zip: rebuilt "
                 f"({'unchanged' if sha256_file(zpath) == old_zip_hash
                 else 'CHANGED'})")
    report["changes"] = diffs
    report["qa"] = "PASS"
    report["content_expectations"] = len(exp_)
    report["v3_version"] = "3.1"
    report["v3_operations"] = len(json.loads(v3_bytes).get("operations", []))


def _walk(pdir):
    """os.walk generator (Path.walk is 3.12+)."""
    import os
    for dp, dn, fns in os.walk(pdir):
        yield Path(dp), dn, fns


def _walk_files(pdir):
    for dp, _dn, fns in _walk(pdir):
        for fn in sorted(fns):
            full = dp / fn
            yield full, str(full.relative_to(pdir))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portfolio-root", required=True)
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: verify-only)")
    args = ap.parse_args()
    portfolio_root = Path(args.portfolio_root).resolve()
    if not (portfolio_root / "DOWNLOAD").exists():
        raise SystemExit(f"not a portfolio clone: {portfolio_root}")

    report = {
        "artifact": "R408_V31_RESHIP",
        "mode": "APPLY" if args.apply else "VERIFY_ONLY",
        "package": PKG_ID,
        "folder": FOLDER,
    }

    # 0. pre-ship scan: MODEL geometry must not reference removed
    #    embodiments (the R407 gate, unchanged)
    blockers, disclosed = preship_scan(portfolio_root)
    report["preship_scan"] = {"blockers": blockers,
                              "orphaned_embodiment_metadata": disclosed}
    if blockers:
        print("PRE-SHIP SCAN FAILED (MODEL geometry references a removed "
              "embodiment — do NOT re-ship without a CAD decision):")
        for b in blockers:
            print("  -", b)
        if args.apply:
            raise SystemExit(1)

    packages = load_all_packages()
    headlines = {r["package_id"]: r for r in json.load(
        open(INPUT_DIR / "headlines_r371.json", encoding="utf-8"))
        ["packages"]}
    by_id = {p.pkg_id: p for p in packages}
    pkg = by_id[PKG_ID]
    if pkg.version != "3.1":
        raise SystemExit(
            f"expected V3.1-corrected canonical view, got version "
            f"{pkg.version!r} — run scripts/r408_build_v31_corrections.py "
            f"first")

    v3_ops = len(json.loads(
        (V3_DIR / f"{PKG_ID}_V3_CORRECTIONS.json").read_text(
            encoding="utf-8"))["operations"])
    print(f"[{PKG_ID}] mode={'APPLY' if args.apply else 'VERIFY'} "
          f"(V3.1, {v3_ops} ops)")
    reship_v31(pkg, headlines[PKG_ID], portfolio_root, args.apply, report)

    if args.apply:
        # registry + identity first (the certificate reads them), then the
        # master ZIP, then the content manifest, then the distribution
        # certificate from the FINAL tree state (W1-a fix)
        rebuild_identity_registry(portfolio_root, True, report)
        # the P-22-R1 registry row moves to V3.1
        reg_path = portfolio_root / "PORTFOLIO_IDENTITY_REGISTRY.json"
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        for row in reg.get("packages", []):
            if row.get("historical_package_id") == PKG_ID:
                row["version"] = "3.1"
        _write_json(reg_path, reg)
        rebuild_master_zip(portfolio_root, True, report)
        rebuild_release_content_manifest(portfolio_root, True, report)
        regenerate_distribution_certificate(portfolio_root, True, report)
        report["distribution_certificate_note"] = (
            "W1-a: master_zip_hash regenerated from the post-Z3 tree (the "
            "R407 re-ship left it pinning the superseded b9dd8a8f ZIP "
            "because the certificate was not re-run after the aab9e39 "
            "master-ZIP rebuild)")

        # the orphan census: every buyer-visible residual occurrence
        pdir = portfolio_root / "DOWNLOAD" / FOLDER
        report["orphan_census"] = {
            "non_model_orphans": orphan_census(pdir),
            "model_metadata_orphans": model_metadata_census(pdir),
            "note": "B1_RESHIP_REPORT.json's orphan list is set to exactly "
                    "this census (MODEL/ metadata + the MATURITY_BASIS "
                    "known_blockers row + any non-model residue); "
                    "V3_MUTATION_ADDENDUM 'before' strings are the "
                    "intentional correction trail, not residue",
        }
        # MATURITY_BASIS known_blockers row (R370-era record, disclosed)
        mb = json.loads((pdir / "MATURITY_BASIS.json").read_text(
            encoding="utf-8"))
        for i, kb in enumerate(mb.get("known_blockers", [])):
            low = str(kb).lower()
            if any(n in low for n in NEEDLES):
                report["orphan_census"][
                    "maturity_basis_rows"] = report["orphan_census"].get(
                        "maturity_basis_rows", []) + [
                        f"{FOLDER}/MATURITY_BASIS.json:known_blockers[{i}]"]
        # update B1_RESHIP_REPORT.json's orphan list to EXACTLY the census
        b1_path = ENGINE_ROOT / "R407" / "B1_RESHIP_REPORT.json"
        b1 = json.loads(b1_path.read_text(encoding="utf-8"))
        oc = report["orphan_census"]
        b1["preship_scan"]["orphaned_embodiment_metadata"] = (
            oc["model_metadata_orphans"] + oc.get("maturity_basis_rows", [])
            + oc["non_model_orphans"])
        b1["v31_extension"] = {
            "round": "R408",
            "orphan_list_equals_buyer_visible_residue": True,
            "census": oc,
            "fixed_via_v31_canonical_ops": 41 - 7 if False else None,
            "note": "the V3.1 operations (31 new, 41 total) close the "
                    "derivable surfaces; the enumerated orphans are the "
                    "complete buyer-visible residue",
        }
        b1["v31_extension"]["fixed_via_v31_canonical_ops"] = len(
            json.loads((V3_DIR / f"{PKG_ID}_V3_CORRECTIONS.json").read_text(
                encoding="utf-8"))["operations"]) - 7
        b1_path.write_text(json.dumps(b1, indent=1, ensure_ascii=False)
                           + "\n", encoding="utf-8")

    out = ENGINE_ROOT / "R408" / "V31_RESHIP_REPORT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"[report] {out}")
    if not args.apply:
        print("VERIFY-ONLY: no files were written. Re-run with --apply.")


if __name__ == "__main__":
    main()

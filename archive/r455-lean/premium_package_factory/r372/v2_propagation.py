"""
v2_propagation.py — R372-6: prove V2 mutation propagation end-to-end.

CEO R372-6: for every mutation verify the buyer actually receives V2
EVERYWHERE:

    V1 -> evidence correction -> V2 canonical state
        -> PDF  (V2 text rendered; V1 text absent from buyer documents)
        -> JSON (addendum shipped verbatim; version 2.0 in manifests)
        -> ZIP  (extracted bytes == folder bytes)

No repeat of the R370 defect (addenda shipped as JSON without re-rendering
the buyer PDFs).

Checks per package with a recorded V2 addendum:
  1. ADDENDUM_VERBATIM   the shipped V2_MUTATION_ADDENDUM.json is
                         byte-identical to the engine input snapshot
  2. CERTIFICATE_SHIPPED the package mutation certificate is present
  3. VERSION_2           PACKAGE_MANIFEST.package_version == addendum
                         v2_version AND the identity registry marks V2
  4. V2_RENDERED         every mutation's v2_text appears in at least one
                         buyer PDF of the package
  5. V1_ABSENT           no mutation's v1_text appears in any buyer PDF
                         (the V1 string may appear ONLY inside the addendum
                         JSON itself — never in the rendered documents)
  6. ZIP_EQUIV           every file extracted from the package ZIP is
                         byte-identical to the folder file
"""

import hashlib
import json
import os
import subprocess
import zipfile

_PDF_CACHE = {}


def _pdf_text(path):
    """pdftotext extraction cached by file identity (path+mtime+size) so a
    tampered/rebuilt file is never verified against stale cached text."""
    stat = os.stat(path)
    key = (path, stat.st_mtime_ns, stat.st_size)
    if key not in _PDF_CACHE:
        r = subprocess.run(["pdftotext", path, "-"], capture_output=True,
                           text=True)
        _PDF_CACHE[key] = r.stdout or ""
    return _PDF_CACHE[key]


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


BUYER_PDFS = [
    "00_PACKAGE_README.pdf",
    "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
    "02_ENGINEERING_TECHNICS_TRANSFER_DOSSIER.pdf",  # placeholder; corrected below
]
BUYER_PDFS[2] = "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"
BUYER_PDFS += ["03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
               "05_TRANSFER_MANIFEST.pdf"]

# R382 disposition locations, in resolution order. The engine build applies
# the CEO disposition (4 buyer-primary in DOWNLOAD; the rest in HOLDING /
# SPECIALIST_TRACK / RETIRED); the portfolio release tree is the flat
# pre-disposition layout (all 15 under DOWNLOAD). Both are valid states and
# both must be verifiable — the resolver finds a package wherever it lives.
DISPOSITION_BASES = ("DOWNLOAD", "HOLDING", "SPECIALIST_TRACK", "RETIRED")


def resolve_package_dir(portfolio_root, folder):
    """Disposition-aware package directory (R382 layouts and flat layouts)."""
    for base in DISPOSITION_BASES:
        cand = os.path.join(str(portfolio_root), base, folder)
        if os.path.isdir(cand):
            return cand
    return os.path.join(str(portfolio_root), "DOWNLOAD", folder)


def package_zip_path(portfolio_root, folder):
    """Disposition-aware package ZIP path."""
    for base in DISPOSITION_BASES:
        cand = os.path.join(str(portfolio_root), base, f"{folder}.zip")
        if os.path.isfile(cand):
            return cand
    return os.path.join(str(portfolio_root), "DOWNLOAD", f"{folder}.zip")


def walk_relative_files(pdir):
    """Every file under a package dir as '/'-separated relative paths.

    R381 3D-layer aware: packages now contain a MODEL/ subdirectory, so a
    flat os.listdir() no longer equals the manifest's recursive file set
    (a latent flat-layout assumption in the R372 instruments, found live by
    the R386 full-suite run)."""
    out = set()
    for root, _dirs, files in os.walk(str(pdir)):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), str(pdir))
            out.add(rel.replace(os.sep, "/"))
    return out


def verify_package_v2(portfolio_root, pkg, addendum_input_path: str) -> dict:
    """Verify V2 propagation for one package with a recorded addendum."""
    pdir = resolve_package_dir(portfolio_root, pkg.folder)
    checks = []
    ok_all = True

    def record(name, ok, detail=""):
        nonlocal ok_all
        checks.append({"check": name, "status": "PASS" if ok else "FAIL",
                       "detail": str(detail)[:200]})
        if not ok:
            ok_all = False

    # 1. addendum shipped verbatim
    shipped = os.path.join(pdir, "V2_MUTATION_ADDENDUM.json")
    if os.path.exists(shipped) and os.path.exists(addendum_input_path):
        record("ADDENDUM_VERBATIM",
               _sha256_file(shipped) == _sha256_file(addendum_input_path),
               "shipped addendum byte-identical to engine input snapshot")
    else:
        record("ADDENDUM_VERBATIM", False, "addendum missing")

    with open(shipped, encoding="utf-8") as f:
        addendum = json.load(f)

    # 2. certificate present
    cert_present = any(
        f.startswith("PACKAGE_MUTATION_CERTIFICATE")
        and "_V2.json" in f and pkg.pkg_id in f
        for f in os.listdir(pdir))
    record("CERTIFICATE_SHIPPED", cert_present,
           "package mutation certificate present")

    # 3. version 2.0 everywhere
    pm_path = os.path.join(pdir, "PACKAGE_MANIFEST.json")
    version_ok = False
    if os.path.exists(pm_path):
        pm = json.load(open(pm_path, encoding="utf-8"))
        version_ok = pm.get("package_version") == addendum.get("v2_version")
    record("VERSION_2", version_ok,
           f"PACKAGE_MANIFEST version == {addendum.get('v2_version')}")

    reg_path = os.path.join(str(portfolio_root),
                            "PORTFOLIO_IDENTITY_REGISTRY.json")
    reg_ok = False
    reg_detail = "identity registry status == V2"
    if os.path.exists(reg_path):
        reg = json.load(open(reg_path, encoding="utf-8"))
        row = next((r for r in reg["packages"]
                    if r["historical_package_id"] == pkg.pkg_id), None)
        reg_ok = bool(row) and row.get("status") == "V2"
        if row is None:
            # R382 disposition: the identity registry scopes to the
            # buyer-visible release. A V2-carrying package that is NOT
            # buyer-visible (HOLDING/SPECIALIST_TRACK/RETIRED) is legitimately
            # outside the registry; a buyer-visible (DOWNLOAD) package that
            # is missing from the registry is genuine identity drift.
            buyer_visible = os.path.basename(
                os.path.dirname(pdir)) == "DOWNLOAD"
            reg_ok = not buyer_visible
            reg_detail = ("not in registry scope (R382 disposition, "
                          "non-buyer-visible package)" if reg_ok else
                          "buyer-visible package missing from registry")
    record("REGISTRY_V2", reg_ok, reg_detail)

    # 4/5. V2 rendered, V1 absent (buyer PDFs)
    pdf_texts = {}
    for pdf in BUYER_PDFS:
        fp = os.path.join(pdir, pdf)
        if os.path.exists(fp):
            pdf_texts[pdf] = _pdf_text(fp)

    mutations = addendum.get("mutations", [])
    for m in mutations:
        mid = m.get("mutation_id", "?")
        v1 = m.get("v1_text", "")
        v2 = m.get("v2_text", "")
        # dual-reference mutations are split the same way the renderer splits
        v2_variants = [v2]
        if " / " in v2:
            v2_variants += [p for p in v2.split(" / ") if p]
        # PDF rendering re-wraps lines: match on whitespace-free forms
        rendered = any(
            _compact(var) and _compact(var) in _compact(txt)
            for var in v2_variants
            for txt in pdf_texts.values())
        record(f"V2_RENDERED[{mid}]", rendered,
               f"v2_text present in buyer PDFs")
        if v1:
            v1_variants = [v1] + ([p for p in v1.split(" / ") if p]
                                  if " / " in v1 else [])
            stale_hits = []
            for pdf, txt in pdf_texts.items():
                txt_c = _compact(txt)
                for var in v1_variants:
                    var_c = _compact(var)
                    if not var_c:
                        continue
                    start = 0
                    while True:
                        i = txt_c.find(var_c, start)
                        if i < 0:
                            break
                        # An occurrence is acceptable ONLY when it is part
                        # of the V2 rendering itself (extension mutations
                        # whose v2 contains the v1 as a prefix).
                        v2_c = _compact(v2)
                        covered = any(
                            _compact(variant) and var_c in _compact(variant)
                            and txt_c[i:i + len(_compact(variant))]
                            == _compact(variant)
                            for variant in v2_variants)
                        if not covered:
                            stale_hits.append(pdf)
                            break
                        start = i + 1
            record(f"V1_ABSENT[{mid}]", not stale_hits,
                   f"v1_text absent from buyer PDFs outside V2 renderings "
                   f"(stale in: {sorted(set(stale_hits))})")

    # 6. ZIP == folder (R381 3D-layer aware: recursive relative file walk,
    # directory entries in the ZIP skipped)
    zpath = package_zip_path(portfolio_root, pkg.folder)
    zip_ok = True
    if os.path.exists(zpath):
        with zipfile.ZipFile(zpath) as zf:
            names = {n for n in zf.namelist() if not n.endswith("/")}
            folder_files = walk_relative_files(pdir)
            if names != folder_files:
                zip_ok = False
            else:
                for n in names:
                    if hashlib.sha256(zf.read(n)).hexdigest() != \
                            _sha256_file(os.path.join(pdir, n)):
                        zip_ok = False
                        break
    else:
        zip_ok = False
    record("ZIP_EQUIV", zip_ok,
           "every ZIP-extracted file byte-identical to the folder file")

    return {
        "package_id": pkg.pkg_id,
        "portfolio_number": pkg.num,
        "mutation_count": len(mutations),
        "checks": checks,
        "all_pass": ok_all,
    }


def _compact(text: str) -> str:
    """Whitespace-free form for wrap-tolerant exact matching (the PDF
    renderer re-wraps lines; whitespace is presentation, not content)."""
    import re
    return re.sub(r"\s+", "", text or "")


def verify_portfolio_v2(portfolio_root, packages, addendum_dir: str) -> dict:
    """Verify V2 propagation for every package carrying an addendum."""
    results = []
    for pkg in packages:
        if not pkg.addendum:
            continue
        addendum_input = os.path.join(
            addendum_dir, f"V2_MUTATION_ADDENDUM_{pkg.pkg_id}.json")
        results.append(verify_package_v2(portfolio_root, pkg,
                                          addendum_input))
    total_mutations = sum(r["mutation_count"] for r in results)
    passed = sum(1 for r in results if r["all_pass"])
    return {
        "report": "R372_V2_PROPAGATION",
        "packages_with_addenda": len(results),
        "total_mutations": total_mutations,
        "packages_all_pass": passed,
        "propagation_complete": passed == len(results) and len(results) > 0,
        "results": results,
    }

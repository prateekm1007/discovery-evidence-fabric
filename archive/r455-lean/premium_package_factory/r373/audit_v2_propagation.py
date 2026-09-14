"""
audit_v2_propagation.py — R373-5: end-to-end V2 mutation propagation.

For EVERY recorded mutation the full chain is audited:

    1 V1_SOURCE       v1_text provenance, mechanically verified in one of
                      three recorded forms:
                        VERBATIM_CANONICAL    compact match inside the
                                              R370Q canonical export
                        VERBATIM_V1_RELEASE   compact match inside the
                                              frozen V1 release PDFs
                                              (portfolio git, commit
                                              ef619a1 — the immutable
                                              pre-mutation release)
                        ADDITIVE_PLACEHOLDER  the recorded "(No explicit
                                              ... in V1 dossier)" form
                                              for disclosures added where
                                              none existed
                      Untraceable v1_text = audit failure.
    2 CORRECTION      addendum carries a reason and evidence basis
    3 CANONICAL_V2    v2_text non-empty
    4 ENGINEERING_JSON  shipped addendum byte-identical to the engine
                      input snapshot; PACKAGE_MANIFEST version 2.0;
                      identity registry marks V2; NO shipped JSON carries
                      the stale v1_text as current content
    5 DOSSIER_PDF     v2 operative form rendered; v1 absent
    6 BUYER_CARD      v2 rendered (corrections section); v1 absent
    7 EVIDENCE_SUMMARY  full v2 text rendered in the mutation trail
    8 TRANSFER_MANIFEST v2 rendered (corrections section); v1 absent
    9 ZIP             every ZIP-extracted file byte-identical to the
                      folder file, and the ZIP member set == folder set

"One missing propagation should fail the release" — any failed stage
fails the package (and therefore the release).

All checks are read-only with respect to the portfolio (Art. IX). The
V1 release text is extracted from the portfolio repo's git history with
`git show` into a temp dir.
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile

_PDF_CACHE = {}
_ZIP_CACHE = {}

BUYER_PDFS = [
    "00_PACKAGE_README.pdf",
    "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
    "03_BUYER_DECISION_CARD.pdf",
    "04_EVIDENCE_SUMMARY.pdf",
    "05_TRANSFER_MANIFEST.pdf",
]


def _compact(t: str) -> str:
    return re.sub(r"\s+", "", t or "")


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


_FOOTER_RE = re.compile(
    r"Portfolio\s+\d+\s+of\s+15\s*-\s*Package\s+[A-Z0-9-]+\s*-\s*"
    r"Version\s+[\d.]+\s*CONFIDENTIAL\s*—\s*TECHNOLOGY\s*TRANSFER\s*"
    r"EVALUATION\s*Page\s+\d+", re.I)


def _pdf_text(path):
    stat = os.stat(path)
    key = (path, stat.st_mtime_ns, stat.st_size)
    if key not in _PDF_CACHE:
        r = subprocess.run(["pdftotext", "-raw", path, "-"],
                           capture_output=True, text=True)
        # strip the page footer (presentation chrome): a long rendered
        # string that wraps across a page boundary has the footer
        # interleaved in the extraction stream and would otherwise break
        # contiguous content matching.
        _PDF_CACHE[key] = _FOOTER_RE.sub("", r.stdout or "")
    return _PDF_CACHE[key]


def _v1_parts(v1: str):
    parts = [v1]
    if " / " in v1:
        parts += [p for p in v1.split(" / ") if p]
    return [p for p in parts if p]


def _v2_forms(v2: str):
    forms = [v2]
    if " / " in v2:
        forms += [p for p in v2.split(" / ") if p]
    return [f for f in forms if f]


# ---------------------------------------------------------------------------
# V1 release text extraction (portfolio git history, read-only)
# ---------------------------------------------------------------------------

_V1_RELEASE_COMMIT = "ef619a1ed7678467781a03494c964ec5c75ec501"


def _git_show(portfolio_root: str, spec: str) -> bytes:
    """`git show <commit>:<path>` with a targeted fetch fallback for
    shallow clones (the frozen V1 release commit predates a depth-1
    clone's history)."""
    r = subprocess.run(["git", "-C", portfolio_root, "show", spec],
                       capture_output=True)
    if r.returncode == 0 and r.stdout:
        return r.stdout
    commit = spec.split(":", 1)[0]
    subprocess.run(["git", "-C", portfolio_root, "fetch", "--depth", "1",
                    "origin", commit], capture_output=True, timeout=180)
    r = subprocess.run(["git", "-C", portfolio_root, "show", spec],
                       capture_output=True)
    return r.stdout if r.returncode == 0 else b""


def v1_release_texts(portfolio_root: str, pkg, folder: str) -> str:
    """Concatenated PDF text of the package as shipped in the immutable
    V1 release commit ef619a1 (pre-mutation buyer portfolio)."""
    key = pkg.pkg_id
    if key in _ZIP_CACHE:
        return _ZIP_CACHE[key]
    try:
        data = _git_show(portfolio_root,
                         f"{_V1_RELEASE_COMMIT}:DOWNLOAD/{folder}.zip")
        if not data:
            _ZIP_CACHE[key] = ""
            return ""
        with tempfile.TemporaryDirectory() as td:
            zp = os.path.join(td, "v1.zip")
            with open(zp, "wb") as f:
                f.write(data)
            with zipfile.ZipFile(zp) as zf:
                zf.extractall(td)
            texts = []
            for fn in sorted(os.listdir(td)):
                if fn.endswith(".pdf"):
                    texts.append(_pdf_text(os.path.join(td, fn)))
        _ZIP_CACHE[key] = " ".join(texts)
    except Exception:
        _ZIP_CACHE[key] = ""
    return _ZIP_CACHE[key]


_PLACEHOLDER_RE = re.compile(r"^\(No explicit .* in V1 dossier\)$", re.I)


def classify_v1_source(v1_text: str, canonical_export_text: str,
                       v1_release_text: str) -> dict:
    """Mechanically verify where the recorded v1_text comes from."""
    parts = _v1_parts(v1_text)
    canon_c = _compact(canonical_export_text)
    v1_c = _compact(v1_release_text)
    for p in parts:
        if _compact(p) in canon_c:
            return {"v1_source_type": "VERBATIM_CANONICAL",
                    "evidence": f"v1 part verbatim in R370Q export: "
                                f"{p[:60]!r}"}
    for p in parts:
        if _compact(p) in v1_c:
            return {"v1_source_type": "VERBATIM_V1_RELEASE",
                    "evidence": f"v1 part verbatim in frozen V1 release "
                                f"(portfolio ef619a1): {p[:60]!r}"}
    if _PLACEHOLDER_RE.match(v1_text.strip()):
        return {"v1_source_type": "ADDITIVE_PLACEHOLDER",
                "evidence": "recorded placeholder form for an additive "
                            "disclosure (no V1 text existed)"}
    return {"v1_source_type": "V1_SOURCE_UNTRACEABLE",
            "evidence": "v1 text found in neither the canonical export "
                        "nor the frozen V1 release; not a recorded "
                        "additive placeholder"}


# ---------------------------------------------------------------------------
# per-package audit
# ---------------------------------------------------------------------------

def _stale_v1_hits(v1_forms, text_c, v2_forms):
    """Occurrences of v1 text not covered by a v2 rendering."""
    hits = []
    for var in v1_forms:
        var_c = _compact(var)
        if not var_c:
            continue
        start = 0
        while True:
            i = text_c.find(var_c, start)
            if i < 0:
                break
            covered = any(_compact(f) and var_c in _compact(f)
                          and text_c[i:i + len(_compact(f))]
                          == _compact(f) for f in v2_forms)
            if not covered:
                hits.append(var[:50])
                break
            start = i + 1
    return hits


def audit_package_v2(portfolio_root, pkg, addendum_input_path,
                     canonical_export_path) -> dict:
    """Audit the complete 9-stage chain for every mutation of a package."""
    pdir = os.path.join(portfolio_root, "DOWNLOAD", pkg.folder)
    checks = []
    ok_all = True

    def record(name, ok, detail=""):
        nonlocal ok_all
        checks.append({"stage": name, "status": "PASS" if ok else "FAIL",
                       "detail": str(detail)[:250]})
        if not ok:
            ok_all = False

    with open(addendum_input_path, encoding="utf-8") as f:
        addendum = json.load(f)
    mutations = addendum.get("mutations", [])
    with open(canonical_export_path, encoding="utf-8") as f:
        canonical_text = f.read()

    # ---- stage 4 prelude: addendum shipped verbatim --------------------
    shipped = os.path.join(pdir, "V2_MUTATION_ADDENDUM.json")
    record("ENGINEERING_JSON.ADDENDUM_VERBATIM",
           os.path.exists(shipped) and
           _sha256_file(shipped) == _sha256_file(addendum_input_path),
           "shipped addendum byte-identical to engine input snapshot")
    pm = json.load(open(os.path.join(pdir, "PACKAGE_MANIFEST.json"),
                        encoding="utf-8"))
    # R407 P0 (B1 class — V3-aware): the R394 V3 corrections supersede
    # the V2 line for P-07 / P-22-R1 / P-24; the shipped manifest
    # version and registry status carry the CURRENT shipped version.
    expected_version = addendum.get("v2_version")
    expected_status = "V2"
    if getattr(pkg, "v3_corrections", None):
        expected_version = pkg.v3_corrections.get(
            "v3_version", "3.0")
        expected_status = "V3"
    record("ENGINEERING_JSON.VERSION_2",
           pm.get("package_version") == expected_version,
           f"PACKAGE_MANIFEST version == {expected_version}"
           f"{' (V3 supersedes the V2 line)' if expected_status == 'V3'
             else ''}")
    reg = json.load(open(os.path.join(portfolio_root,
                                      "PORTFOLIO_IDENTITY_REGISTRY.json"),
                         encoding="utf-8"))
    row = next((r for r in reg["packages"]
                if r["historical_package_id"] == pkg.pkg_id), None)
    record("ENGINEERING_JSON.REGISTRY_V2",
           bool(row) and row.get("status") == expected_status,
           f"identity registry status == {expected_status}")

    # ---- per-mutation stages -------------------------------------------
    pdf_texts = {pdf: _pdf_text(os.path.join(pdir, pdf))
                 for pdf in BUYER_PDFS
                 if os.path.exists(os.path.join(pdir, pdf))}

    v1_release = v1_release_texts(portfolio_root, pkg, pkg.folder)
    mutation_reports = []
    for m in mutations:
        mid = m.get("mutation_id", "?")
        mr = {"mutation_id": mid, "stages": []}

        # 1 V1_SOURCE
        src = classify_v1_source(m.get("v1_text", ""), canonical_text,
                                 v1_release)
        ok = src["v1_source_type"] != "V1_SOURCE_UNTRACEABLE"
        mr["stages"].append({"stage": "V1_SOURCE", "status":
                             "PASS" if ok else "FAIL", "detail": src})
        if not ok:
            ok_all = False

        # 2 CORRECTION
        ok = bool(str(m.get("reason", "")).strip()) and \
            bool(m.get("evidence_basis"))
        mr["stages"].append({"stage": "CORRECTION",
                             "status": "PASS" if ok else "FAIL",
                             "detail": "reason + evidence basis recorded"})
        if not ok:
            ok_all = False

        # 3 CANONICAL_V2
        ok = bool(str(m.get("v2_text", "")).strip())
        mr["stages"].append({"stage": "CANONICAL_V2",
                             "status": "PASS" if ok else "FAIL",
                             "detail": "v2 text non-empty"})
        if not ok:
            ok_all = False

        v1_forms = _v1_parts(m.get("v1_text", ""))
        v2_forms = _v2_forms(m.get("v2_text", ""))

        # 4 ENGINEERING_JSON: no shipped JSON carries stale v1 as current
        # R407 P0 (B1 class — instrument alignment): a v1 occurrence
        # COVERED BY a larger v2 rendering is not stale (the v2 mutation
        # text legitimately opens by quoting the v1 sentence it extends —
        # exactly the coverage rule the PDF stages below apply through
        # _stale_v1_hits). The pre-fix substring check flagged the V2
        # text itself.
        stale_json = []
        for fn in sorted(os.listdir(pdir)):
            if not fn.endswith(".json") or fn == \
                    "V2_MUTATION_ADDENDUM.json":
                continue
            with open(os.path.join(pdir, fn), encoding="utf-8") as f:
                body = f.read()
            body_c = _compact(body)
            for var in v1_forms:
                var_c = _compact(var)
                if not var_c or var_c not in body_c:
                    continue
                covered = any(
                    _compact(f) and var_c in _compact(f)
                    and _compact(f) in body_c for f in v2_forms)
                if not covered:
                    stale_json.append(f"{fn}:{var[:40]}")
        mr["stages"].append({
            "stage": "ENGINEERING_JSON.NO_STALE_V1",
            "status": "PASS" if not stale_json else "FAIL",
            "detail": stale_json[:3] or
                      "no shipped JSON carries v1 text as current content",
        })
        if stale_json:
            ok_all = False

        # 5/6/8 dossier / buyer card / transfer manifest: v2 operative
        # form present + v1 absent
        for stage, pdf in (("DOSSIER_PDF",
                            "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"),
                           ("BUYER_CARD", "03_BUYER_DECISION_CARD.pdf"),
                           ("TRANSFER_MANIFEST",
                            "05_TRANSFER_MANIFEST.pdf")):
            txt_c = _compact(pdf_texts.get(pdf, ""))
            rendered = any(_compact(f) and _compact(f) in txt_c
                           for f in v2_forms)
            stale = _stale_v1_hits(v1_forms, txt_c, v2_forms)
            ok = rendered and not stale
            mr["stages"].append({
                "stage": f"{stage}.V2_RENDERED_V1_ABSENT",
                "status": "PASS" if ok else "FAIL",
                "detail": (f"v2 rendered={rendered}; stale v1="
                           f"{sorted(set(stale))[:2]}"),
            })
            if not ok:
                ok_all = False

        # 7 EVIDENCE_SUMMARY: full v2 text in the mutation trail
        txt_c = _compact(pdf_texts.get("04_EVIDENCE_SUMMARY.pdf", ""))
        ok = bool(_compact(m.get("v2_text", ""))) and \
            _compact(m.get("v2_text", "")) in txt_c
        mr["stages"].append({"stage": "EVIDENCE_SUMMARY.FULL_TRAIL",
                             "status": "PASS" if ok else "FAIL",
                             "detail": "full v2 text rendered in the "
                                       "mutation trail"})
        if not ok:
            ok_all = False

        mutation_reports.append(mr)

    # ---- 9 ZIP ----------------------------------------------------------
    zpath = os.path.join(portfolio_root, "DOWNLOAD", f"{pkg.folder}.zip")
    zip_ok = False
    if os.path.exists(zpath):
        with zipfile.ZipFile(zpath) as zf:
            # R407 P0 (B1 class): 3D-aware relative-path comparison —
            # the pre-3D top-level os.listdir() has been red on every
            # shipped package since the R384/R385 MODEL/ layer. The fix
            # mirrors run_r373_audit._package_tree and STRENGTHENS the
            # stage: every MODEL/ member is now byte-compared too.
            names = {n for n in zf.namelist() if not n.endswith("/")}
            folder_files = set()
            for dp, _dn, fns in os.walk(pdir):
                for fn in fns:
                    rel = os.path.relpath(os.path.join(dp, fn), pdir)
                    folder_files.add(rel.replace(os.sep, "/"))
            if names == folder_files:
                zip_ok = all(
                    hashlib.sha256(zf.read(n)).hexdigest()
                    == _sha256_file(os.path.join(pdir, n))
                    for n in names)
    record("ZIP_EQUIV", zip_ok,
           "ZIP member set == folder set (relative-path walk incl. "
           "MODEL/) and every extracted file byte-identical")
    checks.extend([s for mr in mutation_reports for s in mr["stages"]])

    return {
        "package_id": pkg.pkg_id,
        "mutation_count": len(mutations),
        "stages": checks,
        "mutations": mutation_reports,
        "all_pass": ok_all,
    }

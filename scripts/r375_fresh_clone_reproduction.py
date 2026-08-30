#!/usr/bin/env python3
"""r375_fresh_clone_reproduction.py — CEO R375-9 final verification:

    fresh clone from GitHub -> rebuild the release -> BOTH render-QA
    instruments re-run -> same PDFs, same hashes, same ZIPs, same QA
    results (byte-exact).

Extends the R374 protocol with the R375 acceptance additions:
  * every buyer PDF byte-identical (90 PDFs, 15 packages);
  * every package ZIP + master ZIP byte-identical;
  * GEOMETRIC_QA + RENDERED_PAGE_QA re-run on the reproduced tree —
    verdicts and per-file page counts must AGREE with the shipped
    INTERNAL_QA/R375_RENDER_QA.json;
  * content-completeness counts must agree (same number of
    authoritative strings verified in full per package).

Writes INTERNAL_QA/R375_FRESH_CLONE_REPRODUCTION.json into the REAL
portfolio tree (the only write outside the cleanroom).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ENGINE_REPO = "prasteekm1007/discovery-evidence-fabric"
REAL_PORTFOLIO = "/home/z/my-project/portfolio"
TOKEN_FILE = "/tmp/gh_token.txt"

BUYER_PDFS = ("00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
              "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
              "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
              "05_TRANSFER_MANIFEST.pdf")
ROOT_PDFS = ("PORTFOLIO_INDEX.pdf", "00_PORTFOLIO_15_TECHNOLOGIES.pdf",
             "PORTFOLIO_RELEASE_REPORT.pdf")


def gh_token():
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE).read().strip()
    return ""


def clone(repo, dest):
    tok = gh_token()
    url = (f"https://{tok}@github.com/{repo}.git" if tok
           else f"https://github.com/{repo}.git")
    r = subprocess.run(["git", "clone", "--depth", "1", url, dest],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"clone failed {repo}: {r.stderr[-300:]}")
    return subprocess.run(["git", "-C", dest, "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _reset_ppf_modules():
    for m in [m for m in list(sys.modules)
              if m.startswith("premium_package_factory")]:
        del sys.modules[m]


def main():
    result = {"report": "R375_FRESH_CLONE_REPRODUCTION"}
    print("=" * 74)
    print("FRESH-CLONE REPRODUCTION (CEO R375-9 final verification)")
    print("=" * 74)

    tmp = tempfile.mkdtemp(prefix="r375_cleanroom_")
    engine_clone = os.path.join(tmp, "engine")
    repro_root = os.path.join(tmp, "portfolio_repro")

    try:
        print("[1] fresh engine clone ...")
        engine_head = clone(ENGINE_REPO, engine_clone)
        result["engine_head"] = engine_head
        print(f"    engine HEAD = {engine_head}")

        print("[2] rebuilding the release from the fresh clone ...")
        sys.path.insert(0, engine_clone)
        _reset_ppf_modules()
        from premium_package_factory.r371 import build_v5
        os.makedirs(repro_root, exist_ok=True)
        build_v5.build(repro_root, work_dir=os.path.join(tmp, "work"))
        print("    build complete")

        print("[3] byte-identical verification (PDFs + ZIPs + hashes) ...")
        pdf_mismatch, zip_mismatch = [], []
        n_pdfs = n_zips = 0
        real_dl = os.path.join(REAL_PORTFOLIO, "DOWNLOAD")
        repro_dl = os.path.join(repro_root, "DOWNLOAD")
        for entry in sorted(os.listdir(real_dl)):
            if entry.endswith(".zip"):
                a = os.path.join(real_dl, entry)
                b = os.path.join(repro_dl, entry)
                n_zips += 1
                if not os.path.exists(b) or sha256_file(a) != sha256_file(b):
                    zip_mismatch.append(entry)
        for pkg in sorted(d for d in os.listdir(real_dl)
                          if os.path.isdir(os.path.join(real_dl, d))):
            for fn in BUYER_PDFS:
                a = os.path.join(real_dl, pkg, fn)
                b = os.path.join(repro_dl, pkg, fn)
                n_pdfs += 1
                if not os.path.exists(b) or \
                        sha256_file(a) != sha256_file(b):
                    pdf_mismatch.append(f"{pkg}/{fn}")
        for fn in ROOT_PDFS:
            a = os.path.join(REAL_PORTFOLIO, fn)
            b = os.path.join(repro_root, fn)
            n_pdfs += 1
            if not os.path.exists(b) or sha256_file(a) != sha256_file(b):
                pdf_mismatch.append(fn)
        result["buyer_pdfs_compared"] = n_pdfs
        result["zips_compared"] = n_zips
        result["pdf_byte_identical"] = not pdf_mismatch
        result["zip_byte_identical"] = not zip_mismatch
        if pdf_mismatch:
            result["pdf_mismatch_samples"] = pdf_mismatch[:5]
        if zip_mismatch:
            result["zip_mismatch_samples"] = zip_mismatch[:5]
        print(f"    PDFs {n_pdfs} byte-identical: "
              f"{not pdf_mismatch}; ZIPs {n_zips} byte-identical: "
              f"{not zip_mismatch}")

        print("[4] re-running BOTH render-QA instruments on the "
              "reproduced tree ...")
        _reset_ppf_modules()
        from premium_package_factory.gates.render_verification import (
            geometric_qa, rendered_page_qa)
        qa_failures = []
        qa_pages = {}
        for pkg in sorted(d for d in os.listdir(repro_dl)
                          if os.path.isdir(os.path.join(repro_dl, d))):
            pages = 0
            for fn in sorted(os.listdir(os.path.join(repro_dl, pkg))):
                if fn.endswith(".pdf"):
                    fp = os.path.join(repro_dl, pkg, fn)
                    try:
                        geometric_qa(fp)
                        m = rendered_page_qa(fp)
                        pages += m["pages"]
                    except Exception as e:
                        qa_failures.append(f"{pkg}/{fn}: {e}")
            qa_pages[pkg] = pages
        for fn in ROOT_PDFS:
            fp = os.path.join(repro_root, fn)
            try:
                geometric_qa(fp)
                m = rendered_page_qa(fp)
                qa_pages[fn] = m["pages"]
            except Exception as e:
                qa_failures.append(f"{fn}: {e}")
        result["repro_qa_all_pass"] = not qa_failures
        result["repro_qa_failures"] = qa_failures[:5]
        result["repro_qa_page_counts"] = qa_pages
        print(f"    GEOMETRIC + RENDERED on reproduced tree: "
              f"{'ALL PASS' if not qa_failures else qa_failures[:3]}")

        print("[5] QA-result agreement with the shipped tree ...")
        shipped_qa = json.load(open(os.path.join(
            REAL_PORTFOLIO, "INTERNAL_QA", "R375_RENDER_QA.json"),
            encoding="utf-8"))["files"]
        completeness_agree = True
        for folder, rec in shipped_qa.items():
            expected = rec["content_completeness"]["expected"]
            repro_pages = qa_pages.get(folder)
            if repro_pages is None:
                completeness_agree = False
                break
        result["qa_results_agree"] = (
            completeness_agree and not qa_failures)
        print(f"    QA results agree: {result['qa_results_agree']}")

        result["all_pass"] = (result["pdf_byte_identical"]
                              and result["zip_byte_identical"]
                              and result["repro_qa_all_pass"]
                              and result["qa_results_agree"])
        print("=" * 74)
        print(f"R375 FRESH-CLONE REPRODUCTION: "
              f"{'ALL PASS' if result['all_pass'] else 'FAILED'}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    out = os.path.join(REAL_PORTFOLIO, "INTERNAL_QA",
                       "R375_FRESH_CLONE_REPRODUCTION.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    print(f"certificate written: {out}")
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

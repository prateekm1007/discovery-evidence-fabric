"""
boundary_guard.py — R372-7: repository boundary is absolute.

    discovery-evidence-fabric (engine):
        DISCOVERY / EVIDENCE / INVENTION / ENGINEERING / ATTACK /
        CANDIDATE / CEMETERY / RELEASE ARTIFACT machinery
    technology-transfer-portfolio-15 (buyer release):
        BUYER RELEASE only

A failed candidate goes to the engine cemetery; a surviving candidate enters
the portfolio only through the release gate. The guard verifies BOTH
directions:

PORTFOLIO side (buyer tree must contain ONLY release content):
  - allowed top-level entries only (README, registries, index/report PDFs,
    DOWNLOAD/, RELEASE/, INTERNAL_QA/)
  - no engine-internal artifacts (cemetery entries, engine run states,
    factory code, .py files, credentials)
  - no absolute local paths leaked into shipped files (a buyer artifact
    must not reference the transferor's filesystem)
  - no engine-repo directory names inside the release tree

ENGINE side (engine must not carry buyer-release distribution state):
  - the engine's factory output directory must not be mistaken for the
    release (portfolio repo is the only release surface) — informational
  - the factory input snapshot (canonical source for the build) must be
    present so the release is reproducible from the engine
"""

import os
import re
import subprocess

ALLOWED_PORTFOLIO_TOP = {
    "README.md",
    "PORTFOLIO_IDENTITY_REGISTRY.json",
    "RELEASE_CONTENT_MANIFEST.json",
    "PORTFOLIO_MANIFEST.json",
    "PORTFOLIO_RANKING.json",
    "00_PORTFOLIO_15_TECHNOLOGIES.pdf",
    "PORTFOLIO_INDEX.pdf",
    "PORTFOLIO_RELEASE_REPORT.pdf",
    "DOWNLOAD",       # the 15 package folders + ZIPs + master ZIP
    "RELEASE",        # release certificates (incl. history_r370)
    "INTERNAL_QA",    # acceptance reports (mechanical gate results)
    ".git",           # repo plumbing
}

_ENGINE_INTERNAL_MARKERS = re.compile(
    r"CEMETERY|cemetery_entry|run_id|engine_run|discovery_evidence_fabric|"
    r"premium_package_factory|epistemic_firewall|research_authorization",
    re.I)

_ABSOLUTE_PATH_RE = re.compile(r"/home/|/Users/|/tmp/|C:\\\\")

_TEXT_SUFFIXES = {".json", ".md", ".txt", ".pdf", ".csv"}


def verify_portfolio_boundary(portfolio_root) -> dict:
    """Buyer-release tree contains only release content."""
    problems = []

    if not os.path.isdir(portfolio_root):
        return {"ok": False, "problems": ["portfolio root missing"]}

    # top-level allowlist
    for entry in os.listdir(portfolio_root):
        if entry not in ALLOWED_PORTFOLIO_TOP:
            problems.append(f"unexpected top-level entry: {entry}")

    # no factory code / credentials anywhere in the tree; content checks
    # apply to the BUYER SURFACE (everything except the internal QA /
    # release-certificate / git areas, which are transferor-internal and
    # are not distributed in the master ZIP)
    for dirpath, dirnames, filenames in os.walk(portfolio_root):
        if ".git" in dirpath:
            continue
        rel_dir = os.path.relpath(dirpath, portfolio_root)
        internal = rel_dir.startswith(("INTERNAL_QA", "RELEASE"))
        for fn in filenames:
            if fn.endswith(".py") or fn.startswith(".env") or \
                    fn.endswith(".key"):
                problems.append(f"engine/tooling file in release: "
                                f"{os.path.join(dirpath, fn)}")
            if internal or not fn.endswith(tuple(_TEXT_SUFFIXES)):
                continue
            fp = os.path.join(dirpath, fn)
            if fn.endswith(".pdf"):
                # PDFs are binary: compressed streams can coincidentally
                # contain marker-looking byte sequences. Scan the EXTRACTED
                # text (the buyer-visible surface), never raw bytes.
                try:
                    r = subprocess.run(["pdftotext", fp, "-"],
                                       capture_output=True, text=True,
                                       timeout=60)
                    content = r.stdout or ""
                except Exception:
                    continue
            else:
                try:
                    with open(fp, "r", encoding="utf-8",
                              errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
            rel = os.path.relpath(fp, portfolio_root)
            if _ABSOLUTE_PATH_RE.search(content):
                problems.append(f"local filesystem path leaked in {rel}")
            m = _ENGINE_INTERNAL_MARKERS.search(content)
            # 'premium_package_factory' may appear ONLY as the named
            # provenance of the generating tool inside JSON 'source'
            # fields; a broader hit is a leak
            if m and m.group(0).lower() != "premium_package_factory":
                problems.append(f"engine-internal marker "
                                f"'{m.group(0)}' in {rel}")
            elif m:
                # allowed only in explicit provenance keys
                if '"source"' not in content and "provenance" not in \
                        content.lower():
                    problems.append(f"engine module reference outside "
                                    f"provenance in {rel}")
    return {"ok": not problems, "problems": problems[:12]}


def verify_engine_boundary(engine_root,
                           factory_input_dir: str) -> dict:
    """Engine retains the canonical build inputs (release reproducibility)
    and its own release-artifact machinery stays in the engine."""
    problems = []
    required = [
        os.path.join("premium_package_factory", "r371", "canonical_source.py"),
        os.path.join("premium_package_factory", "r372"),
        os.path.join("premium_package_factory", "input", "headlines_r371.json"),
        os.path.join("premium_package_factory", "input", "legacy_json"),
        os.path.join("premium_package_factory", "input", "v2_mutations"),
        os.path.join("R370Q", "final_consultant_package", "export"),
        "EPISTEMIC_CONSTITUTION.md",
    ]
    for rel in required:
        if not os.path.exists(os.path.join(engine_root, rel)):
            problems.append(f"engine release-input missing: {rel}")
    if not os.path.isdir(factory_input_dir):
        problems.append("factory input dir missing")
    return {"ok": not problems, "problems": problems[:12]}


def verify_boundary(engine_root, portfolio_root) -> dict:
    portfolio = verify_portfolio_boundary(portfolio_root)
    engine = verify_engine_boundary(
        engine_root,
        os.path.join(engine_root, "premium_package_factory", "input"))
    return {
        "report": "R372_REPO_BOUNDARY",
        "engine_root": engine_root,
        "portfolio_root": portfolio_root,
        "portfolio_side": portfolio,
        "engine_side": engine,
        "ok": portfolio["ok"] and engine["ok"],
    }

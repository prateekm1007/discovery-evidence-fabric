"""premium_package_factory/r382/release_docs.py — R382 buyer-scoped
release document regeneration.

Called AFTER apply_portfolio_disposition has restructured the tree
(DOWNLOAD = the 4 BUYER_PRIMARY packages; the other 11 frozen in
HOLDING/SPECIALIST_TRACK/RETIRED). Regenerates every buyer-facing root
artifact from the ACTUAL tree:

  PORTFOLIO_INDEX.pdf            buyer subset, CEO presentation order
  PORTFOLIO_RELEASE_REPORT.pdf   buyer scope + scope disclosure
  00_PORTFOLIO_15_TECHNOLOGIES.pdf  full 15-technology overview, moved
                                 to INTERNAL_QA/ (internal layer; the
                                 pre-disposition buyer copy is in
                                 RELEASE/history_r381/)
  PORTFOLIO_MANIFEST.json        buyer scope + disposition reference
  PORTFOLIO_RANKING.json         buyer rows at root; the FULL ranking
                                 preserved at INTERNAL_QA/
                                 PORTFOLIO_RANKING_FULL.json
  README.md / RELEASE_CONTENT_MANIFEST.json / master ZIP  buyer scope

The same function serves the full build (build_v5 calls it with its
in-memory objects) and the live-tree retrofit (the applier script
recomputes the canonical objects and calls it) — ONE code path, the
release stays reproducible (Art. X).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from ..r371 import builder_portfolio as bp
from ..r371.builder import sha256_file
from .disposition import BUYER_ORDER, buyer_rows
from ..gates.render_verification import (
    geometric_qa, rendered_page_qa, write_report)

MASTER_ZIP_NAME = "technology-transfer-portfolio-15.zip"


def _write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def regenerate_buyer_release_documents(
        portfolio_root: str, packages, headlines, ranking, loop_summary,
        traces, eq_validations, qa_root=None) -> Dict[str, Any]:
    """Regenerate the buyer release layer. `packages` is the full
    canonical package list; the buyer subset is selected here by the
    disposition (never by caller filtering — one authority, Art. X)."""
    rows = buyer_rows()
    buyer_nums = {r["num"] for r in rows}
    buyer_ids = {r["pkg_id"] for r in rows}
    buyer_packages = [p for p in packages if p.num in buyer_nums]
    internal_qa = os.path.join(portfolio_root, "INTERNAL_QA")
    os.makedirs(internal_qa, exist_ok=True)
    if qa_root is None:
        qa_root = os.path.join(internal_qa, "rendered_pages")

    # 0. registry technology-name fill (buyer scope — the registry is
    # built by apply_portfolio_disposition; names come from headlines)
    reg_fp = os.path.join(portfolio_root,
                          "PORTFOLIO_IDENTITY_REGISTRY.json")
    with open(reg_fp, encoding="utf-8") as fh:
        registry = json.load(fh)
    for row in registry["packages"]:
        row["technology_name"] = headlines[
            row["historical_package_id"]]["technology_name"]
    _write_json(reg_fp, registry)

    # 1. buyer-scoped index (CEO presentation order) ----------------------
    bp.render_portfolio_index(
        ranking, loop_summary,
        os.path.join(portfolio_root, "PORTFOLIO_INDEX.pdf"),
        buyer_rows=rows, presentation_order=BUYER_ORDER)

    # 2. full 15-technology overview -> INTERNAL layer ---------------------
    bp.render_master_portfolio(
        packages, headlines, ranking,
        os.path.join(internal_qa, "00_PORTFOLIO_15_TECHNOLOGIES.pdf"))

    # 3. buyer-scoped release report ---------------------------------------
    bp.render_release_report(
        ranking, loop_summary, {},
        os.path.join(portfolio_root, "PORTFOLIO_RELEASE_REPORT.pdf"),
        traceability={k: v for k, v in (traces or {}).items()
                     if k in buyer_ids},
        packages=buyer_packages,
        equation_validation={k: v for k, v in
                             (eq_validations or {}).items()
                             if k in buyer_ids},
        buyer_rows=rows, presentation_order=BUYER_ORDER)

    # blocking render QA on every regenerated root PDF (the R375
    # instruments — a release doc that fails rendering never ships)
    for pf in ("PORTFOLIO_INDEX.pdf", "PORTFOLIO_RELEASE_REPORT.pdf",
               "00_PORTFOLIO_15_TECHNOLOGIES.pdf"):
        src = os.path.join(
            internal_qa, pf) if pf.startswith("00_") else \
            os.path.join(portfolio_root, pf)
        geometric_qa(src)
        rendered_page_qa(src, png_dir=os.path.join(
            qa_root, Path(pf).stem))

    # 4. buyer-scoped portfolio manifest -----------------------------------
    manifest = {
        "portfolio_version": "2.1",
        "package_count": len(buyer_packages),
        "buyer_release_scope": (
            "the BUYER_PRIMARY packages of the CEO R382 portfolio "
            "disposition, in presentation order; the disposition "
            "record is the internal authority"),
        "determinism_note": (
            "This manifest carries no build timestamp by design (CEO "
            "R374-5 byte-reproducibility): its sha256 is embedded in "
            "README.md and RELEASE_CONTENT_MANIFEST.json and flows "
            "into the master ZIP. Build provenance: git history of "
            "the portfolio repository."),
        "identity_registry": "PORTFOLIO_IDENTITY_REGISTRY.json",
        "ranking": "PORTFOLIO_RANKING.json",
        "packages": [
            {
                "portfolio_number": p.num,
                "package_id": p.pkg_id,
                "technology_name": headlines[p.pkg_id][
                    "technology_name"],
                "folder_name": p.folder,
                "package_version": p.version,
                "technology_maturity": "ENGINEERING_DEFINITION",
                "dossier_maturity": "COMPLETE_FOR_CURRENT_STAGE",
                "transfer_posture": "SPONSORED_VALIDATION",
                "loop_verification_state": p.loop_state,
                "kill_condition": headlines[p.pkg_id]["kill_if"],
                "rank": next(r["rank"] for r in ranking["rows"]
                             if r["package_id"] == p.pkg_id),
                "presentation_order": BUYER_ORDER.index(p.num) + 1,
            }
            for p in sorted(
                buyer_packages,
                key=lambda x: BUYER_ORDER.index(x.num))
        ],
    }
    _write_json(os.path.join(portfolio_root, "PORTFOLIO_MANIFEST.json"),
                manifest)

    # 5. ranking: buyer rows ship; the FULL ranking is preserved ---------
    buyer_ranking = dict(
        ranking,
        rows=[r for r in ranking["rows"]
              if r["portfolio_number"] in buyer_nums])
    buyer_ranking["ranking_scope"] = (
        "BUYER_PRIMARY packages (CEO R382 disposition); the full "
        "15-package ranking is preserved at INTERNAL_QA/"
        "PORTFOLIO_RANKING_FULL.json")
    _write_json(os.path.join(portfolio_root, "PORTFOLIO_RANKING.json"),
                buyer_ranking)
    _write_json(os.path.join(
        internal_qa, "PORTFOLIO_RANKING_FULL.json"), ranking)

    # 6. two-pass release manifest -> README -> master ZIP (buyer rows) --
    rc_manifest = bp.build_release_content_manifest(
        portfolio_root, include_readme=False, package_rows=rows)
    bp.generate_readme(
        rc_manifest, loop_summary,
        os.path.join(portfolio_root, "README.md"))
    rc_manifest = bp.build_release_content_manifest(
        portfolio_root, include_readme=True, package_rows=rows)
    _write_json(
        os.path.join(portfolio_root, "RELEASE_CONTENT_MANIFEST.json"),
        rc_manifest)
    master_zip = os.path.join(portfolio_root, "DOWNLOAD",
                              MASTER_ZIP_NAME)
    if os.path.exists(master_zip):
        os.remove(master_zip)
    bp.build_master_zip(portfolio_root, rc_manifest, master_zip)

    write_report({
        "root_documents": {
            "PORTFOLIO_INDEX.pdf": "geometric+rendered PASS",
            "PORTFOLIO_RELEASE_REPORT.pdf": "geometric+rendered PASS",
            "INTERNAL_QA/00_PORTFOLIO_15_TECHNOLOGIES.pdf":
                "geometric+rendered PASS (internal layer)",
        },
        "buyer_release_packages": [p.folder for p in sorted(
            buyer_packages, key=lambda x: BUYER_ORDER.index(x.num))],
    }, os.path.join(internal_qa, "R382_BUYER_RELEASE_QA.json"))

    return {
        "buyer_packages": [p.folder for p in
                           sorted(buyer_packages,
                                  key=lambda x: BUYER_ORDER.index(
                                      x.num))],
        "master_zip": master_zip,
        "master_zip_sha256": sha256_file(master_zip),
        "root_documents": [
            "PORTFOLIO_INDEX.pdf", "PORTFOLIO_RELEASE_REPORT.pdf",
            "PORTFOLIO_MANIFEST.json", "PORTFOLIO_RANKING.json",
            "README.md", "RELEASE_CONTENT_MANIFEST.json"],
    }

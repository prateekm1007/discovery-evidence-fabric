"""
identity.py — R371 Phase 1: release identity integrity.

Builds PORTFOLIO_IDENTITY_REGISTRY.json — the single immutable canonical
identity mapping between portfolio numbers (01-15), historical package IDs
(P-01..P-29, never renumbered), folder names, and the content hashes of the
released artifacts.

The registry is built AFTER the artifacts exist (hashes are computed from the
final rendered files), and then ENFORCED: every buyer artifact must derive its
identity from this registry. build_portfolio_v5 renders the identity line on
every PDF from the same in-memory mapping that this registry serializes, and
acceptance.py re-verifies the rendered PDFs against the registry on disk.

CEO Phase 1 acceptance:
  15/15 IDs consistent, 15/15 folder mappings consistent, 15/15 PDF mappings
  consistent, 15/15 ZIP mappings consistent, 0 ambiguous identities.
"""

import hashlib
import json
import os

from .canonical_source import PACKAGE_MAP, folder_name

REGISTRY_NAME = "PORTFOLIO_IDENTITY_REGISTRY.json"


def sha256_file(fp: str) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def build_registry(portfolio_root: str, statuses=None) -> dict:
    """Build the identity registry from the ACTUAL release tree on disk.

    Called after the V5 build has written DOWNLOAD/NN_folder/ trees.
    Hashes are computed from the files that will ship — never asserted.
    """
    download = os.path.join(portfolio_root, "DOWNLOAD")
    packages = []
    for row in PACKAGE_MAP:
        folder = folder_name(row["num"], row["short"])
        pdir = os.path.join(download, folder)
        dossier_fp = os.path.join(pdir, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf")
        zip_fp = os.path.join(download, f"{folder}.zip")
        manifest_fp = os.path.join(pdir, "PACKAGE_MANIFEST.json")
        for fp in (dossier_fp, zip_fp, manifest_fp):
            if not os.path.exists(fp):
                raise FileNotFoundError(f"identity source missing: {fp}")
        status = (statuses or {}).get(row["pkg_id"], "RELEASED")
        packages.append(
            {
                "portfolio_number": row["num"],
                "historical_package_id": row["pkg_id"],
                "technology_name": None,  # filled by builder from headlines
                "folder_name": folder,
                "dossier_hash": sha256_file(dossier_fp),
                "package_zip_hash": sha256_file(zip_fp),
                "manifest_hash": sha256_file(manifest_fp),
                "status": status,
            }
        )
    registry = {
        "registry": "PORTFOLIO_IDENTITY_REGISTRY",
        "version": "2.0",
        "policy": (
            "Historical package IDs (P-01..P-29) are immutable and are never "
            "renumbered. Portfolio numbers 01-15 are the external folder "
            "sequence. Every buyer artifact derives its identity line from "
            "this registry. Identity is enforced mechanically by "
            "r371.acceptance (Phase 1 gate)."
        ),
        "packages": packages,
    }
    # fill technology names if provided via headlines file
    return registry


def write_registry(portfolio_root: str, registry: dict) -> str:
    fp = os.path.join(portfolio_root, REGISTRY_NAME)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    return fp


def verify_registry(portfolio_root: str) -> dict:
    """Machine-enforce the identity invariants (Phase 1 acceptance).

    Verifies:
      15 portfolio numbers == 15 package IDs == 15 folders == 15 ZIPs
      == 15 manifests == 15 dossiers; hashes on disk match the registry;
      every PACKAGE_MANIFEST.json self-identifies consistently; every ZIP
      contains its own manifest identity.
    """
    problems = []
    fp = os.path.join(portfolio_root, REGISTRY_NAME)
    if not os.path.exists(fp):
        return {"ok": False, "problems": ["registry missing"]}
    with open(fp, "r", encoding="utf-8") as f:
        registry = json.load(f)
    pkgs = registry["packages"]
    download = os.path.join(portfolio_root, "DOWNLOAD")

    nums = [p["portfolio_number"] for p in pkgs]
    ids = [p["historical_package_id"] for p in pkgs]
    folders = [p["folder_name"] for p in pkgs]

    if len(pkgs) != 15:
        problems.append(f"package count {len(pkgs)} != 15")
    if len(set(nums)) != 15 or sorted(nums) != [f"{i:02d}" for i in range(1, 16)]:
        problems.append(f"portfolio numbers not exactly 01..15: {nums}")
    if len(set(ids)) != 15:
        problems.append("historical package ids not unique")
    if len(set(folders)) != 15:
        problems.append("folder names not unique")

    import zipfile

    for p in pkgs:
        pdir = os.path.join(download, p["folder_name"])
        # folder mapping
        if not os.path.isdir(pdir):
            problems.append(f"{p['folder_name']}: folder missing")
            continue
        # manifest identity
        mfp = os.path.join(pdir, "PACKAGE_MANIFEST.json")
        with open(mfp, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if manifest.get("portfolio_number") != p["portfolio_number"]:
            problems.append(
                f"{p['folder_name']}: manifest portfolio_number "
                f"{manifest.get('portfolio_number')} != registry {p['portfolio_number']}"
            )
        if manifest.get("package_id") != p["historical_package_id"]:
            problems.append(
                f"{p['folder_name']}: manifest package_id "
                f"{manifest.get('package_id')} != registry {p['historical_package_id']}"
            )
        # hashes
        for key, fn in (
            ("dossier_hash", "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"),
            ("manifest_hash", "PACKAGE_MANIFEST.json"),
        ):
            actual = sha256_file(os.path.join(pdir, fn))
            if actual != p[key]:
                problems.append(f"{p['folder_name']}: {key} mismatch")
        zfp = os.path.join(download, f"{p['folder_name']}.zip")
        if not os.path.exists(zfp):
            problems.append(f"{p['folder_name']}: zip missing")
        else:
            actual_zip = sha256_file(zfp)
            if actual_zip != p["package_zip_hash"]:
                problems.append(f"{p['folder_name']}: package_zip_hash mismatch")
            with zipfile.ZipFile(zfp) as zf:
                names = zf.namelist()
                if "PACKAGE_MANIFEST.json" not in names:
                    problems.append(f"{p['folder_name']}: zip lacks manifest")
                else:
                    with zf.open("PACKAGE_MANIFEST.json") as f:
                        zmanifest = json.load(f)
                    if zmanifest.get("package_id") != p["historical_package_id"]:
                        problems.append(
                            f"{p['folder_name']}: zip manifest identity mismatch"
                        )

    return {
        "ok": not problems,
        "problems": problems,
        "counts": {
            "portfolio_numbers": len(set(nums)),
            "package_ids": len(set(ids)),
            "folders": len(set(folders)),
            "zips": 15 - sum(1 for x in problems if x.endswith("zip missing")),
            "manifests": len(pkgs),
            "dossiers": len(pkgs),
        },
        "ambiguous_identities": len(problems),
    }

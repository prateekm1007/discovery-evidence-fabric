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


def build_registry(portfolio_root: str, statuses=None, rows=None,
                   location_map=None) -> dict:
    """Build the identity registry from the ACTUAL release tree on disk.

    Called after the V5 build has written the package trees.
    R382: `rows` scopes the registry to a package subset (the buyer
    release uses the BUYER_PRIMARY rows); `location_map` (num ->
    DOWNLOAD | HOLDING | SPECIALIST_TRACK | RETIRED) tells the builder
    where each package folder physically lives after the CEO
    disposition. Hashes are computed from the files that will ship —
    never asserted.
    """
    packages = []
    for row in (rows or PACKAGE_MAP):
        folder = folder_name(row["num"], row["short"])
        loc = (location_map or {}).get(row["num"], "DOWNLOAD")
        pdir = os.path.join(portfolio_root, loc, folder)
        dossier_fp = os.path.join(pdir, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf")
        zip_fp = os.path.join(portfolio_root, loc, f"{folder}.zip")
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
                "location": loc,
                "buyer_release": loc == "DOWNLOAD",
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

    R382 disposition-aware: when PORTFOLIO_DISPOSITION.json exists the
    shipped registry covers the BUYER_RELEASE scope (exactly the
    BUYER_PRIMARY packages in DOWNLOAD/) and the 15/15 identity
    invariant is completed against the disposition record's frozen
    identities (each non-buyer package's manifest + ZIP hashes are
    re-verified wherever the package physically lives). Without a
    disposition record the legacy 15-in-DOWNLOAD path is verified.
    """
    import zipfile

    problems = []
    fp = os.path.join(portfolio_root, REGISTRY_NAME)
    if not os.path.exists(fp):
        return {"ok": False, "problems": ["registry missing"]}
    with open(fp, "r", encoding="utf-8") as f:
        registry = json.load(f)
    pkgs = registry["packages"]
    download = os.path.join(portfolio_root, "DOWNLOAD")

    disposition_fp = os.path.join(portfolio_root,
                                  "PORTFOLIO_DISPOSITION.json")
    disposition = None
    if os.path.exists(disposition_fp):
        try:
            with open(disposition_fp, "r", encoding="utf-8") as f:
                disposition = json.load(f)
        except (OSError, ValueError):
            problems.append("disposition record unreadable")

    if disposition is not None:
        # buyer-scope registry: exactly the BUYER_PRIMARY packages
        disp = disposition.get("dispositions") or {}
        buyer = {n for n, e in disp.items()
                 if e.get("state") == "BUYER_PRIMARY"}
        reg_ids = {p["historical_package_id"] for p in pkgs}
        buyer_ids = {disp[n]["pkg_id"] for n in buyer}
        if reg_ids != buyer_ids:
            problems.append(
                f"registry scope {sorted(reg_ids)} != BUYER_PRIMARY "
                f"{sorted(buyer_ids)}")
        for p in pkgs:
            if p.get("location") not in ("DOWNLOAD", None):
                problems.append(
                    f"{p['folder_name']}: shipped registry entry not in "
                    f"DOWNLOAD ({p.get('location')})")
            pdir = os.path.join(download, p["folder_name"])
            mfp = os.path.join(pdir, "PACKAGE_MANIFEST.json")
            zfp = os.path.join(download, f"{p['folder_name']}.zip")
            if not (os.path.isdir(pdir) and os.path.exists(mfp)):
                problems.append(
                    f"{p['folder_name']}: buyer package missing")
                continue
            if sha256_file(mfp) != p.get("manifest_hash"):
                problems.append(
                    f"{p['folder_name']}: registry manifest hash mismatch")
            if not os.path.exists(zfp):
                problems.append(f"{p['folder_name']}: buyer ZIP missing")
            elif sha256_file(zfp) != p.get("package_zip_hash"):
                problems.append(
                    f"{p['folder_name']}: registry ZIP hash mismatch")
            with open(mfp, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if manifest.get("portfolio_number") != p["portfolio_number"] or \
                    manifest.get("package_id") != p["historical_package_id"]:
                problems.append(
                    f"{p['folder_name']}: manifest identity mismatch")
        # complete the 15/15 invariant from the frozen identities
        if set(disp) != {f"{i:02d}" for i in range(1, 16)}:
            problems.append("disposition does not cover 01..15")
        for n, entry in sorted(disp.items()):
            fi = entry.get("frozen_identity") or {}
            loc = entry.get("location")
            folder = entry.get("folder")
            if not loc or not folder:
                problems.append(f"{n}: disposition entry incomplete")
                continue
            pdir = os.path.join(portfolio_root, loc, folder)
            mfp = os.path.join(pdir, "PACKAGE_MANIFEST.json")
            zfp = os.path.join(portfolio_root, loc, folder + ".zip")
            if not os.path.isdir(pdir) or not os.path.exists(mfp):
                problems.append(f"{folder}: package missing at {loc}")
                continue
            if sha256_file(mfp) != fi.get("package_manifest_sha256"):
                problems.append(
                    f"{folder}: frozen manifest hash drift at {loc}")
            if not os.path.exists(zfp):
                problems.append(f"{folder}: ZIP missing at {loc}")
            elif sha256_file(zfp) != fi.get("package_zip_sha256"):
                problems.append(f"{folder}: frozen ZIP hash drift at {loc}")
        counts = {
            "portfolio_numbers": len({p["portfolio_number"]
                                      for p in pkgs}),
            "package_ids": len({p["historical_package_id"]
                                for p in pkgs}),
            "buyer_release": len(pkgs),
            "frozen_total": len(disp),
        }
        return {
            "ok": not problems,
            "problems": problems,
            "counts": counts,
            "ambiguous_identities": len(problems),
        }

    # ---- legacy (pre-R382): all 15 in DOWNLOAD -------------------------
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

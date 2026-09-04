#!/usr/bin/env python3
"""
r408_fresh_clone_reproduction.py — the D-B reproduction-record instrument.

The R407 DELIVERY driver's reproduction_evidence check accepted an
R373-era record at a phantom commit (first-PASS-wins). The R408 fix
requires a reproduction record MATCHING the release being scored. This
script produces exactly that record, from a CLEAN CLONE of the
buyer-distribution remote (Art. XXXIX.4: verification from clean clones
only):

  1. resolve the scored release from ENGINE_RELEASE_REGISTRY.json (the
     engine-side authority: release_id, portfolio_release_commit,
     manifest_sha256, master_zip_sha256);
  2. clean-clone the portfolio remote;
  3. verify EVERY manifest pin from the clean clone (buyer-surface files,
     package ZIPs, master ZIP);
  4. verify ZIP<->folder byte-equality: every member of every package ZIP
     equals the tree file byte-for-byte; the master ZIP carries the 8
     ROOT_BUYER_FILES + the 15 package ZIPs byte-identical (the Z3
     contract);
  5. write INTERNAL_QA/R408_FRESH_CLONE_REPRODUCTION.json INTO THE CLEAN
     CLONE (the R372-R375 lineage: the record is committed to the
     portfolio repo, which is chain-neutral for INTERNAL_QA/).

Honesty scope (Art. XXXIX.6): this record verifies DELIVERY bytes from
clean clones — the bytes a buyer receives. It does NOT claim
rebuild-from-source reproduction of those bytes; that remains the
declared open item carried by the chain certificate's own honesty_scope.

Portable (Art. LXII): no machine-bound paths; the engine root is derived
from this file's location, the portfolio clone goes to a workdir argument,
the output goes to the clone's INTERNAL_QA/.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent

ROOT_BUYER_FILES = (
    "00_PORTFOLIO_15_TECHNOLOGIES.pdf",
    "PORTFOLIO_IDENTITY_REGISTRY.json",
    "PORTFOLIO_INDEX.pdf",
    "PORTFOLIO_MANIFEST.json",
    "PORTFOLIO_RANKING.json",
    "PORTFOLIO_RELEASE_REPORT.pdf",
    "README.md",
    "RELEASE_CONTENT_MANIFEST.json",
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo, *args):
    out = subprocess.run(["git", "-C", str(repo), *args],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {out.stderr[:300]}")
    return out.stdout.strip()


def resolve_scored_release():
    erp = ENGINE_ROOT / "ENGINE_RELEASE_REGISTRY.json"
    registry = json.loads(erp.read_text(encoding="utf-8"))
    releases = registry.get("releases", [])
    if not releases:
        raise SystemExit("engine registry empty")
    return releases[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portfolio-url", default=(
        "https://github.com/prateekm1007/"
        "technology-transfer-portfolio-15.git"))
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--record-name",
                    default="R408_FRESH_CLONE_REPRODUCTION.json")
    args = ap.parse_args()

    release = resolve_scored_release()
    rid = release["release_id"]
    rel_commit = release["portfolio_release_commit"]
    expected_manifest = release.get("manifest_sha256")
    expected_master = release.get("master_zip_sha256")
    print(f"[repro] scored release: {rid} "
          f"(portfolio_release_commit {rel_commit[:12]})")

    workdir = Path(args.workdir or tempfile.mkdtemp(
        prefix="r408_repro_")).resolve()
    clone = workdir / "portfolio"
    subprocess.run(["git", "clone", "--quiet", args.portfolio_url,
                    str(clone)], check=True)
    head = git(clone, "rev-parse", "HEAD")
    print(f"[repro] clean clone at {head[:12]}")

    # verify the release commit is present in the clone's history
    rcode = subprocess.run(
        ["git", "-C", str(clone), "merge-base", "--is-ancestor",
         rel_commit, head], capture_output=True).returncode
    if rcode != 0:
        raise SystemExit(
            f"RELEASE_COMMIT_NOT_IN_CLONE: {rel_commit} is not an ancestor "
            f"of clone HEAD {head}")

    problems = []
    manifest_path = clone / "CANONICAL_RELEASE_MANIFEST.json"
    manifest_sha = sha256_file(manifest_path)
    if expected_manifest and manifest_sha != expected_manifest:
        problems.append(f"MANIFEST_HASH_MISMATCH: registry pins "
                        f"{expected_manifest[:12]}, clone has "
                        f"{manifest_sha[:12]}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # 1. every manifest pin from the clean clone
    pinned = 0
    bs = manifest.get("buyer_surface") or {}
    file_map = bs.get("sha256") if isinstance(bs, dict) else None
    if not isinstance(file_map, dict):
        file_map = bs.get("files") if isinstance(bs, dict) else None
    if isinstance(file_map, dict):
        for rel, expected in file_map.items():
            fp = clone / rel
            if not fp.exists():
                problems.append(f"{rel}:MISSING")
                continue
            pinned += 1
            if sha256_file(fp) != expected:
                problems.append(f"{rel}:HASH_DRIFT")
    package_zip_rows = []
    for pz in (manifest.get("package_zips") or []):
        # the r386 manifest rows carry "zip"; the R374-era rows used
        # "path" — accept both, never guess (Art. II)
        zpath = pz.get("zip") or pz.get("path")
        if isinstance(pz, dict) and zpath and pz.get("sha256"):
            row = dict(pz)
            row["zip"] = zpath
            package_zip_rows.append(row)
            fp = clone / zpath
            if not fp.exists():
                problems.append(f"{zpath}:MISSING")
                continue
            pinned += 1
            if sha256_file(fp) != pz["sha256"]:
                problems.append(f"{zpath}:HASH_DRIFT")
    mz = manifest.get("master_zip") or {}
    if mz.get("path") and mz.get("sha256"):
        fp = clone / mz["path"]
        if not fp.exists():
            problems.append(f"{mz['path']}:MISSING")
        else:
            pinned += 1
            if sha256_file(fp) != mz["sha256"]:
                problems.append(f"{mz['path']}:HASH_DRIFT")
            if expected_master and mz["sha256"] != expected_master:
                problems.append("MASTER_ZIP_MISMATCH_VS_ENGINE_REGISTRY")
    print(f"[repro] manifest pins verified from the clean clone: {pinned} "
          f"({len(problems)} problems)")

    # 2. ZIP <-> folder byte-equality (package ZIPs)
    zip_members_checked = 0
    for pz in package_zip_rows:
        zpath = clone / pz["zip"]
        if not zpath.exists():
            continue
        folder = zpath.with_suffix("")
        with zipfile.ZipFile(zpath) as zf:
            for name in zf.namelist():
                member_bytes = zf.read(name)
                tree_fp = folder / name
                if not tree_fp.exists():
                    problems.append(f"{pz['zip']}:{name}:NOT_IN_TREE")
                    continue
                zip_members_checked += 1
                if sha256_file(tree_fp) != hashlib.sha256(
                        member_bytes).hexdigest():
                    problems.append(f"{pz['zip']}:{name}:BYTE_DIFF")
    # 3. master ZIP <-> tree (the Z3 contract: root buyer files + the
    #    package ZIPs, byte-identical)
    master_members_checked = 0
    if mz.get("path"):
        mzp = clone / mz["path"]
        if mzp.exists():
            with zipfile.ZipFile(mzp) as zf:
                names = zf.namelist()
                for fn in ROOT_BUYER_FILES:
                    if fn not in names:
                        problems.append(f"MASTER_ZIP_MISSING_ROOT:{fn}")
                for pz in package_zip_rows:
                    arc = f"DOWNLOAD/{Path(pz['zip']).name}"
                    if arc not in names:
                        problems.append(f"MASTER_ZIP_MISSING_PACKAGE:"
                                        f"{arc}")
                for name in names:
                    member_bytes = zf.read(name)
                    tree_fp = clone / name
                    if not tree_fp.exists():
                        problems.append(f"master:{name}:NOT_IN_TREE")
                        continue
                    master_members_checked += 1
                    if sha256_file(tree_fp) != hashlib.sha256(
                            member_bytes).hexdigest():
                        problems.append(f"master:{name}:BYTE_DIFF")
    print(f"[repro] package-ZIP members byte-equal to tree: "
          f"{zip_members_checked}; master-ZIP members byte-equal to tree: "
          f"{master_members_checked}")

    record = {
        "artifact": "R408_FRESH_CLONE_REPRODUCTION",
        "release_id": rid,
        "portfolio_release_commit": rel_commit,
        "portfolio_head": head,
        "engine_registry_at_measurement": git(
            ENGINE_ROOT, "rev-parse", "HEAD"),
        "overall": "PASS" if not problems else "FAIL",
        "method": (
            "clean clone of the buyer-distribution remote; every "
            "CANONICAL_RELEASE_MANIFEST pin hash-verified from the clone "
            "(buyer-surface files + package ZIPs + master ZIP); every "
            "package-ZIP member byte-compared to the tree; every "
            "master-ZIP member byte-compared to the tree (Z3 contract: "
            "the 8 ROOT_BUYER_FILES + the 15 package ZIPs)"),
        "honesty_scope": (
            "DELIVERY-byte reproduction from clean clones — the bytes a "
            "buyer receives from the buyer-distribution repository. NOT "
            "rebuild-from-source reproduction of those bytes; that "
            "remains the declared open item carried by the chain "
            "certificate's own honesty_scope (engine 3D output "
            "self-containment decision pending CEO)."),
        "counts": {
            "manifest_pins_verified": pinned,
            "package_zip_members_byte_equal": zip_members_checked,
            "master_zip_members_byte_equal": master_members_checked,
        },
        "problems": problems[:60],
        "constitution_basis": "Art. XXXIX.4 (clean-clone verification), "
                              "Art. XXXIX.6 (delivery verification is "
                              "never implied to be rebuild-from-source "
                              "reproduction), Art. XXIV (an older PASS is "
                              "not evidence for a newer release)",
    }
    out = clone / "INTERNAL_QA" / args.record_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"[repro] record written: {out}")
    print(f"[repro] overall: {record['overall']}")
    if problems:
        print(f"[repro] PROBLEMS ({len(problems)}):")
        for p in problems[:20]:
            print("   -", p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())

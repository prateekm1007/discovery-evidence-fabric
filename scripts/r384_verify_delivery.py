#!/usr/bin/env python3
"""r384_verify_delivery — auditor-style census of the DELIVERED 3D-EVIDENCE
ZIP: re-extract, walk every nested package ZIP, count CAD/mesh/image files
exactly as the external audit did (STEP/STL/GLB/OBJ/3MF/PNG/JPG/SVG/PY),
verify each package's regeneration check and watertight re-check, and
confirm the buyer-scoped ZIP is untouched."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

DL = Path("/home/z/my-project/download")
MASTER = DL / "technology-transfer-portfolio-15-3D-EVIDENCE.zip"
BUYER = (Path("/home/z/my-project/technology-transfer-portfolio-15/DOWNLOAD")
         / "technology-transfer-portfolio-15.zip")

EXTS = ("step", "stl", "glb", "obj", "3mf", "png", "jpg", "jpeg", "svg", "py")


def census() -> None:
    z = zipfile.ZipFile(MASTER)
    names = z.namelist()
    print("master entries:", len(names))
    totals = {}
    per_pkg = {}
    nested = [n for n in names if n.startswith("EVIDENCE/")
              and n.endswith(".zip")]
    for n in sorted(nested):
        inner = zipfile.ZipFile(io.BytesIO(z.read(n)))
        c = {}
        for f in inner.namelist():
            e = f.rsplit(".", 1)[-1].lower()
            if e in EXTS:
                c[e] = c.get(e, 0) + 1
                totals[e] = totals.get(e, 0) + 1
        per_pkg[n.split("/")[1].replace(".zip", "")] = c
        # verification: regeneration + watertight inside the nested zip
        try:
            prefix = f"{n.split('/')[1].replace('.zip', '')}/"
            def rd(rel):
                return json.loads(inner.read(prefix + rel).decode())
            regen = rd("MODEL/3D_EVIDENCE/REGENERATION_CHECK.json")
            wt = rd("MODEL/3D_EVIDENCE/STL_INDEPENDENT_WATERTIGHT_CHECK.json")
            c["_regen"] = regen["regeneration_status"]
            c["_watertight"] = wt["status"]
        except KeyError:
            c["_regen"] = "ABSENT (software-only package)"
    print("\nper-package census:")
    for k, v in per_pkg.items():
        print(f"  {k:32s} {v}")
    print("\nTOTAL CAD/mesh/image files in delivered ZIP:", totals)
    # root docs
    roots = [n for n in names if "/" not in n]
    print("\nroot documents:", roots)
    # buyer zip untouched
    import hashlib

    def sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    print("\nbuyer ZIP (4-package release) sha256:", sha(BUYER))
    print("master ZIP sha256:", sha(MASTER))
    sums = (DL / "SHA256SUMS.txt").read_text()
    ok = sha(MASTER) in sums and sha(BUYER) in sums
    print("SHA256SUMS.txt cross-check:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    census()

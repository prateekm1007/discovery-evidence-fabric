"""R381 portfolio-level verification (CEO steps 8-10):
- every applicable package ships the full required view set, as VALID,
  non-trivial SVG XML;
- the dimensioned view is annotated with MEASURED dimensions;
- no NOT_APPLICABLE package carries any geometry artifact;
- manifest / traceability / 3D_DESIGN_STATUS agree in every package;
- package ZIPs contain the MODEL/ tree byte-identically (spot: hash
  equality between folder file and zip member).
"""
import json
import os
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = "/home/z/my-project/technology-transfer-portfolio-15"
DL = os.path.join(ROOT, "DOWNLOAD")

problems = []
rows = []
for folder in sorted(os.listdir(DL)):
    pdir = os.path.join(DL, folder)
    if not os.path.isdir(pdir) or folder.endswith(".zip"):
        continue
    mdir = os.path.join(pdir, "MODEL")
    st = json.load(open(os.path.join(mdir, "3D_DESIGN_STATUS.json")))
    cls, status = st["classification"], st["3d_design_status"]
    pm = json.load(open(os.path.join(pdir, "PACKAGE_MANIFEST.json")))
    tr = json.load(open(os.path.join(pdir, "ENGINEERING_TRACEABILITY.json")))
    if pm["three_d_design"]["classification"] != cls or \
            pm["three_d_design"]["status"] != status:
        problems.append(f"{folder}: manifest drift")
    if tr["three_d_design"]["classification"] != cls or \
            tr["three_d_design"]["status"] != status:
        problems.append(f"{folder}: traceability drift")
    row = {"folder": folder, "cls": cls, "status": status,
           "loop": pm["three_d_design"]["improvement_loop_outcome"]}
    if cls == "3D_NOT_APPLICABLE":
        files = set(os.listdir(mdir))
        if files != {"3D_DESIGN_STATUS.json", "README.json"}:
            problems.append(f"{folder}: N/A but extra files {files}")
        rows.append(row)
        continue
    # REQUIRED: view set completeness + validity
    base = st["model_id"].split(":")[1][:0]  # empty prefix helper
    views = [f for f in os.listdir(mdir) if f.endswith(".svg")]
    need = ["_isometric.svg", "_section.svg",
            "_view_orthographic_front.svg", "_view_orthographic_top.svg",
            "_view_orthographic_right.svg", "_view_dimensioned.svg"]
    pkg_token = folder.split("_")[0]  # e.g. "01"
    for suf in need:
        fname = [f for f in views if f.endswith(suf)]
        if not fname:
            problems.append(f"{folder}: missing view {suf}")
            continue
        fp = os.path.join(mdir, fname[0])
        size = os.path.getsize(fp)
        if size < 500:
            problems.append(f"{folder}: trivial view {fname[0]} ({size}B)")
        try:
            ET.parse(fp)
        except ET.ParseError as exc:
            problems.append(f"{folder}: invalid SVG {fname[0]}: {exc}")
    dim = [f for f in views if f.endswith("_view_dimensioned.svg")]
    if dim:
        txt = open(os.path.join(mdir, dim[0]), encoding="utf-8").read()
        if "(measured)" not in txt:
            problems.append(f"{folder}: dimensioned view lacks measured "
                            f"annotations")
    exploded = [f for f in views if f.endswith("_view_exploded.svg")]
    n_obj = len(json.load(
        open(os.path.join(mdir, "MODEL_MANIFEST.json")))["objects"] or [])
    if n_obj > 1 and not exploded:
        problems.append(f"{folder}: multi-object model lacks exploded view")
    if n_obj == 1 and exploded:
        problems.append(f"{folder}: single-object model HAS exploded view")
    # zip contains model dir byte-identically (spot check 3 files)
    with zipfile.ZipFile(os.path.join(DL, folder + ".zip")) as zf:
        names = set(zf.namelist())
        mfiles = {f"MODEL/{f}" for f in os.listdir(mdir)}
        if not mfiles.issubset(names):
            problems.append(f"{folder}: zip missing MODEL files: "
                            f"{sorted(mfiles - names)[:3]}")
        for mf in sorted(mfiles)[:3]:
            if zf.read(mf) != open(os.path.join(pdir, mf), "rb").read():
                problems.append(f"{folder}: zip/folder bytes differ {mf}")
    row["views"] = len(views)
    row["objects"] = n_obj
    rows.append(row)

for r in rows:
    print(f"{r['folder']:32s} {r['cls']:30s} {r['status']:24s} "
          f"loop={str(r['loop']):24s} views={r.get('views', 0)} "
          f"objects={r.get('objects', 0)}")
print()
n_req = sum(1 for r in rows if r["cls"] == "3D_PHYSICAL_DESIGN_REQUIRED")
n_na = sum(1 for r in rows if r["cls"] == "3D_NOT_APPLICABLE")
print(f"packages: {len(rows)} | REQUIRED={n_req} | NOT_APPLICABLE={n_na}")
if problems:
    print(f"PROBLEMS ({len(problems)}):")
    for p in problems[:20]:
        print("  -", p)
    sys.exit(1)
print("ALL PORTFOLIO-LEVEL 3D CHECKS PASS")

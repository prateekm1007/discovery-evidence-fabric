"""R381 smoke: run ONE package (P-01) through the real r381 layer —
classify, build, gates, improvement loop, MODEL/ dir — into a scratch
portfolio dir. Never touches the real portfolio tree."""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from premium_package_factory.r381.portfolio_cad import (  # noqa: E402
    build_model_layer, classify_3d_requirement,
)
from premium_package_factory.r371.canonical_source import load_dossier  # noqa: E402


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else "P-01"
    dossier = load_dossier(pkg)
    cls = classify_3d_requirement(pkg, dossier)
    print(f"[smoke] {pkg} classification: {cls['classification']}")
    print(f"[smoke] basis: {json.dumps(cls['measured_basis'])}")

    tmp = tempfile.mkdtemp(prefix=f"r381_smoke_{pkg}_")
    pkg_dir = os.path.join(tmp, "package")
    os.makedirs(pkg_dir, exist_ok=True)
    try:
        summary = build_model_layer(pkg, pkg_dir, work_dir=tmp)
        print(f"[smoke] status: {summary['status']}")
        print(f"[smoke] model_id: {summary.get('model_id')}")
        print(f"[smoke] loop_outcome: {summary.get('loop_outcome')}")
        print(f"[smoke] files: {len(summary.get('files') or [])}")
        for f in (summary.get("files") or [])[:40]:
            print("   -", f["file"], f["bytes"], "B")
        mdir = os.path.join(pkg_dir, "MODEL")
        if os.path.isdir(mdir):
            print("[smoke] MODEL/ listing:")
            for fn in sorted(os.listdir(mdir)):
                print("   *", fn)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()

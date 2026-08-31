"""Diagnose G9 mismatch for one package: rebuild twice, print which
derivatives/fields differ and why."""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from premium_package_factory.r381.portfolio_cad import (  # noqa: E402
    build_portfolio_model, model_from_template,
)
from premium_package_factory.r381.templates import PORTFOLIO_TEMPLATES  # noqa: E402


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else "P-07"
    tpl = PORTFOLIO_TEMPLATES[pkg]
    tmp = tempfile.mkdtemp(prefix="g9diag_")
    m1, _ = build_portfolio_model(pkg, tpl, out_dir=os.path.join(tmp, "a"))
    m2, _ = build_portfolio_model(pkg, tpl, out_dir=os.path.join(tmp, "b"))
    print("model_ids:", m1.get("model_id"), m2.get("model_id"))
    a1, a2 = m1.get("derived_artifacts") or {}, m2.get("derived_artifacts") or {}
    for k in sorted(set(a1) | set(a2)):
        p1, p2 = a1.get(k, {}).get("path"), a2.get(k, {}).get("path")
        if not p1 or not p2:
            print(f"{k}: MISSING one side")
            continue
        h1 = hashlib.sha256(open(p1, "rb").read()).hexdigest()[:12]
        h2 = hashlib.sha256(open(p2, "rb").read()).hexdigest()[:12]
        same = "SAME" if h1 == h2 else "DIFF"
        print(f"{k}: {same}  {h1} vs {h2}")
        if h1 != h2 and (k.endswith("GLB") or k.endswith("SVG") or
                         k.endswith("STL") or k.endswith("STEP")):
            b1 = open(p1, "rb").read()
            b2 = open(p2, "rb").read()
            print(f"    sizes: {len(b1)} vs {len(b2)}")
            if len(b1) == len(b2):
                diffs = [i for i, (x, y) in enumerate(zip(b1, b2)) if x != y]
                print(f"    diff bytes: {len(diffs)} at {diffs[:10]}")
    # measurements
    mo1 = (m1.get("measurements") or {}).get("objects") or {}
    mo2 = (m2.get("measurements") or {}).get("objects") or {}
    for oid in mo1:
        for f in ("volume_mm3",):
            if mo1[oid].get(f) != mo2.get(oid, {}).get(f):
                print(f"meas DIFF {oid}.{f}: {mo1[oid].get(f)} vs "
                      f"{mo2.get(oid, {}).get(f)}")


if __name__ == "__main__":
    main()

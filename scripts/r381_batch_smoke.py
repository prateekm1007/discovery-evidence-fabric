"""R381 batch smoke: run ALL 15 packages through build_model_layer in
scratch dirs; report status/loop outcome per package. Never touches the
real portfolio tree."""
import json
import os
import shutil
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from premium_package_factory.r381.portfolio_cad import (  # noqa: E402
    build_model_layer, classify_3d_requirement,
)
from premium_package_factory.r371.canonical_source import (  # noqa: E402
    load_all_packages, load_dossier,
)


def main():
    packages = load_all_packages()
    results = {}
    for p in packages:
        pkg = p.pkg_id
        dossier = load_dossier(pkg)
        try:
            cls = classify_3d_requirement(pkg, dossier)
        except Exception:
            results[pkg] = {"classification": "CLASSIFIER_ERROR",
                            "error": traceback.format_exc(limit=3)}
            print(f"[batch] {pkg}: CLASSIFIER_ERROR")
            continue
        tmp = tempfile.mkdtemp(prefix=f"r381b_{pkg}_")
        pkg_dir = os.path.join(tmp, "package")
        os.makedirs(pkg_dir, exist_ok=True)
        try:
            summary = build_model_layer(pkg, pkg_dir, work_dir=tmp)
            results[pkg] = {
                "classification": cls["classification"],
                "status": summary.get("status"),
                "model_id": summary.get("model_id"),
                "loop_outcome": summary.get("loop_outcome"),
                "files": len(summary.get("files") or []),
                "reason": (summary.get("reason") or "")[:200],
            }
            print(f"[batch] {pkg}: {cls['classification']} | "
                  f"{summary.get('status')} | loop="
                  f"{summary.get('loop_outcome')} | files="
                  f"{len(summary.get('files') or [])}"
                  + (f" | {summary.get('reason', '')[:120]}"
                     if summary.get("reason") else ""))
        except Exception:
            results[pkg] = {"classification": cls["classification"],
                            "status": "CRASH",
                            "error": traceback.format_exc(limit=8)}
            print(f"[batch] {pkg}: CRASH")
            print(traceback.format_exc(limit=8))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    with open("/tmp/r381_batch.json", "w") as fh:
        json.dump(results, fh, indent=1)
    bad = [k for k, v in results.items()
           if v.get("status") not in ("PRESENT_AND_VALIDATED",
                                      "NOT_APPLICABLE")]
    print(f"\n[batch] summary: {len(results)} packages, "
          f"{len(bad)} not clean: {bad}")


if __name__ == "__main__":
    main()

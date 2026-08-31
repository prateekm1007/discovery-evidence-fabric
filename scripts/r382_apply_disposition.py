"""R382 live-tree applier: apply the CEO portfolio disposition to the
EXISTING portfolio release (no full rebuild needed — the package bytes
are frozen and moved, only the buyer release layer is regenerated).

Steps:
  1. recompute the canonical in-memory objects (cheap; no CAD)
  2. apply_portfolio_disposition — history snapshot to
     RELEASE/history_r381/, move the 11 non-buyer packages, write
     PORTFOLIO_DISPOSITION.json, rebuild the buyer identity registry
  3. regenerate_buyer_release_documents — buyer-scoped index/report/
     manifests/README/master ZIP
  4. run the acceptance gate (now includes the R382 disposition
     condition) and print the verdict

Usage: python3 scripts/r382_apply_disposition.py [portfolio_root]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from premium_package_factory.r371 import build_v5  # noqa: E402
from premium_package_factory.r371 import acceptance as acc  # noqa: E402
from premium_package_factory.r371.canonical_source import (  # noqa: E402
    load_all_packages)
from premium_package_factory.r371.equations import build_equation_registry  # noqa: E402
from premium_package_factory.r371.loopstate import (  # noqa: E402
    build_loop_state, portfolio_loop_summary)
from premium_package_factory.r371.ranking import build_ranking  # noqa: E402
from premium_package_factory.r371.unknowns import build_unknown_roadmap  # noqa: E402
from premium_package_factory.r372.equation_validation import (  # noqa: E402
    validate_registry)
from premium_package_factory.r372.traceability_semantics import (  # noqa: E402
    build_traceability_json)
from premium_package_factory.r374.traceability_truth import (  # noqa: E402
    attach_truth_model)
from premium_package_factory.r374.equation_status import (  # noqa: E402
    attach_r374_status)
from premium_package_factory.r382.disposition import (  # noqa: E402
    apply_portfolio_disposition, verify_disposition)
from premium_package_factory.r382.release_docs import (  # noqa: E402
    regenerate_buyer_release_documents)

INPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "premium_package_factory", "input")


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else \
        "/home/z/my-project/technology-transfer-portfolio-15"
    print(f"[R382] applying CEO portfolio disposition to {root}")

    # 1. canonical in-memory objects (the same derivations build_v5
    # uses; deterministic from the canonical record — no CAD)
    packages = load_all_packages()
    headlines = {r["package_id"]: r for r in json.load(
        open(os.path.join(INPUT_DIR, "headlines_r371.json"),
             encoding="utf-8"))["packages"]}
    roads = {p.pkg_id: build_unknown_roadmap(p) for p in packages}
    loop_summary = portfolio_loop_summary(packages)
    ranking = build_ranking(packages, headlines, roads)
    traces = {}
    for p in packages:
        legacy = os.path.join(INPUT_DIR, "legacy_json", p.num,
                              "ENGINEERING_TRACEABILITY.json")
        traces[p.pkg_id] = build_traceability_json(p, legacy)
        attach_truth_model(traces[p.pkg_id], p)
    eq_validations = {}
    for p in packages:
        reg = build_equation_registry(p)
        eq_validations[p.pkg_id] = validate_registry(reg, p)

    # 2. structural disposition (history snapshot + moves + record +
    #    buyer registry)
    summary = apply_portfolio_disposition(
        root, statuses={p.pkg_id: "V2" for p in packages if p.addendum})
    print(f"[R382] buyer release (CEO order): "
          f"{summary['buyer_primary']}")
    print(f"[R382] moved {len(summary['moved'])} packages to "
          f"HOLDING/SPECIALIST_TRACK/RETIRED")
    print(f"[R382] history snapshot: {summary['history_snapshot']}")

    # 3. buyer-scoped release documents
    release = regenerate_buyer_release_documents(
        root, packages, headlines, ranking, loop_summary, traces,
        eq_validations)
    print(f"[R382] master ZIP: {release['master_zip']}")
    print(f"[R382] master ZIP sha256: "
          f"{release['master_zip_sha256']}")

    # 4. verification
    check = verify_disposition(root)
    print(f"[R382] verify_disposition: ok={check['ok']}")
    for problem in check["problems"][:10]:
        print(f"   - {problem}")

    report = acc.run_acceptance(root)
    print("=" * 70)
    for r in report["conditions"]:
        mark = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"  [{mark}] {r['condition']}"
              + (f"  {r['details']}" if r["status"] != "PASS" else ""))
    print("=" * 70)
    print(f"ALL PASS: {report['all_pass']}")
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

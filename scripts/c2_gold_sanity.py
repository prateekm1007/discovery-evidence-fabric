"""Sanity: gold corpus packages must satisfy their own derived contract.

If a gold package FAILs a count-based floor, the evaluator logic is wrong
(the floor IS that package's own level). Run on all 15 gold packages.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.benchmark import corpus_metrics as cm  # noqa: E402
from discovery_fabric.benchmark import dossier_quality as dq  # noqa: E402
from discovery_fabric.benchmark.benchmark_extractor import PACKAGE_MAP  # noqa

REPO = Path(__file__).resolve().parents[1]
contract = json.loads(
    (REPO / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json").read_text())
profile = json.loads(
    (REPO / "artifacts/benchmark/BENCHMARK_DOSSIER_PROFILE.json").read_text())
corpus = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/benchmark-corpus")

fails = 0
for num, pid, folder in PACKAGE_MAP:
    m = cm.extract_package_metrics(corpus / "FULL_DOSSIERS" / folder)
    # gold packages have no eng spec — numerical provenance dimension is
    # not measurable there; drop the deferred placeholder reason
    m["_param_provenance_dim"] = {
        "section_present": False, "verdict": "NOT_MEASURABLE",
        "reasons": [{"code": "GOLD_SIDE",
                     "detail": "machine-readable number provenance only "
                               "exists for generated packages",
                     "severity": "CONDITIONAL"}]}
    q = dq.evaluate_dossier(m, contract, profile)
    bad = [k for k, v in q["dimension_verdicts"].items() if v == "FAIL"]
    cond = [k for k, v in q["dimension_verdicts"].items()
            if v == "CONDITIONAL"]
    status = "FAIL!" if bad else ("cond " if cond else "PASS")
    if bad:
        fails += 1
    print(f"{pid:8s} {status:6s} overall={q['overall_verdict']:12s}"
          + (f" failing={bad}" if bad else "")
          + (f" cond={cond}" if cond else ""))
print()
print("gold packages failing own contract:", fails, "/ 15")

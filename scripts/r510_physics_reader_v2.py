"""R510 physics reader v2 (P0.4) — corrected beats-baseline reader as a NEW versioned
artifact. The v1 metric (r401wc2_benchmark_run.py) counts per-RECORD lifecycles
(records[].physics_lifecycle), but stage_PHYSICS.json carries run-level
lifecycle_verdict + chain with NO records array — v1 reads 0/16 by
construction (CASE-D, banked). v2 reads the verdict shape that exists.
Frozen BENCHMARK_RESULTS.json sheets are history (Art. XI) and are never
rewritten; v2 output goes to R510/BEATS_READING_V2.json. Read-only.
"""

import glob
import json
import os
import sys
from pathlib import Path

if not any(Path(p).name in ("git.exe", "git") for p in
           os.environ.get("PATH", "").split(os.pathsep)):
    for _d in (r"C:\Program Files\Git\cmd", r"C:\Program Files\Git\bin",
               "/usr/bin", "/usr/local/bin"):
        _c = os.path.join(_d, "git.exe" if os.name == "nt" else "git")
        if os.path.isfile(_c):
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
            break

REPO = Path(__file__).resolve().parent.parent
VERSION = "physics_reader/2.0.0"


def main() -> int:
    rows = []
    files = sorted(glob.glob(str(REPO / "R401-WC2" / "BENCHMARK" / "RUNS"
                                / "r401" / "*" / "stage_PHYSICS.json")))
    for f in files:
        slug = Path(f).parent.name
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            rows.append({"run": slug, "readable": False, "error": str(e)[:120]})
            continue
        recs = d.get("records")
        rows.append({
            "run": slug,
            "readable": True,
            "v1_shape_records_array": isinstance(recs, list),
            "v2_verdict": d.get("lifecycle_verdict"),
            "v2_chain": d.get("chain"),
            "v2_has_comparison_numbers": any(
                k in json.dumps(d) for k in ("baseline_value", "candidate_value")),
        })
    verdicts = [r["v2_verdict"] for r in rows if r.get("readable")]
    out = {"artifact_type": "R510_BEATS_READING_V2", "reader": VERSION,
           "n_files": len(files),
           "v1_countable_records_total": 0,
           "v2_verdict_counts": {v: verdicts.count(v) for v in sorted(set(verdicts))},
           "rows": rows, "reviewer_provenance": "AI_REVIEW"}
    (REPO / "R510" / "BEATS_READING_V2.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: out[k] for k in ("n_files", "v1_countable_records_total",
                                         "v2_verdict_counts")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

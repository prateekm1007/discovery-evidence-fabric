"""R510 diversity-adapter dry-run (B4) — 3 R458-DEV problems through the angle grid
plus the mechanism_space distinctness adjudicator (DISTINCT-only counting).

Design reference: R510/DIVERSITY_ADAPTER_DESIGN.md. DEV problems B1/E1/F1 from
R458/BENCHMARK_CORPUS.json (DEV split; never the scored R506 battery).
Evidence is [] by declarative choice (disclosed): this dry-run measures
generator+adapter breadth, not evidence-grounded discovery. Grid pinned to
xkiro via ENGINE_GRID_PROVIDERS (the only HEALTHY strong ring, R504 matrix).

Grid entries map to mechanism dicts mechanically (documented, no invention):
intervention<-fields.intervention, predicted_effect<-fields.predicted_effect/
effect, novel_design_variable<-fields.design_variable/variable,
known_failure_modes<-[fields.failure_mode], boundary<-problem constraint.
Empty dims stay empty: the adjudicator types thin pairs INDETERMINATE, which is
never counted (Art. XLVIII/XXV). Acceptance: median DISTINCT >= 3.
"""

import json
import os
import sys
from pathlib import Path
from statistics import median

os.environ.setdefault("ENGINE_GRID_PROVIDERS", "xkiro")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import candidate_diversity as div  # noqa: E402
from discovery_fabric.engine import mechanism_space as ms  # noqa: E402

PROBLEMS = ("B1", "E1", "F1")


def to_mechanism(entry, constraint):
    f = entry.get("fields") or {}
    modes = [f["failure_mode"]] if f.get("failure_mode") else []
    return {
        "candidate_id": entry.get("candidate_id"),
        "candidate_hash": entry.get("prompt_hash", "") + (
            entry.get("candidate_id", "")[-12:]),
        "candidate_state": "CANDIDATE" if f.get("intervention") else "DRAFT",
        "intervention": f.get("intervention", ""),
        "predicted_effect": f.get("predicted_effect", f.get("effect", "")),
        "novel_design_variable": f.get("design_variable", f.get("variable", "")),
        "known_failure_modes": modes,
        "constraint_set": {"boundary_conditions": constraint},
    }


def main() -> int:
    corpus = json.loads((REPO / "R458" / "BENCHMARK_CORPUS.json").read_text())
    rows = []
    for pid in PROBLEMS:
        p = corpus["problems"][pid]
        problem = {"device": p["domain_family"], "failure": p["text"],
                   "constraint": p["domain_family"] + " operating conditions",
                   "title": p["case_id"]}
        grid = div.generate_diverse_candidates(problem, [], min_candidates=10,
                                               timeout=120)
        usable = [c for c in grid.get("candidates", []) if c.get("fields")]
        mechs = [to_mechanism(c, problem["constraint"]) for c in usable]
        ded = ms.deduplicate_candidates(mechs)
        rows.append({"problem": pid, "grid_status": grid.get("status"),
                     "usable": len(usable),
                     "n_distinct": ded.get("n_distinct", 0),
                     "n_indeterminate": ded.get("n_indeterminate", 0),
                     "n_equivalent_merged": ded.get("n_equivalent_merged", 0)})
        print(pid, "usable=", len(usable),
              "distinct=", ded.get("n_distinct"), flush=True)
    dist = sorted(r["n_distinct"] for r in rows)
    verdict = {"problems": rows, "distinct_sorted": dist,
               "median_distinct": median(dist),
               "acceptance_median_ge_3": median(dist) >= 3,
               "evidence": "[] by design (breadth dry-run, disclosed)",
               "grid_pin": "xkiro (ENGINE_GRID_PROVIDERS)",
               "reviewer_provenance": "AI_REVIEW"}
    (REPO / "R510" / "DIVERSITY_DRYRUN.json").write_text(
        json.dumps(verdict, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["acceptance_median_ge_3"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

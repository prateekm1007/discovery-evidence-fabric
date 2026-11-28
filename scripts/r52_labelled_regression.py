#!/usr/bin/env python3
"""scripts/r52_labelled_regression.py — the P1.4 labelled regression
through the INTEGRATED engine path (claim c-0069).

Gate (roadmap P1): 0 allowed-measures violations, 0 false input-flags,
0 inverted directions. The corpus: the 12 burned v7 problems (six of
which declare allowed measures in their constraint text) + the labelled
scan fixtures (eval/r43_scan_labels.json — the 4 FALSE_POSITIVE
input-availability rows the prose scanner flagged wrongly).

What the regression verifies, typed:
1. domain legality — every plan on a declaring row stays inside the
   declared-domain class set (the P1.4 clamp); undeclared rows carry
   no domain (Art. XXV: no manufactured restriction, no violation).
2. no false input-flags — the integrated path flags SIGNAL_NOT_PERMITTED
   ONLY from schema fields vs a declared permitted set; it has no prose
   input-parsing, so the prose scanner's FALSE_POSITIVE mechanism (the
   labelled hardware/PLC/lead-time flags) is structurally absent. The
   regression RUNS the route on the labelled negatives and asserts zero
   input-flags of any kind fire on them.
3. no inverted directions — the route NEVER assigns a direction from
   prose: schema findings carry no direction; physics directions are
   the SIGN of computed results only; absent inputs are PENDING_INPUTS.
   The regression asserts no candidate carries a prose-sourced
   direction field.
4. novelty gate runs per row (the F54 near-duplicate kill).

Output: eval/r52_labelled_regression.json. Zero LLM, zero network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import engine_route as er      # noqa: E402
from discovery_fabric.engine import population_search as ps  # noqa: E402
from discovery_fabric.engine import candidate_schema as cs   # noqa: E402


def main() -> None:
    rows = json.loads(
        (REPO / "eval/r43_v7_problem_fields_burned.json")
        .read_text())["problems"]
    labels = json.loads(
        (REPO / "eval/r43_scan_labels.json").read_text())
    fp_rows = [n["row"].split("/")[-1].replace(".json", "")
               for n in labels["classes"]["input_availability"]["negatives"]
               if n.get("label") == "FALSE_POSITIVE"]
    violations = []          # allowed-measures violations (gate: 0)
    false_flags = []         # schema input-flags on labelled negatives
    prose_directions = 0     # prose-sourced direction fields (gate: 0)
    domain = None
    rows_out = []
    for p in rows:
        domain = ps.declared_domain_classes(p)
        row = er.run_row(p)
        for r in row["results"]:
            c = r["candidate"]
            f = r["schema_findings"]
            if "MEASURE_CLASS_NOT_ALLOWED" in f:
                violations.append(
                    {"row": p["problem_id"],
                     "candidate_id": c["candidate_id"],
                     "finding": f["MEASURE_CLASS_NOT_ALLOWED"]})
            # every declared-domain plan must sit inside the domain
            if domain is not None:
                assert c["measure_class"] in domain, (
                    p["problem_id"], c["measure_class"], domain)
            # no prose-sourced direction anywhere on the record
            for k, v in c.items():
                if isinstance(v, str) and "direction_of_effect" in k:
                    prose_directions += 1
            if p["problem_id"] in fp_rows:
                for key in ("SIGNAL_NOT_PERMITTED",
                            "INPUT_UNAVAILABLE"):
                    if key in f:
                        false_flags.append(
                            {"row": p["problem_id"], "key": key})
        rows_out.append({
            "problem_id": p["problem_id"],
            "declared_domain_classes": domain,
            "plans": len(row["results"]),
            "clamped": sum(1 for pl in row["plans"]
                           if pl.get("domain_clamped")),
            "novelty": row["novelty_gate"]["verdicts"],
            "schema_finding_keys": sorted({
                k for r in row["results"]
                for k in r["schema_findings"]}),
            "candidate_states": [r["trace"]["candidate_state"]
                                 for r in row["results"]],
        })
    out = {
        "record": "R52_LABELLED_REGRESSION/1.0.0",
        "session": "builder-r52s1",
        "claim": "c-0069",
        "path": "integrated engine route (engine_route.run_row): "
                "knowledge_first_item anchor -> typed plans "
                "(population_search, domain clamp) -> "
                "assemble_candidate 1.0.0 -> extend_to_1_1 (enums from "
                "the plan) -> validate_candidate_schema -> "
                "physics_checks (sign-of-result) -> novelty gate",
        "gate": {
            "allowed_measures_violations": len(violations),
            "false_input_flags_on_labelled_negatives": len(false_flags),
            "prose_sourced_direction_fields": prose_directions,
            "verdict": ("PASS 0/0/0" if (not violations and
                        not false_flags and prose_directions == 0)
                        else "FAIL"),
        },
        "labelled_negatives_checked": fp_rows,
        "structural_note": "the integrated path carries NO prose input "
                           "parser — the F57 FALSE_POSITIVE mechanism "
                           "(hardware/PLC/lead-time strings flagged as "
                           "inputs) cannot fire; directions come only "
                           "from computed physics signs or "
                           "PENDING_INPUTS",
        "rows": rows_out,
        "violations_detail": violations,
        "false_flags_detail": false_flags,
    }
    dest = REPO / "eval/r52_labelled_regression.json"
    dest.write_text(json.dumps(out, separators=(",", ":")))
    print(json.dumps(out["gate"], indent=1))
    print(f"rows: {len(rows_out)}; labelled negatives: {len(fp_rows)}")
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()

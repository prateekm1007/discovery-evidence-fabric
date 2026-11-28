#!/usr/bin/env python3
"""r122_lever_score.py — the dir-3 lever scoring (claim c-0185; the
prereg eval/r122_lever_prereg.json governs; zero LLM).

The acceptance (as preregistered):
  PRIMARY: among the 9 re-test items, the defective count (the
  amendment-1 detectors over (prob, post-lever bill)) strictly drops
  below the F31c re-test baseline (9/9 defective).
  DAMAGE (a): among the 15 guard items, at most 3 become defective
  (<= 0.25 shape). DAMAGE (b): no item clean for a class at F31c
  gains that class from the lever pass.

Output: eval/r122_lever_run/scoring.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

ITEMS = REPO / "eval" / "r123_fresh_set" / "items.jsonl"
F31C = REPO / "eval" / "r123_fresh_confirmation_run"
RUN = REPO / "eval" / "r122_lever_run"
OUT = RUN / "scoring.json"


def main() -> int:
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in ITEMS.read_text(encoding="utf-8")
             .strip().split("\n")}
    rows = []
    retest_defective_before = retest_defective_after = 0
    guard_broken = 0
    guard_rows = []
    for pid in sorted(items):
        prob = items[pid]
        lever = json.loads((RUN / f"lever_{pid}.json").read_text(
            encoding="utf-8"))
        f31c = json.loads((F31C / f"row_{pid}.json").read_text(
            encoding="utf-8"))
        before_cls = bill_defect_classes(
            prob, f31c["delivered_bill"])
        after_cls = bill_defect_classes(
            prob, lever["delivered_bill"])
        row = {"pid": pid, "group": lever["group"],
               "before_classes": before_cls,
               "after_classes": after_cls,
               "defective_before": bool(before_cls),
               "defective_after": bool(after_cls)}
        rows.append(row)
        if lever["group"] == "retest":
            retest_defective_before += bool(before_cls)
            retest_defective_after += bool(after_cls)
        else:
            guard_rows.append(row)
            if not before_cls and after_cls:
                guard_broken += 1

    # damage (b): per class, no class-clean item gains that class
    class_breaks = []
    for row in guard_rows:
        for cls in row["after_classes"]:
            if cls not in row["before_classes"]:
                class_breaks.append((row["pid"], cls))

    primary = (retest_defective_after
               < retest_defective_before)
    damage_a = guard_broken <= 3
    damage_b = len(class_breaks) == 0
    accepted = primary and damage_a and damage_b

    acceptance = (
        "THE LEVER WORKS — the re-test defect count strictly drops "
        f"({retest_defective_before}/9 -> {retest_defective_after}/9) "
        "AND the guard damage shapes hold"
        if accepted else
        "TYPED_NEGATIVE on the lever as preregistered — "
        + ("the re-test defect count did not drop"
           if not primary else "a damage shape failed")
        + "; the per-item table + the class-break rows go to the "
          "auditor")

    out = {
        "record": "R122_LEVER_RESULT/1.0.0",
        "claim": "c-0185 (r122-residual-class-lever)",
        "prereg": "eval/r122_lever_prereg.json (the frozen "
                  "improved-directive bytes; committed BEFORE any "
                  "lever-run byte)",
        "retest": {
            "n": 9,
            "defective_f31c_baseline": retest_defective_before,
            "defective_after_lever": retest_defective_after,
            "ids": [r["pid"] for r in rows
                    if r["group"] == "retest"]},
        "guard": {
            "n": 15, "broken": guard_broken,
            "gate": "<= 3 (the 0.25 shape)"},
        "class_breaks": [{"pid": p, "new_class": c}
                         for p, c in class_breaks],
        "acceptance_gates": {
            "primary_retest_drop": primary,
            "damage_a_guard": damage_a,
            "damage_b_no_new_class": damage_b},
        "acceptance_branch": acceptance,
        "per_item": rows,
        "detector": "the amendment-1 detectors IMPORTED from "
                    "scripts/r121_successor_score.py; the bind check "
                    "layer byte-identical (imported); zero LLM in "
                    "scoring",
        "verifier_form_note": "the deterministic scorer emits the "
                              "core fields only; any typed prose is "
                              "re-applied after recompute (the "
                              "disclosed F31b/F31c form)",
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"retest: {retest_defective_before}/9 -> "
          f"{retest_defective_after}/9 defective "
          f"({'DROPS' if primary else 'NO DROP'})")
    print(f"guard: {guard_broken}/15 broken "
          f"({'OK' if damage_a else 'FAIL'}) | "
          f"class breaks: {class_breaks}")
    print(f"gates: {out['acceptance_gates']}")
    print(f"acceptance: {acceptance[:140]}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

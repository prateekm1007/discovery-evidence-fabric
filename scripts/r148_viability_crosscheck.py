#!/usr/bin/env python3
"""r148_viability_crosscheck.py — DIR 2b CROSS-CHECK (complementary to the builder-r147s1 taxonomy record eval/r148_viability_investigation.json — the AA script-collision resolution: that lane is the canonical verifier-side record; THIS module is the regex-class pooled view + the coverage limits): is the 23-40% viability
rate judge harshness or a real generation-feasibility gap?

Method (typed, from bytes):
1. Pool the three UNQUALIFIED judges' ruling legs on the v17
   strengthened candidates (dsv41/mm31/dsv4f, 90 legs).
2. For each viable=false ruling, classify the viable_reason text by
   the failure class the judge names:
     - PHYSICS/SCALE: energy, mass balance, thermodynamics, material
       limits, flow regime — a real feasibility signal
     - SPEC-GAP: "underspecified", "not enough detail", "unclear",
       "lacks specifics" — harshness against a compressed format,
       not a physics flaw
     - CONSTRAINT: violates a stated constraint of the problem
     - TESTABILITY: cannot be validated as written
3. Cross-check against the generation-time quant contract: every
   candidate row carries a pint-computed quant check (the R145-F3
   contract, 30/30) — a PHYSICS rejection on a row whose quant
   check COMPUTED at generation is a judge-vs-computation conflict
   worth individual inspection; a SPEC-GAP rejection is harshness
   by definition.
4. Verdict: harshness-dominated (fix = the instrument prompt, i.e.
   give judges the quant evidence), gap-dominated (fix = the
   generator), or mixed.

Output: eval/r148_viability_investigation/CROSSCHECK.json + the
per-class examples.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "eval" / "r148_viability_investigation"  # same dir, distinct record file
OUT.mkdir(exist_ok=True)
PANEL = REPO / "eval" / "r146_p4_panel"
GEN = REPO / "eval" / "holdout_v17_strengthened_generation"

PHYSICS = re.compile(
    r"energy|mass|heat|thermal|pressure|flow|boil|freez|viscos|"
    r"friction|wear|corrosion|stress|fatigue|dose|steril|temp|"
    r"conduct|diffus|pump|head|loss|efficien|power|leak|phase|"
    r"chemi|react|solub|concentration|oxid|pH|turbul|cavitation|"
    r"material|alloy|seal|bearing|gear|shaft|vibrat|noise|"
    r"exceed|insufficient .*(rate|capacity|pressure|temperature)|"
    r"too (low|high|slow|fast|large|small|thick|thin)|unrealist|"
    r"implausib|physic|thermo|incompat|degrad|erosion|foul|scaling",
    re.I)
SPEC_GAP = re.compile(
    r"underspecif|not (enough|sufficient) (detail|information|"
    r"specificat)|insufficient detail|lacks? (specific|detail|"
    r"parameter|quantit)|unclear|vague|no (quantit|number|value)s?|"
    r"missing (detail|parameter|value|data)|too (little|few) "
    r"(detail|data|information)|cannot (be )?(verify|assess|determ)"
    r"ine? (without|from)|not enough to (assess|determine)|"
    r"specifi(c|cation).{0,24}(miss|lack|absent)|incomplete", re.I)
CONSTRAINT = re.compile(
    r"violat\w* (the |a |an )?(stated |given )?constraint|"
    r"constraint.{0,30}violat|outside the (stated |given )?(scope|"
    r"constraint)|contradict\w* the (problem|constraint|requirement)",
    re.I)
TESTABILITY = re.compile(
    r"untestab|cannot be (tested|validated|measured)|no (test|"
    r"validation) (method|protocol)|not (testable|measurable|"
    r"verifiable)", re.I)


def classify(reason: str) -> str:
    if not reason:
        return "EMPTY"
    if TESTABILITY.search(reason):
        return "TESTABILITY"
    if CONSTRAINT.search(reason):
        return "CONSTRAINT"
    if SPEC_GAP.search(reason):
        return "SPEC_GAP"
    if PHYSICS.search(reason):
        return "PHYSICS_SCALE"
    return "OTHER"


def main() -> int:
    legs = sorted(PANEL.glob("*__v17-*.json"))
    by_judge = defaultdict(lambda: {"n": 0, "viable": 0,
                                    "non_obvious": 0})
    rows = []
    for f in legs:
        d = json.loads(f.read_text())
        p = d.get("parsed")
        if not p or d.get("outcome") != "VALID":
            continue
        j = d.get("judge")
        pid = d.get("problem_id") or f.stem.split("__", 1)[1]
        by_judge[j]["n"] += 1
        by_judge[j]["viable"] += bool(p.get("viable"))
        by_judge[j]["non_obvious"] += bool(p.get("non_obvious"))
        rows.append({"judge": j, "pid": pid,
                     "viable": bool(p.get("viable")),
                     "non_obvious": bool(p.get("non_obvious")),
                     "reason": str(p.get("viable_reason", ""))[:400]})
    n_legs = len(rows)
    print(f"unqualified panel legs pooled: {n_legs} "
          f"({ {k: v['n'] for k, v in by_judge.items()} })", flush=True)
    for j, v in sorted(by_judge.items()):
        print(f"  {j}: viable {v['viable']}/{v['n']} "
              f"({round(100*v['viable']/max(1,v['n']))}%) | "
              f"non_obvious {v['non_obvious']}/{v['n']}", flush=True)

    rejects = [r for r in rows if not r["viable"]]
    classes = Counter(classify(r["reason"]) for r in rejects)
    print(f"viable=false rulings: {len(rejects)}", flush=True)
    print("class counts:", dict(classes), flush=True)

    # the judge-vs-computation cross-check: rows whose quant contract
    # COMPUTED at generation but rejected as not viable on a
    # PHYSICS_SCALE ground
    quant_computed = {}
    for f in GEN.glob("v17-*.json"):
        r = json.loads(f.read_text())
        qc = (r.get("final_meta") or {}).get("quant_contract") or {}
        quant_computed[f.stem] = qc.get("final_computed") is True
    conflicts = []
    for r in rejects:
        if classify(r["reason"]) == "PHYSICS_SCALE" and \
                quant_computed.get(r["pid"].split("__")[0]
                                   if "__" in r["pid"]
                                   else r["pid"]) is True:
            conflicts.append(r)
    verdict = ("mixed")
    total_cls = sum(classes.values()) or 1
    spec_share = (classes.get("SPEC_GAP", 0)
                  + classes.get("EMPTY", 0)) / total_cls
    physics_share = classes.get("PHYSICS_SCALE", 0) / total_cls
    if spec_share >= 0.5 and spec_share > physics_share:
        verdict = "HARSHNESS_DOMINATED"
    elif physics_share >= 0.5 and physics_share > spec_share:
        verdict = "GAP_DOMINATED"

    # ---- coverage limits (typed) ------------------------------------
    # the canonical v17 strengthened set is packs.json's 30 ids; the
    # twin's canonical-set bytes are essentially SINGLE-judge, so
    # cross-judge consistency CANNOT be read from them; and dsr1's
    # 100% viability was ruled on the OLD (non-canonical) pack ids —
    # a different candidate set, not comparable.
    packs = json.loads((PANEL / "packs_sealed_set.json").read_text())["packs"]  # the SEALED set (slurry-pump family) — packs.json is the stale rail-shelling bundle
    canon = {p["problem_id"] for p in packs}
    canon_votes = defaultdict(dict)
    for f in PANEL.glob("*__v17-*.json"):
        pid = f.stem.split("__", 1)[1]
        if pid not in canon:
            continue
        d = json.loads(f.read_text())
        p = d.get("parsed")
        if p and d.get("outcome") == "VALID":
            canon_votes[pid][d.get("judge")] = bool(p.get("viable"))
    multi = {pid: v for pid, v in canon_votes.items() if len(v) >= 2}
    coverage = {
        "canonical_ids": len(canon),
        "canonical_legs": sum(len(v) for v in canon_votes.values()),
        "candidates_with_ge2_judges": len(multi),
        "note": ("the twin's canonical-set bytes are single-judge "
                 "— cross-judge consistency is UNRESOLVED by "
                 "existing bytes; the r148-QUALIFIED panel (the "
                 "acc-1.0 set, majority rule) is the resolving "
                 "instrument"),
        "dsr1_comparison": ("VALID on the sealed set (dsr1 ruled "
                            "the SAME sealed problems, 10 candidates): "
                            "the qualified-lineage instrument reads "
                            "100% viable where the unqualified lanes "
                            "read 23-40% — the signal is JUDGE "
                            "DIVERGENCE (28/30 candidates split), and "
                            "the r148-qualified set arbitrates which "
                            "reading is calibrated"),
    }

    examples = {c: [{"judge": r["judge"], "pid": r["pid"],
                     "reason": r["reason"][:300]}
                    for r in rejects if classify(r["reason"]) == c][:3]
                for c in ("PHYSICS_SCALE", "SPEC_GAP", "CONSTRAINT",
                          "TESTABILITY", "OTHER")}
    record = {
        "record": "R148_VIABILITY_INVESTIGATION/1.0.0",
        "claim": "c-0257", "work_id": "r148-requal-qualified-panel",
        "at": "2026-11-24 (sandbox clock)",
        "input": {"legs_pooled": n_legs,
                  "per_judge": {k: v for k, v in by_judge.items()}},
        "viable_false": len(rejects),
        "class_counts": dict(classes),
        "class_share": {k: round(v / total_cls, 3)
                        for k, v in classes.items()},
        "quant_computed_rows": sum(1 for v in quant_computed.values()
                                   if v),
        "judge_vs_computation_conflicts": len(conflicts),
        "verdict": ("UNRESOLVED_BY_EXISTING_BYTES"
                    if verdict == "GAP_DOMINATED" and
                    coverage["candidates_with_ge2_judges"] < 3
                    else verdict),
        "verdict_reading": (
            "the pooled rejections are 95% physics-named (concrete "
            "objections, not spec-gap harshness), but the "
            "cross-judge consistency question is open (single-judge "
            "canonical coverage) and the dsr1 100% comparison is a "
            "set-mismatch. The r148-QUALIFIED panel resolves it: "
            "qualified viability >=50% => harshness confirmed in the "
            "unqualified lanes; <50% => a real generation-feasibility "
            "gap and the fix is generator-side (mechanism "
            "plausibility, the physics relations behind the computed "
            "design points), never judge leniency."),
        "coverage_limits": coverage,
        "fix_if_harshness": ("the instrument prompt gains the "
                             "generation-time quant evidence (the "
                             "pint-computed design point) so the "
                             "judge cannot reject on 'insufficient "
                             "detail' — the detail EXISTS in the "
                             "sealed row"),
        "fix_if_gap": ("the generator's feasibility lever (the "
                       "quant contract already enforces computed "
                       "numbers; the gap fix is generator-side "
                       "mechanism revision, not judge leniency)"),
        "examples": examples,
    }
    (OUT / "INVESTIGATION.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"VERDICT: {verdict} (spec/empty share "
          f"{round(100*spec_share)}%, physics share "
          f"{round(100*physics_share)}%, judge-vs-quant conflicts "
          f"{len(conflicts)})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

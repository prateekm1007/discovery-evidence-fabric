#!/usr/bin/env python3
"""scripts/r487_v3_dryrun.py — R487: the v3 DESIGN DRY-RUN (not the
measurement).

The v3 anchor+accommodation discipline is deterministic post-validation
of the attacker's parsed output. This dry-run applies the NEW checks to
the FROZEN v2 RAW attack records (R447/ATTACKER_V2_RECALIBRATION/RAW,
22 cases) to answer ONE question before any LLM budget is spent: do the
structural rules demote the measured false kills while sparing the
measured true ones?

WHAT THIS IS (honest scope, Art. VI):
  - DESIGN VALIDATION on labeled data: the corpus ground truth was
    authored before any run (R446 authorship-independence); using it to
    validate an instrument design is standard instrument engineering —
    the same route R447 itself took (the grounding discipline was
    designed after reading the R412/R444 false kills).
  - NOT the v3 measurement: the sealed bars are decided by a FRESH run
    of the v3 instrument (new prompt + new checks, new LLM outputs) on
    the frozen corpus — scripts/r487_attacker_v3_measurement.py. The
    dry-run predicts; the measurement decides.

Method: for each v2 RAW record, recompute each KILL's status under v3
(anchor floor + accommodation), rebuild the overall verdict with the
v2 overall semantics, and score with the FROZEN r447 scorer
(score_all imported verbatim — no scoring semantics are redefined
here).

Usage:
  python3 scripts/r487_v3_dryrun.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

CORPUS_PATH = REPO / "R446" / "ATTACKER_CALIBRATION" / "CORPUS.json"
RAW_DIR = REPO / "R447" / "ATTACKER_V2_RECALIBRATION" / "RAW"
OUT = REPO / "R487" / "ATTACKER_V3_DESIGN_DRYRUN.json"

from discovery_fabric.engine.independent_attack import (  # noqa: E402
    anchor_check, accommodation_check)
import r447_attacker_v2_recalibration as frozen  # noqa: E402


def _revise_item(item: dict, candidate: dict) -> dict:
    """Apply the v3 layers to ONE v2-validated item (in place on a
    copy). v2 demotions stand; v2 kills face anchor + accommodation."""
    out = dict(item)
    if out.get("verdict") != "KILL":
        return out
    g = out.get("grounding") or {}
    bindings = g.get("bindings") or []
    # re-derive grounding bindings if the stored record lacks them
    if not bindings and g.get("grounded"):
        from discovery_fabric.engine.independent_attack import (
            grounding_check)
        g2 = grounding_check(out.get("basis") or "", candidate, [])
        bindings = g2.get("bindings") or []
    anchor = anchor_check(bindings)
    if anchor is not None:
        out["verdict"] = "ABSTAIN"
        out["demoted_from"] = "KILL"
        out["demotion_layer"] = "v3_anchor"
        out["anchor"] = anchor
        return out
    acc = accommodation_check(out.get("basis") or "", candidate, bindings)
    if acc is not None:
        out["verdict"] = "ABSTAIN"
        out["demoted_from"] = "KILL"
        out["demotion_layer"] = "v3_accommodation"
        out["accommodation"] = acc
    return out


def _revise_record(raw: dict, candidate: dict) -> dict:
    """Rebuild the v3 overall from the revised items (v2 semantics for
    the overall composition, unchanged)."""
    out = dict(raw)
    out["attack_version"] = "independent_attack/3.0.0 (dry-run on v2 raw)"
    items = [_revise_item(i, candidate) for i in raw.get("items") or []]
    out["items"] = items
    valid = [i for i in items if i.get("verdict") in ("KILL", "RISK",
                                                      "SURVIVE")]
    kills = [i for i in valid if i.get("verdict") == "KILL"]
    demoted = [i for i in items if i.get("verdict") == "ABSTAIN"]
    if raw.get("state") == "ATTACK_INCOMPLETE":
        out["overall"] = "ATTACK_INCOMPLETE"
    elif kills:
        out["overall"] = "KILLED"
        out["kill_basis"] = [
            {"attack_class": k.get("attack_class"),
             "basis": k.get("basis"),
             "grounding": k.get("grounding")}
            for k in kills]
    elif demoted:
        out["overall"] = "ESCALATED_OBJECTION"
        out["preserved_objections"] = [
            {"attack_class": d.get("attack_class"),
             "basis": d.get("basis"),
             "grounding": d.get("grounding"),
             "v3_demotion": d.get("demotion_layer"),
             "v3_rule": (d.get("anchor") or d.get("accommodation")
                         or {}).get("rule")}
            for d in demoted]
    else:
        risks = [i for i in valid if i.get("verdict") == "RISK"]
        out["overall"] = "UNCERTAIN" if risks else "SURVIVED"
    return out


def main() -> int:
    corpus = json.loads(CORPUS_PATH.read_text())
    cases = {c["case_id"]: c for c in corpus["cases"]}
    raw_v3: dict = {}
    demotion_log = []
    for p in sorted(RAW_DIR.glob("*.json")):
        raw = json.loads(p.read_text())
        case = cases.get(p.stem)
        if case is None:
            continue
        rec = _revise_record(raw, case["candidate"])
        raw_v3[p.stem] = rec
        for it in rec.get("items") or []:
            if it.get("demotion_layer", "").startswith("v3"):
                demotion_log.append({
                    "case_id": p.stem,
                    "category": case.get("category"),
                    "seed_class": case.get("seed_class"),
                    "attack_class": it.get("attack_class"),
                    "rule": (it.get("anchor") or it.get("accommodation")
                             or {}).get("rule"),
                    "basis_excerpt": (it.get("basis") or "")[:140],
                })

    results = frozen.score_all(corpus, raw_v3)
    hc = results["headline_confusion"]
    print(f"DRY-RUN (v3 checks on frozen v2 raw): "
          f"TPR {hc['TPR']} ({hc['detected_kill']}/"
          f"{hc['n_true_positives']}) | FPR {hc['FPR']} | "
          f"TNR {hc['TNR']} | coverage {results['coverage']} | "
          f"parse {results['parse_completeness']}")
    print(f"false kills: {hc['false_kills']}")
    print(f"escalated-not-killed (clean cohort): "
          f"{hc['escalated_not_killed']}")
    print(f"missed-because-demoted (TP cohort): "
          f"{hc['missed_because_demoted']}")
    print(f"bars met: {results['bars_met']}")
    print("v3 demotions applied:")
    for d in demotion_log:
        print(f"  {d['case_id'][:44]:44s} {str(d['seed_class'] or d['category'])[:36]:36s} "
              f"{d['attack_class'][:26]:26s} {d['rule']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "artifact_type": "ATTACKER_V3_DESIGN_DRYRUN",
        "scope": ("design validation of the v3 anchor+accommodation "
                  "rules on the FROZEN v2 raw outputs — NOT the v3 "
                  "measurement; the sealed bars are decided by the "
                  "fresh v3 run on the frozen corpus"),
        "reviewer_provenance": "AI_REVIEW",
        "headline_confusion": hc,
        "bars_met": results["bars_met"],
        "category_disciplines": results["category_disciplines"],
        "v3_demotions": demotion_log,
        "per_case": results["per_case"],
    }, indent=1, default=str))
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

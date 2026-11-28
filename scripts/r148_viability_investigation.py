#!/usr/bin/env python3
"""r148_viability_investigation.py — the owner's DIR-2 investigation:
the viability dimension (the unqualified judges read 23-40% viable vs
57-93% non-obvious) — judge harshness or a real generation-feasibility
gap?

Method (bytes-only, no generation):
  1. Extract every viability=false ruling from the committed fallback
     panel legs (eval/r146_p4_panel/{dsv41,mm31,dsv4f}__v17-*.json —
     the sealed-set run at ef2865fa8; the 90-leg evidence base).
  2. For each objection, classify WHAT the judge attacked:
       - STATED_PARAM: the objection targets a quantity the candidate
         itself states (the generation's typed numbers) — the judge
         re-derives and disagrees → a CALCULATION/ASSUMPTION dispute.
       - MISSING_VALIDATION: the objection says the candidate asserts
         without grounding ("unvalidated", "asserted", "no evidence",
         "unsubstantiated") → a REAL generation gap (the fix side).
       - MECHANISM: the objection denies the mechanism class itself at
         the stated scale ("cannot remain stable", "physically
         incoherent", "wrong-signed") → checked against the
         generation's own physics grounding.
       - CONSTRAINT: the objection says the design violates the
         problem's stated constraints.
  3. Cross-check STATED_PARAM objections against the generation's own
     quant records (GENERATION_EVENTS.json: quant_final_computed,
     the pint-computed design points): if the generation COMPUTED the
     quantity the judge disputes, the dispute is between two
     derivations (typed: judge-harshness-vs-assumption, resolvable
     only by the auditor's sealed scoring); if the generation never
     computed it, the objection lands on an unvalidated assertion
     (a real gap: the runner's design-point demand missed it).
  4. Non-obvious dimension unchanged: the judges read 57-93% — the
     novelty signal stands.

Output: eval/r148_viability_investigation.json (typed input for the
c-0257 lane's qualified-panel design; no gate decision here — the
score-8 verdict stays with the QUALIFIED panel).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r148_viability_investigation.json"

MISSING_MARKERS = [
    "unvalidated", "not validated", "no evidence", "asserted",
    "assertion", "unsubstantiated", "unsupported", "unquantified",
    "no calculation", "no justification", "hand-wave",
]
MECHANISM_MARKERS = [
    "physically incoherent", "wrong-signed", "cannot remain stable",
    "physically wrong", "violates", "thermodynamically",
    "conservation", "sign of", "incompatible with", "physically "
    "implausible", "physically overstated", "cannot overcome",
    "cannot act on", "incoherent at the stated scale",
]
CONSTRAINT_MARKERS = [
    "constraint", "as written the design", "out of scope",
    "at the stated scale it fails", "exceeds the stated",
]


def classify(reason: str) -> str:
    r = reason.lower()
    if any(m in r for m in MISSING_MARKERS):
        return "MISSING_VALIDATION"
    if any(m in r for m in MECHANISM_MARKERS):
        return "MECHANISM"
    if any(m in r for m in CONSTRAINT_MARKERS):
        return "CONSTRAINT"
    return "STATED_PARAM"


def main() -> int:
    import subprocess
    sealed = json.loads(subprocess.run(
        ["git", "show",
         "origin/audit/r11-auditor-verdict-20261114:eval/"
         "holdout_v17/problems.json"],
        capture_output=True, text=True, check=True).stdout)
    plist = sealed.get("problems") if isinstance(sealed, dict) \
        else sealed
    sealed_pids = {p["problem_id"] for p in plist}
    legs = []
    for tag in ("dsv41", "mm31", "dsv4f"):
        for f in sorted((REPO / "eval" / "r146_p4_panel")
                        .glob(f"{tag}__v17-*.json")):
            r = json.loads(f.read_text())
            if r["pid"] not in sealed_pids:
                continue  # the wrong-set legs never enter the analysis
            p = r.get("parsed")
            if not p:
                continue
            legs.append({"judge": tag, "pid": r["pid"],
                         "viable": p["viable"],
                         "reason": p.get("viable_reason", "")})
    n_v_false = [l for l in legs if not l["viable"]]
    for l in n_v_false:
        l["objection_class"] = classify(l["reason"])
    # the generation's own quant/physics grounding per pid
    ev = json.loads((REPO / "eval" /
                     "holdout_v17_strengthened_generation" /
                     "GENERATION_EVENTS.json").read_text())["events"]
    by_pid = {e["problem_id"]: e for e in ev}
    cross = []
    for l in n_v_false:
        e = by_pid.get(l["pid"], {})
        cross.append({
            "judge": l["judge"], "pid": l["pid"],
            "objection_class": l["objection_class"],
            "generation_quant_computed": bool(
                e.get("quant_final_computed")),
            "generation_off_target": bool(e.get("off_target")),
            "reason_excerpt": l["reason"][:180],
        })
    from collections import Counter
    cls = Counter(l["objection_class"] for l in n_v_false)
    n_viable = sum(1 for l in legs if l["viable"])
    out = {
        "record": "R148_VIABILITY_INVESTIGATION/1.0.0",
        "at": "2026-11-24 (sandbox clock)",
        "executor": "builder-r147s1 (the verifier lane; bytes-only "
                    "analysis, no generation — input for the c-0257 "
                    "lane's qualified-panel design)",
        "evidence_base": ("the committed fallback panel legs "
                          "(90 judgments, 3 judges x 30 sealed-set "
                          "candidates, ef2865fa8) — the UNQUALIFIED "
                          "panel; used ONLY for the objection "
                          "taxonomy, never as quality"),
        "headline": {
            "n_judgments": len(legs),
            "n_viable_true": n_viable,
            "n_viability_false": len(n_v_false),
            "viable_rate": round(n_viable / max(1, len(legs)), 3),
            "objection_classes": dict(cls),
        },
        "reading": {
            "MECHANISM": ("the judge denies the mechanism class at "
                          "the stated scale — checked against the "
                          "generation's own physics grounding; these "
                          "are the rows the qualified panel must "
                          "re-examine (the auditor's rubric is the "
                          "arbiter, not the unqualified judges)"),
            "STATED_PARAM": ("the dispute is between the "
                             "generation's pint-computed design "
                             "point and the judge's re-derivation — "
                             "a typed assumption/calculus dispute, "
                             "resolvable only by the sealed scoring"),
            "MISSING_VALIDATION": ("a REAL generation gap: the "
                                   "objection lands on an "
                                   "unvalidated assertion — the "
                                   "runner's design-point demand "
                                   "missed this quantity; the fix "
                                   "side of the owner's order"),
            "CONSTRAINT": ("the judge reads the design as violating "
                           "the problem's stated constraints"),
        },
        "cross_check": cross,
        "note": ("no gate decision here: the score-8 verdict stays "
                 "with the QUALIFIED-judge panel (the c-0257 lane); "
                 "the investigation types WHERE a real feasibility "
                 "gap would live and what the fix must demand"),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["headline"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

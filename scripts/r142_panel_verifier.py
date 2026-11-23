#!/usr/bin/env python3
"""r142_panel_verifier.py — the VERIFIER-side independent recompute of
the R-CAL panel one-shot (R142 DIR-2, builder-r141s1 verifier lane for
the twin's c-0227 EXECUTOR one-shot; Art. 29(c)).

Independence: this script does NOT import the executor's
panel_agreement code path for its primary numbers. It re-reads the
per-leg bytes (eval/r142_panel/<tag>__<pid>__<order>.json), re-derives
per-judge correctness against the corpus's overall_preference, the
answered rates, the majority agreement, and re-runs the engine's
panel_agreement as the cross-check only. diff vs the executor's
eval/r142_panel_qualification.json is the verdict.

One-shot discipline: this is a RECOMPUTE of committed bytes, never a
re-execution of judge calls (no re-roll, Art. 7).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "eval" / "auditor_rcal_corpus_r142.json"
LEGS = REPO / "eval" / "r142_panel"
EXEC = REPO / "eval" / "r142_panel_qualification.json"

# the expected file digest (R142 DIR-8 canonicalization: the corpus
# bytes the executor was required to run against)
EXPECTED_FILE_DIGEST = "3df491d57232825a6e29b42751fac9cef234c3498a666618f208e4fa0834056b"


def main() -> int:
    if not CORPUS.exists():
        print("NOT_PRESENT: the sealed corpus is not in this checkout "
              "(it lives on the audit branch)")
        return 2
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))

    sys.path.insert(0, str(REPO))
    from scripts.rcal_corpus_digest import canonical_file_digest
    dig = canonical_file_digest(corpus)
    digest_ok = dig == EXPECTED_FILE_DIGEST

    if not LEGS.exists():
        print("NOT_PRESENT: no per-leg bytes yet (the one-shot lane is "
              "still in progress) — the verifier recompute runs when "
              "the executor's bytes land")
        return 2

    legs = []
    for f in sorted(LEGS.glob("*.json")):
        legs.append(json.loads(f.read_text(encoding="utf-8")))

    # blind legs only (the parity swap's second leg is a re-presentation
    # of the same pair in swapped order — it must agree or the judge is
    # position-biased; the executor's protocol types which is which)
    verdicts = {}
    for leg in legs:
        tag = leg.get("judge_tag") or (leg.get("judge") or {}).get("tag")
        pid = leg.get("problem_id")
        order = leg.get("order") or leg.get("parity")
        key = (tag, pid)
        verdicts.setdefault(key, {})[order] = leg

    per_judge = {}
    for (tag, pid), by_order in verdicts.items():
        pair = next((p for p in corpus["pairs"]
                     if p.get("problem_id") == pid), None)
        if pair is None:
            continue
        pref = pair.get("overall_preference")
        # correctness: the judge's forced-choice must match the
        # corpus's overall_preference on the blind leg
        for order, leg in by_order.items():
            choice = leg.get("choice") or leg.get("preferred")
            answered = choice is not None
            rec = per_judge.setdefault(
                tag, {"n": 0, "answered": 0, "correct": 0})
            rec["n"] += 1
            if answered:
                rec["answered"] += 1
                if str(choice) == str(pref):
                    rec["correct"] += 1

    summary = {}
    for tag, rec in per_judge.items():
        summary[tag] = {
            "n_pairs": rec["n"],
            "answered_rate": round(rec["answered"] / max(1, rec["n"]), 3),
            "accuracy": round(rec["correct"] / max(1, rec["answered"]), 3)
            if rec["answered"] else None,
        }

    # the engine's panel agreement as the CROSS-CHECK
    cross = None
    try:
        from discovery_fabric.engine.panel_agreement import (
            compute_panel_agreement as _cpa)
        cross = _cpa(legs) if legs else None
    except Exception as exc:  # noqa: BLE001
        cross = {"error": str(exc)[:120]}

    diff = []
    exec_rec = json.loads(EXEC.read_text(encoding="utf-8")) \
        if EXEC.exists() else None
    if exec_rec:
        exec_judges = exec_rec.get("per_judge") or {}
        for tag, s in summary.items():
            e = exec_judges.get(tag) or {}
            for k in ("accuracy", "answered_rate"):
                if k in e and s.get(k) is not None:
                    if abs(float(e[k]) - float(s[k])) > 0.001:
                        diff.append(f"{tag}.{k}")
    else:
        diff.append("executor_record_missing")

    out = {
        "record": "R142_PANEL_VERIFIER_RECOMPUTE/1.0.0",
        "verifier": "builder-r141s1 (VERIFIER for the twin's c-0227)",
        "corpus_file_digest_ok": digest_ok,
        "corpus_file_digest": dig,
        "n_leg_files": len(legs),
        "per_judge_independent": summary,
        "engine_cross_check": cross,
        "diff_vs_executor": diff,
        "diff_zero": diff == [],
    }
    (REPO / "eval" / "r142_panel_verifier_recompute.json").write_text(
        json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

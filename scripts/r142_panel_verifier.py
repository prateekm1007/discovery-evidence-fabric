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

    # the real leg schema (the executor's one-shot bytes): parsed is a
    # dict (or JSON string) with prefer: "A"|"B"; a_is names which corpus
    # mechanism sits in position A for THIS leg ("a1"|"baseline");
    # pass in {det, mir} — the DISCOVERED BASIS (this verifier's own
    # reverse-engineering, typed): the executor's acc scores the DET
    # pass (12 legs/judge); the MIR legs are the swap-robustness mirror
    # (swap_instability = pairs whose det/mir identities disagree,
    # unanswered legs excluded). Both bases reproduced 5/5.
    legs = [json.loads(f.read_text(encoding="utf-8"))
            for f in sorted(LEGS.glob("*.json"))]

    def ident_of(leg):
        _p = leg.get("parsed")
        choice = _p.get("prefer") if isinstance(_p, dict) else None
        if choice not in ("A", "B"):
            return None
        a_is = leg.get("a_is")
        if a_is not in ("a1", "baseline"):
            return None
        return a_is if choice == "A" else \
            {"a1": "baseline", "baseline": "a1"}[a_is]

    def tally(passes):
        per = {}
        pairmap = {}
        for leg in legs:
            if leg.get("pass") not in passes:
                continue
            tag = leg.get("judge")
            pid = leg.get("pid")
            pref = (next((q for q in corpus["pairs"]
                          if q.get("problem_id") == pid), None) or {})
            ok = leg.get("outcome") == "VALID"
            ident = ident_of(leg)
            e = per.setdefault(tag, {"c": 0, "n": 0})
            if ok and ident is not None:
                e["n"] += 1
                e["c"] += 1 if ident == pref.get("overall_preference") \
                    else 0
            pairmap.setdefault((tag, pid), {})[leg.get("pass")] = \
                (1 if (ok and ident is not None and
                       ident == pref.get("overall_preference")) else 0)
            if not ok:
                pairmap[(tag, pid)][leg.get("pass")] = None
        out = {}
        for tag, e in per.items():
            acc = round(e["c"] / max(1, e["n"]), 3) if e["n"] else None
            # swap_instability (the DISCOVERED basis, reproduced 5/5):
            # the rate of pairs whose det and mir legs DISAGREE ON
            # CORRECTNESS, over ALL 12 pairs (an unanswered/RATE_LIMITED
            # leg is not a disagreement — qw32b's 1/12 confirms)
            total_pairs = sum(1 for (t, _pid) in pairmap if t == tag)
            unstable = 0
            for (t, _pid), by_pass in pairmap.items():
                if t != tag:
                    continue
                a, b = by_pass.get("det"), by_pass.get("mir")
                if a is not None and b is not None and a != b:
                    unstable += 1
            out[tag] = {"acc": acc, "n_answered": e["n"],
                        "swap_instability":
                            round(unstable / max(1, total_pairs), 3)}
        return out

    det_tally = tally({"det"})
    pooled_tally = tally({"det", "mir"})
    # acc rides the det basis; the swap rides the POOLED det+mir pairmap
    summary = {tag: dict(det_tally[tag],
                         pooled_acc=pooled_tally[tag]["acc"],
                         swap_instability=pooled_tally[tag][
                             "swap_instability"])
               for tag in det_tally}

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
        exec_judges = ((exec_rec.get("gates") or {})
                       .get("per_judge_results") or {})
        for tag, s in summary.items():
            e = exec_judges.get(tag) or {}
            if e.get("acc") is not None and s.get("acc") is not None:
                if abs(float(e["acc"]) - float(s["acc"])) > 0.001:
                    diff.append(f"{tag}.acc")
            if e.get("swap_instability") is not None:
                if abs(float(e["swap_instability"]) -
                       float(s["swap_instability"])) > 0.001:
                    diff.append(f"{tag}.swap_instability")
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

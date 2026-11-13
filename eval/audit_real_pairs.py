"""eval/audit_real_pairs.py — the REAL-PAIRS acceptance test for the
structured constraint audit (owner audit round 2026-11-12, directive 1).

"TEST ON THE COMMITTED REAL PAIRS ONLY: fu-004, new04, new01, sofc must
be flagged; new02, fu-001, p02 must pass. No hand-built fixtures as the
only evidence."

What it does:
  1. Loads the AUDITED composer-era answers for the 9 judged pairs —
     the committed bytes the auditor judged (eval/runs/<commit>/...
     ANSWER_COMPOSED.json + the committed pair files), and the real
     problem context from eval/problems_dev12.json.
  2. Runs the deterministic floor (audit_constraints) on each.
  3. Runs the structured LLM check (llm_constraint_check — ONE call per
     problem) on each answer against the real constraints.
  4. Prints the verdict table; the acceptance rule is applied to the
     MERGED audit (floor + LLM check):
       must flag   : dev-fu-004, eval-new04, eval-new01, eval-sofc
       must pass   : eval-new02, dev-fu-001, bench-p02
  5. Writes the record to eval/runs/<commit>/audit_real_pairs.json
     (the acceptance evidence; rides the round record, never a report).

Usage: python3 eval/audit_real_pairs.py [--runs-root eval/runs]
Requires the zai gateway (the driver's own spawn: ZAI_API_KEY must be
operator-declared; see scripts/r6_run_dev12.sh for the route contract).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

#: the audited composer-era answers: for each judged problem, the run
#: whose ANSWER_COMPOSED.json carries the answer the auditor judged.
#: Resolved live from the run tree (latest run with a non-empty answer
#: for the problem), so the bytes are always the committed ones.
TARGETS_MUST_FLAG = ("dev-fu-004-fouling",
                     "eval-new04-chiller-fouling-predictor",
                     "eval-new01-supercap-dryout",
                     "eval-sofc-thermal-cycling")
TARGETS_MUST_PASS = ("eval-new02-slipring-predictor",
                     "dev-fu-001-bearing-spalling",
                     "bench-p02-leadacid-grid-corrosion")
ALL_JUDGED = TARGETS_MUST_FLAG + TARGETS_MUST_PASS


def _audited_answer(runs_root: Path, pid: str):
    """The committed audited answer for a problem — the REAL pair bytes,
    never hand fixtures. Resolution order (deterministic, disclosed on
    the row):
      1. The committed pair file eval/pairs/dev12_fresh/<pid>.json —
         the audited bytes the auditor judged (fu-004/sofc
         byte-RESTORED 2026-11-13 after commit 22cb7f5cd had
         re-committed them with pipeline_answer: null). The RETIRED
         banner text ("CONTRACT-INVALID COMPOSITION ...") is NOT a
         proposal: when the pair file carries only the banner, the
         pair's committed restoration.constraint_audit_input (the
         composition the verdicts ran on, sofc sha 6cb5453c) is the
         audit input — COMMITTED bytes, no gitignored tree needed
         (owner round 2026-11-13: the acceptance evidence must be
         rerunnable from committed bytes alone).
      2. The AUDITED run tree eval/runs/977851bc16a5 (the runs the
         af7e2a03f pairs were built from — the kill records cite these
         run dirs): the problem's latest record with a non-empty
         answer. Measured identity: the fu-004 record here is
         byte-identical to the af7e2a03f pair answer (sha f691cd9101dd);
         the fu-001/new01/new02/new04 records are byte-identical to the
         committed pair answers.
      3. Any other run tree (DISCLOSED as non-audited — never used for
         the acceptance verdict without note)."""
    pair_p = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
    if pair_p.exists():
        try:
            d = json.loads(pair_p.read_text(encoding="utf-8"))
            ans = d.get("pipeline_answer")
            if isinstance(ans, str) and ans.strip() \
                    and not ans.lstrip().startswith(
                        "CONTRACT-INVALID COMPOSITION"):
                return {"answer": ans, "source": str(pair_p),
                        "state": "pair_bytes(committed)"}
            # banner-only pair: the committed audit-input composition
            # (restoration.constraint_audit_input) is the audit plane
            r = d.get("restoration") or {}
            cai = (r.get("constraint_audit_input") or {})
            ctext = cai.get("text")
            if isinstance(ctext, str) and ctext.strip():
                return {"answer": ctext, "source": str(pair_p),
                        "state": "pair_bytes(committed:"
                                 "constraint_audit_input)",
                        "audit_input_sha256_8":
                            cai.get("sha256_8")}
        except Exception:  # noqa: BLE001
            pass
    audited = runs_root / "977851bc16a5"
    for root in (audited, runs_root):
        best = None
        for f in sorted(glob.glob(str(
                root / "*" / "*" / "pipeline" / "ANSWER_COMPOSED.json"))):
            if f"/{pid}/" not in f:
                continue
            try:
                d = json.loads(Path(f).read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            ans = d.get("answer")
            if isinstance(ans, str) and ans.strip() \
                    and not ans.lstrip().startswith(
                        "CONTRACT-INVALID COMPOSITION"):
                if best is None or f > best[0]:
                    best = (f, ans, d.get("state"))
        if best:
            return {"answer": best[1], "source": best[0],
                    "state": best[2],
                    "audited_tree": str(root) == str(audited)}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default="eval/runs")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    runs_root = REPO / args.runs_root

    probs = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval/problems_dev12.json").read_text(
            encoding="utf-8"))["problems"]}

    from discovery_fabric.engine.constraint_audit import (
        audit_constraints, llm_constraint_check, llm_check_violations)
    from discovery_fabric.engine.mechanism_space import llm_generate

    rows = []
    for pid in ALL_JUDGED:
        prob = probs.get(pid)
        got = _audited_answer(runs_root, pid)
        if prob is None or got is None:
            rows.append({"problem_id": pid, "error": "missing "
                         + ("problem" if prob is None else "answer")})
            continue
        ans = got["answer"]
        floor = audit_constraints(prob, ans)
        check = llm_constraint_check(prob, ans, llm_generate)
        viol_types = [v["type"] for v in floor.get("violations") or []]
        llm_types = [v["type"] for v in llm_check_violations(check)]
        merged = viol_types + llm_types
        rows.append({
            "problem_id": pid,
            "answer_source": got["source"],
            "answer_state": got["state"],
            "floor": {"state": floor.get("state"),
                      "violations": viol_types},
            "llm_check": {"state": check.get("state"),
                          "n_violations": check.get("n_violations"),
                          "verdicts": check.get("verdicts"),
                          "restates_device": check.get("restates_device"),
                          "restates_constraint":
                              check.get("restates_constraint"),
                          "violations": llm_types,
                          "provider": check.get("provider"),
                          "model": check.get("model")},
            "merged_flagged": bool(merged),
            "merged_violation_types": merged,
        })
        tag = "FLAG " if merged else "PASS "
        print(f"[audit-real] {tag} {pid}: floor={floor.get('state')}"
              f"({len(viol_types)}) llm={check.get('state')}"
              f"({check.get('n_violations')})", flush=True)
        for v in (check.get("verdicts") or []):
            print(f"    C{v.get('constraint_index')}: {v.get('verdict')}"
                  f" quote_verified={v.get('quote_verified')}"
                  f" :: {str(v.get('quote'))[:90]}", flush=True)

    flagged = {r["problem_id"] for r in rows if r.get("merged_flagged")}
    ok = True
    for pid in TARGETS_MUST_FLAG:
        if pid not in flagged:
            ok = False
            print(f"[audit-real] ACCEPTANCE FAIL: {pid} not flagged",
                  flush=True)
    for pid in TARGETS_MUST_PASS:
        if pid in flagged:
            ok = False
            print(f"[audit-real] ACCEPTANCE FAIL: {pid} must pass "
                  "but flagged", flush=True)
    print(f"[audit-real] ACCEPTANCE "
          f"{'PASS' if ok else 'FAIL'}: flagged={sorted(flagged)}",
          flush=True)

    out = args.out or (runs_root / "audit_real_pairs.json")
    Path(out).write_text(json.dumps(
        {"instrument": "audit_real_pairs/1.0",
         "acceptance": "PASS" if ok else "FAIL",
         "targets_must_flag": list(TARGETS_MUST_FLAG),
         "targets_must_pass": list(TARGETS_MUST_PASS),
         "rows": rows}, indent=1, default=str) + "\n",
        encoding="utf-8")
    print(f"[audit-real] record: {out}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""R510 A2 DEV rerun (B2) — 2.1.0 repetition on the frozen R492 DEV corpus, outputs to R510/.

Reuses scripts/r505_a2_strong_ring.py's frozen measurement functions
(_freeze_check, _identity_gate, _post_case, _rule45_firings, score) WITHOUT
editing that file. Only the output parent differs (R510/, per the §8.3
placement law — never write into another round's directory). Same
anti-shopping discipline as r505: verdict-class records are final, transport
failures retry honestly, freeze re-verified post-run, identical six-field
headline. DEV corpus only; sealed corpora are hashed for the no-leak proof
and never executed (Art. LIX).
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

if not shutil.which("git"):  # Windows stock PATH gap (measured R510-C1)
    for _d in (r"C:\Program Files\Git\cmd", r"C:\Program Files\Git\bin",
               "/usr/bin", "/usr/local/bin"):
        if os.path.isfile(os.path.join(
                _d, "git.exe" if os.name == "nt" else "git")):
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
            break

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import r505_a2_strong_ring as m  # noqa: E402  (frozen instrument, read-only use)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="xkiro")
    ap.add_argument("--pace", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="A2_V42_XKIRO_RERUN")
    ap.add_argument("--abort-after-failures", type=int, default=6)
    a = ap.parse_args()

    m.OUT_DIR = REPO / "R510" / a.out
    m.RAW_DIR = m.OUT_DIR / "RAW"
    m.RESULTS_PATH = m.OUT_DIR / "MEASUREMENT_RESULTS.json"

    sha = m._freeze_check()
    m._log(f"frozen corpus verified: {sha[:16]}...")
    identity = m._identity_gate()
    m.RAW_DIR.mkdir(parents=True, exist_ok=True)
    corpus = json.loads(m.CORPUS_PATH.read_text())
    cases = corpus["cases"][:a.limit] if a.limit else corpus["cases"]
    (m.OUT_DIR / "IDENTITY.json").write_text(
        json.dumps(identity, indent=1), encoding="utf-8", newline="\n")
    consecutive_failures = 0
    for i, case in enumerate(cases, 1):
        cid = case["case_id"]
        rec = m._post_case(case, a.provider)
        attack = rec.get("attack") or {}
        if rec.get("http") == 200 and attack.get("overall"):
            m._log(f"  overall={attack.get('overall')} "
                   f"rule45={m._rule45_firings(attack)} "
                   f"latency={rec.get('latency_s')}s")
        else:
            m._log(f"  TRANSPORT FAILURE http={rec.get('http')} "
                   f"error={json.dumps(rec.get('error'))[:160]}")
        (m.RAW_DIR / f"{cid}.json").write_text(
            json.dumps(rec, indent=1), encoding="utf-8", newline="\n")
        got_verdict = (rec.get("http") == 200 and attack.get("overall") in
                       ("KILLED", "PASS", "ADVERSARIAL_INVALID"))
        consecutive_failures = 0 if got_verdict else consecutive_failures + 1
        if a.abort_after_failures and \
                consecutive_failures >= a.abort_after_failures:
            m._log("  PHASE EARLY-STOP: pinned ring measurably down; "
                   "partial records stand, scored post-hoc honestly")
            break
        if i < len(cases):
            time.sleep(a.pace)
    post = m._freeze_check()
    if post != sha:
        raise SystemExit("FATAL: corpus bytes changed DURING the run")
    m._log("freeze re-verified post-run")
    r = m.score()
    # r505's own RESULTS write uses platform text mode (CRLF on Windows);
    # that file is frozen-instrument output, so normalize the emitted bytes
    # to LF here instead of editing the instrument (placement/freeze law).
    for _p in (m.RESULTS_PATH, m.OUT_DIR / "IDENTITY.json"):
        _p.write_text(_p.read_text(encoding="utf-8"), encoding="utf-8",
                      newline="\n")
    for _p in m.RAW_DIR.glob("*.json"):
        _p.write_text(_p.read_text(encoding="utf-8"), encoding="utf-8",
                      newline="\n")
    h = r["headline"]
    m._log(f"HEADLINE: TPR={h['tpr_defect_cohorts']} FPR={h['fpr_known_good']} "
           f"coverage={h['coverage_all_9_fields']} parse={h['parse_completeness']} "
           f"rule45={r['rule45_attacker_computes']['total_firings']} "
           f"verdict={r['threshold_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

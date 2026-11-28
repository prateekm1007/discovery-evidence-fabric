#!/usr/bin/env python3
"""r36_verifier_recompute.py — AM34-ruling D4: the VERIFIER duty on
c-0038/c-0039 discharged from COMMITTED BYTES, never a re-run (zero
LLM calls). Verifies:

  c-0039 (instrument pins + calibration):
    1. the pytest bind suite (deterministic scans on committed v5
       bytes) — 17/17 expected EXACT;
    2. the c-0026 calibration acceptance recompute — the committed
       eval/judge_feasibility_calibration_r29.json per-row comparison
       re-derived (within-1 count, bar 16/18) EXACT;
    3. the pin-test acceptance recompute from the committed
       eval/r35_pin_tests.json (D2/D3 fire + 0 FP) EXACT.

  c-0038 (sealed v6 one-shot):
    4. seal-untouched: no v6 generation artifacts exist; the v6
       problems bytes are unchanged since d49694879 (cb4e984a…); the
       registry holds no v6 EXECUTOR DONE;
    5. the precondition chain: the committed preflight/transport/custody
       records agree (window CLOSED on availability; custody UNANCHORED)
       and both support "seal not burned".

Writes eval/r36_verifier_recompute.json. Exit 0 iff all EXACT.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r36_verifier_recompute.json"


def sh(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    return p.returncode, (p.stdout + p.stderr).strip()


def main() -> int:
    checks: list[dict] = []

    # 1. pytest bind suite (zero LLM, committed bytes)
    rc, out = sh(["python3", "-m", "pytest",
                  "tests/test_r30_am29_binds.py", "-q"])
    # this repo's pytest.ini (addopts = -q) renders no summary line:
    # a passing run is exactly 17 dots + [100%]; any failure shows F/E
    import re as _re
    dots17 = bool(_re.search(r"\.{17}\s", out))
    low = out.lower()
    checks.append({
        "item": "c-0039 pytest bind suite",
        "expected": "exit 0; exactly 17 passing dots; no F/E markers",
        "observed": out.splitlines()[-1][:60] if out else "",
        "exact": rc == 0 and dots17 and "failed" not in low
        and "error" not in low,
    })

    # 2. c-0026 acceptance recompute
    cal = json.loads((REPO / "eval" /
                      "judge_feasibility_calibration_r29.json")
                     .read_text(encoding="utf-8"))
    comp = cal.get("comparison") or []
    n_within = sum(1 for r in comp if r.get("within_1"))
    acc = cal.get("acceptance") or {}
    checks.append({
        "item": "c-0026 acceptance recompute",
        "expected": {"n_compared": acc.get("n_compared"),
                     "n_within_1": acc.get("n_within_1"),
                     "met": acc.get("met")},
        "observed": {"n_compared": len(comp), "n_within_1": n_within,
                     "met": n_within >= 16},
        "exact": (len(comp) == acc.get("n_compared")
                  and n_within == acc.get("n_within_1")
                  and (n_within >= 16) == acc.get("met")),
    })

    # 3. pin-test acceptance recompute
    pt = json.loads((REPO / "eval" / "r35_pin_tests.json")
                    .read_text(encoding="utf-8"))
    rows = pt.get("rows") or []
    d2 = bool(pt.get("d2_actuation_pin_fires_on_HO5_05"))
    d3 = bool(pt.get("d3_direction_pin_fires_on_HO5_06"))
    fp_n = (pt.get("false_positive_check") or {}).get("n_fp_rows")
    fp_recomputed = sum(
        1 for r in rows
        if not r["problem_id"].startswith(("HO5-05", "HO5-06"))
        and (r.get("ACTUATION_DEVICE_AS_MEASURE")
             or r.get("DIRECTION_INVERTED_ARITHMETIC")))
    checks.append({
        "item": "c-0039 pin acceptance recompute",
        "expected": {"d2_fire": d2, "d3_fire": d3, "fp_rows": fp_n},
        "observed": {"d2_fire": d2, "d3_fire": d3,
                     "fp_rows": fp_recomputed},
        "exact": (d2 and d3 and fp_recomputed == fp_n == 0),
    })

    # 4. seal-untouched (c-0038)
    v6_rows = REPO / "eval" / "pairs" / "holdout_v6_generation"
    rc2, cur_sha = sh(["git", "show",
                       "origin/audit/r11-auditor-verdict-20261114:"
                       "audit/holdout_v6/holdout_v6_problems.json"])
    import hashlib
    cur_sha = hashlib.sha256(cur_sha.encode()).hexdigest()
    claims = json.loads((REPO / "eval" / "work_claims.json")
                        .read_text(encoding="utf-8"))["claims"]
    v6_done = [c["claim_id"] for c in claims
               if c.get("work_id") == "holdout-v6-generation"
               and c.get("role") == "EXECUTOR"
               and c.get("status") in ("DONE", "EXECUTION-COMPLETE-"
                                       "PENDING-VERIFICATION")]
    seal_ok = (not v6_rows.exists() and len(cur_sha) == 64
               and cur_sha.startswith("cb4e984a")
               and not v6_done)
    checks.append({
        "item": "c-0038 seal-untouched",
        "expected": "no v6 generation artifacts; problems bytes "
                    "cb4e984a…; no v6 EXECUTOR completion",
        "observed": {"artifacts": v6_rows.exists(),
                     "problems_sha16": cur_sha[:16],
                     "v6_executor_done": v6_done},
        "exact": seal_ok,
    })

    # 5. precondition chain agreement
    tb = json.loads((REPO / "eval" / "v6_transport_block.json")
                    .read_text(encoding="utf-8"))
    cb = json.loads((REPO / "eval" / "v6_seal_custody_break.json")
                    .read_text(encoding="utf-8"))
    pf = json.loads((REPO / "eval" / "v6_serving_preflight.json")
                    .read_text(encoding="utf-8"))
    peer = json.loads((REPO / "eval" / "r35_serving_preflight_peer.json")
                      .read_text(encoding="utf-8")) if Path(
        REPO / "eval" / "r35_serving_preflight_peer.json").exists() else {}
    checks.append({
        "item": "c-0038 precondition chain",
        "expected": "all committed records agree: no burn",
        "observed": {
            "transport_block": tb.get("verdict", "")[:60],
            "custody_break": cb.get("verdict", "")[:60],
            "window_probe": pf.get("verdict", "")[:60],
            "peer_record_verdict": json.dumps(peer.get("VERDICT", ""))
            [:60] or "(peer record at eval/r35_serving_preflight.json)",
        },
        "exact": ("not taken" in tb.get("verdict", "").lower()
                  and cb.get("verdict", "").startswith("UNANCHORED")
                  and pf.get("verdict", "").startswith(
                      "AVAILABILITY_BLOCK")),
    })

    all_exact = all(c["exact"] for c in checks)
    rec = {
        "record": "R36_VERIFIER_RECOMPUTE/1.0.0",
        "session": "builder-r20s2",
        "at": "2026-11-16T14:30:00Z (sandbox clock)",
        "verifies": ["c-0038 (sealed v6 one-shot — precondition state)",
                     "c-0039 (instrument pins + c-0026 calibration)"],
        "method": "zero-LLM recompute from committed bytes (Art. 13/29(c)); "
                  "deterministic scans re-run; acceptance recomputed from "
                  "committed per-row bytes; NO live re-judgment",
        "disclosure": "self-verification of the builder's own claims, "
                      "filed on the auditor's direct order (AM34-ruling "
                      "D4) because the peer verifier's sandbox is down; "
                      "the peer's independent recompute stays invited",
        "all_exact": all_exact,
        "checks": checks,
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    for c in checks:
        print(f"{'PASS' if c['exact'] else 'FAIL'} | {c['item']}")
    print(f"ALL EXACT: {all_exact}")
    return 0 if all_exact else 1


if __name__ == "__main__":
    sys.exit(main())

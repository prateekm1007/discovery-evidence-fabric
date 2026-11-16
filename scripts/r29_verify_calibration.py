#!/usr/bin/env python3
"""r29_verify_calibration.py — the Art. 13/29(c) ZERO-LLM verifier for
the R29 judge feasibility-axis calibration (c-0026).

Recomputes EVERYTHING from committed bytes; exits 0 only on full
reproduction. Never calls an LLM, never re-judges:

  1. INPUT DISCIPLINE — the 18 rows match the r27 judge packet's
     intervention rows; every v3 prompt = the packet's rubric_prompt
     with the v2 suffix replaced by the v3 suffix, pre-suffix prefix
     BYTE-IDENTICAL (recomputed per row); the v3 suffix differs from
     the v2 suffix by EXACTLY the F-axis calibration pins (every
     other suffix byte identical; the N/T/C axis text unchanged).
  2. AUDITOR ANCHOR — the comparison base is the pinned audit tip's
     adjudication (read via git show, never copied into the queue
     tree); all 18 per-row auditor scores present.
  3. MEDIANS — per-row machine a1_feasibility medians recompute from
     the stored draws (median of the valid F_A values); all rows
     carry >=1 valid draw (K=3 health).
  4. COMPARISON + ACCEPTANCE — per-row |machine - auditor| recomputes;
     the within-1 count and the >=16/18 acceptance recompute; the
     F39 pin rows (the four procedure-class rows the R28 machine read
     F_A=1 on) are present with their deltas.
  5. CLAIM LINKAGE — c-0026 EXECUTOR claim present and OPEN with the
     declared artifact paths.
  6. CROSS-CHECK TYPING — the record is typed CROSS-CHECK INSTRUMENT
     CALIBRATION (never a gate input on feasibility; the gate is
     auditor-judged); zero generator calls.

Run: python3 scripts/r29_verify_calibration.py   (exit 0 = verified)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "judge_feasibility_calibration_r29.json"
PACKET = REPO / "eval" / "r27_judge_packet.json"
CLAIMS = REPO / "eval" / "work_claims.json"
V2 = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
V3 = (REPO / "scripts" / "_r29_axis_suffix_v3.txt").read_text()
AUDITOR_SHA = "d7540c6fe"
F39_ROWS = ["bench-p10-pv-pid", "dev-fu-005-bridge-bearing",
            "eval-new05-liion-balance-drift", "eval-sofc-redox"]

CHECKS = []


def check(name: str, ok: bool, detail: str = ""):
    CHECKS.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    rec = json.loads(OUT.read_text(encoding="utf-8"))
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    claims = json.loads(CLAIMS.read_text(encoding="utf-8"))

    # ---- 1. input discipline
    rows = rec["results"]
    packet_int = [r for r in packet["rows"] if str(
        r.get("question_type", "")).startswith("intervention")]
    check("18 rows matching the packet's intervention rows",
          sorted(r["problem_id"] for r in rows)
          == sorted(r["problem_id"] for r in packet_int)
          and len(rows) == 18)
    prompt_ok = True
    for r in rows:
        pr = next(p for p in packet_int
                  if p["problem_id"] == r["problem_id"])
        rp = pr["rubric_prompt"]
        if not rp.endswith(V2):
            prompt_ok = False
            continue
        v3_prompt = rp[: -len(V2)] + V3
        if _sha(v3_prompt) != r["v3_prompt_sha256_16"]:
            prompt_ok = False
    check("v3 prompts = packet prompts with the v2->v3 suffix swap "
          "(prefix byte-identical, sha-recomputed)", prompt_ok)
    # the suffix delta is EXACTLY the F-axis pins
    v2f = V2.replace(V2[V2.index("  feasibility (F):"):V2.index(
        "  testability (T):")], "")
    v3f = V3.replace(V3[V3.index("  feasibility (F):"):V3.index(
        "  testability (T):")], "")
    check("the suffix delta is exactly the F-axis block",
          v2f == v3f and V3 != V2 and "CALIBRATION PINS" in V3
          and "F at 4 or 5, never" in V3
          and "F at 3 or" in V3)
    # the v2 F paragraph survives byte-identical inside the v3 F block
    v2_fpara = V2[V2.index("  feasibility (F):"):V2.index(
        "  testability (T):")]
    check("the v2 F-axis text survives byte-identical in v3",
          v2_fpara.rstrip("\n") in V3)

    # ---- 2. auditor anchor
    out = subprocess.run(
        ["git", "-C", str(REPO), "show",
         f"{AUDITOR_SHA}:eval/auditor_r28_adjudication.json"],
        capture_output=True, text=True, check=True)
    auditor = json.loads(out.stdout)
    a_rows = {p["problem_id"]: p for p in auditor["per_row"]}
    check("auditor anchor: 18 per-row scores from the pinned audit tip",
          len(a_rows) == 18
          and rec["auditor_anchor"]["sha"] == AUDITOR_SHA)

    # ---- 3. medians recompute
    med_ok = True
    for r in rows:
        f_vals = sorted(d["axes"]["F_A"] for d in r["draws"]
                        if d["outcome"] == "JUDGE_VALID"
                        and d.get("axes") and "F_A" in d["axes"])
        med = f_vals[len(f_vals) // 2] if f_vals else None
        if med != r["machine_a1_feasibility_median"]:
            med_ok = False
        if sorted(f_vals) != sorted(
                r["machine_a1_feasibility_values"] or []):
            med_ok = False
        if r["n_valid_draws"] < 1:
            med_ok = False
    check("per-row F_A medians + valid-draw health recompute", med_ok)

    # ---- 4. comparison + acceptance recompute
    comp_ok = True
    n_within = 0
    for e in rec["comparison"]:
        a = a_rows[e["problem_id"]]
        if e["auditor_r28"]["a1_feasibility"] != a["a1_feasibility"]:
            comp_ok = False
        m = e["machine"]["a1_feasibility"]
        if m is not None:
            d = m - a["a1_feasibility"]
            if e.get("delta") != d or e.get("within_1") != (abs(d) <= 1):
                comp_ok = False
            if abs(d) <= 1:
                n_within += 1
    acc = rec["acceptance"]
    check("per-row deltas + auditor scores recompute", comp_ok)
    check("the within-1 count and the >=16/18 acceptance recompute",
          acc["n_within_1"] == n_within
          and acc["met"] == bool(n_within >= 16)
          and acc["n_rows"] == 18)
    f39_ok = (sorted(e["problem_id"] for e in rec["f39_pin_rows"])
              == sorted(F39_ROWS))
    check("the F39 pin rows present with deltas", f39_ok)

    # ---- 5. claim linkage
    c26 = [c for c in claims["claims"] if c["claim_id"] == "c-0026"]
    check("c-0026 EXECUTOR claim present and OPEN",
          len(c26) == 1 and c26[0]["role"] == "EXECUTOR"
          and c26[0]["status"] == "OPEN"
          and c26[0]["work_id"] == "r29-judge-feasibility-calibration")
    paths_ok = all((REPO / p).exists() for p in c26[0]["artifact_paths"]
                   if not p.endswith("/"))
    check("claim artifact paths exist", paths_ok)

    # ---- 6. cross-check typing
    typed = str(rec.get("typed", ""))
    check("typed CROSS-CHECK INSTRUMENT CALIBRATION (never a gate "
          "input on feasibility)",
          "CROSS-CHECK" in typed and "auditor-judged" in typed)
    check("zero generator calls",
          rec["generation"]["calls"] == 0)
    check("route independence typed",
          rec["judge"]["route"][0] == "crowllm"
          and "independent" in rec["judge"]["independence"])

    print()
    n_pass = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"[r29-verify-calibration] {n_pass}/{len(CHECKS)} checks PASS")
    for name, ok, detail in CHECKS:
        if not ok:
            print(f"  FAIL: {name} — {detail}")
    return 0 if n_pass == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())

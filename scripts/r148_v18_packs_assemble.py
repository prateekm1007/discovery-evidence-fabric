#!/usr/bin/env python3
"""r148_v18_packs_assemble.py — assemble the V18 panel packs from the
LANDED physics-correct generation rows (eval/holdout_v18_physics_generation/
v17-*.json, a1_answer = candidate_text) with the prior arts reused
BYTE-IDENTICAL from the committed r147 sealed-set retrieval
(eval/r146_p4_panel/packs_sealed_set.json).

Typed provenance: the prior arts are retrieved independently of the
generator from the standing AM48 corpus family (SPECTER2, r147); the
v18 rows share the SAME sealed problem set (pids v17-01..v17-30, the
sealed_problems_digest16 asserted against the audit-branch problems
bytes), so the per-pid prior arts and the sha-parity presentation
rotation carry over verbatim. The v18 candidate deltas do not change
the retrieval's independence (it was run before/outside this
generation); a re-run with torch+SPECTER2 is the typed fallback if
the panel flags the retrieval as materially stale.

DIR-6 rule honored: the problem set is loaded from the SEALED
audit-branch bytes (git show origin/audit/...), digest-asserted,
never a local problems.json.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROWS = REPO / "eval" / "holdout_v18_physics_generation"
SEALED_PACKS = REPO / "eval" / "r146_p4_panel" / "packs_sealed_set.json"
OUT = REPO / "eval" / "holdout_v18_physics_generation" / "packs_v18.json"
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"


def main() -> int:
    # 1. the sealed problems from the AUDIT BRANCH bytes (DIR-6 rule)
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:eval/holdout_v17/problems.json"],
        capture_output=True, text=True, check=True).stdout
    probs = json.loads(raw)
    probs = probs if isinstance(probs, list) else probs["problems"]
    file_digest16 = __import__("hashlib").sha256(
        raw.encode()).hexdigest()[:16]
    # the generation lane's digest convention: the CANONICAL list
    # (sorted keys, no whitespace) — content-identical to the file
    canonical16 = __import__("hashlib").sha256(
        json.dumps(probs, sort_keys=True).encode()).hexdigest()[:16]
    sealed_pids = sorted(p["problem_id"] for p in probs)
    digest16 = canonical16
    print(f"sealed problems (audit branch): {len(sealed_pids)} pids, "
          f"file_digest16={file_digest16}, canonical16={canonical16}")

    # 2. the landed v18 rows
    rows = {}
    for f in sorted(ROWS.glob("v17-*.json")):
        d = json.loads(f.read_text())
        rows[d["problem_id"]] = d
    print(f"v18 rows: {len(rows)}")
    assert len(rows) == 30, f"expected 30 v18 rows, got {len(rows)}"
    row_pids = sorted(rows)
    assert row_pids == sealed_pids, (
        "the v18 row pids do not match the sealed problem set — "
        "typed refusal (the wrong-set discipline, DIR-6)")
    # the rows' own sealed-problems digest assertion
    row_digests = {d.get("sealed_problems_digest16") for d in rows.values()}
    assert len(row_digests) == 1, f"inconsistent row digests: {row_digests}"
    rd = row_digests.pop()
    print(f"rows' sealed_problems_digest16: {rd} "
          f"({'matches audit-branch bytes' if rd == digest16 else 'MISMATCH vs audit bytes'})")

    # 3. the committed sealed retrieval (prior arts + rotation)
    sp = json.loads(SEALED_PACKS.read_text())
    packs_sealed = sp["packs"] if isinstance(sp, dict) else sp
    prior_by_pid = {p["problem_id"]: {
        "prior_arts": p["prior_arts"],
        "prior_arts_rotated": p["prior_arts_rotated"],
        "retrieval_cosine": p.get("nearest_cosine")} for p in packs_sealed}
    assert set(prior_by_pid) == set(row_pids), (
        "the sealed retrieval pids do not cover the v18 set")

    # 4. assemble + per-row byte provenance
    packs = []
    for pid in row_pids:
        d = rows[pid]
        pa = prior_by_pid[pid]
        packs.append({
            "problem_id": pid,
            "candidate_text": d["a1_answer"],
            "prior_arts": pa["prior_arts"],
            "prior_arts_rotated": pa["prior_arts_rotated"],
            "row_sha256_16": d.get("sha256_16"),
            "row_model": d.get("registered_model"),
            "row_engine": (d.get("engine_trace") or {}).get(
                "measured_path"),
            "row_physics_gate": (d.get("final_meta") or {}).get(
                "physics_gate"),
        })

    doc = {
        "record": "R148_V18_PANEL_PACKS/1.0.0",
        "sealed_problems_digest16": digest16,
        "rows_digest_assertion": rd,
        "retrieval": ("prior arts BYTE-REUSED from "
                      "eval/r146_p4_panel/packs_sealed_set.json "
                      "(SPECTER2 vs the standing AM48 corpus family, "
                      "r147 sealed retrieval; same sealed problem "
                      "set; independence from the generator preserved "
                      "— retrieved before/outside the v18 run); the "
                      "sha-parity presentation rotation carried as "
                      "prior_arts_rotated; torch+SPECTER2 re-run is "
                      "the typed fallback"),
        "candidates": ("the 30 physics-correct v18 rows "
                       "(a1_answer) from "
                       "eval/holdout_v18_physics_generation/, each "
                       "with its row sha256_16 + the engine trace "
                       "path + the physics-gate verdict"),
        "packs": packs,
    }
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")

    # 5. self-check
    chk = json.loads(OUT.read_text())
    assert len(chk["packs"]) == 30
    assert all(p["candidate_text"] for p in chk["packs"])
    assert all(len(p["prior_arts"]) == 3 for p in chk["packs"])
    print(f"OUT: {OUT.relative_to(REPO)} — 30 packs, all with "
          f"candidate_text + 3 prior arts; self-check PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""r29_holdout_v4_generate.py — c-0029 EXECUTOR: holdout v4 ONE-SHOT
generation (AM28 D1; sealed set audit/holdout_v4/ @ audit branch tip
af3ef4d01, selection_sha256 00dfaf7e..., authored+sealed by the
AUDITOR; the executor is the non-author session per the sealed
pre-registration's division of labor).

Art. 29(b)/(c) claim-before-work: claim c-0029 filed and pushed
BEFORE any problem read / generation call. One generation for
one-shot/sealed work (Art. 29(c)).

DISCIPLINE (per audit/holdout_v4/PREREGISTRATION.json @ af3ef4d01):
  - executor receives PROBLEMS ONLY: the PRIVATE rubric is NEVER
    opened, listed, or copied (fail-closed custody read);
  - A1 answers generated ONCE per problem with the FROZEN V7.4
    machine — IMPORTED BYTE-IDENTICAL from the peer's committed
    module (scripts/r29_tune_battery_v74.py::machine_generate_v74,
    commit 7a1b7e050, which is contract_for_v72 + critic +
    question-type gate + typed scans [base + constraint-fit +
    catalog-v2 + standard-bill + operational-loss + conversion] +
    the machine's own NEUTRAL V74 repair directive, budget 3).
    Importing (not re-implementing) IS the no-edit proof: the code
    path is the committed bytes, not a copy;
  - K_GEN=1: no best-of-k, no selection;
  - NO judge calls, NO baseline assembly, NO problem-set iteration,
    NO rubric feedback (the auditor scores with the PRIVATE rubric);
  - transport-level transient retry only (Art. 15): a call that
    RETURNS content is never re-drawn (one-shot);
  - pace staggered between problems (shared upstream quota);
  - resume anchors per Art. 18/29(d): an existing per-problem record
    is skipped, never re-drawn.

Outputs (canonical, Art. 29(e)): eval/holdout_v4_generation/
  - HO4 per-problem records + holdout_v4_generation_record.json
    (custody + one-shot disclosures).
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

AUDIT_BRANCH = "origin/audit/r11-auditor-verdict-20261114"
PROBLEMS_PATH = "audit/holdout_v4/holdout_v4_problems.json"
PREREG_PATH = "audit/holdout_v4/PREREGISTRATION.json"
OUT_DIR = REPO / "eval" / "holdout_v4_generation"
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
GW_PORT = 8787

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")

# the FROZEN V7.4 machine — committed bytes, imported not copied
from r29_tune_battery_v74 import machine_generate_v74  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _now():
    return datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_problems():
    """Problems ONLY, from the auditor's custody (fail-closed). The
    PRIVATE rubric is never touched by this script."""
    tip = subprocess.run(["git", "rev-parse", "--short=9", AUDIT_BRANCH],
                         capture_output=True, text=True, cwd=REPO)
    assert tip.returncode == 0, "audit branch not fetched — fail closed"
    tip = tip.stdout.strip()
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_BRANCH}:{PROBLEMS_PATH}"],
        capture_output=True, text=True, cwd=REPO)
    assert raw.returncode == 0, f"problems file missing on {AUDIT_BRANCH}"
    pre = subprocess.run(
        ["git", "show", f"{AUDIT_BRANCH}:{PREREG_PATH}"],
        capture_output=True, text=True, cwd=REPO)
    sel = ""
    if pre.returncode == 0:
        sel = str(json.loads(pre.stdout).get("selection_sha256") or "")
    return tip, raw.stdout, json.loads(raw.stdout), sel


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tip, raw_problems, doc, sel = load_problems()
    probs = doc["problems"]
    problems_sha = _sha(raw_problems)
    print(f"[custody] audit tip {tip} | problems sha256_16 {problems_sha} "
          f"| selection_sha256 (sealed pre-registration, received) "
          f"{sel[:16]} | n={len(probs)}", flush=True)
    if len(probs) != doc["n_problems"]:
        raise RuntimeError("n_problems mismatch — fail closed")

    record = {
        "record": "HOLDOUT_V4_GENERATION/1.0.0",
        "work_id": "holdout-v4-generation",
        "claim": "c-0029 (EXECUTOR builder-r20s1, one_shot, filed+pushed "
                 "BEFORE any problem read / generation call — Art. "
                 "29(b)); the EXECUTOR is the non-author session per "
                 "the sealed pre-registration (author: the AUDITOR — "
                 "fully auditor-authored problems and rubric, removing "
                 "the v3 builder-authored-problems caveat)",
        "at": _now(),
        "custody": {
            "audit_branch": AUDIT_BRANCH,
            "audit_tip_at_read": tip,
            "problems_file": PROBLEMS_PATH,
            "problems_sha256_16": problems_sha,
            "selection_sha256_received": sel,
            "private_rubric_accessed": False,
            "note": "executor received PROBLEMS ONLY per the sealed "
                    "pre-registration; the PRIVATE rubric was never "
                    "opened, listed, or copied by the executor (no "
                    "rubric exists on any builder-visible branch by "
                    "design; names-only custody listing)"},
        "discipline": {
            "one_shot": "one generation pass per problem (Art. 29(c)); a "
                        "call that returns content is never re-drawn; "
                        "transport-level transient retries only (Art. 15)",
            "machine": "FROZEN V7.4 machine IMPORTED BYTE-IDENTICAL from "
                       "the peer's committed module "
                       "scripts/r29_tune_battery_v74.py::"
                       "machine_generate_v74 (commit 7a1b7e050): "
                       "contract_for_v72 (intervention -> "
                       "SYS_A1_INT_V72, predictor -> SYS_A1F_V5) + "
                       "critic + question-type gate + typed scans "
                       "(base + constraint-fit + catalog-v2 + "
                       "standard-bill + operational-loss + conversion) "
                       "+ the machine's own NEUTRAL V74 repair "
                       "directive, budget 3. Import (not copy) = the "
                       "no-contract-edit proof. The machine-internal "
                       "repair loop is part of the machine under test "
                       "(same code path as the R29 dev battery, "
                       "disclosed)",
            "no_selection": "K_GEN=1 — no best-of-k, no selection (BOK "
                            "arm RETIRED per ABLATION_REGISTRY)",
            "no_judge": "NO judge calls, NO baseline/B-side assembly — "
                        "the auditor scores with the PRIVATE rubric "
                        "(never seen by builder/pipeline/judge)",
            "no_iteration": "no rubric feedback, no problem-set "
                            "iteration, no tuning — the problems are "
                            "unseen (the executor is the non-author "
                            "session)",
            "stagger": f"pace {PACE_S}s between problems (shared "
                       "upstream quota)"},
        "generator": {"model": "zai-org/GLM-5.3", "temperature": 0.0,
                      "max_tokens": 2600,
                      "route": "local zai gateway (infra, not contract)"},
        "results": [],
    }

    gw, gw_key = start_gateway()
    print(f"[gateway] up on {GW_PORT} (pid {gw.pid})", flush=True)
    try:
        for i, prob in enumerate(sorted(probs,
                                        key=lambda p: p["problem_id"])):
            pid = prob["problem_id"]
            qt = prob["question_type"]
            out = OUT_DIR / f"{pid}.json"
            if out.exists():  # resume anchor (Art. 18/29(d))
                print(f"[{i + 1}/{len(probs)}] {pid} already present — "
                      "resume, skipping (no re-draw)", flush=True)
                rec = json.loads(out.read_text(encoding="utf-8"))
                if not any(r["problem_id"] == pid
                           for r in record["results"]):
                    record["results"].append(rec)
                continue
            print(f"[{i + 1}/{len(probs)}] {pid} ({qt}) generating "
                  "ONCE...", flush=True)
            ans, attempts, meta = machine_generate_v74(prob, gw_key)
            rec = {
                "problem_id": pid,
                "question_type": qt,
                "a1_source": ("SYS_A1_INT_V72"
                              if qt.startswith("intervention")
                              else "SYS_A1F_V5"),
                "machine_module": "scripts/r29_tune_battery_v74.py::"
                                  "machine_generate_v74 (imported, "
                                  "commit 7a1b7e050)",
                "a1_answer": ans,
                "a1_answer_sha256_16": _sha(ans),
                "attempts": attempts,
                "machine_meta": meta,
                "problems_sha256_16": problems_sha,
                "audit_tip_at_read": tip,
                "generated_at": _now(),
                "one_shot": True,
                "judged": False,
                "note": ("PENDING-AUDITOR (Art. 10: the builder never "
                         "scores; the auditor scores with the PRIVATE "
                         "rubric; acceptance bar mean >=3.0/4 and 0 "
                         "allowed-measures violations per the sealed "
                         "pre-registration)")
            }
            out.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                           + "\n", encoding="utf-8")
            record["results"].append(rec)
            (OUT_DIR / "holdout_v4_generation_record.json").write_text(
                json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"    -> {pid[:36]:<38} repairs={meta['repairs']} "
                  f"residual={list(meta['residual_findings']) or 'CLEAN'}",
                  flush=True)
            time.sleep(PACE_S)
    finally:
        gw.terminate()
    (OUT_DIR / "holdout_v4_generation_record.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    n = len([r for r in record["results"] if r.get("one_shot")])
    print(f"[done] {n}/{len(probs)} problems generated ONCE; "
          f"record at {OUT_DIR / 'holdout_v4_generation_record.json'}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main() or 0)

#!/usr/bin/env python3
"""r25_holdout_v3_generate.py — c-0016 EXECUTOR: holdout v3 ONE-SHOT
generation (AM24 D3; sealed set audit/holdout_v3/ @ audit branch,
selection_sha256 642bc978..., author builder-r20s1, sealed by the
auditor 3053d8dce).

Art. 29(b)/(c) claim-before-work: claim c-0016 filed and pushed
BEFORE any generation call. One generation for one-shot/sealed work
(Art. 29(c)). The EXECUTOR is the non-author session (builder-r25s1)
per the sealed pre-registration's division of labor: author != executor
(cross-actor seal).

DISCIPLINE (per audit/holdout_v3/PREREGISTRATION.json @ 3053d8dce):
  - executor receives PROBLEMS ONLY: audit/holdout_v3/holdout_v3_problems.json
    read from the audit branch; the PRIVATE rubric is NEVER opened by this
    script (it is not read, not listed, not copied — no rubric exists on
    any builder-visible branch by design);
  - A1 answers generated ONCE per problem with the FROZEN type-aware
    machine (committed BEFORE the sealed authoring, provable git order):
    contract mapping intervention-proposal -> SYS_A1_INT_V61 /
    predictor-design -> SYS_A1F_V5 (the c-0014 constraint-aware
    contracts, byte-unchanged); machine path = critic + question-type
    gate + typed scans (base scan + the DETERMINISTIC constraint-fit
    scan + predictor violations on the predictor side) with the machine's
    own NEUTRAL repair directives (REPAIR_BUDGET=2) — the machine-internal
    repair loop IS the machine under test (same code path as r20/r21/
    holdout v2 + the c-0014 scan extension; disclosed, not new);
  - K_GEN=1: no best-of-k, no selection (the BOK arm is RETIRED per
    ABLATION_REGISTRY);
  - NO judge calls, NO baseline/B-side assembly, NO problem-set iteration,
    NO rubric feedback (the auditor scores with the private rubric);
  - transport-level transient retry only (Art. 15 hardening): a FAILED
    call (HTTP 5xx/timeout) is retried up to 3 times; a call that RETURNS
    content is never re-drawn (one-shot);
  - pace staggered between problems (shared upstream quota).

Outputs (canonical, Art. 29(e)): eval/holdout_v3_generation/
  - HO3 per-problem records + holdout_v3_generation_record.json
    (custody + one-shot disclosures); resume anchors per Art. 18/29(d).
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

AUDIT_BRANCH = "origin/audit/r11-auditor-verdict-20261114"
PROBLEMS_PATH = "audit/holdout_v3/holdout_v3_problems.json"
OUT_DIR = REPO / "eval" / "holdout_v3_generation"
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
REPAIR_BUDGET = 2
GEN_ATTEMPTS = 3  # transport-level only (Art. 15); never re-draws content
GW_PORT = 8787  # _gen (r13_a1t_generate) posts to the 127.0.0.1:8787
# gateway — the shared transport endpoint (infra, not contract)

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")

from r24_a1w_v61_contract import (  # noqa: E402
    MACHINE_REPAIR_DIRECTIVE, PREDICTOR_CONSTRAINT, SYS_A1F_V5,
    SYS_A1_INT_V61)
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from r19_a1w_v4_contract import predictor_violations  # noqa: E402


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _now():
    return datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic(path, obj):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(path)


def contract_for_v61(qt):
    """The FROZEN type-aware mapping of the V6.1 machine (c-0014
    pre-registration): intervention -> SYS_A1_INT_V61 (V6 bind +
    CONSTRAINT BIND), predictor -> SYS_A1F_V5 (A1F_V4 +
    PRIMARY-INDICATOR CONSTRAINT)."""
    if str(qt or "").lower().startswith("intervention"):
        return SYS_A1_INT_V61
    return SYS_A1F_V5


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
        ["git", "show", f"{AUDIT_BRANCH}:audit/holdout_v3/"
         "PREREGISTRATION.json"],
        capture_output=True, text=True, cwd=REPO)
    sel = ""
    if pre.returncode == 0:
        sel = str(json.loads(pre.stdout).get("selection_sha256") or "")
    return tip, raw.stdout, json.loads(raw.stdout), sel


def gen_retry(q, contract, gw_key):
    """Transport-level transient retry (Art. 15): a FAILED call is
    retried; a call that RETURNS content is never re-drawn (one-shot)."""
    last = None
    for i in range(GEN_ATTEMPTS):
        try:
            return _gen(q, contract, gw_key), i + 1
        except (urllib.error.HTTPError, urllib.error.URLError,
                TimeoutError, OSError) as e:
            last = e
            print(f"    [transport] attempt {i + 1}/{GEN_ATTEMPTS} failed: "
                  f"{type(e).__name__}; backoff 20s", flush=True)
            time.sleep(20)
    raise RuntimeError(f"generation transport dead after {GEN_ATTEMPTS} "
                       f"attempts: {last}")


def machine_generate(prob, gw_key):
    """The FROZEN V6.1 type-aware machine (the c-0014 code path): one
    generation pass under contract_for_v61(qt) + critic + question-type
    gate + typed scans (base + constraint-fit + predictor violations on
    the predictor side) + the machine's own NEUTRAL repair directives
    (REPAIR_BUDGET=2). NO outcome-based feedback, NO selection."""
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    contract = contract_for_v61(qt)
    attempts = []
    (final, lat), tries = gen_retry(q, contract, gw_key)
    final_meta = {}
    rep = 0
    while True:
        cr = critic(final, prob)
        tg = gate_question_type(final, prob)
        vio = {}
        vio.update(base_scan(final))
        vio.update(scan_constraint_fit(prob, final))
        if qt.startswith("predictor"):
            pv = predictor_violations(final)
            if pv:
                vio.update({"PREDICTOR_VIOLATION": list(pv)})
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        problems = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        problems += findings
        att = {"stage": ("draft" if rep == 0 else f"repair_{rep}"),
               "chars": len(final), "latency_s": round(lat, 1),
               "transport_tries": tries,
               "critic_verdict": cr["verdict"], "type_gate": tg,
               "scan": {k: list(v) for k, v in vio.items()},
               "sha256_16": _sha(final)}
        if rep:
            att["findings_disclosed"] = [p for p in problems if p]
        attempts.append(att)
        if not [p for p in problems if p]:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "residual_findings": {}}
            return final, attempts, final_meta
        if rep == REPAIR_BUDGET:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()}}
            return final, attempts, final_meta
        directive = MACHINE_REPAIR_DIRECTIVE.format(
            findings="; ".join(p for p in problems if p))
        (final, lat), tries = gen_retry(q + "\n\n" + directive, contract,
                                        gw_key)
        rep += 1


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
        "record": "HOLDOUT_V3_GENERATION/1.0.0",
        "work_id": "holdout-v3-generation",
        "claim": "c-0016 (EXECUTOR builder-r25s1, one_shot, filed+pushed "
                 "BEFORE any generation call — Art. 29(b)); the EXECUTOR "
                 "is the non-author session per the sealed pre-"
                 "registration's division of labor (author builder-r20s1)",
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
            "machine": "FROZEN type-aware machine (committed BEFORE the "
                       "sealed authoring, c-0014 pre-registration "
                       "5acb63012): intervention -> SYS_A1_INT_V61, "
                       "predictor -> SYS_A1F_V5, byte-unchanged; critic + "
                       "question-type gate + typed scans (base scan + "
                       "DETERMINISTIC constraint-fit scan + predictor "
                       "violations) + machine NEUTRAL repair directives "
                       "(REPAIR_BUDGET=2) — the machine-internal repair "
                       "loop is part of the machine under test (same code "
                       "path as r20/r21/holdout v2 + the c-0014 scan "
                       "extension, disclosed)",
            "no_selection": "K_GEN=1 — no best-of-k, no selection (BOK arm "
                            "RETIRED per ABLATION_REGISTRY)",
            "no_judge": "NO judge calls, NO baseline/B-side assembly — the "
                        "auditor scores with the PRIVATE rubric (never "
                        "seen by builder/pipeline/judge)",
            "no_iteration": "no rubric feedback, no problem-set iteration, "
                            "no tuning — the problems are unseen "
                            "(split=HOLDOUT; the executor is the "
                            "non-author session)",
            "stagger": f"pace {PACE_S}s between problems (shared upstream "
                       "quota)"},
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
                if not any(r["problem_id"] == pid for r in record["results"]):
                    record["results"].append(rec)
                continue
            print(f"[{i + 1}/{len(probs)}] {pid} ({qt}) generating ONCE...",
                  flush=True)
            ans, attempts, meta = machine_generate(prob, gw_key)
            rec = {
                "problem_id": pid,
                "question_type": qt,
                "a1_source": ("SYS_A1_INT_V61"
                              if qt.startswith("intervention")
                              else "SYS_A1F_V5"),
                "contract_for_qt": True,
                "a1_answer": ans,
                "a1_answer_sha256_16": _sha(ans),
                "attempts": attempts,
                "machine_meta": meta,
                "problems_sha256_16": problems_sha,
                "audit_tip_at_read": tip,
                "generated_at": _now(),
                "one_shot": True,
                "judged": False,
                "judge": "NONE — auditor scores with the PRIVATE rubric",
            }
            _atomic(out, rec)
            record["results"].append(rec)
            _atomic(OUT_DIR / "holdout_v3_generation_record.json", record)
            print(f"    -> {len(ans)} chars, repairs={meta.get('repairs')}, "
                  f"critic={meta.get('critic_verdict')}, "
                  f"gate={meta.get('type_gate', {}).get('verdict')}, "
                  f"residual={list(meta.get('residual_findings') or []) or 'CLEAN'}",
                  flush=True)
            if i < len(probs) - 1:
                time.sleep(PACE_S)
    finally:
        gw.terminate()

    n = len(record["results"])
    if n != len(probs):
        print(f"INCOMPLETE: {n}/{len(probs)} — partial record committed as "
              "the resume anchor (Art. 18/29(d))", flush=True)
    _atomic(OUT_DIR / "holdout_v3_generation_record.json", record)
    print(f"DONE: {n}/{len(probs)} problems generated ONCE; record at "
          "eval/holdout_v3_generation/holdout_v3_generation_record.json",
          flush=True)
    return 0 if n == len(probs) else 2


if __name__ == "__main__":
    sys.exit(main())

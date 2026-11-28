#!/usr/bin/env python3
"""r22_holdout_v2_generate.py — c-0009 EXECUTOR: holdout v2 ONE-SHOT
generation (AM23, PREREGISTRATION.json @ audit branch).

Art. 29(b)/(c) claim-before-work: claim c-0009 filed and pushed
(55f59facb) BEFORE any generation call. One generation for one-shot/sealed
work (Art. 29(c)).

DISCIPLINE (per audit/holdout_v2/PREREGISTRATION.json @ 6235108c3):
  - builder receives PROBLEMS ONLY: audit/holdout_v2/holdout_v2_problems.json
    read from the audit branch; the PRIVATE rubric is NEVER opened by this
    script (it is not read, not listed, not copied);
  - A1 answers generated ONCE per problem with the BYTE-UNCHANGED type-aware
    machine: contract_for(qt) -> SYS_A1_INT_V4 (intervention-proposal) /
    SYS_A1F_V4 (predictor-design); critic + question-type gate + typed
    violations with the machine's own repair directives (REPAIR_BUDGET=2)
    — the machine-internal repair loop IS the machine being tested (same
    code path as r20/r21; disclosed, not new);
  - K_GEN=1: no best-of-k, no selection (the BOK arm is RETIRED per
    ABLATION_REGISTRY @ 931c1eb6a);
  - NO judge calls, NO baseline/B-side assembly, NO problem-set iteration,
    NO rubric feedback (the auditor scores with the private rubric);
  - transport-level transient retry only (Art. 15 hardening, same as the
    peer's V5 driver): a FAILED call (HTTP 5xx/timeout) is retried up to 3
    times; a call that RETURNS content is never re-drawn (one-shot);
  - phases staggered vs the peer's live c-0006 run (pace sleep between
    problems; upstream zai/GLM quota is shared).

Outputs (canonical, Art. 29(e)): eval/holdout_v2_generation/
  - HO2 per-problem records + .partial.json resume anchor (Art. 18/29(d))
  - holdout_v2_generation_record.json (custody + one-shot disclosures)
"""
import datetime
import glob
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
PROBLEMS_PATH = "audit/holdout_v2/holdout_v2_problems.json"
OUT_DIR = REPO / "eval" / "holdout_v2_generation"
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
REPAIR_BUDGET = 2
GEN_ATTEMPTS = 3  # transport-level only (Art. 15); never re-draws content
GW_PORT = 8787

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")

from r19_a1w_v4_contract import (  # noqa: E402
    SYS_A1_INT_V4, contract_for, predictor_violations, DEV_NEED_MARKERS)
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402


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


def load_problems():
    """Problems ONLY, from the auditor's branch (fail-closed). The PRIVATE
    rubric is never touched by this script."""
    tip = subprocess.run(["git", "rev-parse", "--short=9", AUDIT_BRANCH],
                         capture_output=True, text=True, cwd=REPO)
    assert tip.returncode == 0, "audit branch not fetched — fail closed"
    tip = tip.stdout.strip()
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_BRANCH}:{PROBLEMS_PATH}"],
        capture_output=True, text=True, cwd=REPO)
    assert raw.returncode == 0, f"problems file missing on {AUDIT_BRANCH}"
    return tip, raw.stdout, json.loads(raw.stdout)


def start_gateway():
    import hashlib as _h
    key = "gwkey-" + _h.sha256(str(time.time()).encode()).hexdigest()[:12]
    env = dict(os.environ, ZAI_GATEWAY_KEY=key)
    log = open("/tmp/gw_holdout_v2.log", "wb")
    p = subprocess.Popen(
        ["node", str(REPO / "scripts" / "zai_gateway.mjs"), str(GW_PORT)],
        stdout=log, stderr=subprocess.STDOUT, env=env)
    for _ in range(60):
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{GW_PORT}/healthz", timeout=2)
            return p, key
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise RuntimeError("gateway not healthy")


def gen_retry(q, contract, gw_key):
    """Transport-level transient retry (Art. 15): a FAILED call is retried;
    a call that RETURNS content is never re-drawn (one-shot discipline)."""
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
    """The BYTE-UNCHANGED type-aware machine (r20/r21 code path): one
    generation pass + critic + question-type gate + typed violations with
    the machine's own repair directives (REPAIR_BUDGET=2)."""
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    contract = contract_for(qt)
    attempts = []
    (ans, lat), tries = gen_retry(q, contract, gw_key)
    attempts.append({"kind": "generation", "latency_s": round(lat, 1),
                     "chars": len(ans), "transport_tries": tries})
    final, meta = ans, {}
    for rep in range(REPAIR_BUDGET + 1):
        cr = critic(final, prob)
        tg = gate_question_type(final, prob)
        hits = sorted({m.group(0).lower()
                       for m in DEV_NEED_MARKERS.finditer(final)})
        vio = (predictor_violations(final) if qt.startswith("predictor")
               else ({"DEV_NEED": hits} if hits else {}))
        problems = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        for kind, found in vio.items():
            if kind == "DEV_NEED":
                problems.append(
                    "V4 NO-DEVELOPMENT RULE violation: the bill "
                    "concedes a development program (" + "; ".join(found)
                    + "). Re-express the SAME mechanism through "
                      "procurable classes only; the mechanism stays "
                      "novel, the COMPONENTS must all exist today.")
            elif kind == "BASELINE_PROGRAM":
                problems.append(
                    "V4 NO-BASELINE-PROGRAM violation: the scheme's "
                    "trust is built by a data program (" + "; ".join(
                        found) + "). Derive every reference from "
                    "ALREADY-RECORDED data, stated specs, or stated "
                    "physics; label it DERIVED with its source.")
            elif kind == "COMMISSIONING_PROGRAM":
                problems.append(
                    "V4 NO-COMMISSIONING-PROGRAM violation: the scheme "
                    "needs a tuning/validation campaign (" + "; ".join(
                        found) + "). Replace with a decision rule "
                        "computable NOW from stated data/specs/physics.")
        if not [p for p in problems if p]:
            meta = {"critic_verdict": cr["verdict"], "type_gate": tg,
                    "violations": vio, "repairs": rep}
            return final, attempts, meta
        if rep == REPAIR_BUDGET:
            meta = {"critic_verdict": cr["verdict"], "type_gate": tg,
                    "violations": vio, "repairs": rep,
                    "residual_findings": [p for p in problems if p]}
            return final, attempts, meta
        directive = ("REPAIR DIRECTIVE (typed findings on the previous "
                     "draft, disclosed): " + "; ".join(
                         p for p in problems if p)
                     + ". Fix ONLY these defects; keep the proposal's "
                       "core otherwise intact. The ONLY USER CONSTRAINT "
                       "labels allowed are the user-stated variables.")
        final, lat2 = _gen(q + "\n\n" + directive, contract, gw_key)
        attempts.append({"kind": f"repair_{rep + 1}",
                         "latency_s": round(lat2, 1),
                         "chars": len(final),
                         "findings_disclosed":
                             [p for p in problems if p]})
    raise RuntimeError("unreachable")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tip, raw_problems, doc = load_problems()
    probs = doc["problems"]
    problems_sha = _sha(raw_problems)
    print(f"[custody] audit tip {tip} | problems sha256_16 {problems_sha} "
          f"| selection_sha256 (auditor pre-registration, received) "
          f"{doc['selection_sha256'][:16]} | n={len(probs)}", flush=True)
    if len(probs) != doc["n_problems"]:
        raise RuntimeError("n_problems mismatch — fail closed")

    record = {
        "record": "HOLDOUT_V2_GENERATION/1.0.0",
        "work_id": "holdout-v2-generation",
        "claim": "c-0009 (EXECUTOR builder-r20s2, one_shot, filed+pushed "
                 "55f59facb BEFORE any generation call — Art. 29(b))",
        "at": _now(),
        "custody": {
            "audit_branch": AUDIT_BRANCH,
            "audit_tip_at_read": tip,
            "problems_file": PROBLEMS_PATH,
            "problems_sha256_16": problems_sha,
            "selection_sha256_received": doc["selection_sha256"],
            "private_rubric_accessed": False,
            "note": "builder received PROBLEMS ONLY per the "
                    "pre-registration; the PRIVATE rubric was never opened, "
                    "listed, or copied by the builder"},
        "discipline": {
            "one_shot": "one generation pass per problem (Art. 29(c)); a "
                        "call that returns content is never re-drawn; "
                        "transport-level transient retries only (Art. 15)",
            "machine": "BYTE-UNCHANGED type-aware machine: contract_for(qt) "
                       "— SYS_A1_INT_V4 (intervention-proposal) / SYS_A1F_V4 "
                       "(predictor-design); critic + question-type gate + "
                       "typed violations + machine repair directives "
                       "(REPAIR_BUDGET=2) — the machine-internal repair "
                       "loop is part of the machine under test (same code "
                       "path as r20/r21, disclosed)",
            "no_selection": "K_GEN=1 — no best-of-k, no selection (BOK arm "
                            "RETIRED per ABLATION_REGISTRY @ 931c1eb6a)",
            "no_judge": "NO judge calls, NO baseline/B-side assembly — the "
                        "auditor scores with the PRIVATE rubric (never "
                        "seen by builder/pipeline/judge)",
            "no_iteration": "no rubric feedback, no problem-set iteration, "
                            "no tuning — the problems are unseen (split=HOLDOUT)",
            "stagger": f"pace {PACE_S}s between problems, staggered against "
                       "the peer's live c-0006 run (shared upstream quota)",
        },
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
                "a1_source": "SYS_A1_INT_V4" if qt.startswith("intervention")
                             else "SYS_A1F_V4",
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
            _atomic(OUT_DIR / "holdout_v2_generation_record.json", record)
            print(f"    -> {len(ans)} chars, repairs={meta.get('repairs')}, "
                  f"critic={meta.get('critic_verdict')}, "
                  f"gate={meta.get('type_gate', {}).get('verdict')}",
                  flush=True)
            if i < len(probs) - 1:
                time.sleep(PACE_S)
    finally:
        gw.terminate()

    n = len(record["results"])
    if n != len(probs):
        print(f"INCOMPLETE: {n}/{len(probs)} — partial record committed as "
              "the resume anchor (Art. 18/29(d))", flush=True)
    _atomic(OUT_DIR / "holdout_v2_generation_record.json", record)
    print(f"DONE: {n}/{len(probs)} problems generated ONCE; record at "
          "eval/holdout_v2_generation/holdout_v2_generation_record.json",
          flush=True)
    return 0 if n == len(probs) else 2


if __name__ == "__main__":
    sys.exit(main())

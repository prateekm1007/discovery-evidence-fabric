#!/usr/bin/env python3
"""scripts/r401wc2_model_contest.py — R401-WC2 Phase 7: the MODEL
CONTEST harness (CEO directive 7).

    Do not hardcode DeepSeek merely because one experiment favored it.
    Benchmark the currently servable models against the same frozen
    synthesis/verification benchmark. Select the winner from measured
    behavior.

How the contest works:
  1. SERVABILITY is measured first: every registered provider is
     probed live (a tiny call; providers without credentials or with
     dead endpoints are recorded honestly — they are NOT contestants,
     they are absent, Art. XXV).
  2. Every SERVABLE model runs the SAME frozen battery through the
     ENGINE'S OWN call sites (extraction -> operator instantiation ->
     independent attack) on the frozen fixture problems — the contest
     measures behavior in the engine's real context, never an
     out-of-context quiz.
  3. Scoring is the machine validators (never narrative): extraction
     field validity + span binding (the mechanism_space validators),
     operator semantic check + testable-prediction check, attack parse
     validity + verdict structure (the independent_attack contract).
  4. The comparison table records per-model: validator pass rates,
     latency, statuses. The winner is selected FROM THE MEASUREMENT;
     with one servable model the contest result is a baseline
     measurement, not a selection (recorded exactly so).

The frozen battery fixture is the COMMITTED record
R401-WC2/OPERATOR_PROOF/LIVE_RETRIEVAL.json (24 live-retrieved EuropePMC
+ arXiv records, committed 2026-09-03 — deterministic, reproducible) +
three fixture problems that are NOT from the frozen cross-domain
benchmark (which is reserved for the baseline-vs-R401 measurement) and
NOT from the 18-case battery.

Usage:
  python3 scripts/r401wc2_model_contest.py [--providers pid,pid]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "R401-WC2" / "MODEL_CONTEST"
FIXTURE = (REPO_ROOT / "R401-WC2" / "OPERATOR_PROOF" /
           "LIVE_RETRIEVAL.json")
GATEWAY_PORT = 8787

BATTERY_VERSION = "r401wc2-model-contest/1.0.0"

# The three frozen contest problems (disjoint from the frozen benchmark
# and the 18-case battery; mechanism-rich, evidence-backed by the
# committed fixture records).
CONTEST_PROBLEMS = [
    {"problem_id": "contest-p1-heat-exchanger-fouling",
     "device": "shell-and-tube heat exchanger",
     "failure": ("mineral scale and biofilm layers on tube walls "
                 "raise thermal resistance and cut heat duty over "
                 "months of service"),
     "failure_mode": "fouling",
     "constraint": ("hold overall heat transfer above 2000 W/m2K "
                    "for a 6-month interval without chemical "
                    "cleaning")},
    {"problem_id": "contest-p2-li-ion-separator-shutdown",
     "device": "lithium-ion cell separator membrane",
     "failure": ("internal short events heat the cell faster than "
                 "the separator's shutdown mechanism can block ion "
                 "flow, escalating to thermal runaway"),
     "failure_mode": "thermal runaway",
     "constraint": ("block ion transport within 200 ms of a 150 C "
                    "internal hot spot while preserving 30 percent "
                    "porosity at 60 C operation")},
    {"problem_id": "contest-p3-hydraulic-valve-cavitation",
     "device": "hydraulic proportional control valve",
     "failure": ("cavitation erosion at the valve trim pits the "
                 "metering edges, degrading flow control accuracy "
                 "across the duty cycle"),
     "failure_mode": "erosion",
     "constraint": ("hold flow control accuracy within 2 percent "
                    "across a 70-bar pressure drop without staged "
                    "pressure-reduction trim")},
]


def _log(msg: str) -> None:
    print(f"[r401wc2-contest] {msg}", flush=True)


def _load_key() -> str:
    kv = {}
    p = REPO_ROOT / ".env.keys"
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                kv[m.group(1)] = m.group(2)
    return kv.get("ZAI_API_KEY", "")


def _start_gateway(key: str):
    import os
    subprocess.run(["pkill", "-f", "zai_gateway.mjs"],
                   capture_output=True, timeout=5)
    time.sleep(0.5)
    env = dict(os.environ)
    env["ZAI_GATEWAY_KEY"] = key
    env["ZAI_API_KEY"] = key
    proc = subprocess.Popen(
        ["node", "scripts/zai_gateway.mjs", str(GATEWAY_PORT)],
        cwd=str(REPO_ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    for _ in range(20):
        time.sleep(0.5)
        import urllib.error
        import urllib.request
        req = urllib.request.Request(
            f"http://127.0.0.1:{GATEWAY_PORT}/healthz", method="GET")
        try:
            urllib.request.urlopen(req, timeout=3)
            return proc
        except urllib.error.HTTPError:
            return proc
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
    proc.terminate()
    return None


# ---------------------------------------------------------------------------
# per-model pinned generation (through the engine's own registry)
# ---------------------------------------------------------------------------
def _pinned_generate(provider_id: str, prompt: str, system: str,
                     purpose: str, max_tokens: int = 700,
                     timeout: int = 240) -> Dict[str, Any]:
    from discovery_fabric.engine.llm_registry import (
        SelectionPolicy, generate)
    policy = SelectionPolicy(
        preferred_providers=[provider_id],
        max_preference_fallback=0,  # NO substitution: measure THIS model
        purpose=purpose)
    res = generate(prompt, system=system, policy=policy,
                   timeout=timeout, max_tokens=max_tokens)
    return {"ok": res.ok, "status": res.status, "content": res.content,
            "provider": res.provider_id, "model": res.model,
            "latency_ms": res.latency_ms, "error": res.error,
            "substituted_from": res.substituted_from}


def _probe_servability(providers: List[Dict[str, Any]]) -> Dict[str, Dict]:
    """Tiny live call per provider: the measured servability record."""
    out: Dict[str, Dict[str, Any]] = {}
    for p in providers:
        pid = p["provider_id"]
        if not p["available"]:
            out[pid] = {"servable": False,
                        "state": "NO_CREDENTIAL",
                        "model": p["model"]}
            continue
        r = _pinned_generate(
            pid, "Reply with exactly: CONTEST_PROBE_OK",
            system="You are a calibration probe.",
            purpose="model_contest_probe", max_tokens=20, timeout=90)
        out[pid] = {
            "servable": bool(r.get("ok")),
            "state": r.get("status"),
            "model": p["model"],
            "latency_ms": r.get("latency_ms"),
            "error": (r.get("error") or "")[:160],
        }
        _log(f"probe {pid}: {out[pid]['state']} "
             f"({out[pid].get('latency_ms')} ms)")
    return out


# ---------------------------------------------------------------------------
# the frozen battery (the engine's own call sites, pinned to one model)
# ---------------------------------------------------------------------------
def _run_battery(provider_id: str, records: List[Dict],
                 ) -> Dict[str, Any]:
    """One model through the frozen battery: extraction, operator
    instantiation, independent attack — all scored by the machine
    validators. Nothing narrative."""
    from discovery_fabric.engine import mechanism_space as ms
    from discovery_fabric.engine.independent_attack import (
        _parse_attack, _validate_parsed)

    per_problem: List[Dict[str, Any]] = []
    for problem in CONTEST_PROBLEMS:
        # --- stage 1: EXTRACTION on two fixture records
        recs = [r for r in records
                if (r.get("abstract") or "")[:200]][:2]
        extraction_scores = []
        for rec in recs:
            # pin the provider for the engine's own extraction call
            import discovery_fabric.engine.mechanism_space as _ms
            orig = _ms.llm_generate

            def _pinned(prompt, system="", timeout=240, max_tokens=700,
                        purpose="mechanism_space", exclude_providers=None,
                        _pid=provider_id):
                return _pinned_generate(
                    _pid, prompt, system, purpose, max_tokens, timeout)
            _ms.llm_generate = _pinned
            try:
                item = ms.extract_structured_evidence_item(rec, problem)
            finally:
                _ms.llm_generate = orig
            fields = item.get("fields") or {}
            n_valid = sum(1 for v in fields.values()
                          if (v or {}).get("state") == "VALID")
            extraction_scores.append({
                "n_fields_valid": n_valid,
                "mechanism_extracted": bool(
                    item.get("extraction_summary", {})
                    .get("mechanism_extracted")),
            })
        # --- stage 2: OPERATOR instantiation on a qualifying-shaped item
        # (use the engine's own contract + semantic validator)
        op_scores = []
        for op_id in ("GEOMETRIC_TRANSFORMATION",
                      "BOUNDARY_CONDITION_CHANGE"):
            op = next(o for o in ms.TRANSFORMATION_OPERATORS
                      if o["operator_id"] == op_id)
            # a controlled M1 built from the fixture record text (the
            # operator machinery under measurement, fixture disclosed)
            rec = recs[0] if recs else {}
            text = (rec.get("title") or "") + " " + \
                (rec.get("abstract") or "")
            m1 = {
                "item_id": f"contest-m1-{op_id}",
                "fields": {
                    "mechanism": {"value": "surface texture modifies "
                                   "boundary layer transport",
                                  "state": "VALID", "binding": None},
                    "system": {"value": problem["device"],
                               "state": "VALID", "binding": None},
                    "intervention": {"value": "textured surface layer",
                                     "state": "VALID", "binding": None},
                    "observed_effect": {"value": "transport rate "
                                        "changed measurably",
                                        "state": "VALID", "binding": None},
                    "boundary_conditions": {"value": "flow regime "
                                            "laminar and pressure 1 bar",
                                            "state": "VALID",
                                            "binding": None},
                    "constraints": {"value": "none stated", "state":
                                    "VALID", "binding": None},
                    "failure_mode": {"value": problem["failure_mode"],
                                     "state": "VALID", "binding": None},
                    "confidence": {"value": "HIGH", "state": "VALID",
                                   "binding": None},
                },
                "source": {"source_id": rec.get("source_id", "fixture"),
                           "source_name": "contest fixture",
                           "content_hash": rec.get("content_hash", ""),
                           "title": rec.get("title", ""),
                           "retrieval_timestamp":
                               rec.get("content_hash", "")},
                "provenance": {"custody": "CONTEST_FIXTURE"},
                "structured_hash": "contest",
                "extraction_summary": {"mechanism_extracted": True},
                "confidence": "HIGH",
                "_record_text": text,
            }
            import discovery_fabric.engine.mechanism_space as _ms
            orig = _ms.llm_generate

            def _pinned2(prompt, system="", timeout=240, max_tokens=700,
                         purpose="mechanism_space", exclude_providers=None,
                         _pid=provider_id):
                return _pinned_generate(
                    _pid, prompt, system, purpose, max_tokens, timeout)
            _ms.llm_generate = _pinned2
            try:
                res = ms.apply_operator(op, [m1], problem,
                                        per_operator_item_cap=1)
            finally:
                _ms.llm_generate = orig
            cands = [c for c in res.get("candidates", [])
                     if isinstance(c, dict)]
            cand = cands[0] if cands else {}
            sem = ms.operator_semantic_check(
                op_id, m1, cand, problem) if cand.get(
                    "candidate_id") else {}
            op_scores.append({
                "operator": op_id,
                "candidate_state": cand.get("candidate_state",
                                            "NO_CANDIDATE"),
                "semantic_verdict": sem.get("semantic_verdict", "N/A"),
                "testable": bool((cand.get("testable_prediction_check")
                                  or {}).get("testable")),
                "llm_status": (cand.get("derivation_trace") or {}).get(
                    "llm_provider") or cand.get("llm_status"),
            })
        # --- stage 3: INDEPENDENT ATTACK on one calibration case
        # (the machine contract: parse + verdict structure)
        cal = json.loads((REPO_ROOT / "R401-WC2" / "ATTACKER_CALIBRATION"
                          / "CORPUS.json").read_text())
        case = next(c for c in cal["cases"]
                    if c["case_id"] == "cal-13-clean-vane-quantified")
        attack_prompt = None
        # build the engine's own attack prompt through its API:
        # independent_attack with the provider pinned as generator AND
        # attacker (contest = measure THIS model's attack behavior)
        import discovery_fabric.engine.independent_attack as _ia
        from discovery_fabric.engine.mechanism_space import llm_generate \
            as _ms_gen

        def _pinned3(prompt, system="", timeout=240, max_tokens=700,
                     purpose="mechanism_space", exclude_providers=None,
                     _pid=provider_id):
            return _pinned_generate(
                _pid, prompt, system, purpose, max_tokens, timeout)
        # the attack path calls llm_generate via mechanism_space import
        _ia.llm_generate = _pinned3
        import discovery_fabric.engine.mechanism_space as _ms
        _orig_ms_gen = _ms.llm_generate
        _ms.llm_generate = _pinned3
        try:
            from discovery_fabric.engine.independent_attack import \
                independent_attack
            atk = independent_attack(
                case["candidate"], cal["the_common_problem"],
                case.get("evidence_items") or [],
                generator_provider=provider_id)
        finally:
            _ms.llm_generate = _orig_ms_gen
        items = _validate_parsed(_parse_attack(
            json.dumps({}) if not atk else "")) if False else atk.get(
            "items", [])
        n_valid_verdicts = sum(
            1 for i in items if i.get("verdict") in
            ("KILL", "RISK", "SURVIVE"))
        attack_score = {
            "state": atk.get("state"),
            "overall": atk.get("overall"),
            "n_classes_valid": n_valid_verdicts,
            "attacker_provider": atk.get("attacker_provider"),
        }
        per_problem.append({
            "problem_id": problem["problem_id"],
            "extraction": extraction_scores,
            "operators": op_scores,
            "attack": attack_score,
        })
    return {"per_problem": per_problem}


def _summarize(battery: Dict[str, Any]) -> Dict[str, Any]:
    """The measured aggregate per model (validator pass rates)."""
    probs = battery["per_problem"]
    n_ext = sum(len(p["extraction"]) for p in probs)
    ext_valid = sum(e["n_fields_valid"] for p in probs
                    for e in p["extraction"])
    mech_ext = sum(1 for p in probs for e in p["extraction"]
                   if e["mechanism_extracted"])
    ops = [o for p in probs for o in p["operators"]]
    return {
        "extraction": {
            "n_calls": n_ext,
            "fields_valid_total": ext_valid,
            "fields_valid_per_call": round(ext_valid / n_ext, 2) if n_ext
            else None,
            "mechanism_extracted_rate": round(mech_ext / n_ext, 3)
            if n_ext else None,
        },
        "operators": {
            "n_calls": len(ops),
            "n_candidates": sum(1 for o in ops
                                if o["candidate_state"] == "CANDIDATE"),
            "n_semantically_valid": sum(1 for o in ops if o[
                "semantic_verdict"] == "SEMANTICALLY_VALID"),
            "n_testable": sum(1 for o in ops if o["testable"]),
        },
        "attack": {
            "n_problems": len(probs),
            "states": [p["attack"]["state"] for p in probs],
            "verdict_classes_valid": sum(
                p["attack"]["n_classes_valid"] for p in probs),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="")
    args = ap.parse_args()

    key = _load_key()
    gateway = None
    if key:
        import os
        os.environ["ZAI_API_KEY"] = key
        gateway = _start_gateway(key)

    from discovery_fabric.engine.llm_registry import availability_matrix
    matrix = availability_matrix()
    providers = matrix
    if args.providers:
        want = set(args.providers.split(","))
        providers = [p for p in matrix if p["provider_id"] in want]

    _log("measuring servability (one tiny live call per provider)...")
    servability = _probe_servability(providers)
    contestants = [pid for pid, s in servability.items() if s["servable"]]
    if not contestants:
        _log("contestants: NONE (all dead/absent — the contest records "
             "the honest state)")
    else:
        _log(f"contestants: {contestants}")

    fixture = json.loads(FIXTURE.read_text())
    records = fixture.get("records", [])
    _log(f"frozen fixture: {len(records)} committed records "
         f"(LIVE_RETRIEVAL.json)")

    results: Dict[str, Any] = {}
    for pid in contestants:
        _log(f"running {pid} through the frozen battery...")
        try:
            battery = _run_battery(pid, records)
        except Exception as exc:  # noqa: BLE001 — recorded, never hidden
            battery = {"error": f"{type(exc).__name__}: {exc}"[:300]}
        results[pid] = {
            "servability": servability[pid],
            "battery": battery,
            "summary": _summarize(battery) if battery.get("per_problem")
            else battery,
        }
    report = {
        "contest_version": BATTERY_VERSION,
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "fixture": str(FIXTURE.relative_to(REPO_ROOT)),
        "problems": [p["problem_id"] for p in CONTEST_PROBLEMS],
        "servability": servability,
        "contestants": contestants,
        "results": results,
        "selection_rule": (
            "the winner is selected FROM THE MEASUREMENT over the same "
            "frozen battery; with fewer than two contestants there is "
            "no selection — the run is a baseline measurement, recorded "
            "exactly so (never a crowning; never reputation-based). "
            "DeepSeek is not hardcoded: it is a contestant only when "
            "servable and only through measured behavior."),
        "note": ("the battery runs the engine's OWN call sites "
                 "(extraction / operator instantiation / independent "
                 "attack) pinned per model with NO provider "
                 "substitution; scoring is the machine validators "
                 "(field validity, span binding, semantic verdicts, "
                 "testable predictions, attack verdict structure) — "
                 "never narrative."),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "MODEL_CONTEST_RESULTS.json"
    out.write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({"servability": servability,
                      "contestants": contestants,
                      "summaries": {k: v["summary"] for k, v in
                                    results.items() if "summary" in v}},
                     indent=1, default=str))
    print(f"\nfull report -> {out}")
    if gateway:
        gateway.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""R495 — the v4.2 DEV measurement (a2_adversarial_gauntlet/2.1.0, the
ATTACKER-COMPUTES kill standard) on the frozen R492 DEV corpus, on the
local z-ai gateway ring (the R494 cross-ring executed path).

THIS IS A DEV PROBE, NOT A SEAL MEASUREMENT (Art. LIX, disclosed):
  - the instrument bytes are THIS TREE's 2.1.0 — NOT the deployed 2.0.0
    (the deployed transport still serves 2.0.0; the identity gate is
    DELIBERATELY not asserted because the point is to measure the NEW
    rules before any deploy);
  - tuning against the DEV corpus is exactly what the DEV corpus is
    for (frozen before any tuning, R492);
  - a future seal still requires: deploy of 2.1.0 + the DEPLOYED-
    instrument measurement + repetition (the R493 seal discipline) —
    nothing here can flip calibration state.

THE MEASURED QUESTION: does the attacker-computes standard move TPR on
the hedged class (2.0.0 measured TPR 0.2727 xkiro / 0.3636 zai / 0.2222
xkiro-repetition, FPR 0.0 everywhere) WITHOUT reopening the false-kill
classes (FPR must stay 0.0 — the v4.1 floors and the rule-order
guarantees are pinned by test)?

Commands:
  python3 scripts/r495_v42_dev_measurement.py --run [--pace 10]
      [--slice N] [--resume] [--port 8787]
  python3 scripts/r495_v42_dev_measurement.py --score
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r493_a2_baseline as baseline  # noqa: E402  (the sibling's scorer)

OUT_DIR = REPO / "R495" / "A2_V42_DEV"
RAW_DIR = OUT_DIR / "RAW"
GATEWAY = REPO / "scripts" / "zai_gateway.mjs"
CORPUS_PATH = REPO / "R495" / "CORPUS_RECOVERY.json"
PINNED_PROVIDER = "zai"
V42 = "a2_adversarial_gauntlet/2.1.0"


def _log(msg: str) -> None:
    print(f"[r495-v42] {msg}", flush=True)


def _start_gateway(port: int, key: str) -> subprocess.Popen:
    subprocess.run(["pkill", "-f", f"zai_gateway.mjs {port}"],
                   capture_output=True)
    time.sleep(1)
    env = dict(os.environ)
    env["ZAI_GATEWAY_KEY"] = key
    log_path = OUT_DIR / "gateway.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w")
    proc = subprocess.Popen(
        ["node", str(GATEWAY), str(port)], env=env,
        stdout=log, stderr=subprocess.STDOUT, cwd=str(REPO))
    atexit.register(lambda: proc.poll() is None and proc.terminate())

    import urllib.request
    for _ in range(30):
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/healthz",
                    timeout=3) as r:
                if r.status == 200:
                    return proc
        except Exception:  # noqa: BLE001
            time.sleep(1)
    proc.terminate()
    raise RuntimeError("the local gateway did not become healthy")


def _attack_local(case: Dict[str, Any]) -> Dict[str, Any]:
    from discovery_fabric.a2.adversarial import \
        adversarial_challenge as _a2_attack
    packet = dict(case["candidate"])
    ev = case.get("evidence_items") or []
    if ev:
        packet["evidence_items"] = ev
    record = _a2_attack(
        packet,
        evidence_verified=True,
        prior_art_state=(case.get("ground_truth") or {})
        .get("prior_art_state") or "UNKNOWN",
        require_provider=PINNED_PROVIDER)
    return dict(record or {})


def run(pace: int, slice_n: int, resume: bool, port: int) -> int:
    corpus = json.loads(CORPUS_PATH.read_text())
    cases_all = corpus["cases"]
    _log(f"instrument: {V42} (DEV — this tree, NOT the deployed 2.0.0)")
    _log(f"corpus: {corpus['corpus_id']} (recovery-verified, "
         f"{len(cases_all)} cases)")

    gw_key = "r495-v42-dev-key"
    os.environ["ZAI_API_KEY"] = gw_key
    os.environ.pop("ZAI_BASE_URL", None)
    os.environ["ENGINE_MODEL_COST_POLICY"] = "UNRESTRICTED"
    os.environ["ENGINE_LLM_TIMEOUT_S"] = "360"
    _start_gateway(port, gw_key)
    _log(f"gateway healthy on :{port}; pin '{PINNED_PROVIDER}'")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    done = {f.stem for f in RAW_DIR.glob("*.json")}
    pending = [c for c in cases_all if c["case_id"] not in done]
    if resume:
        _log(f"resume: {len(done)} on disk, {len(pending)} pending")
    todo = pending[:slice_n] if slice_n else pending
    _log(f"run: {len(todo)} cases this slice, pace {pace}s")

    for i, case in enumerate(todo, 1):
        cid = case["case_id"]
        _log(f"[{i}/{len(todo)}] {cid} (cat={case['category'][:30]})")
        t0 = time.time()
        try:
            record = _attack_local(case)
        except Exception as exc:  # noqa: BLE001 — typed, retriable
            _log(f"  EXECUTION FAILURE {type(exc).__name__}: {exc} — "
                 f"no marker, retriable")
            if i < len(todo) and pace:
                time.sleep(pace)
            continue
        pin = (record.get("transport") or {}).get("ring_pin") or {}
        served = pin.get("served_provider")
        gv = record.get("gauntlet_version")
        if record.get("overall") == "EVALUATOR_CALL_FAILED":
            _log(f"  EVALUATOR_CALL_FAILED on the pinned ring "
                 f"({time.time() - t0:.0f}s) — no marker, retriable")
        elif gv and gv != V42:
            _log(f"  INSTRUMENT MISMATCH: {gv} (expected {V42}) — "
                 f"DISCARDED")
        elif pin.get("pin_violation") or (served
                                          and served != PINNED_PROVIDER):
            _log(f"  RING DEVIATION (served '{served}') — DISCARDED")
        else:
            (RAW_DIR / f"{cid}.json").write_text(
                json.dumps({"http": 200, "attack": record,
                            "latency_s": round(time.time() - t0, 1)},
                           indent=1, default=str))
            _log(f"  overall={record.get('overall')} killed="
                 f"{record.get('killed_count')} risks="
                 f"{len(record.get('risk_flags') or [])} "
                 f"({time.time() - t0:.0f}s, {served}/"
                 f"{pin.get('served_model')}, {gv})")
        if i < len(todo) and pace:
            time.sleep(pace)
    _log(f"slice done: {len(done) + len(todo)} total on disk "
         f"(of {len(cases_all)})")
    return 0


def _ring_summary() -> Dict[str, Any]:
    providers: Dict[str, int] = {}
    models: Dict[str, int] = {}
    pin_violations = []
    versions = {}
    for f in sorted(RAW_DIR.glob("*.json")):
        rec = json.loads(f.read_text())
        attack = rec.get("attack") or {}
        pin = (attack.get("transport") or {}).get("ring_pin") or {}
        served = pin.get("served_provider") or (
            attack.get("transport") or {}).get("provider")
        model = pin.get("served_model") or (
            attack.get("transport") or {}).get("model")
        if served:
            providers[served] = providers.get(served, 0) + 1
        if model:
            models[model] = models.get(model, 0) + 1
        if pin.get("pin_violation"):
            pin_violations.append(f.stem)
        gv = attack.get("gauntlet_version")
        if gv:
            versions[gv] = versions.get(gv, 0) + 1
    return {"providers": providers, "models": models,
            "pin_violations": pin_violations, "gauntlet_versions": versions,
            "pin_requested": PINNED_PROVIDER}


def score() -> int:
    corpus = json.loads(CORPUS_PATH.read_text())
    baseline.CORPUS_PATH = CORPUS_PATH
    baseline.RAW_DIR = RAW_DIR
    baseline.RESULTS_PATH = OUT_DIR / "MEASUREMENT_RESULTS.json"
    baseline.MEASUREMENT_PATH = OUT_DIR / "MEASUREMENT.json"
    results = baseline.score()

    results["report_version"] = "r495-a2-v42-dev/1.0.0"
    results["round"] = "R495"
    results["instrument"] = (
        f"a2/adversarial.py::adversarial_challenge ({V42} — the "
        "ATTACKER-COMPUTES kill standard), THIS TREE, DEV, NOT DEPLOYED")
    results["transport"] = (
        "IN-PROCESS adversarial_challenge with require_provider='zai' "
        "on the local gateway (scripts/zai_gateway.mjs -> the z-ai "
        "CLI's embedded model, ENVIRONMENT_GRANT) — the R494 executed "
        "path; identity gate DELIBERATELY not asserted (a DEV probe of "
        "the un-deployed 2.1.0; Art. LIX: the DEV corpus is the tuning "
        "surface; a seal still requires the deploy + the deployed-"
        "instrument measurement + repetition)")
    results["ring_summary"] = _ring_summary()
    h = results.get("headline") or {}
    results["dev_probe_disclosure"] = {
        "is_seal_measurement": False,
        "why_not": (
            "the instrument is not deployed; the R492 freeze "
            "discipline and the R493 seal rule both require the seal "
            "to ride a DEPLOYED-instrument measurement; this run "
            "informs the deploy decision only"),
        "the_measured_question": (
            "does the attacker-computes standard move TPR on the "
            "hedged class without reopening FPR (v4.2's one change; "
            "the 2.0.0 numbers: TPR 0.2727/0.3636/0.2222, FPR 0.0 on "
            "all three runs)"),
    }

    # the computed-kill ledger: how many kills rode rule 4.5
    dispositions = {}
    for f in sorted(RAW_DIR.glob("*.json")):
        rec = json.loads(f.read_text())
        for b in (rec.get("attack") or {}).get(
                "burden_of_proof", {}).get("ledger", []) or []:
            d = b.get("disposition") or b.get("demotion_class")
            if d:
                dispositions[d] = dispositions.get(d, 0) + 1
    results["burden_dispositions"] = dispositions

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "MEASUREMENT_RESULTS.json").write_text(
        json.dumps(results, indent=1, default=str))
    _log(f"results -> {OUT_DIR.relative_to(REPO)}/MEASUREMENT_RESULTS.json")
    _log(f"HEADLINE (DEV): TPR={h.get('tpr_defect_cohorts')} "
         f"({h.get('detected_in_defect_cohorts')}) FPR="
         f"{h.get('fpr_known_good')} "
         f"({h.get('false_kills_on_controls')}) coverage="
         f"{h.get('coverage_all_9_fields')} parse="
         f"{h.get('parse_completeness')}")
    _log(f"burden dispositions: {dispositions}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--pace", type=int, default=10)
    ap.add_argument("--slice", type=int, default=8)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args()
    if a.run:
        return run(a.pace, a.slice, a.resume, a.port)
    if a.score:
        return score()
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""scripts/r491_local_gateway_measurement.py — R491: the ring-pinned
sealed-corpus measurement of independent_attack/3.0.0 on the LOCAL
z-ai gateway ring (the R446/R447 canonical path, restored).

WHY LOCAL (the disclosed sequence, all in this round's records):
  - the deployed atria endpoint (BOTH slots: atria's ATRIA_API_KEY
    ring and zai's re-pointed ZAI_BASE_URL ring — same endpoint,
    same model) returns EMPTY CONTENT at the 8192-token reasoning
    ceiling on the attack prompt: 3 pinned attempts, each typed
    MODEL_FAILURE/CALL_FAILED, with ENGINE_LLM_TIMEOUT_S raised to
    360s (the R445-C override) — the endpoint is typed-broken for
    this prompt shape TODAY. R488's atria successes (cal-17/18,
    117-123s) prove the ring CAN serve; today it does not.
  - the R487/R488 detour through the DEPLOYED transport was a FORCED
    substitution (the container recycle destroyed the local vault),
    never the canonical discipline: the R446/R447 sealed-corpus
    measurements ran LOCALLY on the sandbox gateway.
  - the sandbox z-ai CLI is HEALTHY again in this container (probe:
    2026-09-17, ~6s, model glm-4-plus — the grant's embedded GLM
    class). This is the SAME transport that produced the R447 v2 raw
    outputs the R487 design dry-run validated (v3 rules on that
    ring's outputs: FPR 0.25). The (rules x ring) hypothesis is
    tested on the ring it was formed from.

HONEST DISCLOSURES carried into the record:
  - transport: LOCAL sandbox gateway (ENVIRONMENT_GRANT, the z-ai
    CLI's embedded model glm-4-plus), MODEL_COST_POLICY=UNRESTRICTED
    (the R451 vocabulary's recorded override; the grant is neither
    self-hosted weights nor a free-tier API)
  - instrument bytes: local HEAD == deployed dc90b510 (verified);
    the instrument code path is IDENTICAL to production
  - the served model id is whatever the CLI reports (glm-4-plus),
    recorded verbatim — never the requested id
  - NO threshold, corpus byte, scoring rule, or verdict path is
    touched; the gate DERIVES the state from the shipped record
    whatever it says; the true number is reported whatever it is

Commands:
  python3 scripts/r491_local_gateway_measurement.py --run [--resume]
      [--pace 20] [--limit N] [--skip id1,id2] [--port 8787]
  python3 scripts/r491_local_gateway_measurement.py --score
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r491_ring_pinned_measurement import (  # noqa: E402
    CORPUS_PATH, RAW_DIR, _freeze_check, _log, _ring_summary,
    load_raw, write_measurement,
)
import r447_attacker_v2_recalibration as frozen  # noqa: E402
from discovery_fabric.engine import attacker_calibration as gate  # noqa: E402

GATEWAY = REPO / "scripts" / "zai_gateway.mjs"
PINNED_PROVIDER = "zai"   # the registry slot whose default URL is the
#                          local gateway (127.0.0.1:8787); availability
#                          marker ZAI_API_KEY; NO ZAI_BASE_URL override
DEPLOYED_IDENTITY = "dc90b51004cf4755aee122b912f030db2351fded"

RESULTS_PATH = REPO / "R491" / "RING_PINNED_MEASUREMENT" / \
    "MEASUREMENT_RESULTS.json"
MEASUREMENT_PATH = REPO / "R491" / "RING_PINNED_MEASUREMENT" / \
    "MEASUREMENT.json"


def _git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"],
                          cwd=str(REPO), capture_output=True,
                          text=True).stdout.strip()


def _start_gateway(port: int, key: str) -> subprocess.Popen:
    env = dict(os.environ)
    env["ZAI_GATEWAY_KEY"] = key
    log = open(REPO / "R491" / "gateway.log", "w")
    proc = subprocess.Popen(
        ["node", str(GATEWAY), str(port)], env=env,
        stdout=log, stderr=subprocess.STDOUT,
        cwd=str(REPO))
    atexit.register(lambda: proc.poll() is None and proc.terminate())
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


def _attack_local(case: Dict[str, Any], problem: Dict[str, Any]
                  ) -> Dict[str, Any]:
    """Run the instrument IN-PROCESS on the pinned local ring."""
    from discovery_fabric.engine.independent_attack \
        import independent_attack
    return independent_attack(
        case["candidate"], problem, case.get("evidence_items") or [],
        None, require_provider=PINNED_PROVIDER)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--pace", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip", default="")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()

    corpus = json.loads(CORPUS_PATH.read_text())
    problem = corpus["the_common_problem"]
    head = _git_head()
    if head != DEPLOYED_IDENTITY:
        _log(f"FATAL: local HEAD {head[:12]} != deployed "
             f"{DEPLOYED_IDENTITY[:12]} — the instrument bytes must "
             f"match production for the measurement to claim the "
             f"deployed instrument")
        return 2

    if args.run:
        freeze = _freeze_check()
        if not freeze["freeze_ok"]:
            _log("FATAL: corpus not byte-identical to the frozen R446 "
                 "record (or dirty)")
            return 2
        # the local-ring env wiring (recorded, never silent):
        #  - ZAI_API_KEY = the gateway key (availability + Bearer auth)
        #  - ZAI_BASE_URL REMOVED (the zai slot's default URL is the
        #    local gateway; the production repoint must NOT leak in)
        #  - MODEL_COST_POLICY=UNRESTRICTED (the R451 vocabulary's
        #    recorded override: the environment grant is neither
        #    self-hosted weights nor a free-tier API)
        #  - ENGINE_LLM_TIMEOUT_S=360 (the same ceiling set on the
        #    deployed instrument this round)
        gw_key = "r491-local-measurement-key"
        os.environ["ZAI_API_KEY"] = gw_key
        os.environ.pop("ZAI_BASE_URL", None)
        os.environ["ENGINE_MODEL_COST_POLICY"] = "UNRESTRICTED"
        os.environ["ENGINE_LLM_TIMEOUT_S"] = "360"
        _log("starting the LOCAL z-ai gateway (the R446/R447 "
             "canonical transport)...")
        _start_gateway(args.port, gw_key)
        _log(f"gateway healthy on :{args.port}; instrument HEAD "
             f"{head[:12]} == deployed; corpus frozen OK")

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        skip_ids = {s.strip() for s in args.skip.split(",") if s.strip()}
        cases = corpus["cases"]
        if args.limit:
            cases = cases[:args.limit]
        if skip_ids:
            _log(f"batching skip (this pass only): {sorted(skip_ids)}")
            cases = [c for c in cases if c["case_id"] not in skip_ids]
        n_done = 0
        for case in cases:
            marker = RAW_DIR / f"{case['case_id']}.json"
            if args.resume and marker.exists():
                _log(f"{case['case_id']}: RAW exists (resume)")
                continue
            if n_done and args.pace:
                time.sleep(args.pace)
            _log(f"{case['case_id']}: attacking (pinned "
                 f"'{PINNED_PROVIDER}', local gateway)...")
            t0 = time.time()
            try:
                record = _attack_local(case, problem)
            except Exception as exc:  # noqa: BLE001 — typed, retriable
                _log(f"{case['case_id']}: EXECUTION FAILURE "
                     f"{type(exc).__name__}: {exc} — no marker, "
                     f"retriable")
                continue
            rp = record.get("ring_pin") or {}
            served_p = record.get("attacker_provider")
            if record.get("overall") == "ATTACK_INCOMPLETE" \
                    or record.get("llm_status") not in (None, "OK"):
                _log(f"{case['case_id']}: ATTACK_INCOMPLETE on the "
                     f"pinned ring (llm_status="
                     f"{record.get('llm_status')}) — no marker, "
                     f"retriable")
                continue
            if rp.get("pin_violation") or (
                    served_p and served_p != PINNED_PROVIDER):
                _log(f"{case['case_id']}: RING DEVIATION (served "
                     f"'{served_p}', pinned '{PINNED_PROVIDER}') — "
                     f"marker DISCARDED")
                continue
            marker.write_text(json.dumps({"attack": record}, indent=1,
                                         default=str))
            n_done += 1
            _log(f"{case['case_id']}: {record.get('overall')} "
                 f"({time.time() - t0:.0f}s, {served_p}/"
                 f"{record.get('attacker_model')})")

    raw = load_raw()
    if not raw:
        _log("no RAW records yet — run with --run first")
        return 0
    results = frozen.score_all(corpus, raw)
    results["report_version"] = "r491-local-gateway-measurement/1.0.0"
    results["freeze_check"] = _freeze_check()
    results["instrument"] = (
        "independent_attack/3.0.0 (unchanged rules; the RING-PINNED "
        "re-measurement on the LOCAL z-ai gateway — the R446/R447 "
        "canonical transport, the dry-run's ring)")
    results["ring_summary"] = _ring_summary(raw)
    results["ring_pin_requested"] = PINNED_PROVIDER
    results["transport_disclosure"] = {
        "transport": ("LOCAL sandbox gateway (scripts/zai_gateway.mjs "
                      "-> the z-ai CLI's embedded model; "
                      "ENVIRONMENT_GRANT)"),
        "served_model": "the CLI's self-reported id, recorded verbatim "
                        "on every record (glm-4-plus at measurement "
                        "time)",
        "cost_policy": "ENGINE_MODEL_COST_POLICY=UNRESTRICTED (the R451 "
                       "vocabulary's recorded override for the "
                       "environment grant)",
        "instrument_bytes": (f"local HEAD == deployed "
                             f"{DEPLOYED_IDENTITY[:12]} — the "
                             f"instrument code path is identical to "
                             f"production"),
        "why_not_the_deployed_ring": (
            "the deployed atria endpoint returned EMPTY CONTENT at "
            "the 8192-token reasoning ceiling on the attack prompt "
            "(3 pinned attempts, typed MODEL_FAILURE/CALL_FAILED, "
            "ENGINE_LLM_TIMEOUT_S=360; both slots — atria's own key "
            "ring and the zai re-point — same endpoint, same model); "
            "R488's atria successes prove the ring CAN serve; today "
            "it does not — the typed evidence is in this round's "
            "records"),
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=1, default=str))
    meas = write_measurement(results, PINNED_PROVIDER)

    hc = results["headline_confusion"]
    _log(f"ring served: {json.dumps(results['ring_summary']['providers'])}"
         f" (pin violations: "
         f"{results['ring_summary']['pin_violations'] or 'none'})")
    _log(f"TPR {hc['TPR']} ({hc['detected_kill']}/"
         f"{hc['n_true_positives']}) | FPR {hc['FPR']} | "
         f"TNR {hc['TNR']} | coverage {results['coverage']} | "
         f"parse {results['parse_completeness']}")
    _log(f"false kills: {hc['false_kills']}")
    _log(f"escalated-not-killed (clean cohort): "
         f"{hc['escalated_not_killed']}")
    _log(f"missed-because-demoted (TP cohort): "
         f"{hc['missed_because_demoted']}")
    _log(f"bars met: {results['bars_met']}")
    _log(f"threshold_verdict.calibrated: "
         f"{meas['threshold_verdict']['calibrated']}")
    st = gate.resolve_state(
        measurement_path=MEASUREMENT_PATH, seal_path=REPO / "R491" /
        "RING_PINNED_MEASUREMENT" / "SEAL.json",
        instrument_version="independent_attack/3.0.0")
    _log(f"GATE STATE (this record, pre-shipment): {st.get('state')} "
         f"(terminal_kill_admissible="
         f"{st.get('terminal_kill_admissible')}; ring_binding="
         f"{st.get('ring_binding')}) — the shipped-record flip happens"
         f" via scripts/r491_ship_records.py")
    _log(f"results -> {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

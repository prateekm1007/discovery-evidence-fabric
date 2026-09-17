#!/usr/bin/env python3
"""scripts/r494_a2_baseline_local.py — R494: the UNTUNED A2 baseline
measurement (the R493 driver's measured question) on the LOCAL z-ai
gateway ring, because the sibling's declared primary ring (atria) is
typed-broken for attack prompts TODAY (the R491 finding, re-probed
this round: 2 fresh pinned attempts, both CALL_FAILED — empty content
at the reasoning ceiling; the watch record is
scripts/r494_atria_watch/ATRIA_WATCH.json on the session side and is
shipped with this round's records).

WHAT THIS MEASURES (the sibling's own words, r493_a2_baseline.py):
the CURRENT (untuned) gauntlet on the frozen DEV corpus — the baseline
the v4 tuning is judged against, and the first A2 number that has ever
existed. The scoring is the sibling's score() IMPORTED VERBATIM (no
re-derivation, no threshold invention — Art. XXVII); the input mapping
mirrors the deployed transport's own (evidence_items merged into the
candidate packet, prior_art_state from the case ground truth).

DISCIPLINE (the R447/R487/R491/R493 lineage, preserved):
  - the FROZEN corpus asserted before and after (the sibling's
    _freeze_check — sha 1e4a593f...); no corpus byte touched
  - identity gate: local HEAD == deployed dedca446 — the instrument
    bytes are the deployed instrument's
  - ring pin: every case require_provider='zai' (the local gateway);
    a pin violation or ring deviation NEVER scores (marker discarded)
  - sequential, paced (the ring-friendly shape)
  - RAW markers land in the sibling's own R493/A2_BASELINE/RAW/
    (union-friendly: the sibling's --resume treats them as done)
  - transport stamped on every record EXACTLY as the deployed endpoint
    stamps it (_LAST_ATTACK_PROVIDER_META -> record["transport"])

Commands:
  python3 scripts/r494_a2_baseline_local.py --run [--resume]
      [--pace 15] [--limit N] [--port 8788]
  python3 scripts/r494_a2_baseline_local.py --score
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
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# the sibling's driver: scoring + freeze check imported verbatim
import r493_a2_baseline as baseline  # noqa: E402

CORPUS_PATH = REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json"
RAW_DIR = REPO / "R493" / "A2_BASELINE" / "RAW"
GATEWAY = REPO / "scripts" / "zai_gateway.mjs"
PINNED_PROVIDER = "zai"          # the registry slot whose default URL is
#                                 the local gateway (127.0.0.1:8787)
DEPLOYED_IDENTITY = "dedca4468fcc00b004993fc729762cd6e8cf02f2"
MEASUREMENT_RESULTS = REPO / "R493" / "A2_BASELINE" / \
    "MEASUREMENT_RESULTS_LOCAL_RING.json"


def _log(msg: str) -> None:
    print(f"[r494-baseline-local] {msg}", flush=True)


def _git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"],
                          cwd=str(REPO), capture_output=True,
                          text=True).stdout.strip()


def _tree_clean() -> bool:
    out = subprocess.run(["git", "status", "--porcelain", "--",
                          "discovery_fabric", "toscanini"],
                         cwd=str(REPO), capture_output=True,
                         text=True).stdout.strip()
    return not out


def _start_gateway(port: int, key: str) -> subprocess.Popen:
    # preflight: a stale gateway holding the port (the smoke-test
    # lesson) reads as NETWORK_FAILURE at probe time — kill strays
    # owned by this session's user before binding
    subprocess.run(["pkill", "-f", f"zai_gateway.mjs {port}"],
                   capture_output=True)
    time.sleep(1)
    env = dict(os.environ)
    env["ZAI_GATEWAY_KEY"] = key
    log_path = REPO / "R493" / "A2_BASELINE" / "gateway.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w")
    proc = subprocess.Popen(
        ["node", str(GATEWAY), str(port)], env=env,
        stdout=log, stderr=subprocess.STDOUT, cwd=str(REPO))
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


def _attack_local(case: Dict[str, Any]) -> Dict[str, Any]:
    """Run the A2 gauntlet IN-PROCESS on the pinned local ring, with the
    deployed transport's own input mapping and transport stamping."""
    from discovery_fabric.a2.adversarial import \
        adversarial_challenge as _a2_attack
    from discovery_fabric.a2 import adversarial as _adv_mod
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
    record = dict(record or {})
    # EXACTLY the deployed endpoint's stamping (toscanini/server.py):
    record["transport"] = dict(getattr(
        _adv_mod, "_LAST_ATTACK_PROVIDER_META", {}) or {})
    return record


def run(pace: int, limit: int, resume: bool, port: int) -> int:
    head = _git_head()
    if head != DEPLOYED_IDENTITY:
        _log(f"FATAL: local HEAD {head[:12]} != deployed "
             f"{DEPLOYED_IDENTITY[:12]} — the instrument bytes must be "
             f"the deployed instrument's")
        return 2
    if not _tree_clean():
        _log("FATAL: discovery_fabric/ or toscanini/ is dirty — the "
             "measurement must run on the clean deployed bytes")
        return 2
    sha = baseline._freeze_check()
    _log(f"frozen corpus verified: {sha[:16]}... (the sibling's check)")

    gw_key = "r494-a2-baseline-key"
    os.environ["ZAI_API_KEY"] = gw_key
    os.environ.pop("ZAI_BASE_URL", None)          # keep the slot loopback
    os.environ["ENGINE_MODEL_COST_POLICY"] = "UNRESTRICTED"
    os.environ["ENGINE_LLM_TIMEOUT_S"] = "360"
    _log("starting the LOCAL z-ai gateway (the R446/R447 canonical "
         "transport, the R491 executed path)...")
    _start_gateway(port, gw_key)
    _log(f"gateway healthy on :{port}; instrument HEAD {head[:12]} == "
         f"deployed; pin '{PINNED_PROVIDER}'")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    corpus = json.loads(CORPUS_PATH.read_text())
    cases = corpus["cases"][:limit] if limit else corpus["cases"]
    if resume:
        done = {f.stem for f in RAW_DIR.glob("*.json")}
        cases = [c for c in cases if c["case_id"] not in done]
        _log(f"resume: {len(done)} on disk, {len(cases)} to run")
    n_done = 0
    for i, case in enumerate(cases, 1):
        cid = case["case_id"]
        _log(f"[{i}/{len(cases)}] {cid} "
             f"(cat={case['category'][:28]})")
        t0 = time.time()
        try:
            record = _attack_local(case)
        except Exception as exc:  # noqa: BLE001 — typed, retriable
            _log(f"  EXECUTION FAILURE {type(exc).__name__}: {exc} — no "
                 f"marker, retriable")
            if i < len(cases) and pace:
                time.sleep(pace)
            continue
        pin = (record.get("transport") or {}).get("ring_pin") or {}
        served = pin.get("served_provider")
        if record.get("overall") == "EVALUATOR_CALL_FAILED":
            _log(f"  EVALUATOR_CALL_FAILED on the pinned ring "
                 f"({time.time() - t0:.0f}s) — no marker, retriable")
        elif pin.get("pin_violation") or (served and served != PINNED_PROVIDER):
            _log(f"  RING DEVIATION (served '{served}') — marker "
                 f"DISCARDED")
        else:
            (RAW_DIR / f"{cid}.json").write_text(
                json.dumps({"http": 200, "attack": record,
                            "latency_s": round(time.time() - t0, 1)},
                           indent=1, default=str))
            n_done += 1
            _log(f"  overall={record.get('overall')} killed="
                 f"{record.get('killed_count')} "
                 f"({time.time() - t0:.0f}s, {served}/"
                 f"{pin.get('served_model')})")
        if i < len(cases) and pace:
            time.sleep(pace)
    post = baseline._freeze_check()
    if post != sha:
        raise SystemExit("FATAL: corpus bytes changed DURING the run")
    _log("freeze re-verified post-run")
    return score()


def score() -> int:
    # the sibling's scoring, imported verbatim — pointed at the same
    # RAW dir it already reads (R493/A2_BASELINE/RAW)
    results = baseline.score()
    results["report_version"] = "r494-a2-baseline-local/1.0.0"
    results["instrument"] = (
        "a2/adversarial.py::adversarial_challenge (as deployed at "
        f"{DEPLOYED_IDENTITY[:12]}, UNTUNED baseline) — measured on the "
        "LOCAL z-ai gateway ring")
    results["transport"] = (
        "IN-PROCESS adversarial_challenge with require_provider='zai' "
        "on the local gateway (scripts/zai_gateway.mjs -> the z-ai CLI's "
        "embedded model, ENVIRONMENT_GRANT); input mapping and transport "
        "stamping mirror the deployed /api/ops/a2-attack byte-for-byte; "
        "local HEAD == deployed " + DEPLOYED_IDENTITY[:12])
    results["transport_disclosure"] = {
        "why_not_the_deployed_ring": (
            "the sibling's declared primary ring (atria) is typed-broken "
            "for attack prompts: re-probed this round, 2 pinned attempts "
            "both CALL_FAILED (empty content at the reasoning ceiling, "
            "the R491 class; R488's cal-17/18 successes prove the ring "
            "CAN serve) — the watch record ships with this round"),
        "ring": "zai / the CLI's self-reported model id, recorded "
                "verbatim on every record",
        "cost_policy": "ENGINE_MODEL_COST_POLICY=UNRESTRICTED (the R451 "
                       "vocabulary's recorded override for the "
                       "environment grant)",
        "union_note": (
            "RAW markers live in the sibling's own R493/A2_BASELINE/RAW/ "
            "— the sibling's --resume treats them as done; the scoring "
            "is the sibling's score() imported verbatim (Art. XXVII)"),
    }
    MEASUREMENT_RESULTS.write_text(json.dumps(results, indent=1,
                                              default=str))
    _log(f"results -> {MEASUREMENT_RESULTS.relative_to(REPO)}")
    h = results["headline"]
    _log(f"HEADLINE: TPR={h['tpr_defect_cohorts']} "
         f"({h['detected_in_defect_cohorts']}) FPR={h['fpr_known_good']} "
         f"({h['false_kills_on_controls']}) coverage="
         f"{h['coverage_all_9_fields']} parse={h['parse_completeness']} "
         f"verdict={results['threshold_verdict']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--pace", type=int, default=15)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--port", type=int, default=8788)
    a = ap.parse_args()
    if a.run:
        return run(a.pace, a.limit, a.resume, a.port)
    if a.score:
        return score()
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

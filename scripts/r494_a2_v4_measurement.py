#!/usr/bin/env python3
"""scripts/r494_a2_v4_measurement.py — R494: the v4 BURDEN-OF-PROOF
gauntlet (a2_adversarial_gauntlet/2.0.0) measured on the FROZEN R492
DEV corpus, the same ring as the untuned baseline (the local z-ai
gateway — the R491 executed path; atria remains typed-broken for
attack prompts, re-probed this round).

THE MEASURED QUESTION: does the v4 rules (lacks-derivation -> RISK
never KILL + the mandatory-basis prompt + the machine-side
enforce_burden_of_proof) meet the corpus's PRE-REGISTERED thresholds
(the R412 sealed bars reused verbatim, Art. XXVII) on the SAME frozen
corpus the untuned baseline measured TPR 0.0909 / FPR 1.0 on?

DISCIPLINE (the R447/R487/R491/R493 lineage, preserved):
  - the FROZEN corpus asserted before and after (the sibling's
    _freeze_check — sha 1e4a593f...); no corpus byte touched
  - identity gate: local HEAD == the DEPLOYED commit that ships the
    v4 instrument (the deployed-build check runs before --run; the
    exact sha is pinned below at authoring time and verified against
    /api/version at run time)
  - ring pin: every case require_provider='zai' (the same ring as the
    baseline — the rules delta is measured on ONE ring, never
    confounded); pin violations NEVER score
  - the sibling's score() imported VERBATIM, pointed at THIS round's
    RAW dir (never mixed with the baseline's RAW — different rules
    versions never share a scoring pool)
  - the record ships in the ENGINE registry schema (metrics.* +
    scoped_tpr_diagnostic.tpr + threshold_verdict + attacker_ring) so
    the seal plugs into the canonical registry WITHOUT translation

Commands:
  python3 scripts/r494_a2_v4_measurement.py --run [--resume]
      [--pace 12] [--limit N] [--port 8787] [--deployed <sha>]
  python3 scripts/r494_a2_v4_measurement.py --score
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

import r493_a2_baseline as baseline  # noqa: E402

CORPUS_PATH = REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json"
OUT_DIR = REPO / "R494" / "A2_V4_CALIBRATION"
RAW_DIR = OUT_DIR / "RAW"
GATEWAY = REPO / "scripts" / "zai_gateway.mjs"
PINNED_PROVIDER = "zai"
BASE_URL = "https://prateekm1-toscanini-prod-validation.hf.space"

# pinned at authoring; overridden by --deployed; verified against the
# LIVE /api/version before any case runs (the identity gate)
DEPLOYED_IDENTITY = ""
MEASUREMENT_RESULTS = OUT_DIR / "MEASUREMENT_RESULTS.json"
MEASUREMENT = OUT_DIR / "MEASUREMENT.json"
SEAL = OUT_DIR / "SEAL.json"


def _log(msg: str) -> None:
    print(f"[r494-v4] {msg}", flush=True)


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


def _deployed_commit() -> str:
    with urllib.request.urlopen(f"{BASE_URL}/api/version",
                                timeout=30) as r:
        v = json.loads(r.read().decode())
    return str(v.get("engine_commit") or "")


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


def _ring_summary(raw_dir: Path) -> Dict[str, Any]:
    providers: Dict[str, int] = {}
    models: Dict[str, int] = {}
    pin_violations = []
    for f in sorted(raw_dir.glob("*.json")):
        rec = json.loads(f.read_text())
        tr = (rec.get("attack") or {}).get("transport") or {}
        pin = tr.get("ring_pin") or {}
        served = pin.get("served_provider") or tr.get("provider")
        model = pin.get("served_model") or tr.get("model")
        if served:
            providers[served] = providers.get(served, 0) + 1
        if model:
            models[model] = models.get(model, 0) + 1
        if pin.get("pin_violation"):
            pin_violations.append(f.stem)
    return {"providers": providers, "models": models,
            "pin_violations": pin_violations,
            "pin_requested": PINNED_PROVIDER}


def run(pace: int, limit: int, resume: bool, port: int,
        deployed: str) -> int:
    head = _git_head()
    deployed = deployed or DEPLOYED_IDENTITY
    live = _deployed_commit()
    _log(f"local HEAD {head[:12]} | pinned deployed "
         f"{deployed[:12] if deployed else '<unset>'} | live "
         f"/api/version {live[:12]}")
    if deployed and head != deployed:
        _log("FATAL: local HEAD != the pinned deployed commit — the "
             "instrument bytes must be the deployed instrument's")
        return 2
    if live != head:
        _log("FATAL: the LIVE deployed build is not local HEAD — "
             "deploy first (the measurement must run on the deployed "
             "instrument's bytes)")
        return 2
    if not _tree_clean():
        _log("FATAL: discovery_fabric/ or toscanini/ is dirty — the "
             "measurement must run on the clean deployed bytes")
        return 2
    sha = baseline._freeze_check()
    _log(f"frozen corpus verified: {sha[:16]}... (the sibling's check)")

    gw_key = "r494-a2-v4-key"
    os.environ["ZAI_API_KEY"] = gw_key
    os.environ.pop("ZAI_BASE_URL", None)
    os.environ["ENGINE_MODEL_COST_POLICY"] = "UNRESTRICTED"
    os.environ["ENGINE_LLM_TIMEOUT_S"] = "360"
    _log("starting the LOCAL z-ai gateway (the baseline's ring — the "
         "rules delta on ONE ring)...")
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
    for i, case in enumerate(cases, 1):
        cid = case["case_id"]
        _log(f"[{i}/{len(cases)}] {cid} "
             f"(cat={case['category'][:28]})")
        t0 = time.time()
        try:
            record = _attack_local(case)
        except Exception as exc:  # noqa: BLE001 — typed, retriable
            _log(f"  EXECUTION FAILURE {type(exc).__name__}: {exc} — "
                 f"no marker, retriable")
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
            _log(f"  overall={record.get('overall')} killed="
                 f"{record.get('killed_count')} risks="
                 f"{len(record.get('risk_flags') or [])} "
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
    # the sibling's scoring imported VERBATIM, pointed at THIS round's
    # RAW dir (module-global override; never mixed with the baseline's)
    baseline.RAW_DIR = RAW_DIR
    results = baseline.score()
    # score() writes the sibling's own paths — capture and move
    results["report_version"] = "r494-a2-v4-measurement/1.0.0"
    results["instrument"] = (
        "a2/adversarial.py::adversarial_challenge "
        "(a2_adversarial_gauntlet/2.0.0 — the v4 BURDEN-OF-PROOF "
        f"rules), as deployed at {_git_head()[:12]}")
    results["attacker_ring"] = _ring_summary(RAW_DIR)
    results["transport"] = (
        "IN-PROCESS adversarial_challenge with require_provider='zai' "
        "on the local gateway (scripts/zai_gateway.mjs -> the z-ai "
        "CLI's embedded model, ENVIRONMENT_GRANT) — the SAME ring as "
        "the untuned baseline (the rules delta on one ring); input "
        "mapping mirrors the deployed /api/ops/a2-attack "
        "byte-for-byte; local HEAD == deployed == live /api/version")
    results["transport_disclosure"] = {
        "why_not_the_deployed_ring": (
            "the sibling's declared primary ring (atria) remains "
            "typed-broken for attack prompts (re-probed this round, 2 "
            "pinned attempts both CALL_FAILED — the R491 empty-content "
            "class); the local gateway is the R491 executed path and "
            "the SAME ring the baseline measured on"),
        "ring": "zai / the CLI's self-reported model id, recorded "
                "verbatim on every record",
        "cost_policy": "ENGINE_MODEL_COST_POLICY=UNRESTRICTED (the "
                       "R451 vocabulary's recorded override for the "
                       "environment grant)",
        "rules_delta": (
            "v4 vs the untuned 1.0.0 baseline: the three-verdict "
            "vocabulary (PASS | RISK | KILLED) with mandatory inline "
            "basis, the machine-side enforce_burden_of_proof "
            "(lacks-derivation -> RISK never KILL; absence never "
            "contradiction; attacker-imported scope and unbound "
            "assertions demote; the evidence-bare honest kill and the "
            "prior-art state binding keep authority)"),
    }
    # the ENGINE registry schema (resolve_state reads these keys) so
    # the seal plugs in WITHOUT translation
    h = results.get("headline") or {}
    verdict = results.get("threshold_verdict") or {}
    measurement = {
        "artifact_type": "A2_GAUNTLET_V4_MEASUREMENT",
        "instrument": "a2_adversarial_gauntlet/2.0.0",
        "measured_at": results.get("measured_at"),
        "reviewer_provenance": "AI_REVIEW",
        "corpus": {
            "path": "R492/A2_DEV_CORPUS/CORPUS.json",
            "corpus_id": results.get("corpus_id"),
            "sha256": results.get("corpus_sha256"),
            "frozen_unchanged": True,
            "n_cases": results.get("n_cases"),
        },
        "attacker_ring": {
            "provider": "zai",
            "model": (results.get("attacker_ring") or {})
            .get("models") and next(iter(
                (results.get("attacker_ring") or {})
                .get("models"))) or None,
            "ring_pin": "zai",
            "serving": (results.get("attacker_ring") or {})
            .get("providers"),
            "pin_violations": (results.get("attacker_ring") or {})
            .get("pin_violations") or [],
            "note": "the calibration is (rules x ring) — the gate "
                    "binds terminal kill authority to THIS ring at "
                    "consumption (R488/R491)",
        },
        "metrics": {
            "false_kill_rate_on_known_good":
                h.get("fpr_known_good"),
            "coverage": h.get("coverage_all_9_fields"),
            "parse_completeness": h.get("parse_completeness"),
            "tnr": h.get("tnr"),
        },
        "scoped_tpr_diagnostic": {
            "tpr": h.get("tpr_defect_cohorts"),
            "cohort": "defect cohorts (TRUE_POSITIVE_seeded_defect + "
                      "EVIDENCE_CONTRADICTED), marker-bound kills per "
                      "the corpus's scoring contract",
        },
        "n_cases_attacked": results.get("n_measured"),
        "threshold_verdict": verdict,
        "measured_verdict_note": (
            "the v4 burden-of-proof record on the frozen R492 DEV "
            "corpus; the untuned 1.0.0 baseline measured TPR 0.0909 / "
            "FPR 1.0 on the same corpus, same ring (the before-number "
            "in R493/A2_BASELINE)"),
        "baseline_comparison": {
            "untuned_1_0_0": {
                "tpr": 0.0909, "fpr": 1.0, "coverage": 1.0,
                "parse": 1.0,
                "record": "R493/A2_BASELINE/MEASUREMENT_RESULTS_LOCAL_RING.json",
            },
            "v4_2_0_0": {
                "tpr": h.get("tpr_defect_cohorts"),
                "fpr": h.get("fpr_known_good"),
                "coverage": h.get("coverage_all_9_fields"),
                "parse": h.get("parse_completeness"),
            },
        },
        "category_disciplines": results.get("category_disciplines"),
        "per_case": results.get("per_case"),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MEASUREMENT_RESULTS.write_text(json.dumps(results, indent=1,
                                              default=str))
    MEASUREMENT.write_text(json.dumps(measurement, indent=1,
                                      default=str))
    # the seal: the corpus's OWN pre-registered thresholds, copied
    # verbatim (Art. XXVII — no threshold invented at seal time)
    corpus = json.loads(CORPUS_PATH.read_text())
    seal = {
        "artifact_type": "A2_GAUNTLET_V4_SEAL",
        "sealed_at": results.get("measured_at"),
        "instrument": "a2_adversarial_gauntlet/2.0.0",
        "corpus_id": corpus.get("corpus_id"),
        "corpus_sha256": corpus.get("corpus_sha256"),
        "pre_registered_thresholds":
            corpus["pre_registered_thresholds"],
        "threshold_provenance": (
            "copied VERBATIM from the frozen corpus's own "
            "pre_registered_thresholds (R492/A2_DEV_CORPUS/"
            "CORPUS.json — the R412 sealed bars REUSED per Art. "
            "XXVII); the thresholds predate the v4 tuning (frozen "
            "2026-09-17 before any A2 measurement ran — the R492 "
            "FREEZE record)"),
        "sealing_discipline": (
            "Art. LIX: the DEV corpus is the tuning surface; the "
            "sealed benchmarks (R446/R412) are never touched by this "
            "tuning; the state is DERIVED by resolve_state from the "
            "measurement's numbers against these thresholds — never "
            "asserted"),
        "reviewer_provenance": "AI_REVIEW",
    }
    SEAL.write_text(json.dumps(seal, indent=1))
    _log(f"results -> {MEASUREMENT_RESULTS.relative_to(REPO)}")
    _log(f"measurement (registry schema) -> "
         f"{MEASUREMENT.relative_to(REPO)}")
    _log(f"seal -> {SEAL.relative_to(REPO)}")
    _log(f"HEADLINE: TPR={h.get('tpr_defect_cohorts')} "
         f"({h.get('detected_in_defect_cohorts')}) FPR="
         f"{h.get('fpr_known_good')} "
         f"({h.get('false_kills_on_controls')}) coverage="
         f"{h.get('coverage_all_9_fields')} parse="
         f"{h.get('parse_completeness')} verdict={verdict}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--pace", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--deployed", default="")
    a = ap.parse_args()
    if a.run:
        return run(a.pace, a.limit, a.resume, a.port, a.deployed)
    if a.score:
        return score()
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

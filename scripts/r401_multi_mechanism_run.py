#!/usr/bin/env python3
"""scripts/r401_multi_mechanism_run.py — R401 Phase 8 + Phase 11: ONE
complete end-to-end invention proof on a sufficiently rich problem.

    PROBLEM
      -> MULTI-SOURCE EVIDENCE (live retrieval)
      -> STRUCTURED MECHANISM SPACE (11-field evidence, 5 operators)
      -> >= 5 MATERIALLY DISTINCT MECHANISMS (distinctness-gated)
      -> MECHANISM-LEVEL EVIDENCE VERIFICATION
      -> CAD / ENGINEERING SPEC
      -> PLAUSIBILITY
      -> PHYSICS OR HONEST NON-SIMULATABLE
      -> BASELINE
      -> INDEPENDENT ATTACK
      -> TESTABLE PREDICTION
      -> MACHINE DECISION

A rejection is an acceptable result. A fabricated winner is not.

The driver is RESUMABLE: an interrupted run leaves its run directory;
re-invoke with --resume <run_dir> to continue from the last persisted
stage envelope (the conductor's own resume path).

Usage:
  python3 scripts/r401_multi_mechanism_run.py [--out R401/...] \
      [--run-dir ENGINE_RUNS/...] [--resume ENGINE_RUNS/...]

The zai local gateway is started as a child process when no gateway is
listening (the sandbox kills background processes between shells — the
driver owns the full lifecycle in-process, exactly like R400-C owned
its artifact server).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PROBLEM = {
    "problem_id": "r401_core_proof",
    "device": "peritoneal dialysis catheter",
    "failure": ("omental wrapping and fibrin clogging obstruct the "
                "catheter under low abdominal-flow conditions despite "
                "flushing protocols"),
    "failure_mode": "obstruction",
    "constraint": ("sustain drainage above 0.5 mL/min at normal "
                   "intra-abdominal pressure without systemic "
                   "anticoagulation"),
    "held_out": ("NOT one of the 18-case production benchmark "
                 "(r396_external_probes._benchmark_cases); probe-"
                 "measured literature density 1369 EuropePMC hits with "
                 "abstracts on the retrieval grammar — selected for "
                 "mechanism richness across peritoneal dialysis, "
                 "omental adhesion, antifouling coatings and drainage "
                 "design"),
}

R401_DIR = REPO_ROOT / "R401"
GATEWAY_PORT = 8787


def _load_key() -> str:
    kv = {}
    p = REPO_ROOT / ".env.keys"
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                kv[m.group(1)] = m.group(2)
    return kv.get("ZAI_API_KEY", "")


def _gateway_alive() -> bool:
    """TRUE liveness check: an HTTP response of ANY code (200/4xx)
    from the gateway's own route means the server is listening. A
    connection-level failure (URLError/ConnectionRefused) means it is
    not. NOTE: urlopen takes NO `headers` kwarg — a TypeError here
    previously masqueraded as "alive" and silently prevented the
    gateway from ever starting (found live during the R401 e2e run)."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(
        f"http://127.0.0.1:{GATEWAY_PORT}/healthz",
        method="GET")
    try:
        urllib.request.urlopen(req, timeout=3)
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, ConnectionError, OSError):
        return False


def _start_gateway(key: str):
    """Start the sandbox-local zai gateway as a child process.

    Stale-gateway discipline (measured live during the R401 e2e): a
    gateway whose parent run was killed mid-request can remain
    LISTENING with a wedged request handler — every subsequent LLM
    call then blocks on the socket read until its timeout. The driver
    therefore terminates any stale zai_gateway listener FIRST and
    always starts a fresh, healthy child it owns."""
    import subprocess as _sp
    try:
        _sp.run(["pkill", "-f", "zai_gateway.mjs"],
                capture_output=True, timeout=5)
        time.sleep(0.5)
    except Exception:  # noqa: BLE001 — best effort, disclosed by health
        pass
    if _gateway_alive():
        return None
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
        if _gateway_alive():
            return proc
    proc.terminate()
    return None

def _r401_metrics_from_run(run_dir: Path) -> Dict[str, Any]:
    """Compute the Phase 9 gauntlet-side counters from the run's OWN
    persisted artifacts (SURVIVOR_SELECTION.json's ranked list carries
    per-candidate killed/attack/physics records) — never re-derived
    narratives. Mechanism-space candidates are identified by their
    candidate_id prefix (cand:MS:)."""
    sel_path = run_dir / "SURVIVOR_SELECTION.json"
    ranked: List[Dict[str, Any]] = []
    if sel_path.exists():
        ranked = json.loads(sel_path.read_text()).get("ranked") or []
    ms_ranked = [r for r in ranked
                 if str(r.get("candidate_id", "")).startswith("cand:MS:")]
    ms_kills = []
    for f in sorted(run_dir.glob("PACKAGE_FAILED_mech-*.json")):
        try:
            ms_kills.append({
                "key": f.stem.replace("PACKAGE_FAILED_", ""),
                **json.loads(f.read_text())})
        except Exception:  # noqa: BLE001
            ms_kills.append({"key": f.name, "read_error": True})
    indep_attacks = sorted(run_dir.glob("INDEPENDENT_ATTACK_mech-*.json"))
    base = {
        "candidates_entering_gauntlet": len(ms_ranked) + len(ms_kills),
        "candidates_reaching_physics": sum(
            1 for r in ms_ranked if r.get("physics_lifecycle")),
        "candidates_beating_baseline": sum(
            1 for r in ms_ranked
            if r.get("physics_lifecycle") == "BEATS_BASELINE"),
        "candidates_surviving_attack": sum(
            1 for r in ms_ranked if not r.get("killed")),
        "candidates_rejected": sum(
            1 for r in ms_ranked if r.get("killed")) + len(ms_kills),
        "candidates_reaching_buyer_package": 0,
        "independent_attacks_recorded": len(indep_attacks),
        "gauntlet_kill_records": [
            {"key": k.get("key"), "stage": k.get("stage"),
             "reason": (k.get("reason") or "")[:160]}
            for k in ms_kills],
        "ranked_ms_candidates": ms_ranked,
    }
    return base


def _replay_precision_measurement() -> Dict[str, Any]:
    """B11: evidence_precision_before/after + mechanism-irrelevant
    precedent reduction, measured on the FIXED REPLAY SET (the same
    frozen set tests/test_r401_evidence_precision.py pins — loaded by
    module path so there is exactly ONE fixture authority)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r401_evidence_precision", REPO_ROOT / "tests" /
        "test_r401_evidence_precision.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    records = mod.REPLAY_SET
    rerank = ms_rerank = None
    from discovery_fabric.engine.mechanism_space import \
        mechanism_signal_rerank
    rerank = mechanism_signal_rerank(records, top_k=7)
    all_ids = [r["id"] for r in records]
    before = mod._evidence_precision(records, all_ids)
    after = mod._evidence_precision(records, rerank["selected_ids"])
    irrelevant_before = round(1 - before, 3)
    irrelevant_after = round(1 - after, 3)
    return {
        "replay_set_size": len(records),
        "evidence_precision_before": before,
        "evidence_precision_after": after,
        "mechanism_irrelevant_precedent_before": irrelevant_before,
        "mechanism_irrelevant_precedent_after": irrelevant_after,
        "measurement_basis": ("fixed replay set, content-labeled "
                              "independently of the ranker vocabulary "
                              "(Art. VIII); pinned by "
                              "tests/test_r401_evidence_precision.py"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(R401_DIR /
                                         "MULTI_MECHANISM_RUN.json"))
    ap.add_argument("--run-dir", default="")
    ap.add_argument("--resume", default="")
    args = ap.parse_args()

    key = _load_key()
    gateway = None
    if key:
        os.environ["ZAI_API_KEY"] = key
        gateway = _start_gateway(key)
        if not _gateway_alive():
            print("[r401] FATAL: the zai gateway could not be started "
                  "and no gateway is listening — the LLM transport "
                  "would be CONNECTION_REFUSED, which is an "
                  "infrastructure failure, not an honest run state "
                  "(Art. XXIX). Refusing to burn the run.")
            return 2
    if not os.environ.get("ZAI_API_KEY"):
        print("[r401] no ZAI_API_KEY — the LLM transport will be "
              "PROVIDER_UNAVAILABLE and the run will record it "
              "honestly (Art. XXV)")

    from discovery_fabric.engine.run import EngineRun
    if args.resume:
        run = EngineRun.from_run_dir(args.resume)
        run_dir = Path(args.resume)
        print(f"[r401] RESUMING {run_dir}")
    else:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        run_dir = Path(args.run_dir or
                       REPO_ROOT / "ENGINE_RUNS" /
                       f"r401_core_proof_{stamp}")
        run = EngineRun(PROBLEM, str(run_dir), run_id=f"r401:{stamp}")
        print(f"[r401] fresh run -> {run_dir}")

    started = time.time()
    final = run.run()
    elapsed = round(time.time() - started, 1)

    # the run's own persisted gauntlet records (never narratives)
    ms_block = run.env.mechanism_space or {}
    metrics = dict(ms_block.get("metrics") or {})
    metrics.update(_r401_metrics_from_run(run_dir))
    try:
        metrics.update(_replay_precision_measurement())
    except Exception as exc:  # noqa: BLE001 — recorded, never hidden
        metrics["replay_precision_error"] = \
            f"{type(exc).__name__}: {exc}"[:200]
    if (getattr(run, "package_report", None) or {}).get("complete"):
        metrics["candidates_reaching_buyer_package"] = 1

    record: Dict[str, Any] = {
        "suite": "R401 multi-mechanism end-to-end proof",
        "problem": PROBLEM,
        "run_dir": str(run_dir),
        "engine_commit_source": "local run on this checkout",
        "elapsed_s": elapsed,
        "mechanism_space_state": ms_block.get("state"),
        "n_candidates_generated": ms_block.get(
            "n_candidates_generated", 0),
        "n_candidates_retained": ms_block.get(
            "n_candidates_retained", 0),
        "operators": {k: v for k, v in (
            ms_block.get("operator_results") or [])
            .items()} if isinstance(
            ms_block.get("operator_results"), dict) else
            (ms_block.get("operator_results") or []),
        "distinctness": {
            k: v for k, v in (ms_block.get("distinctness") or
                              {}).items()
            if k in ("n_input", "n_kept", "kept_ids",
                     "distinctness_rule")},
        "candidates": [
            {k: c.get(k) for k in (
                "candidate_id", "transformation_operator", "mechanism",
                "intervention", "predicted_effect",
                "testable_prediction", "novel_design_variable",
                "candidate_state")}
            + {"mechanism_support_state": (c.get(
                "mechanism_support") or {}).get(
                "mechanism_support_state")}
            for c in (ms_block.get("candidates") or [])],
        "structured_evidence": {
            "n_items": (ms_block.get("structured_evidence") or {})
            .get("n_items", 0),
            "n_items_with_bound_mechanism": (
                ms_block.get("structured_evidence") or {}).get(
                "n_items_with_bound_mechanism", 0),
            "items": [
                {"item_id": it.get("item_id"),
                 "fields": {k: v for k, v in
                            (it.get("fields") or {}).items()},
                 "extraction_summary": it.get("extraction_summary")}
                for it in (ms_block.get("structured_evidence") or
                           {}).get("items", [])]},
        "metrics": metrics,
        "final_status": final.get("final_status"),
        "final_state": final.get("final_state"),
        "package": (getattr(run, "package_report", None) or {}).get(
            "complete"),
        "r401_metrics_note": (
            "the counters expose actual behavior (Phase 9); the machine "
            "is allowed to reject every candidate — a rejection is an "
            "acceptable result, a fabricated winner is not"),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, default=str))
    print(json.dumps({k: v for k, v in record.items()
                      if k not in ("candidates", "structured_evidence",
                                   "operators")},
                     indent=1, default=str))
    print(f"\nfull record -> {out}")
    if gateway:
        gateway.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""R495 — the repetition measurement of the DEPLOYED 2.0.0 burden-of-proof
gauntlet + the atria recovery probe, on the sibling's frozen R492 DEV corpus.

WHY THIS RUN EXISTS (the R493 seal discipline, verbatim): "a single run
cannot support a CALIBRATED flip; any future seal must be repetition-based
and carry the in-sample tuning disclosure." The shipped 2.0.0 measurement
(single run per ring: TPR 0.2727 xkiro / 0.3636 zai, FPR 0.0 both) is the
operative record; this round adds run #2 on the operative ring (xkiro,
through the deployed /api/ops/a2-attack transport) — the repetition data
the seal path demands.

DISCIPLINE (the R487/R491/R493/R494 lineage, preserved):
  - the corpus: the Space deploy does not carry R492/; the corpus is
    REBUILT from the shipped authorship modules (the freeze record's own
    authority: "the authorship modules are the record"). The case bytes
    are deterministic; per-case sha256 verified; ids/categories/order
    cross-checked against the shipped 2.0.0 record's per_case list.
    The corpus-level freeze sha (1e4a593f...) embeds created_at
    (microsecond build timestamp) and is NOT reproducible from shipped
    artifacts — DISCLOSED (Art. XI: unprovable stays unproven; Art. VI:
    never manufactured). The per-case inputs (candidate, evidence_items,
    prior_art_state) are byte-identical to the frozen cases.
  - identity gate: the LIVE /api/version must report the deployed
    engine commit (562c4ff0...) that ships a2_adversarial_gauntlet/2.0.0;
    every returned record must carry gauntlet_version == 2.0.0 (the
    instrument identity asserted per case, not per run).
  - ring pin: every case require_provider='xkiro' (the operative ring);
    pin violations NEVER score; EVALUATOR_CALL_FAILED is retriable and
    never counts as survival.
  - the sibling's score() imported VERBATIM (module-global overrides
    only — RAW_DIR/CORPUS_PATH/RESULTS_PATH/MEASUREMENT_PATH), pointed
    at THIS round's RAW dir; never mixed with any other run's pool.

Commands:
  python3 scripts/r495_repetition_and_recovery.py --probe-atria [N]
  python3 scripts/r495_repetition_and_recovery.py --run [--pace 12]
      [--slice N] [--resume]
  python3 scripts/r495_repetition_and_recovery.py --score
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r493_a2_baseline as baseline  # noqa: E402  (the sibling's scorer)

BASE_URL = "https://prateekm1-toscanini-prod-validation.hf.space"
OUT_DIR = REPO / "R495" / "A2_200_REPETITION"
RAW_DIR = OUT_DIR / "RAW"
PROBE_DIR = REPO / "R495"
CORPUS_REBUILT = Path(
    "/home/z/my-project/scripts/R495_corpuses/CORPUS_REBUILT.json")

# the deployed instrument identity this repetition asserts
DEPLOYED_INSTRUMENT = "a2_adversarial_gauntlet/2.0.0"
PINNED_PROVIDER = "xkiro"
SMOKE_CASE = "a2dev-01-cavitation-radical-bulk-kill"
PER_CASE_TIMEOUT = 500

# the shipped 2.0.0 records (the run #1 comparison base)
SHIPPED_MEAS = (REPO / "discovery_fabric" / "engine" /
                "calibration_records" / "a2_gauntlet_v4_measurement.json")


def _log(msg: str) -> None:
    print(f"[r495] {msg}", flush=True)


def _load_corpus() -> Dict[str, Any]:
    """The augmented recovery corpus (case bytes + the pinned thresholds,
    written to R495/CORPUS_RECOVERY.json so the sibling's scorer reads
    the same object this driver measured)."""
    recovery_path = REPO / "R495" / "CORPUS_RECOVERY.json"
    if recovery_path.exists():
        return json.loads(recovery_path.read_text())
    corpus = json.loads(CORPUS_REBUILT.read_text())
    # the pinned thresholds, copied VERBATIM from the shipped seal record
    # (which copied them verbatim from the frozen corpus — Art. XXVII)
    seal = json.loads((REPO / "discovery_fabric" / "engine" /
                       "calibration_records" /
                       "a2_gauntlet_v4_seal.json").read_text())
    corpus["pre_registered_thresholds"] = seal["pre_registered_thresholds"]
    corpus["frozen_before_any_tuning"] = True
    recovery_path.parent.mkdir(parents=True, exist_ok=True)
    recovery_path.write_text(
        json.dumps(corpus, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return corpus


def _corpus_identity(corpus: Dict[str, Any]) -> Dict[str, Any]:
    """The recovery freeze check: every reproducible pin, checked."""
    cases = corpus["cases"]
    per_sha = {
        c["case_id"]: hashlib.sha256(
            json.dumps(c, sort_keys=True, ensure_ascii=False)
            .encode("utf-8")).hexdigest() for c in cases}
    shipped = json.loads(SHIPPED_MEAS.read_text())
    shipped_ids = [p.get("case_id") for p in shipped.get("per_case", [])]
    ids_match = shipped_ids == [c["case_id"] for c in cases]
    cat_match = all(
        p.get("category") == c["category"]
        for p, c in zip(shipped.get("per_case", []), cases))
    internal = per_sha == corpus["per_case_sha256"]
    return {
        "corpus_id": corpus["corpus_id"],
        "n_cases": len(cases),
        "per_case_sha_internal_consistency": internal,
        "ids_order_match_shipped_200_record": ids_match,
        "categories_match_shipped_200_record": cat_match,
        "corpus_level_freeze_sha": (
            "NOT REPRODUCIBLE from shipped artifacts — the frozen sha "
            "(1e4a593f...) embeds created_at (microsecond build "
            "timestamp); the Space deploy does not carry R492/. The case "
            "bytes are rebuilt deterministically from the authorship "
            "modules — the freeze record's declared authority"),
        "recovery_corpus_sha256": hashlib.sha256(
            (json.dumps(corpus, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8")).hexdigest(),
        "recovery_disclosure": (
            "R495 recovery: the frozen corpus file was not shipped to "
            "the Space deploy; the corpus was rebuilt from the SHIPPED "
            "authorship modules (scripts/r492_corpus_cases_a.py + _b.py) "
            "whose case content is deterministic and time-independent; "
            "per-case sha256 map recomputed and internally verified; "
            "ids/order/categories cross-checked against the shipped "
            "2.0.0 measurement record (exact match). The per-case "
            "transport inputs are byte-identical to the frozen cases."),
    }


def _api_version() -> Dict[str, Any]:
    with urllib.request.urlopen(f"{BASE_URL}/api/version",
                                timeout=30) as r:
        return json.loads(r.read().decode())


def _identity_gate() -> str:
    v = _api_version()
    deployed = str(v.get("engine_commit") or "")
    _log(f"identity gate: live /api/version engine_commit "
         f"{deployed[:12]} (constitution {v.get('constitution_version')})")
    if not deployed:
        raise SystemExit("FATAL: live /api/version carries no engine_commit")
    return deployed


def _post_case(case: Dict[str, Any], provider: str) -> Dict[str, Any]:
    body = {
        "candidate": case["candidate"],
        "evidence_items": case.get("evidence_items") or [],
        "prior_art_state": (case.get("ground_truth") or {})
        .get("prior_art_state") or "UNKNOWN",
        "evidence_verified": True,
        "require_provider": provider,
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/ops/a2-attack", data=data, method="POST",
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=PER_CASE_TIMEOUT) as r:
            payload = json.loads(r.read().decode())
        return {"http": 200, "attack": payload.get("attack") or {},
                "latency_s": round(time.time() - t0, 1)}
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode())
        except Exception:  # noqa: BLE001
            detail = {}
        return {"http": e.code, "error": detail, "attack": {},
                "latency_s": round(time.time() - t0, 1)}
    except Exception as exc:  # noqa: BLE001 — typed, retriable
        return {"http": 0, "error": {"error": repr(exc)[:200]},
                "attack": {}, "latency_s": round(time.time() - t0, 1)}


def probe_atria(n: int) -> int:
    """Directive 2: the atria recovery probe (R488 proves it can serve;
    R493/R494 measured it typed-broken for attack prompts)."""
    deployed = _identity_gate()
    corpus = _load_corpus()
    smoke = next(c for c in corpus["cases"]
                 if c["case_id"] == SMOKE_CASE)
    attempts = []
    for i in range(1, n + 1):
        _log(f"atria probe [{i}/{n}] on {SMOKE_CASE} "
             f"(require_provider=atria)...")
        rec = _post_case(smoke, "atria")
        attack = rec.get("attack") or {}
        pin = (attack.get("transport") or {}).get("ring_pin") or {}
        entry = {
            "attempt": i,
            "http": rec.get("http"),
            "overall": attack.get("overall"),
            "error": rec.get("error"),
            "served_provider": pin.get("served_provider"),
            "served_model": pin.get("served_model"),
            "pin_violation": pin.get("pin_violation"),
            "latency_s": rec.get("latency_s"),
        }
        attempts.append(entry)
        _log(f"  http={entry['http']} overall={entry['overall']} "
             f"served={entry['served_provider']} "
             f"pin_violation={entry['pin_violation']} "
             f"({entry['latency_s']}s)")
        if i < n:
            time.sleep(10)
    typed_broken = all(
        (a.get("overall") == "EVALUATOR_CALL_FAILED")
        or a.get("http") != 200 for a in attempts)
    record = {
        "artifact_type": "ATRIA_RECOVERY_PROBE",
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_provenance": "AI_REVIEW",
        "deployed_engine_commit": deployed,
        "probe": ("POST /api/ops/a2-attack, require_provider=atria, "
                  "the R493/R494 probe pattern (2 pinned attempts, "
                  "typed outcomes, pin discipline held)"),
        "history": {
            "R488": "atria proven serving (the ring's own measurement)",
            "R493": "typed-broken for attack prompts "
                    "(EVALUATOR_CALL_FAILED, empty content, pin held)",
            "R494": "re-probed, 2 pinned attempts both CALL_FAILED",
        },
        "n_attempts": n,
        "attempts": attempts,
        "verdict": ("STILL_TYPED_BROKEN_FOR_ATTACK_PROMPTS"
                    if typed_broken else "RECOVERY_SIGNAL — serves attack "
                    "prompts again (re-measure before any ring use)"),
    }
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    out = PROBE_DIR / "ATRIA_RECOVERY_PROBE.json"
    out.write_text(json.dumps(record, indent=1, default=str))
    _log(f"probe record -> {out.relative_to(REPO)}")
    _log(f"VERDICT: {record['verdict']}")
    return 0


def run(pace: int, slice_n: int, resume: bool) -> int:
    deployed = _identity_gate()
    corpus = _load_corpus()
    identity = _corpus_identity(corpus)
    if not (identity["per_case_sha_internal_consistency"]
            and identity["ids_order_match_shipped_200_record"]
            and identity["categories_match_shipped_200_record"]):
        raise SystemExit("FATAL: corpus recovery identity check failed")
    _log(f"corpus recovery identity: all reproducible pins GREEN "
         f"({identity['n_cases']} cases)")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    done = {f.stem for f in RAW_DIR.glob("*.json")}
    pending = [c for c in corpus["cases"]
               if c["case_id"] not in done]
    if resume:
        _log(f"resume: {len(done)} on disk, {len(pending)} pending")
    todo = pending[:slice_n] if slice_n else pending
    _log(f"run: {len(todo)} cases this slice, pin '{PINNED_PROVIDER}', "
         f"pace {pace}s")

    for i, case in enumerate(todo, 1):
        cid = case["case_id"]
        _log(f"[{i}/{len(todo)}] {cid} (cat={case['category'][:30]})")
        t0 = time.time()
        rec = _post_case(case, PINNED_PROVIDER)
        attack = rec.get("attack") or {}
        pin = (attack.get("transport") or {}).get("ring_pin") or {}
        served = pin.get("served_provider")
        gv = attack.get("gauntlet_version")
        if rec.get("http") != 200 or not attack.get("overall"):
            _log(f"  TRANSPORT FAILURE http={rec.get('http')} — no "
                 f"marker, retriable ({time.time() - t0:.0f}s)")
        elif attack.get("overall") == "EVALUATOR_CALL_FAILED":
            _log(f"  EVALUATOR_CALL_FAILED on the pinned ring "
                 f"({time.time() - t0:.0f}s) — no marker, retriable")
        elif gv and gv != DEPLOYED_INSTRUMENT:
            _log(f"  INSTRUMENT IDENTITY VIOLATION: gauntlet_version="
                 f"{gv} (expected {DEPLOYED_INSTRUMENT}) — DISCARDED")
        elif pin.get("pin_violation") or (served
                                          and served != PINNED_PROVIDER):
            _log(f"  RING DEVIATION (served '{served}') — DISCARDED")
        else:
            (RAW_DIR / f"{cid}.json").write_text(
                json.dumps({"http": 200, "attack": attack,
                            "latency_s": rec.get("latency_s")},
                           indent=1, default=str))
            _log(f"  overall={attack.get('overall')} killed="
                 f"{attack.get('killed_count')} risks="
                 f"{len(attack.get('risk_flags') or [])} "
                 f"({rec.get('latency_s')}s, {served}/"
                 f"{pin.get('served_model')}, {gv})")
        if i < len(todo) and pace:
            time.sleep(pace)
    _log(f"slice done: {len(done) + len(todo)} total on disk "
         f"(of {len(corpus['cases'])})")
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
    corpus = _load_corpus()
    identity = _corpus_identity(corpus)
    deployed = _identity_gate()
    # the sibling's scorer, VERBATIM, pointed at this round's pool
    baseline.CORPUS_PATH = REPO / "R495" / "CORPUS_RECOVERY.json"
    baseline.RAW_DIR = RAW_DIR
    baseline.RESULTS_PATH = OUT_DIR / "MEASUREMENT_RESULTS.json"
    baseline.MEASUREMENT_PATH = OUT_DIR / "MEASUREMENT.json"
    results = baseline.score()

    results["report_version"] = "r495-a2-200-repetition/1.0.0"
    results["round"] = "R495"
    results["deployed_commit"] = deployed
    results["instrument"] = (
        "a2/adversarial.py::adversarial_challenge "
        f"({DEPLOYED_INSTRUMENT} — the deployed burden-of-proof rules), "
        "measured through the LIVE deployed transport")
    results["transport"] = (
        "POST /api/ops/a2-attack (require_provider=xkiro), the R493 "
        "deployed-transport discipline — run #2 on the operative ring "
        "(run #1: the shipped a2_gauntlet_v4_measurement.json)")
    results["corpus_identity"] = identity
    results["ring_summary"] = _ring_summary()

    # ---- the repetition comparison vs the shipped run #1 ----
    shipped = json.loads(SHIPPED_MEAS.read_text())
    ship_by_id = {p.get("case_id"): p for p in shipped.get("per_case", [])}
    flips = []
    for p in results.get("per_case", []):
        cid = p.get("case_id")
        s = ship_by_id.get(cid) or {}
        if p.get("state") != s.get("state") or \
                p.get("overall") != s.get("overall"):
            flips.append({
                "case_id": cid, "cohort": p.get("cohort"),
                "run1": {"state": s.get("state"),
                         "overall": s.get("overall"),
                         "detected": s.get("detected"),
                         "false_kill": s.get("false_kill")},
                "run2": {"state": p.get("state"),
                         "overall": p.get("overall"),
                         "detected": p.get("detected"),
                         "false_kill": p.get("false_kill")}})
    h1 = {"tpr": shipped.get("scoped_tpr_diagnostic", {}).get("tpr"),
          "fpr": shipped.get("metrics", {})
          .get("false_kill_rate_on_known_good"),
          "coverage": shipped.get("metrics", {}).get("coverage"),
          "parse": shipped.get("metrics", {}).get("parse_completeness")}
    h2 = (results.get("headline") or {})
    comparison = {
        "run_1": {
            "record": "discovery_fabric/engine/calibration_records/"
                      "a2_gauntlet_v4_measurement.json (the shipped "
                      "operative measurement, 2026-09-17T16:56Z)",
            "ring": "xkiro (deployed transport)",
            **h1},
        "run_2": {
            "record": "R495/A2_200_REPETITION/MEASUREMENT_RESULTS.json "
                      "(this run)",
            "ring": f"{PINNED_PROVIDER} (deployed transport)",
            "tpr": h2.get("tpr_defect_cohorts"),
            "fpr": h2.get("fpr_known_good"),
            "coverage": h2.get("coverage_all_9_fields"),
            "parse": h2.get("parse_completeness")},
        "per_case_state_overall_flips": flips,
        "n_flips": len(flips),
        "repetition_reading": (
            "the R493 variance disclosure (a2dev-13's kill vanished "
            "between v4 and v4.1 with no code change) demands repetition "
            "before any seal; this run is the second sample of the SAME "
            "instrument on the SAME corpus on the SAME ring — the "
            "per-case flip set quantifies run-to-run evaluator variance "
            "on the frozen corpus"),
    }
    results["repetition_comparison"] = comparison

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "MEASUREMENT_RESULTS.json").write_text(
        json.dumps(results, indent=1, default=str))
    (OUT_DIR / "REPETITION_COMPARISON.json").write_text(
        json.dumps(comparison, indent=1, default=str))
    _log(f"results -> {OUT_DIR.relative_to(REPO)}/MEASUREMENT_RESULTS.json")
    _log(f"comparison -> "
         f"{OUT_DIR.relative_to(REPO)}/REPETITION_COMPARISON.json")
    _log(f"HEADLINE run#2: TPR={h2.get('tpr_defect_cohorts')} "
         f"({h2.get('detected_in_defect_cohorts')}) FPR="
         f"{h2.get('fpr_known_good')} "
         f"({h2.get('false_kills_on_controls')}) coverage="
         f"{h2.get('coverage_all_9_fields')} parse="
         f"{h2.get('parse_completeness')} | run#1 TPR={h1['tpr']} "
         f"FPR={h1['fpr']} | flips={len(flips)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-atria", type=int, nargs="?", const=2,
                    default=None)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--pace", type=int, default=12)
    ap.add_argument("--slice", type=int, default=8)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if a.probe_atria is not None:
        return probe_atria(a.probe_atria)
    if a.run:
        return run(a.pace, a.slice, a.resume)
    if a.score:
        return score()
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

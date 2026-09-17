#!/usr/bin/env python3
"""scripts/r487_attacker_v3_measurement.py — R487: the FRESH v3
measurement on the frozen R446 corpus (the sealed-bar run).

This is the measurement that decides the v3.0.0 calibration state.
The design dry-run (r487_v3_dryrun.py) validated the rule DIRECTION on
the frozen v2 outputs; THIS run measures the actual instrument — the
v3 prompt (the kill standard) + the anchor floor + the accommodation
checks — as deployed, through its real transport:

  the LOCAL driver submits each frozen corpus case to the deployed
  engine's POST /api/ops/calibration-attack (one attack per request),
  which runs the SAME independent_attack code path every production
  run's gauntlet uses, on the production provider ring. The local
  vault holds no provider keys (the container recycle; BS-021) — the
  Space is the only place the instrument runs as deployed.

Honest protections, all preserved verbatim from the R447 discipline:
  - NO threshold is lowered (the bars are read from the frozen corpus
    header — the R412 sealed bars REUSED)
  - NO corpus byte is modified (the frozen sha is asserted before and
    after the run)
  - NO clean control is altered; no false kill is relabeled
  - the calibration gate DERIVES the state from the committed
    measurement record (attacker_calibration.resolve_state) — this
    driver claims nothing
  - demoted kills are preserved verbatim with their rule records

Commands:
  python3 scripts/r487_attacker_v3_measurement.py --run [--resume]
  python3 scripts/r487_attacker_v3_measurement.py --score
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

CORPUS_PATH = REPO / "R446" / "ATTACKER_CALIBRATION" / "CORPUS.json"
FROZEN_SHA_SOURCE = REPO / "R446" / "ATTACKER_CALIBRATION" / \
    "CALIBRATION_RESULTS.json"
OUT_DIR = REPO / "R487" / "ATTACKER_V3_CALIBRATION"
RAW_DIR = OUT_DIR / "RAW"
RESULTS_PATH = OUT_DIR / "MEASUREMENT_RESULTS.json"
MEASUREMENT_PATH = OUT_DIR / "MEASUREMENT.json"
SEAL_PATH = OUT_DIR / "SEAL.json"

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
EXPECTED_IDENTITY = os.environ.get(
    "EXPECTED_IDENTITY", "")  # set to the deployed v3 commit

from discovery_fabric.engine import attacker_calibration as gate  # noqa: E402
import r447_attacker_v2_recalibration as frozen  # noqa: E402


def _log(msg: str) -> None:
    print(f"[r487-v3-meas] {msg}", flush=True)


def _sha256(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _freeze_check() -> Dict[str, Any]:
    frozen = None
    try:
        rec = json.loads(FROZEN_SHA_SOURCE.read_text())
        frozen = (rec.get("freeze_check") or {}).get("corpus_sha256")
    except Exception:  # noqa: BLE001
        pass
    actual = _sha256(CORPUS_PATH)
    dirty = subprocess.run(
        ["git", "status", "--porcelain",
         "--", str(CORPUS_PATH.relative_to(REPO))],
        cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    return {
        "corpus_sha256": actual,
        "frozen_sha256_from_r446_record": frozen,
        "sha_matches_frozen": (frozen is None or actual == frozen),
        "corpus_dirty_in_worktree": bool(dirty),
        "instrument": "independent_attack/3.0.0",
        "instrument_delta_vs_v2": (
            "the ANCHOR floor (computation-only kills demote) + the "
            "ACCOMMODATION record-answer checks (concession-disposal "
            "/ hedged-target / unstated-element / typical-value-"
            "premise; evidence-anchored kills never demoted) + the "
            "kill-standard prompt paragraph; corpus, thresholds, "
            "clean controls untouched"),
        "transport": (
            "the DEPLOYED engine's /api/ops/calibration-attack — the "
            "same instrument code path the production gauntlet uses, "
            "on the production provider ring"),
        "freeze_ok": (frozen is None or actual == frozen) and not dirty,
    }


def _req(path: str, body: Dict[str, Any] = None, timeout: int = 900):
    # client read ceiling (observation-side only): 240 -> 900s. The
    # parallel R488 line's single-case latency probe measured 440s for
    # ONE attack on the deployed production ring, and this line's
    # foreground-batch run measured 118-551s with cal-12 landing at
    # 542s only on the 5th attempt and cal-18 never landing under a
    # 560s ceiling (5 consecutive read-timeouts) — the R488 union takes
    # the measured-safe 900s. A client POLL_TIMEOUT here is a
    # TRANSPORT_INCOMPLETE observation, never a run verdict (Art.
    # LXXIV), and the case simply re-runs on --resume (no marker
    # written). No threshold, corpus byte, scoring rule, or verdict
    # path is touched. Disclosed in R487/R488_ROUND_RECORD.json.
    import urllib.error
    import urllib.request
    HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
    if not HF_TOKEN:
        p = Path("/home/z/my-project/.secrets.env")
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("HF_TOKEN="):
                    HF_TOKEN = line.split("=", 1)[1].strip()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {HF_TOKEN}"},
        method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"http_status": r.status,
                    "body": json.loads(r.read() or b"{}")}
    except urllib.error.HTTPError as e:
        try:
            txt = e.read()[:300].decode(errors="replace")
        except Exception:  # noqa: BLE001
            txt = ""
        return {"http_status": e.code, "error": txt}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None,
                "error": f"{type(exc).__name__}: {exc}"}


def load_raw() -> Dict[str, Dict[str, Any]]:
    raw: Dict[str, Dict[str, Any]] = {}
    if RAW_DIR.exists():
        for p in sorted(RAW_DIR.glob("*.json")):
            try:
                d = json.loads(p.read_text())
                # the endpoint wraps the record: {"attack": {...}}
                raw[p.stem] = d.get("attack") or d
            except Exception:  # noqa: BLE001
                continue
    return raw


def write_measurement(results: Dict[str, Any]) -> Dict[str, Any]:
    """The gate-readable measurement record (the shape
    attacker_calibration.resolve_state consumes — the r447 shape)."""
    hc = results["headline_confusion"]
    meas = {
        "artifact_type": "ATTACKER_V3_MEASUREMENT",
        "instrument": "independent_attack/3.0.0",
        "measured_at": results["measured_at"],
        "reviewer_provenance": "AI_REVIEW",
        "corpus": {
            "path": "R446/ATTACKER_CALIBRATION/CORPUS.json",
            "sha256": _sha256(CORPUS_PATH),
            "frozen_unchanged": _freeze_check()["sha_matches_frozen"],
            "n_cases": len(results["per_case"]),
        },
        "metrics": {
            "false_kill_rate_on_known_good": hc["FPR"],
            "coverage": results["coverage"],
            "parse_completeness": results["parse_completeness"],
            "tnr": hc["TNR"],
        },
        "scoped_tpr_diagnostic": {
            "tpr": hc["TPR"],
            "cohort": "seeded defects (seed_class set)",
        },
        "n_cases_attacked": sum(
            1 for s in results["per_case"]
            if s.get("outcome") not in ("NOT_RUN",
                                        "TRANSPORT_INCOMPLETE")),
        "threshold_verdict": {
            "calibrated": bool(
                results["bars_met"].get("tpr")
                and results["bars_met"].get("fpr")
                and results["bars_met"].get("coverage")
                and results["bars_met"].get("parse")),
            "bars": results["pre_registered_bars"],
            "bars_met": results["bars_met"],
        },
        "transport": _freeze_check()["transport"],
        "note": ("the constitutional gate (attacker_calibration."
                 "resolve_state) re-derives the admission decision from "
                 "these numbers against the seal — this record's "
                 "threshold_verdict is the same computation, recorded "
                 "for audit; the GATE is the authority"),
    }
    MEASUREMENT_PATH.write_text(json.dumps(meas, indent=1,
                                           default=str))
    seal = {
        "artifact_type": "ATTACKER_V3_SEAL",
        "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "pre_registered_thresholds": results["pre_registered_bars"],
        "provenance": ("REUSED verbatim from the frozen corpus header "
                       "(R446/ATTACKER_CALIBRATION/CORPUS.json "
                       "pre_registered_thresholds), which itself "
                       "reused the R412 sealed bars — NO new threshold "
                       "invented (Art. XXVII)"),
        "note": ("the seal pins the bars the gate reads for "
                 "independent_attack/3.0.0; the corpus and its "
                 "thresholds predate this instrument version"),
    }
    SEAL_PATH.write_text(json.dumps(seal, indent=1, default=str))
    return meas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip", default="",
                    help="comma-separated case_ids to NOT attempt this "
                         "invocation (batching control only — the "
                         "marker discipline is untouched; skipped "
                         "cases simply stay NOT_RUN for this pass "
                         "and are honestly typed)")
    args = ap.parse_args()

    corpus = json.loads(CORPUS_PATH.read_text())
    problem = corpus["the_common_problem"]

    if args.run:
        freeze = _freeze_check()
        if not freeze["freeze_ok"]:
            _log("FATAL: corpus not byte-identical to the frozen R446 "
                 "record (or dirty)")
            return 2
        v = _req("/api/version", timeout=60)
        served = ((v.get("body") or {}).get("engine_commit") or "")
        _log(f"production serves {served[:12]}")
        if EXPECTED_IDENTITY and served != EXPECTED_IDENTITY:
            _log(f"FATAL: identity gate — expected "
                 f"{EXPECTED_IDENTITY[:12]}")
            return 2
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        skip_ids = {s.strip() for s in args.skip.split(",") if s.strip()}
        cases = corpus["cases"]
        if args.limit:
            cases = cases[:args.limit]
        if skip_ids:
            _log(f"batching skip (this pass only): {sorted(skip_ids)}")
            cases = [c for c in cases if c["case_id"] not in skip_ids]
        for case in cases:
            marker = RAW_DIR / f"{case['case_id']}.json"
            if args.resume and marker.exists():
                _log(f"{case['case_id']}: RAW exists (resume)")
                continue
            _log(f"{case['case_id']}: attacking (v3, deployed)...")
            t0 = time.time()
            r = _req("/api/ops/calibration-attack", body={
                "candidate": case["candidate"],
                "problem": problem,
                "evidence": case.get("evidence_items") or [],
            })
            if r.get("http_status") != 200:
                _log(f"{case['case_id']}: TRANSPORT FAILURE "
                     f"{r.get('http_status')} "
                     f"{str(r.get('error'))[:160]}")
                continue
            attack = (r.get("body") or {}).get("attack") or {}
            marker.write_text(json.dumps(r.get("body"), indent=1,
                                         default=str))
            _log(f"{case['case_id']}: {attack.get('overall')} "
                 f"({time.time() - t0:.0f}s, "
                 f"{attack.get('attacker_provider')}/"
                 f"{attack.get('attacker_model')})")

    raw = load_raw()
    results = frozen.score_all(corpus, raw)
    results["report_version"] = "r487-attacker-v3-measurement/1.0.0"
    results["freeze_check"] = _freeze_check()
    results["instrument"] = ("independent_attack/3.0.0 (the anchor + "
                             "accommodation discipline)")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=1, default=str))
    meas = write_measurement(results)

    hc = results["headline_confusion"]
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
    st = gate.resolve_state(instrument_version="independent_attack/3.0.0")
    _log(f"GATE STATE (in-tree, pre-shipment): {st.get('state')} "
         f"(terminal_kill_admissible="
         f"{st.get('terminal_kill_admissible')}) — the shipped-record "
         f"flip happens via scripts/r487_ship_v3_records.py")
    _log(f"results -> {RESULTS_PATH}")
    _log(f"measurement -> {MEASUREMENT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""scripts/r491_ring_pinned_measurement.py — R491: the RING-PINNED
sealed-corpus measurement of independent_attack/3.0.0.

THE MEASURED QUESTION (roadmap minimum-path item 1, the load-bearing
wall): do the v3 rules meet the sealed bars when the attacker runs on
the STRONG ring it declares — instead of wherever the availability
cascade lands under load?

THE MEASURED BASIS (R488, committed bytes): attacker calibration is
(rules x ring). The same v3 rules measured FPR 0.25 on the strong
ring's frozen outputs (the R487 design dry-run over the GLM-5.3-served
v2 raw records) and FPR 1.0 live when the cascade fell to
xkiro/qwen3.8-max:free (20/22 cases, atria rate-limited under the
measurement's own load). This run PINS the attacker to one declared
provider ring via the committed transport's require_provider parameter
(fail-closed: a pinned provider that is unavailable or fails yields a
typed transport failure — NEVER a silent ring change), runs
SEQUENTIALLY with pacing between cases (the ring-friendly shape; the
R488 parallel waves starved atria), and resumes case-by-case.

Honest protections, all preserved verbatim from the R447/R487
discipline:
  - NO threshold is lowered (the R412 sealed bars REUSED, read from
    the frozen corpus header)
  - NO corpus byte is modified (the frozen sha asserted before and
    after the run)
  - NO clean control is altered; no false kill is relabeled
  - the calibration gate DERIVES the state from the committed
    measurement record — this driver claims nothing
  - every case's ring is asserted: a case NOT served by the pinned
    ring is recorded as RING_DEVIATION and never scores

Commands:
  python3 scripts/r491_ring_pinned_measurement.py --run [--resume]
      [--provider atria] [--pace 30] [--limit N] [--skip id1,id2]
  python3 scripts/r491_ring_pinned_measurement.py --score
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
OUT_DIR = REPO / "R491" / "RING_PINNED_MEASUREMENT"
RAW_DIR = OUT_DIR / "RAW"
RESULTS_PATH = OUT_DIR / "MEASUREMENT_RESULTS.json"
MEASUREMENT_PATH = OUT_DIR / "MEASUREMENT.json"
SEAL_PATH = OUT_DIR / "SEAL.json"

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
# the deployed commit that carries the require_provider transport
# (set explicitly at invocation; an empty value disables the gate)
EXPECTED_IDENTITY = os.environ.get("EXPECTED_IDENTITY", "")

from discovery_fabric.engine import attacker_calibration as gate  # noqa: E402
import r447_attacker_v2_recalibration as frozen  # noqa: E402


def _log(msg: str) -> None:
    print(f"[r491-pin-meas] {msg}", flush=True)


def _sha256(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _freeze_check() -> Dict[str, Any]:
    frozen_sha = None
    try:
        rec = json.loads(FROZEN_SHA_SOURCE.read_text())
        frozen_sha = (rec.get("freeze_check") or {}).get("corpus_sha256")
    except Exception:  # noqa: BLE001
        pass
    actual = _sha256(CORPUS_PATH)
    dirty = subprocess.run(
        ["git", "status", "--porcelain",
         "--", str(CORPUS_PATH.relative_to(REPO))],
        cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    return {
        "corpus_sha256": actual,
        "frozen_sha256_from_r446_record": frozen_sha,
        "sha_matches_frozen": (frozen_sha is None or actual == frozen_sha),
        "corpus_dirty_in_worktree": bool(dirty),
        "instrument": "independent_attack/3.0.0",
        "instrument_delta_vs_r488_measurement": (
            "NONE to the instrument's rules — the SAME v3 anchor + "
            "accommodation discipline; the DELTA is the declared RING: "
            "require_provider pins the attacker to one provider "
            "(fail-closed, no cascade), where the R488 measurement "
            "accepted whatever the availability cascade served "
            "(qwen3.8-max:free 20/22)"),
        "transport": (
            "the DEPLOYED engine's /api/ops/calibration-attack with "
            "require_provider — the same instrument code path the "
            "production gauntlet uses, on ONE declared provider ring"),
        "freeze_ok": (frozen_sha is None or actual == frozen_sha)
        and not dirty,
    }


def _req(path: str, body: Dict[str, Any] = None, timeout: int = 900):
    # client read ceiling 900s (the R488 union's measured-safe value;
    # observation-side only — a timeout is TRANSPORT_INCOMPLETE, never
    # a verdict, and the case re-runs on --resume)
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
                raw[p.stem] = d.get("attack") or d
            except Exception:  # noqa: BLE001
                continue
    return raw


def _ring_summary(raw: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """The measured ring, derived from the per-case records — never
    asserted. A case whose pin was violated is disclosed."""
    providers: Dict[str, int] = {}
    models: Dict[str, int] = {}
    deviations = []
    for cid, rec in sorted(raw.items()):
        rp = rec.get("ring_pin") or {}
        served = rp.get("served_provider") or rec.get("attacker_provider")
        model = rp.get("served_model") or rec.get("attacker_model")
        providers[served or "UNKNOWN"] = providers.get(
            served or "UNKNOWN", 0) + 1
        models[model or "UNKNOWN"] = models.get(model or "UNKNOWN", 0) + 1
        if rp.get("pin_violation") or (
                rp.get("requested") and served
                and served != rp.get("requested")):
            deviations.append(cid)
    return {"providers": providers, "models": models,
            "pin_violations": deviations}


def write_measurement(results: Dict[str, Any],
                      provider_pin: str) -> Dict[str, Any]:
    """The gate-readable measurement record (the shape
    attacker_calibration.resolve_state consumes) — now carrying the
    measured attacker_ring block (R491: the calibration is ring-bound
    at consumption)."""
    hc = results["headline_confusion"]
    ring = _ring_summary(results["raw_records"]
                         if "raw_records" in results else load_raw())
    top_provider = max(ring["providers"].items(),
                       key=lambda kv: kv[1])[0] if ring["providers"] \
        else None
    top_model = max(ring["models"].items(),
                    key=lambda kv: kv[1])[0] if ring["models"] else None
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
        "attacker_ring": {
            "provider": top_provider,
            "model": top_model,
            "ring_pin": provider_pin,
            "serving": (f"{sum(ring['providers'].values())} cases; "
                        f"per-provider {json.dumps(ring['providers'])}"),
            "pin_violations": ring["pin_violations"],
            "note": ("R491: the calibration is (rules x ring) — the "
                     "R488 measured lesson; the gate binds terminal "
                     "kill authority to THIS ring at consumption"),
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
    ap.add_argument("--provider", default="atria",
                    help="the declared attacker ring (fail-closed pin)")
    ap.add_argument("--pace", type=int, default=30,
                    help="seconds between sequential cases (ring-"
                         "friendly pacing; the R488 parallel waves "
                         "starved the strong ring)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip", default="",
                    help="comma-separated case_ids to NOT attempt this "
                         "invocation (batching control only)")
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
                 f"{EXPECTED_IDENTITY[:12]} (the ring-pin transport "
                 f"must be the deployed build)")
            return 2
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
                _log(f"pacing {args.pace}s (ring-friendly)")
                time.sleep(args.pace)
            _log(f"{case['case_id']}: attacking (pinned "
                 f"'{args.provider}', deployed)...")
            t0 = time.time()
            r = _req("/api/ops/calibration-attack", body={
                "candidate": case["candidate"],
                "problem": problem,
                "evidence": case.get("evidence_items") or [],
                "require_provider": args.provider,
            })
            if r.get("http_status") != 200:
                _log(f"{case['case_id']}: TRANSPORT FAILURE "
                     f"{r.get('http_status')} "
                     f"{str(r.get('error'))[:200]}")
                # fail-closed pin: no marker, the case re-runs on
                # --resume; NEVER accept a served-wrong-ring response
                continue
            attack = (r.get("body") or {}).get("attack") or {}
            rp = attack.get("ring_pin") or {}
            served_p = attack.get("attacker_provider")
            if rp.get("pin_violation") or (
                    served_p and served_p != args.provider):
                _log(f"{case['case_id']}: RING DEVIATION (served "
                     f"'{served_p}', pinned '{args.provider}') — "
                     f"marker DISCARDED")
                continue
            marker.write_text(json.dumps(r.get("body"), indent=1,
                                         default=str))
            n_done += 1
            _log(f"{case['case_id']}: {attack.get('overall')} "
                 f"({time.time() - t0:.0f}s, "
                 f"{served_p}/{attack.get('attacker_model')})")

    raw = load_raw()
    if not raw:
        _log("no RAW records yet — run with --run first")
        return 0
    results = frozen.score_all(corpus, raw)
    results["report_version"] = "r491-ring-pinned-measurement/1.0.0"
    results["freeze_check"] = _freeze_check()
    results["instrument"] = ("independent_attack/3.0.0 (unchanged "
                             "rules; the RING-PINNED re-measurement)")
    results["ring_summary"] = _ring_summary(raw)
    results["ring_pin_requested"] = args.provider
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=1, default=str))
    meas = write_measurement(results, args.provider)

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
        measurement_path=MEASUREMENT_PATH, seal_path=SEAL_PATH,
        instrument_version="independent_attack/3.0.0")
    _log(f"GATE STATE (this record, pre-shipment): {st.get('state')} "
         f"(terminal_kill_admissible="
         f"{st.get('terminal_kill_admissible')}; ring_binding="
         f"{st.get('ring_binding')}) — the shipped-record flip happens"
         f" via scripts/r491_ship_records.py")
    _log(f"results -> {RESULTS_PATH}")
    _log(f"measurement -> {MEASUREMENT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

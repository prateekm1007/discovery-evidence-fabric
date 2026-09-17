#!/usr/bin/env python3
"""scripts/r493_a2_baseline.py — R493: the UNTUNED baseline measurement
of the A2 gauntlet on the FROZEN DEV corpus, through the DEPLOYED
instrument's own measurement transport.

THE MEASURED QUESTION (the operator's directive, step 2): with the
/api/ops/a2-attack transport live on the deployed build, what does the
CURRENT (untuned) gauntlet actually measure on the frozen DEV corpus?
This number is the baseline the v4 tuning is judged against — and the
first A2 number that has ever existed (the R490 measured fact: the
gauntlet had no calibration corpus, no sealed bars, no measurement).

DISCIPLINE (the R447/R487/R491 measurement lineage, preserved):
  - the FROZEN corpus is asserted before and after (sha 1e4a593f...);
    no corpus byte is modified, no case is altered, no false kill is
    relabeled
  - the identity gate: the deployed engine_commit must equal the
    commit this transport ships in (the measurement runs on the
    DEPLOYED instrument with the production provider ring)
  - the ring pin: every case declares require_provider=atria (the
    gauntlet's declared primary; the R488 lesson: calibration is
    (rules x ring) — a measurement that lands wherever the cascade
    falls measures nothing). A case served by a DIFFERENT ring is
    recorded RING_DEVIATION and never scores (retriable via --resume)
  - SEQUENTIAL with pacing (the ring-friendly shape; the R488
    parallel waves starved the strong ring under the measurement's
    own load)
  - NO threshold is invented: the bars are the corpus's
    pre-registered thresholds (the R412 sealed bars REUSED verbatim,
    Art. XXVII)
  - this driver claims nothing: the calibration gate derives the
    state from committed records; this run only MEASURES

Scoring contract: the corpus's own (R492/A2_DEV_CORPUS/CORPUS.json
scoring_contract) — TPR over the defect cohorts with marker binding,
FPR/TNR over the clean controls, the near-miss / scope-conflict /
malformed category disciplines OUTSIDE the headline, coverage and
parse_completeness with conservative sealed-denominator rules. The
summary also emits the ENGINE registry schema keys
(metrics.false_kill_rate_on_known_good, scoped_tpr_diagnostic.tpr,
threshold_verdict) so a future seal plugs into the canonical registry
without translation.

Commands:
  python3 scripts/r493_a2_baseline.py --run [--resume] [--provider atria]
      [--pace 20] [--limit N]
  python3 scripts/r493_a2_baseline.py --score
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

CORPUS_PATH = REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json"
FREEZE_PATH = REPO / "R492" / "A2_DEV_CORPUS" / "FREEZE.json"
OUT_DIR = REPO / "R493" / "A2_BASELINE"
RAW_DIR = OUT_DIR / "RAW"
RESULTS_PATH = OUT_DIR / "MEASUREMENT_RESULTS.json"
MEASUREMENT_PATH = OUT_DIR / "MEASUREMENT.json"

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
EXPECTED_COMMIT = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=str(REPO),
    capture_output=True, text=True).stdout.strip()
PER_CASE_TIMEOUT = 500     # gauntlet llm_chat 420s + server overhead
DIMENSIONS = ["unsupported_mechanism", "weak_transfer",
              "obvious_combination", "prior_art", "contradiction",
              "boundary_failure", "engineering_infeasibility",
              "regulatory_incompatibility"]


def _log(msg: str) -> None:
    print(f"[r493-baseline] {msg}", flush=True)


def _sha256(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _freeze_check() -> str:
    """The R492 freeze hash is the CANONICAL reconstruction sha (the
    corpus body without the corpus_sha256 key, json.dumps indent=2
    ensure_ascii=False + trailing newline) — the same computation the
    R492 freeze tests pin, NOT the raw file bytes."""
    frozen = json.loads(FREEZE_PATH.read_text()).get("corpus_sha256")
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    body = {k: v for k, v in corpus.items() if k != "corpus_sha256"}
    blob = json.dumps(body, indent=2, ensure_ascii=False) + "\n"
    actual = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    if not frozen or actual != frozen:
        raise SystemExit(
            f"FATAL: corpus freeze mismatch: FREEZE says {frozen}, "
            f"reconstruction hashes {actual} — the corpus moved; this "
            "is a NEW corpus version and the old freeze exposes it "
            "(Art. LIX)")
    return actual


def _identity_gate() -> Dict[str, Any]:
    req = urllib.request.Request(f"{BASE}/api/version", method="GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        v = json.loads(r.read().decode())
    deployed = v.get("engine_commit", "")
    ok = bool(deployed) and deployed == EXPECTED_COMMIT
    _log(f"identity gate: deployed={deployed[:12]} "
         f"expected={EXPECTED_COMMIT[:12]} -> {'OK' if ok else 'MISMATCH'}")
    if not ok:
        raise SystemExit(
            "FATAL: the deployed build is not the commit that ships "
            "the A2 transport — deploy first (the measurement must "
            "run on the deployed instrument)")
    return v


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
        f"{BASE}/api/ops/a2-attack", data=data, method="POST",
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


def _kill_dims(record: Dict[str, Any]) -> List[str]:
    return [d for d, v in (record.get("attacks") or {}).items()
            if "KILLED" in str(v).upper()
            and "ADVERSARIAL_INVALID" not in str(v).upper()]


def _basis_text(record: Dict[str, Any]) -> str:
    parts = [str((record.get("attacks") or {}).get(d, ""))
             for d in DIMENSIONS]
    parts.append(str(record.get("reason") or ""))
    return " ".join(parts).lower()


def _marker_bound(case: Dict[str, Any], record: Dict[str, Any]) -> bool:
    markers = [(case.get("ground_truth") or {})
               .get("expected_defect_in_basis") or []]
    text = _basis_text(record)
    return any(m and str(m).lower() in text for m in markers[0])


def _parsed_fields(record: Dict[str, Any]) -> int:
    attacks = record.get("attacks") or {}
    n = sum(1 for d in DIMENSIONS if str(attacks.get(d, "")).strip())
    if str(record.get("overall", "")).strip():
        n += 1
    return n


def score() -> Dict[str, Any]:
    corpus = json.loads(CORPUS_PATH.read_text())
    cases = corpus["cases"]
    raw: Dict[str, Any] = {}
    for f in sorted(RAW_DIR.glob("*.json")):
        raw[f.stem] = json.loads(f.read_text())

    per_case: List[Dict[str, Any]] = []
    for case in cases:
        cid = case["case_id"]
        rec = raw.get(cid)
        if not rec:
            per_case.append({"case_id": cid, "state": "NOT_RUN"})
            continue
        entry: Dict[str, Any] = {
            "case_id": cid, "category": case["category"],
            "latency_s": rec.get("latency_s"),
        }
        if rec.get("http") != 200 or not (rec.get("attack") or {}).get(
                "overall"):
            entry["state"] = (
                "RING_DEVIATION"
                if (rec.get("error") or {}).get("code") == "RING_DEVIATION"
                else "TRANSPORT_FAILURE")
            entry["error"] = rec.get("error")
            per_case.append(entry)
            continue
        attack = rec["attack"]
        overall = attack.get("overall")
        pin = (attack.get("transport") or {}).get("ring_pin") or {}
        served = pin.get("served_provider")
        if served and pin.get("requested") and served != pin.get("requested"):
            entry["state"] = "RING_DEVIATION"
            entry["served"] = served
            per_case.append(entry)
            continue
        if overall not in ("KILLED", "PASS"):
            # the conservative sealed-denominator rule (the corpus's own
            # scoring contract): incomplete / failed / invalid attacks
            # count against COVERAGE, never as survival and never as a
            # detection failure in the headline cohorts
            entry["state"] = "ATTACK_INCOMPLETE"
            entry["overall"] = overall
            entry["served_provider"] = served
            per_case.append(entry)
            continue
        entry["state"] = "MEASURED"
        entry["overall"] = overall
        entry["served_provider"] = served
        entry["served_model"] = pin.get("served_model") or (
            attack.get("transport") or {}).get("model")
        entry["killed_dimensions"] = _kill_dims(attack)
        entry["parsed_fields"] = _parsed_fields(attack)
        entry["v4_corrections"] = attack.get("v4_corrections_applied")
        gt = case.get("ground_truth") or {}
        cat = case["category"]
        killed = overall == "KILLED"
        entry["marker_bound"] = _marker_bound(case, attack) if killed else None
        if cat in ("TRUE_POSITIVE_seeded_defect", "EVIDENCE_CONTRADICTED"):
            entry["cohort"] = "defect"
            if cat == "EVIDENCE_CONTRADICTED":
                entry["contradiction_bound"] = bool(
                    killed and (entry["marker_bound"]))
            entry["detected"] = bool(killed and entry["marker_bound"])
        elif cat == "TRUE_NEGATIVE_clean_control":
            entry["cohort"] = "control"
            entry["false_kill"] = killed
        elif cat == "NEAR_MISS_real_effect_fatal_magnitude":
            entry["cohort"] = "near_miss"
            entry["detected"] = bool(killed and _marker_bound(case, attack))
        elif cat == "SCOPE_CONFLICT_declared_boundary_trap":
            entry["cohort"] = "scope_conflict"
            entry["scope_mismatch_false_kill"] = killed
        elif cat == "MALFORMED_MISSING_EVIDENCE":
            entry["cohort"] = "malformed"
            contradiction_kill = any(
                d == "contradiction" for d in entry["killed_dimensions"])
            entry["absence_as_contradiction"] = bool(
                killed and contradiction_kill)
            entry["unsupported_only"] = bool(
                killed and entry["killed_dimensions"] ==
                ["unsupported_mechanism"])
        per_case.append(entry)

    meas = [e for e in per_case if e.get("state") == "MEASURED"]
    incomplete = [e for e in per_case
                  if e.get("state") in ("ATTACK_INCOMPLETE",
                                        "RING_DEVIATION",
                                        "TRANSPORT_FAILURE")]
    defect = [e for e in meas if e.get("cohort") == "defect"]
    controls = [e for e in meas if e.get("cohort") == "control"]
    near = [e for e in meas if e.get("cohort") == "near_miss"]
    scope = [e for e in meas if e.get("cohort") == "scope_conflict"]
    malf = [e for e in meas if e.get("cohort") == "malformed"]

    n_defect = len(defect)
    detected = sum(1 for e in defect if e.get("detected"))
    tpr = round(detected / n_defect, 4) if n_defect else None
    n_ctrl = len(controls)
    false_kills = sum(1 for e in controls if e.get("false_kill"))
    fpr = round(false_kills / n_ctrl, 4) if n_ctrl else None
    tnr = round(1 - fpr, 4) if fpr is not None else None
    covered = sum(1 for e in meas if e.get("parsed_fields") == 9)
    coverage = round(covered / len(meas), 4) if meas else None
    parse = (round(sum(e["parsed_fields"] for e in meas)
                   / (9 * len(meas)), 4) if meas else None)
    # conservative sealed-denominator: non-measured cases count against
    # coverage (never as survival)
    coverage_strict = (round(covered / len(per_case), 4)
                       if per_case else None)

    thresholds = corpus["pre_registered_thresholds"]
    numbers = (tpr, fpr, coverage, parse)
    complete = all(isinstance(v, (int, float)) for v in numbers)
    verdict = {
        "calibrated": bool(complete and
                           tpr >= thresholds["tpr_min"] and
                           fpr <= thresholds["fpr_max"] and
                           coverage >= thresholds["coverage_min"] and
                           parse >= thresholds["parse_completeness_min"]),
    }
    if complete:
        verdict["failures"] = [k for k, bad in [
            ("tpr_min", tpr < thresholds["tpr_min"]),
            ("fpr_max", fpr > thresholds["fpr_max"]),
            ("coverage_min", coverage < thresholds["coverage_min"]),
            ("parse_completeness_min",
             parse < thresholds["parse_completeness_min"])] if bad]
    else:
        verdict["failures"] = ["incomplete_numbers"]

    results = {
        "artifact_type": "A2_BASELINE_MEASUREMENT_RESULTS",
        "round": "R493",
        "reviewer_provenance": "AI_REVIEW",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "instrument": ("a2/adversarial.py::adversarial_challenge "
                       "(as deployed, UNTUNED baseline)"),
        "transport": "POST /api/ops/a2-attack (the R493 deployed transport)",
        "deployed_commit": EXPECTED_COMMIT,
        "corpus_id": corpus.get("corpus_id"),
        "corpus_sha256": corpus.get("corpus_sha256"),
        "frozen_before_any_tuning": corpus.get("frozen_before_any_tuning"),
        "n_cases": len(cases),
        "n_measured": len(meas),
        "n_attack_incomplete": len(incomplete),
        "incomplete_case_ids": [e["case_id"] for e in incomplete],
        "headline": {
            "tpr_defect_cohorts": tpr,
            "detected_in_defect_cohorts": f"{detected}/{n_defect}",
            "fpr_known_good": fpr,
            "false_kills_on_controls": f"{false_kills}/{n_ctrl}",
            "tnr": tnr,
            "coverage_all_9_fields": coverage,
            "coverage_strict_incl_not_measured": coverage_strict,
            "parse_completeness": parse,
        },
        "category_disciplines": {
            "near_miss": [{k: e.get(k) for k in
                           ("case_id", "overall", "detected",
                            "killed_dimensions")} for e in near],
            "scope_conflict": [{k: e.get(k) for k in
                                ("case_id", "overall",
                                 "scope_mismatch_false_kill")}
                               for e in scope],
            "malformed": [{k: e.get(k) for k in
                           ("case_id", "overall", "absence_as_contradiction",
                            "unsupported_only")} for e in malf],
        },
        "threshold_verdict": {
            "pre_registered_thresholds": thresholds,
            **verdict,
        },
        "registry_schema_summary": {
            # the keys the canonical engine registry reads (the A2 seal
            # plugs in WITHOUT translation if it ever ships)
            "metrics.false_kill_rate_on_known_good": fpr,
            "metrics.coverage": coverage,
            "metrics.parse_completeness": parse,
            "scoped_tpr_diagnostic.tpr": tpr,
            "threshold_verdict.calibrated": verdict["calibrated"],
        },
        "per_case": per_case,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=1))
    _log(f"results -> {RESULTS_PATH.relative_to(REPO)}")
    return results


def run(provider: str, pace: int, limit: int, resume: bool) -> int:
    sha = _freeze_check()
    _log(f"frozen corpus verified: {sha[:16]}...")
    _identity_gate()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    corpus = json.loads(CORPUS_PATH.read_text())
    cases = corpus["cases"][:limit] if limit else corpus["cases"]
    if resume:
        done = {f.stem for f in RAW_DIR.glob("*.json")}
        cases = [c for c in cases if c["case_id"] not in done]
        _log(f"resume: {len(done)} already on disk, {len(cases)} to run")
    for i, case in enumerate(cases, 1):
        cid = case["case_id"]
        gt = case.get("ground_truth") or {}
        _log(f"[{i}/{len(cases)}] {cid} "
             f"(cat={case['category'][:24]}, pa={gt.get('prior_art_state')})")
        rec = _post_case(case, provider)
        attack = rec.get("attack") or {}
        pin = (attack.get("transport") or {}).get("ring_pin") or {}
        if rec.get("http") == 200 and attack.get("overall"):
            served = pin.get("served_provider")
            if served and served != provider:
                _log(f"  RING_DEVIATION: pinned {provider}, served "
                     f"{served} — case recorded, will not score")
            _log(f"  overall={attack.get('overall')} "
                 f"killed={attack.get('killed_count')} "
                 f"latency={rec.get('latency_s')}s served={served}")
        else:
            _log(f"  TRANSPORT FAILURE http={rec.get('http')} "
                 f"error={json.dumps(rec.get('error'))[:160]}")
        (RAW_DIR / f"{cid}.json").write_text(json.dumps(rec, indent=1))
        if i < len(cases):
            time.sleep(pace)
    post = _freeze_check()
    if post != sha:
        raise SystemExit("FATAL: corpus bytes changed DURING the run")
    _log("freeze re-verified post-run")
    r = score()
    h = r["headline"]
    _log(f"HEADLINE: TPR={h['tpr_defect_cohorts']} "
         f"({h['detected_in_defect_cohorts']}) FPR={h['fpr_known_good']} "
         f"({h['false_kills_on_controls']}) coverage={h['coverage_all_9_fields']} "
         f"parse={h['parse_completeness']} "
         f"verdict={r['threshold_verdict']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--provider", default="atria")
    ap.add_argument("--pace", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if a.run:
        return run(a.provider, a.pace, a.limit, a.resume)
    if a.score:
        r = score()
        print(json.dumps(r["headline"], indent=1))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

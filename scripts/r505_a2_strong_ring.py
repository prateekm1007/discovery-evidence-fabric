#!/usr/bin/env python3
"""scripts/r505_a2_strong_ring.py — R505: the v4.2 ATTACKER-COMPUTES
measurement on a FREE STRONG RING — the re-audit's "v4.2 vs strong
ring" item executed on the free path (the adjudicated meaning of the
operator's 'use huggingface and other free sources' directive for the
RING lever).

THE RING LANDSCAPE THIS ROUND (all measured through the deployed
transport's own typing — R505/A2_V42_UNOROUTER and A2_V42_APINEX carry
the failed attempts): unorouter glm-5.3:free AUTH_FAILURE (the Space's
key refused — an owner-gated unblock), apinex free/deepseek-v4.1-flash
CREDIT_EXHAUSTED (the free rung closed), xkiro qwen3.8-max:free
RATE_LIMITED under upstream free-pool congestion then RECOVERED — the
measurement ran on xkiro (the registry's HEALTHY free strong ring).
The engine's capability rotation served ALL cases on
qwen/qwen3.5-plus:free (the spec default qwen3.8-max:free stayed
congested; the plus tier is Qwen's upper-mid class — the record's
served_models map is DERIVED from the per-case records and is the
authoritative composition; the pin is the PROVIDER, model rotation
within it is the transport's documented capability behavior).

THE MEASURED QUESTION: every A2 measurement to date ran on rings that
answer attack calls lazily — the zai gateway (v4.1 TPR 0.3636, v4.2 DEV
TPR 0.2727 with ZERO rule-4.5 firings; the R495 typed conclusion: the
instrument gap is RING-QUALITY-bound) and xkiro qwen3.8-max:free
(TPR 0.2222). The v4.2 standard (rule 4.5, attacker-computes) can only
fire when the attacker ring actually COMPUTES the derivation the record
lacks. The registry's free STRONG rungs are unorouter glm-5.3:free
("the same GLM-5.3 flagship class the zai env contract serves"), xkiro
qwen3.8-max:free ("the MAX tier is Qwen's flagship class"), and apinex
free/deepseek-v4.1-flash — none had EVER been measured for A2. This
driver measures the DEPLOYED v4.2 gauntlet (a2_adversarial_gauntlet/
2.1.0, rule 4.5 live at d7520b9b) on the frozen DEV corpus, PINNED to
one provider ring (--provider), through the production
/api/ops/a2-attack transport.

DISCIPLINE (the R493/R494 measurement lineage, preserved verbatim):
  - the FROZEN corpus is asserted before and after (the R492 canonical
    reconstruction sha); no corpus byte is modified, no case altered,
    no false kill relabeled
  - the identity gate (R504 records-past-deploy shape): the deployed
    engine_commit must equal d7520b9b — the commit that ships gauntlet
    2.1.0 + the a2-attack transport — AND the local HEAD must not
    diverge from it on any instrument file (records-past-deploy by
    design; the diff list is recorded)
  - the ring pin: every case declares require_provider=<the pinned
    ring> (fail-closed; a case served elsewhere is RING_DEVIATION, never
    scores). Free-pool congestion (the registry's measured 403 'model
    busy' class) types per case and resumes via --resume; the phase
    early-stop (--abort-after-failures N, the R497 quota-stewardship
    pattern) stops a phase when the pinned ring is measurably down
  - SEQUENTIAL with pacing (ring-friendly; the R488 lesson)
  - NO threshold invented: the corpus's pre-registered bars (the R412
    sealed bars REUSED verbatim, Art. XXVII)
  - this driver claims nothing: the numbers are measured, the verdict
    derived against the bars, the calibration gate stays the authority
  - ZERO PatentBear debits (the A2 gauntlet is a no-retrieval
    instrument; no metered provider is constructed)

Commands:
  python3 scripts/r505_a2_strong_ring.py --run [--resume] [--pace 30]
      [--limit N] [--provider xkiro] [--out A2_V42_XKIRO]
      [--abort-after-failures N]
  python3 scripts/r505_a2_strong_ring.py --score [--out A2_V42_XKIRO]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]

CORPUS_PATH = REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json"
FREEZE_PATH = REPO / "R492" / "A2_DEV_CORPUS" / "FREEZE.json"
OUT_DIR = REPO / "R505" / "A2_V42_UNOROUTER"
RAW_DIR = OUT_DIR / "RAW"
RESULTS_PATH = OUT_DIR / "MEASUREMENT_RESULTS.json"
MEASUREMENT_PATH = OUT_DIR / "MEASUREMENT.json"

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
# the R504-DEPLOYED commit that ships gauntlet 2.1.0 (v4.2 rule 4.5) +
# the /api/ops/a2-attack transport; local HEAD is records-past-deploy
EXPECTED_DEPLOYED = "d7520b9bc5d7f26a2ab40b28367501e916634513"
INSTRUMENT_PATH_PREFIXES = ("discovery_fabric/", "toscanini/")
PER_CASE_TIMEOUT = 500     # gauntlet llm_chat 420s + server overhead
DIMENSIONS = ["unsupported_mechanism", "weak_transfer",
              "obvious_combination", "prior_art", "contradiction",
              "boundary_failure", "engineering_infeasibility",
              "regulatory_incompatibility"]
RULE45_MARKER = "burden_of_proof:attacker_computed_derivation"


def _log(msg: str) -> None:
    print(f"[r505-a2-strong-ring] {msg}", flush=True)


def _freeze_check() -> str:
    """The R492 freeze hash is the CANONICAL reconstruction sha — the
    same computation the R492 freeze tests pin (preserved verbatim from
    the R493 driver)."""
    frozen = json.loads(FREEZE_PATH.read_text()).get("corpus_sha256")
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    body = {k: v for k, v in corpus.items() if k != "corpus_sha256"}
    blob = json.dumps(body, indent=2, ensure_ascii=False) + "\n"
    actual = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    if not frozen or actual != frozen:
        raise SystemExit(
            f"FATAL: corpus freeze mismatch: FREEZE says {frozen}, "
            f"reconstruction hashes {actual} — the corpus moved (Art. LIX)")
    return actual


def _identity_gate() -> Dict[str, Any]:
    """The R504 records-past-deploy shape: deployed == the commit that
    ships the instrument, and local HEAD diverges from it on RECORDS
    ONLY (no instrument file) — the divergence list is recorded."""
    req = urllib.request.Request(f"{BASE}/api/version", method="GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        v = json.loads(r.read().decode())
    deployed = v.get("engine_commit", "")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                          capture_output=True, text=True).stdout.strip()
    diff = subprocess.run(
        ["git", "diff", "--name-only", EXPECTED_DEPLOYED, head],
        cwd=str(REPO), capture_output=True, text=True).stdout.split()
    instrument_files = [f for f in diff
                        if f.startswith(INSTRUMENT_PATH_PREFIXES)]
    ok = (deployed == EXPECTED_DEPLOYED and not instrument_files)
    _log(f"identity gate: deployed={deployed[:12]} "
         f"expected={EXPECTED_DEPLOYED[:12]} head={head[:12]} "
         f"diff_files={len(diff)} instrument_in_diff="
         f"{len(instrument_files)} -> {'OK' if ok else 'MISMATCH'}")
    if not ok:
        raise SystemExit(
            "FATAL: identity gate failed — the measurement must run on "
            "the deployed v4.2 instrument (deployed commit or "
            "instrument-parity violated)")
    return {"deployed_commit": deployed, "local_head": head,
            "records_past_deploy_files": sorted(diff),
            "instrument_files_in_diff": instrument_files,
            "constitution_version": v.get("constitution_version")}


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


def _rule45_firings(record: Dict[str, Any]) -> int:
    return sum(1 for c in (record.get("v4_corrections_applied") or [])
               if c == RULE45_MARKER)


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
            "latency_s": rec.get("latency_s")}
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
            # scoring contract): incomplete/failed/invalid attacks count
            # against COVERAGE, never as survival and never as a
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
        entry["v4_corrections_applied"] = attack.get("v4_corrections_applied")
        entry["rule45_firings"] = _rule45_firings(attack)
        gt = case.get("ground_truth") or {}
        cat = case["category"]
        killed = overall == "KILLED"
        entry["marker_bound"] = _marker_bound(case, attack) if killed else None
        if cat in ("TRUE_POSITIVE_seeded_defect", "EVIDENCE_CONTRADICTED"):
            entry["cohort"] = "defect"
            if cat == "EVIDENCE_CONTRADICTED":
                entry["contradiction_bound"] = bool(
                    killed and "contradiction" in entry["killed_dimensions"])
            entry["detected"] = bool(killed and (entry["marker_bound"]))
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
    coverage_strict = (round(covered / len(per_case), 4)
                       if per_case else None)
    rule45_total = sum(e.get("rule45_firings", 0) for e in meas)
    rule45_cases = [e["case_id"] for e in meas if e.get("rule45_firings")]

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

    served_providers = Counter(e.get("served_provider")
                               for e in meas if e.get("served_provider"))
    served_models = Counter(e.get("served_model")
                            for e in meas if e.get("served_model"))
    # the pin is DERIVED from the measured records (the R491
    # _ring_summary pattern: the measured ring is never asserted) —
    # the dominant served provider IS the ring this record binds
    measured_pin = (served_providers.most_common(1)[0][0]
                    if served_providers else None)

    results = {
        "artifact_type": "A2_V42_RING_MEASUREMENT_RESULTS",
        "round": "R505",
        "reviewer_provenance": "AI_REVIEW",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "instrument": ("a2/adversarial.py::adversarial_challenge "
                       "(a2_adversarial_gauntlet/2.1.0 — the v4.2 "
                       "ATTACKER-COMPUTES standard, rule 4.5 live), as "
                       "deployed at " + EXPECTED_DEPLOYED[:12]),
        "transport": ("POST /api/ops/a2-attack (the R493 deployed "
                      "transport), require_provider pinned per the ring "
                      "block (derived from the per-case records, never "
                      "asserted) — the first A2 measurement on a "
                      "strong-class FREE ring (every prior A2 run "
                      "measured the lazy zai gateway)"),
        "deployed_commit": EXPECTED_DEPLOYED,
        "corpus_id": corpus.get("corpus_id"),
        "corpus_sha256": corpus.get("corpus_sha256"),
        "frozen_before_any_tuning": corpus.get("frozen_before_any_tuning"),
        "n_cases": len(cases),
        "n_measured": len(meas),
        "n_attack_incomplete": len(incomplete),
        "incomplete_case_ids": [e["case_id"] for e in incomplete],
        "ring": {
            "pin": measured_pin,
            "pin_level": "PROVIDER (require_provider; model rotation "
                         "within the pinned provider is the transport's "
                         "documented capability behavior)",
            "served_providers": dict(served_providers),
            "served_models": dict(served_models),
            "model_mix_disclosure": (
                "the served_models map IS the measured ring composition — "
                "a mixed-model run is disclosed as measured, never "
                "presented as single-model; every per-case record carries "
                "its own served_model"),
            "note": ("calibration is (rules x ring) — the R488 measured "
                     "lesson; this record binds the v4.2 rules to THIS "
                     "ring's measurement"),
        },
        "rule45_attacker_computes": {
            "total_firings": rule45_total,
            "cases_with_firings": rule45_cases,
            "the_v42_question": ("the R495 zai-ring DEV run measured "
                                 "ZERO firings (lazy responses — the "
                                 "typed RING-QUALITY blocker); does a "
                                 "flagship-class free ring COMPUTE the "
                                 "derivations and fire rule 4.5?"),
        },
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


def run(provider: str, pace: int, limit: int, resume: bool,
        out_name: str = "A2_V42_UNOROUTER",
        abort_after_failures: int = 0) -> int:
    global OUT_DIR, RAW_DIR, RESULTS_PATH
    OUT_DIR = REPO / "R505" / out_name
    RAW_DIR = OUT_DIR / "RAW"
    RESULTS_PATH = OUT_DIR / "MEASUREMENT_RESULTS.json"
    sha = _freeze_check()
    _log(f"frozen corpus verified: {sha[:16]}...")
    identity = _identity_gate()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    corpus = json.loads(CORPUS_PATH.read_text())
    cases = corpus["cases"][:limit] if limit else corpus["cases"]
    if resume:
        done = set()
        for f in RAW_DIR.glob("*.json"):
            # Resume boundary (the anti-shopping rule): a case is DONE
            # when a VERDICT-CLASS attempt exists on disk — http 200
            # with overall in (KILLED, PASS, ADVERSARIAL_INVALID,
            # EVALUATION_FAILED). EVALUATION_FAILED means a dimension
            # was ADVERSARIAL_INVALID (adversarial.py:576-579): a REAL
            # evaluator answer with a parse defect — a MEASURED attempt,
            # counted against coverage (the R493 contract's conservative
            # denominator), NEVER retried (retrying it would re-roll
            # parse failures until they pass — measurement-shopping).
            # EVALUATOR_CALL_FAILED / transport failures produced NO
            # verdict — they retry honestly (Art. XXI.3/LXI).
            try:
                rec = json.loads(f.read_text())
            except Exception:  # noqa: BLE001
                continue
            if rec.get("http") == 200 and \
                    (rec.get("attack") or {}).get("overall") in \
                    ("KILLED", "PASS", "ADVERSARIAL_INVALID",
                     "EVALUATION_FAILED"):
                done.add(f.stem)
        cases = [c for c in cases if c["case_id"] not in done]
        _log(f"resume: {len(done)} verdict-class on disk, "
             f"{len(cases)} to (re)run")
    (OUT_DIR / "IDENTITY.json").write_text(json.dumps(identity, indent=1))
    consecutive_failures = 0
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
                 f"rule45={_rule45_firings(attack)} "
                 f"latency={rec.get('latency_s')}s served={served}")
        else:
            _log(f"  TRANSPORT FAILURE http={rec.get('http')} "
                 f"error={json.dumps(rec.get('error'))[:160]}")
        # PHASE EARLY-STOP (the R497 quota-stewardship pattern): when the
        # pinned ring is measurably down (consecutive typed transport
        # failures), running the remaining cases NOW only burns wall-clock
        # against a congested free pool — the phase aborts, the measured
        # cases stay on disk, and --resume continues when the pool
        # recovers. Never a scoring change: unmeasured cases were already
        # going to count against coverage, not survival. NOTE: the
        # verdict classes are (KILLED, PASS, ADVERSARIAL_INVALID) — a 200
        # whose overall is EVALUATOR_CALL_FAILED produced NO verdict (the
        # evaluator call itself failed) and counts as a FAILURE here.
        (RAW_DIR / f"{cid}.json").write_text(json.dumps(rec, indent=1))
        got_verdict = (rec.get("http") == 200 and
                       attack.get("overall") in
                       ("KILLED", "PASS", "ADVERSARIAL_INVALID"))
        if got_verdict:
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if abort_after_failures and \
                    consecutive_failures >= abort_after_failures:
                _log(f"  PHASE EARLY-STOP: {consecutive_failures} "
                     f"consecutive transport failures — the pinned ring "
                     f"is measurably down; resumable via --resume "
                     f"(quota/time stewardship, the R497 pattern)")
                break
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
         f"rule45={r['rule45_attacker_computes']['total_firings']} "
         f"verdict={r['threshold_verdict']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--provider", default="xkiro",
                    help="the pinned strong ring (fail-closed pin)")
    ap.add_argument("--pace", type=int, default=30)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="A2_V42_XKIRO")
    ap.add_argument("--abort-after-failures", type=int, default=0,
                    help="abort the phase after N consecutive transport "
                         "failures (the pinned ring is measurably down; "
                         "resumable — the R497 quota-stewardship pattern)")
    a = ap.parse_args()
    if a.run:
        return run(a.provider, a.pace, a.limit, a.resume, a.out,
                   a.abort_after_failures)
    if a.score:
        global OUT_DIR, RAW_DIR, RESULTS_PATH
        OUT_DIR = REPO / "R505" / a.out
        RAW_DIR = OUT_DIR / "RAW"
        RESULTS_PATH = OUT_DIR / "MEASUREMENT_RESULTS.json"
        r = score()
        print(json.dumps(r["headline"], indent=1))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

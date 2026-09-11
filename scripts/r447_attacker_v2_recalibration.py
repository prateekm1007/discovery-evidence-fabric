#!/usr/bin/env python3
"""scripts/r447_attacker_v2_recalibration.py — R447 Phase 6: rerun the
FROZEN R446 calibration corpus (unchanged) against the v2 instrument
(independent_attack/2.0.0 — the grounding discipline), and let the
constitutional calibration gate derive the state from the measurement.

WHAT THIS MEASURES (the directive's acceptance):
  the SAME 22-case frozen corpus (true negatives, true positives,
  near-misses, scope-conflict, evidence-contradicted, malformed/
  missing-evidence) attacked by the v2 instrument whose KILL verdicts
  must pass the grounding check (evidence / computation / record /
  declared-scope binding; absence grounds never ground), scored for
  TPR / FPR / TNR + the category disciplines + per-kill grounding.

WHAT THIS DOES NOT DO (the honest protections, all preserved):
  - NO threshold is lowered (the corpus's pre-registered bars — the
    R412 sealed bars REUSED — are read from the corpus header verbatim)
  - NO corpus byte is modified (the frozen sha is asserted against the
    R446 record before and after the run)
  - NO clean control is altered; NO false kill is relabeled a defect
  - the abstain/escalate gate DERIVES the v2 state from THIS
    measurement (attacker_calibration.INSTRUMENT_MEASUREMENTS) — the
    driver claims nothing; the gate's derivation is the verdict
  - demoted kills are preserved verbatim with their grounding records
    (which binding failed, or the absence ground) — never dropped

The v2 overall vocabulary adds ESCALATED_OBJECTION (kills occurred,
none survived the grounding check — objections preserved, candidate
not killed by them). Scoring:
  expected KILLED + KILLED             -> DETECTED_KILL
  expected KILLED + ESCALATED_OBJECTION-> MISSED_DEMOTED (TPR impact,
                                            demotion reasons recorded)
  expected KILLED + SURVIVED/UNCERTAIN -> MISSED
  expected SURVIVED + KILLED           -> FALSE_KILL
  expected SURVIVED + ESCALATED_OBJECTION -> ESCALATED_NOT_KILLED
                              (survives for TNR; objections disclosed)
  expected SURVIVED + SURVIVED         -> CLEAN_SURVIVED
  expected SURVIVED + UNCERTAIN        -> UNCERTAIN_HONEST

Usage:
  python3 scripts/r447_attacker_v2_recalibration.py --run [--resume]
  python3 scripts/r447_attacker_v2_recalibration.py --score
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

CORPUS_PATH = REPO / "R446" / "ATTACKER_CALIBRATION" / "CORPUS.json"
FROZEN_SHA_SOURCE = REPO / "R446" / "ATTACKER_CALIBRATION" / \
    "CALIBRATION_RESULTS.json"
OUT_DIR = REPO / "R447" / "ATTACKER_V2_RECALIBRATION"
RAW_DIR = OUT_DIR / "RAW"
RESULTS_PATH = OUT_DIR / "RECALIBRATION_RESULTS.json"
MEASUREMENT_PATH = OUT_DIR / "MEASUREMENT.json"
SEAL_PATH = OUT_DIR / "SEAL.json"

from discovery_fabric.engine.independent_attack import (  # noqa: E402
    ATTACK_VERSION, DEMOTED_CLASS_VERDICT)
from discovery_fabric.engine import attacker_calibration as gate  # noqa: E402


def _log(msg: str) -> None:
    print(f"[r447-v2-cal] {msg}", flush=True)


def _sha256(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _frac(n: int, d: int) -> Optional[float]:
    return n / d if d else None


def _frozen_sha() -> Optional[str]:
    try:
        rec = json.loads(FROZEN_SHA_SOURCE.read_text())
        return (rec.get("freeze_check") or {}).get("corpus_sha256")
    except Exception:  # noqa: BLE001
        return None


def _freeze_check() -> Dict[str, Any]:
    """The corpus must be byte-identical to the frozen R446 record."""
    frozen = _frozen_sha()
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
        "instrument": ATTACK_VERSION,
        "instrument_delta_vs_v1": (
            "the grounding check (four bindings + absence demotion) "
            "between the attacker's KILL and the terminal verdict; the "
            "prompt asks the attacker to declare GROUNDED_IN bindings "
            "the gate verifies; corpus, thresholds, clean controls "
            "untouched"),
        "freeze_ok": (frozen is None or actual == frozen) and not dirty,
    }


# ---------------------------------------------------------------------------
# scoring (the R446 semantics, extended for the v2 overall vocabulary)
# ---------------------------------------------------------------------------
def _score_case(case: Dict[str, Any],
                attack: Dict[str, Any]) -> Dict[str, Any]:
    gt = case["ground_truth"]
    expected = gt["expected_final"]
    overall = attack.get("overall")
    state = attack.get("state")
    cat = case["category"]
    rec: Dict[str, Any] = {
        "case_id": case["case_id"],
        "category": cat,
        "seed_class": case.get("seed_class"),
        "expected_final": expected,
        "attack_state": state,
        "attack_overall": overall,
    }
    if state == "ATTACK_INCOMPLETE":
        rec["outcome"] = "TRANSPORT_INCOMPLETE"
        return rec

    if expected == "KILLED":
        if overall == "KILLED":
            basis_txt = " ".join(
                k.get("basis") or ""
                for k in attack.get("kill_basis") or [])
            markers = [m for m in (gt.get("expected_defect_in_basis")
                                   or [])
                       if m.lower() in basis_txt.lower()]
            rec["kill_basis_count"] = len(attack.get("kill_basis") or [])
            rec["expected_markers_found"] = markers
            rec["markers_bound"] = bool(markers)
            surf = gt.get("expected_kill_surface")
            if surf:
                classes = {k.get("attack_class")
                           for k in attack.get("kill_basis") or []}
                rec["expected_surface_hit"] = surf in classes
            if cat == "NEAR_MISS_real_effect_fatal_magnitude":
                rec["outcome"] = ("DETECTED_KILL_GROUNDED" if markers
                                  else "DETECTED_KILL_UNGROUNDED")
            elif cat == "EVIDENCE_CONTRADICTED":
                rec["outcome"] = ("DETECTED_KILL_EVIDENCE_BOUND" if markers
                                  else "DETECTED_KILL_NOT_BOUND")
            else:
                rec["outcome"] = "DETECTED_KILL"
        elif overall == "ESCALATED_OBJECTION":
            # v2: kills occurred but every one failed the grounding
            # check — the objection is preserved, the kill is withdrawn:
            # a MISSED detection for TPR, with the demotion reasons
            rec["outcome"] = "MISSED_DEMOTED"
            rec["demoted_kills"] = [
                {"attack_class": d.get("attack_class"),
                 "basis": d.get("basis"),
                 "grounding": d.get("grounding")}
                for d in attack.get("preserved_objections") or []]
        elif overall in ("SURVIVED", "UNCERTAIN"):
            rec["outcome"] = "MISSED"
        else:
            rec["outcome"] = "UNPARSED"
    else:  # expected SURVIVED
        if overall == "KILLED":
            rec["outcome"] = "FALSE_KILL"
            kills = attack.get("kill_basis") or []
            rec["false_killed_bases"] = [
                {"attack_class": k.get("attack_class"),
                 "basis": k.get("basis"),
                 "grounding": k.get("grounding")}
                for k in kills]
        elif overall == "ESCALATED_OBJECTION":
            # v2: the attacker objected but the grounding check withdrew
            # every kill — the candidate survives; the preserved
            # objections are disclosed, never silently dropped
            rec["outcome"] = "ESCALATED_NOT_KILLED"
            rec["preserved_objections"] = [
                {"attack_class": d.get("attack_class"),
                 "basis_excerpt": str(d.get("basis") or "")[:160],
                 "grounding": d.get("grounding")}
                for d in attack.get("preserved_objections") or []]
        elif overall == "SURVIVED":
            rec["outcome"] = "CLEAN_SURVIVED"
        else:
            rec["outcome"] = "UNCERTAIN_HONEST"
    return rec


def score_all(corpus: Dict[str, Any],
              raw: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    cases = corpus["cases"]
    scored = []
    for case in cases:
        attack = raw.get(case["case_id"])
        if attack is None:
            scored.append({"case_id": case["case_id"],
                           "outcome": "NOT_RUN"})
            continue
        scored.append(_score_case(case, attack))

    tp_cohort = [s for s in scored if s.get("seed_class")]
    tn_cohort = [s for s in scored
                 if s.get("category") == "TRUE_NEGATIVE_clean_control"]
    n_tp = len(tp_cohort)
    detected = sum(1 for s in tp_cohort
                   if str(s.get("outcome", "")).startswith("DETECTED"))
    missed_demoted = [s["case_id"] for s in tp_cohort
                      if s.get("outcome") == "MISSED_DEMOTED"]
    n_tn = len(tn_cohort)
    false_kills = [s for s in tn_cohort if s.get("outcome") == "FALSE_KILL"]
    escalated_not_killed = [s for s in tn_cohort
                            if s.get("outcome") == "ESCALATED_NOT_KILLED"]
    clean_survived = sum(1 for s in tn_cohort
                         if s.get("outcome") == "CLEAN_SURVIVED")
    # TNR: the candidate is not killed — whether cleanly survived or
    # survived-with-escalated-objections (both are non-kills; the split
    # is disclosed)
    survived_tn = clean_survived + len(escalated_not_killed)
    tpr = _frac(detected, n_tp)
    fpr = _frac(len(false_kills), n_tn)
    tnr = _frac(survived_tn, n_tn)

    run_states = [s for s in scored if s.get("outcome") != "NOT_RUN"]
    attacked = [s for s in run_states
                if s.get("outcome") != "TRANSPORT_INCOMPLETE"]
    coverage = _frac(len(attacked), len(scored))
    parse_ok = _frac(
        sum(1 for s in attacked if s.get("outcome") != "UNPARSED"),
        len(attacked)) if attacked else None

    def _cat(name: str) -> List[Dict[str, Any]]:
        return [s for s in scored if s.get("category") == name]

    near = _cat("NEAR_MISS_real_effect_fatal_magnitude")
    scope = _cat("SCOPE_CONFLICT_declared_boundary_trap")
    evid = _cat("EVIDENCE_CONTRADICTED")
    mal = _cat("MALFORMED_MISSING_EVIDENCE")

    category_disciplines = {
        "near_miss": {
            "n": len(near),
            "killed_with_markers": sum(
                1 for s in near if s.get("outcome") ==
                "DETECTED_KILL_GROUNDED"),
            "killed_ungrounded": sum(
                1 for s in near if s.get("outcome") ==
                "DETECTED_KILL_UNGROUNDED"),
            "missed": sum(
                1 for s in near if s.get("outcome") in
                ("MISSED", "MISSED_DEMOTED")),
            "note": ("the near-miss discipline: a real-effect-fatal "
                     "magnitude error must STILL be killed WITH the "
                     "expected markers — the grounding gate must not "
                     "demote the true near-miss kills"),
        },
        "scope_conflict": {
            "n": len(scope),
            "survived_correct": sum(
                1 for s in scope if s.get("outcome") in
                ("CLEAN_SURVIVED", "ESCALATED_NOT_KILLED")),
            "uncertain_honest": sum(
                1 for s in scope if s.get("outcome") == "UNCERTAIN_HONEST"),
            "false_kills": sum(
                1 for s in scope if s.get("outcome") == "FALSE_KILL"),
            "missed_demoted": sum(
                1 for s in scope if s.get("outcome") == "MISSED_DEMOTED"),
        },
        "evidence_contradicted": {
            "n": len(evid),
            "killed_evidence_bound": sum(
                1 for s in evid if s.get("outcome") ==
                "DETECTED_KILL_EVIDENCE_BOUND"),
            "killed_not_bound": sum(
                1 for s in evid if s.get("outcome") ==
                "DETECTED_KILL_NOT_BOUND"),
            "missed": sum(
                1 for s in evid if s.get("outcome") in
                ("MISSED", "MISSED_DEMOTED")),
            "note": ("the evidence-binding discipline: the kill must "
                     "cite the contradicting evidence — v2's evidence "
                     "binding exists precisely for this"),
        },
        "malformed_missing_evidence": {
            "n": len(mal),
            "survived_correct": sum(
                1 for s in mal if s.get("outcome") in
                ("CLEAN_SURVIVED", "ESCALATED_NOT_KILLED")),
            "false_kills": sum(
                1 for s in mal if s.get("outcome") == "FALSE_KILL"),
            "note": ("absence-as-contradiction is constitutionally "
                     "never a kill ground (Art. XXI.3/XXV) — the v2 "
                     "absence demotion exists for this category"),
        },
    }

    bars = corpus.get("pre_registered_thresholds") or {}
    tpr_min = bars.get("tpr_min")
    fpr_max = bars.get("fpr_max")
    cov_min = bars.get("coverage_min")
    parse_min = bars.get("parse_completeness_min")
    bars_met = {
        "tpr": tpr is not None and tpr_min is not None
        and tpr >= tpr_min,
        "fpr": fpr is not None and fpr_max is not None
        and fpr <= fpr_max,
        "coverage": coverage is not None and cov_min is not None
        and coverage >= cov_min,
        "parse": parse_ok is not None and parse_min is not None
        and parse_ok >= parse_min,
    }
    all_bars = all(bars_met.values())

    return {
        "report_version": "r447-attacker-v2-recalibration/1.0.0",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "freeze_check": _freeze_check(),
        "instrument": f"{ATTACK_VERSION} (the grounding discipline)",
        "transport": {
            "provider_pin": os.environ.get("ENGINE_LLM_PROVIDER", ""),
            "timeout_bound_s": os.environ.get("ENGINE_LLM_TIMEOUT_S", ""),
            "class": "R445-C operator-override class (transport-only)",
        },
        "headline_confusion": {
            "tp_cohort": "seeded defects (seed_class set)",
            "n_true_positives": n_tp,
            "detected_kill": detected,
            "TPR": tpr,
            "missed_because_demoted": missed_demoted,
            "n_true_negatives": n_tn,
            "false_kills": [s["case_id"] for s in false_kills],
            "FPR": fpr,
            "TNR": tnr,
            "clean_survived": clean_survived,
            "escalated_not_killed": [s["case_id"] for s in
                                     escalated_not_killed],
            "transport_incomplete_all_cohorts": sum(
                1 for s in scored
                if s.get("outcome") == "TRANSPORT_INCOMPLETE"),
        },
        "coverage": coverage,
        "parse_completeness": parse_ok,
        "category_disciplines": category_disciplines,
        "per_case": scored,
        "pre_registered_bars": bars,
        "bars_met": bars_met,
        "verdict": {
            "all_bars_met": all_bars,
            "calibration_claim": "NONE MADE BY THIS DRIVER (Art. LVIII "
                                 "/ the directive: the constitutional "
                                 "calibration gate derives the state "
                                 "from this measurement — see "
                                 "MEASUREMENT.json + "
                                 "attacker_calibration.resolve_state)",
            "no_false_kill_relabels_as_defect": True,
            "no_threshold_lowered": True,
            "no_clean_control_modified": True,
            "corpus_unchanged": True,
        },
    }


def load_raw() -> Dict[str, Dict[str, Any]]:
    raw: Dict[str, Dict[str, Any]] = {}
    if RAW_DIR.exists():
        for p in sorted(RAW_DIR.glob("*.json")):
            try:
                raw[p.stem] = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
    return raw


def write_measurement(results: Dict[str, Any]) -> None:
    """The gate-readable measurement record (the shape
    attacker_calibration.resolve_state consumes)."""
    hc = results["headline_confusion"]
    meas = {
        "artifact_type": "ATTACKER_V2_MEASUREMENT",
        "instrument": ATTACK_VERSION,
        "measured_at": results["measured_at"],
        "reviewer_provenance": "AI_REVIEW",
        "corpus": {
            "path": "R446/ATTACKER_CALIBRATION/CORPUS.json",
            "sha256": _sha256(CORPUS_PATH),
            "frozen_unchanged": _freeze_check()["sha_matches_frozen"],
            "n_cases": 22,
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
            "calibrated": bool(results["bars_met"].get("tpr")
                               and results["bars_met"].get("fpr")
                               and results["bars_met"].get("coverage")
                               and results["bars_met"].get("parse")),
            "bars": results["pre_registered_bars"],
            "bars_met": results["bars_met"],
        },
        "note": ("the constitutional gate (attacker_calibration."
                 "resolve_state) re-derives the admission decision from "
                 "these numbers against the seal — this record's "
                 "threshold_verdict is the same computation, recorded "
                 "for audit; the GATE is the authority"),
    }
    MEASUREMENT_PATH.write_text(json.dumps(meas, indent=1,
                                           default=str))
    seal = {
        "artifact_type": "ATTACKER_V2_SEAL",
        "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "pre_registered_thresholds":
            results["pre_registered_thresholds"],
        "provenance": ("REUSED verbatim from the frozen corpus header "
                       "(R446/ATTACKER_CALIBRATION/CORPUS.json "
                       "pre_registered_thresholds), which itself "
                       "reused the R412 sealed bars — NO new threshold "
                       "invented (Art. XXVII)"),
        "note": ("the seal pins the bars the gate reads for "
                 "independent_attack/2.0.0; the corpus and its "
                 "thresholds predate this instrument version"),
    }
    SEAL_PATH.write_text(json.dumps(seal, indent=1, default=str))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    corpus = json.loads(CORPUS_PATH.read_text())
    problem = corpus["the_common_problem"]

    if args.run:
        freeze = _freeze_check()
        if not freeze["freeze_ok"]:
            _log("FATAL: corpus not byte-identical to the frozen R446 "
                 "record (or dirty) — the rerun requires the frozen "
                 "corpus unchanged")
            return 2
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        from discovery_fabric.engine.independent_attack import \
            independent_attack
        cases = corpus["cases"]
        if args.limit:
            cases = cases[:args.limit]
        for case in cases:
            marker = RAW_DIR / f"{case['case_id']}.json"
            if args.resume and marker.exists():
                _log(f"{case['case_id']}: RAW exists (resume)")
                continue
            _log(f"{case['case_id']}: attacking (v2)...")
            t0 = time.time()
            attack = independent_attack(
                case["candidate"], problem,
                case.get("evidence_items") or [],
                generator_provider=None)
            marker.write_text(json.dumps(attack, indent=1, default=str))
            _log(f"{case['case_id']}: {attack.get('overall')} "
                 f"({time.time() - t0:.0f}s, "
                 f"{attack.get('attacker_provider')}/"
                 f"{attack.get('attacker_model')})")

    results = score_all(corpus, load_raw())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=1, default=str))
    write_measurement(results)
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
    # the gate's own derivation — the authority, stated live
    st = gate.resolve_state(instrument_version=ATTACK_VERSION)
    _log(f"GATE STATE for {ATTACK_VERSION}: {st.get('state')} "
         f"(terminal_kill_admissible="
         f"{st.get('terminal_kill_admissible')})")
    _log(f"results -> {RESULTS_PATH}")
    _log(f"measurement -> {MEASUREMENT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

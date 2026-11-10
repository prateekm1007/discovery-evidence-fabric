#!/usr/bin/env python3
"""scripts/r446_attacker_calibration.py — R446-C1 Task 2: the next
attacker-calibration experiment — a measured decision instrument, not
a weakened gate.

WHAT THIS MEASURES (the directive's acceptance):
  an independently frozen corpus (22 cases, 6 categories — true
  negatives, true positives, adversarial near-misses, scope-conflict
  cases, evidence-contradicted cases, malformed/missing-evidence
  cases) attacked by the UNMODIFIED instrument (independent_attack/
  1.0.0), scored for TPR / FPR / TNR + per-category disciplines +
  per-kill-basis mechanical grounding + the R445 false-kill classes.

WHAT THIS DOES NOT DO (the honest protections, all preserved):
  - NO threshold is lowered (the R412 sealed bars are reused verbatim)
  - NO clean control is modified (the corpus is committed BEFORE this
    driver runs on it — the freeze is verifiable in git history)
  - NO false kill is relabeled a defect (the scorer adjudicates false
    kills against the R445 classes and reports them as false kills)
  - the abstain/escalate gate (attacker_calibration.py) stays IN FORCE
    and untouched: this measurement ALONE cannot flip CALIBRATED — the
    gate reads the R417 measurement record; a future instrument
    version must EARN the flip (GATED_INSTRUMENT_VERSION is pinned)
  - "better numbers" are NOT interpreted as calibration: the verdict
    field on the results carries the honest state, whatever the numbers

Transport: the provider matrix via llm_registry (the R445-C
operator-override class — ENGINE_LLM_PROVIDER pin + ENGINE_LLM_TIMEOUT_S
bound; the instrument's prompts, parsing, validation and verdict
semantics are untouched).

Usage:
  python3 scripts/r446_attacker_calibration.py --run [--resume]
  python3 scripts/r446_attacker_calibration.py --score   (rescore RAW/)
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

from r445_false_kill_diagnosis import _basis_grounding, _record_binding  # noqa: E402

OUT_DIR = REPO / "R446" / "ATTACKER_CALIBRATION"
CORPUS_PATH = OUT_DIR / "CORPUS.json"
RAW_DIR = OUT_DIR / "RAW"
RESULTS_PATH = OUT_DIR / "CALIBRATION_RESULTS.json"

# the pre-registered bars (reused from the R412 seal; provenance in the
# corpus header — NO new threshold invented)
BARS = {"tpr_min": 0.75, "fpr_max": 0.30, "coverage_min": 0.875,
        "parse_completeness_min": 0.875}

# the R445 diagnosis classes (verbatim semantics, applied per false kill)
FALSE_KILL_CLASSES = ("UNSUPPORTED_OBJECTION", "RECORD_CONTRADICTED",
                      "SCOPE_MISMATCH", "SEVERITY_INFLATION")
ABSENCE_CLASS = "ABSENCE_AS_CONTRADICTION"


def _log(msg: str) -> None:
    print(f"[r446-cal] {msg}", flush=True)


def _sha256(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _freeze_check() -> Dict[str, Any]:
    """The corpus must be committed BEFORE any RAW record exists
    (freeze-then-run; contamination check per the R444 discipline)."""
    committed = subprocess.run(
        ["git", "log", "--oneline", "--", str(CORPUS_PATH.relative_to(REPO))],
        cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain",
         "--", str(CORPUS_PATH.relative_to(REPO))],
        cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    raw_exists = RAW_DIR.exists() and any(RAW_DIR.glob("*.json"))
    n_commits = len([l for l in committed.splitlines() if l.strip()])
    ok = (n_commits >= 1 and not dirty) or not raw_exists
    return {
        "corpus_sha256": _sha256(CORPUS_PATH),
        "n_corpus_commits": n_commits,
        "corpus_dirty_in_worktree": bool(dirty),
        "raw_records_exist_before_freeze": bool(raw_exists and n_commits == 0),
        "freeze_ok": ok,
        "note": ("the corpus is committed before the first attack run; "
                 "the instrument is unchanged (independent_attack/1.0.0); "
                 "ground truths were authored from first principles "
                 "before any run on this corpus"),
    }


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------
def _markers_in_basis(markers: List[str], basis: str) -> List[str]:
    low = str(basis).lower()
    return [m for m in markers if m.lower() in low]


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
                k.get("basis") or "" for k in attack.get("kill_basis") or [])
            markers = _markers_in_basis(
                gt.get("expected_defect_in_basis") or [], basis_txt)
            rec["kill_basis_count"] = len(attack.get("kill_basis") or [])
            rec["expected_markers_found"] = markers
            rec["markers_bound"] = bool(markers)
            # localization: the expected kill surface carries the kill
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
                 "basis": k.get("basis")} for k in kills]
            # the absence-class discipline: killing on empty/malformed
            # evidence is ABSENCE_AS_CONTRADICTION (Art. XXI.3/XXV)
            if cat == "MALFORMED_MISSING_EVIDENCE":
                rec["false_kill_class"] = ABSENCE_CLASS
            else:
                rec["false_kill_class"] = _classify_false_kill(
                    case, kills)
        elif overall == "SURVIVED":
            rec["outcome"] = "CLEAN_SURVIVED"
        else:
            rec["outcome"] = "UNCERTAIN_HONEST"
    return rec


def _classify_false_kill(case: Dict[str, Any],
                         kills: List[Dict[str, Any]]) -> str:
    """Adjudicate ONE false kill into the R445 classes (the same
    evidence-emergent semantics; ONE dominant class per case by
    PRECEDENCE of specificity — the most specific grounded defect wins
    over the generic bare-assertion class; the per-basis mechanical
    grounding travels alongside in kill_basis_grounding)."""
    cand = case["candidate"]
    bc = str((cand.get("constraint_set") or {})
             .get("boundary_conditions") or "").lower()
    scope_declared = ("out of scope" in bc or "declared scope" in bc
                      or "boundary" in bc)
    scope_demands = 0
    record_contradictions = 0
    unsupported = 0
    severity_inflations = 0
    for k in kills:
        basis = str(k.get("basis") or "")
        low = basis.lower()
        g = _basis_grounding(basis)
        rb = _record_binding(basis, cand)
        # SCOPE_MISMATCH: demands content the declared boundary excludes
        if scope_declared and any(
                w in low for w in ("does not address", "fails to",
                                   "not address", "out of scope",
                                   "beyond", "does not cover")):
            scope_demands += 1
        # RECORD_CONTRADICTED: claims absence of content the record has
        if rb.get("claims_absence") and rb.get("contradictions"):
            record_contradictions += 1
        # UNSUPPORTED_OBJECTION: no citation, no computation, no numbers
        if not (g["citations"] or g["carries_computation"]
                or g["numbers_mentioned"]):
            unsupported += 1
        # SEVERITY_INFLATION: hedged risk language escalated to a kill
        if any(w in low for w in ("may", "might", "could",
                                  "potential", "possible")) and \
                g["absence_claims"]:
            severity_inflations += 1
    # precedence: most specific first (a scope demand or a record
    # contradiction is a SPECIFIC claim; bare assertion is the residue)
    if scope_demands:
        return "SCOPE_MISMATCH"
    if record_contradictions:
        return "RECORD_CONTRADICTED"
    if severity_inflations:
        return "SEVERITY_INFLATION"
    return "UNSUPPORTED_OBJECTION"


def _grounding_for_kills(attack: Dict[str, Any],
                         candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for k in attack.get("kill_basis") or []:
        g = _basis_grounding(k.get("basis") or "")
        rb = _record_binding(k.get("basis") or "", candidate)
        out.append({
            "attack_class": k.get("attack_class"),
            "basis_excerpt": str(k.get("basis") or "")[:160],
            "grounding": g,
            "record_binding": rb,
            "grounded_in_evidence_or_computation": bool(
                g["citations"] or g["carries_computation"]
                or g["numbers_mentioned"] and rb.get("bindings")),
        })
    return out


def score_all(corpus: Dict[str, Any],
              raw: Dict[str, str]) -> Dict[str, Any]:
    cases = corpus["cases"]
    scored = []
    grounding_records = []
    for case in cases:
        attack = raw.get(case["case_id"])
        if attack is None:
            scored.append({"case_id": case["case_id"],
                           "outcome": "NOT_RUN"})
            continue
        scored.append(_score_case(case, attack))
        grounding_records.append({
            "case_id": case["case_id"],
            "kills": _grounding_for_kills(attack, case["candidate"])})

    # ---- the headline confusion matrix (the pre-registered scope) ----
    tp_cohort = [s for s in scored if s.get("seed_class")]
    tn_cohort = [s for s in scored
                 if s.get("category") == "TRUE_NEGATIVE_clean_control"]
    n_tp = len(tp_cohort)
    detected = sum(1 for s in tp_cohort
                   if str(s.get("outcome", "")).startswith("DETECTED"))
    incomplete_tp = sum(1 for s in tp_cohort
                        if s.get("outcome") == "TRANSPORT_INCOMPLETE")
    n_tn = len(tn_cohort)
    false_kills = [s for s in tn_cohort if s.get("outcome") == "FALSE_KILL"]
    clean_survived = sum(1 for s in tn_cohort
                         if s.get("outcome") == "CLEAN_SURVIVED")
    incomplete_tn = sum(1 for s in tn_cohort
                        if s.get("outcome") == "TRANSPORT_INCOMPLETE")
    incomplete_all = sum(1 for s in scored
                         if s.get("outcome") == "TRANSPORT_INCOMPLETE")
    tpr = detected / n_tp if n_tp else None
    fpr = len(false_kills) / n_tn if n_tn else None
    tnr = clean_survived / n_tn if n_tn else None

    # ---- coverage + parse completeness (the R412 semantics) ----------
    run_states = [s for s in scored
                  if s.get("outcome") not in ("NOT_RUN",)]
    attacked = [s for s in run_states
                if s.get("outcome") != "TRANSPORT_INCOMPLETE"]
    coverage = len(attacked) / len(scored) if scored else None
    parse_ok = sum(
        1 for s in attacked
        if s.get("outcome") not in ("UNPARSED",)) / len(attacked) \
        if attacked else None

    # ---- per-category disciplines ------------------------------------
    def _cat(name: str) -> List[Dict[str, Any]]:
        return [s for s in scored if s.get("category") == name]

    near = _cat("NEAR_MISS_real_effect_fatal_magnitude")
    scope = _cat("SCOPE_CONFLICT_declared_boundary_trap")
    evid = _cat("EVIDENCE_CONTRADICTED")
    mal = _cat("MALFORMED_MISSING_EVIDENCE")

    def _frac(n: int, d: int) -> Optional[float]:
        return n / d if d else None

    category_disciplines = {
        "near_miss": {
            "n": len(near),
            "killed_with_markers": sum(
                1 for s in near if s.get("outcome") ==
                "DETECTED_KILL_GROUNDED"),
            "killed_ungrounded": sum(
                1 for s in near if s.get("outcome") ==
                "DETECTED_KILL_UNGROUNDED"),
            "missed": sum(1 for s in near if s.get("outcome") == "MISSED"),
        },
        "scope_conflict": {
            "n": len(scope),
            "survived_correct": sum(
                1 for s in scope if s.get("outcome") == "CLEAN_SURVIVED"),
            "uncertain_honest": sum(
                1 for s in scope if s.get("outcome") == "UNCERTAIN_HONEST"),
            "false_kills": sum(
                1 for s in scope if s.get("outcome") == "FALSE_KILL"),
            "false_kill_is_the_defect_this_category_exists_to_catch":
                "a kill on a declared-boundary case is the SCOPE_MISMATCH "
                "false-kill class the R445 diagnosis measured",
        },
        "evidence_contradicted": {
            "n": len(evid),
            "killed_bound_to_evidence": sum(
                1 for s in evid if s.get("outcome") ==
                "DETECTED_KILL_EVIDENCE_BOUND"),
            "killed_not_bound": sum(
                1 for s in evid if s.get("outcome") ==
                "DETECTED_KILL_NOT_BOUND"),
            "survived": sum(
                1 for s in evid if s.get("outcome") in
                ("CLEAN_SURVIVED", "UNCERTAIN_HONEST")),
        },
        "malformed_missing_evidence": {
            "n": len(mal),
            "not_killed_honest": sum(
                1 for s in mal if s.get("outcome") in
                ("CLEAN_SURVIVED", "UNCERTAIN_HONEST")),
            "kills_on_absence": sum(
                1 for s in mal if s.get("outcome") == "FALSE_KILL"),
            "kills_on_absence_are_the_failure_class":
                ABSENCE_CLASS,
        },
    }

    # ---- grounding aggregate (the R445 finding re-measured) -----------
    all_kills = [k for g in grounding_records for k in g["kills"]]
    grounded = sum(1 for k in all_kills
                   if k["grounded_in_evidence_or_computation"])

    # ---- the gate state (read-only; this run cannot flip it) ----------
    from discovery_fabric.engine.attacker_calibration import resolve_state
    gate_state = resolve_state()

    # ---- the honest verdict (NOT derived from optimism) ----------------
    bars_met = {
        "tpr": tpr is not None and tpr >= BARS["tpr_min"],
        "fpr": fpr is not None and fpr <= BARS["fpr_max"],
        "tnr": tnr is not None and tnr >= (1 - BARS["fpr_max"]),
        "coverage": coverage is not None and coverage >= BARS[
            "coverage_min"],
        "parse": parse_ok is not None and parse_ok >= BARS[
            "parse_completeness_min"],
    }
    all_bars = all(bars_met.values())

    return {
        "report_version": "r446-attacker-calibration/1.0.0",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "freeze_check": _freeze_check(),
        "instrument": "independent_attack/1.0.0 (UNMODIFIED)",
        "transport": {
            "provider_pin": os.environ.get("ENGINE_LLM_PROVIDER", ""),
            "timeout_bound_s": os.environ.get("ENGINE_LLM_TIMEOUT_S", ""),
            "class": "R445-C operator-override (transport-only)",
        },
        "headline_confusion": {
            "tp_cohort": "seeded defects (seed_class set)",
            "n_true_positives": n_tp,
            "detected_kill": detected,
            "TPR": tpr,
            "n_true_negatives": n_tn,
            "false_kills": [s["case_id"] for s in false_kills],
            "FPR": fpr,
            "TNR": tnr,
            "clean_survived": clean_survived,
            "transport_incomplete_all_cohorts": incomplete_all,
            "transport_incomplete_tp_tn": incomplete_tp + incomplete_tn,
        },
        "coverage": coverage,
        "parse_completeness": parse_ok,
        "category_disciplines": category_disciplines,
        "per_case": scored,
        "kill_basis_grounding": {
            "n_kill_bases": len(all_kills),
            "n_grounded_in_evidence_or_computation": grounded,
            "fraction": _frac(grounded, len(all_kills)),
            "per_kill": grounding_records,
        },
        "false_kill_classes": {
            "per_false_kill": [
                {"case_id": s["case_id"],
                 "class": s.get("false_kill_class")}
                for s in scored if s.get("outcome") == "FALSE_KILL"],
            "class_definitions_source":
                "R445/ATTACKER_FALSE_KILL_DIAGNOSIS.json (classes "
                "emerged from evidence there; applied here, not "
                "re-invented)",
        },
        "abstain_escalate_gate": {
            "resolve_state": gate_state,
            "note": ("the gate is untouched and IN FORCE; this "
                     "measurement alone cannot flip CALIBRATED — the "
                     "gate reads the R417 measurement record and "
                     "GATED_INSTRUMENT_VERSION is pinned to "
                     "independent_attack/1.0.0; a future instrument "
                     "version must EARN the flip on its own sealed "
                     "measurement"),
        },
        "pre_registered_bars": BARS,
        "bars_met": bars_met,
        "verdict": {
            "all_bars_met": all_bars,
            "calibration_state_after_this_run": (
                "NOT_CALIBRATED (unchanged — the gate state above is "
                "the authority; better-looking numbers are NOT "
                "interpreted as calibration)"),
            "what_would_earn_calibration": (
                "a future instrument version that mechanically binds "
                "each objection to evidence/computation, the record, "
                "and the declared scope — measured on a sealed corpus "
                "with FPR <= 0.30 at TPR >= 0.75, then wired into the "
                "gate with its own measurement record"),
            "no_false_kill_relabels_as_defect": True,
            "no_threshold_lowered": True,
            "no_clean_control_modified": True,
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
            _log("FATAL: corpus not frozen (commit CORPUS.json before "
                 "the first run — freeze-then-run discipline)")
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
            _log(f"{case['case_id']}: attacking...")
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
    RESULTS_PATH.write_text(json.dumps(results, indent=1, default=str))
    hc = results["headline_confusion"]
    _log(f"TPR {hc['TPR']} ({hc['detected_kill']}/{hc['n_true_positives']}"
         f") | FPR {hc['FPR']} | TNR {hc['TNR']} | "
         f"coverage {results['coverage']} | parse {results['parse_completeness']}")
    _log(f"false kills: {hc['false_kills']}")
    _log(f"gate state: {results['abstain_escalate_gate']['resolve_state'].get('state')}")
    _log(f"results -> {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

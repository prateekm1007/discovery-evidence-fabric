"""R412/CALIBRATION/calibration_metrics.py — P0-1 measurement
mathematics for the sealed attacker-calibration corpus.

Pure functions only (no LLM, no network): every metric here is hermetically
testable against fixed synthetic inputs (Art. XVI: code is a hypothesis;
tests are evidence of enforcement).

OPERATIONAL DEFINITIONS (fixed before the measurement runs; Art. XXVII):

  positives  = cases whose sealed expected_final is KILLED
               (KNOWN_BAD + NEAR_MISS + PRIOR_ART_COLLISION, n=30)
  negatives  = KNOWN_GOOD cases (n=10)
  decisive   = the instrument returned a final verdict
               (attack verdict in {KILLED, SURVIVED})
  coverage   = transport completed (attack status OK) / n
  parse_completeness = decisive / n

  The seal's pre-registered thresholds define the denominators
  explicitly ("TPR >= 0.75 (kills on the 30 defect cases)";
  "FPR (false-kill rate on the 10 KNOWN_GOOD) <= 0.30"), so the
  THRESHOLD-COMPARISON variants are the CONSERVATIVE ones:

    TPR  = killed positives / 30   (a non-decisive positive = a miss)
    FPR  = falsely killed negatives / 10
    TNR  = survived negatives / 10 = 1 - FPR
    FNR  = non-killed positives / 30 = 1 - TPR

  Conditional variants (denominators = decisive cases only) are ALSO
  reported as diagnostics, but never used for the threshold verdict —
  conditioning away the instrument's failures would let incompleteness
  hide misses (Art. XV/XXV: a coverage failure is not a spared case).

  agreement = on cases where BOTH passes are decisive, the fraction
  with identical final verdicts (no ensemble, no voting — parallel
  single-attacker instruments measured independently, per the R412
  directive).

  specificity = killed positives whose kill_surfaces cite the sealed
  expected_kill_surface, plus (diagnostic) the fraction of killed
  positives whose recorded basis mentions at least one sealed
  expected_defect_in_basis marker token.

Constitutional grounding:
  - Art. L: attacker calibration — sensitivity by defect class,
    false-kill rate, independence state, attack coverage.
  - Art. XXVII: thresholds come from the SEALED manifest, read at
    report time; this module never hardcodes them.
  - Art. LIX: the corpus is frozen; nothing here tunes prompts,
    thresholds, or the instrument against it.
  - Art. LXI: transport failure is INCOMPLETE, never counted as a
    scientific verdict in either direction.
  - Art. LXII: per-case prompt/output hashes travel with the results.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DECISIVE_VERDICTS = ("KILLED", "SURVIVED")


# ---------------------------------------------------------------------------
# Preflight: the measurement attacks the SEALED corpus or nothing
# ---------------------------------------------------------------------------

def preflight(corpus_path: Path, seal_path: Path) -> Dict[str, Any]:
    """Verify the corpus bytes against the seal before any attack.

    Returns a preflight record. ok=False means the measurement harness
    MUST NOT run (mutated corpus; Art. VIII seal discipline)."""
    corpus = json.loads(corpus_path.read_text())
    seal = json.loads(seal_path.read_text())
    corpus_sha = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    seal_sha = hashlib.sha256(seal_path.read_bytes()).hexdigest()
    problems: List[str] = []
    if corpus_sha != seal.get("corpus_sha256"):
        problems.append(
            "corpus sha256 does not match the seal — the corpus was "
            "mutated after sealing; refusing to attack it")
    if seal.get("n_cases") != corpus.get("n_cases"):
        problems.append("seal/corpus case-count mismatch")
    if seal.get("corpus_id") != corpus.get("corpus_id"):
        problems.append("seal/corpus id mismatch")
    labels = [c["ground_truth"]["label"] for c in corpus["cases"]]
    expected_counts = seal.get("label_counts") or {}
    for label, count in expected_counts.items():
        if labels.count(label) != count:
            problems.append(
                f"label {label} count {labels.count(label)} != sealed "
                f"{count}")
    return {
        "ok": not problems,
        "corpus_sha256": corpus_sha,
        "seal_sha256": seal_sha,
        "corpus_id": corpus.get("corpus_id"),
        "n_cases": corpus.get("n_cases"),
        "problems": problems,
    }


# ---------------------------------------------------------------------------
# Outcome classification
# ---------------------------------------------------------------------------

def outcome_of(attack_record: Dict[str, Any]) -> str:
    """Map an attack_candidate() return to the measurement outcome:
    KILLED / SURVIVED / CONDITIONAL / INCOMPLETE (Art. LXI: transport
    failure is INCOMPLETE — never a scientific verdict)."""
    if attack_record.get("status") != "OK":
        return "INCOMPLETE"
    verdict = str(attack_record.get("verdict") or "")
    if verdict in DECISIVE_VERDICTS:
        return verdict
    return "CONDITIONAL"


# ---------------------------------------------------------------------------
# Per-pass metrics
# ---------------------------------------------------------------------------

def _r(x: float) -> float:
    return round(x, 4) if x is not None else None


def _marker_in_basis(case: Dict[str, Any], attack_record: Dict[str, Any]
                     ) -> Optional[bool]:
    """True if any sealed expected_defect_in_basis marker token appears
    in the recorded kill text (final objection + surface bases).
    None when the case carries no markers (diagnostic only)."""
    markers = case["ground_truth"].get("expected_defect_in_basis") or []
    if not markers:
        return None
    text = " ".join([
        str(attack_record.get("final_objection") or ""),
        json.dumps(attack_record.get("surfaces") or {}),
    ]).casefold()
    return any(str(m).casefold() in text for m in markers)


def pass_metrics(results: List[Dict[str, Any]],
                 cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute the full per-pass metric block.

    results: per-case records, each {case_id, label, expected_final,
    attack: <attack_candidate return>}. cases: the sealed corpus cases
    (for expected kill surfaces / markers)."""
    by_case = {c["case_id"]: c for c in cases}
    per_case: List[Dict[str, Any]] = []
    outcome_counts: Dict[str, int] = {k: 0 for k in
                                      ("KILLED", "SURVIVED", "CONDITIONAL",
                                       "INCOMPLETE")}
    pos = {"n": 0, "killed": 0, "survived": 0, "non_decisive": 0}
    neg = {"n": 0, "killed": 0, "survived": 0, "non_decisive": 0}
    killed_positives_expected_surface = 0
    killed_positives = 0
    marker_hits: List[bool] = []
    false_kills: List[str] = []
    by_cohort: Dict[str, Dict[str, Any]] = {}

    for rec in results:
        case = by_case.get(rec["case_id"])
        if case is None:
            continue
        gt = case["ground_truth"]
        attack = rec.get("attack") or {}
        outcome = outcome_of(attack)
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        expected = gt["expected_final"]
        is_positive = expected == "KILLED"
        bucket = pos if is_positive else neg
        bucket["n"] += 1
        if outcome == "KILLED":
            bucket["killed"] += 1
        elif outcome == "SURVIVED":
            bucket["survived"] += 1
        else:
            bucket["non_decisive"] += 1

        kill_surfaces = attack.get("kill_surfaces") or []
        eks = gt.get("expected_kill_surface")
        expected_surface_cited = bool(
            outcome == "KILLED" and eks and eks in kill_surfaces)
        if is_positive and outcome == "KILLED":
            killed_positives += 1
            if expected_surface_cited:
                killed_positives_expected_surface += 1
        marker = _marker_in_basis(case, attack)
        if marker is not None:
            marker_hits.append(marker)
        if not is_positive and outcome == "KILLED":
            false_kills.append(rec["case_id"])

        coh = by_cohort.setdefault(
            gt["label"],
            {"n": 0, "KILLED": 0, "SURVIVED": 0,
             "CONDITIONAL": 0, "INCOMPLETE": 0})
        coh["n"] += 1
        coh[outcome] += 1

        per_case.append({
            "case_id": rec["case_id"],
            "label": gt["label"],
            "expected_final": expected,
            "outcome": outcome,
            "correct": (
                (outcome == expected) if outcome in DECISIVE_VERDICTS
                else None),
            "kill_surfaces": kill_surfaces,
            "expected_kill_surface": eks,
            "expected_surface_cited": expected_surface_cited,
            "expected_marker_in_basis": marker,
            "final_objection": str(attack.get("final_objection") or "")[:400],
            "attacker_provider": attack.get("attacker_provider"),
            "attacker_model": attack.get("attacker_model"),
            "independence_mode": attack.get("independence_mode"),
            "prompt_hash": attack.get("prompt_hash"),
            "output_hash": attack.get("output_hash"),
        })

    n = len(results)
    n_decisive = outcome_counts["KILLED"] + outcome_counts["SURVIVED"]
    coverage = _r((outcome_counts["KILLED"] + outcome_counts["SURVIVED"]
                   + outcome_counts["CONDITIONAL"]) / n) if n else None
    parse_completeness = _r(n_decisive / n) if n else None

    def _frac(num: int, den: int) -> Optional[float]:
        return _r(num / den) if den else None

    metrics: Dict[str, Any] = {
        "n": n,
        "outcome_counts": outcome_counts,
        "coverage": coverage,
        "parse_completeness": parse_completeness,
        "confusion": {
            "definition": (
                "conservative variants use the sealed full denominators "
                "(the pre-registered threshold semantics: TPR=killed/30, "
                "FPR=false-killed/10); conditional variants use decisive "
                "cases only and are diagnostics, never threshold inputs"),
            "positives": {
                **pos,
                "TPR": _frac(pos["killed"], pos["n"]),
                "FNR": _frac(pos["n"] - pos["killed"], pos["n"]),
                "TPR_conditional": _frac(
                    pos["killed"], pos["killed"] + pos["survived"]),
                "FNR_conditional": _frac(
                    pos["survived"], pos["killed"] + pos["survived"]),
            },
            "negatives": {
                **neg,
                "FPR": _frac(neg["killed"], neg["n"]),
                "TNR": _frac(neg["survived"], neg["n"]),
                "FPR_conditional": _frac(
                    neg["killed"], neg["killed"] + neg["survived"]),
                "TNR_conditional": _frac(
                    neg["survived"], neg["killed"] + neg["survived"]),
            },
        },
        "by_cohort": by_cohort,
        "specificity": {
            "killed_positives": killed_positives,
            "killed_positives_expected_surface_cited":
                killed_positives_expected_surface,
            "expected_surface_citation_rate": _frac(
                killed_positives_expected_surface, killed_positives),
            "expected_marker_in_basis_rate": _frac(
                sum(1 for m in marker_hits if m), len(marker_hits))
            if marker_hits else None,
        },
        "false_kills": false_kills,
        "false_kill_rate_on_known_good": _frac(
            neg["killed"], neg["n"]),
        "per_case": per_case,
    }
    return metrics


# ---------------------------------------------------------------------------
# Threshold verdict (thresholds read from the SEAL, never hardcoded here)
# ---------------------------------------------------------------------------

def verdict_vs_thresholds(metrics: Dict[str, Any],
                          thresholds: Dict[str, Any]) -> Dict[str, Any]:
    """Compare a pass's metrics against the seal's pre-registered
    thresholds. Returns per-threshold booleans + the overall verdict.
    The thresholds are INPUTS (from the sealed manifest): this function
    cannot tune them (Art. XXVII)."""
    checks = {
        "coverage_min": (
            (metrics.get("coverage") or 0.0)
            >= float(thresholds["coverage_min"])),
        "parse_completeness_min": (
            (metrics.get("parse_completeness") or 0.0)
            >= float(thresholds["parse_completeness_min"])),
        "tpr_min": (
            (metrics.get("confusion", {}).get("positives", {}).get("TPR")
             or 0.0) >= float(thresholds["tpr_min"])),
        "fpr_max": (
            (metrics.get("confusion", {}).get("negatives", {}).get("FPR")
             or 1.0) <= float(thresholds["fpr_max"])),
    }
    calibrated = all(checks.values())
    return {
        "calibrated": calibrated,
        "verdict": "CALIBRATED" if calibrated else "NOT_CALIBRATED",
        "checks": checks,
        "note": (
            "thresholds are the sealed pre-registered values, read from "
            "the manifest at report time; the verdict is a measurement, "
            "never an input to threshold adjustment (Art. XXVII/LIX)"),
    }


# ---------------------------------------------------------------------------
# Cross-pass agreement (no ensemble: parallel single attackers)
# ---------------------------------------------------------------------------

def agreement(pass_results: List[Dict[str, Any]],
              other_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verdict agreement between two passes on cases where BOTH are
    decisive. Disagreements are listed with labels (the user-facing
    artifact: which cases the two instruments split on)."""
    a = {r["case_id"]: r for r in pass_results}
    b = {r["case_id"]: r for r in other_results}
    both_decisive = 0
    agree = 0
    disagreements: List[Dict[str, Any]] = []
    for case_id in sorted(set(a) & set(b)):
        oa = outcome_of((a[case_id].get("attack") or {}))
        ob = outcome_of((b[case_id].get("attack") or {}))
        if oa in DECISIVE_VERDICTS and ob in DECISIVE_VERDICTS:
            both_decisive += 1
            if oa == ob:
                agree += 1
            else:
                disagreements.append({
                    "case_id": case_id,
                    "label": a[case_id].get("label"),
                    "expected_final": a[case_id].get("expected_final"),
                    "pass_a_outcome": oa,
                    "pass_b_outcome": ob,
                })
    return {
        "n_cases_both_decisive": both_decisive,
        "n_agree": agree,
        "n_disagree": len(disagreements),
        "agreement_rate": _r(agree / both_decisive) if both_decisive else
        None,
        "disagreements": disagreements,
        "note": ("parallel single-attacker instruments; no majority-vote "
                 "ensemble is formed (R412 directive)"),
    }


# ---------------------------------------------------------------------------
# Structured death records (the forward-looking guard: ban bare
# "KILLED: KILLED" from future production artifacts)
# ---------------------------------------------------------------------------

def structured_death_record(case: Dict[str, Any],
                            attack_record: Dict[str, Any]
                            ) -> Dict[str, Any]:
    """Every terminal KILLED event must carry a structured reason.

    Fields (the R412 directive minimum):
      death_stage, death_category, specific_reason, evidence_refs,
      attacker_basis

    If the attacker's final_objection was bare ('KILLED' or empty — the
    R411 recorded defect), the specific_reason falls back to the first
    kill-surface basis WITH DISCLOSURE (fallback_used=true). The record
    is never silently repaired (Art. XI: the defect stays visible)."""
    attack = attack_record or {}
    final_objection = str(attack.get("final_objection") or "").strip()
    surfaces = attack.get("surfaces") or {}
    kill_surfaces = attack.get("kill_surfaces") or []
    basis_lines = {
        s: str((surfaces.get(s) or {}).get("basis") or "")
        for s in kill_surfaces
    }
    first_basis = next(
        (b for b in basis_lines.values() if b.strip()), "")

    bare = final_objection.upper() in ("", "KILLED", "SURVIVED")
    specific_reason = final_objection
    fallback_used = False
    if bare:
        if first_basis:
            specific_reason = (
                f"[fallback: first kill-surface basis — the attacker's "
                f"final line was bare] {first_basis}")
            fallback_used = True
        else:
            specific_reason = (
                "[UNSTRUCTURED: the attacker returned a kill with no "
                "objection and no basis text — instrument defect, "
                "recorded not repaired (Art. XV)]")

    evidence_refs = [str(r) for r in
                     ((case.get("candidate") or {}).get("evidence_refs")
                      or [])]
    record = {
        "death_stage": "ATTACK",
        "death_category": kill_surfaces[0] if kill_surfaces
        else "UNSPECIFIED",
        "death_categories_all": list(kill_surfaces),
        "specific_reason": specific_reason[:600],
        "evidence_refs": evidence_refs,
        "attacker_basis": {s: b[:300] for s, b in basis_lines.items()},
        "bare_killed_defect": bare,
        "fallback_used": fallback_used,
    }
    return record


def all_deaths_structured(per_case: List[Dict[str, Any]],
                          cases: List[Dict[str, Any]],
                          pass_results: List[Dict[str, Any]]
                          ) -> Dict[str, Any]:
    """Guard summary for one pass: every KILLED case must have a
    structured record whose specific_reason is not bare. Returns the
    records + a violations list (unstructured kills)."""
    by_case = {c["case_id"]: c for c in cases}
    by_res = {r["case_id"]: r for r in pass_results}
    records: List[Dict[str, Any]] = []
    violations: List[str] = []
    for pc in per_case:
        if pc["outcome"] != "KILLED":
            continue
        case = by_case[pc["case_id"]]
        attack = (by_res.get(pc["case_id"]) or {}).get("attack") or {}
        rec = structured_death_record(case, attack)
        rec["case_id"] = pc["case_id"]
        rec["label"] = pc["label"]
        records.append(rec)
        if rec["bare_killed_defect"] and not rec["fallback_used"]:
            violations.append(pc["case_id"])
    return {
        "n_killed": len(records),
        "records": records,
        "unstructured_violations": violations,
        "guard": (
            "'KILLED: KILLED' (a terminal kill with no structured reason) "
            "is banned from production artifacts; bare finals fall back to "
            "the kill-surface basis with disclosure, and kills with "
            "neither objection nor basis are recorded as violations"),
    }

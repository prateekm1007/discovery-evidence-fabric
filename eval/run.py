#!/usr/bin/env python3
"""EVAL HARNESS for discovery-evidence-fabric (single success metric).

Blind pairwise win-rate of the PIPELINE answer vs the strongest directly
reachable zero-paid single-shot BASELINE, on the 18-problem eval set
(eval/problems.json). Reporting (Art. LXI): win-rate is computed ONLY over
pairs where the pipeline RELEASED an answer; a refusal/infrastructure
failure is never handed to the judge. Headline = "pipeline completion k/N"
plus "win-rate over completed pairs (NOT_MEASURED if none)".

Criteria (fixed):
  A answers the asked question
  B uses user-stated variables
  C specific testable prediction
  D grounded in the provided evidence

Arms
  pipeline  EngineRun end-to-end (resumeable). Answer = released invention
            spec (normalised plain text, labels stripped) or None.
  baseline  strongest directly reachable zero-paid model, called
            INDEPENDENTLY of engine admission, on the SAME frozen evidence
            and the SAME token budget. Model recorded.
  judge     blind pairwise, both switch orders, rubric 1-5 per criterion +
            overall preference. Judge = different provider + model family
            from baseline/generator, never the 1.7B model. Strips labels so
            arms are indistinguishable. Calibrated first (>=10 known-good
            vs known-bad pairs; judge must pick good >=80% or no win-rate).

Honesty
  - An arm with no answer scores nothing (excluded, flagged) � never a
    win by default (Art. LXI).
  - Raw run artifacts stay in eval/runs/ (git-ignored); table carries
    final-state hashes only.
  - Every score is a recorded model call (route + model + prompt hash +
    output hash); the harness never grades itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# DIRECTIVE 1 (owner audit round 2026-11-12): the ONE plain-language
# hypothesis caveat line the harness may append to a delivered answer
# (the composer's own constant — one authority, Art. X). Imported
# AFTER the sys.path insert (the direct-invocation entry point).
from discovery_fabric.engine.answer_composer import HYPOTHESIS_CAVEAT_LINE

# DIRECTIVE 2 (owner audit round 2026-11-12): the composer states that
# DELIVER text (each with at most one plain-language caveat). Every
# other state is the typed no-answer — the delivery rate counts the
# ratio of these states (+ the flagged-hypothesis deliveries) over all
# problems (target >= 90%).
_COMPOSED_DELIVERED_STATES = frozenset({
    "COMPOSED_CONTRACT_VALID",
    "COMPOSED_CONTRACT_DOWNGRADED",
    "COMPOSED_TRUNCATED_DELIVERED",
})


def delivery_rate_from_dirs(pipeline_dirs):
    """Delivery rate over a run's pipeline dirs: delivered / total.
    Delivered = the composer record carries a non-empty answer in a
    _COMPOSED_DELIVERED_STATES state. Typed no-answer (scientific
    refusals, transport failure) counts as NOT delivered — directive 2
    keeps the number honest, never gamed (Art. XIX)."""
    delivered = total = 0
    for d in pipeline_dirs:
        total += 1
        p = Path(d) / "ANSWER_COMPOSED.json"
        if not p.exists():
            continue
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        ans = rec.get("answer")
        if isinstance(ans, str) and ans.strip() \
                and rec.get("state") in _COMPOSED_DELIVERED_STATES:
            delivered += 1
    return {"delivered": delivered, "total": total,
            "rate": round(delivered / total, 4) if total else None}


def _answer_contract(answer, question_type, packet=None,
                     user_variables=None, clarification=None):
    """Deterministic shape check of the released pipeline answer."""
    try:
        from discovery_fabric.engine.answer_contract import validate_answer
        return validate_answer(answer or "", question_type or "",
                               packet=packet or [],
                               user_variables=user_variables or [],
                               clarification=clarification or None)
    except Exception as exc:  # noqa: BLE001
        return {"valid": None, "violations": [f"validator error: {exc}"],
                "question_type": question_type}


def _contract_summary(rows):
    out = []
    for r in rows:
        ac = r.get("answer_contract") or {}
        out.append({"problem_id": r.get("problem_id"),
                    "valid": ac.get("valid"),
                    "violations": ac.get("violations") or []})
    return out

os.environ.setdefault("LOCAL_QWEN_BASE_URL", "http://127.0.0.1:8790/v1/chat/completions")
os.environ.setdefault("MODEL_COST_POLICY", "ZERO_PAID_COST")

PROBLEMS = Path(__file__).resolve().parent / "problems.json"
RUNS_ROOT = Path(__file__).resolve().parent / "runs"
SCORE_DIR = Path(__file__).resolve().parent / "score"
# sealed holdout outputs are always gitignored; the harness reads an
# owner-supplied external file at runtime, never dev problems
HOLDOUT_ROOT = Path(__file__).resolve().parent / "holdout_runs"

# holdout mode suppresses problem identifiers in all printed output
_HOLDOUT_MODE = False
_LBL_MAP: Dict[str, str] = {}


def _label(pid: str) -> str:
    if not _HOLDOUT_MODE:
        return pid
    if pid not in _LBL_MAP:
        _LBL_MAP[pid] = f"problem-{len(_LBL_MAP) + 1}"
    return _LBL_MAP[pid]

# Fast DEV subset (directive: replace the long inner loop; a 6-problem
# subset mixing intervention and predictor types, full 25 only at
# checkpoints). Pre-registered ids, never chosen after seeing results.
DEV7 = [
    "bench-p02-leadacid-grid-corrosion",   # intervention; contamination
    "bench-p05-bridge-bearing-aging",      # intervention; contamination
    "bench-p09-packaging-barrier",         # intervention; contamination
    "eval-new02-slipring-predictor",       # predictor
    "eval-new06-bearing-vibration-predictor",  # predictor
    "eval-new09-hvac-filter-predictor",    # predictor
    "eval-sofc-thermal-cycling",           # intervention; has clarification_answer (e_clarification)
]

CRITERIA = {
    "a_answered": "answers the asked question",
    "b_user_vars": "uses user-stated variables",
    "c_prediction": "gives a specific testable prediction",
    "d_evidence": "grounded in the provided evidence",
    "e_clarification": "uses the user's clarification answer correctly",
    "f_novelty": "gives a specific, non-obvious design (not the generic default)",
}

# Judge must be a different provider + model family from the baseline
# (agnes) and never the 1.7B model. Candidates probed in order.
# INCEPTION MERCURY-3 WAS AUDIT-MEASURED AS NOT CALIBRATABLE (1/30 on
# the known-answer set, 29 empty-output pairs) and is therefore removed;
# an official-provider free-tier key is added only when the owner
# supplies one. No further judge-routing work this round.
JUDGE_CANDIDATES = [
    ("xkiro", "mistralai/ministral-14b"),
    ("xkiro", "mistralai/ministral-8b"),
    ("unorouter", "deepseek-v4-flash:free"),
]
#: R6: the operator-accepted LAST-RESORT judge. When NO independent
#: candidate is reachable, the shared-family judge may serve ONLY when
#: the operator explicitly sets EVAL_JUDGE_ALLOW_SHARED_FAMILY=1 (the
#: owner's 2026-11-11 directive accepts a my-judged win/tie/loss for
#: the R6 dev round). The disclosure travels on EVERY judge record and
#: in SCORE_TABLE.judge_independence — a reader can never mistake a
#: shared-family verdict for an independent one (Art. XXVII: recorded,
#: never silent).
JUDGE_LAST_RESORT = ("zai", "glm-4-plus")
#: R6 owner round 2026-11-12 (operator-override class, Art. XXVII —
#: recorded, never silent; the same class as the ENGINE_*_PROVIDER pins):
#: when the zai loopback-gateway rung has no operator credential
#: (owner-supplied key rounds: AGNES/INCEPTION only), the operator may
#: name the shared-family last-resort judge explicitly:
#:   EVAL_JUDGE_LAST_RESORT=provider,model
#: The name is recorded on the route record AND on every judgment it
#: produces (the disclosure machinery below is unchanged); the 30-pair
#: calibration gate still applies in full — a named shared-family judge
#: that cannot separate known-good from known-bad is still not a judge
#: (Art. XXV), and the route stays NO_CALIBRATED_JUDGE_ROUTE typed. No
#: new gate, no new report: an operator-named rung, exactly like the
#: pins above.
_ENV_JUDGE_LAST_RESORT = "EVAL_JUDGE_LAST_RESORT"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def git_short() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=str(REPO), text=True).strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def git_dirty() -> bool:
    """True when tracked files differ from HEAD (the harness records it
    next to every measured row; a dirty run is never silently clean)."""
    import subprocess
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=str(REPO), text=True)
        return bool(out.strip())
    except Exception:  # noqa: BLE001
        return True


def _round1_problem(problem: Dict[str, Any]) -> Dict[str, Any]:
    """R6 (owner directive 2026-11-11, item 5): the ROUND-1 view of a
    two-turn problem. The follow-up finding is ROUND-2 information
    (Art. LI): a round-1 run that ingests it has leaked the answer to
    the question round 2 is supposed to demonstrate learning on. Every
    round-1 arm (pipeline, baseline, composer, judge) consumes the
    problem THROUGH this helper; the round-2 child process sets
    EVAL_ROUND2_INTAKE=1 so its intake keeps the finding."""
    if os.environ.get("EVAL_ROUND2_INTAKE", "").strip().lower() in (
            "1", "true", "yes"):
        return problem
    return {k: v for k, v in problem.items() if k != "followup_finding"}


def _intake_problem(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Engine intake with the user's clarification answer attached.

    The clarification is a user-stated fact (not retrieved evidence); it
    rides the problem constraint so synthesis, mechanism instantiation
    and the attack all see the same value. The original dict is never
    mutated (the on-disk problem stays the pre-registered one)."""
    q = dict(problem)
    ca = problem.get("clarification_answer")
    ff = problem.get("followup_finding")
    if ff:
        # round-2 engine intake: the follow-up finding is a user-stated fact
        if isinstance(ff, dict):
            txt = "; ".join(f"{k} = {v}" for k, v in ff.items()
                            if k != "note" and not isinstance(v, (dict, list)))
            ff_txt = str(txt) + (f" ({ff.get('note')})" if ff.get("note") else "")
        else:
            ff_txt = str(ff)
        q["followup_text"] = ff_txt
        q["constraint"] = (str(q.get("constraint") or "").rstrip(" .")
                           + f". The user returned with one finding: {ff_txt}.").lstrip(" .")
        q["user_variables"] = list(q.get("user_variables") or []) + [
            f"user finding: {ff_txt}"]
    if not ca:
        return q
    if isinstance(ca, dict):
        vals = [f"{k} = {v}" for k, v in ca.items()
                if k not in ("note",) and not isinstance(v, (dict, list))]
        note = ca.get("note")
        text = "; ".join(vals)
        if note:
            text = (text + f" ({note})").strip()
    else:
        text = str(ca)
    q["clarification_text"] = text
    if text:
        q["constraint"] = (str(q.get("constraint") or "").rstrip(" .")
                           + f". User-stated clarification: {text}.").lstrip(" .")
    return q


# ---------------------------------------------------------------------------
# arm: pipeline
# ---------------------------------------------------------------------------
def run_pipeline_problem(problem: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    """One measured pipeline arm, ALWAYS a full fresh run.

    R5: the earlier auto-resume short-circuit (resume iff
    envelope_RETRIEVE.json exists) let a re-run reuse the previous
    arm's artifacts and report rc=0 with wall_s≈0. For a controlled
    A/B comparison each arm must genuinely re-run the pipeline; stale
    artifacts from a different A/B toggle leaking in would fabricate
    results."""
    # R6 ablation: leave-one-out arms disable stages via
    # EVAL_DISABLE_STAGES (comma-separated), set by the ablation driver
    # on the child env. The disabled set travels into the record (the
    # ablation table cites it per row).
    _dis = [s.strip() for s in
            (os.environ.get("EVAL_DISABLE_STAGES") or "").split(",")
            if s.strip()]
    # Establish a clean out_dir. If we cannot, this measured arm must
    # produce a typed INCOMPLETE record — it must NEVER reuse stale
    # artifacts from an earlier arm (the defect that zeroed the A/B).
    stale_error: Optional[str] = None
    try:
        import shutil
        if out_dir.exists():
            shutil.rmtree(out_dir)   # fail-closed: raise on error
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # noqa: BLE001 — fail closed, never fall through
        stale_error = f"FRESH_RUN_UNESTABLISHABLE: {type(exc).__name__}: {exc}"[:400]
    final_state = out_dir / "final_state.json"
    t0 = time.time()
    status, err = stale_error, None
    if stale_error is None:
        try:
            from discovery_fabric.engine.run import EngineRun
            run = EngineRun(
                _intake_problem(problem), str(out_dir),
                run_id=f"eval-{problem['problem_id']}",
                package_registry_path=str(out_dir / "PACKAGE_ID_REGISTRY.json"),
                with_package=(os.environ.get("ENGINE_NO_PACKAGE", "").strip()
                             not in ("1", "true", "yes")),
                disabled_stages=(_dis or None),
                resume=False)
            manifest = run.run()
            status = manifest.get("final_status") if isinstance(manifest, dict) else None
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"[:400]
    if stale_error is not None:
        err = stale_error
    completed = (stale_error is None
                 and (out_dir / "final_state.json").exists()
                 and json.loads((out_dir / "final_state.json").read_text(encoding="utf-8")).get("final_status") in COMPLETED_STATUSES)
    _legacy_diag = "COMPOSE" in _dis
    _ans = _extract_pipeline_answer(out_dir,
                                    legacy_diagnostic=_legacy_diag)
    _avr = _attack_overall(out_dir)
    _comp = None
    _comp_p = out_dir / "ANSWER_COMPOSED.json"
    if _comp_p.exists():
        try:
            _c = json.loads(_comp_p.read_text(encoding="utf-8"))
            _comp = {"state": _c.get("state"),
                     "n_llm_calls": _c.get("n_llm_calls"),
                     "contract_valid": (
                         (_c.get("contract") or {}).get("valid")
                         if _c.get("contract") else None),
                     "provider": _c.get("provider_route"),
                     "model": _c.get("model")}
        except Exception:  # noqa: BLE001
            _comp = None
    record: Dict[str, Any] = {
        "answer": _ans,
        "answer_source": _answer_source(out_dir,
                                        legacy_diagnostic=_legacy_diag),
        "completed": completed,
        "wall_s": round(time.time() - t0, 1),
        "engine_error": err,
        "stage_times_s": _stage_times(out_dir),
        "same_evidence": _evidence_snapshot(out_dir),
        "attack_verdict": _avr,
        # P0-4: UNVERIFIED_HYPOTHESIS is a delivery state of the
        # DIAGNOSTIC no_COMPOSE arm only (the flagged-hypothesis
        # construction); on the normal path a KILLED attack delivers
        # the typed no-answer state (NO_ANSWER + typed_no_answer:<...>
        # in answer_source), never a legacy construction
        "answer_state": ("UNVERIFIED_HYPOTHESIS"
                         if (_avr == "KILLED" and _ans and _legacy_diag)
                         else ("RELEASED" if _ans else "NO_ANSWER")),
        "disabled_stages": _dis,
        "composer": _comp,
    }
    if final_state.exists() and stale_error is None:
        fs = json.loads(final_state.read_text(encoding="utf-8"))
        record["final_status"] = fs.get("final_status")
        record["reason"] = fs.get("reason")
    elif stale_error is not None:
        record["final_status"] = "INCOMPLETE_INFRASTRUCTURE"
        record["reason"] = stale_error
    return record


COMPLETED_STATUSES = {"AUTOMATED_INVENTION_CANDIDATE",
                      "INVENTION_REQUIRES_EXPERIMENT",
                      "INVENTION_UNDER_DEVELOPMENT",
                      "AUTOMATED_INVENTION"}


# ---------------------------------------------------------------------------
# arm: composer-only (R6 ablation — item 6, "composer-only vs full vs
# leave-one-out per stage"; the composer is item 3's ANSWER COMPOSER)
# ---------------------------------------------------------------------------
def run_composer_only_problem(problem: Dict[str, Any],
                              out_dir: Path) -> Dict[str, Any]:
    """ABLATION ARM 'composer-only': the ANSWER COMPOSER ALONE — one LLM
    call (plus its one in-composer repair retry) with the problem's
    constraints + variables, NO packet, NO candidates, NO verification.
    Measures exactly what the staged pipeline adds over its own final
    writer. The composed answer gets the same deterministic contract and
    the same 0-4 rubric judge as every other arm (paired comparison)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        from discovery_fabric.engine.answer_composer import compose_answer
        rec = compose_answer(
            _intake_problem(problem),
            packet=[],            # composer-only: no frozen packet
            candidates=[],        # composer-only: no staged candidates
            verification=None,    # composer-only: no verification state
            question_type=str(problem.get("question_type")
                              or "intervention-proposal"))
    except Exception as exc:  # noqa: BLE001 — typed failure, never silent
        rec = {"state": "COMPOSE_FAILED_TRANSPORT",
               "error": f"{type(exc).__name__}: {exc}"[:300],
               "answer": None}
    rec["wall_s"] = round(time.time() - t0, 1)
    rec["arm"] = "composer-only"
    rec["problem_id"] = problem["problem_id"]
    (out_dir / "composer_only_record.json").write_text(
        json.dumps(rec, indent=1, default=str) + "\n", encoding="utf-8")
    print(f"[eval] {_label(problem['problem_id'])}: composer-only done "
          f"({rec['wall_s']}s, state={rec.get('state')})", flush=True)
    return rec


def _attack_overall(out_dir: Path) -> str:
    """The gauntlet verdict on the primary candidate."""
    for name in ("envelope_ATTACK.json", "candidate_envelope.json"):
        p = out_dir / name
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            ar = d.get("attack_results")
            v = (ar or {}).get("overall")
            if v:
                return str(v).upper()
        except Exception:  # noqa: BLE001
            continue
    return "UNKNOWN"


#: DIRECTIVE 1 (owner audit round 2026-11-12): caveat lines that
#: narrate pipeline history / truncation repair are NEVER delivered to
#: the judge — only plain-language engineering caveats ride the answer.
_PIPELINE_NARRATION_CAVEAT_MARKERS = (
    "cut off at the model's output budget",
    "larger-budget recomposition",
    "repair attempt was also cut off",
    "pre-repair draft",
    "open contract violations",
    "deterministic format check",
)


def _is_pipeline_narration_caveat(caveat: str) -> bool:
    low = str(caveat or "").lower()
    return any(m in low
               for m in _PIPELINE_NARRATION_CAVEAT_MARKERS)


def _best_flagged_answer(out_dir: Path) -> Optional[str]:
    """Deliver the best flagged hypothesis honestly labeled UNVERIFIED
    (Art. XI/LXI). Never presents a killed candidate as an invention;
    the label says exactly what it is. P0-4: DIAGNOSTIC use only —
    the no_COMPOSE ablation arm (the superseded construction is
    never released on the normal path, Art. IV/LXIV)."""
    ce = out_dir / "candidate_envelope.json"
    if not ce.exists():
        return None
    try:
        d = json.loads(ce.read_text(encoding="utf-8"))
        mm = d.get("mechanism_map") or {}
        parts = []
        for k in ("mechanism", "intervention", "expected_effect",
                  "falsification_test", "predicted_effect"):
            v = mm.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
            elif isinstance(v, dict):
                t = v.get("value") or v.get("mechanism") or ""
                if isinstance(t, str) and t.strip():
                    parts.append(t.strip())
        if not parts:
            return None
        body = "\n\n".join(parts)[:6000]
        # DIRECTIVE 1 (owner audit round 2026-11-12): plain language,
        # one line, no internal state names or process narration.
        return ("UNVERIFIED HYPOTHESIS — this proposal is delivered as "
                "an engineering hypothesis: it requires the stated "
                "falsification test before adoption and is not an "
                "endorsed recommendation.\n\n"
                + body)
    except Exception:
        return None


def _answer_source(out_dir: Path, legacy_diagnostic: bool = False) -> str:
    """Which emitter produced the delivered answer (Art. X/XI).
    P0-4: on the normal path the composer record is the only authority
    (composer_llm_call:<state>) or a TYPED no-answer state
    (typed_no_answer:<state> / composer_record_absent) — the
    superseded construction is never a normal answer. The
    superseded_field_concatenation_* labels remain reachable ONLY on
    the DIAGNOSTIC-labelled no_COMPOSE ablation arm (legacy_diagnostic
    True; Art. LXIV: the superseded implementation is retired when
    that scoped use is complete)."""
    comp_p = Path(out_dir) / "ANSWER_COMPOSED.json"
    comp = None
    if comp_p.exists():
        try:
            comp = json.loads(comp_p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            comp = None
    if comp is not None:
        _a = comp.get("answer")
        if _a and str(_a).strip():
            if comp.get("state") == "COMPOSED_CONTRACT_VALID":
                return (f"composer_llm_call:{comp.get('state') or '?'}")
            # DIRECTIVE 1: a contract-invalid composition is never
            # delivered — the delivered answer is the typed no-answer
            # (the record still carries the invalid text + violations
            # for diagnostics; the DELIVERED outcome is what the label
            # names, Art. X: the label describes the actual delivery)
            return ("typed_no_answer:"
                    + str(comp.get("state") or "FAILED_EXPLICIT"))
        if not legacy_diagnostic:
            return ("typed_no_answer:"
                    + str(comp.get("state") or "FAILED_EXPLICIT"))
        # the explicit no_COMPOSE arm: the composer is disabled here;
        # name the diagnostic construction actually consulted below
    if not legacy_diagnostic:
        return "composer_record_absent"
    if _attack_overall(out_dir) == "KILLED":
        return "diagnostic_unverified_hypothesis_fallback"
    if (Path(out_dir) / "INVENTION_SPECIFICATION.json").exists():
        return "diagnostic_superseded_field_concatenation_invention_spec"
    if (Path(out_dir) / "candidate_envelope.json").exists():
        return ("diagnostic_superseded_field_concatenation_"
                "candidate_envelope")
    return "diagnostic_none"


def _extract_pipeline_answer(out_dir: Path,
                             legacy_diagnostic: bool = False) -> Optional[str]:
    """Delivered plain-text answer, or None when nothing was released
    (a refusal notice is never handed to the judge — Art. LXI).

    P0-4 (owner directive 2026-11-11, item 4; Art. IV no-fallback /
    Art. LXIV retire-superseded): the ANSWER COMPOSER's record
    (ANSWER_COMPOSED.json, one LLM call over constraints + variables
    + candidates + packet + verification) is the ONLY answer
    authority on the normal path. A composition that violates the
    contract is delivered HONESTLY FLAGGED (its violations ride in
    the record) — never silently replaced, never silently dropped.
    When the composer produced no answer (NO_ADMISSIBLE_CANDIDATES,
    SKIPPED_NO_PACKET, COMPOSE_FAILED_TRANSPORT, or no record at
    all), the normal path returns a TYPED incomplete/no-answer state
    (it rides answer_source as typed_no_answer:<state> /
    composer_record_absent) — it never falls through to the
    superseded field-concatenation construction, which would release
    an answer that did not pass the current composition contract
    (Art. IV: the failure of the strong path is never the quiet
    activation of a weaker one).

    legacy_diagnostic=True is reachable ONLY from the explicitly
    selected no_COMPOSE ablation arm: the superseded construction
    (flagged-UNVERIFIED hypothesis on KILLED, INVENTION_
    SPECIFICATION.json / candidate_envelope.json field
    concatenation) remains as clearly labelled DIAGNOSTIC material
    for that arm's pruning question, and is never released as the
    normal answer. Art. LXIV: the superseded implementation is
    retired when this explicitly scoped ablation use is complete."""
    comp_p = Path(out_dir) / "ANSWER_COMPOSED.json"
    comp: Optional[Dict[str, Any]] = None
    if comp_p.exists():
        try:
            comp = json.loads(comp_p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — corrupt record reads as absent
            comp = None
    # 0) composed answer (R6 ANSWER COMPOSER — the normal-path authority)
    if comp is not None:
        _c_ans = comp.get("answer")
        if _c_ans and str(_c_ans).strip():
            # DIRECTIVE 2 (owner audit round 2026-11-12): the delivered
            # classes are the composer's DELIVERED states — valid,
            # downgraded (unsupported certainty relabeled ASSUMPTION,
            # invalid citations dropped), or a truncated draft cut at
            # the last complete sentence. Each ships with at most ONE
            # plain-language caveat line; the typed states (open
            # violations, repair history, constraint-audit findings)
            # ride the record metadata, never the delivered text
            # (Art. XXV; Art. LXI: infrastructure is never silence).
            if comp.get("state") in _COMPOSED_DELIVERED_STATES:
                _delivered = str(_c_ans)
                _cav = [str(c) for c in (comp.get("caveats") or [])
                        if isinstance(c, str) and c.strip()]
                _plain = [c for c in _cav
                          if not _is_pipeline_narration_caveat(c)]
                if comp.get("admitted_candidates") and any(
                        c.get("hypothesis") for c in
                        comp.get("admitted_candidates")
                        if isinstance(c, dict)):
                    _plain.insert(0, HYPOTHESIS_CAVEAT_LINE)
                if _plain:
                    _delivered = _delivered.rstrip() + "\n\n" + _plain[0]
                return _delivered[:6000]
            # a state with no delivered text (transport failure, the
            # composer's typed scientific refusals) is the typed
            # no-answer: the label names the actual delivery (Art. X)
            return ("typed_no_answer:"
                    + str(comp.get("state") or "FAILED_EXPLICIT"))
        if not legacy_diagnostic:
            # P0-4 normal path: the composer ran and produced no
            # admissible answer — typed no-answer state, NEVER a
            # silent fall-through to the superseded construction
            # (Art. IV: no fallback epistemology)
            return None
        # the explicitly selected no_COMPOSE arm: the composer is
        # DISABLED_BY_CONFIG here; the construction below is
        # DIAGNOSTIC-labelled (Art. LXIV)
    if not legacy_diagnostic:
        # P0-4: no composer record at all on the normal path (the
        # engine never reached the COMPOSE stage, or the record was
        # lost) — typed infrastructure state (Art. LXI), never the
        # superseded construction
        return None
    # ---- DIAGNOSTIC (no_COMPOSE ablation arm) superseded
    # ---- construction — clearly labelled, never a normal answer
    # Always-deliver (Art. XI): if the gauntlet killed everything but a
    # candidate exists, deliver the best hypothesis honestly labeled
    # UNVERIFIED (diagnostic arm only).
    if _attack_overall(out_dir) == "KILLED":
        released = _best_flagged_answer(out_dir)
        if released:
            return released
    # 1) released invention spec (post-rank path)
    spec_p = out_dir / "INVENTION_SPECIFICATION.json"
    if spec_p.exists():
        try:
            spec = json.loads(spec_p.read_text(encoding="utf-8"))

            def val(key: str) -> str:
                v = spec.get(key)
                if isinstance(v, dict):
                    inner = v.get("value")
                    if isinstance(inner, dict):
                        return " ".join(str(x) for x in inner.values() if x)
                    return str(inner or "")
                if isinstance(v, str):
                    return v
                return ""

            parts = [val(k).strip() for k in ("mechanism", "causal_chain", "killer_experiment")]
            parts = [p for p in parts if p]
            if parts:
                return "\n\n".join(parts)[:6000]
        except Exception:  # noqa: BLE001
            pass
    # 2) candidate envelope (mechanism_map) - primary discovery loop output
    ce = out_dir / "candidate_envelope.json"
    if ce.exists():
        try:
            d = json.loads(ce.read_text(encoding="utf-8"))
            mm = d.get("mechanism_map") or {}
            parts = []
            for k in ("mechanism", "intervention", "expected_effect",
                      "falsification_test", "predicted_effect"):
                v = mm.get(k)
                if isinstance(v, str) and v.strip():
                    parts.append(v.strip())
                elif isinstance(v, dict):
                    t = v.get("value") or v.get("mechanism") or ""
                    if isinstance(t, str) and t.strip():
                        parts.append(t.strip())
            if parts:
                return "\n\n".join(parts)[:6000]
        except Exception:  # noqa: BLE001
            pass
    return None


def _stage_times(out_dir: Path) -> Dict[str, float]:
    """Per-stage durations straight from the durable stage ledger.

    The engine already records `duration_monotonic_s` on every stage_log
    entry; this reads it (never re-times, never estimates). Candidate
    envelope first, then any envelope that carries the log."""
    for name in ("candidate_envelope.json", "envelope_RANK.json",
                 "envelope_CLASSIFY.json"):
        p = out_dir / name
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        log = d.get("stage_log") or []
        out: Dict[str, float] = {}
        for row in log:
            if not isinstance(row, dict):
                continue
            stage = row.get("stage")
            dur = row.get("duration_monotonic_s")
            if stage and isinstance(dur, (int, float)):
                out[str(stage)] = round(float(dur), 3)
        if out:
            return out
    return {}


def _evidence_snapshot(out_dir: Path) -> Optional[Dict[str, Any]]:
    freeze = out_dir / "envelope_FREEZE.json"
    if not freeze.exists():
        return None
    try:
        d = json.loads(freeze.read_text(encoding="utf-8"))
        ev = d.get("evidence") or []
        ids = [e.get("id") for e in ev if isinstance(e, dict) and e.get("id")]
        return {"ids": ids, "hash": _sha(json.dumps(ev, ensure_ascii=False)),
                "items": ev, "problem": d.get("problem")}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)[:200]}


# ---------------------------------------------------------------------------
# zero-paid route probe (baseline + judge are independent of engine admission)
# ---------------------------------------------------------------------------
def _probe_rung(provider: str, model: str) -> bool:
    from discovery_fabric.engine import llm_registry as lr
    from discovery_fabric.engine import runtime_admission as ra
    spec = next((s for s in lr.PROVIDER_SPECS if s.provider_id == provider), None)
    if spec is None:
        return False
    try:
        pr = ra.probe_capability(provider, model, timeout_s=120, persist_ledger=False)
        return bool(pr.get("ok"))
    except Exception:  # noqa: BLE001
        return False


def _call_rung_direct(provider: str, model: str, prompt: str, system: str,
                      max_tokens: int) -> Dict[str, Any]:
    from discovery_fabric.engine import llm_registry as lr
    spec = next((s for s in lr.PROVIDER_SPECS if s.provider_id == provider), None)
    if spec is None:
        return {"status": "NO_SPEC", "content": None}
    try:
        res = lr.generate(
            prompt, system=system, max_tokens=max_tokens, timeout=900,
            policy=lr.SelectionPolicy(preferred_providers=[provider],
                                      purpose="eval:direct"),
            run_id=f"eval-direct-{provider}")
        # force the model via env pin semantics is not needed; generate
        # uses spec.default_model. Override by calling transport directly:
        return {"status": res.status, "provider_id": res.provider_id,
                "model": res.model, "content": res.content,
                "error": res.error, "failure_type": res.failure_type}
    except Exception as exc:  # noqa: BLE001
        return {"status": "EXC", "content": None, "error": str(exc)[:200]}


def _transport_call(provider: str, model: str, prompt: str, system: str,
                    max_tokens: int) -> Dict[str, Any]:
    """Call a (provider, model) directly via the transport, bypassing the
    registry's pinned-model families and admission cache. Used by the
    baseline and judge arms (Art. LXI: strongest DIRECTLY REACHABLE
    model, independent of engine admission)."""
    from discovery_fabric.engine import llm_registry as lr
    spec = next((s for s in lr.PROVIDER_SPECS if s.provider_id == provider), None)
    if spec is None:
        return {"status": "NO_SPEC", "content": None}
    # honour operator pin via env so model_for_call picks it
    os.environ[f"{provider.upper()}_MODEL"] = model
    # R6 (owner directive: FAST and LEAN): the judge/baseline arms are
    # single-shot short-answer calls — measured OK latency on the R6
    # gateway <= 15 s, and the gateway's own watchdog now bounds every
    # connection server-side. The old 900 s per-attempt socket budget let
    # ONE wedged connection consume 15 minutes (3 attempts = 45 min) of
    # the run's wall inside getresponse (measured on fresh-run 1's
    # judge-calibration phase). 180 s is ~12x the measured p99 OK latency
    # and still under the gateway's CLI generation cap for a slow but
    # legitimate long generation; a silent wedge costs its 180 s and the
    # retry ladder opens a FRESH connection (never 45 min).
    _R6_CALL_BUDGET_S = 180
    try:
        # anthropic flavor not needed for our free rungs (all openai)
        content = None
        if spec.flavor == "anthropic":
            content = lr._call_anthropic_flavor(spec, [{"role": "user", "content": prompt}],
                                                _R6_CALL_BUDGET_S, max_tokens, model_override=model)
        else:
            content = lr._call_openai_flavor(spec, [{"role": "user", "content": prompt}],
                                             _R6_CALL_BUDGET_S, max_tokens, model_override=model)
        return {"status": "OK", "provider_id": provider, "model": model,
                "content": content}
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "provider_id": provider, "model": model,
                "content": None, "error": str(exc)[:300]}
    finally:
        os.environ.pop(f"{provider.upper()}_MODEL", None)


def probe_zero_paid_route() -> Dict[str, Any]:
    """Strongest directly reachable rung (probe, then return). Tries
    candidate (provider, model) pairs in quality order.

    R6 (owner directive 2026-11-11, "world-class, end-to-end"): the
    sandbox's own rung (zai/glm-4-plus, cost basis ENVIRONMENT_GRANT —
    recorded honestly, never claimed free-tier or self-hosted) is the
    LAST candidate: reachable only when the operator sets
    ENGINE_MODEL_COST_POLICY=UNRESTRICTED for this measurement round
    (recorded per run in _run_meta.json; the ZERO_PAID_COST policy
    refuses it fail-closed — the refusal, not a silent widening, is the
    default)."""
    try:
        from discovery_fabric.engine import adapters as _ad
        _ad.load_credentials()
    except Exception:  # noqa: BLE001
        pass
    candidates = [
        ("agnes", "agnes-3.0-flash"),
        ("xkiro", "mistralai/ministral-14b"),
        ("xkiro", "mistralai/ministral-8b"),
        ("unorouter", "deepseek-v4-flash:free"),
        ("agnes", "agnes-2.5-flash"),
        ("unorouter", "qwen3.8-27b:free"),
        ("zai", "glm-4-plus"),
    ]
    # R6 owner round 2026-11-12 (measured): consult the ONE retirement
    # gate before probing. The baseline is a synthesis-class call (the
    # same long-form shape as SYNTHESIZE), so a provider retired from
    # ROLE_SYNTHESIS is skipped BEFORE the probe — a single probe call
    # can still pass inside a quota window (agnes: 1 request per 3
    # minutes passed the probe, then the real baseline call burned the
    # breaker). The blocked state rides the attempts record (Art.
    # XXVII: recorded, never silent).
    from discovery_fabric.engine.provider_health import (
        ROLE_SYNTHESIS as _ROLE_SYNTHESIS, is_route_retired)
    attempts = []
    for prov, model in candidates:
        if is_route_retired(prov, role=_ROLE_SYNTHESIS):
            attempts.append({"provider": prov, "model": model,
                             "state": "RETIRED_ROUTE_BLOCKED"})
            continue
        ok = _probe_rung(prov, model)
        attempts.append({"provider": prov, "model": model, "state": "OK" if ok else "FAIL"})
        if ok:
            return {"provider": prov, "model": model, "state": "OK",
                    "probed": attempts, "at": utc_now()}
    return {"provider": None, "model": None, "state": "NO_ZERO_PAID_ROUTE_REACHABLE",
            "probed": attempts, "at": utc_now()}


# The previously calibration-verified judge (xkiro/ministral-14b, 30/30 on
# the 30-pair known-answer set, verified 2026-11-10) is the historical
# REFERENCE — its record is preserved. It is NOT used to authorize a
# route without a live calibration. R5 P0-1: route selection is
# calibration-aware; the sequence continues to the next candidate when a
# selected provider fails actual calibration. Eligibility = PASS on the
# existing 30-pair calibration (>=24/30, 0.8 threshold). Capability
# failures are classified distinctly: HTTP 401 auth / 403 quota /
# 429 throttling / 5xx upstream / empty-or-truncated generation /
# timeout / parse. An auth rejection is never reported as generic
# temporary unavailability.
def probe_judge_route(baseline_provider: str) -> Dict[str, Any]:
    """Calibration-aware judge selection. Returns the first
    calibration-eligible candidate, with a full per-candidate record."""
    results = []
    for prov, model in JUDGE_CANDIDATES:
        rec: Dict[str, Any] = {"provider": prov, "model": model,
                               "reference": (
                                   "xkiro/ministral-14b historically "
                                   "calibrated 30/30 (2026-11-10); record "
                                   "preserved, never used as authorization"
                                   if (prov, model) ==
                                   ("xkiro", "mistralai/ministral-14b")
                                   else None)}
        if prov == baseline_provider:
            rec.update({"eligible": False,
                        "decision": "REJECTED_SAME_PROVIDER_AS_BASELINE",
                        "capability": {"state": "SKIPPED"}})
            results.append(rec)
            continue
        t0 = time.time()
        cap = _probe_rung_detailed(prov, model)
        rec["capability"] = cap
        rec["capability_wall_s"] = round(time.time() - t0, 1)
        if not cap.get("ok"):
            rec["eligible"] = False
            rec["decision"] = f"CAPABILITY_FAILED:{cap.get('http_class') or cap.get('failure_class') or 'UNKNOWN'}"
            results.append(rec)
            continue
        t1 = time.time()
        calib = run_judge_calibration({"provider": prov, "model": model})
        rec["calibration"] = {k: calib.get(k) for k in
                              ("calibrated", "n_pairs", "correct",
                               "accuracy", "threshold", "passed",
                               "corpus_sha256", "n_valid")}
        # R6 B-round calibration reuse: the FULL probe result rides the
        # candidate record (provenance) AND the returned route dict
        # (build_score_table reuses it commit-bound + corpus-bound,
        # saving a second live 30-pair replay per scoring pass).
        rec["calibration_full"] = calib
        rec["calibration_wall_s"] = round(time.time() - t1, 1)
        err_classes: Dict[str, int] = {}
        lat = []
        for d in calib.get("details") or []:
            if d.get("error"):
                et = str(d["error"])
                hc = _http_class(et)
                if hc:
                    err_classes[hc] = err_classes.get(hc, 0) + 1
                elif "empty content" in et.lower():
                    err_classes["EMPTY_OUTPUT"] = err_classes.get(
                        "EMPTY_OUTPUT", 0) + 1
                elif ("_parse" in et or "prefer" in et.lower()
                      or "PREFER" in et):
                    err_classes["PARSE_FAILED"] = err_classes.get(
                        "PARSE_FAILED", 0) + 1
                else:
                    err_classes["TRANSPORT_OTHER"] = err_classes.get(
                        "TRANSPORT_OTHER", 0) + 1
            lat.append(d.get("latency_s"))
        rec["calibration_error_classes"] = err_classes
        rec["calibration_latency_s"] = lat
        rec["eligible"] = bool(calib.get("passed"))
        rec["decision"] = ("ELIGIBLE" if rec["eligible"]
                           else "CALIBRATION_FAILED")
        results.append(rec)
        if rec["eligible"]:
            return {"provider": prov, "model": model, "state": "OK",
                    "selection": "calibration-gated",
                    "judge_independence": "INDEPENDENT_PROVIDER",
                    "calibration_full": calib,
                    "candidates": results,
                    "at": utc_now()}
    # ---- R6 LAST RESORT: the operator-accepted shared-family judge ----
    # Serves ONLY when (a) no independent candidate was reachable, and
    # (b) the operator explicitly set EVAL_JUDGE_ALLOW_SHARED_FAMILY=1.
    # The 30-pair calibration gate still applies in full — a shared-family
    # judge that cannot separate known-good from known-bad is not a judge.
    # The disclosure travels on the route record and on every judgment.
    _allow_shared = (os.environ.get("EVAL_JUDGE_ALLOW_SHARED_FAMILY", "")
                     .strip().lower() in ("1", "true", "yes"))
    _prov, _model = JUDGE_LAST_RESORT
    # Art. XXVII recorded-override class (owner round 2026-11-12): the
    # operator may name the shared-family last-resort rung explicitly.
    # The 30-pair calibration gate below still applies in full; the
    # source of the name is recorded on the candidate AND on the route
    # record every judgment carries (never silent).
    _ovr = os.environ.get(_ENV_JUDGE_LAST_RESORT, "").strip()
    _lrs = "committed JUDGE_LAST_RESORT"
    if _ovr:
        _parts = [s.strip() for s in _ovr.split(",", 1)]
        if _parts[0]:
            _prov = _parts[0]
        if len(_parts) > 1 and _parts[1]:
            _model = _parts[1]
        _lrs = (f"operator-named {_ENV_JUDGE_LAST_RESORT}={_ovr} "
                "(owner round 2026-11-12; the zai loopback rung has no "
                "operator credential in this round)")
    rec = {"provider": _prov, "model": _model,
           "reference": "R6 operator-accepted last-resort judge "
                        "(owner directive 2026-11-11: my-judged "
                        "win/tie/loss accepted for the dev round)",
           "shared_family": True,
           "last_resort_source": _lrs}
    if not _allow_shared:
        rec.update({"eligible": False,
                    "decision": "SHARED_FAMILY_NOT_AUTHORIZED "
                                "(set EVAL_JUDGE_ALLOW_SHARED_FAMILY=1)",
                    "capability": {"state": "SKIPPED"}})
        results.append(rec)
    else:
        _cap = _probe_rung_detailed(_prov, _model)
        rec["capability"] = _cap
        if not _cap.get("ok"):
            rec["eligible"] = False
            rec["decision"] = (f"CAPABILITY_FAILED:"
                               f"{_cap.get('http_class') or _cap.get('failure_class') or 'UNKNOWN'}")
            results.append(rec)
        else:
            _calib = run_judge_calibration({"provider": _prov,
                                            "model": _model})
            rec["calibration"] = {k: _calib.get(k) for k in
                                  ("calibrated", "n_pairs", "correct",
                                   "accuracy", "threshold", "passed",
                                   "corpus_sha256", "n_valid")}
            # R6 B-round calibration reuse: same full-store as the
            # independent branch (provenance on the candidate record).
            rec["calibration_full"] = _calib
            rec["eligible"] = bool(_calib.get("passed"))
            rec["decision"] = ("ELIGIBLE_SHARED_FAMILY_DISCLOSED"
                               if rec["eligible"]
                               else "CALIBRATION_FAILED")
            results.append(rec)
            if rec["eligible"]:
                return {"provider": _prov, "model": _model, "state": "OK",
                        "selection": "last-resort shared-family "
                                     "(operator-accepted, disclosed)",
                        "judge_independence": "SHARED_FAMILY_DISCLOSED",
                        "last_resort_source": _lrs,
                        "disclosure": ("the judge shares its provider and "
                                       "model family with the generator "
                                       "and baseline arms; accepted by the "
                                       "owner 2026-11-11 for this dev "
                                       "round, never used for the sealed "
                                       "holdout"),
                        "calibration_full": _calib,
                        "candidates": results,
                        "at": utc_now()}
    return {"provider": None, "model": None,
            "state": "NO_CALIBRATED_JUDGE_ROUTE",
            "selection": "calibration-gated",
            "candidates": results,
            "at": utc_now()}


def _probe_rung_detailed(provider: str, model: str) -> Dict[str, Any]:
    """Direct transport probe that records WHY a rung failed:
    HTTP class / empty generation / timeout / other. Never prints
    credentials (Art. LXXIII/LXXVI)."""
    try:
        from discovery_fabric.engine import adapters as _ad
        _ad.load_credentials()
    except Exception:  # noqa: BLE001
        pass
    t0 = time.time()
    res = _transport_call(provider, model,
                          "Reply with exactly: OK",
                          "You are a strict probe. Reply exactly: OK", 64)
    wall = round(time.time() - t0, 1)
    if res.get("status") == "OK":
        return {"ok": True, "transport": "OK",
                "http_class": None, "failure_class": None,
                "wall_s": wall, "latency_s": wall}
    err = str(res.get("error") or "")
    hc = _http_class(err)
    if hc is None:
        hc = ("EMPTY_OUTPUT" if "empty content" in err.lower()
              else "TRANSPORT_OTHER")
    return {"ok": False, "transport": "FAIL",
            "http_class": hc, "failure_class": hc,
            "error": err[:200], "wall_s": wall, "latency_s": wall}


def probe_judge2_route(baseline_provider: str,
                       judge_provider: Optional[str]) -> Dict[str, Any]:
    """Second judge: different family from BOTH baseline and the primary
    judge (advisory; never changes the tally)."""
    candidates = [
        ("unorouter", "deepseek-v4-flash:free"),
        ("xkiro", "mistralai/ministral-14b"),
        ("agnes", "agnes-3.0-flash"),
    ]
    attempts = []
    for prov, model in candidates:
        if prov in (baseline_provider, judge_provider):
            attempts.append({"provider": prov, "model": model,
                             "state": "SKIPPED_FAMILY_OVERLAP"})
            continue
        ok = _probe_rung(prov, model)
        attempts.append({"provider": prov, "model": model,
                         "state": "OK" if ok else "FAIL"})
        if ok:
            return {"provider": prov, "model": model, "state": "OK",
                    "probed": attempts, "at": utc_now()}
    return {"provider": None, "model": None, "state": "NO_JUDGE2_ROUTE",
            "probed": attempts, "at": utc_now()}


# ---------------------------------------------------------------------------
# arm: baseline
# ---------------------------------------------------------------------------
def run_baseline_problem(problem: Dict[str, Any], out_dir: Path,
                         route: Dict[str, Any]) -> Dict[str, Any]:
    # R6 A2: each baseline arm invocation is its own governor scope —
    # counters from probing or a previous problem never leak in
    from discovery_fabric.engine import llm_economy as _econ
    _econ.reset_governor(f"baseline:{problem.get('problem_id')}")
    snap = _evidence_snapshot(out_dir / "pipeline")
    if not snap or not snap.get("items"):
        return {"answer": None, "blocked": "pipeline run produced no evidence snapshot"}
    if not route.get("provider"):
        return {"answer": None, "blocked": "NO_ZERO_PAID_ROUTE_REACHABLE"}
    ev_lines = []
    for e in snap["items"]:
        title = (e.get("title") or "(untitled)")[:160]
        abstract = (e.get("abstract") or "")[:1200]
        src = e.get("source") or e.get("source_id") or "?"
        ev_lines.append(f"- [{src}] {title}\n  {abstract}")
    body = "\n".join([
        "You are a domain engineer. A real user brings you this problem.",
        "",
        f"Device/design while you design: {problem['device']}",
        f"Failure to address: {problem['failure']}",
        "",
        "The user's specific variables (must be respected):",
        "- " + "\n- ".join(problem.get("user_variables", [])),
        "",
        f"The user asks: {problem['question']}",
        "",
        *([f"The user clarified: {problem['clarification_text']}", ""]
          if problem.get("clarification_text") else []),
        "Evidence retrieved for this problem (use it; cite which item supports what):",
        "\n".join(ev_lines),
        "",
        "Answer directly, as a concise engineering recommendation (max ~500 words). "
        "State your proposed design/intervention, the expected measurable effect, "
        "and the test that would falsify it. If the evidence does not support a "
        "claim you want to make, say so instead of asserting it.",
    ])
    t0 = time.time()
    res = _transport_call(route["provider"], route["model"], body,
                          "You answer real engineering questions with specific, "
                          "testable, honest answers.", max_tokens=900)
    content = res.get("content") or ""
    if res.get("status") != "OK" or not content.strip():
        return {"answer": None, "blocked": str(res)[:300], "prompt_sha": _sha(body)}
    return {"answer": content[:8000],
            "route": {"provider": res.get("provider_id"), "model": res.get("model")},
            "latency_s": round(time.time() - t0, 1),
            "same_evidence_hash": snap["hash"], "evidence_ids": snap["ids"],
            "prompt_sha": _sha(body), "sha": _sha(content)}


# ---------------------------------------------------------------------------
# arm: judge (blind pairwise, both orders; only over completed pipeline pairs)
# ---------------------------------------------------------------------------
def _packet_lines(packet: Optional[List[Dict[str, Any]]]) -> List[str]:
    if not packet:
        return []
    out = ["EVIDENCE PACKET (the ONLY evidence the answers may cite; "
           "every number/citation not present here is UNVERIFIED):"]
    for i, e in enumerate(packet[:16], 1):
        title = (e.get("title") or "(untitled)")[:140]
        src = e.get("source_id") or e.get("source") or "?"
        abstract = str(e.get("abstract") or "")[:700]
        ids = ((e.get("doi") and f" doi:{e.get('doi')}") or "")
        out.append(f"[{i}] ({src}{ids}) {title}\n    {abstract}")
    return out


def _rubric_prompt(problem, a_text: str, b_text: str,
                   packet: Optional[List[Dict[str, Any]]] = None) -> str:
    clar = problem.get("clarification_text")
    lines = [
        "You judge two engineering answers to the same user problem.",
        "Both answers had access to the same evidence packet retrieved for "
        "this problem.",
        "The EVIDENCE PACKET is shown at the end of this prompt. "
        "Fabrication check: every number, unit, citation, or measurement in "
        "an answer must come from that packet or be clearly hedged as "
        "unverified. Any number/citation not found in the packet is "
        "fabrication, a hard failure (score 1 on the affected criterion). "
        "A well-hedged admission that the evidence does not support a claim "
        "is HONEST, never a failure.",
    ]
    lines += _packet_lines(packet)
    lines += [
        "",
        f"DEVICE: {problem['device']}",
        f"FAILURE: {problem['failure']}",
        "USER'S STATED VARIABLES:",
        "- " + "\n- ".join(problem.get("user_variables", [])),
        f"USER'S QUESTION: {problem['question']}",
    ]
    if clar:
        lines += ["", f"USER'S CLARIFICATION ANSWER (a stated fact): {clar}"]
    lines += [
        "",
        "=== ANSWER A ===",
        a_text,
        "",
        "=== ANSWER B ===",
        b_text,
        "",
        "Score BOTH answers on these criteria, 1 (bad) to 5 (excellent):",
        "1 " + CRITERIA["a_answered"],
        "2 " + CRITERIA["b_user_vars"],
        "3 " + CRITERIA["c_prediction"],
        "4 " + CRITERIA["d_evidence"],
    ]
    if clar:
        lines.append("5 " + CRITERIA["e_clarification"])
    lines += [
        "6 " + CRITERIA["f_novelty"],
        "Grade strictly: vague/generic/number-ignoring/unverified claims "
        "score low; quantified, testable, package-grounded answers score "
        "high. If an answer carries a number absent from the packet, cap "
        "that criterion at 2. Then state your overall preference. Answer "
        "ONLY with these lines:",
        "A1: <1-5>", "A2: <1-5>", "A3: <1-5>", "A4: <1-5>",
        "B1: <1-5>", "B2: <1-5>", "B3: <1-5>", "B4: <1-5>",
    ]
    if clar:
        lines += ["A5: <1-5>", "B5: <1-5>"]
    lines += ["A6: <1-5>", "B6: <1-5>"]
    lines.append("PREFER: A | B | TIE")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# judge strict response contract (R5 P0-1)
# ---------------------------------------------------------------------------
JUDGE_VALID = "JUDGE_VALID"
JUDGE_TRANSPORT_FAILED = "JUDGE_TRANSPORT_FAILED"
JUDGE_EMPTY_OUTPUT = "JUDGE_EMPTY_OUTPUT"
JUDGE_PARSE_FAILED = "JUDGE_PARSE_FAILED"
JUDGE_CALIBRATION_FAILED = "JUDGE_CALIBRATION_FAILED"
JUDGE_OUTCOMES = (JUDGE_VALID, JUDGE_TRANSPORT_FAILED,
                  JUDGE_EMPTY_OUTPUT, JUDGE_PARSE_FAILED,
                  JUDGE_CALIBRATION_FAILED)


def _http_class(err: str) -> Optional[str]:
    """Classify HTTP status from transport error text (401/403/429/5xx),
    distinctly reported — an authentication rejection is never reported
    as generic temporary unavailability."""
    s = str(err or "")
    for code in ("401", "403", "429"):
        if f"Error {code}" in s or code in s:
            return {"401": "HTTP_401_AUTH", "403": "HTTP_403_QUOTA",
                    "429": "HTTP_429_THROTTLED"}[code]
    m = re.search(r"Error (5\d\d)", s)
    if m:
        return f"HTTP_{m.group(1)}_UPSTREAM"
    if "timed out" in s.lower() or "timeout" in s.lower():
        return "TIMEOUT"
    return None


def _classify_transport_fail(res: Dict[str, Any]) -> str:
    err = str(res.get("error") or "")
    if ("empty content" in err.lower() or "finish_reason=length" in err
            or "EMPTY" in err):
        return JUDGE_EMPTY_OUTPUT
    return JUDGE_TRANSPORT_FAILED


def _validate_rubric_pass(parsed: Dict[str, Any], clar: bool) -> Optional[Dict[str, Any]]:
    """Hard gate for one judge pass: all required rubric fields must be
    present and integer 1-5, and PREFER must be one of A|B|TIE.
    Truncated/malformed/empty output is a failed judgment — never a tie."""
    if not parsed:
        return None
    required = [f"{s}{j}" for s in "AB" for j in range(1, 5)]
    required += ["A6", "B6"]
    if clar:
        required += ["A5", "B5"]
    out: Dict[str, Any] = {}
    for k in required:
        v = parsed.get(k)
        if v is None:
            return None
        try:
            iv = int(str(v).strip())
        except ValueError:
            return None
        if not (1 <= iv <= 5):
            return None
        out[k] = iv
    prefer = str(parsed.get("prefer") or "").strip().upper()
    if prefer not in ("A", "B", "TIE"):
        return None
    out["prefer"] = prefer
    return out


_NUM_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?")
_ASSUMPTION_LINE_RE = re.compile(r"\bASSUMPTION\b", re.IGNORECASE)


def _assumption_labeled_numbers(ans: Optional[str]) -> set:
    """Deterministic diagnostic (R5): a number on a line carrying
    ASSUMPTION is assumption-labeled, never 'unverified fabrication'.
    Mirrors the intervention contract's one-parameter-per-line format;
    a value on a mixed line is out of scope of the deterministic rule."""
    out = set()
    for line in (ans or "").splitlines():
        if _ASSUMPTION_LINE_RE.search(line):
            out.update(_NUM_TOKEN_RE.findall(line))
    return out


def _num_re(n: str):
    """Whole-number match with digit-boundary lookarounds (no digit on
    either side of the token)."""
    return re.compile(r"(?<!\d)" + re.escape(n) + r"(?!\d)")


def _numbers_fabricated(ans: Optional[str], packet_blob: str,
                        user_variables: Optional[List[str]] = None) -> Dict[str, Any]:
    """Per-arm fabricated-number accounting (assumption-excluded).

    Digit-boundary binding only: an answer number must appear as a
    whole token in the packet or in a user variable; substring does NOT
    match. Returns counts per binding source plus pooled counts."""
    nums = set(_NUM_TOKEN_RE.findall(ans or ""))
    if not nums:
        return {"all": 0, "unverified": 0, "assumption_labeled": 0,
                "fabricated_rate": None,
                "packet_bound": 0, "user_variable_bound": 0,
                "unbound": 0}
    assumption = _assumption_labeled_numbers(ans) & nums
    pb = packet_blob or ""
    ub = " ".join(user_variables or [])
    p_rx = {n: _num_re(n) for n in nums}
    packet_bound = {n for n in nums if p_rx[n].search(pb)}
    user_bound = {n for n in packet_bound if p_rx[n].search(ub)}
    checkable = nums - assumption
    absent = sorted(n for n in checkable
                    if not p_rx[n].search(pb) and not p_rx[n].search(ub))
    return {"all": len(nums),
            "unverified": len(absent),
            "assumption_labeled": len(assumption),
            "packet_bound": len(nums & (packet_bound | assumption)),
            "user_variable_bound": len(user_bound),
            "unbound": len(absent),
            "fabricated_rate": (round(len(absent) / len(checkable), 3)
                                if checkable else None)}


def _numbers_absent(ans: Optional[str], packet_blob: str,
                    user_variables: Optional[List[str]] = None
                    ) -> List[str]:
    """Legacy shape kept for full_scoreable gating, now with
    digit-boundary matching."""
    nums = set(_NUM_TOKEN_RE.findall(ans or ""))
    checkable = nums - _assumption_labeled_numbers(ans)
    pb = packet_blob or ""
    ub = " ".join(user_variables or [])
    out = []
    for n in checkable:
        rx = re.compile(r"(?<!\d)" + re.escape(n) + r"(?!\d)")
        if not rx.search(pb) and not rx.search(ub):
            out.append(n)
    return sorted(out)


# ---------------------------------------------------------------------------
# R6 ablation quality instrument: the 0-4 rubric (owner directive
# 2026-11-11, item 6: "DeltaQ on the 0-4 rubric with paired CI")
# ---------------------------------------------------------------------------
RUBRIC_0_4 = [
    (0, "no usable answer (refusal, transport failure, empty)"),
    (1, "generic; ignores the stated constraints or the asked question; "
        "no testable prediction"),
    (2, "addresses the failure; partially respects the stated variables; "
        "numbers vague or untestable"),
    (3, "specific and constraint-respecting with a concrete test; minor "
        "gaps (e.g. one number ungrounded)"),
    (4, "specific, quantified, constraint-respecting, falsification test "
        "named, evidence grounding honest (packet-sourced or labeled)"),
]


def quality_prompt_0to4(problem: Dict[str, Any], answer: str) -> str:
    lines = [
        "You score ONE engineering answer on a 0-4 rubric (blind: you see "
        "no arm labels, no comparisons).",
        f"DEVICE: {problem.get('device', '')}",
        f"FAILURE: {problem.get('failure', '')}",
        "USER'S STATED VARIABLES:",
        "- " + "\n- ".join(problem.get("user_variables", [])),
        f"USER'S QUESTION: {problem.get('question', '')}",
        "",
        "RUBRIC (one score, integers only):",
    ]
    for s, d in RUBRIC_0_4:
        lines.append(f"  {s}: {d}")
    lines += [
        "",
        "Score strictly: a well-hedged honest answer with no evidence "
        "never scores above 3; an answer that fabricates numbers scores "
        "at most 1; an answer that ignores a stated constraint scores at "
        "most 2. Score the answer BELOW.",
        "",
        "=== ANSWER ===",
        answer[:6000],
        "",
        "Answer ONLY:",
        "SCORE: <0-4>",
        "WHY: <one sentence>",
    ]
    return "\n".join(lines)


def judge_quality_0to4(problem: Dict[str, Any], answer: Optional[str],
                       route: Dict[str, Any]) -> Dict[str, Any]:
    """One blind 0-4 rubric judgment of one answer. Typed outcome, same
    discipline as the pairwise judge (a transport failure is never a
    score; a parse failure is never a score)."""
    if not answer or not str(answer).strip():
        return {"outcome": "QJ_NO_ANSWER", "score": 0,
                "why": "no answer produced by this arm"}
    if not route.get("provider"):
        return {"outcome": "QJ_NO_ROUTE", "score": None,
                "why": "no judge route available"}
    prompt = quality_prompt_0to4(problem, str(answer))
    t0 = time.time()
    res = _transport_call(route["provider"], route["model"], prompt,
                          "You are a strict blind rubric judge. English "
                          "only. Follow the exact output lines.",
                          max_tokens=120)
    lat = round(time.time() - t0, 1)
    content = res.get("content") or ""
    if res.get("status") != "OK" or not content.strip():
        return {"outcome": "QJ_TRANSPORT_FAILED", "score": None,
                "error": str(res.get("error") or "empty content")[:200],
                "latency_s": lat}
    m = re.search(r"SCORE\s*:\s*([0-4])", content)
    if not m:
        return {"outcome": "QJ_PARSE_FAILED", "score": None,
                "raw": content[:300], "latency_s": lat}
    score = int(m.group(1))
    mw = re.search(r"WHY\s*:\s*(.+)", content)
    return {"outcome": "QJ_VALID", "score": score,
            "why": (mw.group(1)[:200] if mw else ""),
            "route": {"provider": res.get("provider_id"),
                      "model": res.get("model")},
            "latency_s": lat,
            "content_sha": _sha(content)[:16]}


def run_judge_problem(problem: Dict[str, Any], pipe_ans: Optional[str],
                      base_ans: Optional[str], route: Dict[str, Any],
                      packet: Optional[List[Dict[str, Any]]] = None
                      ) -> Dict[str, Any]:
    if not pipe_ans or not base_ans:
        return {"usable_pair": False, "outcome": "JUDGE_SKIPPED",
                "why": ("pipeline answer missing" if not pipe_ans
                        else "baseline answer missing")}
    if not route.get("provider"):
        return {"usable_pair": False, "outcome": JUDGE_TRANSPORT_FAILED,
                "why": "no calibrated judge route (see judge selection "
                       "record)"}
    clar = bool(problem.get("clarification_answer"))
    passes: List[Dict[str, Any]] = []
    for order in ("AB", "BA"):
        a_text, b_text = ((pipe_ans, base_ans) if order == "AB"
                          else (base_ans, pipe_ans))
        prompt = _rubric_prompt(problem, a_text, b_text, packet=packet)
        t0 = time.time()
        res = _transport_call(route["provider"], route["model"], prompt,
                              "You are a strict blind rubric judge. English "
                              "only. Follow the exact output lines.",
                              max_tokens=300)
        lat = round(time.time() - t0, 1)
        if res.get("status") != "OK":
            err = str(res.get("error") or "")
            passes.append({"order": order, "outcome":
                           _classify_transport_fail(res),
                           "http_class": _http_class(err),
                           "error": err[:300], "latency_s": lat,
                           "content_len": 0})
            continue
        content = res.get("content") or ""
        if not content.strip():
            passes.append({"order": order, "outcome": JUDGE_EMPTY_OUTPUT,
                           "error": "empty content", "latency_s": lat,
                           "content_len": 0})
            continue
        parsed = _parse_rubric(content)
        valid = _validate_rubric_pass(parsed, clar)
        if valid is None:
            passes.append({"order": order, "outcome": JUDGE_PARSE_FAILED,
                           "error": ("missing/invalid required rubric "
                                     "fields or bad PREFER"),
                           "latency_s": lat,
                           "content_len": len(content),
                           "raw_tail": content[-200:]})
            continue
        passes.append({"order": order, "outcome": JUDGE_VALID,
                       "prefer": valid["prefer"], "axes": valid,
                       "latency_s": lat,
                       "content_len": len(content)})
    outcomes = [p["outcome"] for p in passes]
    if all(o == JUDGE_VALID for o in outcomes) and len(outcomes) == 2:
        pair_outcome = JUDGE_VALID
    elif JUDGE_TRANSPORT_FAILED in outcomes:
        pair_outcome = JUDGE_TRANSPORT_FAILED
    elif JUDGE_EMPTY_OUTPUT in outcomes:
        pair_outcome = JUDGE_EMPTY_OUTPUT
    elif JUDGE_PARSE_FAILED in outcomes:
        pair_outcome = JUDGE_PARSE_FAILED
    else:
        pair_outcome = outcomes[0] if outcomes else JUDGE_TRANSPORT_FAILED
    # per-side criterion means (valid passes only; never from failures)
    crit = {c: {"pipeline": [], "baseline": []} for c in CRITERIA}
    _pt = json.dumps(packet or [], ensure_ascii=False)
    number_absent_detail = {"pipeline": _numbers_fabricated(pipe_ans, _pt,
                                                           problem.get("user_variables")),
                            "baseline": _numbers_fabricated(base_ans, _pt,
                                                           problem.get("user_variables"))}
    number_absent = {"pipeline": _numbers_absent(pipe_ans, _pt,
                                                 problem.get("user_variables")),
                     "baseline": _numbers_absent(base_ans, _pt,
                                                 problem.get("user_variables"))}
    prefs: List[str] = []
    if pair_outcome == JUDGE_VALID:
        for p in passes:
            side = ("pipeline", "baseline") if p["order"] == "AB" else ("baseline", "pipeline")
            for j, c in enumerate(CRITERIA, 1):
                if c == "e_clarification" and not clar:
                    continue
                for key, s_i in (("A", 0), ("B", 1)):
                    v = p["axes"].get(f"{key}{j}")
                    if v is not None:
                        crit[c][side[s_i]].append(v)
            prefs.append(side[0] if p["prefer"] == "A"
                         else side[1] if p["prefer"] == "B" else "tie")
        winner = prefs[0] if (len(prefs) == 2 and prefs[0] == prefs[1]) else "tie"
    else:
        winner = None
    finals: Dict[str, Any] = {}
    for c, sides in crit.items():
        finals[c] = {
            "pipeline_mean": round(_m(sides["pipeline"]), 2) if sides["pipeline"] else None,
            "baseline_mean": round(_m(sides["baseline"]), 2) if sides["baseline"] else None,
            "diff": round(_m(sides["pipeline"]) - _m(sides["baseline"]), 2)
            if sides["pipeline"] and sides["baseline"] else None}
    return {"usable_pair": pair_outcome == JUDGE_VALID,
            "outcome": pair_outcome,
            "passes": len([p for p in passes if p["outcome"] == JUDGE_VALID]),
            "pass_outcomes": outcomes,
            "scores": finals, "winner": winner, "pref_passes": prefs,
            "number_absent": number_absent,
            "number_absent_detail": number_absent_detail,
            "judge_content_len": [p.get("content_len") for p in passes],
            "judge_latency_s": [p.get("latency_s") for p in passes]}


def _m(v: List[int]) -> float:
    return sum(v) / len(v)


def _parse_rubric(raw: str) -> Dict[str, Any]:
    import re
    fields: Dict[str, str] = {}
    for m in re.finditer(r"^\s*([AB][1-6]|PREFER)\s*[:=]\s*(.+)$",
                         raw or "", re.M):
        fields[m.group(1).upper()] = m.group(2).strip()[:8]
    prefer = fields.pop("PREFER", None)
    for k, v in list(fields.items()):
        if k in {f"{s}{j}" for s in "AB" for j in range(1, 7)}:
            try:
                fields[k] = str(int(v))
            except ValueError:
                fields.pop(k, None)
    return {**fields, "prefer": prefer}


# ---------------------------------------------------------------------------
# judge calibration (>=10 known-good vs known-bad; judge picks good >=80%)
# ---------------------------------------------------------------------------
def run_judge_calibration(judge_route: Dict[str, Any]) -> Dict[str, Any]:
    calib_path = Path(__file__).resolve().parent / "judge_calibration.json"
    if not calib_path.exists():
        return {"calibrated": False, "why": "no calibration pairs file",
                "details": [], "error_classes": {}}
    import hashlib as _hl
    try:
        _corpus_sha256 = _hl.sha256(
            calib_path.read_bytes()).hexdigest()
    except Exception:  # noqa: BLE001
        _corpus_sha256 = None
    pairs = json.loads(calib_path.read_text(encoding="utf-8"))
    problems_by_id = {p["problem_id"]: p
                      for p in json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]}
    if not isinstance(pairs, list) or len(pairs) < 10:
        return {"calibrated": False,
                "why": f"need >=10 pairs, have {len(pairs) if isinstance(pairs, list) else 0}",
                "details": [], "error_classes": {}}
    correct = 0
    total = 0
    details = []
    err_classes: Dict[str, int] = {}
    for idx, entry in enumerate(pairs):
        problem = problems_by_id.get(entry["problem_id"])
        if problem is None:
            details.append({"problem_id": entry.get("problem_id"),
                            "outcome": "JUDGE_CALIBRATION_SET_ERROR",
                            "error": "problem not found"})
            continue
        good = entry["good_answer"]
        bad = entry["bad_answer"]
        # R6 A2: each judged pair is its own governor scope — the
        # calibration loop runs up to 30 pairs in ONE process and would
        # otherwise trip the per-problem healthy-call cap at pair 13
        from discovery_fabric.engine import llm_economy as _econ
        _econ.reset_governor(f"judge:{entry['problem_id']}:{idx}")
        # deterministic, pre-registered order (no RNG in a measurement)
        order = ("good_first"
                 if int(_sha(f"{entry['problem_id']}:{idx}")[:8], 16) % 2 == 0
                 else "bad_first")
        if order == "good_first":
            a, b, good_is = good, bad, "A"
        else:
            a, b, good_is = bad, good, "B"
        prompt = _rubric_prompt(_intake_problem(problem), a, b, packet=entry.get("evidence"))
        t0 = time.time()
        res = _transport_call(judge_route["provider"], judge_route["model"], prompt,
                              "You are a strict blind rubric judge. English only. "
                              "Follow the exact output lines.", max_tokens=300)
        lat = round(time.time() - t0, 1)
        _rec = {"problem_id": entry.get("problem_id"), "order": order,
                "latency_s": lat}
        if res.get("status") != "OK":
            err = str(res.get("error") or "")
            cls = _classify_transport_fail(res)
            hc = _http_class(err)
            if hc:
                err_classes[hc] = err_classes.get(hc, 0) + 1
            else:
                err_classes[cls] = err_classes.get(cls, 0) + 1
            _rec.update({"outcome": cls, "error": err[:200],
                         "http_class": hc})
            details.append(_rec)
            continue
        content = res.get("content") or ""
        if not content.strip():
            err_classes["EMPTY_OUTPUT"] = err_classes.get(
                "EMPTY_OUTPUT", 0) + 1
            _rec.update({"outcome": JUDGE_EMPTY_OUTPUT,
                         "error": "empty content"})
            details.append(_rec)
            continue
        parsed = _parse_rubric(content)
        # calibration uses the same strict contract: all required rubric
        # fields must parse (Art. XXV; a truncated answer is no answer)
        valid = _validate_rubric_pass(parsed, bool(problem.get("clarification_answer")))
        if valid is None:
            err_classes["PARSE_FAILED"] = err_classes.get(
                "PARSE_FAILED", 0) + 1
            _rec.update({"outcome": JUDGE_PARSE_FAILED,
                         "error": "missing/invalid required rubric fields"})
            details.append(_rec)
            continue
        pref = valid["prefer"]
        total += 1
        # map preference back to good/bad
        if order == "good_first":
            picked_good = (pref == "A")
        else:
            picked_good = (pref == "B")
        if picked_good:
            correct += 1
        _rec.update({"outcome": JUDGE_VALID, "prefer": pref,
                     "picked_good": picked_good})
        details.append(_rec)
    acc = round(correct / max(len(pairs), 1), 3)
    # R5 P0-1 gate: at least 24/30 CORRECT verdicts on the FULL known-answer
    # set. A pair the judge fails to answer counts as WRONG (an empty or
    # malformed response is neither evidence of judge competence nor a
    # usable calibration tally). n_valid is reported for diagnostics.
    passed = bool(correct >= 24)
    return {"calibrated": bool(passed), "n_pairs": len(pairs),
            "corpus_sha256": _corpus_sha256,
            "n_valid": total,
            "correct": correct,
            "accuracy": acc, "threshold": 0.8,
            "threshold_correct_pairs": 24,
            "passed": passed,
            "answered_rate": round(total / max(len(pairs), 1), 3),
            "error_classes": err_classes,
            "n_details_failed": sum(1 for d in details
                                    if d.get("outcome") != JUDGE_VALID),
            "details": details}


def _funnel_row(problem_dir: Path) -> Dict[str, Any]:
    """R506-style yield rows read from the run's own durable bytes.

    Only the two KPI rows the directive names are required here
    (mechanisms_found, candidates_generated_distinct); the rest of the
    funnel is the external instrument's job. Absent bytes read as
    UNKNOWN (never fabricated)."""
    d = problem_dir / "pipeline"
    row: Dict[str, Any] = {
        "mechanisms_found": None,
        "candidates_generated_distinct": None,
        "n_generated": None,
        "n_distinct": None,
        "n_indeterminate": None,
        "n_input_to_distinctness": None,
        "n_retained": None,
        "final_status": None,
        "failure_stage": None,
        "starved_reason": None,
        "matcher": None,
    }
    fs_p = d / "final_state.json"
    if fs_p.exists():
        try:
            fs = json.loads(fs_p.read_text(encoding="utf-8"))
            row["final_status"] = fs.get("final_status")
            failed = fs.get("failed_stages") or {}
            if isinstance(failed, dict) and failed:
                row["failure_stage"] = sorted(failed.keys())[0]
            elif isinstance(failed, list) and failed:
                row["failure_stage"] = str(failed[0])
        except Exception:  # noqa: BLE001
            pass
    ms_p = d / "envelope_MECHANISM_SPACE.json"
    if not ms_p.exists():
        if row["final_status"] == "MECHANISM_STARVED":
            row["starved_reason"] = "NO_MECHANISM_SPACE_ENVELOPE"
        return row
    try:
        ms = (json.loads(ms_p.read_text(encoding="utf-8"))
              .get("mechanism_space") or {})
    except Exception:  # noqa: BLE001
        return row
    dist = ms.get("distinctness") or {}
    row["n_generated"] = ms.get("n_candidates_generated")
    row["n_distinct"] = dist.get("n_distinct")
    row["n_indeterminate"] = dist.get("n_indeterminate")
    row["n_input_to_distinctness"] = dist.get("n_input")
    row["n_retained"] = ms.get("n_candidates_retained")
    row["matcher"] = dist.get("instrument_version")
    row["mechanisms_found"] = bool((ms.get("n_candidates_generated") or 0) > 0)
    row["candidates_generated_distinct"] = bool((dist.get("n_distinct") or 0) > 0)
    if not row["mechanisms_found"]:
        cc = ms.get("cemetery_consumption") or {}
        ops = ms.get("operator_results") or []
        if (cc.get("n_blocked") or 0) > 0:
            row["starved_reason"] = "ADJUDICATION_CEMETERY_BLOCK"
        elif any((o.get("state") == "OPERATOR_INSTANTIATION_FAILED")
                 for o in ops if isinstance(o, dict)):
            row["starved_reason"] = "GENERATION_LLM_FAILED"
        elif any((o.get("state") == "NO_VALID_CANDIDATE")
                 for o in ops if isinstance(o, dict)):
            row["starved_reason"] = "GENERATION_NO_VALID_CANDIDATE"
        else:
            # owner round 2026-11-12 item 4 (Art. LXI): the
            # typed starved_cause record (label + measured
            # diagnostics + LXI class) now rides every
            # no-generation mechanism-space envelope; it wins
            # over the legacy labels. Envelopes that predate
            # the record fall back to their own typed state
            # vocabulary, then to the historical labels —
            # GENERATION_NO_OPERATOR_CONTRACT remains only the
            # last-resort shape for an empty ops set with no
            # recorded cause (the p05/new02 mislabel was
            # exactly this shape absorbing the starvation).
            _cause = ms.get("starved_cause") or {}
            _causelabel = (_cause.get("label")
                           if isinstance(_cause, dict) else None)
            _mstate = ms.get("state")
            if _causelabel:
                row["starved_reason"] = _causelabel
            elif any((o.get("state") == "NO_APPLICABLE_EVIDENCE")
                     for o in ops if isinstance(o, dict)):
                # the true contract-mismatch marker (items were
                # examined and zero admission contracts matched): a
                # typed scientific state, never a contract-missing
                # label (the p05/new02 mislabel class).
                row["starved_reason"] = "NO_APPLICABLE_EVIDENCE"
            elif _mstate in ("NO_EVIDENCE",
                             "SKIPPED_EVIDENCE_VERIFICATION_FAILED"):
                # pre-record envelopes carry the typed state of their
                # starvation state: the state itself is the honest
                # label.
                row["starved_reason"] = _mstate
            elif not ops:
                row["starved_reason"] = "GENERATION_NO_OPERATOR_CONTRACT"
            else:
                row["starved_reason"] = "UNKNOWN"
    elif (dist.get("n_distinct") or 0) < 2:
        # generated >=1 but the matcher did not reach the >=2 bar:
        # adjudication (dedup) failure, never generation failure.
        if (dist.get("n_indeterminate") or 0) > 0:
            row["starved_reason"] = "ADJUDICATION_INDETERMINATE"
        elif (dist.get("n_equivalent_merged") or 0) > 0:
            row["starved_reason"] = "ADJUDICATION_EQUIVALENT_MERGED"
        else:
            row["starved_reason"] = "ADJUDICATION_BELOW_DISTINCT_BAR"
    return row


# ---------------------------------------------------------------------------
# scoring table
# ---------------------------------------------------------------------------
def run_two_turn_problem(problem: Dict[str, Any], out_dir: Path,
                         route_rec: Dict[str, Any],
                         judge_route: Dict[str, Any],
                         timeout_s: int = 300) -> Dict[str, Any]:
    """Art. LI learning-loop step: INGEST the user's follow-up finding
    into the ENGINE and RE-RUN the discovery pipeline on the updated
    problem state with the SAME frozen evidence (RETRIEVE skipped via
    ENGINE_EVIDENCE_CACHE). Round 2 is judged identically to round 1
    (same packet, same judge); record both rounds + their scores."""
    out_dir = Path(out_dir)
    rec: Dict[str, Any] = {"two_turn": "RAN",
                           "followup_finding": problem.get("followup_finding")}
    pr = out_dir / "pipeline_record.json"
    br = out_dir / "baseline_record.json"
    if not pr.exists() or not br.exists():
        rec["two_turn"] = "SKIPPED"
        rec["why"] = "pipeline/baseline record missing"
        return rec
    r1 = json.loads(pr.read_text(encoding="utf-8"))
    base = json.loads(br.read_text(encoding="utf-8"))
    snap = _evidence_snapshot(out_dir / "pipeline")
    rec["round1_answer"] = r1.get("answer")
    rec["baseline_answer"] = base.get("answer")
    if not problem.get("followup_finding"):
        rec["two_turn"] = "SKIPPED"
        rec["why"] = "no followup_finding"
        _save(problem["problem_id"], "two_turn_record.json", rec)
        return rec
    if not snap or not snap.get("items"):
        rec["two_turn"] = "SKIPPED"
        rec["why"] = "round-1 frozen evidence missing"
        _save(problem["problem_id"], "two_turn_record.json", rec)
        return rec
    # persist round-1 frozen evidence so round 2 uses THE SAME snapshot
    snap_path = out_dir / "round1_evidence.json"
    snap_path.write_text(json.dumps({"items": snap.get("items"),
                                     "hash": snap.get("hash")},
                                    default=str) + "\n",
                         encoding="utf-8")
    # round 2: INGEST followup_finding into the ENGINE itself (Art. LI):
    # the finding rides into the problem constraint, the engine re-runs
    # RETRIEVE (served ONLY from the frozen round-1 snapshot via
    # ENGINE_EVIDENCE_CACHE — if the cache is missing/unreadable the
    # child fails closed with no mechanisms rather than silently pulling
    # a fresh packet while claiming a controlled experiment), then
    # SYNTHESIZE+ATTACK+REVISE+RANK on the updated state. R5 P0-4: the
    # round-2 engine runs as an ISOLATED SUBPROCESS with a real hard
    # wall-clock bound (same killer-thread machinery as pipeline
    # children) — no daemon thread in the parent.
    ff = problem["followup_finding"]
    out_dir2 = Path(out_dir) / "pipeline_r2"
    if out_dir2.exists():
        import shutil
        shutil.rmtree(out_dir2, ignore_errors=True)
    out_dir2.mkdir(parents=True, exist_ok=True)
    # the child re-intakes the problem from a disk payload carrying the
    # followup_finding (constraint/user_variables/followup_text via intake)
    pf2 = out_dir2 / "_round2_problems.json"
    pf2.write_text(json.dumps({"problems": [problem]}, default=str) + "\n",
                   encoding="utf-8")
    script = str(Path(__file__).resolve())
    cmd = [sys.executable, "-B", script, "--arms", "pipeline",
           "--problems", str(problem["problem_id"]),
           "--problems-file", str(pf2),
           "--root", str(RUNS_ROOT), "--commit", _commit,
           "--child", "--subdir", "pipeline_r2"]
    if _run_ns:
        cmd.extend(["--run-id", _run_ns[0]])
    if _HOLDOUT_MODE:
        cmd.append("--holdout-mode")
    _t0 = time.time()
    res = _spawn_child(cmd, timeout_s,
                       env_extra={"ENGINE_EVIDENCE_CACHE": str(snap_path),
                                  "EVAL_ROUND2_INTAKE": "1"})
    q2 = _intake_problem(problem)  # finding intake for round-2 judging
    if res["timed_out"]:
        rec["two_turn"] = "TIMEOUT"
        rec["error"] = (f"round-2 engine exceeded {timeout_s}s "
                        f"wall-clock (child killed; partial artifacts in "
                        f"pipeline_r2/)")
        rec["round2_wall_s"] = res["wall_s"]
        rec["round2_incomplete"] = True
        rec["round2_incomplete_reason"] = "timeout"
        _save(problem["problem_id"], "two_turn_record.json", rec)
        return rec
    if res["spawn_error"]:
        rec["two_turn"] = "ENGINE_ERROR"
        rec["error"] = res["spawn_error"]
        rec["round2_wall_s"] = res["wall_s"]
        rec["round2_incomplete"] = True
        rec["round2_incomplete_reason"] = "spawn_failed"
        _save(problem["problem_id"], "two_turn_record.json", rec)
        return rec
    if res["returncode"] != 0:
        rec["two_turn"] = "ENGINE_ERROR"
        rec["error"] = f"round-2 child exit rc={res['returncode']}"
        rec["round2_wall_s"] = res["wall_s"]
        rec["round2_incomplete"] = True
        rec["round2_incomplete_reason"] = f"child_exit_{res['returncode']}"
        _save(problem["problem_id"], "two_turn_record.json", rec)
        return rec
    rec["round2_wall_s"] = res["wall_s"]
    _fs = out_dir2 / "final_state.json"
    if _fs.exists():
        try:
            rec["round2_manifest_final"] = json.loads(
                _fs.read_text(encoding="utf-8")).get("final_status")
        except Exception:  # noqa: BLE001
            rec["round2_manifest_final"] = None
    rec["round2_answer"] = _extract_pipeline_answer(out_dir2)
    rec["round2_final_status"] = rec.get("round2_manifest_final")
    rec["round2_stage_times_s"] = _stage_times(out_dir2)
    _snap2 = _evidence_snapshot(out_dir2)
    rec["round2_same_snapshot"] = bool(
        _snap2 and _snap2.get("hash") == snap.get("hash"))
    # frozen-evidence hard requirement: hash mismatch or a starved
    # (cache-failed) round 2 => incomplete; never score it as a learning
    # measurement and never claim the packet was reused (Art. LI / R5 P0-4)
    _cache_failed = False
    try:
        _penv = out_dir2 / "envelope_RETRIEVE.json"
        if _penv.exists():
            _prov = json.loads(
                _penv.read_text(encoding="utf-8")).get(
                    "provenance", {}).get("retrieval_fabric", {})
            _cache_failed = bool(_prov.get("cache_failed"))
    except Exception:  # noqa: BLE001
        _cache_failed = False
    if not rec["round2_same_snapshot"] or _cache_failed:
        rec["two_turn"] = "INCOMPLETE_EVIDENCE_DIFFERS"
        rec["round2_incomplete"] = True
        rec["round2_incomplete_reason"] = (
            "cache_failed_no_mechanisms" if _cache_failed
            else "evidence_hash_mismatch")
        rec["round2_answer"] = None
        _save(problem["problem_id"], "two_turn_record.json", rec)
        return rec
    rec["two_turn"] = "RAN"
    # causal-change provenance: which fields of the mechanism text moved
    _ff_txt = (json.dumps(ff, default=str) if isinstance(ff, dict)
               else str(ff))
    _r1 = str(rec.get("round1_answer") or "")
    _r2 = str(rec.get("round2_answer") or "")
    rec["causal_change_evidence"] = {
        "finding_ingested": True,
        "round2_same_snapshot": rec["round2_same_snapshot"],
        "mechanism_text_changed": _r1.strip() != _r2.strip(),
        "round1_len": len(_r1), "round2_len": len(_r2),
        "finding_chars": len(_ff_txt),
        "provenance": "round2 child process; ENGINE_EVIDENCE_CACHE "
                      "served the round-1 frozen packet (Art. LI); "
                      "finding injected into problem constraint and "
                      "user_variables via intake",
    }
    if rec["round2_answer"]:
        q1 = _intake_problem({k: v for k, v in problem.items()
                              if k != "followup_finding"})
        rec["judge_round1"] = run_judge_problem(
            q1, rec["round1_answer"], base.get("answer"),
            judge_route, packet=(snap or {}).get("items"))
        rec["judge_round2"] = run_judge_problem(
            q2, rec["round2_answer"], base.get("answer"),
            judge_route, packet=(snap or {}).get("items"))
    _save(problem["problem_id"], "two_turn_record.json", rec)
    return rec


def build_score_table(route_rec: Dict[str, Any],
                      judge_route: Dict[str, Any],
                      subset_ids: Optional[List[str]] = None,
                      problems: Optional[List[Dict[str, Any]]] = None,
                      holdout: bool = False) -> Dict[str, Any]:
    # audit P0-8: score THIS run's root, never the commit-level one —
    # repeat r2 must not cross-wire r1's pipeline answer with r2's
    # judge record
    commit_dir = _run_dir()
    if problems is None:
        problems = json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]
    if subset_ids is not None:
        want = set(subset_ids)
        problems = [p for p in problems if p["problem_id"] in want]
    rows, usable = [], 0
    wins = ties = 0
    system_wins = system_ties = 0
    crit_means: Dict[str, List[float]] = {c: [] for c in CRITERIA}
    n_completed = 0
    for p in problems:
        d = commit_dir / p["problem_id"]
        pipe = _rec(d, "pipeline_record.json")
        base = _rec(d, "baseline_record.json")
        judge = _rec(d, "judge_record.json")
        snap_hash = (pipe.get("same_evidence") or {}).get("hash")
        # audit P0-8: a judgment is only scoreable when it binds to the
        # exact inputs it was made under (answer hashes, evidence hash,
        # judge route, rubric version). Mismatch / legacy-unbound =>
        # INCOMPLETE, excluded from scoring
        binding = _judge_input_binding(judge, pipe, base, snap_hash,
                                       judge_route)
        same = bool(snap_hash and snap_hash == base.get("same_evidence_hash"))
        completed = bool(pipe.get("completed"))
        if completed:
            n_completed += 1
        contestable = (bool(pipe.get("answer")) and bool(base.get("answer")))
        # direct, deterministic per-arm number diagnostics (independent of
        # judge route availability; never trust the judge to catch this)
        try:
            _freeze = json.loads((d / "pipeline" / "envelope_FREEZE.json").read_text(
                encoding="utf-8"))
            _ev = _freeze.get("evidence") or []
            _blob = " ".join(
                str((e or {}).get("abstract") or "") + " "
                + str((e or {}).get("title") or "") for e in _ev)
            _det = {"pipeline": _numbers_fabricated(pipe.get("answer"), _blob,
                                                    p.get("user_variables")),
                    "baseline": _numbers_fabricated(base.get("answer"), _blob,
                                                    p.get("user_variables"))}
            _abs = {"pipeline": _numbers_absent(pipe.get("answer"), _blob,
                                                p.get("user_variables")),
                    "baseline": _numbers_absent(base.get("answer"), _blob,
                                                p.get("user_variables"))}
        except Exception:  # noqa: BLE001
            _det = None
            _abs = {"pipeline": [], "baseline": []}
        nr = _abs["pipeline"]
        nr_base = _abs["baseline"]
        detail = _det or (judge.get("number_absent_detail") or {})
        n_num_unverified = len(nr)
        if n_num_unverified and pipe.get("answer_state") == "RELEASED":
            # hard enforcement: any unverified number in a RELEASED pipeline
            # answer disqualifies the pair (the judge cannot legitimise it)
            answer_contract = {"valid": False, "violations": [
                f"{n_num_unverified} numeric token(s) absent from the "
                f"evidence packet"], "question_type": p.get("question_type")}
        else:
            answer_contract = _answer_contract(
                pipe.get("answer"),
                p.get("question_type"),
                packet=(json.loads((d / "pipeline" / "envelope_FREEZE.json")
                               .read_text(encoding="utf-8")).get("evidence")
                        if (d / "pipeline" / "envelope_FREEZE.json"
                            ).exists() else []),
                user_variables=list(p.get("user_variables") or []),
                clarification=str(p.get("clarification_answer")
                                  or p.get("clarification") or
                                  p.get("followup_clarification") or ""))
        # R6 owner directive 2026-11-11: contract/number diagnostics are
        # SYMMETRIC — the same answer-shape contract and the same
        # fabricated-number accounting are REPORTED for both arms. The
        # hard unverified-number disqualification and the
        # full_scoreable gate stay pipeline-side by design (the pipeline
        # is the system under test; the baseline is the comparison
        # instrument) — reporting symmetry, not enforcement symmetry.
        baseline_answer_contract = _answer_contract(
            base.get("answer"),
            p.get("question_type"),
            packet=(json.loads((d / "pipeline" / "envelope_FREEZE.json")
                               .read_text(encoding="utf-8")).get("evidence")
                    if (d / "pipeline" / "envelope_FREEZE.json"
                        ).exists() else []),
            user_variables=list(p.get("user_variables") or []))
        row = {
            "problem_id": p["problem_id"],
            "question_type": p["question_type"],
            "contamination_tag": p.get("contamination_tag"),
            "has_clarification": bool(p.get("clarification_answer")),
            "answer_contract": answer_contract,
            "baseline_answer_contract": baseline_answer_contract,
            "n_numbers_unverified": n_num_unverified,
            "n_numbers_unverified_baseline": len(nr_base),
            "numbers_fabricated": {
                "pipeline": (detail or {}).get("pipeline") or {},
                "baseline": (detail or {}).get("baseline") or {},
            },
            "full_scoreable": (
                contestable and same
                and answer_contract.get("valid") is True
                and judge.get("outcome") == JUDGE_VALID
                and binding.get("state") == "BOUND_OK"
                and not nr),
            "judge_input_binding": binding,
            "judge_outcome": judge.get("outcome"),
            "pipeline_final_status": pipe.get("final_status"),
            "pipeline_completed": completed,
            "wall_s": pipe.get("wall_s"),
            "stage_times_s": pipe.get("stage_times_s"),
            "synthesis_fallback": _fallback_flag(d),
            "n_evidence": len((pipe.get("same_evidence") or {}).get("ids") or []),
            "baseline_route": (base.get("route") or {}).get("provider")
                or route_rec.get("provider"),
            "same_evidence": same,
            "usable_pair": judge.get("usable_pair", False),
            "winner": judge.get("winner"),
            "number_absent": judge.get("number_absent"),
            "second_judge": (judge.get("second_judge") or {}).get("agreement"),
            "criterion_diffs": {c: (judge.get("scores") or {}).get(c, {}).get("diff")
                                for c in CRITERIA},
            "notes": (base.get("blocked") or pipe.get("engine_error") or "")[:120],
            "funnel": _funnel_row(d),
            "hashes": {
                "pipeline_answer_sha": _sha(pipe.get("answer") or "")[:16] if pipe.get("answer") else None,
                "baseline_answer_sha": _sha(base.get("answer") or "")[:16] if base.get("answer") else None,
            },
        }
        rows.append(row)
        if (completed and judge.get("usable_pair")
                and binding.get("state") == "BOUND_OK"):
            usable += 1
        # conditional quality: over FULLY SCOREABLE pairs only
        # (full_scoreable controls the numerators here too)
        if row["full_scoreable"]:
            if judge.get("winner") == "pipeline":
                wins += 1
                system_wins += 1
            elif judge.get("winner") == "tie":
                ties += 1
                system_ties += 1
            for c in CRITERIA:
                diff = (judge.get("scores") or {}).get(c, {}).get("diff")
                if diff is not None:
                    crit_means[c].append(diff)
    # Calibration first: a judge that cannot separate good from bad
    # cannot certify a win (Art. LXI). No calibrated route =>
    # NOT_MEASURED for BOTH judgments; never 0 or 0.5.
    #
    # R6 B-round calibration reuse (owner directive 2026-11-12,
    # measured: B5's 25-minute non-exit was THIS site re-running the
    # live 30-pair calibration that probe_judge_route had already run
    # once). The probe's live calibration is REUSED only when it is
    # bound to (a) THIS commit (the route probe is cross-commit
    # forbidden — the audit verified shadowed-route reuse) and (b) the
    # BYTE-IDENTICAL corpus — the corpus sha256 is recomputed from
    # eval/judge_calibration.json bytes here, so any corpus edit
    # forces a fresh live calibration. Any mismatch => live replay,
    # never stale reuse (Art. XXV: measured reality over aspiration).
    import hashlib
    if judge_route.get("provider"):
        _full = judge_route.get("calibration_full") or {}
        _corpus_p = Path(__file__).resolve().parent / "judge_calibration.json"
        _corpus_sha = (hashlib.sha256(_corpus_p.read_bytes()).hexdigest()
                       if _corpus_p.exists() else None)
        if (_full.get("corpus_sha256") == _corpus_sha
                and judge_route.get("commit") == _commit
                and _corpus_sha):
            calib = dict(_full)
            calib["calibration_source"] = "commit-bound-probe-reuse"
        else:
            calib = run_judge_calibration(judge_route)
            calib["calibration_source"] = "live-replay"
    else:
        calib = {"calibrated": False,
                 "why": "no judge route (pipeline-only run)",
                 "calibration_source": "none"}
    judge_valid = bool(calib.get("calibrated"))
    import math

    def _per_problem_score(w: int, t: int):
        scores = [1.0] * w + [0.5] * t + [0.0] * (len(problems) - w - t)
        mean = sum(scores) / len(scores) if scores else 0.0
        if len(scores) < 2:
            var = 0.0
        else:
            var = sum((s - mean) ** 2 for s in scores) / (len(scores) - 1)
        se = math.sqrt(var / len(scores)) if scores else 0.0
        half = round(1.959964 * se, 3)
        ci = (round(max(0.0, mean - half), 3),
              round(min(1.0, mean + half), 3))
        return mean, ci

    n_full = sum(1 for r in rows if r["full_scoreable"])
    # system metric: denominator is ALL N problems; full_scoreable
    # controls the numerators. A missing/infrastructure-blocked answer
    # is a loss. Judge invalid => NOT_MEASURED, never 0 or 0.5.
    system_pw = system_wins + 0.5 * system_ties
    system_score, system_ci = ((round(system_pw / len(problems), 3),
                                _per_problem_score(system_wins,
                                                  system_ties)[1])
                               if judge_valid else (None, None))
    system_losses = (len(problems) - system_wins - system_ties
                     if judge_valid else None)
    full_scoreable_baseline_wins = (
        n_full - wins - ties
        if judge_valid else None)
    # conditional quality: strictly fully scoreable pairs
    cond_pw = wins + 0.5 * ties
    conditional_quality = (round(cond_pw / n_full, 3)
                           if (judge_valid and n_full) else "NOT_MEASURED")
    conditional_losses = (n_full - wins - ties
                          if judge_valid else None)
    win_rate = conditional_quality
    ci = system_ci                          # normal-approx interval
    ci_method = "normal_approx_0_0.5_1"
    system_wilson = None
    # fresh vs contaminated split
    def _split(tag_val):
        sub = [r for r in rows if r.get("contamination_tag") == tag_val]
        if not sub:
            return None
        u = sum(1 for r in sub if r.get("usable_pair"))
        w = sum(1 for r in sub if r.get("winner") == "pipeline")
        t = sum(1 for r in sub if r.get("winner") == "tie")
        pair_wr = (round((w + 0.5 * t) / u, 3)
                   if (u and calib.get("calibrated")) else "NOT_MEASURED")
        return {"n": len(sub), "completed": sum(1 for r in sub if r["pipeline_completed"]),
                "usable": u, "win_rate": pair_wr}
    def _funnel_agg(tag_val: Optional[str],
                    fresh_only: bool = False) -> Dict[str, Any]:
        sub = [r for r in rows
               if (r.get("contamination_tag") is None if fresh_only
                   else (tag_val is None
                         or r.get("contamination_tag") == tag_val))]
        n = len(sub)
        n_mech = sum(1 for r in sub
                     if (r.get("funnel") or {}).get("mechanisms_found"))
        n_dist = sum(1 for r in sub
                     if (r.get("funnel") or {}).get(
                         "candidates_generated_distinct"))
        return {
            "n": n,
            "completed": sum(1 for r in sub if r["pipeline_completed"]),
            "mechanisms_found": n_mech,
            "candidates_generated_distinct": n_dist,
            "mechanisms_rate": round(n_mech / n, 3) if n else None,
            "distinct_rate": round(n_dist / n, 3) if n else None,
            "starved": [r["problem_id"] for r in sub
                        if not (r.get("funnel") or {}).get(
                            "mechanisms_found")],
            "starved_reasons": {
                r["problem_id"]: (r.get("funnel") or {}).get("starved_reason")
                for r in sub
                if not (r.get("funnel") or {}).get("mechanisms_found")},
        }

    walls = [r["wall_s"] for r in rows if isinstance(r.get("wall_s"), (int, float))]
    all_stages: Dict[str, List[float]] = {}
    for r in rows:
        for k, v in (r.get("stage_times_s") or {}).items():
            if isinstance(v, (int, float)):
                all_stages.setdefault(k, []).append(float(v))
    wall_time = {
        "sum_wall_s": round(sum(walls), 1) if walls else None,
        "mean_wall_s": round(sum(walls) / len(walls), 1) if walls else None,
        "max_wall_s": round(max(walls), 1) if walls else None,
        "mean_stage_s": {k: round(sum(v) / len(v), 2)
                         for k, v in sorted(all_stages.items())},
    }

    def _pct(vals: List[float], q: float) -> Optional[float]:
        if not vals:
            return None
        s = sorted(vals)
        if len(s) == 1:
            return round(s[0], 1)
        k = (len(s) - 1) * q
        lo, hi = int(k), min(int(k) + 1, len(s) - 1)
        return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)

    speed = {
        "n": len(walls),
        "p50_wall_s": _pct(walls, 0.50),
        "p95_wall_s": _pct(walls, 0.95),
        "timeout_count": sum(
            1 for r in rows
            if r["pipeline_final_status"] == "INCOMPLETE_INFRASTRUCTURE"),
        "budget_note": ("owner budget: median ~120 s, worst ~300 s; "
                        "timeouts are INCOMPLETE_INFRASTRUCTURE"),
    }
    return {
        "metric": "blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)",
        "kpi": "R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct",
        "criteria": CRITERIA,
        "commit": _commit,
        "dirty_tree": _dirty,
        "run_id": _run_ns[0] if _run_ns else None,
        "rubric_version": RUBRIC_VERSION,
        "n_input_mismatches": sum(
            1 for r in rows
            if (r.get("judge_input_binding") or {}).get("state")
            == "INCOMPLETE_INPUT_MISMATCH"),
        "n_unbound_legacy": sum(
            1 for r in rows
            if (r.get("judge_input_binding") or {}).get("state")
            == "UNBOUND_LEGACY"),
        "generated_at": utc_now(),
        "pipeline_completion": f"{n_completed}/{len(problems)}",
        "pipeline_completion_rate": round(n_completed / len(problems), 3) if problems else 0.0,
        "yield_funnel_DEV": _funnel_agg(None),
        "yield_funnel_fresh": _funnel_agg(None, fresh_only=True),
        "wall_time": wall_time,
        "speed": speed,
        "baseline_route": {"provider": route_rec.get("provider"), "model": route_rec.get("model"),
                           "state": route_rec.get("state")},
        "judge_route": {"provider": judge_route.get("provider"), "model": judge_route.get("model"),
                        "independence": (judge_route.get("judge_independence")
                                         or ("different provider+family from "
                                             "baseline; not 1.7B"
                                             if judge_route.get("provider")
                                             else "NO_ROUTE")),
                        "disclosure": judge_route.get("disclosure")},
        "judge_calibration": calib,
        "n_problems": len(problems),
        "subset": ("holdout:" + str(len(problems))) if holdout else
                  ("dev7" if subset_ids is not None
                   and set(subset_ids) == set(DEV7) else
                   ("all" if subset_ids is None else f"custom:{len(subset_ids)}")),
        "n_completed_pipeline": n_completed,
        "n_usable_pairs": usable,
        "full_scoreable_pairs": sum(1 for r in rows if r.get("full_scoreable")),
        "n_numbers_unverified": sum(1 for r in rows
                                     if r.get("n_numbers_unverified")),
        "n_numbers_unverified_baseline": sum(
            1 for r in rows
            if r.get("n_numbers_unverified_baseline")),
        "fabricated_number_rate_pipeline": round(
            sum((r.get("numbers_fabricated") or {}).get("pipeline", {}).get("fabricated_rate") or 0
                for r in rows)
            / max(1, sum(1 for r in rows
                         if (r.get("numbers_fabricated") or {}).get("pipeline"))), 3),
        "fabricated_number_rate_baseline": round(
            sum((r.get("numbers_fabricated") or {}).get("baseline", {}).get("fabricated_rate") or 0
                for r in rows)
            / max(1, sum(1 for r in rows
                         if (r.get("numbers_fabricated") or {}).get("baseline"))), 3),
        # R6 symmetric contract diagnostics (owner directive 2026-11-11):
        # the SAME answer-shape contract is reported for both arms
        "contract_valid_pipeline": sum(
            1 for r in rows
            if (r.get("answer_contract") or {}).get("valid") is True),
        "contract_valid_baseline": sum(
            1 for r in rows
            if (r.get("baseline_answer_contract") or {}).get("valid") is True),
        "contract_violations_pipeline": sum(
            len((r.get("answer_contract") or {}).get("violations") or [])
            for r in rows),
        "contract_violations_baseline": sum(
            len((r.get("baseline_answer_contract") or {}).get("violations") or [])
            for r in rows),
        "threshold_basis_pipeline": {
            b: sum(1 for r in rows
                   if ((r.get("answer_contract") or {}).get("bindings") or {})
                   .get("threshold_basis") == b)
            for b in ("packet_or_user_variable", "assumption",
                      "calibration_rule", "unknown", "no_number")},
        "pipeline_wins": wins,
        "baseline_wins": full_scoreable_baseline_wins,
        "ties": ties,
        # R5 P0-2 metric block: system = unconditional, N denominator;
        # conditional = strictly fully scoreable pairs; both NOT_MEASURED
        # unless the judge passes the live calibration gate. Wilson 95%
        # interval on N (declared on DEV before any sealed run).
        "system_score": system_score,
        "system_wins": system_wins,
        "system_ties": system_ties,
        "system_losses": system_losses,
        "system_ci_95": system_ci,
        "conditional_quality": conditional_quality,
        "conditional_wins": wins,
        "conditional_ties": ties,
        "conditional_losses": conditional_losses,
        "conditional_quality_pairs": n_full,
        "BLIND_PAIRWISE_WIN_RATE": win_rate,
        "ci_method": ci_method,
        "ci_95": ci,
        "second_judge": {
            "agree": sum(1 for r in rows
                         if r.get("second_judge") == "AGREE"),
            "disagree": sum(1 for r in rows
                            if r.get("second_judge") == "DISAGREE"),
            "no_route_or_invalid": sum(1 for r in rows
                                       if r.get("second_judge") in
                                       (None, "NO_ROUTE")),
        },
        "judge_outcomes": {
            o: sum(1 for r in rows if r.get("judge_outcome") == o)
            for o in JUDGE_OUTCOMES
        },
        "fresh_vs_contaminated": {
            "DEV_CONTAMINATED": _split("DEV_CONTAMINATED"),
            "FRESH": _split(None),
        },
        "criterion_mean_diffs_pipeline_minus_baseline": {
            c: (round(sum(v) / len(v), 3) if v else None)
            for c, v in crit_means.items()},
        "rows": rows,
    }


def _rec(d: Path, name: str) -> Dict[str, Any]:
    f = d / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _fallback_flag(problem_dir: Path) -> Optional[bool]:
    f = problem_dir / "pipeline" / "final_state.json"
    if not f.exists():
        return None
    try:
        fs = json.loads(f.read_text(encoding="utf-8"))
        ev = fs.get("evolution") or {}
        gen_s = ev.get("gen1") or ev.get("iterations") or None
        if isinstance(gen_s, dict) and "origin" in gen_s:
            return gen_s.get("origin") == "BASELINE_FALLBACK_GENERATION"
        if isinstance(gen_s, list) and gen_s and isinstance(gen_s[0], dict):
            return gen_s[0].get("origin") == "BASELINE_FALLBACK_GENERATION"
    except Exception:  # noqa: BLE001
        return None
    return None


def write_table(table: Dict[str, Any]) -> None:
    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    (SCORE_DIR / "SCORE_TABLE.json").write_text(
        json.dumps(table, indent=1, default=str) + "\n", encoding="utf-8")
    lines = [
        f"# eval score table (commit {table['commit']}, "
        f"dirty_tree={table.get('dirty_tree')}, {table['generated_at']})",
        "",
        f"metric: {table['metric']}",
        f"KPI: {table.get('kpi')}",
        "criteria: " + "; ".join(f"{k.split('_', 1)[0]}={v}"
                                for k, v in table["criteria"].items()),
        "",
        f"pipeline completion: {table['pipeline_completion']}",
        f"subset: {table.get('subset')} (n={table.get('n_problems')})",
        "yield funnel (DEV): " + json.dumps(table.get("yield_funnel_DEV"),
                                             default=str),
        "yield funnel (fresh): " + json.dumps(table.get("yield_funnel_fresh"),
                                               default=str),
        "wall time: " + json.dumps(table.get("wall_time"), default=str),
        "speed: " + json.dumps(table.get("speed"), default=str),
        f"baseline route: {table['baseline_route'].get('provider')} / "
        f"{table['baseline_route'].get('model')} ({table['baseline_route'].get('state')})",
        f"judge route: {table['judge_route'].get('provider')} / "
        f"{table['judge_route'].get('model')} ({table['judge_route'].get('independence')})",
        f"judge calibration: {table['judge_calibration'].get('accuracy')} "
        f"(n={table['judge_calibration'].get('n_pairs')}, "
        f"passed={table['judge_calibration'].get('passed')})",
        "",
        f"n usable pairs (completed pipeline only): {table['n_usable_pairs']}/{table['n_completed_pipeline']}",
        f"full scoreable pairs: {table.get('full_scoreable_pairs')}",
        f"pairs with unverified numbers: {table.get('n_numbers_unverified')}",
        f"pipeline wins {table['pipeline_wins']}  baseline wins "
        f"{table['baseline_wins']}  ties {table['ties']}",
        "",
        f"**SYSTEM SCORE (unconditional, all {table['n_problems']} problems): "
        f"{table.get('system_score')}**  ({table.get('system_wins')} wins, "
        f"{table.get('system_ties')} ties)",
        "",
        f"**CONDITIONAL QUALITY (fully scoreable pairs, calibration-gated): "
        f"{table.get('conditional_quality')}**  "
        f"({table.get('conditional_wins')}W {table.get('conditional_ties')}T "
        f"{table.get('conditional_losses')}L over {table.get('full_scoreable_pairs')} pairs)",
        "",
        f"system losses (infrastructure/refusal/contract-invalid, N={table['n_problems']}): "
        f"{table.get('system_losses')};  normal-approx CI on N: {table.get('ci_95')} "
        f"(method {table.get('ci_method')})",
        f"judge outcomes: {json.dumps(table.get('judge_outcomes'), default=str)}",
        f"second judge: {json.dumps(table.get('second_judge'), default=str)}",
        "",
        "fresh vs contaminated: " + json.dumps(table["fresh_vs_contaminated"]),
        "criterion mean diffs (pipeline-baseline): "
        + json.dumps(table["criterion_mean_diffs_pipeline_minus_baseline"]),
        "answer-shape contract: "
        + json.dumps(_contract_summary(table.get("rows") or []), default=str),
        "",
        "| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in table["rows"]:
        f = r.get("funnel") or {}
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                r["problem_id"], r.get("contamination_tag"),
                r["question_type"], r["pipeline_final_status"],
                r["pipeline_completed"], r.get("wall_s"),
                f.get("mechanisms_found"), f.get("candidates_generated_distinct"),
                f.get("starved_reason"), r["winner"],
                json.dumps(r["criterion_diffs"], default=str)[:120]))
    (SCORE_DIR / "SCORE_TABLE.md").write_text("\n".join(lines) + "\n",
                                              encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
_commit = git_short()
_dirty = git_dirty()

#: run-identity layer (audit P0-8): every measured attempt gets its own
#: root — RUNS_ROOT/<commit>/<run-id>/<problem>. The run id carries
#: repeat + arms + timestamp, so repeats NEVER overwrite an earlier
#: run's pipeline/baseline/judge records, and a later score table can
#: never cross-wire one repeat's pipeline answer with another's judge
#: record. _run_ns is set in main(); child processes receive it
#: verbatim via --run-id (they must write into the PARENT's root).
_run_ns: List[str] = []

#: R6 B-round engine-env handoff (owner directive 2026-11-12): the
#: launcher passes engine env as an EXPLICIT argv dict (--engine-env
#: KEY=VALUE); no shell exports. Measured basis: this host's bash layer
#: is WSL and its exports do not cross into native .exe children (the
#: B5 smoke ran on the code defaults cache-off/cap-12 while the launcher
#: echoed rw/18). Argv crosses; _spawn_child merges this dict into every
#: child env explicitly, so parent and children share one effective env.
_ENGINE_ENV_OVERRIDES: Dict[str, str] = {}


def _run_dir() -> Path:
    base = RUNS_ROOT / _commit
    return base.joinpath(*_run_ns) if _run_ns else base


#: the rubric generation a judge record is bound to (its prompt shape).
#: A judgment made under a different rubric version is not comparable
#: and must not be reused (audit P0-8: bind every judgment to the
#: rubric version it was made under).
RUBRIC_VERSION = "0-4-rubric/1"


def _judge_input_binding(judge_rec: Dict[str, Any],
                         pipe: Dict[str, Any],
                         base: Dict[str, Any],
                         pipe_ev_hash: Optional[str],
                         route: Dict[str, Any]) -> Dict[str, Any]:
    """Verify a judge record against the EXACT inputs it was made
    under. Any mismatch -> the result is INCOMPLETE and excluded from
    scoring (audit P0-8; Art. XXV: unknown stays unknown, never
    silently reused)."""
    b = judge_rec.get("bound_inputs")
    if not isinstance(b, dict):
        return {"state": "UNBOUND_LEGACY",
                "why": "no input binding recorded (pre-P0-8 judge "
                       "record) — a result whose inputs cannot be "
                       "verified is INCOMPLETE, not a score"}
    bad = []
    p_sha = b.get("pipeline_answer_sha256")
    if p_sha in (None, "ABSENT"):
        if pipe.get("answer"):
            bad.append("pipeline answer changed after the judgment")
    elif p_sha != _sha(pipe.get("answer") or ""):
        bad.append("pipeline answer hash mismatch")
    b_sha = b.get("baseline_answer_sha256")
    if b_sha in (None, "ABSENT"):
        if base.get("answer"):
            bad.append("baseline answer changed after the judgment")
    elif b_sha != _sha(base.get("answer") or ""):
        bad.append("baseline answer hash mismatch")
    e_sha = b.get("evidence_sha256")
    if e_sha:
        if pipe_ev_hash != e_sha:
            bad.append("evidence snapshot hash mismatch")
    jr = b.get("judge_route") or {}
    if (jr.get("provider") != (route or {}).get("provider")
            or jr.get("model") != (route or {}).get("model")):
        bad.append("judge route differs from the bound record")
    if str(b.get("rubric_version") or "") != RUBRIC_VERSION:
        bad.append("rubric version differs")
    if bad:
        return {"state": "INCOMPLETE_INPUT_MISMATCH", "why": "; ".join(bad)}
    return {"state": "BOUND_OK", "why": ""}


def _save(problem_id: str, name: str, rec: Dict[str, Any]) -> None:
    d = _run_dir() / problem_id
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(rec, indent=1, default=str) + "\n",
                          encoding="utf-8")


# ---------------------------------------------------------------------------
# shared child spawn (Popen + DEVNULL + daemon killer; hard wall-clock)
# ---------------------------------------------------------------------------
def _spawn_child(cmd: List[str], timeout_s: int,
                 env_extra: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Run one child process with a hard wall-clock bound and no pipes.
    env_extra merges over os.environ (never persisted)."""
    import subprocess
    import threading
    env = dict(os.environ)
    if _ENGINE_ENV_OVERRIDES:
        # explicit engine-env dict (argv handoff; never shell exports)
        env.update(_ENGINE_ENV_OVERRIDES)
    if env_extra:
        env.update(env_extra)
    _killed = {"fired": False}
    cp = subprocess.Popen(cmd, cwd=str(REPO),
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,
                          env=env)

    def _killer():
        time.sleep(timeout_s)
        if cp.poll() is None:
            _killed["fired"] = True
            try:
                cp.terminate()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(10)
            if cp.poll() is None:
                try:
                    cp.kill()
                except Exception:  # noqa: BLE001
                    pass

    th = threading.Thread(target=_killer, daemon=True)
    th.start()
    t0 = time.time()
    try:
        rc = cp.wait()
        err = None
    except Exception as exc:  # noqa: BLE001
        rc, err = None, f"{type(exc).__name__}: {exc}"[:300]
    return {"returncode": rc, "wall_s": round(time.time() - t0, 1),
            "timed_out": bool(_killed["fired"]), "spawn_error": err}


def _run_pipeline_parallel(problems: List[Dict[str, Any]], workers: int,
                           timeout_s: int, problems_file: str = "") -> None:
    """Run each pipeline problem in its own process with a hard timeout.

    A process exits at the timeout; the parent records the typed
    INCOMPLETE_INFRASTRUCTURE row (Art. LXI: infrastructure loss is
    never a refusal and never silently dropped). Process isolation also
    means an edit in the main tree cannot touch an in-flight run."""
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    script = str(Path(__file__).resolve())

    def _one(p: Dict[str, Any]) -> Dict[str, Any]:
        pid = p["problem_id"]
        cmd = [sys.executable, "-B", script, "--arms", "pipeline",
               "--problems", pid, "--problems-file", problems_file,
               "--root", str(RUNS_ROOT), "--commit", _commit,
               "--child", "--subdir", "pipeline"]
        if _run_ns:
            cmd.extend(["--run-id", _run_ns[0]])
        if _HOLDOUT_MODE:
            cmd.append("--holdout-mode")
        t0 = time.time()
        try:
            res = _spawn_child(cmd, timeout_s)
            state = ("DONE" if (res["returncode"] == 0
                                and not res["timed_out"]) else "TIMEOUT")
            return {"problem_id": pid, "state": state,
                    "returncode": res["returncode"],
                    "wall_s": res["wall_s"],
                    "timed_out": res["timed_out"]}
        except Exception as _exc:  # noqa: BLE001 — spawn failure is infra
            return {"problem_id": pid, "state": "TIMEOUT",
                    "returncode": "SPAWN_FAILED",
                    "wall_s": round(time.time() - t0, 1)}

    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(problems)))) as ex:
        futs = [ex.submit(_one, p) for p in problems]
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            print(f"[eval] {_label(r['problem_id'])}: {r['state']} "
                  f"({r['wall_s']}s, rc={r['returncode']})", flush=True)
            if r["state"] == "TIMEOUT":
                d = _run_dir() / r["problem_id"] / "pipeline"
                rec = {
                    "answer": None, "completed": False,
                    "wall_s": r["wall_s"],
                    "final_status": "INCOMPLETE_INFRASTRUCTURE",
                    "reason": f"hard per-problem timeout {timeout_s}s",
                    "engine_error": "TIMEOUT",

                    "stage_times_s": _stage_times(d),
                }
                _save(r["problem_id"], "pipeline_record.json", rec)
            elif r["returncode"] not in (0, None):
                # the child crashed before writing its record: record the
                # typed infrastructure failure instead of a silent gap
                rec_p = (_run_dir() / r["problem_id"]
                         / "pipeline_record.json")
                if not rec_p.exists():
                    d = _run_dir() / r["problem_id"] / "pipeline"
                    _save(r["problem_id"], "pipeline_record.json", {
                        "answer": None, "completed": False,
                        "wall_s": r["wall_s"],
                        "final_status": "INCOMPLETE_INFRASTRUCTURE",
                        "reason": f"child exit {r['returncode']}",
                        "engine_error": f"child exit {r.get('returncode')}",
                        "stage_times_s": _stage_times(d),
                    })


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="pipeline")
    ap.add_argument("--problems", default="all")
    ap.add_argument("--problems-file", default=str(PROBLEMS),
                    help="problems JSON (external holdouts use this)")
    ap.add_argument("--holdout", default=None,
                    help="owner-held sealed holdout JSON path; outputs go "
                         "to the gitignored eval/holdout_runs/<commit>")
    ap.add_argument("--two-turns", action="store_true",
                    help="round 2: ingest followup_finding and revise "
                         "against the same frozen evidence (Art. LI)")
    ap.add_argument("--root", default=None,
                    help="explicit run-root for this process (used by "
                         "child workers; the parent passes its own)")
    ap.add_argument("--pairs-out", default=None,
                    help="directory for raw pair files (ordinary runs; "
                         "arms of an A/B block pass separate dirs)")
    ap.add_argument("--subset", default="all",
                    choices=["all", "dev7"])
    ap.add_argument("--workers", type=int, default=1,
                    help="parallel pipeline workers (process per problem)")
    ap.add_argument("--timeout", type=int, default=300,
                    help="hard per-problem timeout in seconds")
    ap.add_argument("--child", action="store_true",
                    help="internal: one problem in its own process")
    ap.add_argument("--holdout-mode", action="store_true",
                    help="internal: child received explicit holdout state; "
                         "never overwrite the parent's metadata, print only "
                         "problem-N ids")
    ap.add_argument("--expected-selection-sha256", default=None,
                    help="internal/test: override the expected selection hash "
                         "(default is the sealed pre-registered value; a "
                         "disposable fixture passes its own hash)")
    ap.add_argument("--subdir", default="pipeline",
                    help="internal: pipeline subdirectory for this run "
                         "(round-2 children use pipeline_r2)")
    ap.add_argument("--commit", default=None,
                    help="internal: the parent's commit; the child reuses "
                         "it verbatim instead of resolving HEAD "
                         "(prevents run-dir splitting when HEAD moves "
                         "mid-run)")
    ap.add_argument("--repeat", type=int, default=1,
                    help="which repeat of this (commit, arms, dataset) "
                         "block this run is; every repeat gets its own "
                         "run root (audit P0-8: no overwriting earlier "
                         "records)")
    ap.add_argument("--run-id", default=None,
                    help="internal: the parent's run id; children reuse "
                         "it verbatim so parent and child share ONE run "
                         "root")
    ap.add_argument("--engine-env", action="append", default=None,
                    metavar="KEY=VALUE",
                    help="R6 B-round env handoff: pass ONE engine env "
                         "var EXPLICITLY on argv (repeatable; no shell "
                         "exports — measured on this host: the WSL bash "
                         "layer's exports do not cross into native .exe "
                         "children). Applied to os.environ before any "
                         "launch and merged into every child env by "
                         "_spawn_child, so parent and children share "
                         "ONE effective engine env")
    args = ap.parse_args(argv)
    global RUNS_ROOT, _commit, _HOLDOUT_MODE, _run_ns
    if args.engine_env:
        # R6 B-round env handoff (owner directive 2026-11-12): the
        # explicit argv dict is the ONLY mechanism that sets engine
        # env this round. Measured basis: WSL exports do not reach
        # the native .exe children (reproduced: bash one-liner ->
        # python.exe sees None). Every value rides argv -> os.environ
        # -> _ENGINE_ENV_OVERRIDES -> every child env, and the echo
        # below is the effective-env record (Art. XXVII: recorded,
        # never silent).
        for _ee in args.engine_env:
            _k, _sep, _v = _ee.partition("=")
            if not _sep or not _k:
                raise SystemExit(
                    f"--engine-env expects KEY=VALUE, got {_ee!r}")
            os.environ[_k] = _v
            _ENGINE_ENV_OVERRIDES[_k] = _v
        print(f"[engine-env] applied {len(_ENGINE_ENV_OVERRIDES)} keys "
              f"on argv: {sorted(_ENGINE_ENV_OVERRIDES)}", flush=True)
    arms = [a.strip().lower() for a in args.arms.split(",") if a.strip()]
    if args.root:
        RUNS_ROOT = Path(args.root)
    if args.commit:
        _commit = args.commit
    # run identity (audit P0-8): parent mints a fresh run id; children
    # inherit it. The id carries repeat + arms + timestamp, so this
    # attempt's records can never overwrite an earlier attempt's.
    if args.run_id:
        _run_ns = [args.run_id]
    else:
        _ts = utc_now().replace("T", "").replace("+", "").replace(":", "")
        _run_ns = [f"r{args.repeat}-{'+'.join(arms) or 'run'}-{_ts[:19]}"]
    _HOLDOUT_MODE = bool(args.holdout) or bool(getattr(args, "holdout_mode", False))
    PRE_REGISTERED_SELECTION_SHA256 = (
        "57be8218d1fa681c972ff80d084f55666a53a640b3aa4aeb6c02be5ce9c6b107")
    if args.holdout:
        hpath = Path(args.holdout)
        if not hpath.exists():
            print(f"[holdout] missing file: {hpath}", flush=True)
            return 2
        hold = json.loads(hpath.read_text(encoding="utf-8"))
        problems = list(hold.get("problems") or [])
        if not problems:
            print("[holdout] no 'problems' array in the file", flush=True)
            return 2
        if len(problems) != 24:
            print(f"[holdout] refusing to run: expected 24 problems, "
                  f"got {len(problems)} (P0, holdout isolation)", flush=True)
            return 2
        # P0-3: recompute and verify the selection hash from the LOADED
        # input using the repository's canonical method (never merely write
        # the pre-registered constant into metadata). No contents printed.
        try:
            from eval.validate_problems import selection_hash
            recomputed = selection_hash(problems)
        except Exception as exc:  # noqa: BLE001 — fail closed
            print(f"[holdout] refusing to run: canonical selection-hash "
                  f"method unavailable: {exc}", flush=True)
            return 2
        expected = (args.expected_selection_sha256
                    or PRE_REGISTERED_SELECTION_SHA256)
        if recomputed != expected:
            print(f"[holdout] refusing to run: recomputed selection hash "
                  f"{recomputed} != expected {expected} "
                  f"({'pre-registered sealed value'
                      if args.expected_selection_sha256 is None
                      else 'operator-declared fixture value'}); no problem "
                  f"content printed", flush=True)
            return 2
        args.subset = "all"
        args.problems = "all"
        args.problems_file = args.holdout
        args.workers = 1  # holdout is always sequential (the two max runs)
        RUNS_ROOT = HOLDOUT_ROOT
        print(f"[holdout] loaded sealed problem file; outputs in "
              f"{HOLDOUT_ROOT} (gitignored); n=24; selection hash verified "
              f"against {'pre-registered' if args.expected_selection_sha256 is None else 'operator-declared'} "
              f"value", flush=True)
    else:
        problems = json.loads(
            Path(args.problems_file).read_text(encoding="utf-8"))["problems"]
    if args.subset == "dev7" and args.problems == "all":
        problems = [p for p in problems if p["problem_id"] in DEV7]
    if args.problems != "all":
        want = {p.strip() for p in args.problems.split(",") if p.strip()}
        problems = [p for p in problems if p["problem_id"] in want]

    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    (RUNS_ROOT / _commit).mkdir(parents=True, exist_ok=True)
    _run_dir().mkdir(parents=True, exist_ok=True)
    # children inherit explicit holdout state and NEVER overwrite the
    # parent's canonical metadata; only the parent (non-child) writes it.
    # The run-scoped meta carries the run identity (audit P0-8): no two
    # attempts share a root, and each root's meta says which repeat of
    # which arms block it belongs to.
    if not args.child:
        (_run_dir() / "_run_meta.json").write_text(
            json.dumps({"commit": _commit, "dirty_tree": _dirty,
                        "run_id": _run_ns[0] if _run_ns else None,
                        "repeat": args.repeat,
                        "arms": args.arms,
                        "dont_write_bytecode": bool(sys.dont_write_bytecode),
                        "executable": sys.executable,
                        "argv": list(argv or []),
                        "holdout": _HOLDOUT_MODE,
                        "n_problems": len(problems),
                        "selection_sha256_recomputed": (
                            recomputed if args.holdout else None),
                        "selection_sha256_verified": bool(
                            args.holdout and recomputed == expected),
                        "pre_registered_selection_sha256": (
                            PRE_REGISTERED_SELECTION_SHA256
                            if args.holdout else None),
                        "holdout_mode_state": (
                            "explicit (--holdout)" if args.holdout
                            else "none"),
                        "started_at": utc_now()}, indent=1) + "\n",
            encoding="utf-8")

    route_rec: Dict[str, Any] = {}
    judge_route: Dict[str, Any] = {}
    if any(a in ("baseline", "judge") for a in arms):
        probe_p = RUNS_ROOT / _commit / "_route_probe.json"
        if probe_p.exists():
            route_rec = json.loads(probe_p.read_text(encoding="utf-8"))
        else:
            route_rec = probe_zero_paid_route()
            RUNS_ROOT.mkdir(parents=True, exist_ok=True)
            (RUNS_ROOT / _commit).mkdir(parents=True, exist_ok=True)
            probe_p.write_text(json.dumps(route_rec, indent=1) + "\n",
                               encoding="utf-8")
        # judge route (different provider). A cached probe is only
        # reusable within the SAME commit; cross-commit cache reuse
        # is forbidden (the audit verified shadowed-route reuse).
        jp = RUNS_ROOT / _commit / "_judge_route_probe.json"
        if jp.exists() and json.loads(
                jp.read_text(encoding="utf-8")
                ).get("commit") == _commit:
            judge_route = json.loads(jp.read_text(encoding="utf-8"))
        else:
            judge_route = probe_judge_route(route_rec.get("provider"))
            # bind the probe to this commit
            judge_route = {**judge_route, "commit": _commit}
            jp.write_text(json.dumps(judge_route, indent=1) + "\n",
                          encoding="utf-8")
        # second judge (different family from both baseline and primary
        # judge); advisory, never changes the tally
        if os.environ.get("ENGINE_SECOND_JUDGE", "1").strip() not in (
                "0", "false", "no"):
            jp2 = RUNS_ROOT / _commit / "_judge2_route_probe.json"
            if jp2.exists() and json.loads(
                    jp2.read_text(encoding="utf-8")
                    ).get("commit") == _commit:
                judge2_route = json.loads(jp2.read_text(encoding="utf-8"))
            else:
                judge2_route = probe_judge2_route(
                    route_rec.get("provider"), judge_route.get("provider"))
                judge2_route = {**judge2_route, "commit": _commit}
                jp2.write_text(json.dumps(judge2_route, indent=1) + "\n",
                               encoding="utf-8")
        else:
            judge2_route = {"provider": None, "state": "DISABLED"}
        print(f"[eval] baseline route: {route_rec.get('provider')} / "
              f"{route_rec.get('model')} ({route_rec.get('state')})", flush=True)
        print(f"[eval] judge route: {judge_route.get('provider')} / "
              f"{judge_route.get('model')} ({judge_route.get('state')})", flush=True)

    pipeline_done = False
    if "pipeline" in arms and not args.child:
        # every pipeline arm runs isolated in its own subprocess so the
        # hard per-problem timeout (workers=1 => sequential but still
        # capped) applies to all runs (Art. LXI)
        _run_pipeline_parallel(problems, args.workers, args.timeout,
                               args.problems_file)
        pipeline_done = True
        arms = [a for a in arms if a != "pipeline"]

    for p in problems:
        pid = p["problem_id"]
        d = _run_dir() / pid
        print(f"[eval] {_label(pid)}: start", flush=True)
        if "pipeline" in arms:
            _rec_name = ("pipeline_record.json" if args.subdir == "pipeline"
                         else f"{args.subdir}_record.json")
            # R6 item 5: the round-1 pipeline arm NEVER sees the follow-up
            # finding (the round-2 child sets EVAL_ROUND2_INTAKE=1 and
            # consumes the full problem — this strip does not touch it)
            rec = run_pipeline_problem(_round1_problem(p), d / args.subdir)
            _save(pid, _rec_name, rec)
            print(f"[eval] {_label(pid)}: pipeline done ({rec['wall_s']}s, "
                  f"status={rec.get('final_status')}, completed={rec.get('completed')})",
                  flush=True)
        if "composer" in arms:
            # R6 ablation arm: the ANSWER COMPOSER alone (one LLM call,
            # no packet, no candidates, no verification). Fresh dir per
            # run (the fresh-run discipline applies to every measured arm).
            _cdir = d / "composer"
            if _cdir.exists():
                import shutil
                shutil.rmtree(_cdir, ignore_errors=True)
            _cdir.mkdir(parents=True, exist_ok=True)
            run_composer_only_problem(_round1_problem(p), _cdir)
        if "baseline" in arms:
            rec = run_baseline_problem(
                _intake_problem(_round1_problem(p)), d, route_rec)
            _save(pid, "baseline_record.json", rec)
            print(f"[eval] {_label(pid)}: baseline done "
                  f"({'ok' if rec.get('answer') else rec.get('blocked')})",
                  flush=True)
        if "judge" in arms:
            pr = d / "pipeline_record.json"
            ba = d / "baseline_record.json"
            if not (pr.exists() and ba.exists()):
                print(f"[eval] {_label(pid)}: judge skipped (missing arm records)", flush=True)
                continue
            pv = (json.loads(pr.read_text(encoding="utf-8")) or {}).get("answer")
            bv = (json.loads(ba.read_text(encoding="utf-8")) or {}).get("answer")
            # audit P0-8: every judge record binds to the EXACT inputs it
            # was made under (answer hashes, evidence hash, judge route,
            # rubric version) so a later scoring pass can verify — or
            # exclude — the judgment. The skip path binds what it has.
            _bound = {
                "pipeline_answer_sha256": _sha(pv) if pv else "ABSENT",
                "baseline_answer_sha256": _sha(bv) if bv else "ABSENT",
                "evidence_sha256": None,
                "judge_route": {"provider": judge_route.get("provider"),
                                 "model": judge_route.get("model")},
                "rubric_version": RUBRIC_VERSION,
            }
            # never hand a refusal to the judge: only completed pipeline pairs
            pipe_completed = (json.loads(pr.read_text(encoding="utf-8")) or {}).get("completed")
            if not pipe_completed:
                _save(pid, "judge_record.json", {"usable_pair": False,
                        "why": "pipeline did not release an answer",
                        "bound_inputs": _bound})
                print(f"[eval] {_label(pid)}: judge skipped (pipeline not completed)", flush=True)
                continue
            snap = _evidence_snapshot(Path(d) / "pipeline")
            # bind this judgment to the evidence snapshot it actually saw
            _bound["evidence_sha256"] = (snap or {}).get("hash")
            # round-1 pair is judged WITHOUT the follow-up finding; the
            # finding belongs only to round 2 (run_two_turn_problem)
            q1 = _intake_problem({k: v for k, v in p.items()
                                  if k != "followup_finding"})
            rec = run_judge_problem(q1, pv, bv, judge_route, packet=(snap or {}).get("items"))
            if judge2_route.get("provider") and rec.get("usable_pair"):
                rec2 = run_judge_problem(q1, pv, bv,
                                         judge2_route,
                                         packet=(snap or {}).get("items"))
                rec["second_judge"] = {
                    "provider": judge2_route.get("provider"),
                    "model": judge2_route.get("model"),
                    "winner": rec2.get("winner"),
                    "scores": rec2.get("scores"),
                    "usable_pair": bool(rec2.get("usable_pair")),
                    "agreement": ("AGREE" if rec2.get("winner") == rec.get("winner")
                                  else ("DISAGREE" if rec2.get("usable_pair")
                                        else "NO_ROUTE")),
                }
            elif judge2_route.get("provider"):
                rec["second_judge"] = {"provider": judge2_route.get("provider"),
                                       "state": "skipped (first-judge pair unusable)"}
            rec["bound_inputs"] = _bound
            _save(pid, "judge_record.json", rec)
            # raw pair for independent audit (Art. XII custody): both
            # answers, the evidence ids, the judge output — never edited
            try:
                if args.holdout:
                    pairs_dir = HOLDOUT_ROOT / _commit / "_pairs"
                else:
                    pairs_dir = (Path(args.pairs_out) if args.pairs_out
                                 else Path(__file__).resolve().parent
                                      / "pairs")
                pairs_dir.mkdir(parents=True, exist_ok=True)
                pair = {
                    "problem_id": pid,
                    "commit": _commit,
                    "run_id": _run_ns[0] if _run_ns else None,
                    "dirty_tree": _dirty,
                    "question": p.get("question"),
                    "clarification_answer": p.get("clarification_answer"),
                    "baseline_answer": bv,
                    "pipeline_answer": pv,
                    "evidence_ids": (snap or {}).get("ids"),
                    "bound_inputs": _bound,
                    "judge_record": rec,
                    "baseline_same_evidence_hash": (
                        ((json.loads((d / "baseline_record.json").read_text(
                            encoding="utf-8")) or {}).get("same_evidence_hash")
                         if (d / "baseline_record.json").exists() else None)),
                    "pipeline_same_evidence_hash": (snap or {}).get("hash"),
                }
                (pairs_dir / f"{pid}.json").write_text(
                    json.dumps(pair, indent=1, default=str) + "\n",
                    encoding="utf-8")
            except Exception as _exc:  # noqa: BLE001
                print(f"[eval] {_label(pid)}: pair custody write failed: {_exc}",
                      flush=True)
            print(f"[eval] {_label(pid)}: judge -> "
                  f"{rec.get('winner') if rec.get('usable_pair') else rec.get('why')}",
                  flush=True)

    if args.two_turns:
        if not route_rec or not judge_route:
            print("[two-turns] needs baseline+judge routes; skipping",
                  flush=True)
        else:
            for p in problems:
                pid = p["problem_id"]
                d = _run_dir() / pid
                r = run_two_turn_problem(p, d, route_rec, judge_route,
                                         timeout_s=args.timeout)
                print(f"[two-turns] {pid}: round2 "
                      f"{'ok' if r.get('round2_answer') else r.get('two_turn')}",
                      flush=True)

    if args.child:
        return 0

    # DIRECTIVE 2 (owner audit round 2026-11-12): the delivery rate
    # rides the run summary — delivered / total pipeline problems for
    # THIS run (the composer's delivered states + hypothesis-class
    # deliveries over every problem attempted; never recomputed from
    # memory — read from the durable ANSWER_COMPOSED.json records).
    _drate = None
    try:
        _dirs = [p for p in _run_dir().glob("*") if p.is_dir()
                 and (p / "ANSWER_COMPOSED.json").exists()]
        _drate = delivery_rate_from_dirs(_dirs)
    except Exception as _exc:  # noqa: BLE001 — never fatal
        _drate = {"error": str(_exc)[:120]}
    table = build_score_table(route_rec or {}, judge_route or {},
                              [p["problem_id"] for p in problems],
                              problems=problems,
                              holdout=bool(args.holdout))
    table["delivery_rate"] = _drate
    if args.holdout:
        # sealed outputs never touch the repo: table lives inside the
        # gitignored holdout run dir
        (HOLDOUT_ROOT / _commit).mkdir(parents=True, exist_ok=True)
        (HOLDOUT_ROOT / _commit / "SCORE_TABLE.json").write_text(
            json.dumps(table, indent=1, default=str) + "\n",
            encoding="utf-8")
    else:
        write_table(table)
    print(json.dumps({k: table[k] for k in
                      ("commit", "dirty_tree", "pipeline_completion",
                       "yield_funnel_DEV", "wall_time", "speed",
                       "system_score", "system_wins", "system_ties",
                       "system_losses", "system_ci_95",
                       "conditional_quality", "conditional_wins",
                       "conditional_ties", "conditional_losses",
                       "ci_method",
                       "full_scoreable_pairs", "n_numbers_unverified",
                       "n_usable_pairs", "pipeline_wins", "baseline_wins",
                       "ties", "judge_calibration", "judge_outcomes",
                       "second_judge")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

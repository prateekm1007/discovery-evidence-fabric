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
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

os.environ.setdefault("LOCAL_QWEN_BASE_URL", "http://127.0.0.1:8790/v1/chat/completions")
os.environ.setdefault("MODEL_COST_POLICY", "ZERO_PAID_COST")

PROBLEMS = Path(__file__).resolve().parent / "problems.json"
RUNS_ROOT = Path(__file__).resolve().parent / "runs"
SCORE_DIR = Path(__file__).resolve().parent / "score"

# Fast DEV subset (directive: replace the long inner loop; a 6-problem
# subset mixing intervention and predictor types, full 25 only at
# checkpoints). Pre-registered ids, never chosen after seeing results.
DEV6 = [
    "bench-p02-leadacid-grid-corrosion",
    "bench-p05-bridge-bearing-aging",
    "bench-p09-packaging-barrier",
    "eval-new02-slipring-predictor",
    "eval-new06-bearing-vibration-predictor",
    "eval-new09-hvac-filter-predictor",
]

CRITERIA = {
    "a_answered": "answers the asked question",
    "b_user_vars": "uses user-stated variables",
    "c_prediction": "gives a specific testable prediction",
    "d_evidence": "grounded in the provided evidence",
    "e_clarification": "uses the user's clarification answer correctly",
}

# Judge must be a different provider + model family from the baseline
# (agnes) and never the 1.7B model. Candidates probed in order.
JUDGE_CANDIDATES = [
    ("xkiro", "mistralai/ministral-14b"),
    ("xkiro", "mistralai/ministral-8b"),
    ("unorouter", "deepseek-v4-flash:free"),
]


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


def _intake_problem(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Engine intake with the user's clarification answer attached.

    The clarification is a user-stated fact (not retrieved evidence); it
    rides the problem constraint so synthesis, mechanism instantiation
    and the attack all see the same value. The original dict is never
    mutated (the on-disk problem stays the pre-registered one)."""
    q = dict(problem)
    ca = problem.get("clarification_answer")
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
    final_state = out_dir / "final_state.json"
    resume = (out_dir / "envelope_RETRIEVE.json").exists() and not final_state.exists()
    t0 = time.time()
    status, err = None, None
    if not final_state.exists():
        try:
            from discovery_fabric.engine.run import EngineRun
            run = EngineRun(
                _intake_problem(problem), str(out_dir),
                run_id=f"eval-{problem['problem_id']}",
                package_registry_path=str(out_dir / "PACKAGE_ID_REGISTRY.json"),
                with_package=(os.environ.get("ENGINE_NO_PACKAGE", "").strip()
                             not in ("1", "true", "yes")),
                resume=resume)
            manifest = run.run()
            status = manifest.get("final_status") if isinstance(manifest, dict) else None
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"[:400]
    completed = (out_dir / "final_state.json").exists() and \
        json.loads((out_dir / "final_state.json").read_text(encoding="utf-8")).get("final_status") in COMPLETED_STATUSES
    record: Dict[str, Any] = {
        "answer": _extract_pipeline_answer(out_dir),
        "completed": completed,
        "wall_s": round(time.time() - t0, 1),
        "engine_error": err,
        "stage_times_s": _stage_times(out_dir),
        "same_evidence": _evidence_snapshot(out_dir),
    }
    if final_state.exists():
        fs = json.loads(final_state.read_text(encoding="utf-8"))
        record["final_status"] = fs.get("final_status")
        record["reason"] = fs.get("reason")
    return record


COMPLETED_STATUSES = {"AUTOMATED_INVENTION_CANDIDATE",
                      "INVENTION_REQUIRES_EXPERIMENT",
                      "INVENTION_UNDER_DEVELOPMENT",
                      "AUTOMATED_INVENTION"}


def _extract_pipeline_answer(out_dir: Path) -> Optional[str]:
    """Normalised plain-text answer, or None when nothing was released
    (a refusal notice is never handed to the judge �? Art. LXI)."""
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
    try:
        # anthropic flavor not needed for our free rungs (all openai)
        content = None
        if spec.flavor == "anthropic":
            content = lr._call_anthropic_flavor(spec, [{"role": "user", "content": prompt}],
                                                900, max_tokens, model_override=model)
        else:
            content = lr._call_openai_flavor(spec, [{"role": "user", "content": prompt}],
                                             900, max_tokens, model_override=model)
        return {"status": "OK", "provider_id": provider, "model": model,
                "content": content}
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "provider_id": provider, "model": model,
                "content": None, "error": str(exc)[:300]}
    finally:
        os.environ.pop(f"{provider.upper()}_MODEL", None)


def probe_zero_paid_route() -> Dict[str, Any]:
    """Strongest directly reachable zero-paid rung (probe, then return).
    Tries candidate (provider, model) pairs in quality order."""
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
    ]
    attempts = []
    for prov, model in candidates:
        ok = _probe_rung(prov, model)
        attempts.append({"provider": prov, "model": model, "state": "OK" if ok else "FAIL"})
        if ok:
            return {"provider": prov, "model": model, "state": "OK",
                    "probed": attempts, "at": utc_now()}
    return {"provider": None, "model": None, "state": "NO_ZERO_PAID_ROUTE_REACHABLE",
            "probed": attempts, "at": utc_now()}


def probe_judge_route(baseline_provider: str) -> Dict[str, Any]:
    """Judge = different provider + model family from baseline, never 1.7B."""
    candidates = [c for c in JUDGE_CANDIDATES]
    attempts = []
    for prov, model in candidates:
        if prov == baseline_provider:
            attempts.append({"provider": prov, "model": model, "state": "SAME_PROVIDER_AS_BASELINE"})
            continue
        ok = _probe_rung(prov, model)
        attempts.append({"provider": prov, "model": model, "state": "OK" if ok else "FAIL"})
        if ok:
            return {"provider": prov, "model": model, "state": "OK",
                    "probed": attempts, "at": utc_now()}
    return {"provider": None, "model": None, "state": "NO_JUDGE_ROUTE",
            "probed": attempts, "at": utc_now()}


# ---------------------------------------------------------------------------
# arm: baseline
# ---------------------------------------------------------------------------
def run_baseline_problem(problem: Dict[str, Any], out_dir: Path,
                         route: Dict[str, Any]) -> Dict[str, Any]:
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
def _rubric_prompt(problem, a_text: str, b_text: str) -> str:
    clar = problem.get("clarification_text")
    lines = [
        "You judge two engineering answers to the same user problem.",
        "Both answers had access to the same evidence packet retrieved for "
        "this problem.",
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
        "Grade strictly: vague/generic/number-ignoring/unsupported answers "
        "score low; quantified, testable, evidence-using answers score high.",
        "Fabricated numbers, fabricated citations, or invented measurements "
        "are a hard failure (score 1 on the affected criterion).",
        "Then state your overall preference. Answer ONLY with these lines:",
        "A1: <1-5>", "A2: <1-5>", "A3: <1-5>", "A4: <1-5>",
        "B1: <1-5>", "B2: <1-5>", "B3: <1-5>", "B4: <1-5>",
    ]
    if clar:
        lines += ["A5: <1-5>", "B5: <1-5>"]
    lines.append("PREFER: A | B | TIE")
    return "\n".join(lines)


def run_judge_problem(problem: Dict[str, Any], pipe_ans: Optional[str],
                      base_ans: Optional[str], route: Dict[str, Any]) -> Dict[str, Any]:
    if not pipe_ans or not base_ans:
        return {"usable_pair": False,
                "why": ("pipeline answer missing" if not pipe_ans
                        else "baseline answer missing")}
    if not route.get("provider"):
        return {"usable_pair": False, "why": "no judge route"}
    passes: List[Dict[str, Any]] = []
    for order in ("AB", "BA"):
        a_text, b_text = ((pipe_ans, base_ans) if order == "AB"
                          else (base_ans, pipe_ans))
        prompt = _rubric_prompt(problem, a_text, b_text)
        res = _transport_call(route["provider"], route["model"], prompt,
                              "You are a strict blind rubric judge. English "
                              "only. Follow the exact output lines.",
                              max_tokens=300)
        if res.get("status") != "OK":
            passes.append({"order": order, "error": str(res)[:200]})
            continue
        passes.append({"order": order, "raw": res.get("content", ""),
                       **_parse_rubric(res.get("content", ""))})
    crit = {c: {"pipeline": [], "baseline": []} for c in CRITERIA}
    prefs: List[str] = []
    for p in passes:
        if "error" in p:
            continue
        side = ("pipeline", "baseline") if p["order"] == "AB" else ("baseline", "pipeline")
        for j, c in enumerate(CRITERIA, 1):
            for s_i, name in enumerate(("A", "B")):
                if f"{name}{j}" in p:
                    crit[c][side[s_i]].append(int(p[f"{name}{j}"]))
        if p.get("prefer") in ("A", "B"):
            prefs.append(side[0] if p["prefer"] == "A" else side[1])
        elif p.get("prefer") == "TIE":
            prefs.append("tie")
    finals: Dict[str, Any] = {}
    for c, sides in crit.items():
        finals[c] = {
            "pipeline_mean": round(_m(sides["pipeline"]), 2) if sides["pipeline"] else None,
            "baseline_mean": round(_m(sides["baseline"]), 2) if sides["baseline"] else None,
            "diff": round(_m(sides["pipeline"]) - _m(sides["baseline"]), 2)
            if sides["pipeline"] and sides["baseline"] else None}
    if len(prefs) == 2 and prefs[0] == prefs[1]:
        winner = prefs[0]
    elif len(prefs) == 1:
        winner = prefs[0]
    else:
        winner = "tie"
    return {"usable_pair": True,
            "passes": len([p for p in passes if "error" not in p]),
            "scores": finals, "winner": winner, "pref_passes": prefs}


def _m(v: List[int]) -> float:
    return sum(v) / len(v)


def _parse_rubric(raw: str) -> Dict[str, Any]:
    import re
    fields: Dict[str, str] = {}
    for m in re.finditer(r"^\s*([AB][1-5]|PREFER)\s*[:=]\s*(.+)$",
                         raw or "", re.M):
        fields[m.group(1).upper()] = m.group(2).strip()[:8]
    prefer = fields.pop("PREFER", None)
    for k, v in list(fields.items()):
        if k in {f"{s}{j}" for s in "AB" for j in range(1, 6)}:
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
        return {"calibrated": False, "why": "no calibration pairs file"}
    pairs = json.loads(calib_path.read_text(encoding="utf-8"))
    problems_by_id = {p["problem_id"]: p
                      for p in json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]}
    if not isinstance(pairs, list) or len(pairs) < 10:
        return {"calibrated": False, "why": f"need >=10 pairs, have {len(pairs) if isinstance(pairs, list) else 0}"}
    correct = 0
    total = 0
    details = []
    for idx, entry in enumerate(pairs):
        problem = problems_by_id.get(entry["problem_id"])
        if problem is None:
            details.append({"problem_id": entry.get("problem_id"), "error": "problem not found"})
            continue
        good = entry["good_answer"]
        bad = entry["bad_answer"]
        # deterministic, pre-registered order (no RNG in a measurement)
        order = ("good_first"
                 if int(_sha(f"{entry['problem_id']}:{idx}")[:8], 16) % 2 == 0
                 else "bad_first")
        if order == "good_first":
            a, b, good_is = good, bad, "A"
        else:
            a, b, good_is = bad, good, "B"
        prompt = _rubric_prompt(_intake_problem(problem), a, b)
        res = _transport_call(judge_route["provider"], judge_route["model"], prompt,
                              "You are a strict blind rubric judge. English only. "
                              "Follow the exact output lines.", max_tokens=300)
        if res.get("status") != "OK":
            details.append({"problem_id": entry.get("problem_id"), "error": str(res)[:120]})
            continue
        parsed = _parse_rubric(res.get("content", ""))
        pref = parsed.get("prefer")
        total += 1
        # map preference back to good/bad
        if order == "good_first":
            picked_good = (pref == "A")
        else:
            picked_good = (pref == "B")
        if picked_good:
            correct += 1
        details.append({"problem_id": entry.get("problem_id"), "order": order,
                        "prefer": pref, "picked_good": picked_good})
    acc = round(correct / total, 3) if total else 0.0
    passed = acc >= 0.8
    return {"calibrated": bool(passed), "n_pairs": total, "correct": correct,
            "accuracy": acc, "threshold": 0.8, "passed": passed,
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
def build_score_table(route_rec: Dict[str, Any],
                      judge_route: Dict[str, Any],
                      subset_ids: Optional[List[str]] = None
                      ) -> Dict[str, Any]:
    commit_dir = RUNS_ROOT / _commit
    problems = json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]
    if subset_ids is not None:
        want = set(subset_ids)
        problems = [p for p in problems if p["problem_id"] in want]
    rows, usable = [], 0
    wins = ties = 0
    crit_means: Dict[str, List[float]] = {c: [] for c in CRITERIA}
    n_completed = 0
    for p in problems:
        d = commit_dir / p["problem_id"]
        pipe = _rec(d, "pipeline_record.json")
        base = _rec(d, "baseline_record.json")
        judge = _rec(d, "judge_record.json")
        snap_hash = (pipe.get("same_evidence") or {}).get("hash")
        same = bool(snap_hash and snap_hash == base.get("same_evidence_hash"))
        completed = bool(pipe.get("completed"))
        if completed:
            n_completed += 1
        row = {
            "problem_id": p["problem_id"],
            "question_type": p["question_type"],
            "contamination_tag": p.get("contamination_tag"),
            "has_clarification": bool(p.get("clarification_answer")),
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
        if completed and judge.get("usable_pair"):
            usable += 1
            if judge.get("winner") == "pipeline":
                wins += 1
            elif judge.get("winner") == "tie":
                ties += 1
            for c in CRITERIA:
                diff = (judge.get("scores") or {}).get(c, {}).get("diff")
                if diff is not None:
                    crit_means[c].append(diff)
    # Calibration first: the win-rate is NOT_MEASURED unless the judge
    # itself passed the known-good/known-bad gate. A judge that cannot
    # separate good from bad cannot certify a win (Art. LXI).
    calib = (run_judge_calibration(judge_route)
             if judge_route.get("provider") else
             {"calibrated": False, "why": "no judge route (pipeline-only run)"})
    win_rate = (round((wins + 0.5 * ties) / usable, 3)
                if (usable and calib.get("calibrated")) else "NOT_MEASURED")
    import math
    ci = round(1.96 * math.sqrt(0.25 / usable), 3) if usable else None
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
                        "independence": "different provider+family from baseline; not 1.7B"},
        "judge_calibration": calib,
        "n_problems": len(problems),
        "subset": ("dev6" if subset_ids is not None
                   and set(subset_ids) == set(DEV6) else
                   ("all" if subset_ids is None else f"custom:{len(subset_ids)}")),
        "n_completed_pipeline": n_completed,
        "n_usable_pairs": usable,
        "pipeline_wins": wins, "baseline_wins": usable - wins - ties, "ties": ties,
        "BLIND_PAIRWISE_WIN_RATE": win_rate,
        "win_rate_95ci_pm": ci,
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
        f"pipeline wins {table['pipeline_wins']}  baseline wins "
        f"{table['baseline_wins']}  ties {table['ties']}",
        "",
        f"**BLIND PAIRWISE WIN-RATE: {table['BLIND_PAIRWISE_WIN_RATE']}** "
        f"({table['win_rate_95ci_pm']} CI half-width)",
        "",
        "fresh vs contaminated: " + json.dumps(table["fresh_vs_contaminated"]),
        "criterion mean diffs (pipeline-baseline): "
        + json.dumps(table["criterion_mean_diffs_pipeline_minus_baseline"]),
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


def _save(problem_id: str, name: str, rec: Dict[str, Any]) -> None:
    d = RUNS_ROOT / _commit / problem_id
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(rec, indent=1, default=str) + "\n",
                          encoding="utf-8")


def _run_pipeline_parallel(problems: List[Dict[str, Any]], workers: int,
                           timeout_s: int) -> None:
    """Run each pipeline problem in its own process with a hard timeout.

    A process exits at the timeout; the parent records the typed
    INCOMPLETE_INFRASTRUCTURE row (Art. LXI: infrastructure loss is
    never a refusal and never silently dropped). Process isolation also
    means an edit in the main tree cannot touch an in-flight run."""
    import subprocess
    from concurrent.futures import ThreadPoolExecutor, as_completed

    script = str(Path(__file__).resolve())

    def _one(p: Dict[str, Any]) -> Dict[str, Any]:
        pid = p["problem_id"]
        cmd = [sys.executable, "-B", script, "--arms", "pipeline",
               "--problems", pid, "--child"]
        t0 = time.time()
        try:
            cp = subprocess.run(cmd, cwd=str(REPO), capture_output=True,
                                text=True, timeout=timeout_s)
            return {"problem_id": pid, "state": "DONE",
                    "returncode": cp.returncode,
                    "stdout": (cp.stdout or "")[-1600:],
                    "stderr": (cp.stderr or "")[-800:],
                    "wall_s": round(time.time() - t0, 1)}
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout or ""
            if isinstance(out, bytes):
                out = out.decode("utf-8", "replace")
            return {"problem_id": pid, "state": "TIMEOUT",
                    "returncode": "TIMEOUT",
                    "stdout": str(out)[-1600:], "stderr": "",
                    "wall_s": round(time.time() - t0, 1)}

    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(problems)))) as ex:
        futs = [ex.submit(_one, p) for p in problems]
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            print(f"[eval] {r['problem_id']}: {r['state']} "
                  f"({r['wall_s']}s, rc={r['returncode']})", flush=True)
            if r["state"] == "TIMEOUT":
                d = RUNS_ROOT / _commit / r["problem_id"] / "pipeline"
                rec = {
                    "answer": None, "completed": False,
                    "wall_s": r["wall_s"],
                    "final_status": "INCOMPLETE_INFRASTRUCTURE",
                    "reason": f"hard per-problem timeout {timeout_s}s",
                    "engine_error": "TIMEOUT",
                    "child_stdout_tail": str(r.get("stdout") or "")[-1200:],
                    "stage_times_s": _stage_times(d),
                }
                _save(r["problem_id"], "pipeline_record.json", rec)
            elif r["returncode"] not in (0, None):
                # the child crashed before writing its record: record the
                # typed infrastructure failure instead of a silent gap
                rec_p = (RUNS_ROOT / _commit / r["problem_id"]
                         / "pipeline_record.json")
                if not rec_p.exists():
                    d = RUNS_ROOT / _commit / r["problem_id"] / "pipeline"
                    _save(r["problem_id"], "pipeline_record.json", {
                        "answer": None, "completed": False,
                        "wall_s": r["wall_s"],
                        "final_status": "INCOMPLETE_INFRASTRUCTURE",
                        "reason": f"child exit {r['returncode']}",
                        "engine_error": (r["stderr"] or "")[-400:],
                        "stage_times_s": _stage_times(d),
                    })


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="pipeline")
    ap.add_argument("--problems", default="all")
    ap.add_argument("--subset", default="all",
                    choices=["all", "dev6"])
    ap.add_argument("--workers", type=int, default=1,
                    help="parallel pipeline workers (process per problem)")
    ap.add_argument("--timeout", type=int, default=300,
                    help="hard per-problem timeout in seconds")
    ap.add_argument("--child", action="store_true",
                    help="internal: one problem in its own process")
    args = ap.parse_args(argv)
    arms = [a.strip().lower() for a in args.arms.split(",") if a.strip()]
    problems = json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]
    if args.subset == "dev6" and args.problems == "all":
        problems = [p for p in problems if p["problem_id"] in DEV6]
    if args.problems != "all":
        want = {p.strip() for p in args.problems.split(",") if p.strip()}
        problems = [p for p in problems if p["problem_id"] in want]

    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    (RUNS_ROOT / _commit).mkdir(parents=True, exist_ok=True)
    (RUNS_ROOT / _commit / "_run_meta.json").write_text(
        json.dumps({"commit": _commit, "dirty_tree": _dirty,
                    "dont_write_bytecode": bool(sys.dont_write_bytecode),
                    "executable": sys.executable,
                    "argv": list(argv or []),
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
        # judge route (different provider)
        jp = RUNS_ROOT / _commit / "_judge_route_probe.json"
        if jp.exists():
            judge_route = json.loads(jp.read_text(encoding="utf-8"))
        else:
            judge_route = probe_judge_route(route_rec.get("provider"))
            jp.write_text(json.dumps(judge_route, indent=1) + "\n",
                          encoding="utf-8")
        print(f"[eval] baseline route: {route_rec.get('provider')} / "
              f"{route_rec.get('model')} ({route_rec.get('state')})", flush=True)
        print(f"[eval] judge route: {judge_route.get('provider')} / "
              f"{judge_route.get('model')} ({judge_route.get('state')})", flush=True)

    pipeline_done = False
    if "pipeline" in arms and not args.child and args.workers > 1:
        _run_pipeline_parallel(problems, args.workers, args.timeout)
        pipeline_done = True
        arms = [a for a in arms if a != "pipeline"]

    for p in problems:
        pid = p["problem_id"]
        d = RUNS_ROOT / _commit / pid
        print(f"[eval] {pid}: start", flush=True)
        if "pipeline" in arms:
            rec = run_pipeline_problem(p, d / "pipeline")
            _save(pid, "pipeline_record.json", rec)
            print(f"[eval] {pid}: pipeline done ({rec['wall_s']}s, "
                  f"status={rec.get('final_status')}, completed={rec.get('completed')})",
                  flush=True)
        if "baseline" in arms:
            rec = run_baseline_problem(_intake_problem(p), d, route_rec)
            _save(pid, "baseline_record.json", rec)
            print(f"[eval] {pid}: baseline done "
                  f"({'ok' if rec.get('answer') else rec.get('blocked')})",
                  flush=True)
        if "judge" in arms:
            pr = d / "pipeline_record.json"
            ba = d / "baseline_record.json"
            if not (pr.exists() and ba.exists()):
                print(f"[eval] {pid}: judge skipped (missing arm records)", flush=True)
                continue
            pv = (json.loads(pr.read_text(encoding="utf-8")) or {}).get("answer")
            bv = (json.loads(ba.read_text(encoding="utf-8")) or {}).get("answer")
            # never hand a refusal to the judge: only completed pipeline pairs
            pipe_completed = (json.loads(pr.read_text(encoding="utf-8")) or {}).get("completed")
            if not pipe_completed:
                _save(pid, "judge_record.json", {"usable_pair": False,
                        "why": "pipeline did not release an answer"})
                print(f"[eval] {pid}: judge skipped (pipeline not completed)", flush=True)
                continue
            rec = run_judge_problem(_intake_problem(p), pv, bv, judge_route)
            _save(pid, "judge_record.json", rec)
            print(f"[eval] {pid}: judge -> "
                  f"{rec.get('winner') if rec.get('usable_pair') else rec.get('why')}",
                  flush=True)

    if args.child:
        return 0

    table = build_score_table(route_rec or {}, judge_route or {},
                              [p["problem_id"] for p in problems])
    write_table(table)
    print(json.dumps({k: table[k] for k in
                      ("commit", "dirty_tree", "pipeline_completion",
                       "yield_funnel_DEV", "wall_time", "speed",
                       "BLIND_PAIRWISE_WIN_RATE",
                       "n_usable_pairs", "pipeline_wins", "baseline_wins",
                       "ties", "judge_calibration")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

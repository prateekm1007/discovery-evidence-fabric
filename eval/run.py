#!/usr/bin/env python3
"""EVAL HARNESS for discovery-evidence-fabric (the mission's single metric).

Blind pairwise win-rate of the PIPELINE answer vs a BASE strong-model
answer, on the 18-problem eval set (eval/problems.json):

  (A) answers the asked question
  (B) uses user-stated variables
  (C) specific testable prediction
  (D) grounded in evidence

Arms
  pipeline  the current engine, run end-to-end per problem
            (EngineRun; resumeable).
  baseline  ONE single-shot completion by the strongest model reachable
            on ZERO-PAID routes at run time (localqwen today, under
            MODEL_COST_POLICY=ZERO_PAID_COST), answering the same
            question from the SAME frozen evidence snapshot the pipeline
            froze for that problem (mirrored from envelope_FREEZE.json,
            with its own same-evidence hash check).
  judge     blind pairwise comparison, BOTH switch orders, rubric-
            scored per criterion 1-5 plus overall preference. The judge
            model is recorded; judge==baseline model overlap is
            disclosed in the table.

Honesty rules
  - an arm that produced no answer scores nothing (excluded from the
    denominator, flagged). Never a win by default.
  - raw run artifacts stay in eval/runs/ and are NOT committed; the
    score table carries final-state hashes only.
  - the harness never grades the eval itself: every score above is a
    recorded model call (route + model + prompt hash + output hash).

Usage:
  python eval/run.py --arms pipeline            [--problems p1,p2]
  python eval/run.py --arms baseline,judge
  python eval/run.py --arms pipeline,baseline,judge

Output: eval/score/SCORE_TABLE.json + SCORE_TABLE.md (committed bytes).
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

# The zero-paid local transport: this env var is BOTH the availability
# marker and the endpoint URL (R453-LEAN); set it before ANY engine
# import so the availability matrix sees it. Only localqwen is usable
# without an operator credential key.
os.environ.setdefault("LOCAL_QWEN_BASE_URL",
                      "http://127.0.0.1:8790/v1/chat/completions")
os.environ.setdefault("MODEL_COST_POLICY", "ZERO_PAID_COST")

PROBLEMS = Path(__file__).resolve().parent / "problems.json"
RUNS_ROOT = Path(__file__).resolve().parent / "runs"
SCORE_DIR = Path(__file__).resolve().parent / "score"

CRITERIA = {
    "a_answered": "answers the asked question",
    "b_user_vars": "uses user-stated variables",
    "c_prediction": "gives a specific testable prediction",
    "d_evidence": "grounded in the provided evidence",
}


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


# ---------------------------------------------------------------------------
# arm: pipeline
# ---------------------------------------------------------------------------
def run_pipeline_problem(problem: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    """Full engine run (resumeable). Returns the extracted answer record."""
    final_state = out_dir / "final_state.json"
    resume = (out_dir / "envelope_RETRIEVE.json").exists() and not final_state.exists()
    t0 = time.time()
    status, err = None, None
    if not final_state.exists():
        try:
            from discovery_fabric.engine.run import EngineRun
            run = EngineRun(
                problem, str(out_dir),
                run_id=f"eval-{problem['problem_id']}",
                package_registry_path=str(out_dir / "PACKAGE_ID_REGISTRY.json"),
                with_package=False,
                resume=resume)
            manifest = run.run()
            status = manifest.get("final_status") if isinstance(manifest, dict) else None
        except Exception as exc:  # noqa: BLE001 - honest failure stays recorded
            err = f"{type(exc).__name__}: {exc}"[:400]
    record: Dict[str, Any] = {
        "answer": _extract_pipeline_answer(out_dir),
        "wall_s": round(time.time() - t0, 1),
        "engine_error": err,
        "same_evidence": _evidence_snapshot(out_dir),
        "pipeline_dir": str(out_dir),
    }
    if final_state.exists():
        fs = json.loads(final_state.read_text(encoding="utf-8"))
        record["final_status"] = fs.get("final_status")
        record["reason"] = fs.get("reason")
    return record


def _extract_pipeline_answer(out_dir: Path) -> Optional[str]:
    """The user-facing answer of a pipeline run: mechanism + causal answer
    + falsifier from the released spec, or the honest final reason when
    nothing was released."""
    spec_p = out_dir / "INVENTION_SPECIFICATION.json"
    parts: List[str] = []
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

            parts = [f"Mechanism: {val('mechanism')}",
                     f"Causal chain: {val('causal_chain')}",
                     f"What would falsify it: {val('killer_experiment')}"]
        except Exception as exc:  # noqa: BLE001
            parts.append(f"(spec unreadable: {exc})")

    if not any(p.split(":", 1)[-1].strip() for p in parts):
        fs = out_dir / "final_state.json"
        if fs.exists():
            f = json.loads(fs.read_text(encoding="utf-8"))
            parts = [f"The engine released no invention. Final status: "
                     f"{f.get('final_status')}. Reason: {f.get('reason')}"]
        else:
            return None
    return "\n".join(parts)[:6000]


def _evidence_snapshot(out_dir: Path) -> Optional[Dict[str, Any]]:
    """The pipeline's frozen evidence (envelope_FREEZE.json) with its own
    hash for the same-evidence check."""
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
# zero-paid route probe (baseline + judge share the admitted rung)
# ---------------------------------------------------------------------------
def probe_zero_paid_route() -> Dict[str, Any]:
    """Strongest zero-paid model REACHABLE right now (tier order; first
    PROBE_OK wins). Records every attempt - never a guess."""
    from discovery_fabric.engine import llm_registry as lr
    from discovery_fabric.engine import runtime_admission as ra
    candidates = [s for s in lr.PROVIDER_SPECS
                  if (s.cost_basis or "") in
                  {"ZERO_PAID_COST_SELF_HOSTED", "FREE_TIER_API"}]
    # ZERO_PAID order / quality: localqwen tier 4 last-resort is fine
    # because availability decides, not tier; sort by tier ascending.
    candidates.sort(key=lambda s: (s.quality_tier, s.cost_tier, s.latency_tier))
    attempts: List[Dict[str, Any]] = []
    for spec in candidates:
        if spec.provider_id != "localqwen" and not os.environ.get(spec.env_var, "").strip():
            attempts.append({"provider": spec.provider_id, "state": "NO_CREDENTIAL"})
            continue
        try:
            pr = ra.probe_capability(spec.provider_id, spec.default_model,
                                     timeout_s=120, persist_ledger=False)
            ok = bool(pr.get("ok") or pr.get("state") == "PROBE_OK")
        except Exception as exc:  # noqa: BLE001
            attempts.append({"provider": spec.provider_id,
                             "state": f"FAIL:{type(exc).__name__}"})
            continue
        attempts.append({"provider": spec.provider_id, "model": spec.default_model,
                         "state": "OK" if ok else (pr.get("state") or "PROBE_FAILED")})
        if ok:
            return {"provider": spec.provider_id, "model": spec.default_model,
                    "state": "OK", "probed": attempts, "at": utc_now()}
    return {"provider": None, "model": None,
            "state": "NO_ZERO_PAID_ROUTE_REACHABLE",
            "probed": attempts, "at": utc_now()}


def _pinned_generate(prompt: str, system: str, route: Dict[str, Any],
                     max_tokens: int, purpose: str) -> Dict[str, Any]:
    from discovery_fabric.engine import llm_registry as lr
    res = lr.generate(
        prompt, system=system, max_tokens=max_tokens, timeout=900,
        policy=lr.SelectionPolicy(preferred_providers=[route["provider"]],
                                  purpose=purpose),
        run_id=f"eval-{route.get('provider')}")
    return {"status": res.status, "provider_id": res.provider_id,
            "model": res.model, "content": res.content,
            "failures": list(res.failures)[:3], "_raw_failure_names": res.failures}


def run_baseline_problem(problem: Dict[str, Any], out_dir: Path,
                         route: Dict[str, Any]) -> Dict[str, Any]:
    snap = _evidence_snapshot(out_dir / "pipeline")
    if not snap or not snap.get("items"):
        return {"answer": None,
                "blocked": "pipeline run produced no evidence snapshot"}
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
        "Evidence retrieved for this problem (use it; cite which item "
        "supports what):",
        "\n".join(ev_lines),
        "",
        "Answer directly, as a concise engineering recommendation "
        "(max ~500 words). State your proposed design/intervention, the "
        "expected measurable effect, and the test that would falsify it. "
        "If the evidence does not support a claim you want to make, say "
        "so instead of asserting it.",
    ])
    t0 = time.time()
    res = _pinned_generate(
        body,
        "You answer real engineering questions with specific, testable, "
        "honest answers.",
        route, max_tokens=900, purpose="eval:baseline")
    content = res.get("content") or ""
    if res.get("status") != "OK" or not content.strip():
        return {"answer": None, "blocked": str(res)[:300], "prompt_sha": _sha(body)}
    return {"answer": content[:8000], "route": {"provider": res.get("provider_id"),
                                                "model": res.get("model")},
            "latency_s": round(time.time() - t0, 1),
            "same_evidence_hash": snap["hash"], "evidence_ids": snap["ids"],
            "prompt_sha": _sha(body), "sha": _sha(content)}


# ---------------------------------------------------------------------------
# arm: judge (blind pairwise, both orders)
# ---------------------------------------------------------------------------
def _rubric_prompt(problem, a_text: str, b_text: str) -> str:
    return "\n".join([
        "You judge two engineering answers to the same user problem.",
        "Both answers had access to the same evidence packet retrieved "
        "for this problem.",
        "",
        f"DEVICE: {problem['device']}",
        f"FAILURE: {problem['failure']}",
        "USER'S STATED VARIABLES:",
        "- " + "\n- ".join(problem.get("user_variables", [])),
        f"USER'S QUESTION: {problem['question']}",
        "",
        "=== ANSWER A ===",
        a_text,
        "",
        "=== ANSWER B ===",
        b_text,
        "",
        "Score BOTH answers on four criteria, 1 (bad) to 5 (excellent):",
        "1 " + CRITERIA["a_answered"],
        "2 " + CRITERIA["b_user_vars"],
        "3 " + CRITERIA["c_prediction"],
        "4 " + CRITERIA["d_evidence"],
        "Grade strictly: an answer that is vague, generic, ignores the "
        "user's numbers, or asserts without evidence scores low. A "
        "quantified, testable, evidence-using answer scores high.",
        "Then state your overall preference. Answer ONLY with these lines:",
        "A1: <1-5>",
        "A2: <1-5>",
        "A3: <1-5>",
        "A4: <1-5>",
        "B1: <1-5>",
        "B2: <1-5>",
        "B3: <1-5>",
        "B4: <1-5>",
        "PREFER: A | B | TIE",
    ])


def run_judge_problem(problem: Dict[str, Any], pipe_ans: Optional[str],
                      base_ans: Optional[str], route: Dict[str, Any]) -> Dict[str, Any]:
    if not pipe_ans or not base_ans:
        return {"usable_pair": False,
                "why": ("pipeline answer missing" if not pipe_ans
                        else "baseline answer missing")}
    if not route.get("provider"):
        return {"usable_pair": False, "why": "no zero-paid route"}
    passes: List[Dict[str, Any]] = []
    for order in ("AB", "BA"):  # position debias
        a_text, b_text = ((pipe_ans, base_ans) if order == "AB"
                          else (base_ans, pipe_ans))
        prompt = _rubric_prompt(problem, a_text, b_text)
        res = _pinned_generate(
            prompt,
            "You are a strict blind rubric judge. English only. Follow "
            "the exact output lines.",
            route, max_tokens=300, purpose="eval:judge")
        if res.get("status") != "OK":
            passes.append({"order": order, "error": str(res)[:200]})
            continue
        raw = res.get("content", "")
        passes.append({"order": order, "raw": raw, **_parse_rubric(raw)})
    # aggregate position-debiased
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
        winner = "tie" if len(set(prefs)) > 1 else "tie"
    return {"usable_pair": True,
            "passes": len([p for p in passes if "error" not in p]),
            "scores": finals, "winner": winner, "pref_passes": prefs}


def _m(v: List[int]) -> float:
    return sum(v) / len(v)


def _parse_rubric(raw: str) -> Dict[str, Any]:
    import re
    fields: Dict[str, str] = {}
    for m in re.finditer(r"^\s*([AB][1-4]|PREFER)\s*[:=]\s*(.+)$",
                         raw or "", re.M):
        fields[m.group(1).upper()] = m.group(2).strip()[:8]
    prefer = fields.pop("PREFER", None)
    # validate
    for k, v in list(fields.items()):
        if k.startswith("PREFER"):
            continue
        if k in {f"{s}{j}" for s in "AB" for j in range(1, 5)}:
            try:
                fields[k] = str(int(v))
            except ValueError:
                fields.pop(k, None)
    return {**fields, "prefer": prefer}


# ---------------------------------------------------------------------------
# scoring table
# ---------------------------------------------------------------------------
def build_score_table(route_rec: Dict[str, Any]) -> Dict[str, Any]:
    commit_dir = RUNS_ROOT / _commit
    problems = json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]
    rows, usable = [], 0
    wins = ties = 0
    crit_means: Dict[str, List[float]] = {c: [] for c in CRITERIA}
    for p in problems:
        d = commit_dir / p["problem_id"]
        pipe = _rec(d, "pipeline_record.json")
        base = _rec(d, "baseline_record.json")
        judge = _rec(d, "judge_record.json")
        snap_hash = (pipe.get("same_evidence") or {}).get("hash")
        same = bool(snap_hash and snap_hash == base.get("same_evidence_hash"))
        row = {
            "problem_id": p["problem_id"],
            "question_type": p["question_type"],
            "pipeline_final_status": pipe.get("final_status"),
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
            "hashes": {
                "pipeline_answer_sha": _sha(pipe.get("answer") or "")[:16] if pipe.get("answer") else None,
                "baseline_answer_sha": _sha(base.get("answer") or "")[:16] if base.get("answer") else None,
            },
        }
        rows.append(row)
        if judge.get("usable_pair"):
            usable += 1
            if judge.get("winner") == "pipeline":
                wins += 1
            elif judge.get("winner") == "tie":
                ties += 1
            for c in CRITERIA:
                diff = (judge.get("scores") or {}).get(c, {}).get("diff")
                if diff is not None:
                    crit_means[c].append(diff)
    win_rate = round((wins + 0.5 * ties) / usable, 3) if usable else None
    import math
    ci = round(1.96 * math.sqrt(0.25 / usable), 3) if usable else None
    return {
        "metric": "blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)",
        "criteria": CRITERIA,
        "commit": _commit,
        "generated_at": utc_now(),
        "baseline_route": {k: route_rec.get(k) for k in ("provider", "model", "state", "at")},
        "judge_route": {"provider": route_rec.get("provider"),
                        "model": route_rec.get("model"),
                        "note": ("judge and baseline arms share the same "
                                 "route model (single zero-paid transport "
                                 "on this host)")},
        "n_problems": len(problems),
        "n_usable_pairs": usable,
        "pipeline_wins": wins,
        "baseline_wins": usable - wins - ties,
        "ties": ties,
        "BLIND_PAIRWISE_WIN_RATE": win_rate,
        "win_rate_95ci_pm": ci,
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
        gen_s = (ev.get("gen1") or ev.get("iterations") or None)
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
        f"# eval score table (commit {table['commit']}, {table['generated_at']})",
        "",
        f"metric: {table['metric']}",
        "criteria: " + "; ".join(f"{k.split('_', 1)[0]}={v}"
                                for k, v in table["criteria"].items()),
        "",
        f"baseline route: {table['baseline_route'].get('provider')} / "
        f"{table['baseline_route'].get('model')} "
        f"({table['baseline_route'].get('state')})",
        f"judge route: {table['judge_route'].get('provider')} / "
        f"{table['judge_route'].get('model')}",
        "",
        f"n usable pairs: {table['n_usable_pairs']}/{table['n_problems']}  "
        f"pipeline wins {table['pipeline_wins']}  baseline wins "
        f"{table['baseline_wins']}  ties {table['ties']}",
        "",
        f"**BLIND PAIRWISE WIN-RATE: {table['BLIND_PAIRWISE_WIN_RATE']}** "
        f"({table['win_rate_95ci_pm']} CI half-width)",
        "",
        "criterion mean diffs (pipeline-baseline): "
        + json.dumps(table["criterion_mean_diffs_pipeline_minus_baseline"]),
        "",
        "| problem | type | final_status | fallback_gen1 | same ev | winner | crit diffs |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in table["rows"]:
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} |".format(
                r["problem_id"], r["question_type"],
                r["pipeline_final_status"], r["synthesis_fallback"],
                r["same_evidence"], r["winner"],
                json.dumps(r["criterion_diffs"], default=str)[:150]))
    (SCORE_DIR / "SCORE_TABLE.md").write_text("\n".join(lines) + "\n",
                                              encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
_commit = git_short()


def _save(problem_id: str, name: str, rec: Dict[str, Any]) -> None:
    d = RUNS_ROOT / _commit / problem_id
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(rec, indent=1, default=str) + "\n",
                          encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="pipeline")
    ap.add_argument("--problems", default="all")
    args = ap.parse_args(argv)
    arms = [a.strip().lower() for a in args.arms.split(",") if a.strip()]
    problems = json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]
    if args.problems != "all":
        want = {p.strip() for p in args.problems.split(",") if p.strip()}
        problems = [p for p in problems if p["problem_id"] in want]

    route_rec: Dict[str, Any] = {}
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
        print(f"[eval] baseline/judge route: "
              f"{route_rec.get('provider')} / {route_rec.get('model')} "
              f"({route_rec.get('state')})", flush=True)

    for p in problems:
        pid = p["problem_id"]
        d = RUNS_ROOT / _commit / pid
        print(f"[eval] {pid}: start", flush=True)
        if "pipeline" in arms:
            rec = run_pipeline_problem(p, d / "pipeline")
            _save(pid, "pipeline_record.json", rec)
            print(f"[eval] {pid}: pipeline done ({rec['wall_s']}s, "
                  f"status={rec.get('final_status')})", flush=True)
        if "baseline" in arms:
            rec = run_baseline_problem(p, d, route_rec)
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
            rec = run_judge_problem(p, pv, bv, route_rec)
            _save(pid, "judge_record.json", rec)
            print(f"[eval] {pid}: judge -> "
                  f"{rec.get('winner') if rec.get('usable_pair') else rec.get('why')}",
                  flush=True)

    table = build_score_table(route_rec or
                              _probe_route_rec())
    write_table(table)
    print(json.dumps({k: table[k] for k in
                      ("BLIND_PAIRWISE_WIN_RATE", "n_usable_pairs",
                       "pipeline_wins", "baseline_wins", "ties")}, indent=1))
    return 0


def _probe_route_rec() -> Dict[str, Any]:
    probe_p = RUNS_ROOT / _commit / "_route_probe.json"
    if probe_p.exists():
        return json.loads(probe_p.read_text(encoding="utf-8"))
    return {}


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r175_cmb_run.py — the DIR-2 compute-matched baseline RUN (claim
c-0276; the prereg eval/r175_cmb_prereg.json GOVERNS — AM44: criteria
before data; AM52 capability-first, R174-F1).

WHAT IT MEASURES (one run per item per arm, byte-resume, cache off):
  PIPELINE arm  = EngineRun end-to-end (15 canonical stages, cache
                  off, governor cap 12) + the DOMINANCE-INJECTED
                  final compose (the baseline's best answer ENTERS
                  the composer's candidate pool — the pipeline can
                  only lose if its final selection is worse than
                  baseline_best).
  BASELINE arm  = K_i INDEPENDENT single-shot draws on the SAME frozen
                  evidence packet (the engine's own composer prompt
                  bytes, candidates empty, verification absent — one
                  raw agnes-3.0-flash call per draw, no repair
                  retries) + ONE critique call selecting the best
                  (deterministic backup: fewest bill_defect_classes,
                  tie -> draw 1; typed-fail draws score +inf).
  K_i            = the pipeline run's own recorded LLM call count:
                  max(governor healthy+retry, routing-ledger
                  RUN_OWNED rows for run_id r175-cmb-pipe-{pid}).

BLIND JUDGING (machine panel = INPUT; the reviewer's blind judgment
from the committed review packets is the GATE — AM52 'auditor-judged'):
  per pair, seeded A/B assignment committed BEFORE judging; TWO passes
  order-swapped; the seat ladder is the established panel transport
  (budget ladder + contract-reminder retries INSIDE one leg, all
  attempts recorded; a leg that exhausts its ladder is typed
  INVALID_LEG and is never re-run as a fresh leg).

Usage:
  python3 scripts/r175_cmb_run.py --phase probe     # seat probes
  python3 scripts/r175_cmb_run.py --phase pipeline  [--only PID]
  python3 scripts/r175_cmb_run.py --phase baseline  [--only PID]
  python3 scripts/r175_cmb_run.py --phase dominance [--only PID]
  python3 scripts/r175_cmb_run.py --phase abmap
  python3 scripts/r175_cmb_run.py --phase judge     [--only PID]
  python3 scripts/r175_cmb_run.py --phase packets

Writes: eval/r175_cmb_run/ (committed in ONE commit at the end — the
12 DEV pairs land together per the prereg; per-item files are the
byte-resume checkpoints).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import secrets
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r175_cmb_run"
OUT.mkdir(parents=True, exist_ok=True)
SCRATCH = REPO / "ENGINE_RUNS" / "r175_cmb"

from r7_queue_runner import _load_key_vault  # noqa: E402

_load_key_vault()

import discovery_fabric.engine.route_adapter as ra  # noqa: E402
from discovery_fabric.engine.answer_composer import (  # noqa: E402
    COMPOSE_MAX_TOKENS, _COMPOSER_SYSTEM, _candidates_block,
    _packet_block, _variables_block, _verification_block, compose_answer)
from discovery_fabric.engine.answer_contract import (  # noqa: E402
    ANSWER_SHAPE_BLOCK)
from discovery_fabric.engine.constraint_audit import (  # noqa: E402
    CONSTRAINT_CHECK_BLOCK_SPEC, numbered_constraints_block,
    strip_constraint_check)
from discovery_fabric.engine.run import EngineRun  # noqa: E402
from r121_successor_score import bill_defect_classes  # noqa: E402

V = "agnes-3.0-flash"
SESSION = "builder-r175s1"
WORK_ID = "r175-compute-matched-baseline-dev12"
CORPUS = REPO / "eval" / "problems_dev12.json"
PACE_S = 8.0

# the qualified serving seats (availability-probed at --phase probe;
# hy4f joins only if probed live — the cent-ai outage is measured,
# not assumed). agnes holds NO seat (generator isolation, Art. 26).
SEATS = {
    "snlite": {"model": "sensenova/sensenova-6.8-flash-lite",
               "family": "sensenova", "transport": "xkiro",
               "budgets": [12000], "timeout_s": 240.0, "pace": 6},
    "gpt6luna": {"model": "openai/gpt-6-luna", "family": "openai",
                 "transport": "ctai", "budgets": [4000, 8000, 12000],
                 "timeout_s": 240.0, "pace": 6},
    "hy4f": {"model": "hy4-flash:free", "family": "hy4",
             "transport": "cent", "budgets": [4000, 8000, 12000],
             "timeout_s": 240.0, "pace": 6},
}

JUDGE_SYSTEM = ("You are a rigorous blind judge comparing two "
                "candidate engineering answers for the same problem. "
                "You see only the two answers (A and B) — never their "
                "provenance. Respond only with the required JSON.")

JUDGE_TASK = """You judge TWO candidate engineering answers (ANSWER A and ANSWER B) for the same problem, against the same frozen evidence packet.

PROBLEM:
- Device: {device}
- Failure: {failure}
- Failure mode: {failure_mode}
- Constraint: {constraint}

FROZEN EVIDENCE PACKET (the only citable evidence for either answer):
{packet_block}

=== {first_label} ===
{first_text}

=== {second_label} ===
{second_text}

Judge, in order:
1. NOVELTY: which answer proposes the less obvious, less routine mechanism — beyond what the packet's own items already teach and beyond standard engineering practice?
2. FEASIBILITY: which answer is more physically sound at the stated scale, respects the stated constraint, and carries concrete parameter values?
3. GROUNDING: which answer uses the packet's evidence more honestly (numbers traceable to the packet, no fabricated figures or citations)?
4. OVERALL: which is the better engineering answer overall? TIE only if they are genuinely indistinguishable in quality.

Respond with ONLY this JSON object (no other text):
{{"winner": "A" | "B" | "TIE",
 "novelty": "A" | "B" | "EVEN",
 "feasibility": "A" | "B" | "EVEN",
 "grounding": "A" | "B" | "EVEN",
 "rationale": "one sentence"}}"""

CRITIQUE_SYSTEM = ("You are the selection critic for independent "
                   "single-shot engineering answers. Respond only "
                   "with the required JSON.")

CRITIQUE_TASK = """You are the selection critic. {n} INDEPENDENT single-shot engineering answers were written for the same problem. Select the single best answer.

PROBLEM:
- Device: {device}
- Failure: {failure}
- Failure mode: {failure_mode}
- Constraint: {constraint}

FROZEN EVIDENCE PACKET (the only citable evidence; cite item ids):
{packet_block}

THE {n} CANDIDATE ANSWERS:
{numbered_answers}

Select the best: the answer that is the most physically sound, respects the stated constraint, uses the packet's evidence honestly, and proposes the most inventive (non-routine) mechanism.

Respond with ONLY this JSON object (no other text):
{{"best": <the candidate number 1..{n}>, "reason": "one sentence"}}"""


# ---------------------------------------------------------------- transport

# THE ENGINE'S OWN REGISTERED TRANSPORT (measured in the wiring smoke:
# the pipeline's stage calls ride the llm_registry cascade — xkiro/
# qwen/qwen3.5-plus:free in this window, NOT direct agnes; the
# baseline arm MUST ride the same route or the arms are not
# compute-matched on the generator). llm_generate is the ONE engine
# transport wrapper (mechanism_space.llm_generate) — the same path
# the pipeline stages and the dominance compose use.
from discovery_fabric.engine.mechanism_space import llm_generate  # noqa: E402


def engine_call(prompt: str, system: str = "", target: int = 1400,
                what: str = "", purpose: str = "r175_cmb",
                attempts_out: list | None = None) -> tuple[str, dict]:
    """The established transport backoff (4 attempts, 120 s sleeps,
    rate_limited/transport ONLY; parse failures NEVER retried here)
    around the engine's llm_generate. Returns (content, meta) where
    meta records the provider_route actually served (the generator of
    record for the arm — provider/model per call, Art. 11)."""
    last: Exception | None = None
    for attempt in (1, 2, 3, 4):
        if attempts_out is not None:
            attempts_out.append(attempt)
        try:
            r = llm_generate(prompt, system=system, timeout=300,
                             max_tokens=target, purpose=purpose)
            if not r.get("ok") or not (r.get("content") or "").strip():
                raise RuntimeError(
                    f"transport not ok: {str(r.get('error')
                                              or r.get('status'))[:160]}")
            meta = {"provider_route": r.get("provider_route"),
                    "model": r.get("model"),
                    "usage": r.get("usage")}
            return (r.get("content") or ""), meta
        except ra.RouteRefused as e:
            if e.kind in ("auth", "missing_key"):
                raise
            last = e
            print(f"    {what} attempt {attempt} refused ({e.kind});"
                  f" backoff 120s", flush=True)
            if attempt < 4:
                time.sleep(120)
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"    {what} attempt {attempt} failed "
                  f"{type(e).__name__}: {str(e)[:160]}; backoff 120s",
                  flush=True)
            if attempt < 4:
                time.sleep(120)
    raise last if last else RuntimeError("transport backoff exhausted")


def _seat_transport(seat: dict):
    if seat["transport"] == "xkiro":
        return ra.xkiro_chat
    if seat["transport"] == "ctai":
        return ra.ctai_chat
    return ra.cent_ai_chat


def _parse_json_obj(raw: str, required: set) -> dict:
    txt = (raw or "").strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.startswith("json"):
            txt = txt[4:]
    a, b = txt.find("{"), txt.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("no JSON object in the response")
    d = json.loads(txt[a:b + 1])
    if not isinstance(d, dict) or not required.issubset(d.keys()):
        missing = sorted(required - set(d.keys() if isinstance(
            d, dict) else []))
        raise ValueError(f"missing keys: {missing}")
    return d


JUDGE_KEYS = {"winner", "novelty", "feasibility", "grounding",
              "rationale"}
CRITIQUE_KEYS = {"best", "reason"}


def seat_probe() -> dict:
    """Live/dead probe per seat; hy4f joins only on a live probe."""
    st = {}
    for tag, seat in SEATS.items():
        try:
            t0 = time.monotonic()
            r = _seat_transport(seat)(
                [{"role": "user",
                  "content": "Reply with the single word: READY."}],
                model=seat["model"], max_tokens=2000,
                timeout_s=90.0)
            ok = bool((r.get("content") or "").strip())
            st[tag] = {"live": ok,
                       "latency_s": round(time.monotonic() - t0, 1),
                       "error": r.get("error") or None}
        except Exception as e:  # noqa: BLE001
            st[tag] = {"live": False, "error":
                       f"{type(e).__name__}: {str(e)[:120]}"}
        print(f"seat {tag}: {'LIVE' if st[tag]['live'] else 'DEAD'} "
              f"{st[tag].get('error') or ''}", flush=True)
    live_fams = sorted({SEATS[t]["family"] for t, v in st.items()
                        if v["live"]})
    st["_live_families"] = live_fams
    st["_panel_ok"] = len(live_fams) >= 2
    (OUT / "seat_probe.json").write_text(
        json.dumps(st, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"panel_ok={st['_panel_ok']} families={live_fams}",
          flush=True)
    return st


# ------------------------------------------------------------- the corpus

def problems() -> list:
    d = json.loads(CORPUS.read_text(encoding="utf-8"))
    return d.get("problems", d) if isinstance(d, dict) else d


def _packet_text(packet: list) -> str:
    return _packet_block(packet)


def single_shot_prompt(prob: dict, packet_text: str) -> str:
    """The engine's OWN composer prompt bytes, single-shot form:
    candidates EMPTY (no pipeline-generated candidates), verification
    ABSENT (no staged verification) — the same problem block, the
    same frozen packet, the same answer-shape contract."""
    qt = str(prob.get("question_type") or "intervention-proposal")
    shape = ANSWER_SHAPE_BLOCK.get(qt, "")
    from discovery_fabric.engine.answer_composer import _COMPOSER_PROMPT
    return _COMPOSER_PROMPT.format(
        device=prob.get("device", ""),
        failure=prob.get("failure", ""),
        failure_mode=prob.get("failure_mode", ""),
        variables_block=_variables_block(prob),
        numbered_constraints=numbered_constraints_block(prob),
        candidates_block=_candidates_block([]),
        packet_block=packet_text,
        verification_block=_verification_block(None),
        shape_hint="" if shape else " (none — unknown question type)",
        shape_block=shape,
        constraint_check_spec=CONSTRAINT_CHECK_BLOCK_SPEC)


# ------------------------------------------------------------- phase: pipe

def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _ledger_run_owned(run_id: str) -> tuple:
    """(count, provider/model distribution) of RUN_OWNED ledger rows
    for the run — the pipeline arm's generator of record (Art. 11:
    independence is tracked, the generator is recorded per arm)."""
    led = REPO / "ENGINE_RUNS" / "model_routing" / "ledger.jsonl"
    if not led.exists():
        return 0, {}
    n, dist = 0, {}
    for line in led.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (row.get("run_id") == run_id
                and row.get("call_class") == "RUN_OWNED"):
            n += 1
            key = f"{row.get('provider')}/{row.get('model')}"
            dist[key] = dist.get(key, 0) + 1
    return n, dist


def phase_pipeline(prob: dict) -> dict:
    pid = prob["problem_id"]
    outfile = OUT / f"{pid}_pipeline.json"
    if outfile.exists():
        print(f"{pid}: pipeline resumed", flush=True)
        return _read(outfile)
    out_dir = SCRATCH / f"pipe_{pid}"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"r175-cmb-pipe-{pid}"
    t0 = time.monotonic()
    print(f"=== PIPELINE {pid} (EngineRun, cache off) ...", flush=True)
    run = EngineRun(dict(prob), str(out_dir), run_id=run_id,
                    with_package=False, resume=True)
    manifest = run.run()
    wall = round(time.monotonic() - t0, 1)

    ce_p = out_dir / "candidate_envelope.json"
    ac_p = out_dir / "ANSWER_COMPOSED.json"
    fs_p = out_dir / "final_state.json"
    le_p = out_dir / "LLM_ECONOMY.json"
    if not ce_p.exists():
        rec = {"pid": pid, "state": "PIPELINE_NO_ENVELOPE",
               "manifest_status": (manifest or {}).get("final_status"),
               "wall_s": wall}
        outfile.write_text(json.dumps(rec, indent=1,
                                     ensure_ascii=False) + "\n",
                           encoding="utf-8")
        return rec
    ce, ac, fs = _read(ce_p), _read(ac_p), _read(fs_p)
    le = _read(le_p) if le_p.exists() else {}
    gov = le.get("governor") or {}
    ledger_n, gen_dist = _ledger_run_owned(run_id)
    K = max(int(gov.get("healthy_calls") or 0)
            + int(gov.get("retry_attempts") or 0), ledger_n)
    packet = ce.get("evidence") or []
    verification = {
        "attack_overall": fs.get("adversarial_overall"),
        "physics_status": ((fs.get("physics") or {}).get("verdict")
                           or (fs.get("physics") or {}).get("overall")),
        "contradiction_status": ((fs.get("contradictions") or {})
                                 .get("overall")),
        "premise_gate": ((fs.get("premise_gate") or {})
                         .get("verdict")),
        "final_status": fs.get("final_status"),
    }
    internal, _ = strip_constraint_check(
        str(ac.get("answer") or ""))
    rec = {
        "pid": pid, "state": "OK", "run_id": run_id, "wall_s": wall,
        "K_i": K,
        "generator_of_record": {
            "note": "the engine's registered route (the llm_registry "
                    "cascade) served the pipeline's stage calls; "
                    "per-call provider_route in the routing ledger "
                    "(the ledger rows are the byte record)",
            "ledger_run_owned_distribution": gen_dist},
        "governor_stops": (gov.get("stops") or []),
        "call_accounting": {
            "governor_healthy": gov.get("healthy_calls"),
            "governor_retries": gov.get("retry_attempts"),
            "ledger_run_owned": ledger_n,
            "compose_internal_n_llm_calls": ac.get("n_llm_calls"),
            "formula": "K_i = max(governor healthy+retry, ledger "
                       "RUN_OWNED)"},
        "final_status": fs.get("final_status"),
        "evidence_packet_ids": [str(e.get("id")
                                   or e.get("source_id") or "?")
                                for e in packet],
        "packet_block_text": _packet_text(packet),
        "admitted_candidates": ac.get("admitted_candidates") or [],
        "pipeline_answer_internal": internal,
        "composer_state_internal": ac.get("state"),
        "verification": verification,
    }
    outfile.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                       + "\n", encoding="utf-8")
    print(f"{pid}: pipeline OK (K_i={K}, status="
          f"{fs.get('final_status')}, wall={wall}s)", flush=True)
    return rec


# --------------------------------------------------------- phase: baseline

def phase_baseline(prob: dict, pipe_rec: dict) -> dict:
    pid = prob["problem_id"]
    outfile = OUT / f"{pid}_baseline.json"
    if outfile.exists():
        print(f"{pid}: baseline resumed", flush=True)
        return _read(outfile)
    K = int(pipe_rec.get("K_i") or 0)
    if pipe_rec.get("state") != "OK" or K < 1:
        rec = {"pid": pid, "state": "TYPED_NO_BUDGET",
               "reason": "pipeline record not OK or K_i<1"}
        outfile.write_text(json.dumps(rec, indent=1,
                                     ensure_ascii=False) + "\n",
                           encoding="utf-8")
        return rec
    # TYPED GOVERNOR HANDLING (disclosed in the prereg): the governor
    # is a PROCESS-GLOBAL per-problem instrument (cap 12) that the
    # pipeline's EngineRun already consumed; the baseline arm is a
    # STANDALONE call sequence whose budget is its own K_i draws + 1
    # critique (driver-enforced below) — a FRESH scope with the cap
    # disabled for THIS arm's calls, never an unbounded lane: the
    # draw loop is exactly N draws + 1 critique, recorded per item.
    from discovery_fabric.engine import llm_economy as _econ
    os.environ["FABRIC_PROBLEM_CALL_CAP"] = "0"
    _econ.reset_governor(f"r175-cmb-baseline-{pid}")
    out_dir = SCRATCH / f"pipe_{pid}"
    ce = _read(out_dir / "candidate_envelope.json")
    packet_text = _packet_text(ce.get("evidence") or [])
    prompt = single_shot_prompt(prob, packet_text)
    n_draws = K
    print(f"=== BASELINE {pid}: {n_draws} draws + 1 critique ...",
          flush=True)
    draws, fails = [], 0
    for k in range(1, n_draws + 1):
        attempts: list = []
        t0 = time.monotonic()
        try:
            raw, meta = engine_call(
                prompt, system=_COMPOSER_SYSTEM, target=1400,
                what=f"{pid} draw {k}",
                purpose=f"r175_cmb_baseline_draw")
            answer, _ = strip_constraint_check(raw.strip())
            defects = bill_defect_classes(prob, answer)
            draws.append({"draw": k, "state": "OK", "answer": answer,
                          "defect_classes": defects,
                          "transport_attempts": attempts,
                          "generator": {"model": meta.get("model"),
                                        "provider_route":
                                            meta.get("provider_route")},
                          "latency_s": round(time.monotonic() - t0, 1)})
            print(f"  draw {k}/{n_draws} ok "
                  f"({len(answer)} ch, defects={defects})", flush=True)
        except Exception as e:  # noqa: BLE001
            fails += 1
            draws.append({"draw": k, "state": "TYPED_CALL_FAIL",
                          "error": f"{type(e).__name__}: "
                                   f"{str(e)[:160]}",
                          "transport_attempts": attempts})
            print(f"  draw {k}/{n_draws} TYPED_CALL_FAIL", flush=True)
        if k < n_draws:
            time.sleep(PACE_S)
    ok_draws = [d for d in draws if d.get("state") == "OK"]
    if not ok_draws:
        rec = {"pid": pid, "state": "TYPED_CALL_FAIL",
               "n_draws": n_draws,
               "reason": "all baseline draws failed transport"}
        outfile.write_text(json.dumps(rec, indent=1,
                                     ensure_ascii=False) + "\n",
                           encoding="utf-8")
        return rec

    numbered = "\n\n".join(
        f"CANDIDATE {d['draw']}:\n{d['answer']}" for d in ok_draws)
    cp = CRITIQUE_TASK.format(
        n=len(ok_draws), device=prob.get("device", ""),
        failure=prob.get("failure", ""),
        failure_mode=prob.get("failure_mode", ""),
        constraint=prob.get("constraint", ""),
        packet_block=packet_text, numbered_answers=numbered)
    crit_attempts: list = []
    critique = {"state": "TYPED_PARSE_FAIL"}
    try:
        raw, cmeta = engine_call(
            cp, system=CRITIQUE_SYSTEM, target=600,
            what=f"{pid} critique", purpose="r175_cmb_baseline_critique")
        parsed = _parse_json_obj(raw, CRITIQUE_KEYS)
        best = int(parsed.get("best"))
        ok_numbers = [d["draw"] for d in ok_draws]
        if best in ok_numbers:
            critique = {"state": "OK", "best": best,
                        "reason": parsed.get("reason"),
                        "generator": {"model": cmeta.get("model")}}
        else:
            critique = {"state": "TYPED_OUT_OF_RANGE", "best": best,
                        "reason": parsed.get("reason")}
    except Exception as e:  # noqa: BLE001
        critique = {"state": "TYPED_PARSE_FAIL",
                    "error": f"{type(e).__name__}: {str(e)[:160]}"}
        print(f"  critique parse-fail -> deterministic rule",
              flush=True)

    # deterministic backup rule (fewest defect classes; tie -> draw 1)
    det = min(ok_draws, key=lambda d: (len(d["defect_classes"]),
                                        d["draw"]))
    if critique.get("state") == "OK":
        pick = next(d for d in ok_draws
                    if d["draw"] == critique["best"])
        rule = "critique"
    else:
        pick = det
        rule = "deterministic_fewest_defects"
    rec = {
        "pid": pid, "state": "OK", "N_draws": n_draws,
        "draws": draws, "draw_fails": fails,
        "critique": critique, "critique_attempts": crit_attempts,
        "selection_rule_applied": rule,
        "baseline_best": pick["answer"],
        "baseline_best_draw": pick["draw"],
        "baseline_best_defects": pick["defect_classes"],
        "calls_total": n_draws + (1 if critique.get("state") == "OK"
                                  else 0),
    }
    outfile.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                       + "\n", encoding="utf-8")
    print(f"{pid}: baseline OK (best=draw {pick['draw']}, rule="
          f"{rule})", flush=True)
    return rec


# -------------------------------------------------------- phase: dominance

def phase_dominance(prob: dict, pipe_rec: dict,
                    base_rec: dict) -> dict:
    pid = prob["problem_id"]
    outfile = OUT / f"pair_{pid}.json"
    if outfile.exists():
        print(f"{pid}: pair resumed", flush=True)
        return _read(outfile)
    # a FRESH governor scope for the arm's selection step (the process
    # may have consumed an earlier scope; 1-3 calls, cap far away).
    # The baseline phase disabled the cap for its standalone budget —
    # RESTORE the engine's default cap here (the dominance compose is
    # the pipeline arm's step and rides the engine's instrument).
    from discovery_fabric.engine import llm_economy as _econ
    os.environ["FABRIC_PROBLEM_CALL_CAP"] = "12"
    _econ.reset_governor(f"r175-cmb-dominance-{pid}")
    if pipe_rec.get("state") != "OK" or base_rec.get("state") != "OK":
        rec = {"pid": pid, "state": "TYPED_ARM_INCOMPLETE",
               "pipeline_state": pipe_rec.get("state"),
               "baseline_state": base_rec.get("state")}
        outfile.write_text(json.dumps(rec, indent=1,
                                     ensure_ascii=False) + "\n",
                           encoding="utf-8")
        return rec
    out_dir = SCRATCH / f"pipe_{pid}"
    ce = _read(out_dir / "candidate_envelope.json")
    packet = ce.get("evidence") or []
    best = base_rec["baseline_best"]
    cand = list(pipe_rec.get("admitted_candidates") or [])
    pool = cand + [{"candidate_id": f"r175-baseline-best-{pid}",
                    "attack_verdict": None, "hypothesis": best}]
    t0 = time.monotonic()
    rec_c = compose_answer(
        dict(prob), packet, pool,
        pipe_rec.get("verification") or {},
        str(prob.get("question_type") or "intervention-proposal"))
    wall = round(time.monotonic() - t0, 1)
    answer, _ = strip_constraint_check(
        str(rec_c.get("answer") or ""))
    state = rec_c.get("state")
    ok = bool(answer.strip()) and state not in (
        "COMPOSE_FAILED_TRANSPORT", "COMPOSE_TRUNCATED", None)
    rec = {
        "pid": pid,
        "state": "OK" if ok else f"TYPED_{state or 'COMPOSE_FAILED'}",
        "dominance_pool_ids": [c.get("candidate_id") for c in pool],
        "baseline_best_in_pool": True,
        "pipeline_answer": answer if ok else None,
        "composer_state": state,
        "compose_error": rec_c.get("error"),
        "compose_n_llm_calls": rec_c.get("n_llm_calls"),
        "compose_generator": {"model": rec_c.get("model"),
                              "provider_route":
                                  rec_c.get("provider_route")},
        "pipeline_answer_internal_no_dominance":
            pipe_rec.get("pipeline_answer_internal"),
        "pipeline_answer_internal_no_dominance":
            pipe_rec.get("pipeline_answer_internal"),
        "call_accounting": {
            "pipeline_total_calls": int(pipe_rec["K_i"])
            + int(rec_c.get("n_llm_calls") or 0),
            "baseline_total_calls": base_rec["calls_total"],
            "pipeline_strict_within_budget":
                int(pipe_rec["K_i"]) + int(
                    rec_c.get("n_llm_calls") or 0)
                <= int(base_rec["calls_total"])},
        "wall_s": wall,
    }
    outfile.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                       + "\n", encoding="utf-8")
    print(f"{pid}: dominance compose {state} "
          f"({rec['call_accounting']})", flush=True)
    return rec


# ------------------------------------------------------- phase: ab map

def phase_abmap() -> dict:
    f = OUT / "ab_map.json"
    if f.exists():
        return _read(f)
    seed = secrets.token_hex(16)
    rng = random.Random(seed)
    probs = problems()
    amap = {"seed": seed, "generated_at": time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pairs": {}}
    for p in probs:
        pid = p["problem_id"]
        amap["pairs"][pid] = {
            "A": "pipeline" if rng.random() < 0.5 else "baseline",
        }
        amap["pairs"][pid]["B"] = ("baseline"
                                  if amap["pairs"][pid]["A"] == "pipeline"
                                  else "pipeline")
    f.write_text(json.dumps(amap, indent=1, ensure_ascii=False) + "\n",
                 encoding="utf-8")
    print(f"ab_map committed with seed {seed[:8]}... (before judging)",
          flush=True)
    return amap


# ------------------------------------------------------------ phase: judge

def phase_judge(only: str | None) -> None:
    amap = _read(OUT / "ab_map.json")
    probe_p = OUT / "seat_probe.json"
    if not probe_p.exists():
        raise SystemExit("seat probe missing — run --phase probe "
                         "first (fail closed)")
    probe = _read(probe_p)
    live = {t for t in SEATS if probe.get(t, {}).get("live")}
    fams = {SEATS[t]["family"] for t in live}
    if len(fams) < 2:
        raise SystemExit(
            f"fewer than 2 live non-agnes judge families "
            f"({sorted(live)}) — typed DEGRADED_PANEL; the reviewer's "
            f"blind judgment alone would decide (re-probe or proceed "
            f"without the machine panel)")
    for prob in problems():
        pid = prob["problem_id"]
        if only and pid != only:
            continue
        pair = _read(OUT / f"pair_{pid}.json")
        if pair.get("state") != "OK":
            print(f"{pid}: pair not OK — judged set skips (typed)",
                  flush=True)
            continue
        pa = pair.get("pipeline_answer")
        base = _read(OUT / f"{pid}_baseline.json")
        ba = base.get("baseline_best")
        assign = amap["pairs"][pid]
        texts = {"pipeline": pa, "baseline": ba}
        out_dir = SCRATCH / f"pipe_{pid}"
        ce = _read(out_dir / "candidate_envelope.json")
        packet_text = _packet_text(ce.get("evidence") or [])
        for tag in sorted(live):
            seat = SEATS[tag]
            for pno in (1, 2):
                jf = OUT / f"judgment_{tag}_{pid}_pass{pno}.json"
                if jf.exists():
                    continue
                if pno == 1:
                    first, second = "A", "B"
                else:
                    first, second = "B", "A"
                prompt = JUDGE_TASK.format(
                    device=prob.get("device", ""),
                    failure=prob.get("failure", ""),
                    failure_mode=prob.get("failure_mode", ""),
                    constraint=prob.get("constraint", ""),
                    packet_block=packet_text,
                    first_label=f"ANSWER {first}",
                    first_text=texts[assign[first]],
                    second_label=f"ANSWER {second}",
                    second_text=texts[assign[second]])
                leg = _seat_leg(seat, prompt)
                leg.update({"pid": pid, "seat": tag, "pass": pno,
                            "presented_order": f"{first},{second}"})
                jf.write_text(json.dumps(leg, indent=1,
                                         ensure_ascii=False) + "\n",
                              encoding="utf-8")
                print(f"{pid}: {tag} pass{pno} "
                      f"{leg['outcome']}", flush=True)
                time.sleep(seat["pace"])


def _seat_leg(seat: dict, prompt: str) -> dict:
    """One judging leg on the established panel transport: the
    budget ladder + the contract-reminder retry INSIDE one leg (all
    attempts recorded); a leg that exhausts its ladder is typed
    INVALID_LEG — never re-run as a fresh leg."""
    attempts, outcome, parsed = [], "TRANSPORT_FAILED", None
    p = prompt
    for attempt in range(1, 5):
        budget = seat["budgets"][min(attempt - 1,
                                      len(seat["budgets"]) - 1)]
        t0 = time.monotonic()
        try:
            kw = ({"stream": True}
                  if seat.get("transport") == "cent" else {})
            r = _seat_transport(seat)(
                [{"role": "system", "content": JUDGE_SYSTEM},
                 {"role": "user", "content": p}],
                model=seat["model"], max_tokens=budget,
                timeout_s=seat["timeout_s"], **kw)
            raw = r.get("content") or ""
            err = r.get("error")
        except Exception as e:  # noqa: BLE001
            raw, err = None, f"{type(e).__name__}: {str(e)[:160]}"
        attempts.append({"attempt": attempt, "budget": budget,
                         "latency_s": round(time.monotonic() - t0, 1),
                         "error": err})
        if raw:
            try:
                parsed = _parse_json_obj(raw, JUDGE_KEYS)
                if not all(parsed.get(k) in (
                        "A", "B", "TIE", "EVEN") for k in (
                        "winner", "novelty", "feasibility",
                        "grounding")):
                    raise ValueError("illegal axis value")
                outcome = "VALID"
                break
            except (ValueError, json.JSONDecodeError) as e:
                outcome = "PARSE_FAILED"
                if attempt < 4:
                    p = (prompt + "\n\nYour previous output violated "
                         "the contract (" + str(e)[:120] + "). Respond "
                         "with ONLY the JSON object with the five "
                         "keys, winner A|B|TIE and each axis A|B|EVEN."
                         " No other text.")
                    time.sleep(3)
        elif err and ("429" in str(err) or "Rate" in str(err)):
            outcome = "RATE_LIMITED"
            time.sleep(120)
        elif err and any(s in str(err) for s in (
                "503", "502", "timeout", "upstream", "Bad Gateway")):
            outcome = "TRANSIENT"
            time.sleep(30)
        elif attempt < 4:
            time.sleep(10)
    return {"outcome": outcome,
            "verdict": parsed if outcome == "VALID" else None,
            "attempts": attempts}


# ---------------------------------------------------- phase: review packets

def phase_packets() -> None:
    amap = _read(OUT / "ab_map.json")
    for prob in problems():
        pid = prob["problem_id"]
        pair = _read(OUT / f"pair_{pid}.json")
        if pair.get("state") != "OK":
            continue
        base = _read(OUT / f"{pid}_baseline.json")
        assign = amap["pairs"][pid]
        out_dir = SCRATCH / f"pipe_{pid}"
        ce = _read(out_dir / "candidate_envelope.json")
        packet_text = _packet_text(ce.get("evidence") or [])
        rp = {
            "pid": pid, "blinded": True,
            "note": ("The reviewer judges this pair blind; the A/B "
                     "assignment map lives in ab_map.json (committed "
                     "with this packet; the judge never sees it "
                     "inside the prompt)."),
            "problem": {k: prob.get(k) for k in (
                "problem_id", "device", "failure", "failure_mode",
                "constraint", "domain", "question_type", "question",
                "user_variables", "clarification_answer")},
            "frozen_evidence_packet": packet_text,
            "ANSWER_A": (pair.get("pipeline_answer")
                         if assign["A"] == "pipeline"
                         else base.get("baseline_best")),
            "ANSWER_B": (pair.get("pipeline_answer")
                         if assign["B"] == "pipeline"
                         else base.get("baseline_best")),
        }
        (OUT / f"review_packet_{pid}.json").write_text(
            json.dumps(rp, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"{pid}: review packet written", flush=True)


# ------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["probe", "pipeline", "baseline",
                             "dominance", "abmap", "judge", "packets"])
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    if args.phase == "probe":
        seat_probe()
        return 0
    if args.phase == "abmap":
        phase_abmap()
        return 0
    if args.phase == "packets":
        phase_packets()
        return 0

    for prob in problems():
        if args.only and prob["problem_id"] != args.only:
            continue
        pid = prob["problem_id"]
        if args.phase == "pipeline":
            phase_pipeline(prob)
        elif args.phase == "baseline":
            pipe = _read(OUT / f"{pid}_pipeline.json") \
                if (OUT / f"{pid}_pipeline.json").exists() else None
            if pipe is None:
                print(f"{pid}: pipeline record missing — run pipeline "
                      f"first", flush=True)
                continue
            phase_baseline(prob, pipe)
        elif args.phase == "dominance":
            pipe = _read(OUT / f"{pid}_pipeline.json") \
                if (OUT / f"{pid}_pipeline.json").exists() else {}
            base = _read(OUT / f"{pid}_baseline.json") \
                if (OUT / f"{pid}_baseline.json").exists() else {}
            phase_dominance(prob, pipe, base)
        elif args.phase == "judge":
            phase_judge(args.only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

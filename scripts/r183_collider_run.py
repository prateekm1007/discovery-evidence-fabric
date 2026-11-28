#!/usr/bin/env python3
"""r183_collider_run.py -- DIR-2 (AM53/AM54): the COLLIDER-WIRED
invention run + the PAIRED no-collider ablation.

WHAT CHANGES vs scripts/r176_invention_run.py (the pre-registered
invention instrument): ONE arm is added to the candidate pool -- the
open-collider 'collision' candidate already generated for every item in
eval/r176_invention_run/gen_*.json ('collider' key, scripts/
r178s1_collider_arm.py). Everything else is byte-faithful to r176:
same 24-item corpus, same strategy prompts, same baseline recipe
(4 plain draws + critique + revise), same obviousness subtraction
(Jaccard > 0.6 on MECH_PAT), same round-robin tournament with the
baseline in the pool and the baseline tie-break RETAINED, same blind
two-pass final judge (order-swapped, WIN only on both passes), same
AM53 exclusion taxonomy (dominance ties + plain wins excluded), same
Wilson 95% CI.

PAIRED ABLATION FROM ONE JUDGE WAVE: all unordered pairs of the
SIX-candidate pool (plain, departure, contradiction, relaxation,
collision, baseline) are judged once. The with-collider champion is the
max over all six; the no-collider champion is the max over the FIVE-node
subgraph (collision legs removed). Because the subgraph legs are
identical, this is a genuinely paired comparison at ~2 extra legs per
item, not a second independent run. The blind two-pass is run for each
arm's champion (one shared pass when both arms pick the same candidate).
The collider arm is KEPT only if it raises the genuine-win rate; the
pre-registered kill criterion (ship best-of-N+verifier, retire the
multi-stage architecture for invention) applies otherwise.

TYPED TRANSPORT ADAPTATION (availability-only, recorded per pair):
  * generator: DIRECT agnes-3.0-flash API (AGNES_BASE_URL, 2-key
    rotation, 4x120s backoff) -- the DIR-1 default generator. The
    sandbox has no `z-ai` CLI, so scripts/r40_machine_v77.start_gateway()
    cannot serve a completion here (measured HTTP 500). Same served
    model id, same prompts, same max_tokens/temperature as _gen_v77.
  * judge: the ONLY live preregistered substitute seat,
    tr-deepseek (deepseek/deepseek-v4.1-flash-1017-free via
    TOKENROUTER). ctai is 429 (burned ctai_dm38 key, per the owner's
    rotate note) and snlite is xkiro-quota-blocked (both measured this
    session). Same judge prompt, same bars, same budget; concurrency
    is a transport accelerator only (leg order is still randomized
    from the fixed SEED, deterministically precomputed).
  * GEN checkpoints from the canonical r176 run are READ ONLY
    (Art. 29(e)); merged/new bytes land in eval/r183_collider_run/.

Usage: python3 scripts/r183_collider_run.py [--only PID] [--workers N]
Writes: eval/r183_collider_run/{gen_,pair_}*.json
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import random
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r176_invention_run import (  # noqa: E402
    SEED, packet_of, task_of, strat_prompts, mech_phrases, wilson,
    NOVEL as NOVEL_BASE,
)

CORPUS = REPO / "eval" / "r176_invention_corpus" / "items.jsonl"
CANON_GEN = REPO / "eval" / "r176_invention_run"
OUT = REPO / "eval" / "r183_collider_run"
OUT.mkdir(exist_ok=True)
NOVEL = NOVEL_BASE + ("collision",)
TR_MODEL = "deepseek/deepseek-v4.1-flash-1017-free"
TR_BASE = "https://api.tokenrouter.com/v1"
AG_MODEL = "agnes-3.0-flash"
ROT = 0
ROT_LOCK = threading.Lock()


def env_keys() -> dict:
    out = {}
    for line in (REPO / ".env.keys").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def d12(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def _post(url: str, key: str, body: dict, timeout: float = 400.0) -> tuple:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:  # noqa: BLE001
            return e.code, {}
    except Exception as e:  # noqa: BLE001
        return -1, {"error": f"{type(e).__name__}: {str(e)[:120]}"}


def agnes(prompt: str, keys: dict, what: str = "") -> str:
    """The DIR-1 default generator: agnes-3.0-flash, 2-key rotation,
    4 attempts with 120 s backoff on 429/transport, immediate rotate on
    auth failure."""
    global ROT
    base = keys["AGNES_BASE_URL"].rstrip("/") + "/chat/completions"
    body = {"model": AG_MODEL, "max_tokens": 2600, "temperature": 0.0,
            "messages": [{"role": "system", "content": ""},
                         {"role": "user", "content": prompt}]}
    last = None
    for attempt in range(1, 5):
        with ROT_LOCK:
            key = keys["AGNES_API_KEY" if ROT % 2 == 0
                       else "AGNES_API_KEY_2"]
            ROT += 1
        st, rsp = _post(base, key, body, timeout=300.0)
        if st == 200:
            ch = (rsp.get("choices") or [{}])[0]
            txt = (ch.get("message") or {}).get("content") or ""
            if txt.strip():
                return txt
            last = RuntimeError("empty agnes content")
        else:
            last = RuntimeError(f"agnes HTTP{st}")
            if st in (401, 403):
                continue  # rotate immediately
        print(f"    {what} agnes attempt {attempt}: {last}; "
              f"backoff 120s", flush=True)
        if attempt < 4:
            time.sleep(120)
    raise last  # typed failure, never silently re-rolled


def judge(prompt: str, keys: dict, what: str = "") -> tuple:
    """One tr-deepseek judge leg. Returns (verdict, raw) where verdict
    in {X,Y,TIE}. 4 attempts x 120s on 429/transport."""
    body = {"model": TR_MODEL, "max_tokens": 12000,
            "include_reasoning": False,
            "messages": [{"role": "user", "content": prompt}]}
    last = None
    for attempt in range(1, 5):
        st, rsp = _post(TR_BASE + "/chat/completions",
                        keys["TOKENROUTER_API_KEY"], body)
        if st == 200:
            ch = (rsp.get("choices") or [{}])[0]
            txt = (ch.get("message") or {}).get("content") or ""
            up = txt.upper()
            v = ("X" if "VERDICT: X" in up else
                 "Y" if "VERDICT: Y" in up else
                 "TIE" if "VERDICT: TIE" in up else None)
            if v:
                return v, txt
            last = RuntimeError(f"unparseable judge: {txt[:60]!r}")
        else:
            last = RuntimeError(f"judge HTTP{st}: "
                                f"{str(rsp.get('error') or rsp)[:80]}")
            if st in (401, 403):
                break
        print(f"    {what} judge attempt {attempt}: {last}; "
              f"backoff 120s", flush=True)
        if attempt < 4:
            time.sleep(120)
    raise last


def judge_prompt(packet: str, task: str, x: str, y: str) -> str:
    return (
        "Two engineering INVENTION proposals for the same problem. "
        "Judge which is better on physical soundness (obeys physics "
        "and the stated constraints), genuine mechanism novelty (a new "
        "physical principle or coupling vs standard practice), and "
        "actionability (a concrete falsification test). Ignore length "
        "and style.\n\nPROBLEM:\n" + packet + "\n\nTASK:\n" + task
        + "\n\nPROPOSAL X:\n" + x[:4500]
        + "\n\nPROPOSAL Y:\n" + y[:4500]
        + "\n\nAnswer EXACTLY: VERDICT: X|Y|TIE")


def blind_prompt(packet: str, task: str, a: str, b: str) -> str:
    return (
        "You are a blind reviewer of engineering INVENTION proposals. "
        "Two proposals for the same problem; judge which is better on "
        "physical soundness (obeys physics and the stated constraints), "
        "genuine mechanism novelty (a new physical principle or coupling "
        "vs standard practice), and actionability (a concrete "
        "falsification test). Ignore length and style.\n\nPROBLEM:\n"
        + packet + "\n\nTASK:\n" + task + "\n\nPROPOSAL X:\n"
        + a[:4500] + "\n\nPROPOSAL Y:\n" + b[:4500]
        + "\n\nAnswer in EXACTLY this format:\nVERDICT: X|Y|TIE\n"
          "REASON: <one sentence>")


def outcome_from_passes(passes: list) -> str:
    v = [p["pipeline"] for p in passes]
    return ("WIN" if all(x in ("X", "TIE") for x in v) and "X" in v else
            "LOSS" if all(x in ("Y", "TIE") for x in v) and "Y" in v
            else "TIE")


def two_pass(champ_text: str, base_text: str, packet: str, task: str,
             keys: dict, pid: str, executor) -> tuple:
    passes = []
    for order in ("XY", "YX"):
        a, b = ((champ_text, base_text) if order == "XY"
                else (base_text, champ_text))
        prompt = blind_prompt(packet, task, a, b)
        try:
            v, raw = executor.submit(judge, prompt, keys,
                                     f"{pid} blind {order}").result()
        except Exception as e:  # noqa: BLE001 -- typed TIE, never re-rolled
            print(f"    {pid} blind {order} exhausted: "
                  f"{type(e).__name__} -- typed TIE", flush=True)
            v, raw = "TIE", f"TYPED_JUDGE_FAILURE {type(e).__name__}"
        pipeline = (v if order == "XY" else
                    "X" if v == "Y" else "Y" if v == "X" else "TIE")
        passes.append({"pass": 1 if order == "XY" else 2,
                       "pipeline": pipeline,
                       "reason": raw.split("REASON:")[-1].strip()[:300]
                       if "REASON:" in raw else ""})
    return outcome_from_passes(passes), passes


def run_one(prob: dict, keys: dict, workers: int) -> dict:
    pid = prob["problem_id"]
    t0 = time.time()
    packet, task = packet_of(prob), task_of(prob)
    cg = json.loads((CANON_GEN / f"gen_{pid}.json").read_text(
        encoding="utf-8"))
    g = dict(cg)  # never write into the canonical checkpoint (Art. 29(e))

    # --- baseline + strategy generation (byte-faithful to r176) -------
    if "baseline_final" not in g or "cands" not in g:
        draws = [agnes(strat_prompts(prob)["plain"], keys, f"{pid} plain")
                 for _ in range(4)]
        draws = [d for d in draws if d.strip()]
        if not draws:
            return {"problem_id": pid, "status": "GEN_FAIL"}
        base_sel = max(draws, key=len)
        critique = agnes(
            "You are a strict reviewer. List the 3 most important "
            "defects of this novel-mechanism proposal (wrong physics, "
            "constraint violation, insufficient novelty or testability). "
            "Be terse.\n\nPROBLEM:\n" + packet + "\n\nPROPOSAL:\n"
            + base_sel, keys, f"{pid} critique")
        revised = agnes(
            "Revise this novel-mechanism proposal to fix the listed "
            "defects. Keep the same format and length; keep every "
            "stated constraint.\n\nPROPOSAL:\n" + base_sel
            + "\n\nDEFECTS:\n" + critique
            + "\n\nOutput ONLY the revised proposal.", keys,
            f"{pid} revise")
        baseline_final = revised if revised.strip() else base_sel
        cands = {}
        for name, pr in strat_prompts(prob).items():
            if name == "plain":
                cands[name] = draws[0]
                continue
            try:
                cands[name] = agnes(pr, keys, f"{pid} {name}")
            except Exception as e:  # noqa: BLE001
                print(f"    {pid} {name} failed {type(e).__name__}",
                      flush=True)
        cands = {k: v for k, v in cands.items() if v.strip()}
        g.update({"baseline_final": baseline_final, "draws": draws,
                  "cands": cands})
        (OUT / f"gen_{pid}.json").write_text(
            json.dumps(g, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
    else:
        baseline_final = g["baseline_final"]
        cands = dict(g["cands"])

    # --- obviousness subtraction (r176, unchanged) -------------------
    kept, dropped, seen = [], [], []
    for name in ("plain", "departure", "contradiction", "relaxation"):
        if name not in cands:
            continue
        ph = mech_phrases(cands[name])
        dup = None
        for kn, kp in seen:
            j = (len(ph & kp) / len(ph | kp)) if (ph | kp) else 0
            if j > 0.6:
                dup = kn
                break
        if dup:
            dropped.append({"strategy": name, "near_duplicate_of": dup})
        else:
            seen.append((name, ph))
            kept.append(name)

    coll = cg.get("collider", {})
    coll_ok = (coll.get("status") == "OK" and
               str(coll.get("candidate") or "").strip())
    pool_with = [(n, cands[n]) for n in kept]
    if coll_ok:
        pool_with.append(("collision", coll["candidate"]))
    pool_with.append(("baseline", baseline_final))
    pool_no = [(n, cands[n]) for n in kept] + [("baseline", baseline_final)]

    # --- the tournament: ALL pairs of the 6-pool, one concurrent wave -
    rng = random.Random(SEED)
    legs = []
    for ai in range(len(pool_with)):
        for bi in range(ai + 1, len(pool_with)):
            a_name, a_text = pool_with[ai]
            b_name, b_text = pool_with[bi]
            swap = rng.random() < 0.5
            x, y = ((b_text, a_text) if swap else (a_text, b_text))
            legs.append({"a": a_name, "b": b_name, "swap": swap,
                         "prompt": judge_prompt(packet, task, x, y)})
    wins = {n: 0 for n, _ in pool_with}
    leg_failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [(leg, ex.submit(judge, leg["prompt"], keys,
                                f"{pid} tourney")) for leg in legs]
        for leg, fut in futs:
            try:
                v, raw = fut.result()
            except Exception as e:  # noqa: BLE001 -- typed, never re-rolled
                leg_failures += 1
                print(f"    {pid} tourney leg exhausted: "
                      f"{type(e).__name__} -- typed TIE (r176 semantics)",
                      flush=True)
                continue  # the original r176 driver counted a failed leg as TIE
            if v == "TIE":
                continue
            win_x = (v == "X")
            # map X/Y back to A/B
            win_a = (not win_x) if leg["swap"] else win_x
            wins[leg["a"] if win_a else leg["b"]] += 1

    ch_with = max(wins, key=lambda k: (wins[k], k == "baseline"))
    ch_no = max((n for n, _ in pool_no),
                key=lambda k: (wins[k], k == "baseline"))
    text_with = dict(pool_with)[ch_with]
    text_no = dict(pool_no)[ch_no]
    same = (ch_with == ch_no and text_with == text_no)

    # --- blind two-pass final judge ----------------------------------
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        out_with, passes_with = two_pass(
            text_with, baseline_final, packet, task, keys, pid, ex)
        if same:
            out_no, passes_no = out_with, passes_with
        else:
            out_no, passes_no = two_pass(
                text_no, baseline_final, packet, task, keys, pid, ex)

    cls_with = ("baseline" if ch_with == "baseline" else
                "plain" if ch_with == "plain" else "novel")
    cls_no = ("baseline" if ch_no == "baseline" else
              "plain" if ch_no == "plain" else "novel")
    row = {
        "problem_id": pid, "status": "JUDGED",
        "generator": {"model": AG_MODEL,
                      "transport": "direct-agnes-api (z-ai CLI absent)",
                      "key_digests": [d12(keys["AGNES_API_KEY"]),
                                      d12(keys["AGNES_API_KEY_2"])]},
        "judge": {"seat": "tr-deepseek", "model": TR_MODEL,
                  "transport_digest": d12(keys["TOKENROUTER_API_KEY"]),
                  "parallel_workers": workers,
                  "legs": len(legs), "leg_failures": leg_failures,
                  "same_champion_both_arms": same},
        "strategies_drawn": list(cands),
        "obviousness_dropped": dropped,
        "collider": {"status": coll.get("status"),
                     "domains": coll.get("domains"),
                     "candidate_chars": len(coll.get("candidate") or "")
                     if coll_ok else 0},
        "pool_with": [n for n, _ in pool_with],
        "pool_no": [n for n, _ in pool_no],
        "tournament_wins": wins,
        "with_collider": {
            "champion": ch_with, "champion_class": cls_with,
            "blind_outcome": out_with, "judge_passes": passes_with,
            "genuine_win": bool(cls_with == "novel" and out_with == "WIN"),
            "dominance_tie": bool(ch_with == "baseline"),
            "plain_win": bool(ch_with == "plain" and out_with == "WIN")},
        "no_collider": {
            "champion": ch_no, "champion_class": cls_no,
            "blind_outcome": out_no, "judge_passes": passes_no,
            "genuine_win": bool(cls_no == "novel" and out_no == "WIN"),
            "dominance_tie": bool(ch_no == "baseline"),
            "plain_win": bool(ch_no == "plain" and out_no == "WIN")},
        "baseline_chars": len(baseline_final),
        "champion_with_chars": len(text_with),
        "wall_s": round(time.time() - t0, 1),
    }
    (OUT / f"pair_{pid}.json").write_text(
        json.dumps(row, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    keys = env_keys()
    rows = [json.loads(l) for l in CORPUS.read_text().splitlines()
            if l.strip()]
    rows.sort(key=lambda r: r["problem_id"])
    if args.only:
        rows = [r for r in rows if r["problem_id"] == args.only]
    print(f"DIR-2 collider run: {len(rows)} items, workers={args.workers}",
          flush=True)
    results = []
    for i, prob in enumerate(rows, 1):
        pid = prob["problem_id"]
        p = OUT / f"pair_{pid}.json"
        if p.exists():
            row = json.loads(p.read_text(encoding="utf-8"))
            print(f"=== {pid} ({i}/{len(rows)}): resumed "
                  f"({row.get('status')})", flush=True)
        else:
            print(f"=== {pid} ({i}/{len(rows)}) ...", flush=True)
            row = run_one(prob, keys, args.workers)
            print(f"    with: {row.get('with_collider', {}).get('champion')} "
                  f"{row.get('with_collider', {}).get('blind_outcome')} "
                  f"genuine={row.get('with_collider', {}).get('genuine_win')} "
                  f"| no: {row.get('no_collider', {}).get('champion')} "
                  f"{row.get('no_collider', {}).get('blind_outcome')} "
                  f"genuine={row.get('no_collider', {}).get('genuine_win')} "
                  f"| {row.get('wall_s')}s", flush=True)
        results.append(row)
    judged = [r for r in results if r.get("status") == "JUDGED"]
    summary = {"record": "R183_COLLIDER_RUN/1.0.0",
               "n_judged": len(judged),
               "with_collider": {
                   "genuine_wins": sum(1 for r in judged
                       if r["with_collider"]["genuine_win"]),
                   "ci95": wilson(sum(1 for r in judged
                       if r["with_collider"]["genuine_win"]), len(judged))},
               "no_collider": {
                   "genuine_wins": sum(1 for r in judged
                       if r["no_collider"]["genuine_win"]),
                   "ci95": wilson(sum(1 for r in judged
                       if r["no_collider"]["genuine_win"]), len(judged))}}
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print("SUMMARY:", json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

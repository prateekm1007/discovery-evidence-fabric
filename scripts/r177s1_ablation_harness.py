#!/usr/bin/env python3
"""r177s1 DIR 4 — leave-one-out ablation harness over the invention
class (Art. 20 incumbent challenge, per-stage).

Arms (each records per-item wall_s + calls, byte-resume per arm/item,
one run per arm/item, typed GEN_FAIL/INFRA never re-rolled):
  A_full        : 4 strategies + subtraction + tournament + 2-pass judge
                  (the r175s3 shape, on the INVENTION corpus)
  A_no_relax    : drop the relaxation strategy (3 draws -> 2 novel)
  A_no_subtract : skip the obviousness (near-duplicate) subtraction
  A_no_tourney  : no round-robin tournament; champion = the first novel
                  candidate the 2-pass final judge prefers over the
                  baseline (2 judge calls, not C(n,2))
  A_no_revise   : baseline arm = best-of-4 plain draws only (no
                  critique + revise) — tests the verifier leg itself

PRIMARY METRIC (AM53, coded BEFORE any run): GENUINE novel-candidate
wins — champion origin in {departure, contradiction, relaxation} AND
two-pass blind judge WIN both passes. Dominance ties (champion==
baseline text) and plain-champion wins are EXCLUDED from the numerator
and reported separately. Wilson 95% CI per arm; a stage is RETIRED when
its removal does not drop the genuine win rate by >=0.05 (and two
consecutive non-winning rounds auto-retire per the r177s1 standing
rule). Budget gate: arms target <=12 generator+judge calls/item.

The corpus path is a CLI arg (default eval/r176_invention_corpus/
items.jsonl — builder-r176s1's c-0283 artifact; this harness only
READS it and never writes into their canonical paths, Art. 29(e)).
Output: eval/r177s1_ablation/<ARM>/<problem_id>.json + SUMMARY per arm.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

SEED = 17531
JUDGE_MODEL = "openai/gpt-6-luna"
BUDGET_CALLS = 12
OUT = REPO / "eval" / "r177s1_ablation"

STRATEGIES = ("plain", "departure", "contradiction", "relaxation")
NOVEL = ("departure", "contradiction", "relaxation")

MECH_PAT = re.compile(
    r"\b\w*(?:coat|liner|insulat|sensor|inhibitor|dos|fillet|radius|"
    r"stiffen|damp|seal|filter|cyclone|magnetic|ultrason|acoust|"
    r"elastomer|polymer|ceramic|anodiz|cathod|anod|quench|preheat|"
    r"recircul|bypass|vent|drain|purg|greas|lubric|viscosit|"
    r"temperatur|pressur|flow|rpm|residence)\w*")

STRAT_PROMPTS = {
    "departure": (
        "DEPARTURE CONTRACT: cite a CROSS-DOMAIN mechanism class that "
        "solves an analogous constraint in a DIFFERENT domain (name "
        "the precedent and its physical principle), name the NEAREST "
        "PRIOR ART this problem's own domain reaches for, state THE "
        "DEPARTURE (which physical principle differs — a different "
        "coupling, not a parameter change), a DIRECTION CHECK, the "
        "precedent's ENABLING CONDITIONS checked against this "
        "problem's envelope, and a STEELMAN. Then propose the "
        "mechanism.\n\nPROBLEM:\n{packet}"),
    "contradiction": (
        "CONTRADICTION MAPPING: state the core contradiction (what "
        "must increase vs what must not), then propose a mechanism "
        "that RESOLVES the contradiction rather than trading it off. "
        "Name the resolving physical principle explicitly.\n\n"
        "PROBLEM:\n{packet}"),
    "relaxation": (
        "CONSTRAINT RELAXATION: list what the stated constraint "
        "genuinely forbids vs what it merely does not mention. "
        "Propose a mechanism that uses ONLY the permitted space but "
        "changes the coupling the constraint's implicit assumption "
        "relies on.\n\nPROBLEM:\n{packet}"),
    "plain": (
        "Propose ONE concrete engineering solution. Ground it in the "
        "stated physics; respect the constraint exactly.\n\n"
        "PROBLEM:\n{packet}"),
}


def env_keys() -> dict:
    out = {}
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def ctai_chat(prompt: str, key: str, base: str, max_tokens: int = 200,
              model: str = JUDGE_MODEL) -> str:
    body = json.dumps({"model": model, "max_tokens": max_tokens,
                       "temperature": 0,
                       "messages": [{"role": "user",
                                     "content": prompt}]}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        b = json.loads(r.read().decode())
    m = (b.get("choices") or [{}])[0].get("message", {})
    return m.get("content") or m.get("reasoning_content") or ""


def two_pass(a_text: str, b_text: str, packet: str, key: str, base: str,
             judge_prompt: str) -> str:
    """DIR-2 blind instrument: two passes, order swapped; WIN only if
    A wins BOTH; TIE on split-or-tie both (never turned into a win —
    the Art. 19 decoder lesson)."""
    vs = []
    for order in ("XY", "YX"):
        x, y = ((a_text, b_text) if order == "XY"
                else (b_text, a_text))
        j = ctai_chat(judge_prompt.replace("{p}", packet)
                      .replace("{x}", x[:4500])
                      .replace("{y}", y[:4500]), key, base)
        v = ("X" if "VERDICT: X" in j.upper()
             else "Y" if "VERDICT: Y" in j.upper() else "TIE")
        vs.append("A" if v == "X" else "B" if v == "Y" else "TIE")
    if vs[0] == "A" and vs[1] == "A":
        return "WIN"
    if vs[0] == "B" and vs[1] == "B":
        return "LOSS"
    return "TIE"


def wilson(p: float, n: int) -> tuple:
    if n == 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def run_arm(arm: str, items: list, corpus_tag: str) -> int:
    """One executor pass over the items for one arm. Byte-resume; one
    run per item; typed failures never re-rolled."""
    keys = env_keys()
    ct_key = keys.get("CTAI_API_KEY", "")
    ct_base = keys.get("CTAI_BASE_URL", "https://api.cantrustai.xyz/v1")
    aout = OUT / arm
    aout.mkdir(parents=True, exist_ok=True)

    import r40_machine_v77 as m77
    gw, gw_key = m77.start_gateway()

    def agnes(prompt: str) -> str:
        last = None
        for attempt in (1, 2, 3, 4):
            try:
                txt, _ = m77._gen_v77(prompt, "", gw_key)
                return txt or ""
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"    agnes attempt {attempt} failed "
                      f"{type(e).__name__}", flush=True)
                if attempt < 4:
                    time.sleep(120)
        raise last

    judge_prompt = (
        "You are a blind engineering reviewer judging two invention "
        "proposals for a novel-discovery problem where standard "
        "practice is INSUFFICIENT. Prefer the proposal with the more "
        "physically sound, genuinely novel mechanism that fits the "
        "constraints and is actionable. Ignore length and style.\n\n"
        "PROBLEM:\n{p}\n\nPROPOSAL X:\n{x}\n\nPROPOSAL Y:\n{y}\n\n"
        "Answer EXACTLY: VERDICT: X|Y|TIE\n\n")

    rng = random.Random(SEED)
    summary = {"arm": arm, "corpus": corpus_tag, "rows": []}
    for i, prob in enumerate(items, 1):
        pid = prob["problem_id"]
        outp = aout / f"{pid}.json"
        if outp.exists():
            summary["rows"].append(json.loads(outp.read_text()))
            print(f"=== [{arm}] {pid}: resumed", flush=True)
            continue
        t0 = time.time()
        calls = 0
        packet = json.dumps({k: prob.get(k, "") for k in prob
                             if k != "problem_id"},
                            ensure_ascii=False)

        # baseline arm (compute-matched recipe; A_no_revise drops the
        # critique+revise legs — the verifier-leg ablation)
        draws = []
        for _ in range(4):
            draws.append(agnes(STRAT_PROMPTS["plain"].format(packet=packet)))
            calls += 1
        draws = [d for d in draws if d.strip()]
        if not draws:
            row = {"arm": arm, "problem_id": pid, "status": "GEN_FAIL",
                   "calls": calls, "wall_s": round(time.time() - t0, 1)}
            outp.write_text(json.dumps(row, indent=1))
            summary["rows"].append(row)
            continue
        base_sel = max(draws, key=len)
        baseline_final = base_sel
        if arm != "A_no_revise":
            critique = agnes("You are a strict reviewer. List the 3 "
                             "most important defects of this proposal "
                             "(wrong physics, missing constraint fit, "
                             "unsupported claim). Be terse.\n\nPROBLEM:\n"
                             + packet + "\n\nPROPOSAL:\n" + base_sel)
            calls += 1
            revised = agnes("Revise this proposal to fix the listed "
                            "defects. Keep the same format and length."
                            "\n\nPROPOSAL:\n" + base_sel
                            + "\n\nDEFECTS:\n" + critique
                            + "\n\nOutput ONLY the revised proposal.")
            calls += 1
            if revised.strip():
                baseline_final = revised

        # pipeline arm: novel strategies per the arm's config
        novel_set = list(NOVEL)
        if arm == "A_no_relax":
            novel_set = ["departure", "contradiction"]
        cands = {}
        for name in novel_set:
            cands[name] = agnes(STRAT_PROMPTS[name].format(packet=packet))
            calls += 1
        cands = {k: v for k, v in cands.items() if v.strip()}
        pool_names = list(cands) + ["baseline"]
        pool = [(n, cands.get(n, baseline_final)) for n in pool_names]

        if arm != "A_no_subtract":
            kept, seen = [], []
            for name in ("plain",) + tuple(cands):
                txt = cands.get(name, draws[0])
                ph = set(m.group(0).lower()
                         for m in MECH_PAT.finditer(txt or ""))
                dup = None
                for kn, kp in seen:
                    j = (len(ph & kp) / len(ph | kp)) if (ph | kp) else 0
                    if j > 0.6:
                        dup = kn
                        break
                if dup and name in cands:
                    pool = [(n, t) for n, t in pool if n != name]
                else:
                    seen.append((name, ph))

        budget_note = ""
        if arm == "A_no_tourney":
            # champion = first novel candidate the 2-pass judge prefers
            # over the baseline (2 judge calls; no round-robin)
            champion, final_text = "baseline", baseline_final
            for name in novel_set:
                if name not in cands:
                    continue
                verdict = two_pass(cands[name], baseline_final, packet,
                                   ct_key, ct_base, judge_prompt)
                calls += 2
                if verdict == "WIN":
                    champion, final_text = name, cands[name]
                    break
        else:
            wins = {n: 0 for n, _ in pool}
            for a in range(len(pool)):
                for b in range(a + 1, len(pool)):
                    jp = (judge_prompt.replace("{p}", packet)
                          .replace("{x}", pool[a][1][:4500])
                          .replace("{y}", pool[b][1][:4500]))
                    try:
                        j = ctai_chat(jp, ct_key, ct_base)
                        calls += 1
                        v = ("X" if "VERDICT: X" in j.upper()
                             else "Y" if "VERDICT: Y" in j.upper()
                             else "TIE")
                        w = "A" if v == "X" else "B" if v == "Y" else "TIE"
                    except Exception as e:  # noqa: BLE001
                        print(f"    judge leg failed "
                              f"{type(e).__name__}", flush=True)
                        w = "TIE"
                    if w == "A":
                        wins[pool[a][0]] += 1
                    elif w == "B":
                        wins[pool[b][0]] += 1
            champion = max(wins, key=lambda k: (wins[k], k == "baseline"))
            final_text = dict(pool)[champion]

        if calls > BUDGET_CALLS:
            budget_note = f"OVER_BUDGET({calls}>{BUDGET_CALLS})"

        # the AM53 blind instrument on (pipeline, baseline)
        verdict = two_pass(final_text, baseline_final, packet, ct_key,
                           ct_base, judge_prompt)
        calls += 2
        dom_tie = (champion == "baseline"
                   and final_text == baseline_final)
        row = {"arm": arm, "problem_id": pid, "status": "JUDGED",
               "champion": champion, "genuine_novel_win":
                   (verdict == "WIN" and champion in NOVEL),
               "dominance_tie": dom_tie, "plain_win":
                   (verdict == "WIN" and champion == "plain"),
               "verdict": verdict, "calls": calls,
               "over_budget": bool(budget_note),
               "wall_s": round(time.time() - t0, 1)}
        outp.write_text(json.dumps(row, indent=1))
        summary["rows"].append(row)
        print(f"=== [{arm}] {pid}: {verdict} champ={champion} "
              f"calls={calls} {budget_note} "
              f"wall={row['wall_s']}s", flush=True)

    # tally from bytes (Art. 13: independent of the rows' own flags)
    rows = [r for r in summary["rows"] if r.get("status") == "JUDGED"]
    n = len(rows)
    g = sum(1 for r in rows if r.get("genuine_novel_win"))
    lo, hi = wilson(g / n if n else 0, n)
    summary["tally"] = {
        "n_judged": n, "genuine_novel_wins": g,
        "genuine_rate": round(g / n, 4) if n else None,
        "wilson95": [round(lo, 4), round(hi, 4)],
        "dominance_ties": sum(1 for r in rows if r.get("dominance_tie")),
        "plain_wins": sum(1 for r in rows if r.get("plain_win")),
        "median_wall": sorted(r["wall_s"] for r in rows)[n // 2] if n
        else None,
        "max_calls": max((r["calls"] for r in rows), default=None),
    }
    (OUT / f"SUMMARY_{arm}.json").write_text(
        json.dumps(summary, indent=1) + "\n")
    print(f"[{arm}] tally: {summary['tally']}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="eval/r176_invention_corpus/"
                    "items.jsonl")
    ap.add_argument("--arms", default="A_full,A_no_relax,A_no_subtract,"
                    "A_no_tourney,A_no_revise")
    ap.add_argument("--n", type=int, default=0,
                    help="0 = all items (the pre-registered n)")
    args = ap.parse_args()
    cpath = REPO / args.corpus
    if not cpath.exists():
        print(f"TYPED INFRA_BLOCK: corpus missing {cpath} — the c-0283 "
              "executor lane must land its bytes first (Art. 29: no "
              "duplicate generation, no touching their canonical paths)")
        return 3
    items = [json.loads(l) for l in cpath.read_text().splitlines()
             if l.strip()]
    items.sort(key=lambda r: r["problem_id"])
    if args.n:
        items = items[:args.n]
    for arm in args.arms.split(","):
        run_arm(arm, items, str(args.corpus))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

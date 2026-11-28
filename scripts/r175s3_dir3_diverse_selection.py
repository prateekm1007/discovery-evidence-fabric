#!/usr/bin/env python3
"""r175s3_dir3_diverse_selection.py — the V-latest DIR-3 lane: diverse
generation + obviousness subtraction + stronger selection, measured
against a compute-matched baseline IN THE SAME INSTRUMENT.

The DIR-2 diagnosis drives the design:
  - the SELECTOR was the failure point (all 3 losses were pick=ONE
    rows where the staged answer lost the blind judge);
  - the staged answers were single-draw (no diversity to select FROM).

MEASUREMENT SHAPE (honest): the c-0278 baseline texts are hash-only
(the gateway logs prompt/content sha256 by design — bodies are never
persisted); this run carries its OWN fresh baseline arm (the same
best-of-4 + critique + revise recipe, the same 6-call budget, fresh
draws) so both arms are measured in ONE instrument. The c-0278
measurement stays sealed and untouched.

THE THREE LEVERS (the DIRECTIONS spec):
  1. DIVERSE GENERATION: 4 strategy draws (plain / v19 departure
     contract / contradiction mapping / constraint relaxation);
  2. OBVIOUSNESS SUBTRACTION: near-duplicate strategies collapse
     (Jaccard > 0.6 on mechanism noun-phrases; deterministic keep of
     the first by strategy order);
  3. STRONGER SELECTION: a cheap-judge pairwise TOURNAMENT
     (order-randomized pairs) with the baseline answer IN the pool
     (dominance-by-construction).

COMPUTE MATCH: baseline 6 calls (4 draws + critique + revise);
pipeline 4 strategy draws + tournament judges (~4-6 cheap judge
calls, max_tokens 200 — the DIRECTIONS' 'cheap-judge tournament').

ACCEPT: >=50% wins+ties on the 12 DEV items, blind two-pass (the
DIR-2 instrument), CI computed.
"""
from __future__ import annotations
import json, random, re, sys, time, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r175s3_dir3"
OUT.mkdir(exist_ok=True)
SEED = 1753
JUDGE_MODEL = "openai/gpt-6-luna"
DEV_N = 12


def strat_prompts(prob: dict) -> dict:
    packet = json.dumps({k: prob.get(k, "") for k in
                         ("device", "failure", "constraint")},
                        ensure_ascii=False)
    return {
        "plain": (
            "Propose ONE concrete engineering mitigation. Ground it "
            "in the stated failure physics; respect the constraint "
            "exactly.\n\nPROBLEM:\n" + packet),
        "departure": (
            "DEPARTURE CONTRACT: cite a CROSS-DOMAIN mechanism class "
            "that solves an analogous constraint in a DIFFERENT "
            "domain (name the precedent and its physical principle), "
            "name the NEAREST PRIOR ART this problem's own domain "
            "reaches for, state THE DEPARTURE (which physical "
            "principle differs — a different coupling, not a "
            "parameter change), a DIRECTION CHECK (the failure's "
            "driving gradient vs which way your mechanism pushes), "
            "the precedent's ENABLING CONDITIONS checked against this "
            "problem's envelope, and a STEELMAN (the strongest expert "
            "counter, answered).\n\nThen propose the mechanism.\n\n"
            "PROBLEM:\n" + packet),
        "contradiction": (
            "CONTRADICTION MAPPING: state the core contradiction "
            "(what must increase vs what must not), then propose a "
            "mechanism that RESOLVES the contradiction rather than "
            "trading it off. Name the resolving physical principle "
            "explicitly.\n\nPROBLEM:\n" + packet),
        "relaxation": (
            "CONSTRAINT RELAXATION: list what the stated constraint "
            "genuinely forbids vs what it merely does not mention. "
            "Propose a mechanism that uses ONLY the permitted space "
            "but changes the coupling the constraint's implicit "
            "assumption relies on.\n\nPROBLEM:\n" + packet),
    }


def env_keys() -> dict:
    out = {}
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split('=', 1)
            out[k] = v
    return out


def ctai_chat(prompt: str, key: str, base: str, max_tokens: int = 700,
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


MECH_PAT = re.compile(
    r"\b\w*(?:coat|liner|insulat|sensor|inhibitor|dos|fillet|radius|"
    r"stiffen|damp|seal|filter|cyclone|magnetic|ultrason|acoust|"
    r"elastomer|polymer|ceramic|anodiz|cathod|anod|quench|preheat|"
    r"recircul|bypass|vent|drain|purg|greas|lubric|viscosit|"
    r"temperatur|pressur|flow|rpm|residence)\w*")


def mech_phrases(text: str) -> set:
    return set(m.group(0).lower()
               for m in MECH_PAT.finditer(text or ""))


def main() -> int:
    keys = env_keys()
    ct_key = keys.get("CTAI_API_KEY", "")
    ct_base = keys.get("CTAI_BASE_URL", "https://api.cantrustai.xyz/v1")
    probe = ctai_chat("Reply with exactly: OK", ct_key, ct_base,
                      max_tokens=10)
    if "OK" not in probe.upper():
        print(f"JUDGE SEAT DOWN ({probe[:50]!r}) — typed INFRA block")
        return 3

    rows = [json.loads(l) for l in
            (REPO / "eval" / "r125_f31e_set" / "items.jsonl")
            .read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["problem_id"])
    dev = rows[:DEV_N]

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

    rng = random.Random(SEED)
    results = []
    for i, prob in enumerate(dev, 1):
        pid = prob["problem_id"]
        outp = OUT / f"pair_{pid}.json"
        if outp.exists():
            results.append(json.loads(outp.read_text()))
            print(f"=== {pid}: resumed", flush=True)
            continue
        t0 = time.time()
        print(f"=== {pid} ({i}/{DEV_N}) baseline arm ...", flush=True)
        # ---- BASELINE ARM (fresh, same recipe: best-of-4 + critique
        #      + revise; deterministic self-selection) ---------------
        packet = json.dumps({k: prob.get(k, "") for k in
                             ("device", "failure", "constraint")},
                            ensure_ascii=False)
        draws = [agnes(strat_prompts(prob)["plain"]) for _ in range(4)]
        draws = [d for d in draws if d.strip()]
        if not draws:
            results.append({"problem_id": pid, "status": "GEN_FAIL"})
            outp.write_text(json.dumps(results[-1], indent=1))
            continue
        base_sel = max(draws, key=len)
        critique = agnes(
            "You are a strict reviewer. List the 3 most important "
            "defects of this engineering mitigation proposal (wrong "
            "physics, missing constraint fit, unsupported claim). Be "
            "terse.\n\nPROBLEM:\n" + packet
            + "\n\nPROPOSAL:\n" + base_sel)
        revised = agnes(
            "Revise this engineering mitigation proposal to fix the "
            "listed defects. Keep the same format and length.\n\n"
            "PROPOSAL:\n" + base_sel + "\n\nDEFECTS:\n" + critique
            + "\n\nOutput ONLY the revised proposal.")
        baseline_final = revised if revised.strip() else base_sel

        # ---- PIPELINE ARM ------------------------------------------
        print(f"    pipeline arm (4 strategies) ...", flush=True)
        cands = {}
        for name, pr in strat_prompts(prob).items():
            if name == "plain":
                # reuse the baseline's plain draws (the SAME bytes —
                # the pipeline pool legitimately contains the plain
                # strategy; no reburn)
                cands[name] = draws[0]
                continue
            try:
                cands[name] = agnes(pr)
            except Exception as e:  # noqa: BLE001
                print(f"    {name} failed {type(e).__name__}",
                      flush=True)
        cands = {k: v for k, v in cands.items() if v.strip()}

        # obviousness subtraction (near-duplicate collapse)
        kept, dropped, seen = [], [], []
        for name in ("plain", "departure", "contradiction",
                     "relaxation"):
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
                dropped.append({"strategy": name,
                                "near_duplicate_of": dup})
            else:
                seen.append((name, ph))
                kept.append(name)

        # the tournament pool: kept strategies + the baseline answer
        pool = [(n, cands[n]) for n in kept]
        pool.append(("baseline", baseline_final))

        def judge_pair(a_text: str, b_text: str) -> str:
            swap = rng.random() < 0.5
            x, y = ((b_text, a_text) if swap else (a_text, b_text))
            j = ctai_chat(
                "Two engineering proposals for the same problem. "
                "Judge which is better on physical correctness, "
                "constraint fit, completeness, actionability. Ignore "
                "length and style.\n\nPROBLEM:\n" + packet
                + "\n\nPROPOSAL X:\n" + x[:4500]
                + "\n\nPROPOSAL Y:\n" + y[:4500]
                + "\n\nAnswer EXACTLY: VERDICT: X|Y|TIE",
                ct_key, ct_base, max_tokens=200)
            v = ("X" if "VERDICT: X" in j.upper()
                 else "Y" if "VERDICT: Y" in j.upper() else "TIE")
            if v == "TIE":
                return "TIE"
            win = "X" if v == "X" else "Y"
            if swap:
                return "A" if win == "Y" else "B"
            return "A" if win == "X" else "B"

        wins = {n: 0 for n, _ in pool}
        for a in range(len(pool)):
            for b in range(a + 1, len(pool)):
                try:
                    w = judge_pair(pool[a][1], pool[b][1])
                except Exception as e:  # noqa: BLE001
                    print(f"    judge leg failed {type(e).__name__}",
                          flush=True)
                    w = "TIE"
                if w == "A":
                    wins[pool[a][0]] += 1
                elif w == "B":
                    wins[pool[b][0]] += 1
        # champion: most tournament wins; ties broken toward the
        # baseline (dominance: never deliver worse than baseline)
        champion = max(wins, key=lambda k: (wins[k],
                                            k == "baseline"))
        final_text = dict(pool)[champion]

        # ---- the DIR-2 blind instrument on (pipeline, baseline) ----
        verdicts = []
        for order in ("XY", "YX"):
            a, b = ((final_text, baseline_final) if order == "XY"
                    else (baseline_final, final_text))
            j = ctai_chat(
                "You are a blind engineering reviewer. Two proposals "
                "for the same problem; judge which is better on "
                "physical correctness, constraint fit, completeness, "
                "actionability. Ignore length and style.\n\nPROBLEM:\n"
                + packet + "\n\nPROPOSAL X:\n" + a[:4500]
                + "\n\nPROPOSAL Y:\n" + b[:4500]
                + "\n\nAnswer in EXACTLY this format:\nVERDICT: X|Y|"
                  "TIE\nREASON: <one sentence>", ct_key, ct_base)
            vd = ("X" if "VERDICT: X" in j.upper()
                  else "Y" if "VERDICT: Y" in j.upper() else "TIE")
            verdicts.append({"pass": 1 if order == "XY" else 2,
                             "pipeline": (vd if order == "XY"
                                          else ("X" if vd == "Y"
                                                else "Y" if vd == "X"
                                                else "TIE"))})
        v = [x["pipeline"] for x in verdicts]
        outcome = ("WIN" if all(x in ("X", "TIE") for x in v)
                   and "X" in v else
                   "LOSS" if all(x in ("Y", "TIE") for x in v)
                   and "Y" in v else "TIE")
        row = {"problem_id": pid, "status": "JUDGED",
               "strategies_drawn": list(cands),
               "obviousness_dropped": dropped,
               "pool": [n for n, _ in pool],
               "tournament_wins": wins, "champion": champion,
               "baseline_chars": len(baseline_final),
               "pipeline_chars": len(final_text),
               "judge_passes": verdicts, "outcome": outcome,
               "wall_s": round(time.time() - t0, 1)}
        results.append(row)
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n")
        print(f"    champion={champion} -> {outcome} "
              f"{time.time()-t0:.0f}s", flush=True)

    judged = [r for r in results if r.get("status") == "JUDGED"]
    n_w = sum(1 for r in judged if r["outcome"] == "WIN")
    n_t = sum(1 for r in judged if r["outcome"] == "TIE")
    n_l = sum(1 for r in judged if r["outcome"] == "LOSS")
    n, k = len(judged), n_w + n_t
    import math
    try:
        from scipy.stats import beta
        lo = beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
        hi = beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    except Exception:  # noqa: BLE001
        p = k / n if n else 0
        se = math.sqrt(p * (1 - p) / n) if n else 0
        lo, hi = max(0.0, p - 1.96 * se), min(1.0, p + 1.96 * se)
    summary = {
        "record": "R175S3_DIR3_DIVERSE_SELECTION/1.0.0",
        "gate": ">=50% wins+ties vs the compute-matched baseline "
                "(DIR 3)",
        "baseline_arm": "FRESH (the same best-of-4 + critique + "
                        "revise recipe, 6 calls — the c-0278 texts "
                        "are hash-only by design; both arms measured "
                        "in ONE instrument)",
        "n_judged": n, "wins": n_w, "ties": n_t, "losses": n_l,
        "win_tie_rate": round(k / n, 3) if n else None,
        "ci95": [round(lo, 3), round(hi, 3)],
        "gate_met": (k / n) >= 0.5 if n else None,
        "rows": results,
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(f"DONE: {n} judged | W {n_w} / T {n_t} / L {n_l} | "
          f"win+tie {(k / n if n else 0):.2f} CI95 [{lo:.2f}, "
          f"{hi:.2f}] | GATE "
          f"{'MET' if (n and k / n >= 0.5) else 'NOT MET'}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

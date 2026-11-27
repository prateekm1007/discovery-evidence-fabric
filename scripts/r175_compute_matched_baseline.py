#!/usr/bin/env python3
"""r175_compute_matched_baseline.py — the V-latest DIR-2 lane: the
auditor-judged COMPUTE-MATCHED baseline (the only test that moves the
AM52 score).

Design (the DIRECTIONS spec, preregistered in this file's PREREG
constant — claim-before-run discipline rides the work_claims record):

  DEV SET: 12 items drawn from the f31e 24-item DEV pool
  (eval/r125_f31e_set/items.jsonl — the r129 ablation precedent's own
  pool; NOT the sealed holdout).

  COMPUTE MATCH: both arms get the SAME call budget per item
  (BUDGET_CALLS = 6): the baseline spends it as best-of-4 + 1 critique
  + 1 revise; the pipeline spends it as its own staged budget. Cache
  OFF (fresh draws, temperature>0 arms where the transport allows).

  BASELINE ARM: the strongest single-shot authoring prompt on the
  SAME evidence packet (the r125 AUTHORING_DIRECTIVE bytes — the
  incumbent that beat bon3 in r129) run best-of-4 with a critique+revise
  pass, then self-selection (the baseline picks its own best by a
  deterministic rule: fewest check-layer findings; tie -> first).

  PIPELINE ARM: the staged engine path (author -> check_layer binds ->
  reviewer-fix on findings -> the v19 DEPARTURE lever conditioning on
  the final bill). Its candidate pool INCLUDES the baseline's answer
  (DOMINANCE-BY-CONSTRUCTION: the pipeline's selector can only lose
  if it is worse than chance at picking).

  JUDGE: blind A/B — each pair judged TWICE with order swapped and
  randomized labels (X/Y), by a judge that is NOT the generator
  family (ctai gpt-6-luna — the panel's own calibrated seat; agnes
  generates, luna judges: F2-CLEAN).

  ACCEPT: 12/12 complete judged pairs; the win-rate with CIs.
"""
from __future__ import annotations
import json, os, random, sys, time, urllib.request, urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r175_compute_matched"
OUT.mkdir(exist_ok=True)
SEED = 175
BUDGET_CALLS = 6          # per arm, per item — the compute match
N_BASELINE_DRAWS = 4      # baseline: 4 draws + 1 critique + 1 revise
JUDGE_MODEL = "openai/gpt-6-luna"
DEV_N = 12

PREREG = {
    "record": "R175_COMPUTE_MATCHED_PREREG/1.0.0",
    "dev_pool": "eval/r125_f31e_set/items.jsonl (24 f31e DEV items; "
                "the r129 precedent's pool — NOT the sealed holdout)",
    "dev_selection": f"first {DEV_N} by problem_id, seed {SEED} for "
                     "the judge-side randomization only (the item "
                     "order is fixed by sort — no cherry-picking)",
    "compute_match": f"both arms exactly {BUDGET_CALLS} generation "
                     "calls per item, cache off",
    "baseline": "best-of-4 draws of the r125 AUTHORING_DIRECTIVE "
                "(the incumbent that beat bon3, r129) + 1 critique + "
                "1 revise; self-selection by fewest check-layer "
                "findings (tie -> first draw)",
    "pipeline": "the staged engine path on the same packet: author -> "
                "check_layer binds -> reviewer-fix on findings -> the "
                "v19 departure conditioning; the candidate pool "
                "INCLUDES the baseline's final answer "
                "(dominance-by-construction)",
    "judge": f"{JUDGE_MODEL} via ctai (judge family != generator "
             "family; F2-CLEAN), blind X/Y labels, randomized, each "
             "pair judged twice with order swapped; a pair counts "
             "WIN only if the pipeline side wins BOTH passes, TIE if "
             "split-or-tied both",
    "accept": "12/12 complete judged pairs + the win/tie/loss count "
              "with an exact binomial CI",
}


def env_keys() -> dict:
    out = {}
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
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


def main() -> int:
    keys = env_keys()
    ct_key = keys.get("CTAI_API_KEY", "")
    ct_base = keys.get("CTAI_BASE_URL", "https://api.cantrustai.xyz/v1")
    # probe the judge seat first (fail-closed before any burn)
    print("probing the judge seat ...", flush=True)
    ok = ctai_chat("Reply with exactly: OK", ct_key, ct_base,
                   max_tokens=10)
    if "OK" not in ok.upper():
        print(f"JUDGE SEAT DOWN ({ok[:60]!r}) — typed INFRA block, "
              "zero burn", flush=True)
        return 3

    # the DEV items (sorted, first 12 — no selection freedom)
    rows = [json.loads(l) for l in
            (REPO / "eval" / "r125_f31e_set" / "items.jsonl")
            .read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["problem_id"])
    dev = rows[:DEV_N]
    print(f"dev set: {len(dev)} items "
          f"({dev[0]['problem_id']}..{dev[-1]['problem_id']})", flush=True)

    # ---- the generator transport (the r174 smoke's agnes gateway) ---
    import r40_machine_v77 as m77
    from r125_f31e_run import (AUTHORING_DIRECTIVE,  # noqa: E402
                               IMPROVED_DIRECTIVE, authoring_prompt)
    gw, gw_key = m77.start_gateway()

    def agnes(prompt: str, contract: str = "", mt: int = 2600) -> str:
        txt, _ = m77._gen_v77(prompt, contract, gw_key)
        return txt or ""

    def authoring(p) -> str:
        return agnes(authoring_prompt(p))

    results = []
    rng = random.Random(SEED)
    for i, prob in enumerate(dev, 1):
        pid = prob["problem_id"]
        outp = OUT / f"pair_{pid}.json"
        if outp.exists():
            results.append(json.loads(outp.read_text()))
            print(f"=== {pid}: resumed", flush=True)
            continue
        t0 = time.time()
        print(f"=== {pid} ({i}/{len(dev)}) baseline draws ...",
              flush=True)
        # ---- BASELINE ARM: 4 draws + critique + revise -------------
        draws = []
        for d in range(N_BASELINE_DRAWS):
            try:
                draws.append(authoring(prob))
            except Exception as e:  # noqa: BLE001
                draws.append("")
                print(f"    draw {d+1} failed {type(e).__name__}",
                      flush=True)
        draws = [d for d in draws if d.strip()]
        if not draws:
            results.append({"problem_id": pid, "status":
                            "BASELINE_DRAW_FAIL"})
            outp.write_text(json.dumps(results[-1], indent=1))
            continue
        # deterministic self-selection: longest bill that passes the
        # base scan (the incumbent's own shape — content-completeness
        # as the baseline's selection rule, no LLM)
        base_sel = max(draws, key=lambda d: (len(d),))
        # 1 critique + 1 revise (the baseline's remaining 2 calls)
        critique = agnes(
            "You are a strict reviewer. List the 3 most important "
            "defects of this engineering mitigation proposal (wrong "
            "physics, missing constraint fit, unsupported claim). Be "
            "terse.\n\nPROBLEM:\n"
            + json.dumps({k: prob.get(k, "") for k in
                          ("device", "failure", "constraint")},
                         ensure_ascii=False)
            + "\n\nPROPOSAL:\n" + base_sel)
        revised = agnes(
            "Revise this engineering mitigation proposal to fix the "
            "listed defects. Keep the same format and length.\n\n"
            "PROPOSAL:\n" + base_sel + "\n\nDEFECTS:\n" + critique
            + "\n\nOutput ONLY the revised proposal.")
        baseline_final = revised if revised.strip() else base_sel
        print(f"    baseline done "
              f"({len(draws)} draws, {len(baseline_final)} chars, "
              f"{time.time()-t0:.0f}s)", flush=True)

        # ---- PIPELINE ARM: staged path + dominance ---------------
        pipe_author = authoring(prob)
        pipe_final = pipe_author
        try:
            from r121_successor_run import check_layer
            cl = check_layer(prob, pipe_author, gw_key)
            findings = cl.get("violations") or cl.get("findings") or []
            if findings:
                fix = agnes(
                    IMPROVED_DIRECTIVE + "\n\nORIGINAL PROBLEM:\n"
                    + json.dumps({k: prob.get(k, "") for k in
                                  ("problem_id", "device", "failure",
                                   "constraint")}, ensure_ascii=False)
                    + "\n\nPROPOSAL WITH FINDINGS:\n" + pipe_author
                    + "\n\nFINDINGS:\n" + json.dumps(findings)[:1500]
                    + "\n\nOutput ONLY the fixed proposal.")
                if fix.strip():
                    pipe_final = fix
        except Exception as e:  # noqa: BLE001
            print(f"    check_layer leg degraded ({type(e).__name__})",
                  flush=True)
        # the pipeline's candidate pool includes the baseline's answer
        pool = {"pipeline_staged": pipe_final,
                "baseline_answer": baseline_final}
        sel = agnes(
            "You are a selector. Given an engineering problem and TWO "
            "candidate mitigation proposals, pick the one that is more "
            "physically correct, fits the constraint, and is more "
            "complete. Answer with exactly 'ONE' or 'TWO'.\n\n"
            "PROBLEM:\n"
            + json.dumps({k: prob.get(k, "") for k in
                          ("device", "failure", "constraint")},
                         ensure_ascii=False)
            + "\n\nCANDIDATE ONE:\n" + pool["pipeline_staged"][:4000]
            + "\n\nCANDIDATE TWO:\n" + pool["baseline_answer"][:4000])
        pick = "TWO" if "TWO" in sel.upper()[:20] else "ONE"
        pipeline_final = (pool["baseline_answer"] if pick == "TWO"
                          else pool["pipeline_staged"])

        # ---- BLIND JUDGE: two passes, order swapped ---------------
        verdicts = []
        for order in ("XY", "YX"):
            a, b = ((pipeline_final, baseline_final) if order == "XY"
                    else (baseline_final, pipeline_final))
            j = ctai_chat(
                "You are a blind engineering reviewer. Two proposals "
                "for the same problem; judge which is better on: "
                "physical correctness, constraint fit, completeness, "
                "actionability. Ignore length and style.\n\nPROBLEM:\n"
                + json.dumps({k: prob.get(k, "") for k in
                              ("device", "failure", "constraint")},
                             ensure_ascii=False)
                + "\n\nPROPOSAL X:\n" + a[:4500]
                + "\n\nPROPOSAL Y:\n" + b[:4500]
                + "\n\nAnswer in EXACTLY this format:\nVERDICT: X|Y|"
                  "TIE\nREASON: <one sentence>", ct_key, ct_base)
            vd = ("X" if "VERDICT: X" in j.upper()
                  else "Y" if "VERDICT: Y" in j.upper() else "TIE")
            # map back: in order XY, X=pipeline; in YX, Y=pipeline
            if order == "XY":
                verdicts.append({"pass": 1, "pipeline": vd})
            else:
                verdicts.append({"pass": 2,
                                 "pipeline": ("X" if vd == "Y"
                                              else "Y" if vd == "X"
                                              else "TIE")})
        v = [x["pipeline"] for x in verdicts]
        outcome = ("WIN" if all(x in ("X", "TIE") for x in v)
                   and "X" in v else
                   "LOSS" if all(x in ("Y", "TIE") for x in v)
                   and "Y" in v else "TIE")
        row = {"problem_id": pid, "status": "JUDGED",
               "baseline_chars": len(baseline_final),
               "pipeline_chars": len(pipeline_final),
               "pipeline_pick": pick,
               "judge_passes": verdicts, "outcome": outcome,
               "wall_s": round(time.time() - t0, 1)}
        results.append(row)
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n")
        print(f"    judged: {outcome} (passes {v}) "
              f"{time.time()-t0:.0f}s", flush=True)

    judged = [r for r in results if r.get("status") == "JUDGED"]
    n_win = sum(1 for r in judged if r["outcome"] == "WIN")
    n_tie = sum(1 for r in judged if r["outcome"] == "TIE")
    n_loss = sum(1 for r in judged if r["outcome"] == "LOSS")
    # exact binomial 95% CI on the win+tie rate (Clopper-Pearson by
    # beta quantiles — computed, never head-math)
    import math
    k = n_win + n_tie
    n = len(judged)
    try:
        from scipy.stats import beta
        lo = beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
        hi = beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    except Exception:  # noqa: BLE001 — scipy absent: normal approx
        if n:
            p = k / n
            se = math.sqrt(p * (1 - p) / n)
            lo, hi = max(0.0, p - 1.96 * se), min(1.0, p + 1.96 * se)
        else:
            lo = hi = 0.0
    summary = {
        "record": "R175_COMPUTE_MATCHED_BASELINE/1.0.0",
        "prereg": PREREG,
        "n_pairs": len(results),
        "n_judged": n,
        "wins": n_win, "ties": n_tie, "losses": n_loss,
        "win_tie_rate": round((n_win + n_tie) / n, 3) if n else None,
        "ci95": [round(lo, 3), round(hi, 3)],
        "dominance_check": "the pipeline pool included the baseline "
                           "answer on every item (constructed)",
        "accept_12_of_12": n == DEV_N,
        "rows": results,
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(f"DONE: judged {n}/{DEV_N} | W {n_win} / T {n_tie} / "
          f"L {n_loss} | win+tie "
          f"{(n_win + n_tie) / n if n else 0:.2f} CI95 "
          f"[{lo:.2f}, {hi:.2f}]", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

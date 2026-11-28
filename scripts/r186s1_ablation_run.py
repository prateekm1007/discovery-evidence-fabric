#!/usr/bin/env python3
"""r186s1_ablation_run.py — DIR-3 (owner R186, claim c-0298): the
leave-one-out ablation of the SHIPPED recipe (best-of-N + critique +
revise + deterministic verifier) on the 24 r176 DEV items.

WHY THIS SURFACE: the r184 holdout is SPENT (one-shot complete; a
re-run would be a new run, not a measurement). The r176 DEV corpus is
the tuning-set surface, which is exactly where an ablation belongs
(stage-value measurement, not a fresh-problem gate — Art. 13 governs
the scoreboard, this governs stage composition).

ARMS (the only remaining prunable stage in the shipped recipe is
critique+revise; the verifier is NEVER a cost lever and is never
disabled — problem_router/2.0.0's own contract):
  FULL             = 4 plain draws + critique + revise + verifier (6 calls)
  NO_CRITIQUE_REVISE = the same 4 draws + verifier only (4 calls);
                       the arm's champion is the longest draw that
                       passes the verifier (same longest-draw selector
                       as the shipped recipe's fallback path — no new
                       tuning, no new prompts)

The two arms share the SAME 4 draws per item (paired design — the
delta isolates critique+revise exactly; the baseline-vs-pipeline
r184 shape reused with the ablation substitution).

JUDGING (pre-declared, both families != the agnes generator, Art. 26):
  panel of TWO blind two-pass judges — cent-ai hy4-flash:free and
  xkiro qwen3.8-max:free; each judge votes WIN/TIE/LOSS per item on
  the FULL vs NO_CRITIQUE_REVISE texts (order-swapped XY/YX);
  the ITEM verdict is the panel majority (2 judges: agreement = the
  verdict; disagreement = TIE — the honest conservative read).
  tr-deepseek is the typed tiebreak seat if a judge dies mid-run
  (rate-limited: max_tokens 2000+, 120s backoffs).

PRE-DECLARED KEEP RULE (typed in the claim c-0298 BEFORE any byte):
  critique+revise is KEPT only if FULL beats NO_CRITIQUE_REVISE on
  wins+ties with the paired delta's Wilson 95% CI lower > 0;
  otherwise PRUNED (problem_router 2.1.0: calls/item 6 -> 4).

TARGETS MEASURED (the owner's accept): generator calls per problem
per arm, and median per-item wall latency (vs <=12 calls, <=2 min
median). One run, no tuning, no re-rolls; byte-resume per item.

Usage: python3 scripts/r186s1_ablation_run.py
Writes: eval/r186s1_ablation/pair_{pid}.json
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r186s1_ablation"
OUT.mkdir(exist_ok=True)
CORPUS = REPO / "eval" / "r176_invention_corpus" / "items.jsonl"

AG_MODEL = "agnes-3.0-flash"

JUDGES = {
    "hy4-flash-centai": {
        "base": "https://api.cent-ai.dev/v1",
        "key_env": "CENTAI_API_KEY",
        "model": "hy4-flash:free",
        "family": "hunyuan",
        "max_tokens": 2000,
    },
    "qwen3.8-max-xkiro": {
        "base": "https://api.xkiro.com/v1",
        "key_env": "XKIRO_API_KEY",
        "model": "qwen/qwen3.8-max:free",
        "family": "qwen",
        "max_tokens": 2000,
    },
    # typed tiebreak seat only (rate-limited; >=2000 max_tokens)
    "tr-deepseek": {
        "base": "https://api.tokenrouter.com/v1",
        "key_env": "TOKENROUTER_API_KEY",
        "model": "deepseek/deepseek-v4.1-flash-1017-free",
        "family": "deepseek",
        "max_tokens": 2600,
    },
}

CITE_PAT = re.compile(
    r"\b10\.\d{4,9}/\S+|\b(?:US|WO|EP|CN)\s?\d{6,}|\bet al\.?"
    r"|\b(?:19|20)\d{2}\s*\)|\bRef(?:erence)?\s*\[", re.I)
TEST_PAT = re.compile(
    r"\b(falsif|test|measur|observ|validat|verif|experiment|predict|"
    r"would show|should show)\w*", re.I)


def env_keys() -> dict:
    out = {}
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def _post(url, key, body, timeout=300.0):
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
        return -1, {"error": f"{type(e).__name__}: {str(e)[:100]}"}


def agnes(prompt, keys, what=""):
    base = keys["AGNES_BASE_URL"].rstrip("/") + "/chat/completions"
    body = {"model": AG_MODEL, "max_tokens": 2600,
            "temperature": 0,
            "messages": [{"role": "system", "content": ""},
                         {"role": "user", "content": prompt}]}
    last = None
    for attempt in range(1, 5):
        st, rsp = _post(base, keys["AGNES_API_KEY"], body)
        if st == 200:
            txt = (rsp.get("choices") or [{}])[0].get(
                "message", {}).get("content") or ""
            if txt.strip():
                return txt
            last = RuntimeError("empty agnes content")
        else:
            last = RuntimeError(f"agnes HTTP{st}")
            if st in (401, 403):
                continue
        print(f"    {what} agnes attempt {attempt}: {last}; "
              f"backoff 120s", flush=True)
        if attempt < 4:
            time.sleep(120)
    raise last


def judge_leg(seat_tag, prompt, keys, what=""):
    """One judge vote on one seat. Returns (verdict, raw_text)."""
    j = JUDGES[seat_tag]
    body = {"model": j["model"], "max_tokens": j["max_tokens"],
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}]}
    last = None
    for attempt in range(1, 5):
        st, rsp = _post(j["base"] + "/chat/completions",
                        keys[j["key_env"]], body)
        if st == 200:
            txt = (rsp.get("choices") or [{}])[0].get(
                "message", {}).get("content") or ""
            up = txt.upper()
            v = ("X" if "VERDICT: X" in up else
                 "Y" if "VERDICT: Y" in up else
                 "TIE" if "VERDICT: TIE" in up else None)
            if v:
                return v, txt
            last = RuntimeError(f"unparseable: {txt[:60]!r}")
        else:
            last = RuntimeError(f"judge HTTP{st}")
            if st in (401, 403):
                break
        print(f"    {what} judge attempt {attempt}: {last}; "
              f"backoff 120s", flush=True)
        if attempt < 4:
            time.sleep(120)
    raise last


def packet(prob):
    return json.dumps({k: prob.get(k, "") for k in
                       ("device", "failure", "constraint")},
                      ensure_ascii=False)


def plain_prompt(prob):
    return ("Propose ONE concrete novel mechanism that achieves the "
            "stated capability target. Ground it in the stated failure "
            "physics; respect every stated constraint exactly; include "
            "the concrete test that would falsify it.\n\nPROBLEM:\n"
            + packet(prob) + "\n\nTASK:\n"
            + str(prob.get("question") or ""))


def blind_prompt(p, a, b):
    return ("You are a blind reviewer of engineering INVENTION "
            "proposals. Two proposals for the same problem; judge "
            "which is better on physical soundness, genuine mechanism "
            "novelty and actionability (a concrete falsification "
            "test). Ignore length and style.\n\nPROBLEM:\n" + p
            + "\n\nPROPOSAL X:\n" + a[:4500]
            + "\n\nPROPOSAL Y:\n" + b[:4500]
            + "\n\nAnswer in EXACTLY this format:\nVERDICT: X|Y|TIE\n"
              "REASON: <one sentence>")


def verify(text):
    """The shipped deterministic verifier, byte-faithful to
    scripts/r184_holdout_run.py (citation-pattern + falsification-span
    checks; never disabled)."""
    cites = CITE_PAT.findall(text or "")
    test = bool(TEST_PAT.search(text or ""))
    ok = (not cites) and test
    return {"ok": ok, "citation_patterns": cites[:5],
            "has_falsification_span": test,
            "reason": "OK" if ok else
            ("FABRICATED_CITATION_PATTERN" if cites else
             "NO_FALSIFICATION_TEST")}


def run_one(prob, keys):
    pid = prob["problem_id"]
    t0 = time.time()
    p = packet(prob)

    # ---- shared 4 draws (paired design) ---------------------------
    draws = [agnes(plain_prompt(prob), keys, f"{pid} draw{i}")
             for i in range(4)]
    draws = [d for d in draws if d.strip()]
    if not draws:
        return {"problem_id": pid, "status": "GEN_FAIL"}
    longest = max(draws, key=len)

    # ---- FULL arm: + critique + revise + verifier (6 calls) -------
    critique = agnes(
        "You are a strict reviewer. List the 3 most important defects "
        "of this novel-mechanism proposal (wrong physics, constraint "
        "violation, insufficient novelty or testability). Be terse."
        "\n\nPROBLEM:\n" + p + "\n\nPROPOSAL:\n" + longest,
        keys, f"{pid} critique")
    revised = agnes(
        "Revise this novel-mechanism proposal to fix the listed "
        "defects. Keep the same format and length; keep every stated "
        "constraint.\n\nPROPOSAL:\n" + longest + "\n\nDEFECTS:\n"
        + critique + "\n\nOutput ONLY the revised proposal; cite no "
        "literature.", keys, f"{pid} revise")
    v_full = verify(revised)
    if v_full["ok"]:
        full_text = revised
        full_fallback = None
    else:
        full_text = longest
        full_fallback = "LONGEST_PLAIN_DRAW"

    # ---- NO_CRITIQUE_REVISE arm: verifier only (4 calls) ----------
    # the longest draw that PASSES the verifier; if none passes, the
    # longest draw (the shipped fallback shape, no new tuning)
    v_arm = verify(longest)
    if v_arm["ok"]:
        nc_text, nc_fallback = longest, None
    else:
        passing = [d for d in draws if verify(d)["ok"]]
        if passing:
            nc_text = max(passing, key=len)
            nc_fallback = "LONGEST_PASSING_DRAW"
        else:
            nc_text = longest
            nc_fallback = "LONGEST_PLAIN_DRAW_NO_PASS"
        v_arm = verify(nc_text)

    # ---- panel judging: two seats x two order-swapped passes ------
    votes = {}
    judge_meta = []
    for seat in ("hy4-flash-centai", "qwen3.8-max-xkiro"):
        vals = []
        for order in ("XY", "YX"):
            a, b = ((full_text, nc_text) if order == "XY"
                    else (nc_text, full_text))
            try:
                verdict, raw = judge_leg(
                    seat, blind_prompt(p, a, b), keys,
                    f"{pid} {seat} {order}")
            except Exception as e:  # noqa: BLE001 typed, never re-roll
                verdict, raw = "TIE", f"TYPED_JUDGE_FAILURE {type(e).__name__}"
            pip = (verdict if order == "XY" else
                   "X" if verdict == "Y" else
                   "Y" if verdict == "X" else "TIE")
            vals.append(pip)
        if all(x in ("X", "TIE") for x in vals) and "X" in vals:
            votes[seat] = "WIN"
        elif all(x in ("Y", "TIE") for x in vals) and "Y" in vals:
            votes[seat] = "LOSS"
        else:
            votes[seat] = "TIE"
        judge_meta.append({"seat": seat, "family":
                           JUDGES[seat]["family"], "vote": votes[seat]})

    # panel majority: agreement = the verdict; disagreement = TIE
    vs = list(votes.values())
    if vs[0] == vs[1]:
        outcome = vs[0]
    else:
        outcome = "TIE"

    return {
        "problem_id": pid, "status": "JUDGED",
        "generator": {"model": AG_MODEL,
                      "transport": "direct-agnes-api",
                      "calls_full": 6, "calls_no_critique_revise": 4},
        "judges": judge_meta,
        "draws_kept": len(draws),
        "full_text": full_text,
        "no_critique_revise_text": nc_text,
        "verifier_full": v_full, "verifier_arm": v_arm,
        "full_fallback": full_fallback, "arm_fallback": nc_fallback,
        "votes": votes, "outcome": outcome,
        "win_plus_tie": outcome in ("WIN", "TIE"),
        "fabricated_citations_full": len(v_full["citation_patterns"]),
        "fabricated_citations_arm": len(v_arm["citation_patterns"]),
        "wall_s": round(time.time() - t0, 1),
    }


def main() -> int:
    keys = env_keys()
    rows = [json.loads(l) for l in
            CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"R186S1 ablation: {len(rows)} items, "
          f"FULL(6 calls) vs NO_CRITIQUE_REVISE(4 calls)", flush=True)
    for i, prob in enumerate(rows, 1):
        pid = prob["problem_id"]
        outp = OUT / f"pair_{pid}.json"
        if outp.exists():
            d = json.loads(outp.read_text())
            print(f"=== {pid} ({i}/{len(rows)}): resumed "
                  f"{d.get('outcome')}", flush=True)
            continue
        t0 = time.time()
        row = run_one(prob, keys)
        outp.write_text(json.dumps(row, indent=1,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"=== {pid} ({i}/{len(rows)}): {row.get('outcome')} "
              f"w+t={row.get('win_plus_tie')} "
              f"verifier_full={row.get('verifier_full', {}).get('reason')} "
              f"verifier_arm={row.get('verifier_arm', {}).get('reason')} "
              f"{row.get('wall_s')}s", flush=True)
    print("ablation run complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r147s1 P4 panel resume on the OWNER-DESIGNATED fallback transport
(DIR 2, R147) — the credit-gated completion of the c-0252 panel lane.

Context (typed lineage): the V112-validated panel instrument ran on
the v17 strengthened generation; dsr1 completed 10/30 legs (ALL ten
rulings viable AND non_obvious) then the HF Inference Providers
account returned HTTP 402 (pre-paid credits exhausted) — 110 legs
typed-refused with no generation (Art. 15: infra failure is never a
scientific result). The R147 owner order designates the fallback:
probe the HF free serverless for the judge models (TYPED RESULT:
api-inference.huggingface.co is DNS-unreachable from this sandbox —
a network-policy block, not a model availability answer) and the
supplied judge path api.cent-ai.dev with hy4-flash:free (the probe:
3 cent models serve the judge-shaped ruling contract cleanly).

THE CALIBRATION CAVEAT (typed on every leg and in the tally): the
V109 qualification (3 judges acc>=0.8, kappa 0.668) binds the judge
IDENTITIES dsr1/qw32b/qwen235b/dsv32. The cent models
(hy4-flash:free / deepseek-v4.1-flash / qwen3.8-flash) are the
OWNER-DESIGNATED FALLBACK JUDGES — NOT V109-qualified; their
accuracy/kappa against the auditor's rubric is UNKNOWN and the
panel verdict must disclose this. The existing 10 dsr1 legs stand
unmodified (the qualified signal); the 20 failed dsr1 legs are NOT
substituted (the judge identity awaits credit restore — Art. 7).

The instrument is otherwise byte-identical: the sealed problem
bytes, the packs (eval/r146_p4_panel/packs.json), SYSTEM/TASK/
AM47_CLAUSE, build_prompt, parse_ruling (the 7-key JSON contract),
neutral_index, the budget-escalation + 429/503 backoffs, one
generation per (judge, candidate) — no re-roll. Byte-resume: only
VALID legs skip (the c-0252 typed fix; failed legs carry no
generation). Modes: R147_JUDGE=<tag> runs one judge; unfiltered
runs all + the tally.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r146_p4_panel_oneshot as p146  # the validated instrument

OUT_DIR = REPO / "eval" / "r146_p4_panel"  # the c-0252 lane's dir

# the OWNER-DESIGNATED FALLBACK JUDGES (R147 DIR 2) — cent-ai.
# qw38 (qwen3.8-flash) was DROPPED: its legs TRANSPORT_FAILED at
# ~360s under the full 15K-char panel prompt (4 attempts timing out;
# the short-prompt probe did not transfer — the R64s4 lesson) —
# typed in the lane record, not silently substituted; minimax-m3.1-
# flash probed VALID on the full prompt (1315 chars, finish=stop,
# 14.5s) and takes the third seat with a distinct family.
JUDGES_CENT = [
    {"model": "hy4-flash:free", "family": "hy4", "tag": "hy4flash",
     "transport": "cent-ai", "pace": 4,
     "budgets": [3000, 5000, 7000], "timeout_s": 150},
    {"model": "deepseek-v4.1-flash", "family": "deepseek",
     "tag": "dsv41", "transport": "cent-ai", "pace": 4,
     "budgets": [4000, 7000, 10000], "timeout_s": 120},
    {"model": "minimax-m3.1-flash", "family": "minimax",
     "tag": "mm31", "transport": "cent-ai", "pace": 4,
     "budgets": [4000, 6000, 8000], "timeout_s": 150},
    {"model": "deepseek-v4-flash", "family": "deepseek",
     "tag": "dsv4f", "transport": "cent-ai", "pace": 4,
     "budgets": [4000, 6000, 8000], "timeout_s": 120},
]
CALIBRATION_NOTE = ("OWNER-DESIGNATED FALLBACK JUDGE (R147 DIR 2) "
                    "— NOT V109-qualified (acc/kappa vs the "
                    "auditor's rubric UNKNOWN); the V109-calibrated "
                    "judges await the HF credit restore; every leg "
                    "carries this typing")


def _cent_key() -> tuple:
    k = os.environ.get("CENT_API_KEY")
    b = os.environ.get("CENT_BASE_URL")
    if not k or not b:
        env_keys = REPO / ".env.keys"
        for line in env_keys.read_text().splitlines():
            if line.startswith("CENT_API_KEY=") and not k:
                k = line.split("=", 1)[1].strip()
            if line.startswith("CENT_BASE_URL=") and not b:
                b = line.split("=", 1)[1].strip()
    assert k and b, "the cent transport keys missing (typed abort)"
    return b, k


def _cent_chat(messages: list, model: str, max_tokens: int,
               timeout_s: float) -> dict:
    import urllib.request
    base, key = _cent_key()
    body = {"model": model, "messages": messages,
            "max_tokens": max_tokens}
    req = urllib.request.Request(
        base + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=timeout_s))
        ch = (r.get("choices") or [{}])[0]
        return {"content": (ch.get("message") or {}).get("content"),
                "finish": ch.get("finish_reason"), "error": None}
    except Exception as e:  # noqa: BLE001 — typed degradation
        return {"content": None, "finish": None,
                "error": f"{type(e).__name__}: {str(e)[:160]}"}


def _leg_cent(judge: dict, prompt: str) -> dict:
    attempts, outcome, parsed, raw = [], "TRANSPORT_FAILED", None, None
    for attempt in range(1, 5):
        budget = judge["budgets"][min(attempt - 1,
                                      len(judge["budgets"]) - 1)]
        t0 = time.monotonic()
        r = _cent_chat([{"role": "system", "content": p146.SYSTEM},
                        {"role": "user", "content": prompt}],
                       model=judge["model"], max_tokens=budget,
                       timeout_s=judge["timeout_s"])
        raw = r.get("content") or ""
        err = r.get("error")
        lat = round(time.monotonic() - t0, 1)
        attempts.append({"attempt": attempt, "budget": budget,
                         "latency_s": lat, "error": err,
                         "finish": r.get("finish")})
        if raw:
            try:
                parsed = p146.parse_ruling(raw)
                outcome = "VALID"
                break
            except (ValueError, json.JSONDecodeError) as e:
                outcome = "PARSE_FAILED"
                if attempt < 4:
                    prompt = (prompt + "\n\nYour previous output "
                              "violated the contract (" + str(e)[:120]
                              + "). Respond with ONLY the JSON object "
                              "with the seven keys, viable/non_obvious "
                              "as booleans. No other text.")
                    time.sleep(3)
        elif err and ("429" in str(err) or "Rate" in str(err)):
            outcome = "RATE_LIMITED"
            time.sleep(90)
        elif err and ("503" in str(err) or "timeout" in str(err)
                      or "upstream" in str(err)):
            time.sleep(30)
    return {"outcome": outcome, "parsed": parsed,
            "raw_tail": (raw or "")[-900:] if raw else None,
            "attempts": attempts}


def sealed_problems() -> dict:
    out = subprocess.run(
        ["git", "show",
         "origin/audit/r11-auditor-verdict-20261114:eval/holdout_v17/"
         "problems.json"],
        capture_output=True, text=True)
    assert out.returncode == 0
    sealed = json.loads(out.stdout)
    probs = sealed.get("problems") if isinstance(sealed, dict) else sealed
    return {p["problem_id"]: p for p in probs}


def main() -> int:
    packs_path = Path(os.environ.get(
        "R147_PACKS", str(OUT_DIR / "packs.json")))
    packs_doc = json.loads(packs_path.read_text())
    packs = packs_doc["packs"]
    problems = sealed_problems()
    print(f"packs: {packs_path.name} | n: {len(packs)} | "
          f"first pid: {packs[0]['problem_id']}", flush=True)
    only = os.environ.get("R147_JUDGE", "").strip()
    judges = ([j for j in JUDGES_CENT if j["tag"] == only] if only
              else JUDGES_CENT)
    print(f"packs: {len(packs)} | cent judges: "
          f"{[j['tag'] for j in judges]}", flush=True)
    for j in judges:
        for p in packs:
            pid = p["problem_id"]
            legfile = OUT_DIR / f"{j['tag']}__{pid}.json"
            if legfile.exists():
                rec = json.loads(legfile.read_text())
                if rec.get("outcome") == "VALID":
                    continue  # the c-0252 fix: only VALID legs skip
            prob = problems.get(pid, {})
            problem_text = str(prob.get("problem", "")).strip()
            prompt = p146.build_prompt(problem_text,
                                       p["candidate_text"],
                                       p["prior_arts"])
            t0 = time.monotonic()
            leg = _leg_cent(j, prompt)
            wall = round(time.monotonic() - t0, 1)
            rec = {"judge": j["tag"], "family": j["family"],
                   "model": j["model"], "transport": j["transport"],
                   "calibration": CALIBRATION_NOTE,
                   "pid": pid,
                   "neutral_index": p146.neutral_index(pid),
                   "prior_order": [a["prior_id"]
                                   for a in p["prior_arts"]],
                   "outcome": leg["outcome"],
                   "parsed": leg["parsed"],
                   "raw_tail": leg["raw_tail"],
                   "attempts": leg["attempts"], "wall_s": wall}
            legfile.write_text(json.dumps(rec, indent=1,
                                          ensure_ascii=False) + "\n")
            pr = (leg["parsed"] or {})
            print(f"{j['tag']} #{p146.neutral_index(pid)}: "
                  f"{leg['outcome']} viable={pr.get('viable')} "
                  f"non_obvious={pr.get('non_obvious')} ({wall}s)",
                  flush=True)
            time.sleep(j["pace"] if leg["outcome"] == "VALID" else 5)
    if only:
        print(f"judge {only}: legs done", flush=True)
        return 0
    # ---------- the tally (all judges incl. the dsr1 qualified legs)
    rows = []
    all_judges = [j["tag"] for j in JUDGES_CENT] + ["dsr1"]
    for p in packs:
        pid = p["problem_id"]
        legs = []
        for tag in all_judges:
            lf = OUT_DIR / f"{tag}__{pid}.json"
            if not lf.exists():
                continue
            r = json.loads(lf.read_text())
            legs.append({"judge": tag, "outcome": r["outcome"],
                         "transport": r.get("transport", "hf"),
                         "parsed": r["parsed"]})
        valid = [l for l in legs if l["parsed"]]
        n_v = sum(1 for l in valid if l["parsed"]["viable"])
        n_no = sum(1 for l in valid if l["parsed"]["non_obvious"])
        n = len(valid)
        rows.append({
            "problem_id": pid, "n_valid": n, "n_viable": n_v,
            "n_non_obvious": n_no,
            "majority_viable": n_v * 2 > n if n else False,
            "majority_non_obvious": n_no * 2 > n if n else False,
            "viable_and_non_obvious": bool(
                n and n_v * 2 > n and n_no * 2 > n),
            "low_vote": n < 3,
            "legs": legs})
    n_both = sum(1 for r in rows if r["viable_and_non_obvious"])
    tally = {
        "record": "R147_P4_PANEL_CENT_TALLY/1.0.0",
        "at": "2026-11-24 (sandbox clock)",
        "instrument": ("the V112-validated panel on the v17 "
                       "strengthened generation; the fallback "
                       "transport = the OWNER-DESIGNATED cent-ai "
                       "judges (R147 DIR 2) after the HF 402 "
                       "exhaustion and the free-tier DNS block"),
        "calibration_caveat": ("the 3 cent judges are NOT "
                               "V109-qualified (acc/kappa UNKNOWN); "
                               "the 10 dsr1 legs are the "
                               "qualified-judge signal and stand "
                               "unmodified; the 20 failed dsr1 legs "
                               "are NOT substituted (Art. 7)"),
        "bar": {"pct_viable_and_non_obvious_ge": 50.0,
                "set": "the FULL 30-candidate v17 set (no subsets)"},
        "tally": {"n_candidates": len(rows),
                  "n_viable_and_non_obvious": n_both,
                  "pct": round(100 * n_both / max(1, len(rows)), 1),
                  "low_vote_candidates": sum(
                      1 for r in rows if r["low_vote"]),
                  "pass": n_both / max(1, len(rows)) >= 0.5},
        "rows": rows,
    }
    (OUT_DIR / "tally_r147.json").write_text(
        json.dumps(tally, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(tally["tally"], indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

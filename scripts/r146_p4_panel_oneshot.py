#!/usr/bin/env python3
"""r146s1 P4 panel oneshot — the r145 panel instrument BYTE-FAITHFUL
(the same V109-qualified four judges, the same blind neutral index,
the same sha-parity swap, the same AM47 viability-necessity clause,
the same EPO problem-solution ruling contract) re-pointed at the
r146 v17 NOVELTY-strength candidates (DIR-4: rate the STRENGTHENED
generation). One generation per (judge, candidate), byte-resume;
the tally uses the majority rule (>=3/4 viable AND non-obvious).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT_DIR = REPO / "eval" / "r146_p4_panel"
PACKS = OUT_DIR / "packs.json"

JUDGES = [
    {"model": "deepseek-ai/DeepSeek-R1", "family": "deepseek",
     "tag": "dsr1", "transport": "hf", "pace": 20,
     "budgets": [8000, 12000, 16000], "timeout_s": 420.0},
    {"model": "Qwen/Qwen3-32B", "family": "qwen",
     "tag": "qw32b", "transport": "hf", "pace": 20,
     "budgets": [8000, 12000, 16000], "timeout_s": 420.0},
    {"model": "Qwen/Qwen3-235B-A22B-Instruct-2507", "family": "qwen",
     "tag": "qwen235b", "transport": "hf", "pace": 20,
     "budgets": [4000, 8000, 12000], "timeout_s": 300.0},
    {"model": "deepseek-ai/DeepSeek-V3.2", "family": "deepseek",
     "tag": "dsv32", "transport": "hf", "pace": 20,
     "budgets": [4000, 8000, 12000], "timeout_s": 300.0},
]

SYSTEM = ("You are a strict blind patent-examiner-style judge. "
          "English only. Follow the response contract exactly.")

AM47_CLAUSE = (
    "VIABILITY IS NECESSARY: a mechanism that is infeasible or "
    "untestable AS WRITTEN (requires unobtainium, violates a stated "
    "constraint, cannot be validated, or is physically implausible "
    "at the stated scale) is NOT the better invention, NO MATTER "
    "how novel it is. Novelty alone never wins.")

TASK = f"""
You judge ONE candidate engineering solution against EXTERNAL PRIOR
ART, using the problem-solution approach (the inventive-step shape).

{AM47_CLAUSE}

Your analysis, in order:
1. CLOSEST PRIOR ART: which of PRIOR ART 1/2/3 is the closest to
   the candidate's mechanism (or "none" if none is close).
2. DISTINGUISHING FEATURES: what the candidate has that the closest
   prior art lacks (up to 4, one line each; empty if none).
3. OBJECTIVE TECHNICAL PROBLEM: the technical problem those
   distinguishing features actually solve, phrased independently of
   the solution's wording.
4. VIABLE (true/false): is the candidate a sound, physically
   feasible mechanism that addresses the stated failure mode, at
   the stated scale, as written?
5. NON-OBVIOUS (true/false): would the distinguishing features
   have been OBVIOUS to a skilled engineer facing the objective
   technical problem with the closest prior art at hand? Answer
   false when the candidate merely applies the closest art's
   approach with routine parameter changes; answer true only when
   the distinguishing mechanism itself is not an obvious step.

Respond with ONLY this JSON object (no other text):
{{"closest_prior_art": "1" | "2" | "3" | "none",
 "distinguishing_features": ["...", "..."],
 "objective_technical_problem": "...",
 "viable": true | false,
 "non_obvious": true | false,
 "viable_reason": "one sentence",
 "non_obvious_reason": "one sentence"}}
"""

REQUIRED_KEYS = {"closest_prior_art", "distinguishing_features",
                 "objective_technical_problem", "viable",
                 "non_obvious", "viable_reason",
                 "non_obvious_reason"}


def neutral_index(pid: str) -> int:
    return int(hashlib.sha256(f"{pid}::r146idx".encode())
               .hexdigest()[:8], 16) % 900 + 100


def build_prompt(problem_text: str, cand_text: str,
                 prior_arts: list) -> str:
    lines = [
        "You judge one engineering answer against external prior art.",
        "",
        f"PROBLEM: {problem_text.strip()}",
        "",
        "CANDIDATE SOLUTION:",
        cand_text.strip()[:5200],
        "",
        "EXTERNAL PRIOR ART (the closest known solutions from the "
        "field, retrieved independently):",
    ]
    for i, pa in enumerate(prior_arts, 1):
        lines.append(f"PRIOR ART {i}: {pa['text'].strip()[:2600]}")
    lines.append(TASK)
    return "\n".join(lines)


def parse_ruling(raw: str) -> dict:
    import re
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("no JSON object found")
    d = json.loads(m.group(0))
    missing = REQUIRED_KEYS - set(d.keys())
    if missing:
        raise ValueError(f"missing keys: {sorted(missing)}")
    if str(d["closest_prior_art"]) not in ("1", "2", "3", "none"):
        raise ValueError("closest_prior_art must be 1|2|3|none")
    if not isinstance(d["viable"], bool) or \
            not isinstance(d["non_obvious"], bool):
        raise ValueError("viable/non_obvious must be booleans")
    feats = d["distinguishing_features"]
    if not isinstance(feats, list) or \
            any(not isinstance(x, str) for x in feats):
        raise ValueError("distinguishing_features must be a list "
                         "of strings")
    return d


def _leg(judge: dict, prompt: str) -> dict:
    attempts, outcome, parsed, raw = [], "TRANSPORT_FAILED", None, None
    for attempt in range(1, 5):
        budget = judge["budgets"][min(attempt - 1,
                                      len(judge["budgets"]) - 1)]
        t0 = time.monotonic()
        try:
            from discovery_fabric.engine.route_adapter import (
                hf_router_chat)
            r = hf_router_chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": prompt}],
                model=judge["model"], max_tokens=budget,
                timeout_s=judge["timeout_s"])
            raw = r.get("content") or ""
            err = r.get("error")
        except Exception as e:  # noqa: BLE001 — typed degradation
            raw, err = None, f"{type(e).__name__}: {str(e)[:160]}"
        lat = round(time.monotonic() - t0, 1)
        attempts.append({"attempt": attempt, "budget": budget,
                         "latency_s": lat, "error": err})
        if raw:
            try:
                parsed = parse_ruling(raw)
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
            time.sleep(120)
        elif err and ("503" in str(err) or "timeout" in str(err)
                      or "upstream" in str(err)):
            time.sleep(30)
    return {"outcome": outcome, "parsed": parsed,
            "raw_tail": (raw or "")[-900:] if raw else None,
            "attempts": attempts}


def main() -> int:
    from r7_queue_runner import _load_key_vault
    _load_key_vault()
    packs_doc = json.loads(PACKS.read_text())
    packs = packs_doc["packs"]
    problems = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval/holdout_v17/problems.json").read_text())}

    only = os.environ.get("R146_JUDGE", "").strip()
    judges = ([j for j in JUDGES if j["tag"] == only] if only
              else JUDGES)
    print(f"packs: {len(packs)} | judges: "
          f"{[j['tag'] for j in judges]}", flush=True)

    for j in judges:
        for pk in packs:
            pid = pk["problem_id"]
            outp = OUT_DIR / f"{j['tag']}__{pid}.json"
            if outp.exists():  # byte-resume, same ruling
                continue
            prob_text = (problems.get(pid) or {}).get("problem", "")
            prompt = build_prompt(prob_text, pk["candidate_text"],
                                  pk["prior_arts"])
            t0 = time.monotonic()
            leg = _leg(j, prompt)
            rec = {"judge": j["tag"], "family": j["family"],
                   "model": j["model"], "pid": pid,
                   "neutral_index": neutral_index(pid),
                   "prior_order": [
                       pa["prior_id"] for pa in pk["prior_arts"]],
                   "outcome": leg["outcome"], "parsed": leg["parsed"],
                   "raw_tail": leg["raw_tail"],
                   "attempts": leg["attempts"],
                   "wall_s": round(time.monotonic() - t0, 1)}
            outp.write_text(json.dumps(rec, indent=1) + "\n",
                            encoding="utf-8")
            print(f"{j['tag']} {pid}: {rec['outcome']} "
                  f"v={leg['parsed'].get('viable') if leg['parsed'] else '-'} "
                  f"n={leg['parsed'].get('non_obvious') if leg['parsed'] else '-'} "
                  f"{rec['wall_s']}s", flush=True)
            time.sleep(j["pace"])

    # the tally (the majority rule, the FULL set only)
    import collections
    by_pid = collections.defaultdict(dict)
    for pk in packs:
        pid = pk["problem_id"]
        for j in JUDGES:
            f = OUT_DIR / f"{j['tag']}__{pid}.json"
            if not f.exists():
                continue
            d = json.loads(f.read_text())
            p = d.get("parsed") or {}
            if isinstance(p, dict) and d.get("outcome") == "VALID":
                by_pid[pid][j["tag"]] = bool(p.get("viable")) and \
                    bool(p.get("non_obvious"))
    tally_rows = []
    n_pass = 0
    for pid in sorted(by_pid):
        yes = sum(1 for v in by_pid[pid].values() if v)
        total = len(by_pid[pid])
        passed = total >= 3 and yes >= 3
        n_pass += passed
        tally_rows.append({"problem_id": pid, "yes": yes,
                           "judges_total": total, "passed": passed})
    pct = round(100.0 * n_pass / max(1, len(tally_rows)), 1)
    tally = {
        "record": "r146_p4_calibrated_panel/1.0.0 — the V109-"
                  "qualified four judges, blind (neutral sha-derived "
                  "index) + swapped (the prior-art sha-parity "
                  "rotation), on the FULL r146 v17 30-candidate set; "
                  "the majority rule >=3/4 viable AND non-obvious",
        "instrument": {"judges": [j["tag"] for j in JUDGES],
                       "qualification": "the V109-qualified panel "
                       "(acc>=0.8, kappa 0.668, 2 non-agnes families); "
                       "no re-qualification, no new judges",
                       "bar_pct_ge": 50.0,
                       "set": "the FULL 30-candidate set (no subsets)"},
        "tally": {"n_candidates": len(tally_rows),
                  "n_viable_and_non_obvious": n_pass, "pct": pct,
                  "pass": bool(pct >= 50.0)},
        "rows": tally_rows}
    (OUT_DIR / "tally.json").write_text(json.dumps(tally, indent=1)
                                        + "\n")
    print(f"TALLY: {n_pass}/{len(tally_rows)} = {pct}% "
          f"(bar >= 50%)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

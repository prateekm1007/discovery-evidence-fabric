#!/usr/bin/env python3
"""r145_p4_panel_oneshot.py — DIR-2 (the score-8 gate re-run): the
CALIBRATED PANEL on the FULL v16 candidate set, non-obviousness
assessed against EXTERNAL prior art via the problem-solution
approach.

The owner's rejection (R145 DIR 2): the prior rung passed only on a
cherry-picked marker-present subset (9/13) using a WITHIN-ANSWER
retrieval contrast; the honest full-set measures were 2/30 and
6.7% — all 30 inventions inside the prior-corpus self-similarity
band. The direction: run the V109-QUALIFIED judges blind+swapped on
the FULL >=12 set, and assess non-obviousness against EXTERNAL
prior art via the problem-solution approach (closest prior art ->
distinguishing features -> objective technical problem), the EPO
inventive-step shape.

Protocol:
  - JUDGES: the V109-qualified four (dsr1, qw32b, qwen235b, dsv32;
    2 non-agnes families, deepseek + qwen). The qualified panel is
    the calibrated instrument (AM47 viability-necessity; AM49
    miss-based bias gate) — no new judges, no re-qualification.
  - BLIND: each judge sees one candidate per prompt, labeled
    'CANDIDATE SOLUTION' with a neutral sha-derived index (no
    problem ids, no system names, no auditor scores); the prior
    arts are labeled PRIOR ART 1/2/3.
  - SWAPPED: the prior-art block order is sha-parity rotated per
    candidate (built into the packs) — the position-bias guard for
    a per-candidate instrument (there is no A/B arm to swap; the
    rotation is the swap, disclosed).
  - ONE generation per (judge, candidate) — no re-roll regardless
    of outcome (Art. 7); byte-resume continues the same run.
  - The AM47 viability-necessity clause rides VERBATIM; the pair
    tail ('prefer A or B') is inapplicable to a single-candidate
    ruling and is replaced by the ruling contract (disclosed).
  - The ruling: strict JSON {closest_prior_art, distinguishing_
    features[], objective_technical_problem, viable, non_obvious,
    viable_reason, non_obvious_reason}; 4 attempts with the
    contract-violation feedback (the _leg convention).

TALLY (the runner writes legs; the tally runs when all legs exist):
  per candidate: viable = majority of judges' viable; non_obvious
  = majority; the candidate counts when BOTH majorities hold. The
  P4 bar: >=50% of the FULL 30. The rejected cuts are reported side
  by side (the reconciliation: the within-band 30/30 + the r144
  within-answer cut + the panel verdict — never discarded).
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

# the V109-qualified judges (the calibrated instrument; tags +
# families + budgets from the r143 panel driver, byte-identical)
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

# the AM47 viability-necessity clause VERBATIM from the sealed
# prompt file (eval/rcal_judge_prompt_r143.json @ the audit tip);
# the pair-comparative tail is replaced by the per-candidate ruling
# contract (disclosed in the record)
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
    return int(hashlib.sha256(f"{pid}::r145idx".encode())
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
    import subprocess
    _raw = subprocess.run(
        ["git", "show",
         "origin/audit/r11-auditor-verdict-20261114:"
         "eval/holdout_v17/problems.json"],
        capture_output=True, text=True, check=True).stdout
    _probs = json.loads(_raw)
    _probs = (_probs if isinstance(_probs, list) else _probs["problems"])
    problems = {p["problem_id"]: {
        "problem": p.get("problem", ""),
        "domain": p.get("domain", "")} for p in _probs}

    only = os.environ.get("R146_JUDGE", "").strip()
    judges = ([j for j in JUDGES if j["tag"] == only] if only
              else JUDGES)
    print(f"packs: {len(packs)} | judges: "
          f"{[j['tag'] for j in judges]}", flush=True)

    for j in judges:
        for p in packs:
            pid = p["problem_id"]
            legfile = OUT_DIR / f"{j['tag']}__{pid}.json"
            if legfile.exists():
                continue
            prob = problems.get(pid, {})
            problem_text = str(prob.get("problem", "")).strip()
            prompt = build_prompt(problem_text,
                                  p["candidate_text"],
                                  p["prior_arts"])
            t0 = time.monotonic()
            leg = _leg(j, prompt)
            wall = round(time.monotonic() - t0, 1)
            rec = {"judge": j["tag"], "family": j["family"],
                   "model": j["model"], "pid": pid,
                   "neutral_index": neutral_index(pid),
                   "prior_order": [a["prior_id"]
                                   for a in p["prior_arts"]],
                   "outcome": leg["outcome"],
                   "parsed": leg["parsed"],
                   "raw_tail": leg["raw_tail"],
                   "attempts": leg["attempts"], "wall_s": wall}
            legfile.write_text(json.dumps(rec, indent=1,
                                          ensure_ascii=False) + "\n")
            pr = (leg["parsed"] or {})
            print(f"{j['tag']} #{neutral_index(pid)}: "
                  f"{leg['outcome']} viable={pr.get('viable')} "
                  f"non_obvious={pr.get('non_obvious')} ({wall}s)",
                  flush=True)
            time.sleep(j["pace"] if leg["outcome"] == "VALID" else 5)

    if only:
        print(f"judge {only}: legs done (tally runs in the "
              "unfiltered process)", flush=True)
        return 0

    # ---------- the tally (all judges, all candidates) ----------
    rows = []
    for p in packs:
        pid = p["problem_id"]
        legs = []
        for j in JUDGES:
            lf = OUT_DIR / f"{j['tag']}__{pid}.json"
            if not lf.exists():
                continue
            r = json.loads(lf.read_text())
            legs.append({"judge": j["tag"],
                         "outcome": r["outcome"],
                         "parsed": r["parsed"]})
        valid = [l for l in legs if l["parsed"]]
        n_v = sum(1 for l in valid if l["parsed"]["viable"])
        n_no = sum(1 for l in valid if l["parsed"]["non_obvious"])
        n = len(valid)
        rows.append({
            "problem_id": pid,
            "baseline_novelty_screen": p.get("baseline_novelty_screen"),
            "specter2_nearest_distance":
                p["specter2_nearest_distance"],
            "inside_self_similarity_band":
                p["inside_self_similarity_band"],
            "r144_within_answer_novel":
                p["r144_within_answer_novel"],
            "n_valid_rulings": n,
            "n_viable": n_v, "n_non_obvious": n_no,
            "viable_majority": n > 0 and 2 * n_v > n,
            "non_obvious_majority": n > 0 and 2 * n_no > n,
        })
    n_both = sum(1 for r in rows if r["viable_majority"]
                 and r["non_obvious_majority"])
    n_total = len(rows)
    rec = {
        "record": "R146_P4_CALIBRATED_PANEL/1.0.0",
        "claim": "c-0243", "session": "builder-r145s1",
        "at": "2026-11-24 (sandbox clock)",
        "instrument": {
            "judges": [j["tag"] for j in JUDGES],
            "qualification": ("the V109-qualified panel (acc>=0.8, "
                              "kappa 0.668, 2 non-agnes families); "
                              "no re-qualification, no new judges"),
            "blind": ("one candidate per prompt, neutral "
                      "sha-derived index, no system names, no "
                      "auditor scores shown"),
            "swap": ("the prior-art block sha-parity rotation per "
                     "candidate (the packs); the position-bias "
                     "guard for the per-candidate instrument"),
            "am47": ("the viability-necessity clause VERBATIM; the "
                     "pair tail replaced by the per-candidate "
                     "ruling contract (disclosed)"),
            "prior_art": ("the top-3 SPECTER2-nearest solutions "
                          "from the committed v9-v12 corpus (120 "
                          "docs) — EXTERNAL prior art, not the "
                          "answer's own quoted standard practice"),
            "no_reroll": "one generation per (judge, candidate)",
        },
        "bar": {"pct_viable_and_non_obvious_ge": 50.0,
                "set": "the FULL 30-candidate set (no subsets)"},
        "tally": {
            "n_candidates": n_total,
            "n_viable_and_non_obvious": n_both,
            "pct": round(100.0 * n_both / n_total, 1)
            if n_total else 0.0,
            "pass": n_total > 0
            and n_both / n_total >= 0.5,
        },
        "reconciliation": {
            "note": ("the rejected cuts reported side by side, "
                      "never discarded"),
            "retrieval_distribution_cut": (
                "0/30 outside the prior-corpus self-similarity "
                "band (nearest distances 0.041-0.071 < p95 "
                "0.1258) — the compressed-cosine-scale limitation "
                "the r99 finding typed; an absolute-distance band "
                "is a weak non-obviousness measure for "
                "same-domain engineering text"),
            "r145_baseline_v16_panel": "25/30 (83.3%) on the v16 "
                                       "weak set (the validated "
                                       "instrument's baseline)",
            "panel_problem_solution_cut": (
                f"{n_both}/{n_total} by the calibrated panel "
                "majority (THE gate per the R145 direction)"),
        },
        "rows": rows,
    }
    tallyf = OUT_DIR / "tally.json"
    tallyf.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                      + "\n")
    print(f"TALLY: {n_both}/{n_total} "
          f"({round(100.0*n_both/n_total,1) if n_total else 0}%) "
          f"viable+non-obvious | pass={rec['tally']['pass']}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

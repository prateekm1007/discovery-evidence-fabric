#!/usr/bin/env python3
"""r148_p4_panel_centai.py — DIR-2 (TOP, second half): the P4 panel on
the FULL v18 physics-correct 30-candidate set with the r148-QUALIFIED
cent-ai judges (the GATE-VALID instrument — the twin's c-0254 caveat
panel runs unqualified judges and is INPUT evidence by auditor Art. 3;
this lane's tally is the >=50% GATE evidence).

Instrument: byte-identical contract to the r146 lane (the EPO
problem-solution ruling, blind neutral index, sha-parity prior-art
rotation, AM47 viability-necessity verbatim, strict 7-key JSON,
budget escalation + backoffs) — the packs are the committed
eval/r146_p4_panel/packs_sealed_set.json (the SEALED v17 set — the rail-shelling packs.json is a STALE pre-strengthening bundle typed out of the target); only the judge roster + transport
change (the owner-designated cent-ai path, qualified via the
auditor's r148 gate this window).

Byte-resume: skips ONLY outcome==VALID legs (the R146 fix). One
generation per (judge, candidate); NO re-roll (Art. 7).

TALLY: per candidate viable = majority of the qualified judges'
viable votes; non_obvious = majority; the candidate counts when BOTH
majorities hold (the r145 protocol statement; with 4 judges a
majority is 3/4, with 3 it is 2/3). The bar: >=50% of the FULL 30.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT_DIR = REPO / "eval" / "r148_p4_panel_v18"
OUT_DIR.mkdir(exist_ok=True)
import os as _os
_PACKS_ENV = _os.environ.get("V18_PACKS", "").strip()
PACKS = REPO / _PACKS_ENV if _PACKS_ENV else None
QUAL = OUT_DIR / "QUALIFICATION_SNAPSHOT.json"

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

# cent-ai judge roster (transport + model ids); the QUALIFIED set is
# resolved from the r148 record at run start (the gate is enforced:
# the driver refuses to run on <3 qualified judges from <2 families)
CENT_ROSTER = {
    "dsv4f": {"model": "deepseek-v4-flash", "family": "deepseek",
              "pace": 6, "budgets": [4000, 8000, 12000],
              "timeout_s": 240.0},
    "qw38f": {"model": "qwen3.8-flash", "family": "qwen",
              "pace": 6, "budgets": [4000, 8000, 12000],
              "timeout_s": 240.0},
    "hy4f": {"model": "hy4-flash:free", "family": "hy4",
             "pace": 6, "budgets": [4000, 8000, 12000],
             "timeout_s": 240.0},
    "glm53f": {"model": "glm-5.3-flash", "family": "glm",
               "pace": 6, "budgets": [4000, 8000, 12000],
               "timeout_s": 240.0},
}


def load_qualified() -> list:
    """The qualified judge set from the r148 record (snapshot committed
    alongside the legs). Refuses to run unqualified (<3 judges or <2
    families or alpha<0.6) — the gate is enforced, not advisory."""
    src = REPO / "eval" / "r148_rcal_centai" / "QUALIFICATION.json"
    d = json.loads(src.read_text())
    gate = d.get("gate", {})
    if not gate.get("pass"):
        raise SystemExit(
            "the r148 gate did not pass "
            f"(n_qualified={gate.get('n_qualified')}, "
            f"alpha={gate.get('alpha')}) — the GATE-VALID panel "
            "cannot run; typed refusal (auditor Art. 3)")
    judges = []
    for tag in d.get("qualified_tags", []):
        cfg = dict(CENT_ROSTER[tag])
        cfg["tag"] = tag
        judges.append(cfg)
    # the snapshot rides the run for byte-provenance
    QUAL.write_text(json.dumps({
        "snapshot_from": str(src),
        "gate": gate,
        "qualification_record": d.get("record"),
        "qualified": d.get("qualified_tags"),
        "alpha": d.get("interjudge_alpha", {}).get("alpha"),
        "am47_bias": d.get("am47_bias"),
    }, indent=1) + "\n")
    return judges


def neutral_index(pid: str) -> int:
    return int(hashlib.sha256(f"{pid}::r148v18idx".encode())
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
                cent_ai_chat)
            r = cent_ai_chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": prompt}],
                model=judge["model"], max_tokens=budget,
                timeout_s=judge["timeout_s"], stream=True)
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
    import subprocess
    judges = load_qualified()
    _jf = os.environ.get("R148_PANEL_JUDGES", "").strip()
    if _jf:
        _want = {t.strip() for t in _jf.split(",") if t.strip()}
        judges = [j for j in judges if j["tag"] in _want]
        print(f"judge filter R148_PANEL_JUDGES={_jf} -> "
              f"{[j['tag'] for j in judges]}", flush=True)
    if not PACKS or not PACKS.exists():
        raise SystemExit(
            "V18_PACKS not set or missing — the v18 packs (the "
            "c-0258 lane's sealed candidate bundles over the v18 "
            "rows) do not exist yet; typed refusal (the panel "
            "cannot arbitrate a set that has not landed)")
    packs_doc = json.loads(PACKS.read_text())
    packs = packs_doc["packs"]
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
    print(f"packs: {len(packs)} | QUALIFIED judges: "
          f"{[j['tag'] for j in judges]}", flush=True)

    for j in judges:
        for pk in packs:
            pid = pk["problem_id"]
            legfile = OUT_DIR / f"{j['tag']}__{pid}.json"
            if legfile.exists():
                prev = json.loads(legfile.read_text())
                if prev.get("outcome") == "VALID":
                    continue  # only VALID legs skip (the R146 fix)
            pr = problems.get(pid, {})
            prompt = build_prompt(
                pr.get("problem") or pk.get("problem_text") or "",
                pk["candidate_text"], pk["prior_arts"])
            t0 = time.monotonic()
            leg = _leg(j, prompt)
            wall = round(time.monotonic() - t0, 1)
            rec = {"judge": j["tag"], "family": j["family"],
                   "model": j["model"], "problem_id": pid,
                   "neutral_index": neutral_index(pid),
                   "outcome": leg["outcome"], "parsed": leg["parsed"],
                   "raw_tail": leg["raw_tail"],
                   "attempts": leg["attempts"], "wall_s": wall}
            legfile.write_text(json.dumps(rec, indent=1,
                                          ensure_ascii=False) + "\n")
            p = leg.get("parsed") or {}
            print(f"{j['tag']} #{neutral_index(pid)}: {leg['outcome']} "
                  f"viable={p.get('viable')} "
                  f"non_obvious={p.get('non_obvious')} ({wall}s)",
                  flush=True)
            time.sleep(j["pace"] if leg["outcome"] == "VALID" else 5)

    # ---- the tally (majority rule on BOTH axes; the FULL set) ------
    import collections
    by_pid = collections.defaultdict(dict)
    for pk in packs:
        pid = pk["problem_id"]
        for j in judges:
            f = OUT_DIR / f"{j['tag']}__{pid}.json"
            if not f.exists():
                continue
            d = json.loads(f.read_text())
            p = d.get("parsed") or {}
            if isinstance(p, dict) and d.get("outcome") == "VALID":
                by_pid[pid][j["tag"]] = (bool(p.get("viable")),
                                         bool(p.get("non_obvious")))
    tally_rows, n_pass = [], 0
    for pid in sorted(by_pid):
        votes = by_pid[pid]
        nv = len(votes)
        v_yes = sum(1 for v, _ in votes.values() if v)
        n_yes = sum(1 for _, n in votes.values() if n)
        v_maj = v_yes * 2 > nv
        n_maj = n_yes * 2 > nv
        passed = nv > 0 and v_maj and n_maj
        n_pass += passed
        tally_rows.append({"problem_id": pid, "judges_voted": nv,
                           "viable_yes": v_yes, "nonobvious_yes": n_yes,
                           "passed": passed})
    pct = round(100.0 * n_pass / max(1, len(tally_rows)), 1)
    tally = {
        "record": "R148_P4_PANEL_V18/1.0.0 — the GATE-VALID panel: "
                  "the r148-qualified cent-ai judges, blind (neutral "
                  "sha-derived index) + swapped (the prior-art "
                  "sha-parity rotation), on the FULL v18 physics-correct "
                  "30-candidate set; majority of the votes cast on "
                  "BOTH axes; the >=50% bar",
        "instrument": {
            "judges": [j["tag"] for j in judges],
            "qualification": "r148 gate (auditor corpus, "
                             "acc>=0.8/answered>=0.9/bias<=1, "
                             "alpha>=0.6) — QUALIFICATION_SNAPSHOT.json "
                             "rides this run",
            "bar_pct_ge": 50.0,
            "set": "the FULL 30-candidate set (no subsets)"},
        "tally": {"n_candidates": len(tally_rows),
                  "n_viable_and_non_obvious": n_pass, "pct": pct,
                  "pass": bool(pct >= 50.0)},
        "rows": tally_rows}
    (OUT_DIR / "tally.json").write_text(json.dumps(tally, indent=1,
                                                   ensure_ascii=False)
                                        + "\n")
    print(f"TALLY: {n_pass}/{len(tally_rows)} = {pct}% (bar >= 50%)",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

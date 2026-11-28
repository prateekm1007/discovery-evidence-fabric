#!/usr/bin/env python3
"""r190s1_threearm_run.py — DIR 4 (owner merged-and-locked): the
three-arm pool + error-gated selection, TOURNAMENT BYPASSED.

POOL (owner-fixed, NEVER tuned; r191s2 re-lock): departure -> relaxation -> contradiction (plain deleted from the pool per DIR-5: never picked under the fixed order; the baseline arm already covers it)
  (the consultant's 7/8 error-free coverage vs plain alone 1/8).
  ONE draw per arm (3 generator calls; byte-faithful strategy prompts
  imported from scripts/r176_invention_run.py).

BASELINE: the LANDED baseline_final bytes from the byte-authoritative
  gen checkpoints (dominance-by-construction stays in the delivery
  track; the baseline is OUT of the novelty pool; zero extra calls).

SELECTION (owner-fixed):
  1. structural gate first — the shipped deterministic verifier
     (citation patterns + falsification span; imported byte-faithful
     from the r186 instrument);
  2. ONE batched critic call over the surviving candidates (the
     engine's discovery_fabric/engine/error_critic.critic_batched —
     families distinct from the agnes generator);
  3. the FIRST candidate with zero serious flags in the owner's order
     departure -> relaxation -> contradiction; if none clean, the FEWEST flags
     (ties -> the owner's order). The order is a constant, never tuned.

JUDGING: the selected novel candidate goes STRAIGHT to the blind
  two-family panel vs the landed baseline (no tournament gate on the
  novelty metric); order-swapped XY/YX; panel majority, disagreement
  = TIE; AM53 taxonomy in the tally (a plain selection is a
  best-of-N-class win, NOT a genuine invention win; genuine =
  relaxation/departure selection + blind WIN).

TYPED GATE (Art. 3): the run REFUSES (exit 3) until
  eval/r190s1_critic_calibration/summary.json exists with
  bar_met=true — the selection consumes the CALIBRATED critic (owner
  DIR-3 bar; no uncalibrated-critic genuine-count claim).

Usage: python3 scripts/r190s1_threearm_run.py [--only <pid>]
Writes: eval/r190s1_threearm_run/pair_{pid}.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r186s1_ablation_run import (  # noqa: E402  (byte-faithful reuse)
    JUDGES, agnes, blind_prompt, env_keys, judge_leg, verify,
)
from r176_invention_run import strat_prompts  # noqa: E402
from discovery_fabric.engine import error_critic as ec  # noqa: E402

OUT = REPO / "eval" / "r190s1_threearm_run"
OUT.mkdir(exist_ok=True)
CORPUS = REPO / "eval" / "r176_invention_corpus" / "items.jsonl"
CALIB = REPO / "eval" / "r190s1_critic_calibration" / "summary.json"

POOL_ORDER = ("departure", "relaxation", "contradiction")
CRITIC_FAMILY = "hy4-flash-centai"   # the calibrated kept variant's seat


def landed_baseline(pid: str) -> str:
    """The byte-authoritative landed baseline (dominance-by-construction
    for the delivery track; out of the novelty pool)."""
    for d in (REPO / "eval" / "r183_collider_run",
              REPO / "eval" / "r176_invention_run"):
        p = d / f"gen_{pid}.json"
        if p.exists():
            g = json.loads(p.read_text(encoding="utf-8"))
            if g.get("baseline_final"):
                return g["baseline_final"]
    raise FileNotFoundError(f"no landed baseline for {pid}")


def select(cands: dict, flags_by_arm: dict) -> dict:
    """The owner-fixed selection: first zero-serious-flags candidate in
    POOL_ORDER; else fewest flags (ties -> POOL_ORDER). Never tuned."""
    for arm in POOL_ORDER:
        if arm in cands and not flags_by_arm.get(arm):
            return {"arm": arm, "rule": "FIRST_ZERO_FLAGS", "rank": 1}
    ranked = sorted(
        (a for a in POOL_ORDER if a in cands),
        key=lambda a: (len(flags_by_arm.get(a, [])),
                       POOL_ORDER.index(a)))
    if ranked:
        return {"arm": ranked[0], "rule": "FEWEST_FLAGS", "rank": 2}
    return {"arm": None, "rule": "NO_PASSING_CANDIDATE", "rank": 0}


def run_one(prob: dict, keys: dict) -> dict:
    pid = prob["problem_id"]
    t0 = time.time()
    calls = {"draws": 0, "critic": 0}

    # ---- 3 pool draws (byte-faithful strategy prompts) ----
    prompts = strat_prompts(prob)
    pool = {}
    for arm in POOL_ORDER:
        pool[arm] = agnes(prompts[arm], keys, what=f"{pid} {arm}")
        calls["draws"] += 1

    baseline = landed_baseline(pid)

    # ---- 1. the structural gate (the shipped deterministic verifier) ----
    gate = {arm: verify(pool[arm]) for arm in POOL_ORDER}
    passing = [a for a in POOL_ORDER if gate[a]["ok"]]

    # ---- 2. ONE batched critic call over the survivors ----
    flags_by_arm = {a: [] for a in POOL_ORDER}
    critic_status = "SKIPPED_NO_PASSING_CANDIDATE"
    if passing:
        seat = ec.SEATS[CRITIC_FAMILY]
        try:
            per = ec.critic_batched(
                prob, [pool[a] for a in passing],
                _mk_transport(keys), seat["base"],
                keys[seat["key_env"]], seat["model"],
                seat["max_tokens"])
            for a, fl in zip(passing, per):
                flags_by_arm[a] = fl
            critic_status = "OK"
            calls["critic"] = 1
        except Exception as e:  # noqa: BLE001 typed, never re-roll
            critic_status = f"TRANSPORT_FAILED {type(e).__name__}"

    # ---- 3. the owner-fixed selection ----
    sel = select({a: pool[a] for a in passing}, flags_by_arm)

    # ---- 4. the blind two-family judge vs the landed baseline ----
    votes, judge_meta = {}, []
    if sel["arm"]:
        chosen = pool[sel["arm"]]
        for seat_tag in ("hy4-flash-centai", "qwen3.8-max-xkiro"):
            vals = []
            for order in ("XY", "YX"):
                a, b = ((chosen, baseline) if order == "XY"
                        else (baseline, chosen))
                try:
                    verdict, _raw = judge_leg(
                        seat_tag, blind_prompt(prob, a, b), keys,
                        f"{pid} {seat_tag} {order}")
                except Exception as e:  # noqa: BLE001 typed
                    verdict = "TIE"
                    vals.append(f"TYPED_JUDGE_FAILURE {type(e).__name__}")
                    continue
                vals.append(verdict if order == "XY"
                            else ("X" if verdict == "Y"
                                  else "Y" if verdict == "X" else "TIE"))
            if all(x in ("X", "TIE") for x in vals) and "X" in vals:
                votes[seat_tag] = "WIN"
            elif all(x in ("Y", "TIE") for x in vals) and "Y" in vals:
                votes[seat_tag] = "LOSS"
            else:
                votes[seat_tag] = "TIE"
            judge_meta.append({"seat": seat_tag,
                                "family": JUDGES[seat_tag]["family"],
                                "vote": votes[seat_tag]})
    vs = list(votes.values())
    outcome = vs[0] if vs and vs[0] == vs[1] else "TIE"

    return {
        "problem_id": pid, "status": "JUDGED",
        "pool_arms": list(POOL_ORDER),
        "selected_arm": sel["arm"], "selection_rule": sel["rule"],
        "structural_gate": {a: gate[a]["reason"] for a in POOL_ORDER},
        "critic_flags": {a: flags_by_arm[a] for a in POOL_ORDER},
        "critic_status": critic_status,
        "selected_error_free": (sel["arm"] is not None
                                and not flags_by_arm.get(sel["arm"])),
        "judges": judge_meta, "votes": votes,
        "outcome": outcome,
        "genuine_AM53": (sel["arm"] in ("departure", "relaxation",
                                    "contradiction")
                         and outcome == "WIN"),
        "am53_class": ("plain_best_of_n" if sel["arm"] == "plain"
                       else "novel_strategy" if sel["arm"]
                       else "none_selected"),
        "calls": calls,
        "llm_calls_total": calls["draws"] + calls["critic"],
        "wall_s": round(time.time() - t0, 1),
    }


def _mk_transport(keys: dict):
    import urllib.request

    def transport(base_url, key, model, prompt, max_tokens):
        body = {"model": model, "max_tokens": max_tokens,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}]}
        req = urllib.request.Request(
            base_url, data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            doc = json.loads(r.read().decode())
        return ((doc.get("choices") or [{}])[0]
                .get("message", {}).get("content") or "")
    return transport


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()

    # TYPED GATE: the selection consumes the CALIBRATED critic
    if not CALIB.exists():
        print("TYPED REFUSAL (Art. 3): the calibrated critic does not "
              "exist yet (eval/r190s1_critic_calibration/summary.json "
              "absent) — the label set's per-text labels are still "
              "MISSING_OWNER_INPUT, so no calibration claim and no "
              "calibrated-critic selection run is valid (owner DIR-3/4 "
              "rule).", flush=True)
        return 3
    calib = json.loads(CALIB.read_text(encoding="utf-8"))
    if not calib.get("bar_met"):
        print("TYPED REFUSAL (Art. 3): the calibration bar was not met "
              f"(best variant {calib.get('best_by_f1')}); the owner "
              "decides the fallback before any selection run.", flush=True)
        return 3

    keys = env_keys()
    rows = [json.loads(l) for l in
            CORPUS.read_text().splitlines() if l.strip()]
    # the 12 landed DEV items (the bytes with judged pair evidence)
    landed = sorted(p.stem.replace("pair_", "") for p in
                    (REPO / "eval" / "r183_collider_run").glob("pair_*.json"))
    rows = [r for r in rows if r["problem_id"] in landed]
    if args.only:
        rows = [r for r in rows if r["problem_id"] == args.only]
    print(f"R190S1 three-arm run: {len(rows)} landed DEV items, "
          f"pool={POOL_ORDER} (owner-fixed order, never tuned)",
          flush=True)
    for i, prob in enumerate(rows, 1):
        pid = prob["problem_id"]
        outp = OUT / f"pair_{pid}.json"
        if outp.exists():
            print(f"=== {pid} ({i}/{len(rows)}): resumed", flush=True)
            continue
        row = run_one(prob, keys)
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        print(f"=== {pid} ({i}/{len(rows)}): selected="
              f"{row['selected_arm']} ({row['selection_rule']}) "
              f"outcome={row['outcome']} genuine={row['genuine_AM53']} "
              f"error_free={row['selected_error_free']} "
              f"{row['wall_s']}s", flush=True)
    print("three-arm run complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r133_panel_driver — the THIN driver for the P4 panel round-2
(claim c-0212, prereg eval/r133_panel_prereg.json — typed before any
panel call; pushed 39c29c0d5).

The R132-F1 fix: ALL judging/tally logic lives in the engine
(discovery_fabric/engine/blind_panel.py build_pair_prompt +
parse_pair_rating; panel_agreement.py rcal_qualification +
swap_robust_panel). This driver does transport, pacing, and record
writing ONLY.

Levers (R133): (a) swap-robust vote — the r9 parity-drawn order is
the voting leg, the mirror is a consistency check; (b) forced-choice
prefer (no TIE); (c) larger rungs (Qwen3-235B, DeepSeek-V3.2,
Llama-4-Maverick paced, Llama-3.3-70B margin).

Usage: python3 -I scripts/r133_panel_driver.py [pace_s]
"""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from discovery_fabric.engine.route_adapter import hf_router_chat  # noqa: E402
from discovery_fabric.engine.blind_panel import (  # noqa: E402
    build_pair_prompt, parse_pair_rating)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "eval" / "r133_panel"
OUT.mkdir(exist_ok=True)

JUDGES = [
    {"model": "Qwen/Qwen3-235B-A22B-Instruct-2507", "family": "qwen",
     "tag": "qwen235b", "pace": 20},
    {"model": "deepseek-ai/DeepSeek-V3.2", "family": "deepseek",
     "tag": "dsv32", "pace": 20},
    {"model": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
     "family": "meta-llama", "tag": "llama4mav", "pace": 90},
    {"model": "meta-llama/Llama-3.3-70B-Instruct", "family": "meta-llama",
     "tag": "llama33", "pace": 20},
]
MAX_TOKENS = 4000
TIMEOUT_S = 300.0
SYSTEM = ("You are a strict blind rubric judge. English only. "
          "Respond with ONLY the JSON object.")


def blind_order(pid: str) -> str:
    """The committed r9 convention: sha256(pid::pair) parity decides
    which arm is slot A (even -> a1 first)."""
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "a1_first" if int(h, 16) % 2 == 0 else "base_first"


def _load_r5():
    import subprocess
    r5 = json.loads(subprocess.run(
        ["git", "show",
         "009ce91a8:eval/auditor_judgments_r11_r5.json"],
        capture_output=True, text=True, check=True).stdout)
    labels, probs = {}, {}
    for p in r5["pairs"]:
        labels[p["problem_id"]] = p.get("overall_preference")
    for src in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / src).read_text())["problems"]:
            probs.setdefault(p["problem_id"], p)
    def arms(pid):
        a1 = json.loads((REPO / "eval/pairs/r11_a1_r3" / f"{pid}.json")
                        .read_text()).get("a1_answer")
        base = ""
        for d in ("eval/pairs/dev12_fresh", "eval/baselines_curated"):
            f = REPO / d / f"{pid}.json"
            if f.exists():
                base = (json.loads(f.read_text()).get("baseline_answer")
                        or json.loads(f.read_text()).get("standard_answer")
                        or "")
                if str(base).strip():
                    break
        return str(a1 or "")[:6000], str(base or "")[:6000]
    out = []
    for pid, lab in sorted(labels.items()):
        a1, base = arms(pid)
        if a1.strip() and base.strip():
            # forced-choice labels: the auditor's labels are never-tie
            lab_f = lab if lab in ("a1", "baseline") else None
            if lab_f is None:
                print(f"[skip] {pid}: label {lab!r} not forced-choice")
                continue
            out.append({"pid": pid, "prob": probs.get(pid, {}),
                        "a1": a1, "base": base, "label": lab_f})
    return out


def _leg(j, pid, prompt):
    attempts, outcome, parsed = [], "TRANSPORT_FAILED", None
    for attempt in (1, 2):
        t0 = time.monotonic()
        try:
            r = hf_router_chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": prompt}],
                model=j["model"], max_tokens=MAX_TOKENS,
                timeout_s=TIMEOUT_S)
            raw, err = r.get("content"), r.get("error")
        except Exception as e:  # noqa: BLE001
            raw, err = None, f"{type(e).__name__}: {str(e)[:160]}"
        lat = round(time.monotonic() - t0, 1)
        attempts.append({"attempt": attempt, "latency_s": lat,
                         "error": err})
        if raw:
            try:
                parsed = parse_pair_rating(raw)  # the ENGINE parse
                outcome = "VALID"
                break
            except ValueError as e:
                outcome = "PARSE_FAILED"
                if attempt == 1:
                    prompt = (prompt + "\n\nYour previous output "
                              "violated the contract (" + str(e)[:120]
                              + "). Respond with ONLY the JSON object "
                              "with the eight axis keys and "
                              '"prefer": "A" or "B". No other text.')
                    time.sleep(3)
                    continue
        elif err and "429" in str(err):
            outcome = "RATE_LIMITED"
            break
    return {"outcome": outcome, "parsed": parsed, "attempts": attempts}


def main() -> int:
    pairs = _load_r5()
    print(f"R-CAL round-2: {len(JUDGES)} judges x {len(pairs)} pairs "
          f"x 2 orders; engine-routed (blind_panel pair contract)",
          flush=True)
    for j in JUDGES:
        pace = j["pace"]
        for p in pairs:
            order = blind_order(p["pid"])
            for tag, a_text, b_text in (
                    ("det", p["a1"], p["base"]) if order == "a1_first"
                    else ("det", p["base"], p["a1"]),
                    ("mir", p["base"], p["a1"]) if order == "a1_first"
                    else ("mir", p["a1"], p["base"])):
                f = OUT / f"{j['tag']}__{p['pid']}__{tag}.json"
                if f.exists():  # byte-resume
                    continue
                prompt = build_pair_prompt(  # the ENGINE prompt
                    p["prob"], a_text, b_text)
                r = _leg(j, p["pid"], prompt)
                rec = {
                    "judge_family": j["family"], "model": j["model"],
                    "problem_id": p["pid"], "order": order, "pass": tag,
                    "a_is": ("a1" if (tag == "det") ==
                             (order == "a1_first") else "baseline"),
                    "outcome": r["outcome"], "parsed": r["parsed"],
                    "attempts": r["attempts"],
                    "auditor_label": p["label"],
                    "engine_contract": "blind_panel.build_pair_prompt"
                                       "+parse_pair_rating (R132-F1)",
                }
                f.write_text(json.dumps(rec, indent=1) + "\n")
                print(f"  {j['tag']}/{p['pid'][:34]}/{tag} "
                      f"{r['outcome']} "
                      f"{r['attempts'][-1]['latency_s']}s", flush=True)
                time.sleep(pace)
    print("R-CAL round-2 legs complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

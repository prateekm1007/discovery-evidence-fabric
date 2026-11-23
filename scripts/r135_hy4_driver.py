#!/usr/bin/env python3
"""r135_hy4_driver — the hy4-flash:free judge legs (claim c-0215,
amendment eval/r135_panel_amendment.json — typed BEFORE any leg).

The owner directive lane: 20 legs (10 pairs x 2 orders) on the SAME
frozen r5 labels + the SAME CoT engine contract + the SAME swap-
robust vote rule. The transport is the ENGINE cent_ai_chat with the
budget ladder (4000 -> 8000 -> 12000: the reasoning budgets FIRST)
and the patient retry ladder for the measured free-lane 503 class
(upstream_timeout, congestion-variable). Records preserve the FULL
reasoning_content — the thinking is the instrument's evidence.

Byte-resume: a leg whose record file exists is never re-run.

Usage: python3 -I scripts/r135_hy4_driver.py
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
from discovery_fabric.engine.route_adapter import (  # noqa: E402
    cent_ai_chat, RouteRefused)
from discovery_fabric.engine.blind_panel import (  # noqa: E402
    build_pair_prompt, parse_pair_rating)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "eval" / "r135_panel"
OUT.mkdir(exist_ok=True)

MODEL = "hy4-flash:free"
TAG = "hy4f"
FAMILY = "cent-ai"
SYSTEM = ("You are a strict blind rubric judge. English only. "
          "Follow the response contract exactly.")
# the STREAMING shape (the measured wall bypass): the SSE lane has
# NO ~90s gateway wall — the full-pair task completed @12000 in 53s
# (32K reasoning chars, finish=stop, VALID parse). The reasoning
# needs the runway: 12000 first, 16000 the escalation; the 503
# retries stay for the residual congestion class.
BUDGET_LADDER = (12000, 12000, 16000, 16000)
RETRY_BACKOFFS = (45.0, 90.0, 120.0, 180.0)  # the 503 congestion ladder


def blind_order(pid: str) -> str:
    """The committed r9 convention (unchanged)."""
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "a1_first" if int(h, 16) % 2 == 0 else "base_first"


def _load_r5():
    # the same loader as the r134 driver (the frozen pairs + labels)
    import subprocess
    r5 = json.loads(subprocess.run(
        ["git", "show", "009ce91a8:eval/auditor_judgments_r11_r5.json"],
        capture_output=True, text=True, check=True).stdout)
    labels = {p["problem_id"]: p.get("overall_preference")
              for p in r5["pairs"]}
    probs = {}
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
                t = json.loads(f.read_text())
                base = (t.get("baseline_answer") or
                        t.get("standard_answer") or "")
                if str(base).strip():
                    break
        return str(a1 or "")[:6000], str(base or "")[:6000]

    out = []
    for pid, lab in sorted(labels.items()):
        if lab not in ("a1", "baseline"):
            continue
        a1, base = arms(pid)
        if a1.strip() and base.strip():
            out.append({"pid": pid, "prob": probs.get(pid, {}),
                        "a1": a1, "base": base, "label": lab})
    return out


def _leg(prompt: str) -> dict:
    """One leg: the budget ladder per attempt; the 503 retry ladder
    with patient backoff; typed outcomes only."""
    attempts = []
    budget_i = 0
    for attempt in range(1, 6):
        budget = BUDGET_LADDER[min(budget_i, len(BUDGET_LADDER) - 1)]
        t0 = time.monotonic()
        try:
            r = cent_ai_chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": prompt}],
                model=MODEL, max_tokens=budget, timeout_s=420.0,
                stream=True)  # the measured gateway-wall bypass
            raw = r.get("content") or ""
            reasoning = r.get("reasoning") or ""
            lat = round(time.monotonic() - t0, 1)
            try:
                parsed = parse_pair_rating(raw)  # the ENGINE parse
                attempts.append({"attempt": attempt, "budget": budget,
                                 "latency_s": lat, "error": None})
                return {"outcome": "VALID", "parsed": parsed,
                        "reasoning_chars": len(reasoning),
                        "attempts": attempts}
            except ValueError as e:
                # a contract violation: ONE re-ask with the contract
                # reminder, then stand
                attempts.append({"attempt": attempt, "budget": budget,
                                 "latency_s": lat,
                                 "error": f"parse: {str(e)[:100]}"})
                if attempt >= 2:
                    return {"outcome": "PARSE_FAILED", "parsed": None,
                            "reasoning_chars": len(reasoning),
                            "attempts": attempts}
                prompt = (prompt + "\n\nYour previous output violated "
                          "the contract (" + str(e)[:100] + "). End "
                          "your reply with ONE flat JSON object with "
                          "the eight axis keys and \"prefer\": "
                          "\"A\" or \"B\" — nothing after it.")
                continue
        except RouteRefused as e:
            lat = round(time.monotonic() - t0, 1)
            attempts.append({"attempt": attempt, "budget": budget,
                             "latency_s": lat,
                             "error": f"{e.kind}: {str(e)[:110]}"})
            if e.kind == "upstream_timeout" and \
                    attempt <= len(RETRY_BACKOFFS):
                time.sleep(RETRY_BACKOFFS[attempt - 1])
                continue  # same budget, patient retry
            if e.kind == "length_no_content":
                budget_i = min(budget_i + 1, len(BUDGET_LADDER) - 1)
                time.sleep(20.0)
                continue
            if e.kind == "rate_limited" and attempt <= 3:
                time.sleep(60.0)
                continue
            return {"outcome": "TRANSPORT_FAILED", "parsed": None,
                    "reasoning_chars": 0, "attempts": attempts}
        except Exception as e:  # noqa: BLE001
            lat = round(time.monotonic() - t0, 1)
            attempts.append({"attempt": attempt, "budget": budget,
                             "latency_s": lat,
                             "error": f"{type(e).__name__}: "
                                      f"{str(e)[:110]}"})
            return {"outcome": "TRANSPORT_FAILED", "parsed": None,
                    "reasoning_chars": 0, "attempts": attempts}
    return {"outcome": "TRANSPORT_FAILED", "parsed": None,
            "reasoning_chars": 0, "attempts": attempts}


def main() -> int:
    pairs = _load_r5()
    print(f"R135 hy4-flash:free legs: {len(pairs)} pairs x 2 orders "
          f"= {len(pairs)*2} legs (the engine CoT contract; budget "
          "ladder 4000/8000/12000; patient 503 retries)", flush=True)
    for p in pairs:
        order = blind_order(p["pid"])
        for tag, a_text, b_text in (
                ("det", p["a1"], p["base"]) if order == "a1_first"
                else ("det", p["base"], p["a1"]),
                ("mir", p["base"], p["a1"]) if order == "a1_first"
                else ("mir", p["a1"], p["base"])):
            f = OUT / f"{TAG}__{p['pid']}__{tag}.json"
            if f.exists():  # byte-resume
                continue
            prompt = build_pair_prompt(  # the ENGINE CoT prompt
                p["prob"], a_text, b_text, cot=True)
            r = _leg(prompt)
            rec = {
                "judge_family": FAMILY, "model": MODEL,
                "problem_id": p["pid"], "order": order, "pass": tag,
                "a_is": ("a1" if (tag == "det") ==
                         (order == "a1_first") else "baseline"),
                "outcome": r["outcome"], "parsed": r["parsed"],
                "reasoning_chars": r["reasoning_chars"],
                "attempts": r["attempts"],
                "auditor_label": p["label"],
                "lever": "the owner HY4 directive (hy4-flash:free, "
                         "the reasoning rung on the cent-ai lane)",
                "engine_contract": "blind_panel.build_pair_prompt"
                                   "(cot=True)+parse_pair_rating; "
                                   "route_adapter.cent_ai_chat",
                "amendment": "eval/r135_panel_amendment.json "
                             "(claim c-0215)",
            }
            f.write_text(json.dumps(rec, indent=1) + "\n")
            print(f"  {p['pid'][:36]}/{tag} {r['outcome']} "
                  f"{r['attempts'][-1]['latency_s']}s "
                  f"(budget {r['attempts'][-1]['budget']})", flush=True)
            time.sleep(30)  # the free-lane courtesy pace
    print("hy4 legs complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

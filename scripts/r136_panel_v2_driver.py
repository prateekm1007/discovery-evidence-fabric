#!/usr/bin/env python3
"""r136_panel_v2_driver — the PANEL-V2 run (claim c-0216, prereg
eval/r136_panel_v2_prereg.json — typed + pushed at 2d1170f06 BEFORE
any leg).

The v2 arm: build_pair_prompt(cot=True, show_constraint=True) — the
judge is shown the problem's constraint (the verifier's finding:
the C-axis was scored blind). v1 stays the baseline arm (its
R134/R135 tallies stand byte-untouched).

Judges: 6 (dsr1, qw32b, qwen235b, dsv32, llama4mav on the HF
router — STREAMED, the 504-class fix; hy4f on cent-ai — the R135
SSE transport). 10 pairs x 2 orders = 120 legs; byte-resume.

Usage: python3 -I scripts/r136_panel_v2_driver.py [tag ...]
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
    hf_router_chat, cent_ai_chat, RouteRefused)
from discovery_fabric.engine.blind_panel import (  # noqa: E402
    build_pair_prompt, parse_pair_rating)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "eval" / "r136_panel_v2"
OUT.mkdir(exist_ok=True)

SYSTEM = ("You are a strict blind rubric judge. English only. "
          "Follow the response contract exactly.")

JUDGES = {
    "dsr1": {"model": "deepseek-ai/DeepSeek-R1",
             "family": "deepseek", "transport": "hf_stream",
             "pace": 20, "max_tokens": 8000, "timeout_s": 420.0},
    "qw32b": {"model": "Qwen/Qwen3-32B",
              "family": "qwen", "transport": "hf_stream",
              "pace": 20, "max_tokens": 8000, "timeout_s": 420.0},
    "qwen235b": {"model": "Qwen/Qwen3-235B-A22B-Instruct-2507",
                 "family": "qwen", "transport": "hf_stream",
                 "pace": 20, "max_tokens": 4000, "timeout_s": 300.0},
    "dsv32": {"model": "deepseek-ai/DeepSeek-V3.2",
              "family": "deepseek", "transport": "hf_stream",
              "pace": 20, "max_tokens": 4000, "timeout_s": 300.0},
    "llama4mav": {"model": "meta-llama/"
                           "Llama-4-Maverick-17B-128E-Instruct",
                  "family": "meta-llama", "transport": "hf_stream",
                  "pace": 60, "max_tokens": 4000, "timeout_s": 300.0},
    "hy4f": {"model": "hy4-flash:free",
             "family": "cent-ai", "transport": "cent_stream",
             "pace": 30, "max_tokens": 12000, "timeout_s": 420.0},
}


def blind_order(pid: str) -> str:
    """The committed r9 convention (unchanged)."""
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "a1_first" if int(h, 16) % 2 == 0 else "base_first"


def _load_r5():
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


def _call(judge, prompt):
    """One streamed call on the judge's transport; the ENGINE parse
    decides VALID/failed; ONE re-ask on a contract violation."""
    last_err = None
    for attempt in (1, 2):
        t0 = time.monotonic()
        try:
            if judge["transport"] == "hf_stream":
                r = hf_router_chat(
                    [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
                    model=judge["model"],
                    max_tokens=judge["max_tokens"],
                    timeout_s=judge["timeout_s"], stream=True)
                raw = r.get("content") or ""
            else:  # cent_stream
                r = cent_ai_chat(
                    [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
                    model=judge["model"],
                    max_tokens=judge["max_tokens"],
                    timeout_s=judge["timeout_s"], stream=True)
                raw = r.get("content") or ""
            lat = round(time.monotonic() - t0, 1)
            try:
                parsed = parse_pair_rating(raw)
                return "VALID", parsed, [
                    {"attempt": attempt, "latency_s": lat,
                     "error": None}]
            except ValueError as e:
                last_err = f"parse: {str(e)[:100]}"
                if attempt == 1:
                    prompt = (prompt + "\n\nYour previous output "
                              "violated the contract (" + str(e)[:100]
                              + "). End your reply with ONE flat "
                              "JSON object with the eight axis keys "
                              'and "prefer": "A" or "B" — nothing '
                              "after it.")
                    time.sleep(3)
                    continue
                return "PARSE_FAILED", None, [
                    {"attempt": attempt, "latency_s": lat,
                     "error": last_err}]
        except RouteRefused as e:
            last_err = f"{e.kind}: {str(e)[:110]}"
            lat = round(time.monotonic() - t0, 1)
            if e.kind in ("upstream_timeout", "rate_limited",
                          "transport", "http_504") and attempt == 1:
                time.sleep(45)  # one patient retry on transport
                continue
            return "TRANSPORT_FAILED", None, [
                {"attempt": attempt, "latency_s": lat,
                 "error": last_err}]
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {str(e)[:110]}"
            return "TRANSPORT_FAILED", None, [
                {"attempt": attempt,
                 "latency_s": round(time.monotonic() - t0, 1),
                 "error": last_err}]
    return "TRANSPORT_FAILED", None, [{"attempt": 2,
                                       "latency_s": 0, "error": last_err}]


def main() -> int:
    only = set(sys.argv[1:]) or set(JUDGES)
    pairs = _load_r5()
    total = sum(1 for t in only) * len(pairs) * 2
    print(f"PANEL-V2 (the constraint arm): judges {sorted(only)} x "
          f"{len(pairs)} pairs x 2 orders; streamed transports; "
          "byte-resume", flush=True)
    for tag, j in JUDGES.items():
        if tag not in only:
            continue
        for p in pairs:
            order = blind_order(p["pid"])
            for pass_, a_text, b_text in (
                    ("det", p["a1"], p["base"]) if order == "a1_first"
                    else ("det", p["base"], p["a1"]),
                    ("mir", p["base"], p["a1"]) if order == "a1_first"
                    else ("mir", p["a1"], p["base"])):
                f = OUT / f"{tag}__{p['pid']}__{pass_}.json"
                if f.exists():  # byte-resume
                    continue
                prompt = build_pair_prompt(  # the V2 arm
                    p["prob"], a_text, b_text, cot=True,
                    show_constraint=True)
                outcome, parsed, attempts = _call(j, prompt)
                rec = {
                    "judge_family": j["family"],
                    "model": j["model"], "transport": j["transport"],
                    "problem_id": p["pid"], "order": order,
                    "pass": pass_,
                    "a_is": ("a1" if (pass_ == "det") ==
                             (order == "a1_first") else "baseline"),
                    "outcome": outcome, "parsed": parsed,
                    "attempts": attempts,
                    "auditor_label": p["label"],
                    "arm": "PANEL-V2 (the constraint line; the R136 "
                           "prereg 2d1170f06)",
                    "engine_contract":
                        "blind_panel.build_pair_prompt(cot=True, "
                        "show_constraint=True)+parse_pair_rating; "
                        "streamed transports",
                }
                f.write_text(json.dumps(rec, indent=1) + "\n")
                print(f"  {tag}/{p['pid'][:32]}/{pass_} {outcome} "
                      f"{attempts[-1]['latency_s']}s", flush=True)
                time.sleep(j["pace"])
    print("v2 legs complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

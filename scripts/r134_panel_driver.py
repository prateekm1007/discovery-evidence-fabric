#!/usr/bin/env python3
"""r134_panel_driver — the THIN driver for the P4 panel round-3
(claim c-0213, prereg eval/r134_panel_prereg.json — typed before any
panel call; pushed be4eb8794).

The two new levers: (a) the CoT comparative judge prompt
(build_pair_prompt(cot=True)); (b) the reasoning rungs (DeepSeek-R1,
Qwen3-32B — QwQ-32B is not served by any router provider, typed in
the prereg). Engine-routed per R132-F1: the driver is transport +
pacing + record writing ONLY.

Usage: python3 -I scripts/r134_panel_driver.py
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
OUT = REPO / "eval" / "r134_panel"
OUT.mkdir(exist_ok=True)

# the prereg's judge table (tags paces + budgets frozen there)
JUDGES = [
    {"model": "deepseek-ai/DeepSeek-R1", "family": "deepseek",
     "tag": "dsr1", "pace": 20, "max_tokens": 8000, "timeout_s": 420.0},
    {"model": "Qwen/Qwen3-32B", "family": "qwen",
     "tag": "qw32b", "pace": 20, "max_tokens": 8000, "timeout_s": 420.0},
    {"model": "Qwen/Qwen3-235B-A22B-Instruct-2507", "family": "qwen",
     "tag": "qwen235b", "pace": 20, "max_tokens": 4000, "timeout_s": 300.0},
    {"model": "deepseek-ai/DeepSeek-V3.2", "family": "deepseek",
     "tag": "dsv32", "pace": 20, "max_tokens": 4000, "timeout_s": 300.0},
    {"model": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
     "family": "meta-llama", "tag": "llama4mav", "pace": 90,
     "max_tokens": 4000, "timeout_s": 300.0},
]
SYSTEM = ("You are a strict blind rubric judge. English only. "
          "Follow the response contract exactly.")


def blind_order(pid: str) -> str:
    """The committed r9 convention (unchanged): sha256(pid::pair)
    parity decides which arm is slot A."""
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "a1_first" if int(h, 16) % 2 == 0 else "base_first"


def _load_r5():
    import subprocess
    r5 = json.loads(subprocess.run(
        ["git", "show", "009ce91a8:eval/auditor_judgments_r11_r5.json"],
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
                t = json.loads(f.read_text())
                base = (t.get("baseline_answer") or
                        t.get("standard_answer") or "")
                if str(base).strip():
                    break
        return str(a1 or "")[:6000], str(base or "")[:6000]

    out = []
    for pid, lab in sorted(labels.items()):
        if lab not in ("a1", "baseline"):
            continue  # forced-choice labels only
        a1, base = arms(pid)
        if a1.strip() and base.strip():
            out.append({"pid": pid, "prob": probs.get(pid, {}),
                        "a1": a1, "base": base, "label": lab})
    return out


def _leg(j, prompt, max_tokens, timeout_s):
    attempts, outcome, parsed = [], "TRANSPORT_FAILED", None
    for attempt in (1, 2):
        t0 = time.monotonic()
        try:
            r = hf_router_chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": prompt}],
                model=j["model"], max_tokens=max_tokens,
                timeout_s=timeout_s)
            raw, err = r.get("content"), r.get("error")
            raw = (raw or "")
            # strip reasoning-model <think> wrappers if the router
            # passes them through (content-only records keep the
            # thinking text; the ENGINE parser takes the last object)
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
                              + "). End your reply with ONE flat JSON "
                              "object with the eight axis keys and "
                              '"prefer": "A" or "B" — nothing after '
                              "it.")
                    time.sleep(3)
                    continue
        elif err and "429" in str(err):
            outcome = "RATE_LIMITED"
            break
    return {"outcome": outcome, "parsed": parsed, "attempts": attempts}


def main() -> int:
    pairs = _load_r5()
    print(f"R-CAL round-3 (CoT): {len(JUDGES)} judges x {len(pairs)} "
          f"pairs x 2 orders = {len(JUDGES)*len(pairs)*2} legs; "
          "engine-routed (blind_panel CoT pair contract)", flush=True)
    for j in JUDGES:
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
                prompt = build_pair_prompt(  # the ENGINE CoT prompt
                    p["prob"], a_text, b_text, cot=True)
                r = _leg(j, prompt, j["max_tokens"], j["timeout_s"])
                rec = {
                    "judge_family": j["family"], "model": j["model"],
                    "problem_id": p["pid"], "order": order, "pass": tag,
                    "a_is": ("a1" if (tag == "det") ==
                             (order == "a1_first") else "baseline"),
                    "outcome": r["outcome"], "parsed": r["parsed"],
                    "attempts": r["attempts"],
                    "auditor_label": p["label"],
                    "lever": "CoT comparative prompt (R134 lever a) "
                             "+ the rung per the prereg",
                    "engine_contract": "blind_panel.build_pair_prompt"
                                       "(cot=True)+parse_pair_rating",
                }
                f.write_text(json.dumps(rec, indent=1) + "\n")
                print(f"  {j['tag']}/{p['pid'][:34]}/{tag} "
                      f"{r['outcome']} "
                      f"{r['attempts'][-1]['latency_s']}s", flush=True)
                time.sleep(j["pace"])
    print("R-CAL round-3 legs complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

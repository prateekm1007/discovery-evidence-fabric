#!/usr/bin/env python3
"""r135_hy4_slowclock — the patient lane for the hy4-flash:free legs
(claim c-0215): ONE 4000-budget attempt per ~4 minutes (the free
lane's congestion clears in windows; the early-session evidence:
identical full-pair payloads succeeded at 28-57s when the lane was
clear). Byte-resume; a leg already recorded is never re-run; the
driver exits when all 20 legs have records. Legs that never land
type TRANSPORT_FAILED honestly in the final tally."""
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
import r135_hy4_driver as D  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "eval" / "r135_panel"
OUT.mkdir(exist_ok=True)
PERIOD = 240.0  # one attempt per 4 minutes


def main() -> int:
    pairs = D._load_r5()
    legs = []
    for p in pairs:
        order = D.blind_order(p["pid"])
        for tag, a_text, b_text in (
                ("det", p["a1"], p["base"]) if order == "a1_first"
                else ("det", p["base"], p["a1"]),
                ("mir", p["base"], p["a1"]) if order == "a1_first"
                else ("mir", p["a1"], p["base"])):
            legs.append((p, order, tag, a_text, b_text))
    print(f"slow-clock: {len(legs)} legs; one 4000-budget attempt "
          f"per {PERIOD:.0f}s", flush=True)
    while True:
        pending = [(p, o, t, a, b) for (p, o, t, a, b) in legs
                   if not (OUT / f"hy4f__{p['pid']}__{t}.json").exists()]
        if not pending:
            print("all legs have records", flush=True)
            return 0
        p, order, tag, a_text, b_text = pending[0]
        f = OUT / f"hy4f__{p['pid']}__{tag}.json"
        prompt = build_pair_prompt(p["prob"], a_text, b_text, cot=True)
        t0 = time.monotonic()
        outcome, parsed, rchars, err = "TRANSPORT_FAILED", None, 0, None
        try:
            r = cent_ai_chat(
                [{"role": "system", "content": D.SYSTEM},
                 {"role": "user", "content": prompt}],
                model=D.MODEL, max_tokens=4000, timeout_s=420.0)
            raw, reasoning = r.get("content") or "", r.get("reasoning") or ""
            try:
                parsed = parse_pair_rating(raw)
                outcome = "VALID"
                rchars = len(reasoning)
            except ValueError as e:
                outcome, err = "PARSE_FAILED", str(e)[:110]
                rchars = len(reasoning)
        except RouteRefused as e:
            err = f"{e.kind}: {str(e)[:110]}"
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:110]}"
        lat = round(time.monotonic() - t0, 1)
        rec = {
            "judge_family": D.FAMILY, "model": D.MODEL,
            "problem_id": p["pid"], "order": order, "pass": tag,
            "a_is": ("a1" if (tag == "det") ==
                     (order == "a1_first") else "baseline"),
            "outcome": outcome, "parsed": parsed,
            "reasoning_chars": rchars, "attempts": [
                {"attempt": 1, "budget": 4000, "latency_s": lat,
                 "error": err}],
            "auditor_label": p["label"],
            "lever": "the owner HY4 directive (hy4-flash:free); the "
                     "slow-clock patient lane (one attempt / 4 min — "
                     "the free lane's congestion windows)",
            "engine_contract": "blind_panel.build_pair_prompt"
                               "(cot=True)+parse_pair_rating; "
                               "route_adapter.cent_ai_chat",
            "amendment": "eval/r135_panel_amendment.json (claim c-0215)",
        }
        f.write_text(__import__("json").dumps(rec, indent=1) + "\n")
        print(f"  {p['pid'][:36]}/{tag} {outcome} {lat}s "
              f"({len(pending)-1} pending)", flush=True)
        time.sleep(max(0.0, PERIOD - (time.monotonic() - t0)))


if __name__ == "__main__":
    raise SystemExit(main())

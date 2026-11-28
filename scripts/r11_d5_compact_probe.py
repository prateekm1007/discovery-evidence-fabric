#!/usr/bin/env python3
"""r11_d5_compact_probe.py — AM3 D5: mercury-3 returns EMPTY on long
prompts (the R3 panel failed 6/6 JUDGE_EMPTY_OUTPUT on full-length
prompts; re-measured here at 7786 chars -> empty in 1.2 s). This probe
finds the largest prompt length mercury-3 reliably answers, using
graded sizes of a REAL judge prompt, so the D4/D5 runs use compact
structured prompts with MEASURED headroom (never guessed)."""
import json
import sys
import time
sys.path.insert(0, ".")
sys.path.insert(0, "scripts")
from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from eval.run import _rubric_prompt, _transport_call  # noqa: E402

probs = {p["problem_id"]: p for p in json.load(
    open("eval/problems_dev12.json"))["problems"]}
pid = "bench-p02-leadacid-grid-corrosion"
base = json.load(open(f"eval/pairs/dev12_fresh/{pid}.json"))[
    "baseline_answer"]
a1 = json.load(open(f"eval/pairs/r11_a1_r3/{pid}.json"))["a1_answer"]
full = _rubric_prompt(probs[pid], a1, base, None)

sizes = [(700, "micro"), (1600, "small"), (3000, "mid"), (5000, "large"),
         (7786, "full")]
for target, name in sizes:
    # head-truncate keeps the contract tail? no — the CONTRACT is at
    # the end; truncate the MIDDLE evidence instead: keep head+tail
    if target >= len(full):
        prompt = full
    else:
        head = full[: int(target * 0.62)]
        tail = full[-int(target * 0.30):]
        prompt = head + "\n[...evidence truncated for length...]\n" + tail
    t0 = time.time()
    res = _transport_call("inception", "mercury-3", prompt,
                          "You are a strict blind rubric judge. English "
                          "only. Respond with ONLY the JSON object.",
                          max_tokens=400)
    out = str(res.get("content") or "")
    print(f"{name:>6} target={target:>5} actual={len(prompt):>5} "
          f"status={res.get('status')} chars_out={len(out)} "
          f"({time.time()-t0:.1f}s) head={out[:60]!r}")

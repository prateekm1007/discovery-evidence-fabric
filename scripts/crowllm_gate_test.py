#!/usr/bin/env python3
"""crowllm gate test: can deepseek-v4-flash:free serve a REAL
full-length judge prompt through the engine's OWN urllib transport?

The R4 lesson (eval/judge_independent_rerun_r11_r4.json): mercury-3
passed the tiny probe (200-OK 'OK') AND the compact calibration
(0.933) but failed 14/20 REAL full-length judgments
(JUDGE_TRANSPORT_FAILED) — a tiny-probe pass proves NOTHING about
full-length service. This gate measures the real thing BEFORE
crowllm is wired anywhere: same vault loading, same _transport_call,
same _rubric_prompt, same graded sizes as r11_d5_compact_probe.

Typed outcomes only (Art. XXV): PASS = full-length serves a complete
verdict JSON; FAIL = typed class, and crowllm never enters
JUDGE_CANDIDATES this window.
"""
import json
import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "scripts")
from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from eval.run import _rubric_prompt, _transport_call  # noqa: E402

MODEL = "deepseek-v4-flash:free"

probs = {p["problem_id"]: p for p in json.load(
    open("eval/problems_dev12.json"))["problems"]}
pid = "bench-p02-leadacid-grid-corrosion"
base = json.load(open(f"eval/pairs/dev12_fresh/{pid}.json"))[
    "baseline_answer"]
a1 = json.load(open(f"eval/pairs/r11_a1_r3/{pid}.json"))["a1_answer"]
full = _rubric_prompt(probs[pid], a1, base, None)
print(f"full judge prompt: {len(full)} chars")

results = []
sizes = [(1600, "small"), (5000, "large"), (len(full), "full")]
for target, name in sizes:
    if target >= len(full):
        prompt = full
    else:
        head = full[: int(target * 0.62)]
        tail = full[-int(target * 0.30):]
        prompt = head + "\n[...evidence truncated for length...]\n" + tail
    t0 = time.time()
    res = _transport_call("crowllm", MODEL, prompt,
                          "You are a strict blind rubric judge. English "
                          "only. Respond with ONLY the JSON object.",
                          max_tokens=400)
    out = str(res.get("content") or "")
    status = res.get("status")
    has_prefer = '"prefer"' in out or "'prefer'" in out
    has_verdict = has_prefer and ("A1" in out)
    results.append({"size": name, "chars": len(prompt), "status": status,
                    "chars_out": len(out), "verdict_json": has_verdict,
                    "wall_s": round(time.time() - t0, 1),
                    "head": out[:60]})
    print(f"{name:>6} chars={len(prompt):>5} status={status} "
          f"chars_out={len(out):>4} verdict_json={has_verdict} "
          f"({time.time()-t0:.1f}s) head={out[:50]!r}")

full_res = results[-1]
gate = {
    "record": "CROWLLM_GATE/1.0.0",
    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "model": MODEL,
    "transport": "engine _transport_call (urllib, vault-loaded key)",
    "sizes": results,
    "gate": "PASS" if (full_res["status"] == "OK"
                       and full_res["verdict_json"]) else "FAIL",
    "gate_reason": (
        "full-length prompt serves a complete verdict JSON through the "
        "engine's own transport"
        if full_res["status"] == "OK" and full_res["verdict_json"]
        else f"full-length status={full_res['status']} "
             f"chars_out={full_res['chars_out']} "
             f"verdict_json={full_res['verdict_json']}"),
}
out_path = "eval/crowllm_gate_r11.json"
with open(out_path, "w") as f:
    json.dump(gate, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"\ngate: {gate['gate']} — {gate['gate_reason']}")
print(f"typed record -> {out_path}")

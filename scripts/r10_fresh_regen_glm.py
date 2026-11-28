#!/usr/bin/env python3
"""r10_fresh_regen_glm.py — AM10 D2 (F29): re-generate the 18 fresh-pair
A1 answers with the curated GLM generator (zai gateway, zai-org/GLM-5.3),
replacing the F29 confound (raw mistral-14b, bytes never committed).

GROUNDING CONTRACT (AM10 D4, baked into the generation system prompt):
the answer must ground feasibility on the SAME terms as standard
practice — physics/unit sanity on every number, an executable
falsification test (concrete protocol, thresholds, pass/fail), and
explicit standard-practice parity (what standard practice does, what it
costs, why the proposed indicator matches it on cost/hardware/
integration). Novelty is NOT re-ideated here; the generation is fresh
for these pairs (they never had GLM-curated answers).

DURABILITY (AM10 D1): each completed pair is written to
eval/pairs/r11_a1_fresh_r10/<pid>.json IMMEDIATELY — the committing
session picks them up in batches while the run continues. One
regeneration attempt on a critic KILL; typed failures stay typed.
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    check_answer_class_defects)

OUT = REPO / "eval" / "pairs" / "r11_a1_fresh_r10"
GW_PORT = 8787
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

SYS_A1_GROUNDED = (
    "You are a careful engineer. Answer the user's problem directly "
    "with concrete engineering: the design or leading indicator, its "
    "threshold, and the falsification test. Respect every stated "
    "constraint verbatim. English only. Label every number as USER "
    "CONSTRAINT, CALCULATED, or ASSUMPTION with a one-line engineering "
    "rationale. FEASIBILITY GROUNDING (mandatory): (1) every number "
    "must be unit-consistent and physically sane for the stated device; "
    "show the arithmetic where a reader would recompute it. (2) the "
    "falsification test must be executable as written: concrete "
    "protocol, measured quantities, explicit thresholds, pass/fail "
    "criteria, and the kill criterion. (3) state what standard practice "
    "does for this failure, then show the proposed indicator matches "
    "it on the SAME feasibility terms (cost order-of-magnitude, "
    "hardware required, integration effort) — novelty must never ride "
    "on hidden feasibility debt.")


def start_gateway():
    key = "gwkey-" + hashlib.sha256(
        str(time.time()).encode()).hexdigest()[:12]
    env = dict(os.environ, ZAI_GATEWAY_KEY=key)
    p = subprocess.Popen(
        ["node", str(REPO / "scripts" / "zai_gateway.mjs"), str(GW_PORT)],
        stdout=open("/tmp/gw_regen.log", "wb"), stderr=subprocess.STDOUT,
        env=env)
    import urllib.request
    for _ in range(60):
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{GW_PORT}/healthz", timeout=2)
            return p, key
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise RuntimeError("gateway not healthy")


def gen_call(prompt, key, max_tokens=1800):
    import urllib.request
    body = json.dumps({
        "model": "zai-org/GLM-5.3",
        "messages": [{"role": "system", "content": SYS_A1_GROUNDED},
                     {"role": "user", "content": prompt}],
        "max_tokens": max_tokens, "temperature": 0.0}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{GW_PORT}/v1/chat/completions",
        data=body, headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    lat = round(time.time() - t0, 1)
    ch = (d.get("choices") or [{}])[0]
    return str((ch.get("message") or {}).get("content") or ""), lat


def main() -> int:
    b5 = json.loads((REPO / "eval" / "battery30_r11_r5.json").read_text())
    b5_gen = {r["problem_id"]: r for r in b5["results"]
              if r.get("a1_state") == "GENERATED"}
    probs = {}
    for src in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / src).read_text())["problems"]:
            probs.setdefault(p["problem_id"], p)
    inv = json.loads((REPO / "eval" / "r10_stage1_inventory.json")
                     .read_text())
    targets = [m["problem_id"] for m in inv["missing_a1_bytes"]
               if m["problem_id"] in b5_gen]
    print(f"[regen] targets: {len(targets)}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    gw, key = start_gateway()
    ok = 0
    try:
        for pid in targets:
            prob = probs[pid]
            q = (f"DEVICE: {prob.get('device')}\nFAILURE: "
                 f"{prob.get('failure')}\nCONSTRAINT: "
                 f"{prob.get('constraint')}\nQUESTION: "
                 f"{prob.get('question')}\nAnswer with the "
                 "design/indicator, its threshold, and the falsification "
                 "test.")
            ans, lat = "", None
            for attempt in (1, 2):
                try:
                    ans, lat = gen_call(q, key)
                    if ans.strip():
                        break
                except Exception as e:  # noqa: BLE001
                    print(f"[regen] {pid} attempt {attempt} FAIL "
                          f"{type(e).__name__}", flush=True)
                    time.sleep(3)
            if not ans.strip():
                (OUT / f"{pid}.json").write_text(json.dumps({
                    "problem_id": pid, "a1_source":
                        "GLM_CURATED_R10_REGEN",
                    "generation_state": "GEN_FAILED", "typed": True,
                    "at": now}, indent=1) + "\n", encoding="utf-8")
                print(f"[regen] {pid}: GEN_FAILED (typed)", flush=True)
                continue
            cr = check_answer_class_defects(
                ans, prob, json.dumps(prob, ensure_ascii=False),
                doi_resolve=False)
            rec = {
                "problem_id": pid,
                "a1_source": "GLM_CURATED_R10_REGEN",
                "generator": "zai-org/GLM-5.3 (zai gateway, sandbox "
                             "environment grant, live)",
                "system_contract": "SYS_A1_GROUNDED (battery SYS_A1 + "
                                   "AM10 D4 feasibility-grounding "
                                   "contract)",
                "generation_state": "GENERATED",
                "critic_verdict": cr["verdict"],
                "critic_anchors": [c.get("anchor") for c in cr["checks"]
                                   if c.get("verdict") != "CLEAN"],
                "latency_s": lat,
                "prompt_hash": hashlib.sha256(q.encode()).hexdigest()[:16],
                "superseded_f29_gen": "BATTERY_R5_FRESH_GEN_mistral14b_"
                                      "SYS_A1 (axes+prompt_hash only, "
                                      "eval/battery30_r11_r5.json)",
                "at": now,
                "a1_answer": ans,
            }
            (OUT / f"{pid}.json").write_text(
                json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            ok += 1
            print(f"[regen] {pid}: GENERATED critic={cr['verdict']} "
                  f"lat={lat}s ({ok}/{len(targets)})", flush=True)
    finally:
        gw.terminate()
    print(f"[regen] DONE {ok}/{len(targets)} generated", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""r11_a1f_v2_generate.py — AM11 D1 (F30): feasibility-AWARE ideation.

The measured F30 tradeoff (audited at 575c7ee57): SYS_A1F's
STANDARD-PRACTICE PARITY section created gravity toward standard-
practice-shaped MECHANISMS (dev12 novelty -1.000; the model satisfied
parity by conventionalizing the indicator), while grounding improved
feasibility (2.0 -> 1.333, still failing). The v2 contract makes the
two axes ORTHOGONAL BY CONSTRUCTION instead of trading them:

  NOVELTY lives in the OBSERVABLE — the leading indicator is a new
  derived quantity that standard monitoring practice for this failure
  class does NOT track (a different physical quantity, a different
  inference from the same data, a different failure signature). The
  measurement PRINCIPLE is the departure.
  FEASIBILITY lives in the IMPLEMENTATION — the observable MUST be
  computable from the stated existing sensors/logging with standard
  engineering math; the deployment is deliberately conventional
  (off-the-shelf, boring, procurable today).
  PARITY becomes a BURDEN LEDGER — same deployment burden, different
  observable — and the contract explicitly forbids winning the parity
  comparison by conventionalizing the indicator (the measured F30
  failure mode, named in the prompt).

Basis (Art. XIX): this targets the mechanism the auditor typed, not a
scored pair; the battery problems are fixed and untouched (Art. LXXIX
tuning discipline: the contract is a system change recorded before the
measurement).

Generator: the curated GLM rung (zai gateway), the F29-consistent
generator. Set: eval/pairs/r11_a1f_r2/ — per-pair records with
generator + system_prompt + question_hash; bytes written per pair for
batch committing (AM10 D1 durability discipline).
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")

OUT_DIR = REPO / "eval" / "pairs" / "r11_a1f_r2"
GW = "http://127.0.0.1:8787/v1/chat/completions"
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

SYS_A1_V2 = (
    "You are a careful engineer. Answer the user's problem directly "
    "with concrete engineering: the design or leading indicator, its "
    "threshold, and the falsification test. Respect every stated "
    "constraint verbatim. English only. Label every number as USER "
    "CONSTRAINT, CALCULATED, or ASSUMPTION with a one-line engineering "
    "rationale.")

SYS_A1F_V2 = SYS_A1_V2 + """

NOVEL-AND-FEASIBLE IDEATION (required — the two properties are
ORTHOGONAL and BOTH mandatory; do not trade one for the other):

STEP 1 — INVENT THE OBSERVABLE (this is where novelty lives): ask
"what could I measure or infer from the ALREADY-INSTALLED
instrumentation that standard monitoring practice for this failure
class does NOT track?" The leading indicator must be a NEW DERIVED
QUANTITY: a different physical quantity, a different inference from
the same data stream, or a different failure signature — NOT a
restatement of the standard condition-monitoring indicator. Name in
one line what standard practice tracks, and in one line why your
observable is a genuine departure from it.

STEP 2 — MAKE THE IMPLEMENTATION BORING (this is where feasibility
lives): your observable must be computable from the STATED existing
sensors, sampling rates, and logging with standard engineering math —
no new sensors, no new infrastructure, no exotic computation. If the
stated hardware seems insufficient, find the observable that IS
computable on it; feasibility is proven by the implementation bill,
not asserted.

REQUIRED SECTIONS (each labeled):
NOVELTY STATEMENT — what standard practice tracks vs your observable,
and the mechanism connecting your observable to the failure physics.
PHYSICS CHECK — the governing physical relation for your observable
and a one-to-two-line magnitude verification; a number that fails its
own physics is a defect.
IMPLEMENTATION BILL — components, materials, instruments, procedure;
off-the-shelf items first; anything that must be developed, say so
explicitly. This section is where feasibility is EARNED.
BURDEN LEDGER (STANDARD-PRACTICE PARITY) — compare installability,
operability, maintenance, rough cost class against the standard-
practice solution. The ledger's expected conclusion is SAME
deployment burden, DIFFERENT observable. Do NOT make the indicator
itself standard practice to win this comparison — that is the
measured failure mode this contract exists to prevent. If your
approach is heavier somewhere, say where and why it is worth it.
EXECUTABLE TEST — the falsification test as a competent engineer
could run it: protocol, instruments, pass/fail thresholds, duration,
kill criterion."""


def start_gateway():
    key = "gwkey-" + hashlib.sha256(
        str(time.time()).encode()).hexdigest()[:12]
    env = dict(os.environ, ZAI_GATEWAY_KEY=key)
    p = subprocess.Popen(
        ["node", str(REPO / "scripts" / "zai_gateway.mjs"), "8787"],
        stdout=open("/tmp/gw_a1fv2.log", "wb"), stderr=subprocess.STDOUT,
        env=env)
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:8787/healthz",
                                   timeout=2)
            return p, key
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise RuntimeError("gateway not healthy")


def gen_call(prompt, key, max_tokens=2600):
    body = json.dumps({
        "model": "zai-org/GLM-5.3",
        "messages": [{"role": "system", "content": SYS_A1F_V2},
                     {"role": "user", "content": prompt}],
        "max_tokens": max_tokens, "temperature": 0.0}).encode()
    req = urllib.request.Request(
        GW, data=body, headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    ch = (d.get("choices") or [{}])[0]
    return (str((ch.get("message") or {}).get("content") or ""),
            round(time.time() - t0, 1))


def main() -> int:
    from discovery_fabric.engine.plausibility_critic import (
        check_answer_class_defects)
    probs = {}
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    for p in plist:
        probs.setdefault(str(p.get("problem_id") or p.get("id")), p)
    for p in json.loads(
            (REPO / "eval" / "problems_dev12.json").read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)
    pids = sorted(probs)
    assert len(pids) == 30, len(pids)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gw, key = start_gateway()
    ok = 0
    try:
        for i, pid in enumerate(pids):
            outp = OUT_DIR / f"{pid}.json"
            if outp.exists():
                ok += 1
                print(f"[a1fv2] [{i+1}/30] {pid}: committed (resume)",
                      flush=True)
                continue
            prob = probs[pid]
            q = (f"DEVICE: {prob.get('device')}\nFAILURE: "
                 f"{prob.get('failure')}\nCONSTRAINT: "
                 f"{prob.get('constraint')}\nQUESTION: "
                 f"{prob.get('question')}\nInvent the leading indicator "
                 "per the NOVEL-AND-FEASIBLE IDEATION contract: the "
                 "observable is the departure, the implementation is "
                 "conventional.")
            ans, lat = "", None
            for attempt in (1, 2):
                try:
                    ans, lat = gen_call(q, key)
                    if ans.strip():
                        break
                except Exception as e:  # noqa: BLE001
                    print(f"[a1fv2] {pid} attempt {attempt} FAIL "
                          f"{type(e).__name__}", flush=True)
                    time.sleep(3)
            if not ans.strip():
                outp.write_text(json.dumps({
                    "problem_id": pid,
                    "generation_state": "GEN_FAILED", "typed": True,
                    "at": now}, indent=1) + "\n", encoding="utf-8")
                print(f"[a1fv2] {pid}: GEN_FAILED (typed)", flush=True)
                continue
            cr = check_answer_class_defects(
                ans, prob, json.dumps(prob, ensure_ascii=False),
                doi_resolve=False)
            rec = {
                "problem_id": pid,
                "a1_source": "GLM_A1F_V2_FEASIBILITY_AWARE",
                "generator": "zai-org/GLM-5.3 (zai gateway, sandbox "
                             "environment grant, live)",
                "system_prompt": "SYS_A1F_V2 (novelty in the observable, "
                                 "feasibility in the implementation; "
                                 "burden ledger replaces parity-"
                                 "conventionalization; F30 contract)",
                "generation_state": "GENERATED",
                "critic_verdict": cr["verdict"],
                "critic_anchors": [c.get("anchor") for c in cr["checks"]
                                   if c.get("verdict") != "CLEAN"],
                "latency_s": lat,
                "question_hash": hashlib.sha256(q.encode()).hexdigest()[:16],
                "at": now,
                "a1_answer": ans,
            }
            outp.write_text(
                json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            ok += 1
            print(f"[a1fv2] [{i+1}/30] {pid}: GENERATED "
                  f"critic={cr['verdict']} lat={lat}s", flush=True)
    finally:
        gw.terminate()
    print(f"[a1fv2] DONE {ok}/30", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

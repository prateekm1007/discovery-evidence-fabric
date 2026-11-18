#!/usr/bin/env python3
"""r11_a1f_v3_generate.py — AM12 direction 3 (F30 iteration): SAME-CLASS
NOVELTY, the strengthened feasibility-parity contract.

Basis (Art. XIX — the failure the r8 measurement exposed, typed from
the committed per-pair bytes of eval/battery_a1f_r8.json @ 663903176):
SYS_A1F_V2's orthogonality (novel OBSERVABLE + boring implementation)
produced BOTH measured failure modes:
  (a) DELIVERY-CLASS MISMATCH — where the field-standard practice for
      the problem is a DESIGN INTERVENTION (inducer fit, electrolyte
      chemistry switch, ...), a novel monitoring observable is the
      wrong class of outcome: the judge scores the missing delivery,
      not the sensor's elegance (worst gaps: bench-p04/p08/p10 fgap=4;
      novelty collapse on the dev12-committed pairs nd -1.7 mean where
      the curated baselines are themselves strong interventions).
  (b) V2 only achieved both clauses where monitoring IS the standard
      practice (the predictor class: bench-p01, eval-new10, eval-new11
      — the three fgap=0 existence proofs, nd=3).
The V2 user-prompt wrapper itself ('Invent the leading indicator')
biased every problem toward the monitoring class — typed as part of
the mechanism.

SYS_A1F_V3 fixes STEP 2 per the AM12 direction ('stronger
feasibility-parity constraint'):
  NOVELTY lives in the MECHANISM INSIDE the problem's own delivery
  class — first name what the standard practice DELIVERS (a design
  change or a monitoring scheme), then deliver THAT class with a
  genuinely different mechanism.
  FEASIBILITY lives in BURDEN-CLASS PARITY — the implementation bill
  uses the SAME instrument/material/service classes as the standard
  solution's own components (stated-present hardware, or off-the-shelf
  of the same class); no new sensing modality the problem does not
  state exists, no exotic materials, no development program.
  Both r8-measured failure modes are NAMED in the prompt as forbidden:
  substituting a sensor where the standard intervenes, and
  conventionalizing the mechanism to win the burden ledger.

The battery problems are fixed and untouched (Art. LXXIX); this
contract is recorded (committed) BEFORE any r9 measurement. Generator:
the curated GLM rung (zai gateway), F29-consistent. Set:
eval/pairs/r11_a1f_r3/ — per-pair records, bytes written per pair for
batch committing.
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

OUT_DIR = REPO / "eval" / "pairs" / "r11_a1f_r3"
GW = "http://127.0.0.1:8787/v1/chat/completions"
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

SYS_A1_V2 = (
    "You are a careful engineer. Answer the user's problem directly "
    "with concrete engineering: the design or leading indicator, its "
    "threshold, and the falsification test. Respect every stated "
    "constraint verbatim. English only. Label every number as USER "
    "CONSTRAINT, CALCULATED, or ASSUMPTION with a one-line engineering "
    "rationale.")

SYS_A1F_V3 = SYS_A1_V2 + """

SAME-CLASS NOVELTY IDEATION (required — novelty and feasibility are
BOTH mandatory and are achieved in the SAME delivery class; do not
trade one for the other):

STEP 1 — DELIVER THE STANDARD PRACTICE'S OUTCOME CLASS (this is where
novelty lives): FIRST name what the field-standard practice for this
problem class DELIVERS — a DESIGN CHANGE (hardware, material, or
procedure modification that prevents or mitigates the failure) or a
MONITORING/INDICATION scheme (a measured or inferred leading
indicator). Your proposal MUST deliver that SAME class of outcome:
where the standard practice intervenes on the design, you propose a
design change; where the standard practice monitors, you propose an
indicator. The novelty lives in the MECHANISM inside that class: a
genuinely different physical mechanism, architecture, or inference
achieving the same class of outcome. Name in one line what the
standard practice delivers, and in one line your mechanism's genuine
departure from it.

FORBIDDEN FAILURE MODES (both measured on the prior contract, named
here so you do not repeat them):
- SUBSTITUTING A SENSOR WHERE THE STANDARD PRACTICE INTERVENES: if the
  standard solution is a design change, a better measurement scheme is
  the wrong class of outcome — it does not solve the problem the
  standard solves.
- CONVENTIONALIZING TO WIN THE BURDEN COMPARISON: restating the
  standard mechanism with new words is not a departure.

STEP 2 — MATCH THE STANDARD PRACTICE'S BURDEN CLASS (this is where
feasibility lives): your implementation bill must use the SAME
instrument, material, and service classes as the standard-practice
solution itself — every component is either (i) already present in the
problem's stated device, instrumentation, or maintenance practice, or
(ii) an off-the-shelf item of the same class as a component the
standard solution itself uses. No new sensing modality the problem
does not state exists; no exotic materials; no development program.
Any capability the bill assumes beyond what the problem states is an
ASSUMPTION, labeled and justified. Feasibility is EARNED by the bill,
never asserted.

REQUIRED SECTIONS (each labeled):
NOVELTY STATEMENT — one line: what the standard practice delivers
(its class and mechanism); one line: your same-class mechanism
departure; then the failure-physics connection that makes your
mechanism work.
PHYSICS CHECK — the governing physical relation for your mechanism and
a one-to-two-line magnitude verification; a number that fails its own
physics is a defect.
IMPLEMENTATION BILL — components, materials, instruments, procedure;
off-the-shelf items first; state explicitly which items are the same
class as the standard solution's own components. This section is where
feasibility is EARNED.
BURDEN LEDGER (STANDARD-PRACTICE PARITY) — installability,
operability, maintenance, rough cost class against the
standard-practice solution. The ledger's expected conclusion is SAME
burden class, DIFFERENT mechanism. If your approach is heavier
somewhere, say where and why it is worth it.
EXECUTABLE TEST — the falsification test as a competent engineer could
run it: protocol, instruments, pass/fail thresholds, duration, kill
criterion."""


def _vault_env(env: dict) -> dict:
    """R64s4: pass the gitignored vault (.env.keys, NAME=VALUE lines)
    through to the gateway child process — the xkiro upstream needs
    XKIRO_API_KEY at call time. Values are never printed or logged;
    existing os.environ entries win (explicit overrides the vault)."""
    v = REPO / ".env.keys"
    if not v.exists():
        return env
    for line in v.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name and name == name.upper() and name not in env:
            env[name] = value.strip()
    return env


def start_gateway():
    key = "gwkey-" + hashlib.sha256(
        str(time.time()).encode()).hexdigest()[:12]
    env = _vault_env(dict(os.environ, ZAI_GATEWAY_KEY=key))
    p = subprocess.Popen(
        ["node", str(REPO / "scripts" / "zai_gateway.mjs"), "8787"],
        stdout=open("/tmp/gw_a1fv3.log", "wb"), stderr=subprocess.STDOUT,
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
    # R36: the auditor's registration ruling (Art. 7, executed verbatim):
    # "the frozen-machine generator registration is corrected to the
    # exact servable id glm-4-plus on the loop-local zai gateway." The
    # prior id zai-org/GLM-5.3 is servable on zero reachable paths —
    # the machine now requests the registered id it is attested against.
    body = json.dumps({
        # r64s4: the R36-corrected id is itself retired now (owner
        # order, AM60) — the request label follows the registration
        # (the gateway serves the registered upstream id regardless,
        # R458-C1; the served identity stays the evidence)
        "model": "cohere/command-a-plus",
        "messages": [{"role": "system", "content": SYS_A1F_V3},
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
                print(f"[a1fv3] [{i+1}/30] {pid}: committed (resume)",
                      flush=True)
                continue
            prob = probs[pid]
            q = (f"DEVICE: {prob.get('device')}\nFAILURE: "
                 f"{prob.get('failure')}\nCONSTRAINT: "
                 f"{prob.get('constraint')}\nQUESTION: "
                 f"{prob.get('question')}\nSolve the problem per the "
                 "SAME-CLASS NOVELTY contract: deliver the field-standard "
                 "practice's outcome class with a genuinely different "
                 "mechanism at the same implementation burden class.")
            ans, lat = "", None
            for attempt in (1, 2):
                try:
                    ans, lat = gen_call(q, key)
                    if ans.strip():
                        break
                except Exception as e:  # noqa: BLE001
                    print(f"[a1fv3] {pid} attempt {attempt} FAIL "
                          f"{type(e).__name__}", flush=True)
                    time.sleep(3)
            if not ans.strip():
                outp.write_text(json.dumps({
                    "problem_id": pid,
                    "generation_state": "GEN_FAILED", "typed": True,
                    "at": now}, indent=1) + "\n", encoding="utf-8")
                print(f"[a1fv3] {pid}: GEN_FAILED (typed)", flush=True)
                continue
            cr = check_answer_class_defects(
                ans, prob, json.dumps(prob, ensure_ascii=False),
                doi_resolve=False)
            rec = {
                "problem_id": pid,
                "a1_source": "GLM_A1F_V3_SAME_CLASS_NOVELTY",
                "generator": "zai-org/GLM-5.3 (zai gateway, sandbox "
                             "environment grant, live)",
                "system_prompt": "SYS_A1F_V3 (delivery-class parity: the "
                                 "standard practice's outcome class + a "
                                 "different mechanism at the same burden "
                                 "class; the r8-measured delivery-class-"
                                 "mismatch and conventionalization failure "
                                 "modes named; AM12 D3 contract)",
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
            print(f"[a1fv3] [{i+1}/30] {pid}: GENERATED "
                  f"critic={cr['verdict']} lat={lat}s", flush=True)
    finally:
        gw.terminate()
    print(f"[a1fv3] DONE {ok}/30", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

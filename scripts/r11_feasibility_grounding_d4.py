#!/usr/bin/env python3
"""D4 (AM9 direction 4) — the feasibility-grounding leg.

The AM9 verdict: the machine invents novel mechanisms that are LESS
feasible than standard practice (auditor n=10 feasibility gap 0.5 >
0.25; battery r6 gap 2.0). The capability frontier is NOT more
novelty — it is feasibility-grounding: novel ideas that survive the
feasibility clause.

This script implements the generation-side leg: SYS_A1F, the
feasibility-grounded intervention contract. On top of SYS_A1 (the
labeled-number contract), the generator must now:

  1. PHYSICS/UNIT SANITY — state the governing physical relation and
     check magnitudes against it (a number that fails its own physics
     is a defect, not a design).
  2. IMPLEMENTATION BILL — name the concrete means (components,
     materials, procedures) with which the change is actually built/
     procured/operated, so feasibility is assessable from the text.
  3. STANDARD-PRACTICE FEASIBILITY PARITY — explicitly compare the
     implementation burden against the standard-practice solution
     (installability, operability, cost class); if the novel approach
     is heavier, say where and why it is worth it.
  4. EXECUTABLE FALSIFICATION — the test must be runnable as written
     (protocol, instruments, pass/fail thresholds, duration).

Output: eval/pairs/r11_a1f_r1/<pid>.json — 30 GLM generations under
SYS_A1F (all 30 problems; the 12 dev12 too, so the battery measures
the feasibility-grounded arm against the SAME curated baselines at
n=30 — the AM9 acceptance: feasibility |gap| <= 0.25 AND novelty
delta >= 0.5 on >= 30 pairs).

Generator: zai/zai-org/GLM-5.3 (the strong rung, UNRESTRICTED
policy, per-pair governor reset, 6s floor). Judge battery: the
recalibrated v2 axis suffix with k=3 majority (the D2 output), run
separately.
"""
import json
import os
import sys
import time
import hashlib
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")

OUT_DIR = REPO / "eval" / "pairs" / "r11_a1f_r1"

SYS_BASE = ("You are a careful engineer. Answer the user's problem "
            "directly with concrete engineering: the design or "
            "leading indicator, its threshold, and the falsification "
            "test. Respect every stated constraint verbatim. English "
            "only.")
SYS_A1 = SYS_BASE + (" Label every number as USER CONSTRAINT, "
                     "CALCULATED, or ASSUMPTION with a one-line "
                     "engineering rationale.")
SYS_A1F = SYS_A1 + """

FEASIBILITY-GROUNDING (required sections, each labeled):
PHYSICS CHECK — name the governing physical relation for your design
(mass/energy balance, rate equation, stress relation, or the
measurement physics) and verify your key magnitudes against it in one
or two lines; a number that fails its own physics is a defect.
IMPLEMENTATION BILL — list the concrete means: components, materials,
instruments, and the procedure by which the change is built,
procured, or operated. Off-the-shelf items first; anything that must
be developed, say so explicitly.
STANDARD-PRACTICE PARITY — in two or three lines compare the
implementation burden (installability, operability, maintenance,
rough cost class) with the standard-practice solution for this
problem class; if your approach is heavier, say where and why it is
worth it.
EXECUTABLE TEST — write the falsification test so a competent
engineer could run it as written: protocol, instruments, pass/fail
thresholds, duration. A test that cannot be run is not a test."""


def main():
    from discovery_fabric.engine import llm_registry as LR
    from discovery_fabric.engine import llm_economy as _econ

    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    probs = {str(p.get("problem_id") or p.get("id")): p for p in plist}
    for p in json.loads((REPO / "eval" / "problems_dev12.json")
                        .read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)
    pids = sorted(probs)
    assert len(pids) == 30, len(pids)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done, failed = 0, []
    for i, pid in enumerate(pids):
        outp = OUT_DIR / f"{pid}.json"
        if outp.exists():
            done += 1
            print(f"[d4] [{i+1}/30] {pid}: committed (resume)", flush=True)
            continue
        prob = probs[pid]
        _econ.reset_governor(f"d4:{pid}")
        q = (f"DEVICE: {prob.get('device')}\nFAILURE: "
             f"{prob.get('failure')}\nCONSTRAINT: "
             f"{prob.get('constraint')}\nQUESTION: "
             f"{prob.get('question')}\nAnswer with the design/indicator, "
             "its threshold, and the falsification test.")
        t0 = time.time()
        res = LR.generate(q, system=SYS_A1F, timeout=240, max_retries=0,
                          max_tokens=4000, hard_pin_provider="zai")
        lat = round(time.time() - t0, 1)
        content = str(res.content or "").strip()
        rec = {
            "problem_id": pid,
            "arm_source": "GLM_FEASIBILITY_GROUNDED_r11_a1f_r1",
            "generator": f"{res.provider_id}/{res.model}",
            "system_prompt": SYS_A1F,
            "question_hash": hashlib.sha256(
                q.encode("utf-8")).hexdigest()[:16],
            "a1_answer": content[:14000],
            "wall_s": lat,
            "at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        if res.status == "OK" and content:
            (OUT_DIR / f"{pid}.json").write_text(
                json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            done += 1
            print(f"[d4] [{i+1}/30] {pid}: {len(content)} chars {lat}s",
                  flush=True)
        else:
            failed.append((pid, res.status, str(res.error or "")[:80]))
            print(f"[d4] [{i+1}/30] {pid}: FAIL {res.status} "
                  f"{str(res.error or '')[:60]}", flush=True)
        time.sleep(6)

    print(f"\n[d4] feasibility-grounded arms: {done}/30, "
          f"{len(failed)} failed")
    for f in failed:
        print("  FAIL:", f)
    return 0 if done == 30 else 1


if __name__ == "__main__":
    sys.exit(main())

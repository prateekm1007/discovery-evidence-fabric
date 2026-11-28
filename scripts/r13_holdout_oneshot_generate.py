#!/usr/bin/env python3
"""r13_holdout_oneshot_generate.py — AM13 D1: the ONE-SHOT sealed
holdout generation (24 problems, HO-01..HO-24).

ONE-SHOT DISCIPLINE (Art. LXXIX + the registered protocol):
- The contract is SYS_A1F_V2 VERBATIM — the machine as measured in
  battery r8 — imported from r11_a1f_v2_generate.py, not copied and
  not tuned. No holdout-specific wording, no rubric access (the
  builder never received it), no iteration against scored feedback.
- Temperature 0. GLM (zai gateway), the curated generator.
- The standing budget: one generation + critic check + up to 2
  disclosed repair re-asks (the r8 discipline). EVERY attempt is
  recorded per problem (zeros are data; superseded bytes stay).
- Output: eval/holdout_v1_a1/HO-*.json — per-problem records with
  generator, contract id, question_hash, and the full attempt trail.
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

from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    check_answer_class_defects)
from r11_a1f_v2_generate import SYS_A1F_V2, start_gateway  # noqa: E402

OUT_DIR = REPO / "eval" / "holdout_v1_a1"
GW = "http://127.0.0.1:8787/v1/chat/completions"
REPAIR_BUDGET = 2  # the standing machine budget (r8 discipline)
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


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


def question_of(prob):
    return (f"DEVICE: {prob.get('device')}\nFAILURE: "
            f"{prob.get('failure')}\nCONSTRAINT: "
            f"{prob.get('constraint')}\nQUESTION: "
            f"{prob.get('question')}\n"
            + ("Invent the leading indicator per the "
               "NOVEL-AND-FEASIBLE IDEATION contract: the observable is "
               "the departure, the implementation is conventional."
               if (prob.get("question_type") or "").startswith(
                   "predictor") else
               "Answer per the NOVEL-AND-FEASIBLE IDEATION contract: "
               "the observable is the departure, the implementation is "
               "conventional."))


def critic(ans, prob):
    return check_answer_class_defects(
        ans, prob, json.dumps(prob, ensure_ascii=False),
        doi_resolve=False)


def main() -> int:
    raw = json.loads((REPO / "eval" / "holdout_v1_problems.json")
                     .read_text())
    plist = raw if isinstance(raw, list) else raw.get("problems", [])
    probs = {p["problem_id"]: p for p in plist}
    assert len(probs) == 24, len(probs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gw, key = start_gateway()
    done = 0
    try:
        for i, pid in enumerate(sorted(probs)):
            outp = OUT_DIR / f"{pid}.json"
            if outp.exists():
                done += 1
                print(f"[ho] [{i+1}/24] {pid}: committed (resume)",
                      flush=True)
                continue
            prob = probs[pid]
            q = question_of(prob)
            attempts = []
            final, verdict, anchors = "", None, []
            try:
                ans, lat = gen_call(q, key)
                attempts.append({"kind": "generation", "latency_s": lat,
                                 "chars": len(ans)})
                cr = critic(ans, prob)
                final, verdict = ans, cr["verdict"]
                anchors = [c.get("anchor") for c in cr["checks"]
                           if c.get("verdict") != "CLEAN"]
                if verdict != "CLEAN":
                    disclosed = (
                        "REPAIR DIRECTIVE (typed critic findings on the "
                        "previous draft, disclosed): "
                        + "; ".join(a for a in anchors if a)
                        + ". Fix ONLY these defects; keep the observable "
                        "(the novelty departure) and the implementation "
                        "bill otherwise intact. The ONLY USER CONSTRAINT "
                        "labels allowed are the user-stated variables; "
                        "unstated equipment is ASSUMPTION with a one-line "
                        "justification.")
                    for rep in range(1, REPAIR_BUDGET + 1):
                        if verdict == "CLEAN":
                            break
                        q2 = q + "\n\n" + disclosed
                        try:
                            ans2, lat2 = gen_call(q2, key)
                        except Exception as e:  # noqa: BLE001
                            attempts.append({"kind": f"repair_{rep}",
                                             "error": type(e).__name__})
                            continue
                        attempts.append({"kind": f"repair_{rep}",
                                         "latency_s": lat2,
                                         "chars": len(ans2),
                                         "findings_disclosed": anchors})
                        cr2 = critic(ans2, prob)
                        if cr2["verdict"] == "CLEAN":
                            final, verdict = ans2, "CLEAN"
                            anchors = []
                        else:
                            anchors = [c.get("anchor")
                                       for c in cr2["checks"]
                                       if c.get("verdict") != "CLEAN"]
                            if not final.strip() or verdict == "KILL":
                                final = ans2 if verdict != "KILL" else final
            except Exception as e:  # noqa: BLE001
                attempts.append({"kind": "generation",
                                 "error": type(e).__name__})
            rec = {
                "problem_id": pid,
                "question_type": prob.get("question_type"),
                "a1_source": "GLM_A1F_V2_HOLDOUT_ONESHOT",
                "generator": "zai-org/GLM-5.3 (zai gateway, sandbox "
                             "environment grant, live)",
                "contract": "SYS_A1F_V2 verbatim (the battery-r8-measured "
                            "machine; no holdout tuning; no rubric access)",
                "one_shot": True,
                "attempts": attempts,
                "critic_verdict": verdict,
                "critic_anchors": anchors,
                "generation_state": ("GENERATED" if final.strip()
                                     else "GEN_FAILED"),
                "question_hash": hashlib.sha256(
                    q.encode()).hexdigest()[:16],
                "at": now,
                "a1_answer": final,
            }
            outp.write_text(
                json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            done += 1
            print(f"[ho] [{i+1}/24] {pid}: {rec['generation_state']} "
                  f"critic={verdict} attempts={len(attempts)}",
                  flush=True)
    finally:
        gw.terminate()
    print(f"[ho] DONE {done}/24", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

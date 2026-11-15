#!/usr/bin/env python3
"""r13_a1t_generate.py — AM14 D2 (F31): QUESTION-TYPE-AWARE ideation.

The F31 fix: one contract cannot serve both question types.
- INTERVENTION-PROPOSAL questions get SYS_A1_INT (defined below,
  committed BEFORE generation per Art. XXVII): invent the MITIGATION
  (design/operational change attacking the failure's driving
  mechanism), feasible hardware, and an EFFECTIVENESS falsifier.
- PREDICTOR-DESIGN questions keep SYS_A1F_V3 (session-2's audited
  contract, imported — not copied): invent the observable, boring
  implementation.

Dispatch is by the problem's question_type field. The AM14 D3
question-type gate (r13_question_type_gate) screens every answer
in-process; a MISMATCH is recorded, the standing repair budget runs
on it, and the final state is typed. Output: eval/pairs/r11_a1t_r1.
"""
import datetime
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
import os  # noqa: E402
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")

from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    check_answer_class_defects)
from r11_a1f_v3_generate import (  # noqa: E402
    SYS_A1F_V3, start_gateway, gen_call)
from r13_question_type_gate import gate_question_type  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r11_a1t_r1"
REPAIR_BUDGET = 2  # standing machine budget
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

SYS_A1_INT = """NOVEL INTERVENTION IDEATION (required — the two
properties are ORTHOGONAL and BOTH mandatory; do not trade one for
the other):

STEP 0 — ANSWER THE QUESTION ASKED: this question asks for an
INTERVENTION — how to prevent, mitigate, reduce, or fix the failure.
The answer is a DESIGN OR OPERATIONAL CHANGE to the equipment, its
materials, its configuration, its duty, or its maintenance. A
monitoring observable, a leading indicator, or a detection scheme is
NOT an answer to an intervention question: it watches the failure
instead of preventing it. Do not propose a predictor.

STEP 1 — INVENT THE MITIGATION (this is where novelty lives): ask
"what change to design, material, configuration, duty, or procedure
directly reduces the DRIVING MECHANISM of the failure that standard
practice does not make?" The mitigation must be a NEW MECHANISM: not
a restatement of the standard mitigation, not "monitor it more
closely", not "do the standard practice more often". Name in one
line what standard practice does, and in one line why your
mitigation is a genuine departure.

STEP 1b — ADJACENT-TECHNIQUE CLEARANCE (mandatory): name the CLOSEST
existing mitigation practice from ANY industry and state in one line
what makes yours different. A mitigation that merely relabels a
textbook fix is a defect: if the closest practice in ANY industry IS
your mitigation, invent a further departure.

STEP 2 — MAKE THE HARDWARE FEASIBLE (this is where feasibility
lives): the mitigation must be installable on the stated equipment
with standard engineering practice — procurable components and
materials, standard procedures, no exotic technology. If the
straightforward version of the mechanism needs exotic hardware, find
the procurable version of the same mechanism; feasibility is proven
by the implementation bill, not asserted.

REQUIRED SECTIONS (each labeled, IN THIS ORDER):
NOVELTY STATEMENT (INTERVENTION) — the question-answered sentence
first (what is being proposed), then what standard practice does vs
your mitigation, the adjacent-technique clearance, and the mechanism
by which the intervention attacks the failure's driving physics.
PHYSICS CHECK — the governing physical relation showing the
intervention reduces the failure mechanism, with a one-to-two-line
magnitude verification; a number that fails its own physics is a
defect.
IMPLEMENTATION BILL — components, materials, instruments, procedure
for INSTALLING and RUNNING the intervention; procurable items first;
anything that must be developed, say so explicitly.
BURDEN LEDGER (STANDARD-PRACTICE PARITY) — compare installability,
operability, maintenance, rough cost class against the standard-
practice solution. The ledger's expected conclusion is SAME
deployment burden, DIFFERENT mechanism. Do NOT strip the novelty to
win this comparison. If heavier somewhere, say where and why it is
worth it.
EXECUTABLE TEST — the falsification test as a competent engineer
could run it: protocol, instruments, pass/fail thresholds, duration,
kill criterion. For an intervention the falsifier validates
EFFECTIVENESS (the failure rate or magnitude DROPS with the
intervention), not a correlation."""


def problem_prompt(prob):
    base = (f"DEVICE: {prob.get('device')}\nFAILURE: "
            f"{prob.get('failure')}\nCONSTRAINT: "
            f"{prob.get('constraint')}\nQUESTION: "
            f"{prob.get('question')}\n")
    qt = (prob.get("question_type") or "").lower()
    if qt.startswith("intervention"):
        return base + ("Propose the mitigation this question asks for, "
                       "per the NOVEL INTERVENTION IDEATION contract: "
                       "the answer is an intervention (a design or "
                       "operational change), NOT a monitoring "
                       "observable.")
    return base + ("Invent the leading indicator per the "
                   "NOVEL-AND-FEASIBLE IDEATION contract: the "
                   "observable is the departure, the implementation "
                   "is conventional.")


def system_contract(prob):
    qt = (prob.get("question_type") or "").lower()
    return SYS_A1_INT if qt.startswith("intervention") else SYS_A1F_V3


def main() -> int:
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    probs = {str(p.get("problem_id") or p.get("id")): p for p in plist}
    for p in json.loads((REPO / "eval" / "problems_dev12.json")
                        .read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)
    assert len(probs) == 30, len(probs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gw, key = start_gateway()
    done = 0
    try:
        for i, pid in enumerate(sorted(probs)):
            outp = OUT_DIR / f"{pid}.json"
            if outp.exists():
                done += 1
                print(f"[a1t] [{i+1}/30] {pid}: committed (resume)",
                      flush=True)
                continue
            prob = probs[pid]
            q = problem_prompt(prob)
            contract = system_contract(prob)
            attempts = []
            final, verdict, anchors, tg = "", None, [], None
            try:
                # v3 gen_call hardcodes SYS_A1F_V3 as the system prompt,
                # so the intervention calls go through a local variant.
                ans, lat = _gen(q, contract, key)
                attempts.append({"kind": "generation", "latency_s": lat,
                                 "chars": len(ans)})
                cr = critic(ans, prob)
                final, verdict = ans, cr["verdict"]
                anchors = [c.get("anchor") for c in cr["checks"]
                           if c.get("verdict") != "CLEAN"]
                tg = gate_question_type(final, prob)
                if verdict != "CLEAN" or tg["verdict"] == "MISMATCH":
                    disclosed = ("REPAIR DIRECTIVE (typed findings on "
                                 "the previous draft, disclosed): "
                                 + "; ".join(a for a in anchors if a)
                                 + ("; " + tg["reason"]
                                    if tg["verdict"] == "MISMATCH"
                                    else "")
                                 + ". " + ("The question asks for an "
                                           "INTERVENTION: replace the "
                                           "observable proposal with an "
                                           "actual design or "
                                           "operational change per the "
                                           "NOVEL INTERVENTION IDEATION "
                                           "contract."
                                           if tg["verdict"] == "MISMATCH"
                                           else
                                           "Fix ONLY these defects; "
                                           "keep the proposal's core "
                                           "otherwise intact.")
                                 + " The ONLY USER CONSTRAINT labels "
                                   "allowed are the user-stated "
                                   "variables; unstated equipment is "
                                   "ASSUMPTION with a one-line "
                                   "justification.")
                    for rep in range(1, REPAIR_BUDGET + 1):
                        if verdict == "CLEAN" and \
                                tg["verdict"] == "MATCH":
                            break
                        try:
                            ans2, lat2 = _gen(q + "\n\n" + disclosed,
                                              contract, key)
                        except Exception as e:  # noqa: BLE001
                            attempts.append({"kind": f"repair_{rep}",
                                             "error": type(e).__name__})
                            continue
                        attempts.append({"kind": f"repair_{rep}",
                                         "latency_s": lat2,
                                         "chars": len(ans2),
                                         "findings_disclosed": anchors,
                                         "type_gate": tg})
                        cr2 = critic(ans2, prob)
                        tg2 = gate_question_type(ans2, prob)
                        if cr2["verdict"] == "CLEAN" and \
                                tg2["verdict"] == "MATCH":
                            final, verdict, anchors = ans2, "CLEAN", []
                            tg = tg2
                        else:
                            anchors = [c.get("anchor")
                                       for c in cr2["checks"]
                                       if c.get("verdict") != "CLEAN"]
                            tg = tg2
                            if not final.strip():
                                final = ans2
                            verdict = cr2["verdict"]
            except Exception as e:  # noqa: BLE001
                attempts.append({"kind": "generation",
                                 "error": type(e).__name__})
            rec = {
                "problem_id": pid,
                "question_type": prob.get("question_type"),
                "a1_source": ("GLM_A1_INT_INTERVENTION_GLM"
                              if (prob.get("question_type") or "")
                              .startswith("intervention")
                              else "GLM_A1F_V3_SAME_CLASS_NOVELTY"),
                "generator": "zai-org/GLM-5.3 (zai gateway, sandbox "
                             "environment grant, live)",
                "contract": ("SYS_A1_INT verbatim (F31 intervention "
                             "contract; committed before generation)"
                             if (prob.get("question_type") or "")
                             .startswith("intervention")
                             else "SYS_A1F_V3 verbatim (session-2 "
                                  "audited predictor contract)"),
                "type_gate": tg,
                "attempts": attempts,
                "critic_verdict": verdict,
                "critic_anchors": anchors,
                "generation_state": ("GENERATED" if final.strip()
                                     else "GEN_FAILED"),
                "at": now,
                "a1_answer": final,
            }
            outp.write_text(json.dumps(rec, indent=1,
                                       ensure_ascii=False) + "\n",
                            encoding="utf-8")
            done += 1
            print(f"[a1t] [{i+1}/30] {pid}: {rec['generation_state']} "
                  f"critic={verdict} type={tg['verdict'] if tg else '?'} "
                  f"attempts={len(attempts)}", flush=True)
    finally:
        gw.terminate()
    print(f"[a1t] DONE {done}/30", flush=True)
    return 0


def _gen(prompt, contract, key):
    """gen_call with an explicit system contract (the v3 helper pins
    SYS_A1F_V3; intervention questions need SYS_A1_INT)."""
    import urllib.request
    body = json.dumps({
        "model": "zai-org/GLM-5.3",
        "messages": [{"role": "system", "content": contract},
                     {"role": "user", "content": prompt}],
        "max_tokens": 2600, "temperature": 0.0}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8787/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    ch = (d.get("choices") or [{}])[0]
    return (str((ch.get("message") or {}).get("content") or ""),
            round(time.time() - t0, 1))


def critic(ans, prob):
    return check_answer_class_defects(
        ans, prob, json.dumps(prob, ensure_ascii=False), doi_resolve=False)


if __name__ == "__main__":
    sys.exit(main())

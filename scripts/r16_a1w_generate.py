#!/usr/bin/env python3
"""r16_a1w_generate.py — AM16 D1 (F30 isolated frontier): WEIGHT-BOUND
mitigation design.

AM16: F31 CLOSED (30/30 type-MATCH credited); F30 OPEN-ISOLATED — the
feasibility failure is carried by the heavy-mechanism interventions
(intervention rows |gap| 2.389 vs predictor 1.167 near-parity;
bench-p02 the counter-proof: sg=+1 — a novel mechanism delivered
through a boring implementation). The fix is NOT novelty-stripping
(Art. XIX: not "what makes the gate pass"; the judge still measures
novelty Delta >= 0.5 and a stripped arm fails that clause) — it is a
binding WEIGHT RULE in the contract: novelty lives in the MECHANISM,
weight lives in the IMPLEMENTATION.

Changes vs SYS_A1_INT (pre-registered verbatim below BEFORE
generation, Art. XXVII):
- STEP 2 replaced by THE WEIGHT RULE (binds): mechanisms must ride
  the standard practice's existing infrastructure and cost class
  (substitution / additive package / duty-schedule-config / fit-
  tolerance-geometry within existing machining / procedural /
  procurable-part swap); new hardware classes are out of scope —
  choose a different mechanism that carries the same physics through
  a lighter implementation (the bench-p02 pattern, named in-contract).
- STEP 3 PROVE THE WEIGHT: the bill is itemized against the standard
  practice's own bill and the ledger CONCLUDES same-or-lower burden
  class from those rows (a "same burden" conclusion over new
  equipment is a defect).
- STEP 0, STEP 1, STEP 1b and the five required sections (incl. the
  EFFECTIVENESS falsifier) carried over unchanged.

Intervention-proposal problems -> SYS_A1_INT_WB; predictor-design
problems -> SYS_A1F_V3 (imported) — but predictor arms are NOT
regenerated here: the 12 predictor records are reused BYTE-IDENTICAL
from r11_a1t_r1 (copied verbatim with a lineage manifest), so battery
r11 isolates the contract change to the intervention arm exactly as
r10 isolated F31 (predictor parity is then measured on identical
bytes re-judged). Output: eval/pairs/r11_a1w_r1.
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
from r11_a1f_v3_generate import SYS_A1F_V3, start_gateway  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r11_a1w_r1"
PREV_DIR = REPO / "eval" / "pairs" / "r11_a1t_r1"
REPAIR_BUDGET = 2  # standing machine budget
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

SYS_A1_INT_WB = """NOVEL INTERVENTION IDEATION — WEIGHT-BOUND (required
— the two properties are ORTHOGONAL and BOTH mandatory; do not trade
one for the other):

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

STEP 2 — THE WEIGHT RULE (this is where feasibility lives, and it
BINDS): the mitigation must be deliverable WITHIN the standard
practice's existing infrastructure and cost class. Prefer mechanism
classes that ride existing practice: a material or coating
substitution, an additive-package change, a duty or schedule or
configuration change, a fit/tolerance/geometry change within
existing machining, a procedural change, or a swap to procurable
standard parts. A mechanism that requires NEW HARDWARE CLASSES —
major redesign, new tooling, exotic instruments, plant-level
changes — is OUT OF SCOPE for this problem: choose a DIFFERENT
mechanism that carries the same physics through a lighter
implementation. The pattern to emulate: novelty lives in the
MECHANISM, weight lives in the IMPLEMENTATION — a genuinely new
mechanism delivered through a boring, procurable implementation. If
the honest version of your mechanism cannot satisfy the weight rule,
go back to STEP 1 and invent a different mechanism; do not keep the
heavy mechanism and hope the ledger hides it.

STEP 3 — PROVE THE WEIGHT: the IMPLEMENTATION BILL must be itemized
against the standard practice's own bill (what the standard fix
already uses vs what yours adds or replaces), and the BURDEN LEDGER
must CONCLUDE same-or-lower burden class FROM THOSE ITEMIZED ROWS.
A ledger that concludes "same burden" while the bill shows new
equipment is a defect. Feasibility is proven by the itemized
comparison, not asserted.

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
for INSTALLING and RUNNING the intervention, itemized against the
standard practice's own bill; procurable items first; anything that
must be developed, say so explicitly (and treat it as a weight-rule
violation to be engineered out).
BURDEN LEDGER (STANDARD-PRACTICE PARITY) — the itemized comparison
from the bill, concluding same-or-lower burden class; if heavier
anywhere, say where and why the physics forces it (this is a typed
defect for the machine, not an acceptable conclusion).
EXECUTABLE TEST — the falsification test as a competent engineer
could run it: protocol, instruments, pass/fail thresholds, duration,
kill criterion. For an intervention the falsifier validates
EFFECTIVENESS (the failure rate or magnitude DROPS with the
intervention), not a correlation."""


def system_contract(prob):
    qt = (prob.get("question_type") or "").lower()
    return SYS_A1_INT_WB if qt.startswith("intervention") else SYS_A1F_V3


def main() -> int:
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    probs = {str(p.get("problem_id") or p.get("id")): p for p in plist}
    for p in json.loads((REPO / "eval" / "problems_dev12.json")
                        .read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)
    assert len(probs) == 30, len(probs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Reuse the 12 predictor arms byte-identical (r11_a1t_r1 -> r11_a1w_r1)
    reused = 0
    for pid, prob in probs.items():
        qt = (prob.get("question_type") or "").lower()
        dst = OUT_DIR / f"{pid}.json"
        if not qt.startswith("intervention") and not dst.exists():
            src = PREV_DIR / f"{pid}.json"
            if src.exists():
                dst.write_text(src.read_text(encoding="utf-8"),
                               encoding="utf-8")
                reused += 1
    print(f"[a1w] predictor arms reused byte-identical: {reused}",
          flush=True)

    gw, key = start_gateway()
    done = 0
    try:
        for i, pid in enumerate(sorted(probs)):
            prob = probs[pid]
            qt = (prob.get("question_type") or "").lower()
            if not qt.startswith("intervention"):
                continue
            outp = OUT_DIR / f"{pid}.json"
            if outp.exists():
                done += 1
                print(f"[a1w] [{i+1}/30] {pid}: committed (resume)",
                      flush=True)
                continue
            base = (f"DEVICE: {prob.get('device')}\nFAILURE: "
                    f"{prob.get('failure')}\nCONSTRAINT: "
                    f"{prob.get('constraint')}\nQUESTION: "
                    f"{prob.get('question')}\n"
                    "Propose the mitigation this question asks for, per "
                    "the NOVEL INTERVENTION IDEATION — WEIGHT-BOUND "
                    "contract: a genuinely new MECHANISM delivered "
                    "through an implementation that rides the standard "
                    "practice's existing infrastructure and cost class.")
            contract = SYS_A1_INT_WB
            attempts = []
            final, verdict, anchors, tg = "", None, [], None
            try:
                ans, lat = _gen(base, contract, key)
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
                                    if tg["verdict"] == "MISMATCH" else "")
                                 + ". Fix ONLY these defects; keep the "
                                   "proposal's core otherwise intact. "
                                   "The ONLY USER CONSTRAINT labels "
                                   "allowed are the user-stated "
                                   "variables; unstated equipment is "
                                   "ASSUMPTION with a one-line "
                                   "justification.")
                    for rep in range(1, REPAIR_BUDGET + 1):
                        if verdict == "CLEAN" and \
                                tg["verdict"] == "MATCH":
                            break
                        try:
                            ans2, lat2 = _gen(base + "\n\n" + disclosed,
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
                "a1_source": "GLM_A1_INT_WB_WEIGHT_BOUND_GLM",
                "generator": ("zai-org/GLM-5.3 (zai gateway, sandbox "
                              "environment grant, live)"),
                "contract": "SYS_A1_INT_WB verbatim (AM16 D1 weight-"
                            "bound contract; committed before "
                            "generation)",
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
            print(f"[a1w] [{i+1}/30] {pid}: {rec['generation_state']} "
                  f"critic={verdict} type={tg['verdict'] if tg else '?'} "
                  f"attempts={len(attempts)}", flush=True)
    finally:
        gw.terminate()
    print(f"[a1w] DONE {done} intervention arms (+{reused} predictor "
          f"reused)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

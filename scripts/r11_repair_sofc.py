#!/usr/bin/env python3
"""r11_repair_sofc.py — the single repair leg for the a1f_v2 batch's
one critic-KILL (eval-sofc-thermal-cycling, NYQUIST_UNSAMPLED +
ARITHMETIC_CYCLES). Same discipline as the audited R10 repair: the
typed findings are disclosed in the re-ask; the mechanism is preserved;
superseded bytes stay in the record (Art. XI); one attempt; a
still-KILL stays typed for the auditor (Art. XXV)."""
import datetime
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

PID = "eval-sofc-thermal-cycling"
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


def main() -> int:
    f = REPO / "eval" / "pairs" / "r11_a1f_r2" / f"{PID}.json"
    rec = json.loads(f.read_text())
    prob = None
    for src in ("eval/problems.json", "eval/problems_dev12.json"):
        d = json.loads((REPO / src).read_text())
        pl = d if isinstance(d, list) else d.get("problems", [])
        for p in pl:
            if str(p.get("problem_id") or p.get("id")) == PID:
                prob = p
    gw, key = start_gateway()
    try:
        repair_note = (
            "REPAIR DIRECTIVE (typed critic findings on the previous "
            "drafts, disclosed): (1) USER_LABEL_FABRICATED_CONSTRAINT "
            "— the previous draft labeled items as USER CONSTRAINT "
            "that the user never stated (e.g. 'thermocouples already "
            "installed', 'existing stack electronics'). The ONLY USER "
            "CONSTRAINT labels allowed are the five user-stated "
            "variables: 500 thermal cycles 25-800 C, 5 C/min heating "
            "rate, OCV above 1.0 V, seal leakage below 1 percent of "
            "fuel flow, stack mass increase below 2 percent. Any "
            "equipment you rely on that the user did not state is an "
            "ASSUMPTION with a one-line justification (e.g. "
            "'ASSUMPTION: type-K thermocouples present — standard on "
            "SOFC test stands'), never a USER CONSTRAINT. (2) "
            "NYQUIST/ARITHMETIC — recompute every periodicity feature "
            "within the sampling rate you actually claim, state that "
            "sampling rate as an ASSUMPTION, and show the thermal-cycle "
            "arithmetic (cycles per day, time-to-threshold) explicitly. "
            "Keep the observable (the novelty departure) and the "
            "implementation bill otherwise intact.")
        q = (f"DEVICE: {prob.get('device')}\nFAILURE: "
             f"{prob.get('failure')}\nCONSTRAINT: {prob.get('constraint')}"
             f"\nQUESTION: {prob.get('question')}\nAnswer per the "
             "NOVEL-AND-FEASIBLE IDEATION contract (observable is the "
             f"departure, implementation is conventional).\n\n{repair_note}")
        body = json.dumps({
            "model": "zai-org/GLM-5.3",
            "messages": [{"role": "system", "content": SYS_A1F_V2},
                         {"role": "user", "content": q}],
            "max_tokens": 2600, "temperature": 0.0}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8787/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read())
        ans = str(((d.get("choices") or [{}])[0].get("message")
                   or {}).get("content") or "")
        if not ans.strip():
            print("[repair] empty answer — pair stays typed-KILL")
            return 1
        cr = check_answer_class_defects(
            ans, prob, json.dumps(prob, ensure_ascii=False),
            doi_resolve=False)
        rec["a1_answer_repair_attempt"] = {
            "at": now,
            "repair_reason": "critic KILL NYQUIST_UNSAMPLED + "
                             "ARITHMETIC_CYCLES on the first "
                             "generation; findings disclosed in the "
                             "re-ask",
            "critic_verdict": cr["verdict"],
            "critic_anchors": [c.get("anchor") for c in cr["checks"]
                               if c.get("verdict") != "CLEAN"],
        }
        rec["a1_answer_superseded"] = rec.pop("a1_answer")
        rec["a1_answer"] = ans
        rec["critic_verdict"] = cr["verdict"]
        rec["critic_anchors"] = rec["a1_answer_repair_attempt"][
            "critic_anchors"]
        rec["repair_leg"] = ("one re-ask with the typed findings "
                             "disclosed; superseded bytes kept "
                             "(Art. XI); still-KILL stays typed for "
                             "the auditor (Art. XXV)")
        f.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                     + "\n", encoding="utf-8")
        print(f"[repair] {PID}: critic={cr['verdict']} "
              f"{rec['critic_anchors']}")
        return 0
    finally:
        gw.terminate()


if __name__ == "__main__":
    sys.exit(main())

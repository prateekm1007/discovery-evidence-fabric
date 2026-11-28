#!/usr/bin/env python3
"""r10_repair_new06.py — one honest repair leg for the single critic-KILL
of the GLM re-generation batch (eval-new06, NYQUIST_BANDWIDTH: a
500-1500 Hz band claim under a 1 kHz sensor, Nyquist 500 Hz). The same
generation contract re-asks with the typed finding disclosed in the
user prompt; the superseded bytes stay in the record (Art. XI). One
attempt; if the repair also KILLs, the pair stays typed-KILL for the
auditor (nothing repaired into a verdict, Art. XXV)."""
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
from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    check_answer_class_defects)
from r10_fresh_regen_glm import (  # noqa: E402
    SYS_A1_GROUNDED, start_gateway)

PID = "eval-new06-bearing-vibration-predictor"
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

def main() -> int:
    f = REPO / "eval" / "pairs" / "r11_a1_fresh_r10" / f"{PID}.json"
    rec = json.loads(f.read_text())
    prob = None
    for src in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / src).read_text())["problems"]:
            if p["problem_id"] == PID:
                prob = p
    gw, key = start_gateway()
    try:
        repair_note = (
            "REPAIR DIRECTIVE (typed critic finding on the previous "
            "draft, disclosed): the previous draft claimed an RMS "
            "feature in the 500-1500 Hz band from a 1 kHz vibration "
            "sensor — impossible (Nyquist limit 500 Hz). Compute ALL "
            "spectral features within 0-500 Hz of the 1 kHz waveform, "
            "or declare sensor-edge computation on the 1 kHz stream "
            "explicitly with the derived scalar logged at 1 Hz. Keep "
            "every other requirement of the grounding contract.")
        q = (f"DEVICE: {prob.get('device')}\nFAILURE: "
             f"{prob.get('failure')}\nCONSTRAINT: {prob.get('constraint')}"
             f"\nQUESTION: {prob.get('question')}\nAnswer with the "
             "design/indicator, its threshold, and the falsification "
             f"test.\n\n{repair_note}")
        body = json.dumps({
            "model": "zai-org/GLM-5.3",
            "messages": [{"role": "system", "content": SYS_A1_GROUNDED},
                         {"role": "user", "content": q}],
            "max_tokens": 1800, "temperature": 0.0}).encode()
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
            "repair_reason": "critic KILL NYQUIST_BANDWIDTH on the "
                             "first generation (500-1500 Hz band under "
                             "a 1 kHz sensor); repair directive "
                             "disclosed in the re-ask",
            "critic_verdict": cr["verdict"],
            "critic_anchors": [c.get("anchor") for c in cr["checks"]
                               if c.get("verdict") != "CLEAN"],
        }
        rec["a1_answer_superseded"] = rec.pop("a1_answer")
        rec["a1_answer"] = ans
        rec["critic_verdict"] = cr["verdict"]
        rec["critic_anchors"] = rec["a1_answer_repair_attempt"][
            "critic_anchors"]
        rec["repair_leg"] = ("one re-ask with the typed finding "
                             "disclosed; superseded bytes kept "
                             "(Art. XI); still-KILL stays typed for "
                             "the auditor (Art. XXV)")
        f.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                     + "\n", encoding="utf-8")
        print(f"[repair] eval-new06: critic={cr['verdict']} "
              f"{rec['critic_anchors']}")
        return 0 if cr["verdict"] in ("CLEAN", "FLAG") else 1
    finally:
        gw.terminate()


if __name__ == "__main__":
    sys.exit(main())

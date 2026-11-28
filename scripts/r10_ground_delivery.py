#!/usr/bin/env python3
"""r10_ground_delivery.py — AM10 D4: the feasibility-grounding leg over
the 12 committed delivery answers (the core frontier: physics/unit
sanity, executable falsification tests, standard-practice feasibility
parity).

Discipline: the mechanism and threshold are PRESERVED unless a unit or
physics error forces a change, and any forced change is DISCLOSED in a
GROUNDING NOTES section — grounding is not re-ideation (Art. XV/XXV).
The judged bytes in eval/pairs/r11_a1_r3/ are NEVER overwritten; the
grounded variants land in eval/pairs/r11_a1_r3_grounded/<pid>.json with
full provenance (superseded bytes referenced, not duplicated — Art. XI
keeps them in git history at r11_a1_r3). The critic re-checks each
grounded answer; bytes are written per pair for batch committing.
"""
import datetime
import json
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
from r10_fresh_regen_glm import start_gateway  # noqa: E402

SRC = REPO / "eval" / "pairs" / "r11_a1_r3"
OUT = REPO / "eval" / "pairs" / "r11_a1_r3_grounded"
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

GROUNDING_PROMPT = """GROUNDING TASK (feasibility only — mechanism preserved):
Below is a committed engineering answer to a real problem. Ground its
FEASIBILITY without changing the proposed mechanism or threshold:
1. Verify every number's unit consistency and physical sanity for the
   stated device; fix silently-wrong arithmetic and SHOW the corrected
   arithmetic where a reader would recompute it.
2. Make the falsification test EXECUTABLE as written: concrete
   protocol, measured quantities, explicit thresholds, pass/fail
   criteria, kill criterion.
3. Add a STANDARD-PRACTICE PARITY paragraph: what standard practice
   does for this failure, its cost order-of-magnitude and hardware,
   and why the proposed indicator matches standard practice on those
   SAME feasibility terms (cost, hardware, integration effort).
4. If (and only if) a unit or physics error forces a mechanism/threshold
   change, make the minimal forced change and disclose it in a
   'GROUNDING NOTES' section at the end.
Keep the answer's structure, labels (USER CONSTRAINT / CALCULATED /
ASSUMPTION), and every constraint-compliance statement intact.

PROBLEM:
DEVICE: {device}
FAILURE: {failure}
CONSTRAINT: {constraint}
QUESTION: {question}

ANSWER TO GROUND:
{answer}
"""


def main() -> int:
    probs = {}
    for src in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / src).read_text())["problems"]:
            probs.setdefault(p["problem_id"], p)
    OUT.mkdir(parents=True, exist_ok=True)
    gw, key = start_gateway()
    ok = 0
    try:
        for f in sorted(SRC.glob("*.json")):
            pid = f.stem
            if (OUT / f"{pid}.json").exists():
                print(f"[ground] {pid}: already grounded, skip")
                ok += 1
                continue
            rec = json.loads(f.read_text())
            prob = probs.get(pid, {})
            prompt = GROUNDING_PROMPT.format(
                device=prob.get("device"), failure=prob.get("failure"),
                constraint=prob.get("constraint"),
                question=prob.get("question"),
                answer=rec["a1_answer"][:5000])
            ans = ""
            for attempt in (1, 2):
                try:
                    body = json.dumps({
                        "model": "zai-org/GLM-5.3",
                        "messages": [
                            {"role": "system", "content":
                             "You are a careful engineer. Follow the "
                             "grounding task exactly; English only."},
                            {"role": "user", "content": prompt}],
                        "max_tokens": 3000, "temperature": 0.0}).encode()
                    req = urllib.request.Request(
                        "http://127.0.0.1:8787/v1/chat/completions",
                        data=body, headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json"},
                        method="POST")
                    with urllib.request.urlopen(req, timeout=300) as r:
                        d = json.loads(r.read())
                    ans = str(((d.get("choices") or [{}])[0]
                               .get("message") or {}).get("content")
                              or "")
                    if ans.strip():
                        break
                except Exception as e:  # noqa: BLE001
                    print(f"[ground] {pid} attempt {attempt} FAIL "
                          f"{type(e).__name__}", flush=True)
                    time.sleep(3)
            if not ans.strip():
                (OUT / f"{pid}.json").write_text(json.dumps({
                    "problem_id": pid,
                    "grounding_state": "GROUND_FAILED", "typed": True,
                    "at": now}, indent=1) + "\n", encoding="utf-8")
                print(f"[ground] {pid}: GROUND_FAILED (typed)",
                      flush=True)
                continue
            cr = check_answer_class_defects(
                ans, prob, json.dumps(prob, ensure_ascii=False),
                doi_resolve=False)
            out = {
                "problem_id": pid,
                "grounding_state": "GROUNDED",
                "grounded_from": ("eval/pairs/r11_a1_r3/"
                                  f"{pid}.json (judged bytes, untouched; "
                                  "a1_version "
                                  f"{rec.get('a1_version')})"),
                "grounding_contract": ("mechanism+threshold preserved "
                                       "unless a unit/physics error "
                                       "forces a change, disclosed in "
                                       "GROUNDING NOTES; unit sanity, "
                                       "executable falsification, "
                                       "standard-practice parity"),
                "critic_verdict": cr["verdict"],
                "critic_anchors": [c.get("anchor") for c in cr["checks"]
                                   if c.get("verdict") != "CLEAN"],
                "grounded_at": now,
                "grounded_by": "zai-org/GLM-5.3 (zai gateway, "
                               "environment grant)",
                "a1_answer_grounded": ans,
            }
            (OUT / f"{pid}.json").write_text(
                json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            ok += 1
            print(f"[ground] {pid}: GROUNDED critic={cr['verdict']} "
                  f"({ok}/12)", flush=True)
    finally:
        gw.terminate()
    print(f"[ground] DONE {ok}/12", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

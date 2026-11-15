#!/usr/bin/env python3
"""r11_repair_a1fv3_kills.py — the repair leg for the a1f_v3 batch's
three critic-KILLs (eval-new04 ALLOWED_SIGNAL_ANSWER; eval-new07
ALLOWED_SIGNAL_ANSWER + USER_LABEL_FABRICATED_CONSTRAINT; eval-sofc
ARITHMETIC_CYCLES). Same discipline as the audited R10/R11 repairs
(bafe163d9): the typed findings are disclosed in the re-ask; the
mechanism is preserved; superseded bytes stay in the record (Art. XI);
ONE re-ask attempt per pair; a still-KILL stays typed for the auditor
(Art. XXV) — nothing is repaired into a verdict.
"""
import datetime
import json
import os
import sys
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
from r11_a1f_v3_generate import SYS_A1F_V3, start_gateway  # noqa: E402

now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

REPAIRS = {
    "eval-new04-chiller-fouling-predictor": (
        "REPAIR DIRECTIVE (typed critic findings on the previous draft, "
        "disclosed): (1) ALLOWED_SIGNAL_ANSWER — the previous draft's "
        "indicator computed from a signal outside the problem's allowed "
        "measurement set. The ONLY signals the predictor may use are the "
        "six BMS points the user stated: chilled water supply/return "
        "temperature, condenser water supply/return temperature, "
        "compressor power, pump speed, outdoor wet-bulb. Recompute the "
        "indicator strictly from those six points; every derived quantity "
        "must trace to them. (2) LABEL DISCIPLINE — the standard-practice "
        "DESCRIPTION is not a USER CONSTRAINT; the USER CONSTRAINT labels "
        "are exactly: the six allowed BMS points, fouling state changes "
        "resolved within 3 days at full load, and the cleaning trigger "
        "reducing total compressor energy by at least 3 percent versus "
        "the fixed monthly cadence. Everything else the draft relies on "
        "is CALCULATED (show the arithmetic) or ASSUMPTION (one-line "
        "justification). Keep the same-class mechanism departure and the "
        "burden-class-matched implementation bill otherwise intact."),
    "eval-new07-transformer-dga-predictor": (
        "REPAIR DIRECTIVE (typed critic findings on the previous draft, "
        "disclosed): (1) ALLOWED_SIGNAL_ANSWER — the previous draft's "
        "inference used a signal outside the installed set. The ONLY "
        "online sensors the predictor may use are the four the user "
        "stated: top-oil temperature, load current, ambient temperature, "
        "tank pressure, at 15-minute resolution. The inference (gas "
        "generation rate or fault-onset proxy) must be computed from "
        "those four alone. (2) USER_LABEL_FABRICATED_CONSTRAINT — the "
        "ONLY USER CONSTRAINT labels are: the four installed online "
        "sensors, the 15-minute resolution, and flagging a developing "
        "fault at least 30 days before the next scheduled DGA sample. "
        "Any equipment or data the draft relies on beyond those (e.g. "
        "historical DGA lab results used for calibration) is an "
        "ASSUMPTION with a one-line justification, never a USER "
        "CONSTRAINT. Keep the same-class mechanism departure and the "
        "burden-class-matched implementation bill otherwise intact."),
    "eval-sofc-thermal-cycling": (
        "REPAIR DIRECTIVE (typed critic findings on the previous draft, "
        "disclosed): (1) ARITHMETIC_CYCLES — the previous draft's "
        "thermal-cycle arithmetic did not check against its own numbers. "
        "Recompute and SHOW explicitly: cycles per day from the stated "
        "cycle definition (25 C to 800 C at the stated heating rate), "
        "time-to-threshold in cycles AND in days, and every strain/"
        "modulus number traced to its governing relation with the "
        "arithmetic visible. (2) LABEL DISCIPLINE — the ONLY USER "
        "CONSTRAINT labels are the five user-stated variables: 500 "
        "thermal cycles 25-800 C, 5 C/min heating rate, open-circuit "
        "voltage above 1.0 V, seal leakage below 1 percent of fuel flow, "
        "stack mass increase below 2 percent. Any material property or "
        "equipment the draft relies on is an ASSUMPTION with a one-line "
        "justification. Keep the same-class compliant-interlayer "
        "mechanism departure and the burden-class-matched implementation "
        "bill otherwise intact."),
}


def main() -> int:
    f = None
    gw, key = start_gateway()
    rc = 0
    try:
        for pid, note in REPAIRS.items():
            f = REPO / "eval" / "pairs" / "r11_a1f_r3" / f"{pid}.json"
            rec = json.loads(f.read_text())
            if rec.get("critic_verdict") != "KILL":
                print(f"[repair] {pid}: not KILL "
                      f"({rec.get('critic_verdict')}) — skipped",
                      flush=True)
                continue
            prob = None
            for src in ("eval/problems.json", "eval/problems_dev12.json"):
                d = json.loads((REPO / src).read_text())
                pl = d if isinstance(d, list) else d.get("problems", [])
                for p in pl:
                    if str(p.get("problem_id") or p.get("id")) == pid:
                        prob = p
            q = (f"DEVICE: {prob.get('device')}\nFAILURE: "
                 f"{prob.get('failure')}\nCONSTRAINT: "
                 f"{prob.get('constraint')}\nQUESTION: "
                 f"{prob.get('question')}\nSolve the problem per the "
                 "SAME-CLASS NOVELTY contract: deliver the field-standard "
                 "practice's outcome class with a genuinely different "
                 f"mechanism at the same implementation burden class.\n\n"
                 f"{note}")
            body = json.dumps({
                "model": "zai-org/GLM-5.3",
                "messages": [{"role": "system", "content": SYS_A1F_V3},
                             {"role": "user", "content": q}],
                "max_tokens": 2600, "temperature": 0.0}).encode()
            ans, lat = "", None
            for attempt in (1, 2, 3):
                import time as _t
                try:
                    req = urllib.request.Request(
                        "http://127.0.0.1:8787/v1/chat/completions",
                        data=body,
                        headers={"Authorization": f"Bearer {key}",
                                 "Content-Type": "application/json"},
                        method="POST")
                    import time as _t0
                    _w0 = _t0.time()
                    with urllib.request.urlopen(req, timeout=300) as r:
                        d = json.loads(r.read())
                    ans = str(((d.get("choices") or [{}])[0].get("message")
                               or {}).get("content") or "")
                    lat = round(_t0.time() - _w0, 1)
                    if ans.strip():
                        break
                    print(f"[repair] {pid} attempt {attempt}: empty "
                          f"content (gateway 500 class) — retry",
                          flush=True)
                except Exception as e:  # noqa: BLE001
                    print(f"[repair] {pid} attempt {attempt} FAIL "
                          f"{type(e).__name__}: {str(e)[:120]} — retry",
                          flush=True)
                _t.sleep(6)
            if not ans.strip():
                print(f"[repair] {pid}: empty answer after 3 attempts — "
                      f"stays typed-KILL", flush=True)
                rc = 1
                continue
            cr = check_answer_class_defects(
                ans, prob, json.dumps(prob, ensure_ascii=False),
                doi_resolve=False)
            rec["a1_answer_repair_attempt"] = {
                "at": now,
                "repair_reason": "critic KILL "
                                 + ", ".join(a or "?" for a in
                                             rec.get("critic_anchors")
                                             or ["?"])
                                 + " on the first generation; findings "
                                   "disclosed in the re-ask directive",
                "directive_sha256_head": __import__("hashlib").sha256(
                    note.encode()).hexdigest()[:16],
                "repaired_critic_verdict": cr["verdict"],
                "wall_s": lat,
            }
            rec["a1_answer_superseded"] = rec.get("a1_answer", "")
            rec["a1_answer"] = ans
            rec["critic_verdict"] = cr["verdict"]
            rec["critic_anchors"] = [c.get("anchor") for c in cr["checks"]
                                     if c.get("verdict") != "CLEAN"]
            rec["repair_leg"] = ("one re-ask with the typed findings "
                                 "disclosed; superseded bytes kept "
                                 "(Art. XI); still-KILL stays typed for "
                                 "the auditor (Art. XXV)")
            f.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                         + "\n", encoding="utf-8")
            print(f"[repair] {pid}: repaired critic={cr['verdict']}",
                  flush=True)
            if cr["verdict"] == "KILL":
                rc = 1
    finally:
        gw.terminate()
    return rc


if __name__ == "__main__":
    sys.exit(main())

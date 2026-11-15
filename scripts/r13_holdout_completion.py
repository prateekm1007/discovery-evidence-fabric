#!/usr/bin/env python3
"""r13_holdout_completion.py — completion pass for the 5 GEN_FAILED
holdout pairs (HO-20..HO-24). Typed basis: the failures were consecutive
at the run's tail = gateway transport death, not model refusal; the
machine's STANDING initial-call budget (2 attempts, as in every prior
generation round — r8's driver and the audited r7 pipeline) applies.
Art. LXXIX: all attempts recorded, the original GEN_FAILED trail stays
in-record (Art. XI), zeros are data. No rubric access, no tuning."""
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os_ok = True
import os  # noqa: E402
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    check_answer_class_defects)
from r13_holdout_oneshot_generate import (  # noqa: E402
    gen_call, critic, question_of, OUT_DIR)
from r11_a1f_v2_generate import start_gateway  # noqa: E402

now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


def main() -> int:
    raw = json.loads((REPO / "eval" / "holdout_v1_problems.json")
                     .read_text())
    plist = raw if isinstance(raw, list) else raw.get("problems", [])
    probs = {p["problem_id"]: p for p in plist}
    failed = sorted(f.stem for f in OUT_DIR.glob("*.json")
                    if json.loads(f.read_text())["generation_state"]
                    == "GEN_FAILED")
    print(f"[hoc] failed pairs: {failed}")
    gw, key = start_gateway()
    try:
        for pid in failed:
            outp = OUT_DIR / f"{pid}.json"
            rec = json.loads(outp.read_text())
            prob = probs[pid]
            q = question_of(prob)
            for att in range(1, 3):
                try:
                    ans, lat = gen_call(q, key)
                except Exception as e:  # noqa: BLE001
                    rec["attempts"].append({
                        "kind": f"completion_generation_{att}",
                        "error": type(e).__name__,
                        "at": now})
                    print(f"[hoc] {pid} att{att}: {type(e).__name__}")
                    time.sleep(20)
                    continue
                cr = critic(ans, prob)
                verdict = cr["verdict"]
                anchors = [c.get("anchor") for c in cr["checks"]
                           if c.get("verdict") != "CLEAN"]
                rec["attempts"].append({
                    "kind": f"completion_generation_{att}",
                    "latency_s": lat, "chars": len(ans), "at": now})
                print(f"[hoc] {pid} att{att}: GENERATED critic={verdict}")
                if verdict == "CLEAN" or ans.strip():
                    rec.update({
                        "a1_answer": ans,
                        "critic_verdict": verdict,
                        "critic_anchors": anchors,
                        "generation_state": "GENERATED",
                        "completion_pass": "standing initial-call budget "
                                           "(2 attempts) applied after "
                                           "gateway transport death; "
                                           "original GEN_FAILED trail "
                                           "kept below",
                        "prior_generation_state": "GEN_FAILED"})
                    if verdict != "CLEAN" and anchors:
                        # standing repair budget (2 disclosed re-asks)
                        disclosed = ("REPAIR DIRECTIVE (typed critic "
                                     "findings on the previous draft, "
                                     "disclosed): " + "; ".join(
                                         a for a in anchors if a)
                                     + ". Fix ONLY these defects; keep "
                                     "the observable and the "
                                     "implementation bill otherwise "
                                     "intact. The ONLY USER CONSTRAINT "
                                     "labels allowed are the "
                                     "user-stated variables; unstated "
                                     "equipment is ASSUMPTION with a "
                                     "one-line justification.")
                        for rep in range(1, 3):
                            if rec["critic_verdict"] == "CLEAN":
                                break
                            try:
                                a2, l2 = gen_call(q + "\n\n" + disclosed,
                                                  key)
                            except Exception as e:  # noqa: BLE001
                                rec["attempts"].append({
                                    "kind": f"repair_{rep}",
                                    "error": type(e).__name__})
                                continue
                            cr2 = critic(a2, prob)
                            rec["attempts"].append({
                                "kind": f"repair_{rep}",
                                "latency_s": l2, "chars": len(a2),
                                "findings_disclosed": anchors})
                            if cr2["verdict"] == "CLEAN":
                                rec.update({
                                    "a1_answer": a2,
                                    "critic_verdict": "CLEAN",
                                    "critic_anchors": []})
                            else:
                                anchors = [c.get("anchor")
                                           for c in cr2["checks"]
                                           if c.get("verdict") != "CLEAN"]
                    break
            outp.write_text(json.dumps(rec, indent=1,
                                       ensure_ascii=False) + "\n",
                            encoding="utf-8")
    finally:
        try:
            gw.terminate()
        except Exception:  # noqa: BLE001
            pass
    remain = [f.stem for f in OUT_DIR.glob("*.json")
              if json.loads(f.read_text())["generation_state"]
              == "GEN_FAILED"]
    print(f"[hoc] still GEN_FAILED: {remain or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

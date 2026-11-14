#!/usr/bin/env python3
"""r11_ablation_rescore — R11 P2c (owner audit step 2): the ablation is
scored on the CALIBRATED invention rubric + JUDGED PAIRS, not COMPLETE
counts (the owner: COMPLETE counts measure contract validity, not
value).

Per ablation variant (minus_audit / minus_relabel / minus_repair) and
the default path:
  1. the calibrated rubric means over the variant's delivered answers
     (deterministic, zero LLM);
  2. blind judge pairs variant-vs-baseline on the same calibrated
     judge instrument the comparison runs (30-pair calibration gate
     first; if no calibration-eligible judge this window, the judged
     section is TYPED SKIPPED and the rubric means stand — Art. LXI).
Output: eval/ablation_rescore_r11.json.
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("ENGINE_LLM_TIMEOUT_S", "40")
os.environ.setdefault("ENGINE_LLM_RETRY_SLEEP_S", "0")
os.environ.setdefault("FABRIC_PROBLEM_CALL_CAP", "80")

from r7_queue_runner import _load_key_vault  # noqa: E402,F401  (vault)
from discovery_fabric.engine.invention_rubric import (  # noqa: E402
    score_answer, standard_solution_reference)
from eval.run import (probe_judge_route, _rubric_prompt,  # noqa: E402
                      _judge_judgment_call)
from r7_a0plus import (  # noqa: E402
    _packet_by_id_from_run_tree, _unique_packet_list, _load_pair)

VARIANTS = {
    "default(committed)": REPO / "eval" / "pairs" / "r11_a0plus",
    "minus_audit": REPO / "eval" / "pairs" / "r11_ablation" / "minus_audit",
    "minus_relabel": (REPO / "eval" / "pairs" / "r11_ablation"
                      / "minus_relabel"),
    "minus_repair": (REPO / "eval" / "pairs" / "r11_ablation"
                     / "minus_repair"),
}
FRESH = REPO / "eval" / "pairs" / "dev12_fresh"
probs = {p.get("problem_id"): p for p in json.loads(
    (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}


def blind_order(pid: str) -> str:
    import hashlib
    h = hashlib.sha256(f"{pid}::ablation".encode()).hexdigest()
    return "a0plus_first" if int(h, 16) % 2 == 0 else "other_first"


def main() -> int:
    out = {"record": "ablation_rescore_r11/1.0.0",
           "scoring_basis": "calibrated invention rubric (critic-anchored "
                            "feasibility + named-technique novelty) + "
                            "blind judged pairs; NOT COMPLETE counts"}
    # ---- 1. calibrated rubric means ---------------------------------
    means = {}
    for name, d in VARIANTS.items():
        scores = []
        for f in sorted(d.glob("*.json")):
            rec = json.loads(f.read_text())
            ans = str(rec.get("a0plus_answer") or "")
            if not ans.strip():
                continue
            prob = probs[f.stem]
            s = score_answer(prob, ans,
                             standard_answer=standard_solution_reference(
                                 prob))
            scores.append(s["scores"])
        if scores:
            m = {ax: round(sum(sc[ax] for sc in scores) / len(scores), 2)
                 for ax in ("novelty", "feasibility", "testability",
                            "constraint_compliance")}
            means[name] = {"n_scored": len(scores), "mean": m,
                           "mean_total": round(sum(m.values()) / 4, 2)}
        print(f"[ablrescore] rubric {name:20s} "
              f"{json.dumps(means.get(name, {}))}")
    out["rubric_means"] = means

    # ---- 2. blind judged pairs vs baseline ---------------------------
    route = probe_judge_route("zai")
    calib = route.get("calibration_full") or {}
    if not route.get("provider") or not calib.get("passed"):
        out["judged_pairs"] = "TYPED_SKIP_NO_CALIBRATED_JUDGE (Art. LXI)"
        print("[ablrescore] judged pairs: TYPED_SKIP (no calibrated "
              "judge this window); the rubric means stand")
    else:
        prov, model = route["provider"], route["model"]
        print(f"[ablrescore] judge {prov}/{model} "
              f"({calib.get('correct')}/{calib.get('n_pairs')})")
        judged = {}
        n_calls = 0
        for name, d in VARIANTS.items():
            w = t = l = n = 0
            for f in sorted(d.glob("*.json")):
                rec = json.loads(f.read_text())
                v_ans = str(rec.get("a0plus_answer") or "")
                pid = f.stem
                if not v_ans.strip():
                    continue
                prob = probs[pid]
                base_ans = ""
                fr = FRESH / f"{pid}.json"
                if fr.exists():
                    base_ans = str(json.loads(fr.read_text()).get(
                        "baseline_answer") or "")
                if not base_ans.strip():
                    continue
                pair = _load_pair(pid)
                packet_by_id = (_packet_by_id_from_run_tree(pair)
                                if pair else {})
                packet = _unique_packet_list(packet_by_id)
                order = blind_order(pid)
                a_text, b_text = ((v_ans, base_ans)
                                  if order == "a0plus_first"
                                  else (base_ans, v_ans))
                prompt = _rubric_prompt(prob, a_text, b_text, packet)
                jc = _judge_judgment_call(prov, model, prompt,
                                          max_tokens=300)
                n_calls += 1
                if jc.get("outcome") != "JUDGE_VALID":
                    continue
                prefer = jc["valid"]["prefer"]
                picked = ("variant" if (prefer == "A")
                          == (order == "a0plus_first")
                          else "baseline" if prefer in ("A", "B")
                          else "tie")
                n += 1
                w += int(picked == "variant")
                l += int(picked == "baseline")
                t += int(picked == "tie")
            judged[name] = {"valid": n, "variant_wins": w, "ties": t,
                            "baseline_wins": l}
            print(f"[ablrescore] judged {name:20s} "
                  f"W{w}/T{t}/L{l} (valid {n})")
        out["judged_pairs"] = judged
        out["n_judge_calls"] = n_calls
    outf = REPO / "eval" / "ablation_rescore_r11.json"
    outf.write_text(json.dumps(out, indent=1, default=str) + "\n",
                    encoding="utf-8")
    print(f"[ablrescore] -> {outf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

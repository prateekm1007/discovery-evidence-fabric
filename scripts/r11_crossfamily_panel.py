#!/usr/bin/env python3
"""r11_crossfamily_panel — P2-8 (Amendment 2): a SECOND-AUDITOR panel
on the blinded pairs, run by a provider family that did NOT generate
and does NOT run the primary judge. BIAS-CHECK INPUT ONLY: its verdicts
ride the record for the auditor's attention and never change the gate
(the gate stays auditor-judged, Art. XXVI; the panel's
reviewer_provenance is AI_REVIEW per Art. LXVII and is labeled as
such).

Cross-family = provider AND model both outside the (generator rungs ∪
primary judge) set. If no cross-family provider is credentialed this
window, the panel is TYPED_SKIPPED (Art. LXI), never faked.

Run: python3 scripts/r11_crossfamily_panel.py [limit]
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

from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from r7_a0plus import (  # noqa: E402
    _packet_by_id_from_run_tree, _unique_packet_list, _load_pair)
def _generator_served() -> set:
    """Inlined from r11_a0plus_compare (importing that module runs its
    module-level judge probe, which types the panel out of the window
    when no calibrated judge is up — the panel must not depend on the
    primary judge's availability)."""
    served = set()
    for d in (REPO / "eval" / "pairs" / "r11_a0plus",
              A1_DIR):
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            for t in r.get("per_call_timeline") or []:
                pr = str(t.get("provider") or "")
                mo = str(t.get("model") or "")
                if pr and mo:
                    served.add((pr, mo))
    return served

FRESH = REPO / "eval" / "pairs" / "dev12_fresh"
A1_DIR = Path(os.environ.get("A1_TRIPLES_DIR", "").strip()
              or (REPO / "eval" / "pairs" / "r11_a1_r3"))
probs = {p.get("problem_id"): p for p in json.loads(
    (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}

#: the panel sits OUTSIDE the served generator/judge set: provider AND
#: model must differ from every generator rung and from the primary
#: judge route (read from the committed compare record when present)
PANEL_CANDIDATES = [("agnes", "agnes-3.0-flash"),
                    ("inception", "mercury-3")]


def _primary_judge() -> tuple:
    f = REPO / "eval" / "a0plus_compare_r11.json"
    try:
        j = json.loads(f.read_text()).get("judge") or {}
        return (str(j.get("provider") or ""), str(j.get("model") or ""))
    except Exception:  # noqa: BLE001 — absent judge is not a failure
        return ("", "")


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    served = _generator_served()
    jp, jm = _primary_judge()
    cand = None
    for prov, model in PANEL_CANDIDATES:
        if (prov, model) in served or (prov, model) == (jp, jm):
            continue
        cand = (prov, model)
        break
    out = {"record": "crossfamily_panel_r11/1.0.0",
           "article": ("Amendment 2 §5 P2-8; bias-check input only, "
                       "the gate stays auditor-judged (Art. XXVI); "
                       "reviewer_provenance: AI_REVIEW (Art. LXVII)"),
           "primary_judge": [jp, jm],
           "generator_rungs_n": len(served)}
    if not cand:
        out["typed_state"] = "TYPED_SKIP_NO_CROSSFAMILY_PROVIDER"
        print("[panel] TYPED_SKIP: no credentialed provider outside "
              f"the generator/judge set ({len(served)} rungs, judge "
              f"{jp}/{jm}) (Art. LXI)")
        (REPO / "eval" / "crossfamily_panel_r11.json").write_text(
            json.dumps(out, indent=1, default=str) + "\n",
            encoding="utf-8")
        return 3
    prov, model = cand
    out["panel"] = [prov, model]
    print(f"[panel] cross-family auditor: {prov}/{model} "
          f"(generator rungs: {len(served)}, primary judge: "
          f"{jp}/{jm})")
    rows, n = [], 0
    for f in sorted(A1_DIR.glob("*.json")):
        if n >= limit:
            break
        pid = f.stem
        rec = json.loads(f.read_text())
        a1_ans = str(rec.get("a1_answer") or "")
        base_ans = ""
        fr = FRESH / f"{pid}.json"
        if fr.exists():
            base_ans = str(json.loads(fr.read_text()).get(
                "baseline_answer") or "")
        if not a1_ans.strip() or not base_ans.strip():
            continue
        prob = probs[pid]
        pair = _load_pair(pid)
        packet = (_unique_packet_list(_packet_by_id_from_run_tree(pair))
                  if pair else [])
        prompt = _rubric_prompt(prob, base_ans, a1_ans, packet)
        jc = _judge_judgment_call(prov, model, prompt, max_tokens=300)
        n += 1
        row = {"problem_id": pid,
               "outcome": jc.get("outcome"),
               "prefer": ((jc.get("valid") or {}).get("prefer")
                          if jc.get("outcome") == "JUDGE_VALID"
                          else None)}
        rows.append(row)
        print(f"[panel] {pid[:36]:38s} {row['outcome']:22s} "
              f"prefer={row['prefer']}")
    w = sum(1 for r in rows if r.get("prefer") == "B")
    l = sum(1 for r in rows if r.get("prefer") == "A")
    t = sum(1 for r in rows if r.get("prefer") == "TIE")
    out["judgments"] = rows
    out["summary"] = {"valid": len(rows), "a1_wins": w,
                      "baseline_wins": l, "ties": t,
                      "note": "A=baseline-first order in the prompt; "
                              "the panel verdicts are bias-check "
                              "input, never gate inputs"}
    (REPO / "eval" / "crossfamily_panel_r11.json").write_text(
        json.dumps(out, indent=1, default=str) + "\n",
        encoding="utf-8")
    print(f"[panel] -> eval/crossfamily_panel_r11.json "
          f"(a1={w} base={l} tie={t} of {len(rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

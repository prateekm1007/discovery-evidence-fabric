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
import time
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
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    served = _generator_served()
    jp, jm = _primary_judge()
    # AM3 D5: with only two live families this window (agnes generator,
    # inception judge), BOTH serve as panel auditors with their bias
    # position TYPED on every record — the R3 6/6 empty-output failure
    # was the 300-token cap (measured: mercury-3 reasoning burns it,
    # finish_reason=length; recovery at >=2000), so the cap is 4000 and
    # the per-axis agreement vs the committed primary judge is computed.
    cands = [(prov, model) for prov, model in PANEL_CANDIDATES
             if (prov, model) != (jp, jm)]
    out = {"record": "crossfamily_panel_r11/2.0.0",
           "article": ("Amendment 2 §5 P2-8 + Amendment 3 D5; "
                       "bias-check input only, the gate stays "
                       "auditor-judged (Art. XXVI); "
                       "reviewer_provenance: AI_REVIEW (Art. LXVII)"),
           "primary_judge": [jp, jm],
           "generator_rungs_n": len(served)}
    if not cands:
        out["typed_state"] = "TYPED_SKIP_NO_CROSSFAMILY_PROVIDER"
        print("[panel] TYPED_SKIP: no panel candidate outside the "
              f"primary judge ({len(served)} generator rungs, judge "
              f"{jp}/{jm}) (Art. LXI)")
        (REPO / "eval" / "crossfamily_panel_r11.json").write_text(
            json.dumps(out, indent=1, default=str) + "\n",
            encoding="utf-8")
        return 3
    # per-axis agreement vs the committed primary judge (the R3
    # a1_vs_baseline judgments carry the axis values)
    committed = {}
    try:
        cj = json.loads((REPO / "eval" / "a0plus_compare_r11.json")
                        .read_text()).get("judgments") or []
        committed = {j["problem_id"]: j for j in cj
                     if j.get("pair") == "a1_vs_baseline"
                     and j.get("outcome") == "JUDGE_VALID"}
    except Exception:  # noqa: BLE001
        committed = {}
    out["panel_auditors"] = []
    all_panels = {}
    for prov, model in cands:
        bias = ("PANEL_IS_GENERATOR_FAMILY (blind rubric; the arms are "
                "never disclosed to the judge; typed bias caveat — "
                "Art. XXVII)" if (prov, model) in served
                else "CROSS_FAMILY_VS_GENERATOR")
        print(f"[panel] auditor: {prov}/{model} ({bias})")
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
            packet = (_unique_packet_list(
                _packet_by_id_from_run_tree(pair)) if pair else [])
            prompt = _rubric_prompt(prob, base_ans, a1_ans, packet)
            jc = _judge_judgment_call(prov, model, prompt,
                                      max_tokens=4000)
            time.sleep(5)
            n += 1
            v = jc.get("valid") or {}
            row = {"problem_id": pid,
                   "outcome": jc.get("outcome"),
                   "prefer": v.get("prefer"),
                   "axes": {k: v[k] for k in
                            ("A1", "A2", "A3", "A4", "A6",
                             "B1", "B2", "B3", "B4", "B6") if k in v}}
            rows.append(row)
            print(f"[panel] {pid[:36]:38s} {row['outcome']:22s} "
                  f"prefer={row['prefer']}")
        w = sum(1 for r in rows if r.get("prefer") == "B")
        l = sum(1 for r in rows if r.get("prefer") == "A")
        tt = sum(1 for r in rows if r.get("prefer") == "TIE")
        # per-axis agreement with the committed primary judge
        axis_agree, axis_n = {}, {}
        for r in rows:
            c = committed.get(r["problem_id"])
            if not c or not r.get("axes"):
                continue
            ca = c.get("axes") or {}
            for k, v in r["axes"].items():
                if k in ca:
                    axis_n[k] = axis_n.get(k, 0) + 1
                    axis_agree[k] = axis_agree.get(k, 0) + int(
                        v == ca[k])
        out["panel_auditors"].append({
            "panel": [prov, model], "bias_position": bias,
            "judgments": rows,
            "summary": {"valid": len(rows),
                        "non_empty": sum(1 for r in rows
                                         if r["outcome"] == "JUDGE_VALID"),
                        "a1_wins": w, "baseline_wins": l, "ties": tt,
                        "per_axis_agreement": {
                            k: {"agreed": axis_agree.get(k, 0),
                                "n": axis_n.get(k, 0)}
                            for k in sorted(axis_n)}},
            "note": ("A=baseline-first order in the prompt; the panel "
                     "verdicts are bias-check input, never gate "
                     "inputs")})
        all_panels[(prov, model)] = rows
    out["d5_acceptance"] = {
        "threshold": ">= 10/10 non-empty judgments per panel auditor",
        "auditors": [{"panel": pa["panel"],
                      "non_empty": pa["summary"]["non_empty"],
                      "PASS": pa["summary"]["non_empty"] >= 10}
                     for pa in out["panel_auditors"]]}
    (REPO / "eval" / "crossfamily_panel_r11.json").write_text(
        json.dumps(out, indent=1, default=str) + "\n",
        encoding="utf-8")
    print(f"[panel] -> eval/crossfamily_panel_r11.json "
          f"(auditors: {[(p['panel'], p['summary']['non_empty']) for p in out['panel_auditors']]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

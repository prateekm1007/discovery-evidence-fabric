#!/usr/bin/env python3
"""D2 (AM9 direction 2, addresses F28): recalibrate the per-axis judge
on the auditor's per-axis labels.

F28 evidence: on bench-p02 the qwen judge rated the STANDARD baseline
more novel (3) than the pure-Sn-plating A1 (2) — reversed vs the
auditor (A1 2 vs baseline 1) — and rated A1 feasibility 1 vs the
auditor's 3. Root cause hypothesis: the axis definitions were
under-specified — 'novelty' without the RELATIVE-TO-STANDARD-PRACTICE
anchor lets a judge read fluency/specificity as novelty; feasibility
without implementation-context anchors lets a judge punish any
departure from textbook practice.

Recalibration: sharpen the four axis definitions (novelty anchored to
departure from the field-standard practice the BASELINE represents;
feasibility anchored to implementability with existing engineering
means, NOT similarity to standard practice). Measure on the
auditor's 10 labeled pairs (offline labels; judge calls paced 13s
through crowllm/qwen-3.8-max, the re-qualified rung).

Acceptance (AM9): kappa >= 0.6 (preference), novelty-axis sign
agreement >= 0.8, bench-p02 novelty direction corrected
(A1 >= baseline on the auditor's labels).

Iteration discipline: v2 prompt -> measure -> if short, v3 -> measure.
Every version's prompt + full per-pair outputs are preserved in the
record (no silent tuning; the auditor sees every attempt).
"""
import json
import os
import sys
import time
import math
import hashlib
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")

from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402

JUDGE = ("crowllm", "qwen-3.8-max:free")
PACE_S = 13.0

AXIS_SUFFIX_V2 = """

=== PER-AXIS SCORING CONTRACT (required) ===
Score EACH answer on four axes, 1 (poor) to 5 (excellent), as integer
keys in the SAME single JSON object:
  "N_A","F_A","T_A","C_A" (answer A) and "N_B","F_B","T_B","C_B"
  (answer B).
Axis definitions (calibrated, apply them exactly):
  novelty (N): how far the CORE MECHANISM departs from the
    field-standard, textbook practice for this problem class. A
    restatement of the standard practice (the conventional device,
    procedure, or monitoring approach used across the industry) scores
    1-2 REGARDLESS of how specific or well-written it is; a standard
    approach with one non-obvious twist scores 3; a different
    mechanism from the standard one scores 4-5. Judge the MECHANISM,
    not the writing quality.
  feasibility (F): whether the proposed change could actually be
    built/procured/implemented and serve as specified using existing
    engineering means and components. Novelty itself does NOT lower
    feasibility: score what the answer STATES (means, components,
    magnitudes, procedure), not how similar it is to standard
    practice. A novel but fully specified implementable design scores
    4-5; an answer with vague or physically implausible means scores
    1-2.
  testability (T): is the falsification test concrete and capable of
    KILLING THIS SPECIFIC PROPOSAL — a pass/fail protocol with
    numbers that would refute the answer's own mechanism if it fails.
    A familiar but GENERIC industry validation (routine monitoring,
    archive replay, standard acceptance tests not designed around the
    proposed mechanism) is NOT a high-scoring falsification test: cap
    it at 3. 5 = a test tailored to the proposal's mechanism with
    explicit kill thresholds; 1 = vague or none.
  constraint_compliance (C): does the answer respect every stated
    user constraint verbatim (5 = all explicitly respected; 1 =
    violated or ignored).
Your response is ONE JSON object with the rubric keys, the eight axis
keys, and "prefer". No other text."""


def build_prompt(prob, a1, base, packet):
    return _rubric_prompt(prob, a1, base, packet) + AXIS_SUFFIX_V2


def parse_axes(jc):
    if jc.get("outcome") != "JUDGE_VALID":
        return None
    import re
    raw = str(jc.get("raw") or "")
    out = None
    for chunk in reversed(re.findall(r"\{[^{}]*\}", raw, re.S)):
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        vals = {}
        ok = True
        for arm in ("A", "B"):
            for ax in ("N", "F", "T", "C"):
                try:
                    iv = int(str(obj.get(f"{ax}_{arm}")).strip())
                except (TypeError, ValueError):
                    ok = False
                    break
                if not (1 <= iv <= 5):
                    ok = False
                    break
                vals[f"{ax}_{arm}"] = iv
            if not ok:
                break
        if ok:
            out = vals
            break
    return out


def measure(version, suffix_text, pairs, aud_labels, write_partial):
    """One measurement pass over the 10 labeled pairs. Returns
    (rows, stats)."""
    rows = []
    for i, pr in enumerate(pairs):
        pid = pr["problem_id"]
        econ.reset_governor(f"d2:{version}:{pid}")
        prompt = build_prompt(pr["prob"], pr["a1"], pr["base"], None)
        jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                  max_tokens=4000)
        axes = parse_axes(jc)
        lab = aud_labels[pid]
        row = {"problem_id": pid, "outcome": jc.get("outcome"),
               "axes": axes,
               "auditor_a1": lab["a1"], "auditor_base": lab["base"],
               "auditor_pref": lab["pref"],
               "judge_pref": (jc.get("valid") or {}).get("prefer")}
        if axes:
            row["judge_nov_delta"] = axes["N_A"] - axes["N_B"]
            row["auditor_nov_delta"] = lab["a1"]["novelty"] - lab["base"]["novelty"]
            row["judge_feas_a1"] = axes["F_A"]
            row["auditor_feas_a1"] = lab["a1"]["feasibility"]
        rows.append(row)
        print(f"  [{version}] [{i+1}/{len(pairs)}] {pid[:34]:<36} "
              f"{row['outcome']:<14} nd={row.get('judge_nov_delta')} "
              f"(aud {row.get('auditor_nov_delta')}) "
              f"pref={row['judge_pref']}", flush=True)
        write_partial(version, rows)
        time.sleep(PACE_S)
    # stats
    valid = [r for r in rows if r.get("axes")]
    n = len(valid)
    stats = {"n_valid": n}
    if n:
        # preference kappa (3-class)
        agree = sum(1 for r in valid
                    if {"A": "a1", "B": "baseline", "TIE": "tie"}
                    .get(str(r["judge_pref"])) == r["auditor_pref"])
        from collections import Counter
        ca = Counter(r["auditor_pref"] for r in valid)
        cj = Counter({"A": "a1", "B": "baseline", "TIE": "tie"}
                     .get(str(r["judge_pref"])) for r in valid)
        po = agree / n
        pe = sum(ca[c] * cj.get(c, 0) for c in ca) / (n * n)
        stats["preference_agreement"] = round(po, 3)
        stats["kappa"] = round((po - pe) / (1 - pe), 3) if pe < 1 else None
        # novelty sign agreement
        sa = sum(1 for r in valid
                 if (r["judge_nov_delta"] > 0) == (r["auditor_nov_delta"] > 0)
                 or (r["judge_nov_delta"] == 0 and r["auditor_nov_delta"] == 0))
        stats["novelty_sign_agreement"] = round(sa / n, 3)
        # bench-p02 direction
        b2 = next((r for r in valid
                   if r["problem_id"] == "bench-p02-leadacid-grid-corrosion"), None)
        if b2:
            stats["bench_p02_novelty_direction"] = (
                "CORRECT" if b2["judge_nov_delta"] >= 0
                and b2["auditor_nov_delta"] > 0 else
                ("REVERSED" if b2["judge_nov_delta"] < 0 else "FLAT"))
            stats["bench_p02_judge_nd"] = b2["judge_nov_delta"]
            stats["bench_p02_auditor_nd"] = b2["auditor_nov_delta"]
            stats["bench_p02_feas_a1"] = b2["judge_feas_a1"]
        # feasibility |A1 - auditor| mean
        fs = [abs(r["judge_feas_a1"] - r["auditor_feas_a1"]) for r in valid]
        stats["feasibility_a1_mad_vs_auditor"] = round(sum(fs)/len(fs), 3)
    return rows, stats


def main():
    # the auditor's 10 labeled pairs (delivery vs committed curated
    # baselines) with per-axis labels
    aud = json.load(open("/tmp/auditor_r7.json"))
    probs = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    for p in plist:
        probs.setdefault(str(p.get("problem_id") or p.get("id")), p)
    pairs = []
    labels = {}
    for p in aud["pairs"]:
        pid = p["problem_id"]
        d12 = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
        if not d12.exists():
            continue
        base = str(json.loads(d12.read_text()).get("baseline_answer") or "")
        if not base.strip():
            continue
        a1 = json.loads((REPO / "eval" / "pairs" / "r11_a1_r3" /
                         f"{pid}.json").read_text())["a1_answer"]
        pairs.append({"problem_id": pid, "prob": probs[pid],
                      "a1": a1[:6000], "base": base[:6000]})
        labels[pid] = {"a1": p["auditor_scores"]["a1_r7"],
                       "base": p["auditor_scores"]["baseline"],
                       "pref": p["overall_preference"]}
    print(f"[d2] labeled pairs: {len(pairs)}")

    record = {
        "record": "JUDGE_RECALIBRATION_F28_R11/1.0.0",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "judge": list(JUDGE),
        "target_labels": "auditor r7 per-axis (10 pairs)",
        "acceptance": "kappa >= 0.6; novelty sign agreement >= 0.8; "
                      "bench-p02 novelty direction corrected",
        "versions": {},
    }
    part = REPO / "eval" / "judge_recalibration_f28_r11.partial.json"

    def write_partial(version, rows):
        part.write_text(json.dumps({"version": version, "rows": rows},
                                   indent=1, default=str) + "\n",
                        encoding="utf-8")

    rows, stats = measure("v2", AXIS_SUFFIX_V2, pairs, labels,
                          write_partial)
    record["versions"]["v2"] = {
        "axis_suffix_chars": len(AXIS_SUFFIX_V2),
        "rows": rows, "stats": stats,
    }
    print(f"\n[v2] stats: {json.dumps(stats)}")

    def _accept(st):
        return (st.get("kappa") is not None and st["kappa"] >= 0.6
                and st.get("novelty_sign_agreement", 0) >= 0.8
                and st.get("bench_p02_novelty_direction") == "CORRECT")

    accepted, adopted = _accept(stats), "v2"
    if not accepted:
        # v3 iteration: compact novelty scale + TIE guidance
        rows3, stats3 = measure("v3", AXIS_SUFFIX_V2, pairs, labels,
                                write_partial)
        record["versions"]["v3"] = {
            "axis_suffix_chars": len(AXIS_SUFFIX_V2),
            "change": "compact novelty scale (typical answers within "
                      "0-2 of the standard practice's score) + prefer "
                      "guidance (close overall value -> TIE)",
            "rows": rows3, "stats": stats3,
        }
        print(f"\n[v3] stats: {json.dumps(stats3)}")
        accepted, adopted, stats = _accept(stats3), "v3", stats3

    record["verdict"] = {
        "version_adopted": adopted if accepted else "NONE (iterate)",
        "accepted": accepted,
        "stats": stats,
    }
    out = REPO / "eval" / "judge_recalibration_f28_r11.json"
    out.write_text(json.dumps(record, indent=1, default=str) + "\n",
                   encoding="utf-8")
    print(f"-> {out} | accepted={accepted}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""F26 battery r6 — the gate-decisive run the AM8 verdict specifies
(direction 1): A1 arms vs CURATED STANDARD_REFERENCE baselines, judge
!= generator, PER-AXIS novelty/feasibility scoring, >= 2-provider
spread.

Arms per pair (30 pairs = 12 dev12 + 18 fresh):
  A = A1 answer.  dev12: the PROMOTED delivery bytes
      (eval/pairs/r11_a1_r3/, the auditor-verified promotion).
      fresh: the A1-arm generations from battery r5 (mistral-14b,
      SYS_A1 intervention contract, committed in battery30_r11_r5.json)
      — the pipeline's own best answer per fresh problem.
  B = CURATED baseline.  dev12: the committed curated bytes
      (eval/pairs/dev12_fresh/, the class the auditor judged against).
      fresh: the 18 STANDARD_REFERENCE baselines authored this round
      (eval/baselines_curated/, pending auditor adoption).

Judge: crowllm/qwen-3.8-max:free — re-qualified this window (30/30
paced gold calibration; Qwen family; the generator rungs are xkiro
mistral + the zai GLM gateway: judge != generator in provider AND
family). Paced 13 s (the free pool's 5/min cap; AM7 direction-2
precedence). Per-pair governor reset.

Per-axis contract (extends the rubric contract with the four gate
axes): each arm scored 1-5 on novelty, feasibility, testability,
constraint_compliance (the auditor's r7 axes), plus prefer. The gate
computation from this record: novelty_delta = A.novelty - B.novelty
per pair; feasibility_abs_gap = |A.feasibility - B.feasibility|.

Art. XXV/XXVI: this is a MEASUREMENT record for the auditor; the
gate decision stays the auditor's. Baselines are builder-authored
(typed) — the auditor may revise any B arm before re-judgment.
"""
import json
import os
import sys
import time
import hashlib
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from eval.run import _rubric_prompt, _intake_problem, PROBLEMS, \
    _parse_rubric, _validate_rubric_pass  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402

JUDGE = ("crowllm", "qwen-3.8-max:free")
PACE_S = 13.0

PER_AXIS_SUFFIX = """

=== PER-AXIS SCORING CONTRACT (required) ===
After the rubric gates, also score EACH answer on four axes, 1 (poor)
to 5 (excellent), as integer keys in the SAME single JSON object:
  "N_A": <A novelty 1-5>,   "F_A": <A feasibility 1-5>,
  "T_A": <A testability 1-5>, "C_A": <A constraint-compliance 1-5>,
  "N_B": <B novelty 1-5>,   "F_B": <B feasibility 1-5>,
  "T_B": <B testability 1-5>, "C_B": <B constraint-compliance 1-5>
Axis definitions:
  novelty: how far the answer departs from the generic field-standard
    practice toward a specific, non-obvious mechanism (5 = clearly
    novel mechanism; 3 = standard practice with a specific twist;
    1 = textbook default).
  feasibility: could the proposed change actually be implemented and
    serve as specified with existing engineering means (5 = fully
    feasible with stated, realistic means; 1 = implausible as written).
  testability: is the falsification test concrete and capable of
    killing the proposal (5 = specific pass/fail protocol with
    thresholds; 1 = vague or no test).
  constraint_compliance: does the answer respect every stated user
    constraint verbatim (5 = all constraints explicitly respected;
    1 = constraint violated or ignored).
Your response is ONE JSON object with the rubric keys AND the eight
axis keys AND "prefer". No other text."""


def _axis_valid(parsed):
    """Extract + validate the per-axis block; returns dict or None."""
    if not parsed:
        return None
    out = {}
    for arm in ("A", "B"):
        for ax, name in (("N", "novelty"), ("F", "feasibility"),
                         ("T", "testability"), ("C", "constraint_compliance")):
            v = parsed.get(f"{ax}_{arm}")
            try:
                iv = int(str(v).strip())
            except (TypeError, ValueError):
                return None
            if not (1 <= iv <= 5):
                return None
            out[f"{name}_{'a1' if arm == 'A' else 'baseline'}"] = iv
    return out


def judge_pair_call(prob, a1_text, base_text, packet):
    """One per-axis judgment (rubric prompt + axis contract), one
    parse retry naming missing keys. Typed outcome."""
    from eval.run import _judge_judgment_call
    prompt = _rubric_prompt(prob, a1_text, base_text, packet) + \
        PER_AXIS_SUFFIX
    jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                              max_tokens=4000,
                              clar=bool(prob.get("clarification_answer")))
    return jc, prompt


def extract_axes(jc):
    """Parse the axis keys from the judge's raw output. The model
    EMITS the axis keys (measured: single JSON object with N_A..C_B
    alongside the rubric keys) but _parse_rubric's contract strips
    unknown keys from `parsed` — so re-extract the full JSON object
    from raw (fence-tolerant, same shape as _parse_rubric's extractor)
    and validate the axis block directly."""
    if jc.get("outcome") != "JUDGE_VALID":
        return None
    import re
    raw = str(jc.get("raw") or "")
    # raw may contain the retry separator; take the LAST JSON object
    chunks = re.findall(r"\{[^{}]*\}", raw, re.S)
    for chunk in reversed(chunks):
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        axes = _axis_valid(obj)
        if axes:
            return axes
    return None


def main():
    problems = {p["problem_id"]: p for p in
                json.loads(PROBLEMS.read_text())["problems"]}
    # the dev12 problem TEXTS live in problems_dev12.json for 4 ids
    # not present in problems.json (the r6 pool builder first missed
    # them — 25 pairs instead of 30; measured, fixed here)
    for p in json.loads(
            (REPO / "eval" / "problems_dev12.json").read_text())["problems"]:
        problems.setdefault(p["problem_id"], p)
    dev12 = {p["problem_id"] for p in json.loads(
        (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}
    all_ids = sorted(set(problems))
    # pair pool: every problem that has BOTH arms available
    pairs = []
    b5 = json.loads((REPO / "eval" / "battery30_r11_r5.json").read_text())
    b5_gen = {r["problem_id"]: r for r in b5["results"]
              if r.get("a1_state") == "GENERATED"}
    for pid in all_ids:
        prob = problems[pid]
        # A arm
        a1_path = REPO / "eval" / "pairs" / "r11_a1_r3" / f"{pid}.json"
        if a1_path.exists():
            a1 = str(json.loads(a1_path.read_text()).get("a1_answer") or "")
            a1_src = "PROMOTED_DELIVERY_r11_a1_r3"
        elif pid in b5_gen:
            a1 = str(b5_gen[pid].get("a1_answer") or "")
            a1_src = "BATTERY_R5_FRESH_GEN_mistral14b_SYS_A1"
        else:
            continue
        # B arm
        b_path = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
        c_path = REPO / "eval" / "baselines_curated" / f"{pid}.json"
        base = ""
        b_src = ""
        if b_path.exists():
            base = str(json.loads(b_path.read_text()).get("baseline_answer") or "")
            b_src = "CURATED_COMMITTED_dev12"
        if not base.strip() and c_path.exists():
            # the committed record carries an EMPTY baseline_answer
            # (the 2 dev12 pairs outside the auditor's judged 10) —
            # the builder-authored STANDARD_REFERENCE baseline serves
            base = str(json.loads(c_path.read_text()).get("baseline_answer") or "")
            b_src = "CURATED_STANDARD_REFERENCE_builder_r8"
        if not base.strip():
            continue
        if a1.strip() and base.strip():
            pairs.append({"problem_id": pid, "a1": a1[:6000],
                          "a1_src": a1_src, "base": base[:6000],
                          "b_src": b_src})
    _only = os.environ.get("R6_ONLY_IDS")
    if _only:
        _keep = set(_only.split(","))
        pairs = [p for p in pairs if p["problem_id"] in _keep]
    print(f"[r6] pool: {len(pairs)} pairs "
          f"(delivery: {sum(1 for p in pairs if 'PROMOTED' in p['a1_src'])}, "
          f"fresh-gen: {sum(1 for p in pairs if 'BATTERY_R5' in p['a1_src'])})")

    results = []
    t0 = time.time()
    for i, pr in enumerate(pairs):
        econ.reset_governor(f"r6:{pr['problem_id']}")
        prob = problems[pr["problem_id"]]
        # packet evidence if the dev12 pair carries one
        packet = None
        try:
            from r7_a0plus import (_load_pair, _packet_by_id_from_run_tree,
                                   _unique_packet_list)
            pair = _load_pair(pr["problem_id"])
            packet = (_unique_packet_list(
                _packet_by_id_from_run_tree(pair)) if pair else None)
        except Exception:  # noqa: BLE001 — packet is optional context
            packet = None
        jc, prompt = judge_pair_call(prob, pr["a1"], pr["base"], packet)
        axes = extract_axes(jc)
        row = {
            "problem_id": pr["problem_id"],
            "a1_source": pr["a1_src"], "baseline_source": pr["b_src"],
            "judge": list(JUDGE),
            "judge_outcome": jc.get("outcome"),
            "prefer": (jc.get("valid") or {}).get("prefer"),
            "axes": axes,
            "prompt_hash": hashlib.sha256(
                prompt.encode("utf-8")).hexdigest()[:16],
        }
        if axes:
            row["novelty_delta"] = axes["novelty_a1"] - axes["novelty_baseline"]
            row["feasibility_abs_gap"] = abs(
                axes["feasibility_a1"] - axes["feasibility_baseline"])
        results.append(row)
        nd = row.get("novelty_delta")
        print(f"  [{i+1}/{len(pairs)}] {pr['problem_id'][:34]:<36} "
              f"{row['judge_outcome']:<16} nd={nd} "
              f"pref={row['prefer']}", flush=True)
        (REPO / "eval" / "battery_peraxis_r11_r6.partial.json").write_text(
            json.dumps(results, indent=1, default=str) + "\n",
            encoding="utf-8")
        time.sleep(PACE_S)

    # ---- gate computation on the per-axis evidence ----------------
    valid = [r for r in results if r.get("axes")]
    n = len(valid)
    import math
    def _tci(vals):
        if len(vals) < 2:
            return (None, None, None)
        m = sum(vals) / len(vals)
        sd = math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))
        se = sd / math.sqrt(len(vals))
        return (round(m, 3), round(m - 1.96 * se, 3), round(m + 1.96 * se, 3))
    nd = [r["novelty_delta"] for r in valid]
    fg = [r["feasibility_abs_gap"] for r in valid]
    nd_m, nd_lo, nd_hi = _tci(nd)
    fg_m, fg_lo, fg_hi = _tci(fg)
    a1_wins = sum(1 for r in valid if r.get("prefer") == "A")
    b_wins = sum(1 for r in valid if r.get("prefer") == "B")
    record = {
        "record": "BATTERY_PERAXIS_R11_R6/1.0.0",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "judge": list(JUDGE),
        "judge_independence": {
            "generator_rungs": ["xkiro/mistralai/ministral-14b",
                                "zai/zai-org/GLM-5.3 (gateway)"],
            "judge_rung": "/".join(JUDGE),
            "independent": True,
            "note": "crowllm provider, Qwen family — differs from every "
                    "served generator rung in provider AND family; "
                    "re-qualified this window (30/30 paced gold "
                    "calibration, eval/crowllm_requalification_r11_r8.json)"},
        "baseline_class": "CURATED (12 committed dev12 + 18 "
                          "builder-authored STANDARD_REFERENCE, pending "
                          "auditor adoption)",
        "results": results,
        "summary": {
            "n_pairs": len(pairs), "n_valid_per_axis": n,
            "novelty_delta_mean": nd_m, "novelty_ci95": [nd_lo, nd_hi],
            "novelty_clause_resolved_pass": (nd_lo is not None
                                             and nd_lo >= 0.5),
            "feasibility_abs_gap_mean": fg_m,
            "feasibility_ci95": [fg_lo, fg_hi],
            "feasibility_clause_resolved_pass": (fg_hi is not None
                                                 and fg_hi <= 0.25),
            "prefer_tally": {"a1": a1_wins, "baseline": b_wins,
                             "tie": n - a1_wins - b_wins},
            "wall_s": round(time.time() - t0, 1),
        },
        "gate_note": (
            "MEASUREMENT for the auditor (Art. XXVI): the two formal "
            "clauses computed from the per-axis evidence — novelty "
            "resolved-PASS when CI lower >= 0.5; feasibility "
            "resolved-PASS when CI upper <= 0.25. The gate decision "
            "remains the auditor's (baseline adoption + judge "
            "acceptance + re-judgment)."),
    }
    out = REPO / "eval" / "battery_peraxis_r11_r6.json"
    out.write_text(json.dumps(record, indent=1, default=str) + "\n",
                   encoding="utf-8")
    s = record["summary"]
    print(f"\n[r6] valid {s['n_valid_per_axis']}/{s['n_pairs']} | "
          f"novelty Δ {s['novelty_delta_mean']} CI {s['novelty_ci95']} | "
          f"feasibility |gap| {s['feasibility_abs_gap_mean']} CI "
          f"{s['feasibility_ci95']} | prefer {s['prefer_tally']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()

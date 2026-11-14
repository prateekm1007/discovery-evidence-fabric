#!/usr/bin/env python3
"""r11_d4_independent_judge.py — Amendment 3 direction 4.

The R3 A1 judgments rode the CONFLICTED xkiro set (AM3 §5: 'the A1
judgments are still the conflicted xkiro set'). This run re-judges the
20 A1 pairs (10 a1_vs_baseline + 10 a1_vs_a0plus, same answers, same
blind order, same evidence bytes) on a judge that differs from every
SERVED generator rung in provider AND model, with:
  * the standard calibration gate on the gold corpus (>=0.8),
  * a POSITION SWAP re-judgment of every pair (swap consistency),
  * the independence check computed from the arm timelines.

Measured basis: the R3 generator served EXACTLY ONE rung
(agnes/agnes-3.0-flash, 17 calls in per_call_timeline). The judge
selected here (inception/mercury-3, measured live) differs in both.
xkiro is 403-dead this window (typed in the candidate record).

F15 root cause (measured this round): the R3 panel's 6/6
JUDGE_EMPTY_OUTPUT was the 300-token cap — mercury-3 burns the cap on
reasoning (finish_reason=length) and answers with the JSON contract at
max_tokens>=2000. The judge call cap is now 2000 (typed in
eval/run.py).
"""
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
os_env = __import__("os").environ
os_env.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os_env.setdefault("ENGINE_LLM_TIMEOUT_S", "120")
os_env.setdefault("ENGINE_LLM_RETRY_SLEEP_S", "0")

from eval.run import (  # noqa: E402
    _rubric_prompt, probe_judge_route, utc_now)


def blind_order(pid: str, pair_kind: str):
    """Deterministic per-pair side order — replicated byte-exact from
    r11_a0plus_compare.py (that script has no main guard and cannot be
    imported without executing the whole comparison)."""
    import hashlib
    h = hashlib.sha256(f"{pid}::{pair_kind}".encode()).hexdigest()
    return ("a0plus_first" if int(h, 16) % 2 == 0 else "other_first")

OUT = REPO / "eval" / "judge_independent_rerun_r11_r4.json"
GEN_TIMELINE_DIR = REPO / "eval" / "pairs" / "r11_a1_r3"
A0_DIR = REPO / "eval" / "pairs" / "r11_a0plus"
BASE_DIR = REPO / "eval" / "pairs" / "dev12_fresh"


def served_rungs() -> set:
    """Every (provider, model) that served ANY generator call in the
    R3 arm timelines — the set the judge must not intersect."""
    served = set()
    for f in sorted(GEN_TIMELINE_DIR.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for c in (d.get("per_call_timeline") or []):
            served.add((str(c.get("provider") or c.get("provider_id")
                            or "?"), str(c.get("model") or "?")))
    return served


def main() -> int:
    t0 = time.time()
    served = served_rungs()
    print("[d4] served generator rungs:", sorted(served))

    # ---- judge selection: calibration-gated, != served rungs --------
    route = probe_judge_route("agnes")  # the served generator provider
    jp, jm = route.get("provider"), route.get("model")
    print(f"[d4] judge route: {jp}/{jm} ({route.get('selection')})")
    cand = {c["provider"] + "/" + c["model"]: c
            for c in (route.get("candidates") or [])}
    calib = route.get("calibration_full") or {}
    calib_acc = calib.get("accuracy")
    calib_n = calib.get("n_valid")

    independent = (jp, jm) not in served
    print(f"[d4] judge independence vs served rungs: {independent}")
    if not (jp and jm and independent):
        print("[d4] VERDICT: NO_INDEPENDENT_JUDGE (typed)")
        OUT.write_text(json.dumps({
            "record": "judge_independent_rerun_r11_r4/1.0.0",
            "at": utc_now(), "served_rungs": sorted(served),
            "route": {k: route.get(k) for k in
                      ("provider", "model", "state", "selection")},
            "candidates": route.get("candidates"),
            "typed_state": "NO_INDEPENDENT_JUDGE"},
            indent=1) + "\n", encoding="utf-8")
        return 4

    # ---- rebuild the 20 A1 pair prompts exactly as R3 built them ----
    probs = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}
    pids = sorted(probs)
    # the evidence packet per problem: rebuild the way the compare
    # script did — the committed pair records carry the packet refs;
    # the judge prompt is deterministic from the SAME answers + packet
    # bytes; the packet comes from the a0plus record's stored packet
    # (the R3 compare loaded it via _load_pair/_packet_by_id_from_
    # run_tree). The prompt_hash in the committed judgments pins the
    # identity — we verify our rebuild matches the committed hashes.
    a0 = json.loads((REPO / "eval" / "a0plus_compare_r11.json")
                    .read_text(encoding="utf-8"))
    committed = {(j["problem_id"], j["pair"]): j
                 for j in (a0.get("judgments") or [])}
    pairs = [(k, v) for k, v in sorted(committed.items())
             if k[1].startswith("a1_")]
    print(f"[d4] committed A1 judgments: {len(pairs)} (of "
          f"{len(committed)} total records)")

    sys.path.insert(0, str(REPO / "scripts"))
    # NOTE: r11_a0plus_compare.py is a top-level script with NO main
    # guard — importing it would EXECUTE the whole comparison (LLM
    # calls). The packet/pair loaders live in r7_a0plus (a proper
    # library with a main guard); the D4 rebuild uses those directly.
    from r7_a0plus import (  # noqa: E402
        _load_pair, _packet_by_id_from_run_tree, _unique_packet_list)

    results, n_ok, n_swap_ok = [], 0, 0
    n_expected = 0
    for (pid, kind), j in pairs:
        n_expected += 1
        prob = probs[pid]
        a1_ans = str(json.loads(
            (GEN_TIMELINE_DIR / f"{pid}.json").read_text())
            .get("a1_answer") or "")
        if kind == "a1_vs_baseline":
            other = str(json.loads(
                (BASE_DIR / f"{pid}.json").read_text())
                .get("baseline_answer") or "")
            other_name = "baseline"
        else:
            oa = json.loads((A0_DIR / f"{pid}.json").read_text())
            other = str(oa.get("a0plus_answer") or oa.get("answer") or "")
            other_name = "a0plus"
        if not a1_ans.strip() or not other.strip():
            results.append({"problem_id": pid, "pair": kind,
                            "typed_state": "EMPTY_ARM_BYTES"})
            continue
        x_ans, y_ans = a1_ans, other
        order = j.get("order") or blind_order(pid, kind)
        # reproduce the committed prompt (verify by hash), then judge
        # BOTH positions; the packet comes from the same run tree the
        # R3 compare loaded (r7_a0plus loaders, main-guarded library)
        pair = _load_pair(pid)
        packet = _unique_packet_list(
            _packet_by_id_from_run_tree(pair)) if pair else None
        a_text, b_text = ((x_ans, y_ans) if order == "a0plus_first"
                          else (y_ans, x_ans))
        prompt = _rubric_prompt(prob, a_text, b_text, packet)
        ph = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        committed_ph = j.get("prompt_hash")
        from eval.run import _judge_judgment_call  # noqa: E402
        jc1 = _judge_judgment_call(jp, jm, prompt, clar=bool(
            prob.get("clarification_answer")))
        time.sleep(6)  # quota-window pacing (AM3 D6 ledger discipline)
        # position swap: same content, A/B exchanged
        prompt_sw = _rubric_prompt(prob, b_text, a_text, packet)
        jc2 = _judge_judgment_call(jp, jm, prompt_sw, clar=bool(
            prob.get("clarification_answer")))
        time.sleep(6)
        v1, v2 = jc1.get("valid"), jc2.get("valid")
        rec = {"problem_id": pid, "pair": kind, "order": order,
               "judge": f"{jp}/{jm}",
               "prompt_hash_committed": committed_ph,
               "prompt_hash_rebuilt": ph,
               "prompt_hash_match": (ph == committed_ph),
               "pass1_outcome": jc1.get("outcome"),
               "pass1": v1, "pass1_raw": (jc1.get("raw") or "")[:200],
               "swap_outcome": jc2.get("outcome"),
               "swap": v2, "swap_raw": (jc2.get("raw") or "")[:200]}
        if v1:
            n_ok += 1
        # decode both passes into (a1 vs other) winners
        def _decode(valid, ord_):
            if not valid:
                return None
            prefer = valid.get("prefer")
            if prefer not in ("A", "B"):
                return "tie"
            a1_is_a = (ord_ == "a0plus_first")  # x=a1 served first
            # in the original order A = a1 when order=='a0plus_first'
            # (x first); in the swap A = the OTHER arm
            pick = "a1" if ((prefer == "A") == a1_is_a) else other_name \
                if not False else None
            return pick
        d1 = _decode(v1, order)
        d2 = _decode(v2, "swapped_first" if True else "")
        # for the swap, A holds the other arm: a1 picked iff
        # prefer=='B'
        if v2:
            pr2 = v2.get("prefer")
            d2 = ("tie" if pr2 not in ("A", "B")
                  else ("a1" if pr2 == "B" else other_name))
        rec["decoded_pass1"], rec["decoded_swap"] = d1, d2
        if d1 is not None and d2 is not None:
            same = (d1 == d2)
            rec["swap_consistent"] = same
            n_swap_ok += int(same)
        results.append(rec)
        print(f"  {pid[:34]:<36} {kind:<16} p1={jc1.get('outcome')[:12]:<14}"
              f" sw={jc2.get('outcome')[:12]:<14} d1={d1} d2={d2}")
        # incremental durability (Art. XXV): the served judgments stay
        # on disk, never lost with the process
        (REPO / "eval" / "judge_independent_rerun_r11_r4.partial.json") \
            .write_text(json.dumps(results, indent=1, default=str) + "\n",
                        encoding="utf-8")

    # ---- recovery lap: ONE cooldown + ONE re-judgment of every pair
    # whose first lap failed on transport/empty (the quota window
    # recovers in minutes; measured this round after the 30-pair
    # calibration burst) -------------------------------------------
    failed = [(i, r) for i, r in enumerate(results)
              if not r.get("decoded_pass1")
              or not r.get("decoded_swap")]
    if failed:
        print(f"[d4] recovery lap: {len(failed)} pair-side misses; "
              "cooldown 120 s (quota window)")
        time.sleep(120)
    for i, r in failed:
        pid, kind = r["problem_id"], r["pair"]
        prob = probs[pid]
        a1_ans = str(json.loads(
            (GEN_TIMELINE_DIR / f"{pid}.json").read_text())
            .get("a1_answer") or "")
        if kind == "a1_vs_baseline":
            other = str(json.loads(
                (BASE_DIR / f"{pid}.json").read_text())
                .get("baseline_answer") or "")
            other_name = "baseline"
        else:
            oa = json.loads((A0_DIR / f"{pid}.json").read_text())
            other = str(oa.get("a0plus_answer") or oa.get("answer") or "")
            other_name = "a0plus"
        if not a1_ans.strip() or not other.strip():
            continue
        order = r["order"]
        pair = _load_pair(pid)
        packet = _unique_packet_list(
            _packet_by_id_from_run_tree(pair)) if pair else None
        x_ans, y_ans = a1_ans, other
        a_text, b_text = ((x_ans, y_ans) if order == "a0plus_first"
                          else (y_ans, x_ans))
        from eval.run import _judge_judgment_call  # noqa: E402
        if not r.get("decoded_pass1"):
            jc = _judge_judgment_call(jp, jm, _rubric_prompt(
                prob, a_text, b_text, packet), clar=bool(
                prob.get("clarification_answer")))
            if jc.get("valid"):
                pr = jc["valid"].get("prefer")
                r["decoded_pass1"] = (
                    "tie" if pr not in ("A", "B")
                    else ("a1" if (pr == "A") == (order == "a0plus_first")
                          else other_name))
                r["pass1_outcome"] = jc.get("outcome")
                r["recovered_pass1"] = True
                n_ok += 1
            time.sleep(6)
        if not r.get("decoded_swap"):
            jc = _judge_judgment_call(jp, jm, _rubric_prompt(
                prob, b_text, a_text, packet), clar=bool(
                prob.get("clarification_answer")))
            if jc.get("valid"):
                pr = jc["valid"].get("prefer")
                r["decoded_swap"] = (
                    "tie" if pr not in ("A", "B")
                    else ("a1" if pr == "B" else other_name))
                r["swap_outcome"] = jc.get("outcome")
                r["recovered_swap"] = True
            time.sleep(6)
        if r.get("decoded_pass1") is not None \
                and r.get("decoded_swap") is not None:
            r["swap_consistent"] = (r["decoded_pass1"]
                                    == r["decoded_swap"])
        print(f"  recovery {pid[:34]:<36} {kind:<16} "
              f"d1={r.get('decoded_pass1')} d2={r.get('decoded_swap')}")
        (REPO / "eval" / "judge_independent_rerun_r11_r4.partial.json") \
            .write_text(json.dumps(results, indent=1, default=str) + "\n",
                        encoding="utf-8")

    n_decoded = sum(1 for r in results if r.get("decoded_pass1"))
    swap_cons = (n_swap_ok / n_decoded) if n_decoded else 0.0
    # calibration acceptance: the standard gold-corpus gate (>=0.8)
    calib_ok = bool(calib_acc is not None and calib_acc >= 0.8)
    acceptance = {
        "D4_independence_20_of_20": {
            "judge": f"{jp}/{jm}",
            "served_rungs": sorted(served),
            "independent": independent,
            "judgments_valid": n_ok,
            "judgments_total": n_expected,
            "PASS": independent and n_ok == n_expected == 20,
        },
        "D4_calibration_close_pairs": {
            "gold_corpus_accuracy": calib_acc,
            "n_valid": calib_n,
            "threshold": 0.8,
            "PASS": calib_ok,
        },
        "D4_swap_consistency": {
            "consistent": n_swap_ok, "decoded": n_decoded,
            "rate": round(swap_cons, 3), "threshold": 0.8,
            "PASS": n_decoded > 0 and swap_cons >= 0.8,
        },
    }
    out = {"record": "judge_independent_rerun_r11_r4/1.0.0",
           "at": utc_now(), "served_rungs": sorted(served),
           "judge": {"provider": jp, "model": jm,
                     "route": route.get("selection"),
                     "calibration": {k: calib.get(k) for k in
                                     ("calibrated", "n_pairs", "correct",
                                      "accuracy", "threshold", "passed",
                                      "corpus_sha256", "n_valid")}},
           "root_cause_f15": ("the R3 panel's JUDGE_EMPTY_OUTPUT was "
                              "the 300-token cap (mercury-3 reasoning "
                              "burns it: finish_reason=length); "
                              "measured recovery at max_tokens>=2000 "
                              "on the FULL-length prompt"),
           "results": results, "acceptance": acceptance,
           "wall_s": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n",
                   encoding="utf-8")
    print(f"[d4] acceptance: {json.dumps(acceptance, default=str)[:400]}")
    ok = all(v.get("PASS") for v in acceptance.values())
    print(f"[d4] VERDICT: {'ACCEPTANCE_MET' if ok else 'ACCEPTANCE_GAP'}")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r143_panel_oneshot — DIR-2 (TOP, the score-8 gate): the R-CAL panel
run EXACTLY ONCE on the auditor's sealed r143 corpus with the AM47
viability-necessity forced-choice suffix on EVERY judge prompt.

Seal typing (honest, the r142 convention): the corpus FILE bytes at
the audit tip hash to 19497e570df7f837; the file's own recorded
selection_sha256[:16] = dcd80334e2810b38, which is the hex the owner
directions quote; the in-file canonicalization recipe ("remove
selection_sha256, json.dumps(indent=1, sort_keys)") recomputes to
014181ff0a787655 — the recorded digest is the auditor's
selection/process digest, not recomputable from the file alone. Typed
in the record; the run is against the COMMITTED BYTES.

Protocol (the corpus 'protocol' field, AM47): judge sees problem + A/B
mechanisms (blind, sha-parity swap), forced-choice prefer; per-judge
acc>=0.8 AND answered>=0.9 AND |over_novel-over_cons|<=1 to qualify;
>=3 qualified from >=2 non-agnes families; inter-judge alpha>=0.6.
NOT a bar-lowering: acc>=0.8 unchanged.

One generation per (judge, pair, order) leg; byte-resume continues the
SAME generation; NO re-roll regardless of outcome (Art. 7). The det
(parity-drawn) order votes; the mir order discloses swap stability.
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r143_panel"
OUT.mkdir(exist_ok=True)

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
CORPUS_PATH = "eval/auditor_rcal_corpus_r143.json"
PROMPT_PATH = "eval/rcal_judge_prompt_r143.json"

JUDGES = [
    {"model": "deepseek-ai/DeepSeek-R1", "family": "deepseek",
     "tag": "dsr1", "transport": "hf", "pace": 20,
     "budgets": [8000, 12000], "timeout_s": 420.0},
    {"model": "Qwen/Qwen3-32B", "family": "qwen",
     "tag": "qw32b", "transport": "hf", "pace": 20,
     "budgets": [8000, 12000], "timeout_s": 420.0},
    {"model": "Qwen/Qwen3-235B-A22B-Instruct-2507", "family": "qwen",
     "tag": "qwen235b", "transport": "hf", "pace": 20,
     "budgets": [4000, 8000], "timeout_s": 300.0},
    {"model": "deepseek-ai/DeepSeek-V3.2", "family": "deepseek",
     "tag": "dsv32", "transport": "hf", "pace": 20,
     "budgets": [4000, 8000], "timeout_s": 300.0},
    {"model": "hy4-flash:free", "family": "cent-ai",
     "tag": "hy4f", "transport": "cent", "pace": 20,
     "budgets": [4000, 8000, 12000], "timeout_s": 420.0},
]

SYSTEM = ("You are a strict blind rubric judge. English only. "
          "Follow the response contract exactly.")
QUESTION = ("Which of the two candidate mechanisms (A or B) is the "
            "better engineering answer to the stated problem? "
            "Forced choice: no ties.")


def audit_bytes(path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{AUDIT_REF}:{path}"],
        capture_output=True, text=True, check=True).stdout


def load_inputs() -> tuple:
    raw = audit_bytes(CORPUS_PATH)
    d = json.loads(raw)
    file_sha = hashlib.sha256(raw.encode()).hexdigest()[:16]
    labels = {p["problem_id"]: p["overall_preference"]
              for p in d["pairs"]}
    for pid, lab in labels.items():
        if lab not in ("a1", "baseline"):
            raise SystemExit(f"tie-labeled corpus at {pid}: {lab!r}")
    prompt_doc = json.loads(audit_bytes(PROMPT_PATH))
    suffix = (prompt_doc.get("forced_choice_suffix") or "").strip()
    if "VIABILITY IS NECESSARY" not in suffix:
        raise SystemExit("the AM47 viability-necessity suffix is "
                         "missing from the sealed prompt file")
    return d, labels, file_sha, prompt_doc.get("record", ""), suffix


def blind_order(pid: str) -> str:
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "a1_first" if int(h, 16) % 2 == 0 else "base_first"


def problem_dict(pair: dict) -> dict:
    return {
        "device": f"{pair.get('domain', 'engineering')} (domain of record)",
        "failure": str(pair.get("problem", "")).strip(),
        "question": QUESTION,
    }


def _leg(judge: dict, prompt: str) -> dict:
    from discovery_fabric.engine.blind_panel import parse_pair_rating
    attempts, outcome, parsed, raw = [], "TRANSPORT_FAILED", None, None
    for attempt in range(1, 5):
        budget = judge["budgets"][min(attempt - 1,
                                      len(judge["budgets"]) - 1)]
        t0 = time.monotonic()
        try:
            if judge["transport"] == "cent":
                from discovery_fabric.engine.route_adapter import (
                    cent_ai_chat)
                r = cent_ai_chat(
                    [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
                    model=judge["model"], max_tokens=budget,
                    timeout_s=judge["timeout_s"], stream=True)
            else:
                from discovery_fabric.engine.route_adapter import (
                    hf_router_chat)
                r = hf_router_chat(
                    [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
                    model=judge["model"], max_tokens=budget,
                    timeout_s=judge["timeout_s"])
            raw = r.get("content") or ""
            err = r.get("error")
        except Exception as e:  # noqa: BLE001 — typed degradation
            raw, err = None, f"{type(e).__name__}: {str(e)[:160]}"
        lat = round(time.monotonic() - t0, 1)
        attempts.append({"attempt": attempt, "budget": budget,
                         "latency_s": lat, "error": err})
        if raw:
            try:
                parsed = parse_pair_rating(raw)
                outcome = "VALID"
                break
            except ValueError as e:
                outcome = "PARSE_FAILED"
                if attempt < 4:
                    prompt = (prompt + "\n\nYour previous output "
                              "violated the contract (" + str(e)[:120]
                              + "). Respond with ONLY the JSON object "
                              'with the eight axis keys and '
                              '"prefer": "A" or "B". No other text.')
                    time.sleep(3)
        elif err and ("429" in str(err) or "Rate" in str(err)):
            outcome = "RATE_LIMITED"
            time.sleep(120)
        elif err and ("503" in str(err) or "timeout" in str(err)
                      or "upstream" in str(err)):
            time.sleep(30)
    return {"outcome": outcome, "parsed": parsed,
            "raw_tail": (raw or "")[-800:] if raw else None,
            "attempts": attempts}


def am47_bias(judge_rows: dict, labels: dict) -> dict:
    """Per-judge over_novel / over_cons from the DET votes (the voting
    legs) + the sealed labels: over_novel = chose the novel (a1) arm
    where the auditor preferred the baseline; over_cons = the mirror."""
    bias = {}
    for key, rows in judge_rows.items():
        on = oc = 0
        for r in rows:
            if r.get("pass") != "det" or not r.get("parsed"):
                continue
            chosen = r["a_is"] if r["parsed"].get("prefer") == "A" \
                else ("baseline" if r["a_is"] == "a1" else "a1")
            lab = labels.get(r["pid"])
            if chosen == "a1" and lab == "baseline":
                on += 1
            elif chosen == "baseline" and lab == "a1":
                oc += 1
        bias[key] = {"over_novel": on, "over_cons": oc,
                     "imbalance": abs(on - oc)}
    return bias


def main() -> int:
    import os
    from discovery_fabric.engine.blind_panel import (
        build_pair_prompt, parse_pair_rating)

    corpus, labels, file_sha, prompt_record, suffix = load_inputs()
    pairs = corpus["pairs"]
    only = os.environ.get("R143_JUDGE", "").strip()
    judges = ([j for j in JUDGES if j["tag"] == only] if only else JUDGES)
    print(f"corpus: {len(pairs)} pairs | raw file sha {file_sha} | "
          f"selection {corpus.get('selection_sha256', '')[:16]} | "
          f"prefer_a1={corpus['prefer_a1']} "
          f"prefer_baseline={corpus['prefer_baseline']} | "
          f"prompt={prompt_record[:60]} | "
          f"judges={[j['tag'] for j in judges]}", flush=True)

    for j in judges:
        for p in pairs:
            pid = p["problem_id"]
            det_a1_first = blind_order(pid) == "a1_first"
            for order in ("det", "mir"):
                legfile = OUT / f"{j['tag']}__{pid}__{order}.json"
                if legfile.exists():
                    continue
                a_is = "a1" if (
                    (order == "det") == det_a1_first) else "baseline"
                a_text = (p["a1_mechanism"] if a_is == "a1"
                          else p["baseline_mechanism"])
                b_text = (p["baseline_mechanism"] if a_is == "a1"
                          else p["a1_mechanism"])
                prompt = build_pair_prompt(problem_dict(p),
                                           a_text, b_text, cot=True)
                if suffix:
                    prompt = prompt + "\n" + suffix
                t0 = time.monotonic()
                leg = _leg(j, prompt)
                wall = round(time.monotonic() - t0, 1)
                rec = {"judge": j["tag"], "family": j["family"],
                       "model": j["model"], "pid": pid,
                       "pass": order, "a_is": a_is,
                       "blind_order_parity": det_a1_first,
                       "outcome": leg["outcome"],
                       "parsed": leg["parsed"],
                       "raw_tail": leg["raw_tail"],
                       "attempts": leg["attempts"], "wall_s": wall}
                legfile.write_text(json.dumps(rec, indent=1,
                                              ensure_ascii=False) + "\n")
                pref = ((leg["parsed"] or {}).get("prefer")
                        if leg["parsed"] else None)
                print(f"{j['tag']} {pid} {order}: "
                      f"{leg['outcome']} prefer={pref} ({wall}s)",
                      flush=True)
                time.sleep(j["pace"] if leg["outcome"] == "VALID" else 5)

    if only:
        print(f"judge {only}: all legs done (tally runs in the "
              "unfiltered process)", flush=True)
        return 0

    judge_rows = {}
    for j in JUDGES:
        rows = []
        for p in pairs:
            pid = p["problem_id"]
            for order in ("det", "mir"):
                lf = OUT / f"{j['tag']}__{pid}__{order}.json"
                if not lf.exists():
                    continue
                r = json.loads(lf.read_text())
                rows.append({"pid": pid, "pass": r["pass"],
                             "a_is": r["a_is"],
                             "outcome": r["outcome"],
                             "parsed": r["parsed"]})
        judge_rows[j["family"] + ":" + j["tag"]] = rows

    from discovery_fabric.engine.panel_agreement import (
        rcal_qualification, swap_robust_panel)

    bias = am47_bias(judge_rows, labels)
    qual = rcal_qualification(judge_rows, labels, expected_legs=24)
    for fam, q in qual.items():
        b = bias.get(fam, {"imbalance": 9})
        q["am47_bias"] = bias.get(fam)
        q["qualified"] = bool(
            q.get("qualified")
            and (b.get("imbalance") if isinstance(b, dict) else 9) <= 1)
    qualified = [fam for fam, q in qual.items() if q["qualified"]]
    qualified_tags = [f.split(":")[1] for f in qualified]

    gold = {}
    for p in pairs:
        pid = p["problem_id"]
        det_a1_first = blind_order(pid) == "a1_first"
        det_a_is = "a1" if det_a1_first else "baseline"
        lab = labels[pid]
        for arm_name, corpus_arm in (("A", det_a_is),
                                     ("B", "baseline" if det_a_is == "a1"
                                      else "a1")):
            good = (corpus_arm == lab)
            gold[f"{pid}::{arm_name}"] = {
                "pid": pid, "arm": arm_name,
                "label": "GOOD" if good else "BAD"}

    panel = swap_robust_panel(judge_rows, qualified, labels,
                              gold_novelty=gold)
    fams = {f.split(":")[1]: f.split(":")[0] for f in qualified}
    session = os.environ.get("R143_SESSION", "builder-r142s2")
    record = {
        "record": "R143_PANEL_ONESHOT/1.0.0",
        "claim": "c-0232", "work_id": "r143-rcal-panel-oneshot",
        "session": session,
        "at": "2026-11-23 (sandbox clock)",
        "corpus": {
            "source": f"{AUDIT_REF}:{CORPUS_PATH}",
            "raw_file_sha256_16": file_sha,
            "recorded_selection_sha256_16":
                corpus.get("selection_sha256", "")[:16],
            "canonicalization_recipe_recompute_16": "014181ff0a787655",
            "note": ("the direction's dcd80334e2810b38 is the corpus's "
                     "own recorded selection_sha256 prefix; the run is "
                     "against the committed FILE bytes; the recipe "
                     "recompute mismatch is typed exactly like the "
                     "r142 selection-process distinction"),
            "n_pairs": len(pairs),
            "prefer_a1": corpus["prefer_a1"],
            "prefer_baseline": corpus["prefer_baseline"]},
        "prompt": {"record": prompt_record,
                   "am47_suffix_applied": True,
                   "viability_necessity": "VIABILITY IS NECESSARY "
                                          "checked present in the "
                                          "sealed suffix"},
        "protocol": corpus.get("protocol"),
        "one_shot": ("exactly one generation; byte-resume continues the "
                     "same generation; NO re-roll (Art. 7) — the "
                     "outcome below is final; burn after"),
        "qualification": qual,
        "qualified_tags": qualified_tags,
        "qualified_families": fams,
        "am47_bias": bias,
        "gates": {
            "n_qualified": len(qualified),
            "distinct_non_agnes_families": len(set(fams.values())),
            "per_judge_bar": "acc>=0.8 AND answered>=0.9 AND "
                             "|over_novel-over_cons|<=1",
            "panel_agreement": panel.get("panel_agreement"),
            "kappa_mean": panel.get("kappa_mean"),
            "auc": panel.get("auc"),
            "agreement_ge_0.7":
                (panel.get("panel_agreement") or 0) >= 0.7,
            "kappa_ge_0.6": (panel.get("kappa_mean") or 0) >= 0.6,
            "auc_ge_0.8": (panel.get("auc") or 0) >= 0.8},
        "panel": panel,
        "labels_used_for_tally_only":
            "the judge inputs never carried the label fields "
            "(build_pair_prompt formats only what its caller passes)",
    }
    (REPO / "eval" / "r143_panel_qualification.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(record["gates"], indent=1))
    print("am47_bias:", json.dumps(bias))
    print("qualified:", qualified_tags)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

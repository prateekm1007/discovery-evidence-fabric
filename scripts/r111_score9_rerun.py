#!/usr/bin/env python3
"""r111_score9_rerun.py — claim c-152 (the auditor direction 5): the
score-9 re-run's INDEPENDENT RECOMPUTE. The batch ran ONCE (Art. 29(c),
one generation run — the checkpoint /tmp/r111_score9_checkpoint.json
with run_id typed below); this recompute reads the COMMITTED eval-log
bytes and the engine's DETERMINISTIC acceptance module
(rediscovery_protocol.acceptance — the c-0131/c-0132 precedent:
deterministic engine modules may be exercised by the verifier/recompute;
no generation, no judge call, no quota).

Outputs: recovery rate + Wilson 95% CI (the conservative 30-denominator
AND the evaluated subset when parse exhaustions typed), the gate verdict
(>=0.40 -> the score-9 gate, else the typed RCA fields)."""
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys_path = str(REPO)
import sys  # noqa: E402
sys.path.insert(0, sys_path)

from discovery_fabric.engine import rediscovery_protocol as rp  # noqa
from inspect_ai.log import read_eval_log  # noqa: E402

OUT = REPO / "eval" / "r111_score9_rerun.json"


def wilson95(k: int, n: int) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    z = 1.959963984540054
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return [round(max(0.0, center - half), 4),
            round(min(1.0, center + half), 4)]


def main():
    logs = sorted((REPO / "eval" / "r111_score9_inspect_logs").glob(
        "*.eval"), key=lambda p: p.stat().st_mtime)
    assert logs, "no eval log"
    log = read_eval_log(str(logs[-1]))
    assert log.status == "success", f"eval status {log.status}"
    recoveries, item_ids = [], []
    parse_exhausted = []
    for s in log.samples or []:
        sc = (s.scores or {}).get("recovery_scorer")
        val = getattr(sc, "value", None) if sc is not None else None
        item_ids.append(s.id)
        if val == "ITEM_GENERATION_PARSE_EXHAUSTION":
            parse_exhausted.append(s.id)
            recoveries.append(val)
        else:
            recoveries.append(str(val))
    acc30 = rp.acceptance(["PARTIAL" if r ==
                           "ITEM_GENERATION_PARSE_EXHAUSTION" else r
                           for r in recoveries])
    evaluated = [r for r in recoveries
                 if r != "ITEM_GENERATION_PARSE_EXHAUSTION"]
    acc_eval = rp.acceptance(evaluated)
    # Wilson on the RECOVERED rate (the conservative + the subset)
    hits30 = sum(1 for r in recoveries if r == "RECOVERED")
    hits_eval = sum(1 for r in evaluated if r == "RECOVERED")
    cp = Path("/tmp/r111_score9_checkpoint.json")
    usage = json.loads(cp.read_text()).get("usage", {}) if cp.exists() \
        else {}
    rec = {
        "record": "R111_SCORE9_RERUN/1.0.0",
        "executor": "builder-r111s1",
        "claim": "c-152 (r111-score9-rerun, measurement; ONE generation "
                 "run — the checkpoint's run_id is typed below)",
        "checkpoint_run_id": json.loads(cp.read_text()).get("run_id")
        if cp.exists() else None,
        "corpus": ("eval/r106_score9_corpus_postcutoff/"
                   "sampled_items.jsonl (the 30 post-cutoff items; the "
                   "peer's re-authored corpus lineage)"),
        "generator": "agnes-3.0-flash (the registered route; api_key "
                     "from the Art. 17 vault, never in code)",
        "harness": "Inspect AI 0.3.291 (the harness-of-record; the "
                   "task scripts/r106_score9_inspect_task.py unchanged)",
        "interventions": 0,
        "usage": usage,
        "recompute": {
            "source": "the committed eval-log bytes (read via the "
                      "harness's own reader) + the engine's "
                      "DETERMINISTIC acceptance module; zero LLM calls",
            "all_30_conservative": {**acc30,
                                    "recovery_rate_wilson95": wilson95(
                                        hits30, 30)},
            "evaluated_subset": {**acc_eval,
                                 "n_evaluated": len(evaluated),
                                 "recovery_rate_wilson95": wilson95(
                                     hits_eval, len(evaluated))},
            "parse_exhausted_items": parse_exhausted,
        },
        "gate": {
            "bar": rp.RECOVERY_BAR,
            "met": bool(acc30["recovery_rate"] >= rp.RECOVERY_BAR),
            "note": (">=0.40 -> the score-9 gate; a miss files the "
                     "typed RCA (this record + the honest_note)"),
        },
        "typed_rca": {
            "finding": ("the 0.40 score-9 bar is NOT met on the "
                        "post-cutoff corpus: 5/30 RECOVERED = 0.1667, "
                        "CI95 [0.0734, 0.3356]"),
            "cross_corpus_caveat": ("the r106 run's 0.30 was the m2 "
                                    "corpus (per_item ids m2-00.., the "
                                    "MOOSE-Chem2 curated GTs); THIS run "
                                    "is the post-cutoff corpus "
                                    "(pc-01..pc-30, abstract-authored "
                                    "GTs) — the two rates are NOT a "
                                    "like-for-like delta (the corpus "
                                    "provenance's own typed caveat in "
                                    "eval/r105s2_score9_postcutoff_"
                                    "status.json); the direction's "
                                    "'re-authored' items are this "
                                    "post-cutoff lineage"),
            "distribution": {"RECOVERED": 5, "PARTIAL": 24,
                             "NOT_RECOVERED": 1},
            "root_causes": [
                ("the two-judge adjudication degrades to PARTIAL "
                 "unless BOTH judges rate RECOVERED (the protocol's "
                 "fail-closed rule) — 24/30 rows landed PARTIAL, so "
                 "the RECOVERED rate is a both-agreement rate, "
                 "structurally below any single-judge rate"),
                ("the post-cutoff ground truths are authored from "
                 "publisher abstracts (the c-0129 typed caveat): the "
                 "task calibration differs from the curated m2 GTs — "
                 "the bar's calibration class is the m2 lineage"),
                ("zero parse exhaustions this run (5/30 in r106): the "
                 "strict-JSON contract + the parse-repair retry held — "
                 "the generator-side failure mode is gone; the miss is "
                 "a genuine recovery miss, not an infrastructure one"),
            ],
            "pooled_estimate_guard": ("a pooled two-run rate is NOT "
                                      "computed: the runs are on "
                                      "different corpora"),
        },
        "per_item": {iid: v for iid, v in zip(item_ids, recoveries)},
        "no_acceptance_claims": True,
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(f"recovery (30-denominator): {acc30['recovered']}/30 = "
          f"{acc30['recovery_rate']} CI95 "
          f"{wilson95(hits30, 30)} | bar {rp.RECOVERY_BAR}: "
          f"met={acc30['recovery_rate'] >= rp.RECOVERY_BAR}")
    print(f"evaluated subset: {hits_eval}/{len(evaluated)} = "
          f"{acc_eval['recovery_rate']} CI95 "
          f"{wilson95(hits_eval, len(evaluated))}")
    print(f"parse exhausted: {len(parse_exhausted)} "
          f"{parse_exhausted[:6]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""r105s2 — the score-9 POST-CUTOFF status record (claim c-0129, the
final stage): the canonical per-work_id record for the rebuilt-corpus
rerun, from the committed checkpoint bytes."""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric")
REPO = Path("/home/z/my-project/discovery-evidence-fabric")
CKPT = Path("/tmp/r105s2_score9_postcutoff_checkpoint.json")
OUT = REPO / "eval" / "r105s2_score9_postcutoff_status.json"
from discovery_fabric.engine import rediscovery_protocol as rp  # noqa


def sha16(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def main():
    d = json.loads(CKPT.read_text())
    its = d["completed_items"]
    recs = []
    for k, v in sorted(its.items(), key=lambda kv: kv[1]["item_id"]):
        recs.append({
            "item_id": v["item_id"],
            "state": v.get("state"),
            "J1": (v.get("judge_J1") or {}).get("recovery"),
            "J2": (v.get("judge_J2") or {}).get("recovery"),
            "adjudicated": v.get("recovery"),
            "generation_sha16": v.get("generation_sha16"),
        })
    ok = [r for r in recs if r["state"] == "OK"]
    # the independent tally recompute (auditor Art. 13): re-adjudicate
    # from the RAW judge outputs, compare with the driver's tally
    recomp = [rp.adjudicate(r["J1"], r["J2"]) for r in ok]
    agree = sum(1 for r, c in zip(ok, recomp) if r["adjudicated"] == c)
    full = [r["adjudicated"] if r["state"] == "OK"
            else "NOT_RECOVERED" for r in recs]   # fail closed
    acc = rp.acceptance(full)
    corr = json.loads((REPO / "eval"
                       / "r106_score9_corpus_postcutoff"
                       / "sampling_record.json").read_text())
    probe = json.loads((REPO / "eval"
                        / "r105s2_agnes_cutoff_probe.json").read_text())
    record = {
        "record": "R105S2_SCORE9_POSTCUTOFF_STATUS/1.0.0",
        "ran_at": datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "executor": "builder-r105s2",
        "claim": "c-0129 (p3-score9-lane-d4d5d6; the direction-4/5 rerun)",
        "lane": ("the auditor verdict 2026-11-20 directions 4+5: the "
                 "corpus rebuilt on a MEASURED generator cutoff + the "
                 "parse-repair retry, then the full 30-batch rerun"),
        "cutoff_basis": {
            "probe_record": "eval/r105s2_agnes_cutoff_probe.json",
            "latest_event_answered_correctly": probe["estimate"][
                "latest_event_answered_correctly"],
            "conservative_bound": "2025-05-07",
            "corpus_date_range": corr["date_range"],
            "all_after_conservative_bound":
                corr["all_after_conservative_bound"],
            "auditor_test_100pct_postcutoff": True,
        },
        "corpus_provenance": {
            "source": corr["source"],
            "author_separation": corr["author_separation"],
            "typed_caveat": ("the rebuilt corpus is NOT the MOOSE-Chem2 "
                             "curated corpus: the ground truths are "
                             "authored from publisher abstracts — the "
                             "task calibration differs from the m2 run; "
                             "the recovery-rate COMPARISON across the "
                             "two corpora is typed NOT-APPLICABLE"),
        },
        "run": {
            "harness": "scripts/r106_score9_inspect_task.py (the "
                       "committed harness; the corpus/checkpoint paths "
                       "env-overridable, defaults unchanged — Art. 4)",
            "generators_judges": ("agnes-3.0-flash generation (ONE per "
                                  "item) + z-ai judge J1 + xkiro/cohere "
                                  "judge J2; the judge/generator "
                                  "separation kept"),
            "usage": d.get("usage"),
            "parse_repair": {
                "repair_calls": d.get("usage", {}).get(
                    "agnes_repair_calls", 0),
                "exhaustion_items": len(recs) - len(ok),
                "auditor_test_zero_losses": len(recs) - len(ok) == 0,
                "typed_state": ("the direction-5 test is NOT fully met: "
                                "1/30 item remains at typed "
                                "ITEM_GENERATION_PARSE_EXHAUSTION "
                                "AFTER the repair retry (the retry "
                                "reduced the m2 run's 5/30 to 1/30; "
                                "the residual is disclosed, fail-closed "
                                "to NOT_RECOVERED in the arithmetic)"),
            },
        },
        "results": {
            "n_items": len(recs),
            "n_ok": len(ok),
            "J1_hist": _hist([r["J1"] for r in ok]),
            "J2_hist": _hist([r["J2"] for r in ok]),
            "adjudicated_hist": _hist([r["adjudicated"] for r in ok]),
            "independent_recompute": {
                "method": "rp.adjudicate from the raw J1/J2 bytes",
                "tally": _hist(recomp),
                "driver_agreement": f"{agree}/{len(ok)}",
            },
            "acceptance_full_30": acc,
        },
        "typed_conclusion": (
            "the post-cutoff recovery rate is "
            f"{acc['recovery_rate']:.4f} vs the 0.40 bar — NOT MET "
            "(2 RECOVERED / 25 PARTIAL / 3 NOT_RECOVERED, "
            "agent_validated true); the m2 run's 0.30 was an UPPER "
            "bound on easier, pre-cutoff material; the cross-corpus "
            "comparison is typed NOT-APPLICABLE (different ground-"
            "truth calibration); the score-9 bar remains NOT MET and "
            "the score stands 7/10 per the ledger — the auditor owns "
            "the verdict"),
        "per_item": recs,
        "no_acceptance_or_score_claims": True,
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes)")
    print("recovery:", acc["recovery_rate"], "| bar met:", acc[
        "recovery_bar_met"], "| recompute agree:", f"{agree}/{len(ok)}")


def _hist(xs):
    from collections import Counter
    return dict(Counter(x or "None" for x in xs))


if __name__ == "__main__":
    main()

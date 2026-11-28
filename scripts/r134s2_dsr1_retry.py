#!/usr/bin/env python3
"""r134s2_dsr1_retry — the typed one-attempt transport-retry pass for
the dsr1 legs whose BOTH attempts hit 504 gateway timeouts (claim
c-0214, prereg eval/r134s2_resume_prereg.json — typed before the run).

Writes SEPARATE __retry1.json records; canonical records are NEVER
mutated. SUPERSEDE RULE: a retry record replaces the canonical in the
tally ONLY IF outcome == VALID (enforced by the recompute's load_raw
merge). The prompt contract is byte-identical to the driver's
(same blind_order parity, same build_pair_prompt(cot=True), same
JUDGES entry), cross-asserted against the failed record's own
order/a_is/pass fields.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path(__file__).resolve().parents[1] / "eval" / "r134_panel"

from r134_panel_driver import JUDGES, SYSTEM, _leg, _load_r5, blind_order  # noqa: E402
from discovery_fabric.engine.blind_panel import build_pair_prompt  # noqa: E402

RETRY_TAGS = ("dsr1", "llama4mav")  # typed scope per the prereg: the
# dsr1 504s + ANY llama4mav transport fail the resume lands (missing
# legs are the driver's byte-resume job, not this pass)


def pairs_by_pid():
    return {p["pid"]: p for p in _load_r5()}


def judge_by_tag(tag):
    for j in JUDGES:
        if j["tag"] == tag:
            return j
    raise SystemExit(f"no judge {tag}")


def retry_one(tag: str, pid: str, pas: str) -> None:
    j = judge_by_tag(tag)
    p = pairs_by_pid()[pid]
    order = blind_order(pid)
    if order == "a1_first":
        det, mir = (p["a1"], p["base"]), (p["base"], p["a1"])
    else:
        det, mir = (p["base"], p["a1"]), (p["a1"], p["base"])
    a_text, b_text = det if pas == "det" else mir
    a_is = "a1" if (pas == "det") == (order == "a1_first") else "baseline"
    canon = OUT / f"{tag}__{pid}__{pas}.json"
    old = json.loads(canon.read_text())
    assert old["order"] == order and old["a_is"] == a_is and \
        old["pass"] == pas, f"contract drift on {canon.name}"
    assert old.get("outcome") != "VALID", "canonical already VALID"
    prompt = build_pair_prompt(p["prob"], a_text, b_text, cot=True)
    r = _leg(j, prompt, j["max_tokens"], j["timeout_s"])
    rec = {
        "judge_family": j["family"], "model": j["model"],
        "problem_id": pid, "order": order, "pass": pas,
        "a_is": a_is,
        "outcome": r["outcome"], "parsed": r["parsed"],
        "attempts": r["attempts"],
        "auditor_label": p["label"],
        "lever": "CoT comparative prompt (R134 lever a) + the rung "
                 "per the prereg",
        "engine_contract": "blind_panel.build_pair_prompt(cot=True)"
                           "+parse_pair_rating",
        "retry_of": canon.name,
        "retry_supersede_rule": "replaces the canonical record in the "
                                "tally ONLY IF outcome == VALID "
                                "(prereg eval/r134s2_resume_prereg.json)",
    }
    out = OUT / f"{tag}__{pid}__{pas}__retry1.json"
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"  retry {out.name}: {r['outcome']} "
          f"{r['attempts'][-1]['latency_s']}s", flush=True)


def main() -> int:
    targets = []
    for f in sorted(OUT.glob("*.json")):
        parts = f.stem.split("__")
        if len(parts) != 3 or parts[0] not in RETRY_TAGS:
            continue
        rec = json.loads(f.read_text())
        if rec.get("outcome") in ("TRANSPORT_FAILED", "RATE_LIMITED"):
            targets.append((parts[0], parts[1], parts[2]))
    print(f"typed transport-retry pass: {len(targets)} leg(s)", flush=True)
    for tag, pid, pas in targets:
        retry_one(tag, pid, pas)
        time.sleep(5)
    print("retry pass complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

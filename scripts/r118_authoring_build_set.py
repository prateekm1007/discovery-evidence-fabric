#!/usr/bin/env python3
"""r118_authoring_build_set.py — build the F31a authoring-task set
(eval/r118_authoring_set/) per eval/r118_authoring_bind_value_prereg.json:
the SAME 12 pair-scenarios / 6 defect classes / sealed key spans as the
F30 v1.1.0 battery, REKEYED for authoring (question_type
intervention-proposal, the v15 problem shape, NO draft embedded).

Output: items.jsonl (24 authoring items) + key.json (the class map +
the same deterministic detectors' ground truth). Zero LLM, zero
network. The defect detectors are the F30 preflight's own logic
(imported, never re-declared).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

SRC_ITEMS = REPO / "eval" / "r116_f30_set" / "items_v1_1.jsonl"
SRC_KEY = REPO / "eval" / "r116_f30_set" / "seeded_defect_key_v1_1.json"
OUT = REPO / "eval" / "r118_authoring_set"
OUT.mkdir(parents=True, exist_ok=True)


def authoring_question(failure: str) -> str:
    return f"Propose a mitigation for {failure}."


def main() -> int:
    key = json.loads(SRC_KEY.read_text(encoding="utf-8"))
    src = [json.loads(l) for l in
           SRC_ITEMS.read_text(encoding="utf-8").strip().split("\n")]
    # the scenario fields come from the healthy twins (device/failure/
    # constraint are pair-shared); strip the draft-review question
    by_pid = {i["problem_id"]: i for i in src}
    rows, key_pairs = [], []
    for p in key["pairs"]:
        base = p["item_id"]
        h = by_pid[p["healthy_problem_id"]]
        for seed in (1, 2):
            pid = f"f31a-{base[4:]}-s{seed}"
            rows.append({
                "problem_id": pid,
                "device": h["device"],
                "failure": h["failure"],
                "question": authoring_question(h["failure"]),
                "question_type": "intervention-proposal",
                "constraint": h["constraint"],
                "user_variables": h.get("user_variables", ""),
            })
        key_pairs.append({
            "pair": base, "class": p["class"],
            "key_span": p["key_span"],
            "items": [f"f31a-{base[4:]}-s1", f"f31a-{base[4:]}-s2"]})
    (OUT / "items.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        + "\n", encoding="utf-8")
    (OUT / "key.json").write_text(json.dumps({
        "record": "R118_AUTHORING_SET/1.0.0",
        "note": "the F31a authoring battery: the 12 F30 pair-scenarios "
                "x 2 seeds, rekeyed for authoring (no draft embedded); "
                "the class map + key spans are the F30 v1.1.0 bytes; "
                "the detectors are scripts/r117_f30_build_v11.py's own "
                "logic (imported at scoring time); generation prompts "
                "never read this file",
        "pairs": key_pairs}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"written: {OUT/'items.jsonl'} ({len(rows)} items) + key.json")
    # sanity: no draft text leaked into the authoring questions
    assert all("DRAFT" not in r["question"] for r in rows)
    print("sanity: no draft text in authoring questions — PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

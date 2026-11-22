#!/usr/bin/env python3
"""r117_f30_build_v11.py — regenerate the F30 set at v1.1.0 per
eval/r117_f30_prereg_amendment_1.json: the DRAFT PROPOSAL embedded in
the question field (the v1.0.0 canonical answers, verbatim), so the
seeded defect lives in the problem bytes the arms actually read.

The 12 defect classes, key spans and canonical answers are UNCHANGED
from v1.0.0 (read from the committed key, never re-authored). The
output: eval/r116_f30_set/items_v1_1.jsonl + key_v1_1.json. The v1.0.0
files stay in git history. Zero LLM, zero network.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

SET = REPO / "eval" / "r116_f30_set"
OLD_ITEMS = SET / "items.jsonl"
OLD_KEY = SET / "seeded_defect_key.json"
NEW_ITEMS = SET / "items_v1_1.jsonl"
NEW_KEY = SET / "seeded_defect_key_v1_1.json"

from discovery_fabric.engine import physics_checks as pc  # noqa: E402
from r40_machine_v77 import (  # noqa: E402
    scan_input_availability, scan_duty_cycle_pricing)


def review_question(draft: str) -> str:
    return ("A draft mitigation proposal is given below. Review it "
            "against the stated failure and constraint: does it "
            "violate any constraint, rely on anything unavailable, "
            "invert any physical direction, or misprice any duty "
            "cycle? Answer with your verdict and reasoning.\n\n"
            "DRAFT PROPOSAL:\n" + draft)


def build():
    key = json.loads(OLD_KEY.read_text(encoding="utf-8"))
    pairs = key["pairs"]
    rows, new_key_pairs = [], []
    for p in pairs:
        base_id = p["item_id"]
        # the v1.0.0 items carry the shared problem fields per pair
        old = [json.loads(l) for l in
               OLD_ITEMS.read_text(encoding="utf-8").strip().split("\n")]
        pair_items = {i["item_id"].rsplit("-", 1)[-1]: i for i in old
                      if i["item_id"].rsplit("-", 1)[0] == base_id}
        healthy_prob = pair_items["healthy"]
        for side, ans_key, flag in (("h", "answer_healthy", False),
                                    ("s", "answer_seeded", True)):
            draft = p[ans_key]
            row = {
                "problem_id": f"{base_id}-{side}",
                "device": healthy_prob["device"]
                if "device" in healthy_prob else
                healthy_prob["failure"].split(";")[0][:60],
                "failure": healthy_prob["failure"],
                "question": review_question(draft),
                "question_type": "draft-review",
                "constraint": healthy_prob["constraint"],
                "user_variables": healthy_prob.get(
                    "user_variables", ""),
            }
            rows.append(row)
        new_key_pairs.append({
            "item_id": base_id,
            "class": p["class"],
            "key_span": p["key_span"],
            "mutation": p["mutation"],
            "seeded_problem_id": f"{base_id}-s",
            "healthy_problem_id": f"{base_id}-h",
            "answer_healthy": p["answer_healthy"],
            "answer_seeded": p["answer_seeded"],
        })
    return rows, new_key_pairs


def detector_fires(cls: str, prob: dict, review_text: str) -> bool:
    """The deterministic detector on a REVIEW text: caught = the review
    names/declines/corrects the defect (for the arms) — for the
    preflight the same detector must fire on the machine-side draft
    finding class. Here: prove the defect is DETECTABLE from the
    problem bytes alone (the draft carries it)."""
    if cls == "input_availability":
        r = scan_input_availability(prob, prob["question"])
        return "INPUT_UNAVAILABLE" in json.dumps(r)
    if cls == "duty_pricing":
        # the draft (in the question) modulates a duty schedule unpriced
        r = scan_duty_cycle_pricing(prob["question"])
        return "UNPRICED_DUTY_CYCLE" in json.dumps(r)
    if cls == "physics_direction_inversion":
        m = re.search(r"(\d+)\s*C", prob["question"])
        if not m:
            return False
        r = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=80.0,
                         t1_degC=24.0, t2_degC=float(m.group(1)))
        return r["verdict"] == "RUN" and (
            r["direction_of_effect"] == "worsens")
    if cls == "measurement_not_allowed":
        return bool(re.search(
            r"(?:hold|trim|control|close the loop)\w*[^.]{0,60}pH|"
            r"pH[^.]{0,60}(?:loop|trim|feedback)", prob["question"],
            re.I)) and not re.search(
            r"no\s+pH\s+feedback", prob["question"], re.I)
    if cls == "constraint_violation":
        return "automatic lubricator" in prob["question"].lower()
    if cls == "magnitude_bound_violation":
        m = re.search(r"(\d+(?:\.\d+)?)\s*mol/L", prob["question"])
        return bool(m) and float(m.group(1)) > 0.9
    raise ValueError(cls)


def healthy_draft_clean(cls: str, prob: dict) -> bool:
    """The healthy twin's draft (in its question) must NOT trip the
    detector — no false alarm by construction."""
    return not detector_fires(cls, prob, "")


def main() -> int:
    rows, new_pairs = build()
    # preflight on the EMBEDDED drafts: the seeded item's problem
    # bytes must trip the detector; the healthy twin's must not
    by_pid = {r["problem_id"]: r for r in rows}
    fires, silent = 0, 0
    for p in new_pairs:
        s_prob = by_pid[p["seeded_problem_id"]]
        h_prob = by_pid[p["healthy_problem_id"]]
        if detector_fires(p["class"], s_prob, ""):
            fires += 1
        else:
            print("SEED NOT EMBEDDED:", p["item_id"], p["class"])
        if not detector_fires(p["class"], h_prob, ""):
            silent += 1
        else:
            print("FALSE ALARM BY CONSTRUCTION:", p["item_id"],
                  p["class"])
    n = len(new_pairs)
    ok = fires == n and silent == n
    NEW_ITEMS.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        + "\n", encoding="utf-8")
    NEW_KEY.write_text(json.dumps({
        "record": "R117_F30_SEEDED_DEFECT_KEY/1.1.0",
        "note": "v1.1.0 per eval/r117_f30_prereg_amendment_1.json: the "
                "draft proposal embedded in the question field; the "
                "canonical answers are the v1.0.0 bytes UNCHANGED; "
                "generation prompts never read this file",
        "preflight_v1_1": {
            "seeded_problem_bytes_trip_detector": f"{fires}/{n}",
            "healthy_problem_bytes_clean": f"{silent}/{n}",
            "verdict": "PASS" if ok else "FAIL",
        },
        "pairs": new_pairs}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"v1.1 preflight: seeded {fires}/{n}, healthy {silent}/{n} "
          f"-> {'PASS' if ok else 'FAIL'}")
    print(f"written: {NEW_ITEMS} ({len(rows)}) + {NEW_KEY}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

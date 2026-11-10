#!/usr/bin/env python3
"""Problem-set integrity: disjointness + pre-registered selection hash.

Directive (audit hold): "add a disjointness test and a pre-registered
selection hash for new problems, else tag them DEV".

Two checks, both deterministic and side-effect free by default:

1. DISJOINTNESS -- pairwise token Jaccard over device+failure+question.
   A pair at or above the threshold (0.60) is a near-duplicate: the
   newer problem is a development (DEV) item, never a holdout sample.

2. SELECTION HASH -- sha256 over the canonical (id, device, failure,
   question, question_type, user_variables) tuples of every FRESH
   problem (contamination_tag is None), sorted by id. The value is
   pre-registered in problems.json before the run; a mismatch means the
   selection changed after registration and every unmatched new problem
   is tagged DEV.

Usage:
  python -B eval/validate_problems.py            # check (exit 1 on fail)
  python -B eval/validate_problems.py --write-hash  # register hash
  python -B eval/validate_problems.py --tag-dev     # force split=DEV
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PROBLEMS = Path(__file__).resolve().parent / "problems.json"
PROVENANCE = Path(__file__).resolve().parent / "PROBLEM_PROVENANCE.json"
THRESHOLD = 0.60
_STOP = frozenset(
    "the a an and or of to in for on with without at by from into during "
    "is are was were be been being this that these those it its their "
    "can could should must may might will would do does did not no "
    "than then when where which who whom whose what how why".split())


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-]+", (text or "").lower())
            if w not in _STOP and len(w) > 2}


def _key(p: dict) -> str:
    return " ".join(str(p.get(k) or "") for k in
                    ("device", "failure", "question"))


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _selection_payload(p: dict) -> list:
    return [p.get("problem_id"), p.get("device"), p.get("failure"),
            p.get("question"), p.get("question_type"),
            list(p.get("user_variables") or [])]


def selection_hash(problems: list) -> str:
    fresh = [p for p in problems if p.get("contamination_tag") is None]
    payload = [_selection_payload(p) for p in sorted(
        fresh, key=lambda x: str(x.get("problem_id")))]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def disjointness(problems: list) -> list:
    rows = []
    toks = {p["problem_id"]: _tokens(_key(p)) for p in problems}
    for i, a in enumerate(problems):
        for b in problems[i + 1:]:
            j = _jaccard(toks[a["problem_id"]], toks[b["problem_id"]])
            if j >= THRESHOLD:
                rows.append({"a": a["problem_id"], "b": b["problem_id"],
                             "jaccard": round(j, 3)})
    return sorted(rows, key=lambda r: -r["jaccard"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-hash", action="store_true")
    ap.add_argument("--tag-dev", action="store_true")
    args = ap.parse_args(argv)

    doc = json.loads(PROBLEMS.read_text(encoding="utf-8"))
    problems = doc["problems"]
    h = selection_hash(problems)
    dupes = disjointness(problems)
    registered = doc.get("selection_sha256")

    if args.write_hash:
        doc["selection_sha256"] = h
        doc["selection_hash_basis"] = (
            "sha256 over canonical tuples of FRESH problems "
            "(contamination_tag is None), sorted by problem_id")
        PROBLEMS.write_text(json.dumps(doc, indent=1, ensure_ascii=False)
                            + "\n", encoding="utf-8")
        registered = h
        print(f"[problems] registered selection_sha256={h}")

    if args.tag_dev:
        for p in problems:
            p["split"] = "DEV"
        PROBLEMS.write_text(json.dumps(doc, indent=1, ensure_ascii=False)
                            + "\n", encoding="utf-8")

    hash_ok = bool(registered and registered == h)
    disjoint_ok = not dupes
    # every problem is explicitly DEV unless it passed BOTH checks and
    # was registered (no silent holdout claim)
    for p in problems:
        p.setdefault("split", "DEV")
        if not (hash_ok and disjoint_ok):
            p["split"] = "DEV"

    prov = {
        "selection_sha256": h,
        "registered_selection_sha256": registered,
        "hash_ok": hash_ok,
        "disjointness_threshold": THRESHOLD,
        "disjointness_ok": disjoint_ok,
        "near_duplicates": dupes,
        "split_reason": ("hash registered AND disjoint" if
                         (hash_ok and disjoint_ok) else
                         "hash missing/mismatch or near-duplicate -> DEV"),
        "n_problems": len(problems),
        "n_fresh": sum(1 for p in problems
                       if p.get("contamination_tag") is None),
    }
    PROVENANCE.write_text(json.dumps(prov, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(prov, indent=1))
    return 0 if (hash_ok and disjoint_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""test_seal_anchor.py — the auditor's seal-anchor recipe as an executable
check (AM34/35 F50 ruling; required instrument, run by BOTH sides before
any burn so a recipe error can never again masquerade as a custody break).

The registered `selection_sha256` is NOT a file hash. It is the sha256 of
the canonical-tuple projection of the fresh problems:
  [problem_id, device, failure, question, question_type, list(user_variables)]
sorted by problem_id, serialized json.dumps(..., sort_keys=True,
ensure_ascii=False, separators=(',',':')).

Recipe provenance: audit/r11-auditor-verdict-20261114 @ 5b4fd95db:
eval/seal_anchor_verification_recipe.json (identical basis to
eval/validate_problems.py and the selection_hash_basis field in every
holdout doc). Problems docs ride `git show` from the audit branch —
auditor-controlled bytes are never copied into the queue tree.

Applies to holdout v1..v6 (the recipe's applies_to list): every problems
doc that carries a `selection_sha256` field is checked.
"""
import json, hashlib, subprocess

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
HOLDOUTS = [1, 2, 3, 4, 5, 6]


def _load_doc(v):
    out = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:audit/holdout_v{v}/holdout_v{v}_problems.json"],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return json.loads(out.stdout)


def _project(p):
    return [p["problem_id"], p["device"], p["failure"], p["question"],
            p["question_type"], list(p["user_variables"])]


def _selection_hash(doc):
    fresh = [p for p in doc["problems"] if p.get("contamination_tag") is None]
    blob = json.dumps([_project(p) for p in sorted(fresh, key=lambda x: x["problem_id"])],
                      sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_seal_anchor_v1_to_v6():
    checked = []
    for v in HOLDOUTS:
        doc = _load_doc(v)
        if doc is None:
            continue  # problems doc not present on the audit branch tip
        if "selection_sha256" not in doc:
            continue  # older docs may register the hash in PREREGISTRATION only
        recomputed = _selection_hash(doc)
        assert recomputed == doc["selection_sha256"], (
            f"holdout v{v}: recomputed selection hash {recomputed[:16]} != "
            f"registered {doc['selection_sha256'][:16]} (canonical-tuple projection)")
        checked.append(f"v{v}:{doc['selection_sha256'][:8]}")
    # the v6 seal is the live acceptance instrument: it MUST be present and anchored
    doc6 = _load_doc(6)
    assert doc6 is not None, "holdout v6 problems doc missing from the audit branch tip"
    assert "selection_sha256" in doc6, "holdout v6 doc carries no selection_sha256"
    assert _selection_hash(doc6) == doc6["selection_sha256"], "v6 seal anchor mismatch"
    assert len([p for p in doc6["problems"] if p.get("contamination_tag") is None]) == 12, \
        "v6 fresh-problem count != 12"
    assert checked and any(c.startswith("v6:") for c in checked), checked


if __name__ == "__main__":
    test_seal_anchor_v1_to_v6()
    print("SEAL ANCHOR: EXACT (canonical-tuple projection, holdouts checked)")

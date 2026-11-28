#!/usr/bin/env python3
"""tests/test_seal_anchor.py — AM34/35 F50 required instrument.

The registered `selection_sha256` of every holdout problems doc is
the sha256 of the canonical-TUPLE projection (NOT a file hash):

    [problem_id, device, failure, question, question_type,
     list(user_variables)]

of every FRESH problem (contamination_tag is None), sorted by
problem_id, json.dumps(sort_keys=True, ensure_ascii=False,
separators=(',',':')). Recipe (published by the auditor,
eval/seal_anchor_verification_recipe.json, identical to
eval/validate_problems.py): run by BOTH sides before any burn, so a
recipe error can never again masquerade as a custody break.

Auditor bytes are NEVER copied into the queue tree: the problems docs
ride `git show` from the pinned audit tip at runtime. If the audit
ref is unavailable (e.g. an offline checkout), the case is a typed
SKIP — never a silent pass.
"""
import hashlib
import json
import subprocess

import pytest

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
AUDIT_TIP = "5b4fd95db"
HOLDOUTS = [f"audit/holdout_v{v}/holdout_v{v}_problems.json"
            for v in range(1, 7)]


def _canonical_tuple_hash(doc):
    fresh = [p for p in doc["problems"]
             if p.get("contamination_tag") is None]
    payload = [
        [p.get("problem_id"), p.get("device"), p.get("failure"),
         p.get("question"), p.get("question_type"),
         list(p.get("user_variables") or [])]
        for p in sorted(fresh, key=lambda x: str(x.get("problem_id")))]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _audit_doc(path):
    for ref in (AUDIT_REF, AUDIT_TIP):
        r = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout), ref
    # the audit ref may be absent on a shallow CI checkout: fetch it
    subprocess.run(
        ["git", "fetch", "origin", "audit/r11-auditor-verdict-20261114",
         "--depth=1"], capture_output=True, text=True, timeout=120)
    r = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:{path}"],
        capture_output=True, text=True)
    if r.returncode == 0:
        return json.loads(r.stdout), AUDIT_REF
    pytest.skip(f"audit ref unavailable (offline checkout): {path}")


@pytest.mark.parametrize("path", HOLDOUTS)
def test_seal_anchor(path):
    doc, ref = _audit_doc(path)
    registered = doc.get("selection_sha256")
    if not registered:
        # typed skip: holdout_v3 predates the selection-hash recipe;
        # its custody rests on its own era's registration mechanism
        pytest.skip(f"{path}: no registered selection_sha256 "
                    "(pre-recipe era; typed skip, not a pass)")
    recomputed = _canonical_tuple_hash(doc)
    assert recomputed == registered, (
        f"{path} @ {ref}: recomputed canonical-tuple hash "
        f"{recomputed[:16]} != registered {registered[:16]} — the "
        "selection changed after registration; NO BURN (Art. 3)")


def test_v6_seal_anchor_exact():
    """The acceptance-relevant pin: the v6 problems doc recomputes to
    the pre-registered 4d60488a… EXACTLY (F50, verified by BOTH
    sides)."""
    doc, ref = _audit_doc(HOLDOUTS[5])
    assert doc.get("selection_sha256") == (
        "4d60488a581897b9b7452158158049e65656c26ac58ea7e611236047a9aab804")
    assert _canonical_tuple_hash(doc) == doc["selection_sha256"]
